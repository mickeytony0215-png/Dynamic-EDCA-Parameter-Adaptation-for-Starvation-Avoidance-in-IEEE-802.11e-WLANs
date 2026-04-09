# EDCA Fairness Project

IEEE 802.11e EDCA starvation avoidance via dynamic parameter adaptation (QAD-EDCA).  
NSYSU Wireless Communications Network — Term Project, Spring 2026.

## Quick Start

```bash
# 1. Source OMNeT++ environment
source ~/simulation/omnetpp-6.1/setenv

# 2. Run baseline QoS showcase to verify setup
cd ~/simulation/inet4.5/showcases/wireless/qos
opp_run -m -u Cmdenv -c Qos -n .:../../../src -l ../../../src/INET omnetpp.ini

# 3. Run project simulations (after building)
cd simulations/
opp_run -m -u Cmdenv -c Baseline_N10 omnetpp.ini

# 4. Generate sample figures
cd ../analysis/
python plot_figures.py --sample --outdir ../results/figures
```

## Structure

| Directory | Contents |
|-----------|----------|
| `proposal/` | Project proposal (Markdown) |
| `simulations/` | NED topology and .ini configs |
| `simulations/scenarios/` | Baseline, QAD-EDCA, and high-load configs |
| `src/` | QAD-EDCA C++ module (NED + header + implementation) |
| `analysis/` | Python scripts for parsing results and plotting |
| `results/` | Simulation output (generated) |
| `references/` | Reference papers |
| `docs/` | Final report draft |

## Environment

- **OMNeT++ 6.1**: `~/simulation/omnetpp-6.1/`
- **INET 4.5**: `~/simulation/inet4.5/`
- **Python**: 3.10+ with numpy, pandas, matplotlib

## Timeline

| Weeks | Task |
|-------|------|
| 1--2 (Apr 15--28) | Baseline simulation and starvation demonstration |
| 3--4 (Apr 29--May 12) | QAD-EDCA implementation |
| 5--6 (May 13--26) | Full experiments and data collection |
| 7--8 (May 27--Jun 10) | Analysis, report, presentation |
