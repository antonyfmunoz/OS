from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SUPERVISOR = ROOT / "nodes" / "windows" / "umh_node" / "task_supervisor.ps1"
STOPPER = ROOT / "nodes" / "windows" / "umh_node" / "stop_daemon.ps1"
INSTALLER = ROOT / "nodes" / "windows" / "umh_node" / "install_task.ps1"
SERVICE = ROOT / "nodes" / "windows" / "umh_node" / "service.py"
RECONCILER = ROOT / "scripts" / "wave2_beast_reconciler.py"


def _text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def test_task_supervisor_owns_op_run_in_kill_on_close_job() -> None:
    body = _text(SUPERVISOR)

    assert "CreateJobObject" in body
    assert "SetInformationJobObject" in body
    assert "AssignProcessToJobObject" in body
    assert "JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE" in body
    assert "op.exe" in body
    assert "run" in body
    assert "--env-file=$EnvTemplate" in body
    assert "Quote-Arg" in body
    assert "pythonw.exe" in body
    assert "launcher.py" in body
    assert "taskkill /IM" not in body
    assert "Stop-Process -Name" not in body


def test_installer_makes_powershell_supervisor_the_task_action() -> None:
    body = _text(INSTALLER)

    assert "task_supervisor.ps1" in body
    assert "New-ScheduledTaskAction" in body
    assert '-Execute "powershell.exe"' in body
    assert "-WorkingDirectory $runRoot" in body
    assert "op run" not in body.lower()
    assert "pythonw.exe" not in body.lower()


def test_stop_helper_attempts_graceful_event_before_scheduler_end() -> None:
    body = _text(STOPPER)

    assert "OpenEvent" in body
    assert "SetEvent" in body
    assert "schtasks /End" in body
    assert "nodes\\\\windows\\\\umh_node\\\\launcher\\.py" in body
    assert "taskkill /IM" not in body
    assert "Stop-Process -Name" not in body
    assert "/PID" not in body


def test_service_listens_for_supervisor_stop_event() -> None:
    body = _text(SERVICE)

    assert "UMH_DAEMON_STOP_EVENT" in body
    assert "OpenEventW" in body
    assert "WaitForSingleObject" in body
    assert "client.stop()" in body


def test_reconciler_uses_canonical_stop_helper_not_pid_force_kill() -> None:
    body = _text(RECONCILER)

    assert "stop_daemon.ps1" in body
    assert "stop_task" in body
    assert "taskkill /PID" not in body
    assert "terminate every launcher.py process" not in body
