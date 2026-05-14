"""Tests for Phase 96.8BC — Constitutional Strategic Intelligence.

Verifies:
  1.  Constants — correct counts and types
  2.  StrategicForecast — projections, trends
  3.  StrategicForecastSet — aggregation, timestamp
  4.  LeverageChain — effective leverage, safety
  5.  RecursiveLeverageModel — chain aggregation
  6.  BottleneckPrediction — severity, impact
  7.  BottleneckForecastSet — critical/high counts
  8.  HorizonSimulationOutcome — ID generation, 9 types
  9.  StrategicSequenceItem — composite priority
  10. StrategicSequence — ordering
  11. StrategicTopology — 7 types, hash
  12. StrategicAdaptation — drift/instability
  13. StrategyEvidence — 30 fields, to_dict
  14. StrategyProof — proof ID, to_dict
  15. build_strategic_forecasts — 9 primitives
  16. build_recursive_leverage_model — safe/unsafe chains
  17. build_bottleneck_predictions — 8 types
  18. run_long_horizon_simulations — 9 types
  19. build_strategic_sequence — 7 items
  20. build_strategic_topology — 7 types
  21. build_strategic_adaptations — 6 types
  22. enforce_strategic_hard_ceilings — ceiling triggers
  23. compute_strategy_maturity — score accumulation
  24. strategy_maturity_ceiling — ceiling classification
  25. classify_strategy_maturity — level clamped by ceiling
  26. build_full_strategy_proof — full pipeline
  27. persist_strategy_proof — file written, JSON valid
  28. Command registration — 23 commands, !strategy-report present
  29. Full upstream proof chain (10 layers deep)
"""

import json
import sys
from pathlib import Path

import pytest

import os
sys.path.insert(0, os.environ.get("UMH_ROOT") or os.environ.get("OS_ROOT") or os.environ.get("EOS_ROOT") or "/opt/OS")
_ROOT = os.environ.get("UMH_ROOT") or os.environ.get("OS_ROOT") or os.environ.get("EOS_ROOT") or "/opt/OS"
sys.path.insert(0, os.path.join(os.environ.get("UMH_ROOT") or os.environ.get("OS_ROOT") or os.environ.get("EOS_ROOT") or "/opt/OS", "services"))


class TestStrategyConstants:
    def test_maturity_levels_count(self) -> None:
        from core.workstation.constitutional_strategic_intelligence_engine_v1 import (
            STRATEGY_MATURITY_LEVELS,
        )

        assert len(STRATEGY_MATURITY_LEVELS) == 6

    def test_maturity_levels_order(self) -> None:
        from core.workstation.constitutional_strategic_intelligence_engine_v1 import (
            STRATEGY_MATURITY_LEVELS,
        )

        assert STRATEGY_MATURITY_LEVELS[0] == "L0_NO_STRATEGIC_INTELLIGENCE"
        assert STRATEGY_MATURITY_LEVELS[5] == "L5_CONSTITUTIONAL_STRATEGIC_INTELLIGENCE"

    def test_forecasting_primitives_count(self) -> None:
        from core.workstation.constitutional_strategic_intelligence_engine_v1 import (
            STRATEGIC_FORECASTING_PRIMITIVES,
        )

        assert len(STRATEGIC_FORECASTING_PRIMITIVES) == 9

    def test_leverage_dimensions_count(self) -> None:
        from core.workstation.constitutional_strategic_intelligence_engine_v1 import (
            RECURSIVE_LEVERAGE_DIMENSIONS,
        )

        assert len(RECURSIVE_LEVERAGE_DIMENSIONS) == 8

    def test_bottleneck_types_count(self) -> None:
        from core.workstation.constitutional_strategic_intelligence_engine_v1 import (
            STRATEGIC_BOTTLENECK_TYPES,
        )

        assert len(STRATEGIC_BOTTLENECK_TYPES) == 8

    def test_simulation_types_count(self) -> None:
        from core.workstation.constitutional_strategic_intelligence_engine_v1 import (
            LONG_HORIZON_SIMULATION_TYPES,
        )

        assert len(LONG_HORIZON_SIMULATION_TYPES) == 9

    def test_sequencing_priorities_count(self) -> None:
        from core.workstation.constitutional_strategic_intelligence_engine_v1 import (
            STRATEGIC_SEQUENCING_PRIORITIES,
        )

        assert len(STRATEGIC_SEQUENCING_PRIORITIES) == 7

    def test_topology_types_count(self) -> None:
        from core.workstation.constitutional_strategic_intelligence_engine_v1 import (
            STRATEGIC_TOPOLOGY_TYPES,
        )

        assert len(STRATEGIC_TOPOLOGY_TYPES) == 7

    def test_hard_ceilings_count(self) -> None:
        from core.workstation.constitutional_strategic_intelligence_engine_v1 import (
            STRATEGIC_HARD_CEILINGS,
        )

        assert len(STRATEGIC_HARD_CEILINGS) == 7
        assert isinstance(STRATEGIC_HARD_CEILINGS, frozenset)

    def test_adaptation_types_count(self) -> None:
        from core.workstation.constitutional_strategic_intelligence_engine_v1 import (
            STRATEGIC_ADAPTATION_TYPES,
        )

        assert len(STRATEGIC_ADAPTATION_TYPES) == 6


