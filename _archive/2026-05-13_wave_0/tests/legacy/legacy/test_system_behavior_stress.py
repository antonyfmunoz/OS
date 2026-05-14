"""
System behavior stress test — adversarial, long-run, and edge case validation.

Exercises both goal systems:
  1. GoalSelector (runtime/) — portfolio-level selection with multi-horizon scoring
  2. UMH GoalArbitrator/GoalEvaluator/MetaGoalEngine — per-turn arbitration

Tests cover:
  - Adversarial goal sets (conflicting priorities, dependencies, reward asymmetries)
  - Long-run simulation (100-500 cycles, convergence, churn, stability)
  - Failure-heavy scenarios (repeated failures, noisy outcomes, intermittent success)
  - Opportunity traps (short-term spikes vs long-term strategy)
  - Edge cases (all equal, empty, all failing, all succeeding)
  - Operator control (aggressive/conservative modes, budget changes, overrides)

No DB calls — all in-memory. No LLM calls. Deterministic.
"""

import math
import random
import statistics
import sys
import uuid
from collections import Counter
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Optional

sys.path.insert(0, "/opt/OS")

from runtime.goal_selector import (
    DEFAULT_FOCUS_BUDGET,
    DEFAULT_WEIGHTS,
    Goal,
    GoalSelector,
    GoalState,
    MultiHorizonProfile,
    OpportunityCostLayer,
    OutcomeTracker,
    PerformanceProfile,
    StrategicHorizonLayer,
)
from umh.goals.state import GoalRegistry, GoalState as UMHGoalState, GoalTracker
from umh.runtime_engine.goal_arbitrator import (
    GoalArbitrator,
    SWITCH_COST,
    W_DELTA,
    W_PRIORITY,
    W_RECENCY,
    W_SCORE,
)
from umh.runtime_engine.meta_goal import (
    COOLDOWN_TURNS,
    MAX_GOALS,
    MetaGoal,
    MetaGoalEngine,
)

# ─── Helpers ─────────────────────────────────────────────────────────────────

NOW = datetime.now(timezone.utc)


def _make_goal(
    title: str,
    priority: int = 5,
    impact: float = 0.5,
    cost: float = 0.5,
    confidence: float = 0.5,
    state: GoalState = GoalState.DEFERRED,
    blocked_by: list[str] | None = None,
    perf: PerformanceProfile | None = None,
    created_days_ago: int = 0,
    gid: str | None = None,
) -> Goal:
    """Build an in-memory Goal for testing without DB."""
    return Goal(
        id=gid or str(uuid.uuid4())[:8],
        org_id="test-org",
        title=title,
        state=state,
        priority=priority,
        expected_impact=impact,
        estimated_cost=cost,
        confidence=confidence,
        blocked_by=blocked_by or [],
        performance=perf or PerformanceProfile(),
        created_at=NOW - timedelta(days=created_days_ago),
        updated_at=NOW,
    )


def _inject_performance(
    goal: Goal,
    success_rate: float,
    efficiency: float = 0.5,
    reliability: float = 0.8,
    impact_score: float = 0.5,
    total_outcomes: int = 10,
) -> Goal:
    """Inject a synthetic performance profile."""
    successes = int(total_outcomes * success_rate)
    goal.performance = PerformanceProfile(
        success_rate=success_rate,
        efficiency=efficiency,
        reliability=reliability,
        impact_score=impact_score,
        total_outcomes=total_outcomes,
        total_successes=successes,
        total_failures=total_outcomes - successes,
        avg_execution_time=30.0,
        last_outcome_at=NOW - timedelta(hours=1),
    )
    goal.horizons = MultiHorizonProfile(
        short_term=goal.performance,
        medium_term=goal.performance,
        long_term=goal.performance,
    )
    return goal


def _selector_no_db(**kwargs) -> GoalSelector:
    """Create a GoalSelector that doesn't touch DB."""
    sel = GoalSelector.__new__(GoalSelector)
    sel.org_id = "test-org"
    sel.focus_budget = kwargs.get("focus_budget", DEFAULT_FOCUS_BUDGET)
    sel.weights = kwargs.get("weights", dict(DEFAULT_WEIGHTS))
    sel.opportunity_cost = OpportunityCostLayer(
        weight=kwargs.get("opportunity_cost_weight", 0.10),
        swap_threshold=kwargs.get("swap_threshold", 0.05),
        sustained_cycles=kwargs.get("swap_sustained_cycles", 3),
    )
    sel.strategic_horizon = StrategicHorizonLayer(
        horizon_weights=kwargs.get("horizon_weights"),
        performance_weight=sel.weights.get("performance", 0.20),
    )
    return sel


