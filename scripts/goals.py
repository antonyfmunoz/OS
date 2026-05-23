#!/usr/bin/env python3
"""CLI entry points for goal management. Wraps runtime/goal_selector.py."""

import os
import sys

_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

from substrate.control_plane.goals.goal_selector import GoalSelector, GoalState
import json


def _sel() -> GoalSelector:
    budget = int(os.getenv("GOAL_FOCUS_BUDGET", "3"))
    return GoalSelector(focus_budget=budget)


def cmd_goals():
    """List all goals with state and score."""
    sel = _sel()
    goals = sel.list_goals()
    if not goals:
        print("No goals.")
        return
    for g in goals:
        marker = "●" if g.state == GoalState.ACTIVE else "○"
        print(
            f"  {marker} [{g.id}] {g.title}  "
            f"state={g.state.value}  score={g.score:.3f}  rank={g.rank}"
        )


def cmd_goal_add(
    title: str,
    priority: int = 5,
    impact: float = 0.5,
    cost: float = 0.5,
    confidence: float = 0.5,
    venture: str | None = None,
):
    """Add a new goal."""
    sel = _sel()
    goal = sel.add_goal(
        title=title,
        priority=priority,
        expected_impact=impact,
        estimated_cost=cost,
        confidence=confidence,
        venture_id=venture,
    )
    print(f"Created [{goal.id}]: {goal.title}  state={goal.state.value}")
    return goal


def cmd_goal_activate(goal_id: str):
    """Force-activate a goal."""
    sel = _sel()
    goal = sel.activate(goal_id)
    print(f"Activated [{goal.id}]: {goal.title}")
    return goal


def cmd_goal_defer(goal_id: str):
    """Defer a goal."""
    sel = _sel()
    goal = sel.defer(goal_id)
    print(f"Deferred [{goal.id}]: {goal.title}")
    return goal


def cmd_goal_cycle():
    """Run selection cycle."""
    sel = _sel()
    active = sel.run_selection_cycle()
    print(f"Selection cycle complete. {len(active)} active goals:")
    for g in active:
        print(f"  ● [{g.id}] {g.title}  score={g.score:.3f}")
    return active


def cmd_goal_explain(goal_id: str):
    """Explain scoring for a goal."""
    sel = _sel()
    goal = sel.get_goal(goal_id)
    sel.score_goal(goal, sel.load_goals())
    info = sel.explain(goal)
    print(json.dumps(info, indent=2))
    return info


if __name__ == "__main__":
    if len(sys.argv) < 2:
        cmd_goals()
    else:
        cmd = sys.argv[1]
        if cmd == "add" and len(sys.argv) >= 3:
            cmd_goal_add(title=" ".join(sys.argv[2:]))
        elif cmd == "activate" and len(sys.argv) >= 3:
            cmd_goal_activate(sys.argv[2])
        elif cmd == "defer" and len(sys.argv) >= 3:
            cmd_goal_defer(sys.argv[2])
        elif cmd == "cycle":
            cmd_goal_cycle()
        elif cmd == "explain" and len(sys.argv) >= 3:
            cmd_goal_explain(sys.argv[2])
        else:
            print("Usage: goals.py [add|activate|defer|cycle|explain] [args]")
