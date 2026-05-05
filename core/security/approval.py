"""
approval.py — Approval queue for high-risk actions.

Flow (matches the objective in the spec):

    ActionSystem.execute()
        → SecurityContext.authorize_action()
        → RBAC says "needs_approval" for this (role, op, risk)
        → approval.ApprovalQueue.create_request(...)
        → caller polls, waits, or returns a "pending" decision
        → a human (or a higher-authority token) calls
          queue.approve(request_id, approver_token) or .reject(...)
        → the original caller sees the status flip and proceeds

Data layout
-----------
    data/security/approvals/pending.jsonl          — append-only queue
    data/security/approvals/<req_id>.json          — authoritative per-request
                                                     state (status flips here)
    data/security/approvals/history.jsonl          — append-only decisions

Why file-backed
---------------
- Survives process restarts. The orchestrator can crash and the pending
  request is still there when it comes back.
- Readable from the operator CLI. `cat pending.jsonl` shows the queue.
- Same shape as the rest of EOS's JSONL data surfaces.

Design notes
------------
- A request is PENDING until someone calls `approve` or `reject`.
- `wait_for_decision(request_id, timeout)` polls the per-request JSON.
  Timeout returns None — caller decides whether to treat that as "denied"
  or "defer until later".
- Approvals are single-decision. Once APPROVED or REJECTED, a request
  is terminal.
- Self-approval is blocked: the `approver` in `approve()` must be
  different from the `requester` recorded on the request, unless an
  explicit `allow_self=True` is passed (admin-level override).
"""

from __future__ import annotations

import json
import time
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Iterable

_SECURITY_DIR = Path("/opt/OS/data/security")
_APPROVALS_DIR = _SECURITY_DIR / "approvals"
_PENDING_PATH = _APPROVALS_DIR / "pending.jsonl"
_HISTORY_PATH = _APPROVALS_DIR / "history.jsonl"


