"""Production Operations Runtime — Campaign 22.0.

Unified view of ALL software production work across every target
(substrate, projections, client products, tools, websites, automations).

Answers: What is being produced? What phase is it in? What ships next?
What is blocked? How many concurrent projects?

Phase is DERIVED, not stored. Reads subsystems deterministically.
Completion is outcome-based: a production is not done when code is generated,
only when proof passes and governance approves.

C22 substrate organism subsystem. Instance-agnostic.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

logger = logging.getLogger(__name__)


# ── Enums ────────────────────────────────────────────────────────────────


class ProductionPhase(str, Enum):
    IDLE = "idle"
    PLANNING = "planning"
    PRODUCING = "producing"
    REVIEWING = "reviewing"
    APPROVAL_PENDING = "approval_pending"
    SHIPPING = "shipping"
    LEARNING = "learning"
    DEGRADED = "degraded"


class ProductionTarget(str, Enum):
    SUBSTRATE = "substrate"
    PROJECTION = "projection"
    CLIENT_PRODUCT = "client_product"
    INTERNAL_TOOL = "internal_tool"
    WEBSITE = "website"
    AUTOMATION = "automation"


class ProductionHealth(str, Enum):
    OPTIMAL = "optimal"
    ACTIVE = "active"
    CONSTRAINED = "constrained"
    BLOCKED = "blocked"
    OFFLINE = "offline"


# ── Dataclasses ──────────────────────────────────────────────────────────


@dataclass
class ProductionEntry:
    """A single production unit tracked by the runtime."""

    production_id: str = ""
    target_type: str = ProductionTarget.SUBSTRATE.value
    goal: str = ""
    phase: str = ProductionPhase.IDLE.value
    packets: list[dict[str, Any]] = field(default_factory=list)
    quality_checks_passed: bool = False
    governance_approved: bool = False
    proof_assembled: bool = False
    blocked_reasons: list[str] = field(default_factory=list)
    started_at: float = 0.0
    completed_at: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "production_id": self.production_id,
            "target_type": self.target_type,
            "goal": self.goal,
            "phase": self.phase,
            "packet_count": len(self.packets),
            "quality_checks_passed": self.quality_checks_passed,
            "governance_approved": self.governance_approved,
            "proof_assembled": self.proof_assembled,
            "blocked_reasons": list(self.blocked_reasons),
            "started_at": self.started_at,
            "completed_at": self.completed_at,
        }


@dataclass
class ProductionSnapshot:
    """Aggregate view of all production activity."""

    phase: str = ProductionPhase.IDLE.value
    health: str = ProductionHealth.OFFLINE.value
    active_productions: list[dict[str, Any]] = field(default_factory=list)
    workforce: dict[str, Any] = field(default_factory=dict)
    pending_reviews: int = 0
    pending_approvals: int = 0
    blocked_count: int = 0
    queue_depth: int = 0
    concurrent_projects: int = 0
    session_context: dict[str, Any] = field(default_factory=dict)
    per_project_phases: dict[str, str] = field(default_factory=dict)
    generated_at: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "phase": self.phase,
            "health": self.health,
            "active_productions": self.active_productions,
            "workforce": self.workforce,
            "pending_reviews": self.pending_reviews,
            "pending_approvals": self.pending_approvals,
            "blocked_count": self.blocked_count,
            "queue_depth": self.queue_depth,
            "concurrent_projects": self.concurrent_projects,
            "session_context": self.session_context,
            "per_project_phases": dict(self.per_project_phases),
            "generated_at": self.generated_at,
        }


# ── Runtime ──────────────────────────────────────────────────────────────


class ProductionOpsRuntime:
    """Unified production operations view — composes 6 runtimes.

    Composes:
      - MetaIDERuntime: existing development loop skeleton
      - GovernedExecutionRuntime: execution state, blockers
      - ExecutionFabricRuntime: active executions, capacity
      - AgentWorkforceRuntime: agent health
      - SessionMachineRuntime: session bindings
      - MetaIdeContextRuntime: repo, branch, active files

    Phase derivation is deterministic — no stored state.
    Completion is outcome-based: proof + governance approval required.
    """

    def __init__(
        self,
        meta_ide: Any | None = None,
        governed_execution: Any | None = None,
        execution_fabric: Any | None = None,
        agent_workforce: Any | None = None,
        session_machine: Any | None = None,
        meta_ide_context: Any | None = None,
    ) -> None:
        self._meta_ide_dep = meta_ide
        self._governed_execution_dep = governed_execution
        self._execution_fabric_dep = execution_fabric
        self._agent_workforce_dep = agent_workforce
        self._session_machine_dep = session_machine
        self._meta_ide_context_dep = meta_ide_context

        self._productions: dict[str, ProductionEntry] = {}

    # ── Lazy subsystem access ────────────────────────────────────────

    @property
    def _meta_ide(self) -> Any | None:
        if self._meta_ide_dep is not None:
            return self._meta_ide_dep
        try:
            from substrate.organism.meta_ide_runtime import MetaIDERuntime

            class _MinimalFleet:
                def assign(self, **kw: Any) -> Any:
                    return type("A", (), {"agent_type": "", "to_dict": lambda s: {}})()

                def dispatch(self, assignment: Any, **kw: Any) -> Any:
                    return type("D", (), {"dispatch_id": "", "to_dict": lambda s: {}})()

            self._meta_ide_dep = MetaIDERuntime(agent_fleet=_MinimalFleet())
        except Exception as exc:
            logger.debug("production_ops: meta_ide init failed: %s", exc)
        return self._meta_ide_dep

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
            logger.debug("production_ops: governed_execution init failed: %s", exc)
        return self._governed_execution_dep

    @property
    def _execution_fabric(self) -> Any | None:
        if self._execution_fabric_dep is not None:
            return self._execution_fabric_dep
        try:
            from substrate.workstation.execution_fabric_runtime import (
                ExecutionFabricRuntime,
            )

            self._execution_fabric_dep = ExecutionFabricRuntime()
        except Exception as exc:
            logger.debug("production_ops: execution_fabric init failed: %s", exc)
        return self._execution_fabric_dep

    @property
    def _agent_workforce(self) -> Any | None:
        if self._agent_workforce_dep is not None:
            return self._agent_workforce_dep
        try:
            from substrate.workstation.agent_workforce_runtime import (
                AgentWorkforceRuntime,
            )

            self._agent_workforce_dep = AgentWorkforceRuntime()
        except Exception as exc:
            logger.debug("production_ops: agent_workforce init failed: %s", exc)
        return self._agent_workforce_dep

    @property
    def _session_machine(self) -> Any | None:
        if self._session_machine_dep is not None:
            return self._session_machine_dep
        try:
            from substrate.workstation.session_machine_runtime import (
                SessionMachineRuntime,
            )

            self._session_machine_dep = SessionMachineRuntime()
        except Exception as exc:
            logger.debug("production_ops: session_machine init failed: %s", exc)
        return self._session_machine_dep

    @property
    def _meta_ide_context(self) -> Any | None:
        if self._meta_ide_context_dep is not None:
            return self._meta_ide_context_dep
        try:
            from substrate.workstation.meta_ide_context_runtime import (
                MetaIdeContextRuntime,
            )

            self._meta_ide_context_dep = MetaIdeContextRuntime()
        except Exception as exc:
            logger.debug("production_ops: meta_ide_context init failed: %s", exc)
        return self._meta_ide_context_dep

    # ── Safe accessor helper ─────────────────────────────────────────

    def _safe_call(self, obj: Any, method: str, *args: Any, **kwargs: Any) -> Any:
        if obj is None:
            return None
        fn = getattr(obj, method, None)
        if fn is None:
            return None
        try:
            return fn(*args, **kwargs)
        except Exception as exc:
            logger.debug("production_ops._safe_call(%s) failed: %s", method, exc)
            return None

    # ── Production registration ──────────────────────────────────────

    def register_production(
        self,
        production_id: str,
        goal: str,
        target_type: str = ProductionTarget.SUBSTRATE.value,
        packets: list[dict[str, Any]] | None = None,
    ) -> ProductionEntry:
        entry = ProductionEntry(
            production_id=production_id,
            target_type=target_type,
            goal=goal,
            packets=packets or [],
            started_at=time.time(),
        )
        entry.phase = self._derive_entry_phase(entry)
        self._productions[production_id] = entry
        return entry

    def update_production_state(
        self,
        production_id: str,
        quality_checks_passed: bool | None = None,
        governance_approved: bool | None = None,
        proof_assembled: bool | None = None,
        blocked_reasons: list[str] | None = None,
    ) -> ProductionEntry | None:
        entry = self._productions.get(production_id)
        if entry is None:
            return None
        if quality_checks_passed is not None:
            entry.quality_checks_passed = quality_checks_passed
        if governance_approved is not None:
            entry.governance_approved = governance_approved
        if proof_assembled is not None:
            entry.proof_assembled = proof_assembled
        if blocked_reasons is not None:
            entry.blocked_reasons = blocked_reasons
        entry.phase = self._derive_entry_phase(entry)
        return entry

    # ── Phase derivation ─────────────────────────────────────────────

    def _derive_entry_phase(self, entry: ProductionEntry) -> str:
        if entry.blocked_reasons:
            return ProductionPhase.DEGRADED.value

        if not entry.packets:
            return ProductionPhase.PLANNING.value

        all_executed = self._all_packets_executed(entry)
        if not all_executed:
            return ProductionPhase.PRODUCING.value

        if not entry.quality_checks_passed:
            return ProductionPhase.REVIEWING.value

        if not entry.governance_approved:
            return ProductionPhase.APPROVAL_PENDING.value

        if not entry.proof_assembled:
            return ProductionPhase.SHIPPING.value

        return ProductionPhase.LEARNING.value

    def _all_packets_executed(self, entry: ProductionEntry) -> bool:
        if not entry.packets:
            return False
        for pkt in entry.packets:
            status = pkt.get("status", "")
            if status not in ("completed", "shipped", "merged", "verified"):
                return False
        return True

    # ── Organism-level phase (across all productions) ────────────────

    def phase(self) -> str:
        if not self._productions:
            ide_status = self._safe_call(self._meta_ide, "ide_status")
            if ide_status is not None:
                if hasattr(ide_status, "active_streams") and ide_status.active_streams > 0:
                    return ProductionPhase.PRODUCING.value
                if hasattr(ide_status, "pending_reviews") and ide_status.pending_reviews > 0:
                    return ProductionPhase.REVIEWING.value

            exec_state = self._safe_call(self._governed_execution, "state")
            if exec_state is not None:
                state_val = exec_state.value if hasattr(exec_state, "value") else str(exec_state)
                if state_val == "executing":
                    return ProductionPhase.PRODUCING.value
                if state_val == "governed":
                    return ProductionPhase.APPROVAL_PENDING.value
                if state_val == "blocked":
                    return ProductionPhase.DEGRADED.value

            return ProductionPhase.IDLE.value

        phases = [e.phase for e in self._productions.values()]

        if ProductionPhase.DEGRADED.value in phases:
            return ProductionPhase.DEGRADED.value
        if ProductionPhase.PRODUCING.value in phases:
            return ProductionPhase.PRODUCING.value
        if ProductionPhase.REVIEWING.value in phases:
            return ProductionPhase.REVIEWING.value
        if ProductionPhase.APPROVAL_PENDING.value in phases:
            return ProductionPhase.APPROVAL_PENDING.value
        if ProductionPhase.SHIPPING.value in phases:
            return ProductionPhase.SHIPPING.value
        if ProductionPhase.PLANNING.value in phases:
            return ProductionPhase.PLANNING.value
        if ProductionPhase.LEARNING.value in phases:
            return ProductionPhase.LEARNING.value

        return ProductionPhase.IDLE.value

    # ── Health derivation ────────────────────────────────────────────

    def health(self) -> str:
        exec_health = self._safe_call(self._governed_execution, "health")
        workforce_health = self._safe_call(self._agent_workforce, "health")

        blocked_count = sum(
            1 for e in self._productions.values()
            if e.phase == ProductionPhase.DEGRADED.value
        )
        active_count = sum(
            1 for e in self._productions.values()
            if e.phase not in (ProductionPhase.IDLE.value, ProductionPhase.LEARNING.value)
        )

        if blocked_count > 0:
            return ProductionHealth.BLOCKED.value

        if active_count == 0:
            if exec_health is not None:
                h_val = exec_health.value if hasattr(exec_health, "value") else str(exec_health)
                if h_val == "offline":
                    return ProductionHealth.OFFLINE.value
            return ProductionHealth.OFFLINE.value

        wh_val = ""
        if workforce_health is not None:
            wh_val = workforce_health.value if hasattr(workforce_health, "value") else str(workforce_health)

        if wh_val in ("constrained", "overloaded"):
            return ProductionHealth.CONSTRAINED.value

        eh_val = ""
        if exec_health is not None:
            eh_val = exec_health.value if hasattr(exec_health, "value") else str(exec_health)

        if eh_val == "optimal" or (eh_val == "active" and wh_val in ("optimal", "active", "")):
            return ProductionHealth.OPTIMAL.value

        return ProductionHealth.ACTIVE.value

    # ── Completion invariant ─────────────────────────────────────────

    def is_complete(self, production_id: str) -> bool:
        entry = self._productions.get(production_id)
        if entry is None:
            return False

        return (
            entry.quality_checks_passed
            and entry.governance_approved
            and entry.proof_assembled
            and self._all_packets_executed(entry)
            and not entry.blocked_reasons
        )

    # ── Active productions ───────────────────────────────────────────

    def active_productions(self) -> list[dict[str, Any]]:
        active = []
        for entry in self._productions.values():
            if entry.phase not in (
                ProductionPhase.IDLE.value,
                ProductionPhase.LEARNING.value,
            ):
                active.append(entry.to_dict())
        return active

    # ── What ships next ──────────────────────────────────────────────

    def what_ships_next(self) -> list[dict[str, Any]]:
        ready = []
        for entry in self._productions.values():
            if entry.phase in (
                ProductionPhase.SHIPPING.value,
                ProductionPhase.APPROVAL_PENDING.value,
            ):
                ready.append(entry.to_dict())

        ready.sort(key=lambda e: e.get("started_at", 0))
        return ready

    # ── Blockers ─────────────────────────────────────────────────────

    def blockers(self) -> list[dict[str, Any]]:
        result: list[dict[str, Any]] = []

        for entry in self._productions.values():
            if entry.blocked_reasons:
                result.append({
                    "production_id": entry.production_id,
                    "reasons": list(entry.blocked_reasons),
                })

        exec_blockers = self._safe_call(self._governed_execution, "blockers")
        if exec_blockers:
            for b in exec_blockers:
                result.append({
                    "production_id": "_organism",
                    "reasons": [b.get("description", str(b))] if isinstance(b, dict) else [str(b)],
                })

        return result

    # ── By target ────────────────────────────────────────────────────

    def by_target(self, target_type: str) -> list[dict[str, Any]]:
        return [
            e.to_dict()
            for e in self._productions.values()
            if e.target_type == target_type
        ]

    # ── Per-project phase map ────────────────────────────────────────

    def per_project_phases(self) -> dict[str, str]:
        return {
            pid: entry.phase
            for pid, entry in self._productions.items()
        }

    # ── Snapshot ──────────────────────────────────────────────────────

    def snapshot(self) -> ProductionSnapshot:
        now = time.time()

        workforce_summary: dict[str, Any] = {}
        wf_snap = self._safe_call(self._agent_workforce, "summary")
        if wf_snap is not None:
            workforce_summary = wf_snap if isinstance(wf_snap, dict) else {}

        pending_reviews = 0
        ide_status = self._safe_call(self._meta_ide, "ide_status")
        if ide_status is not None and hasattr(ide_status, "pending_reviews"):
            pending_reviews = ide_status.pending_reviews

        pending_approvals = 0
        exec_assessment = self._safe_call(self._governed_execution, "assessment")
        if exec_assessment is not None:
            pending_approvals = getattr(exec_assessment, "pending_approval_count", 0)

        blocked = sum(
            1 for e in self._productions.values()
            if e.phase == ProductionPhase.DEGRADED.value
        )

        queue_depth = 0
        fabric_snap = self._safe_call(self._execution_fabric, "snapshot")
        if fabric_snap is not None:
            queue_depth = getattr(fabric_snap, "queue_depth", 0)

        session_ctx: dict[str, Any] = {}
        ctx_snap = self._safe_call(self._meta_ide_context, "summary")
        if ctx_snap is not None:
            session_ctx = ctx_snap if isinstance(ctx_snap, dict) else {}

        active = self.active_productions()
        concurrent = len(set(
            e.production_id for e in self._productions.values()
            if e.phase not in (ProductionPhase.IDLE.value, ProductionPhase.LEARNING.value)
        ))

        return ProductionSnapshot(
            phase=self.phase(),
            health=self.health(),
            active_productions=active,
            workforce=workforce_summary,
            pending_reviews=pending_reviews,
            pending_approvals=pending_approvals,
            blocked_count=blocked,
            queue_depth=queue_depth,
            concurrent_projects=concurrent,
            session_context=session_ctx,
            per_project_phases=self.per_project_phases(),
            generated_at=now,
        )

    # ── Summary ──────────────────────────────────────────────────────

    def summary(self) -> dict[str, Any]:
        snap = self.snapshot()
        return {
            "phase": snap.phase,
            "health": snap.health,
            "active_count": len(snap.active_productions),
            "concurrent_projects": snap.concurrent_projects,
            "pending_reviews": snap.pending_reviews,
            "pending_approvals": snap.pending_approvals,
            "blocked_count": snap.blocked_count,
            "queue_depth": snap.queue_depth,
        }
