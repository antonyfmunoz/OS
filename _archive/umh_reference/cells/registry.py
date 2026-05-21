"""Cell type registry — stores cell type definitions and metadata.

In-memory registry of available cell types. Supports registration of
custom cell types with metadata. No execution, no adapters, no shell.
"""

from __future__ import annotations

import threading
from dataclasses import dataclass, field
from typing import Any

from umh.cells.models import CellType
from umh.core.clock import iso_now as _iso_now


@dataclass(frozen=True)
class CellTypeDefinition:
    """Definition of a cell type — its capabilities and constraints."""

    cell_type: CellType
    description: str = ""
    default_authority: str = "propose"
    required_capabilities: tuple[str, ...] = ()
    default_primitives: tuple[str, ...] = ()
    default_constraints: tuple[str, ...] = ()
    registered_at: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        if not self.registered_at:
            object.__setattr__(self, "registered_at", _iso_now())

    def to_dict(self) -> dict[str, Any]:
        return {
            "cell_type": self.cell_type.value,
            "description": self.description,
            "default_authority": self.default_authority,
            "required_capabilities": list(self.required_capabilities),
            "default_primitives": list(self.default_primitives),
            "default_constraints": list(self.default_constraints),
            "registered_at": self.registered_at,
            "metadata": self.metadata,
        }


_lock = threading.Lock()
_definitions: dict[CellType, CellTypeDefinition] = {}


def register_cell_type(definition: CellTypeDefinition) -> None:
    with _lock:
        _definitions[definition.cell_type] = definition


def get_cell_type(cell_type: CellType) -> CellTypeDefinition | None:
    with _lock:
        return _definitions.get(cell_type)


def list_cell_types() -> list[CellTypeDefinition]:
    with _lock:
        return list(_definitions.values())


def clear() -> None:
    """Reset registry — for testing only."""
    with _lock:
        _definitions.clear()


def ensure_default_types() -> list[CellType]:
    """Register default cell type definitions. Idempotent."""
    created: list[CellType] = []

    defaults = [
        CellTypeDefinition(
            cell_type=CellType.INTERPRETATION,
            description="Interprets signals and context into structured understanding.",
            default_primitives=("signal", "state", "constraint"),
        ),
        CellTypeDefinition(
            cell_type=CellType.DECOMPOSITION,
            description="Decomposes objectives into structured task plans.",
            default_primitives=("goal", "action", "resource"),
        ),
        CellTypeDefinition(
            cell_type=CellType.PLANNING,
            description="Creates execution plans from objectives.",
            default_primitives=("goal", "constraint", "resource"),
            default_authority="propose",
        ),
        CellTypeDefinition(
            cell_type=CellType.REVIEW,
            description="Reviews plans and execution results for quality.",
            default_primitives=("feedback", "constraint"),
            default_authority="advise",
        ),
        CellTypeDefinition(
            cell_type=CellType.DEBUG,
            description="Analyzes failures and proposes corrections.",
            default_primitives=("state", "signal", "feedback"),
            default_authority="advise",
        ),
        CellTypeDefinition(
            cell_type=CellType.EXECUTION_REQUESTER,
            description="Requests execution through the control plane bridge.",
            default_primitives=("action", "resource"),
            default_authority="propose",
        ),
        CellTypeDefinition(
            cell_type=CellType.LEARNING,
            description="Extracts patterns and corrections from execution outcomes.",
            default_primitives=("feedback", "signal"),
            default_authority="advise",
        ),
        CellTypeDefinition(
            cell_type=CellType.MONITOR,
            description="Observes system state and emits signals.",
            default_primitives=("state", "signal"),
            default_authority="observe",
        ),
        CellTypeDefinition(
            cell_type=CellType.WORKSTATION,
            description="Manages environment and tooling state.",
            default_primitives=("state", "resource"),
            default_authority="observe",
        ),
    ]

    with _lock:
        for defn in defaults:
            if defn.cell_type not in _definitions:
                _definitions[defn.cell_type] = defn
                created.append(defn.cell_type)

    return created
