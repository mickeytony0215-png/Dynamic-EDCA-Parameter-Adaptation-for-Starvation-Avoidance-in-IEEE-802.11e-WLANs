#!/usr/bin/env python3
"""
Generate publication-quality figures for EDCA fairness analysis.

Usage:
    python plot_figures.py [results_csv] [--outdir figures] [--sample]
"""

import argparse
import os
import re
from dataclasses import dataclass, field

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

STYLE = {
    "font.size": 12, "font.family": "serif", "axes.labelsize": 14,
    "axes.titlesize": 14, "legend.fontsize": 11,
    "xtick.labelsize": 12, "ytick.labelsize": 12,
    "figure.figsize": (8, 5), "figure.dpi": 150,
    "savefig.dpi": 300,
}
plt.rcParams.update(STYLE)

AC_ORDER = ["AC_VO", "AC_VI", "AC_BE", "AC_BK"]
AC_COLORS = dict(zip(AC_ORDER, ["#e74c3c", "#3498db", "#2ecc71", "#95a5a6"]))


@dataclass
class BarSpec:
    metric: str
    ylabel: str
    title: str
    filename: str
    hlines: dict = field(default_factory=dict)


BAR_CHARTS = [
    BarSpec("throughput_mbps", "Throughput (Mbps)", "Per-AC Throughput Comparison",
            "throughput_comparison"),
    BarSpec("avg_delay_ms", "Average Delay (ms)", "Per-AC Delay Comparison",
            "delay_comparison", {"VO bound (150ms)": 150, "VI bound (150ms)": 150}),
    BarSpec("loss_rate_pct", "Packet Loss Rate (%)", "Per-AC Packet Loss Rate",
            "packet_loss"),
]


def _save(fig: plt.Figure, outdir: str, name: str):
    for ext in ("pdf", "png"):
        fig.savefig(os.path.join(outdir, f"{name}.{ext}"), bbox_inches="tight")
    plt.close(fig)
    print(f"  -> {name}.pdf")


def plot_bar(df: pd.DataFrame, spec: BarSpec, outdir: str):
    """Generic grouped bar chart driven by a BarSpec descriptor."""
    fig, ax = plt.subplots()
    schemes = df["scheme"].unique()
    x = np.arange(len(AC_ORDER))
    w = 0.8 / len(schemes)

    for i, scheme in enumerate(schemes):
        s = df[df["scheme"] == scheme]
        vals = [s.loc[s["ac"] == ac, spec.metric].mean() for ac in AC_ORDER]
        errs = [s.loc[s["ac"] == ac, spec.metric].std() for ac in AC_ORDER]
        ax.bar(x + i * w, vals, w, yerr=errs, label=scheme, alpha=0.85, capsize=3)

    for label, yval in spec.hlines.items():
        ax.axhline(y=yval, linestyle="--", alpha=0.5, label=label)

    ax.set(xlabel="Access Category", ylabel=spec.ylabel, title=spec.title)
    ax.set_xticks(x + w * (len(schemes) - 1) / 2, AC_ORDER)
    ax.legend()
    ax.grid(axis="y", alpha=0.3)
    _save(fig, outdir, spec.filename)


def plot_fairness(df: pd.DataFrame, outdir: str):
    """Jain's Fairness Index vs. high-priority STA proportion."""
    fig, ax = plt.subplots()
    for scheme in df["scheme"].unique():
        s = df[df["scheme"] == scheme].sort_values("hi_priority_ratio")
        ax.plot(s["hi_priority_ratio"] * 100, s["jains_index"],
                marker="o", label=scheme, linewidth=2)
    ax.set(xlabel="High-Priority STA Proportion (%)",
           ylabel="Jain's Fairness Index",
           title="Fairness Index vs. High-Priority Load", ylim=(0, 1.05))
    ax.legend()
    ax.grid(alpha=0.3)
    _save(fig, outdir, "fairness_index")


def plot_timeline(df_ts: pd.DataFrame, outdir: str):
    """Queue occupancy and throughput over time."""
    fig, axes = plt.subplots(2, 1, figsize=(10, 8), sharex=True)
    fields = [("queue_occupancy", "Queue Occupancy Ratio", "Queue Dynamics Over Time"),
              ("throughput_inst", "Instantaneous Throughput (Mbps)", None)]
    for ax, (col, ylabel, title) in zip(axes, fields):
        for ac in AC_ORDER:
            s = df_ts[df_ts["ac"] == ac]
            if not s.empty:
                ax.plot(s["time"], s[col], label=ac, color=AC_COLORS[ac], lw=1.5)
        ax.set_ylabel(ylabel)
        if title:
            ax.set_title(title)
            ax.axhline(y=0.8, color="red", ls="--", alpha=0.5, label="Threshold")
        ax.legend(loc="upper right")
        ax.grid(alpha=0.3)
    axes[-1].set_xlabel("Simulation Time (s)")
    _save(fig, outdir, "starvation_timeline")