class TestStrategicForecast:
    def test_default(self) -> None:
        from core.workstation.constitutional_strategic_intelligence_engine_v1 import (
            StrategicForecast,
        )

        f = StrategicForecast()
        assert f.trend == "stable"
        assert f.risk_level == "low"

    def test_to_dict_serializable(self) -> None:
        from core.workstation.constitutional_strategic_intelligence_engine_v1 import (
            StrategicForecast,
        )

        f = StrategicForecast(primitive="test", current_value=0.5)
        d = f.to_dict()
        assert d["primitive"] == "test"
        s = json.dumps(d)
        assert len(s) > 0


class TestStrategicForecastSet:
    def test_auto_timestamp(self) -> None:
        from core.workstation.constitutional_strategic_intelligence_engine_v1 import (
            StrategicForecastSet,
        )

        fs = StrategicForecastSet()
        assert len(fs.timestamp) > 0

    def test_to_dict(self) -> None:
        from core.workstation.constitutional_strategic_intelligence_engine_v1 import (
            StrategicForecastSet,
        )

        fs = StrategicForecastSet(forecast_count=3)
        d = fs.to_dict()
        assert d["forecast_count"] == 3


class TestLeverageChain:
    def test_effective_leverage_safe(self) -> None:
        from core.workstation.constitutional_strategic_intelligence_engine_v1 import (
            LeverageChain,
        )

        c = LeverageChain(
            leverage_multiplier=1.5,
            order=1,
            compounding_rate=0.1,
            governance_safe=True,
            replay_safe=True,
            continuity_safe=True,
        )
        assert c.effective_leverage() > 0

    def test_effective_leverage_unsafe_zero(self) -> None:
        from core.workstation.constitutional_strategic_intelligence_engine_v1 import (
            LeverageChain,
        )

        c = LeverageChain(governance_safe=False)
        assert c.effective_leverage() == 0.0

    def test_higher_order_compounds(self) -> None:
        from core.workstation.constitutional_strategic_intelligence_engine_v1 import (
            LeverageChain,
        )

        c1 = LeverageChain(
            leverage_multiplier=1.0,
            order=1,
            compounding_rate=0.1,
            governance_safe=True,
            replay_safe=True,
            continuity_safe=True,
        )
        c2 = LeverageChain(
            leverage_multiplier=1.0,
            order=2,
            compounding_rate=0.1,
            governance_safe=True,
            replay_safe=True,
            continuity_safe=True,
        )
        assert c2.effective_leverage() > c1.effective_leverage()


class TestRecursiveLeverageModel:
    def test_default(self) -> None:
        from core.workstation.constitutional_strategic_intelligence_engine_v1 import (
            RecursiveLeverageModel,
        )

        m = RecursiveLeverageModel()
        assert len(m.chains) == 0
        assert m.total_leverage == 0.0

    def test_to_dict(self) -> None:
        from core.workstation.constitutional_strategic_intelligence_engine_v1 import (
            RecursiveLeverageModel,
        )

        m = RecursiveLeverageModel()
        d = m.to_dict()
        assert "chain_count" in d


