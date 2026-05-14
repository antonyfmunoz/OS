#!/usr/bin/env python3
"""
Discord Channel Mode Routing v1 — smoke test.

Proves that:
  1.  Channel → mode classification is deterministic and exact-match only.
  2.  Mode → session mapping returns the right target/session per mode.
  3.  Unknown mode is a safe no-op (no thread-local poison, no defaults).
  4.  Thread-local mode_context binds and clears cleanly.
  5.  The new discord_mode_routing module imports NO hot-path modules.
  6.  End-to-end: a Discord text ingress in a builder channel causes the
      shared router's Claude CLI backend to be called with the builder
      target/session — WITHOUT forking the pipeline.
  7.  End-to-end: a Discord text ingress in a product channel causes the
      shared router's Claude CLI backend to be called with the product
      target/session.
  8.  End-to-end: an unknown channel falls through with router env
      defaults unchanged (no mode override applied).
  9.  Both modes still flow through model_router.call_with_fallback
      (single shared router; no second cognition pipeline).
 10.  TTS/footer split behavior in discord_text_transport is not
      regressed by the mode metadata additions.

Runs in-process. Stubs the Claude CLI backend so no tmux/claude CLI is
needed. Returns 0 on success, non-zero on failure.
"""

from __future__ import annotations

import os
import sys

sys.path.insert(0, os.environ.get("UMH_ROOT") or os.environ.get("OS_ROOT") or os.environ.get("EOS_ROOT") or "/opt/OS")


FAILURES: list[str] = []


def check(name: str, cond: bool, detail: str = "") -> None:
    if cond:
        print(f"  [PASS] {name}")
    else:
        FAILURES.append(name)
        print(f"  [FAIL] {name}  {detail}")


def _header(msg: str) -> None:
    print(f"\n── {msg} " + "─" * max(0, 60 - len(msg)))


def _reset_env() -> None:
    for k in (
        "EOS_DISCORD_BUILDER_CHANNELS",
        "EOS_DISCORD_PRODUCT_CHANNELS",
        "EOS_DISCORD_BUILDER_TARGET",
        "EOS_DISCORD_BUILDER_SESSION",
        "EOS_DISCORD_PRODUCT_TARGET",
        "EOS_DISCORD_PRODUCT_SESSION",
        "EOS_DISCORD_MODE_PER_CHANNEL",
        "EOS_DISCORD_TEXT_TRANSPORT_ENABLED",
        "EOS_DISCORD_TEXT_REPLY_TTS_ENABLED",
        "EOS_DISCORD_TEXT_ALLOWED_GUILDS",
        "EOS_DISCORD_TEXT_ALLOWED_CHANNELS",
        "EOS_DISCORD_TEXT_ALLOWED_USERS",
        "EOS_ROUTER_CLAUDE_CLI_TARGET",
        "EOS_ROUTER_CLAUDE_CLI_SESSION",
    ):
        os.environ.pop(k, None)


def test_classification() -> None:
    _header("1. resolve_discord_mode classification")
    from runtime.substrate import discord_mode_routing as dmr

    _reset_env()
    os.environ["EOS_DISCORD_BUILDER_CHANNELS"] = "111,222"
    os.environ["EOS_DISCORD_PRODUCT_CHANNELS"] = "333,444"

    check(
        "builder channel resolves to builder",
        dmr.resolve_discord_mode("g", "111") == dmr.MODE_BUILDER,
    )
    check(
        "product channel resolves to product",
        dmr.resolve_discord_mode("g", "333") == dmr.MODE_PRODUCT,
    )
    check(
        "unlisted channel resolves to unknown",
        dmr.resolve_discord_mode("g", "999") == dmr.MODE_UNKNOWN,
    )
    check(
        "None channel resolves to unknown",
        dmr.resolve_discord_mode("g", None) == dmr.MODE_UNKNOWN,
    )

    # Builder wins if a channel is in both lists
    os.environ["EOS_DISCORD_BUILDER_CHANNELS"] = "777"
    os.environ["EOS_DISCORD_PRODUCT_CHANNELS"] = "777"
    check(
        "builder wins when channel is in both",
        dmr.resolve_discord_mode("g", "777") == dmr.MODE_BUILDER,
    )

    # No fuzzy matching
    os.environ["EOS_DISCORD_BUILDER_CHANNELS"] = "111"
    check(
        "exact match only — substring does not match",
        dmr.resolve_discord_mode("g", "1111") == dmr.MODE_UNKNOWN,
    )


