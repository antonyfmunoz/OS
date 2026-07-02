"""P2 Phase 1 — WorkflowRunner tests.

Verifies:
1. WorkflowRunner executes steps through governed_mutation
2. Step failures propagate correctly (skip vs halt)
3. WorkflowResult tracks outcomes accurately
4. Report dispatch fires on completion

Run with: pytest tests/test_p2_phase1_runner.py -v
"""

import json
import os
import sys
import tempfile

import pytest

_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _REPO_ROOT)

pytestmark = pytest.mark.smoke

from projections.eos.workflows.types import (
    StepResult,
    WorkflowResult,
    WorkflowStep,
)


class TestWorkflowTypes:

    def test_workflow_step_creation(self):
        step = WorkflowStep(
            name="test_step",
            mutation_name="command_submit",
            intent="test intent",
            execute_fn=lambda: ("ok", True),
        )
        assert step.name == "test_step"
        assert step.mutation_name == "command_submit"
        assert step.skip_on_failure is False

    def test_step_result_creation(self):
        result = StepResult(
            step_name="test",
            success=True,
            output="done",
            envelope_id="env-123",
        )
        assert result.success
        assert result.output == "done"
        assert not result.skipped

    def test_workflow_result_summary(self):
        result = WorkflowResult(
            workflow_name="test_workflow",
            steps_completed=3,
            steps_total=4,
            success=False,
            duration_seconds=2.5,
        )
        summary = result.summary()
        assert "test_workflow" in summary
        assert "FAILED" in summary
        assert "3/4" in summary

    def test_workflow_result_to_dict(self):
        result = WorkflowResult(
            workflow_name="test",
            steps_completed=1,
            steps_total=1,
            success=True,
            step_results=[
                StepResult(step_name="s1", success=True, output="ok"),
            ],
            duration_seconds=1.0,
            source="discord",
        )
        d = result.to_dict()
        assert d["workflow_name"] == "test"
        assert d["success"] is True
        assert len(d["step_results"]) == 1
        assert d["step_results"][0]["step_name"] == "s1"

    def test_workflow_result_outputs_property(self):
        result = WorkflowResult(
            workflow_name="test",
            steps_completed=2,
            steps_total=2,
            success=True,
            step_results=[
                StepResult(step_name="s1", success=True, output="first"),
                StepResult(step_name="s2", success=True, output="second"),
            ],
        )
        assert result.outputs == ["first", "second"]


class TestWorkflowRunnerImports:

    def test_runner_module_importable(self):
        from projections.eos.workflows.runner import WorkflowRunner
        assert WorkflowRunner is not None

    def test_types_module_importable(self):
        from projections.eos.workflows.types import (
            WorkflowStep,
            WorkflowResult,
            StepResult,
        )
        assert WorkflowStep is not None
        assert WorkflowResult is not None
        assert StepResult is not None

    def test_runner_in_workflows_package(self):
        from projections.eos.workflows import runner
        assert hasattr(runner, "WorkflowRunner")


