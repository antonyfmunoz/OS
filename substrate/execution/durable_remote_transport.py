"""Durable request/result transport for remote node operations.

This module is intentionally small and file-backed.  It gives Wave 2 a
production primitive whose truth is not an in-memory WebSocket future:
controller requests are persisted before delivery, nodes claim them
idempotently, terminal results are atomically published, and cancellation
intent survives temporary transport loss.
"""

from __future__ import annotations

import hashlib
import json
import os
import time
from contextlib import contextmanager
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterator
from uuid import uuid4

from substrate.execution.mesh_verdict import (
    CONSEQUENTIAL_WRITE_EFFECT,
    canonical_sync_effect_policy,
)

TERMINAL_STATES = frozenset({"SUCCEEDED", "FAILED", "CANCELLED", "EXPIRED"})
ACTIVE_STATES = frozenset({"QUEUED", "CLAIMED", "RUNNING", "CANCEL_REQUESTED"})
RECOVERY_STATES = frozenset({"RECONCILIATION_REQUIRED"})
STATE_ORDER = {
    "QUEUED": 0,
    "CLAIMED": 1,
    "RUNNING": 2,
    "CANCEL_REQUESTED": 3,
    "RECONCILIATION_REQUIRED": 4,
    "EXPIRED": 5,
    "FAILED": 5,
    "CANCELLED": 5,
    "SUCCEEDED": 5,
}


def _request_budget(
    req: "DurableRemoteRequest",
    key: str,
    default: float,
    *,
    minimum: float = 0.0,
    maximum: float = 3600.0,
) -> float:
    budgets = req.params.get("budgets") if isinstance(req.params, dict) else {}
    raw = budgets.get(key, default) if isinstance(budgets, dict) else default
    try:
        value = float(raw)
    except (TypeError, ValueError):
        value = default
    return max(minimum, min(value, maximum))


def default_controller_root() -> Path:
    return Path(os.environ.get("UMH_DURABLE_REMOTE_ROOT", "/var/lib/umh/durable_remote"))


def default_node_root() -> Path:
    if os.name == "nt":
        return Path(os.environ.get("PROGRAMDATA", r"C:\ProgramData")) / "UMH" / "durable_remote"
    return Path(os.environ.get("UMH_NODE_DURABLE_REMOTE_ROOT", "/var/lib/umh/node_durable_remote"))


def now_s() -> float:
    return time.time()


def sha256_json(value: Any) -> str:
    blob = json.dumps(value, sort_keys=True, separators=(",", ":"), default=str).encode()
    return hashlib.sha256(blob).hexdigest()


def _normalized_idempotency_key(value: str) -> str:
    return str(value or "").strip()


def _logical_payload_params(params: dict[str, Any]) -> dict[str, Any]:
    logical_params = dict(params)
    logical_params.pop("governance_verdict_id", None)
    return logical_params


def _request_payload_digest(
    *,
    operation_type: str,
    capability: str,
    params: dict[str, Any],
    candidate_sha: str,
    authority_id: str,
) -> str:
    return sha256_json(
        {
            "operation_type": operation_type,
            "capability": capability,
            "params": _logical_payload_params(params),
            "candidate_sha": candidate_sha,
            "authority_id": authority_id,
        }
    )


_IDEMPOTENCY_IDENTITY_FIELDS = (
    "idempotency_key",
    "candidate_sha",
    "node_id",
    "capability",
    "operation_type",
    "risk_class",
    "authority_id",
    "payload_digest",
)


def _atomic_write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + f".tmp-{uuid4().hex}")
    tmp.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    tmp.replace(path)


def _read_json(path: Path) -> dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return {}
    if not isinstance(data, dict):
        return {}
    return data


@dataclass
class DurableRemoteRequest:
    request_id: str
    correlation_id: str
    candidate_sha: str
    node_id: str
    operation_type: str
    capability: str
    params: dict[str, Any]
    risk_class: str = "reversible_write"
    authority_id: str = ""
    idempotency_key: str = ""
    attempt: int = 1
    created_at: float = field(default_factory=now_s)
    expires_at: float = 0.0
    payload_digest: str = ""
    lifecycle_state: str = "QUEUED"
    delivered_at: float = 0.0
    delivery_attempts: int = 0
    claim_id: str = ""
    lease_expires_at: float = 0.0
    process_tree: dict[str, Any] = field(default_factory=dict)
    result_digest: str = ""
    cancellation_requested_at: float = 0.0
    cancellation_deadline_at: float = 0.0
    cancellation_acknowledged_at: float = 0.0
    reconciliation_requested_at: float = 0.0
    reconciliation_deadline_at: float = 0.0
    terminalized_at: float = 0.0
    updated_at: float = 0.0
    cleanup: dict[str, Any] = field(default_factory=dict)
    diagnostics: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.payload_digest:
            self.payload_digest = _request_payload_digest(
                operation_type=self.operation_type,
                capability=self.capability,
                params=self.params,
                candidate_sha=self.candidate_sha,
                authority_id=self.authority_id,
            )
        normalized_key = _normalized_idempotency_key(self.idempotency_key)
        self.idempotency_key = normalized_key

    def to_dict(self) -> dict[str, Any]:
        return {
            "request_id": self.request_id,
            "correlation_id": self.correlation_id,
            "candidate_sha": self.candidate_sha,
            "node_id": self.node_id,
            "operation_type": self.operation_type,
            "capability": self.capability,
            "params": self.params,
            "risk_class": self.risk_class,
            "authority_id": self.authority_id,
            "idempotency_key": self.idempotency_key,
            "attempt": self.attempt,
            "created_at": self.created_at,
            "expires_at": self.expires_at,
            "payload_digest": self.payload_digest,
            "lifecycle_state": self.lifecycle_state,
            "delivered_at": self.delivered_at,
            "delivery_attempts": self.delivery_attempts,
            "claim_id": self.claim_id,
            "lease_expires_at": self.lease_expires_at,
            "process_tree": self.process_tree,
            "result_digest": self.result_digest,
            "cancellation_requested_at": self.cancellation_requested_at,
            "cancellation_deadline_at": self.cancellation_deadline_at,
            "cancellation_acknowledged_at": self.cancellation_acknowledged_at,
            "reconciliation_requested_at": self.reconciliation_requested_at,
            "reconciliation_deadline_at": self.reconciliation_deadline_at,
            "terminalized_at": self.terminalized_at,
            "updated_at": self.updated_at,
            "cleanup": self.cleanup,
            "diagnostics": self.diagnostics,
        }

    def cancellation_identity(self, *, claim_id: str | None = None) -> dict[str, Any]:
        identity = {
            "request_id": self.request_id,
            "correlation_id": self.correlation_id,
            "node_id": self.node_id,
            "claim_id": claim_id if claim_id is not None else self.claim_id,
            "cancellation_generation": self.cancellation_requested_at,
            "cancellation_requested_at": self.cancellation_requested_at,
            "cancellation_deadline_at": self.cancellation_deadline_at,
        }
        identity["cancellation_envelope_digest"] = sha256_json(identity)
        return identity

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "DurableRemoteRequest":
        return cls(
            request_id=str(data.get("request_id", "")),
            correlation_id=str(data.get("correlation_id", "")),
            candidate_sha=str(data.get("candidate_sha", "")),
            node_id=str(data.get("node_id", "")),
            operation_type=str(data.get("operation_type", "")),
            capability=str(data.get("capability", "")),
            params=dict(data.get("params") or {}),
            risk_class=str(data.get("risk_class", "reversible_write")),
            authority_id=str(data.get("authority_id", "")),
            idempotency_key=str(data.get("idempotency_key", "")),
            attempt=int(data.get("attempt", 1) or 1),
            created_at=float(data.get("created_at", 0.0) or 0.0),
            expires_at=float(data.get("expires_at", 0.0) or 0.0),
            payload_digest=str(data.get("payload_digest", "")),
            lifecycle_state=str(data.get("lifecycle_state", "QUEUED")),
            delivered_at=float(data.get("delivered_at", 0.0) or 0.0),
            delivery_attempts=int(data.get("delivery_attempts", 0) or 0),
            claim_id=str(data.get("claim_id", "")),
            lease_expires_at=float(data.get("lease_expires_at", 0.0) or 0.0),
            process_tree=dict(data.get("process_tree") or {}),
            result_digest=str(data.get("result_digest", "")),
            cancellation_requested_at=float(data.get("cancellation_requested_at", 0.0) or 0.0),
            cancellation_deadline_at=float(data.get("cancellation_deadline_at", 0.0) or 0.0),
            cancellation_acknowledged_at=float(data.get("cancellation_acknowledged_at", 0.0) or 0.0),
            reconciliation_requested_at=float(data.get("reconciliation_requested_at", 0.0) or 0.0),
            reconciliation_deadline_at=float(data.get("reconciliation_deadline_at", 0.0) or 0.0),
            terminalized_at=float(data.get("terminalized_at", 0.0) or 0.0),
            updated_at=float(data.get("updated_at", 0.0) or 0.0),
            cleanup=dict(data.get("cleanup") or {}),
            diagnostics=dict(data.get("diagnostics") or {}),
        )


