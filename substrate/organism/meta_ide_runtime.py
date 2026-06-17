"""Meta IDE Runtime — unified development surface.

Composes meta_ide subsystems + AgentFleetRuntime (W3) into a single
development loop: inspect → plan → assign → monitor → review → merge.

Campaign invariant: eliminates operator need to bounce between VSCode,
Cursor, Claude Code, and terminal for development work.

W2. UMH substrate subsystem. Instance-agnostic.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any
from uuid import uuid4

logger = logging.getLogger(__name__)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Enums
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


class ReviewStatus(str, Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    MERGED = "merged"


class DevelopmentPhase(str, Enum):
    INSPECTING = "inspecting"
    PLANNING = "planning"
    ASSIGNING = "assigning"
    EXECUTING = "executing"
    REVIEWING = "reviewing"
    MERGING = "merging"
    COMPLETE = "complete"


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Dataclasses
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


@dataclass
class WorkspaceSnapshot:
    """Unified workspace view: repos + sessions + reviews."""

    repos: list[dict[str, Any]] = field(default_factory=list)
    active_sessions: int = 0
    open_reviews: int = 0
    pending_merges: int = 0
    snapshot_at: float = field(default_factory=time.time)

    def to_dict(self) -> dict[str, Any]:
        return {
            "repos": list(self.repos),
            "active_sessions": self.active_sessions,
            "open_reviews": self.open_reviews,
            "pending_merges": self.pending_merges,
            "snapshot_at": self.snapshot_at,
        }


@dataclass
class IDEPlan:
    """Engineering plan created from operator intent."""

    plan_id: str = field(default_factory=lambda: f"idp-{uuid4().hex[:8]}")
    intent_text: str = ""
    tasks: list[dict[str, Any]] = field(default_factory=list)
    capabilities_needed: list[str] = field(default_factory=list)
    risk_class: str = "low"
    status: str = "draft"
    created_at: float = field(default_factory=time.time)

    def to_dict(self) -> dict[str, Any]:
        return {
            "plan_id": self.plan_id,
            "intent_text": self.intent_text,
            "tasks": list(self.tasks),
            "capabilities_needed": list(self.capabilities_needed),
            "risk_class": self.risk_class,
            "status": self.status,
            "created_at": self.created_at,
        }


@dataclass
class DevelopmentStream:
    """Live view of an in-flight development activity."""

    stream_id: str = field(default_factory=lambda: f"ds-{uuid4().hex[:8]}")
    plan_id: str = ""
    agent_type: str = ""
    compute_node_id: str = ""
    dispatch_id: str = ""
    phase: DevelopmentPhase = DevelopmentPhase.EXECUTING
    description: str = ""
    started_at: float = field(default_factory=time.time)

    def to_dict(self) -> dict[str, Any]:
        return {
            "stream_id": self.stream_id,
            "plan_id": self.plan_id,
            "agent_type": self.agent_type,
            "compute_node_id": self.compute_node_id,
            "dispatch_id": self.dispatch_id,
            "phase": self.phase.value,
            "description": self.description,
            "started_at": self.started_at,
        }


@dataclass
class ReviewDetail:
    """Review package with execution lineage."""

    review_id: str = field(default_factory=lambda: f"rv-{uuid4().hex[:8]}")
    plan_id: str = ""
    session_id: str = ""
    status: ReviewStatus = ReviewStatus.PENDING
    artifacts: list[dict[str, Any]] = field(default_factory=list)
    lineage_chain: list[str] = field(default_factory=list)
    recommendation: str = ""
    reasoning: str = ""
    created_at: float = field(default_factory=time.time)
    resolved_at: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "review_id": self.review_id,
            "plan_id": self.plan_id,
            "session_id": self.session_id,
            "status": self.status.value,
            "artifacts": list(self.artifacts),
            "lineage_chain": list(self.lineage_chain),
            "recommendation": self.recommendation,
            "reasoning": self.reasoning,
            "created_at": self.created_at,
            "resolved_at": self.resolved_at,
        }


@dataclass
class MergeResult:
    """Outcome of an approved merge."""

    review_id: str = ""
    merged_at: float = 0.0
    branch: str = ""
    commit_sha: str = ""
    lineage_chain_id: str = ""
    success: bool = False
    error: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "review_id": self.review_id,
            "merged_at": self.merged_at,
            "branch": self.branch,
            "commit_sha": self.commit_sha,
            "lineage_chain_id": self.lineage_chain_id,
            "success": self.success,
            "error": self.error,
        }


@dataclass
class IDEStatusSnapshot:
    """Aggregated IDE status."""

    active_agents: int = 0
    pending_reviews: int = 0
    repos_with_changes: int = 0
    recent_merges: int = 0
    active_streams: int = 0
    total_plans: int = 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "active_agents": self.active_agents,
            "pending_reviews": self.pending_reviews,
            "repos_with_changes": self.repos_with_changes,
            "recent_merges": self.recent_merges,
            "active_streams": self.active_streams,
            "total_plans": self.total_plans,
        }


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Meta IDE Runtime
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


class MetaIDERuntime:
    """Unified development surface — one loop for inspect/plan/assign/review/merge.

    Composes:
      - meta_ide subsystems (planner, session coordinator, review builder)
      - AgentFleetRuntime (W3) for agent assignment + dispatch
      - RepositoryModel for repo awareness
      - WorkspaceObservation for live workspace state
      - ExecutionGraph (Gate 8) for lineage tracking
    """

    def __init__(
        self,
        agent_fleet: Any,
        repository_model: Any | None = None,
        workspace_observation: Any | None = None,
        engineering_planner: Any | None = None,
        review_builder: Any | None = None,
        session_coordinator: Any | None = None,
        execution_graph: Any | None = None,
        intent_runtime: Any | None = None,
    ) -> None:
        self._agent_fleet = agent_fleet
        self._repository_model = repository_model
        self._workspace_observation = workspace_observation
        self._engineering_planner = engineering_planner
        self._review_builder = review_builder
        self._session_coordinator = session_coordinator
        self._execution_graph = execution_graph
        self._intent_runtime = intent_runtime

        self._plans: dict[str, IDEPlan] = {}
        self._streams: dict[str, DevelopmentStream] = {}
        self._reviews: dict[str, ReviewDetail] = {}
        self._merges: list[MergeResult] = []

    # ── Inspect ───────────────────────────────────────────────────

    def workspace_snapshot(self) -> WorkspaceSnapshot:
        """Compose repo model + workspace observation into unified view."""
        repos: list[dict[str, Any]] = []
        if self._repository_model is not None:
            try:
                snap = self._repository_model.snapshot()
                repos = [snap] if isinstance(snap, dict) else snap
            except Exception as exc:
                logger.debug("repository model snapshot failed: %s", exc)

        return WorkspaceSnapshot(
            repos=repos,
            active_sessions=len([
                s for s in self._streams.values()
                if s.phase not in (DevelopmentPhase.COMPLETE,)
            ]),
            open_reviews=len([
                r for r in self._reviews.values()
                if r.status == ReviewStatus.PENDING
            ]),
            pending_merges=len([
                r for r in self._reviews.values()
                if r.status == ReviewStatus.APPROVED
            ]),
        )

    def repo_status(self, repo_id: str) -> dict[str, Any]:
        """Get status of a specific repository."""
        if self._repository_model is not None:
            try:
                return self._repository_model.repo_status(repo_id)
            except AttributeError:
                pass
        return {"repo_id": repo_id, "status": "unknown"}

    # ── Plan ──────────────────────────────────────────────────────

    def plan_from_intent(self, intent_text: str) -> IDEPlan:
        """Create an engineering plan from natural language intent.

        Uses IntentRuntime for capture + EngineeringPlanner for breakdown.
        Falls back to simple task decomposition if subsystems unavailable.
        """
        capabilities = self._extract_capabilities(intent_text)
        risk = self._classify_risk(intent_text)

        tasks: list[dict[str, Any]] = []
        if self._engineering_planner is not None:
            try:
                planner_result = self._engineering_planner.plan(intent_text)
                if hasattr(planner_result, "tasks"):
                    tasks = [
                        t.to_dict() if hasattr(t, "to_dict") else {"description": str(t)}
                        for t in planner_result.tasks
                    ]
            except Exception as exc:
                logger.debug("engineering planner failed: %s", exc)

        if not tasks:
            tasks = [{"description": intent_text, "type": "engineering"}]

        plan = IDEPlan(
            intent_text=intent_text,
            tasks=tasks,
            capabilities_needed=capabilities,
            risk_class=risk,
            status="draft",
        )
        self._plans[plan.plan_id] = plan
        return plan

    # ── Assign + Dispatch ─────────────────────────────────────────

    def assign_plan(self, plan_id: str) -> list[dict[str, Any]]:
        """Assign plan tasks to agents via W3 fleet. Returns assignments."""
        plan = self._plans.get(plan_id)
        if not plan:
            return []

        assignments = []
        for task in plan.tasks:
            caps = plan.capabilities_needed or ["code"]
            assignment = self._agent_fleet.assign(
                capabilities_required=caps,
                risk_class=plan.risk_class,
            )
            assignments.append(assignment.to_dict())

        plan.status = "assigned"
        return assignments

    def dispatch_plan(self, plan_id: str) -> list[dict[str, Any]]:
        """Assign + dispatch plan tasks through the agent fleet."""
        plan = self._plans.get(plan_id)
        if not plan:
            return []

        dispatches = []
        for task in plan.tasks:
            caps = plan.capabilities_needed or ["code"]
            assignment = self._agent_fleet.assign(
                capabilities_required=caps,
                risk_class=plan.risk_class,
            )
            if assignment.agent_type:
                dispatch = self._agent_fleet.dispatch(
                    assignment,
                    description=task.get("description", ""),
                )
                dispatches.append(dispatch.to_dict())

                stream = DevelopmentStream(
                    plan_id=plan_id,
                    agent_type=assignment.agent_type,
                    compute_node_id=assignment.compute_node_id,
                    dispatch_id=dispatch.dispatch_id,
                    description=task.get("description", ""),
                )
                self._streams[stream.stream_id] = stream

                if self._execution_graph is not None:
                    try:
                        self._execution_graph.add_node(
                            node_id=dispatch.dispatch_id,
                            node_type="fleet_dispatch",
                            metadata={"plan_id": plan_id, "agent_type": assignment.agent_type},
                        )
                    except Exception as exc:
                        logger.debug("execution graph add_node failed: %s", exc)

        plan.status = "dispatched"
        return dispatches

    # ── Monitor ───────────────────────────────────────────────────

    def active_development(self) -> list[DevelopmentStream]:
        """All in-flight development streams."""
        return [
            s for s in self._streams.values()
            if s.phase not in (DevelopmentPhase.COMPLETE,)
        ]

    def session_detail(self, stream_id: str) -> dict[str, Any]:
        """Detail for a specific development stream."""
        stream = self._streams.get(stream_id)
        if not stream:
            return {"error": "stream not found"}
        return stream.to_dict()

    # ── Review ────────────────────────────────────────────────────

    def create_review(
        self,
        plan_id: str,
        artifacts: list[dict[str, Any]] | None = None,
        session_id: str = "",
    ) -> ReviewDetail:
        """Create a review package for completed work."""
        lineage: list[str] = []
        if self._execution_graph is not None:
            try:
                chain = self._execution_graph.get_chain(plan_id)
                if chain:
                    lineage = chain
            except Exception:
                pass

        review = ReviewDetail(
            plan_id=plan_id,
            session_id=session_id,
            artifacts=artifacts or [],
            lineage_chain=lineage,
        )

        if self._review_builder is not None:
            try:
                rec = self._review_builder.compute_recommendation_simple(artifacts or [])
                if rec:
                    review.recommendation = str(rec.get("recommendation", ""))
                    review.reasoning = str(rec.get("reasoning", ""))
            except Exception:
                pass

        self._reviews[review.review_id] = review
        return review

    def review_packages(self, status: str = "pending") -> list[ReviewDetail]:
        """Get review packages filtered by status."""
        try:
            target = ReviewStatus(status)
        except ValueError:
            target = ReviewStatus.PENDING
        return [r for r in self._reviews.values() if r.status == target]

    def review_detail(self, review_id: str) -> ReviewDetail | None:
        """Get detail for a specific review."""
        return self._reviews.get(review_id)

    # ── Merge ─────────────────────────────────────────────────────

    def approve_and_merge(self, review_id: str) -> MergeResult:
        """Approve a review and record the merge."""
        review = self._reviews.get(review_id)
        if not review:
            return MergeResult(review_id=review_id, error="review not found")

        if review.status != ReviewStatus.PENDING:
            return MergeResult(
                review_id=review_id,
                error=f"review status is {review.status.value}, expected pending",
            )

        review.status = ReviewStatus.APPROVED
        review.resolved_at = time.time()

        merge_sha = f"merge-{uuid4().hex[:8]}"
        result = MergeResult(
            review_id=review_id,
            merged_at=time.time(),
            branch=f"plan/{review.plan_id}",
            commit_sha=merge_sha,
            lineage_chain_id=review.lineage_chain[0] if review.lineage_chain else "",
            success=True,
        )

        review.status = ReviewStatus.MERGED
        self._merges.append(result)

        for s in self._streams.values():
            if s.plan_id == review.plan_id:
                s.phase = DevelopmentPhase.COMPLETE

        return result

    def reject_review(self, review_id: str, reason: str) -> bool:
        """Reject a review with reason."""
        review = self._reviews.get(review_id)
        if not review:
            return False
        review.status = ReviewStatus.REJECTED
        review.reasoning = reason
        review.resolved_at = time.time()
        return True

    # ── Status ────────────────────────────────────────────────────

    def ide_status(self) -> IDEStatusSnapshot:
        """Aggregated IDE status."""
        active_streams = self.active_development()
        agent_types = set()
        for s in active_streams:
            if s.agent_type:
                agent_types.add(s.agent_type)

        return IDEStatusSnapshot(
            active_agents=len(agent_types),
            pending_reviews=len(self.review_packages("pending")),
            repos_with_changes=len(self.workspace_snapshot().repos),
            recent_merges=len(self._merges),
            active_streams=len(active_streams),
            total_plans=len(self._plans),
        )

    # ── Helpers ───────────────────────────────────────────────────

    _CAPABILITY_KEYWORDS: dict[str, list[str]] = {
        "code": ["build", "implement", "add", "create", "fix", "refactor", "write"],
        "test": ["test", "verify", "validate", "check"],
        "deploy": ["deploy", "ship", "release", "publish"],
        "debug": ["debug", "investigate", "diagnose", "trace"],
        "code_review": ["review", "audit", "inspect"],
        "web_search": ["research", "search", "find", "look up"],
        "writing": ["document", "write docs", "readme"],
    }

    def _extract_capabilities(self, text: str) -> list[str]:
        """Deterministic capability extraction from intent text."""
        lower = text.lower()
        found: list[str] = []
        for cap, keywords in self._CAPABILITY_KEYWORDS.items():
            for kw in keywords:
                if kw in lower and cap not in found:
                    found.append(cap)
                    break
        return found or ["code"]

    _RISK_KEYWORDS: dict[str, list[str]] = {
        "high": ["migration", "schema", "production", "deploy", "delete", "drop"],
        "medium": ["refactor", "update", "change", "modify"],
    }

    def _classify_risk(self, text: str) -> str:
        """Deterministic risk classification from intent text."""
        lower = text.lower()
        for level, keywords in self._RISK_KEYWORDS.items():
            for kw in keywords:
                if kw in lower:
                    return level
        return "low"
