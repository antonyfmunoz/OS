"""Tests for C22.0 — Production Operations Runtime.

Verifies: phase derivation, health classification, completion invariant,
multi-project support, target filtering, blocker extraction, snapshot
composition.
"""

from __future__ import annotations

import sys
import time
import unittest
from dataclasses import dataclass, field
from typing import Any
from unittest.mock import MagicMock

sys.path.insert(0, "/opt/OS")

from substrate.organism.production_ops_runtime import (
    ProductionEntry,
    ProductionHealth,
    ProductionOpsRuntime,
    ProductionPhase,
    ProductionSnapshot,
    ProductionTarget,
)


# ── Fakes ────────────────────────────────────────────────────────────────


class FakeIDEStatus:
    def __init__(
        self,
        active_streams: int = 0,
        pending_reviews: int = 0,
    ) -> None:
        self.active_streams = active_streams
        self.pending_reviews = pending_reviews


class FakeMetaIDE:
    def __init__(self, status: FakeIDEStatus | None = None) -> None:
        self._status = status or FakeIDEStatus()

    def ide_status(self) -> FakeIDEStatus:
        return self._status


class FakeExecutionState:
    def __init__(self, value: str = "idle") -> None:
        self.value = value


class FakeExecutionHealth:
    def __init__(self, value: str = "offline") -> None:
        self.value = value


class FakeAssessment:
    def __init__(self, pending_approval_count: int = 0) -> None:
        self.pending_approval_count = pending_approval_count


class FakeGovernedExecution:
    def __init__(
        self,
        state: str = "idle",
        health: str = "offline",
        blockers: list[dict[str, Any]] | None = None,
        pending_approvals: int = 0,
    ) -> None:
        self._state = state
        self._health = health
        self._blockers = blockers or []
        self._pending = pending_approvals

    def state(self) -> FakeExecutionState:
        return FakeExecutionState(self._state)

    def health(self) -> FakeExecutionHealth:
        return FakeExecutionHealth(self._health)

    def blockers(self) -> list[dict[str, Any]]:
        return self._blockers

    def assessment(self) -> FakeAssessment:
        return FakeAssessment(self._pending)


class FakeWorkforceHealth:
    def __init__(self, value: str = "idle") -> None:
        self.value = value


class FakeAgentWorkforce:
    def __init__(
        self,
        health: str = "idle",
        summary: dict[str, Any] | None = None,
    ) -> None:
        self._health = health
        self._summary = summary or {"total_agent_types": 0}

    def health(self) -> FakeWorkforceHealth:
        return FakeWorkforceHealth(self._health)

    def summary(self) -> dict[str, Any]:
        return dict(self._summary)


class FakeExecutionFabricSnapshot:
    def __init__(self, queue_depth: int = 0) -> None:
        self.queue_depth = queue_depth


class FakeExecutionFabric:
    def __init__(self, queue_depth: int = 0) -> None:
        self._queue_depth = queue_depth

    def snapshot(self) -> FakeExecutionFabricSnapshot:
        return FakeExecutionFabricSnapshot(self._queue_depth)


class FakeMetaIdeContext:
    def __init__(self, summary: dict[str, Any] | None = None) -> None:
        self._summary = summary or {"repo": "test-repo", "branch": "main"}

    def summary(self) -> dict[str, Any]:
        return dict(self._summary)


class FakeSessionMachine:
    def summary(self) -> dict[str, Any]:
        return {"total_sessions": 1}


# ── Tests ────────────────────────────────────────────────────────────────


class TestProductionPhaseEnum(unittest.TestCase):
    def test_all_phases_exist(self) -> None:
        phases = {p.value for p in ProductionPhase}
        expected = {
            "idle", "planning", "producing", "reviewing",
            "approval_pending", "shipping", "learning", "degraded",
        }
        self.assertEqual(phases, expected)


