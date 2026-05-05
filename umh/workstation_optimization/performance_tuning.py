"""Phase 87C performance tuning — categories, risk assessment, and safe first steps.

Advisory/planning only. No real scanning. No overclocking. No settings changes.
"""

from __future__ import annotations

from typing import Any

from umh.workstation_optimization.contracts import (
    OptimizationApprovalRequirement,
    OptimizationRiskLevel,
    PerformanceTuningAdvisory,
    PerformanceTuningCategory,
    _ws_id,
)


_TUNING_CATEGORIES: list[dict[str, Any]] = [
    {
        "category": PerformanceTuningCategory.POWER_PROFILE,
        "summary": "Switch between Balanced, High Performance, and Power Saver modes",
        "risk": OptimizationRiskLevel.LOW,
        "approval": OptimizationApprovalRequirement.REVIEW_RECOMMENDED,
        "stability_test": False,
        "rollback": "Switch back to previous power profile",
    },
    {
        "category": PerformanceTuningCategory.THERMAL_MANAGEMENT,
        "summary": "Improve cooling through dust cleanup, airflow, thermal paste replacement",
        "risk": OptimizationRiskLevel.LOW,
        "approval": OptimizationApprovalRequirement.REVIEW_RECOMMENDED,
        "stability_test": False,
        "rollback": "Physical changes are reversible",
    },
    {
        "category": PerformanceTuningCategory.DRIVER_UPDATE,
        "summary": "Update GPU, chipset, and peripheral drivers through official channels",
        "risk": OptimizationRiskLevel.MEDIUM,
        "approval": OptimizationApprovalRequirement.EXPLICIT_APPROVAL,
        "stability_test": True,
        "rollback": "Rollback to previous driver version via device manager",
    },
    {
        "category": PerformanceTuningCategory.OVERCLOCKING,
        "summary": "Increase CPU/GPU/RAM clock speeds beyond factory defaults",
        "risk": OptimizationRiskLevel.HIGH,
        "approval": OptimizationApprovalRequirement.EXPERT_REVIEW_REQUIRED,
        "stability_test": True,
        "rollback": "Reset BIOS to defaults / CMOS clear",
    },
    {
        "category": PerformanceTuningCategory.UNDERVOLTING,
        "summary": "Reduce CPU/GPU voltage to lower temperatures and power consumption",
        "risk": OptimizationRiskLevel.HIGH,
        "approval": OptimizationApprovalRequirement.EXPERT_REVIEW_REQUIRED,
        "stability_test": True,
        "rollback": "Reset voltage to default in BIOS or software",
    },
    {
        "category": PerformanceTuningCategory.FAN_CURVE,
        "summary": "Modify fan speed curves for quieter operation or better cooling",
        "risk": OptimizationRiskLevel.MEDIUM,
        "approval": OptimizationApprovalRequirement.EXPLICIT_APPROVAL,
        "stability_test": True,
        "rollback": "Reset to default fan profile",
    },
    {
        "category": PerformanceTuningCategory.RAM_XMP_EXPO,
        "summary": "Enable XMP/EXPO profiles to run RAM at advertised speeds",
        "risk": OptimizationRiskLevel.MEDIUM,
        "approval": OptimizationApprovalRequirement.EXPLICIT_APPROVAL,
        "stability_test": True,
        "rollback": "Disable XMP/EXPO in BIOS",
    },
    {
        "category": PerformanceTuningCategory.GPU_PROFILE,
        "summary": "Adjust GPU power limits, clock offsets, or fan curves",
        "risk": OptimizationRiskLevel.MEDIUM,
        "approval": OptimizationApprovalRequirement.EXPLICIT_APPROVAL,
        "stability_test": True,
        "rollback": "Reset to default GPU profile",
    },
    {
        "category": PerformanceTuningCategory.STORAGE_UPGRADE,
        "summary": "Replace HDD with SSD or add additional storage",
        "risk": OptimizationRiskLevel.LOW,
        "approval": OptimizationApprovalRequirement.REVIEW_RECOMMENDED,
        "stability_test": False,
        "rollback": "Keep old drive as backup during transition",
    },
    {
        "category": PerformanceTuningCategory.RAM_UPGRADE,
        "summary": "Add or replace RAM modules for more capacity",
        "risk": OptimizationRiskLevel.LOW,
        "approval": OptimizationApprovalRequirement.REVIEW_RECOMMENDED,
        "stability_test": True,
        "rollback": "Reinstall original RAM if new modules fail",
    },
    {
        "category": PerformanceTuningCategory.CLEANING_COOLING,
        "summary": "Physical cleaning of dust, vents, fans, and thermal paste replacement",
        "risk": OptimizationRiskLevel.LOW,
        "approval": OptimizationApprovalRequirement.NONE,
        "stability_test": False,
        "rollback": "N/A — physical maintenance",
    },
]


def build_performance_tuning_categories() -> list[dict[str, Any]]:
    return [
        {
            "category": cat["category"].value,
            "summary": cat["summary"],
            "risk": cat["risk"].value,
            "approval": cat["approval"].value,
            "stability_test_required": cat["stability_test"],
            "rollback_plan": cat["rollback"],
        }
        for cat in _TUNING_CATEGORIES
    ]


