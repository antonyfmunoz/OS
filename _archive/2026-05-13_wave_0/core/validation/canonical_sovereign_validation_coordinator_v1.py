"""Canonical Sovereign Validation Coordinator v1.

Coordinates adversarial sovereign validation across all
substrate layers. Generates sovereign validation receipts.

Must NEVER: adapt autonomously, heal autonomously,
defend autonomously, bypass constitutional runtime,
bypass canonical spine.

Validation is: adversarial, observational, governed,
bounded, deterministic.

UMH substrate subsystem. Phase 96.8CJ.
"""

from __future__ import annotations

from typing import Any

from core.validation.sovereign_operational_validation_contracts_v1 import (
    SovereignValidationState,
    SovereignValidationReceipt,
    _now_iso,
    _deterministic_id,
)
from core.validation.sovereign_validation_lifecycle_engine_v1 import (
    SovereignValidationLifecycleEngine,
)
from core.validation.governance_assault_engine_v1 import (
    GovernanceAssaultEngine,
)
from core.validation.replay_durability_engine_v1 import (
    SovereignReplayDurabilityEngine,
)
from core.validation.continuity_corruption_engine_v1 import (
    ContinuityCorruptionEngine,
)
from core.validation.topology_stress_engine_v1 import (
    TopologyStressEngine,
)
from core.validation.semantic_drift_assault_engine_v1 import (
    SemanticDriftAssaultEngine,
)
from core.validation.sovereign_integrity_engine_v1 import (
    SovereignIntegrityEngine,
)
from core.validation.runtime_pressure_engine_v1 import (
    RuntimePressureEngine,
)
from core.validation.sovereign_validation_observability_pipeline_v1 import (
    SovereignValidationObservabilityPipeline,
)
from core.validation.sovereign_validation_replay_validator_v1 import (
    SovereignValidationReplayValidator,
)
from core.validation.sovereign_validation_boundary_policies_v1 import (
    SovereignValidationBoundaryPolicies,
)


MAX_VALIDATION_RUNS = 50


