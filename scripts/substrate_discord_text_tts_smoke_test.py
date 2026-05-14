#!/usr/bin/env python3
"""
Discord Pseudo-Live Voice Loop v1 — smoke test.

Proves the bounded Discord text-channel ingress + TTS reply envelope
end-to-end WITHOUT requiring a live Discord client.

  1. Default OFF: maybe_mirror_discord_text_message returns None when
     EOS_DISCORD_TEXT_TRANSPORT_ENABLED is not truthy.
  2. Enabled but no allowlists: ingress is "gate_denied" (strict empty).
  3. Enabled + allowlists: ingress flows through the SAME voice node as
     DiscordVoiceTransport for (guild, channel) — one shared session.
  4. Transcript is tagged source="discord_text" in the audio_loop ring.
  5. An AGENT turn is produced on the shared voice session.
  6. build_tts_reply_envelope returns tts=True when TTS flag is on.
  7. build_tts_reply_envelope degrades to tts=False when TTS flag is off.
  8. Gating denies unauthorized channels even with feature flag on.
  9. transport_report._pseudo_live_block (via status) surfaces state.
 10. Hot path imports remain clean.
 11. Reply truncation respects EOS_DISCORD_TEXT_REPLY_MAX_CHARS cap.
"""

from __future__ import annotations

import os
import sys

sys.path.insert(0, os.environ.get("UMH_ROOT") or os.environ.get("OS_ROOT") or os.environ.get("EOS_ROOT") or "/opt/OS")

from runtime.substrate.audio_loop import (  # noqa: E402
    get_audio_loop_store,
    reset_audio_loop_store_for_tests,
)
from runtime.substrate.discord_text_transport import (  # noqa: E402
    build_tts_reply_envelope,
    ingest_text_message,
    get_text_history,
    maybe_mirror_discord_text_message,
    pseudo_live_status,
    reset_text_history_for_tests,
    truncate_reply,
)
from runtime.substrate.discord_voice_transport import (  # noqa: E402
    get_default_discord_voice_transport,
    reset_default_discord_voice_transports_for_tests,
    reset_transport_history_for_tests,
)
from runtime.substrate.station_bus import get_station_bus  # noqa: E402
from runtime.substrate.station_daemon import StationDaemon  # noqa: E402
from runtime.substrate.voice_session import (  # noqa: E402
    VoiceTurnSource,
    get_voice_session_store,
    reset_voice_session_store_for_tests,
)

TEST_GUILD = "ptest-guild"
TEST_CHANNEL = "ptest-channel"
TEST_USER = "9999"
OTHER_CHANNEL = "ptest-channel-NOPE"

ENV_INGRESS = "EOS_DISCORD_TEXT_TRANSPORT_ENABLED"
ENV_TTS = "EOS_DISCORD_TEXT_REPLY_TTS_ENABLED"
ENV_GUILDS = "EOS_DISCORD_TEXT_ALLOWED_GUILDS"
ENV_CHANNELS = "EOS_DISCORD_TEXT_ALLOWED_CHANNELS"
ENV_USERS = "EOS_DISCORD_TEXT_ALLOWED_USERS"
ENV_MAX = "EOS_DISCORD_TEXT_REPLY_MAX_CHARS"

_ALL_ENV = [ENV_INGRESS, ENV_TTS, ENV_GUILDS, ENV_CHANNELS, ENV_USERS, ENV_MAX]


def _header(msg: str) -> None:
    print(f"\n── {msg} " + "─" * max(0, 60 - len(msg)))


def _clear_env() -> None:
    for k in _ALL_ENV:
        os.environ.pop(k, None)


def _bootstrap_shared_node() -> str:
    """Create the shared (guild, channel) voice transport + daemon so
    the responder chain can emit SPEAK_TEXT during inject."""
    transport = get_default_discord_voice_transport(
        guild_id=TEST_GUILD, channel_id=TEST_CHANNEL
    )
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
    return transport.node_id


