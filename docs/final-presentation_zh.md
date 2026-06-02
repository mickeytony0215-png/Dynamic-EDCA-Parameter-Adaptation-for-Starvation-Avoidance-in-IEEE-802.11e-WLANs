# 期末專案簡報
# IEEE 802.11 WLAN 中避免飢餓現象的動態 EDCA 參數自適應機制
### QAD-EDCA：Queue-Aware Dynamic EDCA

> 報告時間：約 15 分鐘 + 5 分鐘 Q&A
> 課程：NSYSU 無線通訊網路，Spring 2026
> 圖檔：`analysis/figures/`（PDF/PNG）；數據基準：`docs/standards-alignment-2026-05-28.md`
> 模擬平台：OMNeT++ 6.1 + INET 4.5；每組態 5 次重複（動態場景 10 次）取平均

---

## 1. 簡介（Introduction）（~2 分鐘）

### 投影片 1-1：標題頁
- 題目：Dynamic EDCA Parameter Adaptation for Starvation Avoidance in IEEE 802.11 WLANs
- 組員姓名 / 學號、課程名稱 / 日期

### 投影片 1-2：研究動機
- 現代 WLAN 同時承載語音、視訊、網頁、背景同步等異質流量。
- EDCA 以**靜態**參數做 QoS 差異化（AC_VO > AC_VI > AC_BE > AC_BK）；高負載下低優先權（BE/BK）會**飢餓**。
- Wi-Fi 6/7 雖引入 MU-EDCA、MLO，EDCA 公平性問題仍在。
- 既有 DRL 方案效能佳但**需訓練、運算成本高**——需要輕量級替代方案。

### 投影片 1-3：研究目標與貢獻
- 提出 **QAD-EDCA**：AP 端即時監控佇列 → 偵測飢餓 → 動態調整 EDCA 參數 → 飢餓解除後指數衰減回復。
- 目標：在**不需事先人工調參**下緩解飢餓、且不犧牲高優先權 QoS、運算成本 O(1)。
- 本報告也誠實呈現一個重要的工程教訓：**「動態自適應」必須驗證偵測器真的會觸發**（見 §6）。

---

## 2. 背景與問題定義（~3 分鐘）

### 投影片 2-1：EDCA 機制與標準預設
四個存取類別的 IEEE 802.11-2020 Table 9-155（OFDM PHY）預設值：

| AC | CWmin | CWmax | AIFSN | TXOP limit |
|----|-------|-------|-------|-----------|
| AC_BK | 15 | 1023 | 7 | **0**（單幀） |
| AC_BE | 15 | 1023 | 3 | **0**（單幀） |
| AC_VI | 7  | 15   | 2 | 3.008 ms |
| AC_VO | 3  | 7    | 2 | 1.504 ms |

> 重點：標準下 **BE/BK 的 TXOP = 0**（每次競爭只送一幀）。這在 §6 會成為關鍵。

### 投影片 2-2：飢餓問題（實測）
- 重負載（N=10，1 VO/1 VI/4 BE/4 BK，BE 飽和）下，標準 EDCA 的 **AC_BE 丟包率 ≈ 94.7%、平均延遲 ≈ 1086 ms**（見 §4 表）。
- Ugwu 等人 [2]：AIFSN 對 QoS 影響顯著大於 CW。
- Mammeri 等人 [3]：802.11ac 低優先權流量面臨嚴重飢餓。

### 投影片 2-3：問題形式化
飢餓判定（proposal §3.1）：

$$\text{Starvation}(AC_i) \iff \Big(\tfrac{Q_i}{Q_{cap}} > Q_{th}\Big) \lor \big(P_{loss,i} > P_{th}\big)$$

- $Q_i$：AP 端該 AC 的待傳佇列佔用；$P_{loss,i}$：區間丟包率。
- 預設 $Q_{th}=0.8$、$P_{th}=0.1$。

### 投影片 2-4：現有方案不足與研究缺口

| 方案 | 限制 |
|------|------|
| SDMA [3] | 依賴多通道，不適用單通道 |
| OBSS QoS [4] | 只處理跨 BSS 干擾 |
| PDCF-DRL [6] / FDRL [7] | 運算複雜度高、需訓練收斂 |
| ReinWiFi [8] | 作用於應用層，非 MAC 層 |

- **研究缺口**：輕量級、MAC 層、即時佇列感知的飢餓迴避。

