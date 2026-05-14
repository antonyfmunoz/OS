"""Canonical Constitutional Explainability Coordinator v1.

Coordinates deterministic constitutional explainability across
all substrate layers. Generates explanation receipts.

Must NEVER: invent reasoning, synthesize unstored causes,
hallucinate lineage, mutate runtime state, bypass replay
evidence, bypass constitutional runtime.

All explanations derive ONLY from: runtime lineage, replay
traces, governance receipts, continuity chains, observability
events, topology graphs, certification artifacts.

UMH substrate subsystem. Phase 96.8CK.
"""

from __future__ import annotations

from typing import Any

from core.explainability.constitutional_explainability_contracts_v1 import (
    ConstitutionalExplanationState,
    ConstitutionalExplanationReceipt,
    _now_iso,
    _deterministic_id,
)
from core.explainability.explainability_lifecycle_engine_v1 import (
    ExplainabilityLifecycleEngine,
)
from core.explainability.causal_lineage_reconstruction_engine_v1 import (
    CausalLineageReconstructionEngine,
)
from core.explainability.governance_justification_engine_v1 import (
    GovernanceJustificationEngine,
)
from core.explainability.replay_accountability_engine_v1 import (
    ReplayAccountabilityEngine,
)
from core.explainability.continuity_accountability_engine_v1 import (
    ContinuityAccountabilityEngine,
)
from core.explainability.operational_provenance_graph_engine_v1 import (
    OperationalProvenanceGraphEngine,
)
from core.explainability.constitutional_reasoning_engine_v1 import (
    ConstitutionalReasoningEngine,
)
from core.explainability.explainability_observability_pipeline_v1 import (
    ExplainabilityObservabilityPipeline,
)
from core.explainability.constitutional_explainability_replay_validator_v1 import (
    ConstitutionalExplainabilityReplayValidator,
)
from core.explainability.explainability_boundary_policies_v1 import (
    ExplainabilityBoundaryPolicies,
)


MAX_EXPLANATION_RUNS = 50


class CanonicalConstitutionalExplainabilityCoordinator:
    """Coordinates constitutional explainability.

    Cannot invent reasoning.
    Cannot synthesize unstored causes.
    Cannot hallucinate lineage.
    Cannot mutate runtime state.
    Cannot bypass replay evidence.
    Cannot bypass constitutional runtime.
    """

    def __init__(self, state_dir: str = "") -> None:
        self._lifecycle = ExplainabilityLifecycleEngine()
        self._lineage = CausalLineageReconstructionEngine()
        self._governance = GovernanceJustificationEngine()
        self._replay = ReplayAccountabilityEngine()
        self._continuity = ContinuityAccountabilityEngine()
        self._provenance = OperationalProvenanceGraphEngine()
        self._reasoning = ConstitutionalReasoningEngine()
        self._obs_pipeline = ExplainabilityObservabilityPipeline(output_dir=state_dir)
        self._replay_validator = ConstitutionalExplainabilityReplayValidator()
        self._boundary = ExplainabilityBoundaryPolicies()

        self._explanations: list[ConstitutionalExplanationState] = []
        self._receipts: list[ConstitutionalExplanationReceipt] = []

    def start_explanation(self, run_id: str = "") -> dict[str, Any]:
        if len(self._explanations) >= MAX_EXPLANATION_RUNS:
            raise ValueError("Max explanation runs reached")
        if not run_id:
            run_id = _deterministic_id("exprun-", _now_iso())
        state = ConstitutionalExplanationState(domain="all", decision_id=run_id)
        self._explanations.append(state)
        self._obs_pipeline.emit_explanation_requested({"run_id": run_id})
        return {"run_id": run_id, "status": "started"}

    def reconstruct_lineage(self) -> dict[str, Any]:
        result = self._lineage.reconstruct_all_domains()
        self._obs_pipeline.emit_lineage_reconstructed({"total": result["total"]})
        return result

    def justify_governance(self) -> dict[str, Any]:
        result = self._governance.justify_all_types()
        self._obs_pipeline.emit_governance_reasoning_reconstructed({"total": result["total"]})
        return result

    def explain_replay(self) -> dict[str, Any]:
        result = self._replay.explain_all_domains()
        self._obs_pipeline.emit_replay_explanation_generated({"total": result["total"]})
        return result

    def explain_continuity(self) -> dict[str, Any]:
        result = self._continuity.explain_all_domains()
        self._obs_pipeline.emit_continuity_explanation_generated({"total": result["total"]})
        return result

    def generate_provenance(self) -> dict[str, Any]:
        result = self._provenance.generate_all_domains()
        self._obs_pipeline.emit_provenance_graph_generated({"total": result["total"]})
        return result

    def generate_reasoning(self) -> dict[str, Any]:
        result = self._reasoning.generate_all_domains()
        self._obs_pipeline.emit_constitutional_reasoning_generated({"total": result["total"]})
        return result

    def validate_replay_determinism(self) -> dict[str, Any]:
        return self._replay_validator.validate_all()

    def check_boundary(self, limit_name: str, current_value: int) -> dict[str, Any]:
        return self._boundary.check_limit(limit_name, current_value)

    def complete_explanation(self, run_id: str) -> dict[str, Any]:
        all_explained = all([
            self._lineage.all_deterministic(),
            self._governance.all_justified(),
            self._replay.all_deterministic(),
            self._continuity.all_valid(),
            self._provenance.all_deterministic(),
            self._reasoning.all_justified(),
            self._replay_validator.all_deterministic(),
        ])

        outcome = "explained" if all_explained else "incomplete"
        explanations_generated = (
            self._lineage.get_stats()["total_traces"]
            + self._governance.get_stats()["total_justifications"]
            + self._replay.get_stats()["total_explanations"]
            + self._continuity.get_stats()["total_explanations"]
            + self._provenance.get_stats()["total_graphs"]
            + self._reasoning.get_stats()["total_traces"]
        )

        receipt = ConstitutionalExplanationReceipt(
            run_id=run_id,
            outcome=outcome,
            explanations_generated=explanations_generated,
        )
        self._receipts.append(receipt)
        self._obs_pipeline.emit_explanation_completed(
            {"run_id": run_id, "outcome": outcome},
        )
        return receipt.to_dict()

    def get_explainability_report(self) -> dict[str, Any]:
        return {
            "lineage": self._lineage.get_stats(),
            "governance": self._governance.get_stats(),
            "replay": self._replay.get_stats(),
            "continuity": self._continuity.get_stats(),
            "provenance": self._provenance.get_stats(),
            "reasoning": self._reasoning.get_stats(),
            "replay_validator": self._replay_validator.get_stats(),
            "all_explained": all([
                self._lineage.all_deterministic(),
                self._governance.all_justified(),
                self._replay.all_deterministic(),
                self._continuity.all_valid(),
                self._provenance.all_deterministic(),
                self._reasoning.all_justified(),
            ]),
        }

    def get_stats(self) -> dict[str, Any]:
        return {
            "lifecycle": self._lifecycle.get_stats(),
            "lineage": self._lineage.get_stats(),
            "governance": self._governance.get_stats(),
            "replay": self._replay.get_stats(),
            "continuity": self._continuity.get_stats(),
            "provenance": self._provenance.get_stats(),
            "reasoning": self._reasoning.get_stats(),
            "replay_validator": self._replay_validator.get_stats(),
            "boundary": self._boundary.get_stats(),
            "obs_pipeline": self._obs_pipeline.get_stats(),
            "explanations": len(self._explanations),
            "receipts": len(self._receipts),
        }
