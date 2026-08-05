"""Verified-commit retention + explicit trusted sandbox base.

These tests drive the REAL shipped path: the real ``SandboxManager``, real git
repositories, the real ``LeaseManager``, and the real ``terminalize()``. Nothing
about the boundary under test is stubbed — a stand-in that bypasses git or the
sandbox would prove nothing about the defect this closes.

The defect (field run ``20260805T182714Z-p1``): a verified predecessor's commit
was destroyed by ``cleanup_sandbox`` → ``git branch -D`` **56 ms** before the
dependent Task's lease was created, so the dependent branched from a stale HEAD
and could not see content it was contractually told to integrate.

Scope: retention keeps verified commits reachable and ``create_sandbox`` accepts
an explicit trusted base. Fan-in *consumption* of retained commits is NOT
implemented — no test here implies it is.
"""

from __future__ import annotations

import os
import subprocess
from types import SimpleNamespace

import pytest

from substrate.execution.attempts.records import ExecutionAttempt, ExecutionAttemptStatus
from substrate.execution.attempts.verified_commit_retention import (
    TRUSTED_ROOT,
    CpuGateRefused,
    RetentionError,
    release_trusted_refs,
    resolve_trusted_commit,
    retain_verified_commit,
    trusted_ref,
)
from substrate.organism.worktree_sandbox import SandboxManager

_S = ExecutionAttemptStatus
CAND = "9a8c4a30620cfde5cec7b05e7a54d625ee6cd450"
RUN = "20260805T182714Z-p1"


def _git(args: list[str], cwd: str) -> subprocess.CompletedProcess:
    return subprocess.run(["git", *args], cwd=cwd, capture_output=True, text=True)


@pytest.fixture
def repo(tmp_path):
    """A real fixture repo shaped like the field fixture."""
    # CANONICAL candidate layout — production always uses
    # .../candidates/<lane>/<candidate-sha>/targets/<run-id>/fixture, and the
    # authoritative retention binding is derived from exactly this path.
    r = str(tmp_path / "candidates" / "wave2" / CAND / "targets" / RUN / "fixture")
    os.makedirs(r)
    _git(["init", "-q", "-b", "master"], r)
    _git(["config", "user.email", "t@t"], r)
    _git(["config", "user.name", "t"], r)
    os.makedirs(f"{r}/app/static")
    os.makedirs(f"{r}/tests")
    open(f"{r}/app/main.py", "w").write("base\n")
    open(f"{r}/app/static/index.html", "w").write("<html>\n")
    open(f"{r}/tests/test_api.py", "w").write("x\n")
    _git(["add", "-A"], r)
    _git(["commit", "-qm", "fixture: base notes app (green)"], r)
    return r


@pytest.fixture
def mgr(repo, tmp_path):
    return SandboxManager(
        repo_root=repo,
        worktree_base=str(tmp_path / "leases"),
        store_dir=str(tmp_path / "sandboxes"),
        max_parallel=8,
    )


def _direct_runner(**kw):
    """The mutation-runner shape LeaseManager expects (mirrors
    tests/test_wave2_terminalization.py::_lease_manager)."""
    fn = kw.get("execute_fn")
    out, ok = fn() if fn else ("", True)
    return SimpleNamespace(success=ok, output=out)


def _store(tmp_path, tag):
    from substrate.execution.attempts.store import ExecutionAttemptStore

    return ExecutionAttemptStore(
        attempts_path=str(tmp_path / f"a{tag}.jsonl"),
        grants_path=str(tmp_path / f"g{tag}.jsonl"),
        readiness_path=str(tmp_path / f"r{tag}.jsonl"),
        leases_path=str(tmp_path / f"l{tag}.jsonl"),
        assignments_path=str(tmp_path / f"asn{tag}.jsonl"),
    )


ASSIGNMENT = SimpleNamespace(
    worker_identity="cc-cli@vps-host",
    worker_agent_type="developer_agent",
    compute_node_id="n1",
    environment_class="git_worktree",
    tool_profile=[],
)
GRANT = SimpleNamespace(tenant_id="t1", credential_scope_refs=[])

BACKEND = {"app/main.py": "def search(): ...\n", "tests/test_search_api.py": "s\n"}
FRONTEND = {
    "app/static/index.html": '<input data-testid="note-search-input">\n',
    "tests/test_ui_search.py": "u\n",
}


def _work(mgr, repo, *, attempt_id, task_id, writes, retain=True, commit=True):
    """Run one 'worker': sandbox → write → commit → retain → cleanup."""
    sb = mgr.create_sandbox(candidate_id=attempt_id, candidate_slug=f"attempt-{attempt_id[:8]}")
    for path, content in writes.items():
        fp = os.path.join(sb.worktree_path, path)
        os.makedirs(os.path.dirname(fp), exist_ok=True)
        with open(fp, "a") as fh:
            fh.write(content)
    if commit:
        _git(["add", "-A"], sb.worktree_path)
        _git(["commit", "-qm", task_id], sb.worktree_path)
    sha = ""
    if retain:
        sha = retain_verified_commit(
            repo=repo, worktree=sb.worktree_path, candidate=CAND, run_id=RUN,
            task_id=task_id, attempt_id=attempt_id, base_commit=sb.base_commit,
        )
    base = sb.base_commit
    mgr.cleanup_sandbox(sb.sandbox_id)
    return sha, base


# ── 1,2: retention survives worker cleanup ──────────────────────────────────


