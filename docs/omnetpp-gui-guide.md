# OMNeT++ GUI 可視化操作指南

本文件說明如何在 OMNeT++ Qtenv 圖形介面中觀察 QAD-EDCA 模擬的各項內部狀態。

---

## 啟動 GUI

```bash
cd "$HOME/wirleess communication network project"
./run.sh QadEdca_N10 qad_edca       # QAD-EDCA 場景
./run.sh Baseline_N10 baseline      # Baseline 場景
```

啟動後會看到網路拓撲畫面，包含 AP、server、各類站台。

---

## 模擬控制

| 按鈕 | 快捷鍵 | 功能 |
|------|--------|------|
| ▶ Step | F4 | 執行一個事件 |
| ▶ Run | F5 | 連續執行（有動畫） |
| ▶▶ Fast | F6 | 快速執行（簡化動畫） |
| ▶▶▶ Express | F7 | 最快執行（無動畫，只更新進度） |
| ⏸ Stop | F8 | 暫停模擬 |

建議先按 **F5（Run）** 讓模擬跑一段時間，再暫停觀察。

---

## 模組層級結構

雙擊模組可以進入其內部。完整路徑如下：

```
EdcaFairnessNetwork                    ← 最外層網路
├── qadManager (QadEdcaManager)        ← QAD-EDCA 管理器（僅 QAD-EDCA 場景）
├── ap (AccessPoint)                   ← 基地台
│   └── wlan[0] (Ieee80211Interface)
│       └── mac (Ieee80211Mac)
│           └── hcf (Hcf / QadHcf)
│               └── edca (Edca / QadEdca)
│                   ├── edcaf[0] — AC_BK (Background)
│                   │   ├── pendingQueue     ← 等待傳送的佇列
│                   │   ├── contention       ← 頻道競爭模組
│                   │   ├── txopProcedure    ← TXOP 控制
│                   │   ├── ackHandler       ← ACK 處理
│                   │   └── recoveryProcedure ← 重傳恢復
│                   ├── edcaf[1] — AC_BE (Best Effort)
│                   ├── edcaf[2] — AC_VI (Video)
│                   └── edcaf[3] — AC_VO (Voice)
├── server (WirelessHost)              ← 接收端伺服器
├── voSta[0..n] (WirelessHost)         ← Voice 站台
├── viSta[0..n] (WirelessHost)         ← Video 站台
├── beSta[0..n] (WirelessHost)         ← Best Effort 站台
├── bkSta[0..n] (WirelessHost)         ← Background 站台
├── radioMedium                        ← 無線電傳播環境
├── configurator                       ← IP 位址分配
└── visualizer                         ← 視覺化輔助
```

---

## 觀察佇列狀態

### 路徑

```
ap → wlan[0] → mac → hcf → edca → edcaf[i] → pendingQueue
```

### 步驟

1. 雙擊 **ap** → 雙擊 **wlan[0]** → 雙擊 **mac** → 雙擊 **hcf** → 雙擊 **edca**
2. 畫面會顯示 **edcaf[0]~[3]** 四個子模組
3. 雙擊想觀察的 **edcaf[i]** → 看到 **pendingQueue**
4. 點選 **pendingQueue**，左下角 Inspector 面板會顯示：
   - `numPackets` — 目前佇列中的封包數量
   - `maxNumPackets` — 佇列容量上限（預設 100）

### AC 索引對照

| edcaf 索引 | AC 類別 | 流量類型 |
|-----------|---------|---------|
| edcaf[0] | AC_BK | Background（背景） |
| edcaf[1] | AC_BE | Best Effort（一般資料） |
| edcaf[2] | AC_VI | Video（視訊） |
| edcaf[3] | AC_VO | Voice（語音） |

---

## 觀察 EDCA 參數（CWmin / AIFSN / TXOP）

### 路徑

```
ap → wlan[0] → mac → hcf → edca → edcaf[i]
```

### 步驟

1. 點選某個 **edcaf[i]**
2. 在左下角 Inspector 面板展開 **fields**，可以看到：
   - `cwMin` — 目前的最小競爭視窗
   - `cwMax` — 目前的最大競爭視窗
   - `cw` — 目前實際的競爭視窗值
   - `ifs` — 目前的 IFS 時間（由 AIFSN 計算得出）
   - `slotTime` — 時槽時間
   - `sifs` — SIFS 時間
   - `owning` — 是否正在佔用頻道

### 觀察 TXOP

```
ap → wlan[0] → mac → hcf → edca → edcaf[i] → txopProcedure
```

