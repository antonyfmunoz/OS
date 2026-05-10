"""UMH Capability Specifications — types of execution the system supports.

Each capability type maps to an ExecutionClass and defines what inputs/outputs
are expected. The execution spine routes requests based on capability type.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class CapabilityType(str, Enum):
    """Types of execution the system can perform."""

    LLM_CALL = "llm_call"
    SHELL_COMMAND = "shell_command"
    FILE_OPERATION = "file_operation"
    BROWSER_ACTION = "browser_action"
    COMPUTER_USE = "computer_use"
    OS_INTERACTION = "os_interaction"


class RiskLevel(str, Enum):
    """Risk classification for capability execution."""

    LOW = "low"  # read-only, no side effects
    MEDIUM = "medium"  # writes data, reversible
    HIGH = "high"  # system commands, external calls
    CRITICAL = "critical"  # destructive or irreversible


@dataclass(frozen=True)
class CapabilitySpec:
    """Describes a specific capability execution request."""

    capability_type: CapabilityType
    operation: str
    inputs: dict[str, Any] = field(default_factory=dict)
    risk_level: RiskLevel = RiskLevel.MEDIUM
    requires_approval: bool = False
    timeout_s: int = 30

    @property
    def is_llm(self) -> bool:
        return self.capability_type == CapabilityType.LLM_CALL

    @property
    def is_implemented(self) -> bool:
        return self.capability_type in _IMPLEMENTED_CAPABILITIES


_IMPLEMENTED_CAPABILITIES = frozenset(
    {
        CapabilityType.LLM_CALL,
        CapabilityType.SHELL_COMMAND,
        CapabilityType.FILE_OPERATION,
    }
)
