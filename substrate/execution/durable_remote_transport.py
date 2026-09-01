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
    is_write_class,
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
_RESIDUE_RECONCILIATION_INITIAL_REMINDER_S = 1.0
_RESIDUE_RECONCILIATION_MAX_REMINDER_S = 300.0
_RESULT_DELIVERY_INITIAL_RETRY_S = 1.0
_RESULT_DELIVERY_MAX_RETRY_S = 300.0

SHELL_LAUNCH_INTENT_PERSISTED = "LAUNCH_INTENT_PERSISTED"
SHELL_LAUNCH_IN_PROGRESS = "LAUNCH_IN_PROGRESS"
SHELL_PROCESS_IDENTITY_PERSISTED = "PROCESS_IDENTITY_PERSISTED"
SHELL_LAUNCH_RUNNING = "RUNNING"
SHELL_LAUNCH_STATES = frozenset(
    {
        SHELL_LAUNCH_INTENT_PERSISTED,
        SHELL_LAUNCH_IN_PROGRESS,
        SHELL_PROCESS_IDENTITY_PERSISTED,
        SHELL_LAUNCH_RUNNING,
    }
)
_SHELL_LAUNCH_STATE_ORDER = {
    SHELL_LAUNCH_INTENT_PERSISTED: 0,
    SHELL_LAUNCH_IN_PROGRESS: 1,
    SHELL_PROCESS_IDENTITY_PERSISTED: 2,
    SHELL_LAUNCH_RUNNING: 3,
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


def terminal_result_identity(
    request: "DurableRemoteRequest",
    result: dict[str, Any],
) -> dict[str, Any]:
    """Return the stable logical identity for exact terminal result material."""
    identity = {
        "request_id": request.request_id,
        "correlation_id": request.correlation_id,
        "idempotency_key": request.idempotency_key,
        "candidate_sha": request.candidate_sha,
        "node_id": request.node_id,
        "operation_type": request.operation_type,
        "capability": request.capability,
        "payload_digest": request.payload_digest,
        "claim_id": str(result.get("claim_id", "") or ""),
        "state": str(result.get("state", "") or ""),
        "result_digest": str(result.get("result_digest", "") or ""),
        "cleanup_digest": str(result.get("cleanup_digest", "") or ""),
    }
    identity["result_id"] = sha256_json(identity)
    return identity


def _normalized_idempotency_key(value: str) -> str:
    return str(value or "").strip()


def _reject_duplicate_json_object_pairs(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for key, value in pairs:
        if key in out:
            raise ValueError(f"duplicate JSON object key: {key}")
        out[key] = value
    return out


def _loads_authority_json_object(raw: bytes | str) -> dict[str, Any]:
    if isinstance(raw, bytes):
        text = raw.decode("utf-8")
    else:
        text = raw
    data = json.loads(text, object_pairs_hook=_reject_duplicate_json_object_pairs)
    if not isinstance(data, dict):
        raise ValueError("json record is not an object")
    return dict(data)


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

LOAD_ABSENT = "ABSENT"
LOAD_VALID = "VALID"
LOAD_CORRUPT = "CORRUPT"
LOAD_READ_ERROR = "READ_ERROR"
UNKNOWN_IDEMPOTENCY_SCOPE = "__unknown_idempotency_scope__"


def _atomic_write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + f".tmp-{uuid4().hex}")
    tmp.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    tmp.replace(path)


@dataclass(frozen=True)
class _DurableRecordLoad:
    status: str
    path: Path
    data: dict[str, Any] | None = None
    reason: str = ""

    @property
    def valid(self) -> bool:
        return self.status == LOAD_VALID and isinstance(self.data, dict)

    @property
    def unavailable(self) -> bool:
        return self.status in {LOAD_CORRUPT, LOAD_READ_ERROR}


@dataclass(frozen=True)
class _DurableRequestLoad:
    status: str
    path: Path
    request: "DurableRemoteRequest | None" = None
    data: dict[str, Any] | None = None
    reason: str = ""

    @property
    def valid(self) -> bool:
        return self.status == LOAD_VALID and self.request is not None

    @property
    def unavailable(self) -> bool:
        return self.status in {LOAD_CORRUPT, LOAD_READ_ERROR}


@dataclass(frozen=True)
class _DurableEventJournalLoad:
    bindings: list[dict[str, Any]]
    complete: bool = True
    reason: str = ""

    @property
    def incomplete(self) -> bool:
        return not self.complete


@dataclass(frozen=True)
class _IdempotencyCorruptionScope:
    same_key: bool = False
    unknown_scope: bool = False
    read_error: bool = False
    reasons: tuple[str, ...] = ()

    @property
    def blocks_fresh_authority(self) -> bool:
        return self.same_key or self.unknown_scope or self.read_error

    def reason(self, idempotency_key: str) -> str:
        labels: list[str] = []
        if self.same_key:
            labels.append("same-key corrupt request material")
        if self.unknown_scope:
            labels.append("unknown-scope corrupt request material")
        if self.read_error:
            labels.append("request read error")
        detail = "; ".join(self.reasons[:3])
        base = ", ".join(labels) or "request corruption"
        suffix = f": {detail}" if detail else ""
        return f"idempotency request corruption fenced for key {idempotency_key}: {base}{suffix}"


def _read_json(path: Path) -> dict[str, Any]:
    outcome = _load_json_record(path)
    return dict(outcome.data or {}) if outcome.valid else {}


def _load_json_record(
    path: Path,
    *,
    record_kind: str | None = None,
    identity: str = "",
) -> _DurableRecordLoad:
    try:
        raw = path.read_bytes()
    except FileNotFoundError:
        if identity and _corruption_fence_exists(path, identity=identity):
            return _DurableRecordLoad(
                LOAD_CORRUPT,
                path,
                reason="unresolved corruption fence exists",
            )
        return _DurableRecordLoad(LOAD_ABSENT, path)
    except OSError as exc:
        reason = f"{type(exc).__name__}: {exc}"
        _record_persistence_issue(
            path,
            reason=reason,
            record_kind=record_kind,
            identity=identity,
            status=LOAD_READ_ERROR,
        )
        return _DurableRecordLoad(LOAD_READ_ERROR, path, reason=reason)
    try:
        data = _loads_authority_json_object(raw)
    except (json.JSONDecodeError, UnicodeDecodeError, ValueError) as exc:
        reason = f"{type(exc).__name__}: {exc}"
        _record_persistence_issue(
            path,
            reason=reason,
            record_kind=record_kind,
            identity=identity,
            status=LOAD_CORRUPT,
        )
        return _DurableRecordLoad(LOAD_CORRUPT, path, reason=reason)
    return _DurableRecordLoad(LOAD_VALID, path, data=data)


def _corruption_fence_path(path: Path, *, identity: str) -> Path:
    root = (
        path.parent.parent
        if path.parent.name in {"requests", "idempotency", "results"}
        else path.parent
    )
    fence_identity = f"{path.parent.name}:{identity}"
    return (
        root / "corrupt" / f"fence-{hashlib.sha256(fence_identity.encode()).hexdigest()[:32]}.json"
    )


def _corruption_fence_exists(path: Path, *, identity: str) -> bool:
    return _corruption_fence_path(path, identity=identity).exists()


def _record_persistence_issue(
    path: Path,
    *,
    reason: str,
    record_kind: str | None = None,
    identity: str = "",
    status: str = LOAD_CORRUPT,
) -> None:
    try:
        raw = path.read_bytes()
    except OSError:
        raw = b""
    kind = record_kind or path.parent.name
    root = (
        path.parent.parent
        if path.parent.name in {"requests", "idempotency", "results"}
        else path.parent
    )
    evidence = {
        "record_path": str(path),
        "record_kind": kind,
        "identity": identity,
        "status": status,
        "reason": reason,
        "sha256": hashlib.sha256(raw).hexdigest(),
        "size_bytes": len(raw),
        "observed_at": now_s(),
        "disposition": "corrupt_record_isolated_fail_closed",
    }
    evidence_path = (
        root / "corrupt" / f"{kind}-{hashlib.sha256(str(path).encode()).hexdigest()[:16]}.json"
    )
    try:
        _atomic_write_json(evidence_path, evidence)
        if identity:
            fence = dict(evidence)
            fence["fence_identity"] = identity
            _atomic_write_json(_corruption_fence_path(path, identity=identity), fence)
    except OSError:
        pass


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
            cancellation_acknowledged_at=float(
                data.get("cancellation_acknowledged_at", 0.0) or 0.0
            ),
            reconciliation_requested_at=float(data.get("reconciliation_requested_at", 0.0) or 0.0),
            reconciliation_deadline_at=float(data.get("reconciliation_deadline_at", 0.0) or 0.0),
            terminalized_at=float(data.get("terminalized_at", 0.0) or 0.0),
            updated_at=float(data.get("updated_at", 0.0) or 0.0),
            cleanup=dict(data.get("cleanup") or {}),
            diagnostics=dict(data.get("diagnostics") or {}),
        )


