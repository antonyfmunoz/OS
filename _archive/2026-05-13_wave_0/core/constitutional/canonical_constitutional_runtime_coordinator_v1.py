"""Canonical Constitutional Runtime Coordinator v1.

Consolidates all substrate layers into a single constitutional
runtime fabric with unified invariants, lifecycle semantics,
replay semantics, topology semantics, governance semantics,
continuity semantics, and observability semantics.

This is consolidation/hardening — not a new layer.

It NEVER creates new orchestration paths.
It NEVER creates new execution paths.
It NEVER bypasses existing governance.
It NEVER mutates subsystem logic.

UMH substrate subsystem. Phase 96.8CG.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from core.constitutional.constitutional_runtime_contracts_v1 import (
    ConstitutionalReceipt,
    _now_iso,
)
from core.constitutional.constitutional_lifecycle_engine_v1 import (
    ConstitutionalLifecycleEngine,
)
from core.constitutional.invariant_consolidation_engine_v1 import (
    InvariantConsolidationEngine,
)
from core.constitutional.unified_replay_semantics_engine_v1 import (
    UnifiedReplaySemanticsEngine,
)
from core.constitutional.unified_lifecycle_semantics_engine_v1 import (
    UnifiedLifecycleSemanticsEngine,
)
from core.constitutional.unified_topology_semantics_engine_v1 import (
    UnifiedTopologySemanticsEngine,
)
from core.constitutional.unified_continuity_semantics_engine_v1 import (
    UnifiedContinuitySemanticsEngine,
)
from core.constitutional.unified_observability_semantics_engine_v1 import (
    UnifiedObservabilitySemanticsEngine,
)
from core.constitutional.constitutional_observability_pipeline_v1 import (
    ConstitutionalObservabilityPipeline,
)


class CanonicalConstitutionalRuntimeCoordinator:
    """Coordinates constitutional runtime consolidation.

    Cannot create new orchestration paths.
    Cannot create new execution paths.
    Cannot bypass existing governance.
    Cannot mutate subsystem logic.
    """

    def __init__(
        self,
        state_dir: str | Path = "data/runtime/constitutional",
    ) -> None:
        self._state_dir = Path(state_dir)
        self._state_dir.mkdir(parents=True, exist_ok=True)

        self._lifecycle = ConstitutionalLifecycleEngine()
        self._invariants = InvariantConsolidationEngine()
        self._replay = UnifiedReplaySemanticsEngine()
        self._lifecycle_semantics = UnifiedLifecycleSemanticsEngine()
        self._topology = UnifiedTopologySemanticsEngine()
        self._continuity = UnifiedContinuitySemanticsEngine()
        self._observability = UnifiedObservabilitySemanticsEngine()
        self._obs_pipeline = ConstitutionalObservabilityPipeline(
            state_dir=self._state_dir / "observability",
        )

    def validate_invariants(self) -> dict[str, Any]:
        result = self._invariants.validate_all()

        if result["all_enforced"]:
            for inv in self._invariants.get_all_invariants():
                self._obs_pipeline.emit_invariant_validated(
                    invariant_id=inv["invariant_id"],
                    domain=inv["domain"],
                )

        return result

    def validate_replay_semantics(
        self,
        layer: str,
        input_data: str,
        output_data: str,
    ) -> dict[str, Any]:
        result = self._replay.validate_layer_replay(
            layer=layer,
            input_data=input_data,
            output_data=output_data,
        )

        self._obs_pipeline.emit_replay_semantics_validated(
            layers_checked=1,
        )

        return result

    def validate_lifecycle_semantics(
        self,
        layer: str,
        has_terminal_states: bool = True,
        terminal_absorbing: bool = True,
        valid_transitions_only: bool = True,
        restoration_re_entry: bool = True,
        archival_is_final: bool = True,
    ) -> dict[str, Any]:
        result = self._lifecycle_semantics.validate_layer_lifecycle(
            layer=layer,
            has_terminal_states=has_terminal_states,
            terminal_absorbing=terminal_absorbing,
            valid_transitions_only=valid_transitions_only,
            restoration_re_entry=restoration_re_entry,
            archival_is_final=archival_is_final,
        )

        self._obs_pipeline.emit_lifecycle_semantics_validated(
            layers_checked=1,
        )

        return result

    def register_topology(
        self,
        domain: str,
        topology_hash: str,
    ) -> dict[str, Any]:
        result = self._topology.register_topology(
            domain=domain,
            topology_hash=topology_hash,
        )

        self._obs_pipeline.emit_topology_semantics_validated(
            domains_checked=1,
        )

        return result

    def validate_continuity(
        self,
        layer: str,
        checkpoints_deterministic: bool = True,
        restoration_verified: bool = True,
        lineage_preserved: bool = True,
        session_chain_unbroken: bool = True,
    ) -> dict[str, Any]:
        result = self._continuity.validate_layer_continuity(
            layer=layer,
            checkpoints_deterministic=checkpoints_deterministic,
            restoration_verified=restoration_verified,
            lineage_preserved=lineage_preserved,
            session_chain_unbroken=session_chain_unbroken,
        )

        self._obs_pipeline.emit_continuity_semantics_validated(
            layers_checked=1,
        )

        return result

    def validate_observability(
        self,
        layer: str,
        events_persisted: bool = True,
        event_map_from_enum: bool = True,
        receipts_emitted: bool = True,
        lineage_tracked: bool = True,
        replay_evidence_generated: bool = True,
    ) -> dict[str, Any]:
        return self._observability.validate_layer_observability(
            layer=layer,
            events_persisted=events_persisted,
            event_map_from_enum=event_map_from_enum,
            receipts_emitted=receipts_emitted,
            lineage_tracked=lineage_tracked,
            replay_evidence_generated=replay_evidence_generated,
        )

    def get_coherence_report(self) -> dict[str, Any]:
        replay_state = self._replay.get_unified_state()
        lifecycle_state = self._lifecycle_semantics.get_unified_state()
        topology_state = self._topology.get_unified_state()
        continuity_state = self._continuity.get_unified_state()
        observability_state = self._observability.get_unified_state()

        all_coherent = all([
            replay_state.deterministic,
            lifecycle_state.lifecycle_coherent,
            topology_state.topology_coherent,
            continuity_state.continuity_coherent,
            observability_state.observability_coherent,
        ])

        return {
            "all_coherent": all_coherent,
            "replay": replay_state.to_dict(),
            "lifecycle": lifecycle_state.to_dict(),
            "topology": topology_state.to_dict(),
            "continuity": continuity_state.to_dict(),
            "observability": observability_state.to_dict(),
        }

    def detect_drift(self) -> list[str]:
        drift: list[str] = []
        drift.extend(
            f"topology:{d}" for d in self._topology.detect_all_drift()
        )
        drift.extend(
            f"lifecycle:{l}"
            for l in self._lifecycle_semantics.get_incoherent_layers()
        )
        drift.extend(
            f"continuity:{l}"
            for l in self._continuity.get_incoherent_layers()
        )
        drift.extend(
            f"observability:{l}"
            for l in self._observability.get_incoherent_layers()
        )
        return drift

    def get_health(self) -> dict[str, Any]:
        return {
            "lifecycle_phase": self._lifecycle.current_phase,
            "invariants": self._invariants.get_stats(),
            "replay": self._replay.get_stats(),
            "lifecycle_semantics": self._lifecycle_semantics.get_stats(),
            "topology": self._topology.get_stats(),
            "continuity": self._continuity.get_stats(),
            "observability": self._observability.get_stats(),
        }

    def get_stats(self) -> dict[str, Any]:
        return {
            "lifecycle": self._lifecycle.get_stats(),
            "invariants": self._invariants.get_stats(),
            "replay": self._replay.get_stats(),
            "lifecycle_semantics": self._lifecycle_semantics.get_stats(),
            "topology": self._topology.get_stats(),
            "continuity": self._continuity.get_stats(),
            "observability": self._observability.get_stats(),
            "obs_pipeline": self._obs_pipeline.get_stats(),
        }
