"""Phase 87 — Leverage + Resource / Tool Taxonomy v1 test suite.

115+ tests covering contracts, resources, tools, taxonomy, scoring,
recommendations, views, safety, EOS integration, layering, and regression.
"""

from __future__ import annotations

import ast
import pathlib
import sys
import tempfile
import unittest

sys.path.insert(0, "/opt/OS")

from umh.leverage.contracts import (
    LeverageAction,
    LeverageAssessment,
    LeverageConfidence,
    LeverageOpportunity,
    LeverageRecommendation,
    LeverageRiskLevel,
    LeverageTimeHorizon,
    LeverageType,
    ResourceProfile,
    ResourceType,
    ToolProfile,
    ToolType,
    _lev_id,
    clamp_score,
    normalize_confidence,
    normalize_leverage_action,
    normalize_leverage_type,
    normalize_resource_type,
    normalize_risk_level,
    normalize_time_horizon,
    normalize_tool_type,
)
from umh.leverage.resources import (
    build_default_user_resource_profiles,
    build_eos_workflow_resource_profiles,
    classify_resource,
    create_resource_profile,
)
from umh.leverage.tools import (
    build_default_tool_profiles,
    build_eos_workflow_tool_profiles,
    classify_tool,
    create_tool_profile,
)
from umh.leverage.taxonomy import (
    LeverageTaxonomyNode,
    build_default_leverage_taxonomy,
    explain_leverage_type,
    get_taxonomy_node,
    map_resource_to_leverage,
    map_tool_to_leverage,
)
from umh.leverage.scoring import (
    LeverageScorecard,
    build_leverage_scorecard,
    rank_leverage_opportunities,
    score_attention_efficiency,
    score_compounding_potential,
    score_cost_efficiency,
    score_dependency_risk,
    score_multiplier,
    score_overall_leverage,
    score_reversibility,
    score_risk_adjusted_value,
    score_strategic_alignment,
    score_time_to_impact,
)
from umh.leverage.recommendations import (
    assess_leverage_for_eos_tomorrow_plan,
    build_initiate_arena_leverage_recommendations,
    build_leverage_recommendation,
    leverage_recommendation_to_dict,
    recommend_leverage_action,
)
from umh.leverage.views import (
    LeverageAssessmentView,
    LeverageDashboardView,
    LeverageOpportunityView,
    LeverageRecommendationView,
    LeverageScorecardView,
    ResourceProfileView,
    ToolProfileView,
    assessment_to_view,
    build_leverage_dashboard_view,
    opportunity_to_view,
    recommendation_to_view,
    resource_to_view,
    scorecard_to_view,
    tool_to_view,
)
from umh.leverage.safety import (
    LeverageSafetyResult,
    leverage_safety_result_to_dict,
    scan_leverage_for_execution_patterns,
    scan_leverage_for_forbidden_imports,
    validate_leverage_modules_are_advisory_only,
    validate_leverage_recommendation_has_no_execution,
)


# ═══════════════════════════════════════════════════════════════════
#  1. CONTRACTS — NORMALIZATION
# ═══════════════════════════════════════════════════════════════════


class TestContractNormalization(unittest.TestCase):
    def test_normalize_leverage_type(self):
        self.assertEqual(normalize_leverage_type("human"), LeverageType.HUMAN)
        self.assertEqual(normalize_leverage_type(LeverageType.CAPITAL), LeverageType.CAPITAL)

    def test_normalize_resource_type(self):
        self.assertEqual(normalize_resource_type("money"), ResourceType.MONEY)
        self.assertEqual(normalize_resource_type(ResourceType.CODE), ResourceType.CODE)

    def test_normalize_tool_type(self):
        self.assertEqual(normalize_tool_type("software"), ToolType.SOFTWARE)
        self.assertEqual(normalize_tool_type(ToolType.API), ToolType.API)

    def test_normalize_leverage_action(self):
        self.assertEqual(normalize_leverage_action("do_self"), LeverageAction.DO_SELF)
        self.assertEqual(
            normalize_leverage_action(LeverageAction.AUTOMATE), LeverageAction.AUTOMATE
        )

    def test_normalize_time_horizon(self):
        self.assertEqual(normalize_time_horizon("today"), LeverageTimeHorizon.TODAY)
        self.assertEqual(normalize_time_horizon("century"), LeverageTimeHorizon.CENTURY)

    def test_normalize_risk(self):
        self.assertEqual(normalize_risk_level("high"), LeverageRiskLevel.HIGH)
        self.assertEqual(normalize_risk_level(LeverageRiskLevel.NONE), LeverageRiskLevel.NONE)

    def test_normalize_confidence(self):
        self.assertEqual(normalize_confidence("very_high"), LeverageConfidence.VERY_HIGH)
        self.assertEqual(normalize_confidence(LeverageConfidence.LOW), LeverageConfidence.LOW)

    def test_unknowns_degrade_safely(self):
        self.assertEqual(normalize_leverage_type("garbage"), LeverageType.UNKNOWN)
        self.assertEqual(normalize_resource_type("garbage"), ResourceType.UNKNOWN)
        self.assertEqual(normalize_tool_type("garbage"), ToolType.UNKNOWN)
        self.assertEqual(normalize_leverage_action("garbage"), LeverageAction.UNKNOWN)
        self.assertEqual(normalize_time_horizon("garbage"), LeverageTimeHorizon.UNKNOWN)
        self.assertEqual(normalize_risk_level("garbage"), LeverageRiskLevel.UNKNOWN)
        self.assertEqual(normalize_confidence("garbage"), LeverageConfidence.UNKNOWN)


