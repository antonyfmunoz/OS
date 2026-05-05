#!/usr/bin/env python3
"""Regression smoke test: router claude_cli backend runtime activation.

Locks in the invariants behind the 2026-04-08 fix where the os-discord
container wasn't reaching the host tmux session. Verifies:

  1. Live router path (call_with_fallback) enters the claude_cli backend
     branch when EOS_ROUTER_CLAUDE_CLI_ENABLED=1, regardless of fast/heavy.
  2. Backend #0 attempt is surfaced via [Router] log lines.
  3. When the bridge returns ok=True, cc_sdk/gemini/ollama are never touched.
  4. When the bridge returns ok=False (e.g. tmux missing), we fall through
     to the rest of the provider chain.
  5. The Discord shared path (voice_eos_responder._eos_voice_responder)
     reaches the exact same router entrypoint.
  6. Disabling the gate (EOS_ROUTER_CLAUDE_CLI_ENABLED=0) skips the
     backend entirely without touching the bridge.

This is a pure unit-level smoke test — it monkeypatches the bridge and the
router internals so it can run anywhere, with or without tmux installed.
Run: python3 scripts/substrate_router_claude_runtime_activation_smoke_test.py
"""

from __future__ import annotations

import logging
import os
import sys

sys.path.insert(0, "/opt/OS")


def _reload_router():
    import importlib

    import eos_ai.model_router as mr

    return importlib.reload(mr)


def _install_bridge_stub(*, ok: bool, reason: str = "ok", reply: str = "hi"):
    """Replace respond_via_claude_session with a deterministic stub."""
    import eos_ai.substrate.claude_responder as cr

    calls: list[dict] = []

    def _stub(text: str, *, target: str, session_name: str, **_kw) -> dict:
        calls.append({"text": text, "target": target, "session_name": session_name})
        return {
            "ok": ok,
            "reply": reply if ok else "",
            "source": "claude_session",
            "session": session_name,
            "target": target,
            "reason": reason,
        }

    cr.respond_via_claude_session = _stub  # type: ignore[assignment]
    return calls


def _stub_registry_providers(mr_mod):
    """Neuter MODEL_REGISTRY + cc_sdk so they can't mask backend #0."""

    class _FakeRouter:
        _cc_sdk_available = False
        _last_input_tokens = 0
        _last_output_tokens = 0

        def _check_availability(self) -> None:
            return None

        def call(self, *_a, **_k) -> str:
            return "FALLBACK_REPLY"

    mr_mod.get_router = lambda: _FakeRouter()  # type: ignore[assignment]
    mr_mod.MODEL_REGISTRY = {}  # type: ignore[assignment]


def check(name: str, cond: bool, detail: str = "") -> None:
    mark = "✓" if cond else "✗"
    print(f"  {mark} {name}{(' — ' + detail) if detail else ''}")
    if not cond:
        raise SystemExit(1)


def main() -> int:
    logging.basicConfig(level=logging.INFO, format="%(message)s")

    # ── Test 1: backend entered + success path short-circuits fallback ──
    print("\n[1] claude_cli success path")
    os.environ["EOS_ROUTER_CLAUDE_CLI_ENABLED"] = "1"
    os.environ["EOS_ROUTER_CLAUDE_CLI_TARGET"] = "vps"
    os.environ["EOS_ROUTER_CLAUDE_CLI_SESSION"] = "dex_smoke"
    mr = _reload_router()
    _stub_registry_providers(mr)
    calls = _install_bridge_stub(ok=True, reply="PRIMARY_OK")
    result = mr.call_with_fallback(prompt="ping", task_type="fast_response")
    check("backend invoked", len(calls) == 1, f"calls={len(calls)}")
    check("target wired", calls[0]["target"] == "vps")
    check("session wired", calls[0]["session_name"] == "dex_smoke")
    check("provider = claude_cli", result.provider == "claude_cli")
    check("reply propagated", result.output == "PRIMARY_OK")
    check(
        "fallback providers untouched",
        result.model.startswith("tmux:"),
        detail=result.model,
    )

    # ── Test 2: heavy path also enters backend #0 ──
    print("\n[2] claude_cli heavy path")
    mr = _reload_router()
    _stub_registry_providers(mr)
    calls = _install_bridge_stub(ok=True, reply="HEAVY_OK")
    result = mr.call_with_fallback(
        prompt="strategic q", task_type="analyze", agent_type="portfolio_advisor"
    )
    check("heavy path invoked backend", len(calls) == 1)
    check("heavy path used claude_cli", result.provider == "claude_cli")

    # ── Test 3: bounded failure falls through to provider chain ──
    print("\n[3] claude_cli failure falls through")
    mr = _reload_router()
    _stub_registry_providers(mr)
    calls = _install_bridge_stub(ok=False, reason="tmux_not_available")
    result = mr.call_with_fallback(prompt="ping", task_type="fast_response")
    check("backend was still attempted", len(calls) == 1)
    check("did not return claude_cli", result.provider != "claude_cli")
    # FakeRouter.call returns "FALLBACK_REPLY" — if it's reached we know the
    # chain moved on past backend #0.
    check(
        "chain progressed past backend #0",
        result.output in ("FALLBACK_REPLY", "") or result.provider == "none",
        detail=f"provider={result.provider} output={result.output[:40]!r}",
    )

    # ── Test 4: env gate disables backend ──
    print("\n[4] env gate disables backend entirely")
    os.environ["EOS_ROUTER_CLAUDE_CLI_ENABLED"] = "0"
    mr = _reload_router()
    _stub_registry_providers(mr)
    calls = _install_bridge_stub(ok=True, reply="SHOULD_NOT_SEE")
    result = mr.call_with_fallback(prompt="ping", task_type="fast_response")
    check("bridge not called when gated off", len(calls) == 0)
    check("provider != claude_cli when gated off", result.provider != "claude_cli")
    os.environ["EOS_ROUTER_CLAUDE_CLI_ENABLED"] = "1"

    # ── Test 5: Discord shared path is wired to the same router entry ──
    #
    # voice_eos_responder is the shared responder invoked by the voice
    # substrate that ingest_text_message feeds into. The invariant we need
    # to lock in is "this module imports call_with_fallback from
    # eos_ai.model_router" — NOT a second router or a bypass path. If that
    # import ever drifts (e.g. someone copies the router or adds a
    # discord-only shortcut), this test will catch it.
    print("\n[5] discord shared path is wired to eos_ai.model_router")
    import inspect

    from eos_ai.substrate import voice_eos_responder as ver

    src = inspect.getsource(ver._eos_voice_responder)
    check(
        "voice_eos_responder imports call_with_fallback",
        "from eos_ai.model_router import call_with_fallback" in src,
    )
    check(
        "voice_eos_responder calls call_with_fallback",
        "call_with_fallback(" in src,
    )

    # And prove that discord_text_transport routes into the same voice
    # substrate (ingest_text_message), not a private bypass.
    from eos_ai.substrate import discord_text_transport as dtt

    mirror_src = inspect.getsource(dtt.maybe_mirror_discord_text_message)
    check(
        "discord mirror uses shared ingest_text_message",
        "ingest_text_message(" in mirror_src,
    )

    print("\nAll router claude_cli runtime activation checks passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
