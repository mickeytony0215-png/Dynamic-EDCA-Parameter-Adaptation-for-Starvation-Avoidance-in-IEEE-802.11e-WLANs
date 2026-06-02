#!/usr/bin/env python3
"""
Dynamic (transient) scenario analysis — ensemble-averaged time series.

Reads the SQLite .vec files produced by the Dynamic_* configs (dynamic_load.ini)
and produces:

  fig_dynamic_be_throughput   BE throughput over time, 3 schemes (the "BE rescue")
  fig_dynamic_hi_delay        VO+VI mean delay over time, 3 schemes (the "VO/VI tax")
  fig_dynamic_qad_adapt       QAD adaptation trace (AIFSN / CWmin / starvation)

plus a per-phase summary table (printed + CSV).

Load profile: calm [0,20) / surge [20,40) / calm [40,60).

Usage:
    python dynamic_timeseries.py <results_dynamic_dir> [--outdir figures]
"""
import argparse
import glob
import os
import re
import sqlite3
from collections import defaultdict

import matplotlib.pyplot as plt
import numpy as np

plt.rcParams.update({
    "font.size": 12, "font.family": "serif", "axes.labelsize": 14,
    "axes.titlesize": 14, "legend.fontsize": 11,
    "xtick.labelsize": 12, "ytick.labelsize": 12,
    "figure.dpi": 150, "savefig.dpi": 300,
})

SCHEME = {
    "Dynamic_Baseline":    ("Standard EDCA",    "#e74c3c", "--"),
    "Dynamic_TunedStatic": ("Tuned Static EDCA", "#f39c12", ":"),
    "Dynamic_QadEdca":     ("QAD-EDCA",          "#2980b9", "-"),
}
SIM_T = 60.0
BIN = 0.5                       # s, time-series bin width
PHASES = [("Calm 1", 0, 20), ("Surge", 20, 40), ("Calm 2", 40, 60)]
APP_AC = {0: "VO", 1: "VI", 2: "BE", 3: "BK"}


def _read_vector(con, module_exact, vname):
    rows = con.execute(
        """SELECT d.simtimeRaw, d.value FROM vector v JOIN vectorData d
           ON v.vectorId = d.vectorId
           WHERE v.moduleName = ? AND v.vectorName = ? ORDER BY d.simtimeRaw""",
        (module_exact, vname)).fetchall()
    if not rows:
        return np.array([]), np.array([])
    return (np.array([r[0] for r in rows]) / 1e12,
            np.array([r[1] for r in rows], dtype=float))


def _bin_mean(t, y, edges):
    """Mean of samples falling in each [edge_i, edge_{i+1}) bin (NaN if empty)."""
    out = np.full(len(edges) - 1, np.nan)
    if t.size:
        idx = np.digitize(t, edges) - 1
        for b in range(len(edges) - 1):
            sel = y[idx == b]
            if sel.size:
                out[b] = sel.mean()
    return out


def _files_by_config(results_dir):
    by = defaultdict(list)
    for f in sorted(glob.glob(os.path.join(results_dir, "Dynamic_*.vec"))):
        cfg = re.sub(r"-#\d+\.vec$", "", os.path.basename(f))
        by[cfg].append(f)
    return by


def _ensemble(files, module, vname, edges):
    """Average the per-rep binned series across reps."""
    series = []
    for f in files:
        con = sqlite3.connect(f)
        try:
            t, y = _read_vector(con, module, vname)
        finally:
            con.close()
        series.append(_bin_mean(t, y, edges))
    if not series:
        return np.full(len(edges) - 1, np.nan)
    return np.nanmean(np.vstack(series), axis=0)


def _shade_phases(ax):
    ax.axvspan(20, 40, color="#cccccc", alpha=0.35, lw=0)
    ax.text(30, ax.get_ylim()[1] * 0.94, "surge", ha="center",
            fontsize=10, color="#555555")


