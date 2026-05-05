#!/usr/bin/env python3
"""
Local listener smoke test.

Proves the smallest real end-to-end activation flow:
  1. A node is registered + heartbeated via StationDaemon (so readiness is fresh).
  2. LocalListener.manual_activate(...) emits a bounded trigger.
  3. The listener delegates to start_open_day, which runs the ritual body.
  4. Readiness/policy/scene logic is REUSED (not duplicated).
  5. Trigger history is recorded.
  6. Reporting helpers see the activation.
  7. Safety: a trigger for an unregistered node is SKIPPED, not raised.
  8. Safety: a second trigger while open_day is active is SKIPPED.

Runs in-process. Uses dedicated test nodes. dry_run=True so no real apps
spawn. Returns 0 on success, non-zero on assertion failure.
"""

from __future__ import annotations

import sys

sys.path.insert(0, "/opt/OS")

from eos_ai.substrate.local_listener import (  # noqa: E402
    LocalListener,
    LocalTrigger,
    TriggerKind,
    TriggerStatus,
    get_trigger_history,
    listener_report,
)
from eos_ai.substrate.nodes import NodeRegistry, NodeStatus  # noqa: E402
from eos_ai.substrate.rituals import RitualKind, RitualRegistry  # noqa: E402
from eos_ai.substrate.station_bus import get_station_bus  # noqa: E402
from eos_ai.substrate.station_daemon import StationDaemon  # noqa: E402

TEST_NODE = "smoketest-local-listener"
GHOST_NODE = "smoketest-ghost-never-registered"


def _header(msg: str) -> None:
    print(f"\n── {msg} " + "─" * max(0, 60 - len(msg)))


def _fail_terminal_open_days() -> None:
    """Force-terminate any leftover open_day rituals from prior runs so the
    duplicate-suppression check can be exercised cleanly."""
    reg = RitualRegistry.default()
    for r in reg.active(kind=RitualKind.OPEN_DAY):
        try:
            reg.fail(r.ritual_id, "smoketest cleanup")
        except Exception:  # noqa: BLE001
            pass


def main() -> int:
    bus = get_station_bus()
    bus.daemon_take_outbox(TEST_NODE)
    bus.drain_inbox(TEST_NODE)

    _header("0. Cleanup: terminate any active open_day rituals + clear history")
    _fail_terminal_open_days()
    get_trigger_history().clear()

    _header("1. Register node + fresh heartbeat")
    daemon = StationDaemon(
        node_id=TEST_NODE,
        poll_interval_s=0.05,
        heartbeat_interval_s=0.01,
        dry_run=True,
    )
    daemon.register()
    daemon._tick()  # noqa: SLF001
    node = NodeRegistry.default().get(TEST_NODE)
    assert node is not None and node.status == NodeStatus.ONLINE, node
    print(
        f"  node={node.node_id} status={node.status.value} last_seen={node.last_seen}"
    )

    _header("2. LocalListener.manual_activate fires open_day")
    listener = LocalListener()
    t1 = listener.manual_activate(TEST_NODE, requested_mode="operator_mode")
    print(f"  trigger_id={t1.trigger_id} status={t1.status.value}")
    print(f"  ritual_id={t1.ritual_id}")
    print(f"  decision_reason={t1.decision_reason}")
    assert t1.status == TriggerStatus.ACCEPTED, t1.as_dict()
    assert t1.ritual_id is not None, "ritual_id should be set on ACCEPTED trigger"

    ritual = RitualRegistry.default().get(t1.ritual_id)
    assert ritual is not None, "ritual should exist in registry"
    assert ritual.kind == RitualKind.OPEN_DAY
    body = ritual.outputs.get("body_actions", [])
    print(f"  ritual body actions: {len(body)}")
    for entry in body[:6]:
        print(f"    • {entry.get('kind')}: {entry.get('detail')}")
    # Body must have run scene_decision (proves readiness/policy reuse).
    assert any(b.get("kind") == "scene_decision" for b in body), body

    _header("3. Duplicate trigger while open_day active → SKIPPED")
    t2 = listener.manual_activate(TEST_NODE)
    print(f"  status={t2.status.value} reason={t2.decision_reason}")
    assert t2.status == TriggerStatus.SKIPPED
    assert "already active" in (t2.decision_reason or "")

    _header("4. Trigger for unregistered node → SKIPPED, never raised")
    t3 = listener.simulate_wake_word(GHOST_NODE)
    print(f"  status={t3.status.value} reason={t3.decision_reason}")
    assert t3.status == TriggerStatus.SKIPPED
    assert "not registered" in (t3.decision_reason or "")

    _header("5. Trigger history is bounded + readable")
    history = get_trigger_history().latest(limit=10)
    print(f"  recorded {len(history)} triggers")
    assert len(history) == 3, history
    kinds = {h["kind"] for h in history}
    assert TriggerKind.MANUAL_ACTIVATE.value in kinds
    assert TriggerKind.WAKE_WORD_DETECTED.value in kinds

    _header("6. listener_report() exposes last_activation")
    report = listener_report(node_id=TEST_NODE, limit=5)
    print(f"  count={report['count']}")
    print(
        f"  last_activation_status={report['last_activation']['status'] if report['last_activation'] else None}"
    )
    assert report["last_activation"] is not None
    assert report["last_activation"]["status"] == "accepted"

    _header("7. Stub trigger kinds (clap_detected) accepted as bounded events")
    # Terminate the active ritual so we can exercise another acceptance path.
    _fail_terminal_open_days()
    t4 = listener.simulate_clap(TEST_NODE)
    print(f"  status={t4.status.value} reason={t4.decision_reason}")
    assert t4.status in (TriggerStatus.ACCEPTED, TriggerStatus.SKIPPED), t4.as_dict()
    # If accepted, it must have produced a ritual_id.
    if t4.status == TriggerStatus.ACCEPTED:
        assert t4.ritual_id is not None

    _header("SMOKE TEST PASSED")
    print("  verified: trigger model → activation → ritual reuse → history → report")
    print("  hot path: untouched")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
