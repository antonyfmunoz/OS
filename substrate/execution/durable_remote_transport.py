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
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any
from uuid import uuid4


TERMINAL_STATES = frozenset(
    {"SUCCEEDED", "FAILED", "CANCELLED", "EXPIRED", "RECONCILIATION_REQUIRED"}
)
ACTIVE_STATES = frozenset({"QUEUED", "CLAIMED", "RUNNING", "CANCEL_REQUESTED"})


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
    claim_id: str = ""
    lease_expires_at: float = 0.0
    process_tree: dict[str, Any] = field(default_factory=dict)
    result_digest: str = ""
    cancellation_requested_at: float = 0.0
    cleanup: dict[str, Any] = field(default_factory=dict)
    diagnostics: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.idempotency_key:
            self.idempotency_key = self.request_id
        if not self.payload_digest:
            self.payload_digest = sha256_json(
                {
                    "operation_type": self.operation_type,
                    "capability": self.capability,
                    "params": self.params,
                    "candidate_sha": self.candidate_sha,
                    "correlation_id": self.correlation_id,
                    "authority_id": self.authority_id,
                }
            )

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
            "claim_id": self.claim_id,
            "lease_expires_at": self.lease_expires_at,
            "process_tree": self.process_tree,
            "result_digest": self.result_digest,
            "cancellation_requested_at": self.cancellation_requested_at,
            "cleanup": self.cleanup,
            "diagnostics": self.diagnostics,
        }

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
            claim_id=str(data.get("claim_id", "")),
            lease_expires_at=float(data.get("lease_expires_at", 0.0) or 0.0),
            process_tree=dict(data.get("process_tree") or {}),
            result_digest=str(data.get("result_digest", "")),
            cancellation_requested_at=float(data.get("cancellation_requested_at", 0.0) or 0.0),
            cleanup=dict(data.get("cleanup") or {}),
            diagnostics=dict(data.get("diagnostics") or {}),
        )


