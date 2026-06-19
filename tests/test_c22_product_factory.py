"""Tests for C22.5 — Product Factory Runtime.

Self-contained fakes — no conftest, no external dependencies.
"""
from __future__ import annotations

import sys
import time

import os as _os

_repo = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))
sys.path.insert(0, _repo)
sys.path.insert(0, "/opt/OS")

import unittest
from dataclasses import dataclass, field
from typing import Any

from substrate.organism.product_factory_runtime import (
    ProductFactoryRuntime,
    ProductFactorySnapshot,
    ProductGoal,
    ProductGoalType,
    ProductPlan,
    ProductReadiness,
    _build_dependency_order,
    _classify_goal_risk,
    _classify_goal_type,
    _estimate_complexity,
    _estimate_roles,
)


# ── Fakes ────────────────────────────────────────────────────────────


@dataclass
class FakeIntegrationGap:
    gap_id: str = "gap-1"
    severity: str = "medium"
    description: str = "missing registration"

    def to_dict(self) -> dict[str, Any]:
        return {"gap_id": self.gap_id, "severity": self.severity, "description": self.description}


@dataclass
class FakeBuildReadiness:
    projection_id: str = ""
    readiness_score: float = 0.7
    missing_requirements: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "projection_id": self.projection_id,
            "readiness_score": self.readiness_score,
            "missing_requirements": self.missing_requirements,
        }


class FakeProjectionIntegrationRuntime:
    def integration_gaps(self, projection_id: str) -> list[FakeIntegrationGap]:
        return [FakeIntegrationGap(gap_id="gap-1", severity="medium")]

    def build_readiness(self, projection_id: str) -> FakeBuildReadiness:
        return FakeBuildReadiness(projection_id=projection_id, readiness_score=0.7)


class FakeProductionPlan:
    def __init__(self, goal: str = "", target: str = "") -> None:
        self.goal = goal
        self.target = target
        self.packets = [{"packet_id": "pkt-fake", "title": goal, "status": "planned"}]

    def to_dict(self) -> dict[str, Any]:
        return {
            "goal": self.goal,
            "target": self.target,
            "packets": self.packets,
        }


class FakeProductionPlanningRuntime:
    def __init__(self) -> None:
        self._calls: list[dict[str, Any]] = []

    def plan_production(
        self,
        goal: str = "",
        target: str = "",
        constraints: dict[str, Any] | None = None,
    ) -> FakeProductionPlan:
        self._calls.append({"goal": goal, "target": target, "constraints": constraints})
        return FakeProductionPlan(goal=goal, target=target)


class FakeGovernanceHealth:
    value = "coherent"


class FakeGovernanceRuntime:
    def health(self) -> FakeGovernanceHealth:
        return FakeGovernanceHealth()


@dataclass
class FakeTradeoffAnalysis:
    analysis_id: str = "ta-1"
    severity: str = "negligible"
    recommendation: str = "proceed"

    def to_dict(self) -> dict[str, Any]:
        return {
            "analysis_id": self.analysis_id,
            "severity": self.severity,
            "recommendation": self.recommendation,
            "available": True,
        }


class FakeTradeoffEngine:
    def analyze(self, target_id: str) -> FakeTradeoffAnalysis:
        return FakeTradeoffAnalysis(analysis_id=f"ta-{target_id}")


# ── Helper Functions Tests ───────────────────────────────────────────


class TestGoalTypeClassification(unittest.TestCase):
    def test_infrastructure_keywords(self) -> None:
        self.assertEqual(_classify_goal_type("Set up Docker infrastructure"), "infrastructure")
        self.assertEqual(_classify_goal_type("Configure CI/CD pipeline"), "infrastructure")

    def test_feature_keywords(self) -> None:
        self.assertEqual(_classify_goal_type("Build user dashboard"), "feature")
        self.assertEqual(_classify_goal_type("Add new component"), "feature")

    def test_migration_keywords(self) -> None:
        self.assertEqual(_classify_goal_type("Migrate to new schema"), "migration")
        self.assertEqual(_classify_goal_type("Data migration plan"), "migration")

    def test_integration_keywords(self) -> None:
        self.assertEqual(_classify_goal_type("Integrate Stripe API"), "integration")
        self.assertEqual(_classify_goal_type("Connect webhook adapter"), "integration")

    def test_launch_keywords(self) -> None:
        self.assertEqual(_classify_goal_type("Launch to production"), "launch")
        self.assertEqual(_classify_goal_type("Public release v1"), "launch")

    def test_capability_keywords(self) -> None:
        self.assertEqual(_classify_goal_type("Enable capability"), "capability")
        self.assertEqual(_classify_goal_type("Build new subsystem framework"), "capability")

    def test_unknown_defaults_to_feature(self) -> None:
        self.assertEqual(_classify_goal_type("do something random"), "feature")


