"""Deterministic repository root for tests — derived, never hardcoded.

Why this exists
---------------
Six test modules pinned the repo root to an ABSOLUTE path from a long-gone
campaign worktree (``/opt/OS/.claude/worktrees/c4-6-cockpit-finalization``) at
MODULE-IMPORT time::

    sys.path.insert(0, "/opt/OS/.claude/worktrees/c4-6-cockpit-finalization")
    os.environ.setdefault("UMH_ROOT", "/opt/OS/.claude/worktrees/c4-6-cockpit-finalization")

Two properties made that actively dangerous rather than merely stale:

1. It runs at IMPORT (collection) time, not inside a test, so pytest applies it
   while merely *collecting* the file.
2. ``os.environ`` is process-global and nothing restored it, so every module
   collected AFTERWARDS in the same process saw the foreign root.

The observed consequence was not a subtle wrong answer — it was a hard
**collection abort**: ``tests/test_p1_phase2b_operator.py`` resolves
``OPERATOR_DIR`` from ``UMH_ROOT`` at import time, so once the foreign root
leaked it raised ``FileNotFoundError`` and pytest interrupted the ENTIRE shard
(``Interrupted: 1 error during collection``). In a whole-tree file-sharded run
that silently voided ~127 files' worth of evidence while every surface signal
still looked healthy.

Note the path is not simply "deleted": the directory still exists but no longer
contains ``substrate/``, which is exactly why the failure surfaced as a missing
subdirectory rather than a missing root.

The rule
--------
A test must derive the repository root from the ACTIVE CHECKOUT it is running
from. ``REPO_ROOT`` below is computed from this file's own location, so it is
correct in the main checkout, in any worktree, on any host, for any user — and
it can never point at a foreign tree.

If a test genuinely needs a DIFFERENT root, it sets ``UMH_ROOT`` inside the test
with ``monkeypatch.setenv`` (auto-restored) — never at module scope.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

# This file lives at <repo>/tests/repo_root.py → parents[1] is <repo>.
REPO_ROOT: str = str(Path(__file__).resolve().parents[1])


def ensure_repo_on_path() -> str:
    """Put the ACTIVE checkout on ``sys.path`` and return it.

    Import-time safe and idempotent. Deliberately does NOT touch ``UMH_ROOT``:
    mutating process-global env at import time is the defect this module exists
    to remove. A test needing a specific ``UMH_ROOT`` uses ``monkeypatch.setenv``
    so pytest restores it.
    """
    if REPO_ROOT not in sys.path:
        sys.path.insert(0, REPO_ROOT)
    return REPO_ROOT


def umh_root() -> str:
    """The repo root a test should act on: ``UMH_ROOT`` if set, else this checkout.

    Reads the env at CALL time rather than caching at import, so a test that
    legitimately overrides ``UMH_ROOT`` (via monkeypatch) is honored and the
    override disappears when pytest restores the environment.
    """
    return os.environ.get("UMH_ROOT") or REPO_ROOT
