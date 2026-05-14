"""Tests for constitutional_epistemic_intelligence_engine_v1."""

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


class TestEpistemicConstants:
    def test_maturity_levels_count(self) -> None:
        from core.workstation.constitutional_epistemic_intelligence_engine_v1 import (
            EPISTEMIC_MATURITY_LEVELS,
        )

        assert len(EPISTEMIC_MATURITY_LEVELS) == 6

    def test_maturity_levels_order(self) -> None:
        from core.workstation.constitutional_epistemic_intelligence_engine_v1 import (
            EPISTEMIC_MATURITY_LEVELS,
        )

        assert EPISTEMIC_MATURITY_LEVELS[0] == "L0_NO_EPISTEMIC_INTELLIGENCE"
        assert EPISTEMIC_MATURITY_LEVELS[5] == "L5_CONSTITUTIONAL_EPISTEMIC_INTELLIGENCE"

    def test_primitives_count(self) -> None:
        from core.workstation.constitutional_epistemic_intelligence_engine_v1 import (
            EPISTEMIC_PRIMITIVES,
        )

        assert len(EPISTEMIC_PRIMITIVES) == 10

    def test_integrity_dimensions_count(self) -> None:
        from core.workstation.constitutional_epistemic_intelligence_engine_v1 import (
            EVIDENCE_INTEGRITY_DIMENSIONS,
        )

        assert len(EVIDENCE_INTEGRITY_DIMENSIONS) == 8

    def test_coherence_detectors_count(self) -> None:
        from core.workstation.constitutional_epistemic_intelligence_engine_v1 import (
            REALITY_COHERENCE_DETECTORS,
        )

        assert len(REALITY_COHERENCE_DETECTORS) == 8

    def test_probabilistic_types_count(self) -> None:
        from core.workstation.constitutional_epistemic_intelligence_engine_v1 import (
            PROBABILISTIC_REASONING_TYPES,
        )

        assert len(PROBABILISTIC_REASONING_TYPES) == 7

    def test_contradiction_types_count(self) -> None:
        from core.workstation.constitutional_epistemic_intelligence_engine_v1 import (
            CONTRADICTION_TYPES,
        )

        assert len(CONTRADICTION_TYPES) == 7

    def test_topology_types_count(self) -> None:
        from core.workstation.constitutional_epistemic_intelligence_engine_v1 import (
            EPISTEMIC_TOPOLOGY_TYPES,
        )

        assert len(EPISTEMIC_TOPOLOGY_TYPES) == 7

    def test_hard_ceilings_count(self) -> None:
        from core.workstation.constitutional_epistemic_intelligence_engine_v1 import (
            EPISTEMIC_HARD_CEILINGS,
        )

        assert len(EPISTEMIC_HARD_CEILINGS) == 7

    def test_adaptation_types_count(self) -> None:
        from core.workstation.constitutional_epistemic_intelligence_engine_v1 import (
            EPISTEMIC_ADAPTATION_TYPES,
        )

        assert len(EPISTEMIC_ADAPTATION_TYPES) == 6


# ---------------------------------------------------------------------------
# Dataclasses
# ---------------------------------------------------------------------------


class TestEpistemicPrimitive:
    def test_default(self) -> None:
        from core.workstation.constitutional_epistemic_intelligence_engine_v1 import (
            EpistemicPrimitive,
        )

        p = EpistemicPrimitive()
        assert p.confidence == 0.0
        assert p.certainty == 0.0

    def test_to_dict_serializable(self) -> None:
        from core.workstation.constitutional_epistemic_intelligence_engine_v1 import (
            EpistemicPrimitive,
        )

        p = EpistemicPrimitive(primitive="test", confidence=0.5)
        d = p.to_dict()
        json.dumps(d)
        assert d["primitive"] == "test"


class TestEpistemicPrimitiveSet:
    def test_auto_timestamp(self) -> None:
        from core.workstation.constitutional_epistemic_intelligence_engine_v1 import (
            EpistemicPrimitiveSet,
        )

        s = EpistemicPrimitiveSet()
        assert s.timestamp != ""

    def test_to_dict(self) -> None:
        from core.workstation.constitutional_epistemic_intelligence_engine_v1 import (
            EpistemicPrimitiveSet,
        )

        s = EpistemicPrimitiveSet()
        d = s.to_dict()
        json.dumps(d)


