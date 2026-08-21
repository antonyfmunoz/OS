"""Canonical runtime-state path resolution — the runtime/source boundary.

Wave 0 of the MVP campaign separates the tracked source checkout from mutable
runtime state. Every runtime journal, snapshot, queue, and heartbeat that a
live service writes on a normal run resolves its home through this module —
never through a hardcoded ``data/umh/<subsystem>/`` literal.

Resolution order:
  1. ``UMH_STATE_DIR`` env var when set (must be an absolute path), else
  2. ``$UMH_ROOT/data/runtime/umh`` (``data/runtime/`` is reserved and
     gitignored by repository law).

This provides Git/source-identity separation — the live organism never dirties
a tracked file. It is NOT full physical storage separation; a future
``/var/lib/umh`` migration can happen by pointing ``UMH_STATE_DIR`` elsewhere.

Containment: subsystem names and filenames are validated against traversal —
no absolute paths, no empty segments, no ``.``/``..``, no lexical or resolved
escape outside the state root. Directories are created only on an explicit
path request, never at import time. Log lines never include secret or env
values.
"""

from __future__ import annotations

import os
from pathlib import Path

_DEFAULT_ROOT = "/opt/OS"
_STATE_SUBDIR = ("data", "runtime", "umh")


def _validate_segments(name: str, kind: str) -> list[str]:
    """Split a relative name into segments, rejecting traversal."""
    if not isinstance(name, str) or not name.strip():
        raise ValueError(f"runtime-state {kind} must be a non-empty string")
    if name.startswith(("/", "\\")) or (len(name) > 1 and name[1] == ":"):
        raise ValueError(f"runtime-state {kind} must be relative, got an absolute path")
    segments = name.replace("\\", "/").split("/")
    for seg in segments:
        if not seg:
            raise ValueError(f"runtime-state {kind} contains an empty path segment")
        if seg in (".", ".."):
            raise ValueError(f"runtime-state {kind} may not contain '.' or '..' segments")
    return segments


def runtime_state_root() -> Path:
    """Resolve the runtime-state root directory (no directory creation)."""
    override = os.environ.get("UMH_STATE_DIR")
    if override is not None:
        if not override.strip():
            raise ValueError("UMH_STATE_DIR is set but empty")
        root = Path(override)
        if not root.is_absolute():
            raise ValueError("UMH_STATE_DIR must be an absolute path")
        return root
    if os.environ.get("UMH_REQUIRE_STATE_DIR", "").strip().lower() in {
        "1",
        "true",
        "yes",
        "on",
    }:
        raise ValueError("UMH_STATE_DIR is required when UMH_REQUIRE_STATE_DIR is enabled")
    umh_root = os.environ.get("UMH_ROOT") or _DEFAULT_ROOT
    return Path(umh_root).joinpath(*_STATE_SUBDIR)


def _contained(root: Path, candidate: Path) -> Path:
    """Reject candidates that escape the state root after resolution."""
    resolved_root = root.resolve()
    resolved = candidate.resolve()
    if resolved != resolved_root and resolved_root not in resolved.parents:
        raise ValueError("runtime-state path escapes the state root")
    return candidate


def runtime_state_dir(subsystem: str, *, create: bool = True) -> Path:
    """Directory for one runtime subsystem (e.g. ``organism``, ``operator/intent_loop``).

    Nested subsystem names are allowed; traversal and absolute paths are not.
    The directory is created on request (``create=True``), never on import.
    """
    root = runtime_state_root()
    segments = _validate_segments(subsystem, "subsystem")
    path = _contained(root, root.joinpath(*segments))
    if create:
        path.mkdir(parents=True, exist_ok=True)
    return path


def runtime_state_path(subsystem: str, filename: str, *, create_parent: bool = True) -> Path:
    """Full path for one runtime-state file inside a subsystem directory."""
    directory = runtime_state_dir(subsystem, create=create_parent)
    segments = _validate_segments(filename, "filename")
    return _contained(runtime_state_root(), directory.joinpath(*segments))
