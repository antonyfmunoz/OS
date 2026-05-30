"""Phase 10.5 — Reliability-Weighted Cadence Ranking + Promotion Thresholds.

Tests reliability signal aggregation, weighted ranking, promotion thresholds,
cadence integration, API routes, and decision simulation correctness.
"""

from __future__ import annotations

import json
import os
import sys
import unittest

sys.path.insert(0, "/opt/OS")


# ── TST-22: Reliability Signal Aggregation ───────────────────────────────────

class TestReliabilitySignalAggregation(unittest.TestCase):
    """TST-22: Verify reliability signals aggregate from real artifacts."""

    def setUp(self):
        from substrate.organism.reliability_signals import ReliabilitySignalAggregator
        self.agg = ReliabilitySignalAggregator()
        self.agg.aggregate()

    def test_template_signals_populated(self):
        self.assertGreater(len(self.agg._template_signals), 0)

    def test_agent_signals_populated(self):
        self.assertGreater(len(self.agg._agent_signals), 0)

    def test_source_signals_populated(self):
        self.assertGreater(len(self.agg._source_signals), 0)

    def test_validation_signals_populated(self):
        self.assertGreater(len(self.agg._validation_signals), 0)

    def test_production_truth_signal_exists(self):
        pt = self.agg.get_production_truth_signal()
        self.assertIsNotNone(pt)
        self.assertGreater(pt.pmv_pass_rate, 0)

    def test_to_dict_structure(self):
        result = self.agg.to_dict()
        self.assertIn("templates", result)
        self.assertIn("agents", result)
        self.assertIn("sources", result)
        self.assertIn("validations", result)
        self.assertIn("production_truth", result)


# ── TST-23: Template Reliability Extraction ──────────────────────────────────

class TestTemplateReliabilityExtraction(unittest.TestCase):
    """TST-23: Verify template signals from real Phase 10.4R artifacts."""

    def setUp(self):
        from substrate.organism.reliability_signals import ReliabilitySignalAggregator
        self.agg = ReliabilitySignalAggregator()
        self.agg.aggregate()

    def test_documentation_alignment_confidence(self):
        sig = self.agg.get_template_signal("tpl-seed-documentation-alignment-01")
        self.assertGreaterEqual(sig.confidence, 0.85)

    def test_test_repair_confidence(self):
        sig = self.agg.get_template_signal("tpl-seed-test-repair-01")
        self.assertGreaterEqual(sig.confidence, 0.82)

    def test_template_score_in_range(self):
        for tid, sig in self.agg._template_signals.items():
            score = sig.score()
            self.assertGreaterEqual(score, 0.0, f"{tid} score below 0")
            self.assertLessEqual(score, 1.0, f"{tid} score above 1")

    def test_production_successes_nonzero(self):
        sig = self.agg.get_template_signal("tpl-seed-documentation-alignment-01")
        self.assertGreater(sig.production_successes, 0)

    def test_unknown_template_returns_default(self):
        sig = self.agg.get_template_signal("nonexistent-template")
        self.assertEqual(sig.template_id, "nonexistent-template")
        self.assertEqual(sig.confidence, 0.0)


# ── TST-24: Agent Reliability Extraction ─────────────────────────────────────

class TestAgentReliabilityExtraction(unittest.TestCase):
    """TST-24: Verify agent signals from real Phase 10.4R artifacts."""

    def setUp(self):
        from substrate.organism.reliability_signals import ReliabilitySignalAggregator
        self.agg = ReliabilitySignalAggregator()
        self.agg.aggregate()

    def test_developer_agent_exists(self):
        sig = self.agg.get_agent_signal("developer_agent")
        self.assertEqual(sig.agent_type, "developer_agent")

    def test_developer_agent_perfect_reliability(self):
        sig = self.agg.get_agent_signal("developer_agent")
        self.assertEqual(sig.production_failures, 0)
        self.assertGreater(sig.production_successes, 0)

    def test_agent_score_in_range(self):
        for atype, sig in self.agg._agent_signals.items():
            score = sig.score()
            self.assertGreaterEqual(score, 0.0)
            self.assertLessEqual(score, 1.0)


# ── TST-25: Candidate Source Reliability ─────────────────────────────────────