class TestGoalRiskClassification(unittest.TestCase):
    def test_high_risk_keywords(self) -> None:
        self.assertEqual(_classify_goal_risk("Database migration"), "high")
        self.assertEqual(_classify_goal_risk("Auth security update"), "high")

    def test_medium_risk_keywords(self) -> None:
        self.assertEqual(_classify_goal_risk("New API endpoint"), "medium")
        self.assertEqual(_classify_goal_risk("Deploy configuration"), "medium")

    def test_low_risk_default(self) -> None:
        self.assertEqual(_classify_goal_risk("Add component"), "low")
        self.assertEqual(_classify_goal_risk("Write readme"), "low")


class TestComplexityEstimation(unittest.TestCase):
    def test_empty_goals_trivial(self) -> None:
        self.assertEqual(_estimate_complexity([]), "trivial")

    def test_few_simple_goals_low(self) -> None:
        goals = [
            ProductGoal(title="A", goal_type="feature", risk_class="low"),
            ProductGoal(title="B", goal_type="feature", risk_class="low"),
        ]
        self.assertEqual(_estimate_complexity(goals), "low")

    def test_infra_goals_medium(self) -> None:
        goals = [
            ProductGoal(title="A", goal_type="infrastructure", risk_class="low"),
            ProductGoal(title="B", goal_type="feature", risk_class="low"),
        ]
        self.assertEqual(_estimate_complexity(goals), "medium")

    def test_many_goals_high(self) -> None:
        goals = [
            ProductGoal(title=f"G{i}", goal_type="feature", risk_class="low")
            for i in range(8)
        ]
        self.assertEqual(_estimate_complexity(goals), "high")

    def test_high_risk_goals_medium(self) -> None:
        goals = [
            ProductGoal(title="A", goal_type="feature", risk_class="high"),
        ]
        self.assertEqual(_estimate_complexity(goals), "medium")

    def test_multiple_high_risk_goals_high(self) -> None:
        goals = [
            ProductGoal(title=f"G{i}", goal_type="feature", risk_class="high")
            for i in range(3)
        ]
        self.assertEqual(_estimate_complexity(goals), "high")


class TestDependencyOrder(unittest.TestCase):
    def test_no_deps(self) -> None:
        goals = [
            ProductGoal(goal_id="a", title="A"),
            ProductGoal(goal_id="b", title="B"),
        ]
        order = _build_dependency_order(goals)
        self.assertEqual(len(order), 2)
        self.assertIn("a", order)
        self.assertIn("b", order)

    def test_simple_chain(self) -> None:
        goals = [
            ProductGoal(goal_id="b", title="B", dependencies=["a"]),
            ProductGoal(goal_id="a", title="A"),
        ]
        order = _build_dependency_order(goals)
        self.assertLess(order.index("a"), order.index("b"))

    def test_circular_deps_resolved(self) -> None:
        goals = [
            ProductGoal(goal_id="a", title="A", dependencies=["b"]),
            ProductGoal(goal_id="b", title="B", dependencies=["a"]),
        ]
        order = _build_dependency_order(goals)
        self.assertEqual(len(order), 2)


class TestRoleEstimation(unittest.TestCase):
    def test_feature_goals(self) -> None:
        goals = [ProductGoal(goal_type="feature")]
        roles = _estimate_roles(goals)
        self.assertIn("contributor", roles)
        self.assertIn("reviewer", roles)

    def test_infra_goals(self) -> None:
        goals = [ProductGoal(goal_type="infrastructure")]
        roles = _estimate_roles(goals)
        self.assertIn("architect", roles)
        self.assertIn("lead", roles)

    def test_many_goals_add_director(self) -> None:
        goals = [ProductGoal(goal_type="feature") for _ in range(5)]
        roles = _estimate_roles(goals)
        self.assertIn("director", roles)


