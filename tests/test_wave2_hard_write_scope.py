"""Wave 2 — writable_path_scope is a CAPABILITY, not a request.

Field run ``20260803T191345Z-fail`` is the reason this file exists. Both workers
received correct, distinct, self-sufficient WorkPackets naming their exact
allowed AND forbidden paths, plus a verbatim "do NOT solve the complete
objective" and a numbered precedence note subordinating ``OBJECTIVE.md``. Both
nevertheless wrote the identical complete six-file objective, self-reported
success, and were refused on ``diff_scope`` — twice each, retries included.

That disproved the hypothesis that instruction content could enforce scope. The
canonical defect: ``writable_path_scope`` existed only as prompt text BEFORE the
work and a verification rule AFTER it. Nothing stood between the worker and the
file.

Two corrections, both proven here against the SHIPPED path:

A. ``project_task_local_objective`` — the worker's operative objective document
   is derived from its own canonical package; the all-Tasks fixture objective is
   demoted to read-only, explicitly non-authoritative ``SHARED_CONTEXT.md``.
B. ``readonly_binds_for_scope`` + ``IsolationProfile.readonly_subpaths`` — every
   path the Task may not modify is re-bound READ-ONLY inside the writable
   worktree, so an out-of-scope write fails at the MOUNT before the target
   changes. Not chmod: chmod still permits rename-over, delete-and-recreate, and
   parent-directory replacement, all of which are exercised below.

Execution scope and verification scope come from ONE authority: both derive from
the Task's persisted ``writable_path_scope`` via ``normalize_allowed_paths``.
The hard barrier SUPPLEMENTS the verifier; it never replaces it.
"""

from __future__ import annotations

import hashlib
import os
import subprocess
import sys
import tempfile
from types import SimpleNamespace
from typing import Any

import pytest

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if REPO not in sys.path:
    sys.path.insert(0, REPO)

from substrate.execution.attempts.field_task_scope import (  # noqa: E402
    BACKEND,
    FIXTURE_ALLOWED_PATHS,
    FRONTEND,
    VERIFICATION,
    ScopeResolutionError,
    normalize_allowed_paths,
    readonly_binds_for_scope,
)
from substrate.execution.attempts.host_isolation import (  # noqa: E402
    IsolationProfile,
    build_isolated_command,
    isolation_primitive,
)
from substrate.execution.attempts.worker_claude_cli import (  # noqa: E402
    _sealed_writable_scope,
    project_task_local_objective,
)

_FIXTURE_FILES = {
    "app/main.py": "backend",
    "app/store.py": "store",
    "app/static/app.js": "js",
    "app/static/index.html": "html",
    "tests/test_search_api.py": "be_test",
    "tests/test_ui_search.py": "fe_test",
    "OBJECTIVE.md": "TASK A contract\nTASK B contract\nTASK C contract\nTASK D contract",
}

_BWRAP = isolation_primitive() == "bwrap"
_needs_bwrap = pytest.mark.skipif(not _BWRAP, reason="bwrap primitive unavailable")


def _worktree() -> str:
    root = tempfile.mkdtemp()
    for rel, body in _FIXTURE_FILES.items():
        path = os.path.join(root, rel)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(body)
    # A realistic .git: the barrier is computed from paths that EXIST, so a
    # fixture missing `hooks/` cannot prove hooks are locked — and hooks are the
    # highest-value surface (executable code git runs on the worker's behalf).
    os.makedirs(os.path.join(root, ".git", "refs", "heads"), exist_ok=True)
    os.makedirs(os.path.join(root, ".git", "hooks"), exist_ok=True)
    os.makedirs(os.path.join(root, ".git", "objects"), exist_ok=True)
    with open(os.path.join(root, ".git", "config"), "w", encoding="utf-8") as fh:
        fh.write("[core]\n")
    with open(os.path.join(root, ".git", "HEAD"), "w", encoding="utf-8") as fh:
        fh.write("ref: refs/heads/main\n")
    return root


def _sha(path: str) -> str:
    with open(path, "rb") as fh:
        return hashlib.sha256(fh.read()).hexdigest()


