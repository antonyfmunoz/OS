"""Canonical Adaptive Learning Coordinator v1.

Coordinates governed adaptive learning:
  signal collection, outcome classification, pattern detection,
  improvement proposals, governance, observability.

The learning layer may learn, score, compress, and propose.
The operator approves canonical change.
It NEVER mutates canon, policy, templates, or routing directly.

UMH substrate subsystem. Phase 96.8CC.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from core.learning.adaptive_learning_contracts_v1 import (
    LearningLifecycleState,
    _now_iso,
)
from core.learning.learning_lifecycle_engine_v1 import LearningLifecycleEngine
from core.learning.outcome_learning_engine_v1 import OutcomeLearningEngine
from core.learning.pattern_detection_engine_v1 import PatternDetectionEngine
from core.learning.improvement_proposal_engine_v1 import (
    ImprovementProposalEngine,
)
from core.learning.learning_governance_engine_v1 import (
    LearningGovernanceEngine,
)
from core.learning.learning_observability_pipeline_v1 import (
    LearningObservabilityPipeline,
)


class CanonicalAdaptiveLearningCoordinator:
    """Coordinates all adaptive learning operations.

    Cannot mutate canon directly. Cannot mutate policy directly.
    Cannot mutate routing directly. Cannot mutate templates directly.
    Cannot execute actions directly.
    All mutations require operator approval.
    """

    def __init__(
        self,
        state_dir: str | Path = "data/runtime/learning",
    ) -> None:
        self._state_dir = Path(state_dir)
        self._state_dir.mkdir(parents=True, exist_ok=True)

        self._lifecycle = LearningLifecycleEngine(state_dir=self._state_dir)
        self._outcomes = OutcomeLearningEngine(state_dir=self._state_dir)
        self._patterns = PatternDetectionEngine(state_dir=self._state_dir)
        self._proposals = ImprovementProposalEngine(
            state_dir=self._state_dir,
        )
        self._governance = LearningGovernanceEngine(
            state_dir=self._state_dir,
        )
        self._observability = LearningObservabilityPipeline(
            state_dir=self._state_dir / "observability",
        )

    def observe_signal(
        self,
        source: str,
        content: str,
        severity: float = 0.0,
        session_id: str = "",
    ) -> dict[str, Any]:
        signal = self._outcomes.observe(source, content, severity, session_id)

        self._observability.emit_learning_signal_observed(
            signal_id=signal["signal_id"], source=source,
        )

        pattern = self._patterns.ingest_signal(
            signal["signal_id"], source, content,
        )
        if pattern is not None:
            self._observability.emit_pattern_candidate_detected(
                pattern_id=pattern.pattern_id,
                pattern_type=pattern.pattern_type,
                confidence=pattern.confidence,
            )

        return signal

    def record_correction(
        self,
        original_action: str,
        corrected_action: str,
        reason: str = "",
    ) -> dict[str, Any]:
        return self._outcomes.record_correction(
            original_action, corrected_action, reason,
            corrected_by="operator",
        )

    def generate_proposal(
        self,
        proposal_type: str,
        description: str,
        pattern_id: str = "",
        confidence: float = 0.0,
        provenance: list[str] | None = None,
        rollback_reference: str = "",
    ) -> dict[str, Any] | None:
        proposal = self._proposals.generate(
            proposal_type=proposal_type,
            description=description,
            pattern_id=pattern_id,
            confidence=confidence,
            provenance=provenance,
            rollback_reference=rollback_reference,
        )
        if proposal is None:
            self._observability.emit_learning_boundary_denied(
                action="generate_proposal",
                reason=f"rejected: type={proposal_type} conf={confidence}",
            )
            return None

        validation = self._governance.validate_proposal(proposal)

        self._observability.emit_proposal_generated(
            proposal_id=proposal.proposal_id,
            proposal_type=proposal_type,
        )

        result = proposal.to_dict()
        result["governance_validation"] = validation
        return result

    def approve_proposal(self, proposal_id: str) -> dict[str, Any] | None:
        proposal = self._proposals.approve(
            proposal_id, approved_by="operator",
        )
        if proposal is None:
            return None

        self._governance.record_approval(
            proposal_id=proposal_id,
            from_state="pending",
            to_state="approved",
            approved_by="operator",
        )

        self._observability.emit_proposal_approved(
            proposal_id=proposal_id, approved_by="operator",
        )

        return proposal.to_dict()

    def deny_proposal(self, proposal_id: str) -> dict[str, Any] | None:
        proposal = self._proposals.deny(
            proposal_id, denied_by="operator",
        )
        if proposal is None:
            return None

        self._governance.record_denial(
            proposal_id=proposal_id,
            from_state="pending",
            denied_by="operator",
        )

        self._observability.emit_proposal_denied(
            proposal_id=proposal_id, reason="operator_denied",
        )

        return proposal.to_dict()

    def mark_applied(self, proposal_id: str) -> dict[str, Any] | None:
        proposal = self._proposals.mark_applied(proposal_id)
        return proposal.to_dict() if proposal else None

    def get_learning_state(self) -> dict[str, Any]:
        return self._outcomes.get_outcome_state()

    def get_signals(self, limit: int = 50) -> list[dict[str, Any]]:
        return self._outcomes.get_signals(limit)

    def get_signals_by_source(self, source: str) -> list[dict[str, Any]]:
        return self._outcomes.get_signals_by_source(source)

    def get_corrections(self, limit: int = 20) -> list[dict[str, Any]]:
        return self._outcomes.get_corrections(limit)

    def get_patterns(self, limit: int = 50) -> list[dict[str, Any]]:
        return self._patterns.get_patterns(limit)

    def get_patterns_by_type(
        self,
        pattern_type: str,
    ) -> list[dict[str, Any]]:
        return self._patterns.get_patterns_by_type(pattern_type)

    def get_high_confidence_patterns(
        self,
        threshold: float = 0.5,
    ) -> list[dict[str, Any]]:
        return self._patterns.get_high_confidence(threshold)

    def get_pending_proposals(self) -> list[dict[str, Any]]:
        return self._proposals.get_pending()

    def get_completed_proposals(self, limit: int = 20) -> list[dict[str, Any]]:
        return self._proposals.get_completed(limit)

    def get_governance_receipts(self, limit: int = 20) -> list[dict[str, Any]]:
        return self._governance.get_receipts(limit)

    def get_health(self) -> dict[str, Any]:
        return {
            "lifecycle_state": self._lifecycle.current_state,
            "outcomes": self._outcomes.get_stats(),
            "patterns": self._patterns.get_stats(),
            "proposals": self._proposals.get_stats(),
        }

    def get_stats(self) -> dict[str, Any]:
        return {
            "lifecycle": self._lifecycle.get_stats(),
            "outcomes": self._outcomes.get_stats(),
            "patterns": self._patterns.get_stats(),
            "proposals": self._proposals.get_stats(),
            "governance": self._governance.get_stats(),
            "observability": self._observability.get_stats(),
        }
