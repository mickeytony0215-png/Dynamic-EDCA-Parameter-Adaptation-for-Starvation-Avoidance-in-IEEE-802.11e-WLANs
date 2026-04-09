# QAD-EDCA 與 INET 4.5 整合實作方案

> 產出日期：2026-04-09
> 目的：為 `QadEdcaManager.cc` 中 4 個 TODO helper functions 提供具體實作方案

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

**缺點**：
- 需要透過較長的模組路徑存取（但 OMNeT++ 完全支援）

---

## 3. 四個 TODO 函數的實作方案

### 3.1 取得 Edcaf 模組的共用邏輯

新增一個 private helper 在 `QadEdcaManager` 中，在 `initialize()` 時快取指標：

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

同時修改 `detectStarvation()` 中的 `queueCapacity`：

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

INET 的 `Edcaf` 沒有直接提供 loss rate API。有兩個可行方案：

#### 方案 A：監聽 `packetDropped` signal（推薦）

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

#### 方案 B：讀取統計量（簡易但精度較低）

直接從 `edcaf` 的 recorded statistics 讀取 `packetSentToPeer:count`，與自行維護的入隊計數比較。此方案較不精確，不推薦。

**結論：採用方案 A。**

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

這是最關鍵的部分。INET 的 `Edcaf` 在 `calculateTimingParameters()` 中從 `par()` 讀取 `cwMin`、`cwMax`、`aifsn`，且 `cwMin`/`cwMax` 也存為成員變數。

#### 修改 cwMin / cwMax

`Edcaf` 的 `cwMin`、`cwMax`、`cw` 是 **protected** 成員，無法從外部直接設定。

**方案：透過 NED 參數 + 重新觸發 `calculateTimingParameters()`**

```cpp
void QadEdcaManager::applyParameters() {
    for (int i = 0; i < 4; i++) {
        cModule *edcafMod = check_and_cast<cModule *>(edcafs[i]);

        // 設定 NED 參數（volatile 可在執行期修改）
        edcafMod->par("cwMin").setIntValue(currentParams[i].cwMin);
        edcafMod->par("cwMax").setIntValue(currentParams[i].cwMax);
        edcafMod->par("aifsn").setIntValue(currentParams[i].aifsn);

        // 重新計算 timing（這會重新讀取 par 值並更新內部成員）
        edcafs[i]->calculateTimingParameters();
    }
}
```

**重要問題**：`calculateTimingParameters()` 是 **protected** 方法。

**解決方案（二選一）**：

| 方案 | 做法 | 影響 |
|------|------|------|
| A. 子類化（推薦） | 建立 `QadEdcaf extends Edcaf`，新增 `public recalculate()` 方法呼叫 `calculateTimingParameters()`，在 NED 中以 `QadEdcaf` 取代 `Edcaf` | 需新增一個薄包裝類別，但不修改 INET 原始碼 |
| B. Friend class | 在 INET 的 `Edcaf.h` 加入 `friend class QadEdcaManager` | 直接修改 INET，不推薦 |

**結論：採用方案 A（子類化）。**

#### 修改 TXOP Limit

`TxopProcedure` 的 `limit` 是 protected 成員，初始化時從 `par("txopLimit")` 讀取。

同樣方案：子類化 `TxopProcedure` 為 `QadTxopProcedure`，新增 public setter：

```cpp
class QadTxopProcedure : public TxopProcedure {
  public:
    void setTxopLimit(simtime_t newLimit) { limit = newLimit; }
};
```

---

## 4. 需要新增的檔案清單

| 檔案 | 說明 |
|------|------|
| `src/QadEdcaf.h` | Edcaf 子類別，暴露 `recalculate()` 方法 |
| `src/QadEdcaf.cc` | 實作（極簡，僅轉發呼叫） |
| `src/QadEdcaf.ned` | NED 定義，extends Edcaf |
| `src/QadTxopProcedure.h` | TxopProcedure 子類別，新增 `setTxopLimit()` |
| `src/QadTxopProcedure.cc` | 實作（極簡） |
| `src/QadTxopProcedure.ned` | NED 定義，extends TxopProcedure |
| `src/QadEdcaManager.ned`（已存在） | 需更新，新增 `apModule` 參數 |
| `src/QadEdcaManager.h`（已存在） | 需更新，新增快取指標和 signal 處理 |
| `src/QadEdcaManager.cc`（已存在） | 需更新，填入 TODO 實作 |
| `Makefile` | 新建，引用 INET 的 include/lib 路徑 |

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

要讓 AP 使用子類化的 `QadEdcaf` 和 `QadTxopProcedure`，在 `omnetpp.ini` 中覆蓋模組類型：

```ini
# 使用 QAD-EDCA 子類化模組（僅在 qad_edca 場景中）
*.ap.wlan[*].mac.hcf.edca.edcaf[*].typename = "QadEdcaf"
*.ap.wlan[*].mac.hcf.edca.edcaf[*].txopProcedure.typename = "QadTxopProcedure"
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

資料流：
  QadEdcaManager ──(每 T_mon 秒)──→ 讀取 queue/loss/delay
       │
       ├─ 偵測到飢餓 → 調整 AIFSN/CWmin/TXOP
       │
       └─ 飢餓解除 → 指數衰減恢復預設值
```

---

## 8. 實作優先順序建議

| 步驟 | 工作 | 預估複雜度 |
|------|------|-----------|
| 1 | 建立 `QadEdcaf` 和 `QadTxopProcedure` 子類別 | 低（各約 20 行） |
| 2 | 建立 Makefile 並確認可編譯空專案 | 低 |
| 3 | 實作 `getQueueLength()` + 快取指標 | 低 |
| 4 | 實作 `applyParameters()`（依賴步驟 1） | 中 |
| 5 | 實作 `getPacketLossRate()`（signal 訂閱） | 中 |
| 6 | 實作 `getAverageDelay()`（signal 訂閱） | 中 |
| 7 | 端對端測試：baseline 場景驗證參數不變 | 低 |
| 8 | 端對端測試：qad_edca 場景驗證動態調整 | 中 |