# ═══════════════════════════════════════════════════════════════════
#  2. CONTRACTS — SERIALIZATION
# ═══════════════════════════════════════════════════════════════════


class TestContractSerialization(unittest.TestCase):
    def test_resource_profile_serializes(self):
        r = ResourceProfile(resource_id="r1", name="Test", resource_type=ResourceType.TIME)
        d = r.to_dict()
        self.assertEqual(d["resource_id"], "r1")
        self.assertEqual(d["resource_type"], "time")
        r2 = ResourceProfile.from_dict(d)
        self.assertEqual(r2.resource_type, ResourceType.TIME)

    def test_tool_profile_serializes(self):
        t = ToolProfile(tool_id="t1", name="Test", tool_type=ToolType.SOFTWARE)
        d = t.to_dict()
        self.assertEqual(d["tool_type"], "software")
        t2 = ToolProfile.from_dict(d)
        self.assertEqual(t2.tool_type, ToolType.SOFTWARE)

    def test_leverage_opportunity_serializes(self):
        o = LeverageOpportunity(
            opportunity_id="o1",
            title="Test",
            leverage_type=LeverageType.CAPITAL,
            risk_level=LeverageRiskLevel.LOW,
            confidence=LeverageConfidence.HIGH,
        )
        d = o.to_dict()
        self.assertEqual(d["leverage_type"], "capital")
        o2 = LeverageOpportunity.from_dict(d)
        self.assertEqual(o2.leverage_type, LeverageType.CAPITAL)

    def test_leverage_assessment_serializes(self):
        a = LeverageAssessment(assessment_id="a1", goal="Test goal")
        d = a.to_dict()
        self.assertEqual(d["goal"], "Test goal")
        self.assertIsInstance(d["resources"], list)

    def test_leverage_recommendation_serializes(self):
        r = LeverageRecommendation(
            recommendation_id="rec1",
            action=LeverageAction.DO_SELF,
            summary="Do it",
        )
        d = r.to_dict()
        self.assertEqual(d["action"], "do_self")
        self.assertEqual(d["summary"], "Do it")


# ═══════════════════════════════════════════════════════════════════
#  3. RESOURCES
# ═══════════════════════════════════════════════════════════════════


class TestResources(unittest.TestCase):
    def setUp(self):
        self.defaults = build_default_user_resource_profiles()

    def _has_resource(self, substring: str) -> bool:
        return any(substring.lower() in r.name.lower() for r in self.defaults)

    def test_default_resources_include_user_attention(self):
        self.assertTrue(self._has_resource("User Attention"))

    def test_default_resources_include_user_time(self):
        self.assertTrue(self._has_resource("User Time"))

    def test_default_resources_include_personal_brand_audience(self):
        self.assertTrue(self._has_resource("Personal Brand Audience"))

    def test_default_resources_include_umh_codebase(self):
        self.assertTrue(self._has_resource("UMH Codebase"))

    def test_default_resources_include_eos_tomorrow_loop(self):
        self.assertTrue(self._has_resource("EOS Tomorrow Operating Loop"))

    def test_default_resources_include_initiate_arena_offer(self):
        self.assertTrue(self._has_resource("Initiate Arena Offer"))

    def test_default_resources_include_empyrean_studio(self):
        self.assertTrue(self._has_resource("Empyrean Studio"))

    def test_default_resources_include_lyfe_institute(self):
        self.assertTrue(self._has_resource("Lyfe Institute"))

    def test_default_resources_include_ai_chat_archive(self):
        self.assertTrue(self._has_resource("AI Chat Archive"))

    def test_resource_classification_works(self):
        self.assertEqual(classify_resource("my attention span"), ResourceType.ATTENTION)
        self.assertEqual(classify_resource("some money"), ResourceType.MONEY)
        self.assertEqual(classify_resource("a codebase"), ResourceType.CODE)
        self.assertEqual(classify_resource("xyzzygarbage"), ResourceType.UNKNOWN)


