"""Tests for runtime.memory_fabric — unified append-only memory."""

import sys

sys.path.insert(0, "/opt/OS")

from umh.runtime_engine.memory_fabric import (
    AGG_ALPHA,
    MAX_ENTRIES,
    MIN_ENTRIES_FOR_AGG,
    AggregationResult,
    EntryType,
    FabricSnapshot,
    MemoryEntry,
    MemoryFabric,
    NO_AGGREGATION,
    NO_SNAPSHOT,
    get_memory_fabric,
)

_pass = 0
_fail = 0


def check(cond: bool, label: str) -> None:
    global _pass, _fail
    if cond:
        _pass += 1
    else:
        _fail += 1
        print(f"  FAIL: {label}")


def section(name: str) -> None:
    print(f"\n{'─' * 60}")
    print(f"  {name}")
    print(f"{'─' * 60}")


# ─────────────────────────────────────────────────────────────
# Section 1: MemoryEntry construction
# ─────────────────────────────────────────────────────────────
section("1. MemoryEntry construction")
e1 = MemoryEntry(
    entry_type=EntryType.STRATEGY_OUTCOME,
    turn=1,
    features={"strategy": "direct", "quality": 0.8},
    outcome=0.75,
    source="strategy_memory",
)
check(e1.entry_type == EntryType.STRATEGY_OUTCOME, "entry_type")
check(e1.turn == 1, "turn")
check(e1.features["strategy"] == "direct", "features.strategy")
check(e1.outcome == 0.75, "outcome")
check(e1.source == "strategy_memory", "source")
check(e1.entry_id == "", "default entry_id")

# ─────────────────────────────────────────────────────────────
# Section 2: MemoryEntry is frozen
# ─────────────────────────────────────────────────────────────
section("2. MemoryEntry is frozen")
try:
    e1.outcome = 0.5  # type: ignore[misc]
    check(False, "should raise")
except AttributeError:
    check(True, "frozen dataclass")

# ─────────────────────────────────────────────────────────────
# Section 3: MemoryEntry to_dict
# ─────────────────────────────────────────────────────────────
section("3. MemoryEntry to_dict")
d1 = e1.to_dict()
check(d1["entry_type"] == "strategy_outcome", "type serialized")
check(d1["turn"] == 1, "turn serialized")
check(d1["outcome"] == 0.75, "outcome serialized")
check(d1["source"] == "strategy_memory", "source serialized")

# ─────────────────────────────────────────────────────────────
# Section 4: EntryType enum values
# ─────────────────────────────────────────────────────────────
section("4. EntryType enum values")
check(EntryType.STRATEGY_OUTCOME.value == "strategy_outcome", "strategy_outcome")
check(EntryType.STATE_OBSERVATION.value == "state_observation", "state_observation")
check(EntryType.SIGNAL_OUTCOME.value == "signal_outcome", "signal_outcome")
check(EntryType.DIRECTIVE_EVENT.value == "directive_event", "directive_event")
check(EntryType.PLAN_OUTCOME.value == "plan_outcome", "plan_outcome")
check(EntryType.CREDIT_EVENT.value == "credit_event", "credit_event")

# ─────────────────────────────────────────────────────────────
# Section 5: MemoryFabric — basic recording
# ─────────────────────────────────────────────────────────────
section("5. Basic recording")
mf = MemoryFabric()
check(mf.entry_count == 0, "starts empty")
eid = mf.record(e1)
check(mf.entry_count == 1, "one entry after record")
check(eid.startswith("mf_"), "auto-assigned entry_id")

# ─────────────────────────────────────────────────────────────
# Section 6: Recording with explicit entry_id
# ─────────────────────────────────────────────────────────────
section("6. Explicit entry_id")
e2 = MemoryEntry(
    entry_type=EntryType.PLAN_OUTCOME,
    turn=2,
    features={"plan_id": "p1", "step": "s1"},
    outcome=0.6,
    entry_id="custom_id",
)
eid2 = mf.record(e2)
check(eid2 == "custom_id", "uses provided entry_id")
check(mf.entry_count == 2, "two entries")

# ─────────────────────────────────────────────────────────────
# Section 7: Recording preserves entry immutability
# ─────────────────────────────────────────────────────────────
section("7. Entry immutability after record")
results = mf.query()
check(len(results) == 2, "query returns all entries")
try:
    results[0].outcome = 999.0  # type: ignore[misc]
    check(False, "should raise")
