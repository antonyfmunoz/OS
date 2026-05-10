"""
Forward rollout (foresight) — shallow simulation of future trajectories.

Uses learned signals from causal memory and credit assignment to estimate
short-horizon outcomes for each candidate action. Produces bounded biases
that nudge decisions toward actions with better expected trajectories.

NOT planning. NOT tree search. Deterministic, shallow, bounded foresight.

Stateless — reads from existing signal engines, produces no new state.
No snapshot/restore needed. No LLM calls. No randomness.
"""

from __future__ import annotations

from dataclasses import dataclass

# ─── Constants ──────────────────────────────────────────────────────

MAX_DEPTH = 3
GAMMA = 0.8
MAX_BIAS = 0.05
MIN_DATA_OBSERVATIONS = 5
REWARD_WEIGHT = 0.5
OBJECTIVE_WEIGHT = 0.5
CONFIDENCE_MIN_SIGNALS = 1
CONFIDENCE_FULL_SIGNALS = 3
AGREEMENT_WEIGHT = 0.4
DATA_WEIGHT = 0.3
VARIANCE_WEIGHT = 0.3
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
class RolloutResult:
    """Outcome of simulating a single action forward."""

    action: str
    expected_reward: float
    expected_objective: float
    trajectory_score: float
    steps_used: int
    confidence: float

    def to_dict(self) -> dict:
        return {
            "action": self.action,
            "expected_reward": round(self.expected_reward, 6),
            "expected_objective": round(self.expected_objective, 6),
            "trajectory_score": round(self.trajectory_score, 6),
            "steps_used": self.steps_used,
            "confidence": round(self.confidence, 4),
        }


@dataclass(frozen=True)
class ForesightSignal:
    """Output of foresight engine: bounded per-action trajectory biases."""

    action_bias: dict[str, float]
    confidence: float
    horizon: int
    reason: str
    rollouts: tuple[RolloutResult, ...] = ()

    def to_dict(self) -> dict:
        d: dict = {
            "action_bias": {k: round(v, 6) for k, v in self.action_bias.items()},
            "confidence": round(self.confidence, 4),
            "horizon": self.horizon,
            "reason": self.reason,
        }
        if self.rollouts:
            d["rollouts"] = [r.to_dict() for r in self.rollouts]
        return d


NO_FORESIGHT_SIGNAL = ForesightSignal(
    action_bias={},
    confidence=0.0,
    horizon=0,
    reason="no_data",
)


# ─── Engine ─────────────────────────────────────────────────────────


