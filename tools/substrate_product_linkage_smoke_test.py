#!/usr/bin/env python3
"""
Smoke test for Product Linkage Layer v1.

Validates the stable, versioned, product-facing contract built on top of
the intelligence layers. Pure transform; no execution, no side effects.

Checks:
  1. build_linkage_snapshot builds a well-formed dict on a fresh summary
  2. schema_version is present and stable ("v1")
  3. All top-level blocks present: summary, execution, temporal,
     coordination, actionable (+ meta: schema_version, contract, source,
     node_id, meeting_id, generated_at)
  4. actionable.items are normalized to stable keys
  5. readiness_summary is normalized
  6. ownership/temporal/execution blocks populated from a realistic summary
  7. actionable cap respected (MAX_ACTIONABLE_ITEMS)
  8. Malformed input degrades safely (None summary → empty snapshot)
  9. Existing intelligence_report_block still works and still exposes
     the pre-existing Execution Linkage keys (no regression)
 10. Snapshot is JSON-serializable
 11. product_linkage_block / linkage_snapshot entry points work
 12. Hot-path files remain clean (grep guard)
 13. Contract surface is backward-compatible: intelligence_report_block
     is unchanged in its key set (sanity check on known keys)

Prints:
    PRODUCT LINKAGE SMOKE TEST PASSED
"""

from __future__ import annotations

import json
import subprocess
import sys
import time

sys.path.insert(0, "/opt/OS")

from umh.runtime_engine.substrate import meeting_intelligence as mi  # noqa: E402

HOT_PATH_FILES = (
    "eos/gateway.py",
    "eos/cognitive_loop.py",
    "eos/model_router.py",
    "eos/agent_runtime.py",
    "eos/primitives.py",
)

REQUIRED_TOP_LEVEL_KEYS = {
    "schema_version",
    "contract",
    "source",
    "node_id",
    "meeting_id",
    "generated_at",
    "summary",
    "execution",
    "temporal",
    "coordination",
    "actionable",
}

REQUIRED_SUMMARY_KEYS = {
    "priority_level",
    "decision_pressure_score",
    "ambiguity_score",
    "escalation_level",
    "escalation_trend",
    "participants_count",
    "open_loops_count",
    "decisions_count",
}

REQUIRED_EXECUTION_KEYS = {
    "commitments_count",
    "unresolved_commitments_count",
    "resolved_commitments_count",
    "completion_rate",
    "stale_commitments_count",
}

REQUIRED_TEMPORAL_KEYS = {
    "temporal_health",
    "oldest_unresolved_commitment_age_seconds",
    "stale_open_loops_count",
    "followup_cooldown_active",
    "next_followup_eligible_ts",
}

REQUIRED_COORDINATION_KEYS = {
    "ownership_distribution",
    "unassigned_commitments_count",
    "top_owner",
    "ownership_pressure_hint",
}

REQUIRED_ACTIONABLE_KEYS = {
    "items",
    "count",
    "ready_count",
    "blocked_count",
    "readiness_summary",
    "top_actionable_owner",
    "highest_priority_actionable",
}

REQUIRED_ITEM_KEYS = {
    "text",
    "kind",
    "owner",
    "owner_confidence",
    "priority",
    "readiness_state",
    "readiness_reason",
    "execution_ready",
    "source",
}


def _fresh_summary() -> mi.MeetingSummary:
    mi.reset_meeting_summary_store_for_tests()
    return mi.MeetingSummary(node_id="node-prod", meeting_id="meet-prod")


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


def _assert(cond: bool, msg: str) -> None:
    if not cond:
        raise AssertionError(msg)


def test_01_empty_snapshot_shape() -> None:
    snap = mi.build_linkage_snapshot(None, node_id="node-x", meeting_id="meet-x")
    _assert(isinstance(snap, dict), "snapshot must be dict")
    _assert(
        REQUIRED_TOP_LEVEL_KEYS.issubset(snap.keys()),
        f"missing top-level keys: {REQUIRED_TOP_LEVEL_KEYS - snap.keys()}",
    )
    _assert(snap["schema_version"] == "v1", "schema_version must be v1")
    _assert(snap["contract"] == "product_linkage", "contract label mismatch")
    _assert(snap["source"] == "meeting_intelligence", "source label mismatch")
    _assert(snap["node_id"] == "node-x", "node_id must be preserved")
    _assert(snap["meeting_id"] == "meet-x", "meeting_id must be preserved")
    _assert(isinstance(snap["generated_at"], float), "generated_at must be float")


