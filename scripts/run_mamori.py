#!/usr/bin/env python3
"""MAMORI CLI: run the (model x defense x language x mode) grid.

Examples
--------
# Dry run: print the grid that would execute (no model needed)
python scripts/run_mamori.py --dry-run

# Open-weight model served by vLLM on :8000
#   (serve first, e.g.: python -m vllm.entrypoints.openai.api_server \
#       --model meta-llama/Meta-Llama-3-8B-Instruct --port 8000)
LOCAL_LLM_PORT=8000 python scripts/run_mamori.py \
    --model local --model-id meta-llama/Meta-Llama-3-8B-Instruct \
    --suite workspace --languages en de tr ko ar sw \
    --defenses none transformers_pi_detector spotlighting_with_delimiting

# API model
ANTHROPIC_API_KEY=... python scripts/run_mamori.py \
    --model claude-3-5-sonnet-20241022 --suite workspace
"""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from mamori.harness import GridSpec, run_grid, DEFENSES
from mamori.variants import Mode
from mamori.languages import DEFAULT_LANGUAGES
from mamori.leaderboard import build_leaderboard, write_leaderboard


def main():
    ap = argparse.ArgumentParser(description="Run the MAMORI grid.")
    ap.add_argument("--model", action="append", dest="models",
                    help="Model name (repeatable). 'local' for vLLM open-weight.")
    ap.add_argument("--model-id", dest="model_id",
                    help="HF id for the local/vLLM model (maps to --model local).")
    ap.add_argument("--defenses", nargs="+", default=DEFENSES, choices=DEFENSES)
    ap.add_argument("--languages", nargs="+", default=DEFAULT_LANGUAGES)
    ap.add_argument("--modes", nargs="+", default=["plain"],
                    choices=[m.value for m in Mode])
    ap.add_argument("--suite", default="workspace")
    ap.add_argument("--benchmark-version", default="v1.2.1")
    ap.add_argument("--user-tasks", nargs="*", default=None,
                    help="Subset of user task IDs (for quick runs).")
    ap.add_argument("--injection-tasks", nargs="*", default=None)
    ap.add_argument("--logdir", default="runs/mamori")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    models = args.models or ["local"]
    model_ids = {"local": args.model_id} if args.model_id else {}

    spec = GridSpec(
        models=models,
        model_ids=model_ids,
        defenses=args.defenses,
        languages=args.languages,
        modes=[Mode(m) for m in args.modes],
        suite=args.suite,
        benchmark_version=args.benchmark_version,
        user_tasks=args.user_tasks,
        injection_tasks=args.injection_tasks,
    )
    logdir = Path(args.logdir)
    cells = run_grid(spec, logdir, dry_run=args.dry_run)

    if cells and not args.dry_run:
        rows = build_leaderboard(cells)
        write_leaderboard(rows, logdir / "leaderboard.csv")
        print(f"[mamori] leaderboard -> {logdir/'leaderboard.csv'}")
        print("\nTop configs by cross-lingual robustness:")
        for r in rows[:5]:
            print(f"  {r.robustness_score:>6.3f}  {r.model} / {r.defense}  "
                  f"(ASR en={r.asr_english}, mean={r.asr_mean_all}, "
                  f"worst={r.asr_worst_lang}@{r.worst_lang})")


if __name__ == "__main__":
    main()
