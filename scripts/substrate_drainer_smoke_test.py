#!/usr/bin/env python3
"""
Substrate station drainer smoke test.

Proves the EOS-side ingestion seam end-to-end:

  1. Daemon-side: post a StationEvent via StationBus.daemon_post_event()
  2. EOS-side:    drain_node() reads the inbox
  3. Ingest:      StationContract.record_event() is invoked
  4. Bridge:      EventBus receives "station.<event_type>"
  5. Malformed:   garbage event payloads are skipped, not raised
  6. Results:     inbox result entries are counted as skipped, not ingested

Runs in-process. Uses a dedicated test node_id so it never collides with a
real workstation daemon.

Usage:
    python3 /opt/OS/scripts/substrate_drainer_smoke_test.py
"""

from __future__ import annotations

import sys
import threading
import time

sys.path.insert(0, "/opt/OS")

from eos_ai.event_bus import EventBus  # noqa: E402
from eos_ai.substrate.actions import ActionResult, ActionStatus  # noqa: E402
from eos_ai.substrate.station import StationContract, StationEvent  # noqa: E402
from eos_ai.substrate.station_bus import get_station_bus  # noqa: E402
from eos_ai.substrate.station_drainer import drain_node  # noqa: E402


TEST_NODE = "drainer-smoketest"


def _header(msg: str) -> None:
    print(f"\n── {msg} " + "─" * max(0, 60 - len(msg)))


def main() -> int:
    bus = get_station_bus()

    # Clean any stale state from a prior run.
    bus.daemon_take_outbox(TEST_NODE)
    bus.drain_inbox(TEST_NODE)

    # Subscribe to the EventBus topic we expect the bridge to publish onto.
    received: list[dict] = []
    received_lock = threading.Lock()

    def _capture(payload: dict) -> None:
        with received_lock:
            received.append(payload)

    EventBus().subscribe("station.pomodoro_started", _capture)

    _header("1. Daemon posts a well-formed StationEvent")
    evt = StationEvent(
        node_id=TEST_NODE,
        event_type="pomodoro_started",
        payload={"duration_min": 25, "label": "deep work"},
    )
    bus.daemon_post_event(TEST_NODE, evt)

    # Also drop a malformed event and a result entry to exercise the filters.
    bus._inbox_append(TEST_NODE, {"type": "event", "payload": {"event_type": "no_node"}})  # noqa: SLF001
    bus._inbox_append(TEST_NODE, {"type": "event", "payload": "not-a-dict"})  # noqa: SLF001
    bus.daemon_post_result(
        TEST_NODE,
        ActionResult(
            action_id="noop-1",
            status=ActionStatus.SUCCEEDED,
            detail="noop",
        ),
    )

    _header("2. EOS-side drain_node()")
    contract = StationContract(node_id=TEST_NODE)
    stats = drain_node(TEST_NODE, contract=contract)
    print(f"  stats: {stats.as_dict()}")

    assert stats.drained == 1, f"expected 1 drained, got {stats.drained}"
    assert stats.malformed == 2, f"expected 2 malformed, got {stats.malformed}"
    assert stats.skipped == 1, f"expected 1 skipped (the result), got {stats.skipped}"
    assert stats.errors == 0, f"expected 0 errors, got {stats.errors}"
    assert stats.event_types.get("pomodoro_started") == 1

    _header("3. StationContract recorded the event")
    log = contract.event_log()
    assert len(log) == 1, f"expected 1 event in contract log, got {len(log)}"
    assert log[0].event_type == "pomodoro_started"
    print(f"  contract event_log: {[e.event_type for e in log]}")

    _header("4. EventBus bridge fired")
    # publish_async uses a daemon thread — give it a moment.
    deadline = time.time() + 2.0
    while time.time() < deadline:
        with received_lock:
            if received:
                break
        time.sleep(0.05)

    with received_lock:
        assert received, "EventBus bridge did not receive station.pomodoro_started"
        assert received[0]["node_id"] == TEST_NODE
        assert received[0]["payload"]["duration_min"] == 25
        print(f"  bridge payload: {received[0]}")

    _header("5. Second drain is empty (atomic clear)")
    stats2 = drain_node(TEST_NODE)
    assert stats2.drained == 0 and stats2.skipped == 0 and stats2.malformed == 0
    print(f"  stats: {stats2.as_dict()}")

    _header("DRAINER SMOKE TEST PASSED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