點選 **txopProcedure**，Inspector 面板顯示：
- `limit` — TXOP 時間限制
- `start` — TXOP 開始時間（-1 表示目前未在 TXOP 中）

---

## 觀察 QAD-EDCA Manager 狀態

### 路徑

```
EdcaFairnessNetwork → qadManager
```

（僅在 QAD-EDCA 場景中存在，Baseline 場景沒有此模組）

### 步驟

1. 在最外層網路畫面點選 **qadManager**
2. Inspector 面板展開 **fields** 可以看到：
   - `starvationActive` — 是否正在偵測到飢餓
   - `monitorInterval` — 監控間隔
   - `queueThreshold` / `lossThreshold` — 飢餓偵測閾值
3. 展開 **signals,statistics** 可以看到：
   - `starvationDetected` — 飢餓偵測事件計數
   - `adjustedCwMinVo` / `adjustedCwMinVi` — VO/VI 的 CWmin 調整軌跡
   - `adjustedAifsnBe` / `adjustedAifsnBk` — BE/BK 的 AIFSN 調整軌跡

---

## 觀察封包傳送與丟棄

### 封包傳送統計

```
ap → wlan[0] → mac → hcf → edca → edcaf[i]
```

點選 edcaf[i]，展開 **signals,statistics**：
- `packetSentToPeer:count` — 此 AC 成功傳送的封包總數
- `packetSentToPeer:sum(packetBytes)` — 傳送的位元組總數

### 封包丟棄統計

```
ap → wlan[0] → mac → hcf
```

點選 **hcf**，展開 **signals,statistics**：
- `packetDrop:count` — 封包丟棄總數
- `packetDropQueueOverflow:count` — 因佇列溢出丟棄的數量
- `packetDropRetryLimitReached:count` — 因重傳上限丟棄的數量

---

## 觀察應用層收包

### 路徑

```
server → app[i]
```

| app 索引 | 對應 AC | 監聽埠 |
|---------|---------|--------|
| app[0] | AC_VO | port 5000 |
| app[1] | AC_VI | port 4000 |
| app[2] | AC_BE | port 80 |
| app[3] | AC_BK | port 21 |

點選 **server** → 雙擊進入 → 點選 **app[i]**，展開 **signals,statistics**：
- `packetReceived:count` — 收到的封包數
- `packetReceived:sum(packetBytes)` — 收到的位元組數
- `endToEndDelay:mean` — 平均端到端延遲

---

## 觀察站台發送端

### 路徑

```
voSta[0] → app[0]     ← Voice 發送源
viSta[0] → app[0]     ← Video 發送源
beSta[0] → app[0]     ← Best Effort 發送源
bkSta[0] → app[0]     ← Background 發送源
```

點選任一站台的 app[0]，可以看到：
- `packetSent:count` — 已發送的封包數
- `sendInterval` — 發送間隔

---

## 使用 Object Navigator（左上角樹狀結構）

不需要一層一層雙擊，可以直接在左上角的樹狀結構中展開路徑：

```
▶ EdcaFairnessNetwork
  ▶ ap
    ▶ wlan[0]
      ▶ mac
        ▶ hcf
          ▶ edca
            ▶ edcaf[0]  ← 直接點這裡
```

點選任一節點，右邊畫面會切換到該模組的內部視圖，左下角 Inspector 會顯示其屬性。

---

## 常用觀察情境

### 情境 1：觀察 BE 是否飢餓

1. 進入 `ap → wlan[0] → mac → hcf → edca → edcaf[1]`（AC_BE）
2. 看 `pendingQueue` 的 `numPackets` 是否持續接近上限（100）
3. 對比 `edcaf[3]`（AC_VO）的 pendingQueue 是否幾乎為空

### 情境 2：觀察 QAD-EDCA 參數調整效果

1. 在最外層點選 `qadManager`，看 `starvationActive` 狀態
2. 進入 `edcaf[3]`（AC_VO），看 `cwMin` 是否從 3 被調高
3. 進入 `edcaf[1]`（AC_BE），看 `ifs` 是否縮短（AIFSN 被降低）

### 情境 3：比較 Baseline vs QAD-EDCA

1. 分別用 `./run.sh Baseline_N10 baseline` 和 `./run.sh QadEdca_N10 qad_edca` 開兩次 GUI
2. 讓兩個模擬跑到相同時間點（例如 10 秒）
3. 比較 `server → app[2]`（AC_BE）的 `packetReceived:count`
