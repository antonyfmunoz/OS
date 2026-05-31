"""Runtime manager — orchestrates governed runtime session lifecycle.

Creates, starts, monitors, stops, and validates runtime sessions within
UMH governance boundaries. Never self-approves; never merges PRs; never
mutates production directly.

Phase 13.2. Substrate layer. Instance-agnostic.
"""

from __future__ import annotations

import logging
import os
import subprocess
import time
import uuid
from typing import Any

from substrate.organism.runtime_adapter import (
    RuntimeAdapter,
    RuntimeInjectRequest,
    RuntimeStartRequest,
    RuntimeStartResult,
)
from substrate.organism.runtime_session import (
    RuntimeEvent,
    RuntimeEventType,
    RuntimeSession,
    RuntimeStatus,
    RuntimeType,
    get_session,
    load_events,
    load_sessions,
    persist_event,
    persist_session,
)
from substrate.organism.shell_runtime_adapter import ShellRuntimeAdapter
from substrate.organism.claude_code_runtime_adapter import ClaudeCodeRuntimeAdapter

logger = logging.getLogger(__name__)

_REPO_ROOT = os.environ.get("UMH_ROOT", "/opt/OS")


class RuntimePolicyViolation(Exception):
    pass


class RuntimeManager:
    """Manages the full lifecycle of governed runtime sessions."""

    def __init__(self) -> None:
        self._adapters: dict[str, RuntimeAdapter] = {
            RuntimeType.SHELL.value: ShellRuntimeAdapter(),
            RuntimeType.CLAUDE_CODE_PTY.value: ClaudeCodeRuntimeAdapter(),
        }

    def get_adapters(self) -> dict[str, dict[str, Any]]:
        return {k: v.availability_detail() for k, v in self._adapters.items()}

    def validate_runtime_policy(
        self,
        runtime_type: str,
        command: str,
        risk_class: str,
        cwd: str,
        work_packet_id: str,
        operator_session_id: str,
    ) -> dict[str, Any]:
        violations: list[str] = []

        if not work_packet_id and not operator_session_id:
            violations.append("runtime session requires Work Packet or OperatorSession linkage")

        if risk_class in ("high", "critical"):
            violations.append(f"risk_class={risk_class} is blocked for runtime execution")

        if risk_class == "medium":
            return {
                "allowed": False,
                "approval_required": True,
                "reason": "medium-risk runtime requires explicit operator approval",
                "violations": violations,
            }

        if cwd:
            abs_cwd = os.path.abspath(cwd)
            main_repo = os.path.abspath(_REPO_ROOT)
            if abs_cwd == main_repo:
                violations.append("runtime must not operate directly on main repo root — use sandbox/worktree")

        from substrate.organism.shell_runtime_adapter import is_command_blocked
        blocked, reason = is_command_blocked(command)
        if blocked:
            violations.append(f"blocked command: {reason}")

        adapter = self._adapters.get(runtime_type)
        if not adapter:
            violations.append(f"no adapter registered for runtime_type={runtime_type}")
        elif not adapter.is_available():
            violations.append(f"adapter {runtime_type} is not available")

        if violations:
            return {"allowed": False, "approval_required": False, "violations": violations}

        return {"allowed": True, "approval_required": False, "violations": []}

    def allocate_sandbox_or_worktree(self, session_id: str) -> dict[str, Any]:
        worktree_name = f"runtime-{session_id}"
        worktree_base = os.path.join(_REPO_ROOT, ".claude", "worktrees")
        worktree_path = os.path.join(worktree_base, worktree_name)

        if os.path.isdir(worktree_path):
            return {
                "allocated": True,
                "worktree_path": worktree_path,
                "branch_name": f"worktree-{worktree_name}",
                "reused": True,
            }

        try:
            os.makedirs(worktree_base, exist_ok=True)
            result = subprocess.run(
                ["git", "worktree", "add", "-b", f"worktree-{worktree_name}", worktree_path, "HEAD"],
                cwd=_REPO_ROOT,
                capture_output=True,
                text=True,
                timeout=30,
            )
            if result.returncode != 0:
                return {
                    "allocated": False,
                    "error": result.stderr.strip(),
                    "fallback": "use existing sandbox directory",
                }
            return {
                "allocated": True,
                "worktree_path": worktree_path,
                "branch_name": f"worktree-{worktree_name}",
                "reused": False,
            }
        except Exception as exc:
            return {"allocated": False, "error": str(exc)}

    def create_runtime_session(
        self,
        runtime_type: str = RuntimeType.SHELL.value,
        command: str = "",
        prompt: str = "",
        work_packet_id: str = "",
        operator_session_id: str = "",
        workcell_id: str = "",
        risk_class: str = "low",
        cwd: str = "",
        idempotency_key: str = "",
        metadata: dict[str, Any] | None = None,
    ) -> tuple[RuntimeSession, dict[str, Any]]:
        if idempotency_key:
            for existing in load_sessions():
                if existing.idempotency_key == idempotency_key and not existing.is_terminal():
                    return existing, {"duplicate": True, "reason": "idempotent session exists"}

        policy = self.validate_runtime_policy(
            runtime_type=runtime_type,
            command=command,
            risk_class=risk_class,
            cwd=cwd,
            work_packet_id=work_packet_id,
            operator_session_id=operator_session_id,
        )

        if not policy["allowed"]:
            session = RuntimeSession.create(
                runtime_type=runtime_type,
                command=command,
                prompt=prompt,
                work_packet_id=work_packet_id,
                operator_session_id=operator_session_id,
                workcell_id=workcell_id,
                risk_class=risk_class,
                cwd=cwd,
                idempotency_key=idempotency_key,
                metadata=metadata,
            )
            if policy.get("approval_required"):
                session.runtime_status = RuntimeStatus.BLOCKED.value
                session.failure_reason = "approval_required: " + policy.get("reason", "")
            else:
                session.runtime_status = RuntimeStatus.BLOCKED.value
                session.failure_reason = "; ".join(policy["violations"])

            persist_session(session)
            persist_event(RuntimeEvent.create(
                session_id=session.session_id,
                event_type=RuntimeEventType.BLOCKED,
                message=session.failure_reason,
            ))
            return session, policy

        session = RuntimeSession.create(
            runtime_type=runtime_type,
            command=command,
            prompt=prompt,
            work_packet_id=work_packet_id,
            operator_session_id=operator_session_id,
            workcell_id=workcell_id,
            risk_class=risk_class,
            cwd=cwd,
            idempotency_key=idempotency_key,
            metadata=metadata,
        )
        persist_session(session)
        persist_event(RuntimeEvent.create(
            session_id=session.session_id,
            event_type=RuntimeEventType.SESSION_CREATED,
            message=f"type={runtime_type}, command={command[:80]}",
        ))
        return session, policy

    def start_session(self, session_id: str, approved_by: str = "operator") -> RuntimeStartResult:
        session = get_session(session_id)
        if not session:
            return RuntimeStartResult(session_id=session_id, started=False, error="session not found")

        if session.is_terminal():
            return RuntimeStartResult(session_id=session_id, started=False, error="session already terminal")

        if session.is_running():
            return RuntimeStartResult(session_id=session_id, started=False, error="session already running")

        adapter = self._adapters.get(session.runtime_type)
        if not adapter:
            return RuntimeStartResult(session_id=session_id, started=False, error=f"no adapter for {session.runtime_type}")

        sandbox = self.allocate_sandbox_or_worktree(session_id)
        cwd = session.cwd
        if sandbox.get("allocated") and not cwd:
            cwd = sandbox["worktree_path"]

        session.runtime_status = RuntimeStatus.APPROVED.value
        session.approved_by = approved_by
        session.worktree_path = sandbox.get("worktree_path", "")
        session.branch_name = sandbox.get("branch_name", "")
        session.cwd = cwd
        session.started_at = time.time()
        session.updated_at = time.time()
        persist_session(session)

        request = RuntimeStartRequest(
            session_id=session_id,
            runtime_type=session.runtime_type,
            cwd=cwd,
            command=session.command,
            prompt=session.prompt,
            timeout_seconds=300,
            sandbox_required=True,
            risk_class=session.risk_class,
            work_packet_id=session.work_packet_id,
            workcell_id=session.workcell_id,
        )

        session.runtime_status = RuntimeStatus.STARTING.value
        session.updated_at = time.time()
        persist_session(session)

        result = adapter.start(request)

        if result.started:
            session.runtime_status = RuntimeStatus.COMPLETED.value if result.status == "completed" else RuntimeStatus.RUNNING.value
            session.completed_at = time.time() if result.status == "completed" else 0.0
        else:
            session.runtime_status = RuntimeStatus.FAILED.value
            session.failure_reason = result.error
        session.updated_at = time.time()
        session.validation_results = adapter.validate(session_id)
        persist_session(session)

        return result

    def inject_message(self, session_id: str, message: str, mode: str = "stdin") -> dict[str, Any]:
        session = get_session(session_id)
        if not session:
            return {"injected": False, "reason": "session not found"}
        if not session.is_running():
            return {"injected": False, "reason": f"session status={session.runtime_status}, not running"}

        adapter = self._adapters.get(session.runtime_type)
        if not adapter:
            return {"injected": False, "reason": "no adapter"}

        request = RuntimeInjectRequest(session_id=session_id, message=message, injection_mode=mode)
        return adapter.inject(request)

    def stop_session(self, session_id: str, reason: str = "operator_requested") -> dict[str, Any]:
        session = get_session(session_id)
        if not session:
            return {"stopped": False, "reason": "session not found"}

        adapter = self._adapters.get(session.runtime_type)
        if not adapter:
            return {"stopped": False, "reason": "no adapter"}

        result = adapter.stop(session_id, reason)

        session.runtime_status = RuntimeStatus.STOPPED.value
        session.stopped_at = time.time()
        session.stop_reason = reason
        session.updated_at = time.time()
        persist_session(session)

        return result

    def stream_events(self, session_id: str, since_sequence: int = 0) -> list[dict[str, Any]]:
        events = load_events(session_id)
        return [e.to_dict() for e in events if e.sequence >= since_sequence]

    def collect_artifacts(self, session_id: str) -> list[str]:
        session = get_session(session_id)
        if not session:
            return []
        adapter = self._adapters.get(session.runtime_type)
        if not adapter:
            return []
        return adapter.collect_artifacts(session_id)

    def validate_session_outputs(self, session_id: str) -> dict[str, Any]:
        session = get_session(session_id)
        if not session:
            return {"valid": False, "reason": "session not found"}
        adapter = self._adapters.get(session.runtime_type)
        if not adapter:
            return {"valid": False, "reason": "no adapter"}
        return adapter.validate(session_id)

    def list_sessions(self) -> list[dict[str, Any]]:
        return [s.to_dict() for s in load_sessions()]

    def get_session(self, session_id: str) -> dict[str, Any] | None:
        s = get_session(session_id)
        return s.to_dict() if s else None

    def get_events(self, session_id: str) -> list[dict[str, Any]]:
        return [e.to_dict() for e in load_events(session_id)]

    def cleanup_expired_sessions(self, max_age_seconds: float = 86400) -> list[str]:
        cleaned: list[str] = []
        now = time.time()
        for session in load_sessions():
            if session.is_running() and session.started_at > 0:
                if now - session.started_at > max_age_seconds:
                    adapter = self._adapters.get(session.runtime_type)
                    if adapter:
                        adapter.cleanup(session.session_id)
                    session.runtime_status = RuntimeStatus.EXPIRED.value
                    session.updated_at = now
                    persist_session(session)
                    cleaned.append(session.session_id)
        return cleaned

    def get_overview(self) -> dict[str, Any]:
        sessions = load_sessions()
        by_status: dict[str, int] = {}
        for s in sessions:
            by_status[s.runtime_status] = by_status.get(s.runtime_status, 0) + 1
        return {
            "total_sessions": len(sessions),
            "active_sessions": sum(1 for s in sessions if s.is_running()),
            "completed_sessions": sum(1 for s in sessions if s.runtime_status == RuntimeStatus.COMPLETED.value),
            "failed_sessions": sum(1 for s in sessions if s.runtime_status == RuntimeStatus.FAILED.value),
            "blocked_sessions": sum(1 for s in sessions if s.runtime_status == RuntimeStatus.BLOCKED.value),
            "by_status": by_status,
            "adapters": self.get_adapters(),
        }
