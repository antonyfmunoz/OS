"""Tests for constitutional antifragility and evolutionary resilience engine v1."""

from __future__ import annotations

import json
import sys
import tempfile
import uuid
from pathlib import Path

import pytest

import os
sys.path.insert(0, os.environ.get("UMH_ROOT") or os.environ.get("OS_ROOT") or os.environ.get("EOS_ROOT") or "/opt/OS")
_ROOT = os.environ.get("UMH_ROOT") or os.environ.get("OS_ROOT") or os.environ.get("EOS_ROOT") or "/opt/OS"


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------


class TestResilienceConstants:
    def test_maturity_levels_count(self) -> None:
        from core.workstation.constitutional_antifragility_resilience_engine_v1 import (
            RESILIENCE_MATURITY_LEVELS,
        )

        assert len(RESILIENCE_MATURITY_LEVELS) == 6

    def test_maturity_levels_order(self) -> None:
        from core.workstation.constitutional_antifragility_resilience_engine_v1 import (
            RESILIENCE_MATURITY_LEVELS,
        )

        assert RESILIENCE_MATURITY_LEVELS[0] == "L0_NO_RESILIENCE_ANALYSIS"
        assert RESILIENCE_MATURITY_LEVELS[5] == "L5_CONSTITUTIONAL_ANTIFRAGILITY"

    def test_primitives_count(self) -> None:
        from core.workstation.constitutional_antifragility_resilience_engine_v1 import (
            RESILIENCE_PRIMITIVES,
        )

        assert len(RESILIENCE_PRIMITIVES) == 10

    def test_catastrophic_scenario_count(self) -> None:
        from core.workstation.constitutional_antifragility_resilience_engine_v1 import (
            CATASTROPHIC_SCENARIO_TYPES,
        )

        assert len(CATASTROPHIC_SCENARIO_TYPES) == 10

    def test_antifragility_dimensions_count(self) -> None:
        from core.workstation.constitutional_antifragility_resilience_engine_v1 import (
            ANTIFRAGILITY_DIMENSIONS,
        )

        assert len(ANTIFRAGILITY_DIMENSIONS) == 8

    def test_evolutionary_forecasts_count(self) -> None:
        from core.workstation.constitutional_antifragility_resilience_engine_v1 import (
            EVOLUTIONARY_RESILIENCE_FORECASTS,
        )

        assert len(EVOLUTIONARY_RESILIENCE_FORECASTS) == 8

    def test_existential_risk_count(self) -> None:
        from core.workstation.constitutional_antifragility_resilience_engine_v1 import (
            EXISTENTIAL_RISK_TYPES,
        )

        assert len(EXISTENTIAL_RISK_TYPES) == 8

    def test_topology_types_count(self) -> None:
        from core.workstation.constitutional_antifragility_resilience_engine_v1 import (
            RESILIENCE_TOPOLOGY_TYPES,
        )

        assert len(RESILIENCE_TOPOLOGY_TYPES) == 7

    def test_hard_ceilings_count(self) -> None:
        from core.workstation.constitutional_antifragility_resilience_engine_v1 import (
            RESILIENCE_HARD_CEILINGS,
        )

        assert len(RESILIENCE_HARD_CEILINGS) == 7

    def test_adaptation_types_count(self) -> None:
        from core.workstation.constitutional_antifragility_resilience_engine_v1 import (
            RESILIENCE_ADAPTATION_TYPES,
        )

        assert len(RESILIENCE_ADAPTATION_TYPES) == 6


# ---------------------------------------------------------------------------
# Dataclass tests
# ---------------------------------------------------------------------------


class TestResiliencePrimitive:
    def test_default(self) -> None:
        from core.workstation.constitutional_antifragility_resilience_engine_v1 import (
            ResiliencePrimitive,
        )

        p = ResiliencePrimitive()
        assert p.primitive == ""
        assert p.tolerance == 0.0
        assert p.fragility_score == 0.0

    def test_to_dict_serializable(self) -> None:
        from core.workstation.constitutional_antifragility_resilience_engine_v1 import (
            ResiliencePrimitive,
        )

        p = ResiliencePrimitive(primitive="shock_tolerance", tolerance=0.75)
        d = p.to_dict()
        json.dumps(d)
        assert d["primitive"] == "shock_tolerance"