def test_verified_commit_survives_branch_and_worktree_deletion(mgr, repo):
    """1,2: a verified commit gets a trusted ref, and the worker branch and
    worktree may be removed while the commit stays reachable.

    This is the exact defect from field run 20260805T182714Z-p1.
    """
    sha, base = _work(mgr, repo, attempt_id="ea-be", task_id="wp-be", writes=BACKEND)
    assert sha and sha != base, "the attempt's own commit must be retained, not its base"

    branches = _git(["branch", "--format=%(refname:short)"], repo).stdout.split()
    assert branches == ["master"], f"worker branches must be deleted, found {branches}"

    assert _git(["cat-file", "-e", f"{sha}^{{commit}}"], repo).returncode == 0
    assert resolve_trusted_commit(
        repo=repo, candidate=CAND, run_id=RUN, task_id="wp-be", attempt_id="ea-be"
    ) == sha


def test_retained_commits_survive_aggressive_gc(mgr, repo):
    """10: retention must not depend on reflogs or unreachable-object grace."""
    sha, _ = _work(mgr, repo, attempt_id="ea-be", task_id="wp-be", writes=BACKEND)
    _git(["reflog", "expire", "--expire=now", "--all"], repo)
    _git(["gc", "--prune=now", "-q"], repo)
    assert _git(["cat-file", "-e", f"{sha}^{{commit}}"], repo).returncode == 0, (
        "a trusted ref must keep the commit alive through gc --prune=now"
    )


def test_parallel_predecessors_each_retain_their_own_commit(mgr, repo):
    """Two parallel attempts from ONE base each retain a DISTINCT commit."""
    b, base_b = _work(mgr, repo, attempt_id="ea-be", task_id="wp-be", writes=BACKEND)
    f, base_f = _work(mgr, repo, attempt_id="ea-fe", task_id="wp-fe", writes=FRONTEND)
    assert base_b == base_f, "parallel attempts must branch from one common base"
    assert b and f and b != f
    for sha in (b, f):
        assert _git(["cat-file", "-e", f"{sha}^{{commit}}"], repo).returncode == 0


# ── 9: workers cannot reach the trusted namespace ───────────────────────────


def test_trusted_refs_live_outside_refs_heads(mgr, repo):
    """9: a worker lease can write refs/heads; the trusted namespace is elsewhere."""
    _work(mgr, repo, attempt_id="ea-be", task_id="wp-be", writes=BACKEND)
    ref = trusted_ref(candidate=CAND, run_id=RUN, task_id="wp-be", attempt_id="ea-be")
    assert ref.startswith(TRUSTED_ROOT + "/")
    assert not ref.startswith("refs/heads")
    assert ref not in _git(["for-each-ref", "--format=%(refname)", "refs/heads"], repo).stdout


def test_trusted_ref_path_cannot_escape_namespace():
    """A crafted id must not escape into refs/heads or become a git option."""
    for bad in ("../heads", "-x", "--upload-pack=evil", "a/b", "", "..", ".", "a/../../heads"):
        with pytest.raises(RetentionError, match="unsafe"):
            trusted_ref(candidate=bad, run_id=RUN, task_id="t", attempt_id="a")


# ── 3,4: failed / unverified / no-commit attempts retain nothing ────────────


def test_attempt_with_no_commit_retains_nothing(mgr, repo):
    """3: an attempt whose HEAD is still its base produced no output. Retaining
    it would publish the pre-existing base as if it were verified work."""
    sha, _ = _work(
        mgr, repo, attempt_id="ea-none", task_id="wp-be",
        writes={"app/main.py": "scratch\n"}, commit=False,
    )
    assert sha == "", "uncommitted worker scratch must never be retained as verified"
    assert resolve_trusted_commit(
        repo=repo, candidate=CAND, run_id=RUN, task_id="wp-be", attempt_id="ea-none"
    ) == ""


def test_successful_retry_retains_its_own_commit_and_failure_retains_none(mgr, repo):
    """4: retry lineage — the failed attempt leaves no ref; the successful retry
    retains its own commit. No special case is needed: a failed attempt simply
    has nothing to find."""
    failed, _ = _work(
        mgr, repo, attempt_id="ea-fail", task_id="wp-be", writes={}, retain=False, commit=False
    )
    assert failed == ""
    assert resolve_trusted_commit(
        repo=repo, candidate=CAND, run_id=RUN, task_id="wp-be", attempt_id="ea-fail"
    ) == ""

    retry, _ = _work(mgr, repo, attempt_id="ea-retry", task_id="wp-be", writes=BACKEND)
    assert retry
    assert resolve_trusted_commit(
        repo=repo, candidate=CAND, run_id=RUN, task_id="wp-be", attempt_id="ea-retry"
    ) == retry


# ── 5,8: idempotence + immutability ─────────────────────────────────────────


def test_retention_is_idempotent_but_immutable(mgr, repo):
    """5,8: re-retaining the same commit is a no-op; rewriting the ref to a
    DIFFERENT commit is refused — a dependent may already trust that name."""
    sb = mgr.create_sandbox(candidate_id="ea-be", candidate_slug="attempt-be")
    open(f"{sb.worktree_path}/app/main.py", "a").write("def search(): ...\n")
    _git(["add", "-A"], sb.worktree_path)
    _git(["commit", "-qm", "backend"], sb.worktree_path)
    kw = dict(candidate=CAND, run_id=RUN, task_id="wp-be", attempt_id="ea-be")

    first = retain_verified_commit(repo=repo, worktree=sb.worktree_path, **kw)
    again = retain_verified_commit(repo=repo, worktree=sb.worktree_path, **kw)
    assert first == again, "duplicate terminalization must be idempotent"

    with pytest.raises(RetentionError, match="immutable once retained"):
        retain_verified_commit(repo=repo, worktree=repo, **kw)
    assert resolve_trusted_commit(repo=repo, **kw) == first


# ── 6,7: CPU-gate refusal and write failure block destructive cleanup ───────