# ═══════════════════════════════════════════════════════════════════
#  4. TOOLS
# ═══════════════════════════════════════════════════════════════════


class TestTools(unittest.TestCase):
    def setUp(self):
        self.defaults = build_default_tool_profiles()

    def _has_tool(self, substring: str) -> bool:
        return any(substring.lower() in t.name.lower() for t in self.defaults)

    def test_default_tools_include_umh(self):
        self.assertTrue(self._has_tool("UMH"))

    def test_default_tools_include_entrepreneuros(self):
        self.assertTrue(self._has_tool("EntrepreneurOS"))

    def test_default_tools_include_claude_code(self):
        self.assertTrue(self._has_tool("Claude Code"))

    def test_default_tools_include_llms(self):
        self.assertTrue(self._has_tool("ChatGPT") or self._has_tool("LLM"))

    def test_default_tools_include_computer_use(self):
        self.assertTrue(self._has_tool("Computer Use"))

    def test_default_tools_include_obsidian(self):
        self.assertTrue(self._has_tool("Obsidian"))

    def test_default_tools_include_notion(self):
        self.assertTrue(self._has_tool("Notion"))

    def test_default_tools_include_google_workspace(self):
        self.assertTrue(self._has_tool("Google Workspace"))

    def test_default_tools_include_instagram(self):
        self.assertTrue(self._has_tool("Instagram"))

    def test_default_tools_include_templates_sops(self):
        self.assertTrue(self._has_tool("Templates") or self._has_tool("SOP"))

    def test_tool_classification_works(self):
        self.assertEqual(classify_tool("claude code"), ToolType.AI_MODEL)
        self.assertEqual(classify_tool("instagram account"), ToolType.SOCIAL_PLATFORM)
        self.assertEqual(classify_tool("my template"), ToolType.TEMPLATE)
        self.assertEqual(classify_tool("xyzzygarbage"), ToolType.UNKNOWN)


# ═══════════════════════════════════════════════════════════════════
#  5. TAXONOMY
# ═══════════════════════════════════════════════════════════════════


class TestTaxonomy(unittest.TestCase):
    def setUp(self):
        self.taxonomy = build_default_leverage_taxonomy()

    def _has_type(self, lt: LeverageType) -> bool:
        return any(n.leverage_type == lt for n in self.taxonomy)

    def test_taxonomy_includes_human(self):
        self.assertTrue(self._has_type(LeverageType.HUMAN))

    def test_taxonomy_includes_code_software(self):
        self.assertTrue(self._has_type(LeverageType.CODE_SOFTWARE))

    def test_taxonomy_includes_content_media(self):
        self.assertTrue(self._has_type(LeverageType.CONTENT_MEDIA))

    def test_taxonomy_includes_capital(self):
        self.assertTrue(self._has_type(LeverageType.CAPITAL))

    def test_taxonomy_includes_systems_process(self):
        self.assertTrue(self._has_type(LeverageType.SYSTEMS_PROCESS))

    def test_taxonomy_includes_ai_model(self):
        self.assertTrue(self._has_type(LeverageType.AI_MODEL))

    def test_taxonomy_includes_network_relationship(self):
        self.assertTrue(self._has_type(LeverageType.NETWORK_RELATIONSHIP))

    def test_taxonomy_includes_attention_focus(self):
        self.assertTrue(self._has_type(LeverageType.ATTENTION_FOCUS))

    def test_taxonomy_includes_data(self):
        self.assertTrue(self._has_type(LeverageType.DATA))

    def test_taxonomy_includes_distribution(self):
        self.assertTrue(self._has_type(LeverageType.DISTRIBUTION))

    def test_taxonomy_includes_brand(self):
        self.assertTrue(self._has_type(LeverageType.BRAND))

    def test_taxonomy_includes_physical_infrastructure(self):
        self.assertTrue(self._has_type(LeverageType.PHYSICAL_INFRASTRUCTURE))

    def test_taxonomy_includes_robotics_automation(self):
        self.assertTrue(self._has_type(LeverageType.ROBOTICS_AUTOMATION))

    def test_taxonomy_includes_real_estate(self):
        self.assertTrue(self._has_type(LeverageType.REAL_ESTATE))

    def test_taxonomy_includes_manufacturing(self):
        self.assertTrue(self._has_type(LeverageType.MANUFACTURING))

    def test_taxonomy_includes_fulfillment(self):
        self.assertTrue(self._has_type(LeverageType.FULFILLMENT))

    def test_taxonomy_node_has_examples(self):
        node = get_taxonomy_node(LeverageType.HUMAN)
        self.assertIsNotNone(node)
        self.assertTrue(len(node.examples) > 0)

    def test_taxonomy_node_has_failure_modes(self):
        node = get_taxonomy_node(LeverageType.AI_MODEL)
        self.assertIsNotNone(node)
        self.assertTrue(len(node.common_failure_modes) > 0)

    def test_map_resource_to_leverage_works(self):
        r = ResourceProfile(resource_type=ResourceType.MONEY)
        self.assertEqual(map_resource_to_leverage(r), LeverageType.CAPITAL)

    def test_map_tool_to_leverage_works(self):
        t = ToolProfile(tool_type=ToolType.AI_MODEL)
        self.assertEqual(map_tool_to_leverage(t), LeverageType.AI_MODEL)


