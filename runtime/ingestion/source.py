"""Source abstraction for the generic ingestion pipeline."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol, runtime_checkable


@dataclass
class RawContent:
    """Content read from a source."""

    content: str
    content_type: str
    size_bytes: int
    sha256: str


@runtime_checkable
class Source(Protocol):
    """Minimum interface for an ingestion source."""

    source_type: str
    source_id: str

    def read(self) -> RawContent: ...

    def metadata(self) -> dict[str, Any]: ...

    def exists(self) -> bool: ...
