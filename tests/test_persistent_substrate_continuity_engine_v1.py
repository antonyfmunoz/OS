"""Tests for persistent_substrate_continuity_engine_v1.

Phase 96.8AX. UMH substrate.
"""

from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, "/opt/OS")

from core.workstation.persistent_substrate_continuity_engine_v1 import (
    CONTINUITY_GOVERNANCE_VIOLATIONS,
    CONTINUITY_MATURITY_LEVELS,
    CONTINUITY_MATURITY_REQUIREMENTS,
    CONTINUITY_REJECTION_TRIGGERS,
    CONTINUITY_REPORT_DIR,
    DRIFT_TYPES,
    CapabilityContinuityMemory,
    ContinuityEvidence,
    ContinuityLineageEntry,
    ContinuityProof,
    DriftSignal,
    EpistemicContinuityMemory,
    EvolutionScores,
    ExecutionContinuityMemory,
    ExecutionLineageEntry,
    MaturityTransition,
    SubstrateSnapshot,
    TopologyContinuityMemory,
    build_capability_continuity,
    build_continuity_lineage,
    build_epistemic_continuity,
    build_execution_continuity,
    build_full_continuity_proof,
    build_substrate_snapshot,
    build_topology_continuity,
    classify_continuity_maturity,
    compute_continuity_maturity,
    compute_evolution_scores,
    continuity_maturity_ceiling,
    detect_continuity_corruption,
    detect_drift,
    persist_continuity_proof,
    replay_drift_emergence,
    replay_maturity_evolution,
    replay_orchestration_history,
    validate_governance_continuity,
    validate_replay_continuity,
    validate_rollback_continuity,
)
from core.workstation.governed_recursive_orchestration_engine_v1 import (
    OrchestrationEvidence,
    OrchestrationProof,
    build_full_orchestration_proof,
)
from core.workstation.recursive_capability_planning_engine_v1 import (
    build_full_capability_proof,
)


# ───────────────────────────────────────────────────────────────────
# Test data helpers
# ───────────────────────────────────────────────────────────────────


def _make_orch_proof(
    founder: bool = False,
    is_dry_run: bool = False,
) -> OrchestrationProof:
    cap = build_full_capability_proof(
        founder_confirmed=founder,
        is_dry_run=is_dry_run,
        trace_id="test-trace",
        request_id="test-req",
    )
    return build_full_orchestration_proof(
        capability_proof=cap,
        founder_confirmed=founder,
        is_dry_run=is_dry_run,
        trace_id="test-trace",
        request_id="test-req",
    )


def _full_evidence(**overrides: object) -> ContinuityEvidence:
    defaults = {
        "execution_lineage_present": True,
        "execution_lineage_depth": 3,
        "orchestration_history_present": True,
        "orchestration_history_count": 2,
        "capability_evolution_present": True,
        "capability_evolution_count": 5,
        "maturity_transitions_present": True,
        "maturity_transition_count": 2,
        "topology_evolution_present": True,
        "topology_evolution_count": 3,
        "registry_evolution_present": True,
        "registry_evolution_count": 1,
        "drift_analysis_completed": True,
        "drift_signal_count": 1,
        "drift_max_severity": 0.3,
        "replay_continuity_validated": True,
        "replay_chain_count": 2,
        "rollback_continuity_validated": True,
        "rollback_chain_count": 2,
        "governance_continuity_enforced": True,
        "continuity_proofs_persisted": True,
        "snapshot_count": 1,
        "evolution_composite_score": 0.75,
        "founder_confirmed": True,
        "is_dry_run": False,
        "trace_id": "test",
        "request_id": "test",
    }
    defaults.update(overrides)
    return ContinuityEvidence(**defaults)


# ═══════════════════════════════════════════════════════════════════
# Dataclass tests
# ═══════════════════════════════════════════════════════════════════


class TestExecutionLineageEntry(unittest.TestCase):
    def test_auto_id(self) -> None:
        e = ExecutionLineageEntry()
        self.assertTrue(e.entry_id.startswith("EXEC-"))

    def test_fields(self) -> None:
        e = ExecutionLineageEntry(command="!ping", action_type="ping", outcome="ok")
        self.assertEqual(e.command, "!ping")
        self.assertEqual(e.outcome, "ok")

    def test_to_dict(self) -> None:
        d = ExecutionLineageEntry().to_dict()
        self.assertIn("entry_id", d)
        self.assertIn("timestamp", d)

    def test_timestamp_auto(self) -> None:
        e = ExecutionLineageEntry()
        self.assertTrue(len(e.timestamp) > 0)


class TestExecutionContinuityMemory(unittest.TestCase):
    def test_empty_depth(self) -> None:
        m = ExecutionContinuityMemory()
        self.assertEqual(m.depth, 0)

    def test_depth_with_entries(self) -> None:
        m = ExecutionContinuityMemory(lineage=[ExecutionLineageEntry(), ExecutionLineageEntry()])
        self.assertEqual(m.depth, 2)

    def test_to_dict(self) -> None:
        d = ExecutionContinuityMemory().to_dict()
        self.assertEqual(d["lineage_depth"], 0)
        self.assertIn("orchestration_dag_history", d)


class TestMaturityTransition(unittest.TestCase):
    def test_auto_id(self) -> None:
        t = MaturityTransition()
        self.assertTrue(t.transition_id.startswith("MTRANS-"))

    def test_fields(self) -> None:
        t = MaturityTransition(from_level="L0", to_level="L1", domain="test")
        self.assertEqual(t.from_level, "L0")
        self.assertEqual(t.domain, "test")

    def test_to_dict(self) -> None:
        d = MaturityTransition().to_dict()
        self.assertIn("transition_id", d)
        self.assertIn("founder_confirmed", d)


class TestCapabilityContinuityMemory(unittest.TestCase):
    def test_empty(self) -> None:
        m = CapabilityContinuityMemory()
        self.assertEqual(len(m.capability_evolution), 0)

    def test_to_dict(self) -> None:
        d = CapabilityContinuityMemory(maturity_transitions=[MaturityTransition()]).to_dict()
        self.assertEqual(len(d["maturity_transitions"]), 1)


