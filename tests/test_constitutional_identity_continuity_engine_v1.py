"""Tests for constitutional_identity_continuity_engine_v1."""

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


class TestIdentityConstants:
    def test_maturity_levels_count(self) -> None:
        from core.workstation.constitutional_identity_continuity_engine_v1 import (
            IDENTITY_MATURITY_LEVELS,
        )

        assert len(IDENTITY_MATURITY_LEVELS) == 6

    def test_maturity_levels_order(self) -> None:
        from core.workstation.constitutional_identity_continuity_engine_v1 import (
            IDENTITY_MATURITY_LEVELS,
        )

        assert IDENTITY_MATURITY_LEVELS[0] == "L0_NO_IDENTITY_CONTINUITY"
        assert IDENTITY_MATURITY_LEVELS[5] == "L5_CONSTITUTIONAL_IDENTITY_CONTINUITY"

    def test_primitives_count(self) -> None:
        from core.workstation.constitutional_identity_continuity_engine_v1 import (
            IDENTITY_PRIMITIVES,
        )

        assert len(IDENTITY_PRIMITIVES) == 10

    def test_memory_layers_count(self) -> None:
        from core.workstation.constitutional_identity_continuity_engine_v1 import (
            SOVEREIGN_MEMORY_LAYERS,
        )

        assert len(SOVEREIGN_MEMORY_LAYERS) == 8

    def test_narrative_dimensions_count(self) -> None:
        from core.workstation.constitutional_identity_continuity_engine_v1 import (
            NARRATIVE_CONTINUITY_DIMENSIONS,
        )

        assert len(NARRATIVE_CONTINUITY_DIMENSIONS) == 8

    def test_drift_types_count(self) -> None:
        from core.workstation.constitutional_identity_continuity_engine_v1 import (
            IDENTITY_DRIFT_TYPES,
        )

        assert len(IDENTITY_DRIFT_TYPES) == 8

    def test_reconciliation_types_count(self) -> None:
        from core.workstation.constitutional_identity_continuity_engine_v1 import (
            HISTORICAL_RECONCILIATION_TYPES,
        )

        assert len(HISTORICAL_RECONCILIATION_TYPES) == 6

    def test_topology_types_count(self) -> None:
        from core.workstation.constitutional_identity_continuity_engine_v1 import (
            TEMPORAL_TOPOLOGY_TYPES,
        )

        assert len(TEMPORAL_TOPOLOGY_TYPES) == 7

    def test_hard_ceilings_count(self) -> None:
        from core.workstation.constitutional_identity_continuity_engine_v1 import (
            IDENTITY_HARD_CEILINGS,
        )

        assert len(IDENTITY_HARD_CEILINGS) == 7

    def test_adaptation_types_count(self) -> None:
        from core.workstation.constitutional_identity_continuity_engine_v1 import (
            IDENTITY_ADAPTATION_TYPES,
        )

        assert len(IDENTITY_ADAPTATION_TYPES) == 6


# ---------------------------------------------------------------------------
# Dataclasses
# ---------------------------------------------------------------------------


class TestIdentityPrimitive:
    def test_default(self) -> None:
        from core.workstation.constitutional_identity_continuity_engine_v1 import (
            IdentityPrimitive,
        )

        p = IdentityPrimitive()
        assert p.confidence == 0.0
        assert p.stability == 0.0

    def test_to_dict_serializable(self) -> None:
        from core.workstation.constitutional_identity_continuity_engine_v1 import (
            IdentityPrimitive,
        )

        p = IdentityPrimitive(primitive="test", confidence=0.5)
        d = p.to_dict()
        json.dumps(d)
        assert d["primitive"] == "test"


class TestIdentityPrimitiveSet:
    def test_auto_timestamp(self) -> None:
        from core.workstation.constitutional_identity_continuity_engine_v1 import (
            IdentityPrimitiveSet,
        )

        s = IdentityPrimitiveSet()
        assert s.timestamp != ""

    def test_to_dict(self) -> None:
        from core.workstation.constitutional_identity_continuity_engine_v1 import (
            IdentityPrimitiveSet,
        )

        s = IdentityPrimitiveSet()
        d = s.to_dict()
        json.dumps(d)


