"""Resource Router — decomposes a pipeline into per-step capability assignments.

The router takes a ComposedStructure and produces an ExecutionPlan where
each step is assigned its own optimal capability.  This enables hybrid
execution: reasoning goes to Claude, formatting to local Python,
generation to a fast LLM, etc.

The router also builds a fallback chain per step so execution can retry
with the next-best capability if the primary fails.

Usage:
    from core.router import route_execution

    plan = route_execution(structure, constraints={"budget": "low"})
    for step in plan.steps:
        print(step.name, step.capability.name, step.fallback_chain)
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any

from core.capabilities import Capability, record_outcome
from core.composer import ComposedStructure
from core.matcher import CapabilitySelection, match_for_step
from core.orchestrator.pipeline import (
    ActionStep,
    FuncStep,
    Pipeline,
    PipelineResult,
    StepOutcome,
    run_pipeline,
)
from core.primitives import PrimitiveTag


# ---------------------------------------------------------------------------
# Execution plan types
# ---------------------------------------------------------------------------


@dataclass
class RoutedStep:
    """A pipeline step with its assigned capability and fallback chain."""

    name: str
    description: str
    capability: Capability
    selection: CapabilitySelection
    fallback_chain: list[Capability]
    original_step: ActionStep | FuncStep

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "capability": self.capability.name,
            "capability_type": self.capability.type,
            "score": round(self.selection.score, 4),
            "fallback_chain": [c.name for c in self.fallback_chain],
            "reasoning": self.selection.reasoning,
        }


@dataclass
class ExecutionPlan:
    """The output of route_execution() — a fully routed pipeline.

    Each step has an assigned capability and fallback chain.
    The plan includes the primitive trace and routing metadata.
    """

    intent: str
    domain_type: str
    steps: list[RoutedStep]
    constraints: dict[str, Any]
    primitive_trace: list[dict[str, Any]]
    routing_metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def is_hybrid(self) -> bool:
        """True if different steps use different capability types."""
        types = {s.capability.type for s in self.steps}
        return len(types) > 1

    def to_dict(self) -> dict[str, Any]:
        return {
            "intent": self.intent,
            "domain_type": self.domain_type,
            "is_hybrid": self.is_hybrid,
            "steps": [s.to_dict() for s in self.steps],
            "constraints": self.constraints,
            "primitive_trace": self.primitive_trace,
            "routing_metadata": self.routing_metadata,
        }


# ---------------------------------------------------------------------------
# Routing logic
# ---------------------------------------------------------------------------


def _get_step_primitives(step: ActionStep | FuncStep) -> set[PrimitiveTag]:
    """Extract primitive tags from a step's inputs."""
    if isinstance(step, FuncStep):
        return {PrimitiveTag.ACTION}  # FuncSteps are pure execution

    raw_tags: list[str] = (step.inputs or {}).get("primitive_tags", [])
    result: set[PrimitiveTag] = set()
    for tv in raw_tags:
        try:
            result.add(PrimitiveTag(tv))
        except ValueError:
            pass
    return result or {PrimitiveTag.ACTION}


def route_execution(
    structure: ComposedStructure,
    constraints: dict[str, Any] | None = None,
    *,
    max_fallbacks: int = 2,
) -> ExecutionPlan:
    """Route a composed structure to per-step capability assignments.

    Args:
        structure:     The ComposedStructure from compose().
        constraints:   Budget/latency/quality constraints for matching.
        max_fallbacks: Max fallback capabilities per step.

    Returns:
        ExecutionPlan with per-step routing and fallback chains.
    """
    from core.execution_bridge import build_pipeline

    constraints = constraints or {}
    pipeline = build_pipeline(structure)
    routed_steps: list[RoutedStep] = []

    for step in pipeline.steps:
        step_prims = _get_step_primitives(step)
        step_desc = (
            step.fn.__doc__ or step.name
            if isinstance(step, FuncStep)
            else step.description
        )

        selection = match_for_step(
            step_description=step_desc,
            primitives=step_prims,
            constraints=constraints,
        )

        # Build fallback chain from alternatives
        fallbacks = [alt.capability for alt in selection.alternatives[:max_fallbacks]]

        routed_steps.append(
            RoutedStep(
                name=step.name if isinstance(step, ActionStep) else step.name,
                description=step_desc,
                capability=selection.selected,
                selection=selection,
                fallback_chain=fallbacks,
                original_step=step,
            )
        )

    # Compute routing metadata
    capability_distribution: dict[str, int] = {}
    for rs in routed_steps:
        cap_name = rs.capability.name
        capability_distribution[cap_name] = capability_distribution.get(cap_name, 0) + 1

    return ExecutionPlan(
        intent=structure.intent,
        domain_type=structure.domain_type,
        steps=routed_steps,
        constraints=constraints,
        primitive_trace=structure.primitive_trace,
        routing_metadata={
            "capability_distribution": capability_distribution,
            "is_hybrid": len(set(rs.capability.type for rs in routed_steps)) > 1,
            "total_estimated_cost": sum(rs.capability.cost for rs in routed_steps),
            "total_estimated_latency": sum(
                rs.capability.latency for rs in routed_steps
            ),
            "pipeline_name": pipeline.name,
        },
    )


