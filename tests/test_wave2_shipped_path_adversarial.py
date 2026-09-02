"""Wave 2 — adversarial proofs for the shipped package/spool/git/phase boundaries.

The authorization names a specific adversarial set. The vectors that live at the
BARRIER (forbidden edits, hooks, config, refs, renames) are proven in
``test_wave2_shipped_path_integration.py`` against real bwrap; the vectors here
are the TRANSPORT and PHASE ones: replay against the wrong Attempt or SHA, scope
widening by worker-reachable data, and the ordering guarantee that separates
trusted writes from worker capability.

Each asserts a DENIAL plus the state that must remain untouched — a fix that
reverts after the fact is explicitly not acceptable.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from substrate.execution.attempts import worker_claude_cli as W
from substrate.execution.attempts.field_control_plane import governance_envelope_fields
from substrate.execution.attempts.spool import DispatchEnvelope, DispatchSpool

SECRET = "adversarial-secret"
SCOPE = ["app/main.py"]


def _package(scope=None, *, task_id="wp-backend"):
    class _P:
        role_instructions = "implementer"
        operation_instructions = "implement"
        ordered_context = [{"section": "contract", "payload": "c"}]
        operation_identity = {"task_id": task_id}
        governance_constraints = [f"writable_path_scope={sorted(scope or SCOPE)}"]
        verification_requirements = []

    return _P()


def _envelope(**over):
    fields = dict(
        dispatch_id="d-1",
        attempt_id="ea-1",
        task_id="wp-backend",
        authorization_ref="grant-1",
        package_hash="ph-1",
        lease_id="lease-1",
        worktree_path="/tmp/lease",
        base_commit="aaaa1111",
        nonce=os.urandom(8).hex(),
        sequence=1,
        **governance_envelope_fields(_package()),
    )
    fields.update(over)
    return DispatchEnvelope(**fields)


def _tamper(spool_root: str, mutate) -> None:
    """Rewrite the queued envelope WITHOUT re-signing (an attacker's edit)."""
    inbox = os.path.join(spool_root, "inbox")
    name = sorted(os.listdir(inbox))[0]
    path = os.path.join(inbox, name)
    with open(path, encoding="utf-8") as fh:
        record = json.load(fh)
    mutate(record["envelope"])
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(record, fh)


# ── replay / rebinding ───────────────────────────────────────────────────────


def test_package_replayed_against_the_wrong_attempt_is_rejected(tmp_path):
    """Re-pointing a signed dispatch at a DIFFERENT attempt must fail closed.

    The envelope's authority is bound to one Attempt. Rebinding it would let a
    completed (or cheaper) attempt's authorization drive work for another.
    """
    root = str(tmp_path)
    spool = DispatchSpool(root, SECRET)
    spool.enqueue(_envelope())
    _tamper(root, lambda env: env.update(attempt_id="ea-SOMEONE-ELSE"))
    assert spool.claim_next() is None, "a replay against another Attempt must be refused"


def test_package_replayed_against_the_wrong_sha_is_rejected(tmp_path):
    """Re-pointing the authorized base commit must fail closed.

    base_commit is the anchor the worker's artifacts are attributed against;
    moving it silently re-scopes what counts as this attempt's output.
    """
    root = str(tmp_path)
    spool = DispatchSpool(root, SECRET)
    spool.enqueue(_envelope())
    _tamper(root, lambda env: env.update(base_commit="deadbeefdeadbeef"))
    assert spool.claim_next() is None, "a replay against another SHA must be refused"


def test_a_duplicate_dispatch_cannot_be_executed_twice(tmp_path):
    """The same signed envelope must not be consumable a second time.

    Signature proves authenticity, never freshness — a byte-perfect copy
    verifies cleanly, so replay protection has to be separate.
    """
    root = str(tmp_path)
    spool = DispatchSpool(root, SECRET)
    envelope = _envelope()
    spool.enqueue(envelope)
    assert spool.claim_next() is not None, "the first claim must succeed"
    spool.enqueue(envelope)  # byte-identical replay
    assert spool.claim_next() is None, "a replayed dispatch must be quarantined"


def test_worker_reachable_data_cannot_widen_the_scope(tmp_path):
    """Scope widening is refused even when every other field is untouched."""
    root = str(tmp_path)
    spool = DispatchSpool(root, SECRET)
    spool.enqueue(_envelope())
    _tamper(
        root,
        lambda env: env.update(
            governance_constraints=["writable_path_scope=['app', 'tests', '.git']"]
        ),
    )
    assert spool.claim_next() is None, "a widened scope must be refused"


def test_removing_the_scope_entirely_is_refused(tmp_path):
    """Stripping the constraint must not degrade to an unconstrained run."""
    root = str(tmp_path)
    spool = DispatchSpool(root, SECRET)
    spool.enqueue(_envelope())
    _tamper(root, lambda env: env.update(governance_constraints=[]))
    assert spool.claim_next() is None, "a stripped scope must be refused"


def test_an_envelope_that_never_carried_a_scope_is_refused(tmp_path):
    """Not a tamper — a correctly-signed envelope with no authority at all.

    This is the shape the runner used to build for EVERY dispatch (F-2). It is
    refused at the transport, before any launch decision.
    """
    root = str(tmp_path)
    spool = DispatchSpool(root, SECRET)
    spool.enqueue(
        DispatchEnvelope(
            dispatch_id="d-noscope",
            attempt_id="ea-1",
            task_id="wp-backend",
            nonce=os.urandom(8).hex(),
            sequence=1,
        )
    )
    assert spool.claim_next() is None, "an envelope with no scope must be refused"
    quarantine = os.listdir(os.path.join(root, "quarantine"))
    assert any("governance" in q for q in quarantine), (
        f"it must be quarantined for the governance defect, got {quarantine}"
    )


# ── phase separation ─────────────────────────────────────────────────────────


def _real_lease(root: str) -> tuple[str, str]:
    repo = os.path.join(root, "fixture")
    os.makedirs(os.path.join(repo, "app"))

    def g(*a):
        return subprocess.run(["git", *a], cwd=repo, capture_output=True, text=True, timeout=60)

    with open(os.path.join(repo, "app", "main.py"), "w", encoding="utf-8") as fh:
        fh.write("# base\n")
    with open(os.path.join(repo, "OBJECTIVE.md"), "w", encoding="utf-8") as fh:
        fh.write("# ALL TASKS\n")
    g("init", "-q", "-b", "main")
    g("config", "user.email", "t@t.t")
    g("config", "user.name", "t")
    g("add", "-A")
    g("commit", "-qm", "base")
    base = g("rev-parse", "HEAD").stdout.strip()
    lease = os.path.join(root, "lease")
    g("worktree", "add", "-q", "-b", "b", lease, "HEAD")
    W.make_lease_selfcontained(lease)
    return lease, base


def test_trusted_writes_precede_the_worker_and_are_git_invisible():
    """Proof: the trusted phase completes BEFORE worker confinement begins.

    Ordering is the whole of F-3. If the projection were written after the
    worker's base was anchored, its two files would be attributed to the worker;
    if it were written INSIDE the sandbox, it would need worker write authority
    over paths the worker must never hold.

    Invocation-41 form: the projection is EXECUTION CONTEXT — on disk, git
    hidden, and the base UNMOVED, so the retained commit carries no per-Task
    system delta and fan-in composition cannot conflict on it.
    """
    root = tempfile.mkdtemp()
    lease, base = _real_lease(root)
    projection = W.project_task_local_objective(_package(), lease)
    assert projection.get("ok")
    W._mark_projection_execution_context(lease, projection)

    def g(*a):
        return subprocess.run(["git", *a], cwd=lease, capture_output=True, text=True, timeout=60)

    assert g("rev-parse", "HEAD").stdout.strip() == base, (
        "the trusted phase must NOT move the attempt base — a projection commit "
        "poisons every retained predecessor with a divergent OBJECTIVE.md"
    )
    assert g("status", "--porcelain").stdout.strip() == "", (
        "the trusted phase must leave a git-clean tree"
    )
    with open(os.path.join(lease, "OBJECTIVE.md"), encoding="utf-8") as fh:
        assert "# Your Task" in fh.read(), "the projected content must be in effect on disk"


def test_projection_paths_are_never_inside_a_workers_writable_scope():
    """The worker must not gain write authority over trusted artifacts.

    "The worker must never receive permission to write projection or evidence
    paths merely because the orchestrator needs them later."
    """
    from substrate.execution.attempts.field_task_scope import (
        FIXTURE_ALLOWED_PATHS,
        readonly_binds_for_scope,
    )

    root = tempfile.mkdtemp()
    for rel in ("OBJECTIVE.md", "SHARED_CONTEXT.md"):
        with open(os.path.join(root, rel), "w", encoding="utf-8") as fh:
            fh.write("x")
    os.makedirs(os.path.join(root, "app"))
    with open(os.path.join(root, "app", "main.py"), "w", encoding="utf-8") as fh:
        fh.write("x")

    for label, scope in FIXTURE_ALLOWED_PATHS.items():
        for trusted in W.TRUSTED_PROJECTION_PATHS:
            assert trusted not in scope, f"{label} must not hold write authority over {trusted}"
        rel = {os.path.relpath(b, root) for b in readonly_binds_for_scope(scope, lease_root=root)}
        for trusted in W.TRUSTED_PROJECTION_PATHS:
            assert trusted in rel, f"{label}: {trusted} must be read-only to the worker"


def test_git_objects_info_is_locked_against_alternates_planting():
    """A worker must not be able to plant `.git/objects/info/alternates`.

    Found by a SELF-DIRECTED probe of the surface the F-1 correction OPENED —
    `objects/` had to become writable so commits could work, and `objects/info/`
    came along with it. `alternates` names an EXTERNAL object store git resolves
    objects from. Measured impact before the fix: inside the sandbox git could
    not normalize the path (isolation held), but the FILE PERSISTED TO THE HOST
    and `git cat-file` on the host then read a blob out of an unrelated
    repository and printed its contents. A persistence primitive that outlives
    confinement, not a contained failure.

    `objects/info` is CREATED when absent so it can be locked: "the directory
    does not exist yet" must never degrade into "the worker may create it".
    """
    from substrate.execution.attempts.field_task_scope import git_readonly_subpaths

    root = tempfile.mkdtemp()
    os.makedirs(os.path.join(root, ".git", "objects"))
    subs = {os.path.relpath(p, root) for p in git_readonly_subpaths(root)}
    assert ".git/objects/info" in subs, (
        "objects/info holds `alternates` and must be read-only even though "
        "objects/ itself must stay writable for commits"
    )
    assert ".git/objects" not in subs, (
        "objects/ itself must stay WRITABLE — locking it would break every commit"
    )
    assert os.path.isdir(os.path.join(root, ".git", "objects", "info")), (
        "the directory must be created so there is something to bind read-only"
    )


def test_git_worktrees_registry_is_locked_against_pollution():
    """A worker must not be able to register a linked worktree on the host.

    Also found by the self-directed probe. `make_lease_selfcontained`
    deliberately does not copy `.git/worktrees`, so it did not exist, so nothing
    locked it — and `git worktree add` inside the sandbox created it. Measured:
    the host's `git worktree list` went 1 -> 2 and `.git/worktrees/` appeared on
    the host, even though the new worktree's own path (sandbox tmpfs) did not
    survive. Registry pollution that outlives confinement violates the
    zero-worktree-residue requirement.
    """
    from substrate.execution.attempts.field_task_scope import git_readonly_subpaths

    root = tempfile.mkdtemp()
    os.makedirs(os.path.join(root, ".git"))
    subs = {os.path.relpath(p, root) for p in git_readonly_subpaths(root)}
    assert ".git/worktrees" in subs, "the linked-worktree registry must be read-only"
    assert os.path.isdir(os.path.join(root, ".git", "worktrees"))


def test_worker_cannot_version_the_projection_through_the_index():
    """The one remaining index channel is adjudicated, not waved through.

    ``.git/index`` must stay writable (`git add` needs it), so a worker CAN run
    ``git update-index --no-skip-worktree OBJECTIVE.md`` (rc=0), stage the
    projected content, and commit it. That is the only way projection content
    can enter git history after the invocation-41 correction — and it puts
    ``OBJECTIVE.md`` squarely into ``<base>..HEAD``, where the diff-scope
    verdict refuses the attempt. rc=0 on the update-index is benign; a SUCCEEDED
    attempt carrying projection content would not be.
    """
    root = tempfile.mkdtemp()
    lease, base = _real_lease(root)
    projection = W.project_task_local_objective(_package(), lease)
    W._mark_projection_execution_context(lease, projection)
    W.prepare_attempt_git_capability(lease, "ea-adv")

    res = _run_git(
        lease,
        "set -e\n"
        "git update-index --no-skip-worktree OBJECTIVE.md\n"
        "git add OBJECTIVE.md\n"
        "echo work >> app/main.py; git add app/main.py\n"
        "git -c user.email=w@w -c user.name=w commit -q -m 'claim projection as work'\n",
    )
    assert res.returncode == 0, f"the vector itself must be reproducible: {res.stderr}"
    ok, detail = _verdict(lease, base)
    assert not ok, f"projection content committed as worker output must be refused, got: {detail}"
    assert "OBJECTIVE.md" in detail, detail


def _lease_with_secret(root: str) -> tuple[str, str]:
    """A lease whose scope is ONLY `app/main.py`; `secret/` is forbidden."""
    repo = os.path.join(root, "fixture")
    os.makedirs(os.path.join(repo, "app"))
    os.makedirs(os.path.join(repo, "secret"))

    def g(*a):
        return subprocess.run(["git", *a], cwd=repo, capture_output=True, text=True, timeout=60)

    for rel, body in (
        ("app/main.py", "# base\n"),
        ("secret/key.txt", "REAL SECRET\n"),
        ("OBJECTIVE.md", "# ALL TASKS\n"),
    ):
        with open(os.path.join(repo, rel), "w", encoding="utf-8") as fh:
            fh.write(body)
    g("init", "-q", "-b", "main")
    g("config", "user.email", "t@t.t")
    g("config", "user.name", "t")
    g("add", "-A")
    g("commit", "-qm", "seed")
    # A second commit so the authorized base has a parent: the detach vector
    # (`reset --soft HEAD~1`) needs somewhere below the base to land.
    with open(os.path.join(repo, "app", "main.py"), "a", encoding="utf-8") as fh:
        fh.write("# evolved\n")
    g("add", "-A")
    g("commit", "-qm", "base")
    lease = os.path.join(root, "lease")
    g("worktree", "add", "-q", "-b", "b", lease, "HEAD")
    W.make_lease_selfcontained(lease)
    projection = W.project_task_local_objective(_package(["app/main.py"]), lease)
    W._mark_projection_execution_context(lease, projection)
    attempt_base = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=lease, capture_output=True, text=True, timeout=60
    ).stdout.strip()
    return lease, attempt_base


