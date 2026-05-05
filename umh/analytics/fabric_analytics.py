"""
FabricAnalytics — read-only intelligence layer over MemoryFabric.

Computes cross-cutting analytics that no individual subsystem can
produce alone.  Pure functions that read from the fabric via
query() and aggregate() — never write, never mutate.

All outputs are deterministic: same fabric contents → same results.
Bounded computation: O(n) where n ≤ MAX_ENTRIES (500).

Functions::

    get_strategy_performance_by_state  — strategy outcomes grouped by cluster
    get_policy_outcome_distribution    — outcome stats per active policy
    get_directive_success_rate         — success rate per directive type
    get_signal_correlations            — per-signal outcome correlation
    get_plan_structure_success         — plan/goal outcome grouping
    compute_analytics_summary          — combined summary for trace

No LLM calls.  No randomness.  No mutation.
"""

from __future__ import annotations

from dataclasses import dataclass

from umh.persistence_layer.memory_fabric import EntryType, MemoryEntry, MemoryFabric

EMA_ALPHA = 0.20
MIN_ENTRIES = 3


def _clamp(v: float, lo: float, hi: float) -> float:
    if v < lo:
        return lo
    if v > hi:
        return hi
    return v


@dataclass(frozen=True)
class StrategyStatePerformance:
    """Outcome EMA per strategy within each world-state cluster."""

    by_cluster: dict[str, dict[str, float]]
    by_strategy: dict[str, float]
    total_entries: int

    def to_dict(self) -> dict:
        return {
            "by_cluster": {
                c: {s: round(v, 4) for s, v in strats.items()}
                for c, strats in self.by_cluster.items()
            },
            "by_strategy": {s: round(v, 4) for s, v in self.by_strategy.items()},
            "total_entries": self.total_entries,
        }


@dataclass(frozen=True)
class PolicyOutcomeDistribution:
    """Outcome statistics per policy mode."""

    by_policy: dict[str, dict[str, float]]
    total_entries: int

    def to_dict(self) -> dict:
        return {
            "by_policy": {
                p: {k: round(v, 4) for k, v in stats.items()}
                for p, stats in self.by_policy.items()
            },
            "total_entries": self.total_entries,
        }


@dataclass(frozen=True)
class DirectiveSuccessRate:
    """Success rate and EMA score per directive type."""

    by_type: dict[str, dict[str, float]]
    total_entries: int

    def to_dict(self) -> dict:
        return {
            "by_type": {
                t: {k: round(v, 4) for k, v in stats.items()}
                for t, stats in self.by_type.items()
            },
            "total_entries": self.total_entries,
        }


@dataclass(frozen=True)
class SignalCorrelations:
    """Per-signal outcome EMA and directional correlation."""

    by_signal: dict[str, dict[str, float]]
    overall_outcome_ema: float
    total_entries: int

    def to_dict(self) -> dict:
        return {
            "by_signal": {
                s: {k: round(v, 4) for k, v in stats.items()}
                for s, stats in self.by_signal.items()
            },
            "overall_outcome_ema": round(self.overall_outcome_ema, 4),
            "total_entries": self.total_entries,
        }


@dataclass(frozen=True)
class PlanStructureSuccess:
    """Outcome grouping by plan and goal identifiers."""

    by_plan: dict[str, dict[str, float]]
    by_goal: dict[str, dict[str, float]]
    total_entries: int

    def to_dict(self) -> dict:
        return {
            "by_plan": {
                p: {k: round(v, 4) for k, v in stats.items()}
                for p, stats in self.by_plan.items()
            },
            "by_goal": {
                g: {k: round(v, 4) for k, v in stats.items()}
                for g, stats in self.by_goal.items()
            },
            "total_entries": self.total_entries,
        }