def test_cpu_gate_refusal_never_reads_as_a_git_answer(monkeypatch):
    """6: a gate refusal mapped to rc=1 made every `rc != 0` consumer read
    "no commit to retain" / "no such ref" / "nothing to delete".

    Under load that meant: verified commit NOT retained → lease released →
    `git branch -D` → commit unreachable. That is the original field defect
    reproduced *silently*, precisely when the host is busy. A refusal must RAISE.
    """
    import substrate.execution.attempts.verified_commit_retention as m

    monkeypatch.setattr(m, "gated_subprocess_run", lambda *a, **k: None)
    kw = dict(candidate="C", run_id="R", task_id="t", attempt_id="a")
    with pytest.raises(CpuGateRefused):
        m.retain_verified_commit(repo="/tmp", worktree="/tmp", **kw)
    with pytest.raises(CpuGateRefused):
        m.resolve_trusted_commit(repo="/tmp", **kw)
    with pytest.raises(CpuGateRefused):
        m.release_trusted_refs(repo="/tmp", candidate="C", run_id="R")


def test_refused_retention_blocks_destructive_cleanup(tmp_path, monkeypatch, repo, mgr):
    """6,7: a refused retention must BLOCK destructive cleanup.

    The invariant is the COMMIT, not a status flag. An earlier version of this
    test asserted only ``not result.ok`` and ``"retention" in errors`` — both
    were already true while the lease was still released, the branch deleted, and
    the verified commit destroyed. The reporting had been fixed; the outcome had
    not. Assert what the docstring actually promises.
    """
    from substrate.execution.attempts.leases import LeaseManager
    from substrate.execution.attempts.terminalization import terminalize

    monkeypatch.setenv("UMH_W2_CANDIDATE_SHA", CAND)
    monkeypatch.setenv("UMH_W2_RUN_ID", RUN)
    lm = LeaseManager(_store(tmp_path, "gate"), mgr, mutation_runner=_direct_runner)
    attempt = ExecutionAttempt(
        attempt_id="ea-gate", task_id="wp-be", status=_S.LEASED.value,
        worker_identity="cc-cli@vps-host",
    )
    lease = lm.acquire(attempt=attempt, assignment=ASSIGNMENT, grant=GRANT)
    with open(os.path.join(lease.worktree_path, "app/main.py"), "a") as fh:
        fh.write("def search(): ...\n")
    _git(["add", "-A"], lease.worktree_path)
    _git(["commit", "-qm", "backend"], lease.worktree_path)
    verified = _git(["rev-parse", "HEAD"], lease.worktree_path).stdout.strip()

    import substrate.execution.attempts.verified_commit_retention as m

    monkeypatch.setattr(m, "gated_subprocess_run", lambda *a, **k: None)
    attempt.status = _S.SUCCEEDED.value
    attempt.lease_id = lease.lease_id
    result = terminalize(
        attempt=attempt, reason="succeeded", lease_manager=lm,
        run_root=str(tmp_path / "run"), raise_on_security_failure=False,
    )

    assert not result.ok, "a refused retention must fail the terminalization"
    assert any("retention" in e for e in result.errors), result.errors

    # THE INVARIANT — everything above is reporting; these are the outcome.
    assert not result.lease_released, (
        "the lease must NOT be released: releasing runs cleanup_sandbox → "
        "git branch -D, which destroys the verified commit"
    )
    assert os.path.isdir(lease.worktree_path), "the worker worktree must survive"
    _git(["reflog", "expire", "--expire=now", "--all"], repo)
    _git(["gc", "--prune=now", "-q"], repo)
    assert _git(["cat-file", "-e", f"{verified}^{{commit}}"], repo).returncode == 0, (
        "the verifier-approved commit must still exist — a refused retention that "
        "still deletes the branch reproduces field run 20260805T182714Z-p1 exactly"
    )


def test_refused_retention_raises_when_the_caller_wants_it_to(tmp_path, monkeypatch, repo, mgr):
    """The default (``raise_on_security_failure=True``) surfaces the refusal
    rather than returning a quietly-degraded result."""
    from substrate.execution.attempts.leases import LeaseManager
    from substrate.execution.attempts.terminalization import TerminalizationError, terminalize

    monkeypatch.setenv("UMH_W2_CANDIDATE_SHA", CAND)
    monkeypatch.setenv("UMH_W2_RUN_ID", RUN)
    lm = LeaseManager(_store(tmp_path, "raise"), mgr, mutation_runner=_direct_runner)
    attempt = ExecutionAttempt(
        attempt_id="ea-raise", task_id="wp-be", status=_S.LEASED.value,
        worker_identity="cc-cli@vps-host",
    )
    lease = lm.acquire(attempt=attempt, assignment=ASSIGNMENT, grant=GRANT)
    with open(os.path.join(lease.worktree_path, "app/main.py"), "a") as fh:
        fh.write("work\n")
    _git(["add", "-A"], lease.worktree_path)
    _git(["commit", "-qm", "w"], lease.worktree_path)

    import substrate.execution.attempts.verified_commit_retention as m

    monkeypatch.setattr(m, "gated_subprocess_run", lambda *a, **k: None)
    attempt.status = _S.SUCCEEDED.value
    attempt.lease_id = lease.lease_id
    with pytest.raises(TerminalizationError, match="lease NOT released"):
        terminalize(
            attempt=attempt, reason="succeeded", lease_manager=lm,
            run_root=str(tmp_path / "run"),
        )
    assert os.path.isdir(lease.worktree_path), "the worktree must survive the raise"


