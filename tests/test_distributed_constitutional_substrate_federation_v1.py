"""Tests for Distributed Constitutional Substrate Federation v1.

Covers:
  1. All constants (counts, membership, types)
  2. All dataclass contracts (fields, defaults, to_dict, post_init)
  3. Layer 1: Federated node registry builder
  4. Layer 2: Federated replay coordination builder
  5. Layer 3: Federated continuity coordination builder
  6. Layer 4: Federated constitutional governance builder
  7. Federation trust scoring (7 dimensions)
  8. Federation drift detection (7 types)
  9. Federation emergency governance
  10. Federation hard ceiling enforcement
  11. Federation simulation engine (8 types)
  12. Maturity classification + ceilings (L0-L5)
  13. Full pipeline integration
  14. Proof persistence
  15. Canonical instance separation
  16. Registry integration (21 commands, parity checks)
"""

import json
import shutil
import sys
import unittest
from dataclasses import fields
from pathlib import Path

sys.path.insert(0, "/opt/OS")
sys.path.insert(0, "/opt/OS/services")


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------


class TestConstants(unittest.TestCase):
    def test_maturity_levels_count(self) -> None:
        from core.workstation.distributed_constitutional_substrate_federation_v1 import (
            FEDERATION_MATURITY_LEVELS,
        )

        self.assertEqual(len(FEDERATION_MATURITY_LEVELS), 6)

    def test_maturity_levels_order(self) -> None:
        from core.workstation.distributed_constitutional_substrate_federation_v1 import (
            FEDERATION_MATURITY_LEVELS,
        )

        self.assertEqual(FEDERATION_MATURITY_LEVELS[0], "L0_NO_FEDERATION")
        self.assertEqual(FEDERATION_MATURITY_LEVELS[5], "L5_DISTRIBUTED_CONSTITUTIONAL_FEDERATION")

    def test_trust_dimensions_count(self) -> None:
        from core.workstation.distributed_constitutional_substrate_federation_v1 import (
            FEDERATION_TRUST_DIMENSIONS,
        )

        self.assertEqual(len(FEDERATION_TRUST_DIMENSIONS), 7)

    def test_trust_dimensions_membership(self) -> None:
        from core.workstation.distributed_constitutional_substrate_federation_v1 import (
            FEDERATION_TRUST_DIMENSIONS,
        )

        self.assertIn("replay_reliability", FEDERATION_TRUST_DIMENSIONS)
        self.assertIn("federation_drift_risk", FEDERATION_TRUST_DIMENSIONS)

    def test_drift_types_count(self) -> None:
        from core.workstation.distributed_constitutional_substrate_federation_v1 import (
            FEDERATION_DRIFT_TYPES,
        )

        self.assertEqual(len(FEDERATION_DRIFT_TYPES), 7)

    def test_drift_types_membership(self) -> None:
        from core.workstation.distributed_constitutional_substrate_federation_v1 import (
            FEDERATION_DRIFT_TYPES,
        )

        self.assertIn("node_divergence", FEDERATION_DRIFT_TYPES)
        self.assertIn("federation_entropy", FEDERATION_DRIFT_TYPES)

    def test_emergency_actions_count(self) -> None:
        from core.workstation.distributed_constitutional_substrate_federation_v1 import (
            FEDERATION_EMERGENCY_ACTIONS,
        )

        self.assertEqual(len(FEDERATION_EMERGENCY_ACTIONS), 6)

    def test_emergency_actions_is_frozenset(self) -> None:
        from core.workstation.distributed_constitutional_substrate_federation_v1 import (
            FEDERATION_EMERGENCY_ACTIONS,
        )

        self.assertIsInstance(FEDERATION_EMERGENCY_ACTIONS, frozenset)

    def test_hard_ceilings_count(self) -> None:
        from core.workstation.distributed_constitutional_substrate_federation_v1 import (
            FEDERATION_HARD_CEILINGS,
        )

        self.assertEqual(len(FEDERATION_HARD_CEILINGS), 7)

    def test_hard_ceilings_is_frozenset(self) -> None:
        from core.workstation.distributed_constitutional_substrate_federation_v1 import (
            FEDERATION_HARD_CEILINGS,
        )

        self.assertIsInstance(FEDERATION_HARD_CEILINGS, frozenset)

    def test_hard_ceilings_membership(self) -> None:
        from core.workstation.distributed_constitutional_substrate_federation_v1 import (
            FEDERATION_HARD_CEILINGS,
        )

        self.assertIn("incompatible_constitutional_node", FEDERATION_HARD_CEILINGS)
        self.assertIn("distributed_replay_corruption", FEDERATION_HARD_CEILINGS)

    def test_simulation_types_count(self) -> None:
        from core.workstation.distributed_constitutional_substrate_federation_v1 import (
            FEDERATION_SIMULATION_TYPES,
        )

        self.assertEqual(len(FEDERATION_SIMULATION_TYPES), 8)

    def test_simulation_types_membership(self) -> None:
        from core.workstation.distributed_constitutional_substrate_federation_v1 import (
            FEDERATION_SIMULATION_TYPES,
        )

        self.assertIn("node_failure", FEDERATION_SIMULATION_TYPES)
        self.assertIn("distributed_emergency_recovery", FEDERATION_SIMULATION_TYPES)

    def test_lineage_types_count(self) -> None:
        from core.workstation.distributed_constitutional_substrate_federation_v1 import (
            FEDERATION_LINEAGE_TYPES,
        )

        self.assertEqual(len(FEDERATION_LINEAGE_TYPES), 6)

    def test_lineage_types_membership(self) -> None:
        from core.workstation.distributed_constitutional_substrate_federation_v1 import (
            FEDERATION_LINEAGE_TYPES,
        )

        self.assertIn("node_lineage", FEDERATION_LINEAGE_TYPES)
        self.assertIn("federated_governance_lineage", FEDERATION_LINEAGE_TYPES)


