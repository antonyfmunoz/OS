"""Unified Workstation Runtime — Campaign 18.0.

Single source of truth for workstation state. Composes 7 existing runtimes
into one read-only snapshot answering: "What is the organism doing? What
does the operator see? What needs attention?"

Read-only. No decisions. No execution. No mutation.
Aggregate → normalize → present.

WorkstationMode (what the operator is doing) and UnifiedWorkstationState
(what the organism is doing) are orthogonal — both visible simultaneously.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

logger = logging.getLogger(__name__)


# ── Types ─────────────────────────────────────────────────────────────────


class UnifiedWorkstationState(str, Enum):
    """What the organism is doing — derived deterministically."""
    IDLE = "idle"
    BUILDING = "building"
    GOVERNING = "governing"
    EXECUTING = "executing"
    MONITORING = "monitoring"
    DEGRADED = "degraded"


@dataclass
class UnifiedWorkstationSnapshot:
    workstation_state: str = UnifiedWorkstationState.IDLE.value
    organism_mode: str = "idle"
    execution_state: str = "idle"
    presence_mode: str = "listening"
    active_project: str = ""
    active_repo: str = ""
    active_panel: str = ""
    pending_approvals: int = 0
    active_delegations: int = 0
    active_risks: list[dict[str, Any]] = field(default_factory=list)
    attention_items: list[dict[str, Any]] = field(default_factory=list)
    subsystem_health: list[dict[str, Any]] = field(default_factory=list)
    organism_health: str = "unknown"
    coherence_score: float = 0.0
    generated_at: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "workstation_state": self.workstation_state,
            "organism_mode": self.organism_mode,
            "execution_state": self.execution_state,
            "presence_mode": self.presence_mode,
            "active_project": self.active_project,
            "active_repo": self.active_repo,
            "active_panel": self.active_panel,
            "pending_approvals": self.pending_approvals,
            "active_delegations": self.active_delegations,
            "active_risks": self.active_risks,
            "attention_items": self.attention_items,
            "subsystem_health": self.subsystem_health,
            "organism_health": self.organism_health,
            "coherence_score": self.coherence_score,
            "generated_at": self.generated_at,
        }


# ── Runtime ─────────────────────────────────────────────────────────


class UnifiedWorkstationRuntime:
    """Unified workstation state — composes 7 runtimes into one snapshot.

    Composes:
    - OrchestratorPresenceRuntime (C17.0): orchestrator mode, context
    - WorkstationPresenceRuntime (C17.2): device, panel, project
    - OrganismStateRuntime (C16.1): organism mode, health
    - GovernedExecutionRuntime (C16.0): execution state, blockers
    - OrganismPortfolioRuntime (C15.3): subsystem health scores
    - UnifiedApprovalRuntime (C4.2): pending approvals
    - CommandCenterMVPRuntime (C3): command center snapshot
    """

    def __init__(
        self,
        orchestrator_presence: Any | None = None,
        workstation_presence: Any | None = None,
        organism_state: Any | None = None,
        governed_execution: Any | None = None,
        organism_portfolio: Any | None = None,
        unified_approvals: Any | None = None,
        command_center: Any | None = None,
    ) -> None:
        self._orchestrator_presence_dep = orchestrator_presence
        self._workstation_presence_dep = workstation_presence
        self._organism_state_dep = organism_state
        self._governed_execution_dep = governed_execution
        self._organism_portfolio_dep = organism_portfolio
        self._unified_approvals_dep = unified_approvals
        self._command_center_dep = command_center

    # ── Lazy subsystem access ────────────────────────────────────

    @property
    def _orchestrator_presence(self) -> Any:
        if self._orchestrator_presence_dep is None:
            try:
                from substrate.workstation.orchestrator_presence_runtime import (
                    OrchestratorPresenceRuntime,
                )
                self._orchestrator_presence_dep = OrchestratorPresenceRuntime()
            except Exception:
                logger.debug("OrchestratorPresenceRuntime unavailable")
        return self._orchestrator_presence_dep

    @property
    def _workstation_presence(self) -> Any:
        if self._workstation_presence_dep is None:
            try:
                from substrate.workstation.workstation_presence_runtime import (
                    WorkstationPresenceRuntime,
                )
                self._workstation_presence_dep = WorkstationPresenceRuntime()
            except Exception:
                logger.debug("WorkstationPresenceRuntime unavailable")
        return self._workstation_presence_dep

    @property
    def _organism_state(self) -> Any:
        if self._organism_state_dep is None:
            try:
                from substrate.organism.organism_state_runtime import (
                    OrganismStateRuntime,
                )
                self._organism_state_dep = OrganismStateRuntime()
            except Exception:
                logger.debug("OrganismStateRuntime unavailable")
        return self._organism_state_dep

    @property
    def _governed_execution(self) -> Any:
        if self._governed_execution_dep is None:
            try:
                from substrate.organism.governed_execution_runtime import (
                    GovernedExecutionRuntime,
                )
                self._governed_execution_dep = GovernedExecutionRuntime()
            except Exception:
                logger.debug("GovernedExecutionRuntime unavailable")
        return self._governed_execution_dep

    @property
    def _organism_portfolio(self) -> Any:
        if self._organism_portfolio_dep is None:
            try:
                from substrate.organism.organism_portfolio_runtime import (
                    OrganismPortfolioRuntime,
                )
                self._organism_portfolio_dep = OrganismPortfolioRuntime()
            except Exception:
                logger.debug("OrganismPortfolioRuntime unavailable")
        return self._organism_portfolio_dep

    @property
    def _unified_approvals(self) -> Any:
        if self._unified_approvals_dep is None:
            try:
                from substrate.workstation.unified_approval_runtime import (
                    UnifiedApprovalRuntime,
                )
                self._unified_approvals_dep = UnifiedApprovalRuntime()
            except Exception:
                logger.debug("UnifiedApprovalRuntime unavailable")
        return self._unified_approvals_dep

    @property
    def _command_center(self) -> Any:
        if self._command_center_dep is None:
            try:
                from substrate.workstation.command_center_mvp_runtime import (
                    CommandCenterMVPRuntime,
                )
                self._command_center_dep = CommandCenterMVPRuntime()
            except Exception:
                logger.debug("CommandCenterMVPRuntime unavailable")
        return self._command_center_dep

    # ── Helpers ──────────────────────────────────────────────────

    def _safe_call(self, obj: Any, method: str, *args: Any) -> Any:
        if obj is None:
            return None
        try:
            fn = getattr(obj, method, None)
            if fn is None:
                return None
            return fn(*args)
        except Exception:
            logger.debug("safe_call %s.%s failed", type(obj).__name__, method)
            return None

    def _get_orchestrator_snapshot(self) -> dict[str, Any]:
        snap = self._safe_call(self._orchestrator_presence, "snapshot")
        if snap is None:
            return {}
        return snap.to_dict() if hasattr(snap, "to_dict") else {}

    def _get_workstation_snapshot(self) -> dict[str, Any]:
        snap = self._safe_call(self._workstation_presence, "snapshot")
        if snap is None:
            return {}
        return snap.to_dict() if hasattr(snap, "to_dict") else {}

    def _get_organism_snapshot(self) -> dict[str, Any]:
        snap = self._safe_call(self._organism_state, "snapshot")
        if snap is None:
            return {}
        return snap.to_dict() if hasattr(snap, "to_dict") else {}

    def _get_execution_assessment(self) -> dict[str, Any]:
        assess = self._safe_call(self._governed_execution, "assess")
        if assess is None:
            return {}
        return assess.to_dict() if hasattr(assess, "to_dict") else {}

    def _get_portfolio_snapshot(self) -> dict[str, Any]:
        snap = self._safe_call(self._organism_portfolio, "snapshot")
        if snap is None:
            return {}
        return snap.to_dict() if hasattr(snap, "to_dict") else {}

    def _get_approval_count(self) -> int:
        snap = self._safe_call(self._unified_approvals, "snapshot")
        if snap is None:
            return 0
        d = snap.to_dict() if hasattr(snap, "to_dict") else {}
        return d.get("pending_count", 0)

    # ── State Derivation ─────────────────────────────────────────

    def _derive_state(
        self,
        organism_mode: str,
        execution_state: str,
        pending_approvals: int,
        active_delegations: int,
        organism_health: str,
    ) -> UnifiedWorkstationState:
        if organism_health in ("critical", "fragmented"):
            return UnifiedWorkstationState.DEGRADED
        if organism_mode == "degraded":
            return UnifiedWorkstationState.DEGRADED
        if execution_state == "executing":
            return UnifiedWorkstationState.EXECUTING
        if organism_mode == "governing":
            return UnifiedWorkstationState.GOVERNING
        if execution_state in ("assessing", "governed"):
            return UnifiedWorkstationState.BUILDING
        if pending_approvals > 0 or active_delegations > 0:
            return UnifiedWorkstationState.MONITORING
        return UnifiedWorkstationState.IDLE

    # ── Public API ───────────────────────────────────────────────

    def snapshot(self) -> UnifiedWorkstationSnapshot:
        orch = self._get_orchestrator_snapshot()
        ws = self._get_workstation_snapshot()
        org = self._get_organism_snapshot()
        exe = self._get_execution_assessment()
        port = self._get_portfolio_snapshot()
        approval_count = self._get_approval_count()

        organism_mode = org.get("mode", "idle")
        execution_state = exe.get("state", "idle")
        organism_health = port.get("organism_health", "unknown")
        active_delegations = orch.get("active_delegation_count", 0)

        state = self._derive_state(
            organism_mode=organism_mode,
            execution_state=execution_state,
            pending_approvals=approval_count,
            active_delegations=active_delegations,
            organism_health=organism_health,
        )

        return UnifiedWorkstationSnapshot(
            workstation_state=state.value,
            organism_mode=organism_mode,
            execution_state=execution_state,
            presence_mode=orch.get("mode", "listening"),
            active_project=orch.get("active_project", "") or ws.get("active_project", ""),
            active_repo=orch.get("active_repo", "") or ws.get("active_repo", ""),
            active_panel=ws.get("active_panel", ""),
            pending_approvals=approval_count,
            active_delegations=active_delegations,
            active_risks=exe.get("top_blockers", []),
            attention_items=org.get("attention_items", []),
            subsystem_health=port.get("subsystem_health", []),
            organism_health=organism_health,
            coherence_score=port.get("coherence_score", 0.0),
            generated_at=time.time(),
        )

    def mode(self) -> str:
        snap = self.snapshot()
        return snap.workstation_state

    def attention(self) -> list[dict[str, Any]]:
        snap = self.snapshot()
        return snap.attention_items

    def risks(self) -> list[dict[str, Any]]:
        snap = self.snapshot()
        return snap.active_risks

    def summary(self) -> dict[str, Any]:
        snap = self.snapshot()
        return {
            "state": snap.workstation_state,
            "organism_mode": snap.organism_mode,
            "execution_state": snap.execution_state,
            "project": snap.active_project,
            "pending_approvals": snap.pending_approvals,
            "active_delegations": snap.active_delegations,
            "organism_health": snap.organism_health,
            "attention_count": len(snap.attention_items),
            "risk_count": len(snap.active_risks),
        }
