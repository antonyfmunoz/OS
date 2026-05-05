"""Shared types for the world substrate and signal ingestion layers.

All types are frozen dataclasses — immutable after creation.
No LLM calls, no external dependencies, no randomness.
"""

from __future__ import annotations

from dataclasses import dataclass, field

# Primitive value type union used across the substrate.
PrimitiveValue = float | int | str | bool | None


@dataclass(frozen=True)
class Entity:
    """A named object in the world model."""

    entity_id: str
    entity_type: str
    attributes: dict[str, PrimitiveValue] = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "entity_id": self.entity_id,
            "entity_type": self.entity_type,
            "attributes": dict(self.attributes),
        }

    @classmethod
    def from_dict(cls, d: dict) -> Entity:
        return cls(
            entity_id=d["entity_id"],
            entity_type=d["entity_type"],
            attributes=dict(d.get("attributes") or {}),
        )


@dataclass(frozen=True)
class Relation:
    """Directional relation between two entities."""

    source_id: str
    relation_type: str
    target_id: str
    weight: float = 1.0

    def to_dict(self) -> dict:
        return {
            "source_id": self.source_id,
            "relation_type": self.relation_type,
            "target_id": self.target_id,
            "weight": self.weight,
        }

    @classmethod
    def from_dict(cls, d: dict) -> Relation:
        return cls(
            source_id=d["source_id"],
            relation_type=d["relation_type"],
            target_id=d["target_id"],
            weight=d.get("weight", 1.0),
        )


@dataclass(frozen=True)
class Observation:
    """Append-only atomic evidence record."""

    observation_id: str
    timestamp_turn: int
    source: str
    entity_id: str
    signal_type: str
    value: float | int | str | bool
    confidence: float
    metadata: dict[str, PrimitiveValue] = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "observation_id": self.observation_id,
            "timestamp_turn": self.timestamp_turn,
            "source": self.source,
            "entity_id": self.entity_id,
            "signal_type": self.signal_type,
            "value": self.value,
            "confidence": self.confidence,
            "metadata": dict(self.metadata),
        }

    @classmethod
    def from_dict(cls, d: dict) -> Observation:
        return cls(
            observation_id=d["observation_id"],
            timestamp_turn=d["timestamp_turn"],
            source=d["source"],
            entity_id=d["entity_id"],
            signal_type=d["signal_type"],
            value=d["value"],
            confidence=d["confidence"],
            metadata=dict(d.get("metadata") or {}),
        )


@dataclass(frozen=True)
class StateFact:
    """Current best-known state for one field of one entity."""

    entity_id: str
    key: str
    value: PrimitiveValue
    confidence: float
    last_updated_turn: int
    update_count: int

    def to_dict(self) -> dict:
        return {
            "entity_id": self.entity_id,
            "key": self.key,
            "value": self.value,
            "confidence": self.confidence,
            "last_updated_turn": self.last_updated_turn,
            "update_count": self.update_count,
        }

    @classmethod
    def from_dict(cls, d: dict) -> StateFact:
        return cls(
            entity_id=d["entity_id"],
            key=d["key"],
            value=d["value"],
            confidence=d["confidence"],
            last_updated_turn=d["last_updated_turn"],
            update_count=d["update_count"],
        )


@dataclass(frozen=True)
class WorldSnapshot:
    """Immutable snapshot of the current derived world view."""

    entities: tuple[Entity, ...]
    relations: tuple[Relation, ...]
    state_facts: tuple[StateFact, ...]
    observation_count: int
    version: int

    def to_dict(self) -> dict:
        return {
            "entities": [e.to_dict() for e in self.entities],
            "relations": [r.to_dict() for r in self.relations],
            "state_facts": [f.to_dict() for f in self.state_facts],
            "observation_count": self.observation_count,
            "version": self.version,
        }

    @classmethod
    def from_dict(cls, d: dict) -> WorldSnapshot:
        return cls(
            entities=tuple(Entity.from_dict(e) for e in d.get("entities", ())),
            relations=tuple(Relation.from_dict(r) for r in d.get("relations", ())),
            state_facts=tuple(StateFact.from_dict(f) for f in d.get("state_facts", ())),
            observation_count=d.get("observation_count", 0),
            version=d.get("version", 0),
        )