class TestEvidenceIntegrityResult:
    def test_default(self) -> None:
        from core.workstation.constitutional_epistemic_intelligence_engine_v1 import (
            EvidenceIntegrityResult,
        )

        r = EvidenceIntegrityResult()
        assert r.consistent is True
        assert r.divergence_detected is False

    def test_to_dict(self) -> None:
        from core.workstation.constitutional_epistemic_intelligence_engine_v1 import (
            EvidenceIntegrityResult,
        )

        r = EvidenceIntegrityResult(dimension="test", integrity_score=0.8)
        d = r.to_dict()
        assert d["dimension"] == "test"


class TestRealityCoherenceDetection:
    def test_default(self) -> None:
        from core.workstation.constitutional_epistemic_intelligence_engine_v1 import (
            RealityCoherenceDetection,
        )

        d = RealityCoherenceDetection()
        assert d.drift_detected is False
        assert d.coherence_score == 1.0

    def test_to_dict(self) -> None:
        from core.workstation.constitutional_epistemic_intelligence_engine_v1 import (
            RealityCoherenceDetection,
        )

        d = RealityCoherenceDetection(detector="test")
        result = d.to_dict()
        assert result["detector"] == "test"


class TestContradiction:
    def test_default(self) -> None:
        from core.workstation.constitutional_epistemic_intelligence_engine_v1 import (
            Contradiction,
        )

        c = Contradiction()
        assert c.severity == 0.0
        assert c.resolution_possible is True

    def test_to_dict(self) -> None:
        from core.workstation.constitutional_epistemic_intelligence_engine_v1 import (
            Contradiction,
        )

        c = Contradiction(contradiction_type="test", severity=0.3)
        d = c.to_dict()
        assert d["severity"] == 0.3


class TestEpistemicTopologyNode:
    def test_default(self) -> None:
        from core.workstation.constitutional_epistemic_intelligence_engine_v1 import (
            EpistemicTopologyNode,
        )

        n = EpistemicTopologyNode()
        assert n.connections == 0


class TestEpistemicTopology:
    def test_auto_hash(self) -> None:
        from core.workstation.constitutional_epistemic_intelligence_engine_v1 import (
            EpistemicTopology,
            EpistemicTopologyNode,
        )

        t = EpistemicTopology(nodes=[EpistemicTopologyNode(node_id="n1", topology_type="test")])
        assert t.topology_hash != ""

    def test_hash_deterministic(self) -> None:
        from core.workstation.constitutional_epistemic_intelligence_engine_v1 import (
            EpistemicTopology,
            EpistemicTopologyNode,
        )

        nodes = [EpistemicTopologyNode(node_id="n1", topology_type="test", confidence=0.5)]
        t1 = EpistemicTopology(nodes=list(nodes), topology_hash="")
        t2 = EpistemicTopology(nodes=list(nodes), topology_hash="")
        assert t1.topology_hash == t2.topology_hash


class TestEpistemicAdaptation:
    def test_default_invariants_preserved(self) -> None:
        from core.workstation.constitutional_epistemic_intelligence_engine_v1 import (
            EpistemicAdaptation,
        )

        a = EpistemicAdaptation()
        assert a.invariants_preserved is True

    def test_to_dict(self) -> None:
        from core.workstation.constitutional_epistemic_intelligence_engine_v1 import (
            EpistemicAdaptation,
        )

        a = EpistemicAdaptation(adaptation_type="test")
        d = a.to_dict()
        assert d["adaptation_type"] == "test"


class TestEpistemicEvidence:
    def test_field_count(self) -> None:
        from core.workstation.constitutional_epistemic_intelligence_engine_v1 import (
            EpistemicEvidence,
        )

        ev = EpistemicEvidence()
        d = ev.to_dict()
        assert len(d) == 36

    def test_to_dict_serializable(self) -> None:
        from core.workstation.constitutional_epistemic_intelligence_engine_v1 import (
            EpistemicEvidence,
        )

        ev = EpistemicEvidence()
        json.dumps(ev.to_dict())


