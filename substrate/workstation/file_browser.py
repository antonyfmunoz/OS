"""Safe read-only file browser with allowlisted root paths.

Provides filesystem browsing for the Meta IDE workspace without
exposing arbitrary filesystem traversal. All paths are validated
against an explicit allowlist before access.

Phase 14.11C. Substrate layer. Instance-agnostic.
"""

from __future__ import annotations

import os
import platform
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


_REPO_ROOT = os.environ.get("UMH_ROOT", "/opt/OS")

ALLOWED_ROOTS: list[str] = [
    "/",
]

DENIED_PATTERNS: list[str] = [
    ".git/objects",
    ".git/refs",
    ".git/logs",
    "node_modules",
    "__pycache__",
    ".mypy_cache",
    ".ruff_cache",
    ".pytest_cache",
    ".env",
    "credentials",
    "secrets",
    ".claude/worktrees",
]


@dataclass
class FileEntry:
    name: str
    path: str
    entry_type: str  # "file" or "directory"
    size: int = 0
    source_env: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "path": self.path,
            "type": self.entry_type,
            "size": self.size,
            "source_env": self.source_env,
        }


@dataclass
class BrowseResult:
    ok: bool = True
    path: str = ""
    source_env: str = ""
    entries: list[FileEntry] = field(default_factory=list)
    error: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "ok": self.ok,
            "path": self.path,
            "source_env": self.source_env,
            "entries": [e.to_dict() for e in self.entries],
            "error": self.error,
        }


@dataclass
class FileReadResult:
    ok: bool = True
    path: str = ""
    source_env: str = ""
    content: str = ""
    size: int = 0
    language: str = "plaintext"
    truncated: bool = False
    error: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "ok": self.ok,
            "path": self.path,
            "source_env": self.source_env,
            "content": self.content,
            "size": self.size,
            "language": self.language,
            "truncated": self.truncated,
            "error": self.error,
        }


def _detect_source_env() -> str:
    system = platform.system().lower()
    if system == "linux":
        if os.path.exists("/.dockerenv"):
            return "container"
        return "vps"
    if system == "windows":
        return "windows"
    if system == "darwin":
        return "macos"
    return "unknown"


def _is_path_allowed(target: str) -> bool:
    try:
        resolved = os.path.realpath(target)
    except (OSError, ValueError):
        return False

    for root in ALLOWED_ROOTS:
        root_resolved = os.path.realpath(root)
        prefix = root_resolved if root_resolved.endswith(os.sep) else root_resolved + os.sep
        if resolved == root_resolved or resolved.startswith(prefix):
            for pattern in DENIED_PATTERNS:
                if pattern in resolved:
                    return False
            return True
    return False


def _detect_language(name: str) -> str:
    ext = name.rsplit(".", 1)[-1].lower() if "." in name else ""
    lang_map = {
        "py": "python", "ts": "typescript", "tsx": "typescriptreact",
        "js": "javascript", "jsx": "javascriptreact", "json": "json",
        "md": "markdown", "yaml": "yaml", "yml": "yaml", "toml": "toml",
        "sql": "sql", "sh": "shellscript", "css": "css", "html": "html",
        "rs": "rust", "go": "go", "rb": "ruby", "java": "java",
    }
    return lang_map.get(ext, "plaintext")


MAX_FILE_SIZE = 512 * 1024  # 512 KB read limit


def browse_directory(target_path: str) -> BrowseResult:
    if not _is_path_allowed(target_path):
        return BrowseResult(
            ok=False,
            path=target_path,
            error="Path not in allowlist or contains denied pattern",
        )

    resolved = os.path.realpath(target_path)
    if not os.path.isdir(resolved):
        return BrowseResult(ok=False, path=target_path, error="Not a directory")

    source_env = _detect_source_env()
    entries: list[FileEntry] = []

    try:
        for item in sorted(os.listdir(resolved)):
            item_path = os.path.join(resolved, item)
            if not _is_path_allowed(item_path):
                continue
            try:
                stat = os.stat(item_path)
                entry_type = "directory" if os.path.isdir(item_path) else "file"
                entries.append(FileEntry(
                    name=item,
                    path=item_path,
                    entry_type=entry_type,
                    size=stat.st_size if entry_type == "file" else 0,
                    source_env=source_env,
                ))
            except OSError:
                continue
    except OSError as e:
        return BrowseResult(ok=False, path=target_path, error=str(e))

    return BrowseResult(
        ok=True,
        path=resolved,
        source_env=source_env,
        entries=entries,
    )


def read_file(target_path: str) -> FileReadResult:
    if not _is_path_allowed(target_path):
        return FileReadResult(
            ok=False,
            path=target_path,
            error="Path not in allowlist or contains denied pattern",
        )

    resolved = os.path.realpath(target_path)
    if not os.path.isfile(resolved):
        return FileReadResult(ok=False, path=target_path, error="Not a file")

    source_env = _detect_source_env()
    name = os.path.basename(resolved)

    try:
        size = os.path.getsize(resolved)
        truncated = size > MAX_FILE_SIZE
        with open(resolved, "r", errors="replace") as f:
            content = f.read(MAX_FILE_SIZE)
    except OSError as e:
        return FileReadResult(ok=False, path=target_path, error=str(e))

    return FileReadResult(
        ok=True,
        path=resolved,
        source_env=source_env,
        content=content,
        size=size,
        language=_detect_language(name),
        truncated=truncated,
    )
