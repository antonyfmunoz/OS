"""Projection Readiness Gate — blocks feature build until source reconciliation is sufficient.

Phase 14.0. UMH substrate subsystem. Instance-agnostic.

Evaluates whether the projection source universe has been sufficiently
reconciled to proceed with feature build. Returns a structured report
with blocking issues and recommendations.
"""

from __future__ import annotations

import json
import logging
import os
from typing import Any

logger = logging.getLogger(__name__)

_REPO_ROOT = os.environ.get("UMH_ROOT", "/opt/OS")
_RECON_DIR = os.path.join(_REPO_ROOT, "data", "umh", "projection_reconciliation")


def _file_exists(filename: str) -> bool:
    return os.path.isfile(os.path.join(_RECON_DIR, filename))


def _load_json(filename: str) -> dict[str, Any] | None:
    path = os.path.join(_RECON_DIR, filename)
    if not os.path.isfile(path):
        return None
    try:
        with open(path) as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return None


def assess_projection_readiness() -> dict[str, Any]:
    """Evaluate projection reconciliation readiness across all gates."""
    blocking_issues: list[str] = []
    required_permissions: list[str] = []
    uninspected_sources: list[str] = []
    canonicality_unknowns: list[str] = []

    source_map_exists = _file_exists("projection_source_map.json")
    divergence_exists = _file_exists("phase14_0_divergence_diagnostic.json")
    convergence_plan_exists = _file_exists("trinity_convergence_plan.json")
    work_packets_exist = _file_exists("phase14_0_work_packets.json")
    permission_requests_exist = _file_exists("phase14_0_permission_requests.json")
    registry_exists = _file_exists("source_registry.jsonl")

    if not source_map_exists:
        blocking_issues.append("Source map does not exist")
    if not divergence_exists:
        blocking_issues.append("Divergence diagnostic does not exist")
    if not convergence_plan_exists:
        blocking_issues.append("Convergence plan does not exist")

    permissions = _load_json("phase14_0_permission_requests.json")
    if permissions:
        for req in permissions.get("requests", []):
            if req.get("status") == "pending":
                required_permissions.append(req.get("title", "unknown"))

    source_map = _load_json("projection_source_map.json")
    if source_map:
        projections = source_map.get("projections", {})
        for proj_name, proj_data in projections.items():
            if isinstance(proj_data, dict):
                for unknown in proj_data.get("unknowns", []):
                    canonicality_unknowns.append(f"{proj_name}: {unknown}")
                assessment = proj_data.get("canonicality_assessment", "")
                if "UNKNOWN" in str(assessment).upper() or "uninspected" in str(assessment).lower():
                    uninspected_sources.append(f"{proj_name}: {assessment}")

    divergence_data = _load_json("phase14_0_divergence_diagnostic.json")
    high_severity_count = 0
    if divergence_data:
        summary = divergence_data.get("summary", {})
        by_severity = summary.get("by_severity", {})
        high_severity_count = by_severity.get("high", 0) + by_severity.get("critical", 0)
        if high_severity_count > 0:
            blocking_issues.append(
                f"{high_severity_count} high/critical severity divergences unresolved"
            )

    ready_for_feature_build = (
        len(blocking_issues) == 0
        and len(required_permissions) == 0
        and len(uninspected_sources) == 0
        and high_severity_count == 0
    )

    ready_for_source_inspection = (
        permission_requests_exist
        and registry_exists
    )

    ready_for_convergence_execution = (
        source_map_exists
        and divergence_exists
        and convergence_plan_exists
        and len(required_permissions) == 0
        and len(uninspected_sources) == 0
    )

    if ready_for_feature_build:
        recommended_next = "Phase 14.2 — Feature Build"
    elif ready_for_convergence_execution:
        recommended_next = "Phase 14.1+ — Convergence Execution"
    elif ready_for_source_inspection:
        recommended_next = "Phase 14.1 — Permissioned Source Inspection Execution"
    else:
        recommended_next = "Complete Phase 14.0 artifacts"

    return {
        "ready_for_feature_build": ready_for_feature_build,
        "ready_for_source_inspection": ready_for_source_inspection,
        "ready_for_convergence_execution": ready_for_convergence_execution,
        "blocking_issues": blocking_issues,
        "required_permissions": required_permissions,
        "uninspected_sources": uninspected_sources,
        "canonicality_unknowns": canonicality_unknowns,
        "recommended_next_phase": recommended_next,
        "evidence": {
            "source_map_exists": source_map_exists,
            "divergence_diagnostic_exists": divergence_exists,
            "convergence_plan_exists": convergence_plan_exists,
            "work_packets_exist": work_packets_exist,
            "permission_requests_exist": permission_requests_exist,
            "registry_exists": registry_exists,
            "high_severity_divergences": high_severity_count,
        },
    }