# ── Runtime Tests ────────────────────────────────────────────────────


class TestProductFactoryBasic(unittest.TestCase):
    def setUp(self) -> None:
        self.factory = ProductFactoryRuntime(
            projection_integration=FakeProjectionIntegrationRuntime(),
            production_planning=FakeProductionPlanningRuntime(),
            governance_runtime=FakeGovernanceRuntime(),
            tradeoff_engine=FakeTradeoffEngine(),
        )

    def test_generate_plan_basic(self) -> None:
        plan = self.factory.generate_product_plan(
            "prod-1",
            {
                "name": "Test Product",
                "target_type": "internal_tool",
                "goals": [
                    {"title": "Build CLI", "description": "Command-line tool"},
                    {"title": "Add tests", "description": "Unit tests"},
                ],
            },
        )
        self.assertIsInstance(plan, ProductPlan)
        self.assertEqual(plan.product_id, "prod-1")
        self.assertEqual(plan.product_name, "Test Product")
        self.assertEqual(plan.target_type, "internal_tool")
        self.assertEqual(len(plan.goals), 2)
        self.assertTrue(len(plan.production_packets) > 0)
        self.assertTrue(len(plan.capability_requirements) > 0)

    def test_generate_plan_no_goals_creates_default(self) -> None:
        plan = self.factory.generate_product_plan(
            "prod-2",
            {"name": "Auto Goal Product", "target_type": "website"},
        )
        self.assertEqual(len(plan.goals), 1)
        self.assertIn("Build Auto Goal Product", plan.goals[0]["title"])

    def test_product_registered_after_plan(self) -> None:
        self.factory.generate_product_plan(
            "prod-3",
            {"name": "P3", "target_type": "automation", "goals": [{"title": "Script"}]},
        )
        products = self.factory.list_products()
        self.assertEqual(len(products), 1)
        self.assertEqual(products[0]["product_id"], "prod-3")
        self.assertEqual(products[0]["target_type"], "automation")


class TestTargetAgnostic(unittest.TestCase):
    """Verify same pipeline for ALL target types."""

    def setUp(self) -> None:
        self.factory = ProductFactoryRuntime(
            production_planning=FakeProductionPlanningRuntime(),
            governance_runtime=FakeGovernanceRuntime(),
            tradeoff_engine=FakeTradeoffEngine(),
            projection_integration=FakeProjectionIntegrationRuntime(),
        )

    def _make_plan(self, target: str) -> ProductPlan:
        return self.factory.generate_product_plan(
            f"test-{target}",
            {
                "name": f"Test {target}",
                "target_type": target,
                "goals": [
                    {"title": "Build core", "description": "Core functionality"},
                    {"title": "Add tests", "description": "Test suite"},
                ],
            },
        )

    def test_substrate_plan(self) -> None:
        plan = self._make_plan("substrate")
        self.assertEqual(plan.target_type, "substrate")
        self.assertTrue(len(plan.production_packets) > 0)

    def test_projection_plan(self) -> None:
        plan = self._make_plan("projection")
        self.assertEqual(plan.target_type, "projection")
        self.assertTrue(len(plan.production_packets) > 0)

    def test_client_product_plan(self) -> None:
        plan = self._make_plan("client_product")
        self.assertEqual(plan.target_type, "client_product")
        self.assertTrue(len(plan.production_packets) > 0)

    def test_internal_tool_plan(self) -> None:
        plan = self._make_plan("internal_tool")
        self.assertEqual(plan.target_type, "internal_tool")
        self.assertTrue(len(plan.production_packets) > 0)

    def test_website_plan(self) -> None:
        plan = self._make_plan("website")
        self.assertEqual(plan.target_type, "website")
        self.assertTrue(len(plan.production_packets) > 0)

    def test_automation_plan(self) -> None:
        plan = self._make_plan("automation")
        self.assertEqual(plan.target_type, "automation")
        self.assertTrue(len(plan.production_packets) > 0)

    def test_all_targets_produce_goals_and_packets(self) -> None:
        """Self-build and projection-build are the same capability."""
        for target in ["substrate", "projection", "client_product", "internal_tool", "website", "automation"]:
            plan = self._make_plan(target)
            self.assertTrue(len(plan.goals) > 0, f"{target} should have goals")
            self.assertTrue(len(plan.production_packets) > 0, f"{target} should have packets")

    def test_pipeline_structure_identical(self) -> None:
        """All targets produce plans with the same structure."""
        plans = [self._make_plan(t) for t in self.factory.all_target_types()]
        for plan in plans:
            self.assertTrue(hasattr(plan, "goals"))
            self.assertTrue(hasattr(plan, "production_packets"))
            self.assertTrue(hasattr(plan, "capability_requirements"))
            self.assertTrue(hasattr(plan, "gap_analysis"))
            self.assertTrue(hasattr(plan, "estimated_complexity"))
            self.assertTrue(hasattr(plan, "estimated_roles"))