except AttributeError:
    check(True, "entries stay frozen")

# ─────────────────────────────────────────────────────────────
# Section 8: Memory cap enforcement — FIFO eviction
# ─────────────────────────────────────────────────────────────
section("8. Memory cap — FIFO eviction")
small_mf = MemoryFabric(max_entries=5)
for i in range(10):
    small_mf.record(
        MemoryEntry(
            entry_type=EntryType.STRATEGY_OUTCOME,
            turn=i,
            features={"idx": float(i)},
            outcome=float(i) / 10,
        )
    )
check(small_mf.entry_count == 5, "capped at max_entries")
remaining = small_mf.query()
check(remaining[0].turn == 5, "oldest surviving is turn 5")
check(remaining[-1].turn == 9, "newest is turn 9")

# ─────────────────────────────────────────────────────────────
# Section 9: Query by entry_type
# ─────────────────────────────────────────────────────────────
section("9. Query by entry_type")
mf2 = MemoryFabric()
mf2.record(
    MemoryEntry(
        entry_type=EntryType.STRATEGY_OUTCOME,
        turn=1,
        features={"s": "a"},
        outcome=0.5,
    )
)
mf2.record(
    MemoryEntry(
        entry_type=EntryType.PLAN_OUTCOME,
        turn=2,
        features={"p": "b"},
        outcome=0.6,
    )
)
mf2.record(
    MemoryEntry(
        entry_type=EntryType.STRATEGY_OUTCOME,
        turn=3,
        features={"s": "c"},
        outcome=0.7,
    )
)
strat_only = mf2.query(entry_type=EntryType.STRATEGY_OUTCOME)
check(len(strat_only) == 2, "filters by type")
plan_only = mf2.query(entry_type=EntryType.PLAN_OUTCOME)
check(len(plan_only) == 1, "plan filter")

# ─────────────────────────────────────────────────────────────
# Section 10: Query by source
# ─────────────────────────────────────────────────────────────
section("10. Query by source")
mf3 = MemoryFabric()
mf3.record(
    MemoryEntry(
        entry_type=EntryType.SIGNAL_OUTCOME,
        turn=1,
        features={"goal": 0.8},
        outcome=0.7,
        source="influence_scoring",
    )
)
mf3.record(
    MemoryEntry(
        entry_type=EntryType.SIGNAL_OUTCOME,
        turn=2,
        features={"goal": 0.9},
        outcome=0.8,
        source="meta_weight",
    )
)
inf_only = mf3.query(source="influence_scoring")
check(len(inf_only) == 1, "filter by source")
check(inf_only[0].features["goal"] == 0.8, "correct entry returned")

# ─────────────────────────────────────────────────────────────
# Section 11: Query by turn range
# ─────────────────────────────────────────────────────────────
section("11. Query by turn range")
mf4 = MemoryFabric()
for i in range(10):
    mf4.record(
        MemoryEntry(
            entry_type=EntryType.STRATEGY_OUTCOME,
            turn=i,
            features={"i": float(i)},
            outcome=0.5,
        )
    )
mid = mf4.query(min_turn=3, max_turn=7)
check(len(mid) == 5, "turn range inclusive")
check(mid[0].turn == 3, "starts at min_turn")
check(mid[-1].turn == 7, "ends at max_turn")

# ─────────────────────────────────────────────────────────────
# Section 12: Query by feature_key
# ─────────────────────────────────────────────────────────────
section("12. Query by feature_key")
mf5 = MemoryFabric()
mf5.record(
    MemoryEntry(
        entry_type=EntryType.STRATEGY_OUTCOME,
        turn=1,
        features={"strategy": "direct", "quality": 0.8},
        outcome=0.7,
    )
)
mf5.record(
    MemoryEntry(
        entry_type=EntryType.STRATEGY_OUTCOME,
        turn=2,
        features={"quality": 0.6},
        outcome=0.5,
    )
)
with_strat = mf5.query(feature_key="strategy")
check(len(with_strat) == 1, "only entries with feature_key")

