#!/usr/bin/env python3
"""Production reproduction: two withheld retentions at max_parallel=2.

Runs the REAL SandboxManager / LeaseManager / ControlPlanePoller._terminalize at
the PRODUCTION concurrency limit (scripts/wave2_attempt_runner.py:256).

BEFORE the slot-preserving cleanup, this printed:
    THIRD TASK BLOCKED: Max parallel sandboxes (2) reached. Active: 2
    expire_stale cleared: 2 leases -> active_sandboxes STILL 2 -> still blocked

AFTER, it prints ADMITTED and both preserved commits survive `git gc`.
"""
from __future__ import annotations

import os
import subprocess
import sys
import tempfile
import time
from types import SimpleNamespace

# Anchor on THIS checkout (data/audits/proof/<dir>/ → 4 levels up), so the proof
# always exercises the tree it ships in, not whatever UMH_ROOT happens to be.
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", "..")))

from substrate.execution.attempts.leases import LeaseManager  # noqa: E402
from substrate.execution.attempts.poller import (  # noqa: E402
    ControlPlanePoller,
    PollerPassReport,
)
from substrate.execution.attempts.records import (  # noqa: E402
    ExecutionAttempt,
    ExecutionAttemptStatus,
)
from substrate.execution.attempts.store import ExecutionAttemptStore  # noqa: E402
from substrate.organism.worktree_sandbox import SandboxManager  # noqa: E402

CAND = "9a8c4a30620cfde5cec7b05e7a54d625ee6cd450"
RUN = "20260805T182714Z-p1"
_S = ExecutionAttemptStatus
ASSIGNMENT = SimpleNamespace(worker_identity="cc-cli@vps-host", compute_node_id="n", tool_profile=[])
GRANT = SimpleNamespace(tenant_id="t1", credential_scope_refs=[])


def git(args, cwd):
    return subprocess.run(["git", *args], cwd=cwd, capture_output=True, text=True)


def direct_runner(**kw):
    fn = kw.get("execute_fn")
    out, ok = fn() if fn else ("", True)
    return SimpleNamespace(success=ok, output=out)


def main() -> int:
    tmp = tempfile.mkdtemp(prefix="starve-")
    repo = os.path.join(tmp, "candidates", "wave2", CAND, "targets", RUN, "fixture")
    os.makedirs(os.path.join(repo, "app"))
    for a in (["init", "-q", "-b", "master"], ["config", "user.email", "t@t"], ["config", "user.name", "t"]):
        git(a, repo)
    open(f"{repo}/app/main.py", "w").write("base\n")
    git(["add", "-A"], repo)
    git(["commit", "-qm", "base"], repo)

    mgr = SandboxManager(
        repo_root=repo,
        worktree_base=os.path.join(tmp, "wt"),
        store_dir=os.path.join(tmp, "sb"),
        max_parallel=2,  # PRODUCTION VALUE
    )
    store = ExecutionAttemptStore(
        attempts_path=f"{tmp}/a.jsonl", grants_path=f"{tmp}/g.jsonl",
        readiness_path=f"{tmp}/r.jsonl", leases_path=f"{tmp}/l.jsonl",
        assignments_path=f"{tmp}/asn.jsonl",
    )
    lm = LeaseManager(store, mgr, mutation_runner=direct_runner)
    poller = ControlPlanePoller(
        store=store, spool=None, scheduler=None, verify_fn=lambda **kw: None,
        lease_manager=lm, run_root=os.path.join(tmp, "run"),
    )

    import substrate.execution.attempts.verified_commit_retention as m

    real_gate = m.gated_subprocess_run
    commits = []
    for tag in ("w1", "w2"):
        att = ExecutionAttempt(
            attempt_id=f"ea-{tag}", task_id=f"wp-{tag}", status=_S.LEASED.value,
            worker_identity="cc-cli@vps-host", correlation_id=f"w2-{RUN}",
        )
        lease = lm.acquire(attempt=att, assignment=ASSIGNMENT, grant=GRANT)
        with open(os.path.join(lease.worktree_path, "app/main.py"), "a") as fh:
            fh.write(f"VERIFIED {tag}\n")
        git(["add", "-A"], lease.worktree_path)
        git(["commit", "-qm", f"verified {tag}"], lease.worktree_path)
        commits.append(git(["rev-parse", "HEAD"], lease.worktree_path).stdout.strip())

        att.status = _S.SUCCEEDED.value
        att.lease_id = lease.lease_id
        m.gated_subprocess_run = lambda *a, **k: None  # CPU gate refuses
        rep = PollerPassReport()
        poller._terminalize(att, "succeeded", rep)  # noqa: SLF001
        m.gated_subprocess_run = real_gate
        withheld = any("WITHHELD" in e for e in rep.errors)
        print(f"withhold {tag}: withheld={withheld} active_sandboxes={len(mgr.active_sandboxes)}")

    third = ExecutionAttempt(
        attempt_id="ea-w3", task_id="wp-w3", status=_S.LEASED.value,
        worker_identity="cc-cli@vps-host", correlation_id=f"w2-{RUN}",
    )
    try:
        l3 = lm.acquire(attempt=third, assignment=ASSIGNMENT, grant=GRANT)
        print(f"THIRD TASK ADMITTED: {l3.worktree_path}")
        admitted = True
    except Exception as exc:
        print(f"THIRD TASK BLOCKED: {exc}")
        admitted = False

    print(f"expire_stale cleared: {lm.expire_stale(now=time.time() + 10_000)}")
    print(f"active_sandboxes after expire: {len(mgr.active_sandboxes)}")

    git(["reflog", "expire", "--expire=now", "--all"], repo)
    git(["gc", "--prune=now", "-q"], repo)
    survived = all(git(["cat-file", "-e", f"{c}^{{commit}}"], repo).returncode == 0 for c in commits)
    print(f"BOTH PRESERVED COMMITS SURVIVE GC: {survived}")
    print(f"VERDICT: {'PASS' if admitted and survived else 'FAIL'}")
    return 0 if (admitted and survived) else 1


if __name__ == "__main__":
    sys.exit(main())