class TestTopologyContinuityMemory(unittest.TestCase):
    def test_empty(self) -> None:
        m = TopologyContinuityMemory()
        self.assertEqual(len(m.graph_evolution), 0)

    def test_blast_radius_rounding(self) -> None:
        m = TopologyContinuityMemory(blast_radius_trends=[0.12345, 0.67891])
        d = m.to_dict()
        self.assertEqual(d["blast_radius_trends"], [0.123, 0.679])


class TestEpistemicContinuityMemory(unittest.TestCase):
    def test_defaults(self) -> None:
        m = EpistemicContinuityMemory()
        self.assertEqual(m.observed_count, 0)
        self.assertEqual(m.simulated_count, 0)

    def test_to_dict(self) -> None:
        d = EpistemicContinuityMemory(observed_count=3, founder_confirmed_count=1).to_dict()
        self.assertEqual(d["observed_count"], 3)
        self.assertEqual(d["founder_confirmed_count"], 1)


class TestSubstrateSnapshot(unittest.TestCase):
    def test_auto_id(self) -> None:
        s = SubstrateSnapshot()
        self.assertTrue(s.snapshot_id.startswith("SNAP-"))

    def test_fields(self) -> None:
        s = SubstrateSnapshot(
            orchestration_maturity="L3",
            capability_count=21,
            continuity_hash="abc123",
        )
        self.assertEqual(s.orchestration_maturity, "L3")
        self.assertEqual(s.continuity_hash, "abc123")

    def test_to_dict(self) -> None:
        d = SubstrateSnapshot().to_dict()
        self.assertIn("continuity_hash", d)
        self.assertIn("replay_hash", d)
        self.assertIn("drift_signatures", d)


class TestDriftSignal(unittest.TestCase):
    def test_auto_id(self) -> None:
        d = DriftSignal()
        self.assertTrue(d.signal_id.startswith("DRIFT-"))

    def test_severity_rounding(self) -> None:
        d = DriftSignal(severity=0.12345).to_dict()
        self.assertEqual(d["severity"], 0.123)

    def test_fields(self) -> None:
        d = DriftSignal(
            drift_type="registry_divergence",
            severity=0.8,
            description="test",
        )
        self.assertEqual(d.drift_type, "registry_divergence")


class TestContinuityLineageEntry(unittest.TestCase):
    def test_auto_id(self) -> None:
        e = ContinuityLineageEntry()
        self.assertTrue(e.lineage_id.startswith("CLIN-"))

    def test_fields(self) -> None:
        e = ContinuityLineageEntry(
            parent_orchestration_id="ORCH-1",
            replay_lineage=["a", "b"],
            rollback_lineage=["c"],
        )
        self.assertEqual(len(e.replay_lineage), 2)
        self.assertEqual(len(e.rollback_lineage), 1)

    def test_to_dict(self) -> None:
        d = ContinuityLineageEntry().to_dict()
        self.assertIn("parent_orchestration_id", d)
        self.assertIn("evolution_chain", d)


class TestEvolutionScores(unittest.TestCase):
    def test_defaults_zero(self) -> None:
        s = EvolutionScores()
        self.assertEqual(s.composite(), 0.0)

    def test_composite_positive(self) -> None:
        s = EvolutionScores(
            stability_trend=1.0,
            governance_integrity_trend=1.0,
            replayability_trend=1.0,
            rollbackability_trend=1.0,
            capability_leverage_trend=1.0,
            orchestration_entropy_trend=0.0,
            drift_acceleration_trend=0.0,
        )
        self.assertAlmostEqual(s.composite(), 0.85, places=2)

    def test_composite_with_penalty(self) -> None:
        s = EvolutionScores(
            stability_trend=1.0,
            governance_integrity_trend=1.0,
            replayability_trend=1.0,
            rollbackability_trend=1.0,
            capability_leverage_trend=1.0,
            orchestration_entropy_trend=1.0,
            drift_acceleration_trend=1.0,
        )
        self.assertAlmostEqual(s.composite(), 0.6, places=2)

    def test_to_dict_has_composite(self) -> None:
        d = EvolutionScores().to_dict()
        self.assertIn("composite_score", d)

    def test_seven_dimensions(self) -> None:
        d = EvolutionScores().to_dict()
        dims = [
            "stability_trend",
            "governance_integrity_trend",
            "replayability_trend",
            "rollbackability_trend",
            "orchestration_entropy_trend",
            "drift_acceleration_trend",
            "capability_leverage_trend",
        ]
        for dim in dims:
            self.assertIn(dim, d)


class TestContinuityEvidence(unittest.TestCase):
    def test_defaults(self) -> None:
        e = ContinuityEvidence()
        self.assertFalse(e.execution_lineage_present)
        self.assertFalse(e.founder_confirmed)

    def test_to_dict_fields(self) -> None:
        d = ContinuityEvidence().to_dict()
        expected_keys = [
            "execution_lineage_present",
            "orchestration_history_present",
            "capability_evolution_present",
            "maturity_transitions_present",
            "topology_evolution_present",
            "registry_evolution_present",
            "drift_analysis_completed",
            "replay_continuity_validated",
            "rollback_continuity_validated",
            "governance_continuity_enforced",
            "continuity_proofs_persisted",
            "founder_confirmed",
        ]
        for k in expected_keys:
            self.assertIn(k, d)

    def test_severity_rounding(self) -> None:
        e = ContinuityEvidence(drift_max_severity=0.12345)
        d = e.to_dict()
        self.assertEqual(d["drift_max_severity"], 0.123)