class TestCandidateSourceReliability(unittest.TestCase):
    """TST-25: Verify source signals computed from campaign data."""

    def setUp(self):
        from substrate.organism.reliability_signals import ReliabilitySignalAggregator
        self.agg = ReliabilitySignalAggregator()
        self.agg.aggregate()

    def test_stale_docstrings_source_exists(self):
        sig = self.agg.get_source_signal("stale_docstrings")
        self.assertEqual(sig.source_name, "stale_docstrings")

    def test_proven_source_has_merges(self):
        sig = self.agg.get_source_signal("stale_docstrings")
        self.assertGreater(sig.prs_merged, 0)

    def test_source_score_in_range(self):
        for src, sig in self.agg._source_signals.items():
            score = sig.score()
            self.assertGreaterEqual(score, 0.0)
            self.assertLessEqual(score, 1.0)


# ── TST-26: Validation Reliability ───────────────────────────────────────────

class TestValidationReliability(unittest.TestCase):
    """TST-26: Verify validation signals from merge verification data."""

    def setUp(self):
        from substrate.organism.reliability_signals import ReliabilitySignalAggregator
        self.agg = ReliabilitySignalAggregator()
        self.agg.aggregate()

    def test_import_substrate_validation_exists(self):
        sig = self.agg.get_validation_signal("import substrate")
        self.assertEqual(sig.validation_method, "import substrate")

    def test_validation_pass_rate_positive(self):
        sig = self.agg.get_validation_signal("import substrate")
        self.assertGreater(sig.pass_rate, 0.0)

    def test_baseline_comparison_support(self):
        sig = self.agg.get_validation_signal("import substrate")
        self.assertTrue(sig.baseline_comparison_support)


# ── TST-27: Rollback Reliability ─────────────────────────────────────────────

class TestRollbackReliability(unittest.TestCase):
    """TST-27: Verify rollback signal scoring."""

    def test_non_mutating_scores_perfect(self):
        from substrate.organism.reliability_signals import RollbackReliabilitySignal
        sig = RollbackReliabilitySignal(non_mutating=True)
        self.assertEqual(sig.score(), 1.0)

    def test_no_rollback_scores_zero(self):
        from substrate.organism.reliability_signals import RollbackReliabilitySignal
        sig = RollbackReliabilitySignal()
        self.assertEqual(sig.score(), 0.0)

    def test_rollback_exists_scores_positive(self):
        from substrate.organism.reliability_signals import RollbackReliabilitySignal
        sig = RollbackReliabilitySignal(rollback_method_exists=True)
        self.assertGreater(sig.score(), 0.0)

    def test_rollback_tested_increases_score(self):
        from substrate.organism.reliability_signals import RollbackReliabilitySignal
        base = RollbackReliabilitySignal(rollback_method_exists=True)
        tested = RollbackReliabilitySignal(rollback_method_exists=True, rollback_tested=True)
        self.assertGreater(tested.score(), base.score())


# ── TST-28: Production Truth Reliability ─────────────────────────────────────

class TestProductionTruthReliability(unittest.TestCase):
    """TST-28: Verify production truth signal from real PMV data."""

    def setUp(self):
        from substrate.organism.reliability_signals import ReliabilitySignalAggregator
        self.agg = ReliabilitySignalAggregator()
        self.agg.aggregate()

    def test_pmv_pass_rate_positive(self):
        pt = self.agg.get_production_truth_signal()
        self.assertGreater(pt.pmv_pass_rate, 0.0)

    def test_idempotency_pass_rate(self):
        pt = self.agg.get_production_truth_signal()
        self.assertEqual(pt.idempotency_pass_rate, 1.0)

    def test_duplicate_suppression_pass_rate(self):
        pt = self.agg.get_production_truth_signal()
        self.assertEqual(pt.duplicate_suppression_pass_rate, 1.0)


# ── TST-29: Weighted Ranking Formula ────────────────────────────────────────