---

## 3. 解決方案（Solution）（~4 分鐘）

### 投影片 3-1：QAD-EDCA 架構
```
┌─────────────────────────────────┐
│       QAD-EDCA Manager (AP)      │
│   監控 ──→ 偵測 ──→ 調整 ──→ 回復 │
│  佇列/丟包  飢餓?   AIFSN/CW/TXOP  指數衰減 │
└────────────┬────────────────────┘
   每 T_mon=100ms 一個控制迴圈；只調 AP 端 edcaf
```
- 實作：INET `Hcf→Edca→Edcaf→TxopProcedure` 子類化鏈（OMNeT++ 6.1 不支援固定型別子模組 typename override，故用 NED 複製鏈）。

### 投影片 3-2：飢餓緩解策略（proposal §3.3 的三維 AIFSN/CWmin/TXOP）
偵測到飢餓時：
1. **降低 BE/BK 的 AIFSN**（−1/週期，下限 minAifsn=2）→ 縮短競爭前等待。
2. **雙向調整 CWmin**：**提高 VO/VI 的 CWmin**（×cwScaleFactor，上限 15）抑制高優先權；
   **同時降低 BE/BK 的 CWmin**（÷cwScaleFactor，下限 = AC_VI 預設 7）讓低優先權更積極。
3. **縮減 VO/VI 的 TXOP**（×txopScaleFactor，下限 0.5 ms）→ 釋放通道時間。

### 投影片 3-3：回復、安全閥、與遲滯（避免震盪）
- **遲滯偵測（Schmitt trigger）**：以高門檻觸發 ON、較低的 release band（0.4×門檻）才解除。
  原因：回饋控制一旦緩解飢餓就排空它監看的佇列、移除自身觸發條件而造成 boost 震盪衰退；
  遲滯讓緩解在持續飽和下撐住，**同時保留自適應**（真正空閒時佇列跌破 release band → 解除、停止壓制 VO/VI）。
- 未偵測到飢餓：指數衰減回復 $P(t{+}1)=P(t)+\gamma\,(P_{default}-P(t))$，$\gamma=0.3$（double 累加器，避免整數截斷死結）。
- QoS 安全閥：若 VO/VI 延遲 > 150 ms（ITU-T G.114 / 3GPP 5QI=1,2），對 VO/VI 調整做 50% 部分回復。

### 投影片 3-4：演算法參數表（皆為設計選擇，靠 §5 sensitivity 自證）

| 參數 | 預設 | 標準依據 / 性質 |
|------|------|----------------|
| $T_{mon}$ | 100 ms | 與 Beacon 間隔同級 |
| $Q_{th}$ / $P_{th}$ | 0.8 / 0.1 | 自訂（sweep 驗證） |
| $\alpha_{CW}$ (cwScale) | 2.0 | 自訂 |
| $\beta_{TXOP}$ | 0.75 | 自訂 |
| $\gamma$ (recovery) | 0.3 | 自訂 |
| minAifsn | 2 | IEEE：AIFS=SIFS+AIFSN·slot > DIFS ⇒ AIFSN≥2 |

### 投影片 3-5：演算法虛擬碼（O(1) / 每 $T_{mon}$ 一次，在 AP）

```
每隔 T_mon（=100 ms，與 Beacon 同步）:
  1. 讀取: 對 i ∈ {BE, BK} 讀 佇列佔用率 Q_i/Q_cap、丟包率 P_loss_i
  2. 偵測 (含 Schmitt 遲滯):
       Starv(AC_i) ⟺ (Q_i/Q_cap > Q_th) ∨ (P_loss_i > P_th)
  3. if Starv(BE) ∨ Starv(BK):            // 飢餓 → 三維調整
       AIFSN_{BE,BK} = max(AIFSN − 1, 2)
       CWmin_{VO,VI} = min(CWmin × α_CW, 15)     // 抑制高優先權
       CWmin_{BE,BK} = max(CWmin ÷ α_CW, 7)      // 加速低優先權
       TXOP_{VO,VI}  = max(TXOP × β_TXOP, TXOP_min)
     else:                                  // 無飢餓 → 指數衰減回復
       對每個參數 P: P ← P + γ·(P_default − P)
  4. 廣播: 經 Beacon 的 EDCA Parameter Set 下發新參數
  5. QoS 安全閥: if d_VO > 150ms ∨ d_VI > 150ms:
       P ← (P_adjusted + P_default) / 2       // QoS 優先於飢餓緩解
```
- 核心數學：通道存取機率 $\tau \approx 2/(\mathrm{CWmin}+1)$——CWmin 3→15 使 $\tau$ 由 0.5 降到 0.125，這是「抑制高優先權」的量化依據。
- 複雜度 **O(1)**：每週期只讀 4 佇列 + 4 丟包率、做門檻判斷與定值運算——無訓練、無矩陣運算（對比 DRL 的 O(DRL 推論)）。

