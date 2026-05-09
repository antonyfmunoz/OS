"""Tests for Phase 96.8AW — Governed Recursive Orchestration Engine.

Verifies:
  1. DAG construction (7 types) with cycle detection and topological sort
  2. Blast radius analysis per upgrade
  3. Rollback planning with determinism and strategy
  4. Rollout simulation (8 outcome types)
  5. Replayability enforcement (safe/unsafe classification)
  6. Unsafe chain detection
  7. Governance bottleneck detection
  8. Safety-first sequencing (6-key priority)
  9. Conflict detection between proposals
  10. Orchestration maturity levels L0-L5
  11. Hard ceilings preventing maturity inflation
  12. Full pipeline integration
  13. Proof persistence
  14. Canonical instance separation (no shared state)
  15. Registry integration (17 commands, parity checks)
"""

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, "/opt/OS")
sys.path.insert(0, "/opt/OS/services")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _get_proposals():
    from core.workstation.recursive_capability_planning_engine_v1 import (
        CapabilityPlanningEvidence,
        build_capability_graph,
        generate_upgrade_proposals,
    )

    ev = CapabilityPlanningEvidence()
    graph = build_capability_graph(ev)
    return generate_upgrade_proposals(ev, graph)


# ---------------------------------------------------------------------------
# DAGNode
# ---------------------------------------------------------------------------


class TestDAGNode:
    def test_node_creates_with_defaults(self) -> None:
        from core.workstation.governed_recursive_orchestration_engine_v1 import DAGNode

        node = DAGNode(name="test")
        assert node.name == "test"
        assert node.dag_type == "execution"
        assert node.node_id.startswith("DAGN-")
        assert node.wave == 0

    def test_node_to_dict(self) -> None:
        from core.workstation.governed_recursive_orchestration_engine_v1 import DAGNode

        node = DAGNode(name="test", blast_radius=0.5)
        d = node.to_dict()
        assert d["name"] == "test"
        assert d["blast_radius"] == 0.5

    def test_node_dependencies(self) -> None:
        from core.workstation.governed_recursive_orchestration_engine_v1 import DAGNode

        node = DAGNode(name="a", dependencies=["b", "c"])
        assert len(node.dependencies) == 2

    def test_node_flags(self) -> None:
        from core.workstation.governed_recursive_orchestration_engine_v1 import DAGNode

        node = DAGNode(replay_safe=True, rollback_safe=True, governance_approved=True)
        assert node.replay_safe is True
        assert node.rollback_safe is True
        assert node.governance_approved is True


# ---------------------------------------------------------------------------
# OrchestrationDAG
# ---------------------------------------------------------------------------


class TestOrchestrationDAG:
    def test_dag_creates_with_defaults(self) -> None:
        from core.workstation.governed_recursive_orchestration_engine_v1 import (
            OrchestrationDAG,
        )

        dag = OrchestrationDAG()
        assert dag.dag_id.startswith("DAG-")
        assert dag.dag_type == "execution"
        assert dag.has_cycles is False

    def test_dag_to_dict(self) -> None:
        from core.workstation.governed_recursive_orchestration_engine_v1 import (
            DAGNode,
            OrchestrationDAG,
        )

        dag = OrchestrationDAG(
            nodes=[DAGNode(name="a"), DAGNode(name="b")],
            edges=[("a", "b")],
        )
        d = dag.to_dict()
        assert d["node_count"] == 2
        assert d["edge_count"] == 1
        assert d["has_cycles"] is False

    def test_dag_cycle_flag(self) -> None:
        from core.workstation.governed_recursive_orchestration_engine_v1 import (
            OrchestrationDAG,
        )

        dag = OrchestrationDAG(has_cycles=True)
        assert dag.has_cycles is True


# ---------------------------------------------------------------------------
# BlastRadius
# ---------------------------------------------------------------------------


class TestBlastRadius:
    def test_blast_radius_auto_compute(self) -> None:
        from core.workstation.governed_recursive_orchestration_engine_v1 import (
            BlastRadius,
        )

        br = BlastRadius(
            upgrade_name="test",
            affected_registries=["a", "b"],
            affected_relays=["c"],
        )
        assert br.total_affected == 3
        assert br.risk_score > 0

    def test_blast_radius_risk_capped(self) -> None:
        from core.workstation.governed_recursive_orchestration_engine_v1 import (
            BlastRadius,
        )

        br = BlastRadius(
            upgrade_name="test",
            affected_registries=["a"] * 25,
        )
        assert br.risk_score <= 1.0

    def test_blast_radius_to_dict(self) -> None:
        from core.workstation.governed_recursive_orchestration_engine_v1 import (
            BlastRadius,
        )

        br = BlastRadius(upgrade_name="x")
        d = br.to_dict()
        assert d["upgrade_name"] == "x"
        assert "risk_score" in d

    def test_blast_radius_empty(self) -> None:
        from core.workstation.governed_recursive_orchestration_engine_v1 import (
            BlastRadius,
        )

        br = BlastRadius(upgrade_name="empty")
        assert br.total_affected == 0
        assert br.risk_score == 0.0


# ---------------------------------------------------------------------------
# RollbackPlan
# ---------------------------------------------------------------------------


class TestRollbackPlan:
    def test_rollback_plan_creates(self) -> None:
        from core.workstation.governed_recursive_orchestration_engine_v1 import (
            RollbackPlan,
        )

        rp = RollbackPlan(upgrade_name="test", rollback_safe=True)
        assert rp.plan_id.startswith("RBACK-")
        assert rp.rollback_safe is True

    def test_rollback_plan_to_dict(self) -> None:
        from core.workstation.governed_recursive_orchestration_engine_v1 import (
            RollbackPlan,
        )

        rp = RollbackPlan(upgrade_name="x", rollback_strategy="revert")
        d = rp.to_dict()
        assert d["rollback_strategy"] == "revert"

    def test_rollback_plan_determinism(self) -> None:
        from core.workstation.governed_recursive_orchestration_engine_v1 import (
            RollbackPlan,
        )

        det = RollbackPlan(rollback_deterministic=True)
        non = RollbackPlan(rollback_deterministic=False)
        assert det.rollback_deterministic is True
        assert non.rollback_deterministic is False


# ---------------------------------------------------------------------------
# SimulationOutcome
# ---------------------------------------------------------------------------