class TestWeightedRankingFormula(unittest.TestCase):
    """TST-29: Verify ranking formula weights sum to 1.0 and produce correct scores."""

    def test_weights_sum_to_one(self):
        from substrate.organism.reliability_weighted_ranker import ReliabilityWeightedRanker
        total = sum(ReliabilityWeightedRanker.WEIGHTS.values())
        self.assertAlmostEqual(total, 1.0, places=4)

    def test_ranking_deterministic(self):
        from substrate.organism.reliability_signals import ReliabilitySignalAggregator
        from substrate.organism.reliability_weighted_ranker import ReliabilityWeightedRanker
        agg = ReliabilitySignalAggregator()
        agg.aggregate()
        r1 = ReliabilityWeightedRanker(aggregator=agg)
        r2 = ReliabilityWeightedRanker(aggregator=agg)
        candidates = [{"candidate_id": "test-1", "source": "stale_docstrings",
                       "template_id": "tpl-seed-documentation-alignment-01",
                       "validation_method": "py_compile", "non_mutating": True,
                       "risk_class": "low", "evidence": [{"detail": "test"}],
                       "affected_files": ["test.py"], "description": "test"}]
        ranked1 = r1.rank_candidates(candidates)
        ranked2 = r2.rank_candidates(candidates)
        self.assertEqual(ranked1[0].weighted_score, ranked2[0].weighted_score)

    def test_higher_template_confidence_ranks_higher(self):
        from substrate.organism.reliability_signals import ReliabilitySignalAggregator
        from substrate.organism.reliability_weighted_ranker import ReliabilityWeightedRanker
        agg = ReliabilitySignalAggregator()
        agg.aggregate()
        ranker = ReliabilityWeightedRanker(aggregator=agg)
        candidates = [
            {"candidate_id": "high", "source": "stale_docstrings",
             "template_id": "tpl-seed-documentation-alignment-01",
             "validation_method": "py_compile", "non_mutating": True,
             "risk_class": "low", "evidence": [{"detail": "test"}],
             "affected_files": ["a.py"], "description": "test fix"},
            {"candidate_id": "low", "source": "template_audit_gaps",
             "template_id": "tpl-seed-maintenance-action-01",
             "validation_method": "py_compile", "non_mutating": True,
             "risk_class": "low", "evidence": [{"detail": "test"}],
             "affected_files": ["b.py"], "description": "test fix"},
        ]
        ranked = ranker.rank_candidates(candidates)
        self.assertEqual(ranked[0].candidate_id, "high")


# ── TST-30: Hard Gates ──────────────────────────────────────────────────────

class TestHardGates(unittest.TestCase):
    """TST-30: Verify hard gates block ineligible candidates."""

    def setUp(self):
        from substrate.organism.reliability_signals import ReliabilitySignalAggregator
        from substrate.organism.reliability_weighted_ranker import ReliabilityWeightedRanker
        agg = ReliabilitySignalAggregator()
        agg.aggregate()
        self.ranker = ReliabilityWeightedRanker(aggregator=agg)

    def test_medium_risk_blocked(self):
        ranked = self.ranker.rank_candidates([{
            "candidate_id": "med", "risk_class": "medium",
            "template_id": "tpl-x", "validation_method": "test",
            "non_mutating": True, "evidence": [{"d": "t"}],
            "affected_files": ["a.py"], "description": "test",
        }])
        self.assertFalse(ranked[0].eligible)
        self.assertIn("risk_not_low", " ".join(ranked[0].blocking_reasons))

    def test_no_template_blocked(self):
        ranked = self.ranker.rank_candidates([{
            "candidate_id": "no-tpl", "risk_class": "low",
            "validation_method": "test", "non_mutating": True,
            "evidence": [{"d": "t"}], "affected_files": ["a.py"],
            "description": "test",
        }])
        self.assertFalse(ranked[0].eligible)

    def test_no_validation_blocked(self):
        ranked = self.ranker.rank_candidates([{
            "candidate_id": "no-val", "risk_class": "low",
            "template_id": "tpl-x", "non_mutating": True,
            "evidence": [{"d": "t"}], "affected_files": ["a.py"],
            "description": "test",
        }])
        self.assertFalse(ranked[0].eligible)

    def test_no_rollback_and_not_non_mutating_blocked(self):
        ranked = self.ranker.rank_candidates([{
            "candidate_id": "no-rb", "risk_class": "low",
            "template_id": "tpl-x", "validation_method": "test",
            "evidence": [{"d": "t"}], "affected_files": ["a.py"],
            "description": "test",
        }])
        self.assertFalse(ranked[0].eligible)

    def test_sensitive_path_blocked(self):
        ranked = self.ranker.rank_candidates([{
            "candidate_id": "sens", "risk_class": "low",
            "template_id": "tpl-x", "validation_method": "test",
            "non_mutating": True, "evidence": [{"d": "t"}],
            "affected_files": [".env"], "description": "test",
        }])
        self.assertFalse(ranked[0].eligible)

    def test_blocked_keyword_blocks(self):
        ranked = self.ranker.rank_candidates([{
            "candidate_id": "kw", "risk_class": "low",
            "template_id": "tpl-x", "validation_method": "test",
            "non_mutating": True, "evidence": [{"d": "t"}],
            "affected_files": ["a.py"], "description": "fix docker container",
        }])
        self.assertFalse(ranked[0].eligible)

    def test_resolved_candidate_blocked(self):
        ranked = self.ranker.rank_candidates([{
            "candidate_id": "resolved", "risk_class": "low",
            "template_id": "tpl-x", "validation_method": "test",
            "non_mutating": True, "evidence": [{"d": "t"}],
            "affected_files": ["a.py"], "description": "test",
            "policy_decision": "resolved",
        }])
        self.assertFalse(ranked[0].eligible)