class TestContinuityProof(unittest.TestCase):
    def test_auto_id(self) -> None:
        p = ContinuityProof()
        self.assertTrue(p.proof_id.startswith("CONTPROOF-"))

    def test_default_maturity(self) -> None:
        p = ContinuityProof()
        self.assertEqual(p.maturity_level, "L0_NO_CONTINUITY")

    def test_to_dict_proof_type(self) -> None:
        d = ContinuityProof().to_dict()
        self.assertEqual(d["proof_type"], "persistent_substrate_continuity")

    def test_to_dict_structure(self) -> None:
        d = ContinuityProof().to_dict()
        expected = [
            "proof_id",
            "maturity_level",
            "maturity_ceiling",
            "escalation_blocked",
            "snapshot_count",
            "drift_signal_count",
            "lineage_depth",
            "execution_strategy",
        ]
        for k in expected:
            self.assertIn(k, d)


# ═══════════════════════════════════════════════════════════════════
# Constants tests
# ═══════════════════════════════════════════════════════════════════


class TestConstants(unittest.TestCase):
    def test_maturity_level_count(self) -> None:
        self.assertEqual(len(CONTINUITY_MATURITY_LEVELS), 6)

    def test_maturity_levels_ordered(self) -> None:
        self.assertEqual(CONTINUITY_MATURITY_LEVELS[0], "L0_NO_CONTINUITY")
        self.assertEqual(
            CONTINUITY_MATURITY_LEVELS[5],
            "L5_PERSISTENT_GOVERNED_SUBSTRATE_CONTINUITY",
        )

    def test_requirements_cover_all_levels(self) -> None:
        for level in CONTINUITY_MATURITY_LEVELS:
            self.assertIn(level, CONTINUITY_MATURITY_REQUIREMENTS)

    def test_l0_no_requirements(self) -> None:
        self.assertEqual(len(CONTINUITY_MATURITY_REQUIREMENTS["L0_NO_CONTINUITY"]), 0)

    def test_l5_all_requirements(self) -> None:
        reqs = CONTINUITY_MATURITY_REQUIREMENTS["L5_PERSISTENT_GOVERNED_SUBSTRATE_CONTINUITY"]
        self.assertGreaterEqual(len(reqs), 10)
        self.assertIn("founder_confirmed", reqs)

    def test_drift_types_count(self) -> None:
        self.assertEqual(len(DRIFT_TYPES), 8)

    def test_drift_types_content(self) -> None:
        expected = {
            "registry_divergence",
            "topology_divergence",
            "orchestration_divergence",
            "maturity_drift",
            "replay_drift",
            "relay_drift",
            "governance_drift",
            "execution_lineage_corruption",
        }
        self.assertEqual(DRIFT_TYPES, expected)

    def test_governance_violations_count(self) -> None:
        self.assertEqual(len(CONTINUITY_GOVERNANCE_VIOLATIONS), 7)

    def test_governance_violations_content(self) -> None:
        self.assertIn("lineage_rewrite", CONTINUITY_GOVERNANCE_VIOLATIONS)
        self.assertIn("canonical_auto_promotion", CONTINUITY_GOVERNANCE_VIOLATIONS)

    def test_rejection_triggers_count(self) -> None:
        self.assertEqual(len(CONTINUITY_REJECTION_TRIGGERS), 7)

    def test_rejection_triggers_content(self) -> None:
        self.assertIn("orphaned_orchestration_chain", CONTINUITY_REJECTION_TRIGGERS)
        self.assertIn("continuity_corruption", CONTINUITY_REJECTION_TRIGGERS)

    def test_report_dir(self) -> None:
        self.assertEqual(
            str(CONTINUITY_REPORT_DIR),
            "data/runtime/workstation_relay/continuity_reports",
        )


# ═══════════════════════════════════════════════════════════════════
# Builder tests — 4 memory layers
# ═══════════════════════════════════════════════════════════════════


class TestBuildExecutionContinuity(unittest.TestCase):
    def test_no_proof(self) -> None:
        m = build_execution_continuity(None, Path(tempfile.mkdtemp()))
        self.assertEqual(m.depth, 0)

    def test_with_proof(self) -> None:
        td = Path(tempfile.mkdtemp())
        orch_dir = td / "data/runtime/workstation_relay/orchestration_reports"
        orch_dir.mkdir(parents=True)
        proof_data = {
            "proof_id": "ORCHPROOF-test1",
            "trace_id": "t1",
            "maturity_level": "L3",
        }
        (orch_dir / "ORCHPROOF-test1.json").write_text(json.dumps(proof_data))
        m = build_execution_continuity(None, td)
        self.assertGreaterEqual(m.depth, 1)

    def test_with_orch_proof_object(self) -> None:
        proof = _make_orch_proof()
        td = Path(tempfile.mkdtemp())
        m = build_execution_continuity(proof, td)
        self.assertIsInstance(m, ExecutionContinuityMemory)

    def test_rollback_history(self) -> None:
        proof = _make_orch_proof(founder=True)
        td = Path(tempfile.mkdtemp())
        m = build_execution_continuity(proof, td)
        self.assertIsInstance(m.rollback_history, list)

    def test_replay_history(self) -> None:
        proof = _make_orch_proof(founder=True)
        td = Path(tempfile.mkdtemp())
        m = build_execution_continuity(proof, td)
        self.assertIsInstance(m.replay_history, list)


class TestBuildCapabilityContinuity(unittest.TestCase):
    def test_no_proof(self) -> None:
        m = build_capability_continuity(None, Path(tempfile.mkdtemp()))
        self.assertGreater(len(m.capability_evolution), 0)

    def test_with_proof(self) -> None:
        proof = _make_orch_proof()
        m = build_capability_continuity(proof, Path(tempfile.mkdtemp()))
        self.assertGreater(len(m.capability_evolution), 0)

    def test_dependency_evolution(self) -> None:
        proof = _make_orch_proof()
        m = build_capability_continuity(proof, Path(tempfile.mkdtemp()))
        self.assertIsInstance(m.dependency_evolution, list)

    def test_maturity_transitions_with_proof(self) -> None:
        proof = _make_orch_proof(founder=True)
        m = build_capability_continuity(proof, Path(tempfile.mkdtemp()))
        self.assertIsInstance(m.maturity_transitions, list)