def test_successful_retention_still_completes_full_cleanup(tmp_path, monkeypatch, repo, mgr):
    """The new gate must not block the HAPPY path: when retention succeeds,
    every downstream step still runs."""
    from substrate.execution.attempts.leases import LeaseManager
    from substrate.execution.attempts.terminalization import terminalize

    monkeypatch.setenv("UMH_W2_CANDIDATE_SHA", CAND)
    monkeypatch.setenv("UMH_W2_RUN_ID", RUN)
    lm = LeaseManager(_store(tmp_path, "happy"), mgr, mutation_runner=_direct_runner)
    attempt = ExecutionAttempt(
        attempt_id="ea-ok", task_id="wp-be", status=_S.LEASED.value,
        worker_identity="cc-cli@vps-host",
    )
    lease = lm.acquire(attempt=attempt, assignment=ASSIGNMENT, grant=GRANT)
    with open(os.path.join(lease.worktree_path, "app/main.py"), "a") as fh:
        fh.write("work\n")
    _git(["add", "-A"], lease.worktree_path)
    _git(["commit", "-qm", "w"], lease.worktree_path)

    attempt.status = _S.SUCCEEDED.value
    attempt.lease_id = lease.lease_id
    result = terminalize(
        attempt=attempt, reason="succeeded", lease_manager=lm,
        run_root=str(tmp_path / "run"), raise_on_security_failure=False,
    )
    assert result.retained_commit, "retention must have succeeded"
    assert result.lease_released, "the happy path must still release the lease"
    assert not os.path.isdir(lease.worktree_path), "and still destroy the worktree"
    assert result.home_destroyed, "and still destroy the credential home"


# ── the REAL terminalize() ordering ─────────────────────────────────────────


def test_terminalize_retains_before_releasing_the_lease(tmp_path, monkeypatch, repo, mgr):
    """THE regression, driven through the REAL ``terminalize()`` with a REAL
    ``LeaseManager`` and REAL ``SandboxManager``.

    Retention MUST happen before ``_release_lease``, because release runs
    ``cleanup_sandbox`` → ``git branch -D``. Ordering these two the other way
    round restores the original defect exactly — a unit test of the pieces cannot
    see it, which is why this drives the real authority.
    """
    from substrate.execution.attempts.leases import LeaseManager
    from substrate.execution.attempts.terminalization import terminalize

    monkeypatch.setenv("UMH_W2_CANDIDATE_SHA", CAND)
    monkeypatch.setenv("UMH_W2_RUN_ID", RUN)
    lm = LeaseManager(_store(tmp_path, "ord"), mgr, mutation_runner=_direct_runner)
    attempt = ExecutionAttempt(
        attempt_id="ea-be", task_id="wp-be", status=_S.LEASED.value,
        worker_identity="cc-cli@vps-host",
    )
    lease = lm.acquire(attempt=attempt, assignment=ASSIGNMENT, grant=GRANT)

    wt = lease.worktree_path
    with open(os.path.join(wt, "app/main.py"), "a") as fh:
        fh.write("def search(): ...\n")
    _git(["add", "-A"], wt)
    _git(["commit", "-qm", "backend"], wt)
    verified = _git(["rev-parse", "HEAD"], wt).stdout.strip()

    attempt.status = _S.SUCCEEDED.value
    attempt.lease_id = lease.lease_id
    result = terminalize(
        attempt=attempt, reason="succeeded", lease_manager=lm,
        run_root=str(tmp_path / "run"), raise_on_security_failure=False,
    )

    assert result.retained_commit == verified
    assert result.lease_released, "the lease must still be released"
    assert not os.path.isdir(wt), "the worker worktree must still be destroyed"
    assert resolve_trusted_commit(
        repo=repo, candidate=CAND, run_id=RUN, task_id="wp-be", attempt_id="ea-be"
    ) == verified, (
        "the verified commit must be reachable through its trusted ref AFTER the "
        "lease was released — retention ordered after release loses it entirely"
    )
    _git(["reflog", "expire", "--expire=now", "--all"], repo)
    _git(["gc", "--prune=now", "-q"], repo)
    assert _git(["cat-file", "-e", f"{verified}^{{commit}}"], repo).returncode == 0


def test_terminalize_retains_nothing_for_a_failed_attempt(tmp_path, monkeypatch, repo, mgr):
    """3: a rejected attempt must contribute NOTHING — no trusted ref at all."""
    from substrate.execution.attempts.leases import LeaseManager
    from substrate.execution.attempts.terminalization import terminalize

    monkeypatch.setenv("UMH_W2_CANDIDATE_SHA", CAND)
    monkeypatch.setenv("UMH_W2_RUN_ID", RUN)
    lm = LeaseManager(_store(tmp_path, "fail"), mgr, mutation_runner=_direct_runner)
    attempt = ExecutionAttempt(
        attempt_id="ea-fail", task_id="wp-be", status=_S.LEASED.value,
        worker_identity="cc-cli@vps-host",
    )
    lease = lm.acquire(attempt=attempt, assignment=ASSIGNMENT, grant=GRANT)
    with open(os.path.join(lease.worktree_path, "app/main.py"), "a") as fh:
        fh.write("half-finished\n")
    _git(["add", "-A"], lease.worktree_path)
    _git(["commit", "-qm", "partial"], lease.worktree_path)

    attempt.status = _S.FAILED.value
    attempt.lease_id = lease.lease_id
    result = terminalize(
        attempt=attempt, reason="verification_rejected", lease_manager=lm,
        run_root=str(tmp_path / "run"), raise_on_security_failure=False,
    )
    assert result.retained_commit == ""
    assert resolve_trusted_commit(
        repo=repo, candidate=CAND, run_id=RUN, task_id="wp-be", attempt_id="ea-fail"
    ) == "", "a rejected attempt must leave no trusted ref for any dependent to find"


# ── 11,12,13: explicit trusted sandbox base ─────────────────────────────────