def plot_n_scaling(df: pd.DataFrame, outdir: str):
    """Throughput / delay / loss versus number of stations (N=5,10,15,20)."""
    nx = df[df["configName"].str.match(r"(Baseline|QadEdca)_N\d+$", na=False)].copy()
    if nx.empty:
        return
    nx["N"] = nx["configName"].str.extract(r"_N(\d+)$").astype(int)
    metrics = [("throughput_mbps", "Throughput (Mbps)"),
               ("avg_delay_ms",    "Average Delay (ms)"),
               ("loss_rate_pct",   "Packet Loss Rate (%)")]
    fig, axes = plt.subplots(1, 3, figsize=(18, 5))
    for ax, (col, ylabel) in zip(axes, metrics):
        for scheme in nx["scheme"].unique():
            ls = "-" if scheme == "QAD-EDCA" else "--"
            for ac in AC_ORDER:
                s = (nx[(nx["scheme"] == scheme) & (nx["ac"] == ac)]
                     .groupby("N")[col].mean().reset_index())
                ax.plot(s["N"], s[col], marker="o", ls=ls,
                        color=AC_COLORS[ac], label=f"{scheme} - {ac}", alpha=0.85)
        ax.set(xlabel="Number of Stations", ylabel=ylabel)
        ax.set_xticks(sorted(nx["N"].unique()))
        ax.grid(alpha=0.3)
        if col == "avg_delay_ms":
            ax.axhline(y=150, ls=":", color="black", alpha=0.5, label="VO/VI bound 150ms")
    axes[0].legend(loc="best", fontsize=9, ncol=2)
    fig.suptitle("Scale Effect: Per-AC Metrics vs. Network Size")
    _save(fig, outdir, "n_scaling")


def _swept_value_numeric(itv: str, param: str) -> float | None:
    """Pull numeric portion of e.g. 'cwScale=2.0' or 'monInt=200ms'."""
    m = re.search(rf"{re.escape(param)}=([0-9.]+)", str(itv))
    return float(m.group(1)) if m else None


def plot_param_sweep(df: pd.DataFrame, outdir: str,
                     config: str, param: str, xlabel: str):
    """Generic single-parameter sweep — line chart of throughput/delay per AC.

    Filename is derived from `config` (e.g. QadEdca_CwScaleSweep -> sweep_cwscale).
    """
    s = df[df["configName"] == config].copy()
    if s.empty:
        return
    s["x"] = s["iterationVars"].apply(lambda v: _swept_value_numeric(v, param))
    s = s.dropna(subset=["x"])
    filename = "sweep_" + re.sub(r"^QadEdca_|Sweep$", "", config).lower()

    fig, axes = plt.subplots(1, 2, figsize=(14, 5))
    for col, ylabel, ax in [("throughput_mbps", "Throughput (Mbps)", axes[0]),
                            ("avg_delay_ms",    "Average Delay (ms)", axes[1])]:
        for ac in AC_ORDER:
            g = (s[s["ac"] == ac].groupby("x")[col]
                 .agg(["mean", "std"]).reset_index())
            ax.errorbar(g["x"], g["mean"], yerr=g["std"], marker="o",
                        color=AC_COLORS[ac], label=ac, capsize=3, alpha=0.85)
        ax.set(xlabel=xlabel, ylabel=ylabel)
        ax.grid(alpha=0.3)
        ax.legend()
    fig.suptitle(f"Sensitivity: {xlabel}")
    _save(fig, outdir, filename)


