# IEEE 802.11 WLAN 中避免飢餓現象的動態 EDCA 參數自適應機制

## 組員

| 姓名 | 學號 | 負責項目 |
|------|------|---------|
| （all members） | | |
| （all members） | | |

---

## 1. Background（背景）

### 1.1 EDCA 機制與 QoS 差異化

IEEE 802.11 標準中的增強型分散式通道存取（Enhanced Distributed Channel Access, EDCA）機制為無線區域網路提供了服務品質（QoS）差異化能力。EDCA 將流量分為四種存取類別（Access Category, AC）——語音（AC_VO）、視訊（AC_VI）、盡力而為（AC_BE）及背景（AC_BK），並為每種類別分配不同的通道存取參數：仲裁幀間距編號（AIFSN）、競爭視窗（CWmin/CWmax）及傳輸機會限制（TXOP limit）[1]。

然而，近年研究持續揭示 EDCA 靜態參數配置的根本缺陷。Ugwu 等人 [2] 透過 MATLAB 模擬系統性地分析了 EDCA 中服務差異化對 QoS 的影響，證實高優先權流量在飽和狀態下會嚴重侵佔低優先權流量的通道資源，且 AIFSN 對 QoS 的影響顯著大於 CW。Mammeri 等人 [3] 在 IEEE 802.11ac 系統中觀察到，EDCA 的優先權機制使低優先權流量面臨嚴重飢餓，並提出基於動態多通道存取的飢餓迴避方法（SDMA）。

### 1.2 從 Wi-Fi 6 到 Wi-Fi 7 的 EDCA 演進

隨著 IEEE 802.11ax（Wi-Fi 6）的推出，EDCA 機制延伸至多使用者場景（MU-EDCA），引入了觸發幀（Trigger Frame）和目標喚醒時間（TWT）等新特性 [10]。Tuan 等人 [4] 針對 802.11ax 環境中重疊基本服務集（OBSS）問題，提出降低干擾 AP 傳輸功率並延長低 QoS 站台 TXOP 限制的機制，在 128 kbits/s 資料到達率下將受干擾站台的平均下行傳輸延遲降低了 21.4%。

IEEE 802.11be（Wi-Fi 7）進一步引入多鏈路操作（Multi-Link Operation, MLO），為 EDCA 帶來跨鏈路流量管理的新挑戰。最新研究 [5] 指出，靜態 EDCA 參數在 MLO 環境中無法保證嚴格的延遲上界，並提出基於遺傳演算法的 MLO EDCA QoS 最佳化方案。

### 1.3 機器學習驅動的 EDCA 最佳化

近年來，深度強化學習（DRL）技術被廣泛應用於 EDCA 參數的動態調整。Zuo 等人 [6] 提出 PDCF-DRL 方案，將 DRL 整合至 EDCA 的競爭視窗退避機制中，在 20–120 個站台的場景下，正規化吞吐量維持在 76% 以上、碰撞率控制在 18% 以下。在單一 AC_VO 流量場景中，傳統 EDCA 的碰撞率高達 64%–85%、吞吐量僅 13%–32%，而 PDCF-DRL 則將碰撞率控制在 7%–16%、吞吐量維持在 77%–85%。Du 等人 [7] 結合聯邦學習（FL）與深度確定性策略梯度（DDPG）演算法，提出適用於密集 Wi-Fi 部署的智慧通道存取機制，在動態場景中相較傳統 DRL 方案降低 MAC 延遲達 45.9%。Li 等人 [8] 提出 ReinWiFi 框架，利用強化學習在應用層最佳化 Wi-Fi 網路的 QoS，在有未知干擾的商用環境中顯著優於 EDCA 機制。

儘管 DRL 方法展現了出色的效能，其高運算複雜度和訓練收斂時間限制了在資源受限設備上的即時部署。本專案探索一種輕量級、基於規則的自適應方案，以較低的運算成本達到有效的飢餓迴避。

---

## 2. Problem Definition（問題定義）

### 2.1 飢餓條件的形式化定義