# ═══════════════════════════════════════════════════════════════════
#  6. SCORING
# ═══════════════════════════════════════════════════════════════════


class TestScoring(unittest.TestCase):
    def _make_opp(self, **kwargs) -> LeverageOpportunity:
        defaults = {
            "opportunity_id": "opp_test",
            "title": "Test",
            "expected_multiplier": 5.0,
            "time_to_impact": "week",
            "cost": "low",
            "risk_level": LeverageRiskLevel.LOW,
            "reversibility": "reversible",
            "compounding_potential": 0.5,
            "strategic_alignment": 0.7,
            "attention_required": "medium",
            "confidence": LeverageConfidence.HIGH,
        }
        defaults.update(kwargs)
        return LeverageOpportunity(**defaults)

    def test_score_multiplier_bounded(self):
        self.assertGreaterEqual(score_multiplier(self._make_opp()), 0.0)
        self.assertLessEqual(score_multiplier(self._make_opp()), 1.0)

    def test_time_to_impact_score_bounded(self):
        self.assertGreaterEqual(score_time_to_impact(self._make_opp()), 0.0)
        self.assertLessEqual(score_time_to_impact(self._make_opp()), 1.0)

    def test_cost_efficiency_score_bounded(self):
        self.assertGreaterEqual(score_cost_efficiency(self._make_opp()), 0.0)
        self.assertLessEqual(score_cost_efficiency(self._make_opp()), 1.0)

    def test_risk_adjusted_score_bounded(self):
        self.assertGreaterEqual(score_risk_adjusted_value(self._make_opp()), 0.0)
        self.assertLessEqual(score_risk_adjusted_value(self._make_opp()), 1.0)

    def test_reversibility_score_bounded(self):
        self.assertGreaterEqual(score_reversibility(self._make_opp()), 0.0)
        self.assertLessEqual(score_reversibility(self._make_opp()), 1.0)

    def test_compounding_score_bounded(self):
        self.assertGreaterEqual(score_compounding_potential(self._make_opp()), 0.0)
        self.assertLessEqual(score_compounding_potential(self._make_opp()), 1.0)

    def test_strategic_alignment_score_bounded(self):
        self.assertGreaterEqual(score_strategic_alignment(self._make_opp()), 0.0)
        self.assertLessEqual(score_strategic_alignment(self._make_opp()), 1.0)

    def test_attention_efficiency_score_bounded(self):
        self.assertGreaterEqual(score_attention_efficiency(self._make_opp()), 0.0)
        self.assertLessEqual(score_attention_efficiency(self._make_opp()), 1.0)

    def test_dependency_risk_score_bounded(self):
        self.assertGreaterEqual(score_dependency_risk(self._make_opp()), 0.0)
        self.assertLessEqual(score_dependency_risk(self._make_opp()), 1.0)

    def test_overall_score_bounded(self):
        self.assertGreaterEqual(score_overall_leverage(self._make_opp()), 0.0)
        self.assertLessEqual(score_overall_leverage(self._make_opp()), 1.0)

    def test_high_dependency_risk_lowers_score(self):
        normal = score_overall_leverage(self._make_opp(metadata={"dependency_risk": "low"}))
        high_dep = score_overall_leverage(self._make_opp(metadata={"dependency_risk": "critical"}))
        self.assertGreater(normal, high_dep)

    def test_high_compounding_raises_score(self):
        low_comp = score_overall_leverage(self._make_opp(compounding_potential=0.1))
        high_comp = score_overall_leverage(self._make_opp(compounding_potential=0.9))
        self.assertGreater(high_comp, low_comp)

    def test_ranking_deterministic(self):
        opps = [
            self._make_opp(opportunity_id="a", expected_multiplier=2.0),
            self._make_opp(opportunity_id="b", expected_multiplier=10.0),
            self._make_opp(opportunity_id="c", expected_multiplier=5.0),
        ]
        r1 = rank_leverage_opportunities(opps)
        r2 = rank_leverage_opportunities(opps)
        self.assertEqual(
            [x[0].opportunity_id for x in r1],
            [x[0].opportunity_id for x in r2],
        )


