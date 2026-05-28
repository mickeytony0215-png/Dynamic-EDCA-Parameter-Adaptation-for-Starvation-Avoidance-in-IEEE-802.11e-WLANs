# Standards Alignment — 2026-05-28

> 紀錄 2026-05-28 完成的「魔術數字 → 官方標準」對齊作業：包含查詢的文件、
> 引用回填的參數、值已調整的參數，以及尚未取得標準依據的待辦項目。
>
> 本檔案搭配 `docs/dev-report-2026-04-14.md`、`docs/code-review-2026-04-14.md`
> 一起構成專案的技術備忘鏈。

---

## 1. 背景

`docs/code-review-2026-04-14.md` 的「待完成」清單中包含「參數調優與引用」一
項。原始 `omnetpp.ini` / `network.ned` / `QadEdcaManager.ned` 內有多處 PHY、
應用層、QoS 與拓樸參數是憑慣例填的，缺乏明確的標準引用。期末報告需要這些
引用作為設定理由的依據。

本次作業以 **NotebookLM 輔助查詢** 8 份官方文件，把可從文件背書的參數補上
標準引用，並把與最新規格不一致的兩個值對齊回標準推薦值。

---

## 2. 查詢的官方文件清單

| ID | 標準 / RFC | 章節索引 | 用途 |
|----|------------|----------|------|
| §1 | **IEEE Std 802.11-2020** | Clause 17（OFDM PHY）、Clause 9.4.2.28（EDCA Parameter Set IE）、Table 9-25（MSDU size）、Table 9-155（EDCA defaults） | 54 Mbps bitrate、AC 預設 EDCA 參數、AP 透過 Beacon 廣播 EDCA Parameter Set |
| §2 | **3GPP TS 23.501** | Table 5.7.4-1（Standardized 5QI） | 5QI=1/2/3/4/8/9 之 Resource Type、Priority、PDB、PER；對應到 VO/VI/BE/BK |
| §3 | **ITU-T G.114** | Figure 1（E-model）、§1 文字建議 | One-way mouth-to-ear delay：150 ms 為「essentially transparent」、400 ms 為一般網路規劃上限 |
| §4 | **ITU-T G.711** | §6.1（codec）、Table 6-1 | PCMU/PCMA 64 kbit/s；20 ms × 64 kbit/s = 160 B/封包 |
| §5 | **3GPP TS 26.114** | §5.2.1.1（codec）、§7.5.2、Annex A.4.7、Annex E（QoS profiles） | IMS MTSI：AMR/AMR-WB/EVS、HD 視訊 1280×720 H.264@25fps ≈ 950–1060 kbps；VoIP transfer delay 130 ms / 視訊 170 ms |
| §6 | **IEEE Std 802.3-2005** | Clause 3.2.7 + Figure 3-1、Table 4.4 | MAC Client Data 上限 1500 octets（由 `maxUntaggedFrameSize` 1518 octets 扣 18 octets 頭尾推出） |
| §7 | **3GPP TR 38.901** | Table 7.2-2 | Indoor Hotspot (InH) / Indoor-office 場景尺寸 120 m × 50 m × 3 m |
| §8 | **RFC 3551** | §4.2、Table 4（payload type 0 = PCMU、8 = PCMA） | G.711 RTP 預設 ptime = 20 ms、8 kHz 取樣、1 channel |

> 註：原計畫第 7 份文件「IEEE 802.11ax TGax Scenarios」(11-14/0980r16) 因為
> 我們的拓樸尺寸與其場景皆不相符（最接近的 Outdoor Large BSS 有 130 m ICD 但
> 50–100 STA/AP，與我們 N=5–20 不符），最終未引用。

---

## 3. 值已修改的參數

