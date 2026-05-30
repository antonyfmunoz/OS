"""Workcell — planning/delegation workcell model for Work Packets.

A Workcell is a bounded execution unit spawned from a WorkPacket. Workcells
may recursively subdivide. Every workcell with parallel advisor branches
must reconverge before completing.

Distinct from workcell_protocol.py (low-level inbox/outbox execution cells).

Phase 11.1. UMH substrate subsystem. Instance-agnostic.
"""

from __future__ import annotations

import json
import logging
import os
import tempfile
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any
from uuid import uuid4

logger = logging.getLogger(__name__)

_REPO_ROOT = os.environ.get("UMH_ROOT", "/opt/OS")

DEFAULT_MAX_DEPTH = 5


class PlanningWorkcellStatus(str, Enum):
    PENDING = "pending"
    ACTIVE = "active"
    BRANCHED = "branched"
    RECONVERGING = "reconverging"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class AdvisorBranchStatus(str, Enum):
    PENDING = "pending"
    ACTIVE = "active"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class AdvisorBranch:
    advisor_id: str = field(default_factory=lambda: f"adv-{uuid4().hex[:8]}")
    perspective: str = ""
    brief: str = ""
    context_slice: str = ""
    output_contract: str = ""
    confidence: float = 0.0
    result: str = ""
    status: AdvisorBranchStatus = AdvisorBranchStatus.PENDING

    def to_dict(self) -> dict[str, Any]:
        return {
            "advisor_id": self.advisor_id,
            "perspective": self.perspective,
            "brief": self.brief,
            "context_slice": self.context_slice,
            "output_contract": self.output_contract,
            "confidence": round(self.confidence, 4),
            "result": self.result,
            "status": self.status.value,
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> AdvisorBranch:
        status_raw = d.get("status", "pending")
        try:
            status = AdvisorBranchStatus(status_raw)
        except ValueError:
            status = AdvisorBranchStatus.PENDING
        return cls(
            advisor_id=d.get("advisor_id", f"adv-{uuid4().hex[:8]}"),
            perspective=d.get("perspective", ""),
            brief=d.get("brief", ""),
            context_slice=d.get("context_slice", ""),
            output_contract=d.get("output_contract", ""),
            confidence=float(d.get("confidence", 0.0)),
            result=d.get("result", ""),
            status=status,
        )


@dataclass
class ReconvergenceResult:
    source_workcell_id: str = ""
    branch_count: int = 0
    contradictions_detected: list[str] = field(default_factory=list)
    conflicts_resolved: list[str] = field(default_factory=list)
    confidence: float = 0.0
    final_synthesis: str = ""
    unresolved_questions: list[str] = field(default_factory=list)
    recommended_next_actions: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "source_workcell_id": self.source_workcell_id,
            "branch_count": self.branch_count,
            "contradictions_detected": self.contradictions_detected,
            "conflicts_resolved": self.conflicts_resolved,
            "confidence": round(self.confidence, 4),
            "final_synthesis": self.final_synthesis,
            "unresolved_questions": self.unresolved_questions,
            "recommended_next_actions": self.recommended_next_actions,
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> ReconvergenceResult:
        return cls(
            source_workcell_id=d.get("source_workcell_id", ""),
            branch_count=int(d.get("branch_count", 0)),
            contradictions_detected=d.get("contradictions_detected", []),
            conflicts_resolved=d.get("conflicts_resolved", []),
            confidence=float(d.get("confidence", 0.0)),
            final_synthesis=d.get("final_synthesis", ""),
            unresolved_questions=d.get("unresolved_questions", []),
            recommended_next_actions=d.get("recommended_next_actions", []),
        )


@dataclass
class Workcell:
    workcell_id: str = field(default_factory=lambda: f"wc-{uuid4().hex[:10]}")
    parent_packet_id: str = ""
    parent_workcell_id: str = ""
    title: str = ""
    objective: str = ""
    scope: str = ""
    context_packet: str = ""
    constraints: list[str] = field(default_factory=list)
    assigned_role_contracts: list[str] = field(default_factory=list)
    advisor_branches: list[AdvisorBranch] = field(default_factory=list)
    child_workcells: list[str] = field(default_factory=list)
    required_knowledge_models: list[str] = field(default_factory=list)
    required_tools: list[str] = field(default_factory=list)
    output_contract: str = ""
    reconvergence_target: str = ""
    reconvergence_result: ReconvergenceResult | None = None
    validation_plan: str = ""
    status: PlanningWorkcellStatus = PlanningWorkcellStatus.PENDING
    depth: int = 0
    budget: float = 0.0
    time_limit: float = 0.0
    context_limit: int = 0
    risk_limit: str = "low"
    created_at: float = field(default_factory=time.time)
    completed_at: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "workcell_id": self.workcell_id,
            "parent_packet_id": self.parent_packet_id,
            "parent_workcell_id": self.parent_workcell_id,
            "title": self.title,
            "objective": self.objective,
            "scope": self.scope,
            "context_packet": self.context_packet,
            "constraints": self.constraints,
            "assigned_role_contracts": self.assigned_role_contracts,
            "advisor_branches": [b.to_dict() for b in self.advisor_branches],
            "child_workcells": self.child_workcells,
            "required_knowledge_models": self.required_knowledge_models,
            "required_tools": self.required_tools,
            "output_contract": self.output_contract,
            "reconvergence_target": self.reconvergence_target,
            "reconvergence_result": self.reconvergence_result.to_dict() if self.reconvergence_result else None,
            "validation_plan": self.validation_plan,
            "status": self.status.value,
            "depth": self.depth,
            "budget": self.budget,
            "time_limit": self.time_limit,
            "context_limit": self.context_limit,
            "risk_limit": self.risk_limit,
            "created_at": self.created_at,
            "completed_at": self.completed_at,
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> Workcell:
        status_raw = d.get("status", "pending")
        try:
            status = PlanningWorkcellStatus(status_raw)
        except ValueError:
            status = PlanningWorkcellStatus.PENDING

        branches = [AdvisorBranch.from_dict(b) for b in d.get("advisor_branches", [])]
        recon_raw = d.get("reconvergence_result")
        recon = ReconvergenceResult.from_dict(recon_raw) if recon_raw else None

        return cls(
            workcell_id=d.get("workcell_id", f"wc-{uuid4().hex[:10]}"),
            parent_packet_id=d.get("parent_packet_id", ""),
            parent_workcell_id=d.get("parent_workcell_id", ""),
            title=d.get("title", ""),
            objective=d.get("objective", ""),
            scope=d.get("scope", ""),
            context_packet=d.get("context_packet", ""),
            constraints=d.get("constraints", []),
            assigned_role_contracts=d.get("assigned_role_contracts", []),
            advisor_branches=branches,
            child_workcells=d.get("child_workcells", []),
            required_knowledge_models=d.get("required_knowledge_models", []),
            required_tools=d.get("required_tools", []),
            output_contract=d.get("output_contract", ""),
            reconvergence_target=d.get("reconvergence_target", ""),
            reconvergence_result=recon,
            validation_plan=d.get("validation_plan", ""),
            status=status,
            depth=int(d.get("depth", 0)),
            budget=float(d.get("budget", 0.0)),
            time_limit=float(d.get("time_limit", 0.0)),
            context_limit=int(d.get("context_limit", 0)),
            risk_limit=d.get("risk_limit", "low"),
            created_at=float(d.get("created_at", time.time())),
            completed_at=float(d.get("completed_at", 0.0)),
        )

    def has_branches(self) -> bool:
        return len(self.advisor_branches) > 0

    def requires_reconvergence(self) -> bool:
        return self.has_branches() and self.reconvergence_result is None

    def can_subdivide(self, max_depth: int = DEFAULT_MAX_DEPTH) -> bool:
        return self.depth < max_depth

    def all_branches_distinct(self) -> bool:
        briefs = [b.brief for b in self.advisor_branches if b.brief]
        return len(briefs) == len(set(briefs))


def persist_workcells(
    workcells: list[Workcell],
    store_path: str | None = None,
) -> None:
    path = store_path or os.path.join(
        _REPO_ROOT, "data", "umh", "universal_work", "workcells.jsonl",
    )
    dir_path = os.path.dirname(path)
    os.makedirs(dir_path, exist_ok=True)
    fd, tmp_path = tempfile.mkstemp(dir=dir_path, suffix=".tmp")
    try:
        with os.fdopen(fd, "w") as f:
            for wc in workcells:
                f.write(json.dumps(wc.to_dict()) + "\n")
        os.replace(tmp_path, path)
    except BaseException:
        if os.path.exists(tmp_path):
            os.unlink(tmp_path)
        raise


def load_workcells(store_path: str | None = None) -> list[Workcell]:
    path = store_path or os.path.join(
        _REPO_ROOT, "data", "umh", "universal_work", "workcells.jsonl",
    )
    if not os.path.exists(path):
        return []
    workcells: list[Workcell] = []
    with open(path, "r") as f:
        for line_num, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                continue
            try:
                d = json.loads(line)
                workcells.append(Workcell.from_dict(d))
            except (json.JSONDecodeError, KeyError, TypeError) as exc:
                raise ValueError(
                    f"Corrupt workcell at line {line_num}: {exc}"
                ) from exc
    return workcells
