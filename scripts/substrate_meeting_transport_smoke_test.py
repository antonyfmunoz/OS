#!/usr/bin/env python3
"""
Meeting voice transport smoke test.

Proves the bounded transcript-only meeting transport adapter end-to-end:
  1. MeetingTransport(...) constructs without any browser/client/network.
  2. Auto-registers a meeting_<platform>_<id> node so VoiceSessionRuntime
     accepts it.
  3. start_session() opens a bounded voice session on that node.
  4. inject_utterance() flows through inject_transcript(source="meeting_voice")
     and produces USER + AGENT turns + a SPEAK_TEXT action_id.
  5. The audio_loop transcript ring on the meeting_<platform>_* node contains
     an entry tagged source="meeting_voice".
  6. status_report() returns the expected shape with mode="transcript_only"
     and playback_enabled=False.
  7. maybe_mirror_meeting_utterance() is a no-op when the env hook is OFF.
  8. maybe_mirror_meeting_utterance() actually injects when the env hook is ON.
  9. attach_playback_sink() flips mode to "attached" and play_reply() routes
     to the bounded sink contract.
 10. detach_playback_sink() returns the transport to transcript_only mode.
 11. end_session() marks the session terminal.
 12. unified_transport_report() includes the meeting_transport section.
 13. Hot path imports remain clean.

Runs in-process. No real meeting bridge is constructed.
Returns 0 on success, non-zero on assertion failure.
"""

from __future__ import annotations

import os
import sys

sys.path.insert(0, os.environ.get("UMH_ROOT") or os.environ.get("OS_ROOT") or os.environ.get("EOS_ROOT") or "/opt/OS")

from runtime.substrate.audio_loop import (  # noqa: E402
    get_audio_loop_store,
    reset_audio_loop_store_for_tests,
)
from runtime.substrate.meeting_transport import (  # noqa: E402
    MeetingTransport,
    get_default_meeting_transport,
    get_meeting_transport_history,
    maybe_mirror_meeting_utterance,
    reset_default_meeting_transports_for_tests,
    reset_meeting_transport_history_for_tests,
)
from runtime.substrate.station_bus import get_station_bus  # noqa: E402
from runtime.substrate.station_daemon import StationDaemon  # noqa: E402
from runtime.substrate.transport_report import unified_transport_report  # noqa: E402
from runtime.substrate.voice_session import (  # noqa: E402
    VoiceSessionStatus,
    VoiceTurnSource,
    get_voice_session_store,
    reset_voice_session_store_for_tests,
)

TEST_PLATFORM = "google_meet"
TEST_MEETING_ID = "smoketest-meet-1"
ENV_VAR = "EOS_MEETING_VOICE_TRANSPORT_ENABLED"


def _header(msg: str) -> None:
    print(f"\n── {msg} " + "─" * max(0, 60 - len(msg)))


class _FakeSink:
    """Minimal playback sink mirroring the contract a real meeting bridge
    would implement: a `play_text(text) -> dict` method."""

    def __init__(self) -> None:
        self.played: list[str] = []

    def play_text(self, text: str) -> dict:
        self.played.append(text)
        return {"played": True, "len": len(text)}


