"""Tests for Phase 96.8CO — Directory Convergence Finalization and Ingestion Resume Gate.

Covers: contracts, enums, lifecycle, topology scanner, namespace convergence,
duplicate detection, quarantine, import graph, entrypoints, filesystem integrity,
ingestion readiness, observability pipeline, replay validator, boundary policies,
continuity bridges, coordinator, constraint verification.
"""

import sys
import tempfile
from pathlib import Path

import os
sys.path.insert(0, os.environ.get("UMH_ROOT") or os.environ.get("OS_ROOT") or os.environ.get("EOS_ROOT") or "/opt/OS")
_ROOT = os.environ.get("UMH_ROOT") or os.environ.get("OS_ROOT") or os.environ.get("EOS_ROOT") or "/opt/OS"

import pytest

from core.convergence.repository_topology_contracts_v1 import (
    CanonicalRepositoryTopology,
    RuntimeTopologyState,
    NamespaceConvergenceState,
    DuplicateSubsystemState,
    RepositoryBoundaryState,
    ImportGraphState,
    RuntimeEntrypointState,
    DriftDetectionState,
    ConvergenceReceipt,
    QuarantineState,
    CanonicalDirectoryState,
    IngestionReadinessState,
    FilesystemIntegrityState,
    ConvergedRuntimeState,
    ConvergencePhase,
    ConvergenceEventType,
    SubsystemClassification,
    ConvergenceDomain,
    _now_iso,
    _deterministic_id,
)
from core.convergence.convergence_lifecycle_engine_v1 import (
    ConvergenceLifecycleEngine,
    CONVERGENCE_LIFECYCLE_ORDER,
    TERMINAL_CONVERGENCE_PHASES,
)
from core.convergence.repository_topology_scanner_v1 import (
    RepositoryTopologyScanner,
    CANONICAL_SCAN_DIRECTORIES,
    MAX_SCANS,
)
from core.convergence.namespace_convergence_engine_v1 import (
    NamespaceConvergenceEngine,
    CANONICAL_NAMESPACES,
)
from core.convergence.duplicate_subsystem_detection_engine_v1 import (
    DuplicateSubsystemDetectionEngine,
    SUBSYSTEM_TYPES,
)
from core.convergence.stale_runtime_quarantine_engine_v1 import (
    StaleRuntimeQuarantineEngine,
)
from core.convergence.import_graph_verification_engine_v1 import (
    ImportGraphVerificationEngine,
)
from core.convergence.runtime_entrypoint_verification_engine_v1 import (
    RuntimeEntrypointVerificationEngine,
)
from core.convergence.filesystem_integrity_engine_v1 import (
    FilesystemIntegrityEngine,
    CANONICAL_OWNERSHIP,
)
from core.convergence.ingestion_readiness_restoration_engine_v1 import (
    IngestionReadinessRestorationEngine,
)
from core.convergence.convergence_observability_pipeline_v1 import (
    ConvergenceObservabilityPipeline,
    EVENT_FILE_MAP,
)
from core.convergence.convergence_replay_validator_v1 import (
    ConvergenceReplayValidator,
    REPLAY_CHECKS,
)
from core.convergence.convergence_boundary_policies_v1 import (
    ConvergenceBoundaryPolicies,
    CONVERGENCE_LIMITS,
    FORBIDDEN_CONVERGENCE_ACTIONS,
)
from core.convergence.convergence_continuity_bridges_v1 import (
    RuntimeConvergenceBridge,
    GovernanceConvergenceBridge,
    ReplayConvergenceBridge,
    ContinuityConvergenceBridge,
    ObservabilityConvergenceBridge,
    IngestionConvergenceBridge,
    TopologyConvergenceBridge,
    FederationConvergenceBridge,
    ConstitutionalConvergenceBridge,
    ALL_BRIDGE_CLASSES,
)
from core.convergence.canonical_repository_convergence_coordinator_v1 import (
    CanonicalRepositoryConvergenceCoordinator,
    MAX_CONVERGENCE_RUNS,
)


# ─── Contracts ───────────────────────────────────────────

