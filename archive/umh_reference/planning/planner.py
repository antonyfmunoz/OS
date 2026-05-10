"""UMH Execution Planner — objective-to-task planning pipeline.

Converts PlanObjective → ExecutionPlan → validated plan → Task.

Template-first: checks registered templates before attempting LLM planning.
LLM plans are treated as untrusted and must pass the same validator.

Usage:
    from umh.planning.planner import create_plan, execute_plan

    plan = create_plan(objective)
    if plan.status == PlanStatus.VALIDATED:
        task = execute_plan(plan)
"""

from __future__ import annotations

import json
import logging
import threading
import uuid
from typing import TYPE_CHECKING

from umh.core.clock import iso_now as _iso_now

if TYPE_CHECKING:
    from umh.brains.context import BrainContext
from umh.events.stream import publish as _publish_event
from umh.planning.explanation import explain_plan as _explain_plan
from umh.planning.models import (
    ExecutionPlan,
    ExecutionPlanStep,
    PlanObjective,
    PlanSource,
    PlanStatus,
)
from umh.planning.objective import reconstruct_objective
from umh.planning.quality import QualityVerdict, score_plan as _score_plan
from umh.planning.templates import get_template, list_templates
from umh.planning.validator import validate_plan

_log = logging.getLogger(__name__)


def create_plan_from_raw(
    raw_input: str,
    requested_by: str = "",
    brain_context: "BrainContext | None" = None,
) -> ExecutionPlan:
    """Create a plan from raw user input string.

    Reconstructs a structured objective from messy text, then delegates
    to create_plan(). When brain_context is provided, it's injected
    into the objective's context dict so the planner has richer input.
    """
    objective = reconstruct_objective(raw_input)
    if requested_by:
        objective.requested_by = requested_by

    if brain_context and brain_context.brain_id:
        objective.context["brain"] = brain_context.to_dict()

    _publish_event(
        "objective.reconstructed",
        payload={
            "objective_id": objective.objective_id,
            "raw_input": raw_input,
            "title": objective.title,
            "intent_category": objective.intent_category,
            "uncertainty": list(objective.uncertainty),
        },
        actor_id=requested_by,
    )

    return create_plan(objective)


def create_plan(objective: PlanObjective) -> ExecutionPlan:
    """Create a plan from an objective using templates or LLM.

    1. Check template registry for a matching template.
    2. If no template, attempt LLM-assisted planning (optional).
    3. Validate the plan.
    4. Score quality and generate explanation.
    5. Return validated or rejected plan with quality/explanation attached.
    """
    plan = _try_template(objective)

    if plan is None:
        plan = _try_llm_plan(objective)

    if plan is None:
        plan = ExecutionPlan(
            objective=objective,
            steps=[],
            source=PlanSource.MANUAL,
            status=PlanStatus.REJECTED,
            validation_errors=[f"No template found for '{objective.title}'"],
        )
        quality = _score_plan(plan)
        explanation = _explain_plan(plan, None, quality)
        plan.quality_score = quality.to_dict()
        plan.explanation = explanation.to_dict()
        _publish_event(
            "plan.rejected",
            payload={
                "plan_id": plan.plan_id,
                "reason": "no_template",
                "objective_title": objective.title,
            },
            actor_id=objective.requested_by,
        )
        _save_plan(plan)
        return plan

    validation = validate_plan(plan)

    if not validation.valid:
        plan.status = PlanStatus.REJECTED
        plan.validation_errors = validation.errors
        quality = _score_plan(plan, validation)
        explanation = _explain_plan(plan, validation, quality)
        plan.quality_score = quality.to_dict()
        plan.explanation = explanation.to_dict()
        _publish_event(
            "plan.rejected",
            payload={
                "plan_id": plan.plan_id,
                "errors": validation.errors,
                "objective_title": objective.title,
            },
            actor_id=objective.requested_by,
        )
        _save_plan(plan)
        return plan

    plan.status = PlanStatus.VALIDATED

    quality = _score_plan(plan, validation)
    explanation = _explain_plan(plan, validation, quality)
    plan.quality_score = quality.to_dict()
    plan.explanation = explanation.to_dict()

    _publish_event(
        "plan.created",
        payload={
            "plan_id": plan.plan_id,
            "source": plan.source.value,
            "step_count": len(plan.steps),
            "objective_title": objective.title,
        },
        actor_id=objective.requested_by,
    )
    _publish_event(
        "plan.validated",
        payload={
            "plan_id": plan.plan_id,
            "warnings": validation.warnings,
        },
        actor_id=objective.requested_by,
    )
    _publish_event(
        "plan.quality_scored",
        payload={
            "plan_id": plan.plan_id,
            "score": quality.score,
            "verdict": quality.verdict,
        },
        actor_id=objective.requested_by,
    )

    # Agent review (advisory — does not gate execution)
    try:
        from umh.agents.reviewer import ReviewerAgent

        reviewer = ReviewerAgent()
        review_input = {
            "plan": plan.to_dict(),
            "objective": plan.objective.title,
        }
        review_output = reviewer.run(review_input)
        plan.review = review_output.to_dict()
        plan.decision_trace.append(
            {
                "agent": "reviewer",
                "verdict": review_output.output.get("verdict", ""),
                "risk_level": review_output.output.get("risk_level", ""),
                "timestamp": review_output.timestamp,
            }
        )
        _publish_event(
            "agent.review_completed",
            payload={
                "plan_id": plan.plan_id,
                "verdict": review_output.output.get("verdict", ""),
                "risk_level": review_output.output.get("risk_level", ""),
                "issue_count": len(review_output.output.get("issues", [])),
            },
            actor_id=plan.objective.requested_by,
        )
    except Exception as exc:
        _log.warning("Reviewer agent failed: %s", exc)

    _save_plan(plan)
    return plan


