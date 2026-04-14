# QAD-EDCA 程式碼審查報告

- **審查日期**：2026-04-14（第一輪）／ 2026-04-14（第二輪複審）
- **狀態**：第一輪提出的 1 Critical + 2 中等 + 6 Low 共 9 項全部修復完畢，已重新編譯 `libedcafairness.so`
- **審查範圍**：`docs/dev-report-2026-04-14.md` 所列的新增/修改檔案
  - INET 整合子類鏈：`QadEdcaf.{h,cc,ned}`、`QadEdca.{h,cc,ned}`、`QadHcf.ned`、`QadTxopProcedure.{h,cc,ned}`
  - 核心演算法：`QadEdcaManager.{h,cc,ned}`
  - 模擬場景：`network.ned`、`omnetpp.ini`、`scenarios/{baseline,high_load,qad_edca}.ini`
  - 建置與執行：`Makefile`、`run.sh`、`package.ned`、`HOW_TO_RUN.md`
- **參考來源**：`~/simulation/inet4.5/src/inet/linklayer/ieee80211/mac/channelaccess/Edcaf.{h,cc}`、`.../originator/TxopProcedure.{h,cc}`、`inet/common/Simsignals.h`

---

## 整體評價

**設計巧思值得肯定**：以「固定型別的父模組」→「可覆蓋型別的祖父模組」反推出 `Hcf → Edca → Edcaf → TxopProcedure` 的 NED 複製 + C++ 子類鏈，是繞過 INET 4.5 `typename` 限制的正確解法；直接繼承後寫 protected 成員（`cwMin/cwMax/cw/ifs/eifs/limit`）也優於硬改 INET 原始碼。

但 `QadEdcaManager` 的執行期邏輯存在 **1 個關鍵 bug + 2 個中等 bug**，建議在批次實驗前修復，否則初步數據（尤其 Jain's Fairness 驟降至 0.409）的解讀會失真。

---

## 關鍵問題（必修）

### [CRITICAL] `packetDroppedSignal` 雙重訂閱導致丟包數雙倍計算

**位置**：`src/QadEdcaManager.cc:77`、`:82`

```cpp
hcfModule->subscribe(packetDroppedSignal, this);              // 在 hcf
for (int i = 0; i < 4; i++)
    queueModules[i]->subscribe(packetDroppedSignal, this);    // 在 pendingQueue
```

**問題**：OMNeT++ signal 會往上游傳播，同一個 listener 在祖先與子孫都訂閱同一信號時，每次 emit 會**被遞送兩次**。`pendingQueue` 是 `hcf` 的子孫，所以佇列溢出丟包會同時觸發：

1. `queueModules[i]` 的 listener → `findAcForQueue(source)` 命中 → `dropCount[ac]++` → return
2. 信號傳播到 `hcfModule`，同一個 listener 再次收到（source 仍為 `queueModules[i]`）→ 第一個 branch 又命中 → `dropCount[ac]++` 再加一次

**後果**：

- `getPacketLossRate()` 被**高估兩倍**（尤其在純佇列溢出的情況）
- `detectStarvation()` 會過早觸發（`lossThreshold=0.1` 實際上等於 0.05）
- 首輪實驗 baseline 的「封包丟棄 13,044」實際可能只有一半，「-100%」的改善幅度是對錯誤基準的比較
- `enqueueCount` 只訂閱一次（pendingQueue），沒有雙計，所以 `rate = dropCount/enqueueCount` 會呈現不自然的高比例

**修法（擇一）**：

- **方案 A（推薦）**：只訂閱 `hcfModule`，在 `receiveSignal` 中先用 `findAcForQueue(source)` 判斷是否來自某個 `queueModule`，再處理重傳丟棄分支。祖先訂閱已能收到子孫信號。
- **方案 B**：保留兩個訂閱點，但在 hcf branch 中去重（當 `source` 命中 `queueModules[i]` 時直接 return 不計數）。反直覺，易誤修，不建議。