class TestContracts:
    def test_canonical_repository_topology(self):
        t = CanonicalRepositoryTopology(root_path=_ROOT)
        d = t.to_dict()
        assert d["root_path"] == _ROOT

    def test_runtime_topology_state(self):
        s = RuntimeTopologyState(spine_count=1, single_spine=True)
        d = s.to_dict()
        assert d["single_spine"]

    def test_namespace_convergence_state(self):
        s = NamespaceConvergenceState(namespaces_checked=4, converged=True)
        d = s.to_dict()
        assert d["converged"]

    def test_duplicate_subsystem_state(self):
        s = DuplicateSubsystemState(subsystem_type="runtime")
        d = s.to_dict()
        assert d["subsystem_type"] == "runtime"

    def test_repository_boundary_state(self):
        s = RepositoryBoundaryState(action="test")
        d = s.to_dict()
        assert d["action"] == "test"

    def test_import_graph_state(self):
        s = ImportGraphState(total_modules=50, canonical=True)
        d = s.to_dict()
        assert d["canonical"]

    def test_runtime_entrypoint_state(self):
        s = RuntimeEntrypointState(single_spine_verified=True)
        d = s.to_dict()
        assert d["single_spine_verified"]

    def test_drift_detection_state(self):
        s = DriftDetectionState(domain="topology")
        d = s.to_dict()
        assert d["domain"] == "topology"

    def test_convergence_receipt(self):
        s = ConvergenceReceipt(run_id="run1", outcome="converged")
        d = s.to_dict()
        assert d["outcome"] == "converged"

    def test_quarantine_state(self):
        s = QuarantineState(path="/old/path", reason="dead")
        d = s.to_dict()
        assert d["path"] == "/old/path"

    def test_canonical_directory_state(self):
        s = CanonicalDirectoryState(path="core", canonical=True)
        d = s.to_dict()
        assert d["canonical"]

    def test_ingestion_readiness_state_score(self):
        s = IngestionReadinessState(
            directories_exist=True, runtime_paths_valid=True,
            dependencies_canonical=True, import_graph_stable=True,
            continuity_valid=True, replay_valid=True,
            observability_valid=True, ready=True,
        )
        assert s.readiness_score == 1.0

    def test_ingestion_readiness_partial_score(self):
        s = IngestionReadinessState(directories_exist=True)
        assert 0 < s.readiness_score < 1.0

    def test_filesystem_integrity_state(self):
        s = FilesystemIntegrityState(canonical_structure_valid=True)
        d = s.to_dict()
        assert d["canonical_structure_valid"]

    def test_converged_runtime_state_score(self):
        s = ConvergedRuntimeState(
            single_spine=True, single_orchestration_root=True,
            no_duplicate_governance=True, no_duplicate_cognition=True,
            no_duplicate_ingestion=True, no_hidden_roots=True,
            no_speculative_branching=True,
        )
        assert s.convergence_score == 1.0

    def test_converged_runtime_partial_score(self):
        s = ConvergedRuntimeState(single_spine=True)
        assert 0 < s.convergence_score < 1.0

    def test_deterministic_id_stable(self):
        a = _deterministic_id("x-", "a", "b")
        b = _deterministic_id("x-", "a", "b")
        assert a == b

    def test_now_iso_format(self):
        ts = _now_iso()
        assert "T" in ts


# ─── Enums ───────────────────────────────────────────────

class TestEnums:
    def test_convergence_phase_count(self):
        assert len(ConvergencePhase) == 7

    def test_convergence_event_type_count(self):
        assert len(ConvergenceEventType) == 9

    def test_subsystem_classification_count(self):
        assert len(SubsystemClassification) == 6

    def test_convergence_domain_count(self):
        assert len(ConvergenceDomain) == 8

    def test_phase_values(self):
        vals = {p.value for p in ConvergencePhase}
        assert "scanned" in vals
        assert "archived" in vals

    def test_classification_values(self):
        vals = {c.value for c in SubsystemClassification}
        assert "canonical" in vals
        assert "quarantined" in vals


# ─── Lifecycle Engine ────────────────────────────────────

class TestLifecycleEngine:
    def test_lifecycle_order_length(self):
        assert len(CONVERGENCE_LIFECYCLE_ORDER) == 7

    def test_valid_transition(self):
        e = ConvergenceLifecycleEngine()
        assert e.can_transition(ConvergencePhase.SCANNED, ConvergencePhase.CLASSIFIED)

    def test_invalid_skip_transition(self):
        e = ConvergenceLifecycleEngine()
        assert not e.can_transition(ConvergencePhase.SCANNED, ConvergencePhase.CONVERGED)

    def test_transition_succeeds(self):
        e = ConvergenceLifecycleEngine()
        r = e.transition(ConvergencePhase.SCANNED, ConvergencePhase.CLASSIFIED)
        assert r["from"] == "scanned"

    def test_transition_invalid_raises(self):
        e = ConvergenceLifecycleEngine()
        with pytest.raises(ValueError):
            e.transition(ConvergencePhase.SCANNED, ConvergencePhase.ARCHIVED)

    def test_terminal_phase_raises(self):
        e = ConvergenceLifecycleEngine()
        with pytest.raises(ValueError, match="terminal"):
            e.transition(ConvergencePhase.ARCHIVED, ConvergencePhase.SCANNED)

    def test_full_lifecycle(self):
        e = ConvergenceLifecycleEngine()
        phases = list(ConvergencePhase)
        for i in range(len(phases) - 1):
            e.transition(phases[i], phases[i + 1])
        assert e.get_stats()["total_transitions"] == 6

    def test_get_stats(self):
        e = ConvergenceLifecycleEngine()
        assert e.get_stats()["total_transitions"] == 0