class TestResiliencePrimitiveSet:
    def test_auto_timestamp(self) -> None:
        from core.workstation.constitutional_antifragility_resilience_engine_v1 import (
            ResiliencePrimitiveSet,
        )

        ps = ResiliencePrimitiveSet()
        assert ps.timestamp != ""

    def test_to_dict(self) -> None:
        from core.workstation.constitutional_antifragility_resilience_engine_v1 import (
            ResiliencePrimitiveSet,
        )

        ps = ResiliencePrimitiveSet()
        d = ps.to_dict()
        json.dumps(d)
        assert "primitives" in d


class TestCatastrophicScenario:
    def test_default(self) -> None:
        from core.workstation.constitutional_antifragility_resilience_engine_v1 import (
            CatastrophicScenario,
        )

        s = CatastrophicScenario()
        assert s.scenario_type == ""
        assert s.severity == 0.0
        assert s.cascading_failures == 0

    def test_to_dict(self) -> None:
        from core.workstation.constitutional_antifragility_resilience_engine_v1 import (
            CatastrophicScenario,
        )

        s = CatastrophicScenario(scenario_type="federation_collapse", severity=0.85)
        d = s.to_dict()
        json.dumps(d)
        assert d["scenario_type"] == "federation_collapse"


class TestAntifragilityDimension:
    def test_default(self) -> None:
        from core.workstation.constitutional_antifragility_resilience_engine_v1 import (
            AntifragilityDimension,
        )

        a = AntifragilityDimension()
        assert a.dimension == ""
        assert a.gain_from_stress == 0.0

    def test_to_dict(self) -> None:
        from core.workstation.constitutional_antifragility_resilience_engine_v1 import (
            AntifragilityDimension,
        )

        a = AntifragilityDimension(dimension="stress_adaptation", gain_from_stress=0.15)
        d = a.to_dict()
        json.dumps(d)
        assert d["dimension"] == "stress_adaptation"


class TestEvolutionaryResilienceForecast:
    def test_default(self) -> None:
        from core.workstation.constitutional_antifragility_resilience_engine_v1 import (
            EvolutionaryResilienceForecast,
        )

        f = EvolutionaryResilienceForecast()
        assert f.forecast_type == ""
        assert f.brittleness == 0.0

    def test_to_dict(self) -> None:
        from core.workstation.constitutional_antifragility_resilience_engine_v1 import (
            EvolutionaryResilienceForecast,
        )

        f = EvolutionaryResilienceForecast(
            forecast_type="long_horizon_survivability", horizon_score=0.7
        )
        d = f.to_dict()
        json.dumps(d)
        assert d["forecast_type"] == "long_horizon_survivability"


class TestExistentialRiskDetection:
    def test_default(self) -> None:
        from core.workstation.constitutional_antifragility_resilience_engine_v1 import (
            ExistentialRiskDetection,
        )

        r = ExistentialRiskDetection()
        assert r.risk_type == ""
        assert r.severity == "low"
        assert r.mitigation_available is True

    def test_to_dict(self) -> None:
        from core.workstation.constitutional_antifragility_resilience_engine_v1 import (
            ExistentialRiskDetection,
        )

        r = ExistentialRiskDetection(risk_type="irreversible_drift", severity="critical")
        d = r.to_dict()
        json.dumps(d)
        assert d["severity"] == "critical"


class TestResilienceTopologyNode:
    def test_default(self) -> None:
        from core.workstation.constitutional_antifragility_resilience_engine_v1 import (
            ResilienceTopologyNode,
        )

        n = ResilienceTopologyNode()
        assert n.topology_type == ""
        assert n.single_points_of_failure == 0

    def test_to_dict(self) -> None:
        from core.workstation.constitutional_antifragility_resilience_engine_v1 import (
            ResilienceTopologyNode,
        )

        n = ResilienceTopologyNode(topology_type="survivability_graph", node_count=8, edge_count=15)
        d = n.to_dict()
        json.dumps(d)
        assert d["node_count"] == 8


class TestResilienceTopology:
    def test_auto_hash(self) -> None:
        from core.workstation.constitutional_antifragility_resilience_engine_v1 import (
            ResilienceTopology,
            ResilienceTopologyNode,
        )

        t = ResilienceTopology(nodes=[ResilienceTopologyNode(topology_type="test")])
        assert t.topology_hash != ""

    def test_hash_deterministic(self) -> None:
        from core.workstation.constitutional_antifragility_resilience_engine_v1 import (
            ResilienceTopology,
            ResilienceTopologyNode,
        )

        nodes = [ResilienceTopologyNode(topology_type="test", node_count=5)]
        t1 = ResilienceTopology(nodes=nodes)
        t2 = ResilienceTopology(nodes=nodes)
        assert t1.topology_hash == t2.topology_hash