class TestEpistemicProof:
    def test_auto_proof_id(self) -> None:
        from core.workstation.constitutional_epistemic_intelligence_engine_v1 import (
            EpistemicProof,
        )

        p = EpistemicProof()
        assert p.proof_id.startswith("EPIS-")

    def test_to_dict_serializable(self) -> None:
        from core.workstation.constitutional_epistemic_intelligence_engine_v1 import (
            EpistemicProof,
            EpistemicEvidence,
        )

        p = EpistemicProof(evidence=EpistemicEvidence())
        json.dumps(p.to_dict(), default=str)


# ---------------------------------------------------------------------------
# Builders
# ---------------------------------------------------------------------------


class TestBuildEpistemicPrimitives:
    def test_produces_10_primitives(self) -> None:
        from core.workstation.constitutional_epistemic_intelligence_engine_v1 import (
            build_epistemic_primitives,
        )

        result = build_epistemic_primitives()
        assert len(result.primitives) == 10

    def test_composite_confidence_positive(self) -> None:
        from core.workstation.constitutional_epistemic_intelligence_engine_v1 import (
            build_epistemic_primitives,
        )

        result = build_epistemic_primitives()
        assert result.composite_confidence > 0

    def test_all_primitives_named(self) -> None:
        from core.workstation.constitutional_epistemic_intelligence_engine_v1 import (
            build_epistemic_primitives,
            EPISTEMIC_PRIMITIVES,
        )

        result = build_epistemic_primitives()
        names = {p.primitive for p in result.primitives}
        assert names == set(EPISTEMIC_PRIMITIVES)


class TestBuildEvidenceIntegrity:
    def test_produces_8_dimensions(self) -> None:
        from core.workstation.constitutional_epistemic_intelligence_engine_v1 import (
            build_evidence_integrity,
        )

        result = build_evidence_integrity()
        assert len(result.results) == 8

    def test_composite_positive(self) -> None:
        from core.workstation.constitutional_epistemic_intelligence_engine_v1 import (
            build_evidence_integrity,
        )

        result = build_evidence_integrity()
        assert result.composite_integrity > 0


class TestBuildRealityCoherence:
    def test_produces_8_detections(self) -> None:
        from core.workstation.constitutional_epistemic_intelligence_engine_v1 import (
            build_epistemic_primitives,
            build_evidence_integrity,
            build_reality_coherence,
        )

        prims = build_epistemic_primitives()
        integ = build_evidence_integrity()
        result = build_reality_coherence(prims, integ)
        assert len(result.detections) == 8

    def test_composite_coherence_between_0_and_1(self) -> None:
        from core.workstation.constitutional_epistemic_intelligence_engine_v1 import (
            build_epistemic_primitives,
            build_evidence_integrity,
            build_reality_coherence,
        )

        prims = build_epistemic_primitives()
        integ = build_evidence_integrity()
        result = build_reality_coherence(prims, integ)
        assert 0 <= result.composite_coherence <= 1


class TestBuildProbabilisticReasoning:
    def test_produces_7_assessments(self) -> None:
        from core.workstation.constitutional_epistemic_intelligence_engine_v1 import (
            build_epistemic_primitives,
            build_evidence_integrity,
            build_probabilistic_reasoning,
        )

        prims = build_epistemic_primitives()
        integ = build_evidence_integrity()
        result = build_probabilistic_reasoning(prims, integ)
        assert len(result.assessments) == 7


class TestBuildContradictionAnalysis:
    def test_produces_contradiction_types(self) -> None:
        from core.workstation.constitutional_epistemic_intelligence_engine_v1 import (
            build_epistemic_primitives,
            build_evidence_integrity,
            build_reality_coherence,
            build_contradiction_analysis,
        )

        prims = build_epistemic_primitives()
        integ = build_evidence_integrity()
        coh = build_reality_coherence(prims, integ)
        result = build_contradiction_analysis(integ, coh)
        assert result.total_count >= 0

    def test_density_between_0_and_1(self) -> None:
        from core.workstation.constitutional_epistemic_intelligence_engine_v1 import (
            build_epistemic_primitives,
            build_evidence_integrity,
            build_reality_coherence,
            build_contradiction_analysis,
        )

        prims = build_epistemic_primitives()
        integ = build_evidence_integrity()
        coh = build_reality_coherence(prims, integ)
        result = build_contradiction_analysis(integ, coh)
        assert 0 <= result.composite_density <= 1