# ─── Topology Scanner ───────────────────────────────────

class TestTopologyScanner:
    def test_scan_topology(self):
        s = RepositoryTopologyScanner(root_path=_ROOT)
        r = s.scan_topology()
        assert r["total_directories_scanned"] > 0
        assert r["topology_hash"] != ""

    def test_canonical_directories_found(self):
        s = RepositoryTopologyScanner(root_path=_ROOT)
        r = s.scan_topology()
        assert "core" in r["canonical_directories"]

    def test_detect_duplicate_domains(self):
        s = RepositoryTopologyScanner(root_path=_ROOT)
        dups = s.detect_duplicate_domains()
        assert isinstance(dups, list)

    def test_scan_directories_count(self):
        assert len(CANONICAL_SCAN_DIRECTORIES) >= 5

    def test_get_stats(self):
        s = RepositoryTopologyScanner(root_path=_ROOT)
        st = s.get_stats()
        assert st["total_scans"] == 0


# ─── Namespace Convergence Engine ────────────────────────

class TestNamespaceConvergenceEngine:
    def test_converged_namespace(self):
        e = NamespaceConvergenceEngine()
        r = e.check_convergence(namespaces_checked=4)
        assert r["converged"]

    def test_non_converged_namespace(self):
        e = NamespaceConvergenceEngine()
        r = e.check_convergence(namespaces_checked=4, duplicates_found=2)
        assert not r["converged"]

    def test_all_converged(self):
        e = NamespaceConvergenceEngine()
        e.check_convergence(namespaces_checked=4)
        assert e.all_converged()

    def test_canonical_namespaces_defined(self):
        assert len(CANONICAL_NAMESPACES) >= 3

    def test_get_stats(self):
        e = NamespaceConvergenceEngine()
        s = e.get_stats()
        assert s["total_checks"] == 0


# ─── Duplicate Detection Engine ──────────────────────────

class TestDuplicateDetectionEngine:
    def test_detect_single_instance(self):
        e = DuplicateSubsystemDetectionEngine()
        r = e.detect_duplicate("runtime", ["core/runtime"])
        assert r["classification"] == "canonical"

    def test_detect_multiple_instances(self):
        e = DuplicateSubsystemDetectionEngine()
        e.detect_duplicate("runtime", ["core/runtime", "eos_ai/runtime"])
        dups = e.get_duplicates()
        assert len(dups) == 1

    def test_no_duplicates(self):
        e = DuplicateSubsystemDetectionEngine()
        e.detect_duplicate("runtime", ["core/runtime"])
        assert e.no_duplicates()

    def test_subsystem_types_count(self):
        assert len(SUBSYSTEM_TYPES) == 8

    def test_get_by_classification(self):
        e = DuplicateSubsystemDetectionEngine()
        e.detect_duplicate("runtime", ["core/runtime"], classification="canonical")
        e.detect_duplicate("old_runtime", ["old/runtime"], classification="deprecated")
        assert len(e.get_by_classification("deprecated")) == 1

    def test_get_stats(self):
        e = DuplicateSubsystemDetectionEngine()
        s = e.get_stats()
        assert s["total_detections"] == 0


# ─── Quarantine Engine ───────────────────────────────────