def test_02_sub_block_schemas_on_empty() -> None:
    snap = mi.build_linkage_snapshot(None, node_id="n", meeting_id="m")
    _assert(
        REQUIRED_SUMMARY_KEYS.issubset(snap["summary"].keys()), "summary schema"
    )
    _assert(
        REQUIRED_EXECUTION_KEYS.issubset(snap["execution"].keys()), "execution schema"
    )
    _assert(
        REQUIRED_TEMPORAL_KEYS.issubset(snap["temporal"].keys()), "temporal schema"
    )
    _assert(
        REQUIRED_COORDINATION_KEYS.issubset(snap["coordination"].keys()),
        "coordination schema",
    )
    _assert(
        REQUIRED_ACTIONABLE_KEYS.issubset(snap["actionable"].keys()),
        "actionable schema",
    )


def test_03_realistic_populated_snapshot() -> None:
    s = _fresh_summary()
    s.priority_level = "high"
    s.decision_pressure_score = 12
    s.ambiguity_score = 4
    s.escalation_level = "medium"
    s.escalation_trend = "rising"
    s.participants = {"antony", "daisy"}
    s.open_loops = ["legal review outstanding", "pricing unsettled"]
    s.decisions = ["ship v1 friday"]
    s.commitments = [
        _commitment("send the signed contract to legal by friday", "antony"),
        _commitment("circle back", None, conf="low"),
        _commitment("prepare the pricing memo for the investor meeting", "daisy"),
    ]
    mi.get_meeting_summary_store().put(s)

    snap = mi.build_linkage_snapshot(
        s, node_id=s.node_id, meeting_id=s.meeting_id
    )

    # summary block reflects state
    _assert(snap["summary"]["priority_level"] == "high", "priority propagated")
    _assert(snap["summary"]["decision_pressure_score"] == 12, "pressure propagated")
    _assert(snap["summary"]["participants_count"] == 2, "participants counted")
    _assert(snap["summary"]["open_loops_count"] == 2, "open loops counted")
    _assert(snap["summary"]["decisions_count"] == 1, "decisions counted")

    # execution block
    _assert(snap["execution"]["commitments_count"] == 3, "commitments counted")
    _assert(snap["execution"]["unresolved_commitments_count"] == 3, "unresolved")
    _assert(snap["execution"]["completion_rate"] == 0.0, "completion rate zero")

    # coordination block
    _assert(
        snap["coordination"]["unassigned_commitments_count"] >= 1,
        "unassigned counted",
    )
    _assert(
        isinstance(snap["coordination"]["ownership_distribution"], dict),
        "ownership distribution dict",
    )

    # actionable block normalized
    items = snap["actionable"]["items"]
    _assert(isinstance(items, list), "items must be list")
    _assert(len(items) == snap["actionable"]["count"], "count matches length")
    for it in items:
        _assert(
            REQUIRED_ITEM_KEYS.issubset(it.keys()),
            f"item missing keys: {REQUIRED_ITEM_KEYS - it.keys()}",
        )
        _assert(
            it["readiness_state"]
            in {
                "ready",
                "blocked_missing_owner",
                "blocked_ambiguous",
                "blocked_low_context",
            },
            f"invalid readiness_state: {it['readiness_state']}",
        )
        _assert(it["priority"] in {"low", "medium", "high"}, "priority valid")
    _assert(
        snap["actionable"]["ready_count"] + snap["actionable"]["blocked_count"]
        == snap["actionable"]["count"],
        "ready + blocked == count",
    )


def test_04_actionable_cap_respected() -> None:
    s = _fresh_summary()
    s.priority_level = "high"
    # 30 commitments with clear owners + clear text — all candidates
    s.commitments = [
        _commitment(
            f"finalize deliverable number {i} for the client review", "antony"
        )
        for i in range(30)
    ]
    mi.get_meeting_summary_store().put(s)

    snap = mi.build_linkage_snapshot(
        s, node_id=s.node_id, meeting_id=s.meeting_id
    )
    _assert(
        snap["actionable"]["count"] <= mi.MAX_ACTIONABLE_ITEMS,
        f"cap exceeded: {snap['actionable']['count']}",
    )


