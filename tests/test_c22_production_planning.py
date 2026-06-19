"""Tests for C22.1 — Production Planning Runtime."""
from __future__ import annotations

import sys
import time
import unittest
from dataclasses import dataclass, field
from typing import Any
from unittest.mock import MagicMock

sys.path.insert(0, "/opt/OS")

from substrate.organism.production_planning_runtime import (
    DisciplinePacket,
    ProductionDiscipline,
    ProductionPlan,
    ProductionPlanningRuntime,
    ProductionType,
    _PRODUCTION_TEMPLATES,
    _TYPE_KEYWORDS,
    _TYPE_PRIORITY,
)


# ── Fakes ────────────────────────────────────────────────────────────


class FakeWorkPacketEngine:
    """Fake WorkPacketEngine that records calls and returns canned batches."""

    def __init__(self) -> None:
        self.decompose_calls: list[dict[str, Any]] = []
        self._call_count = 0

    def decompose_intent_to_batch(
        self,
        user_intent: str = "",
        desired_end_state: str = "",
        constraints: list[str] | None = None,
        idempotency_key: str = "",
    ) -> dict[str, Any]:
        self._call_count += 1
        self.decompose_calls.append({
            "user_intent": user_intent,
            "desired_end_state": desired_end_state,
            "constraints": constraints,
            "idempotency_key": idempotency_key,
        })
        return {
            "batch_id": f"batch-{self._call_count}",
            "idempotency_key": idempotency_key,
            "parent_packet": {"packet_id": f"wp-parent-{self._call_count}", "title": user_intent[:50]},
            "child_packets": [],
            "dependency_edges": [],
            "overnight_classification": {},
            "created_count": 1,
            "already_existed": False,
            "ok": True,
        }


class FakeGovernanceRuntime:
    """Fake GovernanceRuntime with configurable health."""

    def __init__(self, health_value: str = "coherent") -> None:
        self._health_value = health_value

    def health(self) -> Any:
        mock = MagicMock()
        mock.value = self._health_value
        return mock


class _Unavailable:
    """Sentinel to prevent lazy loading in tests."""

    def __getattr__(self, name: str) -> Any:
        raise AttributeError(f"Unavailable: {name}")


@dataclass
class FakeTradeoffSnapshot:
    active_tradeoffs: list[dict[str, Any]] = field(default_factory=list)
    highest_cost_targets: list[dict[str, Any]] = field(default_factory=list)
    resource_contention: dict[str, list[str]] = field(default_factory=dict)
    overall_severity: str = "negligible"
    generated_at: float = 0.0


class FakeTradeoffEngine:
    """Fake TradeoffIntelligenceEngine."""

    def __init__(self, severity: str = "negligible") -> None:
        self._severity = severity

    def snapshot(self) -> FakeTradeoffSnapshot:
        return FakeTradeoffSnapshot(
            overall_severity=self._severity,
            generated_at=time.time(),
        )


@dataclass
class FakeTrajectoryForecast:
    status: str = "stable"
    confidence: float = 0.7
    entity_id: str = "work"
    entity_type: str = "portfolio"


class FakeTrajectoryRuntime:
    """Fake TrajectoryIntelligenceRuntime."""

    def __init__(self, status: str = "stable", confidence: float = 0.7) -> None:
        self._status = status
        self._confidence = confidence

    def forecast_work(self) -> FakeTrajectoryForecast:
        return FakeTrajectoryForecast(
            status=self._status,
            confidence=self._confidence,
        )


# ── Test helpers ─────────────────────────────────────────────────────


def _make_runtime(
    packets: bool = True,
    governance: bool = True,
    tradeoff: bool = True,
    trajectory: bool = True,
) -> ProductionPlanningRuntime:
    """Create a ProductionPlanningRuntime with fake subsystems.

    When a subsystem is disabled, we pass _Unavailable() instead of None
    so the lazy property doesn't try to import the real implementation.
    """
    _no = _Unavailable()
    return ProductionPlanningRuntime(
        work_packet_engine=FakeWorkPacketEngine() if packets else _no,
        governance_runtime=FakeGovernanceRuntime() if governance else _no,
        tradeoff_engine=FakeTradeoffEngine() if tradeoff else _no,
        trajectory_runtime=FakeTrajectoryRuntime() if trajectory else _no,
    )


