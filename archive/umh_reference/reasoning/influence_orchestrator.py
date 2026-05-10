"""
InfluenceOrchestrator — deterministic merge of all next-turn influences.

Collects pending directives from Control, Convergence, Strategy, and Goal
layers, resolves conflicts with a fixed priority order, and produces a
single UnifiedInfluence object consumed by the next turn.

Priority (highest → lowest):
    1. SAFETY / CONTROL — cannot be overridden
    2. CONVERGENCE corrections
    3. GOAL progress gating — refines within allowed space
    4. STRATEGY overrides — only apply if not blocked by higher layers
    5. SYNTHESIS / EXPLORATION toggles — lowest

Goal-driven behavioral gating:
    - goal_progress_signal (delta) directly gates exploration/synthesis
    - Negative delta (< GOAL_NEGATIVE_THRESHOLD) disables exploration
    - Sustained positive delta (>= GOAL_POSITIVE_THRESHOLD for
      GOAL_POSITIVE_STREAK_WINDOW turns) enables synthesis
    - Convergence UNSTABLE always overrides goal gating
    - No goal → gating bypassed entirely

No LLM calls. No randomness. Pure deterministic merge.

Usage::

    from umh.reasoning.influence_orchestrator import resolve_influence, UnifiedInfluence

    influence = resolve_influence(
        control_directives=["be precise"],
        convergence_directives=["simplify"],
        strategy_override="structured",
        synthesis_suppressed=True,
        exploration_suppressed=False,
        convergence_status="unstable",
        goal_progress_signal=-0.08,
        goal_delta_history=[-0.06, -0.08],
    )
    # influence.directives — deduplicated, priority-ordered
    # influence.strategy_override — "structured" or None
    # influence.synthesis_enabled — True/False
    # influence.exploration_enabled — True/False
    # influence.goal_gating_reason — why goal gating acted (or None)
"""

from __future__ import annotations

from dataclasses import dataclass

# ─── Goal gating thresholds (deterministic constants) ──────────────────────

GOAL_NEGATIVE_THRESHOLD = -0.05
GOAL_POSITIVE_THRESHOLD = 0.05
GOAL_POSITIVE_STREAK_WINDOW = 3


@dataclass(frozen=True)
class UnifiedInfluence:
    """Single coherent directive set for the next turn."""

    directives: tuple[str, ...]
    strategy_override: str | None
    synthesis_enabled: bool
    exploration_enabled: bool
    goal_weight: float = 0.0
    goal_directives: tuple[str, ...] = ()
    goal_progress_signal: float = 0.0
    convergence_status: str | None = None
    goal_gating_reason: str | None = None

    def to_dict(self) -> dict:
        d: dict = {
            "directives": list(self.directives),
            "strategy_override": self.strategy_override,
            "synthesis_enabled": self.synthesis_enabled,
            "exploration_enabled": self.exploration_enabled,
            "goal_weight": self.goal_weight,
            "goal_directives": list(self.goal_directives),
            "goal_progress_signal": self.goal_progress_signal,
        }
        if self.convergence_status is not None:
            d["convergence_status"] = self.convergence_status
        if self.goal_gating_reason is not None:
            d["goal_gating_reason"] = self.goal_gating_reason
        return d


NO_INFLUENCE = UnifiedInfluence(
    directives=(),
    strategy_override=None,
    synthesis_enabled=True,
    exploration_enabled=True,
    goal_weight=0.0,
    goal_directives=(),
    goal_progress_signal=0.0,
    convergence_status=None,
    goal_gating_reason=None,
)