修完後請重跑 `Baseline_N10` 與 `QadEdca_N10`，重新對比真實 drop count。

---

### [HIGH] `applyRecovery()` 整數截斷讓恢復卡住

**位置**：`src/QadEdcaManager.cc:281-294`

```cpp
currentParams[i].aifsn += (int)(recoveryFactor
    * (defaultParams[i].aifsn - currentParams[i].aifsn));

currentParams[i].cwMin += (int)(recoveryFactor
    * (defaultParams[i].cwMin - currentParams[i].cwMin));
```

**問題**：`recoveryFactor = 0.3`。當差值很小：

- 差值 = 1：`(int)(0.3 * 1) = 0`，永遠不動
- 差值 = 3：`(int)(0.9) = 0`，永遠不動
- 差值 = 4：`(int)(1.2) = 1`，跳到差值 3 → 卡住

只有 `txopLimit`（`simtime_t`，浮點）恢復邏輯能正常運作。

**後果**：觸發一次 starvation 後，AIFSN 會永久停在調降後的值，直到模擬結束。這會扭曲「動態恢復」的論點，並間接劣化 Jain's Fairness Index（高優先權長期被壓抑無法回彈）。

**修法**：把 `currentParams` 的整數欄位內部儲存為 `double`，僅在送給 `setEdcaParameters()` 時才 `std::round` 成整數。這樣小差值可以透過浮點累加器逐步逼近 default，避免被反覆截斷。簡化版：

```cpp
// 在 QadEdcaParamsDouble 結構體中累積
doubleParams[i].aifsn += recoveryFactor * (defaultParams[i].aifsn - doubleParams[i].aifsn);
currentParams[i].aifsn = (int)std::round(doubleParams[i].aifsn);
```

---

### [MEDIUM] `applyParameters()` 每週期無條件呼叫 → 強制 `cw = cwMin`

**位置**：`src/QadEdcaf.h:22-31` 配合 `src/QadEdcaManager.cc:355-370`、`:230`

```cpp
// QadEdcaf::setEdcaParameters
cwMin = newCwMin;
cwMax = newCwMax;
cw = cwMin;        // ← 每次都會把 cw 拉回 cwMin
```

```cpp
// QadEdcaManager::monitorAndAdjust
...
applyParameters();  // 每 monitorInterval 都呼叫，不論值是否改變
```

**問題**：Manager 在 `monitorAndAdjust()` 結尾**無條件**呼叫 `applyParameters()`，即使 `currentParams` 與上輪完全相同。於是每 100 ms 就把每個 AC 的 `cw` 從目前值（可能是碰撞後 `incrementCw()` 放大到的值）強制拉回 `cwMin`，相當於**每 100 ms 清除所有 AC 的指數退避狀態**。

參考 `Edcaf.cc:94-99`（`incrementCw`）與 `:102-106`（`resetCw`）：標準行為僅在成功傳輸或達重傳上限時才重置 `cw`。Manager 的無條件覆寫違反此語意。

**後果**：

- 打破 802.11 標準「碰撞後指數退避」的正常語意
- AC_VO/VI 在高負載下反而更容易碰撞（退避沒機會擴張）
- 可能是初步數據 Jain's Fairness 0.686 → 0.409 的重要來源之一

**修法**：

1. 只在值實際改變時才呼叫 `setEdcaParameters()`（維護 `prevParams[4]` 做比對）
2. 即使改變，也只在 `newCwMin > cw`（需要擴大退避）時才覆寫 `cw`，否則保留目前進行中的 backoff：

```cpp
void setEdcaParameters(int newCwMin, int newCwMax, int newAifsn) {
    cwMin = newCwMin;
    cwMax = newCwMax;
    if (cw < cwMin) cw = cwMin;   // 只向上夾
    simtime_t aifs = sifs + newAifsn * slotTime;
    ifs = aifs;
    eifs = sifs + aifs + modeSet->getSlowestMandatoryMode()->getDuration(LENGTH_ACK);
}
```

---