class CanonicalSovereignValidationCoordinator:
    """Coordinates adversarial sovereign validation.

    Cannot adapt autonomously.
    Cannot heal autonomously.
    Cannot defend autonomously.
    Cannot bypass constitutional runtime.
    Cannot bypass canonical spine.
    """

    def __init__(self, state_dir: str = "") -> None:
        self._lifecycle = SovereignValidationLifecycleEngine()
        self._governance = GovernanceAssaultEngine()
        self._replay = SovereignReplayDurabilityEngine()
        self._continuity = ContinuityCorruptionEngine()
        self._topology = TopologyStressEngine()
        self._semantics = SemanticDriftAssaultEngine()
        self._integrity = SovereignIntegrityEngine()
        self._pressure = RuntimePressureEngine()
        self._obs_pipeline = SovereignValidationObservabilityPipeline(output_dir=state_dir)
        self._replay_validator = SovereignValidationReplayValidator()
        self._boundary = SovereignValidationBoundaryPolicies()

        self._runs: list[SovereignValidationState] = []
        self._receipts: list[SovereignValidationReceipt] = []

    def start_validation(self, run_id: str = "") -> dict[str, Any]:
        if len(self._runs) >= MAX_VALIDATION_RUNS:
            raise ValueError("Max validation runs reached")
        if not run_id:
            run_id = _deterministic_id("svrun-", _now_iso())
        state = SovereignValidationState(run_id=run_id)
        self._runs.append(state)
        self._obs_pipeline.emit_validation_started({"run_id": run_id})
        return {"run_id": run_id, "status": "started"}

    def assault_governance(self) -> dict[str, Any]:
        result = self._governance.simulate_all_attacks()
        self._obs_pipeline.emit_governance_attack_detected({"total": result["total"]})
        return result

    def assault_replay(self) -> dict[str, Any]:
        result = self._replay.simulate_all_attacks()
        self._obs_pipeline.emit_replay_attack_detected({"total": result["total"]})
        return result

    def assault_continuity(self) -> dict[str, Any]:
        result = self._continuity.simulate_all_attacks()
        self._obs_pipeline.emit_continuity_attack_detected({"total": result["total"]})
        return result

    def assault_topology(self) -> dict[str, Any]:
        result = self._topology.simulate_all_attacks()
        self._obs_pipeline.emit_topology_pressure_detected({"total": result["total"]})
        return result

    def assault_semantics(self) -> dict[str, Any]:
        result = self._semantics.simulate_all_attacks()
        self._obs_pipeline.emit_semantic_drift_detected({"total": result["total"]})
        return result

    def compute_sovereign_integrity(self) -> dict[str, Any]:
        integrity = self._integrity.compute_integrity(
            governance_integrity=self._governance.all_blocked(),
            replay_integrity=self._replay.all_preserved(),
            continuity_integrity=self._continuity.all_preserved(),
            topology_integrity=self._topology.all_preserved(),
            constitutional_integrity=True,
            observability_integrity=True,
            deployment_integrity=True,
        )
        self._obs_pipeline.emit_sovereign_integrity_computed(
            {"score": integrity["sovereign_integrity_score"]},
        )
        return integrity

    def apply_runtime_pressure(self, pressure_level: int = 50) -> dict[str, Any]:
        return self._pressure.apply_all_pressures(pressure_level=pressure_level)

    def validate_replay_determinism(self) -> dict[str, Any]:
        return self._replay_validator.validate_all()

    def check_boundary(self, limit_name: str, current_value: int) -> dict[str, Any]:
        return self._boundary.check_limit(limit_name, current_value)

    def complete_validation(self, run_id: str) -> dict[str, Any]:
        all_sovereign = all([
            self._governance.all_blocked(),
            self._replay.all_preserved(),
            self._continuity.all_preserved(),
            self._topology.all_preserved(),
            self._semantics.all_preserved(),
            self._integrity.all_sovereign(),
            self._pressure.all_bounded(),
            self._replay_validator.all_deterministic(),
        ])

        outcome = "sovereign" if all_sovereign else "compromised"
        attacks_blocked = (
            self._governance.get_stats()["blocked"]
            + self._replay.get_stats()["preserved"]
            + self._continuity.get_stats()["preserved"]
            + self._topology.get_stats()["preserved"]
            + self._semantics.get_stats()["preserved"]
        )

        receipt = SovereignValidationReceipt(
            run_id=run_id,
            outcome=outcome,
            scenarios_executed=len(self._runs),
            attacks_blocked=attacks_blocked,
        )
        self._receipts.append(receipt)
        self._obs_pipeline.emit_validation_completed(
            {"run_id": run_id, "outcome": outcome},
        )
        return receipt.to_dict()

    def get_sovereign_report(self) -> dict[str, Any]:
        return {
            "governance": self._governance.get_stats(),
            "replay": self._replay.get_stats(),
            "continuity": self._continuity.get_stats(),
            "topology": self._topology.get_stats(),
            "semantics": self._semantics.get_stats(),
            "integrity": self._integrity.get_stats(),
            "pressure": self._pressure.get_stats(),
            "replay_validator": self._replay_validator.get_stats(),
            "all_sovereign": all([
                self._governance.all_blocked(),
                self._replay.all_preserved(),
                self._continuity.all_preserved(),
                self._topology.all_preserved(),
                self._semantics.all_preserved(),
                self._integrity.all_sovereign(),
                self._pressure.all_bounded(),
            ]),
        }

    def get_stats(self) -> dict[str, Any]:
        return {
            "lifecycle": self._lifecycle.get_stats(),
            "governance": self._governance.get_stats(),
            "replay": self._replay.get_stats(),
            "continuity": self._continuity.get_stats(),
            "topology": self._topology.get_stats(),
            "semantics": self._semantics.get_stats(),
            "integrity": self._integrity.get_stats(),
            "pressure": self._pressure.get_stats(),
            "replay_validator": self._replay_validator.get_stats(),
            "boundary": self._boundary.get_stats(),
            "obs_pipeline": self._obs_pipeline.get_stats(),
            "runs": len(self._runs),
            "receipts": len(self._receipts),
        }
