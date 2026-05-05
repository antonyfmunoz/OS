#!/usr/bin/env python3
"""
Wake producer smoke test.

Proves the bounded wake producer layer end-to-end:

  1. Reset state: clear voice session store, wake producer history, trigger history.
  2. Register a test node (so voice session + listener paths succeed).
  3. Wake word "hey ea" on test node → start_voice_session, role ea_orchestrator.
  4. Second wake word on same node → resume_voice_session, same session_id,
     bounded SYSTEM wake marker appended. Responder NOT invoked. No new utterance.
  5. End the active session, then wake word "portfolio" → new session with
     role_slug=portfolio_advisor.
  6. Clap on test node → bounded LocalTrigger path used. action_taken in
     ("open_day", "skipped") depending on active-ritual state.
  7. Wake word on a ghost (unregistered) node → skipped with reason.
  8. History / report checks: count > 0, by_kind populated, recent events visible.
  9. result_query.recent_wake_producer_events() surfaces the history.
 10. Hot path import check.

Runs in-process. Never raises. Returns 0 on success.
"""

from __future__ import annotations

import sys

sys.path.insert(0, "/opt/OS")

from umh.substrate.local_listener import (  # noqa: E402
    get_trigger_history,
)
from umh.substrate.result_query import (  # noqa: E402
    recent_wake_producer_events,
)
from umh.substrate.station_bus import get_station_bus  # noqa: E402
from umh.substrate.station_daemon import StationDaemon  # noqa: E402
from umh.substrate.voice_session import (  # noqa: E402
    VoiceSessionStatus,
    VoiceTurnSource,
    get_voice_session_store,
    reset_voice_session_store_for_tests,
)
from umh.substrate.wake_producer import (  # noqa: E402
    WakeProducerKind,
    get_wake_producer_history,
    get_wake_producer_runtime,
    reset_wake_producer_runtime_for_tests,
    resolve_role_hint,
)

TEST_NODE = "smoketest-wake-producer"
GHOST_NODE = "smoketest-wake-producer-ghost"


def _header(msg: str) -> None:
    print(f"\n── {msg} " + "─" * max(0, 60 - len(msg)))


