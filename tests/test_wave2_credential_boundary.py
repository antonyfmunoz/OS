"""Wave 2 R1 — ADVERSARIAL tests for the per-attempt credential boundary.

These attack the boundary; they do not mock it. Where a claim is about the
sandbox (one worker cannot read another's credential; the worker cannot read
/opt/OS), the test RUNS A REAL bwrap process and asserts on what that process
could actually see. A test that stubs the sandbox would prove nothing.

Repairs pinned here (finding SEC-C2): ``worker_home`` was
``dirname(worktree_path)`` — identical for every lease in a run — so two
concurrent workers shared one home, the real ``~/.claude`` credential was copied
into it, and nothing deleted it.
"""

from __future__ import annotations

import os
import shutil
import stat
import subprocess

import pytest

from substrate.execution.attempts.host_isolation import (
    FORBIDDEN_ENV_PREFIXES,
    IsolationProfile,
    build_bwrap_command,
    isolation_primitive,
    scrub_worker_env,
)
from substrate.execution.attempts.worker_credential_boundary import (
    CredentialBoundaryError,
    assert_no_credential_residue,
    attempt_home_path,
    close_attempt_credential_home,
    open_attempt_credential_home,
    worker_homes_root,
)
from substrate.execution.attempts import worker_credential_boundary as wcb

_HAVE_BWRAP = isolation_primitive() == "bwrap"
_needs_bwrap = pytest.mark.skipif(_HAVE_BWRAP is False, reason="bwrap not available")


def _fake_claude_dir(tmp_path, token_body: str):
    """A stand-in for the operator's ~/.claude holding a planted credential."""
    src = tmp_path / "real-claude"
    src.mkdir()
    (src / ".credentials.json").write_text(token_body, encoding="utf-8")
    (src / "config.json").write_text('{"theme":"dark"}', encoding="utf-8")
    # Must never be copied across the boundary.
    (src / "settings.json").write_text('{"secret":"NOPE"}', encoding="utf-8")
    (src / "history.jsonl").write_text('{"h":1}\n', encoding="utf-8")
    return str(src)


# ── 1. one private home per attempt ─────────────────────────────────────────


def test_home_is_derived_from_attempt_id_not_worktree_parent(tmp_path):
    """The regression itself: two attempts sharing a worktree PARENT must still
    get different homes. Under the old derivation both resolved to
    `<leases>/.worker-home` and collided."""
    run_root = str(tmp_path / "run")
    a = attempt_home_path(run_root, "ea-aaaa1111")
    b = attempt_home_path(run_root, "ea-bbbb2222")
    assert a != b, "distinct attempts must not share a home"
    # And neither is the shared-parent path the old code produced.
    shared_parent_style = os.path.join(run_root, "leases", ".worker-home")
    assert a != shared_parent_style and b != shared_parent_style


def test_retry_attempt_gets_a_new_home(tmp_path):
    """A2 is a NEW attempt id, so it must not inherit A1's home/credential."""
    run_root = str(tmp_path / "run")
    src = _fake_claude_dir(tmp_path, "A1-TOKEN")
    a1 = open_attempt_credential_home(attempt_id="ea-a1", run_root=run_root, source_claude_dir=src)
    a2 = open_attempt_credential_home(attempt_id="ea-a2", run_root=run_root, source_claude_dir=src)
    assert a1.home_path != a2.home_path
    close_attempt_credential_home(a1)
    # A1 destroyed; A2 survives independently.
    assert not os.path.exists(a1.home_path)
    assert os.path.isdir(a2.home_path)
    close_attempt_credential_home(a2)


def test_home_and_credential_modes_are_private(tmp_path):
    run_root = str(tmp_path / "run")
    src = _fake_claude_dir(tmp_path, "TOKEN-MODE")
    home = open_attempt_credential_home(
        attempt_id="ea-mode", run_root=run_root, source_claude_dir=src
    )
    assert stat.S_IMODE(os.stat(home.home_path).st_mode) == 0o700
    assert stat.S_IMODE(os.stat(home.tmp_path).st_mode) == 0o700
    assert home.credential_files, "a credential should have been placed"
    for cred in home.credential_files:
        mode = stat.S_IMODE(os.stat(cred).st_mode)
        assert mode == 0o600, f"{cred} must be 0600, got {mode:o}"
    close_attempt_credential_home(home)


