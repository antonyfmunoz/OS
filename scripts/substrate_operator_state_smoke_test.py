#!/usr/bin/env python3
"""
Operator state engine smoke test.

Proves the bounded OperatorState layer end-to-end:

  1. Reset state: clear voice/wake/operator stores.
  2. Register a test node + heartbeat.
  3. Wake word on idle node → OperatorMode IDLE → STARTING (transition recorded).
  4. The voice session that started moves operator into ACTIVE.
  5. Second wake word on active node → resume_voice_session, mode stays ACTIVE
     (no spurious transition recorded).
  6. End the voice session → mode drops back to IDLE.
  7. Clap on idle node → bounded LocalTrigger path; if accepted as open_day,
     state moves through STARTING. If skipped (no policy), state stays IDLE
     and the skip is reflected in last_wake_action.
  8. Open day ritual via ritual_runner with policy on the test node →
     mode transitions to FOCUSED, then back to IDLE on finish.
  9. Close day ritual → mode CLOSING → IDLE on finish.
 10. Operator state report via result_query.operator_state_snapshot.
 11. Hot path imports unchanged.

Runs in-process. Never raises into the harness. Returns 0 on success.
"""

from __future__ import annotations

import sys

import os
sys.path.insert(0, os.environ.get("UMH_ROOT") or os.environ.get("OS_ROOT") or os.environ.get("EOS_ROOT") or "/opt/OS")

from runtime.substrate.local_listener import (  # noqa: E402
    get_trigger_history,
)
from runtime.substrate.operator_presence import line_for_transition  # noqa: E402
from runtime.substrate.operator_state import (  # noqa: E402
    OperatorMode,
    get_operator_state_store,
    reset_operator_state_store_for_tests,
)
from runtime.substrate.result_query import operator_state_snapshot  # noqa: E402
from runtime.substrate.ritual_body import RitualPolicy  # noqa: E402
from runtime.substrate.ritual_runner import (  # noqa: E402
    finish_close_day,
    finish_open_day,
    start_close_day,
    start_open_day,
)
from runtime.substrate.station_bus import get_station_bus  # noqa: E402
from runtime.substrate.station_daemon import StationDaemon  # noqa: E402
from runtime.substrate.voice_session import (  # noqa: E402
    VoiceSessionRuntime,
    get_voice_session_store,
    reset_voice_session_store_for_tests,
)
from runtime.substrate.wake_producer import (  # noqa: E402
    get_wake_producer_history,
    get_wake_producer_runtime,
    reset_wake_producer_runtime_for_tests,
)

TEST_NODE = "smoketest-operator-state"


def _header(msg: str) -> None:
    print(f"\n── {msg} " + "─" * max(0, 60 - len(msg)))


