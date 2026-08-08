"""Wave 2 — durable object promotion: worker-ephemeral commits become control-plane truth.

WHY THIS FILE EXISTS (invocation 40, run 20260807T234550Z-p1)
-------------------------------------------------------------
The lease is a SELF-CONTAINED repo (``make_lease_selfcontained`` copies the
fixture's objects into the lease's own ``.git``), so an isolated worker's commit
objects exist only in the lease's private object store. Every succeeded worker
attempt of the field runs 20260807T005250Z-p1 and 20260807T234550Z-p1 then failed
retention identically: ``update-ref … nonexistent object`` in the fixture repo,
the lease was withheld, and Task C blocked with "no retained commit under
refs/umh/verified" — the entire fan-in property was unreachable.

The correction: trusted control-plane code imports the attempt's complete
reachable object closure into the durable repo (``promote_attempt_objects``,
``refs/umh/promoted/<cand>/<run>/<task>/<attempt>``) BEFORE verification
settles, so the verifier proves an object that already durably exists and
retention pins that SAME object:

    VERIFIED_COMMIT_SHA == DURABLE_PROMOTED_COMMIT_SHA == RETAINED_REF_TARGET

Every test here uses REAL git repos and the REAL production functions
(``make_lease_selfcontained``, ``prepare_attempt_git_capability``) — the same
machinery the isolated worker runs against.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys

import pytest

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if REPO not in sys.path:
    sys.path.insert(0, REPO)

from substrate.execution.attempts.field_task_scope import (  # noqa: E402
    attempt_ref_name,
    prepare_attempt_git_capability,
)
from substrate.execution.attempts.verified_commit_retention import (  # noqa: E402
    RetentionError,
    list_promoted_refs,
    promote_attempt_objects,
    promoted_ref,
    release_promoted_refs,
    resolve_promoted_commit,
    retain_verified_commit,
)
from substrate.execution.attempts.worker_claude_cli import (  # noqa: E402
    make_lease_selfcontained,
)

CAND = "cand4f2b9a01"
RUN = "20260808T000000Z-p1"
TASK = "wp-promotest01"
ATTEMPT = "ea-promo000001"


def _git(cwd, *args, check=True):
    r = subprocess.run(["git", "-C", str(cwd), *args], capture_output=True, text=True)
    if check and r.returncode != 0:
        raise RuntimeError(f"git {args} in {cwd}: {r.stderr}")
    return r


def _exists(repo, sha) -> bool:
    return _git(repo, "cat-file", "-e", sha, check=False).returncode == 0


def _mk_fixture(tmp_path):
    """A real fixture repo with one base commit, in the candidate layout."""
    fixture = tmp_path / "candidates" / "wave2" / CAND / "targets" / RUN / "fixture"
    fixture.mkdir(parents=True)
    _git(fixture, "init", "-q", "-b", "main")
    _git(fixture, "config", "user.email", "t@t")
    _git(fixture, "config", "user.name", "t")
    (fixture / "app.py").write_text("base\n")
    _git(fixture, "add", "-A")
    _git(fixture, "commit", "-qm", "base")
    return fixture, _git(fixture, "rev-parse", "HEAD").stdout.strip()


def _mk_lease(fixture, base, attempt_id=ATTEMPT, name="auto-t1"):
    """A real lease: git worktree add + PRODUCTION self-containment + attempt ref."""
    lease = fixture.parent / "leases" / name
    _git(fixture, "worktree", "add", "-q", str(lease), base)
    make_lease_selfcontained(str(lease))
    prepare_attempt_git_capability(str(lease), attempt_id)
    _git(lease, "config", "user.email", "w@w")
    _git(lease, "config", "user.name", "w")
    return lease


def _worker_commit(lease, msg="worker: change", fname="app.py", content="worker change\n"):
    (lease / fname).write_text(
        (lease / fname).read_text() + content if (lease / fname).exists() else content
    )
    _git(lease, "add", "-A")
    _git(lease, "commit", "-qm", msg)
    return _git(lease, "rev-parse", "HEAD").stdout.strip()


def _promote(fixture, lease, base, attempt_id=ATTEMPT, task_id=TASK):
    return promote_attempt_objects(
        repo=str(fixture),
        worktree=str(lease),
        candidate=CAND,
        run_id=RUN,
        task_id=task_id,
        attempt_id=attempt_id,
        base_commit=base,
    )


# ─────────────────────────────────────────────────────────────────────────────
# THE DEFECT, THEN THE MECHANISM
# ─────────────────────────────────────────────────────────────────────────────
def test_worker_commit_is_attempt_local_before_promotion(tmp_path):
    """The measured invocation-40 defect: commit in lease, NOT in the fixture."""
    fixture, base = _mk_fixture(tmp_path)
    lease = _mk_lease(fixture, base)
    sha = _worker_commit(lease)
    assert _exists(lease, sha), "worker commit must exist in the lease's own store"
    assert not _exists(fixture, sha), (
        "the self-contained lease must NOT share objects with the fixture — "
        "if this resolves, the defect premise changed and this suite must be revisited"
    )
    # And retention alone (without promotion) reproduces the field failure.
    with pytest.raises(RetentionError, match="could not write trusted ref"):
        retain_verified_commit(
            repo=str(fixture),
            worktree=str(lease),
            candidate=CAND,
            run_id=RUN,
            task_id=TASK,
            attempt_id=ATTEMPT,
            base_commit=base,
        )


def test_promotion_makes_commit_durable_with_full_closure(tmp_path):
    fixture, base = _mk_fixture(tmp_path)
    lease = _mk_lease(fixture, base)
    sha = _worker_commit(lease)
    got = _promote(fixture, lease, base)
    assert got == sha
    assert _exists(fixture, sha)
    tree = _git(fixture, "rev-parse", f"{sha}^{{tree}}").stdout.strip()
    assert tree
    # Every blob in the tree is readable — complete closure, not just the commit.
    out = _git(fixture, "ls-tree", "-r", sha).stdout
    for line in [ln for ln in out.splitlines() if ln.strip()]:
        blob = line.split()[2]
        assert _exists(fixture, blob), f"blob {blob} missing — incomplete closure"
    assert (
        resolve_promoted_commit(
            repo=str(fixture), candidate=CAND, run_id=RUN, task_id=TASK, attempt_id=ATTEMPT
        )
        == sha
    )


def test_promotion_writes_only_the_promoted_namespace(tmp_path):
    """Promotion may not move branches, HEAD, or any shared authority ref."""
    fixture, base = _mk_fixture(tmp_path)
    lease = _mk_lease(fixture, base)
    before_head = _git(fixture, "rev-parse", "HEAD").stdout.strip()
    before_refs = {
        ln.split()[1]: ln.split()[0]
        for ln in _git(fixture, "show-ref").stdout.splitlines()
        if ln.strip()
    }
    _worker_commit(lease)
    _promote(fixture, lease, base)
    after_refs = {
        ln.split()[1]: ln.split()[0]
        for ln in _git(fixture, "show-ref").stdout.splitlines()
        if ln.strip()
    }
    assert _git(fixture, "rev-parse", "HEAD").stdout.strip() == before_head
    new_refs = set(after_refs) - set(before_refs)
    assert new_refs == {
        promoted_ref(candidate=CAND, run_id=RUN, task_id=TASK, attempt_id=ATTEMPT)
    }, f"promotion created unexpected refs: {new_refs}"
    for name, sha in before_refs.items():
        assert after_refs.get(name) == sha, f"promotion moved pre-existing ref {name}"


def test_promotion_is_idempotent(tmp_path):
    fixture, base = _mk_fixture(tmp_path)
    lease = _mk_lease(fixture, base)
    sha = _worker_commit(lease)
    assert _promote(fixture, lease, base) == sha
    assert _promote(fixture, lease, base) == sha  # crash-recovery re-run converges


def test_no_commit_promotes_nothing(tmp_path):
    """head == base (the injected-failure shape) is 'nothing', never an error."""
    fixture, base = _mk_fixture(tmp_path)
    lease = _mk_lease(fixture, base)
    assert _promote(fixture, lease, base) == ""
    assert list_promoted_refs(repo=str(fixture), candidate=CAND, run_id=RUN) == [], (
        "a no-commit attempt must create no promoted ref"
    )


# ─────────────────────────────────────────────────────────────────────────────
# AUTHORITY — the worker cannot pick what gets promoted
# ─────────────────────────────────────────────────────────────────────────────
def test_worker_reported_commits_are_never_an_input(tmp_path):
    """The promoted sha is derived from the attempt's own ref, not any report.

    Structural half: the function signature accepts no worker-reported commit.
    Behavioural half: the promoted sha equals the attempt-ref target even when a
    'report' would have named something else.
    """
    import inspect

    params = set(inspect.signature(promote_attempt_objects).parameters)
    assert "commits" not in params and "worker_result" not in params

    fixture, base = _mk_fixture(tmp_path)
    lease = _mk_lease(fixture, base)
    sha = _worker_commit(lease)
    assert _promote(fixture, lease, base) == sha  # derived, not reported


def test_promotion_refuses_a_repointed_head(tmp_path):
    """HEAD detached away from the attempt ref = not this attempt's work."""
    fixture, base = _mk_fixture(tmp_path)
    lease = _mk_lease(fixture, base)
    _worker_commit(lease)
    # Worker (or anything) re-points HEAD at a second commit made on a side ref.
    _git(lease, "checkout", "-q", "--detach", "HEAD")
    (lease / "side.py").write_text("side\n")
    _git(lease, "add", "-A")
    _git(lease, "commit", "-qm", "side commit off the attempt ref")
    with pytest.raises(RetentionError, match="does not equal the attempt's"):
        _promote(fixture, lease, base)