def test_windows_attempt_home_uses_private_acl_not_posix_mode(tmp_path, monkeypatch):
    calls = []

    class Result:
        returncode = 0
        stdout = (
            "C:\\tmp\\home DESKTOP-LVGUIQ9\\antonys beast pc:(F)\n"
            "            NT AUTHORITY\\SYSTEM:(F)\n"
            "Successfully processed 1 files; Failed processing 0 files"
        )
        stderr = ""

    def fake_acl(args):
        calls.append(args)
        return Result()

    src = tmp_path / "real-codex"
    src.mkdir()
    (src / "auth.json").write_text('{"account":"test"}', encoding="utf-8")
    monkeypatch.setattr(wcb, "_IS_WINDOWS", True)
    monkeypatch.setattr(wcb, "_run_acl_command", fake_acl)
    monkeypatch.setenv("USERDOMAIN", "DESKTOP-LVGUIQ9")
    monkeypatch.setenv("USERNAME", "antonys beast pc")

    home = open_attempt_credential_home(
        attempt_id="ea-windows",
        run_root=str(tmp_path / "run"),
        provider="codex",
        source_codex_dir=str(src),
    )

    try:
        assert home.credential_files
        assert any(call[:3] == ["icacls", home.home_path, "/inheritance:r"] for call in calls)
        assert any(str(call[1]).endswith("auth.json") for call in calls)
        assert any("DESKTOP-LVGUIQ9\\antonys beast pc" in part for call in calls for part in call)
    finally:
        close_attempt_credential_home(home)


def test_windows_acl_assertion_rejects_broad_access(monkeypatch):
    class Result:
        returncode = 0
        stdout = "C:\\tmp\\home BUILTIN\\Users:(I)(RX)\n"
        stderr = ""

    monkeypatch.setattr(wcb, "_IS_WINDOWS", True)
    monkeypatch.setattr(wcb, "_run_acl_command", lambda args: Result())

    with pytest.raises(CredentialBoundaryError, match="broad Windows access"):
        wcb._assert_private("C:\\tmp\\home")


def test_env_overrides_are_all_attempt_private(tmp_path):
    """HOME alone is not enough — XDG_*, CLAUDE_CONFIG_DIR and TMPDIR must also
    point inside the attempt boundary, or config lookup escapes it."""
    run_root = str(tmp_path / "run")
    home = open_attempt_credential_home(
        attempt_id="ea-env", run_root=run_root, copy_credentials=False
    )
    env = home.env_overrides()
    for key in (
        "HOME",
        "XDG_CONFIG_HOME",
        "XDG_CACHE_HOME",
        "XDG_DATA_HOME",
        "CLAUDE_CONFIG_DIR",
        "TMPDIR",
    ):
        assert key in env, f"{key} must be overridden"
        assert env[key].startswith(home.home_path), f"{key} escapes the attempt home"
    close_attempt_credential_home(home)


def test_only_minimal_credential_files_cross_the_boundary(tmp_path):
    """settings.json / history.jsonl must NOT be copied into an attempt home."""
    run_root = str(tmp_path / "run")
    src = _fake_claude_dir(tmp_path, "TOKEN-MIN")
    home = open_attempt_credential_home(
        attempt_id="ea-min", run_root=run_root, source_claude_dir=src
    )
    present = set(os.listdir(home.claude_dir))
    assert ".credentials.json" in present
    assert "settings.json" not in present, "settings.json must not cross the boundary"
    assert "history.jsonl" not in present, "history must not cross the boundary"
    close_attempt_credential_home(home)


# ── 2. credential lifetime is attempt-bound ─────────────────────────────────


def test_close_destroys_home_and_credential(tmp_path):
    run_root = str(tmp_path / "run")
    src = _fake_claude_dir(tmp_path, "TOKEN-DESTROY")
    home = open_attempt_credential_home(
        attempt_id="ea-destroy", run_root=run_root, source_claude_dir=src
    )
    cred = home.credential_files[0]
    assert os.path.isfile(cred)
    close_attempt_credential_home(home)
    assert not os.path.exists(cred)
    assert not os.path.exists(home.home_path)
    assert assert_no_credential_residue(run_root) == []


def test_close_is_idempotent(tmp_path):
    run_root = str(tmp_path / "run")
    home = open_attempt_credential_home(
        attempt_id="ea-idem", run_root=run_root, copy_credentials=False
    )
    close_attempt_credential_home(home)
    close_attempt_credential_home(home)  # must not raise
    assert home.closed


def test_residue_detector_finds_a_planted_credential(tmp_path):
    """The detector must actually detect — otherwise 'cleaned up' is unverified."""
    run_root = str(tmp_path / "run")
    home = open_attempt_credential_home(
        attempt_id="ea-residue", run_root=run_root, copy_credentials=False
    )
    planted = os.path.join(home.claude_dir, ".credentials.json")
    with open(planted, "w", encoding="utf-8") as fh:
        fh.write("LEFTOVER")
    assert assert_no_credential_residue(run_root) == [planted]
    close_attempt_credential_home(home)
    assert assert_no_credential_residue(run_root) == []


