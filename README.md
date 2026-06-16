# MAMORI

**M**ultilingual **A**gent **M**easurement **O**f **R**obustness to **I**njection.

**A cross-lingual indirect-prompt-injection (IPI) robustness benchmark for tool-using LLM agents.**

> *Name:* **MAMORI** is the backronym above; it also reads as 守り (*mamori*,
> "protection/defense" in Japanese), pairing with **AgentDojo** (*dōjō*, training
> hall), the environment it extends.

MAMORI extends [AgentDojo](https://github.com/ethz-spylab/agentdojo) with
injection payloads rendered across **high-, mid-, and low-resource languages**
(plus **code-switched** and **transliterated** variants) and measures, per
language, attack success rate (ASR), benign utility, and defense effectiveness.
It operationalises the question in the proposal: *do indirect-prompt-injection
defenses, all tuned on English, survive translation?*

This repository is the **implementation of the MAMORI proposal**. It is built
directly on AgentDojo's real API (the cross-lingual attacks register into
AgentDojo's own attack registry and run through its stock benchmark runner), so
results are produced by the established, peer-reviewed environment — we only add
the multilingual contribution.

---

## What is implemented (and verified offline in this repo)

| Component | File | Status |
|---|---|---|
| Language registry (resource level, script, morphology) | `mamori/languages.py` | ✅ |
| Verified carrier translations (EN/DE/TR/KO/AR/SW) + goal scaffolds | `mamori/translations.py` | ✅ verified subset; provenance-flagged |
| Translator: seed + literal-preserving goal translation + pluggable MT | `mamori/translator.py` | ✅ |
| Code-switching + transliteration generators | `mamori/variants.py` | ✅ |
| Cross-lingual attacks registered into AgentDojo | `mamori/attacks.py` | ✅ (registers + generates real injections offline) |
| Metrics: ASR, utility, Δ, Gap(ℓ) | `mamori/metrics.py` | ✅ (unit-tested) |
| Grid harness (model × defense × language × mode) | `mamori/harness.py` | ✅ (wired to AgentDojo's real runner) |
| Public leaderboard aggregator | `mamori/leaderboard.py` | ✅ |
| Payload exporter (real GOALs → multilingual payloads) | `scripts/make_payloads.py` | ✅ ran on the real workspace suite |
| Metric self-test | `scripts/selftest_metrics.py` | ✅ passes |

**Verified here without any model:** the payload generator emits 182 fully-rendered
payloads from the real 14 workspace injection tasks; the cross-lingual attacks
register into AgentDojo and produce real injections through its ground-truth
pipeline; the metric math is unit-tested.

## What needs your hardware (the headline ASR tables)

Producing ASR/utility numbers requires **running the agent loop against a served
model**, which needs a GPU (for open-weight models via vLLM) or an API key. This
environment has neither, so **no ASR numbers are included** — see
`results/RESULTS_TODO.md` for the exact commands. Do **not** write any numbers
into the paper that did not come from a real run on your machine.

---

## Install

```bash
pip install agentdojo            # the base environment (pip-installable)
pip install -e .                 # MAMORI (this repo)
```

## Mapping to the proposal

- **Foundation (§IV.a):** built on AgentDojo; cross-lingual attacks are first-class
  AgentDojo attacks (`important_instructions__tr`, `..._ko__translit`, …).
- **Languages (§IV.b):** English (ref), German (high), Turkish/Korean/Arabic (mid),
  Swahili (low), foregrounding Turkish (agglutinative) and Korean (distinct script).
- **Adversarial conditions (§IV.b):** `Mode.CODESWITCH` (English frame + target-language
  instruction) and `Mode.TRANSLIT` (Latinised Arabic/Korean).
- **Payload construction (§IV.c):** verified human carriers + literal-preserving goal
  scaffolds; uncovered (long, composite) goals use a pluggable MT backend with
  native-speaker verification on a sample, and every payload carries translation
  provenance so degradation can't be blamed on broken translation.
- **Defenses (§IV.d):** AgentDojo's `transformers_pi_detector` (English-trained
  ProtectAI DeBERTa → H2), `spotlighting_with_delimiting` (structured → H4),
  `repeat_user_prompt` (prompt hardening → H4), `tool_filter` (LLM filter), run
  unchanged to measure English-tuned transfer.
- **Metrics (§V.C):** ASR per language, utility, defense effectiveness Δ, and the
  headline `Gap(ℓ) = ASR(ℓ) − ASR(English)`.
- **Hypotheses (§III.d):** H1 (resource level), H2 (detectors degrade most),
  H3 (code-switch/translit evade even high-resource), H4 (structured/alignment more
  robust but still leak) — all read directly off the metrics table + leaderboard.

## Quick start

```bash
# 1) Generate the multilingual payload dataset from real AgentDojo goals (offline)
python scripts/make_payloads.py workspace

# 2) Sanity-check the metric math (offline)
python scripts/selftest_metrics.py

# 3) Preview the full run grid without touching a model
python scripts/run_mamori.py --dry-run

# 4) Real run with an open-weight model served by vLLM (needs a GPU)
python -m vllm.entrypoints.openai.api_server \
    --model meta-llama/Meta-Llama-3-8B-Instruct --port 8000 &
LOCAL_LLM_PORT=8000 python scripts/run_mamori.py \
    --model local --model-id meta-llama/Meta-Llama-3-8B-Instruct \
    --suite workspace --languages en de tr ko ar sw \
    --defenses none transformers_pi_detector spotlighting_with_delimiting repeat_user_prompt
```

## Plugging an MT backend (for full goal coverage / more languages)

```python
from mamori.attacks import set_translator

class MyMT:
    name = "nllb-200-3.3B"
    def translate(self, text, lang, protect):
        ...  # translate text->lang, leaving every string in `protect` untouched
        return translated

set_translator(MyMT())   # uncovered goals now machine-translated, literal-preserving, flagged
```

## Ethics

Defensive evaluation only. All attacker tasks are AgentDojo's benign sandbox
actions (e.g. sending an email inside a simulated workspace); no real-world-harm
instructions are produced. Findings affecting specific deployed systems are
disclosed responsibly before release. See the proposal's §VIII.
