"""One idempotent terminalization authority for an ExecutionAttempt (C-2).

Every way an attempt can END must converge on ONE operation. Before this module,
cleanup was scattered: ``LeaseManager.release`` had zero production callers, the
worker destroyed only its own credential home in a ``finally``, and nothing tied
lease release to home destruction to retry admission. The consequence was the
C-2 deadlock: A1 fails → its lease stays ACTIVE → the scheduler mints A2 →
``LeaseManager.acquire`` raises (one active lease per task) → A2 BLOCKED →
re-READY → BLOCKED, forever — while producing the exact observable shape the
qualification expects ("A failed, C blocked, no false Proof") for the wrong
reason.

``terminalize`` is the single authority. It SUPPORTS every terminal condition:

    SUCCEEDED · FAILED · CANCELLED · REVOKED · EXPIRED · verification rejection ·
    worker crash · dispatch abandonment · authorization expiry ·
    security-boundary failure · cleanup failure · qualification teardown

PRODUCTION WIRING (truthful, not aspirational). Today the live pipeline performs
exactly TWO terminal attempt transitions, and BOTH route through this authority:
the control-plane poller calls it on ``succeeded`` and on
``verification_rejected``. Those are the only terminal transitions the run-scoped
pipeline currently makes on an attempt. The remaining reasons (cancellation,
revocation, expiry, dispatch abandonment, worker crash, teardown,
security-boundary failure) are SUPPORTED by this function but their production
call sites do not exist yet — a grant-level REVOKED/INVALIDATED cascade onto
in-flight attempts, and a teardown-time sweep, are Wave 2 follow-ons. This is
stated in the C-2 ledger entry and pinned by a test, so the "eleven paths" are
never mistaken for "eleven wired paths".

Invariant (strict order — each step must complete before the next):

    1. terminalize ONCE          — idempotent; a second call is a verified no-op
    2. persist terminal state    — the attempt reaches its terminal status first
    2b. retain the verified commit (SUCCEEDED only) under a trusted ref, BEFORE
        release — release deletes the worker branch, so this is the last moment
        the commit is reachable
    2c. STOP if retention failed — every step below is destructive, and running
        them after a failed retention DESTROYS the verified commit. Recording the
        error and continuing is not "fail closed": it changes the reporting, not
        the outcome. The lease is deliberately left ACTIVE and the withhold is
        stated on ``result.lease_withheld_reason`` so no consumer mistakes it for
        a release fault and "heals" it (the poller's RV-HIGH-2 healer revokes,
        and revoke also deletes the branch). Truthfully: this DEFERS destruction
        and blocks retry FOR THIS TASK until the retention condition is resolved.
        It does NOT stall the run — the sandbox concurrency slot is freed with the
        branch preserved (see ``_preserve_sandbox_slot``), so unrelated Tasks keep
        being admitted at the production ``max_parallel=2``. The lease itself
        self-heals: ``LeaseManager.expire_stale`` runs every poller cycle and is
        non-destructive, so the lease expires (TTL) with the commit intact.
        Bounded retry of retention before release would avoid the withhold
        entirely and is not implemented.
    3. release / revoke lease     — the lease is no longer ACTIVE
    4. destroy attempt-private home + remove credential material
    5. reconcile spool ownership  — drop any inflight claim for this attempt
    6. permit retry ONLY after the prior lease is no longer active
       (enforced structurally: acquire() already refuses while one is active,
        and terminalization is what makes it inactive)

Cleanup failure is a BLOCKING SECURITY CONDITION, never a warning. If the
credential home cannot be destroyed, ``terminalize`` records the failure on the
result AND raises unless the caller explicitly collects the outcome — a run may
not be reported clean while credential material survives on disk.

This module imports only downward (substrate + same-package).
"""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass, field
from typing import Any

from substrate.execution.attempts.worker_credential_boundary import (
    CredentialBoundaryError,
    assert_no_credential_residue,
    attempt_home_path,
)

logger = logging.getLogger(__name__)

# The complete set of reasons an attempt terminalizes. Every terminal path in
# the system maps to exactly one of these — there is no "other".
TERMINAL_REASONS = frozenset(
    {
        "succeeded",
        "failed",
        "cancelled",
        "revoked",
        "expired",
        "verification_rejected",
        "worker_crash",
        "dispatch_abandoned",
        "authorization_expired",
        "security_boundary_failure",
        "cleanup_failure",
        "teardown",
    }
)


