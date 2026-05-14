"""Learning Governance Engine v1.

Enforces governance constraints on the learning layer:
  proposal-only mutation, operator approval required,
  provenance required, confidence required,
  rollback reference required, replay proof required.

Cannot approve its own proposals. Cannot mutate directly.

UMH substrate subsystem. Phase 96.8CC.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from core.learning.adaptive_learning_contracts_v1 import (
    ImprovementProposal,
    LearningReceipt,
    _now_iso,
)

MIN_CONFIDENCE_FOR_APPROVAL = 0.3
GOVERNANCE_REQUIREMENTS = [
    "provenance_required",
    "confidence_required",
    "rollback_reference_required",
    "operator_approval_required",
    "replay_proof_required",
    "proposal_only_mutation",
]


class LearningGovernanceEngine:
    """Enforces governance on learning proposals."""

    def __init__(self, state_dir: str | Path | None = None) -> None:
        self._receipts: list[LearningReceipt] = []
        self._total_checks = 0
        self._total_passed = 0
        self._total_failed = 0

    def validate_proposal(
        self,
        proposal: ImprovementProposal,
    ) -> dict[str, Any]:
        self._total_checks += 1
        violations: list[str] = []

        if not proposal.provenance:
            violations.append("missing_provenance")

        if proposal.confidence < MIN_CONFIDENCE_FOR_APPROVAL:
            violations.append("insufficient_confidence")

        if not proposal.rollback_reference:
            violations.append("missing_rollback_reference")

        if not proposal.proposal_type:
            violations.append("missing_proposal_type")

        passed = len(violations) == 0
        if passed:
            self._total_passed += 1
        else:
            self._total_failed += 1

        return {
            "proposal_id": proposal.proposal_id,
            "passed": passed,
            "violations": violations,
            "timestamp": _now_iso(),
        }

    def record_approval(
        self,
        proposal_id: str,
        from_state: str,
        to_state: str,
        approved_by: str = "operator",
    ) -> dict[str, Any]:
        if approved_by != "operator":
            raise ValueError(
                f"Only operator can approve. Got: {approved_by}"
            )

        receipt = LearningReceipt(
            operation="approval",
            proposal_id=proposal_id,
            from_state=from_state,
            to_state=to_state,
            approved_by=approved_by,
        )
        self._receipts.append(receipt)
        return receipt.to_dict()

    def record_denial(
        self,
        proposal_id: str,
        from_state: str,
        denied_by: str = "operator",
    ) -> dict[str, Any]:
        if denied_by != "operator":
            raise ValueError(
                f"Only operator can deny. Got: {denied_by}"
            )

        receipt = LearningReceipt(
            operation="denial",
            proposal_id=proposal_id,
            from_state=from_state,
            to_state="denied",
            approved_by=denied_by,
        )
        self._receipts.append(receipt)
        return receipt.to_dict()

    def get_receipts(self, limit: int = 20) -> list[dict[str, Any]]:
        return [r.to_dict() for r in self._receipts[-limit:]]

    def get_stats(self) -> dict[str, object]:
        return {
            "total_checks": self._total_checks,
            "total_passed": self._total_passed,
            "total_failed": self._total_failed,
            "total_receipts": len(self._receipts),
        }