class TestProductionTargetEnum(unittest.TestCase):
    def test_all_targets_exist(self) -> None:
        targets = {t.value for t in ProductionTarget}
        expected = {
            "substrate", "projection", "client_product",
            "internal_tool", "website", "automation",
        }
        self.assertEqual(targets, expected)


class TestProductionEntry(unittest.TestCase):
    def test_to_dict_contains_all_fields(self) -> None:
        entry = ProductionEntry(
            production_id="p1",
            target_type="substrate",
            goal="Build feature",
        )
        d = entry.to_dict()
        self.assertIn("production_id", d)
        self.assertIn("target_type", d)
        self.assertIn("goal", d)
        self.assertIn("phase", d)
        self.assertIn("packet_count", d)
        self.assertIn("quality_checks_passed", d)
        self.assertIn("governance_approved", d)
        self.assertIn("proof_assembled", d)

    def test_default_phase_is_idle(self) -> None:
        entry = ProductionEntry()
        self.assertEqual(entry.phase, ProductionPhase.IDLE.value)


class TestProductionSnapshot(unittest.TestCase):
    def test_to_dict_roundtrip(self) -> None:
        snap = ProductionSnapshot(
            phase="idle",
            health="offline",
            concurrent_projects=2,
            per_project_phases={"p1": "producing", "p2": "reviewing"},
        )
        d = snap.to_dict()
        self.assertEqual(d["concurrent_projects"], 2)
        self.assertEqual(d["per_project_phases"]["p1"], "producing")


class TestRuntimeCreation(unittest.TestCase):
    def test_creates_with_no_args(self) -> None:
        rt = ProductionOpsRuntime()
        self.assertIsNotNone(rt)

    def test_creates_with_injected_deps(self) -> None:
        rt = ProductionOpsRuntime(
            meta_ide=FakeMetaIDE(),
            governed_execution=FakeGovernedExecution(),
            execution_fabric=FakeExecutionFabric(),
            agent_workforce=FakeAgentWorkforce(),
            session_machine=FakeSessionMachine(),
            meta_ide_context=FakeMetaIdeContext(),
        )
        self.assertIsNotNone(rt)


