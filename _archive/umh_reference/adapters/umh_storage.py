"""EOS → UMH storage adapter.

Wraps the existing umh.substrate.storage backend to satisfy the
UMH StorageBackend protocol. This keeps all EOS/Neon/JSON-file
specifics outside of UMH while preserving current behavior.

Usage::

    from umh.adapters.umh_storage import get_umh_storage

    store = get_umh_storage()  # returns SubstrateStorage wrapped as StorageBackend
"""

from __future__ import annotations

from typing import Any


class SubstrateStorageAdapter:
    """Adapts umh.substrate.storage to the UMH StorageBackend protocol."""

    def __init__(self) -> None:
        from umh.substrate.storage import get_storage as _get_substrate_storage

        self._inner = _get_substrate_storage()

    def get(self, key: str, default: Any = None) -> Any:
        return self._inner.get(key, default)

    def put(self, key: str, value: Any) -> None:
        self._inner.put(key, value)

    def all_keys(self) -> list[str]:
        return self._inner.all_keys()


_ADAPTER_INSTANCE: SubstrateStorageAdapter | None = None


def get_umh_storage() -> SubstrateStorageAdapter:
    """Get the singleton UMH storage adapter backed by EOS substrate storage."""
    global _ADAPTER_INSTANCE
    if _ADAPTER_INSTANCE is None:
        _ADAPTER_INSTANCE = SubstrateStorageAdapter()
    return _ADAPTER_INSTANCE
