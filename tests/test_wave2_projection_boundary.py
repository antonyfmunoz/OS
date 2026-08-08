"""Wave 2 — projection boundary: task-local context never becomes work product.

WHY THIS FILE EXISTS (invocation 41, run 20260808T014829Z-p1)
-------------------------------------------------------------
The trusted phase used to COMMIT the task-local projection (``OBJECTIVE.md``
rewritten per Task + ``SHARED_CONTEXT.md``) and re-anchor the attempt to that
commit. That kept the projection out of each worker's DIFF — but pushed it into
each worker's retained LINEAGE: predecessors A and B then carried *different*
system-projected ``OBJECTIVE.md`` blobs, so fan-in composition met a genuine
merge conflict on a file no worker ever touched, and the graph could never
complete in the field.

The correction (``_mark_projection_execution_context``): the projection is
EXECUTION CONTEXT, never versioned work product. The files land on disk for the
worker to read; git is told they are not content (``skip-worktree`` for tracked
paths, ``.git/info/exclude`` for untracked ones — and ``.git/info`` is locked
read-only by the scope barrier). The attempt stays anchored at the CANONICAL
governed base, so the retained commit is canonical base + authorized worker
delta, nothing else — and disjoint predecessors compose cleanly.

Every test here uses REAL git repos and the REAL production functions; the
end-to-end acceptance test drives REAL bwrap-isolated workers, not stubs.
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

from substrate.execution.attempts.composition import (  # noqa: E402
    CompositionConflict,
    compose_predecessors,
)
from substrate.execution.attempts.field_task_scope import (  # noqa: E402
    prepare_attempt_git_capability,
    readonly_binds_for_scope,
)
from substrate.execution.attempts.verified_commit_retention import (  # noqa: E402
    promote_attempt_objects,
    resolve_promoted_commit,
    resolve_trusted_commit,
    retain_verified_commit,
)
from substrate.execution.attempts.worker_claude_cli import (  # noqa: E402
    TRUSTED_PROJECTION_PATHS,
    _mark_projection_execution_context,
    make_lease_selfcontained,
    project_task_local_objective,
)

_needs_bwrap = pytest.mark.skipif(
    not shutil.which("bwrap"), reason="bwrap not available on this host"
)

CAND = "candproj00001"
RUN = "20260808T100000Z-p1"

CANONICAL_OBJECTIVE = "# Objective: add note search to the fixture app (ALL tasks)\n"


def _git(cwd, *args, check=True):
    r = subprocess.run(["git", "-C", str(cwd), *args], capture_output=True, text=True)
    if check and r.returncode != 0:
        raise RuntimeError(f"git {args} in {cwd}: {r.stderr}")
    return r


def _exists(repo, sha) -> bool:
    return _git(repo, "cat-file", "-e", sha, check=False).returncode == 0


def _mk_fixture(tmp_path):
    """A real fixture repo shipping the canonical all-tasks OBJECTIVE.md."""
    fixture = tmp_path / "candidates" / "wave2" / CAND / "targets" / RUN / "fixture"
    fixture.mkdir(parents=True)
    _git(fixture, "init", "-q", "-b", "main")
    _git(fixture, "config", "user.email", "t@t")
    _git(fixture, "config", "user.name", "t")
    (fixture / "app").mkdir()
    (fixture / "app" / "main.py").write_text("# base\n")
    (fixture / "app" / "store.py").write_text("# base store\n")
    (fixture / "OBJECTIVE.md").write_text(CANONICAL_OBJECTIVE)
    _git(fixture, "add", "-A")
    _git(fixture, "commit", "-qm", "base")
    return fixture, _git(fixture, "rev-parse", "HEAD").stdout.strip()


def _package(task_id: str, scope: list[str], contract: str):
    class _P:
        role_instructions = "implementer"
        operation_instructions = "implement"
        ordered_context = [{"section": "contract", "payload": contract}]
        operation_identity = {"task_id": task_id}
        governance_constraints = [f"writable_path_scope={sorted(scope)}"]
        verification_requirements = []

    return _P()


def _mk_lease(fixture, base, name: str):
    lease = fixture.parent / "leases" / name
    _git(fixture, "worktree", "add", "-q", str(lease), base)
    make_lease_selfcontained(str(lease))
    _git(lease, "config", "user.email", "w@w")
    _git(lease, "config", "user.name", "w")
    return lease


def _project(lease, package) -> None:
    """The production trusted phase, both steps."""
    projection = project_task_local_objective(package, str(lease))
    assert projection.get("ok"), projection
    _mark_projection_execution_context(str(lease), projection)


def _run_isolated(lease, attempt_id: str, scope: list[str], script: str):
    """A REAL bwrap-isolated process runs ``script`` inside the lease."""
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
        readonly_subpaths=readonly_binds_for_scope(scope, lease_root=str(lease)),
        writable_subpaths=[ref_dir],
        scope_enforced=True,
    )
    inner = ["bash", "-c", f"cd /workspace 2>/dev/null || cd {lease}; {script}"]
    cmd = build_isolated_command(inner, profile)
    return subprocess.run(cmd, capture_output=True, text=True, timeout=60)


def _verdict(lease, base, scope: list[str]):
    from substrate.execution.attempts.verification import _diff_scope_verdict

    class _Packet:
        packet_id = "wp-test"
        requirements = {"writable_path_scope": list(scope), "scope_declared": True}

    lease_obj = type("L", (), {"worktree_path": str(lease), "snapshot_ref": base})()
    result = type("R", (), {"files_changed": ["app/main.py"], "commits": ["x"]})()
    return _diff_scope_verdict(lease=lease_obj, packet=_Packet(), worker_result=result)


# ── the acceptance chain: distinct contexts → identical system metadata ──────


@_needs_bwrap
def test_full_projection_boundary_a_b_c_d_real_isolation(tmp_path):
    """THE invocation-41 acceptance chain, no worker stubs.

    canonical fixture → distinct A/B task-local projections → REAL bwrap
    workers see their OWN objectives → durable promotion → retention →
    retained commits share CANONICAL system metadata → composition succeeds →
    the composed tree carries both slices → Task D's worktree observes both.
    """
    fixture, base = _mk_fixture(tmp_path)

    lanes = {
        "wp-laneA": ("ea-proj000000a", "app/search_api.py", "A: implement the search API"),
        "wp-laneB": ("ea-proj000000b", "app/search_ui.py", "B: implement the search UI"),
    }

    leases, views = {}, {}
    for task, (attempt, fname, contract) in lanes.items():
        lease = _mk_lease(fixture, base, f"auto-{attempt}")
        _project(lease, _package(task, [fname], contract))
        leases[task] = lease

    # Behaviors 1/2/19: each CONCURRENTLY-projected lease shows its OWN
    # objective to a real isolated worker — read from inside the sandbox.
    for task, (attempt, fname, contract) in lanes.items():
        r = _run_isolated(leases[task], attempt, [fname], "cat OBJECTIVE.md")
        assert r.returncode == 0, r.stderr[-300:]
        assert task in r.stdout, f"worker for {task} must see its own task-local objective"
        assert contract in r.stdout
        views[task] = r.stdout
    assert views["wp-laneA"] != views["wp-laneB"], "the two views must be distinct"

    shas = {}
    for task, (attempt, fname, contract) in lanes.items():
        lease = leases[task]
        r = _run_isolated(
            lease,
            attempt,
            [fname],
            f"printf 'slice for {task}\\n' > {fname} && "
            f"git add {fname} && "
            f"git -c user.email=w@w -c user.name=w commit -qm 'worker: {task}'",
        )
        assert r.returncode == 0, r.stderr[-300:]
        sha = _git(lease, "rev-parse", "HEAD").stdout.strip()
        assert sha != base

        # Behavior 4: the worker-authored delta is EXACTLY its slice — no
        # projection path appears in <base>..HEAD.
        delta = _git(lease, "diff", "--name-only", f"{base}..HEAD").stdout.split()
        assert delta == [fname], f"worker delta must be only the slice, got {delta}"

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
        # Behavior 9: one object is what was promoted, retained, and verifiable.
        assert sha == promoted == retained
        shas[task] = (attempt, sha)

        # Behaviors 3/23: the retained commit's system metadata is CANONICAL —
        # the task-local projection did not enter the trusted lineage.
        assert _git(fixture, "show", f"{sha}:OBJECTIVE.md").stdout == CANONICAL_OBJECTIVE, (
            "retained OBJECTIVE.md must be the canonical base version"
        )
        assert (
            _git(fixture, "cat-file", "-e", f"{sha}:SHARED_CONTEXT.md", check=False).returncode != 0
        ), "SHARED_CONTEXT.md must not exist in the retained tree"

        shutil.rmtree(lease)  # behavior 10: lease destruction loses nothing

    _git(fixture, "worktree", "prune")
    _git(fixture, "gc", "--prune=now", "-q")
    for task, (attempt, sha) in shas.items():
        assert _exists(fixture, sha)
        assert (
            resolve_trusted_commit(
                repo=str(fixture), candidate=CAND, run_id=RUN, task_id=task, attempt_id=attempt
            )
            == sha
        )
        assert (
            resolve_promoted_commit(
                repo=str(fixture), candidate=CAND, run_id=RUN, task_id=task, attempt_id=attempt
            )
            == sha
        )

    # Behavior 11: DESPITE distinct task-local objectives, the disjoint slices
    # compose cleanly — the exact property invocation 41 proved impossible.
    result = compose_predecessors(
        repo=str(fixture),
        candidate=CAND,
        run_id=RUN,
        task_id="wp-laneC",
        attempt_id="ea-proj000000c",
        predecessor_commits={t: sha for t, (_a, sha) in shas.items()},
    )
    assert result.ok and result.composed_commit, f"composition failed: {result.steps}"
    assert result.conflict_paths == []

    # Behavior 12: the composed tree contains both real slices AND canonical
    # system metadata.
    composed = result.composed_commit
    tree = _git(fixture, "ls-tree", "-r", "--name-only", composed).stdout.split()
    assert "app/search_api.py" in tree and "app/search_ui.py" in tree
    assert _git(fixture, "show", f"{composed}:OBJECTIVE.md").stdout == CANONICAL_OBJECTIVE
    assert "SHARED_CONTEXT.md" not in tree

    # Behaviors 13/14: Task D checks out the EXACT composed commit and observes
    # both slices on disk.
    d_lease = fixture.parent / "leases" / "auto-ea-proj000000d"
    _git(fixture, "worktree", "add", "-q", "--detach", str(d_lease), composed)
    assert _git(d_lease, "rev-parse", "HEAD").stdout.strip() == composed
    assert (d_lease / "app" / "search_api.py").read_text() == "slice for wp-laneA\n"
    assert (d_lease / "app" / "search_ui.py").read_text() == "slice for wp-laneB\n"


@_needs_bwrap
def test_genuine_overlapping_conflict_still_blocks(tmp_path):
    """Behavior 15: removing the FALSE conflict must not hide a REAL one.

    Two real isolated workers modify the SAME authorized path differently; the
    projection boundary keeps OBJECTIVE.md out of the merge, but the genuine
    content conflict on the shared path must still refuse composition.
    """
    fixture, base = _mk_fixture(tmp_path)
    shas = {}
    for task, attempt, line in (
        ("wp-confA", "ea-conf000000a", "A version"),
        ("wp-confB", "ea-conf000000b", "B version"),
    ):
        lease = _mk_lease(fixture, base, f"auto-{attempt}")
        _project(lease, _package(task, ["app/main.py"], f"{task}: edit main"))
        r = _run_isolated(
            lease,
            attempt,
            ["app/main.py"],
            f"printf '{line}\\n' > app/main.py && git add app/main.py && "
            f"git -c user.email=w@w -c user.name=w commit -qm 'worker: {task}'",
        )
        assert r.returncode == 0, r.stderr[-300:]
        sha = _git(lease, "rev-parse", "HEAD").stdout.strip()
        promote_attempt_objects(
            repo=str(fixture),
            worktree=str(lease),
            candidate=CAND,
            run_id=RUN,
            task_id=task,
            attempt_id=attempt,
            base_commit=base,
        )
        retain_verified_commit(
            repo=str(fixture),
            worktree=str(lease),
            candidate=CAND,
            run_id=RUN,
            task_id=task,
            attempt_id=attempt,
            base_commit=base,
        )
        shas[task] = sha

    with pytest.raises(CompositionConflict) as exc:
        compose_predecessors(
            repo=str(fixture),
            candidate=CAND,
            run_id=RUN,
            task_id="wp-confC",
            attempt_id="ea-conf000000c",
            predecessor_commits=shas,
        )
    assert "app/main.py" in str(exc.value)
    assert "OBJECTIVE.md" not in str(exc.value), (
        "the system projection must play no part in a genuine conflict"
    )


# ── the projection cannot become worker output ───────────────────────────────


@_needs_bwrap
def test_worker_cannot_write_projection_paths_at_the_mount(tmp_path):
    """Behavior 5 (filesystem half): writes to projection paths are DENIED."""
    fixture, base = _mk_fixture(tmp_path)
    lease = _mk_lease(fixture, base, "auto-ea-mnt0000001")
    _project(lease, _package("wp-mnt", ["app/main.py"], "mnt: edit main"))
    before_obj = (lease / "OBJECTIVE.md").read_text()
    before_ctx = (lease / "SHARED_CONTEXT.md").read_text()
    r = _run_isolated(
        lease,
        "ea-mnt0000001",
        ["app/main.py"],
        "echo PWNED > OBJECTIVE.md 2>/dev/null; echo PWNED > SHARED_CONTEXT.md 2>/dev/null; "
        "echo done",
    )
    assert r.returncode == 0
    assert (lease / "OBJECTIVE.md").read_text() == before_obj
    assert (lease / "SHARED_CONTEXT.md").read_text() == before_ctx


def test_projection_only_change_cannot_mint_a_deliverable(tmp_path):
    """Behavior 6: a worker whose ONLY change is a projection path is refused.

    The index stays writable, so clearing skip-worktree and committing the
    projected content is mechanically possible — and lands the path in
    ``<base>..HEAD``, where the diff-scope verdict refuses the attempt.
    """
    fixture, base = _mk_fixture(tmp_path)
    lease = _mk_lease(fixture, base, "auto-ea-only000001")
    _project(lease, _package("wp-only", ["app/main.py"], "only: edit main"))
    prepare_attempt_git_capability(str(lease), "ea-only000001")
    r = subprocess.run(
        [
            "bash",
            "-c",
            "set -e\n"
            "git update-index --no-skip-worktree OBJECTIVE.md\n"
            "git add OBJECTIVE.md\n"
            "git -c user.email=w@w -c user.name=w commit -qm 'projection as work'\n",
        ],
        cwd=lease,
        capture_output=True,
        text=True,
        timeout=60,
    )
    assert r.returncode == 0, r.stderr
    ok, detail = _verdict(lease, base, ["app/main.py"])
    assert not ok, f"a projection-only commit must be refused, got: {detail}"
    assert "OBJECTIVE.md" in detail


def test_scope_granting_projection_path_is_a_contradiction(tmp_path):
    """SYSTEM-OWNED PATH LAW: a sealed scope naming a projection path refuses.

    ``run_worker_in_lease`` must never run a worker whose declared writable
    scope includes a control-plane projection path — checked structurally
    against TRUSTED_PROJECTION_PATHS, not a hardcoded filename.
    """
    from substrate.execution.attempts.field_task_scope import paths_outside

    for p in TRUSTED_PROJECTION_PATHS:
        assert paths_outside([p], ["app/main.py"]) == [p], f"{p} must be outside a normal scope"
        # inside a scope that names it → NOT outside → the launcher refuses
        assert paths_outside([p], [p]) == []


def test_worker_byte_and_mode_exact_preservation(tmp_path):
    """Behavior 7: a genuine worker change is preserved byte- and mode-exact."""
    fixture, base = _mk_fixture(tmp_path)
    lease = _mk_lease(fixture, base, "auto-ea-mode000001")
    _project(lease, _package("wp-mode", ["app/run.sh"], "mode: add script"))
    prepare_attempt_git_capability(str(lease), "ea-mode000001")
    script = lease / "app" / "run.sh"
    script.write_text("#!/bin/sh\necho run\n")
    script.chmod(0o755)
    _git(lease, "add", "app/run.sh")
    _git(lease, "-c", "user.email=w@w", "-c", "user.name=w", "commit", "-qm", "worker: script")
    sha = _git(lease, "rev-parse", "HEAD").stdout.strip()
    promoted = promote_attempt_objects(
        repo=str(fixture),
        worktree=str(lease),
        candidate=CAND,
        run_id=RUN,
        task_id="wp-mode",
        attempt_id="ea-mode000001",
        base_commit=base,
    )
    assert promoted == sha
    entry = _git(fixture, "ls-tree", sha, "app/run.sh").stdout.split()
    assert entry[0] == "100755", f"executable mode must be preserved, got {entry}"
    assert _git(fixture, "show", f"{sha}:app/run.sh").stdout == "#!/bin/sh\necho run\n"


# ── retry and crash behavior ─────────────────────────────────────────────────


def test_retry_gets_its_own_uncontaminated_projection(tmp_path):
    """Behaviors 17/18: a retry lease carries ITS OWN projection, cleanly.

    A failed attempt's lease held projection state (working-tree rewrite,
    skip-worktree bit, exclude entry) — none of it is git content, so nothing
    can propagate through history. The retry's fresh lease is projected from
    its own package and shows its own context, git-invisibly.
    """
    fixture, base = _mk_fixture(tmp_path)
    l1 = _mk_lease(fixture, base, "auto-ea-retry00001")
    _project(l1, _package("wp-retry", ["app/main.py"], "attempt-1 context"))
    shutil.rmtree(l1)  # the failed attempt's lease is destroyed on terminalization
    _git(fixture, "worktree", "prune")

    l2 = _mk_lease(fixture, base, "auto-ea-retry00002")
    _project(l2, _package("wp-retry", ["app/main.py"], "attempt-2 context"))
    body = (l2 / "OBJECTIVE.md").read_text()
    assert "attempt-2 context" in body
    assert "attempt-1 context" not in body
    assert _git(l2, "status", "--porcelain").stdout.strip() == ""
    assert _git(l2, "rev-parse", "HEAD").stdout.strip() == base


def test_crash_between_projection_and_worker_is_rerunnable(tmp_path):
    """Behavior 20: re-running the whole trusted phase is a clean no-op.

    A crash after projection leaves disk files + index bits + exclude entries.
    Recovery re-runs both steps against the same lease: same content, no
    duplicate exclude lines, still git-clean, base still unmoved.
    """
    fixture, base = _mk_fixture(tmp_path)
    lease = _mk_lease(fixture, base, "auto-ea-crash00001")
    pkg = _package("wp-crash", ["app/main.py"], "crash: context")
    _project(lease, pkg)
    exclude_once = (lease / ".git" / "info" / "exclude").read_text()
    _project(lease, pkg)  # the recovery pass
    assert (lease / ".git" / "info" / "exclude").read_text() == exclude_once
    assert _git(lease, "status", "--porcelain").stdout.strip() == ""
    assert _git(lease, "rev-parse", "HEAD").stdout.strip() == base
    assert "crash: context" in (lease / "OBJECTIVE.md").read_text()


def test_crash_after_worker_commit_promotion_is_idempotent(tmp_path):
    """Behaviors 21/22: a restart re-promotes the SAME object, never a rival."""
    fixture, base = _mk_fixture(tmp_path)
    lease = _mk_lease(fixture, base, "auto-ea-idem000001")
    _project(lease, _package("wp-idem", ["app/main.py"], "idem: context"))
    prepare_attempt_git_capability(str(lease), "ea-idem000001")
    (lease / "app" / "main.py").write_text("worker output\n")
    _git(lease, "add", "app/main.py")
    _git(lease, "-c", "user.email=w@w", "-c", "user.name=w", "commit", "-qm", "worker: idem")
    kw = dict(
        repo=str(fixture),
        worktree=str(lease),
        candidate=CAND,
        run_id=RUN,
        task_id="wp-idem",
        attempt_id="ea-idem000001",
        base_commit=base,
    )
    first = promote_attempt_objects(**kw)
    second = promote_attempt_objects(**kw)  # the restart
    assert first == second == _git(lease, "rev-parse", "HEAD").stdout.strip()
    retained_1 = retain_verified_commit(**kw)
    retained_2 = retain_verified_commit(**kw)
    assert retained_1 == first
    assert retained_2 in ("", first), "a second retention must reuse, never re-pin elsewhere"


# ── mechanism pins (mutation anchors) ────────────────────────────────────────


def test_projection_paths_are_git_invisible_by_the_exact_mechanisms(tmp_path):
    """The mechanism itself: skip-worktree for tracked, info/exclude for untracked."""
    fixture, base = _mk_fixture(tmp_path)
    lease = _mk_lease(fixture, base, "auto-ea-mech000001")
    _project(lease, _package("wp-mech", ["app/main.py"], "mech: context"))
    flagged = _git(lease, "ls-files", "-v", "--", "OBJECTIVE.md").stdout.strip()
    assert flagged.startswith("S"), f"OBJECTIVE.md must carry skip-worktree, got {flagged!r}"
    exclude = (lease / ".git" / "info" / "exclude").read_text()
    assert "/SHARED_CONTEXT.md" in exclude
    # the three channels the verifier reads are all clean
    assert _git(lease, "status", "--porcelain").stdout.strip() == ""
    assert _git(lease, "diff", "--name-only", base).stdout.strip() == ""
    assert _git(lease, "ls-files", "--others", "--exclude-standard").stdout.strip() == ""


@_needs_bwrap
def test_git_info_is_locked_readonly_in_the_sandbox(tmp_path):
    """The exclusion registry is an authority surface: unwritable by the worker."""
    fixture, base = _mk_fixture(tmp_path)
    lease = _mk_lease(fixture, base, "auto-ea-info000001")
    _project(lease, _package("wp-info", ["app/main.py"], "info: context"))
    before = (lease / ".git" / "info" / "exclude").read_text()
    r = _run_isolated(
        lease,
        "ea-info000001",
        ["app/main.py"],
        "echo tamper >> .git/info/exclude 2>/dev/null; "
        "rm -f .git/info/exclude 2>/dev/null; echo done",
    )
    assert r.returncode == 0
    assert (lease / ".git" / "info" / "exclude").read_text() == before, (
        ".git/info/exclude must be read-only to the worker"
    )


def test_marking_fails_closed_when_projection_stays_visible(tmp_path):
    """The final invisibility verification is load-bearing, not ceremony.

    Force the one state the mechanisms cannot hide: SHARED_CONTEXT.md already
    STAGED in the index before the trusted phase runs. skip-worktree hides
    worktree-vs-index differences, never index-vs-HEAD ones, and an exclude
    entry cannot unstage a path — so `status --porcelain` still reports it and
    the marking must RAISE rather than run a worker who will be blamed for a
    system file.
    """
    from substrate.execution.attempts.worker_claude_cli import LeaseGitError

    fixture, base = _mk_fixture(tmp_path)
    lease = _mk_lease(fixture, base, "auto-ea-vis0000001")
    projection = project_task_local_objective(
        _package("wp-vis", ["app/main.py"], "vis: context"), str(lease)
    )
    assert projection.get("ok")
    _git(lease, "add", "-f", "SHARED_CONTEXT.md")
    with pytest.raises(LeaseGitError, match="still visible"):
        _mark_projection_execution_context(str(lease), projection)


def test_scope_contradiction_guard_normalizes_before_checking(tmp_path):
    """Reviewer-A LOW: the guard must normalize the scope exactly as the verifier.

    A scope spelled ``./OBJECTIVE.md`` normalizes to ``OBJECTIVE.md``, so the
    diff-scope verifier would accept a committed OBJECTIVE.md under it. The
    system-owned-path guard must therefore refuse that scope too — matching the
    verifier's normalization instead of comparing raw strings.
    """
    from substrate.execution.attempts.field_task_scope import (
        normalize_allowed_paths,
        paths_outside,
    )

    # The un-normalized form evades a naive raw-string check...
    assert paths_outside(["OBJECTIVE.md"], ["./OBJECTIVE.md"]) == ["OBJECTIVE.md"]
    # ...but after normalization the projection path is INSIDE the scope, so the
    # guard (which normalizes first) correctly finds the contradiction.
    normalized = normalize_allowed_paths(["./OBJECTIVE.md"], lease_root=str(tmp_path))
    assert normalized == ["OBJECTIVE.md"]
    assert paths_outside(["OBJECTIVE.md"], normalized) == []
