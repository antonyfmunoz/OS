"""Tests for Constitutional Substrate Governance Layer v1.

Covers:
  1. All dataclass contracts
  2. All constants (counts, membership)
  3. Layer 1: Safety invariant enforcement
  4. Layer 2: Authority boundary enforcement
  5. Layer 3: Continuity contract enforcement
  6. Layer 4: Emergency governance
  7. Constitutional integrity validation
  8. Mutation classification
  9. Constitutional risk scoring
  10. Governance contract builder
  11. Hard ceiling enforcement
  12. Constitutional simulation engine
  13. Constitutional migration contracts
  14. Maturity classification + ceilings
  15. Full pipeline integration
  16. Proof persistence
  17. Canonical instance separation
  18. Registry integration (20 commands, parity checks)
"""

import json
import sys
import unittest
from dataclasses import fields
from pathlib import Path

import os
sys.path.insert(0, os.environ.get("UMH_ROOT") or os.environ.get("OS_ROOT") or os.environ.get("EOS_ROOT") or "/opt/OS")
_ROOT = os.environ.get("UMH_ROOT") or os.environ.get("OS_ROOT") or os.environ.get("EOS_ROOT") or "/opt/OS"
sys.path.insert(0, os.path.join(os.environ.get("UMH_ROOT") or os.environ.get("OS_ROOT") or os.environ.get("EOS_ROOT") or "/opt/OS", "services"))


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------


class TestConstants(unittest.TestCase):
    def test_maturity_levels_count(self) -> None:
        from core.workstation.constitutional_substrate_governance_layer_v1 import (
            CONSTITUTIONAL_MATURITY_LEVELS,
        )

        self.assertEqual(len(CONSTITUTIONAL_MATURITY_LEVELS), 6)

    def test_maturity_levels_order(self) -> None:
        from core.workstation.constitutional_substrate_governance_layer_v1 import (
            CONSTITUTIONAL_MATURITY_LEVELS,
        )

        self.assertEqual(CONSTITUTIONAL_MATURITY_LEVELS[0], "L0_NO_CONSTITUTIONAL_GOVERNANCE")
        self.assertEqual(
            CONSTITUTIONAL_MATURITY_LEVELS[5], "L5_CONSTITUTIONAL_RECURSIVE_GOVERNANCE"
        )

    def test_safety_invariants_count(self) -> None:
        from core.workstation.constitutional_substrate_governance_layer_v1 import (
            CONSTITUTIONAL_SAFETY_INVARIANTS,
        )

        self.assertEqual(len(CONSTITUTIONAL_SAFETY_INVARIANTS), 6)

    def test_authority_boundaries_count(self) -> None:
        from core.workstation.constitutional_substrate_governance_layer_v1 import (
            CONSTITUTIONAL_AUTHORITY_BOUNDARIES,
        )

        self.assertEqual(len(CONSTITUTIONAL_AUTHORITY_BOUNDARIES), 5)

    def test_continuity_contracts_count(self) -> None:
        from core.workstation.constitutional_substrate_governance_layer_v1 import (
            CONSTITUTIONAL_CONTINUITY_CONTRACTS,
        )

        self.assertEqual(len(CONSTITUTIONAL_CONTINUITY_CONTRACTS), 5)

    def test_emergency_actions_count(self) -> None:
        from core.workstation.constitutional_substrate_governance_layer_v1 import (
            CONSTITUTIONAL_EMERGENCY_ACTIONS,
        )

        self.assertEqual(len(CONSTITUTIONAL_EMERGENCY_ACTIONS), 6)

    def test_hard_ceilings_count(self) -> None:
        from core.workstation.constitutional_substrate_governance_layer_v1 import (
            CONSTITUTIONAL_HARD_CEILINGS,
        )

        self.assertEqual(len(CONSTITUTIONAL_HARD_CEILINGS), 8)

    def test_integrity_checks_count(self) -> None:
        from core.workstation.constitutional_substrate_governance_layer_v1 import (
            CONSTITUTIONAL_INTEGRITY_CHECKS,
        )

        self.assertEqual(len(CONSTITUTIONAL_INTEGRITY_CHECKS), 7)

    def test_mutation_classifications_count(self) -> None:
        from core.workstation.constitutional_substrate_governance_layer_v1 import (
            MUTATION_CLASSIFICATIONS,
        )

        self.assertEqual(len(MUTATION_CLASSIFICATIONS), 6)

    def test_risk_dimensions_count(self) -> None:
        from core.workstation.constitutional_substrate_governance_layer_v1 import (
            CONSTITUTIONAL_RISK_DIMENSIONS,
        )

        self.assertEqual(len(CONSTITUTIONAL_RISK_DIMENSIONS), 7)

    def test_simulation_types_count(self) -> None:
        from core.workstation.constitutional_substrate_governance_layer_v1 import (
            CONSTITUTIONAL_SIMULATION_TYPES,
        )

        self.assertEqual(len(CONSTITUTIONAL_SIMULATION_TYPES), 8)

    def test_migration_requirements_count(self) -> None:
        from core.workstation.constitutional_substrate_governance_layer_v1 import (
            CONSTITUTIONAL_MIGRATION_REQUIREMENTS,
        )

        self.assertEqual(len(CONSTITUTIONAL_MIGRATION_REQUIREMENTS), 6)

    def test_hard_ceilings_immutable(self) -> None:
        from core.workstation.constitutional_substrate_governance_layer_v1 import (
            CONSTITUTIONAL_HARD_CEILINGS,
        )

        self.assertIsInstance(CONSTITUTIONAL_HARD_CEILINGS, frozenset)

    def test_safety_invariants_immutable(self) -> None:
        from core.workstation.constitutional_substrate_governance_layer_v1 import (
            CONSTITUTIONAL_SAFETY_INVARIANTS,
        )

        self.assertIsInstance(CONSTITUTIONAL_SAFETY_INVARIANTS, frozenset)


# ---------------------------------------------------------------------------
# Dataclass contracts
# ---------------------------------------------------------------------------


