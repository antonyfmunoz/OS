"""Engineering Intent Contract — types for autonomous engineering planning.

Defines the contract between operator engineering intent and the planning
layer. All types are planning artifacts — no execution, no mutation.

Phase 22. UMH substrate subsystem. Instance-agnostic.
"""

from __future__ import annotations

import re
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any
from uuid import uuid4


class EngineeringIntentType(str, Enum):
    FEATURE = "feature"
    BUGFIX = "bugfix"
    REFACTOR = "refactor"
    INFRASTRUCTURE = "infrastructure"
    RESEARCH = "research"


_INTENT_PATTERNS: list[tuple[re.Pattern[str], EngineeringIntentType]] = [
    (
        re.compile(
            r"^(build|create|implement|add|develop|introduce|design|make)\b",
            re.IGNORECASE,
        ),
        EngineeringIntentType.FEATURE,
    ),
    (
        re.compile(
            r"^(fix|resolve|patch|debug|repair|correct|handle)\b",
            re.IGNORECASE,
        ),
        EngineeringIntentType.BUGFIX,
    ),
    (
        re.compile(
            r"^(refactor|clean|simplify|extract|reorganize|restructure|consolidate|rename)\b",
            re.IGNORECASE,
        ),
        EngineeringIntentType.REFACTOR,
    ),
    (
        re.compile(
            r"^(deploy|configure|setup|set up|migrate|install|upgrade|provision)\b",
            re.IGNORECASE,
        ),
        EngineeringIntentType.INFRASTRUCTURE,
    ),
    (
        re.compile(
            r"^(research|investigate|analyze|audit|evaluate|assess|explore|study)\b",
            re.IGNORECASE,
        ),
        EngineeringIntentType.RESEARCH,
    ),
]

_IMPERATIVE_PREFIX = re.compile(
    r"^(build|create|implement|add|develop|introduce|design|make"
    r"|fix|resolve|patch|debug|repair|correct|handle"
    r"|refactor|clean|simplify|extract|reorganize|restructure|consolidate|rename"
    r"|deploy|configure|setup|set up|migrate|install|upgrade|provision"
    r"|research|investigate|analyze|audit|evaluate|assess|explore|study)\b\s*",
    re.IGNORECASE,
)


def classify_engineering_intent(raw_input: str) -> EngineeringIntentType:
    """Deterministic regex-based intent classification."""
    text = raw_input.strip()
    for pattern, intent_type in _INTENT_PATTERNS:
        if pattern.search(text):
            return intent_type
    return EngineeringIntentType.FEATURE


def extract_goal(raw_input: str) -> str:
    """Strip imperative verb prefix to extract the goal."""
    text = raw_input.strip()
    result = _IMPERATIVE_PREFIX.sub("", text, count=1).strip()
    return result if result else text


@dataclass
class EngineeringIntent:
    """High-level engineering intent — what the operator wants done."""

    intent_id: str = field(default_factory=lambda: f"ei-{uuid4().hex[:12]}")
    raw_input: str = ""
    intent_type: EngineeringIntentType = EngineeringIntentType.FEATURE
    goal: str = ""
    scope: list[str] = field(default_factory=list)
    constraints: list[str] = field(default_factory=list)
    success_criteria: list[str] = field(default_factory=list)
    affected_repos: list[str] = field(default_factory=list)
    affected_domains: list[str] = field(default_factory=list)
    estimated_risk: str = "low"
    created_at: float = field(default_factory=time.time)

    def to_dict(self) -> dict[str, Any]:
        return {
            "intent_id": self.intent_id,
            "raw_input": self.raw_input,
            "intent_type": self.intent_type.value,
            "goal": self.goal,
            "scope": self.scope,
            "constraints": self.constraints,
            "success_criteria": self.success_criteria,
            "affected_repos": self.affected_repos,
            "affected_domains": self.affected_domains,
            "estimated_risk": self.estimated_risk,
            "created_at": self.created_at,
        }


@dataclass
class EngineeringTask:
    """Individual task within an engineering plan."""

    task_id: str = field(default_factory=lambda: f"et-{uuid4().hex[:12]}")
    title: str = ""
    description: str = ""
    task_type: str = ""
    dependencies: list[str] = field(default_factory=list)
    affected_files: list[str] = field(default_factory=list)
    risk_class: str = "low"
    validation_requirements: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "task_id": self.task_id,
            "title": self.title,
            "description": self.description,
            "task_type": self.task_type,
            "dependencies": self.dependencies,
            "affected_files": self.affected_files,
            "risk_class": self.risk_class,
            "validation_requirements": self.validation_requirements,
        }


@dataclass
class EngineeringPlan:
    """Complete engineering plan — reviewable before packet generation."""

    plan_id: str = field(default_factory=lambda: f"ep-{uuid4().hex[:12]}")
    intent: EngineeringIntent = field(default_factory=EngineeringIntent)
    tasks: list[EngineeringTask] = field(default_factory=list)
    dependency_graph: dict[str, list[str]] = field(default_factory=dict)
    estimated_total_risk: str = "low"
    roadmap_context: dict[str, Any] = field(default_factory=dict)
    workspace_health: dict[str, Any] = field(default_factory=dict)
    engineering_risks: list[dict[str, Any]] = field(default_factory=list)
    created_at: float = field(default_factory=time.time)
    status: str = "draft"

    def to_dict(self) -> dict[str, Any]:
        return {
            "plan_id": self.plan_id,
            "intent": self.intent.to_dict(),
            "tasks": [t.to_dict() for t in self.tasks],
            "dependency_graph": self.dependency_graph,
            "estimated_total_risk": self.estimated_total_risk,
            "roadmap_context": self.roadmap_context,
            "workspace_health": self.workspace_health,
            "engineering_risks": self.engineering_risks,
            "created_at": self.created_at,
            "status": self.status,
        }


@dataclass
class EngineeringPlanReceipt:
    """Receipt for plan approval and packet generation."""

    receipt_id: str = field(default_factory=lambda: f"epr-{uuid4().hex[:12]}")
    plan_id: str = ""
    work_packet_ids: list[str] = field(default_factory=list)
    governance_decisions: list[str] = field(default_factory=list)
    status: str = "planned"
    created_at: float = field(default_factory=time.time)

    def to_dict(self) -> dict[str, Any]:
        return {
            "receipt_id": self.receipt_id,
            "plan_id": self.plan_id,
            "work_packet_ids": self.work_packet_ids,
            "governance_decisions": self.governance_decisions,
            "status": self.status,
            "created_at": self.created_at,
        }