## 次要問題

### [LOW] Getter 帶副作用（reset）且非對稱

**位置**：`src/QadEdcaManager.cc:334-353`

`getPacketLossRate()` 在讀取後重置 `dropCount[ac]`、`enqueueCount[ac]`，`getAverageDelay()` 類似。問題：

- `detectStarvation()` 只呼叫 BE/BK 的 `getPacketLossRate()` → **VO/VI 的計數器永遠不會重置**（無界累積）
- `checkQosConstraints()` 只呼叫 VO/VI 的 `getAverageDelay()` → **BE/BK 的 delay 計數器永遠不會重置**
- 30 秒模擬還沒事，但批次實驗若拉長或 repeat 數變多，會有溢出與統計偏差的隱性風險

**修法**：拆出一個顯式的 `resetIntervalCounters()`，在 `monitorAndAdjust()` 尾端一次性重置所有 AC；getter 改為純讀取。

---

### [LOW] `QadEdca` C++ 子類與 NED `@class` 不一致

**位置**：`src/QadEdca.ned:28`

```
@class(inet::ieee80211::Edca);   // ← 指向原始類，而非 QadEdca
```

但 `QadEdca.h/cc` 定義了 `class QadEdca : public Edcaf` 並 `Define_Module(QadEdca)`。兩者不矛盾（NED 贏，OMNeT++ 會實例化 `inet::ieee80211::Edca`），但 C++ 類是**死碼**，且會誤導後續接手者以為有覆寫行為。

**建議**：

- 若未來不會覆寫 Edca 行為：刪掉 `QadEdca.h/cc`，保留 NED 即可
- 若打算覆寫：把 NED 的 `@class(QadEdca)` 改對，並確認 Makefile 中 `OBJS` 有包含

---

### [LOW] `dev-report` 把 signal-based delay 稱為「MAC 層延遲」

**位置**：`docs/dev-report-2026-04-14.md:52-53`

`packet->getCreationTime()` 傳回的是封包物件**最初建構**的模擬時間（通常在 STA 端應用層），不是封包進 AP MAC 的時間。`simTime() - getCreationTime()` 實際上是 **end-to-end delay**（app→MAC delivered），不是 MAC-only。

對 QoS 安全閥來說其實**反而正確**（VO 150 ms 是端對端 bound），只是文件敘述需要修正避免未來混淆。

---

### [LOW] `omnetpp.ini` 在 QoS 模式下仍設定 `dcf` 參數

**位置**：`simulations/omnetpp.ini:30-31`

```ini
*.*.wlan[*].mac.dcf.channelAccess.cwMin = -1
*.*.wlan[*].mac.dcf.channelAccess.cwMax = -1
```

`qosStation = true` 時 `dcf` 子模組不存在，這兩行會在啟動時產生「unused parameter」警告。對功能無影響，但雜訊干擾 log 可讀性。建議刪除。

---

### [LOW] `~QadEdcaManager()` 沒做 unsubscribe

**位置**：`src/QadEdcaManager.cc:17-20`

`finish()` 有 unsubscribe，但若模擬因例外中止，`finish()` 不保證呼叫。析構時 `cListener` 仍然掛在別的模組上 → 潛在 UB。

**建議**：抽一個 `unsubscribeAll()` helper，在 destructor 與 `finish()` 共用，並以 flag 避免重複呼叫。

---

## 架構層次的觀察（非 bug，但值得討論）

### 只調整 AP 側 Edcaf 的作用域限制

Manager 透過 `ap.wlan[0].mac.hcf.edca.edcaf[i]` 取得的是 **AP 自身**的下行 Edcaf。在目前拓撲（STA → AP → server，AP 作為轉發中繼）中，這個作用域**確實**能影響 AP 端的下行流（AP→server），並間接減輕頻道競爭壓力，但：

