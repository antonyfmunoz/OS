"""
Temporal credit assignment — propagates outcome credit backward through time.

Upgrades causal memory from single-step (action → immediate outcome) to
multi-step (action → delayed impact over H turns). Uses exponential decay
(gamma^k) to distribute credit to earlier actions proportional to temporal
distance.

NOT planning. NOT simulation. Backward credit propagation from observed
outcomes to past actions.

Deterministic. Bounded. No LLM calls. No randomness.
"""

from __future__ import annotations

from dataclasses import dataclass, field

# ─── Constants ──────────────────────────────────────────────────────

MAX_TRACE_LENGTH = 20
MIN_TRACE_LENGTH = 5
GAMMA = 0.8
MAX_CREDIT = 0.05
REWARD_WEIGHT = 0.6
OBJECTIVE_WEIGHT = 0.4
CONFIDENCE_MIN_TRACE = 5
CONFIDENCE_FULL_TRACE = 15
VARIANCE_DAMPING = 2.0
MAX_CREDIT_ENTRIES = 200


# ─── Helpers ────────────────────────────────────────────────────────


def _clamp(v: float, lo: float, hi: float) -> float:
    if v < lo:
        return lo
    if v > hi:
        return hi
    return v


# ─── Data structures ───────────────────────────────────────────────


@dataclass(frozen=True)
class CreditSignal:
    """Output of credit assignment: bounded per-action credit adjustments."""

    action_credit: dict[str, float]
    horizon: int
    confidence: float
    reason: str

    def to_dict(self) -> dict:
        return {
            "action_credit": {k: round(v, 6) for k, v in self.action_credit.items()},
            "horizon": self.horizon,
            "confidence": round(self.confidence, 4),
            "reason": self.reason,
        }


NO_CREDIT_SIGNAL = CreditSignal(
    action_credit={},
    horizon=0,
    confidence=0.0,
    reason="no_data",
)


@dataclass
class CreditAccumulator:
    """Per-action accumulated credit from backward propagation."""

    action: str
    reward_credit: float = 0.0
    objective_credit: float = 0.0
    observation_count: int = 0
    positive_count: int = 0
    sum_sq_diff: float = 0.0
    ema_credit: float = 0.0

    @property
    def combined_credit(self) -> float:
        return (
            REWARD_WEIGHT * self.reward_credit
            + OBJECTIVE_WEIGHT * self.objective_credit
        )

    @property
    def consistency(self) -> float:
        if self.observation_count == 0:
            return 0.0
        rate = self.positive_count / self.observation_count
        return max(rate, 1.0 - rate)

    @property
    def variance(self) -> float:
        if self.observation_count < 2:
            return 0.0
        return self.sum_sq_diff / self.observation_count

    @property
    def stability(self) -> float:
        v = self.variance
        if v < 1e-9:
            return 1.0
        return _clamp(1.0 / (1.0 + v * VARIANCE_DAMPING), 0.0, 1.0)

    def to_dict(self) -> dict:
        return {
            "action": self.action,
            "reward_credit": round(self.reward_credit, 6),
            "objective_credit": round(self.objective_credit, 6),
            "observation_count": self.observation_count,
            "positive_count": self.positive_count,
            "sum_sq_diff": round(self.sum_sq_diff, 6),
            "ema_credit": round(self.ema_credit, 6),
        }


# ─── Engine ─────────────────────────────────────────────────────────


