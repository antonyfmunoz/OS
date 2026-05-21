"""Generalized adapter maturity evidence model.

Extends AdapterMaturityLevel (defined in adapter_manifest.py) with an
evidence dataclass and requirement predicates that determine which level
an adapter has actually earned. Generalizes the CU-specific
actuator_maturity_v1.py pattern to all modality types.

Layer 3 Unified Architecture §3.
UMH substrate subsystem.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from adapters.adapter_engine.adapter_manifest import AdapterMaturityLevel


@dataclass
class MaturityEvidence:
    """Observable facts about an adapter's operational history.

    Four dimensions (architecture doc §3.3):
      - capability coverage: auth_verified, capability_count
      - doc absorption: doc_absorption_pct
      - operational experience: execution_count, success_count,
        failure_modes_documented, mean_latency_ms, p99_latency_ms
      - edge case knowledge: edge_cases_mapped, edge_case_coverage_pct,
        has_recovery_playbook, optimization_applied, cross_adapter_tested
    """

    auth_verified: bool = False
    capability_count: int = 0
    execution_count: int = 0
    success_count: int = 0
    failure_modes_documented: int = 0
    doc_absorption_pct: float = 0.0
    edge_cases_mapped: int = 0
    edge_case_coverage_pct: float = 0.0
    mean_latency_ms: float = 0.0
    p99_latency_ms: float = 0.0
    has_recovery_playbook: bool = False
    optimization_applied: bool = False
    cross_adapter_tested: bool = False


MATURITY_REQUIREMENTS: dict[AdapterMaturityLevel, list[str]] = {
    AdapterMaturityLevel.L0_REGISTERED: [],
    AdapterMaturityLevel.L1_CONNECTED: [
        "auth_verified",
    ],
    AdapterMaturityLevel.L2_CAPABILITIES_KNOWN: [
        "auth_verified",
        "capability_count_gt_0",
    ],
    AdapterMaturityLevel.L3_TESTED: [
        "auth_verified",
        "capability_count_gt_0",
        "execution_count_gt_10",
    ],
    AdapterMaturityLevel.L4_EDGE_CASES_MAPPED: [
        "auth_verified",
        "capability_count_gt_0",
        "execution_count_gt_10",
        "failure_modes_documented_gt_0",
        "edge_cases_mapped_gt_0",
    ],
    AdapterMaturityLevel.L5_OPTIMIZED: [
        "auth_verified",
        "capability_count_gt_0",
        "execution_count_gt_10",
        "failure_modes_documented_gt_0",
        "edge_cases_mapped_gt_0",
        "doc_absorption_gt_80pct",
        "optimization_applied",
    ],
    AdapterMaturityLevel.L6_EXPERT: [
        "auth_verified",
        "capability_count_gt_0",
        "execution_count_gt_10",
        "failure_modes_documented_gt_0",
        "edge_cases_mapped_gt_0",
        "doc_absorption_gt_90pct",
        "optimization_applied",
        "has_recovery_playbook",
        "edge_case_coverage_gt_80pct",
    ],
    AdapterMaturityLevel.L7_MASTERFUL: [
        "auth_verified",
        "capability_count_gt_0",
        "execution_count_gt_10",
        "failure_modes_documented_gt_0",
        "edge_cases_mapped_gt_0",
        "doc_absorption_gt_90pct",
        "optimization_applied",
        "has_recovery_playbook",
        "edge_case_coverage_gt_90pct",
        "cross_adapter_tested",
    ],
}


def _check_predicate(predicate: str, evidence: MaturityEvidence) -> bool:
    """Evaluate a string predicate against evidence fields.

    Three comparator forms:
      - bare name        → getattr(evidence, name) is truthy
      - name_gt_N        → int field > N
      - name_gt_Npct     → float field (stored as 0-100) > N
    """
    if "pct" in predicate:
        parts = predicate.rsplit("_gt_", 1)
        if len(parts) != 2:
            return False
        field_name = parts[0] + "_pct"
        threshold = float(parts[1].replace("pct", ""))
        return float(getattr(evidence, field_name, 0.0)) > threshold

    if "_gt_" in predicate:
        parts = predicate.rsplit("_gt_", 1)
        if len(parts) != 2:
            return False
        field_name = parts[0]
        threshold = int(parts[1])
        return int(getattr(evidence, field_name, 0)) > threshold

    return bool(getattr(evidence, predicate, False))


def compute_adapter_maturity(evidence: MaturityEvidence) -> AdapterMaturityLevel:
    """Determine the highest maturity level the evidence supports.

    Walk-down-from-top: start at L7, return first level where every
    predicate passes. Guarantees cumulative semantics — a gap at any
    level caps the result below it.
    """
    for level in reversed(AdapterMaturityLevel):
        predicates = MATURITY_REQUIREMENTS.get(level, [])
        if all(_check_predicate(p, evidence) for p in predicates):
            return level
    return AdapterMaturityLevel.L0_REGISTERED


def validate_maturity_claim(
    claimed: AdapterMaturityLevel,
    evidence: MaturityEvidence,
) -> tuple[bool, AdapterMaturityLevel, list[str]]:
    """Check whether *claimed* level is justified by *evidence*.

    Returns (is_valid, actual_level, missing_predicates).
    missing_predicates lists every predicate in the claimed level's
    requirements that the evidence fails.
    """
    actual = compute_adapter_maturity(evidence)
    missing = [
        p for p in MATURITY_REQUIREMENTS.get(claimed, []) if not _check_predicate(p, evidence)
    ]
    return (actual >= claimed, actual, missing)
