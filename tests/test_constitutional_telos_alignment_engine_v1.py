"""Tests for constitutional_telos_alignment_engine_v1."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

import os
sys.path.insert(0, os.environ.get("UMH_ROOT") or os.environ.get("OS_ROOT") or os.environ.get("EOS_ROOT") or "/opt/OS")
_ROOT = os.environ.get("UMH_ROOT") or os.environ.get("OS_ROOT") or os.environ.get("EOS_ROOT") or "/opt/OS"
sys.path.insert(0, os.path.join(os.environ.get("UMH_ROOT") or os.environ.get("OS_ROOT") or os.environ.get("EOS_ROOT") or "/opt/OS", "services"))


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------


class TestTelosConstants:
    def test_maturity_levels_count(self) -> None:
        from execution.workers.workstation.constitutional_telos_alignment_engine_v1 import (
            TELOS_MATURITY_LEVELS,
        )

        assert len(TELOS_MATURITY_LEVELS) == 6

    def test_maturity_levels_order(self) -> None:
        from execution.workers.workstation.constitutional_telos_alignment_engine_v1 import (
            TELOS_MATURITY_LEVELS,
        )

        assert TELOS_MATURITY_LEVELS[0] == "L0_NO_TELOS_ALIGNMENT"
        assert TELOS_MATURITY_LEVELS[5] == "L5_CONSTITUTIONAL_TELOS_ALIGNMENT"

    def test_primitives_count(self) -> None:
        from execution.workers.workstation.constitutional_telos_alignment_engine_v1 import (
            TELOS_PRIMITIVES,
        )

        assert len(TELOS_PRIMITIVES) == 10

    def test_mission_dimensions_count(self) -> None:
        from execution.workers.workstation.constitutional_telos_alignment_engine_v1 import (
            MISSION_CONTINUITY_DIMENSIONS,
        )

        assert len(MISSION_CONTINUITY_DIMENSIONS) == 8

    def test_optimization_direction_count(self) -> None:
        from execution.workers.workstation.constitutional_telos_alignment_engine_v1 import (
            OPTIMIZATION_DIRECTION_TYPES,
        )

        assert len(OPTIMIZATION_DIRECTION_TYPES) == 8

    def test_value_hierarchy_count(self) -> None:
        from execution.workers.workstation.constitutional_telos_alignment_engine_v1 import (
            VALUE_HIERARCHY_TYPES,
        )

        assert len(VALUE_HIERARCHY_TYPES) == 8

    def test_purpose_conflict_count(self) -> None:
        from execution.workers.workstation.constitutional_telos_alignment_engine_v1 import (
            PURPOSE_CONFLICT_TYPES,
        )

        assert len(PURPOSE_CONFLICT_TYPES) == 7

    def test_topology_types_count(self) -> None:
        from execution.workers.workstation.constitutional_telos_alignment_engine_v1 import (
            ALIGNMENT_TOPOLOGY_TYPES,
        )

        assert len(ALIGNMENT_TOPOLOGY_TYPES) == 7

    def test_hard_ceilings_count(self) -> None:
        from execution.workers.workstation.constitutional_telos_alignment_engine_v1 import (
            TELOS_HARD_CEILINGS,
        )

        assert len(TELOS_HARD_CEILINGS) == 7

    def test_adaptation_types_count(self) -> None:
        from execution.workers.workstation.constitutional_telos_alignment_engine_v1 import (
            TELOS_ADAPTATION_TYPES,
        )

        assert len(TELOS_ADAPTATION_TYPES) == 6


# ---------------------------------------------------------------------------
# Dataclasses
# ---------------------------------------------------------------------------


class TestTelosPrimitive:
    def test_default(self) -> None:
        from execution.workers.workstation.constitutional_telos_alignment_engine_v1 import (
            TelosPrimitive,
        )

        p = TelosPrimitive()
        assert p.confidence == 0.0
        assert p.stability == 0.0
        assert p.alignment_score == 0.0

    def test_to_dict_serializable(self) -> None:
        from execution.workers.workstation.constitutional_telos_alignment_engine_v1 import (
            TelosPrimitive,
        )

        p = TelosPrimitive(primitive="test", confidence=0.5)
        d = p.to_dict()
        json.dumps(d)
        assert d["primitive"] == "test"


class TestTelosPrimitiveSet:
    def test_auto_timestamp(self) -> None:
        from execution.workers.workstation.constitutional_telos_alignment_engine_v1 import (
            TelosPrimitiveSet,
        )

        s = TelosPrimitiveSet()
        assert s.timestamp != ""

    def test_to_dict(self) -> None:
        from execution.workers.workstation.constitutional_telos_alignment_engine_v1 import (
            TelosPrimitiveSet,
        )

        s = TelosPrimitiveSet()
        d = s.to_dict()
        json.dumps(d)


class TestMissionContinuityDimension:
    def test_default(self) -> None:
        from execution.workers.workstation.constitutional_telos_alignment_engine_v1 import (
            MissionContinuityDimension,
        )

        m = MissionContinuityDimension()
        assert m.alignment_score == 0.0
        assert m.continuity_intact is True

    def test_to_dict(self) -> None:
        from execution.workers.workstation.constitutional_telos_alignment_engine_v1 import (
            MissionContinuityDimension,
        )

        m = MissionContinuityDimension(dimension="test", alignment_score=0.8)
        d = m.to_dict()
        assert d["dimension"] == "test"


class TestOptimizationDirectionDetection:
    def test_default(self) -> None:
        from execution.workers.workstation.constitutional_telos_alignment_engine_v1 import (
            OptimizationDirectionDetection,
        )

        d = OptimizationDirectionDetection()
        assert d.drift_detected is False
        assert d.severity == "low"

    def test_to_dict(self) -> None:
        from execution.workers.workstation.constitutional_telos_alignment_engine_v1 import (
            OptimizationDirectionDetection,
        )

        d = OptimizationDirectionDetection(direction_type="test", severity="high")
        result = d.to_dict()
        assert result["severity"] == "high"


class TestValueHierarchyEntry:
    def test_default(self) -> None:
        from execution.workers.workstation.constitutional_telos_alignment_engine_v1 import (
            ValueHierarchyEntry,
        )

        v = ValueHierarchyEntry()
        assert v.enforced is True
        assert v.weight == 0.0

    def test_to_dict(self) -> None:
        from execution.workers.workstation.constitutional_telos_alignment_engine_v1 import (
            ValueHierarchyEntry,
        )

        v = ValueHierarchyEntry(hierarchy_type="test", weight=0.5)
        d = v.to_dict()
        assert d["hierarchy_type"] == "test"


class TestPurposeConflict:
    def test_default(self) -> None:
        from execution.workers.workstation.constitutional_telos_alignment_engine_v1 import (
            PurposeConflict,
        )

        c = PurposeConflict()
        assert c.conflict_detected is False
        assert c.severity == 0.0

    def test_to_dict(self) -> None:
        from execution.workers.workstation.constitutional_telos_alignment_engine_v1 import (
            PurposeConflict,
        )

        c = PurposeConflict(conflict_type="test", severity=0.3)
        d = c.to_dict()
        assert d["conflict_type"] == "test"


class TestAlignmentTopologyNode:
    def test_default(self) -> None:
        from execution.workers.workstation.constitutional_telos_alignment_engine_v1 import (
            AlignmentTopologyNode,
        )

        n = AlignmentTopologyNode()
        assert n.connections == 0
        assert n.alignment == 0.0

    def test_to_dict(self) -> None:
        from execution.workers.workstation.constitutional_telos_alignment_engine_v1 import (
            AlignmentTopologyNode,
        )

        n = AlignmentTopologyNode(node_id="n1", topology_type="test")
        d = n.to_dict()
        assert d["node_id"] == "n1"


class TestAlignmentTopology:
    def test_auto_hash(self) -> None:
        from execution.workers.workstation.constitutional_telos_alignment_engine_v1 import (
            AlignmentTopology,
            AlignmentTopologyNode,
        )

        t = AlignmentTopology(nodes=[AlignmentTopologyNode(node_id="n1", topology_type="test")])
        assert t.topology_hash != ""

    def test_hash_deterministic(self) -> None:
        from execution.workers.workstation.constitutional_telos_alignment_engine_v1 import (
            AlignmentTopology,
            AlignmentTopologyNode,
        )

        nodes = [AlignmentTopologyNode(node_id="n1", topology_type="test", alignment=0.5)]
        t1 = AlignmentTopology(nodes=list(nodes), topology_hash="")
        t2 = AlignmentTopology(nodes=list(nodes), topology_hash="")
        assert t1.topology_hash == t2.topology_hash


class TestTelosAdaptation:
    def test_default_invariants_preserved(self) -> None:
        from execution.workers.workstation.constitutional_telos_alignment_engine_v1 import (
            TelosAdaptation,
        )

        a = TelosAdaptation()
        assert a.invariants_preserved is True

    def test_to_dict(self) -> None:
        from execution.workers.workstation.constitutional_telos_alignment_engine_v1 import (
            TelosAdaptation,
        )

        a = TelosAdaptation(adaptation_type="test")
        d = a.to_dict()
        assert d["adaptation_type"] == "test"


class TestTelosEvidence:
    def test_field_count(self) -> None:
        from execution.workers.workstation.constitutional_telos_alignment_engine_v1 import (
            TelosEvidence,
        )

        ev = TelosEvidence()
        d = ev.to_dict()
        assert len(d) == 40

    def test_to_dict_serializable(self) -> None:
        from execution.workers.workstation.constitutional_telos_alignment_engine_v1 import (
            TelosEvidence,
        )

        ev = TelosEvidence()
        json.dumps(ev.to_dict())


class TestTelosProof:
    def test_auto_proof_id(self) -> None:
        from execution.workers.workstation.constitutional_telos_alignment_engine_v1 import (
            TelosProof,
        )

        p = TelosProof()
        assert p.proof_id.startswith("TELS-")

    def test_to_dict_serializable(self) -> None:
        from execution.workers.workstation.constitutional_telos_alignment_engine_v1 import (
            TelosEvidence,
            TelosProof,
        )

        p = TelosProof(evidence=TelosEvidence())
        json.dumps(p.to_dict(), default=str)


# ---------------------------------------------------------------------------
# Builders
# ---------------------------------------------------------------------------


class TestBuildTelosPrimitives:
    def test_produces_10_primitives(self) -> None:
        from execution.workers.workstation.constitutional_telos_alignment_engine_v1 import (
            build_telos_primitives,
        )

        result = build_telos_primitives()
        assert len(result.primitives) == 10

    def test_composite_confidence_positive(self) -> None:
        from execution.workers.workstation.constitutional_telos_alignment_engine_v1 import (
            build_telos_primitives,
        )

        result = build_telos_primitives()
        assert result.composite_confidence > 0

    def test_all_primitives_named(self) -> None:
        from execution.workers.workstation.constitutional_telos_alignment_engine_v1 import (
            build_telos_primitives,
            TELOS_PRIMITIVES,
        )

        result = build_telos_primitives()
        names = {p.primitive for p in result.primitives}
        assert names == set(TELOS_PRIMITIVES)


class TestBuildMissionContinuity:
    def test_produces_8_dimensions(self) -> None:
        from execution.workers.workstation.constitutional_telos_alignment_engine_v1 import (
            build_telos_primitives,
            build_mission_continuity,
        )

        prims = build_telos_primitives()
        result = build_mission_continuity(prims)
        assert len(result.dimensions) == 8

    def test_composite_alignment_between_0_and_1(self) -> None:
        from execution.workers.workstation.constitutional_telos_alignment_engine_v1 import (
            build_telos_primitives,
            build_mission_continuity,
        )

        prims = build_telos_primitives()
        result = build_mission_continuity(prims)
        assert 0 <= result.composite_alignment <= 1


class TestBuildOptimizationDirection:
    def test_produces_8_detections(self) -> None:
        from execution.workers.workstation.constitutional_telos_alignment_engine_v1 import (
            build_telos_primitives,
            build_mission_continuity,
            build_optimization_direction,
        )

        prims = build_telos_primitives()
        mission = build_mission_continuity(prims)
        result = build_optimization_direction(prims, mission)
        assert len(result.detections) == 8

    def test_all_types_covered(self) -> None:
        from execution.workers.workstation.constitutional_telos_alignment_engine_v1 import (
            build_telos_primitives,
            build_mission_continuity,
            build_optimization_direction,
            OPTIMIZATION_DIRECTION_TYPES,
        )

        prims = build_telos_primitives()
        mission = build_mission_continuity(prims)
        result = build_optimization_direction(prims, mission)
        types = {d.direction_type for d in result.detections}
        assert types == set(OPTIMIZATION_DIRECTION_TYPES)


class TestBuildValueHierarchy:
    def test_produces_8_entries(self) -> None:
        from execution.workers.workstation.constitutional_telos_alignment_engine_v1 import (
            build_telos_primitives,
            build_mission_continuity,
            build_optimization_direction,
            build_value_hierarchy,
        )

        prims = build_telos_primitives()
        mission = build_mission_continuity(prims)
        optim = build_optimization_direction(prims, mission)
        result = build_value_hierarchy(prims, mission, optim)
        assert len(result.entries) == 8

    def test_composite_stability_positive(self) -> None:
        from execution.workers.workstation.constitutional_telos_alignment_engine_v1 import (
            build_telos_primitives,
            build_mission_continuity,
            build_optimization_direction,
            build_value_hierarchy,
        )

        prims = build_telos_primitives()
        mission = build_mission_continuity(prims)
        optim = build_optimization_direction(prims, mission)
        result = build_value_hierarchy(prims, mission, optim)
        assert result.composite_stability > 0


class TestBuildPurposeConflicts:
    def test_produces_7_conflicts(self) -> None:
        from execution.workers.workstation.constitutional_telos_alignment_engine_v1 import (
            build_telos_primitives,
            build_mission_continuity,
            build_optimization_direction,
            build_value_hierarchy,
            build_purpose_conflicts,
        )

        prims = build_telos_primitives()
        mission = build_mission_continuity(prims)
        optim = build_optimization_direction(prims, mission)
        vh = build_value_hierarchy(prims, mission, optim)
        result = build_purpose_conflicts(mission, optim, vh)
        assert len(result.conflicts) == 7

    def test_all_types_covered(self) -> None:
        from execution.workers.workstation.constitutional_telos_alignment_engine_v1 import (
            build_telos_primitives,
            build_mission_continuity,
            build_optimization_direction,
            build_value_hierarchy,
            build_purpose_conflicts,
            PURPOSE_CONFLICT_TYPES,
        )

        prims = build_telos_primitives()
        mission = build_mission_continuity(prims)
        optim = build_optimization_direction(prims, mission)
        vh = build_value_hierarchy(prims, mission, optim)
        result = build_purpose_conflicts(mission, optim, vh)
        types = {c.conflict_type for c in result.conflicts}
        assert types == set(PURPOSE_CONFLICT_TYPES)


class TestBuildAlignmentTopology:
    def test_covers_7_types(self) -> None:
        from execution.workers.workstation.constitutional_telos_alignment_engine_v1 import (
            build_telos_primitives,
            build_mission_continuity,
            build_optimization_direction,
            build_value_hierarchy,
            build_alignment_topology,
        )

        prims = build_telos_primitives()
        mission = build_mission_continuity(prims)
        optim = build_optimization_direction(prims, mission)
        vh = build_value_hierarchy(prims, mission, optim)
        result = build_alignment_topology(prims, mission, optim, vh)
        assert result.topology_types_covered == 7

    def test_hash_not_empty(self) -> None:
        from execution.workers.workstation.constitutional_telos_alignment_engine_v1 import (
            build_telos_primitives,
            build_mission_continuity,
            build_optimization_direction,
            build_value_hierarchy,
            build_alignment_topology,
        )

        prims = build_telos_primitives()
        mission = build_mission_continuity(prims)
        optim = build_optimization_direction(prims, mission)
        vh = build_value_hierarchy(prims, mission, optim)
        result = build_alignment_topology(prims, mission, optim, vh)
        assert result.topology_hash != ""


class TestBuildTelosAdaptations:
    def test_produces_6_adaptations(self) -> None:
        from execution.workers.workstation.constitutional_telos_alignment_engine_v1 import (
            build_telos_primitives,
            build_mission_continuity,
            build_optimization_direction,
            build_value_hierarchy,
            build_purpose_conflicts,
            build_telos_adaptations,
        )

        prims = build_telos_primitives()
        mission = build_mission_continuity(prims)
        optim = build_optimization_direction(prims, mission)
        vh = build_value_hierarchy(prims, mission, optim)
        conflicts = build_purpose_conflicts(mission, optim, vh)
        result = build_telos_adaptations(optim, conflicts, mission, prims)
        assert len(result.adaptations) == 6

    def test_invariants_preserved(self) -> None:
        from execution.workers.workstation.constitutional_telos_alignment_engine_v1 import (
            build_telos_primitives,
            build_mission_continuity,
            build_optimization_direction,
            build_value_hierarchy,
            build_purpose_conflicts,
            build_telos_adaptations,
        )

        prims = build_telos_primitives()
        mission = build_mission_continuity(prims)
        optim = build_optimization_direction(prims, mission)
        vh = build_value_hierarchy(prims, mission, optim)
        conflicts = build_purpose_conflicts(mission, optim, vh)
        result = build_telos_adaptations(optim, conflicts, mission, prims)
        assert result.all_invariants_preserved is True


class TestEnforceTelosHardCeilings:
    def test_no_violation_on_clean(self) -> None:
        from execution.workers.workstation.constitutional_telos_alignment_engine_v1 import (
            TelosPrimitiveSet,
            OptimizationDirectionAnalysis,
            PurposeConflictAnalysis,
            TelosAdaptationSet,
            enforce_telos_hard_ceilings,
        )

        prims = TelosPrimitiveSet(
            composite_confidence=0.75,
            composite_stability=0.7,
            composite_alignment=0.7,
        )
        optim = OptimizationDirectionAnalysis(
            critical_drift_count=0, total_drift_count=0, composite_drift=0.0
        )
        conflicts = PurposeConflictAnalysis(unreconciled_count=0)
        adapts = TelosAdaptationSet(all_invariants_preserved=True)
        blocked, reasons = enforce_telos_hard_ceilings(prims, optim, conflicts, adapts)
        assert blocked is False
        assert len(reasons) == 0

    def test_invariant_violation_blocks(self) -> None:
        from execution.workers.workstation.constitutional_telos_alignment_engine_v1 import (
            TelosPrimitiveSet,
            OptimizationDirectionAnalysis,
            PurposeConflictAnalysis,
            TelosAdaptationSet,
            TelosAdaptation,
            enforce_telos_hard_ceilings,
        )

        prims = TelosPrimitiveSet(
            composite_confidence=0.1,
            composite_stability=0.1,
            composite_alignment=0.1,
        )
        optim = OptimizationDirectionAnalysis(
            critical_drift_count=3,
            total_drift_count=5,
            composite_drift=0.4,
        )
        conflicts = PurposeConflictAnalysis(unreconciled_count=4)
        adapts = TelosAdaptationSet(
            adaptations=[TelosAdaptation(invariants_preserved=False)],
            all_invariants_preserved=False,
        )
        blocked, reasons = enforce_telos_hard_ceilings(prims, optim, conflicts, adapts)
        assert blocked is True
        assert "unconstitutional_optimization" in reasons
        assert "mission_breaking_recursion" in reasons
        assert "unstable_value_evolution" in reasons
        assert "identity_purpose_divergence" in reasons
        assert "governance_purpose_contradiction" in reasons
        assert "alignment_breaking_leverage_accumulation" in reasons
        assert "civilization_scale_objective_instability" in reasons


# ---------------------------------------------------------------------------
# Maturity
# ---------------------------------------------------------------------------


class TestComputeTelosMaturity:
    def test_empty_evidence_low_score(self) -> None:
        from execution.workers.workstation.constitutional_telos_alignment_engine_v1 import (
            TelosEvidence,
            compute_telos_maturity,
        )

        ev = TelosEvidence(
            all_invariants_preserved=False,
            hard_ceilings_enforced=False,
            telos_constitutionally_safe=False,
            purpose_coherent=False,
        )
        assert compute_telos_maturity(ev) == 0

    def test_full_evidence_high_score(self) -> None:
        from execution.workers.workstation.constitutional_telos_alignment_engine_v1 import (
            TelosEvidence,
            compute_telos_maturity,
        )

        ev = TelosEvidence(
            primitives_evaluated=True,
            mission_analyzed=True,
            optimization_analyzed=True,
            value_hierarchy_analyzed=True,
            conflicts_analyzed=True,
            topology_generated=True,
            adaptations_applied=True,
            all_invariants_preserved=True,
            hard_ceilings_enforced=True,
            telos_constitutionally_safe=True,
            purpose_coherent=True,
        )
        assert compute_telos_maturity(ev) == 10


class TestTelosMaturityCeiling:
    def test_dry_run_l0(self) -> None:
        from execution.workers.workstation.constitutional_telos_alignment_engine_v1 import (
            TelosEvidence,
            telos_maturity_ceiling,
        )

        ev = TelosEvidence(is_dry_run=True, primitives_evaluated=True)
        assert telos_maturity_ceiling(ev) == "L0_NO_TELOS_ALIGNMENT"

    def test_no_primitives_l0(self) -> None:
        from execution.workers.workstation.constitutional_telos_alignment_engine_v1 import (
            TelosEvidence,
            telos_maturity_ceiling,
        )

        ev = TelosEvidence(primitives_evaluated=False)
        assert telos_maturity_ceiling(ev) == "L0_NO_TELOS_ALIGNMENT"

    def test_full_evidence_l5(self) -> None:
        from execution.workers.workstation.constitutional_telos_alignment_engine_v1 import (
            TelosEvidence,
            telos_maturity_ceiling,
        )

        ev = TelosEvidence(
            primitives_evaluated=True,
            mission_analyzed=True,
            value_hierarchy_analyzed=True,
            conflicts_analyzed=True,
            founder_confirmed=True,
        )
        assert telos_maturity_ceiling(ev) == "L5_CONSTITUTIONAL_TELOS_ALIGNMENT"

    def test_no_founder_capped_l4(self) -> None:
        from execution.workers.workstation.constitutional_telos_alignment_engine_v1 import (
            TelosEvidence,
            telos_maturity_ceiling,
        )

        ev = TelosEvidence(
            primitives_evaluated=True,
            mission_analyzed=True,
            value_hierarchy_analyzed=True,
            conflicts_analyzed=True,
            founder_confirmed=False,
        )
        assert telos_maturity_ceiling(ev) == "L4_TELOS_RECONCILED"


class TestClassifyTelosMaturity:
    def test_empty_l0(self) -> None:
        from execution.workers.workstation.constitutional_telos_alignment_engine_v1 import (
            TelosEvidence,
            classify_telos_maturity,
        )

        ev = TelosEvidence(
            all_invariants_preserved=False,
            hard_ceilings_enforced=False,
            telos_constitutionally_safe=False,
            purpose_coherent=False,
        )
        level, ceiling, blocked, reason = classify_telos_maturity(ev)
        assert level == "L0_NO_TELOS_ALIGNMENT"


# ---------------------------------------------------------------------------
# Full pipeline
# ---------------------------------------------------------------------------


class TestBuildFullTelosProof:
    def test_no_upstream(self) -> None:
        from execution.workers.workstation.constitutional_telos_alignment_engine_v1 import (
            build_full_telos_proof,
        )

        proof = build_full_telos_proof()
        assert proof.proof_id.startswith("TELS-")
        assert proof.evidence is not None
        assert proof.evidence.primitives_evaluated is True

    def test_dry_run(self) -> None:
        from execution.workers.workstation.constitutional_telos_alignment_engine_v1 import (
            build_full_telos_proof,
        )

        proof = build_full_telos_proof(is_dry_run=True)
        assert proof.maturity_level == "L0_NO_TELOS_ALIGNMENT"
        assert proof.execution_strategy == "telos_alignment_dry_run"

    def test_founder_telos(self) -> None:
        from execution.workers.workstation.constitutional_telos_alignment_engine_v1 import (
            build_full_telos_proof,
        )

        proof = build_full_telos_proof(founder_confirmed=True)
        assert proof.evidence.founder_confirmed is True

    def test_with_full_upstream_chain(self) -> None:
        from execution.workers.workstation.constitutional_telos_alignment_engine_v1 import (
            build_full_telos_proof,
        )
        from execution.workers.workstation.constitutional_identity_continuity_engine_v1 import (
            build_full_identity_proof,
        )
        from execution.workers.workstation.constitutional_epistemic_intelligence_engine_v1 import (
            build_full_epistemic_proof,
        )
        from execution.workers.workstation.constitutional_strategic_intelligence_engine_v1 import (
            build_full_strategy_proof,
        )
        from execution.workers.workstation.constitutional_resource_economics_engine_v1 import (
            build_full_economics_proof,
        )
        from execution.workers.workstation.distributed_constitutional_substrate_federation_v1 import (
            build_full_federation_proof,
        )
        from execution.workers.workstation.governed_recursive_orchestration_engine_v1 import (
            build_full_orchestration_proof,
        )
        from execution.workers.workstation.recursive_capability_planning_engine_v1 import (
            build_full_capability_proof,
        )

        cap = build_full_capability_proof()
        orch = build_full_orchestration_proof(capability_proof=cap)
        fed = build_full_federation_proof(orchestration_proof=orch, capability_proof=cap)
        econ = build_full_economics_proof(
            federation_proof=fed, orchestration_proof=orch, capability_proof=cap
        )
        strat = build_full_strategy_proof(
            economics_proof=econ,
            federation_proof=fed,
            orchestration_proof=orch,
            capability_proof=cap,
            founder_confirmed=True,
        )
        epis = build_full_epistemic_proof(
            strategy_proof=strat,
            economics_proof=econ,
            federation_proof=fed,
            orchestration_proof=orch,
            capability_proof=cap,
            founder_confirmed=True,
        )
        iden = build_full_identity_proof(
            epistemic_proof=epis,
            strategy_proof=strat,
            economics_proof=econ,
            federation_proof=fed,
            orchestration_proof=orch,
            capability_proof=cap,
            founder_confirmed=True,
        )

        proof = build_full_telos_proof(
            identity_proof=iden,
            epistemic_proof=epis,
            strategy_proof=strat,
            economics_proof=econ,
            federation_proof=fed,
            orchestration_proof=orch,
            capability_proof=cap,
            founder_confirmed=True,
        )
        assert proof.maturity_level != "L0_NO_TELOS_ALIGNMENT"
        assert proof.evidence.primitive_count == 10
        assert proof.evidence.mission_analyzed is True
        assert proof.evidence.optimization_analyzed is True
        assert proof.evidence.value_hierarchy_analyzed is True
        assert proof.evidence.conflicts_analyzed is True


# ---------------------------------------------------------------------------
# Persistence
# ---------------------------------------------------------------------------


class TestPersistTelosProof:
    def test_persist_creates_file(self, tmp_path: Path) -> None:
        from execution.workers.workstation.constitutional_telos_alignment_engine_v1 import (
            build_full_telos_proof,
            persist_telos_proof,
        )

        proof = build_full_telos_proof(trace_id="persist-test")
        path = persist_telos_proof(proof, base_dir=tmp_path)
        assert path.exists()
        assert path.name.startswith("TELS-")
        data = json.loads(path.read_text())
        assert data["proof_type"] == "constitutional_telos_alignment"

    def test_persist_json_valid(self, tmp_path: Path) -> None:
        from execution.workers.workstation.constitutional_telos_alignment_engine_v1 import (
            build_full_telos_proof,
            persist_telos_proof,
        )

        proof = build_full_telos_proof()
        path = persist_telos_proof(proof, base_dir=tmp_path)
        data = json.loads(path.read_text())
        assert "evidence" in data
        assert "primitives" in data
        assert "conflicts" in data


# ---------------------------------------------------------------------------
# Mission drift detection
# ---------------------------------------------------------------------------


class TestMissionDriftDetection:
    def test_mission_drift_logic(self) -> None:
        from execution.workers.workstation.constitutional_telos_alignment_engine_v1 import (
            build_full_telos_proof,
        )

        proof = build_full_telos_proof()
        ev = proof.evidence
        expected = ev.critical_optimization_drift == 0 and ev.all_invariants_preserved
        assert ev.purpose_coherent is expected


# ---------------------------------------------------------------------------
# Recursive alignment stability
# ---------------------------------------------------------------------------


class TestRecursiveAlignmentStability:
    def test_alignment_with_federation(self) -> None:
        from execution.workers.workstation.constitutional_telos_alignment_engine_v1 import (
            build_full_telos_proof,
        )
        from execution.workers.workstation.distributed_constitutional_substrate_federation_v1 import (
            build_full_federation_proof,
        )
        from execution.workers.workstation.governed_recursive_orchestration_engine_v1 import (
            build_full_orchestration_proof,
        )
        from execution.workers.workstation.recursive_capability_planning_engine_v1 import (
            build_full_capability_proof,
        )

        cap = build_full_capability_proof()
        orch = build_full_orchestration_proof(capability_proof=cap)
        fed = build_full_federation_proof(orchestration_proof=orch, capability_proof=cap)
        proof = build_full_telos_proof(
            federation_proof=fed, orchestration_proof=orch, capability_proof=cap
        )
        assert proof.evidence is not None


# ---------------------------------------------------------------------------
# Value hierarchy consistency
# ---------------------------------------------------------------------------


class TestValueHierarchyConsistency:
    def test_all_types_present(self) -> None:
        from execution.workers.workstation.constitutional_telos_alignment_engine_v1 import (
            build_telos_primitives,
            build_mission_continuity,
            build_optimization_direction,
            build_value_hierarchy,
            VALUE_HIERARCHY_TYPES,
        )

        prims = build_telos_primitives()
        mission = build_mission_continuity(prims)
        optim = build_optimization_direction(prims, mission)
        vh = build_value_hierarchy(prims, mission, optim)
        types = {e.hierarchy_type for e in vh.entries}
        assert types == set(VALUE_HIERARCHY_TYPES)


# ---------------------------------------------------------------------------
# Alignment topology generation
# ---------------------------------------------------------------------------


class TestAlignmentTopologyGeneration:
    def test_all_7_types_generated(self) -> None:
        from execution.workers.workstation.constitutional_telos_alignment_engine_v1 import (
            build_telos_primitives,
            build_mission_continuity,
            build_optimization_direction,
            build_value_hierarchy,
            build_alignment_topology,
            ALIGNMENT_TOPOLOGY_TYPES,
        )

        prims = build_telos_primitives()
        mission = build_mission_continuity(prims)
        optim = build_optimization_direction(prims, mission)
        vh = build_value_hierarchy(prims, mission, optim)
        topo = build_alignment_topology(prims, mission, optim, vh)
        types = {n.topology_type for n in topo.nodes}
        assert types == set(ALIGNMENT_TOPOLOGY_TYPES)


# ---------------------------------------------------------------------------
# Continuity-safe alignment adaptation
# ---------------------------------------------------------------------------


class TestContinuitySafeAlignment:
    def test_purpose_continuity_always_applied(self) -> None:
        from execution.workers.workstation.constitutional_telos_alignment_engine_v1 import (
            TelosPrimitiveSet,
            OptimizationDirectionAnalysis,
            PurposeConflictAnalysis,
            MissionContinuityAnalysis,
            build_telos_adaptations,
        )

        prims = TelosPrimitiveSet(composite_stability=0.5, composite_confidence=0.5)
        optim = OptimizationDirectionAnalysis(total_drift_count=0, composite_drift=0.0)
        conflicts = PurposeConflictAnalysis(unreconciled_count=0)
        mission = MissionContinuityAnalysis(divergent_count=0)
        adapts = build_telos_adaptations(optim, conflicts, mission, prims)
        cont_adapt = [
            a for a in adapts.adaptations if a.adaptation_type == "purpose_continuity_maintenance"
        ]
        assert len(cont_adapt) == 1
        assert cont_adapt[0].applied is True
        assert cont_adapt[0].invariants_preserved is True


# ---------------------------------------------------------------------------
# Command registration (26 commands)
# ---------------------------------------------------------------------------


class TestTelosCommandRegistration:
    def test_registry_has_26_commands(self) -> None:
        from composition.registries.canonical_command_registry_v1 import get_canonical_registry

        reg = get_canonical_registry()
        assert len(reg) == 27

    def test_telos_report_in_registry(self) -> None:
        from composition.registries.canonical_command_registry_v1 import get_canonical_registry

        reg = get_canonical_registry()
        assert "!telos-report" in reg.commands

    def test_action_in_allowed(self) -> None:
        from control_plane.router.router_contracts import ALLOWED_ACTION_TYPES

        assert "telos_report" in ALLOWED_ACTION_TYPES

    def test_action_in_map(self) -> None:
        from control_plane.router.control_plane_router_v1 import (
            ACTION_CAPABILITY_MAP,
        )

        assert "telos_report" in ACTION_CAPABILITY_MAP

    def test_config_has_26_actions(self) -> None:
        import json

        with open(f"{_ROOT}/config/control_plane_router_v1.json") as f:
            config = json.load(f)
        assert len(config["allowed_action_types"]) == 27

    def test_substrate_commands(self) -> None:
        from interface.presence.handlers.substrate_command_handler import SUBSTRATE_COMMANDS

        assert "!telos-report" in SUBSTRATE_COMMANDS
        assert len(SUBSTRATE_COMMANDS) == 27


# ---------------------------------------------------------------------------
# Live proof
# ---------------------------------------------------------------------------


class TestLiveTelosProof:
    def test_live_proof_with_full_upstream(self) -> None:
        from execution.workers.workstation.constitutional_telos_alignment_engine_v1 import (
            build_full_telos_proof,
        )
        from execution.workers.workstation.constitutional_identity_continuity_engine_v1 import (
            build_full_identity_proof,
        )
        from execution.workers.workstation.constitutional_epistemic_intelligence_engine_v1 import (
            build_full_epistemic_proof,
        )
        from execution.workers.workstation.constitutional_strategic_intelligence_engine_v1 import (
            build_full_strategy_proof,
        )
        from execution.workers.workstation.constitutional_resource_economics_engine_v1 import (
            build_full_economics_proof,
        )
        from execution.workers.workstation.distributed_constitutional_substrate_federation_v1 import (
            build_full_federation_proof,
        )
        from execution.workers.workstation.constitutional_substrate_governance_layer_v1 import (
            build_full_constitutional_proof,
        )
        from execution.workers.workstation.adaptive_governance_intelligence_engine_v1 import (
            build_full_governance_intelligence_proof,
        )
        from execution.workers.workstation.governed_recursive_orchestration_engine_v1 import (
            build_full_orchestration_proof,
        )
        from execution.workers.workstation.persistent_substrate_continuity_engine_v1 import (
            build_full_continuity_proof,
        )
        from execution.workers.workstation.recursive_capability_planning_engine_v1 import (
            build_full_capability_proof,
        )

        cap = build_full_capability_proof()
        orch = build_full_orchestration_proof(capability_proof=cap)
        cont = build_full_continuity_proof(orchestration_proof=orch, capability_proof=cap)
        gov_intel = build_full_governance_intelligence_proof(
            orchestration_proof=orch, capability_proof=cap
        )
        const_gov = build_full_constitutional_proof(
            governance_proof=gov_intel,
            orchestration_proof=orch,
            continuity_proof=cont,
            capability_proof=cap,
        )
        fed = build_full_federation_proof(
            orchestration_proof=orch,
            capability_proof=cap,
            continuity_proof=cont,
            governance_proof=gov_intel,
            constitutional_proof=const_gov,
        )
        econ = build_full_economics_proof(
            federation_proof=fed,
            orchestration_proof=orch,
            capability_proof=cap,
        )
        strat = build_full_strategy_proof(
            economics_proof=econ,
            federation_proof=fed,
            orchestration_proof=orch,
            capability_proof=cap,
            founder_confirmed=True,
        )
        epis = build_full_epistemic_proof(
            strategy_proof=strat,
            economics_proof=econ,
            federation_proof=fed,
            orchestration_proof=orch,
            continuity_proof=cont,
            constitutional_proof=const_gov,
            governance_proof=gov_intel,
            capability_proof=cap,
            founder_confirmed=True,
        )
        iden = build_full_identity_proof(
            epistemic_proof=epis,
            strategy_proof=strat,
            economics_proof=econ,
            federation_proof=fed,
            orchestration_proof=orch,
            continuity_proof=cont,
            constitutional_proof=const_gov,
            governance_proof=gov_intel,
            capability_proof=cap,
            founder_confirmed=True,
        )

        proof = build_full_telos_proof(
            identity_proof=iden,
            epistemic_proof=epis,
            strategy_proof=strat,
            economics_proof=econ,
            federation_proof=fed,
            orchestration_proof=orch,
            continuity_proof=cont,
            constitutional_proof=const_gov,
            governance_proof=gov_intel,
            capability_proof=cap,
            founder_confirmed=True,
        )

        assert proof.maturity_level == "L5_CONSTITUTIONAL_TELOS_ALIGNMENT"
        assert proof.evidence.primitives_evaluated is True
        assert proof.evidence.mission_analyzed is True
        assert proof.evidence.optimization_analyzed is True
        assert proof.evidence.value_hierarchy_analyzed is True
        assert proof.evidence.conflicts_analyzed is True
        assert proof.evidence.topology_generated is True
        assert proof.evidence.adaptations_applied is True
        assert proof.evidence.founder_confirmed is True
        assert proof.execution_strategy == "constitutional_telos_alignment_active"