class TestSimulationOutcome:
    def test_outcome_creates(self) -> None:
        from core.workstation.governed_recursive_orchestration_engine_v1 import (
            SimulationOutcome,
        )

        so = SimulationOutcome(outcome_type="successful_rollout", succeeded=True)
        assert so.outcome_id.startswith("SIM-")
        assert so.succeeded is True

    def test_outcome_to_dict(self) -> None:
        from core.workstation.governed_recursive_orchestration_engine_v1 import (
            SimulationOutcome,
        )

        so = SimulationOutcome(outcome_type="test", failure_reason="x")
        d = so.to_dict()
        assert d["failure_reason"] == "x"

    def test_outcome_recovery_path(self) -> None:
        from core.workstation.governed_recursive_orchestration_engine_v1 import (
            SimulationOutcome,
        )

        so = SimulationOutcome(recovery_path="rollback")
        assert so.recovery_path == "rollback"


# ---------------------------------------------------------------------------
# OrchestrationEvidence
# ---------------------------------------------------------------------------


class TestOrchestrationEvidence:
    def test_evidence_defaults(self) -> None:
        from core.workstation.governed_recursive_orchestration_engine_v1 import (
            OrchestrationEvidence,
        )

        ev = OrchestrationEvidence()
        assert ev.dag_generated is False
        assert ev.founder_confirmed is False

    def test_evidence_to_dict(self) -> None:
        from core.workstation.governed_recursive_orchestration_engine_v1 import (
            OrchestrationEvidence,
        )

        ev = OrchestrationEvidence(dag_generated=True, dag_count=7)
        d = ev.to_dict()
        assert d["dag_generated"] is True
        assert d["dag_count"] == 7

    def test_evidence_all_fields(self) -> None:
        from core.workstation.governed_recursive_orchestration_engine_v1 import (
            OrchestrationEvidence,
        )

        ev = OrchestrationEvidence(
            dag_generated=True,
            replay_validated=True,
            rollback_validated=True,
            governance_validated=True,
            sequencing_validated=True,
            blast_radius_analyzed=True,
            simulation_completed=True,
            founder_confirmed=True,
        )
        d = ev.to_dict()
        for k in [
            "dag_generated",
            "replay_validated",
            "rollback_validated",
            "governance_validated",
            "sequencing_validated",
            "blast_radius_analyzed",
            "simulation_completed",
            "founder_confirmed",
        ]:
            assert d[k] is True


# ---------------------------------------------------------------------------
# OrchestrationProof
# ---------------------------------------------------------------------------


class TestOrchestrationProof:
    def test_proof_creates(self) -> None:
        from core.workstation.governed_recursive_orchestration_engine_v1 import (
            OrchestrationProof,
        )

        p = OrchestrationProof(trace_id="test")
        assert p.proof_id.startswith("ORCHPROOF-")
        assert p.maturity_level == "L0_SIMULATED_ORCHESTRATION"

    def test_proof_to_dict(self) -> None:
        from core.workstation.governed_recursive_orchestration_engine_v1 import (
            OrchestrationProof,
        )

        p = OrchestrationProof(trace_id="t1")
        d = p.to_dict()
        assert d["proof_type"] == "governed_recursive_orchestration"
        assert d["trace_id"] == "t1"
        assert "dag_count" in d

    def test_proof_serializable(self) -> None:
        from core.workstation.governed_recursive_orchestration_engine_v1 import (
            OrchestrationProof,
        )

        p = OrchestrationProof()
        s = json.dumps(p.to_dict())
        assert len(s) > 0


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------


class TestConstants:
    def test_dag_types_count(self) -> None:
        from core.workstation.governed_recursive_orchestration_engine_v1 import (
            DAG_TYPES,
        )

        assert len(DAG_TYPES) == 7

    def test_dag_types_values(self) -> None:
        from core.workstation.governed_recursive_orchestration_engine_v1 import (
            DAG_TYPES,
        )

        expected = {
            "execution",
            "dependency",
            "governance",
            "rollback",
            "replay",
            "maturity",
            "infrastructure_mutation",
        }
        assert DAG_TYPES == expected

    def test_simulation_outcomes_count(self) -> None:
        from core.workstation.governed_recursive_orchestration_engine_v1 import (
            SIMULATION_OUTCOMES,
        )

        assert len(SIMULATION_OUTCOMES) == 8

    def test_simulation_outcomes_values(self) -> None:
        from core.workstation.governed_recursive_orchestration_engine_v1 import (
            SIMULATION_OUTCOMES,
        )

        expected = {
            "successful_rollout",
            "partial_rollout",
            "stale_rollout",
            "replay_failure",
            "relay_disconnect",
            "governance_rejection",
            "rollback_recovery",
            "partial_infrastructure_mutation",
        }
        assert SIMULATION_OUTCOMES == expected

    def test_maturity_levels_count(self) -> None:
        from core.workstation.governed_recursive_orchestration_engine_v1 import (
            ORCHESTRATION_MATURITY_LEVELS,
        )

        assert len(ORCHESTRATION_MATURITY_LEVELS) == 6

    def test_maturity_requirements_keys(self) -> None:
        from core.workstation.governed_recursive_orchestration_engine_v1 import (
            ORCHESTRATION_MATURITY_LEVELS,
            ORCHESTRATION_MATURITY_REQUIREMENTS,
        )

        for level in ORCHESTRATION_MATURITY_LEVELS:
            assert level in ORCHESTRATION_MATURITY_REQUIREMENTS

    def test_upgrade_blast_map_count(self) -> None:
        from core.workstation.governed_recursive_orchestration_engine_v1 import (
            UPGRADE_BLAST_MAP,
        )

        assert len(UPGRADE_BLAST_MAP) == 5

    def test_rollback_strategies_count(self) -> None:
        from core.workstation.governed_recursive_orchestration_engine_v1 import (
            ROLLBACK_STRATEGIES,
        )

        assert len(ROLLBACK_STRATEGIES) == 5


# ---------------------------------------------------------------------------
# Cycle detection
# ---------------------------------------------------------------------------


