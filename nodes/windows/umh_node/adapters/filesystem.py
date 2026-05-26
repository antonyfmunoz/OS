"""Filesystem adapter — read, write, list, move, delete files."""

from __future__ import annotations

import logging
import os
import shutil
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


class FilesystemAdapter:
    """File operations on the local machine."""

    def execute(self, operation: str, params: dict[str, Any]) -> dict[str, Any]:
        ops = {
            "fs.read": self._read,
            "fs.write": self._write,
            "fs.list": self._list,
            "fs.move": self._move,
            "fs.delete": self._delete,
        }
        handler = ops.get(operation)
        if handler is None:
            return {"success": False, "error": f"unknown operation: {operation}"}
        try:
            return handler(params)
        except Exception as exc:
            return {"success": False, "error": f"{type(exc).__name__}: {exc}"}

    def _read(self, params: dict[str, Any]) -> dict[str, Any]:
        path = Path(params.get("path", ""))
        if not path.exists():
            return {"success": False, "error": f"file not found: {path}"}
        if not path.is_file():
            return {"success": False, "error": f"not a file: {path}"}

        max_bytes = params.get("max_bytes", 1_000_000)
        content = path.read_text(errors="replace")[:max_bytes]
        return {
            "success": True,
            "content": content,
            "size": path.stat().st_size,
            "path": str(path.resolve()),
        }

    def _write(self, params: dict[str, Any]) -> dict[str, Any]:
        path = Path(params.get("path", ""))
        content = params.get("content", "")
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content)
        return {"success": True, "path": str(path.resolve()), "bytes_written": len(content)}

    def _list(self, params: dict[str, Any]) -> dict[str, Any]:
        path = Path(params.get("path", "."))
        if not path.exists():
            return {"success": False, "error": f"directory not found: {path}"}
        if not path.is_dir():
            return {"success": False, "error": f"not a directory: {path}"}

        entries = []
        for item in sorted(path.iterdir()):
            try:
                stat = item.stat()
                entries.append(
                    {
                        "name": item.name,
                        "type": "dir" if item.is_dir() else "file",
                        "size": stat.st_size if item.is_file() else 0,
                    }
                )
            except OSError:
                entries.append({"name": item.name, "type": "unknown", "size": 0})
        return {"success": True, "path": str(path.resolve()), "entries": entries[:500]}

    def _move(self, params: dict[str, Any]) -> dict[str, Any]:
        src = Path(params.get("source", ""))
        dst = Path(params.get("destination", ""))
        if not src.exists():
            return {"success": False, "error": f"source not found: {src}"}
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(src), str(dst))
        return {"success": True, "source": str(src), "destination": str(dst.resolve())}

    def _delete(self, params: dict[str, Any]) -> dict[str, Any]:
        path = Path(params.get("path", ""))
        if not path.exists():
            return {"success": True, "message": "already absent"}
        if path.is_dir():
            shutil.rmtree(path)
        else:
            path.unlink()
        return {"success": True, "deleted": str(path.resolve())}
