#!/usr/bin/env python3
"""
check_skill_staleness.py — Tool Mastery Engine staleness audit.

Compares each skill's `last_researched` date against the freshness
window for its `speed_category` (fast=30d, medium=60d, stable=90d).
Reports STALE, NEAR_STALE (>= 80% of window), MISSING_DATE, or FRESH.

Usage:
    python3 scripts/check_skill_staleness.py --all
    python3 scripts/check_skill_staleness.py --skill notion
    python3 scripts/check_skill_staleness.py --all --markdown [> report.md]
    python3 scripts/check_skill_staleness.py --all --json
    python3 scripts/check_skill_staleness.py --all --only stale

Exit codes:
    0 — no stale skills
    1 — at least one stale or missing-date skill
"""
from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass
from datetime import date

import os
sys.path.insert(0, os.environ.get("UMH_ROOT") or os.environ.get("OS_ROOT") or os.environ.get("EOS_ROOT") or "/opt/OS")

from scripts._tme_common import (  # noqa: E402
    NEAR_STALE_FRACTION,
    SkillRecord,
    all_skill_slugs,
    days_since,
    freshness_window,
    load_skill,
)

STATUS_FRESH = "fresh"
STATUS_NEAR = "near_stale"
STATUS_STALE = "stale"
STATUS_MISSING = "missing_date"


@dataclass
class StalenessRow:
    slug: str
    status: str
    speed: str
    window: int
    age_days: int | None
    last_researched: str | None

    def to_dict(self) -> dict:
        return {
            "slug": self.slug,
            "status": self.status,
            "speed_category": self.speed,
            "window_days": self.window,
            "age_days": self.age_days,
            "last_researched": self.last_researched,
        }


def _assess(rec: SkillRecord, today: date) -> StalenessRow:
    window = freshness_window(rec.speed_category)
    lr = rec.last_researched
    if lr is None:
        return StalenessRow(
            slug=rec.slug,
            status=STATUS_MISSING,
            speed=rec.speed_category,
            window=window,
            age_days=None,
            last_researched=None,
        )
    age = days_since(lr, today)
    if age > window:
        status = STATUS_STALE
    elif age >= int(window * NEAR_STALE_FRACTION):
        status = STATUS_NEAR
    else:
        status = STATUS_FRESH
    return StalenessRow(
        slug=rec.slug,
        status=status,
        speed=rec.speed_category,
        window=window,
        age_days=age,
        last_researched=lr.isoformat(),
    )


def _render_text(rows: list[StalenessRow]) -> None:
    order = {STATUS_STALE: 0, STATUS_MISSING: 1, STATUS_NEAR: 2, STATUS_FRESH: 3}
    for r in sorted(rows, key=lambda x: (order[x.status], x.slug)):
        age_txt = f"{r.age_days}d" if r.age_days is not None else "—"
        print(
            f"[{r.status.upper():12s}] {r.slug:30s} "
            f"speed={r.speed:7s} window={r.window}d age={age_txt} "
            f"researched={r.last_researched or '—'}"
        )
    print("---")
    counts = {s: 0 for s in (STATUS_FRESH, STATUS_NEAR, STATUS_STALE, STATUS_MISSING)}
    for r in rows:
        counts[r.status] += 1
    print(
        f"fresh={counts[STATUS_FRESH]} near_stale={counts[STATUS_NEAR]} "
        f"stale={counts[STATUS_STALE]} missing_date={counts[STATUS_MISSING]} "
        f"total={len(rows)}"
    )


def _render_markdown(rows: list[StalenessRow], today: date) -> None:
    order = {STATUS_STALE: 0, STATUS_MISSING: 1, STATUS_NEAR: 2, STATUS_FRESH: 3}
    print(f"# Tool Mastery Engine — Staleness Report\n")
    print(f"_Generated: {today.isoformat()}_\n")
    counts = {s: 0 for s in (STATUS_FRESH, STATUS_NEAR, STATUS_STALE, STATUS_MISSING)}
    for r in rows:
        counts[r.status] += 1
    print(
        f"**{len(rows)} skills** — {counts[STATUS_FRESH]} fresh, "
        f"{counts[STATUS_NEAR]} near-stale, **{counts[STATUS_STALE]} stale**, "
        f"{counts[STATUS_MISSING]} missing date\n"
    )
    print("| Status | Skill | Speed | Window | Age | Last Researched |")
    print("|---|---|---|---|---|---|")
    for r in sorted(rows, key=lambda x: (order[x.status], x.slug)):
        age_txt = f"{r.age_days}d" if r.age_days is not None else "—"
        print(
            f"| {r.status} | `{r.slug}` | {r.speed} | {r.window}d | "
            f"{age_txt} | {r.last_researched or '—'} |"
        )


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    group = ap.add_mutually_exclusive_group(required=True)
    group.add_argument("--all", action="store_true")
    group.add_argument("--skill", metavar="SLUG")
    out = ap.add_mutually_exclusive_group()
    out.add_argument("--markdown", action="store_true", help="render markdown report")
    out.add_argument("--json", action="store_true")
    ap.add_argument(
        "--only",
        choices=[STATUS_FRESH, STATUS_NEAR, STATUS_STALE, STATUS_MISSING],
        help="filter results",
    )
    args = ap.parse_args()

    today = date.today()
    slugs = all_skill_slugs() if args.all else [args.skill]
    rows = [_assess(load_skill(s), today) for s in slugs]
    if args.only:
        rows = [r for r in rows if r.status == args.only]

    if args.json:
        print(json.dumps([r.to_dict() for r in rows], indent=2))
    elif args.markdown:
        _render_markdown(rows, today)
    else:
        _render_text(rows)

    any_bad = any(r.status in (STATUS_STALE, STATUS_MISSING) for r in rows)
    return 1 if any_bad else 0


if __name__ == "__main__":
    sys.exit(main())