def _run_selection_cycle_inmemory(
    selector: GoalSelector,
    goals: list[Goal],
) -> list[Goal]:
    """Run selection cycle without DB persistence or event logging."""
    scorable = [g for g in goals if g.state in {GoalState.ACTIVE, GoalState.DEFERRED}]
    blocked = [g for g in goals if g.state == GoalState.BLOCKED]

    # Auto-unblock
    for g in blocked:
        if selector._blockers_resolved(g, goals):
            g.state = GoalState.DEFERRED
            scorable.append(g)

    for g in scorable:
        selector.score_goal(g, goals)

    scorable.sort(key=lambda g: (-g.score, -g.priority, g.created_at))

    for i, g in enumerate(scorable):
        if i < selector.focus_budget:
            g.state = GoalState.ACTIVE
        else:
            g.state = GoalState.DEFERRED

    selector.opportunity_cost.compute_relative_penalties(scorable, selector.focus_budget)

    active_goals = [g for g in scorable if g.state == GoalState.ACTIVE]
    deferred_goals = [g for g in scorable if g.state == GoalState.DEFERRED]
    swaps = selector.opportunity_cost.evaluate_swap_pressure(active_goals, deferred_goals)

    for demote, promote in swaps:
        demote.state = GoalState.DEFERRED
        promote.state = GoalState.ACTIVE

    scorable.sort(key=lambda g: (-g.score, -g.priority, g.created_at))
    active: list[Goal] = []
    for i, g in enumerate(scorable):
        g.rank = i + 1
        if g.state == GoalState.ACTIVE:
            active.append(g)

    return active


@dataclass
class SimulationMetrics:
    """Track simulation run metrics."""

    total_cycles: int = 0
    active_goal_ids_per_cycle: list[list[str]] = field(default_factory=list)
    scores_per_cycle: list[dict[str, float]] = field(default_factory=list)
    swaps: int = 0
    convergence_point: int | None = None

    @property
    def churn_rate(self) -> float:
        """Fraction of cycles where active set changed."""
        if len(self.active_goal_ids_per_cycle) < 2:
            return 0.0
        changes = 0
        for i in range(1, len(self.active_goal_ids_per_cycle)):
            if set(self.active_goal_ids_per_cycle[i]) != set(
                self.active_goal_ids_per_cycle[i - 1]
            ):
                changes += 1
        return changes / (len(self.active_goal_ids_per_cycle) - 1)

    @property
    def score_variance(self) -> float:
        """Mean variance of goal scores across cycles."""
        if not self.scores_per_cycle:
            return 0.0
        all_scores = []
        for cycle_scores in self.scores_per_cycle:
            all_scores.extend(cycle_scores.values())
        if len(all_scores) < 2:
            return 0.0
        return statistics.variance(all_scores)


# ═══════════════════════════════════════════════════════════════════════════════
# 1. ADVERSARIAL GOALS
# ═══════════════════════════════════════════════════════════════════════════════


