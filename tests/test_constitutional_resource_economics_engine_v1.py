"""Tests for Phase 96.8BB — Constitutional Resource Economics and Coordination.

Verifies:
  1.  Constants — correct counts and types
  2.  NodeResourceProfile — capacity scoring, to_dict
  3.  FederationResourceGraph — aggregation, bottleneck/hotspot detection
  4.  ExecutionEconomicsScores — composite scoring, all 8 dimensions
  5.  DelegationPath — delegation scoring, safe/unsafe
  6.  DelegationTopology — path aggregation, trust averaging
  7.  DegradedModeStatus — readiness tracking, active mode detection
  8.  ScarcitySimulationOutcome — ID generation, 8 types
  9.  EconomicsEvidence — 28 fields, to_dict
  10. EconomicsProof — proof ID generation, to_dict
  11. build_resource_graph — from federation proof, default node
  12. compute_execution_economics — from resource graph
  13. build_delegation_topology — safe/unsafe classification
  14. build_degraded_mode_status — founder-dependent quarantine
  15. enforce_economics_hard_ceilings — ceiling triggers
  16. run_scarcity_simulations — all 8 types
  17. compute_economics_maturity — score accumulation
  18. economics_maturity_ceiling — ceiling classification
  19. classify_economics_maturity — level clamped by ceiling
  20. build_full_economics_proof — full pipeline no federation
  21. build_full_economics_proof — full pipeline with federation
  22. persist_economics_proof — file written, JSON valid
  23. Maturity L5 requires founder confirmation
  24. Hard ceilings block escalation
  25. Command registration — 22 commands, !economics-report present
  26. Router config parity — all actions in config
  27. Substrate handler — !economics-report in SUBSTRATE_COMMANDS
  28. Proof chain — capability→orch→cont→gov→const→fed→economics
"""

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, "/opt/OS")
sys.path.insert(0, "/opt/OS/services")


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------


class TestEconomicsConstants:
    def test_maturity_levels_count(self) -> None:
        from core.workstation.constitutional_resource_economics_engine_v1 import (
            ECONOMICS_MATURITY_LEVELS,
        )

        assert len(ECONOMICS_MATURITY_LEVELS) == 6

    def test_maturity_levels_order(self) -> None:
        from core.workstation.constitutional_resource_economics_engine_v1 import (
            ECONOMICS_MATURITY_LEVELS,
        )

        assert ECONOMICS_MATURITY_LEVELS[0] == "L0_NO_RESOURCE_COORDINATION"
        assert ECONOMICS_MATURITY_LEVELS[5] == "L5_CONSTITUTIONAL_RESOURCE_COORDINATION"

    def test_resource_primitives_count(self) -> None:
        from core.workstation.constitutional_resource_economics_engine_v1 import (
            RESOURCE_PRIMITIVES,
        )

        assert len(RESOURCE_PRIMITIVES) == 9

    def test_execution_economics_dimensions_count(self) -> None:
        from core.workstation.constitutional_resource_economics_engine_v1 import (
            EXECUTION_ECONOMICS_DIMENSIONS,
        )

        assert len(EXECUTION_ECONOMICS_DIMENSIONS) == 8

    def test_constrained_node_types_count(self) -> None:
        from core.workstation.constitutional_resource_economics_engine_v1 import (
            CONSTRAINED_NODE_TYPES,
        )

        assert len(CONSTRAINED_NODE_TYPES) == 7

    def test_degraded_mode_types_count(self) -> None:
        from core.workstation.constitutional_resource_economics_engine_v1 import (
            DEGRADED_MODE_TYPES,
        )

        assert len(DEGRADED_MODE_TYPES) == 6

    def test_scarcity_simulation_types_count(self) -> None:
        from core.workstation.constitutional_resource_economics_engine_v1 import (
            SCARCITY_SIMULATION_TYPES,
        )

        assert len(SCARCITY_SIMULATION_TYPES) == 8

    def test_economics_hard_ceilings_count(self) -> None:
        from core.workstation.constitutional_resource_economics_engine_v1 import (
            ECONOMICS_HARD_CEILINGS,
        )

        assert len(ECONOMICS_HARD_CEILINGS) == 7
        assert isinstance(ECONOMICS_HARD_CEILINGS, frozenset)

    def test_resource_graph_dimensions_count(self) -> None:
        from core.workstation.constitutional_resource_economics_engine_v1 import (
            RESOURCE_GRAPH_DIMENSIONS,
        )

        assert len(RESOURCE_GRAPH_DIMENSIONS) == 7


# ---------------------------------------------------------------------------
# Dataclasses
# ---------------------------------------------------------------------------


