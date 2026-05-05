"""Phase 88 KPI tracking — default KPIs for business and self-build tracks.

No execution. No mutation. No adapter calls. No LLM calls.
"""

from __future__ import annotations

from typing import Any

from umh.workflows.contracts import (
    KPIName,
    WorkflowKPIRecord,
    WorkflowStage,
    _wf_id,
)


_DEFAULT_TARGETS: dict[str, float] = {
    KPIName.POSTS_PUBLISHED.value: 1.0,
    KPIName.COMMENTS_GENERATED.value: 5.0,
    KPIName.DMS_OPENED.value: 10.0,
    KPIName.LEADS_CAPTURED.value: 2.0,
    KPIName.QUALIFIED_LEADS.value: 1.0,
    KPIName.CALLS_BOOKED.value: 0.5,
    KPIName.REVENUE_COLLECTED.value: 0.0,
    KPIName.OBJECTIONS_CAPTURED.value: 3.0,
    KPIName.FOLLOWUPS_SENT.value: 5.0,
    KPIName.MANUAL_HOURS_SPENT.value: 3.0,
    KPIName.BOTTLENECKS_FOUND.value: 1.0,
}


def build_default_kpis_for_first_workflow() -> list[WorkflowKPIRecord]:
    return [
        WorkflowKPIRecord(
            kpi_name=KPIName.POSTS_PUBLISHED,
            value=0.0,
            unit="count",
            stage=WorkflowStage.PUBLISHING,
        ),
        WorkflowKPIRecord(
            kpi_name=KPIName.COMMENTS_GENERATED,
            value=0.0,
            unit="count",
            stage=WorkflowStage.ENGAGEMENT_CAPTURE,
        ),
        WorkflowKPIRecord(
            kpi_name=KPIName.DMS_OPENED,
            value=0.0,
            unit="count",
            stage=WorkflowStage.DM_CONVERSATION,
        ),
        WorkflowKPIRecord(
            kpi_name=KPIName.LEADS_CAPTURED,
            value=0.0,
            unit="count",
            stage=WorkflowStage.LEAD_CAPTURE,
        ),
        WorkflowKPIRecord(
            kpi_name=KPIName.QUALIFIED_LEADS,
            value=0.0,
            unit="count",
            stage=WorkflowStage.QUALIFICATION,
        ),
        WorkflowKPIRecord(
            kpi_name=KPIName.CALLS_BOOKED,
            value=0.0,
            unit="count",
            stage=WorkflowStage.SALES_CONVERSATION,
        ),
        WorkflowKPIRecord(
            kpi_name=KPIName.REVENUE_COLLECTED,
            value=0.0,
            unit="usd",
            stage=WorkflowStage.CLOSE_PAYMENT,
        ),
        WorkflowKPIRecord(
            kpi_name=KPIName.OBJECTIONS_CAPTURED,
            value=0.0,
            unit="count",
            stage=WorkflowStage.ENGAGEMENT_CAPTURE,
        ),
        WorkflowKPIRecord(
            kpi_name=KPIName.FOLLOWUPS_SENT,
            value=0.0,
            unit="count",
            stage=WorkflowStage.DM_CONVERSATION,
        ),
        WorkflowKPIRecord(
            kpi_name=KPIName.MANUAL_HOURS_SPENT,
            value=0.0,
            unit="hours",
            stage=WorkflowStage.END_OF_DAY_REVIEW,
        ),
        WorkflowKPIRecord(
            kpi_name=KPIName.BOTTLENECKS_FOUND,
            value=0.0,
            unit="count",
            stage=WorkflowStage.END_OF_DAY_REVIEW,
        ),
    ]


def create_kpi_record(
    kpi_name: KPIName,
    value: float,
    unit: str = "count",
    stage: WorkflowStage = WorkflowStage.UNKNOWN,
    notes: str = "",
) -> WorkflowKPIRecord:
    return WorkflowKPIRecord(
        kpi_name=kpi_name,
        value=value,
        unit=unit,
        stage=stage,
        notes=notes,
    )


def validate_kpi_record(record: WorkflowKPIRecord) -> dict[str, Any]:
    warnings: list[str] = []
    if record.kpi_name == KPIName.UNKNOWN:
        warnings.append("KPI name is UNKNOWN")
    if record.value < 0:
        warnings.append(f"Negative KPI value: {record.value}")
    return {"valid": len(warnings) == 0, "warnings": warnings}


