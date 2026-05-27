"""JSONL rotation utility.

Append-only JSONL files grow without bound. This module provides
line-count-based rotation: when a file exceeds max_lines, its
contents are moved to a timestamped archive and the active file
is truncated.

Usage:
    from substrate.observability.jsonl_rotation import rotate_if_needed
    rotate_if_needed(Path("data/umh/traces/traces.jsonl"), max_lines=5000)
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from pathlib import Path

logger = logging.getLogger(__name__)

DEFAULT_MAX_LINES = 5000


def _count_lines(path: Path) -> int:
    if not path.exists():
        return 0
    count = 0
    with open(path, "rb") as f:
        for _ in f:
            count += 1
    return count


def rotate_if_needed(
    path: Path,
    max_lines: int = DEFAULT_MAX_LINES,
) -> Path | None:
    """Rotate a JSONL file if it exceeds max_lines.

    Returns the archive path if rotation happened, None otherwise.
    """
    if not path.exists():
        return None

    line_count = _count_lines(path)
    if line_count <= max_lines:
        return None

    ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    archive_name = f"{path.stem}_{ts}{path.suffix}"
    archive_path = path.parent / "archive" / archive_name

    archive_path.parent.mkdir(parents=True, exist_ok=True)
    path.rename(archive_path)
    path.touch()

    logger.info(
        "rotated %s → %s (%d lines)",
        path.name,
        archive_path.name,
        line_count,
    )
    return archive_path
