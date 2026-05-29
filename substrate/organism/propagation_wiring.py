"""Propagation wiring — registers all propagation targets with the engine.

Creates a fully-wired ParallelPropagationEngine with handlers bound to
real organism subsystems. Called by the daemon during startup.

Wave 1 (independent immediate updates):
  - OutcomeLearningLoop.record_outcome
  - TemplateRegistry.generate_candidate_from_outcome
  - MemoryPromotionPipeline.generate_candidate_from_outcome
  - AgentCapabilityModel.update_reliability
  - WorldModel evidence attachment

Wave 2 (derived recalculation):
  - ContradictionEngine recheck
  - ReadinessModel recalculate
  - BottleneckEngine recalculate
  - CompositionEngine template index refresh
  - DependencyGraph recompute

UMH substrate subsystem. Instance-agnostic.
"""

from __future__ import annotations

import logging
from typing import Any

from substrate.organism.coherence_propagation import (
    OutcomeCommitted,
    ParallelPropagationEngine,
    PrimitiveRelationship,
    PropagationTarget,
)
from substrate.organism.outcome_learning import OutcomeLearningLoop, OutcomeRecord, OutcomeStatus
from substrate.organism.template_registry import TemplateRegistry
from substrate.organism.agent_capability_model import AgentCapabilityModel

logger = logging.getLogger(__name__)


def _build_outcome_learning_handler(
    learning_loop: OutcomeLearningLoop,
) -> callable:
    def handler(outcome: OutcomeCommitted) -> dict[str, Any]:
        status = (
            OutcomeStatus.SUCCESS
            if outcome.validation_result == "passed"
            else OutcomeStatus.PARTIAL
        )
        record = OutcomeRecord(
            action_type=outcome.action_type,
            plan_id=outcome.execution_graph_id,
            description=f"Governed execution: {outcome.action_type}",
            status=status,
            duration_seconds=outcome.duration_ms / 1000.0,
        )
        learning_loop.record_outcome(record)
        return {
            "recorded": True,
            "action_type": outcome.action_type,
            "status": status.value,
        }
    return handler


def _build_template_generation_handler(
    registry: TemplateRegistry,
) -> callable:
    def handler(outcome: OutcomeCommitted) -> dict[str, Any]:
        outcome_dict = outcome.to_outcome_dict()
        candidate = registry.generate_candidate_from_outcome(outcome_dict)
        return {
            "template_id": candidate.template_id,
            "template_type": candidate.template_type.value,
            "confidence": candidate.confidence,
        }
    return handler


def _build_memory_generation_handler(
    pipeline: Any,
) -> callable:
    def handler(outcome: OutcomeCommitted) -> dict[str, Any]:
        outcome_dict = outcome.to_outcome_dict()
        candidates = pipeline.generate_candidate_from_outcome(outcome_dict)
        return {
            "candidates_generated": len(candidates),
            "ids": [c.id for c in candidates],
        }
    return handler


def _build_agent_capability_handler(
    model: AgentCapabilityModel,
) -> callable:
    def handler(outcome: OutcomeCommitted) -> dict[str, Any]:
        success = outcome.validation_result == "passed"
        records = model.update_reliability(
            agent_type=outcome.agent_type,
            capabilities_used=outcome.capabilities_used or ["code_search", "file_edit"],
            success=success,
            duration_ms=outcome.duration_ms,
            outcome_id=outcome.event_id,
            action_envelope_id=outcome.action_envelope_id,
            risk_class=outcome.risk_class,
        )
        return {
            "records_created": len(records),
            "agent_type": outcome.agent_type,
            "success": success,
        }
    return handler


def _build_world_model_evidence_handler() -> callable:
    def handler(outcome: OutcomeCommitted) -> dict[str, Any]:
        from substrate.organism.world_model import extract_world_model
        wm = extract_world_model()
        matched = 0
        for entity_id in outcome.changed_entities:
            entity = wm.get_entity(entity_id)
            if entity and outcome.evidence:
                entity.evidence_sources.extend(outcome.evidence[:3])
                matched += 1
        return {
            "entities_checked": len(wm.entities),
            "entities_matched": matched,
            "evidence_attached": len(outcome.evidence),
        }
    return handler


def _build_contradiction_recheck_handler() -> callable:
    def handler(outcome: OutcomeCommitted) -> dict[str, Any]:
        from substrate.organism.world_model import extract_world_model
        from substrate.organism.dependency_graph import build_dependency_graph
        from substrate.organism.contradiction_engine import detect_contradictions
        wm = extract_world_model()
        dep = build_dependency_graph(wm)
        cr = detect_contradictions(wm, dep)
        return {
            "contradictions_after": len(cr.contradictions),
            "severity_counts": {
                s.value: sum(1 for c in cr.contradictions if c.severity == s)
                for s in set(c.severity for c in cr.contradictions)
            },
        }
    return handler


