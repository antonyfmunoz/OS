#!/usr/bin/env python3
"""Wave 2 host-side attempt runner (run-scoped — NOT a persistent supervisor).

Ties the governed control plane to real, isolated workers. Started/stopped by the
field dispatcher for the duration of one qualification run. It:

1. verifies enforced host isolation is available (bwrap) — refuses to run
   otherwise (Amendment v1 clause 4);
2. claims signed dispatch envelopes from the spool (bad/expired → quarantined);
3. does NOT itself verify grant status or scope hash. That claim used to be
   here and was false: independent review (R9) grepped this file and found no
   such check. The real authority is `attempts/admission.py` (attempt↔grant
   binding, task-in-frontier, tenant, plan+version, TOCTOU packet recheck),
   which gates lease + dispatch before an envelope is ever enqueued, and
   `attempts/dispatch.py`, which seals authorization_ref / authorized_scope_hash
   / authorized_tasks into the package hash the worker is bound to;
4. runs the policy-selected model worker in the lease worktree under bwrap isolation;
5. writes a SIGNED result to the spool outbox — never mutates the attempt ledger
   directly (the control-plane poller owns canonical transitions);
6. receives NO signing secret in the worker subprocess env.

The runner holds the run's dispatch secret; the WORKER never does. The
ExecutionAttemptStore remains the sole current execution truth — this runner only
moves work and reports results over the ephemeral spool.
"""

from __future__ import annotations

import argparse
import json
import os
import signal
import sys
import time
from concurrent.futures import FIRST_COMPLETED, ThreadPoolExecutor, wait
from typing import Any

# An INFLIGHT claim older than this with no result is treated as abandoned by a
# crashed worker and returned to the inbox. Generously above the 600s execution
# budget so a slow-but-live worker is never stolen from.
_INFLIGHT_RECOVERY_SECONDS = 1200.0

# How often a live claimant tends its own claims while waiting on workers.
# Must be comfortably under _INFLIGHT_RECOVERY_SECONDS so a long-running but
# HEALTHY worker is never declared abandoned (finding NEW-2).
_HEARTBEAT_SECONDS = 60.0

# Log an idle cycle every N iterations so a stall is visible without flooding.
_IDLE_LOG_EVERY = 30

# BOUNDED control-plane failure policy. A driver fault used to be logged
# "(continuing)" with no bound at all, so a permanently broken control plane
# burned the whole run budget while the process looked healthy. Consecutive
# failures catch a hard-down driver fast; the cumulative bound catches one
# that flaps just often enough to keep resetting the consecutive counter.
_CP_MAX_CONSECUTIVE_ERRORS = 5
_CP_MAX_TOTAL_ERRORS = 20

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if REPO not in sys.path:
    sys.path.insert(0, REPO)

from substrate.execution.attempts.worker_model_executor import run_worker_in_lease  # noqa: E402


class ControlPlaneFailureBudget:
    """The bounded control-plane failure policy, as executable state.

    Extracted to module scope so the regression tests drive THIS accounting
    rather than a replay of it. Independent review (R9) killed the replay-style
    tests with two mutants a simulation cannot see -- a counter that never
    increments (`+= 0`) and a reset moved into the `except` branch (so it always
    resets). Both leave the constants and the algorithm's *description* intact
    while changing when the bound fires, from cycle 5 to cycle 20.
    """

    def __init__(self, max_consecutive: int, max_total: int) -> None:
        self.max_consecutive = max_consecutive
        self.max_total = max_total
        self.consecutive = 0
        self.total = 0
        self.last_error = ""

    def record_success(self) -> None:
        """A completed cycle clears the consecutive budget (never the total)."""
        self.consecutive = 0

    def record_failure(self, exc: BaseException) -> None:
        self.consecutive += 1
        self.total += 1
        self.last_error = f"{type(exc).__name__}: {exc}"

    @property
    def exhausted(self) -> bool:
        return self.consecutive >= self.max_consecutive or self.total >= self.max_total


