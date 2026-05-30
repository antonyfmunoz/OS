"""Change Event — state change model for propagation planning.

Captures what changed, computes affected nodes, and produces
dependency-aware propagation plans with waves, parallel groups,
reconvergence points, and governance gates.

Phase 12.0. UMH substrate subsystem. Instance-agnostic.
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

_REPO_ROOT = os.environ.get("UMH_ROOT", "/opt/OS")


class ChangeType(str, Enum):
    WORK_PACKET_CREATED = "work_packet_created"
    WORK_PACKET_UPDATED = "work_packet_updated"
    WORKCELL_UPDATED = "workcell_updated"
    ROLE_CONTRACT_UPDATED = "role_contract_updated"
    KNOWLEDGE_MODEL_UPDATED = "knowledge_model_updated"
    TEMPLATE_UPDATED = "template_updated"
    MEMORY_PROMOTED = "memory_promoted"
    PRODUCTION_TRUTH_COMMITTED = "production_truth_committed"
    CANDIDATE_RESOLVED = "candidate_resolved"
    ROADMAP_PHASE_UPDATED = "roadmap_phase_updated"
    AGENT_RELIABILITY_UPDATED = "agent_reliability_updated"
    API_ROUTE_ADDED = "api_route_added"
    COCKPIT_PANEL_ADDED = "cockpit_panel_added"
    COMPANY_UPDATED = "company_updated"
    PRODUCT_UPDATED = "product_updated"
    OFFER_UPDATED = "offer_updated"
    HUMAN_ACTION_COMPLETED = "human_action_completed"


class PropagationActionStatus(str, Enum):
    PENDING = "pending"
    DRY_RUN = "dry_run"
    EXECUTING = "executing"
    COMPLETED = "completed"
    FAILED = "failed"
    BLOCKED = "blocked"
    APPROVAL_REQUIRED = "approval_required"
    HUMAN_REQUIRED = "human_required"
    SKIPPED = "skipped"


@dataclass
class ChangeEvent:
    change_id: str = field(default_factory=lambda: f"ce-{uuid4().hex[:12]}")
    change_type: ChangeType = ChangeType.WORK_PACKET_UPDATED
    source_node_id: str = ""
    source_type: str = ""
    source_id: str = ""
    title: str = ""
    description: str = ""
    before_state: dict[str, Any] = field(default_factory=dict)
    after_state: dict[str, Any] = field(default_factory=dict)
    changed_fields: list[str] = field(default_factory=list)
    changed_files: list[str] = field(default_factory=list)
    changed_entities: list[str] = field(default_factory=list)
    changed_relationships: list[str] = field(default_factory=list)
    risk_class: str = "low"
    initiated_by: str = "operator"
    timestamp: float = field(default_factory=time.time)
    evidence: list[dict[str, Any]] = field(default_factory=list)
    idempotency_key: str = field(default_factory=lambda: f"idem-{uuid4().hex[:12]}")

    def to_dict(self) -> dict[str, Any]:
        return {
            "change_id": self.change_id,
            "change_type": self.change_type.value if isinstance(self.change_type, Enum) else self.change_type,
            "source_node_id": self.source_node_id,
            "source_type": self.source_type,
            "source_id": self.source_id,
            "title": self.title,
            "description": self.description,
            "before_state": self.before_state,
            "after_state": self.after_state,
            "changed_fields": self.changed_fields,
            "changed_files": self.changed_files,
            "changed_entities": self.changed_entities,
            "changed_relationships": self.changed_relationships,
            "risk_class": self.risk_class,
            "initiated_by": self.initiated_by,
            "timestamp": self.timestamp,
            "evidence": self.evidence,
            "idempotency_key": self.idempotency_key,
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> ChangeEvent:
        ct = d.get("change_type", "work_packet_updated")
        try:
            change_type = ChangeType(ct)
        except ValueError:
            change_type = ChangeType.WORK_PACKET_UPDATED
        return cls(
            change_id=d.get("change_id", f"ce-{uuid4().hex[:12]}"),
            change_type=change_type,
            source_node_id=d.get("source_node_id", ""),
            source_type=d.get("source_type", ""),
            source_id=d.get("source_id", ""),
            title=d.get("title", ""),
            description=d.get("description", ""),
            before_state=d.get("before_state", {}),
            after_state=d.get("after_state", {}),
            changed_fields=d.get("changed_fields", []),
            changed_files=d.get("changed_files", []),
            changed_entities=d.get("changed_entities", []),
            changed_relationships=d.get("changed_relationships", []),
            risk_class=d.get("risk_class", "low"),
            initiated_by=d.get("initiated_by", "operator"),
            timestamp=d.get("timestamp", time.time()),
            evidence=d.get("evidence", []),
            idempotency_key=d.get("idempotency_key", f"idem-{uuid4().hex[:12]}"),
        )


@dataclass
class PropagationAction:
    action_id: str = field(default_factory=lambda: f"pa-{uuid4().hex[:12]}")
    node_id: str = ""
    action_type: str = "notify_only"
    reason: str = ""
    input_evidence: list[dict[str, Any]] = field(default_factory=list)
    output_expected: str = ""
    approval_required: bool = False
    validation_required: bool = False
    human_required: bool = False
    risk_class: str = "low"
    idempotency_key: str = field(default_factory=lambda: f"idem-{uuid4().hex[:12]}")
    status: PropagationActionStatus = PropagationActionStatus.PENDING

    def to_dict(self) -> dict[str, Any]:
        return {
            "action_id": self.action_id,
            "node_id": self.node_id,
            "action_type": self.action_type,
            "reason": self.reason,
            "input_evidence": self.input_evidence,
            "output_expected": self.output_expected,
            "approval_required": self.approval_required,
            "validation_required": self.validation_required,
            "human_required": self.human_required,
            "risk_class": self.risk_class,
            "idempotency_key": self.idempotency_key,
            "status": self.status.value if isinstance(self.status, Enum) else self.status,
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> PropagationAction:
        st = d.get("status", "pending")
        try:
            status = PropagationActionStatus(st)
        except ValueError:
            status = PropagationActionStatus.PENDING
        return cls(
            action_id=d.get("action_id", f"pa-{uuid4().hex[:12]}"),
            node_id=d.get("node_id", ""),
            action_type=d.get("action_type", "notify_only"),
            reason=d.get("reason", ""),
            input_evidence=d.get("input_evidence", []),
            output_expected=d.get("output_expected", ""),
            approval_required=d.get("approval_required", False),
            validation_required=d.get("validation_required", False),
            human_required=d.get("human_required", False),
            risk_class=d.get("risk_class", "low"),
            idempotency_key=d.get("idempotency_key", f"idem-{uuid4().hex[:12]}"),
            status=status,
        )


@dataclass
class PropagationWave:
    wave_id: str = field(default_factory=lambda: f"pw-{uuid4().hex[:12]}")
    wave_number: int = 0
    nodes: list[str] = field(default_factory=list)
    actions: list[PropagationAction] = field(default_factory=list)
    can_run_parallel: bool = True
    dependencies: list[str] = field(default_factory=list)
    reconvergence_required: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "wave_id": self.wave_id,
            "wave_number": self.wave_number,
            "nodes": self.nodes,
            "actions": [a.to_dict() for a in self.actions],
            "can_run_parallel": self.can_run_parallel,
            "dependencies": self.dependencies,
            "reconvergence_required": self.reconvergence_required,
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> PropagationWave:
        return cls(
            wave_id=d.get("wave_id", f"pw-{uuid4().hex[:12]}"),
            wave_number=d.get("wave_number", 0),
            nodes=d.get("nodes", []),
            actions=[PropagationAction.from_dict(a) for a in d.get("actions", [])],
            can_run_parallel=d.get("can_run_parallel", True),
            dependencies=d.get("dependencies", []),
            reconvergence_required=d.get("reconvergence_required", False),
        )


@dataclass
class PropagationPlan:
    plan_id: str = field(default_factory=lambda: f"pp-{uuid4().hex[:12]}")
    change_event_id: str = ""
    root_node_id: str = ""
    affected_nodes: list[str] = field(default_factory=list)
    propagation_waves: list[PropagationWave] = field(default_factory=list)
    blocked_nodes: list[str] = field(default_factory=list)
    approval_required_nodes: list[str] = field(default_factory=list)
    human_required_nodes: list[str] = field(default_factory=list)
    validation_required_nodes: list[str] = field(default_factory=list)
    no_op_nodes: list[str] = field(default_factory=list)
    expected_updates: int = 0
    risk_summary: dict[str, Any] = field(default_factory=dict)
    execution_mode: str = "dry_run"
    created_at: float = field(default_factory=time.time)

    def to_dict(self) -> dict[str, Any]:
        return {
            "plan_id": self.plan_id,
            "change_event_id": self.change_event_id,
            "root_node_id": self.root_node_id,
            "affected_nodes": self.affected_nodes,
            "propagation_waves": [w.to_dict() for w in self.propagation_waves],
            "blocked_nodes": self.blocked_nodes,
            "approval_required_nodes": self.approval_required_nodes,
            "human_required_nodes": self.human_required_nodes,
            "validation_required_nodes": self.validation_required_nodes,
            "no_op_nodes": self.no_op_nodes,
            "expected_updates": self.expected_updates,
            "risk_summary": self.risk_summary,
            "execution_mode": self.execution_mode,
            "created_at": self.created_at,
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> PropagationPlan:
        return cls(
            plan_id=d.get("plan_id", f"pp-{uuid4().hex[:12]}"),
            change_event_id=d.get("change_event_id", ""),
            root_node_id=d.get("root_node_id", ""),
            affected_nodes=d.get("affected_nodes", []),
            propagation_waves=[PropagationWave.from_dict(w) for w in d.get("propagation_waves", [])],
            blocked_nodes=d.get("blocked_nodes", []),
            approval_required_nodes=d.get("approval_required_nodes", []),
            human_required_nodes=d.get("human_required_nodes", []),
            validation_required_nodes=d.get("validation_required_nodes", []),
            no_op_nodes=d.get("no_op_nodes", []),
            expected_updates=d.get("expected_updates", 0),
            risk_summary=d.get("risk_summary", {}),
            execution_mode=d.get("execution_mode", "dry_run"),
            created_at=d.get("created_at", time.time()),
        )


@dataclass
class PropagationResult:
    result_id: str = field(default_factory=lambda: f"pr-{uuid4().hex[:12]}")
    plan_id: str = ""
    change_event_id: str = ""
    wave_results: list[dict[str, Any]] = field(default_factory=list)
    completed_actions: list[str] = field(default_factory=list)
    failed_actions: list[str] = field(default_factory=list)
    blocked_actions: list[str] = field(default_factory=list)
    approval_required_actions: list[str] = field(default_factory=list)
    human_required_actions: list[str] = field(default_factory=list)
    no_op_actions: list[str] = field(default_factory=list)
    reconvergence_results: list[dict[str, Any]] = field(default_factory=list)
    duration_ms: float = 0.0
    status: str = "pending"

    def to_dict(self) -> dict[str, Any]:
        return {
            "result_id": self.result_id,
            "plan_id": self.plan_id,
            "change_event_id": self.change_event_id,
            "wave_results": self.wave_results,
            "completed_actions": self.completed_actions,
            "failed_actions": self.failed_actions,
            "blocked_actions": self.blocked_actions,
            "approval_required_actions": self.approval_required_actions,
            "human_required_actions": self.human_required_actions,
            "no_op_actions": self.no_op_actions,
            "reconvergence_results": self.reconvergence_results,
            "duration_ms": self.duration_ms,
            "status": self.status,
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> PropagationResult:
        return cls(
            result_id=d.get("result_id", f"pr-{uuid4().hex[:12]}"),
            plan_id=d.get("plan_id", ""),
            change_event_id=d.get("change_event_id", ""),
            wave_results=d.get("wave_results", []),
            completed_actions=d.get("completed_actions", []),
            failed_actions=d.get("failed_actions", []),
            blocked_actions=d.get("blocked_actions", []),
            approval_required_actions=d.get("approval_required_actions", []),
            human_required_actions=d.get("human_required_actions", []),
            no_op_actions=d.get("no_op_actions", []),
            reconvergence_results=d.get("reconvergence_results", []),
            duration_ms=d.get("duration_ms", 0.0),
            status=d.get("status", "pending"),
        )


def persist_change_events(events: list[ChangeEvent], path: str | None = None) -> str:
    path = path or os.path.join(
        _REPO_ROOT, "data", "umh", "propagation_graph", "change_events.jsonl",
    )
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as f:
        for event in events:
            f.write(json.dumps(event.to_dict()) + "\n")
    return path


def load_change_events(path: str | None = None) -> list[ChangeEvent]:
    path = path or os.path.join(
        _REPO_ROOT, "data", "umh", "propagation_graph", "change_events.jsonl",
    )
    if not os.path.exists(path):
        return []
    events = []
    with open(path) as f:
        for line in f:
            line = line.strip()
            if line:
                events.append(ChangeEvent.from_dict(json.loads(line)))
    return events


def persist_propagation_plans(plans: list[PropagationPlan], path: str | None = None) -> str:
    path = path or os.path.join(
        _REPO_ROOT, "data", "umh", "propagation_graph", "propagation_plans.jsonl",
    )
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as f:
        for plan in plans:
            f.write(json.dumps(plan.to_dict()) + "\n")
    return path


def persist_propagation_results(results: list[PropagationResult], path: str | None = None) -> str:
    path = path or os.path.join(
        _REPO_ROOT, "data", "umh", "propagation_graph", "propagation_results.jsonl",
    )
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as f:
        for result in results:
            f.write(json.dumps(result.to_dict()) + "\n")
    return path