- **STA 端上行的 Edcaf 並未被調整**
- 真實 802.11 的做法是 AP 透過 Beacon 的 EDCA Parameter Set IE 廣播給所有 STA，STA 再更新自己的 Edcaf
- 初步數據的 BE throughput +180% 主要源自 AP 下行改善；論文裡若要聲稱這是「整體飢餓消除」需要明確界定作用域

**建議**（不阻塞當前開發）：

- 在 proposal / dev-report 明確寫清楚「作用域為 AP 內部 downlink 調整，對應論文中 AP 以 Beacon 通告 EDCA parameter 的模擬簡化」
- 或增加 STA-side 的 QadEdcaf（Manager 訂閱每顆 STA 的 queue/edcaf）— 後續選項

---

### Jain's Fairness 指數下降（0.686 → 0.409）的可能成因

在「減少飢餓」的脈絡下，這個跌幅是反直覺的。結合前述 bug：

1. **Loss rate 雙計數** → 頻繁誤觸發 starvation → 過度調整
2. **Recovery 卡在截斷點** → 調整完後無法回復 → 高優先權持續被壓
3. **`cw` 每 100 ms 重置** → 退避狀態被抹平 → 碰撞頻率改變

修好 1/2/3 後再觀察該指數，若仍偏低才考慮：

- **差異化對待 BE / BK**：背景流本來就不該跟 BE 拿一樣的 boost
- **`cwScaleFactor = 2.0` 太激進**：VO cwMin 從 3 → 6 → 12 → 15 (cap)，第三次觸發就封頂。建議 1.5
- **`recoveryFactor = 0.3`**：修好截斷 bug 後可更積極（0.4–0.5）

---

## 驗證過的假設（供參考）

審查過程中對照了 INET 原始碼確認以下前提成立：

| 項目 | 驗證來源 |
|------|----------|
| `Edcaf::{cwMin, cwMax, cw, ifs, eifs, sifs, slotTime}` 為 protected | `Edcaf.h:51-59` |
| `ModeSetListener::modeSet` 為 protected（子類可存取） | `ModeSetListener.h:19` |
| `TxopProcedure::limit` 為 protected | `TxopProcedure.h:35` |
| `Edcaf::pendingQueue` 與 `txopProcedure` 在 `INITSTAGE_LOCAL` 已快取 | `Edcaf.cc:31-40` |
| `calculateTimingParameters()` 會從 NED 重讀 `cwMin/cwMax`，故不能直接呼叫（會覆蓋自訂值） | `Edcaf.cc:71-89` |
| `QadEdcaf::setEdcaParameters()` 的 IFS 計算公式與 `calculateTimingParameters()` 完全一致 | 對照一致 |
| `packetDroppedSignal` / `packetPushedInSignal` / `packetSentToPeerSignal` 是全域 signal | `Simsignals.h:94, 102, 109` |

---

## 快速結論

| 層面 | 評分 | 備註 |
|-----|------|------|
| NED 子類鏈設計 | 優 | 巧妙且最小化侵入 INET 原始碼 |
| C++ 子類實作 | 可 | 3 個 bug 需修 |
| 信號訂閱邏輯 | 需修 | 雙計數是關鍵錯誤 |
| 恢復機制正確性 | 需修 | 整數截斷 |
| 配置檔 / Makefile | 良 | 小瑕疵可忽略 |
| 實驗結果可信度 | 待重測 | 建議修完 bug 重跑 baseline 對照 |

---

## 建議行動順序

1. **修 Critical 雙計數**（訂閱改為只在 `hcf`，用 `source` 判別 AC）→ 重跑 `Baseline_N10` + `QadEdca_N10` 看真實 drop count
2. **修 Recovery 截斷**（整數欄位改用 `double` 累加器）→ 觀察 AIFSN 是否真正回到 default
3. **修 `cw` 重置條件**（只在值改變時 apply，且只在需要擴大時覆寫 `cw`）→ 觀察 Jain 指數
4. 修完再 tuning `cwScaleFactor / recoveryFactor / monitorInterval`
5. 之後才做 N=5/15/20 批次與 Tuned Static EDCA 比較實驗
6. 最後處理 Low-severity 清理項目（死碼、getter 副作用、析構清理、ini 警告）