class TestPhaseDerived(unittest.TestCase):
    def test_idle_when_no_productions(self) -> None:
        rt = ProductionOpsRuntime(
            governed_execution=FakeGovernedExecution(),
        )
        self.assertEqual(rt.phase(), ProductionPhase.IDLE.value)

    def test_producing_from_meta_ide_active_streams(self) -> None:
        rt = ProductionOpsRuntime(
            meta_ide=FakeMetaIDE(FakeIDEStatus(active_streams=2)),
            governed_execution=FakeGovernedExecution(),
        )
        self.assertEqual(rt.phase(), ProductionPhase.PRODUCING.value)

    def test_reviewing_from_meta_ide_pending_reviews(self) -> None:
        rt = ProductionOpsRuntime(
            meta_ide=FakeMetaIDE(FakeIDEStatus(pending_reviews=3)),
            governed_execution=FakeGovernedExecution(),
        )
        self.assertEqual(rt.phase(), ProductionPhase.REVIEWING.value)

    def test_approval_pending_from_governed_state(self) -> None:
        rt = ProductionOpsRuntime(
            meta_ide=FakeMetaIDE(),
            governed_execution=FakeGovernedExecution(state="governed"),
        )
        self.assertEqual(rt.phase(), ProductionPhase.APPROVAL_PENDING.value)

    def test_degraded_from_governed_blocked(self) -> None:
        rt = ProductionOpsRuntime(
            meta_ide=FakeMetaIDE(),
            governed_execution=FakeGovernedExecution(state="blocked"),
        )
        self.assertEqual(rt.phase(), ProductionPhase.DEGRADED.value)

    def test_planning_from_registered_production(self) -> None:
        rt = ProductionOpsRuntime(
            governed_execution=FakeGovernedExecution(),
        )
        rt.register_production("p1", "Build X", "substrate")
        self.assertEqual(rt.phase(), ProductionPhase.PLANNING.value)

    def test_producing_from_registered_production_with_packets(self) -> None:
        rt = ProductionOpsRuntime(
            governed_execution=FakeGovernedExecution(),
        )
        rt.register_production(
            "p1", "Build X", "substrate",
            packets=[{"id": "wp1", "status": "in_progress"}],
        )
        self.assertEqual(rt.phase(), ProductionPhase.PRODUCING.value)

    def test_reviewing_when_packets_done_but_no_quality(self) -> None:
        rt = ProductionOpsRuntime(
            governed_execution=FakeGovernedExecution(),
        )
        rt.register_production(
            "p1", "Build X", "substrate",
            packets=[{"id": "wp1", "status": "completed"}],
        )
        self.assertEqual(rt.phase(), ProductionPhase.REVIEWING.value)

    def test_approval_pending_when_quality_passed(self) -> None:
        rt = ProductionOpsRuntime(
            governed_execution=FakeGovernedExecution(),
        )
        rt.register_production(
            "p1", "Build X", "substrate",
            packets=[{"id": "wp1", "status": "completed"}],
        )
        rt.update_production_state("p1", quality_checks_passed=True)
        self.assertEqual(rt.phase(), ProductionPhase.APPROVAL_PENDING.value)

    def test_shipping_when_approved_but_no_proof(self) -> None:
        rt = ProductionOpsRuntime(
            governed_execution=FakeGovernedExecution(),
        )
        rt.register_production(
            "p1", "Build X", "substrate",
            packets=[{"id": "wp1", "status": "completed"}],
        )
        rt.update_production_state(
            "p1",
            quality_checks_passed=True,
            governance_approved=True,
        )
        self.assertEqual(rt.phase(), ProductionPhase.SHIPPING.value)

    def test_learning_when_fully_complete(self) -> None:
        rt = ProductionOpsRuntime(
            governed_execution=FakeGovernedExecution(),
        )
        rt.register_production(
            "p1", "Build X", "substrate",
            packets=[{"id": "wp1", "status": "completed"}],
        )
        rt.update_production_state(
            "p1",
            quality_checks_passed=True,
            governance_approved=True,
            proof_assembled=True,
        )
        self.assertEqual(rt.phase(), ProductionPhase.LEARNING.value)

    def test_degraded_when_blocked(self) -> None:
        rt = ProductionOpsRuntime(
            governed_execution=FakeGovernedExecution(),
        )
        rt.register_production(
            "p1", "Build X", "substrate",
            packets=[{"id": "wp1", "status": "completed"}],
        )
        rt.update_production_state(
            "p1",
            blocked_reasons=["dependency missing"],
        )
        self.assertEqual(rt.phase(), ProductionPhase.DEGRADED.value)


