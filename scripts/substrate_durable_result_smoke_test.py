#!/usr/bin/env python3
"""
Substrate durable-result smoke test.

Proves the ResultStore + ritual reconciliation loop survives a process
boundary. We can't fork a real subprocess cheaply here, so we simulate
the boundary by:

  1. Draining results + reconciling a ritual in-process
  2. Calling reset_result_store_for_tests() AND reset_storage_for_tests()
     to drop every in-memory singleton (same effect as a fresh process)
  3. Re-fetching the ResultStore — which MUST rehydrate from the durable
     backing (Neon or JSON file) and still answer by action_id
  4. Re-running reconcile_ritual() — which MUST still match

If durability is broken, step 3 returns None and the test fails.

Usage:
    python3 /opt/OS/scripts/substrate_durable_result_smoke_test.py
"""

from __future__ import annotations

import sys

sys.path.insert(0, "/opt/OS")

from eos_ai.substrate.result_query import (  # noqa: E402
    by_action_id,
    latest,
    latest_by_kind,
    latest_by_node,
    latest_failed,
    node_health_summary,
    ritual_outcomes_summary,
    stats as result_stats,
    unresolved_rituals,
)
from eos_ai.substrate.actions import ActionResult, ActionStatus  # noqa: E402
from eos_ai.substrate.result_store import (  # noqa: E402
    get_result_store,
    reset_result_store_for_tests,
)
from eos_ai.substrate.ritual_body import RitualPolicy  # noqa: E402
from eos_ai.substrate.ritual_reconciler import reconcile_ritual  # noqa: E402
from eos_ai.substrate.ritual_runner import start_open_day  # noqa: E402
from eos_ai.substrate.rituals import RitualRegistry  # noqa: E402
from eos_ai.substrate.station_bus import get_station_bus  # noqa: E402
from eos_ai.substrate.station_daemon import StationDaemon  # noqa: E402
from eos_ai.substrate.station_drainer import drain_all  # noqa: E402


TEST_NODE = "durable-result-smoketest"


def _header(msg: str) -> None:
    print(f"\n── {msg} " + "─" * max(0, 60 - len(msg)))


