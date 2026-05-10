"""
ExecutionLoop — closed-loop goal execution with outcome feedback.

The reality bridge: connects goal selection → planning → execution →
outcome recording → automatic reselection into a single deterministic
cycle.

Core rule: ONLY the Executor can act. Everything else selects, plans,
or observes.

Usage:
    from eos_ai.execution_loop import ExecutionLoop

    loop = ExecutionLoop()
    loop.run(cycles=10)

CLI:
    python3 -m eos_ai.execution_loop --cycles 10
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Callable, Protocol

import os
_REPO_ROOT = os.environ.get("UMH_ROOT") or os.environ.get("OS_ROOT") or os.environ.get("EOS_ROOT") or "/opt/OS"
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

from eos_ai.goal_selector import Goal, GoalSelector, GoalState, OutcomeTracker


# ─── ExecutionResult ─────────────────────────────────────────────────────────


@dataclass
class ExecutionResult:
    """Outcome of a single goal execution attempt."""

    success: bool
    output: dict = field(default_factory=dict)
    error: str | None = None
    execution_time: float = 0.0
    impact_delta: float = 0.0


# ─── Executor Protocol ───────────────────────────────────────────────────────


class Executor(Protocol):
    """Single-writer contract: only execute() may produce side effects."""

    def execute(self, goal: Goal, plan: dict) -> ExecutionResult: ...


# ─── Planner Protocol ────────────────────────────────────────────────────────


class Planner(Protocol):
    """Plan creation is read-only: no state mutation, no side effects."""

    def create_plan(self, goal: Goal) -> dict: ...


# ─── Default Planner (pass-through) ──────────────────────────────────────────


class PassthroughPlanner:
    """Minimal planner that forwards goal metadata as the plan.

    Real planners (LLM, substrate) plug in via the Planner protocol.
    """

    def create_plan(self, goal: Goal) -> dict:
        return {
            "goal_id": goal.id,
            "title": goal.title,
            "priority": goal.priority,
            "expected_impact": goal.expected_impact,
            "venture_id": goal.venture_id,
        }


# ─── Default Executor (no-op proof) ─────────────────────────────────────────


class NoOpExecutor:
    """Executor that always succeeds without side effects.

    Used for testing and proving the loop wiring works.
    Replace with real executor for production.
    """

    def execute(self, goal: Goal, plan: dict) -> ExecutionResult:
        return ExecutionResult(
            success=True,
            output={"action": "noop", "plan": plan},
            execution_time=0.0,
        )


# ─── Cycle Result ────────────────────────────────────────────────────────────


@dataclass
class CycleResult:
    """Summary of a single execution cycle."""

    cycle: int
    active_goals: list[str]
    results: dict[str, ExecutionResult]
    reselected: list[str]
    timestamp: str = ""


# ─── ExecutionLoop ───────────────────────────────────────────────────────────


class ExecutionLoop:
    """Closed-loop execution: select → plan → execute → record → reselect.

    Hard constraints:
    - No parallel execution
    - No agent mutation
    - No randomness in selection
    - Execution failures do NOT crash the loop
    - Each cycle is deterministic given inputs
    """

    def __init__(
        self,
        selector: GoalSelector | None = None,
        planner: Planner | None = None,
        executor: Executor | None = None,
        outcome_tracker: OutcomeTracker | None = None,
        event_publisher: Callable[[str, dict], Any] | None = None,
    ) -> None:
        self.selector = selector or GoalSelector()
        self.planner = planner or PassthroughPlanner()
        self.executor = executor or NoOpExecutor()
        self.outcomes = outcome_tracker or OutcomeTracker()
        self._publish = event_publisher or self._default_publish
        self._cycle_history: list[CycleResult] = []

    @staticmethod
    def _default_publish(event_type: str, payload: dict) -> None:
        try:
            from eos_ai.event_bus import get_bus

            get_bus().publish(event_type, payload)
        except Exception as e:
            print(f"[ExecutionLoop] event publish failed: {e}")

    # ─── Single cycle ────────────────────────────────────────────────────────

    def run_cycle(self, cycle_num: int = 0) -> CycleResult:
        """Execute one full cycle: select → plan → execute → record → reselect."""
        ts = datetime.now(timezone.utc).isoformat()

        # 1. Select active goals
        active_goals = self.selector.run_selection_cycle()
        active_ids = [g.id for g in active_goals]

        # 2. Execute each active goal sequentially
        results: dict[str, ExecutionResult] = {}
        for goal in active_goals:
            result = self._execute_goal(goal)
            results[goal.id] = result

        # 3. Reselect after all outcomes are recorded
        reselected = self.selector.run_selection_cycle()
        reselected_ids = [g.id for g in reselected]

        cycle_result = CycleResult(
            cycle=cycle_num,
            active_goals=active_ids,
            results=results,
            reselected=reselected_ids,
            timestamp=ts,
        )
        self._cycle_history.append(cycle_result)
        return cycle_result

    def _execute_goal(self, goal: Goal) -> ExecutionResult:
        """Plan → execute → record outcome for a single goal."""
        t0 = time.monotonic()

        # Plan (read-only)
        try:
            plan = self.planner.create_plan(goal)
        except Exception as e:
            plan = {"error": f"planning failed: {e}"}

        # Execute (ONLY mutation point)
        try:
            result = self.executor.execute(goal, plan)
            result.execution_time = time.monotonic() - t0
        except Exception as e:
            result = ExecutionResult(
                success=False,
                error=str(e),
                execution_time=time.monotonic() - t0,
            )

        # Record outcome (feeds back into scoring)
        outcome_type = "success" if result.success else "failure"
        try:
            self.outcomes.record_outcome(
                goal_id=goal.id,
                outcome_type=outcome_type,
                execution_time=result.execution_time,
                impact_delta=result.impact_delta,
                task_type="execution_loop",
                metadata={"output": _safe_serialize(result.output)},
            )
        except Exception as e:
            print(f"[ExecutionLoop] outcome recording failed for {goal.id}: {e}")

        # Publish event
        self._publish(
            "goal_executed",
            {
                "goal_id": goal.id,
                "success": result.success,
                "execution_time": result.execution_time,
                "error": result.error,
                "cycle": len(self._cycle_history),
            },
        )

        return result

    # ─── Multi-cycle run ─────────────────────────────────────────────────────

    def run(self, cycles: int = 1) -> list[CycleResult]:
        """Run multiple execution cycles sequentially."""
        results: list[CycleResult] = []
        for i in range(cycles):
            print(f"\n[ExecutionLoop] ── cycle {i + 1}/{cycles} ──")
            try:
                cycle_result = self.run_cycle(cycle_num=i)
                results.append(cycle_result)
                self._print_cycle_summary(cycle_result)
            except Exception as e:
                print(f"[ExecutionLoop] cycle {i + 1} failed: {e}")
                results.append(
                    CycleResult(
                        cycle=i,
                        active_goals=[],
                        results={},
                        reselected=[],
                        timestamp=datetime.now(timezone.utc).isoformat(),
                    )
                )
        return results

    @property
    def cycle_history(self) -> list[CycleResult]:
        return list(self._cycle_history)

    # ─── Display ─────────────────────────────────────────────────────────────

    @staticmethod
    def _print_cycle_summary(cr: CycleResult) -> None:
        successes = sum(1 for r in cr.results.values() if r.success)
        failures = len(cr.results) - successes
        print(
            f"  active={len(cr.active_goals)} "
            f"executed={len(cr.results)} "
            f"success={successes} fail={failures} "
            f"reselected={len(cr.reselected)}"
        )
        for gid, result in cr.results.items():
            status = "OK" if result.success else f"FAIL: {result.error or 'unknown'}"
            print(f"    [{gid[:8]}] {status} ({result.execution_time:.3f}s)")


# ─── Helpers ─────────────────────────────────────────────────────────────────


def _safe_serialize(obj: Any) -> Any:
    """Make output JSON-safe for metadata storage."""
    try:
        json.dumps(obj)
        return obj
    except (TypeError, ValueError):
        return str(obj)


# ─── CLI Entry ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="EOS Execution Loop")
    parser.add_argument("--cycles", type=int, default=1, help="Number of execution cycles")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Use NoOpExecutor (no real side effects)",
    )
    args = parser.parse_args()

    print("=" * 60)
    print("  EOS EXECUTION LOOP")
    print(f"  cycles={args.cycles} dry_run={args.dry_run}")
    print("=" * 60)

    loop = ExecutionLoop()
    results = loop.run(cycles=args.cycles)

    total_executed = sum(len(cr.results) for cr in results)
    total_success = sum(sum(1 for r in cr.results.values() if r.success) for cr in results)
    print(f"\n{'=' * 60}")
    print(
        f"  COMPLETE: {len(results)} cycles, {total_executed} executions, {total_success} successes"
    )
    print(f"{'=' * 60}")