# ── Tests ────────────────────────────────────────────────────────────


class TestProductionTypes(unittest.TestCase):
    """Test production type enum and templates."""

    def test_all_production_types_have_templates(self) -> None:
        for pt in ProductionType:
            if pt.value == "documentation":
                continue
            self.assertIn(pt.value, _PRODUCTION_TEMPLATES, f"Missing template for {pt.value}")

    def test_all_template_disciplines_are_valid(self) -> None:
        valid = {d.value for d in ProductionDiscipline}
        for tname, entries in _PRODUCTION_TEMPLATES.items():
            for discipline, _label, _desc in entries:
                self.assertIn(
                    discipline, valid,
                    f"Template {tname} has invalid discipline: {discipline}",
                )

    def test_type_priority_covers_all_keyword_types(self) -> None:
        for tname in _TYPE_KEYWORDS:
            self.assertIn(tname, _TYPE_PRIORITY, f"Missing from priority: {tname}")


class TestClassification(unittest.TestCase):
    """Test deterministic production type classification."""

    def setUp(self) -> None:
        self.runtime = _make_runtime()

    def test_fix_classification(self) -> None:
        result = self.runtime.classify_production_type("Fix the login bug in auth module")
        self.assertEqual(result, "fix")

    def test_refactor_classification(self) -> None:
        result = self.runtime.classify_production_type("Refactor the authentication module to decouple concerns")
        self.assertEqual(result, "refactor")

    def test_infrastructure_classification(self) -> None:
        result = self.runtime.classify_production_type("Set up Docker deployment pipeline")
        self.assertEqual(result, "infrastructure")

    def test_feature_classification(self) -> None:
        result = self.runtime.classify_production_type("Add user profile page")
        self.assertEqual(result, "feature")

    def test_full_product_classification(self) -> None:
        result = self.runtime.classify_production_type("Build new app from scratch")
        self.assertEqual(result, "full_product")

    def test_migration_classification(self) -> None:
        result = self.runtime.classify_production_type("Migrate database schema to v2")
        self.assertEqual(result, "migration")

    def test_automation_classification(self) -> None:
        result = self.runtime.classify_production_type("Automate the daily backup workflow")
        self.assertEqual(result, "automation")

    def test_documentation_classification(self) -> None:
        result = self.runtime.classify_production_type("Write API documentation for the REST endpoints")
        self.assertEqual(result, "documentation")

    def test_unknown_defaults_to_feature(self) -> None:
        result = self.runtime.classify_production_type("something completely unrelated xyz")
        self.assertEqual(result, "feature")

    def test_case_insensitive(self) -> None:
        result = self.runtime.classify_production_type("FIX THE LOGIN BUG")
        self.assertEqual(result, "fix")


class TestRiskClassification(unittest.TestCase):
    """Test deterministic risk classification."""

    def setUp(self) -> None:
        self.runtime = _make_runtime()

    def test_high_risk_database(self) -> None:
        self.assertEqual(self.runtime.classify_risk("Migrate database schema"), "high")

    def test_high_risk_auth(self) -> None:
        self.assertEqual(self.runtime.classify_risk("Fix auth token handling"), "high")

    def test_medium_risk_api(self) -> None:
        self.assertEqual(self.runtime.classify_risk("Refactor the API endpoints"), "medium")

    def test_low_risk_docs(self) -> None:
        self.assertEqual(self.runtime.classify_risk("Update readme"), "low")

    def test_default_low(self) -> None:
        self.assertEqual(self.runtime.classify_risk("xyz unknown"), "low")


