"""Phase 82 storage policy — rules for what operations are allowed per record type.

No execution. No mutation. No adapter calls. No LLM calls.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from typing import Any

from umh.storage.contracts import (
    StorageMutability,
    StorageOperation,
    StorageRecordDescriptor,
    StorageRecordType,
)


@dataclass
class StoragePolicyDecision:
    decision_id: str
    allowed: bool = False
    operation: StorageOperation = StorageOperation.UNKNOWN
    record_type: StorageRecordType = StorageRecordType.UNKNOWN
    mutability: StorageMutability = StorageMutability.UNKNOWN
    reason: str = ""
    required_authority: str = ""
    warnings: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "decision_id": self.decision_id,
            "allowed": self.allowed,
            "operation": self.operation.value,
            "record_type": self.record_type.value,
            "mutability": self.mutability.value,
            "reason": self.reason,
            "required_authority": self.required_authority,
            "warnings": self.warnings,
            "metadata": self.metadata,
        }


_APPEND_ONLY_TYPES = frozenset(
    {
        StorageRecordType.TRACE,
        StorageRecordType.OUTCOME,
        StorageRecordType.FEEDBACK,
        StorageRecordType.AUDIT_RECORD,
        StorageRecordType.SYSTEM_REPORT,
    }
)

_PROMOTABLE_TYPES = frozenset(
    {
        StorageRecordType.MEMORY_CANDIDATE,
    }
)

_MUTABLE_TYPES = frozenset(
    {
        StorageRecordType.WORKSTATION_PROFILE,
        StorageRecordType.SESSION_STATE,
        StorageRecordType.DEVICE_REGISTRY,
        StorageRecordType.ENVIRONMENT_REGISTRY,
        StorageRecordType.IDENTITY,
    }
)

_VERSIONED_TYPES = frozenset(
    {
        StorageRecordType.REGISTRY_ITEM,
    }
)

_IMMUTABLE_TYPES = frozenset(
    {
        StorageRecordType.ONTOLOGY_PRIMITIVE,
        StorageRecordType.ONTOLOGY_LAW,
        StorageRecordType.DOMAIN_PROJECTION,
        StorageRecordType.CORRESPONDENCE_MAP,
    }
)

_FUTURE_TYPES = frozenset(
    {
        StorageRecordType.TEMPLATE,
        StorageRecordType.LIBRARY_ITEM,
        StorageRecordType.WORLD_MODEL_STATE,
    }
)


@dataclass
class StoragePolicy:
    append_only_types: frozenset[StorageRecordType] = field(
        default_factory=lambda: _APPEND_ONLY_TYPES
    )
    promotable_types: frozenset[StorageRecordType] = field(
        default_factory=lambda: _PROMOTABLE_TYPES
    )
    mutable_types: frozenset[StorageRecordType] = field(default_factory=lambda: _MUTABLE_TYPES)
    versioned_types: frozenset[StorageRecordType] = field(default_factory=lambda: _VERSIONED_TYPES)
    immutable_types: frozenset[StorageRecordType] = field(default_factory=lambda: _IMMUTABLE_TYPES)
    future_types: frozenset[StorageRecordType] = field(default_factory=lambda: _FUTURE_TYPES)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "append_only_types": sorted(t.value for t in self.append_only_types),
            "promotable_types": sorted(t.value for t in self.promotable_types),
            "mutable_types": sorted(t.value for t in self.mutable_types),
            "versioned_types": sorted(t.value for t in self.versioned_types),
            "immutable_types": sorted(t.value for t in self.immutable_types),
            "future_types": sorted(t.value for t in self.future_types),
            "metadata": self.metadata,
        }


def build_default_storage_policy() -> StoragePolicy:
    return StoragePolicy()


def classify_record_mutability(record_type: StorageRecordType) -> StorageMutability:
    if record_type in _APPEND_ONLY_TYPES:
        return StorageMutability.APPEND_ONLY
    if record_type in _PROMOTABLE_TYPES:
        return StorageMutability.PROMOTABLE
    if record_type in _MUTABLE_TYPES:
        return StorageMutability.MUTABLE
    if record_type in _VERSIONED_TYPES:
        return StorageMutability.VERSIONED
    if record_type in _IMMUTABLE_TYPES:
        return StorageMutability.IMMUTABLE
    if record_type in _FUTURE_TYPES:
        return StorageMutability.UNKNOWN
    return StorageMutability.UNKNOWN


def is_append_only(record_type: StorageRecordType) -> bool:
    return record_type in _APPEND_ONLY_TYPES


def is_promotable(record_type: StorageRecordType) -> bool:
    return record_type in _PROMOTABLE_TYPES


def is_mutable(record_type: StorageRecordType) -> bool:
    return record_type in _MUTABLE_TYPES or record_type in _VERSIONED_TYPES


def _decision_id() -> str:
    return f"spd_{uuid.uuid4().hex[:10]}"


def evaluate_storage_operation(
    descriptor: StorageRecordDescriptor,
    operation: StorageOperation,
    policy: StoragePolicy | None = None,
) -> StoragePolicyDecision:
    if policy is None:
        policy = build_default_storage_policy()

    rt = descriptor.record_type
    mut = classify_record_mutability(rt)
    warnings: list[str] = []

    if operation == StorageOperation.DELETE:
        return StoragePolicyDecision(
            decision_id=_decision_id(),
            allowed=False,
            operation=operation,
            record_type=rt,
            mutability=mut,
            reason="DELETE denied by default storage policy",
        )

    if operation in (StorageOperation.READ, StorageOperation.LIST, StorageOperation.AUDIT):
        return StoragePolicyDecision(
            decision_id=_decision_id(),
            allowed=True,
            operation=operation,
            record_type=rt,
            mutability=mut,
            reason="Read/list/audit always allowed",
        )

    if rt == StorageRecordType.UNKNOWN:
        if operation in (
            StorageOperation.WRITE,
            StorageOperation.APPEND,
            StorageOperation.UPDATE,
            StorageOperation.PROMOTE,
        ):
            return StoragePolicyDecision(
                decision_id=_decision_id(),
                allowed=False,
                operation=operation,
                record_type=rt,
                mutability=mut,
                reason="Write/update/promote denied for unknown record type",
            )

    if rt in _FUTURE_TYPES:
        return StoragePolicyDecision(
            decision_id=_decision_id(),
            allowed=False,
            operation=operation,
            record_type=rt,
            mutability=mut,
            reason=f"{rt.value} is a future type; persistence not implemented yet",
            warnings=["Future type — requires future phase implementation"],
        )

    if mut == StorageMutability.APPEND_ONLY:
        if operation == StorageOperation.APPEND or operation == StorageOperation.WRITE:
            return StoragePolicyDecision(
                decision_id=_decision_id(),
                allowed=True,
                operation=operation,
                record_type=rt,
                mutability=mut,
                reason="Append allowed for append-only record type",
            )
        if operation == StorageOperation.UPDATE:
            return StoragePolicyDecision(
                decision_id=_decision_id(),
                allowed=False,
                operation=operation,
                record_type=rt,
                mutability=mut,
                reason="Update denied for append-only record type",
            )
        if operation == StorageOperation.PROMOTE:
            return StoragePolicyDecision(
                decision_id=_decision_id(),
                allowed=False,
                operation=operation,
                record_type=rt,
                mutability=mut,
                reason="Promote not applicable to append-only record type",
            )

    if mut == StorageMutability.IMMUTABLE:
        if operation == StorageOperation.WRITE:
            return StoragePolicyDecision(
                decision_id=_decision_id(),
                allowed=False,
                operation=operation,
                record_type=rt,
                mutability=mut,
                reason="Write denied for immutable record type (read-only metadata)",
                warnings=["Immutable types are loaded from defaults, not written"],
            )
        if operation in (StorageOperation.UPDATE, StorageOperation.PROMOTE):
            return StoragePolicyDecision(
                decision_id=_decision_id(),
                allowed=False,
                operation=operation,
                record_type=rt,
                mutability=mut,
                reason=f"{operation.value} denied for immutable record type",
            )

    if mut == StorageMutability.PROMOTABLE:
        if operation == StorageOperation.PROMOTE:
            return StoragePolicyDecision(
                decision_id=_decision_id(),
                allowed=False,
                operation=operation,
                record_type=rt,
                mutability=mut,
                reason="Promote requires future promotion engine (not implemented in Phase 82)",
                required_authority="promotion_engine",
                warnings=["Promotion logic deferred to future phase"],
            )
        if operation in (StorageOperation.WRITE, StorageOperation.APPEND):
            return StoragePolicyDecision(
                decision_id=_decision_id(),
                allowed=True,
                operation=operation,
                record_type=rt,
                mutability=mut,
                reason="Write/append allowed for promotable candidate",
            )
        if operation == StorageOperation.UPDATE:
            return StoragePolicyDecision(
                decision_id=_decision_id(),
                allowed=True,
                operation=operation,
                record_type=rt,
                mutability=mut,
                reason="Update allowed for promotable candidate (status change)",
                warnings=["Updates should not auto-promote"],
            )

    if mut in (StorageMutability.MUTABLE, StorageMutability.VERSIONED):
        if operation in (StorageOperation.WRITE, StorageOperation.APPEND, StorageOperation.UPDATE):
            if mut == StorageMutability.VERSIONED:
                warnings.append("Versioned type — consider recording version")
            return StoragePolicyDecision(
                decision_id=_decision_id(),
                allowed=True,
                operation=operation,
                record_type=rt,
                mutability=mut,
                reason=f"{operation.value} allowed for {mut.value} record type",
                warnings=warnings,
            )

    return StoragePolicyDecision(
        decision_id=_decision_id(),
        allowed=False,
        operation=operation,
        record_type=rt,
        mutability=mut,
        reason="Operation not explicitly allowed by storage policy",
    )
