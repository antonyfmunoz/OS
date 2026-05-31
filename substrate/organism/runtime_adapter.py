"""Runtime adapter interface — abstract contract for execution surfaces.

Each adapter (shell, claude_code_pty, codex, browser, human, test) implements
this interface. The RuntimeManager selects and drives adapters; adapters
never self-start or self-approve.

Phase 13.2. Substrate layer. Instance-agnostic.
"""

from __future__ import annotations

import abc
from dataclasses import dataclass, field
from typing import Any


@dataclass
class RuntimeStartRequest:
    session_id: str
    runtime_type: str
    cwd: str = ""
    command: str = ""
    prompt: str = ""
    env_policy: str = "sandbox"
    timeout_seconds: int = 300
    max_output_bytes: int = 1_000_000
    sandbox_required: bool = True
    allowed_paths: list[str] = field(default_factory=list)
    blocked_paths: list[str] = field(default_factory=list)
    risk_class: str = "low"
    work_packet_id: str = ""
    workcell_id: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class RuntimeStartResult:
    session_id: str
    started: bool = False
    pid: int | None = None
    status: str = ""
    output: str = ""
    error: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class RuntimeInjectRequest:
    session_id: str
    message: str = ""
    injection_mode: str = "stdin"
    requires_enter: bool = True
    max_chunk_size: int = 4096


class RuntimeAdapter(abc.ABC):
    """Abstract runtime adapter. One per RuntimeType."""

    adapter_id: str = ""
    runtime_type: str = ""

    @abc.abstractmethod
    def is_available(self) -> bool:
        """Return True if the adapter's runtime is installed/configured."""

    @abc.abstractmethod
    def availability_detail(self) -> dict[str, Any]:
        """Return availability info including reason if unavailable."""

    @abc.abstractmethod
    def prepare(self, request: RuntimeStartRequest) -> dict[str, Any]:
        """Validate and prepare the runtime environment. Return prep metadata."""

    @abc.abstractmethod
    def start(self, request: RuntimeStartRequest) -> RuntimeStartResult:
        """Start the runtime process. Return result with pid/status."""

    @abc.abstractmethod
    def inject(self, request: RuntimeInjectRequest) -> dict[str, Any]:
        """Inject a message into the running runtime."""

    @abc.abstractmethod
    def stop(self, session_id: str, reason: str = "") -> dict[str, Any]:
        """Stop the runtime process gracefully."""

    @abc.abstractmethod
    def status(self, session_id: str) -> dict[str, Any]:
        """Return current runtime process status."""

    @abc.abstractmethod
    def collect_output(self, session_id: str) -> str:
        """Collect stdout/stderr output from the runtime."""

    @abc.abstractmethod
    def collect_artifacts(self, session_id: str) -> list[str]:
        """Collect artifact file paths produced by the runtime."""

    @abc.abstractmethod
    def validate(self, session_id: str) -> dict[str, Any]:
        """Run validation checks on runtime outputs."""

    @abc.abstractmethod
    def cleanup(self, session_id: str) -> dict[str, Any]:
        """Clean up runtime resources (processes, temp files)."""