class TestNodeResourceProfile:
    def test_default_capacity(self) -> None:
        from core.workstation.constitutional_resource_economics_engine_v1 import (
            NodeResourceProfile,
        )

        p = NodeResourceProfile()
        assert p.total_capacity() >= 0

    def test_full_capacity_node(self) -> None:
        from core.workstation.constitutional_resource_economics_engine_v1 import (
            NodeResourceProfile,
        )

        p = NodeResourceProfile(
            compute_capacity=1.0,
            orchestration_bandwidth=1.0,
            relay_availability=1.0,
            governance_overhead=0.0,
            coordination_latency=0.0,
        )
        assert p.total_capacity() == 1.0

    def test_to_dict_has_total_capacity(self) -> None:
        from core.workstation.constitutional_resource_economics_engine_v1 import (
            NodeResourceProfile,
        )

        p = NodeResourceProfile(node_id="test")
        d = p.to_dict()
        assert "total_capacity" in d
        assert d["node_id"] == "test"

    def test_degraded_flag(self) -> None:
        from core.workstation.constitutional_resource_economics_engine_v1 import (
            NodeResourceProfile,
        )

        p = NodeResourceProfile(degraded=True, constraint_type="low_capacity")
        assert p.degraded is True
        assert p.constraint_type == "low_capacity"


class TestFederationResourceGraph:
    def test_default_graph(self) -> None:
        from core.workstation.constitutional_resource_economics_engine_v1 import (
            FederationResourceGraph,
        )

        g = FederationResourceGraph()
        assert len(g.node_profiles) == 0
        assert g.total_compute == 0.0

    def test_to_dict_serializable(self) -> None:
        from core.workstation.constitutional_resource_economics_engine_v1 import (
            FederationResourceGraph,
        )

        g = FederationResourceGraph()
        d = g.to_dict()
        s = json.dumps(d)
        assert len(s) > 0

    def test_timestamp_auto_set(self) -> None:
        from core.workstation.constitutional_resource_economics_engine_v1 import (
            FederationResourceGraph,
        )

        g = FederationResourceGraph()
        assert len(g.timestamp) > 0


class TestExecutionEconomicsScores:
    def test_composite_economics(self) -> None:
        from core.workstation.constitutional_resource_economics_engine_v1 import (
            ExecutionEconomicsScores,
        )

        s = ExecutionEconomicsScores(
            execution_value=0.8,
            leverage_score=0.7,
            resource_efficiency=0.9,
            federation_stability_impact=0.6,
        )
        assert s.composite_economics() > 0

    def test_composite_negative_factors(self) -> None:
        from core.workstation.constitutional_resource_economics_engine_v1 import (
            ExecutionEconomicsScores,
        )

        s = ExecutionEconomicsScores(
            governance_risk=1.0,
            blast_radius=1.0,
            continuity_risk=1.0,
            replay_complexity=1.0,
        )
        assert s.composite_economics() < 0

    def test_to_dict_has_composite(self) -> None:
        from core.workstation.constitutional_resource_economics_engine_v1 import (
            ExecutionEconomicsScores,
        )

        s = ExecutionEconomicsScores()
        d = s.to_dict()
        assert "composite_economics" in d


class TestDelegationPath:
    def test_safe_delegation_score(self) -> None:
        from core.workstation.constitutional_resource_economics_engine_v1 import (
            DelegationPath,
        )

        p = DelegationPath(
            trust_weight=0.8,
            replay_integrity=0.7,
            continuity_integrity=0.6,
            governance_maturity=0.9,
            delegation_safe=True,
        )
        assert p.delegation_score() > 0

    def test_unsafe_delegation_score_zero(self) -> None:
        from core.workstation.constitutional_resource_economics_engine_v1 import (
            DelegationPath,
        )

        p = DelegationPath(delegation_safe=False, trust_weight=0.9)
        assert p.delegation_score() == 0.0

    def test_to_dict_has_delegation_score(self) -> None:
        from core.workstation.constitutional_resource_economics_engine_v1 import (
            DelegationPath,
        )

        p = DelegationPath()
        d = p.to_dict()
        assert "delegation_score" in d


class TestDelegationTopology:
    def test_default_topology(self) -> None:
        from core.workstation.constitutional_resource_economics_engine_v1 import (
            DelegationTopology,
        )

        t = DelegationTopology()
        assert len(t.paths) == 0
        assert t.safe_path_count == 0

    def test_to_dict_serializable(self) -> None:
        from core.workstation.constitutional_resource_economics_engine_v1 import (
            DelegationTopology,
        )

        t = DelegationTopology()
        d = t.to_dict()
        s = json.dumps(d)
        assert len(s) > 0


