# IEEE 802.11 WLAN 中避免飢餓現象的動態 EDCA 參數自適應機制

## 組員

| 姓名 | 學號 | 負責項目 |
|------|------|---------|
| （待填寫） | | |
| （待填寫） | | |

---

## 1. Background（背景）

### 1.1 EDCA 機制與 QoS 差異化

IEEE 802.11 標準中的增強型分散式通道存取（Enhanced Distributed Channel Access, EDCA）機制為無線區域網路提供了服務品質（QoS）差異化能力。EDCA 將流量分為四種存取類別（Access Category, AC）——語音（AC_VO）、視訊（AC_VI）、盡力而為（AC_BE）及背景（AC_BK），並為每種類別分配不同的通道存取參數：仲裁幀間距編號（AIFSN）、競爭視窗（CWmin/CWmax）及傳輸機會限制（TXOP limit）[1]。

然而，近年研究持續揭示 EDCA 靜態參數配置的根本缺陷。Ugwu 等人 [2] 透過 MATLAB 模擬系統性地分析了 EDCA 中服務差異化對 QoS 的影響，證實高優先權流量在飽和狀態下會嚴重侵佔低優先權流量的通道資源，且 AIFSN 對 QoS 的影響顯著大於 CW。Lee 等人 [3] 在 IEEE 802.11ac 系統中觀察到，EDCA 的優先權機制使低優先權流量面臨嚴重飢餓，並提出基於動態多通道存取的飢餓迴避方法（SDMA）。

### 1.2 從 Wi-Fi 6 到 Wi-Fi 7 的 EDCA 演進

隨著 IEEE 802.11ax（Wi-Fi 6）的推出，EDCA 機制延伸至多使用者場景（MU-EDCA），引入了觸發幀（Trigger Frame）和目標喚醒時間（TWT）等新特性 [10]。Tuan 等人 [4] 針對 802.11ax 環境中重疊基本服務集（OBSS）問題，提出降低干擾 AP 傳輸功率並延長低 QoS 站台 TXOP 限制的機制，在 128 kbits/s 資料到達率下將受干擾站台的平均下行傳輸延遲降低了 21.4%。

IEEE 802.11be（Wi-Fi 7）進一步引入多鏈路操作（Multi-Link Operation, MLO），為 EDCA 帶來跨鏈路流量管理的新挑戰。最新研究 [5] 指出，靜態 EDCA 參數在 MLO 環境中無法保證嚴格的延遲上界，並提出基於遺傳演算法的 MLO EDCA QoS 最佳化方案。

### 1.3 機器學習驅動的 EDCA 最佳化

近年來，深度強化學習（DRL）技術被廣泛應用於 EDCA 參數的動態調整。Zuo 等人 [6] 提出 PDCF-DRL 方案，將 DRL 整合至 EDCA 的競爭視窗退避機制中，在 20–120 個站台的場景下，正規化吞吐量維持在 76% 以上、碰撞率控制在 18% 以下，顯著優於傳統 EDCA（吞吐量 13%–67%、碰撞率 29%–85%）。Du 等人 [7] 結合聯邦學習（FL）與深度確定性策略梯度（DDPG）演算法，提出適用於密集 Wi-Fi 部署的智慧通道存取機制，在靜態場景中降低 MAC 延遲 7.96%–25.24%。Li 等人 [8] 提出 ReinWiFi 框架，利用強化學習在應用層最佳化 Wi-Fi 網路的 QoS，在有未知干擾的商用環境中顯著優於 EDCA 機制。

儘管 DRL 方法展現了出色的效能，其高運算複雜度和訓練收斂時間限制了在資源受限設備上的即時部署。本專案探索一種輕量級、基於規則的自適應方案，以較低的運算成本達到有效的飢餓迴避。

---

## 2. Problem Definition（問題定義）

### 2.1 飢餓條件的形式化定義

我們正式定義低優先權存取類別 $AC_i$（其中 $i \in \{BE, BK\}$）的飢餓條件如下：