# ── TST-31: Promotion Classes ────────────────────────────────────────────────

class TestPromotionClasses(unittest.TestCase):
    """TST-31: Verify promotion class assignment."""

    def test_execute_ready_with_proven_template(self):
        from substrate.organism.reliability_signals import ReliabilitySignalAggregator
        from substrate.organism.reliability_weighted_ranker import ReliabilityWeightedRanker, PromotionClass
        agg = ReliabilitySignalAggregator()
        agg.aggregate()
        ranker = ReliabilityWeightedRanker(aggregator=agg)
        ranked = ranker.rank_candidates([{
            "candidate_id": "proven", "risk_class": "low",
            "source": "stale_docstrings",
            "template_id": "tpl-seed-documentation-alignment-01",
            "validation_method": "py_compile", "non_mutating": True,
            "evidence": [{"d": "t"}], "affected_files": ["a.py"],
            "description": "update stale name",
        }])
        self.assertEqual(ranked[0].promotion_class, PromotionClass.EXECUTE_READY_LOW_RISK)

    def test_supervised_with_weak_template(self):
        from substrate.organism.reliability_signals import ReliabilitySignalAggregator
        from substrate.organism.reliability_weighted_ranker import ReliabilityWeightedRanker, PromotionClass
        agg = ReliabilitySignalAggregator()
        agg.aggregate()
        ranker = ReliabilityWeightedRanker(aggregator=agg)
        ranked = ranker.rank_candidates([{
            "candidate_id": "weak", "risk_class": "low",
            "source": "template_audit_gaps",
            "template_id": "tpl-seed-maintenance-action-01",
            "validation_method": "py_compile", "non_mutating": True,
            "evidence": [{"d": "t"}], "affected_files": ["a.py"],
            "description": "fix maintenance gap",
        }])
        self.assertIn(ranked[0].promotion_class, [PromotionClass.SUPERVISED_LOW_RISK, PromotionClass.RECOMMEND_ONLY])

    def test_blocked_class_value(self):
        from substrate.organism.reliability_weighted_ranker import PromotionClass
        self.assertEqual(PromotionClass.BLOCKED.value, "blocked")

    def test_all_four_classes_exist(self):
        from substrate.organism.reliability_weighted_ranker import PromotionClass
        self.assertEqual(len(PromotionClass), 4)


# ── TST-32: Threshold Policy ────────────────────────────────────────────────