# ---------------------------------------------------------------------------
# Dataclass Contracts
# ---------------------------------------------------------------------------


class TestFederatedNode(unittest.TestCase):
    def test_defaults(self) -> None:
        from core.workstation.distributed_constitutional_substrate_federation_v1 import (
            FederatedNode,
        )

        n = FederatedNode()
        self.assertTrue(n.node_id.startswith("NODE-"))
        self.assertFalse(n.online)
        self.assertFalse(n.replay_compatible)
        self.assertEqual(n.trust_classification, "untrusted")

    def test_to_dict_keys(self) -> None:
        from core.workstation.distributed_constitutional_substrate_federation_v1 import (
            FederatedNode,
        )

        d = FederatedNode().to_dict()
        self.assertIn("node_id", d)
        self.assertIn("constitutional_hash", d)
        self.assertIn("online", d)


class TestFederatedNodeRegistry(unittest.TestCase):
    def test_defaults(self) -> None:
        from core.workstation.distributed_constitutional_substrate_federation_v1 import (
            FederatedNodeRegistry,
        )

        r = FederatedNodeRegistry()
        self.assertTrue(r.federation_id.startswith("FED-"))
        self.assertEqual(r.node_count(), 0)

    def test_counts(self) -> None:
        from core.workstation.distributed_constitutional_substrate_federation_v1 import (
            FederatedNode,
            FederatedNodeRegistry,
        )

        r = FederatedNodeRegistry(
            nodes=[
                FederatedNode(online=True, trust_classification="trusted"),
                FederatedNode(online=False, trust_classification="untrusted"),
            ]
        )
        self.assertEqual(r.node_count(), 2)
        self.assertEqual(r.online_count(), 1)
        self.assertEqual(r.trusted_count(), 1)

    def test_registry_hash(self) -> None:
        from core.workstation.distributed_constitutional_substrate_federation_v1 import (
            FederatedNodeRegistry,
        )

        r = FederatedNodeRegistry()
        h = r.compute_registry_hash()
        self.assertEqual(len(h), 16)

    def test_to_dict(self) -> None:
        from core.workstation.distributed_constitutional_substrate_federation_v1 import (
            FederatedNodeRegistry,
        )

        d = FederatedNodeRegistry().to_dict()
        self.assertIn("federation_id", d)
        self.assertIn("node_count", d)


class TestFederatedReplayCoordination(unittest.TestCase):
    def test_defaults(self) -> None:
        from core.workstation.distributed_constitutional_substrate_federation_v1 import (
            FederatedReplayCoordination,
        )

        c = FederatedReplayCoordination()
        self.assertFalse(c.cross_node_replay_validated)
        self.assertEqual(c.replay_determinism_score, 0.0)

    def test_to_dict(self) -> None:
        from core.workstation.distributed_constitutional_substrate_federation_v1 import (
            FederatedReplayCoordination,
        )

        d = FederatedReplayCoordination().to_dict()
        self.assertIn("cross_node_replay_validated", d)
        self.assertIn("replay_determinism_score", d)


class TestFederatedContinuityCoordination(unittest.TestCase):
    def test_defaults(self) -> None:
        from core.workstation.distributed_constitutional_substrate_federation_v1 import (
            FederatedContinuityCoordination,
        )

        c = FederatedContinuityCoordination()
        self.assertFalse(c.distributed_continuity_lineage)
        self.assertEqual(c.continuity_preservation_score, 0.0)

    def test_to_dict(self) -> None:
        from core.workstation.distributed_constitutional_substrate_federation_v1 import (
            FederatedContinuityCoordination,
        )

        d = FederatedContinuityCoordination().to_dict()
        self.assertIn("distributed_continuity_lineage", d)
        self.assertIn("governance_lineage_preservation_score", d)


class TestFederatedConstitutionalGovernance(unittest.TestCase):
    def test_defaults(self) -> None:
        from core.workstation.distributed_constitutional_substrate_federation_v1 import (
            FederatedConstitutionalGovernance,
        )

        g = FederatedConstitutionalGovernance()
        self.assertFalse(g.constitutional_compatibility_validated)
        self.assertEqual(g.compatible_node_count, 0)

    def test_to_dict(self) -> None:
        from core.workstation.distributed_constitutional_substrate_federation_v1 import (
            FederatedConstitutionalGovernance,
        )

        d = FederatedConstitutionalGovernance().to_dict()
        self.assertIn("constitutional_compatibility_validated", d)
        self.assertIn("constitutional_invariant_score", d)


class TestFederationTrustScores(unittest.TestCase):
    def test_defaults(self) -> None:
        from core.workstation.distributed_constitutional_substrate_federation_v1 import (
            FederationTrustScores,
        )

        t = FederationTrustScores()
        self.assertEqual(t.composite_trust(), 0.0)

    def test_composite(self) -> None:
        from core.workstation.distributed_constitutional_substrate_federation_v1 import (
            FederationTrustScores,
        )

        t = FederationTrustScores(
            replay_reliability=0.7,
            governance_reliability=0.7,
            continuity_reliability=0.7,
            rollback_reliability=0.7,
            topology_stability=0.7,
            constitutional_integrity=0.7,
            federation_drift_risk=0.7,
        )
        self.assertAlmostEqual(t.composite_trust(), 0.7, places=3)

    def test_to_dict_has_composite(self) -> None:
        from core.workstation.distributed_constitutional_substrate_federation_v1 import (
            FederationTrustScores,
        )

        d = FederationTrustScores().to_dict()
        self.assertIn("composite_trust", d)
        self.assertEqual(len(d), 8)  # 7 dimensions + composite