class TestDataclassContracts(unittest.TestCase):
    def test_safety_invariant_status_to_dict(self) -> None:
        from core.workstation.constitutional_substrate_governance_layer_v1 import (
            ConstitutionalSafetyInvariantStatus,
        )

        s = ConstitutionalSafetyInvariantStatus()
        d = s.to_dict()
        self.assertIn("all_invariants_active", d)
        self.assertIn("invariant_count", d)

    def test_authority_boundary_status_to_dict(self) -> None:
        from core.workstation.constitutional_substrate_governance_layer_v1 import (
            ConstitutionalAuthorityBoundaryStatus,
        )

        s = ConstitutionalAuthorityBoundaryStatus()
        d = s.to_dict()
        self.assertIn("all_boundaries_enforced", d)
        self.assertIn("violations_detected", d)

    def test_continuity_contract_status_to_dict(self) -> None:
        from core.workstation.constitutional_substrate_governance_layer_v1 import (
            ConstitutionalContinuityContractStatus,
        )

        s = ConstitutionalContinuityContractStatus()
        d = s.to_dict()
        self.assertIn("all_contracts_enforced", d)

    def test_emergency_governance_status_to_dict(self) -> None:
        from core.workstation.constitutional_substrate_governance_layer_v1 import (
            ConstitutionalEmergencyGovernanceStatus,
        )

        s = ConstitutionalEmergencyGovernanceStatus()
        d = s.to_dict()
        self.assertIn("all_emergency_actions_available", d)

    def test_integrity_result_to_dict(self) -> None:
        from core.workstation.constitutional_substrate_governance_layer_v1 import (
            ConstitutionalIntegrityResult,
        )

        r = ConstitutionalIntegrityResult()
        d = r.to_dict()
        self.assertIn("all_integrity_checks_pass", d)
        self.assertIn("replay_integrity", d)
        self.assertEqual(len([k for k in d if k.endswith("_integrity")]), 7)

    def test_mutation_classification_to_dict(self) -> None:
        from core.workstation.constitutional_substrate_governance_layer_v1 import (
            ConstitutionalMutationClassification,
        )

        m = ConstitutionalMutationClassification()
        d = m.to_dict()
        self.assertIn("classification", d)
        self.assertEqual(d["classification"], "safe_mutation")

    def test_risk_scores_to_dict(self) -> None:
        from core.workstation.constitutional_substrate_governance_layer_v1 import (
            ConstitutionalRiskScores,
        )

        r = ConstitutionalRiskScores()
        d = r.to_dict()
        self.assertIn("composite_risk", d)
        self.assertEqual(len(d), 8)

    def test_risk_scores_composite(self) -> None:
        from core.workstation.constitutional_substrate_governance_layer_v1 import (
            ConstitutionalRiskScores,
        )

        r = ConstitutionalRiskScores(constitutional_fragility=0.7, invariant_pressure=0.3)
        self.assertGreater(r.composite_risk(), 0)

    def test_governance_contract_to_dict(self) -> None:
        from core.workstation.constitutional_substrate_governance_layer_v1 import (
            ConstitutionalGovernanceContract,
        )

        c = ConstitutionalGovernanceContract()
        d = c.to_dict()
        self.assertIn("invariant_compatibility", d)
        self.assertIn("approved", d)

    def test_simulation_outcome_to_dict(self) -> None:
        from core.workstation.constitutional_substrate_governance_layer_v1 import (
            ConstitutionalSimulationOutcome,
        )

        s = ConstitutionalSimulationOutcome(simulation_type="test")
        d = s.to_dict()
        self.assertIn("simulation_id", d)
        self.assertTrue(d["simulation_id"].startswith("CONSIM-"))

    def test_migration_contract_to_dict(self) -> None:
        from core.workstation.constitutional_substrate_governance_layer_v1 import (
            ConstitutionalMigrationContract,
        )

        m = ConstitutionalMigrationContract()
        d = m.to_dict()
        self.assertIn("all_requirements_met", d)
        self.assertTrue(d["migration_id"].startswith("CONMIG-"))

    def test_evidence_to_dict(self) -> None:
        from core.workstation.constitutional_substrate_governance_layer_v1 import (
            ConstitutionalEvidence,
        )

        e = ConstitutionalEvidence()
        d = e.to_dict()
        self.assertIn("hard_ceilings_enforced", d)
        self.assertIn("governance_bypass_blocked", d)

    def test_proof_to_dict(self) -> None:
        from core.workstation.constitutional_substrate_governance_layer_v1 import (
            ConstitutionalProof,
        )

        p = ConstitutionalProof(trace_id="test")
        d = p.to_dict()
        self.assertEqual(d["proof_type"], "constitutional_substrate_governance")
        self.assertTrue(d["proof_id"].startswith("CONST-"))

    def test_proof_auto_fields(self) -> None:
        from core.workstation.constitutional_substrate_governance_layer_v1 import (
            ConstitutionalProof,
        )

        p = ConstitutionalProof(trace_id="auto-test")
        self.assertTrue(p.proof_id.startswith("CONST-"))
        self.assertGreater(len(p.timestamp), 0)


# ---------------------------------------------------------------------------
# Layer 1: Safety invariant enforcement
# ---------------------------------------------------------------------------


class TestBuildSafetyInvariants(unittest.TestCase):
    def test_no_inputs(self) -> None:
        from core.workstation.constitutional_substrate_governance_layer_v1 import (
            build_safety_invariants,
        )

        s = build_safety_invariants()
        self.assertEqual(s.invariant_count, 6)
        self.assertEqual(s.active_count, 0)
        self.assertFalse(s.all_invariants_active)

    def test_with_orchestration_proof(self) -> None:
        from core.workstation.constitutional_substrate_governance_layer_v1 import (
            build_safety_invariants,
        )
        from core.workstation.governed_recursive_orchestration_engine_v1 import (
            OrchestrationProof,
            OrchestrationEvidence,
        )

        ev = OrchestrationEvidence(
            replay_validated=True,
            rollback_validated=True,
            governance_validated=True,
        )
        proof = OrchestrationProof(evidence=ev)
        s = build_safety_invariants(orchestration_proof=proof)
        self.assertTrue(s.replayability_required)
        self.assertTrue(s.rollbackability_required)
        self.assertTrue(s.governance_lineage_required)
        self.assertGreaterEqual(s.active_count, 3)

    def test_full_invariants(self) -> None:
        from core.workstation.constitutional_substrate_governance_layer_v1 import (
            build_safety_invariants,
        )
        from core.workstation.governed_recursive_orchestration_engine_v1 import (
            OrchestrationProof,
            OrchestrationEvidence,
        )
        from core.workstation.persistent_substrate_continuity_engine_v1 import (
            ContinuityProof,
            ContinuityEvidence,
        )
        from core.workstation.adaptive_governance_intelligence_engine_v1 import (
            GovernanceIntelligenceProof,
            GovernanceIntelligenceEvidence,
        )

        oev = OrchestrationEvidence(
            replay_validated=True, rollback_validated=True, governance_validated=True
        )
        cev = ContinuityEvidence(execution_lineage_present=True)
        gev = GovernanceIntelligenceEvidence(
            governance_ceilings_enforced=True, autonomous_mutation_blocked=True
        )
        s = build_safety_invariants(
            OrchestrationProof(evidence=oev),
            ContinuityProof(evidence=cev),
            GovernanceIntelligenceProof(evidence=gev),
        )
        self.assertTrue(s.all_invariants_active)
        self.assertEqual(s.active_count, 6)


