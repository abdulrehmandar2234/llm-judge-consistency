"""Render the charts used in the README from results/metrics.json.

    python src/plots.py

Writes three PNGs into results/:

    agreement.png       tau / top-5 overlap per comparison, with the worst pair
    position_bias.png   presented slot vs assigned rank, over the shuffled runs
    rank_spread.png     per-candidate rank volatility on identical inputs
"""

import json
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

sys.path.insert(0, str(Path(__file__).parent))

import config

INK = "#1b1b1f"
ACCENT = "#2f6f9f"
MUTED = "#b8c4cc"
WARN = "#c2683c"


def _style(ax):
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.spines["left"].set_color(MUTED)
    ax.spines["bottom"].set_color(MUTED)
    ax.tick_params(colors=INK, labelsize=9)
    ax.yaxis.grid(True, color=MUTED, alpha=0.4, linewidth=0.6)
    ax.set_axisbelow(True)


def plot_agreement(m, path):
    labels, means, mins, overlaps = [], [], [], []
    for label, block in m["comparisons"].items():
        p = block["pooled"]
        if not p:
            continue
        labels.append(label.split(". ", 1)[-1])
        means.append(p["kendall_tau"]["mean"])
        mins.append(p["kendall_tau"]["min"])
        overlaps.append(p["top5_overlap"]["mean"])

    x = range(len(labels))
    fig, ax = plt.subplots(figsize=(8, 4.2))
    ax.bar([i - 0.19 for i in x], means, width=0.38, color=ACCENT,
           label="Kendall tau-b (mean)")
    ax.bar([i + 0.19 for i in x], overlaps, width=0.38, color=MUTED,
           label="Top-5 overlap (mean)")
    ax.scatter(list(x), mins, color=WARN, zorder=3, s=28,
               label="Kendall tau-b (worst pair)")

    ax.set_xticks(list(x))
    ax.set_xticklabels(labels, fontsize=8.5)
    ax.set_ylim(0, 1.05)
    ax.set_ylabel("agreement (1.0 = identical)", color=INK, fontsize=9)
    ax.set_title("Ranking agreement by condition", color=INK, fontsize=11, pad=12)
    ax.legend(frameon=False, fontsize=8.5, loc="lower left")
    _style(ax)
    fig.tight_layout()
    fig.savefig(path, dpi=160)
    plt.close(fig)


def plot_position_bias(runs, path):
    shown, ranked = [], []
    for rec in runs:
        if rec.get("condition") != "shuffled" or not rec.get("ranking"):
            continue
        for slot, cid in enumerate(rec["presentation_order"]):
            if cid in rec["ranking"]:
                shown.append(slot)
                ranked.append(rec["ranking"].index(cid))
    if not shown:
        return False

    fig, ax = plt.subplots(figsize=(5.6, 5))
    ax.scatter(shown, ranked, alpha=0.32, s=26, color=ACCENT, edgecolors="none")
    lim = max(max(shown), max(ranked)) + 0.5
    ax.plot([0, lim], [0, lim], color=WARN, linewidth=1, linestyle="--",
            label="perfect primacy (rank = slot)")
    ax.set_xlabel("slot the candidate was shown in", fontsize=9)
    ax.set_ylabel("rank the candidate received", fontsize=9)
    ax.set_title("Presentation order vs assigned rank", color=INK, fontsize=11, pad=12)
    ax.legend(frameon=False, fontsize=8.5)
    _style(ax)
    fig.tight_layout()
    fig.savefig(path, dpi=160)
    plt.close(fig)
    return True


def plot_rank_spread(m, path):
    pooled = {}
    for spread in m["rank_spread"].values():
        for cid, swing in spread["per_candidate"].items():
            pooled[cid] = max(pooled.get(cid, 0), swing)
    if not pooled:
        return False
    items = sorted(pooled.items(), key=lambda kv: -kv[1])
    labels = [k for k, _ in items]
    values = [v for _, v in items]

    fig, ax = plt.subplots(figsize=(8, 4))
    ax.bar(range(len(values)), values,
           color=[WARN if v >= 4 else ACCENT for v in values])
    ax.set_xticks(range(len(labels)))
    ax.set_xticklabels(labels, rotation=90, fontsize=7)
    ax.set_ylabel("widest rank swing (positions)", fontsize=9)
    ax.set_title("Rank volatility on identical inputs, worst job per candidate",
                 color=INK, fontsize=11, pad=12)
    _style(ax)
    fig.tight_layout()
    fig.savefig(path, dpi=160)
    plt.close(fig)
    return True


def main():
    if not config.METRICS_PATH.exists():
        raise SystemExit("results/metrics.json not found. Run `python src/evaluate.py` first.")
    m = json.loads(config.METRICS_PATH.read_text())
    runs = [json.loads(l) for l in config.RUNS_PATH.read_text().splitlines() if l.strip()]

    plot_agreement(m, config.RESULTS_DIR / "agreement.png")
    print("wrote results/agreement.png")
    if plot_position_bias(runs, config.RESULTS_DIR / "position_bias.png"):
        print("wrote results/position_bias.png")
    if plot_rank_spread(m, config.RESULTS_DIR / "rank_spread.png"):
        print("wrote results/rank_spread.png")


if __name__ == "__main__":
    main()