# ═══════════════════════════════════════════════════════════════════
#  7. RECOMMENDATIONS
# ═══════════════════════════════════════════════════════════════════


class TestRecommendations(unittest.TestCase):
    def _make_opp(self, **kwargs) -> LeverageOpportunity:
        defaults = {
            "opportunity_id": "opp_test",
            "title": "Test task",
            "expected_multiplier": 3.0,
            "risk_level": LeverageRiskLevel.LOW,
            "confidence": LeverageConfidence.HIGH,
        }
        defaults.update(kwargs)
        return LeverageOpportunity(**defaults)

    def test_repeated_low_risk_recommends_automate_or_template(self):
        opp = self._make_opp(
            title="Repeated scheduling task", description="repeated rule-based low-risk automation"
        )
        action = recommend_leverage_action(opp)
        self.assertIn(action, (LeverageAction.AUTOMATE, LeverageAction.TEMPLATE))

    def test_core_personal_brand_recommends_do_self(self):
        opp = self._make_opp(
            title="Personal brand sales call", description="high-trust selling judgment"
        )
        action = recommend_leverage_action(opp)
        self.assertEqual(action, LeverageAction.DO_SELF)

    def test_resource_bottleneck_recommends_delegate_or_hire(self):
        opp = self._make_opp(
            title="Bottleneck on editing", description="bandwidth bottleneck delegate"
        )
        action = recommend_leverage_action(opp)
        self.assertIn(action, (LeverageAction.DELEGATE, LeverageAction.HIRE))

    def test_insufficient_evidence_recommends_research(self):
        opp = self._make_opp(confidence=LeverageConfidence.VERY_LOW)
        action = recommend_leverage_action(opp)
        self.assertEqual(action, LeverageAction.RESEARCH)

    def test_high_uncertainty_recommends_simulate(self):
        opp = self._make_opp(
            risk_level=LeverageRiskLevel.HIGH,
            confidence=LeverageConfidence.MEDIUM,
            title="Test scenario",
            description="uncertain outcome",
        )
        action = recommend_leverage_action(opp)
        self.assertEqual(action, LeverageAction.SIMULATE)

    def test_low_value_task_recommends_eliminate(self):
        opp = self._make_opp(title="Low value busywork", description="no strategic value vanity")
        action = recommend_leverage_action(opp)
        self.assertEqual(action, LeverageAction.ELIMINATE)

    def test_high_risk_real_world_recommends_approve_later(self):
        opp = self._make_opp(
            title="Financial commitment",
            description="real-world financial action",
            risk_level=LeverageRiskLevel.CRITICAL,
            confidence=LeverageConfidence.HIGH,
        )
        action = recommend_leverage_action(opp)
        self.assertEqual(action, LeverageAction.APPROVE_AND_EXECUTE_LATER)

    def test_initiate_arena_recommendations_include_content(self):
        recs = build_initiate_arena_leverage_recommendations()
        summaries = [r.summary.lower() for r in recs]
        self.assertTrue(any("content" in s for s in summaries))

    def test_initiate_arena_recommendations_include_dm(self):
        recs = build_initiate_arena_leverage_recommendations()
        summaries = [r.summary.lower() for r in recs]
        self.assertTrue(any("dm" in s or "conversation" in s for s in summaries))

    def test_initiate_arena_recommendations_include_qualifying(self):
        recs = build_initiate_arena_leverage_recommendations()
        summaries = [r.summary.lower() for r in recs]
        self.assertTrue(any("qualif" in s for s in summaries))

    def test_initiate_arena_recommendations_include_objections(self):
        recs = build_initiate_arena_leverage_recommendations()
        summaries = [r.summary.lower() for r in recs]
        self.assertTrue(any("objection" in s for s in summaries))

    def test_initiate_arena_recommendations_include_kpi(self):
        recs = build_initiate_arena_leverage_recommendations()
        summaries = [r.summary.lower() for r in recs]
        self.assertTrue(any("kpi" in s or "track" in s for s in summaries))

    def test_recommendation_includes_guardrails(self):
        recs = build_initiate_arena_leverage_recommendations()
        for rec in recs:
            self.assertIsInstance(rec.guardrails, list)
            self.assertTrue(len(rec.guardrails) > 0, f"{rec.summary} has no guardrails")

    def test_recommendation_includes_non_actions(self):
        recs = build_initiate_arena_leverage_recommendations()
        has_non_actions = any(len(rec.non_actions) > 0 for rec in recs)
        self.assertTrue(has_non_actions)