def test_promotion_refuses_missing_attempt_ref(tmp_path):
    """HEAD above base but no attempt ref → no trusted derivation → refuse.

    HEAD is detached at the commit first (so it still resolves), THEN the
    attempt ref is deleted — the exact state where a caller could be tempted to
    "just take HEAD". Taking HEAD there would promote a commit the attempt-ref
    machinery no longer vouches for.
    """
    fixture, base = _mk_fixture(tmp_path)
    lease = _mk_lease(fixture, base)
    sha = _worker_commit(lease)
    _git(lease, "checkout", "-q", "--detach", sha)
    _git(lease, "update-ref", "-d", attempt_ref_name(ATTEMPT))
    with pytest.raises(RetentionError, match="cannot derive a trusted commit"):
        _promote(fixture, lease, base)


def test_promotion_refuses_non_descendant_history(tmp_path):
    """A commit that does not descend from the authorized base is foreign."""
    fixture, base = _mk_fixture(tmp_path)
    lease = _mk_lease(fixture, base)
    ref = attempt_ref_name(ATTEMPT)
    # Rebuild the attempt ref on an orphan root — valid objects, wrong ancestry.
    _git(lease, "checkout", "-q", "--orphan", "orphanwork")
    (lease / "app.py").write_text("orphan\n")
    _git(lease, "add", "-A")
    _git(lease, "commit", "-qm", "orphan root")
    orphan = _git(lease, "rev-parse", "HEAD").stdout.strip()
    _git(lease, "update-ref", ref, orphan)
    _git(lease, "symbolic-ref", "HEAD", ref)
    with pytest.raises(RetentionError, match="does not descend from"):
        _promote(fixture, lease, base)


def test_promotion_refuses_repointing_an_existing_promoted_ref(tmp_path):
    """One attempt promotes exactly one commit — ever."""
    fixture, base = _mk_fixture(tmp_path)
    lease = _mk_lease(fixture, base)
    sha1 = _worker_commit(lease)
    assert _promote(fixture, lease, base) == sha1
    _worker_commit(lease, msg="worker: second commit", content="more\n")
    with pytest.raises(RetentionError, match="refusing to repoint"):
        _promote(fixture, lease, base)


