#!/usr/bin/env python3
"""
Google Meet source adapter smoke test.

Proves the GoogleMeetSource adapter:
  - parses meet URLs / codes
  - reports honest mode (transcript_only / attached_degraded / attached_live)
  - attaches to MeetingTransport via the existing seam
  - feeds utterances through pump_attached_sources -> shared inject seam
  - propagates google_meet_code metadata
  - degrades safely when no hook is wired
  - swallows hook exceptions (never raises)
  - leaves the hot path imports clean

Does NOT require a real meeting, browser, or Playwright session. The
"live" hook is a deterministic in-process callable.
"""

from __future__ import annotations

import os
import sys

sys.path.insert(0, os.environ.get("UMH_ROOT") or os.environ.get("OS_ROOT") or os.environ.get("EOS_ROOT") or "/opt/OS")

from dotenv import load_dotenv  # noqa: E402

load_dotenv(os.path.join(os.environ.get('UMH_ROOT') or os.environ.get('OS_ROOT') or os.environ.get('EOS_ROOT') or '/opt/OS', 'runtime', '.env'))

from runtime.substrate.audio_loop import (  # noqa: E402
    get_audio_loop_store,
    reset_audio_loop_store_for_tests,
)
from runtime.substrate.google_meet_source import (  # noqa: E402
    LIVE_ENV_VAR,
    PROVIDER,
    GoogleMeetSource,
    is_google_meet_source,
    parse_meet_url,
)
from runtime.substrate.meeting_sources import is_meeting_source  # noqa: E402
from runtime.substrate.meeting_transport import (  # noqa: E402
    MeetingTransport,
    reset_default_meeting_transports_for_tests,
    reset_meeting_transport_history_for_tests,
)
from runtime.substrate.station_bus import get_station_bus  # noqa: E402
from runtime.substrate.station_daemon import StationDaemon  # noqa: E402
from runtime.substrate.voice_session import (  # noqa: E402
    VoiceTurnSource,
    get_voice_session_store,
    reset_voice_session_store_for_tests,
)

PLATFORM = "google_meet"
MEETING_CODE = "abc-defg-hij"
MEETING_URL = f"https://meet.google.com/{MEETING_CODE}?authuser=0"


def _header(msg: str) -> None:
    print(f"\n── {msg} " + "─" * max(0, 60 - len(msg)))


def _fail(msg: str) -> None:
    print(f"FAIL: {msg}")
    sys.exit(1)


