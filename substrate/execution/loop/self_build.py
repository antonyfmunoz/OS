"""SelfBuildLoop — persistent loop for UMH self-improvement.

Composes:
  - ExecutionLoop (goal-driven select → plan → execute → record)
  - FeedbackLoop (quality scoring from outcomes)

Selects improvement goals from the goal selector, plans them,
executes via the substrate, records outcomes for learning.

The loop is the system improving itself — code quality, test
coverage, observability gaps, documentation freshness.

Interval: 30 minutes (1800s) — improvement tasks are heavier.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

from substrate.execution.loop.persistent_loop import CycleReport, PersistentLoop

logger = logging.getLogger(__name__)

_SELF_BUILD_DOMAIN = "self_improvement"


class SelfBuildLoop(PersistentLoop):
    """Drive continuous system improvement via goal execution."""

    def __init__(self, interval_seconds: int = 1800) -> None:
        super().__init__(
            name="self_build",
            domain=_SELF_BUILD_DOMAIN,
            interval_seconds=interval_seconds,
        )
        self._execution_loop = None

    def _get_execution_loop(self) -> Any:
        """Lazy-init the execution loop with self-build goal selector."""
        if self._execution_loop is None:
            from substrate.execution.loop.execution_loop import ExecutionLoop
            self._execution_loop = ExecutionLoop()
        return self._execution_loop

    def run_cycle(self) -> CycleReport:
        t0 = datetime.now(timezone.utc)
        actions = 0
        errors = 0
        details: list[dict] = []

        # Phase 1: Run one execution cycle (select → plan → execute → record)
        try:
            loop = self._get_execution_loop()
            cycle_result = loop.run_cycle(cycle_num=self._cycle_count)
            actions += len(cycle_result.results)
            goal_errors = sum(
                1 for r in cycle_result.results.values() if not r.success
            )
            errors += goal_errors
            details.append({
                "phase": "goal_execution",
                "active_goals": cycle_result.active_goals,
                "results": {
                    gid: {"success": r.success, "time": r.execution_time}
                    for gid, r in cycle_result.results.items()
                },
                "reselected": cycle_result.reselected,
            })
        except Exception as e:
            errors += 1
            details.append({"phase": "goal_execution", "error": str(e)})
            logger.warning(f"[self_build] goal execution failed: {e}")

        # Phase 2: Aggregate feedback for learning
        try:
            feedback_summary = self._collect_feedback()
            details.append({"phase": "feedback", **feedback_summary})
        except Exception as e:
            details.append({"phase": "feedback", "error": str(e)})
            logger.debug(f"[self_build] feedback collection failed: {e}")

        # Phase 3: Check system health indicators
        try:
            health = self._check_system_health()
            details.append({"phase": "health_check", **health})
        except Exception as e:
            details.append({"phase": "health_check", "error": str(e)})

        return CycleReport(
            loop_name=self.name,
            cycle_num=self._cycle_count,
            started_at=t0.isoformat(),
            finished_at=datetime.now(timezone.utc).isoformat(),
            actions_taken=actions,
            errors=errors,
            details=details,
        )

    def _collect_feedback(self) -> dict:
        """Aggregate recent feedback scores."""
        try:
            from substrate.execution.feedback_loop import get_feedback_loop
            fl = get_feedback_loop()
            stats = fl.get_aggregate_stats()
            return {"recent_stats": stats}
        except Exception:
            return {"recent_stats": {}}

    def _check_system_health(self) -> dict:
        """Deterministic health indicators for the substrate."""
        import os
        from pathlib import Path

        root = Path(os.getenv("UMH_ROOT", "/opt/OS"))
        indicators: dict[str, Any] = {}

        # Check heartbeat freshness for key services
        heartbeat_dir = root / "data" / "runtime" / "loop_heartbeats"
        if heartbeat_dir.exists():
            import json
            for hb_file in heartbeat_dir.glob("*.json"):
                try:
                    data = json.loads(hb_file.read_text())
                    indicators[hb_file.stem] = data.get("state", "unknown")
                except Exception:
                    indicators[hb_file.stem] = "unreadable"

        # Check error log growth (last 100 lines)
        error_log = root / "logs" / "errors.log"
        if error_log.exists():
            try:
                lines = error_log.read_text().strip().split("\n")
                indicators["recent_errors"] = len(lines[-100:]) if lines else 0
            except Exception:
                indicators["recent_errors"] = -1

        return indicators
