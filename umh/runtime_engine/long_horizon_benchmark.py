"""
Long-horizon stability & drift validation harness for EOS.

Runs EOS and baselines for 1k–10k turns across six deterministic scenarios,
measures drift, oscillation, lock-in, and recovery properties, and produces
structured stability reports.

Read-only with respect to core EOS logic — measurement only, no fixes.

Scenarios:
    STATIC_STABLE    — fixed environment, tests convergence stability
    PERIODIC_SHIFT   — reward shifts every N turns, tests repeated adaptation
    ADVERSARIAL_FLIP — reward inverts then restores, tests trap recovery
    NOISY_STATIONARY — static optimum with seeded noise, tests drift resistance
    SLOW_DRIFT       — gradual environment change, tests sensitivity
    MIXED_REGIME     — combines quiet, shift, noise, adversarial windows

Systems compared:
    eos_substrate, eos_exploration, eos_regime, static_weights, random, policy_only

Diagnostics:
    Oscillation, lock-in, drift, runaway adaptation, restart divergence
"""

from __future__ import annotations

import hashlib
import math
from dataclasses import dataclass, field
from typing import Any

from umh.runtime_engine.benchmark_env import (
    DecisionSystem,
    EOSDecisionSystem,
    EOSWithCorrectionSystem,
    EOSWithExplorationSystem,
    EOSWithRegimeSystem,
    PolicyOnlyBaseline,
    RandomBaseline,
    Scenario,
    StaticWeightsBaseline,
    run_simulation,
)


# ─── Constants ──────────────────────────────────────────────────────

DEFAULT_HORIZON = 1000
ROLLING_WINDOW = 50
SLOPE_TAIL_FRACTION = 0.20

# Detector thresholds
OSCILLATION_WINDOW = 20
OSCILLATION_SWITCH_RATE_THRESHOLD = 0.6
OSCILLATION_REWARD_GAIN_THRESHOLD = 0.01

LOCK_IN_WINDOW = 50
LOCK_IN_REWARD_DROP_THRESHOLD = 0.10

DRIFT_WINDOW = 200
DRIFT_SLOPE_THRESHOLD = -0.0001

RUNAWAY_WINDOW = 100
RUNAWAY_BIAS_GROWTH_THRESHOLD = 0.05

RESTART_DIVERGENCE_TOLERANCE = 0.02


# ─── Extended scenarios ─────────────────────────────────────────────


class StaticStableScenario(Scenario):
    """Fixed reward landscape over long horizon. action_0 is always best."""

    def __init__(self, n_actions: int = 4, seed: int = 42) -> None:
        super().__init__(n_actions, seed)
        self._rewards = {self.actions[i]: 1.0 - i * 0.2 for i in range(n_actions)}

    def evaluate_action(self, action: str, step: int) -> tuple[float, bool]:
        reward = self._rewards.get(action, 0.0)
        return reward, reward >= 0.5