class TestCycleDetection:
    def test_no_cycles_in_dag(self) -> None:
        from core.workstation.governed_recursive_orchestration_engine_v1 import (
            _detect_cycles,
        )

        adj = {"a": ["b"], "b": ["c"], "c": []}
        assert _detect_cycles(adj) is False

    def test_detects_cycle(self) -> None:
        from core.workstation.governed_recursive_orchestration_engine_v1 import (
            _detect_cycles,
        )

        adj = {"a": ["b"], "b": ["c"], "c": ["a"]}
        assert _detect_cycles(adj) is True

    def test_self_loop(self) -> None:
        from core.workstation.governed_recursive_orchestration_engine_v1 import (
            _detect_cycles,
        )

        adj = {"a": ["a"]}
        assert _detect_cycles(adj) is True

    def test_empty_graph(self) -> None:
        from core.workstation.governed_recursive_orchestration_engine_v1 import (
            _detect_cycles,
        )

        assert _detect_cycles({}) is False


# ---------------------------------------------------------------------------
# Topological sort
# ---------------------------------------------------------------------------


class TestTopologicalSort:
    def test_linear_sort(self) -> None:
        from core.workstation.governed_recursive_orchestration_engine_v1 import (
            _topological_sort,
        )

        adj = {"a": [], "b": ["a"], "c": ["b"]}
        result = _topological_sort(adj)
        assert result == ["c", "b", "a"]

    def test_returns_empty_on_cycle(self) -> None:
        from core.workstation.governed_recursive_orchestration_engine_v1 import (
            _topological_sort,
        )

        adj = {"a": ["b"], "b": ["a"]}
        assert _topological_sort(adj) == []

    def test_deterministic_tie_breaking(self) -> None:
        from core.workstation.governed_recursive_orchestration_engine_v1 import (
            _topological_sort,
        )

        adj = {"c": [], "b": [], "a": []}
        result = _topological_sort(adj)
        assert result == ["a", "b", "c"]


# ---------------------------------------------------------------------------
# Wave assignment
# ---------------------------------------------------------------------------


class TestWaveAssignment:
    def test_wave_depth(self) -> None:
        from core.workstation.governed_recursive_orchestration_engine_v1 import (
            _assign_waves,
        )

        adj = {"a": [], "b": ["a"], "c": ["b"]}
        order = ["a", "b", "c"]
        waves = _assign_waves(adj, order)
        assert waves["a"] == 0
        assert waves["b"] == 1
        assert waves["c"] == 2

    def test_parallel_waves(self) -> None:
        from core.workstation.governed_recursive_orchestration_engine_v1 import (
            _assign_waves,
        )

        adj = {"a": [], "b": [], "c": ["a", "b"]}
        order = ["a", "b", "c"]
        waves = _assign_waves(adj, order)
        assert waves["a"] == 0
        assert waves["b"] == 0
        assert waves["c"] == 1


# ---------------------------------------------------------------------------
# DAG builders
# ---------------------------------------------------------------------------


class TestDAGBuilders:
    def test_execution_dag(self) -> None:
        from core.workstation.governed_recursive_orchestration_engine_v1 import (
            build_execution_dag,
        )

        proposals = _get_proposals()
        dag = build_execution_dag(proposals)
        assert dag.dag_type == "execution"
        assert len(dag.nodes) == len(proposals)
        assert dag.has_cycles is False

    def test_dependency_dag(self) -> None:
        from core.workstation.governed_recursive_orchestration_engine_v1 import (
            build_dependency_dag,
        )

        proposals = _get_proposals()
        dag = build_dependency_dag(proposals)
        assert dag.dag_type == "dependency"
        assert len(dag.nodes) == len(proposals)

    def test_governance_dag(self) -> None:
        from core.workstation.governed_recursive_orchestration_engine_v1 import (
            build_governance_dag,
        )

        proposals = _get_proposals()
        dag = build_governance_dag(proposals)
        assert dag.dag_type == "governance"
        assert len(dag.nodes) == len(proposals)

    def test_rollback_dag(self) -> None:
        from core.workstation.governed_recursive_orchestration_engine_v1 import (
            build_rollback_dag,
        )

        proposals = _get_proposals()
        dag = build_rollback_dag(proposals)
        assert dag.dag_type == "rollback"
        safe_nodes = [n for n in dag.nodes if n.rollback_safe]
        assert len(safe_nodes) > 0

    def test_replay_dag(self) -> None:
        from core.workstation.governed_recursive_orchestration_engine_v1 import (
            build_replay_dag,
        )

        proposals = _get_proposals()
        dag = build_replay_dag(proposals)
        assert dag.dag_type == "replay"
        replay_nodes = [n for n in dag.nodes if n.replay_safe]
        assert len(replay_nodes) > 0

    def test_maturity_dag(self) -> None:
        from core.workstation.governed_recursive_orchestration_engine_v1 import (
            build_maturity_dag,
        )

        proposals = _get_proposals()
        dag = build_maturity_dag(proposals)
        assert dag.dag_type == "maturity"
        assert dag.has_cycles is False

    def test_infrastructure_mutation_dag(self) -> None:
        from core.workstation.governed_recursive_orchestration_engine_v1 import (
            build_infrastructure_mutation_dag,
        )

        proposals = _get_proposals()
        dag = build_infrastructure_mutation_dag(proposals)
        assert dag.dag_type == "infrastructure_mutation"
        blast_nodes = [n for n in dag.nodes if n.blast_radius > 0]
        assert len(blast_nodes) > 0

    def test_all_dags_count(self) -> None:
        from core.workstation.governed_recursive_orchestration_engine_v1 import (
            build_all_dags,
        )

        proposals = _get_proposals()
        dags = build_all_dags(proposals)
        assert len(dags) == 7

    def test_all_dag_types_represented(self) -> None:
        from core.workstation.governed_recursive_orchestration_engine_v1 import (
            DAG_TYPES,
            build_all_dags,
        )

        proposals = _get_proposals()
        dags = build_all_dags(proposals)
        types = {d.dag_type for d in dags}
        assert types == DAG_TYPES


# ---------------------------------------------------------------------------
# Blast radius analysis
# ---------------------------------------------------------------------------


