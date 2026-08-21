"""Wave 2 C4 part 2 — host isolation, signed dispatch spool, real worker guards."""

from __future__ import annotations

import os
import subprocess

import pytest

from substrate.execution.attempts.host_isolation import (
    IsolationProfile,
    build_isolated_command,
    isolation_primitive,
    preflight_isolation,
    scrub_worker_env,
)
from substrate.execution.attempts.spool import DispatchEnvelope, DispatchSpool

# ── Host isolation (clause 4) ────────────────────────────────────────────────


def test_isolation_primitive_available():
    # This environment must have a real isolation primitive for qualification.
    assert isolation_primitive() is not None


@pytest.mark.skipif(isolation_primitive() != "bwrap", reason="bwrap-specific probe")
def test_preflight_hides_opt_os():
    ok, detail = preflight_isolation("/opt/OS")
    assert ok, detail
    assert "hidden" in detail


def test_env_scrub_strips_all_credentials():
    dirty = {
        "PATH": "/usr/bin",
        "HOME": "/home/x",
        "GIT_AUTHOR_NAME": "w",
        "OP_SERVICE_ACCOUNT_TOKEN": "s",
        "FLY_API_TOKEN": "s",
        "GITHUB_TOKEN": "s",
        "DISCORD_BOT_TOKEN": "s",
        "UMH_MESH_RELAY_SECRET": "s",
        "ANTHROPIC_API_KEY": "s",
        "AWS_SECRET_ACCESS_KEY": "s",
        "DATABASE_URL": "s",
        "SSH_AUTH_SOCK": "s",
    }
    clean = scrub_worker_env(dirty, extra_allow={"CLAUDE_CODE_OAUTH_TOKEN": "tok"})
    assert set(clean) == {"PATH", "HOME", "GIT_AUTHOR_NAME", "CLAUDE_CODE_OAUTH_TOKEN"}
    for forbidden in (
        "OP_SERVICE_ACCOUNT_TOKEN",
        "FLY_API_TOKEN",
        "GITHUB_TOKEN",
        "DISCORD_BOT_TOKEN",
        "UMH_MESH_RELAY_SECRET",
        "ANTHROPIC_API_KEY",
        "AWS_SECRET_ACCESS_KEY",
        "DATABASE_URL",
        "SSH_AUTH_SOCK",
    ):
        assert forbidden not in clean


def test_isolated_command_wraps_inner(tmp_path):
    wt = str(tmp_path / "wt")
    home = str(tmp_path / "home")
    os.makedirs(wt)
    os.makedirs(home)
    profile = IsolationProfile(worktree_path=wt, worker_home=home)
    cmd = build_isolated_command(["echo", "hi"], profile)
    # The inner command is wrapped by the isolation primitive.
    assert cmd[0] in ("bwrap", "systemd-run", "nsjail")
    assert "echo" in cmd and "hi" in cmd


@pytest.mark.skipif(isolation_primitive() != "bwrap", reason="bwrap-specific capability denial")
def test_worktree_readonly_capability_denial_blocks_shell_writes(tmp_path):
    wt = tmp_path / "wt"
    home = tmp_path / "home"
    wt.mkdir()
    home.mkdir()
    target = wt / "app.py"
    target.write_text("original\n", encoding="utf-8")

    profile = IsolationProfile(
        worktree_path=str(wt),
        worker_home=str(home),
        worktree_readonly=True,
    )
    cmd = build_isolated_command(
        ["sh", "-c", f"set -e; printf hacked > {target}; cat {target}"],
        profile,
    )
    proc = subprocess.run(cmd, capture_output=True, text=True, timeout=30)

    assert proc.returncode != 0
    assert target.read_text(encoding="utf-8") == "original\n"


@pytest.mark.skipif(isolation_primitive() != "bwrap", reason="bwrap-specific capability denial")
def test_worktree_readonly_capability_denial_rejects_writable_reopen(tmp_path):
    wt = tmp_path / "wt"
    home = tmp_path / "home"
    wt.mkdir()
    home.mkdir()
    profile = IsolationProfile(
        worktree_path=str(wt),
        worker_home=str(home),
        worktree_readonly=True,
        writable_subpaths=[str(wt / ".git" / "refs" / "attempt" / "ea-1")],
    )

    with pytest.raises(Exception, match="worktree_readonly profiles cannot re-open"):
        build_isolated_command(["true"], profile)


# ── Signed dispatch spool (clause 3) ─────────────────────────────────────────


