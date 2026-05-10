"""Phase 84 surface registry — registered interface surfaces and capabilities.

Metadata only. No UI rendering. No external calls. No execution.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from umh.core.clock import iso_now as _iso_now
from umh.interface.surfaces import (
    InterfaceCapability,
    InterfacePlatform,
    InterfaceSurface,
    InterfaceSurfaceStatus,
    InterfaceSurfaceType,
    SurfaceCapabilityMatrix,
    build_surface_capability_matrix,
    get_default_interface_surfaces,
)


class InterfaceSurfaceRegistry:
    def __init__(self) -> None:
        self._surfaces: dict[str, InterfaceSurface] = {}

    def register_surface(self, surface: InterfaceSurface) -> None:
        self._surfaces[surface.surface_id] = surface

    def register_many(self, surfaces: list[InterfaceSurface]) -> None:
        for s in surfaces:
            self.register_surface(s)

    def get_surface(self, surface_id: str) -> InterfaceSurface | None:
        return self._surfaces.get(surface_id)

    def list_surfaces(
        self,
        surface_type: InterfaceSurfaceType | None = None,
        platform: InterfacePlatform | None = None,
        status: InterfaceSurfaceStatus | None = None,
        limit: int = 100,
    ) -> list[InterfaceSurface]:
        results: list[InterfaceSurface] = []
        for s in self._surfaces.values():
            if surface_type and s.surface_type != surface_type:
                continue
            if platform and s.platform != platform:
                continue
            if status and s.status != status:
                continue
            results.append(s)
            if len(results) >= limit:
                break
        return results

    def query_by_capability(
        self,
        capability: str,
        platform: InterfacePlatform | None = None,
        limit: int = 100,
    ) -> list[InterfaceSurface]:
        results: list[InterfaceSurface] = []
        for s in self._surfaces.values():
            if capability not in s.capabilities:
                continue
            if platform and s.platform != platform:
                continue
            results.append(s)
            if len(results) >= limit:
                break
        return results

    def build_capability_matrix(self, limit: int = 100) -> list[SurfaceCapabilityMatrix]:
        results: list[SurfaceCapabilityMatrix] = []
        for s in list(self._surfaces.values())[:limit]:
            results.append(build_surface_capability_matrix(s))
        return results

    @property
    def surface_count(self) -> int:
        return len(self._surfaces)

    def to_dict(self) -> dict[str, Any]:
        return {
            "surfaces": [s.to_dict() for s in self._surfaces.values()],
            "total": len(self._surfaces),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> InterfaceSurfaceRegistry:
        reg = cls()
        for sd in data.get("surfaces", []):
            reg.register_surface(InterfaceSurface.from_dict(sd))
        return reg


def build_default_surface_registry() -> InterfaceSurfaceRegistry:
    reg = InterfaceSurfaceRegistry()
    reg.register_many(get_default_interface_surfaces())
    return reg


def explain_surface_limitations(surface: InterfaceSurface) -> str:
    if not surface.limitations:
        return f"{surface.name}: no known limitations"
    limits = "; ".join(surface.limitations)
    return f"{surface.name}: {limits}"


def find_best_surface_for_capability(
    registry: InterfaceSurfaceRegistry,
    capability: str,
    platform: InterfacePlatform | None = None,
) -> InterfaceSurface | None:
    candidates = registry.query_by_capability(capability, platform=platform, limit=100)
    available = [
        s
        for s in candidates
        if s.status in (InterfaceSurfaceStatus.AVAILABLE, InterfaceSurfaceStatus.ACTIVE)
    ]
    if available:
        return available[0]
    if candidates:
        return candidates[0]
    return None