# ─────────────────────────────────────────────────────────────
# Section 13: Query by feature_key + feature_value
# ─────────────────────────────────────────────────────────────
section("13. Query by feature_key + feature_value")
mf6 = MemoryFabric()
mf6.record(
    MemoryEntry(
        entry_type=EntryType.STRATEGY_OUTCOME,
        turn=1,
        features={"strategy": "direct"},
        outcome=0.7,
    )
)
mf6.record(
    MemoryEntry(
        entry_type=EntryType.STRATEGY_OUTCOME,
        turn=2,
        features={"strategy": "analytical"},
        outcome=0.6,
    )
)
direct_only = mf6.query(feature_key="strategy", feature_value="direct")
check(len(direct_only) == 1, "filter by value")
check(direct_only[0].features["strategy"] == "direct", "correct value")

# ─────────────────────────────────────────────────────────────
# Section 14: Query with limit
# ─────────────────────────────────────────────────────────────
section("14. Query with limit")
mf7 = MemoryFabric()
for i in range(10):
    mf7.record(
        MemoryEntry(
            entry_type=EntryType.STRATEGY_OUTCOME,
            turn=i,
            features={"i": float(i)},
            outcome=0.5,
        )
    )
limited = mf7.query(limit=3)
check(len(limited) == 3, "respects limit")
check(limited[0].turn == 7, "returns last N entries")

# ─────────────────────────────────────────────────────────────
# Section 15: Query combined filters (AND logic)
# ─────────────────────────────────────────────────────────────
section("15. Combined filters (AND)")
mf8 = MemoryFabric()
mf8.record(
    MemoryEntry(
        entry_type=EntryType.STRATEGY_OUTCOME,
        turn=1,
        features={"strategy": "direct"},
        outcome=0.7,
        source="sm",
    )
)
mf8.record(
    MemoryEntry(
        entry_type=EntryType.STRATEGY_OUTCOME,
        turn=5,
        features={"strategy": "direct"},
        outcome=0.8,
        source="sm",
    )
)
mf8.record(
    MemoryEntry(
        entry_type=EntryType.PLAN_OUTCOME,
        turn=3,
        features={"plan": "p1"},
        outcome=0.6,
        source="sm",
    )
)
combined = mf8.query(entry_type=EntryType.STRATEGY_OUTCOME, source="sm", min_turn=2)
check(len(combined) == 1, "AND filters all apply")
check(combined[0].turn == 5, "correct entry")

# ─────────────────────────────────────────────────────────────
# Section 16: Aggregation — empty fabric
# ─────────────────────────────────────────────────────────────
section("16. Aggregation — empty fabric")
mf_empty = MemoryFabric()
agg = mf_empty.aggregate()
check(agg.total_entries == 0, "empty count")
check(agg.entries_by_type == {}, "no types")
check(agg.outcome_ema_by_type == {}, "no emas")

# ─────────────────────────────────────────────────────────────
# Section 17: Aggregation — single entry
# ─────────────────────────────────────────────────────────────
section("17. Aggregation — single entry")
mf_one = MemoryFabric()
mf_one.record(
    MemoryEntry(
        entry_type=EntryType.STRATEGY_OUTCOME,
        turn=1,
        features={"quality": 0.8},
        outcome=0.75,
    )
)
agg1 = mf_one.aggregate()
check(agg1.total_entries == 1, "one entry")
check(agg1.entries_by_type["strategy_outcome"] == 1, "type count")
check(abs(agg1.outcome_ema_by_type["strategy_outcome"] - 0.75) < 1e-6, "ema init")
check(abs(agg1.feature_emas["quality"] - 0.8) < 1e-6, "feature ema init")
check(agg1.oldest_turn == 1, "oldest")
check(agg1.newest_turn == 1, "newest")

# ─────────────────────────────────────────────────────────────
# Section 18: Aggregation — EMA computation deterministic
# ─────────────────────────────────────────────────────────────
section("18. Aggregation EMA deterministic")
mf_ema = MemoryFabric()
outcomes = [0.5, 0.6, 0.7, 0.8, 0.9]
for i, o in enumerate(outcomes):
    mf_ema.record(
        MemoryEntry(
            entry_type=EntryType.STRATEGY_OUTCOME,
            turn=i,
            features={"q": o},
            outcome=o,
        )
    )
agg_a = mf_ema.aggregate()
agg_b = mf_ema.aggregate()
check(
    agg_a.outcome_ema_by_type == agg_b.outcome_ema_by_type,
    "same result twice",
)

expected_ema = outcomes[0]
for o in outcomes[1:]:
    expected_ema = AGG_ALPHA * o + (1.0 - AGG_ALPHA) * expected_ema
