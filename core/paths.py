"""Centralized root path resolution for the UMH harness.

Single source of truth for the repository root path.
All path-dependent code should import from here rather than
hardcoding /opt/OS.

Resolution order:
  1. UMH_ROOT env var  (canonical)
  2. OS_ROOT env var   (backward compat, aliased from EOS_ROOT)
  3. EOS_ROOT env var  (legacy)
  4. /opt/OS           (hardcoded fallback)
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

_FALLBACK = "/opt/OS"

_resolved_root: Path | None = None
_resolved_source: str | None = None


def _resolve() -> tuple[Path, str]:
    for var in ("UMH_ROOT", "OS_ROOT", "EOS_ROOT"):
        val = os.environ.get(var)
        if val:
            return Path(val), var
    return Path(_FALLBACK), "hardcoded"


def get_root() -> Path:
    """Return the resolved repository root as a Path."""
    global _resolved_root, _resolved_source
    if _resolved_root is None:
        _resolved_root, _resolved_source = _resolve()
        if _resolved_source == "hardcoded":
            print(
                f"[paths] UMH_ROOT not set — using legacy fallback {_FALLBACK}",
                file=sys.stderr,
            )
    return _resolved_root


def get_root_source() -> str:
    """Return which env var (or 'hardcoded') resolved the root."""
    if _resolved_source is None:
        get_root()
    return _resolved_source  # type: ignore[return-value]


def ensure_sys_path() -> None:
    """Ensure the repo root is on sys.path."""
    root = str(get_root())
    if root not in sys.path:
        sys.path.insert(0, root)


ROOT = get_root()