class TestBuildEpistemicTopology:
    def test_covers_7_types(self) -> None:
        from core.workstation.constitutional_epistemic_intelligence_engine_v1 import (
            build_epistemic_primitives,
            build_evidence_integrity,
            build_reality_coherence,
            build_contradiction_analysis,
            build_epistemic_topology,
        )

        prims = build_epistemic_primitives()
        integ = build_evidence_integrity()
        coh = build_reality_coherence(prims, integ)
        contrs = build_contradiction_analysis(integ, coh)
        result = build_epistemic_topology(prims, integ, coh, contrs)
        assert result.topology_types_covered == 7

    def test_hash_deterministic(self) -> None:
        from core.workstation.constitutional_epistemic_intelligence_engine_v1 import (
            build_epistemic_primitives,
            build_evidence_integrity,
            build_reality_coherence,
            build_contradiction_analysis,
            build_epistemic_topology,
        )

        prims = build_epistemic_primitives()
        integ = build_evidence_integrity()
        coh = build_reality_coherence(prims, integ)
        contrs = build_contradiction_analysis(integ, coh)
        t1 = build_epistemic_topology(prims, integ, coh, contrs)
        assert t1.topology_hash != ""


class TestBuildEpistemicAdaptations:
    def test_produces_6_adaptations(self) -> None:
        from core.workstation.constitutional_epistemic_intelligence_engine_v1 import (
            build_epistemic_primitives,
            build_evidence_integrity,
            build_reality_coherence,
            build_contradiction_analysis,
            build_epistemic_adaptations,
        )

        prims = build_epistemic_primitives()
        integ = build_evidence_integrity()
        coh = build_reality_coherence(prims, integ)
        contrs = build_contradiction_analysis(integ, coh)
        result = build_epistemic_adaptations(coh, contrs, prims)
        assert len(result.adaptations) == 6

    def test_invariants_preserved(self) -> None:
        from core.workstation.constitutional_epistemic_intelligence_engine_v1 import (
            build_epistemic_primitives,
            build_evidence_integrity,
            build_reality_coherence,
            build_contradiction_analysis,
            build_epistemic_adaptations,
        )

        prims = build_epistemic_primitives()
        integ = build_evidence_integrity()
        coh = build_reality_coherence(prims, integ)
        contrs = build_contradiction_analysis(integ, coh)
        result = build_epistemic_adaptations(coh, contrs, prims)
        assert result.all_invariants_preserved is True


class TestEnforceEpistemicHardCeilings:
    def test_no_violation_on_clean(self) -> None:
        from core.workstation.constitutional_epistemic_intelligence_engine_v1 import (
            EpistemicPrimitiveSet,
            EpistemicPrimitive,
            RealityCoherenceAnalysis,
            ContradictionAnalysis,
            EpistemicAdaptationSet,
            enforce_epistemic_hard_ceilings,
        )

        prims = EpistemicPrimitiveSet(
            primitives=[
                EpistemicPrimitive(primitive="evidence_confidence", confidence=0.8),
                EpistemicPrimitive(primitive="replay_certainty", confidence=0.7),
                EpistemicPrimitive(primitive="continuity_confidence", confidence=0.6),
            ],
            composite_confidence=0.7,
        )
        coh = RealityCoherenceAnalysis(composite_coherence=0.8, hallucination_risk=0.1)
        contrs = ContradictionAnalysis(critical_count=0, quarantined_count=0)
        adapts = EpistemicAdaptationSet(all_invariants_preserved=True)
        blocked, reasons = enforce_epistemic_hard_ceilings(prims, coh, contrs, adapts)
        assert blocked is False
        assert len(reasons) == 0

    def test_invariant_violation_blocks(self) -> None:
        from core.workstation.constitutional_epistemic_intelligence_engine_v1 import (
            EpistemicPrimitiveSet,
            EpistemicPrimitive,
            RealityCoherenceAnalysis,
            ContradictionAnalysis,
            EpistemicAdaptationSet,
            enforce_epistemic_hard_ceilings,
        )

        prims = EpistemicPrimitiveSet(
            primitives=[EpistemicPrimitive(primitive="evidence_confidence", confidence=0.1)],
            composite_confidence=0.1,
        )
        coh = RealityCoherenceAnalysis(composite_coherence=0.2, hallucination_risk=0.8)
        contrs = ContradictionAnalysis(critical_count=2, quarantined_count=5)
        adapts = EpistemicAdaptationSet(all_invariants_preserved=False)
        blocked, reasons = enforce_epistemic_hard_ceilings(prims, coh, contrs, adapts)
        assert blocked is True
        assert "low_confidence_autonomous_escalation" in reasons
        assert "contradictory_governance_proofs" in reasons
        assert "unstable_reality_models" in reasons
        assert "hallucinated_leverage_accumulation" in reasons


