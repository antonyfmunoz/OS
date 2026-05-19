"""Work packet executor — the governed execution pipeline."""

from __future__ import annotations

import time
from datetime import datetime, timezone
from typing import Any, Protocol
from uuid import UUID

from services.umh.execution.proof_generator import ProofGenerator
from services.umh.governance.risk_classes import RiskClass
from services.umh.protocols.execution_result import ExecutionOutcome, ExecutionResult
from services.umh.protocols.governance import GovernanceDecision, GovernanceVerdict
from services.umh.protocols.proof import Proof
from services.umh.protocols.work_packet import WorkPacket, WorkPacketStatus


class AdapterProtocol(Protocol):
    """Minimal interface an adapter must satisfy for the executor."""

    @property
    def name(self) -> str: ...

    def execute(self, operation: str, params: dict[str, Any]) -> dict[str, Any]: ...

    def classify_risk(self, operation: str, params: dict[str, Any]) -> RiskClass: ...


class ExecutionBundle:
    """The complete output of a work packet execution."""

    def __init__(
        self,
        result: ExecutionResult,
        proof: Proof,
        governance_proof: Proof,
    ) -> None:
        self.result = result
        self.proof = proof
        self.governance_proof = governance_proof


class WorkPacketExecutor:
    """Executes work packets through the governance → adapter → proof pipeline.

    Flow:
    1. Receive typed work packet + governance verdict
    2. Verify verdict allows execution
    3. Select adapter and classify risk
    4. Execute via adapter
    5. Return ExecutionResult + ProofArtifact
    6. Never writes memory directly
    """

    def __init__(self) -> None:
        self._adapters: dict[str, AdapterProtocol] = {}
        self._proof_gen = ProofGenerator()

    def register_adapter(self, adapter: AdapterProtocol) -> None:
        self._adapters[adapter.name] = adapter

    def get_adapter(self, name: str) -> AdapterProtocol | None:
        return self._adapters.get(name)

    @property
    def registered_adapters(self) -> list[str]:
        return list(self._adapters.keys())

    def execute(
        self,
        packet: WorkPacket,
        verdict: GovernanceVerdict,
        adapter_name: str,
        operation: str,
        params: dict[str, Any] | None = None,
    ) -> ExecutionBundle:
        """Execute a work packet through the governed pipeline."""
        params = params or {}

        governance_proof = self._proof_gen.generate_governance_proof(
            verdict,
            risk_class_name=params.get("_risk_class", "unknown"),
        )

        if not verdict.is_executable():
            result = ExecutionResult(
                work_packet_id=packet.id,
                trace_id=packet.trace_id,
                outcome=ExecutionOutcome.REJECTED,
                error=f"governance denied: {verdict.rationale}",
                metadata={"governance_decision": verdict.decision.value},
            )
            proof = self._proof_gen.generate(packet, verdict, result, adapter_name)
            return ExecutionBundle(result, proof, governance_proof)

        adapter = self._adapters.get(adapter_name)
        if adapter is None:
            result = ExecutionResult(
                work_packet_id=packet.id,
                trace_id=packet.trace_id,
                outcome=ExecutionOutcome.FAILURE,
                error=f"adapter not registered: {adapter_name}",
            )
            proof = self._proof_gen.generate(packet, verdict, result, adapter_name)
            return ExecutionBundle(result, proof, governance_proof)

        packet.status = WorkPacketStatus.IN_PROGRESS
        packet.started_at = datetime.now(timezone.utc)
        packet.attempt += 1

        t0 = time.monotonic()
        try:
            output = adapter.execute(operation, params)
            duration = (time.monotonic() - t0) * 1000

            side_effects = output.pop("_side_effects", [])
            if not isinstance(side_effects, list):
                side_effects = []

            result = ExecutionResult(
                work_packet_id=packet.id,
                trace_id=packet.trace_id,
                outcome=ExecutionOutcome.SUCCESS,
                output_data=output,
                duration_ms=duration,
                side_effects=side_effects,
            )
            packet.status = WorkPacketStatus.COMPLETED
            packet.completed_at = datetime.now(timezone.utc)

        except PermissionError as exc:
            duration = (time.monotonic() - t0) * 1000
            result = ExecutionResult(
                work_packet_id=packet.id,
                trace_id=packet.trace_id,
                outcome=ExecutionOutcome.REJECTED,
                error=f"permission denied: {exc}",
                duration_ms=duration,
            )
            packet.status = WorkPacketStatus.FAILED

        except TimeoutError as exc:
            duration = (time.monotonic() - t0) * 1000
            result = ExecutionResult(
                work_packet_id=packet.id,
                trace_id=packet.trace_id,
                outcome=ExecutionOutcome.TIMEOUT,
                error=str(exc),
                duration_ms=duration,
            )
            packet.status = WorkPacketStatus.FAILED

        except Exception as exc:
            duration = (time.monotonic() - t0) * 1000
            result = ExecutionResult(
                work_packet_id=packet.id,
                trace_id=packet.trace_id,
                outcome=ExecutionOutcome.FAILURE,
                error=f"{type(exc).__name__}: {exc}",
                duration_ms=duration,
            )
            packet.status = WorkPacketStatus.FAILED

        proof = self._proof_gen.generate(packet, verdict, result, adapter_name)
        return ExecutionBundle(result, proof, governance_proof)