def resolve_influence(
    control_directives: list[str] | None = None,
    convergence_directives: list[str] | None = None,
    strategy_override: str | None = None,
    synthesis_suppressed: bool = False,
    exploration_suppressed: bool = False,
    goal_state: object | None = None,
    goal_progress_signal: float = 0.0,
    convergence_status: str | None = None,
    goal_delta_history: list[float] | None = None,
    blended_goal_state: object | None = None,
    goal_registry: object | None = None,
) -> UnifiedInfluence:
    """Merge all pending next-turn influences deterministically.

    Merge rules (strict priority):
        1. Control directives are always included first and cannot be removed.
        2. Convergence directives are appended after control directives.
        3. Duplicate directives (exact string match) are removed, keeping
           the first occurrence (which preserves priority ordering).
        4. Strategy override is accepted ONLY if control did not already
           set directives (control intervention implies the system is in
           a corrective state — strategy overrides are deferred).
        5. Synthesis is disabled if EITHER control directives are present
           OR convergence explicitly suppresses it.
        6. Exploration is disabled if EITHER control directives are present
           OR convergence explicitly suppresses it.
        7. Goal-driven behavioral gating refines exploration/synthesis
           within the space allowed by Control and Convergence.
           Priority: Control > Convergence > Goal.
        8. Goal directives and weight are computed from goal_state when
           provided and active. Goal directives are NOT merged into the
           main directive list — they travel separately so consumers can
           position them independently (e.g., before unified directives).

    When no inputs are pending and no goal is set, returns NO_INFLUENCE
    — identical to pre-orchestrator behavior.
    """
    ctrl = control_directives or []
    conv = convergence_directives or []

    has_control = len(ctrl) > 0

    # ── 1-3. Merge directives in priority order, deduplicate ────────────
    merged: list[str] = []
    seen: set[str] = set()

    for d in ctrl:
        if d not in seen:
            seen.add(d)
            merged.append(d)

    for d in conv:
        if d not in seen:
            seen.add(d)
            merged.append(d)

    # ── 4. Strategy override: blocked when control is intervening ───────
    resolved_override: str | None = None
    if not has_control and strategy_override is not None:
        resolved_override = strategy_override

    # ── 5-6. Synthesis/exploration: disabled by control OR convergence ──
    synthesis_enabled = True
    exploration_enabled = True

    if has_control or synthesis_suppressed:
        synthesis_enabled = False

    if has_control or exploration_suppressed:
        exploration_enabled = False

    # ── 7. Goal-driven behavioral gating ────────────────────────────────
    # Only refines within the space allowed by Control + Convergence.
    # If higher-priority layers already disabled, goal cannot re-enable.
    goal_gating_reason: str | None = None
    _goal_progress = goal_progress_signal
    _delta_hist = goal_delta_history or []

    if goal_state is not None and _goal_progress != 0.0:
        # Rule: UNSTABLE convergence overrides all goal gating
        if convergence_status == "unstable":
            goal_gating_reason = "convergence_override"
        else:
            # Exploration gating: negative delta disables
            if exploration_enabled and _goal_progress < GOAL_NEGATIVE_THRESHOLD:
                exploration_enabled = False
                goal_gating_reason = "negative_goal_delta"

            # Exploration gating: positive delta enables (within allowed space)
            elif (
                not exploration_enabled
                and _goal_progress > GOAL_POSITIVE_THRESHOLD
                and convergence_status != "unstable"
                and not has_control
                and not exploration_suppressed
            ):
                exploration_enabled = True
                goal_gating_reason = "positive_goal_delta"

            # Synthesis gating: negative delta disables
            if synthesis_enabled and _goal_progress < GOAL_NEGATIVE_THRESHOLD:
                synthesis_enabled = False
                if goal_gating_reason is None:
                    goal_gating_reason = "negative_goal_delta"
                elif goal_gating_reason == "negative_goal_delta":
                    pass  # already set
                else:
                    goal_gating_reason = goal_gating_reason + "+negative_synthesis"

            # Synthesis gating: sustained positive delta enables
            if (
                not synthesis_enabled
                and not has_control
                and not synthesis_suppressed
                and convergence_status != "unstable"
                and _has_sustained_positive(_delta_hist, _goal_progress)
            ):
                synthesis_enabled = True
                if goal_gating_reason is None:
                    goal_gating_reason = "sustained_positive_delta"
                else:
                    goal_gating_reason = (
                        goal_gating_reason + "+sustained_positive_synthesis"
                    )

    # ── 8. Goal conditioning ────────────────────────────────────────────
    # Blended goals: merge directives from all blended goals in weight
    # order. Compute blended goal_weight as weighted sum.
    # Falls back to single goal_state when no blend is present.
    goal_weight: float = 0.0
    goal_directives: tuple[str, ...] = ()

    if blended_goal_state is not None and goal_registry is not None:
        try:
            from umh.goals.state import compute_goal_weight, generate_goal_directives

            _blend_goals = getattr(blended_goal_state, "goals", ())
            if _blend_goals:
                _blended_weight = 0.0
                _blended_dirs: list[str] = []
                _dir_seen: set[str] = set()

                for _bgid, _bw in _blend_goals:
                    _bg = goal_registry.get_goal(_bgid)
                    if _bg is None:
                        continue
                    _gw = compute_goal_weight(_bg)
                    _blended_weight += _gw * _bw
                    for _d in generate_goal_directives(_bg):
                        if _d not in _dir_seen:
                            _dir_seen.add(_d)
                            _blended_dirs.append(_d)

                goal_weight = _blended_weight
                goal_directives = tuple(_blended_dirs)
        except Exception:
            pass
    elif goal_state is not None:
        try:
            from umh.goals.state import compute_goal_weight, generate_goal_directives

            goal_weight = compute_goal_weight(goal_state)
            goal_directives = generate_goal_directives(goal_state)
        except Exception:
            pass

    # ── Short-circuit: no influence at all ──────────────────────────────
    if (
        not merged
        and resolved_override is None
        and synthesis_enabled
        and exploration_enabled
        and goal_weight == 0.0
        and not goal_directives
        and _goal_progress == 0.0
        and convergence_status is None
        and goal_gating_reason is None
    ):
        return NO_INFLUENCE

    return UnifiedInfluence(
        directives=tuple(merged),
        strategy_override=resolved_override,
        synthesis_enabled=synthesis_enabled,
        exploration_enabled=exploration_enabled,
        goal_weight=goal_weight,
        goal_directives=goal_directives,
        goal_progress_signal=_goal_progress,
        convergence_status=convergence_status,
        goal_gating_reason=goal_gating_reason,
    )


def _has_sustained_positive(
    delta_history: list[float],
    current_delta: float,
) -> bool:
    """Check if there's a sustained positive delta streak.

    Requires GOAL_POSITIVE_STREAK_WINDOW consecutive positive deltas
    (including the current one) all >= GOAL_POSITIVE_THRESHOLD.
    """
    recent = list(delta_history)
    if current_delta not in recent:
        recent.append(current_delta)

    if len(recent) < GOAL_POSITIVE_STREAK_WINDOW:
        return False

    tail = recent[-GOAL_POSITIVE_STREAK_WINDOW:]
    return all(d >= GOAL_POSITIVE_THRESHOLD for d in tail)
