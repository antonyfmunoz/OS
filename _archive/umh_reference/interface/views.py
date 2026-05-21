"""Phase 79 interface view models — UI-facing read models.

Stable, typed, safe for display. No secrets. No execution.
No adapter calls. No trace mutation. Sparse-safe.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class TraceView:
    trace_id: str
    user_id: str = ""
    session_id: str = ""
    status: str = ""
    capability: str = ""
    environment: str = ""
    adapter: str = ""
    started_at: str = ""
    completed_at: str = ""
    duration_ms: int | None = None
    outcome_status: str = ""
    summary: str = ""
    attention_required: bool = False
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "trace_id": self.trace_id,
            "user_id": self.user_id,
            "session_id": self.session_id,
            "status": self.status,
            "capability": self.capability,
            "environment": self.environment,
            "adapter": self.adapter,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
            "duration_ms": self.duration_ms,
            "outcome_status": self.outcome_status,
            "summary": self.summary,
            "attention_required": self.attention_required,
            "metadata": self.metadata,
        }


@dataclass
class OutcomeView:
    outcome_id: str
    trace_id: str = ""
    user_id: str = ""
    status: str = ""
    success_score: float = 0.0
    confidence: float = 0.0
    summary: str = ""
    evidence_count: int = 0
    errors_count: int = 0
    timestamp: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "outcome_id": self.outcome_id,
            "trace_id": self.trace_id,
            "user_id": self.user_id,
            "status": self.status,
            "success_score": self.success_score,
            "confidence": self.confidence,
            "summary": self.summary,
            "evidence_count": self.evidence_count,
            "errors_count": self.errors_count,
            "timestamp": self.timestamp,
            "metadata": self.metadata,
        }


@dataclass
class FeedbackView:
    feedback_id: str
    trace_id: str = ""
    outcome_id: str = ""
    user_id: str = ""
    signal_type: str = ""
    score: float = 0.0
    confidence: float = 0.0
    source: str = ""
    notes_preview: str = ""
    timestamp: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "feedback_id": self.feedback_id,
            "trace_id": self.trace_id,
            "outcome_id": self.outcome_id,
            "user_id": self.user_id,
            "signal_type": self.signal_type,
            "score": self.score,
            "confidence": self.confidence,
            "source": self.source,
            "notes_preview": self.notes_preview,
            "timestamp": self.timestamp,
            "metadata": self.metadata,
        }


@dataclass
class MemoryCandidateView:
    candidate_id: str
    trace_id: str = ""
    outcome_id: str = ""
    user_id: str = ""
    memory_type: str = ""
    confidence: float = 0.0
    reason: str = ""
    promotion_status: str = "candidate"
    content_preview: str = ""
    created_at: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "candidate_id": self.candidate_id,
            "trace_id": self.trace_id,
            "outcome_id": self.outcome_id,
            "user_id": self.user_id,
            "memory_type": self.memory_type,
            "confidence": self.confidence,
            "reason": self.reason,
            "promotion_status": self.promotion_status,
            "content_preview": self.content_preview,
            "created_at": self.created_at,
            "metadata": self.metadata,
        }


@dataclass
class GovernanceDecisionView:
    trace_id: str
    user_id: str = ""
    status: str = ""
    authority_required: str = ""
    risk_level: str = ""
    capability: str = ""
    environment: str = ""
    reason: str = ""
    attention_required: bool = False
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "trace_id": self.trace_id,
            "user_id": self.user_id,
            "status": self.status,
            "authority_required": self.authority_required,
            "risk_level": self.risk_level,
            "capability": self.capability,
            "environment": self.environment,
            "reason": self.reason,
            "attention_required": self.attention_required,
            "metadata": self.metadata,
        }


@dataclass
class AdapterStatusView:
    adapter_name: str
    capabilities: list[str] = field(default_factory=list)
    environments: list[str] = field(default_factory=list)
    status: str = "unknown"
    simulated: bool = False
    last_used_trace_id: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "adapter_name": self.adapter_name,
            "capabilities": self.capabilities,
            "environments": self.environments,
            "status": self.status,
            "simulated": self.simulated,
            "last_used_trace_id": self.last_used_trace_id,
            "metadata": self.metadata,
        }


@dataclass
class WorkstationStatusView:
    user_id: str
    workstation_id: str = ""
    active_mode: str = ""
    active_session_id: str = ""
    active_device: str = ""
    active_environment: str = ""
    execution_preference: dict[str, Any] = field(default_factory=dict)
    pending_approval_count: int = 0
    recent_trace_count: int = 0
    resume_summary: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "user_id": self.user_id,
            "workstation_id": self.workstation_id,
            "active_mode": self.active_mode,
            "active_session_id": self.active_session_id,
            "active_device": self.active_device,
            "active_environment": self.active_environment,
            "execution_preference": self.execution_preference,
            "pending_approval_count": self.pending_approval_count,
            "recent_trace_count": self.recent_trace_count,
            "resume_summary": self.resume_summary,
            "metadata": self.metadata,
        }


@dataclass
class OperatorDashboardSnapshot:
    user_id: str
    generated_at: str = ""
    system_health: str = "unknown"
    workstation: dict[str, Any] = field(default_factory=dict)
    recent_traces: list[dict[str, Any]] = field(default_factory=list)
    recent_outcomes: list[dict[str, Any]] = field(default_factory=list)
    recent_feedback: list[dict[str, Any]] = field(default_factory=list)
    memory_candidates: list[dict[str, Any]] = field(default_factory=list)
    failures: list[dict[str, Any]] = field(default_factory=list)
    denials: list[dict[str, Any]] = field(default_factory=list)
    pending_attention: list[dict[str, Any]] = field(default_factory=list)
    adapter_statuses: list[dict[str, Any]] = field(default_factory=list)
    ontology_summary: dict[str, Any] = field(default_factory=dict)
    storage_summary: dict[str, Any] = field(default_factory=dict)
    memory_discipline_summary: dict[str, Any] = field(default_factory=dict)
    migration_summary: dict[str, Any] = field(default_factory=dict)
    interface_summary: dict[str, Any] = field(default_factory=dict)
    next_resume_points: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "user_id": self.user_id,
            "generated_at": self.generated_at,
            "system_health": self.system_health,
            "workstation": self.workstation,
            "recent_traces": self.recent_traces,
            "recent_outcomes": self.recent_outcomes,
            "recent_feedback": self.recent_feedback,
            "memory_candidates": self.memory_candidates,
            "failures": self.failures,
            "denials": self.denials,
            "pending_attention": self.pending_attention,
            "adapter_statuses": self.adapter_statuses,
            "ontology_summary": self.ontology_summary,
            "storage_summary": self.storage_summary,
            "memory_discipline_summary": self.memory_discipline_summary,
            "migration_summary": self.migration_summary,
            "interface_summary": self.interface_summary,
            "next_resume_points": self.next_resume_points,
            "warnings": self.warnings,
            "metadata": self.metadata,
        }