class TerminalizationError(RuntimeError):
    """A terminalization step failed in a way the caller must not ignore.

    Raised specifically for cleanup / credential-residue failures — a run may
    never be reported clean while these are unresolved.
    """


@dataclass
class TerminalizationResult:
    """Truthful, side-effect-free record of one terminalization."""

    attempt_id: str = ""
    task_id: str = ""
    lease_id: str = ""
    reason: str = ""
    already_terminal: bool = False
    lease_released: bool = False
    # Verifier-approved commit pinned under the trusted namespace before the
    # lease was released. "" for every non-SUCCEEDED terminalization.
    retained_commit: str = ""
    # NON-EMPTY when the lease was DELIBERATELY left active to preserve the only
    # verified commit. A bare ``lease_released == False`` cannot express this: the
    # poller's RV-HIGH-2 healer reads that flag as "release faulted" and force-
    # revokes, which runs cleanup_sandbox → `git branch -D` and destroys the very
    # commit the withhold protected. Measured before this field existed. Any
    # consumer that reacts to an unreleased lease MUST check this first.
    lease_withheld_reason: str = ""
    # True when a withhold freed the sandbox CONCURRENCY SLOT (worktree removed)
    # while PRESERVING the branch, so unrelated Tasks keep running. False on the
    # withhold path means the slot is still held — recoverable, but at
    # max_parallel=2 two such holds stall the run.
    sandbox_slot_freed: bool = False
    home_destroyed: bool = False
    spool_reconciled: bool = False
    credential_residue: list[str] = field(default_factory=list)
    steps: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        """A terminalization is OK only if it FULLY succeeded.

        ANY error fails the contract — lease release failure, missing
        LeaseManager while a lease_id exists, inability to verify home
        destruction, credential residue, spool reconciliation failure, or an
        unknown terminal reason. The earlier version restricted failure to
        SECURITY-prefixed errors, which failed OPEN on every other cleanup fault:
        a lease that could not be released would report ok=True and the run would
        pass while the task's lease stayed ACTIVE. There is no such tier now — an
        error is an error.
        """
        return not self.errors and not self.credential_residue

    def _security_errors(self) -> list[str]:
        return [e for e in self.errors if e.startswith("SECURITY:")]

    def to_dict(self) -> dict[str, Any]:
        return {
            "attempt_id": self.attempt_id,
            "task_id": self.task_id,
            "lease_id": self.lease_id,
            "reason": self.reason,
            "already_terminal": self.already_terminal,
            "lease_released": self.lease_released,
            "retained_commit": self.retained_commit,
            "lease_withheld_reason": self.lease_withheld_reason,
            "sandbox_slot_freed": self.sandbox_slot_freed,
            "home_destroyed": self.home_destroyed,
            "spool_reconciled": self.spool_reconciled,
            "credential_residue": list(self.credential_residue),
            "steps": list(self.steps),
            "errors": list(self.errors),
            "ok": self.ok,
        }


