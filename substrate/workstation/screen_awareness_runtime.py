"""Screen Awareness Runtime — Campaign 21.0.

Thin composition over Phase 33 ScreenObservationEngine + workspace/presence.
Adds device-session binding and health derivation that Phase 33 does not
provide. Answers: "What am I looking at, on which device, in which session?"

Composes:
  - ScreenObservationEngine (substrate.operator)
  - WorkspaceAwarenessRuntime (substrate.organism)
  - PresenceRuntime (substrate.organism)

C21 substrate workstation subsystem. Instance-agnostic.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

logger = logging.getLogger(__name__)

_STALE_THRESHOLD_S = 120.0


# ── Types ─────────────────────────────────────────────────────────────────


class ScreenAwarenessHealth(str, Enum):
    ACTIVE = "active"
    STALE = "stale"
    DEGRADED = "degraded"
    OFFLINE = "offline"


@dataclass
class DeviceScreenBinding:
    device_id: str = ""
    device_role: str = ""
    session_id: str = ""
    source_type: str = ""
    provider_status: str = ""
    confidence: float = 0.0
    bound_at: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "device_id": self.device_id,
            "device_role": self.device_role,
            "session_id": self.session_id,
            "source_type": self.source_type,
            "provider_status": self.provider_status,
            "confidence": self.confidence,
            "bound_at": self.bound_at,
        }


@dataclass
class ScreenAwarenessSnapshot:
    health: str = ScreenAwarenessHealth.OFFLINE.value
    current_screen: dict[str, Any] = field(default_factory=dict)
    device_binding: dict[str, Any] = field(default_factory=dict)
    workspace_context: dict[str, Any] = field(default_factory=dict)
    provider_status: dict[str, Any] = field(default_factory=dict)
    history_count: int = 0
    generated_at: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "health": self.health,
            "current_screen": self.current_screen,
            "device_binding": self.device_binding,
            "workspace_context": self.workspace_context,
            "provider_status": self.provider_status,
            "history_count": self.history_count,
            "generated_at": self.generated_at,
        }


# ── Runtime ───────────────────────────────────────────────────────────────


class ScreenAwarenessRuntime:
    """Composed screen awareness — device-bound, session-aware."""

    def __init__(
        self,
        screen_observation_engine: Any | None = None,
        workspace_awareness_runtime: Any | None = None,
        presence_runtime: Any | None = None,
    ) -> None:
        self._screen_observation_engine = screen_observation_engine
        self._workspace_awareness_runtime = workspace_awareness_runtime
        self._presence_runtime = presence_runtime

    # ── Lazy accessors ─────────────────────────────────────────────

    @property
    def screen_observation_engine(self) -> Any | None:
        if self._screen_observation_engine is None:
            try:
                from substrate.operator.screen_observation_engine import (
                    ScreenObservationEngine,
                )

                self._screen_observation_engine = ScreenObservationEngine()
            except Exception:
                logger.debug("ScreenObservationEngine unavailable")
        return self._screen_observation_engine

    @property
    def workspace_awareness_runtime(self) -> Any | None:
        if self._workspace_awareness_runtime is None:
            try:
                from substrate.organism.workspace_awareness import (
                    WorkspaceAwarenessRuntime,
                )

                self._workspace_awareness_runtime = WorkspaceAwarenessRuntime()
            except Exception:
                logger.debug("WorkspaceAwarenessRuntime unavailable")
        return self._workspace_awareness_runtime

    @property
    def presence_runtime(self) -> Any | None:
        if self._presence_runtime is None:
            try:
                from substrate.organism.presence_runtime import (
                    get_presence_runtime,
                )

                self._presence_runtime = get_presence_runtime()
            except Exception:
                logger.debug("PresenceRuntime unavailable")
        return self._presence_runtime

    # ── Helpers ────────────────────────────────────────────────────

    @staticmethod
    def _safe_call(fn: Any, default: Any = None) -> Any:
        try:
            return fn()
        except Exception:
            logger.debug("_safe_call failed for %s", fn)
            return default

    # ── Public API ─────────────────────────────────────────────────

    def current_screen(self) -> dict[str, Any]:
        engine = self.screen_observation_engine
        if engine is None:
            return {"error": "ScreenObservationEngine unavailable"}
        snap = self._safe_call(engine.current_snapshot)
        if snap is None:
            return {"error": "snapshot unavailable"}
        return snap.to_dict() if hasattr(snap, "to_dict") else {}

    def device_binding(self) -> DeviceScreenBinding:
        binding = DeviceScreenBinding(bound_at=time.time())

        engine = self.screen_observation_engine
        if engine is not None:
            snap = self._safe_call(engine.current_snapshot)
            if snap is not None:
                binding.source_type = getattr(snap, "source_type", "")
                if hasattr(binding.source_type, "value"):
                    binding.source_type = binding.source_type.value
                binding.device_id = getattr(snap, "source_device_id", "") or getattr(
                    snap, "device_id", ""
                )
                binding.device_role = getattr(snap, "source_device_role", "")
                binding.confidence = getattr(snap, "source_confidence", 0.0)

            provider_st = self._safe_call(engine.provider_status, {})
            if provider_st:
                for name, info in provider_st.items():
                    if info.get("available"):
                        binding.provider_status = name
                        break

        presence = self.presence_runtime
        if presence is not None:
            p_snap = self._safe_call(presence.capture_snapshot)
            if p_snap is not None:
                session = getattr(p_snap, "active_session", None)
                if session:
                    binding.session_id = getattr(session, "session_id", "") or str(session)

        return binding

    def health(self) -> ScreenAwarenessHealth:
        engine = self.screen_observation_engine
        if engine is None:
            return ScreenAwarenessHealth.OFFLINE

        snap = self._safe_call(engine.current_snapshot)
        if snap is None:
            return ScreenAwarenessHealth.OFFLINE

        status_val = getattr(snap, "status", None)
        if status_val is not None and hasattr(status_val, "value"):
            status_val = status_val.value

        if status_val == "unknown":
            return ScreenAwarenessHealth.OFFLINE

        age = time.time() - getattr(snap, "generated_at", 0.0)
        if age > _STALE_THRESHOLD_S:
            return ScreenAwarenessHealth.STALE

        provider_st = self._safe_call(engine.provider_status, {})
        if provider_st:
            available_count = sum(1 for v in provider_st.values() if v.get("available"))
            if available_count == 0:
                return ScreenAwarenessHealth.OFFLINE
            if available_count < len(provider_st):
                return ScreenAwarenessHealth.DEGRADED

        return ScreenAwarenessHealth.ACTIVE

    def application(self) -> dict[str, Any]:
        screen = self.current_screen()
        app = screen.get("active_application")
        return app if app else {}

    def repository(self) -> dict[str, Any]:
        screen = self.current_screen()
        repo = screen.get("repository_context")
        return repo if repo else {}

    def file_context(self) -> dict[str, Any]:
        screen = self.current_screen()
        fc = screen.get("file_context")
        return fc if fc else {}

    def snapshot(self) -> ScreenAwarenessSnapshot:
        now = time.time()
        screen = self.current_screen()
        binding = self.device_binding()
        h = self.health()

        workspace_ctx: dict[str, Any] = {}
        ws_rt = self.workspace_awareness_runtime
        if ws_rt is not None:
            ws_snap = self._safe_call(ws_rt.detect_active_workspace)
            if ws_snap is not None:
                workspace_ctx = ws_snap.to_dict() if hasattr(ws_snap, "to_dict") else {}

        provider_st: dict[str, Any] = {}
        engine = self.screen_observation_engine
        if engine is not None:
            provider_st = self._safe_call(engine.provider_status, {})

        history_count = 0
        if engine is not None:
            hist = self._safe_call(lambda: engine.history(limit=0), [])
            history_count = len(self._safe_call(lambda: engine.history(limit=100), []))

        return ScreenAwarenessSnapshot(
            health=h.value,
            current_screen=screen,
            device_binding=binding.to_dict(),
            workspace_context=workspace_ctx,
            provider_status=provider_st,
            history_count=history_count,
            generated_at=now,
        )

    def summary(self) -> dict[str, Any]:
        h = self.health()
        screen = self.current_screen()
        app = screen.get("active_application", {})
        repo = screen.get("repository_context", {})
        return {
            "health": h.value,
            "application": app.get("app_name", "") if app else "",
            "repository": repo.get("repo_name", "") if repo else "",
            "branch": repo.get("branch", "") if repo else "",
            "source_type": screen.get("source_type", ""),
        }
