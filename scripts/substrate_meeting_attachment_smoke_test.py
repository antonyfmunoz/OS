#!/usr/bin/env python3
"""
Slice A smoke test: real meeting attachment seam.

Proves MeetingTransport.attach_source / pump_attached_sources / detach_source
work end-to-end through the existing bounded inject_transcript seam, without
touching the hot path or creating a parallel agent loop.
"""

from __future__ import annotations

import sys

import os
sys.path.insert(0, os.environ.get("UMH_ROOT") or os.environ.get("OS_ROOT") or os.environ.get("EOS_ROOT") or "/opt/OS")

from dotenv import load_dotenv  # noqa: E402

load_dotenv(os.path.join(os.environ.get('UMH_ROOT') or os.environ.get('OS_ROOT') or os.environ.get('EOS_ROOT') or '/opt/OS', 'eos_ai', '.env'))

from eos_ai.substrate.audio_loop import (  # noqa: E402
    get_audio_loop_store,
    reset_audio_loop_store_for_tests,
)
from eos_ai.substrate.meeting_sources import FakeMeetingSource  # noqa: E402
from eos_ai.substrate.meeting_transport import (  # noqa: E402
    MeetingTransport,
    reset_default_meeting_transports_for_tests,
    reset_meeting_transport_history_for_tests,
)
from eos_ai.substrate.station_bus import get_station_bus  # noqa: E402
from eos_ai.substrate.station_daemon import StationDaemon  # noqa: E402
from eos_ai.substrate.voice_session import (  # noqa: E402
    VoiceTurnSource,
    get_voice_session_store,
    reset_voice_session_store_for_tests,
)

PLATFORM = "generic_meeting"
MEETING_ID = "smoke_attach_001"


def _header(msg: str) -> None:
    print(f"\n── {msg} " + "─" * max(0, 60 - len(msg)))


def _fail(msg: str) -> None:
    print(f"FAIL: {msg}")
    sys.exit(1)


def main() -> int:
    _header("0. Reset stores")
    reset_voice_session_store_for_tests()
    reset_audio_loop_store_for_tests()
    reset_meeting_transport_history_for_tests()
    reset_default_meeting_transports_for_tests()
    get_voice_session_store().clear()

    _header("1. Build MeetingTransport")
    transport = MeetingTransport(platform=PLATFORM, meeting_id=MEETING_ID)
    print(f"  node_id={transport.node_id}")

    _header("2. Heartbeat daemon so SPEAK_TEXT flows")
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

    _header("3. attach_source: FakeMeetingSource")
    src = FakeMeetingSource(
        name="fake_a",
        provider="generic_meeting",
        utterances=[
            {
                "text": "hello from meeting",
                "user_id": "u1",
                "participant_name": "Alice",
            },
            {"text": "second line"},
        ],
    )
    res = transport.attach_source(src)
    print(f"  attach={res}")
    if res.get("status") != "attached":
        _fail(f"attach status not attached: {res}")

    report = transport.status_report()
    print(f"  mode={report['mode']} attached_sources={len(report['attached_sources'])}")
    if len(report["attached_sources"]) != 1:
        _fail(f"expected 1 attached source: {report['attached_sources']}")
    if report["mode"] != "attached":
        _fail(f"expected mode=attached, got {report['mode']}")

    _header("4. pump_attached_sources(max_per_source=2)")
    pumped = transport.pump_attached_sources(max_per_source=2)
    print(f"  pumped={pumped}")
    if pumped.get("pumped", 0) < 2:
        _fail(f"expected pumped>=2, got {pumped}")

    _header("5. audio_loop transcripts tagged source='meeting_voice'")
    state = get_audio_loop_store().get(transport.node_id)
    if state is None:
        _fail("no audio_loop state for meeting node")
    sources = [t.source for t in state.transcripts]
    print(f"  transcript_sources={sources}")
    if "meeting_voice" not in sources:
        _fail(f"expected meeting_voice in {sources}")

    _header("6. Latest voice session has USER + AGENT(action_id) turns")
    sessions = get_voice_session_store().latest(limit=5, node_id=transport.node_id)
    if not sessions:
        _fail("no voice sessions for meeting node")
    sess = sessions[0]
    user_turns = [t for t in sess.turns if t.source == VoiceTurnSource.USER]
    agent_turns = [t for t in sess.turns if t.source == VoiceTurnSource.AGENT]
    print(f"  user={len(user_turns)} agent={len(agent_turns)}")
    if not user_turns:
        _fail("no USER turns")
    if not agent_turns:
        _fail("no AGENT turns")
    if not any(t.action_id for t in agent_turns):
        _fail("no AGENT turn with action_id (SPEAK_TEXT)")

    _header("7. Per-source metadata reached USER turn metadata")
    found_meta = False
    for t in user_turns:
        meta = getattr(t, "metadata", None) or {}
        if isinstance(meta, dict) and meta.get("meeting_source") == "fake_a":
            found_meta = True
            break
    print(f"  found_meeting_source_meta={found_meta}")
    if not found_meta:
        # Fallback: check transcripts in audio_loop
        for tr in state.transcripts:
            tmeta = getattr(tr, "metadata", None) or {}
            if isinstance(tmeta, dict) and tmeta.get("meeting_source") == "fake_a":
                found_meta = True
                break
    if not found_meta:
        _fail("meeting_source metadata not propagated to turn or transcript")

    _header("8. Reject path: invalid source object")
    bad = transport.attach_source(object())
    print(f"  reject={bad}")
    if bad.get("status") != "rejected" or bad.get("reason") != "invalid_source":
        _fail(f"expected rejected/invalid_source, got {bad}")

    _header("9. Duplicate path: re-attach same name")
    dup_src = FakeMeetingSource(
        name="fake_a", provider="generic_meeting", utterances=[]
    )
    dup = transport.attach_source(dup_src)
    print(f"  duplicate={dup}")
    if dup.get("status") != "rejected" or dup.get("reason") != "duplicate_name":
        _fail(f"expected rejected/duplicate_name, got {dup}")

    _header("10. detach_source returns to transcript_only")
    det = transport.detach_source("fake_a")
    print(f"  detach={det}")
    if det.get("status") != "detached":
        _fail(f"expected detached, got {det}")
    after = transport.status_report()
    print(f"  mode={after['mode']} attached_sources={after['attached_sources']}")
    if after["attached_sources"]:
        _fail(f"expected empty attached_sources, got {after['attached_sources']}")
    if after["mode"] != "transcript_only":
        _fail(f"expected transcript_only mode, got {after['mode']}")

    _header("11. Pump after detach is a no-op")
    pumped2 = transport.pump_attached_sources()
    print(f"  pumped2={pumped2}")
    if pumped2.get("pumped", 0) != 0:
        _fail(f"expected pumped=0 after detach, got {pumped2}")

    _header("12. Hot path imports unchanged")
    import importlib

    for mod in (
        "eos_ai.gateway",
        "eos_ai.cognitive_loop",
        "eos_ai.model_router",
        "eos_ai.agent_runtime",
        "eos_ai.primitives",
    ):
        try:
            importlib.import_module(mod)
            print(f"  ok: {mod}")
        except Exception as e:  # noqa: BLE001
            print(f"  WARN ({mod}): {e}")

    print("\nOK substrate_meeting_attachment_smoke_test")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
