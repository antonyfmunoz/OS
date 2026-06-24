"""Engineering Execution Contracts — governed execution session types.

Defines the contract between approved engineering plans (Phase 22) and
the execution coordination layer (Phase 23). Session, artifact, and
proof package types with full lineage tracking.

No execution logic. No LLM calls. Pure data contracts.

Phase 23. UMH substrate subsystem. Instance-agnostic.
"""

from __future__ import annotations

import hashlib
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any
from uuid import uuid4


class EngineeringExecutionStatus(str, Enum):
    PENDING = "pending"
    PLANNED = "planned"
    EXECUTING = "executing"
    VALIDATING = "validating"
    AWAITING_REVIEW = "awaiting_review"
    APPROVED = "approved"
    REJECTED = "rejected"
    FAILED = "failed"
    PAUSED = "paused"
    CANCELLED = "cancelled"


class OperatorRecommendation(str, Enum):
    APPROVE = "approve"
    APPROVE_WITH_NOTES = "approve_with_notes"
    NEEDS_REVIEW = "needs_review"
    REJECT = "reject"


class EngineeringArtifactType(str, Enum):
    CODE = "code"
    TEST = "test"
    DOCUMENTATION = "documentation"
    CONFIGURATION = "configuration"
    REPORT = "report"


@dataclass
class EngineeringArtifact:
    """File-level artifact produced during engineering execution."""

    artifact_id: str = field(default_factory=lambda: f"eart-{uuid4().hex[:12]}")
    session_id: str = ""
    task_id: str = ""
    file_path: str = ""
    artifact_type: EngineeringArtifactType = EngineeringArtifactType.CODE
    diff_summary: str = ""
    content_hash: str = ""
    created_at: float = field(default_factory=time.time)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "artifact_id": self.artifact_id,
            "session_id": self.session_id,
            "task_id": self.task_id,
            "file_path": self.file_path,
            "artifact_type": self.artifact_type.value
            if isinstance(self.artifact_type, EngineeringArtifactType)
            else self.artifact_type,
            "diff_summary": self.diff_summary,
            "content_hash": self.content_hash,
            "created_at": self.created_at,
            "metadata": self.metadata,
        }

    @classmethod
    def from_executor_artifact(
        cls,
        executor_artifact: dict[str, Any],
        session_id: str,
        task_id: str,
    ) -> EngineeringArtifact:
        """Map an ExecutorArtifact dict to an EngineeringArtifact."""
        content = executor_artifact.get("content", "")
        return cls(
            session_id=session_id,
            task_id=task_id,
            file_path=executor_artifact.get("name", ""),
            artifact_type=_classify_artifact_type(executor_artifact.get("artifact_type", "")),
            diff_summary=content[:500] if content else "",
            content_hash=hashlib.sha256(
                content.encode() if isinstance(content, str) else content
            ).hexdigest()[:16],
            metadata=executor_artifact.get("metadata", {}),
        )


def _classify_artifact_type(raw_type: str) -> EngineeringArtifactType:
    """Deterministic classification of executor artifact types."""
    lower = raw_type.lower()
    if "test" in lower:
        return EngineeringArtifactType.TEST
    if "doc" in lower or "readme" in lower:
        return EngineeringArtifactType.DOCUMENTATION
    if "config" in lower or "yaml" in lower or "json" in lower:
        return EngineeringArtifactType.CONFIGURATION
    if "report" in lower or "audit" in lower:
        return EngineeringArtifactType.REPORT
    return EngineeringArtifactType.CODE


