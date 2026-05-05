#!/usr/bin/env python3
"""Operator CLI for EOS execution trace history.

Usage:
    python3 scripts/substrate_execution_trace_cli.py latest
    python3 scripts/substrate_execution_trace_cli.py show --trace-id abc12345
    python3 scripts/substrate_execution_trace_cli.py compact --limit 10
    python3 scripts/substrate_execution_trace_cli.py summary
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter

sys.path.insert(0, "/opt/OS")


def _print_json(obj) -> None:
    print(json.dumps(obj, indent=2, default=str))


def _history():
    from eos_ai.substrate.execution_trace import get_trace_history

    return get_trace_history()


def cmd_latest(args: argparse.Namespace) -> int:
    traces = _history().latest(limit=args.limit)
    _print_json(traces)
    return 0


def cmd_show(args: argparse.Namespace) -> int:
    traces = _history().latest(limit=500)
    tid = args.trace_id.lower()
    matches = [
        t
        for t in traces
        if str(t.get("trace_id", "")).lower().startswith(tid)
        or str(t.get("trace_id", "")).lower() == tid
    ]
    if not matches:
        _print_json({"error": "no trace found", "trace_id_prefix": args.trace_id})
        return 1
    if len(matches) == 1:
        _print_json(matches[0])
    else:
        _print_json(matches)
    return 0


def cmd_by_mode(args: argparse.Namespace) -> int:
    traces = _history().by_mode(args.mode, limit=args.limit)
    _print_json(traces)
    return 0


def cmd_by_session(args: argparse.Namespace) -> int:
    traces = _history().by_session(args.name, limit=args.limit)
    _print_json(traces)
    return 0


def cmd_compact(args: argparse.Namespace) -> int:
    from eos_ai.substrate.execution_trace import format_trace_compact

    traces = _history().latest(limit=args.limit)
    for t in traces:
        print(format_trace_compact(t))
    return 0


def cmd_clear_history(_args: argparse.Namespace) -> int:
    _history().clear()
    _print_json({"status": "cleared"})
    return 0


def cmd_by_provider(args: argparse.Namespace) -> int:
    traces = _history().by_provider(args.provider, limit=args.limit)
    _print_json(traces)
    return 0


def cmd_by_path(args: argparse.Namespace) -> int:
    traces = _history().by_execution_path(args.path, limit=args.limit)
    _print_json(traces)
    return 0


def cmd_summary(_args: argparse.Namespace) -> int:
    traces = _history().latest(limit=10000)
    total = len(traces)
    by_mode: Counter = Counter()
    by_result: Counter = Counter()
    by_provider: Counter = Counter()
    for t in traces:
        by_mode[t.get("mode", "unknown")] += 1
        by_result[t.get("result", "unknown")] += 1
        by_provider[t.get("provider", "unknown")] += 1
    _print_json(
        {
            "total_traces": total,
            "by_mode": dict(by_mode.most_common()),
            "by_result": dict(by_result.most_common()),
            "by_provider": dict(by_provider.most_common()),
        }
    )
    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description=__doc__.strip().splitlines()[0])
    sub = p.add_subparsers(dest="cmd", required=True)

    # latest
    s = sub.add_parser("latest", help="show recent traces (JSON)")
    s.add_argument("--limit", type=int, default=20)
    s.set_defaults(func=cmd_latest)

    # show
    s = sub.add_parser("show", help="show single trace by ID (partial match OK)")
    s.add_argument("--trace-id", required=True, help="trace ID or first 8+ chars")
    s.set_defaults(func=cmd_show)

    # by-mode
    s = sub.add_parser("by-mode", help="filter traces by mode (builder/product)")
    s.add_argument("mode", help="builder or product")
    s.add_argument("--limit", type=int, default=20)
    s.set_defaults(func=cmd_by_mode)

    # by-session
    s = sub.add_parser("by-session", help="filter traces by session name")
    s.add_argument("name", help="session name")
    s.add_argument("--limit", type=int, default=20)
    s.set_defaults(func=cmd_by_session)

    # by-provider
    s = sub.add_parser("by-provider", help="filter traces by provider")
    s.add_argument("provider", help="provider name (e.g. claude_cli, gemini)")
    s.add_argument("--limit", type=int, default=20)
    s.set_defaults(func=cmd_by_provider)

    # by-path
    s = sub.add_parser("by-path", help="filter traces by execution path")
    s.add_argument("path", help="execution path (conversation, workflow, rerouted)")
    s.add_argument("--limit", type=int, default=20)
    s.set_defaults(func=cmd_by_path)

    # compact
    s = sub.add_parser("compact", help="one-line-per-trace compact view")
    s.add_argument("--limit", type=int, default=20)
    s.set_defaults(func=cmd_compact)

    # clear-history
    s = sub.add_parser("clear-history", help="clear trace buffer")
    s.set_defaults(func=cmd_clear_history)

    # summary
    s = sub.add_parser("summary", help="aggregate counts by mode/result/provider")
    s.set_defaults(func=cmd_summary)

    return p


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
