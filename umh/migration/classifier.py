"""Phase 83 module classifier — static analysis for migration risk classification.

Classifies modules by reading file content for bypass-risk patterns.
No dynamic imports. No subprocess. No execution. No deletion.
Findings are risk signals, not proof.
"""

from __future__ import annotations

import os
import re
from typing import Any

from umh.migration.contracts import (
    LegacyModuleCategory,
    LegacyModuleRecord,
    LegacyModuleStatus,
    MigrationAction,
    MigrationRiskLevel,
)


_SUBPROCESS_PATTERNS: list[re.Pattern[str]] = [
    re.compile(r"\bsubprocess\.(run|call|Popen|check_output|check_call)\b"),
    re.compile(r"\bos\.system\s*\("),
    re.compile(r"\bos\.popen\s*\("),
]

_NETWORK_PATTERNS: list[re.Pattern[str]] = [
    re.compile(r"\brequests\.(get|post|put|delete|patch|head)\s*\("),
    re.compile(r"\bhttpx\.(get|post|put|delete|AsyncClient|Client)\b"),
    re.compile(r"\burllib\.request\b"),
    re.compile(r"\baiohttp\.ClientSession\b"),
]

_DIRECT_STORAGE_PATTERNS: list[re.Pattern[str]] = [
    re.compile(r"""\bopen\s*\([^)]*['"][wa]"""),
    re.compile(r"\bPath\s*\([^)]*\)\s*\.write_text\b"),
    re.compile(r"\bPath\s*\([^)]*\)\s*\.write_bytes\b"),
    re.compile(r"\bjson\.dump\s*\("),
    re.compile(r"\bsqlite3\.connect\b"),
    re.compile(r"\bos\.remove\s*\("),
    re.compile(r"\bshutil\.(rmtree|move|copy)\b"),
]

_EXECUTION_BYPASS_PATTERNS: list[re.Pattern[str]] = [
    re.compile(r"\bwhile\s+True\s*:.*(?:run|execute|process|loop)", re.IGNORECASE),
    re.compile(r"\basyncio\.run\s*\("),
    re.compile(r"\bdef\s+run_loop\b"),
    re.compile(r"\bdef\s+main_loop\b"),
    re.compile(r"\bdef\s+execution_loop\b"),
    re.compile(r"\bclass\s+\w*Worker\b"),
    re.compile(r"\bclass\s+\w*Runner\b"),
    re.compile(r"\bclass\s+\w*Executor\b"),
]

_MEMORY_BYPASS_PATTERNS: list[re.Pattern[str]] = [
    re.compile(r"\bclass\s+\w*MemoryStore\b"),
    re.compile(r"\bclass\s+\w*Memory\b.*store", re.IGNORECASE),
    re.compile(r"\b_memories\s*:\s*dict\b"),
    re.compile(r"\bclass\s+\w*SessionStore\b"),
]

_DUPLICATE_CONCEPT_MAP: dict[str, list[str]] = {
    "causal_attribution": ["umh.reasoning.causal_attribution"],
    "causal_credit": ["umh.reasoning.causal_credit"],
    "causal_memory": ["umh.reasoning.causal_memory"],
    "context_engine": ["umh.reasoning.context_engine"],
    "control_layer": ["umh.reasoning.control_layer"],
    "convergence": ["umh.reasoning.convergence"],
    "counterfactual_eval": ["umh.reasoning.counterfactual_eval"],
    "credit_assignment": ["umh.reasoning.credit_assignment"],
    "influence_orchestrator": ["umh.reasoning.influence_orchestrator"],
    "influence_scoring": ["umh.reasoning.influence_scoring"],
    "meta_weight_engine": ["umh.reasoning.meta_weight_engine"],
    "adaptive_exploration": ["umh.analytics.adaptive_exploration"],
    "exploration_engine": ["umh.analytics.exploration_engine"],
    "fabric_analytics": ["umh.analytics.fabric_analytics"],
    "pattern_engine": ["umh.analytics.pattern_engine"],
    "score_distribution": ["umh.analytics.score_distribution"],
    "signal_orchestrator": ["umh.analytics.signal_orchestrator"],
    "strategy_pattern_memory": ["umh.analytics.strategy_pattern_memory"],
    "directive_engine": ["umh.planning.directive_engine"],
    "hierarchical_planning": ["umh.planning.hierarchical_planning"],
    "plan_mutation": ["umh.planning.plan_mutation"],
    "outcome_evaluator": ["umh.feedback.outcome_evaluator"],
    "outcome_feedback": ["umh.feedback.outcome_feedback"],
    "foresight_engine": ["umh.policy.foresight_engine"],
    "stability_guard": ["umh.policy.stability_guard"],
    "system_graph": ["umh.execution.system_graph"],
    "system_registry": ["umh.execution.system_registry"],
    "system_selector": ["umh.execution.system_selector"],
}


