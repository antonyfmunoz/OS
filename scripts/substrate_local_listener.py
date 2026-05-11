#!/usr/bin/env python3
"""
Local listener CLI — emit a bounded activation trigger.

This is the operator-facing entrypoint for the new local listener layer.
It is intentionally tiny: pick a trigger kind, pick a node, optionally
hint a requested mode, and the listener will (safely) attempt to start an
open_day ritual on that node, reusing all existing readiness/scene-policy
logic.

Examples:
    # Manual activation of the local workstation
    python3 scripts/substrate_local_listener.py \\
        --trigger manual_activate --node antony-workstation

    # Hotkey activation requesting builder mode
    python3 scripts/substrate_local_listener.py \\
        --trigger hotkey_activate --node antony-workstation --mode builder

    # Show recent triggers without firing one
    python3 scripts/substrate_local_listener.py --history --limit 10

This CLI never raises into the shell. It exits 0 on a recorded trigger
(even if the trigger was safely SKIPPED), and 1 only on argument errors.
"""

from __future__ import annotations

import argparse
import json
import sys

import os
sys.path.insert(0, os.environ.get("UMH_ROOT") or os.environ.get("OS_ROOT") or os.environ.get("EOS_ROOT") or "/opt/OS")

from runtime.substrate.local_listener import (  # noqa: E402
    LocalListener,
    TriggerKind,
    get_trigger_history,
    listener_report,
)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Emit a bounded local listener trigger."
    )
    parser.add_argument(
        "--trigger",
        choices=[k.value for k in TriggerKind],
        help="Trigger kind to emit.",
    )
    parser.add_argument("--node", help="Target node id.")
    parser.add_argument(
        "--mode",
        choices=["builder", "operator_mode", "full_station"],
        default=None,
        help="Optional requested scene mode hint. If omitted, ritual_body inference runs.",
    )
    parser.add_argument(
        "--history",
        action="store_true",
        help="Print recent listener history instead of firing a trigger.",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=10,
        help="History limit (with --history).",
    )
    args = parser.parse_args()

    if args.history:
        print(
            json.dumps(listener_report(node_id=args.node, limit=args.limit), indent=2)
        )
        return 0

    if not args.trigger or not args.node:
        parser.error("--trigger and --node are required unless --history is given")
        return 2  # unreachable; argparse exits

    listener = LocalListener()
    kind = TriggerKind(args.trigger)
    from runtime.substrate.local_listener import LocalTrigger

    trigger = listener.emit(
        LocalTrigger(node_id=args.node, kind=kind, requested_mode=args.mode)
    )
    print(json.dumps(trigger.as_dict(), indent=2))

    # History tail for context.
    print("\n── recent triggers ──", file=sys.stderr)
    for h in get_trigger_history().latest(limit=5, node_id=args.node):
        print(
            f"  {h['occurred_at']}  {h['kind']:<22} {h['status']:<8} "
            f"{(h.get('decision_reason') or '')[:80]}",
            file=sys.stderr,
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
