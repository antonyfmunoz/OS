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
_CONSUMED = "consumed"  # durable anti-replay ledger (one marker per dispatch)


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
    # ── Governance authority carried across the transport (finding F-2) ──────
    # The sealed package's ``governance_constraints`` — including the
    # ``writable_path_scope=`` declaration that IS the worker's write authority.
    # Before this existed, the runner rebuilt a 4-attribute stand-in package on
    # the far side of the spool, so the scope was minted correctly by
    # ``compile_attempt_package`` and then DISCARDED in transit. The launcher's
    # fail-closed guard then refused every real dispatch: the barrier was
    # mechanically correct and mechanically unreachable.
    #
    # These fields are inside ``asdict(self)``, so they are covered by the
    # envelope HMAC automatically — a scope cannot be widened in transit without
    # invalidating the signature, and the worker never holds the secret.
    governance_constraints: list[str] = field(default_factory=list)
    # The canonical instruction body + context, carried so the far side renders
    # the SAME prompt the control plane compiled rather than inventing one.
    role_instructions: str = ""
    operation_instructions: str = ""
    ordered_context: list[dict[str, Any]] = field(default_factory=list)
    operation_identity: dict[str, Any] = field(default_factory=dict)
    verification_requirements: list[str] = field(default_factory=list)

    def signable(self) -> str:
        d = asdict(self)
        return json.dumps(d, sort_keys=True, separators=(",", ":"))