def test_session_mapping() -> None:
    _header("2. resolve_mode_session mapping")
    from runtime.substrate import discord_mode_routing as dmr

    _reset_env()
    os.environ["EOS_DISCORD_BUILDER_TARGET"] = "local"
    os.environ["EOS_DISCORD_BUILDER_SESSION"] = "dex_builder_main"
    os.environ["EOS_DISCORD_PRODUCT_TARGET"] = "vps"
    os.environ["EOS_DISCORD_PRODUCT_SESSION"] = "dex_product_main"

    b = dmr.resolve_mode_session(dmr.MODE_BUILDER, channel_id="111")
    check(
        "builder target/session resolved",
        b["mode"] == "builder"
        and b["target"] == "local"
        and b["session_name"] == "dex_builder_main",
        detail=str(b),
    )

    p = dmr.resolve_mode_session(dmr.MODE_PRODUCT, channel_id="333")
    check(
        "product target/session resolved",
        p["mode"] == "product"
        and p["target"] == "vps"
        and p["session_name"] == "dex_product_main",
        detail=str(p),
    )

    u = dmr.resolve_mode_session(dmr.MODE_UNKNOWN, channel_id="999")
    check(
        "unknown mode returns None target/session (no override)",
        u["mode"] == "unknown" and u["target"] is None and u["session_name"] is None,
        detail=str(u),
    )

    # Per-channel suffix
    os.environ["EOS_DISCORD_MODE_PER_CHANNEL"] = "1"
    b2 = dmr.resolve_mode_session(dmr.MODE_BUILDER, channel_id="111")
    check(
        "per-channel suffix appended to builder session",
        b2["session_name"] == "dex_builder_main_111",
        detail=str(b2),
    )
    p2 = dmr.resolve_mode_session(dmr.MODE_PRODUCT, channel_id="333")
    check(
        "per-channel suffix appended to product session",
        p2["session_name"] == "dex_product_main_333",
        detail=str(p2),
    )
    os.environ.pop("EOS_DISCORD_MODE_PER_CHANNEL", None)

    # Invalid target clamps to vps default
    os.environ["EOS_DISCORD_BUILDER_TARGET"] = "garbage"
    b3 = dmr.resolve_mode_session(dmr.MODE_BUILDER, channel_id="111")
    check(
        "invalid target clamps to vps default",
        b3["target"] == "vps",
        detail=str(b3),
    )


def test_thread_local_context() -> None:
    _header("3. mode_context thread-local binding")
    from runtime.substrate import discord_mode_routing as dmr

    dmr.clear_mode_context_for_tests()
    check(
        "starts clean",
        dmr.current_mode_context() is None,
    )

    with dmr.mode_context(
        dmr.MODE_BUILDER,
        target="vps",
        session_name="dex_builder_main",
        guild_id="g1",
        channel_id="c1",
    ):
        ctx = dmr.current_mode_context()
        check(
            "mode context set inside block",
            ctx is not None
            and ctx["mode"] == "builder"
            and ctx["session_name"] == "dex_builder_main",
            detail=str(ctx),
        )

    check(
        "mode context cleared after block",
        dmr.current_mode_context() is None,
    )

    # Unknown mode is a no-op — does NOT poison the thread-local
    with dmr.mode_context(dmr.MODE_UNKNOWN):
        check(
            "unknown mode leaves context None",
            dmr.current_mode_context() is None,
        )


def test_hotpath_clean() -> None:
    _header("4. hot-path hygiene on discord_mode_routing")
    from runtime.substrate import discord_mode_routing as dmr

    src = open(dmr.__file__).read()
    forbidden = (
        "runtime.gateway",
        "control_plane.runtime.cognitive_loop",
        "runtime.model_router",
        "execution.runtime.agent_runtime",
        "runtime.primitives",
    )
    leaked = [f for f in forbidden if f in src]
    check(
        "no hot-path imports in discord_mode_routing",
        not leaked,
        detail=f"leaked={leaked}",
    )


