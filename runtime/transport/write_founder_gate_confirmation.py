"""Write a founder visual confirmation file to the local inbox.

Usage:
    python3 /opt/OS/runtime/transport/write_founder_gate_confirmation.py \
        --work-order-id WO-LOCAL-PILOT-GDRIVE-GDOCS-001 \
        --gate VISIBLE_CHROME_LAUNCH \
        --confirmed true \
        --notes "Chrome visibly open on desktop"

    python3 /opt/OS/runtime/transport/write_founder_gate_confirmation.py \
        --work-order-id WO-LOCAL-PILOT-GDRIVE-GDOCS-001 \
        --gate VISIBLE_CHROME_LAUNCH \
        --confirmed false \
        --notes "Chrome did not visibly open"

The file is written to ~/eos_advisor_messages/inbox/ where the local
worker polls for it.
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

INBOX_DIR = Path.home() / "eos_advisor_messages" / "inbox"


def build_founder_visual_confirmation(
    work_order_id: str,
    gate: str,
    confirmed: bool,
    visible_app: str = "",
    notes: str = "",
) -> dict:
    """Build a founder visual confirmation response dict."""
    return {
        "response_type": "founder_visual_confirmation",
        "work_order_id": work_order_id,
        "gate": gate,
        "confirmed": confirmed,
        "visible_app": visible_app or ("Google Chrome" if confirmed else ""),
        "notes": notes,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


def write_confirmation(
    work_order_id: str,
    gate: str,
    confirmed: bool,
    visible_app: str = "",
    notes: str = "",
    inbox_dir: Path | None = None,
) -> Path:
    """Write the confirmation JSON to the inbox directory."""
    if inbox_dir is None:
        inbox_dir = INBOX_DIR
    inbox_dir.mkdir(parents=True, exist_ok=True)

    data = build_founder_visual_confirmation(
        work_order_id=work_order_id,
        gate=gate,
        confirmed=confirmed,
        visible_app=visible_app,
        notes=notes,
    )

    filename = f"founder_visual_confirmation_{work_order_id}.json"
    path = inbox_dir / filename
    with open(path, "w") as f:
        json.dump(data, f, indent=2)

    return path


def main() -> None:
    parser = argparse.ArgumentParser(description="Write founder gate confirmation")
    parser.add_argument("--work-order-id", required=True)
    parser.add_argument("--gate", required=True)
    parser.add_argument("--confirmed", required=True, choices=["true", "false"])
    parser.add_argument("--visible-app", default="")
    parser.add_argument("--notes", default="")
    args = parser.parse_args()

    confirmed = args.confirmed.lower() == "true"
    path = write_confirmation(
        work_order_id=args.work_order_id,
        gate=args.gate,
        confirmed=confirmed,
        visible_app=args.visible_app,
        notes=args.notes,
    )

    status = "CONFIRMED" if confirmed else "DENIED"
    print(f"[founder] Gate confirmation written: {status}")
    print(f"[founder] File: {path}")
    print(f"[founder] Work order: {args.work_order_id}")
    print(f"[founder] Gate: {args.gate}")


if __name__ == "__main__":
    main()
