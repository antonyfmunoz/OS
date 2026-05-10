#!/usr/bin/env python3
"""Phase 8 batch measurement — full re-extraction.

For each of the 8 benchmark tools:
1. Loads the latest research artifact JSON + raw captures from disk
2. Re-runs extraction with *current* Phase 8 code on every OK raw capture
3. Merges new patterns into the loaded artifact
4. Runs author mapping + drafting to count sourced sections
5. Reports per-tool and aggregate coverage

This correctly measures Phase 8 impact: same raw captures, new extraction code.
"""

import json
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import os
sys.path.insert(0, os.environ.get("UMH_ROOT") or os.environ.get("OS_ROOT") or os.environ.get("EOS_ROOT") or "/opt/OS")

from core.tool_mastery_author_agent.loader import (
    LoadedArtifact,
    RawCapture,
    load_artifact,
    sanitize_text,
)
from core.tool_mastery_author_agent.mapping import (
    _split_prose_blocks,
    _strip_html,
    map_sections,
)
from core.tool_mastery_author_agent.draft import build_drafts
from core.tool_mastery_research_agent.artifact import TME_SECTIONS
from core.tool_mastery_research_agent.extraction import (
    extract_from_source,
    merge_extractions,
)

TOOLS = [
    "notion", "stripe", "posthog", "drizzle_orm",
    "remotion", "higgsfield", "clo3d", "shadcn_ui",
]

LOG_ROOT = Path("/opt/OS/logs/tool_mastery_research")


@dataclass
class ToolResult:
    tool: str
    artifact_path: str
    sources_ok: int
    sources_planned: int
    total_bytes: int
    sourced: int
    uncovered: int
    sourced_sections: list[str] = field(default_factory=list)
    uncovered_sections: list[str] = field(default_factory=list)
    grounding: dict[str, int] = field(default_factory=dict)
    pattern_count: int = 0
    pattern_kinds: dict[str, int] = field(default_factory=dict)
    error: str = ""


def find_latest_artifact(tool: str) -> Path | None:
    tool_dir = LOG_ROOT / tool
    if not tool_dir.is_dir():
        return None
    best_path = None
    best_time = ""
    for run_dir in tool_dir.iterdir():
        if not run_dir.is_dir():
            continue
        artifact = run_dir / "research_artifact.json"
        if artifact.is_file():
            dirname = run_dir.name
            if dirname > best_time:
                best_time = dirname
                best_path = artifact
    return best_path


def _load_raw_captures_from_disk(run_dir: Path) -> list[RawCapture]:
    """Fallback: load raw captures directly from raw/ directory on disk.

    Used when artifact JSON has empty fetch_results but raw files exist.
    """
    raw_dir = run_dir / "raw"
    if not raw_dir.is_dir():
        return []
    captures = []
    for raw_file in sorted(raw_dir.iterdir()):
        if not raw_file.is_file():
            continue
        try:
            text = raw_file.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        # Infer URL from filename pattern: NN_host_path.txt
        name = raw_file.stem
        parts = name.split("_", 1)
        url_hint = parts[1] if len(parts) > 1 else name
        captures.append(RawCapture(
            url=url_hint.replace("_", "/"),
            tier="unknown",
            label=name,
            raw_path=str(raw_file),
            text=text,
            bytes=raw_file.stat().st_size,
        ))
    return captures


def re_extract_patterns(
    loaded: LoadedArtifact,
    fallback_raw: list[RawCapture] | None = None,
) -> dict[str, list[dict[str, Any]]]:
    """Re-run Phase 5+7+8 extraction on all raw captures using current code."""
    captures = loaded.raw_captures if loaded.raw_captures else (fallback_raw or [])
    extractions = []
    for cap in captures:
        raw_text = cap.text
        sanitized = sanitize_text(raw_text)
        plain = _strip_html(sanitized)
        blocks = _split_prose_blocks(plain)
        prose_chars = sum(len(b) for b in blocks)

        extraction = extract_from_source(
            url=cap.url,
            raw_text=raw_text,
            sanitized_text=sanitized,
            plain_text=plain,
            prose_chars=prose_chars,
            rendered_by_headless=False,
        )
        extractions.append(extraction)

    return merge_extractions(extractions)


