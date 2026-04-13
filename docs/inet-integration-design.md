# QAD-EDCA 與 INET 4.5 整合實作方案

> 產出日期：2026-04-09
> 最後更新：2026-04-13
> 目的：為 QAD-EDCA 演算法在 OMNeT++/INET 4.5 中的完整實作提供技術規格

---

## 0. 設計目標與約束（依據 proposal §2.4 / §3.1）

### 目標優先順序

| 優先順序 | 目標 | 量化指標 |
|---------|------|--------|
| 1 | 緩解低優先權 AC 飢餓 | AC_BE/AC_BK 封包遺失率 < 15% |
| 2 | 保障高優先權 QoS | AC_VO 延遲 < 150 ms、AC_VI 延遲 < 300 ms |
| 3 | 提升整體公平性 | Jain Index > 0.8 |

### 設計約束

- **不修改 `~/simulation/inet4.5/` 的任何檔案**
- 所有編譯產出在專案的 `out/` 目錄
- 運算複雜度 O(1) / 監控週期
- 透過子類化（而非 friend class）存取 INET 的 protected 成員

### EDCA 標準參數（IEEE 802.11-2020 Table 9-155，OFDM PHY Clause 17–21）

| AC | CWmin | CWmax | AIFSN | TXOP limit |
|----|-------|-------|-------|------------|
| AC_BK | 15 | 1023 | 7 | 2.528 ms |
| AC_BE | 15 | 1023 | 3 | 2.528 ms |
| AC_VI | 7 | 15 | 2 | 4.096 ms |
| AC_VO | 3 | 7 | 2 | 2.080 ms |

**注意**：INET 4.5 的 `TxopProcedure.cc` 使用舊值（VO=1.504ms, VI=3.008ms），需在 `QadTxopProcedure` 的 `initialize()` 中以標準值覆蓋。

### QAD-EDCA 演算法參數

| 參數 | 符號 | 預設值 | 調整範圍 |
|------|------|--------|---------|
| 監控間隔 | T_mon | 100 ms | 與 beacon 間隔同步 |
| 佇列閾值 | Q_th | 80% | — |
| 遺失率閾值 | P_th | 10% | — |
| AIFS 調整步長 | Δ_AIFS | 1 | 下界 = 2（不低於 VO/VI 預設） |
| CW 縮放因子 | α_CW | 2.0 | 上界 = CWmin_default_BE (15) |
| TXOP 縮放因子 | β_TXOP | 0.75 | 下界 = TXOP_min |
| 恢復因子 | γ | 0.3 | ~83% 恢復 in 5 cycles |

### 飢餓偵測公式

$$Starvation(AC_i) \iff (Q_i/Q_{cap} > Q_{th}) \lor (P_{loss,i} > P_{th}), \quad i \in \{BE, BK\}$$

### 安全閥

$$\text{若 } d_{VO} > 150\text{ms} \lor d_{VI} > 300\text{ms}: \quad P_{adjusted} \leftarrow \frac{P_{adjusted} + P_{default}}{2}$$

---

## 1. INET 模組層級結構

QAD-EDCA Manager 需要存取 AP 內部的 MAC 模組。完整路徑如下：

```
AccessPoint (ap)
  └── wlan[0] : Ieee80211Interface
        └── mac : Ieee80211Mac
              └── hcf : Hcf
                    └── edca : Edca
                          ├── edcaf[0] : Edcaf  (AC_BK)
                          │     ├── pendingQueue : PendingQueue (implements IPacketQueue)
                          │     ├── contention : Contention
                          │     └── txopProcedure : TxopProcedure
                          ├── edcaf[1] : Edcaf  (AC_BE)
                          ├── edcaf[2] : Edcaf  (AC_VI)
                          └── edcaf[3] : Edcaf  (AC_VO)
```

AC 索引對應（定義在 `Edca.ned`）：
| 索引 | AC |
|------|------|
| 0 | AC_BK |
| 1 | AC_BE |
| 2 | AC_VI |
| 3 | AC_VO |

---

## 2. QadEdcaManager 的 NED 掛載方案

