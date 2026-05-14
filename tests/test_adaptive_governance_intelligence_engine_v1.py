"""Tests for adaptive_governance_intelligence_engine_v1.

Phase 96.8AY. UMH substrate.
"""

from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

import os
sys.path.insert(0, os.environ.get("UMH_ROOT") or os.environ.get("OS_ROOT") or os.environ.get("EOS_ROOT") or "/opt/OS")
_ROOT = os.environ.get("UMH_ROOT") or os.environ.get("OS_ROOT") or os.environ.get("EOS_ROOT") or "/opt/OS"

from core.workstation.adaptive_governance_intelligence_engine_v1 import (
    GOVERNANCE_INTELLIGENCE_HARD_CEILINGS,
    GOVERNANCE_INTELLIGENCE_MATURITY_LEVELS,
    GOVERNANCE_INTELLIGENCE_MATURITY_REQUIREMENTS,
    GOVERNANCE_INTELLIGENCE_REPORT_DIR,
    PROPOSAL_TYPES,
    SIMULATION_POLICY_TYPES,
    AdaptiveRiskScores,
    ContinuityIntelligence,
    EpistemicIntelligence,
    GovernanceIntelligenceEvidence,
    GovernanceIntelligenceProof,
    GovernanceIntegrityIntelligence,
    GovernanceLearningMemory,
    GovernanceProposal,
    OrchestrationIntelligence,
    PolicySimulationOutcome,
    build_continuity_intelligence,
    build_epistemic_intelligence,
    build_full_governance_intelligence_proof,
    build_governance_integrity,
    build_governance_learning_memory,
    build_orchestration_intelligence,
    classify_governance_intelligence_maturity,
    compute_adaptive_risk,
    compute_governance_intelligence_maturity,
    generate_governance_proposals,
    governance_intelligence_maturity_ceiling,
    persist_governance_intelligence_proof,
    simulate_policy_changes,
)
from core.workstation.governed_recursive_orchestration_engine_v1 import (
    OrchestrationEvidence,
    OrchestrationProof,
    build_full_orchestration_proof,
)
from core.workstation.persistent_substrate_continuity_engine_v1 import (
    ContinuityEvidence,
    ContinuityProof,
    DriftSignal,
    EpistemicContinuityMemory,
    EvolutionScores,
    build_full_continuity_proof,
)
from core.workstation.recursive_capability_planning_engine_v1 import (
    build_full_capability_proof,
)


# ───────────────────────────────────────────────────────────────────
# Test data helpers
# ───────────────────────────────────────────────────────────────────


def _make_orch_proof(founder: bool = False) -> OrchestrationProof:
    cap = build_full_capability_proof(
        founder_confirmed=founder,
        trace_id="test",
        request_id="test",
    )
    return build_full_orchestration_proof(
        capability_proof=cap,
        founder_confirmed=founder,
        trace_id="test",
        request_id="test",
    )


def _make_cont_proof(founder: bool = False) -> ContinuityProof:
    td = Path(tempfile.mkdtemp())
    orch = _make_orch_proof(founder)
    return build_full_continuity_proof(
        orchestration_proof=orch,
        founder_confirmed=founder,
        trace_id="test",
        base_dir=td,
    )


def _full_gi_evidence(**overrides: object) -> GovernanceIntelligenceEvidence:
    defaults = {
        "governance_integrity_analyzed": True,
        "gate_effectiveness_scored": True,
        "orchestration_intelligence_analyzed": True,
        "sequencing_efficiency_scored": True,
        "continuity_intelligence_analyzed": True,
        "drift_trends_analyzed": True,
        "epistemic_intelligence_analyzed": True,
        "evidence_integrity_scored": True,
        "governance_proposals_generated": True,
        "governance_proposal_count": 3,
        "adaptive_risk_scored": True,
        "adaptive_risk_composite": 0.15,
        "policy_simulation_completed": True,
        "policy_simulation_count": 6,
        "governance_ceilings_enforced": True,
        "autonomous_mutation_blocked": True,
        "founder_confirmed": True,
        "is_dry_run": False,
        "trace_id": "test",
        "request_id": "test",
    }
    defaults.update(overrides)
    return GovernanceIntelligenceEvidence(**defaults)


# ═══════════════════════════════════════════════════════════════════
# Dataclass tests
# ═══════════════════════════════════════════════════════════════════


class TestGovernanceIntegrityIntelligence(unittest.TestCase):
    def test_defaults(self) -> None:
        g = GovernanceIntegrityIntelligence()
        self.assertEqual(g.gate_effectiveness, 0.0)
        self.assertFalse(g.governance_validated)

    def test_to_dict(self) -> None:
        d = GovernanceIntegrityIntelligence(gate_effectiveness=0.95).to_dict()
        self.assertEqual(d["gate_effectiveness"], 0.95)

    def test_rounding(self) -> None:
        d = GovernanceIntegrityIntelligence(gate_effectiveness=0.12345).to_dict()
        self.assertEqual(d["gate_effectiveness"], 0.123)