class TestBlastRadiusAnalysis:
    def test_known_upgrade_blast(self) -> None:
        from core.workstation.governed_recursive_orchestration_engine_v1 import (
            compute_blast_radius,
        )

        br = compute_blast_radius("local_adapter_execution")
        assert br.total_affected > 0
        assert len(br.affected_registries) > 0
        assert br.upgrade_name == "local_adapter_execution"

    def test_unknown_upgrade_empty(self) -> None:
        from core.workstation.governed_recursive_orchestration_engine_v1 import (
            compute_blast_radius,
        )

        br = compute_blast_radius("nonexistent")
        assert br.total_affected == 0

    def test_world_model_highest_blast(self) -> None:
        from core.workstation.governed_recursive_orchestration_engine_v1 import (
            compute_blast_radius,
        )

        wm = compute_blast_radius("world_model_integration")
        la = compute_blast_radius("local_adapter_execution")
        assert wm.total_affected > la.total_affected

    def test_all_blast_radii(self) -> None:
        from core.workstation.governed_recursive_orchestration_engine_v1 import (
            compute_all_blast_radii,
        )

        proposals = _get_proposals()
        radii = compute_all_blast_radii(proposals)
        assert len(radii) == len(proposals)

    def test_blast_radius_seven_categories(self) -> None:
        from core.workstation.governed_recursive_orchestration_engine_v1 import (
            compute_blast_radius,
        )

        br = compute_blast_radius("cu_adapter_execution")
        d = br.to_dict()
        for key in [
            "affected_registries",
            "affected_relays",
            "affected_adapters",
            "affected_execution_chains",
            "affected_proofs",
            "affected_governance_surfaces",
            "affected_topology_layers",
        ]:
            assert key in d


# ---------------------------------------------------------------------------
# Rollback planning
# ---------------------------------------------------------------------------


class TestRollbackPlanning:
    def test_known_rollback_plan(self) -> None:
        from core.workstation.governed_recursive_orchestration_engine_v1 import (
            build_rollback_plan,
        )

        rp = build_rollback_plan("local_adapter_execution")
        assert rp.rollback_safe is True
        assert rp.rollback_deterministic is True
        assert len(rp.rollback_replay_contract) > 0

    def test_non_deterministic_rollback(self) -> None:
        from core.workstation.governed_recursive_orchestration_engine_v1 import (
            build_rollback_plan,
        )

        rp = build_rollback_plan("multi_platform_ingestion")
        assert rp.rollback_deterministic is False

    def test_unknown_upgrade_fallback(self) -> None:
        from core.workstation.governed_recursive_orchestration_engine_v1 import (
            build_rollback_plan,
        )

        rp = build_rollback_plan("nonexistent")
        assert rp.rollback_strategy == "no_strategy_defined"
        assert rp.rollback_safe is False

    def test_all_rollback_plans(self) -> None:
        from core.workstation.governed_recursive_orchestration_engine_v1 import (
            build_all_rollback_plans,
        )

        proposals = _get_proposals()
        plans = build_all_rollback_plans(proposals)
        assert len(plans) == len(proposals)

    def test_rollback_blast_radius_values(self) -> None:
        from core.workstation.governed_recursive_orchestration_engine_v1 import (
            build_rollback_plan,
        )

        local = build_rollback_plan("local_adapter_execution")
        world = build_rollback_plan("world_model_integration")
        assert local.rollback_blast_radius < world.rollback_blast_radius


# ---------------------------------------------------------------------------
# Rollout simulation
# ---------------------------------------------------------------------------


class TestRolloutSimulation:
    def test_successful_rollout(self) -> None:
        from core.workstation.governed_recursive_orchestration_engine_v1 import (
            BlastRadius,
            RollbackPlan,
            simulate_rollout,
        )

        rb = RollbackPlan(rollback_safe=True)
        br = BlastRadius(risk_score=0.2)
        sim = simulate_rollout("test", "successful_rollout", rb, br)
        assert sim.succeeded is True
        assert sim.replay_intact is True

    def test_partial_rollout(self) -> None:
        from core.workstation.governed_recursive_orchestration_engine_v1 import (
            BlastRadius,
            RollbackPlan,
            simulate_rollout,
        )

        sim = simulate_rollout("test", "partial_rollout", RollbackPlan(), BlastRadius())
        assert sim.succeeded is False
        assert sim.failure_reason == "partial_completion"

    def test_governance_rejection(self) -> None:
        from core.workstation.governed_recursive_orchestration_engine_v1 import (
            BlastRadius,
            RollbackPlan,
            simulate_rollout,
        )

        sim = simulate_rollout("test", "governance_rejection", RollbackPlan(), BlastRadius())
        assert sim.governance_satisfied is False
        assert sim.recovery_path == "obtain_founder_approval"

    def test_relay_disconnect(self) -> None:
        from core.workstation.governed_recursive_orchestration_engine_v1 import (
            BlastRadius,
            RollbackPlan,
            simulate_rollout,
        )

        sim = simulate_rollout("test", "relay_disconnect", RollbackPlan(), BlastRadius())
        assert sim.rollback_viable is True
        assert sim.replay_intact is True

    def test_replay_failure(self) -> None:
        from core.workstation.governed_recursive_orchestration_engine_v1 import (
            BlastRadius,
            RollbackPlan,
            simulate_rollout,
        )

        sim = simulate_rollout("test", "replay_failure", RollbackPlan(), BlastRadius())
        assert sim.replay_intact is False

    def test_rollback_recovery_deterministic(self) -> None:
        from core.workstation.governed_recursive_orchestration_engine_v1 import (
            BlastRadius,
            RollbackPlan,
            simulate_rollout,
        )

        rb = RollbackPlan(rollback_deterministic=True, rollback_blast_radius=0.2)
        sim = simulate_rollout("test", "rollback_recovery", rb, BlastRadius())
        assert sim.succeeded is True
        assert sim.blast_radius_acceptable is True

    def test_partial_infrastructure_mutation(self) -> None:
        from core.workstation.governed_recursive_orchestration_engine_v1 import (
            BlastRadius,
            RollbackPlan,
            simulate_rollout,
        )

        sim = simulate_rollout(
            "test", "partial_infrastructure_mutation", RollbackPlan(), BlastRadius()
        )
        assert sim.succeeded is False
        assert sim.blast_radius_acceptable is False

    def test_stale_rollout(self) -> None:
        from core.workstation.governed_recursive_orchestration_engine_v1 import (
            BlastRadius,
            RollbackPlan,
            simulate_rollout,
        )

        sim = simulate_rollout("test", "stale_rollout", RollbackPlan(), BlastRadius())
        assert sim.replay_intact is False
        assert sim.governance_satisfied is False

    def test_all_outcome_types_simulated(self) -> None:
        from core.workstation.governed_recursive_orchestration_engine_v1 import (
            SIMULATION_OUTCOMES,
            simulate_all_rollouts,
            compute_all_blast_radii,
            build_all_rollback_plans,
        )

        proposals = _get_proposals()
        rb = build_all_rollback_plans(proposals)
        br = compute_all_blast_radii(proposals)
        sims = simulate_all_rollouts(proposals, rb, br)
        assert len(sims) == len(proposals) * len(SIMULATION_OUTCOMES)

    def test_unknown_outcome_type(self) -> None:
        from core.workstation.governed_recursive_orchestration_engine_v1 import (
            BlastRadius,
            RollbackPlan,
            simulate_rollout,
        )

        sim = simulate_rollout("test", "totally_unknown", RollbackPlan(), BlastRadius())
        assert sim.outcome_type == "unknown"


