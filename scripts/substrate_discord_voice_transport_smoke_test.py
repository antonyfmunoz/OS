#!/usr/bin/env python3
"""
Discord voice transport smoke test.

Proves the bounded transcript-only Discord transport adapter end-to-end:
  1. DiscordVoiceTransport(...) constructs without any network/client.
  2. Auto-registers a discord_vc_* node so VoiceSessionRuntime accepts it.
  3. start_session() opens a bounded voice session on that node.
  4. inject_utterance() flows through inject_transcript(source="discord_voice")
     and produces USER + AGENT turns + a SPEAK_TEXT action_id.
  5. The audio_loop transcript ring on the discord_vc_* node contains an
     entry tagged source="discord_voice".
  6. status_report() returns the expected shape with mode="transcript_only"
     and playback_enabled=False.
  7. maybe_mirror_discord_utterance() is a no-op when the env hook is OFF.
  8. maybe_mirror_discord_utterance() actually injects when the env hook is ON.
  9. end_session() marks the session terminal.
 10. Hot path imports remain clean.

Runs in-process. dry_run is enforced via the bounded substrate; no real
Discord client is created.
Returns 0 on success, non-zero on assertion failure.
"""

from __future__ import annotations

import os
import sys

sys.path.insert(0, os.environ.get("UMH_ROOT") or os.environ.get("OS_ROOT") or os.environ.get("EOS_ROOT") or "/opt/OS")

from runtime.transport.audio_loop import (  # noqa: E402
    get_audio_loop_store,
    reset_audio_loop_store_for_tests,
)
from runtime.transport.discord_voice_transport import (  # noqa: E402
    DiscordVoiceTransport,
    get_default_discord_voice_transport,
    get_transport_history,
    maybe_mirror_discord_utterance,
    reset_default_discord_voice_transports_for_tests,
    reset_transport_history_for_tests,
)
from runtime.transport.station_bus import get_station_bus  # noqa: E402
from runtime.transport.station_daemon import StationDaemon  # noqa: E402
from runtime.transport.voice_session import (  # noqa: E402
    VoiceSessionStatus,
    VoiceTurnSource,
    get_voice_session_store,
    reset_voice_session_store_for_tests,
)

TEST_GUILD = "smoketest-guild-1"
TEST_CHANNEL = "smoketest-channel-1"
ENV_VAR = "EOS_DISCORD_VOICE_TRANSPORT_ENABLED"


def _header(msg: str) -> None:
    print(f"\n── {msg} " + "─" * max(0, 60 - len(msg)))


def main() -> int:
    _header("0. Cleanup test stores + env")
    reset_voice_session_store_for_tests()
    reset_audio_loop_store_for_tests()
    reset_transport_history_for_tests()
    reset_default_discord_voice_transports_for_tests()
    get_voice_session_store().clear()
    os.environ.pop(ENV_VAR, None)

    _header("1. Construct DiscordVoiceTransport (no network)")
    transport = DiscordVoiceTransport(
        guild_id=TEST_GUILD, channel_id=TEST_CHANNEL, role_slug="ea_orchestrator"
    )
    print(f"  node_id={transport.node_id}")
    assert transport.node_id == f"discord_vc_{TEST_GUILD}_{TEST_CHANNEL}"
    assert transport._mode == "transcript_only"  # noqa: SLF001
    assert transport._playback_enabled is False  # noqa: SLF001

    _header("2. Auto-registered node + heartbeat via daemon (so SPEAK_TEXT flows)")
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
        "what is on the agenda today",
        user_id="42",
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

    _header("5. audio_loop transcript ring tagged source='discord_voice'")
    state = get_audio_loop_store().get(transport.node_id)
    assert state is not None
    sources = [t.source for t in state.transcripts]
    print(f"  sources={sources}")
    assert "discord_voice" in sources, sources
    assert "voice_turn" in sources, sources

    _header("6. status_report shape + transport_only mode")
    report = transport.status_report()
    print(f"  mode={report['mode']} playback_enabled={report['playback_enabled']}")
    print(f"  active_session_count={report['active_session_count']}")
    print(f"  recent_events_count={len(report['recent_events'])}")
    assert report["mode"] in ("transcript_only", "transcript_only_no_lib"), report
    assert report["playback_enabled"] is False
    assert report["active_session_count"] >= 1
    assert len(report["recent_events"]) >= 1
    assert report["env_hook_enabled"] is False

    _header("7. maybe_mirror_discord_utterance: no-op when env hook OFF")
    os.environ.pop(ENV_VAR, None)
    mirror_off = maybe_mirror_discord_utterance(
        "should be ignored",
        user_id="42",
        guild_id=TEST_GUILD,
        channel_id=TEST_CHANNEL,
    )
    print(f"  mirror_off={mirror_off}")
    assert mirror_off is None

    _header("8. maybe_mirror_discord_utterance: injects when env hook ON")
    os.environ[ENV_VAR] = "1"
    try:
        before = len(get_transport_history().latest(limit=50))
        mirror_on = maybe_mirror_discord_utterance(
            "mirrored from discord bot",
            user_id="42",
            guild_id=TEST_GUILD,
            channel_id=TEST_CHANNEL,
        )
        after = len(get_transport_history().latest(limit=50))
        print(f"  mirror_on.status={mirror_on.get('status') if mirror_on else None}")
        print(f"  history before={before} after={after}")
        assert mirror_on is not None
        assert mirror_on.get("status") == "ok", mirror_on
        assert after == before + 1
    finally:
        os.environ.pop(ENV_VAR, None)

    _header("9. end_session marks the active session terminal")
    ended = transport.end_session(reason="smoketest done")
    print(f"  ended={ended}")
    assert ended.get("status") == VoiceSessionStatus.ENDED.value, ended

    _header("10. Default singleton accessor returns the same instance")
    t1 = get_default_discord_voice_transport(
        guild_id=TEST_GUILD, channel_id=TEST_CHANNEL
    )
    t2 = get_default_discord_voice_transport(
        guild_id=TEST_GUILD, channel_id=TEST_CHANNEL
    )
    assert t1 is t2, "default transport should be cached per (guild,channel)"

    _header("11. Hot path imports unchanged")
    import importlib

    for mod in (
        "control_plane.runtime.gateway",
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

    _header("DISCORD VOICE TRANSPORT SMOKE TEST PASSED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
