"""Wave 2 field control-plane driver (run-scoped — NOT a persistent supervisor).

This is the HOST-side control-plane half of the field execution loop. The
candidate operator (in its container) surfaces the execution-authorization
Decision in the HUD and, on approve, activates the grant + transitions the
authorized Tasks PLANNED→APPROVED in the SHARED ``ExecutionAttemptStore`` /
WorkPacketQueue (both under ``UMH_STATE_DIR`` = the candidate's state mount,
visible to host and container alike). But nothing INSIDE the container drives a
scheduler pass or writes dispatch envelopes — the candidate is deliberately
mesh-less and worker-less (workers cannot run in a container; ``cc_sdk`` refuses
inside ``/.dockerenv``). This driver is what closes that seam.

It composes the REAL, already-tested substrate pieces against the shared ledger
and the run's signed spool:

    active grant + WorkPacketQueue (shared candidate state)
      → AttemptScheduler (real place_attempt / LeaseManager over a real
        SandboxManager rooted at the fixture repo / compile_attempt_package /
        a spool-writing dispatch_fn that consults the field-failure policy)
      → ControlPlanePoller (real verify_attempt; drains the outbox the host
        WORKER runner fills, advances the canonical ledger, re-runs the
        scheduler so the newly-unblocked frontier dispatches)

The WORKER half — claim inbox → run the real isolated Claude-CLI worker → write
signed outbox result — is ``scripts/wave2_attempt_runner.py``'s existing loop.
This driver and that worker loop share ONE spool; running both is the full
field loop. Ownership boundaries hold exactly as in the no-quota rehearsal
(``tests/test_wave2_harness_rehearsal.py``), with real components swapped for the
stubs: the store is the sole current truth; the spool is ephemeral transport;
the verifier identity is always distinct from the worker; a worker's self-report
is never trusted to complete a Task.

Imports only downward (substrate + same-package). Never touches
transports/services/adapters.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from typing import Any, Callable

logger = logging.getLogger(__name__)

# Deterministic role identities. The implementer role is distinct from the
# verifier role by construction (separation of duty; the placement + lifecycle
# guards re-check this). Frontend vs backend vs integration all use the same
# implementer role id here — the SoD invariant Wave 2 enforces is
# verifier ≠ worker, not per-task role uniqueness.
_IMPLEMENTER_ROLE_ID = "role-implementer-op"
_INTEGRATOR_ROLE_ID = "role-integrator-op"
_VERIFIER_ROLE_ID = "role-verifier-op"


@dataclass
class _RoleView:
    """Minimal RoleContract shape the placement pipeline reads."""

    role_id: str
    allowed_tools: list[str] = field(default_factory=lambda: ["shell", "Edit", "Write"])
    prohibited_skill_ids: list[str] = field(default_factory=list)


@dataclass
class ControlPlaneCycleReport:
    """What one driver cycle did — truthful, side-effect-free summary."""

    grant_ref: str = ""
    results_drained: int = 0
    succeeded: list[str] = field(default_factory=list)
    failed: list[str] = field(default_factory=list)
    admitted: list[str] = field(default_factory=list)
    idle: bool = False
    errors: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "grant_ref": self.grant_ref,
            "results_drained": self.results_drained,
            "succeeded": list(self.succeeded),
            "failed": list(self.failed),
            "admitted": list(self.admitted),
            "idle": self.idle,
            "errors": list(self.errors),
        }


def _role_resolver_for(task_id: str) -> Callable[[Any], Any]:
    """Return a role resolver bound to the implementer identity for this task.

    An integration Task (id starts with the integrator marker) resolves the
    integrator role; every other implementation Task resolves the implementer
    role. Both are ≠ the verifier role (SoD).
    """
    lowered = task_id.lower()
    is_integration = "integrat" in lowered or lowered.endswith("-c") or lowered == "c"
    role_id = _INTEGRATOR_ROLE_ID if is_integration else _IMPLEMENTER_ROLE_ID

    def _resolve(_packet: Any) -> Any:
        return _RoleView(role_id=role_id)

    return _resolve


def _default_role_resolver(_packet: Any) -> Any:
    return _RoleView(role_id=_IMPLEMENTER_ROLE_ID)


def _verifier_role_resolver(_packet: Any) -> str:
    return _VERIFIER_ROLE_ID


def _worker_candidates() -> list[dict[str, Any]]:
    """The single real worker candidate: the host Claude-CLI worker.

    Its capabilities cover the fixture Tasks' required capabilities. The
    placement ranker is deterministic (single candidate → stable winner).
    """
    return [
        {
            "worker_identity": "cc-cli@vps-host",
            "agent_type": "developer_agent",
            "capabilities": [
                "code_write",
                "code_read",
                "shell",
                "git",
                "test_run",
                "integration",
            ],
            "reliability": 0.9,
            "model_profile": {"model": "claude-opus", "harness": "cc_cli_worktree"},
            "harness_profile": {"harness": "cc_cli_worktree"},
        }
    ]


def _compute_nodes() -> list[dict[str, Any]]:
    """The VPS host is the one compute node for field workers."""
    return [{"node_id": "vps-host", "headroom": 2}]


class FieldControlPlaneDriver:
    """Run-scoped host-side control-plane loop over the shared ledger + spool.

    Constructed with the shared store/queue (pointed at the candidate state via
    ``UMH_STATE_DIR``), the run's ``DispatchSpool``, a ``SandboxManager`` rooted
    at the fixture repo, and the failure-injection ``targets_dir`` (so the
    ``.inject_failure`` marker genuinely revokes tools on the arming pass).

    ``run_cycle()`` performs exactly one bounded control-plane pass per ACTIVE
    grant: drain the worker outbox → apply canonical transitions with an
    independent verifier → re-run the scheduler so the next frontier is admitted
    and its dispatch envelopes are written to the inbox for the worker loop.
    """

    def __init__(
        self,
        *,
        store: Any,
        work_queue: Any,
        spool: Any,
        sandbox_manager: Any,
        targets_dir: str,
        mutation_runner: Callable[..., Any] | None = None,
        lock_dir: str | None = None,
        proof_runtime: Any | None = None,
    ) -> None:
        self._store = store
        self._queue = work_queue
        self._spool = spool
        self._sandbox = sandbox_manager
        self._targets_dir = targets_dir
        self._mutation_runner = mutation_runner
        self._lock_dir = lock_dir
        # The verifying→succeeded lifecycle guard requires a real AttemptProof
        # (proof_id). Wire the ONE canonical ProofRuntime (honors UMH_STATE_DIR →
        # the shared candidate proof store) so a passing verification actually
        # mints a proof; without it, every passing attempt would be refused
        # succeeded for lack of a proof.
        if proof_runtime is None:
            from substrate.organism.proof_runtime import ProofRuntime

            proof_runtime = ProofRuntime()
        self._proof_runtime = proof_runtime
        self._seq = 0

    # ── the signed spool dispatch_fn (real transport) ────────────────────────

    def _dispatch_fn(self) -> Callable[..., None]:
        from substrate.execution.attempts.field_failure_policy import disallowed_tools_for
        from substrate.execution.attempts.spool import DispatchEnvelope

        def dispatch(
            *, attempt: Any, assignment: Any, lease: Any, package: Any, grant: Any
        ) -> None:
            self._seq += 1
            # Consult the field-failure policy so `inject-failure --variant
            # tools-revoked-a` genuinely revokes Edit/Write on A's FIRST attempt
            # (the marker is ACTUALLY consumed here — review W1). A clean run has
            # no marker → empty revocation.
            revoked = disallowed_tools_for(
                targets_dir=self._targets_dir,
                task_id=getattr(attempt, "task_id", ""),
                attempt_number=int(getattr(attempt, "attempt_number", 1) or 1),
            )
            self._spool.enqueue(
                DispatchEnvelope(
                    dispatch_id=f"d-{attempt.attempt_id}",
                    attempt_id=attempt.attempt_id,
                    task_id=attempt.task_id,
                    authorization_ref=getattr(grant, "decision_ref", ""),
                    package_hash=getattr(package, "package_hash", ""),
                    lease_id=getattr(lease, "lease_id", ""),
                    worktree_path=getattr(lease, "worktree_path", ""),
                    nonce=f"n{self._seq}",
                    sequence=self._seq,
                    expires_at=time.time() + float(getattr(attempt, "timeout_seconds", 600) or 600),
                    disallowed_tools=list(revoked),
                    max_turns=int(getattr(attempt, "max_turns", 30) or 30),
                    timeout_seconds=int(getattr(attempt, "timeout_seconds", 600) or 600),
                    payload_hash=getattr(package, "package_hash", ""),
                )
            )

        return dispatch

    # ── assemble the real scheduler + poller ─────────────────────────────────

    def _build_scheduler(self) -> Any:
        from substrate.execution.attempts.dispatch import compile_attempt_package
        from substrate.execution.attempts.leases import LeaseManager
        from substrate.execution.attempts.placement import place_attempt
        from substrate.execution.attempts.scheduler import AttemptScheduler

        lease_manager = LeaseManager(
            self._store, self._sandbox, mutation_runner=self._mutation_runner
        )
        return AttemptScheduler(
            self._store,
            work_queue=self._queue,
            placement_fn=place_attempt,
            lease_manager=lease_manager,
            compile_fn=compile_attempt_package,
            dispatch_fn=self._dispatch_fn(),
            max_concurrency=2,
            mutation_runner=self._mutation_runner,
            lock_dir=self._lock_dir,
        )

    def _build_poller(self, scheduler: Any, grant: Any) -> Any:
        from substrate.execution.attempts.poller import ControlPlanePoller
        from substrate.execution.attempts.verification import verify_attempt

        return ControlPlanePoller(
            store=self._store,
            spool=self._spool,
            scheduler=scheduler,
            verify_fn=verify_attempt,
            proof_runtime=self._proof_runtime,
            assignment_lookup=self._assignment_lookup,
            scheduler_pass_kwargs=dict(
                grant=grant,
                role_resolver=_default_role_resolver,
                verifier_role_resolver=_verifier_role_resolver,
                worker_candidates=_worker_candidates(),
                compute_nodes=_compute_nodes(),
            ),
        )

    def _assignment_lookup(self, assignment_id: str) -> Any:
        lister = getattr(self._store, "list_assignments", None)
        if not callable(lister):
            return None
        for asn in lister() or []:
            if getattr(asn, "assignment_id", "") == assignment_id:
                return asn
        return None

    # ── one bounded cycle ────────────────────────────────────────────────────

    def run_cycle(self) -> list[ControlPlaneCycleReport]:
        """One control-plane pass across every ACTIVE grant in the shared ledger.

        For each ACTIVE grant, run ONE poller pass: drain the worker outbox →
        apply canonical transitions with an independent verifier → run one
        scheduler pass so the next frontier is admitted and its dispatch
        envelopes are written to the inbox. The poller ALWAYS runs the scheduler
        after draining (even with an empty outbox), so the very first cycle
        admits the initial frontier — no separate admission pass is needed (a
        second, direct pass would re-enter admission for still-dispatched
        attempts and conflict on their active leases). Idempotent and safe to
        call repeatedly — terminal attempts are no-ops.
        """
        reports: list[ControlPlaneCycleReport] = []
        grants = [g for g in self._store.active_grants() if getattr(g, "status", "") == "active"]
        for grant in grants:
            report = ControlPlaneCycleReport(grant_ref=getattr(grant, "decision_ref", ""))
            try:
                scheduler = self._build_scheduler()
                poller = self._build_poller(scheduler, grant)
                pass_report = poller.run_pass()
                report.results_drained = pass_report.results_drained
                report.succeeded = list(pass_report.succeeded)
                report.failed = list(pass_report.failed)
                report.admitted = list(pass_report.scheduler_admitted)
                report.idle = (
                    report.results_drained == 0
                    and not report.admitted
                    and not self._has_live_attempts(grant)
                )
                report.errors = list(pass_report.errors)
            except Exception as exc:  # a bad grant never stalls the others
                report.errors.append(str(exc))
                logger.debug("field control-plane cycle failed: %s", exc, exc_info=True)
            reports.append(report)
        return reports

    def _has_live_attempts(self, grant: Any) -> bool:
        plan_id = getattr(grant, "plan_record_id", "")
        for att in self._store.attempts_for_plan(plan_id):
            if not att.is_terminal():
                return True
        return False


__all__ = [
    "FieldControlPlaneDriver",
    "ControlPlaneCycleReport",
]
