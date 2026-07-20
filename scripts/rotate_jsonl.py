#!/usr/bin/env python3
"""Rotate JSONL stores that exceed a size threshold.

Runs nightly via cron. For each target file:
  - If size > MAX_BYTES, rename to .old (overwriting any previous .old)
  - Create a fresh empty file in its place

This prevents unbounded append-only stores from consuming disk.

Wave 0: runtime journals live under the runtime-state root (data/runtime/umh
by default, UMH_STATE_DIR override) — resolved through
substrate.state.runtime_paths, never hardcoded checkout paths. The one
non-migrated legacy target (learning/signal_feed.jsonl) still resolves under
UMH_ROOT until its subsystem migrates.
"""

from __future__ import annotations

import os
import shutil
import sys

sys.path.insert(0, os.environ.get("UMH_ROOT", "/opt/OS"))

from substrate.state.runtime_paths import runtime_state_path  # noqa: E402

MAX_BYTES = 10 * 1024 * 1024  # 10 MB

UMH_ROOT = os.environ.get("UMH_ROOT", "/opt/OS")

# (subsystem, filename) pairs under the runtime-state root.
STATE_TARGETS = [
    ("organism", "outcome_learning.jsonl"),
    ("organism", "events.jsonl"),
    ("organism", "execution_journal.jsonl"),
    ("organism", "messages.jsonl"),
    ("organism", "reports.jsonl"),
    ("organism", "deliverables.jsonl"),
    ("organism", "proof_packages.jsonl"),
    ("organism", "learning_signals.jsonl"),
    ("qualification", "predictions.jsonl"),
    ("work_portfolio", "velocity.jsonl"),
]

# Legacy checkout-relative targets whose subsystems have not migrated yet
# (shrink-only — remove entries as their writers move to runtime_paths).
LEGACY_TARGETS = [
    "data/umh/learning/signal_feed.jsonl",
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
    for subsystem, filename in STATE_TARGETS:
        full = str(runtime_state_path(subsystem, filename, create_parent=False))
        if rotate(full):
            rotated += 1
    for rel in LEGACY_TARGETS:
        full = os.path.join(UMH_ROOT, rel)
        if rotate(full):
            rotated += 1
    print(f"[rotate] done: {rotated} file(s) rotated")


if __name__ == "__main__":
    sys.exit(main() or 0)
