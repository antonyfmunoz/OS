"""Workstation Presence Runtime — operator footprint across the workstation.

Answers: "Where is the operator? What device, panel, project, last action?"

Tracks ephemeral operator state (active panel, last command, last approval)
and composes 5 existing subsystems for device/workspace/continuity awareness.

Ephemeral state is in-memory only — not persisted, recomputed on demand.

Campaign 17.2. UMH substrate layer. Instance-agnostic.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)


# ── Types ─────────────────────────────────────────────────────────────────


@dataclass
class WorkstationPresenceSnapshot:
    active_device: str = ""
    active_sessions: list[dict[str, Any]] = field(default_factory=list)
    active_panel: str = ""
    active_project: str = ""
    active_repo: str = ""
    last_command: dict[str, Any] = field(default_factory=dict)
    last_approval: dict[str, Any] = field(default_factory=dict)
    continuity_state: str = ""
    checkpoint_count: int = 0
    generated_at: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "active_device": self.active_device,
            "active_sessions": self.active_sessions,
            "active_panel": self.active_panel,
            "active_project": self.active_project,
            "active_repo": self.active_repo,
            "last_command": self.last_command,
            "last_approval": self.last_approval,
            "continuity_state": self.continuity_state,
            "checkpoint_count": self.checkpoint_count,
            "generated_at": self.generated_at,
        }


# ── Runtime ─────────────────────────────────────────────────────────


class WorkstationPresenceRuntime:
    """Operator footprint — device, panel, project, recent actions.

    Composes 5 subsystems:
    - DeviceAwarenessRuntime: active device detection
    - WorkspaceAwarenessRuntime: active workspace/repo
    - ContinuityEngine: session continuity state
    - UnifiedApprovalRuntime: recent approval decisions
    - DevicePresenceRegistry: active device sessions

    Holds lightweight ephemeral state (not persisted):
    - active_panel: updated via update_panel()
    - last_command: updated via record_command()
    """

    def __init__(
        self,
        device_awareness: Any | None = None,
        workspace_awareness: Any | None = None,
        continuity_engine: Any | None = None,
        unified_approvals: Any | None = None,
        device_presence: Any | None = None,
    ) -> None:
        self._device_awareness_dep = device_awareness
        self._workspace_awareness_dep = workspace_awareness
        self._continuity_engine_dep = continuity_engine
        self._unified_approvals_dep = unified_approvals
        self._device_presence_dep = device_presence

        self._active_panel: str = ""
        self._active_device_override: str = ""
        self._last_command_data: dict[str, Any] = {}
        self._active_context: dict[str, Any] = {}

    # ── Lazy subsystem access ───────────────────────────────────────

    @property
    def _device_awareness(self) -> Any | None:
        if self._device_awareness_dep is not None:
            return self._device_awareness_dep
        try:
            from substrate.organism.device_awareness import (
                DeviceAwarenessRuntime,
            )

            self._device_awareness_dep = DeviceAwarenessRuntime()
        except Exception as exc:
            logger.debug("ws_presence: device_awareness init failed: %s", exc)
        return self._device_awareness_dep

    @property
    def _workspace_awareness(self) -> Any | None:
        if self._workspace_awareness_dep is not None:
            return self._workspace_awareness_dep
        try:
            from substrate.organism.workspace_awareness import (
                WorkspaceAwarenessRuntime,
            )

            self._workspace_awareness_dep = WorkspaceAwarenessRuntime()
        except Exception as exc:
            logger.debug("ws_presence: workspace_awareness init failed: %s", exc)
        return self._workspace_awareness_dep

    @property
    def _continuity_engine(self) -> Any | None:
        if self._continuity_engine_dep is not None:
            return self._continuity_engine_dep
        try:
            from substrate.workstation.continuity_engine import (
                ContinuityEngine,
            )

            self._continuity_engine_dep = ContinuityEngine()
        except Exception as exc:
            logger.debug("ws_presence: continuity_engine init failed: %s", exc)
        return self._continuity_engine_dep

    @property
    def _unified_approvals(self) -> Any | None:
        if self._unified_approvals_dep is not None:
            return self._unified_approvals_dep
        try:
            from substrate.workstation.unified_approval_runtime import (
                UnifiedApprovalRuntime,
            )

            self._unified_approvals_dep = UnifiedApprovalRuntime()
        except Exception as exc:
            logger.debug("ws_presence: unified_approvals init failed: %s", exc)
        return self._unified_approvals_dep

    @property
    def _device_presence(self) -> Any | None:
        if self._device_presence_dep is not None:
            return self._device_presence_dep
        try:
            from substrate.workstation.device_presence import (
                DevicePresenceRegistry,
            )

            self._device_presence_dep = DevicePresenceRegistry()
        except Exception as exc:
            logger.debug("ws_presence: device_presence init failed: %s", exc)
        return self._device_presence_dep

    # ── Data extraction helpers ─────────────────────────────────────

    def _get_active_device(self) -> str:
        if self._active_device_override:
            return self._active_device_override
        try:
            if self._device_awareness is not None:
                return self._device_awareness.detect_active_device()
        except Exception as exc:
            logger.debug("ws_presence: active_device failed: %s", exc)
        return ""

    def _get_active_sessions(self) -> list[dict[str, Any]]:
        try:
            if self._device_presence is not None:
                sessions = self._device_presence.active_sessions()
                result: list[dict[str, Any]] = []
                for s in sessions[:10]:
                    if hasattr(s, "to_dict"):
                        result.append(s.to_dict())
                    elif isinstance(s, dict):
                        result.append(s)
                return result
        except Exception as exc:
            logger.debug("ws_presence: active_sessions failed: %s", exc)
        return []

    def _get_workspace(self) -> dict[str, Any]:
        try:
            if self._workspace_awareness is not None:
                snap = self._workspace_awareness.snapshot()
                return snap if isinstance(snap, dict) else {}
        except Exception as exc:
            logger.debug("ws_presence: workspace failed: %s", exc)
        return {}

    def _get_continuity_state(self) -> str:
        try:
            if self._continuity_engine is not None:
                if hasattr(self._continuity_engine, "state"):
                    s = self._continuity_engine.state()
                    return s.value if hasattr(s, "value") else str(s)
                elif hasattr(self._continuity_engine, "snapshot"):
                    snap = self._continuity_engine.snapshot()
                    if hasattr(snap, "to_dict"):
                        d = snap.to_dict()
                        return d.get("state", "unknown")
                    elif isinstance(snap, dict):
                        return snap.get("state", "unknown")
        except Exception as exc:
            logger.debug("ws_presence: continuity_state failed: %s", exc)
        return "unknown"

    def _get_checkpoint_count(self) -> int:
        try:
            if self._continuity_engine is not None:
                if hasattr(self._continuity_engine, "checkpoints"):
                    return len(self._continuity_engine.checkpoints())
        except Exception as exc:
            logger.debug("ws_presence: checkpoint_count failed: %s", exc)
        return 0

    def _get_last_approval(self) -> dict[str, Any]:
        try:
            if self._unified_approvals is not None:
                decisions = self._unified_approvals.recent_decisions(limit=1)
                if decisions:
                    d = decisions[0]
                    if hasattr(d, "to_dict"):
                        return d.to_dict()
                    elif isinstance(d, dict):
                        return d
        except Exception as exc:
            logger.debug("ws_presence: last_approval failed: %s", exc)
        return {}

    # ── Mutation API (ephemeral state) ──────────────────────────────

    def update_panel(self, panel_id: str) -> None:
        self._active_panel = panel_id

    def update_device(self, device_id: str) -> None:
        self._active_device_override = device_id

    def update_context(self, ctx: dict[str, Any]) -> None:
        self._active_context = ctx

    def record_command(self, cmd: dict[str, Any]) -> None:
        cmd["recorded_at"] = time.time()
        self._last_command_data = cmd

    # ── Read API ────────────────────────────────────────────────────

    def last_command(self) -> dict[str, Any]:
        return self._last_command_data

    def last_approval(self) -> dict[str, Any]:
        return self._get_last_approval()

    def snapshot(self) -> WorkstationPresenceSnapshot:
        workspace = self._get_workspace()

        return WorkstationPresenceSnapshot(
            active_device=self._get_active_device(),
            active_sessions=self._get_active_sessions(),
            active_panel=self._active_panel,
            active_project=self._active_context.get(
                "project", workspace.get("project", "")
            ),
            active_repo=self._active_context.get(
                "repo", workspace.get("repo", "")
            ),
            last_command=self._last_command_data,
            last_approval=self._get_last_approval(),
            continuity_state=self._get_continuity_state(),
            checkpoint_count=self._get_checkpoint_count(),
            generated_at=time.time(),
        )

    def summary(self) -> dict[str, Any]:
        return {
            "active_device": self._get_active_device(),
            "active_panel": self._active_panel,
            "session_count": len(self._get_active_sessions()),
            "continuity_state": self._get_continuity_state(),
            "has_recent_command": bool(self._last_command_data),
        }
