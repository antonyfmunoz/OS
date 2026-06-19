"""Orchestrator Presence Runtime — persistent presence layer for the primary orchestrator.

Answers: "What mode is the orchestrator in? What context is active? What's pending?"

Composes 8 existing subsystems into a single presence snapshot.
No mutation. No execution authority. Read-only presence coordination.

Campaign 17.0. UMH substrate layer. Instance-agnostic.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

logger = logging.getLogger(__name__)


# ── Types ─────────────────────────────────────────────────────────────────


class PresenceMode(str, Enum):
    LISTENING = "listening"
    CLARIFYING = "clarifying"
    PLANNING = "planning"
    WAITING_APPROVAL = "waiting_approval"
    MONITORING = "monitoring"
    DEGRADED = "degraded"


@dataclass
class OrchestratorPresenceSnapshot:
    mode: str = "listening"
    active_device: str = ""
    active_panel: str = ""
    active_project: str = ""
    active_repo: str = ""
    active_directory: str = ""
    pending_approval_count: int = 0
    active_delegation_count: int = 0
    organism_mode: str = "idle"
    execution_state: str = "idle"
    context_summary: dict[str, Any] = field(default_factory=dict)
    generated_at: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "mode": self.mode,
            "active_device": self.active_device,
            "active_panel": self.active_panel,
            "active_project": self.active_project,
            "active_repo": self.active_repo,
            "active_directory": self.active_directory,
            "pending_approval_count": self.pending_approval_count,
            "active_delegation_count": self.active_delegation_count,
            "organism_mode": self.organism_mode,
            "execution_state": self.execution_state,
            "context_summary": self.context_summary,
            "generated_at": self.generated_at,
        }


# ── Runtime ─────────────────────────────────────────────────────────


class OrchestratorPresenceRuntime:
    """Persistent orchestrator presence — mode, context, pending state.

    Composes 8 subsystems:
    - OrchestratorAwarenessRuntime: full 23-subsystem context
    - OrganismStateRuntime: organism mode/health
    - GovernedExecutionRuntime: execution state/assessment
    - ContextResolutionEngine: natural language → resolved context
    - WorkspaceAwarenessRuntime: active workspace detection
    - DeviceAwarenessRuntime: active device detection
    - UnifiedApprovalRuntime: pending approvals
    - DelegationReadinessRuntime: delegation coverage

    No mutation. No execution. Read-only presence.
    """

    def __init__(
        self,
        orchestrator_awareness: Any | None = None,
        organism_state: Any | None = None,
        governed_execution: Any | None = None,
        context_resolution: Any | None = None,
        workspace_awareness: Any | None = None,
        device_awareness: Any | None = None,
        unified_approvals: Any | None = None,
        delegation_readiness: Any | None = None,
    ) -> None:
        self._orchestrator_awareness_dep = orchestrator_awareness
        self._organism_state_dep = organism_state
        self._governed_execution_dep = governed_execution
        self._context_resolution_dep = context_resolution
        self._workspace_awareness_dep = workspace_awareness
        self._device_awareness_dep = device_awareness
        self._unified_approvals_dep = unified_approvals
        self._delegation_readiness_dep = delegation_readiness
        self._last_resolution: dict[str, Any] | None = None
        self._last_resolution_at: float = 0.0

    # ── Lazy subsystem access ───────────────────────────────────────

    @property
    def _orchestrator_awareness(self) -> Any | None:
        if self._orchestrator_awareness_dep is not None:
            return self._orchestrator_awareness_dep
        try:
            from substrate.organism.orchestrator_awareness_runtime import (
                OrchestratorAwarenessRuntime,
            )

            self._orchestrator_awareness_dep = OrchestratorAwarenessRuntime()
        except Exception as exc:
            logger.debug("presence: orchestrator_awareness init failed: %s", exc)
        return self._orchestrator_awareness_dep

    @property
    def _organism_state(self) -> Any | None:
        if self._organism_state_dep is not None:
            return self._organism_state_dep
        try:
            from substrate.organism.organism_state_runtime import (
                OrganismStateRuntime,
            )

            self._organism_state_dep = OrganismStateRuntime()
        except Exception as exc:
            logger.debug("presence: organism_state init failed: %s", exc)
        return self._organism_state_dep

    @property
    def _governed_execution(self) -> Any | None:
        if self._governed_execution_dep is not None:
            return self._governed_execution_dep
        try:
            from substrate.organism.governed_execution_runtime import (
                GovernedExecutionRuntime,
            )

            self._governed_execution_dep = GovernedExecutionRuntime()
        except Exception as exc:
            logger.debug("presence: governed_execution init failed: %s", exc)
        return self._governed_execution_dep

    @property
    def _context_resolution(self) -> Any | None:
        if self._context_resolution_dep is not None:
            return self._context_resolution_dep
        try:
            from substrate.organism.context_resolution import (
                ContextResolutionEngine,
            )

            self._context_resolution_dep = ContextResolutionEngine()
        except Exception as exc:
            logger.debug("presence: context_resolution init failed: %s", exc)
        return self._context_resolution_dep

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
            logger.debug("presence: workspace_awareness init failed: %s", exc)
        return self._workspace_awareness_dep

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
            logger.debug("presence: device_awareness init failed: %s", exc)
        return self._device_awareness_dep

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
            logger.debug("presence: unified_approvals init failed: %s", exc)
        return self._unified_approvals_dep

    @property
    def _delegation_readiness(self) -> Any | None:
        if self._delegation_readiness_dep is not None:
            return self._delegation_readiness_dep
        try:
            from substrate.organism.delegation_readiness_runtime import (
                DelegationReadinessRuntime,
            )

            self._delegation_readiness_dep = DelegationReadinessRuntime()
        except Exception as exc:
            logger.debug("presence: delegation_readiness init failed: %s", exc)
        return self._delegation_readiness_dep

    # ── Data extraction helpers ─────────────────────────────────────

    def _get_organism_mode(self) -> str:
        try:
            if self._organism_state is not None:
                m = self._organism_state.mode()
                return m.value if hasattr(m, "value") else str(m)
        except Exception as exc:
            logger.debug("presence: organism_mode failed: %s", exc)
        return "idle"

    def _get_organism_degraded(self) -> bool:
        try:
            if self._organism_state is not None:
                return self._organism_state.is_degraded()
        except Exception as exc:
            logger.debug("presence: is_degraded failed: %s", exc)
        return False

    def _get_execution_state(self) -> str:
        try:
            if self._governed_execution is not None:
                s = self._governed_execution.state()
                return s.value if hasattr(s, "value") else str(s)
        except Exception as exc:
            logger.debug("presence: execution_state failed: %s", exc)
        return "idle"

    def _get_pending_approvals(self) -> list[Any]:
        try:
            if self._unified_approvals is not None:
                return self._unified_approvals.pending()
        except Exception as exc:
            logger.debug("presence: pending_approvals failed: %s", exc)
        return []

    def _get_active_device(self) -> str:
        try:
            if self._device_awareness is not None:
                return self._device_awareness.detect_active_device()
        except Exception as exc:
            logger.debug("presence: active_device failed: %s", exc)
        return ""

    def _get_workspace_snapshot(self) -> dict[str, Any]:
        try:
            if self._workspace_awareness is not None:
                return self._workspace_awareness.snapshot()
        except Exception as exc:
            logger.debug("presence: workspace_snapshot failed: %s", exc)
        return {}

    def _get_delegation_count(self) -> int:
        try:
            if self._delegation_readiness is not None:
                snap = self._delegation_readiness.snapshot()
                if hasattr(snap, "to_dict"):
                    d = snap.to_dict()
                    return d.get("delegatable_count", 0)
        except Exception as exc:
            logger.debug("presence: delegation_count failed: %s", exc)
        return 0

    def _get_orchestrator_context(self) -> dict[str, Any]:
        try:
            if self._orchestrator_awareness is not None:
                ctx = self._orchestrator_awareness.context()
                if hasattr(ctx, "to_dict"):
                    return ctx.to_dict()
                return ctx if isinstance(ctx, dict) else {}
        except Exception as exc:
            logger.debug("presence: orchestrator_context failed: %s", exc)
        return {}

    # ── Mode classification (deterministic) ─────────────────────────

    def mode(self) -> PresenceMode:
        if self._get_organism_degraded():
            return PresenceMode.DEGRADED

        exec_state = self._get_execution_state()
        if exec_state == "executing":
            return PresenceMode.MONITORING

        pending = self._get_pending_approvals()
        if len(pending) > 0:
            return PresenceMode.WAITING_APPROVAL

        delegation_count = self._get_delegation_count()
        if delegation_count > 0:
            return PresenceMode.PLANNING

        if (
            self._last_resolution is not None
            and (time.time() - self._last_resolution_at) < 30.0
        ):
            return PresenceMode.CLARIFYING

        return PresenceMode.LISTENING

    # ── Public API ──────────────────────────────────────────────────

    def interpret(self, text: str) -> dict[str, Any]:
        """Resolve natural language into context. Delegates to ContextResolutionEngine."""
        try:
            if self._context_resolution is not None:
                resolved = self._context_resolution.resolve(text)
                result = resolved.to_dict() if hasattr(resolved, "to_dict") else {}
                self._last_resolution = result
                self._last_resolution_at = time.time()
                return result
        except Exception as exc:
            logger.debug("presence: interpret failed: %s", exc)
        return {"error": "context_resolution_unavailable"}

    def active_device(self) -> str:
        return self._get_active_device()

    def pending_approvals(self) -> list[dict[str, Any]]:
        approvals = self._get_pending_approvals()
        result: list[dict[str, Any]] = []
        for a in approvals[:20]:
            if hasattr(a, "to_dict"):
                result.append(a.to_dict())
            elif isinstance(a, dict):
                result.append(a)
            else:
                result.append({"id": str(a)})
        return result

    def active_delegations(self) -> list[dict[str, Any]]:
        try:
            if self._delegation_readiness is not None:
                snap = self._delegation_readiness.snapshot()
                if hasattr(snap, "to_dict"):
                    d = snap.to_dict()
                    return d.get("delegations", [])
        except Exception as exc:
            logger.debug("presence: active_delegations failed: %s", exc)
        return []

    def context(self) -> dict[str, Any]:
        return self._get_orchestrator_context()

    def snapshot(self) -> OrchestratorPresenceSnapshot:
        workspace = self._get_workspace_snapshot()
        ctx = self._get_orchestrator_context()

        return OrchestratorPresenceSnapshot(
            mode=self.mode().value,
            active_device=self._get_active_device(),
            active_panel=ctx.get("active_panel", ""),
            active_project=ctx.get("active_project", ""),
            active_repo=ctx.get("active_repo", ""),
            active_directory=ctx.get("active_directory", workspace.get("directory", "")),
            pending_approval_count=len(self._get_pending_approvals()),
            active_delegation_count=self._get_delegation_count(),
            organism_mode=self._get_organism_mode(),
            execution_state=self._get_execution_state(),
            context_summary={
                "workspace": workspace,
                "has_resolution": self._last_resolution is not None,
            },
            generated_at=time.time(),
        )

    def summary(self) -> dict[str, Any]:
        return {
            "mode": self.mode().value,
            "active_device": self._get_active_device(),
            "organism_mode": self._get_organism_mode(),
            "execution_state": self._get_execution_state(),
            "pending_approval_count": len(self._get_pending_approvals()),
            "active_delegation_count": self._get_delegation_count(),
        }
