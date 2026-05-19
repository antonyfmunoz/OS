"""Runtime persona configuration — the user-facing AI identity.

The persona is a runtime value, never hardcoded. Each user/org
configures their own persona name, voice profile, and presentation
style. The substrate (UMH) is the platform; the persona is the face.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from enum import Enum


class PresentationStyle(Enum):
    CONCISE = "concise"
    CONVERSATIONAL = "conversational"
    FORMAL = "formal"
    TACTICAL = "tactical"


@dataclass(frozen=True)
class VoiceProfile:
    tone: str = "neutral"
    pace: str = "moderate"
    formality: str = "professional"


@dataclass
class Persona:
    name: str = ""
    voice_profile: VoiceProfile = field(default_factory=VoiceProfile)
    presentation_style: PresentationStyle = PresentationStyle.TACTICAL

    @classmethod
    def from_env(cls) -> Persona:
        return cls(
            name=os.environ.get("UMH_PERSONA_NAME", ""),
            voice_profile=VoiceProfile(
                tone=os.environ.get("UMH_PERSONA_TONE", "neutral"),
                pace=os.environ.get("UMH_PERSONA_PACE", "moderate"),
                formality=os.environ.get("UMH_PERSONA_FORMALITY", "professional"),
            ),
            presentation_style=PresentationStyle(
                os.environ.get("UMH_PERSONA_STYLE", "tactical")
            ),
        )

    @property
    def display_name(self) -> str:
        return self.name if self.name else "UMH"