# ---------------------------------------------------------------------------
# Layer 2: Authority boundary enforcement
# ---------------------------------------------------------------------------


class TestBuildAuthorityBoundaries(unittest.TestCase):
    def test_no_inputs(self) -> None:
        from core.workstation.constitutional_substrate_governance_layer_v1 import (
            build_authority_boundaries,
        )

        ab = build_authority_boundaries()
        self.assertEqual(ab.boundary_count, 5)
        self.assertEqual(ab.enforced_count, 5)
        self.assertTrue(ab.all_boundaries_enforced)
        self.assertEqual(ab.violations_detected, 0)

    def test_violation_detected(self) -> None:
        from core.workstation.constitutional_substrate_governance_layer_v1 import (
            build_authority_boundaries,
        )
        from core.workstation.adaptive_governance_intelligence_engine_v1 import (
            GovernanceIntelligenceProof,
            GovernanceIntelligenceEvidence,
        )

        gev = GovernanceIntelligenceEvidence(
            autonomous_mutation_blocked=False, governance_ceilings_enforced=False
        )
        ab = build_authority_boundaries(GovernanceIntelligenceProof(evidence=gev))
        self.assertGreater(ab.violations_detected, 0)
        self.assertFalse(ab.all_boundaries_enforced)


# ---------------------------------------------------------------------------
# Layer 3: Continuity contract enforcement
# ---------------------------------------------------------------------------


class TestBuildContinuityContracts(unittest.TestCase):
    def test_no_inputs(self) -> None:
        from core.workstation.constitutional_substrate_governance_layer_v1 import (
            build_continuity_contracts,
        )

        cc = build_continuity_contracts()
        self.assertEqual(cc.contract_count, 5)
        self.assertEqual(cc.enforced_count, 0)
        self.assertFalse(cc.all_contracts_enforced)

    def test_full_contracts(self) -> None:
        from core.workstation.constitutional_substrate_governance_layer_v1 import (
            build_continuity_contracts,
        )
        from core.workstation.governed_recursive_orchestration_engine_v1 import (
            OrchestrationProof,
            OrchestrationEvidence,
        )
        from core.workstation.persistent_substrate_continuity_engine_v1 import (
            ContinuityProof,
            ContinuityEvidence,
        )
        from core.workstation.adaptive_governance_intelligence_engine_v1 import (
            GovernanceIntelligenceProof,
            GovernanceIntelligenceEvidence,
        )

        oev = OrchestrationEvidence(replay_validated=True, rollback_validated=True)
        cev = ContinuityEvidence(execution_lineage_present=True, drift_analysis_completed=True)
        gev = GovernanceIntelligenceEvidence(governance_ceilings_enforced=True)
        cc = build_continuity_contracts(
            OrchestrationProof(evidence=oev),
            ContinuityProof(evidence=cev),
            GovernanceIntelligenceProof(evidence=gev),
        )
        self.assertTrue(cc.all_contracts_enforced)
        self.assertEqual(cc.enforced_count, 5)


# ---------------------------------------------------------------------------
# Layer 4: Emergency governance
# ---------------------------------------------------------------------------


class TestBuildEmergencyGovernance(unittest.TestCase):
    def test_no_inputs(self) -> None:
        from core.workstation.constitutional_substrate_governance_layer_v1 import (
            build_emergency_governance,
        )

        eg = build_emergency_governance()
        self.assertEqual(eg.emergency_action_count, 6)
        self.assertEqual(eg.available_count, 0)
        self.assertFalse(eg.all_emergency_actions_available)

    def test_full_emergency(self) -> None:
        from core.workstation.constitutional_substrate_governance_layer_v1 import (
            build_emergency_governance,
        )
        from core.workstation.governed_recursive_orchestration_engine_v1 import (
            OrchestrationProof,
            OrchestrationEvidence,
        )
        from core.workstation.persistent_substrate_continuity_engine_v1 import (
            ContinuityProof,
        )
        from core.workstation.adaptive_governance_intelligence_engine_v1 import (
            GovernanceIntelligenceProof,
        )

        oev = OrchestrationEvidence(rollback_validated=True)
        eg = build_emergency_governance(
            OrchestrationProof(evidence=oev),
            ContinuityProof(),
            GovernanceIntelligenceProof(),
            founder_confirmed=True,
        )
        self.assertTrue(eg.all_emergency_actions_available)
        self.assertEqual(eg.available_count, 6)


# ---------------------------------------------------------------------------
# Constitutional integrity validation
# ---------------------------------------------------------------------------


class TestValidateIntegrity(unittest.TestCase):
    def test_no_inputs(self) -> None:
        from core.workstation.constitutional_substrate_governance_layer_v1 import (
            validate_constitutional_integrity,
        )

        ir = validate_constitutional_integrity()
        self.assertEqual(ir.check_count, 7)
        self.assertEqual(ir.passed_count, 0)
        self.assertFalse(ir.all_integrity_checks_pass)

    def test_full_integrity(self) -> None:
        from core.workstation.constitutional_substrate_governance_layer_v1 import (
            validate_constitutional_integrity,
        )
        from core.workstation.governed_recursive_orchestration_engine_v1 import (
            OrchestrationProof,
            OrchestrationEvidence,
        )
        from core.workstation.persistent_substrate_continuity_engine_v1 import (
            ContinuityProof,
            ContinuityEvidence,
        )
        from core.workstation.adaptive_governance_intelligence_engine_v1 import (
            GovernanceIntelligenceProof,
            GovernanceIntelligenceEvidence,
        )

        oev = OrchestrationEvidence(
            replay_validated=True,
            rollback_validated=True,
            governance_validated=True,
            sequencing_validated=True,
        )
        cev = ContinuityEvidence(execution_lineage_present=True, drift_analysis_completed=True)
        gev = GovernanceIntelligenceEvidence(governance_ceilings_enforced=True)
        ir = validate_constitutional_integrity(
            OrchestrationProof(evidence=oev),
            ContinuityProof(evidence=cev),
            GovernanceIntelligenceProof(evidence=gev),
        )
        self.assertTrue(ir.all_integrity_checks_pass)
        self.assertEqual(ir.passed_count, 7)