### 方案選擇：作為 Network 層級的獨立模組

**不修改 INET 的 AccessPoint.ned**，而是將 QadEdcaManager 放在 `EdcaFairnessNetwork` 層級，透過模組路徑存取 AP 內部結構。

修改 `network.ned`，新增：

```ned
submodules:
    qadManager: QadEdcaManager {
        parameters:
            apModule = "ap";  // 指向 AP 模組的路徑
            @display("p=400,50");
    }
```

**優點**：
- 不需修改 INET 原始碼
- 與 `~/simulation/inet4.5/` 完全解耦
- 透過 `getModuleByPath()` 存取 AP 內部模組

---

## 3. 四個 TODO 函數的實作方案

### 3.1 取得 Edcaf 模組的共用邏輯

新增 private helper 在 `QadEdcaManager` 中，在 `initialize()` 時快取指標：

```cpp
// 新增成員變數
Edcaf *edcafs[4] = {nullptr};
queueing::IPacketQueue *queues[4] = {nullptr};
TxopProcedure *txops[4] = {nullptr};

// 在 initialize(INITSTAGE_LINK_LAYER) 中快取
void QadEdcaManager::initialize(int stage) {
    // ... 現有邏輯 ...
    else if (stage == INITSTAGE_LINK_LAYER) {
        std::string apPath = par("apModule").stdstringValue();
        cModule *edca = getModuleByPath(
            (apPath + ".wlan[0].mac.hcf.edca").c_str());

        for (int i = 0; i < 4; i++) {
            edcafs[i] = check_and_cast<Edcaf *>(
                edca->getSubmodule("edcaf", i));
            queues[i] = edcafs[i]->getPendingQueue();  // public 方法
            txops[i] = edcafs[i]->getTxopProcedure();   // public 方法
        }
        // ... 其餘初始化 ...
    }
}
```

### 3.2 `getQueueLength(AccessCategory ac)` — 取得佇列長度

**API**：`IPacketQueue` 繼承自 `IPacketCollection`，提供：
- `getNumPackets()` → 目前佇列中的封包數
- `getMaxNumPackets()` → 佇列容量上限（-1 表示無限制）

```cpp
int QadEdcaManager::getQueueLength(AccessCategory ac) {
    return queues[ac]->getNumPackets();
}
```

同時修改 `detectStarvation()`：

```cpp
bool QadEdcaManager::detectStarvation() {
    for (int ac : {AC_BE, AC_BK}) {
        int qLen = queues[ac]->getNumPackets();
        int qCap = queues[ac]->getMaxNumPackets();
        if (qCap <= 0) qCap = 100;  // fallback

        bool starving = (double(qLen) / qCap > queueThreshold)
                        || (getPacketLossRate((AccessCategory)ac) > lossThreshold);
        if (starving) return true;
    }
    return false;
}
```

### 3.3 `getPacketLossRate(AccessCategory ac)` — 取得封包遺失率

採用方案 A：監聽 `packetDropped` signal。

`Hcf` 模組會發出 `packetDroppedSignal`（定義在 `inet/common/Simsignals.h`），每次有封包被丟棄（佇列溢出、重傳超限）都會觸發。

```cpp
// 新增成員
long dropCount[4] = {0};
long enqueueCount[4] = {0};

// initialize() 中訂閱 signal
cModule *hcf = getModuleByPath((apPath + ".wlan[0].mac.hcf").c_str());
hcf->subscribe(packetDroppedSignal, this);

// 同時訂閱 pendingQueue 的 packetPushedIn signal 來追蹤入隊數
for (int i = 0; i < 4; i++) {
    cModule *pq = check_and_cast<cModule *>(queues[i]);
    pq->subscribe(packetPushedInSignal, this);
}
```

在 `receiveSignal()` 中根據封包的 AC 分類累計，每次 `monitorAndAdjust()` 時計算區間 loss rate 再重置計數器。

```cpp
double QadEdcaManager::getPacketLossRate(AccessCategory ac) {
    long total = enqueueCount[ac];
    if (total == 0) return 0.0;
    double rate = double(dropCount[ac]) / total;
    // 重置（區間統計）
    dropCount[ac] = 0;
    enqueueCount[ac] = 0;
    return rate;
}
```