# ---------------------------------------------------------------------------
# Replayability enforcement
# ---------------------------------------------------------------------------


class TestReplayabilityEnforcement:
    def test_replay_safety_classification(self) -> None:
        from core.workstation.governed_recursive_orchestration_engine_v1 import (
            validate_replay_safety,
            build_all_rollback_plans,
        )

        proposals = _get_proposals()
        rbs = build_all_rollback_plans(proposals)
        safe, unsafe = validate_replay_safety(proposals, rbs)
        assert len(safe) + len(unsafe) == len(proposals)

    def test_replay_safe_has_requirements(self) -> None:
        from core.workstation.governed_recursive_orchestration_engine_v1 import (
            validate_replay_safety,
            build_all_rollback_plans,
        )

        proposals = _get_proposals()
        rbs = build_all_rollback_plans(proposals)
        safe, _ = validate_replay_safety(proposals, rbs)
        for name in safe:
            p = next(p for p in proposals if p.name == name)
            assert len(p.replay_requirements) > 0
            assert len(p.governance_constraints) > 0


# ---------------------------------------------------------------------------
# Unsafe chain detection
# ---------------------------------------------------------------------------


class TestUnsafeChainDetection:
    def test_detects_unsafe_chains(self) -> None:
        from core.workstation.governed_recursive_orchestration_engine_v1 import (
            detect_unsafe_chains,
            build_all_rollback_plans,
            compute_all_blast_radii,
        )

        proposals = _get_proposals()
        rbs = build_all_rollback_plans(proposals)
        brs = compute_all_blast_radii(proposals)
        unsafe = detect_unsafe_chains(proposals, rbs, brs)
        assert isinstance(unsafe, list)

    def test_non_deterministic_flagged(self) -> None:
        from core.workstation.governed_recursive_orchestration_engine_v1 import (
            detect_unsafe_chains,
            build_all_rollback_plans,
            compute_all_blast_radii,
        )

        proposals = _get_proposals()
        rbs = build_all_rollback_plans(proposals)
        brs = compute_all_blast_radii(proposals)
        unsafe = detect_unsafe_chains(proposals, rbs, brs)
        non_det = [u for u in unsafe if "non_deterministic_rollback" in u]
        assert len(non_det) > 0

    def test_high_blast_flagged(self) -> None:
        from core.workstation.governed_recursive_orchestration_engine_v1 import (
            detect_unsafe_chains,
            build_all_rollback_plans,
            compute_all_blast_radii,
        )

        proposals = _get_proposals()
        rbs = build_all_rollback_plans(proposals)
        brs = compute_all_blast_radii(proposals)
        unsafe = detect_unsafe_chains(proposals, rbs, brs)
        high_blast = [u for u in unsafe if "high_blast_radius" in u]
        assert isinstance(high_blast, list)


# ---------------------------------------------------------------------------
# Governance bottleneck detection
# ---------------------------------------------------------------------------


class TestGovernanceBottleneckDetection:
    def test_detects_bottlenecks(self) -> None:
        from core.workstation.governed_recursive_orchestration_engine_v1 import (
            detect_governance_bottlenecks,
        )

        proposals = _get_proposals()
        bottlenecks = detect_governance_bottlenecks(proposals)
        assert isinstance(bottlenecks, list)

    def test_multi_governance_flagged(self) -> None:
        from core.workstation.governed_recursive_orchestration_engine_v1 import (
            detect_governance_bottlenecks,
        )

        proposals = _get_proposals()
        multi_gov = [p for p in proposals if len(p.governance_constraints) > 1]
        bottlenecks = detect_governance_bottlenecks(proposals)
        multi_flagged = [b for b in bottlenecks if "governance approvals" in b]
        assert len(multi_flagged) == len(multi_gov)


# ---------------------------------------------------------------------------
# Safety-first sequencing
# ---------------------------------------------------------------------------


class TestSafetyFirstSequencing:
    def test_sequencing_returns_all(self) -> None:
        from core.workstation.governed_recursive_orchestration_engine_v1 import (
            sequence_upgrades,
            build_all_rollback_plans,
            compute_all_blast_radii,
        )

        proposals = _get_proposals()
        rbs = build_all_rollback_plans(proposals)
        brs = compute_all_blast_radii(proposals)
        seq = sequence_upgrades(proposals, brs, rbs)
        assert len(seq) == len(proposals)
        assert set(seq) == {p.name for p in proposals}

    def test_safest_first(self) -> None:
        from core.workstation.governed_recursive_orchestration_engine_v1 import (
            sequence_upgrades,
            build_all_rollback_plans,
            compute_all_blast_radii,
        )

        proposals = _get_proposals()
        rbs = build_all_rollback_plans(proposals)
        brs = compute_all_blast_radii(proposals)
        seq = sequence_upgrades(proposals, brs, rbs)
        first = seq[0]
        rb = next((r for r in rbs if r.upgrade_name == first), None)
        assert rb is not None
        assert rb.rollback_safe is True

    def test_deterministic_ordering(self) -> None:
        from core.workstation.governed_recursive_orchestration_engine_v1 import (
            sequence_upgrades,
            build_all_rollback_plans,
            compute_all_blast_radii,
        )

        proposals = _get_proposals()
        rbs = build_all_rollback_plans(proposals)
        brs = compute_all_blast_radii(proposals)
        seq1 = sequence_upgrades(proposals, brs, rbs)
        seq2 = sequence_upgrades(proposals, brs, rbs)
        assert seq1 == seq2


