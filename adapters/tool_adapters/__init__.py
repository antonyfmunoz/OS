"""Tool adapters — governed access to external systems (filesystem, shell, git, tmux)."""

from adapters.tool_adapters.base import BaseAdapter
from adapters.tool_adapters.filesystem import FilesystemAdapter
from adapters.tool_adapters.shell import ShellAdapter
from adapters.tool_adapters.git import GitAdapter
from adapters.tool_adapters.tmux import TmuxAdapter

__all__ = [
    "BaseAdapter",
    "FilesystemAdapter",
    "ShellAdapter",
    "GitAdapter",
    "TmuxAdapter",
]