class TestDisciplineExpansion(unittest.TestCase):
    """Test discipline template expansion."""

    def setUp(self) -> None:
        self.runtime = _make_runtime()

    def test_full_product_has_all_9_disciplines(self) -> None:
        disciplines = self.runtime.required_disciplines("full_product")
        self.assertEqual(len(disciplines), 9)
        for d in ProductionDiscipline:
            self.assertIn(d.value, disciplines)

    def test_feature_has_4_disciplines(self) -> None:
        disciplines = self.runtime.required_disciplines("feature")
        self.assertEqual(len(disciplines), 4)
        self.assertIn("architecture", disciplines)
        self.assertIn("implementation", disciplines)
        self.assertIn("testing", disciplines)
        self.assertIn("review", disciplines)

    def test_fix_has_4_disciplines(self) -> None:
        disciplines = self.runtime.required_disciplines("fix")
        self.assertEqual(len(disciplines), 4)

    def test_infrastructure_has_6_disciplines(self) -> None:
        disciplines = self.runtime.required_disciplines("infrastructure")
        self.assertEqual(len(disciplines), 6)
        self.assertIn("security", disciplines)
        self.assertIn("recovery", disciplines)

    def test_unknown_type_falls_back_to_feature(self) -> None:
        disciplines = self.runtime.required_disciplines("nonexistent")
        self.assertEqual(disciplines, self.runtime.required_disciplines("feature"))

    def test_template_produces_discipline_packets(self) -> None:
        packets = self.runtime.template_for_type("feature")
        self.assertEqual(len(packets), 4)
        self.assertIsInstance(packets[0], DisciplinePacket)
        self.assertEqual(packets[0].discipline, "architecture")

    def test_dependency_chain_is_sequential(self) -> None:
        packets = self.runtime.template_for_type("full_product")
        self.assertEqual(packets[0].depends_on, [])
        self.assertEqual(packets[1].depends_on, ["architecture"])
        self.assertIn("architecture", packets[2].depends_on)
        self.assertIn("implementation", packets[2].depends_on)


class TestRoleEstimation(unittest.TestCase):
    """Test org role estimation."""

    def setUp(self) -> None:
        self.runtime = _make_runtime()

    def test_feature_roles(self) -> None:
        disciplines = ["architecture", "implementation", "testing", "review"]
        roles = self.runtime.estimate_roles(disciplines)
        role_names = [r["role"] for r in roles]
        self.assertIn("architect", role_names)
        self.assertIn("contributor", role_names)
        self.assertIn("reviewer", role_names)

    def test_full_product_roles_include_lead(self) -> None:
        disciplines = self.runtime.required_disciplines("full_product")
        roles = self.runtime.estimate_roles(disciplines)
        role_names = [r["role"] for r in roles]
        self.assertIn("lead", role_names)

    def test_no_duplicate_roles(self) -> None:
        disciplines = self.runtime.required_disciplines("full_product")
        roles = self.runtime.estimate_roles(disciplines)
        role_names = [r["role"] for r in roles]
        self.assertEqual(len(role_names), len(set(role_names)))

    def test_contributor_accumulates_disciplines(self) -> None:
        disciplines = ["implementation", "testing", "documentation"]
        roles = self.runtime.estimate_roles(disciplines)
        contributor = next(r for r in roles if r["role"] == "contributor")
        self.assertGreater(len(contributor["disciplines"]), 1)