class DurableRemoteStore:
    """File-backed canonical store for one controller or node spool."""

    def __init__(self, root: Path | str | None = None) -> None:
        self.root = Path(root) if root is not None else default_controller_root()
        self.requests_dir = self.root / "requests"
        self.results_dir = self.root / "results"
        self.idempotency_dir = self.root / "idempotency"
        self.events_path = self.root / "events.jsonl"
        self.requests_dir.mkdir(parents=True, exist_ok=True)
        self.results_dir.mkdir(parents=True, exist_ok=True)
        self.idempotency_dir.mkdir(parents=True, exist_ok=True)

    def _request_path(self, request_id: str) -> Path:
        return self.requests_dir / f"{request_id}.json"

    def _result_path(self, request_id: str) -> Path:
        return self.results_dir / f"{request_id}.json"

    def _rejected_result_path(self, request_id: str, digest: str) -> Path:
        return self.results_dir / f"{request_id}.rejected-{digest[:16]}-{uuid4().hex[:8]}.json"

    def _lock_path(self, request_id: str) -> Path:
        return self.root / "locks" / f"{request_id}.lock"

    def _idempotency_index_path(self, idempotency_key: str) -> Path:
        return self.idempotency_dir / f"{hashlib.sha256(idempotency_key.encode()).hexdigest()}.json"

    def _idempotency_lock_path(self, idempotency_key: str) -> Path:
        return (
            self.root
            / "locks"
            / f"idempotency-{hashlib.sha256(idempotency_key.encode()).hexdigest()}.lock"
        )

    def _lock_owner_pid(self, lock_path: Path) -> int | None:
        try:
            raw = lock_path.read_text(encoding="ascii").split(maxsplit=1)[0]
            pid = int(raw)
        except (FileNotFoundError, IndexError, UnicodeDecodeError, ValueError):
            return None
        return pid if pid > 0 else None

    def _lock_owner_alive(self, pid: int | None) -> bool:
        if pid is None:
            return True
        try:
            os.kill(pid, 0)
        except ProcessLookupError:
            return False
        except PermissionError:
            return True
        return True

    @contextmanager
    def _file_lock(
        self,
        lock_path: Path,
        *,
        label: str,
        timeout_s: float = 10.0,
        break_stale_owner: bool = True,
    ) -> Iterator[None]:
        lock_path.parent.mkdir(parents=True, exist_ok=True)
        deadline = now_s() + timeout_s
        acquired = False
        while not acquired:
            tmp_path = lock_path.with_name(f".{lock_path.name}.tmp-{uuid4().hex}")
            try:
                fd = os.open(str(tmp_path), os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
                try:
                    os.write(fd, f"{os.getpid()} {now_s()}\n".encode("ascii"))
                    os.fsync(fd)
                finally:
                    os.close(fd)
                os.link(tmp_path, lock_path)
                acquired = True
            except FileExistsError:
                try:
                    owner_pid = self._lock_owner_pid(lock_path)
                    owner_alive = self._lock_owner_alive(owner_pid)
                    is_old = now_s() - lock_path.stat().st_mtime > timeout_s
                    if not owner_alive or (break_stale_owner and owner_pid is None and is_old):
                        lock_path.unlink()
                        continue
                except FileNotFoundError:
                    continue
                if now_s() >= deadline:
                    raise TimeoutError(f"timed out acquiring durable lock: {label}")
                time.sleep(0.05)
            finally:
                try:
                    tmp_path.unlink()
                except FileNotFoundError:
                    pass
        try:
            yield
        finally:
            try:
                lock_path.unlink()
            except FileNotFoundError:
                pass

    @contextmanager
    def _request_lock(self, request_id: str, *, timeout_s: float = 10.0) -> Iterator[None]:
        with self._file_lock(
            self._lock_path(request_id),
            label=f"request:{request_id}",
            timeout_s=timeout_s,
        ):
            yield

    @contextmanager
    def _idempotency_lock(
        self, idempotency_key: str, *, timeout_s: float = 10.0
    ) -> Iterator[None]:
        with self._file_lock(
            self._idempotency_lock_path(idempotency_key),
            label=f"idempotency:{hashlib.sha256(idempotency_key.encode()).hexdigest()}",
            timeout_s=timeout_s,
            break_stale_owner=True,
        ):
            yield

    def _event(self, request_id: str, event: str, data: dict[str, Any] | None = None) -> None:
        self.events_path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "ts": now_s(),
            "request_id": request_id,
            "event": event,
            "data": data or {},
        }
        with self.events_path.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(payload, sort_keys=True) + "\n")

    def _idempotency_binding(self, request: DurableRemoteRequest) -> dict[str, Any]:
        return {
            "version": 1,
            "idempotency_scope": "durable_remote_store",
            "idempotency_key": request.idempotency_key,
            "canonical_request_id": request.request_id,
            "correlation_id": request.correlation_id,
            "candidate_sha": request.candidate_sha,
            "node_id": request.node_id,
            "capability": request.capability,
            "operation_type": request.operation_type,
            "risk_class": request.risk_class,
            "authority_id": request.authority_id,
            "effect_class": CONSEQUENTIAL_WRITE_EFFECT,
            "payload_digest": request.payload_digest,
            "created_at": request.created_at,
            "lifecycle_state": request.lifecycle_state,
        }

    def _canonicalize_request_payload_identity(self, request: DurableRemoteRequest) -> None:
        computed = _request_payload_digest(
            operation_type=request.operation_type,
            capability=request.capability,
            params=request.params,
            candidate_sha=request.candidate_sha,
            authority_id=request.authority_id,
        )
        if request.payload_digest and request.payload_digest != computed:
            request.diagnostics.setdefault("incoming_payload_digest_mismatch", []).append(
                {
                    "supplied_payload_digest": request.payload_digest,
                    "computed_payload_digest": computed,
                }
            )
        request.payload_digest = computed

    def _write_idempotency_index(self, request: DurableRemoteRequest) -> None:
        if not request.idempotency_key:
            return
        existing = _read_json(self._idempotency_index_path(request.idempotency_key))
        existing_request_id = str(existing.get("canonical_request_id", "")) if existing else ""
        if existing_request_id and existing_request_id != request.request_id:
            raise ValueError("idempotency index canonical request mismatch")
        _atomic_write_json(
            self._idempotency_index_path(request.idempotency_key),
            self._idempotency_binding(request),
        )

    def _validate_idempotent_replay(
        self,
        existing: DurableRemoteRequest,
        incoming: DurableRemoteRequest,
    ) -> None:
        self._canonicalize_request_payload_identity(existing)
        self._canonicalize_request_payload_identity(incoming)
        for field_name in _IDEMPOTENCY_IDENTITY_FIELDS:
            if getattr(existing, field_name) != getattr(incoming, field_name):
                raise ValueError(
                    f"idempotency conflict: {field_name} differs for key "
                    f"{incoming.idempotency_key}"
                )

    @staticmethod
    def _strip_noncanonical_authority_fields(req: DurableRemoteRequest) -> None:
        req.claim_id = ""
        req.lease_expires_at = 0.0
        req.process_tree = {}

    @staticmethod
    def _request_sort_key(req: DurableRemoteRequest) -> tuple[float, str]:
        return (float(req.created_at or 0.0), req.request_id)

    def _immutable_request_mutation_fields(
        self,
        current: DurableRemoteRequest,
        incoming: DurableRemoteRequest,
    ) -> list[str]:
        mismatched = [
            field_name
            for field_name in _IDEMPOTENCY_IDENTITY_FIELDS
            if getattr(current, field_name) != getattr(incoming, field_name)
        ]
        if current.params != incoming.params:
            mismatched.append("params")
        current_verdict_digest = current.diagnostics.get("verdict_payload_digest")
        incoming_verdict_digest = incoming.diagnostics.get("verdict_payload_digest")
        if current_verdict_digest != incoming_verdict_digest:
            mismatched.append("diagnostics.verdict_payload_digest")
        return mismatched

    def _quarantine_duplicate_idempotency_record_locked(
        self, duplicate: DurableRemoteRequest, *, canonical_request_id: str
    ) -> None:
        if duplicate.request_id == canonical_request_id:
            return
        with self._request_lock(duplicate.request_id):
            current = self._get_request_raw(duplicate.request_id)
            if current is None:
                return
            current.diagnostics.setdefault(
                "duplicate_idempotency_noncanonical",
                {
                    "canonical_request_id": canonical_request_id,
                    "detected_at": now_s(),
                },
            )
            self._strip_noncanonical_authority_fields(current)
            if current.lifecycle_state in {"QUEUED", "DELIVERED", "CLAIMED", "RUNNING", "CANCEL_REQUESTED"}:
                current.lifecycle_state = "RECONCILIATION_REQUIRED"
                current.diagnostics.setdefault("reconciliation_reasons", []).append(
                    "duplicate_idempotency_noncanonical"
                )
                if not current.reconciliation_requested_at:
                    current.reconciliation_requested_at = now_s()
                current.reconciliation_deadline_at = max(
                    current.reconciliation_deadline_at,
                    current.reconciliation_requested_at + 15.0,
                )
                self._update_request_locked(
                    current,
                    "DUPLICATE_IDEMPOTENCY_QUARANTINED",
                    write_idempotency_index=False,
                )
            else:
                self._update_request_locked(current, "", write_idempotency_index=False)

    def _mark_noncanonical_request_locked(
        self,
        req: DurableRemoteRequest,
        *,
        canonical_request_id: str,
        event: str,
    ) -> DurableRemoteRequest:
        req.diagnostics.setdefault(
            "duplicate_idempotency_noncanonical",
            {
                "canonical_request_id": canonical_request_id,
                "detected_at": now_s(),
            },
        )
        req.diagnostics.setdefault("noncanonical_event_rejected", []).append(
            {"event": event, "observed_at": now_s()}
        )
        self._strip_noncanonical_authority_fields(req)
        if req.lifecycle_state in {"QUEUED", "DELIVERED", "CLAIMED", "RUNNING", "CANCEL_REQUESTED"}:
            req.lifecycle_state = "RECONCILIATION_REQUIRED"
            req.diagnostics.setdefault("reconciliation_reasons", []).append(
                "duplicate_idempotency_noncanonical"
            )
            if not req.reconciliation_requested_at:
                req.reconciliation_requested_at = now_s()
            req.reconciliation_deadline_at = max(
                req.reconciliation_deadline_at,
                req.reconciliation_requested_at + 15.0,
            )
        self._update_request_locked(
            req,
            "NONCANONICAL_IDEMPOTENCY_EVENT_REJECTED",
            write_idempotency_index=False,
        )
        return req

    def _mark_missing_idempotency_key_locked(
        self, req: DurableRemoteRequest, *, event: str
    ) -> DurableRemoteRequest:
        req.diagnostics.setdefault(
            "missing_idempotency_key_rejected",
            {"event": event, "observed_at": now_s()},
        )
        req.diagnostics.setdefault("noncanonical_event_rejected", []).append(
            {"event": event, "observed_at": now_s()}
        )
        self._strip_noncanonical_authority_fields(req)
        if req.lifecycle_state in {"QUEUED", "DELIVERED", "CLAIMED", "RUNNING", "CANCEL_REQUESTED"}:
            req.lifecycle_state = "RECONCILIATION_REQUIRED"
            req.diagnostics.setdefault("reconciliation_reasons", []).append(
                "missing_idempotency_key"
            )
            if not req.reconciliation_requested_at:
                req.reconciliation_requested_at = now_s()
            req.reconciliation_deadline_at = max(
                req.reconciliation_deadline_at,
                req.reconciliation_requested_at + 15.0,
            )
        self._update_request_locked(
            req,
            "MISSING_IDEMPOTENCY_KEY_REJECTED",
            write_idempotency_index=False,
        )
        return req

    def _reject_noncanonical_update_locked(
        self, req: DurableRemoteRequest, *, event: str
    ) -> DurableRemoteRequest | None:
        if not req.idempotency_key:
            return self._mark_missing_idempotency_key_locked(req, event=event)
        index = _read_json(self._idempotency_index_path(req.idempotency_key))
        canonical_request_id = str(index.get("canonical_request_id", "")) if index else ""
        if not canonical_request_id:
            matches: list[DurableRemoteRequest] = []
            for path in sorted(self.requests_dir.glob("*.json")):
                data = _read_json(path)
                if not data:
                    continue
                candidate = DurableRemoteRequest.from_dict(data)
                if candidate.idempotency_key == req.idempotency_key:
                    matches.append(candidate)
            if matches:
                if len(matches) > 1:
                    return self._mark_noncanonical_request_locked(
                        req,
                        canonical_request_id="ambiguous_idempotency_recovery",
                        event=event,
                    )
                recovered = matches[0]
                canonical_request_id = recovered.request_id
                self._write_idempotency_index(recovered)
        if canonical_request_id and canonical_request_id != req.request_id:
            return self._mark_noncanonical_request_locked(
                req,
                canonical_request_id=canonical_request_id,
                event=event,
            )
        return None

    def _find_request_by_idempotency_key_locked(
        self, idempotency_key: str
    ) -> DurableRemoteRequest | None:
        matches = self._requests_by_idempotency_key_locked(idempotency_key)
        if not matches:
            return None
        if len(matches) > 1:
            self._fail_ambiguous_idempotency_recovery_locked(
                matches,
                event="AMBIGUOUS_IDEMPOTENCY_RECOVERY_REJECTED",
            )
            raise ValueError("ambiguous idempotency recovery: multiple request records")
        canonical = matches[0]
        return canonical

    def _requests_by_idempotency_key_locked(
        self, idempotency_key: str
    ) -> list[DurableRemoteRequest]:
        matches: list[DurableRemoteRequest] = []
        for path in sorted(self.requests_dir.glob("*.json")):
            data = _read_json(path)
            if not data:
                continue
            req = DurableRemoteRequest.from_dict(data)
            if req.idempotency_key == idempotency_key:
                matches.append(req)
        matches.sort(key=self._request_sort_key)
        return matches

    def _fail_ambiguous_idempotency_recovery_locked(
        self,
        matches: list[DurableRemoteRequest],
        *,
        event: str,
    ) -> None:
        detected_at = now_s()
        request_ids = sorted(req.request_id for req in matches)
        for duplicate in matches:
            duplicate.diagnostics.setdefault(
                "ambiguous_idempotency_recovery",
                {
                    "request_ids": request_ids,
                    "detected_at": detected_at,
                },
            )
            self._mark_noncanonical_request_locked(
                duplicate,
                canonical_request_id="ambiguous_idempotency_recovery",
                event=event,
            )

    def _quarantine_noncanonical_idempotency_records_locked(
        self, idempotency_key: str, *, canonical_request_id: str
    ) -> None:
        for path in sorted(self.requests_dir.glob("*.json")):
            if path.stem == canonical_request_id:
                continue
            data = _read_json(path)
            if not data:
                continue
            duplicate = DurableRemoteRequest.from_dict(data)
            if duplicate.idempotency_key != idempotency_key:
                continue
            self._quarantine_duplicate_idempotency_record_locked(
                duplicate,
                canonical_request_id=canonical_request_id,
            )

    def _request_is_canonical_for_idempotency(self, req: DurableRemoteRequest) -> bool:
        if not req.idempotency_key:
            with self._request_lock(req.request_id):
                current = self._get_request_raw(req.request_id)
                if current is not None and not current.idempotency_key:
                    self._mark_missing_idempotency_key_locked(
                        current,
                        event="CANONICAL_IDEMPOTENCY_CHECK",
                    )
            return False
        with self._idempotency_lock(req.idempotency_key):
            index = _read_json(self._idempotency_index_path(req.idempotency_key))
            if index:
                canonical_request_id = str(index.get("canonical_request_id", ""))
                if not canonical_request_id:
                    raise ValueError("idempotency index missing canonical request id")
                matches = self._requests_by_idempotency_key_locked(req.idempotency_key)
                if matches and matches[0].request_id != canonical_request_id:
                    self._fail_ambiguous_idempotency_recovery_locked(
                        matches,
                        event="IDEMPOTENCY_INDEX_CONFLICT_REJECTED",
                    )
                    return False
                if canonical_request_id != req.request_id:
                    self._quarantine_duplicate_idempotency_record_locked(
                        req,
                        canonical_request_id=canonical_request_id,
                    )
                    return False
                return True
            try:
                recovered = self._find_request_by_idempotency_key_locked(req.idempotency_key)
            except ValueError as exc:
                if "ambiguous idempotency recovery" not in str(exc):
                    raise
                return False
            if recovered is None:
                return True
            with self._request_lock(recovered.request_id):
                current = self._get_request_raw(recovered.request_id) or recovered
                self._write_idempotency_index(current)
            return recovered.request_id == req.request_id

    def is_canonical_request(self, req: DurableRemoteRequest) -> bool:
        """Return whether ``req`` is the canonical request for its logical key."""
        return self._request_is_canonical_for_idempotency(req)

    def _record_idempotent_replay_locked(
        self,
        existing: DurableRemoteRequest,
        incoming: DurableRemoteRequest,
    ) -> DurableRemoteRequest:
        if existing.request_id == incoming.request_id:
            return existing
        replays = existing.diagnostics.setdefault("idempotent_replays", [])
        if not isinstance(replays, list):
            replays = []
            existing.diagnostics["idempotent_replays"] = replays
        replays.append(
            {
                "incoming_transport_request_id": incoming.request_id,
                "incoming_correlation_id": incoming.correlation_id,
                "payload_digest": incoming.payload_digest,
                "observed_at": now_s(),
                "disposition": "canonical_request_reused",
            }
        )
        if len(replays) > 20:
            del replays[: len(replays) - 20]
        self._update_request_locked(
            existing,
            "IDEMPOTENT_REPLAY",
            event_data={"incoming_request_id": incoming.request_id},
        )
        return existing

    def _existing_request_from_idempotency_index_locked(
        self, incoming: DurableRemoteRequest
    ) -> DurableRemoteRequest | None:
        index = _read_json(self._idempotency_index_path(incoming.idempotency_key))
        if not index:
            recovered = self._find_request_by_idempotency_key_locked(incoming.idempotency_key)
            if recovered is None:
                return None
            self._validate_idempotent_replay(recovered, incoming)
            with self._request_lock(recovered.request_id):
                current = self._get_request_raw(recovered.request_id) or recovered
                self._write_idempotency_index(current)
                result = self._record_idempotent_replay_locked(current, incoming)
            self._quarantine_noncanonical_idempotency_records_locked(
                incoming.idempotency_key,
                canonical_request_id=result.request_id,
            )
            return result
        canonical_request_id = str(index.get("canonical_request_id", ""))
        if not canonical_request_id:
            raise ValueError("idempotency index missing canonical request id")
        existing = self._get_request_raw(canonical_request_id)
        if existing is None:
            raise ValueError("idempotency index points to missing canonical request")
        matches = self._requests_by_idempotency_key_locked(incoming.idempotency_key)
        if matches and matches[0].request_id != canonical_request_id:
            self._fail_ambiguous_idempotency_recovery_locked(
                matches,
                event="IDEMPOTENCY_INDEX_CONFLICT_REJECTED",
            )
            raise ValueError("idempotency index conflicts with request records")
        self._validate_idempotent_replay(existing, incoming)
        with self._request_lock(existing.request_id):
            current = self._get_request_raw(existing.request_id)
            if current is None:
                raise ValueError("idempotency index points to missing canonical request")
            current = self._maybe_converge_recovery_locked(current)
            result = self._record_idempotent_replay_locked(current, incoming)
        self._quarantine_noncanonical_idempotency_records_locked(
            incoming.idempotency_key,
            canonical_request_id=result.request_id,
        )
        return result

    def put_request(self, request: DurableRemoteRequest) -> DurableRemoteRequest:
        self._canonicalize_request_payload_identity(request)
        request.idempotency_key = _normalized_idempotency_key(request.idempotency_key)
        if not request.idempotency_key:
            raise ValueError("consequential durable request requires idempotency_key")
        effect_policy = canonical_sync_effect_policy(
            request.capability,
            declared_effect_class=CONSEQUENTIAL_WRITE_EFFECT,
        )
        if effect_policy.authoritative_effect_class != CONSEQUENTIAL_WRITE_EFFECT:
            raise ValueError("durable request capability has no canonical consequential policy")
        with self._idempotency_lock(request.idempotency_key):
            existing_by_key = self._existing_request_from_idempotency_index_locked(request)
            if existing_by_key is not None:
                return existing_by_key
            with self._request_lock(request.request_id):
                existing = self._get_request_raw(request.request_id)
                if existing is not None:
                    self._validate_idempotent_replay(existing, request)
                    self._write_idempotency_index(existing)
                    return existing
                self._update_request_locked(
                    request,
                    "QUEUED",
                    event_data={
                        "node_id": request.node_id,
                        "idempotency_key": request.idempotency_key,
                    },
                )
                return request

    def _get_request_raw(self, request_id: str) -> DurableRemoteRequest | None:
        data = _read_json(self._request_path(request_id))
        if not data:
            return None
        return DurableRemoteRequest.from_dict(data)

    def get_request(self, request_id: str) -> DurableRemoteRequest | None:
        req = self._get_request_raw(request_id)
        if req is None:
            return None
        if (
            req.lifecycle_state not in TERMINAL_STATES
            and not self._recovery_due(req)
            and self.result_for(request_id) is None
        ):
            return req
        with self._request_lock(request_id):
            current = self._get_request_raw(request_id)
            if current is None:
                return None
            return self._maybe_converge_recovery_locked(current)

    def update_request(self, request: DurableRemoteRequest, event: str = "") -> None:
        with self._request_lock(request.request_id):
            current = self._get_request_raw(request.request_id)
            self._canonicalize_request_payload_identity(request)
            request.idempotency_key = _normalized_idempotency_key(request.idempotency_key)
            if not request.idempotency_key:
                raise ValueError("consequential durable request requires idempotency_key")
            noncanonical_probe = current or request
            self._canonicalize_request_payload_identity(noncanonical_probe)
            noncanonical = self._reject_noncanonical_update_locked(
                noncanonical_probe,
                event=event or "UPDATE_REQUEST",
            )
            if noncanonical is not None:
                return
            if current is None:
                raise KeyError(request.request_id)
            if current is not None:
                self._canonicalize_request_payload_identity(current)
                mismatched_identity = self._immutable_request_mutation_fields(current, request)
                if mismatched_identity:
                    current.diagnostics.setdefault("identity_mutation_rejected", []).append(
                        {
                            "fields": mismatched_identity,
                            "event": event,
                            "observed_at": now_s(),
                        }
                    )
                    self._update_request_locked(current, "IDENTITY_MUTATION_REJECTED")
                    return
            if current is not None and (
                current.lifecycle_state in TERMINAL_STATES
                or current.lifecycle_state in RECOVERY_STATES
                or STATE_ORDER.get(request.lifecycle_state, -1)
                < STATE_ORDER.get(current.lifecycle_state, -1)
                or bool(current.claim_id and request.claim_id != current.claim_id)
                or bool(not current.claim_id and request.claim_id)
            ):
                return
            self._update_request_locked(request, event)

    def record_transport_diagnostic(
        self,
        request_id: str,
        event: str,
        payload: dict[str, Any] | None = None,
        *,
        max_events: int = 40,
    ) -> DurableRemoteRequest | None:
        """Record bounded transport-coordination provenance.

        These diagnostics are evidence only. They do not advance lifecycle and
        they never establish claim or execution authority.
        """
        with self._request_lock(request_id):
            req = self._get_request_raw(request_id)
            if req is None:
                return None
            noncanonical = self._reject_noncanonical_update_locked(req, event=event)
            if noncanonical is not None:
                return noncanonical
            transport = req.diagnostics.setdefault("transport_control", {})
            if not isinstance(transport, dict):
                transport = {}
                req.diagnostics["transport_control"] = transport
            events = transport.setdefault("events", [])
            if not isinstance(events, list):
                events = []
                transport["events"] = events
            entry = {"event": event, "ts": now_s()}
            if payload:
                entry.update(payload)
            events.append(entry)
            if len(events) > max_events:
                del events[: len(events) - max_events]
            transport["last_event"] = event
            transport["last_event_at"] = entry["ts"]
            self._update_request_locked(req, "")
            return req

    def _update_request_locked(
        self,
        request: DurableRemoteRequest,
        event: str = "",
        *,
        event_data: dict[str, Any] | None = None,
        write_idempotency_index: bool = True,
    ) -> None:
        request.updated_at = now_s()
        if request.lifecycle_state in TERMINAL_STATES and not request.terminalized_at:
            request.terminalized_at = request.updated_at
        _atomic_write_json(self._request_path(request.request_id), request.to_dict())
        if write_idempotency_index:
            self._write_idempotency_index(request)
        if event:
            data = {"state": request.lifecycle_state}
            if event_data:
                data.update(event_data)
            self._event(request.request_id, event, data)

    def _has_process_residue_diagnostic(self, req: DurableRemoteRequest) -> bool:
        return bool(
            req.diagnostics.get("cancel_without_cleanup")
            or req.diagnostics.get("failed_without_cleanup")
            or req.diagnostics.get("success_without_cleanup")
            or req.diagnostics.get("terminal_cancel_cleanup_conflict")
            or req.cleanup.get("process_residue")
        )

    def _cancellation_ack_rejection_reason(
        self,
        req: DurableRemoteRequest,
        *,
        claim_id: str,
        cleanup: dict[str, Any] | None,
    ) -> str:
        if claim_id == "unclaimed" and req.diagnostics.get("cancelled_before_claim"):
            return ""
        if not req.cancellation_requested_at or not req.cancellation_deadline_at:
            return "cancel_ack_without_active_cancellation"
        if cleanup is None:
            return "cancel_ack_missing_cleanup"
        if cleanup.get("process_residue") != []:
            return "cancel_ack_without_zero_residue"
        expected = req.cancellation_identity(claim_id=claim_id)
        for key, value in expected.items():
            if cleanup.get(key) != value:
                return f"cancel_ack_identity_mismatch:{key}"
        return ""

    def _converge_existing_result_locked(
        self, req: DurableRemoteRequest
    ) -> DurableRemoteRequest:
        existing = self.result_for(req.request_id)
        if not existing:
            return req
        if req.lifecycle_state in RECOVERY_STATES and self._has_process_residue_diagnostic(req):
            return req
        state = str(existing.get("state", ""))
        if state not in TERMINAL_STATES:
            return req
        if existing.get("request_id") != req.request_id:
            return req
        if existing.get("correlation_id") != req.correlation_id:
            return req
        if existing.get("node_id") != req.node_id:
            return req
        if existing.get("candidate_sha") != req.candidate_sha:
            return req
        claim_id = str(existing.get("claim_id", ""))
        result = dict(existing.get("result") or {})
        cleanup = dict(existing.get("cleanup") or {})
        result_digest = sha256_json(
            {"state": state, "claim_id": claim_id, "result": result, "cleanup": cleanup}
        )
        cleanup_digest = sha256_json(cleanup)
        if existing.get("result_digest") != result_digest or existing.get(
            "cleanup_digest"
        ) != cleanup_digest:
            req.diagnostics.setdefault("terminal_result_digest_mismatch", []).append(
                {
                    "stored_result_digest": existing.get("result_digest", ""),
                    "expected_result_digest": result_digest,
                    "stored_cleanup_digest": existing.get("cleanup_digest", ""),
                    "expected_cleanup_digest": cleanup_digest,
                }
            )
            return self._enter_reconciliation(req, reason="terminal_result_digest_mismatch")
        if cleanup.get("process_residue"):
            reason_by_state = {
                "CANCELLED": "cancel_without_cleanup",
                "FAILED": "failed_without_cleanup",
                "SUCCEEDED": "success_without_cleanup",
            }
            reason = reason_by_state.get(state, "terminal_without_cleanup")
            req.cleanup = cleanup
            req.diagnostics[reason] = cleanup.get("process_residue")
            return self._enter_reconciliation(req, reason=reason)
        if (
            state == "CANCELLED"
            and claim_id == "unclaimed"
            and req.lifecycle_state == "QUEUED"
            and not req.claim_id
        ):
            req.claim_id = claim_id
            req.lifecycle_state = state
            req.result_digest = str(existing.get("result_digest", req.result_digest))
            req.cleanup = cleanup
            req.diagnostics.setdefault("recovered_terminal_result", True)
            req.diagnostics.setdefault("cancelled_before_claim", True)
            self._update_request_locked(req, "TERMINAL_RESULT_RECOVERED")
            return req
        if state == "CANCELLED":
            reason = self._cancellation_ack_rejection_reason(
                req,
                claim_id=claim_id,
                cleanup=cleanup,
            )
            if reason:
                req.cleanup = cleanup
                req.diagnostics.setdefault("cancel_ack_rejected", []).append(
                    {"reason": reason, "claim_id": claim_id}
                )
                return self._enter_reconciliation(req, reason=reason)
        if not claim_id or req.claim_id != claim_id:
            req.diagnostics.setdefault("unclaimed_terminal_result_ignored", []).append(
                {
                    "result_claim_id": claim_id,
                    "request_claim_id": req.claim_id,
                    "result_digest": existing.get("result_digest", ""),
                }
            )
            self._update_request_locked(req, "UNCLAIMED_TERMINAL_RESULT_IGNORED")
            return req
        if req.lifecycle_state in TERMINAL_STATES:
            return req
        req.lifecycle_state = state
        req.result_digest = str(existing.get("result_digest", req.result_digest))
        req.cleanup = dict(existing.get("cleanup") or {})
        req.diagnostics.setdefault("recovered_terminal_result", True)
        self._update_request_locked(req, "TERMINAL_RESULT_RECOVERED")
        return req

    def result_was_accepted(self, request_id: str, result_digest: str) -> bool:
        existing = self.result_for(request_id)
        return bool(existing and existing.get("result_digest") == result_digest)

    def _enter_reconciliation(
        self,
        req: DurableRemoteRequest,
        *,
        reason: str,
        deadline_seconds: float = 15.0,
    ) -> DurableRemoteRequest:
        req.lifecycle_state = "RECONCILIATION_REQUIRED"
        req.diagnostics.setdefault("reconciliation_reasons", []).append(reason)
        if not req.reconciliation_requested_at:
            req.reconciliation_requested_at = now_s()
        req.reconciliation_deadline_at = max(
            req.reconciliation_deadline_at,
            req.reconciliation_requested_at + max(0.0, deadline_seconds),
        )
        self._update_request_locked(req, "RECONCILIATION_REQUIRED")
        return req

    def _recovery_due(self, req: DurableRemoteRequest) -> bool:
        current = now_s()
        return (
            req.lifecycle_state == "CANCEL_REQUESTED"
            and req.cancellation_deadline_at
            and current >= req.cancellation_deadline_at
        ) or (
            req.lifecycle_state == "RECONCILIATION_REQUIRED"
            and req.reconciliation_deadline_at
            and current >= req.reconciliation_deadline_at
        )

    def _maybe_converge_recovery_locked(self, req: DurableRemoteRequest) -> DurableRemoteRequest:
        req = self._converge_existing_result_locked(req)
        current = now_s()
        if (
            req.lifecycle_state == "CANCEL_REQUESTED"
            and req.cancellation_deadline_at
            and current >= req.cancellation_deadline_at
        ):
            req = self._enter_reconciliation(
                req,
                reason="cancellation_ack_deadline_expired",
                deadline_seconds=_request_budget(
                    req,
                    "reconciliation_timeout_s",
                    15.0,
                    minimum=1.0,
                    maximum=300.0,
                ),
            )
        if (
            req.lifecycle_state == "RECONCILIATION_REQUIRED"
            and req.reconciliation_deadline_at
            and current >= req.reconciliation_deadline_at
        ):
            if self._has_process_residue_diagnostic(req):
                req.diagnostics.setdefault("residue_reconciliation_pending", True)
                self._update_request_locked(req, "RESIDUE_RECONCILIATION_PENDING")
                return req
            req = self._reconcile_request_locked(
                req,
                reason="reconciliation_deadline_expired",
            )
        return req

    def _maybe_converge_recovery(self, req: DurableRemoteRequest) -> DurableRemoteRequest:
        if not self._recovery_due(req) and self.result_for(req.request_id) is None:
            return req
        with self._request_lock(req.request_id):
            current = self._get_request_raw(req.request_id)
            if current is None:
                return req
            return self._maybe_converge_recovery_locked(current)

    def requests_for_node(self, node_id: str) -> list[DurableRemoteRequest]:
        out: list[DurableRemoteRequest] = []
        for path in sorted(self.requests_dir.glob("*.json")):
            req = self._get_request_raw(path.stem)
            if req is None:
                continue
            if req.node_id == node_id:
                if not self._request_is_canonical_for_idempotency(req):
                    continue
                req = self._maybe_converge_recovery(req)
                out.append(req)
        return out

    def reconcile_due_requests(self) -> list[DurableRemoteRequest]:
        """Advance bounded recovery deadlines without requiring node traffic."""
        updated: list[DurableRemoteRequest] = []
        for path in sorted(self.requests_dir.glob("*.json")):
            req = self._get_request_raw(path.stem)
            if req is None:
                continue
            before = req.lifecycle_state
            req = self._maybe_converge_recovery(req)
            if req.lifecycle_state != before:
                updated.append(req)
        return updated

    def deliverable_for_node(
        self,
        node_id: str,
        *,
        limit: int = 1,
        redelivery_after_s: float = 2.0,
    ) -> list[DurableRemoteRequest]:
        current = now_s()
        chosen: list[DurableRemoteRequest] = []
        for req in self.requests_for_node(node_id):
            if req.expires_at and current > req.expires_at and req.lifecycle_state in ACTIVE_STATES:
                with self._request_lock(req.request_id):
                    locked = self._get_request_raw(req.request_id)
                    if locked is None:
                        continue
                    if locked.lifecycle_state in TERMINAL_STATES or locked.lifecycle_state in RECOVERY_STATES:
                        req = self._maybe_converge_recovery_locked(locked)
                    elif locked.lifecycle_state == "QUEUED":
                        locked.lifecycle_state = "EXPIRED"
                        locked.diagnostics.setdefault("expired_before_claim", True)
                        self._update_request_locked(locked, "EXPIRED")
                        req = locked
                    else:
                        locked.lifecycle_state = "CANCEL_REQUESTED"
                        if not locked.cancellation_requested_at:
                            locked.cancellation_requested_at = current
                        if not locked.cancellation_deadline_at:
                            locked.cancellation_deadline_at = current + (
                                _request_budget(
                                    locked,
                                    "cancellation_delivery_timeout_s",
                                    30.0,
                                    minimum=1.0,
                                    maximum=300.0,
                                )
                                + _request_budget(
                                    locked,
                                    "process_termination_timeout_s",
                                    15.0,
                                    minimum=1.0,
                                    maximum=300.0,
                                )
                                + _request_budget(
                                    locked,
                                    "cancellation_ack_timeout_s",
                                    30.0,
                                    minimum=1.0,
                                    maximum=300.0,
                                )
                            )
                        locked.diagnostics.setdefault("expired_during_owned_execution", True)
                        self._update_request_locked(locked, "CANCEL_REQUESTED")
                        req = self._maybe_converge_recovery_locked(locked)
            else:
                req = self._maybe_converge_recovery(req)
            if req.lifecycle_state in {"QUEUED", "CANCEL_REQUESTED"}:
                if req.delivered_at and current - req.delivered_at < redelivery_after_s:
                    continue
                chosen.append(req)
            if len(chosen) >= limit:
                break
        return chosen

    def mark_delivered(self, request_id: str) -> DurableRemoteRequest:
        with self._request_lock(request_id):
            req = self._get_request_raw(request_id)
            if req is None:
                raise KeyError(request_id)
            noncanonical = self._reject_noncanonical_update_locked(req, event="DELIVERED")
            if noncanonical is not None:
                return noncanonical
            req = self._maybe_converge_recovery_locked(req)
            if req.lifecycle_state in {"QUEUED", "CANCEL_REQUESTED"}:
                req.delivered_at = now_s()
                req.delivery_attempts += 1
                self._update_request_locked(req, "DELIVERED")
            return req

    def mark_claimed(
        self,
        request_id: str,
        *,
        claim_id: str,
        lease_seconds: int = 300,
        process_tree: dict[str, Any] | None = None,
    ) -> DurableRemoteRequest:
        with self._request_lock(request_id):
            req = self._get_request_raw(request_id)
            if req is None:
                raise KeyError(request_id)
            noncanonical = self._reject_noncanonical_update_locked(req, event="CLAIMED")
            if noncanonical is not None:
                return noncanonical
            req = self._maybe_converge_recovery_locked(req)
            if req.lifecycle_state in TERMINAL_STATES or req.lifecycle_state in RECOVERY_STATES:
                return req
            if req.lifecycle_state == "CANCEL_REQUESTED":
                return req
            if req.claim_id and req.claim_id != claim_id:
                req.diagnostics["claim_conflict"] = {"existing": req.claim_id, "incoming": claim_id}
                return self._enter_reconciliation(req, reason="claim_conflict")
            if STATE_ORDER.get(req.lifecycle_state, 0) > STATE_ORDER["CLAIMED"]:
                return req
            req.claim_id = claim_id
            req.lease_expires_at = now_s() + lease_seconds
            req.lifecycle_state = "CLAIMED"
            if process_tree is not None:
                req.process_tree = process_tree
                req.process_tree.setdefault("claimed_at", now_s())
            self._update_request_locked(req, "CLAIMED")
            return req

    def mark_running(
        self, request_id: str, *, claim_id: str, process_tree: dict[str, Any] | None = None
    ) -> DurableRemoteRequest:
        with self._request_lock(request_id):
            req = self._get_request_raw(request_id)
            if req is None:
                raise KeyError(request_id)
            noncanonical = self._reject_noncanonical_update_locked(req, event="RUNNING")
            if noncanonical is not None:
                return noncanonical
            req = self._maybe_converge_recovery_locked(req)
            if req.lifecycle_state in TERMINAL_STATES or req.lifecycle_state in RECOVERY_STATES:
                self._event(
                    request_id,
                    "LATE_RUNNING_IGNORED",
                    {
                        "state": req.lifecycle_state,
                        "existing_claim_id": req.claim_id,
                        "incoming_claim_id": claim_id,
                    },
                )
                return req
            if not req.claim_id:
                req.diagnostics["running_without_claim"] = {"incoming": claim_id}
                return self._enter_reconciliation(req, reason="running_without_claim")
            if req.claim_id and req.claim_id != claim_id:
                req.diagnostics["running_claim_conflict"] = {
                    "existing": req.claim_id,
                    "incoming": claim_id,
                }
                return self._enter_reconciliation(req, reason="running_claim_conflict")
            if req.lifecycle_state == "RUNNING":
                if process_tree is not None:
                    req.process_tree = {**req.process_tree, **process_tree}
                    req.process_tree.setdefault("running_at", now_s())
                    self._update_request_locked(req, "RUNNING")
                return req
            if req.lifecycle_state == "CANCEL_REQUESTED":
                return req
            if req.lifecycle_state != "CLAIMED":
                req.diagnostics["running_without_claimed_state"] = {
                    "state": req.lifecycle_state,
                    "claim_id": req.claim_id,
                    "incoming": claim_id,
                }
                return self._enter_reconciliation(req, reason="running_without_claimed_state")
            if req.lifecycle_state not in TERMINAL_STATES and req.lifecycle_state not in RECOVERY_STATES:
                req.claim_id = claim_id
                req.lifecycle_state = "RUNNING"
                if process_tree is not None:
                    req.process_tree = process_tree
                    req.process_tree.setdefault("running_at", now_s())
                self._update_request_locked(req, "RUNNING")
            return req

    def request_cancel(self, request_id: str) -> DurableRemoteRequest:
        with self._request_lock(request_id):
            req = self._get_request_raw(request_id)
            if req is None:
                raise KeyError(request_id)
            noncanonical = self._reject_noncanonical_update_locked(req, event="CANCEL_REQUESTED")
            if noncanonical is not None:
                return noncanonical
            req = self._maybe_converge_recovery_locked(req)
            if req.lifecycle_state == "QUEUED" and not req.claim_id:
                req.lifecycle_state = "CANCELLED"
                if not req.cancellation_requested_at:
                    req.cancellation_requested_at = now_s()
                req.diagnostics.setdefault("cancelled_before_claim", True)
                return self._terminalize(
                    req,
                    claim_id="unclaimed",
                    state="CANCELLED",
                    result={
                        "success": False,
                        "error": "durable remote request cancelled before claim",
                    },
                    cleanup={"process_residue": []},
                    event="CANCELLED_BEFORE_CLAIM",
                )
            if req.lifecycle_state in RECOVERY_STATES:
                return req
            if req.lifecycle_state not in TERMINAL_STATES:
                req.lifecycle_state = "CANCEL_REQUESTED"
                if not req.cancellation_requested_at:
                    req.cancellation_requested_at = now_s()
                if not req.cancellation_deadline_at:
                    req.cancellation_deadline_at = req.cancellation_requested_at + (
                        _request_budget(
                            req,
                            "cancellation_delivery_timeout_s",
                            30.0,
                            minimum=1.0,
                            maximum=300.0,
                        )
                        + _request_budget(
                            req,
                            "process_termination_timeout_s",
                            15.0,
                            minimum=1.0,
                            maximum=300.0,
                        )
                        + _request_budget(
                            req,
                            "cancellation_ack_timeout_s",
                            30.0,
                            minimum=1.0,
                            maximum=300.0,
                        )
                    )
                self._update_request_locked(req, "CANCEL_REQUESTED")
            return req

    def _write_result_record(
        self,
        request: DurableRemoteRequest,
        *,
        claim_id: str,
        state: str,
        result: dict[str, Any],
        cleanup: dict[str, Any] | None = None,
    ) -> str:
        digest = sha256_json(
            {"state": state, "claim_id": claim_id, "result": result, "cleanup": cleanup or {}}
        )
        _atomic_write_json(
            self._result_path(request.request_id),
            {
                "request_id": request.request_id,
                "correlation_id": request.correlation_id,
                "node_id": request.node_id,
                "candidate_sha": request.candidate_sha,
                "claim_id": claim_id,
                "state": state,
                "result": result,
                "result_digest": digest,
                "cleanup_digest": sha256_json(cleanup or {}),
                "cleanup": cleanup or {},
                "published_at": now_s(),
            },
        )
        return digest

    def _write_rejected_result_record(
        self,
        request: DurableRemoteRequest,
        *,
        claim_id: str,
        state: str,
        result: dict[str, Any],
        reason: str,
        cleanup: dict[str, Any] | None = None,
    ) -> str:
        digest = sha256_json(
            {
                "state": state,
                "claim_id": claim_id,
                "result": result,
                "cleanup": cleanup or {},
                "reason": reason,
            }
        )
        _atomic_write_json(
            self._rejected_result_path(request.request_id, digest),
            {
                "request_id": request.request_id,
                "correlation_id": request.correlation_id,
                "node_id": request.node_id,
                "candidate_sha": request.candidate_sha,
                "claim_id": claim_id,
                "state": state,
                "result": result,
                "result_digest": digest,
                "cleanup_digest": sha256_json(cleanup or {}),
                "cleanup": cleanup or {},
                "rejected_reason": reason,
                "rejected_at": now_s(),
            },
        )
        return digest

    def _terminalize(
        self,
        req: DurableRemoteRequest,
        *,
        claim_id: str,
        state: str,
        result: dict[str, Any],
        cleanup: dict[str, Any] | None = None,
        event: str | None = None,
    ) -> DurableRemoteRequest:
        req.claim_id = claim_id
        req.lifecycle_state = state
        req.result_digest = self._write_result_record(
            req,
            claim_id=claim_id,
            state=state,
            result=result,
            cleanup=cleanup,
        )
        if cleanup is not None:
            req.cleanup = cleanup
        if state == "CANCELLED" and not req.cancellation_acknowledged_at:
            req.cancellation_acknowledged_at = now_s()
        self._update_request_locked(req, event or state)
        return req

    def publish_result(
        self,
        request_id: str,
        *,
        claim_id: str,
        state: str,
        result: dict[str, Any],
        cleanup: dict[str, Any] | None = None,
    ) -> DurableRemoteRequest:
        if state not in {"SUCCEEDED", "FAILED", "CANCELLED"}:
            raise ValueError(f"invalid terminal state: {state}")
        with self._request_lock(request_id):
            return self._publish_result_locked(
                request_id,
                claim_id=claim_id,
                state=state,
                result=result,
                cleanup=cleanup,
            )

    def _publish_result_locked(
        self,
        request_id: str,
        *,
        claim_id: str,
        state: str,
        result: dict[str, Any],
        cleanup: dict[str, Any] | None = None,
    ) -> DurableRemoteRequest:
        req = self._get_request_raw(request_id)
        if req is None:
            raise KeyError(request_id)
        noncanonical = self._reject_noncanonical_update_locked(req, event=state)
        if noncanonical is not None:
            return noncanonical
        req = self._maybe_converge_recovery_locked(req)
        if not req.claim_id:
            self._write_rejected_result_record(
                req,
                claim_id=claim_id,
                state=state,
                result=result,
                cleanup=cleanup,
                reason="result_without_claim",
            )
            req.diagnostics["result_without_claim"] = {"incoming": claim_id}
            return self._enter_reconciliation(req, reason="result_without_claim")
        if req.lifecycle_state in TERMINAL_STATES:
            existing = self.result_for(request_id)
            incoming_digest = sha256_json(
                {"state": state, "claim_id": claim_id, "result": result, "cleanup": cleanup or {}}
            )
            if cleanup and cleanup.get("process_residue"):
                self._write_rejected_result_record(
                    req,
                    claim_id=claim_id,
                    state=state,
                    result=result,
                    cleanup=cleanup,
                    reason="terminal_cancel_cleanup_conflict",
                )
                return req
            if (
                existing
                and existing.get("state") == state
                and existing.get("claim_id") == claim_id
                and existing.get("result_digest") == incoming_digest
            ):
                return req
            self._write_rejected_result_record(
                req,
                claim_id=claim_id,
                state=state,
                result=result,
                cleanup=cleanup,
                reason="terminal_result_conflict",
            )
            return req
        if req.claim_id != claim_id:
            self._write_rejected_result_record(
                req,
                claim_id=claim_id,
                state=state,
                result=result,
                cleanup=cleanup,
                reason="result_claim_conflict",
            )
            req.diagnostics["result_claim_conflict"] = {"existing": req.claim_id, "incoming": claim_id}
            return self._enter_reconciliation(req, reason="result_claim_conflict")
        if req.lifecycle_state in RECOVERY_STATES:
            reconciliation_reasons = req.diagnostics.get("reconciliation_reasons")
            is_cancellation_ack_recovery = (
                isinstance(reconciliation_reasons, list)
                and set(reconciliation_reasons) == {"cancellation_ack_deadline_expired"}
                and req.cancellation_requested_at
                and req.cancellation_deadline_at
                and cleanup is not None
                and cleanup.get("process_residue") == []
                and not self._cancellation_ack_rejection_reason(
                    req,
                    claim_id=claim_id,
                    cleanup=cleanup,
                )
                and not self._has_process_residue_diagnostic(req)
            )
            if (
                req.claim_id == claim_id
                and state in {"CANCELLED", "FAILED"}
                and is_cancellation_ack_recovery
            ):
                req.diagnostics.setdefault("recovered_from_reconciliation_result", []).append(
                    {
                        "incoming_state": state,
                        "claim_id": claim_id,
                        "cleanup_digest": sha256_json(cleanup or {}),
                    }
                )
                return self._terminalize(
                    req,
                    claim_id=claim_id,
                    state=state,
                    result=result,
                    cleanup=cleanup,
                    event="RECONCILIATION_RESULT_RECOVERED",
                )
            digest = self._write_rejected_result_record(
                req,
                claim_id=claim_id,
                state=state,
                result=result,
                cleanup=cleanup,
                reason="reconciliation_pending",
            )
            req.diagnostics.setdefault("rejected_during_reconciliation", []).append(
                {"incoming_state": state, "digest": digest}
            )
            self._update_request_locked(req, "LATE_RESULT_REJECTED")
            return req
        if state in TERMINAL_STATES and (
            cleanup is None or cleanup.get("process_residue") != []
        ):
            reason_by_state = {
                "CANCELLED": "cancel_without_cleanup",
                "FAILED": "failed_without_cleanup",
                "SUCCEEDED": "success_without_cleanup",
            }
            reason = reason_by_state.get(state, "terminal_without_cleanup")
            self._write_rejected_result_record(
                req,
                claim_id=claim_id,
                state=state,
                result=result,
                cleanup=cleanup,
                reason=reason,
            )
            req.cleanup = cleanup or {}
            req.diagnostics[reason] = (
                cleanup.get("process_residue")
                if cleanup is not None
                else [{"state": "cleanup_proof_missing"}]
            )
            return self._enter_reconciliation(req, reason=reason)
        if state == "CANCELLED":
            reason = self._cancellation_ack_rejection_reason(
                req,
                claim_id=claim_id,
                cleanup=cleanup,
            )
            if reason:
                self._write_rejected_result_record(
                    req,
                    claim_id=claim_id,
                    state=state,
                    result=result,
                    cleanup=cleanup,
                    reason=reason,
                )
                req.cleanup = cleanup or {}
                req.diagnostics.setdefault("cancel_ack_rejected", []).append(
                    {"reason": reason, "claim_id": claim_id}
                )
                return self._enter_reconciliation(req, reason=reason)
        if req.lifecycle_state == "CANCEL_REQUESTED" and state == "SUCCEEDED":
            if req.cancellation_acknowledged_at:
                self._write_rejected_result_record(
                    req,
                    claim_id=claim_id,
                    state=state,
                    result=result,
                    cleanup=cleanup,
                    reason="late_success_after_cancel_ack",
                )
                req.diagnostics["late_success_rejected"] = True
                self._update_request_locked(req, "LATE_RESULT_REJECTED")
                return req
            if req.expires_at and now_s() > req.expires_at:
                self._write_rejected_result_record(
                    req,
                    claim_id=claim_id,
                    state=state,
                    result=result,
                    cleanup=cleanup,
                    reason="late_success_after_expiry",
                )
                req.diagnostics["late_success_after_expiry"] = True
                return self._enter_reconciliation(req, reason="late_success_after_expiry")
            req.diagnostics["success_after_cancel_requested"] = {
                "cancellation_requested_at": req.cancellation_requested_at,
                "resolution": "success_won_before_acknowledged_cancellation",
            }
        if req.lifecycle_state == "EXPIRED" and state == "SUCCEEDED":
            self._write_rejected_result_record(
                req,
                claim_id=claim_id,
                state=state,
                result=result,
                cleanup=cleanup,
                reason="late_success_after_expiry",
            )
            req.diagnostics["late_success_after_expiry"] = True
            return self._enter_reconciliation(req, reason="late_success_after_expiry")
        return self._terminalize(
            req,
            claim_id=claim_id,
            state=state,
            result=result,
            cleanup=cleanup,
        )

    def reconcile_request(self, request_id: str, *, reason: str = "bounded_reconciliation") -> DurableRemoteRequest:
        with self._request_lock(request_id):
            req = self._get_request_raw(request_id)
            if req is None:
                raise KeyError(request_id)
            return self._reconcile_request_locked(req, reason=reason)

    def _reconcile_request_locked(
        self,
        req: DurableRemoteRequest,
        *,
        reason: str = "bounded_reconciliation",
    ) -> DurableRemoteRequest:
        noncanonical = self._reject_noncanonical_update_locked(req, event="RECONCILE_REJECTED")
        if noncanonical is not None:
            return noncanonical
        if req.lifecycle_state in TERMINAL_STATES:
            return req
        if req.lifecycle_state != "RECONCILIATION_REQUIRED":
            return req
        if self._has_process_residue_diagnostic(req):
            req.diagnostics.setdefault("residue_reconciliation_pending", True)
            self._update_request_locked(req, "RESIDUE_RECONCILIATION_PENDING")
            return req
        req.diagnostics["reconciled_fail_closed"] = {
            "reason": reason,
            "prior_state": "RECONCILIATION_REQUIRED",
            "process_tree": req.process_tree,
            "cleanup": req.cleanup,
        }
        return self._terminalize(
            req,
            claim_id=req.claim_id or "unclaimed",
            state="FAILED",
            result={
                "success": False,
                "error": "durable remote reconciliation failed closed",
                "reason": reason,
            },
            cleanup=req.cleanup,
            event="RECONCILED_FAILED",
        )

    def fail_unresolved_request(
        self, request_id: str, *, reason: str = "unresolved_timeout"
    ) -> DurableRemoteRequest:
        with self._request_lock(request_id):
            req = self._get_request_raw(request_id)
            if req is None:
                raise KeyError(request_id)
            noncanonical = self._reject_noncanonical_update_locked(
                req,
                event="UNRESOLVED_REJECTED",
            )
            if noncanonical is not None:
                return noncanonical
            req = self._maybe_converge_recovery_locked(req)
            if req.lifecycle_state in TERMINAL_STATES:
                return req
            if req.lifecycle_state == "RECONCILIATION_REQUIRED":
                if self._has_process_residue_diagnostic(req):
                    return req
                return self._reconcile_request_locked(req, reason=reason)
            req.diagnostics["unresolved_failed_closed"] = {
                "reason": reason,
                "prior_state": req.lifecycle_state,
                "process_tree": req.process_tree,
                "cleanup": req.cleanup,
            }
            return self._terminalize(
                req,
                claim_id=req.claim_id or "unclaimed",
                state="FAILED",
                result={
                    "success": False,
                    "error": "durable remote unresolved request failed closed",
                    "reason": reason,
                },
                cleanup=req.cleanup,
                event="UNRESOLVED_FAILED",
            )

    def result_for(self, request_id: str) -> dict[str, Any] | None:
        data = _read_json(self._result_path(request_id))
        return data or None

    def remove_request(self, request_id: str, *, force_terminal: bool = False) -> None:
        current = self.get_request(request_id)
        if (
            current is not None
            and current.lifecycle_state in TERMINAL_STATES
            and not force_terminal
        ):
            raise ValueError("refusing to remove terminal durable request without force_terminal")
        for path in (self._request_path(request_id), self._result_path(request_id)):
            try:
                path.unlink()
            except FileNotFoundError:
                pass
        if current is not None and current.idempotency_key:
            preserve_tombstone = (
                current.lifecycle_state in TERMINAL_STATES
                or current.lifecycle_state in RECOVERY_STATES
            )
            if not preserve_tombstone:
                index_path = self._idempotency_index_path(current.idempotency_key)
                index = _read_json(index_path)
                if str(index.get("canonical_request_id", "")) == request_id:
                    try:
                        index_path.unlink()
                    except FileNotFoundError:
                        pass
        self._event(request_id, "REMOVED")


def make_request(
    *,
    correlation_id: str,
    candidate_sha: str,
    node_id: str,
    operation_type: str,
    capability: str,
    params: dict[str, Any],
    risk_class: str = "reversible_write",
    authority_id: str = "",
    ttl_seconds: int = 900,
    idempotency_key: str = "",
) -> DurableRemoteRequest:
    request_id = f"drc-{uuid4().hex[:16]}"
    return DurableRemoteRequest(
        request_id=request_id,
        correlation_id=correlation_id,
        candidate_sha=candidate_sha,
        node_id=node_id,
        operation_type=operation_type,
        capability=capability,
        params=params,
        risk_class=risk_class,
        authority_id=authority_id,
        idempotency_key=idempotency_key,
        expires_at=now_s() + ttl_seconds,
    )
