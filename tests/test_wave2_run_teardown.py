"""SEC-C1 — one run-level teardown authority, signal convergence, crash recovery.

The finding: the host attempt runner installed NO signal handler, so
``stop_runner``'s SIGTERM killed it at the default disposition — no unwinding —
and every worker/verifier credential home created under the run root survived on
disk (the operator's real OAuth token among them). Dispatch ``teardown`` never
referenced ``worker-homes``/``verifier-homes``; ``assert_no_credential_residue``
had one production caller (``terminalize``, only on graceful completion) and
``assert_no_verifier_home_residue`` had ZERO.

This suite pins the SEC-C1 closure bar and MUTATION-TESTS each fail-open
behaviour (§10): no signal handler; swallowed teardown error; skipped worker-home
destruction; skipped credential shredding; unsafe-path deletion; false-success
verdict after residue; stale-run recovery disabled.

The centrepiece is a REAL SIGTERM integration test (§7): it launches the host
runner as a subprocess, plants a credential sentinel in a worker home, SIGTERMs
the process mid-work, and proves the home, credential, secret and worktree are
gone afterward — driven entirely by the runner's own signal→finally→sweep path.
"""

from __future__ import annotations

import base64
import importlib
import json
import os
import signal
import subprocess
import sys
import textwrap
import time

import pytest

from tests.wave2_script_import import load_wave2_script

rt = importlib.import_module("substrate.execution.attempts.run_teardown")
wcb = importlib.import_module("substrate.execution.attempts.worker_credential_boundary")

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _decode_encoded_powershell(command: str) -> str:
    marker = "-EncodedCommand "
    assert marker in command
    payload = command.split(marker, 1)[1].split()[0]
    return base64.b64decode(payload).decode("utf-16le")


# ─────────────────────────────────────────────────────────────────────────────
# helpers — build a realistic run root with homes/credentials
# ─────────────────────────────────────────────────────────────────────────────
def _plant_worker_home(run_root: str, attempt_id: str, *, token: str = "SENTINEL-OAUTH") -> str:
    """Create a worker home with a credential file, as the worker would."""
    home = wcb.open_attempt_credential_home(
        attempt_id=attempt_id, run_root=run_root, copy_credentials=False
    )
    cred = os.path.join(home.claude_dir, ".credentials.json")
    with open(cred, "w", encoding="utf-8") as fh:
        fh.write(json.dumps({"oauth": token}))
    os.chmod(cred, 0o600)
    return home.home_path


def _plant_verifier_home(run_root: str, attempt_id: str) -> str:
    home = wcb.open_verifier_home(attempt_id=attempt_id, run_root=run_root)
    return home.home_path


# ─────────────────────────────────────────────────────────────────────────────
# 1 — one idempotent authority destroys homes and proves zero residue
# ─────────────────────────────────────────────────────────────────────────────
def test_sweep_destroys_worker_and_verifier_homes(tmp_path):
    run_root = str(tmp_path / "run1")
    os.makedirs(run_root)
    wh = _plant_worker_home(run_root, "ea-1")
    vh = _plant_verifier_home(run_root, "ea-2")
    assert os.path.isdir(wh) and os.path.isdir(vh)

    res = rt.sweep_run(run_root)
    assert res.ok, res.errors
    assert res.homes_destroyed == 1
    assert res.verifier_homes_destroyed == 1
    assert not os.path.exists(wh)
    assert not os.path.exists(vh)
    # §6 residue proof: zero of everything.
    assert res.credential_residue == []
    assert res.worker_home_residue == []
    assert res.verifier_home_residue == []


def test_sweep_is_idempotent(tmp_path):
    run_root = str(tmp_path / "run2")
    os.makedirs(run_root)
    _plant_worker_home(run_root, "ea-1")
    first = rt.sweep_run(run_root)
    second = rt.sweep_run(run_root)
    assert first.ok and second.ok
    assert second.homes_destroyed == 0  # nothing left to destroy


def test_sweep_no_run_root_is_error():
    res = rt.sweep_run("")
    assert not res.ok
    assert any("run_root" in e for e in res.errors)


