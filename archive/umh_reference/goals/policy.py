"""UMH Goal Policy — enforcement checks for goal task generation."""

from __future__ import annotations

from dataclasses import dataclass

from umh.goals.models import Goal, GoalStatus


@dataclass
class GoalPolicyResult:
    """Result of a goal policy check."""

    allowed: bool
    reason: str = ""

    @staticmethod
    def allow() -> GoalPolicyResult:
        """Return an allowed result."""
        return GoalPolicyResult(allowed=True)

    @staticmethod
    def deny(reason: str) -> GoalPolicyResult:
        """Return a denied result with explanation."""
        return GoalPolicyResult(allowed=False, reason=reason)


def check_goal_policy(goal: Goal) -> GoalPolicyResult:
    """Check if a goal is allowed to generate tasks.

    Evaluates the goal's status and policy constraints.
    Returns a GoalPolicyResult indicating whether evaluation should proceed.
    """
    if goal.status != GoalStatus.ACTIVE:
        return GoalPolicyResult.deny("goal is not active")

    if goal.tasks_created >= goal.policy.max_active_tasks:
        return GoalPolicyResult.deny("max_active_tasks exceeded")

    return GoalPolicyResult.allow()
