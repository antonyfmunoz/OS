"""Meta IDE Projection Build Loop Runtime — governed build from inside cockpit.

Answers: "Can I prompt the AI and build from inside the cockpit?"

Orchestrates: classify intent → detect projection → plan → dispatch → review → merge.
Does NOT implement projection feature code. Prepares build context and routes
work through AgentFleet + ComputeFabric.

Campaign 3.4. UMH substrate layer. Instance-agnostic.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any
from uuid import uuid4

logger = logging.getLogger(__name__)


class BuildLoopPhase(str, Enum):
    INTENT_CAPTURE = "intent_capture"
    CLASSIFICATION = "classification"
    PLANNING = "planning"
    ASSIGNMENT = "assignment"
    EXECUTION = "execution"
    REVIEW = "review"
    MERGE = "merge"
    COMPLETE = "complete"


@dataclass
class BuildRequest:
    request_id: str = ""
    text: str = ""
    projection_target: str = ""
    phase: BuildLoopPhase = BuildLoopPhase.INTENT_CAPTURE
    intent_classification: dict[str, Any] = field(default_factory=dict)
    plan_id: str = ""
    dispatch_ids: list[str] = field(default_factory=list)
    review_id: str = ""
    merge_result: dict[str, Any] = field(default_factory=dict)
    created_at: float = field(default_factory=time.time)
    error: str = ""

    def __post_init__(self) -> None:
        if not self.request_id:
            self.request_id = f"br-{uuid4().hex[:8]}"

    def to_dict(self) -> dict[str, Any]:
        return {
            "request_id": self.request_id,
            "text": self.text,
            "projection_target": self.projection_target,
            "phase": self.phase.value,
            "intent_classification": self.intent_classification,
            "plan_id": self.plan_id,
            "dispatch_ids": self.dispatch_ids,
            "review_id": self.review_id,
            "merge_result": self.merge_result,
            "created_at": self.created_at,
            "error": self.error,
        }


@dataclass
class BuildLoopStatus:
    active_requests: int = 0
    by_phase: dict[str, int] = field(default_factory=dict)
    active_agents: int = 0
    pending_reviews: int = 0
    recent_merges: int = 0
    projection_distribution: dict[str, int] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "active_requests": self.active_requests,
            "by_phase": self.by_phase,
            "active_agents": self.active_agents,
            "pending_reviews": self.pending_reviews,
            "recent_merges": self.recent_merges,
            "projection_distribution": self.projection_distribution,
        }


_PROJECTION_KEYWORDS: dict[str, list[str]] = {
    "lyfeos": ["lyfeos", "lyfe os", "life management"],
    "creatoros": ["creatoros", "creator os", "content platform"],
    "entrepreneuros": ["eos", "entrepreneuros", "entrepreneur", "outreach"],
}


def _detect_projection(text: str, explicit_target: str = "") -> str:
    if explicit_target:
        lower = explicit_target.lower().strip()
        for proj_id, keywords in _PROJECTION_KEYWORDS.items():
            if lower in keywords or lower == proj_id:
                return proj_id
        return explicit_target

    lower_text = text.lower()
    for proj_id, keywords in _PROJECTION_KEYWORDS.items():
        for kw in keywords:
            if kw in lower_text:
                return proj_id
    return ""


class MetaIDEProjectionLoopRuntime:
    """Governed build loop: intent → plan → dispatch → review → merge.

    Composes EmbodimentRuntime, MetaIDERuntime, AgentFleetRuntime,
    ComputeFabricRuntime, ExecutionGraph, IntentRuntime, ProjectionPort.
    """

    def __init__(
        self,
        embodiment: Any | None = None,
        meta_ide: Any | None = None,
        agent_fleet: Any | None = None,
        compute_fabric: Any | None = None,
        execution_graph: Any | None = None,
        intent_runtime: Any | None = None,
        projection_port: Any | None = None,
    ) -> None:
        self._embodiment = embodiment
        self._meta_ide = meta_ide
        self._agent_fleet = agent_fleet
        self._compute_fabric = compute_fabric
        self._execution_graph = execution_graph
        self._intent_runtime = intent_runtime
        self._projection_port = projection_port
        self._requests: dict[str, BuildRequest] = {}

    def submit(self, text: str, projection_target: str = "") -> BuildRequest:
        req = BuildRequest(text=text)

        # Phase 1: Intent capture
        req.phase = BuildLoopPhase.CLASSIFICATION

        # Phase 2: Classification
        try:
            if self._embodiment:
                classification = self._embodiment.classify_intent(text)
                req.intent_classification = (
                    classification if isinstance(classification, dict)
                    else {"type": str(classification)}
                )
        except Exception:
            logger.debug("Embodiment classification unavailable", exc_info=True)

        # Phase 3: Projection detection
        detected = _detect_projection(text, projection_target)
        if detected:
            req.projection_target = detected

        # Validate against registered projections
        if self._projection_port and detected:
            try:
                registrations = self._projection_port.list_registrations()
                reg_ids = {
                    getattr(r, "projection_id", getattr(r, "name", str(r)))
                    for r in registrations
                } if registrations else set()
                if reg_ids and detected not in reg_ids:
                    logger.debug("Projection '%s' not in registered projections", detected)
            except Exception:
                logger.debug("ProjectionPort unavailable", exc_info=True)

        # Phase 4: Planning
        req.phase = BuildLoopPhase.PLANNING
        try:
            if self._meta_ide:
                plan = self._meta_ide.plan_from_intent(text)
                if plan:
                    req.plan_id = getattr(plan, "plan_id", getattr(plan, "id", str(plan)))
                    req.phase = BuildLoopPhase.ASSIGNMENT
            else:
                req.error = "MetaIDERuntime not available"
        except Exception as e:
            logger.debug("MetaIDE planning failed: %s", e, exc_info=True)
            req.error = f"Planning failed: {e}"

        # Phase 5: Dispatch
        if req.plan_id and not req.error:
            try:
                if self._meta_ide:
                    dispatches = self._meta_ide.dispatch_plan(req.plan_id)
                    if dispatches:
                        req.dispatch_ids = [
                            getattr(d, "dispatch_id", getattr(d, "id", str(d)))
                            for d in (dispatches if isinstance(dispatches, list) else [dispatches])
                        ]
                    req.phase = BuildLoopPhase.EXECUTION
            except Exception as e:
                logger.debug("MetaIDE dispatch failed: %s", e, exc_info=True)
                req.error = f"Dispatch failed: {e}"

        # Record lineage
        if self._execution_graph and req.dispatch_ids:
            try:
                for did in req.dispatch_ids:
                    self._execution_graph.record(
                        node_type="build_loop_dispatch",
                        node_id=did,
                        metadata={"request_id": req.request_id, "projection": req.projection_target},
                    )
            except Exception:
                logger.debug("ExecutionGraph recording failed", exc_info=True)

        self._requests[req.request_id] = req
        return req

    def advance(self, request_id: str) -> BuildRequest:
        req = self._requests.get(request_id)
        if not req:
            return BuildRequest(request_id=request_id, error="Request not found")

        phase_order = list(BuildLoopPhase)
        current_idx = phase_order.index(req.phase)
        if current_idx < len(phase_order) - 1:
            req.phase = phase_order[current_idx + 1]
        return req

    def review(self, request_id: str) -> BuildRequest:
        req = self._requests.get(request_id)
        if not req:
            return BuildRequest(request_id=request_id, error="Request not found")

        if req.phase not in (BuildLoopPhase.EXECUTION, BuildLoopPhase.REVIEW):
            return BuildRequest(
                request_id=request_id,
                error=f"Cannot review in phase {req.phase.value}",
            )

        req.phase = BuildLoopPhase.REVIEW

        try:
            if self._meta_ide and req.plan_id:
                review_result = self._meta_ide.review_packages()
                if review_result:
                    req.review_id = getattr(
                        review_result, "review_id",
                        getattr(review_result, "id", str(review_result)),
                    )
        except Exception as e:
            logger.debug("MetaIDE review failed: %s", e, exc_info=True)
            req.error = f"Review failed: {e}"

        return req

    def merge(self, request_id: str) -> BuildRequest:
        req = self._requests.get(request_id)
        if not req:
            return BuildRequest(request_id=request_id, error="Request not found")

        if req.phase != BuildLoopPhase.REVIEW:
            return BuildRequest(
                request_id=request_id,
                error=f"Cannot merge in phase {req.phase.value}",
            )

        try:
            if self._meta_ide and req.review_id:
                result = self._meta_ide.approve_and_merge(req.review_id)
                req.merge_result = result if isinstance(result, dict) else {"status": "merged"}
            else:
                req.merge_result = {"status": "merged_no_ide"}
        except Exception as e:
            logger.debug("MetaIDE merge failed: %s", e, exc_info=True)
            req.error = f"Merge failed: {e}"

        req.phase = BuildLoopPhase.COMPLETE
        return req

    def reject(self, request_id: str, reason: str) -> BuildRequest:
        req = self._requests.get(request_id)
        if not req:
            return BuildRequest(request_id=request_id, error="Request not found")

        try:
            if self._meta_ide and req.review_id:
                self._meta_ide.reject_review(req.review_id)
        except Exception:
            logger.debug("MetaIDE reject failed", exc_info=True)

        req.error = f"Rejected: {reason}"
        req.phase = BuildLoopPhase.PLANNING
        return req

    def status(self) -> BuildLoopStatus:
        active = [r for r in self._requests.values() if r.phase != BuildLoopPhase.COMPLETE]
        by_phase: dict[str, int] = {}
        proj_dist: dict[str, int] = {}
        pending_reviews = 0
        recent_merges = 0

        for r in self._requests.values():
            by_phase[r.phase.value] = by_phase.get(r.phase.value, 0) + 1
            if r.projection_target:
                proj_dist[r.projection_target] = proj_dist.get(r.projection_target, 0) + 1
            if r.phase == BuildLoopPhase.REVIEW:
                pending_reviews += 1
            if r.phase == BuildLoopPhase.COMPLETE and r.merge_result:
                recent_merges += 1

        active_agents = 0
        if self._agent_fleet:
            try:
                fleet_st = self._agent_fleet.fleet_status()
                active_agents = getattr(fleet_st, "active_agents", 0) if fleet_st else 0
            except Exception:
                pass

        return BuildLoopStatus(
            active_requests=len(active),
            by_phase=by_phase,
            active_agents=active_agents,
            pending_reviews=pending_reviews,
            recent_merges=recent_merges,
            projection_distribution=proj_dist,
        )

    def request_detail(self, request_id: str) -> BuildRequest | None:
        return self._requests.get(request_id)

    def active_requests(self) -> list[BuildRequest]:
        return [
            r for r in self._requests.values()
            if r.phase != BuildLoopPhase.COMPLETE
        ]

    def history(self, limit: int = 50) -> list[BuildRequest]:
        completed = [
            r for r in self._requests.values()
            if r.phase == BuildLoopPhase.COMPLETE
        ]
        completed.sort(key=lambda r: r.created_at, reverse=True)
        return completed[:limit]