class TestOrchestrationIntelligence(unittest.TestCase):
    def test_defaults(self) -> None:
        o = OrchestrationIntelligence()
        self.assertEqual(o.total_simulations, 0)

    def test_to_dict(self) -> None:
        d = OrchestrationIntelligence(
            sequencing_efficiency=0.8, orchestration_entropy=0.3
        ).to_dict()
        self.assertEqual(d["sequencing_efficiency"], 0.8)
        self.assertEqual(d["orchestration_entropy"], 0.3)


class TestContinuityIntelligence(unittest.TestCase):
    def test_defaults(self) -> None:
        c = ContinuityIntelligence()
        self.assertEqual(c.drift_signal_count, 0)

    def test_to_dict(self) -> None:
        d = ContinuityIntelligence(drift_emergence_trend=0.5, lineage_breakage_count=2).to_dict()
        self.assertEqual(d["lineage_breakage_count"], 2)


class TestEpistemicIntelligence(unittest.TestCase):
    def test_defaults(self) -> None:
        e = EpistemicIntelligence()
        self.assertEqual(e.evidence_integrity_score, 0.0)

    def test_to_dict(self) -> None:
        d = EpistemicIntelligence(
            maturity_confidence_score=0.9, evidence_integrity_score=0.85
        ).to_dict()
        self.assertEqual(d["maturity_confidence_score"], 0.9)


class TestGovernanceProposal(unittest.TestCase):
    def test_auto_id(self) -> None:
        p = GovernanceProposal()
        self.assertTrue(p.proposal_id.startswith("GOVPROP-"))

    def test_fields(self) -> None:
        p = GovernanceProposal(
            proposal_type="governance_upgrade",
            title="test",
            confidence_score=0.8,
        )
        self.assertEqual(p.proposal_type, "governance_upgrade")

    def test_to_dict(self) -> None:
        d = GovernanceProposal().to_dict()
        self.assertIn("proposal_id", d)
        self.assertIn("evidence_lineage", d)
        self.assertIn("governance_risk_score", d)
        self.assertIn("confidence_score", d)

    def test_required_fields(self) -> None:
        d = GovernanceProposal(
            rationale="test",
            replay_impact="neutral",
            rollback_impact="neutral",
            blast_radius_estimate=0.1,
            continuity_impact="positive",
            governance_risk_score=0.2,
            confidence_score=0.8,
        ).to_dict()
        self.assertIn("rationale", d)
        self.assertIn("replay_impact", d)
        self.assertIn("rollback_impact", d)
        self.assertIn("blast_radius_estimate", d)
        self.assertIn("continuity_impact", d)


class TestAdaptiveRiskScores(unittest.TestCase):
    def test_defaults_zero(self) -> None:
        r = AdaptiveRiskScores()
        self.assertEqual(r.composite_risk(), 0.0)

    def test_composite_weighted(self) -> None:
        r = AdaptiveRiskScores(
            governance_fragility=1.0,
            orchestration_instability=1.0,
            replay_decay=1.0,
            rollback_uncertainty=1.0,
            topology_volatility=1.0,
            dependency_instability=1.0,
            drift_acceleration=1.0,
            entropy_growth=1.0,
        )
        self.assertAlmostEqual(r.composite_risk(), 1.0, places=2)

    def test_eight_dimensions(self) -> None:
        d = AdaptiveRiskScores().to_dict()
        dims = [
            "governance_fragility",
            "orchestration_instability",
            "replay_decay",
            "rollback_uncertainty",
            "topology_volatility",
            "dependency_instability",
            "drift_acceleration",
            "entropy_growth",
        ]
        for dim in dims:
            self.assertIn(dim, d)

    def test_composite_in_dict(self) -> None:
        d = AdaptiveRiskScores().to_dict()
        self.assertIn("composite_risk", d)


class TestPolicySimulationOutcome(unittest.TestCase):
    def test_auto_id(self) -> None:
        s = PolicySimulationOutcome()
        self.assertTrue(s.simulation_id.startswith("POLSIM-"))

    def test_fields(self) -> None:
        s = PolicySimulationOutcome(
            policy_type="stricter_governance",
            predicted_risk_delta=-0.1,
        )
        self.assertEqual(s.policy_type, "stricter_governance")

    def test_to_dict(self) -> None:
        d = PolicySimulationOutcome().to_dict()
        self.assertIn("simulation_id", d)
        self.assertIn("predicted_risk_delta", d)


class TestGovernanceLearningMemory(unittest.TestCase):
    def test_empty(self) -> None:
        m = GovernanceLearningMemory()
        self.assertEqual(len(m.proposals), 0)

    def test_with_proposals(self) -> None:
        m = GovernanceLearningMemory(proposals=[GovernanceProposal(), GovernanceProposal()])
        d = m.to_dict()
        self.assertEqual(d["proposal_count"], 2)