| 檔案：行 | 參數 | 舊值 | 新值 | 引用依據 | 動機 |
|---|---|---|---|---|---|
| `simulations/omnetpp.ini` `constraintAreaMax{X,Y}` | 模擬區域 | 800 m × 600 m | **120 m × 50 m** | 3GPP TR 38.901 Table 7.2-2 (InH Indoor-office) | 原值為自訂，無標準背書；新值對應到 InH 室內辦公室場景，STA-AP 距離縮到 ≤ 33 m，符合 802.11a 54 Mbps 涵蓋範圍 |
| `simulations/network.ned` `@display("bgb=...")` 與所有站台 `p=...` | 畫布與站台座標 | 800×600 px (=m)、AP@(400,300) 等 | bgb 120×50；AP@(60,25)、server@(60,10)、voSta@(30,20)、viSta@(90,20)、beSta@(30,40)、bkSta@(90,40) | 同上 | 等比例重新佈置到 InH 範圍內；以 StationaryMobility 之 `initFromDisplayString=true` 把 1 px 視為 1 m |
| `src/QadEdcaManager.ned` `viDelayBound` | Video 延遲上限 | 0.3 s | **0.15 s** | 3GPP TS 23.501 Table 5.7.4-1（5QI=2 Conversational Video PDB=150 ms）；TS 26.114 Annex E 視訊 transfer delay=170 ms | 原值 0.3 s 對應 5QI=4 *非*會話式視訊，但我們的 VI 流量是 1280×720 @ 25 fps≈1 Mbps 即時影像，性質為會話式 → 應對應到 5QI=2 |
| `simulations/scenarios/baseline.ini` `Baseline_N5/N10/N15/N20` 的 `${...}` 迭代 | 站台組合迭代方式 | 4 個獨立 `${...}` → 笛卡爾積 256 組合 | 加 `! numVo` 旗標 → **並行迭代 4 組合** | 不是規格對齊，是 bug 修正 | 原語法產生意外的 256 組合 × 5 reps = 1280 runs/config，與配置註解「4 mixes」不符 |
| `simulations/scenarios/qad_edca.ini` `QadEdca_N10/N20` | 同上 | 同上 | 同上並行迭代 | 同上 | 同上 |
| `simulations/omnetpp.ini` `**.vector-recording` | Vector 是否錄製 | 預設 true | **false**（加註解可隨時改回） | 無（工程考量） | 936 MB → 806 KB（1100× 縮減）；統計指標走 statistic 表（histogram）即可 |

---

## 4. 加上標準引用的參數（值未動）

僅補上 `# IEEE ... / 3GPP ... / ITU-T ... / RFC ...` 註解，**原值維持**。

| 檔案 | 參數 | 引用 |
|---|---|---|
| `simulations/omnetpp.ini` `*.*.wlan[*].bitrate = 54Mbps` | PHY 速率 | IEEE 802.11-2020 Clause 17 Table 17-4（OFDM PHY MCS）、Table 17-21（aSlotTime=9 µs, aSIFSTime=16 µs） |
| `simulations/omnetpp.ini` `*.voSta[*].app[0].messageLength=160B; sendInterval=20ms` | VO 封包尺寸與週期 | ITU-T G.711 §6（64 kbit/s）；RFC 3551 §4.2 + Table 4（PT=0/8 ptime=20 ms 預設）；8000 × 8 × 0.02 = 1280 bit = 160 B；3GPP TS 23.501 5QI=1 (Conv. Voice, PDB=100 ms) |
| `simulations/omnetpp.ini` `*.viSta[*].app[0].messageLength=1280B; sendInterval=10ms` | VI 封包尺寸與週期 | 3GPP TS 26.114 Annex A.4.7（HD 1280×720 H.264 @ 25 fps ≈ 950–1060 kbps）；§7.5.2.2（單 slice / RTP，封包 < MTU）；TS 23.501 5QI=2 (Conv. Video, PDB=150 ms) |
| `simulations/omnetpp.ini` `*.beSta[*].app[0].messageLength=1500B; sendInterval=1ms` | BE 封包尺寸與週期 | IEEE Std 802.3-2005 Clause 3.2.7（MAC Client Data 上限 1500 octets）；TS 23.501 5QI=9 (default Non-GBR, PDB=300 ms) |
| `simulations/omnetpp.ini` `*.bkSta[*].app[0]` | BK 流量 | TS 23.501 5QI=8 (Non-GBR background)；封包尺寸/週期為自訂（背景流量無標準規定） |
| `src/QadEdcaManager.ned` `voDelayBound=0.15s` | VO 延遲上限 | ITU-T G.114（≤150 ms = essentially transparent interactivity）；TS 23.501 5QI=1 PDB=100 ms；TS 26.114 Annex E IMS VoIP transfer delay=130 ms |
| `src/QadEdcaManager.ned` `minAifsn=2` | AIFSN 最小值 | IEEE 802.11-2020 EDCA 時序：AIFS = SIFS + AIFSN × aSlotTime，須 > DIFS = SIFS + 2 × aSlotTime → AIFSN ≥ 2 |

