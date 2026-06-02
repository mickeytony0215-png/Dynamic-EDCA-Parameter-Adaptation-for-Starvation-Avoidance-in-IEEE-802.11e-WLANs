#!/bin/bash
# Re-run all QAD-dependent experiments after the TXOP-confound fix in
# QadEdcaManager.cc. Baseline_* / TunedStatic_* steady configs are NOT re-run
# (they never instantiate the manager, so the code change cannot affect them).
#
# Steady QAD configs overwrite the now-invalid May-28 .sca in simulations/results/.
# Dynamic configs go to simulations/results_dynamic/ (time-series, separate analysis).
#
# Uses a manual xargs -P pool instead of opp_runall, because the project path
# contains spaces and opp_runall's generated Makefile mangles the quoting.
# NOTE: no `set -u` — OMNeT++'s setenv references unset vars and aborts under it.
source "$HOME/simulation/omnetpp-6.1/setenv" >/dev/null 2>&1
export PROJECT="$HOME/wirleess communication network project"
export INET="$HOME/simulation/inet4.5"
cd "$PROJECT/simulations" || exit 1
J=18
STAMP=$(date +%Y%m%d_%H%M%S)
export LOG="$PROJECT/results/rerun_${STAMP}.log"
mkdir -p "$PROJECT/results" results_dynamic
echo "rerun batch start $(date)" | tee "$LOG"

numruns(){ # $1=config $2=scenario.ini
  opp_run -m -u Cmdenv -c "$1" -n "$PROJECT:$INET/src" \
    -l "$INET/src/INET" -l "$PROJECT/out/clang-release/edcafairness" \
    -q numruns omnetpp.ini "scenarios/$2" 2>/dev/null \
    | grep -oE 'Number of runs: [0-9]+' | grep -oE '[0-9]+'
}

run_one(){ # $1=config $2=runidx $3=scenario.ini $4=result-dir
  opp_run -m -u Cmdenv -c "$1" -r "$2" -n "$PROJECT:$INET/src" \
    -l "$INET/src/INET" -l "$PROJECT/out/clang-release/edcafairness" \
    --result-dir="$4" --cmdenv-express-mode=true --cmdenv-status-frequency=120s \
    omnetpp.ini "scenarios/$3" >>"$LOG.$1" 2>&1
  echo "ok $1 r$2"
}
export -f run_one

emit_jobs(){
  local scen="$1" rdir="$2"; shift 2
  for c in "$@"; do
    local n; n=$(numruns "$c" "$scen")
    echo "  $c -> $n runs ($scen)" | tee -a "$LOG" >&2
    for ((i=0;i<n;i++)); do echo "$c $i $scen $rdir"; done
  done
}

{
  emit_jobs qad_edca.ini results \
    QadEdca_N5 QadEdca_N10 QadEdca_N15 QadEdca_N20 \
    QadEdca_CwScaleSweep QadEdca_RecoveryFactorSweep \
    QadEdca_MonitorIntervalSweep QadEdca_ThresholdSweep
  emit_jobs dynamic_load.ini results_dynamic \
    Dynamic_Baseline Dynamic_TunedStatic Dynamic_QadEdca
} > /tmp/rerun_jobs.txt

TOTAL=$(wc -l < /tmp/rerun_jobs.txt)
echo "total runs: $TOTAL  (parallel J=$J)" | tee -a "$LOG"
xargs -P"$J" -L1 bash -c 'run_one "$@"' _ < /tmp/rerun_jobs.txt >>"$LOG" 2>&1

cat "$LOG".QadEdca_* "$LOG".Dynamic_* >>"$LOG" 2>/dev/null; rm -f "$LOG".QadEdca_* "$LOG".Dynamic_*
echo "ALL DONE $(date)" | tee -a "$LOG"
touch "$PROJECT/results/rerun_${STAMP}.DONE"
