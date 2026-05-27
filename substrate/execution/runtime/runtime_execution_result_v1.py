"""Runtime Execution Result v1 — proof-bearing execution result type.

Defines the structured result returned by the Local Runtime Supervisor
after executing a governed WorkPacket through the adapter boundary.

UMH substrate subsystem.
"""

from __future__ import annotations

import hashlib
import json
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any


class ExecutionOutcome(str, Enum):
    SUCCESS = "success"
    PARTIAL_SUCCESS = "partial_success"
    FAILURE = "failure"
    TIMEOUT = "timeout"
    BLOCKED = "blocked"
    REJECTED = "rejected"


class ProofArtifactType(str, Enum):
    DISPATCH_PROOF = "dispatch_proof"
    RUNTIME_ACCEPTANCE_PROOF = "runtime_acceptance_proof"
    HEARTBEAT_PROOF = "heartbeat_proof"
    ADAPTER_BOUNDARY_PROOF = "adapter_boundary_proof"
    CHROME_LAUNCH_PROOF = "chrome_launch_proof"
    EXECUTION_PROOF = "execution_proof"
    REPLAY_PROOF = "replay_proof"
    RECOVERY_PROOF = "recovery_proof"


@dataclass
class ProofArtifact:
    """A proof artifact attached to an execution result."""

    proof_id: str
    proof_type: ProofArtifactType
    evidence: dict[str, Any] = field(default_factory=dict)
    worker_id: str = ""
    adapter_id: str = ""
    timestamp: str = ""

    def __post_init__(self) -> None:
        if not self.proof_id:
            self.proof_id = f"PROOF-{uuid.uuid4().hex[:8]}"
        if not self.timestamp:
            self.timestamp = datetime.now(timezone.utc).isoformat()

    def to_dict(self) -> dict[str, Any]:
        return {
            "proof_id": self.proof_id,
            "proof_type": self.proof_type.value,
            "evidence": self.evidence,
            "worker_id": self.worker_id,
            "adapter_id": self.adapter_id,
            "timestamp": self.timestamp,
        }


@dataclass
class RuntimeExecutionResult:
    """Complete result of a governed runtime execution."""

    result_id: str
    dispatch_id: str
    packet_id: str
    worker_id: str
    session_id: str
    action_type: str
    outcome: ExecutionOutcome
    adapter_id: str = ""
    environment_type: str = ""
    execution_started_at: str = ""
    execution_completed_at: str = ""
    proof_artifacts: list[ProofArtifact] = field(default_factory=list)
    governance_trace_id: str = ""
    execution_lineage_id: str = ""
    error_message: str = ""
    result_hash: str = ""

    def __post_init__(self) -> None:
        if not self.result_id:
            self.result_id = f"RESULT-{uuid.uuid4().hex[:8]}"

    @property
    def succeeded(self) -> bool:
        return self.outcome in (ExecutionOutcome.SUCCESS, ExecutionOutcome.PARTIAL_SUCCESS)

    def compute_result_hash(self) -> str:
        payload = json.dumps(
            {
                "result_id": self.result_id,
                "packet_id": self.packet_id,
                "outcome": self.outcome.value,
                "proof_count": len(self.proof_artifacts),
            },
            sort_keys=True,
        )
        self.result_hash = hashlib.sha256(payload.encode()).hexdigest()[:16]
        return self.result_hash

    def to_dict(self) -> dict[str, Any]:
        return {
            "result_id": self.result_id,
            "dispatch_id": self.dispatch_id,
            "packet_id": self.packet_id,
            "worker_id": self.worker_id,
            "session_id": self.session_id,
            "action_type": self.action_type,
            "outcome": self.outcome.value,
            "succeeded": self.succeeded,
            "adapter_id": self.adapter_id,
            "environment_type": self.environment_type,
            "execution_started_at": self.execution_started_at,
            "execution_completed_at": self.execution_completed_at,
            "proof_artifacts": [p.to_dict() for p in self.proof_artifacts],
            "governance_trace_id": self.governance_trace_id,
            "execution_lineage_id": self.execution_lineage_id,
            "error_message": self.error_message,
            "result_hash": self.result_hash,
        }


def persist_execution_result(result: RuntimeExecutionResult, proof_dir: Path) -> Path:
    """Persist an execution result as JSON to the proof directory."""
    proof_dir.mkdir(parents=True, exist_ok=True)
    out_path = proof_dir / f"{result.result_id}.json"
    out_path.write_text(json.dumps(result.to_dict(), indent=2, default=str))
    return out_path
