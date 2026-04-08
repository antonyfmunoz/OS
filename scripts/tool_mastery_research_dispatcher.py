#!/usr/bin/env python3
"""Tool Mastery research dispatcher.

This is the target of Control Plane actions queued by the Tool Mastery
Manager. When the Manager decides a tool needs `research`, `refresh`,
or `repair` work, it enqueues a `run_script` action pointing at this
script with `--work-type <type> --tool <slug>`.

The dispatcher does NOT fabricate research. It prints a structured,
machine-readable next-steps plan. A human (or a research-capable
subagent) is expected to pick up the plan and execute the TME decision
tree at /opt/OS/skills/meta/tool_mastery_engine/SKILL.md.

Exit codes:
    0 — plan printed successfully
    2 — bad invocation
    3 — unknown tool slug (for --work-type refresh|repair the skill
        must already exist; we flag this as an honest failure rather
        than silently scaffold)

Usage:
    python3 scripts/tool_mastery_research_dispatcher.py \\
        --work-type research --tool slack

    python3 scripts/tool_mastery_research_dispatcher.py \\
        --work-type refresh --tool notion

    python3 scripts/tool_mastery_research_dispatcher.py \\
        --work-type repair --tool stripe
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, "/opt/OS")

from core.tool_mastery_manager.coverage import evaluate_coverage  # noqa: E402
from core.tool_mastery_manager.paths import SKILLS_TOOLS_DIR  # noqa: E402

VALID_WORK_TYPES = ("research", "refresh", "repair")

TME_DECISION_TREE = "/opt/OS/skills/meta/tool_mastery_engine/SKILL.md"
VERIFY_CMD = "python3 /opt/OS/scripts/verify_tool_skill.py --skill {slug}"
SYNC_CMD = "python3 /opt/OS/scripts/sync_skills_to_neon.py --skill {slug}"


def _plan_research(slug: str) -> dict:
    return {
        "ok": True,
        "work_type": "research",
        "tool": slug,
        "next_steps": [
            f"1. Open the scaffolded skill at {SKILLS_TOOLS_DIR / slug}/SKILL.md",
            f"2. Follow the TME decision tree at {TME_DECISION_TREE}",
            "3. Research the tool's official docs exhaustively (all 19 sections)",
            f"4. Fill SKILL.md + references/best_practices.md",
            "5. Update frontmatter last_researched to today",
            f"6. Verify: {VERIFY_CMD.format(slug=slug)}",
            f"7. Sync: {SYNC_CMD.format(slug=slug)}",
        ],
        "note": (
            "This dispatcher does not auto-fabricate mastery. Research is "
            "deliberately a manual step so the Gotchas sections remain "
            "grounded in real-world behaviour."
        ),
    }


def _plan_refresh(slug: str, report: dict) -> dict:
    return {
        "ok": True,
        "work_type": "refresh",
        "tool": slug,
        "current_status": report.get("status"),
        "age_days": report.get("age_days"),
        "last_researched": report.get("last_researched"),
        "next_steps": [
            f"1. Re-check official docs for {slug} — scan changelog + version notes",
            "2. Update SKILL.md + references/best_practices.md where docs have drifted",
            "3. Bump frontmatter last_researched to today",
            f"4. Verify: {VERIFY_CMD.format(slug=slug)}",
            f"5. Sync: {SYNC_CMD.format(slug=slug)}",
        ],
    }


def _plan_repair(slug: str, report: dict) -> dict:
    return {
        "ok": True,
        "work_type": "repair",
        "tool": slug,
        "current_status": report.get("status"),
        "verifier_failures": report.get("verifier_failures", []),
        "verifier_warnings": report.get("verifier_warnings", []),
        "next_steps": [
            "1. Read the verifier failures above — each one maps to a missing "
            "section, bad frontmatter key, or size violation",
            f"2. Edit skills/tools/{slug}/SKILL.md and "
            f"skills/tools/{slug}/references/best_practices.md",
            f"3. Verify: {VERIFY_CMD.format(slug=slug)}",
            f"4. Sync: {SYNC_CMD.format(slug=slug)}",
        ],
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--work-type", required=True, choices=VALID_WORK_TYPES)
    ap.add_argument("--tool", required=True)
    ap.add_argument("--json", action="store_true", help="emit JSON plan only")
    ap.add_argument(
        "--execute",
        action="store_true",
        help=(
            "invoke the Tool Mastery Research Agent to perform a real "
            "source-grounded research run instead of just printing the plan"
        ),
    )
    args = ap.parse_args()

    if args.execute:
        # delegate to the research agent; honest v1 — plans are replaced
        # by a real run with artifacts under logs/tool_mastery_research/
        from core.tool_mastery_research_agent.agent import run as _run_research
        from core.tool_mastery_research_agent.models import (
            ResearchMode,
            ResearchRequest,
        )

        request = ResearchRequest(
            tool_slug=args.tool.strip(),
            mode=ResearchMode(args.work_type),
            source_agent="tool_mastery_research_dispatcher",
        )
        result = _run_research(request)
        payload = result.to_dict()
        if args.json:
            print(json.dumps(payload, indent=2))
        else:
            print(
                f"=== Tool Mastery {args.work_type.upper()} EXECUTED: {args.tool} ==="
            )
            print(f"status : {payload['status']}")
            print(f"run_dir: {payload['run_dir']}")
            if payload.get("summary_path"):
                print(f"summary: {payload['summary_path']}")
            for step in payload.get("next_steps", []):
                print(f"  - {step}")
        # exit code: 0 if anything useful produced
        return 0 if payload["status"] in ("ok", "partial", "no_sources") else 1

    slug = args.tool.strip()
    if not slug:
        print("error: --tool is required", file=sys.stderr)
        return 2

    report = evaluate_coverage(slug).to_dict()

    if args.work_type == "research":
        plan = _plan_research(slug)
    elif args.work_type == "refresh":
        if not (SKILLS_TOOLS_DIR / slug / "SKILL.md").is_file():
            print(
                f"error: cannot refresh {slug!r} — no existing SKILL.md",
                file=sys.stderr,
            )
            return 3
        plan = _plan_refresh(slug, report)
    else:  # repair
        if not (SKILLS_TOOLS_DIR / slug / "SKILL.md").is_file():
            print(
                f"error: cannot repair {slug!r} — no existing SKILL.md",
                file=sys.stderr,
            )
            return 3
        plan = _plan_repair(slug, report)

    plan["coverage_report"] = report

    if args.json:
        print(json.dumps(plan, indent=2))
    else:
        print(f"=== Tool Mastery {args.work_type.upper()} plan: {slug} ===")
        print(f"current status: {report.get('status')}")
        print()
        print("Next steps:")
        for step in plan["next_steps"]:
            print(f"  {step}")
        if plan.get("verifier_failures"):
            print()
            print("Verifier failures to resolve:")
            for f in plan["verifier_failures"]:
                print(f"  - {f}")
        if plan.get("note"):
            print()
            print(f"NOTE: {plan['note']}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
