"""Phase 76 filesystem adapter — safe read/write/list with root enforcement.

All paths are resolved to absolute form and checked against configured
safe roots before any operation.  Path traversal is rejected.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from umh.adapters.mvp_contract import (
    AdapterRequest,
    AdapterResult,
    AdapterStatus,
    MVPAdapter,
)

DEFAULT_SAFE_ROOTS: tuple[str, ...] = ("/opt/OS", "/tmp/umh")

_BLOCKED_PATTERNS = frozenset(
    {
        ".env",
        ".ssh",
        "id_rsa",
        "id_ed25519",
        "credentials",
        "secrets",
        ".aws",
        ".gcp",
        ".kube",
    }
)

_BLOCKED_DIRECTORIES = frozenset(
    {
        "/etc/shadow",
        "/etc/passwd",
        "/root/.ssh",
        "/proc",
        "/sys",
        "/dev",
    }
)


def _resolve_safe(path_str: str, safe_roots: tuple[str, ...]) -> str | None:
    """Resolve path and return it if under a safe root, else None."""
    try:
        resolved = str(Path(path_str).resolve())
    except (ValueError, OSError):
        return None

    for root in safe_roots:
        root_resolved = str(Path(root).resolve())
        if resolved == root_resolved or resolved.startswith(root_resolved + "/"):
            return resolved
    return None


def _is_blocked_path(resolved: str) -> str | None:
    """Return reason if path matches a blocked pattern."""
    base = os.path.basename(resolved).lower()
    for pattern in _BLOCKED_PATTERNS:
        if pattern in base:
            return f"Path contains blocked pattern: {pattern}"

    for blocked in _BLOCKED_DIRECTORIES:
        if resolved.startswith(blocked):
            return f"Path in blocked directory: {blocked}"

    return None


class FilesystemAdapter:
    """Safe filesystem operations with root enforcement."""

    def __init__(self, safe_roots: tuple[str, ...] = DEFAULT_SAFE_ROOTS) -> None:
        self._safe_roots = safe_roots

    @property
    def name(self) -> str:
        return "filesystem"

    @property
    def supported_capabilities(self) -> frozenset[str]:
        return frozenset({"filesystem.read", "filesystem.write", "filesystem.list"})

    @property
    def supported_environments(self) -> frozenset[str]:
        return frozenset({"local", "vps", "filesystem"})

    def validate(self, request: AdapterRequest) -> AdapterResult | None:
        path_str = request.inputs.get("path", "")
        if not path_str:
            return AdapterResult(
                request_id=request.request_id,
                adapter_name=self.name,
                capability=request.capability,
                action=request.action,
                status=AdapterStatus.VALIDATION_FAILED,
                error="No path provided",
            )

        resolved = _resolve_safe(path_str, self._safe_roots)
        if resolved is None:
            return AdapterResult(
                request_id=request.request_id,
                adapter_name=self.name,
                capability=request.capability,
                action=request.action,
                status=AdapterStatus.DENIED,
                error=f"Path '{path_str}' is outside safe roots: {', '.join(self._safe_roots)}",
            )

        blocked = _is_blocked_path(resolved)
        if blocked:
            return AdapterResult(
                request_id=request.request_id,
                adapter_name=self.name,
                capability=request.capability,
                action=request.action,
                status=AdapterStatus.DENIED,
                error=blocked,
            )

        if request.capability == "filesystem.write":
            content = request.inputs.get("content")
            if content is None:
                return AdapterResult(
                    request_id=request.request_id,
                    adapter_name=self.name,
                    capability=request.capability,
                    action=request.action,
                    status=AdapterStatus.VALIDATION_FAILED,
                    error="No content provided for write",
                )

        return None

    def execute(self, request: AdapterRequest) -> AdapterResult:
        path_str = request.inputs.get("path", "")
        resolved = _resolve_safe(path_str, self._safe_roots)
        if resolved is None:
            return AdapterResult(
                request_id=request.request_id,
                adapter_name=self.name,
                capability=request.capability,
                action=request.action,
                status=AdapterStatus.DENIED,
                error="Path outside safe roots",
            )

        cap = request.capability
        try:
            if cap == "filesystem.read":
                return self._read(request, resolved)
            elif cap == "filesystem.write":
                return self._write(request, resolved)
            elif cap == "filesystem.list":
                return self._list(request, resolved)
            else:
                return AdapterResult(
                    request_id=request.request_id,
                    adapter_name=self.name,
                    capability=cap,
                    action=request.action,
                    status=AdapterStatus.UNSUPPORTED,
                    error=f"Unsupported capability: {cap}",
                )
        except Exception as e:
            return AdapterResult(
                request_id=request.request_id,
                adapter_name=self.name,
                capability=cap,
                action=request.action,
                status=AdapterStatus.FAILURE,
                error=str(e),
            )

    def _read(self, request: AdapterRequest, resolved: str) -> AdapterResult:
        if not os.path.exists(resolved):
            return AdapterResult(
                request_id=request.request_id,
                adapter_name=self.name,
                capability=request.capability,
                action=request.action,
                status=AdapterStatus.FAILURE,
                error=f"File not found: {resolved}",
                output={"path": resolved, "exists": False},
            )

        if os.path.isdir(resolved):
            return AdapterResult(
                request_id=request.request_id,
                adapter_name=self.name,
                capability=request.capability,
                action=request.action,
                status=AdapterStatus.FAILURE,
                error="Path is a directory, use filesystem.list",
                output={"path": resolved, "is_dir": True},
            )

        size = os.path.getsize(resolved)
        max_bytes = request.constraints.get("max_bytes", 100_000)
        content = Path(resolved).read_text(errors="replace")[:max_bytes]
        return AdapterResult(
            request_id=request.request_id,
            adapter_name=self.name,
            capability=request.capability,
            action=request.action,
            status=AdapterStatus.SUCCESS,
            output={
                "path": resolved,
                "content": content,
                "size": size,
                "exists": True,
                "truncated": size > max_bytes,
            },
        )

    def _write(self, request: AdapterRequest, resolved: str) -> AdapterResult:
        content = request.inputs.get("content", "")
        parent = os.path.dirname(resolved)
        os.makedirs(parent, exist_ok=True)
        Path(resolved).write_text(content)
        return AdapterResult(
            request_id=request.request_id,
            adapter_name=self.name,
            capability=request.capability,
            action=request.action,
            status=AdapterStatus.SUCCESS,
            output={
                "path": resolved,
                "bytes_written": len(content.encode()),
                "operation": "write",
            },
        )

    def _list(self, request: AdapterRequest, resolved: str) -> AdapterResult:
        if not os.path.isdir(resolved):
            return AdapterResult(
                request_id=request.request_id,
                adapter_name=self.name,
                capability=request.capability,
                action=request.action,
                status=AdapterStatus.FAILURE,
                error=f"Not a directory: {resolved}",
                output={"path": resolved, "is_dir": False},
            )

        entries = []
        for entry in sorted(os.listdir(resolved))[:200]:
            full = os.path.join(resolved, entry)
            entries.append(
                {
                    "name": entry,
                    "is_dir": os.path.isdir(full),
                    "size": os.path.getsize(full) if os.path.isfile(full) else 0,
                }
            )

        return AdapterResult(
            request_id=request.request_id,
            adapter_name=self.name,
            capability=request.capability,
            action=request.action,
            status=AdapterStatus.SUCCESS,
            output={
                "path": resolved,
                "entries": entries,
                "count": len(entries),
            },
        )
