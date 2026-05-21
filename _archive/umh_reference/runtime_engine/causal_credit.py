"""
CausalCredit — multi-horizon credit assignment across contributing layers.

Existing CausalAttribution distributes outcome credit reactively when
external feedback arrives.  This module computes per-turn, multi-horizon
credit proactively so every turn's learning signal is causally shaped.

Five contributors are scored every turn:
    step_credit   — active plan step performance
    plan_credit   — active plan confidence / completion
    strategy_credit — selected strategy conditioned score / winner status
    goal_credit   — active/blended goal weight and goal_score
    world_state_credit — conditioning_bias magnitude / state similarity

Three horizons partition each allocation:
    immediate  — what directly contributed this turn
    delayed    — what enabled this turn with short lag (1-3 turns)
    structural — what shaped the environment / search space

No LLM calls.  No randomness.  Pure arithmetic.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field

_log = logging.getLogger(__name__)

CREDIT_FLOOR = 0.01
DELAYED_HORIZON_WINDOW = 3
MAX_PENDING_CREDITS = 50
DELAYED_DECAY = 0.7
STRUCTURAL_WEIGHT = 0.15


@dataclass(frozen=True)
class CreditComponent:
    """A single contributor's credit for one turn."""

    name: str
    raw_signal: float
    normalized_weight: float
    reason: str = ""

    def to_dict(self) -> dict:
        d = {
            "name": self.name,
            "raw_signal": round(self.raw_signal, 4),
            "normalized_weight": round(self.normalized_weight, 4),
        }
        if self.reason:
            d["reason"] = self.reason
        return d


@dataclass(frozen=True)
class CreditAllocation:
    """Per-turn credit distribution across all contributors."""

    turn_id: int
    components: tuple[CreditComponent, ...]
    total_signal: float

    def weight_for(self, name: str) -> float:
        for c in self.components:
            if c.name == name:
                return c.normalized_weight
        return 0.0

    def to_dict(self) -> dict:
        return {
            "turn_id": self.turn_id,
            "total_signal": round(self.total_signal, 4),
            "components": [c.to_dict() for c in self.components],
        }


@dataclass(frozen=True)
class CreditSnapshot:
    """Full multi-horizon credit for a single turn."""

    turn_id: int
    allocation: CreditAllocation
    immediate: dict[str, float]
    delayed: dict[str, float]
    structural: dict[str, float]
    credited_entities: dict[str, str]
    credit_reason: str

    def to_dict(self) -> dict:
        d: dict = {
            "turn_id": self.turn_id,
            "allocation": self.allocation.to_dict(),
            "immediate": {k: round(v, 4) for k, v in self.immediate.items()},
        }
        if self.delayed:
            d["delayed"] = {k: round(v, 4) for k, v in self.delayed.items()}
        if self.structural:
            d["structural"] = {k: round(v, 4) for k, v in self.structural.items()}
        if self.credited_entities:
            d["credited_entities"] = self.credited_entities
        if self.credit_reason:
            d["credit_reason"] = self.credit_reason
        return d


NO_CREDIT = CreditSnapshot(
    turn_id=-1,
    allocation=CreditAllocation(turn_id=-1, components=(), total_signal=0.0),
    immediate={},
    delayed={},
    structural={},
    credited_entities={},
    credit_reason="no_data",
)


# ─── Signal extraction ──────────────────────────────────────────────────────


def _extract_step_signal(trace: object) -> tuple[float, str]:
    score = getattr(trace, "plan_step_attributed_score", None)
    if score is not None and score > 0:
        goal_id = getattr(trace, "plan_step_goal_id", "?")
        return (score, f"step:{goal_id}")
    return (0.0, "")


def _extract_plan_signal(trace: object) -> tuple[float, str]:
    plan_id = getattr(trace, "active_plan_id", None)
    if not plan_id:
        return (0.0, "")
    conf = getattr(trace, "plan_confidence", None)
    if conf is not None and conf > 0:
        return (conf, f"plan:{plan_id}")
    return (CREDIT_FLOOR, f"plan:{plan_id}")