def _verdict(lease: str, base: str):
    from substrate.execution.attempts.verification import _diff_scope_verdict

    class _Packet:
        packet_id = "wp-test"
        requirements = {"writable_path_scope": ["app/main.py"], "scope_declared": True}

    lease_obj = type("L", (), {"worktree_path": lease, "snapshot_ref": base})()
    result = type("R", (), {"files_changed": ["app/main.py"], "commits": ["x"]})()
    return _diff_scope_verdict(lease=lease_obj, packet=_Packet(), worker_result=result)


def _run_git(lease: str, script: str):
    return subprocess.run(
        ["bash", "-c", script], cwd=lease, capture_output=True, text=True, timeout=120
    )


def test_index_smuggled_paths_are_caught_by_the_verifier():
    """Independent review CRITICAL-1.

    The mount barrier protects the WORKING TREE. `.git/objects` and `.git/index`
    must be writable for `git add` to work, so `git hash-object -w` +
    `git update-index --cacheinfo` write a tree entry for ANY path without ever
    touching the file — the mount never fires. Reproduced against the shipped
    launcher: with scope `['app/main.py']`, a worker committed `OBJECTIVE.md` and
    `secret/key.txt` as "SMUGGLED" while both worktree copies stayed
    byte-identical, and the worktree-vs-base diff reported exactly
    `['app/main.py']`. The attempt PASSED containment.

    A barrier that is reachable but bypassable is worse than one that is
    unreachable: it looks enforced. The verdict therefore covers the COMMIT
    RANGE, not just the worktree.
    """
    root = tempfile.mkdtemp()
    lease, base = _lease_with_secret(root)
    _run_git(
        lease,
        "set -e\n"
        "B=$(echo SMUGGLED | git hash-object -w --stdin)\n"
        "git update-index --add --cacheinfo 100644,$B,OBJECTIVE.md\n"
        "git update-index --add --cacheinfo 100644,$B,secret/key.txt\n"
        "echo work >> app/main.py; git add app/main.py\n"
        "git -c user.email=w@w -c user.name=w commit -q -m work\n",
    )
    ok, detail = _verdict(lease, base)
    assert not ok, f"smuggled commit paths must be refused, got: {detail}"
    assert "OBJECTIVE.md" in detail and "secret/key.txt" in detail, detail
    # ...and the worktree copies really were untouched, which is why only the
    # commit range could see it.
    with open(os.path.join(lease, "secret", "key.txt"), encoding="utf-8") as fh:
        assert fh.read().strip() == "REAL SECRET"


