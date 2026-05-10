"""PolicyState — behavioral memory layer for decision discipline.

Tracks how the system's behavior evolves over time, not per decision.
Detects oscillation, mode flipping, over-exploration, and override abuse.
Produces dampening signals that meta-control consumes to enforce consistency.

Stateful across turns. Deterministic. Bounded memory. No ML. No randomness.
"""

from __future__ import annotations

from dataclasses import dataclass


# ─── Constants ──────────────────────────────────────────────────

MAX_HISTORY = 20
EMA_ALPHA = 0.15
OSCILLATION_THRESHOLD = 0.5
CONSISTENCY_THRESHOLD = 0.4
OVERRIDE_RATE_THRESHOLD = 0.6
EXPLORATION_RATE_THRESHOLD = 0.7
MODE_FLIP_THRESHOLD = 0.5
RECOVERY_STEPS = 5
DAMPENING_FACTOR = 0.3


# ─── Data models ───────────────────────────────────────────────


@dataclass(frozen=True)
class PolicySignals:
    """Behavioral flags for the current turn."""

    is_oscillating: bool
    is_over_exploring: bool
    is_overriding_too_much: bool
    is_mode_flipping: bool
    is_stable: bool

    def to_dict(self) -> dict:
        return {
            "is_oscillating": self.is_oscillating,
            "is_over_exploring": self.is_over_exploring,
            "is_overriding_too_much": self.is_overriding_too_much,
            "is_mode_flipping": self.is_mode_flipping,
            "is_stable": self.is_stable,
        }

    def any_flag_active(self) -> bool:
        return (
            self.is_oscillating
            or self.is_over_exploring
            or self.is_overriding_too_much
            or self.is_mode_flipping
        )


STABLE_SIGNALS = PolicySignals(
    is_oscillating=False,
    is_over_exploring=False,
    is_overriding_too_much=False,
    is_mode_flipping=False,
    is_stable=True,
)


@dataclass(frozen=True)
class DampeningResult:
    """Adjustments to apply when behavioral instability is detected."""

    planner_confidence_scale: float
    exploration_boost_scale: float
    stability_weight_bonus: float
    mode_override: str | None

    def to_dict(self) -> dict:
        d: dict = {
            "planner_confidence_scale": round(self.planner_confidence_scale, 6),
            "exploration_boost_scale": round(self.exploration_boost_scale, 6),
            "stability_weight_bonus": round(self.stability_weight_bonus, 6),
        }
        if self.mode_override is not None:
            d["mode_override"] = self.mode_override
        return d


NO_DAMPENING = DampeningResult(
    planner_confidence_scale=1.0,
    exploration_boost_scale=1.0,
    stability_weight_bonus=0.0,
    mode_override=None,
)


# ─── Oscillation detection ───────────────────────────────────


def compute_oscillation_score(actions: list[str]) -> float:
    """Detect rapid switching between actions.

    Counts direction changes in the action sequence.
    A-B-A-B = high oscillation. A-A-A-B = low.
    Returns 0.0 (no oscillation) to 1.0 (maximum oscillation).
    """
    if len(actions) < 3:
        return 0.0

    changes = 0
    for i in range(2, len(actions)):
        if actions[i] != actions[i - 1] and actions[i] == actions[i - 2]:
            changes += 1

    max_possible = len(actions) - 2
    return changes / max_possible if max_possible > 0 else 0.0


def compute_mode_flip_rate(modes: list[str]) -> float:
    """Detect mode flipping (adaptive ↔ full, etc).

    Returns fraction of transitions that are mode changes.
    """
    if len(modes) < 2:
        return 0.0

    flips = sum(1 for i in range(1, len(modes)) if modes[i] != modes[i - 1])
    return flips / (len(modes) - 1)


# ─── Consistency metric ──────────────────────────────────────


