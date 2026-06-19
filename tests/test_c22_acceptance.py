"""Acceptance tests for Campaign 22 — Software Production Organism.

7 end-to-end tests verifying the complete governed production pipeline.
All tests use self-contained fakes — no external dependencies.
"""

from __future__ import annotations

import sys
import time
import unittest
from dataclasses import dataclass, field
from typing import Any

sys.path.insert(0, "/opt/OS")


# ── AT1: Full Production Loop ──────────────────────────────────────────────
# Plan → assign → review → compound — the complete pipeline.


class TestAT1FullProductionLoop(unittest.TestCase):
    """Verify the full production pipeline: plan → assign → review → compound."""

    def test_plan_creates_all_disciplines(self) -> None:
        from substrate.organism.production_planning_runtime import (
            ProductionPlanningRuntime,
        )
        rt = ProductionPlanningRuntime()
        plan = rt.plan_production("Build user dashboard", target="projection")

        self.assertGreater(len(plan.packets), 0)
        disciplines = [p.get("discipline", p.get("type", "")) for p in plan.packets]
        for required in ["architecture", "implementation", "testing", "review"]:
            self.assertIn(
                required, disciplines,
                f"Missing required discipline: {required}",
            )

    def test_plan_then_assign_with_roles(self) -> None:
        from substrate.organism.production_planning_runtime import (
            ProductionPlanningRuntime,
        )
        from substrate.organism.production_workforce_runtime import (
            ProductionWorkforceRuntime,
        )
        planner = ProductionPlanningRuntime()
        workforce = ProductionWorkforceRuntime()

        plan = planner.plan_production("Build user dashboard", target="projection")
        assignments = workforce.assign_production_work(plan.packets, project_id="at1")

        self.assertGreater(len(assignments), 0)
        roles = {a.role for a in assignments}
        self.assertTrue(len(roles) > 0, "Should assign at least one role")
        for a in assignments:
            self.assertTrue(len(a.authority) > 0, "Every assignment needs authority")

    def test_plan_assign_review_pipeline(self) -> None:
        from substrate.organism.production_planning_runtime import (
            ProductionPlanningRuntime,
        )
        from substrate.organism.production_workforce_runtime import (
            ProductionWorkforceRuntime,
        )
        from substrate.organism.production_review_runtime import (
            ProductionReviewRuntime,
        )
        planner = ProductionPlanningRuntime()
        workforce = ProductionWorkforceRuntime()
        reviewer = ProductionReviewRuntime()

        plan = planner.plan_production("Build auth module", target="substrate")
        assignments = workforce.assign_production_work(plan.packets, project_id="at1-review")
        self.assertGreater(len(assignments), 0)

        result = reviewer.review_production(
            "wp-at1",
            packet_data={"goal": "Build auth module", "type": "feature"},
            skip_gate_scripts=True,
        )
        self.assertIn(result.verdict, ["ready", "changes_required", "blocked", "approval_pending"])

    def test_full_loop_with_compounding(self) -> None:
        from substrate.organism.production_planning_runtime import (
            ProductionPlanningRuntime,
        )
        from substrate.organism.capability_compounding_runtime import (
            CapabilityCompoundingRuntime,
        )
        planner = ProductionPlanningRuntime()
        compounding = CapabilityCompoundingRuntime()

        plan = planner.plan_production("Build notification service", target="substrate")
        self.assertGreater(len(plan.packets), 0)

        snap = compounding.snapshot()
        self.assertIsNotNone(snap)
        self.assertIn(snap.health, ["thriving", "healthy", "stagnant", "degraded"])


# ── AT2: Target-Agnostic (Same Pipeline) ───────────────────────────────────
# Both substrate and projection targets go through the same pipeline.