class TestBuildTopologyContinuity(unittest.TestCase):
    def test_no_proof(self) -> None:
        m = build_topology_continuity(None, Path(tempfile.mkdtemp()))
        self.assertGreater(len(m.registry_evolution), 0)

    def test_with_proof(self) -> None:
        proof = _make_orch_proof()
        m = build_topology_continuity(proof, Path(tempfile.mkdtemp()))
        self.assertGreater(len(m.graph_evolution), 0)

    def test_blast_radius_trends(self) -> None:
        proof = _make_orch_proof()
        m = build_topology_continuity(proof, Path(tempfile.mkdtemp()))
        self.assertIsInstance(m.blast_radius_trends, list)

    def test_node_additions(self) -> None:
        proof = _make_orch_proof()
        m = build_topology_continuity(proof, Path(tempfile.mkdtemp()))
        self.assertIsInstance(m.node_additions, list)


class TestBuildEpistemicContinuity(unittest.TestCase):
    def test_no_proof(self) -> None:
        m = build_epistemic_continuity(None, False)
        self.assertEqual(m.observed_count, 0)
        self.assertEqual(m.simulated_count, 0)

    def test_with_proof_not_confirmed(self) -> None:
        proof = _make_orch_proof(founder=False)
        m = build_epistemic_continuity(proof, False)
        self.assertEqual(m.simulated_count, 1)

    def test_with_founder_confirmed(self) -> None:
        m = build_epistemic_continuity(None, True)
        self.assertEqual(m.founder_confirmed_count, 1)

    def test_maturity_ceiling_transitions(self) -> None:
        proof = _make_orch_proof()
        m = build_epistemic_continuity(proof, False)
        self.assertGreater(len(m.maturity_ceiling_transitions), 0)


# ═══════════════════════════════════════════════════════════════════
# Temporal snapshot tests
# ═══════════════════════════════════════════════════════════════════


class TestBuildSubstrateSnapshot(unittest.TestCase):
    def test_no_proofs(self) -> None:
        s = build_substrate_snapshot()
        self.assertTrue(s.snapshot_id.startswith("SNAP-"))
        self.assertGreater(len(s.continuity_hash), 0)
        self.assertGreater(len(s.replay_hash), 0)

    def test_with_orch_proof(self) -> None:
        proof = _make_orch_proof()
        s = build_substrate_snapshot(orchestration_proof=proof)
        self.assertGreater(s.dag_count, 0)

    def test_registry_hash_present(self) -> None:
        s = build_substrate_snapshot()
        self.assertGreater(len(s.registry_hash), 0)

    def test_capability_count(self) -> None:
        s = build_substrate_snapshot()
        self.assertGreater(s.capability_count, 0)


# ═══════════════════════════════════════════════════════════════════
# Drift detection tests
# ═══════════════════════════════════════════════════════════════════


class TestDetectDrift(unittest.TestCase):
    def test_no_inputs(self) -> None:
        td = Path(tempfile.mkdtemp())
        signals = detect_drift(None, None, td)
        self.assertIsInstance(signals, list)

    def test_with_orch_proof(self) -> None:
        proof = _make_orch_proof()
        td = Path(tempfile.mkdtemp())
        (td / "config").mkdir()
        config = {
            "allowed_action_types": list(
                __import__(
                    "core.registry.canonical_command_registry_v1",
                    fromlist=["get_canonical_registry"],
                )
                .get_canonical_registry()
                .actions
            )
        }
        (td / "config" / "control_plane_router_v1.json").write_text(json.dumps(config))
        signals = detect_drift(proof, None, td)
        self.assertIsInstance(signals, list)

    def test_registry_divergence_detected(self) -> None:
        td = Path(tempfile.mkdtemp())
        (td / "config").mkdir()
        config = {"allowed_action_types": ["ping"]}
        (td / "config" / "control_plane_router_v1.json").write_text(json.dumps(config))
        signals = detect_drift(None, None, td)
        divergence = [s for s in signals if s.drift_type == "registry_divergence"]
        self.assertGreater(len(divergence), 0)

    def test_previous_snapshot_drift(self) -> None:
        td = Path(tempfile.mkdtemp())
        old_snap = SubstrateSnapshot(registry_hash="old_hash_value")
        signals = detect_drift(None, old_snap, td)
        divergence = [s for s in signals if s.drift_type == "registry_divergence"]
        self.assertGreater(len(divergence), 0)

    def test_maturity_drift_detection(self) -> None:
        td = Path(tempfile.mkdtemp())
        orch_dir = td / "data/runtime/workstation_relay/orchestration_reports"
        orch_dir.mkdir(parents=True)
        d1 = {"maturity_level": "L0_SIMULATED_ORCHESTRATION"}
        d2 = {"maturity_level": "L3_GOVERNED_ORCHESTRATION"}
        (orch_dir / "ORCHPROOF-001.json").write_text(json.dumps(d1))
        (orch_dir / "ORCHPROOF-002.json").write_text(json.dumps(d2))
        signals = detect_drift(None, None, td)
        mat_drift = [s for s in signals if s.drift_type == "maturity_drift"]
        self.assertGreater(len(mat_drift), 0)


# ═══════════════════════════════════════════════════════════════════
# Continuity lineage tests
# ═══════════════════════════════════════════════════════════════════


