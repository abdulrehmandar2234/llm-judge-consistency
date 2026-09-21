> # ⚠️ SIMULATED OUTPUT — NOT A MEASUREMENT
>
> Every number below was produced by `results/example/simulate.py`, which
> invents rankings by applying a fixed number of adjacent swaps to an arbitrary
> reference order. **No model was called.** The `model` field says so.
>
> These figures describe the swap counts I chose. They say nothing whatsoever
> about any LLM. Real results, when the sweep is run, land in `results/` — not here.

# Results

Model: `SIMULATED-no-model-was-called` · 18 candidates × 3 jobs · 60 usable runs of 60 recorded.

Each cell is the mean over every pair of runs in the comparison, with the worst pair in brackets. Kendall's tau-b of 1.0 is an identical ranking, 0.0 is the agreement of two independent shuffles. Top-5 overlap is the fraction of the shortlist two runs share.

| Comparison | Kendall tau-b | Spearman rho | Top-5 overlap | Pairs |
|---|---|---|---|---|
| A. Repeated identical runs | 0.945 (0.922) | 0.990 (0.981) | 0.89 (0.80) | 30 |
| B. Candidate order shuffled | 0.912 (0.869) | 0.980 (0.961) | 0.89 (0.80) | 75 |
| C. Temperature 0.0 vs 0.7 | 0.922 (0.895) | 0.984 (0.971) | 0.91 (0.80) | 75 |
| D. Prompt variant A vs B | 0.935 (0.908) | 0.987 (0.975) | 0.91 (0.80) | 75 |

## Presentation-order effect

Correlation between the slot a candidate was shown in and the rank it received, pooled over the shuffled runs. Zero means order was ignored.

- Kendall tau-b: **-0.068** (p = 0.114, n = 270)
- Spearman rho: **-0.098**

## Rank volatility on identical inputs

Widest position swing for a single candidate across the repeated control runs, per job.

| Job | Max swing (positions) | Mean swing |
|---|---|---|
| `job_backend` | 3 | 1.0 |
| `job_ml` | 2 | 1.1 |
| `job_frontend` | 2 | 0.8 |

---

Token usage across all recorded runs: 0 prompt + 0 completion = 0 total.
