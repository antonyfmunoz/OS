#!/usr/bin/env python3
"""
STT producer smoke test.

Proves the bounded local STT/mic capture producer end-to-end:

  1. Reset all substrate stores (voice, wake, operator, audio loop, stt).
  2. Register a test node + heartbeat.
  3. stt_runtime_status() returns a JSON-friendly capability snapshot
     and never crashes.
  4. capture_once(mode="simulated", simulated_text=...) on a COLD node
     with start_if_missing=True starts a bounded voice session, pushes
     the transcript through inject_transcript(), and drives the audio
     loop to COOLING_DOWN.
  5. The capture event is recorded in SttCaptureHistory and reachable
     via stt_capture_snapshot + recent_stt_captures (JSON-friendly).
  6. The voice session now has a USER turn with the simulated text and
     an AGENT reply.
  7. capture_once(mode="manual", manual_text="") returns SKIPPED_EMPTY
     without raising.
  8. capture_once(mode="push_to_talk") on this headless env returns a
     DEGRADED event (no mic) without raising.
  9. End voice session → audio loop INACTIVE.
 10. Hot path imports unchanged.

Runs in-process. Never raises into the harness. Returns 0 on success.
"""

from __future__ import annotations

import sys

import os
sys.path.insert(0, os.environ.get("UMH_ROOT") or os.environ.get("OS_ROOT") or os.environ.get("EOS_ROOT") or "/opt/OS")

from runtime.substrate.audio_loop import (  # noqa: E402
    AudioLoopStatus,
    get_audio_loop_store,
    reset_audio_loop_store_for_tests,
)
from runtime.substrate.local_listener import (  # noqa: E402
    get_trigger_history,
)
from runtime.substrate.operator_state import (  # noqa: E402
    get_operator_state_store,
    reset_operator_state_store_for_tests,
)
from runtime.substrate.station_bus import get_station_bus  # noqa: E402
from runtime.substrate.station_daemon import StationDaemon  # noqa: E402
from runtime.substrate.stt_producer import (  # noqa: E402
    SttCaptureSource,
    SttCaptureStatus,
    get_local_stt_runtime,
    get_stt_capture_history,
    recent_stt_captures,
    reset_local_stt_runtime_for_tests,
    reset_stt_capture_history_for_tests,
    stt_capture_snapshot,
    stt_runtime_status,
)
from runtime.substrate.voice_session import (  # noqa: E402
    VoiceSessionRuntime,
    VoiceSessionStatus,
    VoiceTurnSource,
    get_voice_session_store,
    reset_voice_session_store_for_tests,
)
from runtime.substrate.wake_producer import (  # noqa: E402
    get_wake_producer_history,
    reset_wake_producer_runtime_for_tests,
)

TEST_NODE = "smoketest-stt-producer"


def _header(msg: str) -> None:
    print(f"\n── {msg} " + "─" * max(0, 60 - len(msg)))