def durable_execution_identity(
    request: DurableRemoteRequest,
    *,
    claim_id: str,
) -> dict[str, Any]:
    """Return the immutable logical execution identity shared by node and VPS."""

    policy = canonical_sync_effect_policy(
        request.capability,
        declared_effect_class=CONSEQUENTIAL_WRITE_EFFECT,
    )
    identity: dict[str, Any] = {
        "request_id": request.request_id,
        "correlation_id": request.correlation_id,
        "node_id": request.node_id,
        "candidate_sha": request.candidate_sha,
        "idempotency_key": request.idempotency_key,
        "payload_digest": request.payload_digest,
        "claim_id": str(claim_id or ""),
        "capability": request.capability,
        "operation_type": request.operation_type,
        "risk_class": request.risk_class,
        "authority_id": request.authority_id,
        "authoritative_effect_class": policy.authoritative_effect_class,
        "effect_policy_id": policy.policy_id,
        "attempt": request.attempt,
    }
    identity["logical_execution_id"] = sha256_json(identity)
    identity["execution_id"] = identity["logical_execution_id"]
    return identity


def shell_running_identity_error(
    request: DurableRemoteRequest,
    *,
    claim_id: str,
    process_tree: dict[str, Any],
) -> str:
    """Reject partial or foreign process material before canonical shell RUNNING."""

    adapter_key = str(request.capability or "").split(".", 1)[0]
    if adapter_key != "shell":
        return ""
    launch_state = str(process_tree.get("launch_state", "") or "")
    if launch_state not in {SHELL_PROCESS_IDENTITY_PERSISTED, SHELL_LAUNCH_RUNNING}:
        return "shell RUNNING requires persisted process identity state"
    root_pid = process_tree.get("root_pid")
    process_identity = dict(process_tree.get("process_identity") or {})
    if not isinstance(root_pid, int) or root_pid <= 0:
        return "shell RUNNING requires positive root_pid"
    if process_identity.get("pid") != root_pid:
        return "shell RUNNING process identity PID mismatch"
    for key in (
        "start_token",
        "executable",
        "observed_command_digest",
        "command_digest",
        "identity_source",
    ):
        if not str(process_identity.get(key, "") or "").strip():
            return f"shell RUNNING process identity missing {key}"
    if process_identity.get("command_digest") != request.payload_digest:
        return "shell RUNNING process command digest mismatch"
    expected = durable_execution_identity(request, claim_id=claim_id)
    if dict(process_tree.get("execution_identity") or {}) != expected:
        return "shell RUNNING immutable execution identity mismatch"
    if not str(process_tree.get("launch_intent_id", "") or "").strip():
        return "shell RUNNING requires launch_intent_id"
    return ""


