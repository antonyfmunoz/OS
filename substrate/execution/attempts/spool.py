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
    # The lease's AUTHORIZED base commit. The worker computes its artifact set as
    # `<base>..HEAD`, so without this it fell back to "HEAD" — and `HEAD..HEAD`
    # is empty by definition, meaning the worker reported zero files and zero
    # commits for genuinely successful work. Same root cause as the verifier's
    # missing-snapshot_ref defect: a diff with no authorized anchor is not a diff.
    base_commit: str = ""
    nonce: str = ""
    sequence: int = 0
    created_at: float = field(default_factory=time.time)
    # CLAIM deadline only (finding C3). This bounds how long an UNCLAIMED
    # envelope may sit in the inbox — it is NOT the execution budget. Once a
    # worker atomically claims an envelope it must never expire underneath the
    # running worker; execution is bounded by ``timeout_seconds`` (the attempt/
    # lease timeout) instead. Setting this to now+timeout_seconds at dispatch is
    # what caused B to be quarantined while A held the whole 600s.
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
                n
                for n in os.listdir(self._dir(_INBOX))
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

    def reap_stale_unclaimed(self, *, now: float | None = None) -> list[str]:
        """Quarantine UNCLAIMED inbox envelopes whose claim deadline has passed.

        Nothing previously reaped the spool: an envelope that expired simply sat
        there until a claim attempt quarantined it, and its attempt stranded in
        DISPATCHED forever, permanently consuming a concurrency slot (finding
        C3). Returns the quarantined file names.
        """
        now = time.time() if now is None else now
        reaped: list[str] = []
        try:
            names = sorted(
                n
                for n in os.listdir(self._dir(_INBOX))
                if n.endswith(".json") and not n.startswith(".")
            )
        except FileNotFoundError:
            return reaped
        for name in names:
            path = os.path.join(self._dir(_INBOX), name)
            try:
                with open(path, encoding="utf-8") as f:
                    record = json.load(f)
                envelope = DispatchEnvelope(**record.get("envelope", {}))
            except Exception:  # noqa: BLE001 - unreadable is its own quarantine reason
                self._quarantine(name, "unreadable")
                reaped.append(name)
                continue
            if envelope.expires_at and now >= envelope.expires_at:
                self._quarantine(name, "expired unclaimed")
                reaped.append(name)
        return reaped

    def recover_stale_inflight(
        self, *, older_than_seconds: float, now: float | None = None
    ) -> list[str]:
        """Return INFLIGHT envelopes abandoned by a crashed worker to the inbox.

        A worker that dies mid-attempt leaves its claim in ``inflight`` with no
        result ever written. Returning it to the inbox lets another worker claim
        it WITHOUT minting a second attempt — the attempt id on the envelope is
        unchanged, so no duplicate active attempt is created. Returns the names
        recovered.
        """
        now = time.time() if now is None else now
        recovered: list[str] = []
        try:
            names = sorted(os.listdir(self._dir(_INFLIGHT)))
        except FileNotFoundError:
            return recovered
        for name in names:
            if not name.endswith(".json") or name.startswith("."):
                continue
            path = os.path.join(self._dir(_INFLIGHT), name)
            try:
                age = now - os.path.getmtime(path)
            except OSError:
                continue
            if age < older_than_seconds:
                continue
            # Clear the stale CLAIM deadline: the envelope already waited once,
            # and re-expiring it immediately would defeat the recovery.
            try:
                with open(path, encoding="utf-8") as f:
                    record = json.load(f)
                env = record.get("envelope", {})
                if env.get("expires_at"):
                    env["expires_at"] = now + max(60.0, older_than_seconds)
                    record["envelope"] = env
                    record["signature"] = _sign(DispatchEnvelope(**env).signable(), self._secret)
                    tmp = path + ".tmp"
                    with open(tmp, "w", encoding="utf-8") as f:
                        json.dump(record, f, separators=(",", ":"))
                    os.replace(tmp, path)
            except Exception as exc:  # noqa: BLE001
                logger.debug("[DispatchSpool] could not refresh %s: %s", name, exc)
            try:
                os.replace(path, os.path.join(self._dir(_INBOX), name))
                recovered.append(name)
                logger.warning("[DispatchSpool] recovered stale inflight %s", name)
            except FileNotFoundError:
                continue
        return recovered

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
                n
                for n in os.listdir(self._dir(_OUTBOX))
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
            os.replace(
                p, os.path.join(self._dir(_QUARANTINE), f"{name}.{reason.replace(' ', '_')}")
            )
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