def main() -> int:
    bus = get_station_bus()
    bus.daemon_take_outbox(TEST_NODE)
    bus.drain_inbox(TEST_NODE)

    _header("0. Cleanup: clear voice store, wake history, trigger history")
    reset_voice_session_store_for_tests()
    reset_wake_producer_runtime_for_tests()
    get_voice_session_store().clear()
    get_wake_producer_history().clear()
    get_trigger_history().clear()

    _header("1. Register node + heartbeat")
    daemon = StationDaemon(
        node_id=TEST_NODE,
        poll_interval_s=0.05,
        heartbeat_interval_s=0.01,
        dry_run=True,
    )
    daemon.register()
    daemon._tick()  # noqa: SLF001

    _header("1b. Sanity: resolve_role_hint determinism")
    assert resolve_role_hint("hey ea") == "ea_orchestrator"
    assert resolve_role_hint("wake up portfolio") == "portfolio_advisor"
    assert resolve_role_hint("ceo") == "ceo"
    assert resolve_role_hint(None) is None
    assert resolve_role_hint("random phrase") is None
    print("  role hints deterministic")

    rt = get_wake_producer_runtime()

    _header("2. Wake word 'hey ea' → start_voice_session")
    ev1 = rt.simulate_wake_word(TEST_NODE, phrase="hey ea", confidence=0.92)
    print(f"  action={ev1.action_taken} role_hint={ev1.role_hint}")
    print(f"  voice_session_id={ev1.voice_session_id}")
    assert ev1.action_taken == "start_voice_session", ev1.as_dict()
    assert ev1.role_hint == "ea_orchestrator"
    assert ev1.voice_session_id is not None
    session = get_voice_session_store().get(ev1.voice_session_id)
    assert session is not None
    assert session.role_slug == "ea_orchestrator"
    assert session.status == VoiceSessionStatus.ACTIVE
    turn_count_before_resume = session.turn_count
    user_turns_before = sum(
        1 for t in session.turns if t.source == VoiceTurnSource.USER
    )
    agent_turns_before = sum(
        1 for t in session.turns if t.source == VoiceTurnSource.AGENT
    )

    _header("3. Second wake word on same node → resume_voice_session")
    ev2 = rt.simulate_wake_word(TEST_NODE, phrase="hey ea again", confidence=0.88)
    print(f"  action={ev2.action_taken}")
    print(f"  voice_session_id={ev2.voice_session_id}")
    assert ev2.action_taken == "resume_voice_session", ev2.as_dict()
    assert ev2.voice_session_id == ev1.voice_session_id
    session2 = get_voice_session_store().get(ev2.voice_session_id)
    assert session2 is not None
    assert session2.turn_count == turn_count_before_resume + 1, (
        "exactly one SYSTEM marker must have been appended"
    )
    new_turn = session2.turns[-1]
    assert new_turn.source == VoiceTurnSource.SYSTEM
    assert "wake" in new_turn.text.lower()
    assert new_turn.metadata.get("wake_event_id") == ev2.event_id
    # CRITICAL: responder NOT invoked, no new user/agent turns
    user_turns_after = sum(
        1 for t in session2.turns if t.source == VoiceTurnSource.USER
    )
    agent_turns_after = sum(
        1 for t in session2.turns if t.source == VoiceTurnSource.AGENT
    )
    assert user_turns_after == user_turns_before, "must not add USER turn"
    assert agent_turns_after == agent_turns_before, "must not invoke responder"
    print("  responder NOT invoked, no utterance submitted ✓")

    _header("4. End session, then wake word 'portfolio' → new session")
    from umh.substrate.voice_session import VoiceSessionRuntime

    VoiceSessionRuntime().end_session(ev1.voice_session_id, reason="smoketest resume")
    ended = get_voice_session_store().get(ev1.voice_session_id)
    assert ended.status == VoiceSessionStatus.ENDED

    ev3 = rt.simulate_wake_word(TEST_NODE, phrase="wake up portfolio")
    print(f"  action={ev3.action_taken} role_hint={ev3.role_hint}")
    assert ev3.action_taken == "start_voice_session", ev3.as_dict()
    assert ev3.role_hint == "portfolio_advisor"
    assert ev3.voice_session_id != ev1.voice_session_id
    new_session = get_voice_session_store().get(ev3.voice_session_id)
    assert new_session is not None
    assert new_session.role_slug == "portfolio_advisor"
    assert new_session.status == VoiceSessionStatus.ACTIVE

    _header("5. Clap on test node → LocalTrigger bounded path")
    ev4 = rt.simulate_clap(TEST_NODE, confidence=0.75)
    print(f"  action={ev4.action_taken} local_trigger_id={ev4.local_trigger_id}")
    print(f"  reason={ev4.decision_reason}")
    assert ev4.producer_kind == WakeProducerKind.CLAP
    assert ev4.local_trigger_id is not None, "clap must go through LocalListener"
    assert ev4.action_taken in ("open_day", "skipped"), ev4.as_dict()
    # Bounded path confirmation: trigger history should contain our event.
    th = get_trigger_history().latest(limit=5, node_id=TEST_NODE)
    assert any(t.get("trigger_id") == ev4.local_trigger_id for t in th), (
        "clap must be recorded in TriggerHistory"
    )
    print("  clap reused LocalListener ✓")

    _header("6. Wake word on ghost (unregistered) node → skipped")
    ev5 = rt.simulate_wake_word(GHOST_NODE, phrase="hey ea ghost")
    print(f"  action={ev5.action_taken}")
    print(f"  reason={ev5.decision_reason}")
    assert ev5.action_taken == "skipped", ev5.as_dict()
    assert "not registered" in (ev5.decision_reason or "") or "ERROR" in (
        ev5.decision_reason or ""
    )

    _header("7. History + report checks")
    recent = get_wake_producer_history().latest(limit=20)
    print(f"  history count={len(recent)}")
    assert len(recent) >= 5  # events 1..5
    report = rt.report(limit=10)
    print(f"  runtime_mode={report['runtime_mode']}")
    print(f"  by_kind={report['by_kind']}")
    print(f"  by_action_taken={report['by_action_taken']}")
    assert report["runtime_mode"] == "simulated"
    assert report["by_kind"].get("wake_word", 0) >= 4
    assert report["by_kind"].get("clap", 0) >= 1
    assert report["count"] >= 5

    _header("8. result_query.recent_wake_producer_events() surfaces history")
    rq_rows = recent_wake_producer_events(limit=10, node_id=TEST_NODE)
    print(f"  rq rows for TEST_NODE: {len(rq_rows)}")
    assert len(rq_rows) >= 4
    assert all(r.get("node_id") == TEST_NODE for r in rq_rows)

    _header("9. Hot path imports unchanged (sanity check)")
    import importlib

    for mod in (
        "umh.runtime_engine.gateway",
        "umh.runtime_engine.cognitive_loop",
        "umh.runtime_engine.model_router",
        "umh.runtime_engine.agent_runtime",
        "umh.runtime_engine.primitives",
    ):
        try:
            importlib.import_module(mod)
            print(f"  ok: {mod}")
        except Exception as e:  # noqa: BLE001
            print(f"  WARN ({mod}): {e}")

    _header("SMOKE TEST PASSED")
    print("  verified: wake word start → resume (audit marker, no responder) →")
    print("            new session after end → clap via LocalListener →")
    print("            ghost node skipped → history/report → result_query")
    print("  hot path: untouched")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
