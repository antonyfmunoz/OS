"""C40B — Runtime Embodiment Campaign tests.

Tests cover: SLO tracker math, campaign context, embodiment harness,
phase data structures, scenario definitions, and skip-browser campaign run.
"""

from __future__ import annotations

import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

sys.path.insert(0, "/opt/OS")
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from scripts.c40b_phases.campaign_context import (
    CampaignContext,
    DimensionVerdict,
    MutationResult,
    PhaseResult,
    SLOTracker,
    SUCCESS,
    GOVERNANCE_CONSTRAINT,
    IMPLEMENTATION_DEFECT,
)


# ── TestSLOTracker ──────────────────────────────────────────────────────


class TestSLOTracker(unittest.TestCase):
    def test_empty_tracker_defaults(self):
        slo = SLOTracker()
        self.assertEqual(slo.mesh_reliability(), 0.0)
        self.assertEqual(slo.avg_latency_ms(), 0.0)
        self.assertEqual(slo.p95_latency_ms(), 0.0)
        self.assertEqual(slo.proof_completeness(), 0.0)

    def test_mesh_reliability(self):
        slo = SLOTracker(mesh_attempts=100, mesh_successes=99)
        self.assertEqual(slo.mesh_reliability(), 0.99)

    def test_session_availability(self):
        slo = SLOTracker(session_checks=200, session_available=190)
        self.assertEqual(slo.session_availability(), 0.95)

    def test_dispatch_success_rate(self):
        slo = SLOTracker(dispatch_attempts=50, dispatch_successes=48)
        self.assertAlmostEqual(slo.dispatch_success_rate(), 0.96, places=2)

    def test_latency_calculations(self):
        slo = SLOTracker(latencies_ms=[100, 200, 300, 400, 500, 600, 700, 800, 900, 1000])
        self.assertEqual(slo.avg_latency_ms(), 550.0)
        self.assertEqual(slo.p95_latency_ms(), 1000.0)

    def test_p95_single_value(self):
        slo = SLOTracker(latencies_ms=[42.0])
        self.assertEqual(slo.p95_latency_ms(), 42.0)

    def test_adapter_failure_rate(self):
        slo = SLOTracker(adapter_calls=100, adapter_failures=3)
        self.assertEqual(slo.adapter_failure_rate(), 0.03)

    def test_all_slos_met_passing(self):
        slo = SLOTracker(
            mesh_attempts=100, mesh_successes=100,
            session_checks=100, session_available=100,
            dispatch_attempts=100, dispatch_successes=100,
            playwright_checks=100, playwright_available=100,
            chrome_starts=100, chrome_successes=100,
            recovery_attempts=10, recovery_within_30s=10,
            adapter_calls=100, adapter_failures=0,
            latencies_ms=[100.0] * 100,
            event_loss=0,
            proof_total=50, proof_complete=50,
        )
        self.assertTrue(slo.all_slos_met())

    def test_all_slos_met_failing_mesh(self):
        slo = SLOTracker(
            mesh_attempts=100, mesh_successes=90,
            session_checks=100, session_available=100,
            dispatch_attempts=100, dispatch_successes=100,
            playwright_checks=100, playwright_available=100,
            chrome_starts=100, chrome_successes=100,
            adapter_calls=100, adapter_failures=0,
            latencies_ms=[100.0] * 100,
            event_loss=0,
            proof_total=50, proof_complete=50,
        )
        self.assertFalse(slo.all_slos_met())

    def test_all_slos_met_failing_latency(self):
        slo = SLOTracker(
            mesh_attempts=100, mesh_successes=100,
            session_checks=100, session_available=100,
            dispatch_attempts=100, dispatch_successes=100,
            playwright_checks=100, playwright_available=100,
            chrome_starts=100, chrome_successes=100,
            adapter_calls=100, adapter_failures=0,
            latencies_ms=[5000.0] * 100,
            event_loss=0,
            proof_total=50, proof_complete=50,
        )
        self.assertFalse(slo.all_slos_met())

    def test_all_slos_met_event_loss(self):
        slo = SLOTracker(
            mesh_attempts=100, mesh_successes=100,
            session_checks=100, session_available=100,
            dispatch_attempts=100, dispatch_successes=100,
            playwright_checks=100, playwright_available=100,
            chrome_starts=100, chrome_successes=100,
            adapter_calls=100, adapter_failures=0,
            latencies_ms=[100.0] * 100,
            event_loss=1,
            proof_total=50, proof_complete=50,
        )
        self.assertFalse(slo.all_slos_met())

    def test_scorecard_format(self):
        slo = SLOTracker(
            mesh_attempts=100, mesh_successes=99,
            dispatch_attempts=50, dispatch_successes=48,
            latencies_ms=[200.0, 400.0],
        )
        sc = slo.to_scorecard()
        self.assertIn("mesh_reliability", sc)
        self.assertIn("dispatch_success_rate", sc)
        self.assertIn("avg_latency_ms", sc)
        self.assertIn("p95_latency_ms", sc)
        self.assertIn("event_loss", sc)
        self.assertIsInstance(sc["mesh_reliability"], float)

    def test_zero_recovery_attempts_passes(self):
        slo = SLOTracker(
            mesh_attempts=100, mesh_successes=100,
            session_checks=100, session_available=100,
            dispatch_attempts=100, dispatch_successes=100,
            playwright_checks=100, playwright_available=100,
            chrome_starts=100, chrome_successes=100,
            recovery_attempts=0, recovery_within_30s=0,
            adapter_calls=100, adapter_failures=0,
            latencies_ms=[100.0] * 100,
            event_loss=0,
            proof_total=50, proof_complete=50,
        )
        self.assertTrue(slo.all_slos_met())


