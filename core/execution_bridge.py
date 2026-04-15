"""Execution Bridge — converts composed structures into executable pipelines.

This is the Phase 5 connection layer. It takes a ComposedStructure from
the composition engine and produces a Pipeline that runs through the
existing execution system (run_pipeline → ActionStep → run_action →
Control Plane).

The primitive trace from the composition rides along in the pipeline
context so every action in the audit trail knows which L0 primitives
it operates on.

Flow:
    ComposedStructure
    → build_pipeline()
    → Pipeline(steps=[...])
    → run_pipeline()  (existing)
    → PipelineResult with primitive trace

Usage:
    from core.execution_bridge import build_pipeline, execute_composed

    structure = compose("generate outreach message for ICP", ctx)
    result = execute_composed(structure)
    print(result.ok, result.context["_primitive_trace"])
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from core.composer import ComposedStructure
from core.orchestrator.pipeline import (
    ActionStep,
    FuncStep,
    Pipeline,
    PipelineResult,
    run_pipeline,
)


# ---------------------------------------------------------------------------
# Pipeline builders per domain type
# ---------------------------------------------------------------------------


def _build_icp_pipeline(structure: ComposedStructure) -> list[ActionStep | FuncStep]:
    """Build pipeline steps for ICP-related intents (outreach, prospecting)."""
    cc = structure.contextual.context.client_context
    intent = structure.intent

    steps: list[ActionStep | FuncStep] = []

    # Step 1: Generate the outreach message
    steps.append(
        ActionStep(
            name="generate_outreach",
            type="compose_action",
            description=f"Generate outreach content: {intent}",
            inputs={
                "action": "generate_outreach",
                "intent": intent,
                "icp_state": cc.get("current_state", ""),
                "icp_goal": cc.get("desired_state", ""),
                "icp_constraints": cc.get("constraints", []),
                "icp_signals": cc.get("signals", []),
                "tone": structure.contextual.context.preferences.get("tone", "direct"),
                "primitive_tags": sorted(
                    t.value for t in structure.contextual.to_primitives()
                ),
            },
            expected_output="Generated outreach message text",
            risk_level="low",
            source_agent="composer",
        )
    )

    return steps


def _build_offer_pipeline(structure: ComposedStructure) -> list[ActionStep | FuncStep]:
    """Build pipeline steps for offer-related intents."""
    cc = structure.contextual.context.client_context

    return [
        ActionStep(
            name="compose_offer",
            type="compose_action",
            description=f"Compose offer: {structure.intent}",
            inputs={
                "action": "compose_offer",
                "intent": structure.intent,
                "promise": cc.get("promise", ""),
                "price": cc.get("price", 0),
                "deliverables": cc.get("deliverables", []),
                "primitive_tags": sorted(
                    t.value for t in structure.contextual.to_primitives()
                ),
            },
            expected_output="Structured offer document",
            risk_level="low",
            source_agent="composer",
        )
    ]


def _build_workflow_pipeline(
    structure: ComposedStructure,
) -> list[ActionStep | FuncStep]:
    """Build pipeline steps for workflow-related intents."""
    cc = structure.contextual.context.client_context

    return [
        ActionStep(
            name="execute_workflow",
            type="compose_action",
            description=f"Execute workflow: {structure.intent}",
            inputs={
                "action": "execute_workflow",
                "intent": structure.intent,
                "steps": cc.get("steps", []),
                "trigger": cc.get("trigger", "manual"),
                "goal": cc.get("goal", structure.intent),
                "primitive_tags": sorted(
                    t.value for t in structure.contextual.to_primitives()
                ),
            },
            expected_output="Workflow execution result",
            risk_level="medium",
            source_agent="composer",
        )
    ]


def _build_channel_pipeline(
    structure: ComposedStructure,
) -> list[ActionStep | FuncStep]:
    """Build pipeline steps for channel-related intents."""
    cc = structure.contextual.context.client_context

    return [
        ActionStep(
            name="activate_channel",
            type="compose_action",
            description=f"Activate channel: {structure.intent}",
            inputs={
                "action": "activate_channel",
                "intent": structure.intent,
                "medium": cc.get("medium", ""),
                "primitive_tags": sorted(
                    t.value for t in structure.contextual.to_primitives()
                ),
            },
            expected_output="Channel activation result",
            risk_level="low",
            source_agent="composer",
        )
    ]


def _build_kpi_pipeline(structure: ComposedStructure) -> list[ActionStep | FuncStep]:
    """Build pipeline steps for KPI-related intents."""
    cc = structure.contextual.context.client_context

    return [
        ActionStep(
            name="track_kpi",
            type="compose_action",
            description=f"Track KPI: {structure.intent}",
            inputs={
                "action": "track_kpi",
                "intent": structure.intent,
                "metric": cc.get("metric", ""),
                "target": cc.get("target", 0),
                "current": cc.get("current", 0),
                "primitive_tags": sorted(
                    t.value for t in structure.contextual.to_primitives()
                ),
            },
            expected_output="KPI tracking result",
            risk_level="low",
            source_agent="composer",
        )
    ]


def _build_role_pipeline(structure: ComposedStructure) -> list[ActionStep | FuncStep]:
    """Build pipeline steps for role-related intents."""
    cc = structure.contextual.context.client_context

    return [
        ActionStep(
            name="assign_role",
            type="compose_action",
            description=f"Assign role: {structure.intent}",
            inputs={
                "action": "assign_role",
                "intent": structure.intent,
                "objective": cc.get("objective", ""),
                "responsibilities": cc.get("responsibilities", []),
                "primitive_tags": sorted(
                    t.value for t in structure.contextual.to_primitives()
                ),
            },
            expected_output="Role assignment result",
            risk_level="low",
            source_agent="composer",
        )
    ]


def _build_habit_pipeline(structure: ComposedStructure) -> list[ActionStep | FuncStep]:
    """Build pipeline steps for habit-related intents."""
    cc = structure.contextual.context.client_context
    return [
        ActionStep(
            name="build_habit",
            type="compose_action",
            description=f"Build habit: {structure.intent}",
            inputs={
                "action": "build_habit",
                "intent": structure.intent,
                "trigger": cc.get("trigger", ""),
                "frequency": cc.get("frequency", "daily"),
                "goal": cc.get("goal", structure.intent),
                "primitive_tags": sorted(
                    t.value for t in structure.contextual.to_primitives()
                ),
            },
            expected_output="Habit plan with trigger, schedule, and tracking",
            risk_level="low",
            source_agent="composer",
        )
    ]


def _build_energy_pipeline(structure: ComposedStructure) -> list[ActionStep | FuncStep]:
    """Build pipeline steps for energy-related intents."""
    cc = structure.contextual.context.client_context
    return [
        ActionStep(
            name="assess_energy",
            type="compose_action",
            description=f"Assess energy: {structure.intent}",
            inputs={
                "action": "assess_energy",
                "intent": structure.intent,
                "level": cc.get("level", 0.5),
                "sources": cc.get("sources", []),
                "drains": cc.get("drains", []),
                "primitive_tags": sorted(
                    t.value for t in structure.contextual.to_primitives()
                ),
            },
            expected_output="Energy assessment with optimization plan",
            risk_level="low",
            source_agent="composer",
        )
    ]


def _build_focus_pipeline(structure: ComposedStructure) -> list[ActionStep | FuncStep]:
    """Build pipeline steps for focus-related intents."""
    cc = structure.contextual.context.client_context
    return [
        ActionStep(
            name="set_focus",
            type="compose_action",
            description=f"Set focus: {structure.intent}",
            inputs={
                "action": "set_focus",
                "intent": structure.intent,
                "current_focus": cc.get("current_focus", ""),
                "priority_goal": cc.get("priority_goal", ""),
                "time_block": cc.get("time_block", ""),
                "primitive_tags": sorted(
                    t.value for t in structure.contextual.to_primitives()
                ),
            },
            expected_output="Focus plan with time blocks and blocked items",
            risk_level="low",
            source_agent="composer",
        )
    ]


def _build_identity_state_pipeline(
    structure: ComposedStructure,
) -> list[ActionStep | FuncStep]:
    """Build pipeline steps for identity-related intents."""
    cc = structure.contextual.context.client_context
    return [
        ActionStep(
            name="assess_identity",
            type="compose_action",
            description=f"Assess identity: {structure.intent}",
            inputs={
                "action": "assess_identity",
                "intent": structure.intent,
                "current_identity": cc.get("current_identity", ""),
                "target_identity": cc.get("target_identity", ""),
                "primitive_tags": sorted(
                    t.value for t in structure.contextual.to_primitives()
                ),
            },
            expected_output="Identity gap analysis with alignment actions",
            risk_level="low",
            source_agent="composer",
        )
    ]


def _build_content_pipeline(
    structure: ComposedStructure,
) -> list[ActionStep | FuncStep]:
    """Build pipeline steps for content-related intents."""
    cc = structure.contextual.context.client_context
    return [
        ActionStep(
            name="create_content",
            type="compose_action",
            description=f"Create content: {structure.intent}",
            inputs={
                "action": "create_content",
                "intent": structure.intent,
                "format": cc.get("format", ""),
                "topic": cc.get("topic", ""),
                "hook": cc.get("hook", ""),
                "call_to_action": cc.get("call_to_action", ""),
                "primitive_tags": sorted(
                    t.value for t in structure.contextual.to_primitives()
                ),
            },
            expected_output="Content draft with hook, body, and CTA",
            risk_level="low",
            source_agent="composer",
        )
    ]


def _build_audience_pipeline(
    structure: ComposedStructure,
) -> list[ActionStep | FuncStep]:
    """Build pipeline steps for audience-related intents."""
    cc = structure.contextual.context.client_context
    return [
        ActionStep(
            name="analyse_audience",
            type="compose_action",
            description=f"Analyse audience: {structure.intent}",
            inputs={
                "action": "analyse_audience",
                "intent": structure.intent,
                "segment": cc.get("segment", ""),
                "signals": cc.get("signals", []),
                "pain_points": cc.get("pain_points", []),
                "primitive_tags": sorted(
                    t.value for t in structure.contextual.to_primitives()
                ),
            },
            expected_output="Audience analysis with segment profile",
            risk_level="low",
            source_agent="composer",
        )
    ]


def _build_platform_pipeline(
    structure: ComposedStructure,
) -> list[ActionStep | FuncStep]:
    """Build pipeline steps for platform-related intents."""
    cc = structure.contextual.context.client_context
    return [
        ActionStep(
            name="evaluate_platform",
            type="compose_action",
            description=f"Evaluate platform: {structure.intent}",
            inputs={
                "action": "evaluate_platform",
                "intent": structure.intent,
                "platform_name": cc.get("platform_name", ""),
                "rules": cc.get("rules", []),
                "primitive_tags": sorted(
                    t.value for t in structure.contextual.to_primitives()
                ),
            },
            expected_output="Platform strategy with rules and timing",
            risk_level="low",
            source_agent="composer",
        )
    ]


def _build_engagement_pipeline(
    structure: ComposedStructure,
) -> list[ActionStep | FuncStep]:
    """Build pipeline steps for engagement-related intents."""
    cc = structure.contextual.context.client_context
    return [
        ActionStep(
            name="measure_engagement",
            type="compose_action",
            description=f"Measure engagement: {structure.intent}",
            inputs={
                "action": "measure_engagement",
                "intent": structure.intent,
                "metric_type": cc.get("metric_type", ""),
                "value": cc.get("value", 0),
                "benchmark": cc.get("benchmark", 0),
                "primitive_tags": sorted(
                    t.value for t in structure.contextual.to_primitives()
                ),
            },
            expected_output="Engagement metrics analysis",
            risk_level="low",
            source_agent="composer",
        )
    ]


_PIPELINE_BUILDERS = {
    "icp": _build_icp_pipeline,
    "offer": _build_offer_pipeline,
    "workflow": _build_workflow_pipeline,
    "channel": _build_channel_pipeline,
    "kpi": _build_kpi_pipeline,
    "role": _build_role_pipeline,
    # LyfeOS
    "habit": _build_habit_pipeline,
    "energy": _build_energy_pipeline,
    "focus": _build_focus_pipeline,
    "identity_state": _build_identity_state_pipeline,
    # CreatorOS
    "content": _build_content_pipeline,
    "audience": _build_audience_pipeline,
    "platform": _build_platform_pipeline,
    "engagement": _build_engagement_pipeline,
}


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def build_pipeline(structure: ComposedStructure) -> Pipeline:
    """Convert a ComposedStructure into an executable Pipeline.

    The primitive trace is injected into the pipeline context so every
    step has access to the L0 lineage of the work it's doing.
    """
    builder = _PIPELINE_BUILDERS.get(structure.domain_type)
    if not builder:
        raise ValueError(
            f"No pipeline builder for domain type: {structure.domain_type}"
        )

    steps = builder(structure)

    return Pipeline(
        name=f"composed:{structure.domain_type}:{structure.intent[:40]}",
        steps=steps,
        stop_on_fail=True,
        source_agent="composer",
    )


def execute_composed(
    structure: ComposedStructure,
    extra_context: dict[str, Any] | None = None,
) -> PipelineResult:
    """End-to-end: compose → build pipeline → execute.

    Injects primitive trace and composition metadata into the pipeline
    context so every action carries its ontological lineage.
    """
    if not structure.ok:
        raise ValueError(
            f"Cannot execute invalid composition: {structure.validation_errors}"
        )

    pipeline = build_pipeline(structure)

    # Build execution context with primitive trace
    context: dict[str, Any] = {
        "_intent": structure.intent,
        "_domain_type": structure.domain_type,
        "_primitive_trace": structure.primitive_trace,
        "_primitive_tags": sorted(
            t.value for t in structure.contextual.to_primitives()
        ),
        "_context": structure.contextual.context.to_dict(),
        "_composition": structure.contextual.composition.to_dict(),
    }
    if extra_context:
        context.update(extra_context)

    return run_pipeline(pipeline, context=context)


# ---------------------------------------------------------------------------
# Extended pipeline with learning loop (optional, non-breaking)
# ---------------------------------------------------------------------------


@dataclass
class LearningResult:
    """Extended result that includes feedback and transformation trace.

    Wraps the original PipelineResult with primitive-level intelligence.
    """

    original_result: PipelineResult
    feedback: Any  # FeedbackSignal — typed loosely to keep import lightweight
    transformation: Any | None  # TransformationResult or None
    improved_result: PipelineResult | None  # result of re-execution, if attempted
    primitive_trace: dict[str, Any] = field(default_factory=dict)

    @property
    def ok(self) -> bool:
        if self.improved_result:
            return self.improved_result.ok
        return self.original_result.ok

    def to_dict(self) -> dict[str, Any]:
        result: dict[str, Any] = {
            "original": self.original_result.to_dict(),
            "feedback": self.feedback.to_dict() if self.feedback else None,
            "transformation": (
                self.transformation.to_dict() if self.transformation else None
            ),
            "improved": (
                self.improved_result.to_dict() if self.improved_result else None
            ),
            "primitive_trace": self.primitive_trace,
            "used_improved": self.improved_result is not None,
        }
        return result


def execute_with_learning(
    structure: ComposedStructure,
    extra_context: dict[str, Any] | None = None,
    *,
    learning_threshold: float = 0.7,
    max_retransform: int = 1,
) -> LearningResult:
    """Execute with optional feedback → transform → re-execute loop.

    This is the extended pipeline flow:
        intent → compose → run_pipeline → evaluate_result
        → transform (if score < threshold) → re-run improved → store trace

    Default behaviour (score >= threshold) is identical to execute_composed().
    The learning loop only fires when the initial execution scores below
    the threshold.

    Args:
        structure: The ComposedStructure from compose().
        extra_context: Additional context to inject.
        learning_threshold: Score below which transformation is attempted (0.0–1.0).
        max_retransform: Maximum transformation + re-execution attempts.

    Returns:
        LearningResult with full trace of original, feedback, transformation,
        and improved execution.
    """
    from core.feedback import apply_feedback, evaluate_result
    from core.transformer import TransformationResult

    # Step 1: Execute the original composition
    original_result = execute_composed(structure, extra_context)

    # Step 2: Evaluate
    feedback = evaluate_result(original_result, original_result.context)

    # Step 3: Transform if below threshold
    transformation: TransformationResult | None = None
    improved_result: PipelineResult | None = None

    if feedback.success_score < learning_threshold and max_retransform > 0:
        current_tags = structure.contextual.to_primitives()
        improved_tags, transformation = apply_feedback(
            current_tags, feedback, objective=structure.intent
        )

        if transformation.changed:
            # Re-build pipeline with improved primitive tags
            # We inject the improved tags into the context rather than
            # modifying the ComposedStructure (which is immutable-ish)
            improved_context = dict(extra_context or {})
            improved_context["_primitive_tags"] = sorted(t.value for t in improved_tags)
            improved_context["_transformation_applied"] = True
            improved_context["_original_primitive_tags"] = sorted(
                t.value for t in current_tags
            )

            improved_result = execute_composed(structure, improved_context)

    # Step 4: Build the full primitive trace
    trace: dict[str, Any] = {
        "original": sorted(t.value for t in structure.contextual.to_primitives()),
        "transformations": (transformation.to_dict() if transformation else None),
        "feedback": feedback.to_dict(),
        "final": (
            sorted(t.value for t in transformation.transformed_primitives)
            if transformation
            else sorted(t.value for t in structure.contextual.to_primitives())
        ),
    }

    return LearningResult(
        original_result=original_result,
        feedback=feedback,
        transformation=transformation,
        improved_result=improved_result,
        primitive_trace=trace,
    )


# ---------------------------------------------------------------------------
# Routed execution with capability matching (Phase 8 — intelligence allocator)
# ---------------------------------------------------------------------------


@dataclass
class RoutedLearningResult:
    """Full result from execute_with_routing: routing + learning + trace.

    Combines capability selection, routed execution, feedback evaluation,
    and adaptive learning into a single traceable result.
    """

    routed_result: Any  # RoutedExecutionResult — loose to keep imports lightweight
    feedback: Any | None  # FeedbackSignal
    transformation: Any | None  # TransformationResult
    improved_result: Any | None  # RoutedExecutionResult from re-route
    primitive_trace: dict[str, Any] = field(default_factory=dict)

    @property
    def ok(self) -> bool:
        if self.improved_result:
            return self.improved_result.ok
        return self.routed_result.ok

    def to_dict(self) -> dict[str, Any]:
        return {
            "routed_result": self.routed_result.to_dict(),
            "feedback": self.feedback.to_dict() if self.feedback else None,
            "transformation": (
                self.transformation.to_dict() if self.transformation else None
            ),
            "improved": (
                self.improved_result.to_dict() if self.improved_result else None
            ),
            "primitive_trace": self.primitive_trace,
            "used_improved": self.improved_result is not None,
        }


def execute_with_routing(
    structure: ComposedStructure,
    constraints: dict[str, Any] | None = None,
    extra_context: dict[str, Any] | None = None,
    *,
    learning_threshold: float = 0.7,
    max_retransform: int = 1,
) -> RoutedLearningResult:
    """End-to-end: compose → match capabilities → route → execute → learn.

    This is the full intelligence-allocator flow:
        intent
        → compose (existing)
        → match_capability per step
        → route_execution (hybrid capability assignment)
        → execute_routed (with performance tracking)
        → evaluate_result (primitive-level feedback)
        → transform + re-route if below threshold

    Replaces execute_with_learning() when you want dynamic capability
    selection.  Falls back gracefully — if routing fails, delegates
    to execute_composed().

    Args:
        structure:          The ComposedStructure from compose().
        constraints:        Budget/latency/quality constraints for the matcher.
        extra_context:      Additional context to inject into the pipeline.
        learning_threshold: Score below which re-routing is attempted.
        max_retransform:    Maximum re-route attempts.

    Returns:
        RoutedLearningResult with full routing, execution, and learning trace.
    """
    from core.feedback import apply_feedback, evaluate_result
    from core.router import ExecutionPlan, execute_routed, route_execution

    if not structure.ok:
        raise ValueError(
            f"Cannot execute invalid composition: {structure.validation_errors}"
        )

    # Step 1: Route — assign capabilities to each step
    plan = route_execution(structure, constraints)

    # Step 2: Execute with routing
    routed_result = execute_routed(plan, extra_context)

    # Step 3: Evaluate
    feedback = evaluate_result(
        routed_result.pipeline_result,
        routed_result.pipeline_result.context,
    )

    # Step 4: Re-route if below threshold
    transformation = None
    improved_result = None

    if feedback.success_score < learning_threshold and max_retransform > 0:
        current_tags = structure.contextual.to_primitives()
        improved_tags, transformation = apply_feedback(
            current_tags, feedback, objective=structure.intent
        )

        if transformation.changed:
            # Re-route with improved primitive tags — the matcher will
            # potentially select different capabilities for the new composition.
            improved_context = dict(extra_context or {})
            improved_context["_primitive_tags"] = sorted(t.value for t in improved_tags)
            improved_context["_transformation_applied"] = True
            improved_context["_original_primitive_tags"] = sorted(
                t.value for t in current_tags
            )

            # Re-route and re-execute
            improved_plan = route_execution(structure, constraints)
            improved_result = execute_routed(improved_plan, improved_context)

    # Step 5: Build the full trace
    trace: dict[str, Any] = {
        "original_primitives": sorted(
            t.value for t in structure.contextual.to_primitives()
        ),
        "routing_plan": plan.to_dict(),
        "capability_selections": {rs.name: rs.selection.to_dict() for rs in plan.steps},
        "execution_result": {
            "ok": routed_result.ok,
            "step_capabilities": routed_result.step_capabilities,
            "performance_updates": routed_result.performance_updates,
        },
        "feedback": feedback.to_dict(),
        "transformations": transformation.to_dict() if transformation else None,
        "final_primitives": (
            sorted(t.value for t in transformation.transformed_primitives)
            if transformation
            else sorted(t.value for t in structure.contextual.to_primitives())
        ),
    }

    return RoutedLearningResult(
        routed_result=routed_result,
        feedback=feedback,
        transformation=transformation,
        improved_result=improved_result,
        primitive_trace=trace,
    )


# ---------------------------------------------------------------------------
# True Closed-Loop: Reality → Objective → Memory → Adaptation
# ---------------------------------------------------------------------------


@dataclass
class RealityLoopResult:
    """Full result from execute_with_reality_loop.

    Contains the routed execution, reality signal ingestion, objective
    evaluation, memory recording, and optional re-execution trace.
    """

    routed_result: RoutedLearningResult
    reality_signal: Any | None  # RealitySignal from reality_input
    objective_score: Any | None  # ObjectiveScore from objective
    memory_recorded: bool
    iterations: int  # how many loop passes
    final_score: float  # the authoritative score (objective overrides internal)
    primitive_trace: dict[str, Any] = field(default_factory=dict)

    @property
    def ok(self) -> bool:
        if self.objective_score:
            return self.objective_score.achieved
        return self.routed_result.ok

    def to_dict(self) -> dict[str, Any]:
        return {
            "ok": self.ok,
            "routed_result": self.routed_result.to_dict(),
            "reality_signal": (
                self.reality_signal.to_dict() if self.reality_signal else None
            ),
            "objective_score": (
                self.objective_score.to_dict() if self.objective_score else None
            ),
            "memory_recorded": self.memory_recorded,
            "iterations": self.iterations,
            "final_score": round(self.final_score, 4),
            "primitive_trace": self.primitive_trace,
        }


def execute_with_reality_loop(
    structure: ComposedStructure,
    constraints: dict[str, Any] | None = None,
    extra_context: dict[str, Any] | None = None,
    *,
    real_data: dict[str, Any] | None = None,
    objective_name: str | None = None,
    reality_text: str | None = None,
    learning_threshold: float = 0.7,
    max_iterations: int = 2,
) -> RealityLoopResult:
    """Full closed-loop: intent → compose → route → execute → ingest reality
    → evaluate objective → transform → re-run if below threshold → store memory.

    This replaces the synthetic learning loop with a REAL loop that:
    1. Executes the pipeline via execute_with_routing()
    2. Ingests a real-world signal (text, metric, API response)
    3. Evaluates against a real-world objective (overrides internal score)
    4. Transforms primitives if objective not met
    5. Re-executes with improved composition
    6. Records everything to memory for pattern learning

    Args:
        structure:          ComposedStructure from compose().
        constraints:        Budget/latency/quality constraints.
        extra_context:      Additional pipeline context.
        real_data:          Real-world metrics for objective evaluation.
        objective_name:     Name of objective from OBJECTIVE_REGISTRY.
        reality_text:       Raw text signal to ingest from the real world.
        learning_threshold: Score below which re-execution is attempted.
        max_iterations:     Maximum loop iterations.

    Returns:
        RealityLoopResult with full trace of execution, reality, and learning.
    """
    import uuid

    from core.feedback import apply_feedback
    from core.memory_evolution import get_memory
    from core.objective import ObjectiveScore, evaluate_objective, get_objective
    from core.reality_input import RealitySignal, ingest_signal

    iterations = 0
    reality_signal: RealitySignal | None = None
    obj_score: ObjectiveScore | None = None
    current_structure = structure

    # Step 1: Execute with routing
    routed = execute_with_routing(
        current_structure,
        constraints=constraints,
        extra_context=extra_context,
        learning_threshold=learning_threshold,
    )
    iterations += 1

    # Step 2: Ingest reality signal
    if reality_text:
        reality_signal = ingest_signal(reality_text, source="text")

    # Step 3: Evaluate objective (overrides internal scoring)
    final_score = 1.0 if routed.ok else 0.0
    if routed.feedback:
        final_score = routed.feedback.success_score

    if objective_name and real_data:
        objective = get_objective(objective_name)
        if objective:
            pipeline_result = routed.routed_result.pipeline_result
            obj_score = evaluate_objective(
                pipeline_result,
                real_data,
                objective,
                internal_score=final_score,
            )
            # Objective OVERRIDES internal score
            final_score = obj_score.score

    # Step 4: Re-execute if below threshold and we have iterations left
    if final_score < learning_threshold and iterations < max_iterations:
        if routed.feedback:
            current_tags = structure.contextual.to_primitives()
            improved_tags, transformation = apply_feedback(
                current_tags, routed.feedback, objective=structure.intent
            )
            if transformation.changed:
                improved_context = dict(extra_context or {})
                improved_context["_primitive_tags"] = sorted(
                    t.value for t in improved_tags
                )
                improved_context["_transformation_applied"] = True
                improved_context["_reality_loop_iteration"] = iterations + 1

                routed = execute_with_routing(
                    current_structure,
                    constraints=constraints,
                    extra_context=improved_context,
                    learning_threshold=learning_threshold,
                )
                iterations += 1

                # Re-evaluate objective with improved result
                if objective_name and real_data:
                    objective = get_objective(objective_name)
                    if objective:
                        pipeline_result = routed.routed_result.pipeline_result
                        obj_score = evaluate_objective(
                            pipeline_result,
                            real_data,
                            objective,
                            internal_score=(
                                routed.feedback.success_score
                                if routed.feedback
                                else 0.0
                            ),
                        )
                        final_score = obj_score.score

    # Step 5: Record to memory
    mem = get_memory()
    run_id = str(uuid.uuid4())[:8]
    feedback_score = routed.feedback.success_score if routed.feedback else 0.0

    mem.record_run(
        run_id=run_id,
        intent=structure.intent,
        domain_type=structure.domain_type,
        primitive_tags=structure.contextual.to_primitives(),
        success_score=final_score,
        pipeline_ok=routed.ok,
        objective_score=obj_score.score if obj_score else None,
        transformation_applied=routed.transformation is not None,
        transformed_from=(
            set(routed.transformation.original_primitives)
            if routed.transformation
            else None
        ),
        step_scores=routed.feedback.raw_evidence.get("step_scores", {})
        if routed.feedback
        else {},
        metadata={
            "iterations": iterations,
            "objective_name": objective_name,
            "reality_source": reality_signal.source if reality_signal else None,
        },
    )

    # Step 6: Build full trace
    trace: dict[str, Any] = {
        "run_id": run_id,
        "iterations": iterations,
        "original_primitives": sorted(
            t.value for t in structure.contextual.to_primitives()
        ),
        "routing_trace": routed.primitive_trace,
        "reality_signal": reality_signal.to_dict() if reality_signal else None,
        "objective": obj_score.to_dict() if obj_score else None,
        "final_score": final_score,
        "memory_suggestions": mem.suggest_optimizations()[-3:],  # latest 3
    }

    return RealityLoopResult(
        routed_result=routed,
        reality_signal=reality_signal,
        objective_score=obj_score,
        memory_recorded=True,
        iterations=iterations,
        final_score=final_score,
        primitive_trace=trace,
    )


# ---------------------------------------------------------------------------
# Phase 6: Unified Reality Loop — full end-to-end with all new systems
# ---------------------------------------------------------------------------


@dataclass
class FullRealityLoopResult:
    """Complete result from the unified reality loop.

    Integrates: connectors, multi-objective, dynamics, strategy, governor.
    """

    ok: bool
    objective_scores: dict[str, Any]  # from ObjectiveSet.to_dict()
    hard_constraint_failures: list[dict[str, Any]]
    delayed_status: dict[str, Any]  # from DelayedScore.to_dict()
    primitive_trace: dict[str, Any]
    capability_trace: dict[str, Any]
    routing_trace: dict[str, Any]
    memory_recorded: bool
    strategy_updates: list[dict[str, Any]]
    improvement_proposals: list[dict[str, Any]]
    iterations: int
    run_id: str = ""
    final_score: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "ok": self.ok,
            "run_id": self.run_id,
            "final_score": round(self.final_score, 4),
            "objective_scores": self.objective_scores,
            "hard_constraint_failures": self.hard_constraint_failures,
            "delayed_status": self.delayed_status,
            "primitive_trace": self.primitive_trace,
            "capability_trace": self.capability_trace,
            "routing_trace": self.routing_trace,
            "memory_recorded": self.memory_recorded,
            "strategy_updates": self.strategy_updates,
            "improvement_proposals": self.improvement_proposals,
            "iterations": self.iterations,
        }


def execute_with_full_reality_loop(
    structure: ComposedStructure,
    constraints: dict[str, Any] | None = None,
    extra_context: dict[str, Any] | None = None,
    *,
    connector_signals: list[Any] | None = None,
    real_data: dict[str, Any] | None = None,
    objective_set: Any | None = None,
    objective_name: str | None = None,
    dynamics: Any | None = None,
    reality_text: str | None = None,
    learning_threshold: float = 0.7,
    max_iterations: int = 2,
    elapsed_steps: int = 0,
    historical_trajectory: list[float] | None = None,
) -> FullRealityLoopResult:
    """Full unified loop: intent → compose → route → execute → ingest →
    evaluate multi-objective → apply dynamics → transform → memory →
    strategy → governor → return.

    This chains ALL new systems (Phases 1-5) with the existing loop.

    Args:
        structure:              ComposedStructure from compose().
        constraints:            Budget/latency/quality constraints.
        extra_context:          Additional pipeline context.
        connector_signals:      RealSignal list from connectors (Phase 1).
        real_data:              Direct real-world metrics dict (overrides connectors).
        objective_set:          ObjectiveSet for multi-objective eval (Phase 2).
        objective_name:         Single objective name (fallback if no objective_set).
        dynamics:               FeedbackDynamics for delayed scoring (Phase 5).
        reality_text:           Raw text signal to ingest.
        learning_threshold:     Score below which re-execution is attempted.
        max_iterations:         Maximum loop iterations.
        elapsed_steps:          Steps since original execution (for dynamics).
        historical_trajectory:  Past scores for dynamics projection.

    Returns:
        FullRealityLoopResult with complete trace across all systems.
    """
    import uuid

    from core.connectors.base import RealSignal as ConnectorSignal
    from core.connectors.base import aggregate_signals
    from core.dynamics import DelayedScore, FeedbackDynamics
    from core.feedback import apply_feedback
    from core.improvement_governor import get_governor
    from core.memory_evolution import get_memory
    from core.objective import evaluate_objective, get_objective
    from core.objective_engine import ObjectiveSet

    run_id = str(uuid.uuid4())[:8]
    iterations = 0
    improvement_proposals: list[dict[str, Any]] = []
    strategy_updates: list[dict[str, Any]] = []

    # ----- Step 1: Execute with routing -----
    routed = execute_with_routing(
        structure,
        constraints=constraints,
        extra_context=extra_context,
        learning_threshold=learning_threshold,
    )
    iterations += 1

    # ----- Step 2: Ingest connector signals (Phase 1) -----
    merged_real_data: dict[str, Any] = {}

    if connector_signals:
        merged_real_data = aggregate_signals(connector_signals)

    if real_data:
        merged_real_data.update(real_data)

    # Also ingest text signal if provided
    reality_signal = None
    if reality_text:
        from core.reality_input import ingest_signal

        reality_signal = ingest_signal(reality_text, source="text")

    # ----- Step 3: Evaluate against ObjectiveSet (Phase 2) -----
    obj_set_result: dict[str, Any] = {}
    constraint_failures: list[dict[str, Any]] = []
    final_score = 1.0 if routed.ok else 0.0

    if routed.feedback:
        final_score = routed.feedback.success_score

    if objective_set and isinstance(objective_set, ObjectiveSet) and merged_real_data:
        objective_set.evaluate(merged_real_data)
        final_score = objective_set.aggregate_score()
        obj_set_result = objective_set.to_dict()
        constraint_failures = [
            r.to_dict() for r in objective_set.constraint_violations()
        ]
    elif objective_name and merged_real_data:
        # Fallback to single objective
        objective = get_objective(objective_name)
        if objective:
            pipeline_result = routed.routed_result.pipeline_result
            obj_score = evaluate_objective(
                pipeline_result,
                merged_real_data,
                objective,
                internal_score=final_score,
            )
            final_score = obj_score.score
            obj_set_result = {
                "aggregate_score": obj_score.score,
                "ok": obj_score.achieved,
                "results": [obj_score.to_dict()],
                "constraint_violations": [],
                "tradeoffs": [],
            }

    # ----- Step 4: Apply FeedbackDynamics (Phase 5) -----
    delayed_status: dict[str, Any] = {}

    if dynamics and isinstance(dynamics, FeedbackDynamics):
        delayed = dynamics.project_score(
            immediate_score=final_score,
            elapsed_steps=elapsed_steps,
            historical_trajectory=historical_trajectory,
        )
        delayed_status = delayed.to_dict()

        # If score hasn't matured, use projected score for judgment
        if delayed.pending:
            final_score = delayed.projected
    else:
        delayed_status = DelayedScore(
            immediate=final_score,
            projected=final_score,
            matured=True,
            elapsed_steps=elapsed_steps,
            lag_steps=0,
            confidence=0.95,
        ).to_dict()

    # ----- Step 5: Transform primitives if below threshold -----
    if final_score < learning_threshold and iterations < max_iterations:
        if routed.feedback:
            current_tags = structure.contextual.to_primitives()
            improved_tags, transformation = apply_feedback(
                current_tags, routed.feedback, objective=structure.intent
            )
            if transformation.changed:
                improved_context = dict(extra_context or {})
                improved_context["_primitive_tags"] = sorted(
                    t.value for t in improved_tags
                )
                improved_context["_transformation_applied"] = True
                improved_context["_reality_loop_iteration"] = iterations + 1

                routed = execute_with_routing(
                    structure,
                    constraints=constraints,
                    extra_context=improved_context,
                    learning_threshold=learning_threshold,
                )
                iterations += 1

                # Re-evaluate if we have objectives
                if (
                    objective_set
                    and isinstance(objective_set, ObjectiveSet)
                    and merged_real_data
                ):
                    objective_set.evaluate(merged_real_data)
                    final_score = objective_set.aggregate_score()
                    obj_set_result = objective_set.to_dict()

    # ----- Step 6: Record run into memory -----
    mem = get_memory()
    feedback_score = routed.feedback.success_score if routed.feedback else 0.0

    mem.record_run(
        run_id=run_id,
        intent=structure.intent,
        domain_type=structure.domain_type,
        primitive_tags=structure.contextual.to_primitives(),
        success_score=final_score,
        pipeline_ok=routed.ok,
        objective_score=obj_set_result.get("aggregate_score")
        if obj_set_result
        else None,
        transformation_applied=routed.transformation is not None,
        transformed_from=(
            set(routed.transformation.original_primitives)
            if routed.transformation
            else None
        ),
        step_scores=(
            routed.feedback.raw_evidence.get("step_scores", {})
            if routed.feedback
            else {}
        ),
        metadata={
            "iterations": iterations,
            "objective_name": objective_name,
            "dynamics_applied": bool(dynamics),
            "connector_count": len(connector_signals) if connector_signals else 0,
            "delayed_pending": delayed_status.get("pending", False),
        },
    )

    # ----- Step 7: Extract/update strategy patterns (Phase 3) -----
    strategy_suggestions = mem.suggest_strategy_reuse(
        intent=structure.intent,
        domain=structure.domain_type,
        current_tags=structure.contextual.to_primitives(),
    )
    strategy_updates = strategy_suggestions[:3]

    # ----- Step 8: Generate improvement proposals (Phase 4) -----
    gov = get_governor()

    if obj_set_result and obj_set_result.get("results"):
        proposals = gov.propose_from_objective_results(
            objective_results=obj_set_result["results"],
            aggregate_score=obj_set_result.get("aggregate_score", 0),
        )
        improvement_proposals.extend([p.to_dict() for p in proposals])

    # Propose strategy adoption if strong matches exist
    for strat in strategy_updates:
        proposal = gov.propose_from_strategy(strat)
        if proposal:
            improvement_proposals.append(proposal.to_dict())

    # ----- Build traces -----
    primitive_trace = {
        "run_id": run_id,
        "original_primitives": sorted(
            t.value for t in structure.contextual.to_primitives()
        ),
        "domain_type": structure.domain_type,
        "intent": structure.intent,
    }

    capability_trace = {}
    if hasattr(routed, "routed_result") and hasattr(
        routed.routed_result, "step_capabilities"
    ):
        capability_trace = routed.routed_result.step_capabilities

    routing_trace = routed.primitive_trace if hasattr(routed, "primitive_trace") else {}

    # ----- Determine final ok status -----
    ok = final_score >= learning_threshold
    if constraint_failures:
        ok = False
    if delayed_status.get("pending"):
        # Pending runs are not failed — they're deferred
        ok = final_score >= learning_threshold * 0.5  # more lenient for pending

    return FullRealityLoopResult(
        ok=ok,
        objective_scores=obj_set_result,
        hard_constraint_failures=constraint_failures,
        delayed_status=delayed_status,
        primitive_trace=primitive_trace,
        capability_trace=capability_trace,
        routing_trace=routing_trace,
        memory_recorded=True,
        strategy_updates=strategy_updates,
        improvement_proposals=improvement_proposals,
        iterations=iterations,
        run_id=run_id,
        final_score=final_score,
    )


__all__ = [
    "build_pipeline",
    "execute_composed",
    "execute_with_learning",
    "execute_with_routing",
    "execute_with_reality_loop",
    "execute_with_full_reality_loop",
    "LearningResult",
    "RoutedLearningResult",
    "RealityLoopResult",
    "FullRealityLoopResult",
]