現有文獻對 EDCA 飢餓的描述多為定性觀察：Ugwu 等人 [2] 觀察到低優先權流量在飽和狀態下「traffic congestion and frame loss rate are high」；Mammeri 等人 [3] 指出 BE/BK 的「throughputs are almost zero」。然而，文獻中尚無一個可量化、可直接用於即時偵測的形式化判斷準則。本專案提出以下低優先權存取類別 $AC_i$（其中 $i \in \{BE, BK\}$）的飢餓條件：

$$
\text{Starvation}(AC_i) \iff \left( \frac{Q_i}{Q_{cap}} > Q_{th} \right) \lor \left( P_{loss,i} > P_{th} \right)
$$

其中：
- $Q_i$：$AC_i$ 的目前佇列長度
- $Q_{cap}$：佇列容量
- $Q_{th}$：佇列佔用率閾值（預設 80%）
- $P_{loss,i}$：$AC_i$ 在監控區間內的封包遺失率
- $P_{th}$：封包遺失率閾值（預設 10%）

兩項指標以邏輯 OR 結合，因為它們捕捉的是互補的飢餓症狀。佇列佔用率（$Q_i/Q_{cap}$）偵測的是封包在緩衝區中累積速度超過傳輸速度的情況，反映持續的通道存取被剝奪。封包遺失率（$P_{loss,i}$）則捕捉飢餓以封包丟棄而非佇列堆積形式出現的場景——例如佇列已滿、新封包在入口即被丟棄，或封包因與高優先權流量反覆碰撞而超過 MAC 層重傳上限被丟棄。單獨使用任一指標都會遺漏特定的飢餓模式；兩者結合可確保在所有失效模式下皆能穩健偵測。

### 2.2 靜態 EDCA 的局限性

標準 EDCA 依據 IEEE 802.11-2020 Table 9-155 [1] 規範分配固定參數。競爭視窗值由 PHY 層常數 $aCWmin$ 和 $aCWmax$ 透過以下編碼推導：

$$CWmin = 2^{ECWmin} - 1, \quad CWmax = 2^{ECWmax} - 1$$

非 AP STA 的預設 EDCA 參數集（OFDM PHY，Clause 17–21）如下：

| AC | CWmin | CWmax | AIFSN | TXOP limit |
|----|-------|-------|-------|------------|
| AC_BK | $aCWmin$ | $aCWmax$ | 7 | 2.528 ms |
| AC_BE | $aCWmin$ | $aCWmax$ | 3 | 2.528 ms |
| AC_VI | $(aCWmin+1)/2 - 1$ | $aCWmin$ | 2 | 4.096 ms |
| AC_VO | $(aCWmin+1)/4 - 1$ | $(aCWmin+1)/2 - 1$ | 2 | 2.080 ms |

以 OFDM PHY（$aCWmin = 15$、$aCWmax = 1023$）為例，具體數值為：

| AC | CWmin | CWmax | AIFSN | TXOP limit |
|----|-------|-------|-------|------------|
| AC_BK | 15 | 1023 | 7 | 2.528 ms |
| AC_BE | 15 | 1023 | 3 | 2.528 ms |
| AC_VI | 7 | 15 | 2 | 4.096 ms |
| AC_VO | 3 | 7 | 2 | 2.080 ms |

這些參數在關聯時即確定，且在整個連線期間保持不變。該協定缺乏任何回饋機制來偵測或緩解飢餓狀態。如 Ugwu 等人 [2] 所驗證，這些靜態參數在飽和負載下導致低優先權流量的封包遺失率急劇上升。

### 2.3 現有方案的不足

| 方案類別 | 代表文獻 | 主要限制 |
|----------|---------|---------|
| 動態多通道存取 | Mammeri 等人 [3] | 依賴 802.11ac 通道綁定，不直接適用於單通道 BSS 場景 |
| OBSS QoS 改善 | Tuan 等人 [4] | 聚焦於跨 BSS 干擾，未處理單一 BSS 內的 AC 間飢餓 |
| DRL-based 方案 | Zuo 等人 [6]、Du 等人 [7] | 運算複雜度高，訓練收斂慢，不適合資源受限的 AP |
| 應用層最佳化 | Li 等人 [8] | 作用於應用層排程，未直接調整 MAC 層 EDCA 參數 |

