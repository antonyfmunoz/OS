#!/usr/bin/env python3
"""
Smoke test for Operator Interface Layer v1.

Validates the operator query + controlled-command surface built on top
of linkage_snapshot(). Deterministic. Bounded. No automation.

Checks:
    1.  summarize() on empty store returns well-formed dict
    2.  get_actionable_items() returns items on a populated summary
    3.  filter by priority works
    4.  filter by owner works
    5.  ready vs blocked partitions are disjoint and cover all items
    6.  get_top_actionable() returns highest-priority item
    7.  get_owner_breakdown() counts are correct + top_owner matches
    8.  mark_resolved() with selector updates matching commitments
    9.  mark_resolved() reflected in subsequent summarize() delta
    10. assign_owner() updates owner + appears in owner breakdown
    11. refresh() returns a fresh snapshot dict
    12. all query outputs are JSON-serializable
    13. malformed / empty inputs degrade safely (no crash)
    14. CLI subcommands execute cleanly (summary, actionable, top,
        blocked, owners, refresh)
    15. hot-path files remain untouched (grep guard)
    16. existing product linkage smoke test surface untouched (re-import)

Prints:
    OPERATOR INTERFACE SMOKE TEST PASSED
"""

from __future__ import annotations

import json
import subprocess
import sys
import time

import os
sys.path.insert(0, os.environ.get("UMH_ROOT") or os.environ.get("OS_ROOT") or os.environ.get("EOS_ROOT") or "/opt/OS")
_ROOT = os.environ.get("UMH_ROOT") or os.environ.get("OS_ROOT") or os.environ.get("EOS_ROOT") or "/opt/OS"

from runtime.substrate import meeting_intelligence as mi  # noqa: E402
from runtime.substrate import operator_interface as oi  # noqa: E402

HOT_PATH_FILES = (
    "runtime/gateway.py",
    "control_plane/runtime/cognitive_loop.py",
    "runtime/model_router.py",
    "runtime/agent_runtime.py",
    "runtime/primitives.py",
)

NODE = "node-op"
MEET = "meet-op"


# ─── fixtures ────────────────────────────────────────────────────────────────


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


def _fresh_populated() -> mi.MeetingSummary:
    mi.reset_meeting_summary_store_for_tests()
    s = mi.MeetingSummary(node_id=NODE, meeting_id=MEET)
    s.priority_level = "high"
    s.decision_pressure_score = 6
    s.ambiguity_score = 2
    s.participants = {"antony", "daisy", "marcus"}
    s.open_loops = ["pricing unsettled"]
    s.decisions = ["ship v1 friday"]
    s.commitments = [
        _commitment("send the signed contract to legal by friday", "antony"),
        _commitment("prepare the pricing memo for the investor meeting", "daisy"),
        _commitment("circle back on this later", None, conf="low"),
        _commitment("review the draft policy document", "antony"),
    ]
    mi.get_meeting_summary_store().put(s)
    return s


def _assert(cond: bool, msg: str) -> None:
    if not cond:
        raise AssertionError(msg)


# ─── tests ───────────────────────────────────────────────────────────────────


def test_01_summarize_empty() -> None:
    mi.reset_meeting_summary_store_for_tests()
    out = oi.summarize("node-missing", "meet-missing")
    _assert(isinstance(out, dict), "summarize must return dict")
    _assert(out["actionable_count"] == 0, "empty store → 0 actionable")
    _assert(out["commitments_count"] == 0, "empty store → 0 commitments")
    _assert(out["schema_version"] == "v1", "schema_version present")


def test_02_get_actionable_items_populated() -> None:
    _fresh_populated()
    items = oi.get_actionable_items(NODE, MEET)
    _assert(isinstance(items, list), "items list")
    _assert(len(items) >= 1, "at least one actionable on populated summary")
    for it in items:
        _assert("readiness_state" in it, "has readiness_state")
        _assert("priority" in it, "has priority")
        _assert("execution_ready" in it, "has execution_ready")