# ─────────────────────────────────────────────────────────────────────────────
# UNREADABLE REPO — the second review CRITICAL (corrupt lease git must FAIL CLOSED)
# ─────────────────────────────────────────────────────────────────────────────
def test_packed_refs_is_created_and_in_the_readonly_barrier(tmp_path):
    """A fresh self-contained lease has no packed-refs; the barrier must CREATE
    and lock it, or a worker can write it and corrupt its own git (review
    CRITICAL). objects/info and worktrees are created-then-locked for the same
    reason — packed-refs must be too."""
    from substrate.execution.attempts.field_task_scope import git_readonly_subpaths

    fixture, base = _mk_fixture(tmp_path)
    lease = _mk_lease(fixture, base)
    assert not (lease / ".git" / "packed-refs").exists(), "premise: no packed-refs yet"
    ro = git_readonly_subpaths(str(lease))
    assert (lease / ".git" / "packed-refs").exists(), "barrier did not create packed-refs"
    assert any(p.endswith("/.git/packed-refs") for p in ro), (
        "packed-refs is not in the read-only barrier — a worker could write it"
    )


def test_promotion_fails_closed_on_unreadable_repo(tmp_path):
    """A corrupt lease git (unreadable HEAD, rc!=0) must RAISE, never return ""
    — returning "" made the poller mint a durable Proof for a lost object
    (review CRITICAL, the invocation-40 defect through a different door).

    Corrupting ``.git/HEAD`` deterministically breaks ``rev-parse HEAD`` across
    git versions (packed-refs corruption is version-dependent for a loose HEAD);
    the layer under test is promotion's reaction to an unreadable repo, whatever
    the corruption source — including a worker writing packed-refs when the
    barrier fails."""
    fixture, base = _mk_fixture(tmp_path)
    lease = _mk_lease(fixture, base)
    _worker_commit(lease)
    (lease / ".git" / "HEAD").write_text("ref: refs/heads/\x00garbage-not-a-ref\n")
    assert _git(lease, "rev-parse", "HEAD", check=False).returncode != 0, "premise: git is corrupt"
    with pytest.raises(RetentionError, match="unreadable"):
        _promote(fixture, lease, base)


def test_commondir_is_created_and_in_the_readonly_barrier(tmp_path):
    """A fresh self-contained lease has no .git/commondir; the barrier must CREATE
    it (as the inert standalone value '.') and lock it, or a worker can redirect
    where its LOCKED HEAD symref reads refs from — forging a fresh foreign commit
    that slips past even the authorship scan (review CRITICAL). An empty commondir
    is fatal to git, so the created value must be '.', not empty."""
    from substrate.execution.attempts.field_task_scope import git_readonly_subpaths

    fixture, base = _mk_fixture(tmp_path)
    lease = _mk_lease(fixture, base)
    assert not (lease / ".git" / "commondir").exists(), "premise: no commondir yet"
    ro = git_readonly_subpaths(str(lease))
    cd = lease / ".git" / "commondir"
    assert cd.exists(), "barrier did not create commondir"
    assert cd.read_text().strip() == ".", "commondir must be the inert '.' (empty is fatal to git)"
    assert any(p.endswith("/.git/commondir") for p in ro), (
        "commondir is not in the read-only barrier — a worker could redirect ref reads"
    )
    # git remains fully usable with commondir='.'
    assert _git(lease, "rev-parse", "HEAD", check=False).returncode == 0


@pytest.mark.skipif(not shutil.which("bwrap"), reason="bwrap not available on this host")
def test_real_isolated_worker_cannot_write_commondir(tmp_path):
    """The commondir forgery CRITICAL, closed at the mount: a REAL bwrap worker's
    attempt to write .git/commondir is DENIED, so it cannot redirect HEAD's
    ref-read into an evil git dir and promote a fabricated foreign commit."""
    from substrate.execution.attempts.field_task_scope import (
        git_readonly_subpaths,
        prepare_attempt_git_capability,
        readonly_binds_for_scope,
    )
    from substrate.execution.attempts.host_isolation import (
        IsolationProfile,
        build_isolated_command,
    )

    fixture, base = _mk_fixture(tmp_path)
    lease = fixture.parent / "leases" / "auto-cd"
    _git(fixture, "worktree", "add", "-q", str(lease), base)
    make_lease_selfcontained(str(lease))
    ref_dir = prepare_attempt_git_capability(str(lease), "ea-cd00000001")
    ro = readonly_binds_for_scope(["app.py"], lease_root=str(lease))
    assert any(p.endswith("/.git/commondir") for p in git_readonly_subpaths(str(lease)))
    home = lease.parent.parent / "home-cd"
    tmp = lease.parent.parent / "tmp-cd"
    home.mkdir(parents=True, exist_ok=True)
    tmp.mkdir(parents=True, exist_ok=True)
    profile = IsolationProfile(
        worktree_path=str(lease),
        worker_home=str(home),
        tmp_path=str(tmp),
        allow_network=False,
        readonly_subpaths=ro,
        writable_subpaths=[ref_dir],
        scope_enforced=True,
    )
    inner = ["bash", "-c", f"cd {lease}; echo evilgit > .git/commondir && echo WROTE_COMMONDIR"]
    r = subprocess.run(
        build_isolated_command(inner, profile), capture_output=True, text=True, timeout=60
    )
    assert "WROTE_COMMONDIR" not in r.stdout, "worker wrote commondir — barrier failed"
    assert r.returncode != 0, "commondir write was not denied"
    assert (lease / ".git" / "commondir").read_text().strip() == ".", "commondir was mutated"
    assert _git(lease, "rev-parse", "HEAD", check=False).returncode == 0


def test_promotion_requires_an_authorized_base(tmp_path):
    """An empty base disables ancestry+authorship (review MEDIUM) — refuse it.

    Measured: with base='' a fully orphan foreign-root commit was imported. The
    function must enforce its own precondition rather than trust the caller."""
    fixture, base = _mk_fixture(tmp_path)
    lease = _mk_lease(fixture, base)
    _worker_commit(lease)
    with pytest.raises(RetentionError, match="no authorized base"):
        promote_attempt_objects(
            repo=str(fixture),
            worktree=str(lease),
            candidate=CAND,
            run_id=RUN,
            task_id=TASK,
            attempt_id=ATTEMPT,
            base_commit="",
        )


