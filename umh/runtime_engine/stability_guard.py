"""
Stability guard — prevents thrashing without killing adaptation.

Detects high action switch rate combined with low reward improvement
and applies a small dampening signal: slightly reduces exploration
and increases persistence with the current action.

Deterministic. Bounded. Decays automatically.
"""

from __future__ import annotations

from dataclasses import dataclass


SWITCH_RATE_THRESHOLD = 0.6
REWARD_IMPROVEMENT_THRESHOLD = 0.01
GUARD_WINDOW = 20
EXPLORATION_DAMPEN = 0.02
CONFIDENCE_BOOST = 0.02


def _clamp(v: float, lo: float, hi: float) -> float:
    if v < lo:
        return lo
    if v > hi:
        return hi
    return v


@dataclass(frozen=True)
class StabilitySignal:
    """Immutable snapshot of stability guard state."""

    active: bool
    switch_rate: float
    reward_improvement: float
    exploration_adjustment: float
    confidence_adjustment: float
    reason: str

    def to_dict(self) -> dict:
        d: dict = {
            "active": self.active,
        }
        if self.active:
            d["switch_rate"] = round(self.switch_rate, 4)
            d["reward_improvement"] = round(self.reward_improvement, 4)
            d["exploration_adjustment"] = round(self.exploration_adjustment, 4)
            d["confidence_adjustment"] = round(self.confidence_adjustment, 4)
            d["reason"] = self.reason
        return d


NO_STABILITY_SIGNAL = StabilitySignal(
    active=False,
    switch_rate=0.0,
    reward_improvement=0.0,
    exploration_adjustment=0.0,
    confidence_adjustment=0.0,
    reason="",
)


def compute_stability_signal(
    recent_actions: list[str],
    recent_rewards: list[float],
) -> StabilitySignal:
    """Compute whether stability guard should activate.

    Checks the last GUARD_WINDOW turns for high switching + low improvement.
    """
    if len(recent_actions) < GUARD_WINDOW:
        return NO_STABILITY_SIGNAL

    window_actions = recent_actions[-GUARD_WINDOW:]
    window_rewards = recent_rewards[-GUARD_WINDOW:]

    switches = sum(
        1
        for i in range(1, len(window_actions))
        if window_actions[i] != window_actions[i - 1]
    )
    switch_rate = switches / (len(window_actions) - 1)

    half = len(window_rewards) // 2
    first_half_avg = sum(window_rewards[:half]) / max(half, 1)
    second_half_avg = sum(window_rewards[half:]) / max(len(window_rewards) - half, 1)
    improvement = second_half_avg - first_half_avg

    if switch_rate < SWITCH_RATE_THRESHOLD:
        return NO_STABILITY_SIGNAL

    if improvement > REWARD_IMPROVEMENT_THRESHOLD:
        return NO_STABILITY_SIGNAL

    intensity = _clamp(
        (switch_rate - SWITCH_RATE_THRESHOLD) / (1.0 - SWITCH_RATE_THRESHOLD), 0.0, 1.0
    )

    return StabilitySignal(
        active=True,
        switch_rate=switch_rate,
        reward_improvement=improvement,
        exploration_adjustment=-EXPLORATION_DAMPEN * intensity,
        confidence_adjustment=CONFIDENCE_BOOST * intensity,
        reason=f"switch={switch_rate:.2f},improv={improvement:.4f}",
    )