class TestDegradedModeStatus:
    def test_default_not_ready(self) -> None:
        from core.workstation.constitutional_resource_economics_engine_v1 import (
            DegradedModeStatus,
        )

        dm = DegradedModeStatus()
        assert dm.ready_count == 0
        assert dm.partial_federation_ready is False

    def test_to_dict_all_fields(self) -> None:
        from core.workstation.constitutional_resource_economics_engine_v1 import (
            DegradedModeStatus,
        )

        dm = DegradedModeStatus()
        d = dm.to_dict()
        assert "partial_federation_ready" in d
        assert "quarantine_execution_ready" in d


class TestScarcitySimulationOutcome:
    def test_auto_simulation_id(self) -> None:
        from core.workstation.constitutional_resource_economics_engine_v1 import (
            ScarcitySimulationOutcome,
        )

        s = ScarcitySimulationOutcome()
        assert s.simulation_id.startswith("SCARSIM-")

    def test_auto_timestamp(self) -> None:
        from core.workstation.constitutional_resource_economics_engine_v1 import (
            ScarcitySimulationOutcome,
        )

        s = ScarcitySimulationOutcome()
        assert len(s.timestamp) > 0

    def test_to_dict_serializable(self) -> None:
        from core.workstation.constitutional_resource_economics_engine_v1 import (
            ScarcitySimulationOutcome,
        )

        s = ScarcitySimulationOutcome(simulation_type="node_exhaustion")
        d = s.to_dict()
        assert d["simulation_type"] == "node_exhaustion"
        s2 = json.dumps(d)
        assert len(s2) > 0


class TestEconomicsEvidence:
    def test_field_count(self) -> None:
        from core.workstation.constitutional_resource_economics_engine_v1 import (
            EconomicsEvidence,
        )

        ev = EconomicsEvidence()
        d = ev.to_dict()
        assert len(d) == 28

    def test_to_dict_serializable(self) -> None:
        from core.workstation.constitutional_resource_economics_engine_v1 import (
            EconomicsEvidence,
        )

        ev = EconomicsEvidence(resource_graph_analyzed=True, node_count=3)
        s = json.dumps(ev.to_dict())
        assert len(s) > 0


class TestEconomicsProof:
    def test_auto_proof_id(self) -> None:
        from core.workstation.constitutional_resource_economics_engine_v1 import (
            EconomicsProof,
        )

        p = EconomicsProof(trace_id="test-trace")
        assert p.proof_id.startswith("ECON-")

    def test_auto_timestamp(self) -> None:
        from core.workstation.constitutional_resource_economics_engine_v1 import (
            EconomicsProof,
        )

        p = EconomicsProof()
        assert len(p.timestamp) > 0

    def test_to_dict_serializable(self) -> None:
        from core.workstation.constitutional_resource_economics_engine_v1 import (
            EconomicsProof,
        )

        p = EconomicsProof()
        d = p.to_dict()
        s = json.dumps(d, default=str)
        assert len(s) > 0
        assert d["proof_type"] == "constitutional_resource_economics"


# ---------------------------------------------------------------------------
# Builders
# ---------------------------------------------------------------------------


class TestBuildResourceGraph:
    def test_no_federation_creates_default_node(self) -> None:
        from core.workstation.constitutional_resource_economics_engine_v1 import (
            build_resource_graph,
        )

        g = build_resource_graph()
        assert len(g.node_profiles) == 1
        assert g.node_profiles[0].node_id == "primary-default"
        assert g.total_compute == 1.0

    def test_graph_hash_deterministic(self) -> None:
        from core.workstation.constitutional_resource_economics_engine_v1 import (
            build_resource_graph,
        )

        g1 = build_resource_graph()
        g2 = build_resource_graph()
        assert g1.graph_hash == g2.graph_hash
        assert len(g1.graph_hash) == 16

    def test_no_delegation_paths_for_single_node(self) -> None:
        from core.workstation.constitutional_resource_economics_engine_v1 import (
            build_resource_graph,
        )

        g = build_resource_graph()
        assert g.delegation_paths == 0

    def test_hotspot_detection(self) -> None:
        from core.workstation.constitutional_resource_economics_engine_v1 import (
            build_resource_graph,
        )

        g = build_resource_graph()
        assert g.hotspot_count >= 0

    def test_bottleneck_detection(self) -> None:
        from core.workstation.constitutional_resource_economics_engine_v1 import (
            build_resource_graph,
        )

        g = build_resource_graph()
        assert g.bottleneck_count >= 0


