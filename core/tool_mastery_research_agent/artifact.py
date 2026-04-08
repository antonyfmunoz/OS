"""Artifact writer for the Tool Mastery Research Agent.

Takes a list of FetchedSource objects and produces three on-disk
artifacts:

    research_artifact.json  — machine-readable, full provenance
    summary.md              — human-readable overview
    sources.md              — flat source list with URLs + fetch status

All three live in the same per-run directory so a reviewer can diff
them against the TME decision tree by hand.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .models import (
    FetchedSource,
    FetchStatus,
    ResearchArtifact,
    ResearchMode,
    SourcePlan,
)


# Mirror the 19 section headers from TME research_protocol.md. These
# are not filled automatically — the coverage ledger only records
# whether *any* source was fetched successfully. Flipping "has_source"
# to True per-section remains a manual authoring responsibility.
TME_SECTIONS: list[str] = [
    # Tier 1 — Technical Mastery
    "Authentication",
    "Core Operations with Exact Signatures",
    "Pagination Patterns",
    "Rate Limits",
    "Error Codes and Recovery",
    "SDK Idioms",
    "Anti-Patterns",
    "Data Model",
    "Webhooks and Events",
    "Limits",
    "Cost Model",
    "Version Pinning",
    # Tier 2 — Creator Intelligence
    "Design Intent and Tradeoffs",
    "Problem-Solution Map and Hidden Capabilities",
    "Operational Behavior and Edge Cases",
    "Ecosystem Position and Composition",
    "Trajectory and Evolution",
    "Conceptual Model and Solution Recipes",
    "Industry Expert and Cutting-Edge Usage",
]


def _iso_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _ok_sources(sources: list[FetchedSource]) -> list[FetchedSource]:
    return [s for s in sources if s.status is FetchStatus.OK]


def build_artifact(
    *,
    tool_slug: str,
    mode: ResearchMode,
    plan: SourcePlan,
    fetched: list[FetchedSource],
) -> ResearchArtifact:
    """Assemble a ResearchArtifact from the plan + fetch results."""

    ok = _ok_sources(fetched)
    any_source = bool(ok)

    coverage = [
        {
            "section": section,
            "has_source": False,  # honest default — manual pass flips per-section
            "source_urls": [s.ref.url for s in ok] if any_source else [],
            "note": (
                "raw captures available; authoring pass must verify coverage"
                if any_source
                else "no successful fetches — section cannot be researched from this run"
            ),
        }
        for section in TME_SECTIONS
    ]

    notes: list[str] = list(plan.notes)
    if not fetched:
        notes.append("fetcher was not invoked — empty source plan")
    failed = [s for s in fetched if s.status is not FetchStatus.OK]
    if failed:
        notes.append(
            f"{len(failed)}/{len(fetched)} source(s) failed to fetch — see sources section"
        )

    return ResearchArtifact(
        tool_slug=tool_slug,
        mode=mode,
        generated_at=_iso_now(),
        sources=fetched,
        section_coverage=coverage,
        notes=notes,
    )


def _render_summary(artifact: ResearchArtifact, plan: SourcePlan) -> str:
    ok = _ok_sources(artifact.sources)
    total = len(artifact.sources)
    lines: list[str] = []
    lines.append(f"# Tool Mastery Research — {artifact.tool_slug}")
    lines.append("")
    lines.append(f"- mode: `{artifact.mode.value}`")
    lines.append(f"- generated_at: `{artifact.generated_at}`")
    lines.append(f"- sources_planned: {len(plan.sources)}")
    lines.append(f"- sources_fetched_ok: {len(ok)}/{total}")
    lines.append("")

    lines.append("## Discovery notes")
    if plan.notes:
        for n in plan.notes:
            lines.append(f"- {n}")
    else:
        lines.append("- (none)")
    lines.append("")

    lines.append("## Fetched sources")
    if not artifact.sources:
        lines.append("- (none)")
    else:
        for s in artifact.sources:
            status = s.status.value
            if s.status is FetchStatus.OK:
                lines.append(
                    f"- [{s.ref.tier.value}] **{s.ref.label or s.ref.url}** — "
                    f"ok ({s.bytes} B, `{s.content_type or 'unknown'}`) — {s.ref.url}"
                )
            else:
                lines.append(
                    f"- [{s.ref.tier.value}] **{s.ref.label or s.ref.url}** — "
                    f"{status}: {s.error} — {s.ref.url}"
                )
    lines.append("")

    lines.append("## TME section coverage (honest ledger)")
    lines.append("")
    lines.append(
        "The research agent does NOT auto-score sections against the 19 "
        "TME headers. Each row below is marked `has_source=false` until a "
        "human or later authoring pass verifies that the fetched material "
        "actually covers that section. This is intentional — the point is "
        "to remove fabrication, not add it."
    )
    lines.append("")
    lines.append("| Section | Tier | Has source? |")
    lines.append("|---|---|---|")
    for i, row in enumerate(artifact.section_coverage, start=1):
        tier = "Tier 1" if i <= 12 else "Tier 2"
        has = "yes" if row["has_source"] else "no"
        lines.append(f"| {row['section']} | {tier} | {has} |")
    lines.append("")

    if artifact.notes:
        lines.append("## Notes")
        for n in artifact.notes:
            lines.append(f"- {n}")
        lines.append("")

    lines.append("## Next steps (not executed automatically)")
    lines.append("")
    lines.append("1. Read the raw captures under `raw/`")
    lines.append(
        "2. Follow the TME decision tree at `skills/meta/tool_mastery_engine/SKILL.md`"
    )
    lines.append(
        "3. Fill `skills/tools/{slug}/SKILL.md` and `references/best_practices.md` "
        "section by section, quoting source material"
    )
    lines.append(
        "4. Update frontmatter `last_researched` to today and run "
        "`python3 scripts/verify_tool_skill.py --skill {slug}`"
    )
    lines.append("")
    return "\n".join(lines)


def _render_sources(artifact: ResearchArtifact) -> str:
    lines: list[str] = []
    lines.append(f"# Sources — {artifact.tool_slug}")
    lines.append("")
    if not artifact.sources:
        lines.append("(no sources)")
        return "\n".join(lines) + "\n"
    for i, s in enumerate(artifact.sources, start=1):
        lines.append(f"## {i}. {s.ref.label or s.ref.url}")
        lines.append("")
        lines.append(f"- url: {s.ref.url}")
        lines.append(f"- tier: {s.ref.tier.value}")
        lines.append(f"- origin: {s.ref.origin}")
        lines.append(f"- status: {s.status.value}")
        if s.http_status is not None:
            lines.append(f"- http_status: {s.http_status}")
        if s.content_type:
            lines.append(f"- content_type: {s.content_type}")
        if s.bytes:
            lines.append(f"- bytes: {s.bytes}")
        if s.raw_path:
            lines.append(f"- raw_path: {s.raw_path}")
        if s.error:
            lines.append(f"- error: {s.error}")
        lines.append(f"- fetched_at: {s.fetched_at}")
        lines.append("")
    return "\n".join(lines)


def write_artifact(
    run_dir: Path,
    artifact: ResearchArtifact,
    plan: SourcePlan,
) -> dict[str, str]:
    """Write the three artifact files to ``run_dir`` and return their paths."""

    run_dir.mkdir(parents=True, exist_ok=True)

    artifact_path = run_dir / "research_artifact.json"
    summary_path = run_dir / "summary.md"
    sources_path = run_dir / "sources.md"

    payload: dict[str, Any] = {
        "schema_version": 1,
        "plan": plan.to_dict(),
        "artifact": artifact.to_dict(),
    }
    artifact_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    summary_path.write_text(_render_summary(artifact, plan), encoding="utf-8")
    sources_path.write_text(_render_sources(artifact), encoding="utf-8")

    return {
        "artifact_path": str(artifact_path),
        "summary_path": str(summary_path),
        "sources_path": str(sources_path),
    }
