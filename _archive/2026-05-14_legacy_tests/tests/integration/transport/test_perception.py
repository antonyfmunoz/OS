"""Smoke tests for runtime.substrate.perception.

Validates:
  1.  test_perception_record_create   — PerceptionRecord.new() creates correctly
  2.  test_perception_record_roundtrip — to_dict/from_dict roundtrip
  3.  test_fingerprint_stable          — same source+summary => same fingerprint
  4.  test_perception_store_put_get    — store persist and retrieve
  5.  test_perception_store_persistence — survives singleton reset
  6.  test_has_fingerprint             — fingerprint dedup check
  7.  test_collect_task_perception     — task collector runs without error
  8.  test_collect_all_perceptions     — master collector runs without error
  9.  test_severity_filter             — by_severity returns correct records
 10.  test_prune_oldest_info           — pruning removes INFO first

Run directly:
    python3 tests/substrate/test_perception.py
"""

from __future__ import annotations

import sys

sys.path.insert(0, os.environ.get("UMH_ROOT") or os.environ.get("OS_ROOT") or os.environ.get("EOS_ROOT") or "/opt/OS")

from runtime.substrate.perception import (  # noqa: E402
    PerceptionRecord,
    PerceptionSeverity,
    PerceptionSource,
    PerceptionStore,
    collect_all_perceptions,
    collect_task_perception,
)

_PASS = 0
_FAIL = 0


def _report(name: str, passed: bool, detail: str = "") -> None:
    global _PASS, _FAIL  # noqa: PLW0603
    tag = "PASS" if passed else "FAIL"
    if not passed:
        _FAIL += 1
    else:
        _PASS += 1
    suffix = f" — {detail}" if detail else ""
    print(f"  [{tag}] {name}{suffix}")


def _reset_all() -> None:
    """Reset perception store singleton and clear storage key between tests."""
    try:
        from runtime.substrate.storage import get_storage

        get_storage().put("perception_records", None)
    except Exception:  # noqa: BLE001
        pass
    PerceptionStore.reset_default_for_tests()


# ─── Test 1: PerceptionRecord.new() creates correctly ─────────────────────


def test_perception_record_create() -> None:
    print("\n── Test 1: PerceptionRecord.new() creates correctly ──")

    rec = PerceptionRecord.new(
        source=PerceptionSource.TASK_SYSTEM,
        summary="Task blocked >4h: rebuild graph",
        severity=PerceptionSeverity.WARNING,
        payload={"task_id": "task_abc123", "hours_blocked": 5.2},
        suggested_action="Review blocked tasks",
    )

    _report(
        "record_id starts with perc_",
        rec.record_id.startswith("perc_"),
        f"got {rec.record_id!r}",
    )
    _report(
        "source is TASK_SYSTEM",
        rec.source == PerceptionSource.TASK_SYSTEM,
        f"got {rec.source.value}",
    )
    _report(
        "severity is WARNING",
        rec.severity == PerceptionSeverity.WARNING,
        f"got {rec.severity.value}",
    )
    _report(
        "summary matches",
        rec.summary == "Task blocked >4h: rebuild graph",
        f"got {rec.summary!r}",
    )
    _report(
        "fingerprint is not empty",
        bool(rec.fingerprint),
        f"got {rec.fingerprint!r}",
    )
    _report(
        "observed_at is set",
        bool(rec.observed_at),
        f"got {rec.observed_at!r}",
    )
    _report(
        "payload preserved",
        rec.payload.get("task_id") == "task_abc123",
        f"got {rec.payload}",
    )
    _report(
        "suggested_action preserved",
        rec.suggested_action == "Review blocked tasks",
        f"got {rec.suggested_action!r}",
    )


# ─── Test 2: to_dict / from_dict roundtrip ────────────────────────────────


def test_perception_record_roundtrip() -> None:
    print("\n── Test 2: to_dict / from_dict roundtrip ──")

    original = PerceptionRecord.new(
        source=PerceptionSource.GIT_STATUS,
        summary="Uncommitted changes: 25 files",
        severity=PerceptionSeverity.INFO,
        payload={"file_count": 25},
        suggested_action="Commit pending changes",
    )

    d = original.to_dict()
    restored = PerceptionRecord.from_dict(d)

    _report(
        "record_id roundtrips",
        restored.record_id == original.record_id,
        f"expected {original.record_id!r}, got {restored.record_id!r}",
    )
    _report(
        "source roundtrips",
        restored.source == original.source,
        f"expected {original.source.value}, got {restored.source.value}",
    )
    _report(
        "severity roundtrips",
        restored.severity == original.severity,
        f"expected {original.severity.value}, got {restored.severity.value}",
    )
    _report(
        "summary roundtrips",
        restored.summary == original.summary,
        f"got {restored.summary!r}",
    )
    _report(
        "observed_at roundtrips",
        restored.observed_at == original.observed_at,
        f"got {restored.observed_at!r}",
    )
    _report(
        "fingerprint roundtrips",
        restored.fingerprint == original.fingerprint,
        f"got {restored.fingerprint!r}",
    )
    _report(
        "payload roundtrips",
        restored.payload == original.payload,
        f"got {restored.payload}",
    )
    _report(
        "suggested_action roundtrips",
        restored.suggested_action == original.suggested_action,
        f"got {restored.suggested_action!r}",
    )


