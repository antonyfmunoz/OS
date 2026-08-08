"""Wave 2 — the SHIPPED path, proven end to end (findings F-1, F-2, F-3, F-4).

Independent review found the hard write barrier mechanically correct and
mechanically UNREACHABLE:

- **F-1** the barrier made ``.git`` read-only, so ``git add`` failed with
  ``Unable to create '.git/index.lock': Read-only file system`` (rc=128) and no
  worker could ever produce a commit;
- **F-2** the runner rebuilt a 4-attribute stand-in package on the far side of
  the spool, so the sealed ``writable_path_scope`` never crossed the transport
  and the launcher's fail-closed guard refused **every** real dispatch;
- **F-3** the task-local projection wrote ``OBJECTIVE.md`` + ``SHARED_CONTEXT.md``
  after the attempt's base commit was fixed, so those SYSTEM files landed inside
  ``<base>..HEAD`` and were rejected as out-of-scope worker output;
- **F-4** the tests fed the launcher a package shape production never builds and
  never ran a real ``git commit``, so none of the above was visible.

Every test here drives production code. The ONLY substitution is the model CLI
binary itself, replaced by a shell script that performs real file and git
operations — because the real CLI would cost quota and produce nondeterministic
output. Git, bwrap, the spool, the envelope signing, the package reconstruction
and the artifact capture are all the shipped implementations.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from substrate.execution.attempts import worker_claude_cli as W
from substrate.execution.attempts.field_task_scope import (
    ScopeResolutionError,
    attempt_ref_name,
    git_readonly_subpaths,
    prepare_attempt_git_capability,
    readonly_binds_for_scope,
)
from substrate.execution.attempts.spool import DispatchEnvelope, DispatchSpool

_needs_bwrap = pytest.mark.skipif(
    shutil.which("bwrap") is None, reason="bubblewrap not available on this host"
)

BACKEND_SCOPE = ["app/main.py", "tests/test_search_api.py"]
FRONTEND_SCOPE = ["app/static", "tests/test_ui_search.py"]


def _runner_module():
    """Import ``scripts/wave2_attempt_runner.py`` as a module.

    The runner is a script, not a package member, so tests load it by path. This
    is deliberate: the F-2 boundary lives in the runner, and a test that cannot
    reach the runner's real code can only reimplement it.
    """
    import importlib.util

    path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "scripts",
        "wave2_attempt_runner.py",
    )
    spec = importlib.util.spec_from_file_location("wave2_attempt_runner_under_test", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _git(cwd: str, *args: str) -> subprocess.CompletedProcess:
    return subprocess.run(["git", *args], cwd=cwd, capture_output=True, text=True, timeout=60)


def _build_fixture_lease(root: str) -> tuple[str, str]:
    """A REAL git fixture plus a REAL linked worktree lease. Returns (lease, base)."""
    repo = os.path.join(root, "fixture")
    os.makedirs(os.path.join(repo, "app", "static"))
    os.makedirs(os.path.join(repo, "tests"))
    files = {
        "app/main.py": "# backend\n",
        "app/store.py": "# backend store\n",
        "app/static/app.js": "// frontend\n",
        "tests/test_search_api.py": "# backend test\n",
        "tests/test_ui_search.py": "# frontend test\n",
        "OBJECTIVE.md": "# ALL TASKS\nA, B, C and D contracts live here.\n",
    }
    for rel, body in files.items():
        path = os.path.join(repo, rel)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(body)
    _git(repo, "init", "-q", "-b", "main")
    _git(repo, "config", "user.email", "fixture@umh.local")
    _git(repo, "config", "user.name", "fixture")
    _git(repo, "add", "-A")
    _git(repo, "commit", "-qm", "fixture base")
    base = _git(repo, "rev-parse", "HEAD").stdout.strip()
    lease = os.path.join(root, "lease")
    _git(repo, "worktree", "add", "-q", "-b", "attempt-branch", lease, "HEAD")
    W.make_lease_selfcontained(lease)
    return lease, base


def _canonical_package(scope: list[str], *, task_id: str = "wp-backend"):
    """A package with the SHIPPED attribute set (what the runner reconstructs)."""

    class _Package:
        role_instructions = "implementer"
        operation_instructions = "implement the slice"
        ordered_context = [{"section": "contract", "payload": "the task contract"}]
        operation_identity = {"task_id": task_id}
        governance_constraints = [f"writable_path_scope={sorted(scope)}"]
        verification_requirements = ["pytest green"]

    return _Package()


def _prepare_like_production(lease: str, base: str, package, attempt_id: str = "ea-1") -> str:
    """Run the TRUSTED phase exactly as ``run_worker_in_lease`` does.

    Returns the attempt's base commit — UNCHANGED since the invocation-41
    correction: the projection is execution context (skip-worktree /
    info-exclude), never a commit, so the attempt stays anchored at the
    canonical base. Used by tests that need to observe git state as it stands
    when the WORKER starts — i.e. after the system's own authorized writes, so
    those are never mistaken for an escape. Calling it twice is harmless: both
    steps are idempotent.
    """
    projection = W.project_task_local_objective(package, lease)
    assert projection.get("ok"), projection
    W._mark_projection_execution_context(lease, projection)
    W.prepare_attempt_git_capability(lease, attempt_id)
    return base


def _run_worker(lease: str, base: str, package, script: str, attempt_id: str = "ea-1"):
    """Drive the REAL run_worker_in_lease; only the CLI binary is a stand-in."""
    cli = os.path.join(lease, ".git", "stand-in-cli")
    with open(cli, "w", encoding="utf-8") as fh:
        fh.write("#!/bin/bash\n" + script + "\n")
    os.chmod(cli, 0o755)

    class _Lease:
        worktree_path = lease
        snapshot_ref = base

    run_root = tempfile.mkdtemp(prefix="runroot_")
    original = W._resolve_cli_path
    W._resolve_cli_path = lambda: cli
    try:
        return W.run_worker_in_lease(
            package=package,
            lease=_Lease(),
            timeout=180,
            max_turns=5,
            attempt_id=attempt_id,
            run_root=run_root,
        )
    finally:
        W._resolve_cli_path = original


COMMIT = 'git -c user.email=w@w -c user.name=worker commit -q -m "{msg}"'


# ── F-1: the worker can stage and commit its authorized files ────────────────


@_needs_bwrap
def test_1_backend_worker_edits_stages_and_commits_its_own_files():
    """Proof 1 + 3. The whole point of F-1: an authorized worker must succeed."""
    root = tempfile.mkdtemp()
    lease, base = _build_fixture_lease(root)
    result = _run_worker(
        lease,
        base,
        _canonical_package(BACKEND_SCOPE),
        'echo "def search(): pass" >> app/main.py\n'
        'echo "def test_search(): pass" >> tests/test_search_api.py\n'
        "git add app/main.py tests/test_search_api.py\n" + COMMIT.format(msg="backend slice"),
    )
    assert result.ok, f"authorized backend worker must succeed, got: {result.error}"
    assert result.commits, "an authorized worker must produce a real commit"
    assert sorted(result.files_changed) == sorted(BACKEND_SCOPE)


@_needs_bwrap
def test_2_frontend_worker_edits_only_frontend_authorized_files():
    """Proof 2. The other lane, with a disjoint scope, on the same fixture."""
    root = tempfile.mkdtemp()
    lease, base = _build_fixture_lease(root)
    result = _run_worker(
        lease,
        base,
        _canonical_package(FRONTEND_SCOPE, task_id="wp-frontend"),
        'echo "// search box" >> app/static/app.js\n'
        'echo "# ui test" >> tests/test_ui_search.py\n'
        "git add app/static/app.js tests/test_ui_search.py\n" + COMMIT.format(msg="frontend slice"),
    )
    assert result.ok, f"authorized frontend worker must succeed, got: {result.error}"
    assert result.commits
    assert "app/main.py" not in result.files_changed


@_needs_bwrap
def test_3_forbidden_file_cannot_be_edited_staged_or_committed():
    """Proof 4. The barrier still holds now that commits are possible."""
    root = tempfile.mkdtemp()
    lease, base = _build_fixture_lease(root)
    before = open(os.path.join(lease, "app", "store.py"), "rb").read()
    result = _run_worker(
        lease,
        base,
        _canonical_package(BACKEND_SCOPE),
        'echo "PWNED" >> app/store.py 2>/dev/null || echo denied\n'
        'echo "ok" >> app/main.py\n'
        "git add -A\n" + COMMIT.format(msg="attempted"),
    )
    after = open(os.path.join(lease, "app", "store.py"), "rb").read()
    assert after == before, "a forbidden file must be byte-identical after the attempt"
    assert "app/store.py" not in (result.files_changed or [])


@_needs_bwrap
@pytest.mark.parametrize(
    ("label", "script"),
    [
        ("hook_install", 'echo "#!/bin/sh" > .git/hooks/pre-commit'),
        ("hooks_dir_replace", "rm -rf .git/hooks"),
        ("config_write", "git config core.hooksPath /tmp/evil"),
        ("config_rename_over", "echo x > /tmp/c && mv /tmp/c .git/config"),
        ("unrelated_ref", "git update-ref refs/heads/main HEAD"),
        ("loose_ref_create", "echo 0000 > .git/refs/heads/evil"),
        ("packed_refs_rewrite", "echo x > .git/packed-refs"),
        ("head_repoint", 'echo "ref: refs/heads/main" > .git/HEAD'),
        ("refs_tree_replace", "rm -rf .git/refs"),
        (
            "sibling_attempt_ref",
            "mkdir -p .git/refs/attempt/other && echo x > .git/refs/attempt/other/work",
        ),
    ],
)
def test_4_git_authority_surfaces_cannot_be_modified(label, script):
    """Proof 5 + adversarial set. Hooks, config, refs and other attempts' refs.

    Each vector must fail and leave the protected state byte-identical. These
    are the surfaces that make a "writable .git" dangerous — the directive
    permits the broad bind ONLY because each one is independently proven safe.
    """
    root = tempfile.mkdtemp()
    lease, base = _build_fixture_lease(root)
    git_dir = os.path.join(lease, ".git")
    # Snapshot AFTER the trusted phase, not before. The trusted phase
    # legitimately repoints .git/HEAD at this attempt's private ref (that is what
    # gives the worker a writable ref at all), so a before/after comparison
    # spanning it would flag the system's own authorized write as an escape. What
    # must hold is that the WORKER changes nothing.
    prepared = _prepare_like_production(lease, base, _canonical_package(BACKEND_SCOPE))
    guarded = {
        rel: open(os.path.join(git_dir, rel), "rb").read()
        for rel in ("config", "HEAD")
        if os.path.isfile(os.path.join(git_dir, rel))
    }
    _run_worker(lease, prepared, _canonical_package(BACKEND_SCOPE), script)
    for rel, before in guarded.items():
        p = os.path.join(git_dir, rel)
        assert os.path.exists(p), f"{label}: .git/{rel} must not be deleted"
        assert open(p, "rb").read() == before, (
            f"{label}: .git/{rel} must be byte-identical after the WORKER phase"
        )
    assert not os.path.exists(os.path.join(git_dir, "hooks", "pre-commit")), (
        f"{label}: a git hook was installed — that is arbitrary code execution"
    )
    assert not os.path.exists(os.path.join(git_dir, "refs", "heads", "evil"))
    assert not os.path.exists(os.path.join(git_dir, "refs", "attempt", "other"))


# ── F-3: trusted post-commit writes are not worker output ────────────────────


@_needs_bwrap
def test_5_trusted_projection_is_not_attributed_to_the_worker():
    """Proof 9 + 10. The projection must not appear in the worker's diff.

    Before the fix this was the failure even when the worker wrote NOTHING:
    ``M OBJECTIVE.md`` + ``?? SHARED_CONTEXT.md`` sat inside <base>..HEAD.

    The launcher performs the trusted phase itself — this test must NOT do it
    first, or a mutant that removes the launcher's own commit survives (m11/m12).
    """
    root = tempfile.mkdtemp()
    lease, base = _build_fixture_lease(root)
    result = _run_worker(
        lease,
        base,
        _canonical_package(BACKEND_SCOPE),
        'echo "x = 1" >> app/main.py\ngit add app/main.py\n' + COMMIT.format(msg="scoped"),
    )
    assert result.ok, result.error
    assert "OBJECTIVE.md" not in result.files_changed, (
        "the trusted projection must not be attributed to the worker (F-3)"
    )
    assert "SHARED_CONTEXT.md" not in result.files_changed
    # ...and it really did happen: the lease holds the task-local objective.
    body = open(os.path.join(lease, "OBJECTIVE.md"), encoding="utf-8").read()
    assert "# Your Task" in body, "the task-local projection must be in effect"
    assert os.path.exists(os.path.join(lease, "SHARED_CONTEXT.md"))
    # THE F-3 ASSERTION (invocation-41 form): the projection must be
    # git-INVISIBLE — on disk for the worker, but absent from `git status`, so
    # nothing uncommitted is attributed to the worker and the verifier's
    # diff_scope stays clean.
    assert _git(lease, "status", "--porcelain").stdout.strip() == "", (
        "the trusted phase must make its writes git-invisible — anything visible "
        "is attributed to the worker and fails diff_scope (F-3)"
    )
    # ...and the invocation-41 assertion: the projection must NOT be a commit in
    # the attempt's lineage. A committed projection diverges per Task and makes
    # every fan-in composition conflict on OBJECTIVE.md (field run
    # 20260808T014829Z-p1). The worker's history above base carries ONLY the
    # worker's own commit.
    log = _git(lease, "log", "--oneline").stdout
    assert "trusted:" not in log, (
        "the projection must never enter git history — a committed projection "
        "poisons every retained predecessor with a divergent OBJECTIVE.md"
    )
    lineage_files = _git(lease, "diff", "--name-only", f"{base}..HEAD").stdout.split()
    assert "OBJECTIVE.md" not in lineage_files and "SHARED_CONTEXT.md" not in lineage_files, (
        f"projection paths leaked into the attempt lineage: {lineage_files}"
    )


@_needs_bwrap
def test_6_zero_write_lane_produces_an_empty_worker_diff():
    """Proof 12 + 13. The verifier lane writes nothing — including no projection.

    This is the exact case F-3 broke: with the worker writing NOTHING, the
    projection alone produced `M OBJECTIVE.md` + `?? SHARED_CONTEXT.md`, so a
    correct zero-write verifier failed its own scope check.
    """
    root = tempfile.mkdtemp()
    lease, base = _build_fixture_lease(root)
    result = _run_worker(lease, base, _canonical_package([], task_id="wp-verify"), "echo noop")
    assert result.files_changed == [], (
        f"a zero-write lane must produce an empty diff, got {result.files_changed}"
    )
    assert _git(lease, "status", "--porcelain").stdout.strip() == "", (
        "a zero-write lane must leave NOTHING uncommitted in the tree"
    )
    assert not result.commits, "a zero-write lane must produce no worker commit"


@_needs_bwrap
def test_7_worker_cannot_write_the_projection_paths():
    """Proof 10 + adversarial. The worker must not be able to rewrite OBJECTIVE.md."""
    root = tempfile.mkdtemp()
    lease, base = _build_fixture_lease(root)
    _run_worker(
        lease,
        base,
        _canonical_package(BACKEND_SCOPE),
        'echo "PWNED OBJECTIVE" > OBJECTIVE.md 2>/dev/null || echo denied\n'
        'echo "PWNED SHARED" > SHARED_CONTEXT.md 2>/dev/null || echo denied\n',
    )
    assert "PWNED" not in open(os.path.join(lease, "OBJECTIVE.md"), encoding="utf-8").read()
    assert "PWNED" not in open(os.path.join(lease, "SHARED_CONTEXT.md"), encoding="utf-8").read()


# ── F-2: governance survives the real transport ──────────────────────────────


def _spool_roundtrip(tmp_path, **overrides):
    """Enqueue through the REAL spool and claim it back."""
    spool = DispatchSpool(str(tmp_path), "secret-under-test")
    fields = dict(
        dispatch_id="d-1",
        attempt_id="ea-1",
        task_id="wp-backend",
        authorization_ref="grant-1",
        package_hash="ph-1",
        lease_id="lease-1",
        worktree_path="/tmp/lease",
        base_commit="abc123",
        nonce=os.urandom(8).hex(),
        sequence=1,
        governance_constraints=[f"writable_path_scope={sorted(BACKEND_SCOPE)}"],
        role_instructions="implementer",
        operation_instructions="implement",
        ordered_context=[{"section": "contract", "payload": "x"}],
        operation_identity={"task_id": "wp-backend"},
        verification_requirements=["pytest"],
    )
    fields.update(overrides)
    spool.enqueue(DispatchEnvelope(**fields))
    return spool, spool.claim_next()


def test_8_governance_constraints_survive_the_spool(tmp_path):
    """Proof 6. The scope must cross the transport intact."""
    _, claimed = _spool_roundtrip(tmp_path)
    assert claimed is not None, "a well-formed envelope must be claimable"
    _, envelope = claimed
    assert envelope.governance_constraints == [f"writable_path_scope={sorted(BACKEND_SCOPE)}"]


def test_9_runner_package_reconstruction_preserves_the_sealed_scope(tmp_path):
    """Proof 6 + 11. What the runner rebuilds must resolve to the SAME scope.

    Drives the RUNNER'S OWN ``package_from_envelope``. An earlier version of this
    test rebuilt that shape inline and therefore could not see a mutation in the
    runner — mutants m05/m06 (the original F-2 defect, reintroduced) survived it.
    A test that reimplements the code under test proves only that the test works.
    """
    _, claimed = _spool_roundtrip(tmp_path)
    _, envelope = claimed
    package = _runner_module().package_from_envelope(envelope)
    assert W._sealed_writable_scope(package) == sorted(BACKEND_SCOPE)
    assert package.operation_identity == {"task_id": "wp-backend"}
    assert package.ordered_context == [{"section": "contract", "payload": "x"}]


def test_9b_control_plane_puts_the_sealed_scope_on_the_envelope():
    """Proof 6. The DISPATCH side of the same boundary.

    Drives the control plane's real ``governance_envelope_fields``: the sealed
    package's scope must reach the envelope. Without this, the runner could
    reconstruct perfectly and still receive nothing (mutant m06).
    """
    from substrate.execution.attempts.field_control_plane import governance_envelope_fields

    fields = governance_envelope_fields(_canonical_package(BACKEND_SCOPE))
    assert fields["governance_constraints"] == [f"writable_path_scope={sorted(BACKEND_SCOPE)}"], (
        "the control plane must carry the sealed scope onto the envelope"
    )
    assert fields["operation_identity"] == {"task_id": "wp-backend"}


def test_9c_dispatch_to_launcher_round_trip_preserves_authority(tmp_path):
    """The two halves joined: package -> envelope -> spool -> runner -> launcher.

    This is the whole of F-2 in one assertion chain, using only shipped code at
    every hop.
    """
    from substrate.execution.attempts.field_control_plane import governance_envelope_fields

    spool = DispatchSpool(str(tmp_path), "secret-under-test")
    spool.enqueue(
        DispatchEnvelope(
            dispatch_id="d-1",
            attempt_id="ea-1",
            task_id="wp-backend",
            nonce=os.urandom(8).hex(),
            sequence=1,
            **governance_envelope_fields(_canonical_package(BACKEND_SCOPE)),
        )
    )
    claimed = spool.claim_next()
    assert claimed is not None, "the dispatch built by the control plane must be claimable"
    _, envelope = claimed
    package = _runner_module().package_from_envelope(envelope)
    assert W._sealed_writable_scope(package) == sorted(BACKEND_SCOPE)


@pytest.mark.parametrize(
    ("label", "constraints"),
    [
        ("missing", []),
        ("unparseable", ["writable_path_scope=<<broken>>"]),
        ("bare_string", ["writable_path_scope='app/main.py'"]),
    ],
)
def test_10_unusable_governance_fails_closed_at_the_transport(tmp_path, label, constraints):
    """Proof 7. Missing or malformed scope must never be delivered."""
    _, claimed = _spool_roundtrip(tmp_path, governance_constraints=constraints)
    assert claimed is None, f"{label}: an unenforceable envelope must not be delivered"
    quarantined = os.listdir(os.path.join(str(tmp_path), "quarantine"))
    assert quarantined, f"{label}: the envelope must be quarantined, not dropped"


def test_11_widened_scope_in_transit_is_rejected_by_the_signature(tmp_path):
    """Proof 8. Worker-reachable data cannot widen the authority."""
    spool = DispatchSpool(str(tmp_path), "secret-under-test")
    spool.enqueue(
        DispatchEnvelope(
            dispatch_id="d-1",
            attempt_id="ea-1",
            task_id="wp-backend",
            nonce=os.urandom(8).hex(),
            sequence=1,
            governance_constraints=[f"writable_path_scope={sorted(BACKEND_SCOPE)}"],
        )
    )
    inbox = os.path.join(str(tmp_path), "inbox")
    name = sorted(os.listdir(inbox))[0]
    path = os.path.join(inbox, name)
    with open(path, encoding="utf-8") as fh:
        record = json.load(fh)
    record["envelope"]["governance_constraints"] = ["writable_path_scope=['app', 'tests', '.git']"]
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(record, fh)
    assert spool.claim_next() is None, "a widened scope must fail the signature check"


def test_12_empty_scope_is_a_valid_zero_write_policy(tmp_path):
    """An explicit empty scope is the verifier lane — valid, not 'missing'."""
    _, claimed = _spool_roundtrip(tmp_path, governance_constraints=["writable_path_scope=[]"])
    assert claimed is not None, "the zero-write lane must remain dispatchable"


# ── canonical authority: one source for execution and verification ───────────


def test_13_execution_and_verification_read_the_same_scope_declaration():
    """Proof 11. The barrier and the verifier must not derive scope separately."""
    root = tempfile.mkdtemp()
    os.makedirs(os.path.join(root, "app"))
    os.makedirs(os.path.join(root, ".git", "hooks"))
    for rel in ("app/main.py", "app/store.py"):
        with open(os.path.join(root, rel), "w", encoding="utf-8") as fh:
            fh.write("x")
    with open(os.path.join(root, ".git", "config"), "w", encoding="utf-8") as fh:
        fh.write("[core]\n")

    package = _canonical_package(["app/main.py"])
    execution_scope = W._sealed_writable_scope(package)
    binds = readonly_binds_for_scope(execution_scope, lease_root=root)
    rel = {os.path.relpath(b, root) for b in binds}
    assert "app/store.py" in rel
    assert "app/main.py" not in rel


def test_14_git_authority_list_never_includes_git_wholesale():
    """The regression that F-1 was: `.git` itself must stay bindable."""
    root = tempfile.mkdtemp()
    os.makedirs(os.path.join(root, ".git", "hooks"))
    with open(os.path.join(root, ".git", "config"), "w", encoding="utf-8") as fh:
        fh.write("[core]\n")
    subs = {os.path.relpath(p, root) for p in git_readonly_subpaths(root)}
    assert ".git/hooks" in subs and ".git/config" in subs
    assert ".git" not in subs, "locking .git wholesale is what broke every commit"


def test_15_attempt_ref_binds_commit_identity_to_the_attempt():
    """Proof: commit identity is bound to the exact Attempt by construction."""
    assert attempt_ref_name("ea-abc") == "refs/attempt/ea-abc/work"
    for bad in ("", "   ", "a/b", ".", ".."):
        with pytest.raises(ScopeResolutionError):
            attempt_ref_name(bad)


def test_16_git_capability_fails_closed_without_a_git_directory():
    """A lease that cannot get a private ref must abort, never run open."""
    root = tempfile.mkdtemp()
    with pytest.raises(ScopeResolutionError):
        prepare_attempt_git_capability(root, "ea-1")


def test_17_trusted_projection_paths_are_declared_and_git_invisible():
    """The trusted phase must OWN the projection paths as EXECUTION CONTEXT.

    ``TRUSTED_PROJECTION_PATHS`` is what ``_mark_projection_execution_context``
    hides from git. Emptying it (mutant m14) silently returns the projection to
    worker-attributed status: the files are written, nothing hides them, and
    they reappear in the worker's diff — F-3 all over again. Committing them
    instead (the pre-invocation-41 design) poisons fan-in composition with a
    divergent per-Task OBJECTIVE.md.
    """
    assert set(W.TRUSTED_PROJECTION_PATHS) == {"OBJECTIVE.md", "SHARED_CONTEXT.md"}

    root = tempfile.mkdtemp()
    lease, base = _build_fixture_lease(root)
    package = _canonical_package(BACKEND_SCOPE)
    projection = W.project_task_local_objective(package, lease)
    assert projection.get("ok")
    W._mark_projection_execution_context(lease, projection)
    # The base does NOT move: HEAD is still the canonical base commit.
    head = _git(lease, "rev-parse", "HEAD").stdout.strip()
    assert head == base, "the trusted phase must not move the attempt base"
    # The projected content is in effect on disk...
    body = open(os.path.join(lease, "OBJECTIVE.md"), encoding="utf-8").read()
    assert "# Your Task" in body
    # ...but git sees a clean tree: no status entry, no untracked listing.
    assert _git(lease, "status", "--porcelain").stdout.strip() == "", (
        "projection paths must be git-invisible after execution-context marking"
    )
    others = _git(lease, "ls-files", "--others", "--exclude-standard").stdout.strip()
    assert "SHARED_CONTEXT.md" not in others, (
        "the untracked projection file must be excluded from the verifier's listing"
    )
    # The mechanism is explicit: skip-worktree on the tracked path, an
    # info/exclude entry for the untracked one.
    flagged = _git(lease, "ls-files", "-v", "--", "OBJECTIVE.md").stdout.strip()
    assert flagged.startswith("S"), f"OBJECTIVE.md must carry skip-worktree, got {flagged!r}"
    exclude = open(os.path.join(lease, ".git", "info", "exclude"), encoding="utf-8").read()
    assert "/SHARED_CONTEXT.md" in exclude
    # Idempotent: a second marking changes nothing and stays clean.
    W._mark_projection_execution_context(lease, projection)
    assert _git(lease, "status", "--porcelain").stdout.strip() == ""
    exclude2 = open(os.path.join(lease, ".git", "info", "exclude"), encoding="utf-8").read()
    assert exclude2 == exclude, "re-marking must not duplicate exclude entries"


@_needs_bwrap
def test_18_writable_ref_reopen_comes_after_the_readonly_layer():
    """Bind ORDER is load-bearing (mutant m15).

    bwrap resolves binds left-to-right, so the attempt's writable ref namespace
    must be re-opened AFTER ``--ro-bind .git/refs``. Reversed, the read-only refs
    bind masks the attempt's own directory and every commit fails again — the
    exact F-1 symptom, reintroduced through ordering rather than through policy.
    """
    from substrate.execution.attempts.host_isolation import (
        IsolationProfile,
        build_bwrap_command,
    )

    root = tempfile.mkdtemp()
    refs = os.path.join(root, ".git", "refs")
    priv = os.path.join(refs, "attempt", "ea-1")
    os.makedirs(priv)
    cmd = build_bwrap_command(
        ["/bin/true"],
        IsolationProfile(
            worktree_path=root,
            worker_home=tempfile.mkdtemp(),
            tmp_path=tempfile.mkdtemp(),
            readonly_subpaths=[refs],
            writable_subpaths=[priv],
            scope_enforced=True,
        ),
    )
    ro_at = [i for i, a in enumerate(cmd) if a == "--ro-bind" and cmd[i + 1] == refs]
    rw_at = [i for i, a in enumerate(cmd) if a == "--bind" and cmd[i + 1] == priv]
    assert ro_at and rw_at, "both binds must be present"
    assert min(rw_at) > max(ro_at), (
        "the writable ref re-open must come AFTER the read-only refs bind, or the "
        "ro bind masks it and no worker can commit"
    )


@_needs_bwrap
def test_19_reversed_bind_order_actually_breaks_commits():
    """Prove the ordering above is load-bearing rather than merely asserted.

    Builds the reversed order explicitly and shows a real `git commit` fails —
    so the ordering test is anchored to observed behaviour, not to a convention.
    """
    root = tempfile.mkdtemp()
    lease, _ = _build_fixture_lease(root)
    priv = prepare_attempt_git_capability(lease, "ea-1")
    refs = os.path.join(lease, ".git", "refs")
    base_cmd = [
        "bwrap",
        "--die-with-parent",
        "--unshare-all",
        "--proc",
        "/proc",
        "--dev",
        "/dev",
        "--ro-bind",
        "/usr",
        "/usr",
        "--ro-bind",
        "/bin",
        "/bin",
        "--ro-bind",
        "/lib",
        "/lib",
        "--ro-bind",
        "/etc",
        "/etc",
    ]
    if os.path.isdir("/lib64"):
        base_cmd += ["--ro-bind", "/lib64", "/lib64"]
    script = (
        "echo x >> app/main.py && git add app/main.py && "
        "git -c user.email=w@w -c user.name=w commit -q -m t"
    )
    reversed_cmd = base_cmd + [
        "--bind",
        lease,
        lease,
        "--bind",
        priv,
        priv,  # WRONG: re-open first...
        "--ro-bind",
        refs,
        refs,  # ...then the ro layer masks it
        "--chdir",
        lease,
        "/bin/bash",
        "-c",
        script,
    ]
    correct_cmd = base_cmd + [
        "--bind",
        lease,
        lease,
        "--ro-bind",
        refs,
        refs,
        "--bind",
        priv,
        priv,  # RIGHT: re-open last
        "--chdir",
        lease,
        "/bin/bash",
        "-c",
        script,
    ]
    bad = subprocess.run(reversed_cmd, capture_output=True, text=True, timeout=120)
    good = subprocess.run(correct_cmd, capture_output=True, text=True, timeout=120)
    assert bad.returncode != 0, "reversed order must make the commit FAIL"
    assert good.returncode == 0, f"correct order must allow the commit: {good.stderr}"


@pytest.mark.parametrize(
    "spelling",
    [
        "OBJECTIVE.md",  # canonical
        "./OBJECTIVE.md",  # dot-slash — normalizes to OBJECTIVE.md
        "OBJECTIVE.md/",  # trailing slash — normalizes to OBJECTIVE.md
        "app/../OBJECTIVE.md",  # traversal-that-stays-in-root — normalizes to OBJECTIVE.md
    ],
)
def test_19_scope_naming_a_projection_path_refuses_before_the_worker_runs(spelling):
    """SYSTEM-OWNED PATH LAW (invocation 41): projection paths are never scope.

    A sealed package whose writable_path_scope names a projection-owned path
    would let the worker legitimately version control-plane execution context —
    the exact contamination the invocation-41 correction removed. The launcher
    must refuse it as a declaration error before any sandbox exists; the
    stand-in CLI proves the worker never ran.

    Reviewer-B MEDIUM: the guard NORMALIZES the scope exactly as the diff-scope
    verifier does, so a NON-canonical spelling (``./OBJECTIVE.md``,
    ``OBJECTIVE.md/``, ``app/../OBJECTIVE.md`` — all normalize to
    ``OBJECTIVE.md``) must be refused too. Without normalization the launcher
    would ADMIT such a scope while the verifier (which normalizes) would then
    ACCEPT a committed, divergent ``OBJECTIVE.md`` under it — re-arming the
    invocation-41 fan-in poison. This drives the REAL ``run_worker_in_lease``
    (not the helpers in isolation), which is what kills the raw-scope mutant.
    """
    root = tempfile.mkdtemp()
    lease, base = _build_fixture_lease(root)
    marker = os.path.join(lease, ".git", "worker-ran")
    result = _run_worker(
        lease,
        base,
        _canonical_package([spelling, *BACKEND_SCOPE]),
        f"touch {marker}\n",
    )
    assert not result.ok, f"scope spelled {spelling!r} must be refused by the launcher"
    assert "projection" in result.error, result.error
    assert "OBJECTIVE.md" in result.error, result.error
    assert not os.path.exists(marker), "the worker must never have started"
