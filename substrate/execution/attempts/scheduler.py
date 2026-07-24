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

from substrate.execution.attempts.events import emit_execution_event
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
            if getattr(grant, "status", "") != "active":
                report.reason = f"grant {grant.status} not active"
                return report

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
                # Already has a live or successful attempt? skip creation.
                existing = self._store.attempts_for_task(task_id)
                if any(not a.is_terminal() for a in existing):
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
        self._transition(
            created, _S.READY.value, (_S.CREATED.value,), "scheduler", "frontier ready"
        )
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
        ready = sorted(
            [a for a in self._store.active_attempts() if a.status == _S.READY.value],
            key=lambda a: (a.task_id, a.attempt_number),
        )
        for attempt in ready[:slots]:
            packet = self._queue.get_packet(attempt.task_id)
            if packet is None:
                continue
            role = role_resolver(packet) if role_resolver else None
            verifier = (
                verifier_role_resolver(packet) if verifier_role_resolver else "role-verify-op"
            )
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
        return result_holder.get("attempt", attempt)

    def _native_runner(self) -> Callable[..., Any]:
        from substrate.execution.intent.loop import _substrate_native_governed_mutation

        return _substrate_native_governed_mutation


__all__ = ["AttemptScheduler", "SchedulerPassReport"]
