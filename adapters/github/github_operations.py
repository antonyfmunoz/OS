"""GitHub Operations — governed write operations for GitHub via gh CLI.

Wraps PR creation, merging, and branch management as ActionEnvelopes
for submission to GovernedExecutionSpine. Read-only operations (list, view)
are direct calls without governance overhead.

UMH adapter layer. Instance-agnostic.
"""

from __future__ import annotations

import json
import logging
import os
from typing import Any

from substrate.execution.cpu_gate import gated_subprocess_run
from substrate.organism.action_envelope import (
    ActionEnvelope,
    ActionType,
    BlastRadius,
    ExecutionConstraints,
    ReversibilityClass,
    RollbackStrategy,
)

logger = logging.getLogger(__name__)

_REPO_ROOT = os.environ.get("UMH_ROOT", "/opt/OS")


class GitHubOperations:
    """Governed GitHub write operations via gh CLI."""

    def __init__(self, repo: str = "") -> None:
        # Repo is instance context — resolve from env, never hardcode an owner/repo.
        if not repo:
            from substrate.state.business.business_instance import get_github_repo

            repo = get_github_repo()
        self._repo = repo
        self._ops_count = 0
        self._last_pr: int | None = None

    def create_pr_envelope(
        self,
        title: str,
        body: str,
        head_branch: str,
        base_branch: str = "main",
    ) -> ActionEnvelope:
        """Create an ActionEnvelope that opens a PR when executed."""

        def _execute() -> tuple[str, bool]:
            result = gated_subprocess_run(
                [
                    "gh",
                    "pr",
                    "create",
                    "--repo",
                    self._repo,
                    "--title",
                    title,
                    "--body",
                    body,
                    "--head",
                    head_branch,
                    "--base",
                    base_branch,
                ],
                capture_output=True,
                text=True,
                cwd=_REPO_ROOT,
                caller="github_operations.create_pr",
            )
            if result is None:
                return "CPU gate blocked PR creation", False
            if result.returncode != 0:
                msg = (result.stderr or result.stdout or "unknown error")[:200]
                logger.debug("gh pr create failed: %s", msg)
                return msg, False
            self._ops_count += 1
            return result.stdout.strip(), True

        return ActionEnvelope(
            intent=f"Create PR: {title}",
            action_type=ActionType.STATE,
            source="github_operations",
            execute_fn=_execute,
            risk_level="medium",
            blast_radius=BlastRadius.EXTERNAL,
            reversibility=ReversibilityClass.PARTIALLY_REVERSIBLE,
            constraints=ExecutionConstraints(require_approval=True),
            metadata={"repo": self._repo, "head": head_branch, "base": base_branch},
        )

    def merge_pr_envelope(self, pr_number: int) -> ActionEnvelope:
        """Create an ActionEnvelope that merges a PR when executed."""

        def _execute() -> tuple[str, bool]:
            result = gated_subprocess_run(
                [
                    "gh",
                    "pr",
                    "merge",
                    str(pr_number),
                    "--repo",
                    self._repo,
                    "--merge",
                    "--delete-branch",
                ],
                capture_output=True,
                text=True,
                cwd=_REPO_ROOT,
                caller="github_operations.merge_pr",
            )
            if result is None:
                return "CPU gate blocked PR merge", False
            if result.returncode != 0:
                msg = (result.stderr or result.stdout or "unknown error")[:200]
                logger.debug("gh pr merge failed: %s", msg)
                return msg, False
            self._ops_count += 1
            self._last_pr = pr_number
            return f"PR #{pr_number} merged", True

        return ActionEnvelope(
            intent=f"Merge PR #{pr_number}",
            action_type=ActionType.STATE,
            source="github_operations",
            execute_fn=_execute,
            risk_level="medium",
            blast_radius=BlastRadius.EXTERNAL,
            reversibility=ReversibilityClass.PARTIALLY_REVERSIBLE,
            constraints=ExecutionConstraints(require_approval=True),
            metadata={"repo": self._repo, "pr_number": pr_number},
        )

    def create_branch_envelope(self, branch_name: str, base: str = "main") -> ActionEnvelope:
        """Create an ActionEnvelope that creates a git branch when executed."""

        def _execute() -> tuple[str, bool]:
            result = gated_subprocess_run(
                ["git", "checkout", "-b", branch_name, base],
                capture_output=True,
                text=True,
                cwd=_REPO_ROOT,
                caller="github_operations.create_branch",
            )
            if result is None:
                return "CPU gate blocked branch creation", False
            if result.returncode != 0:
                msg = (result.stderr or result.stdout or "unknown error")[:200]
                logger.debug("git checkout -b failed: %s", msg)
                return msg, False
            self._ops_count += 1
            return f"Branch {branch_name} created from {base}", True

        return ActionEnvelope(
            intent=f"Create branch: {branch_name} from {base}",
            action_type=ActionType.FILESYSTEM,
            source="github_operations",
            execute_fn=_execute,
            risk_level="low",
            blast_radius=BlastRadius.LOCAL_RUNTIME,
            reversibility=ReversibilityClass.FULLY_REVERSIBLE,
            constraints=ExecutionConstraints(require_approval=False),
            rollback=RollbackStrategy(
                description=f"Delete branch {branch_name}",
            ),
            metadata={"branch": branch_name, "base": base},
        )

    def list_prs(self, state: str = "open") -> list[dict[str, Any]]:
        """List PRs (read-only, no governance needed)."""
        result = gated_subprocess_run(
            [
                "gh",
                "pr",
                "list",
                "--repo",
                self._repo,
                "--state",
                state,
                "--json",
                "number,title,state,headRefName,baseRefName,url",
            ],
            capture_output=True,
            text=True,
            cwd=_REPO_ROOT,
            caller="github_operations.list_prs",
        )
        if result is None or result.returncode != 0:
            logger.debug("gh pr list failed: %s", getattr(result, "stderr", "gated"))
            return []
        try:
            return json.loads(result.stdout)
        except (json.JSONDecodeError, TypeError) as exc:
            logger.debug("Failed to parse PR list: %s", exc)
            return []

    def pr_status(self, pr_number: int) -> dict[str, Any]:
        """Get PR details (read-only, no governance needed)."""
        result = gated_subprocess_run(
            [
                "gh",
                "pr",
                "view",
                str(pr_number),
                "--repo",
                self._repo,
                "--json",
                "number,title,state,mergeable,reviewDecision,url",
            ],
            capture_output=True,
            text=True,
            cwd=_REPO_ROOT,
            caller="github_operations.pr_status",
        )
        if result is None or result.returncode != 0:
            logger.debug("gh pr view failed: %s", getattr(result, "stderr", "gated"))
            return {"error": "failed to fetch PR status"}
        try:
            return json.loads(result.stdout)
        except (json.JSONDecodeError, TypeError) as exc:
            logger.debug("Failed to parse PR status: %s", exc)
            return {"error": str(exc)}

    def to_dict(self) -> dict[str, Any]:
        """Summary of operations performed."""
        return {
            "repo": self._repo,
            "operations_count": self._ops_count,
            "last_pr": self._last_pr,
        }