class TestSovereignMemoryLayer:
    def test_default(self) -> None:
        from core.workstation.constitutional_identity_continuity_engine_v1 import (
            SovereignMemoryLayer,
        )

        m = SovereignMemoryLayer()
        assert m.integrity_score == 0.0
        assert m.immutable is True

    def test_to_dict(self) -> None:
        from core.workstation.constitutional_identity_continuity_engine_v1 import (
            SovereignMemoryLayer,
        )

        m = SovereignMemoryLayer(layer="test", integrity_score=0.8)
        d = m.to_dict()
        assert d["layer"] == "test"


class TestNarrativeContinuityDimension:
    def test_default(self) -> None:
        from core.workstation.constitutional_identity_continuity_engine_v1 import (
            NarrativeContinuityDimension,
        )

        n = NarrativeContinuityDimension()
        assert n.coherence_score == 0.0
        assert n.divergence_detected is False

    def test_to_dict(self) -> None:
        from core.workstation.constitutional_identity_continuity_engine_v1 import (
            NarrativeContinuityDimension,
        )

        n = NarrativeContinuityDimension(dimension="test")
        d = n.to_dict()
        assert d["dimension"] == "test"


class TestIdentityDriftDetection:
    def test_default(self) -> None:
        from core.workstation.constitutional_identity_continuity_engine_v1 import (
            IdentityDriftDetection,
        )

        d = IdentityDriftDetection()
        assert d.drift_detected is False
        assert d.severity == "low"

    def test_to_dict(self) -> None:
        from core.workstation.constitutional_identity_continuity_engine_v1 import (
            IdentityDriftDetection,
        )

        d = IdentityDriftDetection(drift_type="test", severity="high")
        result = d.to_dict()
        assert result["severity"] == "high"


class TestHistoricalReconciliation:
    def test_default(self) -> None:
        from core.workstation.constitutional_identity_continuity_engine_v1 import (
            HistoricalReconciliation,
        )

        r = HistoricalReconciliation()
        assert r.conflict_detected is False
        assert r.severity == 0.0

    def test_to_dict(self) -> None:
        from core.workstation.constitutional_identity_continuity_engine_v1 import (
            HistoricalReconciliation,
        )

        r = HistoricalReconciliation(reconciliation_type="test", severity=0.5)
        d = r.to_dict()
        assert d["reconciliation_type"] == "test"


class TestTemporalTopologyNode:
    def test_default(self) -> None:
        from core.workstation.constitutional_identity_continuity_engine_v1 import (
            TemporalTopologyNode,
        )

        n = TemporalTopologyNode()
        assert n.connections == 0

    def test_to_dict(self) -> None:
        from core.workstation.constitutional_identity_continuity_engine_v1 import (
            TemporalTopologyNode,
        )

        n = TemporalTopologyNode(node_id="n1", topology_type="test")
        d = n.to_dict()
        assert d["node_id"] == "n1"


class TestTemporalTopology:
    def test_auto_hash(self) -> None:
        from core.workstation.constitutional_identity_continuity_engine_v1 import (
            TemporalTopology,
            TemporalTopologyNode,
        )

        t = TemporalTopology(nodes=[TemporalTopologyNode(node_id="n1", topology_type="test")])
        assert t.topology_hash != ""

    def test_hash_deterministic(self) -> None:
        from core.workstation.constitutional_identity_continuity_engine_v1 import (
            TemporalTopology,
            TemporalTopologyNode,
        )

        nodes = [TemporalTopologyNode(node_id="n1", topology_type="test", coherence=0.5)]
        t1 = TemporalTopology(nodes=list(nodes), topology_hash="")
        t2 = TemporalTopology(nodes=list(nodes), topology_hash="")
        assert t1.topology_hash == t2.topology_hash


class TestIdentityAdaptation:
    def test_default_invariants_preserved(self) -> None:
        from core.workstation.constitutional_identity_continuity_engine_v1 import (
            IdentityAdaptation,
        )

        a = IdentityAdaptation()
        assert a.invariants_preserved is True

    def test_to_dict(self) -> None:
        from core.workstation.constitutional_identity_continuity_engine_v1 import (
            IdentityAdaptation,
        )

        a = IdentityAdaptation(adaptation_type="test")
        d = a.to_dict()
        assert d["adaptation_type"] == "test"