class TestComputeExecutionEconomics:
    def test_from_default_graph(self) -> None:
        from core.workstation.constitutional_resource_economics_engine_v1 import (
            build_resource_graph,
            compute_execution_economics,
        )

        g = build_resource_graph()
        e = compute_execution_economics(g)
        assert e.execution_value > 0
        assert e.resource_efficiency > 0

    def test_all_dimensions_set(self) -> None:
        from core.workstation.constitutional_resource_economics_engine_v1 import (
            build_resource_graph,
            compute_execution_economics,
        )

        g = build_resource_graph()
        e = compute_execution_economics(g)
        d = e.to_dict()
        assert len(d) == 9  # 8 dimensions + composite


class TestBuildDelegationTopology:
    def test_single_node_no_paths(self) -> None:
        from core.workstation.constitutional_resource_economics_engine_v1 import (
            build_delegation_topology,
            build_resource_graph,
        )

        g = build_resource_graph()
        t = build_delegation_topology(g)
        assert len(t.paths) == 0
        assert t.safe_path_count == 0

    def test_multi_node_has_paths(self) -> None:
        from core.workstation.constitutional_resource_economics_engine_v1 import (
            FederationResourceGraph,
            NodeResourceProfile,
            build_delegation_topology,
        )

        g = FederationResourceGraph(
            node_profiles=[
                NodeResourceProfile(node_id="a", trust_score=0.8),
                NodeResourceProfile(node_id="b", trust_score=0.9),
            ]
        )
        t = build_delegation_topology(g)
        assert len(t.paths) == 2
        assert t.safe_path_count + t.unsafe_path_count == 2

    def test_degraded_target_unsafe(self) -> None:
        from core.workstation.constitutional_resource_economics_engine_v1 import (
            FederationResourceGraph,
            NodeResourceProfile,
            build_delegation_topology,
        )

        g = FederationResourceGraph(
            node_profiles=[
                NodeResourceProfile(node_id="a", trust_score=0.8),
                NodeResourceProfile(node_id="b", trust_score=0.9, degraded=True),
            ]
        )
        t = build_delegation_topology(g)
        a_to_b = [p for p in t.paths if p.target_node_id == "b"]
        assert len(a_to_b) == 1
        assert a_to_b[0].delegation_safe is False


class TestBuildDegradedModeStatus:
    def test_no_proofs_partial_only(self) -> None:
        from core.workstation.constitutional_resource_economics_engine_v1 import (
            build_degraded_mode_status,
            build_resource_graph,
        )

        g = build_resource_graph()
        dm = build_degraded_mode_status(g)
        assert dm.partial_federation_ready is True
        assert dm.quarantine_execution_ready is False
        assert dm.ready_count >= 1

    def test_quarantine_requires_founder(self) -> None:
        from core.workstation.constitutional_resource_economics_engine_v1 import (
            build_degraded_mode_status,
            build_resource_graph,
        )
        from core.workstation.constitutional_substrate_governance_layer_v1 import (
            ConstitutionalProof,
        )
        from core.workstation.governed_recursive_orchestration_engine_v1 import (
            OrchestrationProof,
        )

        g = build_resource_graph()
        cp = ConstitutionalProof()
        op = OrchestrationProof()
        dm_no = build_degraded_mode_status(
            g, orchestration_proof=op, constitutional_proof=cp, founder_confirmed=False
        )
        assert dm_no.quarantine_execution_ready is False

        dm_yes = build_degraded_mode_status(
            g, orchestration_proof=op, constitutional_proof=cp, founder_confirmed=True
        )
        assert dm_yes.quarantine_execution_ready is True


class TestEnforceEconomicsHardCeilings:
    def test_no_violation_on_normal(self) -> None:
        from core.workstation.constitutional_resource_economics_engine_v1 import (
            DegradedModeStatus,
            DelegationTopology,
            ExecutionEconomicsScores,
            FederationResourceGraph,
            NodeResourceProfile,
            enforce_economics_hard_ceilings,
        )

        g = FederationResourceGraph(
            node_profiles=[NodeResourceProfile(compute_capacity=0.5, orchestration_bandwidth=0.5)]
        )
        e = ExecutionEconomicsScores(governance_risk=0.2, blast_radius=0.2, replay_complexity=0.2)
        t = DelegationTopology()
        dm = DegradedModeStatus()
        blocked, reasons = enforce_economics_hard_ceilings(g, e, t, dm)
        assert blocked is False

    def test_high_governance_risk_triggers_ceiling(self) -> None:
        from core.workstation.constitutional_resource_economics_engine_v1 import (
            DegradedModeStatus,
            DelegationTopology,
            ExecutionEconomicsScores,
            FederationResourceGraph,
            enforce_economics_hard_ceilings,
        )

        g = FederationResourceGraph()
        e = ExecutionEconomicsScores(governance_risk=0.9)
        t = DelegationTopology()
        dm = DegradedModeStatus()
        blocked, reasons = enforce_economics_hard_ceilings(g, e, t, dm)
        assert blocked is True
        assert any("governance_breaking" in r for r in reasons)

    def test_high_blast_radius_triggers_ceiling(self) -> None:
        from core.workstation.constitutional_resource_economics_engine_v1 import (
            DegradedModeStatus,
            DelegationTopology,
            ExecutionEconomicsScores,
            FederationResourceGraph,
            enforce_economics_hard_ceilings,
        )

        g = FederationResourceGraph()
        e = ExecutionEconomicsScores(blast_radius=0.9)
        t = DelegationTopology()
        dm = DegradedModeStatus()
        blocked, reasons = enforce_economics_hard_ceilings(g, e, t, dm)
        assert blocked is True
        assert any("blast_radius" in r for r in reasons)