def test_shallow_truncation_cannot_hide_a_foreign_commit(tmp_path):
    """A worker-written .git/shallow must not let a foreign commit slip past the
    authorship scan (review MEDIUM-2, pins the ancestry-before-authorship order).

    The worker builds real work ATOP a foreign durable commit F, then writes
    .git/shallow to truncate history so F disappears from `rev-list base..head`.
    The ancestry check (which runs FIRST) fails closed on exactly the cuts that
    hide F, so promotion RAISES either on ancestry or on authorship — never
    promotes the foreign-contaminated history."""
    fixture, base = _mk_fixture(tmp_path)
    foreign = _foreign_in_scope_commit(fixture, base)
    lease = _mk_lease(fixture, base)
    ref = attempt_ref_name(ATTEMPT)
    _git(lease, "update-ref", ref, foreign)
    _git(lease, "symbolic-ref", "HEAD", ref)
    _git(lease, "reset", "-q", "--hard", foreign)
    (lease / "app.py").write_text((lease / "app.py").read_text() + "atop foreign\n")
    _git(lease, "add", "-A")
    _git(lease, "commit", "-qm", "worker: atop foreign, then truncated")
    head = _git(lease, "rev-parse", "HEAD").stdout.strip()
    # Plant a shallow graft truncating at head — F would vanish from base..head.
    (lease / ".git" / "shallow").write_text(head + "\n")
    with pytest.raises(RetentionError, match="does not descend from|already exists in the durable"):
        _promote(fixture, lease, base)
    assert list_promoted_refs(repo=str(fixture), candidate=CAND, run_id=RUN) == []


# ─────────────────────────────────────────────────────────────────────────────
# AUTHORSHIP FORGERY — the review CRITICAL (a worker POINTS AT foreign work)
# ─────────────────────────────────────────────────────────────────────────────
def _foreign_in_scope_commit(fixture, base, fname="app.py"):
    """A commit already durable in the fixture that edits an in-scope path.

    Models a prior promoted commit, another lane's tip, or any commit the
    self-contained lease copies in — every one is resolvable inside the sandbox.
    """
    _git(fixture, "checkout", "-q", "-b", "someone-else", base)
    (fixture / fname).write_text((fixture / fname).read_text() + "foreign in-scope\n")
    _git(fixture, "add", "-A")
    _git(fixture, "commit", "-qm", "foreign: in-scope work this attempt did NOT do")
    foreign = _git(fixture, "rev-parse", "HEAD").stdout.strip()
    _git(fixture, "checkout", "-q", "main")
    return foreign


def test_promotion_refuses_a_foreign_in_scope_commit(tmp_path):
    """A worker that does ZERO work and points its ref at a pre-existing in-scope
    commit must be refused — descent-from-base is shape, not authorship."""
    fixture, base = _mk_fixture(tmp_path)
    foreign = _foreign_in_scope_commit(fixture, base)
    lease = _mk_lease(fixture, base)
    assert _exists(lease, foreign), "premise: foreign commit is visible in the self-contained lease"
    ref = attempt_ref_name(ATTEMPT)
    _git(lease, "update-ref", ref, foreign)
    _git(lease, "symbolic-ref", "HEAD", ref)
    with pytest.raises(RetentionError, match="already exists in the durable repo"):
        _promote(fixture, lease, base)
    # And nothing was promoted.
    assert list_promoted_refs(repo=str(fixture), candidate=CAND, run_id=RUN) == []


def test_promotion_refuses_worker_building_atop_a_foreign_commit(tmp_path):
    """New tip, but a foreign commit sits in its history — refused.

    The tip is genuinely new (doesn't pre-exist), so a tip-only check would pass;
    the authorship scan walks the whole base..head range and catches the foreign
    parent that pre-exists durably.
    """
    fixture, base = _mk_fixture(tmp_path)
    foreign = _foreign_in_scope_commit(fixture, base)
    lease = _mk_lease(fixture, base)
    ref = attempt_ref_name(ATTEMPT)
    _git(lease, "update-ref", ref, foreign)
    _git(lease, "symbolic-ref", "HEAD", ref)
    _git(lease, "reset", "-q", "--hard", foreign)
    (lease / "app.py").write_text((lease / "app.py").read_text() + "atop foreign\n")
    _git(lease, "add", "-A")
    _git(lease, "commit", "-qm", "worker: real work atop foreign history")
    tip = _git(lease, "rev-parse", "HEAD").stdout.strip()
    assert not _exists(fixture, tip), "premise: the tip itself is new"
    with pytest.raises(RetentionError, match="already exists in the durable repo"):
        _promote(fixture, lease, base)


def test_retry_cannot_promote_a_prior_attempts_commit(tmp_path):
    """The retry-contamination path (vector D): a rejected A1 promotes into the
    durable repo, then A2 points at A1's commit. A2 must be refused — a rejected
    attempt's promoted object cannot become the next attempt's 'verified work'.
    """
    fixture, base = _mk_fixture(tmp_path)
    lease1 = _mk_lease(fixture, base, attempt_id="ea-a1000000001", name="auto-c1")
    sha1 = _worker_commit(lease1)
    promote_attempt_objects(
        repo=str(fixture),
        worktree=str(lease1),
        candidate=CAND,
        run_id=RUN,
        task_id=TASK,
        attempt_id="ea-a1000000001",
        base_commit=base,
    )
    assert _exists(fixture, sha1), "A1's commit is now durable (it was promoted)"
    # A2: fresh lease from the (now-contaminated) fixture, points at A1's commit.
    lease2 = _mk_lease(fixture, base, attempt_id="ea-a2000000002", name="auto-c2")
    assert _exists(lease2, sha1), "premise: A2's lease copied A1's promoted commit in"
    ref2 = attempt_ref_name("ea-a2000000002")
    _git(lease2, "update-ref", ref2, sha1)
    _git(lease2, "symbolic-ref", "HEAD", ref2)
    with pytest.raises(RetentionError, match="already exists in the durable repo"):
        promote_attempt_objects(
            repo=str(fixture),
            worktree=str(lease2),
            candidate=CAND,
            run_id=RUN,
            task_id=TASK,
            attempt_id="ea-a2000000002",
            base_commit=base,
        )


def test_legitimate_work_still_promotes_after_authorship_check(tmp_path):
    """THE CONTROL — a real worker commit (new to the durable repo) still promotes."""
    fixture, base = _mk_fixture(tmp_path)
    _foreign_in_scope_commit(fixture, base)  # a foreign commit exists but is unused
    lease = _mk_lease(fixture, base)
    sha = _worker_commit(lease)
    assert _promote(fixture, lease, base) == sha