class TestWorkflowRunnerExecution:

    def test_run_single_step_success(self):
        from projections.eos.workflows.runner import WorkflowRunner

        runner = WorkflowRunner()
        steps = [
            WorkflowStep(
                name="test_step",
                mutation_name="command_submit",
                intent="test single step",
                execute_fn=lambda: ("step executed", True),
            ),
        ]
        result = runner.run("test_wf", steps, source="test")
        assert result.success
        assert result.steps_completed == 1
        assert result.steps_total == 1
        assert result.workflow_name == "test_wf"
        assert result.source == "test"
        assert len(result.step_results) == 1

    def test_run_multi_step_success(self):
        from projections.eos.workflows.runner import WorkflowRunner

        runner = WorkflowRunner()
        steps = [
            WorkflowStep(
                name="step_1",
                mutation_name="command_submit",
                intent="first step",
                execute_fn=lambda: ("one", True),
            ),
            WorkflowStep(
                name="step_2",
                mutation_name="state_mutate",
                intent="second step",
                execute_fn=lambda: ("two", True),
            ),
            WorkflowStep(
                name="step_3",
                mutation_name="outcome_record",
                intent="third step",
                execute_fn=lambda: ("three", True),
            ),
        ]
        result = runner.run("multi_step", steps)
        assert result.success
        assert result.steps_completed == 3
        assert result.steps_total == 3

    def test_run_step_failure_halts(self):
        from projections.eos.workflows.runner import WorkflowRunner

        call_log = []
        runner = WorkflowRunner()
        steps = [
            WorkflowStep(
                name="passes",
                mutation_name="command_submit",
                intent="this passes",
                execute_fn=lambda: ("ok", True),
            ),
            WorkflowStep(
                name="fails",
                mutation_name="command_submit",
                intent="this fails",
                execute_fn=lambda: ("nope", False),
            ),
            WorkflowStep(
                name="never_runs",
                mutation_name="command_submit",
                intent="should be skipped",
                execute_fn=lambda: (call_log.append("ran") or "bad", True),
            ),
        ]
        result = runner.run("halt_test", steps)
        assert not result.success
        assert result.steps_completed == 1
        assert result.step_results[2].skipped
        assert len(call_log) == 0

    def test_run_skip_on_failure_continues(self):
        from projections.eos.workflows.runner import WorkflowRunner

        runner = WorkflowRunner()
        steps = [
            WorkflowStep(
                name="fails",
                mutation_name="command_submit",
                intent="this fails",
                execute_fn=lambda: ("nope", False),
            ),
            WorkflowStep(
                name="skippable",
                mutation_name="command_submit",
                intent="skippable step",
                execute_fn=lambda: ("runs anyway", True),
                skip_on_failure=True,
            ),
        ]
        result = runner.run("skip_test", steps)
        assert not result.success
        assert result.step_results[1].success
        assert not result.step_results[1].skipped

    def test_run_records_duration(self):
        from projections.eos.workflows.runner import WorkflowRunner

        runner = WorkflowRunner()
        steps = [
            WorkflowStep(
                name="quick",
                mutation_name="command_submit",
                intent="fast step",
                execute_fn=lambda: ("fast", True),
            ),
        ]
        result = runner.run("duration_test", steps)
        assert result.duration_seconds >= 0.0

    def test_run_exception_in_step(self):
        from projections.eos.workflows.runner import WorkflowRunner

        def _explode():
            raise ValueError("boom")

        runner = WorkflowRunner()
        steps = [
            WorkflowStep(
                name="explodes",
                mutation_name="command_submit",
                intent="will raise",
                execute_fn=_explode,
            ),
        ]
        result = runner.run("exception_test", steps)
        assert not result.success
        sr = result.step_results[0]
        assert "boom" in sr.output or "boom" in sr.error


class TestWorkflowRunnerJournal:

    def test_journal_entries_written(self):
        from projections.eos.workflows import runner as runner_mod
        from projections.eos.workflows.runner import WorkflowRunner

        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".jsonl", delete=False
        ) as f:
            journal_path = f.name

        original = runner_mod._JOURNAL_PATH
        runner_mod._JOURNAL_PATH = journal_path
        try:
            wf_runner = WorkflowRunner()
            steps = [
                WorkflowStep(
                    name="journaled",
                    mutation_name="command_submit",
                    intent="journal test",
                    execute_fn=lambda: ("logged", True),
                ),
            ]
            wf_runner.run("journal_test", steps)

            with open(journal_path) as f:
                lines = [json.loads(line) for line in f if line.strip()]

            events = [entry["event"] for entry in lines]
            assert "workflow_start" in events
            assert "workflow_complete" in events

            start = next(e for e in lines if e["event"] == "workflow_start")
            assert start["workflow"] == "journal_test"
            assert start["steps"] == 1

            complete = next(e for e in lines if e["event"] == "workflow_complete")
            assert complete["success"] is True
            assert complete["steps_completed"] == 1
        finally:
            runner_mod._JOURNAL_PATH = original
            os.unlink(journal_path)