def test_end_to_end_router_override() -> None:
    """Simulate the full ingress→router path with a stubbed CLI backend."""
    _header("5. end-to-end: router sees builder/product/unknown overrides")

    from runtime.substrate import discord_mode_routing as dmr

    dmr.clear_mode_context_for_tests()

    import runtime.model_router as mr

    captured: list[dict] = []

    def _fake_cli(prompt, *, target, session_name, **kwargs):
        captured.append(
            {
                "target": target,
                "session_name": session_name,
                "mode": (dmr.current_mode_context() or {}).get("mode"),
            }
        )
        return {"ok": True, "reply": f"[stub/{session_name}] ack"}

    # Monkeypatch the responder the router imports locally
    import runtime.substrate.claude_responder as cr

    real_respond = cr.respond_via_claude_session
    cr.respond_via_claude_session = _fake_cli  # type: ignore[assignment]

    try:
        # --- builder mode ---
        with dmr.mode_context(
            dmr.MODE_BUILDER,
            target="vps",
            session_name="dex_builder_main",
            guild_id="g1",
            channel_id="c1",
        ):
            r = mr.call_with_fallback(
                prompt="hello from builder",
                task_type="fast_response",
                trigger_source="conversational",
                agent_type="ea_orchestrator",
            )
        check(
            "builder → router called CLI with builder session",
            captured
            and captured[-1]["session_name"] == "dex_builder_main"
            and captured[-1]["target"] == "vps"
            and captured[-1]["mode"] == "builder",
            detail=str(captured[-1:]),
        )
        check(
            "builder → router returned a RoutingResult via CLI backend",
            getattr(r, "provider", None) == "claude_cli",
            detail=f"provider={getattr(r, 'provider', None)}",
        )

        # --- product mode ---
        with dmr.mode_context(
            dmr.MODE_PRODUCT,
            target="vps",
            session_name="dex_product_main",
            guild_id="g1",
            channel_id="c2",
        ):
            r2 = mr.call_with_fallback(
                prompt="hello from product",
                task_type="fast_response",
                trigger_source="conversational",
                agent_type="ea_orchestrator",
            )
        check(
            "product → router called CLI with product session",
            captured
            and captured[-1]["session_name"] == "dex_product_main"
            and captured[-1]["mode"] == "product",
            detail=str(captured[-1:]),
        )
        check(
            "product → still claude_cli provider (one shared router)",
            getattr(r2, "provider", None) == "claude_cli",
        )

        # --- unknown mode (no context) ---
        dmr.clear_mode_context_for_tests()
        os.environ.pop("EOS_ROUTER_CLAUDE_CLI_TARGET", None)
        os.environ.pop("EOS_ROUTER_CLAUDE_CLI_SESSION", None)
        mr.call_with_fallback(
            prompt="hello unknown",
            task_type="fast_response",
            trigger_source="conversational",
            agent_type="ea_orchestrator",
        )
        last = captured[-1]
        check(
            "unknown → router uses CLI defaults (no mode override)",
            last["mode"] is None
            and last["session_name"] == cr.DEFAULT_SESSION_NAME
            and last["target"] == cr.DEFAULT_TARGET,
            detail=str(last),
        )
    finally:
        cr.respond_via_claude_session = real_respond  # type: ignore[assignment]
        dmr.clear_mode_context_for_tests()