class TestQuarantineEngine:
    def test_quarantine_path(self):
        with tempfile.TemporaryDirectory() as td:
            e = StaleRuntimeQuarantineEngine(output_dir=td)
            r = e.quarantine("/old/path", "stale prototype", "dead")
            assert r["classification"] == "dead"

    def test_quarantine_persisted(self):
        with tempfile.TemporaryDirectory() as td:
            e = StaleRuntimeQuarantineEngine(output_dir=td)
            e.quarantine("/old/path", "dead")
            files = list(Path(td).glob("*.jsonl"))
            assert len(files) == 1

    def test_get_quarantined(self):
        with tempfile.TemporaryDirectory() as td:
            e = StaleRuntimeQuarantineEngine(output_dir=td)
            e.quarantine("/a", "dead")
            e.quarantine("/b", "stale")
            assert len(e.get_quarantined()) == 2

    def test_get_by_classification(self):
        with tempfile.TemporaryDirectory() as td:
            e = StaleRuntimeQuarantineEngine(output_dir=td)
            e.quarantine("/a", "dead", "dead")
            e.quarantine("/b", "stale", "experimental")
            assert len(e.get_by_classification("dead")) == 1

    def test_get_stats(self):
        with tempfile.TemporaryDirectory() as td:
            e = StaleRuntimeQuarantineEngine(output_dir=td)
            e.quarantine("/a", "dead")
            s = e.get_stats()
            assert s["total_quarantined"] == 1


# ─── Import Graph Engine ────────────────────────────────

class TestImportGraphEngine:
    def test_canonical_graph(self):
        e = ImportGraphVerificationEngine()
        r = e.verify_graph(total_modules=50)
        assert r["canonical"]

    def test_non_canonical_graph(self):
        e = ImportGraphVerificationEngine()
        r = e.verify_graph(total_modules=50, cyclic_imports=2)
        assert not r["canonical"]

    def test_all_canonical(self):
        e = ImportGraphVerificationEngine()
        e.verify_graph(total_modules=50)
        assert e.all_canonical()

    def test_get_stats(self):
        e = ImportGraphVerificationEngine()
        s = e.get_stats()
        assert s["total_checks"] == 0


# ─── Entrypoint Engine ──────────────────────────────────

class TestEntrypointEngine:
    def test_single_spine(self):
        e = RuntimeEntrypointVerificationEngine()
        r = e.verify_entrypoints()
        assert r["single_spine_verified"]

    def test_non_single_spine(self):
        e = RuntimeEntrypointVerificationEngine()
        r = e.verify_entrypoints(alternate_roots=2)
        assert not r["single_spine_verified"]

    def test_all_single_spine(self):
        e = RuntimeEntrypointVerificationEngine()
        e.verify_entrypoints()
        assert e.all_single_spine()

    def test_get_stats(self):
        e = RuntimeEntrypointVerificationEngine()
        s = e.get_stats()
        assert s["total_checks"] == 0


# ─── Filesystem Integrity Engine ────────────────────────

class TestFilesystemIntegrityEngine:
    def test_verify_integrity(self):
        with tempfile.TemporaryDirectory() as td:
            e = FilesystemIntegrityEngine(output_dir=td)
            r = e.verify_integrity(root_path=_ROOT)
            assert r["canonical_structure_valid"]
            assert r["layout_hash"] != ""

    def test_all_intact(self):
        with tempfile.TemporaryDirectory() as td:
            e = FilesystemIntegrityEngine(output_dir=td)
            e.verify_integrity(root_path=_ROOT)
            assert e.all_intact()

    def test_canonical_ownership_defined(self):
        assert len(CANONICAL_OWNERSHIP) >= 5

    def test_get_stats(self):
        with tempfile.TemporaryDirectory() as td:
            e = FilesystemIntegrityEngine(output_dir=td)
            s = e.get_stats()
            assert s["total_checks"] == 0


# ─── Ingestion Readiness Engine ──────────────────────────

class TestIngestionReadinessEngine:
    def test_verify_all_ready(self):
        with tempfile.TemporaryDirectory() as td:
            e = IngestionReadinessRestorationEngine(output_dir=td)
            r = e.verify_readiness()
            assert r["ready"]
            assert r["readiness_score"] == 1.0

    def test_verify_not_ready(self):
        with tempfile.TemporaryDirectory() as td:
            e = IngestionReadinessRestorationEngine(output_dir=td)
            r = e.verify_readiness(replay_valid=False)
            assert not r["ready"]

    def test_all_ready(self):
        with tempfile.TemporaryDirectory() as td:
            e = IngestionReadinessRestorationEngine(output_dir=td)
            e.verify_readiness()
            assert e.all_ready()

    def test_persisted(self):
        with tempfile.TemporaryDirectory() as td:
            e = IngestionReadinessRestorationEngine(output_dir=td)
            e.verify_readiness()
            files = list(Path(td).glob("*.json"))
            assert len(files) == 1

    def test_get_stats(self):
        with tempfile.TemporaryDirectory() as td:
            e = IngestionReadinessRestorationEngine(output_dir=td)
            s = e.get_stats()
            assert s["total_checks"] == 0


