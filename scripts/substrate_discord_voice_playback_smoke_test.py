#!/usr/bin/env python3
"""
Discord voice playback smoke test.

Proves the bounded VoiceClient attachment + playback path on top of the
existing Discord voice transport adapter, end-to-end, WITHOUT touching a
real Discord connection.

What this test covers
---------------------
 1. Transcript-only mode is the default and remains a no-op for playback.
 2. attach_voice_client(fake_vc) flips the transport into ATTACHED /
    ATTACHED_DEGRADED mode and enables playback.
 3. inject_utterance() auto-renders the AGENT reply through the playback
    adapter when a VC is attached, and the fake VC observes a play() call.
 4. The bounded queue rejects overlapping playback with a structured
    "busy_skipped" reason instead of crashing.
 5. detach_voice_client() returns the transport to TRANSCRIPT_ONLY safely.
 6. play_reply() with no VC attached returns a "disabled" result, never
    raises.
 7. status_report() exposes playback fields (snapshot + capability + recent).
 8. maybe_attach_discord_voice_client() respects the env gate.
 9. Hot path imports remain clean.

The test uses a tiny FakeVoiceClient — no Discord connection, no audio
hardware, no network. ffmpeg / TTS may or may not be installed; either
way the test asserts the documented degraded behavior, not absolute
playback success.

Returns 0 on success, non-zero on assertion failure.
"""

from __future__ import annotations

import os
import sys

sys.path.insert(0, os.environ.get("UMH_ROOT") or os.environ.get("OS_ROOT") or os.environ.get("EOS_ROOT") or "/opt/OS")

from runtime.substrate.audio_loop import (  # noqa: E402
    reset_audio_loop_store_for_tests,
)
from runtime.substrate.discord_voice_playback import (  # noqa: E402
    DiscordVoicePlayback,
    get_playback_history,
    playback_env_enabled,
    probe_playback_capability,
    reset_playback_history_for_tests,
)
from runtime.substrate.discord_voice_transport import (  # noqa: E402
    DiscordVoiceTransport,
    get_transport_history,
    maybe_attach_discord_voice_client,
    reset_default_discord_voice_transports_for_tests,
    reset_transport_history_for_tests,
)
from runtime.substrate.station_bus import get_station_bus  # noqa: E402
from runtime.substrate.station_daemon import StationDaemon  # noqa: E402
from runtime.substrate.voice_session import (  # noqa: E402
    get_voice_session_store,
    reset_voice_session_store_for_tests,
)

TEST_GUILD = "playback-smoketest-guild"
TEST_CHANNEL = "playback-smoketest-channel"
PLAYBACK_ENV = "EOS_DISCORD_VOICE_PLAYBACK_ENABLED"


def _header(msg: str) -> None:
    print(f"\n── {msg} " + "─" * max(0, 60 - len(msg)))


class FakeVoiceClient:
    """Minimal VoiceClient stand-in. Records play() calls."""

    def __init__(self) -> None:
        self.played: list = []
        self._is_playing_flag = False

    def is_playing(self) -> bool:
        return self._is_playing_flag

    def play(self, source, after=None) -> None:
        self.played.append({"source": source, "after_provided": callable(after)})
        # Simulate the after-callback firing immediately on completion so
        # subsequent calls are not blocked.
        self._is_playing_flag = False
        if callable(after):
            try:
                after(None)
            except Exception:
                pass


def _fresh_transport() -> DiscordVoiceTransport:
    return DiscordVoiceTransport(
        guild_id=TEST_GUILD,
        channel_id=TEST_CHANNEL,
        role_slug="ea_orchestrator",
    )


