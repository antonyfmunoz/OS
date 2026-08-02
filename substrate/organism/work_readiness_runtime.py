"""Work Readiness Runtime — multi-dimensional readiness classification.

Campaign 11.0. UMH substrate layer. Instance-agnostic.

Composes (does not replace):
  - WorkGraph (Gate 3) — work node projection, blocker data
  - GoalAlignmentEngine (C8.4) — work↔goal linkage
  - CapabilityGapEngine (C10.1) — capability gap analysis
  - ExecutionCoordinator (Phase 13) — plan/queue state
  - UnifiedApprovalRuntime (C4.2) — pending approvals
  - DelegationRuntime (C4.7) — active proposals/missions

Authority remains with the source systems. This runtime ONLY classifies
readiness — it never creates, modifies, approves, or executes work.

Read-only. No mutation. No execution. Deterministic. Zero LLM calls.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

logger = logging.getLogger(__name__)


# ── Types ─────────────────────────────────────────────────────────────────


class ReadinessStatus(str, Enum):
    READY = "ready"
    WAITING_APPROVAL = "waiting_approval"
    WAITING_CAPABILITY = "waiting_capability"
    WAITING_DEPENDENCY = "waiting_dependency"
    WAITING_DELEGATION = "waiting_delegation"
    BLOCKED = "blocked"


@dataclass
class ReadinessAssessment:
    work_id: str = ""
    title: str = ""
    status: ReadinessStatus = ReadinessStatus.BLOCKED
    blocking_reasons: list[str] = field(default_factory=list)
    missing_capabilities: list[str] = field(default_factory=list)
    pending_approvals: list[str] = field(default_factory=list)
    unresolved_dependencies: list[str] = field(default_factory=list)
    goal_ids: list[str] = field(default_factory=list)
    readiness_score: float = 0.0
    recommended_action: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "work_id": self.work_id,
            "title": self.title,
            "status": self.status.value if isinstance(self.status, ReadinessStatus) else self.status,
            "blocking_reasons": self.blocking_reasons,
            "missing_capabilities": self.missing_capabilities,
            "pending_approvals": self.pending_approvals,
            "unresolved_dependencies": self.unresolved_dependencies,
            "goal_ids": self.goal_ids,
            "readiness_score": round(self.readiness_score, 4),
            "recommended_action": self.recommended_action,
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> ReadinessAssessment:
        status_val = d.get("status", "blocked")
        try:
            status = ReadinessStatus(status_val)
        except ValueError:
            status = ReadinessStatus.BLOCKED
        return cls(
            work_id=d.get("work_id", ""),
            title=d.get("title", ""),
            status=status,
            blocking_reasons=d.get("blocking_reasons", []),
            missing_capabilities=d.get("missing_capabilities", []),
            pending_approvals=d.get("pending_approvals", []),
            unresolved_dependencies=d.get("unresolved_dependencies", []),
            goal_ids=d.get("goal_ids", []),
            readiness_score=d.get("readiness_score", 0.0),
            recommended_action=d.get("recommended_action", ""),
        )


@dataclass
class WorkReadinessSnapshot:
    total: int = 0
    by_status: dict[str, int] = field(default_factory=dict)
    ready_work: list[ReadinessAssessment] = field(default_factory=list)
    blocked_work: list[ReadinessAssessment] = field(default_factory=list)
    top_blockers: list[str] = field(default_factory=list)
    goals_with_no_ready_work: list[str] = field(default_factory=list)
    health: str = "unknown"
    timestamp: float = field(default_factory=time.time)

    def to_dict(self) -> dict[str, Any]:
        return {
            "total": self.total,
            "by_status": self.by_status,
            "ready_count": len(self.ready_work),
            "blocked_count": len(self.blocked_work),
            "ready_work": [a.to_dict() for a in self.ready_work],
            "blocked_work": [a.to_dict() for a in self.blocked_work],
            "top_blockers": self.top_blockers,
            "goals_with_no_ready_work": self.goals_with_no_ready_work,
            "health": self.health,
            "timestamp": self.timestamp,
        }


# ── Status sets for classification ────────────────────────────────────────

_APPROVAL_PENDING = frozenset({
    "drafted", "classified", "planned", "ready_for_review",
    "approval_pending",
})

_DELEGATED = frozenset({"delegated"})

_EXECUTING = frozenset({"executing", "validating", "reconverging"})

_BLOCKED = frozenset({"blocked", "paused"})

_TERMINAL = frozenset({
    "completed", "rejected", "failed", "superseded", "archived",
})


# ── Runtime ───────────────────────────────────────────────────────────────


class WorkReadinessRuntime:
    """Read-only readiness classification over existing work systems.

    Composes:
      - WorkGraph (Gate 3) — work node projection
      - GoalAlignmentEngine (C8.4) — work↔goal linkage
      - CapabilityGapEngine (C10.1) — gap analysis
      - ExecutionCoordinator (Phase 13) — plan/approval state
      - UnifiedApprovalRuntime (C4.2) — pending approvals
      - DelegationRuntime (C4.7) — delegation state

    Owns nothing. Mutates nothing. Authority stays with source systems.
    """

    def __init__(
        self,
        work_graph: Any | None = None,
        goal_alignment: Any | None = None,
        capability_gap: Any | None = None,
        execution_coordinator: Any | None = None,
        approval_runtime: Any | None = None,
        delegation_runtime: Any | None = None,
    ) -> None:
        self._work_graph = work_graph
        self._goal_alignment = goal_alignment
        self._capability_gap = capability_gap
        self._coordinator = execution_coordinator
        self._approvals = approval_runtime
        self._delegation = delegation_runtime

    # ── Lazy subsystem access ─────────────────────────────────────

    @property
    def work_graph(self) -> Any | None:
        if self._work_graph is None:
            try:
                from substrate.organism.work_graph import WorkGraph
                self._work_graph = WorkGraph()
            except Exception:
                logger.debug("WorkGraph unavailable")
        return self._work_graph

    @property
    def goal_alignment(self) -> Any | None:
        if self._goal_alignment is None:
            try:
                from substrate.organism.goal_alignment_engine import GoalAlignmentEngine
                self._goal_alignment = GoalAlignmentEngine()
            except Exception:
                logger.debug("GoalAlignmentEngine unavailable")
        return self._goal_alignment

    @property
    def capability_gap(self) -> Any | None:
        if self._capability_gap is None:
            try:
                from substrate.organism.capability_gap_engine import CapabilityGapEngine
                self._capability_gap = CapabilityGapEngine()
            except Exception:
                logger.debug("CapabilityGapEngine unavailable")
        return self._capability_gap

    @property
    def coordinator(self) -> Any | None:
        if self._coordinator is None:
            try:
                from substrate.organism.execution_coordinator import ExecutionCoordinator
                self._coordinator = ExecutionCoordinator()
            except Exception:
                logger.debug("ExecutionCoordinator unavailable")
        return self._coordinator

    @property
    def approvals(self) -> Any | None:
        if self._approvals is None:
            try:
                from substrate.workstation.unified_approval_runtime import UnifiedApprovalRuntime
                self._approvals = UnifiedApprovalRuntime()
            except Exception:
                logger.debug("UnifiedApprovalRuntime unavailable")
        return self._approvals

    @property
    def delegation(self) -> Any | None:
        if self._delegation is None:
            try:
                from substrate.organism.delegation_runtime import DelegationRuntime
                self._delegation = DelegationRuntime()
            except Exception:
                logger.debug("DelegationRuntime unavailable")
        return self._delegation

    # ── Core classification ───────────────────────────────────────

    def _get_work_nodes(self) -> list[Any]:
        """Get all active work nodes from WorkGraph."""
        if self.work_graph is None:
            return []
        try:
            nodes = self.work_graph.all_work()
            return nodes if isinstance(nodes, list) else []
        except Exception:
            logger.debug("Failed to get work nodes")
            return []

    def _operation_snapshot(self) -> dict[str, Any] | None:
        """One WorkGraph view for the duration of ONE batch operation.

        Returns ``None`` — meaning "no snapshot, use the original per-call
        fresh-read path" — whenever a snapshot cannot be built. That covers a
        missing graph, a graph that predates ``operation_snapshot`` (test
        doubles and any external implementation of the interface), and any
        read failure. Falling back to the ORIGINAL behavior rather than to an
        empty dict is deliberate: an empty snapshot would silently classify
        every dependency as missing, turning a read problem into a wrong
        governance answer.
        """
        if self.work_graph is None:
            return None
        snap = getattr(self.work_graph, "operation_snapshot", None)
        if not callable(snap):
            return None
        try:
            result = snap()
            return result if isinstance(result, dict) else None
        except Exception:
            logger.debug("Failed to build work-graph operation snapshot")
            return None

    def _get_goal_ids_for_work(self, work_id: str) -> list[str]:
        """Get goal IDs linked to a work item via GoalAlignmentEngine."""
        if self.goal_alignment is None:
            return []
        try:
            chain = self.goal_alignment.goal_for_work(work_id)
            if isinstance(chain, list):
                return [
                    g.get("goal_id", g.get("id", ""))
                    for g in chain if isinstance(g, dict)
                ]
            return []
        except Exception:
            logger.debug("Failed to get goals for work %s", work_id)
            return []

    def _get_missing_capabilities(self, goal_ids: list[str]) -> list[str]:
        """Get missing capabilities for a set of goals."""
        if self.capability_gap is None or not goal_ids:
            return []
        missing: list[str] = []
        for goal_id in goal_ids:
            try:
                gaps = self.capability_gap.gaps_for_goal(goal_id)
                if isinstance(gaps, list):
                    for gap in gaps:
                        name = ""
                        if hasattr(gap, "required_capability"):
                            name = gap.required_capability
                        elif isinstance(gap, dict):
                            name = gap.get("required_capability", "")
                        if name and name not in missing:
                            missing.append(name)
            except Exception:
                logger.debug("Failed to get capability gaps for goal %s", goal_id)
        return missing

    def _get_pending_approvals(self, work_id: str) -> list[str]:
        """Get pending approval IDs for a work item."""
        if self.approvals is None:
            return []
        try:
            snap = self.approvals.snapshot()
            pending: list[str] = []
            items = getattr(snap, "pending", [])
            if isinstance(items, list):
                for item in items:
                    item_work_id = ""
                    if hasattr(item, "source_id"):
                        item_work_id = item.source_id
                    elif isinstance(item, dict):
                        item_work_id = item.get("source_id", "")
                    if item_work_id == work_id:
                        aid = ""
                        if hasattr(item, "approval_id"):
                            aid = item.approval_id
                        elif isinstance(item, dict):
                            aid = item.get("approval_id", "")
                        if aid:
                            pending.append(aid)
            return pending
        except Exception:
            logger.debug("Failed to get pending approvals for %s", work_id)
            return []

    def _get_unresolved_deps(
        self, node: Any, snapshot: dict[str, Any] | None = None
    ) -> list[str]:
        """Get unresolved dependency IDs for a work node.

        ``snapshot`` is the caller's operation-scoped WorkGraph view. When one
        is supplied (batch paths like ``assess_all``), BOTH store reads below
        resolve against it, so a pass over N nodes performs one collection
        rather than N x (1 + deps) full-store parses. Without it the behavior is
        unchanged: fresh reads per call, for independent callers.
        """
        deps: list[str] = []
        if self.work_graph is None:
            return deps
        try:
            node_id = getattr(node, "node_id", "")
            if snapshot is not None:
                dep_ids = self.work_graph.dependencies_of(node_id, snapshot)
            else:
                dep_ids = self.work_graph.dependencies_of(node_id)
            if not isinstance(dep_ids, list):
                return deps
            for dep_id in dep_ids:
                dep_nodes = []
                try:
                    if snapshot is not None:
                        # Same immutable view — no second store read. The
                        # comparison is deliberately IDENTICAL to the uncached
                        # branch below (``node_id == dep_id``), including when
                        # ``dep_id`` is a node object rather than a string:
                        # ``dependencies_of`` returns WorkGraphNode objects, so
                        # that equality is generally False for real nodes and
                        # the dep falls through as unresolved. That is a
                        # PRE-EXISTING behavior of this function and correcting
                        # it is out of scope here — this cycle removes the
                        # repeated store reads WITHOUT altering what the
                        # function decides. Matching the original comparison
                        # exactly is what makes the change semantics-preserving.
                        dep_nodes = [
                            n for n in snapshot.values()
                            if getattr(n, "node_id", "") == dep_id
                        ]
                    else:
                        all_nodes = self.work_graph.all_work()
                        dep_nodes = [
                            n for n in (all_nodes or [])
                            if getattr(n, "node_id", "") == dep_id
                        ]
                except Exception:
                    pass
                if dep_nodes:
                    dep_node = dep_nodes[0]
                    dep_status = getattr(dep_node, "status", "")
                    if dep_status not in _TERMINAL:
                        deps.append(dep_id)
                else:
                    deps.append(dep_id)
            return deps
        except Exception:
            logger.debug("Failed to get dependencies")
            return deps

    def _has_delegation(self, work_id: str) -> bool:
        """Check if work has an active delegation mission."""
        if self.delegation is None:
            return False
        try:
            missions = getattr(self.delegation, "_missions", {})
            if isinstance(missions, dict):
                for mission in missions.values():
                    mid = ""
                    if hasattr(mission, "work_packet_id"):
                        mid = mission.work_packet_id
                    elif isinstance(mission, dict):
                        mid = mission.get("work_packet_id", "")
                    if mid == work_id:
                        return True
            return False
        except Exception:
            return False

    def _classify_node(
        self, node: Any, snapshot: dict[str, Any] | None = None
    ) -> ReadinessAssessment:
        """Classify a single work node's readiness.

        ``snapshot`` is the operation-scoped WorkGraph view owned by the calling
        batch operation; it is threaded down to dependency resolution so the
        whole pass sees ONE point-in-time state. Single-node callers omit it and
        keep the original fresh-read behavior.
        """
        node_id = getattr(node, "node_id", "")
        title = getattr(node, "description", "")
        status_str = getattr(node, "status", "")
        if hasattr(status_str, "value"):
            status_str = status_str.value

        goal_ids = self._get_goal_ids_for_work(node_id)
        blocking_reasons: list[str] = []
        missing_caps: list[str] = []
        pending_apps: list[str] = []
        unresolved_deps: list[str] = []

        # Terminal work is not assessed
        if status_str in _TERMINAL:
            return ReadinessAssessment(
                work_id=node_id,
                title=title,
                status=ReadinessStatus.READY,
                goal_ids=goal_ids,
                readiness_score=1.0,
                recommended_action="completed",
            )

        # Hard block
        if status_str in _BLOCKED:
            blockers = getattr(node, "blockers", []) or []
            for b in blockers:
                desc = ""
                if hasattr(b, "description"):
                    desc = b.description
                elif isinstance(b, dict):
                    desc = b.get("description", "")
                if desc:
                    blocking_reasons.append(desc)
            if not blocking_reasons:
                blocking_reasons.append("work is in blocked state")
            return ReadinessAssessment(
                work_id=node_id,
                title=title,
                status=ReadinessStatus.BLOCKED,
                blocking_reasons=blocking_reasons,
                goal_ids=goal_ids,
                readiness_score=0.0,
                recommended_action=self._recommend_for_blocked(blocking_reasons),
            )

        # Check dependencies
        unresolved_deps = self._get_unresolved_deps(node, snapshot)
        if unresolved_deps:
            blocking_reasons.append(
                f"{len(unresolved_deps)} unresolved dependencies"
            )

        # Check approvals
        if status_str in _APPROVAL_PENDING:
            pending_apps = self._get_pending_approvals(node_id)
            if pending_apps or status_str == "approval_pending":
                blocking_reasons.append("awaiting operator approval")

        # Check capability gaps
        missing_caps = self._get_missing_capabilities(goal_ids)
        if missing_caps:
            blocking_reasons.append(
                f"{len(missing_caps)} missing capabilities"
            )

        # Check delegation
        needs_delegation = (
            status_str in _DELEGATED
            and not self._has_delegation(node_id)
        )
        if needs_delegation:
            blocking_reasons.append("needs executor assignment")

        # Classify
        if not blocking_reasons:
            readiness = ReadinessStatus.READY
            score = 1.0
            action = "execute"
        elif unresolved_deps and not pending_apps and not missing_caps:
            readiness = ReadinessStatus.WAITING_DEPENDENCY
            score = self._dep_score(unresolved_deps)
            action = f"resolve dependencies: {', '.join(unresolved_deps[:3])}"
        elif pending_apps or status_str in _APPROVAL_PENDING:
            readiness = ReadinessStatus.WAITING_APPROVAL
            score = 0.3
            action = "approve pending work"
        elif missing_caps:
            readiness = ReadinessStatus.WAITING_CAPABILITY
            score = self._cap_score(missing_caps)
            action = f"build capability: {missing_caps[0]}"
        elif needs_delegation:
            readiness = ReadinessStatus.WAITING_DELEGATION
            score = 0.4
            action = "assign executor"
        else:
            readiness = ReadinessStatus.BLOCKED
            score = 0.0
            action = self._recommend_for_blocked(blocking_reasons)

        return ReadinessAssessment(
            work_id=node_id,
            title=title,
            status=readiness,
            blocking_reasons=blocking_reasons,
            missing_capabilities=missing_caps,
            pending_approvals=pending_apps,
            unresolved_dependencies=unresolved_deps,
            goal_ids=goal_ids,
            readiness_score=score,
            recommended_action=action,
        )

    def _dep_score(self, deps: list[str]) -> float:
        """Score based on number of unresolved dependencies. Fewer = closer to ready."""
        if not deps:
            return 1.0
        return max(0.0, 1.0 - (len(deps) * 0.2))

    def _cap_score(self, missing: list[str]) -> float:
        """Score based on number of missing capabilities."""
        if not missing:
            return 1.0
        return max(0.0, 1.0 - (len(missing) * 0.25))

    def _recommend_for_blocked(self, reasons: list[str]) -> str:
        if not reasons:
            return "investigate blockers"
        return f"resolve: {reasons[0]}"

    # ── Public API ────────────────────────────────────────────────

    def assess(self, work_id: str) -> ReadinessAssessment:
        """Full readiness assessment for one work item."""
        nodes = self._get_work_nodes()
        node = next(
            (n for n in nodes if getattr(n, "node_id", "") == work_id),
            None,
        )
        if node is None:
            return ReadinessAssessment(
                work_id=work_id,
                status=ReadinessStatus.BLOCKED,
                blocking_reasons=["work item not found"],
                readiness_score=0.0,
                recommended_action="verify work item exists",
            )
        return self._classify_node(node)

    def assess_all(self) -> list[ReadinessAssessment]:
        """Batch readiness assessment for all active work.

        Reads fresh persisted state at the START of the pass, then classifies
        every node against that ONE immutable snapshot. This is
        operation-scoped consistency, not caching: the snapshot is a local
        owned by this frame, it is never stored on the instance, and it is
        dropped when the call returns — a later call reads current state again
        and observes anything committed since.

        Before this, dependency resolution re-read every source store once per
        node (and again per dependency), so a pass over N nodes performed
        O(N^2) full-store parses. At ~1,100 packets over a 2.8 MB store that
        does not terminate, which is what blocked whole-tree validation.
        """
        nodes = self._get_work_nodes()
        snapshot = self._operation_snapshot()
        results: list[ReadinessAssessment] = []
        for node in nodes:
            status_str = getattr(node, "status", "")
            if hasattr(status_str, "value"):
                status_str = status_str.value
            if status_str in _TERMINAL:
                continue
            try:
                results.append(self._classify_node(node, snapshot))
            except Exception:
                logger.debug(
                    "Failed to classify node %s",
                    getattr(node, "node_id", "?"),
                )
        return results

    def ready_work(self) -> list[ReadinessAssessment]:
        """Only READY items."""
        return [a for a in self.assess_all() if a.status == ReadinessStatus.READY]

    def blocked_work(self) -> list[ReadinessAssessment]:
        """All non-READY items with blocking reasons."""
        return [a for a in self.assess_all() if a.status != ReadinessStatus.READY]

    def work_for_goal(self, goal_id: str) -> list[ReadinessAssessment]:
        """All work for a goal, with readiness classification."""
        all_assessed = self.assess_all()
        return [a for a in all_assessed if goal_id in a.goal_ids]

    def work_for_capability(self, capability_name: str) -> list[ReadinessAssessment]:
        """Work items requiring a specific capability (via gap engine)."""
        all_assessed = self.assess_all()
        return [
            a for a in all_assessed
            if capability_name in a.missing_capabilities
        ]

    def next_unblockable(self) -> list[ReadinessAssessment]:
        """Work closest to becoming READY — fewest remaining blockers."""
        blocked = self.blocked_work()
        scored = sorted(blocked, key=lambda a: -a.readiness_score)
        return scored[:10]

    def snapshot(self) -> WorkReadinessSnapshot:
        """Full readiness snapshot."""
        all_assessed = self.assess_all()
        by_status: dict[str, int] = {}
        for s in ReadinessStatus:
            by_status[s.value] = 0
        for a in all_assessed:
            key = a.status.value if isinstance(a.status, ReadinessStatus) else a.status
            by_status[key] = by_status.get(key, 0) + 1

        ready = [a for a in all_assessed if a.status == ReadinessStatus.READY]
        blocked = [a for a in all_assessed if a.status != ReadinessStatus.READY]

        reason_counts: dict[str, int] = {}
        for a in blocked:
            for r in a.blocking_reasons:
                reason_counts[r] = reason_counts.get(r, 0) + 1
        top_blockers = sorted(reason_counts, key=reason_counts.get, reverse=True)[:5]

        goals_no_ready = self._find_goals_with_no_ready_work(all_assessed)

        return WorkReadinessSnapshot(
            total=len(all_assessed),
            by_status=by_status,
            ready_work=ready,
            blocked_work=blocked,
            top_blockers=top_blockers,
            goals_with_no_ready_work=goals_no_ready,
            health=self._classify_health(all_assessed),
            timestamp=time.time(),
        )

    def summary(self) -> dict[str, Any]:
        """Compact dict for API."""
        snap = self.snapshot()
        return {
            "total": snap.total,
            "by_status": snap.by_status,
            "ready_count": len(snap.ready_work),
            "blocked_count": len(snap.blocked_work),
            "top_blockers": snap.top_blockers,
            "health": snap.health,
        }

    def health(self) -> str:
        """Deterministic health classification."""
        return self._classify_health(self.assess_all())

    # ── Private helpers ───────────────────────────────────────────

    def _classify_health(self, assessments: list[ReadinessAssessment]) -> str:
        if not assessments:
            return "unknown"
        ready_count = sum(1 for a in assessments if a.status == ReadinessStatus.READY)
        blocked_count = sum(1 for a in assessments if a.status == ReadinessStatus.BLOCKED)
        total = len(assessments)
        ready_pct = ready_count / total
        blocked_pct = blocked_count / total
        if ready_pct > 0.7:
            return "ready"
        if ready_pct > 0.5:
            return "mostly_ready"
        if blocked_pct > 0.5:
            return "blocked"
        return "constrained"

    def _find_goals_with_no_ready_work(
        self, assessments: list[ReadinessAssessment]
    ) -> list[str]:
        """Goals that appear in assessments but have zero READY items."""
        goal_has_ready: dict[str, bool] = {}
        for a in assessments:
            for gid in a.goal_ids:
                if gid not in goal_has_ready:
                    goal_has_ready[gid] = False
                if a.status == ReadinessStatus.READY:
                    goal_has_ready[gid] = True
        return [gid for gid, has_ready in goal_has_ready.items() if not has_ready]