### 3.4 `getAverageDelay(AccessCategory ac)` — 取得平均延遲

INET 沒有直接在 MAC 層提供 per-AC delay 統計。需要自行追蹤：

```cpp
// 新增成員
simtime_t totalDelay[4] = {0};
long delayCount[4] = {0};
```

**追蹤方式**：監聽 `Edcaf` 的 `packetSentToPeer` signal。封包物件 (`inet::Packet`) 帶有 `creationTime`，可以計算 `simTime() - packet->getCreationTime()` 作為端到端 MAC 延遲。

```cpp
double QadEdcaManager::getAverageDelay(AccessCategory ac) {
    if (delayCount[ac] == 0) return 0.0;
    double avg = totalDelay[ac].dbl() / delayCount[ac];
    // 重置
    totalDelay[ac] = 0;
    delayCount[ac] = 0;
    return avg;
}
```

### 3.5 `applyParameters()` — 動態修改 EDCA 參數

#### 修改 AIFSN / CWmin / CWmax

透過 NED 參數 + 子類化的 `QadEdcaf::recalculate()` 重新觸發 `calculateTimingParameters()`：

```cpp
void QadEdcaManager::applyParameters() {
    for (int i = 0; i < 4; i++) {
        cModule *edcafMod = check_and_cast<cModule *>(edcafs[i]);

        edcafMod->par("cwMin").setIntValue(currentParams[i].cwMin);
        edcafMod->par("cwMax").setIntValue(currentParams[i].cwMax);
        edcafMod->par("aifsn").setIntValue(currentParams[i].aifsn);

        // 透過子類化暴露的 public 方法重新計算 timing
        check_and_cast<QadEdcaf *>(edcafs[i])->recalculate();
    }
}
```

#### 修改 TXOP Limit

透過子類化的 `QadTxopProcedure::setTxopLimit()`：

```cpp
// 在 applyParameters() 中加入
for (int i = 0; i < 4; i++) {
    auto *qadTxop = check_and_cast<QadTxopProcedure *>(txops[i]);
    qadTxop->setTxopLimit(currentParams[i].txopLimit);
}
```

#### 三階段調整的具體邏輯（對應 proposal §3.3）

```cpp
void QadEdcaManager::applyStarvationMitigation() {
    // 策略 1: 降低 BE/BK 的 AIFSN（下界 = 2）
    currentParams[AC_BE].aifsn = std::max(currentParams[AC_BE].aifsn - aifsStep, minAifsn);
    currentParams[AC_BK].aifsn = std::max(currentParams[AC_BK].aifsn - aifsStep, minAifsn);

    // 策略 2: 增加 VO/VI 的 CWmin（上界 = CWmin_default_BE = 15）
    int maxCw = defaultParams[AC_BE].cwMin;
    currentParams[AC_VO].cwMin = std::min((int)(currentParams[AC_VO].cwMin * cwScaleFactor), maxCw);
    currentParams[AC_VI].cwMin = std::min((int)(currentParams[AC_VI].cwMin * cwScaleFactor), maxCw);

    // 策略 3: 縮減 VO/VI 的 TXOP（下界 = TXOP_min）
    currentParams[AC_VO].txopLimit = std::max(currentParams[AC_VO].txopLimit * txopScaleFactor, minTxopLimit);
    currentParams[AC_VI].txopLimit = std::max(currentParams[AC_VI].txopLimit * txopScaleFactor, minTxopLimit);
}
```

#### 恢復邏輯（對應 proposal §3.4）

```cpp
void QadEdcaManager::applyRecovery() {
    for (int i = 0; i < 4; i++) {
        // P(t+1) = P(t) + γ * (P_default - P(t))
        currentParams[i].aifsn += (int)(recoveryFactor * (defaultParams[i].aifsn - currentParams[i].aifsn));
        currentParams[i].cwMin += (int)(recoveryFactor * (defaultParams[i].cwMin - currentParams[i].cwMin));
        currentParams[i].txopLimit += (defaultParams[i].txopLimit - currentParams[i].txopLimit) * recoveryFactor;
    }
}
```