# ─── Test 3: fingerprint stability ────────────────────────────────────────


def test_fingerprint_stable() -> None:
    print("\n── Test 3: same source+summary => same fingerprint ──")

    r1 = PerceptionRecord.new(
        source=PerceptionSource.RUNTIME_LOGS,
        summary="Errors in logs (bot.log): 3 lines",
        severity=PerceptionSeverity.WARNING,
    )
    r2 = PerceptionRecord.new(
        source=PerceptionSource.RUNTIME_LOGS,
        summary="Errors in logs (bot.log): 3 lines",
        severity=PerceptionSeverity.CRITICAL,  # different severity, same fingerprint
    )
    r3 = PerceptionRecord.new(
        source=PerceptionSource.RUNTIME_LOGS,
        summary="Different summary entirely",
        severity=PerceptionSeverity.WARNING,
    )

    _report(
        "same source+summary => same fingerprint",
        r1.fingerprint == r2.fingerprint,
        f"r1={r1.fingerprint!r}, r2={r2.fingerprint!r}",
    )
    _report(
        "different summary => different fingerprint",
        r1.fingerprint != r3.fingerprint,
        f"r1={r1.fingerprint!r}, r3={r3.fingerprint!r}",
    )
    _report(
        "record_ids are different (not coupled to fingerprint)",
        r1.record_id != r2.record_id,
        f"r1={r1.record_id!r}, r2={r2.record_id!r}",
    )


# ─── Test 4: store put and get ────────────────────────────────────────────


def test_perception_store_put_get() -> None:
    print("\n── Test 4: PerceptionStore put and get ──")

    _reset_all()

    store = PerceptionStore.default()
    rec = PerceptionRecord.new(
        source=PerceptionSource.DISCORD_PENDING,
        summary="3 unread messages in #general",
        severity=PerceptionSeverity.INFO,
        payload={"channel": "general", "count": 3},
    )
    store.put(rec)

    retrieved = store.get(rec.record_id)

    _report(
        "record retrieved by ID",
        retrieved is not None,
        "got None" if retrieved is None else "",
    )
    if retrieved is not None:
        _report(
            "record_id matches",
            retrieved.record_id == rec.record_id,
            f"got {retrieved.record_id!r}",
        )
        _report(
            "summary matches",
            retrieved.summary == rec.summary,
            f"got {retrieved.summary!r}",
        )
        _report(
            "source matches",
            retrieved.source == rec.source,
            f"got {retrieved.source.value}",
        )

    missing = store.get("perc_nonexistent")
    _report(
        "missing ID returns None",
        missing is None,
        f"got {missing!r}" if missing is not None else "",
    )


# ─── Test 5: persistence across singleton reset ───────────────────────────


def test_perception_store_persistence() -> None:
    print("\n── Test 5: PerceptionStore survives singleton reset ──")

    _reset_all()

    rec = PerceptionRecord.new(
        source=PerceptionSource.OPERATOR_SESSION,
        summary="Day open for 18h",
        severity=PerceptionSeverity.WARNING,
        payload={"day_session_id": "ds_test456"},
    )
    PerceptionStore.default().put(rec)

    # Reset singleton — simulates process restart
    PerceptionStore.reset_default_for_tests()

    # Reload from storage
    reloaded = PerceptionStore.default().get(rec.record_id)

    _report(
        "record survives singleton reset",
        reloaded is not None,
        "got None" if reloaded is None else "",
    )
    if reloaded is not None:
        _report(
            "record_id survives",
            reloaded.record_id == rec.record_id,
            f"expected {rec.record_id!r}, got {reloaded.record_id!r}",
        )
        _report(
            "summary survives",
            reloaded.summary == rec.summary,
            f"got {reloaded.summary!r}",
        )
        _report(
            "severity survives",
            reloaded.severity == rec.severity,
            f"got {reloaded.severity.value}",
        )