def get_strategy_performance_by_state(
    fabric: MemoryFabric,
    min_turn: int | None = None,
) -> StrategyStatePerformance:
    """Strategy outcomes grouped by world-state cluster.

    Joins strategy_outcome entries with state_observation entries
    on the same turn to produce per-cluster strategy EMA scores.
    """
    strat_entries = fabric.query(
        entry_type=EntryType.STRATEGY_OUTCOME, min_turn=min_turn
    )
    state_entries = fabric.query(
        entry_type=EntryType.STATE_OBSERVATION, min_turn=min_turn
    )

    turn_to_cluster: dict[int, str] = {}
    for se in state_entries:
        cluster = se.features.get("cluster", "")
        if cluster:
            turn_to_cluster[se.turn] = str(cluster)

    cluster_strat_emas: dict[str, dict[str, float]] = {}
    cluster_strat_counts: dict[str, dict[str, int]] = {}
    strat_emas: dict[str, float] = {}
    strat_counts: dict[str, int] = {}

    for e in strat_entries:
        strat = e.features.get("strategy", "")
        if not strat:
            continue
        strat = str(strat)
        outcome = e.outcome

        if strat not in strat_emas:
            strat_emas[strat] = outcome
            strat_counts[strat] = 1
        else:
            strat_emas[strat] = (
                EMA_ALPHA * outcome + (1.0 - EMA_ALPHA) * strat_emas[strat]
            )
            strat_counts[strat] += 1

        cluster = turn_to_cluster.get(e.turn)
        if cluster:
            if cluster not in cluster_strat_emas:
                cluster_strat_emas[cluster] = {}
                cluster_strat_counts[cluster] = {}
            cs = cluster_strat_emas[cluster]
            cc = cluster_strat_counts[cluster]
            if strat not in cs:
                cs[strat] = outcome
                cc[strat] = 1
            else:
                cs[strat] = EMA_ALPHA * outcome + (1.0 - EMA_ALPHA) * cs[strat]
                cc[strat] += 1

    return StrategyStatePerformance(
        by_cluster=cluster_strat_emas,
        by_strategy=strat_emas,
        total_entries=len(strat_entries),
    )


def get_policy_outcome_distribution(
    fabric: MemoryFabric,
    min_turn: int | None = None,
) -> PolicyOutcomeDistribution:
    """Outcome statistics grouped by the active policy at each turn.

    Reads directive_event entries with a 'policy' feature to identify
    the active policy, then correlates with strategy_outcome outcomes
    on the same turn.
    """
    strat_entries = fabric.query(
        entry_type=EntryType.STRATEGY_OUTCOME, min_turn=min_turn
    )
    directive_entries = fabric.query(
        entry_type=EntryType.DIRECTIVE_EVENT, min_turn=min_turn
    )

    turn_to_policy: dict[int, str] = {}
    for de in directive_entries:
        dtype = de.features.get("directive_type", "")
        if dtype:
            turn_to_policy[de.turn] = str(dtype)

    policy_emas: dict[str, float] = {}
    policy_counts: dict[str, int] = {}
    policy_sum: dict[str, float] = {}

    for e in strat_entries:
        policy = turn_to_policy.get(e.turn, "none")
        outcome = e.outcome

        if policy not in policy_emas:
            policy_emas[policy] = outcome
            policy_counts[policy] = 1
            policy_sum[policy] = outcome
        else:
            policy_emas[policy] = (
                EMA_ALPHA * outcome + (1.0 - EMA_ALPHA) * policy_emas[policy]
            )
            policy_counts[policy] += 1
            policy_sum[policy] += outcome

    by_policy: dict[str, dict[str, float]] = {}
    for p in policy_emas:
        avg = policy_sum[p] / policy_counts[p] if policy_counts[p] > 0 else 0.0
        by_policy[p] = {
            "outcome_ema": policy_emas[p],
            "count": float(policy_counts[p]),
            "avg_outcome": avg,
        }

    return PolicyOutcomeDistribution(
        by_policy=by_policy,
        total_entries=len(strat_entries),
    )