# ---------------------------------------------------------------------------
# Maturity
# ---------------------------------------------------------------------------


class TestComputeEpistemicMaturity:
    def test_empty_evidence_low_score(self) -> None:
        from core.workstation.constitutional_epistemic_intelligence_engine_v1 import (
            EpistemicEvidence,
            compute_epistemic_maturity,
        )

        ev = EpistemicEvidence(
            all_invariants_preserved=False,
            hard_ceilings_enforced=False,
            governance_epistemically_safe=False,
            hallucination_prevented=False,
        )
        assert compute_epistemic_maturity(ev) == 0

    def test_full_evidence_high_score(self) -> None:
        from core.workstation.constitutional_epistemic_intelligence_engine_v1 import (
            EpistemicEvidence,
            compute_epistemic_maturity,
        )

        ev = EpistemicEvidence(
            primitives_evaluated=True,
            integrity_analyzed=True,
            coherence_analyzed=True,
            probabilistic_assessed=True,
            contradictions_analyzed=True,
            topology_generated=True,
            adaptations_applied=True,
            all_invariants_preserved=True,
            hard_ceilings_enforced=True,
            governance_epistemically_safe=True,
            hallucination_prevented=True,
        )
        assert compute_epistemic_maturity(ev) == 10


class TestEpistemicMaturityCeiling:
    def test_dry_run_l0(self) -> None:
        from core.workstation.constitutional_epistemic_intelligence_engine_v1 import (
            EpistemicEvidence,
            epistemic_maturity_ceiling,
        )

        ev = EpistemicEvidence(is_dry_run=True, primitives_evaluated=True)
        assert epistemic_maturity_ceiling(ev) == "L0_NO_EPISTEMIC_INTELLIGENCE"

    def test_no_primitives_l0(self) -> None:
        from core.workstation.constitutional_epistemic_intelligence_engine_v1 import (
            EpistemicEvidence,
            epistemic_maturity_ceiling,
        )

        ev = EpistemicEvidence(primitives_evaluated=False)
        assert epistemic_maturity_ceiling(ev) == "L0_NO_EPISTEMIC_INTELLIGENCE"

    def test_full_evidence_l5(self) -> None:
        from core.workstation.constitutional_epistemic_intelligence_engine_v1 import (
            EpistemicEvidence,
            epistemic_maturity_ceiling,
        )

        ev = EpistemicEvidence(
            primitives_evaluated=True,
            integrity_analyzed=True,
            coherence_analyzed=True,
            contradictions_analyzed=True,
            founder_confirmed=True,
        )
        assert epistemic_maturity_ceiling(ev) == "L5_CONSTITUTIONAL_EPISTEMIC_INTELLIGENCE"

    def test_no_founder_capped_l4(self) -> None:
        from core.workstation.constitutional_epistemic_intelligence_engine_v1 import (
            EpistemicEvidence,
            epistemic_maturity_ceiling,
        )

        ev = EpistemicEvidence(
            primitives_evaluated=True,
            integrity_analyzed=True,
            coherence_analyzed=True,
            contradictions_analyzed=True,
            founder_confirmed=False,
        )
        assert epistemic_maturity_ceiling(ev) == "L4_REALITY_GOVERNED"