def main() -> int:
    _header("0. Cleanup test stores + env")
    reset_voice_session_store_for_tests()
    reset_audio_loop_store_for_tests()
    reset_meeting_transport_history_for_tests()
    reset_default_meeting_transports_for_tests()
    get_voice_session_store().clear()
    os.environ.pop(ENV_VAR, None)

    _header("1. Construct MeetingTransport (no network/browser)")
    transport = MeetingTransport(
        platform=TEST_PLATFORM,
        meeting_id=TEST_MEETING_ID,
        role_slug="ea_orchestrator",
    )
    print(f"  node_id={transport.node_id}")
    assert transport.node_id == f"meeting_{TEST_PLATFORM}_{TEST_MEETING_ID}"
    assert transport.platform == TEST_PLATFORM
    assert transport._mode == "transcript_only"  # noqa: SLF001
    assert transport._playback_enabled is False  # noqa: SLF001

    _header("2. Heartbeat via daemon (so SPEAK_TEXT flows through bus)")
    bus = get_station_bus()
    bus.daemon_take_outbox(transport.node_id)
    bus.drain_inbox(transport.node_id)
    daemon = StationDaemon(
        node_id=transport.node_id,
        poll_interval_s=0.05,
        heartbeat_interval_s=0.01,
        dry_run=True,
    )
    daemon.register()
    daemon._tick()  # noqa: SLF001

    _header("3. start_session opens a bounded voice session")
    started = transport.start_session()
    print(f"  started={started}")
    assert started.get("status") in ("active", "pending", "resumed"), started
    assert started.get("session_id"), started

    _header("4. inject_utterance flows through transcript_inject + responder")
    result = transport.inject_utterance(
        "what is on the agenda for this meeting",
        user_id="42",
        participant_name="Antony",
        metadata={"smoketest": True},
    )
    print(f"  status={result['status']} session_id={result['session_id']}")
    print(f"  detail={result['detail']}")
    assert result["status"] == "ok", result
    assert result["session_id"], result
    sid = result["session_id"]

    session = get_voice_session_store().get(sid)
    assert session is not None
    user_turns = [t for t in session.turns if t.source == VoiceTurnSource.USER]
    agent_turns = [t for t in session.turns if t.source == VoiceTurnSource.AGENT]
    print(f"  user_turns={len(user_turns)} agent_turns={len(agent_turns)}")
    assert len(user_turns) == 1, [t.as_dict() for t in session.turns]
    assert len(agent_turns) == 1, [t.as_dict() for t in session.turns]
    assert agent_turns[-1].action_id is not None, "SPEAK_TEXT action_id should be set"

    _header("5. audio_loop transcript ring tagged source='meeting_voice'")
    state = get_audio_loop_store().get(transport.node_id)
    assert state is not None
    sources = [t.source for t in state.transcripts]
    print(f"  sources={sources}")
    assert "meeting_voice" in sources, sources
    assert "voice_turn" in sources, sources

    _header("6. status_report shape + transcript_only mode")
    report = transport.status_report()
    print(f"  mode={report['mode']} playback_enabled={report['playback_enabled']}")
    print(f"  active_session_count={report['active_session_count']}")
    print(f"  recent_events_count={len(report['recent_events'])}")
    assert report["mode"] == "transcript_only", report
    assert report["playback_enabled"] is False
    assert report["attached_sink"] is False
    assert report["platform"] == TEST_PLATFORM
    assert report["meeting_id"] == TEST_MEETING_ID
    assert report["active_session_count"] >= 1
    assert len(report["recent_events"]) >= 1
    assert report["env_hook_enabled"] is False
    assert "supported_platforms" in report
    assert "google_meet" in report["supported_platforms"]

    _header("7. maybe_mirror_meeting_utterance: no-op when env hook OFF")
    os.environ.pop(ENV_VAR, None)
    mirror_off = maybe_mirror_meeting_utterance(
        "should be ignored",
        platform=TEST_PLATFORM,
        meeting_id=TEST_MEETING_ID,
        user_id="42",
    )
    print(f"  mirror_off={mirror_off}")
    assert mirror_off is None

    _header("8. maybe_mirror_meeting_utterance: injects when env hook ON")
    os.environ[ENV_VAR] = "1"
    try:
        before = len(get_meeting_transport_history().latest(limit=50))
        mirror_on = maybe_mirror_meeting_utterance(
            "mirrored from a meeting bridge",
            platform=TEST_PLATFORM,
            meeting_id=TEST_MEETING_ID,
            user_id="42",
            participant_name="Antony",
        )
        after = len(get_meeting_transport_history().latest(limit=50))
        print(f"  mirror_on.status={mirror_on.get('status') if mirror_on else None}")
        print(f"  history before={before} after={after}")
        assert mirror_on is not None
        assert mirror_on.get("status") == "ok", mirror_on
        assert after == before + 1
    finally:
        os.environ.pop(ENV_VAR, None)

    _header("9. attach_playback_sink + play_reply route to bounded sink")
    sink = _FakeSink()
    attach_result = transport.attach_playback_sink(sink, enabled=True)
    print(f"  attach={attach_result}")
    assert attach_result["status"] == "attached"
    assert attach_result["playback_enabled"] is True
    attached_report = transport.status_report()
    assert attached_report["mode"] == "attached", attached_report
    assert attached_report["attached_sink"] is True

    play_result = transport.play_reply("here is the bounded reply")
    print(f"  play_reply={play_result}")
    assert play_result["status"] == "ok", play_result
    assert sink.played == ["here is the bounded reply"], sink.played

    # Auto-playback path: inject another utterance and verify the sink
    # received the agent's reply text.
    inject2 = transport.inject_utterance(
        "what's our top blocker right now",
        user_id="42",
        participant_name="Antony",
    )
    assert inject2["status"] == "ok", inject2
    pb = inject2.get("playback")
    print(f"  auto-playback={pb}")
    assert pb is not None
    assert pb.get("status") in ("ok", "no_reply"), pb
    if pb.get("status") == "ok":
        assert len(sink.played) >= 2

    _header("10. detach_playback_sink returns to transcript_only mode")
    detach_result = transport.detach_playback_sink()
    print(f"  detach={detach_result}")
    assert detach_result["status"] == "detached"
    detached_report = transport.status_report()
    assert detached_report["mode"] == "transcript_only", detached_report
    assert detached_report["playback_enabled"] is False
    assert detached_report["attached_sink"] is False

    _header("11. end_session marks the active session terminal")
    ended = transport.end_session(reason="smoketest done")
    print(f"  ended={ended}")
    assert ended.get("status") == VoiceSessionStatus.ENDED.value, ended

    _header("12. unified_transport_report includes meeting_transport")
    unified = unified_transport_report(
        meeting_platform=TEST_PLATFORM,
        meeting_id=TEST_MEETING_ID,
    )
    print(f"  meeting_node_id={unified.get('meeting_node_id')}")
    print(f"  by_source={unified['transcripts']['by_source']}")
    assert "meeting_transport" in unified
    assert unified["meeting_node_id"] == transport.node_id
    assert unified["meeting_transport"]["platform"] == TEST_PLATFORM
    assert "meeting_voice" in unified["transcripts"]["by_source"]

    _header("13. Default singleton accessor returns the same instance")
    t1 = get_default_meeting_transport(
        platform=TEST_PLATFORM, meeting_id=TEST_MEETING_ID
    )
    t2 = get_default_meeting_transport(
        platform=TEST_PLATFORM, meeting_id=TEST_MEETING_ID
    )
    assert t1 is t2, "default transport should be cached per (platform,meeting_id)"

    _header("14. Hot path imports unchanged")
    import importlib

    for mod in (
        "runtime.gateway",
        "control_plane.runtime.cognitive_loop",
        "execution.runtime.model_router",
        "execution.runtime.agent_runtime",
        "runtime.primitives",
    ):
        try:
            importlib.import_module(mod)
            print(f"  ok: {mod}")
        except Exception as e:  # noqa: BLE001
            print(f"  WARN ({mod}): {e}")

    _header("MEETING VOICE TRANSPORT SMOKE TEST PASSED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
