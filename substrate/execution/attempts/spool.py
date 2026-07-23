"""Signed dispatch spool — the ephemeral control-plane→worker transport.

The spool is a TRANSPORT representation ONLY (Amendment v1 clause 3):
``ExecutionAttemptStore`` remains the sole current execution truth. The spool
carries signed dispatch envelopes from the control plane to the run-scoped host
attempt runner and carries results back. Invariants:

- every envelope is HMAC-SHA256 signed with a per-run secret; an unsigned or
  tampered file is quarantined, never executed;
- atomic inbox → inflight ownership (os.replace rename claims a file);
- the model worker subprocess receives NO signing secret;
- spool loss is recoverable — the runner reconstructs pending work from the
  canonical attempt ledger (attempts in DISPATCHED-but-not-terminal state);
- NO operator status is inferred from file presence — the store is the truth.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import logging
import os
import time
from dataclasses import asdict, dataclass, field
from typing import Any

logger = logging.getLogger(__name__)

_INBOX = "inbox"
_INFLIGHT = "inflight"
_PROCESSED = "processed"
_OUTBOX = "outbox"
_QUARANTINE = "quarantine"


@dataclass
class DispatchEnvelope:
    """One signed unit of worker dispatch."""

    dispatch_id: str = ""
    attempt_id: str = ""
    task_id: str = ""
    authorization_ref: str = ""
    package_hash: str = ""
    lease_id: str = ""
    worktree_path: str = ""
    nonce: str = ""
    sequence: int = 0
    created_at: float = field(default_factory=time.time)
    expires_at: float = 0.0
    disallowed_tools: list[str] = field(default_factory=list)
    max_turns: int = 30
    timeout_seconds: int = 600
    payload_hash: str = ""  # sha256 of the sealed ModelExecutionPackage

    def signable(self) -> str:
        d = asdict(self)
        return json.dumps(d, sort_keys=True, separators=(",", ":"))


def _sign(payload: str, secret: str) -> str:
    return hmac.new(secret.encode(), payload.encode(), hashlib.sha256).hexdigest()


def _verify(payload: str, secret: str, signature: str) -> bool:
    expected = _sign(payload, secret)
    return hmac.compare_digest(expected, signature)


class DispatchSpool:
    """File-backed signed dispatch spool rooted at a run's state dir."""

    def __init__(self, root_dir: str, secret: str) -> None:
        self._root = root_dir
        self._secret = secret
        for sub in (_INBOX, _INFLIGHT, _PROCESSED, _OUTBOX, _QUARANTINE):
            os.makedirs(os.path.join(self._root, sub), exist_ok=True)

    def _dir(self, sub: str) -> str:
        return os.path.join(self._root, sub)

    # ── Control plane: enqueue a signed dispatch ─────────────────────────────

    def enqueue(self, envelope: DispatchEnvelope) -> str:
        payload = envelope.signable()
        record = {"envelope": asdict(envelope), "signature": _sign(payload, self._secret)}
        name = f"{envelope.sequence:08d}-{envelope.dispatch_id}.json"
        tmp = os.path.join(self._dir(_INBOX), f".{name}.tmp")
        final = os.path.join(self._dir(_INBOX), name)
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(record, f, separators=(",", ":"))
        os.replace(tmp, final)
        return name

    # ── Worker runner: claim + verify ────────────────────────────────────────

    def claim_next(self) -> tuple[str, DispatchEnvelope] | None:
        """Atomically claim the oldest inbox dispatch into inflight, verifying
        its signature. A bad signature is quarantined and skipped. Returns
        (claim_token, envelope) or None if the inbox is empty."""
        try:
            names = sorted(
                n for n in os.listdir(self._dir(_INBOX))
                if n.endswith(".json") and not n.startswith(".")
            )
        except FileNotFoundError:
            return None
        for name in names:
            src = os.path.join(self._dir(_INBOX), name)
            claimed = os.path.join(self._dir(_INFLIGHT), name)
            try:
                os.replace(src, claimed)  # atomic ownership claim
            except FileNotFoundError:
                continue  # another runner claimed it
            try:
                with open(claimed, encoding="utf-8") as f:
                    record = json.load(f)
            except Exception:
                self._quarantine(name, "unreadable")
                continue
            envelope = DispatchEnvelope(**record.get("envelope", {}))
            signature = record.get("signature", "")
            if not _verify(envelope.signable(), self._secret, signature):
                self._quarantine(name, "bad signature")
                continue
            if envelope.expires_at and time.time() >= envelope.expires_at:
                self._quarantine(name, "expired")
                continue
            return name, envelope
        return None

    def _quarantine(self, name: str, reason: str) -> None:
        for sub in (_INFLIGHT, _INBOX):
            p = os.path.join(self._dir(sub), name)
            if os.path.exists(p):
                dst = os.path.join(self._dir(_QUARANTINE), f"{name}.{reason.replace(' ', '_')}")
                try:
                    os.replace(p, dst)
                except FileNotFoundError:
                    pass
                logger.warning("[DispatchSpool] quarantined %s: %s", name, reason)
                return

    def complete(self, claim_token: str, result: dict[str, Any]) -> None:
        """Move an inflight claim to processed and write the signed result to
        the outbox for the control-plane poller."""
        inflight = os.path.join(self._dir(_INFLIGHT), claim_token)
        if os.path.exists(inflight):
            os.replace(inflight, os.path.join(self._dir(_PROCESSED), claim_token))
        payload = json.dumps(result, sort_keys=True, separators=(",", ":"))
        record = {"result": result, "signature": _sign(payload, self._secret)}
        name = f"result-{claim_token}"
        tmp = os.path.join(self._dir(_OUTBOX), f".{name}.tmp")
        final = os.path.join(self._dir(_OUTBOX), name)
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(record, f, separators=(",", ":"))
        os.replace(tmp, final)

    # ── Control plane: consume signed results ────────────────────────────────

    def drain_results(self) -> list[dict[str, Any]]:
        """Return verified results from the outbox and remove them. A tampered
        result is quarantined, never consumed."""
        out: list[dict[str, Any]] = []
        try:
            names = sorted(
                n for n in os.listdir(self._dir(_OUTBOX))
                if n.startswith("result-") and not n.startswith(".")
            )
        except FileNotFoundError:
            return out
        for name in names:
            p = os.path.join(self._dir(_OUTBOX), name)
            try:
                with open(p, encoding="utf-8") as f:
                    record = json.load(f)
            except Exception:
                self._quarantine_outbox(name, "unreadable")
                continue
            result = record.get("result", {})
            payload = json.dumps(result, sort_keys=True, separators=(",", ":"))
            if not _verify(payload, self._secret, record.get("signature", "")):
                self._quarantine_outbox(name, "bad signature")
                continue
            out.append(result)
            os.remove(p)
        return out

    def _quarantine_outbox(self, name: str, reason: str) -> None:
        p = os.path.join(self._dir(_OUTBOX), name)
        if os.path.exists(p):
            os.replace(p, os.path.join(self._dir(_QUARANTINE), f"{name}.{reason.replace(' ', '_')}"))
            logger.warning("[DispatchSpool] quarantined result %s: %s", name, reason)

    # ── Recovery ─────────────────────────────────────────────────────────────

    def pending_dispatch_ids(self) -> set[str]:
        """Dispatch ids currently in inbox or inflight (for reconciliation).
        The store — NOT this set — is the source of truth; this only helps the
        runner reconstruct after a spool loss."""
        ids: set[str] = set()
        for sub in (_INBOX, _INFLIGHT):
            try:
                for n in os.listdir(self._dir(sub)):
                    if n.endswith(".json") and not n.startswith("."):
                        ids.add(n.rsplit("-", 1)[-1].removesuffix(".json"))
            except FileNotFoundError:
                pass
        return ids


__all__ = ["DispatchEnvelope", "DispatchSpool"]
