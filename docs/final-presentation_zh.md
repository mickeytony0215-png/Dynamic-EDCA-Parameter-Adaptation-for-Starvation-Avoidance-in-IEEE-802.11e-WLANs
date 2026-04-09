# 期末專案簡報
# IEEE 802.11 WLAN 中避免飢餓現象的動態 EDCA 參數自適應機制

> 時間：約 15 分鐘報告 + 5 分鐘 Q&A
> 狀態：🟢 已完成 / 🟡 待模擬數據補充 / 🔴 待實作

---

## 1. 簡介（Introduction）（~2 分鐘）🟢

### 投影片 1-1：標題頁
- 題目：Dynamic EDCA Parameter Adaptation for Starvation Avoidance in IEEE 802.11 WLANs
- 組員姓名 / 學號
- 課程名稱 / 日期

### 投影片 1-2：研究動機
- 現代 WLAN 同時承載語音、視訊、網頁、背景同步等多種流量
- EDCA 以靜態參數實現 QoS 差異化，但在高負載下造成低優先權流量飢餓
- 近年 Wi-Fi 6/7 引入新特性（MU-EDCA、MLO），EDCA 公平性問題持續存在
- 既有 DRL 方案效能佳但運算成本高，需要輕量級替代方案

### 投影片 1-3：研究目標
- 提出 QAD-EDCA（Queue-Aware Dynamic EDCA）演算法
- 在 AP 端即時監控佇列狀態，動態調整 EDCA 參數
- 目標：緩解飢餓、提升公平性、保障高優先權 QoS、低運算成本

---

## 2. 背景與問題定義（Background + Problem Definition）（~3 分鐘）🟢

### 投影片 2-1：EDCA 機制概述
- 四種存取類別：AC_VO > AC_VI > AC_BE > AC_BK
- 通道存取參數：AIFSN、CWmin/CWmax、TXOP limit
- 參數表：

| AC | CWmin | CWmax | AIFSN | TXOP |
|----|-------|-------|-------|------|
| AC_VO | 3 | 7 | 2 | 1.504 ms |
| AC_VI | 7 | 15 | 2 | 3.008 ms |
| AC_BE | 15 | 1023 | 3 | 0 |
| AC_BK | 15 | 1023 | 7 | 0 |

### 投影片 2-2：飢餓問題
- 圖示：高優先權 STA 比例 vs. AC_BE/AC_BK 吞吐量急劇下降
- Ugwu 等人 [2] 驗證：AIFSN 對 QoS 影響顯著大於 CW
- Lee 等人 [3]：802.11ac 中低優先權流量面臨嚴重飢餓

### 投影片 2-3：問題形式化
- 飢餓條件定義：

$$
\text{Starvation}(AC_i) \iff \left( \frac{Q_i}{Q_{cap}} > Q_{th} \right) \lor \left( P_{loss,i} > P_{th} \right)
$$

### 投影片 2-4：現有方案的不足

| 方案 | 限制 |
|------|------|
| SDMA [3] | 依賴多通道，不適用單通道場景 |
| OBSS QoS [4] | 僅處理跨 BSS 干擾，未解決 BSS 內部飢餓 |
| PDCF-DRL [6] | 運算複雜度高，需訓練收斂時間 |
| ReinWiFi [8] | 作用於應用層，非 MAC 層 |

- **研究缺口**：缺乏輕量級、MAC 層、即時佇列感知的飢餓迴避機制

---

## 3. 解決方案（Solution）（~4 分鐘）🟢

### 投影片 3-1：QAD-EDCA 架構圖

```
┌─────────────────────────────────┐
│       QAD-EDCA Manager (AP)     │
│                                 │
│  監控 ──→ 偵測 ──→ 調整         │
│   │         │        │          │
│  佇列/遺失  飢餓？   AIFSN      │
│  (每個AC)   是/否   CWmin       │
│                     TXOP        │
└────────────┬────────────────────┘
             │ 信標訊框 (Beacon)
    ┌────────┴────────┐
    ▼        ▼        ▼
  STA_1    STA_2    STA_N
```