#### 安全閥邏輯（對應 proposal §3.5）

```cpp
void QadEdcaManager::revertPartialAdjustment() {
    // P_adjusted = (P_adjusted + P_default) / 2
    for (int ac : {AC_VI, AC_VO}) {
        currentParams[ac].cwMin = (currentParams[ac].cwMin + defaultParams[ac].cwMin) / 2;
        currentParams[ac].txopLimit = (currentParams[ac].txopLimit + defaultParams[ac].txopLimit) / 2;
        currentParams[ac].aifsn = (currentParams[ac].aifsn + defaultParams[ac].aifsn) / 2;
    }
}
```

---

## 4. 需要新增的檔案清單

| 檔案 | 說明 | 複雜度 |
|------|------|--------|
| `src/QadEdcaf.h` | Edcaf 子類別，暴露 `recalculate()` 方法 | 低（~10 行） |
| `src/QadEdcaf.cc` | 實作（僅轉發呼叫） | 低（~5 行） |
| `src/QadEdcaf.ned` | NED 定義，extends Edcaf | 低（~5 行） |
| `src/QadTxopProcedure.h` | TxopProcedure 子類別，新增 `setTxopLimit()` | 低（~10 行） |
| `src/QadTxopProcedure.cc` | 實作 + 標準 TXOP 值覆蓋 | 低（~15 行） |
| `src/QadTxopProcedure.ned` | NED 定義，extends TxopProcedure | 低（~5 行） |
| `src/QadEdcaManager.ned`（已存在） | 需更新，新增 `apModule` 參數 | 低 |
| `src/QadEdcaManager.h`（已存在） | 需更新，新增快取指標、signal 處理、計數器 | 中 |
| `src/QadEdcaManager.cc`（已存在） | 需更新，填入 TODO 實作 | 中 |
| `Makefile` | 透過 `opp_makemake` 產生 | 低 |

---

## 5. 建置系統設定

### Makefile 方案

使用 OMNeT++ 的 `opp_makemake` 工具產生 Makefile，不修改 `~/simulation/` 的任何檔案：

```bash
cd "/home/cyw123/wirleess communication network project"

# 產生 Makefile，引用 INET 為外部依賴
opp_makemake -f --deep \
  -O out \
  -I$HOME/simulation/inet4.5/src \
  -L$HOME/simulation/inet4.5/src \
  -lINET \
  -KINET_PROJ=$HOME/simulation/inet4.5
```

**關鍵點**：
- `-I` 只是告訴編譯器去哪裡找 header files（唯讀）
- `-L` 和 `-l` 只是告訴 linker 去哪裡找 shared library（唯讀）
- 所有編譯產出都在專案的 `out/` 目錄
- **不會寫入 `~/simulation/` 的任何檔案**

### 執行方式

```bash
source ~/simulation/omnetpp-6.1/setenv  # 載入 OMNeT++ 環境變數
cd "/home/cyw123/wirleess communication network project"
make                                     # 編譯
cd simulations/
opp_run -m -u Cmdenv -c Baseline_N10 \
  -n ".:../src:$HOME/simulation/inet4.5/src" \
  -l $HOME/simulation/inet4.5/src/INET \
  -l ../src/edcafairness \
  omnetpp.ini
```

---

## 6. INI 配置更新

### Baseline 場景（不啟用 QAD-EDCA）

標準 EDCA 參數，不替換模組類型。用於驗證飢餓現象和作為比較基準。

### QAD-EDCA 場景

要讓 AP 使用子類化的 `QadEdcaf` 和 `QadTxopProcedure`，在 `qad_edca.ini` 中覆蓋模組類型：

```ini
# 使用 QAD-EDCA 子類化模組
*.ap.wlan[*].mac.hcf.edca.edcaf[*].typename = "QadEdcaf"
*.ap.wlan[*].mac.hcf.edca.edcaf[*].txopProcedure.typename = "QadTxopProcedure"
```

### TXOP 標準值覆蓋