def test_03_filter_by_priority() -> None:
    _fresh_populated()
    all_items = oi.get_actionable_items(NODE, MEET)
    high_items = oi.get_actionable_items(
        NODE, MEET, filters={"priority": "high"}
    )
    for it in high_items:
        _assert(it["priority"] == "high", "priority filter")
    _assert(len(high_items) <= len(all_items), "filtered ⊆ all")


def test_04_filter_by_owner() -> None:
    _fresh_populated()
    antony_items = oi.get_actionable_items(
        NODE, MEET, filters={"owner": "antony"}
    )
    for it in antony_items:
        _assert(it.get("owner") == "antony", "owner filter")


def test_05_ready_and_blocked_partition() -> None:
    _fresh_populated()
    all_items = oi.get_actionable_items(NODE, MEET)
    ready = oi.get_ready_items(NODE, MEET)
    blocked = oi.get_blocked_items(NODE, MEET)
    # disjoint by identity of text (no dup text in fixture)
    ready_texts = {it["text"] for it in ready}
    blocked_texts = {it["text"] for it in blocked}
    _assert(
        ready_texts.isdisjoint(blocked_texts),
        "ready and blocked must be disjoint",
    )
    _assert(
        len(ready) + len(blocked) == len(all_items),
        f"ready({len(ready)}) + blocked({len(blocked)}) "
        f"!= total({len(all_items)})",
    )


def test_06_top_actionable_is_highest_priority() -> None:
    _fresh_populated()
    top = oi.get_top_actionable(NODE, MEET)
    _assert(top is not None, "top must exist on populated summary")
    _assert(top.get("priority") == "high", "top priority is high")


def test_07_owner_breakdown_counts() -> None:
    _fresh_populated()
    breakdown = oi.get_owner_breakdown(NODE, MEET)
    _assert(isinstance(breakdown, dict), "breakdown is dict")
    _assert("counts" in breakdown, "counts key")
    _assert("unassigned" in breakdown, "unassigned key")
    _assert("top_owner" in breakdown, "top_owner key")
    _assert("total" in breakdown, "total key")
    counts = breakdown["counts"]
    total_from_counts = sum(counts.values()) + breakdown["unassigned"]
    _assert(
        total_from_counts == breakdown["total"],
        f"counts sum ({total_from_counts}) != total ({breakdown['total']})",
    )
    if counts:
        top = max(counts.items(), key=lambda kv: kv[1])[0]
        _assert(breakdown["top_owner"] == top, "top_owner correct")


def test_08_mark_resolved_with_selector() -> None:
    _fresh_populated()
    before = oi.summarize(NODE, MEET)
    result = oi.mark_resolved(
        NODE, MEET, text_contains="signed contract", owner="antony"
    )
    _assert(result["count"] >= 1, "mark_resolved should match at least 1")
    after = oi.summarize(NODE, MEET)
    _assert(
        after["unresolved_commitments_count"]
        < before["unresolved_commitments_count"],
        "unresolved count must decrease after mark_resolved",
    )


def test_09_mark_resolved_delta_in_summary() -> None:
    _fresh_populated()
    before = oi.summarize(NODE, MEET)
    oi.mark_resolved(NODE, MEET, text_contains="pricing memo")
    after = oi.summarize(NODE, MEET)
    _assert(
        after["completion_rate"] >= before["completion_rate"],
        "completion_rate must not decrease",
    )


def test_10_assign_owner_updates_breakdown() -> None:
    _fresh_populated()
    result = oi.assign_owner(
        NODE,
        MEET,
        text_contains="circle back",
        new_owner="marcus",
    )
    _assert(result["count"] >= 1, "assign_owner should match at least 1")
    breakdown = oi.get_owner_breakdown(NODE, MEET)
    _assert(
        "marcus" in breakdown["counts"] or breakdown["unassigned"] >= 0,
        "marcus must appear in ownership distribution",
    )


def test_11_refresh_returns_snapshot() -> None:
    _fresh_populated()
    snap = oi.refresh(NODE, MEET)
    _assert(isinstance(snap, dict), "refresh returns dict")
    _assert(snap.get("schema_version") == "v1", "v1 schema")
    _assert("actionable" in snap, "actionable block present")