class PeriodicShiftScenario(Scenario):
    """Reward shifts every `period` turns. Best action rotates."""

    def __init__(self, n_actions: int = 4, seed: int = 42, period: int = 200) -> None:
        super().__init__(n_actions, seed)
        self.period = period

    def evaluate_action(self, action: str, step: int) -> tuple[float, bool]:
        phase = (step // self.period) % self.n_actions
        idx = self.actions.index(action) if action in self.actions else 0
        shifted_idx = (idx - phase) % self.n_actions
        reward = 1.0 - shifted_idx * 0.2
        return reward, reward >= 0.5


class AdversarialFlipScenario(Scenario):
    """Reward inverts for a window then restores.

    Normal: action_0 best. Flip window [flip_start, flip_end): action_3 best.
    """

    def __init__(
        self,
        n_actions: int = 4,
        seed: int = 42,
        flip_start: int = 300,
        flip_end: int = 500,
    ) -> None:
        super().__init__(n_actions, seed)
        self.flip_start = flip_start
        self.flip_end = flip_end

    def evaluate_action(self, action: str, step: int) -> tuple[float, bool]:
        idx = self.actions.index(action) if action in self.actions else 0
        if self.flip_start <= step < self.flip_end:
            reward = idx * 0.2 + 0.2
        else:
            reward = 1.0 - idx * 0.2
        return reward, reward >= 0.5


class NoisyStationaryScenario(Scenario):
    """Static optimum with seeded noise. Tests noise-induced drift."""

    def __init__(
        self, n_actions: int = 4, seed: int = 42, noise_scale: float = 0.25
    ) -> None:
        super().__init__(n_actions, seed)
        self.noise_scale = noise_scale
        self._base = {self.actions[i]: 1.0 - i * 0.2 for i in range(n_actions)}

    def evaluate_action(self, action: str, step: int) -> tuple[float, bool]:
        base = self._base.get(action, 0.0)
        h = hashlib.sha256(f"{action}:{step}:{42}".encode()).hexdigest()
        noise = (int(h[:8], 16) / 0xFFFFFFFF - 0.5) * 2 * self.noise_scale
        reward = max(0.0, min(1.0, base + noise))
        return reward, reward >= 0.5


class SlowDriftScenario(Scenario):
    """Environment changes gradually. Best action shifts over time."""

    def __init__(
        self, n_actions: int = 4, seed: int = 42, drift_rate: float = 0.0005
    ) -> None:
        super().__init__(n_actions, seed)
        self.drift_rate = drift_rate

    def evaluate_action(self, action: str, step: int) -> tuple[float, bool]:
        idx = self.actions.index(action) if action in self.actions else 0
        base = 1.0 - idx * 0.2
        shift = step * self.drift_rate
        shifted = base - shift + idx * shift / max(self.n_actions - 1, 1)
        reward = max(0.0, min(1.0, shifted))
        return reward, reward >= 0.5


class MixedRegimeScenario(Scenario):
    """Combines quiet, shift, noise, and adversarial windows.

    0-199:   static (action_0 best)
    200-399: noisy static
    400-599: shift (action_2 best)
    600-799: adversarial flip (action_3 best)
    800+:    return to static (action_0 best)
    """

    def __init__(self, n_actions: int = 4, seed: int = 42) -> None:
        super().__init__(n_actions, seed)

    def evaluate_action(self, action: str, step: int) -> tuple[float, bool]:
        idx = self.actions.index(action) if action in self.actions else 0
        phase = step % 1000

        if phase < 200:
            reward = 1.0 - idx * 0.2
        elif phase < 400:
            base = 1.0 - idx * 0.2
            h = hashlib.sha256(f"{action}:{step}:mixed".encode()).hexdigest()
            noise = (int(h[:8], 16) / 0xFFFFFFFF - 0.5) * 0.4
            reward = max(0.0, min(1.0, base + noise))
        elif phase < 600:
            shifted = (idx - 2) % self.n_actions
            reward = 1.0 - shifted * 0.2
        elif phase < 800:
            reward = idx * 0.2 + 0.2
        else:
            reward = 1.0 - idx * 0.2

        return reward, reward >= 0.5


# ─── Metrics dataclasses ───────────────────────────────────────────


@dataclass(frozen=True)
class RewardMetrics:
    avg_reward: float
    cumulative_reward: float
    rolling_mean_final: float
    rolling_std_final: float

    def to_dict(self) -> dict:
        return {
            "avg_reward": round(self.avg_reward, 6),
            "cumulative_reward": round(self.cumulative_reward, 4),
            "rolling_mean_final": round(self.rolling_mean_final, 6),
            "rolling_std_final": round(self.rolling_std_final, 6),
        }


@dataclass(frozen=True)
class StabilityMetrics:
    action_switch_rate: float
    exploration_activation_rate: float
    regime_activation_rate: float
    objective_volatility: float

    def to_dict(self) -> dict:
        return {
            "action_switch_rate": round(self.action_switch_rate, 6),
            "exploration_activation_rate": round(self.exploration_activation_rate, 6),
            "regime_activation_rate": round(self.regime_activation_rate, 6),
            "objective_volatility": round(self.objective_volatility, 6),
        }


@dataclass(frozen=True)
class RecoveryMetrics:
    shift_recovery_times: tuple[int, ...]
    avg_recovery_time: float
    recovery_degradation: float

    def to_dict(self) -> dict:
        return {
            "shift_recovery_times": list(self.shift_recovery_times),
            "avg_recovery_time": round(self.avg_recovery_time, 2),
            "recovery_degradation": round(self.recovery_degradation, 6),
        }


@dataclass(frozen=True)
class DriftMetrics:
    reward_slope_tail: float
    strategy_concentration: float
    false_lock_in_episodes: int

    def to_dict(self) -> dict:
        return {
            "reward_slope_tail": round(self.reward_slope_tail, 8),
            "strategy_concentration": round(self.strategy_concentration, 6),
            "false_lock_in_episodes": self.false_lock_in_episodes,
        }


@dataclass(frozen=True)
class SafetyMetrics:
    oscillation_episodes: int
    lock_in_episodes: int
    drift_episodes: int
    runaway_episodes: int

    def to_dict(self) -> dict:
        return {
            "oscillation_episodes": self.oscillation_episodes,
            "lock_in_episodes": self.lock_in_episodes,
            "drift_episodes": self.drift_episodes,
            "runaway_episodes": self.runaway_episodes,
        }


@dataclass(frozen=True)
class RestartContinuityMetrics:
    uninterrupted_avg_reward: float
    restarted_avg_reward: float
    divergence: float
    within_tolerance: bool

    def to_dict(self) -> dict:
        return {
            "uninterrupted_avg_reward": round(self.uninterrupted_avg_reward, 6),
            "restarted_avg_reward": round(self.restarted_avg_reward, 6),
            "divergence": round(self.divergence, 6),
            "within_tolerance": self.within_tolerance,
        }


NO_RESTART_METRICS = RestartContinuityMetrics(
    uninterrupted_avg_reward=0.0,
    restarted_avg_reward=0.0,
    divergence=0.0,
    within_tolerance=True,
)


@dataclass(frozen=True)
class StabilityDiagnostics:
    oscillation_detected: bool
    lock_in_detected: bool
    drift_detected: bool
    runaway_detected: bool
    details: dict

    def to_dict(self) -> dict:
        return {
            "oscillation_detected": self.oscillation_detected,
            "lock_in_detected": self.lock_in_detected,
            "drift_detected": self.drift_detected,
            "runaway_detected": self.runaway_detected,
            "details": self.details,
        }


@dataclass(frozen=True)
class LongHorizonRunResult:
    system_name: str
    scenario_name: str
    horizon: int
    seed: int
    reward_metrics: RewardMetrics
    stability_metrics: StabilityMetrics
    recovery_metrics: RecoveryMetrics
    drift_metrics: DriftMetrics
    safety_metrics: SafetyMetrics
    diagnostics: StabilityDiagnostics
    restart_continuity: RestartContinuityMetrics

    def to_dict(self) -> dict:
        return {
            "system_name": self.system_name,
            "scenario_name": self.scenario_name,
            "horizon": self.horizon,
            "seed": self.seed,
            "reward_metrics": self.reward_metrics.to_dict(),
            "stability_metrics": self.stability_metrics.to_dict(),
            "recovery_metrics": self.recovery_metrics.to_dict(),
            "drift_metrics": self.drift_metrics.to_dict(),
            "safety_metrics": self.safety_metrics.to_dict(),
            "diagnostics": self.diagnostics.to_dict(),
            "restart_continuity": self.restart_continuity.to_dict(),
        }


# ─── Metric computation ────────────────────────────────────────────


def compute_reward_metrics(rewards: list[float]) -> RewardMetrics:
    n = len(rewards)
    if n == 0:
        return RewardMetrics(0.0, 0.0, 0.0, 0.0)
    avg = sum(rewards) / n
    cumulative = sum(rewards)

    w = min(ROLLING_WINDOW, n)
    tail = rewards[-w:]
    rm = sum(tail) / w
    rs = math.sqrt(sum((r - rm) ** 2 for r in tail) / max(w - 1, 1))

    return RewardMetrics(avg, cumulative, rm, rs)


def compute_stability_metrics(
    actions: list[str],
    rewards: list[float],
) -> StabilityMetrics:
    n = len(actions)
    if n < 2:
        return StabilityMetrics(0.0, 0.0, 0.0, 0.0)

    switches = sum(1 for i in range(1, n) if actions[i] != actions[i - 1])
    switch_rate = switches / (n - 1)

    obj_vol = 0.0
    if len(rewards) >= 2:
        deltas = [abs(rewards[i] - rewards[i - 1]) for i in range(1, len(rewards))]
        obj_vol = sum(deltas) / len(deltas)

    return StabilityMetrics(
        action_switch_rate=switch_rate,
        exploration_activation_rate=0.0,
        regime_activation_rate=0.0,
        objective_volatility=obj_vol,
    )


def compute_recovery_metrics(
    actions: list[str],
    rewards: list[float],
    scenario: Scenario,
    horizon: int,
) -> RecoveryMetrics:
    recovery_times: list[int] = []

    if isinstance(scenario, PeriodicShiftScenario):
        period = scenario.period
        num_shifts = horizon // period
        for shift_idx in range(1, num_shifts):
            shift_step = shift_idx * period
            if shift_step >= len(rewards):
                break
            window_end = min(shift_step + period, len(rewards))
            window_actions = actions[shift_step:window_end]

            best = _find_best_action_at(scenario, shift_step)
            recovery_t = None
            consecutive = 0
            for i, a in enumerate(window_actions):
                if a == best:
                    consecutive += 1
                    if consecutive >= 5:
                        recovery_t = i - 4
                        break
                else:
                    consecutive = 0

            if recovery_t is not None:
                recovery_times.append(recovery_t)

    if not recovery_times:
        return RecoveryMetrics((), 0.0, 0.0)

    avg_rt = sum(recovery_times) / len(recovery_times)
    degradation = 0.0
    if len(recovery_times) >= 2:
        first_half = recovery_times[: len(recovery_times) // 2]
        second_half = recovery_times[len(recovery_times) // 2 :]
        avg_first = sum(first_half) / len(first_half)
        avg_second = sum(second_half) / len(second_half)
        degradation = avg_second - avg_first

    return RecoveryMetrics(
        shift_recovery_times=tuple(recovery_times),
        avg_recovery_time=avg_rt,
        recovery_degradation=degradation,
    )


def _find_best_action_at(scenario: Scenario, step: int) -> str:
    best_r = -1.0
    best_a = scenario.actions[0]
    for a in scenario.actions:
        r, _ = scenario.evaluate_action(a, step)
        if r > best_r:
            best_r = r
            best_a = a
    return best_a


def compute_drift_metrics(
    rewards: list[float],
    actions: list[str],
) -> DriftMetrics:
    n = len(rewards)
    tail_start = int(n * (1.0 - SLOPE_TAIL_FRACTION))
    tail = rewards[tail_start:]

    slope = 0.0
    if len(tail) >= 2:
        slope = _linear_slope(tail)

    action_set = set(actions)
    if len(action_set) > 0 and n > 0:
        from collections import Counter

        counts = Counter(actions)
        max_count = max(counts.values())
        concentration = max_count / n
    else:
        concentration = 1.0

    lock_in = detect_lock_in(actions, rewards)

    return DriftMetrics(
        reward_slope_tail=slope,
        strategy_concentration=concentration,
        false_lock_in_episodes=lock_in,
    )


def _linear_slope(values: list[float]) -> float:
    n = len(values)
    if n < 2:
        return 0.0
    sx = sum(range(n))
    sy = sum(values)
    sxx = sum(i * i for i in range(n))
    sxy = sum(i * v for i, v in enumerate(values))
    denom = n * sxx - sx * sx
    if abs(denom) < 1e-15:
        return 0.0
    return (n * sxy - sx * sy) / denom


# ─── Diagnostic detectors ──────────────────────────────────────────


def detect_oscillation(actions: list[str], rewards: list[float]) -> int:
    """Count episodes of high-frequency action switching without reward gain."""
    episodes = 0
    n = len(actions)
    for start in range(0, n - OSCILLATION_WINDOW, OSCILLATION_WINDOW // 2):
        end = min(start + OSCILLATION_WINDOW, n)
        window_actions = actions[start:end]
        window_rewards = rewards[start:end]

        switches = sum(
            1
            for i in range(1, len(window_actions))
            if window_actions[i] != window_actions[i - 1]
        )
        switch_rate = switches / max(len(window_actions) - 1, 1)

        if len(window_rewards) >= 2:
            reward_gain = window_rewards[-1] - window_rewards[0]
        else:
            reward_gain = 0.0

        if (
            switch_rate >= OSCILLATION_SWITCH_RATE_THRESHOLD
            and abs(reward_gain) < OSCILLATION_REWARD_GAIN_THRESHOLD
        ):
            episodes += 1

    return episodes


def detect_lock_in(actions: list[str], rewards: list[float]) -> int:
    """Count episodes where same action persists despite degrading reward."""
    episodes = 0
    n = len(actions)
    for start in range(0, n - LOCK_IN_WINDOW, LOCK_IN_WINDOW // 2):
        end = min(start + LOCK_IN_WINDOW, n)
        window_actions = actions[start:end]
        window_rewards = rewards[start:end]

        unique = set(window_actions)
        if len(unique) > 1:
            continue

        if len(window_rewards) < 2:
            continue

        first_half = window_rewards[: len(window_rewards) // 2]
        second_half = window_rewards[len(window_rewards) // 2 :]
        avg_first = sum(first_half) / len(first_half)
        avg_second = sum(second_half) / len(second_half)

        if avg_first - avg_second > LOCK_IN_REWARD_DROP_THRESHOLD:
            episodes += 1

    return episodes


def detect_drift(rewards: list[float]) -> int:
    """Count non-overlapping windows with negative reward slope in stable environment."""
    episodes = 0
    n = len(rewards)
    for start in range(0, n - DRIFT_WINDOW, DRIFT_WINDOW):
        end = min(start + DRIFT_WINDOW, n)
        window = rewards[start:end]
        slope = _linear_slope(window)
        if slope < DRIFT_SLOPE_THRESHOLD:
            episodes += 1
    return episodes


def detect_runaway(rewards: list[float]) -> int:
    """Count windows where reward variance grows without mean improvement."""
    episodes = 0
    n = len(rewards)
    for start in range(0, n - RUNAWAY_WINDOW, RUNAWAY_WINDOW):
        end = min(start + RUNAWAY_WINDOW, n)
        window = rewards[start:end]
        if len(window) < 4:
            continue
        half = len(window) // 2
        first_var = _variance(window[:half])
        second_var = _variance(window[half:])
        first_mean = sum(window[:half]) / half
        second_mean = sum(window[half:]) / (len(window) - half)

        if (
            second_var > first_var + RUNAWAY_BIAS_GROWTH_THRESHOLD
            and second_mean <= first_mean + 0.01
        ):
            episodes += 1
    return episodes


def _variance(values: list[float]) -> float:
    if len(values) < 2:
        return 0.0
    mean = sum(values) / len(values)
    return sum((v - mean) ** 2 for v in values) / (len(values) - 1)


def compute_safety_metrics(actions: list[str], rewards: list[float]) -> SafetyMetrics:
    return SafetyMetrics(
        oscillation_episodes=detect_oscillation(actions, rewards),
        lock_in_episodes=detect_lock_in(actions, rewards),
        drift_episodes=detect_drift(rewards),
        runaway_episodes=detect_runaway(rewards),
    )


def compute_diagnostics(
    actions: list[str], rewards: list[float]
) -> StabilityDiagnostics:
    safety = compute_safety_metrics(actions, rewards)
    return StabilityDiagnostics(
        oscillation_detected=safety.oscillation_episodes > 0,
        lock_in_detected=safety.lock_in_episodes > 0,
        drift_detected=safety.drift_episodes > 0,
        runaway_detected=safety.runaway_episodes > 0,
        details={
            "oscillation_episodes": safety.oscillation_episodes,
            "lock_in_episodes": safety.lock_in_episodes,
            "drift_episodes": safety.drift_episodes,
            "runaway_episodes": safety.runaway_episodes,
        },
    )


# ─── Restart continuity simulation ─────────────────────────────────


def simulate_restart_continuity(
    system_factory,
    scenario: Scenario,
    horizon: int,
    seed: int,
    restart_interval: int = 250,
) -> RestartContinuityMetrics:
    """Compare uninterrupted run vs run with periodic restarts.

    For systems that don't persist state (benchmark systems are stateless
    across resets), we measure whether the reward trajectory diverges when
    the system is periodically reset and restarted.
    """
    scenario.reset(seed)
    system_continuous = system_factory()
    system_continuous.reset()
    continuous_rewards: list[float] = []

    for step in range(horizon):
        env = scenario.get_state(step)
        action = system_continuous.choose_action(env)
        reward, success = scenario.evaluate_action(action, step)
        system_continuous.observe_outcome(action, reward, success, step)
        continuous_rewards.append(reward)

    scenario.reset(seed)
    restarted_rewards: list[float] = []
    system_restarted = system_factory()
    system_restarted.reset()

    for step in range(horizon):
        if step > 0 and step % restart_interval == 0:
            snap = None
            if hasattr(system_restarted, "get_state_snapshot"):
                snap = system_restarted.get_state_snapshot()
            system_restarted = system_factory()
            system_restarted.reset()
            if snap is not None and hasattr(system_restarted, "restore_state_snapshot"):
                system_restarted.restore_state_snapshot(snap)

        env = scenario.get_state(step)
        action = system_restarted.choose_action(env)
        reward, success = scenario.evaluate_action(action, step)
        system_restarted.observe_outcome(action, reward, success, step)
        restarted_rewards.append(reward)

    avg_cont = sum(continuous_rewards) / len(continuous_rewards)
    avg_rest = sum(restarted_rewards) / len(restarted_rewards)
    divergence = abs(avg_cont - avg_rest)

    return RestartContinuityMetrics(
        uninterrupted_avg_reward=avg_cont,
        restarted_avg_reward=avg_rest,
        divergence=divergence,
        within_tolerance=divergence <= RESTART_DIVERGENCE_TOLERANCE,
    )


# ─── Full run assembly ─────────────────────────────────────────────


def run_long_horizon(
    system: DecisionSystem,
    scenario: Scenario,
    horizon: int = DEFAULT_HORIZON,
    seed: int = 42,
    system_factory=None,
) -> LongHorizonRunResult:
    """Run a single system in a single scenario for `horizon` turns."""
    metrics = run_simulation(system, scenario, steps=horizon, seed=seed)

    reward_m = compute_reward_metrics(metrics.rewards)
    stability_m = compute_stability_metrics(metrics.actions_chosen, metrics.rewards)
    recovery_m = compute_recovery_metrics(
        metrics.actions_chosen, metrics.rewards, scenario, horizon
    )
    drift_m = compute_drift_metrics(metrics.rewards, metrics.actions_chosen)
    safety_m = compute_safety_metrics(metrics.actions_chosen, metrics.rewards)
    diag = compute_diagnostics(metrics.actions_chosen, metrics.rewards)

    restart_m = NO_RESTART_METRICS
    if system_factory is not None:
        restart_m = simulate_restart_continuity(system_factory, scenario, horizon, seed)

    return LongHorizonRunResult(
        system_name=system.name,
        scenario_name=type(scenario).__name__,
        horizon=horizon,
        seed=seed,
        reward_metrics=reward_m,
        stability_metrics=stability_m,
        recovery_metrics=recovery_m,
        drift_metrics=drift_m,
        safety_metrics=safety_m,
        diagnostics=diag,
        restart_continuity=restart_m,
    )


# ─── System factories ──────────────────────────────────────────────

SYSTEM_FACTORIES: dict[str, Any] = {
    "eos_substrate": EOSDecisionSystem,
    "eos_exploration": EOSWithExplorationSystem,
    "eos_regime": EOSWithRegimeSystem,
    "eos_corrected": EOSWithCorrectionSystem,
    "static_weights": lambda: StaticWeightsBaseline(fixed_weight=0.1),
    "random": lambda: RandomBaseline(seed=42),
    "policy_only": PolicyOnlyBaseline,
}


def get_all_scenarios(seed: int = 42) -> dict[str, Scenario]:
    return {
        "StaticStable": StaticStableScenario(seed=seed),
        "PeriodicShift": PeriodicShiftScenario(seed=seed, period=200),
        "AdversarialFlip": AdversarialFlipScenario(seed=seed),
        "NoisyStationary": NoisyStationaryScenario(seed=seed),
        "SlowDrift": SlowDriftScenario(seed=seed),
        "MixedRegime": MixedRegimeScenario(seed=seed),
    }


# ─── Full benchmark ────────────────────────────────────────────────


@dataclass
class LongHorizonBenchmarkResult:
    """All results from a full long-horizon benchmark run."""

    results: dict[str, dict[str, LongHorizonRunResult]] = field(default_factory=dict)
    horizon: int = DEFAULT_HORIZON
    seed: int = 42

    def to_dict(self) -> dict:
        return {
            "horizon": self.horizon,
            "seed": self.seed,
            "results": {
                sys_name: {scen_name: r.to_dict() for scen_name, r in scenarios.items()}
                for sys_name, scenarios in self.results.items()
            },
        }

    def summary_table(self) -> str:
        lines = [
            f"{'System':<20} {'Scenario':<20} {'AvgReward':>10} {'SwitchRate':>12} "
            f"{'Oscillate':>10} {'LockIn':>8} {'Drift':>7} {'Runaway':>8} "
            f"{'TailSlope':>10}"
        ]
        lines.append("-" * 115)

        for sys_name in sorted(self.results):
            for scen_name in sorted(self.results[sys_name]):
                r = self.results[sys_name][scen_name]
                lines.append(
                    f"{sys_name:<20} {scen_name:<20} "
                    f"{r.reward_metrics.avg_reward:>10.4f} "
                    f"{r.stability_metrics.action_switch_rate:>12.4f} "
                    f"{r.safety_metrics.oscillation_episodes:>10} "
                    f"{r.safety_metrics.lock_in_episodes:>8} "
                    f"{r.safety_metrics.drift_episodes:>7} "
                    f"{r.safety_metrics.runaway_episodes:>8} "
                    f"{r.drift_metrics.reward_slope_tail:>10.6f}"
                )

        return "\n".join(lines)


def run_full_long_horizon_benchmark(
    horizon: int = DEFAULT_HORIZON,
    seed: int = 42,
    systems: list[str] | None = None,
    scenarios: list[str] | None = None,
) -> LongHorizonBenchmarkResult:
    """Run all systems × all scenarios for the given horizon."""
    system_names = systems or list(SYSTEM_FACTORIES.keys())
    all_scenarios = get_all_scenarios(seed=seed)
    scenario_names = scenarios or list(all_scenarios.keys())

    result = LongHorizonBenchmarkResult(horizon=horizon, seed=seed)

    for sys_name in system_names:
        factory = SYSTEM_FACTORIES.get(sys_name)
        if factory is None:
            continue
        result.results[sys_name] = {}
        system = factory()

        for scen_name in scenario_names:
            scenario = all_scenarios.get(scen_name)
            if scenario is None:
                continue
            run_result = run_long_horizon(
                system=system,
                scenario=scenario,
                horizon=horizon,
                seed=seed,
                system_factory=factory,
            )
            result.results[sys_name][scen_name] = run_result

    return result