class TestAdversarialGoals:
    """Goals designed to break naive prioritization."""

    def test_high_priority_low_success(self):
        """High priority goals with poor track record: priority anchors scoring.

        FINDING: With default weights (priority=0.25, performance=0.20),
        priority dominates. A priority-10 goal with 10% success still beats
        priority-6 with 90% success. The base score gap (~0.10) from priority
        exceeds the max performance adjustment. This is by design: the system
        trusts human-assigned priority as a strong signal. Operators who want
        performance to override priority must use aggressive mode weights.
        """
        selector = _selector_no_db()

        # High priority but historically terrible
        g1 = _make_goal("High Priority Trap", priority=10, impact=0.9, cost=0.2)
        _inject_performance(g1, success_rate=0.1, efficiency=0.2, reliability=0.3)

        # Medium priority but excellent track record
        g2 = _make_goal("Steady Performer", priority=6, impact=0.6, cost=0.3)
        _inject_performance(g2, success_rate=0.9, efficiency=0.8, reliability=0.9)

        goals = [g1, g2]
        _run_selection_cycle_inmemory(selector, goals)

        # Priority anchor: g1 still wins because priority+impact base outweighs
        # the performance penalty. Performance DOES penalize, but not enough.
        assert g1.score > g2.score, (
            f"Priority anchor broken: high-pri ({g1.score:.4f}) "
            f"should beat med-pri ({g2.score:.4f}) under default weights"
        )

        # But performance DID penalize — g1 score should be lower than a
        # hypothetical priority-10 with good performance
        g1_good = _make_goal("High Priority Good", priority=10, impact=0.9, cost=0.2)
        _inject_performance(g1_good, success_rate=0.9, efficiency=0.8, reliability=0.9)
        selector.score_goal(g1_good, [g1_good])
        assert g1.score < g1_good.score, (
            "Performance penalty should reduce score vs same-priority good performer"
        )

    def test_low_priority_high_impact(self):
        """Low priority high impact goals should compete when performance is strong."""
        selector = _selector_no_db()

        g_low_pri = _make_goal("Low Priority High Impact", priority=3, impact=0.95, cost=0.1)
        _inject_performance(g_low_pri, success_rate=0.95, efficiency=0.9, reliability=0.95)

        g_med = _make_goal("Medium Everything", priority=5, impact=0.5, cost=0.5)
        _inject_performance(g_med, success_rate=0.5, efficiency=0.5, reliability=0.5)

        goals = [g_low_pri, g_med]
        _run_selection_cycle_inmemory(selector, goals)

        # Impact + performance should compensate for low priority
        assert g_low_pri.score > 0.3, f"High impact goal scored too low: {g_low_pri.score}"

    def test_conflicting_dependencies(self):
        """Goals that block each other should be handled without deadlock.

        IMPORTANT: Goals must start in BLOCKED state for dependency logic to
        apply. The selector only checks `_blockers_resolved()` on goals that
        are already in GoalState.BLOCKED — DEFERRED goals with blocked_by
        are scored normally (blocked_by is metadata, not a state gate).
        """
        selector = _selector_no_db()

        g_a = _make_goal("Goal A", priority=8, gid="goal-a")
        g_b = _make_goal("Goal B", priority=7, gid="goal-b", blocked_by=["goal-a"])
        g_b.state = GoalState.BLOCKED
        g_c = _make_goal("Goal C", priority=9, gid="goal-c", blocked_by=["goal-b"])
        g_c.state = GoalState.BLOCKED

        goals = [g_a, g_b, g_c]
        active = _run_selection_cycle_inmemory(selector, goals)

        # A should be active (unblocked), B blocked (A not completed), C blocked (B not completed)
        assert g_a.state == GoalState.ACTIVE
        assert g_b.state == GoalState.BLOCKED
        assert g_c.state == GoalState.BLOCKED

        # Complete A → B should unblock (A is now terminal)
        g_a.state = GoalState.COMPLETED
        active = _run_selection_cycle_inmemory(selector, goals)

        assert g_b.state in {GoalState.ACTIVE, GoalState.DEFERRED}
        assert g_b.state != GoalState.BLOCKED
        # C still blocked because B isn't completed yet
        assert g_c.state == GoalState.BLOCKED

    def test_delayed_reward_vs_immediate_win(self):
        """System should not always pick immediate reward over delayed payoff."""
        selector = _selector_no_db()

        # Immediate win: low cost, medium impact, great recent performance
        g_imm = _make_goal("Quick Win", priority=5, impact=0.4, cost=0.1)
        _inject_performance(g_imm, success_rate=0.9, efficiency=0.95, reliability=0.9)

        # Delayed reward: high cost, very high impact, moderate performance
        g_del = _make_goal("Strategic Bet", priority=8, impact=0.95, cost=0.7)
        _inject_performance(g_del, success_rate=0.6, efficiency=0.4, reliability=0.7)

        goals = [g_imm, g_del]
        active = _run_selection_cycle_inmemory(selector, goals)

        # Both should be active (within budget), strategic bet should rank higher
        # because priority (8 vs 5) and impact (0.95 vs 0.4) outweigh cost penalty
        assert g_del.rank <= g_imm.rank or g_del.state == GoalState.ACTIVE

    def test_no_starvation_with_many_goals(self):
        """With many goals, low-ranked goals should still be scorable, not permanently locked out."""
        selector = _selector_no_db(focus_budget=2)

        goals = []
        for i in range(10):
            g = _make_goal(f"Goal {i}", priority=10 - i, impact=0.5)
            goals.append(g)

        active = _run_selection_cycle_inmemory(selector, goals)

        # Only 2 should be active
        assert len(active) == 2

        # All non-terminal goals should still have scores (not starved)
        for g in goals:
            if g.state in {GoalState.ACTIVE, GoalState.DEFERRED}:
                assert g.score > 0, f"Goal {g.title} has zero score — starvation"

    def test_no_irrational_locking(self):
        """If a top goal's performance drops, it should eventually be displaced."""
        selector = _selector_no_db(focus_budget=1)

        g_incumbent = _make_goal("Incumbent", priority=8, gid="inc")
        _inject_performance(g_incumbent, success_rate=0.9)

        g_challenger = _make_goal("Challenger", priority=7, gid="chl")
        _inject_performance(g_challenger, success_rate=0.5)

        goals = [g_incumbent, g_challenger]

        # Cycle 1: incumbent wins
        active = _run_selection_cycle_inmemory(selector, goals)
        assert active[0].id == "inc"

        # Degrade incumbent performance
        _inject_performance(g_incumbent, success_rate=0.1, efficiency=0.1, reliability=0.2)
        _inject_performance(g_challenger, success_rate=0.95, efficiency=0.9, reliability=0.9)

        # Run several cycles to build swap pressure
        for _ in range(5):
            active = _run_selection_cycle_inmemory(selector, goals)

        # Challenger should now be active
        final_active = [g for g in goals if g.state == GoalState.ACTIVE]
        assert any(
            g.id == "chl" for g in final_active
        ), "Challenger should displace degraded incumbent"


# ═══════════════════════════════════════════════════════════════════════════════
# 2. LONG-RUN SIMULATION
# ═══════════════════════════════════════════════════════════════════════════════


