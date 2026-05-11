#!/usr/bin/env python3
"""
Substrate Claude Responder v1 — smoke test.

Validates that the `claude_responder` adapter routes text through the
Claude Session Bridge and returns a structured reply dict without crashing
under any environment condition (tmux missing, session missing, empty
input, invalid target).

Also verifies that the Discord text transport wiring:
  - degrades correctly when the responder flag is OFF
  - routes through the responder when the flag is ON (shape check only —
    reply content depends on live claude CLI and is tolerated as empty)
  - never imports or touches hot-path modules

No provider API calls. No network. No hot-path imports.
"""

from __future__ import annotations

import json
import os
import sys
import uuid

sys.path.insert(0, os.environ.get("UMH_ROOT") or os.environ.get("OS_ROOT") or os.environ.get("EOS_ROOT") or "/opt/OS")

from runtime.substrate import claude_responder as cr  # noqa: E402
from runtime.substrate import claude_session_bridge as csb  # noqa: E402
from runtime.substrate import discord_text_transport as dtt  # noqa: E402

FAILURES: list[str] = []


def check(name: str, cond: bool, detail: str = "") -> None:
    status = "PASS" if cond else "FAIL"
    tail = f" — {detail}" if detail and not cond else ""
    print(f"  [{status}] {name}{tail}")
    if not cond:
        FAILURES.append(name)


def _hotpath_clean() -> bool:
    src = open(cr.__file__).read()
    forbidden = (
        "runtime.gateway",
        "runtime.cognitive_loop",
        "runtime.model_router",
        "runtime.agent_runtime",
        "runtime.primitives",
    )
    return not any(f in src for f in forbidden)