def _try_template(objective: PlanObjective) -> ExecutionPlan | None:
    """Try to generate a plan from a registered template."""
    template_fn = get_template(objective.title)
    if template_fn is None:
        return None
    try:
        return template_fn(objective)
    except Exception as exc:
        _log.warning("Template '%s' failed: %s", objective.title, exc)
        return None


def _try_llm_plan(objective: PlanObjective) -> ExecutionPlan | None:
    """Attempt LLM-assisted plan generation. Treats output as untrusted."""
    try:
        from umh.execution.engine import lightweight_execute
    except ImportError:
        return None

    prompt = (
        f"Generate a JSON execution plan for the following objective.\n"
        f"Title: {objective.title}\n"
        f"Description: {objective.description}\n"
        f"Constraints: {', '.join(objective.constraints) if objective.constraints else 'none'}\n"
        f"Max steps: {objective.max_steps}\n"
        f"Available operations: classify_intent, extract_entities, summarize, "
        f"short_response, validation, shell_command, file_read, file_list, "
        f"file_stat, computer_screenshot.\n\n"
        f"Return ONLY a JSON object with:\n"
        f'{{"steps": [{{"name": "...", "operation": "...", "inputs": {{...}}, '
        f'"execution_class": "llm_call|side_effect|pure", "rationale": "..."}}]}}\n'
    )

    result = lightweight_execute(
        operation="plan_generation",
        prompt=prompt,
        system="You are a deterministic planner. Output only valid JSON.",
        max_tokens=1024,
    )

    if result.status.value != "succeeded":
        return None

    response_text = result.outputs.get("response", "")
    return _parse_llm_plan(response_text, objective)


def _parse_llm_plan(response: str, objective: PlanObjective) -> ExecutionPlan | None:
    """Parse LLM response into an ExecutionPlan. Returns None on failure."""
    try:
        start = response.find("{")
        end = response.rfind("}") + 1
        if start < 0 or end <= start:
            return None
        data = json.loads(response[start:end])
    except (json.JSONDecodeError, ValueError):
        return None

    raw_steps = data.get("steps", [])
    if not isinstance(raw_steps, list) or not raw_steps:
        return None

    steps = []
    for s in raw_steps:
        if not isinstance(s, dict):
            continue
        name = s.get("name", "")
        operation = s.get("operation", "")
        if not name or not operation:
            continue
        steps.append(
            ExecutionPlanStep(
                name=name,
                operation=operation,
                inputs=s.get("inputs", {}),
                execution_class=s.get("execution_class", "llm_call"),
                rationale=s.get("rationale", ""),
            )
        )

    if not steps:
        return None

    return ExecutionPlan(
        objective=objective,
        steps=steps,
        source=PlanSource.LLM,
        confidence=0.7,
        assumptions=["LLM-generated plan — treated as untrusted"],
    )


