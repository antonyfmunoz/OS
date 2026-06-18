"""Decision Registry — first-class strategic decision records for UMH.

StrategicDecision is NOT a chat memory, note, or approval. It is only
created when a decision has durable strategic consequence: goal impact,
project impact, architecture impact, governance impact, or work-packet
impact.

The existing DecisionRecord in strategic_gap_engine.py is a narrow
learning-loop type (recommendation approval/rejection). StrategicDecision
is the institutional memory entity — different concern, not type divergence.

Campaign 9.0 — Decision Intelligence & Strategic Memory.
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


class DecisionStatus(str, Enum):
    PROPOSED = "proposed"
    ACTIVE = "active"
    SUPERSEDED = "superseded"
    INVALIDATED = "invalidated"
    ARCHIVED = "archived"


@dataclass
class StrategicDecision:
    decision_id: str = field(default_factory=lambda: f"sd-{uuid4().hex[:8]}")
    title: str = ""
    summary: str = ""
    rationale: str = ""
    alternatives_considered: list[dict[str, str]] = field(default_factory=list)
    assumptions: list[str] = field(default_factory=list)
    status: str = DecisionStatus.PROPOSED.value
    goal_refs: list[str] = field(default_factory=list)
    project_refs: list[str] = field(default_factory=list)
    work_packet_refs: list[str] = field(default_factory=list)
    approval_refs: list[str] = field(default_factory=list)
    superseded_by: str = ""
    supersedes: str = ""
    tags: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)
    created_at: float = field(default_factory=time.time)
    updated_at: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "decision_id": self.decision_id,
            "title": self.title,
            "summary": self.summary,
            "rationale": self.rationale,
            "alternatives_considered": list(self.alternatives_considered),
            "assumptions": list(self.assumptions),
            "status": self.status,
            "goal_refs": list(self.goal_refs),
            "project_refs": list(self.project_refs),
            "work_packet_refs": list(self.work_packet_refs),
            "approval_refs": list(self.approval_refs),
            "superseded_by": self.superseded_by,
            "supersedes": self.supersedes,
            "tags": list(self.tags),
            "metadata": dict(self.metadata),
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> StrategicDecision:
        return cls(
            decision_id=d.get("decision_id", f"sd-{uuid4().hex[:8]}"),
            title=d.get("title", ""),
            summary=d.get("summary", ""),
            rationale=d.get("rationale", ""),
            alternatives_considered=d.get("alternatives_considered", []),
            assumptions=d.get("assumptions", []),
            status=d.get("status", DecisionStatus.PROPOSED.value),
            goal_refs=d.get("goal_refs", []),
            project_refs=d.get("project_refs", []),
            work_packet_refs=d.get("work_packet_refs", []),
            approval_refs=d.get("approval_refs", []),
            superseded_by=d.get("superseded_by", ""),
            supersedes=d.get("supersedes", ""),
            tags=d.get("tags", []),
            metadata=d.get("metadata", {}),
            created_at=d.get("created_at", 0.0),
            updated_at=d.get("updated_at", 0.0),
        )


# ── Registry ──────────────────────────────────────────────────────────────


class DecisionRegistry:
    """Governed registry for strategic decisions with durable consequence."""

    def __init__(
        self,
        reality_graph: Any | None = None,
        data_dir: str = "",
    ) -> None:
        self._reality_graph = reality_graph
        self._data_dir = data_dir or os.path.join(_ROOT, "data", "umh", "decisions")
        self._decisions: dict[str, StrategicDecision] = {}
        self._load()

    # ── Core CRUD ─────────────────────────────────────────────────────

    def register(self, decision: StrategicDecision) -> StrategicDecision:
        decision.updated_at = time.time()
        self._decisions[decision.decision_id] = decision
        self._persist(decision)
        self._register_in_reality_graph(decision)
        return decision

    def get(self, decision_id: str) -> StrategicDecision | None:
        return self._decisions.get(decision_id)

    def list_decisions(
        self, status: str | None = None
    ) -> list[StrategicDecision]:
        decisions = list(self._decisions.values())
        if status:
            decisions = [d for d in decisions if d.status == status]
        return sorted(decisions, key=lambda d: d.created_at, reverse=True)

    def update_status(
        self, decision_id: str, status: DecisionStatus
    ) -> bool:
        dec = self._decisions.get(decision_id)
        if not dec:
            return False
        dec.status = status.value
        dec.updated_at = time.time()
        self._persist(dec)
        return True

    def supersede(self, old_id: str, new_id: str) -> bool:
        old = self._decisions.get(old_id)
        new = self._decisions.get(new_id)
        if not old or not new:
            return False
        old.status = DecisionStatus.SUPERSEDED.value
        old.superseded_by = new_id
        old.updated_at = time.time()
        new.supersedes = old_id
        new.updated_at = time.time()
        self._persist(old)
        self._persist(new)
        self._register_supersession(old_id, new_id)
        return True

    # ── Queries ───────────────────────────────────────────────────────

    def decisions_for_goal(self, goal_id: str) -> list[StrategicDecision]:
        return [
            d for d in self._decisions.values()
            if goal_id in d.goal_refs
        ]

    def decisions_for_project(
        self, project_id: str
    ) -> list[StrategicDecision]:
        return [
            d for d in self._decisions.values()
            if project_id in d.project_refs
        ]

    def decisions_for_work_packet(
        self, wp_id: str
    ) -> list[StrategicDecision]:
        return [
            d for d in self._decisions.values()
            if wp_id in d.work_packet_refs
        ]

    def active_decisions(self) -> list[StrategicDecision]:
        return self.list_decisions(status=DecisionStatus.ACTIVE.value)

    # ── Aggregation ───────────────────────────────────────────────────

    def summary(self) -> dict[str, Any]:
        by_status: dict[str, int] = {}
        for d in self._decisions.values():
            by_status[d.status] = by_status.get(d.status, 0) + 1
        recent = sorted(
            self._decisions.values(),
            key=lambda d: d.created_at,
            reverse=True,
        )[:5]
        return {
            "total": len(self._decisions),
            "by_status": by_status,
            "recent": [d.to_dict() for d in recent],
            "generated_at": time.time(),
        }

    # ── Reality Graph Integration ─────────────────────────────────────

    def _register_in_reality_graph(self, decision: StrategicDecision) -> None:
        if not self._reality_graph:
            return
        try:
            rg = self._reality_graph
            from substrate.organism.reality_graph import (
                RealityEntity,
                RealityEntityStatus,
                RealityEntityType,
                RealityRelation,
                RealityRelationType,
            )

            entity = RealityEntity(
                entity_id=decision.decision_id,
                entity_type=RealityEntityType.DECISION,
                name=decision.title,
                status=RealityEntityStatus.ACTIVE,
                properties={"summary": decision.summary, "status": decision.status},
                source_system="decision_registry",
                source_id=decision.decision_id,
                last_observed=time.time(),
            )
            rg.add_entity(entity)

            for goal_id in decision.goal_refs:
                rg.add_relation(RealityRelation(
                    source_id=decision.decision_id,
                    target_id=goal_id,
                    relation_type=RealityRelationType.SUPPORTS,
                    properties={},
                ))

            for wp_id in decision.work_packet_refs:
                rg.add_relation(RealityRelation(
                    source_id=decision.decision_id,
                    target_id=wp_id,
                    relation_type=RealityRelationType.CREATED,
                    properties={},
                ))

            for ap_id in decision.approval_refs:
                rg.add_relation(RealityRelation(
                    source_id=decision.decision_id,
                    target_id=ap_id,
                    relation_type=RealityRelationType.APPROVED_BY,
                    properties={},
                ))
        except Exception:
            logger.debug("Failed to register decision in reality graph", exc_info=True)

    def _register_supersession(self, old_id: str, new_id: str) -> None:
        if not self._reality_graph:
            return
        try:
            from substrate.organism.reality_graph import (
                RealityRelation,
                RealityRelationType,
            )
            self._reality_graph.add_relation(RealityRelation(
                source_id=new_id,
                target_id=old_id,
                relation_type=RealityRelationType.SUPERSEDES,
                properties={},
            ))
        except Exception:
            logger.debug("Failed to register supersession relation", exc_info=True)

    # ── Persistence ───────────────────────────────────────────────────

    def _persist(self, decision: StrategicDecision) -> None:
        try:
            os.makedirs(self._data_dir, exist_ok=True)
            path = os.path.join(self._data_dir, "decisions.jsonl")
            with open(path, "a", encoding="utf-8") as f:
                f.write(json.dumps(decision.to_dict()) + "\n")
        except Exception:
            logger.debug("Failed to persist decision", exc_info=True)

    def _load(self) -> None:
        path = os.path.join(self._data_dir, "decisions.jsonl")
        if not os.path.exists(path):
            return
        try:
            with open(path, encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    d = json.loads(line)
                    dec = StrategicDecision.from_dict(d)
                    self._decisions[dec.decision_id] = dec
        except Exception:
            logger.debug("Failed to load decisions", exc_info=True)