---

## 4. 實驗設定與穩態結果（~3 分鐘）

### 投影片 4-1：模擬環境（對齊標準，SSOT = standards-alignment 文件）
- 拓樸：1 AP + 1 server + N STA，120 m × 50 m InH 室內辦公室（**3GPP TR 38.901** Table 7.2-2）。
- PHY：54 Mbps OFDM（**IEEE 802.11-2020** Clause 17）。
- 流量（對齊 **3GPP TS 23.501** 5QI）：
  - VO：G.711 64 kbps，160 B/20 ms（5QI=1，PDB 100 ms）。
  - VI：HD 視訊 ~1 Mbps，1280 B/10 ms（5QI=2，PDB 150 ms）。
  - BE：飽和，1500 B/1 ms（5QI=9）。BK：512 B/100 ms（5QI=8）。
- 對照：**Standard EDCA / Tuned Static EDCA / QAD-EDCA** 三路。
  - Tuned Static：手動把 AC_BE→(CWmin 15→7, AIFSN 3→2)、AC_BK→(15→7, 7→3)，作為「一次性人工調參」基準。

**場景矩陣**（共用上述流量模型，對齊報告 Table II）：

| 場景 | 負載樣態 | N | 重複 × 時間 |
|---|---|---|---|
| 穩態 | 4 種 mix（VO/VI:BE/BK 比例；N=10：1/1/4/4、2/2/3/3、3/3/2/2、4/4/1/1） | 5,10,15,20 | 5 × 30s |
| 動態 | calm → surge → calm | 10 | 10 × 60s |
| 敏感度 | 頭條負載 + 參數掃描（Q_th×P_th、α_CW、γ、T_mon） | 10 | 5 × 30s |

### 投影片 4-2：穩態三路對比（N=10，1 VO/1 VI/4 BE/4 BK，飢餓案例）
圖：`throughput_comparison.png`、`delay_comparison.png`、`packet_loss.png`

per-AC 結果（VO/VI/BK 為 CBR 未飽和，只有 BE 飽和）：

| AC | 吞吐 Std/Tuned/QAD (Mbps) | 延遲 Std/Tuned/QAD (ms) |
|---|---|---|
| VO | 0.06 / 0.06 / 0.06 | 19.9 / 19.4 / 19.6 |
| VI | 1.02 / 1.02 / 1.02 | 21.7 / 21.6 / 21.3 |
| **BE** | 2.53 / 5.80 / **5.44** | 1086 / 832 / 957 |
| BK | 0.16 / 0.16 / 0.16 | 75 / 60 / **152** |

（BE 丟包率：94.7% / 87.9% / **88.6%**）

- **QAD-EDCA 把 BE 吞吐量提升約 2.15×（2.53→5.44）、延遲降 ~12%**。
- **VO/VI 完全不受損**（吞吐/延遲/丟包三方案幾乎一致）；**BK 吞吐保住、延遲略升**（QAD 75→152ms，背景流量無 QoS 上限，可接受）。
- QAD-EDCA ≈ Tuned Static（**略低 ~6%**，雖已加入「降 BE/BK CWmin」追趕）：原因是**結構性的**，見 §6——
  回饋控制在穩態飽和的天花板就是靜態最佳值，無法超越手調。

### 投影片 4-3：規模效應（N = 5/10/15/20）
圖：`n_scaling.png`

AC_BE 吞吐量 (Mbps)，固定 20% 高優先權：

| N | Standard | Tuned | **QAD** |
|---|---|---|---|
| 5 | 3.74 | 5.96 | **5.63** |
| 10 | 2.53 | 5.80 | **5.44** |
| 15 | 1.84 | 5.11 | **4.83** |
| 20 | 1.57 | 4.86 | **4.71** |

