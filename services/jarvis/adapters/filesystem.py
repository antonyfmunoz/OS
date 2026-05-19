"""Filesystem adapter — governed read/write/list/stat operations."""

from __future__ import annotations

import os
import re
from pathlib import Path
from typing import Any

from services.jarvis.adapters.base import BaseAdapter
from services.jarvis.governance.risk_classes import RiskClass

_READ_OPS = frozenset({"read", "list", "stat", "exists", "glob"})
_WRITE_OPS = frozenset({"write", "append", "mkdir"})


class FilesystemAdapter(BaseAdapter):
    """Filesystem access with safe-root enforcement.

    Reads are unrestricted. Writes are only allowed inside
    declared safe roots. Deletes are denied by default.
    """

    _DENIED_OPERATIONS: frozenset[str] = frozenset({"delete", "rm", "rmdir", "unlink", "chmod", "chown"})

    def __init__(self, safe_roots: list[str] | None = None) -> None:
        self._safe_roots = [os.path.realpath(r) for r in (safe_roots or [])]

    @property
    def name(self) -> str:
        return "filesystem"

    @property
    def safe_roots(self) -> list[str]:
        return list(self._safe_roots)

    def classify_risk(self, operation: str, params: dict[str, Any]) -> RiskClass:
        if operation in _READ_OPS:
            return RiskClass.READ_ONLY
        if operation in _WRITE_OPS:
            target = params.get("path", "")
            if self._is_safe_rooted(target):
                return RiskClass.SAFE_WRITE
            return RiskClass.REVERSIBLE_WRITE
        return RiskClass.IRREVERSIBLE_WRITE

    def _is_safe_rooted(self, path: str) -> bool:
        if not path:
            return False
        try:
            resolved = os.path.realpath(path)
        except (OSError, ValueError):
            return False
        return any(resolved.startswith(root + os.sep) or resolved == root for root in self._safe_roots)

    def _execute_impl(self, operation: str, params: dict[str, Any]) -> dict[str, Any]:
        if operation == "read":
            return self._op_read(params)
        if operation == "list":
            return self._op_list(params)
        if operation == "stat":
            return self._op_stat(params)
        if operation == "exists":
            return self._op_exists(params)
        if operation == "glob":
            return self._op_glob(params)
        if operation == "write":
            return self._op_write(params)
        if operation == "append":
            return self._op_append(params)
        if operation == "mkdir":
            return self._op_mkdir(params)
        raise ValueError(f"unknown filesystem operation: {operation}")

    def _op_read(self, params: dict[str, Any]) -> dict[str, Any]:
        path = Path(params["path"])
        max_bytes = params.get("max_bytes", 1_000_000)
        content = path.read_text(encoding="utf-8", errors="replace")[:max_bytes]
        return {
            "content": content,
            "path": str(path),
            "size_bytes": path.stat().st_size,
        }

    def _op_list(self, params: dict[str, Any]) -> dict[str, Any]:
        path = Path(params["path"])
        entries = []
        for entry in sorted(path.iterdir()):
            entries.append({
                "name": entry.name,
                "is_dir": entry.is_dir(),
                "size": entry.stat().st_size if entry.is_file() else 0,
            })
        return {"path": str(path), "entries": entries, "count": len(entries)}

    def _op_stat(self, params: dict[str, Any]) -> dict[str, Any]:
        path = Path(params["path"])
        st = path.stat()
        return {
            "path": str(path),
            "size": st.st_size,
            "modified": st.st_mtime,
            "is_file": path.is_file(),
            "is_dir": path.is_dir(),
        }

    def _op_exists(self, params: dict[str, Any]) -> dict[str, Any]:
        path = Path(params["path"])
        return {"path": str(path), "exists": path.exists()}

    def _op_glob(self, params: dict[str, Any]) -> dict[str, Any]:
        path = Path(params.get("root", "."))
        pattern = params.get("pattern", "*")
        matches = [str(p) for p in sorted(path.glob(pattern))[:500]]
        return {"root": str(path), "pattern": pattern, "matches": matches, "count": len(matches)}

    def _op_write(self, params: dict[str, Any]) -> dict[str, Any]:
        path_str = params["path"]
        if not self._is_safe_rooted(path_str):
            raise PermissionError(f"write denied — {path_str} is not inside a safe root")
        path = Path(path_str)
        path.parent.mkdir(parents=True, exist_ok=True)
        content = params.get("content", "")
        path.write_text(content, encoding="utf-8")
        return {
            "path": str(path),
            "bytes_written": len(content.encode("utf-8")),
            "_side_effects": [f"wrote {path_str}"],
        }

    def _op_append(self, params: dict[str, Any]) -> dict[str, Any]:
        path_str = params["path"]
        if not self._is_safe_rooted(path_str):
            raise PermissionError(f"append denied — {path_str} is not inside a safe root")
        path = Path(path_str)
        content = params.get("content", "")
        with path.open("a", encoding="utf-8") as f:
            f.write(content)
        return {
            "path": str(path),
            "bytes_appended": len(content.encode("utf-8")),
            "_side_effects": [f"appended to {path_str}"],
        }

    def _op_mkdir(self, params: dict[str, Any]) -> dict[str, Any]:
        path_str = params["path"]
        if not self._is_safe_rooted(path_str):
            raise PermissionError(f"mkdir denied — {path_str} is not inside a safe root")
        path = Path(path_str)
        path.mkdir(parents=True, exist_ok=True)
        return {"path": str(path), "created": True, "_side_effects": [f"created directory {path_str}"]}
