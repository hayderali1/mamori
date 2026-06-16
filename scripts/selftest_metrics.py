#!/usr/bin/env python3
"""SELF-TEST of the metric math. SYNTHETIC INPUTS -- NOT EXPERIMENTAL RESULTS.

This validates that ASR, defense effectiveness (delta), and the cross-lingual
gap Gap(l) are computed correctly, using hand-made fake SuiteResults. It exists
so the harness math is trustworthy before any real run. The numbers printed here
are fabricated test fixtures and must never appear in the paper.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from mamori.metrics import (
    asr_from_security, utility_from_results, cell_metrics,
    attach_gaps_and_deltas, CellMetrics,
)


def fake_suite_results(secure_flags, util_flags):
    pairs = [(f"u{i}", "inj") for i in range(len(secure_flags))]
    return {
        "security_results": {p: s for p, s in zip(pairs, secure_flags)},
        "utility_results": {p: u for p, u in zip(pairs, util_flags)},
        "injection_tasks_utility_results": {},
    }


def main():
    # security=True means SECURE (attack failed). ASR = fraction NOT secure.
    assert asr_from_security({("a","b"): True, ("c","d"): False}) == 0.5
    assert asr_from_security({("a","b"): False, ("c","d"): False}) == 1.0
    assert utility_from_results({("a","b"): True, ("c","d"): False}) == 0.5
    print("[ok] ASR and utility primitives")

    # Build a tiny synthetic grid: 1 model, defenses {none, detector}, langs {en, tr}.
    # English: detector stops the attack; Turkish: detector leaks (the paper's thesis).
    cells = [
        cell_metrics("m", "none", "en", "plain",
                     fake_suite_results([False, False, False, False], [True]*4)),   # ASR 1.0
        cell_metrics("m", "none", "tr", "plain",
                     fake_suite_results([False, False, False, False], [True]*4)),   # ASR 1.0
        cell_metrics("m", "transformers_pi_detector", "en", "plain",
                     fake_suite_results([True, True, True, True], [True]*4)),       # ASR 0.0
        cell_metrics("m", "transformers_pi_detector", "tr", "plain",
                     fake_suite_results([True, False, False, False], [True]*4)),    # ASR 0.75
    ]
    attach_gaps_and_deltas(cells)
    got = {(c.defense, c.lang): (c.asr, c.gap_vs_english, c.defense_delta) for c in cells}

    # English detector: ASR 0 -> gap 0, delta = 1.0 - 0.0 = 1.0 (fully effective)
    assert got[("transformers_pi_detector","en")] == (0.0, 0.0, 1.0), got[("transformers_pi_detector","en")]
    # Turkish detector: ASR 0.75 -> gap vs en = 0.75, delta = 1.0 - 0.75 = 0.25 (leaks)
    assert got[("transformers_pi_detector","tr")] == (0.75, 0.75, 0.25), got[("transformers_pi_detector","tr")]
    print("[ok] gap_vs_english and defense_delta")
    print("[ok] detector that is fully effective in English (delta=1.0) leaks in Turkish (delta=0.25)")
    print("\nALL SELF-TESTS PASSED. (Synthetic fixtures only -- not results.)")


if __name__ == "__main__":
    main()