class TestResilienceAdaptation:
    def test_default_invariants_preserved(self) -> None:
        from core.workstation.constitutional_antifragility_resilience_engine_v1 import (
            ResilienceAdaptation,
        )

        a = ResilienceAdaptation()
        assert a.invariants_preserved is True

    def test_to_dict(self) -> None:
        from core.workstation.constitutional_antifragility_resilience_engine_v1 import (
            ResilienceAdaptation,
        )

        a = ResilienceAdaptation(
            adaptation_type="fragile_strategy_reweighting",
            target="high_fragility",
        )
        d = a.to_dict()
        json.dumps(d)
        assert d["adaptation_type"] == "fragile_strategy_reweighting"


class TestResilienceEvidence:
    def test_field_count(self) -> None:
        from core.workstation.constitutional_antifragility_resilience_engine_v1 import (
            ResilienceEvidence,
        )
        import dataclasses

        assert len(dataclasses.fields(ResilienceEvidence)) == 40

    def test_to_dict_serializable(self) -> None:
        from core.workstation.constitutional_antifragility_resilience_engine_v1 import (
            ResilienceEvidence,
        )

        ev = ResilienceEvidence()
        d = ev.to_dict()
        s = json.dumps(d)
        assert len(d) == 40


class TestResilienceProof:
    def test_auto_proof_id(self) -> None:
        from core.workstation.constitutional_antifragility_resilience_engine_v1 import (
            ResilienceProof,
        )

        p = ResilienceProof()
        assert p.proof_id.startswith("RESIL-")

    def test_to_dict_serializable(self) -> None:
        from core.workstation.constitutional_antifragility_resilience_engine_v1 import (
            ResilienceProof,
            ResilienceEvidence,
        )

        p = ResilienceProof(evidence=ResilienceEvidence())
        d = p.to_dict()
        json.dumps(d)
        assert d["proof_type"] == "constitutional_antifragility_resilience"


# ---------------------------------------------------------------------------
# Builder tests
# ---------------------------------------------------------------------------


class TestBuildResiliencePrimitives:
    def test_produces_10_primitives(self) -> None:
        from core.workstation.constitutional_antifragility_resilience_engine_v1 import (
            build_resilience_primitives,
        )

        ps = build_resilience_primitives()
        assert len(ps.primitives) == 10

    def test_composite_tolerance_positive(self) -> None:
        from core.workstation.constitutional_antifragility_resilience_engine_v1 import (
            build_resilience_primitives,
        )

        ps = build_resilience_primitives()
        assert ps.composite_tolerance > 0

    def test_all_primitives_named(self) -> None:
        from core.workstation.constitutional_antifragility_resilience_engine_v1 import (
            build_resilience_primitives,
            RESILIENCE_PRIMITIVES,
        )

        ps = build_resilience_primitives()
        names = {p.primitive for p in ps.primitives}
        assert names == set(RESILIENCE_PRIMITIVES)


class TestBuildCatastropheSimulation:
    def test_produces_10_scenarios(self) -> None:
        from core.workstation.constitutional_antifragility_resilience_engine_v1 import (
            build_resilience_primitives,
            build_catastrophe_simulation,
        )

        ps = build_resilience_primitives()
        cs = build_catastrophe_simulation(ps)
        assert cs.total_scenarios == 10
        assert len(cs.scenarios) == 10

    def test_all_types_covered(self) -> None:
        from core.workstation.constitutional_antifragility_resilience_engine_v1 import (
            build_resilience_primitives,
            build_catastrophe_simulation,
            CATASTROPHIC_SCENARIO_TYPES,
        )

        ps = build_resilience_primitives()
        cs = build_catastrophe_simulation(ps)
        types = {s.scenario_type for s in cs.scenarios}
        assert types == set(CATASTROPHIC_SCENARIO_TYPES)

    def test_worst_case_identified(self) -> None:
        from core.workstation.constitutional_antifragility_resilience_engine_v1 import (
            build_resilience_primitives,
            build_catastrophe_simulation,
        )

        ps = build_resilience_primitives()
        cs = build_catastrophe_simulation(ps)
        assert cs.worst_case_scenario != ""


