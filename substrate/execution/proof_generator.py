"""Proof generator — creates verifiable proof artifacts from execution results."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from substrate.types import (
    ExecutionOutcome,
    PipelineExecutionResult as ExecutionResult,
    PipelineGovernanceVerdict as GovernanceVerdict,
    Proof,
    ProofStatus,
    ProofType,
    WorkPacket,
)


class ProofGenerator:
    """Generates Proof objects from execution outcomes.

    Each execution produces exactly one proof artifact.
    The proof links the work packet, governance verdict,
    and execution result into a single auditable record.
    """

    def generate(
        self,
        packet: WorkPacket,
        verdict: GovernanceVerdict,
        result: ExecutionResult,
        adapter_name: str,
    ) -> Proof:
        """Generate a proof artifact for a completed execution."""
        evidence: dict[str, Any] = {
            "work_packet_id": str(packet.id),
            "governance_verdict_id": str(verdict.id),
            "governance_decision": verdict.decision.value,
            "risk_level": verdict.risk_level.value,
            "adapter": adapter_name,
            "outcome": result.outcome.value,
            "duration_ms": result.duration_ms,
            "side_effects": result.side_effects,
        }

        if result.error:
            evidence["error"] = result.error
        if result.output_data:
            evidence["output_summary"] = _summarize_output(result.output_data)

        status = ProofStatus.VERIFIED if result.is_success() else ProofStatus.FAILED

        return Proof(
            proof_type=ProofType.EXECUTION,
            status=status,
            claim=f"executed {packet.description} via {adapter_name}",
            evidence=evidence,
            trace_id=packet.trace_id,
            verified_by="execution_engine",
            verified_at=datetime.now(timezone.utc) if status == ProofStatus.VERIFIED else None,
            metadata={
                "adapter": adapter_name,
                "packet_priority": packet.priority.value,
                "attempt": packet.attempt,
            },
        )

    def generate_governance_proof(
        self,
        verdict: GovernanceVerdict,
        risk_class_name: str,
    ) -> Proof:
        """Generate a proof artifact for a governance decision itself."""
        return Proof(
            proof_type=ProofType.GOVERNANCE,
            status=ProofStatus.VERIFIED,
            claim=f"governance evaluated {risk_class_name} → {verdict.decision.value}",
            evidence={
                "verdict_id": str(verdict.id),
                "request_id": str(verdict.request_id),
                "decision": verdict.decision.value,
                "risk_level": verdict.risk_level.value,
                "rationale": verdict.rationale,
                "decided_by": verdict.decided_by,
            },
            verified_by="proof_generator",
            verified_at=datetime.now(timezone.utc),
        )


def _summarize_output(data: dict[str, Any], max_keys: int = 10) -> dict[str, str]:
    """Produce a small summary of output data for evidence storage."""
    summary: dict[str, str] = {}
    for i, (k, v) in enumerate(data.items()):
        if i >= max_keys:
            summary["_truncated"] = f"{len(data) - max_keys} more keys"
            break
        val_str = str(v)
        summary[k] = val_str[:200] if len(val_str) > 200 else val_str
    return summary