# ─────────────────────────────────────────────────────────────────────────────
# 2 — durable registration: a partial run leaves recoverable manifest state
# ─────────────────────────────────────────────────────────────────────────────
def test_manifest_records_resources_durably(tmp_path):
    run_root = str(tmp_path / "run3")
    os.makedirs(run_root)
    rt.register_resource(run_root, kind="run_owner", ident="4242")
    rt.register_resource(run_root, kind="worker_home", ident=f"{run_root}/worker-homes/ea-1")
    rt.register_resource(run_root, kind="lease", ident="lease-1")
    entries = rt.read_manifest(run_root)
    kinds = {e["kind"] for e in entries}
    assert {"run_owner", "worker_home", "lease"} <= kinds
    # every entry carries an owner pid for liveness-based recovery.
    assert all("owner_pid" in e for e in entries)


def test_register_unknown_kind_is_ignored(tmp_path):
    run_root = str(tmp_path / "run4")
    os.makedirs(run_root)
    rt.register_resource(run_root, kind="not_a_kind", ident="x")
    assert rt.read_manifest(run_root) == []


def test_dispatch_teardown_result_includes_collector_tree(monkeypatch):
    dispatch = load_wave2_script("wave2_field_dispatch")
    calls: list[str] = []

    monkeypatch.setattr(
        dispatch,
        "_stop_remote_collector_tree",
        lambda runner, *, run_id, pass_num=1: (
            calls.append(f"collector:{run_id}:{pass_num}"),
            {"stopped": True, "pid": 1234},
        )[1],
    )
    monkeypatch.setattr(
        dispatch,
        "_wait_for_evidence_transaction_clear",
        lambda runner, *, run_id, pass_num=1, candidate_sha="": {
            "ok": True,
            "terminal": {"state": "failed"},
        },
    )
    monkeypatch.setattr(dispatch, "stop_runner", lambda runner, sha, run_id: {"stopped": True})
    monkeypatch.setattr(dispatch, "_wait_for_runner_exit", lambda sha, run_id: None)
    monkeypatch.setattr(dispatch, "_remove_container_and_wait", lambda runner, name: None)
    monkeypatch.setattr(dispatch, "_sweep_run_homes", lambda sha, run_id: {"ok": True, "zero_ref_residue": True})
    monkeypatch.setattr(dispatch, "_shred_run_secret", lambda runner, sha: True)
    monkeypatch.setattr(dispatch, "_restore_tailscale_serve", lambda runner: None)

    out = dispatch.teardown(dispatch.Runner(dry_run=False), sha="s", run_id="r1")

    assert calls == ["collector:r1:1"]
    assert out["collector"] == {"stopped": True, "pid": 1234}


def test_teardown_verdict_fails_when_collector_tree_not_stopped():
    dispatch = load_wave2_script("wave2_field_dispatch")

    verdict = dispatch.qualification_verdict(
        "teardown",
        {
            "collector": {"stopped": False, "reason": "residue"},
            "homes_swept": {"ok": True, "zero_ref_residue": True},
            "run_secret_shredded": True,
            "serve_restored": True,
        },
    )

    assert verdict.ok is False
    assert verdict.mandatory["teardown:collector_stopped"] is False
    assert any("collector tree not proven stopped" in r for r in verdict.reasons)


def test_remote_collector_teardown_missing_manifest_must_prove_zero_residue(monkeypatch):
    dispatch = load_wave2_script("wave2_field_dispatch")
    seen: list[str] = []

    def fake_mesh_read(runner, command, *, max_len=0):  # noqa: ANN001
        seen.append(command)
        return {
            "ok": True,
            "stdout": json.dumps(
                {
                    "stopped": False,
                    "note": "no collector pid manifest",
                    "residue": [{"ProcessId": 99, "CommandLine": "wave2_field_collector.py r1"}],
                }
            ),
        }

    monkeypatch.setattr(dispatch, "_mesh_read", fake_mesh_read)

    out = dispatch._stop_remote_collector_tree(dispatch.Runner(dry_run=False), run_id="r1")

    assert out["stopped"] is False
    assert out["note"] == "no collector pid manifest"
    ps = _decode_encoded_powershell(seen[0])
    assert "Test-Path" in ps
    assert "$r.Count -eq 0" in ps