class TestRunScarcitySimulations:
    def test_all_8_types(self) -> None:
        from core.workstation.constitutional_resource_economics_engine_v1 import (
            SCARCITY_SIMULATION_TYPES,
            DelegationTopology,
            ExecutionEconomicsScores,
            FederationResourceGraph,
            NodeResourceProfile,
            run_scarcity_simulations,
        )

        g = FederationResourceGraph(
            node_profiles=[NodeResourceProfile(compute_capacity=1.0)],
            total_compute=1.0,
            total_bandwidth=1.0,
        )
        e = ExecutionEconomicsScores()
        t = DelegationTopology()
        sims = run_scarcity_simulations(g, e, t)
        assert len(sims) == 8
        sim_types = {s.simulation_type for s in sims}
        assert sim_types == set(SCARCITY_SIMULATION_TYPES)

    def test_all_simulations_have_ids(self) -> None:
        from core.workstation.constitutional_resource_economics_engine_v1 import (
            DelegationTopology,
            ExecutionEconomicsScores,
            FederationResourceGraph,
            run_scarcity_simulations,
        )

        g = FederationResourceGraph()
        e = ExecutionEconomicsScores()
        t = DelegationTopology()
        sims = run_scarcity_simulations(g, e, t)
        for s in sims:
            assert s.simulation_id.startswith("SCARSIM-")

    def test_all_simulations_serializable(self) -> None:
        from core.workstation.constitutional_resource_economics_engine_v1 import (
            DelegationTopology,
            ExecutionEconomicsScores,
            FederationResourceGraph,
            run_scarcity_simulations,
        )

        g = FederationResourceGraph()
        e = ExecutionEconomicsScores()
        t = DelegationTopology()
        sims = run_scarcity_simulations(g, e, t)
        for s in sims:
            d = s.to_dict()
            serialized = json.dumps(d)
            assert len(serialized) > 0


# ---------------------------------------------------------------------------
# Maturity Classification
# ---------------------------------------------------------------------------


class TestComputeEconomicsMaturity:
    def test_empty_evidence_score_zero(self) -> None:
        from core.workstation.constitutional_resource_economics_engine_v1 import (
            EconomicsEvidence,
            compute_economics_maturity,
        )

        ev = EconomicsEvidence(hard_ceilings_enforced=False, governance_bypass_blocked=False)
        assert compute_economics_maturity(ev) == 0

    def test_full_evidence_high_score(self) -> None:
        from core.workstation.constitutional_resource_economics_engine_v1 import (
            EconomicsEvidence,
            compute_economics_maturity,
        )

        ev = EconomicsEvidence(
            resource_graph_analyzed=True,
            node_count=2,
            total_compute=2.0,
            execution_economics_scored=True,
            composite_economics=0.5,
            delegation_analyzed=True,
            trust_weighted_delegation=True,
            safe_delegation_paths=1,
            degraded_mode_analyzed=True,
            degraded_mode_ready_count=3,
            scarcity_simulated=True,
            replay_safe_scheduling=True,
            continuity_safe_allocation=True,
            founder_confirmed=True,
            hard_ceilings_enforced=True,
            governance_bypass_blocked=True,
        )
        score = compute_economics_maturity(ev)
        assert score >= 13


