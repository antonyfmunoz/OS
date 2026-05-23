"""ComponentRegistry — unified registry for all substrate components.

In-memory store backed by Neon component_registry table.
Boot sequence loads existing agents + skills from Neon.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable
from uuid import UUID

from substrate.types import (
    Component,
    ComponentStatus,
    ComponentType,
    RegistrationResult,
)


@runtime_checkable
class ComponentRegistry(Protocol):
    async def register(self, component: Component) -> RegistrationResult: ...
    async def lookup(
        self,
        component_type: ComponentType | None = None,
        capabilities: list[str] | None = None,
    ) -> list[Component]: ...
    async def get(self, component_id: UUID) -> Component | None: ...
    async def deregister(self, component_id: UUID) -> bool: ...


class ConcreteComponentRegistry:
    """In-memory component registry with Neon backing."""

    def __init__(self) -> None:
        self._components: dict[UUID, Component] = {}

    def count(self) -> int:
        return len(self._components)

    async def register(self, component: Component) -> RegistrationResult:
        self._components[component.id] = component
        return RegistrationResult(component_id=component.id, success=True)

    async def lookup(
        self,
        component_type: ComponentType | None = None,
        capabilities: list[str] | None = None,
    ) -> list[Component]:
        results = []
        for comp in self._components.values():
            if comp.status == ComponentStatus.DEREGISTERED:
                continue
            if component_type and comp.component_type != component_type:
                continue
            if capabilities and not all(c in comp.capabilities for c in capabilities):
                continue
            results.append(comp)
        return results

    async def get(self, component_id: UUID) -> Component | None:
        comp = self._components.get(component_id)
        if comp and comp.status != ComponentStatus.DEREGISTERED:
            return comp
        return None

    async def deregister(self, component_id: UUID) -> bool:
        if component_id in self._components:
            self._components[component_id].status = ComponentStatus.DEREGISTERED
            return True
        return False

    async def load_from_neon(self) -> int:
        """Boot: load existing agents + skills from Neon into registry."""
        count = 0
        try:
            import sys

            sys.path.insert(0, "/opt/OS")
            from state.storage.db import get_conn

            with get_conn("munoz-holdings") as cur:
                cur.execute("SELECT id, name FROM agents WHERE active = true")
                for row in cur.fetchall():
                    comp = Component(
                        component_type=ComponentType.AGENT,
                        name=row[1],
                        metadata={"neon_id": row[0]},
                    )
                    await self.register(comp)
                    count += 1
                cur.execute("SELECT id, name FROM skills WHERE status = 'active'")
                for row in cur.fetchall():
                    comp = Component(
                        component_type=ComponentType.SKILL,
                        name=row[1],
                        metadata={"neon_id": row[0]},
                    )
                    await self.register(comp)
                    count += 1
        except Exception:
            pass
        return count
