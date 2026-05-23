"""Worker runtime contracts for the UMH substrate layer.

Typed descriptors for worker runtimes, environment authority,
and runtime proof records. These are architectural primitives
that formalize what Phase 96.8J-K proved empirically.

UMH substrate subsystem. EOS is one platform consumer.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any


class EnvironmentType(str, Enum):
    VPS_TMUX = "vps_tmux"
    LOCAL_WSL = "local_wsl"
    LOCAL_WINDOWS_DESKTOP = "local_windows_desktop"


class AuthorityDomain(str, Enum):
    REMOTE_ORCHESTRATION = "remote_orchestration"
    LOCAL_SHELL = "local_shell"
    LOCAL_GUI = "local_gui"
    FILESYSTEM_RELAY = "filesystem_relay"


class MessageBusType(str, Enum):
    FILESYSTEM_JSON = "filesystem_json"
    SSH_TMUX = "ssh_tmux"
    DIRECT_CALL = "direct_call"


class ProofStatus(str, Enum):
    PENDING = "pending"
    COMPLETED = "completed"
    FAILED = "failed"
    TIMEOUT = "timeout"


@dataclass
class EnvironmentAuthorityDescriptor:
    """What an environment is natively authorized to do."""

    environment_type: EnvironmentType
    authority_domains: list[AuthorityDomain]
    can_own_gui: bool = False
    can_own_local_shell: bool = False
    can_own_remote_orchestration: bool = False
    notes: list[str] = field(default_factory=list)

    def has_authority(self, domain: AuthorityDomain) -> bool:
        return domain in self.authority_domains


@dataclass
class WorkerRuntimeDescriptor:
    """Describes a worker runtime instance."""

    worker_id: str
    environment_type: EnvironmentType
    authority: EnvironmentAuthorityDescriptor
    capabilities: list[str] = field(default_factory=list)
    message_bus: MessageBusType = MessageBusType.FILESYSTEM_JSON
    version: str = "v1"

    def can_handle(self, capability: str) -> bool:
        return capability in self.capabilities


@dataclass
class WorkerHeartbeat:
    """Periodic liveness signal from a worker runtime."""

    worker_id: str
    timestamp: str = ""
    status: str = "alive"
    capabilities_active: list[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        if not self.timestamp:
            self.timestamp = datetime.now(timezone.utc).isoformat()


@dataclass
class RuntimeProofRecord:
    """Immutable record that a runtime action was attempted and its outcome."""

    proof_id: str
    worker_id: str
    adapter_id: str
    action_type: str
    proof_status: ProofStatus
    adapter_status: str = ""
    request_id: str = ""
    trace_id: str = ""
    timestamp: str = ""
    evidence: dict[str, Any] = field(default_factory=dict)
    notes: list[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        if not self.timestamp:
            self.timestamp = datetime.now(timezone.utc).isoformat()

    @property
    def succeeded(self) -> bool:
        return self.proof_status == ProofStatus.COMPLETED


# -- Pre-built environment authority descriptors --

VPS_AUTHORITY = EnvironmentAuthorityDescriptor(
    environment_type=EnvironmentType.VPS_TMUX,
    authority_domains=[AuthorityDomain.REMOTE_ORCHESTRATION],
    can_own_gui=False,
    can_own_local_shell=False,
    can_own_remote_orchestration=True,
    notes=["VPS orchestrates via SSH/tmux, never owns local GUI or shell"],
)

WSL_AUTHORITY = EnvironmentAuthorityDescriptor(
    environment_type=EnvironmentType.LOCAL_WSL,
    authority_domains=[AuthorityDomain.LOCAL_SHELL, AuthorityDomain.FILESYSTEM_RELAY],
    can_own_gui=False,
    can_own_local_shell=True,
    can_own_remote_orchestration=False,
    notes=["WSL owns local shell and filesystem relay, never owns GUI"],
)

WINDOWS_DESKTOP_AUTHORITY = EnvironmentAuthorityDescriptor(
    environment_type=EnvironmentType.LOCAL_WINDOWS_DESKTOP,
    authority_domains=[AuthorityDomain.LOCAL_GUI, AuthorityDomain.LOCAL_SHELL],
    can_own_gui=True,
    can_own_local_shell=True,
    can_own_remote_orchestration=False,
    notes=["Windows desktop session owns GUI actuation via logged-in session"],
)