def _extract_strategy_signal(trace: object) -> tuple[float, str]:
    selected = getattr(trace, "selected_strategy", "")
    if not selected:
        return (0.0, "")
    scores = getattr(trace, "strategy_scores", {})
    if scores:
        conditioned = getattr(trace, "strategy_conditioned_scores", None)
        if conditioned and isinstance(conditioned, dict) and selected in conditioned:
            return (max(conditioned[selected], CREDIT_FLOOR), f"strategy:{selected}")
        score = scores.get(selected, 0.0)
        return (max(score, CREDIT_FLOOR), f"strategy:{selected}")
    return (CREDIT_FLOOR, f"strategy:{selected}")


def _extract_goal_signal(trace: object) -> tuple[float, str]:
    active_id = getattr(trace, "active_goal_id", None)
    if not active_id:
        return (0.0, "")

    blended = getattr(trace, "blended_goals", None)
    if blended:
        for gid, weight in blended:
            if gid == active_id:
                goal_score = getattr(trace, "goal_score", None)
                combined = weight
                if goal_score is not None:
                    combined = (weight + goal_score) / 2.0
                return (max(combined, CREDIT_FLOOR), f"goal:{active_id}")

    goal_score = getattr(trace, "goal_score", None)
    if goal_score is not None:
        return (max(goal_score, CREDIT_FLOOR), f"goal:{active_id}")
    return (CREDIT_FLOOR, f"goal:{active_id}")


def _extract_world_state_signal(trace: object) -> tuple[float, str]:
    bias = getattr(trace, "conditioning_bias", None)
    similarity = getattr(trace, "world_state_similarity", None)
    state_id = getattr(trace, "world_state_id", None)

    if not state_id:
        return (0.0, "")

    signal = 0.0
    if similarity is not None:
        signal = similarity * 0.5
    if bias and isinstance(bias, dict):
        strat_bias = bias.get("strategy_bias", {})
        if strat_bias:
            mag = sum(abs(v) for v in strat_bias.values()) / max(len(strat_bias), 1)
            signal += mag * 0.5

    if signal < CREDIT_FLOOR and state_id:
        signal = CREDIT_FLOOR

    cluster = getattr(trace, "world_state_cluster", None)
    label = f"world:{cluster}" if cluster else f"world:{state_id}"
    return (signal, label)


# ─── Core computation ────────────────────────────────────────────────────────


def compute_credit_allocation(trace: object, turn_id: int) -> CreditAllocation:
    """Compute normalized credit allocation across 5 contributors."""
    extractors = [
        ("step", _extract_step_signal),
        ("plan", _extract_plan_signal),
        ("strategy", _extract_strategy_signal),
        ("goal", _extract_goal_signal),
        ("world_state", _extract_world_state_signal),
    ]

    components: list[CreditComponent] = []
    total = 0.0

    for name, extractor in extractors:
        signal, entity = extractor(trace)
        if signal > 0:
            components.append(
                CreditComponent(
                    name=name, raw_signal=signal, normalized_weight=0.0, reason=entity
                )
            )
            total += signal

    if total < 1e-9:
        return CreditAllocation(turn_id=turn_id, components=(), total_signal=0.0)

    normalized = tuple(
        CreditComponent(
            name=c.name,
            raw_signal=c.raw_signal,
            normalized_weight=c.raw_signal / total,
            reason=c.reason,
        )
        for c in components
    )

    return CreditAllocation(turn_id=turn_id, components=normalized, total_signal=total)


