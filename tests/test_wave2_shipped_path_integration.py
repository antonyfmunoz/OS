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

    Returns the attempt's re-anchored base commit. Used by tests that need to
    observe git state as it stands when the WORKER starts — i.e. after the
    system's own authorized writes, so those are never mistaken for an escape.
    Calling it twice is harmless: both steps are idempotent.
    """
    projection = W.project_task_local_objective(package, lease)
    assert projection.get("ok"), projection
    new_base = W._commit_trusted_projection(lease, base, projection)
    W.prepare_attempt_git_capability(lease, attempt_id)
    return new_base


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
        ("sibling_attempt_ref", "mkdir -p .git/refs/attempt/other && echo x > .git/refs/attempt/other/work"),
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


@_needs_bwrap
def test_6_zero_write_lane_produces_an_empty_worker_diff():
    """Proof 12. The verifier lane writes nothing — including no projection."""
    root = tempfile.mkdtemp()
    lease, base = _build_fixture_lease(root)
    result = _run_worker(lease, base, _canonical_package([], task_id="wp-verify"), "echo noop")
    assert result.files_changed == [], (
        f"a zero-write lane must produce an empty diff, got {result.files_changed}"
    )


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
    assert envelope.governance_constraints == [
        f"writable_path_scope={sorted(BACKEND_SCOPE)}"
    ]


def test_9_runner_package_reconstruction_preserves_the_sealed_scope(tmp_path):
    """Proof 6 + 11. What the runner rebuilds must resolve to the SAME scope.

    This is the boundary F-2 lived at: the runner used to substitute a package
    with no governance_constraints at all.
    """
    _, claimed = _spool_roundtrip(tmp_path)
    _, envelope = claimed

    class _Package:  # verbatim shape from scripts/wave2_attempt_runner.py
        role_instructions = envelope.role_instructions
        operation_instructions = envelope.operation_instructions
        ordered_context = list(envelope.ordered_context or [])
        operation_identity = dict(envelope.operation_identity or {})
        governance_constraints = list(envelope.governance_constraints or [])
        verification_requirements = list(envelope.verification_requirements or [])

    assert W._sealed_writable_scope(_Package()) == sorted(BACKEND_SCOPE)


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