check(
    abs(agg_a.outcome_ema_by_type["strategy_outcome"] - expected_ema) < 1e-6,
    "correct EMA formula",
)

# ─────────────────────────────────────────────────────────────
# Section 19: Aggregation — multi-type counting
# ─────────────────────────────────────────────────────────────
section("19. Aggregation multi-type")
mf_mt = MemoryFabric()
for i in range(3):
    mf_mt.record(
        MemoryEntry(
            entry_type=EntryType.STRATEGY_OUTCOME,
            turn=i,
            features={"x": 1.0},
            outcome=0.5,
        )
    )
for i in range(2):
    mf_mt.record(
        MemoryEntry(
            entry_type=EntryType.PLAN_OUTCOME,
            turn=i + 3,
            features={"x": 2.0},
            outcome=0.6,
        )
    )
agg_mt = mf_mt.aggregate()
check(agg_mt.total_entries == 5, "total count")
check(agg_mt.entries_by_type["strategy_outcome"] == 3, "strat count")
check(agg_mt.entries_by_type["plan_outcome"] == 2, "plan count")

# ─────────────────────────────────────────────────────────────
# Section 20: Aggregation — recent_outcome_trend
# ─────────────────────────────────────────────────────────────
section("20. Aggregation — trend")
mf_trend = MemoryFabric()
for i in range(6):
    mf_trend.record(
        MemoryEntry(
            entry_type=EntryType.STRATEGY_OUTCOME,
            turn=i,
            features={},
            outcome=float(i) / 10,
        )
    )
agg_trend = mf_trend.aggregate()
check(agg_trend.recent_outcome_trend > 0, "positive trend")

mf_neg = MemoryFabric()
for i in range(6):
    mf_neg.record(
        MemoryEntry(
            entry_type=EntryType.STRATEGY_OUTCOME,
            turn=i,
            features={},
            outcome=1.0 - float(i) / 10,
        )
    )
agg_neg = mf_neg.aggregate()
check(agg_neg.recent_outcome_trend < 0, "negative trend")

# ─────────────────────────────────────────────────────────────
# Section 21: Aggregation — filter by type
# ─────────────────────────────────────────────────────────────
section("21. Aggregation filtered by type")
agg_strat = mf_mt.aggregate(entry_type=EntryType.STRATEGY_OUTCOME)
check(agg_strat.total_entries == 3, "only strategy entries")
check("plan_outcome" not in agg_strat.entries_by_type, "no plan entries")

# ─────────────────────────────────────────────────────────────
# Section 22: Aggregation — filter by min_turn
# ─────────────────────────────────────────────────────────────
section("22. Aggregation filtered by min_turn")
agg_recent = mf_mt.aggregate(min_turn=3)
check(agg_recent.total_entries == 2, "only recent entries")
check(agg_recent.oldest_turn == 3, "starts at turn 3")

# ─────────────────────────────────────────────────────────────
# Section 23: get_outcome_ema — basic
# ─────────────────────────────────────────────────────────────
section("23. get_outcome_ema basic")
mf_oema = MemoryFabric()
for i in range(5):
    mf_oema.record(
        MemoryEntry(
            entry_type=EntryType.STRATEGY_OUTCOME,
            turn=i,
            features={"strategy": "direct"},
            outcome=0.8,
        )
    )
ema_val = mf_oema.get_outcome_ema(EntryType.STRATEGY_OUTCOME)
check(ema_val is not None, "enough observations")
check(abs(ema_val - 0.8) < 1e-6, "constant outcome → EMA = outcome")

# ─────────────────────────────────────────────────────────────
# Section 24: get_outcome_ema — below threshold
# ─────────────────────────────────────────────────────────────
section("24. get_outcome_ema below MIN_ENTRIES_FOR_AGG")
mf_few = MemoryFabric()
mf_few.record(
    MemoryEntry(
        entry_type=EntryType.STRATEGY_OUTCOME,
        turn=1,
        features={},
        outcome=0.5,
    )
)
check(
    mf_few.get_outcome_ema(EntryType.STRATEGY_OUTCOME) is None,
    "None when too few",
)

# ─────────────────────────────────────────────────────────────
# Section 25: get_outcome_ema — with feature filter
# ─────────────────────────────────────────────────────────────
section("25. get_outcome_ema with feature filter")
mf_feat = MemoryFabric()
for i in range(5):
    mf_feat.record(
        MemoryEntry(
            entry_type=EntryType.STRATEGY_OUTCOME,
            turn=i,
            features={"strategy": "direct"},
            outcome=0.9,
        )
    )