# ---------------------------------------------------------------------------
# Mutation classification
# ---------------------------------------------------------------------------


class TestClassifyMutation(unittest.TestCase):
    def test_safe_mutation(self) -> None:
        from core.workstation.constitutional_substrate_governance_layer_v1 import (
            classify_mutation,
        )

        mc = classify_mutation()
        self.assertEqual(mc.classification, "safe_mutation")
        self.assertFalse(mc.requires_founder_approval)
        self.assertFalse(mc.requires_migration)

    def test_constitutional_impact(self) -> None:
        from core.workstation.constitutional_substrate_governance_layer_v1 import (
            classify_mutation,
        )

        mc = classify_mutation(affects_invariants=True)
        self.assertEqual(mc.classification, "constitutional_impact_mutation")
        self.assertTrue(mc.requires_founder_approval)
        self.assertTrue(mc.requires_migration)

    def test_governance_mutation(self) -> None:
        from core.workstation.constitutional_substrate_governance_layer_v1 import (
            classify_mutation,
        )

        mc = classify_mutation(affects_governance=True)
        self.assertEqual(mc.classification, "governance_mutation")
        self.assertTrue(mc.requires_founder_approval)

    def test_replay_risk(self) -> None:
        from core.workstation.constitutional_substrate_governance_layer_v1 import (
            classify_mutation,
        )

        mc = classify_mutation(affects_replay=True)
        self.assertEqual(mc.classification, "replay_risk_mutation")
        self.assertTrue(mc.requires_founder_approval)

    def test_continuity_risk(self) -> None:
        from core.workstation.constitutional_substrate_governance_layer_v1 import (
            classify_mutation,
        )

        mc = classify_mutation(affects_continuity=True)
        self.assertEqual(mc.classification, "continuity_risk_mutation")

    def test_topology_risk(self) -> None:
        from core.workstation.constitutional_substrate_governance_layer_v1 import (
            classify_mutation,
        )

        mc = classify_mutation(affects_topology=True)
        self.assertEqual(mc.classification, "topology_risk_mutation")

    def test_mutation_id_generated(self) -> None:
        from core.workstation.constitutional_substrate_governance_layer_v1 import (
            classify_mutation,
        )

        mc = classify_mutation()
        self.assertTrue(mc.mutation_id.startswith("MUT-"))

    def test_constitutional_overrides_governance(self) -> None:
        from core.workstation.constitutional_substrate_governance_layer_v1 import (
            classify_mutation,
        )

        mc = classify_mutation(affects_invariants=True, affects_governance=True)
        self.assertEqual(mc.classification, "constitutional_impact_mutation")


# ---------------------------------------------------------------------------
# Constitutional risk scoring
# ---------------------------------------------------------------------------


class TestConstitutionalRiskScoring(unittest.TestCase):
    def test_no_inputs(self) -> None:
        from core.workstation.constitutional_substrate_governance_layer_v1 import (
            compute_constitutional_risk,
        )

        r = compute_constitutional_risk()
        self.assertEqual(r.composite_risk(), 0.0)

    def test_with_safety_invariants(self) -> None:
        from core.workstation.constitutional_substrate_governance_layer_v1 import (
            compute_constitutional_risk,
            ConstitutionalSafetyInvariantStatus,
        )

        si = ConstitutionalSafetyInvariantStatus(invariant_count=6, active_count=3)
        r = compute_constitutional_risk(safety_invariants=si)
        self.assertGreater(r.constitutional_fragility, 0)
        self.assertGreater(r.invariant_pressure, 0)

    def test_all_dimensions_scored(self) -> None:
        from core.workstation.constitutional_substrate_governance_layer_v1 import (
            compute_constitutional_risk,
            ConstitutionalRiskScores,
        )

        r = ConstitutionalRiskScores(
            constitutional_fragility=0.5,
            invariant_pressure=0.4,
            authority_drift=0.3,
            governance_instability=0.2,
            replay_instability=0.1,
            continuity_instability=0.15,
            recursive_entropy_pressure=0.25,
        )
        d = r.to_dict()
        self.assertEqual(len(d), 8)
        self.assertGreater(r.composite_risk(), 0)


# ---------------------------------------------------------------------------
# Governance contract builder
# ---------------------------------------------------------------------------


class TestBuildGovernanceContracts(unittest.TestCase):
    def test_no_proposals(self) -> None:
        from core.workstation.constitutional_substrate_governance_layer_v1 import (
            build_governance_contracts,
        )

        contracts = build_governance_contracts()
        self.assertEqual(len(contracts), 0)

    def test_with_proposals(self) -> None:
        from core.workstation.constitutional_substrate_governance_layer_v1 import (
            build_governance_contracts,
            ConstitutionalSafetyInvariantStatus,
            ConstitutionalAuthorityBoundaryStatus,
            ConstitutionalIntegrityResult,
        )
        from core.workstation.adaptive_governance_intelligence_engine_v1 import (
            GovernanceProposal,
        )

        proposals = [GovernanceProposal(proposal_type="test", proposal_id="P1")]
        si = ConstitutionalSafetyInvariantStatus(all_invariants_active=True)
        ab = ConstitutionalAuthorityBoundaryStatus(all_boundaries_enforced=True)
        ir = ConstitutionalIntegrityResult(all_integrity_checks_pass=True)
        contracts = build_governance_contracts(proposals, si, ab, ir)
        self.assertEqual(len(contracts), 1)
        self.assertTrue(contracts[0].approved)

    def test_incompatible_proposal(self) -> None:
        from core.workstation.constitutional_substrate_governance_layer_v1 import (
            build_governance_contracts,
            ConstitutionalSafetyInvariantStatus,
        )
        from core.workstation.adaptive_governance_intelligence_engine_v1 import (
            GovernanceProposal,
        )

        proposals = [
            GovernanceProposal(
                proposal_type="test",
                proposal_id="P2",
                replay_impact="unsafe replay risk",
            )
        ]
        si = ConstitutionalSafetyInvariantStatus(all_invariants_active=False)
        contracts = build_governance_contracts(proposals, si)
        self.assertEqual(len(contracts), 1)
        self.assertFalse(contracts[0].approved)
        self.assertIn("incompatib", contracts[0].replay_compatibility)

    def test_contract_has_impact_analysis(self) -> None:
        from core.workstation.constitutional_substrate_governance_layer_v1 import (
            build_governance_contracts,
        )
        from core.workstation.adaptive_governance_intelligence_engine_v1 import (
            GovernanceProposal,
        )

        proposals = [GovernanceProposal(proposal_type="x", proposal_id="P3")]
        contracts = build_governance_contracts(proposals)
        self.assertIn("Proposal x", contracts[0].constitutional_impact_analysis)


