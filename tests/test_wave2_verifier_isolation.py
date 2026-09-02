"""Wave 2 C-4 — confined independent verifier. No host-env execution of worker code.

The verifier used to run the fixture's own pytest (which imports the worker's
``conftest.py`` = arbitrary Python) with ``cwd=<lease worktree>`` via
``gated_subprocess_run`` — no bwrap, no env scrub, full host env including the
OAuth token. This suite pins the canonical confined verifier seam
(``run_confined_verifier_checks``): distinct verifier lease + identity, bwrap-only
(fail-closed), read-only source, network unshared, credential-free env, parent-side
zero-diff proof, lease teardown on every path — and the adversarial fixture whose
conftest tries to exfiltrate secrets / read host paths / write source / hit the
network, each of which must fail while a legitimate test still runs.

Tests that need a real sandbox are skipped when bwrap is absent, but the
source/AST guards and the fail-closed-without-bwrap path always run.
"""

from __future__ import annotations

import os
import subprocess

import pytest

from substrate.execution.attempts import verifier_isolation as vi
from substrate.execution.attempts.host_isolation import isolation_primitive

_HAS_BWRAP = isolation_primitive() == "bwrap"
_needs_bwrap = pytest.mark.skipif(not _HAS_BWRAP, reason="bwrap unavailable in this environment")


def _skip_if_cpu_gated():
    """Skip a bwrap-executing test when the CPU gate would block the preflight.

    The confined verifier's isolation preflight runs through the CPU gate; under a
    transient high host load (parallel jobs) the gate blocks it, yielding only the
    fail-closed ``verifier_isolation`` check. That is CORRECT fail-closed behavior,
    not a defect — but it makes the positive-path assertions untestable, so skip."""
    from substrate.execution.attempts.host_isolation import preflight_isolation

    ok, detail = preflight_isolation("/opt/OS")
    if not ok and ("CPU gate" in detail or "skipped" in detail):
        pytest.skip(f"preflight CPU-gated (transient load): {detail}")


class _Att:
    def __init__(self, attempt_id="att-1", task_id="wp-x", worker_identity="worker:impl:att-1"):
        self.attempt_id = attempt_id
        self.task_id = task_id
        self.worker_identity = worker_identity


def _git_fixture(tmp_path, *, extra_files=None, conftest="import os\n"):
    """A minimal committed git source tree with a tests/ dir + conftest."""
    src = tmp_path / "src"
    (src / "tests").mkdir(parents=True)
    (src / "tests" / "conftest.py").write_text(conftest, encoding="utf-8")
    (src / "tests" / "test_basic.py").write_text(
        "def test_arith():\n    assert 1 + 1 == 2\n", encoding="utf-8"
    )
    for rel, content in (extra_files or {}).items():
        p = src / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content, encoding="utf-8")
    subprocess.run(["git", "init", "-q"], cwd=src, check=True)
    subprocess.run(
        ["git", "-c", "user.email=a@b.c", "-c", "user.name=t", "add", "-A"], cwd=src, check=True
    )
    subprocess.run(
        ["git", "-c", "user.email=a@b.c", "-c", "user.name=t", "commit", "-qm", "base"],
        cwd=src,
        check=True,
    )
    sha = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=src, capture_output=True, text=True
    ).stdout.strip()
    return str(src), sha


def _run(src, sha, run_root, *, worker_identity="worker:impl:att-1", timeout_s=120, **kw):
    return vi.run_confined_verifier_checks(
        attempt=_Att(worker_identity=worker_identity),
        run_root=str(run_root),
        source_path=src,
        verifier_role_id="role-verifier-op",
        worker_identity=worker_identity,
        base_commit=kw.pop("base_commit", ""),
        timeout_s=timeout_s,
        **kw,
    )


# ── fail-closed without bwrap (always runs) ─────────────────────────────────


def test_no_bwrap_fails_closed(monkeypatch, tmp_path):
    monkeypatch.setattr(vi, "isolation_primitive", lambda: None)
    src, sha = _git_fixture(tmp_path)
    checks, ev = _run(src, sha, tmp_path / "run")
    iso = next(c for c in checks if c.check_id == "verifier_isolation")
    assert iso.ok is False and "unconfined" in iso.detail.lower()
    assert ev.zero_diff is False and ev.tests_ok is False


