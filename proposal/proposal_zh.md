# IEEE 802.11e WLAN 中避免飢餓現象的動態 EDCA 參數自適應機制

## 組員

| 姓名 | 學號 | 負責項目 |
|------|------|---------|
| （待填寫） | | |
| （待填寫） | | |

---

## 1. 簡介

IEEE 802.11e 修正案引入了增強型分散式通道存取（Enhanced Distributed Channel Access, EDCA）機制，為無線區域網路（WLAN）提供服務品質（QoS）差異化。EDCA 定義了四種存取類別（Access Category, AC）——語音（AC_VO）、視訊（AC_VI）、盡力而為（AC_BE）及背景（AC_BK）——每種類別分別配置不同的通道存取參數：仲裁幀間距編號（AIFSN）、最小與最大競爭視窗（CWmin、CWmax）以及傳輸機會限制（TXOP limit）。高優先權的 AC 被分配較積極的參數（較小的 CWmin、較短的 AIFS、較長的 TXOP），使其能更頻繁且更長時間地獲得通道存取機會。

儘管此差異化機制成功地優先處理了語音和視訊等延遲敏感型流量，但也引發了根本性的公平性問題。在高網路負載下，高優先權流量壟斷了通道存取，導致低優先權流量（BE 和 BK）的吞吐量嚴重下降——在極端情況下甚至完全飢餓。標準 EDCA 機制採用靜態、預先配置的參數，無論實際網路狀況如何都維持不變。這種僵化意味著一旦飢餓狀態發生，標準協定便無任何自適應機制來緩解。

飢餓問題並非僅是理論上的顧慮。在實際部署中，WLAN 同時承載多種流量類型：視訊會議、網頁瀏覽、電子郵件及背景同步。當語音和視訊流量消耗了不成比例的通道資源時，即使是基本的網頁瀏覽（AC_BE）也可能變得無法使用。這種退化違反了使用者的期望，並損害了網路對非即時應用的實用性。

本專案提出**佇列感知動態 EDCA（Queue-Aware Dynamic EDCA, QAD-EDCA）**——一種自適應演算法，透過在存取點（AP）端監控各 AC 的佇列佔用率及封包遺失率，動態調整 EDCA 參數，以在保障高優先權流量 QoS 需求的前提下，為低優先權流量提供最低頻寬保證。我們透過 OMNeT++ 搭配 INET Framework 進行大規模模擬評估，將本方案與標準 EDCA 及文獻中的既有動態調適方案進行比較。

---

## 2. 問題定義

### 2.1 飢餓條件

我們正式定義低優先權存取類別 $AC_i$（其中 $i \in \{BE, BK\}$）的飢餓條件如下：

$$
\text{Starvation}(AC_i) \iff \left( Q_i > Q_{th} \right) \lor \left( P_{loss,i} > P_{th} \right)
$$

其中 $Q_i$ 表示 $AC_i$ 的目前佇列長度，$Q_{th}$ 為佇列長度閾值，$P_{loss,i}$ 為 $AC_i$ 的封包遺失率，$P_{th}$ 為封包遺失率閾值。

飢餓發生於高優先權 AC（AC_VO、AC_VI）主宰通道存取，使得低優先權 AC 無法在可接受的時間範圍內成功傳輸訊框的情況。低優先權 AC 的佇列因溢出而導致封包丟棄及無限延遲。

### 2.2 靜態 EDCA 的局限性

標準 EDCA 依據 802.11e 規範分配固定參數：

| AC | CWmin | CWmax | AIFSN | TXOP limit |
|----|-------|-------|-------|------------|
| AC_VO | $(aCWmin+1)/4 - 1$ | $(aCWmin+1)/2 - 1$ | 2 | 1.504 ms |
| AC_VI | $(aCWmin+1)/2 - 1$ | $aCWmin$ | 2 | 3.008 ms |
| AC_BE | $aCWmin$ | $aCWmax$ | 3 | 0 |
| AC_BK | $aCWmin$ | $aCWmax$ | 7 | 0 |