**研究缺口**：缺乏一種輕量級、在 MAC 層直接運作、能即時感知佇列狀態並動態調整 EDCA 參數的飢餓迴避機制。

現有動態 EDCA 方案通常針對不同網路類型（如車載或 IoT），且僅調整一至兩個參數（通常只調 CW），或缺乏形式化的飢餓偵測準則。QAD-EDCA 針對這些不足，結合佇列佔用率與封包遺失率的雙指標飢餓偵測公式，搭配三維度同步參數調整（AIFSN、CWmin、TXOP），並輔以指數恢復機制與 QoS 安全閥，構成一套針對基礎架構 WLAN 的閉環飢餓迴避系統。

---

## 3. 提出的解決方案：QAD-EDCA

### 3.1 設計目標

QAD-EDCA 旨在解決飢餓問題，同時遵循以下優先順序的目標：

| 優先順序 | 目標 | 量化指標 |
|---------|------|--------|
| 1 | 緩解低優先權 AC 的飢餓 | AC_BE/AC_BK 封包遺失率 < 15%（從 > 40% 降低） |
| 2 | 保障高優先權 QoS | AC_VO 延遲 < 150 ms、AC_VI 延遲 < 300 ms |
| 3 | 提升整體公平性 | Jain 公平性指數 > 0.8（從 ~0.4 提升） |

目標並非讓所有 AC 平等，而是確保低優先權流量能維持最低可用的吞吐量，同時不損害即時服務的品質。

### 3.2 架構設計

佇列感知動態 EDCA（QAD-EDCA）作為集中式監控與控制器運行在存取點（AP）端。選擇 AP 作為控制點的原因：

- AP 能觀察 BSS 內所有 AC 的佇列狀態，具備全局視野。
- AP 可透過信標訊框（beacon frame）中的 EDCA Parameter Set element 將更新後的參數廣播至所有關聯站台，無需修改 STA 端的實作。
- 監控間隔（$T_{mon} = 100$ ms）與標準信標間隔同步，不引入額外開銷。

相較於 DRL 方案 [6][7] 需要訓練階段和大量運算資源，QAD-EDCA 是輕量級的規則引擎，每次監控週期的運算複雜度為 O(1)——僅需讀取 4 個 AC 的佇列長度和遺失率、評估閾值條件、施加確定性調整。

### 3.3 三階段調整策略

偵測到飢餓後，QAD-EDCA 同時施加三種互補策略，分別作用於 EDCA 通道存取過程的不同階段：

#### 策略 1：降低低優先權 AC 的 AIFSN

$$AIFSN_i = \max(AIFSN_i - \Delta_{AIFS},\ 2), \quad i \in \{BE, BK\}$$

AIFSN 決定 STA 在 SIFS 之後需等待多少個時槽才能進入競爭。降低 BE/BK 的 AIFSN 可縮短其競爭前等待時間，使其更早參與通道存取。下界設為 2（與 AC_VO/AC_VI 的預設值相同），確保低優先權 AC 永遠不會比高優先權更具攻擊性。如 Ugwu 等人 [2] 所確認：「AIFS has more influence on the QoS of EDCA protocol」，AIFSN 是最有效的單一調節參數。

#### 策略 2：增加高優先權 AC 的 CWmin

$$CWmin_i = \min(CWmin_i \times \alpha_{CW},\ CWmin_{default,BE}), \quad i \in \{VO, VI\}$$

CWmin 決定退避視窗大小。增加 VO/VI 的 CWmin 可擴大其退避範圍，緩和通道存取的積極性。上界設為 $CWmin_{default,BE} = 15$，確保高優先權 AC 仍保有結構性優勢。對通道存取機率的影響為：

$$\tau_i = \frac{2}{CWmin_i + 1}$$

當 CWmin 從 3 增加到 15 時，每時槽傳輸機率從 50% 降至 12.5%，顯著降低高優先權的主宰程度。

#### 策略 3：縮減高優先權 AC 的 TXOP 限制

$$TXOP_i = \max(TXOP_i \times \beta_{TXOP},\ TXOP_{min}), \quad i \in \{VO, VI\}$$

