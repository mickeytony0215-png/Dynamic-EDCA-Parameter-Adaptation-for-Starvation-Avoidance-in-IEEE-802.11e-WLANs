#!/bin/bash
# Run EVERY experiment from scratch — including the steady Baseline_* and
# TunedStatic_* configs that run_rerun_batch.sh deliberately skips.
#
# Use this for a full clean reproduction (e.g. empty results/ on a new machine).
# If you only changed QadEdcaManager code, run_rerun_batch.sh is enough and faster.
#
# Output dirs (overwrites the per-run .sca/.vec for each config it runs):
#   steady  (Baseline / TunedStatic / QadEdca)  -> simulations/results/
#   dynamic (Dynamic_*)                          -> simulations/results_dynamic/
#   allheavy stress test (AllHeavy_*)            -> simulations/results_allheavy/
# AllHeavy is NOT used by the main report figures; skip it with INCLUDE_ALLHEAVY=0.
#
# Knobs (env vars):
#   J=18              parallel pool size
#   INCLUDE_ALLHEAVY=1  set 0 to skip the stress-test configs
#   DRY_RUN=0           set 1 to list the job plan and exit (no simulation)
#
# Uses a manual `xargs -P` pool instead of opp_runall, because the project path
# contains spaces and opp_runall's generated Makefile mangles the quoting.
# NOTE: no `set -u` — OMNeT++'s setenv references unset vars and aborts under it.

source "$HOME/simulation/omnetpp-6.1/setenv" >/dev/null 2>&1
export PROJECT="$HOME/wirleess communication network project"
export INET="$HOME/simulation/inet4.5"
cd "$PROJECT/simulations" || exit 1

J="${J:-18}"
INCLUDE_ALLHEAVY="${INCLUDE_ALLHEAVY:-1}"
DRY_RUN="${DRY_RUN:-0}"
STAMP=$(date +%Y%m%d_%H%M%S)
export LOG="$PROJECT/results/runall_${STAMP}.log"
mkdir -p "$PROJECT/results" results_dynamic results_allheavy
echo "run-all batch start $(date)  (J=$J, allheavy=$INCLUDE_ALLHEAVY, dry=$DRY_RUN)" | tee "$LOG"

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

emit_jobs(){ # $1=scenario.ini $2=result-dir  $3..=configs
  local scen="$1" rdir="$2"; shift 2
  for c in "$@"; do
    local n; n=$(numruns "$c" "$scen")
    echo "  $c -> $n runs ($scen) -> $rdir" | tee -a "$LOG" >&2
    for ((i=0;i<n;i++)); do echo "$c $i $scen $rdir"; done
  done
}

{
  # --- steady (feeds analysis/transform.py + plot_figures.py) -> results/ ---
  emit_jobs baseline.ini results \
    Baseline_N5 Baseline_N10 Baseline_N15 Baseline_N20 Baseline_LoadSweep
  emit_jobs tuned_static.ini results \
    TunedStatic_N5 TunedStatic_N10 TunedStatic_N15 TunedStatic_N20
  emit_jobs qad_edca.ini results \
    QadEdca_N5 QadEdca_N10 QadEdca_N15 QadEdca_N20 \
    QadEdca_CwScaleSweep QadEdca_RecoveryFactorSweep \
    QadEdca_MonitorIntervalSweep QadEdca_ThresholdSweep

  # --- dynamic (feeds analysis/dynamic_timeseries.py) -> results_dynamic/ ---
  emit_jobs dynamic_load.ini results_dynamic \
    Dynamic_Baseline Dynamic_TunedStatic Dynamic_QadEdca

  # --- optional stress test (not in main report) -> results_allheavy/ ---
  if [[ "$INCLUDE_ALLHEAVY" == "1" ]]; then
    emit_jobs allheavy.ini results_allheavy \
      AllHeavy_Standard AllHeavy_Tuned AllHeavy_QadEdca
  fi
} > /tmp/runall_jobs.txt

TOTAL=$(wc -l < /tmp/runall_jobs.txt)
echo "total runs: $TOTAL  (parallel J=$J)" | tee -a "$LOG"

if [[ "$DRY_RUN" == "1" ]]; then
  echo "[DRY_RUN] job plan written to /tmp/runall_jobs.txt — nothing executed." | tee -a "$LOG"
  exit 0
fi

xargs -P"$J" -L1 bash -c 'run_one "$@"' _ < /tmp/runall_jobs.txt >>"$LOG" 2>&1

# fold per-config logs back into the main log, then clean up
cat "$LOG".* >>"$LOG" 2>/dev/null; rm -f "$LOG".*
echo "ALL DONE $(date)" | tee -a "$LOG"
touch "$PROJECT/results/runall_${STAMP}.DONE"
echo ""
echo "Next: regenerate figures (analysis/ + project venv):"
echo "  cd \"\$HOME/wirleess communication network project/analysis\" && source ../venv/bin/activate"
echo "  python transform.py ../simulations/results --out metrics_per_ac.csv"
echo "  python plot_figures.py metrics_per_ac.csv --outdir figures"
echo "  python dynamic_timeseries.py ../simulations/results_dynamic --outdir figures"
echo "  python positioning_figure.py"