### 投影片 3-2：三階段調整策略
1. **降低 AIFSN**（BE/BK）→ 縮短競爭前等待時間
2. **增加 CWmin**（VO/VI）→ 降低通道存取積極性
3. **縮減 TXOP**（VO/VI）→ 減少通道佔用時間

- 恢復機制：指數衰減 $P(t+1) = P(t) + \gamma \cdot (P_{default} - P(t))$

### 投影片 3-3：演算法虛擬碼

```
每隔 T_mon 秒在 AP 端執行：
  1. 測量 AC_BE、AC_BK 的佇列佔用率 Q_i 與封包遺失率 P_loss_i

  2. 若偵測到飢餓：
       AIFSN_BE/BK  ← max(AIFSN - Δ, 2)
       CWmin_VO/VI  ← min(CWmin × α, CWmin_BE_default)
       TXOP_VO/VI   ← max(TXOP × β, TXOP_min)

  3. 否則：
       指數衰減恢復至預設值

  4. 透過信標訊框廣播更新參數

  5. 若 VO 延遲 > 150ms 或 VI 延遲 > 300ms：
       部分回復調整（縮減 50%）
```

### 投影片 3-4：數學模型
- 通道存取機率：$\tau_i = \frac{2}{CWmin_i + 1}$
- 公平性指標（Jain Index）：$J(\mathbf{x}) = \frac{(\sum x_i)^2}{n \sum x_i^2}$
- 關鍵參數表：

| 參數 | 預設值 | 說明 |
|------|--------|------|
| $T_{mon}$ | 100 ms | 監控間隔 |
| $Q_{th}$ | 80% | 佇列佔用率閾值 |
| $P_{th}$ | 10% | 封包遺失率閾值 |
| $\Delta_{AIFS}$ | 1 | AIFSN 調整步長 |
| $\alpha_{CW}$ | 2.0 | CWmin 縮放因子 |
| $\beta_{TXOP}$ | 0.75 | TXOP 縮放因子 |
| $\gamma$ | 0.3 | 恢復因子 |

---

## 4. 分析與討論（Analysis and Discussion）（~3 分鐘）🟡

### 投影片 4-1：模擬環境
- OMNeT++ 6.1 + INET Framework 4.5
- 網路拓撲：1 AP + N 個 STA（N = 5, 10, 15, 20）
- 流量模型：VO (G.711 64kbps)、VI (1.024 Mbps)、BE (飽和)、BK (40.96 kbps)

### 投影片 4-2：飢餓現象展示（基準線）
<!-- 🟡 待模擬數據 -->
- 圖表：標準 EDCA 下各 AC 吞吐量 vs. 高優先權 STA 比例
- 預期：AC_BE/AC_BK 吞吐量在高優先權比例 >60% 時趨近於零

### 投影片 4-3：QAD-EDCA 效果
<!-- 🟡 待模擬數據 -->
- 圖表：QAD-EDCA vs. 標準 EDCA 的各 AC 吞吐量比較
- 圖表：Jain 公平性指數 vs. 高優先權 STA 比例
- 預期：公平性從 ~0.4 提升至 >0.8

### 投影片 4-4：參數敏感度分析
<!-- 🟡 待模擬數據 -->
- 圖表：不同 $Q_{th}$ 和 $P_{th}$ 組合下的效能
- 圖表：$T_{mon}$ 對反應速度 vs. 穩定性的影響
- 圖表：$\gamma$ 對震盪行為的影響

### 投影片 4-5：QoS 保障驗證
<!-- 🟡 待模擬數據 -->
- 圖表：調整過程中 AC_VO 延遲是否維持 <150 ms
- 圖表：調整過程中 AC_VI 延遲是否維持 <300 ms

---

## 5. 比較與展示（Comparison / Demo）（~3 分鐘）🟡