def _run_confined(root: str, scope: list[str], script: str) -> subprocess.CompletedProcess:
    """Run ``script`` through the SHIPPED isolation builder with ``scope`` enforced."""
    profile = IsolationProfile(
        worktree_path=root,
        worker_home=tempfile.mkdtemp(),
        tmp_path=tempfile.mkdtemp(),
        readonly_subpaths=readonly_binds_for_scope(
            normalize_allowed_paths(scope, lease_root=root), lease_root=root
        ),
        scope_enforced=True,
    )
    return subprocess.run(
        build_isolated_command(["sh", "-c", script], profile),
        capture_output=True,
        text=True,
        timeout=120,
    )


def _package(task_id: str, scope: list[str], *, intent: str = "", end_state: str = "") -> Any:
    return SimpleNamespace(
        operation_identity={"task_id": task_id},
        ordered_context=[
            {
                "section": "context_frame",
                "payload": {
                    "intent": intent or f"Implement {task_id} ONLY",
                    "desired_end_state": end_state or f"{task_id} end state",
                    "constraints": [f"You may change ONLY these paths: {scope}"],
                },
            }
        ],
        governance_constraints=[f"writable_path_scope={sorted(scope)}"],
    )


# ── 1/2/3. Each Task gets exactly its own write authority ────────────────────


@_needs_bwrap
@pytest.mark.parametrize("rel", ["app/main.py", "app/store.py", "tests/test_search_api.py"])
def test_1_backend_worker_can_modify_its_authorized_files(rel):
    root = _worktree()
    result = _run_confined(root, list(FIXTURE_ALLOWED_PATHS[BACKEND]), f"echo LEGIT >> {rel}")
    assert result.returncode == 0, f"authorized write to {rel} must succeed: {result.stderr[:200]}"
    with open(os.path.join(root, rel), encoding="utf-8") as fh:
        assert "LEGIT" in fh.read()


@_needs_bwrap
@pytest.mark.parametrize(
    "rel", ["app/static/app.js", "app/static/index.html", "tests/test_ui_search.py"]
)
def test_2_backend_worker_cannot_modify_frontend_files(rel):
    root = _worktree()
    before = _sha(os.path.join(root, rel))
    result = _run_confined(root, list(FIXTURE_ALLOWED_PATHS[BACKEND]), f"echo HACK > {rel}")
    assert result.returncode != 0, f"out-of-scope write to {rel} must be DENIED"
    assert _sha(os.path.join(root, rel)) == before, f"{rel} must be byte-identical"


@_needs_bwrap
@pytest.mark.parametrize(
    ("rel", "allowed"),
    [
        ("app/static/app.js", True),
        ("tests/test_ui_search.py", True),
        ("app/main.py", False),
        ("app/store.py", False),
        ("tests/test_search_api.py", False),
    ],
)
def test_3_frontend_receives_the_inverse_authority(rel, allowed):
    root = _worktree()
    before = _sha(os.path.join(root, rel))
    result = _run_confined(root, list(FIXTURE_ALLOWED_PATHS[FRONTEND]), f"echo X >> {rel}")
    if allowed:
        assert result.returncode == 0, f"frontend must be able to write {rel}"
    else:
        assert result.returncode != 0, f"frontend must NOT be able to write {rel}"
        assert _sha(os.path.join(root, rel)) == before


# ── 4. Empty scope permits no source write ───────────────────────────────────


@_needs_bwrap
@pytest.mark.parametrize("rel", ["app/main.py", "app/static/app.js", "tests/test_ui_search.py"])
def test_4_verifier_empty_scope_permits_no_source_write(rel):
    """An empty scope is the STRONGEST policy, never 'unrestricted'."""
    assert FIXTURE_ALLOWED_PATHS[VERIFICATION] == []
    root = _worktree()
    before = _sha(os.path.join(root, rel))
    result = _run_confined(root, [], f"echo X > {rel}")
    assert result.returncode != 0, "zero-write lane must be unable to write anything"
    assert _sha(os.path.join(root, rel)) == before


# ── 5. Cross-lane context stays READABLE ─────────────────────────────────────


@_needs_bwrap
def test_5_both_tasks_can_read_required_cross_lane_context():
    """Read-only must mean READ-only, not inaccessible — a backend worker still
    needs to read the frontend contract to honour the shared interface."""
    root = _worktree()
    for scope in (FIXTURE_ALLOWED_PATHS[BACKEND], FIXTURE_ALLOWED_PATHS[FRONTEND]):
        result = _run_confined(root, list(scope), "cat app/static/app.js app/main.py")
        assert result.returncode == 0, f"cross-lane READ must work: {result.stderr[:200]}"
        assert "js" in result.stdout and "backend" in result.stdout