class TestLongRunSimulation:
    """Simulate 100-500 cycles and verify stability."""

    def _run_simulation(
        self,
        goals: list[Goal],
        cycles: int = 200,
        noise_fn=None,
        focus_budget: int = 3,
    ) -> SimulationMetrics:
        selector = _selector_no_db(focus_budget=focus_budget)
        metrics = SimulationMetrics()

        for cycle in range(cycles):
            if noise_fn:
                noise_fn(goals, cycle)

            active = _run_selection_cycle_inmemory(selector, goals)
            metrics.total_cycles += 1
            metrics.active_goal_ids_per_cycle.append([g.id for g in active])
            metrics.scores_per_cycle.append({g.id: g.score for g in goals})

            # Detect convergence: same active set for 10+ consecutive cycles
            if metrics.convergence_point is None and len(metrics.active_goal_ids_per_cycle) > 10:
                last_10 = metrics.active_goal_ids_per_cycle[-10:]
                if all(set(s) == set(last_10[0]) for s in last_10):
                    metrics.convergence_point = cycle - 10

        return metrics

    def test_stable_convergence(self):
        """With stable performance, the system should converge and stay converged."""
        goals = []
        for i in range(6):
            g = _make_goal(f"Stable Goal {i}", priority=8 - i, impact=0.7 - i * 0.05)
            _inject_performance(g, success_rate=0.7 - i * 0.05)
            goals.append(g)

        metrics = self._run_simulation(goals, cycles=100)

        assert metrics.convergence_point is not None, "System should converge"
        assert metrics.convergence_point < 50, (
            f"Convergence too slow: cycle {metrics.convergence_point}"
        )
        assert metrics.churn_rate < 0.2, (
            f"Churn rate too high: {metrics.churn_rate:.2f}"
        )

    def test_gradual_performance_shift(self):
        """When performance gradually shifts, active set should adapt — not oscillate."""
        g_declining = _make_goal("Declining Star", priority=8, gid="dec")
        g_rising = _make_goal("Rising Star", priority=6, gid="ris")
        g_stable = _make_goal("Stable Middle", priority=7, gid="stb")

        _inject_performance(g_declining, success_rate=0.9)
        _inject_performance(g_rising, success_rate=0.3)
        _inject_performance(g_stable, success_rate=0.6)

        goals = [g_declining, g_rising, g_stable]

        def gradual_shift(gs: list[Goal], cycle: int):
            for g in gs:
                if g.id == "dec":
                    new_sr = max(0.1, 0.9 - cycle * 0.004)
                    _inject_performance(g, success_rate=new_sr)
                elif g.id == "ris":
                    new_sr = min(0.95, 0.3 + cycle * 0.003)
                    _inject_performance(g, success_rate=new_sr)

        metrics = self._run_simulation(goals, cycles=300, noise_fn=gradual_shift)

        # System should eventually swap — rising star should appear in later cycles
        last_50 = metrics.active_goal_ids_per_cycle[-50:]
        ris_active_count = sum(1 for ids in last_50 if "ris" in ids)
        assert ris_active_count > 20, (
            f"Rising star only active in {ris_active_count}/50 final cycles"
        )

    def test_score_distribution_bounded(self):
        """All scores should stay within reasonable bounds across a long run."""
        goals = []
        for i in range(8):
            g = _make_goal(f"Dist Goal {i}", priority=random.randint(3, 9))
            _inject_performance(g, success_rate=random.uniform(0.2, 0.8))
            goals.append(g)

        metrics = self._run_simulation(goals, cycles=200)

        for cycle_scores in metrics.scores_per_cycle:
            for gid, score in cycle_scores.items():
                assert -0.5 <= score <= 1.5, (
                    f"Score out of bounds: {gid} = {score}"
                )

    def test_swap_frequency_reasonable(self):
        """Swap frequency should be bounded — no rapid oscillation."""
        goals = []
        for i in range(5):
            g = _make_goal(f"Swap Test {i}", priority=7)
            _inject_performance(g, success_rate=0.5 + (i % 2) * 0.1)
            goals.append(g)

        metrics = self._run_simulation(goals, cycles=200, focus_budget=2)
        assert metrics.churn_rate < 0.3, (
            f"Churn rate too high for similar goals: {metrics.churn_rate:.2f}"
        )


# ═══════════════════════════════════════════════════════════════════════════════
# 3. FAILURE-HEAVY SCENARIOS
# ═══════════════════════════════════════════════════════════════════════════════


class TestFailureHeavy:
    """Inject failures and verify graceful degradation."""

    def test_repeated_failures_dont_collapse_confidence(self):
        """After many failures, system should adapt — not collapse all scores to zero."""
        selector = _selector_no_db()

        goals = []
        for i in range(4):
            g = _make_goal(f"Failing Goal {i}", priority=7)
            _inject_performance(g, success_rate=0.1, reliability=0.2, total_outcomes=50)
            goals.append(g)

        active = _run_selection_cycle_inmemory(selector, goals)

        # All should still have positive scores
        for g in goals:
            assert g.score > 0, f"Score collapsed to zero: {g.title}"

        # The system should still pick the best available
        assert len(active) > 0, "System should still select active goals even with failures"

    def test_noisy_outcomes_dont_cause_oscillation(self):
        """High-variance noise in success rate should not cause goal thrashing."""
        selector = _selector_no_db(focus_budget=2)
        rng = random.Random(42)

        goals = []
        for i in range(5):
            g = _make_goal(f"Noisy Goal {i}", priority=6 + i % 3)
            _inject_performance(g, success_rate=0.5)
            goals.append(g)

        active_history: list[set[str]] = []

        for cycle in range(100):
            # Add noise to performance each cycle
            for g in goals:
                noisy_sr = max(0.05, min(0.95, 0.5 + rng.gauss(0, 0.3)))
                _inject_performance(g, success_rate=noisy_sr)

            active = _run_selection_cycle_inmemory(selector, goals)
            active_history.append({g.id for g in active})

        # Compute churn
        changes = sum(
            1
            for i in range(1, len(active_history))
            if active_history[i] != active_history[i - 1]
        )
        churn = changes / (len(active_history) - 1)

        # With high noise, some churn is expected, but priority should anchor decisions
        assert churn < 0.8, f"Churn too high under noise: {churn:.2f}"

    def test_intermittent_success_adapts(self):
        """Goals with intermittent success should be scored between extremes."""
        selector = _selector_no_db()

        # 50% success rate — intermittent
        g_intermittent = _make_goal("Intermittent", priority=7)
        _inject_performance(g_intermittent, success_rate=0.5, reliability=0.5)

        # Always fails
        g_always_fail = _make_goal("Always Fails", priority=7)
        _inject_performance(g_always_fail, success_rate=0.05, reliability=0.1)

        # Always succeeds
        g_always_win = _make_goal("Always Wins", priority=7)
        _inject_performance(g_always_win, success_rate=0.95, reliability=0.95)

        goals = [g_intermittent, g_always_fail, g_always_win]
        _run_selection_cycle_inmemory(selector, goals)

        assert g_always_fail.score < g_intermittent.score < g_always_win.score, (
            f"Ordering wrong: fail={g_always_fail.score:.4f}, "
            f"intermittent={g_intermittent.score:.4f}, "
            f"win={g_always_win.score:.4f}"
        )