def get_directive_success_rate(
    fabric: MemoryFabric,
    min_turn: int | None = None,
    success_threshold: float = 0.5,
) -> DirectiveSuccessRate:
    """Success rate and EMA per directive type.

    A directive event is "successful" if outcome >= success_threshold.
    """
    entries = fabric.query(entry_type=EntryType.DIRECTIVE_EVENT, min_turn=min_turn)

    type_emas: dict[str, float] = {}
    type_counts: dict[str, int] = {}
    type_successes: dict[str, int] = {}

    for e in entries:
        dtype = str(e.features.get("directive_type", "unknown"))
        outcome = e.outcome

        if dtype not in type_emas:
            type_emas[dtype] = outcome
            type_counts[dtype] = 1
            type_successes[dtype] = 1 if outcome >= success_threshold else 0
        else:
            type_emas[dtype] = (
                EMA_ALPHA * outcome + (1.0 - EMA_ALPHA) * type_emas[dtype]
            )
            type_counts[dtype] += 1
            if outcome >= success_threshold:
                type_successes[dtype] += 1

    by_type: dict[str, dict[str, float]] = {}
    for dt in type_emas:
        cnt = type_counts[dt]
        rate = type_successes[dt] / cnt if cnt > 0 else 0.0
        by_type[dt] = {
            "outcome_ema": type_emas[dt],
            "count": float(cnt),
            "success_count": float(type_successes[dt]),
            "success_rate": rate,
        }

    return DirectiveSuccessRate(
        by_type=by_type,
        total_entries=len(entries),
    )


def get_signal_correlations(
    fabric: MemoryFabric,
    min_turn: int | None = None,
) -> SignalCorrelations:
    """Per-signal outcome correlation from signal_outcome entries.

    For each signal feature, tracks an EMA of the signal value when
    the outcome was above vs below median, producing a directional
    correlation indicator.
    """
    entries = fabric.query(entry_type=EntryType.SIGNAL_OUTCOME, min_turn=min_turn)

    if not entries:
        return SignalCorrelations(
            by_signal={}, overall_outcome_ema=0.0, total_entries=0
        )

    overall_ema = entries[0].outcome
    signal_value_emas: dict[str, float] = {}
    signal_outcome_products: dict[str, float] = {}
    signal_counts: dict[str, int] = {}

    for e in entries[1:]:
        overall_ema = EMA_ALPHA * e.outcome + (1.0 - EMA_ALPHA) * overall_ema

    overall_ema_recompute = entries[0].outcome
    for e in entries:
        if e is not entries[0]:
            overall_ema_recompute = (
                EMA_ALPHA * e.outcome + (1.0 - EMA_ALPHA) * overall_ema_recompute
            )

        for k, v in e.features.items():
            if not isinstance(v, (int, float)):
                continue
            fv = float(v)
            product = fv * e.outcome

            if k not in signal_value_emas:
                signal_value_emas[k] = fv
                signal_outcome_products[k] = product
                signal_counts[k] = 1
            else:
                signal_value_emas[k] = (
                    EMA_ALPHA * fv + (1.0 - EMA_ALPHA) * signal_value_emas[k]
                )
                signal_outcome_products[k] = (
                    EMA_ALPHA * product + (1.0 - EMA_ALPHA) * signal_outcome_products[k]
                )
                signal_counts[k] += 1

    by_signal: dict[str, dict[str, float]] = {}
    for sig in signal_value_emas:
        val_ema = signal_value_emas[sig]
        prod_ema = signal_outcome_products[sig]
        correlation = prod_ema - (val_ema * overall_ema) if val_ema > 0 else 0.0
        by_signal[sig] = {
            "value_ema": val_ema,
            "product_ema": prod_ema,
            "correlation": _clamp(correlation, -1.0, 1.0),
            "count": float(signal_counts[sig]),
        }

    return SignalCorrelations(
        by_signal=by_signal,
        overall_outcome_ema=overall_ema,
        total_entries=len(entries),
    )


