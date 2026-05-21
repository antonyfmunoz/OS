"""Phase 87B ingestion views — UI-safe read models for onboarding/ingestion data.

No sensitive data exposed. No execution. No mutation.

Advisory/planning only. No scraping. No API calls. No account connections.
No file reading. No memory promotion. No execution.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class IngestionSourceView:
    source_id: str = ""
    name: str = ""
    source_class: str = ""
    platform: str = ""
    onboarding_tier: str = ""
    priority: str = ""
    sensitivity: str = ""
    status: str = ""
    modality_count: int = 0
    access_method_count: int = 0
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "source_id": self.source_id,
            "name": self.name,
            "source_class": self.source_class,
            "platform": self.platform,
            "onboarding_tier": self.onboarding_tier,
            "priority": self.priority,
            "sensitivity": self.sensitivity,
            "status": self.status,
            "modality_count": self.modality_count,
            "access_method_count": self.access_method_count,
            "metadata": self.metadata,
        }


@dataclass
class ToolStackProfileView:
    profile_id: str = ""
    user_label: str = ""
    confirmed_count: int = 0
    coverage_pct: float = 0.0
    gap_count: int = 0
    gaps: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "profile_id": self.profile_id,
            "user_label": self.user_label,
            "confirmed_count": self.confirmed_count,
            "coverage_pct": round(self.coverage_pct, 1),
            "gap_count": self.gap_count,
            "gaps": self.gaps,
            "metadata": self.metadata,
        }


@dataclass
class OnboardingPlanView:
    plan_id: str = ""
    tier: str = ""
    name: str = ""
    source_count: int = 0
    prerequisite_count: int = 0
    estimated_effort: str = ""
    warning_count: int = 0
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "plan_id": self.plan_id,
            "tier": self.tier,
            "name": self.name,
            "source_count": self.source_count,
            "prerequisite_count": self.prerequisite_count,
            "estimated_effort": self.estimated_effort,
            "warning_count": self.warning_count,
            "metadata": self.metadata,
        }


@dataclass
class SourceRouteView:
    route_id: str = ""
    source_name: str = ""
    recommended_node: str = ""
    affinity: str = ""
    access_method: str = ""
    sensitivity: str = ""
    warning_count: int = 0
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "route_id": self.route_id,
            "source_name": self.source_name,
            "recommended_node": self.recommended_node,
            "affinity": self.affinity,
            "access_method": self.access_method,
            "sensitivity": self.sensitivity,
            "warning_count": self.warning_count,
            "metadata": self.metadata,
        }


@dataclass
class ReviewPolicyView:
    policy_id: str = ""
    name: str = ""
    source_class: str = ""
    sensitivity: str = ""
    review_requirement: str = ""
    promotion_policy: str = ""
    confidence_threshold: float = 0.0
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "policy_id": self.policy_id,
            "name": self.name,
            "source_class": self.source_class,
            "sensitivity": self.sensitivity,
            "review_requirement": self.review_requirement,
            "promotion_policy": self.promotion_policy,
            "confidence_threshold": round(self.confidence_threshold, 4),
            "metadata": self.metadata,
        }


@dataclass
class IngestionDashboardView:
    total_sources: int = 0
    sources_by_tier: dict[str, int] = field(default_factory=dict)
    sources_by_status: dict[str, int] = field(default_factory=dict)
    sources_by_sensitivity: dict[str, int] = field(default_factory=dict)
    financial_source_count: int = 0
    local_only_source_count: int = 0
    review_policy_count: int = 0
    warnings: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "total_sources": self.total_sources,
            "sources_by_tier": self.sources_by_tier,
            "sources_by_status": self.sources_by_status,
            "sources_by_sensitivity": self.sources_by_sensitivity,
            "financial_source_count": self.financial_source_count,
            "local_only_source_count": self.local_only_source_count,
            "review_policy_count": self.review_policy_count,
            "warnings": self.warnings,
            "metadata": self.metadata,
        }


# ─── Converters ─────────────────────────────────────────────────────


def source_to_view(source: Any) -> IngestionSourceView:
    return IngestionSourceView(
        source_id=getattr(source, "source_id", ""),
        name=getattr(source, "name", ""),
        source_class=_enum_val(getattr(source, "source_class", "")),
        platform=_enum_val(getattr(source, "platform", "")),
        onboarding_tier=_enum_val(getattr(source, "onboarding_tier", "")),
        priority=_enum_val(getattr(source, "priority", "")),
        sensitivity=_enum_val(getattr(source, "sensitivity", "")),
        status=_enum_val(getattr(source, "status", "")),
        modality_count=len(getattr(source, "modalities", [])),
        access_method_count=len(getattr(source, "access_methods", [])),
    )


def tool_stack_to_view(profile: Any) -> ToolStackProfileView:
    confirmed = getattr(profile, "confirmed_platforms", [])
    coverage = getattr(profile, "source_class_coverage", {})
    gaps = getattr(profile, "gaps", [])
    from umh.ingestion.source_classes import list_source_classes

    total_classes = len(list_source_classes())
    coverage_pct = round(len(coverage) / total_classes * 100, 1) if total_classes else 0

    return ToolStackProfileView(
        profile_id=getattr(profile, "profile_id", ""),
        user_label=getattr(profile, "user_label", ""),
        confirmed_count=len(confirmed),
        coverage_pct=coverage_pct,
        gap_count=len(gaps),
        gaps=gaps,
    )


def onboarding_plan_to_view(plan: Any) -> OnboardingPlanView:
    return OnboardingPlanView(
        plan_id=getattr(plan, "plan_id", ""),
        tier=_enum_val(getattr(plan, "tier", "")),
        name=getattr(plan, "name", ""),
        source_count=len(getattr(plan, "sources", [])),
        prerequisite_count=len(getattr(plan, "prerequisites", [])),
        estimated_effort=getattr(plan, "estimated_effort", ""),
        warning_count=len(getattr(plan, "warnings", [])),
    )


def source_route_to_view(route: Any) -> SourceRouteView:
    return SourceRouteView(
        route_id=getattr(route, "route_id", ""),
        source_name=_enum_val(getattr(route, "platform", "")),
        recommended_node=getattr(route, "recommended_node_type", ""),
        affinity=getattr(route, "source_affinity", ""),
        access_method=_enum_val(getattr(route, "access_method", "")),
        sensitivity=_enum_val(getattr(route, "sensitivity", "")),
        warning_count=len(getattr(route, "warnings", [])),
    )


def review_policy_to_view(policy: Any) -> ReviewPolicyView:
    return ReviewPolicyView(
        policy_id=getattr(policy, "policy_id", ""),
        name=getattr(policy, "name", ""),
        source_class=_enum_val(getattr(policy, "source_class", "")),
        sensitivity=_enum_val(getattr(policy, "sensitivity", "")),
        review_requirement=_enum_val(getattr(policy, "review_requirement", "")),
        promotion_policy=_enum_val(getattr(policy, "promotion_policy", "")),
        confidence_threshold=getattr(policy, "confidence_threshold", 0.0),
    )


def build_ingestion_dashboard_view(
    sources: list[Any] | None = None,
    review_policies: list[Any] | None = None,
    warnings: list[str] | None = None,
) -> IngestionDashboardView:
    all_sources = sources or []

    by_tier: dict[str, int] = {}
    by_status: dict[str, int] = {}
    by_sensitivity: dict[str, int] = {}
    financial_count = 0
    local_count = 0

    for s in all_sources:
        tier_val = _enum_val(getattr(s, "onboarding_tier", "unknown"))
        by_tier[tier_val] = by_tier.get(tier_val, 0) + 1

        status_val = _enum_val(getattr(s, "status", "unknown"))
        by_status[status_val] = by_status.get(status_val, 0) + 1

        sens_val = _enum_val(getattr(s, "sensitivity", "unknown"))
        by_sensitivity[sens_val] = by_sensitivity.get(sens_val, 0) + 1

        if sens_val == "financial":
            financial_count += 1

        access_methods = getattr(s, "access_methods", [])
        from umh.ingestion.contracts import AccessMethod

        if any(
            a
            in (
                AccessMethod.BROWSER_SESSION,
                AccessMethod.LOCAL_FILESYSTEM,
                AccessMethod.SCREEN_CAPTURE,
            )
            for a in access_methods
        ):
            local_count += 1

    return IngestionDashboardView(
        total_sources=len(all_sources),
        sources_by_tier=by_tier,
        sources_by_status=by_status,
        sources_by_sensitivity=by_sensitivity,
        financial_source_count=financial_count,
        local_only_source_count=local_count,
        review_policy_count=len(review_policies or []),
        warnings=warnings or [],
    )


def _enum_val(v: Any) -> str:
    if hasattr(v, "value"):
        return v.value
    return str(v)