這些參數在關聯時即確定，且在整個連線期間保持不變。該協定缺乏任何回饋機制來偵測低優先權流量是否正在遭受飢餓，或自適應地重新分配通道存取機會。隨著高優先權站台比例增加，AC 之間固定的參數差距將導致日益嚴重的不公平。

---

## 3. 提出的解決方案：QAD-EDCA

### 3.1 概述

佇列感知動態 EDCA（QAD-EDCA）作為集中式監控與控制器運行在存取點（AP）端。演算法定期取樣各 AC 的佇列狀態與遺失指標，一旦偵測到飢餓條件，便施加漸進式參數調整以重新平衡通道存取機會。調整後的參數透過信標訊框（beacon frame）傳播至所有關聯的站台（STA）。

### 3.2 演算法設計

QAD-EDCA 演算法採用三種互補的調整策略，依積極程度遞增順序施加：

1. **降低低優先權 AC 的 AIFS**：減少 AC_BE 和 AC_BK 的 AIFSN $\Delta_{AIFS}$，縮短其競爭前的等待時間。
2. **增加高優先權 AC 的 CWmin**：以倍率 $\alpha_{CW}$ 增加 AC_VO 和 AC_VI 的 CWmin，緩和其通道存取積極性。
3. **縮減高優先權 AC 的 TXOP 限制**：以倍率 $\beta_{TXOP}$ 縮減 AC_VO 和 AC_VI 的 TXOP 限制，減少每次通道佔用的持續時間。

當飢餓條件解除（佇列長度與遺失率回到閾值以下）時，參數以指數衰減函數逐步恢復至預設值，以避免震盪。

### 3.3 虛擬碼

```
演算法：QAD-EDCA 動態參數調整
輸入：監控間隔 T_mon、閾值 Q_th、P_th
      調整因子：delta_AIFS、alpha_CW、beta_TXOP
      恢復因子：gamma (0 < gamma < 1)

每隔 T_mon 秒在 AP 端執行：
  1. 對每個 AC ∈ {BE, BK}：
       測量 Q_i = AC_i 的佇列長度
       測量 P_loss_i = AC_i 的封包遺失率

  2. 若 (Q_BE > Q_th) 或 (P_loss_BE > P_th)
        或 (Q_BK > Q_th) 或 (P_loss_BK > P_th)：
       // 偵測到飢餓——施加調整
       a. AIFSN_BE = max(AIFSN_BE - delta_AIFS, 2)
          AIFSN_BK = max(AIFSN_BK - delta_AIFS, 2)
       b. CWmin_VO = min(CWmin_VO * alpha_CW, CWmin_default_BE)
          CWmin_VI = min(CWmin_VI * alpha_CW, CWmin_default_BE)
       c. TXOP_VO = max(TXOP_VO * beta_TXOP, TXOP_min)
          TXOP_VI = max(TXOP_VI * beta_TXOP, TXOP_min)

  3. 否則：
       // 未偵測到飢餓——向預設值恢復
       a. AIFSN_BE = AIFSN_BE + gamma * (AIFSN_default_BE - AIFSN_BE)
          AIFSN_BK = AIFSN_BK + gamma * (AIFSN_default_BK - AIFSN_BK)
       b. CWmin_VO = CWmin_VO + gamma * (CWmin_default_VO - CWmin_VO)
          CWmin_VI = CWmin_VI + gamma * (CWmin_default_VI - CWmin_VI)
       c. TXOP_VO = TXOP_VO + gamma * (TXOP_default_VO - TXOP_VO)
          TXOP_VI = TXOP_VI + gamma * (TXOP_default_VI - TXOP_VI)

  4. 透過信標訊框向所有 STA 廣播更新後的參數

  5. 驗證 QoS 限制：
       若 delay_VO > 150 ms 或 delay_VI > 300 ms：
         部分回復調整（將 delta 縮減 50%）
```

