"""Canonical Reality Model — compressed, reusable intelligence.

Sacred — updated only through governed promotion. Patterns represent
validated, high-confidence knowledge that has been proven through
repeated observation.

Persists to JSON on disk. Supports entity relationships, confidence
decay over time, and scored search.
"""

from __future__ import annotations

import json
import logging
import math
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

_DEFAULT_STORE_PATH = Path("/opt/OS/data/umh/reality_model/canonical.json")
_HALF_LIFE_DAYS = 180


class CanonicalRelationship(BaseModel):
    source_name: str
    target_name: str
    relation_type: str = "related_to"
    strength: float = Field(ge=0.0, le=1.0, default=0.5)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class CanonicalPattern(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    name: str = Field(max_length=200)
    domain: str = Field(max_length=100)
    description: str = Field(max_length=1000)
    evidence_count: int = Field(ge=0, default=0)
    confidence: float = Field(ge=0.0, le=1.0, default=0.5)
    promoted_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    last_confirmed: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    tags: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)

    def effective_confidence(self, now: datetime | None = None) -> float:
        """Confidence decays with a 180-day half-life since last confirmation."""
        now = now or datetime.now(timezone.utc)
        days_since = (now - self.last_confirmed).total_seconds() / 86400
        if days_since <= 0:
            return self.confidence
        decay = math.pow(0.5, days_since / _HALF_LIFE_DAYS)
        return round(self.confidence * decay, 4)


class CanonicalRealityModel:
    """Graph-based canonical store with JSON persistence.

    Patterns are nodes, relationships are edges. Governance-gated updates.
    """

    def __init__(self, store_path: Path | None = None) -> None:
        self._store_path = store_path or _DEFAULT_STORE_PATH
        self._patterns: dict[str, CanonicalPattern] = {}
        self._relationships: list[CanonicalRelationship] = []
        self._load()

    def _load(self) -> None:
        if not self._store_path.exists():
            return
        try:
            data = json.loads(self._store_path.read_text())
            for p in data.get("patterns", []):
                pattern = CanonicalPattern(**p)
                self._patterns[pattern.name] = pattern
            for r in data.get("relationships", []):
                self._relationships.append(CanonicalRelationship(**r))
        except Exception as e:
            logger.warning("canonical reality model load failed: %s", e)

    def _save(self) -> None:
        try:
            self._store_path.parent.mkdir(parents=True, exist_ok=True)
            data = {
                "patterns": [
                    json.loads(p.model_dump_json()) for p in self._patterns.values()
                ],
                "relationships": [
                    json.loads(r.model_dump_json()) for r in self._relationships
                ],
            }
            self._store_path.write_text(json.dumps(data, indent=2, default=str))
        except Exception as e:
            logger.warning("canonical reality model save failed: %s", e)

    def store(self, pattern: CanonicalPattern) -> UUID:
        existing = self._patterns.get(pattern.name)
        if existing:
            existing.evidence_count += 1
            existing.last_confirmed = datetime.now(timezone.utc)
            existing.confidence = min(1.0, existing.confidence + 0.05)
            self._save()
            return existing.id
        self._patterns[pattern.name] = pattern
        self._save()
        return pattern.id

    def get_by_name(self, name: str) -> CanonicalPattern | None:
        return self._patterns.get(name)

    def list_by_domain(self, domain: str) -> list[CanonicalPattern]:
        return [p for p in self._patterns.values() if p.domain == domain]

    def all(self) -> list[CanonicalPattern]:
        return list(self._patterns.values())

    def search(self, query: str, limit: int = 10) -> list[CanonicalPattern]:
        """Score-based search across name, domain, description, and tags."""
        terms = query.lower().split()
        if not terms:
            return []

        scored: list[tuple[float, CanonicalPattern]] = []
        for pattern in self._patterns.values():
            searchable = f"{pattern.name} {pattern.domain} {pattern.description} {' '.join(pattern.tags)}".lower()
            score = sum(1.0 for t in terms if t in searchable) / len(terms)
            if score > 0:
                score *= pattern.effective_confidence()
                scored.append((score, pattern))

        scored.sort(key=lambda x: x[0], reverse=True)
        return [p for _, p in scored[:limit]]

    def add_relationship(
        self,
        source_name: str,
        target_name: str,
        relation_type: str = "related_to",
        strength: float = 0.5,
    ) -> None:
        if source_name not in self._patterns or target_name not in self._patterns:
            return
        for r in self._relationships:
            if r.source_name == source_name and r.target_name == target_name and r.relation_type == relation_type:
                r.strength = min(1.0, r.strength + 0.1)
                self._save()
                return
        self._relationships.append(
            CanonicalRelationship(
                source_name=source_name,
                target_name=target_name,
                relation_type=relation_type,
                strength=strength,
            )
        )
        self._save()

    def get_related(self, name: str) -> list[tuple[str, str, float]]:
        """Returns (related_name, relation_type, strength) tuples."""
        related: list[tuple[str, str, float]] = []
        for r in self._relationships:
            if r.source_name == name:
                related.append((r.target_name, r.relation_type, r.strength))
            elif r.target_name == name:
                related.append((r.source_name, r.relation_type, r.strength))
        return related

    def update(
        self, name: str, governance_approved: bool = False, **fields: Any
    ) -> CanonicalPattern:
        if not governance_approved:
            raise ValueError(
                "Canonical patterns require governance approval to update. "
                "Pass governance_approved=True after governance gate."
            )
        pattern = self._patterns.get(name)
        if pattern is None:
            raise KeyError(f"Pattern '{name}' not found")
        for key, value in fields.items():
            if hasattr(pattern, key):
                object.__setattr__(pattern, key, value)
        self._save()
        return pattern

    def prune(self, min_confidence: float = 0.05) -> int:
        """Remove patterns whose effective confidence has decayed below threshold."""
        now = datetime.now(timezone.utc)
        to_remove = [
            name for name, p in self._patterns.items()
            if p.effective_confidence(now) < min_confidence
        ]
        for name in to_remove:
            del self._patterns[name]
            self._relationships = [
                r for r in self._relationships
                if r.source_name != name and r.target_name != name
            ]
        if to_remove:
            self._save()
        return len(to_remove)

    def stats(self) -> dict[str, Any]:
        now = datetime.now(timezone.utc)
        patterns = list(self._patterns.values())
        return {
            "pattern_count": len(patterns),
            "relationship_count": len(self._relationships),
            "domains": list(set(p.domain for p in patterns)),
            "avg_confidence": (
                sum(p.effective_confidence(now) for p in patterns) / len(patterns)
                if patterns else 0.0
            ),
            "avg_evidence_count": (
                sum(p.evidence_count for p in patterns) / len(patterns)
                if patterns else 0.0
            ),
        }
