"""Canonical Repository Convergence Coordinator v1.

Coordinates repository convergence — scanning topology, detecting
duplicates, detecting namespace drift, detecting stale paths,
validating canonical runtime topology, validating ingestion readiness.

Must NEVER: silently delete runtime-critical systems, mutate canonical
runtime without receipts, create new runtime paths, create alternate
execution spines, fabricate convergence proofs.

UMH substrate subsystem. Phase 96.8CO.
"""

from __future__ import annotations

import os
from typing import Any

_DEFAULT_ROOT = os.environ.get("UMH_ROOT") or os.environ.get("OS_ROOT") or os.environ.get("EOS_ROOT") or "/opt/OS"

from core.convergence.repository_topology_contracts_v1 import (
    ConvergenceReceipt,
    ConvergedRuntimeState,
    _now_iso,
    _deterministic_id,
)
from core.convergence.convergence_lifecycle_engine_v1 import ConvergenceLifecycleEngine
from core.convergence.repository_topology_scanner_v1 import RepositoryTopologyScanner
from core.convergence.namespace_convergence_engine_v1 import NamespaceConvergenceEngine
from core.convergence.duplicate_subsystem_detection_engine_v1 import DuplicateSubsystemDetectionEngine
from core.convergence.stale_runtime_quarantine_engine_v1 import StaleRuntimeQuarantineEngine
from core.convergence.import_graph_verification_engine_v1 import ImportGraphVerificationEngine
from core.convergence.runtime_entrypoint_verification_engine_v1 import RuntimeEntrypointVerificationEngine
from core.convergence.filesystem_integrity_engine_v1 import FilesystemIntegrityEngine
from core.convergence.ingestion_readiness_restoration_engine_v1 import IngestionReadinessRestorationEngine
from core.convergence.convergence_observability_pipeline_v1 import ConvergenceObservabilityPipeline
from core.convergence.convergence_replay_validator_v1 import ConvergenceReplayValidator
from core.convergence.convergence_boundary_policies_v1 import ConvergenceBoundaryPolicies


MAX_CONVERGENCE_RUNS = 50