class TestPlanProduction(unittest.TestCase):
    """Test the core plan_production method."""

    def setUp(self) -> None:
        self.runtime = _make_runtime()

    def test_basic_plan_creation(self) -> None:
        plan = self.runtime.plan_production("Build user dashboard", target="projection")
        self.assertIsInstance(plan, ProductionPlan)
        self.assertEqual(plan.goal, "Build user dashboard")
        self.assertEqual(plan.target, "projection")
        self.assertGreater(len(plan.packets), 0)
        self.assertGreater(len(plan.disciplines_covered), 0)
        self.assertTrue(plan.plan_id.startswith("pp-"))
        self.assertGreater(plan.generated_at, 0)

    def test_plan_type_is_classified(self) -> None:
        plan = self.runtime.plan_production("Fix login bug", target="substrate")
        self.assertEqual(plan.production_type, "fix")

    def test_full_product_covers_all_disciplines(self) -> None:
        plan = self.runtime.plan_production(
            "Build new app from scratch", target="client_product"
        )
        self.assertEqual(plan.production_type, "full_product")
        for d in ProductionDiscipline:
            self.assertIn(d.value, plan.disciplines_covered)

    def test_skip_disciplines(self) -> None:
        plan = self.runtime.plan_production(
            "Build new product from scratch",
            target="projection",
            skip_disciplines=["recovery", "documentation"],
        )
        self.assertNotIn("recovery", plan.disciplines_covered)
        self.assertNotIn("documentation", plan.disciplines_covered)
        self.assertEqual(len(plan.disciplines_deferred), 2)

    def test_dependency_order_matches_disciplines(self) -> None:
        plan = self.runtime.plan_production("Add feature X", target="substrate")
        self.assertEqual(plan.dependency_order, plan.disciplines_covered)

    def test_risk_summary_populated(self) -> None:
        plan = self.runtime.plan_production("Migrate database to v2", target="substrate")
        self.assertIn("overall_risk", plan.risk_summary)
        self.assertEqual(plan.risk_summary["overall_risk"], "high")

    def test_tradeoff_analysis_populated(self) -> None:
        plan = self.runtime.plan_production("Add feature X", target="substrate")
        self.assertIn("available", plan.tradeoff_analysis)
        self.assertTrue(plan.tradeoff_analysis["available"])

    def test_estimated_roles_populated(self) -> None:
        plan = self.runtime.plan_production("Add feature X", target="substrate")
        self.assertGreater(len(plan.estimated_roles), 0)
        role_names = [r["role"] for r in plan.estimated_roles]
        self.assertIn("contributor", role_names)

    def test_work_packet_engine_called_per_discipline(self) -> None:
        engine = FakeWorkPacketEngine()
        runtime = ProductionPlanningRuntime(work_packet_engine=engine)
        plan = runtime.plan_production("Add user profile", target="substrate")
        self.assertEqual(len(engine.decompose_calls), len(plan.disciplines_covered))

    def test_plan_stored_in_history(self) -> None:
        plan = self.runtime.plan_production("Build X", target="substrate")
        recent = self.runtime.recent_plans()
        self.assertEqual(len(recent), 1)
        self.assertEqual(recent[0]["plan_id"], plan.plan_id)


class TestPlanWithoutSubsystems(unittest.TestCase):
    """Test graceful degradation when subsystems are unavailable."""

    def test_no_packet_engine_uses_templates(self) -> None:
        runtime = _make_runtime(packets=False)
        plan = runtime.plan_production("Add feature", target="substrate")
        self.assertGreater(len(plan.packets), 0)
        self.assertIn("discipline", plan.packets[0])

    def test_no_governance_still_produces_plan(self) -> None:
        runtime = _make_runtime(governance=False)
        plan = runtime.plan_production("Build X", target="substrate")
        self.assertEqual(plan.risk_summary["governance_health"], "unknown")

    def test_no_tradeoff_reports_unavailable(self) -> None:
        runtime = _make_runtime(tradeoff=False)
        plan = runtime.plan_production("Build X", target="substrate")
        self.assertFalse(plan.tradeoff_analysis["available"])

    def test_no_trajectory_still_produces_summary(self) -> None:
        runtime = _make_runtime(trajectory=False)
        summary = runtime.summary()
        self.assertFalse(summary["trajectory_context"]["available"])


class TestQueryMethods(unittest.TestCase):
    """Test plan query and lookup methods."""

    def setUp(self) -> None:
        self.runtime = _make_runtime()
        self.plan1 = self.runtime.plan_production("Build A", target="substrate")
        self.plan2 = self.runtime.plan_production("Fix B", target="projection")
        self.plan3 = self.runtime.plan_production("Build C", target="substrate")

    def test_recent_plans_ordered_newest_first(self) -> None:
        recent = self.runtime.recent_plans()
        self.assertEqual(len(recent), 3)
        self.assertGreaterEqual(recent[0]["generated_at"], recent[1]["generated_at"])

    def test_recent_plans_respects_limit(self) -> None:
        recent = self.runtime.recent_plans(limit=2)
        self.assertEqual(len(recent), 2)

    def test_plan_by_id(self) -> None:
        found = self.runtime.plan_by_id(self.plan1.plan_id)
        self.assertIsNotNone(found)
        self.assertEqual(found.goal, "Build A")

    def test_plan_by_id_not_found(self) -> None:
        self.assertIsNone(self.runtime.plan_by_id("nonexistent"))

    def test_plans_by_target(self) -> None:
        substrate_plans = self.runtime.plans_by_target("substrate")
        self.assertEqual(len(substrate_plans), 2)

    def test_all_production_types(self) -> None:
        types = self.runtime.all_production_types()
        self.assertIn("feature", types)
        self.assertIn("fix", types)
        self.assertIn("full_product", types)

    def test_all_disciplines(self) -> None:
        disciplines = self.runtime.all_disciplines()
        self.assertEqual(len(disciplines), len(ProductionDiscipline))

    def test_template_summary(self) -> None:
        summary = self.runtime.template_summary()
        self.assertIn("full_product", summary)
        self.assertIn("feature", summary)
        self.assertEqual(len(summary["full_product"]), 9)