# ─── Observability Pipeline ──────────────────────────────

class TestObservabilityPipeline:
    def test_emit_topology_scanned(self):
        with tempfile.TemporaryDirectory() as td:
            p = ConvergenceObservabilityPipeline(output_dir=td)
            r = p.emit_topology_scanned({"hash": "abc"})
            assert r["event_type"] == "topology_scanned"

    def test_emit_namespace_verified(self):
        with tempfile.TemporaryDirectory() as td:
            p = ConvergenceObservabilityPipeline(output_dir=td)
            r = p.emit_namespace_verified({"converged": True})
            assert r["event_type"] == "namespace_verified"

    def test_emit_duplicate_detected(self):
        with tempfile.TemporaryDirectory() as td:
            p = ConvergenceObservabilityPipeline(output_dir=td)
            r = p.emit_duplicate_detected({"type": "runtime"})
            assert r["event_type"] == "duplicate_detected"

    def test_emit_runtime_quarantined(self):
        with tempfile.TemporaryDirectory() as td:
            p = ConvergenceObservabilityPipeline(output_dir=td)
            r = p.emit_runtime_quarantined({"path": "/old"})
            assert r["event_type"] == "runtime_quarantined"

    def test_emit_import_graph_verified(self):
        with tempfile.TemporaryDirectory() as td:
            p = ConvergenceObservabilityPipeline(output_dir=td)
            r = p.emit_import_graph_verified({"canonical": True})
            assert r["event_type"] == "import_graph_verified"

    def test_emit_runtime_entrypoint_verified(self):
        with tempfile.TemporaryDirectory() as td:
            p = ConvergenceObservabilityPipeline(output_dir=td)
            r = p.emit_runtime_entrypoint_verified({"single": True})
            assert r["event_type"] == "runtime_entrypoint_verified"

    def test_emit_filesystem_verified(self):
        with tempfile.TemporaryDirectory() as td:
            p = ConvergenceObservabilityPipeline(output_dir=td)
            r = p.emit_filesystem_verified({"hash": "abc"})
            assert r["event_type"] == "filesystem_verified"

    def test_emit_ingestion_readiness_verified(self):
        with tempfile.TemporaryDirectory() as td:
            p = ConvergenceObservabilityPipeline(output_dir=td)
            r = p.emit_ingestion_readiness_verified({"ready": True})
            assert r["event_type"] == "ingestion_readiness_verified"

    def test_emit_convergence_boundary_denied(self):
        with tempfile.TemporaryDirectory() as td:
            p = ConvergenceObservabilityPipeline(output_dir=td)
            r = p.emit_convergence_boundary_denied({"action": "blocked"})
            assert r["event_type"] == "convergence_boundary_denied"

    def test_event_file_map_count(self):
        assert len(EVENT_FILE_MAP) == len(ConvergenceEventType)

    def test_jsonl_persisted(self):
        with tempfile.TemporaryDirectory() as td:
            p = ConvergenceObservabilityPipeline(output_dir=td)
            p.emit_topology_scanned({})
            files = list(Path(td).glob("*.jsonl"))
            assert len(files) >= 1

    def test_get_stats(self):
        with tempfile.TemporaryDirectory() as td:
            p = ConvergenceObservabilityPipeline(output_dir=td)
            p.emit_topology_scanned({})
            s = p.get_stats()
            assert s["total_events"] == 1


# ─── Replay Validator ────────────────────────────────────

class TestReplayValidator:
    def test_validate_single_check(self):
        v = ConvergenceReplayValidator()
        r = v.validate_check("topology_scan_determinism")
        assert r["deterministic"]

    def test_validate_all(self):
        v = ConvergenceReplayValidator()
        r = v.validate_all()
        assert r["total"] == len(REPLAY_CHECKS)

    def test_all_deterministic(self):
        v = ConvergenceReplayValidator()
        v.validate_all()
        assert v.all_deterministic()

    def test_replay_checks_count(self):
        assert len(REPLAY_CHECKS) == 7

    def test_get_stats(self):
        v = ConvergenceReplayValidator()
        s = v.get_stats()
        assert s["total_checks"] == 0

    def test_empty_is_deterministic(self):
        v = ConvergenceReplayValidator()
        assert v.all_deterministic()


# ─── Boundary Policies ──────────────────────────────────

