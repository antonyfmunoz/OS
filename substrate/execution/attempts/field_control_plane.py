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
import os
import time
from dataclasses import dataclass, field
from typing import Any, Callable
from uuid import uuid4

logger = logging.getLogger(__name__)

# Deterministic role identities. The implementer role is distinct from the
# verifier role by construction (separation of duty; the placement + lifecycle
# guards re-check this). Frontend vs backend vs integration all use the same
# implementer role id here — the SoD invariant Wave 2 enforces is
# verifier ≠ worker, not per-task role uniqueness.
_IMPLEMENTER_ROLE_ID = "role-implementer-op"
_INTEGRATOR_ROLE_ID = "role-integrator-op"
_VERIFIER_ROLE_ID = "role-verifier-op"

# How long an UNCLAIMED dispatch envelope may wait in the inbox before it is
# reaped. This is the QUEUE budget and is deliberately distinct from the
# execution budget (``timeout_seconds``): a claimed envelope never expires under
# a running worker (finding C3).
_CLAIM_BUDGET_SECONDS = 1800.0


class _RecordView:
    """Attribute view over a store record dict.

    The store returns plain dicts, but ``verify_attempt`` reads its inputs with
    ``getattr`` — so passing the raw dict would make every field read as empty
    and the verifier would run blind even after the lookup was fixed (finding
    C4). Wrapping keeps the store's dict contract while satisfying the verifier.
    """

    __slots__ = ("_d",)

    def __init__(self, data: dict[str, Any]) -> None:
        self._d = dict(data or {})

    @classmethod
    def wrap(cls, data: Any) -> Any:
        if data is None or not isinstance(data, dict):
            return data
        return cls(data)

    def __getattr__(self, name: str) -> Any:
        try:
            return self._d[name]
        except KeyError as exc:
            raise AttributeError(name) from exc

    def to_dict(self) -> dict[str, Any]:
        return dict(self._d)


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
    # Tasks in the grant frontier that the scheduler skipped because their
    # packet is not APPROVED/DELEGATED yet (review W5). The scheduler skips
    # these with a bare `continue`, and the runner only logged when something
    # happened — so an activation that never transitioned the packets presented
    # as a HEALTHY-looking process doing nothing, forever.
    skipped_not_approved: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "grant_ref": self.grant_ref,
            "results_drained": self.results_drained,
            "succeeded": list(self.succeeded),
            "failed": list(self.failed),
            "admitted": list(self.admitted),
            "idle": self.idle,
            "skipped_not_approved": list(self.skipped_not_approved),
            "errors": list(self.errors),
        }


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
            # Unique per DISPATCH, not per attempt (review W6). `d-<attempt_id>`
            # collided whenever an attempt was re-dispatched, and the spool
            # filename is `<sequence>-<dispatch_id>.json` written with os.replace
            # — a silent overwrite that stranded the clobbered attempt. `_seq`
            # also reset to 0 on runner restart, so a fresh dispatch could
            # overwrite a pending envelope for a DIFFERENT attempt.
            unique = uuid4().hex[:8]
            self._spool.enqueue(
                DispatchEnvelope(
                    dispatch_id=f"d-{attempt.attempt_id}-{unique}",
                    attempt_id=attempt.attempt_id,
                    task_id=attempt.task_id,
                    authorization_ref=getattr(grant, "decision_ref", ""),
                    package_hash=getattr(package, "package_hash", ""),
                    lease_id=getattr(lease, "lease_id", ""),
                    worktree_path=getattr(lease, "worktree_path", ""),
                    # The AUTHORIZED base the worker attributes its artifacts
                    # against. Without it the worker fell back to "HEAD", making
                    # the range `HEAD..HEAD` — empty by definition.
                    base_commit=str(getattr(lease, "snapshot_ref", "") or ""),
                    nonce=uuid4().hex,  # anti-replay: must not reset on restart
                    sequence=self._seq,
                    # CLAIM budget, NOT the execution budget (finding C3). This
                    # bounds how long an UNCLAIMED envelope may wait; once
                    # claimed it never expires under the running worker.
                    # Previously this was now+timeout_seconds for BOTH A and B,
                    # so B was quarantined while A held the full 600s.
                    expires_at=time.time() + _CLAIM_BUDGET_SECONDS,
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
            lease_lookup=self._lease_lookup,
            packet_lookup=self._packet_lookup,
            independent_checks_for=self._independent_checks_for,
            scheduler_pass_kwargs=dict(
                grant=grant,
                role_resolver=_default_role_resolver,
                verifier_role_resolver=_verifier_role_resolver,
                worker_candidates=_worker_candidates(),
                compute_nodes=_compute_nodes(),
            ),
        )

    def _assignment_lookup(self, assignment_id: str) -> Any:
        """Resolve the durable FleetAssignment via the REAL store API.

        This previously called ``store.list_assignments()`` — a method that does
        not exist — behind a ``getattr`` guard, so it silently returned None for
        every attempt and the verifier ran with no assignment context (finding
        C4). ``get_assignment`` is the actual durable accessor.
        """
        if not assignment_id:
            return None
        getter = getattr(self._store, "get_assignment", None)
        if not callable(getter):
            raise AttributeError(
                "ExecutionAttemptStore has no get_assignment(); refusing to verify "
                "without assignment context"
            )
        return _RecordView.wrap(getter(assignment_id))

    def _packet_lookup(self, task_id: str) -> Any:
        """The canonical WorkPacket for a Task — the diff-scope AUTHORITY (C-1).

        Returns the packet AS PERSISTED. The writable-path authority is a
        first-class field on its requirements contract
        (``writable_path_scope`` + ``scope_declared``), seeded at
        materialization by ``seed_scope_from_label``.

        It is deliberately NOT synthesized here from a semantic label. Doing so
        would mean the enforced scope is whatever the verifier recomputed this
        run rather than what the Task contract actually records — and it would
        route mutation authority through descriptive lineage, which
        ``EvidenceRef`` prohibits ("Evidence is provenance — it can never be a
        mutation authority"). A packet whose contract declares no scope fails
        closed inside ``verify_attempt``.
        """
        if not task_id:
            return None
        return self._queue.get_packet(task_id)

    def _independent_checks_for(self, attempt: Any) -> Callable[[Any], list[Any]] | None:
        """Independent checks the VERIFIER runs itself for this attempt.

        Runs the fixture's own test suite in the lease worktree, so the verdict
        rests on a signal the verifier produced — not on the worker's narrative.
        Returns None when no fixture is wired (the context check then carries the
        weight); the qualification asserts a real check ran.
        """
        fixture = os.path.join(self._targets_dir, "fixture")
        if not os.path.isdir(fixture):
            return None

        def _checks(att: Any) -> list[Any]:
            from substrate.execution.attempts.verification import VerificationCheck
            from substrate.execution.cpu_gate import gated_subprocess_run

            lease = self._lease_lookup(getattr(att, "lease_id", "") or "")
            worktree = str(getattr(lease, "worktree_path", "") or "") if lease else ""
            target = worktree if worktree and os.path.isdir(worktree) else fixture
            result = gated_subprocess_run(
                ["python3", "-m", "pytest", "-q", "--timeout=120"],
                caller="wave2_verifier_independent_tests",
                timeout=300,
                cwd=target,
            )
            if result is None:
                return [
                    VerificationCheck(
                        check_id="independent_tests",
                        kind="tests",
                        ok=False,
                        detail="verifier test run skipped by CPU gate — cannot confirm",
                    )
                ]
            return [
                VerificationCheck(
                    check_id="independent_tests",
                    kind="tests",
                    ok=result.returncode == 0,
                    detail=f"pytest rc={result.returncode} in {target}",
                )
            ]

        return _checks

    def _lease_lookup(self, lease_id: str) -> Any:
        """Resolve the durable EnvironmentLease (never silently None)."""
        if not lease_id:
            return None
        getter = getattr(self._store, "get_lease", None)
        if not callable(getter):
            return None
        return _RecordView.wrap(getter(lease_id))

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
                report.skipped_not_approved = self._not_approved_frontier(grant)
            except Exception as exc:  # a bad grant never stalls the others
                # Surface the TEXT (review W8): the runner previously logged only
                # `errors=N`, so a systematic failure presented as a silent
                # counter with no cause.
                report.errors.append(f"{type(exc).__name__}: {exc}")
                logger.warning("field control-plane cycle failed: %s", exc, exc_info=True)
                logger.debug("field control-plane cycle failed: %s", exc, exc_info=True)
            reports.append(report)
        return reports

    def _not_approved_frontier(self, grant: Any) -> list[str]:
        """Frontier tasks whose packet is not yet APPROVED/DELEGATED.

        The scheduler silently skips these, so without reporting them an
        activation that failed to transition the packets looks identical to
        "no work to do" (review W5).
        """
        out: list[str] = []
        for task_id in list(getattr(grant, "task_frontier", []) or []):
            packet = self._queue.get_packet(task_id)
            if packet is None:
                out.append(f"{task_id}(missing)")
                continue
            status = getattr(getattr(packet, "status", None), "value", "")
            if status not in ("approved", "delegated"):
                out.append(f"{task_id}({status or 'unknown'})")
        return out

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