$$
\text{Starvation}(AC_i) \iff \left( \frac{Q_i}{Q_{cap}} > Q_{th} \right) \lor \left( P_{loss,i} > P_{th} \right)
$$

其中：
- $Q_i$：$AC_i$ 的目前佇列長度
- $Q_{cap}$：佇列容量
- $Q_{th}$：佇列佔用率閾值（預設 80%）
- $P_{loss,i}$：$AC_i$ 在監控區間內的封包遺失率
- $P_{th}$：封包遺失率閾值（預設 10%）

飢餓發生於高優先權 AC（AC_VO、AC_VI）主宰通道存取，使得低優先權 AC 無法在可接受的時間範圍內成功傳輸訊框的情況。

### 2.2 靜態 EDCA 的局限性

標準 EDCA 依據 IEEE 802.11-2020 [1] 規範分配固定參數：

| AC | CWmin | CWmax | AIFSN | TXOP limit |
|----|-------|-------|-------|------------|
| AC_VO | $(aCWmin+1)/4 - 1$ | $(aCWmin+1)/2 - 1$ | 2 | 1.504 ms |
| AC_VI | $(aCWmin+1)/2 - 1$ | $aCWmin$ | 2 | 3.008 ms |
| AC_BE | $aCWmin$ | $aCWmax$ | 3 | 0 |
| AC_BK | $aCWmin$ | $aCWmax$ | 7 | 0 |

如 Ugwu 等人 [2] 所驗證，這些靜態參數在飽和負載下導致低優先權流量的封包遺失率急劇上升，且 EDCA 協定缺乏任何回饋機制來偵測或緩解飢餓狀態。

### 2.3 現有方案的不足

| 方案類別 | 代表文獻 | 主要限制 |
|----------|---------|---------|
| 動態多通道存取 | Lee 等人 [3] | 依賴 802.11ac 通道綁定，不直接適用於單通道 BSS 場景 |
| OBSS QoS 改善 | Tuan 等人 [4] | 聚焦於跨 BSS 干擾，未處理單一 BSS 內的 AC 間飢餓 |
| DRL-based 方案 | Zuo 等人 [6]、Du 等人 [7] | 運算複雜度高，訓練收斂慢，不適合資源受限的 AP |
| 應用層最佳化 | Li 等人 [8] | 作用於應用層排程，未直接調整 MAC 層 EDCA 參數 |

**研究缺口**：缺乏一種輕量級、在 MAC 層直接運作、能即時感知佇列狀態並動態調整 EDCA 參數的飢餓迴避機制。

---

## 3. 提出的解決方案：QAD-EDCA

### 3.1 概述

佇列感知動態 EDCA（Queue-Aware Dynamic EDCA, QAD-EDCA）作為集中式監控與控制器運行在存取點（AP）端。演算法定期取樣各 AC 的佇列狀態與遺失指標，一旦偵測到飢餓條件，便施加漸進式參數調整以重新平衡通道存取機會。調整後的參數透過信標訊框（beacon frame）傳播至所有關聯的站台（STA）。

### 3.2 演算法設計

QAD-EDCA 演算法採用三種互補的調整策略，依積極程度遞增順序施加：

1. **降低低優先權 AC 的 AIFS**：減少 AC_BE 和 AC_BK 的 AIFSN $\Delta_{AIFS}$，縮短其競爭前的等待時間。
2. **增加高優先權 AC 的 CWmin**：以倍率 $\alpha_{CW}$ 增加 AC_VO 和 AC_VI 的 CWmin，緩和其通道存取積極性。
3. **縮減高優先權 AC 的 TXOP 限制**：以倍率 $\beta_{TXOP}$ 縮減 AC_VO 和 AC_VI 的 TXOP 限制，減少每次通道佔用的持續時間。

當飢餓條件解除時，參數以指數衰減函數逐步恢復至預設值，以避免震盪。

### 3.3 數學模型