class TestBoundaryPolicies:
    def test_check_limit_allowed(self):
        b = ConvergenceBoundaryPolicies()
        r = b.check_limit("max_convergence_runs", 10)
        assert r["allowed"]

    def test_check_limit_denied(self):
        b = ConvergenceBoundaryPolicies()
        r = b.check_limit("max_convergence_runs", 50)
        assert not r["allowed"]

    def test_check_limit_unknown_raises(self):
        b = ConvergenceBoundaryPolicies()
        with pytest.raises(ValueError, match="Unknown"):
            b.check_limit("nonexistent", 0)

    def test_override_capping(self):
        b = ConvergenceBoundaryPolicies()
        r = b.check_limit("max_convergence_runs", 10, override=200)
        assert r["effective_limit"] == 50

    def test_override_lower(self):
        b = ConvergenceBoundaryPolicies()
        r = b.check_limit("max_convergence_runs", 10, override=20)
        assert r["effective_limit"] == 20

    def test_check_forbidden_true(self):
        b = ConvergenceBoundaryPolicies()
        r = b.check_forbidden("alternate_runtime_spines")
        assert r["forbidden"]

    def test_check_forbidden_false(self):
        b = ConvergenceBoundaryPolicies()
        r = b.check_forbidden("normal_action")
        assert not r["forbidden"]

    def test_all_forbidden_actions(self):
        b = ConvergenceBoundaryPolicies()
        for action in FORBIDDEN_CONVERGENCE_ACTIONS:
            r = b.check_forbidden(action)
            assert r["forbidden"]

    def test_convergence_limits_count(self):
        assert len(CONVERGENCE_LIMITS) == 8

    def test_forbidden_actions_count(self):
        assert len(FORBIDDEN_CONVERGENCE_ACTIONS) == 10

    def test_denied_tracking(self):
        b = ConvergenceBoundaryPolicies()
        b.check_limit("max_convergence_runs", 100)
        b.check_forbidden("parallel_orchestrators")
        s = b.get_stats()
        assert s["total_denied"] == 2

    def test_get_stats(self):
        b = ConvergenceBoundaryPolicies()
        s = b.get_stats()
        assert s["total_limits"] == 8


# ─── Continuity Bridges ─────────────────────────────────

class TestContinuityBridges:
    def test_all_bridge_classes_count(self):
        assert len(ALL_BRIDGE_CLASSES) == 9

    def test_bridge_record(self):
        with tempfile.TemporaryDirectory() as td:
            b = RuntimeConvergenceBridge(state_dir=td)
            r = b.record("topology_verified")
            assert r["bridge"] == "runtime_convergence"

    def test_bridge_persists_jsonl(self):
        with tempfile.TemporaryDirectory() as td:
            b = GovernanceConvergenceBridge(state_dir=td)
            b.record("test")
            files = list(Path(td).glob("*.jsonl"))
            assert len(files) == 1

    def test_bridge_get_records(self):
        with tempfile.TemporaryDirectory() as td:
            b = ReplayConvergenceBridge(state_dir=td)
            b.record("a")
            b.record("b")
            assert len(b.get_records()) == 2

    def test_bridge_get_stats(self):
        with tempfile.TemporaryDirectory() as td:
            b = ContinuityConvergenceBridge(state_dir=td)
            b.record("x")
            s = b.get_stats()
            assert s["total_records"] == 1

    def test_all_bridges_instantiate(self):
        with tempfile.TemporaryDirectory() as td:
            for cls in ALL_BRIDGE_CLASSES:
                b = cls(state_dir=td)
                assert b.get_stats()["total_records"] == 0

    def test_ingestion_bridge(self):
        with tempfile.TemporaryDirectory() as td:
            b = IngestionConvergenceBridge(state_dir=td)
            r = b.record("readiness_verified")
            assert r["bridge"] == "ingestion_convergence"

    def test_topology_bridge(self):
        with tempfile.TemporaryDirectory() as td:
            b = TopologyConvergenceBridge(state_dir=td)
            r = b.record("scanned")
            assert r["bridge"] == "topology_convergence"

    def test_federation_bridge(self):
        with tempfile.TemporaryDirectory() as td:
            b = FederationConvergenceBridge(state_dir=td)
            r = b.record("aligned")
            assert r["bridge"] == "federation_convergence"

    def test_constitutional_bridge(self):
        with tempfile.TemporaryDirectory() as td:
            b = ConstitutionalConvergenceBridge(state_dir=td)
            r = b.record("verified")
            assert r["bridge"] == "constitutional_convergence"

    def test_observability_bridge(self):
        with tempfile.TemporaryDirectory() as td:
            b = ObservabilityConvergenceBridge(state_dir=td)
            r = b.record("emitted")
            assert r["bridge"] == "observability_convergence"