# ─── Test 6: has_fingerprint dedup check ──────────────────────────────────


def test_has_fingerprint() -> None:
    print("\n── Test 6: has_fingerprint dedup check ──")

    _reset_all()

    rec = PerceptionRecord.new(
        source=PerceptionSource.PIPELINE_SYSTEM,
        summary="Pipeline failed: deploy-prod",
        severity=PerceptionSeverity.CRITICAL,
    )
    store = PerceptionStore.default()
    store.put(rec)

    _report(
        "has_fingerprint returns True for stored record",
        store.has_fingerprint(rec.fingerprint),
        f"fingerprint={rec.fingerprint!r}",
    )
    _report(
        "has_fingerprint returns False for random fingerprint",
        not store.has_fingerprint("deadbeef00000000"),
        "",
    )


# ─── Test 7: collect_task_perception runs without error ────────────────────


def test_collect_task_perception() -> None:
    print("\n── Test 7: collect_task_perception runs without error ──")

    result = collect_task_perception()

    _report(
        "returns a list",
        isinstance(result, list),
        f"got {type(result).__name__}",
    )
    _report(
        "all items are PerceptionRecord",
        all(isinstance(r, PerceptionRecord) for r in result),
        f"got {len(result)} records",
    )


# ─── Test 8: collect_all_perceptions runs without error ────────────────────


def test_collect_all_perceptions() -> None:
    print("\n── Test 8: collect_all_perceptions runs without error ──")

    result = collect_all_perceptions()

    _report(
        "returns a list",
        isinstance(result, list),
        f"got {type(result).__name__}",
    )
    _report(
        "all items are PerceptionRecord",
        all(isinstance(r, PerceptionRecord) for r in result),
        f"got {len(result)} records",
    )


# ─── Test 9: by_severity returns correct subset ───────────────────────────


def test_severity_filter() -> None:
    print("\n── Test 9: by_severity returns correct subset ──")

    _reset_all()

    store = PerceptionStore.default()

    info_rec = PerceptionRecord.new(
        source=PerceptionSource.GIT_STATUS,
        summary="Unpushed commits: 2",
        severity=PerceptionSeverity.INFO,
    )
    warn_rec = PerceptionRecord.new(
        source=PerceptionSource.TASK_SYSTEM,
        summary="Task blocked >4h: fix deploy",
        severity=PerceptionSeverity.WARNING,
    )
    crit_rec = PerceptionRecord.new(
        source=PerceptionSource.RUNTIME_LOGS,
        summary="CRITICAL in logs: 5 lines",
        severity=PerceptionSeverity.CRITICAL,
    )
    warn_rec2 = PerceptionRecord.new(
        source=PerceptionSource.OPERATOR_SESSION,
        summary="Overnight mode >12h",
        severity=PerceptionSeverity.WARNING,
    )

    for rec in [info_rec, warn_rec, crit_rec, warn_rec2]:
        store.put(rec)

    warnings = store.by_severity(PerceptionSeverity.WARNING)
    criticals = store.by_severity(PerceptionSeverity.CRITICAL)
    infos = store.by_severity(PerceptionSeverity.INFO)

    _report(
        "2 WARNING records returned",
        len(warnings) == 2,
        f"got {len(warnings)}",
    )
    _report(
        "1 CRITICAL record returned",
        len(criticals) == 1,
        f"got {len(criticals)}",
    )
    _report(
        "1 INFO record returned",
        len(infos) == 1,
        f"got {len(infos)}",
    )
    _report(
        "all WARNING records have correct severity",
        all(r.severity == PerceptionSeverity.WARNING for r in warnings),
        "",
    )
    _report(
        "CRITICAL record matches",
        criticals[0].record_id == crit_rec.record_id,
        f"got {criticals[0].record_id!r}",
    )


# ─── Test 10: prune removes oldest INFO first ─────────────────────────────


