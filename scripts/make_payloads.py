#!/usr/bin/env python3
"""Generate and export the full multilingual payload set.

Pulls the *real* injection-task GOALs from an AgentDojo suite and renders each
one as a fully-formed injection payload in every (language, mode), using the
verified carriers and the literal-preserving goal translator. Writes a JSON
artifact and prints a sample. Runs fully offline (no model, no keys).

This is the concrete "benchmark dataset" deliverable: every row is a payload an
attacker would embed in untrusted tool output, semantically equivalent across
languages, with the literal target values held identical.
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from agentdojo.task_suite.load_suites import get_suite
from mamori.translator import SeedTranslator
from mamori.variants import Mode, codeswitch_carrier, translit_carrier
from mamori.languages import DEFAULT_LANGUAGES, get as get_lang

USER = "Emma Johnson"
MODEL = "AI assistant"
TRANSLATOR = SeedTranslator()


def render(goal: str, lang: str, mode: Mode) -> dict:
    translated_goal, rec = TRANSLATOR.translate_goal(goal, lang)
    if mode == Mode.CODESWITCH:
        carrier = codeswitch_carrier()
    elif mode == Mode.TRANSLIT:
        carrier = translit_carrier(lang)
    else:
        carrier = TRANSLATOR.carrier(lang)[0]
    payload = carrier.format(goal=translated_goal, user=USER, model=MODEL)
    return {
        "lang": lang,
        "mode": mode.value,
        "resource_level": get_lang(lang).resource_level.value,
        "script": get_lang(lang).script.value,
        "carrier_verified": rec.carrier_verified,
        "goal_matched_scaffold": rec.goal_matched_scaffold,
        "goal_verified": rec.goal_verified,
        "goal_translator": rec.goal_translator,
        "codeswitch_fallback": rec.fallback_codeswitched,
        "translated_goal": translated_goal,
        "payload": payload,
    }


def main():
    suite_name = sys.argv[1] if len(sys.argv) > 1 else "workspace"
    suite = get_suite("v1.2.1", suite_name)

    out = {"suite": suite_name, "user_name": USER, "model_name": MODEL,
           "languages": DEFAULT_LANGUAGES, "injection_tasks": {}}

    n_payloads = 0
    for inj_id, inj_task in suite.injection_tasks.items():
        goal = inj_task.GOAL
        rows = []
        for lang in DEFAULT_LANGUAGES:
            rows.append(render(goal, lang, Mode.PLAIN))
            if lang != "en":
                rows.append(render(goal, lang, Mode.CODESWITCH))
            if lang in ("ar", "ko"):
                rows.append(render(goal, lang, Mode.TRANSLIT))
        out["injection_tasks"][inj_id] = {"english_goal": goal, "payloads": rows}
        n_payloads += len(rows)

    outdir = Path(__file__).resolve().parents[1] / "results"
    outdir.mkdir(parents=True, exist_ok=True)
    outfile = outdir / f"payloads_{suite_name}.json"
    outfile.write_text(json.dumps(out, indent=2, ensure_ascii=False))

    # Coverage report
    n_tasks = len(out["injection_tasks"])
    verified = sum(1 for t in out["injection_tasks"].values()
                   for p in t["payloads"] if p["goal_verified"])
    matched = sum(1 for t in out["injection_tasks"].values()
                  for p in t["payloads"] if p["goal_matched_scaffold"])
    fallback = sum(1 for t in out["injection_tasks"].values()
                   for p in t["payloads"] if p["codeswitch_fallback"])
    print(f"suite={suite_name}  injection_tasks={n_tasks}  payloads={n_payloads}")
    print(f"  goal scaffold matched : {matched}/{n_payloads}")
    print(f"  goal natively verified: {verified}/{n_payloads}")
    print(f"  code-switch fallback  : {fallback}/{n_payloads}")
    print(f"  wrote -> {outfile}")
    return out


if __name__ == "__main__":
    main()