def test_ingest_adds_mode_metadata() -> None:
    """discord_text_transport adds discord_mode to transcript metadata
    AND binds the thread-local around inject_transcript."""
    _header("6. discord_text_transport wires mode into meta + thread-local")

    _reset_env()
    os.environ["EOS_DISCORD_TEXT_TRANSPORT_ENABLED"] = "1"
    os.environ["EOS_DISCORD_TEXT_ALLOWED_GUILDS"] = "*"
    os.environ["EOS_DISCORD_TEXT_ALLOWED_CHANNELS"] = "*"
    os.environ["EOS_DISCORD_TEXT_ALLOWED_USERS"] = "*"
    os.environ["EOS_DISCORD_BUILDER_CHANNELS"] = "111"
    os.environ["EOS_DISCORD_PRODUCT_CHANNELS"] = "333"
    os.environ["EOS_DISCORD_BUILDER_SESSION"] = "dex_builder_main"
    os.environ["EOS_DISCORD_PRODUCT_SESSION"] = "dex_product_main"
    os.environ["EOS_DISCORD_BUILDER_TARGET"] = "vps"
    os.environ["EOS_DISCORD_PRODUCT_TARGET"] = "vps"

    from runtime.substrate import discord_mode_routing as dmr
    from runtime.substrate import discord_text_transport as dtt
    from runtime.substrate import transcript_inject as ti

    captured_meta: list[dict] = []
    captured_mode_during_inject: list = []

    def _fake_inject_transcript(node_id, text, **kwargs):
        captured_meta.append(kwargs.get("metadata") or {})
        captured_mode_during_inject.append(dmr.current_mode_context())
        return {
            "status": "ok",
            "session_id": "sess-test",
            "role_slug": kwargs.get("role_slug"),
            "detail": "stub",
            "audio_loop": None,
        }

    # Patch inject_transcript in the namespace discord_text_transport imports from
    real_inject = ti.inject_transcript
    ti.inject_transcript = _fake_inject_transcript  # type: ignore[assignment]

    # Also stub the transport initializer so no real voice transport is built
    import runtime.substrate.discord_voice_transport as dvt

    class _StubTransport:
        node_id = "stub-node"

    real_get = dvt.get_default_discord_voice_transport
    dvt.get_default_discord_voice_transport = lambda **_k: _StubTransport()  # type: ignore[assignment]

    try:
        # Builder channel
        res_b = dtt.ingest_text_message(
            "hi",
            guild_id="g1",
            channel_id="111",
            user_id="u1",
        )
        check(
            "builder ingest added discord_mode=builder to meta",
            captured_meta[-1].get("discord_mode") == "builder",
            detail=str(captured_meta[-1]),
        )
        check(
            "builder ingest set responder_session to builder main",
            captured_meta[-1].get("responder_session") == "dex_builder_main",
        )
        check(
            "mode_context was bound during inject (builder)",
            captured_mode_during_inject[-1] is not None
            and captured_mode_during_inject[-1]["mode"] == "builder",
            detail=str(captured_mode_during_inject[-1]),
        )

        # Product channel
        dtt.ingest_text_message(
            "hi",
            guild_id="g1",
            channel_id="333",
            user_id="u1",
        )
        check(
            "product ingest added discord_mode=product to meta",
            captured_meta[-1].get("discord_mode") == "product",
        )
        check(
            "mode_context was bound during inject (product)",
            captured_mode_during_inject[-1] is not None
            and captured_mode_during_inject[-1]["mode"] == "product",
        )

        # Unknown channel — mode_context stays None
        dtt.ingest_text_message(
            "hi",
            guild_id="g1",
            channel_id="999",
            user_id="u1",
        )
        check(
            "unknown ingest added discord_mode=unknown to meta",
            captured_meta[-1].get("discord_mode") == "unknown",
        )
        check(
            "mode_context NOT bound for unknown channel",
            captured_mode_during_inject[-1] is None,
            detail=str(captured_mode_during_inject[-1]),
        )

        # Thread-local cleared after ingest returns
        check(
            "thread-local cleared after ingest_text_message returns",
            dmr.current_mode_context() is None,
        )

        # Ingest returned ok (pipeline not broken by metadata additions)
        check(
            "ingest returned status=ok for builder call",
            res_b.get("status") == "ok",
            detail=str(res_b),
        )
    finally:
        ti.inject_transcript = real_inject  # type: ignore[assignment]
        dvt.get_default_discord_voice_transport = real_get  # type: ignore[assignment]
        dmr.clear_mode_context_for_tests()


def test_tts_footer_untouched() -> None:
    """The mode routing additions must not change TTS/footer split behavior."""
    _header("7. TTS/footer split preserved by envelope builder")

    _reset_env()
    os.environ["EOS_DISCORD_TEXT_TRANSPORT_ENABLED"] = "1"
    os.environ["EOS_DISCORD_TEXT_REPLY_TTS_ENABLED"] = "1"

    from runtime.substrate import discord_text_transport as dtt

    env = dtt.build_tts_reply_envelope(
        "hello world 🎉\n— footer debug info",
        guild_id="g1",
        channel_id="111",
    )
    check(
        "envelope returns status=ok",
        env.get("status") == "ok",
        detail=str(env),
    )
    check(
        "envelope exposes display_text and spoken_text fields",
        "display_text" in env and "spoken_text" in env,
    )
    check(
        "envelope exposes emit_plan (split behavior intact)",
        isinstance(env.get("emit_plan"), list),
    )


def test_shared_router_tripwire() -> None:
    """Tripwire: neither mode should bypass the broader router.

    We assert the mode router module does not import or call
    respond_via_claude_session directly — the ONLY path to claude_cli
    is through runtime.model_router.call_with_fallback.
    """
    _header("8. tripwire: no mode router bypass of shared router")

    from runtime.substrate import discord_mode_routing as dmr

    src = open(dmr.__file__).read()
    check(
        "discord_mode_routing does not import claude_responder",
        "claude_responder" not in src,
    )
    check(
        "discord_mode_routing does not import claude_session_bridge",
        "claude_session_bridge" not in src,
    )
    check(
        "discord_mode_routing does not import model_router",
        "from runtime.model_router" not in src
        and "import runtime.model_router" not in src,
    )


def main() -> int:
    print("Discord Channel Mode Routing v1 — smoke test")
    _reset_env()
    test_classification()
    test_session_mapping()
    test_thread_local_context()
    test_hotpath_clean()
    test_end_to_end_router_override()
    test_ingest_adds_mode_metadata()
    test_tts_footer_untouched()
    test_shared_router_tripwire()
    _reset_env()

    print()
    if FAILURES:
        print(f"FAILED ({len(FAILURES)}): {FAILURES}")
        return 1
    print("DISCORD MODE ROUTING SMOKE TEST PASSED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