# ---------------------------------------------------------------------------
# Hard ceiling enforcement
# ---------------------------------------------------------------------------


class TestEnforceHardCeilings(unittest.TestCase):
    def test_no_inputs(self) -> None:
        from core.workstation.constitutional_substrate_governance_layer_v1 import (
            enforce_hard_ceilings,
        )

        blocked, reasons = enforce_hard_ceilings()
        self.assertFalse(blocked)
        self.assertEqual(len(reasons), 0)

    def test_replay_risk_blocked(self) -> None:
        from core.workstation.constitutional_substrate_governance_layer_v1 import (
            enforce_hard_ceilings,
            ConstitutionalMutationClassification,
        )

        mc = ConstitutionalMutationClassification(replay_risk=True)
        blocked, reasons = enforce_hard_ceilings(mutation=mc)
        self.assertTrue(blocked)
        self.assertTrue(any("replay_breaking" in r for r in reasons))

    def test_continuity_risk_blocked(self) -> None:
        from core.workstation.constitutional_substrate_governance_layer_v1 import (
            enforce_hard_ceilings,
            ConstitutionalMutationClassification,
        )

        mc = ConstitutionalMutationClassification(continuity_risk=True)
        blocked, reasons = enforce_hard_ceilings(mutation=mc)
        self.assertTrue(blocked)
        self.assertTrue(any("continuity_breaking" in r for r in reasons))

    def test_governance_bypass_blocked(self) -> None:
        from core.workstation.constitutional_substrate_governance_layer_v1 import (
            enforce_hard_ceilings,
        )
        from core.workstation.adaptive_governance_intelligence_engine_v1 import (
            GovernanceIntelligenceProof,
            GovernanceIntelligenceEvidence,
        )

        gev = GovernanceIntelligenceEvidence(
            autonomous_mutation_blocked=False, governance_ceilings_enforced=False
        )
        blocked, reasons = enforce_hard_ceilings(
            governance_proof=GovernanceIntelligenceProof(evidence=gev)
        )
        self.assertTrue(blocked)
        self.assertGreater(len(reasons), 0)

    def test_invariant_violation_blocked(self) -> None:
        from core.workstation.constitutional_substrate_governance_layer_v1 import (
            enforce_hard_ceilings,
            ConstitutionalMutationClassification,
        )

        mc = ConstitutionalMutationClassification(
            constitutional_impact=True, requires_migration=False
        )
        blocked, reasons = enforce_hard_ceilings(mutation=mc)
        self.assertTrue(blocked)
        self.assertTrue(any("invariant_violation" in r for r in reasons))


# ---------------------------------------------------------------------------
# Constitutional simulation engine
# ---------------------------------------------------------------------------


class TestConstitutionalSimulations(unittest.TestCase):
    def test_all_8_types(self) -> None:
        from core.workstation.constitutional_substrate_governance_layer_v1 import (
            run_constitutional_simulations,
            CONSTITUTIONAL_SIMULATION_TYPES,
        )

        sims = run_constitutional_simulations()
        self.assertEqual(len(sims), 8)
        sim_types = {s.simulation_type for s in sims}
        for st in CONSTITUTIONAL_SIMULATION_TYPES:
            self.assertIn(st, sim_types)

    def test_deterministic(self) -> None:
        from core.workstation.constitutional_substrate_governance_layer_v1 import (
            run_constitutional_simulations,
            ConstitutionalRiskScores,
        )

        risk = ConstitutionalRiskScores(constitutional_fragility=0.5, invariant_pressure=0.3)
        s1 = run_constitutional_simulations(constitutional_risk=risk)
        s2 = run_constitutional_simulations(constitutional_risk=risk)
        for a, b in zip(s1, s2):
            self.assertEqual(a.simulation_type, b.simulation_type)
            self.assertEqual(a.invariants_violated, b.invariants_violated)
            self.assertEqual(a.cascading_failures, b.cascading_failures)

    def test_simulation_has_severity(self) -> None:
        from core.workstation.constitutional_substrate_governance_layer_v1 import (
            run_constitutional_simulations,
        )

        sims = run_constitutional_simulations()
        for s in sims:
            self.assertIn(s.predicted_severity, ("low", "medium", "high", "critical"))

    def test_simulation_ids_unique(self) -> None:
        from core.workstation.constitutional_substrate_governance_layer_v1 import (
            run_constitutional_simulations,
        )

        sims = run_constitutional_simulations()
        ids = [s.simulation_id for s in sims]
        self.assertEqual(len(ids), len(set(ids)))


# ---------------------------------------------------------------------------
# Constitutional migration contracts
# ---------------------------------------------------------------------------


class TestMigrationContracts(unittest.TestCase):
    def test_no_inputs(self) -> None:
        from core.workstation.constitutional_substrate_governance_layer_v1 import (
            build_migration_contract,
        )

        mc = build_migration_contract()
        self.assertFalse(mc.all_requirements_met)
        self.assertEqual(mc.requirement_count, 6)

    def test_full_migration(self) -> None:
        from core.workstation.constitutional_substrate_governance_layer_v1 import (
            build_migration_contract,
        )

        mc = build_migration_contract(
            founder_approved=True,
            replay_validated=True,
            rollback_validated=True,
            continuity_validated=True,
            governance_lineage_present=True,
        )
        self.assertTrue(mc.all_requirements_met)
        self.assertTrue(mc.migration_proof_generated)
        self.assertEqual(mc.met_count, 6)

    def test_partial_migration(self) -> None:
        from core.workstation.constitutional_substrate_governance_layer_v1 import (
            build_migration_contract,
        )

        mc = build_migration_contract(founder_approved=True, replay_validated=True)
        self.assertFalse(mc.all_requirements_met)
        self.assertFalse(mc.migration_proof_generated)


