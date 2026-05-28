"""ActionEnvelope — canonical executable object for ALL organism mutations.

Every action that mutates reality (filesystem, containers, processes,
network, state) MUST be wrapped in an ActionEnvelope and submitted
to the GovernedExecutionSpine. No exceptions.

Subsystems produce ActionEnvelopes. Only the spine executes them.

UMH substrate subsystem. Instance-agnostic.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable
from uuid import uuid4


class ActionType(str, Enum):
    FILESYSTEM = "filesystem"
    CONTAINER = "container"
    PROCESS = "process"
    NETWORK = "network"
    STATE = "state"
    GRAPH = "graph"
    TEST = "test"
    CLEANUP = "cleanup"
    INGESTION = "ingestion"
    DEPLOYMENT = "deployment"


class ReversibilityClass(str, Enum):
    FULLY_REVERSIBLE = "fully_reversible"
    PARTIALLY_REVERSIBLE = "partially_reversible"
    IRREVERSIBLE = "irreversible"


class BlastRadius(str, Enum):
    LOCAL_FILE = "local_file"
    LOCAL_RUNTIME = "local_runtime"
    SINGLE_SERVICE = "single_service"
    MULTI_SERVICE = "multi_service"
    CLUSTER_WIDE = "cluster_wide"
    EXTERNAL = "external"


class EnvelopeStatus(str, Enum):
    PROPOSED = "proposed"
    APPROVED = "approved"
    REJECTED = "rejected"
    EXECUTING = "executing"
    COMPLETED = "completed"
    FAILED = "failed"
    ROLLED_BACK = "rolled_back"
    VERIFIED = "verified"
    VERIFICATION_FAILED = "verification_failed"


@dataclass
class VerificationStrategy:
    description: str
    verify_fn: Callable[[], bool] | None = None
    timeout_seconds: float = 30.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "description": self.description,
            "has_verify_fn": self.verify_fn is not None,
            "timeout_seconds": self.timeout_seconds,
        }


@dataclass
class RollbackStrategy:
    description: str
    rollback_fn: Callable[[], bool] | None = None
    timeout_seconds: float = 30.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "description": self.description,
            "has_rollback_fn": self.rollback_fn is not None,
            "timeout_seconds": self.timeout_seconds,
        }


@dataclass
class ExecutionConstraints:
    max_retries: int = 0
    timeout_seconds: float = 60.0
    require_approval: bool = False
    require_quorum: bool = False
    idempotent: bool = False
    isolated: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "max_retries": self.max_retries,
            "timeout_seconds": self.timeout_seconds,
            "require_approval": self.require_approval,
            "require_quorum": self.require_quorum,
            "idempotent": self.idempotent,
            "isolated": self.isolated,
        }


@dataclass
class ActionEnvelope:
    """The single canonical object for every organism mutation.

    Produced by subsystems (WorkloadRunner, MaintenanceLoop,
    AssistedExecutor, Advisor, etc.).
    Consumed exclusively by GovernedExecutionSpine.
    """

    intent: str
    action_type: ActionType
    source: str
    execute_fn: Callable[[], tuple[str, bool]]

    envelope_id: str = field(default_factory=lambda: uuid4().hex[:16])
    objective_id: str = ""
    risk_level: str = "low"
    blast_radius: BlastRadius = BlastRadius.LOCAL_RUNTIME
    reversibility: ReversibilityClass = ReversibilityClass.FULLY_REVERSIBLE
    verification: VerificationStrategy | None = None
    rollback: RollbackStrategy | None = None
    constraints: ExecutionConstraints = field(default_factory=ExecutionConstraints)
    required_capabilities: list[str] = field(default_factory=list)
    estimated_manual_seconds: float = 60.0
    estimated_cost: float = 0.0
    metadata: dict[str, Any] = field(default_factory=dict)

    status: EnvelopeStatus = EnvelopeStatus.PROPOSED
    result_output: str = ""
    result_success: bool = False
    retry_count: int = 0
    created_at: float = field(default_factory=time.time)
    started_at: float = 0.0
    completed_at: float = 0.0
    approved_by: str = ""
    rejected_reason: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "envelope_id": self.envelope_id,
            "intent": self.intent,
            "action_type": self.action_type.value,
            "source": self.source,
            "objective_id": self.objective_id,
            "risk_level": self.risk_level,
            "blast_radius": self.blast_radius.value,
            "reversibility": self.reversibility.value,
            "status": self.status.value,
            "result_output": self.result_output[:500],
            "result_success": self.result_success,
            "retry_count": self.retry_count,
            "constraints": self.constraints.to_dict(),
            "required_capabilities": self.required_capabilities,
            "estimated_manual_seconds": self.estimated_manual_seconds,
            "estimated_cost": self.estimated_cost,
            "metadata": self.metadata,
            "created_at": self.created_at,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
            "approved_by": self.approved_by,
            "rejected_reason": self.rejected_reason,
            "verification": self.verification.to_dict() if self.verification else None,
            "rollback": self.rollback.to_dict() if self.rollback else None,
        }
