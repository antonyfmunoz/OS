"""UMH Capability Contracts — stable interfaces to wrapped external tools.

Each capability defines a contract that survives tool swaps.  Tier 1 harnesses
wrap external CLIs/services via subprocess; Tier 2 replaces them with native
rewrites.  License gate: Apache-2.0 / MIT / BSD only.
"""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


# ── Shared result type ────────────────────────────────────────────────────────


@dataclass
class CapabilityResult:
    """Standard result from any capability invocation."""

    success: bool
    output: Any = None
    files_changed: list[str] = field(default_factory=list)
    summary: str = ""
    duration_ms: float = 0.0
    error: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


# ── Base contract ─────────────────────────────────────────────────────────────


class CapabilityContract(ABC):
    """Base contract for all UMH capabilities."""

    capability_name: str
    harness_name: str  # current backing tool
    harness_license: str
    tier: int = 1  # 1=subprocess wrap, 2=native rewrite

    @abstractmethod
    async def invoke(self, **kwargs: Any) -> CapabilityResult:
        """Execute the capability with the given arguments."""
        ...

    @abstractmethod
    async def health_check(self) -> bool:
        """Return True if the backing tool is available and ready."""
        ...


# ── software_creation ─────────────────────────────────────────────────────────


@dataclass
class SoftwareCreationRequest:
    """Request payload for the software_creation capability."""

    task: str
    context: str = ""
    repo_path: Path | None = None
    language: str | None = None
    constraints: list[str] = field(default_factory=list)


class SoftwareCreationCapability(CapabilityContract):
    """Create or modify software via an external code generation tool."""

    capability_name = "software_creation"
    harness_name = "goose"  # placeholder — swappable
    harness_license = "Apache-2.0"

    @abstractmethod
    async def invoke(self, request: SoftwareCreationRequest, **kwargs: Any) -> CapabilityResult:  # type: ignore[override]
        ...

    @abstractmethod
    async def health_check(self) -> bool: ...


# ── desktop_control ───────────────────────────────────────────────────────────


@dataclass
class DesktopControlRequest:
    """Request payload for the desktop_control capability."""

    action: str  # "click", "type", "open_app", "screenshot", "navigate"
    target: str = ""
    parameters: dict[str, Any] = field(default_factory=dict)


class DesktopControlCapability(CapabilityContract):
    """Control desktop applications via an external GUI agent."""

    capability_name = "desktop_control"
    harness_name = "ui-tars-desktop"  # placeholder
    harness_license = "Apache-2.0"

    @abstractmethod
    async def invoke(self, request: DesktopControlRequest, **kwargs: Any) -> CapabilityResult:  # type: ignore[override]
        ...

    @abstractmethod
    async def health_check(self) -> bool: ...


# ── voice_interaction ─────────────────────────────────────────────────────────


@dataclass
class VoiceInteractionRequest:
    """Request payload for the voice_interaction capability."""

    audio_input: Path | None = None  # path to audio file
    text_input: str | None = None  # text to synthesize
    mode: str = "transcribe"  # "transcribe" | "synthesize" | "converse"


class VoiceInteractionCapability(CapabilityContract):
    """Voice transcription and synthesis via an external voice tool."""

    capability_name = "voice_interaction"
    harness_name = "voice-pro"  # placeholder
    harness_license = "TBD"

    @abstractmethod
    async def invoke(self, request: VoiceInteractionRequest, **kwargs: Any) -> CapabilityResult:  # type: ignore[override]
        ...

    @abstractmethod
    async def health_check(self) -> bool: ...


# ── creative_generation ───────────────────────────────────────────────────────


@dataclass
class CreativeGenerationRequest:
    """Request payload for the creative_generation capability."""

    prompt: str
    output_type: str  # "image" | "video" | "audio" | "3d"
    parameters: dict[str, Any] = field(default_factory=dict)
    output_dir: Path | None = None


class CreativeGenerationCapability(CapabilityContract):
    """Generate creative assets via an external generative AI tool."""

    capability_name = "creative_generation"
    harness_name = "open-generative-ai"  # placeholder
    harness_license = "TBD"

    @abstractmethod
    async def invoke(self, request: CreativeGenerationRequest, **kwargs: Any) -> CapabilityResult:  # type: ignore[override]
        ...

    @abstractmethod
    async def health_check(self) -> bool: ...