def test_promotion_reports_missing_worktree_clearly(tmp_path):
    """Finding 3: a removed lease is not misreported as CPU overload."""
    fixture, base = _mk_fixture(tmp_path)
    lease = _mk_lease(fixture, base)
    _worker_commit(lease)
    shutil.rmtree(lease)
    with pytest.raises(RetentionError, match="does not exist"):
        _promote(fixture, lease, base)


def test_loose_unreachable_objects_are_not_promoted(tmp_path):
    """fetch transfers the reachable closure only — no smuggling channel."""
    fixture, base = _mk_fixture(tmp_path)
    lease = _mk_lease(fixture, base)
    _worker_commit(lease)
    blob = subprocess.run(
        ["git", "-C", str(lease), "hash-object", "-w", "--stdin"],
        input="smuggled loose content\n",
        capture_output=True,
        text=True,
    ).stdout.strip()
    _promote(fixture, lease, base)
    assert not _exists(fixture, blob), "an unreachable loose object crossed the boundary"


# ─────────────────────────────────────────────────────────────────────────────
# DURABILITY + CRASH SHAPES
# ─────────────────────────────────────────────────────────────────────────────
def test_promoted_object_survives_lease_destruction(tmp_path):
    fixture, base = _mk_fixture(tmp_path)
    lease = _mk_lease(fixture, base)
    sha = _worker_commit(lease)
    _promote(fixture, lease, base)
    shutil.rmtree(lease)
    _git(fixture, "worktree", "prune")
    assert _exists(fixture, sha)
    # And it survives an aggressive gc, because the promoted ref reaches it.
    _git(fixture, "gc", "--prune=now", "-q")
    assert _exists(fixture, sha)


def test_lost_promoted_object_self_heals_while_lease_alive(tmp_path):
    """Durable-storage loss with the lease still present → re-promotion re-imports.

    ``rev-parse --verify <ref>^{commit}`` peels the ref, so a promoted ref whose
    object was pruned does NOT read as "already promoted" — the fetch runs again
    and restores the closure from the lease. Recovery, not silent success.
    """
    fixture, base = _mk_fixture(tmp_path)
    lease = _mk_lease(fixture, base)
    sha = _worker_commit(lease)
    _promote(fixture, lease, base)
    obj = os.path.join(str(fixture), ".git", "objects", sha[:2], sha[2:])
    assert os.path.exists(obj), "test premise: promoted commit is a loose object"
    os.remove(obj)
    assert not _exists(fixture, sha)
    assert _promote(fixture, lease, base) == sha  # self-heal
    assert _exists(fixture, sha)


def test_lost_promoted_object_after_lease_gone_is_not_reported_durable(tmp_path):
    """Object lost AND lease destroyed → nothing lies about durability.

    ``resolve_promoted_commit`` must return "" (the ref cannot peel), so no
    consumer — composition, retention, readiness — can be told the commit is
    durable when its bytes are gone and unrecoverable.
    """
    fixture, base = _mk_fixture(tmp_path)
    lease = _mk_lease(fixture, base)
    sha = _worker_commit(lease)
    _promote(fixture, lease, base)
    shutil.rmtree(lease)
    _git(fixture, "worktree", "prune")
    obj = os.path.join(str(fixture), ".git", "objects", sha[:2], sha[2:])
    os.remove(obj)
    assert (
        resolve_promoted_commit(
            repo=str(fixture), candidate=CAND, run_id=RUN, task_id=TASK, attempt_id=ATTEMPT
        )
        == ""
    )


def test_retry_attempt_promotes_into_its_own_namespace(tmp_path):
    """A retry is a new attempt: its own ref, its own promotion, no inheritance."""
    fixture, base = _mk_fixture(tmp_path)
    lease1 = _mk_lease(fixture, base, attempt_id="ea-promo000001", name="auto-a1")
    sha1 = _worker_commit(lease1)
    promote_attempt_objects(
        repo=str(fixture),
        worktree=str(lease1),
        candidate=CAND,
        run_id=RUN,
        task_id=TASK,
        attempt_id="ea-promo000001",
        base_commit=base,
    )
    lease2 = _mk_lease(fixture, base, attempt_id="ea-promo000002", name="auto-a2")
    sha2 = _worker_commit(lease2, content="retry change\n")
    promote_attempt_objects(
        repo=str(fixture),
        worktree=str(lease2),
        candidate=CAND,
        run_id=RUN,
        task_id=TASK,
        attempt_id="ea-promo000002",
        base_commit=base,
    )
    assert sha1 != sha2
    r1 = resolve_promoted_commit(
        repo=str(fixture),
        candidate=CAND,
        run_id=RUN,
        task_id=TASK,
        attempt_id="ea-promo000001",
    )
    r2 = resolve_promoted_commit(
        repo=str(fixture),
        candidate=CAND,
        run_id=RUN,
        task_id=TASK,
        attempt_id="ea-promo000002",
    )
    assert (r1, r2) == (sha1, sha2)


# ─────────────────────────────────────────────────────────────────────────────
# THE EQUALITY LAW — verified == promoted == retained
# ─────────────────────────────────────────────────────────────────────────────
def test_retention_succeeds_after_promotion_and_targets_the_same_object(tmp_path):
    fixture, base = _mk_fixture(tmp_path)
    lease = _mk_lease(fixture, base)
    sha = _worker_commit(lease)
    promoted = _promote(fixture, lease, base)
    retained = retain_verified_commit(
        repo=str(fixture),
        worktree=str(lease),
        candidate=CAND,
        run_id=RUN,
        task_id=TASK,
        attempt_id=ATTEMPT,
        base_commit=base,
    )
    # The law, asserted as one equality chain over the actual repo state:
    head = _git(lease, "rev-parse", "HEAD").stdout.strip()
    trusted = _git(
        fixture, "rev-parse", f"refs/umh/verified/{CAND}/{RUN}/{TASK}/{ATTEMPT}"
    ).stdout.strip()
    assert head == promoted == retained == trusted == sha
    # And the retained object is durable after the lease is gone.
    shutil.rmtree(lease)
    _git(fixture, "worktree", "prune")
    _git(fixture, "gc", "--prune=now", "-q")
    assert _exists(fixture, sha)


