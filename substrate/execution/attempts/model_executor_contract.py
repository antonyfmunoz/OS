"""Provider-neutral model execution contract for governed attempts.

The control plane owns attempts, grants, lifecycle, composition, verification,
promotion, and Proof. A model executor is only an adapter behind that authority:
it receives a canonical work packet projection plus an isolated workspace, then
returns a structured terminal result. Provider names are adapter metadata, not
canonical domain types.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol


@dataclass(frozen=True)
class ModelExecutorIdentity:
    provider: str
    model: str
    version: str = ""
    adapter: str = ""

    def proof_metadata(self) -> dict[str, str]:
        return {
            "provider": self.provider,
            "model": self.model,
            "version": self.version,
            "adapter": self.adapter,
        }


@dataclass(frozen=True)
class ModelExecutorReadiness:
    ok: bool
    identity: ModelExecutorIdentity
    reason: str = ""
    authenticated: bool = False


@dataclass(frozen=True)
class ModelWorkPacketInput:
    prompt: str
    worktree_path: str
    timeout_seconds: float
    max_turns: int
    disallowed_tools: tuple[str, ...] = ()
    attempt_id: str = ""
    package_hash: str = ""
    operation_identity: dict[str, Any] = field(default_factory=dict)
    proof_binding: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class ModelInvocation:
    argv: list[str]
    stdin: str = ""
    cwd: str = ""
    inherited_fds: tuple[int, ...] = ()
    readonly_fd_mounts: tuple[tuple[int, str], ...] = ()
    execution_identity: dict[str, Any] = field(default_factory=dict)


@dataclass
class ModelTerminalResult:
    ok: bool = False
    status: str = "failed"
    stdout: str = ""
    stderr: str = ""
    summary: str = ""
    exit_code: int | None = None
    duration_seconds: float = 0.0
    timed_out: bool = False
    cancelled: bool = False
    retry_class: str = "unknown"
    usage: dict[str, Any] = field(default_factory=dict)
    cost: dict[str, Any] = field(default_factory=dict)
    identity: ModelExecutorIdentity | None = None
    execution_identity: dict[str, Any] = field(default_factory=dict)
    proof_binding: dict[str, Any] = field(default_factory=dict)

    @property
    def has_real_content(self) -> bool:
        text = (self.stdout or self.summary or "").strip()
        if not text:
            return False
        lowered = text.lower()
        empty_markers = (
            "no output",
            "empty response",
            "authentication required",
            "not authenticated",
            "usage:",
        )
        return not any(marker in lowered for marker in empty_markers)


class ModelExecutor(Protocol):
    """Adapter protocol implemented by every production or test executor."""

    identity: ModelExecutorIdentity

    def readiness(self, *, env: dict[str, str] | None = None) -> ModelExecutorReadiness:
        """Return authenticated readiness without consuming task quota."""

    def build_invocation(self, packet: ModelWorkPacketInput) -> ModelInvocation:
        """Return the inner command the governed worker will isolate and run."""

    def collect_result(
        self, packet: ModelWorkPacketInput, completed: Any | None, *, duration_seconds: float
    ) -> ModelTerminalResult:
        """Normalize a completed isolated subprocess result."""

    def invoke(self, packet: ModelWorkPacketInput, *, env: dict[str, str]) -> ModelTerminalResult:
        """Compatibility helper for direct adapter tests/non-production callers."""


__all__ = [
    "ModelExecutor",
    "ModelExecutorIdentity",
    "ModelInvocation",
    "ModelExecutorReadiness",
    "ModelTerminalResult",
    "ModelWorkPacketInput",
]