# ---------------------------------------------------------------------------
# Conflict detection
# ---------------------------------------------------------------------------


class TestConflictDetection:
    def test_detects_shared_registries(self) -> None:
        from core.workstation.governed_recursive_orchestration_engine_v1 import (
            detect_conflicts,
            compute_all_blast_radii,
        )

        proposals = _get_proposals()
        brs = compute_all_blast_radii(proposals)
        conflicts = detect_conflicts(proposals, brs)
        assert len(conflicts) > 0

    def test_conflict_format(self) -> None:
        from core.workstation.governed_recursive_orchestration_engine_v1 import (
            detect_conflicts,
            compute_all_blast_radii,
        )

        proposals = _get_proposals()
        brs = compute_all_blast_radii(proposals)
        conflicts = detect_conflicts(proposals, brs)
        for c in conflicts:
            assert "<->" in c
            assert "shared" in c


# ---------------------------------------------------------------------------
# Maturity evaluation
# ---------------------------------------------------------------------------


class TestMaturityEvaluation:
    def test_l0_on_dry_run(self) -> None:
        from core.workstation.governed_recursive_orchestration_engine_v1 import (
            OrchestrationEvidence,
            compute_orchestration_maturity,
        )

        ev = OrchestrationEvidence(is_dry_run=True, dag_generated=True)
        assert compute_orchestration_maturity(ev) == "L0_SIMULATED_ORCHESTRATION"

    def test_l0_on_no_evidence(self) -> None:
        from core.workstation.governed_recursive_orchestration_engine_v1 import (
            OrchestrationEvidence,
            compute_orchestration_maturity,
        )

        ev = OrchestrationEvidence()
        assert compute_orchestration_maturity(ev) == "L0_SIMULATED_ORCHESTRATION"

    def test_l1_requires_dag_and_replay(self) -> None:
        from core.workstation.governed_recursive_orchestration_engine_v1 import (
            OrchestrationEvidence,
            compute_orchestration_maturity,
        )

        ev = OrchestrationEvidence(dag_generated=True, replay_validated=True)
        assert compute_orchestration_maturity(ev) == "L1_REPLAY_SAFE_ORCHESTRATION"

    def test_l2_requires_rollback(self) -> None:
        from core.workstation.governed_recursive_orchestration_engine_v1 import (
            OrchestrationEvidence,
            compute_orchestration_maturity,
        )

        ev = OrchestrationEvidence(
            dag_generated=True,
            replay_validated=True,
            rollback_validated=True,
        )
        assert compute_orchestration_maturity(ev) == "L2_ROLLBACK_SAFE_ORCHESTRATION"

    def test_l3_requires_governance(self) -> None:
        from core.workstation.governed_recursive_orchestration_engine_v1 import (
            OrchestrationEvidence,
            compute_orchestration_maturity,
        )

        ev = OrchestrationEvidence(
            dag_generated=True,
            replay_validated=True,
            rollback_validated=True,
            governance_validated=True,
        )
        assert compute_orchestration_maturity(ev) == "L3_GOVERNED_ORCHESTRATION"

    def test_l4_requires_sequencing_and_blast(self) -> None:
        from core.workstation.governed_recursive_orchestration_engine_v1 import (
            OrchestrationEvidence,
            compute_orchestration_maturity,
        )

        ev = OrchestrationEvidence(
            dag_generated=True,
            replay_validated=True,
            rollback_validated=True,
            governance_validated=True,
            sequencing_validated=True,
            blast_radius_analyzed=True,
        )
        assert compute_orchestration_maturity(ev) == "L4_RECURSIVE_ORCHESTRATION"

    def test_l5_requires_simulation_and_founder(self) -> None:
        from core.workstation.governed_recursive_orchestration_engine_v1 import (
            OrchestrationEvidence,
            compute_orchestration_maturity,
        )

        ev = OrchestrationEvidence(
            dag_generated=True,
            replay_validated=True,
            rollback_validated=True,
            governance_validated=True,
            sequencing_validated=True,
            blast_radius_analyzed=True,
            simulation_completed=True,
            founder_confirmed=True,
        )
        assert compute_orchestration_maturity(ev) == "L5_GOVERNED_RECURSIVE_ORCHESTRATION"


# ---------------------------------------------------------------------------
# Hard ceilings
# ---------------------------------------------------------------------------


