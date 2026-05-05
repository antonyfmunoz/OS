"""Runtime loop — non-blocking tick cycle for the organism.

The loop drives the advisor's continuous operation:
  1. Read signals from brain signal store
  2. Update advisor state
  3. Poll heartbeat state and mark stale nodes
  4. Poll job state (timeouts, orphans)
  5. Evaluate active cells
  6. Spawn new cells if needed
  7. Check completed work
  8. Cleanup terminated cells
  9. Run prediction pass (Phase 20)
  10. Cache predicted plans for advisor

Constraints:
  - Deterministic per tick (same state → same actions)
  - No blocking operations
  - No execution logic inside the loop
  - Bounded tick count for safety
  - Node/job failures degrade safely, never crash the loop
  - Predictions never auto-execute (suggest only)

No imports from umh/environments, umh/adapters, subprocess, or shell.
"""

from __future__ import annotations

import logging
from typing import Any

from umh.learning.feedback import ExecutionFeedback
from umh.nodes.health import NodeHealthManager
from umh.nodes.heartbeat import HeartbeatMonitor
from umh.prediction.predictor import PredictionContext
from umh.runtime.advisor import AdvisorRuntime
from umh.runtime.session import SessionType

_log = logging.getLogger(__name__)

_MAX_TICKS = 10000


class RuntimeLoop:
    """Non-blocking tick-based runtime loop with optional node health and job awareness."""

    def __init__(
        self,
        advisor: AdvisorRuntime | None = None,
        heartbeat_monitor: HeartbeatMonitor | None = None,
        health_manager: NodeHealthManager | None = None,
        job_poller: Any | None = None,
        job_store: Any | None = None,
    ) -> None:
        self._advisor = advisor or AdvisorRuntime()
        self._heartbeat = heartbeat_monitor
        self._health = health_manager
        self._job_poller = job_poller
        self._job_store = job_store
        self._running = False
        self._tick_results: list[dict[str, Any]] = []
        self._node_events: list[dict[str, Any]] = []

    @property
    def advisor(self) -> AdvisorRuntime:
        return self._advisor

    @property
    def running(self) -> bool:
        return self._running

    @property
    def tick_results(self) -> list[dict[str, Any]]:
        return list(self._tick_results)

    @property
    def node_events(self) -> list[dict[str, Any]]:
        return list(self._node_events)

    def start(self, session_type: SessionType = SessionType.DAY) -> None:
        if self._running:
            return
        self._advisor.start(session_type)
        self._running = True

    def stop(self) -> None:
        if not self._running:
            return
        self._advisor.stop()
        self._running = False

    def tick(
        self,
        *,
        prediction_context: PredictionContext | None = None,
        completed_feedback: list[ExecutionFeedback] | None = None,
    ) -> dict[str, Any]:
        if not self._running:
            return {"error": "loop not running", "tick": 0}

        if self._advisor.tick_count >= _MAX_TICKS:
            self.stop()
            return {"error": "max ticks reached", "tick": self._advisor.tick_count}

        result = self._advisor.tick(
            prediction_context=prediction_context,
            completed_feedback=completed_feedback,
        )

        node_updates = self._poll_node_health()
        if node_updates:
            result["node_updates"] = node_updates

        job_updates = self._poll_jobs()
        if job_updates:
            result["job_updates"] = job_updates

        self._tick_results.append(result)
        return result

    def run_ticks(self, count: int) -> list[dict[str, Any]]:
        results = []
        for _ in range(count):
            if not self._running:
                break
            results.append(self.tick())
        return results

    def _poll_node_health(self) -> list[dict[str, str]]:
        """Check for stale nodes and update health state. Never crashes."""
        if self._heartbeat is None or self._health is None:
            return []

        updates: list[dict[str, str]] = []
        try:
            stale_nodes = self._heartbeat.list_stale_nodes()
            for node_id in stale_nodes:
                health = self._health.get_health(node_id)
                if health is None or health.state.value != "offline":
                    self._health.mark_stale(node_id)
                    event = {
                        "type": "node.offline",
                        "node_id": node_id,
                        "reason": "heartbeat stale",
                    }
                    updates.append(event)
                    self._node_events.append(event)
                    _log.info("Node %s marked offline (heartbeat stale)", node_id)
        except Exception as e:
            _log.debug("Node health polling error (non-fatal): %s", e)

        return updates

    def _poll_jobs(self) -> dict[str, Any] | None:
        """Poll job timeouts and orphans. Never crashes."""
        if self._job_poller is None or self._job_store is None:
            return None

        try:
            timed_out = self._job_poller.detect_timeouts(self._job_store)
            health_map = None
            if self._health is not None:
                all_health = self._health.list_all()
                health_map = {h.node_id: h for h in all_health}
            orphaned = self._job_poller.detect_orphans(self._job_store, health_by_node=health_map)
            if timed_out or orphaned:
                return {"timed_out": timed_out, "orphaned": orphaned}
        except Exception as e:
            _log.debug("Job polling error (non-fatal): %s", e)

        return None

    def clear(self) -> None:
        self._running = False
        self._advisor.clear()
        self._tick_results.clear()
        self._node_events.clear()