class TestBuildContinuityLineage(unittest.TestCase):
    def test_empty(self) -> None:
        chain = build_continuity_lineage(None, "", Path(tempfile.mkdtemp()))
        self.assertEqual(len(chain), 0)

    def test_with_orch_files(self) -> None:
        td = Path(tempfile.mkdtemp())
        orch_dir = td / "data/runtime/workstation_relay/orchestration_reports"
        orch_dir.mkdir(parents=True)
        data = {
            "proof_id": "ORCHPROOF-x1",
            "simulations": [{"replay_intact": True, "upgrade_name": "u1"}],
            "rollback_plans": [{"rollback_safe": True, "upgrade_name": "u1"}],
            "sequenced_upgrades": ["u1"],
        }
        (orch_dir / "ORCHPROOF-x1.json").write_text(json.dumps(data))
        chain = build_continuity_lineage(None, "", td)
        self.assertEqual(len(chain), 1)
        self.assertGreater(len(chain[0].replay_lineage), 0)
        self.assertGreater(len(chain[0].rollback_lineage), 0)

    def test_chain_linking(self) -> None:
        td = Path(tempfile.mkdtemp())
        orch_dir = td / "data/runtime/workstation_relay/orchestration_reports"
        orch_dir.mkdir(parents=True)
        for i in range(3):
            data = {
                "proof_id": f"ORCHPROOF-c{i}",
                "simulations": [],
                "rollback_plans": [],
                "sequenced_upgrades": [f"u{i}"],
            }
            (orch_dir / f"ORCHPROOF-c{i}.json").write_text(json.dumps(data))
        chain = build_continuity_lineage(None, "prev-123", td)
        self.assertEqual(len(chain), 3)
        self.assertEqual(chain[0].parent_continuity_id, "prev-123")


# ═══════════════════════════════════════════════════════════════════
# Replay engine tests
# ═══════════════════════════════════════════════════════════════════


class TestReplayOrchestrationHistory(unittest.TestCase):
    def test_empty(self) -> None:
        h = replay_orchestration_history(Path(tempfile.mkdtemp()))
        self.assertEqual(len(h), 0)

    def test_with_files(self) -> None:
        td = Path(tempfile.mkdtemp())
        orch_dir = td / "data/runtime/workstation_relay/orchestration_reports"
        orch_dir.mkdir(parents=True)
        data = {
            "proof_id": "ORCHPROOF-h1",
            "maturity_level": "L2",
            "dag_count": 7,
            "execution_strategy": "test",
            "timestamp": "2026-01-01",
        }
        (orch_dir / "ORCHPROOF-h1.json").write_text(json.dumps(data))
        h = replay_orchestration_history(td)
        self.assertEqual(len(h), 1)
        self.assertEqual(h[0]["proof_id"], "ORCHPROOF-h1")


class TestReplayMaturityEvolution(unittest.TestCase):
    def test_empty(self) -> None:
        e = replay_maturity_evolution(Path(tempfile.mkdtemp()))
        self.assertEqual(len(e), 0)

    def test_with_cap_and_orch(self) -> None:
        td = Path(tempfile.mkdtemp())
        cap_dir = td / "data/runtime/workstation_relay/capability_reports"
        cap_dir.mkdir(parents=True)
        (cap_dir / "CAPPROOF-1.json").write_text(
            json.dumps({"maturity_level": "L2", "timestamp": "2026-01-01"})
        )
        orch_dir = td / "data/runtime/workstation_relay/orchestration_reports"
        orch_dir.mkdir(parents=True)
        (orch_dir / "ORCHPROOF-1.json").write_text(
            json.dumps({"maturity_level": "L3", "timestamp": "2026-01-02"})
        )
        e = replay_maturity_evolution(td)
        self.assertEqual(len(e), 2)
        domains = {x["domain"] for x in e}
        self.assertIn("capability", domains)
        self.assertIn("orchestration", domains)


class TestReplayDriftEmergence(unittest.TestCase):
    def test_empty(self) -> None:
        d = replay_drift_emergence(Path(tempfile.mkdtemp()))
        self.assertEqual(len(d), 0)

    def test_with_continuity_proofs(self) -> None:
        td = Path(tempfile.mkdtemp())
        cont_dir = td / "data/runtime/workstation_relay/continuity_reports"
        cont_dir.mkdir(parents=True)
        data = {"drift_signals": [{"drift_type": "registry_divergence", "severity": 0.5}]}
        (cont_dir / "CONTPROOF-1.json").write_text(json.dumps(data))
        d = replay_drift_emergence(td)
        self.assertEqual(len(d), 1)


# ═══════════════════════════════════════════════════════════════════
# Validation tests
# ═══════════════════════════════════════════════════════════════════


class TestValidateReplayContinuity(unittest.TestCase):
    def test_empty_chain(self) -> None:
        self.assertFalse(validate_replay_continuity([]))

    def test_valid_chain(self) -> None:
        chain = [
            ContinuityLineageEntry(replay_lineage=["a"]),
            ContinuityLineageEntry(evolution_chain=["b"]),
        ]
        self.assertTrue(validate_replay_continuity(chain))

    def test_invalid_chain(self) -> None:
        chain = [
            ContinuityLineageEntry(replay_lineage=["a"]),
            ContinuityLineageEntry(),
        ]
        self.assertFalse(validate_replay_continuity(chain))


class TestValidateRollbackContinuity(unittest.TestCase):
    def test_empty_chain(self) -> None:
        self.assertFalse(validate_rollback_continuity([]))

    def test_valid_chain(self) -> None:
        chain = [
            ContinuityLineageEntry(rollback_lineage=["a"]),
            ContinuityLineageEntry(evolution_chain=["b"]),
        ]
        self.assertTrue(validate_rollback_continuity(chain))

    def test_invalid_chain(self) -> None:
        chain = [
            ContinuityLineageEntry(rollback_lineage=["a"]),
            ContinuityLineageEntry(),
        ]
        self.assertFalse(validate_rollback_continuity(chain))


class TestValidateGovernanceContinuity(unittest.TestCase):
    def test_no_proof(self) -> None:
        self.assertFalse(validate_governance_continuity(None))

    def test_no_evidence(self) -> None:
        proof = OrchestrationProof()
        self.assertFalse(validate_governance_continuity(proof))

    def test_governance_not_validated(self) -> None:
        proof = OrchestrationProof(evidence=OrchestrationEvidence(governance_validated=False))
        self.assertFalse(validate_governance_continuity(proof))

    def test_governance_validated(self) -> None:
        proof = OrchestrationProof(evidence=OrchestrationEvidence(governance_validated=True))
        self.assertTrue(validate_governance_continuity(proof))


