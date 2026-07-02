"""P2 Phase 6 — Execution Workflow tests.

Verifies:
1. ExecutionWorkflow produces governed steps for task lifecycle
2. Task definition creates JSON record
3. Completion records outcome
4. Full lifecycle through WorkflowRunner

Run with: pytest tests/test_p2_phase6_execution.py -v
"""

import json
import os
import sys
import tempfile

import pytest

_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _REPO_ROOT)

pytestmark = pytest.mark.smoke


class TestExecutionWorkflowStructure:

    def test_importable(self):
        from projections.eos.workflows.execution import ExecutionWorkflow
        assert ExecutionWorkflow is not None

    def test_define_steps_returns_2(self):
        from projections.eos.workflows.execution import ExecutionWorkflow
        wf = ExecutionWorkflow()
        steps = wf.steps_define("build P2 workflows")
        assert len(steps) == 2
        names = [s.name for s in steps]
        assert names == ["define_task", "record_start"]

    def test_complete_steps_returns_2(self):
        from projections.eos.workflows.execution import ExecutionWorkflow
        wf = ExecutionWorkflow()
        steps = wf.steps_complete("P2 workflows done")
        assert len(steps) == 2
        names = [s.name for s in steps]
        assert names == ["record_completion", "record_outcome"]

    def test_all_steps_have_mutation_names(self):
        from projections.eos.workflows.execution import ExecutionWorkflow
        wf = ExecutionWorkflow()
        for step in wf.steps_define("test") + wf.steps_complete("test"):
            assert step.mutation_name
            assert step.intent


class TestExecutionWorkflowExecution:

    def test_define_task_creates_file(self):
        from projections.eos.workflows import execution as exec_mod
        from projections.eos.workflows.execution import ExecutionWorkflow

        with tempfile.TemporaryDirectory() as tmpdir:
            original = exec_mod._TASKS_DIR
            exec_mod._TASKS_DIR = tmpdir
            try:
                wf = ExecutionWorkflow()
                output, success = wf._define_task("test task creation")
                assert success
                assert "Task defined" in output
                files = os.listdir(tmpdir)
                assert len(files) == 1
                with open(os.path.join(tmpdir, files[0])) as f:
                    data = json.load(f)
                assert data["description"] == "test task creation"
                assert data["status"] == "defined"
            finally:
                exec_mod._TASKS_DIR = original

    def test_record_start_updates_status(self):
        from projections.eos.workflows import execution as exec_mod
        from projections.eos.workflows.execution import ExecutionWorkflow

        with tempfile.TemporaryDirectory() as tmpdir:
            original = exec_mod._TASKS_DIR
            exec_mod._TASKS_DIR = tmpdir
            try:
                wf = ExecutionWorkflow()
                wf._define_task("test start")
                output, success = wf._record_start()
                assert success
                assert wf._task.status == "in_progress"
            finally:
                exec_mod._TASKS_DIR = original

    def test_full_define_through_runner(self):
        from projections.eos.workflows import execution as exec_mod
        from projections.eos.workflows.execution import ExecutionWorkflow
        from projections.eos.workflows.runner import WorkflowRunner

        with tempfile.TemporaryDirectory() as tmpdir:
            original = exec_mod._TASKS_DIR
            exec_mod._TASKS_DIR = tmpdir
            try:
                wf = ExecutionWorkflow()
                runner = WorkflowRunner()
                result = runner.run(
                    "task_define",
                    wf.steps_define("build feature X"),
                    source="test",
                )
                assert result.success
                assert result.steps_completed == 2
            finally:
                exec_mod._TASKS_DIR = original

    def test_full_complete_through_runner(self):
        from projections.eos.workflows import execution as exec_mod
        from projections.eos.workflows.execution import ExecutionWorkflow
        from projections.eos.workflows.runner import WorkflowRunner

        with tempfile.TemporaryDirectory() as tmpdir:
            original = exec_mod._TASKS_DIR
            exec_mod._TASKS_DIR = tmpdir
            try:
                wf = ExecutionWorkflow()
                runner = WorkflowRunner()
                runner.run("task_define", wf.steps_define("test complete"), source="test")
                result = runner.run(
                    "task_complete",
                    wf.steps_complete("feature X shipped"),
                    source="test",
                )
                assert result.steps_completed == 2
            finally:
                exec_mod._TASKS_DIR = original