def terminalize(
    *,
    attempt: Any,
    reason: str,
    lease_manager: Any | None = None,
    run_root: str = "",
    spool: Any | None = None,
    raise_on_security_failure: bool = True,
) -> TerminalizationResult:
    """Terminalize one attempt through the single authority.

    ``attempt`` must already be in (or be transitioned by the CALLER to) a
    terminal status: terminalization does NOT decide the verdict, it enacts the
    consequences of one. The caller owns the ledger transition (SUCCEEDED /
    FAILED / CANCELLED); this owns everything downstream of it.

    Idempotent: a second call with the same attempt whose lease is already
    inactive and whose home is already gone is a verified no-op.

    ``run_root`` locates the attempt-private credential home. Without it the home
    cannot be destroyed, which is a security-blocking failure (unless the caller
    disables raising and inspects the result).
    """
    result = TerminalizationResult(
        attempt_id=str(getattr(attempt, "attempt_id", "") or ""),
        task_id=str(getattr(attempt, "task_id", "") or ""),
        lease_id=str(getattr(attempt, "lease_id", "") or ""),
        reason=reason,
    )
    if reason not in TERMINAL_REASONS:
        # Fail closed on an unknown reason: a terminal path we did not enumerate
        # must be made explicit, never silently accepted.
        result.errors.append(f"unknown terminal reason {reason!r}")
        if raise_on_security_failure:
            raise TerminalizationError(result.errors[-1])
        return result

    # (2) The attempt must be terminal before we tear its resources down. We do
    # NOT transition it here (the caller owns the verdict), but we refuse to
    # terminalize a still-live attempt — releasing the lease under a running
    # worker would strand it.
    status = str(getattr(attempt, "status", "") or "")
    is_terminal = getattr(attempt, "is_terminal", None)
    terminal = is_terminal() if callable(is_terminal) else status in _TERMINAL_STATUSES
    if not terminal:
        result.errors.append(
            f"refusing to terminalize {result.attempt_id}: status {status!r} is not terminal"
        )
        if raise_on_security_failure:
            raise TerminalizationError(result.errors[-1])
        return result

    # (2b) RETAIN the verified commit BEFORE the lease is released. Release runs
    # cleanup_sandbox → `git branch -D`, which makes the worker's commit
    # unreachable; a dependent Task leased milliseconds later then branches from
    # a stale HEAD and cannot see content it was told to integrate. Measured in
    # field run 20260805T182714Z-p1: backend SUCCEEDED at …665.640, the
    # integration lease was created at …665.696, and the backend commit no longer
    # existed as an object. Retention is ordered here, and only for a SUCCEEDED
    # attempt, so failed/unverified work is never retained.
    _retain_verified(result, attempt, lease_manager, reason)

    # (2c) A FAILED retention MUST stop here. Recording the error and continuing
    # is not "fail closed" — it changes the reporting, not the outcome: the very
    # next step deletes the worker branch, so the verified commit is destroyed
    # exactly as it was in field run 20260805T182714Z-p1, on the precise trigger
    # (host load → CPU gate refusal) this module exists to survive. Measured:
    # with the gate refusing, result.ok was False AND the commit was gone.
    #
    # The trade is deliberate. Returning early leaves the lease ACTIVE, which
    # blocks retry admission for THIS Task (acquire() refuses a second active
    # lease) until the lease expires or an operator revokes it. It does NOT stall
    # the run: the concurrency slot is freed below with the branch preserved.
    # A blocked Task is recoverable; a destroyed verifier-approved commit is not.
    if _retention_failed(result):
        # EXPLICIT withhold reason. The poller's RV-HIGH-2 healer force-revokes on
        # `lease_released == False`, and revoke() also runs cleanup_sandbox — so a
        # bare boolean would let the healer undo this protection one frame up.
        # Measured: it did. Consumers must key on this field, not the flag.
        result.lease_withheld_reason = (
            f"{LEASE_WITHHELD_RETENTION}{result.errors[-1] if result.errors else 'unknown'}"
        )
        result.steps.append("destructive cleanup SKIPPED — retention failed")
        # Free the CONCURRENCY SLOT without destroying anything. Holding the slot
        # is not what protects the commit — the intact branch ref is. At the
        # production max_parallel=2 two withholds otherwise halt the entire run
        # (measured), and `expire_stale` clears leases but never slots, so the run
        # never recovers. The lease itself stays ACTIVE: retry for THIS Task stays
        # blocked, which is the intended trade.
        _preserve_sandbox_slot(result, lease_manager)
        logger.error(
            "terminalize(%s): retention failed, refusing to release the lease — "
            "releasing would delete the worker branch and destroy the verified "
            "commit. Lease %s stays ACTIVE until revoked/recovered. %s",
            result.attempt_id,
            result.lease_id or "(none)",
            result.errors[-1] if result.errors else "",
        )
        if raise_on_security_failure:
            raise TerminalizationError(
                f"terminalize({result.attempt_id}, {reason}): {result.errors[-1]} — "
                f"lease NOT released (releasing would destroy the verified commit)"
            )
        return result

    # (3) Release/revoke the lease so it is no longer ACTIVE. This is what
    # unblocks retry admission (acquire() refuses while a task has an active
    # lease). Idempotent: releasing an already-released lease is a no-op.
    _release_lease(result, attempt, lease_manager, reason)

    # (4) Destroy the attempt-private credential home + material. The worker's
    # own finally handles the graceful path; this is the AUTHORITATIVE sweep that
    # also covers the paths the worker never reached (crash, revoke, timeout,
    # abandonment) — the SIGTERM-with-no-handler case that left the operator's
    # real OAuth credential on disk indefinitely (SEC-C1).
    _destroy_home(result, run_root)

    # (5) Reconcile spool ownership: drop any inflight claim for this attempt so
    # the ephemeral transport does not hold a dangling reference to a dead
    # attempt. The ledger, not the spool, is the truth (Amendment v1 clause 3).
    _reconcile_spool(result, spool)

    if not result.ok and raise_on_security_failure:
        raise TerminalizationError(
            f"terminalize({result.attempt_id}, {reason}) left a security-blocking "
            f"condition: residue={result.credential_residue} errors={result._security_errors()}"
        )
    return result