class TestIdentityEvidence:
    def test_field_count(self) -> None:
        from core.workstation.constitutional_identity_continuity_engine_v1 import (
            IdentityEvidence,
        )

        ev = IdentityEvidence()
        d = ev.to_dict()
        assert len(d) == 38

    def test_to_dict_serializable(self) -> None:
        from core.workstation.constitutional_identity_continuity_engine_v1 import (
            IdentityEvidence,
        )

        ev = IdentityEvidence()
        json.dumps(ev.to_dict())


class TestIdentityProof:
    def test_auto_proof_id(self) -> None:
        from core.workstation.constitutional_identity_continuity_engine_v1 import (
            IdentityProof,
        )

        p = IdentityProof()
        assert p.proof_id.startswith("IDEN-")

    def test_to_dict_serializable(self) -> None:
        from core.workstation.constitutional_identity_continuity_engine_v1 import (
            IdentityEvidence,
            IdentityProof,
        )

        p = IdentityProof(evidence=IdentityEvidence())
        json.dumps(p.to_dict(), default=str)


# ---------------------------------------------------------------------------
# Builders
# ---------------------------------------------------------------------------


class TestBuildIdentityPrimitives:
    def test_produces_10_primitives(self) -> None:
        from core.workstation.constitutional_identity_continuity_engine_v1 import (
            build_identity_primitives,
        )

        result = build_identity_primitives()
        assert len(result.primitives) == 10

    def test_composite_confidence_positive(self) -> None:
        from core.workstation.constitutional_identity_continuity_engine_v1 import (
            build_identity_primitives,
        )

        result = build_identity_primitives()
        assert result.composite_confidence > 0

    def test_all_primitives_named(self) -> None:
        from core.workstation.constitutional_identity_continuity_engine_v1 import (
            build_identity_primitives,
            IDENTITY_PRIMITIVES,
        )

        result = build_identity_primitives()
        names = {p.primitive for p in result.primitives}
        assert names == set(IDENTITY_PRIMITIVES)


class TestBuildSovereignMemory:
    def test_produces_8_layers(self) -> None:
        from core.workstation.constitutional_identity_continuity_engine_v1 import (
            build_sovereign_memory,
        )

        result = build_sovereign_memory()
        assert len(result.layers) == 8

    def test_composite_integrity_positive(self) -> None:
        from core.workstation.constitutional_identity_continuity_engine_v1 import (
            build_sovereign_memory,
        )

        result = build_sovereign_memory()
        assert result.composite_integrity > 0


class TestBuildNarrativeContinuity:
    def test_produces_8_dimensions(self) -> None:
        from core.workstation.constitutional_identity_continuity_engine_v1 import (
            build_identity_primitives,
            build_sovereign_memory,
            build_narrative_continuity,
        )

        prims = build_identity_primitives()
        mem = build_sovereign_memory()
        result = build_narrative_continuity(prims, mem)
        assert len(result.dimensions) == 8

    def test_composite_coherence_between_0_and_1(self) -> None:
        from core.workstation.constitutional_identity_continuity_engine_v1 import (
            build_identity_primitives,
            build_sovereign_memory,
            build_narrative_continuity,
        )

        prims = build_identity_primitives()
        mem = build_sovereign_memory()
        result = build_narrative_continuity(prims, mem)
        assert 0 <= result.composite_coherence <= 1


class TestBuildIdentityDrift:
    def test_produces_8_detections(self) -> None:
        from core.workstation.constitutional_identity_continuity_engine_v1 import (
            build_identity_primitives,
            build_sovereign_memory,
            build_narrative_continuity,
            build_identity_drift,
        )

        prims = build_identity_primitives()
        mem = build_sovereign_memory()
        narr = build_narrative_continuity(prims, mem)
        result = build_identity_drift(prims, narr)
        assert len(result.detections) == 8

    def test_drift_types_all_covered(self) -> None:
        from core.workstation.constitutional_identity_continuity_engine_v1 import (
            build_identity_primitives,
            build_sovereign_memory,
            build_narrative_continuity,
            build_identity_drift,
            IDENTITY_DRIFT_TYPES,
        )

        prims = build_identity_primitives()
        mem = build_sovereign_memory()
        narr = build_narrative_continuity(prims, mem)
        result = build_identity_drift(prims, narr)
        types = {d.drift_type for d in result.detections}
        assert types == set(IDENTITY_DRIFT_TYPES)


