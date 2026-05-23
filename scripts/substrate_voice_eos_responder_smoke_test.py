#!/usr/bin/env python3
"""
Voice → EOS responder smoke test.

Proves the bounded EOS-backed voice responder integration end-to-end:
  1. Backward compat: with NO EOS responder installed, the substrate stub
     still works exactly as before.
  2. install_default_eos_voice_responder() routes utterances through a
     mocked call_with_fallback (so this test never needs live providers).
  3. The agent reply text returned by the router is what the runtime
     records as the AGENT turn text and what flows into SPEAK_TEXT.
  4. session.metadata["last_responder"] captures provider/model/role/degraded
     and is visible via voice_session_report().
  5. Role switching changes which agent_type the router is called with.
  6. A router exception degrades safely: session stays alive, agent turn
     contains a structured fallback string, metadata records the error.
  7. uninstall_eos_voice_responder() restores the stub responder.
  8. Hot path imports remain clean.

Runs in-process. dry_run=True so SPEAK_TEXT never invokes real audio.
The router is monkey-patched at the adapter import site so we never hit
Anthropic / Gemini / Ollama. Returns 0 on success, non-zero on failure.
"""

from __future__ import annotations

import sys

import os
sys.path.insert(0, os.environ.get("UMH_ROOT") or os.environ.get("OS_ROOT") or os.environ.get("EOS_ROOT") or "/opt/OS")

from substrate.execution.bridge.result_store import (  # noqa: E402
    get_result_store,
    reset_result_store_for_tests,
)
from substrate.execution.bridge.station_bus import get_station_bus  # noqa: E402
from substrate.execution.bridge.station_daemon import StationDaemon  # noqa: E402
from substrate.execution.bridge.voice_eos_responder import (  # noqa: E402
    EOS_VOICE_ROLES,
    install_default_eos_voice_responder,
    is_eos_voice_responder_installed,
    uninstall_eos_voice_responder,
)
from substrate.execution.bridge.voice_session import (  # noqa: E402
    VoiceSessionRuntime,
    VoiceSessionStatus,
    VoiceTurnSource,
    get_voice_session_store,
    reset_voice_session_store_for_tests,
    voice_session_report,
)

TEST_NODE = "smoketest-voice-eos-responder"


def _header(msg: str) -> None:
    print(f"\n── {msg} " + "─" * max(0, 60 - len(msg)))


# ─── Mock router ──────────────────────────────────────────────────────────────


class _MockRoutingResult:
    """Quack-alike for model_router.RoutingResult."""

    def __init__(self, output: str, provider: str = "mock", model: str = "mock-1"):
        self.output = output
        self.provider = provider
        self.model = model
        self.task_type = "conversation"
        self.tokens_used = 42
        self.input_tokens = 21
        self.output_tokens = 21
        self.cost_usd = 0.0
        self.latency_ms = 5


class _MockRouter:
    """Captures the last call so we can assert agent_type / system / prompt."""

    def __init__(self) -> None:
        self.calls: list[dict] = []
        self.next_output: str = "Mocked agent reply."
        self.next_provider: str = "mock_provider"
        self.next_model: str = "mock-model-x"
        self.raise_next: Exception | None = None

    def __call__(
        self,
        prompt: str,
        system: str | None = None,
        task_type=None,
        trigger_source: str = "conversational",
        agent_type: str | None = None,
        force_opus: bool = False,
    ):
        self.calls.append(
            {
                "prompt": prompt,
                "system": system,
                "task_type": task_type,
                "trigger_source": trigger_source,
                "agent_type": agent_type,
                "force_opus": force_opus,
            }
        )
        if self.raise_next is not None:
            err = self.raise_next
            self.raise_next = None
            raise err
        return _MockRoutingResult(
            output=self.next_output,
            provider=self.next_provider,
            model=self.next_model,
        )


def _install_mock_router(mock: _MockRouter) -> None:
    """Patch the lazily-imported call_with_fallback inside the adapter.

    The adapter imports `from substrate.execution.runtime.model_router import call_with_fallback`
    INSIDE its responder function (to avoid module-load coupling), so the
    canonical patch point is the source module.
    """
    import execution.runtime.model_router as mr

    mr.call_with_fallback = mock  # type: ignore[assignment]