**通道存取機率估計**：對於使用 EDCA 的站台，其在任意時槽成功傳輸的機率可近似為：

$$
\tau_i = \frac{2}{CWmin_i + 1}
$$

**公平性量化**：採用 Jain 公平性指數 [9] 衡量各 AC 間的資源分配公平性：

$$
J(\mathbf{x}) = \frac{\left(\sum_{i=1}^{n} x_i\right)^2}{n \sum_{i=1}^{n} x_i^2}, \quad J \in \left[\frac{1}{n}, 1\right]
$$

其中 $x_i$ 為第 $i$ 個 AC 的正規化吞吐量。$J = 1$ 表示完全公平。

**恢復函數**：飢餓解除後，各參數 $P$ 依以下指數衰減恢復：

$$
P(t+1) = P(t) + \gamma \cdot \left(P_{default} - P(t)\right), \quad 0 < \gamma < 1
$$

### 3.4 虛擬碼

```
演算法：QAD-EDCA 動態參數調整
輸入：監控間隔 T_mon、閾值 Q_th、P_th
      調整因子：delta_AIFS、alpha_CW、beta_TXOP
      恢復因子：gamma (0 < gamma < 1)

每隔 T_mon 秒在 AP 端執行：
  1. 對每個 AC ∈ {BE, BK}：
       測量 Q_i = AC_i 的佇列佔用率
       測量 P_loss_i = AC_i 的封包遺失率

  2. 若 Starvation(AC_BE) 或 Starvation(AC_BK)：
       // 偵測到飢餓——施加調整
       a. AIFSN_BE = max(AIFSN_BE - delta_AIFS, 2)
          AIFSN_BK = max(AIFSN_BK - delta_AIFS, 2)
       b. CWmin_VO = min(CWmin_VO * alpha_CW, CWmin_default_BE)
          CWmin_VI = min(CWmin_VI * alpha_CW, CWmin_default_BE)
       c. TXOP_VO = max(TXOP_VO * beta_TXOP, TXOP_min)
          TXOP_VI = max(TXOP_VI * beta_TXOP, TXOP_min)

  3. 否則：
       // 未偵測到飢餓——向預設值恢復
       對每個參數 P ∈ {AIFSN, CWmin, TXOP}：
         P(t+1) = P(t) + gamma * (P_default - P(t))

  4. 透過信標訊框向所有 STA 廣播更新後的參數

  5. 驗證 QoS 限制：
       若 delay_VO > 150 ms 或 delay_VI > 300 ms：
         部分回復調整（將 delta 縮減 50%）
```

### 3.5 關鍵參數

| 參數 | 符號 | 預設值 | 說明 |
|------|------|--------|------|
| 監控間隔 | $T_{mon}$ | 100 ms | AP 檢查佇列狀態的頻率 |
| 佇列閾值 | $Q_{th}$ | 80% | 觸發飢餓偵測的佇列佔用率 |
| 遺失率閾值 | $P_{th}$ | 10% | 觸發飢餓偵測的封包遺失率 |
| AIFS 調整步長 | $\Delta_{AIFS}$ | 1 | 每次調整週期的 AIFSN 縮減量 |
| CW 縮放因子 | $\alpha_{CW}$ | 2.0 | CWmin 增加的倍率 |
| TXOP 縮放因子 | $\beta_{TXOP}$ | 0.75 | TXOP 縮減的倍率 |
| 恢復因子 | $\gamma$ | 0.3 | 向預設值的指數衰減係數 |

---

## 4. 模擬設計

### 4.1 模擬環境

我們使用 **OMNeT++ 6.1** 搭配 **INET Framework 4.5** 作為模擬平台。INET 透過 `Ieee80211Mac` 模組並啟用 `qosStation` 參數，提供了完整的 IEEE 802.11 EDCA 機制實作。

### 4.2 網路拓撲