---

# 第二輪複審（修復後驗證）

**複審日期**：2026-04-14
**驗證結論**：第一輪提出的三個必修問題與六個 Low-severity 問題**全部修復完畢**，程式碼品質顯著提升，可以進入重測與批次實驗階段。

---

## 逐項驗證

### [CRITICAL] 雙重訂閱 → 已修復

**位置**：`src/QadEdcaManager.cc:67-79`

```cpp
// 只在 hcf 訂閱 packetDroppedSignal（利用 signal 上冒特性收到所有子孫丟包）
hcfModule->subscribe(packetDroppedSignal, this);

for (int i = 0; i < 4; i++)
    queueModules[i]->subscribe(packetPushedInSignal, this);

for (int i = 0; i < 4; i++)
    edcafModules[i]->subscribe(packetSentToPeerSignal, this);
```

`receiveSignal` 中也改為先用 `findAcForQueue(source)` 辨識來源是否為某個 `pendingQueue`，命中就是佇列溢出；否則才檢查 `source == hcfModule` 處理重傳丟包分支。邏輯清晰且無重複計數。

---

### [HIGH] 整數截斷 → 已修復

**位置**：`src/QadEdcaManager.h:56-61`、`src/QadEdcaManager.cc:281-301`

引入 `smoothParams[4]`（結構體 `EdcaParamsDouble { double cwMin, aifsn }`）作為浮點累加器。`applyRecovery`、`applyStarvationMitigation`、`revertPartialAdjustment` 都在 double 空間運算，只在指定給 `currentParams` 時才 `std::round` 成整數。`<cmath>` 也正確 include 到 header。

手算驗證（`AC_BE.aifsn` 從 mitigation 後的 2.0 恢復到 default 3.0，γ=0.3）：

| cycle | smooth | round |
|-------|--------|-------|
| 0 | 2.000 | 2 |
| 1 | 2.300 | 2 |
| 2 | 2.510 | 3 |
| 3 | 2.657 | 3 |
| 4 | 2.760 | 3 |

不再卡住，AIFSN 實際會在約 2 個週期內回升到 3。

---

### [MEDIUM] applyParameters 無條件 + cw 重置 → 已修復

**Part 1：QadEdcaf 只向上夾 cw**（`src/QadEdcaf.h:22-31`）

```cpp
void setEdcaParameters(int newCwMin, int newCwMax, int newAifsn) {
    cwMin = newCwMin;
    cwMax = newCwMax;
    if (cw < cwMin) cw = cwMin;  // only clamp up, preserve backoff state
    simtime_t aifs = sifs + newAifsn * slotTime;
    ifs = aifs;
    eifs = sifs + aifs + modeSet->getSlowestMandatoryMode()->getDuration(LENGTH_ACK);
}
```

只在必要時向上夾 `cw`，保留碰撞後 `incrementCw()` 產生的退避狀態，符合 802.11 退避語意。

**Part 2：applyParameters 有變才套用**（`src/QadEdcaManager.cc:360-383`）

```cpp
if (currentParams[i].cwMin == prevAppliedParams[i].cwMin &&
    currentParams[i].cwMax == prevAppliedParams[i].cwMax &&
    currentParams[i].aifsn == prevAppliedParams[i].aifsn &&
    currentParams[i].txopLimit == prevAppliedParams[i].txopLimit)
    continue;
...
prevAppliedParams[i] = currentParams[i];
```

首輪 `prevAppliedParams[i] = {-1, -1, -1, SIMTIME_ZERO}` 確保第一次必套用。

---

### Low-severity 項目全部處理

