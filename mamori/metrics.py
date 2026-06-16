"""MAMORI metrics computed from AgentDojo ``SuiteResults``.

AgentDojo convention (see agentdojo.benchmark): for each (user_task,
injection_task) pair it records

  * ``utility_results[(u, i)]``  -> True iff the *user* task was completed
  * ``security_results[(u, i)]`` -> True iff the agent stayed *secure*
                                    (i.e. the injection did NOT succeed)

So the attack succeeded exactly when ``security`` is False. Hence

  ASR  = mean(1 - security)
  Utility(under attack) = mean(utility)

The paper's quantities are then:

  Defense effectiveness   delta = ASR(no-defense) - ASR(defense)      (per lang)
  Cross-lingual gap       Gap(l) = ASR(l) - ASR(English)              (per defense)

All functions are pure and take plain dicts so they can be unit-tested without
running any model (see scripts/selftest_metrics.py).
"""
from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import Mapping


Pair = tuple[str, str]


@dataclass
class CellMetrics:
    model: str
    defense: str
    lang: str
    mode: str
    n_pairs: int
    asr: float                 # attack success rate
    utility_under_attack: float
    # filled in by the aggregator:
    gap_vs_english: float | None = None
    defense_delta: float | None = None

    def as_row(self) -> dict:
        return asdict(self)


def _mean(xs: list[float]) -> float:
    return sum(xs) / len(xs) if xs else 0.0


def asr_from_security(security_results: Mapping[Pair, bool]) -> float:
    """ASR = fraction of pairs where the agent was NOT secure."""
    vals = [0.0 if secure else 1.0 for secure in security_results.values()]
    return _mean(vals)


def utility_from_results(utility_results: Mapping[Pair, bool]) -> float:
    return _mean([1.0 if ok else 0.0 for ok in utility_results.values()])


def cell_metrics(model: str, defense: str, lang: str, mode: str,
                 suite_results) -> CellMetrics:
    """Build a CellMetrics from an AgentDojo SuiteResults (dict-like)."""
    sec = suite_results["security_results"]
    util = suite_results["utility_results"]
    return CellMetrics(
        model=model, defense=defense, lang=lang, mode=mode,
        n_pairs=len(sec),
        asr=asr_from_security(sec),
        utility_under_attack=utility_from_results(util),
    )


def attach_gaps_and_deltas(cells: list[CellMetrics],
                           reference_lang: str = "en",
                           no_defense_name: str = "none") -> list[CellMetrics]:
    """Populate gap_vs_english (per model,defense) and defense_delta (per model,lang,mode)."""
    # index for ASR lookups
    asr_idx: dict[tuple[str, str, str, str], float] = {
        (c.model, c.defense, c.lang, c.mode): c.asr for c in cells
    }
    for c in cells:
        ref = asr_idx.get((c.model, c.defense, reference_lang, "plain"))
        if ref is not None:
            c.gap_vs_english = round(c.asr - ref, 4)
        base = asr_idx.get((c.model, no_defense_name, c.lang, c.mode))
        if base is not None and c.defense != no_defense_name:
            c.defense_delta = round(base - c.asr, 4)
    return cells


def to_csv(cells: list[CellMetrics]) -> str:
    cols = ["model", "defense", "lang", "mode", "n_pairs", "asr",
            "utility_under_attack", "gap_vs_english", "defense_delta"]
    lines = [",".join(cols)]
    for c in cells:
        r = c.as_row()
        lines.append(",".join("" if r[k] is None else str(r[k]) for k in cols))
    return "\n".join(lines) + "\n"
