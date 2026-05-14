#!/usr/bin/env python3
"""
Discord Claude Primary Backend + TTS Sanitization — smoke test.

Replaces the former "hard-switch" test. The Discord-only bypass has been
removed: Discord text messages now flow through the shared broader router
(runtime.model_router.call_with_fallback), where Claude CLI tmux is
registered as backend #0. This test proves the NEW invariants:

  1. Discord pseudo-live calls the shared ingest_text_message path — there
     is no Discord-only second cognition pipeline.
  2. TTS sanitization still strips provider/model footer, token/cost lines,
     skill blocks, separator bars, and signature tails.
  3. The clean conversational body is preserved.
  4. Malformed / empty footer input does not crash the sanitizer.
  5. build_tts_reply_envelope still produces the split display/spoken shape.
  6. Hot-path imports remain clean.

No live Discord, tmux, or Claude CLI required.
"""

from __future__ import annotations

import os
import sys

sys.path.insert(0, os.environ.get("UMH_ROOT") or os.environ.get("OS_ROOT") or os.environ.get("EOS_ROOT") or "/opt/OS")

from runtime.transport import discord_text_transport as dtt  # noqa: E402
from runtime.transport.discord_text_transport import (  # noqa: E402
    build_tts_reply_envelope,
    maybe_mirror_discord_text_message,
    pseudo_live_status,
    reset_backend_state_for_tests,
    reset_text_history_for_tests,
)
from runtime.transport.tts_sanitize import sanitize_tts_reply  # noqa: E402

TEST_GUILD = "hs-guild"
TEST_CHANNEL = "hs-channel"
TEST_USER = "7777"

ENV_INGRESS = "EOS_DISCORD_TEXT_TRANSPORT_ENABLED"
ENV_TTS = "EOS_DISCORD_TEXT_REPLY_TTS_ENABLED"
ENV_GUILDS = "EOS_DISCORD_TEXT_ALLOWED_GUILDS"
ENV_CHANNELS = "EOS_DISCORD_TEXT_ALLOWED_CHANNELS"
ENV_USERS = "EOS_DISCORD_TEXT_ALLOWED_USERS"
ENV_CLAUDE = "EOS_DISCORD_CLAUDE_RESPONDER_ENABLED"  # legacy, now observational
_ALL_ENV = [ENV_INGRESS, ENV_TTS, ENV_GUILDS, ENV_CHANNELS, ENV_USERS, ENV_CLAUDE]


def _header(msg: str) -> None:
    print(f"\n── {msg} " + "─" * max(0, 60 - len(msg)))


def _clear_env() -> None:
    for k in _ALL_ENV:
        os.environ.pop(k, None)


def _enable_and_allow() -> None:
    os.environ[ENV_INGRESS] = "1"
    os.environ[ENV_TTS] = "1"
    os.environ[ENV_GUILDS] = TEST_GUILD
    os.environ[ENV_CHANNELS] = TEST_CHANNEL
    os.environ[ENV_USERS] = "*"


FOOTER_REPLY = """\
Here is the answer you asked for. It spans a couple of lines and should
survive sanitization cleanly.

★ Insight ─────────────────────────────────────
- routing choice matters
- model_router fallback chain is Gemini → Ollama
─────────────────────────────────────────────────

Provider: gemini-2.5-flash
Tokens: 1,240    Cost: $0.003
[Skill: using-superpowers]
— DEX
"""

CLEAN_BODY_EXPECTED_SUBSTR = "Here is the answer you asked for."


# ─── Fake shared-router ingress (stand-in for ingest_text_message) ───────────


class _FakeIngestOK:
    called = 0

    def __call__(self, text, **kw):
        type(self).called += 1
        return {
            "status": "ok",
            "session_id": "fake-session-1",
            "role_slug": kw.get("role_slug"),
            "detail": "router_served",
            "audio_loop": None,
            "reply_text": FOOTER_REPLY,
        }