class TestFederationDriftSignal(unittest.TestCase):
    def test_defaults(self) -> None:
        from core.workstation.distributed_constitutional_substrate_federation_v1 import (
            FederationDriftSignal,
        )

        s = FederationDriftSignal(drift_type="node_divergence", severity=0.5)
        self.assertEqual(s.drift_type, "node_divergence")
        self.assertTrue(s.timestamp)

    def test_to_dict(self) -> None:
        from core.workstation.distributed_constitutional_substrate_federation_v1 import (
            FederationDriftSignal,
        )

        d = FederationDriftSignal().to_dict()
        self.assertIn("drift_type", d)
        self.assertIn("severity", d)


class TestFederatedEmergencyGovernance(unittest.TestCase):
    def test_defaults(self) -> None:
        from core.workstation.distributed_constitutional_substrate_federation_v1 import (
            FederatedEmergencyGovernance,
        )

        e = FederatedEmergencyGovernance()
        self.assertFalse(e.all_emergency_actions_available)
        self.assertEqual(e.available_count, 0)

    def test_to_dict(self) -> None:
        from core.workstation.distributed_constitutional_substrate_federation_v1 import (
            FederatedEmergencyGovernance,
        )

        d = FederatedEmergencyGovernance().to_dict()
        self.assertIn("node_quarantine_available", d)
        self.assertIn("emergency_action_count", d)


class TestFederationSimulationOutcome(unittest.TestCase):
    def test_defaults(self) -> None:
        from core.workstation.distributed_constitutional_substrate_federation_v1 import (
            FederationSimulationOutcome,
        )

        s = FederationSimulationOutcome(simulation_type="node_failure")
        self.assertTrue(s.simulation_id.startswith("FEDSIM-"))
        self.assertTrue(s.recovery_possible)

    def test_to_dict(self) -> None:
        from core.workstation.distributed_constitutional_substrate_federation_v1 import (
            FederationSimulationOutcome,
        )

        d = FederationSimulationOutcome().to_dict()
        self.assertIn("simulation_id", d)
        self.assertIn("cascading_failures", d)


class TestFederationEvidence(unittest.TestCase):
    def test_defaults(self) -> None:
        from core.workstation.distributed_constitutional_substrate_federation_v1 import (
            FederationEvidence,
        )

        e = FederationEvidence()
        self.assertFalse(e.node_registry_analyzed)
        self.assertTrue(e.hard_ceilings_enforced)
        self.assertTrue(e.governance_bypass_blocked)

    def test_to_dict_keys(self) -> None:
        from core.workstation.distributed_constitutional_substrate_federation_v1 import (
            FederationEvidence,
        )

        d = FederationEvidence().to_dict()
        self.assertIn("node_count", d)
        self.assertIn("trust_composite", d)
        self.assertIn("hard_ceilings_enforced", d)

    def test_field_count(self) -> None:
        from core.workstation.distributed_constitutional_substrate_federation_v1 import (
            FederationEvidence,
        )

        self.assertEqual(len(fields(FederationEvidence)), 28)


class TestFederationProof(unittest.TestCase):
    def test_defaults(self) -> None:
        from core.workstation.distributed_constitutional_substrate_federation_v1 import (
            FederationProof,
        )

        p = FederationProof()
        self.assertTrue(p.proof_id.startswith("FEDRT-"))
        self.assertEqual(p.maturity_level, "L0_NO_FEDERATION")
        self.assertFalse(p.escalation_blocked)

    def test_to_dict_has_proof_type(self) -> None:
        from core.workstation.distributed_constitutional_substrate_federation_v1 import (
            FederationProof,
        )

        d = FederationProof().to_dict()
        self.assertEqual(d["proof_type"], "distributed_constitutional_federation")


# ---------------------------------------------------------------------------
# Layer 1: Node Registry Builder
# ---------------------------------------------------------------------------


class TestBuildNodeRegistry(unittest.TestCase):
    def test_no_proofs(self) -> None:
        from core.workstation.distributed_constitutional_substrate_federation_v1 import (
            build_node_registry,
        )

        import tempfile

        tmp = Path(tempfile.mkdtemp())
        try:
            reg = build_node_registry(base_dir=tmp)
            self.assertEqual(reg.node_count(), 1)
            primary = reg.nodes[0]
            self.assertEqual(primary.node_name, "primary_vps")
            self.assertTrue(primary.online)
            self.assertEqual(primary.trust_classification, "untrusted")
        finally:
            shutil.rmtree(tmp)

    def test_with_constitutional_proof(self) -> None:
        from core.workstation.distributed_constitutional_substrate_federation_v1 import (
            build_node_registry,
        )
        from core.workstation.constitutional_substrate_governance_layer_v1 import (
            build_full_constitutional_proof,
        )
        from core.workstation.governed_recursive_orchestration_engine_v1 import (
            build_full_orchestration_proof,
        )
        from core.workstation.persistent_substrate_continuity_engine_v1 import (
            build_full_continuity_proof,
        )
        from core.workstation.recursive_capability_planning_engine_v1 import (
            build_full_capability_proof,
        )

        cap = build_full_capability_proof(founder_confirmed=True, trace_id="t1", request_id="r1")
        orch = build_full_orchestration_proof(
            capability_proof=cap, founder_confirmed=True, trace_id="t1", request_id="r1"
        )
        cont = build_full_continuity_proof(
            orchestration_proof=orch,
            capability_proof=cap,
            founder_confirmed=True,
            trace_id="t1",
            request_id="r1",
        )
        const = build_full_constitutional_proof(
            orchestration_proof=orch,
            continuity_proof=cont,
            founder_confirmed=True,
            trace_id="t1",
            request_id="r1",
        )

        reg = build_node_registry(const, orch, cont)
        primary = reg.nodes[0]
        self.assertEqual(primary.trust_classification, "trusted")
        self.assertTrue(primary.constitutionally_compatible)
        self.assertTrue(primary.replay_compatible)
        self.assertTrue(primary.continuity_compatible)
        self.assertTrue(len(primary.constitutional_hash) > 0)


# ---------------------------------------------------------------------------
# Layer 2: Replay Coordination Builder
# ---------------------------------------------------------------------------