class TestThresholdPolicy(unittest.TestCase):
    """TST-32: Verify promotion threshold evaluations."""

    def setUp(self):
        from substrate.organism.reliability_signals import ReliabilitySignalAggregator
        from substrate.organism.promotion_threshold_policy import PromotionThresholdPolicy
        agg = ReliabilitySignalAggregator()
        agg.aggregate()
        self.policy = PromotionThresholdPolicy(aggregator=agg)

    def test_dry_run_always_met(self):
        from substrate.organism.promotion_threshold_policy import CadenceLevel
        evaluation = self.policy.evaluate_level(CadenceLevel.DRY_RUN_ONLY)
        self.assertTrue(evaluation.met)

    def test_medium_risk_execution_blocked(self):
        from substrate.organism.promotion_threshold_policy import CadenceLevel
        evaluation = self.policy.evaluate_level(CadenceLevel.MEDIUM_RISK_SUPERVISED_REVIEW)
        self.assertFalse(evaluation.met)
        self.assertIn("execution blocked until future phase", evaluation.unmet_reasons)

    def test_highest_eligible_is_dry_run(self):
        from substrate.organism.promotion_threshold_policy import CadenceLevel
        highest = self.policy.highest_eligible_level()
        self.assertEqual(highest, CadenceLevel.DRY_RUN_ONLY)

    def test_evaluate_all_returns_all_levels(self):
        evaluations = self.policy.evaluate_all()
        self.assertEqual(len(evaluations), 5)

    def test_to_dict_includes_blocked(self):
        result = self.policy.to_dict()
        self.assertTrue(result["medium_risk_execution_blocked"])

    def test_supervised_pr_has_template_threshold(self):
        from substrate.organism.promotion_threshold_policy import CadenceLevel
        spec = self.policy.THRESHOLDS[CadenceLevel.SUPERVISED_PR_CREATION]
        self.assertGreaterEqual(spec.template_reliability, 0.80)

    def test_batch_mode_requires_operator(self):
        from substrate.organism.promotion_threshold_policy import CadenceLevel
        spec = self.policy.THRESHOLDS[CadenceLevel.LOW_RISK_BATCH_MODE]
        self.assertTrue(spec.operator_enables_batch)


# ── TST-33: Cadence Integration ──────────────────────────────────────────────

class TestCadenceIntegration(unittest.TestCase):
    """TST-33: Verify ranker integrates with candidate supply engine."""

    def test_discover_for_cadence_produces_rankable_dicts(self):
        from substrate.organism.candidate_supply_engine import CandidateSupplyEngine
        from substrate.organism.reliability_weighted_ranker import ReliabilityWeightedRanker
        supply = CandidateSupplyEngine()
        cadence_dicts = supply.discover_for_cadence()
        ranker = ReliabilityWeightedRanker()
        ranked = ranker.rank_candidates(cadence_dicts)
        self.assertIsInstance(ranked, list)

    def test_ranked_candidates_have_scores(self):
        from substrate.organism.candidate_supply_engine import CandidateSupplyEngine
        from substrate.organism.reliability_weighted_ranker import ReliabilityWeightedRanker
        supply = CandidateSupplyEngine()
        cadence_dicts = supply.discover_for_cadence()
        ranker = ReliabilityWeightedRanker()
        ranked = ranker.rank_candidates(cadence_dicts)
        for rc in ranked:
            self.assertIsInstance(rc.weighted_score, float)
            self.assertGreaterEqual(rc.rank, 1)


# ── TST-34: API Route Auth ──────────────────────────────────────────────────

class TestAPIRouteAuth(unittest.TestCase):
    """TST-34: Verify Phase 10.5 routes are registered with auth."""

    def test_routes_registered(self):
        from transports.api.cockpit_autonomous_routes import _build_router
        class FakeDep:
            pass
        r = _build_router(FakeDep)
        paths = [route.path for route in r.routes]
        expected = [
            "/organism/reliability-signals",
            "/organism/cadence-ranked-candidates",
            "/organism/promotion-thresholds",
            "/organism/template-reliability",
            "/organism/agent-reliability",
            "/organism/candidate-source-reliability",
        ]
        for ep in expected:
            self.assertIn(ep, paths, f"Missing route: {ep}")

    def test_route_count_includes_phase10_5(self):
        from transports.api.cockpit_autonomous_routes import _build_router
        class FakeDep:
            pass
        r = _build_router(FakeDep)
        paths = [route.path for route in r.routes]
        reliability_routes = [p for p in paths if "reliability" in p or "ranked" in p or "promotion" in p]
        self.assertGreaterEqual(len(reliability_routes), 6)


# ── TST-35: Dry-Run Simulation ──────────────────────────────────────────────

class TestDryRunSimulation(unittest.TestCase):
    """TST-35: Verify dry-run simulation produces correct comparison data."""

    def test_simulation_artifact_exists(self):
        path = "/opt/OS/data/umh/autonomous_lane/phase10_5_decision_simulation.json"
        self.assertTrue(os.path.isfile(path))

    def test_simulation_verdict_passes(self):
        path = "/opt/OS/data/umh/autonomous_lane/phase10_5_decision_simulation.json"
        with open(path) as f:
            data = json.load(f)
        self.assertEqual(data["verdict"], "ALL VERIFICATIONS PASS")

    def test_simulation_has_comparisons(self):
        path = "/opt/OS/data/umh/autonomous_lane/phase10_5_decision_simulation.json"
        with open(path) as f:
            data = json.load(f)
        self.assertGreater(len(data["comparisons"]), 0)


