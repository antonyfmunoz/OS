"""Runtime session model — governed execution surface for workcell runtimes.

Defines RuntimeSession, RuntimeEvent, and supporting types for tracked,
sandboxed runtime execution within UMH governance.

Phase 13.2. Substrate layer. Instance-agnostic.
"""

from __future__ import annotations

import json
import logging
import os
import time
import uuid
from dataclasses import dataclass, field, asdict
from enum import Enum
from typing import Any

logger = logging.getLogger(__name__)

_REPO_ROOT = os.environ.get("UMH_ROOT", "/opt/OS")
_SESSIONS_PATH = os.path.join(_REPO_ROOT, "data", "umh", "runtime_surface", "sessions.jsonl")
_EVENTS_PATH = os.path.join(_REPO_ROOT, "data", "umh", "runtime_surface", "events.jsonl")


class RuntimeStatus(str, Enum):
    DRAFTED = "drafted"
    APPROVED = "approved"
    STARTING = "starting"
    RUNNING = "running"
    WAITING_FOR_INPUT = "waiting_for_input"
    STOPPING = "stopping"
    STOPPED = "stopped"
    COMPLETED = "completed"
    FAILED = "failed"
    BLOCKED = "blocked"
    EXPIRED = "expired"


class RuntimeType(str, Enum):
    SHELL = "shell"
    CLAUDE_CODE_PTY = "claude_code_pty"
    CODEX_RUNTIME = "codex_runtime"
    BROWSER_RUNTIME = "browser_runtime"
    HUMAN_EXECUTOR = "human_executor"
    TEST_ADAPTER = "test_adapter"


class RuntimeEventType(str, Enum):
    SESSION_CREATED = "session_created"
    RUNTIME_STARTING = "runtime_starting"
    RUNTIME_STARTED = "runtime_started"
    STDOUT = "stdout"
    STDERR = "stderr"
    PROMPT_INJECTED = "prompt_injected"
    PROGRESS = "progress"
    ARTIFACT_CREATED = "artifact_created"
    VALIDATION_STARTED = "validation_started"
    VALIDATION_COMPLETED = "validation_completed"
    APPROVAL_REQUIRED = "approval_required"
    HUMAN_INPUT_REQUIRED = "human_input_required"
    STOP_REQUESTED = "stop_requested"
    STOPPED = "stopped"
    COMPLETED = "completed"
    FAILED = "failed"
    BLOCKED = "blocked"


@dataclass
class RuntimeEvent:
    event_id: str
    session_id: str
    event_type: str
    timestamp: float
    message: str = ""
    stream: str = ""
    sequence: int = 0
    severity: str = "info"
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> RuntimeEvent:
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})

    @classmethod
    def create(
        cls,
        session_id: str,
        event_type: str | RuntimeEventType,
        message: str = "",
        stream: str = "",
        sequence: int = 0,
        severity: str = "info",
        metadata: dict[str, Any] | None = None,
    ) -> RuntimeEvent:
        et = event_type.value if isinstance(event_type, RuntimeEventType) else event_type
        return cls(
            event_id=f"re-{uuid.uuid4().hex[:12]}",
            session_id=session_id,
            event_type=et,
            timestamp=time.time(),
            message=message,
            stream=stream,
            sequence=sequence,
            severity=severity,
            metadata=metadata or {},
        )


@dataclass
class RuntimeSession:
    session_id: str
    operator_session_id: str = ""
    work_packet_id: str = ""
    workcell_id: str = ""
    runtime_type: str = RuntimeType.SHELL.value
    runtime_status: str = RuntimeStatus.DRAFTED.value
    risk_class: str = "low"
    sandbox_id: str = ""
    worktree_path: str = ""
    branch_name: str = ""
    cwd: str = ""
    command: str = ""
    prompt: str = ""
    started_at: float = 0.0
    updated_at: float = 0.0
    completed_at: float = 0.0
    stopped_at: float = 0.0
    created_by: str = "operator"
    approved_by: str = ""
    approval_id: str = ""
    output_log_path: str = ""
    event_log_path: str = ""
    artifact_paths: list[str] = field(default_factory=list)
    changed_files: list[str] = field(default_factory=list)
    validation_results: dict[str, Any] = field(default_factory=dict)
    stop_reason: str = ""
    failure_reason: str = ""
    idempotency_key: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> RuntimeSession:
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})

    @classmethod
    def create(
        cls,
        runtime_type: str | RuntimeType = RuntimeType.SHELL,
        work_packet_id: str = "",
        operator_session_id: str = "",
        workcell_id: str = "",
        command: str = "",
        prompt: str = "",
        risk_class: str = "low",
        cwd: str = "",
        created_by: str = "operator",
        idempotency_key: str = "",
        metadata: dict[str, Any] | None = None,
    ) -> RuntimeSession:
        rt = runtime_type.value if isinstance(runtime_type, RuntimeType) else runtime_type
        now = time.time()
        return cls(
            session_id=f"rs-{uuid.uuid4().hex[:12]}",
            operator_session_id=operator_session_id,
            work_packet_id=work_packet_id,
            workcell_id=workcell_id,
            runtime_type=rt,
            runtime_status=RuntimeStatus.DRAFTED.value,
            risk_class=risk_class,
            command=command,
            prompt=prompt,
            cwd=cwd,
            updated_at=now,
            created_by=created_by,
            idempotency_key=idempotency_key or f"idk-{uuid.uuid4().hex[:8]}",
            metadata=metadata or {},
        )

    def is_terminal(self) -> bool:
        return self.runtime_status in (
            RuntimeStatus.COMPLETED.value,
            RuntimeStatus.FAILED.value,
            RuntimeStatus.STOPPED.value,
            RuntimeStatus.EXPIRED.value,
        )

    def is_running(self) -> bool:
        return self.runtime_status in (
            RuntimeStatus.STARTING.value,
            RuntimeStatus.RUNNING.value,
            RuntimeStatus.WAITING_FOR_INPUT.value,
        )


def _ensure_dir(path: str) -> None:
    d = os.path.dirname(path)
    if d:
        os.makedirs(d, exist_ok=True)


def persist_session(session: RuntimeSession) -> None:
    _ensure_dir(_SESSIONS_PATH)
    with open(_SESSIONS_PATH, "a") as f:
        f.write(json.dumps(session.to_dict()) + "\n")


def persist_event(event: RuntimeEvent) -> None:
    _ensure_dir(_EVENTS_PATH)
    with open(_EVENTS_PATH, "a") as f:
        f.write(json.dumps(event.to_dict()) + "\n")


def load_sessions() -> list[RuntimeSession]:
    if not os.path.exists(_SESSIONS_PATH):
        return []
    sessions: dict[str, RuntimeSession] = {}
    with open(_SESSIONS_PATH) as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                data = json.loads(line)
                s = RuntimeSession.from_dict(data)
                sessions[s.session_id] = s
            except (json.JSONDecodeError, TypeError):
                continue
    return list(sessions.values())


def load_events(session_id: str | None = None) -> list[RuntimeEvent]:
    if not os.path.exists(_EVENTS_PATH):
        return []
    events: list[RuntimeEvent] = []
    with open(_EVENTS_PATH) as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                data = json.loads(line)
                e = RuntimeEvent.from_dict(data)
                if session_id is None or e.session_id == session_id:
                    events.append(e)
            except (json.JSONDecodeError, TypeError):
                continue
    return events


def get_session(session_id: str) -> RuntimeSession | None:
    for s in load_sessions():
        if s.session_id == session_id:
            return s
    return None