---

## 5. 未對齊 / 待補的部分

| 項目 | 現況 | 原因 / 後續處理 |
|---|---|---|
| `bkSta` 流量 512 B / 100 ms | 自訂值 | 背景流量無標準規格；可在報告中陳述「典型參考前作 [3]/[8] 使用 100 ms~1 s 區間」 |
| 4 個 QAD-EDCA 演算法參數（`cwScaleFactor` 2.0、`txopScaleFactor` 0.75、`recoveryFactor` 0.3、`monitorInterval` 0.1 s、threshold 0.8/0.1） | 自訂值 | 屬演算法設計選擇，**不能也不應**套標準。對應作法是用 sensitivity sweep 自證；本次已跑 4 套 sweep（見 `analysis/figures/sweep_*.png`、`threshold_sweep_heatmap.png`） |
| 802.11 LLC/SNAP 封裝 overhead | 未明列數值 | NotebookLM 在 802.11-2020 找不到具體 octets 數；實際為 LLC 3 B + SNAP 5 B = 8 B/MSDU。若報告需引用，需另查 ISO/IEC 8802-2 或 RFC 1042 |
| 800×600m 模擬區域的歷史紀錄 | 已移除 | 沿用原值會與 TR 38.901 InH 不一致；本次替換為 120×50 m。Sanity check（§7）顯示 VO/VI/BK 收包數一致、BE 微升 1.2% |

---

## 6. Sensitivity Analysis 觀察（影響參數選擇陳述）

本次 4 套 sensitivity sweep（cwScaleFactor / recoveryFactor / monitorInterval
全為 4 levels；ThresholdSweep 為 4×4 = 16 組）在 N=10 重負載穩態下，**所有
sweep 值都收斂到相同的 BE throughput ≈ 5.5 Mbps**（見
`analysis/figures/sweep_*.png` 與 `threshold_sweep_heatmap.png`）。

判讀：QAD-EDCA 在持續飽和負載下會把參數壓到操作邊界（cw/AIFSN 達 min、TXOP
達 max），因此 sweep 值僅影響「觸發前」與「過渡期」的細節，**對穩態統計值
沒有可觀測差異**。

對報告的兩種陳述方式（擇一）：
1. **正面**：QAD-EDCA 對 7 個演算法參數的選擇 robust——在重負載穩態下任何
   合理的初始值都會收斂到相同效果；論點為「定值即可，無需 per-deployment
   調校」。
2. **後續工作**：sensitivity 需要 transient 或 dynamic load 情境才會浮現；
   未來工作可用 `HighLoad_Progressive` 類的場景（站台動態加入）重新測試。

---

## 7. 驗證

- 修正前後跑 1 次 `Baseline_N10` run #0（同 seed）對比：
  - 800×600 m：VO=1497, VI=2996, BE=6312, BK=1199 packets
  - 120×50 m：VO=1497, VI=2996, BE=6388 (+1.2%), BK=1197 (-0.2%)
  - 結論：CBR 流量無變化；BE 微升因為 SNR 邊界縮短後通道條件改善
- `opp_run -q numruns` 在 `Baseline_N10` 由 256 (舊) 變回 20（4 並行迭代 × 5
  reps）；`QadEdca_N10` 同步。
- 完整批次（300 runs across 12 configs）跑完 90 分鐘，產生 `simulations/results/`
  全部資料 + `analysis/figures/` 9 張圖。

---

## 8. 相關檔案

- 參數修改：`simulations/omnetpp.ini`、`simulations/network.ned`、`src/QadEdcaManager.ned`、`simulations/scenarios/baseline.ini`、`simulations/scenarios/qad_edca.ini`
- 分析腳本：`analysis/parse_results.py`（修 SQL bug）、`analysis/transform.py`（新增）、`analysis/plot_figures.py`（擴 sweep / scaling / heatmap 函數）
- 產出圖表：`analysis/figures/{throughput,delay,packet,fairness,n_scaling,sweep_*,threshold_*}.{pdf,png}`
- 批次 log：`results/batch_<ts>.log`、`results/phase2_<ts>.log`
