"""
audit.py — Append-only audit log with hash-chain integrity.

Every security-relevant event is recorded as a JSONL row that carries:

    - timestamp (UTC ISO8601)
    - user / agent / role
    - action_type / target / risk
    - operation / environment / approval_chain
    - outcome (allowed | denied | pending | error)
    - prev_hash (hex sha256 of the previous row's canonical JSON)
    - hash (hex sha256 of this row's canonical JSON including prev_hash)

Why a hash chain
----------------
- Tampering with a row breaks every subsequent hash → `verify_chain()`
  detects it in O(n).
- We don't need blockchain-grade strength. We need "did an operator
  edit this file to hide an action" detection. That's sha256 + chain.

Canonical form
--------------
The hash input is `json.dumps(row, sort_keys=True, separators=(",", ":"))`
EXCLUDING the `hash` field but INCLUDING `prev_hash`. This is stable
across Python versions and re-writes.

Data layout
-----------
    data/security/audit.jsonl         — the chain
"""

from __future__ import annotations

import hashlib
import json
import time
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable

_SECURITY_DIR = Path("/opt/OS/data/security")
_AUDIT_PATH = _SECURITY_DIR / "audit.jsonl"

GENESIS_HASH = "0" * 64


@dataclass
class AuditEvent:
    """One row in the audit chain.

    The `hash` and `prev_hash` are populated by AuditLog on write.
    Callers never set them directly.
    """

    event_id: str = ""
    timestamp: str = ""
    user: str = ""
    agent: str = ""
    role: str = ""
    action: str = ""  # "edit_file", "authenticate", "approve", ...
    target: str = ""
    operation: str = ""  # OperationKind value
    risk: str = ""  # RiskTier value
    environment: str = ""
    outcome: str = ""  # "allowed" | "denied" | "pending" | "error"
    reason: str = ""
    approval_chain: list[dict] = field(default_factory=list)
    metadata: dict = field(default_factory=dict)
    prev_hash: str = ""
    hash: str = ""

    def as_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict) -> "AuditEvent":
        return cls(
            event_id=d.get("event_id", ""),
            timestamp=d.get("timestamp", ""),
            user=d.get("user", ""),
            agent=d.get("agent", ""),
            role=d.get("role", ""),
            action=d.get("action", ""),
            target=d.get("target", ""),
            operation=d.get("operation", ""),
            risk=d.get("risk", ""),
            environment=d.get("environment", ""),
            outcome=d.get("outcome", ""),
            reason=d.get("reason", ""),
            approval_chain=list(d.get("approval_chain", [])),
            metadata=dict(d.get("metadata", {})),
            prev_hash=d.get("prev_hash", ""),
            hash=d.get("hash", ""),
        )


# ─── Log ────────────────────────────────────────────────────────────────────


class AuditLog:
    """Append-only hash-chained log.

    Single-writer semantics are expected. Multiple writers still produce
    a valid chain as long as the append is atomic (POSIX `write(2)` on
    a JSONL line is), but readers may see interleaved events. The chain
    still verifies end-to-end.
    """

    def __init__(self, *, path: Path | None = None) -> None:
        self.path = path or _AUDIT_PATH
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.touch(exist_ok=True)

    # ─── Write ─────────────────────────────────────────────────────────────

    def record(
        self,
        *,
        user: str = "",
        agent: str = "",
        role: str = "",
        action: str,
        target: str = "",
        operation: str = "",
        risk: str = "",
        environment: str = "",
        outcome: str,
        reason: str = "",
        approval_chain: list[dict] | None = None,
        metadata: dict | None = None,
    ) -> AuditEvent:
        """Append a new event, chained to the previous tip."""
        prev = self._tail_hash()
        event = AuditEvent(
            event_id=_new_event_id(),
            timestamp=datetime.now(timezone.utc).isoformat(),
            user=user,
            agent=agent,
            role=role,
            action=action,
            target=target,
            operation=operation,
            risk=risk,
            environment=environment,
            outcome=outcome,
            reason=reason,
            approval_chain=list(approval_chain or []),
            metadata=dict(metadata or {}),
            prev_hash=prev,
        )
        event.hash = _hash_row(event.as_dict())
        with self.path.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(event.as_dict()) + "\n")
        return event

    # ─── Read ──────────────────────────────────────────────────────────────

    def read_all(self) -> list[AuditEvent]:
        return list(self._iter_events())

    def tail(self, n: int = 50) -> list[AuditEvent]:
        events = list(self._iter_events())
        return events[-n:]

    def search(
        self,
        *,
        user: str | None = None,
        action: str | None = None,
        outcome: str | None = None,
        since: str | None = None,
    ) -> list[AuditEvent]:
        out: list[AuditEvent] = []
        for ev in self._iter_events():
            if user and ev.user != user:
                continue
            if action and ev.action != action:
                continue
            if outcome and ev.outcome != outcome:
                continue
            if since and ev.timestamp < since:
                continue
            out.append(ev)
        return out

    # ─── Integrity ─────────────────────────────────────────────────────────

    def verify_chain(self) -> tuple[bool, str]:
        """Walk the chain and verify every row.

        Returns (ok, detail). On success detail is "N events, chain ok".
        On failure detail points at the first broken row.
        """
        prev = GENESIS_HASH
        count = 0
        for ev in self._iter_events():
            count += 1
            if ev.prev_hash != prev:
                return (
                    False,
                    f"row {count} ({ev.event_id}): prev_hash mismatch "
                    f"(expected {prev[:12]}…, got {ev.prev_hash[:12]}…)",
                )
            expected = _hash_row(ev.as_dict())
            if ev.hash != expected:
                return (
                    False,
                    f"row {count} ({ev.event_id}): hash mismatch "
                    f"(expected {expected[:12]}…, got {ev.hash[:12]}…)",
                )
            prev = ev.hash
        return True, f"{count} events, chain ok"

    # ─── Internal ──────────────────────────────────────────────────────────

    def _tail_hash(self) -> str:
        last: str = GENESIS_HASH
        if not self.path.exists():
            return last
        with self.path.open("rb") as fh:
            fh.seek(0, 2)  # SEEK_END
            size = fh.tell()
            if size == 0:
                return last
            # Read back up to 8KB to find the last newline.
            chunk = min(8192, size)
            fh.seek(-chunk, 2)
            buf = fh.read().decode("utf-8", errors="replace")
        lines = [ln for ln in buf.strip().splitlines() if ln.strip()]
        if not lines:
            return last
        try:
            row = json.loads(lines[-1])
            return row.get("hash", GENESIS_HASH) or GENESIS_HASH
        except json.JSONDecodeError:
            return GENESIS_HASH

    def _iter_events(self) -> Iterable[AuditEvent]:
        if not self.path.exists():
            return
        with self.path.open("r", encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                try:
                    yield AuditEvent.from_dict(json.loads(line))
                except json.JSONDecodeError:
                    continue


# ─── Hashing ────────────────────────────────────────────────────────────────


def _hash_row(row: dict) -> str:
    payload = {k: v for k, v in row.items() if k != "hash"}
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _new_event_id() -> str:
    return f"ev-{int(time.time() * 1000)}-{uuid.uuid4().hex[:6]}"


__all__ = [
    "AuditEvent",
    "AuditLog",
    "GENESIS_HASH",
]
