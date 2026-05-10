"""Phase 87B tool-stack discovery — user's tool-stack profile building.

Builds a tool-stack profile from declared or discovered platforms.
Identifies coverage gaps per source class. Tool-agnostic — does not
assume any specific user's tooling.

Advisory/planning only. No scraping. No API calls. No account connections.
No file reading. No memory promotion. No execution.
"""

from __future__ import annotations

from typing import Any

from umh.ingestion.contracts import (
    PlatformType,
    SourceClass,
    ToolStackProfile,
    _ingest_id,
    normalize_platform_type,
)
from umh.ingestion.source_classes import (
    get_class_for_platform,
    get_platforms_for_class,
    list_source_classes,
)


def build_tool_stack_profile(
    declared_platforms: list[str | PlatformType],
    user_label: str = "",
) -> ToolStackProfile:
    confirmed: list[PlatformType] = []
    for p in declared_platforms:
        pt = normalize_platform_type(p) if isinstance(p, str) else p
        if pt != PlatformType.UNKNOWN:
            confirmed.append(pt)

    coverage: dict[str, list[str]] = {}
    for sc in list_source_classes():
        class_platforms = get_platforms_for_class(sc)
        matched = [p.value for p in confirmed if p in class_platforms]
        if matched:
            coverage[sc.value] = matched

    gaps = identify_coverage_gaps(confirmed)

    return ToolStackProfile(
        profile_id=_ingest_id("tsp"),
        user_label=user_label,
        discovered_platforms=[],
        confirmed_platforms=confirmed,
        rejected_platforms=[],
        source_class_coverage=coverage,
        gaps=gaps,
    )


def identify_coverage_gaps(
    platforms: list[PlatformType],
) -> list[str]:
    covered_classes: set[SourceClass] = set()
    for p in platforms:
        sc = get_class_for_platform(p)
        if sc != SourceClass.UNKNOWN:
            covered_classes.add(sc)

    gaps: list[str] = []
    essential = [
        SourceClass.EMAIL,
        SourceClass.CALENDAR,
        SourceClass.NOTE_TAKING,
        SourceClass.CODE_REPOSITORY,
        SourceClass.MESSAGING,
        SourceClass.CLOUD_STORAGE,
    ]
    for sc in essential:
        if sc not in covered_classes:
            gaps.append(f"No platform declared for {sc.value}")

    return gaps


def suggest_platforms_for_gap(
    source_class: SourceClass,
) -> list[PlatformType]:
    return get_platforms_for_class(source_class)


def get_source_class_coverage_summary(
    profile: ToolStackProfile,
) -> dict[str, Any]:
    all_classes = list_source_classes()
    covered = list(profile.source_class_coverage.keys())
    uncovered = [sc.value for sc in all_classes if sc.value not in covered]

    return {
        "total_classes": len(all_classes),
        "covered_classes": len(covered),
        "uncovered_classes": len(uncovered),
        "coverage_pct": round(len(covered) / len(all_classes) * 100, 1) if all_classes else 0,
        "covered": covered,
        "uncovered": uncovered,
        "gaps": profile.gaps,
    }