def measure_tool(tool: str) -> ToolResult:
    artifact_path = find_latest_artifact(tool)
    if not artifact_path:
        return ToolResult(
            tool=tool, artifact_path="", sources_ok=0, sources_planned=0,
            total_bytes=0, sourced=0, uncovered=19, error="no artifact found"
        )

    try:
        loaded = load_artifact(artifact_path)
    except Exception as e:
        return ToolResult(
            tool=tool, artifact_path=str(artifact_path), sources_ok=0,
            sources_planned=0, total_bytes=0, sourced=0, uncovered=19,
            error=f"load failed: {e}"
        )

    # Read artifact metadata
    data = json.loads(artifact_path.read_text())
    artifact_data = data.get("artifact", {})
    plan_data = data.get("plan", {})
    sources_planned = len(plan_data.get("sources", []))
    fetch_results = artifact_data.get("fetch_results", [])
    sources_ok = sum(1 for r in fetch_results if r.get("status") == "ok")
    total_bytes = sum(
        r.get("bytes_fetched", 0)
        for r in fetch_results if r.get("status") == "ok"
    )

    # Load raw captures from disk as fallback when artifact has no fetch_results
    fallback_raw: list[RawCapture] | None = None
    if not loaded.has_any_source:
        fallback_raw = _load_raw_captures_from_disk(artifact_path.parent)
        if not fallback_raw:
            return ToolResult(
                tool=tool, artifact_path=str(artifact_path),
                sources_ok=sources_ok, sources_planned=sources_planned,
                total_bytes=total_bytes, sourced=0, uncovered=19,
                grounding={"uncovered": 19},
            )
        # Update source counts from disk
        sources_ok = len(fallback_raw)
        total_bytes = sum(c.bytes for c in fallback_raw)

    # If we loaded fallback raw captures, inject them into the artifact
    # so map_sections can do keyword matching on them
    if fallback_raw and not loaded.raw_captures:
        loaded.raw_captures = fallback_raw

    # Re-extract patterns with current Phase 8 code
    new_patterns = re_extract_patterns(loaded, fallback_raw)

    # Count pattern kinds
    kind_counts: dict[str, int] = {}
    total_pattern_count = 0
    for bucket_name, pats in new_patterns.items():
        for p in pats:
            kind = p.get("kind", "unknown")
            kind_counts[kind] = kind_counts.get(kind, 0) + 1
            total_pattern_count += 1

    # Inject new patterns into loaded artifact
    loaded.extracted_patterns = new_patterns

    # Run mapping + drafting with fresh patterns
    evidence = map_sections(loaded)
    drafts = build_drafts(evidence)

    sourced_sections = [d.section for d in drafts if d.sourced]
    uncovered_sections = [d.section for d in drafts if not d.sourced]

    grounding: dict[str, int] = {}
    draft_pattern_total = 0
    for d in drafts:
        grounding[d.grounding] = grounding.get(d.grounding, 0) + 1
        draft_pattern_total += d.pattern_count

    return ToolResult(
        tool=tool,
        artifact_path=str(artifact_path),
        sources_ok=sources_ok,
        sources_planned=sources_planned,
        total_bytes=total_bytes,
        sourced=len(sourced_sections),
        uncovered=len(uncovered_sections),
        sourced_sections=sourced_sections,
        uncovered_sections=uncovered_sections,
        grounding=grounding,
        pattern_count=total_pattern_count,
        pattern_kinds=kind_counts,
    )


