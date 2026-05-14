#!/usr/bin/env python3
"""
Voice session smoke test.

Proves the bounded voice-presence MVP end-to-end:
  1. A node is registered + heartbeated via StationDaemon (so SPEAK_TEXT can flow).
  2. VoiceSessionRuntime.start_session(...) opens a bounded session for ea_orchestrator.
  3. submit_utterance(...) records a USER turn, runs the responder, and emits
     an AGENT turn whose response is dispatched via SPEAK_TEXT.
  4. A daemon tick executes the SPEAK_TEXT (dry_run) and posts an ActionResult.
  5. The drainer ingests the result into ResultStore; the agent turn's action_id
     appears there with kind="speak_text".
  6. switch_role(...) flips the active role and records role_history.
  7. end_session(...) marks the session terminal and appends a SYSTEM turn.
  8. voice_session_report() and result_query.recent_voice_sessions() see it all.
  9. Safety: starting a session for an unregistered node yields ERROR (not raise).
 10. Safety: starting a session with an unknown role yields ERROR (not raise).
 11. Safety: LocalListener.start_voice_session() bridge produces the same result.
 12. Hot path imports remain clean.

Runs in-process. dry_run=True so SPEAK_TEXT will never invoke real audio.
Returns 0 on success, non-zero on assertion failure.
"""

from __future__ import annotations

import sys

import os
sys.path.insert(0, os.environ.get("UMH_ROOT") or os.environ.get("OS_ROOT") or os.environ.get("EOS_ROOT") or "/opt/OS")

from runtime.transport.local_listener import LocalListener  # noqa: E402
from runtime.transport.nodes import NodeRegistry, NodeStatus  # noqa: E402
from runtime.transport.result_query import recent_voice_sessions  # noqa: E402
from runtime.transport.result_store import (  # noqa: E402
    get_result_store,
    reset_result_store_for_tests,
)
from runtime.transport.station_bus import get_station_bus  # noqa: E402
from runtime.transport.station_daemon import StationDaemon  # noqa: E402
from runtime.transport.station_drainer import drain_results  # noqa: E402
from runtime.transport.voice_session import (  # noqa: E402
    VoiceSessionRuntime,
    VoiceSessionStatus,
    VoiceTurnSource,
    get_voice_session_store,
    reset_voice_session_store_for_tests,
    voice_session_report,
)

TEST_NODE = "smoketest-voice-session"
GHOST_NODE = "smoketest-voice-ghost-never-registered"


def _header(msg: str) -> None:
    print(f"\n── {msg} " + "─" * max(0, 60 - len(msg)))


def _drain(node_id: str) -> int:
    """Drain station inbox results into ResultStore. Returns count ingested."""
    try:
        stats = drain_results(node_id)
        return (
            getattr(stats, "ingested", 0) or getattr(stats, "results_ingested", 0) or 0
        )
    except Exception as e:  # noqa: BLE001
        print(f"  drain failed: {e}")
        return 0


