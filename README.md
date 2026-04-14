# EDCA Fairness Project

IEEE 802.11e EDCA starvation avoidance via dynamic parameter adaptation (QAD-EDCA).  
NSYSU Wireless Communications Network — Term Project, Spring 2026.

## Quick Start

```bash
cd ~/wirleess\ communication\ network\ project

# Build (first time only)
source ~/simulation/omnetpp-6.1/setenv
opp_makemake -f --deep -e cc -O out -o edcafairness --make-so -X venv -X results -X analysis -X references -X proposal -X docs -I$HOME/simulation/inet4.5/src -L$HOME/simulation/inet4.5/src -lINET -KINET_PROJ=$HOME/simulation/inet4.5
make -j$(nproc)

# Run (GUI)
./run.sh Baseline_N10 baseline
./run.sh QadEdca_N10 qad_edca

# Run (CLI, for batch)
./run.sh Baseline_N10 baseline 0 --cli
```

See `HOW_TO_RUN.md` for detailed instructions.

## Structure

| Directory | Contents |
|-----------|----------|
| `src/` | QAD-EDCA C++ modules (QadEdcaManager, QadEdcaf, QadTxopProcedure, QadEdca, QadHcf) |
| `simulations/` | NED topology and .ini configs |
| `simulations/scenarios/` | Baseline, QAD-EDCA, and high-load scenario configs |
| `analysis/` | Python scripts for parsing results and plotting |
| `results/` | Simulation output (generated, gitignored) |
| `proposal/` | Project proposal (Markdown + LaTeX) |
| `docs/` | Design docs, dev reports, review reports, presentation outlines |
| `references/` | Reference papers |

## Environment

- **OMNeT++ 6.1**: `~/simulation/omnetpp-6.1/`
- **INET 4.5**: `~/simulation/inet4.5/`
- **Python**: 3.10+ with numpy, pandas, matplotlib

## Timeline

| Weeks | Task |
|-------|------|
| 1--2 (Apr 15--28) | ~~Baseline simulation and starvation demonstration~~ ✅ |
| 3--4 (Apr 29--May 12) | ~~QAD-EDCA implementation~~ ✅ |
| 5--6 (May 13--26) | Full experiments and data collection |
| 7--8 (May 27--Jun 10) | Analysis, report, presentation |