def test_retention_refuses_a_divergent_promoted_commit(tmp_path):
    """Promoted X but worktree now at Y → the two-object split is refused."""
    fixture, base = _mk_fixture(tmp_path)
    lease = _mk_lease(fixture, base)
    _worker_commit(lease)
    _promote(fixture, lease, base)
    # The worktree moves on (second commit) after promotion, before retention.
    _worker_commit(lease, msg="worker: post-promotion drift", content="drift\n")
    with pytest.raises(RetentionError, match="must be ONE object"):
        retain_verified_commit(
            repo=str(fixture),
            worktree=str(lease),
            candidate=CAND,
            run_id=RUN,
            task_id=TASK,
            attempt_id=ATTEMPT,
            base_commit=base,
        )


# ─────────────────────────────────────────────────────────────────────────────
# TEARDOWN
# ─────────────────────────────────────────────────────────────────────────────
def test_teardown_releases_promoted_refs(tmp_path):
    fixture, base = _mk_fixture(tmp_path)
    lease = _mk_lease(fixture, base)
    _worker_commit(lease)
    _promote(fixture, lease, base)
    assert len(list_promoted_refs(repo=str(fixture), candidate=CAND, run_id=RUN)) == 1
    deleted = release_promoted_refs(repo=str(fixture), candidate=CAND, run_id=RUN)
    assert len(deleted) == 1
    assert list_promoted_refs(repo=str(fixture), candidate=CAND, run_id=RUN) == []
    # Idempotent: releasing nothing is success.
    assert release_promoted_refs(repo=str(fixture), candidate=CAND, run_id=RUN) == []


def test_sweep_run_accounts_promoted_refs(tmp_path):
    """The run sweep releases promoted refs and reports them in refs_deleted."""
    from substrate.execution.attempts.run_teardown import sweep_run

    fixture, base = _mk_fixture(tmp_path)
    lease = _mk_lease(fixture, base)
    _worker_commit(lease)
    _promote(fixture, lease, base)
    run_root = str(fixture.parent)
    res = sweep_run(run_root, repo_root=str(fixture), candidate=CAND, run_id=RUN)
    assert any("promoted" in s for s in res.steps)
    assert res.ref_residue == []
    assert list_promoted_refs(repo=str(fixture), candidate=CAND, run_id=RUN) == []


# ─────────────────────────────────────────────────────────────────────────────
# POLLER INTEGRATION — promotion is on the production settle path, fail-closed
# ─────────────────────────────────────────────────────────────────────────────
def _poller_env(tmp_path, fixture, lease, monkeypatch, repo_root_override=None):
    """A real store + poller wired with a lease whose repo_root binds cand/run.

    ``repo_root_override`` points source_ref.repo_root at a NON-candidate path so
    the retention binding fails to resolve — used to exercise the fail-closed
    Finding-2 path.
    """
    from substrate.execution.attempts.poller import ControlPlanePoller
    from substrate.execution.attempts.records import ExecutionAttempt, ExecutionAttemptStatus
    from substrate.execution.attempts.store import ExecutionAttemptStore

    monkeypatch.setenv("UMH_STATE_DIR", str(tmp_path / "proofstate"))
    store = ExecutionAttemptStore(
        attempts_path=str(tmp_path / "attempts.jsonl"),
        grants_path=str(tmp_path / "grants.jsonl"),
        readiness_path=str(tmp_path / "readiness.jsonl"),
        leases_path=str(tmp_path / "leases.jsonl"),
        assignments_path=str(tmp_path / "assignments.jsonl"),
    )
    a = ExecutionAttempt(
        task_id=TASK,
        objective_id="goal-1",
        plan_record_id="opr-1",
        plan_version=1,
        execution_authorization_ref="objective_plan:opr-1:execution_authorization:v1",
        attempt_number=1,
        tenant_id="tenant-a",
        correlation_id=f"w2-{RUN}",
    )
    a, _ = store.create_attempt_idempotent(a)
    for status, updates in (
        (ExecutionAttemptStatus.READY.value, {"assignment_id": "asn-1"}),
        (ExecutionAttemptStatus.LEASED.value, {"lease_id": "l-1"}),
        (
            ExecutionAttemptStatus.DISPATCHED.value,
            {"instruction_package_hash": "ph-1", "worker_identity": "worker:cc"},
        ),
    ):
        a = store.transition_cas(
            a.attempt_id,
            status,
            expected_record_version=a.record_version,
            expected_statuses=(a.status,),
            actor="test",
            reason="walk",
            updates=updates,
        )

    lease_rec = {
        "lease_id": "l-1",
        "worktree_path": str(lease),
        "snapshot_ref": _git(fixture, "rev-parse", "HEAD").stdout.strip(),
        "source_ref": {
            "repo_root": (repo_root_override if repo_root_override is not None else str(fixture))
        },
    }

    class _Spool:
        def __init__(self, results):
            self._r = list(results)

        def drain_results(self):
            out, self._r = self._r, []
            return out

    verify_calls: list = []

    def _verify(**kw):
        verify_calls.append(kw)

        class _V:
            passed = False
            proof_id = ""
            checks = [{"ok": False, "check_id": "stub", "detail": "stub refuses"}]

        return _V()

    results = [
        {
            "attempt_id": a.attempt_id,
            "worker_result": {"status": "succeeded", "files_changed": [], "commits": []},
        }
    ]

    class _Scheduler:
        def run_scheduler_pass(self, **kw):
            class _R:
                attempts_admitted: list = []

            return _R()

    poller = ControlPlanePoller(
        store=store,
        spool=_Spool(results),
        scheduler=_Scheduler(),
        verify_fn=_verify,
        lease_lookup=lambda _lid: dict(lease_rec),
    )
    return store, poller, a, verify_calls


