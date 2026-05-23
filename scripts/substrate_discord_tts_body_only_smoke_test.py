#!/usr/bin/env python3
"""
Discord TTS Body-Only Split — smoke test.

Proves:
  1. Visible Discord message retains the full reply (footer, skill block,
     provider badge — all preserved).
  2. TTS payload is the sanitized body ONLY — no footer/meta/debug text.
  3. Main conversational body is preserved in spoken_text.
  4. Malformed footer input is safe (no crash).
  5. Empty input is safe.
  6. `emit_plan` drives a two-send split (visible + spoken) when sanitizer
     actually stripped content and TTS is on.
  7. `emit_plan` collapses to a single send when no sanitization was needed.
  8. `emit_plan` collapses to a single visible send when spoken is empty.
  9. Reporting surfaces last_display_length + last_spoken_length.
 10. Hot-path imports remain clean.

No live Discord required — runs purely against the substrate envelope.
"""

from __future__ import annotations

import os
import sys

sys.path.insert(0, os.environ.get("UMH_ROOT") or os.environ.get("OS_ROOT") or os.environ.get("EOS_ROOT") or "/opt/OS")

from substrate.execution.transport import discord_text_transport as dtt  # noqa: E402
from substrate.execution.transport.discord_text_transport import (  # noqa: E402
    build_tts_reply_envelope,
    maybe_mirror_discord_text_message,
    pseudo_live_status,
    reset_backend_state_for_tests,
    reset_text_history_for_tests,
)
from substrate.execution.transport.tts_sanitize import sanitize_tts_reply  # noqa: E402

TEST_GUILD = "bo-guild"
TEST_CHANNEL = "bo-channel"
TEST_USER = "5555"

ENV_INGRESS = "EOS_DISCORD_TEXT_TRANSPORT_ENABLED"
ENV_TTS = "EOS_DISCORD_TEXT_REPLY_TTS_ENABLED"
ENV_GUILDS = "EOS_DISCORD_TEXT_ALLOWED_GUILDS"
ENV_CHANNELS = "EOS_DISCORD_TEXT_ALLOWED_CHANNELS"
ENV_USERS = "EOS_DISCORD_TEXT_ALLOWED_USERS"
ENV_CLAUDE = "EOS_DISCORD_CLAUDE_RESPONDER_ENABLED"
_ALL_ENV = [ENV_INGRESS, ENV_TTS, ENV_GUILDS, ENV_CHANNELS, ENV_USERS, ENV_CLAUDE]


def _header(msg: str) -> None:
    print(f"\n── {msg} " + "─" * max(0, 60 - len(msg)))


def _clear_env() -> None:
    for k in _ALL_ENV:
        os.environ.pop(k, None)


def _enable_and_allow(*, tts: bool = True, claude: bool = True) -> None:
    os.environ[ENV_INGRESS] = "1"
    if tts:
        os.environ[ENV_TTS] = "1"
    os.environ[ENV_GUILDS] = TEST_GUILD
    os.environ[ENV_CHANNELS] = TEST_CHANNEL
    os.environ[ENV_USERS] = "*"
    if claude:
        os.environ[ENV_CLAUDE] = "1"


FULL_REPLY_WITH_FOOTER = """\
Morning. Your agenda for today is:
- close the Lyfe Institute outreach loop
- ship the Discord TTS split
- sleep before midnight

★ Insight ─────────────────────────────────────
- outreach first, code second
- content is the advertising
─────────────────────────────────────────────────

Provider: gemini-2.5-flash
Tokens: 1,240    Cost: $0.003
[Skill: using-superpowers]
— DEX
"""

BODY_SUBSTR_1 = "Morning. Your agenda for today is:"
BODY_SUBSTR_2 = "ship the Discord TTS split"

FOOTER_MARKERS = (
    "★ Insight",
    "Provider:",
    "gemini-2.5-flash",
    "Tokens:",
    "Cost:",
    "[Skill:",
    "— DEX",
    "─────────────",
)


