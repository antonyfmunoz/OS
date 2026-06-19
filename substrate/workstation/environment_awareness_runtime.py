"""Environment Awareness Runtime — Campaign 21.1.

Aggregates all observable surfaces UMH can see into one view.
Answers: "What surfaces am I on? Desktop, cockpit, terminal, browser?"

Composes:
  - PresenceRuntime (devices, sessions)
  - SessionMachineRuntime (device→session bindings)
  - ScreenAwarenessRuntime (C21.0 — screen state)

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


class SurfaceType(str, Enum):
    """Observable interaction surface."""

    DESKTOP = "desktop"
    COCKPIT = "cockpit"
    TERMINAL = "terminal"
    BROWSER = "browser"
    IDE = "ide"
    CONTAINER = "container"
    MOBILE = "mobile"


class SurfaceHealth(str, Enum):
    """Health of an observed surface."""

    ACTIVE = "active"
    IDLE = "idle"
    STALE = "stale"
    OFFLINE = "offline"


_DEVICE_TYPE_TO_SURFACE: dict[str, SurfaceType] = {
    "workstation": SurfaceType.DESKTOP,
    "desktop": SurfaceType.DESKTOP,
    "pc": SurfaceType.DESKTOP,
    "vps": SurfaceType.TERMINAL,
    "server": SurfaceType.TERMINAL,
    "mobile": SurfaceType.MOBILE,
    "phone": SurfaceType.MOBILE,
    "tablet": SurfaceType.MOBILE,
    "ipad": SurfaceType.MOBILE,
    "iphone": SurfaceType.MOBILE,
}

_SESSION_TYPE_TO_SURFACE: dict[str, SurfaceType] = {
    "cockpit": SurfaceType.COCKPIT,
    "terminal": SurfaceType.TERMINAL,
    "ssh": SurfaceType.TERMINAL,
    "browser": SurfaceType.BROWSER,
    "ide": SurfaceType.IDE,
    "vscode": SurfaceType.IDE,
    "container": SurfaceType.CONTAINER,
    "docker": SurfaceType.CONTAINER,
}

_STALE_THRESHOLD_SECONDS = 300.0


@dataclass
class ObservedSurface:
    """A single observable interaction surface."""

    surface_type: str = SurfaceType.DESKTOP.value
    device_id: str = ""
    device_role: str = ""
    session_id: str = ""
    status: str = SurfaceHealth.OFFLINE.value
    detail: dict[str, Any] = field(default_factory=dict)
    last_seen: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "surface_type": self.surface_type,
            "device_id": self.device_id,
            "device_role": self.device_role,
            "session_id": self.session_id,
            "status": self.status,
            "detail": self.detail,
            "last_seen": self.last_seen,
        }


@dataclass
class EnvironmentAwarenessSnapshot:
    """Complete environment awareness state."""

    surfaces: list[dict[str, Any]] = field(default_factory=list)
    active_count: int = 0
    device_count: int = 0
    primary_surface: dict[str, Any] = field(default_factory=dict)
    camera_available: bool = False
    screen_available: bool = False
    generated_at: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "surfaces": self.surfaces,
            "active_count": self.active_count,
            "device_count": self.device_count,
            "primary_surface": self.primary_surface,
            "camera_available": self.camera_available,
            "screen_available": self.screen_available,
            "generated_at": self.generated_at,
        }


# ── Runtime ───────────────────────────────────────────────────────────────


class EnvironmentAwarenessRuntime:
    """Aggregates all observable surfaces into one environment view.

    Composes PresenceRuntime (devices/sessions), SessionMachineRuntime
    (device→session bindings), and ScreenAwarenessRuntime (screen state)
    to answer: "What surfaces does UMH observe right now?"
    """

    def __init__(
        self,
        presence_runtime: Any | None = None,
        session_machine_runtime: Any | None = None,
        screen_awareness_runtime: Any | None = None,
    ) -> None:
        self._presence_runtime = presence_runtime
        self._session_machine_runtime = session_machine_runtime
        self._screen_awareness_runtime = screen_awareness_runtime

    # ── Lazy accessors ─────────────────────────────────────────────

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

    @property
    def session_machine_runtime(self) -> Any | None:
        if self._session_machine_runtime is None:
            try:
                from substrate.workstation.session_machine_runtime import (
                    SessionMachineRuntime,
                )

                self._session_machine_runtime = SessionMachineRuntime()
            except Exception:
                logger.debug("SessionMachineRuntime unavailable")
        return self._session_machine_runtime

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

    # ── Surface discovery ──────────────────────────────────────────

    def _surface_from_device(self, device: dict[str, Any]) -> ObservedSurface:
        """Map a device dict to an ObservedSurface."""
        device_type = str(device.get("type", device.get("device_type", ""))).lower()
        surface_type = _DEVICE_TYPE_TO_SURFACE.get(
            device_type,
            SurfaceType.DESKTOP,
        ).value
        online = device.get("online", device.get("is_online", False))
        status = SurfaceHealth.ACTIVE.value if online else SurfaceHealth.OFFLINE.value
        return ObservedSurface(
            surface_type=surface_type,
            device_id=str(device.get("id", device.get("device_id", ""))),
            device_role=str(device.get("role", device.get("node_role", ""))),
            status=status,
            detail={"name": device.get("name", device.get("display_name", ""))},
            last_seen=float(device.get("last_seen", 0.0)),
        )

    def _surfaces_from_sessions(
        self,
        sessions: list[dict[str, Any]],
    ) -> list[ObservedSurface]:
        """Infer surfaces from active sessions."""
        surfaces: list[ObservedSurface] = []
        for session in sessions:
            client_type = str(
                session.get("client_type", session.get("control_surface", "")),
            ).lower()
            surface_type = _SESSION_TYPE_TO_SURFACE.get(client_type)
            if surface_type is None:
                continue
            now = time.time()
            last_active = float(session.get("last_active", session.get("started_at", now)))
            elapsed = now - last_active
            if elapsed > _STALE_THRESHOLD_SECONDS:
                status = SurfaceHealth.STALE.value
            else:
                status = SurfaceHealth.ACTIVE.value
            surfaces.append(
                ObservedSurface(
                    surface_type=surface_type.value,
                    device_id=str(session.get("device_id", session.get("host", ""))),
                    session_id=str(session.get("session_id", session.get("id", ""))),
                    status=status,
                    detail={
                        "profile_mode": session.get("profile_mode", ""),
                        "interaction_surface": session.get("interaction_surface", ""),
                    },
                    last_seen=last_active,
                )
            )
        return surfaces

    def surfaces(self) -> list[ObservedSurface]:
        """All observable surfaces from devices, sessions, and screen state."""
        result: list[ObservedSurface] = []
        seen_types: set[str] = set()

        # Device-based surfaces
        if self.presence_runtime is not None:
            try:
                devices = self.presence_runtime.get_online_devices()
                for dev in devices:
                    surface = self._surface_from_device(dev)
                    result.append(surface)
                    seen_types.add(surface.surface_type)
            except Exception:
                logger.debug("Failed to get devices for surfaces")

        # Session-based surfaces
        if self.presence_runtime is not None:
            try:
                sessions = self.presence_runtime.get_active_sessions()
                for surface in self._surfaces_from_sessions(sessions):
                    if surface.surface_type not in seen_types:
                        result.append(surface)
                        seen_types.add(surface.surface_type)
            except Exception:
                logger.debug("Failed to get sessions for surfaces")

        # Screen-aware desktop surface
        if self.screen_awareness_runtime is not None:
            try:
                screen = self.screen_awareness_runtime.current_screen()
                if screen and SurfaceType.DESKTOP.value not in seen_types:
                    result.append(
                        ObservedSurface(
                            surface_type=SurfaceType.DESKTOP.value,
                            status=SurfaceHealth.ACTIVE.value,
                            detail={"source": "screen_awareness"},
                            last_seen=time.time(),
                        )
                    )
            except Exception:
                logger.debug("Failed to get screen for surfaces")

        return result

    def active_surfaces(self) -> list[ObservedSurface]:
        """Only surfaces with ACTIVE health."""
        return [s for s in self.surfaces() if s.status == SurfaceHealth.ACTIVE.value]

    def primary_surface(self) -> ObservedSurface | None:
        """The surface the operator is currently focused on."""
        # Screen awareness tells us where focus is
        if self.screen_awareness_runtime is not None:
            try:
                screen = self.screen_awareness_runtime.current_screen()
                if screen:
                    app = screen.get("application", {})
                    category = str(app.get("category", "")).lower()
                    surface_type = SurfaceType.DESKTOP.value
                    if category == "ide":
                        surface_type = SurfaceType.IDE.value
                    elif category == "terminal":
                        surface_type = SurfaceType.TERMINAL.value
                    elif category == "browser":
                        surface_type = SurfaceType.BROWSER.value
                    return ObservedSurface(
                        surface_type=surface_type,
                        status=SurfaceHealth.ACTIVE.value,
                        detail={"focused": True, "application": app.get("app_name", "")},
                        last_seen=time.time(),
                    )
            except Exception:
                logger.debug("Failed to determine primary surface")

        # Fallback: first active surface
        active = self.active_surfaces()
        return active[0] if active else None

    def device_count(self) -> int:
        """Count of online devices."""
        if self.presence_runtime is not None:
            try:
                return len(self.presence_runtime.get_online_devices())
            except Exception:
                logger.debug("Failed to count devices")
        return 0

    def snapshot(self) -> EnvironmentAwarenessSnapshot:
        """Full environment awareness snapshot."""
        all_surfaces = self.surfaces()
        active = [s for s in all_surfaces if s.status == SurfaceHealth.ACTIVE.value]
        primary = self.primary_surface()

        screen_available = False
        if self.screen_awareness_runtime is not None:
            try:
                h = self.screen_awareness_runtime.health()
                screen_available = str(h) not in ("offline", "ScreenAwarenessHealth.OFFLINE")
            except Exception:
                logger.debug("Screen health check failed")

        return EnvironmentAwarenessSnapshot(
            surfaces=[s.to_dict() for s in all_surfaces],
            active_count=len(active),
            device_count=self.device_count(),
            primary_surface=primary.to_dict() if primary else {},
            camera_available=False,
            screen_available=screen_available,
            generated_at=time.time(),
        )

    def summary(self) -> dict[str, Any]:
        """Compact summary."""
        snap = self.snapshot()
        return {
            "active_surfaces": snap.active_count,
            "total_surfaces": len(snap.surfaces),
            "devices": snap.device_count,
            "screen_available": snap.screen_available,
            "camera_available": snap.camera_available,
            "primary": snap.primary_surface.get("surface_type", "none"),
        }