# ── TST-36: Resolved Candidate Suppression ──────────────────────────────────

class TestResolvedCandidateSuppression(unittest.TestCase):
    """TST-36: Verify resolved candidates are suppressed in ranking."""

    def test_resolved_candidate_not_in_discover(self):
        from substrate.organism.candidate_supply_engine import CandidateSupplyEngine
        supply = CandidateSupplyEngine()
        supply.mark_resolved("scripts/notion_setup.py")
        result = supply.discover()
        for c in result.candidates:
            self.assertNotIn("notion_setup", c.description.lower())

    def test_resolved_candidate_blocked_in_ranker(self):
        from substrate.organism.reliability_weighted_ranker import ReliabilityWeightedRanker
        ranker = ReliabilityWeightedRanker()
        ranked = ranker.rank_candidates([{
            "candidate_id": "resolved-test",
            "risk_class": "low",
            "template_id": "tpl-x",
            "validation_method": "test",
            "non_mutating": True,
            "evidence": [{"d": "t"}],
            "affected_files": ["a.py"],
            "description": "test",
            "policy_decision": "resolved",
        }])
        self.assertFalse(ranked[0].eligible)


# ── TST-37: Medium-Risk Execution Blocked ────────────────────────────────────

class TestMediumRiskBlocked(unittest.TestCase):
    """TST-37: Verify medium-risk candidates cannot be executed."""

    def test_medium_risk_blocked_in_ranker(self):
        from substrate.organism.reliability_weighted_ranker import ReliabilityWeightedRanker
        ranker = ReliabilityWeightedRanker()
        ranked = ranker.rank_candidates([{
            "candidate_id": "med-risk",
            "risk_class": "medium",
            "template_id": "tpl-x",
            "validation_method": "test",
            "non_mutating": True,
            "evidence": [{"d": "t"}],
            "affected_files": ["a.py"],
            "description": "test change",
        }])
        self.assertFalse(ranked[0].eligible)

    def test_medium_risk_cadence_blocked(self):
        from substrate.organism.promotion_threshold_policy import (
            PromotionThresholdPolicy, CadenceLevel,
        )
        policy = PromotionThresholdPolicy()
        evaluation = policy.evaluate_level(CadenceLevel.MEDIUM_RISK_SUPERVISED_REVIEW)
        self.assertFalse(evaluation.met)


# ── TST-38: Explainability / Evidence Trace ──────────────────────────────────

class TestExplainability(unittest.TestCase):
    """TST-38: Verify every ranked candidate has an evidence trace."""

    def test_evidence_trace_populated(self):
        from substrate.organism.reliability_weighted_ranker import ReliabilityWeightedRanker
        ranker = ReliabilityWeightedRanker()
        ranked = ranker.rank_candidates([{
            "candidate_id": "explain-test",
            "risk_class": "low",
            "source": "stale_docstrings",
            "template_id": "tpl-seed-documentation-alignment-01",
            "validation_method": "py_compile",
            "non_mutating": True,
            "evidence": [{"d": "t"}],
            "affected_files": ["a.py"],
            "description": "fix stale name",
        }])
        trace = ranked[0].evidence_trace
        self.assertIn("template_id", trace)
        self.assertIn("template_confidence", trace)
        self.assertIn("agent_type", trace)
        self.assertIn("source", trace)

    def test_to_dict_includes_recommended_action(self):
        from substrate.organism.reliability_weighted_ranker import ReliabilityWeightedRanker
        ranker = ReliabilityWeightedRanker()
        ranked = ranker.rank_candidates([{
            "candidate_id": "action-test",
            "risk_class": "low",
            "template_id": "tpl-seed-documentation-alignment-01",
            "validation_method": "py_compile",
            "non_mutating": True,
            "evidence": [{"d": "t"}],
            "affected_files": ["a.py"],
            "description": "fix stale name",
        }])
        d = ranked[0].to_dict()
        self.assertIn("recommended_action", d)
        self.assertNotEqual(d["recommended_action"], "")


# ── TST-39: Signal Bundle Construction ───────────────────────────────────────

