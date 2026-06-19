"""Session Machine Runtime — Campaign 19.2.

Unifies 4 existing runtimes into one operational model binding
machine → session → workspace → task.
Answers: Which device has which sessions? Which workspace is active?
Which session is primary? What handoffs are pending?

Read-only. No dispatch. No execute. No approve. No mutate.
Aggregate → normalize → present.

C19 substrate workstation subsystem. Instance-agnostic.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)


# ── Types ─────────────────────────────────────────────────────────────────


@dataclass
class MachineSessionBinding:
    device_id: str = ""
    device_display_name: str = ""
    device_type: str = ""
    online: bool = False
    sessions: list[dict[str, Any]] = field(default_factory=list)
    total_sessions: int = 0
    active_sessions: int = 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "device_id": self.device_id,
            "device_display_name": self.device_display_name,
            "device_type": self.device_type,
            "online": self.online,
            "sessions": self.sessions,
            "total_sessions": self.total_sessions,
            "active_sessions": self.active_sessions,
        }


@dataclass
class SessionMachineSnapshot:
    bindings: list[dict[str, Any]] = field(default_factory=list)
    total_devices: int = 0
    online_devices: int = 0
    total_sessions: int = 0
    active_sessions: int = 0
    primary_session: dict[str, Any] | None = None
    active_workspaces: list[dict[str, Any]] = field(default_factory=list)
    pending_handoffs: list[dict[str, Any]] = field(default_factory=list)
    continuity_links: list[dict[str, Any]] = field(default_factory=list)
    generated_at: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "bindings": self.bindings,
            "total_devices": self.total_devices,
            "online_devices": self.online_devices,
            "total_sessions": self.total_sessions,
            "active_sessions": self.active_sessions,
            "primary_session": self.primary_session,
            "active_workspaces": self.active_workspaces,
            "pending_handoffs": self.pending_handoffs,
            "continuity_links": self.continuity_links,
            "generated_at": self.generated_at,
        }


# ── Runtime ─────────────────────────────────────────────────────────


class SessionMachineRuntime:
    """Unified device→session→workspace→task view — composes 4 runtimes.

    Read-only. Aggregate → normalize → present.
    """

    def __init__(
        self,
        session_runtime: Any | None = None,
        presence_runtime: Any | None = None,
        workspace_awareness: Any | None = None,
        continuity_runtime: Any | None = None,
    ) -> None:
        self._session_runtime = session_runtime
        self._presence_runtime = presence_runtime
        self._workspace_awareness = workspace_awareness
        self._continuity_runtime = continuity_runtime

    # ── Lazy accessors ────────────────────────────────────────────────

    @property
    def _sessions(self) -> Any:
        if self._session_runtime is None:
            try:
                from substrate.organism.session_runtime import SessionRuntime
                self._session_runtime = SessionRuntime()
            except Exception:
                logger.debug("SessionRuntime unavailable")
        return self._session_runtime

    @property
    def _presence(self) -> Any:
        if self._presence_runtime is None:
            try:
                from substrate.organism.presence_runtime import PresenceRuntime
                self._presence_runtime = PresenceRuntime()
            except Exception:
                logger.debug("PresenceRuntime unavailable")
        return self._presence_runtime

    @property
    def _workspace(self) -> Any:
        if self._workspace_awareness is None:
            try:
                from substrate.organism.workspace_awareness import WorkspaceAwarenessRuntime
                self._workspace_awareness = WorkspaceAwarenessRuntime()
            except Exception:
                logger.debug("WorkspaceAwarenessRuntime unavailable")
        return self._workspace_awareness

    @property
    def _continuity(self) -> Any:
        if self._continuity_runtime is None:
            try:
                from substrate.organism.continuity_runtime import ContinuityRuntime
                self._continuity_runtime = ContinuityRuntime()
            except Exception:
                logger.debug("ContinuityRuntime unavailable")
        return self._continuity_runtime

    # ── Helpers ───────────────────────────────────────────────────────

    def _safe_call(self, obj: Any, method: str, *args: Any, **kwargs: Any) -> Any:
        if obj is None:
            return None
        fn = getattr(obj, method, None)
        if fn is None:
            return None
        try:
            return fn(*args, **kwargs)
        except Exception as exc:
            logger.debug("SessionMachineRuntime._safe_call(%s) failed: %s", method, exc)
            return None

    # ── Public API ────────────────────────────────────────────────────

    def snapshot(self) -> SessionMachineSnapshot:
        now = time.time()
        binding_list = self.bindings()
        all_sessions = self._get_all_sessions()
        active = [s for s in all_sessions if s.get("status") == "active"]
        primary = self.primary_session()
        workspaces = self.active_workspaces()
        handoffs = self._get_pending_handoffs()
        links = self._get_continuity_links()
        devices = self._get_devices()
        online = [d for d in devices if d.get("online", False)]

        binding_dicts = [b.to_dict() if hasattr(b, "to_dict") else b for b in binding_list]

        return SessionMachineSnapshot(
            bindings=binding_dicts,
            total_devices=len(devices),
            online_devices=len(online),
            total_sessions=len(all_sessions),
            active_sessions=len(active),
            primary_session=primary,
            active_workspaces=workspaces,
            pending_handoffs=handoffs,
            continuity_links=links,
            generated_at=now,
        )

    def bindings(self) -> list[MachineSessionBinding]:
        devices = self._get_devices()
        all_sessions = self._get_all_sessions()

        device_sessions: dict[str, list[dict[str, Any]]] = {}
        for s in all_sessions:
            device_id = s.get("device_id", "") or s.get("host", "") or "unknown"
            device_sessions.setdefault(device_id, []).append(s)

        result = []
        seen_devices: set[str] = set()
        for d in devices:
            did = d.get("device_id", "") or d.get("node_id", "")
            seen_devices.add(did)
            sessions = device_sessions.get(did, [])
            active_count = sum(1 for s in sessions if s.get("status") == "active")
            result.append(MachineSessionBinding(
                device_id=did,
                device_display_name=d.get("display_name", "") or d.get("name", ""),
                device_type=d.get("device_type", "") or d.get("type", ""),
                online=d.get("online", False),
                sessions=sessions,
                total_sessions=len(sessions),
                active_sessions=active_count,
            ))

        for did, sessions in device_sessions.items():
            if did not in seen_devices:
                active_count = sum(1 for s in sessions if s.get("status") == "active")
                result.append(MachineSessionBinding(
                    device_id=did,
                    device_display_name=did,
                    device_type="unknown",
                    online=False,
                    sessions=sessions,
                    total_sessions=len(sessions),
                    active_sessions=active_count,
                ))

        return result

    def active_workspaces(self) -> list[dict[str, Any]]:
        snap = self._safe_call(self._workspace, "detect_active_workspace")
        if snap and hasattr(snap, "to_dict"):
            ws = snap.to_dict()
            if ws.get("repo") or ws.get("directory"):
                return [ws]
        all_sessions = self._get_all_sessions()
        workspaces = []
        for s in all_sessions:
            if s.get("status") != "active":
                continue
            ws_info = s.get("workspace") or {}
            if isinstance(ws_info, str):
                ws_info = {"directory": ws_info}
            if ws_info.get("repo") or ws_info.get("directory") or ws_info.get("branch"):
                workspaces.append({
                    "device": s.get("device_id", "") or s.get("host", ""),
                    "repo": ws_info.get("repo", ""),
                    "branch": ws_info.get("branch", ""),
                    "directory": ws_info.get("directory", ""),
                })
        return workspaces

    def primary_session(self) -> dict[str, Any] | None:
        all_sessions = self._get_all_sessions()
        for s in all_sessions:
            authority = s.get("authority", "")
            if authority == "primary" or authority == "PRIMARY":
                return s
        active = [s for s in all_sessions if s.get("status") == "active"]
        if active:
            return active[0]
        return None

    def pending_handoffs(self) -> list[dict[str, Any]]:
        return self._get_pending_handoffs()

    def device_utilization(self) -> dict[str, Any]:
        binding_list = self.bindings()
        result: dict[str, Any] = {}
        for b in binding_list:
            result[b.device_id] = {
                "display_name": b.device_display_name,
                "total_sessions": b.total_sessions,
                "active_sessions": b.active_sessions,
                "online": b.online,
            }
        return result

    def summary(self) -> dict[str, Any]:
        snap = self.snapshot()
        return {
            "ok": True,
            "total_devices": snap.total_devices,
            "online_devices": snap.online_devices,
            "total_sessions": snap.total_sessions,
            "active_sessions": snap.active_sessions,
            "has_primary": snap.primary_session is not None,
            "active_workspace_count": len(snap.active_workspaces),
            "pending_handoff_count": len(snap.pending_handoffs),
            "continuity_link_count": len(snap.continuity_links),
            "generated_at": snap.generated_at,
        }

    # ── Internal data collection ──────────────────────────────────────

    def _get_devices(self) -> list[dict[str, Any]]:
        result = self._safe_call(self._presence, "list_devices")
        if result is None:
            result = self._safe_call(self._presence, "online_devices")
        if result is None:
            return []
        if isinstance(result, list):
            return [d.to_dict() if hasattr(d, "to_dict") else (d if isinstance(d, dict) else {}) for d in result]
        return []

    def _get_all_sessions(self) -> list[dict[str, Any]]:
        result = self._safe_call(self._sessions, "list_all_sessions")
        if result is None:
            result = self._safe_call(self._sessions, "list_active_sessions")
        if result is None:
            return []
        if isinstance(result, list):
            return [s.to_dict() if hasattr(s, "to_dict") else (s if isinstance(s, dict) else {}) for s in result]
        return []

    def _get_pending_handoffs(self) -> list[dict[str, Any]]:
        result = self._safe_call(self._sessions, "pending_handoffs")
        if result is None:
            result = self._safe_call(self._sessions, "list_pending_handoffs")
        if result is None:
            return []
        if isinstance(result, list):
            return [h.to_dict() if hasattr(h, "to_dict") else (h if isinstance(h, dict) else {}) for h in result]
        return []

    def _get_continuity_links(self) -> list[dict[str, Any]]:
        result = self._safe_call(self._continuity, "recent_handoffs")
        if result is None:
            result = self._safe_call(self._continuity, "get_work_lineage")
        if result is None:
            return []
        if isinstance(result, list):
            return [l.to_dict() if hasattr(l, "to_dict") else (l if isinstance(l, dict) else {}) for l in result]
        if hasattr(result, "to_dict"):
            return [result.to_dict()]
        return []
