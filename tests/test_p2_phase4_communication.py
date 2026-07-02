"""P2 Phase 4 — Communication Workflow tests.

Verifies:
1. Existing workflows (outreach, followup, content) have steps() methods
2. Steps return WorkflowStep instances with proper mutation names
3. Workflows execute through WorkflowRunner

Run with: pytest tests/test_p2_phase4_communication.py -v
"""

import os
import sys

import pytest

_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _REPO_ROOT)

pytestmark = pytest.mark.smoke


class TestOutreachWorkflowGoverned:

    def test_has_steps_method(self):
        from projections.eos.workflows.outreach import OutreachWorkflow
        wf = OutreachWorkflow()
        assert hasattr(wf, "steps")

    def test_steps_returns_workflow_steps(self):
        from projections.eos.workflows.outreach import OutreachWorkflow
        from projections.eos.workflows.types import WorkflowStep
        wf = OutreachWorkflow()
        lead = {"id": "test-1", "name": "Test Lead", "source": "instagram"}
        steps = wf.steps(lead)
        assert len(steps) == 3
        for step in steps:
            assert isinstance(step, WorkflowStep)
            assert step.mutation_name
            assert step.intent

    def test_step_names(self):
        from projections.eos.workflows.outreach import OutreachWorkflow
        wf = OutreachWorkflow()
        lead = {"id": "test-1", "name": "Test Lead"}
        names = [s.name for s in wf.steps(lead)]
        assert names == ["qualify", "research", "draft"]

    def test_qualified_lead_runs_all_steps(self):
        from projections.eos.workflows.outreach import OutreachWorkflow
        from projections.eos.workflows.runner import WorkflowRunner
        wf = OutreachWorkflow()
        lead = {
            "id": "test-1",
            "name": "John",
            "source": "instagram",
            "age_range": "18-25",
            "engagement": True,
            "expressed_interest": "self-improvement",
        }
        runner = WorkflowRunner()
        result = runner.run("outreach", wf.steps(lead), source="test")
        assert result.steps_completed == 3
        assert result.success

    def test_unqualified_lead_stops_early(self):
        from projections.eos.workflows.outreach import OutreachWorkflow
        from projections.eos.workflows.runner import WorkflowRunner
        wf = OutreachWorkflow()
        lead = {"id": "test-2", "name": "Nobody"}
        runner = WorkflowRunner()
        result = runner.run("outreach", wf.steps(lead), source="test")
        assert not result.success
        assert result.steps_completed < 3

    def test_original_execute_still_works(self):
        from projections.eos.workflows.outreach import OutreachWorkflow
        wf = OutreachWorkflow()
        lead = {
            "id": "test-3",
            "name": "Bob",
            "source": "referral",
            "age_range": "25-35",
            "engagement": True,
            "expressed_interest": "fitness",
        }
        result = wf.execute(lead)
        assert result.completed
        assert result.message_draft


class TestFollowUpWorkflowGoverned:

    def test_has_steps_method(self):
        from projections.eos.workflows.followup import FollowUpWorkflow
        wf = FollowUpWorkflow()
        assert hasattr(wf, "steps")

    def test_steps_returns_workflow_steps(self):
        from projections.eos.workflows.followup import FollowUpWorkflow
        from projections.eos.workflows.types import WorkflowStep
        wf = FollowUpWorkflow()
        steps = wf.steps(stale_after_days=7)
        assert len(steps) == 2
        for step in steps:
            assert isinstance(step, WorkflowStep)

    def test_step_names(self):
        from projections.eos.workflows.followup import FollowUpWorkflow
        wf = FollowUpWorkflow()
        names = [s.name for s in wf.steps()]
        assert names == ["check_stale", "generate_followups"]

    def test_executes_through_runner(self):
        from projections.eos.workflows.followup import FollowUpWorkflow
        from projections.eos.workflows.runner import WorkflowRunner
        wf = FollowUpWorkflow()
        runner = WorkflowRunner()
        result = runner.run("followup", wf.steps(), source="test")
        assert result.success
        assert result.steps_completed == 2

    def test_original_method_still_works(self):
        from projections.eos.workflows.followup import FollowUpWorkflow
        wf = FollowUpWorkflow()
        actions = wf.check_stale_leads(stale_after_days=3)
        assert isinstance(actions, list)


class TestContentWorkflowGoverned:

    def test_has_steps_method(self):
        from projections.eos.workflows.content import ContentCalendarWorkflow
        wf = ContentCalendarWorkflow()
        assert hasattr(wf, "steps")

    def test_steps_returns_workflow_steps(self):
        from projections.eos.workflows.content import ContentCalendarWorkflow
        from projections.eos.workflows.types import WorkflowStep
        wf = ContentCalendarWorkflow()
        steps = wf.steps(days=7)
        assert len(steps) == 2
        for step in steps:
            assert isinstance(step, WorkflowStep)

    def test_step_names(self):
        from projections.eos.workflows.content import ContentCalendarWorkflow
        wf = ContentCalendarWorkflow()
        names = [s.name for s in wf.steps()]
        assert names == ["generate_calendar", "ideate_content"]

    def test_executes_through_runner(self):
        from projections.eos.workflows.content import ContentCalendarWorkflow
        from projections.eos.workflows.runner import WorkflowRunner
        wf = ContentCalendarWorkflow()
        runner = WorkflowRunner()
        result = runner.run("content", wf.steps(days=3), source="test")
        assert result.success
        assert result.steps_completed == 2

    def test_original_methods_still_work(self):
        from projections.eos.workflows.content import ContentCalendarWorkflow
        wf = ContentCalendarWorkflow()
        cal = wf.generate_calendar(days=3)
        assert len(cal.pieces) > 0
        piece = wf.ideate("test topic")
        assert piece.channel == "instagram"