# ── TestCampaignContext ─────────────────────────────────────────────────


class TestCampaignContext(unittest.TestCase):
    def setUp(self):
        self.ctx = CampaignContext(skip_browser=True)

    def test_creation(self):
        self.assertTrue(self.ctx.skip_browser)
        self.assertIsNotNone(self.ctx.daemon)
        self.assertIsNotNone(self.ctx.router)
        self.assertIsNotNone(self.ctx.event_spine)
        self.assertIsNotNone(self.ctx.registry)

    def test_verdicts_initialized(self):
        self.assertIn("organism", self.ctx.verdicts)
        self.assertIn("runtime", self.ctx.verdicts)
        self.assertIn("projection", self.ctx.verdicts)
        self.assertIn("operator", self.ctx.verdicts)
        for v in self.ctx.verdicts.values():
            self.assertEqual(v.status, "UNTESTED")

    def test_slo_tracker_initialized(self):
        self.assertIsInstance(self.ctx.slo, SLOTracker)
        self.assertEqual(self.ctx.slo.mesh_attempts, 0)

    def test_classify_success(self):
        r = MutationResult(
            operation_id="test", phase=1, mutation_name="test",
            action_type="test", risk_level="low", intent="test",
            source="test", status="completed", success=True,
        )
        self.ctx._classify(r)
        self.assertEqual(r.classification, SUCCESS)

    def test_classify_rejected(self):
        r = MutationResult(
            operation_id="test", phase=1, mutation_name="test",
            action_type="test", risk_level="low", intent="test",
            source="test", status="rejected", rejected_reason="mode",
        )
        self.ctx._classify(r)
        self.assertEqual(r.classification, GOVERNANCE_CONSTRAINT)

    def test_classify_error(self):
        r = MutationResult(
            operation_id="test", phase=1, mutation_name="test",
            action_type="test", risk_level="low", intent="test",
            source="test", error="SomeError: boom",
        )
        self.ctx._classify(r)
        self.assertEqual(r.classification, IMPLEMENTATION_DEFECT)

    def test_noop_execute(self):
        fn = self.ctx.noop_execute("test_label")
        output, success = fn()
        self.assertTrue(success)
        self.assertIn("test_label", output)

    def test_event_count_starts_zero(self):
        self.assertEqual(self.ctx.event_count(), 0)


# ── TestEmbodimentHarness ───────────────────────────────────────────────


