"""Phase 83 compatibility map — known clean equivalents for legacy modules.

Advisory mappings only. No import rewrites. No shim execution.
No dynamic module loading.
"""

from __future__ import annotations

from typing import Any

from umh.migration.contracts import (
    LegacyModuleRecord,
    LegacyModuleStatus,
    MigrationAction,
    MigrationMapping,
)


_KNOWN_EQUIVALENTS: dict[str, str] = {
    "umh.runtime_engine.cognitive_loop": "umh.run / umh.execution.engine",
    "umh.runtime_engine.execution_engine": "umh.execution.engine",
    "umh.runtime_engine.execution_spine": "umh.execution.engine / umh.execution.pipeline",
    "umh.runtime_engine.agent_runtime": "umh.execution.engine / umh.adapters.llm",
    "umh.runtime_engine.gateway": "umh.gateway.entry / umh.execution.governance_gate",
    "umh.runtime_engine.authority_engine": "umh.execution.governance_gate / umh.governance.authority",
    "umh.runtime_engine.memory": "umh.memory / umh.storage / umh.feedback.memory_bridge",
    "umh.runtime_engine.memory_fabric": "umh.memory / umh.feedback.memory_bridge",
    "umh.runtime_engine.model_router": "umh.adapters.model_router",
    "umh.runtime_engine.model_preferences": "umh.adapters.model_router",
    "umh.runtime_engine.decision_trace": "umh.control.trace_store / umh.observability",
    "umh.runtime_engine.decision_log": "umh.control.trace_store",
    "umh.runtime_engine.session_runtime": "umh.workstation.session_state",
    "umh.runtime_engine.session_state": "umh.workstation.session_state",
    "umh.runtime_engine.session_store": "umh.workstation.session_state",
    "umh.runtime_engine.session_interface": "umh.workstation.session_state / umh.interface",
    "umh.runtime_engine.skill_registry": "umh.registry / umh.capabilities",
    "umh.runtime_engine.system_health": "umh.observability.system_status",
    "umh.runtime_engine.status": "umh.observability.system_status",
    "umh.runtime_engine.orchestrator": "umh.orchestrator.engine",
    "umh.runtime_engine.causal_attribution": "umh.reasoning.causal_attribution",
    "umh.runtime_engine.causal_credit": "umh.reasoning.causal_credit",
    "umh.runtime_engine.causal_memory": "umh.reasoning.causal_memory",
    "umh.runtime_engine.context_engine": "umh.reasoning.context_engine",
    "umh.runtime_engine.control_layer": "umh.reasoning.control_layer",
    "umh.runtime_engine.convergence": "umh.reasoning.convergence",
    "umh.runtime_engine.counterfactual_eval": "umh.reasoning.counterfactual_eval",
    "umh.runtime_engine.credit_assignment": "umh.reasoning.credit_assignment",
    "umh.runtime_engine.influence_orchestrator": "umh.reasoning.influence_orchestrator",
    "umh.runtime_engine.influence_scoring": "umh.reasoning.influence_scoring",
    "umh.runtime_engine.meta_weight_engine": "umh.reasoning.meta_weight_engine",
    "umh.runtime_engine.adaptive_exploration": "umh.analytics.adaptive_exploration",
    "umh.runtime_engine.exploration_engine": "umh.analytics.exploration_engine",
    "umh.runtime_engine.fabric_analytics": "umh.analytics.fabric_analytics",
    "umh.runtime_engine.pattern_engine": "umh.analytics.pattern_engine",
    "umh.runtime_engine.score_distribution": "umh.analytics.score_distribution",
    "umh.runtime_engine.signal_orchestrator": "umh.analytics.signal_orchestrator",
    "umh.runtime_engine.strategy_pattern_memory": "umh.analytics.strategy_pattern_memory",
    "umh.runtime_engine.directive_engine": "umh.planning.directive_engine",
    "umh.runtime_engine.hierarchical_planning": "umh.planning.hierarchical_planning",
    "umh.runtime_engine.plan_mutation": "umh.planning.plan_mutation",
    "umh.runtime_engine.outcome_evaluator": "umh.feedback.outcome_evaluator",
    "umh.runtime_engine.outcome_feedback": "umh.feedback.outcome_feedback",
    "umh.runtime_engine.foresight_engine": "umh.policy.foresight_engine",
    "umh.runtime_engine.stability_guard": "umh.policy.stability_guard",
    "umh.runtime_engine.system_graph": "umh.execution.system_graph",
    "umh.runtime_engine.system_registry": "umh.execution.system_registry",
    "umh.runtime_engine.system_selector": "umh.execution.system_selector",
    "umh.substrate.operator_session": "umh.workstation.session_state",
    "umh.substrate.operator_state": "umh.workstation.session_state",
    "umh.substrate.operator_presence": "future interface/presence phase",
    "umh.substrate.operator_delivery": "future interface/presence phase",
    "umh.substrate.execution_worker": "umh.execution.engine (canonical spine)",
    "umh.substrate.task_execution": "umh.execution.engine / umh.orchestrator",
    "umh.substrate.task_pipeline": "umh.execution.pipeline",
    "umh.substrate.task_queue": "umh.orchestrator.engine",
    "umh.substrate.task_system": "umh.orchestrator.engine",
    "umh.substrate.storage": "umh.storage",
    "umh.substrate.event_store": "umh.events.stream / umh.control.trace_store",
    "umh.substrate.result_store": "umh.control.trace_store",
}


