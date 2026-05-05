"""Result ingestion for the Environment Bridge.

Validates and ingests result artifacts from local worker execution.
Checks proof completeness, governance compliance, and founder
confirmation requirements.

UMH substrate subsystem. EOS is one platform consumer.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from .work_packet import WorkPacket


class BridgeResultStatus(str, Enum):
    RECEIVED = "received"
    VALID = "valid"
    INVALID = "invalid"
    PROOF_INCOMPLETE = "proof_incomplete"
    GOVERNANCE_VIOLATION = "governance_violation"
    INGESTED = "ingested"
    BLOCKED = "blocked"


@dataclass
class BridgeResult:
    packet_id: str = ""
    work_order_id: str = ""
    status: BridgeResultStatus = BridgeResultStatus.RECEIVED
    execution_environment: str = ""
    completed_at: str = ""
    outputs: list[str] = field(default_factory=list)
    proof_artifacts: list[str] = field(default_factory=list)
    governance_report: dict[str, bool] = field(default_factory=dict)
    no_secret_confirmed: bool = False
    no_mutation_confirmed: bool = False
    founder_confirmation_required: bool = False
    founder_confirmation_status: str = "not_confirmed"
    errors: list[str] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "packet_id": self.packet_id,
            "work_order_id": self.work_order_id,
            "status": self.status.value,
            "execution_environment": self.execution_environment,
            "completed_at": self.completed_at,
            "outputs": self.outputs,
            "proof_artifacts": self.proof_artifacts,
            "governance_report": self.governance_report,
            "no_secret_confirmed": self.no_secret_confirmed,
            "no_mutation_confirmed": self.no_mutation_confirmed,
            "founder_confirmation_required": self.founder_confirmation_required,
            "founder_confirmation_status": self.founder_confirmation_status,
            "errors": self.errors,
            "notes": self.notes,
        }


def build_bridge_result(
    packet_id: str,
    work_order_id: str = "",
    execution_environment: str = "",
    outputs: list[str] | None = None,
    proof_artifacts: list[str] | None = None,
    governance_report: dict[str, bool] | None = None,
    no_secret_confirmed: bool = False,
    no_mutation_confirmed: bool = False,
    founder_confirmation_required: bool = False,
    founder_confirmation_status: str = "not_confirmed",
) -> BridgeResult:
    return BridgeResult(
        packet_id=packet_id,
        work_order_id=work_order_id,
        execution_environment=execution_environment,
        outputs=outputs or [],
        proof_artifacts=proof_artifacts or [],
        governance_report=governance_report or {},
        no_secret_confirmed=no_secret_confirmed,
        no_mutation_confirmed=no_mutation_confirmed,
        founder_confirmation_required=founder_confirmation_required,
        founder_confirmation_status=founder_confirmation_status,
    )


def validate_bridge_result(result: BridgeResult) -> BridgeResult:
    if not result.no_secret_confirmed:
        result.errors.append("NO_SECRET_CONFIRMATION_MISSING")
    if not result.no_mutation_confirmed:
        result.errors.append("NO_MUTATION_CONFIRMATION_MISSING")

    if result.governance_report:
        for check, passed in result.governance_report.items():
            if not passed:
                result.errors.append(f"GOVERNANCE_VIOLATION: {check}")

    if not result.proof_artifacts:
        result.errors.append("NO_PROOF_ARTIFACTS")

    governance_violations = [e for e in result.errors if "GOVERNANCE_VIOLATION" in e]
    if governance_violations:
        result.status = BridgeResultStatus.GOVERNANCE_VIOLATION
        return result

    if "NO_PROOF_ARTIFACTS" in result.errors:
        result.status = BridgeResultStatus.PROOF_INCOMPLETE
        return result

    secret_or_mutation_missing = (
        "NO_SECRET_CONFIRMATION_MISSING" in result.errors
        or "NO_MUTATION_CONFIRMATION_MISSING" in result.errors
    )
    if secret_or_mutation_missing:
        result.status = BridgeResultStatus.INVALID
        return result

    result.status = BridgeResultStatus.VALID
    return result


def result_satisfies_proof_requirements(result: BridgeResult, packet: WorkPacket) -> bool:
    if not packet.proof_requirements:
        return True
    if not result.proof_artifacts:
        return False
    return result.status in (
        BridgeResultStatus.VALID,
        BridgeResultStatus.INGESTED,
    )


def result_has_governance_compliance(result: BridgeResult) -> bool:
    if not result.no_secret_confirmed:
        return False
    if not result.no_mutation_confirmed:
        return False
    governance_violations = [e for e in result.errors if "GOVERNANCE_VIOLATION" in e]
    return len(governance_violations) == 0


def ingest_bridge_result(result: BridgeResult) -> BridgeResult:
    if result.status == BridgeResultStatus.VALID:
        result.status = BridgeResultStatus.INGESTED
    return result


def summarize_bridge_result(result: BridgeResult) -> dict[str, Any]:
    return {
        "packet_id": result.packet_id,
        "status": result.status.value,
        "execution_environment": result.execution_environment,
        "proof_artifact_count": len(result.proof_artifacts),
        "governance_compliant": result_has_governance_compliance(result),
        "no_secret_confirmed": result.no_secret_confirmed,
        "no_mutation_confirmed": result.no_mutation_confirmed,
        "founder_confirmation_required": result.founder_confirmation_required,
        "error_count": len(result.errors),
        "errors": result.errors,
    }
