"""Assumption Tracking Runtime — governed assumption records for UMH.

Every strategic decision contains assumptions. This runtime tracks them,
records evidence for/against, and surfaces invalidated assumptions so the
Decision Validity Engine can evaluate decision health.

Campaign 9.2 — Decision Intelligence & Strategic Memory.
UMH substrate layer. Instance-agnostic.
"""

from __future__ import annotations

import json
import logging
import os
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any
from uuid import uuid4

logger = logging.getLogger(__name__)

_ROOT = os.environ.get("UMH_ROOT") or "/opt/OS"


# ── Types ─────────────────────────────────────────────────────────────────


class AssumptionStatus(str, Enum):
    ACTIVE = "active"
    VALIDATED = "validated"
    INVALIDATED = "invalidated"
    UNKNOWN = "unknown"


@dataclass
class AssumptionRecord:
    assumption_id: str = field(default_factory=lambda: f"asm-{uuid4().hex[:8]}")
    statement: str = ""
    decision_refs: list[str] = field(default_factory=list)
    goal_refs: list[str] = field(default_factory=list)
    status: str = AssumptionStatus.ACTIVE.value
    evidence_for: list[str] = field(default_factory=list)
    evidence_against: list[str] = field(default_factory=list)
    source: str = ""
    tags: list[str] = field(default_factory=list)
    created_at: float = field(default_factory=time.time)
    updated_at: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "assumption_id": self.assumption_id,
            "statement": self.statement,
            "decision_refs": list(self.decision_refs),
            "goal_refs": list(self.goal_refs),
            "status": self.status,
            "evidence_for": list(self.evidence_for),
            "evidence_against": list(self.evidence_against),
            "source": self.source,
            "tags": list(self.tags),
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> AssumptionRecord:
        return cls(
            assumption_id=d.get("assumption_id", f"asm-{uuid4().hex[:8]}"),
            statement=d.get("statement", ""),
            decision_refs=d.get("decision_refs", []),
            goal_refs=d.get("goal_refs", []),
            status=d.get("status", AssumptionStatus.ACTIVE.value),
            evidence_for=d.get("evidence_for", []),
            evidence_against=d.get("evidence_against", []),
            source=d.get("source", ""),
            tags=d.get("tags", []),
            created_at=d.get("created_at", 0.0),
            updated_at=d.get("updated_at", 0.0),
        )


# ── Runtime ───────────────────────────────────────────────────────────────


class AssumptionTrackingRuntime:
    """Governed registry for strategic assumptions with evidence tracking."""

    def __init__(self, data_dir: str = "") -> None:
        self._data_dir = data_dir or os.path.join(_ROOT, "data", "umh", "decisions")
        self._assumptions: dict[str, AssumptionRecord] = {}
        self._load()

    # ── Core CRUD ─────────────────────────────────────────────────────

    def add(self, assumption: AssumptionRecord) -> AssumptionRecord:
        assumption.updated_at = time.time()
        self._assumptions[assumption.assumption_id] = assumption
        self._persist(assumption)
        return assumption

    def get(self, assumption_id: str) -> AssumptionRecord | None:
        return self._assumptions.get(assumption_id)

    def list_assumptions(
        self, status: str | None = None
    ) -> list[AssumptionRecord]:
        assumptions = list(self._assumptions.values())
        if status:
            assumptions = [a for a in assumptions if a.status == status]
        return sorted(assumptions, key=lambda a: a.created_at, reverse=True)

    def update_status(
        self,
        assumption_id: str,
        status: AssumptionStatus,
        evidence: str = "",
    ) -> bool:
        asm = self._assumptions.get(assumption_id)
        if not asm:
            return False
        asm.status = status.value
        asm.updated_at = time.time()
        if evidence:
            if status == AssumptionStatus.INVALIDATED:
                asm.evidence_against.append(evidence)
            else:
                asm.evidence_for.append(evidence)
        self._persist(asm)
        return True

    # ── Queries ───────────────────────────────────────────────────────

    def assumptions_for_decision(
        self, decision_id: str
    ) -> list[AssumptionRecord]:
        return [
            a for a in self._assumptions.values()
            if decision_id in a.decision_refs
        ]

    def invalidated(self) -> list[AssumptionRecord]:
        return self.list_assumptions(status=AssumptionStatus.INVALIDATED.value)

    def active(self) -> list[AssumptionRecord]:
        return self.list_assumptions(status=AssumptionStatus.ACTIVE.value)

    # ── Aggregation ───────────────────────────────────────────────────

    def summary(self) -> dict[str, Any]:
        by_status: dict[str, int] = {}
        for a in self._assumptions.values():
            by_status[a.status] = by_status.get(a.status, 0) + 1
        return {
            "total": len(self._assumptions),
            "by_status": by_status,
            "invalidated_count": by_status.get(
                AssumptionStatus.INVALIDATED.value, 0
            ),
            "generated_at": time.time(),
        }

    # ── Persistence ───────────────────────────────────────────────────

    def _persist(self, assumption: AssumptionRecord) -> None:
        try:
            os.makedirs(self._data_dir, exist_ok=True)
            path = os.path.join(self._data_dir, "assumptions.jsonl")
            with open(path, "a", encoding="utf-8") as f:
                f.write(json.dumps(assumption.to_dict()) + "\n")
        except Exception:
            logger.debug("Failed to persist assumption", exc_info=True)

    def _load(self) -> None:
        path = os.path.join(self._data_dir, "assumptions.jsonl")
        if not os.path.exists(path):
            return
        try:
            with open(path, encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    d = json.loads(line)
                    rec = AssumptionRecord.from_dict(d)
                    self._assumptions[rec.assumption_id] = rec
        except Exception:
            logger.debug("Failed to load assumptions", exc_info=True)
