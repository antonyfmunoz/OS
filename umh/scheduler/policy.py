"""UMH Scheduler Policy — enforcement checks for scheduled workflow execution."""

from __future__ import annotations

from dataclasses import dataclass

from umh.scheduler.models import ScheduledWorkflow


@dataclass
class PolicyResult:
    """Result of a policy check."""

    allowed: bool
    reason: str = ""

    @staticmethod
    def allow() -> PolicyResult:
        """Return an allowed result."""
        return PolicyResult(allowed=True)

    @staticmethod
    def deny(reason: str) -> PolicyResult:
        """Return a denied result with explanation."""
        return PolicyResult(allowed=False, reason=reason)


def check_policy(workflow: ScheduledWorkflow) -> PolicyResult:
    """Check if a scheduled workflow is allowed to run now.

    Evaluates the workflow's policy constraints and current state.
    Returns a PolicyResult indicating whether execution should proceed.
    """
    if not workflow.enabled:
        return PolicyResult.deny("schedule is disabled")

    policy = workflow.policy

    if workflow.run_count >= policy.max_runs_per_day:
        return PolicyResult.deny(f"max_runs_per_day ({policy.max_runs_per_day}) exceeded")

    return PolicyResult.allow()
