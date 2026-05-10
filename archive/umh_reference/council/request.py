"""Phase 85 deliberation request — typed input to the council.

A DeliberationRequest describes the question, context, constraints,
and urgency that the council should deliberate on.

No execution. No mutation. No adapter calls. No LLM calls.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from umh.council.contracts import (
    CouncilStatus,
    DeliberationDomain,
    UrgencyLevel,
    _council_id,
    normalize_council_status,
    normalize_deliberation_domain,
    normalize_urgency_level,
)


@dataclass
class DeliberationRequest:
    request_id: str = ""
    question: str = ""
    context: str = ""
    domain: DeliberationDomain = DeliberationDomain.UNKNOWN
    urgency: UrgencyLevel = UrgencyLevel.MEDIUM
    constraints: list[str] = field(default_factory=list)
    success_criteria: list[str] = field(default_factory=list)
    relevant_laws: list[str] = field(default_factory=list)
    relevant_polarities: list[str] = field(default_factory=list)
    status: CouncilStatus = CouncilStatus.DRAFT
    requested_by: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "request_id": self.request_id,
            "question": self.question,
            "context": self.context,
            "domain": self.domain.value,
            "urgency": self.urgency.value,
            "constraints": self.constraints,
            "success_criteria": self.success_criteria,
            "relevant_laws": self.relevant_laws,
            "relevant_polarities": self.relevant_polarities,
            "status": self.status.value,
            "requested_by": self.requested_by,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> DeliberationRequest:
        return cls(
            request_id=data.get("request_id", _council_id("dreq")),
            question=data.get("question", ""),
            context=data.get("context", ""),
            domain=normalize_deliberation_domain(data.get("domain", "unknown")),
            urgency=normalize_urgency_level(data.get("urgency", "medium")),
            constraints=data.get("constraints", []),
            success_criteria=data.get("success_criteria", []),
            relevant_laws=data.get("relevant_laws", []),
            relevant_polarities=data.get("relevant_polarities", []),
            status=normalize_council_status(data.get("status", "draft")),
            requested_by=data.get("requested_by", ""),
            metadata=data.get("metadata", {}),
        )


def create_deliberation_request(
    question: str,
    *,
    context: str = "",
    domain: DeliberationDomain = DeliberationDomain.UNKNOWN,
    urgency: UrgencyLevel = UrgencyLevel.MEDIUM,
    constraints: list[str] | None = None,
    success_criteria: list[str] | None = None,
    relevant_laws: list[str] | None = None,
    relevant_polarities: list[str] | None = None,
    requested_by: str = "",
    metadata: dict[str, Any] | None = None,
) -> DeliberationRequest:
    return DeliberationRequest(
        request_id=_council_id("dreq"),
        question=question,
        context=context,
        domain=domain,
        urgency=urgency,
        constraints=constraints or [],
        success_criteria=success_criteria or [],
        relevant_laws=relevant_laws or [],
        relevant_polarities=relevant_polarities or [],
        status=CouncilStatus.DRAFT,
        requested_by=requested_by,
        metadata=metadata or {},
    )


def validate_deliberation_request(req: DeliberationRequest) -> list[str]:
    issues: list[str] = []
    if not req.question or not req.question.strip():
        issues.append("Missing question")
    if not req.request_id:
        issues.append("Missing request_id")
    if req.domain == DeliberationDomain.UNKNOWN:
        issues.append("Domain is unknown — consider specifying")
    return issues