for i in range(5):
    mf_feat.record(
        MemoryEntry(
            entry_type=EntryType.STRATEGY_OUTCOME,
            turn=i + 5,
            features={"strategy": "analytical"},
            outcome=0.3,
        )
    )
ema_direct = mf_feat.get_outcome_ema(
    EntryType.STRATEGY_OUTCOME, feature_key="strategy", feature_value="direct"
)
ema_analytical = mf_feat.get_outcome_ema(
    EntryType.STRATEGY_OUTCOME, feature_key="strategy", feature_value="analytical"
)
check(ema_direct is not None, "direct has enough")
check(ema_analytical is not None, "analytical has enough")
check(ema_direct > ema_analytical, "direct > analytical")

# ─────────────────────────────────────────────────────────────
# Section 26: FabricSnapshot — turn tracking
# ─────────────────────────────────────────────────────────────
section("26. FabricSnapshot turn tracking")
mf_snap = MemoryFabric()
mf_snap.record(
    MemoryEntry(
        entry_type=EntryType.STRATEGY_OUTCOME,
        turn=1,
        features={"s": "a"},
        outcome=0.5,
    )
)
mf_snap.query(entry_type=EntryType.STRATEGY_OUTCOME)
snap = mf_snap.flush_turn_tracking()
check(len(snap.entries_written) == 1, "one write tracked")
check(len(snap.queries_used) == 1, "one query tracked")
check(isinstance(snap.aggregation_summary, dict), "summary is dict")

# ─────────────────────────────────────────────────────────────
# Section 27: FabricSnapshot — flush resets tracking
# ─────────────────────────────────────────────────────────────
section("27. Flush resets tracking")
snap2 = mf_snap.flush_turn_tracking()
check(len(snap2.entries_written) == 0, "writes reset")
check(len(snap2.queries_used) == 0, "queries reset")

# ─────────────────────────────────────────────────────────────
# Section 28: Snapshot/restore persistence
# ─────────────────────────────────────────────────────────────
section("28. Snapshot/restore")
mf_persist = MemoryFabric()
for i in range(5):
    mf_persist.record(
        MemoryEntry(
            entry_type=EntryType.STRATEGY_OUTCOME,
            turn=i,
            features={"q": float(i)},
            outcome=float(i) / 10,
        )
    )
data = mf_persist.snapshot()
check(data["entry_count"] == 5, "snapshot count")

mf_restored = MemoryFabric()
mf_restored.restore(data)
check(mf_restored.entry_count == 5, "restored count")
restored_entries = mf_restored.query()
check(restored_entries[0].turn == 0, "restored first entry")
check(restored_entries[-1].turn == 4, "restored last entry")

# ─────────────────────────────────────────────────────────────
# Section 29: Reset clears everything
# ─────────────────────────────────────────────────────────────
section("29. Reset")
mf_reset = MemoryFabric()
for i in range(5):
    mf_reset.record(
        MemoryEntry(
            entry_type=EntryType.STRATEGY_OUTCOME,
            turn=i,
            features={},
            outcome=0.5,
        )
    )
mf_reset.reset()
check(mf_reset.entry_count == 0, "entries cleared")
check(len(mf_reset.query()) == 0, "query returns nothing")

# ─────────────────────────────────────────────────────────────
# Section 30: Singleton accessor
# ─────────────────────────────────────────────────────────────
section("30. Singleton accessor")
import umh.runtime_engine.memory_fabric as _mf_mod

_mf_mod._fabric = None
f1 = get_memory_fabric()
f2 = get_memory_fabric()
check(f1 is f2, "same instance")
_mf_mod._fabric = None

# ─────────────────────────────────────────────────────────────
# Section 31: NO_AGGREGATION sentinel
# ─────────────────────────────────────────────────────────────
section("31. NO_AGGREGATION sentinel")
check(NO_AGGREGATION.total_entries == 0, "zero entries")
check(NO_AGGREGATION.entries_by_type == {}, "empty types")
check(NO_AGGREGATION.recent_outcome_trend == 0.0, "zero trend")