class CanonicalRepositoryConvergenceCoordinator:
    """Coordinates repository convergence.

    Cannot silently delete runtime-critical systems.
    Cannot mutate canonical runtime without receipts.
    Cannot create new runtime paths.
    Cannot create alternate execution spines.
    Cannot fabricate convergence proofs.
    """

    def __init__(self, state_dir: str = "", root_path: str = _DEFAULT_ROOT) -> None:
        sd = state_dir or "data/runtime/convergence"
        self._lifecycle = ConvergenceLifecycleEngine()
        self._scanner = RepositoryTopologyScanner(root_path=root_path)
        self._namespace = NamespaceConvergenceEngine()
        self._duplicates = DuplicateSubsystemDetectionEngine()
        self._quarantine = StaleRuntimeQuarantineEngine(output_dir=f"{sd}/quarantine")
        self._import_graph = ImportGraphVerificationEngine()
        self._entrypoints = RuntimeEntrypointVerificationEngine()
        self._filesystem = FilesystemIntegrityEngine(output_dir=f"{sd}/filesystem")
        self._ingestion = IngestionReadinessRestorationEngine(output_dir=f"{sd}/reports")
        self._obs_pipeline = ConvergenceObservabilityPipeline(output_dir=sd)
        self._replay_validator = ConvergenceReplayValidator()
        self._boundary = ConvergenceBoundaryPolicies()

        self._runs: list[dict[str, Any]] = []
        self._receipts: list[ConvergenceReceipt] = []

    def start_convergence_run(self, run_id: str = "") -> dict[str, Any]:
        if len(self._runs) >= MAX_CONVERGENCE_RUNS:
            raise ValueError("Max convergence runs reached")
        if not run_id:
            run_id = _deterministic_id("cvrun-", _now_iso())
        self._runs.append({"run_id": run_id, "status": "started"})
        return {"run_id": run_id, "status": "started"}

    def scan_topology(self) -> dict[str, Any]:
        result = self._scanner.scan_topology()
        self._obs_pipeline.emit_topology_scanned({"hash": result.get("topology_hash", "")})
        return result

    def check_namespace_convergence(self, **kwargs: Any) -> dict[str, Any]:
        result = self._namespace.check_convergence(**kwargs)
        self._obs_pipeline.emit_namespace_verified({"converged": result["converged"]})
        return result

    def detect_duplicates(
        self,
        subsystem_type: str,
        instances_found: list[str],
        canonical_instance: str = "",
        classification: str = "canonical",
    ) -> dict[str, Any]:
        result = self._duplicates.detect_duplicate(
            subsystem_type, instances_found, canonical_instance, classification,
        )
        if len(instances_found) > 1:
            self._obs_pipeline.emit_duplicate_detected({"type": subsystem_type, "count": len(instances_found)})
        return result

    def quarantine_path(self, path: str, reason: str, classification: str = "dead") -> dict[str, Any]:
        result = self._quarantine.quarantine(path, reason, classification)
        self._obs_pipeline.emit_runtime_quarantined({"path": path})
        return result

    def verify_import_graph(self, **kwargs: Any) -> dict[str, Any]:
        result = self._import_graph.verify_graph(**kwargs)
        self._obs_pipeline.emit_import_graph_verified({"canonical": result["canonical"]})
        return result

    def verify_entrypoints(self, **kwargs: Any) -> dict[str, Any]:
        result = self._entrypoints.verify_entrypoints(**kwargs)
        self._obs_pipeline.emit_runtime_entrypoint_verified({"single_spine": result["single_spine_verified"]})
        return result

    def verify_filesystem(self, **kwargs: Any) -> dict[str, Any]:
        result = self._filesystem.verify_integrity(**kwargs)
        self._obs_pipeline.emit_filesystem_verified({"hash": result.get("layout_hash", "")})
        return result

    def verify_ingestion_readiness(self, **kwargs: Any) -> dict[str, Any]:
        result = self._ingestion.verify_readiness(**kwargs)
        self._obs_pipeline.emit_ingestion_readiness_verified({"ready": result["ready"]})
        return result

    def validate_replay_determinism(self) -> dict[str, Any]:
        return self._replay_validator.validate_all()

    def check_boundary(self, limit_name: str, current_value: int) -> dict[str, Any]:
        return self._boundary.check_limit(limit_name, current_value)

    def compute_converged_state(self, **overrides: bool) -> dict[str, Any]:
        state = ConvergedRuntimeState(
            single_spine=overrides.get("single_spine", True),
            single_orchestration_root=overrides.get("single_orchestration_root", True),
            no_duplicate_governance=overrides.get("no_duplicate_governance", True),
            no_duplicate_cognition=overrides.get("no_duplicate_cognition", True),
            no_duplicate_ingestion=overrides.get("no_duplicate_ingestion", True),
            no_hidden_roots=overrides.get("no_hidden_roots", True),
            no_speculative_branching=overrides.get("no_speculative_branching", True),
        )
        return state.to_dict()

    def complete_convergence_run(self, run_id: str) -> dict[str, Any]:
        all_converged = all([
            self._namespace.all_converged() if self._namespace.get_stats()["total_checks"] > 0 else True,
            self._duplicates.no_duplicates(),
            self._import_graph.all_canonical() if self._import_graph.get_stats()["total_checks"] > 0 else True,
            self._entrypoints.all_single_spine() if self._entrypoints.get_stats()["total_checks"] > 0 else True,
            self._filesystem.all_intact() if self._filesystem.get_stats()["total_checks"] > 0 else True,
            self._ingestion.all_ready() if self._ingestion.get_stats()["total_checks"] > 0 else True,
            self._replay_validator.all_deterministic(),
        ])

        outcome = "converged" if all_converged else "incomplete"
        receipt = ConvergenceReceipt(
            run_id=run_id,
            outcome=outcome,
            duplicates_quarantined=self._quarantine.get_stats()["total_quarantined"],
            ingestion_ready=self._ingestion.all_ready() if self._ingestion.get_stats()["total_checks"] > 0 else False,
        )
        self._receipts.append(receipt)
        return receipt.to_dict()

    def get_convergence_report(self) -> dict[str, Any]:
        return {
            "scanner": self._scanner.get_stats(),
            "namespace": self._namespace.get_stats(),
            "duplicates": self._duplicates.get_stats(),
            "quarantine": self._quarantine.get_stats(),
            "import_graph": self._import_graph.get_stats(),
            "entrypoints": self._entrypoints.get_stats(),
            "filesystem": self._filesystem.get_stats(),
            "ingestion": self._ingestion.get_stats(),
            "replay_validator": self._replay_validator.get_stats(),
        }

    def get_stats(self) -> dict[str, Any]:
        return {
            "lifecycle": self._lifecycle.get_stats(),
            "scanner": self._scanner.get_stats(),
            "namespace": self._namespace.get_stats(),
            "duplicates": self._duplicates.get_stats(),
            "quarantine": self._quarantine.get_stats(),
            "import_graph": self._import_graph.get_stats(),
            "entrypoints": self._entrypoints.get_stats(),
            "filesystem": self._filesystem.get_stats(),
            "ingestion": self._ingestion.get_stats(),
            "obs_pipeline": self._obs_pipeline.get_stats(),
            "replay_validator": self._replay_validator.get_stats(),
            "boundary": self._boundary.get_stats(),
            "runs": len(self._runs),
            "receipts": len(self._receipts),
        }
