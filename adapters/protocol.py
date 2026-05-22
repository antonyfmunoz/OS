from __future__ import annotations

from typing import Protocol, runtime_checkable
from uuid import UUID

from substrate.types import AdapterRequest, AdapterResponse


@runtime_checkable
class Adapter(Protocol):
    """Every external system connection implements this."""

    adapter_id: UUID
    adapter_type: str
    name: str

    async def execute(self, request: AdapterRequest) -> AdapterResponse: ...
    async def health_check(self) -> bool: ...
    def capabilities(self) -> list[str]: ...
