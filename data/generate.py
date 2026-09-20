"""Generate the synthetic evaluation corpus.

Everything in `data/` is produced by this script from a fixed seed. No real
people, no scraped profiles, no real job postings. Re-running it reproduces
`candidates.json` and `jobs.json` byte-for-byte.

    python data/generate.py

The corpus is deliberately small (18 candidates x 3 jobs). The experiments in
this repo measure the *stability* of a ranker, not its accuracy, so what
matters is that candidates are close enough together to make the ranking
genuinely ambiguous in the middle of the list.
"""

import json
import random
from pathlib import Path

SEED = 20260921
DATA_DIR = Path(__file__).parent

JOBS = [
    {
        "id": "job_backend",
        "title": "Senior Backend Engineer",
        "description": (
            "We are hiring a Senior Backend Engineer to own our core API platform. "
            "You will design and operate distributed services handling millions of "
            "requests per day, lead schema and migration decisions, and mentor "
            "mid-level engineers."
        ),
        "criteria": [
            "5+ years building production backend services",
            "Strong Python or TypeScript; designs APIs others can use",
            "Distributed systems: queues, caching, eventual consistency",
            "Relational and document database modelling, including migrations",
            "Production ownership: on-call, observability, incident response",
        ],
    },
    {
        "id": "job_ml",
        "title": "Machine Learning Engineer (NLP)",
        "description": (
            "We are hiring an ML Engineer to build and evaluate NLP systems in "
            "production. You will own model selection, evaluation harnesses, and "
            "the inference path that serves them."
        ),
        "criteria": [
            "3+ years applied ML, with work that reached production",
            "NLP or LLM systems: fine-tuning, prompting, retrieval, or evaluation",
            "PyTorch or TensorFlow, plus the HuggingFace ecosystem",
            "Designs offline evaluation that predicts online behaviour",
            "Comfortable with inference cost and latency trade-offs",
        ],
    },
    {
        "id": "job_frontend",
        "title": "Frontend Engineer",
        "description": (
            "We are hiring a Frontend Engineer to build the customer-facing web "
            "application. You will own component architecture, performance, and "
            "accessibility across the product surface."
        ),
        "criteria": [
            "3+ years with React and TypeScript",
            "State management and component architecture at scale",
            "Web performance: bundle size, rendering, Core Web Vitals",
            "Accessibility (WCAG) as a default, not an afterthought",
            "Works fluently against REST or GraphQL APIs",
        ],
    },
]

FIRST = ["Alex", "Bianca", "Chen", "Dara", "Elif", "Farid", "Gita", "Hassan",
         "Iris", "Jonas", "Kiran", "Lena", "Mateo", "Nadia", "Omar", "Priya",
         "Rafa", "Sofia"]
LAST = ["Okafor", "Lindqvist", "Wei", "Mbeki", "Demir", "Rahimi", "Sharma",
        "Karim", "Novak", "Berger", "Patel", "Costa", "Alvarez", "Haddad",
        "Siddiqui", "Nair", "Moreau", "Ferreira"]

BACKEND_SKILLS = ["Python", "TypeScript", "Go", "PostgreSQL", "MongoDB", "Redis",
                  "Kafka", "RabbitMQ", "Docker", "Kubernetes", "Terraform", "gRPC"]
ML_SKILLS = ["PyTorch", "TensorFlow", "HuggingFace Transformers", "scikit-learn",
             "pandas", "spaCy", "FAISS", "Weights & Biases", "MLflow", "ONNX"]
FRONTEND_SKILLS = ["React", "TypeScript", "Next.js", "Redux", "TanStack Query",
                   "Tailwind CSS", "Vite", "Playwright", "Storybook", "GraphQL"]

COMPANIES = ["Northwind Systems", "Parallax Labs", "Cobalt Retail Group",
             "Harbour Analytics", "Meridian Health", "Talos Logistics",
             "Vantage Media", "Quill Financial", "Orbit Education"]

DEGREES = [
    ("BSc Computer Science", "State Technical University"),
    ("BSc Software Engineering", "Northern Institute of Technology"),
    ("MSc Computer Science", "University of the Midlands"),
    ("MSc Data Science", "Coastal University"),
    ("BEng Electrical Engineering", "Central Polytechnic"),
]

# Archetypes control how well a candidate fits each job. `weights` is the
# proportion of bullets drawn from each skill pool -- it shapes the generated
# text and is NOT used as ground truth anywhere in the experiments.
ARCHETYPES = [
    ("backend_strong", {"backend": 0.8, "ml": 0.1, "frontend": 0.1}, (6, 11)),
    ("backend_mid", {"backend": 0.7, "ml": 0.15, "frontend": 0.15}, (3, 6)),
    ("ml_strong", {"backend": 0.2, "ml": 0.7, "frontend": 0.1}, (4, 9)),
    ("ml_mid", {"backend": 0.3, "ml": 0.5, "frontend": 0.2}, (2, 5)),
    ("frontend_strong", {"backend": 0.1, "ml": 0.1, "frontend": 0.8}, (4, 9)),
    ("frontend_mid", {"backend": 0.2, "ml": 0.1, "frontend": 0.7}, (2, 5)),
    ("generalist", {"backend": 0.4, "ml": 0.3, "frontend": 0.3}, (3, 8)),
    ("junior_generalist", {"backend": 0.4, "ml": 0.3, "frontend": 0.3}, (1, 3)),
    ("career_changer", {"backend": 0.35, "ml": 0.4, "frontend": 0.25}, (1, 4)),
]

