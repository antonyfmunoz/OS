"""Personality preset system for UMH workstation.

Five personality presets define voice profile, presentation style,
governance level, and behavioral traits. Presets can be assigned
globally or per profile mode (multi-mode stacking).

Extends substrate Persona/PresentationStyle/VoiceProfile — this module
adds the preset layer on top, not replacing the substrate types.
"""

from __future__ import annotations

import json
import logging
import os
from dataclasses import asdict, dataclass, field
from enum import StrEnum

from umh import UMH_ROOT

logger = logging.getLogger(__name__)


class PersonalityPreset(StrEnum):
    """Five canonical personality presets."""

    OPERATOR = "operator"
    ADVISOR = "advisor"
    ANALYST = "analyst"
    CREATIVE = "creative"
    SENTINEL = "sentinel"


class GovernanceLevel(StrEnum):
    """How much autonomy the AI takes."""

    MINIMAL = "minimal"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    MAXIMUM = "maximum"


class ProactivityLevel(StrEnum):
    """How proactively the AI surfaces information."""

    ASK_FIRST = "ask_first"
    SUGGEST = "suggest"
    ACT = "act"


@dataclass(frozen=True)
class PersonalityTraits:
    """Behavioral characteristics for a personality preset."""

    tone: str
    pace: str
    formality: str
    style: str
    governance: GovernanceLevel
    proactivity: ProactivityLevel


PRESET_TRAITS: dict[PersonalityPreset, PersonalityTraits] = {
    PersonalityPreset.OPERATOR: PersonalityTraits(
        tone="direct",
        pace="fast",
        formality="minimal",
        style="tactical",
        governance=GovernanceLevel.HIGH,
        proactivity=ProactivityLevel.ACT,
    ),
    PersonalityPreset.ADVISOR: PersonalityTraits(
        tone="warm",
        pace="measured",
        formality="professional",
        style="coaching",
        governance=GovernanceLevel.MEDIUM,
        proactivity=ProactivityLevel.SUGGEST,
    ),
    PersonalityPreset.ANALYST: PersonalityTraits(
        tone="precise",
        pace="moderate",
        formality="professional",
        style="methodical",
        governance=GovernanceLevel.LOW,
        proactivity=ProactivityLevel.ASK_FIRST,
    ),
    PersonalityPreset.CREATIVE: PersonalityTraits(
        tone="expressive",
        pace="dynamic",
        formality="casual",
        style="associative",
        governance=GovernanceLevel.MEDIUM,
        proactivity=ProactivityLevel.SUGGEST,
    ),
    PersonalityPreset.SENTINEL: PersonalityTraits(
        tone="calm",
        pace="deliberate",
        formality="formal",
        style="cautious",
        governance=GovernanceLevel.MINIMAL,
        proactivity=ProactivityLevel.ASK_FIRST,
    ),
}


@dataclass
class PersonalityConfig:
    """Full personality configuration for a workstation instance.

    Supports three modes:
    1. Single preset — one preset applied globally
    2. Multi-mode — different preset per profile mode
    3. Custom — user-defined traits that override any preset
    """

    preset: PersonalityPreset = PersonalityPreset.OPERATOR
    mode_overrides: dict[str, str] = field(default_factory=dict)
    custom_traits: dict[str, str] = field(default_factory=dict)

    @property
    def traits(self) -> PersonalityTraits:
        """Get traits for the global preset."""
        if self.custom_traits:
            return PersonalityTraits(
                tone=self.custom_traits.get("tone", "neutral"),
                pace=self.custom_traits.get("pace", "moderate"),
                formality=self.custom_traits.get("formality", "professional"),
                style=self.custom_traits.get("style", "balanced"),
                governance=GovernanceLevel(self.custom_traits.get("governance", "medium")),
                proactivity=ProactivityLevel(self.custom_traits.get("proactivity", "suggest")),
            )
        return PRESET_TRAITS[self.preset]

    def traits_for_mode(self, profile_mode: str) -> PersonalityTraits:
        """Get traits for a specific profile mode.

        Falls back to the global preset if no mode override is set.
        """
        override = self.mode_overrides.get(profile_mode)
        if override:
            try:
                return PRESET_TRAITS[PersonalityPreset(override)]
            except ValueError:
                logger.debug("Unknown preset override for mode %s: %s", profile_mode, override)
        return self.traits

    def set_mode_override(self, profile_mode: str, preset: PersonalityPreset) -> None:
        """Assign a personality preset to a specific profile mode."""
        self.mode_overrides[profile_mode] = preset.value

    def clear_mode_override(self, profile_mode: str) -> None:
        self.mode_overrides.pop(profile_mode, None)

    @property
    def is_multi_mode(self) -> bool:
        return len(self.mode_overrides) > 0

    @property
    def is_custom(self) -> bool:
        return len(self.custom_traits) > 0

    def to_voice_profile_kwargs(self, profile_mode: str | None = None) -> dict[str, str]:
        """Get kwargs compatible with substrate VoiceProfile constructor."""
        t = self.traits_for_mode(profile_mode) if profile_mode else self.traits
        return {"tone": t.tone, "pace": t.pace, "formality": t.formality}

    def to_presentation_style(self, profile_mode: str | None = None) -> str:
        """Map personality style to substrate PresentationStyle value."""
        t = self.traits_for_mode(profile_mode) if profile_mode else self.traits
        style_map = {
            "tactical": "tactical",
            "coaching": "conversational",
            "methodical": "formal",
            "associative": "conversational",
            "cautious": "formal",
            "balanced": "tactical",
        }
        return style_map.get(t.style, "tactical")


PERSONALITY_FILE = os.path.join(UMH_ROOT, "data", "sessions", "personality.json")


def load_personality() -> PersonalityConfig:
    """Load personality config from disk, or return default."""
    if os.path.exists(PERSONALITY_FILE):
        try:
            with open(PERSONALITY_FILE, encoding="utf-8") as f:
                data = json.load(f)
            return PersonalityConfig(
                preset=PersonalityPreset(data.get("preset", "operator")),
                mode_overrides=data.get("mode_overrides", {}),
                custom_traits=data.get("custom_traits", {}),
            )
        except Exception as exc:
            logger.debug("Failed to load personality: %s", exc)
    return PersonalityConfig()


def save_personality(config: PersonalityConfig) -> None:
    """Save personality config to disk."""
    os.makedirs(os.path.dirname(PERSONALITY_FILE), exist_ok=True)
    try:
        with open(PERSONALITY_FILE, "w", encoding="utf-8") as f:
            json.dump(asdict(config), f, indent=2)
    except Exception as exc:
        logger.debug("Failed to save personality: %s", exc)


def show_personality() -> int:
    """Display current personality configuration."""
    config = load_personality()
    traits = config.traits
    print()
    print("=" * 42)
    print("  UMH Personality Configuration")
    print("=" * 42)
    print(f"  Preset:       {config.preset.value}")
    print(f"  Tone:         {traits.tone}")
    print(f"  Pace:         {traits.pace}")
    print(f"  Formality:    {traits.formality}")
    print(f"  Style:        {traits.style}")
    print(f"  Governance:   {traits.governance.value}")
    print(f"  Proactivity:  {traits.proactivity.value}")
    if config.is_multi_mode:
        print()
        print("  Mode Overrides:")
        for mode, preset in config.mode_overrides.items():
            print(f"    {mode}: {preset}")
    if config.is_custom:
        print()
        print("  (custom traits active — overriding preset)")
    print("=" * 42)
    print()
    return 0
