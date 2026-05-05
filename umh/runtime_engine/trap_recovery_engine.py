"""
Trap recovery engine — contradiction enforcement for EOS.

Detects "high-confidence + low-reward persistence" and injects bounded
contradiction signals to break suboptimal equilibria.

NOT exploration. This is contradiction enforcement:
- Penalizes the dominant action when reward drops below historical peak
- Boosts alternatives proportionally
- Decays immediately when reward improves

Deterministic. Bounded. One-turn delayed. No randomness.
"""

from __future__ import annotations

from dataclasses import dataclass


STAGNATION_THRESHOLD = 5
REWARD_MISMATCH_RATIO = 0.7
CONFIDENCE_THRESHOLD = 0.7
MAX_TRAP_BIAS = 0.05
REWARD_HISTORY_WINDOW = 50
ROLLING_WINDOW = 10


def _clamp(v: float, lo: float, hi: float) -> float:
    if v < lo:
        return lo
    if v > hi:
        return hi
    return v


@dataclass(frozen=True)
class TrapSignal:
    """Immutable snapshot of trap detection state."""

    active: bool
    dominant_action: str | None
    trap_adjustment: float
    reward_mismatch: float
    stagnation_length: int
    reason: str

    def to_dict(self) -> dict:
        d: dict = {
            "active": self.active,
            "trap_adjustment": round(self.trap_adjustment, 6),
        }
        if self.active:
            d["dominant_action"] = self.dominant_action
            d["reward_mismatch"] = round(self.reward_mismatch, 4)
            d["stagnation_length"] = self.stagnation_length
            d["reason"] = self.reason
        return d


NO_TRAP_SIGNAL = TrapSignal(
    active=False,
    dominant_action=None,
    trap_adjustment=0.0,
    reward_mismatch=0.0,
    stagnation_length=0,
    reason="",
)


class TrapDetector:
    """Stateful trap detection over rolling reward history.

    Tracks reward peak, rolling reward, dominant action persistence,
    and stagnation length. Pure state machine — no randomness.
    """

    def __init__(self) -> None:
        self._reward_history: list[float] = []
        self._action_history: list[str] = []
        self._reward_peak: float = 0.0
        self._stagnation_count: int = 0
        self._last_improvement_step: int = 0
        self._step: int = 0
        self._reward_ema: float = 0.0

    def observe(self, action: str, reward: float) -> None:
        self._reward_history.append(reward)
        if len(self._reward_history) > REWARD_HISTORY_WINDOW:
            self._reward_history = self._reward_history[-REWARD_HISTORY_WINDOW:]

        self._action_history.append(action)
        if len(self._action_history) > REWARD_HISTORY_WINDOW:
            self._action_history = self._action_history[-REWARD_HISTORY_WINDOW:]

        alpha = 0.15
        self._reward_ema = alpha * reward + (1.0 - alpha) * self._reward_ema

        if reward > self._reward_peak:
            self._reward_peak = reward
            self._last_improvement_step = self._step
            self._stagnation_count = 0
        else:
            self._stagnation_count += 1

        self._step += 1

    def compute_signal(self, action_scores: dict[str, float]) -> TrapSignal:
        if self._step < ROLLING_WINDOW:
            return NO_TRAP_SIGNAL

        rolling = self._reward_history[-ROLLING_WINDOW:]
        rolling_avg = sum(rolling) / len(rolling)

        if self._reward_peak <= 0:
            return NO_TRAP_SIGNAL

        mismatch = 1.0 - (rolling_avg / self._reward_peak)

        recent_actions = self._action_history[-ROLLING_WINDOW:]
        if not recent_actions:
            return NO_TRAP_SIGNAL

        from collections import Counter

        counts = Counter(recent_actions)
        dominant_action, dominant_count = counts.most_common(1)[0]
        dominance_ratio = dominant_count / len(recent_actions)

        should_activate = (
            mismatch >= (1.0 - REWARD_MISMATCH_RATIO)
            and dominance_ratio >= CONFIDENCE_THRESHOLD
            and self._stagnation_count >= STAGNATION_THRESHOLD
        )

        if not should_activate:
            return NO_TRAP_SIGNAL

        intensity = _clamp(mismatch * dominance_ratio, 0.0, 1.0)
        adjustment = _clamp(intensity * MAX_TRAP_BIAS, 0.0, MAX_TRAP_BIAS)

        return TrapSignal(
            active=True,
            dominant_action=dominant_action,
            trap_adjustment=adjustment,
            reward_mismatch=mismatch,
            stagnation_length=self._stagnation_count,
            reason=f"mismatch={mismatch:.3f},dom={dominance_ratio:.2f},"
            f"stag={self._stagnation_count}",
        )

    def snapshot(self) -> dict:
        return {
            "reward_history": list(self._reward_history),
            "action_history": list(self._action_history),
            "reward_peak": self._reward_peak,
            "stagnation_count": self._stagnation_count,
            "last_improvement_step": self._last_improvement_step,
            "step": self._step,
            "reward_ema": self._reward_ema,
        }

    def restore(self, data: dict) -> None:
        if not data or not isinstance(data, dict):
            return
        self._reward_history = list(data.get("reward_history", []))
        self._action_history = list(data.get("action_history", []))
        self._reward_peak = float(data.get("reward_peak", 0.0))
        self._stagnation_count = int(data.get("stagnation_count", 0))
        self._last_improvement_step = int(data.get("last_improvement_step", 0))
        self._step = int(data.get("step", 0))
        self._reward_ema = float(data.get("reward_ema", 0.0))

    def reset(self) -> None:
        self.__init__()


def apply_trap_adjustments(
    action_scores: dict[str, float],
    signal: TrapSignal,
) -> dict[str, float]:
    """Apply trap correction to action scores. Additive. All scores floored at 0."""
    if not signal.active or signal.dominant_action is None:
        return dict(action_scores)

    result: dict[str, float] = {}
    others = [k for k in action_scores if k != signal.dominant_action]
    boost_per = signal.trap_adjustment / max(len(others), 1)

    for name, score in action_scores.items():
        if name == signal.dominant_action:
            result[name] = score - signal.trap_adjustment
        else:
            result[name] = score + boost_per

    return result