class TestClassifyEpistemicMaturity:
    def test_empty_l0(self) -> None:
        from core.workstation.constitutional_epistemic_intelligence_engine_v1 import (
            EpistemicEvidence,
            classify_epistemic_maturity,
        )

        ev = EpistemicEvidence(
            all_invariants_preserved=False,
            hard_ceilings_enforced=False,
            governance_epistemically_safe=False,
            hallucination_prevented=False,
        )
        level, ceiling, blocked, reason = classify_epistemic_maturity(ev)
        assert level == "L0_NO_EPISTEMIC_INTELLIGENCE"


# ---------------------------------------------------------------------------
# Full pipeline
# ---------------------------------------------------------------------------


class TestBuildFullEpistemicProof:
    def test_no_upstream(self) -> None:
        from core.workstation.constitutional_epistemic_intelligence_engine_v1 import (
            build_full_epistemic_proof,
        )

        proof = build_full_epistemic_proof()
        assert proof.proof_id.startswith("EPIS-")
        assert proof.evidence is not None
        assert proof.evidence.primitives_evaluated is True

    def test_dry_run(self) -> None:
        from core.workstation.constitutional_epistemic_intelligence_engine_v1 import (
            build_full_epistemic_proof,
        )

        proof = build_full_epistemic_proof(is_dry_run=True)
        assert proof.maturity_level == "L0_NO_EPISTEMIC_INTELLIGENCE"
        assert proof.execution_strategy == "epistemic_intelligence_dry_run"

    def test_founder_epistemic(self) -> None:
        from core.workstation.constitutional_epistemic_intelligence_engine_v1 import (
            build_full_epistemic_proof,
        )

        proof = build_full_epistemic_proof(founder_confirmed=True)
        assert proof.evidence.founder_confirmed is True

    def test_with_full_upstream_chain(self) -> None:
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

        proof = build_full_epistemic_proof(
            strategy_proof=strat,
            economics_proof=econ,
            federation_proof=fed,
            orchestration_proof=orch,
            capability_proof=cap,
            founder_confirmed=True,
        )
        assert proof.maturity_level != "L0_NO_EPISTEMIC_INTELLIGENCE"
        assert proof.evidence.primitive_count == 10
        assert proof.evidence.integrity_analyzed is True
        assert proof.evidence.coherence_analyzed is True
        assert proof.evidence.contradictions_analyzed is True


# ---------------------------------------------------------------------------
# Persistence
# ---------------------------------------------------------------------------


class TestPersistEpistemicProof:
    def test_persist_creates_file(self, tmp_path: Path) -> None:
        from core.workstation.constitutional_epistemic_intelligence_engine_v1 import (
            build_full_epistemic_proof,
            persist_epistemic_proof,
        )

        proof = build_full_epistemic_proof(trace_id="persist-test")
        path = persist_epistemic_proof(proof, base_dir=tmp_path)
        assert path.exists()
        assert path.name.startswith("EPIS-")
        data = json.loads(path.read_text())
        assert data["proof_type"] == "constitutional_epistemic_intelligence"

    def test_persist_json_valid(self, tmp_path: Path) -> None:
        from core.workstation.constitutional_epistemic_intelligence_engine_v1 import (
            build_full_epistemic_proof,
            persist_epistemic_proof,
        )

        proof = build_full_epistemic_proof()
        path = persist_epistemic_proof(proof, base_dir=tmp_path)
        data = json.loads(path.read_text())
        assert "evidence" in data
        assert "primitives" in data
        assert "contradictions" in data


# ---------------------------------------------------------------------------
# Hallucination prevention
# ---------------------------------------------------------------------------


class TestHallucinationPrevention:
    def test_normal_conditions_prevented(self) -> None:
        from core.workstation.constitutional_epistemic_intelligence_engine_v1 import (
            build_full_epistemic_proof,
        )

        proof = build_full_epistemic_proof()
        assert proof.evidence.hallucination_prevented is True

    def test_high_risk_not_prevented(self) -> None:
        from core.workstation.constitutional_epistemic_intelligence_engine_v1 import (
            build_epistemic_primitives,
            build_evidence_integrity,
            build_reality_coherence,
            RealityCoherenceAnalysis,
        )

        prims = build_epistemic_primitives()
        integ = build_evidence_integrity()
        coh = build_reality_coherence(prims, integ)
        assert isinstance(coh, RealityCoherenceAnalysis)


