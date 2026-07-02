"""P3 Phase 1 — GitHub Workflow tests.

Verifies:
1. GitHubWorkflow produces governed steps for PR/branch operations
2. All steps have mutation names
3. Steps execute through WorkflowRunner (with mocked adapter)

Run with: pytest tests/test_p3_phase1_github.py -v
"""

import os
import sys
from unittest.mock import MagicMock, patch

import pytest

_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _REPO_ROOT)

pytestmark = pytest.mark.smoke


class TestGitHubWorkflowStructure:

    def test_importable(self):
        from projections.eos.workflows.github import GitHubWorkflow
        assert GitHubWorkflow is not None

    def test_pr_list_returns_1_step(self):
        from projections.eos.workflows.github import GitHubWorkflow
        wf = GitHubWorkflow()
        steps = wf.pr_list_steps()
        assert len(steps) == 1
        assert steps[0].name == "list_prs"

    def test_pr_create_returns_1_step(self):
        from projections.eos.workflows.github import GitHubWorkflow
        wf = GitHubWorkflow()
        steps = wf.pr_create_steps("title", "body", "feature-branch")
        assert len(steps) == 1
        assert steps[0].name == "create_pr"

    def test_pr_merge_returns_2_steps(self):
        from projections.eos.workflows.github import GitHubWorkflow
        wf = GitHubWorkflow()
        steps = wf.pr_merge_steps(123)
        assert len(steps) == 2
        assert [s.name for s in steps] == ["check_pr_status", "merge_pr"]

    def test_branch_create_returns_1_step(self):
        from projections.eos.workflows.github import GitHubWorkflow
        wf = GitHubWorkflow()
        steps = wf.branch_create_steps("feature-x")
        assert len(steps) == 1
        assert steps[0].name == "create_branch"

    def test_all_steps_have_mutation_names(self):
        from projections.eos.workflows.github import GitHubWorkflow
        wf = GitHubWorkflow()
        all_steps = (
            wf.pr_list_steps()
            + wf.pr_create_steps("t", "b", "br")
            + wf.pr_merge_steps(1)
            + wf.branch_create_steps("b")
        )
        for step in all_steps:
            assert step.mutation_name, f"{step.name} missing mutation_name"
            assert step.intent, f"{step.name} missing intent"

    def test_mutation_names_are_valid(self):
        from projections.eos.workflows.github import GitHubWorkflow
        wf = GitHubWorkflow()
        valid_mutations = {"command_submit", "git_mutate", "shell_execute"}
        all_steps = (
            wf.pr_list_steps()
            + wf.pr_create_steps("t", "b", "br")
            + wf.pr_merge_steps(1)
            + wf.branch_create_steps("b")
        )
        for step in all_steps:
            assert step.mutation_name in valid_mutations, (
                f"{step.name}: {step.mutation_name} not in {valid_mutations}"
            )


class TestGitHubWorkflowExecution:

    def test_list_prs_empty(self):
        from projections.eos.workflows.github import GitHubWorkflow
        wf = GitHubWorkflow()
        with patch.object(wf._gh, "list_prs", return_value=[]):
            output, success = wf._list_prs("open")
            assert success
            assert "No open PRs" in output

    def test_list_prs_with_results(self):
        from projections.eos.workflows.github import GitHubWorkflow
        wf = GitHubWorkflow()
        mock_prs = [
            {"number": 1, "title": "fix bug", "headRefName": "fix", "baseRefName": "main"},
            {"number": 2, "title": "add feature", "headRefName": "feat", "baseRefName": "main"},
        ]
        with patch.object(wf._gh, "list_prs", return_value=mock_prs):
            output, success = wf._list_prs("open")
            assert success
            assert "2 open PRs" in output
            assert "#1" in output
            assert "#2" in output

    def test_check_pr_status(self):
        from projections.eos.workflows.github import GitHubWorkflow
        wf = GitHubWorkflow()
        mock_status = {"number": 5, "state": "OPEN", "mergeable": "MERGEABLE"}
        with patch.object(wf._gh, "pr_status", return_value=mock_status):
            output, success = wf._check_pr_status(5)
            assert success
            assert "OPEN" in output
            assert "MERGEABLE" in output

    def test_check_pr_status_error(self):
        from projections.eos.workflows.github import GitHubWorkflow
        wf = GitHubWorkflow()
        with patch.object(wf._gh, "pr_status", return_value={"error": "not found"}):
            output, success = wf._check_pr_status(999)
            assert not success
            assert "not found" in output

    def test_create_pr_through_envelope(self):
        from projections.eos.workflows.github import GitHubWorkflow
        wf = GitHubWorkflow()
        mock_envelope = MagicMock()
        mock_envelope.execute_fn.return_value = ("https://github.com/test/pr/1", True)
        with patch.object(wf._gh, "create_pr_envelope", return_value=mock_envelope):
            output, success = wf._create_pr("title", "body", "branch", "main")
            assert success
            assert "github.com" in output

    def test_merge_pr_through_envelope(self):
        from projections.eos.workflows.github import GitHubWorkflow
        wf = GitHubWorkflow()
        mock_envelope = MagicMock()
        mock_envelope.execute_fn.return_value = ("PR #5 merged", True)
        with patch.object(wf._gh, "merge_pr_envelope", return_value=mock_envelope):
            output, success = wf._merge_pr(5)
            assert success
            assert "merged" in output

    def test_pr_list_through_runner(self):
        from projections.eos.workflows.github import GitHubWorkflow
        from projections.eos.workflows.runner import WorkflowRunner
        wf = GitHubWorkflow()
        with patch.object(wf._gh, "list_prs", return_value=[]):
            runner = WorkflowRunner()
            result = runner.run("gh_pr_list", wf.pr_list_steps(), source="test")
            assert result.success
            assert result.steps_completed == 1

    def test_pr_merge_through_runner(self):
        from projections.eos.workflows.github import GitHubWorkflow
        from projections.eos.workflows.runner import WorkflowRunner
        wf = GitHubWorkflow()
        mock_status = {"number": 5, "state": "OPEN", "mergeable": "MERGEABLE"}
        mock_envelope = MagicMock()
        mock_envelope.execute_fn.return_value = ("PR #5 merged", True)
        with patch.object(wf._gh, "pr_status", return_value=mock_status):
            with patch.object(wf._gh, "merge_pr_envelope", return_value=mock_envelope):
                runner = WorkflowRunner()
                result = runner.run("gh_pr_merge", wf.pr_merge_steps(5), source="test")
                assert result.success
                assert result.steps_completed == 2

    def test_exception_in_adapter_returns_failure(self):
        from projections.eos.workflows.github import GitHubWorkflow
        wf = GitHubWorkflow()
        with patch.object(wf._gh, "list_prs", side_effect=RuntimeError("connection failed")):
            output, success = wf._list_prs("open")
            assert not success
            assert "connection failed" in output