class TestBuildAntifragilityAnalysis:
    def test_produces_8_dimensions(self) -> None:
        from core.workstation.constitutional_antifragility_resilience_engine_v1 import (
            build_resilience_primitives,
            build_catastrophe_simulation,
            build_antifragility_analysis,
        )

        ps = build_resilience_primitives()
        cs = build_catastrophe_simulation(ps)
        af = build_antifragility_analysis(ps, cs)
        assert len(af.dimensions) == 8

    def test_all_dimensions_covered(self) -> None:
        from core.workstation.constitutional_antifragility_resilience_engine_v1 import (
            build_resilience_primitives,
            build_catastrophe_simulation,
            build_antifragility_analysis,
            ANTIFRAGILITY_DIMENSIONS,
        )

        ps = build_resilience_primitives()
        cs = build_catastrophe_simulation(ps)
        af = build_antifragility_analysis(ps, cs)
        dims = {d.dimension for d in af.dimensions}
        assert dims == set(ANTIFRAGILITY_DIMENSIONS)

    def test_stress_counts_sum(self) -> None:
        from core.workstation.constitutional_antifragility_resilience_engine_v1 import (
            build_resilience_primitives,
            build_catastrophe_simulation,
            build_antifragility_analysis,
        )

        ps = build_resilience_primitives()
        cs = build_catastrophe_simulation(ps)
        af = build_antifragility_analysis(ps, cs)
        assert af.stress_positive_count + af.stress_negative_count == 8


class TestBuildEvolutionaryResilience:
    def test_produces_8_forecasts(self) -> None:
        from core.workstation.constitutional_antifragility_resilience_engine_v1 import (
            build_resilience_primitives,
            build_catastrophe_simulation,
            build_antifragility_analysis,
            build_evolutionary_resilience,
        )

        ps = build_resilience_primitives()
        cs = build_catastrophe_simulation(ps)
        af = build_antifragility_analysis(ps, cs)
        ev = build_evolutionary_resilience(ps, af, cs)
        assert len(ev.forecasts) == 8

    def test_all_types_covered(self) -> None:
        from core.workstation.constitutional_antifragility_resilience_engine_v1 import (
            build_resilience_primitives,
            build_catastrophe_simulation,
            build_antifragility_analysis,
            build_evolutionary_resilience,
            EVOLUTIONARY_RESILIENCE_FORECASTS,
        )

        ps = build_resilience_primitives()
        cs = build_catastrophe_simulation(ps)
        af = build_antifragility_analysis(ps, cs)
        ev = build_evolutionary_resilience(ps, af, cs)
        types = {f.forecast_type for f in ev.forecasts}
        assert types == set(EVOLUTIONARY_RESILIENCE_FORECASTS)


class TestBuildExistentialRiskAnalysis:
    def test_produces_8_risks(self) -> None:
        from core.workstation.constitutional_antifragility_resilience_engine_v1 import (
            build_resilience_primitives,
            build_catastrophe_simulation,
            build_antifragility_analysis,
            build_evolutionary_resilience,
            build_existential_risk_analysis,
        )

        ps = build_resilience_primitives()
        cs = build_catastrophe_simulation(ps)
        af = build_antifragility_analysis(ps, cs)
        ev = build_evolutionary_resilience(ps, af, cs)
        er = build_existential_risk_analysis(ps, cs, ev)
        assert er.total_risk_count == 8
        assert len(er.risks) == 8

    def test_all_types_covered(self) -> None:
        from core.workstation.constitutional_antifragility_resilience_engine_v1 import (
            build_resilience_primitives,
            build_catastrophe_simulation,
            build_antifragility_analysis,
            build_evolutionary_resilience,
            build_existential_risk_analysis,
            EXISTENTIAL_RISK_TYPES,
        )

        ps = build_resilience_primitives()
        cs = build_catastrophe_simulation(ps)
        af = build_antifragility_analysis(ps, cs)
        ev = build_evolutionary_resilience(ps, af, cs)
        er = build_existential_risk_analysis(ps, cs, ev)
        types = {r.risk_type for r in er.risks}
        assert types == set(EXISTENTIAL_RISK_TYPES)