class TestProjectionGapAnalysis(unittest.TestCase):
    def test_projection_delegates_gap_analysis(self) -> None:
        fake_proj = FakeProjectionIntegrationRuntime()
        factory = ProductFactoryRuntime(
            projection_integration=fake_proj,
            production_planning=FakeProductionPlanningRuntime(),
        )
        plan = factory.generate_product_plan(
            "eos-proj",
            {
                "name": "EOS Dashboard",
                "target_type": "projection",
                "goals": [{"title": "Build dashboard"}],
            },
        )
        gap = plan.gap_analysis
        self.assertTrue(gap.get("available"))
        self.assertIn("gaps", gap)
        self.assertIn("readiness", gap)

    def test_non_projection_uses_generic_gap(self) -> None:
        factory = ProductFactoryRuntime(
            production_planning=FakeProductionPlanningRuntime(),
        )
        plan = factory.generate_product_plan(
            "tool-1",
            {
                "name": "Internal Tool",
                "target_type": "internal_tool",
                "goals": [{"title": "Build tool"}],
            },
        )
        gap = plan.gap_analysis
        self.assertTrue(gap.get("available"))
        self.assertIn("required_capabilities", gap)

    def test_missing_projection_runtime_degrades(self) -> None:
        class FailingProjectionRuntime:
            def integration_gaps(self, pid: str) -> list[Any]:
                raise RuntimeError("no projection data")
            def build_readiness(self, pid: str) -> None:
                raise RuntimeError("no projection data")

        factory = ProductFactoryRuntime(
            production_planning=FakeProductionPlanningRuntime(),
            projection_integration=FailingProjectionRuntime(),
        )
        plan = factory.generate_product_plan(
            "no-proj",
            {
                "name": "Projection No Runtime",
                "target_type": "projection",
                "goals": [{"title": "Build"}],
            },
        )
        gap = plan.gap_analysis
        self.assertFalse(gap.get("available"))


class TestProductReadiness(unittest.TestCase):
    def setUp(self) -> None:
        self.factory = ProductFactoryRuntime(
            production_planning=FakeProductionPlanningRuntime(),
            governance_runtime=FakeGovernanceRuntime(),
        )

    def test_readiness_with_plan(self) -> None:
        self.factory.generate_product_plan(
            "ready-1",
            {"name": "R1", "target_type": "automation", "goals": [{"title": "Automate"}]},
        )
        readiness = self.factory.product_readiness("ready-1")
        self.assertIn(readiness["readiness"], ["ready", "partial"])

    def test_readiness_unknown_product(self) -> None:
        readiness = self.factory.product_readiness("nonexistent")
        self.assertEqual(readiness["readiness"], "not_started")


class TestProductFactoryFiltering(unittest.TestCase):
    def setUp(self) -> None:
        self.factory = ProductFactoryRuntime(
            production_planning=FakeProductionPlanningRuntime(),
        )
        self.factory.generate_product_plan(
            "s1", {"name": "S1", "target_type": "substrate", "goals": [{"title": "Build"}]},
        )
        self.factory.generate_product_plan(
            "p1", {"name": "P1", "target_type": "projection", "goals": [{"title": "Build"}]},
        )
        self.factory.generate_product_plan(
            "p2", {"name": "P2", "target_type": "projection", "goals": [{"title": "Build"}]},
        )

    def test_by_target_type(self) -> None:
        projections = self.factory.by_target_type("projection")
        self.assertEqual(len(projections), 2)
        substrates = self.factory.by_target_type("substrate")
        self.assertEqual(len(substrates), 1)

    def test_by_target_type_empty(self) -> None:
        websites = self.factory.by_target_type("website")
        self.assertEqual(len(websites), 0)

    def test_list_products(self) -> None:
        products = self.factory.list_products()
        self.assertEqual(len(products), 3)

    def test_product_by_id(self) -> None:
        entry = self.factory.product_by_id("s1")
        self.assertIsNotNone(entry)
        self.assertEqual(entry.product_name, "S1")

    def test_product_by_id_missing(self) -> None:
        entry = self.factory.product_by_id("nonexistent")
        self.assertIsNone(entry)


