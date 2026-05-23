#!/usr/bin/env python3
"""
Smoke test for Execution Linkage Layer v1.

Validates additive, bounded, deterministic projection of intelligence
state into structured ActionableItems with execution readiness
classification. No hot-path changes; no task execution.

Checks:
  1. Unresolved commitments project into actionable items
  2. Stale open loops project into actionable items
  3. Missing owner     → blocked_missing_owner
  4. Ambiguous wording → blocked_ambiguous
  5. Low owner confidence → blocked_ambiguous
  6. Very short text   → blocked_low_context
  7. Valid owned clear item → ready
  8. MAX_ACTIONABLE_ITEMS cap enforced
  9. intelligence_report_block exposes new fields (success + fallback)
 10. Malformed input does not raise
 11. Existing intelligence fields still present
 12. Output is JSON-serializable
 13. Hot-path files remain clean (grep guard)

Prints:
    EXECUTION LINKAGE SMOKE TEST PASSED
"""

from __future__ import annotations

import json
import subprocess
import sys
import time

import os
sys.path.insert(0, os.environ.get("UMH_ROOT") or os.environ.get("OS_ROOT") or os.environ.get("EOS_ROOT") or "/opt/OS")
_ROOT = os.environ.get("UMH_ROOT") or os.environ.get("OS_ROOT") or os.environ.get("EOS_ROOT") or "/opt/OS"

from substrate.execution.transport import meeting_intelligence as mi  # noqa: E402

HOT_PATH_FILES = (
    "control_plane/runtime/gateway.py",
    "control_plane/runtime/cognitive_loop.py",
    "execution/runtime/model_router.py",
    "execution/runtime/agent_runtime.py",
    "runtime/primitives.py",
)


def _fresh_summary() -> mi.MeetingSummary:
    mi.reset_meeting_summary_store_for_tests()
    return mi.MeetingSummary(node_id="node-exec", meeting_id="meet-exec")


def _commitment(text: str, owner, conf: str = "high", resolved: bool = False) -> dict:
    return {
        "text": text,
        "owner": owner,
        "created_at": time.time(),
        "resolved": resolved,
        "resolved_at": None,
        "source": "meeting",
        "owner_confidence": conf,
    }


def test_commitments_and_open_loops_project() -> None:
    s = _fresh_summary()
    s.priority_level = "medium"
    s.commitments = [
        _commitment("I will send the draft proposal to Sarah tomorrow", "antony"),
        _commitment("circle back on the pricing", None, conf="low"),
    ]
    s.open_loops = ["finalize the launch checklist for monday"]
    # Force stale open loop window
    s.open_loops_since_ts = time.time() - (mi.STALE_OPEN_LOOP_SECONDS + 10)

    items = mi.project_actionable_items(s)
    kinds = {it.kind for it in items}
    assert "commitment" in kinds, f"expected commitment kind, got {kinds}"
    assert "open_loop" in kinds, f"expected open_loop kind, got {kinds}"
    assert len(items) >= 3, f"expected >=3 projections, got {len(items)}"


def test_readiness_states() -> None:
    # missing owner
    i1 = mi.ActionableItem(
        text="send the updated pricing deck to the partner", kind="commitment"
    )
    mi.classify_execution_readiness(i1)
    assert i1.readiness_state == "blocked_missing_owner", i1.readiness_state

    # ambiguous wording
    i2 = mi.ActionableItem(
        text="maybe we should figure out the pricing at some point",
        kind="commitment",
        owner="antony",
        owner_confidence="high",
    )
    mi.classify_execution_readiness(i2)
    assert i2.readiness_state == "blocked_ambiguous", i2.readiness_state

    # low owner confidence
    i3 = mi.ActionableItem(
        text="draft the partnership one-pager this week",
        kind="commitment",
        owner="antony",
        owner_confidence="low",
    )
    mi.classify_execution_readiness(i3)
    assert i3.readiness_state == "blocked_ambiguous", i3.readiness_state

    # low context
    i4 = mi.ActionableItem(text="do it", kind="commitment", owner="antony")
    mi.classify_execution_readiness(i4)
    assert i4.readiness_state == "blocked_low_context", i4.readiness_state

    # ready
    i5 = mi.ActionableItem(
        text="send the signed contract to legal by friday",
        kind="commitment",
        owner="antony",
        owner_confidence="high",
    )
    mi.classify_execution_readiness(i5)
    assert i5.readiness_state == "ready", i5.readiness_state
    assert i5.execution_ready is True


