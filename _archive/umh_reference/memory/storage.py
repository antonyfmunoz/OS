"""UMH StorageBackend — backward-compatible re-export.

Canonical definitions live in umh.storage.backend.
This module re-exports them so existing imports continue to work.
"""

from __future__ import annotations

from typing import Any

from umh.storage.backend import InMemoryStorage, StorageBackend


def _default_storage() -> StorageBackend:
    """Resolve the default storage backend.

    Attempts to load a platform storage adapter via the bridge. Falls back
    to InMemoryStorage if unavailable (e.g. running UMH standalone).
    """
    from umh.adapters.bridge import discover_platform_adapter

    adapter = discover_platform_adapter(
        "umh.adapters.umh_storage", "get_umh_storage"
    )
    if adapter is not None:
        return adapter
    return InMemoryStorage()


_STORAGE_INSTANCE: StorageBackend | None = None


def get_storage() -> StorageBackend:
    """Get the UMH storage backend singleton.

    On first call, resolves the default backend. Can be overridden
    via set_storage() for testing or alternative deployments.
    """
    global _STORAGE_INSTANCE
    if _STORAGE_INSTANCE is None:
        _STORAGE_INSTANCE = _default_storage()
    return _STORAGE_INSTANCE


def set_storage(backend: StorageBackend) -> None:
    """Override the storage backend (for testing or custom deployments)."""
    global _STORAGE_INSTANCE
    _STORAGE_INSTANCE = backend


def reset_storage() -> None:
    """Clear the storage singleton (for testing)."""
    global _STORAGE_INSTANCE
    _STORAGE_INSTANCE = None