class TestGoalTree(unittest.TestCase):
    def test_goal_tree_retrieval(self) -> None:
        factory = ProductFactoryRuntime(
            production_planning=FakeProductionPlanningRuntime(),
        )
        factory.generate_product_plan(
            "tree-1",
            {
                "name": "Tree",
                "target_type": "feature",
                "goals": [
                    {"title": "Foundation", "description": "Base"},
                    {"title": "Feature A", "description": "On top"},
                ],
            },
        )
        tree = factory.goal_tree("tree-1")
        self.assertEqual(len(tree), 2)

    def test_goal_tree_empty_product(self) -> None:
        factory = ProductFactoryRuntime()
        tree = factory.goal_tree("nonexistent")
        self.assertEqual(tree, [])


class TestCapabilityRequirements(unittest.TestCase):
    def test_substrate_capabilities(self) -> None:
        factory = ProductFactoryRuntime(
            production_planning=FakeProductionPlanningRuntime(),
        )
        factory.generate_product_plan(
            "cap-1",
            {"name": "C1", "target_type": "substrate", "goals": [{"title": "Build"}]},
        )
        caps = factory.capability_requirements("cap-1")
        self.assertIn("python_runtime", caps)
        self.assertIn("test_suite", caps)

    def test_website_capabilities(self) -> None:
        factory = ProductFactoryRuntime(
            production_planning=FakeProductionPlanningRuntime(),
        )
        factory.generate_product_plan(
            "cap-2",
            {"name": "C2", "target_type": "website", "goals": [{"title": "Build"}]},
        )
        caps = factory.capability_requirements("cap-2")
        self.assertIn("html_css", caps)
        self.assertIn("static_hosting", caps)

    def test_missing_product_returns_default(self) -> None:
        factory = ProductFactoryRuntime()
        caps = factory.capability_requirements("nonexistent")
        self.assertIsInstance(caps, list)


class TestSnapshot(unittest.TestCase):
    def test_snapshot_empty(self) -> None:
        factory = ProductFactoryRuntime()
        snap = factory.snapshot()
        self.assertEqual(snap.total_products, 0)
        self.assertEqual(snap.total_goals, 0)
        self.assertEqual(snap.total_packets, 0)

    def test_snapshot_with_products(self) -> None:
        factory = ProductFactoryRuntime(
            production_planning=FakeProductionPlanningRuntime(),
        )
        factory.generate_product_plan(
            "snap-1",
            {"name": "S1", "target_type": "substrate", "goals": [{"title": "Build"}]},
        )
        factory.generate_product_plan(
            "snap-2",
            {"name": "S2", "target_type": "projection", "goals": [{"title": "Build"}]},
        )
        snap = factory.snapshot()
        self.assertEqual(snap.total_products, 2)
        self.assertEqual(snap.by_target_type.get("substrate"), 1)
        self.assertEqual(snap.by_target_type.get("projection"), 1)
        self.assertTrue(snap.total_goals > 0)
        self.assertTrue(snap.total_packets > 0)

    def test_snapshot_to_dict(self) -> None:
        factory = ProductFactoryRuntime()
        snap = factory.snapshot()
        d = snap.to_dict()
        self.assertIn("total_products", d)
        self.assertIn("by_target_type", d)


class TestSummary(unittest.TestCase):
    def test_summary_keys(self) -> None:
        factory = ProductFactoryRuntime()
        s = factory.summary()
        self.assertIn("total_products", s)
        self.assertIn("by_target_type", s)
        self.assertIn("by_readiness", s)
        self.assertIn("total_goals", s)
        self.assertIn("total_packets", s)
        self.assertIn("generated_at", s)