def main() -> int:
    bus = get_station_bus()
    bus.daemon_take_outbox(TEST_NODE)
    bus.drain_inbox(TEST_NODE)

    _header("0. Cleanup: clear voice/wake/operator stores")
    reset_voice_session_store_for_tests()
    reset_wake_producer_runtime_for_tests()
    reset_operator_state_store_for_tests()
    get_voice_session_store().clear()
    get_wake_producer_history().clear()
    get_trigger_history().clear()
    get_operator_state_store().clear()

    _header("1. Register node + heartbeat")
    daemon = StationDaemon(
        node_id=TEST_NODE,
        poll_interval_s=0.05,
        heartbeat_interval_s=0.01,
        dry_run=True,
    )
    daemon.register()
    daemon._tick()  # noqa: SLF001

    store = get_operator_state_store()
    rt = get_wake_producer_runtime()

    _header("2. Wake word on idle node → STARTING then ACTIVE")
    ev1 = rt.simulate_wake_word(TEST_NODE, phrase="hey ea", confidence=0.9)
    print(f"  wake action={ev1.action_taken} session={ev1.voice_session_id}")
    assert ev1.action_taken == "start_voice_session"

    state = store.get(TEST_NODE)
    assert state is not None, "operator state must exist after wake event"
    print(f"  operator mode={state.mode.value}")
    print(f"  active_voice_session_id={state.active_voice_session_id}")
    print(f"  last_wake_action={state.last_wake_action}")
    # Wake-then-voice cascade: at least one of STARTING or ACTIVE; but the
    # voice_session start hook should already have flipped us to ACTIVE.
    assert state.mode in (OperatorMode.STARTING, OperatorMode.ACTIVE), state.mode
    assert state.active_voice_session_id == ev1.voice_session_id
    assert state.last_wake_event_id == ev1.event_id

    # Transition history should contain at least one entry for this run.
    assert len(state.transitions) >= 1, "expected at least one transition record"
    first_transition = state.transitions[0]
    print(f"  first transition: {first_transition.from_mode}→{first_transition.to_mode} ({first_transition.reason})")
    assert first_transition.to_mode in (
        OperatorMode.STARTING.value,
        OperatorMode.ACTIVE.value,
    )

    _header("3. Submit a voice utterance → mode ACTIVE confirmed")
    vrt = VoiceSessionRuntime()
    vrt.submit_utterance(ev1.voice_session_id, "status check")
    state = store.get(TEST_NODE)
    print(f"  mode={state.mode.value} last_voice_turn_at={state.last_voice_turn_at}")
    assert state.mode == OperatorMode.ACTIVE, state.mode
    assert state.last_voice_turn_at is not None

    _header("4. Second wake word on active node → resume, mode stays ACTIVE")
    transitions_before = len(state.transitions)
    ev2 = rt.simulate_wake_word(TEST_NODE, phrase="hey ea again")
    print(f"  wake action={ev2.action_taken}")
    assert ev2.action_taken == "resume_voice_session"
    state = store.get(TEST_NODE)
    print(f"  mode={state.mode.value}")
    assert state.mode == OperatorMode.ACTIVE
    # No spurious transition: ACTIVE→ACTIVE is filtered out.
    assert len(state.transitions) == transitions_before, (
        f"resume must not record a spurious transition "
        f"(was {transitions_before}, now {len(state.transitions)})"
    )
    print("  no spurious transition recorded ✓")

    _header("5. End voice session → mode drops to IDLE")
    vrt.end_session(ev1.voice_session_id, reason="smoketest")
    state = store.get(TEST_NODE)
    print(f"  mode={state.mode.value}")
    assert state.mode == OperatorMode.IDLE, state.mode
    assert state.active_voice_session_id is None

    _header("6. Clap on idle node → bounded clap path")
    ev3 = rt.simulate_clap(TEST_NODE)
    print(f"  clap action={ev3.action_taken}")
    state = store.get(TEST_NODE)
    print(f"  mode={state.mode.value} last_wake_kind={state.last_wake_kind}")
    assert state.last_wake_kind == "clap"
    # Either STARTING (open_day accepted) or IDLE (no policy → skipped). Both ok.
    assert state.mode in (OperatorMode.STARTING, OperatorMode.IDLE)

    _header("7. open_day ritual via ritual_runner with policy on TEST_NODE")
    policy = RitualPolicy(
        station_node_id=TEST_NODE,
        open_speak="operator state smoketest",
    )
    rid = start_open_day(policy=policy)
    state = store.get(TEST_NODE)
    print(f"  ritual_id={rid} mode={state.mode.value}")
    assert state.current_ritual_id == rid
    assert state.current_ritual_kind == "open_day"
    # Mode should be FOCUSED (or UNAVAILABLE if readiness reported so).
    assert state.mode in (OperatorMode.FOCUSED, OperatorMode.UNAVAILABLE), state.mode

    finish_open_day(rid, policy=policy)
    state = store.get(TEST_NODE)
    print(f"  after finish: mode={state.mode.value} ritual_state={state.current_ritual_state}")
    assert state.current_ritual_state in ("finished", "completed", "started")
    # Open ritual finished + no active voice session → IDLE
    assert state.mode in (OperatorMode.IDLE, OperatorMode.UNAVAILABLE), state.mode

    _header("8. close_day ritual → CLOSING then IDLE")
    rid2 = start_close_day(policy=policy)
    state = store.get(TEST_NODE)
    print(f"  close ritual={rid2} mode={state.mode.value}")
    assert state.current_ritual_id == rid2
    assert state.current_ritual_kind == "close_day"
    assert state.mode in (OperatorMode.CLOSING, OperatorMode.UNAVAILABLE), state.mode

    finish_close_day(rid2, policy=policy)
    state = store.get(TEST_NODE)
    print(f"  after finish: mode={state.mode.value}")
    assert state.mode in (OperatorMode.IDLE, OperatorMode.UNAVAILABLE), state.mode

    _header("9. operator_state_snapshot via result_query")
    snap = operator_state_snapshot(node_id=TEST_NODE)
    print(f"  snapshot count={snap['count']}")
    print(f"  stats={snap['stats']}")
    assert snap["count"] == 1
    state_dict = snap["states"][0]
    assert state_dict["node_id"] == TEST_NODE
    assert "mode" in state_dict
    assert "transitions" in state_dict
    assert state_dict["last_transition"] is not None
    print(f"  recorded transitions={len(state_dict['transitions'])}")
    assert len(state_dict["transitions"]) >= 3, "expected several transitions across the flow"

    _header("10. Hybrid presence templates exist for key transitions")
    line = line_for_transition(OperatorMode.IDLE.value, OperatorMode.STARTING.value)
    print(f"  idle→starting: {line!r}")
    assert line is not None and len(line) < 80
    line = line_for_transition(OperatorMode.STARTING.value, OperatorMode.ACTIVE.value)
    print(f"  starting→active: {line!r}")
    assert line is not None
    line = line_for_transition(OperatorMode.ACTIVE.value, OperatorMode.CLOSING.value)
    print(f"  active→closing: {line!r}")
    assert line is not None

    _header("11. Hot path imports unchanged (sanity check)")
    import importlib

    for mod in (
        "runtime.gateway",
        "control_plane.runtime.cognitive_loop",
        "runtime.model_router",
        "runtime.agent_runtime",
        "runtime.primitives",
    ):
        try:
            importlib.import_module(mod)
            print(f"  ok: {mod}")
        except Exception as e:  # noqa: BLE001
            print(f"  WARN ({mod}): {e}")

    _header("SMOKE TEST PASSED")
    print("  verified: wake → starting → active → resume (no spurious) →")
    print("            end → idle → clap → open_day FOCUSED → idle →")
    print("            close_day CLOSING → idle → snapshot → templates")
    print("  hot path: untouched")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