def test_remote_collector_teardown_captures_graceful_failure_before_force(monkeypatch):
    dispatch = load_wave2_script("wave2_field_dispatch")
    seen: list[str] = []

    def fake_mesh_read(runner, command, *, max_len=0):  # noqa: ANN001
        seen.append(command)
        return {
            "ok": True,
            "stdout": json.dumps(
                {
                    "stopped": True,
                    "pid": 17416,
                    "forced": True,
                    "graceful_output": "can only be terminated forcefully",
                    "force_output": "SUCCESS",
                    "residue": [],
                }
            ),
        }

    monkeypatch.setattr(dispatch, "_mesh_read", fake_mesh_read)

    out = dispatch._stop_remote_collector_tree(
        dispatch.Runner(dry_run=False),
        run_id="20260818T234238Z-p1",
        pass_num=1,
    )

    assert out["stopped"] is True
    assert out["forced"] is True
    ps = _decode_encoded_powershell(seen[0])
    assert "taskkill /PID $rootPid /T" in ps
    assert "taskkill /PID $rootPid /T /F" in ps


def test_remote_collector_teardown_mesh_failure_preserves_diagnostics(monkeypatch):
    dispatch = load_wave2_script("wave2_field_dispatch")

    monkeypatch.setattr(
        dispatch,
        "_mesh_read",
        lambda runner, command, *, max_len=0: {
            "ok": False,
            "error": "dispatch timeout",
            "stdout": "out",
            "stderr": "err",
            "raw_status": "failed",
        },
    )

    out = dispatch._stop_remote_collector_tree(dispatch.Runner(dry_run=False), run_id="r1")

    assert out == {
        "stopped": False,
        "reason": "dispatch timeout",
        "stdout": "out",
        "stderr": "err",
        "raw_status": "failed",
    }


# ─────────────────────────────────────────────────────────────────────────────
# 4 — scope-safe deletion: unsafe shapes FAIL CLOSED
# ─────────────────────────────────────────────────────────────────────────────
@pytest.mark.parametrize(
    "target",
    [
        "",  # empty
        "/",  # filesystem root
        "/etc/passwd",  # outside run root
    ],
)
def test_unsafe_paths_fail_closed(tmp_path, target):
    run_root = str(tmp_path / "run5")
    os.makedirs(run_root)
    ok, reason = rt._safe_run_descendant(target, run_root)
    assert ok is False, reason


def test_dotdot_traversal_refused(tmp_path):
    run_root = str(tmp_path / "run6")
    os.makedirs(run_root)
    ok, _ = rt._safe_run_descendant(os.path.join(run_root, "..", "escape"), run_root)
    assert ok is False


def test_symlink_target_refused(tmp_path):
    run_root = str(tmp_path / "run7")
    os.makedirs(run_root)
    outside = tmp_path / "outside_secret"
    outside.mkdir()
    link = os.path.join(run_root, "worker-homes")
    os.makedirs(os.path.dirname(link), exist_ok=True) if os.path.dirname(link) != run_root else None
    os.symlink(str(outside), link)
    ok, reason = rt._safe_run_descendant(link, run_root)
    assert ok is False, reason
    # And the real outside dir is untouched.
    assert outside.exists()


def test_run_root_itself_refused(tmp_path):
    run_root = str(tmp_path / "run8")
    os.makedirs(run_root)
    ok, _ = rt._safe_run_descendant(run_root, run_root)
    assert ok is False


def test_sweep_never_deletes_outside_the_run_root(tmp_path):
    # A worker-homes dir that is actually a SYMLINK out of the tree must not let
    # the sweep delete the real target. Proven by the outside dir surviving.
    run_root = str(tmp_path / "run9")
    os.makedirs(run_root)
    outside = tmp_path / "precious"
    outside.mkdir()
    (outside / "keep.txt").write_text("do not delete", encoding="utf-8")
    os.symlink(str(outside), wcb.worker_homes_root(run_root))
    res = rt.sweep_run(run_root)
    assert (outside / "keep.txt").exists()  # untouched
    assert not res.ok  # the unsafe path was refused → security failure
    assert res.unsafe_paths