_TERMINAL_STATUSES = frozenset({"succeeded", "failed", "cancelled", "rolled_back"})

#: Stable marker for a retention failure. The gate below keys on THIS, not on a
#: free-text message, so reworded errors cannot silently re-enable destructive
#: cleanup after a failed retention.
_RETENTION_FAILED_PREFIX = "trusted retention failed: "


def _retention_failed(result: TerminalizationResult) -> bool:
    """True when retention raised — destructive cleanup must not proceed."""
    return any(e.startswith(_RETENTION_FAILED_PREFIX) for e in result.errors)


#: Marker prefix for the "lease deliberately withheld" reason. The poller keys on
#: ``result.lease_withheld_reason`` being non-empty; this prefix is for logs.
LEASE_WITHHELD_RETENTION = "verified-commit retention failed: "

#: Path segment that anchors a candidate directory, e.g.
#: ``/var/lib/umh/candidates/wave2/<sha>/targets/<run-id>/fixture``.
_CANDIDATE_ANCHOR = "candidates"

#: Path segment that separates the candidate from the run in the canonical
#: layout ``.../candidates/<lane>/<candidate>/targets/<run-id>/...``. Requiring
#: it is what distinguishes a real candidate path from any path that merely
#: happens to contain the anchor word.
_TARGETS_ANCHOR = "targets"


def _commit_above_base(worktree: str, base_commit: str) -> str:
    """The attempt's own commit, or "" when it produced none.

    Answers "is anything actually destroyed if we proceed?" — the question that
    decides whether an unresolvable binding is fatal or merely uninteresting.
    A CPU-gate refusal here is NOT "no commit": it means we cannot tell, and
    "cannot tell" must be treated as at-risk.
    """
    from substrate.execution.attempts.verified_commit_retention import (
        CpuGateRefused,
        _git,
    )

    try:
        rc, head, _err = _git(worktree, ["rev-parse", "HEAD"], caller="at_risk_probe")
    except CpuGateRefused:
        # Cannot observe → assume at risk. Failing open here would reintroduce the
        # exact silent-destruction defect under load.
        return "unknown"
    except (FileNotFoundError, OSError):
        # The worktree directory is gone (already removed, or never materialized).
        # Cannot observe HEAD → same "cannot tell" as a gate refusal.
        return "unknown"
    if rc != 0 or not head:
        return ""
    base = str(base_commit or "").strip()
    if not base:
        # FAIL CLOSED. An absent base means we cannot tell whether HEAD is this
        # attempt's own verified work or the pre-existing base — the same
        # "cannot tell" as a gate refusal, and it must get the same answer.
        #
        # The previous "" (→ proceed to destroy) rested on an invariant this
        # function does not own: that the real SandboxManager always records a
        # resolved base. That is true TODAY (`create_sandbox` resolves or
        # raises), which is precisely why returning "" was invisible — and why
        # any future sandbox returning an empty base would silently reopen the
        # destruction defect with `ok=True, errors=[]`.
        return "unknown"
    if head == base:
        return ""
    return head