def compute_consistency_score(
    context_action_pairs: list[tuple[str, str]],
) -> float:
    """Measure how often similar contexts produce the same action.

    Groups by context, checks if same context → same action.
    Returns 1.0 (perfectly consistent) to 0.0 (chaotic).
    """
    if len(context_action_pairs) < 2:
        return 1.0

    context_groups: dict[str, list[str]] = {}
    for ctx, action in context_action_pairs:
        context_groups.setdefault(ctx, []).append(action)

    if not context_groups:
        return 1.0

    consistency_scores: list[float] = []
    for actions in context_groups.values():
        if len(actions) < 2:
            continue
        most_common = max(set(actions), key=actions.count)
        agreement = actions.count(most_common) / len(actions)
        consistency_scores.append(agreement)

    if not consistency_scores:
        return 1.0

    return sum(consistency_scores) / len(consistency_scores)


# ─── Dampening computation ───────────────────────────────────


def compute_dampening(
    signals: PolicySignals,
    oscillation_score: float,
    consistency_score: float,
) -> DampeningResult:
    """Compute dampening adjustments based on behavioral signals.

    When instability is detected, reduces confidence in aggressive layers
    and increases stability weighting.
    """
    if not signals.any_flag_active():
        return NO_DAMPENING

    planner_scale = 1.0
    exploration_scale = 1.0
    stability_bonus = 0.0
    mode_override: str | None = None

    if signals.is_oscillating:
        planner_scale *= 1.0 - (DAMPENING_FACTOR * oscillation_score)
        stability_bonus += 0.1 * oscillation_score

    if signals.is_over_exploring:
        exploration_scale *= 1.0 - DAMPENING_FACTOR

    if signals.is_overriding_too_much:
        planner_scale *= 1.0 - DAMPENING_FACTOR

    if signals.is_mode_flipping:
        mode_override = "adaptive"
        stability_bonus += 0.1

    planner_scale = max(0.3, min(1.0, planner_scale))
    exploration_scale = max(0.3, min(1.0, exploration_scale))
    stability_bonus = min(0.3, stability_bonus)

    return DampeningResult(
        planner_confidence_scale=planner_scale,
        exploration_boost_scale=exploration_scale,
        stability_weight_bonus=stability_bonus,
        mode_override=mode_override,
    )


# ─── Policy state tracker ───────────────────────────────────


