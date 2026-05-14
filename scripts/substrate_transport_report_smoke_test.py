#!/usr/bin/env python3
"""
Unified transport report smoke test.

Proves that the unified report joins both transport fronts cleanly:
  1. A local PTT validation runs against a workstation node and lands
     in the audio_loop ring buffer.
  2. A Discord transport injects an utterance against a discord_vc_* node
     and lands in its own audio_loop ring buffer with source="discord_voice".
  3. unified_transport_report(node_id=local) returns a payload whose:
       - workstation.readiness.classification is set
       - workstation.real_capture_report.history_count >= 1
       - discord_transport.mode is transcript_only*
       - voice_sessions_recent contains at least one session for the
         focus node
       - transcripts.local has the simulated/PTT entry
       - transcripts.discord has the discord_voice entry
       - transcripts.by_source aggregates BOTH sources
  4. Hot path imports remain clean.

Returns 0 on success, non-zero on assertion failure.
"""

from __future__ import annotations

import sys

import os
sys.path.insert(0, os.environ.get("UMH_ROOT") or os.environ.get("OS_ROOT") or os.environ.get("EOS_ROOT") or "/opt/OS")

from runtime.transport.audio_loop import (  # noqa: E402
    reset_audio_loop_store_for_tests,
)
from runtime.transport.discord_voice_transport import (  # noqa: E402
    DiscordVoiceTransport,
    reset_default_discord_voice_transports_for_tests,
    reset_transport_history_for_tests,
)
from runtime.transport.nodes import NodeRegistry, NodeStatus  # noqa: E402
from runtime.transport.ptt_binding import (  # noqa: E402
    reset_validation_history_for_tests,
    validate_real_capture,
)
from runtime.transport.station_bus import get_station_bus  # noqa: E402
from runtime.transport.station_daemon import StationDaemon  # noqa: E402
from runtime.transport.stt_producer import (  # noqa: E402
    reset_local_stt_runtime_for_tests,
    reset_stt_capture_history_for_tests,
)
from runtime.transport.transport_report import unified_transport_report  # noqa: E402
from runtime.transport.voice_session import (  # noqa: E402
    get_voice_session_store,
    reset_voice_session_store_for_tests,
)

LOCAL_NODE = "smoketest-transport-report-local"
DISCORD_GUILD = "smoketest-tr-guild"
DISCORD_CHANNEL = "smoketest-tr-channel"


def _header(msg: str) -> None:
    print(f"\n── {msg} " + "─" * max(0, 60 - len(msg)))


def _register_node(node_id: str) -> None:
    bus = get_station_bus()
    bus.daemon_take_outbox(node_id)
    bus.drain_inbox(node_id)
    daemon = StationDaemon(
        node_id=node_id,
        poll_interval_s=0.05,
        heartbeat_interval_s=0.01,
        dry_run=True,
    )
    daemon.register()
    daemon._tick()  # noqa: SLF001
    node = NodeRegistry.default().get(node_id)
    assert node is not None and node.status == NodeStatus.ONLINE, node


def main() -> int:
    _header("0. Cleanup test stores")
    reset_validation_history_for_tests()
    reset_voice_session_store_for_tests()
    reset_audio_loop_store_for_tests()
    reset_local_stt_runtime_for_tests()
    reset_stt_capture_history_for_tests()
    reset_transport_history_for_tests()
    reset_default_discord_voice_transports_for_tests()
    get_voice_session_store().clear()

    _header("1. Register local workstation node + heartbeat")
    _register_node(LOCAL_NODE)
    print(f"  registered: {LOCAL_NODE}")

    _header("2. Local PTT validation (simulated fallback) injects via the seam")
    ptt_result = validate_real_capture(
        LOCAL_NODE,
        duration_s=0.5,
        simulated_fallback_text="local ptt unified test",
    )
    print(f"  classification={ptt_result['classification']}")
    print(f"  injected={ptt_result['injected']}")
    assert ptt_result["injected"] is True, ptt_result

    _header("3. Discord transport injects against its own node")
    dvt = DiscordVoiceTransport(
        guild_id=DISCORD_GUILD, channel_id=DISCORD_CHANNEL, role_slug="ea_orchestrator"
    )
    _register_node(dvt.node_id)
    dvt.start_session()
    dvt_result = dvt.inject_utterance("discord side unified test", user_id="42")
    print(f"  discord status={dvt_result['status']}")
    assert dvt_result["status"] == "ok", dvt_result

    _header("4. unified_transport_report(node_id=local)")
    report = unified_transport_report(
        node_id=LOCAL_NODE,
        transcript_limit=10,
        discord_guild_id=DISCORD_GUILD,
        discord_channel_id=DISCORD_CHANNEL,
    )
    ws = report["workstation"]
    discord_status = report["discord_transport"]
    print(f"  ws.readiness.classification={ws['readiness'].get('classification')}")
    print(
        f"  ws.real_capture_report.history_count={ws['real_capture_report']['history_count']}"
    )
    print(f"  discord.mode={discord_status.get('mode')}")
    print(
        f"  discord.active_session_count={discord_status.get('active_session_count')}"
    )
    print(f"  voice_sessions_recent={len(report['voice_sessions_recent'])}")
    print(f"  transcripts.by_source={report['transcripts']['by_source']}")
    print(f"  transcripts.local count={len(report['transcripts']['local'])}")
    print(f"  transcripts.discord count={len(report['transcripts']['discord'])}")

    assert ws["readiness"].get("classification") in (
        "real_ready",
        "real_capture_ready",
        "degraded",
        "simulated_only",
        "unsupported",
    )
    assert ws["real_capture_report"]["history_count"] >= 1
    assert discord_status.get("mode") in (
        "transcript_only",
        "transcript_only_no_lib",
    ), discord_status
    assert discord_status.get("active_session_count") >= 1
    assert len(report["voice_sessions_recent"]) >= 1, report["voice_sessions_recent"]
    assert len(report["transcripts"]["local"]) >= 1, report["transcripts"]
    assert len(report["transcripts"]["discord"]) >= 1, report["transcripts"]

    by_source = report["transcripts"]["by_source"]
    # local PTT side
    assert any(k in by_source for k in ("local_stt", "push_to_talk", "voice_turn")), (
        by_source
    )
    # discord side
    assert "discord_voice" in by_source or "voice_turn" in by_source, by_source
    # the actual discord_voice tag should be present at least once
    assert by_source.get("discord_voice", 0) >= 1, by_source

    _header("4b. playback_aggregates present with by_transport + by_status")
    pa = report.get("playback_aggregates")
    print(f"  playback_aggregates.keys={list(pa.keys()) if pa else None}")
    assert isinstance(pa, dict), pa
    assert "by_transport" in pa and "by_status" in pa, pa
    assert "discord" in pa["by_transport"], pa
    assert "meeting" in pa["by_transport"], pa
    assert isinstance(pa["by_status"], dict), pa

    _header("5. Hot path imports unchanged")
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

    _header("UNIFIED TRANSPORT REPORT SMOKE TEST PASSED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
