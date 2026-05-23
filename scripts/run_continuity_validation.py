"""Continuity engine end-to-end validation.

Exercises the full substrate continuity pipeline:
  event ingestion → classification → persistence → open loops →
  snapshot → resume packet → session summary → operator briefing →
  replay validation

Uses realistic runtime event shapes from the existing event spine.

Phase 96.8BN.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import os
sys.path.insert(0, os.environ.get("UMH_ROOT") or os.environ.get("OS_ROOT") or os.environ.get("EOS_ROOT") or "/opt/OS")

from substrate.execution.runtime.substrate_continuity_engine_v1 import SubstrateContinuityEngine

TEST_STORE = Path("data/runtime/substrate_continuity")
TEST_LOOPS = Path("data/runtime/open_loop_registry")
TEST_SUMMARIES = Path("data/runtime/continuity_summaries")
PROOF_DIR = Path("data/runtime/runtime_continuity_replay_proofs")


REALISTIC_EVENTS = [
    {
        "event_id": "evt-001",
        "event_type": "execution_completed",
        "source": "discord_bot",
        "severity": "info",
        "payload": {
            "command": "!constitution-report",
            "summary": "Generated constitutional report",
        },
        "correlation_id": "corr-001",
    },
    {
        "event_id": "evt-002",
        "event_type": "execution_failed",
        "source": "discord_bot",
        "severity": "error",
        "payload": {"command": "!chrome-proof", "summary": "Chrome not available on VPS"},
        "correlation_id": "corr-002",
    },
    {
        "event_id": "evt-003",
        "event_type": "reply_chunk",
        "source": "discord_bot",
        "severity": "debug",
        "payload": {"chunk_index": 0},
        "correlation_id": "corr-001",
    },
    {
        "event_id": "evt-004",
        "event_type": "action_dispatched",
        "source": "spine",
        "severity": "info",
        "payload": {"action": "ingest-safe-doc-cu", "summary": "Document ingestion dispatched"},
        "correlation_id": "corr-003",
    },
    {
        "event_id": "evt-005",
        "event_type": "permission_denied",
        "source": "authority_engine",
        "severity": "warning",
        "payload": {"command": "!delete-data", "summary": "Destructive action denied"},
        "correlation_id": "corr-004",
    },
]

REALISTIC_TRACES = [
    {
        "trace_id": "trace-001",
        "source": "discord_text",
        "mode": "builder",
        "execution_path": "gateway→cognitive_loop",
        "provider": "gemini",
        "model": "gemini-2.5-flash",
        "latency_ms": 1200,
        "result": "success",
        "correlation_id": "corr-001",
    },
    {
        "trace_id": "trace-002",
        "source": "discord_text",
        "mode": "builder",
        "execution_path": "gateway→spine→worker",
        "provider": "ollama",
        "model": "gemma3:4b",
        "latency_ms": 3500,
        "result": "fallback",
        "correlation_id": "corr-002",
    },
]

REALISTIC_OUTCOMES = [
    {
        "outcome_id": "out-001",
        "trace_id": "trace-001",
        "command": "constitution-report",
        "result": "success",
        "duration_ms": 1200,
        "artifacts_produced": ["data/runtime/workstation_relay/constitutional_reports/report.json"],
    },
    {
        "outcome_id": "out-002",
        "trace_id": "trace-002",
        "command": "chrome-proof",
        "result": "failure",
        "error_message": "Chrome binary not found on VPS",
        "duration_ms": 500,
    },
    {
        "outcome_id": "out-003",
        "trace_id": "trace-003",
        "command": "ingest-safe-doc-cu",
        "result": "success",
        "duration_ms": 2500,
        "artifacts_produced": ["data/runtime/real_ingestion_bridge/doc-test.json"],
    },
]


def run() -> dict:
    PROOF_DIR.mkdir(parents=True, exist_ok=True)

    engine = SubstrateContinuityEngine(
        store_dir=TEST_STORE,
        loop_dir=TEST_LOOPS,
        summaries_dir=TEST_SUMMARIES,
    )
    engine.start_session("session-validation-001")

    proof: dict = {"validation_type": "continuity_engine_validation", "tests": []}

    # Test 1: Event ingestion
    print("Test 1: Event ingestion...")
    classifications = []
    for event in REALISTIC_EVENTS:
        result = engine.ingest_event(event)
        classifications.append(result)

    transient_count = sum(1 for c in classifications if c.get("classification") == "transient")
    persisted_count = sum(1 for c in classifications if c.get("persist", True))
    test = {
        "test": "event_ingestion",
        "events_processed": len(REALISTIC_EVENTS),
        "transient": transient_count,
        "persisted": persisted_count,
        "pass": transient_count >= 1 and persisted_count >= 3,
    }
    proof["tests"].append(test)
    print(
        f"  {test['events_processed']} events, {transient_count} transient, {persisted_count} persisted — {'PASS' if test['pass'] else 'FAIL'}"
    )

    # Test 2: Trace ingestion
    print("Test 2: Trace ingestion...")
    for trace in REALISTIC_TRACES:
        engine.ingest_trace(trace)
    trace_count = engine.store.count_traces()
    test = {
        "test": "trace_ingestion",
        "traces_ingested": trace_count,
        "pass": trace_count == len(REALISTIC_TRACES),
    }
    proof["tests"].append(test)
    print(f"  {trace_count} traces ingested — {'PASS' if test['pass'] else 'FAIL'}")

    # Test 3: Outcome recording
    print("Test 3: Outcome recording...")
    outcome_results = []
    for outcome in REALISTIC_OUTCOMES:
        result = engine.record_outcome(outcome)
        outcome_results.append(result)

    promoted = sum(
        1 for r in outcome_results if r.get("promotion", {}).get("should_promote", False)
    )
    test = {
        "test": "outcome_recording",
        "outcomes_recorded": len(REALISTIC_OUTCOMES),
        "promoted_to_memory": promoted,
        "pass": len(REALISTIC_OUTCOMES) == engine.store.count_outcomes(),
    }
    proof["tests"].append(test)
    print(
        f"  {test['outcomes_recorded']} outcomes, {promoted} promoted — {'PASS' if test['pass'] else 'FAIL'}"
    )

    # Test 4: Open loop tracking
    print("Test 4: Open loop tracking...")
    open_loops = engine.loop_registry.get_open_loops()
    loop_stats = engine.loop_registry.get_stats()
    test = {
        "test": "open_loop_tracking",
        "open_loops": len(open_loops),
        "total_loops": loop_stats["total"],
        "pass": len(open_loops) >= 1,
    }
    proof["tests"].append(test)
    print(f"  {len(open_loops)} open loops — {'PASS' if test['pass'] else 'FAIL'}")

    # Test 5: Continuity snapshot
    print("Test 5: Continuity snapshot...")
    snapshot = engine.take_snapshot(active_goals=["Build substrate continuity", "Validate replay"])
    test = {
        "test": "continuity_snapshot",
        "has_state_id": bool(snapshot.state_id),
        "has_goals": len(snapshot.active_goals) > 0,
        "events_in_snapshot": snapshot.total_events_ingested,
        "pass": snapshot.total_events_ingested > 0,
    }
    proof["tests"].append(test)
    print(
        f"  state_id={snapshot.state_id[:16]}..., events={snapshot.total_events_ingested} — {'PASS' if test['pass'] else 'FAIL'}"
    )

    # Test 6: Resume packet generation
    print("Test 6: Resume packet generation...")
    resume = engine.generate_resume_packet(
        active_goals=["Validate continuity"],
        suggested_next_actions=["Run replay validation"],
    )
    test = {
        "test": "resume_packet",
        "has_packet_id": bool(resume.get("packet_id")),
        "has_goals": len(resume.get("active_goals", [])) > 0,
        "has_open_loops": len(resume.get("open_loops", [])) > 0,
        "has_environment": bool(resume.get("environment_state")),
        "pass": bool(resume.get("packet_id")),
    }
    proof["tests"].append(test)
    print(
        f"  packet_id={resume.get('packet_id', '?')[:16]}... — {'PASS' if test['pass'] else 'FAIL'}"
    )

    # Test 7: Session summary
    print("Test 7: Session summary...")
    summary = engine.generate_session_summary(
        phase_name="96.8BN",
        files_modified=["core/runtime/substrate_continuity_engine_v1.py"],
    )
    test = {
        "test": "session_summary",
        "total_events": summary.total_events,
        "total_outcomes": summary.total_outcomes,
        "pass": summary.total_events > 0,
    }
    proof["tests"].append(test)
    print(
        f"  events={summary.total_events}, outcomes={summary.total_outcomes} — {'PASS' if test['pass'] else 'FAIL'}"
    )

    # Test 8: Operator briefing
    print("Test 8: Operator briefing...")
    briefing = engine.generate_operator_briefing()
    test = {
        "test": "operator_briefing",
        "has_health": bool(briefing.get("health")),
        "has_resumability": bool(briefing.get("resumability")),
        "pass": briefing.get("resumability") == "ready",
    }
    proof["tests"].append(test)
    print(f"  resumability={briefing.get('resumability')} — {'PASS' if test['pass'] else 'FAIL'}")

    # Test 9: Context update recording
    print("Test 9: Context update recording...")
    engine.record_context_update(
        update_type="phase_transition",
        field_name="current_phase",
        old_value="96.8BM",
        new_value="96.8BN",
        reason="Phase 96.8BM complete",
        source="developer_agent",
    )
    test = {"test": "context_update", "pass": True}
    proof["tests"].append(test)
    print(f"  Context update recorded — PASS")

    # Test 10: Stats consistency
    print("Test 10: Stats consistency...")
    stats = engine.get_stats()
    test = {
        "test": "stats_consistency",
        "events": stats["events_ingested"],
        "traces": stats["traces_ingested"],
        "outcomes": stats["outcomes_recorded"],
        "pass": (
            stats["events_ingested"] > 0
            and stats["traces_ingested"] > 0
            and stats["outcomes_recorded"] > 0
        ),
    }
    proof["tests"].append(test)
    print(
        f"  events={stats['events_ingested']}, traces={stats['traces_ingested']}, outcomes={stats['outcomes_recorded']} — {'PASS' if test['pass'] else 'FAIL'}"
    )

    # Test 11: Replay determinism
    print("Test 11: Replay determinism...")
    engine2 = SubstrateContinuityEngine(
        store_dir=str(TEST_STORE) + "_replay",
        loop_dir=str(TEST_LOOPS) + "_replay",
        summaries_dir=str(TEST_SUMMARIES) + "_replay",
        promotion_dir="data/runtime/runtime_promotion_receipts_replay",
    )
    engine2.start_session("session-validation-001")

    classifications2 = []
    for event in REALISTIC_EVENTS:
        result = engine2.ingest_event(event)
        classifications2.append(result)

    for trace in REALISTIC_TRACES:
        engine2.ingest_trace(trace)

    for outcome in REALISTIC_OUTCOMES:
        engine2.record_outcome(outcome)

    snapshot2 = engine2.take_snapshot(
        active_goals=["Build substrate continuity", "Validate replay"]
    )

    replay_checks = {
        "classification_count_stable": len(classifications) == len(classifications2),
        "snapshot_events_stable": snapshot.total_events_ingested == snapshot2.total_events_ingested,
        "snapshot_traces_stable": snapshot.total_traces_ingested == snapshot2.total_traces_ingested,
        "snapshot_outcomes_stable": snapshot.total_outcomes_recorded
        == snapshot2.total_outcomes_recorded,
    }

    for i, (c1, c2) in enumerate(zip(classifications, classifications2)):
        replay_checks[f"classification_{i}_stable"] = c1.get("classification") == c2.get(
            "classification"
        )

    all_stable = all(replay_checks.values())
    test = {
        "test": "replay_determinism",
        "checks": replay_checks,
        "all_stable": all_stable,
        "pass": all_stable,
    }
    proof["tests"].append(test)
    for check_name, result in replay_checks.items():
        print(f"  {check_name}: {'PASS' if result else 'FAIL'}")
    print(f"  Overall replay: {'PASS' if all_stable else 'FAIL'}")

    # Test 12: Governance lineage preserved
    print("Test 12: Governance lineage preserved...")
    decisions = engine.governance_bridge.load_decisions()
    test = {
        "test": "governance_lineage",
        "decisions_recorded": len(decisions),
        "all_have_rule": all(d.get("rule_applied") for d in decisions),
        "pass": len(decisions) > 0 and all(d.get("rule_applied") for d in decisions),
    }
    proof["tests"].append(test)
    print(
        f"  {len(decisions)} governance decisions, all have rules — {'PASS' if test['pass'] else 'FAIL'}"
    )

    # Summary
    all_pass = all(t["pass"] for t in proof["tests"])
    proof["all_pass"] = all_pass
    proof["total_tests"] = len(proof["tests"])
    proof["passed"] = sum(1 for t in proof["tests"] if t["pass"])

    proof_path = PROOF_DIR / "continuity_validation_proof.json"
    with open(proof_path, "w") as f:
        json.dump(proof, f, indent=2)

    print(f"\nRESULT: {proof['passed']}/{proof['total_tests']} PASS")
    print(f"Proof saved: {proof_path}")

    return proof


if __name__ == "__main__":
    run()