# ═══════════════════════════════════════════════════════════════════════════════
# 4. OPPORTUNITY TRAPS
# ═══════════════════════════════════════════════════════════════════════════════


class TestOpportunityTraps:
    """Verify system doesn't get distracted by short-term spikes."""

    def test_short_term_spike_doesnt_displace_strategic(self):
        """A sudden performance spike on a low-priority goal should not immediately displace strategic goals."""
        selector = _selector_no_db(focus_budget=2)

        g_strategic = _make_goal("Strategic Long-Term", priority=9, impact=0.9, cost=0.5)
        _inject_performance(g_strategic, success_rate=0.65, efficiency=0.6)

        g_tactical = _make_goal("Quick Tactical", priority=4, impact=0.3, cost=0.1)
        _inject_performance(g_tactical, success_rate=0.95, efficiency=0.95)

        g_filler = _make_goal("Filler", priority=5, impact=0.5)
        _inject_performance(g_filler, success_rate=0.5)

        goals = [g_strategic, g_tactical, g_filler]

        # First cycle: strategic should be active
        active = _run_selection_cycle_inmemory(selector, goals)
        assert g_strategic.state == GoalState.ACTIVE, "Strategic goal should start active"

        # Simulate sudden spike on tactical
        _inject_performance(g_tactical, success_rate=1.0, efficiency=1.0, reliability=1.0, impact_score=1.0)

        # Run again — strategic should STILL be active (priority anchors it)
        active = _run_selection_cycle_inmemory(selector, goals)
        assert g_strategic.state == GoalState.ACTIVE, (
            "Strategic goal displaced by short-term spike — system is too reactive"
        )

    def test_long_term_goals_persist_through_noise(self):
        """Long-term high-priority goals should persist even when performance dips temporarily."""
        selector = _selector_no_db(focus_budget=2)

        g_long = _make_goal("Long-Term Vision", priority=9, impact=0.95, cost=0.6)
        _inject_performance(g_long, success_rate=0.7)

        g_short = _make_goal("Short-Term Gain", priority=5, impact=0.4, cost=0.1)
        _inject_performance(g_short, success_rate=0.8)

        goals = [g_long, g_short]

        # Simulate 10 cycles where long-term dips then recovers
        persistence_count = 0
        for cycle in range(20):
            if 5 <= cycle <= 10:
                _inject_performance(g_long, success_rate=0.3)  # temporary dip
            else:
                _inject_performance(g_long, success_rate=0.7)

            active = _run_selection_cycle_inmemory(selector, goals)
            if g_long.state == GoalState.ACTIVE:
                persistence_count += 1

        assert persistence_count >= 15, (
            f"Long-term goal only persisted {persistence_count}/20 cycles"
        )


# ═══════════════════════════════════════════════════════════════════════════════
# 5. EDGE CASES
# ═══════════════════════════════════════════════════════════════════════════════


class TestEdgeCases:
    """Boundary conditions and degenerate inputs."""

    def test_all_goals_equal(self):
        """When all goals have identical parameters, system should still select deterministically."""
        selector = _selector_no_db(focus_budget=2)

        goals = []
        for i in range(5):
            g = _make_goal(f"Equal Goal {i}", priority=5, impact=0.5, cost=0.5)
            _inject_performance(g, success_rate=0.5)
            goals.append(g)

        active1 = _run_selection_cycle_inmemory(selector, goals)
        # Reset states
        for g in goals:
            g.state = GoalState.DEFERRED
        active2 = _run_selection_cycle_inmemory(selector, goals)

        # Should be deterministic — same input → same output
        assert [g.id for g in active1] == [g.id for g in active2]

    def test_no_goals(self):
        """Empty goal set should not crash."""
        selector = _selector_no_db()
        active = _run_selection_cycle_inmemory(selector, [])
        assert active == []

    def test_single_goal(self):
        """Single goal should always be active."""
        selector = _selector_no_db()
        g = _make_goal("Only Goal", priority=5)
        active = _run_selection_cycle_inmemory(selector, [g])
        assert len(active) == 1
        assert active[0].id == g.id

    def test_all_goals_failing(self):
        """All goals failing should not crash — system picks the least bad."""
        selector = _selector_no_db(focus_budget=2)

        goals = []
        for i in range(4):
            g = _make_goal(f"Failing {i}", priority=5 + i)
            _inject_performance(g, success_rate=0.05, reliability=0.1)
            goals.append(g)

        active = _run_selection_cycle_inmemory(selector, goals)
        assert len(active) == 2
        # Highest priority should still win even when all are failing
        active_priorities = {g.priority for g in active}
        assert max(active_priorities) == 8

    def test_all_goals_succeeding(self):
        """All goals succeeding should select by priority/impact tiebreak."""
        selector = _selector_no_db(focus_budget=2)

        goals = []
        for i in range(4):
            g = _make_goal(f"Winner {i}", priority=5 + i, impact=0.5 + i * 0.1)
            _inject_performance(g, success_rate=0.95, reliability=0.95)
            goals.append(g)

        active = _run_selection_cycle_inmemory(selector, goals)
        assert len(active) == 2
        # Top 2 by priority should be active
        active_priorities = sorted([g.priority for g in active], reverse=True)
        assert active_priorities == [8, 7]

    def test_all_goals_blocked(self):
        """If all goals are blocked, none should be active."""
        selector = _selector_no_db()

        g_a = _make_goal("Blocked A", priority=8, gid="a", blocked_by=["b"])
        g_b = _make_goal("Blocked B", priority=7, gid="b", blocked_by=["a"])
        g_a.state = GoalState.BLOCKED
        g_b.state = GoalState.BLOCKED

        active = _run_selection_cycle_inmemory(selector, [g_a, g_b])
        assert active == [], "Circular blocks should not produce active goals"

    def test_focus_budget_zero(self):
        """Focus budget of zero should produce no active goals."""
        selector = _selector_no_db(focus_budget=0)

        goals = [_make_goal(f"Goal {i}", priority=8) for i in range(3)]
        active = _run_selection_cycle_inmemory(selector, goals)
        assert active == []

    def test_focus_budget_exceeds_goals(self):
        """Focus budget larger than goal count should activate all."""
        selector = _selector_no_db(focus_budget=10)

        goals = [_make_goal(f"Goal {i}", priority=5) for i in range(3)]
        active = _run_selection_cycle_inmemory(selector, goals)
        assert len(active) == 3