class TestCompletionInvariant(unittest.TestCase):
    def test_not_complete_without_quality(self) -> None:
        rt = ProductionOpsRuntime()
        rt.register_production(
            "p1", "Build X", "substrate",
            packets=[{"id": "wp1", "status": "completed"}],
        )
        self.assertFalse(rt.is_complete("p1"))

    def test_not_complete_without_governance(self) -> None:
        rt = ProductionOpsRuntime()
        rt.register_production(
            "p1", "Build X", "substrate",
            packets=[{"id": "wp1", "status": "completed"}],
        )
        rt.update_production_state("p1", quality_checks_passed=True)
        self.assertFalse(rt.is_complete("p1"))

    def test_not_complete_without_proof(self) -> None:
        rt = ProductionOpsRuntime()
        rt.register_production(
            "p1", "Build X", "substrate",
            packets=[{"id": "wp1", "status": "completed"}],
        )
        rt.update_production_state(
            "p1", quality_checks_passed=True, governance_approved=True,
        )
        self.assertFalse(rt.is_complete("p1"))

    def test_not_complete_with_blockers(self) -> None:
        rt = ProductionOpsRuntime()
        rt.register_production(
            "p1", "Build X", "substrate",
            packets=[{"id": "wp1", "status": "completed"}],
        )
        rt.update_production_state(
            "p1",
            quality_checks_passed=True,
            governance_approved=True,
            proof_assembled=True,
            blocked_reasons=["dependency X unavailable"],
        )
        self.assertFalse(rt.is_complete("p1"))

    def test_not_complete_with_unexecuted_packets(self) -> None:
        rt = ProductionOpsRuntime()
        rt.register_production(
            "p1", "Build X", "substrate",
            packets=[{"id": "wp1", "status": "in_progress"}],
        )
        rt.update_production_state(
            "p1",
            quality_checks_passed=True,
            governance_approved=True,
            proof_assembled=True,
        )
        self.assertFalse(rt.is_complete("p1"))

    def test_complete_when_all_gates_pass(self) -> None:
        rt = ProductionOpsRuntime()
        rt.register_production(
            "p1", "Build X", "substrate",
            packets=[{"id": "wp1", "status": "completed"}],
        )
        rt.update_production_state(
            "p1",
            quality_checks_passed=True,
            governance_approved=True,
            proof_assembled=True,
        )
        self.assertTrue(rt.is_complete("p1"))

    def test_complete_with_multiple_packet_statuses(self) -> None:
        rt = ProductionOpsRuntime()
        rt.register_production(
            "p1", "Build X", "substrate",
            packets=[
                {"id": "wp1", "status": "completed"},
                {"id": "wp2", "status": "merged"},
                {"id": "wp3", "status": "verified"},
                {"id": "wp4", "status": "shipped"},
            ],
        )
        rt.update_production_state(
            "p1",
            quality_checks_passed=True,
            governance_approved=True,
            proof_assembled=True,
        )
        self.assertTrue(rt.is_complete("p1"))

    def test_complete_returns_false_for_unknown_id(self) -> None:
        rt = ProductionOpsRuntime()
        self.assertFalse(rt.is_complete("nonexistent"))


class TestMultiProject(unittest.TestCase):
    def test_concurrent_projects_count(self) -> None:
        rt = ProductionOpsRuntime(
            governed_execution=FakeGovernedExecution(),
        )
        rt.register_production("p1", "Build X", "substrate",
                               packets=[{"id": "wp1", "status": "in_progress"}])
        rt.register_production("p2", "Build Y", "projection",
                               packets=[{"id": "wp2", "status": "in_progress"}])
        snap = rt.snapshot()
        self.assertEqual(snap.concurrent_projects, 2)

    def test_per_project_phases(self) -> None:
        rt = ProductionOpsRuntime(
            governed_execution=FakeGovernedExecution(),
        )
        rt.register_production("p1", "Build X", "substrate",
                               packets=[{"id": "wp1", "status": "in_progress"}])
        rt.register_production("p2", "Build Y", "projection",
                               packets=[{"id": "wp2", "status": "completed"}])
        phases = rt.per_project_phases()
        self.assertEqual(phases["p1"], ProductionPhase.PRODUCING.value)
        self.assertEqual(phases["p2"], ProductionPhase.REVIEWING.value)

    def test_overall_phase_worst_case_wins(self) -> None:
        rt = ProductionOpsRuntime(
            governed_execution=FakeGovernedExecution(),
        )
        rt.register_production("p1", "Build X", "substrate",
                               packets=[{"id": "wp1", "status": "completed"}])
        rt.update_production_state(
            "p1", quality_checks_passed=True,
            governance_approved=True, proof_assembled=True,
        )
        rt.register_production("p2", "Build Y", "projection",
                               packets=[{"id": "wp2", "status": "in_progress"}])
        self.assertEqual(rt.phase(), ProductionPhase.PRODUCING.value)


