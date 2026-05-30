"""Self-Build Engineering Queue — canonical work item model and queue engine.

Transforms reliability-ranked candidates, audit findings, roadmap requirements,
and operator requests into governed engineering work items. The queue ranks work
deterministically using production-backed reliability signals and enforces
governed status transitions.

Phase 11.0 core module. UMH substrate subsystem. Instance-agnostic.
"""

from __future__ import annotations

import json
import logging
import os
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any
from uuid import uuid4

logger = logging.getLogger(__name__)

_REPO_ROOT = os.environ.get("UMH_ROOT", "/opt/OS")


class WorkItemStatus(str, Enum):
    DISCOVERED = "discovered"
    RANKED = "ranked"
    TRIAGED = "triaged"
    READY_FOR_APPROVAL = "ready_for_approval"
    APPROVAL_PENDING = "approval_pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    BLOCKED = "blocked"
    SANDBOX_READY = "sandbox_ready"
    SANDBOX_RUNNING = "sandbox_running"
    SANDBOX_COMPLETE = "sandbox_complete"
    PR_CREATED = "pr_created"
    PR_REVIEW = "pr_review"
    MERGED = "merged"
    PRODUCTION_VERIFICATION_PENDING = "production_verification_pending"
    PRODUCTION_VERIFIED = "production_verified"
    RESOLVED = "resolved"
    FAILED = "failed"
    SUPERSEDED = "superseded"
    ARCHIVED = "archived"


class WorkItemSourceType(str, Enum):
    RELIABILITY_RANKED_CANDIDATE = "reliability_ranked_candidate"
    CADENCE_CANDIDATE = "cadence_candidate"
    CONTRADICTION = "contradiction"
    WORLD_MODEL_GAP = "world_model_gap"
    DEPENDENCY_GAP = "dependency_gap"
    READINESS_GAP = "readiness_gap"
    TEMPLATE_GAP = "template_gap"
    PRODUCTION_TRUTH_GAP = "production_truth_gap"
    COCKPIT_GAP = "cockpit_gap"
    AUDIT_FINDING = "audit_finding"
    ROADMAP_REQUIREMENT = "roadmap_requirement"
    OPERATOR_REQUEST = "operator_request"
    PRODUCT_PROJECTION_NEED = "product_projection_need"


_TERMINAL_STATUSES = frozenset({
    WorkItemStatus.RESOLVED,
    WorkItemStatus.FAILED,
    WorkItemStatus.SUPERSEDED,
    WorkItemStatus.ARCHIVED,
    WorkItemStatus.REJECTED,
})

