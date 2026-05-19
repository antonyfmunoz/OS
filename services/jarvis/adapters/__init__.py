"""Adapters — governed access to external systems (filesystem, shell, git, tmux)."""

from services.jarvis.adapters.base import BaseAdapter
from services.jarvis.adapters.filesystem import FilesystemAdapter
from services.jarvis.adapters.shell import ShellAdapter
from services.jarvis.adapters.git import GitAdapter
from services.jarvis.adapters.tmux import TmuxAdapter

__all__ = [
    "BaseAdapter",
    "FilesystemAdapter",
    "ShellAdapter",
    "GitAdapter",
    "TmuxAdapter",
]
