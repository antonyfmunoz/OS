#!/usr/bin/env python3
"""Playback refinement smoke test (Subagent C).

Validates the shared playback status contract:
  - PLAYBACK_REASONS canonical reason dict
  - normalize_playback_result() envelope
  - MeetingTransport.play_reply() normalized envelope parity

The bounded queue (depth=2) was NOT implemented to avoid touching the
Discord after-callback chain in ways that could affect existing smoke
tests. Normalization layer is the must-have and is fully covered.

Standalone. No pytest. Plain asserts. Exit 1 on failure.
"""

from __future__ import annotations

import sys

sys.path.insert(0, os.environ.get("UMH_ROOT") or os.environ.get("OS_ROOT") or os.environ.get("EOS_ROOT") or "/opt/OS")

from runtime.substrate.discord_voice_playback import (  # noqa: E402
    PLAYBACK_REASONS,
    PlaybackResult,
    normalize_playback_result,
)
from runtime.substrate.meeting_transport import MeetingTransport  # noqa: E402


def _header(msg: str) -> None:
    print(f"\n── {msg} " + "─" * max(0, 60 - len(msg)))


CANONICAL_KEYS = {
    "transport",
    "status",
    "reason",
    "detail",
    "text_preview",
    "queued_depth",
    "occurred_at",
}


def test_normalize_from_dict_ok() -> None:
    env = normalize_playback_result(
        {"status": "ok", "detail": "played"}, transport="discord"
    )
    assert CANONICAL_KEYS.issubset(env.keys()), env
    assert env["transport"] == "discord"
    assert env["status"] == "ok"
    assert env["detail"] == "played"
    assert env["reason"] == PLAYBACK_REASONS["ok"]
    assert env["occurred_at"]


def test_normalize_from_playback_result() -> None:
    pr = PlaybackResult(
        status="busy_skipped",
        detail="x",
        text_preview="hi",
        node_id="x",
        queued_depth=0,
        reason="another_utterance_playing",
    )
    env = normalize_playback_result(pr, transport="discord")
    assert env["status"] == "busy_skipped"
    assert env["transport"] == "discord"
    assert env["queued_depth"] == 0
    assert env["text_preview"] == "hi"


def test_normalize_from_string() -> None:
    env = normalize_playback_result("anything weird", transport="discord")
    assert env["status"] == "playback_error"
    assert "anything weird" in env["detail"]


def test_normalize_from_none() -> None:
    env = normalize_playback_result(None, transport="discord")
    assert env["status"] == "playback_error"
    assert "no result" in env["detail"].lower()


def test_normalize_unknown_status_falls_through() -> None:
    env = normalize_playback_result({"status": "floofy"}, transport="discord")
    assert env["status"] == "playback_error"
    assert "floofy" in env["detail"]


def test_playback_reasons_dict_complete() -> None:
    required = {
        "ok",
        "queued",
        "busy_skipped",
        "tts_unavailable",
        "vc_unavailable",
        "ffmpeg_missing",
        "playback_error",
        "empty_text",
        "disabled",
        "sink_error",
    }
    assert required.issubset(set(PLAYBACK_REASONS.keys()))
    for k, v in PLAYBACK_REASONS.items():
        assert isinstance(v, str) and v, f"{k} has empty description"


class _FakeSinkOk:
    def play_text(self, text: str) -> dict:
        return {"detail": "meeting tts ok"}


class _FakeSinkRaises:
    def play_text(self, text: str) -> dict:
        raise RuntimeError("boom")


def _mk_transport() -> MeetingTransport:
    return MeetingTransport(
        platform="google_meet",
        meeting_id="playback-refine-smoke",
        role_slug="ea_orchestrator",
        ensure_node=False,
    )


def test_meeting_play_reply_normalized_when_sink_attached() -> None:
    t = _mk_transport()
    t.attach_playback_sink(_FakeSinkOk(), enabled=True)
    out = t.play_reply("hello")
    assert out["status"] == "ok", out
    assert out.get("transport") == "meeting", out
    assert out.get("occurred_at"), out
    assert out.get("text_preview") == "hello", out


def test_meeting_play_reply_disabled_when_no_sink() -> None:
    t = _mk_transport()
    out = t.play_reply("hi")
    assert out["status"] == "disabled", out
    assert out.get("transport") == "meeting", out
    assert out.get("occurred_at"), out


def test_meeting_play_reply_sink_raises_returns_error_envelope() -> None:
    t = _mk_transport()
    t.attach_playback_sink(_FakeSinkRaises(), enabled=True)
    out = t.play_reply("hi")
    assert out["status"] in ("playback_error", "sink_error"), out
    assert "boom" in out.get("detail", ""), out
    assert out.get("transport") == "meeting", out


# NOTE: queue depth=2 tests intentionally omitted — the bounded queue
# was NOT implemented in this pass. See module docstring.


TESTS = [
    test_normalize_from_dict_ok,
    test_normalize_from_playback_result,
    test_normalize_from_string,
    test_normalize_from_none,
    test_normalize_unknown_status_falls_through,
    test_playback_reasons_dict_complete,
    test_meeting_play_reply_normalized_when_sink_attached,
    test_meeting_play_reply_disabled_when_no_sink,
    test_meeting_play_reply_sink_raises_returns_error_envelope,
]


def run_all() -> int:
    failed = 0
    for fn in TESTS:
        name = fn.__name__
        try:
            fn()
            print(f"  ok  {name}")
        except AssertionError as e:
            failed += 1
            print(f"  FAIL {name}: {e}")
        except Exception as e:  # noqa: BLE001
            failed += 1
            print(f"  ERROR {name}: {type(e).__name__}: {e}")
    _header(
        "PLAYBACK REFINEMENT SMOKE TEST "
        + ("PASSED" if failed == 0 else f"FAILED ({failed})")
    )
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    raise SystemExit(run_all())