# ── 6/7. Task-local objective projection ─────────────────────────────────────


def test_6_task_local_views_exclude_the_other_task_contract():
    root_a, root_b = _worktree(), _worktree()
    project_task_local_objective(
        _package("wp-backend", FIXTURE_ALLOWED_PATHS[BACKEND], intent="BACKEND endpoint ONLY"),
        root_a,
    )
    project_task_local_objective(
        _package("wp-frontend", FIXTURE_ALLOWED_PATHS[FRONTEND], intent="FRONTEND UI ONLY"),
        root_b,
    )
    with open(os.path.join(root_a, "OBJECTIVE.md"), encoding="utf-8") as fh:
        view_a = fh.read()
    with open(os.path.join(root_b, "OBJECTIVE.md"), encoding="utf-8") as fh:
        view_b = fh.read()
    assert "BACKEND endpoint ONLY" in view_a and "FRONTEND UI ONLY" not in view_a
    assert "FRONTEND UI ONLY" in view_b and "BACKEND endpoint ONLY" not in view_b
    for view in (view_a, view_b):
        for other in ("TASK B contract", "TASK C contract", "TASK D contract"):
            assert other not in view, "the all-Tasks objective must not be the operative doc"


def test_6b_global_objective_is_preserved_as_non_authoritative_context():
    """Nothing is hidden: the global text survives, clearly subordinate."""
    root = _worktree()
    result = project_task_local_objective(
        _package("wp-backend", FIXTURE_ALLOWED_PATHS[BACKEND]), root
    )
    assert result["ok"] and result["shared_context"]
    with open(os.path.join(root, "SHARED_CONTEXT.md"), encoding="utf-8") as fh:
        shared = fh.read()
    assert "NOT AUTHORITATIVE" in shared
    assert "does NOT authorize you to widen your change surface" in shared
    assert "TASK B contract" in shared, "cross-lane detail must remain readable"


@_needs_bwrap
def test_7_global_objective_cannot_broaden_worker_authority():
    """Even with the global text present, the mount denies the wider write."""
    root = _worktree()
    before = _sha(os.path.join(root, "app/static/app.js"))
    result = _run_confined(
        root,
        list(FIXTURE_ALLOWED_PATHS[BACKEND]),
        "cat SHARED_CONTEXT.md OBJECTIVE.md 2>/dev/null; echo HACK > app/static/app.js",
    )
    assert result.returncode != 0
    assert _sha(os.path.join(root, "app/static/app.js")) == before


@_needs_bwrap
def test_7b_projected_objective_itself_becomes_read_only():
    """OBJECTIVE.md is outside every Task's scope, so the worker cannot rewrite
    its own assignment."""
    root = _worktree()
    project_task_local_objective(_package("wp-backend", FIXTURE_ALLOWED_PATHS[BACKEND]), root)
    before = _sha(os.path.join(root, "OBJECTIVE.md"))
    result = _run_confined(root, list(FIXTURE_ALLOWED_PATHS[BACKEND]), "echo X > OBJECTIVE.md")
    assert result.returncode != 0
    assert _sha(os.path.join(root, "OBJECTIVE.md")) == before


# ── 12. No unauthorized path changes even transiently ────────────────────────

_ESCAPES = [
    ("redirect", "echo H > {t}"),
    ("append", "echo H >> {t}"),
    ("python_open", 'python3 -c \'open("{t}","w").write("H")\''),
    ("sed_inplace", "sed -i s/js/H/ {t}"),
    ("cp_over", "cp app/main.py {t}"),
    ("mv_over", "cp app/main.py /tmp/s && mv /tmp/s {t}"),
    ("tmp_rename", "echo H > /tmp/t && mv /tmp/t {t}"),
    ("delete", "rm -f {t}"),
    ("delete_recreate", "rm -f {t} && echo H > {t}"),
    ("rm_rf_parent", "rm -rf app/static"),
    ("mv_parent_away", "mv app/static app/gone"),
    ("mkdir_inside", "mkdir -p app/static/evil"),
    ("symlink_escape", "ln -sf /etc/passwd {t} 2>&1; echo H > {t}"),
    ("hardlink_escape", "ln app/main.py {t} 2>&1"),
    ("path_traversal", "echo H > app/../{t}"),
    ("child_subprocess", 'python3 -c \'import subprocess;subprocess.run(["sh","-c","echo H > {t}"])\''),
    ("git_metadata", "echo H > .git/config"),
]