模擬網路由一個運行在基礎架構基本服務集（BSS）模式的存取點（AP）組成，並有 $N$ 個關聯的無線站台（STA）。我們評估四種網路規模：$N \in \{5, 10, 15, 20\}$。

### 4.3 流量模型

| AC | 應用 | 封包大小 | 傳送間隔 | 資料速率 |
|----|------|---------|---------|---------|
| AC_VO | VoIP (G.711) | 160 bytes | 20 ms | 64 kbps |
| AC_VI | 視訊串流 | 1280 bytes | 10 ms | 1.024 Mbps |
| AC_BE | 大量傳輸（飽和 UDP） | 1500 bytes | 可變 | 飽和 |
| AC_BK | 背景同步 | 512 bytes | 100 ms | 40.96 kbps |

### 4.4 實驗變數

1. **高優先權 STA 比例**：20%、40%、60%、80% 的 STA 產生 VO/VI 流量。
2. **整體網路負載**：輕載（$<30\%$）、中載（$30\text{--}60\%$）、重載（$60\text{--}90\%$）、飽和（$>90\%$）。
3. **QAD-EDCA 閾值參數**：掃描 $Q_{th} \in \{50\%, 70\%, 80\%, 90\%\}$ 和 $P_{th} \in \{5\%, 10\%, 15\%, 20\%\}$ 以評估敏感度。

### 4.5 效能指標

- **各 AC 吞吐量**（Mbps）
- **各 AC 平均延遲與延遲抖動**（ms）
- **各 AC 封包遺失率**（%）
- **Jain 公平性指數**（跨所有 AC）
- **QoS 滿足度**：AC_VO 延遲 $< 150$ ms 且 AC_VI 延遲 $< 300$ ms

### 4.6 比較方案

1. **標準 EDCA**（基準線）：依 IEEE 802.11 規範的固定預設參數 [1]。
2. **調優靜態 EDCA**：基於 [2] 研究發現的最佳靜態 AIFSN/CW 配置，代表無動態調適下的最佳效能。
3. **PDCF-DRL（Zuo 2025）**：基於深度強化學習的競爭視窗退避方案 [6]。
4. **QAD-EDCA**（本方案）：佇列感知動態調適方案。

---

## 5. 預期分析與討論

### 5.1 預期結果

基於文獻中的發現，我們預期：
- **飢餓緩解**：在高優先權 STA 比例達 60%–80% 時，QAD-EDCA 應能將 AC_BE/AC_BK 的封包遺失率從標準 EDCA 的 >40% 降至 <15%。
- **公平性提升**：Jain 公平性指數從標準 EDCA 的 ~0.4 提升至 >0.8。
- **QoS 保障**：在參數調整過程中，AC_VO 延遲維持 <150 ms、AC_VI 延遲維持 <300 ms。
- **運算效率**：相較 DRL 方案 [6][7]，QAD-EDCA 不需訓練階段，可即時部署。

### 5.2 討論重點

- 閾值參數（$Q_{th}$、$P_{th}$）的敏感度分析
- 監控間隔 $T_{mon}$ 對反應速度與穩定性的權衡
- 恢復因子 $\gamma$ 對震盪行為的影響
- 與 DRL 方案在不同網路規模下的效能比較

---

## 6. 專案計畫與時程

### 6.1 時程表

| 週次 | 期間 | 任務 | 交付物 |
|------|------|------|--------|
| 1–2 | 4/15 – 4/28 | 環境建置；實作並驗證基準 EDCA 模擬；在高負載下重現標準 EDCA 飢餓現象 | 基準模擬結果；飢餓現象展示圖表 |
| 3–4 | 4/29 – 5/12 | 在 OMNeT++/INET 中實作 QAD-EDCA 演算法；與 Edcaf 模組整合；單元測試 | 可運行的 QAD-EDCA 模組；初步比較結果 |
| 5–6 | 5/13 – 5/26 | 執行完整實驗矩陣；收集吞吐量、延遲、遺失、公平性數據；實作比較方案 | 完整模擬數據；分析腳本 |
| 7–8 | 5/27 – 6/10 | 分析結果並產生圖表；撰寫期末報告；準備簡報投影片 | 期末報告（PDF）；簡報投影片 |

