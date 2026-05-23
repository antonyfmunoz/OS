"""Backlog / bootstrap flow.

`backlog()` runs full discovery + coverage evaluation and returns the
prioritised worklist of non-READY tools. `bootstrap()` is the fresh-
environment path: it calls `backlog()` then invokes `ensure_mastery`
on every non-READY item.

The priority order mirrors the severity ladder in models.CoverageStatus:

    MISSING > INVALID > STALE > PARTIAL

Ties are broken by slug, alphabetical, for determinism.

Reports are written to /opt/OS/logs/tool_mastery_manager/ — both a
human-readable markdown file and a JSON artifact with the full
coverage reports. This gives the installer/operator a durable
checkpoint without blowing up the Control Plane log.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable

from .coverage import evaluate_coverage
from .discovery import discover_all
from .ensure import ensure_mastery
from .models import CoverageReport, CoverageStatus, EnsureResult, ToolRef
from .paths import BACKLOG_DIR

_PRIORITY = {
    CoverageStatus.MISSING: 0,
    CoverageStatus.INVALID: 1,
    CoverageStatus.STALE: 2,
    CoverageStatus.PARTIAL: 3,
    CoverageStatus.READY: 4,
}


@dataclass
class BacklogEntry:
    ref: ToolRef
    report: CoverageReport

    def to_dict(self) -> dict:
        return {
            "tool": self.ref.to_dict(),
            "coverage": self.report.to_dict(),
        }


def _iter_discovered(explicit: Iterable[str] | None = None) -> list[ToolRef]:
    return discover_all(explicit=explicit)


def build_backlog(
    *,
    explicit: Iterable[str] | None = None,
    include_ready: bool = False,
) -> list[BacklogEntry]:
    """Return every discovered tool with its CoverageReport, sorted by priority.

    Excludes READY entries by default — "backlog" means "work to do",
    and returning 80+ READY tools every call is just noise.
    """
    refs = _iter_discovered(explicit)
    entries: list[BacklogEntry] = []
    for ref in refs:
        report = evaluate_coverage(ref.slug)
        if not include_ready and report.status is CoverageStatus.READY:
            continue
        entries.append(BacklogEntry(ref=ref, report=report))
    entries.sort(key=lambda e: (_PRIORITY[e.report.status], e.ref.slug))
    return entries


def _write_report(entries: list[BacklogEntry], kind: str) -> dict[str, str]:
    """Write markdown + JSON artifacts. Returns {'md': path, 'json': path}."""
    BACKLOG_DIR.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H-%M-%SZ")
    md_path = BACKLOG_DIR / f"{kind}-{stamp}.md"
    json_path = BACKLOG_DIR / f"{kind}-{stamp}.json"

    # counts
    counts: dict[str, int] = {}
    for e in entries:
        counts[e.report.status.value] = counts.get(e.report.status.value, 0) + 1

    lines = [
        f"# Tool Mastery Manager — {kind} report",
        "",
        f"_Generated: {stamp}_",
        "",
        f"**{len(entries)} non-ready tool(s).** "
        + ", ".join(f"{k}={v}" for k, v in sorted(counts.items())),
        "",
        "| Priority | Status | Slug | Sources | Reason |",
        "|---|---|---|---|---|",
    ]
    for e in entries:
        reason = (e.report.reasons[0] if e.report.reasons else "").replace("|", "\\|")
        src = ",".join(s.value for s in e.ref.sources)
        lines.append(
            f"| {_PRIORITY[e.report.status]} | {e.report.status.value} | "
            f"`{e.ref.slug}` | {src} | {reason} |"
        )
    md_path.write_text("\n".join(lines), encoding="utf-8")

    json_path.write_text(
        json.dumps(
            {
                "kind": kind,
                "generated_at": stamp,
                "counts": counts,
                "entries": [e.to_dict() for e in entries],
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    return {"md": str(md_path), "json": str(json_path)}


def backlog_report(
    *,
    explicit: Iterable[str] | None = None,
    write_artifacts: bool = True,
) -> dict:
    """Run backlog + optionally persist a report.

    Returns a dict with the counts, entries (as dicts), and artifact
    paths (when persisted). Suitable for printing or JSON emission.
    """
    entries = build_backlog(explicit=explicit)
    artifacts = _write_report(entries, "backlog") if write_artifacts else {}
    return {
        "total": len(entries),
        "counts": {
            s.value: sum(1 for e in entries if e.report.status is s)
            for s in CoverageStatus
            if s is not CoverageStatus.READY
        },
        "entries": [e.to_dict() for e in entries],
        "artifacts": artifacts,
    }


def bootstrap(
    *,
    explicit: Iterable[str] | None = None,
    dry_run: bool = False,
) -> dict:
    """Fresh-environment flow: backlog → ensure_mastery on each non-ready tool.

    Every ensure call is routed through the Control Plane. In dry_run
    mode nothing is scaffolded or queued — the result is purely a plan.
    """
    entries = build_backlog(explicit=explicit)
    results: list[EnsureResult] = []
    for e in entries:
        res = ensure_mastery(e.ref.slug, dry_run=dry_run)
        results.append(res)

    # Persist a bootstrap report alongside the backlog one so the
    # installer has an audit trail of what was queued.
    BACKLOG_DIR.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H-%M-%SZ")
    out_path = BACKLOG_DIR / f"bootstrap-{stamp}.json"
    payload = {
        "kind": "bootstrap",
        "generated_at": stamp,
        "dry_run": dry_run,
        "total_considered": len(entries),
        "results": [r.to_dict() for r in results],
    }
    out_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    return {
        "total_considered": len(entries),
        "dry_run": dry_run,
        "queued": sum(1 for r in results if r.action_id),
        "scaffolded": sum(1 for r in results if r.scaffolded),
        "artifact": str(out_path),
        "results": [r.to_dict() for r in results],
    }