def summarize_kpis(records: list[WorkflowKPIRecord]) -> dict[str, Any]:
    summary: dict[str, float] = {}
    for r in records:
        name = r.kpi_name.value
        summary[name] = summary.get(name, 0.0) + r.value
    return {
        "kpi_count": len(records),
        "unique_kpis": len(summary),
        "totals": summary,
    }


def compare_kpis_to_targets(
    records: list[WorkflowKPIRecord],
    targets: dict[str, float] | None = None,
) -> dict[str, Any]:
    if targets is None:
        targets = dict(_DEFAULT_TARGETS)
    summary = summarize_kpis(records)
    totals = summary["totals"]
    comparisons: list[dict[str, Any]] = []
    for kpi_name, target_value in targets.items():
        actual = totals.get(kpi_name, 0.0)
        met = actual >= target_value if target_value > 0 else True
        comparisons.append(
            {
                "kpi": kpi_name,
                "target": target_value,
                "actual": actual,
                "met": met,
                "delta": actual - target_value,
            }
        )
    met_count = sum(1 for c in comparisons if c["met"])
    return {
        "total_kpis": len(comparisons),
        "met": met_count,
        "missed": len(comparisons) - met_count,
        "comparisons": comparisons,
    }


# ─── Self-Build KPIs ──────────────��─────────────────────────────────

_DEFAULT_SELF_BUILD_TARGETS: dict[str, float] = {
    KPIName.FILES_CHANGED.value: 1.0,
    KPIName.TESTS_ADDED.value: 1.0,
    KPIName.TESTS_PASSED.value: 1.0,
    KPIName.REGRESSION_STATUS.value: 1.0,
    KPIName.SAFETY_VIOLATIONS.value: 0.0,
    KPIName.PHASE_COMPLETION.value: 1.0,
    KPIName.ARCHITECTURE_DRIFT_FOUND.value: 0.0,
    KPIName.TEMPLATE_CANDIDATES_FOUND.value: 1.0,
}


def build_default_self_build_kpis() -> list[WorkflowKPIRecord]:
    return [
        WorkflowKPIRecord(
            kpi_name=KPIName.FILES_CHANGED,
            value=0.0,
            unit="count",
            stage=WorkflowStage.MANUAL_EXECUTION,
        ),
        WorkflowKPIRecord(
            kpi_name=KPIName.TESTS_ADDED,
            value=0.0,
            unit="count",
            stage=WorkflowStage.MANUAL_EXECUTION,
        ),
        WorkflowKPIRecord(
            kpi_name=KPIName.TESTS_PASSED,
            value=0.0,
            unit="count",
            stage=WorkflowStage.MANUAL_EXECUTION,
        ),
        WorkflowKPIRecord(
            kpi_name=KPIName.REGRESSION_STATUS,
            value=0.0,
            unit="bool",
            stage=WorkflowStage.MANUAL_EXECUTION,
        ),
        WorkflowKPIRecord(
            kpi_name=KPIName.SAFETY_VIOLATIONS,
            value=0.0,
            unit="count",
            stage=WorkflowStage.MANUAL_EXECUTION,
        ),
        WorkflowKPIRecord(
            kpi_name=KPIName.PHASE_COMPLETION,
            value=0.0,
            unit="bool",
            stage=WorkflowStage.REVIEW,
        ),
        WorkflowKPIRecord(
            kpi_name=KPIName.ARCHITECTURE_DRIFT_FOUND,
            value=0.0,
            unit="count",
            stage=WorkflowStage.REVIEW,
        ),
        WorkflowKPIRecord(
            kpi_name=KPIName.TEMPLATE_CANDIDATES_FOUND,
            value=0.0,
            unit="count",
            stage=WorkflowStage.TEMPLATE_CANDIDATE_EXTRACTION,
        ),
        WorkflowKPIRecord(
            kpi_name=KPIName.MANUAL_HOURS_SPENT,
            value=0.0,
            unit="hours",
            stage=WorkflowStage.REVIEW,
        ),
        WorkflowKPIRecord(
            kpi_name=KPIName.BOTTLENECKS_FOUND,
            value=0.0,
            unit="count",
            stage=WorkflowStage.REVIEW,
        ),
    ]
