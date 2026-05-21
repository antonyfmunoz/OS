"""
Action Space Shaping — structured, bounded strategy synthesis at the planner level.

When the current action space is exhausted (all candidates are risky, confidence
is low, or performance has plateaued), this module generates new candidate actions
via three mechanisms:

1. Mutation: slight variation of top-performing actions (parameter shift)
2. Combination: weighted blend of two existing strategies
3. Exploration seed: inject a novel, low-confidence candidate

Generated candidates are bounded (K_new ≤ 2), deterministic, and receive no
special treatment — they compete through the same planner + risk model pipeline.

NOT random exploration. Structured, bounded, testable strategy synthesis.

Deterministic. Bounded. No LLM calls. No state mutation. No randomness.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


# ─── Constants ────────────────────────────────────────────────────

MAX_NEW_CANDIDATES = 2
MIN_BASE_CANDIDATES = 2

CONFIDENCE_LOW_THRESHOLD = 0.4
RISK_HIGH_THRESHOLD = 0.5
PLATEAU_WINDOW = 8
PLATEAU_VARIANCE_THRESHOLD = 0.02**2
REGIME_STRENGTH_THRESHOLD = 0.3

MUTATION_SCALE = 0.15
COMBINATION_ALPHA_DEFAULT = 0.5
SEED_SCORE_FLOOR = 0.01

MIN_OBSERVATIONS_FOR_SYNTHESIS = 5
SYNTHESIS_COOLDOWN = 5

UNCERTAINTY_GATE = 0.85
CONTEXT_STABILITY_REQUIRED = "stable"


# ─── Helpers ──────────────────────────────────────────────────────


def _clamp(v: float, lo: float, hi: float) -> float:
    if v < lo:
        return lo
    if v > hi:
        return hi
    return v


# ─── Data structures ─────────────────────────────────────────────


@dataclass(frozen=True)
class SynthesizedAction:
    """A newly generated candidate action."""

    action: str
    strategy_type: str  # "mutation" | "combination" | "seed"
    strategy_origin: tuple[str, ...]
    estimated_score: float
    synthesis_reason: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "action": self.action,
            "strategy_type": self.strategy_type,
            "strategy_origin": list(self.strategy_origin),
            "estimated_score": round(self.estimated_score, 6),
            "synthesis_reason": self.synthesis_reason,
        }


@dataclass(frozen=True)
class SynthesisResult:
    """Output of action space shaping."""

    active: bool
    new_actions: tuple[SynthesizedAction, ...]
    trigger_reason: str
    synthesis_attempted: int
    synthesis_produced: int

    def to_dict(self) -> dict[str, Any]:
        return {
            "active": self.active,
            "new_actions": [a.to_dict() for a in self.new_actions],
            "trigger_reason": self.trigger_reason,
            "synthesis_attempted": self.synthesis_attempted,
            "synthesis_produced": self.synthesis_produced,
        }


@dataclass(frozen=True)
class SynthesisTraceFields:
    """Trace fields for decision trace integration."""

    strategy_generated: bool
    strategy_type: str  # "mutation" | "combination" | "seed" | "none"
    strategy_origin: tuple[str, ...]
    strategy_selected: bool

    def to_dict(self) -> dict[str, Any]:
        return {
            "strategy_generated": self.strategy_generated,
            "strategy_type": self.strategy_type,
            "strategy_origin": list(self.strategy_origin),
            "strategy_selected": self.strategy_selected,
        }


NO_SYNTHESIS = SynthesisResult(
    active=False,
    new_actions=(),
    trigger_reason="",
    synthesis_attempted=0,
    synthesis_produced=0,
)

NO_TRACE = SynthesisTraceFields(
    strategy_generated=False,
    strategy_type="none",
    strategy_origin=(),
    strategy_selected=False,
)


# ─── Trigger detection ───────────────────────────────────────────


def _detect_low_confidence(
    planner_confidence: float,
) -> bool:
    """Planner confidence below threshold."""
    return planner_confidence < CONFIDENCE_LOW_THRESHOLD


def _detect_high_risk_across_all(
    risk_scores: dict[str, float],
) -> bool:
    """All candidate actions have high risk scores."""
    if not risk_scores:
        return False
    return all(s > RISK_HIGH_THRESHOLD for s in risk_scores.values())


def _detect_plateau(
    reward_history: list[float],
) -> bool:
    """No improvement over recent window — flat performance."""
    if len(reward_history) < PLATEAU_WINDOW:
        return False

    recent = reward_history[-PLATEAU_WINDOW:]
    mean = sum(recent) / len(recent)
    variance = sum((r - mean) ** 2 for r in recent) / len(recent)

    return variance < PLATEAU_VARIANCE_THRESHOLD


def _detect_regime_stagnation(
    regime_active: bool,
    regime_strength: float,
) -> bool:
    """Regime engine signals stagnation."""
    return regime_active and regime_strength >= REGIME_STRENGTH_THRESHOLD


def check_synthesis_triggers(
    planner_confidence: float = 1.0,
    risk_scores: dict[str, float] | None = None,
    reward_history: list[float] | None = None,
    regime_active: bool = False,
    regime_strength: float = 0.0,
) -> tuple[bool, str]:
    """Check whether synthesis should activate.

    Returns (should_activate, reason).
    At least one trigger must fire.
    """
    triggers: list[str] = []

    if _detect_low_confidence(planner_confidence):
        triggers.append("low_confidence")

    if risk_scores and _detect_high_risk_across_all(risk_scores):
        triggers.append("all_high_risk")

    if reward_history and _detect_plateau(reward_history):
        triggers.append("performance_plateau")

    if _detect_regime_stagnation(regime_active, regime_strength):
        triggers.append("regime_stagnation")

    if not triggers:
        return False, ""

    return True, "+".join(triggers)


# ─── Safety gating ───────────────────────────────────────────────


def check_safety_gate(
    context_type: str | None,
    uncertainty: float,
    last_synthesis_step: int,
    current_step: int,
) -> str | None:
    """Return a reason string if synthesis should be blocked, else None.

    Blocks when:
    - Context is unstable
    - Uncertainty is too high (system doesn't understand current state)
    - Cooldown hasn't elapsed
    """
    if context_type != CONTEXT_STABILITY_REQUIRED:
        return f"context_not_stable:{context_type}"

    if uncertainty >= UNCERTAINTY_GATE:
        return f"uncertainty_too_high:{uncertainty:.3f}"

    if current_step - last_synthesis_step < SYNTHESIS_COOLDOWN:
        return f"cooldown:{current_step - last_synthesis_step}<{SYNTHESIS_COOLDOWN}"

    return None


# ─── Strategy generation: mutation ───────────────────────────────


def _mutate_action(
    base_action: str,
    base_score: float,
    all_scores: dict[str, float],
) -> SynthesizedAction | None:
    """Create a mutated variant of the top action.

    Mutation shifts the score estimate slightly down (conservative mutation)
    and creates a named variant. The actual behavior difference comes from
    the causal memory's response to the new action name — the system learns
    different outcome patterns for the mutated variant.
    """
    if base_score <= 0:
        return None

    score_range = (
        max(all_scores.values()) - min(all_scores.values())
        if len(all_scores) >= 2
        else base_score
    )
    shift = score_range * MUTATION_SCALE

    mutated_score = base_score - shift

    mut_name = f"mut_{base_action}"
    if mut_name in all_scores:
        return None

    return SynthesizedAction(
        action=mut_name,
        strategy_type="mutation",
        strategy_origin=(base_action,),
        estimated_score=max(mutated_score, SEED_SCORE_FLOOR),
        synthesis_reason=f"mutation_of_{base_action}",
    )


# ─── Strategy generation: combination ────────────────────────────


def _combine_actions(
    action_a: str,
    score_a: float,
    action_b: str,
    score_b: float,
    all_scores: dict[str, float],
) -> SynthesizedAction | None:
    """Blend two existing strategies via weighted interpolation.

    The combined score is the weighted average, biased toward the
    stronger action. The name encodes both parents for traceability.
    """
    if score_a <= 0 and score_b <= 0:
        return None

    total = abs(score_a) + abs(score_b)
    if total < 1e-9:
        alpha = COMBINATION_ALPHA_DEFAULT
    else:
        alpha = abs(score_a) / total

    combined_score = alpha * score_a + (1.0 - alpha) * score_b

    parts = sorted([action_a, action_b])
    combo_name = f"combo_{parts[0]}_{parts[1]}"
    if combo_name in all_scores:
        return None

    return SynthesizedAction(
        action=combo_name,
        strategy_type="combination",
        strategy_origin=(action_a, action_b),
        estimated_score=max(combined_score, SEED_SCORE_FLOOR),
        synthesis_reason=f"blend_{action_a}+{action_b}",
    )


# ─── Strategy generation: exploration seed ───────────────────────


def _seed_novel_action(
    existing_actions: list[str],
    all_scores: dict[str, float],
    causal_stats: dict | None,
) -> SynthesizedAction | None:
    """Inject a novel candidate that hasn't been tried.

    Scans causal memory for actions that have been observed but aren't
    in the current candidate set. If none found, generates a deterministic
    seed name based on the existing action count.
    """
    novel_candidates: list[str] = []

    if causal_stats and isinstance(causal_stats, dict):
        for key in sorted(causal_stats.keys()):
            if "|" in key:
                _, action = key.split("|", 1)
                if action not in existing_actions and action not in all_scores:
                    novel_candidates.append(action)

    if novel_candidates:
        seed_action = novel_candidates[0]
        stat = causal_stats.get(f"stable|{seed_action}") or {}
        seed_score = float(stat.get("ema_reward_delta", SEED_SCORE_FLOOR))
        seed_score = max(seed_score, SEED_SCORE_FLOOR)
    else:
        seed_idx = len(existing_actions)
        seed_action = f"seed_{seed_idx}"
        if seed_action in all_scores:
            return None
        seed_score = SEED_SCORE_FLOOR

    return SynthesizedAction(
        action=seed_action,
        strategy_type="seed",
        strategy_origin=(),
        estimated_score=seed_score,
        synthesis_reason="novel_exploration_seed",
    )


# ─── Core synthesis ──────────────────────────────────────────────


def synthesize_actions(
    candidate_actions: list[str],
    strategy_scores: dict[str, float],
    planner_confidence: float = 1.0,
    risk_scores: dict[str, float] | None = None,
    reward_history: list[float] | None = None,
    regime_active: bool = False,
    regime_strength: float = 0.0,
    context_type: str | None = "stable",
    uncertainty: float = 0.0,
    causal_stats: dict | None = None,
    last_synthesis_step: int = -SYNTHESIS_COOLDOWN,
    current_step: int = 0,
) -> SynthesisResult:
    """Generate new candidate actions when current space is insufficient.

    Checks triggers, applies safety gates, then generates up to
    MAX_NEW_CANDIDATES new actions via mutation, combination, and seeding.
    """
    should_activate, trigger_reason = check_synthesis_triggers(
        planner_confidence=planner_confidence,
        risk_scores=risk_scores,
        reward_history=reward_history,
        regime_active=regime_active,
        regime_strength=regime_strength,
    )

    if not should_activate:
        return NO_SYNTHESIS

    gate_reason = check_safety_gate(
        context_type=context_type,
        uncertainty=uncertainty,
        last_synthesis_step=last_synthesis_step,
        current_step=current_step,
    )
    if gate_reason is not None:
        return SynthesisResult(
            active=False,
            new_actions=(),
            trigger_reason=f"gated:{gate_reason}",
            synthesis_attempted=0,
            synthesis_produced=0,
        )

    if len(candidate_actions) < MIN_BASE_CANDIDATES:
        return SynthesisResult(
            active=False,
            new_actions=(),
            trigger_reason="insufficient_base_candidates",
            synthesis_attempted=0,
            synthesis_produced=0,
        )

    sorted_actions = sorted(
        candidate_actions,
        key=lambda a: strategy_scores.get(a, 0.0),
        reverse=True,
    )

    new_actions: list[SynthesizedAction] = []
    attempted = 0

    # 1. Mutation of top action
    if len(new_actions) < MAX_NEW_CANDIDATES:
        top = sorted_actions[0]
        top_score = strategy_scores.get(top, 0.0)
        attempted += 1
        mutated = _mutate_action(top, top_score, strategy_scores)
        if mutated is not None:
            new_actions.append(mutated)

    # 2. Combination of top two actions
    if len(new_actions) < MAX_NEW_CANDIDATES and len(sorted_actions) >= 2:
        a, b = sorted_actions[0], sorted_actions[1]
        sa, sb = strategy_scores.get(a, 0.0), strategy_scores.get(b, 0.0)
        attempted += 1
        combined = _combine_actions(a, sa, b, sb, strategy_scores)
        if combined is not None:
            new_actions.append(combined)

    # 3. Exploration seed (only if we still have room)
    if len(new_actions) < MAX_NEW_CANDIDATES:
        attempted += 1
        seed = _seed_novel_action(candidate_actions, strategy_scores, causal_stats)
        if seed is not None:
            new_actions.append(seed)

    # Enforce bound
    new_actions = new_actions[:MAX_NEW_CANDIDATES]

    if not new_actions:
        return SynthesisResult(
            active=False,
            new_actions=(),
            trigger_reason=trigger_reason,
            synthesis_attempted=attempted,
            synthesis_produced=0,
        )

    return SynthesisResult(
        active=True,
        new_actions=tuple(new_actions),
        trigger_reason=trigger_reason,
        synthesis_attempted=attempted,
        synthesis_produced=len(new_actions),
    )


# ─── Planner integration ─────────────────────────────────────────


def expand_candidate_set(
    candidate_actions: list[str],
    strategy_scores: dict[str, float],
    synthesis_result: SynthesisResult,
) -> tuple[list[str], dict[str, float]]:
    """Expand the candidate set with synthesized actions.

    Returns new (actions, scores) with synthesized candidates appended.
    New candidates get their estimated scores injected into the score map.

    Returns copies — never mutates inputs.
    """
    if not synthesis_result.active or not synthesis_result.new_actions:
        return list(candidate_actions), dict(strategy_scores)

    expanded_actions = list(candidate_actions)
    expanded_scores = dict(strategy_scores)

    for synth in synthesis_result.new_actions:
        if synth.action not in expanded_scores:
            expanded_actions.append(synth.action)
            expanded_scores[synth.action] = synth.estimated_score

    return expanded_actions, expanded_scores


# ─── Memory integration ──────────────────────────────────────────


@dataclass
class SynthesisMemory:
    """Tracks success/failure of generated strategies across turns.

    Feeds into causal memory indirectly: synthesized actions that
    succeed will accumulate positive causal stats naturally. This
    memory tracks synthesis-specific metadata for tuning generation.
    """

    generated_count: int = 0
    selected_count: int = 0
    mutation_successes: int = 0
    mutation_attempts: int = 0
    combination_successes: int = 0
    combination_attempts: int = 0
    seed_successes: int = 0
    seed_attempts: int = 0
    last_synthesis_step: int = -SYNTHESIS_COOLDOWN

    def record_generation(
        self,
        result: SynthesisResult,
        current_step: int,
    ) -> None:
        """Record that synthesis was attempted."""
        if not result.active:
            return

        self.generated_count += result.synthesis_produced
        self.last_synthesis_step = current_step

        for action in result.new_actions:
            if action.strategy_type == "mutation":
                self.mutation_attempts += 1
            elif action.strategy_type == "combination":
                self.combination_attempts += 1
            elif action.strategy_type == "seed":
                self.seed_attempts += 1

    def record_selection(
        self,
        selected_action: str | None,
        result: SynthesisResult,
    ) -> None:
        """Record whether a synthesized action was selected."""
        if not result.active or selected_action is None:
            return

        synth_actions = {a.action: a for a in result.new_actions}
        if selected_action in synth_actions:
            self.selected_count += 1
            synth = synth_actions[selected_action]
            if synth.strategy_type == "mutation":
                self.mutation_successes += 1
            elif synth.strategy_type == "combination":
                self.combination_successes += 1
            elif synth.strategy_type == "seed":
                self.seed_successes += 1

    def success_rate(self, strategy_type: str | None = None) -> float:
        """Overall or per-type synthesis success rate."""
        if strategy_type == "mutation":
            return self.mutation_successes / max(self.mutation_attempts, 1)
        elif strategy_type == "combination":
            return self.combination_successes / max(self.combination_attempts, 1)
        elif strategy_type == "seed":
            return self.seed_successes / max(self.seed_attempts, 1)
        return self.selected_count / max(self.generated_count, 1)

    def snapshot(self) -> dict[str, Any]:
        return {
            "generated_count": self.generated_count,
            "selected_count": self.selected_count,
            "mutation_successes": self.mutation_successes,
            "mutation_attempts": self.mutation_attempts,
            "combination_successes": self.combination_successes,
            "combination_attempts": self.combination_attempts,
            "seed_successes": self.seed_successes,
            "seed_attempts": self.seed_attempts,
            "last_synthesis_step": self.last_synthesis_step,
        }

    def restore(self, data: dict | None) -> None:
        if not data or not isinstance(data, dict):
            return
        self.generated_count = int(data.get("generated_count", 0))
        self.selected_count = int(data.get("selected_count", 0))
        self.mutation_successes = int(data.get("mutation_successes", 0))
        self.mutation_attempts = int(data.get("mutation_attempts", 0))
        self.combination_successes = int(data.get("combination_successes", 0))
        self.combination_attempts = int(data.get("combination_attempts", 0))
        self.seed_successes = int(data.get("seed_successes", 0))
        self.seed_attempts = int(data.get("seed_attempts", 0))
        self.last_synthesis_step = int(
            data.get("last_synthesis_step", -SYNTHESIS_COOLDOWN)
        )


# ─── Trace field extraction ──────────────────────────────────────


def extract_trace_fields(
    synthesis_result: SynthesisResult,
    selected_action: str | None,
) -> SynthesisTraceFields:
    """Extract trace fields from synthesis result + selection outcome."""
    if not synthesis_result.active or not synthesis_result.new_actions:
        return NO_TRACE

    synth_actions = {a.action: a for a in synthesis_result.new_actions}
    was_selected = selected_action in synth_actions

    if was_selected and selected_action is not None:
        synth = synth_actions[selected_action]
        return SynthesisTraceFields(
            strategy_generated=True,
            strategy_type=synth.strategy_type,
            strategy_origin=synth.strategy_origin,
            strategy_selected=True,
        )

    first = synthesis_result.new_actions[0]
    return SynthesisTraceFields(
        strategy_generated=True,
        strategy_type=first.strategy_type,
        strategy_origin=first.strategy_origin,
        strategy_selected=False,
    )