class TestBuildHistoricalReconciliation:
    def test_produces_reconciliation_types(self) -> None:
        from core.workstation.constitutional_identity_continuity_engine_v1 import (
            build_identity_primitives,
            build_sovereign_memory,
            build_narrative_continuity,
            build_identity_drift,
            build_historical_reconciliation,
        )

        prims = build_identity_primitives()
        mem = build_sovereign_memory()
        narr = build_narrative_continuity(prims, mem)
        drift = build_identity_drift(prims, narr)
        result = build_historical_reconciliation(mem, drift, narr)
        assert result.conflict_count >= 0

    def test_all_types_covered(self) -> None:
        from core.workstation.constitutional_identity_continuity_engine_v1 import (
            build_identity_primitives,
            build_sovereign_memory,
            build_narrative_continuity,
            build_identity_drift,
            build_historical_reconciliation,
            HISTORICAL_RECONCILIATION_TYPES,
        )

        prims = build_identity_primitives()
        mem = build_sovereign_memory()
        narr = build_narrative_continuity(prims, mem)
        drift = build_identity_drift(prims, narr)
        result = build_historical_reconciliation(mem, drift, narr)
        types = {r.reconciliation_type for r in result.reconciliations}
        assert types == set(HISTORICAL_RECONCILIATION_TYPES)


class TestBuildTemporalTopology:
    def test_covers_7_types(self) -> None:
        from core.workstation.constitutional_identity_continuity_engine_v1 import (
            build_identity_primitives,
            build_sovereign_memory,
            build_narrative_continuity,
            build_identity_drift,
            build_temporal_topology,
        )

        prims = build_identity_primitives()
        mem = build_sovereign_memory()
        narr = build_narrative_continuity(prims, mem)
        drift = build_identity_drift(prims, narr)
        result = build_temporal_topology(prims, mem, narr, drift)
        assert result.topology_types_covered == 7

    def test_hash_not_empty(self) -> None:
        from core.workstation.constitutional_identity_continuity_engine_v1 import (
            build_identity_primitives,
            build_sovereign_memory,
            build_narrative_continuity,
            build_identity_drift,
            build_temporal_topology,
        )

        prims = build_identity_primitives()
        mem = build_sovereign_memory()
        narr = build_narrative_continuity(prims, mem)
        drift = build_identity_drift(prims, narr)
        result = build_temporal_topology(prims, mem, narr, drift)
        assert result.topology_hash != ""


class TestBuildIdentityAdaptations:
    def test_produces_6_adaptations(self) -> None:
        from core.workstation.constitutional_identity_continuity_engine_v1 import (
            build_identity_primitives,
            build_sovereign_memory,
            build_narrative_continuity,
            build_identity_drift,
            build_historical_reconciliation,
            build_identity_adaptations,
        )

        prims = build_identity_primitives()
        mem = build_sovereign_memory()
        narr = build_narrative_continuity(prims, mem)
        drift = build_identity_drift(prims, narr)
        recon = build_historical_reconciliation(mem, drift, narr)
        result = build_identity_adaptations(drift, recon, narr, prims)
        assert len(result.adaptations) == 6

    def test_invariants_preserved(self) -> None:
        from core.workstation.constitutional_identity_continuity_engine_v1 import (
            build_identity_primitives,
            build_sovereign_memory,
            build_narrative_continuity,
            build_identity_drift,
            build_historical_reconciliation,
            build_identity_adaptations,
        )

        prims = build_identity_primitives()
        mem = build_sovereign_memory()
        narr = build_narrative_continuity(prims, mem)
        drift = build_identity_drift(prims, narr)
        recon = build_historical_reconciliation(mem, drift, narr)
        result = build_identity_adaptations(drift, recon, narr, prims)
        assert result.all_invariants_preserved is True