_VALID_TRANSITIONS: dict[WorkItemStatus, frozenset[WorkItemStatus]] = {
    WorkItemStatus.DISCOVERED: frozenset({
        WorkItemStatus.RANKED, WorkItemStatus.BLOCKED,
        WorkItemStatus.SUPERSEDED, WorkItemStatus.ARCHIVED,
    }),
    WorkItemStatus.RANKED: frozenset({
        WorkItemStatus.TRIAGED, WorkItemStatus.READY_FOR_APPROVAL,
        WorkItemStatus.BLOCKED, WorkItemStatus.SUPERSEDED,
    }),
    WorkItemStatus.TRIAGED: frozenset({
        WorkItemStatus.READY_FOR_APPROVAL, WorkItemStatus.BLOCKED,
        WorkItemStatus.SUPERSEDED,
    }),
    WorkItemStatus.READY_FOR_APPROVAL: frozenset({
        WorkItemStatus.APPROVAL_PENDING, WorkItemStatus.BLOCKED,
        WorkItemStatus.SUPERSEDED,
    }),
    WorkItemStatus.APPROVAL_PENDING: frozenset({
        WorkItemStatus.APPROVED, WorkItemStatus.REJECTED,
        WorkItemStatus.BLOCKED,
    }),
    WorkItemStatus.APPROVED: frozenset({
        WorkItemStatus.SANDBOX_READY, WorkItemStatus.BLOCKED,
    }),
    WorkItemStatus.SANDBOX_READY: frozenset({
        WorkItemStatus.SANDBOX_RUNNING, WorkItemStatus.BLOCKED,
    }),
    WorkItemStatus.SANDBOX_RUNNING: frozenset({
        WorkItemStatus.SANDBOX_COMPLETE, WorkItemStatus.FAILED,
        WorkItemStatus.BLOCKED,
    }),
    WorkItemStatus.SANDBOX_COMPLETE: frozenset({
        WorkItemStatus.PR_CREATED, WorkItemStatus.FAILED,
        WorkItemStatus.BLOCKED,
    }),
    WorkItemStatus.PR_CREATED: frozenset({
        WorkItemStatus.PR_REVIEW, WorkItemStatus.FAILED,
    }),
    WorkItemStatus.PR_REVIEW: frozenset({
        WorkItemStatus.MERGED, WorkItemStatus.FAILED,
        WorkItemStatus.BLOCKED,
    }),
    WorkItemStatus.MERGED: frozenset({
        WorkItemStatus.PRODUCTION_VERIFICATION_PENDING,
        WorkItemStatus.FAILED,
    }),
    WorkItemStatus.PRODUCTION_VERIFICATION_PENDING: frozenset({
        WorkItemStatus.PRODUCTION_VERIFIED, WorkItemStatus.FAILED,
    }),
    WorkItemStatus.PRODUCTION_VERIFIED: frozenset({
        WorkItemStatus.RESOLVED,
    }),
    WorkItemStatus.BLOCKED: frozenset({
        WorkItemStatus.DISCOVERED, WorkItemStatus.RANKED,
        WorkItemStatus.TRIAGED, WorkItemStatus.READY_FOR_APPROVAL,
        WorkItemStatus.SUPERSEDED, WorkItemStatus.ARCHIVED,
    }),
    WorkItemStatus.REJECTED: frozenset({WorkItemStatus.ARCHIVED}),
    WorkItemStatus.FAILED: frozenset({
        WorkItemStatus.DISCOVERED, WorkItemStatus.ARCHIVED,
    }),
    WorkItemStatus.RESOLVED: frozenset({WorkItemStatus.ARCHIVED}),
    WorkItemStatus.SUPERSEDED: frozenset({WorkItemStatus.ARCHIVED}),
    WorkItemStatus.ARCHIVED: frozenset(),
}


