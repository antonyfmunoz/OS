"""Continuity Engine — operator presence and continuity aggregation.

Composes existing UMH subsystems to determine what the operator is
currently doing, what they were doing recently, and what should resume
after interruption. Observation only — no control, no synchronization,
no autonomous execution.

Cross-substrate composition (operator/ importing meta_ide/, organism/)
follows the same façade pattern as OperatorContextEngine (Phase 31).

Phase 32. UMH substrate subsystem. Instance-agnostic.
"""

from __future__ import annotations

import json
import logging
import os
import time
from typing import Any

from substrate.operator.operator_presence import (
    ActiveContext,
    ContinuityCheckpoint,
    ContinuityStatus,
    OperatorPresence,
    PresenceDeviceType,
    PresenceSnapshot,
    PresenceState,
)

logger = logging.getLogger(__name__)

_UMH_ROOT = os.environ.get("UMH_ROOT", "/opt/OS")

_CHECKPOINT_STALE_SECONDS = 3600
_CHECKPOINT_LOST_SECONDS = 86400

_DEVICE_TYPE_MAP = {
    "vps": PresenceDeviceType.VPS,
    "pc": PresenceDeviceType.WINDOWS,
    "tablet": PresenceDeviceType.IPAD,
    "mobile": PresenceDeviceType.IPHONE,
}