class TestDetectContinuityCorruption(unittest.TestCase):
    def test_no_corruption(self) -> None:
        chain = [ContinuityLineageEntry(replay_lineage=["a"])]
        mem = ExecutionContinuityMemory()
        corruptions = detect_continuity_corruption(chain, mem)
        self.assertEqual(len(corruptions), 0)

    def test_orphaned_chain(self) -> None:
        mem = ExecutionContinuityMemory(lineage=[ExecutionLineageEntry(), ExecutionLineageEntry()])
        corruptions = detect_continuity_corruption([], mem)
        self.assertIn("orphaned_orchestration_chain", corruptions)

    def test_broken_rollback(self) -> None:
        mem = ExecutionContinuityMemory(
            lineage=[ExecutionLineageEntry()],
            rollback_history=[],
        )
        corruptions = detect_continuity_corruption([], mem)
        self.assertIn("broken_rollback_lineage", corruptions)


# ═══════════════════════════════════════════════════════════════════
# Evolution scoring tests
# ═══════════════════════════════════════════════════════════════════


class TestComputeEvolutionScores(unittest.TestCase):
    def test_no_inputs(self) -> None:
        s = compute_evolution_scores(None, None, None)
        self.assertEqual(s.composite(), 0.0)

    def test_with_orch_proof(self) -> None:
        proof = _make_orch_proof(founder=True)
        s = compute_evolution_scores(proof, [], [])
        self.assertGreaterEqual(s.composite(), 0.0)

    def test_drift_penalty(self) -> None:
        drift = [DriftSignal(severity=0.9)]
        s = compute_evolution_scores(None, drift, None)
        self.assertGreater(s.drift_acceleration_trend, 0.0)

    def test_lineage_leverage(self) -> None:
        chain = [ContinuityLineageEntry(evolution_chain=["a", "b", "c"])]
        s = compute_evolution_scores(None, None, chain)
        self.assertGreater(s.capability_leverage_trend, 0.0)

    def test_replayability_from_proof(self) -> None:
        proof = _make_orch_proof(founder=True)
        s = compute_evolution_scores(proof, [], [])
        self.assertIsInstance(s.replayability_trend, float)


# ═══════════════════════════════════════════════════════════════════
# Maturity evaluation tests
# ═══════════════════════════════════════════════════════════════════


class TestComputeContinuityMaturity(unittest.TestCase):
    def test_dry_run(self) -> None:
        ev = _full_evidence(is_dry_run=True)
        self.assertEqual(compute_continuity_maturity(ev), "L0_NO_CONTINUITY")

    def test_l0_no_evidence(self) -> None:
        ev = ContinuityEvidence()
        self.assertEqual(compute_continuity_maturity(ev), "L0_NO_CONTINUITY")

    def test_l1(self) -> None:
        ev = _full_evidence(
            capability_evolution_present=False,
            maturity_transitions_present=False,
            topology_evolution_present=False,
            registry_evolution_present=False,
            drift_analysis_completed=False,
            replay_continuity_validated=False,
            rollback_continuity_validated=False,
            governance_continuity_enforced=False,
            continuity_proofs_persisted=False,
            founder_confirmed=False,
        )
        self.assertEqual(compute_continuity_maturity(ev), "L1_EXECUTION_CONTINUITY")

    def test_l5(self) -> None:
        ev = _full_evidence()
        self.assertEqual(
            compute_continuity_maturity(ev),
            "L5_PERSISTENT_GOVERNED_SUBSTRATE_CONTINUITY",
        )


class TestContinuityMaturityCeiling(unittest.TestCase):
    def test_dry_run(self) -> None:
        ev = _full_evidence(is_dry_run=True)
        self.assertEqual(continuity_maturity_ceiling(ev), "L0_NO_CONTINUITY")

    def test_no_execution_lineage(self) -> None:
        ev = _full_evidence(execution_lineage_present=False)
        self.assertEqual(continuity_maturity_ceiling(ev), "L0_NO_CONTINUITY")

    def test_no_orchestration_history(self) -> None:
        ev = _full_evidence(orchestration_history_present=False)
        self.assertEqual(continuity_maturity_ceiling(ev), "L0_NO_CONTINUITY")

    def test_no_capability_evolution(self) -> None:
        ev = _full_evidence(capability_evolution_present=False)
        self.assertEqual(continuity_maturity_ceiling(ev), "L1_EXECUTION_CONTINUITY")

    def test_no_topology_evolution(self) -> None:
        ev = _full_evidence(topology_evolution_present=False)
        self.assertEqual(continuity_maturity_ceiling(ev), "L2_CAPABILITY_CONTINUITY")

    def test_no_drift_analysis(self) -> None:
        ev = _full_evidence(drift_analysis_completed=False)
        self.assertEqual(continuity_maturity_ceiling(ev), "L3_TOPOLOGY_CONTINUITY")

    def test_no_replay(self) -> None:
        ev = _full_evidence(replay_continuity_validated=False)
        self.assertEqual(continuity_maturity_ceiling(ev), "L3_TOPOLOGY_CONTINUITY")

    def test_no_rollback(self) -> None:
        ev = _full_evidence(rollback_continuity_validated=False)
        self.assertEqual(continuity_maturity_ceiling(ev), "L4_EPISTEMIC_CONTINUITY")

    def test_no_governance(self) -> None:
        ev = _full_evidence(governance_continuity_enforced=False)
        self.assertEqual(continuity_maturity_ceiling(ev), "L4_EPISTEMIC_CONTINUITY")

    def test_no_founder(self) -> None:
        ev = _full_evidence(founder_confirmed=False)
        self.assertEqual(continuity_maturity_ceiling(ev), "L4_EPISTEMIC_CONTINUITY")

    def test_full_l5(self) -> None:
        ev = _full_evidence()
        self.assertEqual(
            continuity_maturity_ceiling(ev),
            "L5_PERSISTENT_GOVERNED_SUBSTRATE_CONTINUITY",
        )