class TestTargetFiltering(unittest.TestCase):
    def test_by_target_filters_correctly(self) -> None:
        rt = ProductionOpsRuntime()
        rt.register_production("p1", "UMH Feature", "substrate")
        rt.register_production("p2", "EOS Feature", "projection")
        rt.register_production("p3", "Landing Page", "website")

        substrate = rt.by_target(ProductionTarget.SUBSTRATE.value)
        self.assertEqual(len(substrate), 1)
        self.assertEqual(substrate[0]["production_id"], "p1")

        projection = rt.by_target(ProductionTarget.PROJECTION.value)
        self.assertEqual(len(projection), 1)
        self.assertEqual(projection[0]["production_id"], "p2")

    def test_by_target_empty_for_missing_type(self) -> None:
        rt = ProductionOpsRuntime()
        rt.register_production("p1", "UMH Feature", "substrate")
        self.assertEqual(rt.by_target("automation"), [])


class TestHealthDerivation(unittest.TestCase):
    def test_offline_when_no_productions(self) -> None:
        rt = ProductionOpsRuntime(
            governed_execution=FakeGovernedExecution(health="offline"),
        )
        self.assertEqual(rt.health(), ProductionHealth.OFFLINE.value)

    def test_blocked_when_degraded_production(self) -> None:
        rt = ProductionOpsRuntime(
            governed_execution=FakeGovernedExecution(health="active"),
            agent_workforce=FakeAgentWorkforce(health="active"),
        )
        rt.register_production("p1", "Build X", "substrate")
        rt.update_production_state("p1", blocked_reasons=["test failure"])
        self.assertEqual(rt.health(), ProductionHealth.BLOCKED.value)

    def test_constrained_when_workforce_overloaded(self) -> None:
        rt = ProductionOpsRuntime(
            governed_execution=FakeGovernedExecution(health="active"),
            agent_workforce=FakeAgentWorkforce(health="overloaded"),
        )
        rt.register_production(
            "p1", "Build X", "substrate",
            packets=[{"id": "wp1", "status": "in_progress"}],
        )
        self.assertEqual(rt.health(), ProductionHealth.CONSTRAINED.value)

    def test_optimal_when_everything_good(self) -> None:
        rt = ProductionOpsRuntime(
            governed_execution=FakeGovernedExecution(health="optimal"),
            agent_workforce=FakeAgentWorkforce(health="optimal"),
        )
        rt.register_production(
            "p1", "Build X", "substrate",
            packets=[{"id": "wp1", "status": "in_progress"}],
        )
        self.assertEqual(rt.health(), ProductionHealth.OPTIMAL.value)

    def test_active_when_mixed(self) -> None:
        rt = ProductionOpsRuntime(
            governed_execution=FakeGovernedExecution(health="constrained"),
            agent_workforce=FakeAgentWorkforce(health="active"),
        )
        rt.register_production(
            "p1", "Build X", "substrate",
            packets=[{"id": "wp1", "status": "in_progress"}],
        )
        self.assertEqual(rt.health(), ProductionHealth.ACTIVE.value)


class TestBlockers(unittest.TestCase):
    def test_production_blockers(self) -> None:
        rt = ProductionOpsRuntime(
            governed_execution=FakeGovernedExecution(),
        )
        rt.register_production("p1", "Build X", "substrate")
        rt.update_production_state("p1", blocked_reasons=["dep missing"])
        blockers = rt.blockers()
        self.assertEqual(len(blockers), 1)
        self.assertEqual(blockers[0]["production_id"], "p1")
        self.assertIn("dep missing", blockers[0]["reasons"])

    def test_organism_level_blockers_from_governed_execution(self) -> None:
        rt = ProductionOpsRuntime(
            governed_execution=FakeGovernedExecution(
                blockers=[{"description": "no executor available"}],
            ),
        )
        blockers = rt.blockers()
        self.assertEqual(len(blockers), 1)
        self.assertEqual(blockers[0]["production_id"], "_organism")