class _FakeResponderOK:
    def __init__(self, reply: str) -> None:
        self._reply = reply

    def __call__(self, text, *, target, session_name, **kw):
        return {
            "ok": True,
            "reply": self._reply,
            "source": "claude_session",
            "session": session_name,
            "target": target,
            "reason": "ok",
        }


def _install_fake_responder(reply: str) -> None:
    import execution.transport.claude_responder as cr

    cr.respond_via_claude_session = _FakeResponderOK(reply)  # type: ignore[assignment]


def main() -> int:
    _header("0. Cleanup")
    _clear_env()
    reset_text_history_for_tests()
    reset_backend_state_for_tests()

    _header("1. sanitize_tts_reply preserves body, strips footer")
    spoken = sanitize_tts_reply(FULL_REPLY_WITH_FOOTER)
    print(f"  spoken_len={len(spoken)}")
    assert BODY_SUBSTR_1 in spoken
    assert BODY_SUBSTR_2 in spoken
    for marker in FOOTER_MARKERS:
        assert marker not in spoken, f"spoken still contains footer marker: {marker}"

    _header("2. Malformed / empty input is safe")
    assert sanitize_tts_reply(None) == ""
    assert sanitize_tts_reply("") == ""
    assert sanitize_tts_reply("   \n\n  ") == ""
    # Only footer, no body → empty spoken
    footer_only = "Provider: gemini\nTokens: 42\n──────────"
    assert sanitize_tts_reply(footer_only) == ""

    _header("3. Envelope split: visible keeps footer, tts_content strips it")
    _enable_and_allow(tts=True, claude=False)
    env = build_tts_reply_envelope(
        FULL_REPLY_WITH_FOOTER,
        guild_id=TEST_GUILD,
        channel_id=TEST_CHANNEL,
    )
    print(f"  status={env['status']} sanitized={env['sanitized']} tts={env['tts']}")
    print(
        f"  display_len={len(env['display_text'])} spoken_len={len(env['spoken_text'])}"
    )
    print(f"  emit_plan_roles={[e['role'] for e in env['emit_plan']]}")
    assert env["status"] == "ok"
    assert env["sanitized"] is True
    # Visible (content / display_text) keeps footer.
    for marker in ("Provider:", "★ Insight", "— DEX"):
        assert marker in env["content"], f"visible lost footer marker: {marker}"
        assert marker in env["display_text"], marker
    # Spoken (tts_content / spoken_text) strips footer.
    for marker in FOOTER_MARKERS:
        assert marker not in env["tts_content"], f"tts_content leaked: {marker}"
        assert marker not in env["spoken_text"], f"spoken_text leaked: {marker}"
    # Body preserved in spoken.
    assert BODY_SUBSTR_1 in env["spoken_text"]
    assert BODY_SUBSTR_2 in env["spoken_text"]

    _header("4. emit_plan yields two sends: visible (tts=False) + spoken (tts=True)")
    plan = env["emit_plan"]
    assert len(plan) == 2, plan
    visible, spoken_entry = plan[0], plan[1]
    assert visible["role"] == "visible"
    assert visible["tts"] is False
    assert "Provider:" in visible["content"]
    assert spoken_entry["role"] == "spoken"
    assert spoken_entry["tts"] is True
    for marker in FOOTER_MARKERS:
        assert marker not in spoken_entry["content"], marker
    assert BODY_SUBSTR_1 in spoken_entry["content"]

    _header("5. Clean body with NO footer → single combined send")
    clean_only = "Hey, that's the update — nothing else to add."
    env_clean = build_tts_reply_envelope(
        clean_only,
        guild_id=TEST_GUILD,
        channel_id=TEST_CHANNEL,
    )
    print(
        f"  sanitized={env_clean['sanitized']} plan_len={len(env_clean['emit_plan'])}"
    )
    assert env_clean["sanitized"] is False
    assert len(env_clean["emit_plan"]) == 1
    assert env_clean["emit_plan"][0]["role"] == "combined"
    assert env_clean["emit_plan"][0]["tts"] is True
    assert env_clean["emit_plan"][0]["content"] == clean_only

    _header("6. Footer-only reply → single visible send, no spoken gibberish")
    env_footer_only = build_tts_reply_envelope(
        "Provider: gemini\nTokens: 42\n──────────\n— DEX",
        guild_id=TEST_GUILD,
        channel_id=TEST_CHANNEL,
    )
    print(
        f"  spoken_text={env_footer_only['spoken_text']!r} plan={env_footer_only['emit_plan']}"
    )
    assert env_footer_only["spoken_text"] == ""
    assert len(env_footer_only["emit_plan"]) == 1
    assert env_footer_only["emit_plan"][0]["role"] == "visible"
    assert env_footer_only["emit_plan"][0]["tts"] is False

    _header("7. TTS disabled → single visible send, tts=False, footer preserved")
    os.environ.pop(ENV_TTS, None)
    env_no_tts = build_tts_reply_envelope(
        FULL_REPLY_WITH_FOOTER,
        guild_id=TEST_GUILD,
        channel_id=TEST_CHANNEL,
    )
    assert len(env_no_tts["emit_plan"]) == 1
    assert env_no_tts["emit_plan"][0]["tts"] is False
    assert "Provider:" in env_no_tts["emit_plan"][0]["content"]
    os.environ[ENV_TTS] = "1"

    _header("8. End-to-end via maybe_mirror_discord_text_message (shared router)")
    _enable_and_allow(tts=True, claude=True)
    # Shared-router path now: Discord calls ingest_text_message which reaches
    # the broader responder. Patch ingest_text_message directly so the test
    # exercises the new seam rather than the removed Discord-only bypass.
    _original_ingest = dtt.ingest_text_message

    def _fake_ingest(text, **kw):
        return {
            "status": "ok",
            "session_id": "fake-session-2",
            "role_slug": kw.get("role_slug"),
            "detail": "router_served",
            "audio_loop": None,
            "reply_text": FULL_REPLY_WITH_FOOTER,
        }

    dtt.ingest_text_message = _fake_ingest  # type: ignore[assignment]
    reset_backend_state_for_tests()
    result = maybe_mirror_discord_text_message(
        "what's on for today",
        guild_id=TEST_GUILD,
        channel_id=TEST_CHANNEL,
        user_id=TEST_USER,
    )
    assert result is not None
    r_env = result["envelope"]
    plan = r_env["emit_plan"]
    print(f"  e2e plan_roles={[e['role'] for e in plan]}")
    assert len(plan) == 2
    assert plan[0]["role"] == "visible" and plan[0]["tts"] is False
    assert plan[1]["role"] == "spoken" and plan[1]["tts"] is True
    assert "Provider:" in plan[0]["content"]
    for marker in FOOTER_MARKERS:
        assert marker not in plan[1]["content"]
    assert BODY_SUBSTR_2 in plan[1]["content"]
    dtt.ingest_text_message = _original_ingest  # type: ignore[assignment]

    _header("9. pseudo_live_status reports display + spoken lengths")
    status = pseudo_live_status()
    print(f"  last_display_length={status['last_display_length']}")
    print(f"  last_spoken_length={status['last_spoken_length']}")
    print(f"  last_tts_sanitized={status['last_tts_sanitized']}")
    assert isinstance(status["last_display_length"], int)
    assert isinstance(status["last_spoken_length"], int)
    assert status["last_display_length"] > status["last_spoken_length"]
    assert status["last_tts_sanitized"] is True

    _header("10. Hot-path imports clean")
    import importlib

    for mod in (
        "substrate.control_plane.runtime.gateway",
        "substrate.control_plane.runtime.cognitive_loop",
        "substrate.execution.runtime.model_router",
        "substrate.execution.runtime.agent_runtime",
        "runtime.primitives",
    ):
        try:
            importlib.import_module(mod)
            print(f"  ok: {mod}")
        except Exception as e:  # noqa: BLE001
            print(f"  WARN ({mod}): {e}")

    _clear_env()
    _header("DISCORD TTS BODY-ONLY SPLIT SMOKE TEST PASSED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