class TestClassifyContinuityMaturity(unittest.TestCase):
    def test_full_returns_l5(self) -> None:
        ev = _full_evidence()
        level, ceiling, blocked, reason = classify_continuity_maturity(ev)
        self.assertEqual(level, "L5_PERSISTENT_GOVERNED_SUBSTRATE_CONTINUITY")
        self.assertFalse(blocked)

    def test_ceiling_blocks(self) -> None:
        ev = _full_evidence(execution_lineage_present=False)
        level, ceiling, blocked, reason = classify_continuity_maturity(ev)
        self.assertEqual(level, "L0_NO_CONTINUITY")
        self.assertTrue(blocked or level == "L0_NO_CONTINUITY")

    def test_dry_run_l0(self) -> None:
        ev = _full_evidence(is_dry_run=True)
        level, ceiling, blocked, reason = classify_continuity_maturity(ev)
        self.assertEqual(level, "L0_NO_CONTINUITY")


# ═══════════════════════════════════════════════════════════════════
# Hard ceiling tests
# ═══════════════════════════════════════════════════════════════════


class TestHardCeilings(unittest.TestCase):
    def test_dry_run_ceiling_l0(self) -> None:
        ev = _full_evidence(is_dry_run=True)
        self.assertEqual(continuity_maturity_ceiling(ev), "L0_NO_CONTINUITY")

    def test_no_execution_ceiling_l0(self) -> None:
        ev = _full_evidence(execution_lineage_present=False)
        self.assertEqual(continuity_maturity_ceiling(ev), "L0_NO_CONTINUITY")

    def test_no_orch_history_ceiling_l0(self) -> None:
        ev = _full_evidence(orchestration_history_present=False)
        self.assertEqual(continuity_maturity_ceiling(ev), "L0_NO_CONTINUITY")

    def test_no_cap_evolution_ceiling_l1(self) -> None:
        ev = _full_evidence(capability_evolution_present=False)
        self.assertEqual(continuity_maturity_ceiling(ev), "L1_EXECUTION_CONTINUITY")

    def test_no_mat_transitions_ceiling_l1(self) -> None:
        ev = _full_evidence(maturity_transitions_present=False)
        self.assertEqual(continuity_maturity_ceiling(ev), "L1_EXECUTION_CONTINUITY")

    def test_no_topo_ceiling_l2(self) -> None:
        ev = _full_evidence(topology_evolution_present=False)
        self.assertEqual(continuity_maturity_ceiling(ev), "L2_CAPABILITY_CONTINUITY")

    def test_no_registry_ceiling_l2(self) -> None:
        ev = _full_evidence(registry_evolution_present=False)
        self.assertEqual(continuity_maturity_ceiling(ev), "L2_CAPABILITY_CONTINUITY")

    def test_no_drift_ceiling_l3(self) -> None:
        ev = _full_evidence(drift_analysis_completed=False)
        self.assertEqual(continuity_maturity_ceiling(ev), "L3_TOPOLOGY_CONTINUITY")

    def test_no_proofs_persisted_ceiling_l4(self) -> None:
        ev = _full_evidence(continuity_proofs_persisted=False)
        self.assertEqual(continuity_maturity_ceiling(ev), "L4_EPISTEMIC_CONTINUITY")

    def test_no_founder_ceiling_l4(self) -> None:
        ev = _full_evidence(founder_confirmed=False)
        self.assertEqual(continuity_maturity_ceiling(ev), "L4_EPISTEMIC_CONTINUITY")


# ═══════════════════════════════════════════════════════════════════
# Full pipeline tests
# ═══════════════════════════════════════════════════════════════════


class TestFullPipeline(unittest.TestCase):
    def test_no_inputs(self) -> None:
        td = Path(tempfile.mkdtemp())
        proof = build_full_continuity_proof(base_dir=td)
        self.assertTrue(proof.proof_id.startswith("CONTPROOF-"))
        self.assertEqual(proof.maturity_level, "L0_NO_CONTINUITY")

    def test_with_orch_proof(self) -> None:
        td = Path(tempfile.mkdtemp())
        orch = _make_orch_proof()
        proof = build_full_continuity_proof(
            orchestration_proof=orch,
            base_dir=td,
        )
        self.assertIsNotNone(proof.evidence)
        self.assertIsNotNone(proof.execution_memory)
        self.assertIsNotNone(proof.capability_memory)
        self.assertIsNotNone(proof.topology_memory)
        self.assertIsNotNone(proof.epistemic_memory)

    def test_strategy_simulation(self) -> None:
        td = Path(tempfile.mkdtemp())
        proof = build_full_continuity_proof(is_dry_run=True, base_dir=td)
        self.assertEqual(proof.execution_strategy, "simulation_only")

    def test_strategy_await_founder(self) -> None:
        td = Path(tempfile.mkdtemp())
        proof = build_full_continuity_proof(
            founder_confirmed=False,
            is_dry_run=False,
            base_dir=td,
        )
        self.assertEqual(proof.execution_strategy, "await_founder_confirmation")

    def test_strategy_active(self) -> None:
        td = Path(tempfile.mkdtemp())
        proof = build_full_continuity_proof(
            founder_confirmed=True,
            is_dry_run=False,
            base_dir=td,
        )
        self.assertEqual(proof.execution_strategy, "persistent_continuity_active")

    def test_evolution_scores_present(self) -> None:
        td = Path(tempfile.mkdtemp())
        proof = build_full_continuity_proof(base_dir=td)
        self.assertIsNotNone(proof.evolution_scores)

    def test_snapshot_present(self) -> None:
        td = Path(tempfile.mkdtemp())
        proof = build_full_continuity_proof(base_dir=td)
        self.assertEqual(len(proof.snapshots), 1)

    def test_to_dict_complete(self) -> None:
        td = Path(tempfile.mkdtemp())
        proof = build_full_continuity_proof(base_dir=td)
        d = proof.to_dict()
        self.assertEqual(d["proof_type"], "persistent_substrate_continuity")
        self.assertIn("evidence", d)
        self.assertIn("execution_memory", d)
        self.assertIn("capability_memory", d)
        self.assertIn("topology_memory", d)
        self.assertIn("epistemic_memory", d)