@_needs_bwrap
@pytest.mark.parametrize(("label", "script"), _ESCAPES, ids=[e[0] for e in _ESCAPES])
def test_12_every_escape_vector_leaves_forbidden_paths_byte_identical(label, script):
    """Real subprocesses, real mount. The target must be UNCHANGED — a denial
    that reverts after the fact is explicitly not acceptable."""
    root = _worktree()
    target = "app/static/app.js"
    guarded = {
        rel: _sha(os.path.join(root, rel))
        for rel in _FIXTURE_FILES
        if rel not in FIXTURE_ALLOWED_PATHS[BACKEND]
    }
    guarded[".git/config"] = _sha(os.path.join(root, ".git", "config"))
    _run_confined(root, list(FIXTURE_ALLOWED_PATHS[BACKEND]), script.format(t=target))
    for rel, before in guarded.items():
        path = os.path.join(root, rel)
        assert os.path.exists(path), f"{label}: {rel} must not be deleted"
        assert _sha(path) == before, f"{label}: {rel} must be byte-identical"


# ── the REAL launcher wires enforcement (no stand-in profile) ────────────────
#
# Everything above builds its own IsolationProfile. That is the right shape for
# proving the BARRIER works, but it cannot prove `run_worker_in_lease` actually
# USES the barrier — six mutants of the launch path survived a suite that only
# tested the mechanism. These tests drive the shipped launcher and inspect the
# command it really builds, so the wiring itself is under test.


class _Recorder:
    """Captures the argv the launcher hands to the sandboxed subprocess."""

    def __init__(self) -> None:
        self.cmd: list[str] = []

    def __call__(self, cmd, **kwargs):  # signature of gated_subprocess_run
        self.cmd = list(cmd)
        return SimpleNamespace(returncode=0, stdout="{}", stderr="")


def _git(root: str, *args: str):
    """Run a real git command in ``root`` (tests use REAL git, never a stub)."""
    return subprocess.run(
        ["git", *args], cwd=root, capture_output=True, text=True, timeout=60
    )


def _git_worktree(root: str) -> str:
    """Make ``root`` a REAL git repo with one base commit; return the base sha.

    Finding F-4. The launcher harness used to stub ``make_lease_selfcontained``
    and ``_capture_git`` and hand it a ``SimpleNamespace`` package — a shape
    production never constructs — so the suite proved the launcher works on
    input the field cannot produce and never exercised the git lifecycle at all.
    That is the same stand-in-bypass class as the earlier defect, moved from the
    object level down to the data level. These tests now use a real repository
    and the real git functions.
    """
    _git(root, "init", "-q", "-b", "main")
    _git(root, "config", "user.email", "test@umh.local")
    _git(root, "config", "user.name", "test")
    _git(root, "add", "-A")
    _git(root, "commit", "-qm", "fixture base")
    return _git(root, "rev-parse", "HEAD").stdout.strip()


def _canonical_package(scope_constraint: str | None, *, task_id: str = "wp-backend"):
    """A package built the way the SHIPPED path builds it.

    Mirrors what ``compile_attempt_package`` seals and what the runner
    reconstructs from the signed envelope: the same attribute set, in particular
    ``governance_constraints`` carrying ``writable_path_scope=``.
    """
    constraints = [] if scope_constraint is None else [scope_constraint]
    return SimpleNamespace(
        operation_identity={"task_id": task_id},
        ordered_context=[{"section": "context_frame", "payload": {"intent": "BACKEND ONLY"}}],
        governance_constraints=constraints,
        role_instructions="",
        operation_instructions="",
        verification_requirements=[],
    )