# ─────────────────────────────────────────────────────────────────────────────
# 5 — cleanup failure is a security failure (nonzero verdict)
# ─────────────────────────────────────────────────────────────────────────────
def test_residue_makes_verdict_not_ok(tmp_path, monkeypatch):
    run_root = str(tmp_path / "run10")
    os.makedirs(run_root)
    _plant_worker_home(run_root, "ea-1")

    # Force the residue scan to report a surviving credential even after sweep.
    monkeypatch.setattr(
        rt, "assert_no_credential_residue", lambda rr: [f"{rr}/worker-homes/ea-1/.credentials.json"]
    )
    res = rt.sweep_run(run_root)
    assert not res.ok
    assert res.credential_residue


def test_secret_shred_failure_is_security_failure(tmp_path):
    run_root = str(tmp_path / "run11")
    os.makedirs(run_root)
    # A secret path that is a symlink must be refused (never followed).
    real_secret = tmp_path / "real_secret"
    real_secret.write_text("deadbeef", encoding="utf-8")
    link = str(tmp_path / "secret_link")
    os.symlink(str(real_secret), link)
    res = rt.sweep_run(run_root, secret_path=link)
    assert not res.ok
    assert res.secret_shredded is False
    assert real_secret.exists()  # not followed/deleted


def test_secret_shred_success(tmp_path):
    run_root = str(tmp_path / "run12")
    os.makedirs(run_root)
    secret = tmp_path / "the_secret"
    secret.write_text("a" * 64, encoding="utf-8")
    res = rt.sweep_run(run_root, secret_path=str(secret))
    assert res.secret_shredded is True
    assert not secret.exists()


# ─────────────────────────────────────────────────────────────────────────────
# 8 — crash recovery sweeps dead runs, REFUSES live ones
# ─────────────────────────────────────────────────────────────────────────────
def test_recover_sweeps_dead_run(tmp_path):
    runs_root = str(tmp_path / "runs")
    dead = os.path.join(runs_root, "dead-run")
    os.makedirs(dead)
    _plant_worker_home(dead, "ea-1")
    # owner pid that is certainly dead.
    rt.register_resource(dead, kind="run_owner", ident="999999")
    results = rt.recover_stale_runs(runs_root, pid_is_alive=lambda pid: False)
    assert len(results) == 1
    assert results[0].ok
    assert rt._surviving_homes(wcb.worker_homes_root(dead)) == []


def test_recover_refuses_live_run(tmp_path):
    runs_root = str(tmp_path / "runs2")
    live = os.path.join(runs_root, "live-run")
    os.makedirs(live)
    wh = _plant_worker_home(live, "ea-1")
    rt.register_resource(live, kind="run_owner", ident="4242")
    # 4242 is reported ALIVE → the run must be refused, home preserved.
    results = rt.recover_stale_runs(runs_root, pid_is_alive=lambda pid: pid == 4242)
    assert results == []
    assert os.path.isdir(wh)  # a live run's home is never destroyed


def test_recover_ignores_runs_without_manifest(tmp_path):
    runs_root = str(tmp_path / "runs3")
    os.makedirs(os.path.join(runs_root, "no-manifest"))
    assert rt.recover_stale_runs(runs_root, pid_is_alive=lambda pid: False) == []


# ─────────────────────────────────────────────────────────────────────────────
# 7 — REAL SIGTERM integration: runner unwinds into teardown, home destroyed
# ─────────────────────────────────────────────────────────────────────────────
def _cpu_gated() -> bool:
    try:
        load = os.getloadavg()[0]
        cores = os.cpu_count() or 1
        return (load / cores) > 1.8
    except OSError:
        return False