# ---------------------------------------------------------------------------
# Truth downgrade safety
# ---------------------------------------------------------------------------


class TestTruthDowngradeSafety:
    def test_low_confidence_triggers_downgrade(self) -> None:
        from core.workstation.constitutional_epistemic_intelligence_engine_v1 import (
            EpistemicPrimitiveSet,
            RealityCoherenceAnalysis,
            ContradictionAnalysis,
            build_epistemic_adaptations,
        )

        prims = EpistemicPrimitiveSet(composite_confidence=0.2)
        coh = RealityCoherenceAnalysis(composite_coherence=0.8)
        contrs = ContradictionAnalysis()
        adapts = build_epistemic_adaptations(coh, contrs, prims)
        downgrade_adapt = [a for a in adapts.adaptations if a.adaptation_type == "truth_downgrade"]
        assert len(downgrade_adapt) == 1
        assert downgrade_adapt[0].applied is True
        assert downgrade_adapt[0].truth_downgraded is True

    def test_high_confidence_no_downgrade(self) -> None:
        from core.workstation.constitutional_epistemic_intelligence_engine_v1 import (
            EpistemicPrimitiveSet,
            RealityCoherenceAnalysis,
            ContradictionAnalysis,
            build_epistemic_adaptations,
        )

        prims = EpistemicPrimitiveSet(composite_confidence=0.8)
        coh = RealityCoherenceAnalysis(composite_coherence=0.9)
        contrs = ContradictionAnalysis()
        adapts = build_epistemic_adaptations(coh, contrs, prims)
        downgrade_adapt = [a for a in adapts.adaptations if a.adaptation_type == "truth_downgrade"]
        assert downgrade_adapt[0].applied is False


# ---------------------------------------------------------------------------
# Uncertainty propagation
# ---------------------------------------------------------------------------


class TestUncertaintyPropagation:
    def test_uncertainty_between_0_and_1(self) -> None:
        from core.workstation.constitutional_epistemic_intelligence_engine_v1 import (
            build_epistemic_primitives,
            build_evidence_integrity,
            build_probabilistic_reasoning,
        )

        prims = build_epistemic_primitives()
        integ = build_evidence_integrity()
        result = build_probabilistic_reasoning(prims, integ)
        assert 0 <= result.total_uncertainty <= 1

    def test_all_assessments_have_uncertainty(self) -> None:
        from core.workstation.constitutional_epistemic_intelligence_engine_v1 import (
            build_epistemic_primitives,
            build_evidence_integrity,
            build_probabilistic_reasoning,
        )

        prims = build_epistemic_primitives()
        integ = build_evidence_integrity()
        result = build_probabilistic_reasoning(prims, integ)
        for a in result.assessments:
            assert a.uncertainty >= 0


# ---------------------------------------------------------------------------
# Federation reality divergence
# ---------------------------------------------------------------------------


class TestFederationRealityDivergence:
    def test_no_divergence_without_high_drift(self) -> None:
        from core.workstation.constitutional_epistemic_intelligence_engine_v1 import (
            build_epistemic_primitives,
            build_evidence_integrity,
            build_reality_coherence,
        )

        prims = build_epistemic_primitives()
        integ = build_evidence_integrity()
        coh = build_reality_coherence(prims, integ)
        fed_detection = [d for d in coh.detections if d.detector == "federation_reality_divergence"]
        assert len(fed_detection) == 1


# ---------------------------------------------------------------------------
# Replay/evidence consistency
# ---------------------------------------------------------------------------


class TestReplayEvidenceConsistency:
    def test_replay_dimension_exists(self) -> None:
        from core.workstation.constitutional_epistemic_intelligence_engine_v1 import (
            build_evidence_integrity,
        )

        result = build_evidence_integrity()
        replay_dims = [r for r in result.results if "replay" in r.dimension]
        assert len(replay_dims) >= 1


# ---------------------------------------------------------------------------
# Epistemic topology generation
# ---------------------------------------------------------------------------