def _drive_launcher(monkeypatch, root: str, scope_constraint: str | None):
    """Run the SHIPPED run_worker_in_lease against a REAL git lease.

    Only the model CLI itself is replaced (by a recorder that captures the argv
    the launcher builds). Git self-containment, the trusted projection commit,
    the attempt git capability, bind computation and artifact capture are all
    production code running for real.
    """
    import substrate.execution.attempts.worker_claude_cli as wcl

    rec = _Recorder()
    monkeypatch.setattr(wcl, "_resolve_cli_path", lambda: "/bin/true")
    # run_worker_in_lease imports gated_subprocess_run INSIDE the function, so
    # the patch must land on the source module, not on a module-level alias.
    # NOTE: the recorder must let REAL git run — the launcher performs genuine
    # git work (rev-parse/add/commit) through this same gate. Only the model CLI
    # invocation is captured; everything else is delegated to the real function.
    import substrate.execution.cpu_gate as _cg

    real_gated = _cg.gated_subprocess_run

    def _dispatch(cmd, **kwargs):
        if cmd and str(cmd[0]).endswith("bwrap"):
            return rec(cmd, **kwargs)
        return real_gated(cmd, **kwargs)

    monkeypatch.setattr(_cg, "gated_subprocess_run", _dispatch)
    base = _git_worktree(root)
    lease = SimpleNamespace(worktree_path=root, base_commit=base, snapshot_ref=base)
    result = wcl.run_worker_in_lease(
        package=_canonical_package(scope_constraint),
        lease=lease,
        attempt_id="ea-test",
        run_root=tempfile.mkdtemp(),
    )
    return rec, result


@_needs_bwrap
def test_launcher_applies_readonly_binds_for_the_declared_scope(monkeypatch):
    """The real launcher must pass the forbidden paths as --ro-bind."""
    root = _worktree()
    rec, _ = _drive_launcher(
        monkeypatch, root, f"writable_path_scope={sorted(FIXTURE_ALLOWED_PATHS[BACKEND])}"
    )
    assert rec.cmd, "launcher must have invoked the sandboxed subprocess"
    ro_targets = {
        rec.cmd[i + 1] for i, a in enumerate(rec.cmd) if a == "--ro-bind" and i + 1 < len(rec.cmd)
    }
    # Forbidden SOURCE paths, plus each git AUTHORITY surface individually.
    # `.git` as a whole is deliberately NOT locked (finding F-1): a read-only
    # `.git` makes `index.lock` uncreatable, so `git add` fails with rc=128 and
    # no worker can ever commit. Its dangerous subpaths are locked instead.
    for forbidden in (
        "app/static",
        "tests/test_ui_search.py",
        ".git/hooks",
        ".git/config",
        ".git/refs",
        ".git/HEAD",
    ):
        assert os.path.join(root, forbidden) in ro_targets, (
            f"launcher must re-bind {forbidden} read-only"
        )
    assert os.path.join(root, ".git") not in ro_targets, (
        ".git must NOT be locked wholesale — that is what made commits impossible"
    )
    for allowed in FIXTURE_ALLOWED_PATHS[BACKEND]:
        assert os.path.join(root, allowed) not in ro_targets


@_needs_bwrap
def test_launcher_ro_binds_come_after_the_rw_worktree_bind(monkeypatch):
    root = _worktree()
    rec, _ = _drive_launcher(
        monkeypatch, root, f"writable_path_scope={sorted(FIXTURE_ALLOWED_PATHS[BACKEND])}"
    )
    rw = max(i for i, a in enumerate(rec.cmd) if a == "--bind" and rec.cmd[i + 1] == root)
    ro = [i for i, a in enumerate(rec.cmd) if a == "--ro-bind" and rec.cmd[i + 1].startswith(root)]
    assert ro and min(ro) > rw, "ro binds must be applied after the rw worktree bind"


def test_launcher_refuses_when_no_scope_is_sealed(monkeypatch):
    """A package with no writable_path_scope must NOT run unconstrained."""
    root = _worktree()
    rec, result = _drive_launcher(monkeypatch, root, None)
    assert not rec.cmd, "no worker may launch without an enforceable scope"
    assert result.ok is False
    assert "writable_path_scope" in result.error


def test_launcher_refuses_when_sealed_scope_is_unparseable(monkeypatch):
    root = _worktree()
    rec, result = _drive_launcher(monkeypatch, root, "writable_path_scope=<broken>")
    assert not rec.cmd, "an unparseable scope must fail closed, not run open"
    assert result.ok is False


@_needs_bwrap
def test_launcher_projects_the_task_local_objective(monkeypatch):
    """The real launcher must rewrite OBJECTIVE.md before the worker starts."""
    root = _worktree()
    _drive_launcher(
        monkeypatch, root, f"writable_path_scope={sorted(FIXTURE_ALLOWED_PATHS[BACKEND])}"
    )
    with open(os.path.join(root, "OBJECTIVE.md"), encoding="utf-8") as fh:
        objective = fh.read()
    assert "# Your Task" in objective, "launcher must project the task-local objective"
    assert "TASK B contract" not in objective
    assert os.path.exists(os.path.join(root, "SHARED_CONTEXT.md"))


