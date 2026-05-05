"""Tests for environment_bridge/bootstrap_plan.py — Phase 96.8A."""

import sys

sys.path.insert(0, "/opt/OS")

import unittest
from core.environment_bridge.bootstrap_plan import (
    BootstrapPlan,
    BootstrapStep,
    BootstrapStepStatus,
    build_local_worker_bootstrap_plan,
    build_windows_task_scheduler_bootstrap_plan,
    build_tmux_local_worker_bootstrap_plan,
    bootstrap_plan_requires_manual_once,
    summarize_bootstrap_plan,
)


class TestBootstrapPlanBuilds(unittest.TestCase):
    def test_build_returns_plan(self):
        plan = build_local_worker_bootstrap_plan()
        self.assertIsInstance(plan, BootstrapPlan)
        self.assertTrue(len(plan.steps) > 0)


class TestIncludesTmuxStep(unittest.TestCase):
    def test_has_tmux_step(self):
        plan = build_local_worker_bootstrap_plan()
        step_ids = [s.step_id for s in plan.steps]
        self.assertIn("start-tmux-session", step_ids)


class TestIncludesLocalWorkerStep(unittest.TestCase):
    def test_has_local_worker_step(self):
        plan = build_local_worker_bootstrap_plan()
        step_ids = [s.step_id for s in plan.steps]
        self.assertIn("run-local-worker", step_ids)


class TestIncludesHeartbeatVerification(unittest.TestCase):
    def test_has_heartbeat_step(self):
        plan = build_local_worker_bootstrap_plan()
        step_ids = [s.step_id for s in plan.steps]
        self.assertIn("verify-heartbeat", step_ids)


class TestManualOnceRequired(unittest.TestCase):
    def test_manual_once_required(self):
        plan = build_local_worker_bootstrap_plan()
        self.assertTrue(bootstrap_plan_requires_manual_once(plan))

    def test_can_automate_after(self):
        plan = build_local_worker_bootstrap_plan()
        self.assertTrue(plan.can_be_automated_after_bootstrap)


class TestOptionalSteps(unittest.TestCase):
    def test_has_optional_steps(self):
        plan = build_local_worker_bootstrap_plan()
        optional = [s for s in plan.steps if not s.required]
        self.assertTrue(len(optional) > 0)

    def test_optional_includes_task_scheduler(self):
        plan = build_local_worker_bootstrap_plan()
        optional_ids = [s.step_id for s in plan.steps if not s.required]
        self.assertIn("optional-task-scheduler", optional_ids)


class TestWindowsTaskSchedulerPlan(unittest.TestCase):
    def test_builds(self):
        plan = build_windows_task_scheduler_bootstrap_plan()
        self.assertIsInstance(plan, BootstrapPlan)
        self.assertEqual(plan.target_environment, "local_windows_gui")


class TestTmuxPlan(unittest.TestCase):
    def test_builds(self):
        plan = build_tmux_local_worker_bootstrap_plan()
        self.assertIsInstance(plan, BootstrapPlan)
        step_ids = [s.step_id for s in plan.steps]
        self.assertIn("create-session", step_ids)


class TestSummarize(unittest.TestCase):
    def test_summarize_returns_dict(self):
        plan = build_local_worker_bootstrap_plan()
        s = summarize_bootstrap_plan(plan)
        self.assertIsInstance(s, dict)
        self.assertIn("plan_id", s)
        self.assertIn("total_steps", s)
        self.assertIn("required_steps", s)
        self.assertIn("manual_once_required", s)
        self.assertTrue(s["manual_once_required"])


if __name__ == "__main__":
    unittest.main()