class TestBuildResilienceTopology:
    def test_covers_7_types(self) -> None:
        from core.workstation.constitutional_antifragility_resilience_engine_v1 import (
            build_resilience_primitives,
            build_catastrophe_simulation,
            build_antifragility_analysis,
            build_evolutionary_resilience,
            build_resilience_topology,
        )

        ps = build_resilience_primitives()
        cs = build_catastrophe_simulation(ps)
        af = build_antifragility_analysis(ps, cs)
        ev = build_evolutionary_resilience(ps, af, cs)
        t = build_resilience_topology(ps, cs, af, ev)
        assert len(t.nodes) == 7

    def test_hash_not_empty(self) -> None:
        from core.workstation.constitutional_antifragility_resilience_engine_v1 import (
            build_resilience_primitives,
            build_catastrophe_simulation,
            build_antifragility_analysis,
            build_evolutionary_resilience,
            build_resilience_topology,
        )

        ps = build_resilience_primitives()
        cs = build_catastrophe_simulation(ps)
        af = build_antifragility_analysis(ps, cs)
        ev = build_evolutionary_resilience(ps, af, cs)
        t = build_resilience_topology(ps, cs, af, ev)
        assert t.topology_hash != ""


class TestBuildResilienceAdaptations:
    def test_produces_6_adaptations(self) -> None:
        from core.workstation.constitutional_antifragility_resilience_engine_v1 import (
            build_resilience_primitives,
            build_catastrophe_simulation,
            build_antifragility_analysis,
            build_evolutionary_resilience,
            build_existential_risk_analysis,
            build_resilience_adaptations,
        )

        ps = build_resilience_primitives()
        cs = build_catastrophe_simulation(ps)
        af = build_antifragility_analysis(ps, cs)
        ev = build_evolutionary_resilience(ps, af, cs)
        er = build_existential_risk_analysis(ps, cs, ev)
        ad = build_resilience_adaptations(cs, er, ps, af)
        assert len(ad.adaptations) == 6

    def test_invariants_preserved(self) -> None:
        from core.workstation.constitutional_antifragility_resilience_engine_v1 import (
            build_resilience_primitives,
            build_catastrophe_simulation,
            build_antifragility_analysis,
            build_evolutionary_resilience,
            build_existential_risk_analysis,
            build_resilience_adaptations,
        )

        ps = build_resilience_primitives()
        cs = build_catastrophe_simulation(ps)
        af = build_antifragility_analysis(ps, cs)
        ev = build_evolutionary_resilience(ps, af, cs)
        er = build_existential_risk_analysis(ps, cs, ev)
        ad = build_resilience_adaptations(cs, er, ps, af)
        assert ad.all_invariants_preserved is True


class TestEnforceResilienceHardCeilings:
    def test_no_violation_on_clean(self) -> None:
        from core.workstation.constitutional_antifragility_resilience_engine_v1 import (
            ResilienceEvidence,
            ResilienceAdaptationSet,
            enforce_resilience_hard_ceilings,
        )

        ev = ResilienceEvidence(
            composite_fragility=0.3,
            total_spof_count=5,
            existential_safe=True,
            composite_brittleness=0.4,
        )
        ad = ResilienceAdaptationSet(all_invariants_preserved=True)
        blocked, violations = enforce_resilience_hard_ceilings(ev, ad)
        assert not blocked
        assert len(violations) == 0

    def test_invariant_violation_blocks(self) -> None:
        from core.workstation.constitutional_antifragility_resilience_engine_v1 import (
            ResilienceEvidence,
            ResilienceAdaptationSet,
            enforce_resilience_hard_ceilings,
        )

        ev = ResilienceEvidence()
        ad = ResilienceAdaptationSet(all_invariants_preserved=False)
        blocked, violations = enforce_resilience_hard_ceilings(ev, ad)
        assert blocked
        assert "resilience_invariant_violation" in violations

    def test_high_fragility_blocks(self) -> None:
        from core.workstation.constitutional_antifragility_resilience_engine_v1 import (
            ResilienceEvidence,
            ResilienceAdaptationSet,
            enforce_resilience_hard_ceilings,
        )

        ev = ResilienceEvidence(composite_fragility=0.90)
        ad = ResilienceAdaptationSet(all_invariants_preserved=True)
        blocked, violations = enforce_resilience_hard_ceilings(ev, ad)
        assert blocked
        assert "brittle_optimization_paths" in violations


