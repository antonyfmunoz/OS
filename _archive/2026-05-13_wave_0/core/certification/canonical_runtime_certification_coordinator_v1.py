"""Canonical Runtime Certification Coordinator v1.

Coordinates system-wide runtime certification across all
substrate layers. Generates runtime attestations.

Must NEVER: mutate runtime state, repair violations
automatically, bypass constitutional runtime, bypass
canonical spine.

Certification is: observational, deterministic,
replayable, non-mutating.

UMH substrate subsystem. Phase 96.8CI.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from core.certification.runtime_certification_contracts_v1 import (
    RuntimeCertificationState,
    RuntimeAttestation,
    RuntimeCertificationReceipt,
    _now_iso,
    _deterministic_id,
)
from core.certification.runtime_certification_lifecycle_engine_v1 import (
    RuntimeCertificationLifecycleEngine,
)
from core.certification.constitutional_invariant_engine_v1 import (
    ConstitutionalInvariantEngine,
)
from core.certification.runtime_guarantee_engine_v1 import (
    RuntimeGuaranteeEngine,
)
from core.certification.runtime_topology_certification_engine_v1 import (
    RuntimeTopologyCertificationEngine,
)
from core.certification.runtime_continuity_certification_engine_v1 import (
    RuntimeContinuityCertificationEngine,
)
from core.certification.runtime_replay_certification_engine_v1 import (
    RuntimeReplayCertificationEngine,
)
from core.certification.constitutional_semantic_consistency_engine_v1 import (
    ConstitutionalSemanticConsistencyEngine,
)
from core.certification.runtime_certification_observability_pipeline_v1 import (
    RuntimeCertificationObservabilityPipeline,
)
from core.certification.runtime_certification_replay_validator_v1 import (
    RuntimeCertificationReplayValidator,
)
from core.certification.runtime_certification_boundary_policies_v1 import (
    RuntimeCertificationBoundaryPolicies,
)


MAX_CERTIFICATION_RUNS = 50


class CanonicalRuntimeCertificationCoordinator:
    """Coordinates runtime certification across all substrate layers.

    Cannot mutate runtime state.
    Cannot repair violations automatically.
    Cannot bypass constitutional runtime.
    Cannot bypass canonical spine.
    """

    def __init__(
        self,
        state_dir: str | Path = "data/runtime/certification",
    ) -> None:
        self._state_dir = Path(state_dir)
        self._state_dir.mkdir(parents=True, exist_ok=True)

        self._lifecycle = RuntimeCertificationLifecycleEngine()
        self._invariants = ConstitutionalInvariantEngine()
        self._guarantees = RuntimeGuaranteeEngine()
        self._topology = RuntimeTopologyCertificationEngine()
        self._continuity = RuntimeContinuityCertificationEngine()
        self._replay = RuntimeReplayCertificationEngine()
        self._semantics = ConstitutionalSemanticConsistencyEngine()
        self._obs_pipeline = RuntimeCertificationObservabilityPipeline(
            state_dir=self._state_dir / "observability",
        )
        self._replay_validator = RuntimeCertificationReplayValidator()
        self._boundary = RuntimeCertificationBoundaryPolicies()

        self._runs: list[RuntimeCertificationState] = []
        self._attestations: list[RuntimeAttestation] = []
        self._receipts: list[RuntimeCertificationReceipt] = []

    def start_certification(self, run_id: str = "") -> dict[str, Any]:
        if len(self._runs) >= MAX_CERTIFICATION_RUNS:
            raise ValueError("Max certification runs reached")

        if not run_id:
            run_id = _deterministic_id("certrun-", _now_iso())

        state = RuntimeCertificationState(run_id=run_id)
        self._runs.append(state)

        self._obs_pipeline.emit_certification_started(run_id=run_id)
        return {"run_id": run_id, "status": "started"}

    def verify_invariants(self) -> dict[str, Any]:
        result = self._invariants.verify_all_domains()

        if result["all_enforced"]:
            self._obs_pipeline.emit_invariant_verified(
                domain="all", invariant_name="global",
            )
        else:
            self._obs_pipeline.emit_invariant_failed(
                domain="all", invariant_name="global",
            )

        return result

    def verify_cross_layer(
        self,
        source_domain: str,
        target_domain: str,
        consistent: bool = True,
    ) -> dict[str, Any]:
        return self._invariants.verify_cross_layer(
            source_domain=source_domain,
            target_domain=target_domain,
            consistent=consistent,
        )

    def issue_guarantees(self) -> dict[str, Any]:
        return self._guarantees.issue_all_guarantees()

    def certify_topology(
        self,
        no_orphans: bool = True,
        no_hidden_mutation: bool = True,
        no_recursive_growth: bool = True,
        bounded: bool = True,
    ) -> dict[str, Any]:
        result = self._topology.certify_topology(
            no_orphans=no_orphans,
            no_hidden_mutation=no_hidden_mutation,
            no_recursive_growth=no_recursive_growth,
            bounded=bounded,
        )

        if result["certified"]:
            self._obs_pipeline.emit_topology_certified(checks_passed=4)

        return result

    def certify_continuity(
        self,
        checkpoint_integrity: bool = True,
        session_continuity: bool = True,
        workflow_restoration: bool = True,
        replay_restoration: bool = True,
        chronology_preserved: bool = True,
    ) -> dict[str, Any]:
        result = self._continuity.certify_continuity(
            checkpoint_integrity=checkpoint_integrity,
            session_continuity=session_continuity,
            workflow_restoration=workflow_restoration,
            replay_restoration=replay_restoration,
            chronology_preserved=chronology_preserved,
        )

        if result["certified"]:
            self._obs_pipeline.emit_continuity_certified(checks_passed=5)

        return result

    def certify_replay(
        self,
        check_name: str,
        input_data: str,
        output_data: str,
    ) -> dict[str, Any]:
        result = self._replay.certify_replay(
            check_name=check_name,
            input_data=input_data,
            output_data=output_data,
        )

        self._obs_pipeline.emit_replay_certified(checks_passed=1)
        return result

    def verify_semantic_consistency(self) -> dict[str, Any]:
        result = self._semantics.verify_all_domains()

        if result["all_coherent"]:
            self._obs_pipeline.emit_semantic_consistency_verified(
                domains_checked=result["domains_checked"],
            )

        return result

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

    def generate_attestation(self, run_id: str) -> dict[str, Any]:
        all_certified = all([
            self._invariants.all_enforced(),
            self._invariants.all_cross_layer_consistent(),
            self._guarantees.all_guaranteed(),
            self._topology.all_certified(),
            self._continuity.all_certified(),
            self._replay.all_deterministic(),
            self._semantics.all_coherent(),
            self._replay_validator.all_deterministic(),
        ])

        attestation = RuntimeAttestation(
            run_id=run_id,
            all_certified=all_certified,
            invariants_verified=self._invariants.get_stats()["total_invariants"],
            guarantees_issued=self._guarantees.get_stats()["total_guarantees"],
        )
        self._attestations.append(attestation)

        self._obs_pipeline.emit_runtime_attestation_generated(
            run_id=run_id, all_certified=all_certified,
        )

        attestation_dir = self._state_dir / "attestations"
        attestation_dir.mkdir(parents=True, exist_ok=True)
        attestation_path = attestation_dir / "runtime_attestation.json"
        with open(attestation_path, "w") as f:
            json.dump(attestation.to_dict(), f, indent=2)

        return attestation.to_dict()

    def complete_certification(
        self, run_id: str,
    ) -> dict[str, Any]:
        all_certified = all([
            self._invariants.all_enforced(),
            self._guarantees.all_guaranteed(),
            self._topology.all_certified(),
            self._continuity.all_certified(),
            self._replay.all_deterministic(),
            self._semantics.all_coherent(),
        ])

        outcome = "certified" if all_certified else "failed"
        receipt = RuntimeCertificationReceipt(
            run_id=run_id,
            outcome=outcome,
            domains_certified=10 if all_certified else 0,
        )
        self._receipts.append(receipt)

        self._obs_pipeline.emit_certification_completed(
            run_id=run_id, certified=all_certified,
        )

        return receipt.to_dict()

    def get_certification_report(self) -> dict[str, Any]:
        return {
            "invariants": self._invariants.get_stats(),
            "guarantees": self._guarantees.get_stats(),
            "topology": self._topology.get_stats(),
            "continuity": self._continuity.get_stats(),
            "replay": self._replay.get_stats(),
            "semantics": self._semantics.get_stats(),
            "replay_validator": self._replay_validator.get_stats(),
        }

    def get_stats(self) -> dict[str, Any]:
        return {
            "lifecycle": self._lifecycle.get_stats(),
            "invariants": self._invariants.get_stats(),
            "guarantees": self._guarantees.get_stats(),
            "topology": self._topology.get_stats(),
            "continuity": self._continuity.get_stats(),
            "replay": self._replay.get_stats(),
            "semantics": self._semantics.get_stats(),
            "replay_validator": self._replay_validator.get_stats(),
            "boundary": self._boundary.get_stats(),
            "obs_pipeline": self._obs_pipeline.get_stats(),
            "runs": len(self._runs),
            "attestations": len(self._attestations),
            "receipts": len(self._receipts),
        }