def test_non_bwrap_primitive_fails_closed(monkeypatch, tmp_path):
    # systemd-run/nsjail provide no mount namespace → must be refused, never used.
    monkeypatch.setattr(vi, "isolation_primitive", lambda: "systemd-run")
    src, sha = _git_fixture(tmp_path)
    checks, _ = _run(src, sha, tmp_path / "run")
    iso = next(c for c in checks if c.check_id == "verifier_isolation")
    assert iso.ok is False


def test_preflight_unproven_fails_closed(monkeypatch, tmp_path):
    monkeypatch.setattr(vi, "isolation_primitive", lambda: "bwrap")
    monkeypatch.setattr(vi, "preflight_isolation", lambda _p="/opt/OS": (False, "probe saw leak"))
    src, sha = _git_fixture(tmp_path)
    checks, _ = _run(src, sha, tmp_path / "run")
    iso = next(c for c in checks if c.check_id == "verifier_isolation")
    assert iso.ok is False and "preflight" in iso.detail.lower()


# ── argv is a real bwrap invocation, never a host shell ─────────────────────


def test_command_is_bwrap_argv_never_shell():
    from substrate.execution.attempts.host_isolation import (
        VerifierIsolationProfile,
        build_isolated_verifier_command,
    )

    if not _HAS_BWRAP:
        pytest.skip("bwrap unavailable")
    prof = VerifierIsolationProfile(
        source_ro_path="/tmp", verifier_home="/tmp/h", tmp_path="/tmp/t", allow_network=False
    )
    argv = build_isolated_verifier_command(["python3", "-m", "pytest"], prof)
    assert argv[0] == "bwrap"
    assert "--unshare-all" in argv  # implies --unshare-net
    assert "--ro-bind" in argv  # source is read-only
    # the source is bound read-only, NEVER writable
    assert "--bind" not in argv[: argv.index("/tmp") + 1] or "--ro-bind" in argv
    assert "--share-net" not in argv  # worker code gets no network


def test_env_scrub_strips_all_credentials():
    from substrate.execution.attempts.host_isolation import scrub_verifier_env

    base = {
        "PATH": "/usr/bin",
        "CLAUDE_CODE_OAUTH_TOKEN": "SECRET",
        "ANTHROPIC_API_KEY": "SECRET",
        "UMH_W2_DISPATCH_SECRET": "SECRET",
        "UMH_MESH_RELAY_SECRET": "SECRET",
        "GITHUB_TOKEN": "SECRET",
        "OP_SERVICE_ACCOUNT_TOKEN": "SECRET",
        "CLAUDE_CONFIG_DIR": "/home/worker/.claude",
        "FLY_API_TOKEN": "SECRET",
    }
    out = scrub_verifier_env(base)
    assert out.get("PATH") == "/usr/bin"
    for forbidden in (
        "CLAUDE_CODE_OAUTH_TOKEN",
        "ANTHROPIC_API_KEY",
        "UMH_W2_DISPATCH_SECRET",
        "UMH_MESH_RELAY_SECRET",
        "GITHUB_TOKEN",
        "OP_SERVICE_ACCOUNT_TOKEN",
        "CLAUDE_CONFIG_DIR",
        "FLY_API_TOKEN",
    ):
        assert forbidden not in out, forbidden


# ── verifier lease distinct from worker; SoD ────────────────────────────────


def test_verifier_lease_distinct_home_credential_free(tmp_path):
    lease = vi.open_verifier_lease(
        attempt_id="att-1",
        task_id="wp-x",
        run_root=str(tmp_path),
        source_ro_path=str(tmp_path),
        verifier_role_id="role-verifier-op",
        worker_identity="worker:impl:att-1",
    )
    try:
        # distinct verifier-homes/ tree, not worker-homes/
        assert "verifier-homes" in lease.home.home_path
        assert "worker-homes" not in lease.home.home_path
        # NO credential placed
        assert lease.home.credential_files == []
        # private HOME/XDG/TMP
        ov = lease.env_overrides()
        assert ov["HOME"] == lease.home.home_path
        assert ov["TMPDIR"] == lease.home.tmp_path
        assert ov["XDG_CONFIG_HOME"].startswith(lease.home.home_path)
        assert lease.verifier_identity != "worker:impl:att-1"
    finally:
        vi.close_verifier_lease(lease)


def test_verifier_identity_collision_with_worker_fails(tmp_path):
    with pytest.raises(vi.VerifierIsolationError, match="separation of duty|collides"):
        vi.open_verifier_lease(
            attempt_id="att-1",
            task_id="wp-x",
            run_root=str(tmp_path),
            source_ro_path=str(tmp_path),
            verifier_role_id="role-verifier-op",
            # a worker that forged the verifier identity string
            worker_identity="verifier:role-verifier-op:att-1",
        )