def _governance_defect(envelope: DispatchEnvelope) -> str:
    """Reason this envelope's governance authority is unusable, or "" if usable.

    Finding F-2. The transport must not deliver an envelope whose write authority
    cannot be enforced. This is a SEMANTIC check layered on top of authenticity
    (HMAC) and freshness (nonce): a correctly-signed envelope carrying no
    enforceable scope is still refused, because the alternative — running it — is
    exactly the default-open behaviour the barrier exists to eliminate.

    It reuses the launcher's canonical parser (``_sealed_writable_scope``) rather
    than re-deriving the meaning of ``writable_path_scope=``, so the transport
    gate and the execution gate can never disagree about what a scope IS. An
    explicitly EMPTY scope is valid (the zero-write verifier lane); only a
    missing or unparseable one is a defect.
    """
    from substrate.execution.attempts.field_task_scope import ScopeResolutionError
    from substrate.execution.attempts.scope_contract import sealed_writable_scope

    class _View:
        governance_constraints = list(envelope.governance_constraints or [])

    try:
        scope = sealed_writable_scope(_View())
    except ScopeResolutionError as exc:
        return str(exc)
    if scope is None:
        return "no writable_path_scope= constraint present"
    return ""


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
        for sub in (_INBOX, _INFLIGHT, _PROCESSED, _OUTBOX, _QUARANTINE, _CONSUMED):
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
            # STAMP THE CLAIM TIME. os.replace preserves the INBOX mtime, and
            # ``recover_stale_inflight`` measures staleness as now - mtime. An
            # envelope that merely WAITED in the inbox longer than the recovery
            # threshold was therefore stale the instant it was claimed, so the
            # very next recovery sweep re-queued it while its worker was still
            # running: two live dispatches of ONE Attempt against ONE lease
            # worktree, and duplicate billed worker quota.
            # Staleness must measure how long THIS claim has been held, not how
            # long the work waited to be picked up. This is the invariant the
            # ``expires_at`` docstring already states: "once a worker atomically
            # claims an envelope it must never expire underneath the running
            # worker". Recorded via the runner heartbeat below as well.
            try:
                os.utime(claimed, None)  # now = claim instant
            except OSError as exc:
                # NEW-3: if the stamp fails we are back to the pre-fix CRITICAL —
                # the claim keeps the inbox mtime and the next recovery sweep can
                # re-queue it under a live worker. The degradation mode of a
                # Critical fix must be LOUD, not a debug line: log at ERROR and
                # refuse the claim rather than proceed on an unstamped one. The
                # envelope stays in inflight and is recovered normally.
                logger.error(
                    "[DispatchSpool] could not stamp claim %s (%s) — refusing the "
                    "claim; an unstamped claim can be recovered under a live worker",
                    name, exc,
                )
                continue
            # PARSE **AND** SCHEMA-CONSTRUCT INSIDE THE QUARANTINE BOUNDARY.
            # DispatchEnvelope(**record) used to sit OUTSIDE this try, so a
            # record that was valid JSON but schema-invalid (unknown key, wrong
            # type) raised TypeError straight out of claim_next() — killing the
            # claim loop instead of quarantining one bad file. The record was
            # already moved to inflight by then, so it was neither executed nor
            # quarantined: it poisoned every later poll. A malformed
            # authority-bearing record must be preserved and set aside, never
            # normalized, retried, or allowed to escape.
            try:
                with open(claimed, encoding="utf-8") as f:
                    record = json.load(f)
                envelope = DispatchEnvelope(**record.get("envelope", {}))
            except Exception as exc:  # noqa: BLE001 - unreadable OR schema-invalid
                self._quarantine(name, f"unreadable or schema-invalid: {exc}")
                continue
            signature = record.get("signature", "")
            if not _verify(envelope.signable(), self._secret, signature):
                self._quarantine(name, "bad signature")
                continue
            if envelope.expires_at and time.time() >= envelope.expires_at:
                self._quarantine(name, "expired")
                continue
            # ANTI-REPLAY. The envelope carries a per-dispatch ``nonce`` whose
            # own comment says "must not reset on restart" — but nothing ever
            # checked it, so an envelope COPIED back into the inbox verified
            # cleanly (the signature covers the original fields) and was
            # re-executed: duplicate billed worker quota and duplicate mutations
            # in the lease worktree (adversarial-review HIGH). Signature proves
            # authenticity, never freshness. The consumed set is durable so a
            # runner restart cannot forget it.
            if not self._consume_nonce(envelope):
                self._quarantine(name, "replayed dispatch (nonce already consumed)")
                continue
            # GOVERNANCE VALIDATION (finding F-2). Authenticity and freshness are
            # now proven; this proves the envelope actually CARRIES enforceable
            # write authority. An envelope whose scope is missing or malformed is
            # not a lesser dispatch to run permissively — it is an unenforceable
            # one, and running it is precisely the failure the barrier exists to
            # prevent. Quarantine (never normalize, never default-open).
            problem = _governance_defect(envelope)
            if problem:
                self._quarantine(name, f"governance constraints unusable: {problem}")
                continue
            return name, envelope
        return None

    def _consume_nonce(self, envelope: DispatchEnvelope) -> bool:
        """Record this dispatch as consumed. False if it was already consumed.

        Keyed on ``dispatch_id`` + ``nonce`` so neither a resent id nor a
        recycled nonce alone can pass. Durable (one file per consumed dispatch)
        because an in-memory set would forget across the runner restarts this
        spool is explicitly designed to survive.
        """
        nonce = f"{getattr(envelope, 'dispatch_id', '')}:{getattr(envelope, 'nonce', '')}"
        if nonce == ":":
            return False  # an unidentifiable dispatch is never replay-safe
        consumed_dir = self._dir(_CONSUMED)
        os.makedirs(consumed_dir, exist_ok=True)
        safe = hashlib.sha256(nonce.encode("utf-8")).hexdigest()
        marker = os.path.join(consumed_dir, f"{safe}.json")
        try:
            # O_EXCL is the atomic test-and-set: the first claimer creates it,
            # every later claim of the same dispatch fails with FileExistsError.
            fd = os.open(marker, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
        except FileExistsError:
            return False
        try:
            os.write(fd, json.dumps({"dispatch_id": envelope.dispatch_id, "at": time.time()}).encode())
        finally:
            os.close(fd)
        return True

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

    def heartbeat_claim(self, claim_token: str) -> bool:
        """Mark a claim as STILL LIVE. Returns False if the claim is gone.

        Staleness is measured from the inflight file's mtime, so a worker that
        legitimately runs longer than the recovery threshold would otherwise be
        declared abandoned and have its envelope re-queued underneath it. The
        claimant calls this periodically; a claim that stops beating is the only
        kind recovery may reclaim. Liveness, not elapsed time, is the signal.
        """
        path = os.path.join(self._dir(_INFLIGHT), claim_token)
        try:
            os.utime(path, None)
            return True
        except OSError:
            return False

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
                    # VERIFY BEFORE RE-SIGNING (independent review HIGH-2).
                    # This used to re-sign whatever was on disk, so an attacker
                    # with spool filesystem access could widen the scope in an
                    # inflight record, wait for recovery, and have the spool mint
                    # a VALID signature over the tampered envelope — laundering
                    # unauthorized authority through the recovery path. The HMAC
                    # is sound everywhere else; this was the one place it was
                    # applied to unverified input.
                    #
                    # Recovery may refresh a CLAIM DEADLINE. It may not bless a
                    # record it has not first authenticated, and it re-signs from
                    # the VERIFIED envelope object with only `expires_at`
                    # replaced — never from the raw dict — so a field the
                    # attacker added cannot ride along.
                    existing = record.get("signature", "")
                    verified = DispatchEnvelope(**env)
                    if not _verify(verified.signable(), self._secret, existing):
                        # `_quarantine` already searches inflight then inbox.
                        self._quarantine(
                            name,
                            "inflight record failed signature verification at recovery "
                            "(tampered while claimed) — refusing to re-sign",
                        )
                        continue
                    verified.expires_at = now + max(60.0, older_than_seconds)
                    record["envelope"] = asdict(verified)
                    record["signature"] = _sign(verified.signable(), self._secret)
                    tmp = path + ".tmp"
                    with open(tmp, "w", encoding="utf-8") as f:
                        json.dump(record, f, separators=(",", ":"))
                    os.replace(tmp, path)
            except Exception as exc:  # noqa: BLE001
                logger.debug("[DispatchSpool] could not refresh %s: %s", name, exc)
            try:
                # AUTHORIZED re-claim: release the anti-replay marker so the
                # recovered envelope can be claimed once more. This is what
                # separates RECOVERY from REPLAY — recovery is performed by the
                # spool itself on an abandoned claim, whereas a replay is an
                # unauthorized copy that never passed through here. Without this
                # release, crash recovery would strand real work behind the
                # replay guard.
                self._release_nonce_from_record(path)
            except Exception as exc:  # noqa: BLE001
                logger.debug("[DispatchSpool] nonce release failed for %s: %s", name, exc)
            try:
                os.replace(path, os.path.join(self._dir(_INBOX), name))
                recovered.append(name)
                logger.warning("[DispatchSpool] recovered stale inflight %s", name)
            except FileNotFoundError:
                continue
        return recovered

    def _release_nonce_from_record(self, path: str) -> None:
        """Drop the consumed-nonce marker for the envelope stored at ``path``."""
        with open(path, encoding="utf-8") as f:
            record = json.load(f)
        env = DispatchEnvelope(**record.get("envelope", {}))
        nonce = f"{env.dispatch_id}:{env.nonce}"
        if nonce == ":":
            return
        marker = os.path.join(
            self._dir(_CONSUMED), f"{hashlib.sha256(nonce.encode('utf-8')).hexdigest()}.json"
        )
        try:
            os.remove(marker)
        except FileNotFoundError:
            pass

    def drop_inflight_for_attempt(self, attempt_id: str) -> list[str]:
        """Reconcile spool ownership when an attempt terminalizes (C-2).

        Moves every INBOX or INFLIGHT envelope whose SIGNED payload names exactly
        this ``attempt_id`` into quarantine, so a dead attempt leaves no dangling
        dispatch the runner could later claim and execute.

        Guarantees:
        - matches the attempt_id inside the VERIFIED envelope, never a filename;
        - an unreadable or badly-signed envelope is QUARANTINED (fail closed) and
          counted as reconciled — a tampered envelope must never be left claimable;
        - moves are atomic (os.replace) and idempotent — a second call finds
          nothing left and returns [];
        - returns the exact list of envelope identities reconciled
          (``dispatch_id`` when resolvable, else the filename).

        Returns the identities reconciled. Raises only on an unexpected OS error,
        which the caller records as a spool-reconcile failure.
        """
        if not attempt_id:
            return []
        reconciled: list[str] = []
        for sub in (_INBOX, _INFLIGHT):
            try:
                names = sorted(
                    n
                    for n in os.listdir(self._dir(sub))
                    if n.endswith(".json") and not n.startswith(".")
                )
            except FileNotFoundError:
                continue
            for name in names:
                path = os.path.join(self._dir(sub), name)
                try:
                    with open(path, encoding="utf-8") as f:
                        record = json.load(f)
                except FileNotFoundError:
                    continue  # claimed/moved concurrently
                except Exception:
                    # Unreadable envelope: fail closed — quarantine it so it can
                    # never be claimed, and count it as reconciled.
                    self._quarantine(name, "unreadable-on-reconcile")
                    reconciled.append(name)
                    continue
                envelope = DispatchEnvelope(**record.get("envelope", {}))
                signature = record.get("signature", "")
                if not _verify(envelope.signable(), self._secret, signature):
                    # A tampered envelope must never survive reconciliation.
                    self._quarantine(name, "bad-signature-on-reconcile")
                    reconciled.append(envelope.dispatch_id or name)
                    continue
                if envelope.attempt_id != attempt_id:
                    continue  # a sibling attempt's envelope — never touch it
                dst = os.path.join(self._dir(_QUARANTINE), f"{name}.terminalized-{attempt_id}")
                try:
                    os.replace(path, dst)
                    reconciled.append(envelope.dispatch_id or name)
                except FileNotFoundError:
                    continue  # moved concurrently
        return reconciled

    @staticmethod
    def _reason_slug(reason: str) -> str:
        """A filesystem-safe, bounded slug for a quarantine reason (NEW-1).

        The reason used to be interpolated into the destination FILENAME with
        only spaces replaced. Once the B5 fix started embedding the raw
        exception text, a malformed record could steer its own quarantine path:
        ``DispatchEnvelope(**record)`` puts the attacker-supplied KEY NAME
        verbatim into the TypeError message, so a key containing ``/`` produced
        a destination whose parent directory does not exist. ``os.replace`` then
        raised FileNotFoundError, which was silently swallowed — the function
        logged "quarantined" and returned having done nothing. The record cycled
        inflight↔inbox forever and the operator's evidence trail was LOST,
        contradicting the whole point of quarantining it.
        """
        safe = "".join(c if (c.isalnum() or c in "-_.") else "_" for c in reason)
        return safe[:120] or "unspecified"

    def _quarantine(self, name: str, reason: str) -> None:
        for sub in (_INFLIGHT, _INBOX):
            p = os.path.join(self._dir(sub), name)
            if os.path.exists(p):
                os.makedirs(self._dir(_QUARANTINE), exist_ok=True)
                dst = os.path.join(
                    self._dir(_QUARANTINE), f"{name}.{self._reason_slug(reason)}"
                )
                try:
                    os.replace(p, dst)
                except OSError as exc:
                    # NEVER claim a quarantine that did not happen. The old code
                    # swallowed FileNotFoundError and logged success anyway, so a
                    # record that was never set aside looked handled. Fall back to
                    # a name that cannot fail, and if even that fails, say so.
                    fallback = os.path.join(
                        self._dir(_QUARANTINE), f"{name}.quarantine_reason_unencodable"
                    )
                    try:
                        os.replace(p, fallback)
                    except OSError as exc2:
                        logger.error(
                            "[DispatchSpool] FAILED to quarantine %s (%s / %s) — "
                            "record left in place, NOT quarantined",
                            name, exc, exc2,
                        )
                        return
                    logger.warning(
                        "[DispatchSpool] quarantined %s under a fallback name (%s): %s",
                        name, exc, reason,
                    )
                    return
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
            # Same slug rule as _quarantine (NEW-1): a reason must never be able
            # to steer the destination path.
            os.makedirs(self._dir(_QUARANTINE), exist_ok=True)
            os.replace(
                p, os.path.join(self._dir(_QUARANTINE), f"{name}.{self._reason_slug(reason)}")
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