BACKEND_BULLETS = [
    "Designed and shipped a {skill}-backed service handling {n}k requests per day",
    "Led the migration of {n} legacy endpoints onto a versioned {skill} API",
    "Cut p99 latency by {n}% by introducing {skill} caching on the read path",
    "Owned on-call for a {n}-service platform; wrote the runbooks the team still uses",
    "Modelled and migrated a {n}-table schema with zero-downtime backfills",
    "Introduced {skill} to decouple write paths from downstream consumers",
]
ML_BULLETS = [
    "Built an evaluation harness in {skill} that caught {n} silent quality regressions",
    "Fine-tuned a transformer classifier with {skill}, improving macro-F1 by {n} points",
    "Shipped a retrieval pipeline over {n}k documents using {skill}",
    "Reduced inference cost {n}% by batching and caching in the {skill} serving path",
    "Ran offline/online agreement analysis on {n} labelled examples with {skill}",
    "Owned model selection and the {skill} experiment tracking the team ran on",
]
FRONTEND_BULLETS = [
    "Rebuilt the {skill} component library used across {n} product surfaces",
    "Cut initial bundle size {n}% through code splitting and {skill} route-level loading",
    "Brought the checkout flow to WCAG 2.1 AA using {skill} and automated audits",
    "Owned state management for a {n}-screen {skill} application",
    "Set up {skill} end-to-end coverage, taking release regressions from weekly to rare",
    "Drove Core Web Vitals into the green on {n} high-traffic pages with {skill}",
]

POOLS = {
    "backend": (BACKEND_SKILLS, BACKEND_BULLETS),
    "ml": (ML_SKILLS, ML_BULLETS),
    "frontend": (FRONTEND_SKILLS, FRONTEND_BULLETS),
}


def make_candidate(rng, idx, archetype):
    name_kind, weights, yoe_range = archetype
    years = rng.randint(*yoe_range)
    n_roles = 1 if years <= 2 else (2 if years <= 6 else 3)

    kinds = list(weights)
    probs = [weights[k] for k in kinds]

    skills = []
    for kind in kinds:
        pool = POOLS[kind][0]
        take = max(1, round(weights[kind] * 8))
        skills += rng.sample(pool, min(take, len(pool)))
    skills = sorted(set(skills))

    roles, remaining = [], years
    for r in range(n_roles):
        span = remaining if r == n_roles - 1 else max(1, rng.randint(1, max(1, remaining - 1)))
        remaining -= span
        kind = rng.choices(kinds, probs)[0]
        pool_skills, pool_bullets = POOLS[kind]
        bullets = [
            b.format(skill=rng.choice(pool_skills), n=rng.choice([2, 3, 5, 8, 12, 20, 35, 60]))
            for b in rng.sample(pool_bullets, k=rng.randint(2, 3))
        ]
        roles.append({
            "title": rng.choice([
                "Software Engineer", "Senior Software Engineer", "Backend Engineer",
                "Machine Learning Engineer", "Frontend Engineer", "Full Stack Engineer",
            ]),
            "company": rng.choice(COMPANIES),
            "years": span,
            "highlights": bullets,
        })
        if remaining <= 0:
            break

    degree, school = rng.choice(DEGREES)
    return {
        "id": f"cand_{idx:02d}",
        "name": f"{FIRST[idx]} {LAST[idx]}",
        "archetype": name_kind,
        "years_experience": years,
        "education": {"degree": degree, "institution": school},
        "skills": skills,
        "experience": roles,
    }


def resume_text(c):
    lines = [
        c["name"],
        f"{c['years_experience']} years of experience",
        f"{c['education']['degree']}, {c['education']['institution']}",
        "",
        "Skills: " + ", ".join(c["skills"]),
        "",
        "Experience:",
    ]
    for r in c["experience"]:
        lines.append(f"- {r['title']}, {r['company']} ({r['years']} yr)")
        lines += [f"    * {h}" for h in r["highlights"]]
    return "\n".join(lines)


def main():
    rng = random.Random(SEED)
    archetypes = [ARCHETYPES[i % len(ARCHETYPES)] for i in range(18)]
    rng.shuffle(archetypes)
    candidates = [make_candidate(rng, i, archetypes[i]) for i in range(18)]
    for c in candidates:
        c["resume_text"] = resume_text(c)

    (DATA_DIR / "candidates.json").write_text(
        json.dumps(candidates, indent=2, ensure_ascii=False) + "\n")
    (DATA_DIR / "jobs.json").write_text(
        json.dumps(JOBS, indent=2, ensure_ascii=False) + "\n")
    print(f"wrote {len(candidates)} candidates and {len(JOBS)} jobs to {DATA_DIR}")


if __name__ == "__main__":
    main()
