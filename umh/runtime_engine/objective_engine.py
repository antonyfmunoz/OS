"""
ObjectiveEngine — unified value function for system trajectory quality.

Combines five orthogonal dimensions into a single [0, 1] scalar that
answers: "how well is the system performing right now?"

Dimensions::

    GOAL_PROGRESS    — are goals being achieved?
    PLAN_EXECUTION   — are plans completing successfully?
    STABILITY        — is the system avoiding failure cascades?
    CONFIDENCE       — how certain is the system in its decisions?
    POLICY_COHERENCE — is the system maintaining consistent strategy?

Read-only: no feedback into behavior.  Deterministic.  Bounded [0, 1].
All component values logged for full interpretability.

No LLM calls.  No randomness.  Deterministic.
"""

from __future__ import annotations

from dataclasses import dataclass


WEIGHT_GOAL_PROGRESS = 0.30
WEIGHT_PLAN_EXECUTION = 0.25
WEIGHT_STABILITY = 0.20
WEIGHT_CONFIDENCE = 0.15
WEIGHT_POLICY_COHERENCE = 0.10

MAX_FAILURE_STREAK = 10
MAX_PLAN_STEPS = 50
MAX_POLICY_CHANGES = 10


def _clamp(v: float, lo: float, hi: float) -> float:
    if v < lo:
        return lo
    if v > hi:
        return hi
    return v


@dataclass(frozen=True)
class ObjectiveSnapshot:
    """Input signals collected from runtime state for objective computation."""

    goal_score: float = 0.0
    goal_delta: float = 0.0
    goal_confidence: float = 0.0

    plan_confidence: float = 0.5
    plan_steps_completed: int = 0
    plan_steps_total: int = 0

    failure_streak: int = 0
    quality_score: float = 0.0

    system_confidence: float = 0.5

    policy_changes: int = 0
    current_policy: str = ""
    previous_policy: str = ""

    def to_dict(self) -> dict:
        return {
            "goal_score": round(self.goal_score, 4),
            "goal_delta": round(self.goal_delta, 4),
            "goal_confidence": round(self.goal_confidence, 4),
            "plan_confidence": round(self.plan_confidence, 4),
            "plan_steps_completed": self.plan_steps_completed,
            "plan_steps_total": self.plan_steps_total,
            "failure_streak": self.failure_streak,
            "quality_score": round(self.quality_score, 4),
            "system_confidence": round(self.system_confidence, 4),
            "policy_changes": self.policy_changes,
            "current_policy": self.current_policy,
            "previous_policy": self.previous_policy,
        }


@dataclass(frozen=True)
class ObjectiveResult:
    """Computed objective value with full component breakdown."""

    value: float
    components: dict[str, float]
    weights: dict[str, float]
    snapshot: ObjectiveSnapshot

    def to_dict(self) -> dict:
        return {
            "value": round(self.value, 4),
            "components": {k: round(v, 4) for k, v in self.components.items()},
            "weights": {k: round(v, 4) for k, v in self.weights.items()},
            "snapshot": self.snapshot.to_dict(),
        }


NO_OBJECTIVE = ObjectiveResult(
    value=0.5,
    components={
        "goal_progress": 0.5,
        "plan_execution": 0.5,
        "stability": 1.0,
        "confidence": 0.5,
        "policy_coherence": 1.0,
    },
    weights={
        "goal_progress": WEIGHT_GOAL_PROGRESS,
        "plan_execution": WEIGHT_PLAN_EXECUTION,
        "stability": WEIGHT_STABILITY,
        "confidence": WEIGHT_CONFIDENCE,
        "policy_coherence": WEIGHT_POLICY_COHERENCE,
    },
    snapshot=ObjectiveSnapshot(),
)


def _normalize_goal_progress(snapshot: ObjectiveSnapshot) -> float:
    """Combine goal score, delta direction, and goal confidence.

    goal_score is already [0, 1].  Delta adds a directional bonus:
    positive delta (improving) nudges up, negative nudges down.
    Goal confidence weights the reliability of the signal.
    """
    base = _clamp(snapshot.goal_score, 0.0, 1.0)
    delta_bonus = _clamp(snapshot.goal_delta * 0.5, -0.2, 0.2)
    conf_weight = _clamp(snapshot.goal_confidence, 0.0, 1.0)
    raw = base + delta_bonus
    return _clamp(raw * conf_weight + raw * (1.0 - conf_weight) * 0.5, 0.0, 1.0)


def _normalize_plan_execution(snapshot: ObjectiveSnapshot) -> float:
    """Combine plan confidence with completion ratio.

    Plan confidence is already [0, 1].  Completion ratio provides
    a progress signal that rewards forward movement.
    """
    conf = _clamp(snapshot.plan_confidence, 0.0, 1.0)
    if snapshot.plan_steps_total > 0:
        completed = min(snapshot.plan_steps_completed, snapshot.plan_steps_total)
        ratio = completed / min(snapshot.plan_steps_total, MAX_PLAN_STEPS)
    else:
        ratio = 0.5
    return _clamp(conf * 0.6 + ratio * 0.4, 0.0, 1.0)


def _normalize_stability(snapshot: ObjectiveSnapshot) -> float:
    """Inverse of failure severity.  No failures = 1.0, many = near 0.

    Uses exponential decay so early failures have outsized impact
    (first failure drops from 1.0 to ~0.7).
    """
    streak = min(snapshot.failure_streak, MAX_FAILURE_STREAK)
    quality = _clamp(snapshot.quality_score, 0.0, 1.0)
    failure_penalty = 1.0 / (1.0 + streak * 0.5)
    return _clamp(failure_penalty * 0.6 + quality * 0.4, 0.0, 1.0)


def _normalize_confidence(snapshot: ObjectiveSnapshot) -> float:
    """System confidence, already [0, 1]."""
    return _clamp(snapshot.system_confidence, 0.0, 1.0)


def _normalize_policy_coherence(snapshot: ObjectiveSnapshot) -> float:
    """How stable is policy selection?

    Frequent policy changes indicate indecision.  Same policy = 1.0.
    Many changes = decays toward 0.
    """
    changes = min(snapshot.policy_changes, MAX_POLICY_CHANGES)
    coherence = 1.0 / (1.0 + changes * 0.3)
    if snapshot.current_policy == snapshot.previous_policy and snapshot.current_policy:
        coherence = min(1.0, coherence + 0.1)
    return _clamp(coherence, 0.0, 1.0)


def compute_objective(snapshot: ObjectiveSnapshot) -> ObjectiveResult:
    """Compute the unified objective value from a snapshot of runtime signals.

    All components are normalized to [0, 1] independently, then combined
    via a weighted sum.  Weights sum to 1.0.  Final value is [0, 1].

    Deterministic: same snapshot → same result.
    """
    components = {
        "goal_progress": _normalize_goal_progress(snapshot),
        "plan_execution": _normalize_plan_execution(snapshot),
        "stability": _normalize_stability(snapshot),
        "confidence": _normalize_confidence(snapshot),
        "policy_coherence": _normalize_policy_coherence(snapshot),
    }

    weights = {
        "goal_progress": WEIGHT_GOAL_PROGRESS,
        "plan_execution": WEIGHT_PLAN_EXECUTION,
        "stability": WEIGHT_STABILITY,
        "confidence": WEIGHT_CONFIDENCE,
        "policy_coherence": WEIGHT_POLICY_COHERENCE,
    }

    value = sum(components[k] * weights[k] for k in components)
    value = _clamp(value, 0.0, 1.0)

    return ObjectiveResult(
        value=value,
        components=components,
        weights=weights,
        snapshot=snapshot,
    )