def _resolve_retention_binding(attempt: Any, repo: str) -> tuple[str, str, str]:
    """Derive (candidate, run_id, detail) from AUTHORITATIVE persisted records.

    Never reads process environment. Returns empty strings when the binding
    cannot be established — the caller then treats that as a retention FAILURE,
    not as "nothing to retain".

    ``run_id``   comes from ``attempt.correlation_id``, which the control plane
                 writes as ``w2-<run_id>`` (verified against real field records:
                 ``w2-20260805T182714Z-p1``). The prefix is stripped when present
                 so the ref path matches the run's own identity.
    ``candidate`` comes from the lease's ``repo_root``, whose canonical shape is
                 ``.../candidates/<lane>/<candidate-sha>/targets/<run-id>/...``.
                 The segment AFTER the lane segment is the candidate.
    """
    run_id = str(getattr(attempt, "correlation_id", "") or "").strip()
    if run_id.startswith("w2-"):
        run_id = run_id[3:]

    parts = [p for p in str(repo or "").split(os.sep) if p]
    detail = f"correlation_id={getattr(attempt, 'correlation_id', '')!r} repo={repo!r}"

    # ONE anchor match yields BOTH components. Resolving `candidate` and the
    # path's run from INDEPENDENT anchors is what produced silently misattributed
    # refs: the candidate was taken from the last `candidates` while the run came
    # from the last `targets`, so on `.../candidates/wave2/<sha>/targets/A/targets/B/f`
    # the two named different levels of the same path and the ref landed under
    # run B with errors=0. Measured. Both now come from the same match, or the
    # binding is refused.
    #
    # Canonical shape, indices relative to the anchor at i:
    #   candidates / <lane> / <candidate> / targets / <run-id> / ...
    #      i          i+1        i+2          i+3       i+4
    path_candidate = ""
    path_run = ""
    for i in (idx for idx, p in enumerate(parts) if p == _CANDIDATE_ANCHOR):
        if len(parts) <= i + 4 or parts[i + 3] != _TARGETS_ANCHOR:
            continue
        cand, prun = parts[i + 2], parts[i + 4]
        # A component that is itself one of the structural markers means the path
        # does not have the canonical shape — refuse rather than guess.
        if cand in (_CANDIDATE_ANCHOR, _TARGETS_ANCHOR):
            continue
        if prun in (_CANDIDATE_ANCHOR, _TARGETS_ANCHOR):
            continue
        if path_candidate and (cand, prun) != (path_candidate, path_run):
            # More than one DIFFERENT canonical match in one path: ambiguous.
            return "", "", f"{detail} (ambiguous: multiple candidate/run matches)"
        path_candidate, path_run = cand, prun

    if not path_candidate:
        return "", "", detail

    # The path names the run too. When correlation_id also names one and they
    # DISAGREE, we cannot tell which is authoritative — picking either could write
    # into another run's namespace. Refuse. When correlation_id is absent or
    # degenerate (e.g. exactly "w2-", which strips to empty), the path is equally
    # authoritative and supplies the run.
    if run_id and path_run != run_id:
        return "", "", f"{detail} (run mismatch: correlation={run_id!r} path={path_run!r})"
    run_id = run_id or path_run

    if not run_id:
        return "", "", detail
    return path_candidate, run_id, detail