在 `QadTxopProcedure` 的 `initialize()` 中以 IEEE 802.11-2020 Table 9-155 的值覆蓋 INET 預設值：

```cpp
void QadTxopProcedure::initialize(int stage) {
    TxopProcedure::initialize(stage);
    if (stage == INITSTAGE_LOCAL) {
        // 覆蓋 INET 的舊值，使用 IEEE 802.11-2020 Table 9-155 標準值
        // 由 QadEdcaManager 在 INITSTAGE_LINK_LAYER 階段設定正確的 AC-specific 值
    }
}
```

---

## 7. 整合架構總覽

```
┌─────────────────────────────────────────────────┐
│ EdcaFairnessNetwork                             │
│                                                 │
│  ┌──────────────┐     getModuleByPath()         │
│  │ QadEdcaManager│─────────────────────┐        │
│  │  (monitor &   │                     │        │
│  │   adjust)     │                     ▼        │
│  └──────────────┘     ┌────────────────────┐    │
│                       │ AccessPoint (ap)   │    │
│                       │  └─ wlan[0]        │    │
│                       │      └─ mac        │    │
│                       │          └─ hcf    │    │
│                       │              └─ edca│   │
│                       │                 ├─ edcaf[0] (BK) │
│                       │                 ├─ edcaf[1] (BE) │
│                       │                 ├─ edcaf[2] (VI) │
│                       │                 └─ edcaf[3] (VO) │
│                       └────────────────────┘    │
│                                                 │
│  ┌──────┐  ┌──────┐  ┌──────┐  ┌──────┐       │
│  │voSta │  │viSta │  │beSta │  │bkSta │       │
│  └──────┘  └──────┘  └──────┘  └──────┘       │
└─────────────────────────────────────────────────┘

運作流程（每 T_mon = 100ms）：
  QadEdcaManager
       │
       ├─ 1. 監控：讀取 BE/BK 的 queue 長度 + loss rate
       │
       ├─ 2. 偵測：評估飢餓條件（Q/Q_cap > Q_th OR P_loss > P_th）
       │
       ├─ 3a. 飢餓 → 三階段同步調整
       │   ├─ AIFSN_BE/BK ↓（下界 2）
       │   ├─ CWmin_VO/VI ↑（上界 15）
       │   └─ TXOP_VO/VI ↓（下界 TXOP_min）
       │
       ├─ 3b. 正常 → 指數衰減恢復（γ=0.3）
       │
       ├─ 4. 廣播：透過 beacon frame 傳播參數
       │
       └─ 5. 安全閥：若 VO/VI 延遲超限 → 部分回復 50%
```

---

## 8. 實作優先順序

| 步驟 | 工作 | 預估複雜度 | 前置依賴 |
|------|------|-----------|---------|
| 1 | 建立 `QadEdcaf` 和 `QadTxopProcedure` 子類別 | 低（各約 20 行） | 無 |
| 2 | 建立 Makefile 並確認可編譯空專案 | 低 | 無 |
| 3 | 實作 `getQueueLength()` + 快取指標 | 低 | 步驟 1 |
| 4 | 實作 `applyParameters()`（含三階段調整、恢復、安全閥） | 中 | 步驟 1 |
| 5 | 實作 `getPacketLossRate()`（signal 訂閱） | 中 | 步驟 2 |
| 6 | 實作 `getAverageDelay()`（signal 訂閱） | 中 | 步驟 2 |
| 7 | 端對端測試：baseline 場景驗證參數不變 | 低 | 步驟 1-6 |
| 8 | 端對端測試：qad_edca 場景驗證動態調整 | 中 | 步驟 7 |

---

## 9. 比較方案的模擬配置

| 方案 | INI 配置 | 說明 |
|------|---------|------|
| Standard EDCA | `baseline.ini`（已存在） | 固定預設參數，不替換模組 |
| Tuned Static EDCA | 新增 `tuned_static.ini` | 基於 [2] 的最佳靜態配置 |
| PDCF-DRL | 不模擬，引用論文數據 | 作為效能參考上界 |
| QAD-EDCA | `qad_edca.ini`（已存在） | 啟用 QadEdcaf + QadTxopProcedure |