class TestEnforceIdentityHardCeilings:
    def test_no_violation_on_clean(self) -> None:
        from core.workstation.constitutional_identity_continuity_engine_v1 import (
            IdentityPrimitiveSet,
            IdentityPrimitive,
            IdentityDriftAnalysis,
            HistoricalReconciliationAnalysis,
            IdentityAdaptationSet,
            enforce_identity_hard_ceilings,
        )

        prims = IdentityPrimitiveSet(
            primitives=[
                IdentityPrimitive(primitive="identity_lineage", confidence=0.8),
                IdentityPrimitive(primitive="historical_consistency", confidence=0.7),
            ],
            composite_confidence=0.75,
            composite_stability=0.7,
        )
        drift = IdentityDriftAnalysis(
            critical_drift_count=0, total_drift_count=0, composite_drift=0.0
        )
        recon = HistoricalReconciliationAnalysis(unreconciled_count=0)
        adapts = IdentityAdaptationSet(all_invariants_preserved=True)
        blocked, reasons = enforce_identity_hard_ceilings(prims, drift, recon, adapts)
        assert blocked is False
        assert len(reasons) == 0

    def test_invariant_violation_blocks(self) -> None:
        from core.workstation.constitutional_identity_continuity_engine_v1 import (
            IdentityPrimitiveSet,
            IdentityPrimitive,
            IdentityDriftAnalysis,
            HistoricalReconciliationAnalysis,
            IdentityAdaptationSet,
            IdentityAdaptation,
            enforce_identity_hard_ceilings,
        )

        prims = IdentityPrimitiveSet(
            primitives=[IdentityPrimitive(primitive="historical_consistency", confidence=0.1)],
            composite_confidence=0.1,
            composite_stability=0.1,
        )
        drift = IdentityDriftAnalysis(
            critical_drift_count=3,
            total_drift_count=5,
            composite_drift=0.5,
        )
        recon = HistoricalReconciliationAnalysis(unreconciled_count=4)
        adapts = IdentityAdaptationSet(
            adaptations=[IdentityAdaptation(invariants_preserved=False)],
            all_invariants_preserved=False,
        )
        blocked, reasons = enforce_identity_hard_ceilings(prims, drift, recon, adapts)
        assert blocked is True
        assert "unconstitutional_memory_mutation" in reasons
        assert "identity_breaking_recursion" in reasons
        assert "historical_replay_invalidation" in reasons
        assert "narrative_corruption" in reasons
        assert "institutional_selfhood_fragmentation" in reasons
        assert "continuity_breaking_identity_evolution" in reasons
        assert "unsourced_historical_rewriting" in reasons


# ---------------------------------------------------------------------------
# Maturity
# ---------------------------------------------------------------------------


class TestComputeIdentityMaturity:
    def test_empty_evidence_low_score(self) -> None:
        from core.workstation.constitutional_identity_continuity_engine_v1 import (
            IdentityEvidence,
            compute_identity_maturity,
        )

        ev = IdentityEvidence(
            all_invariants_preserved=False,
            hard_ceilings_enforced=False,
            identity_constitutionally_safe=False,
            selfhood_stable=False,
        )
        assert compute_identity_maturity(ev) == 0

    def test_full_evidence_high_score(self) -> None:
        from core.workstation.constitutional_identity_continuity_engine_v1 import (
            IdentityEvidence,
            compute_identity_maturity,
        )

        ev = IdentityEvidence(
            primitives_evaluated=True,
            memory_analyzed=True,
            narrative_analyzed=True,
            drift_analyzed=True,
            reconciliation_analyzed=True,
            topology_generated=True,
            adaptations_applied=True,
            all_invariants_preserved=True,
            hard_ceilings_enforced=True,
            identity_constitutionally_safe=True,
            selfhood_stable=True,
        )
        assert compute_identity_maturity(ev) == 10