| 項目 | 狀態 | 位置 |
|------|------|------|
| Getter 副作用 | 拆出 `resetIntervalCounters()`，在 `monitorAndAdjust` 末端統一重置所有 4 個 AC 的計數器；getters 改為純讀取 | `QadEdcaManager.cc:229-230, 341-358, 389-397` |
| `QadEdca` 死碼 | `QadEdca.h/.cc` 已刪除；`Makefile` 已用 `opp_makemake` 重新產生（`OBJS` 只剩 3 個目標檔）；`libedcafairness.so` 已於今天 16:39 重新編譯 | 檔案層 |
| `omnetpp.ini` dcf 警告 | 兩行 `dcf.channelAccess.cwMin/cwMax = -1` 已刪除 | `omnetpp.ini:28-29` |
| 析構函式清理 | 新增 `unsubscribeFromSignals()` helper 與 `subscribedToSignals` 旗標，destructor 與 `finish()` 都呼叫它且避免重複 unsubscribe | `QadEdcaManager.cc:17-21, 403-423` |

---

## 第二輪新觀察（非 bug，可選擇性處理）

1. **`cwMax` 未被調整**：整套邏輯只動 `cwMin`（符合 proposal §3.3 設計），`currentParams[i].cwMax` 永遠等於 `defaultParams[i].cwMax`。`applyParameters` 的比較式保留此欄比對是無害的，但可在未來擴充時留意。

2. **starvation 持續觸發時的單調推進**：當 BE 持續飢餓，`applyStarvationMitigation` 每 100 ms 呼叫一次，`smoothParams[BE].aifsn` 會持續被減 `aifsStep` 直到撞到 `minAifsn`；`smoothParams[VO].cwMin` 則持續被乘 `cwScaleFactor`（2.0）直到撞到 `maxCw`。兩者都有硬上下界不會失控，但意味著「一次觸發就 3 個週期內打到上/下界」，實際 mitigation 是階段式推進而非一次到位。這是設計選擇，請確認與 proposal §3.3 的語意一致（或改成累加式）。

3. **`cwMax` 向下夾**：QadEdcaf 只有 `if (cw < cwMin) cw = cwMin;`，沒有 `if (cw > cwMax) cw = cwMax;`。因為目前永遠不會動 cwMax 所以不是問題，但若未來擴充可加上對稱處理。

4. **dev-report 的延遲敘述**：原本被標記為 Low 的「MAC 層延遲」措辭還沒改，建議在下次更新時校正為「端對端 MAC-deliverable delay」或類似說法。不影響程式正確性。

---

## 建議下一步行動

1. **立即重跑**：`Baseline_N10` + `QadEdca_N10`（各 run 全掃），對比修復前的初步數據，特別觀察：
   - 真實 packet drop count（不再雙倍計算）
   - Jain's Fairness Index（應該從 0.409 往上回）
   - AIFSN 時序曲線（應該能看到回復到 default 的軌跡）

2. **如果 Jain's Fairness 仍不理想**，再調整：
   - `cwScaleFactor`：2.0 → 1.5（減緩 VO/VI 受壓的斜率）
   - `recoveryFactor`：0.3 → 0.4（稍加快回復）
   - 視情況差異化 BE / BK 的 mitigation 強度

3. **然後**才進批次實驗矩陣（N=5/15/20、不同 VO/VI 比例、與 Tuned Static EDCA 比較）。

---

## 第二輪質量總評

| 層面 | 第一輪 | 第二輪 | 變化 |
|-----|--------|--------|------|
| NED 子類鏈設計 | 優 | 優 | — |
| C++ 子類實作 | 可 | 良 | ↑ |
| 信號訂閱邏輯 | 需修 | 優 | ↑↑ |
| 恢復機制正確性 | 需修 | 良 | ↑↑ |
| 配置檔 / Makefile | 良 | 乾淨 | ↑ |
| 實驗結果可信度 | 待重測 | 可重測 | ↑↑ |

修復的品質很高：不只消除了 bug，`smoothParams` 浮點累加器的設計還讓恢復曲線變得平滑可預測；`prevAppliedParams` 比較避免了不必要的 MAC 呼叫；`unsubscribeFromSignals` 用旗標保護防止重複，是教科書級的清理模式。可以放心進入實驗階段。
