#!/usr/bin/env python3
"""
Substrate station full round-trip smoke test.

Proves the result/ritual loop end-to-end:

  1. Ritual body (open_day) proposes SPEAK_TEXT + OPEN_SCENE via the station
  2. StationDaemon consumes the outbox and executes handlers
  3. Daemon posts ActionResult + heartbeat event into the inbox
  4. EOS-side `drain_all()` ingests both in a single atomic read
  5. ResultStore now holds IngestedResult rows for every action_id
  6. `reconcile_ritual()` mirrors outcomes onto ritual.outputs["body_actions"]
  7. A ritual-visible `result_summary` lets operators answer "did it work?"
  8. FOCUS_APP goes end-to-end with graceful fallback on headless hosts

Runs in-process. Uses a dedicated test node_id so it never collides with
the real workstation daemon.

Usage:
    python3 /opt/OS/scripts/substrate_result_loop_smoke_test.py
"""

from __future__ import annotations

import sys

import os
sys.path.insert(0, os.environ.get("UMH_ROOT") or os.environ.get("OS_ROOT") or os.environ.get("EOS_ROOT") or "/opt/OS")

from runtime.substrate.result_store import (  # noqa: E402
    get_result_store,
    reset_result_store_for_tests,
)
from runtime.substrate.ritual_body import RitualPolicy  # noqa: E402
from runtime.substrate.ritual_reconciler import reconcile_ritual  # noqa: E402
from runtime.substrate.ritual_runner import start_open_day  # noqa: E402
from runtime.substrate.rituals import RitualRegistry  # noqa: E402
from runtime.substrate.station_bus import get_station_bus  # noqa: E402
from runtime.substrate.station_daemon import StationDaemon  # noqa: E402
from runtime.substrate.station_drainer import drain_all  # noqa: E402
from runtime.substrate.station_helpers import propose_focus_app  # noqa: E402


TEST_NODE = "result-loop-smoketest"


def _header(msg: str) -> None:
    print(f"\n── {msg} " + "─" * max(0, 60 - len(msg)))


def main() -> int:
    bus = get_station_bus()
    reset_result_store_for_tests()
    store = get_result_store()
    # Wipe durable rows from prior runs so per-node asserts stay deterministic.
    store.clear()

    # Clean stale state
    bus.daemon_take_outbox(TEST_NODE)
    bus.drain_inbox(TEST_NODE)

    _header("1. Daemon registers (dry-run)")
    daemon = StationDaemon(
        node_id=TEST_NODE,
        poll_interval_s=0.05,
        heartbeat_interval_s=0.01,
        dry_run=True,
    )
    daemon.register()
    daemon._tick()  # noqa: SLF001 — initial heartbeat + empty outbox

    _header("2. Ritual body proposes open_day actions")
    policy = RitualPolicy(
        station_node_id=TEST_NODE,
        open_speak="result loop smoke test",
        open_scene="operator_mode",
    )
    rid = start_open_day(policy=policy)
    ritual = RitualRegistry.default().get(rid)
    assert ritual is not None, "ritual vanished after start_open_day"
    body = ritual.outputs.get("body_actions") or []
    proposed_ids = [e["action_id"] for e in body if "action_id" in e]
    print(f"  ritual_id={rid}  body={len(body)}  action_ids={proposed_ids}")
    assert len(proposed_ids) == 2, f"expected 2 action_ids, got {proposed_ids}"

    _header("3. Daemon ticks — executes + posts results")
    daemon._tick()  # noqa: SLF001
    leftover = bus.pending_outbox(TEST_NODE)
    assert leftover == [], f"outbox not drained: {leftover}"

    _header("4. EOS drain_all() ingests events + results atomically")
    stats = drain_all(TEST_NODE)
    print(f"  events:  {stats.events.as_dict()}")
    print(f"  results: {stats.results.as_dict()}")

    assert stats.events.drained >= 1, "no events ingested (heartbeat expected)"
    assert stats.results.drained == 2, f"expected 2 results, got {stats.results.drained}"
    assert stats.results.succeeded == 2, f"expected 2 succeeded, got {stats.results.succeeded}"
    assert stats.results.malformed == 0
    assert stats.results.errors == 0

    _header("5. ResultStore visibility")
    for aid in proposed_ids:
        ir = store.get(aid)
        assert ir is not None, f"result missing for {aid}"
        assert ir.node_id == TEST_NODE
        print(f"  {aid} → {ir.status} (fallback={ir.is_fallback}) — {ir.detail}")
    assert len(store.by_node(TEST_NODE)) == 2

    _header("6. Reconcile ritual against ResultStore")
    summary = reconcile_ritual(rid)
    assert summary is not None, "reconcile returned None"
    print(f"  summary: {summary.as_dict()}")
    assert summary.with_action_id == 2
    assert summary.matched == 2
    assert summary.unmatched == 0
    assert summary.fully_resolved
    assert summary.all_succeeded

    # Ritual outputs should now carry the mirrored result fields
    refreshed = RitualRegistry.default().get(rid)
    body_after = refreshed.outputs.get("body_actions") or []
    for entry in body_after:
        if "action_id" in entry:
            assert "result_status" in entry, f"missing result_status on {entry}"
            print(f"    • {entry['kind']}: {entry['result_status']} — {entry['result_detail']}")
    assert refreshed.outputs.get("result_summary"), "result_summary missing"

    _header("7. Second drain_all is empty (atomic clear)")
    stats2 = drain_all(TEST_NODE)
    assert stats2.events.drained == 0
    assert stats2.results.drained == 0
    print(f"  events/results drained: {stats2.events.drained}/{stats2.results.drained}")

    _header("8. FOCUS_APP round-trip (graceful fallback on headless)")
    focus_action = propose_focus_app(TEST_NODE, "vscode", issued_by="smoke")
    assert focus_action.action_id, "focus_app action_id missing"
    daemon._tick()  # noqa: SLF001
    stats3 = drain_all(TEST_NODE)
    print(f"  results: {stats3.results.as_dict()}")
    focus_ir = store.get(focus_action.action_id)
    assert focus_ir is not None, "focus result missing from store"
    assert focus_ir.status == "succeeded", f"focus status {focus_ir.status}"
    print(f"  focus_app → {focus_ir.status} (fallback={focus_ir.is_fallback}) — {focus_ir.detail}")

    _header("9. Malformed result is rejected cleanly")
    bus._inbox_append(TEST_NODE, {"type": "result", "payload": {"status": "succeeded"}})  # noqa: SLF001
    bus._inbox_append(TEST_NODE, {"type": "result", "payload": "not-a-dict"})  # noqa: SLF001
    stats4 = drain_all(TEST_NODE)
    print(f"  results: {stats4.results.as_dict()}")
    assert stats4.results.drained == 0
    assert stats4.results.malformed == 2
    assert stats4.results.errors == 0

    _header("RESULT LOOP SMOKE TEST PASSED")
    print("  verified: propose → execute → result → store → reconcile → ritual visibility")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