class TestEconomicsMaturityCeiling:
    def test_dry_run_ceiling_l0(self) -> None:
        from core.workstation.constitutional_resource_economics_engine_v1 import (
            EconomicsEvidence,
            economics_maturity_ceiling,
        )

        ev = EconomicsEvidence(is_dry_run=True)
        ceiling, blocked, reason = economics_maturity_ceiling(ev)
        assert ceiling == "L0_NO_RESOURCE_COORDINATION"
        assert blocked is True

    def test_no_graph_ceiling_l0(self) -> None:
        from core.workstation.constitutional_resource_economics_engine_v1 import (
            EconomicsEvidence,
            economics_maturity_ceiling,
        )

        ev = EconomicsEvidence()
        ceiling, blocked, _ = economics_maturity_ceiling(ev)
        assert ceiling == "L0_NO_RESOURCE_COORDINATION"
        assert blocked is True

    def test_no_delegation_ceiling_l2(self) -> None:
        from core.workstation.constitutional_resource_economics_engine_v1 import (
            EconomicsEvidence,
            economics_maturity_ceiling,
        )

        ev = EconomicsEvidence(
            resource_graph_analyzed=True,
            node_count=1,
            execution_economics_scored=True,
        )
        ceiling, blocked, _ = economics_maturity_ceiling(ev)
        assert ceiling == "L2_EXECUTION_PRIORITIZED"
        assert blocked is True

    def test_full_evidence_ceiling_l5(self) -> None:
        from core.workstation.constitutional_resource_economics_engine_v1 import (
            EconomicsEvidence,
            economics_maturity_ceiling,
        )

        ev = EconomicsEvidence(
            resource_graph_analyzed=True,
            node_count=2,
            execution_economics_scored=True,
            delegation_analyzed=True,
            trust_weighted_delegation=True,
            degraded_mode_analyzed=True,
            scarcity_simulated=True,
            replay_safe_scheduling=True,
            continuity_safe_allocation=True,
            founder_confirmed=True,
            hard_ceilings_enforced=True,
            governance_bypass_blocked=True,
        )
        ceiling, blocked, reason = economics_maturity_ceiling(ev)
        assert ceiling == "L5_CONSTITUTIONAL_RESOURCE_COORDINATION"
        assert blocked is False
        assert reason == ""


class TestClassifyEconomicsMaturity:
    def test_empty_evidence_l0(self) -> None:
        from core.workstation.constitutional_resource_economics_engine_v1 import (
            EconomicsEvidence,
            classify_economics_maturity,
        )

        ev = EconomicsEvidence()
        level, ceiling, blocked, reason = classify_economics_maturity(ev)
        assert level == "L0_NO_RESOURCE_COORDINATION"
        assert blocked is True

    def test_level_clamped_by_ceiling(self) -> None:
        from core.workstation.constitutional_resource_economics_engine_v1 import (
            EconomicsEvidence,
            classify_economics_maturity,
        )

        ev = EconomicsEvidence(
            resource_graph_analyzed=True,
            node_count=2,
            total_compute=2.0,
            execution_economics_scored=True,
            composite_economics=0.5,
            delegation_analyzed=True,
            trust_weighted_delegation=True,
            safe_delegation_paths=1,
            degraded_mode_analyzed=True,
            degraded_mode_ready_count=3,
            scarcity_simulated=True,
            replay_safe_scheduling=True,
            continuity_safe_allocation=True,
            founder_confirmed=False,  # ceiling at L4
            hard_ceilings_enforced=True,
            governance_bypass_blocked=True,
        )
        level, ceiling, blocked, reason = classify_economics_maturity(ev)
        assert ceiling == "L4_SCARCITY_COORDINATED"
        assert blocked is True
        assert "founder" in reason


# ---------------------------------------------------------------------------
# Full Pipeline
# ---------------------------------------------------------------------------


class TestBuildFullEconomicsProof:
    def test_no_upstream_produces_proof(self) -> None:
        from core.workstation.constitutional_resource_economics_engine_v1 import (
            build_full_economics_proof,
        )

        proof = build_full_economics_proof(
            trace_id="test-no-upstream",
            request_id="REQ-TEST",
        )
        assert proof.proof_id.startswith("ECON-")
        assert proof.evidence is not None
        assert proof.resource_graph is not None
        assert proof.execution_economics is not None
        assert proof.delegation_topology is not None
        assert proof.degraded_mode is not None
        assert len(proof.simulations) == 8

    def test_dry_run_strategy(self) -> None:
        from core.workstation.constitutional_resource_economics_engine_v1 import (
            build_full_economics_proof,
        )

        proof = build_full_economics_proof(is_dry_run=True)
        assert proof.execution_strategy == "simulation_only"
        assert proof.maturity_level == "L0_NO_RESOURCE_COORDINATION"

    def test_no_founder_confirmation_strategy(self) -> None:
        from core.workstation.constitutional_resource_economics_engine_v1 import (
            build_full_economics_proof,
        )

        proof = build_full_economics_proof(founder_confirmed=False)
        assert proof.execution_strategy == "await_founder_confirmation"

    def test_founder_confirmed_strategy(self) -> None:
        from core.workstation.constitutional_resource_economics_engine_v1 import (
            build_full_economics_proof,
        )

        proof = build_full_economics_proof(founder_confirmed=True)
        assert proof.execution_strategy == "constitutional_resource_coordination_active"