class TestSummary(unittest.TestCase):
    """Test the summary method."""

    def test_empty_summary(self) -> None:
        runtime = _make_runtime()
        summary = runtime.summary()
        self.assertEqual(summary["total_plans"], 0)
        self.assertIn("available_types", summary)
        self.assertIn("available_disciplines", summary)

    def test_summary_with_plans(self) -> None:
        runtime = _make_runtime()
        runtime.plan_production("Fix bug", target="substrate")
        runtime.plan_production("Build feature", target="projection")
        summary = runtime.summary()
        self.assertEqual(summary["total_plans"], 2)
        self.assertIn("fix", summary["plans_by_type"])
        self.assertIn("substrate", summary["plans_by_target"])
        self.assertIn("projection", summary["plans_by_target"])

    def test_summary_trajectory_context(self) -> None:
        runtime = _make_runtime(trajectory=True)
        summary = runtime.summary()
        self.assertTrue(summary["trajectory_context"]["available"])
        self.assertEqual(summary["trajectory_context"]["work_velocity_status"], "stable")


class TestTradeoffPreview(unittest.TestCase):
    """Test tradeoff integration."""

    def test_tradeoff_with_engine(self) -> None:
        runtime = _make_runtime(tradeoff=True)
        preview = runtime.tradeoff_preview("Build X")
        self.assertTrue(preview["available"])
        self.assertEqual(preview["overall_severity"], "negligible")

    def test_tradeoff_without_engine(self) -> None:
        runtime = _make_runtime(tradeoff=False)
        preview = runtime.tradeoff_preview("Build X")
        self.assertFalse(preview["available"])


class TestTargetAgnostic(unittest.TestCase):
    """Test that the same pipeline works for all target types."""

    def setUp(self) -> None:
        self.runtime = _make_runtime()

    def test_substrate_target(self) -> None:
        plan = self.runtime.plan_production("Build feature", target="substrate")
        self.assertEqual(plan.target, "substrate")

    def test_projection_target(self) -> None:
        plan = self.runtime.plan_production("Build feature", target="projection")
        self.assertEqual(plan.target, "projection")

    def test_client_product_target(self) -> None:
        plan = self.runtime.plan_production("Build feature", target="client_product")
        self.assertEqual(plan.target, "client_product")

    def test_same_structure_different_targets(self) -> None:
        plan_sub = self.runtime.plan_production("Build user auth", target="substrate")
        plan_proj = self.runtime.plan_production("Build user auth", target="projection")
        self.assertEqual(plan_sub.production_type, plan_proj.production_type)
        self.assertEqual(plan_sub.disciplines_covered, plan_proj.disciplines_covered)
        self.assertNotEqual(plan_sub.plan_id, plan_proj.plan_id)


class TestProductionPlanDataclass(unittest.TestCase):
    """Test ProductionPlan serialization."""

    def test_to_dict(self) -> None:
        plan = ProductionPlan(
            plan_id="pp-test",
            goal="Build X",
            target="substrate",
            production_type="feature",
            packets=[{"discipline": "architecture"}],
            dependency_order=["architecture"],
            disciplines_covered=["architecture"],
            generated_at=time.time(),
        )
        d = plan.to_dict()
        self.assertEqual(d["plan_id"], "pp-test")
        self.assertEqual(d["goal"], "Build X")
        self.assertIsInstance(d["packets"], list)


class TestDisciplinePacketDataclass(unittest.TestCase):
    """Test DisciplinePacket serialization."""

    def test_to_dict(self) -> None:
        pkt = DisciplinePacket(
            discipline="testing",
            label="Tests",
            description="Write tests",
            depends_on=["implementation"],
            risk_class="low",
            estimated_effort="medium",
        )
        d = pkt.to_dict()
        self.assertEqual(d["discipline"], "testing")
        self.assertEqual(d["depends_on"], ["implementation"])


if __name__ == "__main__":
    unittest.main()
