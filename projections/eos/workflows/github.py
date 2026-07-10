"""GitHub workflow — governed PR and branch operations.

Wraps the existing GitHubOperations adapter so all GitHub mutations
flow through governed_mutation and the organism tracks them.

Step-sets:
- pr_list_steps: list open PRs (read-only, governed for tracking)
- pr_create_steps: create a PR through governed mutation
- pr_merge_steps: merge a PR through governed mutation
- branch_create_steps: create a branch through governed mutation
"""

from __future__ import annotations

import json
import logging
from typing import Any

from adapters.github.github_operations import GitHubOperations
from projections.eos.workflows.types import WorkflowStep

logger = logging.getLogger(__name__)


class GitHubWorkflow:
    """GitHub operations through governed mutation."""

    def __init__(self, repo: str = "") -> None:
        # Empty repo → GitHubOperations resolves it from tenant BIS (get_github_repo).
        self._gh = GitHubOperations(repo=repo)
        self._pr_list: list[dict[str, Any]] = []
        self._pr_status: dict[str, Any] = {}

    def pr_list_steps(self, state: str = "open") -> list[WorkflowStep]:
        """Steps to list PRs (read-only, governed for tracking)."""
        return [
            WorkflowStep(
                name="list_prs",
                mutation_name="command_submit",
                intent=f"List {state} PRs",
                execute_fn=lambda: self._list_prs(state),
            ),
        ]

    def pr_create_steps(
        self,
        title: str,
        body: str,
        head_branch: str,
        base_branch: str = "main",
    ) -> list[WorkflowStep]:
        """Steps to create a PR through governed mutation."""
        return [
            WorkflowStep(
                name="create_pr",
                mutation_name="git_mutate",
                intent=f"Create PR: {title[:80]}",
                execute_fn=lambda: self._create_pr(
                    title, body, head_branch, base_branch
                ),
            ),
        ]

    def pr_merge_steps(self, pr_number: int) -> list[WorkflowStep]:
        """Steps to merge a PR through governed mutation."""
        return [
            WorkflowStep(
                name="check_pr_status",
                mutation_name="command_submit",
                intent=f"Check PR #{pr_number} status before merge",
                execute_fn=lambda: self._check_pr_status(pr_number),
            ),
            WorkflowStep(
                name="merge_pr",
                mutation_name="git_mutate",
                intent=f"Merge PR #{pr_number}",
                execute_fn=lambda: self._merge_pr(pr_number),
            ),
        ]

    def branch_create_steps(
        self, branch_name: str, base: str = "main"
    ) -> list[WorkflowStep]:
        """Steps to create a branch through governed mutation."""
        return [
            WorkflowStep(
                name="create_branch",
                mutation_name="git_mutate",
                intent=f"Create branch: {branch_name} from {base}",
                execute_fn=lambda: self._create_branch(branch_name, base),
            ),
        ]

    def _list_prs(self, state: str) -> tuple[str, bool]:
        try:
            prs = self._gh.list_prs(state=state)
            self._pr_list = prs
            if not prs:
                return (f"No {state} PRs found", True)
            lines = [f"**{len(prs)} {state} PRs:**"]
            for pr in prs:
                lines.append(
                    f"  #{pr.get('number', '?')} — {pr.get('title', 'untitled')} "
                    f"({pr.get('headRefName', '?')} → {pr.get('baseRefName', '?')})"
                )
            return ("\n".join(lines), True)
        except Exception as exc:
            logger.debug("list_prs failed: %s", exc)
            return (f"Failed to list PRs: {exc}", False)

    def _create_pr(
        self,
        title: str,
        body: str,
        head_branch: str,
        base_branch: str,
    ) -> tuple[str, bool]:
        try:
            envelope = self._gh.create_pr_envelope(
                title=title, body=body, head_branch=head_branch, base_branch=base_branch
            )
            return envelope.execute_fn()
        except Exception as exc:
            logger.debug("create_pr failed: %s", exc)
            return (f"Failed to create PR: {exc}", False)

    def _check_pr_status(self, pr_number: int) -> tuple[str, bool]:
        try:
            status = self._gh.pr_status(pr_number)
            self._pr_status = status
            if "error" in status:
                return (f"PR #{pr_number}: {status['error']}", False)
            state = status.get("state", "unknown")
            mergeable = status.get("mergeable", "UNKNOWN")
            return (
                f"PR #{pr_number}: state={state}, mergeable={mergeable}",
                True,
            )
        except Exception as exc:
            logger.debug("pr_status failed: %s", exc)
            return (f"Failed to check PR #{pr_number}: {exc}", False)

    def _merge_pr(self, pr_number: int) -> tuple[str, bool]:
        try:
            envelope = self._gh.merge_pr_envelope(pr_number)
            return envelope.execute_fn()
        except Exception as exc:
            logger.debug("merge_pr failed: %s", exc)
            return (f"Failed to merge PR #{pr_number}: {exc}", False)

    def _create_branch(self, branch_name: str, base: str) -> tuple[str, bool]:
        try:
            envelope = self._gh.create_branch_envelope(branch_name, base=base)
            return envelope.execute_fn()
        except Exception as exc:
            logger.debug("create_branch failed: %s", exc)
            return (f"Failed to create branch: {exc}", False)