### 3.4 關鍵參數

| 參數 | 符號 | 預設值 | 說明 |
|------|------|--------|------|
| 監控間隔 | $T_{mon}$ | 100 ms | AP 檢查佇列狀態的頻率 |
| 佇列閾值 | $Q_{th}$ | 緩衝區大小的 80% | 觸發飢餓偵測 |
| 遺失率閾值 | $P_{th}$ | 10% | 觸發飢餓偵測 |
| AIFS 調整步長 | $\Delta_{AIFS}$ | 1 | 每次調整週期的 AIFSN 縮減量 |
| CW 縮放因子 | $\alpha_{CW}$ | 2.0 | CWmin 增加的倍率 |
| TXOP 縮放因子 | $\beta_{TXOP}$ | 0.75 | TXOP 縮減的倍率 |
| 恢復因子 | $\gamma$ | 0.3 | 向預設值的指數衰減係數 |

---

## 4. 模擬設計

### 4.1 模擬環境

我們使用 **OMNeT++ 6.1** 搭配 **INET Framework 4.5** 作為模擬平台。INET 透過 `Ieee80211Mac` 模組並啟用 `qosStation` 參數，提供了完整的 IEEE 802.11e EDCA 機制實作。

### 4.2 網路拓撲

模擬網路由一個運行在基礎架構基本服務集（BSS）模式的存取點（AP）組成，並有 $N$ 個關聯的無線站台（STA）。我們評估四種網路規模：$N \in \{5, 10, 15, 20\}$。

### 4.3 流量模型

| AC | 應用 | 封包大小 | 傳送間隔 | 資料速率 |
|----|------|---------|---------|---------|
| AC_VO | VoIP (G.711) | 160 bytes | 20 ms | 64 kbps |
| AC_VI | 視訊串流 | 1280 bytes | 10 ms | 1.024 Mbps |
| AC_BE | 大量傳輸（FTP/TCP 或飽和 UDP） | 1500 bytes | 可變 | 飽和 |
| AC_BK | 背景同步 | 512 bytes | 100 ms | 40.96 kbps |

### 4.4 實驗變數

1. **高優先權 STA 比例**：20%、40%、60%、80% 的 STA 產生 VO/VI 流量。
2. **整體網路負載**：輕載（$<30\%$ 容量）、中載（$30\text{--}60\%$）、重載（$60\text{--}90\%$）、飽和（$>90\%$）。
3. **QAD-EDCA 閾值參數**：掃描 $Q_{th} \in \{50\%, 70\%, 80\%, 90\%\}$ 和 $P_{th} \in \{5\%, 10\%, 15\%, 20\%\}$ 以評估敏感度。

### 4.5 效能指標

- **各 AC 吞吐量**（bits/s）
- **各 AC 平均延遲與延遲抖動**（秒）
- **各 AC 封包遺失率**（%）
- **Jain 公平性指數**（跨所有 AC）：$J = \frac{(\sum_{i=1}^{n} x_i)^2}{n \sum_{i=1}^{n} x_i^2}$
- **QoS 滿足度**：AC_VO 延遲 $< 150$ ms 且 AC_VI 延遲 $< 300$ ms

### 4.6 比較方案

1. **標準 EDCA**（基準線）：依 IEEE 802.11e 規範的固定預設參數。
2. **自適應 EDCA（Banchs 2010）**：基於分析模型的最佳 EDCA 參數配置 [1]。
3. **飢餓預測 EDCA（Engelstad 2005）**：具飢餓預測的延遲與吞吐量分析 [2]。
4. **QAD-EDCA**（本方案）：我們提出的佇列感知動態調適方案。

---

## 5. 專案計畫與時程

