"""Signal ingestion layer — raw signal → structured observation → world state.

Validates, normalizes, and maps raw signals into Observation(s) and
optionally inferred Relation(s), then applies them to the WorldSubstrate.

Deterministic. No LLM calls. No randomness. No external dependencies.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field

from umh.world.types import Observation, Relation, PrimitiveValue
from umh.world.substrate import WorldSubstrate, Entity

_log = logging.getLogger(__name__)

# ─── Constants ───────────────────────────────────────────────────

MAX_PAYLOAD_KEYS = 50
CONFIDENCE_MIN = 0.0
CONFIDENCE_MAX = 1.0

RELATION_METADATA_KEYS = frozenset({"related_to", "influences"})


@dataclass(frozen=True)
class RawSignal:
    """External signal before validation and mapping."""

    source: str
    signal_type: str
    target_entity: str
    payload: dict[str, PrimitiveValue]
    confidence: float
    timestamp_turn: int

    def to_dict(self) -> dict:
        return {
            "source": self.source,
            "signal_type": self.signal_type,
            "target_entity": self.target_entity,
            "payload": dict(self.payload),
            "confidence": self.confidence,
            "timestamp_turn": self.timestamp_turn,
        }


@dataclass(frozen=True)
class StructuredSignal:
    """Result of ingesting a raw signal: observations + inferred relations."""

    entity_id: str
    observations: tuple[Observation, ...]
    inferred_relations: tuple[Relation, ...]

    def to_dict(self) -> dict:
        return {
            "entity_id": self.entity_id,
            "observations": [o.to_dict() for o in self.observations],
            "inferred_relations": [r.to_dict() for r in self.inferred_relations],
        }


class SignalIngestionEngine:
    """Validates, parses, and applies raw signals to the world substrate."""

    def __init__(self) -> None:
        self._ingestion_count: int = 0
        self._sources_seen: set[str] = set()

    def ingest(
        self,
        raw_signal: RawSignal,
        world: WorldSubstrate,
    ) -> StructuredSignal | None:
        """Validate, parse, and apply a raw signal to the world model.

        Returns StructuredSignal on success, None if validation fails.
        """
        if not self._validate(raw_signal):
            return None

        entity_id = self._normalize_entity_id(raw_signal.target_entity)

        existing = world.get_entity(entity_id)
        if existing is None:
            world.add_entity(
                Entity(
                    entity_id=entity_id,
                    entity_type=raw_signal.signal_type,
                    attributes={},
                )
            )

        observations = self._parse_payload(raw_signal, entity_id)
        relations = self._infer_relations(raw_signal, entity_id)

        for obs in observations:
            world.record_observation(obs)

        for rel in relations:
            world.add_relation(rel)

        self._ingestion_count += 1
        self._sources_seen.add(raw_signal.source)

        return StructuredSignal(
            entity_id=entity_id,
            observations=tuple(observations),
            inferred_relations=tuple(relations),
        )

    def _validate(self, raw: RawSignal) -> bool:
        """Validate a raw signal for structural correctness."""
        if not raw.source or not raw.source.strip():
            _log.debug("Signal rejected: empty source")
            return False
        if not raw.target_entity or not raw.target_entity.strip():
            _log.debug("Signal rejected: empty target_entity")
            return False
        if not isinstance(raw.payload, dict):
            _log.debug("Signal rejected: payload is not a dict")
            return False
        if len(raw.payload) > MAX_PAYLOAD_KEYS:
            _log.debug("Signal rejected: payload exceeds %d keys", MAX_PAYLOAD_KEYS)
            return False
        if not (CONFIDENCE_MIN <= raw.confidence <= CONFIDENCE_MAX):
            _log.debug("Signal rejected: confidence %.3f out of bounds", raw.confidence)
            return False
        if raw.timestamp_turn < 0:
            _log.debug("Signal rejected: negative timestamp_turn")
            return False
        return True

    def _normalize_entity_id(self, raw_id: str) -> str:
        """Normalize entity ID: strip whitespace, lowercase."""
        return raw_id.strip().lower().replace(" ", "_")

    def _parse_payload(
        self,
        raw: RawSignal,
        entity_id: str,
    ) -> list[Observation]:
        """Map each payload key/value pair to an Observation."""
        observations: list[Observation] = []
        sorted_keys = sorted(raw.payload.keys())

        for i, key in enumerate(sorted_keys):
            if key in RELATION_METADATA_KEYS:
                continue

            value = raw.payload[key]
            if value is None:
                continue

            obs_id = f"obs_{raw.source}_{raw.timestamp_turn}_{entity_id}_{key}_{i}"

            observations.append(
                Observation(
                    observation_id=obs_id,
                    timestamp_turn=raw.timestamp_turn,
                    source=raw.source,
                    entity_id=entity_id,
                    signal_type=key,
                    value=value,
                    confidence=raw.confidence,
                    metadata={
                        "raw_signal_type": raw.signal_type,
                    },
                )
            )
        return observations

    def _infer_relations(
        self,
        raw: RawSignal,
        entity_id: str,
    ) -> list[Relation]:
        """Infer relations from metadata keys in the payload."""
        relations: list[Relation] = []

        for meta_key in RELATION_METADATA_KEYS:
            target = raw.payload.get(meta_key)
            if target is None:
                continue

            if isinstance(target, str) and target.strip():
                normalized_target = self._normalize_entity_id(target)
                relations.append(
                    Relation(
                        source_id=entity_id,
                        relation_type=meta_key,
                        target_id=normalized_target,
                        weight=raw.confidence,
                    )
                )

        return relations

    @property
    def ingestion_count(self) -> int:
        return self._ingestion_count

    @property
    def sources_seen(self) -> frozenset[str]:
        return frozenset(self._sources_seen)

    def get_trace_fields(self) -> dict:
        """Return ingestion stats for decision trace enrichment."""
        return {
            "ingested_signal_count": self._ingestion_count,
            "ingested_signal_sources": tuple(sorted(self._sources_seen)),
        }
