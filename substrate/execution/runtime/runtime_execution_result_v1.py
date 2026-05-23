"""Runtime Execution Result v1 for the UMH substrate layer.

Deterministic execution result with proof chain. Every runtime
execution produces a result with hash-verified evidence, adapter
boundary proof, and execution trace linkage.

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


# NOTE: The canonical ExecutionOutcome is in substrate.types (Pydantic enum).
# This is a runtime-scoped version with CANCELLED and REQUIRES_APPROVAL values.
from substrate.types import ExecutionOutcome as CanonicalExecutionOutcome  # noqa: F401


class ExecutionOutcome(str, Enum):
    SUCCESS = "success"
    FAILURE = "failure"
    TIMEOUT = "timeout"
    CANCELLED = "cancelled"
    REQUIRES_APPROVAL = "requires_approval"


class ProofArtifactType(str, Enum):
    DISPATCH_PROOF = "dispatch_proof"
    RUNTIME_ACCEPTANCE_PROOF = "runtime_acceptance_proof"
    HEARTBEAT_PROOF = "heartbeat_proof"
    EXECUTION_PROOF = "execution_proof"
    CHROME_LAUNCH_PROOF = "chrome_launch_proof"
    ADAPTER_BOUNDARY_PROOF = "adapter_boundary_proof"
    REPLAY_PROOF = "replay_proof"
    RECOVERY_PROOF = "recovery_proof"


@dataclass
class ProofArtifact:
    """A single proof artifact from runtime execution."""

    proof_id: str
    proof_type: ProofArtifactType
    content_hash: str = ""
    evidence: dict[str, Any] = field(default_factory=dict)
    timestamp: str = ""
    worker_id: str = ""
    adapter_id: str = ""
    notes: list[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        if not self.timestamp:
            self.timestamp = datetime.now(timezone.utc).isoformat()
        if not self.proof_id:
            self.proof_id = f"PROOF-{uuid.uuid4().hex[:8]}"
        if not self.content_hash and self.evidence:
            payload = json.dumps(self.evidence, sort_keys=True)
            self.content_hash = hashlib.sha256(payload.encode()).hexdigest()

    def to_dict(self) -> dict[str, Any]:
        return {
            "proof_id": self.proof_id,
            "proof_type": self.proof_type.value,
            "content_hash": self.content_hash,
            "evidence": self.evidence,
            "timestamp": self.timestamp,
            "worker_id": self.worker_id,
            "adapter_id": self.adapter_id,
            "notes": self.notes,
        }


@dataclass
class RuntimeExecutionResult:
    """Complete result of a runtime execution with proof chain."""

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
    duration_seconds: float = 0.0
    proof_artifacts: list[ProofArtifact] = field(default_factory=list)
    governance_trace_id: str = ""
    execution_lineage_id: str = ""
    result_hash: str = ""
    error_message: str = ""
    notes: list[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        if not self.result_id:
            self.result_id = f"EXEC-RESULT-{uuid.uuid4().hex[:8]}"

    def compute_result_hash(self) -> str:
        payload = json.dumps(
            {
                "result_id": self.result_id,
                "dispatch_id": self.dispatch_id,
                "packet_id": self.packet_id,
                "outcome": self.outcome.value,
                "action_type": self.action_type,
                "proof_hashes": sorted(
                    p.content_hash for p in self.proof_artifacts if p.content_hash
                ),
            },
            sort_keys=True,
        )
        self.result_hash = hashlib.sha256(payload.encode()).hexdigest()
        return self.result_hash

    @property
    def succeeded(self) -> bool:
        return self.outcome == ExecutionOutcome.SUCCESS

    @property
    def proof_count(self) -> int:
        return len(self.proof_artifacts)

    def to_dict(self) -> dict[str, Any]:
        return {
            "result_id": self.result_id,
            "dispatch_id": self.dispatch_id,
            "packet_id": self.packet_id,
            "worker_id": self.worker_id,
            "session_id": self.session_id,
            "action_type": self.action_type,
            "outcome": self.outcome.value,
            "adapter_id": self.adapter_id,
            "environment_type": self.environment_type,
            "execution_started_at": self.execution_started_at,
            "execution_completed_at": self.execution_completed_at,
            "duration_seconds": self.duration_seconds,
            "proof_artifacts": [p.to_dict() for p in self.proof_artifacts],
            "governance_trace_id": self.governance_trace_id,
            "execution_lineage_id": self.execution_lineage_id,
            "result_hash": self.result_hash,
            "error_message": self.error_message,
            "succeeded": self.succeeded,
            "proof_count": self.proof_count,
            "notes": self.notes,
        }


def persist_execution_result(result: RuntimeExecutionResult, proof_dir: Path) -> Path:
    """Persist execution result to proof directory."""
    proof_dir.mkdir(parents=True, exist_ok=True)
    path = proof_dir / f"{result.result_id}.json"
    path.write_text(json.dumps(result.to_dict(), indent=2))
    return path