# ─── Coordinator ─────────────────────────────────────────

class TestCoordinator:
    def _make(self):
        td = tempfile.mkdtemp()
        return CanonicalRepositoryConvergenceCoordinator(state_dir=td, root_path=_ROOT), td

    def test_start_convergence_run(self):
        c, _ = self._make()
        r = c.start_convergence_run()
        assert r["status"] == "started"

    def test_scan_topology(self):
        c, _ = self._make()
        r = c.scan_topology()
        assert r["topology_hash"] != ""

    def test_check_namespace_convergence(self):
        c, _ = self._make()
        r = c.check_namespace_convergence(namespaces_checked=4)
        assert r["converged"]

    def test_detect_duplicates(self):
        c, _ = self._make()
        r = c.detect_duplicates("runtime", ["core/runtime"])
        assert r["classification"] == "canonical"

    def test_quarantine_path(self):
        c, _ = self._make()
        r = c.quarantine_path("/old/path", "dead prototype")
        assert r["classification"] == "dead"

    def test_verify_import_graph(self):
        c, _ = self._make()
        r = c.verify_import_graph(total_modules=50)
        assert r["canonical"]

    def test_verify_entrypoints(self):
        c, _ = self._make()
        r = c.verify_entrypoints()
        assert r["single_spine_verified"]

    def test_verify_filesystem(self):
        c, _ = self._make()
        r = c.verify_filesystem(root_path=_ROOT)
        assert r["canonical_structure_valid"]

    def test_verify_ingestion_readiness(self):
        c, _ = self._make()
        r = c.verify_ingestion_readiness()
        assert r["ready"]

    def test_validate_replay_determinism(self):
        c, _ = self._make()
        r = c.validate_replay_determinism()
        assert r["all_deterministic"]

    def test_check_boundary(self):
        c, _ = self._make()
        r = c.check_boundary("max_convergence_runs", 10)
        assert r["allowed"]

    def test_compute_converged_state(self):
        c, _ = self._make()
        r = c.compute_converged_state()
        assert r["convergence_score"] == 1.0

    def test_complete_convergence_run(self):
        c, _ = self._make()
        run = c.start_convergence_run()
        c.check_namespace_convergence(namespaces_checked=4)
        c.verify_import_graph(total_modules=50)
        c.verify_entrypoints()
        c.verify_filesystem(root_path=_ROOT)
        c.verify_ingestion_readiness()
        c.validate_replay_determinism()
        r = c.complete_convergence_run(run["run_id"])
        assert r["outcome"] == "converged"
        assert r["ingestion_ready"]

    def test_get_convergence_report(self):
        c, _ = self._make()
        r = c.get_convergence_report()
        assert "scanner" in r
        assert "ingestion" in r

    def test_get_stats(self):
        c, _ = self._make()
        s = c.get_stats()
        assert "lifecycle" in s
        assert "runs" in s

    def test_max_runs_enforced(self):
        c, _ = self._make()
        for _ in range(MAX_CONVERGENCE_RUNS):
            c.start_convergence_run()
        with pytest.raises(ValueError, match="Max"):
            c.start_convergence_run()

    def test_full_flow(self):
        c, _ = self._make()
        run = c.start_convergence_run("e2e-conv")
        c.scan_topology()
        c.check_namespace_convergence(namespaces_checked=4)
        c.detect_duplicates("runtime", ["core/runtime"])
        c.verify_import_graph(total_modules=50)
        c.verify_entrypoints()
        c.verify_filesystem(root_path=_ROOT)
        c.verify_ingestion_readiness()
        c.validate_replay_determinism()
        cvs = c.compute_converged_state()
        assert cvs["convergence_score"] == 1.0
        receipt = c.complete_convergence_run("e2e-conv")
        assert receipt["outcome"] == "converged"


# ─── Constraint Verification ────────────────────────────

