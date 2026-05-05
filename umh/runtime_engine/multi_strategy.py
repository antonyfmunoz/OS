"""
MultiStrategy — controlled branching + selection for high-value task types.

For selected task types (GENERATE, ANALYZE), produces multiple candidate
responses with varied prompt strategies, evaluates each deterministically,
and selects the best. Only the winning response enters memory, feedback,
and world model — rejected candidates are discarded.

This is NOT full agent orchestration. It is a single-turn branching layer
that wraps the ExecutionSpine without modifying it.

Design:
    - Candidate generation uses model_router.call_with_fallback() directly
      (LLM-only, no side effects — no memory writes, no feedback logging).
    - Evaluation uses OutcomeEvaluator (deterministic heuristics, no LLM).
    - The winning candidate is routed through the full ExecutionSpine pipeline
      for all post-generation stages (memory, feedback, world model).
    - Non-strategy-eligible tasks fall through to normal single execution.

Usage::

    from umh.runtime_engine.multi_strategy import run_with_strategies
    from umh.runtime_engine.execution_spine import SpineResult

    result: SpineResult = run_with_strategies(
        message="Draft outreach for fitness coaches",
        unified_context=uctx,
        agent_type="executive_assistant",
        task_type=TaskType.GENERATE,
        ...
    )
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from umh.runtime_engine.agent_runtime import TaskType

_log = logging.getLogger(__name__)

STRATEGY_ENABLED_TYPES = frozenset({"generate", "analyze"})

STRATEGY_REGISTRY: dict[str, str] = {
    "baseline": "",
    "clarity": (
        "Optimize for clarity and precision. "
        "Use short sentences. Lead with the most important point. "
        "Every sentence must add information."
    ),
    "concise": (
        "Be concise and avoid unnecessary detail. "
        "Eliminate filler words. Every word must earn its place."
    ),
    "structured": (
        "Use structured formatting with clear sections. "
        "Number key points. Use headers where appropriate."
    ),
}

# Per-strategy message-level directives: shape the user prompt before generation.
# System directives (STRATEGY_REGISTRY) tell the LLM how to behave.
# Prompt directives tell the LLM how to approach this specific request.
STRATEGY_PROMPT_DIRECTIVES: dict[str, str] = {
    "baseline": "",
    "clarity": (
        "[Approach: prioritize explicitness — resolve any ambiguity, "
        "state assumptions, lead with the answer.]"
    ),
    "concise": (
        "[Approach: density over length — deliver maximum information "
        "in minimum words, cut preamble.]"
    ),
    "structured": (
        "[Approach: organize reasoning into numbered sections — "
        "outline before drafting, use headings for distinct topics.]"
    ),
}

DEFAULT_STRATEGIES = ["baseline", "clarity"]

# Minimum effective score below which a prompt directive is suppressed.
# Below this, the strategy still runs but without message-level shaping.
DIRECTIVE_SUPPRESSION_THRESHOLD = 0.25


def register_strategy(
    strategy_id: str,
    system_directive: str,
    prompt_directive: str,
) -> bool:
    """Register a new strategy into the live registry.

    Single writer for STRATEGY_REGISTRY mutations.
    Returns True if registered, False if already exists.
    """
    if strategy_id in STRATEGY_REGISTRY:
        return False
    STRATEGY_REGISTRY[strategy_id] = system_directive
    STRATEGY_PROMPT_DIRECTIVES[strategy_id] = prompt_directive
    return True


def unregister_strategy(strategy_id: str) -> bool:
    """Remove a strategy from the live registry.

    Single writer for STRATEGY_REGISTRY deletions.
    Returns True if removed, False if not found.
    """
    if strategy_id not in STRATEGY_REGISTRY:
        return False
    del STRATEGY_REGISTRY[strategy_id]
    STRATEGY_PROMPT_DIRECTIVES.pop(strategy_id, None)
    return True


def _get_suppressed_directives(goal_mode: object = None) -> frozenset[str]:
    """Return directive keys that should be suppressed this turn.

    Combines two sources:
        1. DirectiveMemory: directives with effective_score below threshold.
        2. GoalMode: per-mode suppression list (e.g. FAST suppresses 'structured').

    When directive memory has no data, only mode-based suppression applies.
    Baseline is never suppressed (it has no directive text anyway).
    """
    suppressed: set[str] = set()

    # Mode-based suppression
    if goal_mode is not None:
        try:
            from umh.runtime_engine.goal_mode import MODE_SUPPRESSED_DIRECTIVES

            mode_suppressed = MODE_SUPPRESSED_DIRECTIVES.get(goal_mode, frozenset())
            suppressed.update(mode_suppressed)
        except Exception as e:
            _log.debug("Goal mode directive suppression failed: %s", e)

    # Memory-based suppression
    try:
        from umh.runtime_engine.directive_memory import get_directive_memory

        dmem = get_directive_memory()
        if dmem.has_data():
            current_turn = dmem.global_turn
            for name, stats in dmem.rank_directives():
                if name == "baseline":
                    continue
                if (
                    stats.uses > 0
                    and stats.effective_score(current_turn)
                    < DIRECTIVE_SUPPRESSION_THRESHOLD
                ):
                    suppressed.add(name)
    except Exception:
        pass

    return frozenset(suppressed)


@dataclass
class CandidateResult:
    """A single candidate response with its evaluation."""

    output: str
    strategy_name: str
    quality_score: float
    confidence: float
    evaluation: dict
    model_used: str
    tokens_used: int
    cost_usd: float
    latency_ms: int
    prompt_directive: str = ""
    directive_key: str = ""
    goal_id: str = ""


def _task_type_value(task_type: object) -> str:
    """Extract the string value from a TaskType enum or string."""
    return getattr(task_type, "value", str(task_type) if task_type else "")


def is_strategy_eligible(task_type: object) -> bool:
    """Check whether a task type should use multi-strategy execution."""
    return _task_type_value(task_type) in STRATEGY_ENABLED_TYPES


STALE_THRESHOLD = 5


def pick_strategies(
    num_candidates: int = 2,
    goal_mode: object = None,
    strategy_override: str | None = None,
    exploration_enabled: bool = True,
    goal_state: object = None,
) -> list[str]:
    """Select which strategies to run based on historical performance and goal mode.

    If ``strategy_override`` is set (from UnifiedInfluence), that strategy
    is forced as the first candidate. Remaining slots are filled normally.

    If ``exploration_enabled`` is False, stale strategy rotation is skipped
    (the system stays with proven strategies during corrective phases).

    If goal_mode is provided, its preferred strategies are promoted to
    the front of the selection (bias, not override). Memory-ranked strategies
    fill remaining slots.

    If ``goal_state`` is provided (active GoalState), strategies are
    scored by affinity to the goal and higher-affinity strategies are
    promoted. This is additive to mode preferences, not a replacement.

    If strategy memory has no data, uses mode preferences or DEFAULT_STRATEGIES.
    Always returns strategies that exist in STRATEGY_REGISTRY.
    """
    if strategy_override and strategy_override in STRATEGY_REGISTRY:
        if num_candidates <= 1:
            return [strategy_override]
        remaining = pick_strategies(
            num_candidates=num_candidates - 1,
            goal_mode=goal_mode,
            strategy_override=None,
            exploration_enabled=exploration_enabled,
            goal_state=goal_state,
        )
        remaining = [s for s in remaining if s != strategy_override]
        return [strategy_override] + remaining[: num_candidates - 1]

    from umh.strategy.memory import get_strategy_memory

    # Resolve mode preferences
    mode_prefs: list[str] = []
    if goal_mode is not None:
        try:
            from umh.runtime_engine.goal_mode import MODE_STRATEGY_PREFERENCES

            mode_prefs = [
                s
                for s in MODE_STRATEGY_PREFERENCES.get(goal_mode, [])
                if s in STRATEGY_REGISTRY
            ]
        except Exception as e:
            _log.debug("Goal mode strategy preference resolution failed: %s", e)

    mem = get_strategy_memory()
    if not mem.has_data():
        if mode_prefs:
            base = list(mode_prefs)
            for name in DEFAULT_STRATEGIES:
                if name not in base:
                    base.append(name)
                if len(base) >= num_candidates:
                    break
            return base[:num_candidates]
        return DEFAULT_STRATEGIES[:num_candidates]

    _fetch_count = num_candidates + len(mode_prefs)
    if goal_state is not None:
        _fetch_count = max(_fetch_count, len(STRATEGY_REGISTRY))
    top = mem.get_top_strategies(count=_fetch_count)
    valid = [s for s in top if s in STRATEGY_REGISTRY]

    # Apply mode bias: promote preferred strategies to front
    if mode_prefs:
        promoted: list[str] = []
        for pref in mode_prefs:
            if pref in valid:
                promoted.append(pref)
                valid.remove(pref)
            elif pref in STRATEGY_REGISTRY:
                promoted.append(pref)
        valid = promoted + valid

    # Apply goal-state affinity bias: re-sort by goal affinity score
    if goal_state is not None and not mode_prefs:
        try:
            from umh.goals.state import strategy_goal_score

            valid.sort(
                key=lambda s: strategy_goal_score(s, goal_state),
                reverse=True,
            )
        except Exception as e:
            _log.debug("Goal-state strategy bias failed: %s", e)

    if (
        exploration_enabled
        and len(valid) >= 1
        and num_candidates >= 2
        and not mode_prefs
    ):
        stale = mem.get_stale_strategy(
            known_strategies=list(STRATEGY_REGISTRY.keys()),
            stale_threshold=STALE_THRESHOLD,
        )
        if stale and stale in STRATEGY_REGISTRY and stale not in valid:
            if len(valid) >= num_candidates:
                valid[num_candidates - 1] = stale
            else:
                valid.append(stale)

    if len(valid) < num_candidates:
        for name in DEFAULT_STRATEGIES:
            if name not in valid:
                valid.append(name)
            if len(valid) >= num_candidates:
                break

    return valid[:num_candidates]


def _generate_for_goal(
    message: str,
    system_prompt: str,
    agent_type: str,
    task_type: object,
    strategy_names: list[str],
    suppressed_directives: frozenset[str],
    goal_id: str = "",
) -> list[CandidateResult]:
    """Generate candidates for a single goal with given strategies.

    Internal helper — factored out so budget-driven and legacy paths
    share the same LLM call logic. Each candidate is tagged with goal_id.
    """
    from umh.runtime_engine.model_router import call_with_fallback
    from umh.runtime_engine.outcome_evaluator import evaluate_outcome

    candidates: list[CandidateResult] = []

    for name in strategy_names:
        system_directive = STRATEGY_REGISTRY.get(name, "")
        prompt_directive = STRATEGY_PROMPT_DIRECTIVES.get(name, "")
        if name in suppressed_directives:
            prompt_directive = ""
        prompt = message
        system = system_prompt
        if system_directive:
            system = f"{system_directive}\n\n{system_prompt}"
        if prompt_directive:
            prompt = f"{prompt_directive}\n\n{message}"

        try:
            routing_result = call_with_fallback(
                prompt=prompt,
                system=system or None,
                agent_type=agent_type,
                task_type=task_type,
            )

            output = routing_result.output if routing_result else ""
            if not output:
                _log.debug("Strategy %s returned empty output", name)
                continue

            evaluation = evaluate_outcome(
                input_text=message,
                output_text=output,
                context={
                    "agent_type": agent_type,
                    "task_type": _task_type_value(task_type),
                    "strategy": name,
                },
            )

            candidates.append(
                CandidateResult(
                    output=output,
                    strategy_name=name,
                    quality_score=evaluation["quality_score"],
                    confidence=evaluation["confidence"],
                    evaluation=evaluation,
                    model_used=(
                        f"{routing_result.provider}/{routing_result.model}"
                        if routing_result
                        else "unknown"
                    ),
                    tokens_used=routing_result.tokens_used if routing_result else 0,
                    cost_usd=routing_result.cost_usd if routing_result else 0.0,
                    latency_ms=routing_result.latency_ms if routing_result else 0,
                    prompt_directive=prompt_directive,
                    directive_key=name,
                    goal_id=goal_id,
                )
            )
        except Exception as e:
            _log.warning("Strategy %s failed: %s", name, e)
            continue

    return candidates


def generate_candidates(
    message: str,
    system_prompt: str,
    agent_type: str = "executive_assistant",
    task_type: object = None,
    num_candidates: int = 2,
    goal_mode: object = None,
    strategy_override: str | None = None,
    exploration_enabled: bool = True,
    goal_state: object = None,
    budget_allocation: object = None,
    goal_registry: object = None,
) -> list[CandidateResult]:
    """Generate multiple candidate responses with varied prompt strategies.

    When ``budget_allocation`` is provided, generates candidates per-goal
    according to each goal's candidate_slots. Each candidate is tagged
    with its originating goal_id. Strategy selection is biased toward
    each goal's affinity.

    Without budget_allocation, behavior is identical to before (backward
    compatible single-goal path).

    Calls model_router.call_with_fallback() directly for each candidate.
    No side effects — no memory writes, no feedback logging.
    """
    suppressed_directives = _get_suppressed_directives(goal_mode=goal_mode)

    # Budget-driven per-goal allocation
    if budget_allocation is not None and goal_registry is not None:
        allocs = getattr(budget_allocation, "allocations", ())
        if allocs:
            all_candidates: list[CandidateResult] = []
            for alloc in allocs:
                gid = alloc.goal_id
                slots = alloc.candidate_slots
                if slots <= 0:
                    continue

                goal_for_strat = goal_registry.get_goal(gid) if goal_registry else None
                strat_names = pick_strategies(
                    num_candidates=slots,
                    goal_mode=goal_mode,
                    strategy_override=strategy_override
                    if gid == budget_allocation.primary_goal_id
                    else None,
                    exploration_enabled=exploration_enabled,
                    goal_state=goal_for_strat,
                )

                goal_candidates = _generate_for_goal(
                    message=message,
                    system_prompt=system_prompt,
                    agent_type=agent_type,
                    task_type=task_type,
                    strategy_names=strat_names,
                    suppressed_directives=suppressed_directives,
                    goal_id=gid,
                )
                all_candidates.extend(goal_candidates)

            if all_candidates:
                return all_candidates

    # Legacy single-goal path (backward compat)
    strategy_names = pick_strategies(
        num_candidates,
        goal_mode=goal_mode,
        strategy_override=strategy_override,
        exploration_enabled=exploration_enabled,
        goal_state=goal_state,
    )

    _gid = getattr(goal_state, "goal_id", "") if goal_state else ""

    return _generate_for_goal(
        message=message,
        system_prompt=system_prompt,
        agent_type=agent_type,
        task_type=task_type,
        strategy_names=strategy_names,
        suppressed_directives=suppressed_directives,
        goal_id=_gid,
    )


def select_best(
    candidates: list[CandidateResult],
    min_confidence: float | None = None,
    goal_state: object = None,
    goal_score: float | None = None,
) -> CandidateResult | None:
    """Select the best candidate by quality_score, tie-breaking with confidence.

    Records win/loss to strategy memory so future calls can bias toward
    higher-performing strategies.  When ``min_confidence`` is provided
    (from calibration), it overrides strategy_memory's default gate.

    When ``goal_state`` is provided, quality scores recorded to memory
    are weighted by goal relevance — wins that align with the goal get
    amplified, losses that misalign get dampened.

    When ``goal_score`` is provided, it is passed to strategy_memory
    record_win/loss for goal-aligned reinforcement weighting.

    Selection itself is unchanged (best quality wins regardless of goal).
    """
    if not candidates:
        return None

    winner = max(candidates, key=lambda c: (c.quality_score, c.confidence))

    goal_relevance: float = 1.0
    if goal_state is not None:
        try:
            from umh.goals.state import compute_goal_relevance

            for c in candidates:
                ctx = {
                    "strategy": c.strategy_name,
                    "quality": c.quality_score,
                }
                ctx.update(c.evaluation.get("context", {}))
                goal_relevance = compute_goal_relevance(goal_state, ctx)
                break
        except Exception:
            goal_relevance = 1.0

    try:
        from umh.strategy.memory import get_strategy_memory

        mem = get_strategy_memory()
        for c in candidates:
            weighted_score = c.quality_score * goal_relevance
            if c is winner:
                mem.record_win(
                    c.strategy_name,
                    weighted_score,
                    c.confidence,
                    min_confidence=min_confidence,
                    goal_score=goal_score,
                )
            else:
                mem.record_loss(
                    c.strategy_name,
                    weighted_score,
                    c.confidence,
                    min_confidence=min_confidence,
                    goal_score=goal_score,
                )
    except Exception as e:
        _log.debug("Strategy memory update skipped: %s", e)

    try:
        from umh.runtime_engine.directive_memory import get_directive_memory

        dmem = get_directive_memory()
        for c in candidates:
            directive_key = c.strategy_name
            weighted_score = c.quality_score * goal_relevance
            if c is winner:
                dmem.record_win(
                    directive_key,
                    weighted_score,
                    c.confidence,
                    min_confidence=min_confidence,
                )
            else:
                dmem.record_loss(
                    directive_key,
                    weighted_score,
                    c.confidence,
                    min_confidence=min_confidence,
                )
    except Exception as e:
        _log.debug("Directive memory update skipped: %s", e)

    return winner


def run_with_strategies(
    message: str,
    unified_context: object,
    agent_type: str = "executive_assistant",
    authority_class: str = "analyze",
    session_id: str | None = None,
    channel_id: str | None = None,
    org_id: str | None = None,
    user_id: str | None = None,
    task_type: object = None,
    venture_id: str | None = None,
    skill_name: str | None = None,
    num_candidates: int = 2,
    min_confidence: float | None = None,
    goal_mode: object = None,
    strategy_override: str | None = None,
    exploration_enabled: bool = True,
    goal_state: object = None,
    budget_allocation: object = None,
    goal_registry: object = None,
    exploration_rate: float | None = None,
) -> "SpineResult":
    """Execute with multi-strategy branching for eligible task types.

    When goal_mode is provided, strategy selection and directive filtering
    are biased toward mode-appropriate behavior (deterministic, no LLM).

    When goal_state is provided, strategy selection is further biased by
    goal affinity, and memory feedback is weighted by goal relevance.

    For GENERATE and ANALYZE tasks: generates multiple candidates,
    evaluates each, selects the best, and runs the winner through
    the full spine pipeline (memory, feedback, world model).

    For all other task types: falls through to normal single execution.
    """
    from umh.runtime_engine.execution_spine import run_via_umh, SpineResult

    if not is_strategy_eligible(task_type):
        return run_via_umh(
            message=message,
            unified_context=unified_context,
            agent_type=agent_type,
            authority_class=authority_class,
            session_id=session_id,
            channel_id=channel_id,
            org_id=org_id,
            user_id=user_id,
            task_type=task_type,
            venture_id=venture_id,
            skill_name=skill_name,
        )

    system_prompt = ""
    try:
        system_prompt = unified_context.to_system_prompt()
    except Exception as e:
        _log.warning("Context assembly failed: %s", e)

    # Pre-generation enhancement — same path as ExecutionSpine Stage 2.
    # Runs once before candidate generation so all candidates benefit
    # from the same enhanced prompt.  Side-effect free.
    enhanced_message = message
    try:
        from umh.stages.enhancement import enhance_prompt
        from umh.environments.system_context import load_context_from_env

        _ctx = load_context_from_env()
        _runtime = None
        try:
            from umh.runtime_engine.agent_runtime import AgentRuntime

            _runtime = AgentRuntime()
        except Exception:
            pass
        enhanced_message = enhance_prompt(message, _ctx, _runtime)
    except Exception as e:
        _log.debug("Prompt enhancement skipped for multi-strategy: %s", e)

    _effective_candidates = num_candidates
    if exploration_rate is not None:
        try:
            from umh.runtime_engine.adaptive_exploration import exploration_rate_to_num_candidates

            _effective_candidates = exploration_rate_to_num_candidates(
                exploration_rate, base_candidates=num_candidates
            )
        except Exception:
            pass
    if budget_allocation is not None:
        _effective_candidates = max(
            _effective_candidates,
            getattr(budget_allocation, "total_candidates", num_candidates),
        )

    candidates = generate_candidates(
        message=enhanced_message,
        system_prompt=system_prompt,
        agent_type=agent_type,
        task_type=task_type,
        num_candidates=_effective_candidates,
        goal_mode=goal_mode,
        strategy_override=strategy_override,
        exploration_enabled=exploration_enabled,
        goal_state=goal_state,
        budget_allocation=budget_allocation,
        goal_registry=goal_registry,
    )

    if not candidates:
        _log.warning("All candidates failed, falling back to normal execution")
        return run_via_umh(
            message=message,
            unified_context=unified_context,
            agent_type=agent_type,
            authority_class=authority_class,
            session_id=session_id,
            channel_id=channel_id,
            org_id=org_id,
            user_id=user_id,
            task_type=task_type,
            venture_id=venture_id,
            skill_name=skill_name,
        )

    winner = select_best(
        candidates, min_confidence=min_confidence, goal_state=goal_state
    )
    if winner is None:
        return run_via_umh(
            message=message,
            unified_context=unified_context,
            agent_type=agent_type,
            authority_class=authority_class,
            session_id=session_id,
            channel_id=channel_id,
            org_id=org_id,
            user_id=user_id,
            task_type=task_type,
            venture_id=venture_id,
            skill_name=skill_name,
        )

    _log.info(
        "multi_strategy: %d candidates, winner=%s score=%.3f confidence=%.3f",
        len(candidates),
        winner.strategy_name,
        winner.quality_score,
        winner.confidence,
    )

    total_cost = sum(c.cost_usd for c in candidates)
    total_tokens = sum(c.tokens_used for c in candidates)
    total_latency = sum(c.latency_ms for c in candidates)

    # Commit only the winner through the unified pipeline
    from umh.runtime_engine.commit_pipeline import commit_winner

    _wm_signal = None
    try:
        from umh.runtime_engine.signal_router import route_signals

        _routed = route_signals(winner.evaluation)
        _wm_signal = _routed.world_model
    except Exception:
        pass

    ctx = None
    try:
        from umh.environments.system_context import load_context_from_env

        ctx = load_context_from_env()
    except Exception as e:
        _log.warning("Cannot load context for persistence: %s", e)

    if ctx is not None:
        commit_winner(
            message=message,
            response=winner.output,
            ctx=ctx,
            agent_type=agent_type,
            session_id=session_id,
            channel_id=channel_id,
            org_id=org_id,
            task_type=task_type,
            venture_id=venture_id,
            skill_name=skill_name,
            evaluation=winner.evaluation,
            world_model_signal=_wm_signal,
            model_used=winner.model_used,
            tokens_used={
                "input": 0,
                "output": 0,
                "total": total_tokens,
            },
            iterations=len(candidates),
        )

    return SpineResult(
        winner.output,
        model_used=winner.model_used,
        tokens_used={"input": 0, "output": 0, "total": total_tokens},
        cost_usd=total_cost,
        latency_ms=total_latency,
        session_id=session_id or "",
        iterations=len(candidates),
        was_enhanced=False,
    )