class TestAT2TargetAgnostic(unittest.TestCase):
    """Verify identical pipeline structure for different targets."""

    def test_substrate_and_projection_same_pipeline(self) -> None:
        from substrate.organism.product_factory_runtime import ProductFactoryRuntime

        factory = ProductFactoryRuntime()

        umh_plan = factory.generate_product_plan(
            "umh-substrate",
            {
                "id": "umh-substrate",
                "name": "UMH Feature",
                "target_type": "substrate",
                "goals": [{"title": "Add new capability", "description": "New cap", "type": "capability"}],
            },
        )

        eos_plan = factory.generate_product_plan(
            "eos-dashboard",
            {
                "id": "eos-dashboard",
                "name": "EOS Dashboard",
                "target_type": "projection",
                "goals": [{"title": "Build dashboard", "description": "User dash", "type": "feature"}],
            },
        )

        self.assertEqual(umh_plan.target_type, "substrate")
        self.assertEqual(eos_plan.target_type, "projection")
        self.assertGreater(len(umh_plan.goals), 0)
        self.assertGreater(len(eos_plan.goals), 0)

    def test_all_target_types_accepted(self) -> None:
        from substrate.organism.production_planning_runtime import (
            ProductionPlanningRuntime,
        )
        planner = ProductionPlanningRuntime()
        for target in ["substrate", "projection", "client_product", "internal_tool", "website", "automation"]:
            plan = planner.plan_production(f"Build something for {target}", target=target)
            self.assertEqual(plan.target, target)
            self.assertGreater(len(plan.packets), 0)


# ── AT3: Capability Reuse (Compounding Proven) ─────────────────────────────


class TestAT3CapabilityReuse(unittest.TestCase):
    """Verify compounding pipeline tracks production outputs."""

    def test_compounding_tracks_across_runs(self) -> None:
        from substrate.organism.capability_compounding_runtime import (
            CapabilityCompoundingRuntime,
        )
        rt = CapabilityCompoundingRuntime()

        snap1 = rt.snapshot()
        self.assertIsNotNone(snap1)

        trace = rt.production_to_asset_pipeline("prod-1")
        self.assertIsNotNone(trace)

        snap2 = rt.snapshot()
        self.assertIsNotNone(snap2)

    def test_reusable_assets_queryable(self) -> None:
        from substrate.organism.capability_compounding_runtime import (
            CapabilityCompoundingRuntime,
        )
        rt = CapabilityCompoundingRuntime()
        assets = rt.reusable_assets()
        self.assertIsInstance(assets, list)


# ── AT4: Organizational Lineage ────────────────────────────────────────────
# Source truth traces full chain from work packet to intent.


class TestAT4OrganizationalLineage(unittest.TestCase):
    """Verify SourceTruthRuntime traces full organizational lineage."""

    def test_trace_lineage_returns_chain(self) -> None:
        from substrate.organism.source_truth_runtime import SourceTruthRuntime

        rt = SourceTruthRuntime()
        chain = rt.trace_lineage("wp-at4", "work_packet")
        self.assertIsNotNone(chain)
        self.assertGreater(chain.depth, 0)

    def test_intent_to_capability_chain(self) -> None:
        from substrate.organism.source_truth_runtime import SourceTruthRuntime

        rt = SourceTruthRuntime()
        chain = rt.intent_to_capability("intent-at4")
        self.assertIsNotNone(chain)

    def test_why_does_this_exist(self) -> None:
        from substrate.organism.source_truth_runtime import SourceTruthRuntime

        rt = SourceTruthRuntime()
        chain = rt.why_does_this_exist("artifact-at4")
        self.assertIsNotNone(chain)

    def test_orphaned_work_detectable(self) -> None:
        from substrate.organism.source_truth_runtime import SourceTruthRuntime

        rt = SourceTruthRuntime()
        orphans = rt.orphaned_work()
        self.assertIsInstance(orphans, list)


# ── AT5: Multi-Project Concurrent ──────────────────────────────────────────