def test_forced_cleanup_interruption_leaves_no_credential(tmp_path):
    """Interrupt mid-run: the finally-path must still destroy the credential."""
    run_root = str(tmp_path / "run")
    src = _fake_claude_dir(tmp_path, "TOKEN-INTERRUPT")
    home = open_attempt_credential_home(
        attempt_id="ea-int", run_root=run_root, source_claude_dir=src
    )

    def _work_then_interrupt():
        try:
            raise KeyboardInterrupt("operator cancelled mid-attempt")
        finally:
            close_attempt_credential_home(home)

    with pytest.raises(KeyboardInterrupt):
        _work_then_interrupt()
    assert not os.path.exists(home.home_path)
    assert assert_no_credential_residue(run_root) == []


def test_open_fails_closed_without_attempt_id(tmp_path):
    with pytest.raises(CredentialBoundaryError):
        open_attempt_credential_home(attempt_id="", run_root=str(tmp_path))


# ── 3. separate authority domains (control plane vs worker) ─────────────────


def test_control_plane_api_key_never_reaches_the_worker():
    """The candidate control plane holds ANTHROPIC_API_KEY. The worker must not
    receive it merely because both take part in the same run."""
    base = {
        "ANTHROPIC_API_KEY": "sk-ant-CONTROL-PLANE-KEY",
        "UMH_W2_DISPATCH_SECRET": "d" * 64,
        "UMH_MESH_RELAY_SECRET": "mesh",
        "OP_SERVICE_ACCOUNT_TOKEN": "op",
        "GITHUB_TOKEN": "gh",
        "DATABASE_URL": "postgres://x",
        "PATH": "/usr/bin",
        "HOME": "/root",
    }
    scrubbed = scrub_worker_env(base, extra_allow={"CLAUDE_CODE_OAUTH_TOKEN": "tok"})
    assert "ANTHROPIC_API_KEY" not in scrubbed, "control-plane key crossed into the worker"
    assert "UMH_W2_DISPATCH_SECRET" not in scrubbed, "worker must get NO signing secret"
    for k in ("UMH_MESH_RELAY_SECRET", "OP_SERVICE_ACCOUNT_TOKEN", "GITHUB_TOKEN", "DATABASE_URL"):
        assert k not in scrubbed, f"{k} must not reach the worker"
    assert scrubbed.get("CLAUDE_CODE_OAUTH_TOKEN") == "tok"
    assert "ANTHROPIC_API_KEY" in FORBIDDEN_ENV_PREFIXES


