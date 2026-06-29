"""Surface Switching Cost Tracker — measures continuity across UMH surfaces.

Records surface switch events and measures how much context, state,
and continuity survives the transition. A perfect meta-harness has
zero switching cost — the operator is always inside the same organism.

C33 Benchmark G infrastructure.

UMH substrate subsystem. Instance-agnostic.
"""

from __future__ import annotations

import json
import logging
import os
import time
from dataclasses import asdict, dataclass, field
from typing import Any
from uuid import uuid4

logger = logging.getLogger(__name__)

_REPO_ROOT = os.environ.get("UMH_ROOT", "/opt/OS")
_DEFAULT_STORE = os.path.join(_REPO_ROOT, "data", "umh", "c33", "surface_switches.jsonl")

VALID_SURFACES = frozenset({
    "cockpit", "cli", "discord", "mobile", "desktop",
    "ssh", "terminal", "voice", "api", "browser",
})

# Composite score weights
_WEIGHTS = {
    "context_restored_pct": 0.30,
    "resume_time_seconds": 0.20,
    "objectives_preserved": 0.15,
    "work_packets_preserved": 0.15,
    "memory_continuous": 0.10,
    "execution_continuous": 0.10,
}


@dataclass
class SurfaceSwitchEvent:
    event_id: str = field(default_factory=lambda: f"sw-{uuid4().hex[:8]}")
    timestamp: float = field(default_factory=time.time)
    from_surface: str = ""
    to_surface: str = ""
    context_restored_pct: float = 0.0
    resume_time_seconds: float = 0.0
    info_lost: list[str] = field(default_factory=list)
    objectives_preserved: bool = True
    work_packets_preserved: bool = True
    memory_continuous: bool = True
    conversation_continuous: bool = True
    execution_continuous: bool = True

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> SurfaceSwitchEvent:
        fields = {k: v for k, v in d.items() if k in cls.__dataclass_fields__}
        return cls(**fields)