- **Standard 隨 N 崩潰（3.74→1.57），QAD 撐住（5.63→4.71）**——QAD 對 Standard 的倍率由 1.5× 放大到 **3.0×**。
- QAD 與 Tuned 在各 N 都把 BE 拉離飢餓區、曲線貼近（QAD 略低 ~6%）。

### 投影片 4-4：公平性的正確讀法
圖：`fairness_index.png`
- 跨 4 個 AC 的 Jain index 在「拉高 BE」時**反而下降**（BE 從次高被推到最高、分佈更不均）——此指標不適合衡量「飢餓緩解」。
- 正確結論看 **BE/BK 是否脫離飢餓**（吞吐量、丟包），而非跨-AC Jain。報告中改以「BE 吞吐量回升 + 丟包下降」陳述。

---

## 5. 參數敏感度（Sensitivity）（~2 分鐘）

圖：`sweep_cwscale.png`、`sweep_recoveryfactor.png`、`sweep_monitorinterval.png`、`threshold_sweep_heatmap.png`
（皆在會觸發演算法的 1 VO/1 VI/4 BE/4 BK、偵測器約 0.6 觸發率的條件下重跑）

| 參數 | 掃描範圍 | BE 吞吐量變化 | 趨勢 |
|------|---------|--------------|------|
| cwScaleFactor | 1.5–4.0 | 5.43↔5.44（~0%） | 幾乎無感（很快壓到 CWmin 下限） |
| recoveryFactor | 0.1–0.7 | 5.49→5.41（~1.5%） | 回復越快、BE 略降 |
| monitorInterval | 50–500 ms | 5.41↔5.45（~0.7%） | 影響極小 |
| queueThreshold | 0.5–0.9 | 5.45→5.41（~0.7%） | 門檻越高、觸發越少、BE 略降 |

- **結論：在重負載穩態下，QAD-EDCA 對其 4 個演算法參數高度 robust（≤1.5%）**，且趨勢方向皆符合物理直覺。
- 意涵：**不需要 per-deployment 精調**——任何合理初值都收斂到相近效果。（這是演算法**有在動**的前提下的 robustness，非「沒在動」的假平坦。）

---

## 6. 工程教訓：先驗證「動態」真的有動（誠實揭露）（~1.5 分鐘）

> 這頁是本專案的關鍵發現，也是審查最該問的地方，主動講清楚。

### 投影片 6-1：揭露——初版的「假動態」與修正
- 開發中以向量追蹤 manager 內部狀態，發現**初版的偵測器在所有測試組態都從未觸發**（`starvationDetected` 恆為 false，AIFSN/CW 全程預設值）。
- 真正讓初版「贏」的，是 manager 初始化時**誤把 BE/BK 的 TXOP 設成 2.528 ms**（標準是 0）——這個一次性**靜態** TXOP 賦予讓 BE/BK 可叢發多幀，效益全來自此、與動態演算法無關。
- 對照實驗證明：`Baseline + 靜態 TXOP 賦予`（BE=7.22）≈ 初版「QAD」（7.18），確認效益非來自自適應。
- 而且這個賦予還**反過來把 AP 佇列排空**，使佔用率永遠跨不過門檻——偵測器自我消解。
- **修正**：把 manager 的 TXOP 預設對齊 IEEE OFDM 標準（BK/BE=0、VI=3.008 ms、VO=1.504 ms）。修正後：
  - 偵測器在重載下**真的會觸發（修正當下約 64% 週期）**，AIFSN/CW 真的會隨負載變動（見 §7 圖）。
    （後續 §6-2 加入「降 BE/BK CWmin」後，觸發率因負反饋降到 ~15%，但參數仍持續維持在已調整狀態。）
  - BE 吞吐量改為 **5.44 Mbps**（誠實的 2.15× over Standard），不再是被灌水的 7.19。
- 教訓：**「Dynamic」不能只看輸出數字變好，要驗證控制迴圈真的有閉合**。

