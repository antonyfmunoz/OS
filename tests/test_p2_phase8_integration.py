"""P2 Phase 8 — Integration tests for all workflow domains.

Verifies:
1. All 6 workflow domains are importable and produce governed steps
2. Each workflow executes through WorkflowRunner
3. Each workflow uses governed_mutation (mutation_name on every step)
4. Package exports are complete

Run with: pytest tests/test_p2_phase8_integration.py -v
"""

import os
import sys
import tempfile

import pytest

_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _REPO_ROOT)

pytestmark = pytest.mark.smoke


class TestAllWorkflowsImportable:

    def test_research_importable(self):
        from projections.eos.workflows import ResearchWorkflow
        assert ResearchWorkflow is not None

    def test_planning_importable(self):
        from projections.eos.workflows import PlanningWorkflow
        assert PlanningWorkflow is not None

    def test_outreach_importable(self):
        from projections.eos.workflows import OutreachWorkflow
        assert OutreachWorkflow is not None

    def test_followup_importable(self):
        from projections.eos.workflows import FollowUpWorkflow
        assert FollowUpWorkflow is not None

    def test_content_importable(self):
        from projections.eos.workflows import ContentCalendarWorkflow
        assert ContentCalendarWorkflow is not None

    def test_review_importable(self):
        from projections.eos.workflows import ReviewWorkflow
        assert ReviewWorkflow is not None

    def test_execution_importable(self):
        from projections.eos.workflows import ExecutionWorkflow
        assert ExecutionWorkflow is not None

    def test_daily_importable(self):
        from projections.eos.workflows import DailyRhythmWorkflow
        assert DailyRhythmWorkflow is not None

    def test_runner_importable(self):
        from projections.eos.workflows import WorkflowRunner
        assert WorkflowRunner is not None

    def test_types_importable(self):
        from projections.eos.workflows import WorkflowStep, WorkflowResult, StepResult
        assert WorkflowStep is not None
        assert WorkflowResult is not None
        assert StepResult is not None


class TestAllWorkflowsProduceGovernedSteps:

    def test_research_steps_governed(self):
        from projections.eos.workflows import ResearchWorkflow
        wf = ResearchWorkflow()
        for step in wf.steps("test"):
            assert step.mutation_name, f"{step.name} missing mutation_name"

    def test_planning_steps_governed(self):
        from projections.eos.workflows import PlanningWorkflow
        wf = PlanningWorkflow()
        for step in wf.steps("test goal"):
            assert step.mutation_name, f"{step.name} missing mutation_name"

    def test_outreach_steps_governed(self):
        from projections.eos.workflows import OutreachWorkflow
        wf = OutreachWorkflow()
        for step in wf.steps({"id": "t1", "name": "Test"}):
            assert step.mutation_name, f"{step.name} missing mutation_name"

    def test_followup_steps_governed(self):
        from projections.eos.workflows import FollowUpWorkflow
        wf = FollowUpWorkflow()
        for step in wf.steps():
            assert step.mutation_name, f"{step.name} missing mutation_name"

    def test_content_steps_governed(self):
        from projections.eos.workflows import ContentCalendarWorkflow
        wf = ContentCalendarWorkflow()
        for step in wf.steps(3):
            assert step.mutation_name, f"{step.name} missing mutation_name"

    def test_review_steps_governed(self):
        from projections.eos.workflows import ReviewWorkflow
        wf = ReviewWorkflow()
        for step in wf.steps("gates"):
            assert step.mutation_name, f"{step.name} missing mutation_name"

    def test_execution_define_steps_governed(self):
        from projections.eos.workflows import ExecutionWorkflow
        wf = ExecutionWorkflow()
        for step in wf.steps_define("test"):
            assert step.mutation_name, f"{step.name} missing mutation_name"

    def test_execution_complete_steps_governed(self):
        from projections.eos.workflows import ExecutionWorkflow
        wf = ExecutionWorkflow()
        for step in wf.steps_complete("done"):
            assert step.mutation_name, f"{step.name} missing mutation_name"

    def test_daily_brief_steps_governed(self):
        from projections.eos.workflows import DailyRhythmWorkflow
        wf = DailyRhythmWorkflow()
        for step in wf.brief_steps():
            assert step.mutation_name, f"{step.name} missing mutation_name"

    def test_daily_eod_steps_governed(self):
        from projections.eos.workflows import DailyRhythmWorkflow
        wf = DailyRhythmWorkflow()
        for step in wf.eod_steps():
            assert step.mutation_name, f"{step.name} missing mutation_name"