def test_detaching_the_authorized_base_is_caught_by_the_verifier():
    """Independent review HIGH-1 (invocation-41 form).

    The worker owns its own ref, so `git reset --soft HEAD~1` moves its history
    BELOW the authorized base and lets it re-commit any path with content of its
    choosing — touching no protected file, so the mount barrier stays silent.
    The base-ancestry check must refuse a history the authorized base is no
    longer an ancestor of.

    The invariant was asserted in a comment and never checked. Now it is checked.
    """
    root = tempfile.mkdtemp()
    lease, base = _lease_with_secret(root)
    _run_git(
        lease,
        "set -e\n"
        "git reset --soft HEAD~1\n"
        "B=$(echo REWROTE | git hash-object -w --stdin)\n"
        "git update-index --add --cacheinfo 100644,$B,OBJECTIVE.md\n"
        "echo work >> app/main.py; git add app/main.py\n"
        "git -c user.email=w@w -c user.name=w commit -q -m attempt\n",
    )
    ok, detail = _verdict(lease, base)
    assert not ok, f"a detached trusted base must be refused, got: {detail}"
    assert "ancestor" in detail.lower(), detail


def test_an_honest_in_scope_worker_still_passes():
    """The two fixes above must not refuse legitimate work.

    Without this, "refuse everything" would satisfy both tests above and break
    every real attempt.
    """
    root = tempfile.mkdtemp()
    lease, base = _lease_with_secret(root)
    _run_git(
        lease,
        "set -e\n"
        "echo 'def search(): pass' >> app/main.py\n"
        "git add app/main.py\n"
        "git -c user.email=w@w -c user.name=w commit -q -m legit\n",
    )
    ok, detail = _verdict(lease, base)
    assert ok, f"an honest in-scope worker must still pass, got: {detail}"