### 投影片 6-2：回饋控制在穩態飽和的天花板＝靜態最佳值（核心誠實洞見）
- 為追平靜態調參，我們再加「降 BE/BK CWmin（至 7）」與遲滯，但 BE 只從 5.34→5.44，**仍低於 Tuned 5.80**。
- **這是結構性、非調不夠**：QAD 一降 BE CWmin 就把 AP 佇列排空 → 偵測器看不到飢餓 → 停止緩解 → boost 衰退（觸發率因此從 64% 降到 ~15%）。**「解除飢餓」本身會移除偵測器的觸發**。
- **手調靜態最佳值在每個 mix 都略勝 QAD，且差距跨 mix／規模穩定**（證明是結構性、非調不夠）：

  | BE 吞吐量 (Mbps) | Standard | QAD | Tuned（手調靜態）|
  |---|---|---|---|
  | 1VO/1VI/4BE/4BK | 2.53 | 5.44 | **5.80** |
  | 2VO/2VI/3BE/3BK | 2.59 | 4.82 | **5.20** |
  | 3VO/3VI/2BE/2BK | 2.78 | 4.22 | **4.54** |

  → Tuned **在每個 mix 都略勝 QAD ~0.3–0.4 Mbps**，且差距穩定。
- 含意：**回饋控制要在穩態飽和贏過好的前饋（靜態最佳值），就得無條件持續維持最大 boost——那它就變成靜態方法了**，放棄自適應。
- 所以 QAD 的定位本來就**不是穩態壓過靜態最佳**，而是**免人工調參、且負載變動時自動跟上 / 空閒時自動回退**（§7）。

---

## 7. 動態負載下的自適應（QAD 真正的價值）（~2.5 分鐘）

場景 `dynamic_load.ini`：60 s、三階段 **calm[0,20) → surge[20,40) → calm[40,60)**，高優先權站台在 surge 期間才送流量；背景 4 BE（飽和）+4 BK。10 次重複取系集平均。

### 投影片 7-1：自適應軌跡（證明「有在動」）
圖：`fig_dynamic_qad_adapt.png`
- 上：QAD 全程把 **VO/VI 的 CWmin 從 3/7 拉高到 ~6–10**、**BE 的 AIFSN 壓到 2**（另外 BE/BK 的 CWmin 也被降到 7，圖中未繪）——參數持續被調離預設值。
- 下：`starvationDetected` 系集比例 ~0.15–0.25。**比初版低**，正是 §6-2 的負反饋：降 BE CWmin 排空佇列→偵測變稀疏；但參數因平滑回復而仍持續維持在已調整狀態。

### 投影片 7-2：BE 吞吐量隨時間
圖：`fig_dynamic_be_throughput.png`

| 階段 | Standard | Tuned Static | QAD-EDCA |
|---|---|---|---|
| calm | 2.6 | 6.0 | **5.6** |
| surge | 1.9 | 4.0 | **3.7** |

- 三路在 surge 都被高優先權擠壓而下降，surge 結束後回升。
- **QAD-EDCA 全程貼近 Tuned Static（~2.15× Standard），但無需事先人工設定**——負載一變，QAD 自動跟上；Tuned 的固定值只對「它被調的那個工作點」最佳。

### 投影片 7-3：高優先權 QoS——Standard 在 surge 會破功，QAD 救得回來
- **看階段平均會被騙**：VO/VI 平均延遲三路都 < 150 ms（最差 Standard surge ~33 ms）。但**看時間序列就現形**——`fig_dynamic_hi_delay.png` 顯示 **Standard 在 surge 期瞬間尖峰飆到 ~240 ms**（超過 150 ms VO 上限、真的破 QoS）。
- **Tuned 與 QAD 全程把瞬時延遲壓在低點**：QAD 只在 surge 起點有一個 ~70 ms 短尖峰後立刻壓平。
- **這正是 QAD 的價值**：免手調就把 Standard 的 240 ms 破功尖峰救回到接近 oracle（Tuned）的水準；QoS 安全閥確保抑制 BE/BK 時不犧牲 VO/VI。
- 誠實補述：QAD 在此情境**不贏 Tuned**（BE 與瞬時延遲都略遜），與穩態天花板（§6-2）一致；贏的是「免先知負載、免手調」。

### 投影片 7-4：誠實的限制
- 偵測器看的是 **AP 下行佇列**；在本「STA→AP→server」雙跳拓樸中，surge 時 BE 多半被擠在 **STA 上行**，較少封包抵達 AP，故 AP 端偵測在 surge 反而觸發變少（上圖下半部的凹陷）。
- 這是 AP-端量測的本質限制，非 bug；後續工作可改用 **per-AC 空中時間 / 上行端** 指標。

---

## 8. 比較、結論與未來工作（~2 分鐘）