@dataclass
class EngineeringExecutionSession:
    """Tracks a governed engineering execution from plan to review."""

    session_id: str = field(default_factory=lambda: f"ees-{uuid4().hex[:12]}")
    plan_id: str = ""
    packet_ids: list[str] = field(default_factory=list)
    executor_request_ids: list[str] = field(default_factory=list)
    status: EngineeringExecutionStatus = EngineeringExecutionStatus.PENDING
    artifacts: list[EngineeringArtifact] = field(default_factory=list)
    task_results: dict[str, dict[str, Any]] = field(default_factory=dict)
    workspace_targets: list[str] = field(default_factory=list)
    worker_assignments: dict[str, str] = field(default_factory=dict)
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)
    completed_at: float = 0.0
    operator_id: str = ""
    execution_trace_ids: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    sandbox_worktree: str = ""
    sandbox_branch: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "session_id": self.session_id,
            "plan_id": self.plan_id,
            "packet_ids": self.packet_ids,
            "executor_request_ids": self.executor_request_ids,
            "status": self.status.value
            if isinstance(self.status, EngineeringExecutionStatus)
            else self.status,
            "artifacts": [a.to_dict() for a in self.artifacts],
            "task_results": self.task_results,
            "workspace_targets": self.workspace_targets,
            "worker_assignments": self.worker_assignments,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "completed_at": self.completed_at,
            "operator_id": self.operator_id,
            "execution_trace_ids": self.execution_trace_ids,
            "errors": self.errors,
            "sandbox_worktree": self.sandbox_worktree,
            "sandbox_branch": self.sandbox_branch,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> EngineeringExecutionSession:
        """Restore a session from its serialized dict."""
        status_raw = data.get("status", "pending")
        try:
            status = EngineeringExecutionStatus(status_raw)
        except ValueError:
            status = EngineeringExecutionStatus.PENDING

        session = cls(
            session_id=data.get("session_id", ""),
            plan_id=data.get("plan_id", ""),
            status=status,
            workspace_targets=data.get("workspace_targets", []),
            operator_id=data.get("operator_id", ""),
        )
        session.packet_ids = data.get("packet_ids", [])
        session.executor_request_ids = data.get("executor_request_ids", [])
        session.task_results = data.get("task_results", {})
        session.worker_assignments = data.get("worker_assignments", {})
        session.created_at = data.get("created_at", 0.0)
        session.updated_at = data.get("updated_at", 0.0)
        session.completed_at = data.get("completed_at", 0.0)
        session.execution_trace_ids = data.get("execution_trace_ids", [])
        session.errors = data.get("errors", [])
        session.sandbox_worktree = data.get("sandbox_worktree", "")
        session.sandbox_branch = data.get("sandbox_branch", "")

        for art_data in data.get("artifacts", []):
            art_type_raw = art_data.get("artifact_type", "code")
            try:
                art_type = EngineeringArtifactType(art_type_raw)
            except ValueError:
                art_type = EngineeringArtifactType.CODE
            art = EngineeringArtifact(
                artifact_id=art_data.get("artifact_id", ""),
                session_id=art_data.get("session_id", ""),
                task_id=art_data.get("task_id", ""),
                file_path=art_data.get("file_path", ""),
                artifact_type=art_type,
                diff_summary=art_data.get("diff_summary", ""),
                content_hash=art_data.get("content_hash", ""),
                created_at=art_data.get("created_at", 0.0),
                metadata=art_data.get("metadata", {}),
            )
            session.artifacts.append(art)
        return session


@dataclass
class EngineeringProofPackage:
    """Assembled proof for operator review — no merge/push/deploy authority."""

    proof_id: str = field(default_factory=lambda: f"epp-{uuid4().hex[:12]}")
    session_id: str = ""
    plan_id: str = ""
    artifacts: list[EngineeringArtifact] = field(default_factory=list)
    validation_results: list[dict[str, Any]] = field(default_factory=list)
    risk_summary: list[dict[str, Any]] = field(default_factory=list)
    diff_summary: dict[str, Any] = field(default_factory=dict)
    trace_ids: list[str] = field(default_factory=list)
    operator_recommendation: OperatorRecommendation = OperatorRecommendation.NEEDS_REVIEW
    recommendation_reasoning: list[str] = field(default_factory=list)
    review_status: str = "pending"
    reviewed_at: float = 0.0
    reviewed_by: str = ""
    rejection_reason: str = ""
    browser_verification: dict[str, Any] = field(default_factory=dict)
    outcome_verification: dict[str, Any] = field(default_factory=dict)
    created_at: float = field(default_factory=time.time)

    def to_dict(self) -> dict[str, Any]:
        return {
            "proof_id": self.proof_id,
            "session_id": self.session_id,
            "plan_id": self.plan_id,
            "artifacts": [a.to_dict() for a in self.artifacts],
            "validation_results": self.validation_results,
            "risk_summary": self.risk_summary,
            "diff_summary": self.diff_summary,
            "trace_ids": self.trace_ids,
            "operator_recommendation": self.operator_recommendation.value
            if isinstance(self.operator_recommendation, OperatorRecommendation)
            else self.operator_recommendation,
            "recommendation_reasoning": self.recommendation_reasoning,
            "review_status": self.review_status,
            "reviewed_at": self.reviewed_at,
            "reviewed_by": self.reviewed_by,
            "rejection_reason": self.rejection_reason,
            "browser_verification": self.browser_verification,
            "outcome_verification": self.outcome_verification,
            "created_at": self.created_at,
        }