# ═══════════════════════════════════════════════════════════════════
#  8. EOS INTEGRATION
# ═══════════════════════════════════════════════════════════════════


class TestEOSIntegration(unittest.TestCase):
    def test_phase86_daily_plan_can_receive_leverage(self):
        from umh.tomorrow.views import DailyBriefView, enrich_brief_with_leverage

        brief = DailyBriefView(date="2026-05-03", objective_count=5)
        recs = build_initiate_arena_leverage_recommendations()
        enriched = enrich_brief_with_leverage(brief, recs, bottlenecks=["founder bandwidth"])
        self.assertIn("leverage", enriched.metadata)
        self.assertGreater(enriched.metadata["leverage"]["recommendation_count"], 0)

    def test_phase86_tests_still_pass_import(self):
        from umh.tomorrow import contracts as tc
        from umh.tomorrow import orchestrator as to
        from umh.tomorrow import views as tv

        self.assertTrue(hasattr(tc, "LoopPhase"))
        self.assertTrue(hasattr(to, "run_full_cycle"))
        self.assertTrue(hasattr(tv, "enrich_brief_with_leverage"))


# ═══════════════════════════════════════════════════════════════════
#  9. VIEWS
# ═══════════════════════════════════════════════════════════════════


class TestViews(unittest.TestCase):
    def test_resource_view_serializes(self):
        r = ResourceProfile(resource_id="r1", name="Test", resource_type=ResourceType.TIME)
        v = resource_to_view(r)
        d = v.to_dict()
        self.assertEqual(d["name"], "Test")
        self.assertEqual(d["resource_type"], "time")

    def test_tool_view_serializes(self):
        t = ToolProfile(tool_id="t1", name="Test", tool_type=ToolType.SOFTWARE)
        v = tool_to_view(t)
        d = v.to_dict()
        self.assertEqual(d["tool_type"], "software")

    def test_opportunity_view_serializes(self):
        o = LeverageOpportunity(opportunity_id="o1", title="Test", leverage_type=LeverageType.HUMAN)
        v = opportunity_to_view(o)
        d = v.to_dict()
        self.assertEqual(d["leverage_type"], "human")

    def test_scorecard_view_serializes(self):
        sc = LeverageScorecard(scorecard_id="sc1", overall_score=0.75)
        v = scorecard_to_view(sc)
        d = v.to_dict()
        self.assertEqual(d["overall_score"], 0.75)

    def test_recommendation_view_serializes(self):
        rec = LeverageRecommendation(
            recommendation_id="rec1",
            action=LeverageAction.DO_SELF,
            summary="Do it",
        )
        v = recommendation_to_view(rec)
        d = v.to_dict()
        self.assertEqual(d["action"], "do_self")
        self.assertEqual(d["summary"], "Do it")

    def test_dashboard_view_serializes(self):
        recs = build_initiate_arena_leverage_recommendations()
        resources = build_default_user_resource_profiles()
        tools = build_default_tool_profiles()
        v = build_leverage_dashboard_view(resources, tools, recs)
        d = v.to_dict()
        self.assertGreater(d["resource_count"], 0)
        self.assertGreater(d["tool_count"], 0)
        self.assertGreater(d["recommendation_count"], 0)

    def test_views_omit_secrets(self):
        r = ResourceProfile(
            resource_id="r1",
            name="Test",
            resource_type=ResourceType.TIME,
            sensitivity="secret",
        )
        v = resource_to_view(r)
        d = v.to_dict()
        self.assertNotIn("sensitivity", d)
        self.assertNotIn("constraints", d)
        self.assertNotIn("cost", d)