# ---------------------------------------------------------------------------
# Maturity classification + ceilings
# ---------------------------------------------------------------------------


class TestComputeMaturity(unittest.TestCase):
    def test_l0(self) -> None:
        from core.workstation.constitutional_substrate_governance_layer_v1 import (
            compute_constitutional_maturity,
            ConstitutionalEvidence,
        )

        ev = ConstitutionalEvidence(
            hard_ceilings_enforced=False,
            autonomous_mutation_blocked=False,
            governance_bypass_blocked=False,
        )
        self.assertEqual(compute_constitutional_maturity(ev), 0)

    def test_l5(self) -> None:
        from core.workstation.constitutional_substrate_governance_layer_v1 import (
            compute_constitutional_maturity,
            ConstitutionalEvidence,
        )

        ev = ConstitutionalEvidence(
            safety_invariants_analyzed=True,
            safety_invariants_active=6,
            authority_boundaries_analyzed=True,
            authority_boundaries_enforced=5,
            continuity_contracts_analyzed=True,
            continuity_contracts_enforced=5,
            emergency_governance_analyzed=True,
            emergency_actions_available=6,
            integrity_validated=True,
            integrity_checks_passed=7,
            constitutional_risk_scored=True,
            simulations_completed=True,
            founder_confirmed=True,
            hard_ceilings_enforced=True,
            autonomous_mutation_blocked=True,
            governance_bypass_blocked=True,
        )
        self.assertGreaterEqual(compute_constitutional_maturity(ev), 10)


class TestMaturityCeiling(unittest.TestCase):
    def test_dry_run(self) -> None:
        from core.workstation.constitutional_substrate_governance_layer_v1 import (
            constitutional_maturity_ceiling,
            ConstitutionalEvidence,
        )

        ev = ConstitutionalEvidence(is_dry_run=True)
        ceiling, blocked, reason = constitutional_maturity_ceiling(ev)
        self.assertEqual(ceiling, "L0_NO_CONSTITUTIONAL_GOVERNANCE")
        self.assertTrue(blocked)

    def test_no_safety(self) -> None:
        from core.workstation.constitutional_substrate_governance_layer_v1 import (
            constitutional_maturity_ceiling,
            ConstitutionalEvidence,
        )

        ev = ConstitutionalEvidence(safety_invariants_analyzed=False)
        ceiling, blocked, _ = constitutional_maturity_ceiling(ev)
        self.assertEqual(ceiling, "L0_NO_CONSTITUTIONAL_GOVERNANCE")
        self.assertTrue(blocked)

    def test_no_authority(self) -> None:
        from core.workstation.constitutional_substrate_governance_layer_v1 import (
            constitutional_maturity_ceiling,
            ConstitutionalEvidence,
        )

        ev = ConstitutionalEvidence(
            safety_invariants_analyzed=True, authority_boundaries_analyzed=False
        )
        ceiling, blocked, _ = constitutional_maturity_ceiling(ev)
        self.assertEqual(ceiling, "L1_INVARIANT_DEFINED")
        self.assertTrue(blocked)

    def test_no_continuity(self) -> None:
        from core.workstation.constitutional_substrate_governance_layer_v1 import (
            constitutional_maturity_ceiling,
            ConstitutionalEvidence,
        )

        ev = ConstitutionalEvidence(
            safety_invariants_analyzed=True,
            authority_boundaries_analyzed=True,
            continuity_contracts_analyzed=False,
        )
        ceiling, blocked, _ = constitutional_maturity_ceiling(ev)
        self.assertEqual(ceiling, "L2_AUTHORITY_BOUNDED")
        self.assertTrue(blocked)

    def test_no_integrity(self) -> None:
        from core.workstation.constitutional_substrate_governance_layer_v1 import (
            constitutional_maturity_ceiling,
            ConstitutionalEvidence,
        )

        ev = ConstitutionalEvidence(
            safety_invariants_analyzed=True,
            authority_boundaries_analyzed=True,
            continuity_contracts_analyzed=True,
            emergency_governance_analyzed=True,
            integrity_validated=False,
        )
        ceiling, blocked, _ = constitutional_maturity_ceiling(ev)
        self.assertEqual(ceiling, "L3_CONTINUITY_CONTRACTED")
        self.assertTrue(blocked)

    def test_no_simulations(self) -> None:
        from core.workstation.constitutional_substrate_governance_layer_v1 import (
            constitutional_maturity_ceiling,
            ConstitutionalEvidence,
        )

        ev = ConstitutionalEvidence(
            safety_invariants_analyzed=True,
            authority_boundaries_analyzed=True,
            continuity_contracts_analyzed=True,
            emergency_governance_analyzed=True,
            integrity_validated=True,
            constitutional_risk_scored=True,
            simulations_completed=False,
        )
        ceiling, blocked, _ = constitutional_maturity_ceiling(ev)
        self.assertEqual(ceiling, "L4_EMERGENCY_GOVERNED")
        self.assertTrue(blocked)

    def test_no_founder(self) -> None:
        from core.workstation.constitutional_substrate_governance_layer_v1 import (
            constitutional_maturity_ceiling,
            ConstitutionalEvidence,
        )

        ev = ConstitutionalEvidence(
            safety_invariants_analyzed=True,
            authority_boundaries_analyzed=True,
            continuity_contracts_analyzed=True,
            emergency_governance_analyzed=True,
            integrity_validated=True,
            constitutional_risk_scored=True,
            simulations_completed=True,
            hard_ceilings_enforced=True,
            founder_confirmed=False,
        )
        ceiling, blocked, _ = constitutional_maturity_ceiling(ev)
        self.assertEqual(ceiling, "L4_EMERGENCY_GOVERNED")
        self.assertTrue(blocked)

    def test_full_l5(self) -> None:
        from core.workstation.constitutional_substrate_governance_layer_v1 import (
            constitutional_maturity_ceiling,
            ConstitutionalEvidence,
        )

        ev = ConstitutionalEvidence(
            safety_invariants_analyzed=True,
            authority_boundaries_analyzed=True,
            continuity_contracts_analyzed=True,
            emergency_governance_analyzed=True,
            integrity_validated=True,
            constitutional_risk_scored=True,
            simulations_completed=True,
            hard_ceilings_enforced=True,
            founder_confirmed=True,
            governance_bypass_blocked=True,
        )
        ceiling, blocked, _ = constitutional_maturity_ceiling(ev)
        self.assertEqual(ceiling, "L5_CONSTITUTIONAL_RECURSIVE_GOVERNANCE")
        self.assertFalse(blocked)


