#!/usr/bin/env python3
"""
verify_tool_skill.py — Tool Mastery Engine verifier / linter.

Replaces the brittle ad-hoc regex checks from the in-skill verification
block with a real YAML-aware linter.

Checks each tool skill for:
  1. SKILL.md exists and is non-empty (>= 500 chars)
  2. Frontmatter parses as YAML
  3. Required frontmatter keys (name, description, last_researched, source_url)
  4. last_researched is a valid ISO date
  5. SKILL.md has Authentication + Gotchas sections
  6. references/best_practices.md exists and >= 2000 chars
  7. All 19 required best_practices sections present
  8. Canonical slug rule: directory name is snake_case and matches
     frontmatter `name` if that key is present
  9. No corrupt unicode replacement chars in the body

Usage:
    python3 scripts/verify_tool_skill.py --all
    python3 scripts/verify_tool_skill.py --skill notion
    python3 scripts/verify_tool_skill.py --all --json
    python3 scripts/verify_tool_skill.py --all --quiet  # only failures

Exit codes:
    0 — all verified skills passed
    1 — one or more failures
    2 — bad invocation (no matching skill)
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path

sys.path.insert(0, "/opt/OS")

from scripts._tme_common import (  # noqa: E402
    MIN_BP_CHARS,
    MIN_SKILL_CHARS,
    REQUIRED_BP_SECTIONS,
    REQUIRED_SKILL_SECTIONS,
    SkillRecord,
    all_skill_slugs,
    load_skill,
    section_present,
)

SNAKE_CASE_RE = re.compile(r"^[a-z0-9][a-z0-9_]*$")
REQUIRED_FM_KEYS = ("name", "description", "last_researched", "source_url")


@dataclass
class VerifyResult:
    slug: str
    passed: bool
    failures: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


def _check(rec: SkillRecord) -> VerifyResult:
    res = VerifyResult(slug=rec.slug, passed=True)

    # 1. SKILL.md presence + size
    if not rec.exists:
        res.failures.append("SKILL.md missing")
        res.passed = False
        return res
    raw = rec.skill_md.read_text(encoding="utf-8")
    if len(raw) < MIN_SKILL_CHARS:
        res.failures.append(f"SKILL.md too short: {len(raw)} < {MIN_SKILL_CHARS}")

    # 2. Frontmatter parse
    if rec.parse_error:
        res.failures.append(f"frontmatter: {rec.parse_error}")

    # 3. Required frontmatter keys
    for key in REQUIRED_FM_KEYS:
        if key not in rec.frontmatter:
            res.failures.append(f"frontmatter missing key: {key}")

    # 4. last_researched valid ISO date
    if "last_researched" in rec.frontmatter and rec.last_researched is None:
        res.failures.append(
            f"last_researched not a valid YYYY-MM-DD: "
            f"{rec.frontmatter.get('last_researched')!r}"
        )

    # 5. Required SKILL.md sections
    for section in REQUIRED_SKILL_SECTIONS:
        if not section_present(rec.skill_body, section):
            res.failures.append(f"SKILL.md missing section: ## {section}")

    # 6. best_practices.md presence + size
    if rec.best_practices_md is None or not rec.best_practices_md.is_file():
        res.failures.append("references/best_practices.md missing")
    else:
        bp_len = len(rec.bp_body)
        if bp_len < MIN_BP_CHARS:
            res.failures.append(
                f"best_practices.md too short: {bp_len} < {MIN_BP_CHARS}"
            )
        # 7. Required 19 sections
        for section in REQUIRED_BP_SECTIONS:
            if not section_present(rec.bp_body, section):
                res.failures.append(f"best_practices.md missing section: ## {section}")

    # 8. Canonical slug
    if not SNAKE_CASE_RE.match(rec.slug):
        res.failures.append(f"slug not snake_case: {rec.slug}")
    fm_name = rec.frontmatter.get("name")
    if fm_name and str(fm_name).strip() != rec.slug:
        res.warnings.append(
            f"frontmatter name={fm_name!r} != directory slug {rec.slug!r}"
        )

    # 9. Corruption check
    if "\ufffd" in raw:
        res.warnings.append("SKILL.md contains Unicode replacement chars (\\ufffd)")

    res.passed = not res.failures
    return res


def _render(results: list[VerifyResult], quiet: bool) -> None:
    for r in results:
        if r.passed and quiet:
            continue
        marker = "PASS" if r.passed else "FAIL"
        print(f"[{marker}] {r.slug}")
        for f in r.failures:
            print(f"   - {f}")
        for w in r.warnings:
            print(f"   ~ {w}")
    total = len(results)
    passed = sum(1 for r in results if r.passed)
    failed = total - passed
    print("---")
    print(f"Verified {total} skills: {passed} passed, {failed} failed")


def _render_json(results: list[VerifyResult]) -> None:
    payload = {
        "total": len(results),
        "passed": sum(1 for r in results if r.passed),
        "failed": sum(1 for r in results if not r.passed),
        "results": [
            {
                "slug": r.slug,
                "passed": r.passed,
                "failures": r.failures,
                "warnings": r.warnings,
            }
            for r in results
        ],
    }
    print(json.dumps(payload, indent=2))


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    group = ap.add_mutually_exclusive_group(required=True)
    group.add_argument("--all", action="store_true")
    group.add_argument("--skill", metavar="SLUG")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--quiet", action="store_true", help="only show failures")
    args = ap.parse_args()

    slugs = all_skill_slugs() if args.all else [args.skill]
    if not slugs or (args.skill and not (Path("/opt/OS/skills/tools") / args.skill).is_dir()):
        print(f"No such skill: {args.skill}", file=sys.stderr)
        return 2

    results = [_check(load_skill(s)) for s in slugs]
    if args.json:
        _render_json(results)
    else:
        _render(results, quiet=args.quiet)

    return 0 if all(r.passed for r in results) else 1


if __name__ == "__main__":
    sys.exit(main())