def _retain_verified(
    result: TerminalizationResult, attempt: Any, lease_manager: Any, reason: str
) -> None:
    """Pin a SUCCEEDED attempt's verifier-approved commit under a trusted ref.

    Ordered before ``_release_lease`` because release destroys the worker branch.

    Only ``reason == "succeeded"`` retains: a failed, cancelled, revoked, or
    verification-rejected attempt must contribute NOTHING to any dependent's
    base. A retry that later succeeds retains its own commit under its own
    attempt ref, so retry-success lineage supersedes the failed attempt without
    any special case — the failed attempt simply has no ref to find.

    Non-fatal by construction for runs that do not use composition: a repo
    without the run/candidate binding, or an attempt with nothing committed,
    records a step and moves on. A genuine retention FAILURE is an error, which
    ``result.ok`` already treats as terminalization failure.
    """
    if reason != "succeeded":
        result.steps.append(f"no retention (reason={reason})")
        return

    lease = None
    lease_id = result.lease_id
    if lease_manager is not None and lease_id:
        getter = getattr(getattr(lease_manager, "_store", None), "get_lease", None)
        if callable(getter):
            try:
                lease = getter(lease_id)
            except Exception as exc:  # noqa: BLE001 - recorded, not swallowed
                logger.debug("retain: lease lookup failed for %s: %s", lease_id, exc)
    if not lease:
        result.steps.append("no lease record — nothing to retain")
        return

    def _f(name: str, default: str = "") -> str:
        if isinstance(lease, dict):
            return str(lease.get(name, default) or default)
        return str(getattr(lease, name, default) or default)

    worktree = _f("worktree_path")
    source = (
        lease.get("source_ref", {}) if isinstance(lease, dict) else getattr(lease, "source_ref", {})
    )
    repo = str((source or {}).get("repo_root", "") or "")
    if not repo or not worktree:
        result.steps.append("no repo/worktree on lease — nothing to retain")
        return

    # AUTHORITATIVE binding — derived from persisted records, never process env.
    #
    # This read used to be `os.environ["UMH_W2_CANDIDATE_SHA"/"UMH_W2_RUN_ID"]`,
    # and NOTHING in production ever set them (only tests did, via monkeypatch).
    # The absent binding took an early `steps.append(...)` return, so on a
    # perfectly healthy host retention silently never ran: `result.ok=True`,
    # `errors=[]`, and the verified commit was destroyed by the very next step.
    # That is field run 20260805T182714Z-p1 reproducing on EVERY normal run.
    #
    # Both anchors already exist on records the control plane owns:
    #   run_id    ← attempt.correlation_id ("w2-<run_id>"), verified against real
    #               field data: "w2-20260805T182714Z-p1"
    #   candidate ← the lease's repo_root path, which is
    #               .../candidates/wave2/<candidate-sha>/targets/<run-id>/fixture
    candidate, run_id, binding_detail = _resolve_retention_binding(attempt, repo)

    from substrate.execution.attempts.verified_commit_retention import (
        RetentionError,
        retain_verified_commit,
    )

    if not candidate or not run_id:
        # "The binding is missing" and "there is nothing to retain" are DIFFERENT
        # facts, and the old code conflated them — it skipped silently and the
        # next step destroyed verified work.
        #
        # But failing closed unconditionally is also wrong: `terminalize` is the
        # C-2 authority for ELEVEN terminal paths, not just Wave 2 field runs, and
        # a caller whose repo is not laid out as a candidate would be blocked
        # forever with nothing at stake. So ask the question that actually
        # matters: IS there a commit above the lease's authorized base? Only then
        # is anything destroyed by proceeding.
        at_risk = _commit_above_base(worktree, str((source or {}).get("base_commit", "") or ""))
        if at_risk:
            result.errors.append(
                f"{_RETENTION_FAILED_PREFIX}cannot resolve the candidate/run binding "
                f"({binding_detail}) while a verified commit {at_risk[:12]} exists — "
                f"refusing to destroy a commit that cannot be retained"
            )
            logger.error(
                "retain: no authoritative binding for %s (%s) and commit %s is at "
                "risk — destructive cleanup blocked",
                result.attempt_id,
                binding_detail,
                at_risk[:12],
            )
        else:
            result.steps.append(
                f"no binding and no commit above base — nothing at risk ({binding_detail})"
            )
        return

    try:
        commit = retain_verified_commit(
            repo=repo,
            worktree=worktree,
            candidate=candidate,
            run_id=run_id,
            task_id=result.task_id,
            attempt_id=result.attempt_id,
            # The lease's authorized base. An attempt whose HEAD is still its
            # base produced no commit, so there is nothing verified to retain.
            base_commit=str((source or {}).get("base_commit", "") or ""),
        )
    except RetentionError as exc:
        result.errors.append(f"{_RETENTION_FAILED_PREFIX}{exc}")
        logger.warning("retain failed for %s: %s", result.attempt_id, exc)
        return
    except (FileNotFoundError, OSError) as exc:
        result.errors.append(f"{_RETENTION_FAILED_PREFIX}worktree missing or inaccessible: {exc}")
        logger.warning("retain: worktree gone for %s: %s", result.attempt_id, exc)
        return
    result.retained_commit = commit
    result.steps.append(
        f"retained verified commit {commit[:12]}" if commit else "nothing to retain (no commit)"
    )


def _resolve_sandbox_id(result: TerminalizationResult, lease_manager: Any) -> str:
    """Look up the sandbox_id from the lease record. Returns "" on failure."""
    sandbox_id = ""
    lease_id = result.lease_id
    getter = getattr(getattr(lease_manager, "_store", None), "get_lease", None)
    if callable(getter) and lease_id:
        try:
            row = getter(lease_id)
        except Exception as exc:  # noqa: BLE001 - recorded, not swallowed
            logger.debug("slot preserve: lease lookup failed for %s: %s", lease_id, exc)
            row = None
        if row is not None:
            sandbox_id = (
                str(row.get("sandbox_id", "") or "")
                if isinstance(row, dict)
                else str(getattr(row, "sandbox_id", "") or "")
            )
    if not sandbox_id:
        result.steps.append("slot NOT freed: no sandbox_id on the lease record")
    return sandbox_id


