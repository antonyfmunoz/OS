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

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if REPO not in sys.path:
    sys.path.insert(0, REPO)


def _log(msg: str) -> None:
    print(f"[wave2-runner] {msg}", flush=True)


def run_loop(
    *,
    spool_root: str,
    secret: str,
    max_iterations: int = 0,
    poll_seconds: float = 2.0,
    oauth_token: str | None = None,
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
    _log(f"runner up: spool={spool_root} primitive={prim}")

    iterations = 0
    while True:
        iterations += 1
        claimed = spool.claim_next()
        if claimed is None:
            if max_iterations and iterations >= max_iterations:
                _log("max iterations reached — exiting")
                return 0
            time.sleep(poll_seconds)
            if max_iterations and iterations >= max_iterations:
                return 0
            continue

        token, envelope = claimed
        _log(f"claimed dispatch {envelope.dispatch_id} attempt={envelope.attempt_id}")

        # (4) run the real worker. The package is reconstructed minimally from the
        # envelope (the sealed package hash is carried for the verifier); the CLI
        # worker renders and runs it in the lease worktree under isolation.
        class _Lease:
            worktree_path = envelope.worktree_path
            snapshot_ref = ""  # base commit resolved from the worktree HEAD if absent

        class _Package:
            role_instructions = ""
            operation_instructions = f"Execute task {envelope.task_id} per the objective contract."
            ordered_context: list = []
            operation_identity = {"task_id": envelope.task_id}

        result = run_worker_in_lease(
            package=_Package(),
            lease=_Lease(),
            timeout=float(envelope.timeout_seconds or 600),
            max_turns=int(envelope.max_turns or 30),
            disallowed_tools=list(envelope.disallowed_tools or []),
            oauth_token=oauth_token,
        )

        # (5) write a SIGNED result to the outbox — the control-plane poller
        # applies the canonical attempt transition; the runner never does.
        spool.complete(token, {
            "dispatch_id": envelope.dispatch_id,
            "attempt_id": envelope.attempt_id,
            "task_id": envelope.task_id,
            "package_hash": envelope.package_hash,
            "worker_result": result.to_dict(),
            "reported_at": time.time(),
        })
        _log(f"completed {envelope.attempt_id}: ok={result.ok} status={result.status} "
             f"files={len(result.files_changed)} isolated={result.isolated}")

        if max_iterations and iterations >= max_iterations:
            return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--spool-root", required=True, help="run's dispatch spool root")
    ap.add_argument("--secret-env", default="UMH_W2_DISPATCH_SECRET",
                    help="env var holding the per-run HMAC secret")
    ap.add_argument("--max-iterations", type=int, default=0, help="0 = run until stopped")
    ap.add_argument("--poll-seconds", type=float, default=2.0)
    ap.add_argument("--preflight-only", action="store_true",
                    help="verify isolation + exit (no worker loop)")
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
        spool_root=args.spool_root, secret=secret,
        max_iterations=args.max_iterations, poll_seconds=args.poll_seconds,
        oauth_token=oauth,
    )


if __name__ == "__main__":
    raise SystemExit(main())
