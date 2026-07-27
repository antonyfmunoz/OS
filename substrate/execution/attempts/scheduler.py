"""AttemptScheduler — bounded, single-writer, dependency-aware admission.

Run-scoped Wave 2 component (NOT the Wave 3 persistent supervisor). One
``run_scheduler_pass()`` is a single bounded sweep that:

1. computes the ready frontier from canonical WorkGraph/WorkPacket dependencies
   (chain, fan-out, fan-in, independent lanes) — dependency truth is the attempt
   ledger (a dep is satisfied only when it has a SUCCEEDED attempt with Proof);
2. propagates failure (a Task whose attempts are exhausted → dependents BLOCKED);
3. creates bounded retries (a new attempt_number, linked to the prior);
4. ADMITS ready attempts up to max_concurrency: place → lease → compile → dispatch,
   each step CAS-guarded so a losing concurrent tick mutates nothing.

Terminal transitions (SUCCEEDED / FAILED-at-verification) are performed by the
control-plane POLLER, which invokes the one terminalization authority
(``terminalization.terminalize``) to release the lease and destroy the credential
home. The scheduler does NOT itself cancel/revoke/expire attempts today — a
grant-level REVOKED/INVALIDATED cascade onto in-flight attempts is a Wave 2
follow-on (the authority supports the ``revoked``/``expired``/``cancelled``
reasons; their scheduler-side wiring is pending and is stated as such in the
C-2 ledger entry, not claimed as done).

Single-writer: a pass acquires an interprocess scheduler lease keyed
tenant+plan+version (non-blocking flock). A losing tick returns immediately with
``acquired=False`` and performs NO mutation. Exactly-once attempt creation comes
from the store's idempotent-create key plus CAS transitions.
"""

from __future__ import annotations

import logging
import os
import time
from contextlib import contextmanager
from dataclasses import dataclass, field
from typing import Any, Callable, Iterator

from substrate.execution.attempts.admission import authorize_admission
from substrate.execution.attempts.events import emit_execution_event
from substrate.execution.attempts.lifecycle import AttemptLifecycleError
from substrate.execution.attempts.records import (
    ExecutionAttempt,
    ExecutionAttemptStatus,
)
from substrate.execution.attempts.store import AttemptStoreConflict, ExecutionAttemptStore

try:
    import fcntl
except ImportError:  # pragma: no cover
    fcntl = None  # type: ignore[assignment]

logger = logging.getLogger(__name__)

_S = ExecutionAttemptStatus


@dataclass
class SchedulerPassReport:
    acquired: bool = False
    grant_ref: str = ""
    attempts_created: list[str] = field(default_factory=list)
    attempts_admitted: list[str] = field(default_factory=list)
    attempts_blocked: list[str] = field(default_factory=list)
    retries_created: list[str] = field(default_factory=list)
    reason: str = ""