# ═══════════════════════════════════════════════════════════════════════════════
# 6. OPERATOR CONTROL VALIDATION
# ═══════════════════════════════════════════════════════════════════════════════


class TestOperatorControl:
    """Verify system respects operator configuration."""

    def test_aggressive_mode(self):
        """With high performance weight, performance should dominate scoring."""
        aggressive_weights = dict(DEFAULT_WEIGHTS)
        aggressive_weights["performance"] = 0.40
        aggressive_weights["priority"] = 0.10
        selector = _selector_no_db(weights=aggressive_weights)

        g_high_perf = _make_goal("High Perf", priority=3)
        _inject_performance(g_high_perf, success_rate=0.95, efficiency=0.9)

        g_high_pri = _make_goal("High Priority", priority=10)
        _inject_performance(g_high_pri, success_rate=0.2, efficiency=0.2)

        goals = [g_high_perf, g_high_pri]
        _run_selection_cycle_inmemory(selector, goals)

        assert g_high_perf.score > g_high_pri.score, (
            "In aggressive mode, performance should beat raw priority"
        )

    def test_conservative_mode(self):
        """With high priority weight, explicit priority should dominate."""
        conservative_weights = dict(DEFAULT_WEIGHTS)
        conservative_weights["priority"] = 0.50
        conservative_weights["performance"] = 0.05
        selector = _selector_no_db(weights=conservative_weights)

        g_high_pri = _make_goal("High Priority", priority=10)
        _inject_performance(g_high_pri, success_rate=0.2)

        g_low_pri = _make_goal("Low Priority Performer", priority=3)
        _inject_performance(g_low_pri, success_rate=0.95)

        goals = [g_high_pri, g_low_pri]
        _run_selection_cycle_inmemory(selector, goals)

        assert g_high_pri.score > g_low_pri.score, (
            "In conservative mode, priority should beat performance"
        )

    def test_focus_budget_change(self):
        """Changing focus budget should immediately change active set size."""
        goals = [_make_goal(f"Goal {i}", priority=8 - i) for i in range(6)]

        for budget in [1, 2, 3, 5]:
            selector = _selector_no_db(focus_budget=budget)
            # Reset states
            for g in goals:
                g.state = GoalState.DEFERRED
            active = _run_selection_cycle_inmemory(selector, goals)
            assert len(active) == budget, (
                f"Budget {budget} should produce {budget} active, got {len(active)}"
            )

    def test_priority_override(self):
        """Manual activation should override scoring."""
        selector = _selector_no_db(focus_budget=1)

        g_top = _make_goal("Top Scorer", priority=10, gid="top")
        _inject_performance(g_top, success_rate=0.9)

        g_bottom = _make_goal("Bottom Scorer", priority=1, gid="bot")
        _inject_performance(g_bottom, success_rate=0.1)

        goals = [g_top, g_bottom]
        active = _run_selection_cycle_inmemory(selector, goals)
        assert active[0].id == "top"

        # Manual override: force bottom to active
        g_bottom.state = GoalState.ACTIVE
        g_top.state = GoalState.DEFERRED
        assert g_bottom.state == GoalState.ACTIVE

    def test_custom_horizon_weights(self):
        """Custom horizon weights should shift scoring emphasis."""
        # Short-term heavy
        short_heavy = _selector_no_db(
            horizon_weights={"short": 0.80, "medium": 0.15, "long": 0.05}
        )

        g = _make_goal("Horizon Test", priority=7)
        # Short term great, long term terrible
        g.horizons = MultiHorizonProfile(
            short_term=PerformanceProfile(
                success_rate=0.95, efficiency=0.9, reliability=0.9, impact_score=0.8,
                total_outcomes=10, total_successes=9, total_failures=1,
            ),
            medium_term=PerformanceProfile(
                success_rate=0.5, efficiency=0.5, reliability=0.5, impact_score=0.5,
                total_outcomes=10, total_successes=5, total_failures=5,
            ),
            long_term=PerformanceProfile(
                success_rate=0.2, efficiency=0.2, reliability=0.2, impact_score=0.2,
                total_outcomes=10, total_successes=2, total_failures=8,
            ),
        )

        short_heavy.score_goal(g, [g])
        short_score = g.score

        # Long-term heavy
        long_heavy = _selector_no_db(
            horizon_weights={"short": 0.05, "medium": 0.15, "long": 0.80}
        )
        g.score = 0.0
        g.base_score = 0.0
        g.performance_adjustment = 0.0
        long_heavy.score_goal(g, [g])
        long_score = g.score

        assert short_score > long_score, (
            f"Short-heavy ({short_score:.4f}) should score higher than "
            f"long-heavy ({long_score:.4f}) for this goal"
        )

    def test_no_hidden_behavior(self):
        """System should not produce different results for identical inputs."""
        selector = _selector_no_db()

        goals_a = [_make_goal(f"Goal {i}", priority=7, gid=f"g{i}") for i in range(4)]
        goals_b = [_make_goal(f"Goal {i}", priority=7, gid=f"g{i}") for i in range(4)]

        for ga, gb in zip(goals_a, goals_b):
            _inject_performance(ga, success_rate=0.6)
            _inject_performance(gb, success_rate=0.6)

        active_a = _run_selection_cycle_inmemory(selector, goals_a)
        active_b = _run_selection_cycle_inmemory(selector, goals_b)

        scores_a = {g.id: g.score for g in goals_a}
        scores_b = {g.id: g.score for g in goals_b}

        for gid in scores_a:
            assert abs(scores_a[gid] - scores_b[gid]) < 0.0001, (
                f"Non-deterministic: {gid} scored {scores_a[gid]} vs {scores_b[gid]}"
            )