class TestClassifyMaturity(unittest.TestCase):
    def test_dry_run(self) -> None:
        from core.workstation.constitutional_substrate_governance_layer_v1 import (
            classify_constitutional_maturity,
            ConstitutionalEvidence,
        )

        ev = ConstitutionalEvidence(is_dry_run=True)
        level, ceiling, blocked, reason = classify_constitutional_maturity(ev)
        self.assertEqual(level, "L0_NO_CONSTITUTIONAL_GOVERNANCE")
        self.assertTrue(blocked)

    def test_full_l5(self) -> None:
        from core.workstation.constitutional_substrate_governance_layer_v1 import (
            classify_constitutional_maturity,
            ConstitutionalEvidence,
        )

        ev = ConstitutionalEvidence(
            safety_invariants_analyzed=True,
            safety_invariants_active=6,
            authority_boundaries_analyzed=True,
            authority_boundaries_enforced=5,
            continuity_contracts_analyzed=True,
            continuity_contracts_enforced=5,
            emergency_governance_analyzed=True,
            emergency_actions_available=6,
            integrity_validated=True,
            integrity_checks_passed=7,
            integrity_check_count=7,
            constitutional_risk_scored=True,
            simulations_completed=True,
            hard_ceilings_enforced=True,
            autonomous_mutation_blocked=True,
            governance_bypass_blocked=True,
            founder_confirmed=True,
        )
        level, ceiling, blocked, reason = classify_constitutional_maturity(ev)
        self.assertEqual(level, "L5_CONSTITUTIONAL_RECURSIVE_GOVERNANCE")
        self.assertFalse(blocked)


# ---------------------------------------------------------------------------
# Full pipeline
# ---------------------------------------------------------------------------


class TestFullPipeline(unittest.TestCase):
    def test_no_inputs(self) -> None:
        from core.workstation.constitutional_substrate_governance_layer_v1 import (
            build_full_constitutional_proof,
        )

        proof = build_full_constitutional_proof()
        self.assertIsNotNone(proof.evidence)
        self.assertIsNotNone(proof.safety_invariants)
        self.assertIsNotNone(proof.authority_boundaries)
        self.assertIsNotNone(proof.continuity_contracts)
        self.assertIsNotNone(proof.emergency_governance)
        self.assertIsNotNone(proof.integrity_result)
        self.assertIsNotNone(proof.constitutional_risk)

    def test_strategy_simulation(self) -> None:
        from core.workstation.constitutional_substrate_governance_layer_v1 import (
            build_full_constitutional_proof,
        )

        proof = build_full_constitutional_proof(is_dry_run=True)
        self.assertEqual(proof.execution_strategy, "simulation_only")

    def test_strategy_await_founder(self) -> None:
        from core.workstation.constitutional_substrate_governance_layer_v1 import (
            build_full_constitutional_proof,
        )

        proof = build_full_constitutional_proof(founder_confirmed=False)
        self.assertEqual(proof.execution_strategy, "await_founder_confirmation")

    def test_strategy_active(self) -> None:
        from core.workstation.constitutional_substrate_governance_layer_v1 import (
            build_full_constitutional_proof,
        )

        proof = build_full_constitutional_proof(founder_confirmed=True)
        self.assertEqual(proof.execution_strategy, "constitutional_governance_active")

    def test_simulations_present(self) -> None:
        from core.workstation.constitutional_substrate_governance_layer_v1 import (
            build_full_constitutional_proof,
        )

        proof = build_full_constitutional_proof()
        self.assertEqual(len(proof.simulations), 8)

    def test_to_dict_complete(self) -> None:
        from core.workstation.constitutional_substrate_governance_layer_v1 import (
            build_full_constitutional_proof,
        )

        proof = build_full_constitutional_proof(founder_confirmed=True)
        d = proof.to_dict()
        self.assertEqual(d["proof_type"], "constitutional_substrate_governance")
        self.assertIn("safety_invariants", d)
        self.assertIn("authority_boundaries", d)
        self.assertIn("continuity_contracts", d)
        self.assertIn("emergency_governance", d)
        self.assertIn("integrity_result", d)
        self.assertIn("constitutional_risk", d)
        self.assertIn("simulations", d)

    def test_with_proofs(self) -> None:
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

        orch = build_full_orchestration_proof(founder_confirmed=True)
        cont = build_full_continuity_proof(orchestration_proof=orch, founder_confirmed=True)
        gov = build_full_governance_intelligence_proof(
            orchestration_proof=orch, continuity_proof=cont, founder_confirmed=True
        )
        proof = build_full_constitutional_proof(
            orchestration_proof=orch,
            continuity_proof=cont,
            governance_proof=gov,
            founder_confirmed=True,
        )
        self.assertEqual(proof.maturity_level, "L5_CONSTITUTIONAL_RECURSIVE_GOVERNANCE")
        self.assertTrue(proof.safety_invariants.all_invariants_active)
        self.assertTrue(proof.authority_boundaries.all_boundaries_enforced)


# ---------------------------------------------------------------------------
# Proof persistence
# ---------------------------------------------------------------------------