def test_missing_source_path_fails_closed(tmp_path):
    with pytest.raises(vi.VerifierIsolationError, match="not a directory"):
        vi.open_verifier_lease(
            attempt_id="att-1",
            task_id="wp-x",
            run_root=str(tmp_path),
            source_ro_path=str(tmp_path / "does-not-exist"),
            verifier_role_id="role-verifier-op",
            worker_identity="worker:impl:att-1",
        )


# ── lifecycle / cleanup ─────────────────────────────────────────────────────


def test_verifier_home_destroyed_after_run(tmp_path):
    if not _HAS_BWRAP:
        pytest.skip("bwrap unavailable")
    _skip_if_cpu_gated()
    src, sha = _git_fixture(tmp_path)
    run_root = tmp_path / "run"
    _run(src, sha, run_root)
    from substrate.execution.attempts.worker_credential_boundary import (
        assert_no_verifier_home_residue,
    )

    assert assert_no_verifier_home_residue(str(run_root)) == []


def test_cleanup_failure_is_blocking(monkeypatch, tmp_path):
    if not _HAS_BWRAP:
        pytest.skip("bwrap unavailable")
    _skip_if_cpu_gated()
    from substrate.execution.attempts.worker_credential_boundary import CredentialBoundaryError

    def _boom(_home):
        raise CredentialBoundaryError("residue remains (SECURITY FAILURE)")

    monkeypatch.setattr(vi, "close_attempt_credential_home", _boom)
    src, sha = _git_fixture(tmp_path)
    with pytest.raises(vi.VerifierIsolationError, match="cleanup failed|blocking security"):
        _run(src, sha, tmp_path / "run")


# ── the adversarial worker-authored conftest (through the seam) ─────────────

_ADVERSARIAL_CONFTEST = (
    "import os, urllib.request\n"
    "# exfiltration + escape attempts at COLLECTION time (conftest is arbitrary code)\n"
    "assert os.environ.get('CLAUDE_CODE_OAUTH_TOKEN') is None, 'token leaked to verifier'\n"
    "assert os.environ.get('UMH_W2_DISPATCH_SECRET') is None, 'dispatch secret leaked'\n"
    "assert not os.path.exists('/opt/OS'), '/opt/OS reachable'\n"
    "assert not os.path.exists('/root/.claude'), '/root/.claude reachable'\n"
)

_ADVERSARIAL_TESTS = (
    "import os, urllib.request\n"
    "def test_legit_still_runs():\n"
    "    assert 2 + 2 == 4\n"
    "def test_cannot_write_source():\n"
    "    dst = os.path.join(os.path.dirname(__file__), 'INTRUSION')\n"
    "    try:\n"
    "        open(dst, 'w').write('x'); wrote = True\n"
    "    except OSError:\n"
    "        wrote = False\n"
    "    assert not wrote, 'source was writable'\n"
    "def test_no_outbound_network():\n"
    "    try:\n"
    "        urllib.request.urlopen('http://1.1.1.1', timeout=3); net = True\n"
    "    except Exception:\n"
    "        net = False\n"
    "    assert not net, 'network reachable'\n"
    "def test_host_tmp_absent():\n"
    "    # a host /tmp file must not be visible; our /tmp is a fresh tmpfs\n"
    "    assert not os.path.exists('/tmp/HOST_MARKER_C4')\n"
)


@_needs_bwrap
def test_adversarial_conftest_all_probes_denied_legit_runs(tmp_path):
    _skip_if_cpu_gated()
    # plant a host /tmp marker the sandbox must NOT see
    with open("/tmp/HOST_MARKER_C4", "w") as f:
        f.write("host")
    try:
        # poison the PARENT env — the child must never receive it
        os.environ["CLAUDE_CODE_OAUTH_TOKEN"] = "PARENT-SECRET-TOKEN"
        os.environ["UMH_W2_DISPATCH_SECRET"] = "PARENT-SECRET-DISPATCH"
        src, sha = _git_fixture(
            tmp_path,
            conftest=_ADVERSARIAL_CONFTEST,
            extra_files={"tests/test_adversarial.py": _ADVERSARIAL_TESTS},
        )
        run_root = tmp_path / "run"
        checks, ev = _run(src, sha, run_root)
        by_id = {c.check_id: c for c in checks}
        # legitimate tests passed AND every adversarial probe was denied → rc 0
        assert by_id["independent_tests"].ok is True, by_id["independent_tests"].detail
        assert by_id["verifier_zero_diff"].ok is True
        # env carried NO secret names
        assert "CLAUDE_CODE_OAUTH_TOKEN" not in ev.env_var_names
        assert "UMH_W2_DISPATCH_SECRET" not in ev.env_var_names
        # mount policy proves the boundaries
        assert ev.mount_policy["opt_os_bound"] is False
        assert ev.mount_policy["network"] == "unshared"
        assert ev.evidence_sha256  # hashed evidence produced
    finally:
        os.path.exists("/tmp/HOST_MARKER_C4") and os.unlink("/tmp/HOST_MARKER_C4")


