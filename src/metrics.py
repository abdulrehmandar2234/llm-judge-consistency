"""Rank-agreement metrics. Pure functions over id lists, no IO."""

from itertools import combinations, product

from scipy.stats import kendalltau, spearmanr


def rank_vector(ranking, ids):
    """Map an ordered id list to positions (0 = best) in a fixed id order."""
    pos = {cid: i for i, cid in enumerate(ranking)}
    return [pos[cid] for cid in ids]


def agreement(ranking_a, ranking_b, ids):
    """Kendall tau-b and Spearman rho between two rankings of the same ids."""
    va, vb = rank_vector(ranking_a, ids), rank_vector(ranking_b, ids)
    tau = kendalltau(va, vb)
    rho = spearmanr(va, vb)
    return {"kendall_tau": float(tau.statistic), "spearman_rho": float(rho.statistic)}


def top_k_overlap(ranking_a, ranking_b, k=5):
    """Fraction of the top-k shortlist shared by two rankings.

    This is the metric a recruiter actually feels: two runs can correlate at
    tau = 0.8 and still disagree on who makes the interview list.
    """
    a, b = set(ranking_a[:k]), set(ranking_b[:k])
    return len(a & b) / k


def pairwise(rankings, ids, k=5):
    """Every unordered pair within one group of rankings."""
    return [_score(a, b, ids, k) for a, b in combinations(rankings, 2)]


def crosswise(rankings_a, rankings_b, ids, k=5):
    """Every pair across two groups of rankings."""
    return [_score(a, b, ids, k) for a, b in product(rankings_a, rankings_b)]


def _score(a, b, ids, k):
    row = agreement(a, b, ids)
    row[f"top{k}_overlap"] = top_k_overlap(a, b, k)
    return row


def summarise(rows):
    """Mean / min / max for each metric across a list of pair scores."""
    if not rows:
        return {}
    out = {}
    for key in rows[0]:
        vals = [r[key] for r in rows]
        out[key] = {
            "mean": sum(vals) / len(vals),
            "min": min(vals),
            "max": max(vals),
            "n_pairs": len(vals),
        }
    return out


def rank_spread(rankings, ids):
    """Per-candidate rank volatility across a group of rankings.

    Returns the widest swing (best position minus worst position) seen for any
    single candidate, and the mean swing across all of them. A large max swing
    with a high mean tau means the instability is concentrated in the middle of
    the list, which is the usual pattern.
    """
    spreads = {}
    for cid in ids:
        positions = [r.index(cid) for r in rankings]
        spreads[cid] = max(positions) - min(positions)
    values = list(spreads.values())
    return {
        "per_candidate": spreads,
        "max_swing": max(values),
        "mean_swing": sum(values) / len(values),
    }


def position_bias(records):
    """Correlation between where a candidate was shown and where it was ranked.

    Pools every (presentation index, final rank index) pair across the given
    records. Near zero means the model ignored presentation order. Positive
    means candidates shown earlier were ranked better -- a primacy effect.
    """
    shown, ranked = [], []
    for rec in records:
        order = rec["presentation_order"]
        for slot, cid in enumerate(order):
            shown.append(slot)
            ranked.append(rec["ranking"].index(cid))
    if len(shown) < 3:
        return None
    tau = kendalltau(shown, ranked)
    rho = spearmanr(shown, ranked)
    return {
        "kendall_tau": float(tau.statistic),
        "kendall_p": float(tau.pvalue),
        "spearman_rho": float(rho.statistic),
        "n_observations": len(shown),
    }
