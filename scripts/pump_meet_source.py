#!/usr/bin/env python3
"""
pump_meet_source — operator-driven single-shot pump for a Google Meet
transcript bridge source.

Attaches a ``GoogleMeetSource.from_bridge(...)`` to the default meeting
transport and drains up to ``--max`` lines from its JSONL caption bridge
through the bounded ``inject_utterance`` seam.

This is intentionally a ONE-SHOT command. No loops. No daemon. No watch
mode. Operators run it interactively to advance a meeting transport by a
small, inspectable amount. Wire it into a tmux/cron loop yourself if you
want continuous operation — this script won't do it for you.

With ``--no-attach`` the source is built but NOT attached; the script
prints the source's ``status_snapshot()`` instead of pumping.

With ``--show-report`` the script also prints a small, operator-focused
subset of ``unified_transport_report()`` covering the meeting transport
mode, attached sources, the meet_bridges entry for this meeting, and
supervision hints.

Exit codes:
    0  pump status "ok" (or --no-attach succeeded)
    1  pump status non-ok, or any setup error
"""

from __future__ import annotations

import argparse
import json
import sys
import traceback

sys.path.insert(0, "/opt/OS")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--meeting-code", required=True, help="Meeting code slug")
    ap.add_argument("--name", default=None, help="Source name (default meet_bridge)")
    ap.add_argument("--max", type=int, default=5, help="Max utterances per pump")
    ap.add_argument("--no-attach", action="store_true", help="Build source only, do not attach/pump")
    ap.add_argument("--show-report", action="store_true", help="Also print a focused unified_transport_report subset")
    ap.add_argument("--platform", default="google_meet", help="Meeting platform label")
    args = ap.parse_args()

    try:
        from eos_ai.substrate.google_meet_source import GoogleMeetSource
        from eos_ai.substrate.meeting_transport import MeetingTransport
    except Exception as e:  # noqa: BLE001
        print(json.dumps({"status": "import_error", "detail": str(e)}))
        return 1

    out: dict = {
        "meeting_code": args.meeting_code,
        "platform": args.platform,
        "name": args.name or "meet_bridge",
    }

    try:
        transport = MeetingTransport(
            platform=args.platform,
            meeting_id=args.meeting_code,
            ensure_node=True,
        )
        source = GoogleMeetSource.from_bridge(
            name=args.name or "meet_bridge",
            meeting_code=args.meeting_code,
        )
    except Exception as e:  # noqa: BLE001
        print(json.dumps({
            "status": "setup_error",
            "detail": str(e),
            "trace": traceback.format_exc(limit=3),
        }))
        return 1

    if args.no_attach:
        out["mode"] = "no_attach"
        out["source_status"] = source.status_snapshot()
        print(json.dumps(out, indent=2, default=str))
        return 0

    attach_result = transport.attach_source(source)
    out["attach"] = attach_result
    if attach_result.get("status") not in ("attached",):
        print(json.dumps(out, indent=2, default=str))
        return 1

    pump = transport.pump_attached_sources(max_per_source=max(1, int(args.max)))
    out["pump"] = pump

    if args.show_report:
        try:
            from eos_ai.substrate.transport_report import unified_transport_report

            report = unified_transport_report(
                meeting_platform=args.platform,
                meeting_id=args.meeting_code,
            )
            mt = report.get("meeting_transport") or {}
            # Find bridge entry matching this code (sanitized).
            code_key = args.meeting_code.replace("/", "_")
            bridge_entry = None
            for b in report.get("meet_bridges") or []:
                if b.get("meeting_code", "").endswith(
                    code_key.split("/")[-1]
                ) or b.get("meeting_code") == args.meeting_code:
                    bridge_entry = b
                    break
            out["report_subset"] = {
                "meeting_transport_mode": mt.get("mode"),
                "attached_sources": mt.get("attached_sources"),
                "meet_bridge": bridge_entry,
                "supervision_hints": report.get("supervision_hints"),
            }
        except Exception as e:  # noqa: BLE001
            out["report_subset_error"] = str(e)

    print(json.dumps(out, indent=2, default=str))

    pump_status = (pump or {}).get("status")
    return 0 if pump_status == "ok" else 1


if __name__ == "__main__":
    raise SystemExit(main())