def plan_to_task(plan: ExecutionPlan):
    """Convert a validated ExecutionPlan to a Task for execution."""
    from umh.orchestrator.task import Task, TaskStep

    if plan.status != PlanStatus.VALIDATED:
        raise ValueError(f"Cannot convert plan with status '{plan.status.value}'")

    task_steps = []
    for step in plan.steps:
        task_steps.append(
            TaskStep(
                operation=step.operation,
                inputs_template=step.inputs,
                output_key=step.step_id,
                execution_class=step.execution_class,
            )
        )

    return Task(
        steps=task_steps,
        context={"plan_id": plan.plan_id, "objective_id": plan.objective.objective_id},
        issued_by=plan.objective.requested_by,
    )


def execute_plan(plan: ExecutionPlan, force: bool = False):
    """Execute a validated plan through the existing task system.

    Converts plan to task, runs execute_task, updates plan status.
    Returns the completed Task.

    Quality gate:
    - verdict=fail → blocked unless force=True (still blocked)
    - verdict=warn → allowed, warning included
    - verdict=pass → allowed
    """
    from umh.orchestrator.task import execute_task, TaskStatus

    if plan.status != PlanStatus.VALIDATED:
        raise ValueError(f"Cannot execute plan with status '{plan.status.value}'")

    if plan.quality_score:
        verdict = plan.quality_score.get("verdict", "pass")
        if verdict == QualityVerdict.FAIL:
            _publish_event(
                "plan.execution_blocked_quality",
                payload={
                    "plan_id": plan.plan_id,
                    "verdict": verdict,
                    "score": plan.quality_score.get("score", 0),
                },
                actor_id=plan.objective.requested_by,
            )
            raise ValueError(
                f"Plan quality verdict is 'fail' (score={plan.quality_score.get('score', 0)}) "
                f"— execution blocked"
            )

    if plan.objective.dry_run:
        _log.info("Dry run: plan %s not executed", plan.plan_id)
        return None

    task = plan_to_task(plan)
    plan.task_id = task.id
    plan.status = PlanStatus.EXECUTING

    _publish_event(
        "plan.executed",
        payload={
            "plan_id": plan.plan_id,
            "task_id": task.id,
            "step_count": len(plan.steps),
        },
        actor_id=plan.objective.requested_by,
    )

    result = execute_task(task)

    if result.status == TaskStatus.COMPLETED:
        plan.status = PlanStatus.COMPLETED
    elif result.status == TaskStatus.PAUSED:
        plan.status = PlanStatus.EXECUTING
    else:
        plan.status = PlanStatus.FAILED

        # Debug analysis (advisory)
        try:
            from umh.agents.debugger import DebugAgent

            debugger = DebugAgent()
            debug_input = {
                "task": result.to_dict(),
                "error": result.error or "",
                "plan": plan.to_dict(),
            }
            debug_output = debugger.run(debug_input)
            plan.debug_analysis = debug_output.to_dict()
            plan.decision_trace.append(
                {
                    "agent": "debugger",
                    "root_cause": debug_output.output.get("root_cause", ""),
                    "retryable": debug_output.output.get("retryable", False),
                    "timestamp": debug_output.timestamp,
                }
            )
            _publish_event(
                "agent.debug_completed",
                payload={
                    "plan_id": plan.plan_id,
                    "task_id": task.id,
                    "root_cause": debug_output.output.get("root_cause", ""),
                    "failure_category": debug_output.output.get("failure_category", ""),
                    "retryable": debug_output.output.get("retryable", False),
                },
                actor_id=plan.objective.requested_by,
            )
        except Exception as exc:
            _log.warning("Debug agent failed: %s", exc)

    _save_plan(plan)
    return result


# ── Plan Store ─────────────────────────────────────────────────────

_plans: dict[str, ExecutionPlan] = {}
_plans_lock = threading.Lock()


def _save_plan(plan: ExecutionPlan) -> None:
    with _plans_lock:
        _plans[plan.plan_id] = plan


def get_plan(plan_id: str) -> ExecutionPlan | None:
    with _plans_lock:
        return _plans.get(plan_id)


def list_plans() -> list[ExecutionPlan]:
    with _plans_lock:
        return list(_plans.values())


def reset_plans() -> None:
    with _plans_lock:
        _plans.clear()
