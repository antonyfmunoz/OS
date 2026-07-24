#!/usr/bin/env python3
"""Wave 2 host-side attempt runner (run-scoped — NOT a persistent supervisor).

Ties the governed control plane to real, isolated workers. Started/stopped by the
field dispatcher for the duration of one qualification run. It:

1. verifies enforced host isolation is available (bwrap) — refuses to run
   otherwise (Amendment v1 clause 4);
2. claims signed dispatch envelopes from the spool (bad/expired → quarantined);
3. verifies each envelope's authorization is an ACTIVE grant and its scope hash
   matches (defense in depth over the spine's own check);
4. runs the real Claude-CLI worker in the lease worktree under bwrap isolation;
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
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any

# An INFLIGHT claim older than this with no result is treated as abandoned by a
# crashed worker and returned to the inbox. Generously above the 600s execution
# budget so a slow-but-live worker is never stolen from.
_INFLIGHT_RECOVERY_SECONDS = 1200.0

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if REPO not in sys.path:
    sys.path.insert(0, REPO)


def _log(msg: str) -> None:
    print(f"[wave2-runner] {msg}", flush=True)


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

    store = ExecutionAttemptStore()  # honors UMH_STATE_DIR (shared candidate state)
    queue = UniversalWorkQueue()  # honors UMH_STATE_DIR
    sandbox = SandboxManager(
        repo_root=fixture_repo,
        worktree_base=leases_dir,
        store_dir=os.path.join(targets_dir, "sandboxes"),
        max_parallel=2,
    )
    return FieldControlPlaneDriver(
        store=store,
        work_queue=queue,
        spool=spool,
        sandbox_manager=sandbox,
        targets_dir=targets_dir,
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
    from substrate.execution.attempts.spool import DispatchSpool
    from substrate.execution.attempts.worker_claude_cli import run_worker_in_lease

    # (1) enforced host isolation preflight — fail closed.
    prim = isolation_primitive()
    if prim is None:
        _log("FATAL: no host-isolation primitive (bwrap/nsjail/systemd-run) — refusing to run")
        return 2
    ok, detail = preflight_isolation("/opt/OS")
    _log(f"isolation preflight: {ok} ({detail})")
    if not ok and prim == "bwrap":
        _log("FATAL: isolation preflight failed — refusing to run workers unconfined")
        return 2

    spool = DispatchSpool(spool_root, secret)
    _log(f"runner up: spool={spool_root} primitive={prim} max_workers={max_workers}")

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
            _log(f"control-plane driver up: fixture={fixture_repo} targets={targets_dir}")
        except Exception as exc:  # worker-only fallback, loudly logged
            _log(f"control-plane driver unavailable ({exc}) — worker-only mode")
            driver = None

    iterations = 0
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
            except Exception as exc:  # never let a control-plane fault kill the worker
                _log(f"control-plane cycle error (continuing): {exc}")

        # (3) reap stale UNCLAIMED envelopes and recover crashed inflight work.
        # Nothing previously did either: an expired envelope stranded its attempt
        # in DISPATCHED forever, permanently consuming a concurrency slot, and a
        # crashed worker's claim was never returned (finding C3).
        try:
            for name in spool.reap_stale_unclaimed():
                _log(f"reaped stale unclaimed dispatch {name}")
            for name in spool.recover_stale_inflight(older_than_seconds=_INFLIGHT_RECOVERY_SECONDS):
                _log(f"recovered abandoned inflight dispatch {name}")
        except Exception as exc:  # never let reaping kill the loop
            _log(f"spool reap/recovery error (continuing): {exc}")

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

        run_root = targets_dir or os.path.dirname(spool_root.rstrip("/"))
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
            for fut in as_completed(futures):
                env = futures[fut]
                try:
                    fut.result()
                except Exception as exc:  # a worker fault must not kill the pool
                    _log(f"worker for {env.attempt_id} raised: {exc}")

        if max_iterations and iterations >= max_iterations:
            return 0


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
        snapshot_ref = ""  # base commit resolved from the worktree HEAD if absent

    class _Package:
        role_instructions = ""
        operation_instructions = f"Execute task {envelope.task_id} per the objective contract."
        ordered_context: list = []
        operation_identity = {"task_id": envelope.task_id}

    started_at = time.time()
    result = run_worker(
        package=_Package(),
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
        return 0 if (prim and (ok or prim != "bwrap")) else 2

    secret = os.environ.get(args.secret_env, "")
    if not secret:
        _log(f"FATAL: {args.secret_env} not set — the runner needs the per-run dispatch secret")
        return 2
    oauth = os.environ.get("CLAUDE_CODE_OAUTH_TOKEN") or None
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