def _preserve_sandbox_slot(result: TerminalizationResult, lease_manager: Any) -> None:
    """Free the sandbox concurrency slot while KEEPING the branch (and its commits).

    Called only on the withhold path. Removes the worktree so an unrelated Task
    can be admitted, and preserves the branch ref so the verified commit stays
    reachable and survives ``git gc``.

    FAIL CLOSED on any doubt: if the sandbox manager cannot be reached, or does
    not support ``preserve_branch``, do NOTHING. Calling the plain
    ``cleanup_sandbox`` here would delete the branch — the precise destruction
    the withhold exists to prevent. A held slot is recoverable; a destroyed
    commit is not.
    """
    import inspect

    sandbox = getattr(lease_manager, "_sandbox", None)
    if sandbox is None:
        result.steps.append("slot NOT freed: no sandbox manager on the lease manager")
        return

    cleanup = getattr(sandbox, "cleanup_sandbox", None)
    if not callable(cleanup):
        result.steps.append("slot NOT freed: sandbox manager has no cleanup_sandbox")
        return

    try:
        supports = "preserve_branch" in inspect.signature(cleanup).parameters
    except (TypeError, ValueError) as exc:  # noqa: BLE001 - recorded, not swallowed
        logger.debug("slot preserve: cannot inspect cleanup_sandbox: %s", exc)
        supports = False
    if not supports:
        # Never fall back to the destructive call.
        result.steps.append(
            "slot NOT freed: cleanup_sandbox does not support preserve_branch — "
            "refusing the destructive variant"
        )
        return

    sandbox_id = _resolve_sandbox_id(result, lease_manager)
    if not sandbox_id:
        return

    # --- Tier 1: normal cleanup with preserve_branch (uses git subprocesses) ---
    try:
        freed = bool(cleanup(sandbox_id, preserve_branch=True))
    except Exception as exc:  # noqa: BLE001 - recorded, not swallowed
        logger.warning("slot preserve (tier 1) failed for sandbox %s: %s", sandbox_id, exc)
        freed = False

    if freed:
        result.sandbox_slot_freed = True
        result.steps.append(f"sandbox slot {sandbox_id} freed with branch PRESERVED")
        return

    # --- Tier 2: filesystem-only emergency release (no git subprocesses) ---
    emergency = getattr(sandbox, "emergency_free_slot", None)
    if not callable(emergency):
        result.steps.append(
            "slot NOT freed: sandbox manager supports neither preserve_branch "
            "nor emergency_free_slot — refusing the destructive variant"
        )
        return

    try:
        freed = bool(emergency(sandbox_id))
    except Exception as exc:  # noqa: BLE001 - recorded, not swallowed
        logger.warning("emergency slot free failed for sandbox %s: %s", sandbox_id, exc)
        result.steps.append(f"slot NOT freed: emergency_free_slot raised for {sandbox_id}: {exc}")
        return

    result.sandbox_slot_freed = freed
    result.steps.append(
        f"sandbox slot {sandbox_id} freed via emergency path (filesystem only, prune deferred)"
        if freed
        else f"slot NOT freed: emergency_free_slot({sandbox_id}) returned False"
    )


def _release_lease(
    result: TerminalizationResult, attempt: Any, lease_manager: Any, reason: str
) -> None:
    lease_id = result.lease_id
    if not lease_id:
        result.steps.append("no lease to release")
        result.lease_released = True
        return
    if lease_manager is None:
        result.errors.append("no lease_manager supplied — lease not released")
        return
    try:
        # REVOKED/EXPIRED terminal reasons revoke; everything else releases.
        # Both drive the lease out of ACTIVE and destroy the sandbox worktree;
        # revoke is used when the termination is adversarial/forced.
        if reason in ("revoked", "expired", "authorization_expired", "security_boundary_failure"):
            lease_manager.revoke(lease_id, f"terminalize:{reason}")
        else:
            lease_manager.release(lease_id, cleanup=True)
        result.lease_released = True
        result.steps.append(f"lease {lease_id} released ({reason})")
    except Exception as exc:  # noqa: BLE001 - recorded, not swallowed
        result.errors.append(f"lease release failed: {exc}")
        logger.debug("terminalize: lease release failed for %s: %s", lease_id, exc)


