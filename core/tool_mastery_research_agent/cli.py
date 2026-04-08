"""CLI entry for the Tool Mastery Research Agent.

Usage:
    python3 -m core.tool_mastery_research_agent \\
        --tool notebooklm_mcp --mode research

    python3 -m core.tool_mastery_research_agent \\
        --tool notion --mode refresh --official-url https://developers.notion.com/

    python3 -m core.tool_mastery_research_agent \\
        --consume-action /opt/OS/logs/deferred/<id>.json

The --consume-action form loads a deferred Control Plane action file
and runs the research for the slug embedded in its inputs. This is
how the agent plugs into the existing queue.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .agent import run
from .models import ResearchMode, ResearchRequest


def _load_action_file(path: Path) -> ResearchRequest:
    data = json.loads(path.read_text(encoding="utf-8"))
    # the deferred file wraps the action under "action"
    action = data.get("action") or data
    inputs = action.get("inputs") or {}
    slug = inputs.get("tool")
    if not slug:
        raise ValueError(f"action file {path} has no inputs.tool")
    work_type = inputs.get("work_type", "research")
    mode = ResearchMode(work_type)
    return ResearchRequest(
        tool_slug=slug,
        mode=mode,
        action_id=action.get("id"),
        source_agent=action.get("source_agent", "tool_mastery_research_agent"),
    )


def build_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(
        prog="tool_mastery_research_agent",
        description="Execute source-grounded research for a tool slug.",
    )
    ap.add_argument("--tool", help="tool slug")
    ap.add_argument(
        "--mode",
        choices=[m.value for m in ResearchMode],
        default=ResearchMode.RESEARCH.value,
    )
    ap.add_argument("--official-url", default=None)
    ap.add_argument(
        "--hint",
        action="append",
        default=[],
        help="additional source URL (repeatable)",
    )
    ap.add_argument(
        "--consume-action",
        type=Path,
        default=None,
        help="path to a deferred Control Plane action file",
    )
    ap.add_argument("--json", action="store_true", help="emit machine-readable result")
    return ap


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)

    if args.consume_action:
        try:
            request = _load_action_file(args.consume_action)
        except (OSError, ValueError, KeyError) as err:
            print(f"error: {err}", file=sys.stderr)
            return 2
    elif args.tool:
        request = ResearchRequest(
            tool_slug=args.tool,
            mode=ResearchMode(args.mode),
            source_hints=list(args.hint),
            official_url=args.official_url,
        )
    else:
        print("error: --tool or --consume-action required", file=sys.stderr)
        return 2

    result = run(request)

    if args.json:
        print(json.dumps(result.to_dict(), indent=2))
    else:
        print(
            f"=== Tool Mastery Research: {request.tool_slug} ({request.mode.value}) ==="
        )
        print(f"status    : {result.status.value}")
        print(f"run_dir   : {result.run_dir}")
        if result.summary_path:
            print(f"summary   : {result.summary_path}")
        if result.next_steps:
            print("next_steps:")
            for s in result.next_steps:
                print(f"  - {s}")

    # exit code: 0 if artifact produced at all, 1 if fully empty / errored
    return 0 if result.status.value in ("ok", "partial", "no_sources") else 1


if __name__ == "__main__":
    sys.exit(main())