class SurfaceSwitchingScorer:
    """Tracks and scores surface switching cost for C33 Benchmark G."""

    def __init__(self, store_path: str = "") -> None:
        self._store_path = store_path or _DEFAULT_STORE
        self._events: list[SurfaceSwitchEvent] = []
        self._load()

    def _load(self) -> None:
        if not os.path.isfile(self._store_path):
            return
        try:
            with open(self._store_path) as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        d = json.loads(line)
                        self._events.append(SurfaceSwitchEvent.from_dict(d))
                    except (json.JSONDecodeError, TypeError) as exc:
                        logger.debug("Skip malformed switch event: %s", exc)
        except OSError as exc:
            logger.debug("Cannot read %s: %s", self._store_path, exc)

    def _persist(self, event: SurfaceSwitchEvent) -> None:
        os.makedirs(os.path.dirname(self._store_path), exist_ok=True)
        try:
            with open(self._store_path, "a") as f:
                f.write(json.dumps(event.to_dict(), default=str) + "\n")
        except OSError as exc:
            logger.debug("Failed to persist switch event: %s", exc)

    def record_switch(
        self,
        from_surface: str,
        to_surface: str,
        context_restored_pct: float = 0.0,
        resume_time_seconds: float = 0.0,
        info_lost: list[str] | None = None,
        objectives_preserved: bool = True,
        work_packets_preserved: bool = True,
        memory_continuous: bool = True,
        conversation_continuous: bool = True,
        execution_continuous: bool = True,
    ) -> SurfaceSwitchEvent:
        """Record a surface switch and return the event."""
        event = SurfaceSwitchEvent(
            from_surface=from_surface,
            to_surface=to_surface,
            context_restored_pct=context_restored_pct,
            resume_time_seconds=resume_time_seconds,
            info_lost=info_lost or [],
            objectives_preserved=objectives_preserved,
            work_packets_preserved=work_packets_preserved,
            memory_continuous=memory_continuous,
            conversation_continuous=conversation_continuous,
            execution_continuous=execution_continuous,
        )
        self._events.append(event)
        self._persist(event)
        return event

    def score_switch(self, event: SurfaceSwitchEvent) -> float:
        """Score a single switch event. Returns 0.0-1.0 composite."""
        context_score = min(1.0, max(0.0, event.context_restored_pct / 100.0))
        resume_score = max(0.0, 1.0 - (event.resume_time_seconds / 60.0))
        obj_score = 1.0 if event.objectives_preserved else 0.0
        wp_score = 1.0 if event.work_packets_preserved else 0.0
        mem_score = 1.0 if event.memory_continuous else 0.0
        exec_score = 1.0 if event.execution_continuous else 0.0

        composite = (
            context_score * _WEIGHTS["context_restored_pct"]
            + resume_score * _WEIGHTS["resume_time_seconds"]
            + obj_score * _WEIGHTS["objectives_preserved"]
            + wp_score * _WEIGHTS["work_packets_preserved"]
            + mem_score * _WEIGHTS["memory_continuous"]
            + exec_score * _WEIGHTS["execution_continuous"]
        )
        return round(composite, 4)

    def score_all(self) -> dict[str, Any]:
        """Aggregate scores across all recorded switches."""
        if not self._events:
            return {
                "total_switches": 0,
                "avg_composite": 0.0,
                "pass": False,
                "dimensions": {},
            }

        scores = [self.score_switch(e) for e in self._events]
        n = len(self._events)

        avg_context = sum(e.context_restored_pct for e in self._events) / n
        avg_resume = sum(e.resume_time_seconds for e in self._events) / n
        all_objectives = all(e.objectives_preserved for e in self._events)
        all_work_packets = all(e.work_packets_preserved for e in self._events)
        no_complete_loss = all(e.context_restored_pct > 0 for e in self._events)

        passes = (
            avg_context > 80.0
            and avg_resume < 30.0
            and all_objectives
            and all_work_packets
            and no_complete_loss
        )

        return {
            "total_switches": n,
            "avg_composite": round(sum(scores) / n, 4),
            "min_composite": round(min(scores), 4),
            "max_composite": round(max(scores), 4),
            "pass": passes,
            "dimensions": {
                "avg_context_restored_pct": round(avg_context, 2),
                "avg_resume_time_seconds": round(avg_resume, 2),
                "all_objectives_preserved": all_objectives,
                "all_work_packets_preserved": all_work_packets,
                "no_complete_context_loss": no_complete_loss,
                "memory_continuous_rate": round(
                    sum(1 for e in self._events if e.memory_continuous) / n, 4
                ),
                "execution_continuous_rate": round(
                    sum(1 for e in self._events if e.execution_continuous) / n, 4
                ),
                "conversation_continuous_rate": round(
                    sum(1 for e in self._events if e.conversation_continuous) / n, 4
                ),
            },
            "per_switch": [
                {
                    "event_id": e.event_id,
                    "from": e.from_surface,
                    "to": e.to_surface,
                    "score": round(self.score_switch(e), 4),
                }
                for e in self._events
            ],
        }

    def summary(self) -> dict[str, Any]:
        """Quick summary for reporting."""
        if not self._events:
            return {"total_switches": 0, "pass": False}

        all_scores = self.score_all()
        unique_surfaces = set()
        for e in self._events:
            unique_surfaces.add(e.from_surface)
            unique_surfaces.add(e.to_surface)

        return {
            "total_switches": all_scores["total_switches"],
            "avg_composite": all_scores["avg_composite"],
            "pass": all_scores["pass"],
            "surfaces_used": sorted(unique_surfaces),
            "top_info_lost": self._top_info_lost(),
        }

    def _top_info_lost(self, limit: int = 5) -> list[str]:
        """Most frequently reported lost information."""
        counts: dict[str, int] = {}
        for e in self._events:
            for item in e.info_lost:
                counts[item] = counts.get(item, 0) + 1
        return sorted(counts, key=lambda k: counts[k], reverse=True)[:limit]