# ═══════════════════════════════════════════════════════════════════
# Proof persistence tests
# ═══════════════════════════════════════════════════════════════════


class TestProofPersistence(unittest.TestCase):
    def test_persist(self) -> None:
        td = Path(tempfile.mkdtemp())
        proof = ContinuityProof(proof_id="CONTPROOF-test1", trace_id="t1")
        path = persist_continuity_proof(proof, base_dir=td)
        self.assertTrue(path.exists())
        self.assertEqual(path.name, "CONTPROOF-test1.json")

    def test_persist_creates_dir(self) -> None:
        td = Path(tempfile.mkdtemp())
        proof = ContinuityProof()
        path = persist_continuity_proof(proof, base_dir=td)
        self.assertTrue(path.parent.exists())

    def test_persist_valid_json(self) -> None:
        td = Path(tempfile.mkdtemp())
        proof = ContinuityProof()
        path = persist_continuity_proof(proof, base_dir=td)
        data = json.loads(path.read_text())
        self.assertEqual(data["proof_type"], "persistent_substrate_continuity")

    def test_persist_full_pipeline(self) -> None:
        td = Path(tempfile.mkdtemp())
        proof = build_full_continuity_proof(
            founder_confirmed=True,
            trace_id="persist-test",
            base_dir=td,
        )
        path = persist_continuity_proof(proof, base_dir=td)
        data = json.loads(path.read_text())
        self.assertIn("evidence", data)
        self.assertIn("execution_memory", data)


# ═══════════════════════════════════════════════════════════════════
# Canonical instance separation
# ═══════════════════════════════════════════════════════════════════


class TestCanonicalInstanceSeparation(unittest.TestCase):
    def test_independent_proofs(self) -> None:
        td = Path(tempfile.mkdtemp())
        p1 = build_full_continuity_proof(trace_id="a", base_dir=td)
        p2 = build_full_continuity_proof(trace_id="b", base_dir=td)
        self.assertNotEqual(p1.proof_id, p2.proof_id)

    def test_founder_vs_no_founder(self) -> None:
        td = Path(tempfile.mkdtemp())
        p1 = build_full_continuity_proof(founder_confirmed=False, base_dir=td)
        p2 = build_full_continuity_proof(founder_confirmed=True, base_dir=td)
        self.assertNotEqual(p1.execution_strategy, p2.execution_strategy)


# ═══════════════════════════════════════════════════════════════════
# Registry integration tests
# ═══════════════════════════════════════════════════════════════════


class TestRegistryIntegration(unittest.TestCase):
    def test_registry_count_is_20(self) -> None:
        from core.registry.canonical_command_registry_v1 import (
            get_canonical_registry,
        )

        reg = get_canonical_registry()
        self.assertEqual(len(reg), 23)

    def test_continuity_report_in_registry(self) -> None:
        from core.registry.canonical_command_registry_v1 import (
            get_canonical_registry,
        )

        reg = get_canonical_registry()
        self.assertIn("!continuity-report", reg.commands)

    def test_continuity_report_action(self) -> None:
        from core.registry.canonical_command_registry_v1 import (
            get_canonical_registry,
        )

        reg = get_canonical_registry()
        self.assertIn("continuity_report", reg.actions)

    def test_router_contracts_capability_type(self) -> None:
        from core.control_plane_router.router_contracts import (
            ALLOWED_ACTION_TYPES,
            CapabilityType,
        )

        self.assertIn("continuity_report", ALLOWED_ACTION_TYPES)
        self.assertEqual(
            CapabilityType.SUBSTRATE_CONTINUITY.value,
            "substrate_continuity",
        )

    def test_router_action_map(self) -> None:
        from core.control_plane_router.control_plane_router_v1 import (
            ACTION_CAPABILITY_MAP,
        )

        self.assertIn("continuity_report", ACTION_CAPABILITY_MAP)

    def test_adapter_contracts_enum(self) -> None:
        from core.environment_bridge.windows_desktop_adapter_contracts import (
            WindowsDesktopActionType,
        )

        self.assertEqual(
            WindowsDesktopActionType.CONTINUITY_REPORT.value,
            "continuity_report",
        )

    def test_config_json(self) -> None:
        config = json.loads(Path("/opt/OS/config/control_plane_router_v1.json").read_text())
        self.assertIn("continuity_report", config["allowed_action_types"])

    def test_config_action_count(self) -> None:
        config = json.loads(Path("/opt/OS/config/control_plane_router_v1.json").read_text())
        self.assertEqual(len(config["allowed_action_types"]), 23)

    def test_adapter_registry_workers(self) -> None:
        reg = json.loads(
            Path("/opt/OS/data/registries/local_worker_adapter_registry_v1.json").read_text()
        )
        wsl = reg["workers"]["local_wsl_worker"]["capabilities"]
        win = reg["workers"]["windows_interactive_desktop_relay"]["capabilities"]
        self.assertIn("continuity_report", wsl)
        self.assertIn("continuity_report", win)

    def test_adapter_registry_capability_entry(self) -> None:
        reg = json.loads(
            Path("/opt/OS/data/registries/local_worker_adapter_registry_v1.json").read_text()
        )
        caps = reg["adapters"]["windows_interactive_desktop_relay"]["capabilities"]
        cap_ids = [c["capability_id"] for c in caps]
        self.assertIn("continuity_report", cap_ids)

    def test_allowed_action_types_count(self) -> None:
        from core.control_plane_router.router_contracts import (
            ALLOWED_ACTION_TYPES,
        )

        self.assertEqual(len(ALLOWED_ACTION_TYPES), 23)


if __name__ == "__main__":
    unittest.main()
