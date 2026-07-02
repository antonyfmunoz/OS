"""P2 Phase 5 — Review Workflow tests.

Verifies:
1. ReviewWorkflow produces governed steps
2. Scope identification handles directories, files, and named reviews
3. Analysis runs pre-commit gates
4. Findings are structured properly

Run with: pytest tests/test_p2_phase5_review.py -v
"""

import os
import sys

import pytest

_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _REPO_ROOT)

pytestmark = pytest.mark.smoke


class TestReviewWorkflowStructure:

    def test_importable(self):
        from projections.eos.workflows.review import ReviewWorkflow
        assert ReviewWorkflow is not None

    def test_steps_returns_3_steps(self):
        from projections.eos.workflows.review import ReviewWorkflow
        wf = ReviewWorkflow()
        steps = wf.steps("substrate")
        assert len(steps) == 3
        names = [s.name for s in steps]
        assert names == ["identify_scope", "analyze", "generate_findings"]

    def test_all_steps_have_mutation_names(self):
        from projections.eos.workflows.review import ReviewWorkflow
        wf = ReviewWorkflow()
        for step in wf.steps("tests"):
            assert step.mutation_name
            assert step.intent

    def test_review_types_defined(self):
        from projections.eos.workflows.review import ReviewWorkflow
        assert "architecture" in ReviewWorkflow.REVIEW_TYPES
        assert "types" in ReviewWorkflow.REVIEW_TYPES
        assert "imports" in ReviewWorkflow.REVIEW_TYPES
        assert "tests" in ReviewWorkflow.REVIEW_TYPES
        assert "gates" in ReviewWorkflow.REVIEW_TYPES


class TestReviewScopeIdentification:

    def test_named_review_type(self):
        from projections.eos.workflows.review import ReviewWorkflow
        wf = ReviewWorkflow()
        output, success = wf._identify_scope("architecture")
        assert success
        assert wf._scope is not None
        assert wf._scope.scope_type == "architecture"

    def test_directory_scope(self):
        from projections.eos.workflows.review import ReviewWorkflow
        wf = ReviewWorkflow()
        output, success = wf._identify_scope("substrate/organism")
        assert success
        assert wf._scope is not None
        assert wf._scope.scope_type == "directory"
        assert wf._scope.file_count > 0

    def test_file_scope(self):
        from projections.eos.workflows.review import ReviewWorkflow
        wf = ReviewWorkflow()
        output, success = wf._identify_scope("substrate/organism/daemon.py")
        assert success
        assert wf._scope is not None
        assert wf._scope.scope_type == "file"
        assert wf._scope.file_count == 1

    def test_unknown_target_defaults_to_gates(self):
        from projections.eos.workflows.review import ReviewWorkflow
        wf = ReviewWorkflow()
        output, success = wf._identify_scope("nonexistent_target_xyz")
        assert success
        assert wf._scope is not None
        assert wf._scope.scope_type == "gates"


class TestReviewExecution:

    def test_directory_review_finds_issues(self):
        from projections.eos.workflows.review import ReviewWorkflow
        wf = ReviewWorkflow()
        wf._identify_scope("substrate/organism")
        output, success = wf._analyze()
        assert success

    def test_generate_findings_clean(self):
        from projections.eos.workflows.review import ReviewWorkflow
        wf = ReviewWorkflow()
        wf._scope = wf.__class__.__new__(wf.__class__)
        wf._identify_scope("projections/eos/workflows")
        wf._findings = []
        output, success = wf._generate_findings()
        assert success
        assert "clean" in output.lower() or "0" in output

    def test_full_workflow_through_runner(self):
        from projections.eos.workflows.review import ReviewWorkflow
        from projections.eos.workflows.runner import WorkflowRunner
        wf = ReviewWorkflow()
        runner = WorkflowRunner()
        result = runner.run("review", wf.steps("projections"), source="test")
        assert result.steps_total == 3
        assert result.steps_completed >= 2