def package_from_envelope(envelope: Any) -> Any:
    """Rebuild the canonical execution package from a SIGNED dispatch envelope.

    Finding F-2. This used to be a hand-built 4-attribute stand-in with an
    invented instruction string and NO ``governance_constraints``. The effect was
    not cosmetic: ``compile_attempt_package`` sealed the Task's
    ``writable_path_scope`` correctly and the runner then threw it away on the
    far side of the spool, so the launcher's fail-closed guard refused 100% of
    real dispatches. The hard write barrier — proven against 36 adversarial
    vectors — was mechanically unreachable in the shipped path.

    Every field comes from the HMAC-signed envelope, so the worker runs the
    instructions the control plane compiled under the scope the control plane
    sealed. Nothing is invented here, and nothing worker-controlled can reach it:
    the runner reads only the signed envelope, and the worker never holds the
    signing secret.

    Module-level (not a closure inside ``_run_one_claim``) so tests can drive the
    REAL reconstruction. A test that rebuilds this shape inline proves nothing
    about the runner — that is how the original defect survived a green suite.
    """

    class _Package:
        role_instructions = getattr(envelope, "role_instructions", "")
        operation_instructions = getattr(envelope, "operation_instructions", "")
        ordered_context = list(getattr(envelope, "ordered_context", None) or [])
        operation_identity = dict(getattr(envelope, "operation_identity", None) or {})
        governance_constraints = list(getattr(envelope, "governance_constraints", None) or [])
        verification_requirements = list(getattr(envelope, "verification_requirements", None) or [])

    return _Package()


def _log(msg: str) -> None:
    print(f"[wave2-runner] {msg}", flush=True)


class _Shutdown(BaseException):
    """Raised out of the signal handler to unwind the loop into its finally.

    A BaseException (not Exception) so the worker-fault ``except Exception`` inside
    the loop never swallows it — a SIGTERM must always reach the run's finally,
    where the ONE run-teardown authority sweeps every credential home. This is the
    SEC-C1 fix: the default SIGTERM disposition terminated the process with no
    unwinding, leaving worker/verifier homes (and the operator's OAuth token) on
    disk. The handler converts the signal into controlled unwinding — it does NOT
    maintain a second cleanup implementation.
    """


def _install_signal_handlers() -> None:
    def _handler(signum, _frame):  # noqa: ANN001
        _log(f"received signal {signum} — unwinding into run teardown")
        raise _Shutdown()

    for sig in (signal.SIGTERM, signal.SIGINT):
        signal.signal(sig, _handler)


def _register_host_control_plane(store: Any) -> Any:
    """Build + register a HOST-SIDE governed control plane so the driver's
    execution mutations are governed, NOT degraded.

    The host runner is a separate process from the candidate container; the
    organism daemon (and its GovernedExecutionSpine) live INSIDE the container,
    so nothing is registered on the canonical ``organism_port`` in the runner's
    process. The driver creates/leases/dispatches attempts through governed
    mutations (``execution_attempt_create`` etc.), all of which have
    ``degraded_mode_allowed=False``. With no spine registered,
    ``_substrate_native_governed_mutation`` fell back to
    ``route_mutation_degraded`` and every one fail-closed — the grant activated,
    the packet was APPROVED, the driver reached admission, and then refused to
    create the attempt ("control plane unavailable — FAIL CLOSED on
    execution_attempt_create") so NO worker ran (field run 20260725T202237Z,
    the fifth control-plane layer).

    The spine is entirely substrate-level and host-constructible. We build the
    minimal real spine (event spine + execution mode + mutation registry +
    journal) plus the clause-5 ``authorization_lookup`` that resolves a grant by
    decision_ref from the SAME shared store (fresh per call), and register it on
    the canonical port. The native runner then routes through
    ``MutationRouter → GovernedExecutionSpine`` in-process — a real, audited,
    non-degraded control plane. The organism-like holder exposes exactly the two
    attributes the native runner reads (``governed_spine`` /
    ``mutation_registry``); nothing else in the daemon is needed host-side.
    """
    from substrate.organism.event_spine import get_shared_event_spine
    from substrate.organism.execution_journal import ExecutionJournal
    from substrate.organism.execution_modes import ExecutionMode, ExecutionModeManager
    from substrate.organism.governed_spine import GovernedExecutionSpine
    from substrate.organism.mutation_registry import MutationRegistry
    from substrate.sockets.organism_port import get_organism, register_organism_accessor
    from substrate.state.runtime_paths import runtime_state_path

    # If something already registered a daemon in this process, don't shadow it.
    existing = None
    try:
        existing = get_organism()
    except Exception:  # noqa: BLE001 — treat an unresolvable accessor as absent
        existing = None
    if existing is not None:
        return existing

    event_spine = get_shared_event_spine()  # persisted, honors UMH_STATE_DIR
    registry = MutationRegistry()  # auto-registers execution_* specs
    journal = ExecutionJournal(
        persist_path=str(runtime_state_path("execution", "host_control_plane_journal.jsonl"))
    )
    # AUTONOMOUS: this is a headless run-scoped host loop consuming an already
    # HUD-authorized grant — there is no interactive operator to ASSIST. The
    # per-action authority still comes from the ACTIVE grant (clause 5), which
    # the authorization_lookup below enforces on every authorization-bound action.
    mode = ExecutionModeManager(initial_mode=ExecutionMode.AUTONOMOUS, event_spine=event_spine)
    spine = GovernedExecutionSpine(
        event_spine=event_spine,
        execution_mode=mode,
        mutation_registry=registry,
        journal=journal,
        # clause 5 lookup, wired for correctness but INERT on the field path.
        # The previous comment claimed execution_attempt_dispatch "carries an
        # authorization_ref" — it does not. Independent review (R9) enumerated
        # every ActionEnvelope/MutationRequest producer in the tree: only
        # mutation_router forwards these fields, and BOTH production
        # MutationRequest producers on the Wave 2 path
        # (intent/loop.py, transports/api/governed.py) leave authorization_ref
        # empty, so governed_spine._check_authorization_scope returns at its
        # `if not auth_ref` early-out and this lookup is never invoked.
        # Kept because it is free and correct the moment an authorization-bound
        # envelope exists; NOT counted as an operational Wave 2 control. The
        # live equivalent invariant is in attempts/admission.py.
        authorization_lookup=store.get_grant,
    )

    class _HostControlPlane:
        governed_spine = spine
        mutation_registry = registry

    holder = _HostControlPlane()
    register_organism_accessor(lambda: holder)
    _log("host control plane registered (governed spine live — mutations NOT degraded)")
    return holder