# ---------------------------------------------------------------------------
# Routed execution
# ---------------------------------------------------------------------------


@dataclass
class RoutedExecutionResult:
    """Result of executing a routed plan.

    Extends PipelineResult with routing trace — which capability was
    used for each step, whether fallbacks fired, and performance data.
    """

    pipeline_result: PipelineResult
    execution_plan: ExecutionPlan
    step_capabilities: dict[str, str]  # step_name → capability_name used
    fallbacks_used: dict[str, list[str]]  # step_name → [caps tried before success]
    performance_updates: list[dict[str, Any]]

    @property
    def ok(self) -> bool:
        return self.pipeline_result.ok

    def to_dict(self) -> dict[str, Any]:
        return {
            "pipeline_result": self.pipeline_result.to_dict(),
            "execution_plan": self.execution_plan.to_dict(),
            "step_capabilities": self.step_capabilities,
            "fallbacks_used": self.fallbacks_used,
            "performance_updates": self.performance_updates,
        }


def execute_routed(
    plan: ExecutionPlan,
    extra_context: dict[str, Any] | None = None,
) -> RoutedExecutionResult:
    """Execute a routed plan, tracking which capability handles each step.

    Injects routing metadata into the pipeline context so every action
    knows which capability was selected and why.  After execution,
    performance records are updated for adaptive learning.
    """
    # Build pipeline context with full routing trace
    context: dict[str, Any] = {
        "_intent": plan.intent,
        "_domain_type": plan.domain_type,
        "_primitive_trace": plan.primitive_trace,
        "_routing_plan": plan.to_dict(),
        "_constraints": plan.constraints,
    }
    if extra_context:
        context.update(extra_context)

    # Inject per-step capability info into the context
    for routed_step in plan.steps:
        context[f"_capability:{routed_step.name}"] = {
            "selected": routed_step.capability.name,
            "type": routed_step.capability.type,
            "score": routed_step.selection.score,
            "reasoning": routed_step.selection.reasoning,
            "fallbacks": [c.name for c in routed_step.fallback_chain],
        }

    # Build the raw pipeline from the routed steps
    raw_steps = [rs.original_step for rs in plan.steps]
    pipeline = Pipeline(
        name=f"routed:{plan.domain_type}:{plan.intent[:40]}",
        steps=raw_steps,
        stop_on_fail=True,
        source_agent="router",
    )

    # Execute
    started = time.time()
    result = run_pipeline(pipeline, context=context)
    total_latency = time.time() - started

    # Track which capabilities were used and update performance
    step_capabilities: dict[str, str] = {}
    fallbacks_used: dict[str, list[str]] = {}
    perf_updates: list[dict[str, Any]] = []

    for routed_step, outcome in zip(plan.steps, result.steps):
        cap_name = routed_step.capability.name
        step_capabilities[routed_step.name] = cap_name
        fallbacks_used[routed_step.name] = []  # no fallback execution yet

        step_success = outcome.status == "ok"
        step_latency = total_latency / max(len(plan.steps), 1)

        record_outcome(
            capability_name=cap_name,
            success=step_success,
            latency_s=step_latency,
            cost=routed_step.capability.cost,
        )

        perf_updates.append(
            {
                "step": routed_step.name,
                "capability": cap_name,
                "success": step_success,
                "latency_s": round(step_latency, 4),
            }
        )

    return RoutedExecutionResult(
        pipeline_result=result,
        execution_plan=plan,
        step_capabilities=step_capabilities,
        fallbacks_used=fallbacks_used,
        performance_updates=perf_updates,
    )


__all__ = [
    "ExecutionPlan",
    "RoutedStep",
    "RoutedExecutionResult",
    "route_execution",
    "execute_routed",
]