class TestBuildReplayCoordination(unittest.TestCase):
    def test_empty(self) -> None:
        from core.workstation.distributed_constitutional_substrate_federation_v1 import (
            FederatedNodeRegistry,
            build_replay_coordination,
        )

        coord = build_replay_coordination(FederatedNodeRegistry())
        self.assertFalse(coord.cross_node_replay_validated)
        self.assertEqual(coord.replay_determinism_score, 0.0)

    def test_with_orchestration(self) -> None:
        from core.workstation.distributed_constitutional_substrate_federation_v1 import (
            FederatedNodeRegistry,
            build_replay_coordination,
        )
        from core.workstation.governed_recursive_orchestration_engine_v1 import (
            build_full_orchestration_proof,
        )
        from core.workstation.recursive_capability_planning_engine_v1 import (
            build_full_capability_proof,
        )

        cap = build_full_capability_proof(founder_confirmed=True, trace_id="t", request_id="r")
        orch = build_full_orchestration_proof(
            capability_proof=cap, founder_confirmed=True, trace_id="t", request_id="r"
        )
        reg = FederatedNodeRegistry()
        coord = build_replay_coordination(reg, orch)
        self.assertTrue(coord.cross_node_replay_validated)
        self.assertGreater(coord.replay_determinism_score, 0)


# ---------------------------------------------------------------------------
# Layer 3: Continuity Coordination Builder
# ---------------------------------------------------------------------------


class TestBuildContinuityCoordination(unittest.TestCase):
    def test_empty(self) -> None:
        from core.workstation.distributed_constitutional_substrate_federation_v1 import (
            FederatedNodeRegistry,
            build_continuity_coordination,
        )

        coord = build_continuity_coordination(FederatedNodeRegistry())
        self.assertFalse(coord.distributed_continuity_lineage)

    def test_with_continuity_proof(self) -> None:
        from core.workstation.distributed_constitutional_substrate_federation_v1 import (
            FederatedNodeRegistry,
            build_continuity_coordination,
        )
        from core.workstation.governed_recursive_orchestration_engine_v1 import (
            build_full_orchestration_proof,
        )
        from core.workstation.persistent_substrate_continuity_engine_v1 import (
            build_full_continuity_proof,
        )
        from core.workstation.recursive_capability_planning_engine_v1 import (
            build_full_capability_proof,
        )

        cap = build_full_capability_proof(founder_confirmed=True, trace_id="t", request_id="r")
        orch = build_full_orchestration_proof(
            capability_proof=cap, founder_confirmed=True, trace_id="t", request_id="r"
        )
        cont = build_full_continuity_proof(
            orchestration_proof=orch,
            capability_proof=cap,
            founder_confirmed=True,
            trace_id="t",
            request_id="r",
        )
        reg = FederatedNodeRegistry()
        coord = build_continuity_coordination(reg, cont, orchestration_proof=orch)
        self.assertTrue(coord.distributed_continuity_lineage)
        self.assertGreater(coord.continuity_preservation_score, 0)


# ---------------------------------------------------------------------------
# Layer 4: Constitutional Governance Builder
# ---------------------------------------------------------------------------


class TestBuildConstitutionalGovernance(unittest.TestCase):
    def test_empty(self) -> None:
        from core.workstation.distributed_constitutional_substrate_federation_v1 import (
            FederatedNodeRegistry,
            build_constitutional_governance,
        )

        gov = build_constitutional_governance(FederatedNodeRegistry())
        self.assertFalse(gov.constitutional_compatibility_validated)

    def test_with_proofs(self) -> None:
        from core.workstation.distributed_constitutional_substrate_federation_v1 import (
            build_node_registry,
            build_constitutional_governance,
        )
        from core.workstation.constitutional_substrate_governance_layer_v1 import (
            build_full_constitutional_proof,
        )
        from core.workstation.governed_recursive_orchestration_engine_v1 import (
            build_full_orchestration_proof,
        )
        from core.workstation.persistent_substrate_continuity_engine_v1 import (
            build_full_continuity_proof,
        )
        from core.workstation.adaptive_governance_intelligence_engine_v1 import (
            build_full_governance_intelligence_proof,
        )
        from core.workstation.recursive_capability_planning_engine_v1 import (
            build_full_capability_proof,
        )

        cap = build_full_capability_proof(founder_confirmed=True, trace_id="t", request_id="r")
        orch = build_full_orchestration_proof(
            capability_proof=cap, founder_confirmed=True, trace_id="t", request_id="r"
        )
        cont = build_full_continuity_proof(
            orchestration_proof=orch,
            capability_proof=cap,
            founder_confirmed=True,
            trace_id="t",
            request_id="r",
        )
        gov_intel = build_full_governance_intelligence_proof(
            orchestration_proof=orch,
            continuity_proof=cont,
            capability_proof=cap,
            founder_confirmed=True,
            trace_id="t",
            request_id="r",
        )
        const = build_full_constitutional_proof(
            orchestration_proof=orch,
            continuity_proof=cont,
            governance_proof=gov_intel,
            capability_proof=cap,
            founder_confirmed=True,
            trace_id="t",
            request_id="r",
        )

        reg = build_node_registry(const, orch, cont)
        fed_gov = build_constitutional_governance(reg, const, gov_intel, founder_confirmed=True)
        self.assertTrue(fed_gov.constitutional_compatibility_validated)
        self.assertTrue(fed_gov.authority_boundaries_enforced)
        self.assertTrue(fed_gov.governance_federation_validated)
        self.assertTrue(fed_gov.emergency_federation_governance)
        self.assertGreater(fed_gov.constitutional_invariant_score, 0)


# ---------------------------------------------------------------------------
# Federation Trust Scoring
# ---------------------------------------------------------------------------