@_needs_bwrap
def test_launcher_marks_the_profile_as_scope_enforced(monkeypatch):
    """The recorded command must reflect real enforcement, not a claim."""
    root = _worktree()
    rec, _ = _drive_launcher(
        monkeypatch, root, f"writable_path_scope={sorted(FIXTURE_ALLOWED_PATHS[BACKEND])}"
    )
    assert rec.cmd.count("--ro-bind") >= 3, (
        "scope_enforced must correspond to actual --ro-bind arguments"
    )


@_needs_bwrap
def test_launcher_zero_write_scope_locks_every_source_path(monkeypatch):
    root = _worktree()
    rec, _ = _drive_launcher(monkeypatch, root, "writable_path_scope=[]")
    ro_targets = {
        rec.cmd[i + 1] for i, a in enumerate(rec.cmd) if a == "--ro-bind" and i + 1 < len(rec.cmd)
    }
    for rel in ("app", "tests", "OBJECTIVE.md", ".git/hooks", ".git/config", ".git/refs"):
        assert os.path.join(root, rel) in ro_targets, f"zero-write lane must lock {rel}"
    # Even the zero-write (verifier) lane keeps `.git` itself bindable, because
    # the verifier still runs git READ commands and a wholesale lock is what
    # broke commits for the implementer lanes (F-1). Authority surfaces above
    # are locked individually in every lane.
    assert os.path.join(root, ".git") not in ro_targets


def test_launcher_refuses_when_bind_resolution_fails(monkeypatch):
    """A scope that cannot be turned into binds must ABORT the launch.

    Converting this failure into ``readonly_subpaths=[]`` would run the worker
    with a fully writable worktree — the exact defect this change removes, but
    reached through the error path instead of the happy path.
    """
    import substrate.execution.attempts.worker_claude_cli as wcl

    root = _worktree()

    def _boom(*_a, **_k):
        raise ScopeResolutionError("cannot enumerate lease")

    monkeypatch.setattr(wcl, "readonly_binds_for_scope", _boom)
    rec, result = _drive_launcher(
        monkeypatch, root, f"writable_path_scope={sorted(FIXTURE_ALLOWED_PATHS[BACKEND])}"
    )
    assert not rec.cmd, "no worker may launch when its barrier could not be built"
    assert result.ok is False
    assert "write-scope enforcement" in result.error


@_needs_bwrap
def test_launcher_enforcement_flag_matches_actual_binds(monkeypatch):
    """``scope_enforced`` must never claim more or less than the mount does.

    A profile that reports ``scope_enforced=False`` while binds are applied (or
    the reverse) makes the attempt record lie about whether the Task's authority
    was mechanically enforced.
    """
    import substrate.execution.attempts.host_isolation as iso

    root = _worktree()
    seen: list[IsolationProfile] = []
    real_build = iso.build_isolated_command

    def _spy(inner_cmd, profile):
        seen.append(profile)
        return real_build(inner_cmd, profile)

    monkeypatch.setattr(
        "substrate.execution.attempts.worker_claude_cli.build_isolated_command", _spy
    )
    _drive_launcher(
        monkeypatch, root, f"writable_path_scope={sorted(FIXTURE_ALLOWED_PATHS[BACKEND])}"
    )
    assert seen, "the launcher must build an isolated command"
    profile = seen[0]
    assert profile.readonly_subpaths, "binds must have been computed"
    assert profile.scope_enforced is True, (
        "a profile carrying real read-only binds must report scope_enforced=True"
    )


# ── scope resolution is fail-closed and canonical ────────────────────────────