def _build_control_plane_driver(
    *, spool: Any, fixture_repo: str, targets_dir: str, leases_dir: str
) -> Any:
    """Assemble the host-side control-plane driver over the shared candidate
    ledger (via UMH_STATE_DIR) and this run's spool. Returns None if the shared
    state / fixture is not resolvable (the runner then behaves as worker-only)."""
    from substrate.execution.attempts.field_control_plane import FieldControlPlaneDriver
    from substrate.execution.attempts.store import ExecutionAttemptStore
    from substrate.organism.universal_work_queue import UniversalWorkQueue
    from substrate.organism.worktree_sandbox import SandboxManager

    # SEALED BY DEFAULT. This is the governed Wave 2 run entry point, so the
    # attempt-creation boundary starts closed and is opened only by a positively
    # verified execution declaration (FieldControlPlaneDriver applies it below).
    # Without this flag the store would start permissive, which is exactly the
    # default that five reproduced bypasses walked through.
    store = ExecutionAttemptStore(governed_run=True)  # honors UMH_STATE_DIR
    queue = UniversalWorkQueue()  # honors UMH_STATE_DIR
    sandbox = SandboxManager(
        repo_root=fixture_repo,
        worktree_base=leases_dir,
        store_dir=os.path.join(targets_dir, "sandboxes"),
        max_parallel=2,
    )
    # Register the host governed control plane BEFORE building the driver so the
    # driver's mutations route through a live spine (never degraded). The driver
    # leaves mutation_runner=None → the scheduler/lease manager resolve the
    # native runner, which now finds the spine we just registered.
    _register_host_control_plane(store)
    return FieldControlPlaneDriver(
        store=store,
        work_queue=queue,
        spool=spool,
        sandbox_manager=sandbox,
        targets_dir=targets_dir,
        # PRE-QUOTA GRAPH-SHAPE GATE, on the path that actually spends quota.
        # Enabled whenever the run declares a multi-lane decomposition: the
        # gate then refuses a wrong-shaped graph BEFORE any dispatch envelope
        # is written. Without this the gate exists but is dark — the exact
        # "contract right, production unwired" shape that produced the last ten
        # defect layers. A single-Task smoke objective declares no lanes, so
        # the gate stays off there and is not misreported as malformed.
        enforce_graph_shape=bool(os.environ.get("UMH_WORKSPACE_LANES", "").strip()),
    )


