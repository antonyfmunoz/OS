#!/usr/bin/env python3
"""TME Quality Audit — checks content depth, not just structure.

Validates that tool skills meet creator-level quality standards:
- Frontmatter completeness (10 required fields)
- Section presence (19 sections in best_practices.md)
- Content depth markers (code examples, exact numbers, community sources)
- EOS Usage Patterns section
- Gotchas from real production experience

Usage:
    python3 scripts/tme_quality_audit.py              # audit all
    python3 scripts/tme_quality_audit.py stripe        # audit one
    python3 scripts/tme_quality_audit.py --all         # audit all (explicit)
    python3 scripts/tme_quality_audit.py --quiet       # summary only
    python3 scripts/tme_quality_audit.py --json        # machine-readable
    python3 scripts/tme_quality_audit.py --speed fast  # audit one category
"""
import os
import re
import sys
import json
import argparse

sys.path.insert(0, os.environ.get("UMH_ROOT") or os.environ.get("OS_ROOT") or os.environ.get("EOS_ROOT") or "/opt/OS")

from scripts._tme_common import (
    load_all_skills,
    load_skill,
    all_skill_slugs,
    section_present,
    REQUIRED_BP_SECTIONS,
)

REQUIRED_FM = [
    "name", "description", "version", "source_url",
    "last_researched", "api_version", "speed_category",
    "trigger", "effort", "context",
]