def test_recovery_refuses_to_resign_a_tampered_inflight_record(tmp_path):
    """Independent review HIGH-2.

    Stale-inflight recovery refreshes a claim deadline and re-signs. It used to
    re-sign whatever was on disk, so an attacker with spool filesystem access
    could widen the scope in an inflight record, wait for recovery, and have the
    spool mint a VALID signature over the tampered envelope. The HMAC is sound
    everywhere else; this was the one place it was applied to unverified input.
    """
    import time

    root = str(tmp_path)
    spool = DispatchSpool(root, SECRET)
    spool.enqueue(
        DispatchEnvelope(
            dispatch_id="d-1",
            attempt_id="ea-1",
            task_id="wp-a",
            nonce=os.urandom(8).hex(),
            sequence=1,
            expires_at=time.time() + 3600,
            governance_constraints=["writable_path_scope=['app/main.py']"],
        )
    )
    assert spool.claim_next() is not None, "precondition: honest envelope claimable"

    inflight = os.path.join(root, "inflight")
    name = sorted(f for f in os.listdir(inflight) if f.endswith(".json"))[0]
    path = os.path.join(inflight, name)
    with open(path, encoding="utf-8") as fh:
        record = json.load(fh)
    record["envelope"]["governance_constraints"] = ["writable_path_scope=['/']"]
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(record, fh)
    stale = time.time() - 99999
    os.utime(path, (stale, stale))

    spool.recover_stale_inflight(older_than_seconds=60.0)
    assert spool.claim_next() is None, "a tampered record must never be re-signed"
    assert os.listdir(os.path.join(root, "quarantine")), "it must be quarantined"