class TestComputeResilienceMaturity:
    def test_empty_evidence_low_score(self) -> None:
        from core.workstation.constitutional_antifragility_resilience_engine_v1 import (
            ResilienceEvidence,
            compute_resilience_maturity,
        )

        ev = ResilienceEvidence()
        score = compute_resilience_maturity(ev)
        assert score < 0.15

    def test_full_evidence_high_score(self) -> None:
        from core.workstation.constitutional_antifragility_resilience_engine_v1 import (
            ResilienceEvidence,
            compute_resilience_maturity,
        )

        ev = ResilienceEvidence(
            primitives_evaluated=True,
            composite_tolerance=0.8,
            catastrophe_simulated=True,
            mean_survivability=0.7,
            antifragility_measured=True,
            composite_antifragility=0.3,
            evolutionary_forecasted=True,
            composite_survivability=0.7,
            existential_risks_analyzed=True,
            existential_safe=True,
            composite_vulnerability=0.1,
            topology_generated=True,
            composite_redundancy=0.7,
            adaptations_applied=True,
            all_invariants_preserved=True,
            founder_confirmed=True,
        )
        score = compute_resilience_maturity(ev)
        assert score > 0.60


class TestResilienceMaturityCeiling:
    def test_dry_run_l0(self) -> None:
        from core.workstation.constitutional_antifragility_resilience_engine_v1 import (
            ResilienceEvidence,
            resilience_maturity_ceiling,
        )

        ev = ResilienceEvidence(is_dry_run=True)
        assert resilience_maturity_ceiling(ev) == "L0_NO_RESILIENCE_ANALYSIS"

    def test_no_primitives_l0(self) -> None:
        from core.workstation.constitutional_antifragility_resilience_engine_v1 import (
            ResilienceEvidence,
            resilience_maturity_ceiling,
        )

        ev = ResilienceEvidence(primitives_evaluated=False)
        assert resilience_maturity_ceiling(ev) == "L0_NO_RESILIENCE_ANALYSIS"

    def test_full_evidence_l5(self) -> None:
        from core.workstation.constitutional_antifragility_resilience_engine_v1 import (
            ResilienceEvidence,
            resilience_maturity_ceiling,
        )

        ev = ResilienceEvidence(
            primitives_evaluated=True,
            catastrophe_simulated=True,
            antifragility_measured=True,
            evolutionary_forecasted=True,
            existential_risks_analyzed=True,
            topology_generated=True,
            adaptations_applied=True,
            hard_ceilings_enforced=True,
            all_invariants_preserved=True,
            founder_confirmed=True,
        )
        assert resilience_maturity_ceiling(ev) == "L5_CONSTITUTIONAL_ANTIFRAGILITY"

    def test_no_founder_capped_l4(self) -> None:
        from core.workstation.constitutional_antifragility_resilience_engine_v1 import (
            ResilienceEvidence,
            resilience_maturity_ceiling,
        )

        ev = ResilienceEvidence(
            primitives_evaluated=True,
            catastrophe_simulated=True,
            antifragility_measured=True,
            evolutionary_forecasted=True,
            existential_risks_analyzed=True,
            topology_generated=True,
            adaptations_applied=True,
            hard_ceilings_enforced=True,
            all_invariants_preserved=True,
            founder_confirmed=False,
        )
        assert resilience_maturity_ceiling(ev) == "L4_RESILIENCE_RECONCILED"


class TestClassifyResilienceMaturity:
    def test_empty_l0(self) -> None:
        from core.workstation.constitutional_antifragility_resilience_engine_v1 import (
            classify_resilience_maturity,
        )

        assert (
            classify_resilience_maturity(0.0, "L5_CONSTITUTIONAL_ANTIFRAGILITY")
            == "L0_NO_RESILIENCE_ANALYSIS"
        )


# ---------------------------------------------------------------------------
# Full pipeline tests
# ---------------------------------------------------------------------------