class TestComputeFederationTrust(unittest.TestCase):
    def test_empty(self) -> None:
        from core.workstation.distributed_constitutional_substrate_federation_v1 import (
            FederatedNodeRegistry,
            FederatedReplayCoordination,
            FederatedContinuityCoordination,
            FederatedConstitutionalGovernance,
            compute_federation_trust,
        )

        trust = compute_federation_trust(
            FederatedNodeRegistry(),
            FederatedReplayCoordination(),
            FederatedContinuityCoordination(),
            FederatedConstitutionalGovernance(),
        )
        self.assertEqual(trust.composite_trust(), 0.0)

    def test_dimension_count(self) -> None:
        from core.workstation.distributed_constitutional_substrate_federation_v1 import (
            FederationTrustScores,
        )

        d = FederationTrustScores().to_dict()
        trust_keys = [k for k in d if k != "composite_trust"]
        self.assertEqual(len(trust_keys), 7)


# ---------------------------------------------------------------------------
# Federation Drift Detection
# ---------------------------------------------------------------------------


class TestDetectFederationDrift(unittest.TestCase):
    def test_minimal(self) -> None:
        from core.workstation.distributed_constitutional_substrate_federation_v1 import (
            FederatedNodeRegistry,
            FederatedReplayCoordination,
            FederatedContinuityCoordination,
            FederatedConstitutionalGovernance,
            detect_federation_drift,
        )

        signals = detect_federation_drift(
            FederatedNodeRegistry(),
            FederatedReplayCoordination(),
            FederatedContinuityCoordination(),
            FederatedConstitutionalGovernance(),
        )
        self.assertIsInstance(signals, list)
        drift_types = {s.drift_type for s in signals}
        self.assertIn("governance_divergence", drift_types)

    def test_offline_node_entropy(self) -> None:
        from core.workstation.distributed_constitutional_substrate_federation_v1 import (
            FederatedNode,
            FederatedNodeRegistry,
            FederatedReplayCoordination,
            FederatedContinuityCoordination,
            FederatedConstitutionalGovernance,
            detect_federation_drift,
        )

        reg = FederatedNodeRegistry(
            nodes=[
                FederatedNode(node_name="primary_vps", online=True),
                FederatedNode(node_name="secondary", online=False),
            ]
        )
        signals = detect_federation_drift(
            reg,
            FederatedReplayCoordination(),
            FederatedContinuityCoordination(),
            FederatedConstitutionalGovernance(),
        )
        entropy_signals = [s for s in signals if s.drift_type == "federation_entropy"]
        self.assertEqual(len(entropy_signals), 1)


# ---------------------------------------------------------------------------
# Federation Emergency Governance
# ---------------------------------------------------------------------------


class TestBuildEmergencyGovernance(unittest.TestCase):
    def test_no_proofs(self) -> None:
        from core.workstation.distributed_constitutional_substrate_federation_v1 import (
            build_emergency_governance,
        )

        eg = build_emergency_governance()
        self.assertEqual(eg.emergency_action_count, 6)
        self.assertEqual(eg.available_count, 0)
        self.assertFalse(eg.all_emergency_actions_available)

    def test_full_proofs_with_founder(self) -> None:
        from core.workstation.distributed_constitutional_substrate_federation_v1 import (
            build_emergency_governance,
            build_node_registry,
        )
        from core.workstation.constitutional_substrate_governance_layer_v1 import (
            build_full_constitutional_proof,
        )
        from core.workstation.governed_recursive_orchestration_engine_v1 import (
            build_full_orchestration_proof,
        )
        from core.workstation.persistent_substrate_continuity_engine_v1 import (
            build_full_continuity_proof,
        )
        from core.workstation.recursive_capability_planning_engine_v1 import (
            build_full_capability_proof,
        )

        cap = build_full_capability_proof(founder_confirmed=True, trace_id="t", request_id="r")
        orch = build_full_orchestration_proof(
            capability_proof=cap, founder_confirmed=True, trace_id="t", request_id="r"
        )
        cont = build_full_continuity_proof(
            orchestration_proof=orch,
            capability_proof=cap,
            founder_confirmed=True,
            trace_id="t",
            request_id="r",
        )
        const = build_full_constitutional_proof(
            orchestration_proof=orch,
            continuity_proof=cont,
            founder_confirmed=True,
            trace_id="t",
            request_id="r",
        )
        reg = build_node_registry(const, orch, cont)

        eg = build_emergency_governance(const, orch, reg, founder_confirmed=True)
        self.assertEqual(eg.available_count, 6)
        self.assertTrue(eg.all_emergency_actions_available)


# ---------------------------------------------------------------------------
# Hard Ceiling Enforcement
# ---------------------------------------------------------------------------


class TestEnforceFederationHardCeilings(unittest.TestCase):
    def test_no_violations(self) -> None:
        from core.workstation.distributed_constitutional_substrate_federation_v1 import (
            FederatedNode,
            FederatedNodeRegistry,
            FederatedReplayCoordination,
            FederatedContinuityCoordination,
            FederatedConstitutionalGovernance,
            enforce_federation_hard_ceilings,
        )

        reg = FederatedNodeRegistry(
            nodes=[FederatedNode(constitutionally_compatible=True, online=True)]
        )
        gov = FederatedConstitutionalGovernance(
            compatible_node_count=1,
            incompatible_node_count=0,
            governance_federation_validated=True,
        )
        replay = FederatedReplayCoordination(
            replay_drift_detected=False,
        )
        cont = FederatedContinuityCoordination(
            distributed_continuity_lineage=True,
        )
        blocked, reasons = enforce_federation_hard_ceilings(reg, gov, replay, cont)
        self.assertFalse(blocked)

    def test_incompatible_node_blocks(self) -> None:
        from core.workstation.distributed_constitutional_substrate_federation_v1 import (
            FederatedNodeRegistry,
            FederatedReplayCoordination,
            FederatedContinuityCoordination,
            FederatedConstitutionalGovernance,
            enforce_federation_hard_ceilings,
        )

        gov = FederatedConstitutionalGovernance(incompatible_node_count=2)
        blocked, reasons = enforce_federation_hard_ceilings(
            FederatedNodeRegistry(),
            gov,
            FederatedReplayCoordination(),
            FederatedContinuityCoordination(),
        )
        self.assertTrue(blocked)
        self.assertTrue(any("incompatible_constitutional_node" in r for r in reasons))

    def test_replay_drift_blocks(self) -> None:
        from core.workstation.distributed_constitutional_substrate_federation_v1 import (
            FederatedNodeRegistry,
            FederatedReplayCoordination,
            FederatedContinuityCoordination,
            FederatedConstitutionalGovernance,
            enforce_federation_hard_ceilings,
        )

        replay = FederatedReplayCoordination(replay_drift_detected=True, replay_drift_severity=0.8)
        blocked, reasons = enforce_federation_hard_ceilings(
            FederatedNodeRegistry(),
            FederatedConstitutionalGovernance(),
            replay,
            FederatedContinuityCoordination(),
        )
        self.assertTrue(blocked)
        self.assertTrue(any("replay_breaking_federation" in r for r in reasons))


