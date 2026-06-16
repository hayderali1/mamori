"""Translation layer for MAMORI.

``Translator`` exposes two operations the attack layer needs:

* ``carrier(lang)``            -> the per-language fixed carrier template
* ``translate_goal(goal, lang)`` -> the GOAL with its scaffold translated and
  its literal target values (emails, ids, quoted payload text) preserved.

The default ``SeedTranslator`` is fully offline: it uses the verified assets in
``translations.py`` and performs NO network calls, so the benchmark is
reproducible and the *carrier* wording is controlled. For languages or GOAL
scaffolds not covered by the seed, you plug an ``MTBackend`` (NLLB, Google
Translate, GPT-4, ...) via ``SeedTranslator(mt_backend=...)``; uncovered GOALs
then get machine-translated with literal protection, and every such event is
recorded in ``provenance`` so coverage is auditable.

`TranslationRecord` accompanies every produced payload so the harness can log
*which* translator produced it and whether it was human-verified -- this is the
"translation-quality provenance" the proposal promises.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Protocol

from . import translations as T


@dataclass
class TranslationRecord:
    lang: str
    carrier_verified: bool
    carrier_translator: str
    goal_matched_scaffold: bool
    goal_verified: bool
    goal_translator: str
    fallback_codeswitched: bool = False


class MTBackend(Protocol):
    """Optional machine-translation backend for uncovered languages/scaffolds.

    Implementations must translate ``text`` from English into ``lang`` while
    leaving any substring in ``protect`` untouched (the caller passes the
    literal target values here).
    """

    name: str

    def translate(self, text: str, lang: str, protect: list[str]) -> str: ...


# Literal slots in AgentDojo GOALs are single-quoted; we also defensively
# protect anything that looks like an email or an opaque id token.
_QUOTED = re.compile(r"'(.+?)'")
_EMAILISH = re.compile(r"\b[\w.+-]+@[\w-]+\.[\w.-]+\b")
_IDISH = re.compile(r"\b[0-9a-fA-F]{6,}\b|\b\d{3,}\b")


def extract_literals(goal: str) -> list[str]:
    """Return the literal target values that must survive translation verbatim."""
    lits: list[str] = []
    lits += _QUOTED.findall(goal)
    lits += _EMAILISH.findall(goal)
    lits += _IDISH.findall(goal)
    # De-dup, longest first, so substrings of longer literals are protected too.
    seen: set[str] = set()
    out: list[str] = []
    for lit in sorted(lits, key=len, reverse=True):
        if lit and lit not in seen:
            seen.add(lit)
            out.append(lit)
    return out


class SeedTranslator:
    def __init__(self, mt_backend: MTBackend | None = None):
        self.mt = mt_backend

    # -- carrier -----------------------------------------------------------
    def carrier(self, lang: str) -> tuple[str, bool, str]:
        if lang in T.CARRIERS:
            c = T.CARRIERS[lang]
            return c.template, c.verified, c.translator
        if self.mt is not None:
            # Translate the English carrier but keep the placeholders intact.
            en = T.CARRIERS["en"].template
            translated = self.mt.translate(en, lang, protect=["{user}", "{model}", "{goal}"])
            return translated, False, self.mt.name
        raise KeyError(
            f"No verified carrier for '{lang}' and no MT backend supplied. "
            f"Add one to translations.CARRIERS or pass mt_backend=..."
        )

    # -- goal --------------------------------------------------------------
    def translate_goal(self, goal: str, lang: str) -> tuple[str, TranslationRecord]:
        carrier_tmpl, c_ver, c_tr = self.carrier(lang)

        if lang == "en":
            return goal, TranslationRecord(
                lang, c_ver, c_tr, goal_matched_scaffold=True,
                goal_verified=True, goal_translator="human",
            )

        # 1) Try the verified scaffolds (literal-preserving by construction).
        for sc in T.GOAL_SCAFFOLDS:
            m = re.match(sc.pattern, goal)
            if m and lang in sc.forms:
                literals = list(m.groups())
                translated = sc.forms[lang].format(*literals)
                return translated, TranslationRecord(
                    lang, c_ver, c_tr, goal_matched_scaffold=True,
                    goal_verified=sc.verified.get(lang, False),
                    goal_translator="human" if sc.verified.get(lang, False) else "human-draft",
                )

        # 2) MT fallback with literal protection, if a backend is available.
        if self.mt is not None:
            protect = extract_literals(goal)
            translated = self.mt.translate(goal, lang, protect=protect)
            return translated, TranslationRecord(
                lang, c_ver, c_tr, goal_matched_scaffold=False,
                goal_verified=False, goal_translator=self.mt.name,
            )

        # 3) Code-switch fallback: keep the English instruction inside the
        #    translated carrier. This is itself a legitimate (and reported)
        #    code-switched condition, but we flag it so coverage stays honest.
        return goal, TranslationRecord(
            lang, c_ver, c_tr, goal_matched_scaffold=False,
            goal_verified=False, goal_translator="codeswitch-fallback",
            fallback_codeswitched=True,
        )


# A tiny identity MT backend used only for offline smoke tests of the plumbing
# (it "translates" by tagging, never used for real results).
class _EchoMT:
    name = "echo-mt(test-only)"

    def translate(self, text: str, lang: str, protect: list[str]) -> str:
        return f"[{lang}] {text}"
