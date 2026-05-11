#!/usr/bin/env python3
"""Operator CLI to append Meet captions to the JSONL bridge.

Usage:
    meet_caption_writer.py --meeting-code CODE [--speaker NAME] [--ts TS] \
        [--stdin] [TEXT ...]

With --stdin: reads one caption per line from stdin (blank lines ignored).
Else: joins positional TEXT args into a single caption.

Prints one JSON result dict per caption written. Exits 0 on any success,
1 if all writes failed.
"""

from __future__ import annotations

import argparse
import json
import sys

import os
sys.path.insert(0, os.environ.get("UMH_ROOT") or os.environ.get("OS_ROOT") or os.environ.get("EOS_ROOT") or "/opt/OS")

from runtime.substrate.meet_caption_bridge import CaptionWriter  # noqa: E402


def main() -> int:
    p = argparse.ArgumentParser(description="Append Meet captions to JSONL bridge.")
    p.add_argument("--meeting-code", required=True, help="Meet meeting code")
    p.add_argument("--speaker", default=None, help="Speaker label")
    p.add_argument("--ts", default=None, help="ISO-8601 UTC timestamp")
    p.add_argument("--stdin", action="store_true", help="Read captions from stdin")
    p.add_argument("text", nargs="*", help="Caption text (positional)")
    args = p.parse_args()

    writer = CaptionWriter(args.meeting_code)
    any_ok = False
    any_written = False

    if args.stdin:
        for raw in sys.stdin:
            line = raw.rstrip("\n")
            if not line.strip():
                continue
            any_written = True
            result = writer.append(line, speaker=args.speaker, ts=args.ts)
            print(json.dumps(result, ensure_ascii=False))
            if result["status"] == "ok":
                any_ok = True
    else:
        text = " ".join(args.text).strip()
        if text:
            any_written = True
            result = writer.append(text, speaker=args.speaker, ts=args.ts)
            print(json.dumps(result, ensure_ascii=False))
            if result["status"] == "ok":
                any_ok = True

    if not any_written:
        print(json.dumps({"status": "empty_text", "detail": "no input"}))
        return 1
    return 0 if any_ok else 1


if __name__ == "__main__":
    sys.exit(main())