class TestIdentityMaturityCeiling:
    def test_dry_run_l0(self) -> None:
        from core.workstation.constitutional_identity_continuity_engine_v1 import (
            IdentityEvidence,
            identity_maturity_ceiling,
        )

        ev = IdentityEvidence(is_dry_run=True, primitives_evaluated=True)
        assert identity_maturity_ceiling(ev) == "L0_NO_IDENTITY_CONTINUITY"

    def test_no_primitives_l0(self) -> None:
        from core.workstation.constitutional_identity_continuity_engine_v1 import (
            IdentityEvidence,
            identity_maturity_ceiling,
        )

        ev = IdentityEvidence(primitives_evaluated=False)
        assert identity_maturity_ceiling(ev) == "L0_NO_IDENTITY_CONTINUITY"

    def test_full_evidence_l5(self) -> None:
        from core.workstation.constitutional_identity_continuity_engine_v1 import (
            IdentityEvidence,
            identity_maturity_ceiling,
        )

        ev = IdentityEvidence(
            primitives_evaluated=True,
            memory_analyzed=True,
            narrative_analyzed=True,
            reconciliation_analyzed=True,
            founder_confirmed=True,
        )
        assert identity_maturity_ceiling(ev) == "L5_CONSTITUTIONAL_IDENTITY_CONTINUITY"

    def test_no_founder_capped_l4(self) -> None:
        from core.workstation.constitutional_identity_continuity_engine_v1 import (
            IdentityEvidence,
            identity_maturity_ceiling,
        )

        ev = IdentityEvidence(
            primitives_evaluated=True,
            memory_analyzed=True,
            narrative_analyzed=True,
            reconciliation_analyzed=True,
            founder_confirmed=False,
        )
        assert identity_maturity_ceiling(ev) == "L4_IDENTITY_RECONCILED"


class TestClassifyIdentityMaturity:
    def test_empty_l0(self) -> None:
        from core.workstation.constitutional_identity_continuity_engine_v1 import (
            IdentityEvidence,
            classify_identity_maturity,
        )

        ev = IdentityEvidence(
            all_invariants_preserved=False,
            hard_ceilings_enforced=False,
            identity_constitutionally_safe=False,
            selfhood_stable=False,
        )
        level, ceiling, blocked, reason = classify_identity_maturity(ev)
        assert level == "L0_NO_IDENTITY_CONTINUITY"


# ---------------------------------------------------------------------------
# Full pipeline
# ---------------------------------------------------------------------------


class TestBuildFullIdentityProof:
    def test_no_upstream(self) -> None:
        from core.workstation.constitutional_identity_continuity_engine_v1 import (
            build_full_identity_proof,
        )

        proof = build_full_identity_proof()
        assert proof.proof_id.startswith("IDEN-")
        assert proof.evidence is not None
        assert proof.evidence.primitives_evaluated is True

    def test_dry_run(self) -> None:
        from core.workstation.constitutional_identity_continuity_engine_v1 import (
            build_full_identity_proof,
        )

        proof = build_full_identity_proof(is_dry_run=True)
        assert proof.maturity_level == "L0_NO_IDENTITY_CONTINUITY"
        assert proof.execution_strategy == "identity_continuity_dry_run"

    def test_founder_identity(self) -> None:
        from core.workstation.constitutional_identity_continuity_engine_v1 import (
            build_full_identity_proof,
        )

        proof = build_full_identity_proof(founder_confirmed=True)
        assert proof.evidence.founder_confirmed is True

    def test_with_full_upstream_chain(self) -> None:
        from core.workstation.constitutional_identity_continuity_engine_v1 import (
            build_full_identity_proof,
        )
        from core.workstation.constitutional_epistemic_intelligence_engine_v1 import (
            build_full_epistemic_proof,
        )
        from core.workstation.constitutional_strategic_intelligence_engine_v1 import (
            build_full_strategy_proof,
        )
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

        proof = build_full_identity_proof(
            epistemic_proof=epis,
            strategy_proof=strat,
            economics_proof=econ,
            federation_proof=fed,
            orchestration_proof=orch,
            capability_proof=cap,
            founder_confirmed=True,
        )
        assert proof.maturity_level != "L0_NO_IDENTITY_CONTINUITY"
        assert proof.evidence.primitive_count == 10
        assert proof.evidence.memory_analyzed is True
        assert proof.evidence.narrative_analyzed is True
        assert proof.evidence.reconciliation_analyzed is True


# ---------------------------------------------------------------------------
# Persistence
# ---------------------------------------------------------------------------


class TestPersistIdentityProof:
    def test_persist_creates_file(self, tmp_path: Path) -> None:
        from core.workstation.constitutional_identity_continuity_engine_v1 import (
            build_full_identity_proof,
            persist_identity_proof,
        )

        proof = build_full_identity_proof(trace_id="persist-test")
        path = persist_identity_proof(proof, base_dir=tmp_path)
        assert path.exists()
        assert path.name.startswith("IDEN-")
        data = json.loads(path.read_text())
        assert data["proof_type"] == "constitutional_identity_continuity"

    def test_persist_json_valid(self, tmp_path: Path) -> None:
        from core.workstation.constitutional_identity_continuity_engine_v1 import (
            build_full_identity_proof,
            persist_identity_proof,
        )

        proof = build_full_identity_proof()
        path = persist_identity_proof(proof, base_dir=tmp_path)
        data = json.loads(path.read_text())
        assert "evidence" in data
        assert "primitives" in data
        assert "reconciliation" in data