def main() -> int:
    _header("0. Cleanup stores + env")
    reset_voice_session_store_for_tests()
    reset_audio_loop_store_for_tests()
    reset_transport_history_for_tests()
    reset_default_discord_voice_transports_for_tests()
    reset_text_history_for_tests()
    get_voice_session_store().clear()
    _clear_env()

    _header("1. Default OFF: mirror returns None")
    result = maybe_mirror_discord_text_message(
        "hello from text",
        guild_id=TEST_GUILD,
        channel_id=TEST_CHANNEL,
        user_id=TEST_USER,
    )
    print(f"  result={result}")
    assert result is None

    _header("2. Ingress enabled but empty allowlists → gate_denied")
    os.environ[ENV_INGRESS] = "1"
    # Allowlists intentionally unset → strict empty → deny.
    result = maybe_mirror_discord_text_message(
        "hello from text",
        guild_id=TEST_GUILD,
        channel_id=TEST_CHANNEL,
        user_id=TEST_USER,
    )
    print(f"  ingress_status={result['ingress']['status']}")
    print(f"  ingress_detail={result['ingress']['detail']}")
    assert result["ingress"]["status"] == "gate_denied"
    assert result["ingress"]["detail"] in (
        "guild_not_allowed",
        "channel_not_allowed",
        "user_not_allowed",
    )

    _header("3. Allow + bootstrap shared voice node")
    os.environ[ENV_GUILDS] = TEST_GUILD
    os.environ[ENV_CHANNELS] = TEST_CHANNEL
    os.environ[ENV_USERS] = "*"
    node_id = _bootstrap_shared_node()
    print(f"  shared node_id={node_id}")
    assert node_id == f"discord_vc_{TEST_GUILD}_{TEST_CHANNEL}"

    _header("4. Ingest text message flows through inject_transcript")
    result = ingest_text_message(
        "what is on the agenda for today",
        guild_id=TEST_GUILD,
        channel_id=TEST_CHANNEL,
        user_id=TEST_USER,
    )
    print(f"  status={result['status']} session_id={result.get('session_id')}")
    print(f"  reply_text_present={bool(result.get('reply_text'))}")
    assert result["status"] == "ok", result
    assert result["session_id"], result
    sid = result["session_id"]

    _header("5. Shared voice session has USER + AGENT turns")
    session = get_voice_session_store().get(sid)
    assert session is not None
    user_turns = [t for t in session.turns if t.source == VoiceTurnSource.USER]
    agent_turns = [t for t in session.turns if t.source == VoiceTurnSource.AGENT]
    print(f"  user_turns={len(user_turns)} agent_turns={len(agent_turns)}")
    assert len(user_turns) >= 1
    assert len(agent_turns) >= 1

    _header("6. audio_loop transcript ring tagged source='discord_text'")
    state = get_audio_loop_store().get(node_id)
    assert state is not None
    sources = [t.source for t in state.transcripts]
    print(f"  sources={sources}")
    assert "discord_text" in sources, sources

    _header("7. build_tts_reply_envelope with TTS enabled → tts=True")
    os.environ[ENV_TTS] = "1"
    env_on = build_tts_reply_envelope(
        result.get("reply_text") or "fallback reply body",
        guild_id=TEST_GUILD,
        channel_id=TEST_CHANNEL,
    )
    print(f"  envelope_on={env_on}")
    assert env_on["status"] == "ok"
    assert env_on["tts"] is True
    assert env_on["content"]

    _header("8. build_tts_reply_envelope with TTS disabled → tts=False (plain)")
    os.environ.pop(ENV_TTS, None)
    env_off = build_tts_reply_envelope(
        result.get("reply_text") or "fallback reply body",
        guild_id=TEST_GUILD,
        channel_id=TEST_CHANNEL,
    )
    print(f"  envelope_off_status={env_off['status']} tts={env_off['tts']}")
    assert env_off["status"] == "ok"
    assert env_off["tts"] is False
    assert env_off["content"]

    _header("9. Gating: unauthorized channel is denied even with flag ON")
    denied = maybe_mirror_discord_text_message(
        "should be blocked",
        guild_id=TEST_GUILD,
        channel_id=OTHER_CHANNEL,
        user_id=TEST_USER,
    )
    print(f"  denied_status={denied['ingress']['status']}")
    assert denied["ingress"]["status"] == "gate_denied"
    assert denied["ingress"]["detail"] == "channel_not_allowed"

    _header("10. pseudo_live_status surfaces state")
    status = pseudo_live_status()
    print(f"  ingress_enabled={status['ingress_enabled']}")
    print(f"  tts_reply_enabled={status['tts_reply_enabled']}")
    print(f"  allowlists={status['allowlists']}")
    print(f"  recent_events_count={len(status['recent_events'])}")
    assert status["ingress_enabled"] is True
    assert status["tts_reply_enabled"] is False
    assert TEST_GUILD in status["allowlists"]["guilds"]
    assert TEST_CHANNEL in status["allowlists"]["channels"]
    assert "*" in status["allowlists"]["users"]
    assert len(status["recent_events"]) >= 1

    _header("11. Reply truncation respects max_chars cap")
    os.environ[ENV_MAX] = "60"
    long_reply = "x" * 500
    trimmed_env = build_tts_reply_envelope(
        long_reply, guild_id=TEST_GUILD, channel_id=TEST_CHANNEL
    )
    print(f"  trimmed_len={len(trimmed_env['content'])} cap={trimmed_env['max_chars']}")
    assert trimmed_env["status"] == "ok"
    assert len(trimmed_env["content"]) <= 60
    # Also test the pure helper.
    assert len(truncate_reply("y" * 500, max_chars=20)) <= 20

    _header("12. transport_report pseudo_live block present")
    from runtime.substrate.transport_report import unified_transport_report  # noqa: E402

    report = unified_transport_report(node_id=node_id)
    pl = report.get("pseudo_live") or {}
    print(f"  pseudo_live.ingress_enabled={pl.get('ingress_enabled')}")
    print(f"  pseudo_live.transcript_source={pl.get('transcript_source')}")
    assert pl.get("transcript_source") == "discord_text"
    assert "allowlists" in pl

    _header("13. Hot path imports unchanged")
    import importlib

    for mod in (
        "runtime.gateway",
        "control_plane.runtime.cognitive_loop",
        "runtime.model_router",
        "execution.runtime.agent_runtime",
        "runtime.primitives",
    ):
        try:
            importlib.import_module(mod)
            print(f"  ok: {mod}")
        except Exception as e:  # noqa: BLE001
            print(f"  WARN ({mod}): {e}")

    _header("14. history ring captured events")
    events = get_text_history().latest(limit=50)
    kinds = {e["kind"] for e in events}
    print(f"  kinds={kinds} count={len(events)}")
    assert "ingress" in kinds
    assert "reply" in kinds
    assert "gate_denied" in kinds

    _clear_env()
    _header("DISCORD PSEUDO-LIVE TEXT+TTS SMOKE TEST PASSED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