class TestBottleneckPrediction:
    def test_default(self) -> None:
        from core.workstation.constitutional_strategic_intelligence_engine_v1 import (
            BottleneckPrediction,
        )

        b = BottleneckPrediction()
        assert b.severity == "low"

    def test_to_dict(self) -> None:
        from core.workstation.constitutional_strategic_intelligence_engine_v1 import (
            BottleneckPrediction,
        )

        b = BottleneckPrediction(bottleneck_type="test", severity="high")
        d = b.to_dict()
        assert d["severity"] == "high"


class TestHorizonSimulationOutcome:
    def test_auto_id(self) -> None:
        from core.workstation.constitutional_strategic_intelligence_engine_v1 import (
            HorizonSimulationOutcome,
        )

        s = HorizonSimulationOutcome()
        assert s.simulation_id.startswith("STRSIM-")

    def test_auto_timestamp(self) -> None:
        from core.workstation.constitutional_strategic_intelligence_engine_v1 import (
            HorizonSimulationOutcome,
        )

        s = HorizonSimulationOutcome()
        assert len(s.timestamp) > 0

    def test_to_dict_serializable(self) -> None:
        from core.workstation.constitutional_strategic_intelligence_engine_v1 import (
            HorizonSimulationOutcome,
        )

        s = HorizonSimulationOutcome(simulation_type="test")
        d = s.to_dict()
        assert d["simulation_type"] == "test"
        json.dumps(d)


class TestStrategicSequenceItem:
    def test_composite_priority(self) -> None:
        from core.workstation.constitutional_strategic_intelligence_engine_v1 import (
            StrategicSequenceItem,
        )

        item = StrategicSequenceItem(
            leverage_score=0.8,
            compounding_value=0.7,
            constitutional_reinforcement=0.9,
            governance_risk=0.1,
            blast_radius=0.1,
        )
        assert item.composite_priority() > 0

    def test_to_dict_has_composite(self) -> None:
        from core.workstation.constitutional_strategic_intelligence_engine_v1 import (
            StrategicSequenceItem,
        )

        item = StrategicSequenceItem()
        d = item.to_dict()
        assert "composite_priority" in d


class TestStrategicTopology:
    def test_default(self) -> None:
        from core.workstation.constitutional_strategic_intelligence_engine_v1 import (
            StrategicTopology,
        )

        t = StrategicTopology()
        assert len(t.nodes) == 0

    def test_to_dict(self) -> None:
        from core.workstation.constitutional_strategic_intelligence_engine_v1 import (
            StrategicTopology,
        )

        t = StrategicTopology()
        d = t.to_dict()
        assert "topology_hash" in d


class TestStrategicAdaptation:
    def test_default_invariants_preserved(self) -> None:
        from core.workstation.constitutional_strategic_intelligence_engine_v1 import (
            StrategicAdaptation,
        )

        a = StrategicAdaptation()
        assert a.constitutional_invariants_preserved is True

    def test_to_dict(self) -> None:
        from core.workstation.constitutional_strategic_intelligence_engine_v1 import (
            StrategicAdaptation,
        )

        a = StrategicAdaptation(adaptation_type="test")
        d = a.to_dict()
        assert d["adaptation_type"] == "test"


class TestStrategyEvidence:
    def test_field_count(self) -> None:
        from core.workstation.constitutional_strategic_intelligence_engine_v1 import (
            StrategyEvidence,
        )

        ev = StrategyEvidence()
        d = ev.to_dict()
        assert len(d) == 30

    def test_to_dict_serializable(self) -> None:
        from core.workstation.constitutional_strategic_intelligence_engine_v1 import (
            StrategyEvidence,
        )

        ev = StrategyEvidence(forecasts_generated=True, forecast_count=9)
        s = json.dumps(ev.to_dict())
        assert len(s) > 0


class TestStrategyProof:
    def test_auto_proof_id(self) -> None:
        from core.workstation.constitutional_strategic_intelligence_engine_v1 import (
            StrategyProof,
        )

        p = StrategyProof(trace_id="test")
        assert p.proof_id.startswith("STRAT-")

    def test_to_dict_serializable(self) -> None:
        from core.workstation.constitutional_strategic_intelligence_engine_v1 import (
            StrategyProof,
        )

        p = StrategyProof()
        d = p.to_dict()
        s = json.dumps(d, default=str)
        assert len(s) > 0
        assert d["proof_type"] == "constitutional_strategic_intelligence"