# ═══════════════════════════════════════════════════════════════════
#  10. SAFETY
# ═══════════════════════════════════════════════════════════════════


class TestSafety(unittest.TestCase):
    def test_safety_scan_safe_on_leverage_module(self):
        result = validate_leverage_modules_are_advisory_only()
        self.assertTrue(result.safe, f"Violations: {result.violations}")

    def test_safety_detects_subprocess_in_temp(self):
        with tempfile.NamedTemporaryFile(suffix=".py", mode="w", delete=False) as f:
            f.write("import subprocess\n")
            f.flush()
            result = scan_leverage_for_forbidden_imports([f.name])
            self.assertFalse(result.safe)
            self.assertTrue(any("subprocess" in v for v in result.violations))

    def test_safety_detects_requests_in_temp(self):
        with tempfile.NamedTemporaryFile(suffix=".py", mode="w", delete=False) as f:
            f.write("import requests\n")
            f.flush()
            result = scan_leverage_for_forbidden_imports([f.name])
            self.assertFalse(result.safe)

    def test_safety_detects_adapter_import_in_temp(self):
        with tempfile.NamedTemporaryFile(suffix=".py", mode="w", delete=False) as f:
            f.write("from umh.adapters.slack import send\n")
            f.flush()
            result = scan_leverage_for_forbidden_imports([f.name])
            self.assertFalse(result.safe)
            self.assertTrue(any("adapter" in v.lower() for v in result.violations))

    def test_safety_detects_execution_pattern_in_temp(self):
        with tempfile.NamedTemporaryFile(suffix=".py", mode="w", delete=False) as f:
            f.write("def foo():\n    execute()\n")
            f.flush()
            result = scan_leverage_for_execution_patterns([f.name])
            self.assertFalse(result.safe)

    def test_recommendation_has_no_execution(self):
        rec = LeverageRecommendation(action=LeverageAction.DO_SELF, first_step="Start with content")
        result = validate_leverage_recommendation_has_no_execution(rec)
        self.assertTrue(result.safe)


# ═══════════════════════════════════════════════════════════════════
#  11. LAYERING
# ═══════════════════════════════════════════════════════════════════