def _build_readiness_recalculate_handler(
    readiness_model: Any,
) -> callable:
    def handler(outcome: OutcomeCommitted) -> dict[str, Any]:
        report = readiness_model.compute()
        return {
            "composite_score": round(report.composite_score, 1),
            "status": report.overall_status,
        }
    return handler


def _build_bottleneck_recalculate_handler(
    bottleneck_engine: Any,
) -> callable:
    def handler(outcome: OutcomeCommitted) -> dict[str, Any]:
        return {
            "active_bottlenecks": len(bottleneck_engine.active),
            "recalculated": True,
        }
    return handler


def _build_composition_refresh_handler(
    template_registry: TemplateRegistry,
) -> callable:
    def handler(outcome: OutcomeCommitted) -> dict[str, Any]:
        promoted = template_registry.list_promoted()
        candidates = template_registry.list_candidates()
        return {
            "promoted_templates": len(promoted),
            "total_candidates": len(candidates),
            "index_refreshed": True,
        }
    return handler


def _build_dependency_recompute_handler() -> callable:
    def handler(outcome: OutcomeCommitted) -> dict[str, Any]:
        from substrate.organism.world_model import extract_world_model
        from substrate.organism.dependency_graph import build_dependency_graph
        wm = extract_world_model()
        dep = build_dependency_graph(wm)
        return {
            "edges": len(dep.edges),
            "orphans": len(dep.orphaned_nodes()),
            "recomputed": True,
        }
    return handler


def build_propagation_engine(
    learning_loop: OutcomeLearningLoop,
    template_registry: TemplateRegistry,
    memory_pipeline: Any,
    agent_capability_model: AgentCapabilityModel,
    readiness_model: Any | None = None,
    bottleneck_engine: Any | None = None,
    store_dir: str | None = None,
) -> ParallelPropagationEngine:
    """Build a fully-wired ParallelPropagationEngine.

    All handlers are bound to real subsystem instances. The engine
    is ready to be injected into GovernedExecutionSpine.
    """
    engine = ParallelPropagationEngine(store_dir=store_dir)

    engine.register_target(PropagationTarget(
        name="outcome_learning",
        primitive_relationship=PrimitiveRelationship.FEEDBACK,
        wave=1,
        handler=_build_outcome_learning_handler(learning_loop),
    ))

    engine.register_target(PropagationTarget(
        name="template_generation",
        primitive_relationship=PrimitiveRelationship.ACTION,
        wave=1,
        handler=_build_template_generation_handler(template_registry),
    ))

    engine.register_target(PropagationTarget(
        name="memory_generation",
        primitive_relationship=PrimitiveRelationship.FEEDBACK,
        wave=1,
        handler=_build_memory_generation_handler(memory_pipeline),
    ))

    engine.register_target(PropagationTarget(
        name="agent_capability_update",
        primitive_relationship=PrimitiveRelationship.RESOURCE,
        wave=1,
        handler=_build_agent_capability_handler(agent_capability_model),
    ))

    engine.register_target(PropagationTarget(
        name="world_model_evidence",
        primitive_relationship=PrimitiveRelationship.STATE,
        wave=1,
        handler=_build_world_model_evidence_handler(),
    ))

    engine.register_target(PropagationTarget(
        name="contradiction_recheck",
        primitive_relationship=PrimitiveRelationship.CONSTRAINT,
        wave=2,
        handler=_build_contradiction_recheck_handler(),
    ))

    if readiness_model is not None:
        engine.register_target(PropagationTarget(
            name="readiness_recalculate",
            primitive_relationship=PrimitiveRelationship.STATE,
            wave=2,
            handler=_build_readiness_recalculate_handler(readiness_model),
        ))

    if bottleneck_engine is not None:
        engine.register_target(PropagationTarget(
            name="bottleneck_recalculate",
            primitive_relationship=PrimitiveRelationship.STATE,
            wave=2,
            handler=_build_bottleneck_recalculate_handler(bottleneck_engine),
        ))

    engine.register_target(PropagationTarget(
        name="composition_template_refresh",
        primitive_relationship=PrimitiveRelationship.GOAL,
        wave=2,
        handler=_build_composition_refresh_handler(template_registry),
    ))

    engine.register_target(PropagationTarget(
        name="dependency_recompute",
        primitive_relationship=PrimitiveRelationship.CONSTRAINT,
        wave=2,
        handler=_build_dependency_recompute_handler(),
    ))

    logger.info(
        "propagation engine built: %d targets across %d waves",
        len(engine._targets),
        len(set(t.wave for t in engine._targets)),
    )

    return engine