def test_an_uninspectable_commit_range_fails_closed(monkeypatch):
    """Mutation m22: "the commit range could not be read" must not mean "empty".

    The CRITICAL-1 fix reads `<base>..HEAD` to catch index-smuggled paths. If
    that command fails and the code carried on with whatever the worktree diff
    said, the smuggling window reopens exactly when git is least healthy — and a
    failure to observe would silently read as an observation of nothing. That is
    the fail-open shape this campaign keeps rediscovering, so it gets a real
    test rather than an equivalence argument.
    """
    import substrate.execution.cpu_gate as cg
    from substrate.execution.attempts.verification import _actual_changed_paths

    root = tempfile.mkdtemp()
    lease, base = _lease_with_secret(root)
    real = cg.gated_subprocess_run

    def fail_commit_range(cmd, **kwargs):
        # Only the commit-range probe fails; every other git call is real.
        if list(cmd)[:3] == ["git", "diff", "--name-only"] and ".." in str(cmd[-1]):
            return type("R", (), {"returncode": 128, "stdout": "", "stderr": "boom"})()
        return real(cmd, **kwargs)

    monkeypatch.setattr(cg, "gated_subprocess_run", fail_commit_range)
    lease_obj = type("L", (), {"worktree_path": lease, "snapshot_ref": base})()
    result = type("R", (), {"files_changed": [], "commits": []})()
    paths, source, independent = _actual_changed_paths(lease_obj, result)
    assert not independent, (
        "an uninspectable commit range must NOT yield an independent verdict — "
        f"got independent={independent} via {source!r}"
    )
    assert paths == []