class TestBuildStrategicForecasts:
    def test_produces_9_primitives(self) -> None:
        from core.workstation.constitutional_strategic_intelligence_engine_v1 import (
            STRATEGIC_FORECASTING_PRIMITIVES,
            build_strategic_forecasts,
        )

        fs = build_strategic_forecasts()
        assert fs.forecast_count == 9
        primitives = {f.primitive for f in fs.forecasts}
        assert primitives == set(STRATEGIC_FORECASTING_PRIMITIVES)

    def test_composite_trajectory_positive(self) -> None:
        from core.workstation.constitutional_strategic_intelligence_engine_v1 import (
            build_strategic_forecasts,
        )

        fs = build_strategic_forecasts()
        assert fs.composite_trajectory > 0

    def test_stability_between_0_and_1(self) -> None:
        from core.workstation.constitutional_strategic_intelligence_engine_v1 import (
            build_strategic_forecasts,
        )

        fs = build_strategic_forecasts()
        assert 0 <= fs.trajectory_stability <= 1.0


class TestBuildRecursiveLeverageModel:
    def test_produces_chains(self) -> None:
        from core.workstation.constitutional_strategic_intelligence_engine_v1 import (
            build_recursive_leverage_model,
        )

        m = build_recursive_leverage_model()
        assert len(m.chains) > 0
        assert m.safe_chain_count + m.unsafe_chain_count == len(m.chains)

    def test_has_first_and_second_order(self) -> None:
        from core.workstation.constitutional_strategic_intelligence_engine_v1 import (
            build_recursive_leverage_model,
        )

        m = build_recursive_leverage_model()
        orders = {c.order for c in m.chains}
        assert 1 in orders
        assert 2 in orders

    def test_total_leverage_positive(self) -> None:
        from core.workstation.constitutional_strategic_intelligence_engine_v1 import (
            build_recursive_leverage_model,
        )

        m = build_recursive_leverage_model()
        assert m.total_leverage > 0


class TestBuildBottleneckPredictions:
    def test_produces_8_types(self) -> None:
        from core.workstation.constitutional_strategic_intelligence_engine_v1 import (
            STRATEGIC_BOTTLENECK_TYPES,
            build_bottleneck_predictions,
        )

        bf = build_bottleneck_predictions()
        assert bf.total_count == 8
        types = {p.bottleneck_type for p in bf.predictions}
        assert types == set(STRATEGIC_BOTTLENECK_TYPES)

    def test_counts_consistent(self) -> None:
        from core.workstation.constitutional_strategic_intelligence_engine_v1 import (
            build_bottleneck_predictions,
        )

        bf = build_bottleneck_predictions()
        assert bf.critical_count <= bf.total_count
        assert bf.high_count <= bf.total_count


class TestRunLongHorizonSimulations:
    def test_produces_9_types(self) -> None:
        from core.workstation.constitutional_strategic_intelligence_engine_v1 import (
            LONG_HORIZON_SIMULATION_TYPES,
            build_strategic_forecasts,
            build_recursive_leverage_model,
            run_long_horizon_simulations,
        )

        fs = build_strategic_forecasts()
        lm = build_recursive_leverage_model()
        sims = run_long_horizon_simulations(fs, lm)
        assert len(sims) == 9
        sim_types = {s.simulation_type for s in sims}
        assert sim_types == set(LONG_HORIZON_SIMULATION_TYPES)

    def test_all_have_ids(self) -> None:
        from core.workstation.constitutional_strategic_intelligence_engine_v1 import (
            build_strategic_forecasts,
            build_recursive_leverage_model,
            run_long_horizon_simulations,
        )

        fs = build_strategic_forecasts()
        lm = build_recursive_leverage_model()
        sims = run_long_horizon_simulations(fs, lm)
        for s in sims:
            assert s.simulation_id.startswith("STRSIM-")

    def test_cycle_counts_vary(self) -> None:
        from core.workstation.constitutional_strategic_intelligence_engine_v1 import (
            build_strategic_forecasts,
            build_recursive_leverage_model,
            run_long_horizon_simulations,
        )

        fs = build_strategic_forecasts()
        lm = build_recursive_leverage_model()
        sims = run_long_horizon_simulations(fs, lm)
        cycles = {s.cycles_simulated for s in sims}
        assert 1 in cycles
        assert 5 in cycles
        assert 20 in cycles