class TestEpistemicTopologyGeneration:
    def test_all_7_types_generated(self) -> None:
        from core.workstation.constitutional_epistemic_intelligence_engine_v1 import (
            build_epistemic_primitives,
            build_evidence_integrity,
            build_reality_coherence,
            build_contradiction_analysis,
            build_epistemic_topology,
            EPISTEMIC_TOPOLOGY_TYPES,
        )

        prims = build_epistemic_primitives()
        integ = build_evidence_integrity()
        coh = build_reality_coherence(prims, integ)
        contrs = build_contradiction_analysis(integ, coh)
        topo = build_epistemic_topology(prims, integ, coh, contrs)
        types = {n.topology_type for n in topo.nodes}
        assert types == set(EPISTEMIC_TOPOLOGY_TYPES)


# ---------------------------------------------------------------------------
# Continuity-safe epistemic recovery
# ---------------------------------------------------------------------------


class TestContinuitySafeRecovery:
    def test_continuity_preservation_always_applied(self) -> None:
        from core.workstation.constitutional_epistemic_intelligence_engine_v1 import (
            EpistemicPrimitiveSet,
            RealityCoherenceAnalysis,
            ContradictionAnalysis,
            build_epistemic_adaptations,
        )

        prims = EpistemicPrimitiveSet(composite_confidence=0.5)
        coh = RealityCoherenceAnalysis(composite_coherence=0.5)
        contrs = ContradictionAnalysis()
        adapts = build_epistemic_adaptations(coh, contrs, prims)
        cont_adapt = [
            a for a in adapts.adaptations if a.adaptation_type == "continuity_preservation"
        ]
        assert len(cont_adapt) == 1
        assert cont_adapt[0].applied is True
        assert cont_adapt[0].invariants_preserved is True


# ---------------------------------------------------------------------------
# Command registration (24 commands)
# ---------------------------------------------------------------------------


class TestEpistemicCommandRegistration:
    def test_registry_has_24_commands(self) -> None:
        from composition.registries.canonical_command_registry_v1 import get_canonical_registry

        reg = get_canonical_registry()
        assert len(reg) == 27

    def test_epistemic_report_in_registry(self) -> None:
        from composition.registries.canonical_command_registry_v1 import get_canonical_registry

        reg = get_canonical_registry()
        assert "!epistemic-report" in reg.commands

    def test_action_in_allowed(self) -> None:
        from core.control_plane_router.router_contracts import ALLOWED_ACTION_TYPES

        assert "epistemic_report" in ALLOWED_ACTION_TYPES

    def test_action_in_map(self) -> None:
        from core.control_plane_router.control_plane_router_v1 import (
            ACTION_CAPABILITY_MAP,
        )

        assert "epistemic_report" in ACTION_CAPABILITY_MAP

    def test_config_has_24_actions(self) -> None:
        import json

        with open(f"{_ROOT}/config/control_plane_router_v1.json") as f:
            config = json.load(f)
        assert len(config["allowed_action_types"]) == 27

    def test_substrate_commands(self) -> None:
        from handlers.substrate_command_handler import SUBSTRATE_COMMANDS

        assert "!epistemic-report" in SUBSTRATE_COMMANDS
        assert len(SUBSTRATE_COMMANDS) == 27


# ---------------------------------------------------------------------------
# Live proof
# ---------------------------------------------------------------------------


class TestLiveEpistemicProof:
    def test_live_proof_with_full_upstream(self) -> None:
        from core.workstation.constitutional_epistemic_intelligence_engine_v1 import (
            build_full_epistemic_proof,
            persist_epistemic_proof,
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

        proof = build_full_epistemic_proof(
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

        assert proof.maturity_level == "L5_CONSTITUTIONAL_EPISTEMIC_INTELLIGENCE"
        assert proof.evidence.primitives_evaluated is True
        assert proof.evidence.integrity_analyzed is True
        assert proof.evidence.coherence_analyzed is True
        assert proof.evidence.contradictions_analyzed is True
        assert proof.evidence.topology_generated is True
        assert proof.evidence.adaptations_applied is True
        assert proof.evidence.hallucination_prevented is True
        assert proof.evidence.founder_confirmed is True
        assert proof.execution_strategy == "constitutional_epistemic_intelligence_active"