class AttemptScheduler:
    def __init__(
        self,
        store: ExecutionAttemptStore,
        *,
        work_queue: Any,
        placement_fn: Callable[..., Any],
        lease_manager: Any,
        compile_fn: Callable[..., Any],
        dispatch_fn: Callable[..., Any] | None = None,
        dep_success_lookup: Callable[[str], bool] | None = None,
        max_concurrency: int = 2,
        mutation_runner: Callable[..., Any] | None = None,
        lock_dir: str | None = None,
        latest_plan_lookup: Callable[[str], Any] | None = None,
    ) -> None:
        self._store = store
        self._queue = work_queue
        self._place = placement_fn
        self._leases = lease_manager
        self._compile = compile_fn
        self._dispatch = dispatch_fn
        self._dep_lookup = dep_success_lookup or self._default_dep_lookup
        self._max_concurrency = max_concurrency
        self._mutation_runner = mutation_runner
        if lock_dir is None:
            from substrate.state.runtime_paths import runtime_state_dir

            lock_dir = str(runtime_state_dir("operator/execution_attempts"))
        self._lock_dir = lock_dir
        # Supersession lookup, defaulted for EVERY caller (same pattern and same
        # default as ExecutionAuthorizationDecisionSource). Left as None this
        # would silently skip the supersession branch of is_authorization_valid
        # on the one path that runs every pass — which is exactly how a
        # superseded grant kept dispatching.
        if latest_plan_lookup is None:

            def _default_latest_plan_lookup(objective_id: str) -> Any:
                from substrate.execution.planning.store import PlanningStore

                try:
                    return PlanningStore().latest_version_of(objective_id)
                except Exception as exc:  # unreadable store → treat as absent
                    logger.debug("latest-plan lookup failed for %s: %s", objective_id, exc)
                    return None

            latest_plan_lookup = _default_latest_plan_lookup
        self._latest_plan_lookup = latest_plan_lookup

    # ── Single-writer lease ──────────────────────────────────────────────────

    @contextmanager
    def _scheduler_lease(self, key: str) -> Iterator[bool]:
        """Non-blocking interprocess lease keyed tenant+plan+version. Yields True
        if acquired, False if another writer holds it (the caller no-ops)."""
        os.makedirs(self._lock_dir, exist_ok=True)
        safe = key.replace("/", "_").replace(":", "_")
        lock_path = os.path.join(self._lock_dir, f"scheduler-{safe}.lock")
        fd = os.open(lock_path, os.O_CREAT | os.O_RDWR, 0o644)
        acquired = False
        try:
            if fcntl is not None:
                try:
                    fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
                    acquired = True
                except OSError:
                    acquired = False
            else:  # pragma: no cover
                acquired = True
            yield acquired
        finally:
            if acquired and fcntl is not None:
                try:
                    fcntl.flock(fd, fcntl.LOCK_UN)
                except OSError:
                    pass
            os.close(fd)

    @contextmanager
    def _task_admission_lock(self, tenant_id: str, task_id: str) -> Iterator[None]:
        """BLOCKING interprocess lock keyed on the RESOURCE being admitted.

        `_scheduler_lease` is keyed `tenant:plan_record_id:version` — that is the
        AUTHORIZATION, not the resource. Two grants for the same plan at
        different versions are both legitimately active and both name the same
        Task in their frontier, so they take DIFFERENT lock keys and never
        serialize against one another (round-7 adversarial review F2). The
        "single-writer scheduler" guarantee therefore did not hold for the
        concurrent case that actually matters.

        The Task is what must not be admitted twice, so the Task is what is
        locked — held across the whole verdict → place → lease → dispatch
        window, so no second admitter can interleave between the decision and
        the effects that decision authorizes.

        Blocking rather than try-lock: the loser must WAIT and then evaluate
        admission against post-winner state, where check 16
        (`no_live_sibling_attempt`) refuses it on the merits. A try-lock that
        skipped would silently drop legitimate work from the pass.
        """
        os.makedirs(self._lock_dir, exist_ok=True)
        safe = f"{tenant_id}:{task_id}".replace("/", "_").replace(":", "_")
        lock_path = os.path.join(self._lock_dir, f"task-admission-{safe}.lock")
        fd = os.open(lock_path, os.O_CREAT | os.O_RDWR, 0o644)
        try:
            if fcntl is not None:
                fcntl.flock(fd, fcntl.LOCK_EX)
            yield
        finally:
            try:
                if fcntl is not None:
                    fcntl.flock(fd, fcntl.LOCK_UN)
            finally:
                os.close(fd)

    def _default_dep_lookup(self, dep_task_id: str) -> bool:
        """A dependency is satisfied iff it has a SUCCEEDED attempt with a Proof."""
        for att in self._store.attempts_for_task(dep_task_id):
            if att.status == _S.SUCCEEDED.value and att.proof_id:
                return True
        return False

    # ── One bounded pass ─────────────────────────────────────────────────────

    def run_scheduler_pass(
        self,
        grant: Any,
        *,
        role_resolver: Callable[[Any], Any] | None = None,
        verifier_role_resolver: Callable[[Any], str] | None = None,
        worker_candidates: list[dict[str, Any]] | None = None,
        compute_nodes: list[dict[str, Any]] | None = None,
        now: float | None = None,
    ) -> SchedulerPassReport:
        now = time.time() if now is None else now
        key = f"{getattr(grant, 'tenant_id', '')}:{getattr(grant, 'plan_record_id', '')}:v{getattr(grant, 'plan_version', 0)}"
        report = SchedulerPassReport(grant_ref=getattr(grant, "decision_ref", ""))

        with self._scheduler_lease(key) as acquired:
            report.acquired = acquired
            if not acquired:
                report.reason = "another scheduler tick holds the lease (no-op)"
                return report

            # Re-read canonical state AFTER lock acquisition (single-writer).
            #
            # This must be a REAL reread of the durable record, not a look at
            # the caller-passed object: the grant reference is captured before
            # the lock, so a revocation committed in between was invisible for
            # the life of that reference and the docstring above was false
            # (adversarial-review CRITICAL).
            fresh = None
            try:
                fresh = self._store.get_grant(getattr(grant, "decision_ref", ""))
            except Exception as exc:  # unreadable ledger → fail closed below
                logger.debug("scheduler grant reread failed: %s", exc)
            if fresh is None:
                report.reason = "grant not resolvable from the ledger (fail closed)"
                return report
            grant = fresh

            # Validity is MORE than the status field. `is_authorization_valid`
            # is the authority on it — it checks not_before, expires_at, and
            # plan supersession. The scheduler previously compared
            # `status != "active"` and nothing else, so a grant that was
            # EXPIRED or NOT-YET-VALID in substance, but whose status field
            # still read "active", minted attempts, acquired leases, and spent
            # real billed worker quota. The time window was decorative and
            # operator revocation was unenforced. `is_authorization_valid` had
            # ZERO production callers before this line.
            from substrate.execution.attempts.decisions import is_authorization_valid

            # SUPERSESSION IS AN ADMISSION-TIME QUESTION, NOT ONLY AN
            # APPROVE-TIME ONE (adversarial-review HIGH). `is_authorization_valid`
            # skips its supersession block when `latest_plan_lookup is None`, so
            # calling it bare here re-checked the time window but NEVER asked
            # whether the plan had moved on. Wiring the default lookup into the
            # decision source closed the approve-time hole only: a grant approved
            # while the plan was v1 kept admitting, leasing and dispatching after
            # the operator revised to v2, because the scheduler is the component
            # that runs every pass and it never asked the question.
            valid, why = is_authorization_valid(
                grant, latest_plan_lookup=self._latest_plan_lookup
            )
            if not valid:
                report.reason = f"authorization invalid: {why}"
                return report

            # Un-block TRANSIENTLY-blocked attempts so they retry this pass.
            # A CPU-gate refusal during lease acquisition parks the attempt in
            # BLOCKED (recoverable, non-terminal) — but nothing ever moved it
            # back, so a task that hit an overloaded host at admission stayed
            # wedged forever ("no eligible work") even after load dropped (field
            # run 20260725T205058Z, sixth control-plane layer). BLOCKED→READY is
            # a legal transition; re-arming here lets the very next admission try
            # again. Only transient (CPU-gate) blocks are re-armed — a block from
            # a real admission fault is left parked.
            self._rearm_transient_blocks(grant)

            frontier = list(getattr(grant, "task_frontier", []) or [])

            # (3) failure propagation: a Task with an exhausted FAILED attempt
            # blocks its dependents.
            failed_tasks = self._exhausted_failed_tasks(grant)

            for task_id in frontier:
                packet = self._queue.get_packet(task_id)
                if packet is None:
                    continue
                pkt_status = getattr(getattr(packet, "status", None), "value", "")
                # Only APPROVED|DELEGATED Tasks are admissible (activation done).
                if pkt_status not in ("approved", "delegated"):
                    continue

                # BOUNDED-AUTHORIZATION BINDING (adversarial-review CRITICAL).
                # A grant authorizes a SPECIFIC Task set, of a SPECIFIC plan
                # version, for a SPECIFIC tenant. This loop previously enforced
                # only "the id string appears in task_frontier" and then COPIED
                # the grant's tenant onto the attempt — it never COMPARED the
                # packet's own tenant or plan to the grant's. The checks that
                # would have bound it live in the readiness module, which no
                # production caller invokes.
                #
                # So any principal who got a grant approved for their own plan
                # could name ANY Task id in the system and have a real worker
                # execute it — in a lease worktree, spending billed quota,
                # mutating a repository — against another tenant's Task, another
                # plan, or a stale plan version. The store is tenant-blind, so
                # there was no downstream defense. The same defect class was
                # fixed on the API surface; this is the surface that actually
                # spends quota.
                if not self._packet_bound_to_grant(packet, grant, task_id, report):
                    continue
                # Already has a live or successful attempt? skip creation.
                existing = self._store.attempts_for_task(task_id)
                # …EXCEPT one still stuck at CREATED. `_create_attempt` returns
                # None when its created→READY transition loses a CAS race, and
                # the attempt is left CREATED for "the next pass to retry". But
                # CREATED is not terminal, so this very guard used to `continue`
                # past it — the attempt blocked its own retry and the Task was
                # stranded FOREVER, silently, even after the interference
                # cleared. Verified: a second, entirely healthy pass left it
                # `('created', 1)` and admitted nothing.
                #
                # Self-found while checking whether the N-1 fix could strand a
                # Task; the comment claiming the next pass retries it was false
                # until this branch existed. Promoting it here is the retry.
                stuck_created = [
                    a
                    for a in existing
                    if a.status == _S.CREATED.value and not a.is_terminal()
                ]
                live = [
                    a
                    for a in existing
                    if not a.is_terminal() and a.status != _S.CREATED.value
                ]
                if not live and stuck_created:
                    for orphan in stuck_created:
                        try:
                            self._transition(
                                orphan,
                                _S.READY.value,
                                (_S.CREATED.value,),
                                "scheduler",
                                "frontier ready (recovered from a lost transition)",
                            )
                        except (AttemptStoreConflict, AttemptLifecycleError) as exc:
                            logger.warning(
                                "attempt %s still cannot be made READY: %s",
                                orphan.attempt_id,
                                exc,
                            )
                    continue
                if live:
                    continue
                if any(a.status == _S.SUCCEEDED.value for a in existing):
                    continue

                # (2) dependency gate.
                deps = list(getattr(packet, "dependencies", []) or [])
                if any(d in failed_tasks for d in deps):
                    report.attempts_blocked.append(task_id)
                    continue
                if not all(self._dep_lookup(d) for d in deps):
                    continue  # predecessors not yet proven — not ready

                # (4) retry vs first attempt.
                prior_failed = [a for a in existing if a.status == _S.FAILED.value]
                attempt_number = len(existing) + 1 if existing else 1
                max_attempts = int(getattr(grant, "max_attempts_per_task", 1))
                if attempt_number > max_attempts:
                    report.attempts_blocked.append(task_id)
                    continue

                attempt = self._create_attempt(grant, packet, attempt_number, prior_failed)
                if attempt is None:
                    continue
                report.attempts_created.append(attempt.attempt_id)
                if prior_failed:
                    report.retries_created.append(attempt.attempt_id)

            # (5) admission up to concurrency.
            self._admit(
                grant,
                report,
                role_resolver,
                verifier_role_resolver,
                worker_candidates or [],
                compute_nodes or [],
                now,
            )
            return report

    # A block whose reason names the CPU gate is transient and safe to re-arm.
    _TRANSIENT_BLOCK_MARKERS = ("cpu gate", "cpu_gate", "host overloaded")

    def _rearm_transient_blocks(self, grant: Any) -> None:
        """Move CPU-gate-blocked attempts BLOCKED→READY so they retry.

        A CPU-gate refusal during lease acquisition is transient: the attempt is
        parked in BLOCKED (non-terminal) with a reason naming the CPU gate. Once
        load drops the attempt should be admissible again, but the admission loop
        only ever looks at READY attempts and the frontier loop SKIPS a task that
        has any non-terminal attempt — so without this re-arm the task is wedged
        permanently. Re-arm ONLY transient (CPU) blocks; a block from a genuine
        admission fault stays parked for inspection."""
        for task_id in getattr(grant, "task_frontier", []) or []:
            for att in self._store.attempts_for_task(task_id):
                if att.status != _S.BLOCKED.value:
                    continue
                reason = (getattr(att, "blocked_reason", "") or "").lower()
                if not any(m in reason for m in self._TRANSIENT_BLOCK_MARKERS):
                    continue
                try:
                    self._transition(
                        att,
                        _S.READY.value,
                        (_S.BLOCKED.value,),
                        "scheduler",
                        "re-arm after transient CPU-gate block",
                        updates={"blocked_reason": ""},
                    )
                except AttemptStoreConflict:
                    pass  # a concurrent pass already moved it — fine

    def _exhausted_failed_tasks(self, grant: Any) -> set[str]:
        max_attempts = int(getattr(grant, "max_attempts_per_task", 1))
        out: set[str] = set()
        for task_id in getattr(grant, "task_frontier", []) or []:
            attempts = self._store.attempts_for_task(task_id)
            failed = [a for a in attempts if a.status == _S.FAILED.value]
            if (
                failed
                and len(attempts) >= max_attempts
                and not any(a.status == _S.SUCCEEDED.value for a in attempts)
            ):
                out.add(task_id)
        return out

    @staticmethod
    def _packet_bound_to_grant(packet: Any, grant: Any, task_id: str, report: Any) -> bool:
        """Fail closed unless the packet is EXACTLY what the grant authorized.

        Compares the packet's OWN tenant and plan lineage against the grant's,
        rather than trusting frontier membership. Empty on either side is a
        MISMATCH, never a pass: an unbound packet or an unbound grant is
        precisely the case that must not execute.
        """
        scope = getattr(packet, "work_scope", None) or {}
        lineage = getattr(packet, "lineage", None) or {}
        if not isinstance(scope, dict):
            scope = {}
        if not isinstance(lineage, dict):
            lineage = {}

        pkt_tenant = str(scope.get("tenant_id", "") or "")
        grant_tenant = str(getattr(grant, "tenant_id", "") or "")
        if not pkt_tenant or not grant_tenant or pkt_tenant != grant_tenant:
            logger.error(
                "scheduler refused task %s: tenant %r is not the grant's %r",
                task_id,
                pkt_tenant,
                grant_tenant,
            )
            report.attempts_blocked.append(task_id)
            return False

        pkt_plan = str(lineage.get("plan_record_id", "") or "")
        grant_plan = str(getattr(grant, "plan_record_id", "") or "")
        if not pkt_plan or not grant_plan or pkt_plan != grant_plan:
            logger.error(
                "scheduler refused task %s: plan %r is not the grant's %r",
                task_id,
                pkt_plan,
                grant_plan,
            )
            report.attempts_blocked.append(task_id)
            return False
        return True

    def _create_attempt(
        self, grant: Any, packet: Any, attempt_number: int, prior_failed: list
    ) -> ExecutionAttempt | None:
        runner = self._mutation_runner or self._native_runner()
        attempt = ExecutionAttempt(
            task_id=getattr(packet, "packet_id", ""),
            objective_id=getattr(grant, "objective_id", ""),
            plan_record_id=getattr(grant, "plan_record_id", ""),
            plan_version=getattr(grant, "plan_version", 0),
            execution_authorization_ref=getattr(grant, "decision_ref", ""),
            attempt_number=attempt_number,
            tenant_id=getattr(grant, "tenant_id", ""),
            principal_id=getattr(grant, "principal_id", ""),
            membership_id=getattr(grant, "membership_id", ""),
            correlation_id=getattr(grant, "correlation_id", ""),
            previous_attempt_id=prior_failed[-1].attempt_id if prior_failed else "",
        )

        created_holder: dict[str, Any] = {}

        def _apply() -> tuple[str, bool]:
            created, is_new = self._store.create_attempt_idempotent(attempt)
            created_holder["attempt"] = created
            created_holder["is_new"] = is_new
            return (f"attempt {'created' if is_new else 'exists'}: {created.attempt_id}", True)

        runner(
            mutation_name="execution_attempt_create",
            intent=f"create attempt for task {attempt.task_id}",
            execute_fn=_apply,
            source="execution_attempts_scheduler",
            metadata={"task_id": attempt.task_id, "attempt_number": attempt_number},
        )
        created = created_holder.get("attempt")
        if created is None or not created_holder.get("is_new"):
            return None
        emit_execution_event(
            "execution.attempt_created",
            {
                "attempt_id": created.attempt_id,
                "task_id": created.task_id,
                "decision_ref": getattr(grant, "decision_ref", ""),
            },
            correlation_id=getattr(grant, "correlation_id", ""),
        )
        # created → ready.
        #
        # `_transition` now RAISES when the ledger does not show the target
        # status, instead of silently returning the stale attempt (H-1). That
        # is correct at the admission boundary, where a refused transition must
        # stop the attempt — but here it would escape `_create_attempt`, escape
        # the frontier loop, and ABORT THE WHOLE SCHEDULER PASS, killing work
        # for every OTHER Task in the frontier. Before H-1 this path degraded
        # silently; a fix that converts a one-Task hiccup into a fleet-wide
        # outage trades one defect for a worse one.
        #
        # Self-found while auditing the H-1 fix: reproduced by swallowing only
        # `execution_attempt_transition`, which aborted `run_scheduler_pass`
        # with `AttemptStoreConflict ... → ready did not commit`.
        #
        # So: this Task is dropped from THIS pass and stays CREATED. The NEXT
        # pass recovers it — but only because the frontier loop explicitly
        # promotes a stuck-CREATED attempt (see `stuck_created` above). When
        # this comment was first written that promotion did NOT exist: CREATED
        # is not terminal, so the loop's `not a.is_terminal()` guard skipped
        # straight past the orphan, which then blocked its own retry and
        # stranded the Task FOREVER. The claim "the next pass retries it" was
        # false for one commit; both halves now exist and are pinned by
        # `test_an_attempt_stranded_at_created_is_recovered_by_a_later_pass`.
        try:
            self._transition(
                created, _S.READY.value, (_S.CREATED.value,), "scheduler", "frontier ready"
            )
        except (AttemptStoreConflict, AttemptLifecycleError) as exc:
            logger.warning(
                "attempt %s could not be made READY this pass (%s); it stays "
                "CREATED and the next pass retries it",
                created.attempt_id,
                exc,
            )
            return None
        return created

    def _admit(
        self,
        grant,
        report,
        role_resolver,
        verifier_role_resolver,
        worker_candidates,
        compute_nodes,
        now,
    ) -> None:
        active = [
            a
            for a in self._store.active_attempts()
            if a.status in (_S.LEASED.value, _S.DISPATCHED.value, _S.RUNNING.value)
        ]
        slots = self._max_concurrency - len(active)
        if slots <= 0:
            return
        # `active_attempts()` reads the ENTIRE ledger — it is tenant-blind and
        # grant-blind, and the store is a shared multi-tenant, multi-plan file.
        # Admission must therefore re-establish the grant binding itself; it
        # cannot inherit it from the frontier loop (adversarial-review CRITICAL).
        #
        # Guarding only attempt CREATION left this door open: every READY
        # attempt in the whole store was leased, compiled and dispatched under
        # whatever grant the current pass happened to hold. An attacker's
        # entirely legitimate grant — with an EMPTY task_frontier, naming
        # nothing — leased and dispatched another tenant's Task. This is the
        # surface that spends billed quota and mutates repositories.
        #
        # Frontier membership is checked FIRST as a cheap narrowing, but it is
        # explicitly NOT the binding check: A-1 established that membership of
        # an id string proves nothing about ownership.
        frontier_ids = {str(t) for t in (getattr(grant, "task_frontier", []) or [])}
        ready = sorted(
            [
                a
                for a in self._store.active_attempts()
                if a.status == _S.READY.value
                and a.task_id in frontier_ids
                and str(getattr(a, "execution_authorization_ref", "")) == str(
                    getattr(grant, "decision_ref", "")
                )
            ],
            key=lambda a: (a.task_id, a.attempt_number),
        )
        for attempt in ready[:slots]:
            # Per-TASK lock (the resource), entered BEFORE the verdict and held
            # through dispatch: the state the verdict judged cannot change
            # between the decision and the effects it authorizes, and no second
            # admitter — another grant version, another process — can interleave.
            with self._task_admission_lock(
                str(getattr(grant, "tenant_id", "") or ""), str(attempt.task_id)
            ):
                packet = self._queue.get_packet(attempt.task_id)
                if packet is None:
                    continue
                role = role_resolver(packet) if role_resolver else None
                verifier = (
                    verifier_role_resolver(packet) if verifier_role_resolver else "role-verify-op"
                )

                # ── THE admission boundary ───────────────────────────────────
                # ONE canonical fail-closed authority, consumed ATOMICALLY here:
                # inside the single-writer scheduler lease, on the RE-READ packet
                # and the RE-READ grant, in the same transaction that leases and
                # dispatches. Nothing downstream re-interprets these conditions
                # and no earlier, staler assessment can authorize execution.
                #
                # Before this, `evaluate_execution_readiness`'s 15 checks had ZERO
                # production callers: the scheduler open-coded a partial subset
                # (tenant + plan + frontier + deps) and never asked the rest, so
                # `grant.role_ids`, `grant.allowed_tools` and `grant.cost_limit_usd`
                # — bounds the OPERATOR sets on the decision — were decorative, and
                # comments in lifecycle.py/placement.py described the absent checks
                # as already performed (round-3 finding R2-5, escalated to HIGH).
                verdict = authorize_admission(
                    packet=packet,
                    grant=grant,
                    attempt=attempt,
                    role_contract=role,
                    verifier_role_id=verifier,
                    plan_lookup=self._latest_plan_lookup,
                    attempts_for_task=self._store.attempts_for_task,
                )
                if not verdict.admitted:
                    logger.error(
                        "admission REFUSED for attempt %s (task %s): %s [%s]",
                        attempt.attempt_id,
                        attempt.task_id,
                        verdict.reason,
                        verdict.refusal_code,
                    )
                    report.attempts_blocked.append(attempt.task_id)
                    try:
                        self._transition(
                            attempt,
                            _S.BLOCKED.value,
                            (_S.READY.value,),
                            "scheduler",
                            f"admission refused: {verdict.refusal_code}",
                            updates={"blocked_reason": verdict.reason[:200]},
                        )
                    except AttemptStoreConflict:
                        pass
                    except AttemptLifecycleError as exc:
                        logger.debug("blocking refused attempt %s: %s", attempt.attempt_id, exc)
                    continue

                lease = None
                try:
                    assignment = self._place(
                        packet=packet,
                        grant=grant,
                        role_contract=role,
                        attempt_id=attempt.attempt_id,
                        worker_candidates=worker_candidates,
                        compute_nodes=compute_nodes,
                        verifier_role_id=verifier,
                        store=self._store,
                        mutation_runner=self._mutation_runner,
                    )
                    lease = self._leases.acquire(attempt=attempt, assignment=assignment, grant=grant)
                    attempt = self._transition(
                        attempt,
                        _S.LEASED.value,
                        (_S.READY.value,),
                        "scheduler",
                        "placed + leased",
                        updates={
                            "assignment_id": assignment.assignment_id,
                            "lease_id": lease.lease_id,
                            "verifier_role_id": assignment.verifier_role_id,
                        },
                    )
                    package = self._compile(
                        attempt=attempt, packet=packet, assignment=assignment, grant=grant
                    )
                    attempt = self._transition(
                        attempt,
                        _S.DISPATCHED.value,
                        (_S.LEASED.value,),
                        "scheduler",
                        "package sealed",
                        updates={
                            "instruction_package_hash": package.package_hash,
                            "worker_identity": assignment.worker_identity,
                            "max_turns": 30,
                            "timeout_seconds": 600,
                        },
                    )
                    report.attempts_admitted.append(attempt.attempt_id)
                    if self._dispatch is not None:
                        self._dispatch(
                            attempt=attempt,
                            assignment=assignment,
                            lease=lease,
                            package=package,
                            grant=grant,
                        )
                except Exception as exc:
                    logger.debug("admission of %s failed: %s", attempt.attempt_id, exc)
                    # RELEASE THE LEASE. It is acquired before the package is
                    # compiled, and compilation can now fail closed (a Task with
                    # undeclared mutation authority raises DispatchBlocked). Without
                    # this the lease survives a BLOCKED attempt — which is NOT a
                    # terminal status, so terminalization never releases it — and
                    # LeaseManager.acquire then refuses the task forever ("task
                    # already has an active lease"). Worse, each orphan lease holds
                    # a sandbox worktree, so TWO admission failures exhaust
                    # max_parallel=2 and wedge the entire run.
                    if lease is not None:
                        try:
                            self._leases.release(getattr(lease, "lease_id", ""), cleanup=True)
                        except Exception as rel:
                            logger.debug(
                                "lease release after failed admission of %s: %s",
                                attempt.attempt_id,
                                rel,
                            )
                    try:
                        self._transition(
                            attempt,
                            _S.BLOCKED.value,
                            (_S.READY.value, _S.LEASED.value),
                            "scheduler",
                            f"admission failed: {exc}",
                            updates={"blocked_reason": str(exc)[:200]},
                        )
                    except AttemptStoreConflict:
                        pass

    def _transition(self, attempt, to_status, expected, actor, reason, updates=None):
        runner = self._mutation_runner or self._native_runner()
        result_holder: dict[str, Any] = {}

        def _apply() -> tuple[str, bool]:
            updated = self._store.transition_cas(
                attempt.attempt_id,
                to_status,
                expected_record_version=attempt.record_version,
                expected_statuses=expected,
                actor=actor,
                reason=reason,
                updates=updates or {},
            )
            result_holder["attempt"] = updated
            return (f"{attempt.attempt_id} → {to_status}", True)

        runner(
            mutation_name="execution_attempt_transition",
            intent=f"transition attempt {attempt.attempt_id} to {to_status}",
            execute_fn=_apply,
            source="execution_attempts_scheduler",
            metadata={"attempt_id": attempt.attempt_id, "to_status": to_status},
        )
        updated = result_holder.get("attempt")
        if updated is not None:
            return updated

        # The holder is empty, so `_apply` did not complete. DO NOT return the
        # stale pre-transition attempt as if nothing were wrong: every real
        # governed runner CATCHES what `execute_fn` raises and returns a
        # response object instead of re-raising (`GovernedExecutionSpine._execute`,
        # `MutationRouter.execute`, `route_mutation_degraded`), so an
        # `AttemptStoreConflict` from `transition_cas` never reaches the
        # `except AttemptStoreConflict` handlers in this module. Silently
        # returning the stale attempt made a REFUSED transition indistinguishable
        # from a successful one — the caller then proceeds as though the attempt
        # had advanced (round-8 independent review H-1, executed and confirmed:
        # an illegal ready→dispatched jump returned status 'ready' with the
        # ledger unchanged and no signal).
        #
        # Same remedy as the lease claim (C-1): the durable ledger is the only
        # authority. Re-read it; if the attempt really did advance (a concurrent
        # writer, or a runner that persisted without populating the holder),
        # honour that. Otherwise raise so the caller fails closed.
        fresh = None
        try:
            fresh = self._store.get_attempt(attempt.attempt_id)
        except Exception as exc:  # unreadable ledger → fail closed
            logger.debug("attempt re-read failed for %s: %s", attempt.attempt_id, exc)
        if fresh is not None and str(getattr(fresh, "status", "")) == str(to_status):
            return fresh
        raise AttemptStoreConflict(
            f"transition {attempt.attempt_id} → {to_status} did not commit "
            f"(ledger status "
            f"{str(getattr(fresh, 'status', 'unreadable')) if fresh is not None else 'unreadable'})"
        )

    def _native_runner(self) -> Callable[..., Any]:
        from substrate.execution.intent.loop import _substrate_native_governed_mutation

        return _substrate_native_governed_mutation


__all__ = ["AttemptScheduler", "SchedulerPassReport"]