class TestBuildStrategicSequence:
    def test_produces_7_items(self) -> None:
        from core.workstation.constitutional_strategic_intelligence_engine_v1 import (
            build_recursive_leverage_model,
            build_bottleneck_predictions,
            build_strategic_sequence,
        )

        lm = build_recursive_leverage_model()
        bf = build_bottleneck_predictions()
        ss = build_strategic_sequence(lm, bf)
        assert len(ss.items) == 7

    def test_items_ranked(self) -> None:
        from core.workstation.constitutional_strategic_intelligence_engine_v1 import (
            build_recursive_leverage_model,
            build_bottleneck_predictions,
            build_strategic_sequence,
        )

        lm = build_recursive_leverage_model()
        bf = build_bottleneck_predictions()
        ss = build_strategic_sequence(lm, bf)
        ranks = [i.priority_rank for i in ss.items]
        assert ranks == list(range(1, 8))


class TestBuildStrategicTopology:
    def test_covers_7_types(self) -> None:
        from core.workstation.constitutional_strategic_intelligence_engine_v1 import (
            build_recursive_leverage_model,
            build_strategic_forecasts,
            build_strategic_topology,
        )

        lm = build_recursive_leverage_model()
        fs = build_strategic_forecasts()
        tp = build_strategic_topology(lm, fs)
        assert tp.topology_types_covered == 7

    def test_hash_deterministic(self) -> None:
        from core.workstation.constitutional_strategic_intelligence_engine_v1 import (
            build_recursive_leverage_model,
            build_strategic_forecasts,
            build_strategic_topology,
        )

        lm = build_recursive_leverage_model()
        fs = build_strategic_forecasts()
        tp1 = build_strategic_topology(lm, fs)
        tp2 = build_strategic_topology(lm, fs)
        assert tp1.topology_hash == tp2.topology_hash
        assert len(tp1.topology_hash) == 16


class TestBuildStrategicAdaptations:
    def test_produces_6_adaptations(self) -> None:
        from core.workstation.constitutional_strategic_intelligence_engine_v1 import (
            STRATEGIC_ADAPTATION_TYPES,
            build_strategic_forecasts,
            build_recursive_leverage_model,
            build_bottleneck_predictions,
            build_strategic_adaptations,
        )

        fs = build_strategic_forecasts()
        lm = build_recursive_leverage_model()
        bf = build_bottleneck_predictions()
        ad = build_strategic_adaptations(fs, lm, bf)
        assert len(ad.adaptations) == 6
        types = {a.adaptation_type for a in ad.adaptations}
        assert types == set(STRATEGIC_ADAPTATION_TYPES)

    def test_invariants_preserved(self) -> None:
        from core.workstation.constitutional_strategic_intelligence_engine_v1 import (
            build_strategic_forecasts,
            build_recursive_leverage_model,
            build_bottleneck_predictions,
            build_strategic_adaptations,
        )

        fs = build_strategic_forecasts()
        lm = build_recursive_leverage_model()
        bf = build_bottleneck_predictions()
        ad = build_strategic_adaptations(fs, lm, bf)
        assert ad.all_invariants_preserved is True


class TestEnforceStrategicHardCeilings:
    def test_no_violation_on_normal(self) -> None:
        from core.workstation.constitutional_strategic_intelligence_engine_v1 import (
            build_strategic_forecasts,
            build_recursive_leverage_model,
            build_bottleneck_predictions,
            build_strategic_adaptations,
            enforce_strategic_hard_ceilings,
        )

        fs = build_strategic_forecasts()
        lm = build_recursive_leverage_model()
        bf = build_bottleneck_predictions()
        ad = build_strategic_adaptations(fs, lm, bf)
        blocked, reasons = enforce_strategic_hard_ceilings(fs, lm, bf, ad)
        assert blocked is False

    def test_invariant_violation_blocks(self) -> None:
        from core.workstation.constitutional_strategic_intelligence_engine_v1 import (
            StrategicForecastSet,
            RecursiveLeverageModel,
            BottleneckForecastSet,
            StrategicAdaptationSet,
            enforce_strategic_hard_ceilings,
        )

        fs = StrategicForecastSet(trajectory_stability=0.8)
        lm = RecursiveLeverageModel()
        bf = BottleneckForecastSet()
        ad = StrategicAdaptationSet(all_invariants_preserved=False)
        blocked, reasons = enforce_strategic_hard_ceilings(fs, lm, bf, ad)
        assert blocked is True
        assert any("constitutional_instability" in r for r in reasons)