class TestBuildFullEconomicsProofWithUpstream:
    def test_with_federation_proof(self) -> None:
        from core.workstation.constitutional_resource_economics_engine_v1 import (
            build_full_economics_proof,
        )
        from core.workstation.distributed_constitutional_substrate_federation_v1 import (
            build_full_federation_proof,
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
        from core.workstation.adaptive_governance_intelligence_engine_v1 import (
            build_full_governance_intelligence_proof,
        )

        cap = build_full_capability_proof(trace_id="chain-test")
        orch = build_full_orchestration_proof(capability_proof=cap, trace_id="chain-test")
        cont = build_full_continuity_proof(
            orchestration_proof=orch, capability_proof=cap, trace_id="chain-test"
        )
        gov = build_full_governance_intelligence_proof(
            orchestration_proof=orch,
            continuity_proof=cont,
            capability_proof=cap,
            trace_id="chain-test",
        )
        const = build_full_constitutional_proof(
            orchestration_proof=orch,
            continuity_proof=cont,
            governance_proof=gov,
            capability_proof=cap,
            trace_id="chain-test",
        )
        fed = build_full_federation_proof(
            constitutional_proof=const,
            orchestration_proof=orch,
            continuity_proof=cont,
            governance_proof=gov,
            capability_proof=cap,
            trace_id="chain-test",
        )

        proof = build_full_economics_proof(
            federation_proof=fed,
            orchestration_proof=orch,
            continuity_proof=cont,
            constitutional_proof=const,
            governance_proof=gov,
            capability_proof=cap,
            founder_confirmed=True,
            trace_id="chain-test",
        )

        assert proof.proof_id.startswith("ECON-")
        assert proof.resource_graph is not None
        assert len(proof.resource_graph.node_profiles) >= 1
        assert proof.execution_economics is not None
        assert proof.delegation_topology is not None
        assert len(proof.simulations) == 8
        assert proof.evidence.founder_confirmed is True
        assert proof.execution_strategy == "constitutional_resource_coordination_active"

    def test_full_chain_maturity_above_l0(self) -> None:
        from core.workstation.constitutional_resource_economics_engine_v1 import (
            build_full_economics_proof,
        )
        from core.workstation.distributed_constitutional_substrate_federation_v1 import (
            build_full_federation_proof,
        )
        from core.workstation.governed_recursive_orchestration_engine_v1 import (
            build_full_orchestration_proof,
        )
        from core.workstation.recursive_capability_planning_engine_v1 import (
            build_full_capability_proof,
        )

        cap = build_full_capability_proof()
        orch = build_full_orchestration_proof(capability_proof=cap)
        fed = build_full_federation_proof(orchestration_proof=orch, capability_proof=cap)

        proof = build_full_economics_proof(
            federation_proof=fed,
            orchestration_proof=orch,
            capability_proof=cap,
            founder_confirmed=True,
        )
        assert proof.maturity_level != "L0_NO_RESOURCE_COORDINATION"


# ---------------------------------------------------------------------------
# Persistence
# ---------------------------------------------------------------------------


class TestPersistEconomicsProof:
    def test_persist_creates_file(self, tmp_path: Path) -> None:
        from core.workstation.constitutional_resource_economics_engine_v1 import (
            build_full_economics_proof,
            persist_economics_proof,
        )

        proof = build_full_economics_proof(trace_id="persist-test")
        path = persist_economics_proof(proof, base_dir=tmp_path)
        assert path.exists()
        assert path.name.startswith("ECON-")
        data = json.loads(path.read_text())
        assert data["proof_type"] == "constitutional_resource_economics"
        assert data["proof_id"] == proof.proof_id

    def test_persist_json_valid(self, tmp_path: Path) -> None:
        from core.workstation.constitutional_resource_economics_engine_v1 import (
            build_full_economics_proof,
            persist_economics_proof,
        )

        proof = build_full_economics_proof(trace_id="json-test")
        path = persist_economics_proof(proof, base_dir=tmp_path)
        data = json.loads(path.read_text())
        assert "evidence" in data
        assert "resource_graph" in data
        assert "execution_economics" in data
        assert "simulations" in data


# ---------------------------------------------------------------------------
# Command Registration
# ---------------------------------------------------------------------------


class TestEconomicsCommandRegistration:
    def test_registry_has_22_commands(self) -> None:
        from core.registry.canonical_command_registry_v1 import (
            CanonicalCommandRegistryV1,
        )

        reg = CanonicalCommandRegistryV1()
        assert len(reg) == 22

    def test_economics_report_in_registry(self) -> None:
        from core.registry.canonical_command_registry_v1 import (
            CanonicalCommandRegistryV1,
        )

        reg = CanonicalCommandRegistryV1()
        assert "!economics-report" in reg.commands
        entry = reg.get("!economics-report")
        assert entry is not None
        assert entry.canonical_action == "economics_report"

    def test_economics_report_action_in_allowed(self) -> None:
        from core.control_plane_router.router_contracts import ALLOWED_ACTION_TYPES

        assert "economics_report" in ALLOWED_ACTION_TYPES

    def test_allowed_action_types_count(self) -> None:
        from core.control_plane_router.router_contracts import ALLOWED_ACTION_TYPES

        assert len(ALLOWED_ACTION_TYPES) == 22

    def test_economics_report_in_action_map(self) -> None:
        from core.control_plane_router.control_plane_router_v1 import (
            ACTION_CAPABILITY_MAP,
        )

        assert "economics_report" in ACTION_CAPABILITY_MAP

    def test_config_has_22_actions(self) -> None:
        config = json.loads(Path("/opt/OS/config/control_plane_router_v1.json").read_text())
        assert len(config["allowed_action_types"]) == 22
        assert "economics_report" in config["allowed_action_types"]

    def test_substrate_commands_has_economics(self) -> None:
        from handlers.substrate_command_handler import SUBSTRATE_COMMANDS

        assert "!economics-report" in SUBSTRATE_COMMANDS

    def test_substrate_commands_count(self) -> None:
        from handlers.substrate_command_handler import SUBSTRATE_COMMANDS

        assert len(SUBSTRATE_COMMANDS) == 22


# ---------------------------------------------------------------------------
# Live Proof
# ---------------------------------------------------------------------------


class TestLiveEconomicsProof:
    def test_live_proof_with_full_upstream(self) -> None:
        from core.workstation.constitutional_resource_economics_engine_v1 import (
            ECONOMICS_HARD_CEILINGS,
            ECONOMICS_MATURITY_LEVELS,
            SCARCITY_SIMULATION_TYPES,
            build_full_economics_proof,
        )
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

        base = Path("/opt/OS")
        cap = build_full_capability_proof(trace_id="live-econ")
        orch = build_full_orchestration_proof(capability_proof=cap, trace_id="live-econ")
        cont = build_full_continuity_proof(
            orchestration_proof=orch,
            capability_proof=cap,
            trace_id="live-econ",
            base_dir=base,
        )
        gov = build_full_governance_intelligence_proof(
            orchestration_proof=orch,
            continuity_proof=cont,
            capability_proof=cap,
            trace_id="live-econ",
            base_dir=base,
        )
        const = build_full_constitutional_proof(
            orchestration_proof=orch,
            continuity_proof=cont,
            governance_proof=gov,
            capability_proof=cap,
            trace_id="live-econ",
            base_dir=base,
        )
        fed = build_full_federation_proof(
            constitutional_proof=const,
            orchestration_proof=orch,
            continuity_proof=cont,
            governance_proof=gov,
            capability_proof=cap,
            trace_id="live-econ",
            base_dir=base,
        )

        proof = build_full_economics_proof(
            federation_proof=fed,
            orchestration_proof=orch,
            continuity_proof=cont,
            constitutional_proof=const,
            governance_proof=gov,
            capability_proof=cap,
            founder_confirmed=True,
            trace_id="live-econ",
            base_dir=base,
        )

        assert proof.proof_id.startswith("ECON-")
        assert proof.maturity_level in ECONOMICS_MATURITY_LEVELS
        assert proof.evidence is not None
        assert proof.evidence.resource_graph_analyzed is True
        assert proof.evidence.node_count >= 1
        assert proof.evidence.execution_economics_scored is True
        assert proof.evidence.delegation_analyzed is True
        assert proof.evidence.scarcity_simulated is True
        assert proof.evidence.founder_confirmed is True
        assert len(proof.simulations) == 8
        sim_types = {s.simulation_type for s in proof.simulations}
        assert sim_types == set(SCARCITY_SIMULATION_TYPES)
        assert proof.resource_graph is not None
        assert proof.execution_economics is not None
        assert proof.delegation_topology is not None
        assert proof.degraded_mode is not None
        assert proof.execution_strategy == "constitutional_resource_coordination_active"