def _read_content(file_path: str, content: str | None = None) -> str:
    if content is not None:
        return content
    if not os.path.isfile(file_path):
        return ""
    try:
        with open(file_path, "r", errors="replace") as f:
            return f.read()
    except Exception:
        return ""


def _strip_comments(text: str) -> str:
    lines = text.split("\n")
    result: list[str] = []
    for line in lines:
        stripped = line.lstrip()
        if stripped.startswith("#"):
            continue
        result.append(line)
    return "\n".join(result)


def detect_bypass_risk(content: str) -> list[str]:
    """Detect patterns that suggest execution/governance bypass. Returns evidence list."""
    evidence: list[str] = []
    code = _strip_comments(content)
    for pat in _SUBPROCESS_PATTERNS:
        if pat.search(code):
            evidence.append(f"subprocess/os usage: {pat.pattern}")
    for pat in _NETWORK_PATTERNS:
        if pat.search(code):
            evidence.append(f"direct network access: {pat.pattern}")
    return evidence


def detect_direct_execution_patterns(content: str) -> list[str]:
    """Detect alternative execution loops or workers."""
    evidence: list[str] = []
    code = _strip_comments(content)
    for pat in _EXECUTION_BYPASS_PATTERNS:
        if pat.search(code):
            evidence.append(f"execution bypass pattern: {pat.pattern}")
    return evidence


def detect_direct_storage_patterns(content: str) -> list[str]:
    """Detect direct file/storage writes outside the storage gateway."""
    evidence: list[str] = []
    code = _strip_comments(content)
    for pat in _DIRECT_STORAGE_PATTERNS:
        if pat.search(code):
            evidence.append(f"direct storage pattern: {pat.pattern}")
    return evidence


def detect_direct_network_patterns(content: str) -> list[str]:
    """Detect direct network usage."""
    evidence: list[str] = []
    code = _strip_comments(content)
    for pat in _NETWORK_PATTERNS:
        if pat.search(code):
            evidence.append(f"network pattern: {pat.pattern}")
    return evidence


def detect_direct_imports(content: str) -> list[str]:
    """Detect imports of legacy runtime_engine modules from content."""
    evidence: list[str] = []
    for line in content.split("\n"):
        stripped = line.strip()
        if stripped.startswith("#"):
            continue
        if "umh.runtime_engine" in stripped and ("import" in stripped):
            evidence.append(f"runtime_engine import: {stripped[:120]}")
    return evidence


def detect_duplicate_concept(file_path: str, content: str | None = None) -> str | None:
    """If this module name is a known duplicate, return the clean equivalent."""
    basename = os.path.basename(file_path).replace(".py", "")
    equivalents = _DUPLICATE_CONCEPT_MAP.get(basename)
    if equivalents:
        return equivalents[0]
    return None