class TestComputeStrategyMaturity:
    def test_empty_evidence_low_score(self) -> None:
        from core.workstation.constitutional_strategic_intelligence_engine_v1 import (
            StrategyEvidence,
            compute_strategy_maturity,
        )

        ev = StrategyEvidence(
            hard_ceilings_enforced=False,
            governance_safe_planning=False,
            all_invariants_preserved=False,
        )
        assert compute_strategy_maturity(ev) == 0

    def test_full_evidence_high_score(self) -> None:
        from core.workstation.constitutional_strategic_intelligence_engine_v1 import (
            StrategyEvidence,
            compute_strategy_maturity,
        )

        ev = StrategyEvidence(
            forecasts_generated=True,
            forecast_count=9,
            composite_trajectory=0.5,
            leverage_modeled=True,
            total_leverage=5.0,
            safe_chain_count=10,
            compounding_score=0.1,
            bottlenecks_predicted=True,
            simulations_run=True,
            sequencing_generated=True,
            topology_generated=True,
            topology_types_covered=7,
            adaptation_analyzed=True,
            all_invariants_preserved=True,
            replay_safe_adaptation=True,
            continuity_safe_forecasting=True,
            recursive_leverage_score=0.5,
            founder_confirmed=True,
            hard_ceilings_enforced=True,
            governance_safe_planning=True,
        )
        assert compute_strategy_maturity(ev) >= 16


class TestStrategyMaturityCeiling:
    def test_dry_run_l0(self) -> None:
        from core.workstation.constitutional_strategic_intelligence_engine_v1 import (
            StrategyEvidence,
            strategy_maturity_ceiling,
        )

        ev = StrategyEvidence(is_dry_run=True)
        ceiling, blocked, _ = strategy_maturity_ceiling(ev)
        assert ceiling == "L0_NO_STRATEGIC_INTELLIGENCE"
        assert blocked is True

    def test_no_forecasts_l0(self) -> None:
        from core.workstation.constitutional_strategic_intelligence_engine_v1 import (
            StrategyEvidence,
            strategy_maturity_ceiling,
        )

        ev = StrategyEvidence()
        ceiling, blocked, _ = strategy_maturity_ceiling(ev)
        assert ceiling == "L0_NO_STRATEGIC_INTELLIGENCE"

    def test_full_evidence_l5(self) -> None:
        from core.workstation.constitutional_strategic_intelligence_engine_v1 import (
            StrategyEvidence,
            strategy_maturity_ceiling,
        )

        ev = StrategyEvidence(
            forecasts_generated=True,
            forecast_count=9,
            leverage_modeled=True,
            total_leverage=5.0,
            bottlenecks_predicted=True,
            simulations_run=True,
            sequencing_generated=True,
            topology_generated=True,
            adaptation_analyzed=True,
            replay_safe_adaptation=True,
            continuity_safe_forecasting=True,
            founder_confirmed=True,
            hard_ceilings_enforced=True,
            all_invariants_preserved=True,
        )
        ceiling, blocked, reason = strategy_maturity_ceiling(ev)
        assert ceiling == "L5_CONSTITUTIONAL_STRATEGIC_INTELLIGENCE"
        assert blocked is False

    def test_no_founder_capped_l4(self) -> None:
        from core.workstation.constitutional_strategic_intelligence_engine_v1 import (
            StrategyEvidence,
            strategy_maturity_ceiling,
        )

        ev = StrategyEvidence(
            forecasts_generated=True,
            forecast_count=9,
            leverage_modeled=True,
            total_leverage=5.0,
            bottlenecks_predicted=True,
            simulations_run=True,
            sequencing_generated=True,
            topology_generated=True,
            adaptation_analyzed=True,
            replay_safe_adaptation=True,
            continuity_safe_forecasting=True,
            founder_confirmed=False,
            hard_ceilings_enforced=True,
            all_invariants_preserved=True,
        )
        ceiling, blocked, reason = strategy_maturity_ceiling(ev)
        assert ceiling == "L4_STRATEGICALLY_SEQUENCED"
        assert "founder" in reason


