"""Canonical Operational Fabric Stabilization Coordinator v1.

Coordinates operational fabric stabilization across all substrate
layers. Stress-tests, validates durability, and hardens the
unified constitutional runtime fabric.

Must NEVER: mutate runtime topology silently, create hidden
execution paths, bypass constitutional runtime, bypass canonical spine.

UMH substrate subsystem. Phase 96.8CH.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from core.stabilization.constitutional_operational_fabric_contracts_v1 import (
    StabilizationScenario,
    FabricStabilityReceipt,
    _now_iso,
    _deterministic_id,
)
from core.stabilization.stabilization_lifecycle_engine_v1 import (
    StabilizationLifecycleEngine,
)
from core.stabilization.concurrency_durability_engine_v1 import (
    ConcurrencyDurabilityEngine,
)
from core.stabilization.replay_durability_engine_v1 import (
    ReplayDurabilityEngine,
)
from core.stabilization.continuity_durability_engine_v1 import (
    ContinuityDurabilityEngine,
)
from core.stabilization.topology_durability_engine_v1 import (
    TopologyDurabilityEngine,
)
from core.stabilization.resilience_interaction_engine_v1 import (
    ResilienceInteractionEngine,
)
from core.stabilization.stabilization_observability_pipeline_v1 import (
    StabilizationObservabilityPipeline,
)
from core.stabilization.stabilization_replay_validator_v1 import (
    StabilizationReplayValidator,
)
from core.stabilization.stabilization_boundary_policies_v1 import (
    StabilizationBoundaryPolicies,
)


MAX_SCENARIOS = 100
MAX_RUNS = 50


class CanonicalOperationalFabricStabilizationCoordinator:
    """Coordinates operational fabric stabilization.

    Cannot mutate runtime topology silently.
    Cannot create hidden execution paths.
    Cannot bypass constitutional runtime.
    Cannot bypass canonical spine.
    """

    def __init__(
        self,
        state_dir: str | Path = "data/runtime/stabilization",
    ) -> None:
        self._state_dir = Path(state_dir)
        self._state_dir.mkdir(parents=True, exist_ok=True)

        self._lifecycle = StabilizationLifecycleEngine()
        self._concurrency = ConcurrencyDurabilityEngine()
        self._replay = ReplayDurabilityEngine()
        self._continuity = ContinuityDurabilityEngine()
        self._topology = TopologyDurabilityEngine()
        self._resilience = ResilienceInteractionEngine()
        self._obs_pipeline = StabilizationObservabilityPipeline(
            state_dir=self._state_dir / "observability",
        )
        self._replay_validator = StabilizationReplayValidator()
        self._boundary = StabilizationBoundaryPolicies()

        self._scenarios: list[StabilizationScenario] = []
        self._receipts: list[FabricStabilityReceipt] = []

    def create_scenario(
        self,
        name: str,
        domain: str,
        intensity: str = "medium",
    ) -> dict[str, Any]:
        if len(self._scenarios) >= MAX_SCENARIOS:
            raise ValueError("Max scenarios reached")

        scenario = StabilizationScenario(
            name=name,
            domain=domain,
            intensity=intensity,
        )
        self._scenarios.append(scenario)
        return scenario.to_dict()

    def start_run(self, run_id: str = "") -> dict[str, Any]:
        if len(self._receipts) >= MAX_RUNS:
            raise ValueError("Max stabilization runs reached")

        if not run_id:
            run_id = _deterministic_id("run-", _now_iso())

        self._obs_pipeline.emit_stabilization_run_started(run_id=run_id)
        return {"run_id": run_id, "status": "started"}

    def complete_run(
        self,
        run_id: str,
        outcome: str = "stable",
        domains_validated: int = 0,
    ) -> dict[str, Any]:
        receipt = FabricStabilityReceipt(
            run_id=run_id,
            outcome=outcome,
            domains_validated=domains_validated,
        )
        self._receipts.append(receipt)

        self._obs_pipeline.emit_stabilization_run_completed(
            run_id=run_id, outcome=outcome,
        )

        return receipt.to_dict()

    def validate_concurrency(
        self,
        concurrent_operations: int,
        all_deterministic: bool = True,
        fanout_bounded: bool = True,
    ) -> dict[str, Any]:
        result = self._concurrency.validate_concurrency(
            concurrent_operations=concurrent_operations,
            all_deterministic=all_deterministic,
            fanout_bounded=fanout_bounded,
        )

        self._obs_pipeline.emit_concurrency_validated(
            concurrent_operations=concurrent_operations,
        )

        return result

    def validate_replay_durability(
        self,
        layers_validated: int,
        all_deterministic: bool = True,
        lineage_intact: bool = True,
    ) -> dict[str, Any]:
        result = self._replay.validate_replay_durability(
            layers_validated=layers_validated,
            all_deterministic=all_deterministic,
            lineage_intact=lineage_intact,
        )

        self._obs_pipeline.emit_replay_durability_validated(
            layers_validated=layers_validated,
        )

        return result

    def validate_continuity_durability(
        self,
        layers_validated: int,
        checkpoints_restored: int = 0,
        all_restored: bool = True,
    ) -> dict[str, Any]:
        result = self._continuity.validate_continuity_durability(
            layers_validated=layers_validated,
            checkpoints_restored=checkpoints_restored,
            all_restored=all_restored,
        )

        self._obs_pipeline.emit_continuity_durability_validated(
            layers_validated=layers_validated,
        )

        return result

    def validate_topology_durability(
        self,
        topologies_validated: int,
        all_intact: bool = True,
        no_orphans: bool = True,
        no_hidden_mutation: bool = True,
    ) -> dict[str, Any]:
        result = self._topology.validate_topology_durability(
            topologies_validated=topologies_validated,
            all_intact=all_intact,
            no_orphans=no_orphans,
            no_hidden_mutation=no_hidden_mutation,
        )

        self._obs_pipeline.emit_topology_durability_validated(
            domains_validated=topologies_validated,
        )

        return result

    def validate_resilience(
        self,
        recovery_scenarios: int,
        all_stable: bool = True,
        no_recursive_loops: bool = True,
    ) -> dict[str, Any]:
        return self._resilience.validate_resilience(
            recovery_scenarios=recovery_scenarios,
            all_stable=all_stable,
            no_recursive_loops=no_recursive_loops,
        )

    def validate_replay_determinism(
        self,
        check_name: str,
        input_data: str,
        output_data: str,
    ) -> dict[str, Any]:
        return self._replay_validator.validate_determinism(
            check_name=check_name,
            input_data=input_data,
            output_data=output_data,
        )

    def check_boundary(
        self, limit_name: str, current_value: int,
    ) -> dict[str, Any]:
        return self._boundary.check_limit(
            limit_name=limit_name,
            current_value=current_value,
        )

    def get_durability_report(self) -> dict[str, Any]:
        all_durable = all([
            self._concurrency.all_durable(),
            self._replay.all_durable(),
            self._continuity.all_durable(),
            self._topology.all_durable(),
            self._resilience.all_durable(),
        ])

        return {
            "all_durable": all_durable,
            "concurrency": self._concurrency.get_stats(),
            "replay": self._replay.get_stats(),
            "continuity": self._continuity.get_stats(),
            "topology": self._topology.get_stats(),
            "resilience": self._resilience.get_stats(),
        }

    def get_stats(self) -> dict[str, Any]:
        return {
            "lifecycle": self._lifecycle.get_stats(),
            "concurrency": self._concurrency.get_stats(),
            "replay": self._replay.get_stats(),
            "continuity": self._continuity.get_stats(),
            "topology": self._topology.get_stats(),
            "resilience": self._resilience.get_stats(),
            "replay_validator": self._replay_validator.get_stats(),
            "boundary": self._boundary.get_stats(),
            "obs_pipeline": self._obs_pipeline.get_stats(),
            "scenarios": len(self._scenarios),
            "receipts": len(self._receipts),
        }