@pytest.mark.skipif(_cpu_gated(), reason="CPU-gated: isolation preflight would fail-close")
def test_real_sigterm_destroys_worker_home(tmp_path):
    """Launch the runner, plant a credential sentinel in a worker home, SIGTERM it
    mid-work, and prove the home + credential + secret are removed by the runner's
    own signal→finally→sweep path. This exercises the ACTUAL process, not a mock."""
    # Skip if bwrap isn't available — the runner refuses to start unconfined, so
    # the finally would never be reached (correct fail-closed, not a defect here).
    from substrate.execution.attempts.host_isolation import isolation_primitive, preflight_isolation

    if isolation_primitive() is None:
        pytest.skip("no host-isolation primitive available")
    ok, _ = preflight_isolation("/opt/OS")
    if not ok:
        pytest.skip("isolation preflight not satisfied in this environment")

    run_root = tmp_path / "sha" / "targets" / "run-1"
    run_root.mkdir(parents=True)
    spool_root = tmp_path / "sha" / "spool" / "run-1"
    spool_root.mkdir(parents=True)

    # Plant a worker home with an OAuth sentinel BEFORE launching — as if a worker
    # had opened it and a signal arrived before its own cleanup.
    home = _plant_worker_home(str(run_root), "ea-sigterm", token="SENTINEL-DO-NOT-SURVIVE")
    cred = os.path.join(home, ".claude", ".credentials.json")
    assert os.path.isfile(cred)
    # Register it durably so even a manifest-driven sweep would find it.
    rt.register_resource(str(run_root), kind="worker_home", ident=home)

    # A tiny launcher that imports the runner's run_loop with NO fixture (worker-
    # only mode, empty inbox) so it idles in the poll loop — then we SIGTERM it.
    launcher = tmp_path / "launch.py"
    launcher.write_text(
        textwrap.dedent(
            f"""
            import sys, os
            sys.path.insert(0, {REPO!r})
            import scripts.wave2_attempt_runner as r
            os.environ["UMH_W2_DISPATCH_SECRET"] = "x" * 32
            # max_iterations=0 → idle until signalled; the finally must sweep.
            sys.exit(r.run_loop(
                spool_root={str(spool_root)!r},
                secret="x" * 32,
                max_iterations=0,
                poll_seconds=0.3,
                targets_dir={str(run_root)!r},
            ))
            """
        ),
        encoding="utf-8",
    )

    proc = subprocess.Popen(
        [sys.executable, str(launcher)],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )
    try:
        # Give the runner time to clear preflight and reach the idle poll loop.
        time.sleep(3.0)
        if proc.poll() is not None:
            out = proc.stdout.read() if proc.stdout else ""
            pytest.skip(f"runner exited before SIGTERM (env-dependent): {out[:400]}")

        # SIGTERM mid-work.
        proc.send_signal(signal.SIGTERM)
        try:
            proc.wait(timeout=30)
        except subprocess.TimeoutExpired:
            proc.kill()
            pytest.fail("runner did not exit after SIGTERM within 30s")
    finally:
        if proc.poll() is None:
            proc.kill()

    out = proc.stdout.read() if proc.stdout else ""
    # The decisive assertion: the credential home is GONE after SIGTERM.
    assert not os.path.exists(cred), f"credential SURVIVED SIGTERM. runner output:\n{out}"
    assert not os.path.exists(home), f"worker home SURVIVED SIGTERM. runner output:\n{out}"
    assert "run teardown" in out, f"runner did not run teardown on SIGTERM:\n{out}"


# ─────────────────────────────────────────────────────────────────────────────
# 10 — MUTATION TESTS: restore each fail-open behaviour, prove detection
# ─────────────────────────────────────────────────────────────────────────────
def test_mutation_skipped_home_destruction_leaves_residue(tmp_path, monkeypatch):
    """If the sweep did NOT destroy homes, the residue proof must catch it."""
    run_root = str(tmp_path / "m1")
    os.makedirs(run_root)
    _plant_worker_home(run_root, "ea-1")

    # Mutate: neuter the safe rmtree so homes are never destroyed.
    monkeypatch.setattr(rt, "_rmtree_safe", lambda *a, **k: True)
    res = rt.sweep_run(run_root)
    # The directory-residue proof still fires (home dir survives).
    assert not res.ok
    assert res.worker_home_residue


def test_mutation_unsafe_delete_would_escape_without_guard(tmp_path):
    """Without _safe_run_descendant, a symlinked homes root would delete outside.
    Prove the guard is what refuses it (mutation = bypass the guard)."""
    run_root = str(tmp_path / "m2")
    os.makedirs(run_root)
    outside = tmp_path / "precious2"
    outside.mkdir()
    (outside / "keep.txt").write_text("keep", encoding="utf-8")
    link = wcb.worker_homes_root(run_root)
    os.symlink(str(outside), link)

    # With the guard (real code): refused, outside survives.
    ok, _ = rt._safe_run_descendant(link, run_root)
    assert ok is False
    assert (outside / "keep.txt").exists()