def test_api_key_is_never_written_into_an_attempt_home(tmp_path, monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-MUST-NOT-APPEAR")
    run_root = str(tmp_path / "run")
    src = _fake_claude_dir(tmp_path, "TOKEN-DOMAIN")
    home = open_attempt_credential_home(
        attempt_id="ea-domain", run_root=run_root, source_claude_dir=src
    )
    for dirpath, _d, files in os.walk(home.home_path):
        for name in files:
            body = open(os.path.join(dirpath, name), encoding="utf-8", errors="replace").read()
            assert "sk-ant-MUST-NOT-APPEAR" not in body
    close_attempt_credential_home(home)


# ── 4. the sandbox actually enforces it (REAL bwrap, no mocks) ──────────────


def _run_probe(profile: IsolationProfile, shell_cmd: str, env: dict | None = None):
    cmd = build_bwrap_command(["/bin/sh", "-c", shell_cmd], profile)
    return subprocess.run(  # noqa: S603 - test probe, fixed argv
        cmd,
        capture_output=True,
        text=True,
        timeout=60,
        env=env or {"PATH": "/usr/bin:/bin"},
    )


@_needs_bwrap
def test_worker_cannot_read_another_attempts_credential(tmp_path):
    """A runs under its own profile and tries to read B's credential file. The
    sandbox must not contain B's home at all."""
    run_root = str(tmp_path / "run")
    src = _fake_claude_dir(tmp_path, "B-SECRET-TOKEN")
    a = open_attempt_credential_home(attempt_id="ea-A", run_root=run_root, source_claude_dir=src)
    b = open_attempt_credential_home(attempt_id="ea-B", run_root=run_root, source_claude_dir=src)
    wt = tmp_path / "wt-a"
    wt.mkdir()

    profile = IsolationProfile(
        worktree_path=str(wt),
        worker_home=a.home_path,
        tmp_path=a.tmp_path,
        env_overrides=a.env_overrides(),
    )
    b_cred = os.path.join(b.claude_dir, ".credentials.json")
    r = _run_probe(profile, f"cat {b_cred} 2>/dev/null && echo LEAK || echo OK")
    assert "B-SECRET-TOKEN" not in (r.stdout or ""), "worker A read worker B's credential"
    assert "LEAK" not in (r.stdout or "")

    # And A cannot even enumerate the sibling homes directory.
    r2 = _run_probe(profile, f"ls {worker_homes_root(run_root)} 2>/dev/null || echo NOLIST")
    assert "ea-B" not in (r2.stdout or ""), "sibling attempt homes are enumerable"

    close_attempt_credential_home(a)
    close_attempt_credential_home(b)


@_needs_bwrap
def test_worker_can_read_its_own_credential(tmp_path):
    """Control for the test above: the boundary must not be so tight that the
    worker cannot authenticate — otherwise the previous test proves nothing."""
    run_root = str(tmp_path / "run")
    src = _fake_claude_dir(tmp_path, "MY-OWN-TOKEN")
    a = open_attempt_credential_home(attempt_id="ea-self", run_root=run_root, source_claude_dir=src)
    wt = tmp_path / "wt-self"
    wt.mkdir()
    profile = IsolationProfile(
        worktree_path=str(wt),
        worker_home=a.home_path,
        tmp_path=a.tmp_path,
        env_overrides=a.env_overrides(),
    )
    r = _run_probe(profile, 'cat "$HOME/.claude/.credentials.json"')
    assert "MY-OWN-TOKEN" in (r.stdout or ""), "worker cannot read its OWN credential"
    close_attempt_credential_home(a)


@_needs_bwrap
@pytest.mark.parametrize(
    "forbidden",
    ["/opt/OS", "/root/.ssh", "/root/.config/op", "/var/lib/umh"],
)
def test_worker_cannot_read_forbidden_host_paths(tmp_path, forbidden):
    """/opt/OS, host home, SSH and 1Password paths, candidate state."""
    run_root = str(tmp_path / "run")
    a = open_attempt_credential_home(
        attempt_id="ea-forbid", run_root=run_root, copy_credentials=False
    )
    wt = tmp_path / "wt-f"
    wt.mkdir()
    profile = IsolationProfile(
        worktree_path=str(wt),
        worker_home=a.home_path,
        tmp_path=a.tmp_path,
        env_overrides=a.env_overrides(),
    )
    r = _run_probe(profile, f"if [ -e {forbidden} ]; then echo LEAK; else echo OK; fi")
    assert "OK" in (r.stdout or ""), f"{forbidden} visible inside the sandbox: {r.stdout!r}"
    assert "LEAK" not in (r.stdout or "")
    close_attempt_credential_home(a)


@_needs_bwrap
def test_sandbox_env_points_config_inside_the_boundary(tmp_path):
    """HOME/CLAUDE_CONFIG_DIR/TMPDIR observed INSIDE the sandbox must be the
    attempt's own paths, not inherited host values."""
    run_root = str(tmp_path / "run")
    a = open_attempt_credential_home(
        attempt_id="ea-envprobe", run_root=run_root, copy_credentials=False
    )
    wt = tmp_path / "wt-e"
    wt.mkdir()
    profile = IsolationProfile(
        worktree_path=str(wt),
        worker_home=a.home_path,
        tmp_path=a.tmp_path,
        env_overrides=a.env_overrides(),
    )
    r = _run_probe(
        profile,
        'echo "H=$HOME"; echo "C=$CLAUDE_CONFIG_DIR"; echo "T=$TMPDIR"',
        env={"PATH": "/usr/bin:/bin", "HOME": "/root", "TMPDIR": "/tmp"},
    )
    out = r.stdout or ""
    assert f"H={a.home_path}" in out, out
    assert f"C={a.claude_dir}" in out, out
    assert f"T={a.tmp_path}" in out, out
    close_attempt_credential_home(a)


def test_worktree_parent_derivation_is_gone_from_the_source():
    """Guard the specific regression: the old shared-home derivation must not
    reappear in the worker."""
    src = open(
        os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "substrate",
            "execution",
            "attempts",
            "worker_claude_cli.py",
        ),
        encoding="utf-8",
    ).read()
    assert ".worker-home" not in src, "shared .worker-home derivation reintroduced"
    assert "open_attempt_credential_home" in src, "worker must use the per-attempt boundary"


def test_cleanup_failure_is_raised_not_warned(tmp_path, monkeypatch):
    """Cleanup failure must be a visible SECURITY failure, never a warning."""
    run_root = str(tmp_path / "run")
    home = open_attempt_credential_home(
        attempt_id="ea-stuck", run_root=run_root, copy_credentials=False
    )
    # Simulate an undeletable home (rmtree cannot remove it).
    monkeypatch.setattr(shutil, "rmtree", lambda *a, **k: None)
    with pytest.raises(CredentialBoundaryError, match="SECURITY FAILURE"):
        close_attempt_credential_home(home)
