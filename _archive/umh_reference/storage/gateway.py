"""Phase 82 storage gateway — disciplined wrapper for storage operations.

Enforces StoragePolicy before any write. Does not replace existing stores;
wraps and coordinates where possible.

No execution. No adapter calls. No LLM calls.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from typing import Any

from umh.core.clock import iso_now as _iso_now
from umh.storage.contracts import (
    StorageBackendType,
    StorageMutability,
    StorageOperation,
    StorageReadRequest,
    StorageReadResult,
    StorageRecordDescriptor,
    StorageRecordType,
    StorageWriteRequest,
    StorageWriteResult,
)
from umh.storage.policy import (
    StoragePolicy,
    build_default_storage_policy,
    classify_record_mutability,
    evaluate_storage_operation,
)


class InMemoryStorageBackend:
    """Append-safe in-memory backend for tests and bootstrapping."""

    def __init__(self) -> None:
        self._records: list[dict[str, Any]] = []
        self._descriptors: list[StorageRecordDescriptor] = []

    def append(self, descriptor: StorageRecordDescriptor, payload: Any = None) -> None:
        self._descriptors.append(descriptor)
        self._records.append({"descriptor": descriptor, "payload": payload})

    def update(self, descriptor: StorageRecordDescriptor, payload: Any = None) -> bool:
        for rec in self._records:
            if rec["descriptor"].record_id == descriptor.record_id:
                rec["payload"] = payload
                rec["descriptor"] = descriptor
                return True
        return False

    def read(self, record_id: str) -> dict[str, Any] | None:
        for rec in self._records:
            if rec["descriptor"].record_id == record_id:
                return rec
        return None

    def list_descriptors(
        self,
        record_type: StorageRecordType | None = None,
        owner_id: str = "",
        limit: int = 50,
    ) -> list[StorageRecordDescriptor]:
        results: list[StorageRecordDescriptor] = []
        for rec in self._records:
            d = rec["descriptor"]
            if record_type is not None and d.record_type != record_type:
                continue
            if owner_id and d.owner_id != owner_id:
                continue
            results.append(d)
            if len(results) >= limit:
                break
        return results


def _request_id() -> str:
    return f"swreq_{uuid.uuid4().hex[:10]}"


@dataclass
class StorageGateway:
    """Disciplined storage gateway enforcing policy on all write paths."""

    policy: StoragePolicy = field(default_factory=build_default_storage_policy)
    backends: dict[str, Any] = field(default_factory=dict)
    _default_backend: InMemoryStorageBackend = field(default_factory=InMemoryStorageBackend)
    _audit_log: list[dict[str, Any]] = field(default_factory=list)

    def register_backend(
        self,
        name: str,
        backend: Any,
        backend_type: StorageBackendType = StorageBackendType.UNKNOWN,
    ) -> None:
        self.backends[name] = {"backend": backend, "type": backend_type}

    def _get_backend(self, descriptor: StorageRecordDescriptor) -> Any:
        bt = (
            descriptor.backend_type.value
            if descriptor.backend_type != StorageBackendType.UNKNOWN
            else ""
        )
        if bt and bt in self.backends:
            return self.backends[bt]["backend"]
        if descriptor.record_type.value in self.backends:
            return self.backends[descriptor.record_type.value]["backend"]
        return self._default_backend

    def describe_record(
        self,
        record_id: str,
        record_type: StorageRecordType | None = None,
        owner_id: str = "",
    ) -> StorageRecordDescriptor | None:
        backend = self._default_backend
        rec = backend.read(record_id)
        if rec:
            return rec["descriptor"]
        for name, entry in self.backends.items():
            b = entry["backend"]
            if hasattr(b, "read"):
                r = b.read(record_id)
                if r and isinstance(r, dict) and "descriptor" in r:
                    return r["descriptor"]
        return None

    def read(self, request: StorageReadRequest) -> StorageReadResult:
        if request.record_id:
            desc = self.describe_record(request.record_id)
            if desc:
                return StorageReadResult(
                    request_id=request.request_id,
                    records=[desc],
                    total_returned=1,
                )
            return StorageReadResult(
                request_id=request.request_id,
                records=[],
                total_returned=0,
                warnings=["Record not found"],
            )

        backend = self._default_backend
        descs = backend.list_descriptors(
            record_type=request.record_type,
            owner_id=request.owner_id,
            limit=request.effective_limit(),
        )
        return StorageReadResult(
            request_id=request.request_id,
            records=descs,
            total_returned=len(descs),
        )

    def write(self, request: StorageWriteRequest) -> StorageWriteResult:
        decision = evaluate_storage_operation(request.descriptor, request.operation, self.policy)

        self._audit_log.append(
            {
                "timestamp": _iso_now(),
                "request_id": request.request_id,
                "operation": request.operation.value,
                "record_type": request.descriptor.record_type.value,
                "allowed": decision.allowed,
                "reason": decision.reason,
            }
        )

        if not decision.allowed:
            return StorageWriteResult(
                request_id=request.request_id,
                allowed=False,
                status="denied",
                descriptor=request.descriptor,
                errors=[decision.reason],
                warnings=decision.warnings,
            )

        backend = self._get_backend(request.descriptor)
        now = _iso_now()
        request.descriptor.updated_at = now
        if not request.descriptor.created_at:
            request.descriptor.created_at = now

        try:
            if request.operation in (StorageOperation.APPEND, StorageOperation.WRITE):
                if hasattr(backend, "append"):
                    backend.append(request.descriptor, request.payload)
                elif hasattr(backend, "put"):
                    backend.put(request.descriptor.record_id, request.payload)
            elif request.operation == StorageOperation.UPDATE:
                if hasattr(backend, "update"):
                    backend.update(request.descriptor, request.payload)
                elif hasattr(backend, "put"):
                    backend.put(request.descriptor.record_id, request.payload)
        except Exception as e:
            return StorageWriteResult(
                request_id=request.request_id,
                allowed=True,
                status="error",
                descriptor=request.descriptor,
                errors=[f"Backend write failed: {str(e)[:200]}"],
            )

        return StorageWriteResult(
            request_id=request.request_id,
            allowed=True,
            status="written",
            descriptor=request.descriptor,
            warnings=decision.warnings,
        )

    def append(
        self,
        descriptor: StorageRecordDescriptor,
        payload: Any = None,
        reason: str = "",
        metadata: dict[str, Any] | None = None,
    ) -> StorageWriteResult:
        return self.write(
            StorageWriteRequest(
                request_id=_request_id(),
                descriptor=descriptor,
                operation=StorageOperation.APPEND,
                payload=payload,
                reason=reason,
                metadata=metadata or {},
            )
        )

    def update(
        self,
        descriptor: StorageRecordDescriptor,
        payload: Any = None,
        reason: str = "",
        metadata: dict[str, Any] | None = None,
    ) -> StorageWriteResult:
        return self.write(
            StorageWriteRequest(
                request_id=_request_id(),
                descriptor=descriptor,
                operation=StorageOperation.UPDATE,
                payload=payload,
                reason=reason,
                metadata=metadata or {},
            )
        )

    def promote(
        self,
        descriptor: StorageRecordDescriptor,
        payload: Any = None,
        reason: str = "",
        metadata: dict[str, Any] | None = None,
    ) -> StorageWriteResult:
        return self.write(
            StorageWriteRequest(
                request_id=_request_id(),
                descriptor=descriptor,
                operation=StorageOperation.PROMOTE,
                payload=payload,
                reason=reason,
                metadata=metadata or {},
            )
        )

    def list_descriptors(
        self,
        record_type: StorageRecordType | None = None,
        owner_id: str = "",
        limit: int = 50,
    ) -> list[StorageRecordDescriptor]:
        capped = max(1, min(limit, 500))
        return self._default_backend.list_descriptors(record_type, owner_id, capped)

    def audit(self) -> list[dict[str, Any]]:
        return list(self._audit_log)

    def to_dict(self) -> dict[str, Any]:
        return {
            "backend_count": len(self.backends) + 1,
            "registered_backends": sorted(self.backends.keys()),
            "default_record_count": len(self._default_backend._records),
            "audit_log_count": len(self._audit_log),
            "policy": self.policy.to_dict(),
        }