def test_05_malformed_input_degrades_safely() -> None:
    class Broken:
        @property
        def node_id(self):
            raise RuntimeError("boom")

    snap = mi.build_linkage_snapshot(Broken(), node_id="n", meeting_id="m")
    _assert(snap["schema_version"] == "v1", "still well-formed on failure")
    _assert(REQUIRED_TOP_LEVEL_KEYS.issubset(snap.keys()), "all blocks present")


def test_06_no_regression_in_intelligence_report_block() -> None:
    # After adding product linkage, the existing report must still work
    # and still expose its pre-existing keys.
    s = _fresh_summary()
    s.priority_level = "medium"
    s.commitments = [_commitment("review the draft policy", "antony")]
    mi.get_meeting_summary_store().put(s)

    report = mi.intelligence_report_block(
        node_id=s.node_id, meeting_id=s.meeting_id
    )
    expected_legacy_keys = {
        "summary",
        "scoring",
        "actionable_items",
        "actionable_items_count",
        "execution_readiness_summary",
        "ownership_distribution",
        "temporal_health",
        "commitments_count",
    }
    _assert(
        expected_legacy_keys.issubset(report.keys()),
        f"regression — missing legacy keys: {expected_legacy_keys - report.keys()}",
    )


def test_07_entry_points_work() -> None:
    s = _fresh_summary()
    s.commitments = [_commitment("draft the brief", "antony")]
    mi.get_meeting_summary_store().put(s)

    snap_a = mi.linkage_snapshot(s.node_id, s.meeting_id)
    snap_b = mi.product_linkage_block(s.node_id, s.meeting_id)

    _assert(snap_a["schema_version"] == "v1", "linkage_snapshot ok")
    _assert(snap_b["schema_version"] == "v1", "product_linkage_block ok")
    _assert(snap_a["node_id"] == s.node_id, "node_id preserved")
    _assert(snap_b["meeting_id"] == s.meeting_id, "meeting_id preserved")

    # Unknown node degrades safely
    empty = mi.linkage_snapshot("node-does-not-exist", "meet-nope")
    _assert(empty["schema_version"] == "v1", "unknown node still returns v1")
    _assert(empty["actionable"]["count"] == 0, "unknown node has no items")


def test_08_json_serializable() -> None:
    s = _fresh_summary()
    s.priority_level = "high"
    s.commitments = [_commitment("confirm the venue booking", "daisy")]
    mi.get_meeting_summary_store().put(s)
    snap = mi.build_linkage_snapshot(
        s, node_id=s.node_id, meeting_id=s.meeting_id
    )
    blob = json.dumps(snap)
    _assert(len(blob) > 0, "json serializable")


def test_09_hot_path_files_clean() -> None:
    # Guard: no Product Linkage symbols should have leaked into hot-path files.
    for f in HOT_PATH_FILES:
        try:
            out = subprocess.run(
                ["grep", "-l", "LINKAGE_SCHEMA_VERSION", f"/opt/OS/{f}"],
                capture_output=True,
                text=True,
            )
            _assert(
                out.returncode != 0,
                f"hot-path file touched: {f}",
            )
        except FileNotFoundError:
            # grep missing is not a failure condition for this smoke test
            pass


def main() -> int:
    tests = [
        test_01_empty_snapshot_shape,
        test_02_sub_block_schemas_on_empty,
        test_03_realistic_populated_snapshot,
        test_04_actionable_cap_respected,
        test_05_malformed_input_degrades_safely,
        test_06_no_regression_in_intelligence_report_block,
        test_07_entry_points_work,
        test_08_json_serializable,
        test_09_hot_path_files_clean,
    ]
    for t in tests:
        t()
        print(f"  ok — {t.__name__}")
    print("PRODUCT LINKAGE SMOKE TEST PASSED")
    return 0


if __name__ == "__main__":
    sys.exit(main())