class ContinuityEngine:
    """Aggregation façade for operator presence and continuity."""

    def __init__(
        self,
        workspace_engine: Any = None,
        topology_engine: Any = None,
        action_bridge: Any = None,
        context_engine: Any = None,
        node_registry: Any = None,
    ) -> None:
        self._workspace_engine = workspace_engine
        self._topology_engine = topology_engine
        self._action_bridge = action_bridge
        self._context_engine = context_engine
        self._node_registry = node_registry

    # ── Lazy properties ──────────────────────────────────────────

    @property
    def workspace_engine(self) -> Any:
        if self._workspace_engine is None:
            try:
                from substrate.meta_ide.workspace_observation import (
                    WorkspaceObservationEngine,
                )
                self._workspace_engine = WorkspaceObservationEngine()
            except Exception:
                logger.debug("WorkspaceObservationEngine unavailable")
        return self._workspace_engine

    @property
    def topology_engine(self) -> Any:
        if self._topology_engine is None:
            try:
                from substrate.organism.workspace_topology_engine import (
                    WorkspaceTopologyEngine,
                )
                self._topology_engine = WorkspaceTopologyEngine()
            except Exception:
                logger.debug("WorkspaceTopologyEngine unavailable")
        return self._topology_engine

    @property
    def action_bridge(self) -> Any:
        if self._action_bridge is None:
            try:
                from substrate.organism.action_bridge import ActionBridge
                self._action_bridge = ActionBridge()
            except Exception:
                logger.debug("ActionBridge unavailable")
        return self._action_bridge

    @property
    def context_engine(self) -> Any:
        if self._context_engine is None:
            try:
                from substrate.operator.operator_context_engine import (
                    OperatorContextEngine,
                )
                self._context_engine = OperatorContextEngine()
            except Exception:
                logger.debug("OperatorContextEngine unavailable")
        return self._context_engine

    @property
    def node_registry(self) -> Any:
        if self._node_registry is None:
            try:
                from substrate.organism.umh_node_registry import UMHNodeRegistry
                self._node_registry = UMHNodeRegistry()
            except Exception:
                logger.debug("UMHNodeRegistry unavailable")
        return self._node_registry

    # ── Public API ───────────────────────────────────────────────

    def snapshot(self) -> PresenceSnapshot:
        """Full operator presence and continuity state."""
        presence = self.current_presence()
        context = self.active_context()
        checkpoints = self.continuity_checkpoints()

        return PresenceSnapshot(
            operator_state=presence.state,
            active_device=presence.device_type,
            active_device_id=presence.device_id,
            active_node_id=presence.node_id,
            active_context=context,
            continuity_checkpoints=checkpoints,
        )

    def current_presence(self) -> OperatorPresence:
        """Determine current operator presence from available signals."""
        device_type, device_id = self._detect_device()
        node_id = self._detect_node()
        state = self._determine_state()

        return OperatorPresence(
            state=state,
            device_type=device_type,
            device_id=device_id,
            node_id=node_id,
        )

    def active_context(self) -> ActiveContext:
        """What the operator is currently working on."""
        ws = self._get_workspace_context()
        session = self._get_session_context()
        runtime = self._get_runtime_context()

        return ActiveContext(
            workspace_id=ws.get("workspace_id", ""),
            workspace_name=ws.get("workspace_name", ""),
            session_id=session.get("session_id", ""),
            session_type=session.get("session_type", ""),
            runtime_id=runtime.get("runtime_id", ""),
            work_packet_id=self._get_active_work_packet_id(),
            description=ws.get("description", ""),
        )

    def continuity_checkpoints(self) -> list[ContinuityCheckpoint]:
        """Generate resumable checkpoints from current state."""
        checkpoints: list[ContinuityCheckpoint] = []
        now = time.time()

        checkpoints.extend(self._session_checkpoints(now))
        checkpoints.extend(self._approval_checkpoints(now))
        checkpoints.extend(self._workspace_checkpoints(now))

        for cp in checkpoints:
            cp.status = self._classify_checkpoint(cp, now)

        checkpoints.sort(key=lambda c: c.created_at, reverse=True)
        return checkpoints

    def resume_suggestion(self) -> dict[str, Any]:
        """Suggested resume state after interruption."""
        presence = self.current_presence()
        context = self.active_context()
        checkpoints = self.continuity_checkpoints()

        resumable = [
            c for c in checkpoints
            if c.status in (ContinuityStatus.CURRENT, ContinuityStatus.RESUMABLE)
        ]

        suggestion: dict[str, Any] = {
            "device": presence.device_type.value,
            "node": presence.node_id,
            "state": presence.state.value,
        }

        if context.workspace_name:
            suggestion["workspace"] = context.workspace_name

        if context.session_id:
            suggestion["session"] = {
                "id": context.session_id,
                "type": context.session_type,
            }

        if resumable:
            suggestion["resume_items"] = [
                {
                    "type": c.checkpoint_type,
                    "title": c.title,
                    "detail": c.detail,
                    "status": c.status.value,
                }
                for c in resumable[:5]
            ]

        suggestion["pending_approvals"] = self._get_pending_approval_count()

        return suggestion

    # ── Provider methods (composition boundary) ──────────────────

    def _detect_device(self) -> tuple[PresenceDeviceType, str]:
        """Determine device type from device registry + node hostname."""
        registry = self._load_device_registry()
        hostname = os.uname().nodename.lower()

        for device in registry:
            ts_name = device.get("tailscale_name", "").lower()
            if ts_name and ts_name in hostname:
                dev_type = _DEVICE_TYPE_MAP.get(
                    device.get("device_type", ""),
                    PresenceDeviceType.UNKNOWN,
                )
                return dev_type, device.get("id", "")

        if "srv" in hostname:
            return PresenceDeviceType.VPS, "vps"
        return PresenceDeviceType.UNKNOWN, ""

    def _detect_node(self) -> str:
        """Determine node ID from registry."""
        registry = self.node_registry
        if registry is None:
            return os.uname().nodename
        try:
            primary = registry.primary_node()
            if primary is not None:
                return primary.node_id
        except Exception:
            logger.debug("Failed to detect node", exc_info=True)
        return os.uname().nodename

    def _determine_state(self) -> PresenceState:
        """Determine operator state from signals."""
        ws = self.workspace_engine
        if ws is not None:
            try:
                snap = ws.latest()
                if snap is not None:
                    return PresenceState.ACTIVE
            except Exception:
                pass

        ctx = self.context_engine
        if ctx is not None:
            try:
                health = ctx.health_summary()
                if health.overall_status != "unknown":
                    return PresenceState.ACTIVE
            except Exception:
                pass

        return PresenceState.IDLE

    def _get_workspace_context(self) -> dict[str, Any]:
        """Current workspace from observation engine."""
        ws = self.workspace_engine
        if ws is None:
            return {}
        try:
            snap = ws.latest()
            if snap is None:
                return {}
            d = snap.to_dict()
            repos = d.get("repositories", [])
            if repos:
                return {
                    "workspace_id": repos[0].get("repo_id", ""),
                    "workspace_name": repos[0].get("name", ""),
                    "description": f"{len(repos)} repo(s) observed",
                }
            return {"description": "Workspace observed, no repos"}
        except Exception:
            logger.debug("Failed to get workspace context", exc_info=True)
            return {}

    def _get_session_context(self) -> dict[str, Any]:
        """Current session from workspace observation."""
        ws = self.workspace_engine
        if ws is None:
            return {}
        try:
            snap = ws.latest()
            if snap is None:
                return {}
            d = snap.to_dict()
            sessions = d.get("sessions", [])
            if sessions:
                s = sessions[0]
                return {
                    "session_id": s.get("session_id", ""),
                    "session_type": s.get("session_type", ""),
                }
            return {}
        except Exception:
            logger.debug("Failed to get session context", exc_info=True)
            return {}

    def _get_runtime_context(self) -> dict[str, Any]:
        """Current runtime from topology engine."""
        topo = self.topology_engine
        if topo is None:
            return {}
        try:
            snap = topo.snapshot()
            runtimes = snap.get("runtimes", []) if isinstance(snap, dict) else []
            if runtimes:
                return {"runtime_id": runtimes[0].get("runtime_id", "")}
            return {}
        except Exception:
            logger.debug("Failed to get runtime context", exc_info=True)
            return {}

    def _get_active_work_packet_id(self) -> str:
        """Active work packet from context engine."""
        ctx = self.context_engine
        if ctx is None:
            return ""
        try:
            approvals = ctx.pending_approvals()
            items = approvals.get("items", [])
            if items:
                return items[0].get("packet_id", "")
        except Exception:
            pass
        return ""

    def _get_pending_approval_count(self) -> int:
        """Pending approval count from context engine."""
        ctx = self.context_engine
        if ctx is None:
            return 0
        try:
            return ctx.pending_approvals().get("count", 0)
        except Exception:
            return 0

    # ── Checkpoint generators ────────────────────────────────────

    def _session_checkpoints(self, now: float) -> list[ContinuityCheckpoint]:
        """Checkpoints from engineering sessions."""
        checkpoints: list[ContinuityCheckpoint] = []
        session = self._get_session_context()
        if session.get("session_id"):
            device_type, device_id = self._detect_device()
            checkpoints.append(ContinuityCheckpoint(
                checkpoint_type="engineering_session",
                title=f"Engineering session: {session.get('session_type', 'unknown')}",
                detail=f"Session {session['session_id']}",
                device_type=device_type,
                device_id=device_id,
                session_id=session["session_id"],
                created_at=now,
            ))
        return checkpoints

    def _approval_checkpoints(self, now: float) -> list[ContinuityCheckpoint]:
        """Checkpoints from pending approvals."""
        checkpoints: list[ContinuityCheckpoint] = []
        ctx = self.context_engine
        if ctx is None:
            return checkpoints

        try:
            approvals = ctx.pending_approvals()
            count = approvals.get("count", 0)
            if count > 0:
                device_type, device_id = self._detect_device()
                checkpoints.append(ContinuityCheckpoint(
                    checkpoint_type="governance_review",
                    title=f"{count} pending approval(s)",
                    detail="Governance decisions awaiting operator input",
                    device_type=device_type,
                    device_id=device_id,
                    created_at=now,
                ))
        except Exception:
            logger.debug("Failed to create approval checkpoints", exc_info=True)

        return checkpoints

    def _workspace_checkpoints(self, now: float) -> list[ContinuityCheckpoint]:
        """Checkpoints from workspace activity."""
        checkpoints: list[ContinuityCheckpoint] = []
        ws_data = self._get_workspace_context()
        if ws_data.get("workspace_name"):
            device_type, device_id = self._detect_device()
            checkpoints.append(ContinuityCheckpoint(
                checkpoint_type="workspace_activity",
                title=f"Workspace: {ws_data['workspace_name']}",
                detail=ws_data.get("description", ""),
                device_type=device_type,
                device_id=device_id,
                workspace_id=ws_data.get("workspace_id", ""),
                created_at=now,
            ))
        return checkpoints

    def _classify_checkpoint(
        self, checkpoint: ContinuityCheckpoint, now: float
    ) -> ContinuityStatus:
        """Classify checkpoint freshness."""
        age = now - checkpoint.created_at

        if checkpoint.expires_at > 0 and now > checkpoint.expires_at:
            return ContinuityStatus.LOST

        if age < 300:
            return ContinuityStatus.CURRENT
        if age < _CHECKPOINT_STALE_SECONDS:
            return ContinuityStatus.RESUMABLE
        if age < _CHECKPOINT_LOST_SECONDS:
            return ContinuityStatus.STALE
        return ContinuityStatus.LOST

    # ── Helpers ──────────────────────────────────────────────────

    def _load_device_registry(self) -> list[dict[str, Any]]:
        """Load device registry from canonical location."""
        registry_path = os.path.join(_UMH_ROOT, "infra", "device_registry.json")
        try:
            with open(registry_path) as f:
                return json.load(f)
        except (OSError, json.JSONDecodeError):
            logger.debug("Device registry not found or invalid")
            return []