# ─────────────────────────────────────────────────────────────
# Section 32: NO_SNAPSHOT sentinel
# ─────────────────────────────────────────────────────────────
section("32. NO_SNAPSHOT sentinel")
check(NO_SNAPSHOT.entries_written == (), "empty writes")
check(NO_SNAPSHOT.queries_used == (), "empty queries")
check(NO_SNAPSHOT.aggregation_summary == {}, "empty summary")

# ─────────────────────────────────────────────────────────────
# Section 33: AggregationResult.to_dict
# ─────────────────────────────────────────────────────────────
section("33. AggregationResult.to_dict")
ar = AggregationResult(
    total_entries=10,
    entries_by_type={"strategy_outcome": 7, "plan_outcome": 3},
    outcome_ema_by_type={"strategy_outcome": 0.7777, "plan_outcome": 0.6666},
    feature_emas={"quality": 0.8888},
    recent_outcome_trend=0.1234,
    oldest_turn=0,
    newest_turn=9,
)
ard = ar.to_dict()
check(ard["total_entries"] == 10, "total in dict")
check(ard["outcome_ema_by_type"]["strategy_outcome"] == 0.7777, "ema rounded")
check(ard["feature_emas"]["quality"] == 0.8888, "feature ema rounded")

# ─────────────────────────────────────────────────────────────
# Section 34: FabricSnapshot.to_dict
# ─────────────────────────────────────────────────────────────
section("34. FabricSnapshot.to_dict")
fs = FabricSnapshot(
    entries_written=("mf_1", "mf_2"),
    queries_used=("q1",),
    aggregation_summary={"total_entries": 5},
)
fsd = fs.to_dict()
check(fsd["entries_written"] == ["mf_1", "mf_2"], "writes serialized")
check(fsd["queries_used"] == ["q1"], "queries serialized")
check(fsd["aggregation_summary"]["total_entries"] == 5, "summary serialized")

# ─────────────────────────────────────────────────────────────
# Section 35: Feature EMA ignores non-numeric features
# ─────────────────────────────────────────────────────────────
section("35. Non-numeric features ignored in aggregation")
mf_str = MemoryFabric()
mf_str.record(
    MemoryEntry(
        entry_type=EntryType.STRATEGY_OUTCOME,
        turn=1,
        features={"strategy": "direct", "quality": 0.8},
        outcome=0.7,
    )
)
agg_str = mf_str.aggregate()
check("strategy" not in agg_str.feature_emas, "string feature excluded")
check("quality" in agg_str.feature_emas, "numeric feature included")

# ─────────────────────────────────────────────────────────────
# Section 36: All 6 entry types can be recorded and queried
# ─────────────────────────────────────────────────────────────
section("36. All 6 entry types recordable/queryable")
mf_all = MemoryFabric()
for et in EntryType:
    mf_all.record(
        MemoryEntry(
            entry_type=et,
            turn=1,
            features={"type": et.value},
            outcome=0.5,
        )
    )
check(mf_all.entry_count == 6, "all 6 types recorded")
for et in EntryType:
    found = mf_all.query(entry_type=et)
    check(len(found) == 1, f"query returns {et.value}")

# ─────────────────────────────────────────────────────────────
# Section 37: Large-scale determinism
# ─────────────────────────────────────────────────────────────
section("37. Large-scale determinism")
mf_det_a = MemoryFabric()
mf_det_b = MemoryFabric()
for i in range(100):
    e = MemoryEntry(
        entry_type=EntryType.STRATEGY_OUTCOME if i % 2 == 0 else EntryType.PLAN_OUTCOME,
        turn=i,
        features={"val": float(i) * 0.01},
        outcome=float(i % 10) / 10,
    )
    mf_det_a.record(e)
    mf_det_b.record(e)
agg_det_a = mf_det_a.aggregate()
agg_det_b = mf_det_b.aggregate()
check(agg_det_a.to_dict() == agg_det_b.to_dict(), "identical aggregation")

# ─────────────────────────────────────────────────────────────
# Section 38: DecisionTrace fields exist
# ─────────────────────────────────────────────────────────────
section("38. DecisionTrace memory fabric fields")
from umh.runtime_engine.decision_trace import DecisionTrace, build_trace

t = build_trace(
    turn_id=1,
    memory_entries_written=("mf_1", "mf_2"),
    memory_queries_used=("q_type=strategy",),
    memory_aggregation_summary={"total_entries": 10},
)
check(t.memory_entries_written == ("mf_1", "mf_2"), "entries_written on trace")
check(t.memory_queries_used == ("q_type=strategy",), "queries_used on trace")
check(
    t.memory_aggregation_summary == {"total_entries": 10},
    "aggregation_summary on trace",
)

