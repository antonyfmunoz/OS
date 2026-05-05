"""Unified coverage evaluator for the Tool Mastery Manager.

This is the composition layer. It calls existing TME utilities and
collapses their per-concern verdicts into a single CoverageStatus per
tool. No verification or staleness logic is duplicated here — if the
underlying rules change in _tme_common / verify_tool_skill /
check_skill_staleness, this evaluator picks up the change for free.

Status ladder:

    READY     — skill exists, verifier passes, staleness = fresh
    MISSING   — no directory at all under skills/tools/<slug>
    INVALID   — exists but verifier fails with hard failures
    STALE     — exists, verifier passes, staleness = stale or missing_date
    PARTIAL   — exists, verifier passes with warnings OR staleness = near_stale

Tiebreaks (most severe wins):
    MISSING > INVALID > STALE > PARTIAL > READY
"""

from __future__ import annotations

import sys
from datetime import date

sys.path.insert(0, "/opt/OS")

from scripts._tme_common import load_skill  # noqa: E402
from scripts.check_skill_staleness import _assess  # noqa: E402
from scripts.verify_tool_skill import _check  # noqa: E402

from .models import CoverageReport, CoverageStatus
from .paths import SKILLS_TOOLS_DIR


def evaluate_coverage(slug: str, *, today: date | None = None) -> CoverageReport:
    """Classify a single tool slug into one CoverageStatus.

    Composes the three existing TME internals:
        - _tme_common.load_skill   — filesystem + frontmatter
        - verify_tool_skill._check  — 9-point verifier
        - check_skill_staleness._assess — freshness window
    """
    today = today or date.today()

    rec = load_skill(slug)
    tool_dir = SKILLS_TOOLS_DIR / slug
    exists_dir = tool_dir.is_dir()
    exists_skill_md = rec.skill_md.is_file()

    # --- MISSING ---
    if not exists_dir or not exists_skill_md:
        return CoverageReport(
            slug=slug,
            status=CoverageStatus.MISSING,
            reasons=["no SKILL.md at skills/tools/{}/SKILL.md".format(slug)],
            exists_on_disk=exists_dir,
        )

    # --- Verifier (composes all 9 checks) ---
    v = _check(rec)

    # --- Staleness (only meaningful if the record loaded enough to read freshness) ---
    s = _assess(rec, today)

    report = CoverageReport(
        slug=slug,
        status=CoverageStatus.READY,  # optimistic; downgraded below
        verifier_failures=list(v.failures),
        verifier_warnings=list(v.warnings),
        staleness_status=s.status,
        age_days=s.age_days,
        last_researched=s.last_researched,
        speed_category=s.speed,
        exists_on_disk=True,
    )

    # --- INVALID: verifier has hard failures ---
    if v.failures:
        report.status = CoverageStatus.INVALID
        report.reasons.append(
            f"verifier reported {len(v.failures)} hard failure(s)"
        )
        return report

    # --- STALE: verifier passes, staleness says stale/missing_date ---
    if s.status in ("stale", "missing_date"):
        report.status = CoverageStatus.STALE
        if s.status == "stale":
            report.reasons.append(
                f"last_researched {s.last_researched} is {s.age_days}d old "
                f"(window={s.window}d, speed={s.speed})"
            )
        else:
            report.reasons.append("last_researched date missing from frontmatter")
        return report

    # --- PARTIAL: verifier passes but has warnings, or staleness = near_stale ---
    if v.warnings or s.status == "near_stale":
        report.status = CoverageStatus.PARTIAL
        if v.warnings:
            report.reasons.append(
                f"verifier reported {len(v.warnings)} warning(s)"
            )
        if s.status == "near_stale":
            report.reasons.append(
                f"near freshness window ({s.age_days}d / {s.age_days and s.age_days}d)"
            )
        return report

    # --- READY ---
    report.reasons.append("verifier clean, within freshness window")
    return report


def evaluate_many(slugs: list[str], *, today: date | None = None) -> list[CoverageReport]:
    """Evaluate a batch of slugs. Order preserved."""
    today = today or date.today()
    return [evaluate_coverage(s, today=today) for s in slugs]