# ─────────────────────────────────────────────────────────────────────────────
# THE ACCEPTANCE REGRESSION — REAL isolated worker, NO worker stub
# ─────────────────────────────────────────────────────────────────────────────
def _run_real_isolated_worker(lease, attempt_id, fname, content):
    """A REAL bwrap-isolated process performs the worker's edit + commit.

    Uses the production isolation machinery end-to-end: the real
    ``IsolationProfile``, the real ``readonly_binds_for_scope`` barrier (git
    authority surfaces read-only, attempt ref dir re-opened writable), and the
    real ``build_isolated_command``. The inner process is a shell performing
    exactly what the model worker's tools do — edit a scoped file, ``git add``,
    ``git commit`` — with no model in the loop, because the subject under test
    is the isolation/durability boundary, not the model.
    """
    from substrate.execution.attempts.field_task_scope import readonly_binds_for_scope
    from substrate.execution.attempts.host_isolation import (
        IsolationProfile,
        build_isolated_command,
    )

    ref_dir = prepare_attempt_git_capability(str(lease), attempt_id)
    home = lease.parent.parent / f"home-{attempt_id}"
    tmp = lease.parent.parent / f"tmp-{attempt_id}"
    home.mkdir(parents=True, exist_ok=True)
    tmp.mkdir(parents=True, exist_ok=True)
    profile = IsolationProfile(
        worktree_path=str(lease),
        worker_home=str(home),
        tmp_path=str(tmp),
        allow_network=False,
        readonly_subpaths=readonly_binds_for_scope([fname], lease_root=str(lease)),
        writable_subpaths=[ref_dir],
        scope_enforced=True,
    )
    inner = [
        "bash",
        "-c",
        f"cd /workspace 2>/dev/null || cd {lease}; "
        f"printf '%s\\n' '{content}' >> {fname} && "
        f"git add {fname} && "
        f"git -c user.email=w@w -c user.name=w commit -qm 'worker: {fname}'",
    ]
    cmd = build_isolated_command(inner, profile)
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
    assert r.returncode == 0, f"isolated worker failed: {r.stderr[-500:]}"
    return _git(lease, "rev-parse", "HEAD").stdout.strip()


@pytest.mark.skipif(not shutil.which("bwrap"), reason="bwrap not available on this host")
def test_real_isolated_worker_cannot_write_packed_refs(tmp_path):
    """The review CRITICAL, closed at the mount: a REAL bwrap worker's attempt to
    write .git/packed-refs is DENIED, so it cannot corrupt its own git and force
    the silent-lost-commit path. The legitimate commit path still works."""
    from substrate.execution.attempts.field_task_scope import (
        git_readonly_subpaths,
        prepare_attempt_git_capability,
        readonly_binds_for_scope,
    )
    from substrate.execution.attempts.host_isolation import (
        IsolationProfile,
        build_isolated_command,
    )

    fixture, base = _mk_fixture(tmp_path)
    lease = fixture.parent / "leases" / "auto-pr"
    _git(fixture, "worktree", "add", "-q", str(lease), base)
    make_lease_selfcontained(str(lease))
    ref_dir = prepare_attempt_git_capability(str(lease), "ea-pr00000001")
    ro = readonly_binds_for_scope(["app.py"], lease_root=str(lease))
    # The barrier must include packed-refs (created-then-locked).
    assert any(p.endswith("/.git/packed-refs") for p in git_readonly_subpaths(str(lease)))
    home = lease.parent.parent / "home-pr"
    tmp = lease.parent.parent / "tmp-pr"
    home.mkdir(parents=True, exist_ok=True)
    tmp.mkdir(parents=True, exist_ok=True)
    profile = IsolationProfile(
        worktree_path=str(lease),
        worker_home=str(home),
        tmp_path=str(tmp),
        allow_network=False,
        readonly_subpaths=ro,
        writable_subpaths=[ref_dir],
        scope_enforced=True,
    )
    inner = [
        "bash",
        "-c",
        f"cd {lease}; echo 'garbage' >> .git/packed-refs && echo WROTE_PACKED_REFS",
    ]
    r = subprocess.run(
        build_isolated_command(inner, profile), capture_output=True, text=True, timeout=60
    )
    assert "WROTE_PACKED_REFS" not in r.stdout, "worker wrote packed-refs — barrier failed"
    assert r.returncode != 0, "packed-refs write was not denied"
    # And the lease git is still readable (not corrupted).
    assert _git(lease, "rev-parse", "HEAD", check=False).returncode == 0


@pytest.mark.skipif(not shutil.which("bwrap"), reason="bwrap not available on this host")
def test_real_isolated_worker_to_composition_end_to_end(tmp_path):
    """The invocation-40 acceptance chain with a REAL isolated worker, no stubs.

    real bwrap worker → commit → worker exits → PROMOTION → durable object
    resolves → retention pins it → lease destroyed + gc → ref still resolves →
    compose_predecessors CONSUMES both retained commits.
    """
    from substrate.execution.attempts.composition import compose_predecessors
    from substrate.execution.attempts.verified_commit_retention import (
        resolve_trusted_commit,
    )

    fixture, base = _mk_fixture(tmp_path)
    (fixture / "app_b.py").write_text("base b\n")
    _git(fixture, "add", "-A")
    _git(fixture, "commit", "-qm", "base: second file")
    base = _git(fixture, "rev-parse", "HEAD").stdout.strip()

    shas = {}
    for task, attempt, fname, name in (
        ("wp-laneA", "ea-real0000000a", "app.py", "auto-ra"),
        ("wp-laneB", "ea-real0000000b", "app_b.py", "auto-rb"),
    ):
        lease = fixture.parent / "leases" / name
        _git(fixture, "worktree", "add", "-q", str(lease), base)
        make_lease_selfcontained(str(lease))
        _git(lease, "config", "user.email", "w@w")
        _git(lease, "config", "user.name", "w")
        sha = _run_real_isolated_worker(lease, attempt, fname, f"change for {task}")
        assert sha != base, "the isolated worker did not commit"
        assert not _exists(fixture, sha), "premise: commit is lease-local before promotion"

        promoted = promote_attempt_objects(
            repo=str(fixture),
            worktree=str(lease),
            candidate=CAND,
            run_id=RUN,
            task_id=task,
            attempt_id=attempt,
            base_commit=base,
        )
        retained = retain_verified_commit(
            repo=str(fixture),
            worktree=str(lease),
            candidate=CAND,
            run_id=RUN,
            task_id=task,
            attempt_id=attempt,
            base_commit=base,
        )
        assert sha == promoted == retained
        shas[task] = (attempt, sha)
        # Lease cleanup — the exact step that used to destroy the only copy.
        shutil.rmtree(lease)

    _git(fixture, "worktree", "prune")
    _git(fixture, "gc", "--prune=now", "-q")

    # Retained refs still resolve after cleanup + aggressive prune.
    for task, (attempt, sha) in shas.items():
        assert (
            resolve_trusted_commit(
                repo=str(fixture),
                candidate=CAND,
                run_id=RUN,
                task_id=task,
                attempt_id=attempt,
            )
            == sha
        )
        assert _exists(fixture, sha)

    # Composition consumes the two retained commits — the fan-in property that
    # was unreachable in the field.
    result = compose_predecessors(
        repo=str(fixture),
        candidate=CAND,
        run_id=RUN,
        task_id="wp-laneC",
        attempt_id="ea-real0000000c",
        predecessor_commits={t: sha for t, (_a, sha) in shas.items()},
    )
    assert result.composed_commit, f"composition did not produce a commit: {result.steps}"
    assert result.conflict_paths == []
    assert _exists(fixture, result.composed_commit)


