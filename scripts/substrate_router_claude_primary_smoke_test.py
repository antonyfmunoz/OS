#!/usr/bin/env python3
"""
Router Claude-CLI Primary Backend — smoke test.

Proves the broader router (runtime.model_router.call_with_fallback) now:

  1. Tries Claude CLI (persistent tmux session) FIRST when available.
  2. Returns provider="claude_cli" on success and does NOT fall through to
     cc_sdk / registry providers.
  3. Falls through to the existing provider chain (cc_sdk / registry) when
     Claude CLI returns a bounded failure reason (tmux_not_available,
     claude_cli_not_available, session_missing, empty_reply, ask_exception).
  4. Honors the EOS_ROUTER_CLAUDE_CLI_ENABLED=0 kill-switch.
  5. PROVIDER_PRIORITY / PROVIDER_PRIORITY_FAST both rank CLAUDE_CLI at 0.
  6. Hot-path imports remain clean.

All backends are monkeypatched — no live Anthropic / Gemini / tmux / claude
CLI required. No network calls.
"""

from __future__ import annotations

import os
import sys

sys.path.insert(0, os.environ.get("UMH_ROOT") or os.environ.get("OS_ROOT") or os.environ.get("EOS_ROOT") or "/opt/OS")

from runtime import model_router as mr  # noqa: E402
from runtime.model_router import (  # noqa: E402
    ModelProvider,
    PROVIDER_PRIORITY,
    PROVIDER_PRIORITY_FAST,
    RoutingResult,
    call_with_fallback,
    get_router,
)


def _header(msg: str) -> None:
    print(f"\n── {msg} " + "─" * max(0, 60 - len(msg)))


# ─── Fake backends ───────────────────────────────────────────────────────────


class _FakeClaudeResponder:
    """Stand-in for runtime.substrate.claude_responder.respond_via_claude_session."""

    def __init__(self, *, ok: bool, reply: str = "", reason: str = "ok") -> None:
        self.ok = ok
        self.reply = reply
        self.reason = reason
        self.calls = 0

    def __call__(self, text, *, target, session_name, **kw):
        self.calls += 1
        return {
            "ok": self.ok,
            "reply": self.reply,
            "source": "claude_session",
            "session": session_name,
            "target": target,
            "reason": self.reason,
        }


class _CCSDKTripwire:
    """If called, fail the test — cc_sdk must not be reached when Claude CLI wins."""

    calls = 0

    def __call__(self, *a, **kw):
        type(self).calls += 1
        raise AssertionError(
            "ROUTER VIOLATION: cc_sdk was called even though Claude CLI backend succeeded"
        )


class _CCSDKFake:
    """Stand-in for query_cc_sync when we WANT fallback to reach it."""

    def __init__(self, output: str = "from cc_sdk") -> None:
        self.output = output
        self.calls = 0

    def __call__(self, *, prompt, system, task_type, agent_id, max_budget_usd):
        self.calls += 1

        class _R:
            pass

        r = _R()
        r.output = self.output
        r.model = "claude-opus-4-6"
        return r


def _install_claude_responder(fake) -> None:
    # The router imports claude_responder lazily inside call_with_fallback,
    # so patching via sys.modules works. Easiest: inject a shim module.
    import runtime.substrate.claude_responder as cr

    cr.respond_via_claude_session = fake  # type: ignore[assignment]
    cr.DEFAULT_TARGET = "vps"
    cr.DEFAULT_SESSION_NAME = "dex_main"


def _install_cc_sdk(fn) -> None:
    mr.query_cc_sync = fn  # type: ignore[assignment]


def _force_router_availability() -> None:
    router = get_router()
    router._cc_sdk_available = True