# ---------------------------------------------------------------------------
# Simulation Engine
# ---------------------------------------------------------------------------


class TestRunFederationSimulations(unittest.TestCase):
    def test_produces_8_simulations(self) -> None:
        from core.workstation.distributed_constitutional_substrate_federation_v1 import (
            FederatedNodeRegistry,
            FederationTrustScores,
            run_federation_simulations,
        )

        sims = run_federation_simulations(FederatedNodeRegistry(), FederationTrustScores(), [])
        self.assertEqual(len(sims), 8)

    def test_simulation_types_covered(self) -> None:
        from core.workstation.distributed_constitutional_substrate_federation_v1 import (
            FEDERATION_SIMULATION_TYPES,
            FederatedNodeRegistry,
            FederationTrustScores,
            run_federation_simulations,
        )

        sims = run_federation_simulations(FederatedNodeRegistry(), FederationTrustScores(), [])
        sim_types = {s.simulation_type for s in sims}
        self.assertEqual(sim_types, set(FEDERATION_SIMULATION_TYPES))

    def test_all_have_ids(self) -> None:
        from core.workstation.distributed_constitutional_substrate_federation_v1 import (
            FederatedNodeRegistry,
            FederationTrustScores,
            run_federation_simulations,
        )

        sims = run_federation_simulations(FederatedNodeRegistry(), FederationTrustScores(), [])
        for s in sims:
            self.assertTrue(s.simulation_id.startswith("FEDSIM-"))


# ---------------------------------------------------------------------------
# Maturity Classification
# ---------------------------------------------------------------------------


class TestMaturityClassification(unittest.TestCase):
    def test_l0_no_evidence(self) -> None:
        from core.workstation.distributed_constitutional_substrate_federation_v1 import (
            FederationEvidence,
            classify_federation_maturity,
        )

        ev = FederationEvidence(
            hard_ceilings_enforced=False,
            governance_bypass_blocked=False,
        )
        level, ceiling, blocked, reason = classify_federation_maturity(ev)
        self.assertEqual(level, "L0_NO_FEDERATION")
        self.assertTrue(blocked)

    def test_l0_dry_run(self) -> None:
        from core.workstation.distributed_constitutional_substrate_federation_v1 import (
            FederationEvidence,
            classify_federation_maturity,
        )

        ev = FederationEvidence(
            node_registry_analyzed=True,
            node_count=1,
            is_dry_run=True,
        )
        level, ceiling, blocked, reason = classify_federation_maturity(ev)
        self.assertEqual(ceiling, "L0_NO_FEDERATION")
        self.assertTrue(blocked)
        self.assertIn("dry run", reason)

    def test_l5_full(self) -> None:
        from core.workstation.distributed_constitutional_substrate_federation_v1 import (
            FederationEvidence,
            classify_federation_maturity,
        )

        ev = FederationEvidence(
            node_registry_analyzed=True,
            node_count=2,
            online_count=2,
            trusted_count=2,
            replay_coordination_analyzed=True,
            replay_determinism_validated=True,
            rollback_determinism_validated=True,
            continuity_coordination_analyzed=True,
            continuity_preservation_validated=True,
            governance_lineage_preserved=True,
            constitutional_governance_analyzed=True,
            constitutional_compatibility_validated=True,
            constitutional_invariants_preserved=True,
            trust_scored=True,
            trust_composite=0.8,
            drift_analyzed=True,
            emergency_governance_analyzed=True,
            emergency_actions_available=6,
            simulations_completed=True,
            simulation_count=8,
            hard_ceilings_enforced=True,
            governance_bypass_blocked=True,
            founder_confirmed=True,
        )
        level, ceiling, blocked, reason = classify_federation_maturity(ev)
        self.assertEqual(level, "L5_DISTRIBUTED_CONSTITUTIONAL_FEDERATION")
        self.assertEqual(ceiling, "L5_DISTRIBUTED_CONSTITUTIONAL_FEDERATION")
        self.assertFalse(blocked)

    def test_ceiling_blocks_level(self) -> None:
        from core.workstation.distributed_constitutional_substrate_federation_v1 import (
            FederationEvidence,
            classify_federation_maturity,
        )

        ev = FederationEvidence(
            node_registry_analyzed=True,
            node_count=1,
            replay_coordination_analyzed=False,
            hard_ceilings_enforced=False,
            governance_bypass_blocked=False,
        )
        level, ceiling, blocked, reason = classify_federation_maturity(ev)
        self.assertIn(level, ("L0_NO_FEDERATION", "L1_NODE_REGISTERED"))
        self.assertTrue(blocked)


# ---------------------------------------------------------------------------
# Full Pipeline
# ---------------------------------------------------------------------------


