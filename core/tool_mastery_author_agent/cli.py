"""CLI entry for the Tool Mastery Author Agent.

Usage:
    # Author from a specific research artifact
    python3 -m core.tool_mastery_author_agent \\
        --tool notion \\
        --artifact /opt/OS/logs/tool_mastery_research/notion/<stamp>/research_artifact.json

    # Consume the latest run for a tool
    python3 -m core.tool_mastery_author_agent --tool stitch --latest

    # Force rewrite of an existing human-authored skill (dangerous)
    python3 -m core.tool_mastery_author_agent --tool foo --latest --force-rewrite
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .agent import author
from .models import AuthorRequest
from .paths import RESEARCH_LOG_DIR


def _latest_artifact_for(tool_slug: str) -> Path | None:
    tool_dir = RESEARCH_LOG_DIR / tool_slug
    if not tool_dir.is_dir():
        return None
    runs = sorted(
        (d for d in tool_dir.iterdir() if d.is_dir()),
        key=lambda p: p.name,
        reverse=True,
    )
    for run in runs:
        candidate = run / "research_artifact.json"
        if candidate.is_file():
            return candidate
    return None


def build_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(
        prog="tool_mastery_author_agent",
        description="Author or refresh a tool skill from a source-grounded research artifact.",
    )
    ap.add_argument("--tool", required=True, help="tool slug (snake_case)")
    src = ap.add_mutually_exclusive_group(required=True)
    src.add_argument("--artifact", type=Path, help="path to research_artifact.json")
    src.add_argument(
        "--latest",
        action="store_true",
        help="use the newest research run for this tool",
    )
    ap.add_argument(
        "--no-scaffold",
        action="store_true",
        help="refuse to create a new skill if one does not exist",
    )
    ap.add_argument(
        "--force-rewrite",
        action="store_true",
        help="overwrite existing human-authored skill files (destructive)",
    )
    ap.add_argument(
        "--json",
        action="store_true",
        help="emit machine-readable result",
    )
    return ap


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)

    if args.latest:
        artifact_path = _latest_artifact_for(args.tool)
        if not artifact_path:
            print(
                f"error: no research runs found for tool {args.tool!r} under {RESEARCH_LOG_DIR}",
                file=sys.stderr,
            )
            return 2
    else:
        artifact_path = args.artifact
        if not artifact_path.is_file():
            print(f"error: artifact not found: {artifact_path}", file=sys.stderr)
            return 2

    request = AuthorRequest(
        tool_slug=args.tool,
        artifact_path=str(artifact_path),
        allow_scaffold=not args.no_scaffold,
        force_rewrite=args.force_rewrite,
    )
    result = author(request)

    if args.json:
        print(json.dumps(result.to_dict(), indent=2))
    else:
        print(f"=== Tool Mastery Author: {args.tool} ===")
        print(f"status          : {result.status.value}")
        print(f"sections sourced: {result.sections_sourced}")
        print(f"sections placeholder: {result.sections_placeholder}")
        print(f"sections preserved: {result.sections_preserved}")
        print(f"verifier passed : {result.verifier_passed}")
        if result.verifier_failures:
            print("verifier failures:")
            for f in result.verifier_failures:
                print(f"  - {f}")
        if result.skill_path:
            print(f"skill_path      : {result.skill_path}")
        if result.best_practices_path:
            print(f"best_practices  : {result.best_practices_path}")
        if result.provenance_path:
            print(f"provenance      : {result.provenance_path}")
        if result.notes:
            print("notes:")
            for n in result.notes:
                print(f"  - {n}")

    # Exit codes:
    # 0 — READY or PARTIAL (something useful written)
    # 1 — VERIFY_FAILED or BLOCKED_NO_SOURCES
    ok_states = {"authored_ready", "authored_partial"}
    return 0 if result.status.value in ok_states else 1


if __name__ == "__main__":
    sys.exit(main())