class TestGovernanceIntelligenceEvidence(unittest.TestCase):
    def test_defaults(self) -> None:
        e = GovernanceIntelligenceEvidence()
        self.assertFalse(e.governance_integrity_analyzed)
        self.assertTrue(e.governance_ceilings_enforced)
        self.assertTrue(e.autonomous_mutation_blocked)

    def test_to_dict(self) -> None:
        d = GovernanceIntelligenceEvidence().to_dict()
        self.assertIn("governance_ceilings_enforced", d)
        self.assertIn("autonomous_mutation_blocked", d)


class TestGovernanceIntelligenceProof(unittest.TestCase):
    def test_auto_id(self) -> None:
        p = GovernanceIntelligenceProof()
        self.assertTrue(p.proof_id.startswith("GOVINT-"))

    def test_default_maturity(self) -> None:
        p = GovernanceIntelligenceProof()
        self.assertEqual(p.maturity_level, "L0_NO_GOVERNANCE_INTELLIGENCE")

    def test_to_dict_proof_type(self) -> None:
        d = GovernanceIntelligenceProof().to_dict()
        self.assertEqual(d["proof_type"], "adaptive_governance_intelligence")

    def test_to_dict_structure(self) -> None:
        d = GovernanceIntelligenceProof().to_dict()
        for key in [
            "proof_id",
            "maturity_level",
            "proposal_count",
            "policy_simulation_count",
            "execution_strategy",
        ]:
            self.assertIn(key, d)


# ═══════════════════════════════════════════════════════════════════
# Constants tests
# ═══════════════════════════════════════════════════════════════════


class TestConstants(unittest.TestCase):
    def test_maturity_level_count(self) -> None:
        self.assertEqual(len(GOVERNANCE_INTELLIGENCE_MATURITY_LEVELS), 6)

    def test_maturity_levels_ordered(self) -> None:
        self.assertEqual(
            GOVERNANCE_INTELLIGENCE_MATURITY_LEVELS[0],
            "L0_NO_GOVERNANCE_INTELLIGENCE",
        )
        self.assertEqual(
            GOVERNANCE_INTELLIGENCE_MATURITY_LEVELS[5],
            "L5_ADAPTIVE_GOVERNANCE_INTELLIGENCE",
        )

    def test_requirements_cover_all_levels(self) -> None:
        for level in GOVERNANCE_INTELLIGENCE_MATURITY_LEVELS:
            self.assertIn(level, GOVERNANCE_INTELLIGENCE_MATURITY_REQUIREMENTS)

    def test_l0_no_requirements(self) -> None:
        self.assertEqual(
            len(GOVERNANCE_INTELLIGENCE_MATURITY_REQUIREMENTS["L0_NO_GOVERNANCE_INTELLIGENCE"]),
            0,
        )

    def test_l5_all_requirements(self) -> None:
        reqs = GOVERNANCE_INTELLIGENCE_MATURITY_REQUIREMENTS["L5_ADAPTIVE_GOVERNANCE_INTELLIGENCE"]
        self.assertGreaterEqual(len(reqs), 10)
        self.assertIn("founder_confirmed", reqs)

    def test_hard_ceilings_count(self) -> None:
        self.assertEqual(len(GOVERNANCE_INTELLIGENCE_HARD_CEILINGS), 6)

    def test_hard_ceilings_content(self) -> None:
        self.assertIn("auto_modify_governance_contracts", GOVERNANCE_INTELLIGENCE_HARD_CEILINGS)
        self.assertIn("rewrite_governance_history", GOVERNANCE_INTELLIGENCE_HARD_CEILINGS)

    def test_proposal_types_count(self) -> None:
        self.assertEqual(len(PROPOSAL_TYPES), 7)

    def test_simulation_policy_types_count(self) -> None:
        self.assertEqual(len(SIMULATION_POLICY_TYPES), 6)

    def test_report_dir(self) -> None:
        self.assertEqual(
            str(GOVERNANCE_INTELLIGENCE_REPORT_DIR),
            "data/runtime/workstation_relay/governance_intelligence_reports",
        )


# ═══════════════════════════════════════════════════════════════════
# Layer builder tests
# ═══════════════════════════════════════════════════════════════════


class TestBuildGovernanceIntegrity(unittest.TestCase):
    def test_no_inputs(self) -> None:
        g = build_governance_integrity(None, None)
        self.assertEqual(g.gate_effectiveness, 0.0)

    def test_with_orch_proof(self) -> None:
        proof = _make_orch_proof(founder=True)
        g = build_governance_integrity(proof, None)
        self.assertGreaterEqual(g.gate_effectiveness, 0.0)
        self.assertIsInstance(g.governance_validated, bool)

    def test_with_continuity_proof(self) -> None:
        cont = _make_cont_proof()
        g = build_governance_integrity(None, cont)
        self.assertIsInstance(g, GovernanceIntegrityIntelligence)

    def test_analysis_notes(self) -> None:
        proof = _make_orch_proof(founder=True)
        g = build_governance_integrity(proof, None)
        self.assertIsInstance(g.analysis_notes, list)