class ApprovalStatus(str, Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    EXPIRED = "expired"
    CANCELLED = "cancelled"


class ApprovalAction(str, Enum):
    APPROVE = "approve"
    REJECT = "reject"
    CANCEL = "cancel"


# ─── Data ───────────────────────────────────────────────────────────────────


@dataclass
class ApprovalRequest:
    """A request for permission to perform a high-risk action."""

    request_id: str
    requester: str  # user_id of whoever initiated
    requester_role: str
    action_type: str  # e.g. "edit_file"
    target: str  # e.g. "eos_ai/memory.py"
    operation: str  # OperationKind value
    risk: str  # RiskTier value
    reason: str = ""
    agent: str = ""  # optional agent context
    environment: str = "production"
    status: ApprovalStatus = ApprovalStatus.PENDING
    created_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    expires_at: str = ""  # ISO; empty means no expiry
    approver: str = ""
    decision_at: str = ""
    decision_reason: str = ""
    metadata: dict = field(default_factory=dict)

    def as_dict(self) -> dict:
        d = asdict(self)
        d["status"] = self.status.value
        return d

    @classmethod
    def from_dict(cls, d: dict) -> "ApprovalRequest":
        return cls(
            request_id=d["request_id"],
            requester=d.get("requester", ""),
            requester_role=d.get("requester_role", ""),
            action_type=d.get("action_type", ""),
            target=d.get("target", ""),
            operation=d.get("operation", ""),
            risk=d.get("risk", ""),
            reason=d.get("reason", ""),
            agent=d.get("agent", ""),
            environment=d.get("environment", "production"),
            status=ApprovalStatus(d.get("status", "pending")),
            created_at=d.get("created_at", datetime.now(timezone.utc).isoformat()),
            expires_at=d.get("expires_at", ""),
            approver=d.get("approver", ""),
            decision_at=d.get("decision_at", ""),
            decision_reason=d.get("decision_reason", ""),
            metadata=d.get("metadata", {}),
        )


class ApprovalError(Exception):
    """Raised for illegal approval operations (self-approve, terminal flip, etc)."""


# ─── Queue ──────────────────────────────────────────────────────────────────


class ApprovalQueue:
    """File-backed approval queue.

    One instance per process is fine. All reads replay from disk; all
    writes are idempotent appends to the history log plus an atomic
    write of the per-request JSON.
    """

    def __init__(
        self,
        *,
        approvals_dir: Path | None = None,
    ) -> None:
        self.dir = approvals_dir or _APPROVALS_DIR
        self.pending_path = self.dir / "pending.jsonl"
        self.history_path = self.dir / "history.jsonl"
        self.dir.mkdir(parents=True, exist_ok=True)
        self.pending_path.touch(exist_ok=True)
        self.history_path.touch(exist_ok=True)

    # ─── Create ────────────────────────────────────────────────────────────

    def create_request(
        self,
        *,
        requester: str,
        requester_role: str,
        action_type: str,
        target: str,
        operation: str,
        risk: str,
        reason: str = "",
        agent: str = "",
        environment: str = "production",
        ttl_seconds: int | None = None,
        metadata: dict | None = None,
    ) -> ApprovalRequest:
        request_id = _new_id()
        now_iso = datetime.now(timezone.utc).isoformat()
        expires_at = ""
        if ttl_seconds and ttl_seconds > 0:
            exp_epoch = time.time() + ttl_seconds
            expires_at = datetime.fromtimestamp(exp_epoch, tz=timezone.utc).isoformat()
        req = ApprovalRequest(
            request_id=request_id,
            requester=requester,
            requester_role=requester_role,
            action_type=action_type,
            target=target,
            operation=operation,
            risk=risk,
            reason=reason,
            agent=agent,
            environment=environment,
            status=ApprovalStatus.PENDING,
            created_at=now_iso,
            expires_at=expires_at,
            metadata=metadata or {},
        )
        self._write_state(req)
        self._append(self.pending_path, req.as_dict())
        return req

    # ─── Decide ────────────────────────────────────────────────────────────

    def approve(
        self,
        request_id: str,
        *,
        approver: str,
        approver_role: str,
        can_approve_risk: bool,
        reason: str = "",
        allow_self: bool = False,
    ) -> ApprovalRequest:
        """Flip a pending request to APPROVED.

        Caller must supply `can_approve_risk` — the SecurityContext
        computes this from RBAC. The queue itself does not know about
        roles; it just enforces self-approval rules and terminal state.
        """
        return self._decide(
            request_id,
            approver=approver,
            approver_role=approver_role,
            new_status=ApprovalStatus.APPROVED,
            reason=reason,
            allow_self=allow_self,
            can_approve_risk=can_approve_risk,
        )

    def reject(
        self,
        request_id: str,
        *,
        approver: str,
        approver_role: str,
        reason: str = "",
    ) -> ApprovalRequest:
        """Flip a pending request to REJECTED. Any role can reject a
        request that has authority — or more strictly, any role can
        reject a request made against them. We allow rejection broadly
        because rejecting is never destructive."""
        return self._decide(
            request_id,
            approver=approver,
            approver_role=approver_role,
            new_status=ApprovalStatus.REJECTED,
            reason=reason,
            allow_self=True,  # you can always withdraw your own request as a reject
            can_approve_risk=True,
        )

    def cancel(self, request_id: str, *, requester: str) -> ApprovalRequest:
        """The original requester withdraws a pending request."""
        req = self.get(request_id)
        if req is None:
            raise ApprovalError(f"no such request: {request_id}")
        if req.status != ApprovalStatus.PENDING:
            raise ApprovalError(f"request {request_id} is already {req.status.value}")
        if req.requester != requester:
            raise ApprovalError(
                f"only requester may cancel ({req.requester} != {requester})"
            )
        req.status = ApprovalStatus.CANCELLED
        req.decision_at = datetime.now(timezone.utc).isoformat()
        req.approver = requester
        req.decision_reason = "cancelled by requester"
        self._write_state(req)
        self._append(self.history_path, req.as_dict())
        return req

    def _decide(
        self,
        request_id: str,
        *,
        approver: str,
        approver_role: str,
        new_status: ApprovalStatus,
        reason: str,
        allow_self: bool,
        can_approve_risk: bool,
    ) -> ApprovalRequest:
        req = self.get(request_id)
        if req is None:
            raise ApprovalError(f"no such request: {request_id}")
        if req.status != ApprovalStatus.PENDING:
            raise ApprovalError(f"request {request_id} is already {req.status.value}")
        if self._is_expired(req):
            req.status = ApprovalStatus.EXPIRED
            self._write_state(req)
            self._append(self.history_path, req.as_dict())
            raise ApprovalError(f"request {request_id} expired before decision")
        if not allow_self and approver == req.requester:
            raise ApprovalError(
                f"self-approval blocked: {approver} cannot approve own request"
            )
        if new_status == ApprovalStatus.APPROVED and not can_approve_risk:
            raise ApprovalError(
                f"role {approver_role} lacks authority to approve risk={req.risk}"
            )

        req.status = new_status
        req.approver = approver
        req.decision_at = datetime.now(timezone.utc).isoformat()
        req.decision_reason = reason or ""
        self._write_state(req)
        self._append(self.history_path, req.as_dict())
        return req

    # ─── Read ──────────────────────────────────────────────────────────────

    def get(self, request_id: str) -> ApprovalRequest | None:
        path = self._state_path(request_id)
        if not path.exists():
            return None
        try:
            return ApprovalRequest.from_dict(json.loads(path.read_text()))
        except Exception:
            return None

    def list_pending(self) -> list[ApprovalRequest]:
        out: list[ApprovalRequest] = []
        for path in sorted(self.dir.glob("*.json")):
            try:
                req = ApprovalRequest.from_dict(json.loads(path.read_text()))
            except Exception:
                continue
            if req.status == ApprovalStatus.PENDING and not self._is_expired(req):
                out.append(req)
        out.sort(key=lambda r: r.created_at)
        return out

    def wait_for_decision(
        self,
        request_id: str,
        *,
        timeout: float = 0.0,
        poll_interval: float = 1.0,
    ) -> ApprovalRequest | None:
        """Block until the request is decided or `timeout` elapses.

        `timeout=0` → return immediately (non-blocking check).
        Returns None on timeout. Returns the request on any terminal state.
        """
        deadline = time.time() + timeout if timeout > 0 else 0
        while True:
            req = self.get(request_id)
            if req is None:
                return None
            if req.status != ApprovalStatus.PENDING:
                return req
            if self._is_expired(req):
                req.status = ApprovalStatus.EXPIRED
                req.decision_at = datetime.now(timezone.utc).isoformat()
                req.decision_reason = "ttl expired"
                self._write_state(req)
                self._append(self.history_path, req.as_dict())
                return req
            if deadline == 0 or time.time() >= deadline:
                return None if deadline > 0 else req
            time.sleep(poll_interval)

    def iter_history(self) -> Iterable[ApprovalRequest]:
        for row in self._iter_rows(self.history_path):
            try:
                yield ApprovalRequest.from_dict(row)
            except Exception:
                continue

    # ─── Internal ──────────────────────────────────────────────────────────

    def _state_path(self, request_id: str) -> Path:
        return self.dir / f"{request_id}.json"

    def _write_state(self, req: ApprovalRequest) -> None:
        path = self._state_path(req.request_id)
        tmp = path.with_suffix(".tmp")
        tmp.write_text(json.dumps(req.as_dict(), indent=2))
        tmp.replace(path)

    def _append(self, path: Path, row: dict) -> None:
        with path.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(row) + "\n")

    def _iter_rows(self, path: Path) -> Iterable[dict]:
        if not path.exists():
            return
        with path.open("r", encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                try:
                    yield json.loads(line)
                except json.JSONDecodeError:
                    continue

    def _is_expired(self, req: ApprovalRequest) -> bool:
        if not req.expires_at:
            return False
        try:
            exp = datetime.fromisoformat(req.expires_at)
        except ValueError:
            return False
        return datetime.now(timezone.utc) >= exp


def _new_id() -> str:
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    return f"ar-{stamp}-{uuid.uuid4().hex[:6]}"


__all__ = [
    "ApprovalAction",
    "ApprovalError",
    "ApprovalQueue",
    "ApprovalRequest",
    "ApprovalStatus",
]
