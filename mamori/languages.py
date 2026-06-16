"""Language registry for MAMORI.

Each language carries the metadata needed to test the paper's hypotheses:

* ``resource_level``  -> H1 (ASR rises as resource level falls)
* ``script``          -> H2/H3 (non-Latin scripts stress tokenisers/detectors)
* ``morphology``      -> agglutinative vs. fusional vs. analytic (tokenisation stress)
* ``rtl``             -> right-to-left rendering (Arabic) as a confound to record

Resource levels follow the coarse taxonomy used in the cross-lingual safety
literature (Yong et al. 2023; Deng et al. 2024): HIGH (abundant pre-training +
safety data), MID, LOW (scarce). English is the reference cell against which
``Gap(l) = ASR(l) - ASR(English)`` is computed.

The two *adversarial conditions* from the proposal -- code-switching and
transliteration -- are not languages but payload *modes*; see ``variants.py``.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class ResourceLevel(str, Enum):
    HIGH = "high"
    MID = "mid"
    LOW = "low"


class Script(str, Enum):
    LATIN = "latin"
    HANGUL = "hangul"
    ARABIC = "arabic"


class Morphology(str, Enum):
    ANALYTIC = "analytic"        # English, Swahili-ish
    FUSIONAL = "fusional"        # German, Arabic
    AGGLUTINATIVE = "agglutinative"  # Turkish, Korean


@dataclass(frozen=True)
class Language:
    code: str                    # ISO 639-1/3 code used as the cell key
    name: str                    # human-readable name
    resource_level: ResourceLevel
    script: Script
    morphology: Morphology
    rtl: bool = False
    # Whether the *fixed carrier* translation shipped in translations.py has been
    # checked by a native/fluent speaker. The proposal promises native-speaker
    # verification on a sampled subset; we record provenance per language so a
    # degradation can never be silently blamed on a broken translation.
    carrier_verified: bool = False
    notes: str = ""


# ---------------------------------------------------------------------------
# The registry. English is always present as the reference.
# Turkish and Korean are foregrounded for venue relevance (Turkish is
# agglutinative; Korean uses a distinct script) exactly as the proposal states.
# ---------------------------------------------------------------------------
REGISTRY: dict[str, Language] = {
    "en": Language(
        code="en", name="English", resource_level=ResourceLevel.HIGH,
        script=Script.LATIN, morphology=Morphology.ANALYTIC,
        carrier_verified=True, notes="Reference cell.",
    ),
    "de": Language(
        code="de", name="German", resource_level=ResourceLevel.HIGH,
        script=Script.LATIN, morphology=Morphology.FUSIONAL,
        carrier_verified=True,
        notes="High-resource Latin-script control for the resource axis.",
    ),
    "tr": Language(
        code="tr", name="Turkish", resource_level=ResourceLevel.MID,
        script=Script.LATIN, morphology=Morphology.AGGLUTINATIVE,
        carrier_verified=True,
        notes="Agglutinative; stresses subword tokenisation. Venue language.",
    ),
    "ko": Language(
        code="ko", name="Korean", resource_level=ResourceLevel.MID,
        script=Script.HANGUL, morphology=Morphology.AGGLUTINATIVE,
        carrier_verified=True,
        notes="Distinct script + agglutinative; stresses tokenisation+detection.",
    ),
    "ar": Language(
        code="ar", name="Arabic", resource_level=ResourceLevel.MID,
        script=Script.ARABIC, morphology=Morphology.FUSIONAL, rtl=True,
        carrier_verified=True,
        notes="RTL non-Latin script; transliteration variant also provided.",
    ),
    "sw": Language(
        code="sw", name="Swahili", resource_level=ResourceLevel.LOW,
        script=Script.LATIN, morphology=Morphology.ANALYTIC,
        carrier_verified=False,
        notes="Low-resource Latin-script. Carrier pending native verification.",
    ),
}

# Convenience groupings used by the harness / plots.
DEFAULT_LANGUAGES: list[str] = ["en", "de", "tr", "ko", "ar", "sw"]


def get(code: str) -> Language:
    if code not in REGISTRY:
        raise KeyError(
            f"Unknown language '{code}'. Known: {sorted(REGISTRY)}. "
            "Add it to languages.REGISTRY and provide a carrier in translations.py."
        )
    return REGISTRY[code]


def by_resource(level: ResourceLevel) -> list[str]:
    return [c for c, l in REGISTRY.items() if l.resource_level == level]