def main() -> int:
    _header("0. Reset stores + env")
    reset_voice_session_store_for_tests()
    reset_audio_loop_store_for_tests()
    reset_meeting_transport_history_for_tests()
    reset_default_meeting_transports_for_tests()
    get_voice_session_store().clear()
    os.environ.pop(LIVE_ENV_VAR, None)

    _header("1. parse_meet_url")
    cases = {
        "https://meet.google.com/abc-defg-hij": "abc-defg-hij",
        "meet.google.com/abc-defg-hij?authuser=0": "abc-defg-hij",
        "abc-defg-hij": "abc-defg-hij",
        "ABC-DEFG-HIJ": "abc-defg-hij",
        "https://example.com/nothing": None,
        None: None,
        "": None,
    }
    for raw, expected in cases.items():
        got = parse_meet_url(raw)
        print(f"  {raw!r:55} -> {got!r}")
        if got != expected:
            _fail(f"parse_meet_url({raw!r}) expected {expected!r} got {got!r}")

    _header("2. Construct GoogleMeetSource (no hook)")
    src_off = GoogleMeetSource(name="meet_off", meeting_url=MEETING_URL)
    print(
        f"  provider={src_off.provider} code={src_off.meeting_code} mode={src_off.mode}"
    )
    if src_off.provider != PROVIDER:
        _fail(f"provider should be {PROVIDER}")
    if src_off.meeting_code != MEETING_CODE:
        _fail(f"meeting_code should be {MEETING_CODE}, got {src_off.meeting_code}")
    if src_off.mode != "transcript_only":
        _fail(f"mode without hook should be transcript_only, got {src_off.mode}")
    if not is_meeting_source(src_off):
        _fail("GoogleMeetSource fails MeetingSourceProtocol duck-check")
    if not is_google_meet_source(src_off):
        _fail("is_google_meet_source returned False for GoogleMeetSource")
    if src_off.read_utterance() is not None:
        _fail("read_utterance with no hook must return None")
    if src_off.last_read_status != "empty":
        _fail(f"last_read_status should be empty, got {src_off.last_read_status}")

    _header("3. Mode transitions: degraded vs live")
    queue: list[dict] = []

    def hook() -> dict | None:
        return queue.pop(0) if queue else None

    src = GoogleMeetSource(name="meet_live", meeting_code=MEETING_CODE, hook=hook)
    if src.mode != "attached_degraded":
        _fail(f"with hook + no env, mode should be attached_degraded, got {src.mode}")
    os.environ[LIVE_ENV_VAR] = "1"
    if src.mode != "attached_live":
        _fail(f"with hook + env, mode should be attached_live, got {src.mode}")
    os.environ.pop(LIVE_ENV_VAR, None)
    if src.mode != "attached_degraded":
        _fail("mode should drop back to attached_degraded after env unset")

    _header("4. Build MeetingTransport + attach")
    transport = MeetingTransport(platform=PLATFORM, meeting_id=MEETING_CODE)
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

    res = transport.attach_source(src)
    print(f"  attach={res}")
    if res.get("status") != "attached":
        _fail(f"attach failed: {res}")
    if res.get("provider") != PROVIDER:
        _fail(f"attach should record provider={PROVIDER}, got {res.get('provider')}")

    _header("5. Pump with one queued utterance")
    queue.append(
        {
            "text": "what is our top blocker right now",
            "user_id": "u1",
            "participant_name": "Antony",
            "metadata": {"caption_idx": 7},
        }
    )
    pumped = transport.pump_attached_sources(max_per_source=1)
    print(f"  pumped={pumped}")
    if pumped.get("pumped", 0) != 1:
        _fail(f"expected pumped=1, got {pumped}")
    if src.utterance_count != 1:
        _fail(f"adapter utterance_count should be 1, got {src.utterance_count}")
    if src.last_read_status != "ok":
        _fail(f"last_read_status should be ok, got {src.last_read_status}")

    _header("6. Audio loop + voice session received it")
    state = get_audio_loop_store().get(transport.node_id)
    if state is None:
        _fail("no audio_loop state")
    sources = [t.source for t in state.transcripts]
    if "meeting_voice" not in sources:
        _fail(f"expected meeting_voice in {sources}")

    sessions = get_voice_session_store().latest(limit=5, node_id=transport.node_id)
    if not sessions:
        _fail("no voice sessions")
    sess = sessions[0]
    user_turns = [t for t in sess.turns if t.source == VoiceTurnSource.USER]
    agent_turns = [t for t in sess.turns if t.source == VoiceTurnSource.AGENT]
    print(f"  user_turns={len(user_turns)} agent_turns={len(agent_turns)}")
    if not user_turns:
        _fail("no USER turns")
    if not any(t.action_id for t in agent_turns):
        _fail("no AGENT turn with action_id")

    _header("7. google_meet_code metadata propagated")
    found_code = False
    for t in user_turns:
        meta = getattr(t, "metadata", None) or {}
        if isinstance(meta, dict) and meta.get("google_meet_code") == MEETING_CODE:
            found_code = True
            break
    if not found_code:
        for tr in state.transcripts:
            tmeta = getattr(tr, "metadata", None) or {}
            if (
                isinstance(tmeta, dict)
                and tmeta.get("google_meet_code") == MEETING_CODE
            ):
                found_code = True
                break
    print(f"  found_meet_code_meta={found_code}")
    if not found_code:
        _fail("google_meet_code metadata did not propagate")

    _header("8. Hook raising is swallowed safely")

    def boom() -> dict | None:
        raise RuntimeError("captioner crashed")

    src.attach_hook(boom)
    out = src.read_utterance()
    print(f"  read_after_boom={out} last_error={src.last_error}")
    if out is not None:
        _fail("hook exception must yield None")
    if src.last_error != "captioner crashed":
        _fail(f"last_error not recorded: {src.last_error}")
    if src.last_read_status != "error":
        _fail(f"last_read_status should be error, got {src.last_read_status}")

    _header("9. status_snapshot is JSON-friendly + has recent_events")
    snap = src.status_snapshot()
    import json

    payload = json.dumps(snap, default=str)
    print(f"  snapshot_keys={sorted(snap.keys())}")
    if "recent_events" not in snap or not isinstance(snap["recent_events"], list):
        _fail("snapshot missing recent_events list")
    if not snap["recent_events"]:
        _fail("recent_events should be non-empty")
    if len(payload) < 50:
        _fail("snapshot payload suspiciously small")

    _header("10. detach + transcript_only fallback remains valid")
    det = transport.detach_source(src.name)
    print(f"  detach={det}")
    if det.get("status") != "detached":
        _fail(f"detach failed: {det}")
    after = transport.status_report()
    if after["mode"] != "transcript_only":
        _fail(
            f"transport mode should fall back to transcript_only, got {after['mode']}"
        )

    # Manual transcript_only path still works post-detach.
    inj = transport.inject_utterance(
        "manual fallback line",
        participant_name="Antony",
        meeting_id=MEETING_CODE,
    )
    if inj.get("status") != "ok":
        _fail(f"transcript_only inject failed: {inj}")

    _header("11. Closed source is inert")
    src.close()
    if src.read_utterance() is not None:
        _fail("closed source must return None")

    _header("12. Hot path imports unchanged")
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

    print("\nOK substrate_google_meet_smoke_test")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