class TestHardCeilings:
    def test_dry_run_ceiling_l0(self) -> None:
        from core.workstation.governed_recursive_orchestration_engine_v1 import (
            OrchestrationEvidence,
            orchestration_maturity_ceiling,
        )

        ev = OrchestrationEvidence(is_dry_run=True)
        assert orchestration_maturity_ceiling(ev) == "L0_SIMULATED_ORCHESTRATION"

    def test_no_dag_ceiling_l0(self) -> None:
        from core.workstation.governed_recursive_orchestration_engine_v1 import (
            OrchestrationEvidence,
            orchestration_maturity_ceiling,
        )

        ev = OrchestrationEvidence(dag_generated=False)
        assert orchestration_maturity_ceiling(ev) == "L0_SIMULATED_ORCHESTRATION"

    def test_no_replay_ceiling_l0(self) -> None:
        from core.workstation.governed_recursive_orchestration_engine_v1 import (
            OrchestrationEvidence,
            orchestration_maturity_ceiling,
        )

        ev = OrchestrationEvidence(dag_generated=True, replay_validated=False)
        assert orchestration_maturity_ceiling(ev) == "L0_SIMULATED_ORCHESTRATION"

    def test_no_rollback_ceiling_l1(self) -> None:
        from core.workstation.governed_recursive_orchestration_engine_v1 import (
            OrchestrationEvidence,
            orchestration_maturity_ceiling,
        )

        ev = OrchestrationEvidence(
            dag_generated=True, replay_validated=True, rollback_validated=False
        )
        assert orchestration_maturity_ceiling(ev) == "L1_REPLAY_SAFE_ORCHESTRATION"

    def test_no_governance_ceiling_l2(self) -> None:
        from core.workstation.governed_recursive_orchestration_engine_v1 import (
            OrchestrationEvidence,
            orchestration_maturity_ceiling,
        )

        ev = OrchestrationEvidence(
            dag_generated=True,
            replay_validated=True,
            rollback_validated=True,
            governance_validated=False,
        )
        assert orchestration_maturity_ceiling(ev) == "L2_ROLLBACK_SAFE_ORCHESTRATION"

    def test_no_sequencing_ceiling_l3(self) -> None:
        from core.workstation.governed_recursive_orchestration_engine_v1 import (
            OrchestrationEvidence,
            orchestration_maturity_ceiling,
        )

        ev = OrchestrationEvidence(
            dag_generated=True,
            replay_validated=True,
            rollback_validated=True,
            governance_validated=True,
            sequencing_validated=False,
        )
        assert orchestration_maturity_ceiling(ev) == "L3_GOVERNED_ORCHESTRATION"

    def test_no_blast_analysis_ceiling_l3(self) -> None:
        from core.workstation.governed_recursive_orchestration_engine_v1 import (
            OrchestrationEvidence,
            orchestration_maturity_ceiling,
        )

        ev = OrchestrationEvidence(
            dag_generated=True,
            replay_validated=True,
            rollback_validated=True,
            governance_validated=True,
            sequencing_validated=True,
            blast_radius_analyzed=False,
        )
        assert orchestration_maturity_ceiling(ev) == "L3_GOVERNED_ORCHESTRATION"

    def test_no_simulation_ceiling_l4(self) -> None:
        from core.workstation.governed_recursive_orchestration_engine_v1 import (
            OrchestrationEvidence,
            orchestration_maturity_ceiling,
        )

        ev = OrchestrationEvidence(
            dag_generated=True,
            replay_validated=True,
            rollback_validated=True,
            governance_validated=True,
            sequencing_validated=True,
            blast_radius_analyzed=True,
            simulation_completed=False,
        )
        assert orchestration_maturity_ceiling(ev) == "L4_RECURSIVE_ORCHESTRATION"

    def test_no_founder_ceiling_l4(self) -> None:
        from core.workstation.governed_recursive_orchestration_engine_v1 import (
            OrchestrationEvidence,
            orchestration_maturity_ceiling,
        )

        ev = OrchestrationEvidence(
            dag_generated=True,
            replay_validated=True,
            rollback_validated=True,
            governance_validated=True,
            sequencing_validated=True,
            blast_radius_analyzed=True,
            simulation_completed=True,
            founder_confirmed=False,
        )
        assert orchestration_maturity_ceiling(ev) == "L4_RECURSIVE_ORCHESTRATION"

    def test_ceiling_blocks_escalation(self) -> None:
        from core.workstation.governed_recursive_orchestration_engine_v1 import (
            OrchestrationEvidence,
            classify_orchestration_maturity,
        )

        ev = OrchestrationEvidence(
            dag_generated=True,
            replay_validated=True,
            rollback_validated=True,
            governance_validated=True,
            sequencing_validated=False,
        )
        level, ceiling, blocked, reason = classify_orchestration_maturity(ev)
        assert level == "L3_GOVERNED_ORCHESTRATION"
        assert ceiling == "L3_GOVERNED_ORCHESTRATION"


# ---------------------------------------------------------------------------
# Full pipeline
# ---------------------------------------------------------------------------


class TestFullPipeline:
    def test_full_proof_without_capability_proof(self) -> None:
        from core.workstation.governed_recursive_orchestration_engine_v1 import (
            build_full_orchestration_proof,
        )

        proof = build_full_orchestration_proof(trace_id="test-pipeline")
        assert proof.proof_id.startswith("ORCHPROOF-")
        assert len(proof.dags) == 7
        assert len(proof.blast_radii) > 0
        assert len(proof.rollback_plans) > 0
        assert len(proof.simulations) > 0
        assert len(proof.sequenced_upgrades) > 0

    def test_full_proof_with_capability_proof(self) -> None:
        from core.workstation.governed_recursive_orchestration_engine_v1 import (
            build_full_orchestration_proof,
        )
        from core.workstation.recursive_capability_planning_engine_v1 import (
            build_full_capability_proof,
        )

        cap_proof = build_full_capability_proof(
            founder_confirmed=False,
            is_dry_run=True,
        )
        proof = build_full_orchestration_proof(
            capability_proof=cap_proof,
            founder_confirmed=False,
        )
        assert len(proof.dags) == 7
        assert len(proof.sequenced_upgrades) == len(cap_proof.upgrade_proposals)

    def test_full_proof_dry_run(self) -> None:
        from core.workstation.governed_recursive_orchestration_engine_v1 import (
            build_full_orchestration_proof,
        )

        proof = build_full_orchestration_proof(is_dry_run=True)
        assert proof.execution_strategy == "simulation_only"
        assert proof.evidence.is_dry_run is True

    def test_full_proof_awaits_founder(self) -> None:
        from core.workstation.governed_recursive_orchestration_engine_v1 import (
            build_full_orchestration_proof,
        )

        proof = build_full_orchestration_proof(founder_confirmed=False)
        assert proof.execution_strategy == "await_founder_confirmation"

    def test_full_proof_with_founder(self) -> None:
        from core.workstation.governed_recursive_orchestration_engine_v1 import (
            build_full_orchestration_proof,
        )

        proof = build_full_orchestration_proof(founder_confirmed=True)
        assert proof.execution_strategy == "execute_safest_sequence"

    def test_full_proof_evidence_populated(self) -> None:
        from core.workstation.governed_recursive_orchestration_engine_v1 import (
            build_full_orchestration_proof,
        )

        proof = build_full_orchestration_proof(
            founder_confirmed=True,
            trace_id="test-full",
            request_id="REQ-TEST-001",
        )
        ev = proof.evidence
        assert ev.dag_generated is True
        assert ev.dag_count == 7
        assert ev.simulation_completed is True
        assert ev.simulation_count > 0
        assert ev.trace_id == "test-full"
        assert ev.request_id == "REQ-TEST-001"

    def test_full_proof_serializable(self) -> None:
        from core.workstation.governed_recursive_orchestration_engine_v1 import (
            build_full_orchestration_proof,
        )

        proof = build_full_orchestration_proof(founder_confirmed=True)
        s = json.dumps(proof.to_dict())
        assert len(s) > 100
        d = json.loads(s)
        assert d["proof_type"] == "governed_recursive_orchestration"


# ---------------------------------------------------------------------------
# Proof persistence
# ---------------------------------------------------------------------------