def test_explicit_base_creates_the_worktree_from_that_exact_commit(mgr, repo):
    """11: the sandbox branches from the supplied trusted commit, and the
    worktree is PROVEN to sit on the recorded base."""
    sha, _ = _work(mgr, repo, attempt_id="ea-be", task_id="wp-be", writes=BACKEND)
    sb = mgr.create_sandbox(candidate_id="ea-dep", candidate_slug="a-dep", base_commit=sha)
    assert sb.base_commit == sha, "recorded base must BE the supplied trusted commit"
    assert _git(["rev-parse", "HEAD"], sb.worktree_path).stdout.strip() == sha, (
        "the launched base must equal the recorded base"
    )
    assert os.path.exists(f"{sb.worktree_path}/tests/test_search_api.py"), (
        "the dependent worktree must contain the retained commit's content"
    )


def test_omitted_base_preserves_existing_head_behaviour(mgr, repo):
    """12: explicit base is opt-in — omitting it must not change anything."""
    head = _git(["rev-parse", "HEAD"], repo).stdout.strip()
    sb = mgr.create_sandbox(candidate_id="ea-x", candidate_slug="attempt-x")
    assert sb.base_commit == head
    assert _git(["rev-parse", "HEAD"], sb.worktree_path).stdout.strip() == head


def test_unresolvable_base_fails_closed_without_falling_back(mgr, repo):
    """13: a wrong/stale/missing base must never silently degrade to HEAD."""
    head = _git(["rev-parse", "HEAD"], repo).stdout.strip()
    for bad in ("0" * 40, "refs/umh/verified/nope", "deadbeef"):
        with pytest.raises(RuntimeError, match="does not resolve"):
            mgr.create_sandbox(candidate_id="ea-y", candidate_slug="a-y", base_commit=bad)
    assert _git(["rev-parse", "HEAD"], repo).stdout.strip() == head


def test_lease_snapshot_ref_equals_the_explicit_base(tmp_path, repo, mgr):
    """The verifier's authorized diff base and the launched base must be the same
    value by construction — a divergence voids every scope verdict."""
    from substrate.execution.attempts.leases import LeaseManager

    sha, _ = _work(mgr, repo, attempt_id="ea-be", task_id="wp-be", writes=BACKEND)
    lm = LeaseManager(_store(tmp_path, "snap"), mgr, mutation_runner=_direct_runner)
    lease = lm.acquire(
        attempt=ExecutionAttempt(attempt_id="ea-dep", task_id="wp-dep", status=_S.LEASED.value),
        assignment=ASSIGNMENT, grant=GRANT, base_commit=sha,
    )
    assert lease.snapshot_ref == sha
    assert lease.source_ref["base_commit"] == sha
    assert _git(["rev-parse", "HEAD"], lease.worktree_path).stdout.strip() == sha


def test_lease_refuses_a_sandbox_that_ignored_the_requested_base(tmp_path, repo):
    """A sandbox that honours a DIFFERENT base than requested must fail the lease
    rather than record a base the worktree is not on.

    Asserting only ``snapshot_ref == requested`` cannot see this: when the sandbox
    complies the two are equal, so a mutant recording the REQUESTED value and
    dropping the divergence check still passes. Only a lying sandbox exposes it.
    """
    from substrate.execution.attempts.leases import LeaseError, LeaseManager

    head = _git(["rev-parse", "HEAD"], repo).stdout.strip()

    class _LyingSandbox:
        def __init__(self, root):
            self._repo_root = root
            self._n = 0

        def create_sandbox(
            self, candidate_id, candidate_slug, agent_type="developer_agent", base_commit=""
        ):
            self._n += 1
            wt = os.path.join(str(tmp_path), f"lying-{self._n}")
            branch = f"auto/lying-{self._n}"
            _git(["worktree", "add", "-q", "-b", branch, wt], self._repo_root)
            return SimpleNamespace(
                worktree_path=wt, branch_name=branch, base_commit=head,
                sandbox_id=f"sb-lying-{self._n}",
            )

        def cleanup_sandbox(self, sandbox_id):
            return True

    lm = LeaseManager(_store(tmp_path, "lie"), _LyingSandbox(repo), mutation_runner=_direct_runner)
    with pytest.raises(LeaseError, match="refusing a lease whose recorded base"):
        lm.acquire(
            attempt=ExecutionAttempt(attempt_id="ea-l", task_id="wp-l", status=_S.LEASED.value),
            assignment=ASSIGNMENT, grant=GRANT, base_commit="b" * 40,
        )


def test_legacy_sandbox_manager_without_base_support_still_works(tmp_path, repo):
    """Regression: threading `base_commit` UNCONDITIONALLY broke every sandbox
    implementation predating the parameter (60 failures in
    tests/test_wave2_terminalization.py). Pass it only when one is requested, and
    fail closed when a manager cannot honour it."""
    from substrate.execution.attempts.leases import LeaseError, LeaseManager

    class _LegacySandbox:
        def __init__(self, root):
            self._repo_root = root
            self._n = 0

        def create_sandbox(self, candidate_id, candidate_slug, agent_type="developer_agent"):
            self._n += 1
            wt = os.path.join(str(tmp_path), f"legacy-{self._n}")
            branch = f"auto/legacy-{self._n}"
            _git(["worktree", "add", "-q", "-b", branch, wt], self._repo_root)
            head = _git(["rev-parse", "HEAD"], self._repo_root).stdout.strip()
            return SimpleNamespace(
                worktree_path=wt, branch_name=branch, base_commit=head,
                sandbox_id=f"sb-legacy-{self._n}",
            )

    lm = LeaseManager(
        _store(tmp_path, "legacy"), _LegacySandbox(repo), mutation_runner=_direct_runner
    )
    lease = lm.acquire(
        attempt=ExecutionAttempt(attempt_id="ea-1", task_id="wp-1", status=_S.LEASED.value),
        assignment=ASSIGNMENT, grant=GRANT,
    )
    assert lease.worktree_path, "no explicit base → legacy behaviour unchanged"

    with pytest.raises(LeaseError, match="cannot honour an explicit trusted base"):
        lm.acquire(
            attempt=ExecutionAttempt(attempt_id="ea-2", task_id="wp-2", status=_S.LEASED.value),
            assignment=ASSIGNMENT, grant=GRANT, base_commit="a" * 40,
        )