def plot_threshold_heatmap(df: pd.DataFrame, outdir: str,
                            config: str = "QadEdca_ThresholdSweep"):
    """Heatmap of BE throughput across (queueThreshold, lossThreshold) grid."""
    s = df[(df["configName"] == config) & (df["ac"] == "AC_BE")].copy()
    if s.empty:
        return
    s["qTh"] = s["iterationVars"].apply(lambda v: _swept_value_numeric(v, "qTh"))
    s["pTh"] = s["iterationVars"].apply(lambda v: _swept_value_numeric(v, "pTh"))
    s = s.dropna(subset=["qTh", "pTh"])
    grid = (s.groupby(["qTh", "pTh"])["throughput_mbps"].mean()
              .unstack("pTh").sort_index().sort_index(axis=1))

    fig, ax = plt.subplots(figsize=(8, 6))
    im = ax.imshow(grid.values, cmap="viridis", aspect="auto", origin="lower")
    ax.set_xticks(range(len(grid.columns)), [f"{c:.2f}" for c in grid.columns])
    ax.set_yticks(range(len(grid.index)),   [f"{i:.1f}"  for i in grid.index])
    ax.set(xlabel="lossThreshold (pTh)", ylabel="queueThreshold (qTh)",
           title="Sensitivity: BE Throughput vs. (qTh, pTh)")
    for i in range(grid.shape[0]):
        for j in range(grid.shape[1]):
            ax.text(j, i, f"{grid.values[i,j]:.1f}", ha="center", va="center",
                    color="white", fontsize=9)
    fig.colorbar(im, ax=ax, label="Throughput (Mbps)")
    _save(fig, outdir, "threshold_sweep_heatmap")


def _sample_metrics() -> pd.DataFrame:
    np.random.seed(42)
    cfg = {
        "Standard EDCA": {"tp": [0.5, 4.0, 0.1, 0.01], "dl": [10, 25, 800, 1200], "lr": [0.5, 2, 45, 60]},
        "QAD-EDCA":      {"tp": [0.48, 3.5, 1.2, 0.3],  "dl": [12, 30, 120, 200],  "lr": [0.8, 3, 8, 12]},
    }
    rows = []
    for scheme, v in cfg.items():
        for j, ac in enumerate(AC_ORDER):
            for _ in range(5):
                noise = 1 + np.random.normal(0, 0.1)
                rows.append({"scheme": scheme, "ac": ac,
                             "throughput_mbps": v["tp"][j] * noise,
                             "avg_delay_ms": v["dl"][j] * noise,
                             "loss_rate_pct": v["lr"][j] * noise})
    return pd.DataFrame(rows)


def _sample_fairness() -> pd.DataFrame:
    np.random.seed(42)
    rows = []
    for scheme, base, slope in [("Standard EDCA", 0.9, 0.8), ("QAD-EDCA", 0.95, 0.3)]:
        for r in [0.2, 0.4, 0.6, 0.8]:
            rows.append({"scheme": scheme, "hi_priority_ratio": r,
                         "jains_index": np.clip(base - r * slope + np.random.normal(0, 0.03), 0.2, 1.0)})
    return pd.DataFrame(rows)


def main():
    parser = argparse.ArgumentParser(description="Generate EDCA fairness figures")
    parser.add_argument("results_csv", nargs="?")
    parser.add_argument("--outdir", "-o", default="figures")
    parser.add_argument("--sample", action="store_true")
    args = parser.parse_args()
    os.makedirs(args.outdir, exist_ok=True)

    if args.sample or not args.results_csv:
        print("Using sample data for plot testing...")
        df_metrics, df_fair = _sample_metrics(), _sample_fairness()
        df_full = df_metrics
    else:
        df_full = pd.read_csv(args.results_csv)
        df_metrics = df_full[df_full["configName"].isin(["Baseline_N10", "QadEdca_N10"])]
        df_fair = df_metrics

    print(f"Generating figures in {args.outdir}/")
    # Headline N=10 comparisons
    for spec in BAR_CHARTS:
        plot_bar(df_metrics, spec, args.outdir)
    plot_fairness(df_fair, args.outdir)

    # Scale effect across N=5/10/15/20 + sensitivity sweeps (real data only)
    if not args.sample and args.results_csv:
        plot_n_scaling(df_full, args.outdir)
        plot_param_sweep(df_full, args.outdir, "QadEdca_CwScaleSweep",
                         "cwScale", "CWmin Scale Factor")
        plot_param_sweep(df_full, args.outdir, "QadEdca_RecoveryFactorSweep",
                         "recovery", "Recovery Factor")
        plot_param_sweep(df_full, args.outdir, "QadEdca_MonitorIntervalSweep",
                         "monInt", "Monitor Interval (ms)")
        plot_threshold_heatmap(df_full, args.outdir)
    print("Done.")


if __name__ == "__main__":
    main()