def get_known_clean_equivalents() -> dict[str, str]:
    """Return the full known equivalents map."""
    return dict(_KNOWN_EQUIVALENTS)


def find_clean_equivalent(legacy_module: str) -> str | None:
    """Find the clean equivalent for a legacy module path or name."""
    return _KNOWN_EQUIVALENTS.get(legacy_module)


def build_migration_mapping_for_record(record: LegacyModuleRecord) -> MigrationMapping | None:
    """Build a MigrationMapping from a LegacyModuleRecord if a clean equivalent exists."""
    clean_eq = record.clean_equivalent or find_clean_equivalent(record.module_name)
    if not clean_eq:
        return None

    confidence = 0.8
    if record.status == LegacyModuleStatus.DUPLICATE:
        confidence = 0.9
    elif record.status == LegacyModuleStatus.BYPASS_RISK:
        confidence = 0.5

    blockers: list[str] = []
    if record.status == LegacyModuleStatus.BYPASS_RISK:
        blockers.append("bypass-risk patterns need manual review")
    if record.evidence:
        blockers.append(f"{len(record.evidence)} risk findings need review")

    action = MigrationAction.MIGRATE_IMPORTS
    if record.status == LegacyModuleStatus.DUPLICATE:
        action = MigrationAction.MIGRATE_IMPORTS
    elif record.status == LegacyModuleStatus.BYPASS_RISK:
        action = MigrationAction.REVIEW_MANUALLY

    return MigrationMapping(
        legacy_module=record.module_name,
        clean_equivalent=clean_eq,
        migration_action=action,
        confidence=confidence,
        reason=record.reason or f"maps to {clean_eq}",
    )


def build_migration_mappings(records: list[LegacyModuleRecord]) -> list[MigrationMapping]:
    """Build mappings for all records that have known clean equivalents."""
    mappings: list[MigrationMapping] = []
    for r in records:
        m = build_migration_mapping_for_record(r)
        if m is not None:
            mappings.append(m)
    return mappings


def validate_compatibility_mapping(mapping: MigrationMapping) -> list[str]:
    """Validate a mapping for completeness. Returns list of issues."""
    issues: list[str] = []
    if not mapping.legacy_module:
        issues.append("missing legacy_module")
    if not mapping.clean_equivalent:
        issues.append("missing clean_equivalent")
    if mapping.confidence <= 0:
        issues.append("confidence must be > 0")
    return issues


def explain_compatibility_path(legacy_module: str) -> str:
    """Human-readable explanation of the compatibility/migration path for a module."""
    equiv = find_clean_equivalent(legacy_module)
    if equiv:
        return f"{legacy_module} -> {equiv} (known mapping, advisory only)"
    return f"{legacy_module} -> no known clean equivalent (review manually)"