### 投影片 5-1：方案比較總表
<!-- 🟡 待模擬數據 -->

| 指標 | 標準 EDCA | SDMA [3] | PDCF-DRL [6] | QAD-EDCA |
|------|----------|----------|-------------|----------|
| BE/BK 吞吐量 | — | — | — | — |
| Jain Index | — | — | — | — |
| VO 延遲 | — | — | — | — |
| 運算複雜度 | O(1) | O(1) | O(DRL 訓練) | O(1) |
| 需要訓練 | 否 | 否 | 是 | 否 |

### 投影片 5-2：關鍵發現
<!-- 🟡 待模擬數據 -->
- QAD-EDCA vs. 標準 EDCA：飢餓緩解效果
- QAD-EDCA vs. PDCF-DRL：效能 vs. 運算成本的權衡
- QAD-EDCA 的適用場景與限制

### 投影片 5-3：即時展示（Demo）
<!-- 🔴 待實作 -->
- 使用 OMNeT++ Qtenv GUI 展示：
  1. 基準場景：觀察飢餓發生
  2. QAD-EDCA 場景：觀察參數動態調整過程
  3. 即時佇列佔用率與吞吐量變化

### 投影片 5-4：結論
- QAD-EDCA 以輕量級規則成功緩解 EDCA 飢餓問題
- 在保障 VO/VI QoS 前提下顯著提升公平性
- 無需訓練階段，適合資源受限的 AP 即時部署
- 未來展望：延伸至 Wi-Fi 7 MLO 環境、與 DRL 方案混合使用

---

## Q&A 準備（~5 分鐘）

### 預期問題與回答要點

**Q1：為什麼不直接用 DRL？**
- DRL 效能更好，但需要訓練時間和運算資源
- QAD-EDCA 定位為輕量級替代方案，適合即時部署
- 兩者可互補：QAD-EDCA 作為 DRL 收斂前的過渡機制

**Q2：監控間隔 100ms 會不會太慢？**
- 信標訊框間隔通常為 100ms，與之同步
- 過快的監控會增加運算負擔且可能導致震盪
- 敏感度分析會展示不同 T_mon 的影響

**Q3：如何確保不會過度調整導致 VO/VI QoS 下降？**
- 步驟 5 的 QoS 約束驗證機制
- 調整有上界（CWmin 不超過 BE 預設值、AIFSN 不低於 2）
- 部分回復機制（50% revert）作為安全閥

**Q4：與真實環境的差異？**
- 模擬使用理想通道模型，真實環境有衰落和干擾
- 信標訊框傳播延遲在模擬中為即時，真實環境有延遲
- 未來可結合 802.11ax TWT 進一步改善

---

## 參考文獻

[1] IEEE Standard 802.11-2020.
[2] G. O. Ugwu et al., "Effect of service differentiation on QoS in IEEE 802.11e EDCA," *J. Eng. Appl. Sci.*, 2022.
[3] J. Lee et al., "Starvation avoidance-based dynamic multichannel access for low priority traffics in 802.11ac," *Comput. Electr. Eng.*, 2020.
[4] Y. P. Tuan et al., "Improving QoS mechanisms for IEEE 802.11ax with OBSS," *Wireless Netw.*, 2023.
[5] "Intelligent Multi-link EDCA Optimization for Delay-Bounded QoS in Wi-Fi 7," arXiv:2509.25855, 2025.
[6] Z. Zuo et al., "PDCF-DRL: a contention window backoff scheme based on DRL," *J. Supercomput.*, 2025.
[7] X. Du et al., "Federated DRL-based intelligent channel access in dense Wi-Fi," arXiv:2409.01004, 2024.
[8] Q. Li et al., "ReinWiFi: Application-layer QoS optimization of WiFi networks with RL," arXiv:2405.03526, 2024.
[9] R. Jain et al., "A quantitative measure of fairness," DEC TR-301, 1984.