def compute_credit_horizons(
    allocation: CreditAllocation,
    recent_traces: list[object],
    turn_id: int,
) -> tuple[dict[str, float], dict[str, float], dict[str, float]]:
    """Split allocation into immediate / delayed / structural horizons.

    Immediate: direct contributors this turn.
    Delayed: enabling contributions from recent turns (looked up from traces).
    Structural: environment-shaping contributions (world_state, goal arbitration).
    """
    immediate: dict[str, float] = {}
    delayed: dict[str, float] = {}
    structural: dict[str, float] = {}

    structural_names = {"world_state"}
    delayed_candidates = {"step", "plan", "goal"}

    for comp in allocation.components:
        if comp.name in structural_names:
            structural[comp.name] = comp.normalized_weight * STRUCTURAL_WEIGHT
            immediate[comp.name] = comp.normalized_weight * (1.0 - STRUCTURAL_WEIGHT)
        else:
            immediate[comp.name] = comp.normalized_weight

    # Delayed credit: look at prior turns for enabling signals
    if recent_traces:
        window = recent_traces[-DELAYED_HORIZON_WINDOW:]
        for i, prior_trace in enumerate(window):
            age = len(window) - i
            decay = DELAYED_DECAY**age

            prior_step_score = getattr(prior_trace, "plan_step_attributed_score", None)
            if prior_step_score is not None and prior_step_score > 0.5:
                prior_goal = getattr(prior_trace, "plan_step_goal_id", None)
                if prior_goal:
                    key = f"step:{prior_goal}"
                    delayed[key] = (
                        delayed.get(key, 0.0) + prior_step_score * decay * 0.1
                    )

            prior_plan_conf = getattr(prior_trace, "plan_confidence", None)
            if prior_plan_conf is not None and prior_plan_conf > 0.5:
                prior_plan_id = getattr(prior_trace, "active_plan_id", None)
                if prior_plan_id:
                    key = f"plan:{prior_plan_id}"
                    delayed[key] = (
                        delayed.get(key, 0.0) + prior_plan_conf * decay * 0.05
                    )

    # Normalize delayed if populated
    if delayed:
        d_total = sum(delayed.values())
        if d_total > 0:
            delayed = {k: v / d_total for k, v in delayed.items()}

    return immediate, delayed, structural


def compute_credit_snapshot(
    trace: object,
    turn_id: int,
    recent_traces: list[object] | None = None,
) -> CreditSnapshot:
    """Compute full multi-horizon credit snapshot for a turn."""
    allocation = compute_credit_allocation(trace, turn_id)

    if not allocation.components:
        return CreditSnapshot(
            turn_id=turn_id,
            allocation=allocation,
            immediate={},
            delayed={},
            structural={},
            credited_entities={},
            credit_reason="no_active_contributors",
        )

    immediate, delayed, structural = compute_credit_horizons(
        allocation, recent_traces or [], turn_id
    )

    entities: dict[str, str] = {}
    for comp in allocation.components:
        if comp.reason:
            entities[comp.name] = comp.reason

    dominant = max(allocation.components, key=lambda c: c.normalized_weight)
    reason = (
        f"{dominant.name}_dominant" if dominant.normalized_weight > 0.4 else "balanced"
    )

    return CreditSnapshot(
        turn_id=turn_id,
        allocation=allocation,
        immediate=immediate,
        delayed=delayed,
        structural=structural,
        credited_entities=entities,
        credit_reason=reason,
    )


# ─── Delayed credit buffer ──────────────────────────────────────────────────


@dataclass
class PendingCredit:
    """A credit entry awaiting future-turn confirmation."""

    source_turn: int
    contributor: str
    credit_weight: float
    entity: str
    expiry_turn: int

    def to_dict(self) -> dict:
        return {
            "source_turn": self.source_turn,
            "contributor": self.contributor,
            "credit_weight": round(self.credit_weight, 4),
            "entity": self.entity,
            "expiry_turn": self.expiry_turn,
        }