class TestSignalBundle(unittest.TestCase):
    """TST-39: Verify signal bundle construction and scoring."""

    def test_bundle_from_aggregator(self):
        from substrate.organism.reliability_signals import ReliabilitySignalAggregator
        agg = ReliabilitySignalAggregator()
        agg.aggregate()
        bundle = agg.build_bundle(
            template_id="tpl-seed-documentation-alignment-01",
            agent_type="developer_agent",
            source_name="stale_docstrings",
            validation_method="import substrate",
            non_mutating=True,
        )
        self.assertGreater(bundle.template.confidence, 0)
        self.assertGreater(bundle.agent.production_successes, 0)
        self.assertEqual(bundle.rollback.non_mutating, True)
        self.assertEqual(bundle.rollback.score(), 1.0)

    def test_bundle_to_dict(self):
        from substrate.organism.reliability_signals import ReliabilitySignalAggregator
        agg = ReliabilitySignalAggregator()
        agg.aggregate()
        bundle = agg.build_bundle(template_id="tpl-seed-test-repair-01")
        d = bundle.to_dict()
        self.assertIn("template", d)
        self.assertIn("agent", d)
        self.assertIn("source", d)
        self.assertIn("validation", d)
        self.assertIn("rollback", d)
        self.assertIn("production_truth", d)


# ── TST-40: Safety Invariants ────────────────────────────────────────────────

class TestSafetyInvariants(unittest.TestCase):
    """TST-40: Verify Phase 10.5 safety invariants hold."""

    def test_no_fake_data_in_signals(self):
        path = "/opt/OS/data/umh/autonomous_lane/phase10_5_reliability_signals.json"
        self.assertTrue(os.path.isfile(path))
        with open(path) as f:
            data = json.load(f)
        for tid, sig in data["templates"].items():
            self.assertTrue(tid.startswith("tpl-"), f"Non-template ID: {tid}")

    def test_no_fake_data_in_ranked(self):
        path = "/opt/OS/data/umh/autonomous_lane/phase10_5_ranked_candidates.json"
        self.assertTrue(os.path.isfile(path))
        with open(path) as f:
            data = json.load(f)
        for rc in data["ranked_candidates"]:
            self.assertTrue(rc["candidate_id"].startswith("cse-"))

    def test_cadence_remains_dry_run_only(self):
        from substrate.organism.promotion_threshold_policy import PromotionThresholdPolicy, CadenceLevel
        policy = PromotionThresholdPolicy()
        highest = policy.highest_eligible_level()
        self.assertEqual(highest, CadenceLevel.DRY_RUN_ONLY)

    def test_medium_risk_permanently_blocked(self):
        from substrate.organism.promotion_threshold_policy import PromotionThresholdPolicy, CadenceLevel
        policy = PromotionThresholdPolicy()
        evaluation = policy.evaluate_level(CadenceLevel.MEDIUM_RISK_SUPERVISED_REVIEW)
        self.assertTrue(evaluation.threshold.execution_blocked)

    def test_preflight_artifact_exists(self):
        self.assertTrue(os.path.isfile("/opt/OS/data/umh/autonomous_lane/phase10_5_preflight.json"))


# ── TST-41: Ranker Config Serialization ──────────────────────────────────────

class TestRankerConfigSerialization(unittest.TestCase):
    """TST-41: Verify ranker config is serializable and complete."""

    def test_to_dict_has_weights(self):
        from substrate.organism.reliability_weighted_ranker import ReliabilityWeightedRanker
        ranker = ReliabilityWeightedRanker()
        config = ranker.to_dict()
        self.assertIn("weights", config)
        self.assertEqual(len(config["weights"]), 7)

    def test_to_dict_has_thresholds(self):
        from substrate.organism.reliability_weighted_ranker import ReliabilityWeightedRanker
        ranker = ReliabilityWeightedRanker()
        config = ranker.to_dict()
        self.assertIn("execute_ready_thresholds", config)
        self.assertIn("supervised_thresholds", config)

    def test_to_dict_has_hard_gates(self):
        from substrate.organism.reliability_weighted_ranker import ReliabilityWeightedRanker
        ranker = ReliabilityWeightedRanker()
        config = ranker.to_dict()
        self.assertIn("hard_gates", config)
        self.assertGreaterEqual(len(config["hard_gates"]), 6)


if __name__ == "__main__":
    unittest.main()
