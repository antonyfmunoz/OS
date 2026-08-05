"""Wave 2 control-plane poller (run-scoped — NOT a persistent supervisor).

The scheduler ADMITS attempts to ``dispatched`` and hands each to the host
attempt runner over the signed dispatch spool. The runner executes the real,
isolated worker and writes a SIGNED result to the spool OUTBOX. This poller is
the control-plane half of that loop: it drains verified outbox results and
advances the CANONICAL attempt ledger through its lifecycle, then re-runs a
single scheduler pass so the newly-unblocked frontier is dispatched.

Ownership boundary (Amendment v1 clause 3):
- ``ExecutionAttemptStore`` is the SOLE current execution truth. This poller is
  the only thing that turns a spool result into a canonical transition; the
  runner never mutates the ledger.
- The spool is ephemeral transport. If the outbox is lost, canonical attempt
  state is unchanged and the run is reconstructable from the ledger; NO operator
  status is inferred from file presence.

Lifecycle applied per drained result (guards enforced in ``lifecycle.py``):

    dispatched → running        (worker claimed + started; optimistic on first sight)
    running    → verifying      (worker reported terminal; result recorded)
    verifying  → succeeded       (independent AttemptProof, verifier ≠ worker)
    verifying  → failed          (verification refused — no false Proof)

A worker's self-reported ``ok`` is NEVER trusted to complete a task: the poller
always routes through ``verify_attempt`` with a verifier identity distinct from
the worker, and the ``verifying→succeeded`` guard independently re-checks
verifier≠worker + proof presence. A failed verification transitions to
``failed`` (retry is a NEW attempt minted by the scheduler, never a
re-transition).

This module imports only downward (substrate + same-package) and never touches
transports/services/adapters.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, Callable

from substrate.execution.attempts.records import ExecutionAttemptStatus as _S
from substrate.execution.attempts.store import AttemptStoreConflict, ExecutionAttemptStore

logger = logging.getLogger(__name__)

# Worker-authored lists (files_changed/commits) are self-report only — bounded so
# a lying/oversized result cannot bloat the canonical record (review W5).
_MAX_REPORTED_ITEMS = 500


def _accepts_effective_base(builder: Any) -> bool:
    """Does ``builder`` accept an ``effective_base`` keyword?

    Answered by signature, not by calling and catching TypeError: the builder
    has real side effects (it spawns a confined verifier), so a speculative call
    that fails must never be retried with different arguments. An
    unintrospectable callable (C builtin, exotic wrapper) is treated as NOT
    accepting it — the conservative answer, since the legacy single-argument
    form is always valid.
    """
    import inspect

    try:
        sig = inspect.signature(builder)
    except (TypeError, ValueError):
        return False
    params = sig.parameters
    if any(p.kind is inspect.Parameter.VAR_KEYWORD for p in params.values()):
        return True
    param = params.get("effective_base")
    return param is not None and param.kind in (
        inspect.Parameter.KEYWORD_ONLY,
        inspect.Parameter.POSITIONAL_OR_KEYWORD,
    )


@dataclass
class PollerPassReport:
    """What one poller pass did — a truthful, side-effect-free summary."""

    results_drained: int = 0
    transitioned_running: list[str] = field(default_factory=list)
    transitioned_verifying: list[str] = field(default_factory=list)
    succeeded: list[str] = field(default_factory=list)
    failed: list[str] = field(default_factory=list)
    ignored: list[str] = field(default_factory=list)
    scheduler_admitted: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "results_drained": self.results_drained,
            "transitioned_running": list(self.transitioned_running),
            "transitioned_verifying": list(self.transitioned_verifying),
            "succeeded": list(self.succeeded),
            "failed": list(self.failed),
            "ignored": list(self.ignored),
            "scheduler_admitted": list(self.scheduler_admitted),
            "errors": list(self.errors),
        }


class ControlPlanePoller:
    """Drives the canonical attempt ledger from signed spool results.

    Injected dependencies keep this testable and free of transport coupling:
    - ``store``            — the sole execution-truth ledger.
    - ``spool``            — a ``DispatchSpool`` (only ``drain_results`` is used).
    - ``scheduler``        — an ``AttemptScheduler`` (its ``run_scheduler_pass``
      is re-invoked after transitions so the next frontier dispatches).
    - ``verify_fn``        — callable producing a ``VerificationVerdict``
      (``verify_attempt`` in prod; a deterministic stub in the harness rehearsal).
    - ``assignment_lookup``/``lease_lookup`` — resolve the durable assignment +
      lease for an attempt (from their stores) so the verifier gets real context.
    - ``scheduler_pass_kwargs`` — the kwargs the scheduler pass needs (grant
      resolvers, worker/compute candidates); passed straight through.
    """

    def __init__(
        self,
        *,
        store: ExecutionAttemptStore,
        spool: Any,
        scheduler: Any,
        verify_fn: Callable[..., Any],
        assignment_lookup: Callable[[str], Any] | None = None,
        lease_lookup: Callable[[str], Any] | None = None,
        packet_lookup: Callable[[str], Any] | None = None,
        proof_runtime: Any | None = None,
        independent_checks_for: Callable[[Any], Callable[[Any], list[Any]] | None] | None = None,
        lease_manager: Any | None = None,
        run_root: str = "",
        scheduler_pass_kwargs: dict[str, Any] | None = None,
    ) -> None:
        self._store = store
        self._spool = spool
        self._scheduler = scheduler
        self._verify = verify_fn
        self._assignment_lookup = assignment_lookup or (lambda _aid: None)
        self._lease_lookup = lease_lookup or (lambda _lid: None)
        # Terminalization authority (C-2): on EVERY terminal transition the
        # attempt's lease is released and its credential home destroyed through
        # ONE idempotent path, so a failed A1 never deadlocks A2's retry and no
        # credential survives on disk.
        self._lease_manager = lease_manager
        self._run_root = run_root
        # Default resolves to None → the diff-scope check fails closed. This is
        # deliberate: an unwired packet lookup must NOT silently authorize the
        # whole worktree (finding C-1).
        self._packet_lookup = packet_lookup or (lambda _tid: None)
        self._proof_runtime = proof_runtime
        self._independent_checks_for = independent_checks_for or (lambda _a: None)
        self._pass_kwargs = dict(scheduler_pass_kwargs or {})

    # ── one pass ─────────────────────────────────────────────────────────────

    def run_pass(self, *, run_scheduler: bool = True) -> PollerPassReport:
        """Drain the outbox, apply canonical transitions, then one scheduler pass."""
        report = PollerPassReport()

        results = self._spool.drain_results()
        report.results_drained = len(results)

        for result in results:
            try:
                self._apply_result(result, report)
            except AttemptStoreConflict as exc:
                # A concurrent writer moved the row — safe to ignore this pass;
                # the next pass rereads canonical state.
                report.ignored.append(f"{result.get('attempt_id', '?')}: conflict {exc}")
            except Exception as exc:  # never let one bad result stall the loop
                report.errors.append(f"{result.get('attempt_id', '?')}: {exc}")
                logger.debug("poller: result apply failed: %s", exc, exc_info=True)

        if run_scheduler:
            try:
                sched_report = self._scheduler.run_scheduler_pass(**self._pass_kwargs)
                admitted = getattr(sched_report, "attempts_admitted", None) or []
                report.scheduler_admitted = list(admitted)
            except Exception as exc:
                report.errors.append(f"scheduler_pass: {exc}")
                logger.debug("poller: scheduler pass failed: %s", exc, exc_info=True)

        return report

    # ── per-result state machine ─────────────────────────────────────────────

    def _apply_result(self, result: dict[str, Any], report: PollerPassReport) -> None:
        attempt_id = result.get("attempt_id", "")
        if not attempt_id:
            report.ignored.append("<no attempt_id>")
            return

        attempt = self._store.get_attempt(attempt_id)
        if attempt is None:
            report.ignored.append(f"{attempt_id}: not in ledger")
            return

        # Terminal already? idempotent — a re-delivered result is a no-op.
        if attempt.status in (_S.SUCCEEDED.value, _S.FAILED.value):
            report.ignored.append(f"{attempt_id}: already {attempt.status}")
            return

        # 1. dispatched → running (worker has been handed the packet). We move to
        #    running as soon as we see any result for a dispatched attempt.
        if attempt.status == _S.DISPATCHED.value:
            attempt = self._transition(
                attempt,
                _S.RUNNING.value,
                (_S.DISPATCHED.value,),
                actor="poller",
                reason="worker result received",
            )
            report.transitioned_running.append(attempt_id)

        # 2. running → verifying (record the worker's raw result; never trust it).
        #    The worker AUTHORS files_changed/commits, so they are attacker-
        #    controllable narrative (review W5): they are BOUNDED here and recorded
        #    as a self-report only. verify_fn MUST derive the real changed-file set
        #    by diffing the lease worktree independently — never from these lists.
        if attempt.status == _S.RUNNING.value:
            worker_result = _WorkerResultView(result.get("worker_result", {}) or {})
            attempt = self._transition(
                attempt,
                _S.VERIFYING.value,
                (_S.RUNNING.value,),
                actor="poller",
                reason=f"worker reported status={worker_result.status}",
                updates={
                    "files_changed": list(worker_result.files_changed)[:_MAX_REPORTED_ITEMS],
                    "commits": list(worker_result.commits)[:_MAX_REPORTED_ITEMS],
                },
            )
            report.transitioned_verifying.append(attempt_id)

            # 3. verifying → succeeded | failed via INDEPENDENT verification.
            self._verify_and_settle(attempt, worker_result, result, report)

    def _verify_and_settle(
        self,
        attempt: Any,
        worker_result: Any,
        raw: dict[str, Any],
        report: PollerPassReport,
    ) -> None:
        assignment = self._assignment_lookup(getattr(attempt, "assignment_id", "") or "")
        lease = self._lease_lookup(getattr(attempt, "lease_id", "") or "")
        # TRUSTED BASE RE-ANCHOR (finding F-3 fix). The trusted projection
        # commits system files (OBJECTIVE.md, SHARED_CONTEXT.md) and moves the
        # attempt's diff base PAST them. The lease record still carries the
        # original fixture base. Without re-anchoring, `git diff <old_base>..HEAD`
        # includes the system writes and diff_scope rejects every attempt.
        #
        # The move is AUTHORIZED, never assumed. Moving a base forward shrinks
        # the observed change set, so an unchecked re-anchor is a scope-check
        # bypass: anchoring at the worker's own HEAD returns `changed=0` and
        # passes with out-of-scope files in the tree. `_base_is_ancestor_of_head`
        # does not stop that — every commit on the branch is an ancestor of HEAD.
        # `reanchor_is_authorized` requires a full SHA, forward-only movement
        # from the authorized base, and a skipped range touching ONLY trusted
        # projection paths.
        #
        # Fails CLOSED to the ORIGINAL base: a refused re-anchor yields the
        # pre-fix scope rejection, never a pass.
        trusted_base = str(raw.get("trusted_base", "") or "").strip()
        if trusted_base and lease is not None:
            from substrate.execution.attempts.verification import reanchor_is_authorized

            original_base = str(getattr(lease, "snapshot_ref", "") or "").strip()
            allowed, why = reanchor_is_authorized(
                worktree=str(getattr(lease, "worktree_path", "") or ""),
                original_base=original_base,
                new_base=trusted_base,
            )
            if not allowed:
                logger.warning(
                    "REFUSING trusted-base re-anchor for attempt %s (task %s): "
                    "%s -> %s: %s — verifying against the ORIGINAL base",
                    getattr(attempt, "attempt_id", "?"),
                    getattr(attempt, "task_id", ""),
                    original_base[:12],
                    trusted_base[:12],
                    why,
                )
                report.errors.append(
                    f"{getattr(attempt, 'attempt_id', '?')}: re-anchor refused: {why}"
                )
            elif hasattr(lease, "_d") and isinstance(lease._d, dict):  # noqa: SLF001
                lease._d["snapshot_ref"] = trusted_base  # noqa: SLF001
            elif isinstance(lease, dict):
                lease["snapshot_ref"] = trusted_base
        # Verifier identity is the assignment's verifier role — deterministically
        # distinct from the worker (SoD enforced at placement + here + in the guard).
        verifier_role = (
            getattr(attempt, "verifier_role_id", "")
            or getattr(
                assignment,
                "verifier_role_id",
                "",
            )
            or "role-verify-op"
        )
        verifier_identity = f"verifier:{verifier_role}"
        worker_identity = getattr(attempt, "worker_identity", "") or getattr(
            assignment,
            "worker_identity",
            "",
        )
        if verifier_identity == worker_identity:  # never let them collide
            verifier_identity = f"verifier:{verifier_role}:{attempt.attempt_id}"

        package_hash = getattr(attempt, "instruction_package_hash", "")
        verdict = self._verify(
            attempt=attempt,
            assignment=assignment,
            lease=lease,
            worker_result=worker_result,
            package_hash=package_hash,
            verifier_identity=verifier_identity,
            verifier_role_id=verifier_role,
            # The canonical WorkPacket is the diff-scope AUTHORITY (finding C-1).
            # Without it the verifier cannot resolve which paths this Task was
            # authorized to write, and the scope check fails closed rather than
            # falling back to "the whole worktree is fine".
            packet=self._packet_lookup(getattr(attempt, "task_id", "")),
            # The EFFECTIVE base is derived once, here, and threaded to the
            # checks builder. The builder re-resolves the lease from the store
            # to find the worktree, and that fresh record carries the ORIGINAL
            # snapshot_ref (the re-anchor is deliberately in-memory — the ledger's
            # authorized base stays canonical). Without threading it, diff_scope
            # would enforce the re-anchored base while the persisted Proof
            # recorded the stale one: a Proof attesting to a base that was not
            # the one enforced.
            independent_checks=self._build_independent_checks(attempt, lease),
            proof_runtime=self._proof_runtime,
        )

        if getattr(verdict, "passed", False) and getattr(verdict, "proof_id", ""):
            updated = self._transition(
                attempt,
                _S.SUCCEEDED.value,
                (_S.VERIFYING.value,),
                actor=verifier_identity,
                reason="AttemptProof verified (verifier ≠ worker)",
                updates={
                    "proof_id": verdict.proof_id,
                    "verifier_identity": verifier_identity,
                },
            )
            report.succeeded.append(attempt.attempt_id)
            self._terminalize(updated or attempt, "succeeded", report)
        else:
            reason = "verification refused"
            fails = [c for c in getattr(verdict, "checks", []) if not c.get("ok", False)]
            if fails:
                reason = "verification refused: " + "; ".join(
                    f"{c.get('check_id', '?')}: {(c.get('detail', '') or '')[:80]}"
                    for c in fails[:4]
                )
            logger.warning(
                "verification FAILED for attempt %s (task %s): %s",
                attempt.attempt_id,
                getattr(attempt, "task_id", ""),
                reason,
            )
            updated = self._transition(
                attempt,
                _S.FAILED.value,
                (_S.VERIFYING.value,),
                actor=verifier_identity,
                reason=reason,
                updates={"verifier_identity": verifier_identity, "blocked_reason": reason[:200]},
            )
            report.failed.append(attempt.attempt_id)
            # verification_rejected is a terminal reason: release the lease so the
            # retry is admissible, and destroy the credential home.
            self._terminalize(updated or attempt, "verification_rejected", report)

    def _build_independent_checks(self, attempt: Any, lease: Any) -> Any:
        """Build the independent-checks callable for THIS attempt's effective base.

        The checks builder resolves its own lease record from the store to find
        the worktree; that record carries the ORIGINAL snapshot_ref, because the
        re-anchor is in-memory by design (the ledger's authorized base must stay
        canonical — persisting a run-derived base into durable state would be
        worse than the divergence it fixes).

        So the base the verifier ENFORCES and the base the Proof RECORDS must be
        reconciled here, at the one place that knows both. Builders that accept
        ``effective_base`` receive it; older single-argument builders keep
        working unchanged.
        """
        effective_base = str(getattr(lease, "snapshot_ref", "") or "").strip()
        builder = self._independent_checks_for
        if not effective_base:
            return builder(attempt)
        # Decide by SIGNATURE, never by catching TypeError. A builder that
        # accepts the kwarg can itself raise TypeError from its body — catching
        # it here would swallow a real error and re-invoke the builder a SECOND
        # time with a different base. The production builder spawns a confined
        # verifier, so that is a duplicated side effect AND a Proof recorded
        # against the wrong base. Verified: the try/except form invoked the
        # builder twice.
        if not _accepts_effective_base(builder):
            return builder(attempt)
        return builder(attempt, effective_base=effective_base)

    def _terminalize(self, attempt: Any, reason: str, report: PollerPassReport) -> None:
        """Run the ONE terminalization authority for a just-terminalized attempt.

        Releases the lease (unblocking any retry) and destroys the attempt's
        credential home. A residue/security failure is surfaced on the report —
        never swallowed — but does not raise here, so one bad teardown cannot
        stall the drain loop; the run's teardown + selfcheck fail closed on it.
        """
        from substrate.execution.attempts.terminalization import terminalize

        try:
            result = terminalize(
                attempt=attempt,
                reason=reason,
                lease_manager=self._lease_manager,
                run_root=self._run_root,
                spool=self._spool,
                raise_on_security_failure=False,
            )
            if not result.ok:
                report.errors.append(
                    f"terminalize({attempt.attempt_id},{reason}) SECURITY: {result.errors}"
                )
            # A WITHHELD lease is not a release FAULT. When terminalization
            # deliberately keeps the lease active to preserve the only copy of a
            # verifier-approved commit, healing it here destroys exactly what the
            # withhold protected: `revoke()` also runs `cleanup_sandbox` →
            # `git branch -D`. Measured — the healer silently reversed the
            # protection one frame above `terminalize`, and the field defect
            # reproduced end to end.
            #
            # `lease_released == False` alone cannot distinguish the two cases, so
            # the withhold is stated explicitly on the result. Surface it as a
            # BLOCKING error (the task's retry stays blocked until an operator
            # acts) rather than trading an unrecoverable commit for a recoverable
            # stall.
            withheld = str(getattr(result, "lease_withheld_reason", "") or "").strip()
            if withheld:
                report.errors.append(
                    f"terminalize({attempt.attempt_id},{reason}): lease "
                    f"{result.lease_id} WITHHELD to preserve the verified commit — "
                    f"{withheld}. Retry for this task is blocked until the "
                    f"retention condition is resolved; do NOT revoke this lease, "
                    f"revoking destroys the commit."
                )
                logger.error(
                    "poller: lease %s withheld for attempt %s — not force-revoking: %s",
                    result.lease_id,
                    attempt.attempt_id,
                    withheld,
                )
            # RV-HIGH-2: a lease-release FAULT leaves the task's lease ACTIVE, and
            # `acquire()` refuses a second active lease per task — so the next
            # attempt deadlocks BLOCKED↔READY forever. terminalize does not raise
            # on a non-security error, so heal it HERE at the authoritative terminal
            # transition: re-drive a revoke for the stranded lease so retry admission
            # can proceed. Idempotent — revoking an already-revoked lease is a no-op.
            elif not result.lease_released and result.lease_id and self._lease_manager is not None:
                try:
                    self._lease_manager.revoke(
                        result.lease_id, f"terminalize_release_retry:{reason}"
                    )
                    report.errors.append(
                        f"terminalize({attempt.attempt_id},{reason}): lease "
                        f"{result.lease_id} force-revoked after release fault (retry unblocked)"
                    )
                except Exception as exc:  # noqa: BLE001 - surfaced, never swallowed
                    report.errors.append(
                        f"terminalize({attempt.attempt_id},{reason}): lease "
                        f"{result.lease_id} STILL active after revoke retry: {exc} — "
                        f"retry for this task is blocked until manual release"
                    )
        except Exception as exc:  # never let teardown stall the drain loop
            report.errors.append(f"terminalize({attempt.attempt_id},{reason}) raised: {exc}")
            logger.debug("poller: terminalize failed: %s", exc, exc_info=True)

    # ── canonical write ──────────────────────────────────────────────────────

    def _transition(
        self,
        attempt: Any,
        to_status: str,
        expected: tuple[str, ...],
        *,
        actor: str,
        reason: str,
        updates: dict[str, Any] | None = None,
    ) -> Any:
        return self._store.transition_cas(
            attempt.attempt_id,
            to_status,
            expected_record_version=attempt.record_version,
            expected_statuses=expected,
            actor=actor,
            reason=reason,
            updates=updates or {},
        )


class _WorkerResultView:
    """Adapts the spool result's ``worker_result`` dict to the attribute shape
    ``verify_attempt`` expects (``files_changed``, ``commits``, ``status``,
    ``ok``, ``isolated``)."""

    def __init__(self, d: dict[str, Any]) -> None:
        self._d = d or {}

    @property
    def ok(self) -> bool:
        return bool(self._d.get("ok", False))

    @property
    def status(self) -> str:
        return str(self._d.get("status", "unknown"))

    @property
    def files_changed(self) -> list[str]:
        return list(self._d.get("files_changed", []) or [])

    @property
    def commits(self) -> list[str]:
        return list(self._d.get("commits", []) or [])

    @property
    def isolated(self) -> bool:
        return bool(self._d.get("isolated", False))

    def to_dict(self) -> dict[str, Any]:
        return dict(self._d)


__all__ = ["ControlPlanePoller", "PollerPassReport"]
