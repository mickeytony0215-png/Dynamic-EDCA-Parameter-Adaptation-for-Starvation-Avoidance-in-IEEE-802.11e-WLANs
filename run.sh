#!/bin/bash
# QAD-EDCA 模擬執行腳本
# 用法: ./run.sh <config名稱> <場景檔> [run編號] [--cli]
# 範例:
#   ./run.sh Baseline_N10 baseline             # GUI 模式（預設）
#   ./run.sh QadEdca_N10 qad_edca              # GUI 模式
#   ./run.sh Baseline_N10 baseline 0 --cli     # 命令列模式（批次用）
#   ./run.sh HighLoad_Baseline high_load 3     # 指定 run #3

CONFIG=${1:?"請指定 config 名稱，例如: Baseline_N10 或 QadEdca_N10"}
SCENARIO=${2:?"請指定場景檔名（不含路徑和 .ini），例如: baseline 或 qad_edca"}
RUN=${3:-0}

# 判斷是否使用 CLI 模式
UI="Qtenv"
if [[ "$3" == "--cli" || "$4" == "--cli" ]]; then
    UI="Cmdenv"
fi
# 如果第三個參數是 --cli，run 用預設值 0
if [[ "$3" == "--cli" ]]; then
    RUN=0
fi

PROJECT="$(cd "$(dirname "$0")" && pwd)"
source "$HOME/simulation/omnetpp-6.1/setenv" 2>/dev/null

cd "$PROJECT/simulations"

echo "=== 執行模擬 ==="
echo "  Config:  $CONFIG"
echo "  場景檔:  scenarios/${SCENARIO}.ini"
echo "  Run:     $RUN"
echo "  介面:    $UI"
echo ""

opp_run -m -u "$UI" \
  -c "$CONFIG" \
  -r "$RUN" \
  -n "$PROJECT:$HOME/simulation/inet4.5/src" \
  -l "$HOME/simulation/inet4.5/src/INET" \
  -l "$PROJECT/out/clang-release/edcafairness" \
  omnetpp.ini "scenarios/${SCENARIO}.ini"
