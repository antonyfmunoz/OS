"""Phase 82 storage contracts — typed envelopes for all durable UMH state.

Every durable record declares type, scope, mutability, source, and backend.
No execution. No mutation of external state. No adapter calls.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from umh.core.clock import iso_now as _iso_now


def clamp_confidence(value: float) -> float:
    return max(0.0, min(1.0, value))


class StorageRecordType(str, Enum):
    IDENTITY = "identity"
    TRACE = "trace"
    OUTCOME = "outcome"
    FEEDBACK = "feedback"
    MEMORY_CANDIDATE = "memory_candidate"
    MEMORY_RECORD = "memory_record"
    WORKSTATION_PROFILE = "workstation_profile"
    SESSION_STATE = "session_state"
    DEVICE_REGISTRY = "device_registry"
    ENVIRONMENT_REGISTRY = "environment_registry"
    REGISTRY_ITEM = "registry_item"
    ONTOLOGY_PRIMITIVE = "ontology_primitive"
    ONTOLOGY_LAW = "ontology_law"
    DOMAIN_PROJECTION = "domain_projection"
    CORRESPONDENCE_MAP = "correspondence_map"
    TEMPLATE = "template"
    LIBRARY_ITEM = "library_item"
    WORLD_MODEL_STATE = "world_model_state"
    SYSTEM_REPORT = "system_report"
    AUDIT_RECORD = "audit_record"
    UNKNOWN = "unknown"


def normalize_storage_record_type(value: str) -> StorageRecordType:
    v = value.strip().lower()
    for m in StorageRecordType:
        if m.value == v:
            return m
    return StorageRecordType.UNKNOWN


class StorageScope(str, Enum):
    USER = "user"
    SESSION = "session"
    DEVICE = "device"
    ENVIRONMENT = "environment"
    SYSTEM = "system"
    WORKSPACE = "workspace"
    DOMAIN = "domain"
    GLOBAL = "global"
    UNKNOWN = "unknown"


def normalize_storage_scope(value: str) -> StorageScope:
    v = value.strip().lower()
    for m in StorageScope:
        if m.value == v:
            return m
    return StorageScope.UNKNOWN


class StorageMutability(str, Enum):
    APPEND_ONLY = "append_only"
    IMMUTABLE = "immutable"
    MUTABLE = "mutable"
    VERSIONED = "versioned"
    TRANSIENT = "transient"
    PROMOTABLE = "promotable"
    UNKNOWN = "unknown"


def normalize_storage_mutability(value: str) -> StorageMutability:
    v = value.strip().lower()
    for m in StorageMutability:
        if m.value == v:
            return m
    return StorageMutability.UNKNOWN


class StorageSource(str, Enum):
    SYSTEM = "system"
    USER = "user"
    ADAPTER = "adapter"
    GOVERNANCE = "governance"
    EXECUTION = "execution"
    FEEDBACK_LOOP = "feedback_loop"
    WORKSTATION = "workstation"
    REGISTRY = "registry"
    ONTOLOGY = "ontology"
    OBSERVABILITY = "observability"
    IMPORT = "import"
    UNKNOWN = "unknown"


def normalize_storage_source(value: str) -> StorageSource:
    v = value.strip().lower()
    for m in StorageSource:
        if m.value == v:
            return m
    return StorageSource.UNKNOWN


class StorageBackendType(str, Enum):
    MEMORY = "memory"
    SQLITE = "sqlite"
    JSONL = "jsonl"
    JSON = "json"
    FILESYSTEM = "filesystem"
    NEON = "neon"
    POSTGRES = "postgres"
    UNKNOWN = "unknown"


def normalize_backend_type(value: str) -> StorageBackendType:
    v = value.strip().lower()
    for m in StorageBackendType:
        if m.value == v:
            return m
    return StorageBackendType.UNKNOWN


class StorageOperation(str, Enum):
    READ = "read"
    WRITE = "write"
    APPEND = "append"
    UPDATE = "update"
    PROMOTE = "promote"
    DELETE = "delete"
    LIST = "list"
    AUDIT = "audit"
    UNKNOWN = "unknown"


def normalize_storage_operation(value: str) -> StorageOperation:
    v = value.strip().lower()
    for m in StorageOperation:
        if m.value == v:
            return m
    return StorageOperation.UNKNOWN


def _storage_id(prefix: str = "stor") -> str:
    return f"{prefix}_{uuid.uuid4().hex[:12]}"


@dataclass
class StorageRecordDescriptor:
    record_id: str
    record_type: StorageRecordType = StorageRecordType.UNKNOWN
    scope: StorageScope = StorageScope.UNKNOWN
    mutability: StorageMutability = StorageMutability.UNKNOWN
    source: StorageSource = StorageSource.UNKNOWN
    owner_id: str = ""
    session_id: str = ""
    backend_type: StorageBackendType = StorageBackendType.UNKNOWN
    storage_path: str = ""
    created_at: str = ""
    updated_at: str = ""
    version: str = ""
    confidence: float = 0.5
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "record_id": self.record_id,
            "record_type": self.record_type.value,
            "scope": self.scope.value,
            "mutability": self.mutability.value,
            "source": self.source.value,
            "owner_id": self.owner_id,
            "session_id": self.session_id,
            "backend_type": self.backend_type.value,
            "storage_path": self.storage_path,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "version": self.version,
            "confidence": self.confidence,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> StorageRecordDescriptor:
        return cls(
            record_id=data.get("record_id", _storage_id()),
            record_type=normalize_storage_record_type(data.get("record_type", "unknown")),
            scope=normalize_storage_scope(data.get("scope", "unknown")),
            mutability=normalize_storage_mutability(data.get("mutability", "unknown")),
            source=normalize_storage_source(data.get("source", "unknown")),
            owner_id=data.get("owner_id", ""),
            session_id=data.get("session_id", ""),
            backend_type=normalize_backend_type(data.get("backend_type", "unknown")),
            storage_path=data.get("storage_path", ""),
            created_at=data.get("created_at", ""),
            updated_at=data.get("updated_at", ""),
            version=data.get("version", ""),
            confidence=clamp_confidence(data.get("confidence", 0.5)),
            metadata=data.get("metadata", {}),
        )


@dataclass
class StorageWriteRequest:
    request_id: str
    descriptor: StorageRecordDescriptor
    operation: StorageOperation = StorageOperation.WRITE
    payload: Any = None
    reason: str = ""
    authority_context: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "request_id": self.request_id,
            "descriptor": self.descriptor.to_dict(),
            "operation": self.operation.value,
            "payload": self.payload
            if isinstance(self.payload, (dict, list, str, int, float, bool, type(None)))
            else str(self.payload),
            "reason": self.reason,
            "authority_context": self.authority_context,
            "metadata": self.metadata,
        }


@dataclass
class StorageWriteResult:
    request_id: str
    allowed: bool = False
    status: str = ""
    descriptor: StorageRecordDescriptor | None = None
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "request_id": self.request_id,
            "allowed": self.allowed,
            "status": self.status,
            "descriptor": self.descriptor.to_dict() if self.descriptor else None,
            "errors": self.errors,
            "warnings": self.warnings,
            "metadata": self.metadata,
        }


_MAX_READ_LIMIT = 500


@dataclass
class StorageReadRequest:
    request_id: str
    record_type: StorageRecordType | None = None
    record_id: str = ""
    owner_id: str = ""
    session_id: str = ""
    scope: StorageScope | None = None
    limit: int = 50
    include_payload: bool = False
    metadata: dict[str, Any] = field(default_factory=dict)

    def effective_limit(self) -> int:
        return max(1, min(self.limit, _MAX_READ_LIMIT))

    def to_dict(self) -> dict[str, Any]:
        return {
            "request_id": self.request_id,
            "record_type": self.record_type.value if self.record_type else None,
            "record_id": self.record_id,
            "owner_id": self.owner_id,
            "session_id": self.session_id,
            "scope": self.scope.value if self.scope else None,
            "limit": self.limit,
            "include_payload": self.include_payload,
            "metadata": self.metadata,
        }


@dataclass
class StorageReadResult:
    request_id: str
    records: list[StorageRecordDescriptor] = field(default_factory=list)
    total_returned: int = 0
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "request_id": self.request_id,
            "records": [r.to_dict() for r in self.records],
            "total_returned": self.total_returned,
            "errors": self.errors,
            "warnings": self.warnings,
            "metadata": self.metadata,
        }