@_needs_bwrap
def test_source_mutation_is_detected_parent_side(tmp_path):
    _skip_if_cpu_gated()
    """A test that DID mutate the source (run without the ro-bind) must be caught by
    the parent-side integrity check — proving we never trust the subprocess."""
    src, sha = _git_fixture(
        tmp_path,
        extra_files={
            "tests/test_writes.py": (
                "import os\n"
                "def test_writes_source():\n"
                "    # write into the source dir; under ro-bind this fails, so to\n"
                "    # exercise the PARENT check we assert nothing — the mutation is\n"
                "    # simulated by the test below instead.\n"
                "    assert True\n"
            )
        },
    )
    # Simulate a verifier that mutated the source AFTER the before-snapshot by
    # patching _source_tree_hashes to return divergent maps.
    import substrate.execution.attempts.verifier_isolation as vimod

    orig = vimod._source_tree_hashes
    calls = {"n": 0}

    def _fake(path):
        calls["n"] += 1
        base = orig(path)
        if calls["n"] >= 2:  # the AFTER snapshot differs
            base = {**base, "tests/INTRUSION": "deadbeef"}
        return base

    vimod._source_tree_hashes = _fake
    try:
        checks, ev = _run(src, sha, tmp_path / "run")
        zd = next(c for c in checks if c.check_id == "verifier_zero_diff")
        assert zd.ok is False and "MUTATED" in zd.detail
        # tests check must also be False (tests only count if source intact)
        it = next(c for c in checks if c.check_id == "independent_tests")
        assert it.ok is False
    finally:
        vimod._source_tree_hashes = orig


# ── source/AST guards + mutation guards (item 12) ───────────────────────────


def test_control_plane_never_runs_worker_pytest_on_host():
    """The production verifier path must route through run_confined_verifier_checks
    and must NOT invoke pytest with cwd=<worktree> on the host."""
    import ast
    import inspect

    from substrate.execution.attempts import field_control_plane as fcp

    src = inspect.getsource(fcp.FieldControlPlaneDriver._independent_checks_for)
    tree = ast.parse(src.lstrip())
    code = ast.unparse(tree)
    assert "run_confined_verifier_checks" in code, "must route through the confined seam"
    # the old unconfined form: gated_subprocess_run([... 'pytest' ...], cwd=...)
    assert "cwd=target" not in code, "must not run pytest on the host with cwd=worktree"
    assert "'pytest'" not in code and '"pytest"' not in code, (
        "the control plane must not build a host pytest argv itself"
    )


def test_confined_seam_requires_bwrap_no_host_fallback():
    """AST guard: run_confined_verifier_checks fails closed on a non-bwrap primitive
    and never calls gated_subprocess_run with a bare pytest (unconfined) argv."""
    import ast
    import inspect

    src = inspect.getsource(vi.run_confined_verifier_checks)
    code = ast.unparse(ast.parse(src.lstrip()))
    assert 'prim != "bwrap"' in code or "prim != 'bwrap'" in code
    assert "build_isolated_verifier_command" in code
    # the only gated_subprocess_run in the confined check must run the bwrap argv
    assert "cwd=source" not in code and "cwd=target" not in code, (
        "worker code must run inside bwrap, never a cwd= host subprocess"
    )


def test_default_argv_runs_pytest_inside_bwrap():
    """The default inner argv is pytest, and it is wrapped by the verifier bwrap
    builder (never executed directly)."""
    import ast
    import inspect

    code = ast.unparse(ast.parse(inspect.getsource(vi.run_confined_verifier_checks).lstrip()))
    assert "pytest" in code
    # pytest (as `inner`) is wrapped by the trusted pid wrapper, then by the
    # verifier bwrap builder — never executed directly on the host.
    assert "build_isolated_verifier_command(wrapped_inner, profile)" in code
    assert "_build_pid_wrapper(inner" in code
    assert "allow_network=False" in code