class TestFullPipeline(unittest.TestCase):
    def test_minimal_pipeline(self) -> None:
        from core.workstation.distributed_constitutional_substrate_federation_v1 import (
            build_full_federation_proof,
        )

        proof = build_full_federation_proof(trace_id="test", request_id="req")
        self.assertTrue(proof.proof_id.startswith("FEDRT-"))
        self.assertIsNotNone(proof.evidence)
        self.assertIsNotNone(proof.node_registry)
        self.assertIsNotNone(proof.replay_coordination)
        self.assertIsNotNone(proof.continuity_coordination)
        self.assertIsNotNone(proof.constitutional_governance)
        self.assertIsNotNone(proof.trust_scores)
        self.assertIsNotNone(proof.emergency_governance)
        self.assertEqual(len(proof.simulations), 8)
        self.assertIn("L", proof.maturity_level)

    def test_full_proof_chain(self) -> None:
        from core.workstation.distributed_constitutional_substrate_federation_v1 import (
            build_full_federation_proof,
        )
        from core.workstation.constitutional_substrate_governance_layer_v1 import (
            build_full_constitutional_proof,
        )
        from core.workstation.adaptive_governance_intelligence_engine_v1 import (
            build_full_governance_intelligence_proof,
        )
        from core.workstation.governed_recursive_orchestration_engine_v1 import (
            build_full_orchestration_proof,
        )
        from core.workstation.persistent_substrate_continuity_engine_v1 import (
            build_full_continuity_proof,
        )
        from core.workstation.recursive_capability_planning_engine_v1 import (
            build_full_capability_proof,
        )

        cap = build_full_capability_proof(founder_confirmed=True, trace_id="t", request_id="r")
        orch = build_full_orchestration_proof(
            capability_proof=cap, founder_confirmed=True, trace_id="t", request_id="r"
        )
        cont = build_full_continuity_proof(
            orchestration_proof=orch,
            capability_proof=cap,
            founder_confirmed=True,
            trace_id="t",
            request_id="r",
        )
        gov = build_full_governance_intelligence_proof(
            orchestration_proof=orch,
            continuity_proof=cont,
            capability_proof=cap,
            founder_confirmed=True,
            trace_id="t",
            request_id="r",
        )
        const = build_full_constitutional_proof(
            orchestration_proof=orch,
            continuity_proof=cont,
            governance_proof=gov,
            capability_proof=cap,
            founder_confirmed=True,
            trace_id="t",
            request_id="r",
        )

        proof = build_full_federation_proof(
            constitutional_proof=const,
            orchestration_proof=orch,
            continuity_proof=cont,
            governance_proof=gov,
            capability_proof=cap,
            founder_confirmed=True,
            trace_id="t",
            request_id="r",
        )
        self.assertEqual(proof.maturity_level, "L5_DISTRIBUTED_CONSTITUTIONAL_FEDERATION")
        self.assertFalse(proof.escalation_blocked)
        self.assertEqual(proof.execution_strategy, "distributed_federation_active")
        self.assertTrue(proof.evidence.founder_confirmed)

    def test_dry_run(self) -> None:
        from core.workstation.distributed_constitutional_substrate_federation_v1 import (
            build_full_federation_proof,
        )

        proof = build_full_federation_proof(is_dry_run=True, trace_id="dry", request_id="dry")
        self.assertEqual(proof.execution_strategy, "simulation_only")
        self.assertTrue(proof.evidence.is_dry_run)

    def test_no_founder_strategy(self) -> None:
        from core.workstation.distributed_constitutional_substrate_federation_v1 import (
            build_full_federation_proof,
        )

        proof = build_full_federation_proof(founder_confirmed=False, trace_id="nf", request_id="nf")
        self.assertEqual(proof.execution_strategy, "await_founder_confirmation")


# ---------------------------------------------------------------------------
# Persistence
# ---------------------------------------------------------------------------


class TestPersistence(unittest.TestCase):
    def test_persist_and_read(self) -> None:
        import tempfile

        from core.workstation.distributed_constitutional_substrate_federation_v1 import (
            build_full_federation_proof,
            persist_federation_proof,
        )

        tmp = Path(tempfile.mkdtemp())
        try:
            proof = build_full_federation_proof(trace_id="persist", request_id="persist")
            path = persist_federation_proof(proof, base_dir=tmp)
            self.assertTrue(path.exists())
            self.assertTrue(path.name.startswith("FEDRT-"))
            data = json.loads(path.read_text())
            self.assertEqual(data["proof_type"], "distributed_constitutional_federation")
            self.assertIn("evidence", data)
            self.assertIn("node_registry", data)
        finally:
            shutil.rmtree(tmp)

    def test_persist_full_pipeline(self) -> None:
        import tempfile

        from core.workstation.distributed_constitutional_substrate_federation_v1 import (
            build_full_federation_proof,
            persist_federation_proof,
        )
        from core.workstation.constitutional_substrate_governance_layer_v1 import (
            build_full_constitutional_proof,
        )
        from core.workstation.adaptive_governance_intelligence_engine_v1 import (
            build_full_governance_intelligence_proof,
        )
        from core.workstation.governed_recursive_orchestration_engine_v1 import (
            build_full_orchestration_proof,
        )
        from core.workstation.persistent_substrate_continuity_engine_v1 import (
            build_full_continuity_proof,
        )
        from core.workstation.recursive_capability_planning_engine_v1 import (
            build_full_capability_proof,
        )

        tmp = Path(tempfile.mkdtemp())
        try:
            cap = build_full_capability_proof(founder_confirmed=True, trace_id="t", request_id="r")
            orch = build_full_orchestration_proof(
                capability_proof=cap, founder_confirmed=True, trace_id="t", request_id="r"
            )
            cont = build_full_continuity_proof(
                orchestration_proof=orch,
                capability_proof=cap,
                founder_confirmed=True,
                trace_id="t",
                request_id="r",
            )
            gov = build_full_governance_intelligence_proof(
                orchestration_proof=orch,
                continuity_proof=cont,
                capability_proof=cap,
                founder_confirmed=True,
                trace_id="t",
                request_id="r",
            )
            const = build_full_constitutional_proof(
                orchestration_proof=orch,
                continuity_proof=cont,
                governance_proof=gov,
                capability_proof=cap,
                founder_confirmed=True,
                trace_id="t",
                request_id="r",
            )

            proof = build_full_federation_proof(
                constitutional_proof=const,
                orchestration_proof=orch,
                continuity_proof=cont,
                governance_proof=gov,
                capability_proof=cap,
                founder_confirmed=True,
                trace_id="t",
                request_id="r",
                base_dir=tmp,
            )
            path = persist_federation_proof(proof, base_dir=tmp)
            self.assertTrue(path.exists())
            data = json.loads(path.read_text())
            self.assertEqual(data["maturity_level"], "L5_DISTRIBUTED_CONSTITUTIONAL_FEDERATION")
        finally:
            shutil.rmtree(tmp)


