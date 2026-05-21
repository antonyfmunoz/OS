#!/usr/bin/env python3
"""
BIS context injector — prints active venture context from VENTURES_JSON.
Used by !`command` blocks in skills to inject live venture data.

Usage:
  python3 /opt/OS/scripts/bis_context.py              # default fields
  python3 /opt/OS/scripts/bis_context.py --fields name,stage,icp
  python3 /opt/OS/scripts/bis_context.py --portfolio   # all ventures
  python3 /opt/OS/scripts/bis_context.py --founder     # founder name only
"""

import argparse
import json
import os
import sys

sys.path.insert(0, "/opt/OS")
from dotenv import load_dotenv

load_dotenv("/opt/OS/umh/.env")


def get_ventures() -> list[dict]:
    raw = os.getenv("VENTURES_JSON", "[]")
    try:
        return json.loads(raw)
    except Exception:
        return []


def get_active_venture() -> dict:
    ventures = get_ventures()
    vid = os.getenv("ACTIVE_VENTURE_ID", "")
    v = next((x for x in ventures if x.get("id") == vid), {})
    if not v and ventures:
        v = ventures[0]
    return v


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--fields",
        default="name,stage,binding_constraint,north_star,validation_milestone",
    )
    parser.add_argument("--portfolio", action="store_true")
    parser.add_argument("--founder", action="store_true")
    parser.add_argument("--full", action="store_true")
    args = parser.parse_args()

    if args.founder:
        print(f"Founder: {os.getenv('FOUNDER_NAME', 'the founder')}")
        return

    if args.portfolio:
        ventures = get_ventures()
        print(f"Portfolio: {len(ventures)} ventures")
        for v in ventures:
            print(
                f"  {v.get('name', '?')}: {v.get('stage', '?')} | {v.get('north_star', '?')}"
            )
        return

    v = get_active_venture()
    if args.full:
        fields = list(v.keys())
    else:
        fields = [f.strip() for f in args.fields.split(",")]

    label_map = {
        "name": "Venture",
        "stage": "Stage",
        "binding_constraint": "Constraint",
        "north_star": "North star",
        "validation_milestone": "Validation milestone",
        "icp": "ICP",
        "offer": "Offer",
        "primary_channel": "Channel",
    }
    for field in fields:
        label = label_map.get(field, field.replace("_", " ").title())
        print(f"{label}: {v.get(field, '?')}")


if __name__ == "__main__":
    main()
