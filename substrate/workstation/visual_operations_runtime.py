"""Visual Operations Runtime — Campaign 21.4 (composition root).

Unified visual brain — composes all C21 sub-runtimes into one facade.
Single entry point for visual awareness queries. Methods map directly
to the five acceptance tests:

  what_am_i_looking_at()  → screen + context binding
  continue_this_work()    → context binding → work chain
  error_awareness()       → visual attention signals
  all_surfaces()          → environment awareness
  snapshot()              → full visual operations state

Composes:
  - ScreenAwarenessRuntime (C21.0)
  - EnvironmentAwarenessRuntime (C21.1)
  - VisualContextRuntime (C21.2)
  - AttentionVisionRuntime (C21.3)

C21 substrate workstation subsystem. Instance-agnostic.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

logger = logging.getLogger(__name__)


# ── Types ─────────────────────────────────────────────────────────────────


class VisualOperationsHealth(str, Enum):
    OPTIMAL = "optimal"
    ACTIVE = "active"
    DEGRADED = "degraded"
    OFFLINE = "offline"


@dataclass
class VisualCapabilityStatus:
    screen_awareness: bool = False
    environment_awareness: bool = False
    visual_context: bool = False
    attention_vision: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "screen_awareness": self.screen_awareness,
            "environment_awareness": self.environment_awareness,
            "visual_context": self.visual_context,
            "attention_vision": self.attention_vision,
        }


@dataclass
class VisualOperationsSnapshot:
    health: str = VisualOperationsHealth.OFFLINE.value
    screen_state: dict[str, Any] = field(default_factory=dict)
    environment: dict[str, Any] = field(default_factory=dict)
    context_binding: dict[str, Any] = field(default_factory=dict)
    visual_signals: list[dict[str, Any]] = field(default_factory=list)
    capabilities: dict[str, Any] = field(default_factory=dict)
    critical_count: int = 0
    warning_count: int = 0
    surface_count: int = 0
    generated_at: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "health": self.health,
            "screen_state": self.screen_state,
            "environment": self.environment,
            "context_binding": self.context_binding,
            "visual_signals": self.visual_signals,
            "capabilities": self.capabilities,
            "critical_count": self.critical_count,
            "warning_count": self.warning_count,
            "surface_count": self.surface_count,
            "generated_at": self.generated_at,
        }


# ── Runtime ───────────────────────────────────────────────────────────────


class VisualOperationsRuntime:
    """Unified visual operations — composes all C21 runtimes.

    Provides acceptance-test-aligned methods for the visual brain.
    All sub-runtimes use lazy accessors with graceful degradation.
    """

    def __init__(
        self,
        screen_awareness_runtime: Any | None = None,
        environment_awareness_runtime: Any | None = None,
        visual_context_runtime: Any | None = None,
        attention_vision_runtime: Any | None = None,
    ) -> None:
        self._screen_awareness_runtime = screen_awareness_runtime
        self._environment_awareness_runtime = environment_awareness_runtime
        self._visual_context_runtime = visual_context_runtime
        self._attention_vision_runtime = attention_vision_runtime

    # ── Lazy accessors ─────────────────────────────────────────────

    @property
    def screen_awareness_runtime(self) -> Any | None:
        if self._screen_awareness_runtime is None:
            try:
                from substrate.workstation.screen_awareness_runtime import (
                    ScreenAwarenessRuntime,
                )

                self._screen_awareness_runtime = ScreenAwarenessRuntime()
            except Exception:
                logger.debug("ScreenAwarenessRuntime unavailable")
        return self._screen_awareness_runtime

    @property
    def environment_awareness_runtime(self) -> Any | None:
        if self._environment_awareness_runtime is None:
            try:
                from substrate.workstation.environment_awareness_runtime import (
                    EnvironmentAwarenessRuntime,
                )

                self._environment_awareness_runtime = EnvironmentAwarenessRuntime()
            except Exception:
                logger.debug("EnvironmentAwarenessRuntime unavailable")
        return self._environment_awareness_runtime

    @property
    def visual_context_runtime(self) -> Any | None:
        if self._visual_context_runtime is None:
            try:
                from substrate.workstation.visual_context_runtime import (
                    VisualContextRuntime,
                )

                self._visual_context_runtime = VisualContextRuntime()
            except Exception:
                logger.debug("VisualContextRuntime unavailable")
        return self._visual_context_runtime

    @property
    def attention_vision_runtime(self) -> Any | None:
        if self._attention_vision_runtime is None:
            try:
                from substrate.workstation.attention_vision_runtime import (
                    AttentionVisionRuntime,
                )

                self._attention_vision_runtime = AttentionVisionRuntime()
            except Exception:
                logger.debug("AttentionVisionRuntime unavailable")
        return self._attention_vision_runtime

    # ── Acceptance test methods ────────────────────────────────────

    def what_am_i_looking_at(self) -> dict[str, Any]:
        """Acceptance test 1: full visual context response."""
        result: dict[str, Any] = {"query": "what_am_i_looking_at"}

        if self.screen_awareness_runtime is not None:
            try:
                snap = self.screen_awareness_runtime.snapshot()
                result["screen"] = snap.to_dict() if hasattr(snap, "to_dict") else {}
            except Exception:
                logger.debug("Screen awareness snapshot unavailable")
                result["screen_error"] = "unavailable"
        else:
            result["screen_error"] = "ScreenAwarenessRuntime unavailable"

        if self.visual_context_runtime is not None:
            try:
                binding = self.visual_context_runtime.resolve_context()
                result["context_binding"] = binding.to_dict() if hasattr(binding, "to_dict") else {}
            except Exception:
                logger.debug("Visual context resolution unavailable")
                result["context_error"] = "unavailable"
        else:
            result["context_error"] = "VisualContextRuntime unavailable"

        if self.attention_vision_runtime is not None:
            try:
                signals = self.attention_vision_runtime.critical_signals()
                result["critical_signals"] = [
                    s.to_dict() if hasattr(s, "to_dict") else s for s in signals
                ]
            except Exception:
                logger.debug("Attention vision unavailable")

        return result

    def continue_this_work(self) -> dict[str, Any]:
        """Acceptance test 2: resolve current screen into work chain."""
        if self.visual_context_runtime is not None:
            try:
                return self.visual_context_runtime.continue_work()
            except Exception:
                logger.debug("continue_work failed")
                return {"error": "context resolution failed"}
        return {"error": "VisualContextRuntime unavailable"}

    def error_awareness(self) -> dict[str, Any]:
        """Acceptance test 3: surface errors from screen observation."""
        result: dict[str, Any] = {"query": "error_awareness"}

        if self.attention_vision_runtime is not None:
            try:
                snap = self.attention_vision_runtime.snapshot()
                result["visual_signals"] = snap.to_dict() if hasattr(snap, "to_dict") else {}
                result["critical_count"] = snap.critical_count
                result["warning_count"] = snap.warning_count
            except Exception:
                logger.debug("Attention vision snapshot unavailable")
                result["error"] = "unavailable"
        else:
            result["error"] = "AttentionVisionRuntime unavailable"

        return result

    def all_surfaces(self) -> list[dict[str, Any]]:
        """Acceptance test 4: all observable surfaces."""
        if self.environment_awareness_runtime is not None:
            try:
                surfaces = self.environment_awareness_runtime.surfaces()
                return [s.to_dict() if hasattr(s, "to_dict") else s for s in surfaces]
            except Exception:
                logger.debug("Environment surfaces unavailable")
                return []
        return []

    # ── Snapshot & health ──────────────────────────────────────────

    def capabilities(self) -> VisualCapabilityStatus:
        """Which sub-runtimes are operational."""
        return VisualCapabilityStatus(
            screen_awareness=self._check_subsystem(self.screen_awareness_runtime),
            environment_awareness=self._check_subsystem(self.environment_awareness_runtime),
            visual_context=self._check_subsystem(self.visual_context_runtime),
            attention_vision=self._check_subsystem(self.attention_vision_runtime),
        )

    def health(self) -> VisualOperationsHealth:
        """Derive health from subsystem availability."""
        caps = self.capabilities()
        available = sum(
            [
                caps.screen_awareness,
                caps.environment_awareness,
                caps.visual_context,
                caps.attention_vision,
            ]
        )

        if available == 0:
            return VisualOperationsHealth.OFFLINE
        if available < 3:
            return VisualOperationsHealth.DEGRADED
        if available < 4:
            return VisualOperationsHealth.ACTIVE
        return VisualOperationsHealth.OPTIMAL

    def snapshot(self) -> VisualOperationsSnapshot:
        """Full composed snapshot from all sub-runtimes."""
        now = time.time()
        h = self.health()
        caps = self.capabilities()

        screen_state: dict[str, Any] = {}
        if self.screen_awareness_runtime is not None:
            try:
                s = self.screen_awareness_runtime.snapshot()
                screen_state = s.to_dict() if hasattr(s, "to_dict") else {}
            except Exception:
                logger.debug("Screen awareness snapshot unavailable")
                screen_state = {"error": "unavailable"}

        environment: dict[str, Any] = {}
        surface_count = 0
        if self.environment_awareness_runtime is not None:
            try:
                e = self.environment_awareness_runtime.snapshot()
                environment = e.to_dict() if hasattr(e, "to_dict") else {}
                surface_count = getattr(e, "active_count", 0) or 0
            except Exception:
                logger.debug("Environment snapshot unavailable")
                environment = {"error": "unavailable"}

        context_binding: dict[str, Any] = {}
        if self.visual_context_runtime is not None:
            try:
                binding = self.visual_context_runtime.resolve_context()
                context_binding = binding.to_dict() if hasattr(binding, "to_dict") else {}
            except Exception:
                logger.debug("Visual context unavailable")
                context_binding = {"error": "unavailable"}

        visual_signals: list[dict[str, Any]] = []
        critical_count = 0
        warning_count = 0
        if self.attention_vision_runtime is not None:
            try:
                att_snap = self.attention_vision_runtime.snapshot()
                visual_signals = getattr(att_snap, "visual_signals", []) or []
                critical_count = getattr(att_snap, "critical_count", 0) or 0
                warning_count = getattr(att_snap, "warning_count", 0) or 0
            except Exception:
                logger.debug("Attention vision snapshot unavailable")

        return VisualOperationsSnapshot(
            health=h.value,
            screen_state=screen_state,
            environment=environment,
            context_binding=context_binding,
            visual_signals=visual_signals,
            capabilities=caps.to_dict(),
            critical_count=critical_count,
            warning_count=warning_count,
            surface_count=surface_count,
            generated_at=now,
        )

    def summary(self) -> dict[str, Any]:
        """Compact summary."""
        h = self.health()
        caps = self.capabilities()
        available = sum(
            [
                caps.screen_awareness,
                caps.environment_awareness,
                caps.visual_context,
                caps.attention_vision,
            ]
        )
        return {
            "health": h.value,
            "subsystems_up": available,
            "subsystems_total": 4,
        }

    # ── Internal ───────────────────────────────────────────────────

    @staticmethod
    def _check_subsystem(runtime: Any | None) -> bool:
        """Check if a sub-runtime is available and responsive."""
        if runtime is None:
            return False
        try:
            if hasattr(runtime, "health"):
                h = runtime.health()
                if hasattr(h, "value"):
                    return h.value != "offline"
                return h != "offline"
            return True
        except Exception:
            logger.debug("Subsystem check failed for %s", type(runtime).__name__)
            return False