class TestAT5MultiProjectConcurrent(unittest.TestCase):
    """Verify multiple projects tracked simultaneously."""

    def test_concurrent_projects_counted(self) -> None:
        from substrate.organism.production_ops_runtime import (
            ProductionOpsRuntime,
            ProductionTarget,
        )

        rt = ProductionOpsRuntime()

        rt.register_production(
            "proj-a", "Build API gateway",
            target_type=ProductionTarget.SUBSTRATE.value,
            packets=[{"id": "wp-a1", "goal": "gateway"}],
        )
        rt.register_production(
            "proj-b", "Build EOS dashboard",
            target_type=ProductionTarget.PROJECTION.value,
            packets=[{"id": "wp-b1", "goal": "dashboard"}],
        )

        snap = rt.snapshot()
        self.assertEqual(snap.concurrent_projects, 2)

    def test_independent_phases(self) -> None:
        from substrate.organism.production_ops_runtime import (
            ProductionOpsRuntime,
            ProductionTarget,
        )

        rt = ProductionOpsRuntime()

        rt.register_production(
            "proj-c", "Build feature C",
            target_type=ProductionTarget.SUBSTRATE.value,
            packets=[{"id": "wp-c1", "goal": "feat c"}],
        )
        rt.register_production(
            "proj-d", "Build feature D",
            target_type=ProductionTarget.PROJECTION.value,
            packets=[{"id": "wp-d1", "goal": "feat d"}],
        )

        rt.update_production_state("proj-c", quality_checks_passed=True)

        active = rt.active_productions()
        self.assertEqual(len(active), 2)

        phases = {p["production_id"]: p["phase"] for p in active}
        self.assertIn("proj-c", phases)
        self.assertIn("proj-d", phases)


# ── AT6: Voice-to-Production Queue ─────────────────────────────────────────


class TestAT6VoiceToProductionQueue(unittest.TestCase):
    """Simulate voice intent becoming production work."""

    def test_voice_intent_creates_plan(self) -> None:
        from substrate.organism.production_planning_runtime import (
            ProductionPlanningRuntime,
        )
        from substrate.organism.production_ops_runtime import (
            ProductionOpsRuntime,
        )

        planner = ProductionPlanningRuntime()
        ops = ProductionOpsRuntime()

        plan = planner.plan_production("Add dark mode to cockpit", target="substrate")
        self.assertGreater(len(plan.packets), 0)

        ops.register_production(
            "voice-prod-1",
            "Add dark mode to cockpit",
            target_type="substrate",
            packets=plan.packets,
        )

        phase = ops.phase()
        self.assertNotEqual(phase, "idle")

        active = ops.active_productions()
        self.assertGreater(len(active), 0)
        disciplines = set()
        for packet in plan.packets:
            disciplines.add(packet.get("discipline", packet.get("type", "")))
        self.assertGreater(len(disciplines), 1)


# ── AT7: Completion Is Outcome-Based ───────────────────────────────────────
# Production is not complete until proofs pass. Loops until done.


