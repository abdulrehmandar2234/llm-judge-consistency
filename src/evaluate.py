"""Turn results/runs.jsonl into metrics.json and a summary table.

    python src/evaluate.py

Reads every recorded run, computes rank agreement for each of the four
comparisons, and writes:

    results/metrics.json  -- full numbers, per job and pooled
    results/summary.md    -- the table that goes in the README

Runs whose reply did not contain a clean, complete ranking are excluded from
the correlations and counted separately, so a model that silently drops
candidates shows up as a low usable-run count rather than as good agreement.
"""

import json
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

import config
import metrics as M
from conditions import BY_NAME, COMPARISONS


def load_runs():
    if not config.RUNS_PATH.exists():
        raise SystemExit(
            f"{config.RUNS_PATH} not found. Run `python src/rank.py` first."
        )
    return [json.loads(l) for l in config.RUNS_PATH.read_text().splitlines() if l.strip()]


def usable(rec, n_expected):
    return (rec.get("ranking") is not None
            and not rec.get("issues")
            and len(rec["ranking"]) == n_expected)


def main():
    runs = load_runs()
    ids = [c["id"] for c in json.loads((config.DATA_DIR / "candidates.json").read_text())]
    jobs = json.loads((config.DATA_DIR / "jobs.json").read_text())
    n = len(ids)

    clean = [r for r in runs if usable(r, n)]
    dropped = len(runs) - len(clean)

    # group[job_id][condition] -> list of rankings
    group = defaultdict(lambda: defaultdict(list))
    raw_group = defaultdict(lambda: defaultdict(list))
    for r in clean:
        group[r["job_id"]][r["condition"]].append(r["ranking"])
        raw_group[r["job_id"]][r["condition"]].append(r)

    out = {
        "model": clean[0]["model"] if clean else None,
        "n_candidates": n,
        "n_runs_recorded": len(runs),
        "n_runs_usable": len(clean),
        "n_runs_excluded": dropped,
        "excluded_reasons": sorted({i for r in runs if not usable(r, n)
                                    for i in (r.get("issues") or ["no-ranking"])}),
        "comparisons": {},
        "position_bias": {},
        "rank_spread": {},
        "cost": _cost(runs),
    }

    for label, cond_a, cond_b in COMPARISONS:
        per_job, pooled_rows = {}, []
        for job in jobs:
            jid = job["id"]
            a = group[jid].get(cond_a, [])
            if cond_b is None:
                rows = M.pairwise(a, ids)
            else:
                rows = M.crosswise(a, group[jid].get(cond_b, []), ids)
            if rows:
                per_job[jid] = M.summarise(rows)
                pooled_rows += rows
        out["comparisons"][label] = {
            "conditions": [cond_a] + ([cond_b] if cond_b else []),
            "note": BY_NAME[cond_b or cond_a].note,
            "pooled": M.summarise(pooled_rows),
            "per_job": per_job,
        }

    # Position bias is only meaningful where the order actually varied.
    for jid in group:
        recs = raw_group[jid].get("shuffled", [])
        if recs:
            out["position_bias"][jid] = M.position_bias(recs)
    all_shuffled = [r for jid in raw_group for r in raw_group[jid].get("shuffled", [])]
    if all_shuffled:
        out["position_bias"]["pooled"] = M.position_bias(all_shuffled)

    for jid in group:
        if group[jid].get("base"):
            out["rank_spread"][jid] = M.rank_spread(group[jid]["base"], ids)

    config.RESULTS_DIR.mkdir(exist_ok=True)
    config.METRICS_PATH.write_text(json.dumps(out, indent=2) + "\n")
    config.SUMMARY_PATH.write_text(render_summary(out))
    print(config.SUMMARY_PATH.read_text())
    print(f"wrote {config.METRICS_PATH} and {config.SUMMARY_PATH}")


def _cost(runs):
    p = sum(r.get("usage", {}).get("prompt_tokens", 0) for r in runs)
    c = sum(r.get("usage", {}).get("completion_tokens", 0) for r in runs)
    return {"prompt_tokens": p, "completion_tokens": c, "total_tokens": p + c}


def render_summary(out):
    lines = [
        "# Results",
        "",
        f"Model: `{out['model']}` · {out['n_candidates']} candidates × 3 jobs · "
        f"{out['n_runs_usable']} usable runs of {out['n_runs_recorded']} recorded.",
        "",
        "Each cell is the mean over every pair of runs in the comparison, with the "
        "worst pair in brackets. Kendall's tau-b of 1.0 is an identical ranking, "
        "0.0 is the agreement of two independent shuffles. Top-5 overlap is the "
        "fraction of the shortlist two runs share.",
        "",
        "| Comparison | Kendall tau-b | Spearman rho | Top-5 overlap | Pairs |",
        "|---|---|---|---|---|",
    ]
    for label, block in out["comparisons"].items():
        p = block["pooled"]
        if not p:
            continue
        t, s, k = p["kendall_tau"], p["spearman_rho"], p["top5_overlap"]
        lines.append(
            f"| {label} | {t['mean']:.3f} ({t['min']:.3f}) | "
            f"{s['mean']:.3f} ({s['min']:.3f}) | "
            f"{k['mean']:.2f} ({k['min']:.2f}) | {t['n_pairs']} |"
        )

    pb = out["position_bias"].get("pooled")
    if pb:
        lines += [
            "",
            "## Presentation-order effect",
            "",
            "Correlation between the slot a candidate was shown in and the rank it "
            "received, pooled over the shuffled runs. Zero means order was ignored.",
            "",
            f"- Kendall tau-b: **{pb['kendall_tau']:.3f}** (p = {pb['kendall_p']:.3g}, "
            f"n = {pb['n_observations']})",
            f"- Spearman rho: **{pb['spearman_rho']:.3f}**",
        ]

    if out["rank_spread"]:
        lines += ["", "## Rank volatility on identical inputs", "",
                  "Widest position swing for a single candidate across the repeated "
                  "control runs, per job.", "",
                  "| Job | Max swing (positions) | Mean swing |", "|---|---|---|"]
        for jid, rs in out["rank_spread"].items():
            lines.append(f"| `{jid}` | {rs['max_swing']} | {rs['mean_swing']:.1f} |")

    if out["n_runs_excluded"]:
        lines += ["", "## Excluded runs", "",
                  f"{out['n_runs_excluded']} run(s) were excluded for returning an "
                  f"incomplete or malformed ranking: "
                  f"{', '.join('`' + r + '`' for r in out['excluded_reasons'])}."]

    c = out["cost"]
    lines += ["", "---", "",
              f"Token usage across all recorded runs: {c['prompt_tokens']:,} prompt + "
              f"{c['completion_tokens']:,} completion = {c['total_tokens']:,} total.", ""]
    return "\n".join(lines)


if __name__ == "__main__":
    main()
