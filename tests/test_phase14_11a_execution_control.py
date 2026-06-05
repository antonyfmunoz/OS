"""Phase 14.11A — execution control adapter tests.

Tests RuntimeAdapter defaults, ShellRuntimeAdapter pause/resume,
ClaudeCodeRuntimeAdapter inheriting NOT_SUPPORTED, and environment awareness.
"""

from __future__ import annotations

import sys

sys.path.insert(0, "/opt/OS")

from substrate.organism.runtime_adapter import RuntimeAdapter, RuntimeStartRequest, RuntimeStartResult, RuntimeInjectRequest
from substrate.organism.shell_runtime_adapter import ShellRuntimeAdapter
from substrate.organism.claude_code_runtime_adapter import ClaudeCodeRuntimeAdapter


class _ConcreteAdapter(RuntimeAdapter):
    """Minimal concrete subclass — implements only abstract methods."""
    adapter_id = "test"
    runtime_type = "test"

    def is_available(self) -> bool:
        return True

    def availability_detail(self) -> dict:
        return {"available": True}

    def prepare(self, request: RuntimeStartRequest) -> dict:
        return {"ready": True}

    def start(self, request: RuntimeStartRequest) -> RuntimeStartResult:
        return RuntimeStartResult(session_id="test", started=True)

    def inject(self, request: RuntimeInjectRequest) -> dict:
        return {"injected": True}

    def stop(self, session_id: str, reason: str = "") -> dict:
        return {"stopped": True}

    def status(self, session_id: str) -> dict:
        return {"status": "running"}

    def collect_output(self, session_id: str) -> str:
        return ""

    def collect_artifacts(self, session_id: str) -> list:
        return []

    def validate(self, session_id: str) -> dict:
        return {"valid": True}

    def cleanup(self, session_id: str) -> dict:
        return {"cleaned": True}


class TestRuntimeAdapterDefaults:
    def test_pause_returns_not_supported(self) -> None:
        adapter = _ConcreteAdapter()
        result = adapter.pause("session-1")
        assert result["paused"] is False
        assert result["supported"] is False
        assert "test" in result["reason"]

    def test_resume_returns_not_supported(self) -> None:
        adapter = _ConcreteAdapter()
        result = adapter.resume("session-1")
        assert result["resumed"] is False
        assert result["supported"] is False
        assert "test" in result["reason"]


class TestClaudeCodeAdapterInheritsDefaults:
    def test_pause_not_supported(self) -> None:
        adapter = ClaudeCodeRuntimeAdapter()
        result = adapter.pause("session-1")
        assert result["paused"] is False
        assert result["supported"] is False

    def test_resume_not_supported(self) -> None:
        adapter = ClaudeCodeRuntimeAdapter()
        result = adapter.resume("session-1")
        assert result["resumed"] is False
        assert result["supported"] is False


class TestShellAdapterPauseResume:
    def test_pause_no_process(self) -> None:
        adapter = ShellRuntimeAdapter()
        result = adapter.pause("nonexistent")
        assert result["paused"] is False
        if sys.platform == "linux":
            assert result["supported"] is True
            assert "no process found" in result["reason"]
        else:
            assert result["supported"] is False

    def test_resume_no_process(self) -> None:
        adapter = ShellRuntimeAdapter()
        result = adapter.resume("nonexistent")
        assert result["resumed"] is False
        if sys.platform == "linux":
            assert result["supported"] is True
        else:
            assert result["supported"] is False

    def test_resume_not_paused(self) -> None:
        if sys.platform != "linux":
            return
        import subprocess
        adapter = ShellRuntimeAdapter()
        proc = subprocess.Popen(["sleep", "60"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        adapter._processes["test-resume"] = proc
        adapter._start_times["test-resume"] = 0.0
        try:
            result = adapter.resume("test-resume")
            assert result["resumed"] is False
            assert "not paused" in result["reason"]
        finally:
            proc.kill()
            proc.wait()

    def test_pause_and_resume_cycle(self) -> None:
        if sys.platform != "linux":
            return
        import subprocess
        adapter = ShellRuntimeAdapter()
        proc = subprocess.Popen(["sleep", "60"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        adapter._processes["test-cycle"] = proc
        adapter._start_times["test-cycle"] = 0.0
        try:
            pause_result = adapter.pause("test-cycle")
            assert pause_result["paused"] is True
            assert pause_result["supported"] is True
            assert "test-cycle" in adapter._paused_sessions

            status_result = adapter.status("test-cycle")
            assert status_result["status"] == "paused"

            resume_result = adapter.resume("test-cycle")
            assert resume_result["resumed"] is True
            assert resume_result["supported"] is True
            assert "test-cycle" not in adapter._paused_sessions

            status_result = adapter.status("test-cycle")
            assert status_result["status"] == "running"
        finally:
            proc.kill()
            proc.wait()

    def test_double_pause_idempotent(self) -> None:
        if sys.platform != "linux":
            return
        import subprocess
        adapter = ShellRuntimeAdapter()
        proc = subprocess.Popen(["sleep", "60"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        adapter._processes["test-double"] = proc
        adapter._start_times["test-double"] = 0.0
        try:
            adapter.pause("test-double")
            result = adapter.pause("test-double")
            assert result["paused"] is True
            assert "already paused" in result["reason"]
        finally:
            proc.kill()
            proc.wait()

    def test_cleanup_clears_paused(self) -> None:
        adapter = ShellRuntimeAdapter()
        adapter._paused_sessions.add("test-cleanup")
        adapter.cleanup("test-cleanup")
        assert "test-cleanup" not in adapter._paused_sessions


class TestEnvironmentAwareness:
    def test_shell_adapter_on_linux(self) -> None:
        if sys.platform != "linux":
            return
        adapter = ShellRuntimeAdapter()
        result = adapter.pause("no-such-session")
        assert result["supported"] is True

    def test_adapter_instantiation_no_crash(self) -> None:
        shell = ShellRuntimeAdapter()
        cc = ClaudeCodeRuntimeAdapter()
        assert shell.runtime_type == "shell"
        assert cc.runtime_type == "claude_code_pty"
        assert hasattr(shell, "pause")
        assert hasattr(shell, "resume")
        assert hasattr(cc, "pause")
        assert hasattr(cc, "resume")
