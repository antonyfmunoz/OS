"""UMH Goal Engine — persistent goal evaluation and task generation.

Evaluates active goals on a polling cycle and creates tasks through the
planning pipeline. Never imports from umh.execution.engine or umh.adapters.

Usage:
    from umh.goals.goal_engine import get_goal_engine

    engine = get_goal_engine()
    engine.start()

    # Manual evaluation:
    result = engine.evaluate_now("goal_abc123")
"""

from __future__ import annotations

import logging
import threading

from umh.core.clock import iso_now as _iso_now
from umh.events.stream import publish as _publish_event
from umh.goals.models import Goal, GoalStatus
from umh.goals.policy import check_goal_policy
from umh.goals.store import get_goal_store

_log = logging.getLogger(__name__)


class GoalEngine:
    """Polling engine that evaluates active goals and creates tasks."""

    def __init__(self, poll_interval: float = 120.0) -> None:
        self._poll_interval = poll_interval
        self._running = False
        self._thread: threading.Thread | None = None
        self._stop_event = threading.Event()

    def start(self) -> None:
        """Start the goal evaluation loop in a daemon thread."""
        if self._running:
            return
        self._running = True
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._loop, daemon=True, name="umh-goal-engine")
        self._thread.start()
        _log.info("GoalEngine started with poll_interval=%.1fs", self._poll_interval)

    def stop(self) -> None:
        """Stop the evaluation loop."""
        self._running = False
        self._stop_event.set()
        if self._thread is not None:
            self._thread.join(timeout=self._poll_interval + 5)
            self._thread = None
        _log.info("GoalEngine stopped")

    def is_running(self) -> bool:
        """Return True if the evaluation loop is active."""
        return self._running

    def _loop(self) -> None:
        """Internal polling loop. Evaluates active goals on each tick."""
        while self._running:
            try:
                self._tick()
            except Exception:
                _log.exception("GoalEngine tick failed")
            self._stop_event.wait(timeout=self._poll_interval)

    def _tick(self) -> None:
        """Single evaluation cycle across all active goals."""
        store = get_goal_store()
        now = _iso_now()

        for goal in store.list_active():
            # Skip if evaluation interval has not elapsed
            if goal.last_evaluated_at:
                from datetime import datetime, timezone

                last = datetime.fromisoformat(goal.last_evaluated_at)
                current = datetime.fromisoformat(now)
                elapsed = (current - last).total_seconds()
                if elapsed < goal.policy.evaluation_interval_sec:
                    continue

            try:
                self.evaluate_goal(goal)
            except Exception:
                _log.exception("Failed to evaluate goal %s", goal.id)

    def evaluate_goal(self, goal: Goal) -> dict:
        """Evaluate a goal using strategy decomposition.

        NEW flow (Phase 8B):
        goal → strategy → ready steps → task objectives → tasks

        Strategy is cached per goal to avoid recomputation.
        Only steps with generates_tasks=True and satisfied dependencies produce tasks.
        """
        result = check_goal_policy(goal)
        if not result.allowed:
            return {"actions": [], "status": "skipped", "reason": result.reason}

        store = get_goal_store()

        if goal.progress >= 1.0:
            store.complete(goal.id)
            _publish_event(
                "goal.completed",
                payload={"goal_id": goal.id, "name": goal.name},
                actor_id=f"goal:{goal.id}",
            )
            return {"actions": [], "status": "completed"}

        # Lazy imports — strategy + planning pipeline
        from umh.planning.models import PlanStatus
        from umh.planning.planner import create_plan_from_raw, execute_plan
        from umh.strategy.decomposer import (
            cache_strategy,
            decompose_goal,
            get_cached_strategy,
        )

        actor = f"goal:{goal.id}"

        # Get or create strategy
        strategy = get_cached_strategy(goal.id)
        if strategy is None:
            try:
                strategy = decompose_goal(goal)
                cache_strategy(strategy)
                from umh.strategy.history import record_strategy_version

                record_strategy_version(goal.id, strategy)
            except Exception as exc:
                _log.warning("Strategy decomposition failed for goal %s: %s", goal.id, exc)
                return {"actions": [], "status": "error", "error": str(exc)}

        # Get ready steps (dependencies satisfied, generates_tasks=True)
        ready = strategy.ready_steps()
        if not ready:
            if strategy.progress() >= 1.0:
                store.complete(goal.id)
                _publish_event(
                    "goal.completed",
                    payload={"goal_id": goal.id, "name": goal.name},
                    actor_id=actor,
                )
                return {"actions": [], "status": "completed", "strategy_progress": 1.0}
            return {
                "actions": [],
                "status": "waiting",
                "strategy_progress": strategy.progress(),
            }

        actions: list[dict] = []
        tasks_created = 0

        for step in ready:
            if tasks_created >= goal.policy.max_tasks_per_cycle:
                break

            try:
                plan = create_plan_from_raw(step.description, requested_by=actor)

                if plan.status == PlanStatus.VALIDATED:
                    task = execute_plan(plan)
                    task_id = getattr(task, "id", "") if task else ""
                    strategy.add_task_to_step(step.id, task_id)
                    actions.append(
                        {
                            "task_id": task_id,
                            "plan_id": plan.plan_id,
                            "step_id": step.id,
                        }
                    )
                    tasks_created += 1

                    from umh.strategy.history import record_task_outcome

                    record_task_outcome(goal.id, completed=True)

                    _publish_event(
                        "goal.task_created",
                        payload={
                            "goal_id": goal.id,
                            "task_id": task_id,
                            "plan_id": plan.plan_id,
                            "step_id": step.id,
                        },
                        actor_id=actor,
                    )
                else:
                    break
            except Exception as exc:
                _log.warning("Goal %s step %s task creation failed: %s", goal.id, step.id, exc)
                if goal.policy.auto_pause_on_failure:
                    strategy.mark_step_failed(step.id)
                    from umh.strategy.history import record_task_outcome

                    record_task_outcome(goal.id, failed=True)
                    store.fail(goal.id)
                    _publish_event(
                        "goal.failed",
                        payload={"goal_id": goal.id, "error": str(exc)},
                        actor_id=actor,
                    )
                    return {
                        "actions": actions,
                        "status": "failed",
                        "error": str(exc),
                        "tasks_created": tasks_created,
                    }
                strategy.mark_step_failed(step.id)
                from umh.strategy.history import record_task_outcome as _rec_fail

                _rec_fail(goal.id, failed=True)
                break

        # Update goal tracking with strategy progress
        new_progress = strategy.progress()
        store.update_progress(
            goal.id,
            progress=new_progress,
            tasks_created=goal.tasks_created + tasks_created,
            tasks_completed=goal.tasks_completed,
        )
        store.update_evaluation(goal.id)

        _publish_event(
            "goal.evaluated",
            payload={
                "goal_id": goal.id,
                "tasks_created": tasks_created,
                "total_actions": len(actions),
                "strategy_progress": new_progress,
            },
            actor_id=actor,
        )

        _publish_event(
            "strategy.applied",
            payload={
                "goal_id": goal.id,
                "strategy_id": strategy.id,
                "ready_steps": len(ready),
                "tasks_created": tasks_created,
            },
            actor_id=actor,
        )

        # Check for refinement after sufficient evaluations
        from umh.strategy.history import get_strategy_history
        from umh.strategy.refiner import get_proposal, refine_strategy as _refine, store_proposal

        history = get_strategy_history(goal.id)
        active = history.active_version()
        if active and active.performance.evaluations >= 3 and get_proposal(goal.id) is None:
            proposal = _refine(goal.id)
            if proposal is not None:
                store_proposal(proposal)

        proposal = get_proposal(goal.id)
        return {
            "actions": actions,
            "status": "evaluated",
            "tasks_created": tasks_created,
            "strategy_progress": new_progress,
            "refinement_available": proposal is not None,
            "refinement_recommended": proposal.recommended if proposal else False,
        }

    def evaluate_now(self, goal_id: str) -> dict:
        """Manually trigger evaluation for a specific goal.

        Bypasses the evaluation interval check.
        Returns dict with evaluation results or error.
        """
        store = get_goal_store()
        goal = store.get(goal_id)

        if goal is None:
            return {"error": f"goal {goal_id} not found", "status": "error"}

        return self.evaluate_goal(goal)


_engine: GoalEngine | None = None
_engine_lock = threading.Lock()


def get_goal_engine(poll_interval: float = 120.0) -> GoalEngine:
    """Return the singleton GoalEngine, creating it if needed."""
    global _engine
    if _engine is None:
        with _engine_lock:
            if _engine is None:
                _engine = GoalEngine(poll_interval=poll_interval)
    return _engine


def reset_goal_engine() -> GoalEngine:
    """Reset the singleton engine. Returns the new instance."""
    global _engine
    with _engine_lock:
        _engine = GoalEngine()
    return _engine