class TestEmbodimentHarness(unittest.TestCase):
    def setUp(self):
        from scripts.c40b_phases.embodiment_harness import (
            EmbodimentHarness,
            EmbodimentReport,
            DimensionResult,
            ProductionReadinessCheck,
        )
        self.EmbodimentHarness = EmbodimentHarness
        self.EmbodimentReport = EmbodimentReport
        self.DimensionResult = DimensionResult
        self.ProductionReadinessCheck = ProductionReadinessCheck

    def test_creation(self):
        h = self.EmbodimentHarness()
        self.assertIsNotNone(h.report)
        self.assertEqual(h.report.organism.status, "UNTESTED")

    def test_report_default_not_ready(self):
        report = self.EmbodimentReport()
        self.assertFalse(report.is_production_ready())
        self.assertEqual(report.verdict, "NOT READY")

    def test_all_dimensions_pass(self):
        report = self.EmbodimentReport()
        for dim in [report.organism, report.runtime, report.projection, report.operator]:
            dim.status = "PASS"
        self.assertTrue(report.all_dimensions_pass())

    def test_not_all_pass_with_fail(self):
        report = self.EmbodimentReport()
        report.organism.status = "PASS"
        report.runtime.status = "PASS"
        report.projection.status = "PASS"
        report.operator.status = "FAIL"
        self.assertFalse(report.all_dimensions_pass())

    def test_evaluate_runtime_passing(self):
        h = self.EmbodimentHarness()
        slo = SLOTracker(
            mesh_attempts=100, mesh_successes=100,
            session_checks=100, session_available=100,
            dispatch_attempts=100, dispatch_successes=100,
            playwright_checks=100, playwright_available=100,
            chrome_starts=100, chrome_successes=100,
            adapter_calls=100, adapter_failures=0,
            latencies_ms=[200.0] * 100,
            event_loss=0,
            proof_total=50, proof_complete=50,
        )
        dim = h.evaluate_runtime(slo)
        self.assertEqual(dim.status, "PASS")
        self.assertTrue(dim.gate_passed)
        self.assertEqual(len(dim.blockers), 0)

    def test_evaluate_runtime_failing(self):
        h = self.EmbodimentHarness()
        slo = SLOTracker(
            mesh_attempts=100, mesh_successes=50,
            dispatch_attempts=100, dispatch_successes=50,
            latencies_ms=[5000.0] * 100,
            event_loss=3,
        )
        dim = h.evaluate_runtime(slo)
        self.assertEqual(dim.status, "FAIL")
        self.assertFalse(dim.gate_passed)
        self.assertGreater(len(dim.blockers), 0)

    def test_evaluate_projection_passing(self):
        h = self.EmbodimentHarness()
        dim = h.evaluate_projection(
            event_loss=0, surface_equivalence=1.0,
            proof_completeness=1.0, surfaces_tested=4,
        )
        self.assertEqual(dim.status, "PASS")

    def test_evaluate_projection_failing(self):
        h = self.EmbodimentHarness()
        dim = h.evaluate_projection(event_loss=2)
        self.assertEqual(dim.status, "FAIL")
        self.assertIn("event loss", dim.blockers[0])

    def test_evaluate_operator_passing(self):
        h = self.EmbodimentHarness()
        dim = h.evaluate_operator(
            scenario_success_rate=0.98,
            scenarios_passed=25,
            total_executions=250,
            synthetic_evidence_count=0,
        )
        self.assertEqual(dim.status, "PASS")

    def test_evaluate_operator_failing_synthetic(self):
        h = self.EmbodimentHarness()
        dim = h.evaluate_operator(
            scenario_success_rate=0.98,
            scenarios_passed=25,
            total_executions=250,
            synthetic_evidence_count=5,
        )
        self.assertEqual(dim.status, "FAIL")
        self.assertIn("synthetic", dim.blockers[0])

    def test_production_readiness_all_met(self):
        h = self.EmbodimentHarness()
        slo = SLOTracker(
            mesh_attempts=100, mesh_successes=100,
            session_checks=100, session_available=100,
            dispatch_attempts=100, dispatch_successes=100,
            playwright_checks=100, playwright_available=100,
            chrome_starts=100, chrome_successes=100,
            adapter_calls=100, adapter_failures=0,
            latencies_ms=[200.0] * 100,
            event_loss=0,
            proof_total=50, proof_complete=50,
        )
        checks = h.build_production_readiness(
            slo=slo,
            scenarios_passed=25,
            synthetic_count=0,
            recovery_demonstrated=True,
            total_operator_executions=250,
            browser_availability=0.99,
            proof_chain_complete=True,
            orl_preserved=True,
        )
        self.assertEqual(len(checks), 8)
        self.assertTrue(all(c.met for c in checks))

    def test_production_readiness_some_failing(self):
        h = self.EmbodimentHarness()
        slo = SLOTracker()
        checks = h.build_production_readiness(
            slo=slo,
            scenarios_passed=10,
            synthetic_count=5,
            recovery_demonstrated=False,
            total_operator_executions=50,
            browser_availability=0.50,
            proof_chain_complete=False,
            orl_preserved=False,
        )
        met_count = sum(1 for c in checks if c.met)
        self.assertLess(met_count, 8)

    def test_finalize_production_ready(self):
        h = self.EmbodimentHarness()
        for dim in [h.report.organism, h.report.runtime,
                    h.report.projection, h.report.operator]:
            dim.status = "PASS"
            dim.gate_passed = True
        h.report.production_readiness = [
            self.ProductionReadinessCheck(check="x", requirement="y", met=True)
        ]
        report = h.finalize()
        self.assertEqual(report.verdict, "PRODUCTION READY")

    def test_finalize_not_ready(self):
        h = self.EmbodimentHarness()
        report = h.finalize()
        self.assertEqual(report.verdict, "NOT READY")

    def test_report_to_dict(self):
        report = self.EmbodimentReport()
        d = report.to_dict()
        self.assertIn("organism", d)
        self.assertIn("runtime", d)
        self.assertIn("projection", d)
        self.assertIn("operator", d)
        self.assertIn("verdict", d)


# ── TestPhase1RuntimeAudit ──────────────────────────────────────────────