def main() -> int:
    _header("0. Cleanup")
    _clear_env()
    reset_text_history_for_tests()
    reset_backend_state_for_tests()
    original_ingest = dtt.ingest_text_message

    _header("1. sanitize_tts_reply strips footer + preserves body")
    spoken = sanitize_tts_reply(FOOTER_REPLY)
    print(f"  spoken_repr={spoken!r}")
    assert CLEAN_BODY_EXPECTED_SUBSTR in spoken
    for forbidden in (
        "★ Insight",
        "Provider:",
        "Tokens:",
        "Cost:",
        "[Skill:",
        "— DEX",
        "─────────────",
        "gemini-2.5-flash",
    ):
        assert forbidden not in spoken, f"sanitizer left footer marker: {forbidden}"

    _header("2. sanitize_tts_reply safe on malformed / empty input")
    assert sanitize_tts_reply(None) == ""
    assert sanitize_tts_reply("") == ""
    assert sanitize_tts_reply("   \n\n  ") == ""
    assert sanitize_tts_reply(12345) != ""  # coerces
    footer_only = "Provider: gemini\nTokens: 42\n───────"
    assert sanitize_tts_reply(footer_only) == ""
    once = sanitize_tts_reply(FOOTER_REPLY)
    twice = sanitize_tts_reply(once)
    assert once == twice

    _header("3. Discord path goes through shared ingest_text_message (no bypass)")
    _enable_and_allow()
    reset_backend_state_for_tests()
    fake_ingest = _FakeIngestOK()
    dtt.ingest_text_message = fake_ingest  # type: ignore[assignment]
    result = maybe_mirror_discord_text_message(
        "what's on the agenda",
        guild_id=TEST_GUILD,
        channel_id=TEST_CHANNEL,
        user_id=TEST_USER,
    )
    assert result is not None
    ingress = result["ingress"]
    env = result["envelope"]
    print(f"  ingest_called={_FakeIngestOK.called}")
    print(f"  env.status={env['status']} tts={env['tts']}")
    print(f"  env.sanitized={env['sanitized']}")
    assert _FakeIngestOK.called == 1, (
        "Discord did not reach the shared ingest_text_message — the Discord-"
        "only bypass is still present."
    )
    assert ingress["status"] == "ok"
    assert env["status"] == "ok"
    assert env["sanitized"] is True
    for forbidden in ("Provider:", "Tokens:", "★ Insight", "gemini-2.5-flash"):
        assert forbidden not in env["spoken_text"], forbidden
        assert forbidden not in env["tts_content"], forbidden
    plan = env["emit_plan"]
    assert len(plan) == 2
    assert plan[0]["role"] == "visible" and plan[0]["tts"] is False
    assert plan[1]["role"] == "spoken" and plan[1]["tts"] is True
    # Visible layer still carries the footer — that's intended (operator sees it).
    assert "Provider:" in plan[0]["content"]

    _header("4. pseudo_live_status reports shared_router backend")
    status = pseudo_live_status()
    print(f"  responder_backend={status['responder_backend']}")
    assert status["responder_backend"] == "shared_router"
    assert status["provider_fallback_used"] is False
    assert status["last_tts_sanitized"] is True

    _header("5. build_tts_reply_envelope directly: spoken/display split")
    env_direct = build_tts_reply_envelope(
        FOOTER_REPLY,
        guild_id=TEST_GUILD,
        channel_id=TEST_CHANNEL,
    )
    assert env_direct["status"] == "ok"
    assert env_direct["sanitized"] is True
    assert CLEAN_BODY_EXPECTED_SUBSTR in env_direct["spoken_text"]
    assert "Provider:" not in env_direct["spoken_text"]
    assert "Provider:" in env_direct["display_text"]

    _header("6. Hot-path imports remain clean")
    dtt.ingest_text_message = original_ingest  # type: ignore[assignment]
    import importlib

    for mod in (
        "control_plane.runtime.gateway",
        "control_plane.runtime.cognitive_loop",
        "execution.runtime.model_router",
        "execution.runtime.agent_runtime",
        "runtime.primitives",
    ):
        importlib.import_module(mod)
        print(f"  ok: {mod}")

    _clear_env()
    _header("DISCORD CLAUDE-PRIMARY + TTS SANITIZATION SMOKE TEST PASSED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