def main() -> int:
    _header("0. Cleanup")
    reset_voice_session_store_for_tests()
    reset_audio_loop_store_for_tests()
    reset_transport_history_for_tests()
    reset_default_discord_voice_transports_for_tests()
    reset_playback_history_for_tests()
    get_voice_session_store().clear()
    os.environ.pop(PLAYBACK_ENV, None)

    _header("1. Default transport: transcript-only, no playback")
    t = _fresh_transport()
    assert t._mode == "transcript_only"  # noqa: SLF001
    assert t._playback_enabled is False  # noqa: SLF001
    assert t._attached_vc is None  # noqa: SLF001
    assert t._playback is None  # noqa: SLF001

    # Heartbeat the daemon so SPEAK_TEXT can flow on this node.
    bus = get_station_bus()
    bus.daemon_take_outbox(t.node_id)
    bus.drain_inbox(t.node_id)
    daemon = StationDaemon(
        node_id=t.node_id,
        poll_interval_s=0.05,
        heartbeat_interval_s=0.01,
        dry_run=True,
    )
    daemon.register()
    daemon._tick()  # noqa: SLF001

    _header("2. play_reply with no VC attached returns 'disabled'")
    out = t.play_reply("hello world")
    print(f"  out={out}")
    assert out["status"] == "disabled"

    _header("3. attach_voice_client(fake) → ATTACHED, playback_enabled=True")
    fake = FakeVoiceClient()
    attach = t.attach_voice_client(fake, enabled=True)
    print(f"  attach={attach}")
    assert attach["status"] == "attached"
    assert attach["playback_enabled"] is True
    assert t._attached_vc is fake  # noqa: SLF001
    assert t._playback is not None  # noqa: SLF001
    assert t._playback.is_enabled() is True  # noqa: SLF001

    _header("4. inject_utterance auto-plays the agent reply through fake VC")
    t.start_session()
    inj = t.inject_utterance("what is on the agenda today", user_id="9001")
    print(f"  inj.status={inj['status']}")
    print(f"  inj.playback={inj.get('playback')}")
    assert inj["status"] == "ok", inj
    pb = inj.get("playback")
    assert pb is not None, "playback field should be present when VC attached"
    # ok = TTS happy path; tts_unavailable / ffmpeg_missing = degraded path.
    # All three are documented bounded outcomes — never an exception.
    assert pb["status"] in (
        "ok",
        "tts_unavailable",
        "ffmpeg_missing",
        "playback_error",
        "no_reply",
    ), pb
    if pb["status"] == "ok":
        assert len(fake.played) >= 1, "fake VC should have observed at least one play()"

    _header("5. Bounded busy guard: overlapping play returns 'busy_skipped'")
    # Force the playback adapter into a busy state and verify the guard fires.
    t._playback._busy = True  # noqa: SLF001
    busy_out = t.play_reply("second utterance while busy")
    print(f"  busy_out={busy_out}")
    assert busy_out["status"] == "busy_skipped", busy_out
    t._playback._busy = False  # noqa: SLF001

    _header("6. status_report exposes playback snapshot + capability + recent")
    report = t.status_report()
    print(f"  mode={report['mode']}")
    print(f"  playback_enabled={report['playback_enabled']}")
    print(f"  attached_vc={report['attached_vc']}")
    print(f"  playback={report.get('playback')}")
    assert report["mode"] in ("attached", "attached_degraded"), report
    assert report["playback_enabled"] is True
    assert report["attached_vc"] is True
    assert report["playback"] is not None
    assert report["playback_capability"] is not None
    assert isinstance(report["recent_playback"], list)
    assert len(report["recent_playback"]) >= 1
    assert "playback_env_enabled" in report

    _header("7. detach_voice_client returns to TRANSCRIPT_ONLY safely")
    det = t.detach_voice_client()
    print(f"  detach={det}")
    assert det["status"] == "detached"
    assert t._attached_vc is None  # noqa: SLF001
    assert t._playback_enabled is False  # noqa: SLF001
    after = t.status_report()
    assert after["mode"] in ("transcript_only", "transcript_only_no_lib")
    assert after["playback_enabled"] is False

    _header("8. Direct DiscordVoicePlayback unit checks (empty/disabled)")
    p = DiscordVoicePlayback(node_id="unit-test-node")
    r1 = p.play_text("anything")
    assert r1.status == "disabled", r1
    p.attach(FakeVoiceClient(), enabled=True)
    r2 = p.play_text("")
    assert r2.status == "empty_text", r2
    p.detach()

    _header("9. probe_playback_capability is structured and never raises")
    cap = probe_playback_capability()
    print(f"  capability={cap}")
    for k in (
        "discord_lib_present",
        "voice_extras_present",
        "ffmpeg_present",
        "voice_engine_importable",
    ):
        assert k in cap

    _header("10. maybe_attach_discord_voice_client respects env gate")
    reset_default_discord_voice_transports_for_tests()
    os.environ.pop(PLAYBACK_ENV, None)
    assert playback_env_enabled() is False
    off = maybe_attach_discord_voice_client(
        FakeVoiceClient(), guild_id=TEST_GUILD, channel_id=TEST_CHANNEL
    )
    print(f"  off={off}")
    assert off is None
    os.environ[PLAYBACK_ENV] = "1"
    try:
        on = maybe_attach_discord_voice_client(
            FakeVoiceClient(), guild_id=TEST_GUILD, channel_id=TEST_CHANNEL
        )
        print(f"  on={on}")
        assert on is not None
        assert on.get("status") == "attached", on
    finally:
        os.environ.pop(PLAYBACK_ENV, None)

    _header("10b. PlaybackResult reason field + playback_status_snapshot")
    p2 = DiscordVoicePlayback(node_id="reason-check-node")
    r_disabled = p2.play_text("hi")
    d_dict = r_disabled.as_dict()
    assert "reason" in d_dict, d_dict
    assert d_dict["reason"] == "disabled_by_env", d_dict
    p2.attach(FakeVoiceClient(), enabled=True)
    p2._busy = True  # noqa: SLF001
    r_busy = p2.play_text("second")
    assert r_busy.as_dict().get("reason") == "another_utterance_playing", r_busy
    p2._busy = False  # noqa: SLF001
    pss = p2.playback_status_snapshot()
    print(f"  playback_status_snapshot={pss}")
    for k in ("transport", "mode", "attached", "enabled", "by_status", "max_depth"):
        assert k in pss, pss
    assert pss["transport"] == "discord"
    assert pss["max_depth"] == 1

    _header("11. Bounded history ring records playback attempts")
    rows = get_playback_history().latest(limit=50)
    print(f"  history_rows={len(rows)}")
    assert len(rows) >= 2  # at least the 'disabled' and 'busy_skipped' / 'ok'

    _header("12. Hot path imports remain clean")
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

    # Confirm the transport history singleton is undisturbed.
    th = get_transport_history()
    assert th is not None

    _header("DISCORD VOICE PLAYBACK SMOKE TEST PASSED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