# ---------------------------------------------------------------------------
# Instance Separation
# ---------------------------------------------------------------------------


class TestInstanceSeparation(unittest.TestCase):
    def test_separate_proofs(self) -> None:
        from core.workstation.distributed_constitutional_substrate_federation_v1 import (
            build_full_federation_proof,
        )

        p1 = build_full_federation_proof(trace_id="a", request_id="a")
        p2 = build_full_federation_proof(trace_id="b", request_id="b")
        self.assertNotEqual(p1.proof_id, p2.proof_id)
        self.assertNotEqual(p1.trace_id, p2.trace_id)

    def test_separate_registries(self) -> None:
        from core.workstation.distributed_constitutional_substrate_federation_v1 import (
            FederatedNodeRegistry,
        )

        r1 = FederatedNodeRegistry()
        r2 = FederatedNodeRegistry()
        self.assertNotEqual(r1.federation_id, r2.federation_id)


# ---------------------------------------------------------------------------
# Registry Integration
# ---------------------------------------------------------------------------


class TestRegistryIntegration(unittest.TestCase):
    def test_canonical_registry_count(self) -> None:
        from core.registry.canonical_command_registry_v1 import get_canonical_registry

        reg = get_canonical_registry()
        self.assertEqual(len(reg), 22)

    def test_federation_report_registered(self) -> None:
        from core.registry.canonical_command_registry_v1 import get_canonical_registry

        reg = get_canonical_registry()
        self.assertTrue(reg.contains("!federation-report"))
        entry = reg.get("!federation-report")
        self.assertEqual(entry.canonical_action, "federation_report")
        self.assertEqual(entry.capability_type, "DISTRIBUTED_FEDERATION")

    def test_action_types_count(self) -> None:
        from core.control_plane_router.router_contracts import ALLOWED_ACTION_TYPES

        self.assertEqual(len(ALLOWED_ACTION_TYPES), 22)

    def test_federation_report_in_action_types(self) -> None:
        from core.control_plane_router.router_contracts import ALLOWED_ACTION_TYPES

        self.assertIn("federation_report", ALLOWED_ACTION_TYPES)

    def test_router_map_count(self) -> None:
        from core.control_plane_router.control_plane_router_v1 import ACTION_CAPABILITY_MAP

        self.assertEqual(len(ACTION_CAPABILITY_MAP), 22)

    def test_router_map_has_federation(self) -> None:
        from core.control_plane_router.control_plane_router_v1 import ACTION_CAPABILITY_MAP

        self.assertIn("federation_report", ACTION_CAPABILITY_MAP)

    def test_adapter_contracts_has_federation(self) -> None:
        from core.environment_bridge.windows_desktop_adapter_contracts import (
            WindowsDesktopActionType,
        )

        self.assertEqual(WindowsDesktopActionType.FEDERATION_REPORT.value, "federation_report")

    def test_config_has_federation(self) -> None:
        config_path = Path("/opt/OS/config/control_plane_router_v1.json")
        data = json.loads(config_path.read_text())
        self.assertIn("federation_report", data["allowed_action_types"])
        self.assertEqual(len(data["allowed_action_types"]), 22)

    def test_adapter_registry_has_federation(self) -> None:
        reg_path = Path("/opt/OS/data/registries/local_worker_adapter_registry_v1.json")
        data = json.loads(reg_path.read_text())
        wsl_caps = data["workers"]["local_wsl_worker"]["capabilities"]
        win_caps = data["workers"]["windows_interactive_desktop_relay"]["capabilities"]
        self.assertIn("federation_report", wsl_caps)
        self.assertIn("federation_report", win_caps)

    def test_expected_command_set(self) -> None:
        from core.registry.canonical_command_registry_v1 import get_canonical_registry

        reg = get_canonical_registry()
        expected = {
            "!ping",
            "!chrome",
            "!chrome-open-google-drive",
            "!chrome-proof",
            "!doc",
            "!extract",
            "!ingest-candidate",
            "!ingest-safe-doc",
            "!ingest-safe-doc-cu",
            "!explore-environment",
            "!promote-memory",
            "!query-memory",
            "!actuator-proof",
            "!adapter-report",
            "!capability-report",
            "!orchestration-report",
            "!continuity-report",
            "!governance-intelligence-report",
            "!constitution-report",
            "!economics-report",
            "!federation-report",
            "!relay-status",
        }
        self.assertEqual(reg.commands, expected)

    def test_handler_dispatch_has_federation(self) -> None:
        from handlers.substrate_command_handler import SUBSTRATE_COMMANDS

        self.assertIn("!federation-report", SUBSTRATE_COMMANDS)
        self.assertEqual(len(SUBSTRATE_COMMANDS), 22)

    def test_parity_registry_vs_router(self) -> None:
        from core.registry.canonical_command_registry_v1 import get_canonical_registry
        from core.control_plane_router.router_contracts import ALLOWED_ACTION_TYPES

        reg = get_canonical_registry()
        self.assertEqual(len(reg), len(ALLOWED_ACTION_TYPES))


if __name__ == "__main__":
    unittest.main()
