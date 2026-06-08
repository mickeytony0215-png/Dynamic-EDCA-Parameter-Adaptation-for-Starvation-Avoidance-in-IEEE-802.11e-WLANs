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

# GUI：動態負載 QAD-EDCA（calm→surge→calm）
./run.sh Dynamic_QadEdca dynamic_load

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
| `QadEdca_N5` | 5 | 與 Baseline_N5 對照 |
| `QadEdca_N10` | 10 | 與 Baseline_N10 對照 |
| `QadEdca_N15` | 15 | 與 Baseline_N15 對照 |
| `QadEdca_N20` | 20 | 與 Baseline_N20 對照 |
| `QadEdca_ThresholdSweep` | 10 | 掃描不同 Q_th / P_th 閾值（報告 §敏感度）|
| `QadEdca_CwScaleSweep` | 10 | 掃描 cwScaleFactor（α_CW）|
| `QadEdca_RecoveryFactorSweep` | 10 | 掃描 recoveryFactor（γ）|
| `QadEdca_MonitorIntervalSweep` | 10 | 掃描 monitorInterval（T_mon）|

### Tuned Static 場景（場景檔：`tuned_static`）

| Config 名稱 | 站台數 | 說明 |
|-------------|--------|------|
| `TunedStatic_N5/N10/N15/N20` | 5–20 | 手調靜態 EDCA 對照 |

### 動態負載場景（場景檔：`dynamic_load`）

| Config 名稱 | 說明 |
|-------------|------|
| `Dynamic_Baseline` | Standard EDCA，calm→surge→calm 60s |
| `Dynamic_TunedStatic` | Tuned Static，同上 |
| `Dynamic_QadEdca` | QAD-EDCA，同上 |

> `Dynamic_Base` 是被上面三個繼承的共用基底設定，不要單獨執行。
> 動態場景的結果會輸出到 `simulations/results_dynamic/`（與穩態的 `results/` 分開）。

### 全飽和壓測場景（場景檔：`allheavy`）

| Config 名稱 | 說明 |
|-------------|------|
| `AllHeavy_Standard / AllHeavy_Tuned / AllHeavy_QadEdca` | 4VO/4VI/4BE/4BK 最高競爭 |

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

結果存在以下目錄，格式為 SQLite（`.sca` / `.vec` 檔案）：
- 穩態場景（Baseline / TunedStatic / QadEdca）→ `simulations/results/`
- 動態場景（Dynamic_*）→ `simulations/results_dynamic/`

可用 `scavetool` 或下方的分析腳本讀取。

---

## 完整重現報告的數字與圖表

上面是跑「單一 config」。要重現報告中**平均過的表格**與 `analysis/figures/` 裡的**所有圖**，分兩階段。

### 階段 A：批次跑完所有 runs

專案內 `run_rerun_batch.sh` 用平行 pool 把 QAD 與動態場景的**每一個 run** 跑完：

```bash
cd "$HOME/wirleess communication network project"
./run_rerun_batch.sh
```

- 重跑 `QadEdca_*`（N5/N10/N15/N20 + ThresholdSweep + CwScale/RecoveryFactor/MonitorInterval 三個 sweep）→ 覆寫 `simulations/results/`
- 重跑 `Dynamic_Baseline / Dynamic_TunedStatic / Dynamic_QadEdca` → 輸出到 `simulations/results_dynamic/`
- 平行度 `J=18`（可在腳本內改）；log 在 `results/rerun_<時間戳>.log`，全部跑完會產生 `results/rerun_<時間戳>.DONE`

> **為何不含 `Baseline_*` / `TunedStatic_*`？** 它們不會實例化 QAD manager，程式碼修改不影響其結果，所以批次腳本刻意跳過。repo 內的 `simulations/results/` 已附這些結果，可直接用。
> **要一次跑完「全部」實驗**（含 Baseline / TunedStatic，每個 config 的所有 run）→ 用完整版腳本
> `run_all_batch.sh`（共 445 runs，同樣 J=18 平行）：
> ```bash
> ./run_all_batch.sh                  # 全部 445 runs
> # 旋鈕：DRY_RUN=1 只列計畫不執行｜INCLUDE_ALLHEAVY=0 跳過壓測｜J=8 降平行度
> ```
> 輸出：穩態→`results/`、動態→`results_dynamic/`、壓測→`results_allheavy/`；跑完產生 `results/runall_<時間戳>.DONE`，並印出接續產圖的指令。

### 階段 B：用分析腳本產出 CSV 與圖（使用專案 venv）

```bash
cd "$HOME/wirleess communication network project/analysis"
source ../venv/bin/activate          # 已內含 pandas / numpy / matplotlib

# 1) 穩態：原始 .sca → 寬表 CSV → 圖（吞吐/延遲/丟包/規模/公平性/sweep）
python transform.py ../simulations/results --out metrics_per_ac.csv
python plot_figures.py metrics_per_ac.csv --outdir figures

# 2) 動態：時間序列圖 + 相位摘要表
python dynamic_timeseries.py ../simulations/results_dynamic --outdir figures

# 3) 定位圖（純概念圖，不需資料）
python positioning_figure.py
```

- 圖輸出到 `analysis/figures/`（同時產生 PDF + PNG），即 `report.tex` 引用的那些檔。
- `parse_results.py <results_dir> -o summary.csv` 是另一個快速摘要工具，非主要產圖流程。

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
