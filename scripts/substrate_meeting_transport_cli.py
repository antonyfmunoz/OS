#!/usr/bin/env python3
"""
Meeting voice transport CLI.

Subcommands:
  status   Print MeetingTransport.status_report() (JSON).
  start    Start a bounded voice session for the meeting node.
  inject   Inject a single transcript utterance through the bounded seam.
  end      End the active voice session for the meeting node.

The CLI never opens a browser, never joins a meeting, and never speaks
into one. It is a thin operator-facing wrapper over the bounded
`MeetingTransport` adapter so transcript-only mode can be exercised end-
to-end without any meeting bridge wired up.

Usage examples:
    python3 scripts/substrate_meeting_transport_cli.py status \\
        --platform google_meet --meeting-id abc-defg-hij

    python3 scripts/substrate_meeting_transport_cli.py inject \\
        --platform google_meet --meeting-id abc-defg-hij \\
        --text "what's our top blocker right now" \\
        --participant "Antony"
"""

from __future__ import annotations

import argparse
import json
import sys

sys.path.insert(0, "/opt/OS")


def _print_json(obj) -> None:
    print(json.dumps(obj, indent=2, default=str))


def _transport(args: argparse.Namespace):
    from eos_ai.substrate.meeting_transport import get_default_meeting_transport

    return get_default_meeting_transport(
        platform=args.platform,
        meeting_id=args.meeting_id,
        role_slug=args.role,
    )


def cmd_status(args: argparse.Namespace) -> int:
    _print_json(_transport(args).status_report(history_limit=args.limit))
    return 0


def cmd_start(args: argparse.Namespace) -> int:
    _print_json(_transport(args).start_session())
    return 0


def cmd_inject(args: argparse.Namespace) -> int:
    result = _transport(args).inject_utterance(
        args.text,
        user_id=args.user_id,
        participant_name=args.participant,
        meeting_id=args.meeting_id,
    )
    _print_json(result)
    return 0 if result.get("status") in ("ok", "empty_text") else 1


def cmd_end(args: argparse.Namespace) -> int:
    _print_json(_transport(args).end_session(reason="cli end"))
    return 0


def _add_common(p: argparse.ArgumentParser) -> None:
    p.add_argument(
        "--platform",
        default="generic_meeting",
        help="google_meet|zoom|teams|generic_meeting",
    )
    p.add_argument("--meeting-id", default=None)
    p.add_argument("--role", default="ea_orchestrator")
    p.add_argument(
        "--provider",
        default=None,
        help="provider label for --attach-fake-source (default: generic_meeting)",
    )
    p.add_argument(
        "--attach-fake-source",
        default=None,
        metavar="NAME",
        help="attach a FakeMeetingSource with this name to the meeting transport",
    )
    p.add_argument(
        "--fake-utterance",
        action="append",
        default=None,
        metavar="TEXT",
        help="utterance text for --attach-fake-source (repeatable)",
    )
    p.add_argument(
        "--detach-source",
        default=None,
        metavar="NAME",
        help="detach a previously attached source by name",
    )
    p.add_argument(
        "--pump",
        nargs="?",
        const=1,
        type=int,
        default=None,
        metavar="N",
        help="pump attached sources (default max_per_source=1)",
    )
    p.add_argument(
        "--show-attached",
        action="store_true",
        help="print list_attached_sources() as JSON",
    )


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[1])
    # Top-level flags (also available as no-subcommand operator surface for
    # attach/pump/show/detach). They are re-added to each subcommand via
    # _add_common so both invocation styles work.
    _add_common(p)
    sub = p.add_subparsers(dest="cmd", required=False)

    s = sub.add_parser("status", help="print transport status_report (JSON)")
    _add_common(s)
    s.add_argument("--limit", type=int, default=10)
    s.set_defaults(func=cmd_status)

    st = sub.add_parser("start", help="start a bounded voice session")
    _add_common(st)
    st.set_defaults(func=cmd_start)

    inj = sub.add_parser("inject", help="inject a single transcript utterance")
    _add_common(inj)
    inj.add_argument("--text", required=True)
    inj.add_argument("--user-id", default=None)
    inj.add_argument("--participant", default=None)
    inj.set_defaults(func=cmd_inject)

    en = sub.add_parser("end", help="end the active voice session")
    _add_common(en)
    en.set_defaults(func=cmd_end)

    return p


def _run_source_ops(args: argparse.Namespace) -> None:
    """Run attach/pump/show/detach ops against the configured meeting transport.

    Each block is independent and skipped if not requested.
    """
    needs_transport = any(
        [
            args.attach_fake_source,
            args.pump is not None,
            args.show_attached,
            args.detach_source,
        ]
    )
    if not needs_transport:
        return

    from eos_ai.substrate.meeting_sources import FakeMeetingSource

    transport = _transport(args)

    if args.attach_fake_source:
        provider = args.provider or "generic_meeting"
        utterances = [{"text": t} for t in (args.fake_utterance or [])]
        source = FakeMeetingSource(
            name=args.attach_fake_source,
            provider=provider,
            utterances=utterances,
        )
        _print_json(transport.attach_source(source))

    if args.pump is not None:
        _print_json(transport.pump_attached_sources(max_per_source=args.pump or 1))

    if args.show_attached:
        _print_json(transport.list_attached_sources())

    if args.detach_source:
        _print_json(transport.detach_source(args.detach_source))


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    rc = 0
    if getattr(args, "func", None) is not None:
        rc = args.func(args)
    _run_source_ops(args)
    return rc


if __name__ == "__main__":
    sys.exit(main())