class TestClassifyStrategyMaturity:
    def test_empty_l0(self) -> None:
        from core.workstation.constitutional_strategic_intelligence_engine_v1 import (
            StrategyEvidence,
            classify_strategy_maturity,
        )

        ev = StrategyEvidence()
        level, ceiling, blocked, _ = classify_strategy_maturity(ev)
        assert level == "L0_NO_STRATEGIC_INTELLIGENCE"
        assert blocked is True


class TestBuildFullStrategyProof:
    def test_no_upstream(self) -> None:
        from core.workstation.constitutional_strategic_intelligence_engine_v1 import (
            build_full_strategy_proof,
        )

        proof = build_full_strategy_proof(trace_id="test")
        assert proof.proof_id.startswith("STRAT-")
        assert proof.evidence is not None
        assert proof.forecasts is not None
        assert proof.leverage_model is not None
        assert proof.bottleneck_forecasts is not None
        assert len(proof.simulations) == 9
        assert proof.strategic_sequence is not None
        assert proof.topology is not None
        assert proof.adaptations is not None

    def test_dry_run(self) -> None:
        from core.workstation.constitutional_strategic_intelligence_engine_v1 import (
            build_full_strategy_proof,
        )

        proof = build_full_strategy_proof(is_dry_run=True)
        assert proof.execution_strategy == "simulation_only"

    def test_founder_strategy(self) -> None:
        from core.workstation.constitutional_strategic_intelligence_engine_v1 import (
            build_full_strategy_proof,
        )

        proof = build_full_strategy_proof(founder_confirmed=True)
        assert proof.execution_strategy == "constitutional_strategic_intelligence_active"

    def test_with_full_upstream_chain(self) -> None:
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

        proof = build_full_strategy_proof(
            economics_proof=econ,
            federation_proof=fed,
            orchestration_proof=orch,
            capability_proof=cap,
            founder_confirmed=True,
        )
        assert proof.maturity_level != "L0_NO_STRATEGIC_INTELLIGENCE"
        assert proof.evidence.forecast_count == 9
        assert proof.evidence.leverage_modeled is True


class TestPersistStrategyProof:
    def test_persist_creates_file(self, tmp_path: Path) -> None:
        from core.workstation.constitutional_strategic_intelligence_engine_v1 import (
            build_full_strategy_proof,
            persist_strategy_proof,
        )

        proof = build_full_strategy_proof(trace_id="persist-test")
        path = persist_strategy_proof(proof, base_dir=tmp_path)
        assert path.exists()
        assert path.name.startswith("STRAT-")
        data = json.loads(path.read_text())
        assert data["proof_type"] == "constitutional_strategic_intelligence"

    def test_persist_json_valid(self, tmp_path: Path) -> None:
        from core.workstation.constitutional_strategic_intelligence_engine_v1 import (
            build_full_strategy_proof,
            persist_strategy_proof,
        )

        proof = build_full_strategy_proof(trace_id="json-test")
        path = persist_strategy_proof(proof, base_dir=tmp_path)
        data = json.loads(path.read_text())
        assert "forecasts" in data
        assert "leverage_model" in data
        assert "simulations" in data
        assert "strategic_sequence" in data
        assert "topology" in data
        assert "adaptations" in data


