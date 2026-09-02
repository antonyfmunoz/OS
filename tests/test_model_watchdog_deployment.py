from __future__ import annotations

import ast
import json
import os
import pathlib
import subprocess


ROOT = pathlib.Path(__file__).resolve().parents[1]


def test_model_watchdog_unit_executes_deployed_artifact_outside_git_worktree():
    unit = (ROOT / "infra/systemd/umh-model-watchdog.service").read_text(encoding="utf-8")
    assert "ExecStart=/usr/bin/python3 /opt/umh/runtime/model-watchdog/current/model_watchdog.py" in unit
    assert "ExecStart=/usr/bin/python3 /opt/OS/scripts/model-watchdog.py" not in unit
    assert "WorkingDirectory=/opt/umh/runtime/model-watchdog/current" in unit


def test_model_watchdog_installer_supports_install_verify_and_rollback():
    script = (ROOT / "scripts/install-model-watchdog.sh").read_text(encoding="utf-8")
    assert "--install)" in script
    assert "--verify)" in script
    assert "--rollback)" in script
    assert "sha256sum" in script
    assert "MANIFEST.json" in script
    assert "UMH_MODEL_WATCHDOG_RUNTIME_ROOT" in script
    assert "UMH_MODEL_WATCHDOG_SYSTEMCTL" in script
    assert "restart umh-model-watchdog.service" in script


def test_model_watchdog_installer_install_verify_and_rollback_are_hermetic(tmp_path):
    runtime = tmp_path / "runtime"
    repo_root = tmp_path / "repo"
    (repo_root / "services").mkdir(parents=True)
    (repo_root / "infra/systemd").mkdir(parents=True)
    (repo_root / "substrate/execution").mkdir(parents=True)
    source = repo_root / "services/model_watchdog.py"
    source.write_text((ROOT / "services/model_watchdog.py").read_text(encoding="utf-8"), encoding="utf-8")
    (repo_root / "substrate/execution/cpu_gate.py").write_text(
        (ROOT / "substrate/execution/cpu_gate.py").read_text(encoding="utf-8"),
        encoding="utf-8",
    )
    unit_source = repo_root / "infra/systemd/umh-model-watchdog.service"
    unit_source.write_text(
        (ROOT / "infra/systemd/umh-model-watchdog.service").read_text(encoding="utf-8"),
        encoding="utf-8",
    )
    unit_dest = tmp_path / "umh-model-watchdog.service"
    fake_systemctl = tmp_path / "systemctl"
    fake_systemctl.write_text(
        "#!/bin/sh\n"
        "echo \"$@\" >> \"$UMH_FAKE_SYSTEMCTL_LOG\"\n"
        "exit 0\n",
        encoding="utf-8",
    )
    fake_systemctl.chmod(0o755)
    env = {
        **os.environ,
        "UMH_MODEL_WATCHDOG_RUNTIME_ROOT": str(runtime),
        "UMH_MODEL_WATCHDOG_UNIT_DEST": str(unit_dest),
        "UMH_MODEL_WATCHDOG_SYSTEMCTL": str(fake_systemctl),
        "UMH_FAKE_SYSTEMCTL_LOG": str(tmp_path / "systemctl.log"),
        "UMH_REPO_ROOT": str(repo_root),
    }
    installer = ROOT / "scripts/install-model-watchdog.sh"

    env["UMH_MODEL_WATCHDOG_DEPLOYMENT_ID"] = "release-one"
    subprocess.run(["bash", str(installer), "--install"], cwd=ROOT, env=env, check=True)
    first = runtime / "releases" / "release-one"
    assert (first / "model_watchdog.py").is_file()
    assert (first / "substrate/execution/cpu_gate.py").is_file()
    manifest = json.loads((first / "MANIFEST.json").read_text(encoding="utf-8"))
    assert manifest["deployment_id"] == "release-one"
    assert manifest["runtime_path"] == str(first / "model_watchdog.py")
    assert manifest["cpu_gate_sha256"]
    assert os.path.realpath(runtime / "current") == str(first)

    original_source = source.read_text(encoding="utf-8")
    source.write_text(original_source + "\n# rollback test release mutation\n", encoding="utf-8")
    env["UMH_MODEL_WATCHDOG_DEPLOYMENT_ID"] = "release-two"
    subprocess.run(["bash", str(installer), "--install"], cwd=ROOT, env=env, check=True)
    second = runtime / "releases" / "release-two"
    assert (second / "model_watchdog.py").is_file()
    assert (first / "model_watchdog.py").is_file(), "install must preserve old releases"
    assert (first / "model_watchdog.py").read_bytes() != (second / "model_watchdog.py").read_bytes()
    assert os.path.realpath(runtime / "current") == str(second)

    subprocess.run(["bash", str(installer), "--verify"], cwd=ROOT, env=env, check=True)
    subprocess.run(["bash", str(installer), "--rollback", "release-one"], cwd=ROOT, env=env, check=True)
    assert os.path.realpath(runtime / "current") == str(first)
    log = (tmp_path / "systemctl.log").read_text(encoding="utf-8")
    assert "daemon-reload" in log
    assert "restart umh-model-watchdog.service" in log
    assert "is-active --quiet umh-model-watchdog.service" in log


def test_model_watchdog_health_contains_runtime_version_observability():
    source = (ROOT / "services/model_watchdog.py").read_text(encoding="utf-8")
    tree = ast.parse(source)
    health = next(
        node for node in tree.body if isinstance(node, ast.ClassDef) and node.name == "HealthCounters"
    )
    fields = {
        stmt.target.id
        for stmt in health.body
        if isinstance(stmt, ast.AnnAssign) and isinstance(stmt.target, ast.Name)
    }
    assert {
        "watchdog_version",
        "source_commit",
        "deployment_id",
        "runtime_path",
        "runtime_sha256",
        "unit_sha256",
    } <= fields
    assert "_deployment_manifest" in source
    assert "MANIFEST.json" in source


def test_model_watchdog_runtime_does_not_import_model_executor_boundary():
    source = (ROOT / "services/model_watchdog.py").read_text(encoding="utf-8")
    assert "model_executor" not in source
    assert "worker_model_executor" not in source


def test_model_watchdog_pause_suppresses_claude_discovery():
    source = (ROOT / "services/model_watchdog.py").read_text(encoding="utf-8")
    assert "Claude discovery and remediation suppressed" in source
    run_start = source.index("    def run(self) -> None:")
    run_source = source[run_start:]
    assert "if not self._is_paused():\n            changed, detail = self._ensure_settings_model()" in run_source
    assert source.index("if self._is_paused():") < source.index("sessions = self._get_active_sessions()")