# ── PRODUCTION PATH: the real ControlPlanePoller._terminalize ───────────────
#
# Every test above drives `terminalize()` directly. That is one call-frame deep,
# and it is exactly how two CRITICALs shipped: (1) retention never ran in
# production because its binding came from env vars nothing set, and (2) the
# poller's RV-HIGH-2 healer force-revoked the withheld lease and destroyed the
# commit the withhold protected. Neither was reachable from a direct
# `terminalize()` test. These drive the REAL production caller.


@pytest.fixture
def candidate_repo(tmp_path):
    """A fixture repo at the CANONICAL candidate path, so the authoritative
    binding (candidate sha + run id) is derivable from the lease's repo_root:

        .../candidates/<lane>/<candidate-sha>/targets/<run-id>/fixture
    """
    r = str(tmp_path / "candidates" / "wave2" / CAND / "targets" / RUN / "fixture")
    os.makedirs(r)
    _git(["init", "-q", "-b", "master"], r)
    _git(["config", "user.email", "t@t"], r)
    _git(["config", "user.name", "t"], r)
    os.makedirs(f"{r}/app")
    open(f"{r}/app/main.py", "w").write("base\n")
    _git(["add", "-A"], r)
    _git(["commit", "-qm", "fixture base"], r)
    return r


def _production_terminalize(
    tmp_path, repo, *, tag, correlation_id=f"w2-{RUN}", refuse_gate=False,
    monkeypatch=None, reason="succeeded",
):
    """Run ONE attempt through the REAL ControlPlanePoller._terminalize."""
    from substrate.execution.attempts.leases import LeaseManager
    from substrate.execution.attempts.poller import ControlPlanePoller, PollerPassReport

    mgr = SandboxManager(
        repo_root=repo, worktree_base=str(tmp_path / f"l{tag}"),
        store_dir=str(tmp_path / f"sb{tag}"), max_parallel=8,
    )
    store = _store(tmp_path, tag)
    lm = LeaseManager(store, mgr, mutation_runner=_direct_runner)
    attempt = ExecutionAttempt(
        attempt_id=f"ea-{tag}", task_id="wp-be", status=_S.LEASED.value,
        worker_identity="cc-cli@vps-host", correlation_id=correlation_id,
    )
    lease = lm.acquire(attempt=attempt, assignment=ASSIGNMENT, grant=GRANT)
    with open(os.path.join(lease.worktree_path, "app/main.py"), "a") as fh:
        fh.write("VERIFIED WORK\n")
    _git(["add", "-A"], lease.worktree_path)
    _git(["commit", "-qm", "verified"], lease.worktree_path)
    verified = _git(["rev-parse", "HEAD"], lease.worktree_path).stdout.strip()

    poller = ControlPlanePoller(
        store=store, spool=None, scheduler=None, verify_fn=lambda **kw: None,
        lease_manager=lm, run_root=str(tmp_path / f"run{tag}"),
    )
    attempt.status = _S.SUCCEEDED.value if reason == "succeeded" else _S.FAILED.value
    attempt.lease_id = lease.lease_id
    if refuse_gate:
        import substrate.execution.attempts.verified_commit_retention as m

        monkeypatch.setattr(m, "gated_subprocess_run", lambda *a, **k: None)
    report = PollerPassReport()
    poller._terminalize(attempt, reason, report)  # noqa: SLF001 — THE production caller
    return report, verified, lease, store


def test_production_retention_runs_without_any_env_stub(tmp_path, candidate_repo, monkeypatch):
    """CRITICAL 2: retention must run on a HEALTHY production run with NO
    environment variables set.

    It did not: the binding was read from `UMH_W2_CANDIDATE_SHA` /
    `UMH_W2_RUN_ID`, which NOTHING in production sets. The absent binding took a
    `steps.append(...)` early return, so `result.ok` was True, `errors` was
    empty, and the verified commit was destroyed by the very next step — on every
    normal run, silently.
    """
    monkeypatch.delenv("UMH_W2_CANDIDATE_SHA", raising=False)
    monkeypatch.delenv("UMH_W2_RUN_ID", raising=False)
    _report, verified, lease, _st = _production_terminalize(
        tmp_path, candidate_repo, tag="prodok"
    )

    refs = _git(
        ["for-each-ref", "--format=%(refname)", TRUSTED_ROOT], candidate_repo
    ).stdout.strip()
    assert refs, "retention must have written a trusted ref with NO env vars set"
    assert CAND in refs and RUN in refs, (
        f"the ref must carry the AUTHORITATIVE candidate+run binding, got {refs}"
    )
    _git(["reflog", "expire", "--expire=now", "--all"], candidate_repo)
    _git(["gc", "--prune=now", "-q"], candidate_repo)
    assert _git(["cat-file", "-e", f"{verified}^{{commit}}"], candidate_repo).returncode == 0, (
        "the verified commit must survive a full production terminalization"
    )
    assert not os.path.isdir(lease.worktree_path), "the worktree must still be destroyed"


