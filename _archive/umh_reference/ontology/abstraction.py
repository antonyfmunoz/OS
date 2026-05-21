"""Phase 81 abstraction layers — ordered layers from universal to instance.

No execution. No mutation. No adapter calls. No LLM calls.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class AbstractionLayer(str, Enum):
    UNIVERSAL = "universal"
    DOMAIN = "domain"
    SYSTEM = "system"
    SUBSYSTEM = "subsystem"
    WORKFLOW = "workflow"
    TOOL = "tool"
    RESOURCE = "resource"
    HUMAN = "human"
    ORGANIZATION = "organization"
    ENVIRONMENT = "environment"
    INSTANCE = "instance"
    META_SYSTEM = "meta_system"
    UNKNOWN = "unknown"


_LAYER_ORDER = {
    AbstractionLayer.UNIVERSAL: 0,
    AbstractionLayer.META_SYSTEM: 1,
    AbstractionLayer.DOMAIN: 2,
    AbstractionLayer.ORGANIZATION: 3,
    AbstractionLayer.SYSTEM: 4,
    AbstractionLayer.SUBSYSTEM: 5,
    AbstractionLayer.WORKFLOW: 6,
    AbstractionLayer.HUMAN: 7,
    AbstractionLayer.ENVIRONMENT: 8,
    AbstractionLayer.TOOL: 9,
    AbstractionLayer.RESOURCE: 10,
    AbstractionLayer.INSTANCE: 11,
    AbstractionLayer.UNKNOWN: 99,
}


def normalize_abstraction_layer(value: str) -> AbstractionLayer:
    v = value.strip().lower()
    for m in AbstractionLayer:
        if m.value == v:
            return m
    return AbstractionLayer.UNKNOWN


def is_higher_layer(a: AbstractionLayer, b: AbstractionLayer) -> bool:
    return _LAYER_ORDER.get(a, 99) < _LAYER_ORDER.get(b, 99)


def is_lower_layer(a: AbstractionLayer, b: AbstractionLayer) -> bool:
    return _LAYER_ORDER.get(a, 99) > _LAYER_ORDER.get(b, 99)


@dataclass
class AbstractionNode:
    node_id: str
    name: str = ""
    layer: AbstractionLayer = AbstractionLayer.UNKNOWN
    parent_id: str = ""
    primitive_refs: list[str] = field(default_factory=list)
    law_refs: list[str] = field(default_factory=list)
    description: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "node_id": self.node_id,
            "name": self.name,
            "layer": self.layer.value,
            "parent_id": self.parent_id,
            "primitive_refs": self.primitive_refs,
            "law_refs": self.law_refs,
            "description": self.description,
            "metadata": self.metadata,
        }


@dataclass
class AbstractionPath:
    path_id: str
    source_layer: AbstractionLayer = AbstractionLayer.UNKNOWN
    target_layer: AbstractionLayer = AbstractionLayer.UNKNOWN
    nodes: list[str] = field(default_factory=list)
    preserved_primitives: list[str] = field(default_factory=list)
    transformed_primitives: list[str] = field(default_factory=list)
    lost_information: list[str] = field(default_factory=list)
    confidence: float = 0.5
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "path_id": self.path_id,
            "source_layer": self.source_layer.value,
            "target_layer": self.target_layer.value,
            "nodes": self.nodes,
            "preserved_primitives": self.preserved_primitives,
            "transformed_primitives": self.transformed_primitives,
            "lost_information": self.lost_information,
            "confidence": self.confidence,
            "metadata": self.metadata,
        }


def create_abstraction_node(
    name: str,
    layer: str,
    parent_id: str = "",
    primitive_refs: list[str] | None = None,
    law_refs: list[str] | None = None,
    description: str = "",
) -> AbstractionNode:
    return AbstractionNode(
        node_id=f"anode_{uuid.uuid4().hex[:10]}",
        name=name,
        layer=normalize_abstraction_layer(layer),
        parent_id=parent_id,
        primitive_refs=primitive_refs or [],
        law_refs=law_refs or [],
        description=description,
    )


def build_abstraction_path(
    source: AbstractionLayer,
    target: AbstractionLayer,
    nodes: list[str] | None = None,
    preserved: list[str] | None = None,
    transformed: list[str] | None = None,
    lost: list[str] | None = None,
) -> AbstractionPath:
    return AbstractionPath(
        path_id=f"apath_{uuid.uuid4().hex[:10]}",
        source_layer=source,
        target_layer=target,
        nodes=nodes or [],
        preserved_primitives=preserved or [],
        transformed_primitives=transformed or [],
        lost_information=lost or [],
        confidence=0.6,
    )