class TestBuildOrchestrationIntelligence(unittest.TestCase):
    def test_no_inputs(self) -> None:
        td = Path(tempfile.mkdtemp())
        o = build_orchestration_intelligence(None, td)
        self.assertEqual(o.total_simulations, 0)

    def test_with_orch_proof(self) -> None:
        td = Path(tempfile.mkdtemp())
        proof = _make_orch_proof()
        o = build_orchestration_intelligence(proof, td)
        self.assertGreater(o.total_simulations, 0)

    def test_sequencing_efficiency(self) -> None:
        td = Path(tempfile.mkdtemp())
        proof = _make_orch_proof(founder=True)
        o = build_orchestration_intelligence(proof, td)
        self.assertGreaterEqual(o.sequencing_efficiency, 0.0)

    def test_entropy(self) -> None:
        td = Path(tempfile.mkdtemp())
        proof = _make_orch_proof()
        o = build_orchestration_intelligence(proof, td)
        self.assertIsInstance(o.orchestration_entropy, float)


class TestBuildContinuityIntelligence(unittest.TestCase):
    def test_no_inputs(self) -> None:
        td = Path(tempfile.mkdtemp())
        c = build_continuity_intelligence(None, td)
        self.assertEqual(c.drift_signal_count, 0)

    def test_with_cont_proof(self) -> None:
        td = Path(tempfile.mkdtemp())
        cont = _make_cont_proof()
        c = build_continuity_intelligence(cont, td)
        self.assertIsInstance(c, ContinuityIntelligence)

    def test_drift_analysis(self) -> None:
        td = Path(tempfile.mkdtemp())
        cont = _make_cont_proof()
        c = build_continuity_intelligence(cont, td)
        self.assertIsInstance(c.drift_signal_count, int)


class TestBuildEpistemicIntelligence(unittest.TestCase):
    def test_no_inputs(self) -> None:
        e = build_epistemic_intelligence(None, None, False)
        self.assertEqual(e.evidence_integrity_score, 0.0)

    def test_with_proofs(self) -> None:
        orch = _make_orch_proof(founder=True)
        cont = _make_cont_proof()
        e = build_epistemic_intelligence(orch, cont, True)
        self.assertGreater(e.evidence_integrity_score, 0.0)

    def test_founder_reliability(self) -> None:
        orch = _make_orch_proof(founder=True)
        e = build_epistemic_intelligence(orch, None, True)
        self.assertEqual(e.founder_confirmation_reliability, 1.0)

    def test_no_founder(self) -> None:
        orch = _make_orch_proof(founder=False)
        e = build_epistemic_intelligence(orch, None, False)
        self.assertEqual(e.founder_confirmation_reliability, 0.0)


# ═══════════════════════════════════════════════════════════════════
# Adaptive risk scoring tests
# ═══════════════════════════════════════════════════════════════════


class TestComputeAdaptiveRisk(unittest.TestCase):
    def test_no_inputs(self) -> None:
        r = compute_adaptive_risk(None, None, None)
        self.assertEqual(r.composite_risk(), 0.0)

    def test_with_orch_proof(self) -> None:
        proof = _make_orch_proof()
        r = compute_adaptive_risk(proof, None, None)
        self.assertIsInstance(r.composite_risk(), float)

    def test_with_drift(self) -> None:
        drift = [DriftSignal(severity=0.7)]
        r = compute_adaptive_risk(None, None, drift)
        self.assertEqual(r.drift_acceleration, 0.7)

    def test_with_continuity(self) -> None:
        cont = _make_cont_proof()
        r = compute_adaptive_risk(None, cont, None)
        self.assertIsInstance(r, AdaptiveRiskScores)


# ═══════════════════════════════════════════════════════════════════
# Proposal generation tests
# ═══════════════════════════════════════════════════════════════════


