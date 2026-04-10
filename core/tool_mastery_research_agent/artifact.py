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

from .extraction import (
    SourceExtraction,
    SourceType,
    extract_from_source,
    merge_extractions,
)
from .headless_fetcher import (
    RenderPassReport,
    is_likely_spa,
    render_low_signal_sources,
)
from .models import (
    FetchedSource,
    FetchStatus,
    ResearchArtifact,
    ResearchMode,
    SourcePlan,
)
from .source_quality import (
    SignalReport,
    classify_quality,
    measure_signal,
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


def _run_signal_pass(
    ok_sources: list[FetchedSource],
    *,
    run_dir: Path,
) -> tuple[list[SignalReport], set[str]]:
    """Measure prose density on every OK source.

    Returns (reports, low_signal_urls). Low-signal URLs are the set of
    OK-fetched URLs whose sanitized prose density didn't clear the bar —
    the agent uses this to demote them from OK to SKIPPED before they
    reach the Author Agent.
    """
    reports: list[SignalReport] = []
    low_signal: set[str] = set()
    for s in ok_sources:
        if not s.raw_path:
            continue
        raw_abs = run_dir / s.raw_path
        try:
            raw_bytes = raw_abs.read_bytes()
        except OSError as err:
            report = SignalReport(
                url=s.ref.url,
                raw_path=str(raw_abs),
                reason=f"read error: {err}",
            )
            reports.append(report)
            low_signal.add(s.ref.url)
            continue
        report = measure_signal(
            url=s.ref.url,
            raw_path=str(raw_abs),
            raw_bytes=raw_bytes,
        )
        reports.append(report)
        if not report.passes:
            low_signal.add(s.ref.url)
    return reports, low_signal


def _run_phase5_extraction(
    *,
    ok_sources: list[FetchedSource],
    run_dir: Path,
    signal_reports: list[SignalReport],
    rendered_urls: set[str],
) -> tuple[list[SourceExtraction], dict[str, str]]:
    """Classify every OK source and extract structured patterns.

    Returns ``(extractions, phase5_dropped)`` where ``phase5_dropped`` is a
    mapping ``{url: reason}`` for sources that the classifier labelled as
    UNKNOWN — these should be demoted to SKIPPED by the caller so the
    Author Agent never sees them.

    Lazy imports from the Author Agent are required because the Phase 5
    pipeline wants to share the exact same sanitiser + prose-block splitter
    the author uses, keeping research and author aligned on what "prose"
    means. Adding an import at the top of this module would create a
    research → author hard dependency for test collection.
    """

    from core.tool_mastery_author_agent.loader import sanitize_text
    from core.tool_mastery_author_agent.mapping import (
        _split_prose_blocks,
        _strip_html,
    )

    signal_by_url = {r.url: r for r in signal_reports}

    extractions: list[SourceExtraction] = []
    dropped: dict[str, str] = {}

    for s in ok_sources:
        if not s.raw_path:
            continue
        try:
            raw_bytes = (run_dir / s.raw_path).read_bytes()
        except OSError as err:
            dropped[s.ref.url] = f"read error: {err}"
            continue
        raw_text = raw_bytes.decode("utf-8", errors="replace")
        sanitized = sanitize_text(raw_text)
        plain = _strip_html(sanitized)
        # Reuse already-measured prose_chars when we have it — otherwise
        # recompute so the classifier still has a sensible denominator.
        sig = signal_by_url.get(s.ref.url)
        if sig is not None:
            prose_chars = sig.prose_chars
        else:
            blocks = _split_prose_blocks(plain)
            prose_chars = sum(len(b) for b in blocks)

        extraction = extract_from_source(
            url=s.ref.url,
            raw_text=raw_text,
            sanitized_text=sanitized,
            plain_text=plain,
            prose_chars=prose_chars,
            rendered_by_headless=s.ref.url in rendered_urls,
        )
        extractions.append(extraction)

        if extraction.source_type is SourceType.UNKNOWN:
            dropped[s.ref.url] = extraction.type_report.reason

    return extractions, dropped


def build_artifact(
    *,
    tool_slug: str,
    mode: ResearchMode,
    plan: SourcePlan,
    fetched: list[FetchedSource],
    run_dir: Path,
) -> ResearchArtifact:
    """Assemble a ResearchArtifact from the plan + fetch results.

    Post-fetch filtering: each OK source is measured for prose density.
    Sources that fail the density gate are demoted to SKIPPED with an
    explanatory error so the Author Agent never sees them.
    """

    ok = _ok_sources(fetched)
    reports, low_signal_urls = _run_signal_pass(ok, run_dir=run_dir)

    # Phase 4 — JS rendering unlock.
    # For OK sources the signal gate dropped, check whether the static
    # body looks like an SPA shell. If so, re-render with a headless
    # browser, rewrite the capture in-place, and re-measure signal on
    # just those URLs. All other sources are untouched.
    render_report: RenderPassReport | None = None
    if low_signal_urls:
        spa_candidates: list[FetchedSource] = []
        spa_reasons: dict[str, str] = {}
        for s in ok:
            if s.ref.url not in low_signal_urls or not s.raw_path:
                continue
            try:
                body = (run_dir / s.raw_path).read_bytes()
            except OSError:
                continue
            is_spa, reason = is_likely_spa(body)
            if is_spa:
                spa_candidates.append(s)
                spa_reasons[s.ref.url] = reason

        if spa_candidates:
            rendered_sources, render_report = render_low_signal_sources(
                candidates=spa_candidates,
                run_dir=run_dir,
            )
            # Replace the originals in `fetched` and `ok` with the
            # re-rendered copies so the downstream signal re-measure
            # reads the new body.
            rendered_by_url = {r.ref.url: r for r in rendered_sources}
            if rendered_by_url:
                fetched = [
                    rendered_by_url.get(s.ref.url, s)
                    if s.status is FetchStatus.OK
                    else s
                    for s in fetched
                ]
                ok = _ok_sources(fetched)
                # Re-run the signal pass on ONLY the re-rendered URLs so we
                # don't pay to re-read unchanged captures. Merge results
                # back into the existing report set.
                retry_ok = [s for s in ok if s.ref.url in rendered_by_url]
                retry_reports, retry_low = _run_signal_pass(retry_ok, run_dir=run_dir)
                retry_by_url = {r.url: r for r in retry_reports}
                merged_reports: list[SignalReport] = []
                for r in reports:
                    if r.url in retry_by_url:
                        merged = retry_by_url[r.url]
                        # Tag the reason so provenance is obvious in the summary.
                        merged.reason = f"[headless_render] {merged.reason}"
                        merged_reports.append(merged)
                    else:
                        merged_reports.append(r)
                reports = merged_reports
                # Recompute low_signal_urls from the merged pass.
                low_signal_urls = {r.url for r in reports if not r.passes}

    # Demote low-signal OK sources to SKIPPED in-place so the artifact
    # stays honest about what *actually* went forward.
    signal_reports_by_url = {r.url: r for r in reports}
    filtered_fetched: list[FetchedSource] = []
    for s in fetched:
        if s.status is FetchStatus.OK and s.ref.url in low_signal_urls:
            report = signal_reports_by_url.get(s.ref.url)
            reason = report.reason if report else "low-signal source"
            filtered_fetched.append(
                FetchedSource(
                    ref=s.ref,
                    status=FetchStatus.SKIPPED,
                    http_status=s.http_status,
                    content_type=s.content_type,
                    bytes=s.bytes,
                    raw_path=s.raw_path,
                    error=f"filtered by signal gate: {reason}",
                    fetched_at=s.fetched_at,
                )
            )
        else:
            filtered_fetched.append(s)

    ok_after_filter = _ok_sources(filtered_fetched)

    # Phase 5 — content-based classification + pattern extraction.
    # Runs on sources that survived the signal gate + headless render.
    # Anything classified UNKNOWN is demoted to SKIPPED so the Author
    # Agent never sees cookie-consent / marketing prose that happened
    # to clear the prose density bar.
    extractions, phase5_dropped = _run_phase5_extraction(
        ok_sources=ok_after_filter,
        run_dir=run_dir,
        signal_reports=reports,
        rendered_urls={
            r.url for r in reports if r.reason.startswith("[headless_render]")
        },
    )
    if phase5_dropped:
        new_filtered: list[FetchedSource] = []
        for s in filtered_fetched:
            if s.status is FetchStatus.OK and s.ref.url in phase5_dropped:
                reason = phase5_dropped[s.ref.url]
                new_filtered.append(
                    FetchedSource(
                        ref=s.ref,
                        status=FetchStatus.SKIPPED,
                        http_status=s.http_status,
                        content_type=s.content_type,
                        bytes=s.bytes,
                        raw_path=s.raw_path,
                        error=f"phase5 classifier: {reason}",
                        fetched_at=s.fetched_at,
                    )
                )
            else:
                new_filtered.append(s)
        filtered_fetched = new_filtered
        ok_after_filter = _ok_sources(filtered_fetched)

    any_source = bool(ok_after_filter)

    coverage = [
        {
            "section": section,
            "has_source": False,  # honest default — manual pass flips per-section
            "source_urls": [s.ref.url for s in ok_after_filter] if any_source else [],
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
    failed = [s for s in filtered_fetched if s.status not in (FetchStatus.OK,)]
    if failed:
        notes.append(
            f"{len(failed)}/{len(filtered_fetched)} source(s) did not pass the "
            "fetch+signal gate — see sources section"
        )
    if low_signal_urls:
        notes.append(
            f"signal gate dropped {len(low_signal_urls)} low-signal source(s) "
            "before the Author Agent"
        )
    if render_report is not None:
        notes.append(
            f"headless render pass: {render_report.note}"
            + (
                ""
                if render_report.playwright_available
                else " [playwright unavailable]"
            )
        )
        try:
            (run_dir / "headless_render.json").write_text(
                json.dumps(render_report.to_dict(), indent=2), encoding="utf-8"
            )
        except OSError:
            pass

    # Derive run-level quality flag from the reports of OK-fetched sources.
    # If there were no fetches at all, "low" is the honest default.
    quality = classify_quality(reports) if reports else "low"

    # Phase 5 artifact contributions — keep only extractions for sources
    # that actually survived to ok_after_filter (UNKNOWN ones were dropped
    # above, so filter the list down before serialising).
    surviving_urls = {s.ref.url for s in ok_after_filter}
    kept_extractions = [e for e in extractions if e.url in surviving_urls]
    extracted_patterns = merge_extractions(kept_extractions)
    source_type_reports = [e.type_report.to_dict() for e in extractions]

    total_patterns = (
        len(extracted_patterns["usage"])
        + len(extracted_patterns["api"])
        + len(extracted_patterns["workflows"])
    )
    if phase5_dropped:
        notes.append(
            f"phase5 classifier dropped {len(phase5_dropped)} source(s) as "
            "unknown content (no technical vocabulary / API markers)"
        )
    if total_patterns:
        notes.append(
            f"phase5 extracted {total_patterns} structured pattern(s): "
            f"{len(extracted_patterns['usage'])} usage, "
            f"{len(extracted_patterns['api'])} api, "
            f"{len(extracted_patterns['workflows'])} workflow(s)"
        )

    return ResearchArtifact(
        tool_slug=tool_slug,
        mode=mode,
        generated_at=_iso_now(),
        sources=filtered_fetched,
        section_coverage=coverage,
        notes=notes,
        quality=quality,
        signal_reports=[r.to_dict() for r in reports],
        source_type_reports=source_type_reports,
        extracted_patterns=extracted_patterns,
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
    lines.append(f"- quality: `{artifact.quality}`")
    lines.append("")

    if artifact.signal_reports:
        passing = sum(1 for r in artifact.signal_reports if r.get("passes"))
        lines.append("## Signal gate")
        lines.append("")
        lines.append(
            f"- passed: {passing}/{len(artifact.signal_reports)} "
            "fetched sources contained enough prose to hand off"
        )
        for r in artifact.signal_reports:
            mark = "ok" if r.get("passes") else "drop"
            lines.append(
                f"- [{mark}] {r.get('url')} — "
                f"prose_blocks={r.get('prose_blocks')}, "
                f"prose_chars={r.get('prose_chars')}, "
                f"reason={r.get('reason')}"
            )
        lines.append("")

    lines.append("## Discovery notes")
    if plan.notes:
        for n in plan.notes:
            lines.append(f"- {n}")
    else:
        lines.append("- (none)")
    lines.append("")

    if artifact.source_type_reports:
        lines.append("## Phase 5 — source type classification")
        lines.append("")
        for r in artifact.source_type_reports:
            lines.append(
                f"- **{r.get('source_type')}** ({r.get('confidence')}) — "
                f"{r.get('url')} — {r.get('reason')}"
            )
        lines.append("")

    patt = artifact.extracted_patterns or {}
    total_p = (
        len(patt.get("usage", []))
        + len(patt.get("api", []))
        + len(patt.get("workflows", []))
    )
    if total_p:
        lines.append("## Phase 5 — extracted patterns")
        lines.append("")
        for bucket in ("usage", "api", "workflows"):
            items = patt.get(bucket, [])
            if not items:
                continue
            lines.append(f"### {bucket} ({len(items)})")
            lines.append("")
            for p in items:
                lines.append(
                    f"- `{p.get('kind')}` "
                    f"(confidence={p.get('confidence')}, "
                    f"occurrences={p.get('occurrences')}, "
                    f"structured={p.get('structured')})"
                )
                lines.append(f"  - source: {p.get('url')}")
                excerpt = str(p.get("excerpt", "")).replace("\n", "\n    ")
                lines.append(f"  - excerpt:\n    {excerpt}")
                lines.append("")
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
