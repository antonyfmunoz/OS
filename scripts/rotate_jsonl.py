#!/usr/bin/env python3
"""Rotate JSONL stores that exceed a size threshold.

Runs nightly via cron. For each target file:
  - If size > MAX_BYTES, rename to .old (overwriting any previous .old)
  - Create a fresh empty file in its place

This prevents unbounded append-only stores from consuming disk.
"""

from __future__ import annotations

import os
import shutil
import sys

MAX_BYTES = 10 * 1024 * 1024  # 10 MB

UMH_ROOT = os.environ.get("UMH_ROOT", "/opt/OS")

TARGETS = [
    "data/umh/organism/outcome_learning.jsonl",
    "data/umh/organism/events.jsonl",
    "data/umh/organism/execution_journal.jsonl",
    "data/umh/organism/messages.jsonl",
    "data/umh/organism/reports.jsonl",
    "data/umh/organism/deliverables.jsonl",
    "data/umh/organism/proof_packages.jsonl",
    "data/umh/organism/learning_signals.jsonl",
    "data/umh/learning/signal_feed.jsonl",
    "data/umh/qualification/predictions.jsonl",
    "data/umh/work_portfolio/velocity.jsonl",
]


def rotate(path: str) -> bool:
    if not os.path.isfile(path):
        return False
    size = os.path.getsize(path)
    if size <= MAX_BYTES:
        return False
    old_path = path + ".old"
    shutil.move(path, old_path)
    with open(path, "w"):
        pass
    print(f"[rotate] {path}: {size / 1024 / 1024:.1f}MB → rotated")
    return True


def main() -> None:
    rotated = 0
    for rel in TARGETS:
        full = os.path.join(UMH_ROOT, rel)
        if rotate(full):
            rotated += 1
    print(f"[rotate] done: {rotated} file(s) rotated")


if __name__ == "__main__":
    sys.exit(main() or 0)