class TestBuildFullResilienceProof:
    def test_no_upstream(self) -> None:
        from core.workstation.constitutional_antifragility_resilience_engine_v1 import (
            build_full_resilience_proof,
        )

        proof = build_full_resilience_proof()
        assert proof.proof_id.startswith("RESIL-")
        assert proof.evidence is not None
        assert proof.evidence.primitive_count == 10
        assert proof.evidence.total_scenarios == 10

    def test_dry_run(self) -> None:
        from core.workstation.constitutional_antifragility_resilience_engine_v1 import (
            build_full_resilience_proof,
        )

        proof = build_full_resilience_proof(is_dry_run=True)
        assert proof.maturity_level == "L0_NO_RESILIENCE_ANALYSIS"
        assert proof.evidence.is_dry_run is True

    def test_founder_resilience(self) -> None:
        from core.workstation.constitutional_antifragility_resilience_engine_v1 import (
            build_full_resilience_proof,
        )

        proof = build_full_resilience_proof(founder_confirmed=True)
        assert proof.evidence.founder_confirmed is True
        assert proof.evidence.hard_ceilings_enforced is True
        assert proof.evidence.all_invariants_preserved is True

    def test_with_full_upstream_chain(self) -> None:
        from core.workstation.constitutional_antifragility_resilience_engine_v1 import (
            build_full_resilience_proof,
        )
        from core.workstation.constitutional_telos_alignment_engine_v1 import (
            build_full_telos_proof,
        )
        from core.workstation.constitutional_identity_continuity_engine_v1 import (
            build_full_identity_proof,
        )
        from core.workstation.constitutional_epistemic_intelligence_engine_v1 import (
            build_full_epistemic_proof,
        )

        epis = build_full_epistemic_proof(founder_confirmed=True)
        iden = build_full_identity_proof(epistemic_proof=epis, founder_confirmed=True)
        telos = build_full_telos_proof(identity_proof=iden, founder_confirmed=True)
        proof = build_full_resilience_proof(
            telos_proof=telos,
            epistemic_proof=epis,
            identity_proof=iden,
            founder_confirmed=True,
        )
        assert proof.evidence.upstream_telos_proof == telos.proof_id
        assert proof.evidence.primitive_count == 10
        assert proof.evidence.total_scenarios == 10


class TestPersistResilienceProof:
    def test_persist_creates_file(self) -> None:
        from core.workstation.constitutional_antifragility_resilience_engine_v1 import (
            build_full_resilience_proof,
            persist_resilience_proof,
        )

        proof = build_full_resilience_proof()
        with tempfile.TemporaryDirectory() as td:
            path = persist_resilience_proof(proof, base_dir=Path(td))
            assert path.exists()
            assert proof.proof_id in path.name

    def test_persist_json_valid(self) -> None:
        from core.workstation.constitutional_antifragility_resilience_engine_v1 import (
            build_full_resilience_proof,
            persist_resilience_proof,
        )

        proof = build_full_resilience_proof()
        with tempfile.TemporaryDirectory() as td:
            path = persist_resilience_proof(proof, base_dir=Path(td))
            data = json.loads(path.read_text())
            assert data["proof_id"] == proof.proof_id
            assert data["proof_type"] == "constitutional_antifragility_resilience"


# ---------------------------------------------------------------------------
# Domain-specific tests
# ---------------------------------------------------------------------------


class TestCatastropheSimulationIntegrity:
    def test_survivability_bounded(self) -> None:
        from core.workstation.constitutional_antifragility_resilience_engine_v1 import (
            build_resilience_primitives,
            build_catastrophe_simulation,
        )

        ps = build_resilience_primitives()
        cs = build_catastrophe_simulation(ps)
        for s in cs.scenarios:
            assert 0.0 <= s.survivability <= 1.0

    def test_mean_survivability_computed(self) -> None:
        from core.workstation.constitutional_antifragility_resilience_engine_v1 import (
            build_resilience_primitives,
            build_catastrophe_simulation,
        )

        ps = build_resilience_primitives()
        cs = build_catastrophe_simulation(ps)
        assert cs.mean_survivability > 0.0


class TestAntifragilityMeasurement:
    def test_net_gain_computable(self) -> None:
        from core.workstation.constitutional_antifragility_resilience_engine_v1 import (
            build_resilience_primitives,
            build_catastrophe_simulation,
            build_antifragility_analysis,
        )

        ps = build_resilience_primitives()
        cs = build_catastrophe_simulation(ps)
        af = build_antifragility_analysis(ps, cs)
        assert isinstance(af.net_antifragility_gain, float)


class TestExistentialRiskDetection:
    def test_severity_classification(self) -> None:
        from core.workstation.constitutional_antifragility_resilience_engine_v1 import (
            build_full_resilience_proof,
        )

        proof = build_full_resilience_proof()
        for r in proof.existential_risks.risks:
            assert r.severity in ("low", "medium", "critical")