class DelayedCreditBuffer:
    """Bounded session-scoped buffer for short-horizon delayed credit.

    Tracks enabling contributions that may be confirmed by future turns.
    Deterministic expiration after DELAYED_HORIZON_WINDOW turns.
    """

    def __init__(self) -> None:
        self._pending: list[PendingCredit] = []

    def add(
        self,
        source_turn: int,
        contributor: str,
        credit_weight: float,
        entity: str,
    ) -> None:
        if credit_weight < CREDIT_FLOOR:
            return
        entry = PendingCredit(
            source_turn=source_turn,
            contributor=contributor,
            credit_weight=credit_weight,
            entity=entity,
            expiry_turn=source_turn + DELAYED_HORIZON_WINDOW,
        )
        self._pending.append(entry)
        if len(self._pending) > MAX_PENDING_CREDITS:
            self._pending.pop(0)

    def resolve(self, current_turn: int, outcome_score: float) -> list[PendingCredit]:
        """Resolve pending credits that haven't expired.

        Returns resolved entries and removes them from the buffer.
        Expired entries are dropped silently.
        """
        resolved: list[PendingCredit] = []
        remaining: list[PendingCredit] = []

        for entry in self._pending:
            if current_turn > entry.expiry_turn:
                continue
            if outcome_score > 0.3:
                resolved.append(entry)
            else:
                remaining.append(entry)

        self._pending = remaining
        return resolved

    def expire(self, current_turn: int) -> int:
        """Remove expired entries. Returns count of expired entries."""
        before = len(self._pending)
        self._pending = [e for e in self._pending if current_turn <= e.expiry_turn]
        return before - len(self._pending)

    @property
    def pending_count(self) -> int:
        return len(self._pending)

    def to_dict(self) -> dict:
        return {
            "pending_count": self.pending_count,
            "entries": [e.to_dict() for e in self._pending],
        }


# ─── Weighted memory application ────────────────────────────────────────────


def apply_weighted_credit_to_strategy(
    strategy_name: str,
    quality_score: float,
    strategy_credit: float,
) -> None:
    """Scale strategy learning by causal credit weight.

    Uses apply_outcome pattern: adjusts EMA proportional to credit.
    Does NOT increment uses/wins — this is a credit adjustment, not
    a new observation.
    """
    if strategy_credit < CREDIT_FLOOR or not strategy_name:
        return
    try:
        from umh.strategy.memory import get_strategy_memory

        mem = get_strategy_memory()
        mem.apply_outcome(strategy_name, quality_score, strategy_credit)
    except Exception as e:
        _log.debug("Strategy credit application failed: %s", e)


def apply_weighted_credit_to_goal(
    goal_id: str,
    goal_score: float,
    goal_credit: float,
    goal_registry: object | None = None,
) -> None:
    """Scale goal learning by causal credit weight."""
    if goal_credit < CREDIT_FLOOR or not goal_id or goal_registry is None:
        return
    try:
        tracker = goal_registry.get_tracker(goal_id)
        if tracker is not None:
            tracker.apply_outcome(goal_score, goal_credit)
    except Exception as e:
        _log.debug("Goal credit application failed: %s", e)


def apply_weighted_credit_to_plan(
    plan_id: str,
    step_goal_id: str,
    step_credit: float,
    plan_credit: float,
) -> None:
    """Scale plan confidence update by causal credit weight.

    Adjusts the plan progress confidence proportionally rather than
    creating extra step observations.
    """
    if (step_credit < CREDIT_FLOOR and plan_credit < CREDIT_FLOOR) or not plan_id:
        return
    try:
        from umh.runtime_engine.hierarchical_planning import get_plan_engine

        pe = get_plan_engine()
        progress = pe.get_progress(plan_id)
        if progress is not None:
            combined_credit = (step_credit + plan_credit) / 2.0
            nudge = combined_credit * 0.05
            progress.confidence = min(1.0, progress.confidence + nudge)
    except Exception as e:
        _log.debug("Plan credit application failed: %s", e)


# ─── Singleton ───────────────────────────────────────────────────────────────

_buffer_instance: DelayedCreditBuffer | None = None


def get_delayed_credit_buffer() -> DelayedCreditBuffer:
    global _buffer_instance
    if _buffer_instance is None:
        _buffer_instance = DelayedCreditBuffer()
    return _buffer_instance


def reset_delayed_credit_buffer() -> None:
    global _buffer_instance
    _buffer_instance = None
