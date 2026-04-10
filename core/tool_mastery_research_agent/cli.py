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
from .candidate_approval import (
    apply_decision,
    build_approval_file,
    format_candidates_for_display,
    latest_approval_file,
    load_approval_file,
    persist_approval_file,
    save_approval_file,
)
from .models import ResearchMode, ResearchRequest
from .search_discovery import generate_candidates


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

    # ---- candidate generation / approval subcommands (flag-style) ----
    ap.add_argument(
        "--generate-candidates",
        action="store_true",
        help=(
            "generate deterministic source candidates for --tool and write "
            "them to logs/tool_mastery_research/<slug>/candidates/ for "
            "operator approval. Does NOT fetch anything."
        ),
    )
    ap.add_argument(
        "--show-candidates",
        action="store_true",
        help="print the latest candidates file for --tool",
    )
    ap.add_argument(
        "--accept",
        default="",
        help="comma-separated 1-based indexes of candidates to accept",
    )
    ap.add_argument(
        "--reject",
        default="",
        help="comma-separated 1-based indexes of candidates to reject",
    )
    ap.add_argument("--accept-all", action="store_true")
    ap.add_argument("--reject-all", action="store_true")
    ap.add_argument(
        "--operator",
        default="operator",
        help="name recorded against approval decisions",
    )
    return ap


def _parse_index_set(raw: str) -> set[int]:
    out: set[int] = set()
    for piece in (raw or "").split(","):
        piece = piece.strip()
        if not piece:
            continue
        try:
            out.add(int(piece))
        except ValueError as err:
            raise ValueError(f"invalid index {piece!r}: {err}") from err
    return out


def _handle_generate_candidates(tool: str) -> int:
    plan = generate_candidates(tool)
    if not plan.candidates:
        print(f"no candidates generated for {tool!r}", file=sys.stderr)
        for note in plan.notes:
            print(f"  note: {note}", file=sys.stderr)
        return 1
    approval = build_approval_file(plan)
    path = persist_approval_file(approval)
    print(f"wrote candidates file: {path}")
    print()
    print(format_candidates_for_display(approval))
    print()
    print(
        f"next: review and approve with --tool {tool} --accept <n,m> (or --accept-all)"
    )
    return 0


def _handle_show_candidates(tool: str) -> int:
    path = latest_approval_file(tool)
    if path is None:
        print(f"no candidates file found for {tool!r}", file=sys.stderr)
        return 1
    approval = load_approval_file(path)
    print(f"file: {path}")
    print(format_candidates_for_display(approval))
    return 0


def _handle_apply_decision(args: argparse.Namespace) -> int:
    tool = args.tool
    path = latest_approval_file(tool)
    if path is None:
        print(f"no candidates file found for {tool!r}", file=sys.stderr)
        return 1
    approval = load_approval_file(path)
    try:
        accept = _parse_index_set(args.accept)
        reject = _parse_index_set(args.reject)
    except ValueError as err:
        print(f"error: {err}", file=sys.stderr)
        return 2
    apply_decision(
        approval,
        accept=accept,
        reject=reject,
        accept_all=args.accept_all,
        reject_all=args.reject_all,
        operator=args.operator,
    )
    save_approval_file(path, approval)
    print(f"updated: {path}")
    print(format_candidates_for_display(approval))
    return 0


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)

    # ---- candidate lifecycle subcommands take precedence ----
    if args.generate_candidates:
        if not args.tool:
            print("error: --generate-candidates requires --tool", file=sys.stderr)
            return 2
        return _handle_generate_candidates(args.tool)

    if args.show_candidates:
        if not args.tool:
            print("error: --show-candidates requires --tool", file=sys.stderr)
            return 2
        return _handle_show_candidates(args.tool)

    if args.accept or args.reject or args.accept_all or args.reject_all:
        if not args.tool:
            print("error: --accept/--reject require --tool", file=sys.stderr)
            return 2
        return _handle_apply_decision(args)

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