def run_loop(
    *,
    spool_root: str,
    secret: str,
    max_iterations: int = 0,
    poll_seconds: float = 2.0,
    oauth_token: str | None = None,
    fixture_repo: str = "",
    targets_dir: str = "",
    leases_dir: str = "",
    max_workers: int = 2,
) -> int:
    from substrate.execution.attempts.host_isolation import (
        isolation_primitive,
        preflight_isolation,
    )
    from substrate.execution.attempts.run_teardown import (
        recover_stale_runs,
        register_resource,
        sweep_run,
    )
    from substrate.execution.attempts.spool import DispatchSpool

    # (1) enforced host isolation preflight — fail closed.
    prim = isolation_primitive()
    if prim is None:
        _log("FATAL: no host-isolation primitive (bwrap/nsjail/systemd-run) — refusing to run")
        return 2
    ok, detail = preflight_isolation("/opt/OS")
    _log(f"isolation preflight: {ok} ({detail})")
    if not ok:
        # FAIL CLOSED for EVERY primitive (SEC-C4). The `and prim == "bwrap"`
        # exemption meant a non-bwrap primitive could never fail this gate, while
        # providing no isolation whatsoever.
        _log(f"FATAL: isolation preflight failed ({detail}) — refusing to run workers unconfined")
        return 2

    # (1a) SEC-C1: convert SIGTERM/SIGINT into controlled unwinding so the run
    # teardown below ALWAYS runs. Without this the default disposition killed the
    # process mid-work and every credential home under run_root survived.
    _install_signal_handlers()

    run_root = targets_dir or os.path.dirname(spool_root.rstrip("/"))

    # (1a-i) Crash recovery: before starting, sweep any PRIOR dead run's residue
    # under this run's sibling set (closure bar §8). A run whose owner process is
    # still alive is refused — this destroys only abandoned runs, never a live one.
    try:
        runs_root = os.path.dirname(run_root.rstrip("/"))
        for res in recover_stale_runs(runs_root, live_pids={os.getpid()}):
            _log(f"crash-recovery swept stale run {res.run_root}: ok={res.ok} {res.steps}")
    except Exception as exc:  # never let recovery block startup
        _log(f"crash-recovery sweep error (continuing): {exc}")

    # Record THIS run's owner pid so a future startup can recognise it as ours and
    # (if we die) sweep our residue. 'run_owner' is a liveness anchor, never a
    # swept resource. The homes themselves are registered as the worker opens each
    # one; this anchors the manifest to a live owner.
    register_resource(run_root, kind="run_owner", ident=str(os.getpid()), detail="runner_owner")

    spool = DispatchSpool(spool_root, secret)
    # PROCESS STARTUP, NOT OPERATIONAL READINESS. The launcher must NOT accept
    # this as "started" — the control-plane driver is built further below and
    # can still fail, and a runner without its driver produces no governed
    # progress. The authoritative readiness marker is "control-plane driver up"
    # (or the explicit worker-only declaration), emitted only after that
    # construction succeeds. Both markers carry the pid + run root so a stale
    # log from a previous launch cannot satisfy a new one.
    _log(
        f"runner starting: pid={os.getpid()} run_root={run_root} "
        f"spool={spool_root} primitive={prim} max_workers={max_workers}"
    )

    # In-flight attempt ids, so the run-teardown finally can terminalize workers
    # that a signal interrupted mid-execution before sweeping their homes.
    inflight_attempts: set[str] = set()

    # Bounded control-plane failure accounting (see _CP_MAX_* above).
    cp_budget = ControlPlaneFailureBudget(_CP_MAX_CONSECUTIVE_ERRORS, _CP_MAX_TOTAL_ERRORS)

    # (1b) build the control-plane driver if the fixture + targets are wired.
    # This is the HOST half that turns an ACTIVE grant in the shared candidate
    # ledger into signed dispatch envelopes on this spool (the seam the candidate
    # container cannot drive itself). Worker-only mode (no fixture) keeps the
    # legacy behavior for tests/rehearsal that pre-fill the inbox.
    driver = None
    if fixture_repo and targets_dir:
        try:
            driver = _build_control_plane_driver(
                spool=spool,
                fixture_repo=fixture_repo,
                targets_dir=targets_dir,
                leases_dir=leases_dir or os.path.join(targets_dir, "leases"),
            )
            _log(
                f"control-plane driver up: pid={os.getpid()} run_root={run_root} "
                f"fixture={fixture_repo} targets={targets_dir}"
            )
        except Exception as exc:
            # FAIL CLOSED when this run DECLARED a lane decomposition. The
            # pre-quota graph-shape gate is armed inside the driver
            # (enforce_graph_shape above), so demoting to worker-only here does
            # not merely lose the control plane — it silently deletes the gate
            # while the loop keeps claiming and executing spool envelopes. That
            # is the "gate goes dark unnoticed" shape (adversarial-review
            # MEDIUM), and it matches the isolation preflight's precedent above:
            # a missing enforcement mechanism refuses to run, it does not warn.
            if os.environ.get("UMH_WORKSPACE_LANES", "").strip():
                _log(
                    f"FATAL: control-plane driver unavailable ({exc}) but this run "
                    "declares UMH_WORKSPACE_LANES — refusing to run with the "
                    "pre-quota graph-shape gate disarmed"
                )
                return 2
            _log(f"control-plane driver unavailable ({exc}) — worker-only mode")
            _log(
                f"runner ready worker-only: pid={os.getpid()} run_root={run_root} "
                f"reason={type(exc).__name__}"
            )
            driver = None

    def _run_teardown(reason: str) -> None:
        """The ONE run-teardown, invoked on EVERY exit path via the finally below.

        Sweeps the whole run root through the single run-teardown authority —
        worker/verifier homes (by directory), manifest-recorded leases and
        worktrees, and the spool — proving zero residue. It is idempotent, so the
        normal-exit call and a signal-driven call converge on the same authority
        (no second cleanup implementation). Homes are destroyed by directory here,
        which covers exactly the attempts a signal interrupted mid-run (whose
        per-attempt terminalize never ran).
        """
        if inflight_attempts:
            _log(
                f"run teardown ({reason}): {len(inflight_attempts)} attempt(s) interrupted mid-run"
            )
        res = sweep_run(run_root, spool=spool)
        _log(
            f"run teardown ({reason}): ok={res.ok} homes={res.homes_destroyed} "
            f"verifier_homes={res.verifier_homes_destroyed} "
            f"residue_cred={len(res.credential_residue)} "
            f"residue_worker={len(res.worker_home_residue)} "
            f"residue_verifier={len(res.verifier_home_residue)} errors={res.errors}"
        )

    iterations = 0
    try:
        while True:
            iterations += 1

            # (2) control-plane pass FIRST: turn ACTIVE grants in the shared ledger
            # into signed inbox dispatches, and advance any completed attempts from
            # the outbox (drain → verify → re-schedule). This is what puts work in
            # the inbox for the worker half below to claim.
            if driver is not None:
                try:
                    cycles = driver.run_cycle()
                    for c in cycles:
                        if c.admitted or c.succeeded or c.failed or c.errors:
                            _log(
                                f"control-plane: grant={c.grant_ref[:32]} "
                                f"admitted={len(c.admitted)} succeeded={len(c.succeeded)} "
                                f"failed={len(c.failed)} drained={c.results_drained} "
                                f"errors={len(c.errors)}"
                            )
                            # Surface the CAUSE, not just a count (review W8).
                            for err in c.errors:
                                _log(f"control-plane ERROR: {err}")
                        elif getattr(c, "authority_unresolved", None):
                            # A Task REFUSED because its composition authority
                            # could not be resolved must never read as "no
                            # eligible work". The refusal creates no attempt
                            # record, so without this branch the run's only
                            # human-facing signal was "control-plane idle" —
                            # the exact false-completion the field defect
                            # produced (run 20260807T005250Z-p1). The cycle
                            # already reports idle=False; this makes the
                            # operator log agree with it.
                            _log(
                                f"control-plane REFUSED: grant={c.grant_ref[:32]} could not "
                                f"resolve composition authority for: {c.authority_unresolved} "
                                f"— NOT idle; no worker was dispatched for these tasks"
                            )
                        elif getattr(c, "skipped_not_approved", None):
                            # A stall with a known cause must never look like
                            # "waiting for work" (review W5).
                            if iterations % _IDLE_LOG_EVERY == 1:
                                _log(
                                    f"control-plane IDLE: grant={c.grant_ref[:32]} is waiting on "
                                    f"tasks that are not APPROVED yet: {c.skipped_not_approved}"
                                )
                        elif iterations % _IDLE_LOG_EVERY == 1:
                            _log(f"control-plane idle: grant={c.grant_ref[:32]} no eligible work")
                    # A cycle that completed resets the consecutive-failure
                    # budget: transient faults are tolerated, a BROKEN driver is
                    # not.
                    cp_budget.record_success()
                except Exception as exc:  # a control-plane fault must be BOUNDED
                    cp_budget.record_failure(exc)
                    _log(
                        f"control-plane cycle error "
                        f"({cp_budget.consecutive}/{cp_budget.max_consecutive} consecutive, "
                        f"{cp_budget.total}/{cp_budget.max_total} total): {exc}"
                    )
                    # This used to log "(continuing)" forever with no bound, so a
                    # permanently broken driver consumed the entire run budget
                    # while the loop reported liveness and produced ZERO governed
                    # progress. Process liveness is not control-plane health.
                    if cp_budget.exhausted:
                        _log(
                            f"FATAL: control-plane driver failed "
                            f"{cp_budget.consecutive} consecutive / {cp_budget.total} total "
                            f"cycles — terminal bound reached, refusing to consume the run "
                            f"budget without governed progress. last_error={cp_budget.last_error}"
                        )
                        return 3

            # (3) reap stale UNCLAIMED envelopes and recover crashed inflight work.
            # Nothing previously did either: an expired envelope stranded its attempt
            # in DISPATCHED forever, permanently consuming a concurrency slot, and a
            # crashed worker's claim was never returned (finding C3).
            try:
                for name in spool.reap_stale_unclaimed():
                    _log(f"reaped stale unclaimed dispatch {name}")
                for name in spool.recover_stale_inflight(
                    older_than_seconds=_INFLIGHT_RECOVERY_SECONDS
                ):
                    _log(f"recovered abandoned inflight dispatch {name}")
            except Exception as exc:  # never let reaping kill the loop
                _log(f"spool reap/recovery error (continuing): {exc}")

            # Leases need the same crash recovery the spool has. A process
            # death between acquire() and terminalization leaves the lease
            # ACTIVE forever, and LeaseManager.acquire then refuses that task
            # permanently ("task already has an active lease") while its
            # worktree keeps consuming a max_parallel slot. expires_at was set
            # (ttl 3600s) but never enforced — expire_stale had no caller.
            try:
                # Use the ACCESSOR, not the raw attribute: `_lease_mgr` is lazily
                # built and stays None until a scheduler pass constructs it, so a
                # cycle that returns early (no active grant, or the graph-shape
                # gate refusing) would leave the reap a silent no-op — the exact
                # defect class that has recurred through this review series.
                accessor = getattr(driver, "_lease_manager", None) if driver is not None else None
                if callable(accessor):
                    expired = accessor().expire_stale()
                    if expired:
                        _log(f"expired {expired} stale lease(s)")
            except Exception as exc:  # never let lease expiry kill the loop
                _log(f"lease expiry error (continuing): {exc}")

            # (4) claim up to max_workers envelopes and run them CONCURRENTLY.
            # The previous loop claimed ONE per iteration and ran the worker
            # synchronously, so A and B never overlapped: the exactly-2 concurrency
            # criterion was unobtainable, and B's envelope expired while A held the
            # whole timeout. Claims are atomic (os.replace), so each worker owns a
            # distinct envelope — with its own worktree, lease, package, credential
            # home and process.
            claims: list[tuple[str, Any]] = []
            while len(claims) < max_workers:
                claimed = spool.claim_next()
                if claimed is None:
                    break
                claims.append(claimed)

            if not claims:
                if max_iterations and iterations >= max_iterations:
                    _log("max iterations reached — exiting")
                    return 0
                time.sleep(poll_seconds)
                if max_iterations and iterations >= max_iterations:
                    return 0
                continue

            for _token, env in claims:
                _log(f"claimed dispatch {env.dispatch_id} attempt={env.attempt_id}")
                inflight_attempts.add(str(env.attempt_id))

            with ThreadPoolExecutor(max_workers=max_workers) as pool:
                futures = {
                    pool.submit(
                        _run_one_claim,
                        spool=spool,
                        token=token,
                        envelope=env,
                        oauth_token=oauth_token,
                        run_root=run_root,
                        run_worker=run_worker_in_lease,
                    ): env
                    for token, env in claims
                }
                # HEARTBEAT EVERY LIVE CLAIM WHILE WE WAIT (finding NEW-2).
                # `spool.heartbeat_claim()` existed but had ZERO production
                # callers, so it protected nothing: a worker legitimately running
                # longer than _INFLIGHT_RECOVERY_SECONDS still had its claim
                # declared abandoned and re-queued underneath it — the same
                # duplicate-dispatch outcome the B4 claim-stamp fix was meant to
                # close, just on a longer fuse. Staleness must measure how long a
                # claim has gone UNTENDED, so the claimant has to tend it.
                pending = set(futures)
                while pending:
                    done, pending = wait(
                        pending, timeout=_HEARTBEAT_SECONDS, return_when=FIRST_COMPLETED
                    )
                    for tok, _e in claims:
                        if not spool.heartbeat_claim(tok):
                            # the claim is gone (completed/recovered) — nothing to tend
                            continue
                    for fut in done:
                        env = futures[fut]
                        try:
                            fut.result()
                        except Exception as exc:  # a worker fault must not kill the pool
                            _log(f"worker for {env.attempt_id} raised: {exc}")
                        finally:
                            inflight_attempts.discard(str(env.attempt_id))

            if max_iterations and iterations >= max_iterations:
                return 0
    except _Shutdown:
        # A SIGTERM/SIGINT arrived. The finally below has ALREADY run the run
        # teardown by the time we get here; convert the signal into a clean exit
        # code (143 = 128 + SIGTERM) instead of an uncaught-BaseException stack.
        _log("shutdown complete — exiting after run teardown")
        return 143
    finally:
        # SEC-C1: EVERY exit — normal max-iterations return, a worker-loop
        # exception, or the _Shutdown raised from the SIGTERM/SIGINT handler —
        # unwinds through here. The run-teardown authority destroys every
        # credential home under the run root and proves zero residue. A Shutdown
        # interrupted mid-worker leaves the home on disk; this is what removes it.
        _run_teardown("signal/normal-exit")