class TestGenerateGovernanceProposals(unittest.TestCase):
    def test_determinism(self) -> None:
        gi = GovernanceIntegrityIntelligence(gate_effectiveness=0.7)
        oi = OrchestrationIntelligence(orchestration_entropy=0.5)
        ci = ContinuityIntelligence(drift_emergence_trend=0.5)
        ei = EpistemicIntelligence(evidence_integrity_score=0.6)
        ar = AdaptiveRiskScores(governance_fragility=0.5)

        p1 = generate_governance_proposals(gi, oi, ci, ei, ar)
        p2 = generate_governance_proposals(gi, oi, ci, ei, ar)
        self.assertEqual(len(p1), len(p2))
        for a, b in zip(p1, p2):
            self.assertEqual(a.proposal_type, b.proposal_type)
            self.assertEqual(a.title, b.title)

    def test_proposals_have_required_fields(self) -> None:
        gi = GovernanceIntegrityIntelligence(gate_effectiveness=0.7)
        oi = OrchestrationIntelligence(orchestration_entropy=0.5)
        ci = ContinuityIntelligence()
        ei = EpistemicIntelligence()
        ar = AdaptiveRiskScores()

        proposals = generate_governance_proposals(gi, oi, ci, ei, ar)
        for p in proposals:
            d = p.to_dict()
            self.assertIn("rationale", d)
            self.assertIn("evidence_lineage", d)
            self.assertIn("replay_impact", d)
            self.assertIn("rollback_impact", d)
            self.assertIn("blast_radius_estimate", d)
            self.assertIn("continuity_impact", d)
            self.assertIn("governance_risk_score", d)
            self.assertIn("confidence_score", d)

    def test_entropy_triggers_proposal(self) -> None:
        gi = GovernanceIntegrityIntelligence()
        oi = OrchestrationIntelligence(orchestration_entropy=0.8)
        ci = ContinuityIntelligence()
        ei = EpistemicIntelligence()
        ar = AdaptiveRiskScores()

        proposals = generate_governance_proposals(gi, oi, ci, ei, ar)
        types = [p.proposal_type for p in proposals]
        self.assertIn("entropy_reduction", types)

    def test_drift_triggers_proposal(self) -> None:
        gi = GovernanceIntegrityIntelligence()
        oi = OrchestrationIntelligence()
        ci = ContinuityIntelligence(drift_emergence_trend=0.6)
        ei = EpistemicIntelligence()
        ar = AdaptiveRiskScores()

        proposals = generate_governance_proposals(gi, oi, ci, ei, ar)
        types = [p.proposal_type for p in proposals]
        self.assertIn("drift_mitigation", types)

    def test_replay_lineage_consistency(self) -> None:
        gi = GovernanceIntegrityIntelligence(gate_effectiveness=0.5)
        oi = OrchestrationIntelligence()
        ci = ContinuityIntelligence()
        ei = EpistemicIntelligence()
        ar = AdaptiveRiskScores()

        proposals = generate_governance_proposals(gi, oi, ci, ei, ar)
        for p in proposals:
            self.assertIsInstance(p.evidence_lineage, list)


# ═══════════════════════════════════════════════════════════════════
# Policy simulation tests
# ═══════════════════════════════════════════════════════════════════


class TestSimulatePolicyChanges(unittest.TestCase):
    def test_generates_all_types(self) -> None:
        sims = simulate_policy_changes()
        types = {s.policy_type for s in sims}
        self.assertEqual(types, SIMULATION_POLICY_TYPES)

    def test_consistency(self) -> None:
        s1 = simulate_policy_changes()
        s2 = simulate_policy_changes()
        self.assertEqual(len(s1), len(s2))
        for a, b in zip(s1, s2):
            self.assertEqual(a.policy_type, b.policy_type)
            self.assertEqual(a.predicted_risk_delta, b.predicted_risk_delta)

    def test_with_risk(self) -> None:
        risk = AdaptiveRiskScores(governance_fragility=0.5)
        sims = simulate_policy_changes(adaptive_risk=risk)
        self.assertEqual(len(sims), 6)


# ═══════════════════════════════════════════════════════════════════
# Governance learning memory tests
# ═══════════════════════════════════════════════════════════════════


class TestBuildGovernanceLearningMemory(unittest.TestCase):
    def test_empty(self) -> None:
        td = Path(tempfile.mkdtemp())
        m = build_governance_learning_memory([], td)
        self.assertEqual(len(m.proposals), 0)

    def test_with_proposals(self) -> None:
        td = Path(tempfile.mkdtemp())
        props = [GovernanceProposal(title="test")]
        m = build_governance_learning_memory(props, td)
        self.assertEqual(len(m.proposals), 1)

    def test_with_history(self) -> None:
        td = Path(tempfile.mkdtemp())
        report_dir = td / GOVERNANCE_INTELLIGENCE_REPORT_DIR
        report_dir.mkdir(parents=True)
        data = {
            "proof_id": "GOVINT-test1",
            "proposals": [
                {"proposal_id": "GOVPROP-a", "status": "accepted"},
                {"proposal_id": "GOVPROP-b", "status": "rejected"},
            ],
        }
        (report_dir / "GOVINT-test1.json").write_text(json.dumps(data))
        m = build_governance_learning_memory([], td)
        self.assertIn("GOVPROP-a", m.accepted_proposals)
        self.assertIn("GOVPROP-b", m.rejected_proposals)
        self.assertIn("GOVINT-test1", m.governance_evolution_chain)


# ═══════════════════════════════════════════════════════════════════
# Maturity evaluation tests
# ═══════════════════════════════════════════════════════════════════


class TestComputeMaturity(unittest.TestCase):
    def test_dry_run(self) -> None:
        ev = _full_gi_evidence(is_dry_run=True)
        self.assertEqual(
            compute_governance_intelligence_maturity(ev),
            "L0_NO_GOVERNANCE_INTELLIGENCE",
        )

    def test_l0(self) -> None:
        ev = GovernanceIntelligenceEvidence()
        self.assertEqual(
            compute_governance_intelligence_maturity(ev),
            "L0_NO_GOVERNANCE_INTELLIGENCE",
        )

    def test_l5(self) -> None:
        ev = _full_gi_evidence()
        self.assertEqual(
            compute_governance_intelligence_maturity(ev),
            "L5_ADAPTIVE_GOVERNANCE_INTELLIGENCE",
        )