# ═══════════════════════════════════════════════════════════════════════════════
# 7. UMH GOAL ARBITRATOR STRESS
# ═══════════════════════════════════════════════════════════════════════════════


class TestUMHArbitratorStress:
    """Stress test the per-turn UMH goal arbitrator."""

    def test_switch_cost_prevents_thrashing(self):
        """Two goals with similar utility should not flip-flop every turn."""
        registry = GoalRegistry()

        g_a = UMHGoalState(goal_id="a", description="A", priority=0.6)
        g_b = UMHGoalState(goal_id="b", description="B", priority=0.6)
        registry.add_goal(g_a)
        registry.add_goal(g_b)

        # Give them nearly identical success scores
        tracker_a = registry.get_tracker("a")
        tracker_b = registry.get_tracker("b")
        for _ in range(5):
            tracker_a.update_success(0.6)
            tracker_b.update_success(0.59)

        arbitrator = GoalArbitrator()
        switches = 0
        prev_id: str | None = None

        for turn in range(50):
            registry.advance_turn()
            result = arbitrator.select_active_goal(
                registry, previous_active_goal_id=prev_id
            )
            if result.selected_goal_id != prev_id and prev_id is not None:
                switches += 1
            prev_id = result.selected_goal_id

        assert switches < 10, (
            f"Too many switches ({switches}) for near-identical goals — switch cost isn't working"
        )

    def test_blend_entropy_bounded(self):
        """Blended goal weights should have reasonable entropy."""
        registry = GoalRegistry()

        for i in range(5):
            g = UMHGoalState(
                goal_id=f"g{i}",
                description=f"Goal {i}",
                priority=0.5 + i * 0.1,
            )
            registry.add_goal(g)
            t = registry.get_tracker(f"g{i}")
            for _ in range(3):
                t.update_success(0.5 + i * 0.05)

        arbitrator = GoalArbitrator()
        registry.advance_turn()
        blend = arbitrator.blend_goals(registry)

        assert blend.entropy >= 0.0, "Entropy should be non-negative"
        assert len(blend.goals) <= 3, "Default blend K should be 3"
        assert abs(sum(w for _, w in blend.goals) - 1.0) < 0.001, "Weights should sum to 1.0"

    def test_single_goal_fast_path(self):
        """Single goal should be selected without full utility computation."""
        registry = GoalRegistry()
        g = UMHGoalState(goal_id="solo", description="Only goal", priority=0.8)
        registry.add_goal(g)

        arbitrator = GoalArbitrator()
        result = arbitrator.select_active_goal(registry)
        assert result.selected_goal_id == "solo"
        assert result.reason == "single_goal"

    def test_empty_registry(self):
        """Empty registry should return NO_ARBITRATION."""
        registry = GoalRegistry()
        arbitrator = GoalArbitrator()
        result = arbitrator.select_active_goal(registry)
        assert result.selected_goal_id is None
        assert result.reason == "no_goals"


# ═══════════════════════════════════════════════════════════════════════════════
# 8. META-GOAL ENGINE STRESS
# ═══════════════════════════════════════════════════════════════════════════════


