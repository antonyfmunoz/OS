"""WorldSubstrate — deterministic entity/relation/state substrate.

The canonical reality layer. Maintains a structured representation of
entities, their relations, observed signals, and derived state facts.

All updates are deterministic. No LLM calls. No randomness. No embeddings.
Append-only observation log with FIFO eviction. Bounded memory.

Numeric state updates use confidence-weighted EMA.
Categorical/bool/string updates: latest high-confidence observation wins.
"""

from __future__ import annotations

import logging
from typing import Any

from umh.world.types import (
    Entity,
    Observation,
    PrimitiveValue,
    Relation,
    StateFact,
    WorldSnapshot,
)

_log = logging.getLogger(__name__)

# ─── Capacity bounds ─────────────────────────────────────────────

MAX_ENTITIES = 500
MAX_RELATIONS = 2000
MAX_OBSERVATIONS = 5000
MAX_STATE_FACTS = 5000

# ─── EMA update constants ────────────────────────────────────────

ALPHA_MIN = 0.05
ALPHA_MAX = 0.30
ALPHA_SCALE = 0.30

# ─── Persistence format ─────────────────────────────────────────

SUBSTRATE_VERSION = 1


class WorldSubstrate:
    """Stateful world model engine with snapshot/restore.

    Thread safety: not thread-safe. Intended for single-session use
    within a runtime that is itself single-threaded per turn.
    """

    def __init__(self) -> None:
        self._entities: dict[str, Entity] = {}
        self._relations: list[Relation] = []
        self._relation_set: set[tuple[str, str, str]] = set()
        self._observations: list[Observation] = []
        self._state_facts: dict[tuple[str, str], StateFact] = {}
        self._version: int = 0

    # ─── Entity management ───────────────────────────────────────

    def add_entity(self, entity: Entity) -> Entity:
        """Register an entity. Overwrites if entity_id already exists."""
        if (
            len(self._entities) >= MAX_ENTITIES
            and entity.entity_id not in self._entities
        ):
            _log.debug(
                "Entity cap reached (%d), rejecting %s", MAX_ENTITIES, entity.entity_id
            )
            return entity
        self._entities[entity.entity_id] = entity
        return entity

    def upsert_entity_attributes(
        self,
        entity_id: str,
        attributes: dict[str, PrimitiveValue],
    ) -> Entity | None:
        """Merge attributes into an existing entity. Returns None if not found."""
        existing = self._entities.get(entity_id)
        if existing is None:
            return None
        merged = dict(existing.attributes)
        merged.update(attributes)
        updated = Entity(
            entity_id=existing.entity_id,
            entity_type=existing.entity_type,
            attributes=merged,
        )
        self._entities[entity_id] = updated
        return updated

    def get_entity(self, entity_id: str) -> Entity | None:
        """Retrieve entity by id."""
        return self._entities.get(entity_id)

    # ─── Relation management ─────────────────────────────────────

    def add_relation(self, relation: Relation) -> bool:
        """Add a relation. Returns False if duplicate or at capacity."""
        key = (relation.source_id, relation.relation_type, relation.target_id)
        if key in self._relation_set:
            return False
        if len(self._relations) >= MAX_RELATIONS:
            _log.debug("Relation cap reached (%d), rejecting", MAX_RELATIONS)
            return False
        self._relations.append(relation)
        self._relation_set.add(key)
        return True

    def get_relations(
        self,
        entity_id: str | None = None,
        relation_type: str | None = None,
    ) -> list[Relation]:
        """Query relations. Filters by entity (source or target) and/or type."""
        result = self._relations
        if entity_id is not None:
            result = [
                r
                for r in result
                if r.source_id == entity_id or r.target_id == entity_id
            ]
        if relation_type is not None:
            result = [r for r in result if r.relation_type == relation_type]
        return result

    # ─── Observation log ─────────────────────────────────────────

    def record_observation(self, obs: Observation) -> None:
        """Append an observation and update derived state."""
        if len(self._observations) >= MAX_OBSERVATIONS:
            self._observations = self._observations[-(MAX_OBSERVATIONS // 2) :]
        self._observations.append(obs)
        self._update_state_fact(obs)

    def get_observations(
        self,
        entity_id: str | None = None,
        signal_type: str | None = None,
        limit: int = 100,
    ) -> list[Observation]:
        """Query the observation log. Most recent first."""
        result = self._observations
        if entity_id is not None:
            result = [o for o in result if o.entity_id == entity_id]
        if signal_type is not None:
            result = [o for o in result if o.signal_type == signal_type]
        return list(reversed(result[-limit:]))

    # ─── State facts ─────────────────────────────────────────────

    def _update_state_fact(self, obs: Observation) -> None:
        """Deterministic state update from a single observation."""
        fact_key = (obs.entity_id, obs.signal_type)

        if (
            len(self._state_facts) >= MAX_STATE_FACTS
            and fact_key not in self._state_facts
        ):
            return

        existing = self._state_facts.get(fact_key)

        if isinstance(obs.value, bool):
            new_fact = self._update_categorical(obs, existing)
        elif isinstance(obs.value, (int, float)):
            new_fact = self._update_numeric(obs, existing)
        else:
            new_fact = self._update_categorical(obs, existing)

        if new_fact is not None:
            self._state_facts[fact_key] = new_fact

    def _update_numeric(
        self,
        obs: Observation,
        existing: StateFact | None,
    ) -> StateFact:
        """Confidence-weighted EMA for numeric observations."""
        alpha = min(max(obs.confidence * ALPHA_SCALE, ALPHA_MIN), ALPHA_MAX)

        if existing is None or not isinstance(existing.value, (int, float)):
            return StateFact(
                entity_id=obs.entity_id,
                key=obs.signal_type,
                value=float(obs.value),
                confidence=obs.confidence,
                last_updated_turn=obs.timestamp_turn,
                update_count=1,
            )

        old_val = float(existing.value)
        new_val = alpha * float(obs.value) + (1.0 - alpha) * old_val

        new_confidence = alpha * obs.confidence + (1.0 - alpha) * existing.confidence

        return StateFact(
            entity_id=obs.entity_id,
            key=obs.signal_type,
            value=round(new_val, 8),
            confidence=round(min(new_confidence, 1.0), 8),
            last_updated_turn=obs.timestamp_turn,
            update_count=existing.update_count + 1,
        )

    def _update_categorical(
        self,
        obs: Observation,
        existing: StateFact | None,
    ) -> StateFact | None:
        """Latest high-confidence observation wins for non-numeric values.

        Tie-breaking: higher confidence wins. If equal, later turn wins.
        If equal turn, lexicographic observation_id wins (deterministic).
        """
        if existing is None:
            return StateFact(
                entity_id=obs.entity_id,
                key=obs.signal_type,
                value=obs.value,
                confidence=obs.confidence,
                last_updated_turn=obs.timestamp_turn,
                update_count=1,
            )

        should_replace = False
        if obs.confidence > existing.confidence:
            should_replace = True
        elif obs.confidence == existing.confidence:
            if obs.timestamp_turn > existing.last_updated_turn:
                should_replace = True
            elif obs.timestamp_turn == existing.last_updated_turn:
                # Deterministic tiebreak on observation_id
                obs_key = (obs.entity_id, obs.signal_type)
                last_obs = self._find_last_observation(obs_key)
                if last_obs is None or obs.observation_id > last_obs.observation_id:
                    should_replace = True

        if not should_replace:
            return StateFact(
                entity_id=existing.entity_id,
                key=existing.key,
                value=existing.value,
                confidence=existing.confidence,
                last_updated_turn=existing.last_updated_turn,
                update_count=existing.update_count + 1,
            )

        return StateFact(
            entity_id=obs.entity_id,
            key=obs.signal_type,
            value=obs.value,
            confidence=obs.confidence,
            last_updated_turn=obs.timestamp_turn,
            update_count=existing.update_count + 1,
        )

    def _find_last_observation(self, fact_key: tuple[str, str]) -> Observation | None:
        """Find the most recent observation matching this (entity_id, signal_type)."""
        entity_id, signal_type = fact_key
        for obs in reversed(self._observations):
            if obs.entity_id == entity_id and obs.signal_type == signal_type:
                return obs
        return None

    def get_state_fact(self, entity_id: str, key: str) -> StateFact | None:
        """Get a single derived state fact."""
        return self._state_facts.get((entity_id, key))

    def get_entity_state(self, entity_id: str) -> list[StateFact]:
        """Get all derived state facts for an entity."""
        return [
            f for (eid, _), f in sorted(self._state_facts.items()) if eid == entity_id
        ]

    # ─── Snapshot ─────────────────────────────────────────────────

    def build_snapshot(self) -> WorldSnapshot:
        """Build an immutable snapshot of the current world view."""
        self._version += 1
        return WorldSnapshot(
            entities=tuple(self._entities[k] for k in sorted(self._entities)),
            relations=tuple(self._relations),
            state_facts=tuple(self._state_facts[k] for k in sorted(self._state_facts)),
            observation_count=len(self._observations),
            version=self._version,
        )

    # ─── Persistence ─────────────────────────────────────────────

    def snapshot(self) -> dict[str, Any]:
        """Serialize full engine state for persistence."""
        return {
            "version": SUBSTRATE_VERSION,
            "data": {
                "entities": [e.to_dict() for e in self._entities.values()],
                "relations": [r.to_dict() for r in self._relations],
                "observations": [o.to_dict() for o in self._observations],
                "state_facts": [f.to_dict() for f in self._state_facts.values()],
                "world_version": self._version,
            },
        }

    def restore(self, data: dict | None) -> bool:
        """Restore engine state from a persisted snapshot.

        Returns True if successfully restored, False on failure/fallback.
        Handles corrupt/missing payload and version mismatch.
        """
        if data is None:
            return False

        if not isinstance(data, dict):
            _log.debug("world_substrate restore: not a dict, ignoring")
            return False

        version = data.get("version", 0)
        if version > SUBSTRATE_VERSION:
            _log.debug(
                "world_substrate restore: version %d > %d, ignoring",
                version,
                SUBSTRATE_VERSION,
            )
            return False

        inner = data.get("data")
        if not isinstance(inner, dict):
            _log.debug("world_substrate restore: missing data payload")
            return False

        try:
            entities = [Entity.from_dict(e) for e in inner.get("entities", [])]
            relations = [Relation.from_dict(r) for r in inner.get("relations", [])]
            observations = [
                Observation.from_dict(o) for o in inner.get("observations", [])
            ]
            state_facts = [StateFact.from_dict(f) for f in inner.get("state_facts", [])]

            self._entities = {e.entity_id: e for e in entities[:MAX_ENTITIES]}
            self._relations = relations[:MAX_RELATIONS]
            self._relation_set = {
                (r.source_id, r.relation_type, r.target_id) for r in self._relations
            }
            self._observations = observations[-MAX_OBSERVATIONS:]
            self._state_facts = {
                (f.entity_id, f.key): f for f in state_facts[:MAX_STATE_FACTS]
            }
            self._version = inner.get("world_version", 0)

            _log.debug(
                "world_substrate restored: %d entities, %d relations, "
                "%d observations, %d facts, version=%d",
                len(self._entities),
                len(self._relations),
                len(self._observations),
                len(self._state_facts),
                self._version,
            )
            return True

        except (KeyError, TypeError, ValueError) as e:
            _log.debug("world_substrate restore failed: %s", e)
            return False

    # ─── Diagnostics ─────────────────────────────────────────────

    def summary(self) -> dict[str, int]:
        """Return a diagnostic summary of engine state."""
        return {
            "entity_count": len(self._entities),
            "relation_count": len(self._relations),
            "observation_count": len(self._observations),
            "state_fact_count": len(self._state_facts),
            "version": self._version,
        }