class TestMaturityCeiling(unittest.TestCase):
    def test_dry_run(self) -> None:
        ev = _full_gi_evidence(is_dry_run=True)
        self.assertEqual(
            governance_intelligence_maturity_ceiling(ev),
            "L0_NO_GOVERNANCE_INTELLIGENCE",
        )

    def test_no_governance_integrity(self) -> None:
        ev = _full_gi_evidence(governance_integrity_analyzed=False)
        self.assertEqual(
            governance_intelligence_maturity_ceiling(ev),
            "L0_NO_GOVERNANCE_INTELLIGENCE",
        )

    def test_no_orchestration(self) -> None:
        ev = _full_gi_evidence(orchestration_intelligence_analyzed=False)
        self.assertEqual(
            governance_intelligence_maturity_ceiling(ev),
            "L1_GOVERNANCE_INTEGRITY_INTELLIGENCE",
        )

    def test_no_continuity(self) -> None:
        ev = _full_gi_evidence(continuity_intelligence_analyzed=False)
        self.assertEqual(
            governance_intelligence_maturity_ceiling(ev),
            "L2_ORCHESTRATION_INTELLIGENCE",
        )

    def test_no_epistemic(self) -> None:
        ev = _full_gi_evidence(epistemic_intelligence_analyzed=False)
        self.assertEqual(
            governance_intelligence_maturity_ceiling(ev),
            "L3_CONTINUITY_INTELLIGENCE",
        )

    def test_no_proposals(self) -> None:
        ev = _full_gi_evidence(governance_proposals_generated=False)
        self.assertEqual(
            governance_intelligence_maturity_ceiling(ev),
            "L4_EPISTEMIC_INTELLIGENCE",
        )

    def test_no_simulation(self) -> None:
        ev = _full_gi_evidence(policy_simulation_completed=False)
        self.assertEqual(
            governance_intelligence_maturity_ceiling(ev),
            "L4_EPISTEMIC_INTELLIGENCE",
        )

    def test_no_founder(self) -> None:
        ev = _full_gi_evidence(founder_confirmed=False)
        self.assertEqual(
            governance_intelligence_maturity_ceiling(ev),
            "L4_EPISTEMIC_INTELLIGENCE",
        )

    def test_full_l5(self) -> None:
        ev = _full_gi_evidence()
        self.assertEqual(
            governance_intelligence_maturity_ceiling(ev),
            "L5_ADAPTIVE_GOVERNANCE_INTELLIGENCE",
        )


class TestClassifyMaturity(unittest.TestCase):
    def test_full_l5(self) -> None:
        ev = _full_gi_evidence()
        level, ceiling, blocked, reason = classify_governance_intelligence_maturity(ev)
        self.assertEqual(level, "L5_ADAPTIVE_GOVERNANCE_INTELLIGENCE")
        self.assertFalse(blocked)

    def test_dry_run(self) -> None:
        ev = _full_gi_evidence(is_dry_run=True)
        level, ceiling, blocked, reason = classify_governance_intelligence_maturity(ev)
        self.assertEqual(level, "L0_NO_GOVERNANCE_INTELLIGENCE")


# ═══════════════════════════════════════════════════════════════════
# Hard ceiling enforcement tests
# ═══════════════════════════════════════════════════════════════════


class TestHardCeilings(unittest.TestCase):
    def test_dry_run_l0(self) -> None:
        ev = _full_gi_evidence(is_dry_run=True)
        self.assertEqual(
            governance_intelligence_maturity_ceiling(ev),
            "L0_NO_GOVERNANCE_INTELLIGENCE",
        )

    def test_no_gate_l0(self) -> None:
        ev = _full_gi_evidence(gate_effectiveness_scored=False)
        self.assertEqual(
            governance_intelligence_maturity_ceiling(ev),
            "L0_NO_GOVERNANCE_INTELLIGENCE",
        )

    def test_no_sequencing_l1(self) -> None:
        ev = _full_gi_evidence(sequencing_efficiency_scored=False)
        self.assertEqual(
            governance_intelligence_maturity_ceiling(ev),
            "L1_GOVERNANCE_INTEGRITY_INTELLIGENCE",
        )

    def test_no_drift_l2(self) -> None:
        ev = _full_gi_evidence(drift_trends_analyzed=False)
        self.assertEqual(
            governance_intelligence_maturity_ceiling(ev),
            "L2_ORCHESTRATION_INTELLIGENCE",
        )

    def test_no_evidence_integrity_l3(self) -> None:
        ev = _full_gi_evidence(evidence_integrity_scored=False)
        self.assertEqual(
            governance_intelligence_maturity_ceiling(ev),
            "L3_CONTINUITY_INTELLIGENCE",
        )

    def test_no_risk_l4(self) -> None:
        ev = _full_gi_evidence(adaptive_risk_scored=False)
        self.assertEqual(
            governance_intelligence_maturity_ceiling(ev),
            "L4_EPISTEMIC_INTELLIGENCE",
        )

    def test_ceilings_always_enforced(self) -> None:
        ev = _full_gi_evidence()
        self.assertTrue(ev.governance_ceilings_enforced)
        self.assertTrue(ev.autonomous_mutation_blocked)

    def test_hard_ceiling_set_immutable(self) -> None:
        self.assertIn(
            "auto_modify_governance_contracts",
            GOVERNANCE_INTELLIGENCE_HARD_CEILINGS,
        )
        self.assertIn(
            "auto_deploy_governance_changes",
            GOVERNANCE_INTELLIGENCE_HARD_CEILINGS,
        )