class PolicyStateTracker:
    """Bounded behavioral memory across turns.

    Tracks recent actions, modes, overrides, and exploration usage.
    Produces oscillation/consistency scores and behavioral signals.
    Implements recovery logic: stable for K steps → restore permissions.
    """

    def __init__(self, max_history: int = MAX_HISTORY) -> None:
        self._max_history = max_history
        self._recent_actions: list[str] = []
        self._mode_history: list[str] = []
        self._context_action_pairs: list[tuple[str, str]] = []
        self._override_history: list[bool] = []
        self._exploration_history: list[bool] = []
        self._stability_ema: float = 1.0
        self._steps_stable: int = 0
        self._step: int = 0

    @property
    def step(self) -> int:
        return self._step

    @property
    def stability_score(self) -> float:
        return self._stability_ema

    @property
    def steps_stable(self) -> int:
        return self._steps_stable

    def record_turn(
        self,
        action_id: str | None = None,
        mode: str | None = None,
        context_type: str | None = None,
        planner_override_used: bool = False,
        exploration_used: bool = False,
    ) -> None:
        """Record behavioral data from this turn."""
        self._step += 1

        if action_id is not None:
            self._recent_actions.append(action_id)
            if len(self._recent_actions) > self._max_history:
                self._recent_actions.pop(0)

        if mode is not None:
            self._mode_history.append(mode)
            if len(self._mode_history) > self._max_history:
                self._mode_history.pop(0)

        if context_type is not None and action_id is not None:
            self._context_action_pairs.append((context_type, action_id))
            if len(self._context_action_pairs) > self._max_history:
                self._context_action_pairs.pop(0)

        self._override_history.append(planner_override_used)
        if len(self._override_history) > self._max_history:
            self._override_history.pop(0)

        self._exploration_history.append(exploration_used)
        if len(self._exploration_history) > self._max_history:
            self._exploration_history.pop(0)

        osc = self.oscillation_score
        cons = self.consistency_score
        flip = self.mode_flip_rate
        current_stability = (1.0 - osc) * cons * (1.0 - flip)
        self._stability_ema = (
            1.0 - EMA_ALPHA
        ) * self._stability_ema + EMA_ALPHA * current_stability

        if self._stability_ema > 0.7:
            self._steps_stable += 1
        else:
            self._steps_stable = 0

    @property
    def oscillation_score(self) -> float:
        return compute_oscillation_score(self._recent_actions)

    @property
    def consistency_score(self) -> float:
        return compute_consistency_score(self._context_action_pairs)

    @property
    def override_rate(self) -> float:
        if not self._override_history:
            return 0.0
        return sum(1 for o in self._override_history if o) / len(self._override_history)

    @property
    def exploration_rate(self) -> float:
        if not self._exploration_history:
            return 0.0
        return sum(1 for e in self._exploration_history if e) / len(
            self._exploration_history
        )

    @property
    def mode_flip_rate(self) -> float:
        return compute_mode_flip_rate(self._mode_history)

    def compute_signals(self) -> PolicySignals:
        """Produce behavioral flags from current state."""
        osc = self.oscillation_score
        flip = self.mode_flip_rate
        over = self.override_rate
        expl = self.exploration_rate

        is_oscillating = osc > OSCILLATION_THRESHOLD
        is_mode_flipping = flip > MODE_FLIP_THRESHOLD
        is_overriding = over > OVERRIDE_RATE_THRESHOLD
        is_over_exploring = expl > EXPLORATION_RATE_THRESHOLD
        is_stable = not (
            is_oscillating or is_mode_flipping or is_overriding or is_over_exploring
        )

        return PolicySignals(
            is_oscillating=is_oscillating,
            is_over_exploring=is_over_exploring,
            is_overriding_too_much=is_overriding,
            is_mode_flipping=is_mode_flipping,
            is_stable=is_stable,
        )

    def compute_dampening(self) -> DampeningResult:
        """Compute dampening adjustments from current behavioral state."""
        signals = self.compute_signals()
        return compute_dampening(
            signals, self.oscillation_score, self.consistency_score
        )

    def is_recovered(self) -> bool:
        """True if system has been stable for RECOVERY_STEPS consecutive turns."""
        return self._steps_stable >= RECOVERY_STEPS

    def get_trace_fields(self) -> dict:
        """Return trace-level observability fields."""
        signals = self.compute_signals()
        return {
            "policy_oscillation_score": round(self.oscillation_score, 6),
            "policy_consistency_score": round(self.consistency_score, 6),
            "policy_stability_ema": round(self._stability_ema, 6),
            "policy_flags": signals.to_dict(),
        }

    def reset(self) -> None:
        """Clear all state."""
        self._recent_actions.clear()
        self._mode_history.clear()
        self._context_action_pairs.clear()
        self._override_history.clear()
        self._exploration_history.clear()
        self._stability_ema = 1.0
        self._steps_stable = 0
        self._step = 0


# ─── Meta-control integration ───────────────────────────────


def apply_policy_to_meta_control(
    base_mode: str,
    policy_tracker: PolicyStateTracker,
) -> str:
    """Adjust meta-control mode based on behavioral state.

    If oscillation or mode flipping is detected, downgrade.
    If recovered, allow base mode through.
    """
    signals = policy_tracker.compute_signals()
    dampening = policy_tracker.compute_dampening()

    if dampening.mode_override is not None and not policy_tracker.is_recovered():
        if base_mode == "full" and signals.is_mode_flipping:
            return "adaptive"
        if dampening.mode_override == "adaptive" and base_mode == "full":
            return "adaptive"

    if signals.is_oscillating and base_mode == "full":
        return "adaptive"

    return base_mode


# ─── Module-level singleton ─────────────────────────────────

_global_policy_tracker: PolicyStateTracker | None = None


def get_policy_tracker() -> PolicyStateTracker:
    global _global_policy_tracker
    if _global_policy_tracker is None:
        _global_policy_tracker = PolicyStateTracker()
    return _global_policy_tracker


def reset_policy_tracker() -> None:
    global _global_policy_tracker
    _global_policy_tracker = None