def audit_skill(slug: str) -> dict:
    rec = load_skill(slug)
    result = {
        "tool": slug,
        "speed": rec.speed_category,
        "issues": [],
        "warnings": [],
        "scores": {},
    }

    if not rec.exists:
        result["issues"].append("SKILL.md missing")
        result["grade"] = "F"
        return result

    # --- Frontmatter completeness ---
    fm_score = sum(1 for k in REQUIRED_FM if k in rec.frontmatter)
    for k in REQUIRED_FM:
        if k not in rec.frontmatter:
            result["issues"].append(f"frontmatter missing {k}")
    result["scores"]["frontmatter"] = f"{fm_score}/{len(REQUIRED_FM)}"

    # --- SKILL.md sections ---
    if not section_present(rec.skill_body, "Gotchas"):
        result["issues"].append("SKILL.md missing Gotchas section")

    # --- best_practices.md ---
    if not rec.best_practices_md or not rec.bp_body:
        result["issues"].append("best_practices.md missing")
        result["grade"] = "D"
        return result

    bp = rec.bp_body
    bp_len = len(bp)

    sections_found = sum(1 for s in REQUIRED_BP_SECTIONS if section_present(bp, s))
    for s in REQUIRED_BP_SECTIONS:
        if not section_present(bp, s):
            result["warnings"].append(f"BP missing section: {s}")
    result["scores"]["sections"] = f"{sections_found}/{len(REQUIRED_BP_SECTIONS)}"

    # --- Content depth markers ---
    depth_score = 0
    max_depth = 6

    # 1. Code examples (``` blocks)
    code_blocks = len(re.findall(r"```", bp)) // 2
    if code_blocks >= 5:
        depth_score += 1
    else:
        result["warnings"].append(f"only {code_blocks} code blocks (want 5+)")

    # 2. Exact numbers (digits in rate limit / timeout / size context)
    number_patterns = re.findall(
        r"\b\d+(?:,\d{3})*\s*(?:req|request|per|sec|min|hour|day|ms|MB|KB|GB|byte|char|limit)",
        bp, re.IGNORECASE,
    )
    if len(number_patterns) >= 5:
        depth_score += 1
    else:
        result["warnings"].append(f"only {len(number_patterns)} exact numbers (want 5+)")

    # 3. Gotcha items (real production gotchas)
    gotcha_match = re.search(
        r"(?:## (?:\d+\.\s*)?(?:Gotcha|EOS.*Gotcha))(.*?)(?=\n## |\Z)",
        bp, re.DOTALL | re.IGNORECASE,
    )
    gotcha_section = gotcha_match.group(1) if gotcha_match else ""
    gotcha_items = len(re.findall(r"^[-*] ", gotcha_section, re.MULTILINE))
    if gotcha_items >= 3:
        depth_score += 1
    else:
        result["warnings"].append(f"only {gotcha_items} gotcha items (want 3+)")

    # 4. EOS Usage Patterns section
    has_eos = bool(re.search(r"EOS\s+Usage\s+Pattern", bp, re.IGNORECASE))
    if has_eos:
        depth_score += 1
    else:
        result["warnings"].append("missing EOS Usage Patterns section")

    # 5. Anti-pattern substance
    anti_match = re.search(
        r"## (?:\d+\.\s*)?Anti.?Pattern(.*?)(?=\n## |\Z)",
        bp, re.DOTALL | re.IGNORECASE,
    )
    anti_section = anti_match.group(1) if anti_match else ""
    has_contrast = any(
        w in anti_section.lower()
        for w in ["wrong", "bad", "instead", "don't", "avoid", "never", "incorrect"]
    )
    if has_contrast and len(anti_section) > 200:
        depth_score += 1
    else:
        result["warnings"].append("anti-patterns thin or missing wrong→right examples")

    # 6. Community/external sources referenced
    community_markers = len(re.findall(
        r"github\.com|stackoverflow|reddit|hacker\s*news|community|forum|"
        r"issue\s*#?\d+|production|real.world|blog\..*\.com",
        bp, re.IGNORECASE,
    ))
    if community_markers >= 2:
        depth_score += 1
    else:
        result["warnings"].append(f"only {community_markers} community source refs (want 2+)")

    result["scores"]["depth"] = f"{depth_score}/{max_depth}"

    # --- Reference files ---
    refs_dir = os.path.join(rec.path, "references")
    ref_count = 0
    if os.path.isdir(refs_dir):
        ref_count = len([f for f in os.listdir(refs_dir) if f.endswith(".md")])
    result["scores"]["refs"] = ref_count
    result["scores"]["bp_chars"] = bp_len

    # --- Grade ---
    n_issues = len(result["issues"])
    if fm_score == 10 and sections_found >= 17 and depth_score >= 5 and n_issues == 0:
        result["grade"] = "A"
    elif fm_score >= 8 and sections_found >= 15 and depth_score >= 4 and n_issues == 0:
        result["grade"] = "B"
    elif fm_score >= 6 and sections_found >= 12 and depth_score >= 2:
        result["grade"] = "C"
    elif sections_found >= 8:
        result["grade"] = "D"
    else:
        result["grade"] = "F"

    return result


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("tools", nargs="*", help="specific tool(s) to audit")
    ap.add_argument("--all", action="store_true", help="audit all skills")
    ap.add_argument("--quiet", action="store_true", help="summary only")
    ap.add_argument("--json", action="store_true", help="machine-readable")
    ap.add_argument("--speed", choices=["fast", "medium", "stable", "slow"],
                    help="filter to one speed_category")
    args = ap.parse_args()

    if args.tools and args.tools[0] != "all":
        slugs = args.tools
    else:
        slugs = all_skill_slugs()

    if args.speed:
        all_recs = load_all_skills()
        slugs = [r.slug for r in all_recs if r.speed_category == args.speed]

    results = [audit_skill(s) for s in slugs]

    if args.json:
        print(json.dumps(results, indent=2))
        return 0

    grades = {}
    for r in results:
        g = r.get("grade", "?")
        grades[g] = grades.get(g, 0) + 1

    if not args.quiet:
        for r in results:
            grade = r.get("grade", "?")
            scores = r.get("scores", {})
            depth = scores.get("depth", "?")
            fm = scores.get("frontmatter", "?")
            bp_chars = scores.get("bp_chars", 0)
            n_issues = len(r["issues"])
            n_warns = len(r["warnings"])
            marker = "!!" if grade in ("D", "F") else "  "
            print(
                f"{marker}{r['tool']:30s} grade={grade}  "
                f"fm={fm}  depth={depth}  "
                f"bp={bp_chars:6d}  issues={n_issues}  warns={n_warns}"
            )

    print(f"\n=== GRADE DISTRIBUTION ({len(results)} skills) ===")
    for g in ["A", "B", "C", "D", "F"]:
        count = grades.get(g, 0)
        bar = "#" * count
        print(f"  {g}: {count:3d}  {bar}")

    a_count = grades.get("A", 0)
    b_count = grades.get("B", 0)
    passing = a_count + b_count
    total = len(results)
    pct = 100 * passing // total if total else 0
    print(f"\nPassing (A+B): {passing}/{total} ({pct}%)")

    failing = grades.get("D", 0) + grades.get("F", 0)
    if failing:
        print(f"\nCRITICAL — {failing} skills graded D/F need attention:")
        for r in results:
            if r.get("grade") in ("D", "F"):
                print(f"  {r['tool']}: {'; '.join(r['issues'][:3])}")

    return 1 if failing else 0


if __name__ == "__main__":
    sys.exit(main())