def _save(fig, outdir, name):
    for ext in ("pdf", "png"):
        fig.savefig(os.path.join(outdir, f"{name}.{ext}"), bbox_inches="tight")
    plt.close(fig)
    print(f"  -> {name}.pdf/.png")


def plot_be_throughput(by, edges, centers, outdir):
    fig, ax = plt.subplots(figsize=(9, 5))
    for cfg, (label, color, ls) in SCHEME.items():
        if cfg not in by:
            continue
        y = _ensemble(by[cfg], "EdcaFairnessNetwork.server.app[2]",
                      "throughput:vector", edges) / 1e6
        ax.plot(centers, y, color=color, ls=ls, lw=2, label=label)
    ax.set_ylim(0, 8)          # headroom so the legend clears the ~6 Mbps lines
    _shade_phases(ax)
    ax.set(xlabel="Simulation Time (s)", ylabel="AC_BE Throughput (Mbps)",
           title="Best-Effort Throughput under a Transient High-Priority Surge",
           xlim=(0, SIM_T))
    ax.legend(loc="upper right", framealpha=0.95)
    ax.grid(alpha=0.3)
    _save(fig, outdir, "fig_dynamic_be_throughput")


def plot_hi_delay(by, edges, centers, outdir):
    fig, ax = plt.subplots(figsize=(9, 5))
    # Delay spans ~3 ms (Tuned) to ~240 ms (Standard surge spikes), so a linear
    # axis squashes the low Tuned line onto the x-axis. Use a log y-axis and
    # emphasise Tuned (thicker + markers, drawn on top) so all three separate.
    emph = {
        "Dynamic_Baseline":    dict(lw=1.8, zorder=2),
        "Dynamic_TunedStatic": dict(lw=2.8, zorder=5, marker="o", markevery=8, ms=4),
        "Dynamic_QadEdca":     dict(lw=2.2, zorder=4),
    }
    for cfg, (label, color, ls) in SCHEME.items():
        if cfg not in by:
            continue
        # mean of (VO, VI) per-bin delay, ms
        vo = _ensemble(by[cfg], "EdcaFairnessNetwork.server.app[0]",
                       "endToEndDelay:vector", edges) * 1000
        vi = _ensemble(by[cfg], "EdcaFairnessNetwork.server.app[1]",
                       "endToEndDelay:vector", edges) * 1000
        hi = np.nanmean(np.vstack([vo, vi]), axis=0)
        ax.plot(centers, hi, color=color, ls=ls, label=label, **emph.get(cfg, {}))
    # 150 ms VO QoS bound (ITU-T G.114 / 3GPP 5QI=1).
    ax.axhline(150, color="#777777", ls=(0, (6, 4)), lw=1.2, zorder=1)
    ax.text(0.5, 165, "150 ms VO QoS bound", fontsize=9, color="#666666")
    ax.set_yscale("log")
    ax.set_ylim(1, 600)
    _shade_phases(ax)
    ax.set(xlabel="Simulation Time (s)",
           ylabel="AC_VO/VI Mean Delay (ms, log scale)",
           title="High-Priority (VO/VI) Delay: Standard Spikes above QoS under Surge",
           xlim=(0, SIM_T))
    ax.legend(loc="upper right")
    ax.grid(alpha=0.3, which="both")
    _save(fig, outdir, "fig_dynamic_hi_delay")


