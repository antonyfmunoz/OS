"""Phase 82 memory write validator — validate all memory writes before storage.

Deterministic. No execution. No adapter calls. No LLM calls.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from typing import Any

from umh.memory.discipline import (
    MemoryRecord,
    MemoryStatus,
    MemoryWritePolicy,
    build_default_memory_write_policy,
    clamp_confidence,
)


@dataclass
class MemoryWriteValidationIssue:
    issue_id: str
    severity: str = "warning"
    message: str = ""
    field_name: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "issue_id": self.issue_id,
            "severity": self.severity,
            "message": self.message,
            "field": self.field_name,
            "metadata": self.metadata,
        }


@dataclass
class MemoryWriteValidationResult:
    valid: bool = True
    issues: list[MemoryWriteValidationIssue] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    candidate_id: str = ""
    memory_id: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "valid": self.valid,
            "issues": [i.to_dict() for i in self.issues],
            "warnings": self.warnings,
            "candidate_id": self.candidate_id,
            "memory_id": self.memory_id,
            "metadata": self.metadata,
        }


def _issue_id() -> str:
    return f"mwvi_{uuid.uuid4().hex[:10]}"


def _issue(severity: str, message: str, field_name: str = "") -> MemoryWriteValidationIssue:
    return MemoryWriteValidationIssue(
        issue_id=_issue_id(),
        severity=severity,
        message=message,
        field_name=field_name,
    )


def validate_memory_source(source: str) -> list[MemoryWriteValidationIssue]:
    issues: list[MemoryWriteValidationIssue] = []
    if not source:
        issues.append(_issue("error", "Memory source is required", "source"))
    return issues


def validate_memory_confidence(
    confidence: float,
    min_confidence: float = 0.0,
) -> list[MemoryWriteValidationIssue]:
    issues: list[MemoryWriteValidationIssue] = []
    clamped = clamp_confidence(confidence)
    if clamped != confidence:
        issues.append(
            _issue("warning", f"Confidence clamped from {confidence} to {clamped}", "confidence")
        )
    if clamped < min_confidence:
        issues.append(
            _issue("warning", f"Confidence {clamped} below minimum {min_confidence}", "confidence")
        )
    return issues


def validate_memory_evidence(evidence: list[str] | None) -> list[MemoryWriteValidationIssue]:
    issues: list[MemoryWriteValidationIssue] = []
    if not evidence:
        issues.append(_issue("warning", "No evidence provided", "evidence"))
    return issues


def validate_no_auto_promotion(candidate_or_record: Any) -> list[MemoryWriteValidationIssue]:
    issues: list[MemoryWriteValidationIssue] = []
    status = getattr(candidate_or_record, "status", None)
    if status is not None:
        status_str = status.value if hasattr(status, "value") else str(status).lower()
        if status_str == "promoted":
            issues.append(
                _issue(
                    "error",
                    "Auto-promoted status not allowed in Phase 82",
                    "status",
                )
            )
    ps = getattr(candidate_or_record, "promotion_status", None)
    if ps is not None:
        ps_str = ps.value if hasattr(ps, "value") else str(ps).lower()
        if ps_str == "promoted":
            issues.append(
                _issue(
                    "error",
                    "Auto-promoted promotion_status not allowed in Phase 82",
                    "promotion_status",
                )
            )
    return issues


def validate_memory_candidate(candidate: Any) -> MemoryWriteValidationResult:
    issues: list[MemoryWriteValidationIssue] = []
    warnings: list[str] = []

    cid = getattr(candidate, "candidate_id", "")
    content = getattr(candidate, "content", "")
    source_attr = getattr(candidate, "source", "")
    if not source_attr:
        source_val = "feedback_loop"
    else:
        source_val = source_attr.value if hasattr(source_attr, "value") else str(source_attr)

    conf = getattr(candidate, "confidence", 0.5)
    evidence = list(getattr(candidate, "evidence", []))

    if not content:
        issues.append(_issue("warning", "Candidate has no content", "content"))
        warnings.append("No content")

    issues.extend(validate_memory_source(source_val))
    issues.extend(validate_memory_confidence(conf))
    issues.extend(validate_memory_evidence(evidence))
    issues.extend(validate_no_auto_promotion(candidate))

    errors = [i for i in issues if i.severity == "error"]
    return MemoryWriteValidationResult(
        valid=len(errors) == 0,
        issues=issues,
        warnings=warnings,
        candidate_id=cid,
    )


def validate_memory_write(
    record: MemoryRecord,
    policy: MemoryWritePolicy | None = None,
) -> MemoryWriteValidationResult:
    if policy is None:
        policy = build_default_memory_write_policy()

    issues: list[MemoryWriteValidationIssue] = []
    warnings: list[str] = []

    if policy.require_source:
        issues.extend(validate_memory_source(record.source))

    if policy.require_confidence:
        issues.extend(validate_memory_confidence(record.confidence, policy.min_confidence))

    if policy.requires_evidence:
        issues.extend(validate_memory_evidence(record.evidence))

    issues.extend(validate_no_auto_promotion(record))

    if not record.content:
        issues.append(_issue("error", "Memory record has no content", "content"))

    if record.source and record.source not in policy.allowed_sources:
        warnings.append(f"Source '{record.source}' not in allowed sources")

    errors = [i for i in issues if i.severity == "error"]
    return MemoryWriteValidationResult(
        valid=len(errors) == 0,
        issues=issues,
        warnings=warnings,
        memory_id=record.memory_id,
    )
