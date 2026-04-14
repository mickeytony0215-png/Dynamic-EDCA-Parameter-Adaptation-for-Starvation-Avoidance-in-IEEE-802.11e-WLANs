# QAD-EDCA 開發紀錄 — 2026-04-14

## 開發目標

根據 `docs/inet-integration-design.md` 設計文件，在 OMNeT++ 6.1 / INET 4.5 環境中完整實作 QAD-EDCA（Queue-Aware Dynamic EDCA）演算法，使其能在模擬中動態調整 EDCA 參數以緩解低優先權 AC 的飢餓問題。

---

## 第一階段：核心實作

### 1. 建立子類化模組鏈

由於 INET 4.5 的 Edcaf 和 TxopProcedure 為固定型別子模組，OMNeT++ 6.1 不支援透過 INI 的 `typename` 覆蓋固定型別宣告。解法：從 `Ieee80211Mac` 的 `hcf: <default("Hcf")> like IHcf`（唯一的參數化型別入口）開始，建立完整替換鏈：

```
*.ap.wlan[*].mac.hcf.typename = "edcafairness.src.QadHcf"
  → QadHcf (NED 複製 Hcf，edca 改用 QadEdca)
    → QadEdca (NED 複製 Edca，edcaf[*] 改用 QadEdcaf)
      → QadEdcaf (C++ 子類，新增 setEdcaParameters())
        → QadTxopProcedure (C++ 子類，新增 setTxopLimit())
```

`QadEdcaf::setEdcaParameters()` 直接修改 Edcaf 的 protected 成員（cwMin/cwMax/cw/ifs/eifs），繞過 `@mutable` 限制。`QadHcf` 和 `QadEdca` 的 C++ 行為完全繼承自 INET 原始類別（NED 用 `@class(inet::ieee80211::Hcf)` / `@class(inet::ieee80211::Edca)` 指向原始 C++ 類別）。

### 2. 實作 QadEdcaManager 核心邏輯

四個 TODO 函數全部實作完成：

- **`getQueueLength(ac)`**：透過快取的 `IPacketQueue*` 呼叫 `getNumPackets()`
- **`getPacketLossRate(ac)`**：訂閱 hcf 的 `packetDroppedSignal`（利用 signal 上冒收到所有子孫丟包），以 `findAcForQueue(source)` 判別 AC；入隊數由各 pendingQueue 的 `packetPushedInSignal` 追蹤
- **`getAverageDelay(ac)`**：訂閱各 edcaf 的 `packetSentToPeerSignal`，以 `simTime() - packet->getCreationTime()` 計算端對端延遲
- **`applyParameters()`**：透過 `QadEdcaf::setEdcaParameters()` 和 `QadTxopProcedure::setTxopLimit()` 寫入 MAC 模組

### 3. 網路拓撲與場景配置

- `network.ned`：新增條件式 `qadManager: QadEdcaManager if hasQadManager`
- `qad_edca.ini`：啟用 `hasQadManager = true` + QadHcf typename override
- `package.ned`：建立 NED 套件根（`package edcafairness;`）
- `run.sh`：執行腳本，支援 GUI（Qtenv）/ CLI（Cmdenv）切換

---

## 第二階段：Bug 修復（依審查報告 `code-review-2026-04-14.md`）

### [CRITICAL] packetDroppedSignal 雙重計數

**問題**：同時在 hcf 和 pendingQueue 訂閱 `packetDroppedSignal`，OMNeT++ signal 向上傳播導致佇列溢出丟包被計數兩次。
**修復**：移除 pendingQueue 的 `packetDroppedSignal` 訂閱，只保留 hcf（利用 signal 上冒特性）。

### [HIGH] applyRecovery() 整數截斷

**問題**：`(int)(0.3 * 1) = 0`，差值 ≤ 3 時 AIFSN/CWmin 恢復永遠卡住。
**修復**：引入 `smoothParams[4]`（`EdcaParamsDouble { double cwMin, aifsn }`）作為浮點累加器，僅在傳給 `setEdcaParameters()` 時 `std::round` 成整數。

### [MEDIUM] cw 每 100ms 被強制重置為 cwMin

**問題**：`setEdcaParameters()` 無條件設 `cw = cwMin`，每 100ms 清除 802.11 指數退避狀態。
**修復**：(1) `QadEdcaf::setEdcaParameters()` 改為 `if (cw < cwMin) cw = cwMin`（只向上夾）；(2) `applyParameters()` 引入 `prevAppliedParams[4]` 比對，只在參數實際改變時才呼叫。

### [LOW] 其他清理

- Getter 副作用：拆出 `resetIntervalCounters()`，在 `monitorAndAdjust()` 末端統一重置所有 AC 計數器
- QadEdca 死碼：刪除不必要的 `QadEdca.h/cc`（NED 用 `@class(inet::ieee80211::Edca)` 直接指向原始類別）
- 析構清理：新增 `unsubscribeFromSignals()` + `subscribedToSignals` 旗標，destructor 與 `finish()` 共用
- omnetpp.ini：移除 QoS 模式下無效的 `dcf.channelAccess.cwMin/cwMax` 設定

---

## 設計約束遵守情況

| 約束 | 狀態 |
|------|------|
| 不修改 `~/simulation/inet4.5/` 的任何檔案 | 遵守 |
| 所有編譯產出在專案的 `out/` 目錄 | 遵守 |
| 透過子類化存取 INET 的 protected 成員 | 遵守 |
| 運算複雜度 O(1) / 監控週期 | 遵守 |

---

