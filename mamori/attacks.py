"""Cross-lingual injection attacks for AgentDojo.

We extend AgentDojo's ``ImportantInstructionsAttack`` ("Important messages"
family) rather than rewriting the agent loop, exactly as the proposal specifies.
For each (language, mode) we synthesise a subclass that:

  * uses the per-language *carrier* (translated boilerplate) as its jailbreak
    template, and
  * translates the injection-task ``GOAL`` into the language (literal target
    values preserved) when building the concrete injection.

Each synthesised class is registered into AgentDojo's global ``ATTACKS`` registry
under a deterministic name, e.g. ``important_instructions__tr``,
``important_instructions__ko__codeswitch``, ``important_instructions__ar__translit``.
That means MAMORI attacks are first-class AgentDojo attacks: the stock
``agentdojo`` CLI and ``benchmark_suite_with_injections`` can load them by name.

The per-payload ``TranslationRecord`` is stashed on the attack instance
(``last_translation_records``) so the harness can log translation provenance.
"""
from __future__ import annotations

from typing import Type

from agentdojo.agent_pipeline.base_pipeline_element import BasePipelineElement
from agentdojo.attacks.attack_registry import register_attack, ATTACKS
from agentdojo.attacks.important_instructions_attacks import (
    ImportantInstructionsAttack,
    get_model_name_from_pipeline,
)
from agentdojo.base_tasks import BaseInjectionTask, BaseUserTask
from agentdojo.task_suite.task_suite import TaskSuite

from .languages import get as get_language
from .translator import SeedTranslator, MTBackend
from .variants import Mode, codeswitch_carrier, translit_carrier


# A module-level translator the synthesised classes share. Swap via
# ``set_translator`` before building attacks to plug an MT backend.
_TRANSLATOR = SeedTranslator()


def set_translator(mt_backend: MTBackend | None) -> None:
    global _TRANSLATOR
    _TRANSLATOR = SeedTranslator(mt_backend=mt_backend)


def attack_name(lang: str, mode: Mode) -> str:
    base = f"important_instructions__{lang}"
    return base if mode == Mode.PLAIN else f"{base}__{mode.value}"


def _carrier_for(lang: str, mode: Mode) -> str:
    if mode == Mode.CODESWITCH:
        return codeswitch_carrier()              # English frame, target-lang goal
    if mode == Mode.TRANSLIT:
        return translit_carrier(lang)            # Latin-script carrier
    return _TRANSLATOR.carrier(lang)[0]          # plain translated carrier


def build_attack_class(lang: str, mode: Mode = Mode.PLAIN) -> Type[ImportantInstructionsAttack]:
    """Synthesise and register a cross-lingual attack class for (lang, mode)."""
    get_language(lang)  # validates the language is known
    name = attack_name(lang, mode)
    if name in ATTACKS:                          # already registered
        return ATTACKS[name]  # type: ignore[return-value]

    carrier = _carrier_for(lang, mode)

    class _CrossLingualAttack(ImportantInstructionsAttack):
        # AgentDojo reads ``name`` at registration time.
        pass

    _CrossLingualAttack.name = name
    _CrossLingualAttack._lang = lang             # type: ignore[attr-defined]
    _CrossLingualAttack._mode = mode             # type: ignore[attr-defined]
    _CrossLingualAttack._JB_STRING = carrier     # the translated/variant carrier

    def __init__(self, task_suite: TaskSuite, target_pipeline: BasePipelineElement) -> None:  # noqa: N807
        # Bypass ImportantInstructionsAttack.__init__ (which hardcodes the
        # English _JB_STRING) and feed our carrier to FixedJailbreakAttack.
        from agentdojo.attacks.base_attacks import FixedJailbreakAttack
        FixedJailbreakAttack.__init__(self, carrier, task_suite, target_pipeline)
        self.user_name = "Emma Johnson"
        self.model_name = get_model_name_from_pipeline(target_pipeline)
        self.last_translation_records = []       # populated per generate

    def attack(self, user_task: BaseUserTask, injection_task: BaseInjectionTask) -> dict[str, str]:
        # Translate the GOAL into the target language (literals preserved).
        # In CODESWITCH mode the carrier is English but the GOAL is target-lang;
        # in TRANSLIT mode both carrier and (where covered) goal are Latinised.
        translated_goal, record = _TRANSLATOR.translate_goal(injection_task.GOAL, lang)
        self.last_translation_records.append((user_task.ID, injection_task.ID, record))
        injections: dict[str, str] = {}
        for inj in self.get_injection_candidates(user_task):
            injections[inj] = self.jailbreak.format(
                goal=translated_goal,
                user=self.user_name,
                model=self.model_name,
                task=self.summarize_task(user_task),
            )
        return injections

    _CrossLingualAttack.__init__ = __init__       # type: ignore[assignment]
    _CrossLingualAttack.attack = attack           # type: ignore[assignment]
    _CrossLingualAttack.__name__ = f"ImportantInstructions_{lang}_{mode.value}"
    _CrossLingualAttack.__qualname__ = _CrossLingualAttack.__name__

    register_attack(_CrossLingualAttack)
    return _CrossLingualAttack


def register_all(langs: list[str], modes: list[Mode]) -> list[str]:
    """Register every (lang, mode) cell; return the attack names registered."""
    names: list[str] = []
    for lang in langs:
        for mode in modes:
            # translit only applies to languages with a Latin-script carrier asset
            if mode == Mode.TRANSLIT and lang not in ("ar", "ko"):
                continue
            # codeswitch is meaningless for English (already the frame language)
            if mode == Mode.CODESWITCH and lang == "en":
                continue
            build_attack_class(lang, mode)
            names.append(attack_name(lang, mode))
    return names
