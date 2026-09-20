"""Paths and runtime settings, resolved once."""

import os
from pathlib import Path

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:  # python-dotenv is optional; env vars still work
    pass

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data"
PROMPT_DIR = ROOT / "prompts"
RESULTS_DIR = ROOT / "results"

RUNS_PATH = RESULTS_DIR / "runs.jsonl"
METRICS_PATH = RESULTS_DIR / "metrics.json"
SUMMARY_PATH = RESULTS_DIR / "summary.md"

DEFAULT_MODEL = os.getenv("MODEL", "gpt-4o-mini")
API_KEY_VAR = "OPENAI_API_KEY"


def api_key() -> str:
    key = os.getenv(API_KEY_VAR)
    if not key:
        raise SystemExit(
            f"{API_KEY_VAR} is not set. Copy .env.example to .env and fill it in, "
            f"or export {API_KEY_VAR} in your shell."
        )
    return key