def create_performance_tuning_advisory(
    category: PerformanceTuningCategory,
) -> PerformanceTuningAdvisory:
    for cat in _TUNING_CATEGORIES:
        if cat["category"] == category:
            return PerformanceTuningAdvisory(
                advisory_id=_ws_id("padv"),
                category=category,
                summary=cat["summary"],
                risks=_risks_for_category(category),
                prerequisites=_prerequisites_for_category(category),
                approval_required=cat["approval"],
                rollback_plan=cat["rollback"],
                stability_testing_required=cat["stability_test"],
                recommendation=_recommendation_for_category(category),
            )
    return PerformanceTuningAdvisory(
        advisory_id=_ws_id("padv"),
        category=category,
        summary="Unknown tuning category",
    )


def assess_performance_tuning_risk(category: PerformanceTuningCategory) -> str:
    high_risk = {PerformanceTuningCategory.OVERCLOCKING, PerformanceTuningCategory.UNDERVOLTING}
    medium_risk = {
        PerformanceTuningCategory.DRIVER_UPDATE,
        PerformanceTuningCategory.FAN_CURVE,
        PerformanceTuningCategory.RAM_XMP_EXPO,
        PerformanceTuningCategory.GPU_PROFILE,
    }
    if category in high_risk:
        return "high"
    if category in medium_risk:
        return "medium"
    return "low"


def explain_overclocking_policy() -> str:
    return (
        "Overclocking and undervolting are high-risk performance tuning actions. They modify hardware behavior "
        "at a fundamental level and can cause instability, data corruption, crashes, and hardware damage. "
        "UMH policy: (1) Never automatic — always requires explicit user approval and expert review. "
        "(2) Stability testing required after any change. (3) Temperature monitoring mandatory. "
        "(4) Rollback plan must exist (CMOS clear, BIOS reset). (5) Start conservative and increment slowly. "
        "(6) Safe first steps (cleanup, cooling, power profile) should always be tried before hardware tuning."
    )


def explain_safe_performance_first_steps() -> list[dict[str, str]]:
    return [
        {
            "step": "Free disk space",
            "risk": "low",
            "description": "Remove temp files, caches, old downloads to improve system responsiveness",
        },
        {
            "step": "Review startup items",
            "risk": "low",
            "description": "Disable non-essential startup apps to reduce boot time and background resource use",
        },
        {
            "step": "Close high-memory apps",
            "risk": "low",
            "description": "Close browser tabs and apps you are not actively using",
        },
        {
            "step": "Improve cooling and airflow",
            "risk": "low",
            "description": "Clean dust from vents, ensure laptop is on hard surface, check fan operation",
        },
        {
            "step": "Update through official channels",
            "risk": "medium",
            "description": "Update OS, drivers, and apps through official update mechanisms with caution",
        },
        {
            "step": "Use built-in power profile",
            "risk": "low",
            "description": "Switch to Balanced or High Performance profile as appropriate",
        },
        {
            "step": "Upgrade RAM or storage",
            "risk": "low",
            "description": "Consider hardware upgrade if consistently running out of RAM or disk space",
        },
        {
            "step": "Use external SSD for media",
            "risk": "low",
            "description": "Move large media archives to external SSD to free internal drive space",
        },
    ]


def _risks_for_category(cat: PerformanceTuningCategory) -> list[str]:
    if cat == PerformanceTuningCategory.OVERCLOCKING:
        return [
            "System instability under load",
            "Data corruption",
            "Reduced hardware lifespan",
            "Thermal damage",
            "Voided warranty",
        ]
    if cat == PerformanceTuningCategory.UNDERVOLTING:
        return [
            "Random crashes under specific workloads",
            "Data corruption during unstable operation",
            "Difficulty diagnosing intermittent failures",
        ]
    if cat == PerformanceTuningCategory.DRIVER_UPDATE:
        return [
            "Incompatible driver causing display issues",
            "Boot failure with incompatible chipset driver",
            "Performance regression",
        ]
    if cat == PerformanceTuningCategory.FAN_CURVE:
        return ["Insufficient cooling if fans set too low", "Excessive noise if fans set too high"]
    return ["Minimal risk for this category"]


def _prerequisites_for_category(cat: PerformanceTuningCategory) -> list[str]:
    if cat in (PerformanceTuningCategory.OVERCLOCKING, PerformanceTuningCategory.UNDERVOLTING):
        return [
            "Backup all critical data",
            "Know how to reset BIOS to defaults",
            "Have temperature monitoring software",
            "Understand your hardware specifications",
            "Adequate cooling system",
        ]
    if cat == PerformanceTuningCategory.DRIVER_UPDATE:
        return [
            "Know current driver version",
            "Create system restore point",
            "Download driver from official source",
        ]
    return []


def _recommendation_for_category(cat: PerformanceTuningCategory) -> str:
    if cat == PerformanceTuningCategory.OVERCLOCKING:
        return "Try safe first steps before overclocking. If proceeding: start conservative, stress test thoroughly, monitor temperatures continuously."
    if cat == PerformanceTuningCategory.UNDERVOLTING:
        return "Undervolting can improve thermals but requires per-workload stability testing. Start with small offsets."
    if cat == PerformanceTuningCategory.CLEANING_COOLING:
        return "Best first step for any performance concern. Low risk, immediate benefit."
    return "Proceed with appropriate caution and approval."
