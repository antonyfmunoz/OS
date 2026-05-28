"""WorkcellDaemon — persistent processor for workcell inboxes.

Continuously processes messages across multiple workcells:
  - Polls each workcell inbox in round-robin
  - Respects per-workcell concurrency limits
  - Recovers stale inflight messages on each cycle
  - Heartbeats regularly for liveness detection
  - Shuts down cleanly on stop signal
  - Uses backoff on idle cycles to avoid busy-waiting

Testable without real runtimes by injecting a mock clock and
adapters that return immediately.

UMH substrate subsystem.
"""

from __future__ import annotations

import json
import logging
import threading
import time
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Callable
from uuid import uuid4

from substrate.organism.workcell_protocol import Workcell, WorkcellStatus

logger = logging.getLogger(__name__)

_MIN_POLL_INTERVAL_S = 0.1
_MAX_POLL_INTERVAL_S = 5.0
_BACKOFF_MULTIPLIER = 1.5
_HEARTBEAT_EVERY_N_CYCLES = 10
_STALE_RECOVERY_EVERY_N_CYCLES = 50
_DRAIN_TIMEOUT_S = 30.0


class DaemonStatus(str, Enum):
    STOPPED = "stopped"
    RUNNING = "running"
    DRAINING = "draining"
    ERROR = "error"


@dataclass
class DaemonStats:
    """Accumulated daemon processing statistics."""

    cycles: int = 0
    messages_processed: int = 0
    messages_failed: int = 0
    stale_recovered: int = 0
    idle_cycles: int = 0
    started_at: float = 0.0
    last_activity_at: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        uptime = time.time() - self.started_at if self.started_at else 0
        return {
            "cycles": self.cycles,
            "messages_processed": self.messages_processed,
            "messages_failed": self.messages_failed,
            "stale_recovered": self.stale_recovered,
            "idle_cycles": self.idle_cycles,
            "uptime_seconds": round(uptime, 1),
            "throughput_per_min": round(
                self.messages_processed / (uptime / 60) if uptime > 60 else 0, 2
            ),
        }