def main():
    results: list[ToolResult] = []
    for tool in TOOLS:
        print(f"Measuring {tool}...", end=" ", flush=True)
        r = measure_tool(tool)
        if r.error:
            print(f"ERROR: {r.error}")
        else:
            print(f"{r.sourced}/19 sourced, {r.pattern_count} patterns extracted")
        results.append(r)

    total_sourced = sum(r.sourced for r in results)
    total_slots = len(TOOLS) * 19
    total_uncovered = total_slots - total_sourced

    print("\n" + "=" * 70)
    print(f"OVERALL: {total_sourced}/{total_slots} = {100*total_sourced/total_slots:.1f}%")
    print("=" * 70)

    # Per-tool table
    print(f"\n{'Tool':<15} {'Sourced':<8} {'Uncov':<7} {'Cov%':<8} {'Pats':<6} {'OK Srcs':<8} {'Bytes':<10}")
    print("-" * 70)
    for r in sorted(results, key=lambda x: x.sourced, reverse=True):
        cov = f"{100*r.sourced/19:.1f}%"
        if r.total_bytes >= 1_000_000:
            bytes_str = f"{r.total_bytes/1_000_000:.1f}M"
        elif r.total_bytes > 0:
            bytes_str = f"{r.total_bytes/1024:.0f}K"
        else:
            bytes_str = "0"
        print(f"{r.tool:<15} {r.sourced:<8} {r.uncovered:<7} {cov:<8} {r.pattern_count:<6} {r.sources_ok:<8} {bytes_str:<10}")

    # Per-section coverage
    print(f"\n{'Section':<55} {'Count':<6} {'Tools'}")
    print("-" * 90)
    section_counts: dict[str, int] = {s: 0 for s in TME_SECTIONS}
    section_tools: dict[str, list[str]] = {s: [] for s in TME_SECTIONS}
    for r in results:
        for s in r.sourced_sections:
            section_counts[s] = section_counts.get(s, 0) + 1
            section_tools[s] = section_tools.get(s, []) + [r.tool]
    for s in TME_SECTIONS:
        count = section_counts[s]
        tools = ", ".join(section_tools[s]) if section_tools[s] else "—"
        print(f"{s:<55} {count}/8   {tools}")

    # Grounding breakdown
    print("\nGrounding breakdown (all slots):")
    agg_grounding: dict[str, int] = {}
    for r in results:
        for g, c in r.grounding.items():
            agg_grounding[g] = agg_grounding.get(g, 0) + c
    for g, c in sorted(agg_grounding.items(), key=lambda x: -x[1]):
        print(f"  {g}: {c} ({100*c/total_slots:.1f}%)")

    # Pattern kind breakdown
    print("\nPattern kind totals (across all tools):")
    agg_kinds: dict[str, int] = {}
    for r in results:
        for k, c in r.pattern_kinds.items():
            agg_kinds[k] = agg_kinds.get(k, 0) + c
    for k, c in sorted(agg_kinds.items(), key=lambda x: -x[1]):
        tools_with = [r.tool for r in results if k in r.pattern_kinds]
        print(f"  {k}: {c} ({', '.join(tools_with)})")

    # Write JSON
    output = {
        "date": "2026-04-09",
        "phase": "Phase 8 — HTML Structure Preservation (full re-extraction)",
        "total_sourced": total_sourced,
        "total_slots": total_slots,
        "coverage_pct": round(100 * total_sourced / total_slots, 1),
        "tools": [
            {
                "tool": r.tool,
                "sourced": r.sourced,
                "uncovered": r.uncovered,
                "coverage_pct": round(100 * r.sourced / 19, 1),
                "sourced_sections": r.sourced_sections,
                "uncovered_sections": r.uncovered_sections,
                "grounding": r.grounding,
                "pattern_count": r.pattern_count,
                "pattern_kinds": r.pattern_kinds,
                "sources_ok": r.sources_ok,
                "sources_planned": r.sources_planned,
                "total_bytes": r.total_bytes,
                "artifact_path": r.artifact_path,
                "error": r.error,
            }
            for r in results
        ],
        "section_coverage": {s: section_counts[s] for s in TME_SECTIONS},
        "aggregate_grounding": agg_grounding,
        "aggregate_pattern_kinds": agg_kinds,
    }
    out_path = Path("/opt/OS/logs/tool_mastery_research/phase8_batch_results.json")
    out_path.write_text(json.dumps(output, indent=2))
    print(f"\nResults written to {out_path}")


if __name__ == "__main__":
    main()