def main() -> int:
    _header("0. Setup")
    os.environ.pop("EOS_ROUTER_CLAUDE_CLI_ENABLED", None)
    _force_router_availability()

    _header("1. PROVIDER_PRIORITY has CLAUDE_CLI at position 0")
    assert PROVIDER_PRIORITY[ModelProvider.CLAUDE_CLI] == 0
    assert PROVIDER_PRIORITY_FAST[ModelProvider.CLAUDE_CLI] == 0
    # cc_sdk must be strictly AFTER claude_cli on heavy path
    assert PROVIDER_PRIORITY[ModelProvider.CC_SDK] > 0
    print(
        "  heavy priority: CLAUDE_CLI=0, CC_SDK=%d"
        % PROVIDER_PRIORITY[ModelProvider.CC_SDK]
    )
    print(
        "  fast  priority: CLAUDE_CLI=0, GEMINI=%d"
        % PROVIDER_PRIORITY_FAST[ModelProvider.GEMINI]
    )

    _header("2. Claude CLI success → provider=claude_cli, cc_sdk NEVER called")
    ok_responder = _FakeClaudeResponder(ok=True, reply="hello from tmux claude")
    _install_claude_responder(ok_responder)
    _CCSDKTripwire.calls = 0
    _install_cc_sdk(_CCSDKTripwire())
    result = call_with_fallback(
        prompt="ping",
        task_type="fast_response",
    )
    print(f"  provider={result.provider} model={result.model}")
    print(f"  output={result.output!r}")
    assert isinstance(result, RoutingResult)
    assert result.provider == "claude_cli"
    assert result.output == "hello from tmux claude"
    assert ok_responder.calls == 1
    assert _CCSDKTripwire.calls == 0

    _header("3. Claude CLI success on HEAVY path → provider=claude_cli")
    ok_responder2 = _FakeClaudeResponder(ok=True, reply="heavy reply")
    _install_claude_responder(ok_responder2)
    _CCSDKTripwire.calls = 0
    _install_cc_sdk(_CCSDKTripwire())
    result = call_with_fallback(
        prompt="strategic question",
        task_type="strategic",
        agent_type="ceo",
    )
    print(f"  provider={result.provider}")
    assert result.provider == "claude_cli"
    assert ok_responder2.calls == 1
    assert _CCSDKTripwire.calls == 0

    _header("4. Claude CLI tmux_not_available → fallback to cc_sdk")
    fail_responder = _FakeClaudeResponder(
        ok=False, reply="", reason="tmux_not_available"
    )
    _install_claude_responder(fail_responder)
    cc_fake = _CCSDKFake(output="from cc_sdk fallback")
    _install_cc_sdk(cc_fake)
    result = call_with_fallback(
        prompt="ping",
        task_type="strategic",
        agent_type="ceo",
    )
    print(f"  provider={result.provider} output={result.output!r}")
    assert fail_responder.calls == 1
    assert cc_fake.calls == 1
    assert result.provider == "cc_sdk"
    assert result.output == "from cc_sdk fallback"

    _header("5. Claude CLI empty_reply → fallback path still reached")
    empty_responder = _FakeClaudeResponder(ok=True, reply="", reason="empty_reply")
    _install_claude_responder(empty_responder)
    cc_fake2 = _CCSDKFake(output="cc_sdk after empty")
    _install_cc_sdk(cc_fake2)
    result = call_with_fallback(
        prompt="ping",
        task_type="strategic",
        agent_type="ceo",
    )
    # ok=True but reply="" → router treats as "no output" and falls through
    assert empty_responder.calls == 1
    assert cc_fake2.calls == 1
    assert result.provider == "cc_sdk"

    _header("6. EOS_ROUTER_CLAUDE_CLI_ENABLED=0 kill-switch bypasses claude_cli")
    os.environ["EOS_ROUTER_CLAUDE_CLI_ENABLED"] = "0"
    never_responder = _FakeClaudeResponder(ok=True, reply="should not be used")
    _install_claude_responder(never_responder)
    cc_fake3 = _CCSDKFake(output="cc_sdk direct")
    _install_cc_sdk(cc_fake3)
    result = call_with_fallback(
        prompt="ping",
        task_type="strategic",
        agent_type="ceo",
    )
    assert never_responder.calls == 0, "kill-switch failed: claude_cli was called"
    assert cc_fake3.calls == 1
    assert result.provider == "cc_sdk"
    os.environ.pop("EOS_ROUTER_CLAUDE_CLI_ENABLED", None)

    _header("7. Hot-path imports remain clean")
    import importlib

    for mod in (
        "runtime.gateway",
        "control_plane.runtime.cognitive_loop",
        "runtime.model_router",
        "runtime.agent_runtime",
        "runtime.primitives",
    ):
        importlib.import_module(mod)
        print(f"  ok: {mod}")

    _header("ROUTER CLAUDE-CLI PRIMARY SMOKE TEST PASSED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