class WorkcellDaemon:
    """Persistent daemon that drives workcell inbox processing.

    Register workcells, then call run() to start the processing loop.
    The daemon round-robins across workcells, processing one message
    per workcell per cycle. Idle cycles trigger exponential backoff.
    """

    def __init__(
        self,
        max_concurrency: int = 4,
        state_dir: str | Path = "data/umh/workcell_daemon",
        clock: Callable[[], float] | None = None,
        sleep_fn: Callable[[float], None] | None = None,
    ) -> None:
        self._workcells: dict[str, Workcell] = {}
        self._max_concurrency = max_concurrency
        self._state_dir = Path(state_dir)
        self._state_dir.mkdir(parents=True, exist_ok=True)
        self._clock = clock or time.time
        self._sleep = sleep_fn or time.sleep
        self._status = DaemonStatus.STOPPED
        self._stop_event = threading.Event()
        self._stats = DaemonStats()
        self._poll_interval = _MIN_POLL_INTERVAL_S
        self._inflight_count = 0
        self._schedules: dict[str, dict[str, Any]] = {}

    def register_workcell(self, workcell: Workcell) -> None:
        self._workcells[workcell.workcell_id] = workcell

    def unregister_workcell(self, workcell_id: str) -> bool:
        return self._workcells.pop(workcell_id, None) is not None

    @property
    def status(self) -> DaemonStatus:
        return self._status

    @property
    def stats(self) -> DaemonStats:
        return self._stats

    def run(self, max_cycles: int | None = None) -> DaemonStats:
        """Run the processing loop.

        Args:
            max_cycles: Stop after this many cycles (None = run until stop()).
                        Use for testing.
        """
        self._status = DaemonStatus.RUNNING
        self._stop_event.clear()
        self._stats = DaemonStats(started_at=self._clock())
        cycles_run = 0

        logger.info(
            "workcell daemon started: %d workcells, max_concurrency=%d",
            len(self._workcells),
            self._max_concurrency,
        )

        try:
            while not self._stop_event.is_set():
                if max_cycles is not None and cycles_run >= max_cycles:
                    break

                processed_this_cycle = self._run_cycle()
                cycles_run += 1
                self._stats.cycles = cycles_run

                if processed_this_cycle > 0:
                    self._poll_interval = _MIN_POLL_INTERVAL_S
                    self._stats.last_activity_at = self._clock()
                else:
                    self._stats.idle_cycles += 1
                    self._poll_interval = min(
                        self._poll_interval * _BACKOFF_MULTIPLIER,
                        _MAX_POLL_INTERVAL_S,
                    )

                self._sleep(self._poll_interval)

        except Exception as exc:
            self._status = DaemonStatus.ERROR
            logger.error("workcell daemon error: %s", exc)
            raise
        finally:
            self._shutdown()

        return self._stats

    def _run_cycle(self) -> int:
        """Process one message per workcell, respecting concurrency."""
        processed = 0
        self._inflight_count = 0

        if self._schedules:
            self._check_schedules()

        if self._stats.cycles % _STALE_RECOVERY_EVERY_N_CYCLES == 0:
            for wc in self._workcells.values():
                recovered = wc.recover_stale_inflight()
                self._stats.stale_recovered += recovered

        if self._stats.cycles % _HEARTBEAT_EVERY_N_CYCLES == 0:
            for wc in self._workcells.values():
                wc.write_heartbeat()

        for wc in self._workcells.values():
            if self._inflight_count >= self._max_concurrency:
                break

            if wc.status == WorkcellStatus.SHUTDOWN:
                continue

            result = wc.process_next()
            if result is None:
                continue

            self._inflight_count += 1

            if result.get("status") == "completed":
                processed += 1
                self._stats.messages_processed += 1
            elif result.get("status") == "failed":
                self._stats.messages_failed += 1
                processed += 1
            elif result.get("error"):
                self._stats.messages_failed += 1

        return processed

    def stop(self, drain: bool = True) -> None:
        """Signal the daemon to stop.

        Args:
            drain: If True (default), finish processing any inflight messages
                   before stopping. If False, stop immediately.
        """
        if drain and self._inflight_count > 0:
            self._status = DaemonStatus.DRAINING
            logger.info(
                "workcell daemon draining %d inflight messages",
                self._inflight_count,
            )
        else:
            self._status = DaemonStatus.DRAINING
        self._stop_event.set()
        logger.info("workcell daemon stop requested")

    def _shutdown(self) -> None:
        """Clean shutdown: write final heartbeats and persist state."""
        for wc in self._workcells.values():
            wc.write_heartbeat()

        self._persist_state()
        self._status = DaemonStatus.STOPPED
        logger.info(
            "workcell daemon stopped: %d messages processed in %d cycles",
            self._stats.messages_processed,
            self._stats.cycles,
        )

    def _persist_state(self) -> None:
        state = {
            "status": self._status.value,
            "stats": self._stats.to_dict(),
            "workcells": {
                wid: wc.to_dict() for wid, wc in self._workcells.items()
            },
            "timestamp": self._clock(),
        }
        path = self._state_dir / "daemon_state.json"
        tmp = path.with_suffix(".tmp")
        tmp.write_text(json.dumps(state, indent=2))
        tmp.rename(path)

    def schedule_periodic(
        self,
        workcell_id: str,
        intent: str,
        payload: dict[str, Any],
        interval_s: float,
        catch_up: bool = True,
    ) -> str:
        """Schedule a periodic message to a workcell (cron/catch-up pattern).

        If catch_up is True and the daemon was down, overdue messages are
        sent on startup (once per missed interval, not flooding).

        Returns the schedule ID.
        """
        from substrate.organism.workcell_protocol import WorkcellMessage

        schedule_id = f"sched-{uuid4().hex[:8]}"
        schedule = {
            "id": schedule_id,
            "workcell_id": workcell_id,
            "intent": intent,
            "payload": payload,
            "interval_s": interval_s,
            "catch_up": catch_up,
            "last_fired_at": 0.0,
            "created_at": self._clock(),
        }
        self._schedules[schedule_id] = schedule
        self._persist_state()
        return schedule_id

    def cancel_periodic(self, schedule_id: str) -> bool:
        return self._schedules.pop(schedule_id, None) is not None

    def _check_schedules(self) -> int:
        """Fire any due scheduled messages. Returns count of messages sent."""
        from substrate.organism.workcell_protocol import WorkcellMessage

        now = self._clock()
        sent = 0

        for sched in list(self._schedules.values()):
            wc = self._workcells.get(sched["workcell_id"])
            if not wc:
                continue

            last = sched["last_fired_at"]
            interval = sched["interval_s"]

            if last == 0.0:
                if sched["catch_up"]:
                    sched["last_fired_at"] = now
                    msg = WorkcellMessage(
                        sender="daemon-scheduler",
                        intent=sched["intent"],
                        payload=sched["payload"],
                        priority=3,
                    )
                    wc.send_message(msg)
                    sent += 1
                else:
                    sched["last_fired_at"] = now
                continue

            if now - last >= interval:
                missed = int((now - last) / interval)
                fires = min(missed, 3) if sched["catch_up"] else 1

                for _ in range(fires):
                    msg = WorkcellMessage(
                        sender="daemon-scheduler",
                        intent=sched["intent"],
                        payload=sched["payload"],
                        priority=3,
                    )
                    wc.send_message(msg)
                    sent += 1

                sched["last_fired_at"] = now

        return sent

    def to_dict(self) -> dict[str, Any]:
        return {
            "status": self._status.value,
            "workcell_count": len(self._workcells),
            "max_concurrency": self._max_concurrency,
            "poll_interval": round(self._poll_interval, 3),
            "stats": self._stats.to_dict(),
            "schedules": len(self._schedules),
            "workcells": {
                wid: wc.to_dict() for wid, wc in self._workcells.items()
            },
        }
