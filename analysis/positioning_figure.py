#!/usr/bin/env python3
"""
Performance vs. complexity positioning of the four schemes.

This is a *conceptual* trade-off chart (NOT a mix of incommensurable metrics):
the y-axis is qualitative "starvation relief / throughput optimization", the
x-axis is qualitative "computational cost / training requirement". It visualises
the proposal's positioning — QAD-EDCA is the adaptive-yet-training-free middle
ground between static EDCA and DRL.

PDCF-DRL is placed from its *published* results (Zuo et al. 2025, [6]); see the
annotations. It is a reference point, not a re-simulated head-to-head.

Output: analysis/figures/positioning_tradeoff.{pdf,png}
"""
import os
import matplotlib.pyplot as plt

plt.rcParams.update({
    "font.size": 12, "font.family": "serif", "axes.labelsize": 14,
    "axes.titlesize": 14, "figure.dpi": 150, "savefig.dpi": 300,
})

# (x = cost/training, y = starvation relief), both on a 0..10 qualitative scale.
# label_dxy / note_dxy = offset (points) for the bold name and the small note,
# hand-placed so the four annotations do not overlap.
SCHEMES = [
    ("Standard EDCA",     1.2, 1.4, "#e74c3c", "BE 94.7% loss (starved)",
     (0, 20), (0, -34)),
    ("Tuned Static EDCA", 1.5, 6.2, "#f39c12", "BE 5.80 Mbps,\nhand-tuned, fixed",
     (-6, 20), (-78, -6)),
    ("QAD-EDCA (ours)",   2.6, 4.6, "#2980b9", "BE 5.44 Mbps, O(1),\nno training, adapts",
     (8, -6), (70, -22)),
    ("PDCF-DRL [6]",      8.6, 8.8, "#27ae60", "near-equal AC shares\n(no starv.), but DRL\ntraining required",
     (0, 22), (0, -42)),
]


def main():
    outdir = os.path.join(os.path.dirname(__file__), "figures")
    os.makedirs(outdir, exist_ok=True)
    fig, ax = plt.subplots(figsize=(9, 6.2))

    for name, x, y, c, note, ldxy, ndxy in SCHEMES:
        ax.scatter(x, y, s=520, color=c, edgecolor="black", zorder=3, alpha=0.9)
        ax.annotate(name, (x, y), xytext=ldxy, textcoords="offset points",
                    ha="center", fontsize=12, fontweight="bold")
        ax.annotate(note, (x, y), xytext=ndxy, textcoords="offset points",
                    ha="center", fontsize=8.5, color="#333333")

    # "sweet spot" guide for the low-cost adaptive region
    ax.axvspan(0, 3.2, color="#2980b9", alpha=0.06, zorder=0)
    ax.text(1.6, 9.5, "training-free,\nimmediately deployable",
            ha="center", fontsize=9, color="#2980b9")

    ax.annotate("", xy=(8.2, 8.2), xytext=(2.6, 5.0),
                arrowprops=dict(arrowstyle="->", ls="--", color="#888888"))
    ax.text(5.2, 6.0, "more performance,\nbut training cost",
            ha="center", fontsize=9, color="#888888", rotation=18)

    ax.set_xlim(0, 10)
    ax.set_ylim(0, 10.5)
    ax.set_xlabel("Computational cost / training requirement  →")
    ax.set_ylabel("Starvation relief / throughput optimization  →")
    ax.set_title("Performance–Complexity Positioning of EDCA Starvation-Avoidance Schemes")
    ax.set_xticks([1, 5, 9], ["O(1)\nno training", "rule-based", "DRL\n(trained)"])
    ax.set_yticks([1, 5, 9], ["starved", "partial relief", "near-equal\n(no starv.)"])
    ax.grid(alpha=0.25)
    for ext in ("pdf", "png"):
        fig.savefig(os.path.join(outdir, f"positioning_tradeoff.{ext}"),
                    bbox_inches="tight")
    plt.close(fig)
    print("  -> positioning_tradeoff.pdf/.png")


if __name__ == "__main__":
    main()