def test_production_poller_does_not_reverse_a_withheld_lease(
    tmp_path, candidate_repo, monkeypatch
):
    """CRITICAL 1: the poller's RV-HIGH-2 healer must NOT force-revoke a lease
    that terminalization deliberately withheld.

    It did: the healer keys on `lease_released == False`, and `revoke()` also runs
    `cleanup_sandbox` → `git branch -D`. The gate held inside `terminalize()` and
    was reversed one frame up, so the field defect reproduced end to end.
    """
    report, verified, lease, store = _production_terminalize(
        tmp_path, candidate_repo, tag="withheld", refuse_gate=True, monkeypatch=monkeypatch
    )

    row = store.get_lease(lease.lease_id) or {}
    assert row.get("status") == "active", (
        f"the withheld lease must NOT be revoked, got status={row.get('status')!r}"
    )
    assert os.path.isdir(lease.worktree_path), "the worktree must survive"
    _git(["reflog", "expire", "--expire=now", "--all"], candidate_repo)
    _git(["gc", "--prune=now", "-q"], candidate_repo)
    assert _git(["cat-file", "-e", f"{verified}^{{commit}}"], candidate_repo).returncode == 0, (
        "the verified commit must survive the poller — this is the whole point"
    )
    assert any("WITHHELD" in e for e in report.errors), (
        f"the withhold must be surfaced as a BLOCKING report error, got {report.errors}"
    )
    assert not any("force-revoked" in e for e in report.errors), (
        "the RV-HIGH-2 healer must not have run on a deliberate withhold"
    )


def test_production_missing_binding_fails_closed_and_visibly(
    tmp_path, candidate_repo, monkeypatch
):
    """CRITICAL 2 (other half): when the binding genuinely cannot be resolved,
    retention must FAIL — visibly — not skip silently and destroy the commit."""
    monkeypatch.delenv("UMH_W2_CANDIDATE_SHA", raising=False)
    monkeypatch.delenv("UMH_W2_RUN_ID", raising=False)
    plain = str(tmp_path / "plain")
    os.makedirs(f"{plain}/app")
    _git(["init", "-q", "-b", "master"], plain)
    _git(["config", "user.email", "t@t"], plain)
    _git(["config", "user.name", "t"], plain)
    open(f"{plain}/app/main.py", "w").write("base\n")
    _git(["add", "-A"], plain)
    _git(["commit", "-qm", "base"], plain)

    report, verified, lease, store = _production_terminalize(
        tmp_path, plain, tag="nobind", correlation_id=""
    )

    assert any("cannot resolve the candidate/run binding" in e for e in report.errors), (
        f"an unresolvable binding must be VISIBLE, got {report.errors}"
    )
    row = store.get_lease(lease.lease_id) or {}
    assert row.get("status") == "active", "the lease must be withheld, not released"
    _git(["reflog", "expire", "--expire=now", "--all"], plain)
    _git(["gc", "--prune=now", "-q"], plain)
    assert _git(["cat-file", "-e", f"{verified}^{{commit}}"], plain).returncode == 0, (
        "a commit that cannot be retained must not be destroyed"
    )


def test_production_ordinary_terminal_cleanup_is_unchanged(tmp_path, candidate_repo):
    """A non-SUCCEEDED terminal reason must still fully clean up."""
    report, _verified, lease, store = _production_terminalize(
        tmp_path, candidate_repo, tag="failed", reason="verification_rejected"
    )
    row = store.get_lease(lease.lease_id) or {}
    assert row.get("status") == "released", "a rejected attempt must release normally"
    assert not os.path.isdir(lease.worktree_path), "and destroy the worktree"
    assert not any("WITHHELD" in e for e in report.errors)
    refs = _git(
        ["for-each-ref", "--format=%(refname)", TRUSTED_ROOT], candidate_repo
    ).stdout.strip()
    assert refs == "", "a rejected attempt must leave no trusted ref"


def test_unobservable_head_counts_as_at_risk(tmp_path, monkeypatch):
    """When the binding is unresolvable AND the CPU gate refuses, we cannot tell
    whether a commit exists. "Cannot tell" must count as AT RISK.

    Reading it as "no commit" would fail open exactly under load — the same
    condition that produced the original defect. Mutation R20.
    """
    from substrate.execution.attempts.terminalization import _commit_above_base

    import substrate.execution.attempts.verified_commit_retention as m

    monkeypatch.setattr(m, "gated_subprocess_run", lambda *a, **k: None)
    assert _commit_above_base(str(tmp_path), "abc123") == "unknown", (
        "an unobservable HEAD must report at-risk, never 'nothing to protect'"
    )


def test_unobservable_head_blocks_cleanup_when_binding_is_unresolvable(
    tmp_path, monkeypatch
):
    """End-to-end companion to the above, through the REAL terminalize(): an
    unresolvable binding plus an unobservable worktree must fail closed."""
    from substrate.execution.attempts.leases import LeaseManager
    from substrate.execution.attempts.terminalization import terminalize

    plain = str(tmp_path / "plain")
    os.makedirs(f"{plain}/app")
    _git(["init", "-q", "-b", "master"], plain)
    _git(["config", "user.email", "t@t"], plain)
    _git(["config", "user.name", "t"], plain)
    open(f"{plain}/app/main.py", "w").write("base\n")
    _git(["add", "-A"], plain)
    _git(["commit", "-qm", "base"], plain)

    mgr = SandboxManager(
        repo_root=plain, worktree_base=str(tmp_path / "lu"),
        store_dir=str(tmp_path / "sbu"), max_parallel=4,
    )
    lm = LeaseManager(_store(tmp_path, "unobs"), mgr, mutation_runner=_direct_runner)
    attempt = ExecutionAttempt(
        attempt_id="ea-unobs", task_id="wp-be", status=_S.LEASED.value,
        worker_identity="cc-cli@vps-host", correlation_id="",
    )
    lease = lm.acquire(attempt=attempt, assignment=ASSIGNMENT, grant=GRANT)
    with open(os.path.join(lease.worktree_path, "app/main.py"), "a") as fh:
        fh.write("work\n")
    _git(["add", "-A"], lease.worktree_path)
    _git(["commit", "-qm", "w"], lease.worktree_path)

    import substrate.execution.attempts.verified_commit_retention as m

    monkeypatch.setattr(m, "gated_subprocess_run", lambda *a, **k: None)
    attempt.status = _S.SUCCEEDED.value
    attempt.lease_id = lease.lease_id
    result = terminalize(
        attempt=attempt, reason="succeeded", lease_manager=lm,
        run_root=str(tmp_path / "runu"), raise_on_security_failure=False,
    )
    assert not result.lease_released, (
        "an unobservable worktree with no binding must block destructive cleanup"
    )
    assert result.lease_withheld_reason, "the withhold must be explicit"
    assert os.path.isdir(lease.worktree_path), "the worktree must survive"


