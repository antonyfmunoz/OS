#!/usr/bin/env python3
"""
Substrate station MVP smoke test.

Proves the smallest real end-to-end loop:
  1. Daemon registers as a node and emits a heartbeat.
  2. EOS side proposes SPEAK_TEXT + PLAY_SOUND via StationContract.
  3. Daemon consumes outbox, executes handlers (with graceful fallback),
     and posts ActionResult + StationEvent into the inbox.
  4. EOS side drains the inbox and observes the round trip.

Runs in-process (single Python interpreter) so it's safe on the VPS and on
a workstation. Does not spawn long-lived processes. Uses a dedicated test
node_id to avoid interfering with a real daemon.

Usage:
    python3 /opt/OS/scripts/substrate_smoke_test.py
"""

from __future__ import annotations

import sys
import time

import os
sys.path.insert(0, os.environ.get("UMH_ROOT") or os.environ.get("OS_ROOT") or os.environ.get("EOS_ROOT") or "/opt/OS")

from substrate.execution.bridge.nodes import NodeRegistry, NodeStatus  # noqa: E402
from substrate.execution.bridge.ritual_body import RitualPolicy  # noqa: E402
from substrate.execution.bridge.ritual_runner import (  # noqa: E402
    start_close_day,
    start_open_day,
)
from substrate.execution.bridge.rituals import RitualRegistry  # noqa: E402
from substrate.execution.bridge.station_bus import get_station_bus  # noqa: E402
from substrate.execution.bridge.station_daemon import StationDaemon  # noqa: E402
from substrate.execution.bridge.station_helpers import (  # noqa: E402
    propose_open_scene,
    propose_open_url,
    propose_launch_app,
    propose_play_sound,
    propose_speak_text,
)


TEST_NODE = "smoketest-station"


def _header(msg: str) -> None:
    print(f"\n── {msg} " + "─" * max(0, 60 - len(msg)))


