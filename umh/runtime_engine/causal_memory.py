"""
Causal transition memory — learns empirical action→outcome patterns.

Records what happens when action A is taken in context C, aggregates
into transition statistics, and produces bounded action biases based
on historical cause-effect relationships.

NOT planning. NOT simulation. Empirical pattern memory.

One-turn delayed: only uses data from completed turns. No circular
dependencies — the signal influences the *next* decision, never the
one that produced the data.

Deterministic. Bounded. No LLM calls. No randomness.
"""

from __future__ import annotations

from dataclasses import dataclass, field

# ─── Constants ──────────────────────────────────────────────────────

MAX_TRANSITIONS = 500
MIN_OBSERVATIONS = 10
EMA_ALPHA = 0.1
MAX_BIAS = 0.05
CONFIDENCE_MIN_SAMPLES = 5
CONFIDENCE_FULL_SAMPLES = 30
VARIANCE_DAMPING = 2.0


# ─── Helpers ────────────────────────────────────────────────────────


def _clamp(v: float, lo: float, hi: float) -> float:
    if v < lo:
        return lo
    if v > hi:
        return hi
    return v


# ─── Data structures ───────────────────────────────────────────────


@dataclass(frozen=True)
class TransitionRecord:
    """Single observed transition. Immutable snapshot."""

    context_type: str
    action: str
    reward_delta: float
    objective_delta: float
    next_context_type: str
    step: int


@dataclass
class TransitionStats:
    """Aggregated statistics for a (context_type, action) pair."""

    context_type: str
    action: str
    count: int = 0
    ema_reward_delta: float = 0.0
    ema_objective_delta: float = 0.0
    positive_count: int = 0
    ema_variance: float = 0.0

    @property
    def avg_reward_delta(self) -> float:
        return self.ema_reward_delta

    @property
    def avg_objective_delta(self) -> float:
        return self.ema_objective_delta

    @property
    def success_rate(self) -> float:
        if self.count == 0:
            return 0.0
        return self.positive_count / self.count

    @property
    def stability_score(self) -> float:
        if self.ema_variance < 1e-9:
            return 1.0
        return _clamp(1.0 / (1.0 + self.ema_variance * VARIANCE_DAMPING), 0.0, 1.0)

    def update(self, reward_delta: float, objective_delta: float) -> None:
        alpha = EMA_ALPHA
        if self.count == 0:
            self.ema_reward_delta = reward_delta
            self.ema_objective_delta = objective_delta
            self.ema_variance = 0.0
        else:
            diff = reward_delta - self.ema_reward_delta
            self.ema_variance = (1.0 - alpha) * self.ema_variance + alpha * diff * diff
            self.ema_reward_delta = (
                alpha * reward_delta + (1.0 - alpha) * self.ema_reward_delta
            )
            self.ema_objective_delta = (
                alpha * objective_delta + (1.0 - alpha) * self.ema_objective_delta
            )

        self.count += 1
        if reward_delta > 0.0:
            self.positive_count += 1

    def to_dict(self) -> dict:
        return {
            "context_type": self.context_type,
            "action": self.action,
            "count": self.count,
            "ema_reward_delta": round(self.ema_reward_delta, 6),
            "ema_objective_delta": round(self.ema_objective_delta, 6),
            "positive_count": self.positive_count,
            "ema_variance": round(self.ema_variance, 6),
        }


@dataclass(frozen=True)
class CausalSignal:
    """Output of causal memory: bounded action biases."""

    action_bias: dict[str, float]
    confidence: float
    matched_context: str
    reason: str

    def to_dict(self) -> dict:
        return {
            "action_bias": {k: round(v, 6) for k, v in self.action_bias.items()},
            "confidence": round(self.confidence, 4),
            "matched_context": self.matched_context,
            "reason": self.reason,
        }


NO_CAUSAL_SIGNAL = CausalSignal(
    action_bias={},
    confidence=0.0,
    matched_context="",
    reason="no_data",
)


# ─── Engine ─────────────────────────────────────────────────────────


