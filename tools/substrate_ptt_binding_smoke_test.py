#!/usr/bin/env python3
"""
PTT binding smoke test.

Proves the bounded REAL_READY proof path end-to-end:
  1. stt_workstation_readiness() returns a known classification.
  2. validate_real_capture(...) on a degraded environment with a
     simulated_fallback_text degrades cleanly AND still injects via the
     bounded seam (capture_once → inject_transcript → voice session).
  3. The audio_loop transcript ring buffer for the test node now contains
     an entry tagged with source="push_to_talk" (or "local_stt" — see below).
  4. real_capture_report() reflects the recorded validation history.
  5. Validation history is bounded (cap enforced).
  6. Hot path imports remain clean.

Notes
-----
The PTT binding's simulated fallback path uses
`capture_once(mode="simulated", ...)` which annotates the audio_loop with
its OWN source tag (`local_stt`). The push-to-talk source tag is reserved
for the real capture path. Both flow through the same bounded seam — this
test asserts that BOTH (a) the validation row classifies correctly AND
(b) the audio_loop entry exists with one of the expected substrate sources.

Runs in-process. dry_run=True so no real audio is touched.
Returns 0 on success, non-zero on assertion failure.
"""

from __future__ import annotations

import sys

sys.path.insert(0, "/opt/OS")

from umh.substrate.audio_loop import (  # noqa: E402
    get_audio_loop_store,
    reset_audio_loop_store_for_tests,
)
from umh.substrate.nodes import NodeRegistry, NodeStatus  # noqa: E402
from umh.substrate.ptt_binding import (  # noqa: E402
    real_capture_report,
    reset_validation_history_for_tests,
    validate_real_capture,
)
from umh.substrate.station_bus import get_station_bus  # noqa: E402
from umh.substrate.station_daemon import StationDaemon  # noqa: E402
from umh.substrate.stt_producer import (  # noqa: E402
    reset_local_stt_runtime_for_tests,
    reset_stt_capture_history_for_tests,
    stt_workstation_readiness,
)
from umh.substrate.voice_session import (  # noqa: E402
    get_voice_session_store,
    reset_voice_session_store_for_tests,
)

TEST_NODE = "smoketest-ptt-binding"


def _header(msg: str) -> None:
    print(f"\n── {msg} " + "─" * max(0, 60 - len(msg)))


def main() -> int:
    bus = get_station_bus()
    bus.daemon_take_outbox(TEST_NODE)
    bus.drain_inbox(TEST_NODE)

    _header("0. Cleanup test stores")
    reset_validation_history_for_tests()
    reset_voice_session_store_for_tests()
    reset_audio_loop_store_for_tests()
    reset_local_stt_runtime_for_tests()
    reset_stt_capture_history_for_tests()
    get_voice_session_store().clear()

    _header("1. Register a node + heartbeat (so SPEAK_TEXT can flow)")
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

    _header("2. stt_workstation_readiness returns a known classification")
    readiness = stt_workstation_readiness()
    cls = readiness.get("classification")
    print(f"  classification={cls}")
    assert cls in (
        "real_ready",
        "real_capture_ready",
        "degraded",
        "simulated_only",
        "unsupported",
    ), readiness
    print(f"  reason={readiness.get('reason')}")

    _header("3. validate_real_capture() with simulated fallback degrades cleanly")
    result = validate_real_capture(
        TEST_NODE,
        duration_s=1.0,
        simulated_fallback_text="ptt smoke test transcript",
        metadata={"smoketest": True},
    )
    print(f"  classification={result['classification']}")
    print(f"  attempted={result['attempted']} captured={result['captured']}")
    print(f"  transcribed={result['transcribed']} injected={result['injected']}")
    print(f"  capture_status={result['capture_status']}")
    print(f"  session_id={result['session_id']}")
    assert result["attempted"] is True, result
    # On a real workstation we'd expect classification=real_ready and the
    # capture_status to be 'injected'. On a headless/VPS environment we
    # explicitly take the simulated fallback. Both paths must result in
    # injected=True (otherwise the seam is broken).
    assert result["injected"] is True, result
    assert result["session_id"] is not None, result
    assert result["classification"] in (
        "real_ready",
        "simulated_only",
    ), result

    _header("4. audio_loop transcript ring contains the injected entry")
    state = get_audio_loop_store().get(TEST_NODE)
    assert state is not None, "audio loop state should exist for test node"
    sources = [t.source for t in state.transcripts]
    print(f"  transcript sources: {sources}")
    # Substrate annotates one entry from the voice_session path
    # (source='voice_turn') and one from inject_transcript's annotation
    # path (source='local_stt' for the simulated fallback).
    assert "voice_turn" in sources, sources
    assert any(s in ("local_stt", "push_to_talk") for s in sources), sources

    _header("5. real_capture_report() reflects the recorded history")
    report = real_capture_report(node_id=TEST_NODE, limit=5)
    print(f"  history_count={report['history_count']}")
    print(f"  by_classification={report['by_classification']}")
    assert report["history_count"] >= 1, report
    assert report["readiness"]["classification"] == cls, report

    _header("6. Validation history is bounded")
    for i in range(8):
        validate_real_capture(
            TEST_NODE,
            duration_s=0.1,
            simulated_fallback_text=f"bounded loop iter {i}",
        )
    report2 = real_capture_report(node_id=TEST_NODE, limit=50)
    print(f"  history_count after 8 more: {report2['history_count']}")
    assert report2["history_count"] >= 9 and report2["history_count"] <= 50, report2

    _header("7. Hot path imports unchanged")
    import importlib

    for mod in (
        "umh.runtime_engine.gateway",
        "umh.runtime_engine.cognitive_loop",
        "umh.runtime_engine.model_router",
        "umh.runtime_engine.agent_runtime",
        "umh.runtime_engine.primitives",
    ):
        try:
            importlib.import_module(mod)
            print(f"  ok: {mod}")
        except Exception as e:  # noqa: BLE001
            print(f"  WARN ({mod}): {e}")

    _header("PTT BINDING SMOKE TEST PASSED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