def test_binding_resolves_from_authoritative_records_not_env(monkeypatch):
    """The binding resolver must read persisted records, never process env."""
    from substrate.execution.attempts.terminalization import _resolve_retention_binding

    monkeypatch.setenv("UMH_W2_CANDIDATE_SHA", "ENV-SHOULD-BE-IGNORED")
    monkeypatch.setenv("UMH_W2_RUN_ID", "ENV-SHOULD-BE-IGNORED")
    attempt = SimpleNamespace(correlation_id=f"w2-{RUN}")
    repo = f"/var/lib/umh/candidates/wave2/{CAND}/targets/{RUN}/fixture"
    cand, run, _detail = _resolve_retention_binding(attempt, repo)
    assert cand == CAND, "candidate must come from the lease repo path"
    assert run == RUN, "run must come from correlation_id (w2- prefix stripped)"
    assert "ENV-SHOULD-BE-IGNORED" not in (cand + run)

    cand2, run2, _d2 = _resolve_retention_binding(SimpleNamespace(correlation_id=""), repo)
    assert (cand2, run2) == (CAND, RUN), "path-only fallback must still resolve"

    assert _resolve_retention_binding(SimpleNamespace(correlation_id=""), "/tmp/plain")[:2] == (
        "",
        "",
    ), "an unresolvable binding must return empty so the caller fails closed"


# ── 14: authorized cleanup ──────────────────────────────────────────────────


def test_authorized_cleanup_removes_refs_without_leaks(mgr, repo):
    """14: teardown deletes retention refs, and only then does the content become
    collectable."""
    b, _ = _work(mgr, repo, attempt_id="ea-be", task_id="wp-be", writes=BACKEND)
    _work(mgr, repo, attempt_id="ea-fe", task_id="wp-fe", writes=FRONTEND)

    deleted = release_trusted_refs(repo=repo, candidate=CAND, run_id=RUN)
    assert len(deleted) == 2, f"two retention refs expected, got {deleted}"
    remaining = _git(["for-each-ref", "--format=%(refname)", TRUSTED_ROOT], repo).stdout.strip()
    assert remaining == "", f"no trusted ref may leak, found {remaining}"
    assert release_trusted_refs(repo=repo, candidate=CAND, run_id=RUN) == [], "idempotent"

    _git(["reflog", "expire", "--expire=now", "--all"], repo)
    _git(["gc", "--prune=now", "-q"], repo)
    assert _git(["cat-file", "-e", f"{b}^{{commit}}"], repo).returncode != 0, (
        "after authorized release the retained content must be collectable"
    )


def test_failed_ref_listing_never_reports_a_successful_release(monkeypatch, repo):
    """14: if the LISTING fails we cannot know what to delete. Returning the refs
    deleted so far would report a release that never happened, and the caller
    would treat the graph as torn down while refs leaked."""
    import substrate.execution.attempts.verified_commit_retention as m

    real = m.gated_subprocess_run

    def _fail_listing(cmd, **kw):
        if "for-each-ref" in cmd:
            return SimpleNamespace(returncode=128, stdout="", stderr="fatal: bad ref store")
        return real(cmd, **kw)

    monkeypatch.setattr(m, "gated_subprocess_run", _fail_listing)
    with pytest.raises(RetentionError, match="refusing to report a release that did not happen"):
        m.release_trusted_refs(repo=repo, candidate=CAND, run_id=RUN)


def test_release_is_scoped_to_one_run(mgr, repo):
    """One run's teardown must never free another run's retained commits."""
    _work(mgr, repo, attempt_id="ea-be", task_id="wp-be", writes=BACKEND)
    sb = mgr.create_sandbox(candidate_id="ea-other", candidate_slug="a-other")
    open(f"{sb.worktree_path}/app/main.py", "a").write("other\n")
    _git(["add", "-A"], sb.worktree_path)
    _git(["commit", "-qm", "other"], sb.worktree_path)
    other = retain_verified_commit(
        repo=repo, worktree=sb.worktree_path, candidate=CAND,
        run_id="OTHER-RUN", task_id="wp-be", attempt_id="ea-other",
        base_commit=sb.base_commit,
    )
    mgr.cleanup_sandbox(sb.sandbox_id)

    release_trusted_refs(repo=repo, candidate=CAND, run_id=RUN)
    assert resolve_trusted_commit(
        repo=repo, candidate=CAND, run_id="OTHER-RUN", task_id="wp-be", attempt_id="ea-other"
    ) == other, "another run's retention must survive"


def test_restart_preserves_retained_commits(mgr, repo):
    """10: recovery rests on durable git state alone — no in-memory bookkeeping.
    A fresh process (fresh SandboxManager, no shared state) resolves the same
    commit from the ref."""
    sha, _ = _work(mgr, repo, attempt_id="ea-be", task_id="wp-be", writes=BACKEND)
    resolved = resolve_trusted_commit(
        repo=repo, candidate=CAND, run_id=RUN, task_id="wp-be", attempt_id="ea-be"
    )
    assert resolved == sha
    assert _git(["rev-parse", f"{trusted_ref(candidate=CAND, run_id=RUN, task_id='wp-be', attempt_id='ea-be')}^{{commit}}"], repo).stdout.strip() == sha