class CreditAssignmentEngine:
    """Propagates credit backward through a sliding window of recent turns.

    Each turn appends to the trace. When compute_signal() is called, credit
    from the latest reward delta is distributed backward to earlier actions
    with exponential decay (gamma^k). Accumulated credit per action produces
    bounded adjustments for strategy scoring.
    """

    def __init__(self) -> None:
        self._actions: list[str] = []
        self._contexts: list[str] = []
        self._rewards: list[float] = []
        self._objectives: list[float] = []
        self._accumulators: dict[str, CreditAccumulator] = {}
        self._total_propagations: int = 0

    def record_step(
        self,
        action: str,
        context: str,
        reward: float,
        objective_value: float,
    ) -> None:
        """Append one turn to the sliding window and propagate credit backward."""
        self._actions.append(action)
        self._contexts.append(context)
        self._rewards.append(reward)
        self._objectives.append(objective_value)

        if len(self._actions) > MAX_TRACE_LENGTH:
            self._actions = self._actions[-MAX_TRACE_LENGTH:]
            self._contexts = self._contexts[-MAX_TRACE_LENGTH:]
            self._rewards = self._rewards[-MAX_TRACE_LENGTH:]
            self._objectives = self._objectives[-MAX_TRACE_LENGTH:]

        if len(self._rewards) >= 2:
            self._propagate_credit()

    def _propagate_credit(self) -> None:
        """Distribute credit from latest reward delta backward through the trace."""
        n = len(self._rewards)
        reward_delta = self._rewards[-1] - self._rewards[-2]
        obj_delta = self._objectives[-1] - self._objectives[-2]

        horizon = min(n - 1, MAX_TRACE_LENGTH - 1)
        if horizon < 1:
            return

        for k in range(1, horizon + 1):
            idx = n - 1 - k
            if idx < 0:
                break

            weight = GAMMA**k
            past_action = self._actions[idx]

            if past_action not in self._accumulators:
                self._accumulators[past_action] = CreditAccumulator(action=past_action)

            acc = self._accumulators[past_action]
            r_credit = weight * reward_delta
            o_credit = weight * obj_delta

            combined = REWARD_WEIGHT * r_credit + OBJECTIVE_WEIGHT * o_credit
            diff = combined - acc.ema_credit
            acc.sum_sq_diff += diff * diff
            acc.ema_credit = 0.1 * combined + 0.9 * acc.ema_credit

            acc.reward_credit += r_credit
            acc.objective_credit += o_credit
            acc.observation_count += 1
            if reward_delta > 0:
                acc.positive_count += 1

        self._total_propagations += 1
        self._prune_if_needed()

    def compute_signal(
        self,
        available_actions: list[str] | None = None,
    ) -> CreditSignal:
        """Produce bounded per-action credit adjustments."""
        if len(self._rewards) < MIN_TRACE_LENGTH:
            return NO_CREDIT_SIGNAL

        candidates = list(self._accumulators.values())
        if available_actions is not None:
            action_set = set(available_actions)
            candidates = [a for a in candidates if a.action in action_set]

        candidates = [a for a in candidates if a.observation_count >= 2]

        if not candidates:
            return NO_CREDIT_SIGNAL

        raw_credit: dict[str, float] = {}
        for acc in candidates:
            avg = acc.combined_credit / max(acc.observation_count, 1)
            raw_credit[acc.action] = avg

        if not raw_credit:
            return NO_CREDIT_SIGNAL

        mean_credit = sum(raw_credit.values()) / len(raw_credit)
        centered: dict[str, float] = {
            action: credit - mean_credit for action, credit in raw_credit.items()
        }

        max_abs = max(abs(v) for v in centered.values()) if centered else 1.0
        if max_abs < 1e-9:
            return CreditSignal(
                action_credit={},
                horizon=len(self._rewards),
                confidence=0.0,
                reason="no_differentiation",
            )

        scale = MAX_CREDIT / max(max_abs, MAX_CREDIT)
        confidence = self._compute_confidence(candidates)

        action_credit: dict[str, float] = {}
        for action, credit in centered.items():
            scaled = credit * scale * confidence
            clamped = _clamp(scaled, -MAX_CREDIT, MAX_CREDIT)
            if abs(clamped) > 1e-6:
                action_credit[action] = clamped

        if not action_credit:
            return CreditSignal(
                action_credit={},
                horizon=len(self._rewards),
                confidence=confidence,
                reason="credits_too_small",
            )

        return CreditSignal(
            action_credit=action_credit,
            horizon=len(self._rewards),
            confidence=confidence,
            reason="credit_applied",
        )

    def _compute_confidence(self, accumulators: list[CreditAccumulator]) -> float:
        if not accumulators:
            return 0.0

        trace_len = len(self._rewards)
        trace_conf = _clamp(
            (trace_len - CONFIDENCE_MIN_TRACE)
            / max(CONFIDENCE_FULL_TRACE - CONFIDENCE_MIN_TRACE, 1),
            0.0,
            1.0,
        )

        avg_stability = sum(a.stability for a in accumulators) / len(accumulators)
        avg_consistency = sum(a.consistency for a in accumulators) / len(accumulators)

        return _clamp(
            trace_conf * 0.4 + avg_stability * 0.3 + avg_consistency * 0.3,
            0.0,
            1.0,
        )

    def _prune_if_needed(self) -> None:
        if len(self._accumulators) <= MAX_CREDIT_ENTRIES:
            return
        weakest = min(
            self._accumulators,
            key=lambda k: self._accumulators[k].observation_count,
        )
        if self._accumulators[weakest].observation_count < 3:
            del self._accumulators[weakest]

    # ─── Persistence ────────────────────────────────────────────────

    def snapshot(self) -> dict:
        return {
            "version": 1,
            "actions": list(self._actions),
            "contexts": list(self._contexts),
            "rewards": [round(r, 6) for r in self._rewards],
            "objectives": [round(o, 6) for o in self._objectives],
            "total_propagations": self._total_propagations,
            "accumulators": {k: v.to_dict() for k, v in self._accumulators.items()},
        }

    def restore(self, data: dict | None) -> None:
        if not data or not isinstance(data, dict):
            return

        self._actions = list(data.get("actions", []))
        self._contexts = list(data.get("contexts", []))
        self._rewards = [float(r) for r in data.get("rewards", [])]
        self._objectives = [float(o) for o in data.get("objectives", [])]
        self._total_propagations = int(data.get("total_propagations", 0))

        self._accumulators = {}
        for key, ad in data.get("accumulators", {}).items():
            if not isinstance(ad, dict):
                continue
            action = str(ad.get("action", key))
            if not action:
                continue
            acc = CreditAccumulator(action=action)
            acc.reward_credit = float(ad.get("reward_credit", 0.0))
            acc.objective_credit = float(ad.get("objective_credit", 0.0))
            acc.observation_count = int(ad.get("observation_count", 0))
            acc.positive_count = int(ad.get("positive_count", 0))
            acc.sum_sq_diff = float(ad.get("sum_sq_diff", 0.0))
            acc.ema_credit = float(ad.get("ema_credit", 0.0))
            self._accumulators[action] = acc

    def reset(self) -> None:
        self.__init__()

    @property
    def trace_length(self) -> int:
        return len(self._rewards)

    @property
    def propagation_count(self) -> int:
        return self._total_propagations

    @property
    def tracked_actions(self) -> int:
        return len(self._accumulators)


# ─── Pipeline integration ──────────────────────────────────────────


def apply_credit_adjustment(
    strategy_scores: dict[str, float],
    signal: CreditSignal,
) -> dict[str, float]:
    """Apply bounded credit adjustments to strategy scores.

    Rules:
    - additive only
    - bounded ±MAX_CREDIT
    - cannot invert clear winner (gap > MAX_CREDIT)
    - scaled by confidence
    """
    if not signal.action_credit:
        return strategy_scores

    if not strategy_scores:
        return strategy_scores

    sorted_scores = sorted(strategy_scores.values(), reverse=True)
    leader_gap = sorted_scores[0] - sorted_scores[1] if len(sorted_scores) >= 2 else 0.0

    adjusted = dict(strategy_scores)
    for action, credit in signal.action_credit.items():
        if action in adjusted:
            if (
                leader_gap > MAX_CREDIT
                and credit < 0
                and adjusted[action] == sorted_scores[0]
            ):
                continue
            adjusted[action] = adjusted[action] + credit

    return adjusted