def main() -> int:
    print("Claude Responder v1 smoke test")

    # 1. Structural API
    check("adapter_has_entrypoint", callable(cr.respond_via_claude_session))
    check("adapter_has_default_target", cr.DEFAULT_TARGET in csb.VALID_TARGETS)
    check("adapter_has_default_session", isinstance(cr.DEFAULT_SESSION_NAME, str) and cr.DEFAULT_SESSION_NAME)

    # 2. Empty text → structured failure, never raises
    empty = cr.respond_via_claude_session("")
    check(
        "empty_text_structured",
        isinstance(empty, dict)
        and empty.get("ok") is False
        and empty.get("reason") == "empty_text"
        and empty.get("source") == "claude_session",
    )

    # 3. Invalid target → structured failure
    bad_target = cr.respond_via_claude_session("hello", target="mars")
    check(
        "invalid_target_structured",
        bad_target.get("ok") is False and bad_target.get("reason") == "invalid_target",
    )

    # 4. Session name mapping (per-channel + default)
    check("default_session_when_no_channel", cr.session_name_for_discord_channel(None) == cr.DEFAULT_SESSION_NAME)
    mapped = cr.session_name_for_discord_channel(123456789)
    check("per_channel_session_prefixed", mapped.startswith("dex_discord_") and "123456789" in mapped)

    # 5. Live call shape — use an isolated, never-launched session so no
    # claude CLI is actually required. Expect ok=False with empty reply
    # when tmux exists but claude CLI is absent, or ok=True/empty_reply
    # when the bridge loads successfully.
    tmux_available = csb.detect_tmux_available().get("available")
    cli_available = csb.detect_claude_cli_available().get("available")

    if not tmux_available:
        print("  [INFO] tmux not available — verifying degraded paths only")
        deg = cr.respond_via_claude_session("hello")
        check(
            "degraded_tmux_missing",
            deg.get("ok") is False and deg.get("reason") == "tmux_not_available" and deg.get("reply") == "",
        )
    elif not cli_available:
        print("  [INFO] claude CLI not available — verifying degraded path")
        deg = cr.respond_via_claude_session("hello")
        check(
            "degraded_claude_cli_missing",
            deg.get("ok") is False and deg.get("reason") == "claude_cli_not_available" and deg.get("reply") == "",
        )
    else:
        # Both available — use an isolated scratch session so we don't
        # pollute dex_main, and keep polling tight so the smoke stays fast.
        scratch = f"dex_smoke_resp_{uuid.uuid4().hex[:8]}"
        try:
            # Use a fresh shell (no claude launch) by first ensuring with
            # launch_claude=False, then calling respond which will re-ensure
            # with launch_claude=True. The bridge treats already-existing
            # sessions as idempotent so Claude is NOT re-launched — we
            # therefore expect an empty/garbage reply, which the adapter
            # correctly reports as ok=False, reason="empty_reply".
            csb.ensure_session("local", scratch, launch_claude=False)
            live = cr.respond_via_claude_session(
                "echo SMOKE_PING",
                target="local",
                session_name=scratch,
                poll_interval_s=0.2,
                max_polls=4,
            )
            check(
                "live_call_shape",
                isinstance(live, dict)
                and live.get("source") == "claude_session"
                and live.get("session") == scratch
                and "reply" in live
                and isinstance(live.get("reply"), str),
                json.dumps({k: v for k, v in live.items() if k != "ask"}),
            )
        finally:
            from runtime.substrate.claude_session_bridge import _run_tmux
            _run_tmux(["kill-session", "-t", scratch])

    # 6. Discord wiring — responder flag OFF → legacy substrate path (or
    # ingress_disabled if transport is off). Must not crash.
    os.environ.pop("EOS_DISCORD_CLAUDE_RESPONDER_ENABLED", None)
    os.environ["EOS_DISCORD_TEXT_TRANSPORT_ENABLED"] = "0"
    off_result = dtt.maybe_mirror_discord_text_message(
        "hello", guild_id="g1", channel_id="c1", user_id="u1"
    )
    check("responder_off_transport_off_returns_none", off_result is None)

    # 7. Discord wiring — transport ON, responder ON, but allowlists empty
    # → gate_denied (no crash, structured envelope).
    os.environ["EOS_DISCORD_TEXT_TRANSPORT_ENABLED"] = "1"
    os.environ["EOS_DISCORD_CLAUDE_RESPONDER_ENABLED"] = "1"
    os.environ.pop("EOS_DISCORD_TEXT_ALLOWED_GUILDS", None)
    os.environ.pop("EOS_DISCORD_TEXT_ALLOWED_CHANNELS", None)
    os.environ.pop("EOS_DISCORD_TEXT_ALLOWED_USERS", None)
    gated = dtt.maybe_mirror_discord_text_message(
        "hello", guild_id="g1", channel_id="c1", user_id="u1"
    )
    check(
        "gate_denied_structured",
        isinstance(gated, dict)
        and gated.get("ingress", {}).get("status") == "gate_denied"
        and "envelope" in gated,
    )

    # 8. Discord wiring — transport ON, responder ON, allowlists wide open.
    # Shape-only check: ingress dict present with source=claude_session OR a
    # structured failure reason; envelope present with known status.
    os.environ["EOS_DISCORD_TEXT_ALLOWED_GUILDS"] = "*"
    os.environ["EOS_DISCORD_TEXT_ALLOWED_CHANNELS"] = "*"
    os.environ["EOS_DISCORD_TEXT_ALLOWED_USERS"] = "*"
    # Point at a scratch session so we don't touch dex_main
    scratch2 = f"dex_smoke_wire_{uuid.uuid4().hex[:8]}"
    os.environ["EOS_DISCORD_CLAUDE_RESPONDER_TARGET"] = "local"
    os.environ["EOS_DISCORD_CLAUDE_RESPONDER_SESSION"] = scratch2
    try:
        wired = dtt.maybe_mirror_discord_text_message(
            "ping", guild_id="g1", channel_id="c1", user_id="u1"
        )
        ing = (wired or {}).get("ingress") or {}
        env = (wired or {}).get("envelope") or {}
        check("wiring_returns_dict", isinstance(wired, dict) and "ingress" in wired and "envelope" in wired)
        check(
            "wiring_ingress_source_tagged",
            ing.get("source") == "claude_session" or ing.get("status") in {
                "tmux_not_available", "claude_cli_not_available", "empty_reply", "ok",
            },
            json.dumps(ing),
        )
        check(
            "wiring_envelope_status_known",
            env.get("status") in {"ok", "no_reply", "tts_disabled", "ingress_disabled"},
            json.dumps(env),
        )
    finally:
        if csb.detect_tmux_available().get("available"):
            from runtime.substrate.claude_session_bridge import _run_tmux
            _run_tmux(["kill-session", "-t", scratch2])
        for key in (
            "EOS_DISCORD_TEXT_TRANSPORT_ENABLED",
            "EOS_DISCORD_CLAUDE_RESPONDER_ENABLED",
            "EOS_DISCORD_CLAUDE_RESPONDER_TARGET",
            "EOS_DISCORD_CLAUDE_RESPONDER_SESSION",
            "EOS_DISCORD_TEXT_ALLOWED_GUILDS",
            "EOS_DISCORD_TEXT_ALLOWED_CHANNELS",
            "EOS_DISCORD_TEXT_ALLOWED_USERS",
        ):
            os.environ.pop(key, None)

    # 9. Hot-path hygiene
    check("hotpath_clean", _hotpath_clean())

    # 10. pseudo_live_status surfaces responder config
    status = dtt.pseudo_live_status()
    check(
        "status_reports_responder_fields",
        "claude_responder_enabled" in status
        and "claude_responder_target" in status
        and "claude_responder_session" in status,
    )

    if FAILURES:
        print(f"\nFAIL — {len(FAILURES)}: {FAILURES}")
        return 1
    print("\nALL CHECKS PASSED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