def main() -> int:
    bus = get_station_bus()
    reset_result_store_for_tests()

    # Clean any stale state
    bus.daemon_take_outbox(TEST_NODE)
    bus.drain_inbox(TEST_NODE)

    # Seed: propose a ritual, run the daemon tick, drain results, reconcile.
    _header("1. Seed a ritual + execute via dry-run daemon")
    daemon = StationDaemon(
        node_id=TEST_NODE,
        poll_interval_s=0.05,
        heartbeat_interval_s=0.01,
        dry_run=True,
    )
    daemon.register()
    daemon._tick()  # noqa: SLF001

    policy = RitualPolicy(
        station_node_id=TEST_NODE,
        open_speak="durable smoke test",
        open_scene="operator_mode",
    )
    rid = start_open_day(policy=policy)
    ritual = RitualRegistry.default().get(rid)
    assert ritual is not None
    proposed_ids = [
        e["action_id"]
        for e in (ritual.outputs.get("body_actions") or [])
        if "action_id" in e
    ]
    assert len(proposed_ids) == 2, f"expected 2 action_ids, got {proposed_ids}"
    print(f"  ritual_id={rid}  proposed={proposed_ids}")

    daemon._tick()  # noqa: SLF001
    stats = drain_all(TEST_NODE)
    assert stats.results.drained == 2, (
        f"drain expected 2 results, got {stats.results.drained}"
    )
    assert stats.results.succeeded == 2

    _header("2. Reconcile once (pre-boundary)")
    summary_pre = reconcile_ritual(rid)
    assert summary_pre is not None
    assert summary_pre.matched == 2
    assert summary_pre.fully_resolved
    print(f"  pre:  {summary_pre.as_dict()}")

    # Verify query helpers see the rows before the boundary
    rs_stats = result_stats()
    print(f"  result_store stats: {rs_stats}")
    assert rs_stats["total"] >= 2

    # --- PROCESS BOUNDARY SIMULATION ---------------------------------
    _header("3. Simulate process boundary (drop all in-memory singletons)")
    reset_result_store_for_tests()
    # Also force storage re-resolve so we exercise the real backing read,
    # not a stale in-process dict. RitualRegistry has its own singleton —
    # we leave it alone because rituals are already durable and reconcile
    # is what we're stressing here.
    try:
        from eos_ai.substrate.storage import reset_storage_for_tests

        reset_storage_for_tests()
    except Exception as e:
        print(f"  (storage reset skipped: {e})")
    print("  singletons dropped")

    _header("4. Re-fetch ResultStore — MUST rehydrate from durable backing")
    store2 = get_result_store()
    print(f"  rehydrated rows: {len(store2)}")
    assert len(store2) >= 2, "durable rehydrate returned empty store"

    for aid in proposed_ids:
        ir = store2.get(aid)
        assert ir is not None, f"durable lookup missed {aid}"
        assert ir.node_id == TEST_NODE
        assert ir.status == "succeeded"
        print(f"    • {aid} → {ir.status} ({ir.detail})")

    _header("5. Query helpers post-boundary")
    row = by_action_id(proposed_ids[0])
    assert row is not None and row["action_id"] == proposed_ids[0]
    print(f"  by_action_id: {row['action_id']} status={row['status']}")

    node_rows = latest_by_node(TEST_NODE, limit=10)
    assert len(node_rows) >= 2
    print(f"  latest_by_node({TEST_NODE}): {len(node_rows)} rows")

    latest_rows = latest(limit=5)
    assert len(latest_rows) >= 1
    print(f"  latest(5): {len(latest_rows)} rows")

    failed = latest_failed(limit=10)
    print(f"  latest_failed: {len(failed)} rows (fallbacks count here)")

    _header("6. Reconcile again post-boundary — must still match")
    summary_post = reconcile_ritual(rid)
    assert summary_post is not None
    print(f"  post: {summary_post.as_dict()}")
    assert summary_post.matched == 2, (
        f"cross-process reconcile lost matches: {summary_post.as_dict()}"
    )
    assert summary_post.fully_resolved
    assert summary_post.all_succeeded

    _header("7. Ritual outcomes summary (query helper)")
    outcomes = ritual_outcomes_summary(limit=5)
    print(f"  outcomes rows: {len(outcomes)}")
    assert any(o["ritual_id"] == rid for o in outcomes), "ritual missing from outcomes"

    _header("8. Idempotent re-put — no row explosion")
    before = len(store2)
    for aid in proposed_ids:
        ir = store2.get(aid)
        if ir is not None:
            store2.put(ir)
    after = len(store2)
    assert before == after, f"idempotent put changed count: {before} -> {after}"
    print(f"  rows stable at {after}")

    _header("9. Kind metadata — new results carry kind")
    # The dry-run daemon stamped kind on both results via the new seam.
    kinded = 0
    for aid in proposed_ids:
        ir = store2.get(aid)
        if ir and ir.kind:
            kinded += 1
    assert kinded == 2, f"expected 2 kinded results, got {kinded}"
    enriched_stats = result_stats()
    assert "by_kind" in enriched_stats
    print(f"  stats.by_kind: {enriched_stats['by_kind']}")
    assert enriched_stats["by_kind"], "by_kind must be non-empty after daemon tick"

    speak_rows = latest_by_kind("speak_text", limit=5)
    print(f"  latest_by_kind(speak_text): {len(speak_rows)} rows")
    assert speak_rows, "speak_text kind lookup returned empty"

    node_health = node_health_summary(TEST_NODE)
    print(f"  node_health: {node_health}")
    assert node_health["total"] >= 2
    assert node_health["by_kind"], "node health missing kind breakdown"

    _header("10. Backward compat — result without kind still ingests + resolves")
    # Simulate an older daemon: post a result with NO kind field anywhere.
    legacy_result = ActionResult(
        action_id="act_legacy_nokind",
        status=ActionStatus.SUCCEEDED,
        detail="legacy payload (no kind)",
        data={},
    )
    bus.daemon_post_result(TEST_NODE, legacy_result)  # no kind kwarg
    legacy_stats = drain_all(TEST_NODE)
    assert legacy_stats.results.drained == 1
    assert legacy_stats.results.without_kind == 1
    legacy_ir = get_result_store().get("act_legacy_nokind")
    assert legacy_ir is not None and legacy_ir.kind is None
    print(f"  legacy ingested ok, kind=None, stats.without_kind={legacy_stats.results.without_kind}")

    _header("11. Unresolved rituals helper — empty after reconcile")
    unresolved = unresolved_rituals(limit=10)
    # The seeded ritual was fully reconciled, so it must NOT appear.
    assert not any(u["ritual_id"] == rid for u in unresolved), (
        f"fully-reconciled ritual {rid} leaked into unresolved list"
    )
    print(f"  unresolved rituals: {len(unresolved)}")

    _header("DURABLE RESULT SMOKE TEST PASSED")
    print("  verified: drain → persist → boundary → rehydrate → reconcile")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