@pytest.fixture()
def spool(tmp_path):
    return DispatchSpool(str(tmp_path / "spool"), secret="run-secret-123")


def _env(seq=1, dispatch_id="d1", **kw):
    base = dict(
        dispatch_id=dispatch_id,
        attempt_id="ea-1",
        task_id="wp-a",
        authorization_ref="ref",
        package_hash="ph",
        lease_id="l1",
        worktree_path="/tmp/wt",
        nonce="n1",
        sequence=seq,
        payload_hash="p1",
        # Every real dispatch carries the sealed writable scope (finding F-2);
        # the transport quarantines an envelope that cannot express enforceable
        # write authority. A fixture without it is not a "simpler" dispatch — it
        # is one production can no longer produce.
        governance_constraints=["writable_path_scope=['app/main.py']"],
    )
    base.update(kw)
    return DispatchEnvelope(**base)


def test_enqueue_claim_roundtrip(spool):
    spool.enqueue(_env())
    claimed = spool.claim_next()
    assert claimed is not None
    token, env = claimed
    assert env.attempt_id == "ea-1"
    # Inbox is now empty (claimed into inflight).
    assert spool.claim_next() is None


def test_tampered_envelope_is_quarantined(tmp_path):
    sp = DispatchSpool(str(tmp_path / "s"), secret="secret")
    name = sp.enqueue(_env())
    # Tamper with the signed file directly.
    import json

    p = os.path.join(tmp_path / "s", "inbox", name)
    with open(p) as f:
        rec = json.load(f)
    rec["envelope"]["task_id"] = "wp-HIJACK"  # signature no longer matches
    with open(p, "w") as f:
        json.dump(rec, f)
    assert sp.claim_next() is None  # tampered → quarantined, not returned
    assert os.listdir(os.path.join(tmp_path / "s", "quarantine"))


def test_wrong_secret_rejects(tmp_path):
    producer = DispatchSpool(str(tmp_path / "s"), secret="real")
    producer.enqueue(_env())
    consumer = DispatchSpool(str(tmp_path / "s"), secret="WRONG")
    assert consumer.claim_next() is None  # bad signature under wrong secret


def test_expired_envelope_quarantined(spool):
    spool.enqueue(_env(expires_at=1.0))  # long past
    assert spool.claim_next() is None


def test_result_roundtrip_and_signature(spool):
    spool.enqueue(_env())
    token, env = spool.claim_next()
    spool.complete(token, {"attempt_id": "ea-1", "status": "succeeded"})
    results = spool.drain_results()
    assert len(results) == 1
    assert results[0]["attempt_id"] == "ea-1"
    # Drained once — gone now.
    assert spool.drain_results() == []


def test_tampered_result_quarantined(tmp_path):
    sp = DispatchSpool(str(tmp_path / "s"), secret="secret")
    sp.enqueue(_env())
    token, env = sp.claim_next()
    sp.complete(token, {"status": "failed"})
    # Tamper the outbox result.
    import json

    outdir = os.path.join(tmp_path / "s", "outbox")
    name = os.listdir(outdir)[0]
    with open(os.path.join(outdir, name)) as f:
        rec = json.load(f)
    rec["result"]["status"] = "succeeded"  # signature mismatch
    with open(os.path.join(outdir, name), "w") as f:
        json.dump(rec, f)
    assert sp.drain_results() == []  # tampered → quarantined
    assert os.listdir(os.path.join(tmp_path / "s", "quarantine"))


def test_spool_never_infers_status_only_transports():
    # The spool exposes envelopes/results, not operator status — there is no
    # "is this attempt done" method on the spool. Status comes from the store.
    assert not hasattr(DispatchSpool, "attempt_status")
    assert not hasattr(DispatchSpool, "is_complete")


# ── Real worker guards (no simulation fallback) ──────────────────────────────


def test_worker_fails_closed_without_cli(tmp_path, monkeypatch):
    from types import SimpleNamespace

    from substrate.execution.attempts import worker_claude_cli

    monkeypatch.setattr(worker_claude_cli, "_resolve_cli_path", lambda: "")
    wt = tmp_path / "wt"
    wt.mkdir()
    lease = SimpleNamespace(worktree_path=str(wt), snapshot_ref="HEAD")
    result = worker_claude_cli.run_worker_in_lease(package=SimpleNamespace(), lease=lease)
    assert result.ok is False
    assert "no simulation fallback" in result.error