TXOP 限制決定 STA 贏得競爭後可佔用通道多長時間。縮減 TXOP 迫使高優先權 STA 更快釋放通道，為低優先權流量創造更多存取機會。下界 $TXOP_{min}$ 確保每次存取至少能傳輸一個訊框。

#### 為什麼同時施加三種策略

三種策略同時（而非依序）施加，因為它們作用於通道存取的不同階段：AIFSN 影響「何時開始競爭」、CWmin 影響「退避等待多久」、TXOP 影響「佔用通道多久」。在三個維度同時調整可提供最快速的飢餓回應。

### 3.4 恢復機制

當飢餓條件不再滿足時，各參數透過指數衰減逐步恢復至預設值：

$$P(t+1) = P(t) + \gamma \cdot \left(P_{default} - P(t)\right), \quad 0 < \gamma < 1$$

以 $\gamma = 0.3$ 為例，處於調整極限的參數在 5 個監控週期（~500 ms）內可恢復至預設值的約 83%。漸進式恢復對於防止震盪至關重要：若參數瞬間恢復，飢餓很可能立即再次發生，觸發新一輪調整——形成 ping-pong 效應，同時損害公平性和 QoS 穩定性。

### 3.5 QoS 約束驗證（安全閥）

施加調整後，演算法驗證高優先權 QoS 保障是否仍然完整：

$$\text{若 } d_{VO} > 150\text{ ms} \lor d_{VI} > 300\text{ ms}: \quad P_{adjusted} \leftarrow \frac{P_{adjusted} + P_{default}}{2}$$

此部分回復（取調整值與預設值的中點）作為安全閥，確保**目標 2（QoS 保障）永遠優先於目標 1（飢餓緩解）**。有界的調整範圍（AIFSN 下界 2、CWmin 上界 $CWmin_{default,BE}$、TXOP 下界 $TXOP_{min}$）提供額外的結構性保障。

### 3.6 公平性量化

整體公平性以 Jain 公平性指數 [9] 衡量：

$$J(\mathbf{x}) = \frac{\left(\sum_{i=1}^{n} x_i\right)^2}{n \sum_{i=1}^{n} x_i^2}, \quad J \in \left[\frac{1}{n}, 1\right]$$

其中 $x_i$ 為第 $i$ 個 AC 的正規化吞吐量。$J = 1$ 表示完全公平。在高優先權主宰的標準 EDCA 下，$J$ 降至 ~0.4；QAD-EDCA 目標為 $J > 0.8$。

### 3.7 虛擬碼

```
演算法：QAD-EDCA 動態參數調整
輸入：監控間隔 T_mon、閾值 Q_th、P_th
      調整因子：delta_AIFS、alpha_CW、beta_TXOP
      恢復因子：gamma (0 < gamma < 1)

每隔 T_mon 秒在 AP 端執行：
  1. 監控：對每個 AC ∈ {BE, BK}：
       讀取 Q_i = AC_i 的佇列佔用率
       讀取 P_loss_i = AC_i 的封包遺失率

  2. 偵測：若 Starvation(AC_BE) 或 Starvation(AC_BK)：
       // 偵測到飢餓——施加三階段調整
       a. AIFSN_BE = max(AIFSN_BE - delta_AIFS, 2)
          AIFSN_BK = max(AIFSN_BK - delta_AIFS, 2)
       b. CWmin_VO = min(CWmin_VO * alpha_CW, CWmin_default_BE)
          CWmin_VI = min(CWmin_VI * alpha_CW, CWmin_default_BE)
       c. TXOP_VO = max(TXOP_VO * beta_TXOP, TXOP_min)
          TXOP_VI = max(TXOP_VI * beta_TXOP, TXOP_min)

  3. 恢復：否則（未偵測到飢餓）：
       對每個參數 P ∈ {AIFSN, CWmin, TXOP}：
         P(t+1) = P(t) + gamma * (P_default - P(t))

  4. 廣播：透過信標訊框傳播更新後的參數

  5. 驗證：若 delay_VO > 150 ms 或 delay_VI > 300 ms：
       部分回復：P = (P_adjusted + P_default) / 2
```