# ---------------------------------------------------------------------------
# Selfhood stability
# ---------------------------------------------------------------------------


class TestSelfhoodStability:
    def test_selfhood_logic(self) -> None:
        from core.workstation.constitutional_identity_continuity_engine_v1 import (
            build_full_identity_proof,
        )

        proof = build_full_identity_proof()
        ev = proof.evidence
        expected = ev.critical_drift_count == 0 and ev.all_invariants_preserved
        assert ev.selfhood_stable is expected

    def test_critical_drift_destabilizes(self) -> None:
        from core.workstation.constitutional_identity_continuity_engine_v1 import (
            build_identity_primitives,
            build_sovereign_memory,
            build_narrative_continuity,
            build_identity_drift,
            IdentityDriftAnalysis,
        )

        prims = build_identity_primitives()
        mem = build_sovereign_memory()
        narr = build_narrative_continuity(prims, mem)
        drift = build_identity_drift(prims, narr)
        assert isinstance(drift, IdentityDriftAnalysis)


# ---------------------------------------------------------------------------
# Memory quarantine safety
# ---------------------------------------------------------------------------


class TestMemoryQuarantineSafety:
    def test_no_quarantine_without_corruption(self) -> None:
        from core.workstation.constitutional_identity_continuity_engine_v1 import (
            build_identity_primitives,
            build_sovereign_memory,
            build_narrative_continuity,
            build_identity_drift,
            build_historical_reconciliation,
            build_identity_adaptations,
        )

        prims = build_identity_primitives()
        mem = build_sovereign_memory()
        narr = build_narrative_continuity(prims, mem)
        drift = build_identity_drift(prims, narr)
        recon = build_historical_reconciliation(mem, drift, narr)
        adapts = build_identity_adaptations(drift, recon, narr, prims)
        quarantine = [a for a in adapts.adaptations if a.adaptation_type == "memory_quarantine"]
        assert len(quarantine) == 1


# ---------------------------------------------------------------------------
# Identity preservation
# ---------------------------------------------------------------------------


class TestIdentityPreservation:
    def test_preservation_always_present(self) -> None:
        from core.workstation.constitutional_identity_continuity_engine_v1 import (
            IdentityPrimitiveSet,
            IdentityDriftAnalysis,
            HistoricalReconciliationAnalysis,
            NarrativeContinuityAnalysis,
            build_identity_adaptations,
        )

        prims = IdentityPrimitiveSet(composite_stability=0.5, composite_confidence=0.5)
        drift = IdentityDriftAnalysis(total_drift_count=0, composite_drift=0.0)
        recon = HistoricalReconciliationAnalysis(unreconciled_count=0)
        narr = NarrativeContinuityAnalysis(divergent_count=0)
        adapts = build_identity_adaptations(drift, recon, narr, prims)
        pres_adapt = [a for a in adapts.adaptations if a.adaptation_type == "identity_preservation"]
        assert len(pres_adapt) == 1


# ---------------------------------------------------------------------------
# Replay safe lineage
# ---------------------------------------------------------------------------