def plot_qad_adapt(by, edges, centers, outdir):
    cfg = "Dynamic_QadEdca"
    if cfg not in by:
        return
    M = "EdcaFairnessNetwork.qadManager"
    aifsn_be = _ensemble(by[cfg], M, "adjustedAifsnBe:vector", edges)
    aifsn_bk = _ensemble(by[cfg], M, "adjustedAifsnBk:vector", edges)
    cw_vo = _ensemble(by[cfg], M, "adjustedCwMinVo:vector", edges)
    cw_vi = _ensemble(by[cfg], M, "adjustedCwMinVi:vector", edges)
    starv = _ensemble(by[cfg], M, "starvationDetected:vector", edges)

    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(9, 7), sharex=True)
    ax1.plot(centers, aifsn_be, color="#2ecc71", lw=2, label="AIFSN BE")
    ax1.plot(centers, aifsn_bk, color="#16a085", lw=2, ls="--", label="AIFSN BK")
    ax1.plot(centers, cw_vo, color="#e74c3c", lw=2, label="CWmin VO")
    ax1.plot(centers, cw_vi, color="#c0392b", lw=2, ls="--", label="CWmin VI")
    ax1.set(ylabel="Adapted EDCA parameter",
            title="QAD-EDCA Runtime Adaptation")
    ax1.legend(loc="center right", ncol=2, fontsize=10)
    ax1.grid(alpha=0.3)
    _shade_phases(ax1)

    ax2.fill_between(centers, starv, color="#9b59b6", alpha=0.6, step="mid")
    ax2.set(xlabel="Simulation Time (s)",
            ylabel="Starvation detected\n(fraction of reps)",
            xlim=(0, SIM_T), ylim=(0, 1.05))
    ax2.grid(alpha=0.3)
    _shade_phases(ax2)
    _save(fig, outdir, "fig_dynamic_qad_adapt")


def phase_summary(by, outdir):
    """Per-phase per-AC throughput + VO/VI delay, ensemble mean, CSV + print."""
    fine = np.arange(0, SIM_T + 1e-9, BIN)
    centers = (fine[:-1] + fine[1:]) / 2
    rows = []
    for cfg, (label, _c, _l) in SCHEME.items():
        if cfg not in by:
            continue
        tput = {ac: _ensemble(by[cfg], f"EdcaFairnessNetwork.server.app[{i}]",
                              "throughput:vector", fine) / 1e6
                for i, ac in APP_AC.items()}
        dly = {ac: _ensemble(by[cfg], f"EdcaFairnessNetwork.server.app[{i}]",
                             "endToEndDelay:vector", fine) * 1000
               for i, ac in APP_AC.items() if ac in ("VO", "VI")}
        for pname, lo, hi in PHASES:
            m = (centers >= lo) & (centers < hi)
            row = {"scheme": label, "phase": pname}
            for ac in APP_AC.values():
                row[f"{ac}_tput_mbps"] = round(float(np.nanmean(tput[ac][m])), 3)
            for ac in ("VO", "VI"):
                row[f"{ac}_delay_ms"] = round(float(np.nanmean(dly[ac][m])), 2)
            rows.append(row)

    # print compact table
    print("\n=== Per-phase summary (ensemble mean) ===")
    hdr = ["scheme", "phase", "BE_tput_mbps", "VO_delay_ms", "VI_delay_ms"]
    print("  " + "".join(f"{h:>16}" for h in hdr))
    for r in rows:
        print("  " + "".join(f"{str(r.get(h,'')):>16}" for h in hdr))

    csv = os.path.join(outdir, "dynamic_phase_summary.csv")
    if rows:
        keys = list(rows[0].keys())
        with open(csv, "w") as fh:
            fh.write(",".join(keys) + "\n")
            for r in rows:
                fh.write(",".join(str(r[k]) for k in keys) + "\n")
        print(f"  -> {csv}")


def main():
    p = argparse.ArgumentParser()
    p.add_argument("results_dir")
    p.add_argument("--outdir", "-o", default="figures")
    args = p.parse_args()
    os.makedirs(args.outdir, exist_ok=True)

    by = _files_by_config(args.results_dir)
    if not by:
        raise SystemExit(f"No Dynamic_*.vec in {args.results_dir}")
    for cfg, fs in by.items():
        print(f"{cfg}: {len(fs)} reps")

    edges = np.arange(0, SIM_T + 1e-9, BIN)
    centers = (edges[:-1] + edges[1:]) / 2
    plot_be_throughput(by, edges, centers, args.outdir)
    plot_hi_delay(by, edges, centers, args.outdir)
    plot_qad_adapt(by, edges, centers, args.outdir)
    phase_summary(by, args.outdir)
    print("Done.")


if __name__ == "__main__":
    main()