class TestStrategyCommandRegistration:
    def test_registry_has_23_commands(self) -> None:
        from composition.registries.canonical_command_registry_v1 import (
            CanonicalCommandRegistryV1,
        )

        reg = CanonicalCommandRegistryV1()
        assert len(reg) == 27

    def test_strategy_report_in_registry(self) -> None:
        from composition.registries.canonical_command_registry_v1 import (
            CanonicalCommandRegistryV1,
        )

        reg = CanonicalCommandRegistryV1()
        assert "!strategy-report" in reg.commands
        entry = reg.get("!strategy-report")
        assert entry.canonical_action == "strategy_report"

    def test_action_in_allowed(self) -> None:
        from core.control_plane_router.router_contracts import ALLOWED_ACTION_TYPES

        assert "strategy_report" in ALLOWED_ACTION_TYPES
        assert len(ALLOWED_ACTION_TYPES) == 27

    def test_action_in_map(self) -> None:
        from core.control_plane_router.control_plane_router_v1 import (
            ACTION_CAPABILITY_MAP,
        )

        assert "strategy_report" in ACTION_CAPABILITY_MAP

    def test_config_has_23_actions(self) -> None:
        config = json.loads((Path(_ROOT) / "config" / "control_plane_router_v1.json").read_text())
        assert len(config["allowed_action_types"]) == 27
        assert "strategy_report" in config["allowed_action_types"]

    def test_substrate_commands(self) -> None:
        from handlers.substrate_command_handler import SUBSTRATE_COMMANDS

        assert "!strategy-report" in SUBSTRATE_COMMANDS
        assert len(SUBSTRATE_COMMANDS) == 27


class TestLiveStrategyProof:
    def test_live_proof_with_full_upstream(self) -> None:
        from core.workstation.constitutional_strategic_intelligence_engine_v1 import (
            STRATEGY_MATURITY_LEVELS,
            LONG_HORIZON_SIMULATION_TYPES,
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

        base = Path(_ROOT)
        cap = build_full_capability_proof(trace_id="live-strat")
        orch = build_full_orchestration_proof(capability_proof=cap, trace_id="live-strat")
        cont = build_full_continuity_proof(
            orchestration_proof=orch, capability_proof=cap, trace_id="live-strat", base_dir=base
        )
        gov = build_full_governance_intelligence_proof(
            orchestration_proof=orch,
            continuity_proof=cont,
            capability_proof=cap,
            trace_id="live-strat",
            base_dir=base,
        )
        const = build_full_constitutional_proof(
            orchestration_proof=orch,
            continuity_proof=cont,
            governance_proof=gov,
            capability_proof=cap,
            trace_id="live-strat",
            base_dir=base,
        )
        fed = build_full_federation_proof(
            constitutional_proof=const,
            orchestration_proof=orch,
            continuity_proof=cont,
            governance_proof=gov,
            capability_proof=cap,
            trace_id="live-strat",
            base_dir=base,
        )
        econ = build_full_economics_proof(
            federation_proof=fed,
            orchestration_proof=orch,
            continuity_proof=cont,
            constitutional_proof=const,
            governance_proof=gov,
            capability_proof=cap,
            trace_id="live-strat",
            base_dir=base,
        )

        proof = build_full_strategy_proof(
            economics_proof=econ,
            federation_proof=fed,
            orchestration_proof=orch,
            continuity_proof=cont,
            constitutional_proof=const,
            governance_proof=gov,
            capability_proof=cap,
            founder_confirmed=True,
            trace_id="live-strat",
            base_dir=base,
        )

        assert proof.proof_id.startswith("STRAT-")
        assert proof.maturity_level in STRATEGY_MATURITY_LEVELS
        assert proof.evidence is not None
        assert proof.evidence.forecasts_generated is True
        assert proof.evidence.forecast_count == 9
        assert proof.evidence.leverage_modeled is True
        assert proof.evidence.total_leverage > 0
        assert proof.evidence.bottlenecks_predicted is True
        assert proof.evidence.simulations_run is True
        assert proof.evidence.simulation_count == 9
        assert proof.evidence.sequencing_generated is True
        assert proof.evidence.topology_generated is True
        assert proof.evidence.topology_types_covered == 7
        assert proof.evidence.adaptation_analyzed is True
        assert proof.evidence.all_invariants_preserved is True
        assert proof.evidence.founder_confirmed is True
        assert proof.evidence.recursive_leverage_score > 0
        assert len(proof.simulations) == 9
        sim_types = {s.simulation_type for s in proof.simulations}
        assert sim_types == set(LONG_HORIZON_SIMULATION_TYPES)
        assert proof.execution_strategy == "constitutional_strategic_intelligence_active"
