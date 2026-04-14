# QAD-EDCA 模擬執行指南

## 首次安裝（新電腦）

如果你的電腦還沒有 OMNeT++ 和 INET，只需要執行：

```bash
git clone https://github.com/mickeytony0215-png/Dynamic-EDCA-Parameter-Adaptation-for-Starvation-Avoidance-in-IEEE-802.11e-WLANs.git
cd Dynamic-EDCA-Parameter-Adaptation-for-Starvation-Avoidance-in-IEEE-802.11e-WLANs
chmod +x setup.sh
./setup.sh
```

腳本會自動安裝系統依賴、下載 OMNeT++ 6.1 和 INET 4.5、編譯所有東西、並驗證安裝是否成功。預計耗時 30~60 分鐘。

安裝完成後的環境：
- OMNeT++ 6.1 → `~/simulation/omnetpp-6.1/`
- INET 4.5 → `~/simulation/inet4.5/`

---

## 前置需求（已安裝的電腦）

- OMNeT++ 6.1（安裝在 `~/simulation/omnetpp-6.1/`）
- INET 4.5（安裝在 `~/simulation/inet4.5/`）

## 專案路徑

```
~/wirleess communication network project/
```

---

## 快速開始（推薦）

專案內有 `run.sh` 腳本，只需兩步：

### 步驟 1：進入專案目錄

```bash
cd "$HOME/wirleess communication network project"
```

### 步驟 2：執行模擬

```bash
./run.sh <Config名稱> <場景檔名> [run編號] [--cli]
```

---

## 兩種模式

### GUI 模式（預設） — 可視化模擬

直接執行即可，會打開 OMNeT++ Qtenv 圖形介面：

```bash
./run.sh Baseline_N10 baseline
```

GUI 介面中可以：
- 看到完整網路拓撲（AP、VO/VI/BE/BK 站台位置）
- 用播放按鈕逐步或連續執行模擬
- 即時觀察封包傳送動畫和無線信號範圍
- 雙擊模組查看內部參數和即時統計
- 用 Inspector 面板檢視佇列長度、延遲等指標

### CLI 模式 — 批次執行（跑數據用）

加上 `--cli` 參數，模擬在終端機直接跑完，速度較快，適合批次收集數據：

```bash
./run.sh Baseline_N10 baseline 0 --cli
```

---

## 執行範例

```bash
# GUI：Baseline 10 站台
./run.sh Baseline_N10 baseline

# GUI：QAD-EDCA 10 站台
./run.sh QadEdca_N10 qad_edca

# GUI：高負載 Baseline
./run.sh HighLoad_Baseline high_load

# GUI：高負載 QAD-EDCA
./run.sh HighLoad_QadEdca high_load

# GUI：指定 run 編號
./run.sh Baseline_N10 baseline 3

# CLI：批次執行（不開 GUI）
./run.sh Baseline_N10 baseline 0 --cli
./run.sh QadEdca_N10 qad_edca 0 --cli
```

---

## 可用的 Config 名稱一覽

### Baseline 場景（場景檔：`baseline`）

| Config 名稱 | 站台數 | 說明 |
|-------------|--------|------|
| `Baseline_N5` | 5 | 小規模，不同 VO/VI 比例 |
| `Baseline_N10` | 10 | 中規模，不同 VO/VI 比例 |
| `Baseline_N15` | 15 | 中大規模 |
| `Baseline_N20` | 20 | 大規模 |
| `Baseline_LoadSweep` | 10 | 固定站台數，不同 BE 流量負載 |

### QAD-EDCA 場景（場景檔：`qad_edca`）

| Config 名稱 | 站台數 | 說明 |
|-------------|--------|------|
| `QadEdca_N10` | 10 | 與 Baseline_N10 對照 |
| `QadEdca_N20` | 20 | 與 Baseline_N20 對照 |
| `QadEdca_ThresholdSweep` | 10 | 掃描不同 Q_th / P_th 閾值 |

### 高負載場景（場景檔：`high_load`）

| Config 名稱 | 說明 |
|-------------|------|
| `HighLoad_Baseline` | 標準 EDCA 極端高負載 |
| `HighLoad_QadEdca` | QAD-EDCA 極端高負載 |
| `HighLoad_Progressive` | 漸進式負載增加 |

每個 Config 可能有多個 run（不同的站台比例組合），用第三個參數指定，例如 `./run.sh Baseline_N10 baseline 2`。

---

## 編譯（只需做一次）

首次使用或修改了 `.cc` / `.h` 原始碼後才需要重新編譯：

```bash
cd "$HOME/wirleess communication network project"
source ~/simulation/omnetpp-6.1/setenv
opp_makemake -f --deep -e cc -O out -o edcafairness --make-so -X venv -X results -X analysis -X references -X proposal -X docs -I$HOME/simulation/inet4.5/src -L$HOME/simulation/inet4.5/src -lINET -KINET_PROJ=$HOME/simulation/inet4.5
make -j$(nproc)
```

成功後會產生 `out/clang-release/libedcafairness.so`。

> **注意**：上面的 `opp_makemake` 指令必須在同一行，不能換行。

---

## 模擬結果

結果存在 `simulations/results/` 目錄下，格式為 SQLite（`.sca` / `.vec` 檔案）。

可用 `scavetool` 或 Python（`omnetpp.scave`）讀取分析。

---

## 常見問題

### Q: 出現 "SceneOsgVisualizer not found"
已在 `omnetpp.ini` 中停用。如果仍出現，確認你用的是最新的 `omnetpp.ini`。

### Q: 編譯時出現 "you have both .cc and .cpp files"
重新執行 `opp_makemake` 時加上 `-e cc` 參數（已包含在上方指令中）。

### Q: 想修改模擬時間
修改 `simulations/omnetpp.ini` 中的 `sim-time-limit`（預設 30s）。

### Q: GUI 打不開 / 出現 "cannot connect to display"
確認你有 X Window 環境（桌面環境或 X forwarding）。SSH 連線需加 `-X` 參數：`ssh -X user@host`。

### Q: 指令被換行拆斷，出現奇怪的錯誤
請用 `./run.sh` 腳本，不要手動貼長指令。

### Q: GUI 模式太慢，想快速跑完收數據
加 `--cli` 參數：`./run.sh Baseline_N10 baseline 0 --cli`