def test_cap_enforced() -> None:
    s = _fresh_summary()
    s.commitments = [
        _commitment(f"send artifact number {n} to the team tomorrow", "antony")
        for n in range(25)
    ]
    items = mi.project_actionable_items(s)
    assert len(items) <= mi.MAX_ACTIONABLE_ITEMS, len(items)


def test_report_block_has_linkage_fields() -> None:
    mi.reset_meeting_summary_store_for_tests()
    store = mi.get_meeting_summary_store()
    s = mi.MeetingSummary(node_id="node-exec", meeting_id="meet-exec")
    s.priority_level = "high"
    s.commitments = [
        _commitment("send the signed contract to legal by friday", "antony"),
        _commitment("circle back", None, conf="low"),
    ]
    store.put(s)

    block = mi.intelligence_report_block(node_id="node-exec", meeting_id="meet-exec")
    required = (
        "actionable_items_count",
        "actionable_items_ready_count",
        "actionable_items_blocked_count",
        "actionable_items",
        "execution_readiness_summary",
        "top_actionable_owner",
        "highest_priority_actionable",
    )
    for key in required:
        assert key in block, f"missing key in report block: {key}"
    assert block["actionable_items_count"] >= 2
    summary = block["execution_readiness_summary"]
    for k in (
        "ready",
        "blocked_missing_owner",
        "blocked_ambiguous",
        "blocked_low_context",
    ):
        assert k in summary, k
    # Existing intelligence fields still present
    for legacy in (
        "commitments_count",
        "unresolved_commitments_count",
        "ownership_distribution",
        "scoring",
    ):
        assert legacy in block, f"legacy field missing: {legacy}"
    # JSON-serializable
    json.dumps(block, default=str)


def test_report_block_fallback_has_linkage_fields() -> None:
    # Nonexistent meeting → success path with no live summary → still
    # exposes linkage fields with zeroed values.
    block = mi.intelligence_report_block(node_id="nope", meeting_id="nope")
    assert block["actionable_items_count"] == 0
    assert block["actionable_items"] == []
    assert block["execution_readiness_summary"]["ready"] == 0


def test_malformed_input_safe() -> None:
    # project on None
    assert mi.project_actionable_items(None) == []  # type: ignore[arg-type]
    # classify on degenerate item
    bad = mi.ActionableItem(text="", kind="commitment")
    mi.classify_execution_readiness(bad)
    assert bad.readiness_state == "blocked_low_context"
    # linkage block on None
    b = mi.execution_linkage_block(None)  # type: ignore[arg-type]
    assert b["actionable_items_count"] == 0


def test_hot_path_clean() -> None:
    for path in HOT_PATH_FILES:
        r = subprocess.run(
            [
                "grep",
                "-n",
                "ActionableItem\\|execution_linkage_block\\|project_actionable_items",
                f"{_ROOT}/{path}",
            ],
            capture_output=True,
            text=True,
        )
        assert r.returncode != 0, (
            f"hot-path {path} must not reference linkage layer:\n{r.stdout}"
        )


def main() -> int:
    test_commitments_and_open_loops_project()
    test_readiness_states()
    test_cap_enforced()
    test_report_block_has_linkage_fields()
    test_report_block_fallback_has_linkage_fields()
    test_malformed_input_safe()
    test_hot_path_clean()
    print("EXECUTION LINKAGE SMOKE TEST PASSED")
    return 0


if __name__ == "__main__":
    sys.exit(main())
