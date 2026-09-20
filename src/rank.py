"""Run the ranking conditions against the model and append results to JSONL.

    python src/rank.py --dry-run          # print one prompt, call nothing
    python src/rank.py                    # run everything not yet recorded
    python src/rank.py --only base,temp07 # run a subset of conditions

Every call appends one line to results/runs.jsonl. The file is the only state:
re-running skips any (job, condition, replicate) already recorded, so an
interrupted run resumes without re-spending on completed calls. Delete lines
(or the file) to force a re-run.
"""

import argparse
import json
import random
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

import config
from conditions import BY_NAME, CONDITIONS, REPLICATES


def load_corpus():
    candidates = json.loads((config.DATA_DIR / "candidates.json").read_text())
    jobs = json.loads((config.DATA_DIR / "jobs.json").read_text())
    return candidates, jobs


def presentation_order(candidates, condition, replicate):
    """Return candidates in the order the model will see them.

    For the shuffled condition the permutation is seeded from the replicate
    index, so `runs.jsonl` can be reproduced and the permutation recorded
    alongside the result is the one actually used.
    """
    if condition.order == "canonical":
        return list(candidates)
    rng = random.Random(1000 + replicate)
    shuffled = list(candidates)
    rng.shuffle(shuffled)
    return shuffled


def render_prompt(job, ordered_candidates, condition):
    template = (config.PROMPT_DIR / f"variant_{condition.prompt_variant}.txt").read_text()
    blocks = []
    for c in ordered_candidates:
        blocks.append(f"[{c['id']}]\n{c['resume_text']}")
    return template.format(
        job_title=job["title"],
        job_description=job["description"],
        criteria="\n".join(f"- {c}" for c in job["criteria"]),
        candidates="\n\n".join(blocks),
        n_candidates=len(ordered_candidates),
    )


def parse_ranking(raw_text, expected_ids):
    """Parse the model reply into an ordered id list.

    Returns (ranking, scores, issues). A reply that drops, duplicates or
    invents a candidate is kept with its issues recorded rather than being
    retried away -- how often that happens is itself a result.
    """
    issues = []
    try:
        payload = json.loads(raw_text)
    except json.JSONDecodeError as exc:
        return None, None, [f"json-decode-error: {exc}"]

    rows = payload.get("ranking")
    if not isinstance(rows, list):
        return None, None, ["missing-ranking-array"]

    ranking, scores = [], {}
    for row in rows:
        if not isinstance(row, dict) or "id" not in row:
            issues.append("malformed-row")
            continue
        cid = row["id"]
        if cid in scores:
            issues.append(f"duplicate-id:{cid}")
            continue
        if cid not in expected_ids:
            issues.append(f"unknown-id:{cid}")
            continue
        ranking.append(cid)
        try:
            scores[cid] = float(row.get("score"))
        except (TypeError, ValueError):
            scores[cid] = None

    missing = [i for i in expected_ids if i not in scores]
    if missing:
        issues.append(f"missing-ids:{','.join(missing)}")
    return ranking, scores, issues


def already_done(path):
    if not path.exists():
        return set()
    keys = set()
    for line in path.read_text().splitlines():
        if line.strip():
            rec = json.loads(line)
            keys.add((rec["job_id"], rec["condition"], rec["replicate"], rec["model"]))
    return keys


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--model", default=config.DEFAULT_MODEL)
    ap.add_argument("--replicates", type=int, default=REPLICATES)
    ap.add_argument("--only", help="comma-separated condition names")
    ap.add_argument("--job", help="run a single job id")
    ap.add_argument("--dry-run", action="store_true",
                    help="print the first rendered prompt and exit without calling the API")
    args = ap.parse_args()

    candidates, jobs = load_corpus()
    expected_ids = [c["id"] for c in candidates]
    if args.job:
        jobs = [j for j in jobs if j["id"] == args.job]
        if not jobs:
            raise SystemExit(f"no job with id {args.job}")

    conditions = CONDITIONS
    if args.only:
        conditions = [BY_NAME[n.strip()] for n in args.only.split(",")]

    if args.dry_run:
        job, cond = jobs[0], conditions[0]
        ordered = presentation_order(candidates, cond, 0)
        print(f"--- condition={cond.name} job={job['id']} ---\n")
        print(render_prompt(job, ordered, cond))
        return

    from openai import OpenAI
    client = OpenAI(api_key=config.api_key())
    system_prompt = (config.PROMPT_DIR / "system.txt").read_text()

    config.RESULTS_DIR.mkdir(exist_ok=True)
    done = already_done(config.RUNS_PATH)

    planned = [(j, c, r) for j in jobs for c in conditions for r in range(args.replicates)]
    todo = [p for p in planned
            if (p[0]["id"], p[1].name, p[2], args.model) not in done]
    print(f"{len(planned)} runs planned, {len(planned) - len(todo)} already recorded, "
          f"{len(todo)} to call")

    for n, (job, cond, rep) in enumerate(todo, 1):
        ordered = presentation_order(candidates, cond, rep)
        prompt = render_prompt(job, ordered, cond)
        started = time.time()
        response = client.chat.completions.create(
            model=args.model,
            temperature=cond.temperature,
            response_format={"type": "json_object"},
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": prompt},
            ],
        )
        elapsed = time.time() - started
        raw = response.choices[0].message.content
        ranking, scores, issues = parse_ranking(raw, expected_ids)

        record = {
            "job_id": job["id"],
            "condition": cond.name,
            "replicate": rep,
            "model": args.model,
            "temperature": cond.temperature,
            "prompt_variant": cond.prompt_variant,
            "presentation_order": [c["id"] for c in ordered],
            "ranking": ranking,
            "scores": scores,
            "issues": issues,
            "latency_s": round(elapsed, 2),
            "usage": {
                "prompt_tokens": response.usage.prompt_tokens,
                "completion_tokens": response.usage.completion_tokens,
            },
            "ts": datetime.now(timezone.utc).isoformat(),
        }
        with config.RUNS_PATH.open("a") as fh:
            fh.write(json.dumps(record) + "\n")

        flag = "" if not issues else f"  !! {'; '.join(issues)}"
        print(f"[{n}/{len(todo)}] {job['id']:<14} {cond.name:<10} rep{rep} "
              f"{elapsed:5.1f}s{flag}")

    print(f"\nwrote {config.RUNS_PATH}")


if __name__ == "__main__":
    main()