class ForesightEngine:
    """Shallow forward rollout using learned causal and credit signals.

    Stateless — all data comes from the causal memory and credit
    assignment engines passed at evaluation time. No internal state
    to persist or restore.
    """

    def simulate_action(
        self,
        action: str,
        context: str,
        causal_stats: dict | None = None,
        credit_accumulators: dict | None = None,
        depth: int = MAX_DEPTH,
    ) -> RolloutResult:
        """Simulate forward trajectory for one action.

        Uses causal memory stats to estimate immediate reward deltas
        and credit accumulators for delayed effect estimates. Decays
        each step by gamma^k.
        """
        depth = min(depth, MAX_DEPTH)
        total_reward = 0.0
        total_objective = 0.0
        steps_used = 0
        signals_found = 0

        causal_reward = 0.0
        causal_objective = 0.0
        causal_available = False

        if causal_stats and isinstance(causal_stats, dict):
            key = f"{context}|{action}"
            stat = causal_stats.get(key)
            if stat and isinstance(stat, dict):
                count = int(stat.get("count", 0))
                if count >= MIN_DATA_OBSERVATIONS:
                    causal_reward = float(stat.get("ema_reward_delta", 0.0))
                    causal_objective = float(stat.get("ema_objective_delta", 0.0))
                    causal_available = True
                    signals_found += 1

        credit_reward = 0.0
        credit_objective = 0.0
        credit_available = False

        if credit_accumulators and isinstance(credit_accumulators, dict):
            acc = credit_accumulators.get(action)
            if acc and isinstance(acc, dict):
                obs = int(acc.get("observation_count", 0))
                if obs >= 2:
                    credit_reward = float(acc.get("reward_credit", 0.0)) / max(obs, 1)
                    credit_objective = float(acc.get("objective_credit", 0.0)) / max(
                        obs, 1
                    )
                    credit_available = True
                    signals_found += 1

        if signals_found == 0:
            return RolloutResult(
                action=action,
                expected_reward=0.0,
                expected_objective=0.0,
                trajectory_score=0.0,
                steps_used=0,
                confidence=0.0,
            )

        for k in range(1, depth + 1):
            discount = GAMMA**k

            step_reward = 0.0
            step_objective = 0.0
            contrib_count = 0

            if causal_available:
                step_reward += causal_reward
                step_objective += causal_objective
                contrib_count += 1

            if credit_available:
                step_reward += credit_reward
                step_objective += credit_objective
                contrib_count += 1

            if contrib_count > 1:
                step_reward /= contrib_count
                step_objective /= contrib_count

            total_reward += discount * step_reward
            total_objective += discount * step_objective
            steps_used = k

        trajectory_score = (
            REWARD_WEIGHT * total_reward + OBJECTIVE_WEIGHT * total_objective
        )

        confidence = self._step_confidence(
            signals_found, causal_available, credit_available
        )

        return RolloutResult(
            action=action,
            expected_reward=total_reward,
            expected_objective=total_objective,
            trajectory_score=trajectory_score,
            steps_used=steps_used,
            confidence=confidence,
        )

    def compute_signal(
        self,
        available_actions: list[str],
        context: str,
        causal_stats: dict | None = None,
        credit_accumulators: dict | None = None,
        depth: int = MAX_DEPTH,
    ) -> ForesightSignal:
        """Evaluate all candidate actions and produce bounded biases."""
        if not available_actions:
            return NO_FORESIGHT_SIGNAL

        rollouts: list[RolloutResult] = []
        for action in available_actions:
            result = self.simulate_action(
                action=action,
                context=context,
                causal_stats=causal_stats,
                credit_accumulators=credit_accumulators,
                depth=depth,
            )
            rollouts.append(result)

        scored = [r for r in rollouts if r.steps_used > 0]
        if not scored:
            return NO_FORESIGHT_SIGNAL

        scores = {r.action: r.trajectory_score for r in scored}
        if not scores:
            return NO_FORESIGHT_SIGNAL

        mean_score = sum(scores.values()) / len(scores)
        centered = {action: score - mean_score for action, score in scores.items()}

        max_abs = max(abs(v) for v in centered.values()) if centered else 1.0
        if max_abs < 1e-9:
            return ForesightSignal(
                action_bias={},
                confidence=0.0,
                horizon=depth,
                reason="no_differentiation",
                rollouts=tuple(rollouts),
            )

        scale = MAX_BIAS / max(max_abs, MAX_BIAS)

        confidence = self._aggregate_confidence(scored)

        action_bias: dict[str, float] = {}
        for action, centered_score in centered.items():
            scaled = centered_score * scale * confidence
            clamped = _clamp(scaled, -MAX_BIAS, MAX_BIAS)
            if abs(clamped) > 1e-6:
                action_bias[action] = clamped

        if not action_bias:
            return ForesightSignal(
                action_bias={},
                confidence=confidence,
                horizon=depth,
                reason="biases_too_small",
                rollouts=tuple(rollouts),
            )

        return ForesightSignal(
            action_bias=action_bias,
            confidence=confidence,
            horizon=depth,
            reason="foresight_applied",
            rollouts=tuple(rollouts),
        )

    def _step_confidence(
        self,
        signals_found: int,
        causal_available: bool,
        credit_available: bool,
    ) -> float:
        data_conf = _clamp(
            (signals_found - CONFIDENCE_MIN_SIGNALS)
            / max(CONFIDENCE_FULL_SIGNALS - CONFIDENCE_MIN_SIGNALS, 1),
            0.0,
            1.0,
        )
        agreement = 1.0 if (causal_available and credit_available) else 0.5
        return _clamp(
            DATA_WEIGHT * data_conf
            + AGREEMENT_WEIGHT * agreement
            + VARIANCE_WEIGHT * 0.5,
            0.0,
            1.0,
        )

    def _aggregate_confidence(self, rollouts: list[RolloutResult]) -> float:
        if not rollouts:
            return 0.0
        avg_conf = sum(r.confidence for r in rollouts) / len(rollouts)

        scores = [r.trajectory_score for r in rollouts]
        if len(scores) < 2:
            variance = 0.0
        else:
            mean = sum(scores) / len(scores)
            variance = sum((s - mean) ** 2 for s in scores) / len(scores)
        stability = _clamp(1.0 / (1.0 + variance * VARIANCE_DAMPING), 0.0, 1.0)

        return _clamp(avg_conf * 0.6 + stability * 0.4, 0.0, 1.0)


# ─── Pipeline integration ──────────────────────────────────────────


def apply_foresight_bias(
    strategy_scores: dict[str, float],
    signal: ForesightSignal,
) -> dict[str, float]:
    """Apply bounded foresight biases to strategy scores.

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


# ─── Helpers for extracting engine data ─────────────────────────────


def extract_causal_stats(causal_mem: object) -> dict | None:
    """Extract serialized stats from a CausalMemoryEngine instance."""
    try:
        snap = causal_mem.snapshot()
        return snap.get("stats")
    except Exception:
        return None


def extract_credit_accumulators(credit_eng: object) -> dict | None:
    """Extract serialized accumulators from a CreditAssignmentEngine instance."""
    try:
        snap = credit_eng.snapshot()
        return snap.get("accumulators")
    except Exception:
        return None
