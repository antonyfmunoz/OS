"""Phase 82 storage views — read-only view models for storage state.

UI-safe, typed, no secrets. No execution. No adapter calls. No LLM calls.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from umh.core.clock import iso_now as _iso_now
from umh.storage.contracts import (
    StorageRecordDescriptor,
    StorageRecordType,
)
from umh.storage.policy import (
    StoragePolicy,
    build_default_storage_policy,
    classify_record_mutability,
    is_append_only,
)


@dataclass
class StorageDescriptorView:
    record_id: str
    record_type: str = ""
    scope: str = ""
    mutability: str = ""
    source: str = ""
    backend_type: str = ""
    owner_id: str = ""
    created_at: str = ""
    updated_at: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "record_id": self.record_id,
            "record_type": self.record_type,
            "scope": self.scope,
            "mutability": self.mutability,
            "source": self.source,
            "backend_type": self.backend_type,
            "owner_id": self.owner_id,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "metadata": self.metadata,
        }


@dataclass
class StorageHealthView:
    generated_at: str = ""
    total_records: int = 0
    records_by_type: dict[str, int] = field(default_factory=dict)
    records_by_mutability: dict[str, int] = field(default_factory=dict)
    backend_count: int = 0
    registered_backends: list[str] = field(default_factory=list)
    append_only_count: int = 0
    mutable_count: int = 0
    policy_summary: dict[str, Any] = field(default_factory=dict)
    warnings: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "generated_at": self.generated_at,
            "total_records": self.total_records,
            "records_by_type": self.records_by_type,
            "records_by_mutability": self.records_by_mutability,
            "backend_count": self.backend_count,
            "registered_backends": self.registered_backends,
            "append_only_count": self.append_only_count,
            "mutable_count": self.mutable_count,
            "policy_summary": self.policy_summary,
            "warnings": self.warnings,
            "metadata": self.metadata,
        }


@dataclass
class StorageAuditView:
    generated_at: str = ""
    total_findings: int = 0
    critical_count: int = 0
    error_count: int = 0
    warning_count: int = 0
    info_count: int = 0
    findings_by_type: dict[str, int] = field(default_factory=dict)
    top_findings: list[dict[str, Any]] = field(default_factory=list)
    checked_file_count: int = 0
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "generated_at": self.generated_at,
            "total_findings": self.total_findings,
            "critical_count": self.critical_count,
            "error_count": self.error_count,
            "warning_count": self.warning_count,
            "info_count": self.info_count,
            "findings_by_type": self.findings_by_type,
            "top_findings": self.top_findings,
            "checked_file_count": self.checked_file_count,
            "metadata": self.metadata,
        }


def build_descriptor_view(descriptor: StorageRecordDescriptor) -> StorageDescriptorView:
    return StorageDescriptorView(
        record_id=descriptor.record_id,
        record_type=descriptor.record_type.value,
        scope=descriptor.scope.value,
        mutability=descriptor.mutability.value,
        source=descriptor.source.value,
        backend_type=descriptor.backend_type.value,
        owner_id=descriptor.owner_id,
        created_at=descriptor.created_at,
        updated_at=descriptor.updated_at,
    )


def build_storage_health_view(
    descriptors: list[StorageRecordDescriptor],
    policy: StoragePolicy | None = None,
    backend_names: list[str] | None = None,
) -> StorageHealthView:
    if policy is None:
        policy = build_default_storage_policy()

    by_type: dict[str, int] = {}
    by_mut: dict[str, int] = {}
    ao_count = 0
    mut_count = 0
    warnings: list[str] = []

    for d in descriptors:
        rt = d.record_type.value
        by_type[rt] = by_type.get(rt, 0) + 1

        m = classify_record_mutability(d.record_type)
        mv = m.value
        by_mut[mv] = by_mut.get(mv, 0) + 1

        if is_append_only(d.record_type):
            ao_count += 1
        else:
            mut_count += 1

    return StorageHealthView(
        generated_at=_iso_now(),
        total_records=len(descriptors),
        records_by_type=by_type,
        records_by_mutability=by_mut,
        backend_count=len(backend_names or []) + 1,
        registered_backends=sorted(backend_names or []),
        append_only_count=ao_count,
        mutable_count=mut_count,
        policy_summary=policy.to_dict(),
        warnings=warnings,
    )


def build_storage_audit_view(
    report: Any,
    max_top_findings: int = 10,
) -> StorageAuditView:
    findings = getattr(report, "findings", [])
    by_type: dict[str, int] = {}
    for f in findings:
        ft = getattr(f, "finding_type", "unknown")
        by_type[ft] = by_type.get(ft, 0) + 1

    severity_order = {"critical": 0, "error": 1, "warning": 2, "info": 3}
    sorted_findings = sorted(
        findings,
        key=lambda f: severity_order.get(getattr(f, "severity", "info"), 4),
    )
    top = [getattr(f, "to_dict", lambda: {})() for f in sorted_findings[:max_top_findings]]

    return StorageAuditView(
        generated_at=getattr(report, "generated_at", _iso_now()),
        total_findings=getattr(report, "total_findings", len(findings)),
        critical_count=getattr(report, "critical_count", 0),
        error_count=getattr(report, "error_count", 0),
        warning_count=getattr(report, "warning_count", 0),
        info_count=getattr(report, "info_count", 0),
        findings_by_type=by_type,
        top_findings=top,
        checked_file_count=len(getattr(report, "checked_paths", [])),
    )
