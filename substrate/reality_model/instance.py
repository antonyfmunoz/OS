"""Instance Reality Model — live operational truth of one user/company/environment.

Instance observations are ephemeral, high-volume records of what the system
has seen and done. Unlike canonical patterns (sacred, governance-protected),
instance observations are written freely and decay quickly.

Persists to JSONL on disk. Supports scored search, temporal decay,
domain filtering, and automatic capacity management.
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

_DEFAULT_STORE_PATH = Path("/opt/OS/data/umh/reality_model/instance.jsonl")
_HALF_LIFE_DAYS = 14
_MAX_OBSERVATIONS = 5000


class InstanceObservation(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    content: str = Field(max_length=2000)
    domain: str = Field(default="general", max_length=100)
    confidence: float = Field(ge=0.0, le=1.0, default=0.5)
    source_signal_id: UUID | None = None
    source_trace_id: UUID | None = None
    observed_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    tags: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)

    def effective_confidence(self, now: datetime | None = None) -> float:
        """Confidence decays with a 14-day half-life (instance data is ephemeral)."""
        now = now or datetime.now(timezone.utc)
        days_since = (now - self.observed_at).total_seconds() / 86400
        if days_since <= 0:
            return self.confidence
        decay = math.pow(0.5, days_since / _HALF_LIFE_DAYS)
        return round(self.confidence * decay, 4)


class InstanceRealityModel:
    """JSONL-persisted instance observation store with scored search.

    Writes are append-only (JSONL). Reads load all into memory on init.
    Capacity management prunes oldest entries when limit is reached.
    """

    def __init__(
        self,
        user_id: str,
        org_id: str,
        store_path: Path | None = None,
        max_observations: int = _MAX_OBSERVATIONS,
    ) -> None:
        self.user_id = user_id
        self.org_id = org_id
        self._store_path = store_path or _DEFAULT_STORE_PATH
        self._max = max_observations
        self._observations: list[InstanceObservation] = []
        self._load()

    def _load(self) -> None:
        if not self._store_path.exists():
            return
        try:
            with open(self._store_path) as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        self._observations.append(
                            InstanceObservation(**json.loads(line))
                        )
                    except Exception:
                        pass
        except Exception as e:
            logger.warning("instance reality model load failed: %s", e)

    def _append_to_disk(self, observation: InstanceObservation) -> None:
        try:
            self._store_path.parent.mkdir(parents=True, exist_ok=True)
            with open(self._store_path, "a") as f:
                f.write(observation.model_dump_json() + "\n")
        except Exception as e:
            logger.warning("instance observation persist failed: %s", e)

    def _rewrite(self) -> None:
        """Rewrite the full JSONL file from in-memory state (after prune)."""
        try:
            self._store_path.parent.mkdir(parents=True, exist_ok=True)
            with open(self._store_path, "w") as f:
                for obs in self._observations:
                    f.write(obs.model_dump_json() + "\n")
        except Exception as e:
            logger.warning("instance reality model rewrite failed: %s", e)

    def record(self, observation: InstanceObservation) -> UUID:
        self._observations.append(observation)
        self._append_to_disk(observation)
        if len(self._observations) > self._max:
            self._prune_oldest(self._max // 5)
        return observation.id

    def query(self, text: str, limit: int = 10) -> list[InstanceObservation]:
        """Score-based search: term frequency in content/domain/tags, weighted by recency."""
        terms = text.lower().split()
        if not terms:
            return []

        now = datetime.now(timezone.utc)
        scored: list[tuple[float, InstanceObservation]] = []

        for obs in self._observations:
            searchable = f"{obs.content} {obs.domain} {' '.join(obs.tags)}".lower()
            term_score = sum(1.0 for t in terms if t in searchable) / len(terms)
            if term_score > 0:
                score = term_score * obs.effective_confidence(now)
                scored.append((score, obs))

        scored.sort(key=lambda x: x[0], reverse=True)
        return [obs for _, obs in scored[:limit]]

    def list_by_domain(self, domain: str) -> list[InstanceObservation]:
        return [obs for obs in self._observations if obs.domain == domain]

    def recent(self, limit: int = 20) -> list[InstanceObservation]:
        """Most recent observations, newest first."""
        return list(reversed(self._observations[-limit:]))

    def all(self) -> list[InstanceObservation]:
        return list(self._observations)

    def count(self) -> int:
        return len(self._observations)

    def _prune_oldest(self, count: int) -> int:
        """Remove the oldest N observations and rewrite the JSONL file."""
        if count >= len(self._observations):
            return 0
        removed = self._observations[:count]
        self._observations = self._observations[count:]
        self._rewrite()
        return len(removed)

    def prune_decayed(self, min_confidence: float = 0.01) -> int:
        """Remove observations whose effective confidence has decayed below threshold."""
        now = datetime.now(timezone.utc)
        before = len(self._observations)
        self._observations = [
            obs for obs in self._observations
            if obs.effective_confidence(now) >= min_confidence
        ]
        pruned = before - len(self._observations)
        if pruned > 0:
            self._rewrite()
        return pruned

    def stats(self) -> dict[str, Any]:
        now = datetime.now(timezone.utc)
        return {
            "observation_count": len(self._observations),
            "domains": list(set(obs.domain for obs in self._observations)),
            "avg_effective_confidence": (
                sum(obs.effective_confidence(now) for obs in self._observations)
                / len(self._observations)
                if self._observations else 0.0
            ),
            "oldest": (
                self._observations[0].observed_at.isoformat()
                if self._observations else None
            ),
            "newest": (
                self._observations[-1].observed_at.isoformat()
                if self._observations else None
            ),
        }