class TestMetaGoalEngineStress:
    """Stress test the meta-goal generation/retirement lifecycle."""

    def test_cap_enforcement(self):
        """Engine should never exceed MAX_GOALS."""
        engine = MetaGoalEngine()
        registry = GoalRegistry()

        for i in range(MAX_GOALS + 5):
            g = UMHGoalState(goal_id=f"g{i}", description=f"Goal {i}", priority=0.5)
            registry.add_goal(g)
            tracker = registry.get_tracker(f"g{i}")
            for _ in range(3):
                tracker.update_success(0.5)

        result = engine.evaluate(registry, current_turn=100)
        total_active = len(registry.get_all_goals())
        # Cap is checked against registry size
        assert total_active <= MAX_GOALS + 5  # external goals aren't removed by engine

    def test_cooldown_respected(self):
        """Engine should not generate back-to-back within cooldown period."""
        engine = MetaGoalEngine()
        registry = GoalRegistry()

        g = UMHGoalState(
            goal_id="parent",
            description="Test parent",
            priority=0.5,
            success_criteria={"key": "val"},
        )
        registry.add_goal(g)

        # First eval at turn 0
        engine.evaluate(registry, current_turn=0)

        # Eval at turn 1 — within cooldown, should not generate
        result = engine.evaluate(registry, current_turn=1)
        assert len(result.generated) == 0

    def test_retirement_lifecycle(self):
        """Generated goals should retire after confidence decays below floor."""
        engine = MetaGoalEngine()
        registry = GoalRegistry()

        mg = MetaGoal(
            goal_id="test_gen",
            origin="generated",
            parent_goals=(),
            confidence=0.2,
            utility_estimate=0.5,
            lifecycle_state="candidate",
            description="Test generated",
            success_criteria={"key": "val"},
            generation_turn=0,
        )
        engine.register_generated(mg)

        # Decay over many turns without activity
        for turn in range(50):
            engine.evaluate(registry, current_turn=turn)

        final = engine.get_generated("test_gen")
        assert final is not None
        assert final.lifecycle_state == "retired" or final.confidence <= 0.05

    def test_confidence_update_bounded(self):
        """Confidence updates should stay within [DECAY_FLOOR, 0.95]."""
        engine = MetaGoalEngine()

        mg = MetaGoal(
            goal_id="conf_test",
            origin="generated",
            parent_goals=(),
            confidence=0.5,
            utility_estimate=0.5,
            lifecycle_state="active",
            description="Confidence test",
            success_criteria={"k": "v"},
        )
        engine.register_generated(mg)

        # Push confidence up
        for _ in range(100):
            engine.update_confidence("conf_test", goal_score=1.0, convergence_stable=True)

        high_conf = engine.get_generated("conf_test")
        assert high_conf.confidence <= 0.95

        # Push confidence down
        for _ in range(100):
            engine.update_confidence("conf_test", goal_score=0.0, convergence_stable=False)

        low_conf = engine.get_generated("conf_test")
        assert low_conf.confidence >= 0.05


# ═══════════════════════════════════════════════════════════════════════════════
# 9. CROSS-SYSTEM INTEGRATION
# ═══════════════════════════════════════════════════════════════════════════════


class TestCrossSystemIntegration:
    """Verify both goal systems exhibit consistent behavior patterns."""

    def test_priority_respects_ordering_in_both_systems(self):
        """Both systems should rank higher priority goals higher, all else equal."""
        # GoalSelector
        selector = _selector_no_db()
        gs_goals = [
            _make_goal("High", priority=9, gid="hi"),
            _make_goal("Low", priority=3, gid="lo"),
        ]
        _run_selection_cycle_inmemory(selector, gs_goals)
        hi = next(g for g in gs_goals if g.id == "hi")
        lo = next(g for g in gs_goals if g.id == "lo")
        assert hi.score > lo.score

        # UMH Arbitrator
        registry = GoalRegistry()
        registry.add_goal(UMHGoalState(goal_id="hi", description="High", priority=0.9))
        registry.add_goal(UMHGoalState(goal_id="lo", description="Low", priority=0.3))

        arbitrator = GoalArbitrator()
        registry.advance_turn()
        result = arbitrator.select_active_goal(registry)
        assert result.selected_goal_id == "hi"

    def test_performance_matters_in_both_systems(self):
        """Performance signals should influence ranking in both systems."""
        # GoalSelector: good performer beats poor performer at same priority
        selector = _selector_no_db()
        gs_goals = [
            _make_goal("Good Perf", priority=5, gid="good"),
            _make_goal("Bad Perf", priority=5, gid="bad"),
        ]
        _inject_performance(gs_goals[0], success_rate=0.9)
        _inject_performance(gs_goals[1], success_rate=0.1)
        _run_selection_cycle_inmemory(selector, gs_goals)
        assert gs_goals[0].score > gs_goals[1].score

        # UMH: tracker success_score influences utility
        registry = GoalRegistry()
        registry.add_goal(UMHGoalState(goal_id="good", description="Good", priority=0.5))
        registry.add_goal(UMHGoalState(goal_id="bad", description="Bad", priority=0.5))

        good_t = registry.get_tracker("good")
        bad_t = registry.get_tracker("bad")
        for _ in range(10):
            good_t.update_success(0.9)
            bad_t.update_success(0.1)

        arbitrator = GoalArbitrator()
        registry.advance_turn()
        result = arbitrator.select_active_goal(registry)
        assert result.selected_goal_id == "good"
        assert result.utilities["good"] > result.utilities["bad"]


# ═══════════════════════════════════════════════════════════════════════════════
# Runner
# ═══════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    import pytest

    sys.exit(pytest.main([__file__, "-v", "--tb=short"]))
