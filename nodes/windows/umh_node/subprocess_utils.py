"""Subprocess helpers for the Windows daemon.

Provides platform-aware creation flags so that subprocess calls
from Session 1 (interactive desktop) don't flash visible CMD windows.
"""

from __future__ import annotations

import subprocess
import sys


def no_window_kwargs() -> dict:
    """Return creationflags kwarg to suppress console windows on Windows."""
    if sys.platform == "win32":
        return {"creationflags": subprocess.CREATE_NO_WINDOW}
    return {}