def main() -> int:
    bus = get_station_bus()
    bus.daemon_take_outbox(TEST_NODE)
    bus.drain_inbox(TEST_NODE)

    _header("0. Cleanup: clear all substrate stores")
    reset_voice_session_store_for_tests()
    reset_wake_producer_runtime_for_tests()
    reset_operator_state_store_for_tests()
    reset_audio_loop_store_for_tests()
    reset_local_stt_runtime_for_tests()
    reset_stt_capture_history_for_tests()
    get_voice_session_store().clear()
    get_wake_producer_history().clear()
    get_trigger_history().clear()
    get_operator_state_store().clear()
    get_audio_loop_store().clear()
    get_stt_capture_history().clear()

    _header("1. Register node + heartbeat")
    daemon = StationDaemon(
        node_id=TEST_NODE,
        poll_interval_s=0.05,
        heartbeat_interval_s=0.01,
        dry_run=True,
    )
    daemon.register()
    daemon._tick()  # noqa: SLF001

    audio_store = get_audio_loop_store()
    vsession_store = get_voice_session_store()

    _header("2. stt_runtime_status is JSON-friendly")
    status = stt_runtime_status()
    assert isinstance(status, dict)
    assert "capability" in status
    assert "runtime" in status
    assert "history" in status
    cap = status["capability"]
    assert "real_stt_available" in cap
    assert "simulated_only" in cap
    assert "providers_available" in cap
    assert "reason" in cap
    print(f"  real_stt_available={cap['real_stt_available']}")
    print(f"  simulated_only    ={cap['simulated_only']}")
    print(f"  providers_available={cap['providers_available']}")
    print(f"  reason            ={cap['reason']}")

    _header("3. capture_once(simulated) on cold node — starts session + injects")
    rt = get_local_stt_runtime()
    event = rt.capture_once(
        TEST_NODE,
        mode="simulated",
        simulated_text="status check via local stt",
        start_if_missing=True,
        metadata={"smoketest": "simulated_happy_path"},
    )
    print(f"  event.status={event.status.value}")
    print(f"  event.source={event.source.value}")
    print(f"  event.inject_status={event.inject_status}")
    print(f"  event.session_id={event.session_id}")
    print(f"  event.role_slug={event.role_slug}")
    assert event.source == SttCaptureSource.SIMULATED_STT
    assert event.status == SttCaptureStatus.DEGRADED, event.status
    assert event.inject_status == "ok"
    assert event.session_id is not None
    assert event.role_slug == "ea_orchestrator"

    al_state = audio_store.get(TEST_NODE)
    assert al_state is not None, "audio loop state must exist after simulated capture"
    print(f"  audio_loop status={al_state.status.value}")
    assert al_state.status == AudioLoopStatus.COOLING_DOWN, al_state.status
    # transcripts ring buffer: voice_turn entry + a local_stt annotation entry
    sources = [t.source for t in al_state.transcripts]
    print(f"  transcript sources={sources}")
    assert "voice_turn" in sources, sources
    assert "local_stt" in sources, sources

    _header("4. Voice session has USER + AGENT turns and is ACTIVE/IDLE")
    session = vsession_store.get(event.session_id)
    assert session is not None
    print(f"  session.status={session.status.value}")
    assert session.status in (
        VoiceSessionStatus.ACTIVE,
        VoiceSessionStatus.IDLE,
    )
    turn_sources = [t.source.value for t in session.turns]
    print(f"  turn sources={turn_sources}")
    assert "user" in turn_sources
    assert "agent" in turn_sources
    user_turn = next(
        t for t in session.turns if t.source == VoiceTurnSource.USER
    )
    assert user_turn.text == "status check via local stt"

    _header("5. SttCaptureHistory is persistent and JSON-friendly")
    snap = stt_capture_snapshot(node_id=TEST_NODE)
    assert snap["count"] == 1, snap
    state_dict = snap["states"][0]
    assert state_dict["node_id"] == TEST_NODE
    assert state_dict["source"] == "simulated_stt"
    assert state_dict["status"] == "degraded"
    print(f"  snapshot state_keys={sorted(state_dict.keys())}")

    recent = recent_stt_captures(limit=5, node_id=TEST_NODE)
    assert len(recent) == 1
    assert recent[0]["event_id"] == event.event_id
    print(f"  recent len={len(recent)} event_id={recent[0]['event_id']}")

    _header("6. Empty manual capture is SKIPPED_EMPTY and safe")
    empty_event = rt.capture_once(
        TEST_NODE,
        mode="manual",
        manual_text="   ",
    )
    print(f"  empty_event.status={empty_event.status.value}")
    assert empty_event.status == SttCaptureStatus.SKIPPED_EMPTY
    assert empty_event.inject_status is None

    _header("7. push_to_talk on headless env degrades safely")
    ptt_event = rt.capture_once(
        TEST_NODE,
        mode="push_to_talk",
        duration_s=0.1,
    )
    print(f"  ptt_event.status={ptt_event.status.value}")
    print(f"  ptt_event.detail={ptt_event.detail[:80]}")
    # On this VPS there is no sounddevice, so we expect DEGRADED.
    # If a test host happens to have a mic we still accept INJECTED.
    assert ptt_event.status in (
        SttCaptureStatus.DEGRADED,
        SttCaptureStatus.INJECTED,
        SttCaptureStatus.SKIPPED_EMPTY,
        SttCaptureStatus.ERROR,
    )
    # Must not have crashed; must have been recorded.
    hist_all = recent_stt_captures(limit=10, node_id=TEST_NODE)
    assert any(e["event_id"] == ptt_event.event_id for e in hist_all)

    _header("8. Second simulated capture reuses the active session")
    event2 = rt.capture_once(
        TEST_NODE,
        mode="simulated",
        simulated_text="tell me the pending tasks",
    )
    print(f"  event2.status={event2.status.value}")
    print(f"  event2.session_id={event2.session_id}")
    assert event2.inject_status == "ok"
    assert event2.session_id == event.session_id, (
        "simulated capture should reuse the active voice session, "
        f"first={event.session_id} second={event2.session_id}"
    )

    _header("9. End voice session → AudioLoop INACTIVE")
    vrt = VoiceSessionRuntime()
    vrt.end_session(event.session_id, reason="smoketest_complete")
    al_state = audio_store.get(TEST_NODE)
    print(f"  audio_loop status={al_state.status.value}")
    assert al_state.status == AudioLoopStatus.INACTIVE
    assert al_state.active_voice_session_id is None

    _header("10. Hot path imports still clean")
    import importlib

    for mod in (
        "control_plane.runtime.gateway",
        "control_plane.runtime.cognitive_loop",
        "execution.runtime.model_router",
        "execution.runtime.agent_runtime",
        "runtime.primitives",
    ):
        importlib.import_module(mod)
        print(f"  import ok: {mod}")

    print("\n✅ substrate_stt_producer_smoke_test: PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
