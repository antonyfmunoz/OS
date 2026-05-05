"""Phase 87C recommendations — build optimization candidates and reports.

Advisory/planning only. No real scanning. No cleanup. No deletion.
"""

from __future__ import annotations

from typing import Any

from umh.workstation_optimization.contracts import (
    DeviceArea,
    OptimizationActionType,
    OptimizationApprovalRequirement,
    OptimizationCandidate,
    OptimizationRiskLevel,
    OptimizationReversibility,
    WorkstationOptimizationReport,
    _ws_id,
)
from umh.workstation_optimization.baseline import build_onboarding_workstation_baseline_plan
from umh.workstation_optimization.device_literacy import build_default_device_literacy_explanations


def build_optimization_candidate(
    area: DeviceArea,
    action_type: OptimizationActionType,
    title: str,
    description: str = "",
    target: str = "",
    reason: str = "",
    estimated_benefit: str = "",
    risk_level: OptimizationRiskLevel = OptimizationRiskLevel.LOW,
    approval_required: OptimizationApprovalRequirement = OptimizationApprovalRequirement.EXPLICIT_APPROVAL,
    reversibility: OptimizationReversibility = OptimizationReversibility.FULLY_REVERSIBLE,
) -> OptimizationCandidate:
    return OptimizationCandidate(
        candidate_id=_ws_id("oc"),
        area=area,
        action_type=action_type,
        title=title,
        description=description,
        target=target,
        reason=reason,
        estimated_benefit=estimated_benefit,
        risk_level=risk_level,
        approval_required=approval_required,
        reversibility=reversibility,
    )


def build_onboarding_optimization_recommendations() -> list[OptimizationCandidate]:
    return [
        build_optimization_candidate(
            DeviceArea.LOCAL_FILES,
            OptimizationActionType.RECOMMEND,
            "Review Downloads folder",
            target="~/Downloads",
            reason="Downloads folder often accumulates large forgotten files",
            estimated_benefit="Potentially several GB recovered",
            risk_level=OptimizationRiskLevel.LOW,
        ),
        build_optimization_candidate(
            DeviceArea.PACKAGE_CACHES,
            OptimizationActionType.CLEAR_CACHE,
            "Clear package manager caches",
            target="npm, pip, yarn, cargo caches",
            reason="Package caches grow over time and are safe to clear",
            estimated_benefit="1-10 GB recovered",
            risk_level=OptimizationRiskLevel.LOW,
            approval_required=OptimizationApprovalRequirement.BATCH_APPROVAL_ALLOWED,
        ),
        build_optimization_candidate(
            DeviceArea.DOCKER_VM,
            OptimizationActionType.RECOMMEND,
            "Prune unused Docker images",
            target="Docker system",
            reason="Unused Docker images accumulate and consume significant space",
            estimated_benefit="5-30 GB recovered",
            risk_level=OptimizationRiskLevel.MEDIUM,
        ),
        build_optimization_candidate(
            DeviceArea.STARTUP_ITEMS,
            OptimizationActionType.DISABLE_STARTUP,
            "Review and disable non-essential startup items",
            reason="Unnecessary startup items slow boot and consume background resources",
            estimated_benefit="Faster boot, less background resource usage",
            risk_level=OptimizationRiskLevel.LOW,
        ),
        build_optimization_candidate(
            DeviceArea.DEVELOPMENT_ENVIRONMENT,
            OptimizationActionType.CLEAR_CACHE,
            "Remove node_modules from inactive projects",
            reason="Each node_modules is 200-500 MB and regenerates with npm install",
            estimated_benefit="2-20 GB recovered",
            risk_level=OptimizationRiskLevel.LOW,
            approval_required=OptimizationApprovalRequirement.BATCH_APPROVAL_ALLOWED,
        ),
        build_optimization_candidate(
            DeviceArea.THERMALS,
            OptimizationActionType.RECOMMEND,
            "Check cooling and clean dust from vents",
            reason="Dust buildup is the most common cause of thermal throttling",
            estimated_benefit="Reduced throttling, quieter fans, longer hardware life",
            risk_level=OptimizationRiskLevel.NONE,
            approval_required=OptimizationApprovalRequirement.NONE,
        ),
        build_optimization_candidate(
            DeviceArea.BACKUPS,
            OptimizationActionType.RECOMMEND,
            "Verify backup status and freshness",
            reason="Optimization is safer when backups exist — verify before making changes",
            estimated_benefit="Data safety net for all future optimization actions",
            risk_level=OptimizationRiskLevel.NONE,
            approval_required=OptimizationApprovalRequirement.NONE,
        ),
    ]


def build_workstation_optimization_report(
    node_id: str = "local_pc",
) -> WorkstationOptimizationReport:
    baseline = build_onboarding_workstation_baseline_plan(node_id)
    literacy = build_default_device_literacy_explanations()
    candidates = build_onboarding_optimization_recommendations()

    high_risk = [
        "Overclocking — never automatic, requires expert review",
        "Undervolting — requires stability testing and approval",
        "BIOS/UEFI changes — expert review required",
        "Driver changes — explicit approval and rollback plan required",
        "Docker volumes — may contain irreplaceable data",
    ]

    preserved = [
        "System-critical files and processes",
        "Credentials, secrets, and private keys",
        "Business-critical and legal/financial documents",
        "Unknown files and processes",
        "Security tools and password managers",
        "Source code repositories",
        "Databases and persistent volumes",
    ]

    next_steps = [
        "Run actual device baseline audit (future phase — not Phase 87C)",
        "Present device literacy explanations during onboarding",
        "Generate personalized optimization recommendations based on real audit data",
        "Implement governed execution for approved cleanup actions (future phase)",
    ]

    return WorkstationOptimizationReport(
        report_id=_ws_id("rpt"),
        node_id=node_id,
        baseline_plan=baseline,
        device_literacy_items=literacy,
        optimization_candidates=candidates,
        high_risk_items=high_risk,
        preserved_items=preserved,
        warnings=["This is a planning-only report — no real device was scanned"],
        next_steps=next_steps,
    )