### 投影片 8-1：與 DRL 文獻方案（PDCF-DRL [6]）對照 — reference point
圖：`positioning_tradeoff.png`

> 方法論（依 proposal §「Evaluation」）：PDCF-DRL 用 **DRL 訓練**，重現其訓練環境
> 超出本專案範圍、且與「輕量免訓練」論點相衝，故**引用其發表數據**作為
> performance-complexity trade-off 的**參考上界**，非同條件 head-to-head。
> 兩者模擬設定不同（[6]：20–120 站、normalized throughput %；本研究：N=5–20、per-AC Mbps），
> 僅作趨勢對照。

PDCF-DRL（Zuo 2025）發表結果（其設定）：

| 指標（[6] 原文） | Standard EDCA（[6] 量到） | **PDCF-DRL [6]** |
|---|---|---|
| 碰撞率（AC_VO，20→120 站） | 64%→85% | **6.9%→16.4%** |
| Normalized throughput（AC_VO） | 32%→14% | **85%→76%** |
| 多 AC 下 BE/BK 吞吐量份額 | 被高優先權壓低 | **與 VO/VI 近均等（≈90%+，無飢餓）** |
| 需訓練 / 運算 | 否 / O(1) | **是（DRL 數千 episode）/ O(DRL)** |

- **解讀**：PDCF-DRL 能把四個 AC 的吞吐量幾乎拉平（徹底消除飢餓）、且大幅壓低碰撞率——
  效能是上界；**代價是 DRL 訓練**（收斂前效能可能比 Standard 還差、需算力）。

- **QAD-EDCA 的定位**：以 O(1)、免訓練的規則，從第一個監控週期就提供飢餓緩解（BE ~2.15×），
  落在「免訓練 / 可即時部署」象限——正是 static EDCA 與 DRL 之間的中間地帶。

### 投影片 8-2：方案比較總表（含同條件模擬與文獻參考）

| 指標 | Standard | **QAD-EDCA** | 靜態 oracle（Tuned）| PDCF-DRL [6] |
|------|----------|--------------|---------------|---------------|
| 性質 | 靜態基準 | **動態、AC 感知、輕量** | 靜態，需先知負載 | DRL，AC 區分 |
| 飢餓緩解（BE） | 無（94.7% loss）| **5.44 Mbps（~2.15×）** | 5.80 Mbps | 近均等（無飢餓）|
| 需事先人工調參 / 訓練 | — | **否 / 否** | **需先知負載** | 訓練 |
| 隨負載自適應 | 否 | **是** | 否 | 是 |
| 運算 | O(1) | **O(1)** | O(1) | O(DRL) |
| vs QAD（本研究同條件）| **QAD 贏 2×** | — | 略勝 QAD ~6%（§6-2 天花板）| 發表上界 |

- **可隨插即用（不需先知負載 / 不需訓練）的方法裡，QAD 是最好的**：贏 Standard 2×、從第一個監控週期就以 O(1) 規則提供飢餓緩解。
- 略勝 QAD 的只有兩類「需先知條件」的上界：**靜態 oracle**（Tuned 需先知負載）與 **DRL**（PDCF-DRL 需訓練）。
- 註：Tuned 為本研究同條件模擬；PDCF-DRL 為 [6] 發表值（不同設定，趨勢參考）。

### 投影片 8-3：關鍵發現（誠實版）
1. QAD-EDCA 以輕量級規則把飢餓的 BE 吞吐量提升 ~2.15×、丟包從 94.7%→88.6%；**VO/VI QoS 不受損**（BK 吞吐亦保住、延遲略升）——**在「不需先知負載、不需訓練」的可部署方法裡最佳**。
2. **穩態下略低於需先知條件的兩類上界**：靜態 oracle（Tuned，~6%）與 DRL（PDCF-DRL）。我們證明這是回饋控制的**結構性天花板**（差距跨 mix／規模穩定，§6-2）——是嚴謹貢獻，不是缺陷。
3. 對自身 4 個演算法參數 robust（≤1.5%）。
4. 我們驗證了控制迴圈確實閉合（修掉「假動態」的 bug），這是方法可信度的基礎。