# ═══════════════════════════════════════════════════════════════════
# Full pipeline tests
# ═══════════════════════════════════════════════════════════════════


class TestFullPipeline(unittest.TestCase):
    def test_no_inputs(self) -> None:
        td = Path(tempfile.mkdtemp())
        proof = build_full_governance_intelligence_proof(base_dir=td)
        self.assertTrue(proof.proof_id.startswith("GOVINT-"))

    def test_with_proofs(self) -> None:
        td = Path(tempfile.mkdtemp())
        orch = _make_orch_proof(founder=True)
        cont = build_full_continuity_proof(
            orchestration_proof=orch,
            founder_confirmed=True,
            base_dir=td,
        )
        proof = build_full_governance_intelligence_proof(
            orchestration_proof=orch,
            continuity_proof=cont,
            founder_confirmed=True,
            base_dir=td,
        )
        self.assertIsNotNone(proof.governance_integrity)
        self.assertIsNotNone(proof.orchestration_intelligence)
        self.assertIsNotNone(proof.continuity_intelligence)
        self.assertIsNotNone(proof.epistemic_intelligence)
        self.assertIsNotNone(proof.adaptive_risk)

    def test_strategy_simulation(self) -> None:
        td = Path(tempfile.mkdtemp())
        proof = build_full_governance_intelligence_proof(is_dry_run=True, base_dir=td)
        self.assertEqual(proof.execution_strategy, "simulation_only")

    def test_strategy_await_founder(self) -> None:
        td = Path(tempfile.mkdtemp())
        proof = build_full_governance_intelligence_proof(founder_confirmed=False, base_dir=td)
        self.assertEqual(proof.execution_strategy, "await_founder_confirmation")

    def test_strategy_active(self) -> None:
        td = Path(tempfile.mkdtemp())
        proof = build_full_governance_intelligence_proof(founder_confirmed=True, base_dir=td)
        self.assertEqual(proof.execution_strategy, "adaptive_governance_active")

    def test_proposals_present(self) -> None:
        td = Path(tempfile.mkdtemp())
        proof = build_full_governance_intelligence_proof(base_dir=td)
        self.assertIsInstance(proof.proposals, list)

    def test_simulations_present(self) -> None:
        td = Path(tempfile.mkdtemp())
        proof = build_full_governance_intelligence_proof(base_dir=td)
        self.assertEqual(len(proof.policy_simulations), 6)

    def test_learning_memory_present(self) -> None:
        td = Path(tempfile.mkdtemp())
        proof = build_full_governance_intelligence_proof(base_dir=td)
        self.assertIsNotNone(proof.learning_memory)

    def test_to_dict_complete(self) -> None:
        td = Path(tempfile.mkdtemp())
        proof = build_full_governance_intelligence_proof(base_dir=td)
        d = proof.to_dict()
        self.assertEqual(d["proof_type"], "adaptive_governance_intelligence")
        for key in [
            "governance_integrity",
            "orchestration_intelligence",
            "continuity_intelligence",
            "epistemic_intelligence",
            "adaptive_risk",
            "learning_memory",
        ]:
            self.assertIn(key, d)


# ═══════════════════════════════════════════════════════════════════
# Proof persistence tests
# ═══════════════════════════════════════════════════════════════════


class TestProofPersistence(unittest.TestCase):
    def test_persist(self) -> None:
        td = Path(tempfile.mkdtemp())
        proof = GovernanceIntelligenceProof(proof_id="GOVINT-test1")
        path = persist_governance_intelligence_proof(proof, base_dir=td)
        self.assertTrue(path.exists())
        self.assertEqual(path.name, "GOVINT-test1.json")

    def test_persist_valid_json(self) -> None:
        td = Path(tempfile.mkdtemp())
        proof = GovernanceIntelligenceProof()
        path = persist_governance_intelligence_proof(proof, base_dir=td)
        data = json.loads(path.read_text())
        self.assertEqual(data["proof_type"], "adaptive_governance_intelligence")

    def test_persist_full_pipeline(self) -> None:
        td = Path(tempfile.mkdtemp())
        proof = build_full_governance_intelligence_proof(
            founder_confirmed=True,
            trace_id="persist-test",
            base_dir=td,
        )
        path = persist_governance_intelligence_proof(proof, base_dir=td)
        data = json.loads(path.read_text())
        self.assertIn("evidence", data)
        self.assertIn("proposals", data)

    def test_persist_creates_dir(self) -> None:
        td = Path(tempfile.mkdtemp())
        proof = GovernanceIntelligenceProof()
        path = persist_governance_intelligence_proof(proof, base_dir=td)
        self.assertTrue(path.parent.exists())