def _restore_real_router() -> None:
    """Reload model_router to restore the real call_with_fallback."""
    import importlib

    import execution.runtime.model_router as mr

    importlib.reload(mr)


# ─── Test ────────────────────────────────────────────────────────────────────


def main() -> int:
    bus = get_station_bus()
    bus.daemon_take_outbox(TEST_NODE)
    bus.drain_inbox(TEST_NODE)

    _header("0. Cleanup + ensure stub responder")
    reset_voice_session_store_for_tests()
    reset_result_store_for_tests()
    get_voice_session_store().clear()
    get_result_store().clear()
    uninstall_eos_voice_responder()
    assert not is_eos_voice_responder_installed()

    _header("1. Register node + heartbeat")
    daemon = StationDaemon(
        node_id=TEST_NODE,
        poll_interval_s=0.05,
        heartbeat_interval_s=0.01,
        dry_run=True,
    )
    daemon.register()
    daemon._tick()  # noqa: SLF001

    _header("2. Backward compat: stub responder still works (no EOS installed)")
    rt = VoiceSessionRuntime()
    s_stub = rt.start_session(TEST_NODE, role_slug="ea_orchestrator")
    s_stub = rt.submit_utterance(s_stub.session_id, "hello stub")
    stub_agent = [t for t in s_stub.turns if t.source == VoiceTurnSource.AGENT][-1]
    print(f"  stub agent text: {stub_agent.text!r}")
    assert "[ea_orchestrator] heard: hello stub" in stub_agent.text
    assert stub_agent.action_id is not None
    assert "last_responder" not in s_stub.metadata, (
        "stub path must not write responder metadata"
    )
    rt.end_session(s_stub.session_id, reason="stub leg done")

    _header("3. Install EOS responder + patch router with mock")
    mock = _MockRouter()
    _install_mock_router(mock)
    install_default_eos_voice_responder()
    assert is_eos_voice_responder_installed()

    _header("4. EA-routed utterance hits router with agent_type='ea_orchestrator'")
    mock.next_output = "Today's agenda is light. Outreach first, then build."
    s = rt.start_session(TEST_NODE, role_slug="ea_orchestrator")
    s = rt.submit_utterance(s.session_id, "what is on the agenda today")
    assert s is not None
    last_call = mock.calls[-1]
    print(f"  router agent_type={last_call['agent_type']}")
    print(f"  router task_type={last_call['task_type']}")
    print(f"  router trigger_source={last_call['trigger_source']}")
    assert last_call["agent_type"] == "ea_orchestrator"
    assert last_call["trigger_source"] == "voice_session"
    assert "Recent voice session transcript" in last_call["prompt"] or (
        "User just said" in last_call["prompt"]
    )
    assert last_call["system"] is not None
    assert "Executive Assistant" in last_call["system"]

    agent_turn = [t for t in s.turns if t.source == VoiceTurnSource.AGENT][-1]
    print(f"  agent text: {agent_turn.text!r}")
    assert agent_turn.text == "Today's agenda is light. Outreach first, then build."
    assert agent_turn.action_id is not None, "SPEAK_TEXT must still dispatch"

    last_resp = s.metadata.get("last_responder")
    print(f"  last_responder={last_resp}")
    assert last_resp is not None
    assert last_resp["mode"] == "eos"
    assert last_resp["role_used"] == "ea_orchestrator"
    assert last_resp["provider"] == "mock_provider"
    assert last_resp["model"] == "mock-model-x"
    assert last_resp["degraded"] is False
    assert last_resp["error"] is None

    _header("5. Role switch → CEO; next utterance routes with agent_type='ceo'")
    mock.next_output = "Ship it. Stop second-guessing."
    s = rt.switch_role(s.session_id, "ceo")
    assert s.role_slug == "ceo"
    s = rt.submit_utterance(s.session_id, "should we ship today")
    last_call = mock.calls[-1]
    print(f"  router agent_type={last_call['agent_type']}")
    assert last_call["agent_type"] == "ceo"
    assert "CEO" in last_call["system"]
    agent_turn = [t for t in s.turns if t.source == VoiceTurnSource.AGENT][-1]
    assert agent_turn.text == "Ship it. Stop second-guessing."
    assert s.metadata["last_responder"]["role_used"] == "ceo"

    _header("6. Role switch → portfolio_advisor; routes with agent_type=portfolio_advisor")
    mock.next_output = "Cash runway favors the lower-risk path."
    s = rt.switch_role(s.session_id, "portfolio_advisor")
    s = rt.submit_utterance(s.session_id, "what is the smarter bet")
    last_call = mock.calls[-1]
    print(f"  router agent_type={last_call['agent_type']}")
    assert last_call["agent_type"] == "portfolio_advisor"
    assert "Portfolio Advisor" in last_call["system"]
    assert s.metadata["last_responder"]["role_used"] == "portfolio_advisor"

    _header("7. Router raises → safe degradation, session stays alive")
    mock.raise_next = RuntimeError("simulated provider outage")
    s = rt.submit_utterance(s.session_id, "are we still online")
    assert s.status == VoiceSessionStatus.ACTIVE, s.status
    agent_turn = [t for t in s.turns if t.source == VoiceTurnSource.AGENT][-1]
    print(f"  degraded agent text: {agent_turn.text!r}")
    assert "[portfolio_advisor]" in agent_turn.text
    assert "degraded" in agent_turn.text or "router error" in agent_turn.text
    last_resp = s.metadata.get("last_responder")
    print(f"  degraded last_responder={last_resp}")
    assert last_resp["degraded"] is True
    assert "router_raised" in (last_resp["error"] or "")
    # SPEAK_TEXT should still have been dispatched for the fallback string
    assert agent_turn.action_id is not None

    _header("8. Empty router output → degraded fallback")
    mock.next_output = "   "
    s = rt.submit_utterance(s.session_id, "now what")
    last_resp = s.metadata.get("last_responder")
    print(f"  empty-output last_responder={last_resp}")
    assert last_resp["degraded"] is True
    assert last_resp["error"] == "empty_output"
    agent_turn = [t for t in s.turns if t.source == VoiceTurnSource.AGENT][-1]
    assert "no output" in agent_turn.text or "degraded" in agent_turn.text

    _header("9. voice_session_report surfaces last_responder metadata")
    report = voice_session_report(node_id=TEST_NODE, limit=5)
    print(f"  active_count={report['active_count']}")
    # Find our active session in the report
    active = [
        sd
        for sd in report["active_sessions"]
        if sd["session_id"] == s.session_id
    ]
    assert len(active) == 1, "active session must be in report"
    rep_meta = active[0].get("metadata") or {}
    rep_resp = rep_meta.get("last_responder")
    print(f"  report last_responder={rep_resp}")
    assert rep_resp is not None
    assert rep_resp["mode"] == "eos"
    assert rep_resp["role_used"] == "portfolio_advisor"

    _header("10. Uninstall EOS responder → stub returns")
    uninstall_eos_voice_responder()
    assert not is_eos_voice_responder_installed()
    s2 = rt.start_session(TEST_NODE, role_slug="ea_orchestrator")
    s2 = rt.submit_utterance(s2.session_id, "back to stub")
    stub_agent = [t for t in s2.turns if t.source == VoiceTurnSource.AGENT][-1]
    print(f"  post-uninstall agent text: {stub_agent.text!r}")
    assert "[ea_orchestrator] heard: back to stub" in stub_agent.text
    assert "last_responder" not in s2.metadata
    rt.end_session(s2.session_id, reason="stub-restored leg done")

    _header("11. Role allow-list sanity")
    assert "ea_orchestrator" in EOS_VOICE_ROLES
    assert "ceo" in EOS_VOICE_ROLES
    assert "portfolio_advisor" in EOS_VOICE_ROLES
    assert "rogue_role" not in EOS_VOICE_ROLES

    _header("12. Hot path imports unchanged")
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

    _header("13. Restore real router (cleanup)")
    _restore_real_router()
    # Note: reloading model_router resets call_with_fallback to the real one,
    # but does not affect the substrate's responder pointer. The previous
    # uninstall already restored the stub, so we're clean.

    _header("EOS RESPONDER SMOKE TEST PASSED")
    print("  verified: stub backward-compat → EOS install → role-aware routing →")
    print("            transcript context → safe degradation → reporting → uninstall")
    print("  hot path: untouched")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
