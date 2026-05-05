#!/usr/bin/env python3
"""Emit an orchestrator signal from cron or the shell.

Usage:
    python3 scripts/emit_signal.py <signal_name>
    python3 scripts/emit_signal.py <signal_name> --payload-json '{"k":"v"}'

Prints a single JSON line: {"signal","emission_id","emitted_at","path"}.
Exits 0 on success, 1 on failure. No side effects beyond writing the
pending emission file under /opt/OS/logs/signals/<name>/pending/.

The orchestrator loop (scripts/orchestrator_loop.py) is the consumer.
"""

from __future__ import annotations

import argparse
import json
import sys

sys.path.insert(0, "/opt/OS")

from core.orchestrator.signals import emit_signal  # noqa: E402


def main() -> int:
    p = argparse.ArgumentParser(description="Emit an orchestrator signal")
    p.add_argument("signal", help="Signal name (e.g. morning_ready)")
    p.add_argument(
        "--payload-json",
        default="{}",
        help="JSON object to attach as payload (default: {})",
    )
    args = p.parse_args()

    try:
        payload = json.loads(args.payload_json)
        if not isinstance(payload, dict):
            print(
                json.dumps({"ok": False, "error": "payload must be a JSON object"}),
                file=sys.stderr,
            )
            return 1
    except json.JSONDecodeError as e:
        print(
            json.dumps({"ok": False, "error": f"invalid JSON payload: {e}"}),
            file=sys.stderr,
        )
        return 1

    emission = emit_signal(args.signal, payload=payload)
    print(
        json.dumps(
            {
                "ok": True,
                "signal": emission.signal,
                "emission_id": emission.emission_id,
                "emitted_at": emission.emitted_at,
                "path": emission.path,
            }
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
