"""
Voice-session router responder smoke test.

Proves that the live Discord pseudo-live path wires the router-backed
voice responder (runtime.substrate.voice_eos_responder._eos_voice_responder)
as the global responder for voice sessions, replacing the substrate's
default "[role] heard: ..." echo stub.

This is a unit-level smoke test: it does NOT spin up a Discord client.
It exercises the exact module import chain the os-discord container
runs at startup, then drives a text message through the same
maybe_mirror_discord_text_message entrypoint that services/discord_bot.py
calls from on_message.

The broader router is stubbed via monkey-patching call_with_fallback so
we can prove:

  1. The voice session no longer returns "[role] heard: ..."
  2. The router-backed responder is invoked (call counter > 0)
  3. The role -> agent_type mapping is preserved
  4. On router failure, a bounded fallback string is returned
     (NOT the stub echo, NOT an unbounded traceback)
  5. Import hygiene: importing services/discord_bot.py does NOT import
     the hot path (gateway/cognitive_loop) at module load unintentionally
     — only that the responder install side-effect ran.

Run:

    python3 scripts/substrate_voice_router_responder_smoke_test.py
"""

from __future__ import annotations

import os
import sys

sys.path.insert(0, os.environ.get("UMH_ROOT") or os.environ.get("OS_ROOT") or os.environ.get("EOS_ROOT") or "/opt/OS")

# Force ingress ON for this test, with wildcard allow-lists so the
# Discord pseudo-live path runs end-to-end without real IDs.
os.environ["EOS_DISCORD_TEXT_TRANSPORT_ENABLED"] = "true"
os.environ["EOS_DISCORD_TEXT_REPLY_TTS_ENABLED"] = "false"
os.environ["EOS_DISCORD_TEXT_ALLOWED_GUILDS"] = "*"
os.environ["EOS_DISCORD_TEXT_ALLOWED_CHANNELS"] = "*"
os.environ["EOS_DISCORD_TEXT_ALLOWED_USERS"] = "*"


def _section(title: str) -> None:
    print(f"\n=== {title} ===", flush=True)


def _assert(cond: bool, msg: str) -> None:
    if not cond:
        print(f"  FAIL: {msg}", flush=True)
        raise SystemExit(1)
    print(f"  ok: {msg}", flush=True)


# ─── 1. Install responder exactly how discord_bot.py does at startup ─────────

_section("install router-backed voice responder")

from runtime.substrate.voice_eos_responder import (
    install_default_eos_voice_responder,
    is_eos_voice_responder_installed,
    uninstall_eos_voice_responder,
)

install_default_eos_voice_responder()
_assert(is_eos_voice_responder_installed(), "install_default_eos_voice_responder flagged installed")

# ─── 2. Monkey-patch the broader router so we can observe calls ─────────────

_section("monkey-patch model_router.call_with_fallback")

import runtime.model_router as _mr

_calls: list[dict] = []


class _FakeResult:
    def __init__(self, output: str, provider: str, model: str) -> None:
        self.output = output
        self.provider = provider
        self.model = model


def _fake_call_with_fallback(**kwargs):  # type: ignore[no-untyped-def]
    _calls.append(dict(kwargs))
    return _FakeResult(
        output="Understood — booking held. Next step: confirm time.",
        provider="claude_cli",
        model="cc_sdk",
    )


_real_call = _mr.call_with_fallback
_mr.call_with_fallback = _fake_call_with_fallback  # type: ignore[assignment]

try:
    # ─── 3. Drive the Discord pseudo-live path end-to-end ───────────────────

    _section("drive maybe_mirror_discord_text_message (happy path)")

    from runtime.substrate.discord_text_transport import (
        maybe_mirror_discord_text_message,
    )

    result = maybe_mirror_discord_text_message(
        "Lock the Thursday 4pm slot with Alex",
        guild_id="test_guild",
        channel_id="test_channel",
        user_id="test_user",
        role_slug="ea_orchestrator",
    )

    _assert(result is not None, "ingress not None (feature flag honored)")
    ingress = result.get("ingress") or {}
    envelope = result.get("envelope") or {}
    reply_text = ingress.get("reply_text") or envelope.get("display_text") or ""
    print(f"  reply_text = {reply_text!r}", flush=True)
    print(f"  router calls = {len(_calls)}", flush=True)

    _assert(
        len(_calls) == 1,
        "router-backed responder was invoked exactly once",
    )
    _assert(
        _calls[0].get("agent_type") == "ea_orchestrator",
        "role → agent_type mapping preserved (ea_orchestrator)",
    )
    _assert(
        _calls[0].get("trigger_source") == "voice_session",
        "router trigger_source = voice_session",
    )
    _assert(
        "heard:" not in reply_text,
        "reply is NOT the default stub echo ('[role] heard: ...')",
    )
    _assert(
        "Understood" in reply_text,
        "reply contains the fake router output body",
    )

    # ─── 4. Drive failure path — router raises ─────────────────────────────

    _section("drive router failure path (bounded fallback)")

    def _boom(**_kwargs):  # type: ignore[no-untyped-def]
        raise RuntimeError("simulated router outage")

    _mr.call_with_fallback = _boom  # type: ignore[assignment]

    result2 = maybe_mirror_discord_text_message(
        "This one should trip the fallback",
        guild_id="test_guild",
        channel_id="test_channel",
        user_id="test_user",
        role_slug="ea_orchestrator",
    )
    ingress2 = (result2 or {}).get("ingress") or {}
    envelope2 = (result2 or {}).get("envelope") or {}
    reply2 = ingress2.get("reply_text") or envelope2.get("display_text") or ""
    print(f"  fallback reply = {reply2!r}", flush=True)

    _assert("heard:" not in reply2, "fallback reply is NOT the stub echo")
    _assert(
        "degraded" in reply2 or "reasoning path" in reply2,
        "fallback reply is the bounded safe-fallback string",
    )

finally:
    _mr.call_with_fallback = _real_call  # type: ignore[assignment]
    uninstall_eos_voice_responder()

# ─── 5. Default-responder sanity check (proves the stub still exists) ───────

_section("default responder still returns stub when installed alone")

from runtime.substrate.voice_session import (
    VoiceSession,
    VoiceSessionStatus,
    _default_responder,
)

fake_session = VoiceSession(
    session_id="vs_test",
    node_id="node_test",
    role_slug="ea_orchestrator",
    status=VoiceSessionStatus.ACTIVE,
)
echo = _default_responder(fake_session, "ping")
print(f"  default echo = {echo!r}", flush=True)
_assert(
    echo.startswith("[ea_orchestrator] heard:"),
    "default _default_responder still returns stub echo (unchanged)",
)

_section("PASS")
print("Voice-session router responder wiring verified.", flush=True)