## 模擬結果（Bug 修復後，Baseline_N10 vs QadEdca_N10，30s，run #0）

| 指標 | Baseline | QAD-EDCA | 變化 |
|------|----------|----------|------|
| AC_VO 封包數 | 1,497 | 1,497 | **+0.0%** |
| AC_VI 封包數 | 2,996 | 2,996 | **+0.0%** |
| AC_BE 封包數 | 6,312 | 17,894 | **+183.5%** |
| AC_BK 封包數 | 1,199 | 1,198 | -0.1% |
| AC_VO 平均延遲 | 21.3 ms | 19.6 ms | **-7.8%** |
| AC_VI 平均延遲 | 20.9 ms | 20.4 ms | -2.2% |
| AC_BE 平均延遲 | 1,088 ms | 676 ms | **-37.8%** |
| AC_BK 平均延遲 | 75.0 ms | 51.7 ms | **-31.0%** |
| 封包丟棄 | 13,044 | **0** | **-100%** |
| 總封包數 | 12,004 | 23,585 | **+96.5%** |
| Jain's Fairness Index | 0.686 | 0.418 | 需優化 |

**結論**：修復後 AC_VO/VI 的 throughput 和延遲完全不受影響（修復前 VO 曾下降 18.5%），同時 AC_BE 飢餓問題有效緩解。Jain's Fairness Index 仍偏低，因為 AC_BE 獲得過多資源，需後續調參。

---

## 目前專案檔案結構

```
src/
├── QadEdcaManager.h/cc/ned   ← 核心演算法（已完成所有功能）
├── QadEdcaf.h/cc/ned          ← Edcaf 子類（setEdcaParameters）
├── QadTxopProcedure.h/cc/ned  ← TxopProcedure 子類（setTxopLimit）
├── QadEdca.ned                ← Edca NED 複製（用 QadEdcaf 子模組）
└── QadHcf.ned                 ← Hcf NED 複製（用 QadEdca 子模組）

simulations/
├── network.ned                ← 網路拓撲（含條件式 qadManager）
├── omnetpp.ini                ← 主配置
├── package.ned
└── scenarios/
    ├── baseline.ini           ← Standard EDCA
    ├── qad_edca.ini           ← QAD-EDCA（啟用 QadHcf）
    └── high_load.ini          ← 高負載壓力測試

package.ned                    ← NED 套件根
run.sh                         ← 執行腳本（GUI/CLI 切換）
HOW_TO_RUN.md                  ← 組員操作指南
```

---

## 後續開發指南

### 階段 1：參數調優（改善 Jain's Fairness Index）

目前 Jain's Index 0.418 偏低的主因是 AC_BE 獲得過多資源（17,894 vs 其他 AC ~1,500）。建議調整方向：

1. **`cwScaleFactor`**：2.0 → 1.5（減緩 VO/VI CWmin 被推高的速度，3→5→7→11→15 而非 3→6→12→15）
2. **`recoveryFactor`**：0.3 → 0.4~0.5（加快恢復到 default 的速度）
3. **差異化 BE/BK 的 mitigation 強度**：背景流（BK）不應與 BE 得到相同幅度的 AIFSN 降低

調整方式：修改 `simulations/scenarios/qad_edca.ini` 中的 `*.qadManager.*` 參數，不需重新編譯。

### 階段 2：完整實驗矩陣

需跑的配置組合（每個配置有多個 run，用 `./run.sh <config> <scenario> <run#> --cli` 批次執行）：

| 場景 | Config | 說明 |
|------|--------|------|
| Baseline | `Baseline_N5/N10/N15/N20` | 不同站台數的標準 EDCA |
| Baseline | `Baseline_LoadSweep` | 固定 N=10，不同 BE 負載 |
| QAD-EDCA | `QadEdca_N10/N20` | 對照 Baseline |
| QAD-EDCA | `QadEdca_ThresholdSweep` | Q_th × P_th 敏感度分析 |
| 高負載 | `HighLoad_Baseline/QadEdca` | 極端壓力測試 |
| Tuned Static | **待建立** `tuned_static.ini` | 見下方 |

### 階段 3：建立 Tuned Static EDCA 比較場景

參考 Ugwu et al. [2] Table 5 Case 1 的靜態配置（對高優先權最友好），建立 `simulations/scenarios/tuned_static.ini`：
- BE CWmin=15, CWmax=63
- VO CWmin=3, CWmax=7
- AIFSN 使用預設值
- 不啟用 QadEdcaManager

用途：展示即使選了最優的靜態參數，在負載變化時仍無法避免飢餓。

### 階段 4：結果分析與圖表

使用 `analysis/` 目錄下的 Python 腳本處理 `simulations/results/` 中的 SQLite 檔案，產出：
- 各 AC throughput 對比（bar chart）
- 延遲 CDF
- Jain's Fairness Index 隨時間變化
- AIFSN/CWmin 動態調整軌跡（從 vector 資料）
- 封包丟棄率對比

### 階段 5：期末報告與簡報

基於實驗數據更新 `docs/final-presentation.md` 和 `docs/final-presentation_zh.md`。

### 已知限制（需在報告中說明）

- **作用域為 AP 側**：目前只調整 AP 內部的 Edcaf，STA 端未被調整。真實 802.11 是透過 Beacon 的 EDCA Parameter Set IE 廣播給所有 STA。報告中需明確界定：「作用域為 AP 內部 downlink 調整，對應 AP 以 Beacon 通告 EDCA parameter 的模擬簡化」
- **cwMax 未被調整**：符合 proposal §3.3 設計，但未來可考慮擴充