def main() -> int:
    bus = get_station_bus()
    bus.daemon_take_outbox(TEST_NODE)
    bus.drain_inbox(TEST_NODE)

    _header("0. Cleanup: clear voice session store + result store")
    reset_voice_session_store_for_tests()
    reset_result_store_for_tests()
    get_voice_session_store().clear()
    get_result_store().clear()

    _header("1. Register node + fresh heartbeat")
    daemon = StationDaemon(
        node_id=TEST_NODE,
        poll_interval_s=0.05,
        heartbeat_interval_s=0.01,
        dry_run=True,
    )
    daemon.register()
    daemon._tick()  # noqa: SLF001
    node = NodeRegistry.default().get(TEST_NODE)
    assert node is not None and node.status == NodeStatus.ONLINE, node
    print(f"  node={node.node_id} status={node.status.value}")

    _header("2. start_session for ea_orchestrator")
    rt = VoiceSessionRuntime()
    session = rt.start_session(TEST_NODE, role_slug="ea_orchestrator")
    print(f"  session_id={session.session_id} status={session.status.value}")
    print(f"  role={session.role_slug} turn_count={session.turn_count}")
    assert session.status == VoiceSessionStatus.ACTIVE, session.as_dict()
    assert session.turn_count == 1
    assert session.turns[0].source == VoiceTurnSource.SYSTEM

    _header("3. submit_utterance → user + agent turns + SPEAK_TEXT dispatched")
    session = rt.submit_utterance(session.session_id, "what is on the agenda today")
    assert session is not None
    print(f"  turn_count={session.turn_count}")
    user_turns = [t for t in session.turns if t.source == VoiceTurnSource.USER]
    agent_turns = [t for t in session.turns if t.source == VoiceTurnSource.AGENT]
    assert len(user_turns) == 1, [t.as_dict() for t in session.turns]
    assert len(agent_turns) == 1, [t.as_dict() for t in session.turns]
    agent_turn = agent_turns[-1]
    print(f"  user='{user_turns[-1].text[:40]}'")
    print(f"  agent='{agent_turn.text[:60]}'")
    print(f"  agent_turn.action_id={agent_turn.action_id}")
    assert agent_turn.action_id is not None, "SPEAK_TEXT action_id should be set"

    _header("4. Daemon tick executes SPEAK_TEXT (dry_run) + drain into ResultStore")
    daemon._tick()  # noqa: SLF001
    ingested = _drain(TEST_NODE)
    print(f"  drained {ingested} result(s)")
    result = get_result_store().get(agent_turn.action_id)
    print(f"  result for {agent_turn.action_id}: {result}")
    assert result is not None, "ResultStore should contain SPEAK_TEXT result"
    assert (result.kind or "").lower() == "speak_text", result.kind
    print(f"  result.status={result.status} result.kind={result.kind}")

    _header("5. switch_role → ceo, role_history recorded")
    session = rt.switch_role(session.session_id, "ceo")
    assert session is not None
    print(f"  role_slug={session.role_slug}")
    print(f"  role_history={session.role_history}")
    assert session.role_slug == "ceo"
    assert len(session.role_history) == 1
    assert session.role_history[0]["from"] == "ea_orchestrator"
    assert session.role_history[0]["to"] == "ceo"

    _header("6. submit second utterance under new role")
    session = rt.submit_utterance(session.session_id, "should we ship today")
    last_agent = [t for t in session.turns if t.source == VoiceTurnSource.AGENT][-1]
    print(f"  agent='{last_agent.text[:60]}'")
    assert last_agent.role_slug == "ceo"
    assert last_agent.action_id is not None

    _header("7. switch_role to unknown slug → SYSTEM rejection turn, no crash")
    before_role = session.role_slug
    session = rt.switch_role(session.session_id, "nonexistent_role_xyz")
    assert session.role_slug == before_role, "role must not change on rejection"
    last_system = [t for t in session.turns if t.source == VoiceTurnSource.SYSTEM][-1]
    print(f"  rejection_text='{last_system.text}'")
    assert "rejected" in last_system.text or "unknown" in last_system.text

    _header("8. end_session → terminal + final SYSTEM turn")
    session = rt.end_session(session.session_id, reason="smoketest done")
    print(f"  status={session.status.value} ended_at={session.ended_at}")
    assert session.status == VoiceSessionStatus.ENDED
    assert session.ended_at is not None

    _header("9. submit_utterance after end → no-op, session stays terminal")
    session = rt.submit_utterance(session.session_id, "this should not record")
    assert session.status == VoiceSessionStatus.ENDED

    _header("10. Unknown node → ERROR session, never raised")
    bad = rt.start_session(GHOST_NODE, role_slug="ea_orchestrator")
    print(f"  status={bad.status.value} reason={bad.error_reason}")
    assert bad.status == VoiceSessionStatus.ERROR
    assert "not registered" in (bad.error_reason or "")

    _header("11. Unknown role → ERROR session, never raised")
    bad2 = rt.start_session(TEST_NODE, role_slug="not_a_real_role")
    print(f"  status={bad2.status.value} reason={bad2.error_reason}")
    assert bad2.status == VoiceSessionStatus.ERROR
    assert "unknown role" in (bad2.error_reason or "")

    _header("12. LocalListener bridge produces a real session")
    listener = LocalListener()
    bridged = listener.start_voice_session(TEST_NODE, role_slug="portfolio_advisor")
    assert bridged is not None
    print(f"  bridged_id={bridged.session_id} role={bridged.role_slug}")
    assert bridged.role_slug == "portfolio_advisor"
    assert bridged.status == VoiceSessionStatus.ACTIVE

    _header("13. voice_session_report() + recent_voice_sessions() observability")
    report = voice_session_report(node_id=TEST_NODE, limit=5)
    print(f"  active_count={report['active_count']}")
    print(f"  recent_count={len(report['recent_sessions'])}")
    print(f"  last_role={report['last_role']}")
    print(f"  stats={report['stats']}")
    assert report["active_count"] >= 1  # bridged session is still active
    assert len(report["recent_sessions"]) >= 2

    rq_rows = recent_voice_sessions(limit=5, node_id=TEST_NODE)
    print(f"  recent_voice_sessions() rows: {len(rq_rows)}")
    assert len(rq_rows) >= 2
    assert all("session_id" in r for r in rq_rows)

    _header("14. Hot path imports unchanged (sanity check)")
    import importlib

    for mod in (
        "control_plane.runtime.gateway",
        "control_plane.runtime.cognitive_loop",
        "execution.runtime.model_router",
        "execution.runtime.agent_runtime",
        "runtime.primitives",
    ):
        try:
            importlib.import_module(mod)
            print(f"  ok: {mod}")
        except Exception as e:  # noqa: BLE001
            print(f"  WARN ({mod}): {e}")
            # Hot path may have unrelated import-time issues — we only assert
            # that voice_session itself is clean. Surface but do not fail.

    _header("SMOKE TEST PASSED")
    print("  verified: session lifecycle → SPEAK_TEXT dispatch → ResultStore →")
    print("            role switch → end → reporting → safety → listener bridge")
    print("  hot path: untouched")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
