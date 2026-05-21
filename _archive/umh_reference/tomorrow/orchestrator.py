"""Phase 86 Tomorrow Loop orchestrator — daily operating cycle coordination.

Threads the daily loop phases: prepare → brief → execute → review → close → handoff.
Each phase transition is recorded. The orchestrator produces typed state at every step.

Deterministic v1 — no LLM calls. Consumes existing contracts from the workflow
template and produces objectives, reviews, and handoffs as typed data.

The orchestrator does NOT call adapters directly. It produces state that the
control plane (API/CLI) or scheduled runner can act on.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from umh.core.clock import iso_now as _iso_now

from umh.tomorrow.contracts import (
    DailyObjective,
    DailyReview,
    KPIDefinition,
    LoopPhase,
    ReviewOutcome,
    TomorrowHandoff,
    TomorrowLoopState,
    WorkflowStage,
    WorkflowStageStatus,
    WorkflowTemplate,
    _loop_id,
)


# ─── Phase Transition Rules ────────────────────────────────────────


_VALID_TRANSITIONS: dict[LoopPhase, frozenset[LoopPhase]] = {
    LoopPhase.NOT_STARTED: frozenset({LoopPhase.PREPARE, LoopPhase.FAILED}),
    LoopPhase.PREPARE: frozenset({LoopPhase.BRIEF, LoopPhase.FAILED}),
    LoopPhase.BRIEF: frozenset({LoopPhase.EXECUTE, LoopPhase.FAILED}),
    LoopPhase.EXECUTE: frozenset({LoopPhase.REVIEW, LoopPhase.FAILED}),
    LoopPhase.REVIEW: frozenset({LoopPhase.CLOSE, LoopPhase.FAILED}),
    LoopPhase.CLOSE: frozenset({LoopPhase.HANDOFF, LoopPhase.FAILED}),
    LoopPhase.HANDOFF: frozenset({LoopPhase.COMPLETED, LoopPhase.FAILED}),
    LoopPhase.COMPLETED: frozenset(),
    LoopPhase.FAILED: frozenset(),
}


def _can_transition(current: LoopPhase, target: LoopPhase) -> bool:
    return target in _VALID_TRANSITIONS.get(current, frozenset())


def _record_transition(state: TomorrowLoopState, target: LoopPhase) -> None:
    state.phase_transitions.append(
        {
            "from": state.phase.value,
            "to": target.value,
            "at": _iso_now(),
        }
    )
    state.phase = target


# ─── Loop Initialization ───────────────────────────────────────────


def initialize_loop(
    template: WorkflowTemplate,
    date: str | None = None,
    previous_handoff: TomorrowHandoff | None = None,
) -> TomorrowLoopState:
    """Create a new day's operating loop from a workflow template.

    If a previous_handoff is provided, carries forward unresolved items
    and tomorrow_objectives as today's starting objectives.
    """
    loop_date = date or datetime.now(timezone.utc).strftime("%Y-%m-%d")
    state = TomorrowLoopState(
        loop_id=_loop_id("tloop"),
        date=loop_date,
        phase=LoopPhase.NOT_STARTED,
        template_id=template.template_id,
    )

    if previous_handoff:
        for obj in previous_handoff.tomorrow_objectives:
            state.objectives.append(
                DailyObjective(
                    objective_id=_loop_id("obj"),
                    description=obj.description,
                    stage_id=obj.stage_id,
                    priority=obj.priority,
                    completed=False,
                )
            )
        if previous_handoff.blockers_carried:
            state.warnings.extend(
                f"Carried blocker: {b}" for b in previous_handoff.blockers_carried
            )

    return state


# ─── Phase: Prepare ────────────────────────────────────────────────


def run_prepare(
    state: TomorrowLoopState,
    template: WorkflowTemplate,
) -> TomorrowLoopState:
    """Prepare phase — generate today's objectives from the workflow template.

    If no objectives were carried from yesterday's handoff, generates
    default objectives from active workflow stages.
    """
    if not _can_transition(state.phase, LoopPhase.PREPARE):
        state.warnings.append(f"Cannot prepare from phase {state.phase.value}")
        return state

    _record_transition(state, LoopPhase.PREPARE)

    if not state.objectives:
        for stage in template.stages:
            if stage.status in (WorkflowStageStatus.NOT_STARTED, WorkflowStageStatus.ACTIVE):
                state.objectives.append(
                    DailyObjective(
                        objective_id=_loop_id("obj"),
                        description=f"[{stage.name}] {stage.objective}",
                        stage_id=stage.stage_id,
                        priority="high" if stage.stage_number <= 3 else "medium",
                    )
                )

    if not state.objectives:
        state.warnings.append("No objectives generated — all stages may be completed or blocked")

    return state


# ─── Phase: Brief ──────────────────────────────────────────────────


def run_brief(
    state: TomorrowLoopState,
    template: WorkflowTemplate,
) -> TomorrowLoopState:
    """Brief phase — produce the morning briefing data.

    Deterministic v1: returns structured summary of today's objectives,
    active stages, carried blockers, and KPI targets.
    """
    if not _can_transition(state.phase, LoopPhase.BRIEF):
        state.warnings.append(f"Cannot brief from phase {state.phase.value}")
        return state

    _record_transition(state, LoopPhase.BRIEF)

    active_stages = [s for s in template.stages if s.status == WorkflowStageStatus.ACTIVE]
    blocked_stages = [s for s in template.stages if s.status == WorkflowStageStatus.BLOCKED]

    state.metadata["brief"] = {
        "date": state.date,
        "objective_count": len(state.objectives),
        "active_stage_count": len(active_stages),
        "blocked_stage_count": len(blocked_stages),
        "active_stages": [s.name for s in active_stages],
        "blocked_stages": [s.name for s in blocked_stages],
        "kpi_targets": [
            {"name": k.name, "target": k.target, "current": k.current_value}
            for k in template.kpis[:10]
        ],
        "carried_warnings": list(state.warnings),
    }

    return state


# ─── Phase: Execute ────────────────────────────────────────────────


def record_objective_completion(
    state: TomorrowLoopState,
    objective_id: str,
    result: str = "",
) -> bool:
    """Mark an objective as completed during the execute phase.

    Returns True if the objective was found and updated.
    """
    for obj in state.objectives:
        if obj.objective_id == objective_id:
            obj.completed = True
            obj.result = result
            return True
    return False


def add_objective(
    state: TomorrowLoopState,
    description: str,
    stage_id: str = "",
    priority: str = "medium",
) -> DailyObjective:
    """Add a new objective during the execute phase."""
    obj = DailyObjective(
        objective_id=_loop_id("obj"),
        description=description,
        stage_id=stage_id,
        priority=priority,
    )
    state.objectives.append(obj)
    return obj


def start_execute(state: TomorrowLoopState) -> TomorrowLoopState:
    """Transition to execute phase — the user works on objectives."""
    if not _can_transition(state.phase, LoopPhase.EXECUTE):
        state.warnings.append(f"Cannot execute from phase {state.phase.value}")
        return state

    _record_transition(state, LoopPhase.EXECUTE)
    return state


# ─── Phase: Review ─────────────────────────────────────────────────


def run_review(
    state: TomorrowLoopState,
    *,
    what_worked: list[str] | None = None,
    what_didnt: list[str] | None = None,
    blockers: list[str] | None = None,
) -> TomorrowLoopState:
    """Review phase — analyze today's execution and produce a DailyReview.

    Deterministic v1: calculates completion rate, determines outcome,
    and records learnings.
    """
    if not _can_transition(state.phase, LoopPhase.REVIEW):
        state.warnings.append(f"Cannot review from phase {state.phase.value}")
        return state

    _record_transition(state, LoopPhase.REVIEW)

    completed = state.completed_count
    total = state.objective_count

    if total == 0:
        outcome = ReviewOutcome.NEEDS_ADJUSTMENT
    elif blockers:
        outcome = ReviewOutcome.BLOCKED
    elif completed == total:
        outcome = ReviewOutcome.ON_TRACK
    elif completed >= total * 0.5:
        outcome = ReviewOutcome.NEEDS_ADJUSTMENT
    else:
        outcome = ReviewOutcome.CRITICAL

    state.review = DailyReview(
        review_id=_loop_id("rev"),
        date=state.date,
        objectives_completed=completed,
        objectives_total=total,
        outcome=outcome,
        what_worked=what_worked or [],
        what_didnt=what_didnt or [],
        blockers=blockers or [],
    )

    return state


# ─── Phase: Close ──────────────────────────────────────────────────


def run_close(
    state: TomorrowLoopState,
    *,
    tomorrow_priorities: list[str] | None = None,
) -> TomorrowLoopState:
    """Close phase — finalize today and set tomorrow's priorities.

    Adds tomorrow_priorities to the review and prepares for handoff.
    """
    if not _can_transition(state.phase, LoopPhase.CLOSE):
        state.warnings.append(f"Cannot close from phase {state.phase.value}")
        return state

    _record_transition(state, LoopPhase.CLOSE)

    if state.review and tomorrow_priorities:
        state.review.tomorrow_priorities = tomorrow_priorities

    return state


# ─── Phase: Handoff ────────────────────────────────────────────────


def run_handoff(
    state: TomorrowLoopState,
    template: WorkflowTemplate,
) -> TomorrowLoopState:
    """Handoff phase — produce the TomorrowHandoff for the next day's loop.

    Carries forward: unresolved objectives, blockers, continuity notes,
    and generates tomorrow's starting objectives from the review.
    """
    if not _can_transition(state.phase, LoopPhase.HANDOFF):
        state.warnings.append(f"Cannot handoff from phase {state.phase.value}")
        return state

    _record_transition(state, LoopPhase.HANDOFF)

    unresolved = [o.description for o in state.objectives if not o.completed]

    blockers_carried: list[str] = []
    if state.review:
        blockers_carried = list(state.review.blockers)

    tomorrow_objectives: list[DailyObjective] = []

    if state.review and state.review.tomorrow_priorities:
        for i, pri in enumerate(state.review.tomorrow_priorities[:10]):
            tomorrow_objectives.append(
                DailyObjective(
                    objective_id=_loop_id("obj"),
                    description=pri,
                    priority="high" if i < 3 else "medium",
                )
            )

    for desc in unresolved[:5]:
        tomorrow_objectives.append(
            DailyObjective(
                objective_id=_loop_id("obj"),
                description=f"[Carried] {desc}",
                priority="high",
            )
        )

    continuity_notes: list[str] = []
    if state.review:
        if state.review.outcome == ReviewOutcome.ON_TRACK:
            continuity_notes.append("Yesterday was on track — continue momentum")
        elif state.review.outcome == ReviewOutcome.BLOCKED:
            continuity_notes.append(
                f"Yesterday was blocked — resolve: {', '.join(blockers_carried[:3])}"
            )
        elif state.review.outcome == ReviewOutcome.CRITICAL:
            continuity_notes.append("Yesterday was critical — reassess priorities")

    kpi_snapshot = [k.to_dict() for k in template.kpis[:10]]

    state.handoff = TomorrowHandoff(
        handoff_id=_loop_id("handoff"),
        date=state.date,
        continuity_notes=continuity_notes,
        tomorrow_objectives=tomorrow_objectives,
        unresolved=unresolved,
        blockers_carried=blockers_carried,
        kpi_snapshot=kpi_snapshot,
    )

    return state


# ─── Complete ───────────────────────────────────────────────────────


def complete_loop(state: TomorrowLoopState) -> TomorrowLoopState:
    """Mark the loop as completed."""
    if not _can_transition(state.phase, LoopPhase.COMPLETED):
        state.warnings.append(f"Cannot complete from phase {state.phase.value}")
        return state

    _record_transition(state, LoopPhase.COMPLETED)
    return state


# ─── Full Cycle ─────────────────────────────────────────────────────


def run_full_cycle(
    template: WorkflowTemplate,
    *,
    date: str | None = None,
    previous_handoff: TomorrowHandoff | None = None,
    what_worked: list[str] | None = None,
    what_didnt: list[str] | None = None,
    blockers: list[str] | None = None,
    tomorrow_priorities: list[str] | None = None,
) -> TomorrowLoopState:
    """Run the complete daily cycle: prepare → brief → execute → review → close → handoff → complete.

    This is the top-level convenience function for running a full day's loop
    in a single call. For interactive use, call individual phase functions.
    """
    state = initialize_loop(template, date=date, previous_handoff=previous_handoff)
    state = run_prepare(state, template)
    state = run_brief(state, template)
    state = start_execute(state)
    state = run_review(state, what_worked=what_worked, what_didnt=what_didnt, blockers=blockers)
    state = run_close(state, tomorrow_priorities=tomorrow_priorities)
    state = run_handoff(state, template)
    state = complete_loop(state)
    return state