# ═══════════════════════════════════════════════════════════════════
# Canonical instance separation
# ═══════════════════════════════════════════════════════════════════


class TestCanonicalInstanceSeparation(unittest.TestCase):
    def test_independent_proofs(self) -> None:
        td = Path(tempfile.mkdtemp())
        p1 = build_full_governance_intelligence_proof(trace_id="a", base_dir=td)
        p2 = build_full_governance_intelligence_proof(trace_id="b", base_dir=td)
        self.assertNotEqual(p1.proof_id, p2.proof_id)

    def test_founder_vs_no_founder(self) -> None:
        td = Path(tempfile.mkdtemp())
        p1 = build_full_governance_intelligence_proof(founder_confirmed=False, base_dir=td)
        p2 = build_full_governance_intelligence_proof(founder_confirmed=True, base_dir=td)
        self.assertNotEqual(p1.execution_strategy, p2.execution_strategy)


# ═══════════════════════════════════════════════════════════════════
# Registry integration tests
# ═══════════════════════════════════════════════════════════════════


class TestRegistryIntegration(unittest.TestCase):
    def test_registry_count_is_20(self) -> None:
        from composition.registries.canonical_command_registry_v1 import get_canonical_registry

        reg = get_canonical_registry()
        self.assertEqual(len(reg), 27)

    def test_gov_intel_report_in_registry(self) -> None:
        from composition.registries.canonical_command_registry_v1 import get_canonical_registry

        reg = get_canonical_registry()
        self.assertIn("!governance-intelligence-report", reg.commands)

    def test_gov_intel_report_action(self) -> None:
        from composition.registries.canonical_command_registry_v1 import get_canonical_registry

        reg = get_canonical_registry()
        self.assertIn("governance_intelligence_report", reg.actions)

    def test_router_contracts(self) -> None:
        from control_plane.router.router_contracts import (
            ALLOWED_ACTION_TYPES,
            CapabilityType,
        )

        self.assertIn("governance_intelligence_report", ALLOWED_ACTION_TYPES)
        self.assertEqual(
            CapabilityType.GOVERNANCE_INTELLIGENCE.value,
            "governance_intelligence",
        )

    def test_router_action_map(self) -> None:
        from control_plane.router.control_plane_router_v1 import ACTION_CAPABILITY_MAP

        self.assertIn("governance_intelligence_report", ACTION_CAPABILITY_MAP)

    def test_adapter_contracts_enum(self) -> None:
        from execution.environments.windows_desktop_adapter_contracts import (
            WindowsDesktopActionType,
        )

        self.assertEqual(
            WindowsDesktopActionType.GOVERNANCE_INTELLIGENCE_REPORT.value,
            "governance_intelligence_report",
        )

    def test_config_json(self) -> None:
        config = json.loads((Path(_ROOT) / "config" / "control_plane_router_v1.json").read_text())
        self.assertIn("governance_intelligence_report", config["allowed_action_types"])

    def test_config_action_count(self) -> None:
        config = json.loads((Path(_ROOT) / "config" / "control_plane_router_v1.json").read_text())
        self.assertEqual(len(config["allowed_action_types"]), 27)

    def test_adapter_registry_workers(self) -> None:
        reg = json.loads(
            (Path(_ROOT) / "data" / "registries" / "local_worker_adapter_registry_v1.json").read_text()
        )
        wsl = reg["workers"]["local_wsl_worker"]["capabilities"]
        win = reg["workers"]["windows_interactive_desktop_relay"]["capabilities"]
        self.assertIn("governance_intelligence_report", wsl)
        self.assertIn("governance_intelligence_report", win)

    def test_adapter_registry_capability_entry(self) -> None:
        reg = json.loads(
            (Path(_ROOT) / "data" / "registries" / "local_worker_adapter_registry_v1.json").read_text()
        )
        caps = reg["adapters"]["windows_interactive_desktop_relay"]["capabilities"]
        cap_ids = [c["capability_id"] for c in caps]
        self.assertIn("governance_intelligence_report", cap_ids)

    def test_allowed_action_types_count(self) -> None:
        from control_plane.router.router_contracts import ALLOWED_ACTION_TYPES

        self.assertEqual(len(ALLOWED_ACTION_TYPES), 27)


if __name__ == "__main__":
    unittest.main()