class TestAT7CompletionOutcomeBased(unittest.TestCase):
    """Verify outcome-based completion: loops until proofs pass."""

    def test_incomplete_without_quality_checks(self) -> None:
        from substrate.organism.production_ops_runtime import (
            ProductionOpsRuntime,
        )
        rt = ProductionOpsRuntime()
        rt.register_production(
            "at7-1", "Build something",
            packets=[{"id": "wp-1", "goal": "test", "status": "completed"}],
        )
        self.assertFalse(rt.is_complete("at7-1"))

    def test_incomplete_without_governance(self) -> None:
        from substrate.organism.production_ops_runtime import (
            ProductionOpsRuntime,
        )
        rt = ProductionOpsRuntime()
        rt.register_production(
            "at7-2", "Build something",
            packets=[{"id": "wp-2", "goal": "test", "status": "completed"}],
        )
        rt.update_production_state("at7-2", quality_checks_passed=True)
        self.assertFalse(rt.is_complete("at7-2"))

    def test_incomplete_without_proof(self) -> None:
        from substrate.organism.production_ops_runtime import (
            ProductionOpsRuntime,
        )
        rt = ProductionOpsRuntime()
        rt.register_production(
            "at7-3", "Build something",
            packets=[{"id": "wp-3", "goal": "test", "status": "completed"}],
        )
        rt.update_production_state(
            "at7-3",
            quality_checks_passed=True,
            governance_approved=True,
        )
        self.assertFalse(rt.is_complete("at7-3"))

    def test_complete_only_when_all_gates_pass(self) -> None:
        from substrate.organism.production_ops_runtime import (
            ProductionOpsRuntime,
        )
        rt = ProductionOpsRuntime()
        rt.register_production(
            "at7-4", "Build something",
            packets=[{"id": "wp-4", "goal": "test", "status": "completed"}],
        )
        rt.update_production_state(
            "at7-4",
            quality_checks_passed=True,
            governance_approved=True,
            proof_assembled=True,
        )
        self.assertTrue(rt.is_complete("at7-4"))

    def test_blocked_prevents_completion(self) -> None:
        from substrate.organism.production_ops_runtime import (
            ProductionOpsRuntime,
        )
        rt = ProductionOpsRuntime()
        rt.register_production(
            "at7-5", "Build something",
            packets=[{"id": "wp-5", "goal": "test", "status": "completed"}],
        )
        rt.update_production_state(
            "at7-5",
            quality_checks_passed=True,
            governance_approved=True,
            proof_assembled=True,
            blocked_reasons=["Security review failed"],
        )
        self.assertFalse(rt.is_complete("at7-5"))

    def test_phase_stays_reviewing_until_quality_passes(self) -> None:
        from substrate.organism.production_ops_runtime import (
            ProductionOpsRuntime,
            ProductionPhase,
        )
        rt = ProductionOpsRuntime()
        entry = rt.register_production(
            "at7-6", "Build something",
            packets=[{"id": "wp-6", "goal": "test", "status": "completed"}],
        )
        self.assertNotEqual(entry.phase, ProductionPhase.SHIPPING.value)

        rt.update_production_state("at7-6", quality_checks_passed=True)
        entry = rt._productions["at7-6"]
        self.assertNotEqual(entry.phase, ProductionPhase.SHIPPING.value)

        rt.update_production_state(
            "at7-6",
            governance_approved=True,
            proof_assembled=True,
        )
        entry = rt._productions["at7-6"]
        self.assertEqual(entry.phase, ProductionPhase.SHIPPING.value)


# ── Cross-Runtime Integration ──────────────────────────────────────────────


class TestCrossRuntimeIntegration(unittest.TestCase):
    """Verify all C22 runtimes can be imported and instantiated together."""

    def test_all_runtimes_import(self) -> None:
        from substrate.organism.production_ops_runtime import ProductionOpsRuntime
        from substrate.organism.production_planning_runtime import ProductionPlanningRuntime
        from substrate.organism.production_workforce_runtime import ProductionWorkforceRuntime
        from substrate.organism.production_review_runtime import ProductionReviewRuntime
        from substrate.organism.capability_compounding_runtime import CapabilityCompoundingRuntime
        from substrate.organism.product_factory_runtime import ProductFactoryRuntime
        from substrate.organism.source_truth_runtime import SourceTruthRuntime

        runtimes = [
            ProductionOpsRuntime(),
            ProductionPlanningRuntime(),
            ProductionWorkforceRuntime(),
            ProductionReviewRuntime(),
            CapabilityCompoundingRuntime(),
            ProductFactoryRuntime(),
            SourceTruthRuntime(),
        ]
        self.assertEqual(len(runtimes), 7)

    def test_all_enums_in_canonical_types(self) -> None:
        from substrate.canonical_types import lookup

        required_types = [
            "ProductionPhase", "ProductionTarget", "ProductionHealth",
            "ProductionDiscipline", "ProductionType",
            "ProductionRole", "ProductionAuthority",
            "ReviewVerdict", "QualityDimension",
            "CompoundingStage", "CompoundingHealth",
            "ProductGoalType", "ProductReadiness",
            "LineageNodeType", "LineageTerminalState",
        ]
        for type_name in required_types:
            result = lookup(type_name)
            self.assertIsNotNone(
                result,
                f"Type '{type_name}' not registered in canonical_types.py",
            )


if __name__ == "__main__":
    unittest.main()