def get_plan_structure_success(
    fabric: MemoryFabric,
    min_turn: int | None = None,
) -> PlanStructureSuccess:
    """Plan and goal outcome grouping from plan_outcome entries."""
    entries = fabric.query(entry_type=EntryType.PLAN_OUTCOME, min_turn=min_turn)

    plan_emas: dict[str, float] = {}
    plan_counts: dict[str, int] = {}
    plan_sums: dict[str, float] = {}
    goal_emas: dict[str, float] = {}
    goal_counts: dict[str, int] = {}
    goal_sums: dict[str, float] = {}

    for e in entries:
        plan_id = str(e.features.get("plan_id", ""))
        goal_id = str(e.features.get("goal_id", ""))
        outcome = e.outcome

        if plan_id:
            if plan_id not in plan_emas:
                plan_emas[plan_id] = outcome
                plan_counts[plan_id] = 1
                plan_sums[plan_id] = outcome
            else:
                plan_emas[plan_id] = (
                    EMA_ALPHA * outcome + (1.0 - EMA_ALPHA) * plan_emas[plan_id]
                )
                plan_counts[plan_id] += 1
                plan_sums[plan_id] += outcome

        if goal_id:
            if goal_id not in goal_emas:
                goal_emas[goal_id] = outcome
                goal_counts[goal_id] = 1
                goal_sums[goal_id] = outcome
            else:
                goal_emas[goal_id] = (
                    EMA_ALPHA * outcome + (1.0 - EMA_ALPHA) * goal_emas[goal_id]
                )
                goal_counts[goal_id] += 1
                goal_sums[goal_id] += outcome

    by_plan: dict[str, dict[str, float]] = {}
    for p in plan_emas:
        cnt = plan_counts[p]
        by_plan[p] = {
            "outcome_ema": plan_emas[p],
            "count": float(cnt),
            "avg_outcome": plan_sums[p] / cnt if cnt > 0 else 0.0,
        }

    by_goal: dict[str, dict[str, float]] = {}
    for g in goal_emas:
        cnt = goal_counts[g]
        by_goal[g] = {
            "outcome_ema": goal_emas[g],
            "count": float(cnt),
            "avg_outcome": goal_sums[g] / cnt if cnt > 0 else 0.0,
        }

    return PlanStructureSuccess(
        by_plan=by_plan,
        by_goal=by_goal,
        total_entries=len(entries),
    )


def compute_analytics_summary(
    fabric: MemoryFabric,
    min_turn: int | None = None,
) -> dict:
    """Combined analytics summary for DecisionTrace debug hook.

    Returns a compact dict suitable for the analytics_summary trace field.
    Returns empty dict when fabric has insufficient data.
    """
    total = fabric.entry_count
    if total < MIN_ENTRIES:
        return {}

    result: dict = {"total_entries": total}

    strat_perf = get_strategy_performance_by_state(fabric, min_turn=min_turn)
    if strat_perf.total_entries >= MIN_ENTRIES:
        result["top_strategies"] = dict(
            sorted(
                strat_perf.by_strategy.items(),
                key=lambda x: -x[1],
            )[:5]
        )
        result["strategy_cluster_count"] = len(strat_perf.by_cluster)

    dir_rate = get_directive_success_rate(fabric, min_turn=min_turn)
    if dir_rate.total_entries >= MIN_ENTRIES:
        result["directive_success"] = {
            dt: round(stats.get("success_rate", 0.0), 4)
            for dt, stats in dir_rate.by_type.items()
        }

    sig_corr = get_signal_correlations(fabric, min_turn=min_turn)
    if sig_corr.total_entries >= MIN_ENTRIES:
        top_signals = sorted(
            sig_corr.by_signal.items(),
            key=lambda x: -abs(x[1].get("correlation", 0.0)),
        )[:3]
        result["top_signal_correlations"] = {
            s: round(stats.get("correlation", 0.0), 4) for s, stats in top_signals
        }

    plan_success = get_plan_structure_success(fabric, min_turn=min_turn)
    if plan_success.total_entries >= MIN_ENTRIES:
        result["plan_count"] = len(plan_success.by_plan)
        result["goal_count"] = len(plan_success.by_goal)

    return result