class TestLayering(unittest.TestCase):
    def _get_imports_for_file(self, filepath: str) -> set[str]:
        source = pathlib.Path(filepath).read_text()
        tree = ast.parse(source)
        imports: set[str] = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    imports.add(alias.name.split(".")[0])
            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    imports.add(node.module.split(".")[0])
                    imports.add(node.module)
        return imports

    def _check_no_forbidden(self, filepath: str):
        imports = self._get_imports_for_file(filepath)
        forbidden = {"subprocess", "requests", "httpx"}
        found = imports & forbidden
        self.assertEqual(found, set(), f"{filepath} imports {found}")

    def test_contracts_no_subprocess(self):
        self._check_no_forbidden("/opt/OS/umh/leverage/contracts.py")

    def test_resources_no_subprocess(self):
        self._check_no_forbidden("/opt/OS/umh/leverage/resources.py")

    def test_tools_no_subprocess(self):
        self._check_no_forbidden("/opt/OS/umh/leverage/tools.py")

    def test_taxonomy_no_subprocess(self):
        self._check_no_forbidden("/opt/OS/umh/leverage/taxonomy.py")

    def test_scoring_no_subprocess(self):
        self._check_no_forbidden("/opt/OS/umh/leverage/scoring.py")

    def test_recommendations_no_subprocess(self):
        self._check_no_forbidden("/opt/OS/umh/leverage/recommendations.py")

    def test_views_no_subprocess(self):
        self._check_no_forbidden("/opt/OS/umh/leverage/views.py")

    def test_safety_no_network(self):
        imports = self._get_imports_for_file("/opt/OS/umh/leverage/safety.py")
        self.assertNotIn("requests", imports)
        self.assertNotIn("httpx", imports)

    def test_no_adapter_imports(self):
        leverage_dir = pathlib.Path("/opt/OS/umh/leverage")
        for py_file in leverage_dir.glob("*.py"):
            if py_file.name == "__init__.py":
                continue
            imports = self._get_imports_for_file(str(py_file))
            adapter_imports = [i for i in imports if "adapter" in i.lower()]
            self.assertEqual(adapter_imports, [], f"{py_file.name} imports adapters")

    def test_no_execution_engine_imports(self):
        leverage_dir = pathlib.Path("/opt/OS/umh/leverage")
        for py_file in leverage_dir.glob("*.py"):
            if py_file.name == "__init__.py":
                continue
            imports = self._get_imports_for_file(str(py_file))
            exec_imports = [i for i in imports if "umh.execution" in i]
            self.assertEqual(exec_imports, [], f"{py_file.name} imports execution engine")

    def test_no_governance_mutation_imports(self):
        leverage_dir = pathlib.Path("/opt/OS/umh/leverage")
        for py_file in leverage_dir.glob("*.py"):
            if py_file.name == "__init__.py":
                continue
            imports = self._get_imports_for_file(str(py_file))
            gov_imports = [i for i in imports if "umh.governance" in i]
            self.assertEqual(gov_imports, [], f"{py_file.name} imports governance")

    def test_no_memory_promotion_imports(self):
        leverage_dir = pathlib.Path("/opt/OS/umh/leverage")
        for py_file in leverage_dir.glob("*.py"):
            if py_file.name == "__init__.py":
                continue
            imports = self._get_imports_for_file(str(py_file))
            mem_imports = [i for i in imports if "umh.memory" in i]
            self.assertEqual(mem_imports, [], f"{py_file.name} imports memory")

    def test_no_live_model_calls(self):
        leverage_dir = pathlib.Path("/opt/OS/umh/leverage")
        for py_file in leverage_dir.glob("*.py"):
            if py_file.name == "__init__.py":
                continue
            imports = self._get_imports_for_file(str(py_file))
            model_imports = [
                i
                for i in imports
                if any(m in i for m in ["anthropic", "openai", "google.genai", "ollama"])
            ]
            self.assertEqual(model_imports, [], f"{py_file.name} imports live model SDK")


# ═══════════════════════════════════════════════════════════════════
#  12. REGRESSION
# ═══════════════════════════════════════════════════════════════════


class TestPhase87Regression(unittest.TestCase):
    def test_phase86_importable(self):
        from umh.tomorrow import contracts, orchestrator, views, safety, first_workflow

        self.assertTrue(hasattr(contracts, "LoopPhase"))

    def test_phase85b_importable(self):
        from umh.council.archetypes import get_all_thinker_profiles  # noqa: F401
        from umh.council.adversarial import run_adversarial_assessment  # noqa: F401

    def test_phase85_importable(self):
        from umh.council.deliberation import deliberate  # noqa: F401
        from umh.council.contracts import CouncilStatus  # noqa: F401

    def test_phase84a_importable(self):
        from umh.ontology.polarity_synthesis import PolaritySynthesis  # noqa: F401

    def test_phase84_importable(self):
        from umh.control.api import app  # noqa: F401

    def test_phase82_importable(self):
        from umh.storage.backend import StorageBackend  # noqa: F401

    def test_phase81_importable(self):
        from umh.ontology.laws import UniversalLaw  # noqa: F401

    def test_phase80_importable(self):
        from umh.registry.contracts import RegistryType  # noqa: F401

    def test_phase87_importable(self):
        from umh.leverage import (
            contracts,
            resources,
            tools,
            taxonomy,
            scoring,
            recommendations,
            views,
            safety,
        )

        self.assertTrue(hasattr(contracts, "LeverageType"))
        self.assertTrue(hasattr(resources, "build_default_user_resource_profiles"))
        self.assertTrue(hasattr(tools, "build_default_tool_profiles"))
        self.assertTrue(hasattr(taxonomy, "build_default_leverage_taxonomy"))
        self.assertTrue(hasattr(scoring, "score_overall_leverage"))
        self.assertTrue(hasattr(recommendations, "build_initiate_arena_leverage_recommendations"))
        self.assertTrue(hasattr(views, "build_leverage_dashboard_view"))
        self.assertTrue(hasattr(safety, "validate_leverage_modules_are_advisory_only"))


if __name__ == "__main__":
    unittest.main()