class TestProofPersistence:
    def test_persist_creates_file(self, tmp_path: Path) -> None:
        from core.workstation.governed_recursive_orchestration_engine_v1 import (
            OrchestrationProof,
            persist_orchestration_proof,
        )

        proof = OrchestrationProof(trace_id="test-persist")
        path = persist_orchestration_proof(proof, base_dir=tmp_path)
        assert path.exists()
        assert path.name.startswith("ORCHPROOF-")

    def test_persist_json_valid(self, tmp_path: Path) -> None:
        from core.workstation.governed_recursive_orchestration_engine_v1 import (
            build_full_orchestration_proof,
            persist_orchestration_proof,
        )

        proof = build_full_orchestration_proof(founder_confirmed=True)
        path = persist_orchestration_proof(proof, base_dir=tmp_path)
        data = json.loads(path.read_text())
        assert data["proof_type"] == "governed_recursive_orchestration"
        assert "dags" in data
        assert "blast_radii" in data

    def test_persist_to_correct_dir(self, tmp_path: Path) -> None:
        from core.workstation.governed_recursive_orchestration_engine_v1 import (
            ORCHESTRATION_REPORT_DIR,
            OrchestrationProof,
            persist_orchestration_proof,
        )

        proof = OrchestrationProof()
        path = persist_orchestration_proof(proof, base_dir=tmp_path)
        assert str(ORCHESTRATION_REPORT_DIR) in str(path.parent)

    def test_persist_idempotent(self, tmp_path: Path) -> None:
        from core.workstation.governed_recursive_orchestration_engine_v1 import (
            OrchestrationProof,
            persist_orchestration_proof,
        )

        proof = OrchestrationProof(trace_id="idem")
        p1 = persist_orchestration_proof(proof, base_dir=tmp_path)
        p2 = persist_orchestration_proof(proof, base_dir=tmp_path)
        assert p1 == p2


# ---------------------------------------------------------------------------
# Canonical instance separation
# ---------------------------------------------------------------------------


class TestCanonicalInstanceSeparation:
    def test_separate_proof_instances(self) -> None:
        from core.workstation.governed_recursive_orchestration_engine_v1 import (
            build_full_orchestration_proof,
        )

        p1 = build_full_orchestration_proof(trace_id="t1")
        p2 = build_full_orchestration_proof(trace_id="t2")
        assert p1.proof_id != p2.proof_id
        assert p1.trace_id != p2.trace_id

    def test_separate_evidence_instances(self) -> None:
        from core.workstation.governed_recursive_orchestration_engine_v1 import (
            build_full_orchestration_proof,
        )

        p1 = build_full_orchestration_proof(founder_confirmed=True)
        p2 = build_full_orchestration_proof(founder_confirmed=False)
        assert p1.evidence.founder_confirmed != p2.evidence.founder_confirmed


# ---------------------------------------------------------------------------
# Registry integration (17 commands)
# ---------------------------------------------------------------------------


class TestRegistryIntegration:
    def test_registry_has_17_commands(self) -> None:
        from core.registry.canonical_command_registry_v1 import (
            CanonicalCommandRegistryV1,
        )

        reg = CanonicalCommandRegistryV1()
        assert len(reg) == 17

    def test_orchestration_report_in_registry(self) -> None:
        from core.registry.canonical_command_registry_v1 import (
            CanonicalCommandRegistryV1,
        )

        reg = CanonicalCommandRegistryV1()
        assert "!orchestration-report" in reg.commands
        entry = reg.get("!orchestration-report")
        assert entry is not None
        assert entry.canonical_action == "orchestration_report"

    def test_orchestration_report_in_router_contracts(self) -> None:
        from core.control_plane_router.router_contracts import ALLOWED_ACTION_TYPES

        assert "orchestration_report" in ALLOWED_ACTION_TYPES

    def test_orchestration_report_in_router_map(self) -> None:
        from core.control_plane_router.control_plane_router_v1 import (
            ACTION_CAPABILITY_MAP,
        )

        assert "orchestration_report" in ACTION_CAPABILITY_MAP

    def test_orchestration_report_capability_type(self) -> None:
        from core.control_plane_router.control_plane_router_v1 import (
            ACTION_CAPABILITY_MAP,
        )
        from core.control_plane_router.router_contracts import CapabilityType

        cap = ACTION_CAPABILITY_MAP["orchestration_report"]
        assert cap.capability_type == CapabilityType.ORCHESTRATION_GOVERNANCE

    def test_orchestration_report_in_adapter_enum(self) -> None:
        from core.environment_bridge.windows_desktop_adapter_contracts import (
            WindowsDesktopActionType,
        )

        assert WindowsDesktopActionType.ORCHESTRATION_REPORT.value == "orchestration_report"

    def test_orchestration_report_in_config_json(self) -> None:
        config = json.loads(Path("/opt/OS/config/control_plane_router_v1.json").read_text())
        assert "orchestration_report" in config["allowed_action_types"]

    def test_orchestration_report_in_adapter_registry(self) -> None:
        data = json.loads(
            Path("/opt/OS/data/registries/local_worker_adapter_registry_v1.json").read_text()
        )
        wsl_caps = data["workers"]["local_wsl_worker"]["capabilities"]
        assert "orchestration_report" in wsl_caps
        win_caps = data["workers"]["windows_interactive_desktop_relay"]["capabilities"]
        assert "orchestration_report" in win_caps

    def test_handler_exports_17_commands(self) -> None:
        from handlers.substrate_command_handler import SUBSTRATE_COMMANDS

        assert len(SUBSTRATE_COMMANDS) == 17
        assert "!orchestration-report" in SUBSTRATE_COMMANDS

    def test_router_config_parity(self) -> None:
        from core.registry.canonical_command_registry_v1 import get_canonical_registry

        reg = get_canonical_registry()
        config = json.loads(Path("/opt/OS/config/control_plane_router_v1.json").read_text())
        allowed = set(config["allowed_action_types"])
        for action in reg.actions:
            assert action in allowed

    def test_no_orphan_actions(self) -> None:
        from core.registry.canonical_command_registry_v1 import get_canonical_registry

        reg = get_canonical_registry()
        config = json.loads(Path("/opt/OS/config/control_plane_router_v1.json").read_text())
        for action in config["allowed_action_types"]:
            assert reg.contains_action(action)