class TestFederationSurvivability:
    def test_federation_collapse_simulated(self) -> None:
        from core.workstation.constitutional_antifragility_resilience_engine_v1 import (
            build_full_resilience_proof,
        )

        proof = build_full_resilience_proof()
        types = {s.scenario_type for s in proof.catastrophe.scenarios}
        assert "federation_collapse" in types


class TestBrittlenessDetection:
    def test_brittleness_bounded(self) -> None:
        from core.workstation.constitutional_antifragility_resilience_engine_v1 import (
            build_full_resilience_proof,
        )

        proof = build_full_resilience_proof()
        assert 0.0 <= proof.evidence.composite_brittleness <= 1.0


class TestRecursiveSurvivabilityPreservation:
    def test_continuity_adaptation_always_applied(self) -> None:
        from core.workstation.constitutional_antifragility_resilience_engine_v1 import (
            build_full_resilience_proof,
        )

        proof = build_full_resilience_proof()
        types = {a.adaptation_type for a in proof.adaptations.adaptations}
        assert "continuity_instability_preservation" in types


class TestResilienceWeightedOrchestration:
    def test_survivability_priority_applied(self) -> None:
        from core.workstation.constitutional_antifragility_resilience_engine_v1 import (
            build_full_resilience_proof,
        )

        proof = build_full_resilience_proof()
        types = {a.adaptation_type for a in proof.adaptations.adaptations}
        assert "survivability_priority_enforcement" in types


# ---------------------------------------------------------------------------
# Command registration tests
# ---------------------------------------------------------------------------


class TestResilienceCommandRegistration:
    def test_registry_has_27_commands(self) -> None:
        from composition.registries.canonical_command_registry_v1 import get_canonical_registry

        reg = get_canonical_registry()
        assert len(reg) == 27

    def test_resilience_report_in_registry(self) -> None:
        from composition.registries.canonical_command_registry_v1 import get_canonical_registry

        reg = get_canonical_registry()
        assert "!resilience-report" in reg.commands

    def test_action_in_allowed(self) -> None:
        from control_plane.router.router_contracts import ALLOWED_ACTION_TYPES

        assert "resilience_report" in ALLOWED_ACTION_TYPES

    def test_action_in_map(self) -> None:
        from control_plane.router.control_plane_router_v1 import (
            ACTION_CAPABILITY_MAP,
        )

        assert "resilience_report" in ACTION_CAPABILITY_MAP

    def test_config_has_27_actions(self) -> None:
        import json

        with open(f"{_ROOT}/config/control_plane_router_v1.json") as f:
            config = json.load(f)
        assert len(config["allowed_action_types"]) == 27

    def test_substrate_commands(self) -> None:
        sys.path.insert(0, os.path.join(os.environ.get("UMH_ROOT") or os.environ.get("OS_ROOT") or os.environ.get("EOS_ROOT") or "/opt/OS", "services"))
        from handlers.substrate_command_handler import SUBSTRATE_COMMANDS

        assert len(SUBSTRATE_COMMANDS) == 27


# ---------------------------------------------------------------------------
# Live proof test
# ---------------------------------------------------------------------------


class TestLiveResilienceProof:
    def test_live_proof_with_full_upstream(self) -> None:
        from core.workstation.constitutional_antifragility_resilience_engine_v1 import (
            build_full_resilience_proof,
            persist_resilience_proof,
        )
        from core.workstation.constitutional_telos_alignment_engine_v1 import (
            build_full_telos_proof,
        )

        telos = build_full_telos_proof(founder_confirmed=True)
        proof = build_full_resilience_proof(
            telos_proof=telos,
            founder_confirmed=True,
        )

        assert proof.maturity_level != "L0_NO_RESILIENCE_ANALYSIS"
        assert proof.evidence.upstream_telos_proof == telos.proof_id
        assert proof.evidence.hard_ceilings_enforced is True
        assert proof.evidence.all_invariants_preserved is True
        assert proof.evidence.founder_confirmed is True
        assert proof.evidence.primitive_count == 10
        assert proof.evidence.total_scenarios == 10
        assert proof.evidence.topology_types_covered == 7
        assert proof.evidence.adaptations_count == 6

        with tempfile.TemporaryDirectory() as td:
            path = persist_resilience_proof(proof, base_dir=Path(td))
            data = json.loads(path.read_text())
            assert data["proof_type"] == "constitutional_antifragility_resilience"