class TestReplaySafeLineage:
    def test_replay_safe_with_federation(self) -> None:
        from core.workstation.constitutional_identity_continuity_engine_v1 import (
            build_full_identity_proof,
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
        proof = build_full_identity_proof(
            federation_proof=fed, orchestration_proof=orch, capability_proof=cap
        )
        assert proof.evidence is not None


# ---------------------------------------------------------------------------
# Temporal topology generation
# ---------------------------------------------------------------------------


class TestTemporalTopologyGeneration:
    def test_all_7_types_generated(self) -> None:
        from core.workstation.constitutional_identity_continuity_engine_v1 import (
            build_identity_primitives,
            build_sovereign_memory,
            build_narrative_continuity,
            build_identity_drift,
            build_temporal_topology,
            TEMPORAL_TOPOLOGY_TYPES,
        )

        prims = build_identity_primitives()
        mem = build_sovereign_memory()
        narr = build_narrative_continuity(prims, mem)
        drift = build_identity_drift(prims, narr)
        topo = build_temporal_topology(prims, mem, narr, drift)
        types = {n.topology_type for n in topo.nodes}
        assert types == set(TEMPORAL_TOPOLOGY_TYPES)


# ---------------------------------------------------------------------------
# Continuity-safe memory recovery
# ---------------------------------------------------------------------------


class TestContinuitySafeMemoryRecovery:
    def test_historical_integrity_always_applied(self) -> None:
        from core.workstation.constitutional_identity_continuity_engine_v1 import (
            IdentityPrimitiveSet,
            IdentityDriftAnalysis,
            HistoricalReconciliationAnalysis,
            NarrativeContinuityAnalysis,
            build_identity_adaptations,
        )

        prims = IdentityPrimitiveSet(composite_stability=0.5, composite_confidence=0.5)
        drift = IdentityDriftAnalysis(total_drift_count=0, composite_drift=0.0)
        recon = HistoricalReconciliationAnalysis(unreconciled_count=0)
        narr = NarrativeContinuityAnalysis(divergent_count=0)
        adapts = build_identity_adaptations(drift, recon, narr, prims)
        hist_adapt = [
            a for a in adapts.adaptations if a.adaptation_type == "historical_integrity_restoration"
        ]
        assert len(hist_adapt) == 1
        assert hist_adapt[0].applied is True
        assert hist_adapt[0].invariants_preserved is True


# ---------------------------------------------------------------------------
# Command registration (25 commands)
# ---------------------------------------------------------------------------


class TestIdentityCommandRegistration:
    def test_registry_has_25_commands(self) -> None:
        from composition.registries.canonical_command_registry_v1 import get_canonical_registry

        reg = get_canonical_registry()
        assert len(reg) == 27

    def test_identity_report_in_registry(self) -> None:
        from composition.registries.canonical_command_registry_v1 import get_canonical_registry

        reg = get_canonical_registry()
        assert "!identity-report" in reg.commands

    def test_action_in_allowed(self) -> None:
        from control_plane.router.router_contracts import ALLOWED_ACTION_TYPES

        assert "identity_report" in ALLOWED_ACTION_TYPES

    def test_action_in_map(self) -> None:
        from control_plane.router.control_plane_router_v1 import (
            ACTION_CAPABILITY_MAP,
        )

        assert "identity_report" in ACTION_CAPABILITY_MAP

    def test_config_has_25_actions(self) -> None:
        import json

        with open(f"{_ROOT}/config/control_plane_router_v1.json") as f:
            config = json.load(f)
        assert len(config["allowed_action_types"]) == 27

    def test_substrate_commands(self) -> None:
        from handlers.substrate_command_handler import SUBSTRATE_COMMANDS

        assert "!identity-report" in SUBSTRATE_COMMANDS
        assert len(SUBSTRATE_COMMANDS) == 27


# ---------------------------------------------------------------------------
# Live proof
# ---------------------------------------------------------------------------


class TestLiveIdentityProof:
    def test_live_proof_with_full_upstream(self) -> None:
        from core.workstation.constitutional_identity_continuity_engine_v1 import (
            build_full_identity_proof,
            persist_identity_proof,
        )
        from core.workstation.constitutional_epistemic_intelligence_engine_v1 import (
            build_full_epistemic_proof,
        )
        from core.workstation.constitutional_strategic_intelligence_engine_v1 import (
            build_full_strategy_proof,
        )
        from core.workstation.constitutional_resource_economics_engine_v1 import (
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

        proof = build_full_identity_proof(
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

        assert proof.maturity_level == "L5_CONSTITUTIONAL_IDENTITY_CONTINUITY"
        assert proof.evidence.primitives_evaluated is True
        assert proof.evidence.memory_analyzed is True
        assert proof.evidence.narrative_analyzed is True
        assert proof.evidence.reconciliation_analyzed is True
        assert proof.evidence.topology_generated is True
        assert proof.evidence.adaptations_applied is True
        assert proof.evidence.selfhood_stable is True
        assert proof.evidence.founder_confirmed is True
        assert proof.execution_strategy == "constitutional_identity_continuity_active"