def main() -> int:
    bus = get_station_bus()
    registry = NodeRegistry.default()

    # Clean any stale outbox/inbox from a prior run.
    bus.daemon_take_outbox(TEST_NODE)
    bus.drain_inbox(TEST_NODE)

    _header("1. Daemon registers + single-tick heartbeat")
    daemon = StationDaemon(
        node_id=TEST_NODE,
        poll_interval_s=0.05,
        heartbeat_interval_s=0.01,  # force heartbeat on first tick
        dry_run=True,  # never actually open a browser or launch apps
    )
    daemon.register()
    daemon._tick()  # noqa: SLF001 — exercising the loop once is the point

    node = registry.get(TEST_NODE)
    assert node is not None, "daemon did not register"
    assert node.status == NodeStatus.ONLINE, f"unexpected status {node.status}"
    print(f"  node registered: {node.node_id}  status={node.status.value}")
    print(f"  last_seen: {node.last_seen}")

    _header("2. EOS proposes SPEAK_TEXT + PLAY_SOUND")
    a1 = propose_speak_text(TEST_NODE, "substrate smoke test online")
    a2 = propose_play_sound(TEST_NODE, path="/nonexistent/sound.wav")
    print(f"  dispatched {a1.kind.value} ({a1.action_id}) status={a1.status.value}")
    print(f"  dispatched {a2.kind.value} ({a2.action_id}) status={a2.status.value}")

    pending = bus.pending_outbox(TEST_NODE)
    assert len(pending) == 2, f"expected 2 pending, got {len(pending)}"

    _header("3. Daemon ticks — consumes outbox, posts results")
    daemon._tick()  # noqa: SLF001

    leftover = bus.pending_outbox(TEST_NODE)
    assert leftover == [], f"outbox not drained: {leftover}"

    _header("4. EOS drains inbox")
    messages = bus.drain_inbox(TEST_NODE)
    results = [m for m in messages if m["type"] == "result"]
    events = [m for m in messages if m["type"] == "event"]

    print(f"  inbox: {len(results)} result(s), {len(events)} event(s)")
    for r in results:
        p = r["payload"]
        print(f"    result {p['action_id']} → {p['status']}: {p.get('detail')}")
    for e in events:
        p = e["payload"]
        print(f"    event  {p['event_type']} ({p.get('payload', {}).get('reason')})")

    assert len(results) == 2, f"expected 2 results, got {len(results)}"
    assert any(e["payload"]["event_type"] == "heartbeat" for e in events), (
        "no heartbeat event"
    )

    # SPEAK_TEXT should always succeed (stdout fallback path exists).
    speak_result = next(r for r in results if r["payload"]["action_id"] == a1.action_id)
    assert speak_result["payload"]["status"] == "succeeded", speak_result

    _header("5. Workstation bootstrap: OPEN_URL + OPEN_SCENE")
    url_action = propose_open_url(TEST_NODE, "https://example.com/")
    bad_url = propose_open_url(
        TEST_NODE, "javascript:alert(1)"
    )  # must be rejected by handler
    scene_action = propose_open_scene(TEST_NODE, "operator_mode")
    missing_scene = propose_open_scene(TEST_NODE, "does_not_exist")
    bad_app = propose_launch_app(TEST_NODE, "definitely_not_allowed")

    daemon._tick()  # noqa: SLF001
    msgs2 = bus.drain_inbox(TEST_NODE)
    results2 = {
        m["payload"]["action_id"]: m["payload"] for m in msgs2 if m["type"] == "result"
    }

    for a in (url_action, bad_url, scene_action, missing_scene, bad_app):
        r = results2.get(a.action_id)
        print(f"  {a.kind.value:<11} {a.action_id} → {r['status']}: {r['detail']}")

    assert results2[url_action.action_id]["status"] == "succeeded"
    assert results2[bad_url.action_id]["status"] == "rejected"
    assert results2[scene_action.action_id]["status"] == "succeeded"
    assert results2[missing_scene.action_id]["status"] == "rejected"
    assert results2[bad_app.action_id]["status"] == "rejected"

    # Scene result should include per-step breakdown
    scene_data = results2[scene_action.action_id].get("data", {})
    assert scene_data.get("scene") == "operator_mode"
    assert len(scene_data.get("steps", [])) >= 2, scene_data
    print(f"  operator_mode expanded into {len(scene_data['steps'])} steps")

    _header("6. Ritual body: open_day + close_day propose via policy")
    # Clean outbox so we see exactly what the ritual body proposes.
    bus.daemon_take_outbox(TEST_NODE)
    bus.drain_inbox(TEST_NODE)
    ritual_reg = RitualRegistry.default()

    open_policy = RitualPolicy(
        station_node_id=TEST_NODE,
        open_speak="Good morning. Substrate online.",
        open_scene="operator_mode",
    )
    open_rid = start_open_day(policy=open_policy)
    open_ritual = ritual_reg.get(open_rid)
    body = open_ritual.outputs.get("body_actions", [])
    print(f"  open_day ritual_id={open_rid}  body actions={len(body)}")
    for entry in body:
        print(f"    • {entry['kind']}: {entry['detail']}")

    assert any(e["kind"] == "speak_text" for e in body), body
    assert any(e["kind"] == "open_scene" for e in body), body

    pending_after_open = bus.pending_outbox(TEST_NODE)
    kinds_open = sorted(a["kind"] for a in pending_after_open)
    # Ritual body must have contributed open_scene + speak_text. The audio
    # loop / operator_presence layer may have added an extra speak_text for
    # a meaningful mode transition (e.g. STARTING→FOCUSED); that is
    # additive and expected.
    assert "open_scene" in kinds_open, kinds_open
    assert "speak_text" in kinds_open, kinds_open
    assert 2 <= len(pending_after_open) <= 3, pending_after_open
    print(f"  outbox now holds: {kinds_open}")

    # Drain so close_day starts clean.
    bus.daemon_take_outbox(TEST_NODE)
    bus.drain_inbox(TEST_NODE)

    close_policy = RitualPolicy(
        station_node_id=TEST_NODE,
        close_speak="Closing day. Systems to standby.",
        close_sound="/nonexistent/chime.wav",
    )
    close_rid = start_close_day(policy=close_policy)
    close_ritual = ritual_reg.get(close_rid)
    close_body = close_ritual.outputs.get("body_actions", [])
    print(f"  close_day ritual_id={close_rid}  body actions={len(close_body)}")
    for entry in close_body:
        print(f"    • {entry['kind']}: {entry['detail']}")

    assert any(e["kind"] == "speak_text" for e in close_body), close_body
    assert any(e["kind"] == "play_sound" for e in close_body), close_body

    pending_after_close = bus.pending_outbox(TEST_NODE)
    kinds_close = sorted(a["kind"] for a in pending_after_close)
    # Ritual body contributed play_sound + speak_text. The operator_presence
    # layer may add a bounded second speak_text on FOCUSED/ACTIVE → CLOSING.
    assert "play_sound" in kinds_close, kinds_close
    assert "speak_text" in kinds_close, kinds_close
    assert 2 <= len(pending_after_close) <= 3, pending_after_close
    print(f"  outbox now holds: {kinds_close}")

    # Graceful degradation: no station node at all.
    missing_policy = RitualPolicy(
        station_node_id="ghost-station-does-not-exist",
        open_speak="should not reach daemon",
        open_scene="operator_mode",
    )
    missing_rid = start_open_day(policy=missing_policy)
    missing_ritual = ritual_reg.get(missing_rid)
    missing_body = missing_ritual.outputs.get("body_actions", [])
    assert len(missing_body) == 1 and missing_body[0]["kind"] == "skipped", missing_body
    print(f"  missing-node ritual gracefully skipped: {missing_body[0]['detail']}")

    # Ritual body must not have dispatched anything to our test node.
    bus.daemon_take_outbox(TEST_NODE)

    _header("SMOKE TEST PASSED")
    print(f"  round-trip time: end of tick at {time.time():.2f}")
    print(f"  node_id: {TEST_NODE}")
    print("  verified: register → heartbeat → dispatch → execute → result")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