class DurableRemoteStore:
    """File-backed canonical store for one controller or node spool."""

    def __init__(self, root: Path | str | None = None) -> None:
        self.root = Path(root) if root is not None else default_controller_root()
        self.requests_dir = self.root / "requests"
        self.results_dir = self.root / "results"
        self.events_path = self.root / "events.jsonl"
        self.requests_dir.mkdir(parents=True, exist_ok=True)
        self.results_dir.mkdir(parents=True, exist_ok=True)

    def _request_path(self, request_id: str) -> Path:
        return self.requests_dir / f"{request_id}.json"

    def _result_path(self, request_id: str) -> Path:
        return self.results_dir / f"{request_id}.json"

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

    def put_request(self, request: DurableRemoteRequest) -> DurableRemoteRequest:
        existing = self.get_request(request.request_id)
        if existing is not None:
            if existing.idempotency_key != request.idempotency_key:
                raise ValueError("request_id exists with different idempotency key")
            if existing.payload_digest != request.payload_digest:
                raise ValueError("request_id exists with different payload digest")
            return existing
        _atomic_write_json(self._request_path(request.request_id), request.to_dict())
        self._event(request.request_id, "QUEUED", {"node_id": request.node_id})
        return request

    def get_request(self, request_id: str) -> DurableRemoteRequest | None:
        data = _read_json(self._request_path(request_id))
        if not data:
            return None
        return DurableRemoteRequest.from_dict(data)

    def update_request(self, request: DurableRemoteRequest, event: str = "") -> None:
        _atomic_write_json(self._request_path(request.request_id), request.to_dict())
        if event:
            self._event(request.request_id, event, {"state": request.lifecycle_state})

    def requests_for_node(self, node_id: str) -> list[DurableRemoteRequest]:
        out: list[DurableRemoteRequest] = []
        for path in sorted(self.requests_dir.glob("*.json")):
            req = DurableRemoteRequest.from_dict(_read_json(path))
            if req.node_id == node_id:
                out.append(req)
        return out

    def deliverable_for_node(self, node_id: str, *, limit: int = 1) -> list[DurableRemoteRequest]:
        current = now_s()
        chosen: list[DurableRemoteRequest] = []
        for req in self.requests_for_node(node_id):
            if req.expires_at and current > req.expires_at and req.lifecycle_state in ACTIVE_STATES:
                req.lifecycle_state = "EXPIRED"
                self.update_request(req, "EXPIRED")
            if req.lifecycle_state in {"QUEUED", "CLAIMED", "RUNNING", "CANCEL_REQUESTED"}:
                chosen.append(req)
            if len(chosen) >= limit:
                break
        return chosen

    def mark_claimed(
        self,
        request_id: str,
        *,
        claim_id: str,
        lease_seconds: int = 300,
        process_tree: dict[str, Any] | None = None,
    ) -> DurableRemoteRequest:
        req = self.get_request(request_id)
        if req is None:
            raise KeyError(request_id)
        if req.lifecycle_state in TERMINAL_STATES:
            return req
        if req.claim_id and req.claim_id != claim_id:
            req.lifecycle_state = "RECONCILIATION_REQUIRED"
            req.diagnostics["claim_conflict"] = {"existing": req.claim_id, "incoming": claim_id}
            self.update_request(req, "RECONCILIATION_REQUIRED")
            return req
        req.claim_id = claim_id
        req.lease_expires_at = now_s() + lease_seconds
        req.lifecycle_state = "CLAIMED"
        if process_tree is not None:
            req.process_tree = process_tree
        self.update_request(req, "CLAIMED")
        return req

    def mark_running(
        self, request_id: str, *, claim_id: str, process_tree: dict[str, Any] | None = None
    ) -> DurableRemoteRequest:
        req = self.get_request(request_id)
        if req is None:
            raise KeyError(request_id)
        if req.claim_id and req.claim_id != claim_id:
            req.lifecycle_state = "RECONCILIATION_REQUIRED"
            self.update_request(req, "RECONCILIATION_REQUIRED")
            return req
        if req.lifecycle_state not in TERMINAL_STATES:
            req.claim_id = claim_id
            req.lifecycle_state = "RUNNING"
            if process_tree is not None:
                req.process_tree = process_tree
            self.update_request(req, "RUNNING")
        return req

    def request_cancel(self, request_id: str) -> DurableRemoteRequest:
        req = self.get_request(request_id)
        if req is None:
            raise KeyError(request_id)
        if req.lifecycle_state not in TERMINAL_STATES:
            req.lifecycle_state = "CANCEL_REQUESTED"
            req.cancellation_requested_at = now_s()
            self.update_request(req, "CANCEL_REQUESTED")
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
        req = self.get_request(request_id)
        if req is None:
            raise KeyError(request_id)
        if req.claim_id and req.claim_id != claim_id:
            req.lifecycle_state = "RECONCILIATION_REQUIRED"
            req.diagnostics["result_claim_conflict"] = {"existing": req.claim_id, "incoming": claim_id}
            self.update_request(req, "RECONCILIATION_REQUIRED")
            return req
        if req.lifecycle_state in TERMINAL_STATES:
            existing = self.result_for(request_id)
            incoming_digest = sha256_json(result)
            if (
                existing
                and existing.get("state") == state
                and existing.get("result_digest") == incoming_digest
            ):
                return req
            existing_state = req.lifecycle_state
            req.lifecycle_state = "RECONCILIATION_REQUIRED"
            req.diagnostics["terminal_result_conflict"] = {
                "existing_state": existing_state,
                "incoming_state": state,
            }
            self.update_request(req, "RECONCILIATION_REQUIRED")
            return req
        if req.lifecycle_state in {"CANCEL_REQUESTED", "EXPIRED"} and state == "SUCCEEDED":
            req.lifecycle_state = "RECONCILIATION_REQUIRED"
            req.diagnostics["late_success_rejected"] = True
            self.update_request(req, "RECONCILIATION_REQUIRED")
            return req
        req.claim_id = claim_id
        req.lifecycle_state = state
        req.result_digest = sha256_json(result)
        if cleanup is not None:
            req.cleanup = cleanup
        _atomic_write_json(
            self._result_path(request_id),
            {
                "request_id": request_id,
                "claim_id": claim_id,
                "state": state,
                "result": result,
                "result_digest": req.result_digest,
                "published_at": now_s(),
            },
        )
        self.update_request(req, state)
        return req

    def result_for(self, request_id: str) -> dict[str, Any] | None:
        data = _read_json(self._result_path(request_id))
        return data or None

    def remove_request(self, request_id: str) -> None:
        for path in (self._request_path(request_id), self._result_path(request_id)):
            try:
                path.unlink()
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
        idempotency_key=idempotency_key or request_id,
        expires_at=now_s() + ttl_seconds,
    )
