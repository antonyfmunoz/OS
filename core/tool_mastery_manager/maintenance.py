"""Maintenance flows for the Tool Mastery Manager.

Thin compositions over coverage + ensure. These exist so the ongoing
upkeep path (refresh stale, repair invalid, audit all) is a first-class
Manager surface rather than a tangle of shell commands.
"""

from __future__ import annotations

from .backlog import build_backlog
from .coverage import evaluate_coverage
from .discovery import discover_all
from .ensure import ensure_mastery
from .models import CoverageStatus


def refresh_stale(*, dry_run: bool = False) -> list[dict]:
    """Queue a refresh action for every STALE tool currently discoverable."""
    entries = build_backlog()
    out: list[dict] = []
    for e in entries:
        if e.report.status is not CoverageStatus.STALE:
            continue
        res = ensure_mastery(e.ref.slug, dry_run=dry_run)
        out.append(res.to_dict())
    return out


def repair_invalid(*, dry_run: bool = False) -> list[dict]:
    """Queue a repair action for every INVALID or PARTIAL tool."""
    entries = build_backlog()
    out: list[dict] = []
    for e in entries:
        if e.report.status not in (CoverageStatus.INVALID, CoverageStatus.PARTIAL):
            continue
        res = ensure_mastery(e.ref.slug, dry_run=dry_run)
        out.append(res.to_dict())
    return out


def audit_all() -> dict:
    """Return a full coverage snapshot across all discovered tools.

    Unlike build_backlog(), this includes READY entries so callers can
    see the entire picture at once. Useful for CLI `status`-style
    commands and for the audit report.
    """
    refs = discover_all()
    reports = [evaluate_coverage(r.slug) for r in refs]
    counts: dict[str, int] = {}
    for r in reports:
        counts[r.status.value] = counts.get(r.status.value, 0) + 1
    return {
        "total": len(reports),
        "counts": counts,
        "reports": [
            {"tool": ref.to_dict(), "coverage": rep.to_dict()}
            for ref, rep in zip(refs, reports)
        ],
    }