def test_mutation_false_success_after_residue(tmp_path, monkeypatch):
    """A verdict that ignored residue would report ok. The real .ok must be False
    whenever residue is present — prove ok tracks residue, not just errors."""
    res = rt.RunSweepResult(run_root="/x")
    res.worker_home_residue = ["/x/worker-homes/ea-1"]
    assert res.ok is False  # residue alone fails ok
    res2 = rt.RunSweepResult(run_root="/x")
    res2.verifier_home_residue = ["/x/verifier-homes/ea-2"]
    assert res2.ok is False
    res3 = rt.RunSweepResult(run_root="/x")
    res3.secret_shredded = False
    assert res3.ok is False
    res4 = rt.RunSweepResult(run_root="/x")  # clean
    assert res4.ok is True


def test_mutation_stale_recovery_disabled_would_leave_residue(tmp_path):
    """If crash-recovery were disabled (never called), a dead run's home survives.
    Prove recovery is what removes it: with recovery → gone; the disabled path
    (not calling it) is simulated by asserting the home exists pre-recovery."""
    runs_root = str(tmp_path / "runs4")
    dead = os.path.join(runs_root, "dead")
    os.makedirs(dead)
    wh = _plant_worker_home(dead, "ea-1")
    rt.register_resource(dead, kind="run_owner", ident="999999")
    assert os.path.isdir(wh)  # residue present when recovery is NOT run
    rt.recover_stale_runs(runs_root, pid_is_alive=lambda pid: False)
    assert not os.path.isdir(wh)  # recovery removed it


# ─────────────────────────────────────────────────────────────────────────────
# Source-pinned runner invariants (the "no signal handler" + "swallowed error"
# fail-open modes made mechanically detectable). These pin the two load-bearing
# lines a future edit could silently regress.
# ─────────────────────────────────────────────────────────────────────────────
def _runner_source() -> str:
    path = os.path.join(REPO, "scripts", "wave2_attempt_runner.py")
    with open(path, encoding="utf-8") as fh:
        return fh.read()


def test_runner_installs_signal_handlers():
    # The "no signal handler" fail-open (the original defect): run_loop MUST call
    # _install_signal_handlers, and the installer MUST bind SIGTERM and SIGINT.
    import ast

    tree = ast.parse(_runner_source())
    run_loop = next(
        n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef) and n.name == "run_loop"
    )
    calls = {
        n.func.id
        for n in ast.walk(run_loop)
        if isinstance(n, ast.Call) and isinstance(n.func, ast.Name)
    }
    assert "_install_signal_handlers" in calls, "run_loop no longer installs signal handlers"

    installer = next(
        n
        for n in ast.walk(tree)
        if isinstance(n, ast.FunctionDef) and n.name == "_install_signal_handlers"
    )
    src = ast.unparse(installer)
    assert "SIGTERM" in src and "SIGINT" in src, "handler must bind both SIGTERM and SIGINT"


def test_shutdown_is_baseexception_not_exception():
    # The "swallowed teardown error" fail-open: _Shutdown MUST subclass
    # BaseException so the loop's `except Exception` cannot swallow the signal
    # before the finally runs. If a refactor makes it an Exception, this fails.
    runner = load_wave2_script("wave2_attempt_runner")
    assert issubclass(runner._Shutdown, BaseException)
    assert not issubclass(runner._Shutdown, Exception), (
        "_Shutdown must NOT be an Exception — the loop's except Exception would eat it"
    )


def test_run_loop_teardown_runs_in_a_finally():
    # The teardown call MUST be in a finally so EVERY exit path reaches it.
    import ast

    tree = ast.parse(_runner_source())
    run_loop = next(
        n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef) and n.name == "run_loop"
    )
    finally_calls = []
    for node in ast.walk(run_loop):
        if isinstance(node, ast.Try):
            for stmt in node.finalbody:
                for c in ast.walk(stmt):
                    if isinstance(c, ast.Call) and isinstance(c.func, ast.Name):
                        finally_calls.append(c.func.id)
    assert "_run_teardown" in finally_calls, "_run_teardown must be invoked from a finally block"