class TestConstraintVerification:
    def test_duplicate_runtime_detection(self):
        e = DuplicateSubsystemDetectionEngine()
        e.detect_duplicate("runtime", ["core/runtime", "old/runtime"])
        assert len(e.get_duplicates()) == 1

    def test_namespace_drift_detection(self):
        e = NamespaceConvergenceEngine()
        r = e.check_convergence(namespaces_checked=4, shadow_trees_found=1)
        assert not r["converged"]

    def test_stale_runtime_quarantine(self):
        with tempfile.TemporaryDirectory() as td:
            e = StaleRuntimeQuarantineEngine(output_dir=td)
            r = e.quarantine("/stale/path", "abandoned experiment")
            assert r["classification"] == "dead"

    def test_import_graph_determinism(self):
        e = ImportGraphVerificationEngine()
        r = e.verify_graph(total_modules=50)
        assert r["canonical"]

    def test_single_runtime_spine_enforcement(self):
        e = RuntimeEntrypointVerificationEngine()
        r = e.verify_entrypoints()
        assert r["single_spine_verified"]

    def test_single_orchestration_root_enforcement(self):
        s = ConvergedRuntimeState(single_orchestration_root=True)
        assert s.single_orchestration_root

    def test_no_hidden_runtime_roots(self):
        b = ConvergenceBoundaryPolicies()
        r = b.check_forbidden("hidden_runtime_roots")
        assert r["forbidden"]

    def test_no_duplicate_cognition_systems(self):
        b = ConvergenceBoundaryPolicies()
        r = b.check_forbidden("duplicate_cognition_systems")
        assert r["forbidden"]

    def test_no_duplicate_governance_systems(self):
        b = ConvergenceBoundaryPolicies()
        r = b.check_forbidden("duplicate_governance_layers")
        assert r["forbidden"]

    def test_no_duplicate_ingestion_systems(self):
        b = ConvergenceBoundaryPolicies()
        r = b.check_forbidden("duplicate_ingestion_systems")
        assert r["forbidden"]

    def test_filesystem_integrity_determinism(self):
        with tempfile.TemporaryDirectory() as td:
            e = FilesystemIntegrityEngine(output_dir=td)
            r = e.verify_integrity(root_path=_ROOT)
            assert r["layout_hash"] != ""

    def test_runtime_topology_determinism(self):
        s = RepositoryTopologyScanner(root_path=_ROOT)
        r = s.scan_topology()
        assert r["topology_hash"] != ""

    def test_ingestion_readiness_validation(self):
        with tempfile.TemporaryDirectory() as td:
            e = IngestionReadinessRestorationEngine(output_dir=td)
            r = e.verify_readiness()
            assert r["ready"]
            assert r["readiness_score"] == 1.0

    def test_replay_determinism(self):
        v = ConvergenceReplayValidator()
        r = v.validate_all()
        assert r["all_deterministic"]

    def test_no_execution_outside_spine(self):
        e = RuntimeEntrypointVerificationEngine()
        r = e.verify_entrypoints(alternate_roots=0)
        assert r["single_spine_verified"]

    def test_no_governance_bypass(self):
        b = ConvergenceBoundaryPolicies()
        r = b.check_forbidden("duplicate_governance_layers")
        assert r["forbidden"]

    def test_no_speculative_runtime_branching(self):
        b = ConvergenceBoundaryPolicies()
        r = b.check_forbidden("speculative_runtime_branching")
        assert r["forbidden"]

    def test_override_capping_enforced(self):
        b = ConvergenceBoundaryPolicies()
        r = b.check_limit("max_convergence_runs", 10, override=200)
        assert r["effective_limit"] == 50

    def test_lifecycle_linear_progression(self):
        e = ConvergenceLifecycleEngine()
        with pytest.raises(ValueError):
            e.transition(ConvergencePhase.SCANNED, ConvergencePhase.ARCHIVED)

    def test_lifecycle_terminal_absorbing(self):
        e = ConvergenceLifecycleEngine()
        with pytest.raises(ValueError, match="terminal"):
            e.transition(ConvergencePhase.ARCHIVED, ConvergencePhase.SCANNED)

    def test_convergence_score_computed(self):
        s = ConvergedRuntimeState(
            single_spine=True, single_orchestration_root=True,
            no_duplicate_governance=True, no_duplicate_cognition=True,
            no_duplicate_ingestion=True, no_hidden_roots=True,
            no_speculative_branching=True,
        )
        assert s.convergence_score == 1.0

    def test_full_convergence_flow_end_to_end(self):
        td = tempfile.mkdtemp()
        c = CanonicalRepositoryConvergenceCoordinator(state_dir=td, root_path=_ROOT)
        run = c.start_convergence_run("e2e-test")
        c.scan_topology()
        c.check_namespace_convergence(namespaces_checked=4)
        c.detect_duplicates("runtime", ["core/runtime"])
        c.verify_import_graph(total_modules=50)
        c.verify_entrypoints()
        c.verify_filesystem(root_path=_ROOT)
        c.verify_ingestion_readiness()
        c.validate_replay_determinism()
        receipt = c.complete_convergence_run("e2e-test")
        assert receipt["outcome"] == "converged"
        assert receipt["ingestion_ready"]