### 投影片 8-4：未來工作
- 偵測改用上行/空中時間指標（解 §7-4 限制，也可能緩解 §6-2 的負反饋天花板）。
- 真正異質 / 突發負載、站台動態進出場景（QAD 自適應優勢應更明顯）。
- 與 DRL 混合：QAD 作為 DRL 訓練收斂前的 warm-start 過渡。

---

## Q&A 準備（~5 分鐘）

**Q1：QAD-EDCA 穩態還略低於 Tuned Static，那價值在哪？**
- 我們已證明穩態贏不過手調是**回饋控制的結構性天花板**（§6-2），不是我們沒調好。
- 價值在**自動**：Tuned 的固定值只對單一工作點最佳；負載/流量混合一變就需重調。QAD 在 §7 動態場景中無需人工介入即貼近 Tuned，並能在飢餓解除後自動回復（保護 VO/VI）。

**Q2：你怎麼確定動態演算法真的有作用，而不是參數巧合？**
- 我們以向量記錄 manager 的 `starvationDetected` 與 `adjustedAifsn/CwMin`：在重載下會觸發、參數隨時間變動（`fig_dynamic_qad_adapt.png`；觸發率因增強版的負反饋約 ~15%，但 VO/VI CWmin 與 BE AIFSN 持續被調離預設）。並做過對照實驗排除了 TXOP 靜態賦予的混淆（§6）。

**Q3：為什麼不直接用 DRL（如 PDCF-DRL [6]）？**
- PDCF-DRL 的發表數據確實亮眼（碰撞率 <18%、normalized throughput >76%、多 AC 近均等＝零飢餓），是效能上界。
- 但代價是 **DRL 訓練**：需數千 episode 收斂、收斂前效能可能比 Standard 還差、需算力——資源受限 AP 不一定負擔得起。
- QAD-EDCA 是 O(1)、**免訓練**，從第一個監控週期就提供緩解；可作為 DRL 收斂前的過渡（warm-start）。
- 兩者非同條件 head-to-head（[6] 為 20–120 站、normalized %），我們把它當 performance-complexity 的參考上界。

**Q4：監控間隔 100 ms 會不會太慢？**
- 與 Beacon 間隔同級；sensitivity（§5）顯示 50–500 ms 對穩態 BE 影響 <1.5%。過快只增運算、易震盪。

**Q5：跨-AC Jain index 為何下降？**
- 因為把已是次高的 BE 再拉高會讓四個 AC 更不均。飢餓緩解應看「BE/BK 是否脫離飢餓」（吞吐量↑、丟包↓），而非跨-AC Jain。

**Q6：與真實環境差異？**
- 理想通道、Beacon 傳播即時、server 為無線雙跳（造成 §7-4 的偵測限制）。真實環境有衰落/干擾；未來可結合 802.11ax TWT。

---

## 參考文獻
[1] IEEE Std 802.11-2020.
[2] G. O. Ugwu et al., "Effect of service differentiation on QoS in IEEE 802.11e EDCA," *J. Eng. Appl. Sci.*, 2022.
[3] S. Mammeri et al., "Starvation avoidance-based dynamic multichannel access for low priority traffics in 802.11ac," *Comput. Electr. Eng.*, 2021.
[4] Y. P. Tuan et al., "Improving QoS mechanisms for IEEE 802.11ax with OBSS," *Wireless Netw.*, 2023.
[5] "Intelligent Multi-link EDCA Optimization for Delay-Bounded QoS in Wi-Fi 7," arXiv:2509.25855, 2025.
[6] Z. Zuo et al., "PDCF-DRL: a contention window backoff scheme based on DRL," *J. Supercomput.*, 2025.
[7] X. Du et al., "Federated DRL-based intelligent channel access in dense Wi-Fi," arXiv:2409.01004, 2024.
[8] Q. Li et al., "ReinWiFi: Application-layer QoS optimization of WiFi networks with RL," arXiv:2405.03526, 2024.
[9] R. Jain et al., "A quantitative measure of fairness," DEC TR-301, 1984.
[10] IEEE Std 802.11ax-2021.

- 標準對齊細節：`docs/standards-alignment-2026-05-28.md`（IEEE 802.11-2020 / 3GPP TS 23.501·26.114·TR 38.901 / ITU-T G.114·G.711 / IEEE 802.3-2005 / RFC 3551）。
- 對照組數據來源：Tuned Static 為本研究 OMNeT++ 同條件模擬；PDCF-DRL [6] 為其論文發表值（不同設定，趨勢參考）。
