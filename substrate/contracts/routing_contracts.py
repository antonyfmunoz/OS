"""Routing contracts — substrate-owned capability classes and routing types.

Canonical location for symbolic capability labels. Adapters import from here.
Previously lived in adapters/models/routing/capabilities.py — moved to
enforce correct dependency direction (substrate owns contracts).
"""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field


class CapabilityClass(StrEnum):
    """12 symbolic capability classes covering the full routing surface."""

    BEST_CLOUD_REASONING = "best_cloud_reasoning"
    FAST_CLOUD_REASONING = "fast_cloud_reasoning"
    CHEAP_CLOUD_REASONING = "cheap_cloud_reasoning"
    LOCAL_FAST_MODEL = "local_fast_model"
    LOCAL_CODE_MODEL = "local_code_model"
    LOCAL_EMBEDDING_MODEL = "local_embedding_model"
    LOCAL_VISION_MODEL = "local_vision_model"
    LOCAL_TRANSCRIPTION_MODEL = "local_transcription_model"
    CLOUD_VISION_MODEL = "cloud_vision_model"
    LOCAL_TTS_MODEL = "local_tts_model"
    CLOUD_TTS_MODEL = "cloud_tts_model"
    LOCAL_STT_MODEL = "local_stt_model"


class PrivacyLevel(StrEnum):
    PUBLIC = "public"
    INTERNAL = "internal"
    CONFIDENTIAL = "confidential"
    RESTRICTED = "restricted"


class CapabilityEntry(BaseModel):
    """Full routing entry for a capability class."""

    model_config = ConfigDict(extra="forbid")

    capability_class: CapabilityClass
    preferred_provider_symbol: str
    fallback_provider_symbols: list[str] = Field(default_factory=list)
    privacy_level: PrivacyLevel = PrivacyLevel.INTERNAL
    max_cost_hint: str = "unlimited"
    local_first: bool = False
    notes: str = ""