# ─────────────────────────────────────────────────────────────
# Section 39: DecisionTrace to_dict includes memory fields
# ─────────────────────────────────────────────────────────────
section("39. DecisionTrace to_dict includes memory fields")
td = t.to_dict()
check("memory_entries_written" in td, "entries_written serialized")
check("memory_queries_used" in td, "queries_used serialized")
check("memory_aggregation_summary" in td, "aggregation_summary serialized")

# ─────────────────────────────────────────────────────────────
# Section 40: DecisionTrace omits None memory fields
# ─────────────────────────────────────────────────────────────
section("40. DecisionTrace omits None memory fields")
t_none = build_trace(turn_id=2)
td_none = t_none.to_dict()
check("memory_entries_written" not in td_none, "no entries_written when None")
check("memory_queries_used" not in td_none, "no queries_used when None")
check("memory_aggregation_summary" not in td_none, "no summary when None")

# ─────────────────────────────────────────────────────────────
# Section 41: Subsystem reads — strategy EMA from fabric
# ─────────────────────────────────────────────────────────────
section("41. Subsystem read — strategy EMA")
mf_sub = MemoryFabric()
strategies = ["direct", "analytical", "creative"]
for turn in range(10):
    for s in strategies:
        outcome = 0.9 if s == "direct" else 0.3
        mf_sub.record(
            MemoryEntry(
                entry_type=EntryType.STRATEGY_OUTCOME,
                turn=turn,
                features={"strategy": s, "quality": outcome},
                outcome=outcome,
            )
        )
ema_d = mf_sub.get_outcome_ema(
    EntryType.STRATEGY_OUTCOME, feature_key="strategy", feature_value="direct"
)
ema_a = mf_sub.get_outcome_ema(
    EntryType.STRATEGY_OUTCOME, feature_key="strategy", feature_value="analytical"
)
check(ema_d is not None and ema_d > 0.5, "direct EMA high")
check(ema_a is not None and ema_a < 0.5, "analytical EMA low")

# ─────────────────────────────────────────────────────────────
# Section 42: Subsystem reads — signal outcome aggregation
# ─────────────────────────────────────────────────────────────
section("42. Subsystem read — signal aggregation")
mf_sig = MemoryFabric()
for i in range(10):
    mf_sig.record(
        MemoryEntry(
            entry_type=EntryType.SIGNAL_OUTCOME,
            turn=i,
            features={"goal": 0.8, "plan": 0.6, "strategy": 0.7},
            outcome=0.75,
        )
    )
agg_sig = mf_sig.aggregate(entry_type=EntryType.SIGNAL_OUTCOME)
check(agg_sig.total_entries == 10, "all signal entries counted")
check(abs(agg_sig.feature_emas["goal"] - 0.8) < 1e-6, "goal feature constant")
check(abs(agg_sig.feature_emas["plan"] - 0.6) < 1e-6, "plan feature constant")

# ─────────────────────────────────────────────────────────────
# Section 43: Subsystem reads — directive lifecycle
# ─────────────────────────────────────────────────────────────
section("43. Subsystem read — directive lifecycle")
mf_dir = MemoryFabric()
mf_dir.record(
    MemoryEntry(
        entry_type=EntryType.DIRECTIVE_EVENT,
        turn=1,
        features={
            "directive_id": "recover_t1",
            "directive_type": "recover",
            "priority": 0.9,
        },
        outcome=0.4,
        source="directive_engine",
    )
)
mf_dir.record(
    MemoryEntry(
        entry_type=EntryType.DIRECTIVE_EVENT,
        turn=5,
        features={
            "directive_id": "exploit_t5",
            "directive_type": "exploit",
            "priority": 0.8,
        },
        outcome=0.7,
        source="directive_engine",
    )
)
recover_events = mf_dir.query(
    entry_type=EntryType.DIRECTIVE_EVENT,
    feature_key="directive_type",
    feature_value="recover",
)
check(len(recover_events) == 1, "filter directives by type")
check(recover_events[0].features["directive_id"] == "recover_t1", "correct directive")