def test_prune_oldest_info() -> None:
    print("\n── Test 10: pruning removes INFO first ──")

    _reset_all()

    # Use a small store to test pruning without creating 1000+ records.
    # Temporarily monkey-patch _MAX_RECORDS.
    import runtime.substrate.perception as perc_mod

    original_max = perc_mod._MAX_RECORDS
    perc_mod._MAX_RECORDS = 5

    try:
        store = PerceptionStore.default()

        # Insert 3 INFO records (oldest first)
        info_ids = []
        for i in range(3):
            rec = PerceptionRecord.new(
                source=PerceptionSource.GIT_STATUS,
                summary=f"Info record {i}",
                severity=PerceptionSeverity.INFO,
            )
            # Manually set observed_at to control ordering
            rec.observed_at = f"2026-01-01T0{i}:00:00+00:00"
            store.put(rec)
            info_ids.append(rec.record_id)

        # Insert 2 WARNING records
        warn_ids = []
        for i in range(2):
            rec = PerceptionRecord.new(
                source=PerceptionSource.TASK_SYSTEM,
                summary=f"Warning record {i}",
                severity=PerceptionSeverity.WARNING,
            )
            rec.observed_at = f"2026-01-01T1{i}:00:00+00:00"
            store.put(rec)
            warn_ids.append(rec.record_id)

        _report(
            "store has 5 records at capacity",
            len(store.all()) == 5,
            f"got {len(store.all())}",
        )

        # Insert one more WARNING — should trigger prune, removing oldest INFO
        overflow_rec = PerceptionRecord.new(
            source=PerceptionSource.PIPELINE_SYSTEM,
            summary="Overflow warning",
            severity=PerceptionSeverity.WARNING,
        )
        overflow_rec.observed_at = "2026-01-01T20:00:00+00:00"
        store.put(overflow_rec)

        all_records = store.all()
        remaining_ids = {r.record_id for r in all_records}

        _report(
            "store back at max capacity after prune",
            len(all_records) == 5,
            f"got {len(all_records)}",
        )
        _report(
            "oldest INFO record pruned",
            info_ids[0] not in remaining_ids,
            f"info_ids[0]={info_ids[0]!r} still present"
            if info_ids[0] in remaining_ids
            else "",
        )
        _report(
            "WARNING records all survived",
            all(wid in remaining_ids for wid in warn_ids),
            "",
        )
        _report(
            "overflow record present",
            overflow_rec.record_id in remaining_ids,
            "",
        )
    finally:
        perc_mod._MAX_RECORDS = original_max


# ─── Test 11: new perception sources exist ──────────────────────────────────


def test_new_sources_in_enum() -> None:
    print("\n── Test 11: new perception sources in enum ──")
    _report(
        "STATION_PRESENCE exists",
        hasattr(PerceptionSource, "STATION_PRESENCE"),
    )
    _report(
        "LOCAL_CONTROL exists",
        hasattr(PerceptionSource, "LOCAL_CONTROL"),
    )
    _report(
        "LIVE_SESSION exists",
        hasattr(PerceptionSource, "LIVE_SESSION"),
    )
    _report(
        "STATION_PRESENCE value",
        PerceptionSource.STATION_PRESENCE.value == "station_presence",
    )


# ─── Test 12: station presence collector runs ────────────────────────────────


def test_collect_station_presence_perception() -> None:
    print("\n── Test 12: collect_station_presence_perception ──")
    from runtime.substrate.perception import collect_station_presence_perception

    result = collect_station_presence_perception()
    _report("returns a list", isinstance(result, list))
    _report(
        "all items are PerceptionRecord",
        all(isinstance(r, PerceptionRecord) for r in result),
    )


# ─── Test 13: local control collector runs ───────────────────────────────────


def test_collect_local_control_perception() -> None:
    print("\n── Test 13: collect_local_control_perception ──")
    from runtime.substrate.perception import collect_local_control_perception

    result = collect_local_control_perception()
    _report("returns a list", isinstance(result, list))
    _report(
        "all items are PerceptionRecord",
        all(isinstance(r, PerceptionRecord) for r in result),
    )


# ─── Test 14: live session collector runs ────────────────────────────────────


def test_collect_live_session_perception() -> None:
    print("\n── Test 14: collect_live_session_perception ──")
    from runtime.substrate.perception import collect_live_session_perception

    result = collect_live_session_perception()
    _report("returns a list", isinstance(result, list))
    _report(
        "all items are PerceptionRecord",
        all(isinstance(r, PerceptionRecord) for r in result),
    )


# ─── Run ───────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("Perception Smoke Tests")
    print("=" * 60)

    test_perception_record_create()
    test_perception_record_roundtrip()
    test_fingerprint_stable()
    test_perception_store_put_get()
    test_perception_store_persistence()
    test_has_fingerprint()
    test_collect_task_perception()
    test_collect_all_perceptions()
    test_severity_filter()
    test_prune_oldest_info()
    test_new_sources_in_enum()
    test_collect_station_presence_perception()
    test_collect_local_control_perception()
    test_collect_live_session_perception()

    print("\n" + "=" * 60)
    print(f"Results: {_PASS} passed, {_FAIL} failed")
    if _FAIL:
        sys.exit(1)
    else:
        print("All smoke tests passed.")
