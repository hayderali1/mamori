"""MAMORI: a cross-lingual indirect-prompt-injection robustness benchmark
for tool-using LLM agents, built as an extension of AgentDojo.

Public API:
    languages   - language registry (resource level, script, morphology)
    translator  - verified seed translations + pluggable MT, literal-preserving
    variants    - code-switching and transliteration payload modes
    attacks     - cross-lingual attacks registered into AgentDojo
    metrics     - ASR, utility, defense effectiveness, cross-lingual Gap(l)
    harness     - the (model x defense x language x mode) runner
"""
from . import languages, translator, variants, attacks, metrics, harness  # noqa: F401

__all__ = ["languages", "translator", "variants", "attacks", "metrics", "harness"]
__version__ = "0.1.0"