def _destroy_home(result: TerminalizationResult, run_root: str) -> None:
    if not run_root:
        # No run_root = we cannot even locate the home. If nothing was ever
        # placed this is benign, but we cannot PROVE that — so it is an error,
        # not a silent pass. Callers that never open a home pass run_root anyway.
        result.errors.append("no run_root supplied — cannot verify credential home destroyed")
        return
    if not result.attempt_id:
        result.errors.append("no attempt_id — cannot locate credential home")
        return

    from substrate.execution.attempts.worker_credential_boundary import (
        AttemptHome,
        close_attempt_credential_home,
    )

    home_path = attempt_home_path(run_root, result.attempt_id)
    claude_dir = f"{home_path}/.claude"
    tmp_dir = f"{home_path}/tmp"
    # Reconstruct a closer over the derived path. The credential filenames are
    # the canonical set; close overwrites+removes whatever is present, and the
    # residue scan below is the authoritative check regardless.
    home = AttemptHome(
        attempt_id=result.attempt_id,
        home_path=home_path,
        tmp_path=tmp_dir,
        claude_dir=claude_dir,
        credential_files=[f"{claude_dir}/.credentials.json", f"{claude_dir}/config.json"],
    )
    try:
        close_attempt_credential_home(home)
        result.home_destroyed = True
        result.steps.append(f"home {home_path} destroyed")
    except CredentialBoundaryError as exc:
        # Cleanup failure is a SECURITY failure, not a warning.
        result.errors.append(f"SECURITY: home destruction failed: {exc}")
        logger.error("terminalize: SECURITY home destruction failed for %s: %s", home_path, exc)

    # Authoritative residue scan: 'destroyed' is a verified claim, not a hope.
    residue = assert_no_credential_residue(run_root)
    # Scope the residue to THIS attempt's home (a sibling attempt's live home is
    # not this terminalization's failure). RV-MED-1: use a PATH-BOUNDARY match, not
    # a substring — `home_path in p` mis-attributed a sibling's residue whenever one
    # attempt-id was a prefix of another (att1's home path is a substring of att11's
    # credential path), flagging the wrong attempt.
    mine = [p for p in residue if p == home_path or p.startswith(home_path + os.sep)]
    if mine:
        result.credential_residue = mine
        result.errors.append(f"SECURITY: credential residue survived: {mine}")


def _reconcile_spool(result: TerminalizationResult, spool: Any) -> None:
    if spool is None:
        result.spool_reconciled = True  # nothing to reconcile
        result.steps.append("no spool to reconcile")
        return
    dropper = getattr(spool, "drop_inflight_for_attempt", None)
    if not callable(dropper):
        # A spool WAS supplied but exposes no reconcile hook. This used to be
        # recorded as spool_reconciled=True ("the ledger is truth") — a softening:
        # if the caller passes a spool it means "reconcile it", and a spool that
        # cannot be reconciled is a missing capability, not a benign no-op. Fail
        # explicitly. (A caller with genuinely nothing to reconcile passes
        # spool=None.)
        result.errors.append(
            "spool supplied but has no drop_inflight_for_attempt — cannot reconcile"
        )
        return
    try:
        dropped = dropper(result.attempt_id)
        result.spool_reconciled = True
        result.steps.append(f"spool inflight dropped for {result.attempt_id}: {dropped}")
    except Exception as exc:  # noqa: BLE001
        result.errors.append(f"spool reconcile failed: {exc}")


def retry_admissible(store: Any, task_id: str) -> tuple[bool, str]:
    """Whether a NEW attempt for ``task_id`` may be admitted.

    A retry is admissible ONLY when the task has no ACTIVE lease. This is the
    structural guarantee behind "permit retry only after the prior lease is no
    longer active": terminalize() drives the prior lease out of ACTIVE, and this
    predicate refuses admission until it is.
    """
    active = store.active_lease_for_task(task_id)
    if active is not None:
        return False, f"task {task_id} still has an active lease {active.get('lease_id', '')!r}"
    return True, "no active lease — retry admissible"


__all__ = [
    "TERMINAL_REASONS",
    "TerminalizationError",
    "TerminalizationResult",
    "terminalize",
    "retry_admissible",
]
