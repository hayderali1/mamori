"""MAMORI evaluation harness.

Runs the (model x defense x language x mode) grid by, for each cell:

  1. building a real AgentDojo pipeline with the chosen defense,
  2. loading a real AgentDojo task suite,
  3. building the cross-lingual attack for (language, mode),
  4. calling ``benchmark_suite_with_injections`` (the stock AgentDojo runner),
  5. converting the SuiteResults into MAMORI CellMetrics,
  6. recording translation provenance.

Open-weight models (Llama-3-8B, Mistral-7B, Qwen2.5-7B, Gemma) are served via a
local OpenAI-compatible endpoint (vLLM). Set provider ``local`` (or
``vllm_parsed``), point ``LOCAL_LLM_PORT`` at the server, and pass the HF id as
``model_id``. API models (anthropic/openai/google) work by name with the
corresponding key in the environment.

Nothing here fabricates results: every number comes from AgentDojo executing the
agent loop against a served model. On a machine with no model/key, ``--dry-run``
prints the exact grid that *would* run without touching a model.
"""
from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from pathlib import Path

from .languages import DEFAULT_LANGUAGES
from .variants import Mode
from .attacks import build_attack_class, attack_name
from .metrics import CellMetrics, cell_metrics, attach_gaps_and_deltas, to_csv

# AgentDojo defenses; "none" is the no-defense baseline (config.defense=None).
DEFENSES = ["none", "transformers_pi_detector", "spotlighting_with_delimiting",
            "repeat_user_prompt", "tool_filter"]


@dataclass
class GridSpec:
    models: list[str]                 # e.g. ["local"] (vLLM) or ["claude-3-5-sonnet-20241022"]
    model_ids: dict[str, str] = field(default_factory=dict)  # model -> HF id for local
    defenses: list[str] = field(default_factory=lambda: list(DEFENSES))
    languages: list[str] = field(default_factory=lambda: list(DEFAULT_LANGUAGES))
    modes: list[Mode] = field(default_factory=lambda: [Mode.PLAIN])
    suite: str = "workspace"
    benchmark_version: str = "v1.2.1"
    user_tasks: list[str] | None = None        # subset for quick runs
    injection_tasks: list[str] | None = None

    def cells(self):
        for model in self.models:
            for defense in self.defenses:
                for lang in self.languages:
                    for mode in self.modes:
                        if mode == Mode.CODESWITCH and lang == "en":
                            continue
                        if mode == Mode.TRANSLIT and lang not in ("ar", "ko"):
                            continue
                        yield model, defense, lang, mode


def _build_pipeline(model: str, defense: str, model_id: str | None):
    from agentdojo.agent_pipeline import AgentPipeline, PipelineConfig
    cfg = PipelineConfig(
        llm=model,
        model_id=model_id,
        defense=None if defense == "none" else defense,
        system_message_name=None,
        system_message=None,
    )
    return AgentPipeline.from_config(cfg)


def run_grid(spec: GridSpec, logdir: Path, dry_run: bool = False) -> list[CellMetrics]:
    logdir.mkdir(parents=True, exist_ok=True)
    cells: list[CellMetrics] = []
    provenance: list[dict] = []

    plan = list(spec.cells())
    print(f"[mamori] grid: {len(plan)} cells "
          f"({len(spec.models)} models x {len(spec.defenses)} defenses x "
          f"languages/modes) on suite '{spec.suite}'")

    if dry_run:
        for model, defense, lang, mode in plan:
            print(f"  - model={model:>28}  defense={defense:<26}  "
                  f"attack={attack_name(lang, mode)}")
        return cells

    # Imports deferred so --dry-run works with no model/keys present.
    from agentdojo.task_suite.load_suites import get_suite
    from agentdojo.benchmark import benchmark_suite_with_injections

    suite = get_suite(spec.benchmark_version, spec.suite)

    for model, defense, lang, mode in plan:
        pipeline = _build_pipeline(model, defense, spec.model_ids.get(model))
        AttackCls = build_attack_class(lang, mode)
        attack = AttackCls(suite, pipeline)

        results = benchmark_suite_with_injections(
            agent_pipeline=pipeline,
            suite=suite,
            attack=attack,
            logdir=logdir,
            force_rerun=False,
            user_tasks=spec.user_tasks,
            injection_tasks=spec.injection_tasks,
            verbose=False,
            benchmark_version=spec.benchmark_version,
        )
        cm = cell_metrics(model, defense, lang, mode.value, results)
        cells.append(cm)
        print(f"[mamori] {model} | {defense:<26} | {attack_name(lang, mode):<40} "
              f"ASR={cm.asr:.3f} util={cm.utility_under_attack:.3f} (n={cm.n_pairs})")

        for u, i, rec in getattr(attack, "last_translation_records", []):
            provenance.append({
                "model": model, "defense": defense, "lang": lang, "mode": mode.value,
                "user_task": u, "injection_task": i,
                "carrier_verified": rec.carrier_verified,
                "goal_matched_scaffold": rec.goal_matched_scaffold,
                "goal_verified": rec.goal_verified,
                "goal_translator": rec.goal_translator,
                "codeswitch_fallback": rec.fallback_codeswitched,
            })

    attach_gaps_and_deltas(cells)
    (logdir / "mamori_metrics.csv").write_text(to_csv(cells))
    (logdir / "mamori_metrics.json").write_text(
        json.dumps([c.as_row() for c in cells], indent=2, ensure_ascii=False))
    (logdir / "translation_provenance.json").write_text(
        json.dumps(provenance, indent=2, ensure_ascii=False))
    print(f"[mamori] wrote metrics + provenance to {logdir}")
    return cells