class TestAllTargetTypes(unittest.TestCase):
    def test_returns_all_six(self) -> None:
        factory = ProductFactoryRuntime()
        types = factory.all_target_types()
        self.assertEqual(len(types), 6)
        self.assertIn("substrate", types)
        self.assertIn("projection", types)
        self.assertIn("client_product", types)
        self.assertIn("internal_tool", types)
        self.assertIn("website", types)
        self.assertIn("automation", types)


class TestGracefulDegradation(unittest.TestCase):
    def test_no_subsystems(self) -> None:
        factory = ProductFactoryRuntime()
        plan = factory.generate_product_plan(
            "degrade-1",
            {"name": "D1", "target_type": "internal_tool", "goals": [{"title": "Build tool"}]},
        )
        self.assertIsInstance(plan, ProductPlan)
        self.assertEqual(len(plan.goals), 1)
        self.assertTrue(len(plan.production_packets) > 0)

    def test_planning_failure_creates_fallback_packet(self) -> None:
        class FailingPlanner:
            def plan_production(self, **kwargs: Any) -> None:
                raise RuntimeError("planning failed")

        factory = ProductFactoryRuntime(production_planning=FailingPlanner())
        plan = factory.generate_product_plan(
            "fail-1",
            {"name": "F1", "target_type": "automation", "goals": [{"title": "Automate"}]},
        )
        self.assertTrue(len(plan.production_packets) > 0)
        self.assertEqual(plan.production_packets[0]["status"], "planned")

    def test_governance_failure_degrades(self) -> None:
        class FailingGov:
            def health(self) -> None:
                raise RuntimeError("gov failed")

        factory = ProductFactoryRuntime(
            production_planning=FakeProductionPlanningRuntime(),
            governance_runtime=FailingGov(),
        )
        plan = factory.generate_product_plan(
            "gov-fail-1",
            {"name": "GF1", "target_type": "feature", "goals": [{"title": "Build"}]},
        )
        self.assertIsInstance(plan, ProductPlan)
        gov = plan.gap_analysis.get("governance", {})
        self.assertFalse(gov.get("available", True))


class TestGovernanceAndTradeoffIntegration(unittest.TestCase):
    def test_governance_included_in_gap_analysis(self) -> None:
        factory = ProductFactoryRuntime(
            production_planning=FakeProductionPlanningRuntime(),
            governance_runtime=FakeGovernanceRuntime(),
        )
        plan = factory.generate_product_plan(
            "gov-1",
            {"name": "G1", "target_type": "feature", "goals": [{"title": "Build"}]},
        )
        gov = plan.gap_analysis.get("governance", {})
        self.assertTrue(gov.get("available"))
        self.assertEqual(gov.get("governance_health"), "coherent")

    def test_tradeoff_included_in_gap_analysis(self) -> None:
        factory = ProductFactoryRuntime(
            production_planning=FakeProductionPlanningRuntime(),
            tradeoff_engine=FakeTradeoffEngine(),
        )
        plan = factory.generate_product_plan(
            "trade-1",
            {"name": "T1", "target_type": "feature", "goals": [{"title": "Build"}]},
        )
        tradeoff = plan.gap_analysis.get("tradeoff", {})
        self.assertTrue(tradeoff.get("available"))


class TestProductGoalDataclass(unittest.TestCase):
    def test_auto_id(self) -> None:
        g = ProductGoal(title="Test")
        self.assertTrue(g.goal_id.startswith("goal-"))

    def test_to_dict(self) -> None:
        g = ProductGoal(goal_id="g-1", product_id="p-1", title="T", goal_type="feature")
        d = g.to_dict()
        self.assertEqual(d["goal_id"], "g-1")
        self.assertEqual(d["product_id"], "p-1")
        self.assertEqual(d["goal_type"], "feature")


class TestProductPlanDataclass(unittest.TestCase):
    def test_auto_timestamp(self) -> None:
        p = ProductPlan(product_id="p-1")
        self.assertTrue(p.generated_at > 0)

    def test_to_dict(self) -> None:
        p = ProductPlan(product_id="p-1", product_name="N", target_type="substrate")
        d = p.to_dict()
        self.assertEqual(d["product_id"], "p-1")
        self.assertEqual(d["target_type"], "substrate")


if __name__ == "__main__":
    unittest.main()