class DurableRemoteStore:
    """File-backed canonical store for one controller or node spool."""

    def __init__(self, root: Path | str | None = None) -> None:
        self.root = Path(root) if root is not None else default_controller_root()
        self.requests_dir = self.root / "requests"
        self.results_dir = self.root / "results"
        self.result_outbox_dir = self.root / "result_outbox"
        self.idempotency_dir = self.root / "idempotency"
        self.events_path = self.root / "events.jsonl"
        self.requests_dir.mkdir(parents=True, exist_ok=True)
        self.results_dir.mkdir(parents=True, exist_ok=True)
        self.result_outbox_dir.mkdir(parents=True, exist_ok=True)
        self.idempotency_dir.mkdir(parents=True, exist_ok=True)

    def _request_path(self, request_id: str) -> Path:
        return self.requests_dir / f"{request_id}.json"

    def _result_path(self, request_id: str) -> Path:
        return self.results_dir / f"{request_id}.json"

    def _result_delivery_path(self, request_id: str) -> Path:
        return self.result_outbox_dir / f"{request_id}.json"

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

    def _request_corruption_fence_path(self, identity: str) -> Path:
        return _corruption_fence_path(self.requests_dir / "_scope.json", identity=identity)

    def _request_corruption_fence_exists(self, identity: str) -> bool:
        return self._request_corruption_fence_path(identity).exists()

    def _negative_request_corruption_identity(
        self,
        path: Path,
        *,
        data: dict[str, Any] | None = None,
        request: DurableRemoteRequest | None = None,
    ) -> str:
        if request is not None:
            key = _normalized_idempotency_key(request.idempotency_key)
            if key:
                return key
        if isinstance(data, dict):
            raw_key = data.get("idempotency_key")
            key = _normalized_idempotency_key(raw_key) if isinstance(raw_key, str) else ""
            if key:
                return key
        return ""

    def _record_request_corruption_fence(
        self,
        path: Path,
        *,
        reason: str,
        data: dict[str, Any] | None = None,
        request: DurableRemoteRequest | None = None,
        status: str = LOAD_CORRUPT,
    ) -> str:
        identity = self._negative_request_corruption_identity(path, data=data, request=request)
        if not identity:
            identity = UNKNOWN_IDEMPOTENCY_SCOPE
        _record_persistence_issue(
            path,
            reason=reason,
            record_kind="requests",
            identity=identity,
            status=status,
        )
        return identity

    def _load_request_record(self, request_id: str) -> _DurableRequestLoad:
        path = self._request_path(request_id)
        loaded = _load_json_record(path, record_kind="requests", identity=request_id)
        if not loaded.valid:
            if loaded.unavailable:
                self._record_request_corruption_fence(
                    path,
                    reason=loaded.reason or f"request record {loaded.status.lower()}",
                    data=loaded.data,
                    status=loaded.status,
                )
            return _DurableRequestLoad(
                loaded.status,
                path,
                data=loaded.data,
                reason=loaded.reason,
            )
        data = dict(loaded.data or {})
        try:
            req = DurableRemoteRequest.from_dict(data)
        except (TypeError, ValueError) as exc:
            self._record_request_corruption_fence(
                path,
                reason=f"request materialization failed: {type(exc).__name__}: {exc}",
                data=data,
            )
            return _DurableRequestLoad(
                LOAD_CORRUPT,
                path,
                data=data,
                reason=f"request materialization failed: {type(exc).__name__}: {exc}",
            )
        if req.request_id != request_id:
            reason = f"request path/content identity mismatch: path={request_id} content={req.request_id}"
            self._record_request_corruption_fence(
                path,
                reason=reason,
                data=data,
                request=req,
            )
            return _DurableRequestLoad(LOAD_CORRUPT, path, request=req, data=data, reason=reason)
        if req.lifecycle_state not in STATE_ORDER:
            reason = f"request lifecycle_state invalid: {req.lifecycle_state}"
            self._record_request_corruption_fence(
                path,
                reason=reason,
                data=data,
                request=req,
            )
            return _DurableRequestLoad(LOAD_CORRUPT, path, request=req, data=data, reason=reason)
        return _DurableRequestLoad(LOAD_VALID, path, request=req, data=data)

    def _load_idempotency_index_record(self, idempotency_key: str) -> _DurableRecordLoad:
        key = _normalized_idempotency_key(idempotency_key)
        path = self._idempotency_index_path(key)
        loaded = _load_json_record(path, record_kind="idempotency", identity=key)
        if not loaded.valid:
            return loaded
        data = dict(loaded.data or {})
        if str(data.get("idempotency_key", "") or "").strip() != key:
            reason = "idempotency index path/content identity mismatch"
            _record_persistence_issue(
                path,
                reason=reason,
                record_kind="idempotency",
                identity=key,
            )
            return _DurableRecordLoad(LOAD_CORRUPT, path, data=data, reason=reason)
        if not str(data.get("canonical_request_id", "") or "").strip():
            reason = "idempotency index missing canonical request id"
            _record_persistence_issue(
                path,
                reason=reason,
                record_kind="idempotency",
                identity=key,
            )
            return _DurableRecordLoad(LOAD_CORRUPT, path, data=data, reason=reason)
        return _DurableRecordLoad(LOAD_VALID, path, data=data)

    def _load_result_record(self, request_id: str) -> _DurableRecordLoad:
        path = self._result_path(request_id)
        loaded = _load_json_record(path, record_kind="results", identity=request_id)
        if not loaded.valid:
            return loaded
        data = dict(loaded.data or {})
        if str(data.get("request_id", "") or "").strip() != request_id:
            reason = "result path/content identity mismatch"
            _record_persistence_issue(
                path,
                reason=reason,
                record_kind="results",
                identity=request_id,
            )
            return _DurableRecordLoad(LOAD_CORRUPT, path, data=data, reason=reason)
        if str(data.get("state", "") or "").strip() not in TERMINAL_STATES:
            reason = "result state invalid"
            _record_persistence_issue(
                path,
                reason=reason,
                record_kind="results",
                identity=request_id,
            )
            return _DurableRecordLoad(LOAD_CORRUPT, path, data=data, reason=reason)
        if not isinstance(data.get("result"), dict) or not isinstance(data.get("cleanup"), dict):
            reason = "result or cleanup material is not an object"
            _record_persistence_issue(
                path,
                reason=reason,
                record_kind="results",
                identity=request_id,
            )
            return _DurableRecordLoad(LOAD_CORRUPT, path, data=data, reason=reason)
        return _DurableRecordLoad(LOAD_VALID, path, data=data)

    def _mark_persistence_integrity_failure_locked(
        self,
        req: DurableRemoteRequest,
        *,
        event: str,
        reason: str,
        record_kind: str,
    ) -> DurableRemoteRequest:
        req.diagnostics.setdefault("persistence_integrity_failure", []).append(
            {
                "event": event,
                "record_kind": record_kind,
                "reason": reason,
                "observed_at": now_s(),
            }
        )
        req.diagnostics.setdefault("noncanonical_event_rejected", []).append(
            {"event": event, "observed_at": now_s()}
        )
        if req.lifecycle_state not in TERMINAL_STATES:
            return self._enter_reconciliation(req, reason=f"{record_kind}_corrupt")
        self._update_request_locked(req, event, write_idempotency_index=False)
        return req

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
    def _idempotency_lock(self, idempotency_key: str, *, timeout_s: float = 10.0) -> Iterator[None]:
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

    @staticmethod
    def _idempotency_binding_identity(binding: dict[str, Any]) -> dict[str, Any]:
        return {
            key: binding.get(key)
            for key in (
                "version",
                "idempotency_scope",
                "idempotency_key",
                "canonical_request_id",
                "candidate_sha",
                "node_id",
                "capability",
                "operation_type",
                "risk_class",
                "authority_id",
                "effect_class",
                "payload_digest",
                "created_at",
            )
        }

    def _validate_binding_identity(
        self,
        current: dict[str, Any],
        expected: dict[str, Any],
        *,
        reason: str,
    ) -> None:
        current_identity = self._idempotency_binding_identity(current)
        expected_identity = self._idempotency_binding_identity(expected)
        if current_identity == expected_identity:
            return
        mismatched = sorted(
            key
            for key, expected_value in expected_identity.items()
            if current_identity.get(key) != expected_value
        )
        raise ValueError(f"{reason}: {','.join(mismatched)}")

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

    def _validate_canonical_request_material(
        self,
        request: DurableRemoteRequest,
        *,
        strict_payload_digest: bool = True,
    ) -> None:
        request.idempotency_key = _normalized_idempotency_key(request.idempotency_key)
        required_nonempty = (
            "request_id",
            "candidate_sha",
            "node_id",
            "operation_type",
            "capability",
        )
        for field_name in required_nonempty:
            value = str(getattr(request, field_name, "") or "").strip()
            if not value:
                raise ValueError(f"durable request requires {field_name}")
            setattr(request, field_name, value)
        if not request.idempotency_key:
            raise ValueError("consequential durable request requires idempotency_key")
        computed = _request_payload_digest(
            operation_type=request.operation_type,
            capability=request.capability,
            params=request.params,
            candidate_sha=request.candidate_sha,
            authority_id=request.authority_id,
        )
        if strict_payload_digest and request.payload_digest and request.payload_digest != computed:
            raise ValueError("durable request payload_digest mismatch")
        request.payload_digest = computed
        effect_policy = canonical_sync_effect_policy(
            request.capability,
            declared_effect_class=CONSEQUENTIAL_WRITE_EFFECT,
        )
        if effect_policy.authoritative_effect_class != CONSEQUENTIAL_WRITE_EFFECT:
            raise ValueError("durable request capability has no canonical consequential policy")
        if effect_policy.declared_effect_class != CONSEQUENTIAL_WRITE_EFFECT:
            raise ValueError("durable request declared effect conflicts with canonical policy")
        if not is_write_class(request.risk_class):
            raise ValueError(
                "durable request risk_class conflicts with canonical consequential policy"
            )

    def _mark_invalid_canonical_material_locked(
        self,
        req: DurableRemoteRequest,
        *,
        event: str,
        reason: str,
    ) -> DurableRemoteRequest:
        req.diagnostics.setdefault(
            "canonical_material_rejected",
            {
                "event": event,
                "reason": reason,
                "observed_at": now_s(),
            },
        )
        req.diagnostics.setdefault("noncanonical_event_rejected", []).append(
            {"event": event, "observed_at": now_s()}
        )
        req.diagnostics.setdefault("reconciliation_reasons", []).append(
            "canonical_material_invalid"
        )
        self._strip_noncanonical_authority_fields(req)
        if req.lifecycle_state not in TERMINAL_STATES:
            req.lifecycle_state = "RECONCILIATION_REQUIRED"
            if not req.reconciliation_requested_at:
                req.reconciliation_requested_at = now_s()
            req.reconciliation_deadline_at = max(
                req.reconciliation_deadline_at,
                req.reconciliation_requested_at + 15.0,
            )
        self._update_request_locked(
            req,
            "CANONICAL_MATERIAL_REJECTED",
            write_idempotency_index=False,
        )
        return req

    def _reject_invalid_canonical_material_locked(
        self,
        req: DurableRemoteRequest,
        *,
        event: str,
    ) -> DurableRemoteRequest | None:
        try:
            self._validate_canonical_request_material(req)
        except ValueError as exc:
            return self._mark_invalid_canonical_material_locked(
                req,
                event=event,
                reason=str(exc),
            )
        return None

    def _write_idempotency_index(self, request: DurableRemoteRequest) -> None:
        if not request.idempotency_key:
            return
        self._validate_canonical_request_material(request)
        existing_load = self._load_idempotency_index_record(request.idempotency_key)
        if existing_load.status == LOAD_READ_ERROR:
            raise ValueError("idempotency index read error")
        existing = dict(existing_load.data or {}) if existing_load.valid else {}
        existing_request_id = str(existing.get("canonical_request_id", "")) if existing else ""
        if existing_request_id and existing_request_id != request.request_id:
            raise ValueError("idempotency index canonical request mismatch")
        binding = self._idempotency_binding(request)
        if existing_request_id == request.request_id:
            self._validate_binding_identity(
                binding,
                existing,
                reason="idempotency index binding drift",
            )
        _atomic_write_json(
            self._idempotency_index_path(request.idempotency_key),
            binding,
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
                    f"idempotency conflict: {field_name} differs for key {incoming.idempotency_key}"
                )

    @staticmethod
    def _strip_noncanonical_authority_fields(req: DurableRemoteRequest) -> None:
        req.claim_id = ""
        req.lease_expires_at = 0.0
        req.process_tree = {}

    @staticmethod
    def _request_sort_key(req: DurableRemoteRequest) -> tuple[float, str]:
        return (float(req.created_at or 0.0), req.request_id)

    def _admission_bindings_for_idempotency_key_locked(
        self, idempotency_key: str
    ) -> _DurableEventJournalLoad:
        bindings: list[dict[str, Any]] = []
        seen: set[str] = set()
        try:
            raw = self.events_path.read_bytes()
        except FileNotFoundError:
            return _DurableEventJournalLoad(bindings)
        except OSError as exc:
            reason = f"event journal read failed: {type(exc).__name__}: {exc}"
            _record_persistence_issue(
                self.events_path,
                reason=reason,
                record_kind="events",
                identity="events_journal",
                status=LOAD_READ_ERROR,
            )
            return _DurableEventJournalLoad(bindings, complete=False, reason=reason)
        for line_no, line in enumerate(raw.splitlines(), start=1):
            if not line.strip():
                continue
            try:
                event = _loads_authority_json_object(line)
            except (json.JSONDecodeError, UnicodeDecodeError, ValueError) as exc:
                reason = f"event journal line {line_no} corrupt: {type(exc).__name__}: {exc}"
                _record_persistence_issue(
                    self.events_path,
                    reason=reason,
                    record_kind="events",
                    identity=f"line:{line_no}",
                    status=LOAD_CORRUPT,
                )
                return _DurableEventJournalLoad(bindings, complete=False, reason=reason)
            event_name = event.get("event")
            request_id = str(event.get("request_id", "") or "").strip()
            data = event.get("data")
            if not isinstance(event_name, str) or not request_id:
                reason = f"event journal line {line_no} missing required event identity"
                _record_persistence_issue(
                    self.events_path,
                    reason=reason,
                    record_kind="events",
                    identity=f"line:{line_no}",
                    status=LOAD_CORRUPT,
                )
                return _DurableEventJournalLoad(bindings, complete=False, reason=reason)
            if event_name != "QUEUED":
                continue
            if not isinstance(data, dict) or data.get("idempotency_key") != idempotency_key:
                continue
            if request_id and request_id not in seen:
                seen.add(request_id)
                admission_binding = data.get("admission_binding")
                if isinstance(admission_binding, dict):
                    bindings.append(dict(admission_binding))
                else:
                    bindings.append(
                        {
                            "idempotency_key": idempotency_key,
                            "canonical_request_id": request_id,
                        }
                    )
        return _DurableEventJournalLoad(bindings)

    def _admitted_request_ids_for_idempotency_key_locked(self, idempotency_key: str) -> list[str]:
        return [
            str(binding.get("canonical_request_id", ""))
            for binding in self._admission_bindings_for_idempotency_key_locked(
                idempotency_key
            ).bindings
            if str(binding.get("canonical_request_id", ""))
        ]

    def _validate_request_matches_admission_binding_locked(
        self,
        request: DurableRemoteRequest,
        admission_binding: dict[str, Any],
        *,
        matches: list[DurableRemoteRequest],
    ) -> None:
        if "payload_digest" not in admission_binding:
            return
        self._canonicalize_request_payload_identity(request)
        try:
            self._validate_binding_identity(
                self._idempotency_binding(request),
                admission_binding,
                reason="idempotency admission binding drift",
            )
        except ValueError:
            self._fail_ambiguous_idempotency_recovery_locked(
                matches,
                event="IDEMPOTENCY_ADMISSION_BINDING_DRIFT_REJECTED",
            )
            raise

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
            if current.lifecycle_state in {
                "QUEUED",
                "DELIVERED",
                "CLAIMED",
                "RUNNING",
                "CANCEL_REQUESTED",
            }:
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
        index_load = self._load_idempotency_index_record(req.idempotency_key)
        canonical_request_id = (
            str((index_load.data or {}).get("canonical_request_id", "")) if index_load.valid else ""
        )
        if index_load.status == LOAD_READ_ERROR:
            return self._mark_noncanonical_request_locked(
                req,
                canonical_request_id="idempotency_index_unavailable",
                event=event,
            )
        if canonical_request_id:
            try:
                canonical = self._validate_index_matches_admission_evidence_locked(
                    idempotency_key=req.idempotency_key,
                    canonical_request_id=canonical_request_id,
                )
            except ValueError:
                current = self._get_request_raw(req.request_id)
                return current or self._mark_noncanonical_request_locked(
                    req,
                    canonical_request_id="ambiguous_idempotency_recovery",
                    event=event,
                )
            canonical_request_id = canonical.request_id
        if not canonical_request_id:
            matches = self._requests_by_idempotency_key_locked(req.idempotency_key)
            if matches:
                try:
                    recovered = self._canonical_request_from_admission_evidence_locked(
                        req.idempotency_key,
                        matches=matches,
                    )
                except ValueError:
                    current = self._get_request_raw(req.request_id)
                    return current or self._mark_noncanonical_request_locked(
                        req,
                        canonical_request_id="ambiguous_idempotency_recovery",
                        event=event,
                    )
                if recovered is None:
                    return None
                canonical_request_id = recovered.request_id
                self._write_idempotency_index(recovered)
            elif index_load.status == LOAD_CORRUPT:
                return self._mark_noncanonical_request_locked(
                    req,
                    canonical_request_id="idempotency_index_corrupt",
                    event=event,
                )
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
        return self._canonical_request_from_admission_evidence_locked(
            idempotency_key,
            matches=matches,
        )

    def _requests_by_idempotency_key_locked(
        self, idempotency_key: str
    ) -> list[DurableRemoteRequest]:
        matches: list[DurableRemoteRequest] = []
        for path in sorted(self.requests_dir.glob("*.json")):
            loaded = self._load_request_record(path.stem)
            if not loaded.valid or loaded.request is None:
                continue
            req = loaded.request
            if req.idempotency_key == idempotency_key:
                matches.append(req)
        matches.sort(key=self._request_sort_key)
        return matches

    def _request_corruption_scope_for_idempotency_key_locked(
        self, idempotency_key: str
    ) -> _IdempotencyCorruptionScope:
        key = _normalized_idempotency_key(idempotency_key)
        same_key = self._request_corruption_fence_exists(key)
        unknown_scope = self._request_corruption_fence_exists(UNKNOWN_IDEMPOTENCY_SCOPE)
        read_error = False
        reasons: list[str] = []
        for path in sorted(self.requests_dir.glob("*.json")):
            loaded = self._load_request_record(path.stem)
            if loaded.valid and loaded.request is not None:
                try:
                    self._validate_canonical_request_material(loaded.request)
                except ValueError as exc:
                    recovered_key = self._record_request_corruption_fence(
                        loaded.path,
                        reason=f"request canonical material invalid: {exc}",
                        data=loaded.data,
                        request=loaded.request,
                    )
                    if recovered_key == key:
                        same_key = True
                    elif not recovered_key or recovered_key == UNKNOWN_IDEMPOTENCY_SCOPE:
                        unknown_scope = True
                    reasons.append(f"{path.name}:request canonical material invalid: {exc}")
                    continue
                continue
            if loaded.status == LOAD_READ_ERROR:
                read_error = True
            recovered_key = self._negative_request_corruption_identity(
                loaded.path,
                data=loaded.data,
                request=loaded.request,
            )
            if recovered_key == key:
                same_key = True
            elif not recovered_key and loaded.unavailable:
                unknown_scope = True
            if loaded.reason:
                reasons.append(f"{path.name}:{loaded.reason}")
        return _IdempotencyCorruptionScope(
            same_key=same_key,
            unknown_scope=unknown_scope,
            read_error=read_error,
            reasons=tuple(reasons),
        )

    def _canonical_request_from_admission_evidence_locked(
        self,
        idempotency_key: str,
        *,
        matches: list[DurableRemoteRequest] | None = None,
    ) -> DurableRemoteRequest | None:
        matches = (
            matches
            if matches is not None
            else self._requests_by_idempotency_key_locked(idempotency_key)
        )
        by_id = {req.request_id: req for req in matches}
        admission_evidence = self._admission_bindings_for_idempotency_key_locked(idempotency_key)
        if admission_evidence.incomplete:
            self._fail_ambiguous_idempotency_recovery_locked(
                matches,
                event="IDEMPOTENCY_ADMISSION_EVIDENCE_INCOMPLETE",
            )
            raise ValueError(
                f"idempotency admission evidence incomplete: {admission_evidence.reason}"
            )
        admission_bindings = admission_evidence.bindings
        admitted = [
            str(binding.get("canonical_request_id", ""))
            for binding in admission_bindings
            if str(binding.get("canonical_request_id", ""))
        ]
        if len(admitted) > 1:
            self._fail_ambiguous_idempotency_recovery_locked(
                matches,
                event="AMBIGUOUS_IDEMPOTENCY_ADMISSION_EVENTS_REJECTED",
            )
            raise ValueError("ambiguous idempotency recovery: multiple admission events")
        if admitted:
            if len(matches) > 1:
                self._fail_ambiguous_idempotency_recovery_locked(
                    matches,
                    event="AMBIGUOUS_IDEMPOTENCY_RECOVERY_REJECTED",
                )
                raise ValueError("ambiguous idempotency recovery: multiple request records")
            canonical = by_id.get(admitted[0])
            if canonical is None:
                self._fail_ambiguous_idempotency_recovery_locked(
                    matches,
                    event="IDEMPOTENCY_ADMISSION_EVENT_MISSING_REQUEST_REJECTED",
                )
                raise ValueError("idempotency admission event points to missing request")
            self._validate_request_matches_admission_binding_locked(
                canonical,
                admission_bindings[0],
                matches=matches,
            )
            invalid = self._reject_invalid_canonical_material_locked(
                canonical,
                event="IDEMPOTENCY_RECOVERY_REJECTED",
            )
            if invalid is not None:
                raise ValueError("durable request canonical material invalid")
            return canonical
        if len(matches) == 1:
            invalid = self._reject_invalid_canonical_material_locked(
                matches[0],
                event="IDEMPOTENCY_RECOVERY_REJECTED",
            )
            if invalid is not None:
                raise ValueError("durable request canonical material invalid")
            return matches[0]
        if len(matches) > 1:
            self._fail_ambiguous_idempotency_recovery_locked(
                matches,
                event="AMBIGUOUS_IDEMPOTENCY_RECOVERY_REJECTED",
            )
            raise ValueError("ambiguous idempotency recovery: multiple request records")
        return None

    def _ensure_fresh_idempotency_absence_proven_locked(
        self,
        idempotency_key: str,
        *,
        matches: list[DurableRemoteRequest] | None = None,
    ) -> None:
        corruption = self._request_corruption_scope_for_idempotency_key_locked(idempotency_key)
        if corruption.blocks_fresh_authority:
            if matches:
                self._fail_ambiguous_idempotency_recovery_locked(
                    matches,
                    event="IDEMPOTENCY_REQUEST_CORRUPTION_FENCED",
                )
            raise ValueError(corruption.reason(idempotency_key))

    def _validate_index_matches_admission_evidence_locked(
        self,
        *,
        idempotency_key: str,
        canonical_request_id: str,
        matches: list[DurableRemoteRequest] | None = None,
    ) -> DurableRemoteRequest:
        matches = (
            matches
            if matches is not None
            else self._requests_by_idempotency_key_locked(idempotency_key)
        )
        by_id = {req.request_id: req for req in matches}
        admission_evidence = self._admission_bindings_for_idempotency_key_locked(idempotency_key)
        if admission_evidence.incomplete:
            self._fail_ambiguous_idempotency_recovery_locked(
                matches,
                event="IDEMPOTENCY_ADMISSION_EVIDENCE_INCOMPLETE",
            )
            raise ValueError(
                f"idempotency admission evidence incomplete: {admission_evidence.reason}"
            )
        admission_bindings = admission_evidence.bindings
        admitted = [
            str(binding.get("canonical_request_id", ""))
            for binding in admission_bindings
            if str(binding.get("canonical_request_id", ""))
        ]
        if len(admitted) > 1:
            self._fail_ambiguous_idempotency_recovery_locked(
                matches,
                event="AMBIGUOUS_IDEMPOTENCY_ADMISSION_EVENTS_REJECTED",
            )
            raise ValueError("ambiguous idempotency recovery: multiple admission events")
        if admitted and admitted[0] != canonical_request_id:
            self._fail_ambiguous_idempotency_recovery_locked(
                matches,
                event="IDEMPOTENCY_INDEX_CONFLICT_REJECTED",
            )
            raise ValueError("idempotency index conflicts with admission evidence")
        if not admitted and len(matches) > 1:
            self._fail_ambiguous_idempotency_recovery_locked(
                matches,
                event="AMBIGUOUS_IDEMPOTENCY_RECOVERY_REJECTED",
            )
            raise ValueError("ambiguous idempotency recovery: multiple request records")
        canonical = by_id.get(canonical_request_id)
        if canonical is None:
            raise ValueError("idempotency index points to missing canonical request")
        invalid = self._reject_invalid_canonical_material_locked(
            canonical,
            event="IDEMPOTENCY_INDEX_RECOVERY_REJECTED",
        )
        if invalid is not None:
            raise ValueError("durable request canonical material invalid")
        index_load = self._load_idempotency_index_record(idempotency_key)
        index = dict(index_load.data or {}) if index_load.valid else {}
        if index:
            self._canonicalize_request_payload_identity(canonical)
            try:
                self._validate_binding_identity(
                    self._idempotency_binding(canonical),
                    index,
                    reason="idempotency index binding drift",
                )
            except ValueError:
                self._fail_ambiguous_idempotency_recovery_locked(
                    matches,
                    event="IDEMPOTENCY_INDEX_BINDING_DRIFT_REJECTED",
                )
                raise
        if admission_bindings:
            self._validate_request_matches_admission_binding_locked(
                canonical,
                admission_bindings[0],
                matches=matches,
            )
            if "payload_digest" in admission_bindings[0]:
                try:
                    self._validate_binding_identity(
                        index,
                        admission_bindings[0],
                        reason="idempotency index binding drift",
                    )
                except ValueError:
                    self._fail_ambiguous_idempotency_recovery_locked(
                        matches,
                        event="IDEMPOTENCY_INDEX_BINDING_DRIFT_REJECTED",
                    )
                    raise
        return canonical

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
            loaded = self._load_request_record(path.stem)
            if not loaded.valid or loaded.request is None:
                continue
            duplicate = loaded.request
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
            index_load = self._load_idempotency_index_record(req.idempotency_key)
            index = dict(index_load.data or {}) if index_load.valid else {}
            if index:
                canonical_request_id = str(index.get("canonical_request_id", ""))
                try:
                    canonical = self._validate_index_matches_admission_evidence_locked(
                        idempotency_key=req.idempotency_key,
                        canonical_request_id=canonical_request_id,
                    )
                except ValueError:
                    return False
                canonical_request_id = canonical.request_id
                if canonical_request_id != req.request_id:
                    self._quarantine_duplicate_idempotency_record_locked(
                        req,
                        canonical_request_id=canonical_request_id,
                    )
                    return False
                return True
            if index_load.status == LOAD_READ_ERROR:
                return False
            try:
                matches = self._requests_by_idempotency_key_locked(req.idempotency_key)
                recovered = self._canonical_request_from_admission_evidence_locked(
                    req.idempotency_key,
                    matches=matches,
                )
            except ValueError:
                return False
            if recovered is None:
                corruption = self._request_corruption_scope_for_idempotency_key_locked(
                    req.idempotency_key
                )
                if corruption.blocks_fresh_authority:
                    return False
                return index_load.status != LOAD_CORRUPT
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
        index_load = self._load_idempotency_index_record(incoming.idempotency_key)
        index = dict(index_load.data or {}) if index_load.valid else {}
        if not index:
            matches = self._requests_by_idempotency_key_locked(incoming.idempotency_key)
            recovered = self._canonical_request_from_admission_evidence_locked(
                incoming.idempotency_key,
                matches=matches,
            )
            if recovered is None:
                if index_load.status == LOAD_ABSENT:
                    self._ensure_fresh_idempotency_absence_proven_locked(
                        incoming.idempotency_key,
                        matches=matches,
                    )
                    return None
                raise ValueError(
                    f"idempotency index {index_load.status.lower()} for key "
                    f"{incoming.idempotency_key}"
                )
            self._validate_idempotent_replay(recovered, incoming)
            with self._request_lock(recovered.request_id):
                current = self._get_request_raw(recovered.request_id) or recovered
                if index_load.status == LOAD_READ_ERROR:
                    raise ValueError("idempotency index read error")
                self._write_idempotency_index(current)
                result = self._record_idempotent_replay_locked(current, incoming)
            self._quarantine_noncanonical_idempotency_records_locked(
                incoming.idempotency_key,
                canonical_request_id=result.request_id,
            )
            return result
        canonical_request_id = str(index.get("canonical_request_id", ""))
        matches = self._requests_by_idempotency_key_locked(incoming.idempotency_key)
        existing = self._validate_index_matches_admission_evidence_locked(
            idempotency_key=incoming.idempotency_key,
            canonical_request_id=canonical_request_id,
            matches=matches,
        )
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
        self._validate_canonical_request_material(request, strict_payload_digest=False)
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
                        "admission_binding": self._idempotency_binding(request),
                    },
                )
                return request

    def _get_request_raw(self, request_id: str) -> DurableRemoteRequest | None:
        loaded = self._load_request_record(request_id)
        return loaded.request if loaded.valid else None

    def get_request(self, request_id: str) -> DurableRemoteRequest | None:
        req = self._get_request_raw(request_id)
        if req is None:
            return None
        if (
            req.lifecycle_state not in TERMINAL_STATES
            and req.lifecycle_state not in RECOVERY_STATES
        ):
            with self._request_lock(request_id):
                current = self._get_request_raw(request_id)
                if current is None:
                    return None
                invalid = self._reject_invalid_canonical_material_locked(
                    current,
                    event="GET_REQUEST",
                )
                if invalid is not None:
                    return invalid
                req = current
        if (
            req.lifecycle_state not in TERMINAL_STATES
            and req.lifecycle_state not in RECOVERY_STATES
        ):
            if not self._request_is_canonical_for_idempotency(req):
                return self._get_request_raw(request_id)
        if (
            req.lifecycle_state not in TERMINAL_STATES
            and not self._recovery_due(req)
            and self._load_result_record(request_id).status == LOAD_ABSENT
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

    def _residue_reconciliation_reminder_due_locked(
        self,
        req: DurableRemoteRequest,
        *,
        current: float,
    ) -> bool:
        observation = req.diagnostics.get("residue_reconciliation_observation")
        if not isinstance(observation, dict):
            return True
        next_event_after = observation.get("next_event_after")
        try:
            return current >= float(next_event_after)
        except (TypeError, ValueError):
            return True

    def _record_residue_reconciliation_pending_locked(
        self,
        req: DurableRemoteRequest,
        *,
        current: float,
        reason: str,
    ) -> DurableRemoteRequest:
        req.diagnostics["residue_reconciliation_pending"] = True
        observation = req.diagnostics.get("residue_reconciliation_observation")
        if not isinstance(observation, dict):
            observation = {
                "first_observed_at": current,
                "event_count": 0,
                "check_count": 0,
            }
            req.diagnostics["residue_reconciliation_observation"] = observation
        observation["last_checked_at"] = current
        observation["check_count"] = int(observation.get("check_count", 0) or 0) + 1
        if not self._residue_reconciliation_reminder_due_locked(req, current=current):
            _atomic_write_json(self._request_path(req.request_id), req.to_dict())
            return req
        event_count = int(observation.get("event_count", 0) or 0) + 1
        delay_s = min(
            _RESIDUE_RECONCILIATION_MAX_REMINDER_S,
            _RESIDUE_RECONCILIATION_INITIAL_REMINDER_S * (2 ** min(event_count - 1, 12)),
        )
        observation["event_count"] = event_count
        observation["last_event_at"] = current
        observation["next_event_after"] = current + delay_s
        observation["next_interval_s"] = delay_s
        observation["reason"] = reason
        self._update_request_locked(
            req,
            "RESIDUE_RECONCILIATION_PENDING",
            event_data={
                "reason": reason,
                "check_count": observation["check_count"],
                "event_count": event_count,
                "next_event_after": observation["next_event_after"],
            },
        )
        return req

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

    def _converge_existing_result_locked(self, req: DurableRemoteRequest) -> DurableRemoteRequest:
        invalid = self._reject_invalid_canonical_material_locked(
            req,
            event="TERMINAL_RESULT_RECOVERY_REJECTED",
        )
        if invalid is not None:
            return invalid
        result_load = self._load_result_record(req.request_id)
        if result_load.status == LOAD_ABSENT:
            return req
        if result_load.unavailable:
            return self._mark_persistence_integrity_failure_locked(
                req,
                event="TERMINAL_RESULT_CORRUPT",
                reason=result_load.reason,
                record_kind="result",
            )
        existing = dict(result_load.data or {})
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
        if (
            existing.get("result_digest") != result_digest
            or existing.get("cleanup_digest") != cleanup_digest
        ):
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
                return self._record_residue_reconciliation_pending_locked(
                    req,
                    current=current,
                    reason="reconciliation_deadline_expired",
                )
            req = self._reconcile_request_locked(
                req,
                reason="reconciliation_deadline_expired",
            )
        return req

    def _maybe_converge_recovery(self, req: DurableRemoteRequest) -> DurableRemoteRequest:
        result_load = self._load_result_record(req.request_id)
        if not self._recovery_due(req) and result_load.status == LOAD_ABSENT:
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
                    if (
                        locked.lifecycle_state in TERMINAL_STATES
                        or locked.lifecycle_state in RECOVERY_STATES
                    ):
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
            invalid = self._reject_invalid_canonical_material_locked(req, event="DELIVERED")
            if invalid is not None:
                return invalid
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
            invalid = self._reject_invalid_canonical_material_locked(req, event="CLAIMED")
            if invalid is not None:
                return invalid
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

    def mark_shell_launch_state(
        self,
        request_id: str,
        *,
        claim_id: str,
        launch_state: str,
        launch_material: dict[str, Any],
    ) -> DurableRemoteRequest:
        """Persist one monotonic shell-launch transition while still CLAIMED."""

        if launch_state not in SHELL_LAUNCH_STATES - {SHELL_LAUNCH_RUNNING}:
            raise ValueError(f"invalid pre-running shell launch state: {launch_state}")
        with self._request_lock(request_id):
            req = self._get_request_raw(request_id)
            if req is None:
                raise KeyError(request_id)
            if req.lifecycle_state in TERMINAL_STATES or req.lifecycle_state in RECOVERY_STATES:
                return req
            if req.lifecycle_state != "CLAIMED" or req.claim_id != claim_id:
                return self._enter_reconciliation(
                    req,
                    reason=(
                        "shell launch state requires exact claimed authority: "
                        f"state={req.lifecycle_state} claim={req.claim_id} incoming={claim_id}"
                    ),
                )
            incoming_identity = dict(launch_material.get("execution_identity") or {})
            existing_identity = dict(req.process_tree.get("execution_identity") or {})
            if not incoming_identity or (
                existing_identity and existing_identity != incoming_identity
            ):
                return self._enter_reconciliation(
                    req,
                    reason="shell launch execution identity mismatch",
                )
            prior_state = str(req.process_tree.get("launch_state", "") or "")
            if prior_state:
                prior_order = _SHELL_LAUNCH_STATE_ORDER.get(prior_state, -1)
                next_order = _SHELL_LAUNCH_STATE_ORDER[launch_state]
                if next_order < prior_order or next_order > prior_order + 1:
                    return self._enter_reconciliation(
                        req,
                        reason=f"non-monotonic shell launch transition {prior_state}->{launch_state}",
                    )
                if next_order == prior_order:
                    if any(
                        req.process_tree.get(key) != value for key, value in launch_material.items()
                    ):
                        return self._enter_reconciliation(
                            req,
                            reason=f"conflicting repeated shell launch state {launch_state}",
                        )
                    return req
            elif launch_state != SHELL_LAUNCH_INTENT_PERSISTED:
                return self._enter_reconciliation(
                    req,
                    reason=f"shell launch began without durable intent: {launch_state}",
                )
            req.process_tree = {
                **req.process_tree,
                **launch_material,
                "launch_state": launch_state,
                "launch_state_updated_at": now_s(),
            }
            self._update_request_locked(req, launch_state)
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
            invalid = self._reject_invalid_canonical_material_locked(req, event="RUNNING")
            if invalid is not None:
                return invalid
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
            if (
                req.lifecycle_state not in TERMINAL_STATES
                and req.lifecycle_state not in RECOVERY_STATES
            ):
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
        existing_result = self._load_result_record(request.request_id)
        if existing_result.unavailable:
            raise ValueError(
                f"refusing to overwrite corrupt result record: {existing_result.reason}"
            )
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
        existing_result = self._load_result_record(req.request_id)
        if existing_result.unavailable:
            self._write_rejected_result_record(
                req,
                claim_id=claim_id,
                state=state,
                result=result,
                cleanup=cleanup,
                reason="canonical_result_corrupt",
            )
            return self._mark_persistence_integrity_failure_locked(
                req,
                event=event or f"{state}_REJECTED_CORRUPT_RESULT",
                reason=existing_result.reason,
                record_kind="result",
            )
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
        invalid = self._reject_invalid_canonical_material_locked(req, event=state)
        if invalid is not None:
            self._write_rejected_result_record(
                invalid,
                claim_id=claim_id,
                state=state,
                result=result,
                cleanup=cleanup,
                reason="canonical_material_invalid",
            )
            return invalid
        existing_result = self._load_result_record(request_id)
        if existing_result.unavailable:
            self._write_rejected_result_record(
                req,
                claim_id=claim_id,
                state=state,
                result=result,
                cleanup=cleanup,
                reason="canonical_result_corrupt",
            )
            return self._mark_persistence_integrity_failure_locked(
                req,
                event="RESULT_PUBLISH_REJECTED_CORRUPT",
                reason=existing_result.reason,
                record_kind="result",
            )
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
            result_load = self._load_result_record(request_id)
            existing = dict(result_load.data or {}) if result_load.valid else {}
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
            req.diagnostics["result_claim_conflict"] = {
                "existing": req.claim_id,
                "incoming": claim_id,
            }
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
        if state in TERMINAL_STATES and (cleanup is None or cleanup.get("process_residue") != []):
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

    def reconcile_request(
        self, request_id: str, *, reason: str = "bounded_reconciliation"
    ) -> DurableRemoteRequest:
        with self._request_lock(request_id):
            req = self._get_request_raw(request_id)
            if req is None:
                raise KeyError(request_id)
            return self._reconcile_request_locked(req, reason=reason)

    def mark_reconciliation_required(
        self,
        request_id: str,
        *,
        reason: str,
        cleanup: dict[str, Any] | None = None,
    ) -> DurableRemoteRequest:
        """Persist an unresolved execution/delivery truth without inventing a terminal state."""
        with self._request_lock(request_id):
            req = self._get_request_raw(request_id)
            if req is None:
                raise KeyError(request_id)
            if req.lifecycle_state in TERMINAL_STATES:
                return req
            if cleanup is not None:
                req.cleanup = dict(cleanup)
            return self._enter_reconciliation(req, reason=reason)

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
            return self._record_residue_reconciliation_pending_locked(
                req,
                current=now_s(),
                reason=reason,
            )
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
        loaded = self._load_result_record(request_id)
        return dict(loaded.data or {}) if loaded.valid else None

    def has_persisted_rejected_result_evidence(
        self,
        request_id: str,
        *,
        claim_id: str,
        state: str,
        result: dict[str, Any],
        cleanup: dict[str, Any],
    ) -> bool:
        for path in self.results_dir.glob(f"{request_id}.rejected-*.json"):
            loaded = _load_json_record(path, record_kind="results", identity=request_id)
            if not loaded.valid:
                continue
            data = dict(loaded.data or {})
            if (
                data.get("request_id") == request_id
                and data.get("claim_id") == claim_id
                and data.get("state") == state
                and data.get("result") == result
                and data.get("cleanup") == cleanup
            ):
                return True
        return False

    def _load_result_delivery_record(self, request_id: str) -> _DurableRecordLoad:
        path = self._result_delivery_path(request_id)
        loaded = _load_json_record(path, record_kind="result_outbox", identity=request_id)
        if not loaded.valid:
            return loaded
        data = dict(loaded.data or {})
        if str(data.get("request_id", "") or "").strip() != request_id:
            reason = "result delivery path/content identity mismatch"
            _record_persistence_issue(
                path,
                reason=reason,
                record_kind="result_outbox",
                identity=request_id,
            )
            return _DurableRecordLoad(LOAD_CORRUPT, path, data=data, reason=reason)
        if str(data.get("delivery_state", "")) not in {
            "PENDING",
            "ACKNOWLEDGED",
            "RECONCILIATION_REQUIRED",
        }:
            reason = "result delivery state invalid"
            _record_persistence_issue(
                path,
                reason=reason,
                record_kind="result_outbox",
                identity=request_id,
            )
            return _DurableRecordLoad(LOAD_CORRUPT, path, data=data, reason=reason)
        if not str(data.get("result_id", "") or "").strip():
            reason = "result delivery identity missing"
            _record_persistence_issue(
                path,
                reason=reason,
                record_kind="result_outbox",
                identity=request_id,
            )
            return _DurableRecordLoad(LOAD_CORRUPT, path, data=data, reason=reason)
        return _DurableRecordLoad(LOAD_VALID, path, data=data)

    def stage_terminal_result_delivery(self, request_id: str) -> dict[str, Any]:
        """Durably stage exact terminal evidence for transport delivery."""
        with self._request_lock(request_id):
            request_load = self._load_request_record(request_id)
            result_load = self._load_result_record(request_id)
            if not request_load.valid or request_load.request is None:
                raise ValueError("terminal result delivery requires a valid request record")
            if not result_load.valid:
                raise ValueError("terminal result delivery requires a valid result record")
            request = request_load.request
            result = dict(result_load.data or {})
            if request.lifecycle_state not in TERMINAL_STATES | RECOVERY_STATES:
                raise ValueError(
                    "terminal result delivery requires terminal or reconciliation state"
                )
            identity = terminal_result_identity(request, result)
            if not identity["claim_id"] or not identity["result_digest"]:
                raise ValueError("terminal result delivery identity is incomplete")

            existing_load = self._load_result_delivery_record(request_id)
            if existing_load.unavailable:
                raise ValueError(
                    f"terminal result delivery record unavailable: {existing_load.reason}"
                )
            if existing_load.valid:
                existing = dict(existing_load.data or {})
                if existing.get("result_id") != identity["result_id"]:
                    raise ValueError("terminal result delivery identity conflict")
                return existing

            now = now_s()
            record = {
                **identity,
                "delivery_state": "PENDING",
                "attempt_count": 0,
                "last_attempt_at": 0.0,
                "next_attempt_at": now,
                "last_error": "",
                "acknowledged_at": 0.0,
                "receipt": {},
                "created_at": now,
                "updated_at": now,
            }
            _atomic_write_json(self._result_delivery_path(request_id), record)
            self._event(request_id, "TERMINAL_RESULT_DELIVERY_PENDING")
            return record

    def pending_terminal_result_deliveries(
        self,
        *,
        current_time: float | None = None,
        limit: int = 8,
    ) -> list[dict[str, Any]]:
        """Discover due terminal deliveries, including records predating the outbox."""
        for path in sorted(self.results_dir.glob("*.json")):
            request_id = path.stem
            if ".rejected-" in request_id:
                continue
            try:
                self.stage_terminal_result_delivery(request_id)
            except (KeyError, ValueError):
                continue

        now = now_s() if current_time is None else current_time
        pending: list[dict[str, Any]] = []
        for path in sorted(self.result_outbox_dir.glob("*.json")):
            loaded = self._load_result_delivery_record(path.stem)
            if not loaded.valid:
                continue
            record = dict(loaded.data or {})
            if record.get("delivery_state") != "PENDING":
                continue
            if float(record.get("next_attempt_at", 0.0) or 0.0) > now:
                continue
            pending.append(record)
            if len(pending) >= max(1, limit):
                break
        return pending

    def record_terminal_result_delivery_attempt(
        self,
        request_id: str,
        *,
        error: str = "",
    ) -> dict[str, Any]:
        with self._request_lock(request_id):
            loaded = self._load_result_delivery_record(request_id)
            if not loaded.valid:
                raise ValueError("terminal result delivery record is not valid")
            record = dict(loaded.data or {})
            if record.get("delivery_state") == "ACKNOWLEDGED":
                return record
            now = now_s()
            prior_attempts = int(record.get("attempt_count", 0) or 0)
            attempts = prior_attempts if error and prior_attempts else prior_attempts + 1
            delay = min(
                _RESULT_DELIVERY_INITIAL_RETRY_S * (2 ** min(attempts - 1, 16)),
                _RESULT_DELIVERY_MAX_RETRY_S,
            )
            record.update(
                {
                    "attempt_count": attempts,
                    "last_attempt_at": now,
                    "next_attempt_at": now + delay,
                    "last_error": error,
                    "updated_at": now,
                }
            )
            _atomic_write_json(self._result_delivery_path(request_id), record)
            return record

    def mark_terminal_result_delivery_acknowledged(
        self,
        request_id: str,
        receipt: dict[str, Any],
    ) -> dict[str, Any]:
        with self._request_lock(request_id):
            loaded = self._load_result_delivery_record(request_id)
            if not loaded.valid:
                raise ValueError("terminal result delivery record is not valid")
            record = dict(loaded.data or {})
            required = {
                "request_id": record.get("request_id"),
                "correlation_id": record.get("correlation_id"),
                "candidate_sha": record.get("candidate_sha"),
                "node_id": record.get("node_id"),
                "claim_id": record.get("claim_id"),
                "state": record.get("state"),
                "result_digest": record.get("result_digest"),
                "result_id": record.get("result_id"),
            }
            mismatches = [key for key, value in required.items() if receipt.get(key) != value]
            if receipt.get("ok") is not True or mismatches:
                raise ValueError(
                    "terminal result receipt identity mismatch"
                    + (f": {','.join(mismatches)}" if mismatches else "")
                )
            now = now_s()
            record.update(
                {
                    "delivery_state": "ACKNOWLEDGED",
                    "acknowledged_at": now,
                    "next_attempt_at": 0.0,
                    "last_error": "",
                    "receipt": dict(receipt),
                    "updated_at": now,
                }
            )
            _atomic_write_json(self._result_delivery_path(request_id), record)
            self._event(request_id, "TERMINAL_RESULT_DELIVERY_ACKNOWLEDGED")
            return record

    def mark_terminal_result_delivery_reconciliation_required(
        self,
        request_id: str,
        *,
        reason: str,
        receipt: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Stop retrying terminal evidence whose canonical receipt conflicts."""
        with self._request_lock(request_id):
            loaded = self._load_result_delivery_record(request_id)
            if not loaded.valid:
                raise ValueError("terminal result delivery record is not valid")
            record = dict(loaded.data or {})
            if record.get("delivery_state") == "ACKNOWLEDGED":
                return record
            now = now_s()
            record.update(
                {
                    "delivery_state": "RECONCILIATION_REQUIRED",
                    "next_attempt_at": 0.0,
                    "last_error": str(reason),
                    "receipt": dict(receipt or {}),
                    "updated_at": now,
                }
            )
            _atomic_write_json(self._result_delivery_path(request_id), record)
            self._event(
                request_id,
                "TERMINAL_RESULT_DELIVERY_RECONCILIATION_REQUIRED",
                {"reason": str(reason)},
            )
            return record

    def terminal_result_delivery_for(self, request_id: str) -> dict[str, Any] | None:
        loaded = self._load_result_delivery_record(request_id)
        return dict(loaded.data or {}) if loaded.valid else None

    def remove_request(self, request_id: str, *, force_terminal: bool = False) -> None:
        current = self.get_request(request_id)
        if (
            current is not None
            and current.lifecycle_state in TERMINAL_STATES
            and not force_terminal
        ):
            raise ValueError("refusing to remove terminal durable request without force_terminal")
        for path in (
            self._request_path(request_id),
            self._result_path(request_id),
            self._result_delivery_path(request_id),
        ):
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
                index_load = self._load_idempotency_index_record(current.idempotency_key)
                index = dict(index_load.data or {}) if index_load.valid else {}
                if index and str(index.get("canonical_request_id", "")) == request_id:
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
