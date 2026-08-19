from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SUPERVISOR = ROOT / "nodes" / "windows" / "umh_node" / "task_supervisor.ps1"
CHILD_SUPERVISOR = ROOT / "nodes" / "windows" / "umh_node" / "daemon_child.ps1"
STOPPER = ROOT / "nodes" / "windows" / "umh_node" / "stop_daemon.ps1"
INSTALLER = ROOT / "nodes" / "windows" / "umh_node" / "install_task.ps1"
SERVICE = ROOT / "nodes" / "windows" / "umh_node" / "service.py"
RECONCILER = ROOT / "scripts" / "wave2_beast_reconciler.py"
CLIENT = ROOT / "nodes" / "windows" / "umh_node" / "client.py"


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
    assert "daemon_child.ps1" in body
    assert "powershell.exe" in body
    assert "Quote-Arg" in body
    assert "Resolve-RealPythonw" in body
    assert "WindowsApps" in body
    assert "UMH_PYTHONW_PATH" in body
    assert "pythonw.exe" in body
    assert "launcher.py" in body
    assert "taskkill /IM" not in body
    assert "Stop-Process -Name" not in body


def test_task_supervisor_creates_op_suspended_before_assignment() -> None:
    body = _text(SUPERVISOR)

    assert "CreateProcess" in body
    assert "CREATE_SUSPENDED" in body
    assert "AssignProcessToJobObject($job, $procInfo.hProcess)" in body
    assert "ResumeThread($procInfo.hThread)" in body
    assert body.index("CreateProcess") < body.index("AssignProcessToJobObject($job, $procInfo.hProcess)")
    assert body.index("AssignProcessToJobObject($job, $procInfo.hProcess)") < body.index("ResumeThread($procInfo.hThread)")
    assert "Start-Process -FilePath $op" not in body


def test_task_supervisor_routes_spaceful_python_path_through_job_child() -> None:
    body = _text(SUPERVISOR)

    assert '$childSupervisor = Join-Path $RepoPath "nodes\\windows\\umh_node\\daemon_child.ps1"' in body
    assert '"powershell.exe"' in body
    assert '"-File"' in body
    assert "$childSupervisor" in body
    assert "CommandLine -match [regex]::Escape($launcher)" in body


def test_daemon_child_resolves_spaceful_pythonw_without_op_command_parsing() -> None:
    body = _text(CHILD_SUPERVISOR)

    assert "Resolve-RealPythonw" in body
    assert "WindowsApps" in body
    assert "$process.StartInfo.FileName = $pythonw" in body
    assert "$process.StartInfo.Arguments" in body
    assert "$process.StartInfo.UseShellExecute = $false" in body
    assert "$process.WaitForExit()" in body


def test_task_supervisor_verifies_job_and_descendant_containment() -> None:
    body = _text(SUPERVISOR)

    assert "$basicLimits.LimitFlags = $JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE" in body
    assert "$limits.BasicLimitInformation = $basicLimits" in body
    assert "$limits.BasicLimitInformation.LimitFlags =" not in body
    assert "SetHandleInformation($job, $HANDLE_FLAG_INHERIT, 0)" in body
    assert "SetHandleInformation($stopEvent, $HANDLE_FLAG_INHERIT, 0)" in body
    assert "QueryInformationJobObject" in body
    assert "KILL_ON_JOB_CLOSE not active" in body
    assert "IsProcessInJob($procInfo.hProcess, $job" in body
    assert "launcher containment verification failed" in body
    assert "launcher_in_job" in body
    assert "handles_inheritable = $false" in body
    assert "waits_for_launcher = $true" in body
    assert "supervisor_parent_pid = $PID" in body
    assert "WaitForSingleObject($launcherWaitHandle" in body
    assert "$INFINITE = [uint32]::MaxValue" in body
    assert "WaitForSingleObject($procInfo.hProcess" not in body


def test_task_supervisor_fails_closed_on_native_launch_or_assignment_failure() -> None:
    body = _text(SUPERVISOR)

    assert "CreateProcess(op.exe suspended) failed win32=" in body
    assert "AssignProcessToJobObject failed for suspended op.exe" in body
    assert "TerminateJobObject($job, 2)" in body
    assert "ResumeThread(op.exe) failed win32=" in body
    assert "GetLastWin32Error()" in body


def test_task_supervisor_manifest_records_observed_ownership_boundary() -> None:
    body = _text(SUPERVISOR)

    assert "supervisor_pid" in body
    assert "job_name" in body
    assert "op_pid" in body
    assert "launcher_pid" in body
    assert "candidate_sha" in body
    assert "containment_verified" in body
    assert "UMH_DAEMON_SUPERVISOR_PID" in body


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


def test_service_stops_when_governed_parent_wrapper_exits() -> None:
    body = _text(SERVICE)

    assert "os.getppid()" in body
    assert "UMH_DAEMON_SUPERVISOR_PID" in body
    assert "OpenProcess" in body
    assert "umh-parent-exit" in body
    assert "governed %s exited; stopping daemon" in body
    assert "client.stop()" in body


def test_node_client_stop_drains_adapter_threads_and_executor() -> None:
    body = _text(CLIENT)
    stop_body = body.split("    async def stop(self) -> None:", 1)[1].split(
        "    async def _connect_and_serve", 1
    )[0]

    assert 'adapter.execute("camera.stream_stop", {})' in stop_body
    assert 'hasattr(adapter, "shutdown")' in stop_body
    assert 'hasattr(adapter, "stop")' in stop_body
    assert "self._media_drain_task.cancel()" in stop_body
    assert "self._camera_executor.shutdown" in stop_body


def test_reconciler_uses_canonical_stop_helper_not_pid_force_kill() -> None:
    body = _text(RECONCILER)

    assert "stop_daemon.ps1" in body
    assert "stop_task" in body
    assert "taskkill /PID" not in body
    assert "terminate every launcher.py process" not in body


def test_reconciler_refuses_task_process_divergence_as_healthy() -> None:
    body = _text(RECONCILER)
    condition_body = body.split("def condition(self) -> str:", 1)[1].split(
        "# \u2500\u2500 mesh admin plumbing", 1
    )[0]

    assert "task_process_diverged" in body
    assert "TASK_PROCESS_DIVERGED" in body
    assert "scheduled task/process lifecycle diverged" in body
    assert condition_body.index("TASK_PROCESS_DIVERGED") < condition_body.index("HEALTHY")


def test_reconciler_failed_stop_refuses_restart() -> None:
    body = _text(RECONCILER)
    repair_body = body.split("stop_task", 1)[1].split("start_task", 1)[0]

    assert "canonical stop helper failed" in body
    assert 'if not r["ok"]' in repair_body