class TestProofPersistence(unittest.TestCase):
    def test_persist(self) -> None:
        from core.workstation.constitutional_substrate_governance_layer_v1 import (
            build_full_constitutional_proof,
            persist_constitutional_proof,
        )

        proof = build_full_constitutional_proof(trace_id="persist-test")
        path = persist_constitutional_proof(proof, base_dir=Path("/tmp/const_test"))
        self.assertTrue(path.exists())
        path.unlink()
        path.parent.rmdir()

    def test_persist_valid_json(self) -> None:
        from core.workstation.constitutional_substrate_governance_layer_v1 import (
            build_full_constitutional_proof,
            persist_constitutional_proof,
        )

        proof = build_full_constitutional_proof(trace_id="json-test")
        path = persist_constitutional_proof(proof, base_dir=Path("/tmp/const_json"))
        data = json.loads(path.read_text())
        self.assertEqual(data["proof_type"], "constitutional_substrate_governance")
        path.unlink()
        path.parent.rmdir()

    def test_persist_creates_dir(self) -> None:
        import shutil

        from core.workstation.constitutional_substrate_governance_layer_v1 import (
            build_full_constitutional_proof,
            persist_constitutional_proof,
            CONSTITUTIONAL_REPORT_DIR,
        )

        base = Path("/tmp/const_dir_test")
        if base.exists():
            shutil.rmtree(base)
        proof = build_full_constitutional_proof(trace_id="dir-test")
        path = persist_constitutional_proof(proof, base_dir=base)
        self.assertTrue(path.exists())
        shutil.rmtree(base)

    def test_persist_full_pipeline(self) -> None:
        from core.workstation.constitutional_substrate_governance_layer_v1 import (
            build_full_constitutional_proof,
            persist_constitutional_proof,
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

        orch = build_full_orchestration_proof(founder_confirmed=True)
        cont = build_full_continuity_proof(orchestration_proof=orch, founder_confirmed=True)
        gov = build_full_governance_intelligence_proof(
            orchestration_proof=orch, continuity_proof=cont, founder_confirmed=True
        )
        proof = build_full_constitutional_proof(
            orchestration_proof=orch,
            continuity_proof=cont,
            governance_proof=gov,
            founder_confirmed=True,
            trace_id="full-persist",
        )
        import shutil

        base = Path("/tmp/const_full")
        path = persist_constitutional_proof(proof, base_dir=base)
        data = json.loads(path.read_text())
        self.assertEqual(data["maturity_level"], "L5_CONSTITUTIONAL_RECURSIVE_GOVERNANCE")
        shutil.rmtree(base)


# ---------------------------------------------------------------------------
# Canonical instance separation
# ---------------------------------------------------------------------------


class TestCanonicalInstanceSeparation(unittest.TestCase):
    def test_independent_proofs(self) -> None:
        from core.workstation.constitutional_substrate_governance_layer_v1 import (
            build_full_constitutional_proof,
        )

        p1 = build_full_constitutional_proof(trace_id="inst-1")
        p2 = build_full_constitutional_proof(trace_id="inst-2")
        self.assertNotEqual(p1.proof_id, p2.proof_id)
        self.assertNotEqual(p1.trace_id, p2.trace_id)

    def test_founder_vs_no_founder(self) -> None:
        from core.workstation.constitutional_substrate_governance_layer_v1 import (
            build_full_constitutional_proof,
        )

        p_no = build_full_constitutional_proof(founder_confirmed=False)
        p_yes = build_full_constitutional_proof(founder_confirmed=True)
        self.assertNotEqual(p_no.execution_strategy, p_yes.execution_strategy)


# ---------------------------------------------------------------------------
# Registry integration (20 commands, parity checks)
# ---------------------------------------------------------------------------


class TestRegistryIntegration(unittest.TestCase):
    def test_registry_count_is_20(self) -> None:
        from composition.registries.canonical_command_registry_v1 import get_canonical_registry

        reg = get_canonical_registry()
        self.assertEqual(len(reg), 27)

    def test_constitution_report_in_registry(self) -> None:
        from composition.registries.canonical_command_registry_v1 import get_canonical_registry

        reg = get_canonical_registry()
        self.assertIn("!constitution-report", reg.commands)

    def test_constitution_report_action(self) -> None:
        from composition.registries.canonical_command_registry_v1 import get_canonical_registry

        reg = get_canonical_registry()
        self.assertIn("constitution_report", reg.actions)

    def test_router_contracts(self) -> None:
        from control_plane.router.router_contracts import (
            ALLOWED_ACTION_TYPES,
            CapabilityType,
        )

        self.assertIn("constitution_report", ALLOWED_ACTION_TYPES)
        self.assertEqual(
            CapabilityType.CONSTITUTIONAL_GOVERNANCE.value,
            "constitutional_governance",
        )

    def test_router_action_map(self) -> None:
        from control_plane.router.control_plane_router_v1 import (
            ACTION_CAPABILITY_MAP,
        )

        self.assertIn("constitution_report", ACTION_CAPABILITY_MAP)

    def test_adapter_contracts_enum(self) -> None:
        from execution.environments.windows_desktop_adapter_contracts import (
            WindowsDesktopActionType,
        )

        self.assertEqual(
            WindowsDesktopActionType.CONSTITUTION_REPORT.value,
            "constitution_report",
        )

    def test_config_json(self) -> None:
        config = json.loads((Path(_ROOT) / "config" / "control_plane_router_v1.json").read_text())
        self.assertIn("constitution_report", config["allowed_action_types"])

    def test_config_action_count(self) -> None:
        config = json.loads((Path(_ROOT) / "config" / "control_plane_router_v1.json").read_text())
        self.assertEqual(len(config["allowed_action_types"]), 27)

    def test_adapter_registry_workers(self) -> None:
        reg = json.loads(
            (Path(_ROOT) / "data" / "registries" / "local_worker_adapter_registry_v1.json").read_text()
        )
        wsl = reg["workers"]["local_wsl_worker"]["capabilities"]
        win = reg["workers"]["windows_interactive_desktop_relay"]["capabilities"]
        self.assertIn("constitution_report", wsl)
        self.assertIn("constitution_report", win)

    def test_adapter_registry_capability_entry(self) -> None:
        reg = json.loads(
            (Path(_ROOT) / "data" / "registries" / "local_worker_adapter_registry_v1.json").read_text()
        )
        caps = reg["adapters"]["windows_interactive_desktop_relay"]["capabilities"]
        cap_ids = [c["capability_id"] for c in caps]
        self.assertIn("constitution_report", cap_ids)

    def test_allowed_action_types_count(self) -> None:
        from control_plane.router.router_contracts import ALLOWED_ACTION_TYPES

        self.assertEqual(len(ALLOWED_ACTION_TYPES), 27)

    def test_const_report_in_handler(self) -> None:
        from handlers.substrate_command_handler import SUBSTRATE_COMMANDS

        self.assertIn("!constitution-report", SUBSTRATE_COMMANDS)
        self.assertEqual(len(SUBSTRATE_COMMANDS), 27)


if __name__ == "__main__":
    unittest.main()
