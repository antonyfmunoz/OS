"""Wave 2 — the lease is a self-contained git repo under isolation (eighth layer).

``git worktree add`` gives the lease a ``.git`` FILE pointing at
``<fixture>/.git/worktrees/<id>`` (objects in ``<fixture>/.git``) — both OUTSIDE
the lease dir. The worker runs under bwrap, which binds ONLY the lease dir, so
inside the sandbox the gitdir target does not exist, git fails, and the worker's
commit is orphaned from the fixture base → ``git diff base..HEAD`` is empty →
files=0 on every attempt (field run 20260725T220643Z). ``make_lease_selfcontained``
absorbs the external gitdir into a real ``.git`` directory inside the lease so the
worker can commit and the runner's diff-capture sees the change.
"""

from __future__ import annotations

import os
import subprocess
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if REPO not in sys.path:
    sys.path.insert(0, REPO)

import pytest

from substrate.execution.attempts.worker_claude_cli import (
    LeaseGitError,
    _capture_git,
    make_lease_selfcontained,
)


@pytest.fixture(autouse=True)
def _no_cpu_gate(monkeypatch):
    """These tests exercise real git through the CPU-gated wrappers. Under host
    load the gate returns None and make_lease_selfcontained correctly fail-closes
    (LeaseGitError) — correct production behavior, but it makes the TEST flaky.
    Raise the gate ceiling so the deterministic git operations always run; the
    fail-closed path itself is covered by test_wave2_worktree_sandbox_cpu_gate."""
    import substrate.execution.cpu_gate as gate

    monkeypatch.setattr(gate, "_LOAD_CEILING_PER_CORE", 1_000_000.0, raising=False)
    monkeypatch.setattr(gate, "_CRITICAL_CEILING_PER_CORE", 1_000_000.0, raising=False)


def _git(args, cwd):
    return subprocess.run(args, cwd=cwd, capture_output=True, text=True)


def _fixture_repo(tmp_path):
    base = tmp_path / "fixture"
    base.mkdir()
    for a in (
        ["init", "-q", "-b", "main"],
        ["config", "user.email", "t@e"],
        ["config", "user.name", "t"],
    ):
        _git(["git", *a], str(base))
    (base / "app").mkdir()
    (base / "app" / "main.py").write_text("x = 1\n")
    _git(["git", "add", "-A"], str(base))
    _git(["git", "commit", "-q", "-m", "base"], str(base))
    base_commit = _git(["git", "rev-parse", "HEAD"], str(base)).stdout.strip()
    return str(base), base_commit


def _linked_worktree(base, tmp_path):
    lease = str(tmp_path / "lease")
    _git(["git", "worktree", "add", "-b", "attempt-x", lease], base)
    return lease


def test_worktree_git_is_a_pointer_file_before_fix(tmp_path):
    base, _ = _fixture_repo(tmp_path)
    lease = _linked_worktree(base, tmp_path)
    # This is the field precondition: .git is a FILE pointing outside the lease.
    assert os.path.isfile(os.path.join(lease, ".git"))
    assert not os.path.isdir(os.path.join(lease, ".git"))


def test_selfcontained_makes_git_a_real_dir_preserving_base(tmp_path):
    base, base_commit = _fixture_repo(tmp_path)
    lease = _linked_worktree(base, tmp_path)
    make_lease_selfcontained(lease)
    assert os.path.isdir(os.path.join(lease, ".git")), ".git must become a real directory"
    head = _git(["git", "rev-parse", "HEAD"], lease).stdout.strip()
    assert head == base_commit, "base-commit ancestry must be preserved"


def test_worker_commit_is_visible_to_diff_capture_after_fix(tmp_path):
    """The end-to-end symptom: after self-containment, a commit the worker makes
    IS captured by the runner's base..HEAD diff (previously files=[])."""
    base, base_commit = _fixture_repo(tmp_path)
    lease = _linked_worktree(base, tmp_path)
    make_lease_selfcontained(lease)
    # Simulate the worker's change + commit inside the (now standalone) lease.
    (os.path.join(lease, "app", "search.py"))
    with open(os.path.join(lease, "app", "search.py"), "w") as fh:
        fh.write("def search(q):\n    return []\n")
    _git(["git", "add", "-A"], lease)
    rc = _git(["git", "commit", "-q", "-m", "add search"], lease).returncode
    assert rc == 0, "worker must be able to commit in a self-contained lease"

    files, commits, diff = _capture_git(lease, base_commit)
    assert files == ["app/search.py"], "diff-capture must see the worker's file change"
    assert commits, "diff-capture must see the worker's commit"
    assert diff.strip(), "diff must be non-empty"


def test_idempotent_on_already_standalone(tmp_path):
    base, base_commit = _fixture_repo(tmp_path)
    lease = _linked_worktree(base, tmp_path)
    make_lease_selfcontained(lease)
    # Second call is a no-op (already a dir), must not raise.
    make_lease_selfcontained(lease)
    assert _git(["git", "rev-parse", "HEAD"], lease).stdout.strip() == base_commit


def test_missing_git_raises(tmp_path):
    empty = tmp_path / "nogit"
    empty.mkdir()
    with pytest.raises(LeaseGitError):
        make_lease_selfcontained(str(empty))
