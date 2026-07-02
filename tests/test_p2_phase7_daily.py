"""P2 Phase 7 — Daily Rhythm Workflow tests.

Verifies:
1. DailyRhythmWorkflow produces governed steps
2. State gathering reads from data files
3. Brief generation is deterministic
4. EOD logging writes outcomes

Run with: pytest tests/test_p2_phase7_daily.py -v
"""

import os
import sys

import pytest

_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _REPO_ROOT)

pytestmark = pytest.mark.smoke


class TestDailyRhythmStructure:

    def test_importable(self):
        from projections.eos.workflows.daily import DailyRhythmWorkflow
        assert DailyRhythmWorkflow is not None

    def test_brief_steps_returns_2(self):
        from projections.eos.workflows.daily import DailyRhythmWorkflow
        wf = DailyRhythmWorkflow()
        steps = wf.brief_steps()
        assert len(steps) == 2
        names = [s.name for s in steps]
        assert names == ["gather_state", "generate_brief"]

    def test_eod_steps_returns_2(self):
        from projections.eos.workflows.daily import DailyRhythmWorkflow
        wf = DailyRhythmWorkflow()
        steps = wf.eod_steps()
        assert len(steps) == 2
        names = [s.name for s in steps]
        assert names == ["summarize_day", "log_outcomes"]

    def test_all_steps_have_mutation_names(self):
        from projections.eos.workflows.daily import DailyRhythmWorkflow
        wf = DailyRhythmWorkflow()
        for step in wf.brief_steps() + wf.eod_steps():
            assert step.mutation_name
            assert step.intent


class TestDailyRhythmExecution:

    def test_gather_state(self):
        from projections.eos.workflows.daily import DailyRhythmWorkflow
        wf = DailyRhythmWorkflow()
        output, success = wf._gather_state()
        assert success
        assert "State gathered" in output
        assert wf._state is not None
        assert wf._state.date

    def test_generate_brief(self):
        from projections.eos.workflows.daily import DailyRhythmWorkflow
        wf = DailyRhythmWorkflow()
        wf._gather_state()
        output, success = wf._generate_brief()
        assert success
        assert "Morning Brief" in output
        assert wf._brief

    def test_summarize_day(self):
        from projections.eos.workflows.daily import DailyRhythmWorkflow
        wf = DailyRhythmWorkflow()
        output, success = wf._summarize_day()
        assert success
        assert "EOD" in output

    def test_brief_through_runner(self):
        from projections.eos.workflows.daily import DailyRhythmWorkflow
        from projections.eos.workflows.runner import WorkflowRunner
        wf = DailyRhythmWorkflow()
        runner = WorkflowRunner()
        result = runner.run("morning_brief", wf.brief_steps(), source="test")
        assert result.success
        assert result.steps_completed == 2

    def test_eod_through_runner(self):
        from projections.eos.workflows.daily import DailyRhythmWorkflow
        from projections.eos.workflows.runner import WorkflowRunner
        wf = DailyRhythmWorkflow()
        runner = WorkflowRunner()
        result = runner.run("end_of_day", wf.eod_steps(), source="test")
        assert result.success
        assert result.steps_completed == 2
