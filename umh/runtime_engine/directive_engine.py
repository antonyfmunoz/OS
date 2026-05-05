"""
DirectiveEngine — deterministic meta-goal generation, scoring, and evolution.

Generates high-level directives from runtime signals, scores them against
outcomes and influence, selects a bounded set of active directives (max 3),
and evolves them deterministically over time.

Directive types::

    EXPLORE  — widen search, try new strategies
    EXPLOIT  — double down on what works
    RECOVER  — reduce risk after failures
    OPTIMIZE — refine current plan for efficiency

Directives produce additive effects on goal selection bias, strategy
ranking, and plan generation behavior.

No LLM calls.  No randomness.  Deterministic.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class DirectiveType(Enum):
    EXPLORE = "explore"
    EXPLOIT = "exploit"
    RECOVER = "recover"
    OPTIMIZE = "optimize"


MAX_ACTIVE_DIRECTIVES = 3
MAX_HISTORY = 20

SCORE_ALPHA = 0.20
DECAY_RATE = 0.05
MIN_CONFIDENCE = 0.05
EVOLUTION_THRESHOLD = 0.40

GOAL_BIAS: dict[DirectiveType, float] = {
    DirectiveType.EXPLORE: -0.05,
    DirectiveType.EXPLOIT: 0.05,
    DirectiveType.RECOVER: -0.03,
    DirectiveType.OPTIMIZE: 0.03,
}

STRATEGY_BIAS: dict[DirectiveType, float] = {
    DirectiveType.EXPLORE: 0.05,
    DirectiveType.EXPLOIT: -0.02,
    DirectiveType.RECOVER: 0.03,
    DirectiveType.OPTIMIZE: 0.02,
}

PLAN_BIAS: dict[DirectiveType, float] = {
    DirectiveType.EXPLORE: -0.05,
    DirectiveType.EXPLOIT: 0.05,
    DirectiveType.RECOVER: -0.08,
    DirectiveType.OPTIMIZE: 0.03,
}

MAX_GOAL_BIAS = 0.05
MAX_STRATEGY_BIAS = 0.05
MAX_PLAN_BIAS = 0.08


def _clamp(v: float, lo: float, hi: float) -> float:
    if v < lo:
        return lo
    if v > hi:
        return hi
    return v


@dataclass
class Directive:
    """A single high-level meta-goal directive."""

    directive_id: str
    directive_type: DirectiveType
    priority: float
    confidence: float
    origin: str
    turn_created: int
    score: float = 0.0

    def to_dict(self) -> dict:
        return {
            "directive_id": self.directive_id,
            "directive_type": self.directive_type.value,
            "priority": round(self.priority, 4),
            "confidence": round(self.confidence, 4),
            "origin": self.origin,
            "turn_created": self.turn_created,
            "score": round(self.score, 4),
        }


@dataclass(frozen=True)
class DirectiveEffects:
    """Computed additive effects from active directives."""

    goal_bias: float
    strategy_bias: float
    plan_bias: float

    def to_dict(self) -> dict:
        return {
            "goal_bias": round(self.goal_bias, 4),
            "strategy_bias": round(self.strategy_bias, 4),
            "plan_bias": round(self.plan_bias, 4),
        }


NO_EFFECTS = DirectiveEffects(goal_bias=0.0, strategy_bias=0.0, plan_bias=0.0)


@dataclass(frozen=True)
class DirectiveSnapshot:
    """Immutable snapshot of directive state for a single turn."""

    active: tuple[dict, ...]
    scores: dict[str, float]
    selection_reason: str
    evolution_events: tuple[str, ...]
    effects: DirectiveEffects

    def to_dict(self) -> dict:
        return {
            "active": list(self.active),
            "scores": {k: round(v, 4) for k, v in self.scores.items()},
            "selection_reason": self.selection_reason,
            "evolution_events": list(self.evolution_events),
            "effects": self.effects.to_dict(),
        }


NO_SNAPSHOT = DirectiveSnapshot(
    active=(),
    scores={},
    selection_reason="no_directives",
    evolution_events=(),
    effects=NO_EFFECTS,
)


class DirectiveState:
    """Mutable container for active directives and history."""

    def __init__(self) -> None:
        self.active: list[Directive] = []
        self.history: list[Directive] = []

    @property
    def active_count(self) -> int:
        return len(self.active)

    def to_dict(self) -> dict:
        return {
            "active": [d.to_dict() for d in self.active],
            "history_count": len(self.history),
        }


def generate_directives(
    failure_streak: int,
    exploration_rate: float,
    plan_confidence: float,
    quality_trend: float,
    current_turn: int,
) -> list[Directive]:
    """Generate candidate directives from runtime signals.

    Produces zero or more candidates based on signal thresholds.
    Deterministic: same signals → same candidates.
    """
    candidates: list[Directive] = []

    if failure_streak >= 2:
        candidates.append(
            Directive(
                directive_id=f"recover_t{current_turn}",
                directive_type=DirectiveType.RECOVER,
                priority=0.90,
                confidence=min(0.5 + failure_streak * 0.1, 1.0),
                origin=f"failure_streak={failure_streak}",
                turn_created=current_turn,
            )
        )

    if exploration_rate >= 0.50:
        candidates.append(
            Directive(
                directive_id=f"explore_t{current_turn}",
                directive_type=DirectiveType.EXPLORE,
                priority=0.70,
                confidence=min(exploration_rate, 1.0),
                origin=f"exploration_rate={exploration_rate:.2f}",
                turn_created=current_turn,
            )
        )

    if plan_confidence >= 0.70 and quality_trend >= 0.0:
        candidates.append(
            Directive(
                directive_id=f"exploit_t{current_turn}",
                directive_type=DirectiveType.EXPLOIT,
                priority=0.80,
                confidence=plan_confidence,
                origin=f"confidence={plan_confidence:.2f},trend={quality_trend:.2f}",
                turn_created=current_turn,
            )
        )

    if quality_trend > 0.0 and plan_confidence >= 0.50:
        candidates.append(
            Directive(
                directive_id=f"optimize_t{current_turn}",
                directive_type=DirectiveType.OPTIMIZE,
                priority=0.60,
                confidence=min(quality_trend + 0.3, 1.0),
                origin=f"trend={quality_trend:.2f},confidence={plan_confidence:.2f}",
                turn_created=current_turn,
            )
        )

    return candidates


def score_directives(
    directives: list[Directive],
    outcome_quality: float,
    influence_score: float,
    current_turn: int,
) -> dict[str, float]:
    """Score directives based on outcomes and influence.

    Score = EMA of (priority * confidence * outcome * influence_factor).
    Older directives decay.  Returns dict of directive_id → score.
    """
    scores: dict[str, float] = {}
    quality = _clamp(outcome_quality, 0.0, 1.0)
    influence = _clamp(influence_score, 0.0, 1.0)
    influence_factor = 0.5 + influence * 0.5

    for d in directives:
        age = max(current_turn - d.turn_created, 0)
        decay = max(1.0 - age * DECAY_RATE, 0.0)
        raw = d.priority * d.confidence * quality * influence_factor * decay
        d.score = SCORE_ALPHA * raw + (1.0 - SCORE_ALPHA) * d.score
        scores[d.directive_id] = d.score

    return scores


def select_active_directives(
    state: DirectiveState,
    candidates: list[Directive],
    scores: dict[str, float],
) -> str:
    """Select top-K directives deterministically.

    Merges candidates into state, deduplicates by type (keeps highest
    scored), selects top MAX_ACTIVE_DIRECTIVES by score (tie-break:
    alphabetical id), retires the rest to history.

    Returns selection reason string.
    """
    pool: dict[str, Directive] = {}

    for d in state.active:
        pool[d.directive_id] = d

    for d in candidates:
        existing_for_type = None
        existing_key = None
        for key, ex in pool.items():
            if ex.directive_type == d.directive_type:
                existing_for_type = ex
                existing_key = key
                break

        if existing_for_type is not None:
            ex_score = scores.get(existing_key, existing_for_type.score)
            new_score = scores.get(d.directive_id, d.priority * d.confidence)
            if new_score > ex_score:
                state.history.append(existing_for_type)
                del pool[existing_key]
                pool[d.directive_id] = d
                scores[d.directive_id] = new_score
        else:
            initial_score = d.priority * d.confidence
            d.score = initial_score
            scores[d.directive_id] = initial_score
            pool[d.directive_id] = d

    ranked = sorted(
        pool.items(),
        key=lambda item: (-scores.get(item[0], item[1].score), item[0]),
    )

    selected = ranked[:MAX_ACTIVE_DIRECTIVES]
    retired = ranked[MAX_ACTIVE_DIRECTIVES:]

    state.active = [d for _, d in selected]
    for _, d in retired:
        state.history.append(d)

    if len(state.history) > MAX_HISTORY:
        state.history = state.history[-MAX_HISTORY:]

    if not state.active:
        return "no_directives"
    if len(selected) == 1:
        return f"single:{state.active[0].directive_type.value}"
    types = ",".join(d.directive_type.value for d in state.active)
    return f"top_{len(state.active)}:{types}"


def evolve_directives(
    state: DirectiveState,
    outcome_quality: float,
    current_turn: int,
) -> list[str]:
    """Evolve active directives based on outcomes.

    - Decays confidence of directives with low scores
    - Removes directives below MIN_CONFIDENCE
    - Records evolution events

    Returns list of evolution event descriptions.
    """
    events: list[str] = []
    surviving: list[Directive] = []

    for d in state.active:
        age = max(current_turn - d.turn_created, 0)

        if d.score < EVOLUTION_THRESHOLD and age >= 2:
            d.confidence = max(d.confidence - DECAY_RATE * 2, 0.0)
            events.append(f"decay:{d.directive_id},conf={d.confidence:.2f}")

        if d.confidence < MIN_CONFIDENCE:
            state.history.append(d)
            events.append(f"expired:{d.directive_id}")
            continue

        surviving.append(d)

    state.active = surviving

    if len(state.history) > MAX_HISTORY:
        state.history = state.history[-MAX_HISTORY:]

    return events


def compute_directive_effects(
    active_directives: list[Directive],
) -> DirectiveEffects:
    """Compute additive effects from active directives.

    Each directive contributes its type's bias scaled by confidence.
    Effects are summed across all active directives and clamped.
    """
    if not active_directives:
        return NO_EFFECTS

    total_goal = 0.0
    total_strategy = 0.0
    total_plan = 0.0

    for d in active_directives:
        conf = _clamp(d.confidence, 0.0, 1.0)
        total_goal += GOAL_BIAS[d.directive_type] * conf
        total_strategy += STRATEGY_BIAS[d.directive_type] * conf
        total_plan += PLAN_BIAS[d.directive_type] * conf

    return DirectiveEffects(
        goal_bias=_clamp(total_goal, -MAX_GOAL_BIAS, MAX_GOAL_BIAS),
        strategy_bias=_clamp(total_strategy, -MAX_STRATEGY_BIAS, MAX_STRATEGY_BIAS),
        plan_bias=_clamp(total_plan, -MAX_PLAN_BIAS, MAX_PLAN_BIAS),
    )


class DirectiveEngine:
    """Stateful directive management engine.

    Orchestrates generation, scoring, selection, evolution, and
    effect computation across turns.  Singleton usage recommended.
    """

    def __init__(self) -> None:
        self.state = DirectiveState()
        self._last_snapshot: DirectiveSnapshot = NO_SNAPSHOT

    def process_turn(
        self,
        failure_streak: int = 0,
        exploration_rate: float = 0.0,
        plan_confidence: float = 0.5,
        quality_trend: float = 0.0,
        outcome_quality: float = 0.0,
        influence_score: float = 0.0,
        current_turn: int = 0,
    ) -> DirectiveSnapshot:
        """Run full directive cycle for one turn.

        1. Generate candidates from signals
        2. Score existing + candidates
        3. Evolve (decay/expire)
        4. Select top-K
        5. Compute effects

        Returns immutable DirectiveSnapshot for trace recording.
        """
        candidates = generate_directives(
            failure_streak=failure_streak,
            exploration_rate=exploration_rate,
            plan_confidence=plan_confidence,
            quality_trend=quality_trend,
            current_turn=current_turn,
        )

        all_directives = list(self.state.active) + candidates
        scores = score_directives(
            all_directives,
            outcome_quality=outcome_quality,
            influence_score=influence_score,
            current_turn=current_turn,
        )

        evolution_events = evolve_directives(
            self.state,
            outcome_quality=outcome_quality,
            current_turn=current_turn,
        )

        selection_reason = select_active_directives(
            self.state,
            candidates,
            scores,
        )

        effects = compute_directive_effects(self.state.active)

        active_dicts = tuple(d.to_dict() for d in self.state.active)
        active_scores = {
            d.directive_id: scores.get(d.directive_id, d.score)
            for d in self.state.active
        }

        snapshot = DirectiveSnapshot(
            active=active_dicts,
            scores=active_scores,
            selection_reason=selection_reason,
            evolution_events=tuple(evolution_events),
            effects=effects,
        )
        self._last_snapshot = snapshot
        return snapshot

    @property
    def last_snapshot(self) -> DirectiveSnapshot:
        return self._last_snapshot

    @property
    def active_count(self) -> int:
        return self.state.active_count

    def snapshot(self) -> dict:
        """Serialize engine state for persistence."""
        return {
            "active": [d.to_dict() for d in self.state.active],
            "history_count": len(self.state.history),
        }

    def reset(self) -> None:
        """Reset all directive state."""
        self.state = DirectiveState()
        self._last_snapshot = NO_SNAPSHOT


_engine: DirectiveEngine | None = None


def get_directive_engine() -> DirectiveEngine:
    """Singleton accessor."""
    global _engine
    if _engine is None:
        _engine = DirectiveEngine()
    return _engine