| 週次 | 期間 | 任務 | 交付物 |
|------|------|------|--------|
| 1--2 | 4/15 -- 4/28 | 環境建置；實作並驗證基準 EDCA 模擬；在高負載下重現標準 EDCA 飢餓現象 | 基準模擬結果；飢餓現象展示圖表 |
| 3--4 | 4/29 -- 5/12 | 在 OMNeT++/INET 中實作 QAD-EDCA 演算法；與 Edcaf 模組整合；單元測試 | 可運行的 QAD-EDCA 模組；初步比較結果 |
| 5--6 | 5/13 -- 5/26 | 執行完整實驗矩陣（N、負載、閾值）；收集吞吐量、延遲、遺失、公平性數據；實作文獻比較方案 | 完整模擬數據；分析腳本 |
| 7--8 | 5/27 -- 6/10 | 分析結果並產生圖表；撰寫期末報告；準備簡報投影片 | 期末報告（PDF）；簡報投影片 |

### 甘特圖

```
任務                          W1   W2   W3   W4   W5   W6   W7   W8
                             4/15 4/22 4/29 5/06 5/13 5/20 5/27 6/03
環境建置 & 基準模擬           ████ ████
QAD-EDCA 實作                          ████ ████
實驗 & 數據收集                                ████ ████
文獻比較                                       ████ ████
分析 & 圖表                                              ████ ████
報告撰寫                                            ████ ████ ████
簡報準備                                                       ████
                                                         截止日：6/10
```

---

## 6. 組員分工

| 角色 | 成員 | 任務 |
|------|------|------|
| 演算法設計與實作 | （待填寫） | QAD-EDCA 演算法設計；OMNeT++/INET 中的 C++ 實作 |
| 模擬與實驗 | （待填寫） | 網路拓撲建置；流量配置；執行實驗 |
| 分析與視覺化 | （待填寫） | 結果解析；統計分析；圖表產生 |
| 報告與文獻回顧 | （待填寫） | 文獻調查；提案與期末報告撰寫 |

*備註：組員可跨角色分擔工作。*

---

## 7. 參考文獻

[1] A. Banchs and X. Perez-Costa, "Providing throughput guarantees in IEEE 802.11e wireless LANs," in *Proc. IEEE Wireless Communications and Networking Conference (WCNC)*, 2002; Extended analysis in A. Banchs, A. Azcorra, C. Garcia, and R. Cuevas, "Applications and challenges of the 802.11e EDCA mechanism: a survey," *IEEE Communications Surveys & Tutorials*, vol. 12, no. 1, 2010.

[2] P. E. Engelstad, O. N. Osterbo, "Delay and throughput analysis of IEEE 802.11e EDCA with starvation prediction," in *Proc. IEEE Conference on Local Computer Networks (LCN)*, 2005.

[3] I. Inan, F. Keceli, and E. Ayanoglu, "Fairness Provision in the IEEE 802.11e Infrastructure Basic Service Set," arXiv preprint arXiv:0704.1842, 2007.

[4] J. Lee, J. Choi, and S. Bahk, "Starvation avoidance-based dynamic multichannel access for low priority traffics in 802.11ac," *Computers & Electrical Engineering*, vol. 82, 2020.

[5] IEEE Standard 802.11e-2005, "IEEE Standard for Information technology--Local and metropolitan area networks--Specific requirements--Part 11: Wireless LAN Medium Access Control (MAC) and Physical Layer (PHY) Specifications, Amendment 8: Medium Access Control (MAC) Quality of Service Enhancements," IEEE, 2005.

[6] R. Jain, D. Chiu, and W. Hawe, "A quantitative measure of fairness and discrimination for resource allocation in shared computer systems," *DEC Research Report TR-301*, 1984.

[7] IEEE Standard 802.11-2020, "IEEE Standard for Information Technology--Telecommunications and Information Exchange between Systems--Local and Metropolitan Area Networks--Specific Requirements--Part 11: Wireless LAN Medium Access Control (MAC) and Physical Layer (PHY) Specifications," IEEE, 2020.