### 3.8 關鍵參數

| 參數 | 符號 | 預設值 | 說明 |
|------|------|--------|------|
| 監控間隔 | $T_{mon}$ | 100 ms | 與信標間隔同步 |
| 佇列閾值 | $Q_{th}$ | 80% | 觸發飢餓偵測的佇列佔用率 |
| 遺失率閾值 | $P_{th}$ | 10% | 觸發飢餓偵測的封包遺失率 |
| AIFS 調整步長 | $\Delta_{AIFS}$ | 1 | 每次調整的 AIFSN 縮減量；下界 = 2 |
| CW 縮放因子 | $\alpha_{CW}$ | 2.0 | CWmin 增加倍率；上界 = $CWmin_{default,BE}$ |
| TXOP 縮放因子 | $\beta_{TXOP}$ | 0.75 | TXOP 縮減倍率；下界 = $TXOP_{min}$ |
| 恢復因子 | $\gamma$ | 0.3 | 指數衰減速率；約 5 個週期恢復至 83% |

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
| 演算法設計與實作 | （all members） | QAD-EDCA 演算法設計；OMNeT++/INET 中的 C++ 實作 |
| 模擬與實驗 | （all members） | 網路拓撲建置；流量配置；執行實驗 |
| 分析與視覺化 | （all members） | 結果解析；統計分析；圖表產生 |
| 報告與文獻回顧 | （all members） | 文獻調查；提案與期末報告撰寫 |

*備註：組員可跨角色分擔工作。*

---

## 7. 參考文獻

[1] IEEE Standard 802.11-2020, "IEEE Standard for Information Technology — Wireless LAN Medium Access Control (MAC) and Physical Layer (PHY) Specifications," IEEE, 2020.

[2] G. O. Ugwu, U. N. Nwawelu, and M. A. Ahaneku, "Effect of service differentiation on QoS in IEEE 802.11e enhanced distributed channel access: a simulation approach," *Journal of Engineering and Applied Science*, vol. 69, no. 1, pp. 1–15, 2022. DOI: 10.1186/s44147-021-00055-3.

[3] S. Mammeri, M. Yazid, R. Kacimi, and L. Bouallouche-Medjkoune, "Starvation avoidance-based dynamic multichannel access for low priority traffics in 802.11ac communication systems," *Computers & Electrical Engineering*, vol. 90, art. 106942, 2021. DOI: 10.1016/j.compeleceng.2020.106942.

[4] Y. P. Tuan, L. A. Chen, T. Y. Lin, et al., "Improving QoS mechanisms for IEEE 802.11ax with overlapping basic service sets," *Wireless Networks*, vol. 29, pp. 387–401, 2023. DOI: 10.1007/s11276-022-03148-w.

[5] P. Yi, W. Cheng, J. Wang, J. Pan, Y. Ouyang, and W. Zhang, "Intelligent Multi-link EDCA Optimization for Delay-Bounded QoS in Wi-Fi 7," arXiv preprint arXiv:2509.25855, 2025.

[6] Z. Zuo, D. Wang, X. Nie, X. Pan, M. Deng, and M. Ma, "PDCF-DRL: a contention window backoff scheme based on deep reinforcement learning for differentiating access categories," *The Journal of Supercomputing*, vol. 81, art. 213, 2025. DOI: 10.1007/s11227-024-06634-4.

[7] X. Du, X. Fang, R. He, L. Yan, L. Lu, and C. Luo, "Federated deep reinforcement learning-based intelligent channel access in dense Wi-Fi deployments," arXiv preprint arXiv:2409.01004, 2024.

[8] Q. Li, B. Lv, Y. Hong, and R. Wang, "ReinWiFi: Application-layer QoS optimization of WiFi networks with reinforcement learning," arXiv preprint arXiv:2405.03526, 2024.

[9] R. Jain, D. Chiu, and W. Hawe, "A quantitative measure of fairness and discrimination for resource allocation in shared computer systems," *DEC Research Report TR-301*, 1984.

[10] IEEE Standard 802.11ax-2021, "IEEE Standard for Information Technology — Amendment 1: Enhancements for High-Efficiency WLAN," IEEE, 2021.