@dataclass
class SelfBuildWorkItem:
    work_item_id: str = field(default_factory=lambda: f"wk-{uuid4().hex[:8]}")
    title: str = ""
    description: str = ""
    source_type: str = ""
    source_id: str = ""
    source_evidence: list[dict[str, Any]] = field(default_factory=list)
    linked_candidate_id: str = ""
    linked_template_id: str = ""
    linked_agent_type: str = ""
    linked_capabilities: list[str] = field(default_factory=list)
    risk_class: str = "low"
    promotion_class: str = ""
    weighted_score: float = 0.0
    expected_leverage: float = 0.0
    expected_readiness_delta: float = 0.0
    affected_files: list[str] = field(default_factory=list)
    affected_subsystems: list[str] = field(default_factory=list)
    validation_plan: str = ""
    rollback_plan: str = ""
    governance_requirements: list[str] = field(default_factory=list)
    approval_packet_id: str = ""
    sandbox_id: str = ""
    branch_name: str = ""
    pr_url: str = ""
    production_truth_delta_id: str = ""
    outcome_ids: list[str] = field(default_factory=list)
    memory_candidate_ids: list[str] = field(default_factory=list)
    status: WorkItemStatus = WorkItemStatus.DISCOVERED
    status_reason: str = ""
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)
    expires_at: float = 0.0
    blocked_reasons: list[str] = field(default_factory=list)
    dependency_ids: list[str] = field(default_factory=list)
    parent_goal_id: str = ""
    roadmap_phase: str = ""
    operator_notes: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "work_item_id": self.work_item_id,
            "title": self.title,
            "description": self.description,
            "source_type": self.source_type,
            "source_id": self.source_id,
            "source_evidence": self.source_evidence,
            "linked_candidate_id": self.linked_candidate_id,
            "linked_template_id": self.linked_template_id,
            "linked_agent_type": self.linked_agent_type,
            "linked_capabilities": self.linked_capabilities,
            "risk_class": self.risk_class,
            "promotion_class": self.promotion_class,
            "weighted_score": round(self.weighted_score, 4),
            "expected_leverage": round(self.expected_leverage, 3),
            "expected_readiness_delta": round(self.expected_readiness_delta, 3),
            "affected_files": self.affected_files,
            "affected_subsystems": self.affected_subsystems,
            "validation_plan": self.validation_plan,
            "rollback_plan": self.rollback_plan,
            "governance_requirements": self.governance_requirements,
            "approval_packet_id": self.approval_packet_id,
            "sandbox_id": self.sandbox_id,
            "branch_name": self.branch_name,
            "pr_url": self.pr_url,
            "production_truth_delta_id": self.production_truth_delta_id,
            "outcome_ids": self.outcome_ids,
            "memory_candidate_ids": self.memory_candidate_ids,
            "status": self.status.value,
            "status_reason": self.status_reason,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "expires_at": self.expires_at,
            "blocked_reasons": self.blocked_reasons,
            "dependency_ids": self.dependency_ids,
            "parent_goal_id": self.parent_goal_id,
            "roadmap_phase": self.roadmap_phase,
            "operator_notes": self.operator_notes,
        }

    def to_safe_dict(self) -> dict[str, Any]:
        """Public-safe version omitting internal IDs and evidence details."""
        return {
            "work_item_id": self.work_item_id,
            "title": self.title,
            "description": self.description,
            "source_type": self.source_type,
            "risk_class": self.risk_class,
            "promotion_class": self.promotion_class,
            "weighted_score": round(self.weighted_score, 4),
            "status": self.status.value,
            "status_reason": self.status_reason,
            "roadmap_phase": self.roadmap_phase,
            "blocked_reasons": self.blocked_reasons,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> SelfBuildWorkItem:
        status_raw = d.get("status", "discovered")
        try:
            status = WorkItemStatus(status_raw)
        except ValueError:
            status = WorkItemStatus.DISCOVERED
        return cls(
            work_item_id=d.get("work_item_id", f"wk-{uuid4().hex[:8]}"),
            title=d.get("title", ""),
            description=d.get("description", ""),
            source_type=d.get("source_type", ""),
            source_id=d.get("source_id", ""),
            source_evidence=d.get("source_evidence", []),
            linked_candidate_id=d.get("linked_candidate_id", ""),
            linked_template_id=d.get("linked_template_id", ""),
            linked_agent_type=d.get("linked_agent_type", ""),
            linked_capabilities=d.get("linked_capabilities", []),
            risk_class=d.get("risk_class", "low"),
            promotion_class=d.get("promotion_class", ""),
            weighted_score=float(d.get("weighted_score", 0.0)),
            expected_leverage=float(d.get("expected_leverage", 0.0)),
            expected_readiness_delta=float(d.get("expected_readiness_delta", 0.0)),
            affected_files=d.get("affected_files", []),
            affected_subsystems=d.get("affected_subsystems", []),
            validation_plan=d.get("validation_plan", ""),
            rollback_plan=d.get("rollback_plan", ""),
            governance_requirements=d.get("governance_requirements", []),
            approval_packet_id=d.get("approval_packet_id", ""),
            sandbox_id=d.get("sandbox_id", ""),
            branch_name=d.get("branch_name", ""),
            pr_url=d.get("pr_url", ""),
            production_truth_delta_id=d.get("production_truth_delta_id", ""),
            outcome_ids=d.get("outcome_ids", []),
            memory_candidate_ids=d.get("memory_candidate_ids", []),
            status=status,
            status_reason=d.get("status_reason", ""),
            created_at=float(d.get("created_at", time.time())),
            updated_at=float(d.get("updated_at", time.time())),
            expires_at=float(d.get("expires_at", 0.0)),
            blocked_reasons=d.get("blocked_reasons", []),
            dependency_ids=d.get("dependency_ids", []),
            parent_goal_id=d.get("parent_goal_id", ""),
            roadmap_phase=d.get("roadmap_phase", ""),
            operator_notes=d.get("operator_notes", ""),
        )


class SelfBuildQueueEngine:
    """Deterministic engineering queue — ranks, transitions, and persists work items."""

    RANKING_WEIGHTS = {
        "reliability_score": 0.25,
        "expected_leverage": 0.20,
        "roadmap_priority": 0.15,
        "template_reliability": 0.10,
        "agent_reliability": 0.10,
        "validation_strength": 0.10,
        "rollback_strength": 0.05,
        "freshness": 0.05,
    }

    ROADMAP_PRIORITY_MAP: dict[str, float] = {
        "11.0": 1.0,
        "12": 0.8,
        "13": 0.6,
        "14": 0.4,
        "15": 0.3,
        "20": 0.1,
    }

    def __init__(self, store_path: str | None = None) -> None:
        self._store_path = store_path or os.path.join(
            _REPO_ROOT, "data", "umh", "self_build", "work_items.jsonl",
        )
        self._items: dict[str, SelfBuildWorkItem] = {}
        self._load()

    def _load(self) -> None:
        if not os.path.exists(self._store_path):
            return
        try:
            with open(self._store_path, "r") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    d = json.loads(line)
                    item = SelfBuildWorkItem.from_dict(d)
                    self._items[item.work_item_id] = item
        except (json.JSONDecodeError, OSError) as exc:
            logger.warning("Failed to load work items: %s", exc)

    def _save(self) -> None:
        os.makedirs(os.path.dirname(self._store_path), exist_ok=True)
        with open(self._store_path, "w") as f:
            for item in self._items.values():
                f.write(json.dumps(item.to_dict()) + "\n")

    def create_work_item(
        self,
        title: str,
        description: str,
        source_type: str,
        source_id: str = "",
        source_evidence: list[dict[str, Any]] | None = None,
        **kwargs: Any,
    ) -> SelfBuildWorkItem:
        for existing in self._items.values():
            if (
                existing.source_id == source_id
                and source_id
                and existing.status not in _TERMINAL_STATUSES
            ):
                logger.debug("Duplicate suppressed for source_id=%s", source_id)
                return existing

        item = SelfBuildWorkItem(
            title=title,
            description=description,
            source_type=source_type,
            source_id=source_id,
            source_evidence=source_evidence or [],
            **kwargs,
        )
        self._items[item.work_item_id] = item
        self._save()
        return item

    def ingest_ranked_candidates(
        self, ranked: list[dict[str, Any]],
    ) -> list[SelfBuildWorkItem]:
        created: list[SelfBuildWorkItem] = []
        for rc in ranked:
            cid = rc.get("candidate_id", "")
            item = self.create_work_item(
                title=rc.get("title", f"Ranked candidate: {cid}"),
                description=rc.get("description", ""),
                source_type=WorkItemSourceType.RELIABILITY_RANKED_CANDIDATE.value,
                source_id=cid,
                source_evidence=[{"type": "ranked_candidate", "data": rc}],
                linked_candidate_id=cid,
                linked_template_id=rc.get("template_id", ""),
                linked_agent_type=rc.get("agent_type", ""),
                risk_class=rc.get("risk_class", "low"),
                promotion_class=rc.get("promotion_class", ""),
                weighted_score=float(rc.get("weighted_score", 0.0)),
                expected_leverage=float(rc.get("expected_leverage", 0.0)),
                validation_plan=rc.get("validation_plan", ""),
                rollback_plan=rc.get("rollback_plan", ""),
                affected_files=rc.get("affected_files", []),
            )
            created.append(item)
        return created

    def ingest_audit_findings(
        self, findings: list[dict[str, Any]],
    ) -> list[SelfBuildWorkItem]:
        created: list[SelfBuildWorkItem] = []
        for f in findings:
            item = self.create_work_item(
                title=f.get("title", "Audit finding"),
                description=f.get("description", ""),
                source_type=WorkItemSourceType.AUDIT_FINDING.value,
                source_id=f.get("finding_id", ""),
                source_evidence=[{"type": "audit_finding", "data": f}],
                risk_class=f.get("risk_class", "low"),
                roadmap_phase=f.get("roadmap_phase", ""),
                affected_subsystems=f.get("affected_subsystems", []),
            )
            created.append(item)
        return created

    def ingest_roadmap_requirements(
        self, requirements: list[dict[str, Any]],
    ) -> list[SelfBuildWorkItem]:
        created: list[SelfBuildWorkItem] = []
        for r in requirements:
            item = self.create_work_item(
                title=r.get("title", "Roadmap requirement"),
                description=r.get("description", ""),
                source_type=WorkItemSourceType.ROADMAP_REQUIREMENT.value,
                source_id=r.get("requirement_id", ""),
                source_evidence=[{"type": "roadmap_requirement", "data": r}],
                risk_class=r.get("risk_class", "low"),
                roadmap_phase=r.get("roadmap_phase", ""),
                expected_leverage=float(r.get("expected_leverage", 0.0)),
            )
            created.append(item)
        return created

    def update_status(
        self,
        work_item_id: str,
        new_status: WorkItemStatus,
        reason: str = "",
    ) -> bool:
        item = self._items.get(work_item_id)
        if not item:
            logger.warning("Work item not found: %s", work_item_id)
            return False

        allowed = _VALID_TRANSITIONS.get(item.status, frozenset())
        if new_status not in allowed:
            logger.warning(
                "Invalid transition %s -> %s for %s",
                item.status.value, new_status.value, work_item_id,
            )
            return False

        item.status = new_status
        item.status_reason = reason
        item.updated_at = time.time()
        self._save()
        return True

    def mark_resolved(self, work_item_id: str, reason: str = "") -> bool:
        item = self._items.get(work_item_id)
        if not item:
            return False
        if item.status == WorkItemStatus.PRODUCTION_VERIFIED:
            return self.update_status(work_item_id, WorkItemStatus.RESOLVED, reason)
        return False

    def mark_blocked(
        self, work_item_id: str, reasons: list[str], status_reason: str = "",
    ) -> bool:
        item = self._items.get(work_item_id)
        if not item:
            return False
        item.blocked_reasons = reasons
        return self.update_status(work_item_id, WorkItemStatus.BLOCKED, status_reason)

    def mark_superseded(
        self, work_item_id: str, superseded_by: str = "",
    ) -> bool:
        reason = f"Superseded by {superseded_by}" if superseded_by else "Superseded"
        return self.update_status(
            work_item_id, WorkItemStatus.SUPERSEDED, reason,
        )

    def link_approval_packet(
        self, work_item_id: str, packet_id: str,
    ) -> bool:
        item = self._items.get(work_item_id)
        if not item:
            return False
        item.approval_packet_id = packet_id
        item.updated_at = time.time()
        self._save()
        return True

    def link_sandbox(
        self, work_item_id: str, sandbox_id: str, branch_name: str = "",
    ) -> bool:
        item = self._items.get(work_item_id)
        if not item:
            return False
        item.sandbox_id = sandbox_id
        if branch_name:
            item.branch_name = branch_name
        item.updated_at = time.time()
        self._save()
        return True

    def link_pr(self, work_item_id: str, pr_url: str) -> bool:
        item = self._items.get(work_item_id)
        if not item:
            return False
        item.pr_url = pr_url
        item.updated_at = time.time()
        self._save()
        return True

    def link_production_truth(
        self, work_item_id: str, delta_id: str,
    ) -> bool:
        item = self._items.get(work_item_id)
        if not item:
            return False
        item.production_truth_delta_id = delta_id
        item.updated_at = time.time()
        self._save()
        return True

    def rank_work_items(self) -> list[SelfBuildWorkItem]:
        active = [
            item for item in self._items.values()
            if item.status not in _TERMINAL_STATUSES
        ]
        for item in active:
            item.weighted_score = self._compute_score(item)

        active.sort(key=lambda x: x.weighted_score, reverse=True)
        for i, item in enumerate(active):
            item.updated_at = time.time()

        self._save()
        return active

    def _compute_score(self, item: SelfBuildWorkItem) -> float:
        w = self.RANKING_WEIGHTS
        roadmap_score = self.ROADMAP_PRIORITY_MAP.get(
            item.roadmap_phase, 0.2,
        )
        age_hours = (time.time() - item.created_at) / 3600.0
        freshness = max(0.0, 1.0 - (age_hours / (24.0 * 30.0)))

        risk_mult = {"low": 1.0, "medium": 0.5, "high": 0.1}.get(
            item.risk_class, 0.3,
        )
        if item.blocked_reasons:
            risk_mult *= 0.1

        has_validation = 1.0 if item.validation_plan else 0.3
        has_rollback = 1.0 if item.rollback_plan else 0.3

        raw = (
            item.weighted_score * w["reliability_score"]
            + item.expected_leverage * w["expected_leverage"]
            + roadmap_score * w["roadmap_priority"]
            + risk_mult * w["template_reliability"]
            + risk_mult * w["agent_reliability"]
            + has_validation * w["validation_strength"]
            + has_rollback * w["rollback_strength"]
            + freshness * w["freshness"]
        )
        return round(raw, 4)

    def get_item(self, work_item_id: str) -> SelfBuildWorkItem | None:
        return self._items.get(work_item_id)

    def get_ready_for_approval(self) -> list[SelfBuildWorkItem]:
        return [
            item for item in self._items.values()
            if item.status == WorkItemStatus.READY_FOR_APPROVAL
        ]

    def get_active_work(self) -> list[SelfBuildWorkItem]:
        active_statuses = {
            WorkItemStatus.APPROVED,
            WorkItemStatus.SANDBOX_READY,
            WorkItemStatus.SANDBOX_RUNNING,
            WorkItemStatus.SANDBOX_COMPLETE,
            WorkItemStatus.PR_CREATED,
            WorkItemStatus.PR_REVIEW,
            WorkItemStatus.MERGED,
            WorkItemStatus.PRODUCTION_VERIFICATION_PENDING,
        }
        return [
            item for item in self._items.values()
            if item.status in active_statuses
        ]

    def get_blocked_work(self) -> list[SelfBuildWorkItem]:
        return [
            item for item in self._items.values()
            if item.status == WorkItemStatus.BLOCKED
        ]

    def get_production_verified(self) -> list[SelfBuildWorkItem]:
        return [
            item for item in self._items.values()
            if item.status == WorkItemStatus.PRODUCTION_VERIFIED
        ]

    def get_next_best_work(self) -> SelfBuildWorkItem | None:
        ranked = self.rank_work_items()
        eligible = [
            item for item in ranked
            if item.status in {
                WorkItemStatus.RANKED,
                WorkItemStatus.TRIAGED,
                WorkItemStatus.READY_FOR_APPROVAL,
            }
            and item.risk_class != "medium"
            and not item.blocked_reasons
        ]
        return eligible[0] if eligible else None

    def compute_queue_summary(self) -> dict[str, Any]:
        status_counts: dict[str, int] = {}
        for item in self._items.values():
            key = item.status.value
            status_counts[key] = status_counts.get(key, 0) + 1

        risk_counts: dict[str, int] = {}
        for item in self._items.values():
            if item.status not in _TERMINAL_STATUSES:
                risk_counts[item.risk_class] = risk_counts.get(
                    item.risk_class, 0,
                ) + 1

        source_counts: dict[str, int] = {}
        for item in self._items.values():
            source_counts[item.source_type] = source_counts.get(
                item.source_type, 0,
            ) + 1

        next_best = self.get_next_best_work()
        return {
            "total_items": len(self._items),
            "status_counts": status_counts,
            "risk_counts": risk_counts,
            "source_counts": source_counts,
            "ready_for_approval": len(self.get_ready_for_approval()),
            "active_work": len(self.get_active_work()),
            "blocked": len(self.get_blocked_work()),
            "production_verified": len(self.get_production_verified()),
            "next_best": next_best.to_safe_dict() if next_best else None,
        }

    def check_eligibility(self, item: SelfBuildWorkItem) -> tuple[bool, list[str]]:
        """Check whether a work item is eligible to advance to approval."""
        blockers: list[str] = []

        if not item.source_evidence:
            blockers.append("Missing source evidence")

        if item.risk_class == "medium":
            blockers.append("Medium-risk execution blocked by policy")

        if not item.validation_plan and item.risk_class != "low":
            blockers.append("Missing validation plan for non-low-risk item")

        if not item.rollback_plan and item.risk_class != "low":
            blockers.append("Missing rollback plan for non-low-risk item")

        if item.dependency_ids:
            for dep_id in item.dependency_ids:
                dep = self._items.get(dep_id)
                if dep and dep.status not in _TERMINAL_STATUSES:
                    blockers.append(f"Dependency {dep_id} not resolved")

        return (len(blockers) == 0, blockers)

    def advance_to_ready(self, work_item_id: str) -> tuple[bool, list[str]]:
        """Try to advance item to ready_for_approval if eligible."""
        item = self._items.get(work_item_id)
        if not item:
            return (False, ["Work item not found"])

        eligible, blockers = self.check_eligibility(item)
        if not eligible:
            return (False, blockers)

        if item.status == WorkItemStatus.DISCOVERED:
            self.update_status(work_item_id, WorkItemStatus.RANKED, "Auto-ranked")
        if item.status == WorkItemStatus.RANKED:
            self.update_status(work_item_id, WorkItemStatus.READY_FOR_APPROVAL, "Eligibility checks passed")

        return (True, [])

    def all_items(self) -> list[SelfBuildWorkItem]:
        return list(self._items.values())