def _run_one_claim(
    *,
    spool: Any,
    token: str,
    envelope: Any,
    oauth_token: str | None,
    run_root: str,
    run_worker: Any,
) -> None:
    """Execute ONE claimed dispatch and write its signed result to the outbox.

    Runs on a pool thread so sibling attempts execute concurrently. Everything
    that distinguishes one attempt from another — worktree, lease, package,
    credential home, tool policy — comes from its own envelope, so two workers
    share no mutable state.
    """

    class _Lease:
        worktree_path = envelope.worktree_path
        # The AUTHORIZED base commit, carried on the signed envelope. It was
        # previously "" and the worker fell back to "HEAD", making the artifact
        # range `HEAD..HEAD` — empty by definition, so every attempt reported no
        # files and no commits. The worker now refuses an unanchored lease.
        snapshot_ref = envelope.base_commit

    # THE CANONICAL PACKAGE, RECONSTRUCTED FROM THE SIGNED ENVELOPE (finding F-2).
    # Built by the module-level `package_from_envelope` so the regression tests
    # drive THIS construction rather than a copy of it — a test that rebuilds the
    # package inline cannot see a mutation here, which is exactly how the
    # original defect survived a passing suite.
    package = package_from_envelope(envelope)

    # SEC-C1: durably register the worktree AND the worker home the instant before
    # the worker populates them, so a signal/crash mid-run leaves enough manifest
    # state for the run-teardown sweep (and next-start crash recovery) to find and
    # destroy them. Registration is append-only and never raises into this path.
    from substrate.execution.attempts.run_teardown import register_resource
    from substrate.execution.attempts.worker_credential_boundary import attempt_home_path

    register_resource(
        run_root, kind="worker_home", ident=attempt_home_path(run_root, str(envelope.attempt_id))
    )
    if envelope.worktree_path:
        register_resource(run_root, kind="worktree", ident=str(envelope.worktree_path))

    started_at = time.time()
    result = run_worker(
        package=package,
        lease=_Lease(),
        timeout=float(envelope.timeout_seconds or 600),
        max_turns=int(envelope.max_turns or 30),
        disallowed_tools=list(envelope.disallowed_tools or []),
        oauth_token=oauth_token,
        # Binds this attempt's PRIVATE credential home under the run target
        # dir. A retry is a new attempt_id -> a new home (R1 / SEC-C2).
        attempt_id=envelope.attempt_id,
        run_root=run_root,
    )

    # Write a SIGNED result to the outbox — the control-plane poller applies the
    # canonical attempt transition; the runner never mutates the ledger.
    spool.complete(
        token,
        {
            "dispatch_id": envelope.dispatch_id,
            "attempt_id": envelope.attempt_id,
            "task_id": envelope.task_id,
            "package_hash": envelope.package_hash,
            "worker_result": result.to_dict(),
            "required_model_attestation": {
                "provider": "codex",
                "model": "gpt-5.6-sol",
            },
            # The worker reports its authorized diff base (finding F-3, corrected
            # by invocation 41: the projection is execution context, never a
            # commit, so this is the CANONICAL un-moved base). The poller
            # validates it through the forward-only re-anchor guard; on the
            # shipped path it equals the lease's snapshot_ref.
            #
            # getattr, not attribute access: a worker result that predates this
            # field must degrade to "no re-anchor" (the poller then leaves the
            # lease base untouched), never crash the runner mid-dispatch and
            # strand the attempt in the spool.
            "trusted_base": str(getattr(result, "trusted_base", "") or ""),
            # Real wall-clock bounds, so reconciliation can PROVE overlap:
            # max(started) < min(completed) across A and B.
            "started_at": started_at,
            "completed_at": time.time(),
            "reported_at": time.time(),
        },
    )
    _log(
        f"completed {envelope.attempt_id}: ok={result.ok} status={result.status} "
        f"files={len(result.files_changed)} isolated={result.isolated}"
    )


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--spool-root", required=True, help="run's dispatch spool root")
    ap.add_argument(
        "--secret-env",
        default="UMH_W2_DISPATCH_SECRET",
        help="env var holding the per-run HMAC secret",
    )
    ap.add_argument("--max-iterations", type=int, default=0, help="0 = run until stopped")
    ap.add_argument("--poll-seconds", type=float, default=2.0)
    ap.add_argument(
        "--max-workers",
        type=int,
        default=2,
        help="concurrent implementation workers (qualification bar: 2)",
    )
    ap.add_argument(
        "--preflight-only", action="store_true", help="verify isolation + exit (no worker loop)"
    )
    ap.add_argument(
        "--fixture-repo",
        default="",
        help="fixture repo root the control-plane driver leases worktrees from "
        "(enables the host control-plane loop; omit for worker-only mode)",
    )
    ap.add_argument(
        "--targets-dir",
        default="",
        help="run's targets dir (holds .inject_failure marker, sandboxes, leases)",
    )
    ap.add_argument(
        "--leases-dir", default="", help="worktree base for leases (default: <targets>/leases)"
    )
    args = ap.parse_args()

    if args.preflight_only:
        from substrate.execution.attempts.host_isolation import (
            isolation_primitive,
            preflight_isolation,
        )

        prim = isolation_primitive()
        ok, detail = preflight_isolation("/opt/OS")
        print(json.dumps({"primitive": prim, "isolation_ok": ok, "detail": detail}))
        # FAIL CLOSED: `ok or prim != "bwrap"` let any non-bwrap primitive pass
        # the preflight that start_runner parses to decide whether to launch.
        return 0 if (prim and ok) else 2

    secret = os.environ.get(args.secret_env, "")
    if not secret:
        _log(f"FATAL: {args.secret_env} not set — the runner needs the per-run dispatch secret")
        return 2
    oauth = os.environ.get("MODEL_EXECUTOR_TOKEN") or os.environ.get("CODEX_ACCESS_TOKEN") or None
    # Wave 2's active production policy is Codex/Sol. The provider-neutral
    # executor contract still owns invocation and proof binding; this only pins
    # runtime selection before any worker subprocess is admitted.
    os.environ["UMH_MODEL_EXECUTOR_PROVIDER"] = "codex"
    os.environ["UMH_CODEX_MODEL"] = "gpt-5.6-sol"
    return run_loop(
        spool_root=args.spool_root,
        secret=secret,
        max_iterations=args.max_iterations,
        poll_seconds=args.poll_seconds,
        oauth_token=oauth,
        fixture_repo=args.fixture_repo,
        targets_dir=args.targets_dir,
        leases_dir=args.leases_dir,
        max_workers=args.max_workers,
    )


if __name__ == "__main__":
    raise SystemExit(main())