# ─────────────────────────────────────────────────────────────
# Section 44: Subsystem reads — plan outcome history
# ─────────────────────────────────────────────────────────────
section("44. Subsystem read — plan outcome history")
mf_plan = MemoryFabric()
for i in range(5):
    mf_plan.record(
        MemoryEntry(
            entry_type=EntryType.PLAN_OUTCOME,
            turn=i,
            features={"plan_id": "p1", "step": f"s{i}", "goal_id": "g1"},
            outcome=0.5 + i * 0.1,
        )
    )
plan_hist = mf_plan.query(
    entry_type=EntryType.PLAN_OUTCOME,
    feature_key="plan_id",
    feature_value="p1",
)
check(len(plan_hist) == 5, "all plan entries for p1")
plan_ema = mf_plan.get_outcome_ema(
    EntryType.PLAN_OUTCOME, feature_key="plan_id", feature_value="p1"
)
check(plan_ema is not None, "enough for EMA")
check(plan_ema > 0.5, "trending up")

# ─────────────────────────────────────────────────────────────
# Section 45: Subsystem reads — credit events
# ─────────────────────────────────────────────────────────────
section("45. Subsystem read — credit events")
mf_credit = MemoryFabric()
for i in range(4):
    mf_credit.record(
        MemoryEntry(
            entry_type=EntryType.CREDIT_EVENT,
            turn=i,
            features={"reason": "multi_signal", "total_weight": 0.8 + i * 0.05},
            outcome=0.7,
        )
    )
credit_agg = mf_credit.aggregate(entry_type=EntryType.CREDIT_EVENT)
check(credit_agg.total_entries == 4, "all credit events")
check("total_weight" in credit_agg.feature_emas, "weight feature tracked")

# ─────────────────────────────────────────────────────────────
# Section 46: Constants are accessible
# ─────────────────────────────────────────────────────────────
section("46. Constants")
check(MAX_ENTRIES == 500, "MAX_ENTRIES = 500")
check(AGG_ALPHA == 0.20, "AGG_ALPHA = 0.20")
check(MIN_ENTRIES_FOR_AGG == 3, "MIN_ENTRIES_FOR_AGG = 3")

# ─────────────────────────────────────────────────────────────
# Section 47: No randomness in module
# ─────────────────────────────────────────────────────────────
section("47. No randomness")
import re

with open("/opt/OS/eos/memory_fabric.py") as f:
    src = f.read()
check(not re.search(r"\bimport\s+random\b", src), "no random import")
check("shuffle" not in src, "no shuffle")

# ─────────────────────────────────────────────────────────────
# Section 48: No LLM calls
# ─────────────────────────────────────────────────────────────
section("48. No LLM calls")
check("anthropic" not in src.lower(), "no anthropic")
check("openai" not in src.lower(), "no openai")
check("call_with_fallback" not in src, "no LLM router")

# ─────────────────────────────────────────────────────────────
# Section 49: Regression — DecisionTrace backward compat
# ─────────────────────────────────────────────────────────────
section("49. DecisionTrace backward compat")
t_old = build_trace(turn_id=99)
check(t_old.memory_entries_written is None, "default None")
check(t_old.memory_queries_used is None, "default None")
check(t_old.memory_aggregation_summary is None, "default None")
check(t_old.quality_score == 0.0, "existing fields unchanged")

# ─────────────────────────────────────────────────────────────
# Section 50: Cap at exact boundary
# ─────────────────────────────────────────────────────────────
section("50. Cap at exact boundary")
mf_exact = MemoryFabric(max_entries=3)
for i in range(3):
    mf_exact.record(
        MemoryEntry(
            entry_type=EntryType.STRATEGY_OUTCOME,
            turn=i,
            features={},
            outcome=0.5,
        )
    )
check(mf_exact.entry_count == 3, "at capacity, not over")
mf_exact.record(
    MemoryEntry(
        entry_type=EntryType.STRATEGY_OUTCOME,
        turn=3,
        features={},
        outcome=0.5,
    )
)
check(mf_exact.entry_count == 3, "still at capacity after overshoot")
check(mf_exact.query()[0].turn == 1, "first evicted")

# ─────────────────────────────────────────────────────────────
# SUMMARY
# ─────────────────────────────────────────────────────────────

print(f"\n{'═' * 60}")
print(f"  RESULTS: {_pass} passed, {_fail} failed")
print(f"{'═' * 60}")
if _fail > 0:
    raise SystemExit(1)
