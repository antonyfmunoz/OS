"""Scheduled trigger producer — time-based mode transitions.

Background daemon thread that checks the clock once per minute and
emits SCHEDULED_ACTIVATE triggers through the substrate LocalListener
at configured times:

  - auto_overnight_hour: switch to overnight mode (default 23:00)
  - auto_morning_hour: switch to active mode (default 07:00)
  - maintenance_window_start/end: switch to maintenance mode

Reads timing from WorkstationPreferences. Thread-safe daemon thread
that stops cleanly on session exit.

UMH workstation subsystem.
"""

from __future__ import annotations

import logging
import threading
from datetime import datetime, timezone
from typing import Any

logger = logging.getLogger(__name__)

_NODE_ID = "workstation_local"


class ScheduledTriggerProducer:
    """Background producer that emits time-based triggers.

    Checks once per minute whether any configured time boundary has been
    crossed. Each boundary fires at most once per calendar day.
    """

    def __init__(
        self,
        auto_overnight_hour: int = 23,
        auto_morning_hour: int = 7,
        maintenance_window_start: int = 3,
        maintenance_window_end: int = 4,
        node_id: str = _NODE_ID,
    ) -> None:
        self._overnight_hour = auto_overnight_hour
        self._morning_hour = auto_morning_hour
        self._maint_start = maintenance_window_start
        self._maint_end = maintenance_window_end
        self._node_id = node_id

        self._stop_event = threading.Event()
        self._thread: threading.Thread | None = None
        self._fired_today: set[str] = set()
        self._last_check_day: int = -1
        self._listener: Any = None
        self._trigger_count = 0

    def start(self) -> bool:
        """Start the background scheduler thread."""
        if self._thread is not None and self._thread.is_alive():
            return True

        self._stop_event.clear()
        self._trigger_count = 0
        self._fired_today.clear()
        self._thread = threading.Thread(
            target=self._run,
            daemon=True,
            name="umh-scheduler",
        )
        self._thread.start()
        logger.info(
            "Scheduler started (overnight=%d, morning=%d, maint=%d-%d)",
            self._overnight_hour,
            self._morning_hour,
            self._maint_start,
            self._maint_end,
        )
        return True

    def stop(self) -> None:
        """Stop the scheduler thread."""
        self._stop_event.set()
        if self._thread is not None:
            self._thread.join(timeout=5)
            self._thread = None

    @property
    def is_running(self) -> bool:
        return self._thread is not None and self._thread.is_alive()

    @property
    def trigger_count(self) -> int:
        return self._trigger_count

    def _run(self) -> None:
        """Main loop — check clock every 60 seconds."""
        while not self._stop_event.is_set():
            try:
                self._check_triggers()
            except Exception as exc:
                logger.debug("Scheduler tick failed: %s", exc)

            self._stop_event.wait(timeout=60)

    def _check_triggers(self) -> None:
        """Check if any time boundary has been crossed."""
        now = datetime.now(timezone.utc)
        current_hour = now.hour
        current_day = now.timetuple().tm_yday

        if current_day != self._last_check_day:
            self._fired_today.clear()
            self._last_check_day = current_day

        if current_hour == self._overnight_hour and "overnight" not in self._fired_today:
            self._emit_trigger("overnight_safe_mode", "auto_overnight")
            self._fired_today.add("overnight")

        if current_hour == self._morning_hour and "morning" not in self._fired_today:
            self._emit_trigger("developer_mode", "auto_morning")
            self._fired_today.add("morning")

        if (
            self._maint_start <= current_hour < self._maint_end
            and "maintenance" not in self._fired_today
        ):
            self._emit_trigger("maintenance", "auto_maintenance")
            self._fired_today.add("maintenance")

    def _emit_trigger(self, requested_mode: str, reason: str) -> None:
        """Emit a SCHEDULED_ACTIVATE trigger through LocalListener."""
        listener = self._get_listener()
        if listener is None:
            logger.info("Scheduled trigger %s skipped — no listener", reason)
            return

        try:
            from substrate.execution.bridge.local_listener import (
                LocalTrigger,
                TriggerKind,
            )

            trigger = LocalTrigger(
                node_id=self._node_id,
                kind=TriggerKind.SCHEDULED_ACTIVATE,
                requested_mode=requested_mode,
                metadata={"reason": reason},
                issued_by="umh_scheduler",
            )
            result = listener.emit(trigger)
            self._trigger_count += 1
            logger.info(
                "Scheduled trigger %s: status=%s reason=%s",
                reason,
                result.status.value,
                result.decision_reason,
            )
        except Exception as exc:
            logger.debug("Scheduled trigger emission failed: %s", exc)

    def _get_listener(self) -> Any:
        """Lazy-load the substrate LocalListener."""
        if self._listener is not None:
            return self._listener

        try:
            from substrate.execution.bridge.local_listener import LocalListener

            self._listener = LocalListener()
            return self._listener
        except ImportError:
            logger.debug("LocalListener not available")
            return None

    def get_status(self) -> dict[str, Any]:
        return {
            "running": self.is_running,
            "trigger_count": self._trigger_count,
            "fired_today": sorted(self._fired_today),
            "overnight_hour": self._overnight_hour,
            "morning_hour": self._morning_hour,
            "maintenance_window": f"{self._maint_start:02d}:00-{self._maint_end:02d}:00",
        }


def create_scheduler_from_preferences() -> ScheduledTriggerProducer:
    """Create a scheduler with timing from WorkstationPreferences."""
    try:
        from umh.profile import ProfileManager

        pm = ProfileManager()
        prefs = pm.get_preferences()
        return ScheduledTriggerProducer(
            auto_overnight_hour=getattr(prefs, "auto_overnight_hour", 23),
            auto_morning_hour=getattr(prefs, "auto_morning_hour", 7),
            maintenance_window_start=getattr(prefs, "maintenance_window_start", 3),
            maintenance_window_end=getattr(prefs, "maintenance_window_end", 4),
        )
    except Exception:
        return ScheduledTriggerProducer()


def show_scheduler_status() -> int:
    """Display scheduler status for CLI."""
    try:
        from umh.profile import ProfileManager

        prefs = ProfileManager().get_preferences()
        overnight = getattr(prefs, "auto_overnight_hour", 23)
        morning = getattr(prefs, "auto_morning_hour", 7)
        maint_start = getattr(prefs, "maintenance_window_start", 3)
        maint_end = getattr(prefs, "maintenance_window_end", 4)
    except Exception:
        overnight, morning, maint_start, maint_end = 23, 7, 3, 4

    print()
    print("Scheduled Triggers")
    print("=" * 40)
    print("  (Scheduler runs within the interaction loop)")
    print(f"  Overnight:    {overnight:02d}:00 UTC")
    print(f"  Morning:      {morning:02d}:00 UTC")
    print(f"  Maintenance:  {maint_start:02d}:00-{maint_end:02d}:00 UTC")
    print()
    return 0
