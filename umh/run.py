"""UMH Run — the single entry point for the Universal Meta Harness.

    from umh.run import run
    result = run("What should I focus on today?")
    print(result.response)

The run loop executes 9 stages in sequence:
  1. Signal   — ingest and classify raw input
  2. Intent   — compile structured intent from signals
  3. World    — read/update the world model
  4. Decision — select objective and strategy
  5. Compose  — select or synthesize an execution template
  6. Route    — match to the best available capability
  7. Govern   — authority and safety check
  8. Execute  — dispatch through capability backend
  9. Feedback — record outcome and emit learning signal

Every stage is observable via RunResult.trace.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from umh.core.clock import now_ms as _now_ms

from umh.capability.registry import get_registry
from umh.capability.router import route_to_capability
from umh.context.builder import ContextBuilder
from umh.context.types import ContextPriority, ContextSection
from umh.decision.trace import DecisionTrace
from umh.feedback.loop import OutcomeType, record_outcome
from umh.goals.state import GoalRegistry, GoalState
from umh.governance.authority import AuthorityLevel, check_governance
from umh.intent.compiler import compile_intent
from umh.memory.storage import get_storage
from umh.signal.ingest import classify_input
from umh.signal.types import SignalBundle
from umh.world.model import WorldModel


@dataclass
class RunTrace:
    """Full observability trace of a single run."""

    run_id: str
    started_at: str
    completed_at: str = ""
    total_ms: int = 0
    stages: dict[str, dict[str, Any]] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "run_id": self.run_id,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
            "total_ms": self.total_ms,
            "stages": self.stages,
        }


@dataclass
class RunResult:
    """Result of a single umh.run() invocation."""

    run_id: str
    response: str
    success: bool
    operation: str
    capability_used: str
    trace: RunTrace
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "run_id": self.run_id,
            "response": self.response,
            "success": self.success,
            "operation": self.operation,
            "capability_used": self.capability_used,
            "trace": self.trace.to_dict(),
            "metadata": self.metadata,
        }


def run(
    input_text: str,
    *,
    source: str = "user",
    org_id: str = "default",
    authority: AuthorityLevel = AuthorityLevel.ANALYZE,
    goal: GoalState | None = None,
    constraints: dict[str, Any] | None = None,
    workstation_context: dict[str, Any] | None = None,
) -> RunResult:
    """Execute the full UMH run loop.

    Args:
        input_text: Raw input string to process.
        source: Where the input came from (user, system, cron, etc.).
        org_id: Organization context for world model isolation.
        authority: Maximum authority level for this run.
        goal: Optional active goal to condition the run.
        constraints: Optional constraints (budget, timeout, etc.).
        workstation_context: Optional Phase 77 workstation state (advisory only).

    Returns:
        RunResult with response, trace, and metadata.
    """
    run_id = f"run_{uuid.uuid4().hex[:12]}"
    trace = RunTrace(
        run_id=run_id,
        started_at=datetime.now(timezone.utc).isoformat(),
    )
    start_ms = _now_ms()
    constraints = constraints or {}

    # ── Stage 1: Signal ─────────────────────────────────────────────
    stage_start = _now_ms()
    bundle = classify_input(input_text, source=source)
    trace.stages["signal"] = {
        "elapsed_ms": _now_ms() - stage_start,
        "signal_count": len(bundle.signals),
        "highest_tier": bundle.highest_tier.name if bundle.highest_tier else None,
    }

    # ── Stage 2: Intent ─────────────────────────────────────────────
    stage_start = _now_ms()
    intent = compile_intent(bundle)
    trace.stages["intent"] = {
        "elapsed_ms": _now_ms() - stage_start,
        "intent_type": intent.intent_type,
        "operation": intent.operation,
        "confidence": round(intent.confidence, 4),
    }

    # ── Stage 3: World Model ────────────────────────────────────────
    stage_start = _now_ms()
    world = WorldModel(org_id=org_id)
    world_context = world.get_context_for_prompt(input_text[:100])
    trace.stages["world"] = {
        "elapsed_ms": _now_ms() - stage_start,
        "context_length": len(world_context),
        "org_id": org_id,
    }

    # ── Stage 4: Decision ───────────────────────────────────────────
    stage_start = _now_ms()
    registry = GoalRegistry()
    if goal is not None:
        registry.add_goal(goal)
        registry.set_active_goal(goal.goal_id)
    active_goal = registry.get_active_goal()

    intelligence_enrichment: dict[str, Any] = {}
    try:
        from umh.runtime.enrichment import enrich_decision

        intelligence_enrichment = enrich_decision(
            operation=intent.operation,
            intent_confidence=intent.confidence,
            goal_active=active_goal.active,
            goal_priority=active_goal.priority,
        )
    except Exception:
        pass

    trace.stages["decision"] = {
        "elapsed_ms": _now_ms() - stage_start,
        "active_goal": active_goal.goal_id if active_goal.active else None,
        "goal_priority": active_goal.priority,
        **intelligence_enrichment,
    }

    # ── Stage 5: Route ──────────────────────────────────────────────
    stage_start = _now_ms()
    routing = route_to_capability(intent.operation, constraints)
    capability_name = routing.selected.name if routing.selected else "null_llm"
    uses_llm = routing.selected is not None and routing.selected.capability_type == "llm"
    trace.stages["route"] = {
        "elapsed_ms": _now_ms() - stage_start,
        **routing.to_dict(),
    }

    # ── Stage 6: Compose ────────────────────────────────────────────
    stage_start = _now_ms()
    prompt, system_prompt = _compose_prompt(
        input_text, intent, world_context, active_goal, uses_llm
    )
    trace.stages["compose"] = {
        "elapsed_ms": _now_ms() - stage_start,
        "prompt_length": len(prompt),
        "has_system_prompt": bool(system_prompt),
        "target": "llm" if uses_llm else "runtime",
    }

    # ── Stage 7: Govern ─────────────────────────────────────────────
    stage_start = _now_ms()
    gov_decision = check_governance(
        operation=intent.operation,
        authority_level=authority,
        constraints=constraints,
    )
    trace.stages["govern"] = {
        "elapsed_ms": _now_ms() - stage_start,
        **gov_decision.to_dict(),
    }

    if not gov_decision.allowed:
        trace.completed_at = datetime.now(timezone.utc).isoformat()
        trace.total_ms = _now_ms() - start_ms
        denied_metadata: dict[str, Any] = {"blocked_by": "governance"}
        _attach_phase78_feedback(
            trace,
            denied_metadata,
            governance_denied=True,
            workstation_context=workstation_context,
        )
        return RunResult(
            run_id=run_id,
            response=f"Blocked by governance: {gov_decision.reason}",
            success=False,
            operation=intent.operation,
            capability_used="none",
            trace=trace,
            metadata=denied_metadata,
        )

    # ── Stage 8: Execute ────────────────────────────────────────────
    from umh.execution.engine import dispatch_prompt

    stage_start = _now_ms()
    response, exec_success, exec_error = dispatch_prompt(
        capability_name, intent.operation, prompt, system_prompt, constraints
    )
    exec_ms = _now_ms() - stage_start
    trace.stages["execute"] = {
        "elapsed_ms": exec_ms,
        "capability": capability_name,
        "success": exec_success,
        "error": exec_error,
    }

    # ── Stage 9: Feedback ───────────────────────────────────────────
    stage_start = _now_ms()
    outcome = OutcomeType.SUCCESS if exec_success else OutcomeType.FAILURE
    fb_event = record_outcome(
        operation=intent.operation,
        outcome=outcome,
        capability_name=capability_name,
        latency_ms=exec_ms,
        outputs={"response_length": len(response)},
        error=exec_error,
    )

    if exec_success:
        world.update_from_interaction(input_text, response, outcome="good")

    trace.stages["feedback"] = {
        "elapsed_ms": _now_ms() - stage_start,
        "event_id": fb_event.event_id,
        "outcome": outcome,
    }

    trace.completed_at = datetime.now(timezone.utc).isoformat()
    trace.total_ms = _now_ms() - start_ms

    run_metadata: dict[str, Any] = {
        "intent": intent.to_dict(),
        "governance": gov_decision.to_dict(),
    }
    if workstation_context:
        run_metadata["workstation"] = {
            "active_mode": workstation_context.get("active_mode", ""),
            "active_session_id": workstation_context.get("active_session_id", ""),
            "execution_preference": workstation_context.get("execution_preference", {}),
        }

    _attach_phase78_feedback(
        trace,
        run_metadata,
        workstation_context=workstation_context,
    )

    return RunResult(
        run_id=run_id,
        response=response,
        success=exec_success,
        operation=intent.operation,
        capability_used=capability_name,
        trace=trace,
        metadata=run_metadata,
    )


def _attach_phase78_feedback(
    trace: RunTrace,
    metadata: dict[str, Any],
    *,
    governance_denied: bool = False,
    workstation_context: dict[str, Any] | None = None,
) -> None:
    """Post-execution observer: run Phase 78 feedback loop on trace data.

    Attaches feedback summary to metadata. Failures here never
    propagate — execution result remains source of truth.
    """
    try:
        from umh.feedback.feedback_loop import process_trace_feedback
        from umh.feedback.store import get_feedback_store

        trace_dict: dict[str, Any] = {
            "trace_id": trace.run_id,
            "status": "completed",
            "result": trace.stages.get("execute", {}),
            "error": trace.stages.get("execute", {}).get("error"),
            "created_at": trace.started_at,
            "completed_at": trace.completed_at,
            "events": [],
            "metadata": metadata,
        }

        if governance_denied:
            gov_stage = trace.stages.get("govern", {})
            trace_dict["status"] = "denied"
            trace_dict["events"].append(
                {
                    "event_type": "governance",
                    "payload": {"allowed": False, "outcome": "deny", **gov_stage},
                    "timestamp": trace.completed_at,
                }
            )
        else:
            exec_stage = trace.stages.get("execute", {})
            if exec_stage.get("success") is False:
                trace_dict["status"] = "failed"
                trace_dict["error"] = exec_stage.get("error", "")

        if workstation_context:
            trace_dict.setdefault("metadata", {})["workstation"] = workstation_context

        store = get_feedback_store()
        loop_result = process_trace_feedback(trace_dict, store=store)

        if loop_result.outcome:
            metadata["phase78_feedback"] = {
                "outcome_status": loop_result.outcome.status.value,
                "outcome_id": loop_result.outcome.outcome_id,
                "feedback_id": (loop_result.feedback.feedback_id if loop_result.feedback else None),
                "memory_candidate_id": (
                    loop_result.memory_candidate.candidate_id
                    if loop_result.memory_candidate
                    else None
                ),
            }
    except Exception:
        pass


def _compose_prompt(
    input_text: str,
    intent: Any,
    world_context: str,
    goal: GoalState,
    uses_llm: bool,
) -> tuple[str, str]:
    """Build execution prompt from context layers.

    Uses ContextBuilder for fault-isolated, priority-aware assembly.
    Falls back to inline composition if the builder fails entirely.

    Returns (prompt, system_prompt).
    """
    try:
        return _compose_via_builder(input_text, intent, world_context, goal, uses_llm)
    except Exception:
        return _compose_fallback(input_text, intent, world_context, goal, uses_llm)


def _compose_via_builder(
    input_text: str,
    intent: Any,
    world_context: str,
    goal: GoalState,
    uses_llm: bool,
) -> tuple[str, str]:
    """Context composition via the ContextBuilder."""
    builder = ContextBuilder()

    if goal.active:
        builder.add_section(
            ContextSection(
                name="objective",
                content=f"Your objective: {goal.description}",
                priority=ContextPriority.CRITICAL,
                source="goal",
            )
        )

    if world_context:
        builder.add_section(
            ContextSection(
                name="world",
                content=f"Context:\n{world_context}",
                priority=ContextPriority.HIGH,
                source="world_model",
            )
        )

    builder.add_section(
        ContextSection(
            name="task",
            content=f"Task type: {intent.intent_type} ({intent.operation})",
            priority=ContextPriority.STANDARD,
            source="intent",
        )
    )

    if intent.constraints:
        constraint_str = ", ".join(f"{k}={v}" for k, v in intent.constraints.items())
        builder.add_section(
            ContextSection(
                name="constraints",
                content=f"Constraints: {constraint_str}",
                priority=ContextPriority.STANDARD,
                source="intent",
            )
        )

    if uses_llm:
        result = builder.build(user_prompt=input_text)
        return (result.user_prompt, result.system_prompt)

    result = builder.build(user_prompt=input_text)
    flat_parts = []
    if goal.active:
        flat_parts.append(f"[Objective: {goal.description}]")
    if world_context:
        flat_parts.append(world_context)
    flat_parts.append(f"[Intent: {intent.intent_type} → {intent.operation}]")
    flat_parts.append(input_text)
    return ("\n\n".join(flat_parts), "")


def _compose_fallback(
    input_text: str,
    intent: Any,
    world_context: str,
    goal: GoalState,
    uses_llm: bool,
) -> tuple[str, str]:
    """Inline fallback if ContextBuilder fails entirely."""
    if uses_llm:
        system_parts = []
        if goal.active:
            system_parts.append(f"Your objective: {goal.description}")
        if world_context:
            system_parts.append(f"Context:\n{world_context}")
        system_parts.append(f"Task type: {intent.intent_type} ({intent.operation})")
        if intent.constraints:
            constraint_str = ", ".join(f"{k}={v}" for k, v in intent.constraints.items())
            system_parts.append(f"Constraints: {constraint_str}")
        return (input_text, "\n\n".join(system_parts))

    parts = []
    if goal.active:
        parts.append(f"[Objective: {goal.description}]")
    if world_context:
        parts.append(world_context)
    parts.append(f"[Intent: {intent.intent_type} → {intent.operation}]")
    parts.append(input_text)
    return ("\n\n".join(parts), "")