class CausalMemoryEngine:
    """Learns empirical action→outcome patterns from transition data.

    Stores aggregated TransitionStats per (context_type, action).
    Produces bounded action biases for decision scoring.
    """

    def __init__(self) -> None:
        self._stats: dict[tuple[str, str], TransitionStats] = {}
        self._total_observations: int = 0
        self._prev_context_type: str = "unknown"
        self._prev_action: str = ""
        self._prev_reward: float = 0.0
        self._prev_objective: float = 0.0

    def record_transition(
        self,
        context_type: str,
        action: str,
        reward: float,
        objective_value: float,
    ) -> None:
        """Record a completed turn's data. Updates stats one turn delayed."""
        if self._prev_action:
            reward_delta = reward - self._prev_reward
            objective_delta = objective_value - self._prev_objective

            key = (self._prev_context_type, self._prev_action)
            if key not in self._stats:
                self._stats[key] = TransitionStats(
                    context_type=self._prev_context_type,
                    action=self._prev_action,
                )
            self._stats[key].update(reward_delta, objective_delta)
            self._total_observations += 1

            self._prune_if_needed()

        self._prev_context_type = context_type
        self._prev_action = action
        self._prev_reward = reward
        self._prev_objective = objective_value

    def compute_signal(
        self,
        current_context: str,
        available_actions: list[str] | None = None,
    ) -> CausalSignal:
        """Produce action biases based on historical transitions in this context."""
        context_stats = [
            s
            for s in self._stats.values()
            if s.context_type == current_context and s.count >= MIN_OBSERVATIONS
        ]

        if not context_stats:
            return NO_CAUSAL_SIGNAL

        if available_actions is not None:
            action_set = set(available_actions)
            context_stats = [s for s in context_stats if s.action in action_set]

        if not context_stats:
            return NO_CAUSAL_SIGNAL

        weighted_scores: dict[str, float] = {}
        for s in context_stats:
            score = (
                0.5 * s.avg_reward_delta
                + 0.3 * s.avg_objective_delta
                + 0.2 * s.success_rate
            )
            weighted_scores[s.action] = score

        if not weighted_scores:
            return NO_CAUSAL_SIGNAL

        mean_score = sum(weighted_scores.values()) / len(weighted_scores)

        raw_bias: dict[str, float] = {}
        for action, score in weighted_scores.items():
            raw_bias[action] = score - mean_score

        max_raw = max(abs(v) for v in raw_bias.values()) if raw_bias else 1.0
        if max_raw < 1e-9:
            return CausalSignal(
                action_bias={},
                confidence=0.0,
                matched_context=current_context,
                reason="no_differentiation",
            )

        scale = MAX_BIAS / max(max_raw, MAX_BIAS)

        confidence = self._compute_confidence(context_stats)

        action_bias: dict[str, float] = {}
        for action, bias in raw_bias.items():
            scaled = bias * scale * confidence
            clamped = _clamp(scaled, -MAX_BIAS, MAX_BIAS)
            if abs(clamped) > 1e-6:
                action_bias[action] = clamped

        if not action_bias:
            return CausalSignal(
                action_bias={},
                confidence=confidence,
                matched_context=current_context,
                reason="biases_too_small",
            )

        return CausalSignal(
            action_bias=action_bias,
            confidence=confidence,
            matched_context=current_context,
            reason="causal_bias_applied",
        )

    def _compute_confidence(self, stats_list: list[TransitionStats]) -> float:
        if not stats_list:
            return 0.0

        total_count = sum(s.count for s in stats_list)
        sample_conf = _clamp(
            (total_count - CONFIDENCE_MIN_SAMPLES)
            / max(CONFIDENCE_FULL_SAMPLES - CONFIDENCE_MIN_SAMPLES, 1),
            0.0,
            1.0,
        )

        avg_stability = sum(s.stability_score for s in stats_list) / len(stats_list)

        avg_consistency = 0.0
        for s in stats_list:
            sr = s.success_rate
            avg_consistency += max(sr, 1.0 - sr)
        avg_consistency /= len(stats_list)

        return _clamp(
            sample_conf * 0.4 + avg_stability * 0.3 + avg_consistency * 0.3, 0.0, 1.0
        )

    def _prune_if_needed(self) -> None:
        if self._total_observations <= MAX_TRANSITIONS:
            return
        if len(self._stats) <= 2:
            return
        weakest_key = min(self._stats, key=lambda k: self._stats[k].count)
        if self._stats[weakest_key].count < MIN_OBSERVATIONS:
            del self._stats[weakest_key]

    # ─── Persistence ────────────────────────────────────────────────

    def snapshot(self) -> dict:
        return {
            "version": 1,
            "total_observations": self._total_observations,
            "prev_context_type": self._prev_context_type,
            "prev_action": self._prev_action,
            "prev_reward": self._prev_reward,
            "prev_objective": self._prev_objective,
            "stats": {f"{k[0]}|{k[1]}": v.to_dict() for k, v in self._stats.items()},
        }

    def restore(self, data: dict | None) -> None:
        if not data or not isinstance(data, dict):
            return

        self._total_observations = int(data.get("total_observations", 0))
        self._prev_context_type = str(data.get("prev_context_type", "unknown"))
        self._prev_action = str(data.get("prev_action", ""))
        self._prev_reward = float(data.get("prev_reward", 0.0))
        self._prev_objective = float(data.get("prev_objective", 0.0))

        self._stats = {}
        for _key_str, sd in data.get("stats", {}).items():
            if not isinstance(sd, dict):
                continue
            ctx = str(sd.get("context_type", ""))
            act = str(sd.get("action", ""))
            if not ctx or not act:
                continue
            ts = TransitionStats(context_type=ctx, action=act)
            ts.count = int(sd.get("count", 0))
            ts.ema_reward_delta = float(sd.get("ema_reward_delta", 0.0))
            ts.ema_objective_delta = float(sd.get("ema_objective_delta", 0.0))
            ts.positive_count = int(sd.get("positive_count", 0))
            ts.ema_variance = float(sd.get("ema_variance", 0.0))
            self._stats[(ctx, act)] = ts

    def reset(self) -> None:
        self.__init__()

    @property
    def observation_count(self) -> int:
        return self._total_observations

    @property
    def context_action_pairs(self) -> int:
        return len(self._stats)


# ─── Pipeline integration ──────────────────────────────────────────


def apply_causal_bias(
    strategy_scores: dict[str, float],
    signal: CausalSignal,
) -> dict[str, float]:
    """Apply bounded causal biases to strategy scores.

    Rules:
    - additive only
    - bounded ±MAX_BIAS
    - cannot invert clear winner (gap > MAX_BIAS)
    - scaled by confidence
    """
    if not signal.action_bias:
        return strategy_scores

    if not strategy_scores:
        return strategy_scores

    sorted_scores = sorted(strategy_scores.values(), reverse=True)
    leader_gap = sorted_scores[0] - sorted_scores[1] if len(sorted_scores) >= 2 else 0.0

    adjusted = dict(strategy_scores)
    for action, bias in signal.action_bias.items():
        if action in adjusted:
            if (
                leader_gap > MAX_BIAS
                and bias < 0
                and adjusted[action] == sorted_scores[0]
            ):
                continue
            adjusted[action] = adjusted[action] + bias

    return adjusted