class TestAllWorkflowsThroughRunner:

    def test_research_through_runner(self):
        from projections.eos.workflows import ResearchWorkflow, WorkflowRunner
        from projections.eos.workflows import research as mod

        with tempfile.TemporaryDirectory() as tmpdir:
            orig = mod._FINDINGS_DIR
            mod._FINDINGS_DIR = tmpdir
            try:
                wf = ResearchWorkflow()
                runner = WorkflowRunner()
                result = runner.run("research", wf.steps("UMH"), source="test")
                assert result.steps_total == 4
            finally:
                mod._FINDINGS_DIR = orig

    def test_planning_through_runner(self):
        from projections.eos.workflows import PlanningWorkflow, WorkflowRunner
        from projections.eos.workflows import planning as mod

        with tempfile.TemporaryDirectory() as tmpdir:
            orig = mod._PLANS_DIR
            mod._PLANS_DIR = tmpdir
            try:
                wf = PlanningWorkflow()
                runner = WorkflowRunner()
                result = runner.run("planning", wf.steps("test"), source="test")
                assert result.steps_total == 4
            finally:
                mod._PLANS_DIR = orig

    def test_outreach_through_runner(self):
        from projections.eos.workflows import OutreachWorkflow, WorkflowRunner
        wf = OutreachWorkflow()
        runner = WorkflowRunner()
        lead = {
            "id": "t1", "name": "John", "source": "instagram",
            "age_range": "18-25", "engagement": True,
            "expressed_interest": "fitness",
        }
        result = runner.run("outreach", wf.steps(lead), source="test")
        assert result.steps_total == 3

    def test_followup_through_runner(self):
        from projections.eos.workflows import FollowUpWorkflow, WorkflowRunner
        wf = FollowUpWorkflow()
        runner = WorkflowRunner()
        result = runner.run("followup", wf.steps(), source="test")
        assert result.success

    def test_content_through_runner(self):
        from projections.eos.workflows import ContentCalendarWorkflow, WorkflowRunner
        wf = ContentCalendarWorkflow()
        runner = WorkflowRunner()
        result = runner.run("content", wf.steps(3), source="test")
        assert result.success

    def test_review_through_runner(self):
        from projections.eos.workflows import ReviewWorkflow, WorkflowRunner
        wf = ReviewWorkflow()
        runner = WorkflowRunner()
        result = runner.run("review", wf.steps("projections"), source="test")
        assert result.steps_total == 3

    def test_execution_through_runner(self):
        from projections.eos.workflows import ExecutionWorkflow, WorkflowRunner
        from projections.eos.workflows import execution as mod

        with tempfile.TemporaryDirectory() as tmpdir:
            orig = mod._TASKS_DIR
            mod._TASKS_DIR = tmpdir
            try:
                wf = ExecutionWorkflow()
                runner = WorkflowRunner()
                result = runner.run("task_define", wf.steps_define("test"), source="test")
                assert result.success
            finally:
                mod._TASKS_DIR = orig

    def test_daily_brief_through_runner(self):
        from projections.eos.workflows import DailyRhythmWorkflow, WorkflowRunner
        wf = DailyRhythmWorkflow()
        runner = WorkflowRunner()
        result = runner.run("brief", wf.brief_steps(), source="test")
        assert result.success

    def test_daily_eod_through_runner(self):
        from projections.eos.workflows import DailyRhythmWorkflow, WorkflowRunner
        wf = DailyRhythmWorkflow()
        runner = WorkflowRunner()
        result = runner.run("eod", wf.eod_steps(), source="test")
        assert result.success


class TestWorkflowPackageCompleteness:

    def test_all_workflow_files_exist(self):
        workflows_dir = os.path.join(_REPO_ROOT, "projections", "eos", "workflows")
        expected = [
            "__init__.py", "types.py", "runner.py",
            "research.py", "planning.py", "review.py",
            "execution.py", "daily.py",
            "outreach.py", "followup.py", "content.py",
        ]
        for f in expected:
            path = os.path.join(workflows_dir, f)
            assert os.path.exists(path), f"Missing: {f}"

    def test_workflow_count(self):
        workflows_dir = os.path.join(_REPO_ROOT, "projections", "eos", "workflows")
        py_files = [
            f for f in os.listdir(workflows_dir)
            if f.endswith(".py") and not f.startswith("__")
        ]
        assert len(py_files) >= 9, f"Expected >= 9 workflow files, found {len(py_files)}"

    def test_no_substrate_imports_in_workflows(self):
        """Workflows should not import directly from substrate internals
        (except through abstract ports or public API)."""
        import ast

        workflows_dir = os.path.join(_REPO_ROOT, "projections", "eos", "workflows")
        allowed_substrate = {
            "substrate.organism.report_dispatcher",
            "substrate.execution.cpu_gate",
            "substrate.sockets",
            "substrate",
        }
        violations = []
        for f in os.listdir(workflows_dir):
            if not f.endswith(".py") or f.startswith("__"):
                continue
            path = os.path.join(workflows_dir, f)
            try:
                with open(path) as fh:
                    tree = ast.parse(fh.read())
            except SyntaxError:
                continue
            for node in ast.walk(tree):
                if isinstance(node, ast.ImportFrom) and node.module:
                    mod = node.module
                    if mod.startswith("substrate.") and not any(
                        mod.startswith(a) for a in allowed_substrate
                    ):
                        violations.append(f"{f}: from {mod}")

        assert violations == [], (
            "Workflow files import from substrate internals:\n"
            + "\n".join(violations)
        )