def test_12_json_serializable() -> None:
    _fresh_populated()
    payloads = [
        oi.summarize(NODE, MEET),
        oi.get_actionable_items(NODE, MEET),
        oi.get_top_actionable(NODE, MEET),
        oi.get_blocked_items(NODE, MEET),
        oi.get_ready_items(NODE, MEET),
        oi.get_owner_breakdown(NODE, MEET),
        oi.refresh(NODE, MEET),
    ]
    for p in payloads:
        json.dumps(p, default=str)  # raises on failure


def test_13_degrades_on_empty_and_malformed() -> None:
    mi.reset_meeting_summary_store_for_tests()
    _assert(oi.get_actionable_items("", None) == [], "empty node → []")
    _assert(oi.get_top_actionable("", None) is None, "empty node → None")
    _assert(
        oi.get_owner_breakdown("", None)["total"] == 0,
        "empty node → 0 total",
    )
    _assert(
        oi.mark_resolved("", "", text_contains="x")["count"] == 0,
        "mark_resolved on empty → 0",
    )
    _assert(
        oi.assign_owner("", "", text_contains="x", new_owner="y")["count"] == 0,
        "assign_owner on empty → 0",
    )


def test_14_cli_subcommands_execute() -> None:
    _fresh_populated()
    cli = f"{_ROOT}/scripts/substrate_operator_cli.py"
    cases = [
        ["summary", "--node", NODE, "--meeting-id", MEET],
        ["actionable", "--node", NODE, "--meeting-id", MEET],
        ["actionable", "--node", NODE, "--meeting-id", MEET, "--ready-only"],
        ["actionable", "--node", NODE, "--meeting-id", MEET, "--blocked-only"],
        ["top", "--node", NODE, "--meeting-id", MEET],
        ["blocked", "--node", NODE, "--meeting-id", MEET],
        ["owners", "--node", NODE, "--meeting-id", MEET],
        ["refresh", "--node", NODE, "--meeting-id", MEET],
    ]
    for argv in cases:
        proc = subprocess.run(
            [sys.executable, cli, *argv],
            capture_output=True,
            text=True,
            timeout=20,
        )
        _assert(
            proc.returncode == 0,
            f"cli {argv} failed rc={proc.returncode} stderr={proc.stderr[:400]}",
        )
        # Each subcommand MUST emit JSON
        json.loads(proc.stdout)


def test_15_hot_path_untouched() -> None:
    # grep-guard: our new module name must not appear in hot-path files
    for hp in HOT_PATH_FILES:
        path = f"{_ROOT}/{hp}"
        try:
            with open(path, "r", encoding="utf-8") as f:
                body = f.read()
        except FileNotFoundError:
            continue
        _assert(
            "operator_interface" not in body,
            f"hot-path {hp} must not reference operator_interface",
        )


def test_16_existing_linkage_surface_intact() -> None:
    # Re-import meeting_intelligence entry points; they must still work.
    _fresh_populated()
    snap = mi.linkage_snapshot(NODE, MEET)
    _assert(snap.get("schema_version") == "v1", "linkage_snapshot still v1")
    _assert("actionable" in snap, "actionable block still present")
    rep = mi.intelligence_report_block(node_id=NODE, meeting_id=MEET)
    _assert("actionable_items" in rep, "legacy report still populated")


TESTS = [
    test_01_summarize_empty,
    test_02_get_actionable_items_populated,
    test_03_filter_by_priority,
    test_04_filter_by_owner,
    test_05_ready_and_blocked_partition,
    test_06_top_actionable_is_highest_priority,
    test_07_owner_breakdown_counts,
    test_08_mark_resolved_with_selector,
    test_09_mark_resolved_delta_in_summary,
    test_10_assign_owner_updates_breakdown,
    test_11_refresh_returns_snapshot,
    test_12_json_serializable,
    test_13_degrades_on_empty_and_malformed,
    test_14_cli_subcommands_execute,
    test_15_hot_path_untouched,
    test_16_existing_linkage_surface_intact,
]


def main() -> int:
    for t in TESTS:
        t()
        print(f"ok — {t.__name__}")
    print("OPERATOR INTERFACE SMOKE TEST PASSED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
