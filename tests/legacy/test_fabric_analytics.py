"""Tests for runtime.fabric_analytics — read-only intelligence over MemoryFabric."""

import sys
import time

sys.path.insert(0, "/opt/OS")

from umh.runtime_engine.memory_fabric import EntryType, MemoryEntry, MemoryFabric
from umh.runtime_engine.fabric_analytics import (
    EMA_ALPHA,
    MIN_ENTRIES,
    DirectiveSuccessRate,
    PlanStructureSuccess,
    PolicyOutcomeDistribution,
    SignalCorrelations,
    StrategyStatePerformance,
    compute_analytics_summary,
    get_directive_success_rate,
    get_plan_structure_success,
    get_policy_outcome_distribution,
    get_signal_correlations,
    get_strategy_performance_by_state,
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


def make_fabric_with_data() -> MemoryFabric:
    """Create a fabric pre-loaded with representative test data."""
    mf = MemoryFabric()

    for turn in range(20):
        mf.record(
            MemoryEntry(
                entry_type=EntryType.STRATEGY_OUTCOME,
                turn=turn,
                features={
                    "strategy": "direct" if turn % 2 == 0 else "analytical",
                    "quality": 0.8 if turn % 2 == 0 else 0.4,
                },
                outcome=0.8 if turn % 2 == 0 else 0.4,
                source="strategy_memory",
            )
        )

        mf.record(
            MemoryEntry(
                entry_type=EntryType.STATE_OBSERVATION,
                turn=turn,
                features={
                    "state_id": f"s{turn}",
                    "cluster": "cluster_a" if turn < 10 else "cluster_b",
                    "similarity": 0.85,
                },
                outcome=0.7,
                source="world_state",
            )
        )

        if turn % 3 == 0:
            mf.record(
                MemoryEntry(
                    entry_type=EntryType.DIRECTIVE_EVENT,
                    turn=turn,
                    features={
                        "directive_id": f"d_{turn}",
                        "directive_type": "recover" if turn < 10 else "exploit",
                        "priority": 0.9,
                        "confidence": 0.7,
                    },
                    outcome=0.3 if turn < 10 else 0.8,
                    source="directive_engine",
                )
            )

        mf.record(
            MemoryEntry(
                entry_type=EntryType.SIGNAL_OUTCOME,
                turn=turn,
                features={
                    "goal": 0.7 + turn * 0.01,
                    "plan": 0.5,
                    "strategy": 0.6,
                },
                outcome=0.6 + turn * 0.01,
                source="influence_scoring",
            )
        )

        if turn % 4 == 0:
            mf.record(
                MemoryEntry(
                    entry_type=EntryType.PLAN_OUTCOME,
                    turn=turn,
                    features={
                        "plan_id": "plan_alpha" if turn < 12 else "plan_beta",
                        "step": f"step_{turn}",
                        "goal_id": "g1" if turn < 12 else "g2",
                    },
                    outcome=0.5 + turn * 0.02,
                    source="plan_engine",
                )
            )

        if turn % 5 == 0:
            mf.record(
                MemoryEntry(
                    entry_type=EntryType.CREDIT_EVENT,
                    turn=turn,
                    features={"reason": "multi_signal", "total_weight": 0.85},
                    outcome=0.7,
                    source="causal_credit",
                )
            )

    return mf


# ─────────────────────────────────────────────────────────────
# Section 1: get_strategy_performance_by_state — empty fabric
# ─────────────────────────────────────────────────────────────
section("1. Strategy perf — empty fabric")
empty = MemoryFabric()
sp_empty = get_strategy_performance_by_state(empty)
check(sp_empty.total_entries == 0, "zero entries")
check(sp_empty.by_cluster == {}, "no clusters")
check(sp_empty.by_strategy == {}, "no strategies")

# ─────────────────────────────────────────────────────────────
# Section 2: get_strategy_performance_by_state — basic
# ─────────────────────────────────────────────────────────────
section("2. Strategy perf — basic")
mf = make_fabric_with_data()
sp = get_strategy_performance_by_state(mf)
check(sp.total_entries == 20, "20 strategy entries")
check("direct" in sp.by_strategy, "direct tracked")
check("analytical" in sp.by_strategy, "analytical tracked")
check(sp.by_strategy["direct"] > sp.by_strategy["analytical"], "direct > analytical")

# ─────────────────────────────────────────────────────────────
# Section 3: Strategy perf — cluster grouping
# ─────────────────────────────────────────────────────────────
section("3. Strategy perf — cluster grouping")
check("cluster_a" in sp.by_cluster, "cluster_a present")
check("cluster_b" in sp.by_cluster, "cluster_b present")
check("direct" in sp.by_cluster["cluster_a"], "direct in cluster_a")

# ─────────────────────────────────────────────────────────────
# Section 4: Strategy perf — to_dict serializable
# ─────────────────────────────────────────────────────────────
section("4. Strategy perf — to_dict")
spd = sp.to_dict()
check("by_cluster" in spd, "by_cluster in dict")
check("by_strategy" in spd, "by_strategy in dict")
check("total_entries" in spd, "total_entries in dict")
check(isinstance(spd["by_cluster"]["cluster_a"]["direct"], float), "rounded float")

# ─────────────────────────────────────────────────────────────
# Section 5: Strategy perf — min_turn filter
# ─────────────────────────────────────────────────────────────
section("5. Strategy perf — min_turn")
sp_recent = get_strategy_performance_by_state(mf, min_turn=15)
check(sp_recent.total_entries == 5, "only recent turns")

# ─────────────────────────────────────────────────────────────
# Section 6: Strategy perf — deterministic
# ─────────────────────────────────────────────────────────────
section("6. Strategy perf — deterministic")
sp_a = get_strategy_performance_by_state(mf)
sp_b = get_strategy_performance_by_state(mf)
check(sp_a.to_dict() == sp_b.to_dict(), "same result twice")

# ─────────────────────────────────────────────────────────────
# Section 7: get_policy_outcome_distribution — empty
# ─────────────────────────────────────────────────────────────
section("7. Policy distribution — empty")
pd_empty = get_policy_outcome_distribution(empty)
check(pd_empty.total_entries == 0, "zero entries")
check(pd_empty.by_policy == {}, "no policies")

# ─────────────────────────────────────────────────────────────
# Section 8: get_policy_outcome_distribution — basic
# ─────────────────────────────────────────────────────────────
section("8. Policy distribution — basic")
pd = get_policy_outcome_distribution(mf)
check(pd.total_entries == 20, "20 strategy entries correlate")
check(len(pd.by_policy) >= 1, "at least one policy group")

# ─────────────────────────────────────────────────────────────
# Section 9: Policy distribution — stats structure
# ─────────────────────────────────────────────────────────────
section("9. Policy distribution — stats")
for p, stats in pd.by_policy.items():
    check("outcome_ema" in stats, f"{p} has outcome_ema")
    check("count" in stats, f"{p} has count")
    check("avg_outcome" in stats, f"{p} has avg_outcome")
    check(stats["count"] > 0, f"{p} count > 0")
    break

# ─────────────────────────────────────────────────────────────
# Section 10: Policy distribution — to_dict
# ─────────────────────────────────────────────────────────────
section("10. Policy distribution — to_dict")
pdd = pd.to_dict()
check("by_policy" in pdd, "by_policy in dict")
check("total_entries" in pdd, "total_entries in dict")

# ─────────────────────────────────────────────────────────────
# Section 11: Policy distribution — deterministic
# ─────────────────────────────────────────────────────────────
section("11. Policy distribution — deterministic")
pd_a = get_policy_outcome_distribution(mf)
pd_b = get_policy_outcome_distribution(mf)
check(pd_a.to_dict() == pd_b.to_dict(), "same result twice")

# ─────────────────────────────────────────────────────────────
# Section 12: get_directive_success_rate — empty
# ─────────────────────────────────────────────────────────────
section("12. Directive success — empty")
ds_empty = get_directive_success_rate(empty)
check(ds_empty.total_entries == 0, "zero entries")
check(ds_empty.by_type == {}, "no types")

# ─────────────────────────────────────────────────────────────
# Section 13: get_directive_success_rate — basic
# ─────────────────────────────────────────────────────────────
section("13. Directive success — basic")
ds = get_directive_success_rate(mf)
check(ds.total_entries > 0, "has entries")
check("recover" in ds.by_type, "recover tracked")
check("exploit" in ds.by_type, "exploit tracked")

# ─────────────────────────────────────────────────────────────
# Section 14: Directive success — rates correct
# ─────────────────────────────────────────────────────────────
section("14. Directive success — rates")
recover = ds.by_type["recover"]
exploit = ds.by_type["exploit"]
check(
    recover["success_rate"] < exploit["success_rate"],
    "recover < exploit (recover outcomes=0.3, exploit=0.8)",
)
check(recover["count"] > 0, "recover has entries")
check(exploit["count"] > 0, "exploit has entries")

# ─────────────────────────────────────────────────────────────
# Section 15: Directive success — custom threshold
# ─────────────────────────────────────────────────────────────
section("15. Directive success — custom threshold")
ds_high = get_directive_success_rate(mf, success_threshold=0.9)
for dt, stats in ds_high.by_type.items():
    check(
        stats["success_rate"] <= 1.0,
        f"{dt} rate <= 1.0 at high threshold",
    )

# ─────────────────────────────────────────────────────────────
# Section 16: Directive success — to_dict
# ─────────────────────────────────────────────────────────────
section("16. Directive success — to_dict")
dsd = ds.to_dict()
check("by_type" in dsd, "by_type in dict")
check("total_entries" in dsd, "total_entries in dict")

# ─────────────────────────────────────────────────────────────
# Section 17: Directive success — deterministic
# ─────────────────────────────────────────────────────────────
section("17. Directive success — deterministic")
ds_a = get_directive_success_rate(mf)
ds_b = get_directive_success_rate(mf)
check(ds_a.to_dict() == ds_b.to_dict(), "same result twice")

# ─────────────────────────────────────────────────────────────
# Section 18: get_signal_correlations — empty
# ─────────────────────────────────────────────────────────────
section("18. Signal correlations — empty")
sc_empty = get_signal_correlations(empty)
check(sc_empty.total_entries == 0, "zero entries")
check(sc_empty.by_signal == {}, "no signals")
check(sc_empty.overall_outcome_ema == 0.0, "zero ema")

# ─────────────────────────────────────────────────────────────
# Section 19: get_signal_correlations — basic
# ─────────────────────────────────────────────────────────────
section("19. Signal correlations — basic")
sc = get_signal_correlations(mf)
check(sc.total_entries == 20, "20 signal entries")
check("goal" in sc.by_signal, "goal tracked")
check("plan" in sc.by_signal, "plan tracked")
check("strategy" in sc.by_signal, "strategy tracked")

# ─────────────────────────────────────────────────────────────
# Section 20: Signal correlations — structure
# ─────────────────────────────────────────────────────────────
section("20. Signal correlations — structure")
goal_stats = sc.by_signal["goal"]
check("value_ema" in goal_stats, "value_ema present")
check("product_ema" in goal_stats, "product_ema present")
check("correlation" in goal_stats, "correlation present")
check("count" in goal_stats, "count present")

# ─────────────────────────────────────────────────────────────
# Section 21: Signal correlations — correlation bounded
# ─────────────────────────────────────────────────────────────
section("21. Signal correlations — bounded")
for sig, stats in sc.by_signal.items():
    check(
        -1.0 <= stats["correlation"] <= 1.0,
        f"{sig} correlation in [-1, 1]",
    )

# ─────────────────────────────────────────────────────────────
# Section 22: Signal correlations — to_dict
# ─────────────────────────────────────────────────────────────
section("22. Signal correlations — to_dict")
scd = sc.to_dict()
check("by_signal" in scd, "by_signal in dict")
check("overall_outcome_ema" in scd, "overall_ema in dict")
check("total_entries" in scd, "total_entries in dict")

# ─────────────────────────────────────────────────────────────
# Section 23: Signal correlations — deterministic
# ─────────────────────────────────────────────────────────────
section("23. Signal correlations — deterministic")
sc_a = get_signal_correlations(mf)
sc_b = get_signal_correlations(mf)
check(sc_a.to_dict() == sc_b.to_dict(), "same result twice")

# ─────────────────────────────────────────────────────────────
# Section 24: get_plan_structure_success — empty
# ─────────────────────────────────────────────────────────────
section("24. Plan structure — empty")
ps_empty = get_plan_structure_success(empty)
check(ps_empty.total_entries == 0, "zero entries")
check(ps_empty.by_plan == {}, "no plans")
check(ps_empty.by_goal == {}, "no goals")

# ─────────────────────────────────────────────────────────────
# Section 25: get_plan_structure_success — basic
# ─────────────────────────────────────────────────────────────
section("25. Plan structure — basic")
ps = get_plan_structure_success(mf)
check(ps.total_entries > 0, "has entries")
check("plan_alpha" in ps.by_plan, "plan_alpha tracked")
check("g1" in ps.by_goal, "g1 tracked")

# ─────────────────────────────────────────────────────────────
# Section 26: Plan structure — stats
# ─────────────────────────────────────────────────────────────
section("26. Plan structure — stats")
pa = ps.by_plan["plan_alpha"]
check("outcome_ema" in pa, "ema present")
check("count" in pa, "count present")
check("avg_outcome" in pa, "avg present")
check(pa["count"] >= 1, "has entries")

# ─────────────────────────────────────────────────────────────
# Section 27: Plan structure — to_dict
# ─────────────────────────────────────────────────────────────
section("27. Plan structure — to_dict")
psd = ps.to_dict()
check("by_plan" in psd, "by_plan in dict")
check("by_goal" in psd, "by_goal in dict")
check("total_entries" in psd, "total_entries in dict")

# ─────────────────────────────────────────────────────────────
# Section 28: Plan structure — deterministic
# ─────────────────────────────────────────────────────────────
section("28. Plan structure — deterministic")
ps_a = get_plan_structure_success(mf)
ps_b = get_plan_structure_success(mf)
check(ps_a.to_dict() == ps_b.to_dict(), "same result twice")

# ─────────────────────────────────────────────────────────────
# Section 29: compute_analytics_summary — empty
# ─────────────────────────────────────────────────────────────
section("29. Analytics summary — empty")
summary_empty = compute_analytics_summary(empty)
check(summary_empty == {}, "empty fabric → empty dict")

# ─────────────────────────────────────────────────────────────
# Section 30: compute_analytics_summary — basic
# ─────────────────────────────────────────────────────────────
section("30. Analytics summary — basic")
summary = compute_analytics_summary(mf)
check("total_entries" in summary, "total_entries present")
check(summary["total_entries"] > 0, "nonzero total")

# ─────────────────────────────────────────────────────────────
# Section 31: Analytics summary — top_strategies
# ─────────────────────────────────────────────────────────────
section("31. Analytics summary — top_strategies")
check("top_strategies" in summary, "top_strategies present")
check(len(summary["top_strategies"]) <= 5, "at most 5")
check("direct" in summary["top_strategies"], "direct in top")

# ─────────────────────────────────────────────────────────────
# Section 32: Analytics summary — directive_success
# ─────────────────────────────────────────────────────────────
section("32. Analytics summary — directive_success")
check("directive_success" in summary, "directive_success present")
check("recover" in summary["directive_success"], "recover tracked")

# ─────────────────────────────────────────────────────────────
# Section 33: Analytics summary — signal correlations
# ─────────────────────────────────────────────────────────────
section("33. Analytics summary — signal correlations")
check("top_signal_correlations" in summary, "correlations present")
check(len(summary["top_signal_correlations"]) <= 3, "at most 3")

# ─────────────────────────────────────────────────────────────
# Section 34: Analytics summary — plan/goal counts
# ─────────────────────────────────────────────────────────────
section("34. Analytics summary — plan/goal counts")
check("plan_count" in summary, "plan_count present")
check("goal_count" in summary, "goal_count present")
check(summary["plan_count"] > 0, "has plans")
check(summary["goal_count"] > 0, "has goals")

# ─────────────────────────────────────────────────────────────
# Section 35: Analytics summary — deterministic
# ─────────────────────────────────────────────────────────────
section("35. Analytics summary — deterministic")
s_a = compute_analytics_summary(mf)
s_b = compute_analytics_summary(mf)
check(s_a == s_b, "same result twice")

# ─────────────────────────────────────────────────────────────
# Section 36: Analytics is read-only — fabric unchanged
# ─────────────────────────────────────────────────────────────
section("36. Read-only — fabric unchanged")
count_before = mf.entry_count
snap_before = mf.snapshot()
get_strategy_performance_by_state(mf)
get_policy_outcome_distribution(mf)
get_directive_success_rate(mf)
get_signal_correlations(mf)
get_plan_structure_success(mf)
compute_analytics_summary(mf)
count_after = mf.entry_count
snap_after = mf.snapshot()
check(count_before == count_after, "entry count unchanged")
check(snap_before["entry_count"] == snap_after["entry_count"], "snapshot unchanged")
check(
    len(snap_before["entries"]) == len(snap_after["entries"]),
    "entries list unchanged",
)

# ─────────────────────────────────────────────────────────────
# Section 37: DecisionTrace field exists
# ─────────────────────────────────────────────────────────────
section("37. DecisionTrace field")
from umh.runtime_engine.decision_trace import build_trace

t = build_trace(
    turn_id=1,
    fabric_analytics_summary={"total_entries": 50, "top_strategies": {"direct": 0.8}},
)
check(
    t.fabric_analytics_summary
    == {"total_entries": 50, "top_strategies": {"direct": 0.8}},
    "field stored on trace",
)

# ─────────────────────────────────────────────────────────────
# Section 38: DecisionTrace to_dict includes field
# ─────────────────────────────────────────────────────────────
section("38. DecisionTrace to_dict")
td = t.to_dict()
check("fabric_analytics_summary" in td, "field serialized")
check(td["fabric_analytics_summary"]["total_entries"] == 50, "value correct")

# ─────────────────────────────────────────────────────────────
# Section 39: DecisionTrace omits None
# ─────────────────────────────────────────────────────────────
section("39. DecisionTrace omits None")
t_none = build_trace(turn_id=2)
td_none = t_none.to_dict()
check("fabric_analytics_summary" not in td_none, "not in dict when None")

# ─────────────────────────────────────────────────────────────
# Section 40: DecisionTrace backward compat
# ─────────────────────────────────────────────────────────────
section("40. DecisionTrace backward compat")
check(t_none.fabric_analytics_summary is None, "default None")
check(t_none.quality_score == 0.0, "existing fields unchanged")

# ─────────────────────────────────────────────────────────────
# Section 41: Strategy perf — no state entries → no clusters
# ─────────────────────────────────────────────────────────────
section("41. Strategy perf — no state entries")
mf_strat_only = MemoryFabric()
for i in range(5):
    mf_strat_only.record(
        MemoryEntry(
            entry_type=EntryType.STRATEGY_OUTCOME,
            turn=i,
            features={"strategy": "direct", "quality": 0.8},
            outcome=0.8,
        )
    )
sp_no_state = get_strategy_performance_by_state(mf_strat_only)
check(sp_no_state.total_entries == 5, "5 strategy entries")
check(sp_no_state.by_cluster == {}, "no clusters without state")
check("direct" in sp_no_state.by_strategy, "strategy still tracked")

# ─────────────────────────────────────────────────────────────
# Section 42: Policy distribution — no directive entries
# ─────────────────────────────────────────────────────────────
section("42. Policy distribution — no directives")
mf_no_dir = MemoryFabric()
for i in range(5):
    mf_no_dir.record(
        MemoryEntry(
            entry_type=EntryType.STRATEGY_OUTCOME,
            turn=i,
            features={"strategy": "a"},
            outcome=0.6,
        )
    )
pd_no_dir = get_policy_outcome_distribution(mf_no_dir)
check(pd_no_dir.total_entries == 5, "5 entries")
check("none" in pd_no_dir.by_policy, "falls back to 'none' policy")

# ─────────────────────────────────────────────────────────────
# Section 43: Directive success — all below threshold
# ─────────────────────────────────────────────────────────────
section("43. Directive success — all fail")
mf_all_fail = MemoryFabric()
for i in range(5):
    mf_all_fail.record(
        MemoryEntry(
            entry_type=EntryType.DIRECTIVE_EVENT,
            turn=i,
            features={"directive_type": "recover", "confidence": 0.5},
            outcome=0.1,
        )
    )
ds_fail = get_directive_success_rate(mf_all_fail)
check(ds_fail.by_type["recover"]["success_rate"] == 0.0, "0% success")
check(ds_fail.by_type["recover"]["count"] == 5.0, "counted")

# ─────────────────────────────────────────────────────────────
# Section 44: Directive success — all above threshold
# ─────────────────────────────────────────────────────────────
section("44. Directive success — all pass")
mf_all_pass = MemoryFabric()
for i in range(5):
    mf_all_pass.record(
        MemoryEntry(
            entry_type=EntryType.DIRECTIVE_EVENT,
            turn=i,
            features={"directive_type": "exploit", "confidence": 0.9},
            outcome=0.9,
        )
    )
ds_pass = get_directive_success_rate(mf_all_pass)
check(ds_pass.by_type["exploit"]["success_rate"] == 1.0, "100% success")

# ─────────────────────────────────────────────────────────────
# Section 45: Signal correlations — single entry
# ─────────────────────────────────────────────────────────────
section("45. Signal correlations — single entry")
mf_one = MemoryFabric()
mf_one.record(
    MemoryEntry(
        entry_type=EntryType.SIGNAL_OUTCOME,
        turn=1,
        features={"goal": 0.9},
        outcome=0.8,
    )
)
sc_one = get_signal_correlations(mf_one)
check(sc_one.total_entries == 1, "one entry")
check("goal" in sc_one.by_signal, "goal tracked from single entry")

# ─────────────────────────────────────────────────────────────
# Section 46: Signal correlations — covarying signals
# ─────────────────────────────────────────────────────────────
section("46. Signal correlations — covarying")
mf_cov = MemoryFabric()
for i in range(20):
    v = float(i) / 20
    mf_cov.record(
        MemoryEntry(
            entry_type=EntryType.SIGNAL_OUTCOME,
            turn=i,
            features={"rising": v, "flat": 0.5},
            outcome=v,
        )
    )
sc_cov = get_signal_correlations(mf_cov)
check(
    abs(sc_cov.by_signal["rising"]["correlation"])
    >= abs(sc_cov.by_signal["flat"]["correlation"]),
    "rising has higher |correlation| than flat",
)

# ─────────────────────────────────────────────────────────────
# Section 47: Plan structure — multiple plans
# ─────────────────────────────────────────────────────────────
section("47. Plan structure — multiple plans")
mf_plans = MemoryFabric()
for i in range(10):
    mf_plans.record(
        MemoryEntry(
            entry_type=EntryType.PLAN_OUTCOME,
            turn=i,
            features={"plan_id": "p1" if i < 5 else "p2", "goal_id": "g1"},
            outcome=0.8 if i < 5 else 0.3,
        )
    )
ps_multi = get_plan_structure_success(mf_plans)
check("p1" in ps_multi.by_plan, "p1 tracked")
check("p2" in ps_multi.by_plan, "p2 tracked")
check(
    ps_multi.by_plan["p1"]["avg_outcome"] > ps_multi.by_plan["p2"]["avg_outcome"],
    "p1 better than p2",
)

# ─────────────────────────────────────────────────────────────
# Section 48: Plan structure — multiple goals
# ─────────────────────────────────────────────────────────────
section("48. Plan structure — multiple goals")
check("g1" in ps_multi.by_goal, "g1 tracked")
check(ps_multi.by_goal["g1"]["count"] == 10.0, "g1 has all 10 entries")

# ─────────────────────────────────────────────────────────────
# Section 49: Performance bounded — 500 entries
# ─────────────────────────────────────────────────────────────
section("49. Performance bounded")
mf_big = MemoryFabric()
for i in range(500):
    mf_big.record(
        MemoryEntry(
            entry_type=EntryType.STRATEGY_OUTCOME,
            turn=i,
            features={"strategy": f"s{i % 10}", "quality": float(i % 10) / 10},
            outcome=float(i % 10) / 10,
        )
    )
    mf_big.record(
        MemoryEntry(
            entry_type=EntryType.SIGNAL_OUTCOME,
            turn=i,
            features={"goal": 0.5, "plan": 0.5},
            outcome=0.5,
        )
    )

start = time.monotonic()
compute_analytics_summary(mf_big)
elapsed = time.monotonic() - start
check(elapsed < 1.0, f"analytics in {elapsed:.3f}s < 1s")

# ─────────────────────────────────────────────────────────────
# Section 50: No randomness in module
# ─────────────────────────────────────────────────────────────
section("50. No randomness")
import re

with open("/opt/OS/eos/fabric_analytics.py") as f:
    src = f.read()
check(not re.search(r"\bimport\s+random\b", src), "no random import")
check("shuffle" not in src, "no shuffle")

# ─────────────────────────────────────────────────────────────
# Section 51: No LLM calls
# ─────────────────────────────────────────────────────────────
section("51. No LLM calls")
check("anthropic" not in src.lower(), "no anthropic")
check("openai" not in src.lower(), "no openai")
check("call_with_fallback" not in src, "no LLM router")

# ─────────────────────────────────────────────────────────────
# Section 52: No record/write calls in analytics
# ─────────────────────────────────────────────────────────────
section("52. No writes in analytics")
check(".record(" not in src, "no record calls")
check("_entries.append" not in src, "no direct append")

# ─────────────────────────────────────────────────────────────
# Section 53: Constants
# ─────────────────────────────────────────────────────────────
section("53. Constants")
check(EMA_ALPHA == 0.20, "EMA_ALPHA = 0.20")
check(MIN_ENTRIES == 3, "MIN_ENTRIES = 3")

# ─────────────────────────────────────────────────────────────
# Section 54: Analytics summary — below MIN_ENTRIES threshold
# ─────────────────────────────────────────────────────────────
section("54. Analytics summary — below threshold")
mf_tiny = MemoryFabric()
mf_tiny.record(
    MemoryEntry(
        entry_type=EntryType.STRATEGY_OUTCOME,
        turn=0,
        features={"strategy": "a"},
        outcome=0.5,
    )
)
s_tiny = compute_analytics_summary(mf_tiny)
check(s_tiny == {}, "below MIN_ENTRIES → empty")

# ─────────────────────────────────────────────────────────────
# Section 55: Analytics summary — min_turn filter
# ─────────────────────────────────────────────────────────────
section("55. Analytics summary — min_turn")
s_filtered = compute_analytics_summary(mf, min_turn=18)
check(isinstance(s_filtered, dict), "returns dict")

# ─────────────────────────────────────────────────────────────
# SUMMARY
# ─────────────────────────────────────────────────────────────

print(f"\n{'═' * 60}")
print(f"  RESULTS: {_pass} passed, {_fail} failed")
print(f"{'═' * 60}")
if _fail > 0:
    raise SystemExit(1)