def classify_runtime_engine_module(
    file_path: str,
    content: str | None = None,
) -> LegacyModuleRecord:
    """Classify a runtime_engine module with static analysis."""
    text = _read_content(file_path, content)
    rel_path = file_path.replace("\\", "/")

    from umh.migration.inventory import module_path_to_module_name

    record = LegacyModuleRecord(
        module_path=rel_path,
        module_name=module_path_to_module_name(rel_path),
        category=LegacyModuleCategory.RUNTIME_ENGINE,
        status=LegacyModuleStatus.FUTURE_REVIEW,
        risk_level=MigrationRiskLevel.MEDIUM,
        migration_action=MigrationAction.REVIEW_MANUALLY,
        source="phase83_classifier",
    )

    clean_eq = detect_duplicate_concept(file_path, text)
    if clean_eq:
        record.status = LegacyModuleStatus.DUPLICATE
        record.clean_equivalent = clean_eq
        record.migration_action = MigrationAction.MIGRATE_IMPORTS
        record.reason = f"duplicated by {clean_eq}"
        record.risk_level = MigrationRiskLevel.LOW
        record.tags.append("duplicate")

    bypass_evidence = detect_bypass_risk(text)
    exec_evidence = detect_direct_execution_patterns(text)
    storage_evidence = detect_direct_storage_patterns(text)

    all_evidence = bypass_evidence + exec_evidence + storage_evidence
    record.evidence = all_evidence

    if bypass_evidence:
        record.risk_level = MigrationRiskLevel.HIGH
        record.tags.append("bypass_risk")
        if record.status != LegacyModuleStatus.DUPLICATE:
            record.status = LegacyModuleStatus.BYPASS_RISK
            record.reason = record.reason or "bypass-risk patterns detected"

    if exec_evidence and record.risk_level.value not in ("high", "critical"):
        record.risk_level = MigrationRiskLevel.MEDIUM
        record.tags.append("execution_pattern")

    return record


def classify_substrate_module(
    file_path: str,
    content: str | None = None,
) -> LegacyModuleRecord:
    """Classify a substrate module with static analysis."""
    text = _read_content(file_path, content)
    rel_path = file_path.replace("\\", "/")

    from umh.migration.inventory import module_path_to_module_name

    record = LegacyModuleRecord(
        module_path=rel_path,
        module_name=module_path_to_module_name(rel_path),
        category=LegacyModuleCategory.SUBSTRATE,
        status=LegacyModuleStatus.FUTURE_REVIEW,
        risk_level=MigrationRiskLevel.MEDIUM,
        migration_action=MigrationAction.REVIEW_MANUALLY,
        source="phase83_classifier",
    )

    bypass_evidence = detect_bypass_risk(text)
    exec_evidence = detect_direct_execution_patterns(text)
    storage_evidence = detect_direct_storage_patterns(text)

    all_evidence = bypass_evidence + exec_evidence + storage_evidence
    record.evidence = all_evidence

    if bypass_evidence:
        record.risk_level = MigrationRiskLevel.HIGH
        record.status = LegacyModuleStatus.BYPASS_RISK
        record.reason = "bypass-risk patterns detected"
        record.tags.append("bypass_risk")

    if exec_evidence:
        record.tags.append("execution_pattern")
        if record.risk_level == MigrationRiskLevel.MEDIUM:
            record.reason = record.reason or "alternative execution patterns found"

    return record


def classify_legacy_module(
    file_path: str,
    content: str | None = None,
) -> LegacyModuleRecord:
    """Classify any module. Dispatches to specific classifiers for legacy paths."""
    path = file_path.replace("\\", "/")
    if "runtime_engine/" in path:
        return classify_runtime_engine_module(file_path, content)
    if "substrate/" in path:
        return classify_substrate_module(file_path, content)

    from umh.migration.inventory import classify_module_path, module_path_to_module_name

    category = classify_module_path(path)
    return LegacyModuleRecord(
        module_path=path,
        module_name=module_path_to_module_name(path),
        category=category,
        status=LegacyModuleStatus.ACTIVE_RETAINED,
        risk_level=MigrationRiskLevel.NONE,
        migration_action=MigrationAction.RETAIN,
        source="phase83_classifier",
    )


def recommend_migration_action(record: LegacyModuleRecord) -> MigrationAction:
    """Recommend a migration action based on current classification."""
    if record.status == LegacyModuleStatus.DUPLICATE:
        return MigrationAction.MIGRATE_IMPORTS
    if record.status == LegacyModuleStatus.BYPASS_RISK:
        return MigrationAction.REVIEW_MANUALLY
    if record.status == LegacyModuleStatus.DEPRECATED:
        return MigrationAction.MARK_DEPRECATED
    if record.status == LegacyModuleStatus.ACTIVE_RETAINED:
        return MigrationAction.RETAIN
    if record.status == LegacyModuleStatus.MIGRATED:
        return MigrationAction.FUTURE_DELETE
    if record.status == LegacyModuleStatus.FUTURE_REVIEW:
        return MigrationAction.REVIEW_MANUALLY
    return MigrationAction.UNKNOWN
