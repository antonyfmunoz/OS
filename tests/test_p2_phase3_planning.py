"""P2 Phase 3 — Planning Workflow tests.

Verifies:
1. PlanningWorkflow produces governed steps
2. State assessment reads from data files
3. Gap identification is deterministic
4. Plan creation writes to filesystem

Run with: pytest tests/test_p2_phase3_planning.py -v
"""

import os
import sys
import tempfile

import pytest

_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _REPO_ROOT)

pytestmark = pytest.mark.smoke


class TestPlanningWorkflowStructure:

    def test_importable(self):
        from projections.eos.workflows.planning import PlanningWorkflow
        assert PlanningWorkflow is not None

    def test_steps_returns_4_steps(self):
        from projections.eos.workflows.planning import PlanningWorkflow
        wf = PlanningWorkflow()
        steps = wf.steps("reach $10K/month revenue")
        assert len(steps) == 4
        names = [s.name for s in steps]
        assert names == [
            "assess_current_state", "identify_gaps",
            "generate_options", "create_plan",
        ]

    def test_all_steps_have_mutation_names(self):
        from projections.eos.workflows.planning import PlanningWorkflow
        wf = PlanningWorkflow()
        for step in wf.steps("test goal"):
            assert step.mutation_name
            assert step.intent


class TestPlanningWorkflowExecution:

    def test_assess_state(self):
        from projections.eos.workflows.planning import PlanningWorkflow
        wf = PlanningWorkflow()
        output, success = wf._assess_state("reach revenue target")
        assert success
        assert "State assessed" in output
        assert wf._assessment is not None

    def test_identify_gaps_revenue(self):
        from projections.eos.workflows.planning import PlanningWorkflow
        wf = PlanningWorkflow()
        wf._assess_state("get first sale and revenue")
        output, success = wf._identify_gaps()
        assert success
        assert len(wf._gaps) > 0
        assert any("revenue" in g.lower() or "lead" in g.lower() for g in wf._gaps)

    def test_identify_gaps_content(self):
        from projections.eos.workflows.planning import PlanningWorkflow
        wf = PlanningWorkflow()
        wf._assess_state("build personal brand content")
        output, success = wf._identify_gaps()
        assert success
        assert any("content" in g.lower() for g in wf._gaps)

    def test_generate_options(self):
        from projections.eos.workflows.planning import PlanningWorkflow
        wf = PlanningWorkflow()
        wf._assess_state("ship MVP")
        wf._identify_gaps()
        output, success = wf._generate_options()
        assert success
        assert len(wf._options) >= 3

    def test_create_plan_writes_file(self):
        from projections.eos.workflows import planning as planning_mod
        from projections.eos.workflows.planning import PlanningWorkflow

        with tempfile.TemporaryDirectory() as tmpdir:
            original = planning_mod._PLANS_DIR
            planning_mod._PLANS_DIR = tmpdir
            try:
                wf = PlanningWorkflow()
                wf._assess_state("test plan")
                wf._identify_gaps()
                wf._generate_options()
                output, success = wf._create_plan()
                assert success
                files = os.listdir(tmpdir)
                assert len(files) == 1
                assert files[0].endswith(".md")
                with open(os.path.join(tmpdir, files[0])) as f:
                    content = f.read()
                assert "test plan" in content.lower()
            finally:
                planning_mod._PLANS_DIR = original

    def test_full_workflow_through_runner(self):
        from projections.eos.workflows import planning as planning_mod
        from projections.eos.workflows.planning import PlanningWorkflow
        from projections.eos.workflows.runner import WorkflowRunner

        with tempfile.TemporaryDirectory() as tmpdir:
            original = planning_mod._PLANS_DIR
            planning_mod._PLANS_DIR = tmpdir
            try:
                wf = PlanningWorkflow()
                runner = WorkflowRunner()
                result = runner.run(
                    "planning", wf.steps("ship MVP"), source="test"
                )
                assert result.steps_total == 4
                assert result.steps_completed >= 3
            finally:
                planning_mod._PLANS_DIR = original