def test_an_unanswerable_ancestry_question_fails_closed(monkeypatch):
    """Mutation m24: "cannot tell" must never mean "yes".

    The HIGH-1 fix asks git whether the authorized base is still an ancestor of
    HEAD. If the CPU gate refuses (returns None) and the code treated that as a
    pass, a worker could detach the trusted commit precisely when the host is
    loaded — a defect whose reachability depends on machine load.
    """
    import substrate.execution.cpu_gate as cg
    from substrate.execution.attempts.verification import _base_is_ancestor_of_head

    root = tempfile.mkdtemp()
    lease, base = _lease_with_secret(root)
    monkeypatch.setattr(cg, "gated_subprocess_run", lambda *a, **k: None)
    ok, detail = _base_is_ancestor_of_head(
        type("L", (), {"worktree_path": lease, "snapshot_ref": base})()
    )
    assert not ok, f"an unanswerable ancestry check must fail closed, got: {detail}"
    assert "cpu gate" in detail.lower() or "refused" in detail.lower(), detail


def test_a_primitive_that_cannot_enforce_scope_refuses_to_run(monkeypatch):
    """Independent review MEDIUM-1.

    Only the bwrap branch can express per-path binds; systemd-run and nsjail
    ignore them. On a host without bwrap a profile carrying scope_enforced=True
    would have run with the flag set and NOTHING enforced. A barrier that
    silently becomes advisory is worse than an absent one — the absence is at
    least visible.
    """
    from substrate.execution.attempts import host_isolation as hi

    monkeypatch.setattr(hi, "isolation_primitive", lambda: "systemd-run")
    profile = hi.IsolationProfile(
        worktree_path="/tmp/wt",
        worker_home="/tmp/home",
        tmp_path="/tmp/t",
        readonly_subpaths=["/tmp/wt/secret"],
        writable_subpaths=[],
        scope_enforced=True,
    )
    with pytest.raises(hi.IsolationUnavailable) as exc:
        hi.build_isolated_command(["/bin/true"], profile)
    assert "cannot enforce per-path write scope" in str(exc.value)


@pytest.mark.parametrize("attempt_id", ["", "   ", "../escape", "a/b"])
def test_a_malformed_attempt_id_cannot_mint_a_ref(attempt_id):
    """An attempt id must never be able to traverse out of its namespace."""
    from substrate.execution.attempts.field_task_scope import (
        ScopeResolutionError,
        attempt_ref_name,
    )

    with pytest.raises(ScopeResolutionError):
        attempt_ref_name(attempt_id)
