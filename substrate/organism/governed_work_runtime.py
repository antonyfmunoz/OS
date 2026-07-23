"""Governed Work Runtime — work-lifecycle adapter onto the canonical runtime.

WP-P1-001: this is an ADAPTER onto the one canonical operation runtime
(``governed_mutation`` → ``MutationRouter`` → ``GovernedExecutionSpine``), not a
second execution surface. It owns the work *lifecycle* (intent → packet → plan →
approval → dispatch); its mutation-executing step (``execute_work``) routes
through the canonical governed runtime when canonical routing is enabled, and
preserves its prior coordinator-dispatch behavior when it is not.

  Operator
    ↓
  CommandRuntime (normalize + classify)
    ↓
  GovernedWorkRuntime (this — work lifecycle adapter)
    ↓
  [canonical routing ON]  MutationRouter → GovernedExecutionSpine → executor
  [canonical routing OFF] ExecutionCoordinator (plan + queue + dispatch) → executor

Gate 3 — Governed Work Runtime. UMH substrate subsystem. Instance-agnostic.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from typing import Any
from uuid import uuid4

import os

from substrate.organism.canonical_runtime import canonical_runtime_routing_enabled


def _simulation_executor_allowed() -> bool:
    """Wave 2: the ``simulation`` target executor is a fake-success path and is
    PROHIBITED on the canonical execution path. It is permitted only when a test
    explicitly opts in via ``UMH_ALLOW_SIMULATION_EXECUTOR=1`` — never in
    production, never by default (Amendment / plan §V no-fake gate)."""
    return os.environ.get("UMH_ALLOW_SIMULATION_EXECUTOR") == "1"

logger = logging.getLogger(__name__)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Return types
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


@dataclass
class WorkSubmission:
    work_id: str = ""
    plan_id: str = ""
    status: str = "drafted"
    requires_approval: bool = True
    approval_policy: str = ""
    risk_class: str = "low"
    created_at: float = field(default_factory=time.time)
    error: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "work_id": self.work_id,
            "plan_id": self.plan_id,
            "status": self.status,
            "requires_approval": self.requires_approval,
            "approval_policy": self.approval_policy,
            "risk_class": self.risk_class,
            "created_at": self.created_at,
            "error": self.error,
        }


@dataclass
class ExecutionReceipt:
    work_id: str = ""
    plan_id: str = ""
    executor_type: str = ""
    started_at: float = field(default_factory=time.time)
    status: str = "dispatched"
    proof_id: str = ""
    error: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "work_id": self.work_id,
            "plan_id": self.plan_id,
            "executor_type": self.executor_type,
            "started_at": self.started_at,
            "status": self.status,
            "proof_id": self.proof_id,
            "error": self.error,
        }


@dataclass
class WorkStatus:
    work_id: str = ""
    phase: str = "unknown"
    plan_id: str = ""
    approval_status: str = ""
    proof_id: str = ""
    blockers: list[dict[str, Any]] = field(default_factory=list)
    description: str = ""
    risk_class: str = "low"
    created_at: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "work_id": self.work_id,
            "phase": self.phase,
            "plan_id": self.plan_id,
            "approval_status": self.approval_status,
            "proof_id": self.proof_id,
            "blockers": self.blockers,
            "description": self.description,
            "risk_class": self.risk_class,
            "created_at": self.created_at,
        }


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# GovernedWorkRuntime
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


class GovernedWorkRuntime:
    """Canonical work operations — the mandatory DO layer.

    All work mutations flow through this runtime. It composes:
      - WorkPacketEngine: intent → packet
      - ExecutionCoordinator: packet → plan → queue → dispatch
      - ApprovalPolicyRegistry: risk → approval decision
      - ProofRuntime: execution → proof package
      - WorkGraph: read-only projection for queries
      - WorkRecoveryRuntime: failure → recovery actions
    """

    def __init__(
        self,
        work_graph: Any | None = None,
        packet_engine: Any | None = None,
        execution_coordinator: Any | None = None,
        approval_registry: Any | None = None,
        proof_runtime: Any | None = None,
        recovery_runtime: Any | None = None,
        mutation_router: Any | None = None,
    ) -> None:
        self._work_graph = work_graph
        self._packet_engine = packet_engine
        self._execution_coordinator = execution_coordinator
        self._approval_registry = approval_registry
        self._proof_runtime = proof_runtime
        self._recovery_runtime = recovery_runtime
        # Optional injected MutationRouter (the canonical runtime). When canonical
        # routing is enabled and a router is available, execute_work submits the
        # dispatch as a governed mutation through the canonical spine. Injected by
        # the daemon (which holds the spine); None means "canonical routing not
        # wired here" and execute_work uses its prior coordinator-dispatch path.
        self._mutation_router = mutation_router

    # ── Lazy subsystem access ────────────────────────────────────

    @property
    def work_graph(self) -> Any:
        if self._work_graph is None:
            try:
                from substrate.organism.work_graph import WorkGraph

                self._work_graph = WorkGraph()
            except Exception:
                logger.debug("WorkGraph unavailable")
        return self._work_graph

    @property
    def packet_engine(self) -> Any:
        if self._packet_engine is None:
            try:
                from substrate.organism.work_packet_engine import WorkPacketEngine

                self._packet_engine = WorkPacketEngine()
            except Exception:
                logger.debug("WorkPacketEngine unavailable")
        return self._packet_engine

    @property
    def execution_coordinator(self) -> Any:
        if self._execution_coordinator is None:
            try:
                from substrate.organism.execution_coordinator import ExecutionCoordinator

                self._execution_coordinator = ExecutionCoordinator()
            except Exception:
                logger.debug("ExecutionCoordinator unavailable")
        return self._execution_coordinator

    @property
    def approval_registry(self) -> Any:
        if self._approval_registry is None:
            try:
                from substrate.organism.executors.approval_intercept import (
                    ApprovalPolicyRegistry,
                )

                self._approval_registry = ApprovalPolicyRegistry()
            except Exception:
                logger.debug("ApprovalPolicyRegistry unavailable")
        return self._approval_registry

    @property
    def proof_runtime(self) -> Any:
        if self._proof_runtime is None:
            try:
                from substrate.organism.proof_runtime import ProofRuntime

                self._proof_runtime = ProofRuntime()
            except Exception:
                logger.debug("ProofRuntime unavailable")
        return self._proof_runtime

    @property
    def recovery_runtime(self) -> Any:
        if self._recovery_runtime is None:
            try:
                from substrate.organism.work_recovery_runtime import WorkRecoveryRuntime

                self._recovery_runtime = WorkRecoveryRuntime(
                    work_graph=self.work_graph,
                )
            except Exception:
                logger.debug("WorkRecoveryRuntime unavailable")
        return self._recovery_runtime

    # ── Work Submission ──────────────────────────────────────────

    def submit_work(
        self,
        intent: str,
        risk_class: str = "low",
        target_executor: str = "",
        description: str = "",
    ) -> WorkSubmission:
        """Submit work from operator intent (LEGACY compatibility path).

        Pipeline: intent → WorkPacket → ExecutionPlan → approval check.

        Wave 2: this is NOT the canonical execution entry point. Canonical Wave 2
        execution consumes existing WorkPacket ids produced by the planning
        compiler and flows through ``substrate.execution.attempts`` — it never
        creates a Task from raw intent here. The ``target_executor`` is now
        REQUIRED and explicit; the fake ``simulation`` executor is rejected
        unless a test opts in (fail closed, no default fake success).
        """
        if not intent.strip():
            return WorkSubmission(error="Empty intent")

        if target_executor == "simulation" and not _simulation_executor_allowed():
            return WorkSubmission(
                error=(
                    "simulation executor is prohibited on the canonical path "
                    "(set UMH_ALLOW_SIMULATION_EXECUTOR=1 for tests only)"
                ),
            )

        packet_id = f"wp-{uuid4().hex[:12]}"
        plan_id = ""
        requires_approval = True
        policy_id = ""

        if self.packet_engine is None:
            return WorkSubmission(
                error="WorkPacketEngine unavailable — cannot create governed packet",
            )

        # Canonical DO layer: intent → real WorkPacket with classifier-derived
        # risk. AttributeError/TypeError here means the call site drifted from
        # the engine contract — surface it, never swallow (GAP-C1-001).
        packet = self.packet_engine.create_packet_from_intent(
            user_intent=intent,
            desired_end_state=description or "",
        )
        packet_id = packet.packet_id
        if getattr(packet, "risk_class", "") and risk_class == "low":
            risk_class = packet.risk_class

        if self.approval_registry is not None:
            try:
                from substrate.organism.executors.approval_intercept import ApprovalScope

                requires_approval, policy_id = self.approval_registry.evaluate(
                    risk_class,
                    ApprovalScope.PLAN,
                )
            except Exception:
                pass

        if self.execution_coordinator is not None:
            try:
                plan = self.execution_coordinator.create_plan(
                    source_workpacket_id=packet_id,
                    target_executor=target_executor,
                    risk_class=risk_class,
                    description=description or intent[:200],
                )
                plan_id = plan.execution_plan_id

                if not requires_approval:
                    self.execution_coordinator.approve_plan(plan_id, approved_by="auto-policy")
                    self.execution_coordinator.enqueue_plan(plan_id)
            except Exception as exc:
                logger.debug("ExecutionCoordinator plan creation failed: %s", exc)

        status = "approval_pending" if requires_approval else "queued"

        return WorkSubmission(
            work_id=packet_id,
            plan_id=plan_id,
            status=status,
            requires_approval=requires_approval,
            approval_policy=policy_id,
            risk_class=risk_class,
        )

    # ── Approval ─────────────────────────────────────────────────

    def approve_work(
        self,
        work_id: str,
        decided_by: str = "operator",
    ) -> dict[str, Any]:
        """Approve a work item (approves its execution plan)."""
        from substrate.organism.executors.approval_intercept import ApprovalDecision

        plan = self._find_plan_for_work(work_id)
        if plan is None:
            return ApprovalDecision(
                work_id=work_id,
                status="error",
                reason="No plan found for work_id",
            ).to_dict()

        if self.execution_coordinator is not None:
            approved_plan = self.execution_coordinator.approve_plan(
                plan.execution_plan_id,
                approved_by=decided_by,
            )
            if approved_plan:
                self.execution_coordinator.enqueue_plan(plan.execution_plan_id)

        return ApprovalDecision(
            work_id=work_id,
            status="approved",
            decided_by=decided_by,
            reason="Operator approved",
        ).to_dict()

    def reject_work(
        self,
        work_id: str,
        reason: str = "",
        decided_by: str = "operator",
    ) -> dict[str, Any]:
        """Reject a work item."""
        from substrate.organism.executors.approval_intercept import ApprovalDecision

        plan = self._find_plan_for_work(work_id)
        if plan is None:
            return ApprovalDecision(
                work_id=work_id,
                status="error",
                reason="No plan found for work_id",
            ).to_dict()

        if self.execution_coordinator is not None:
            self.execution_coordinator.deny_plan(
                plan.execution_plan_id,
                reason=reason,
                denied_by=decided_by,
            )

        return ApprovalDecision(
            work_id=work_id,
            status="rejected",
            decided_by=decided_by,
            reason=reason or "Operator rejected",
        ).to_dict()

    # ── Execution ────────────────────────────────────────────────

    def execute_work(self, work_id: str) -> ExecutionReceipt:
        """Execute an approved work item.

        WP-P1-001 + Wave 2 fail-closed: the dispatch is submitted as a governed
        mutation through the canonical runtime (``MutationRouter`` →
        ``GovernedExecutionSpine``), so the executor is only reached via a
        governed verdict. If no canonical router is wired, this path FAILS CLOSED
        with a rejected receipt — it NEVER silently falls back to the legacy
        ``ExecutionCoordinator.dispatch_next()`` path (that fallback let a fake/
        ungoverned executor run without a governed verdict). Legacy callers that
        still need the coordinator dispatch must call it explicitly.
        """
        plan = self._find_plan_for_work(work_id)
        if plan is None:
            return ExecutionReceipt(
                work_id=work_id,
                status="error",
                error="No plan found for work_id",
            )

        if plan.approval_state != "approved":
            return ExecutionReceipt(
                work_id=work_id,
                status="error",
                error=f"Plan not approved (state: {plan.approval_state})",
            )

        snapshot_id = ""
        if self.proof_runtime is not None:
            snapshot_id = self.proof_runtime.capture_before(work_id)

        # Canonical-runtime routing (deterministic). Execution goes through the
        # governed spine ONLY when canonical routing is enabled AND a
        # MutationRouter is wired. There is NO silent fallback to coordinator
        # dispatch_next() — absent either condition, fail closed with a rejected
        # receipt. The routing guard is consulted before any executor is reached.
        route_canonical = canonical_runtime_routing_enabled() and self._mutation_router is not None
        if not route_canonical:
            return ExecutionReceipt(
                work_id=work_id,
                plan_id=plan.execution_plan_id,
                status="rejected",
                error=(
                    "canonical routing unavailable — fail closed (no coordinator "
                    "dispatch fallback). Enable canonical routing and wire a "
                    "MutationRouter to execute."
                ),
            )

        dispatched_plan = self._dispatch_via_canonical_runtime(plan)

        proof_id = ""
        if snapshot_id and self.proof_runtime is not None:
            proof_pkg = self.proof_runtime.capture_after(
                work_id=work_id,
                snapshot_id=snapshot_id,
                action={"operation": "execute", "plan_id": plan.execution_plan_id},
                outcome="dispatched",
                operator="operator",
            )
            proof_id = proof_pkg.proof_id

        return ExecutionReceipt(
            work_id=work_id,
            plan_id=plan.execution_plan_id,
            executor_type=plan.target_executor,
            status="dispatched" if dispatched_plan else "queued",
            proof_id=proof_id,
        )

    # ── Lifecycle operations ─────────────────────────────────────

    def cancel_work(self, work_id: str, reason: str = "") -> bool:
        """Cancel a work item."""
        plan = self._find_plan_for_work(work_id)
        if plan is None:
            return False
        if self.execution_coordinator is not None:
            result = self.execution_coordinator.cancel_plan(plan.execution_plan_id)
            return result is not None
        return False

    def retry_work(self, work_id: str) -> WorkSubmission:
        """Retry a failed work item by creating a new submission."""
        node = None
        if self.work_graph is not None:
            node = self.work_graph.node(work_id)

        intent = ""
        risk_class = "low"
        if node is not None:
            intent = node.description or f"Retry of {work_id}"
            risk_class = node.risk_class
        else:
            intent = f"Retry of {work_id}"

        return self.submit_work(
            intent=intent,
            risk_class=risk_class,
            description=f"Retry of {work_id}",
        )

    # ── Query operations ─────────────────────────────────────────

    def status(self, work_id: str) -> WorkStatus:
        """Get the current status of a work item."""
        if self.work_graph is not None:
            node = self.work_graph.node(work_id)
            if node is not None:
                plan = self._find_plan_for_work(work_id)
                return WorkStatus(
                    work_id=work_id,
                    phase=node.status,
                    plan_id=plan.execution_plan_id if plan else "",
                    approval_status=getattr(plan, "approval_state", "") if plan else "",
                    proof_id=getattr(plan, "proof_id", "") if plan else "",
                    blockers=[b.to_dict() for b in node.blockers],
                    description=node.description,
                    risk_class=node.risk_class,
                    created_at=node.created_at,
                )

        return WorkStatus(work_id=work_id, phase="unknown")

    def queue(self) -> list[dict[str, Any]]:
        """Current work queue."""
        if self.work_graph is not None:
            return [n.to_dict() for n in self.work_graph.executable_work()]
        return []

    def blocked(self) -> list[dict[str, Any]]:
        """Blocked work items."""
        if self.work_graph is not None:
            return [n.to_dict() for n in self.work_graph.blocked_work()]
        return []

    def active(self) -> list[dict[str, Any]]:
        """Currently active work."""
        if self.work_graph is not None:
            return [n.to_dict() for n in self.work_graph.active_work()]
        return []

    def proof(self, work_id: str) -> dict[str, Any] | None:
        """Get proof package for a work item."""
        if self.proof_runtime is not None:
            pkg = self.proof_runtime.package_for(work_id)
            if pkg is not None:
                return pkg.to_dict()
        return None

    def history(self, limit: int = 50) -> list[dict[str, Any]]:
        """Recent work history (completed + failed)."""
        if self.work_graph is not None:
            completed = self.work_graph.completed_work()
            failed = self.work_graph.failed_work()
            all_terminal = completed + failed
            all_terminal.sort(key=lambda n: n.created_at, reverse=True)
            return [n.to_dict() for n in all_terminal[:limit]]
        return []

    def recovery(self) -> list[dict[str, Any]]:
        """Recoverable work items."""
        if self.recovery_runtime is not None:
            return [a.to_dict() for a in self.recovery_runtime.recoverable_work()]
        return []

    def graph_snapshot(self) -> dict[str, Any]:
        """Full work graph snapshot."""
        if self.work_graph is not None:
            return self.work_graph.snapshot().to_dict()
        return {"total": 0, "active": 0, "blocked": 0, "completed": 0, "failed": 0, "nodes": []}

    # ── Internal ─────────────────────────────────────────────────

    def _dispatch_via_canonical_runtime(self, plan: Any) -> Any | None:
        """Submit the plan dispatch through the canonical governed runtime.

        Wraps ``ExecutionCoordinator.dispatch_next()`` in a MutationRequest and
        routes it through the injected MutationRouter (→ GovernedExecutionSpine),
        so reaching the executor requires a governed verdict. Returns the
        dispatched plan on a successful governed execution, else None (the spine
        may reject or hold for approval, in which case nothing is dispatched).
        """
        from substrate.organism.mutation_router import MutationRequest

        if self.execution_coordinator is None:
            return None
        if plan.status == "approved":
            self.execution_coordinator.enqueue_plan(plan.execution_plan_id)

        dispatched_holder: dict[str, Any] = {}

        def _do_dispatch() -> tuple[str, bool]:
            dispatched = self.execution_coordinator.dispatch_next()
            dispatched_holder["plan"] = dispatched
            return (
                (f"dispatched plan {plan.execution_plan_id}", True)
                if dispatched is not None
                else ("no dispatchable plan", False)
            )

        request = MutationRequest(
            mutation_name="work_packet_execute",
            intent=f"dispatch approved work plan {plan.execution_plan_id}",
            execute_fn=_do_dispatch,
            source="governed_work_runtime",
            risk_level=getattr(plan, "risk_class", None),
            metadata={
                "plan_id": plan.execution_plan_id,
                "target_executor": getattr(plan, "target_executor", ""),
            },
        )
        response = self._mutation_router.execute(request)
        if not response.success:
            logger.warning(
                "canonical dispatch not executed for plan %s: %s",
                plan.execution_plan_id,
                response.rejected_reason or response.status,
            )
            return None
        return dispatched_holder.get("plan")

    def _find_plan_for_work(self, work_id: str) -> Any | None:
        """Find the execution plan associated with a work packet ID."""
        if self.execution_coordinator is None:
            return None
        try:
            plans = self.execution_coordinator._plan_store.by_workpacket(work_id)
            if plans:
                return plans[0]
        except Exception:
            pass
        return None