def test_readonly_binds_cover_every_unauthorized_existing_path():
    root = _worktree()
    binds = readonly_binds_for_scope(
        normalize_allowed_paths(list(FIXTURE_ALLOWED_PATHS[BACKEND]), lease_root=root),
        lease_root=root,
    )
    rel = {os.path.relpath(b, root) for b in binds}
    assert "app/static" in rel, "the frontend directory must be read-only"
    assert "tests/test_ui_search.py" in rel
    assert "OBJECTIVE.md" in rel
    # ONE call returns the COMPLETE barrier — forbidden source paths AND the git
    # authority surfaces. It was briefly two functions, and a test that called
    # only this one let `echo H > .git/config` succeed; completeness is now the
    # default so a caller cannot obtain a partial barrier by forgetting a step.
    assert ".git/hooks" in rel, "hooks are executable code run on the worker's behalf"
    assert ".git/config" in rel, "core.hooksPath in config redirects hook execution"
    assert ".git/refs" in rel, "the ref namespace is an authorization surface"
    assert ".git" not in rel, (
        ".git must NOT be locked wholesale — index.lock lives inside it, so a "
        "read-only .git makes `git add` impossible and no worker can commit (F-1)"
    )
    for allowed in FIXTURE_ALLOWED_PATHS[BACKEND]:
        assert allowed not in rel, f"{allowed} is authorized and must stay writable"


def test_partial_overlap_keeps_the_authorized_child_writable():
    """`tests/` holds one allowed and one forbidden file — the parent must be
    descended into, never masked wholesale."""
    root = _worktree()
    binds = readonly_binds_for_scope(
        normalize_allowed_paths(["tests/test_search_api.py"], lease_root=root), lease_root=root
    )
    rel = {os.path.relpath(b, root) for b in binds}
    assert "tests/test_ui_search.py" in rel
    assert "tests" not in rel, "masking the whole dir would break the authorized child"


def test_scope_resolution_fails_closed_on_whole_worktree_and_escape():
    root = _worktree()
    for bad in (["."], [""], ["../escape"], ["/abs/path"]):
        with pytest.raises(ScopeResolutionError):
            normalize_allowed_paths(bad, lease_root=root)


def test_execution_and_verification_read_one_authority():
    """The sealed constraint the sandbox reads is the same one the verifier and
    the prompt read — not a parallel derivation."""
    pkg = _package("wp-backend", FIXTURE_ALLOWED_PATHS[BACKEND])
    assert _sealed_writable_scope(pkg) == sorted(FIXTURE_ALLOWED_PATHS[BACKEND])


def test_missing_sealed_scope_is_none_not_open():
    assert _sealed_writable_scope(SimpleNamespace(governance_constraints=[])) is None


def test_empty_sealed_scope_is_a_real_policy_not_missing():
    pkg = SimpleNamespace(governance_constraints=["writable_path_scope=[]"])
    assert _sealed_writable_scope(pkg) == [], "empty is zero-write, distinct from absent"


def test_unparseable_sealed_scope_fails_closed():
    pkg = SimpleNamespace(governance_constraints=["writable_path_scope=<not-a-list>"])
    with pytest.raises(ScopeResolutionError):
        _sealed_writable_scope(pkg)


def test_string_sealed_scope_fails_closed():
    """A bare string would iterate character-by-character into fake paths."""
    pkg = SimpleNamespace(governance_constraints=["writable_path_scope='app/main.py'"])
    with pytest.raises(ScopeResolutionError):
        _sealed_writable_scope(pkg)


def test_profile_carries_the_enforcement_flag():
    profile = IsolationProfile(
        worktree_path="/x", worker_home="/y", readonly_subpaths=["/x/a"], scope_enforced=True
    )
    assert profile.scope_enforced and profile.readonly_subpaths == ["/x/a"]


def test_default_profile_declares_no_enforcement():
    """A profile built without a scope must not claim enforcement it lacks."""
    profile = IsolationProfile(worktree_path="/x", worker_home="/y")
    assert profile.scope_enforced is False and profile.readonly_subpaths == []


@_needs_bwrap
def test_readonly_binds_appear_after_the_writable_bind():
    """Order is load-bearing: bwrap applies binds left-to-right, so a ro-bind
    placed BEFORE the rw worktree bind would be masked by it."""
    profile = IsolationProfile(
        worktree_path="/w", worker_home="/h", readonly_subpaths=["/w/forbidden"]
    )
    cmd = build_isolated_command(["true"], profile)
    rw = max(i for i, a in enumerate(cmd) if a == "--bind" and cmd[i + 1] == "/w")
    ro = min(i for i, a in enumerate(cmd) if a == "--ro-bind" and cmd[i + 1] == "/w/forbidden")
    assert ro > rw, "read-only subpath binds must come AFTER the writable worktree bind"