def test_poller_promotion_failure_fails_the_attempt_closed(tmp_path, monkeypatch):
    """No attempt ref → promotion refused → FAILED, no Proof, verify never ran."""
    fixture, base = _mk_fixture(tmp_path)
    lease = fixture.parent / "leases" / "auto-p1"
    _git(fixture, "worktree", "add", "-q", str(lease), base)
    make_lease_selfcontained(str(lease))
    store, poller, a, verify_calls = _poller_env(tmp_path, fixture, lease, monkeypatch)
    # The REAL minted attempt id gets its capability, commits, then loses its ref
    # — HEAD still resolves at the commit, so promotion cannot derive trust.
    prepare_attempt_git_capability(str(lease), a.attempt_id)
    _git(lease, "config", "user.email", "w@w")
    _git(lease, "config", "user.name", "w")
    sha = _worker_commit(lease)
    _git(lease, "checkout", "-q", "--detach", sha)
    _git(lease, "update-ref", "-d", attempt_ref_name(a.attempt_id))
    poller.run_pass(run_scheduler=False)
    row = store.get_attempt(a.attempt_id)
    assert getattr(row, "status", "") == "failed"
    assert "object promotion failed" in (getattr(row, "blocked_reason", "") or "")
    assert not getattr(row, "proof_id", "")
    assert verify_calls == [], "verification must not run for an unpromotable attempt"


def test_poller_promotes_before_verification_on_the_success_path(tmp_path, monkeypatch):
    """A healthy attempt is promoted durably BEFORE the verifier is invoked."""
    fixture, base = _mk_fixture(tmp_path)
    lease = fixture.parent / "leases" / "auto-p2"
    _git(fixture, "worktree", "add", "-q", str(lease), base)
    make_lease_selfcontained(str(lease))
    store, poller, a, verify_calls = _poller_env(tmp_path, fixture, lease, monkeypatch)
    prepare_attempt_git_capability(str(lease), a.attempt_id)
    _git(lease, "config", "user.email", "w@w")
    _git(lease, "config", "user.name", "w")
    sha = _worker_commit(lease)
    poller.run_pass(run_scheduler=False)
    # The stub verifier refuses (so the attempt fails verification), but by the
    # time it ran the object was already durable — which is the ordering law.
    assert len(verify_calls) == 1
    assert _exists(fixture, sha), "verification ran against a non-durable object"
    assert (
        resolve_promoted_commit(
            repo=str(fixture),
            candidate=CAND,
            run_id=RUN,
            task_id=TASK,
            attempt_id=a.attempt_id,
        )
        == sha
    )


def test_poller_fails_closed_when_binding_unresolved_and_commit_at_risk(tmp_path, monkeypatch):
    """Finding 2: an unresolvable candidate/run binding must NOT silently skip
    promotion and verify a lease-only commit. If a commit exists above base, the
    attempt fails closed — matching how retention handles the same condition."""
    fixture, base = _mk_fixture(tmp_path)
    # A NON-candidate repo path: _resolve_retention_binding cannot derive cand/run.
    plain = fixture.parent.parent / "plain_repo"
    plain.mkdir()
    lease = fixture.parent / "leases" / "auto-fc"
    _git(fixture, "worktree", "add", "-q", str(lease), base)
    make_lease_selfcontained(str(lease))
    store, poller, a, verify_calls = _poller_env(
        tmp_path, fixture, lease, monkeypatch, repo_root_override=str(plain)
    )
    prepare_attempt_git_capability(str(lease), a.attempt_id)
    _git(lease, "config", "user.email", "w@w")
    _git(lease, "config", "user.name", "w")
    _worker_commit(lease)  # a real commit above base → durability cannot be established
    poller.run_pass(run_scheduler=False)
    row = store.get_attempt(a.attempt_id)
    assert getattr(row, "status", "") == "failed"
    assert "binding unresolved" in (getattr(row, "blocked_reason", "") or "")
    assert not getattr(row, "proof_id", "")
    assert verify_calls == [], "an at-risk commit with no binding must not be verified"


def test_poller_without_repo_root_reaches_verification(tmp_path, monkeypatch):
    """Review MEDIUM disposition: a lease with a worktree but NO repo_root is NOT
    a promotion-governed run — it must reach verification, not fail closed.

    repo_root absent means "not a field run", not "a governed run with lost
    durability". Non-field callers (retry/trusted-base) legitimately carry
    worktree+snapshot_ref with no repo_root and depend on verification running.
    Failing here would be a false positive for a state unreachable in the field
    (a real worker lease always sets repo_root when a worktree exists)."""
    fixture, base = _mk_fixture(tmp_path)
    lease = fixture.parent / "leases" / "auto-nr"
    _git(fixture, "worktree", "add", "-q", str(lease), base)
    make_lease_selfcontained(str(lease))
    store, poller, a, verify_calls = _poller_env(
        tmp_path, fixture, lease, monkeypatch, repo_root_override=""
    )
    prepare_attempt_git_capability(str(lease), a.attempt_id)
    _git(lease, "config", "user.email", "w@w")
    _git(lease, "config", "user.name", "w")
    _worker_commit(lease)  # a real commit above base, but no repo_root binding
    poller.run_pass(run_scheduler=False)
    # Verification WAS invoked (the stub then refuses, so status is failed — but
    # via VERIFICATION, not a promotion short-circuit).
    assert len(verify_calls) == 1, "a non-field lease must reach verification"
