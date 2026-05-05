"""Adapter base contracts — boundary interfaces for external capabilities.

Each adapter type defines the protocol a concrete implementation must
satisfy. Null/stub implementations are provided for standalone operation.

Adapter types:
  LLMAdapter        — language model inference
  ShellAdapter      — system shell commands
  FilesystemAdapter — file read/write
  BrowserAdapter    — web browsing
  WorkstationAdapter — local environment control

All protocols are runtime-checkable. Concrete implementations are
injected by the host environment (EOS, CLI, SaaS runtime, etc.).
"""

from __future__ import annotations

from typing import Any, Protocol, runtime_checkable


@runtime_checkable
class LLMAdapter(Protocol):
    """Contract for language model inference."""

    def generate(self, prompt: str, system: str = "", **kwargs: Any) -> str: ...

    def available(self) -> bool: ...


@runtime_checkable
class ShellAdapter(Protocol):
    """Contract for shell command execution."""

    def run(self, command: str, timeout_s: int = 30) -> tuple[int, str]: ...

    def available(self) -> bool: ...


@runtime_checkable
class FilesystemAdapter(Protocol):
    """Contract for filesystem access."""

    def read(self, path: str) -> str: ...

    def write(self, path: str, content: str) -> None: ...

    def exists(self, path: str) -> bool: ...

    def available(self) -> bool: ...


@runtime_checkable
class BrowserAdapter(Protocol):
    """Contract for web browsing."""

    def navigate(self, url: str) -> str: ...

    def available(self) -> bool: ...


@runtime_checkable
class WorkstationAdapter(Protocol):
    """Contract for local workstation control."""

    def detect_environment(self) -> dict[str, Any]: ...

    def status(self) -> dict[str, Any]: ...

    def available(self) -> bool: ...


# ─── Null/Stub implementations ──────────────────────────────────────────────


class NullLLMAdapter:
    """Stub LLM — echoes input as output."""

    def generate(self, prompt: str, system: str = "", **kwargs: Any) -> str:
        return f"[null-llm] echo: {prompt[:200]}"

    def available(self) -> bool:
        return True


class NullShellAdapter:
    """Stub shell — rejects all commands."""

    def run(self, command: str, timeout_s: int = 30) -> tuple[int, str]:
        return (1, "Shell adapter not configured")

    def available(self) -> bool:
        return False


class NullFilesystemAdapter:
    """Stub filesystem — in-memory store."""

    def __init__(self) -> None:
        self._files: dict[str, str] = {}

    def read(self, path: str) -> str:
        return self._files.get(path, "")

    def write(self, path: str, content: str) -> None:
        self._files[path] = content

    def exists(self, path: str) -> bool:
        return path in self._files

    def available(self) -> bool:
        return True


class NullBrowserAdapter:
    """Stub browser — unavailable."""

    def navigate(self, url: str) -> str:
        return "Browser adapter not configured"

    def available(self) -> bool:
        return False


class NullWorkstationAdapter:
    """Stub workstation — reports minimal environment."""

    def detect_environment(self) -> dict[str, Any]:
        import platform

        return {
            "platform": platform.system(),
            "python": platform.python_version(),
            "adapter": "null",
        }

    def status(self) -> dict[str, Any]:
        return {"state": "stub", "capabilities": []}

    def available(self) -> bool:
        return True


# ─── Adapter registry ────────────────────────────────────────────────────────

_adapters: dict[str, Any] = {}


def get_adapter(name: str) -> Any:
    """Get a registered adapter by name."""
    if name not in _adapters:
        _adapters[name] = _default_adapter(name)
    return _adapters[name]


def set_adapter(name: str, adapter: Any) -> None:
    """Override an adapter (for testing or custom deployments)."""
    _adapters[name] = adapter


def reset_adapters() -> None:
    """Clear all registered adapters."""
    _adapters.clear()


def _default_adapter(name: str) -> Any:
    """Resolve default adapter — tries real adapter, then EOS, falls back to null."""
    if name == "llm":
        from umh.adapters.llm import discover_llm_adapter

        real = discover_llm_adapter()
        if real is not None:
            return real

    defaults: dict[str, Any] = {
        "llm": NullLLMAdapter(),
        "shell": NullShellAdapter(),
        "filesystem": NullFilesystemAdapter(),
        "browser": NullBrowserAdapter(),
        "workstation": NullWorkstationAdapter(),
    }
    return defaults.get(name, NullWorkstationAdapter())


def list_adapters() -> dict[str, bool]:
    """Return adapter availability status."""
    names = ["llm", "shell", "filesystem", "browser", "workstation"]
    return {name: get_adapter(name).available() for name in names}