### 6.2 甘特圖

```
任務                          W1   W2   W3   W4   W5   W6   W7   W8
                             4/15 4/22 4/29 5/06 5/13 5/20 5/27 6/03
環境建置 & 基準模擬           ████ ████
QAD-EDCA 實作                          ████ ████
實驗 & 數據收集                                ████ ████
文獻比較方案實作                                ████ ████
分析 & 圖表                                              ████ ████
報告撰寫                                            ████ ████ ████
簡報準備                                                       ████
                                                         截止日：6/10
```

### 6.3 組員分工

| 角色 | 成員 | 任務 |
|------|------|------|
| 演算法設計與實作 | （待填寫） | QAD-EDCA 演算法設計；OMNeT++/INET 中的 C++ 實作 |
| 模擬與實驗 | （待填寫） | 網路拓撲建置；流量配置；執行實驗 |
| 分析與視覺化 | （待填寫） | 結果解析；統計分析；圖表產生 |
| 報告與文獻回顧 | （待填寫） | 文獻調查；提案與期末報告撰寫 |

*備註：組員可跨角色分擔工作。*

---

## 7. 參考文獻

[1] IEEE Standard 802.11-2020, "IEEE Standard for Information Technology — Wireless LAN Medium Access Control (MAC) and Physical Layer (PHY) Specifications," IEEE, 2020.

[2] G. O. Ugwu, U. N. Nwawelu, and M. A. Ahaneku, "Effect of service differentiation on QoS in IEEE 802.11e enhanced distributed channel access: a simulation approach," *Journal of Engineering and Applied Science*, vol. 69, no. 1, pp. 1–15, 2022. DOI: 10.1186/s44147-021-00055-3.

[3] J. Lee, J. Choi, and S. Bahk, "Starvation avoidance-based dynamic multichannel access for low priority traffics in 802.11ac communication systems," *Computers & Electrical Engineering*, vol. 82, art. 106554, 2020. DOI: 10.1016/j.compeleceng.2020.106554.

[4] Y. P. Tuan, L. A. Chen, T. Y. Lin, et al., "Improving QoS mechanisms for IEEE 802.11ax with overlapping basic service sets," *Wireless Networks*, vol. 29, pp. 387–401, 2023. DOI: 10.1007/s11276-022-03148-w.

[5] P. Yi, W. Cheng, J. Wang, J. Pan, Y. Ouyang, and W. Zhang, "Intelligent Multi-link EDCA Optimization for Delay-Bounded QoS in Wi-Fi 7," arXiv preprint arXiv:2509.25855, 2025.

[6] Z. Zuo, D. Wang, X. Nie, X. Pan, M. Deng, and M. Ma, "PDCF-DRL: a contention window backoff scheme based on deep reinforcement learning for differentiating access categories," *The Journal of Supercomputing*, vol. 81, art. 213, 2025. DOI: 10.1007/s11227-024-06634-4.

[7] X. Du, X. Fang, R. He, L. Yan, L. Lu, and C. Luo, "Federated deep reinforcement learning-based intelligent channel access in dense Wi-Fi deployments," arXiv preprint arXiv:2409.01004, 2024.

[8] Q. Li, B. Lv, Y. Hong, and R. Wang, "ReinWiFi: Application-layer QoS optimization of WiFi networks with reinforcement learning," arXiv preprint arXiv:2405.03526, 2024.

[9] R. Jain, D. Chiu, and W. Hawe, "A quantitative measure of fairness and discrimination for resource allocation in shared computer systems," *DEC Research Report TR-301*, 1984.

[10] IEEE Standard 802.11ax-2021, "IEEE Standard for Information Technology — Amendment 1: Enhancements for High-Efficiency WLAN," IEEE, 2021.