class TestPhase1RuntimeAudit(unittest.TestCase):
    def test_import(self):
        from scripts.c40b_phases.phase1_runtime_audit import (
            run_phase1, BoundaryResult, BrowserPrerequisite, CONTRACT_PATH,
        )
        self.assertIsNotNone(run_phase1)

    def test_boundary_result_structure(self):
        from scripts.c40b_phases.phase1_runtime_audit import BoundaryResult
        b = BoundaryResult(
            boundary_id="test", source="a", destination="b", transport="http",
        )
        d = b.to_dict()
        self.assertIn("boundary_id", d)
        self.assertIn("latency_ms", d)
        self.assertIn("status", d)
        self.assertEqual(d["status"], "untested")

    def test_browser_prerequisite_structure(self):
        from scripts.c40b_phases.phase1_runtime_audit import BrowserPrerequisite
        bp = BrowserPrerequisite()
        self.assertFalse(bp.overall)
        self.assertFalse(bp.beast_connected)

    def test_run_phase1_skip_browser(self):
        ctx = CampaignContext(skip_browser=True)
        from scripts.c40b_phases.phase1_runtime_audit import run_phase1
        pr = run_phase1(ctx)
        self.assertIsInstance(pr, PhaseResult)
        self.assertEqual(pr.phase, 1)
        self.assertEqual(pr.name, "Runtime Boundary Audit")


# ── TestPhase2RuntimeFix ────────────────────────────────────────────────


class TestPhase2RuntimeFix(unittest.TestCase):
    def test_import(self):
        from scripts.c40b_phases.phase2_runtime_fix import run_phase2
        self.assertIsNotNone(run_phase2)

    def test_run_phase2_no_contract_file(self):
        ctx = CampaignContext(skip_browser=True)
        from scripts.c40b_phases.phase2_runtime_fix import run_phase2
        pr = run_phase2(ctx)
        self.assertIsInstance(pr, PhaseResult)
        self.assertEqual(pr.phase, 2)


# ── TestPhase3OperatorQualification ─────────────────────────────────────


class TestPhase3OperatorQualification(unittest.TestCase):
    def test_scenarios_count(self):
        from scripts.c40b_phases.phase3_operator_qualification import SCENARIOS
        self.assertEqual(len(SCENARIOS), 25)

    def test_scenario_structure(self):
        from scripts.c40b_phases.phase3_operator_qualification import SCENARIOS
        for s in SCENARIOS:
            self.assertIn("id", s, "Scenario missing 'id': %s" % s.get("name", "??"))
            self.assertIn("name", s)
            self.assertIn("requires_browser", s)
            self.assertIn("requires_mutation", s)

    def test_scenario_ids_unique(self):
        from scripts.c40b_phases.phase3_operator_qualification import SCENARIOS
        ids = [s["id"] for s in SCENARIOS]
        self.assertEqual(len(ids), len(set(ids)), "Duplicate scenario IDs found")

    def test_reps_per_scenario(self):
        from scripts.c40b_phases.phase3_operator_qualification import REPS_PER_SCENARIO
        self.assertEqual(REPS_PER_SCENARIO, 10)


# ── TestPhase4EmbodiedStress ────────────────────────────────────────────


class TestPhase4EmbodiedStress(unittest.TestCase):
    def test_import(self):
        from scripts.c40b_phases.phase4_embodied_stress import run_phase4
        self.assertIsNotNone(run_phase4)

    def test_imports_scenarios(self):
        from scripts.c40b_phases.phase4_embodied_stress import SCENARIOS
        self.assertEqual(len(SCENARIOS), 25)


# ── TestPhase5Certification ─────────────────────────────────────────────


class TestPhase5Certification(unittest.TestCase):
    def test_import(self):
        from scripts.c40b_phases.phase5_runtime_certification import run_phase5
        self.assertIsNotNone(run_phase5)


# ── TestReportGenerator ─────────────────────────────────────────────────


class TestReportGenerator(unittest.TestCase):
    def test_import(self):
        from scripts.c40b_phases.report_generator import generate_report
        self.assertIsNotNone(generate_report)

    def test_generate_report(self):
        from scripts.c40b_phases.report_generator import generate_report, REPORT_DIR
        ctx = CampaignContext(skip_browser=True)
        path = generate_report(ctx)
        self.assertTrue(Path(path).exists())
        content = Path(path).read_text()
        self.assertIn("C40B", content)
        self.assertIn("Verdict", content)


# ── TestIntegration ─────────────────────────────────────────────────────


class TestIntegration(unittest.TestCase):
    def test_skip_browser_campaign_runs(self):
        from scripts.run_c40b_campaign import run_campaign
        run_campaign(skip_browser=True)

    def test_phase_only_runs(self):
        from scripts.run_c40b_campaign import run_campaign
        run_campaign(skip_browser=True, phase_only=1)


if __name__ == "__main__":
    unittest.main()