class TestWhatShipsNext(unittest.TestCase):
    def test_returns_shipping_and_approval_pending(self) -> None:
        rt = ProductionOpsRuntime()
        rt.register_production(
            "p1", "Feature A", "substrate",
            packets=[{"id": "wp1", "status": "completed"}],
        )
        rt.update_production_state("p1", quality_checks_passed=True)

        rt.register_production(
            "p2", "Feature B", "projection",
            packets=[{"id": "wp2", "status": "completed"}],
        )
        rt.update_production_state(
            "p2", quality_checks_passed=True, governance_approved=True,
        )

        ships = rt.what_ships_next()
        self.assertEqual(len(ships), 2)

    def test_excludes_producing_phase(self) -> None:
        rt = ProductionOpsRuntime()
        rt.register_production(
            "p1", "Feature A", "substrate",
            packets=[{"id": "wp1", "status": "in_progress"}],
        )
        ships = rt.what_ships_next()
        self.assertEqual(len(ships), 0)


class TestSnapshot(unittest.TestCase):
    def test_snapshot_has_all_fields(self) -> None:
        rt = ProductionOpsRuntime(
            meta_ide=FakeMetaIDE(FakeIDEStatus(pending_reviews=2)),
            governed_execution=FakeGovernedExecution(pending_approvals=1),
            execution_fabric=FakeExecutionFabric(queue_depth=3),
            agent_workforce=FakeAgentWorkforce(
                health="active",
                summary={"total_agent_types": 5},
            ),
            meta_ide_context=FakeMetaIdeContext({"repo": "OS", "branch": "main"}),
        )
        rt.register_production(
            "p1", "Build X", "substrate",
            packets=[{"id": "wp1", "status": "in_progress"}],
        )

        snap = rt.snapshot()
        self.assertIsInstance(snap, ProductionSnapshot)
        self.assertEqual(snap.pending_reviews, 2)
        self.assertEqual(snap.pending_approvals, 1)
        self.assertEqual(snap.queue_depth, 3)
        self.assertEqual(snap.concurrent_projects, 1)
        self.assertGreater(snap.generated_at, 0)

    def test_snapshot_to_dict(self) -> None:
        rt = ProductionOpsRuntime(
            governed_execution=FakeGovernedExecution(),
        )
        snap = rt.snapshot()
        d = snap.to_dict()
        self.assertIn("phase", d)
        self.assertIn("health", d)
        self.assertIn("concurrent_projects", d)
        self.assertIn("per_project_phases", d)


class TestSummary(unittest.TestCase):
    def test_summary_returns_dict(self) -> None:
        rt = ProductionOpsRuntime(
            governed_execution=FakeGovernedExecution(),
        )
        s = rt.summary()
        self.assertIsInstance(s, dict)
        self.assertIn("phase", s)
        self.assertIn("health", s)
        self.assertIn("active_count", s)
        self.assertIn("concurrent_projects", s)


class TestUpdateProductionState(unittest.TestCase):
    def test_returns_none_for_unknown_id(self) -> None:
        rt = ProductionOpsRuntime()
        result = rt.update_production_state("nonexistent", quality_checks_passed=True)
        self.assertIsNone(result)

    def test_updates_and_rederives_phase(self) -> None:
        rt = ProductionOpsRuntime()
        rt.register_production(
            "p1", "Build X", "substrate",
            packets=[{"id": "wp1", "status": "completed"}],
        )
        entry = rt.update_production_state("p1", quality_checks_passed=True)
        self.assertIsNotNone(entry)
        self.assertEqual(entry.phase, ProductionPhase.APPROVAL_PENDING.value)


class TestActiveProductions(unittest.TestCase):
    def test_excludes_idle_and_learning(self) -> None:
        rt = ProductionOpsRuntime()
        rt.register_production(
            "p1", "Build X", "substrate",
            packets=[{"id": "wp1", "status": "in_progress"}],
        )
        rt.register_production(
            "p2", "Build Y", "substrate",
            packets=[{"id": "wp2", "status": "completed"}],
        )
        rt.update_production_state(
            "p2",
            quality_checks_passed=True,
            governance_approved=True,
            proof_assembled=True,
        )

        active = rt.active_productions()
        ids = [a["production_id"] for a in active]
        self.assertIn("p1", ids)
        self.assertNotIn("p2", ids)


if __name__ == "__main__":
    unittest.main()
