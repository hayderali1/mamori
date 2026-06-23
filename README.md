<div align="center">

# MAMORI

**M**ultilingual **A**gent **M**easurement **O**f **R**obustness to **I**njection

**A cross-lingual indirect-prompt-injection (IPI) robustness benchmark for tool-using LLM agents.**

[![Built on AgentDojo](https://img.shields.io/badge/built%20on-AgentDojo-blue)](https://github.com/ethz-spylab/agentdojo)
[![Python](https://img.shields.io/badge/python-%E2%89%A53.10-blue)](https://www.python.org/)
[![Status](https://img.shields.io/badge/status-research%20preview-orange)]()

</div>

> **MAMORI** is the backronym above; it also reads as 守り (*mamori*, "protection / defense" in Japanese), pairing with **AgentDojo** (*dōjō*, "training hall"), the environment it extends.

---

## Overview

Tool-using LLM agents read email, browse the web, and call external tools — which exposes them to **indirect prompt injection (IPI)**: malicious instructions hidden in the untrusted data an agent retrieves. Essentially all existing IPI benchmarks and defenses are built and evaluated **in English**, while separate work has shown that translating malicious content into lower-resource languages reliably bypasses safety alignment in chat settings.

**MAMORI asks whether the same cross-lingual weakness compromises IPI *defenses* in tool-using agents.** It extends [AgentDojo](https://github.com/ethz-spylab/agentdojo) with injection payloads and user tasks rendered across **high-, mid-, and low-resource languages** — plus **code-switched** and **transliterated** variants — and measures, per language, **attack success rate (ASR)**, **benign utility**, and **defense effectiveness (Δ)**.

The cross-lingual attacks register directly into AgentDojo's own attack registry and run through its stock benchmark runner, so results are produced by the established, peer-reviewed environment — MAMORI adds only the multilingual contribution.

This work is **defensive**: all attacker tasks are benign sandbox actions inside a simulated environment, and the artifact is oriented toward building stronger multilingual guardrails.

---

## Key features

| Capability | Where |
|---|---|
| 6 languages spanning resource levels, scripts, and morphologies (EN, DE, TR, KO, AR, SW) | `mamori/languages.py` |
| Verified carrier translations + goal scaffolds, with per-payload provenance | `mamori/translations.py`, `mamori/translator.py` |
| Code-switching and transliteration payload generators | `mamori/variants.py` |
| Cross-lingual attacks that register into AgentDojo's real registry | `mamori/attacks.py` |
| Metrics: ASR, utility-under-attack, defense Δ, cross-lingual `Gap(ℓ)`, **ACLR**, **MSI** | `mamori/metrics.py` |
| Grid harness (model × defense × language × mode) over AgentDojo's runner | `mamori/harness.py` |
| Public leaderboard aggregator (configs ranked by cross-lingual robustness) | `mamori/leaderboard.py` |
| Pluggable MT backend for scaling translations | `set_translator()` in `mamori/attacks.py` |

**Languages**

| Code | Language | Resource | Script | Morphology | Variants |
|---|---|---|---|---|---|
| `en` | English | high | Latin | analytic | plain *(reference)* |
| `de` | German | high | Latin | fusional | plain, codeswitch |
| `tr` | Turkish | mid | Latin | agglutinative | plain, codeswitch |
| `ko` | Korean | mid | Hangul | agglutinative | plain, codeswitch, translit |
| `ar` | Arabic | mid | Arabic (RTL) | fusional | plain, codeswitch, translit |
| `sw` | Swahili | low | Latin | analytic | plain, codeswitch |

**Modes:** `plain` · `codeswitch` (English carrier + non-English instruction) · `translit` (Latinised non-Latin script)

**Defenses** (all English-tuned; run unchanged to measure real-world transfer): `none` · `transformers_pi_detector` · `spotlighting_with_delimiting` · `repeat_user_prompt` · `tool_filter`

---

## Installation

Requires **Python ≥ 3.10**.

```bash
# 1. clone
git clone https://github.com/hayderali1/mamori.git
cd mamori

# 2. create + activate a virtual environment
python -m venv .venv
source .venv/bin/activate            # Windows (PowerShell): .venv\Scripts\Activate.ps1

# 3. install the package (pulls in AgentDojo)
pip install -e .

# 4. (optional) detector defense dependencies
#    needed only for the `transformers_pi_detector` defense
pip install transformers torch sentencepiece
```

<details>
<summary><b>Windows / PowerShell notes</b></summary>

- Use `py -m venv .venv` if `python` is not found before the venv exists.
- If activation is blocked: `Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass`, then activate again.
- Once the venv is active (prompt shows `(.venv)`), use `python` (not `py`).
- The detector defense downloads `protectai/deberta-v3-base-prompt-injection-v2` (~440 MB) from HuggingFace on first use; it runs on CPU.

</details>

<details>
<summary><b>Optional: open-weight serving (GPU)</b></summary>

To run the exact 7–8B open-weight models, serve them with vLLM and point MAMORI at the local OpenAI-compatible endpoint:

```bash
pip install -e ".[serving]"     # installs vllm
python -m vllm.entrypoints.openai.api_server \
    --model meta-llama/Meta-Llama-3-8B-Instruct --port 8000
```

</details>

---

## Quickstart

Set your model provider key (example uses OpenAI):

```bash
export OPENAI_API_KEY=sk-...          # Windows (PowerShell): $env:OPENAI_API_KEY = "sk-..."
```

**Dry run** — print the grid that would execute, no model or key needed:

```bash
python scripts/run_mamori.py --dry-run --languages en tr ko sw --modes plain codeswitch translit
```

**Smoke test** — one cell, costs a few cents, validates the full pipeline end-to-end:

```bash
python scripts/run_mamori.py --model gpt-4o-mini-2024-07-18 --suite workspace \
    --languages en tr --defenses none transformers_pi_detector --modes plain \
    --user-tasks user_task_0 --injection-tasks injection_task_0 --logdir runs/smoke
```

---

## Usage

### CLI reference

```
python scripts/run_mamori.py [options]

  --model MODEL            Model id (repeatable). Any AgentDojo-supported model,
                           e.g. gpt-4o-mini-2024-07-18, claude-3-haiku-20240307,
                           or `local` (with --model-id) for a vLLM-served model.
  --model-id ID            HF id for the `local` provider (vLLM).
  --defenses ...           Subset of: none transformers_pi_detector
                           spotlighting_with_delimiting repeat_user_prompt tool_filter
  --languages ...          Subset of: en de tr ko ar sw   (default: all six)
  --modes ...              Subset of: plain codeswitch translit   (default: plain)
  --suite NAME             AgentDojo suite: workspace | banking | travel | slack
  --benchmark-version V    AgentDojo benchmark version (default: v1.2.1)
  --user-tasks ...         Limit to specific user-task ids (cost control)
  --injection-tasks ...    Limit to specific injection-task ids (cost control)
  --logdir PATH            Output + cache directory (default: runs/mamori)
  --dry-run                Print the grid and exit (no model needed)
```

> The harness only builds variants that exist for a language (e.g. transliteration is defined for Korean and Arabic only), so unavailable `(language, mode)` combinations are skipped automatically.

> **Caching.** Runs are resumable: completed `(model, defense, attack, task)` cells are cached in `--logdir` and are neither recomputed nor re-billed. Re-run the same command to continue an interrupted run. Use a **separate `--logdir` per experiment** — the per-run summary CSV is overwritten in place.

### Reproducing the reference experiments

```bash
# Core grid (workspace): 4 languages × {none, detector}, plain mode
python scripts/run_mamori.py --model gpt-4o-mini-2024-07-18 --suite workspace \
    --languages en tr ko sw --defenses none transformers_pi_detector --modes plain \
    --user-tasks user_task_0 user_task_1 user_task_3 user_task_2 user_task_5 user_task_6 user_task_7 user_task_8 \
    --injection-tasks injection_task_0 injection_task_1 injection_task_2 injection_task_3 injection_task_4 \
    --logdir runs/workspace_core

# H3 — code-switch / transliteration evasion (none vs detector)
python scripts/run_mamori.py --model gpt-4o-mini-2024-07-18 --suite workspace \
    --languages tr ko sw --defenses none transformers_pi_detector --modes codeswitch translit \
    --user-tasks user_task_0 user_task_1 user_task_3 user_task_2 user_task_5 user_task_6 user_task_7 user_task_8 \
    --injection-tasks injection_task_0 injection_task_1 injection_task_2 injection_task_3 injection_task_4 \
    --logdir runs/h3_evasion

# H4 — structured / filter defenses (plain mode)
python scripts/run_mamori.py --model gpt-4o-mini-2024-07-18 --suite workspace \
    --languages en tr ko sw --defenses spotlighting_with_delimiting tool_filter --modes plain \
    --user-tasks user_task_0 user_task_1 user_task_3 user_task_2 user_task_5 user_task_6 user_task_7 user_task_8 \
    --injection-tasks injection_task_0 injection_task_1 injection_task_2 injection_task_3 injection_task_4 \
    --logdir runs/h4_defenses

# Second-environment replication (banking)
python scripts/run_mamori.py --model gpt-4o-mini-2024-07-18 --suite banking \
    --languages en tr ko sw --defenses none transformers_pi_detector spotlighting_with_delimiting tool_filter --modes plain \
    --user-tasks user_task_0 user_task_1 user_task_2 user_task_3 user_task_4 user_task_5 user_task_6 user_task_7 \
    --injection-tasks injection_task_0 injection_task_1 injection_task_2 injection_task_3 injection_task_4 \
    --logdir runs/banking
```

### Other entry points

```bash
python scripts/selftest_metrics.py            # unit-test the metric primitives (offline)
python scripts/make_payloads.py workspace     # export real GOALs → multilingual payloads (offline)
```

---

## Outputs

Each `--logdir` contains:

| File | Contents |
|---|---|
| `mamori_metrics.csv` / `.json` | Per-cell `asr`, `utility_under_attack`, `gap_vs_english`, `defense_delta` |
| `translation_provenance.json` | Per-payload translation method (human-verified / scaffold / MT / code-switch fallback) |
| `leaderboard.csv` / `.json` | Configurations ranked by cross-lingual robustness |

Metric definitions:

- **ASR(A, D, ℓ)** — probability the agent executes the attacker task under defense `D` in language `ℓ`.
- **Utility-under-attack** — probability the benign user task completes while the attack is present.
- **Defense Δ** — `ASR(no-defense) − ASR(D)`; positive means the defense reduced attack success.
- **Cross-lingual gap** — `Gap(ℓ) = ASR(ℓ) − ASR(English)`; the safety lost relative to an English-only evaluation.

---

## Preliminary results

Evaluated on **gpt-4o-mini**, *n = 40 task pairs per cell*, with 95% Wilson confidence intervals. No-defense attack success rate (ASR; lower is safer), workspace suite, plain mode:

| Language | Resource | Script | ASR | 95% CI |
|---|---|---|---|---|
| English | high | Latin | **0.35** | [0.22, 0.50] |
| German | **high** | Latin | 0.975 | [0.87, 1.00] |
| Turkish | mid | Latin | 1.00 | [0.91, 1.00] |
| Korean | mid | Hangul | 1.00 | [0.91, 1.00] |
| Arabic | mid | Arabic | 1.00 | [0.91, 1.00] |
| Swahili | low | Latin | 0.80 | [0.65, 0.90] |

**Headline findings:**

1. **The vulnerability is English-specific, not resource-graded.** English (35%) is the lone low-ASR outlier; *every* other language — including high-resource **German (97.5%)** — is attacked 65–100% of the time. German is the control: it has as much training data as English yet behaves like the non-English cluster, so the weakness tracks *English*, not resource scarcity. (English CI does not overlap any other language's.)
2. **No English-tuned defense transfers; some backfire.** Across all defenses and **two environments** (workspace + banking), defense effectiveness Δ is **≤ 0 in every non-English language** (exactly 0.00 on Turkish/Korean/Arabic), while the detector collapses benign utility to near zero.
3. **Transliteration evades the detector across two scripts.** Korean *and* Arabic transliteration ("Arabizi") both hold ASR at 1.00 with detector Δ = 0.00 — the English-trained detector is blind to non-Latin scripts and their Latin transliterations alike.

**Replication:** the cross-lingual gap and the universal defense-failure both reproduce in the **banking** suite (English again lowest; every defense Δ ≤ +0.03 off English).

### Proposed metrics: ACLR and MSI

Because a real attacker chooses the injection language, single-language ASR overstates security. We propose two reusable metrics over a family **ℒ** of language/script/variant renderings:

- **ACLR** (Adversarial Cross-Lingual Robustness) = `1 − maxₗ ASR(ℓ)` — worst-case resistance against a language-choosing adversary.
- **MSI** (Multilingual Safety Illusion) = `(1 − ASR(en)) − ACLR` — how much an English-only number overstates true safety.

On the undefended agent: **ACLR = 0.00** (zero worst-case robustness) while an English-only report would claim 65% safety → **MSI = 0.65**. Every defense tested scores ACLR ≈ 0. See [`paper/`](paper/) for full definitions, properties, and worked examples.

*Scope: single model (gpt-4o-mini), a fixed task subset, two suites. Run the harness to regenerate every number; see `scripts/analyze.py`.*

---

## Repository structure

```
mamori/
├── mamori/
│   ├── languages.py        # language registry (resource level, script, morphology)
│   ├── translations.py     # verified carrier translations + goal scaffolds
│   ├── translator.py       # seed + literal-preserving goal translation; pluggable MT
│   ├── variants.py         # code-switching + transliteration generators; Mode enum
│   ├── attacks.py          # cross-lingual attacks registered into AgentDojo
│   ├── metrics.py          # ASR, utility, Δ, Gap(ℓ), ACLR, MSI
│   ├── harness.py          # model × defense × language × mode grid over AgentDojo
│   └── leaderboard.py      # robustness leaderboard aggregator
├── scripts/
│   ├── run_mamori.py       # main CLI
│   ├── analyze.py          # consolidate result CSVs → tables + H1–H4 verdicts (stdlib only)
│   ├── make_payloads.py    # export real GOALs → multilingual payloads
│   └── selftest_metrics.py # offline metric unit tests
├── results/                # exported payloads + result placeholders
├── paper/                  # results scaffold for the write-up
└── pyproject.toml
```

---

## How it works

MAMORI does **not** fork or reimplement AgentDojo. For each attack template it produces semantically faithful payloads in each target language (and code-switched / transliterated variants), wraps them in an attack class that **registers into AgentDojo's own attack registry**, and runs them through AgentDojo's stock `benchmark_suite_with_injections` runner with stock defenses. Translation provenance is recorded for every payload so that any cross-lingual degradation cannot be attributed to broken translations. Metrics, gaps, and the leaderboard are computed on top of AgentDojo's native utility/security scoring.

To scale translations beyond the verified seed set, register a machine-translation backend:

```python
from mamori.attacks import set_translator

class MyMT:
    name = "nllb-200-3.3B"
    def translate(self, text, lang, protect):
        ...  # translate EN→lang, leaving every string in `protect` untouched
        return translated

set_translator(MyMT())
```

---

## Cost & performance notes

- Runs are **sequential** by default; wall-clock scales with the number of `(user × injection)` pairs. Workspace ≈ 560 pairs/cell at full size; the smaller `banking`/`slack` suites are cheaper.
- Cost scales linearly with pairs. Use `--user-tasks` / `--injection-tasks` to subset, and a cheap model (e.g. `gpt-4o-mini`) for first results.
- Always run the **smoke test** first and read the real per-pair cost from your provider dashboard before launching a large grid.

---

## Ethics & responsible disclosure

This is **defensive** research. All attacker tasks are benign sandbox actions inside AgentDojo's simulated environments; the benchmark contains no instructions for real-world harm. Findings affecting specific deployed systems will be disclosed responsibly to the relevant vendors before public release. The released artifact is oriented toward defense development — including multilingual detector fine-tuning as a mitigation pointer.

---

## Citation

```bibtex
@misc{almamoori_mamori,
  title  = {MAMORI: A Cross-Lingual Benchmark for Indirect Prompt-Injection
            Robustness in Tool-Using LLM Agents},
  author = {Almamoori, Hayder},
  note   = {Department of Electrical and Electronics Engineering, Ege University},
  year   = {2026}
}
```

MAMORI builds on **AgentDojo** (Debenedetti et al., *NeurIPS Datasets & Benchmarks*, 2024); please cite it as well when using this benchmark.

---

## Acknowledgements

Built on [AgentDojo](https://github.com/ethz-spylab/agentdojo). Detector defense uses `protectai/deberta-v3-base-prompt-injection-v2`.
