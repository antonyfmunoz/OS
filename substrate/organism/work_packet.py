"""Work Packet — canonical intent-to-execution container.

A WorkPacket captures user intent, desired end state, classification,
context, constraints, delegation topology, workcells, approval gates,
validation/rollback/propagation plans, and scoring. It is the atomic
unit of the Universal Work Queue.

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


class PacketLifecycleStatus(str, Enum):
    DRAFTED = "drafted"
    CLASSIFIED = "classified"
    PLANNED = "planned"
    READY_FOR_REVIEW = "ready_for_review"
    APPROVAL_PENDING = "approval_pending"
    APPROVED = "approved"
    DELEGATED = "delegated"
    EXECUTING = "executing"
    RECONVERGING = "reconverging"
    VALIDATING = "validating"
    COMPLETED = "completed"
    BLOCKED = "blocked"
    REJECTED = "rejected"
    FAILED = "failed"
    SUPERSEDED = "superseded"
    ARCHIVED = "archived"


_TERMINAL_STATUSES = frozenset({
    PacketLifecycleStatus.COMPLETED,
    PacketLifecycleStatus.REJECTED,
    PacketLifecycleStatus.FAILED,
    PacketLifecycleStatus.SUPERSEDED,
    PacketLifecycleStatus.ARCHIVED,
})

_VALID_TRANSITIONS: dict[PacketLifecycleStatus, frozenset[PacketLifecycleStatus]] = {
    PacketLifecycleStatus.DRAFTED: frozenset({
        PacketLifecycleStatus.CLASSIFIED, PacketLifecycleStatus.BLOCKED,
        PacketLifecycleStatus.SUPERSEDED, PacketLifecycleStatus.ARCHIVED,
    }),
    PacketLifecycleStatus.CLASSIFIED: frozenset({
        PacketLifecycleStatus.PLANNED, PacketLifecycleStatus.BLOCKED,
        PacketLifecycleStatus.SUPERSEDED,
    }),
    PacketLifecycleStatus.PLANNED: frozenset({
        PacketLifecycleStatus.READY_FOR_REVIEW, PacketLifecycleStatus.BLOCKED,
        PacketLifecycleStatus.SUPERSEDED,
    }),
    PacketLifecycleStatus.READY_FOR_REVIEW: frozenset({
        PacketLifecycleStatus.APPROVAL_PENDING, PacketLifecycleStatus.BLOCKED,
        PacketLifecycleStatus.SUPERSEDED,
    }),
    PacketLifecycleStatus.APPROVAL_PENDING: frozenset({
        PacketLifecycleStatus.APPROVED, PacketLifecycleStatus.REJECTED,
        PacketLifecycleStatus.BLOCKED,
    }),
    PacketLifecycleStatus.APPROVED: frozenset({
        PacketLifecycleStatus.DELEGATED, PacketLifecycleStatus.BLOCKED,
    }),
    PacketLifecycleStatus.DELEGATED: frozenset({
        PacketLifecycleStatus.EXECUTING, PacketLifecycleStatus.BLOCKED,
        PacketLifecycleStatus.FAILED,
    }),
    PacketLifecycleStatus.EXECUTING: frozenset({
        PacketLifecycleStatus.RECONVERGING, PacketLifecycleStatus.VALIDATING,
        PacketLifecycleStatus.FAILED, PacketLifecycleStatus.BLOCKED,
    }),
    PacketLifecycleStatus.RECONVERGING: frozenset({
        PacketLifecycleStatus.VALIDATING, PacketLifecycleStatus.FAILED,
        PacketLifecycleStatus.BLOCKED,
    }),
    PacketLifecycleStatus.VALIDATING: frozenset({
        PacketLifecycleStatus.COMPLETED, PacketLifecycleStatus.FAILED,
        PacketLifecycleStatus.BLOCKED,
    }),
    PacketLifecycleStatus.COMPLETED: frozenset({PacketLifecycleStatus.ARCHIVED}),
    PacketLifecycleStatus.BLOCKED: frozenset({
        PacketLifecycleStatus.DRAFTED, PacketLifecycleStatus.CLASSIFIED,
        PacketLifecycleStatus.PLANNED, PacketLifecycleStatus.READY_FOR_REVIEW,
        PacketLifecycleStatus.SUPERSEDED, PacketLifecycleStatus.ARCHIVED,
    }),
    PacketLifecycleStatus.REJECTED: frozenset({PacketLifecycleStatus.ARCHIVED}),
    PacketLifecycleStatus.FAILED: frozenset({
        PacketLifecycleStatus.DRAFTED, PacketLifecycleStatus.ARCHIVED,
    }),
    PacketLifecycleStatus.SUPERSEDED: frozenset({PacketLifecycleStatus.ARCHIVED}),
    PacketLifecycleStatus.ARCHIVED: frozenset(),
}


@dataclass
class WorkPacket:
    packet_id: str = field(default_factory=lambda: f"wp-{uuid4().hex[:12]}")
    title: str = ""
    user_intent: str = ""
    desired_end_state: str = ""
    intent_summary: str = ""
    domain: str = ""
    subdomain: str = ""
    project: str = ""
    company: str = ""
    product: str = ""
    related_entities: list[str] = field(default_factory=list)
    source_type: str = ""
    source_id: str = ""
    source_evidence: list[dict[str, Any]] = field(default_factory=list)
    context_summary: str = ""
    current_state: str = ""
    desired_state: str = ""
    constraints: list[str] = field(default_factory=list)
    assumptions: list[str] = field(default_factory=list)
    success_criteria: list[str] = field(default_factory=list)
    failure_criteria: list[str] = field(default_factory=list)
    leverage_score: float = 0.0
    effectiveness_score: float = 0.0
    efficiency_score: float = 0.0
    risk_class: str = "low"
    risk_factors: list[str] = field(default_factory=list)
    expected_impact: str = ""
    expected_readiness_delta: float = 0.0
    priority: int = 50
    urgency: int = 50
    dependencies: list[str] = field(default_factory=list)
    blockers: list[str] = field(default_factory=list)
    required_knowledge_models: list[str] = field(default_factory=list)
    required_templates: list[str] = field(default_factory=list)
    required_workflows: list[str] = field(default_factory=list)
    required_tools: list[str] = field(default_factory=list)
    required_role_contracts: list[str] = field(default_factory=list)
    delegation_topology_id: str = ""
    workcells: list[str] = field(default_factory=list)
    advisor_council: list[str] = field(default_factory=list)
    reconvergence_protocol: str = ""
    human_required_actions: list[str] = field(default_factory=list)
    approval_gates: list[str] = field(default_factory=list)
    validation_plan: str = ""
    rollback_plan: str = ""
    propagation_plan: str = ""
    output_contracts: list[str] = field(default_factory=list)
    executor_policy: str = ""
    memory_update_targets: list[str] = field(default_factory=list)
    template_update_targets: list[str] = field(default_factory=list)
    agent_reliability_targets: list[str] = field(default_factory=list)
    status: PacketLifecycleStatus = PacketLifecycleStatus.DRAFTED
    status_reason: str = ""
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)
    expires_at: float = 0.0
    parent_packet_id: str = ""
    child_packet_ids: list[str] = field(default_factory=list)
    linked_self_build_item_id: str = ""
    linked_roadmap_phase: str = ""
    linked_approval_packet_id: str = ""
    linked_sandbox_id: str = ""
    linked_pr_url: str = ""
    linked_production_truth_delta_id: str = ""
    outcome_ids: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "packet_id": self.packet_id,
            "title": self.title,
            "user_intent": self.user_intent,
            "desired_end_state": self.desired_end_state,
            "intent_summary": self.intent_summary,
            "domain": self.domain,
            "subdomain": self.subdomain,
            "project": self.project,
            "company": self.company,
            "product": self.product,
            "related_entities": self.related_entities,
            "source_type": self.source_type,
            "source_id": self.source_id,
            "source_evidence": self.source_evidence,
            "context_summary": self.context_summary,
            "current_state": self.current_state,
            "desired_state": self.desired_state,
            "constraints": self.constraints,
            "assumptions": self.assumptions,
            "success_criteria": self.success_criteria,
            "failure_criteria": self.failure_criteria,
            "leverage_score": round(self.leverage_score, 4),
            "effectiveness_score": round(self.effectiveness_score, 4),
            "efficiency_score": round(self.efficiency_score, 4),
            "risk_class": self.risk_class,
            "risk_factors": self.risk_factors,
            "expected_impact": self.expected_impact,
            "expected_readiness_delta": round(self.expected_readiness_delta, 4),
            "priority": self.priority,
            "urgency": self.urgency,
            "dependencies": self.dependencies,
            "blockers": self.blockers,
            "required_knowledge_models": self.required_knowledge_models,
            "required_templates": self.required_templates,
            "required_workflows": self.required_workflows,
            "required_tools": self.required_tools,
            "required_role_contracts": self.required_role_contracts,
            "delegation_topology_id": self.delegation_topology_id,
            "workcells": self.workcells,
            "advisor_council": self.advisor_council,
            "reconvergence_protocol": self.reconvergence_protocol,
            "human_required_actions": self.human_required_actions,
            "approval_gates": self.approval_gates,
            "validation_plan": self.validation_plan,
            "rollback_plan": self.rollback_plan,
            "propagation_plan": self.propagation_plan,
            "output_contracts": self.output_contracts,
            "executor_policy": self.executor_policy,
            "memory_update_targets": self.memory_update_targets,
            "template_update_targets": self.template_update_targets,
            "agent_reliability_targets": self.agent_reliability_targets,
            "status": self.status.value,
            "status_reason": self.status_reason,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "expires_at": self.expires_at,
            "parent_packet_id": self.parent_packet_id,
            "child_packet_ids": self.child_packet_ids,
            "linked_self_build_item_id": self.linked_self_build_item_id,
            "linked_roadmap_phase": self.linked_roadmap_phase,
            "linked_approval_packet_id": self.linked_approval_packet_id,
            "linked_sandbox_id": self.linked_sandbox_id,
            "linked_pr_url": self.linked_pr_url,
            "linked_production_truth_delta_id": self.linked_production_truth_delta_id,
            "outcome_ids": self.outcome_ids,
        }

    def to_safe_dict(self) -> dict[str, Any]:
        return {
            "packet_id": self.packet_id,
            "title": self.title,
            "user_intent": self.user_intent,
            "desired_end_state": self.desired_end_state,
            "domain": self.domain,
            "subdomain": self.subdomain,
            "project": self.project,
            "company": self.company,
            "product": self.product,
            "leverage_score": round(self.leverage_score, 4),
            "effectiveness_score": round(self.effectiveness_score, 4),
            "efficiency_score": round(self.efficiency_score, 4),
            "risk_class": self.risk_class,
            "priority": self.priority,
            "urgency": self.urgency,
            "status": self.status.value,
            "status_reason": self.status_reason,
            "human_required_actions": self.human_required_actions,
            "approval_gates": self.approval_gates,
            "delegation_topology_id": self.delegation_topology_id,
            "linked_roadmap_phase": self.linked_roadmap_phase,
            "blockers": self.blockers,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> WorkPacket:
        status_raw = d.get("status", "drafted")
        try:
            status = PacketLifecycleStatus(status_raw)
        except ValueError:
            status = PacketLifecycleStatus.DRAFTED
        return cls(
            packet_id=d.get("packet_id", f"wp-{uuid4().hex[:12]}"),
            title=d.get("title", ""),
            user_intent=d.get("user_intent", ""),
            desired_end_state=d.get("desired_end_state", ""),
            intent_summary=d.get("intent_summary", ""),
            domain=d.get("domain", ""),
            subdomain=d.get("subdomain", ""),
            project=d.get("project", ""),
            company=d.get("company", ""),
            product=d.get("product", ""),
            related_entities=d.get("related_entities", []),
            source_type=d.get("source_type", ""),
            source_id=d.get("source_id", ""),
            source_evidence=d.get("source_evidence", []),
            context_summary=d.get("context_summary", ""),
            current_state=d.get("current_state", ""),
            desired_state=d.get("desired_state", ""),
            constraints=d.get("constraints", []),
            assumptions=d.get("assumptions", []),
            success_criteria=d.get("success_criteria", []),
            failure_criteria=d.get("failure_criteria", []),
            leverage_score=float(d.get("leverage_score", 0.0)),
            effectiveness_score=float(d.get("effectiveness_score", 0.0)),
            efficiency_score=float(d.get("efficiency_score", 0.0)),
            risk_class=d.get("risk_class", "low"),
            risk_factors=d.get("risk_factors", []),
            expected_impact=d.get("expected_impact", ""),
            expected_readiness_delta=float(d.get("expected_readiness_delta", 0.0)),
            priority=int(d.get("priority", 50)),
            urgency=int(d.get("urgency", 50)),
            dependencies=d.get("dependencies", []),
            blockers=d.get("blockers", []),
            required_knowledge_models=d.get("required_knowledge_models", []),
            required_templates=d.get("required_templates", []),
            required_workflows=d.get("required_workflows", []),
            required_tools=d.get("required_tools", []),
            required_role_contracts=d.get("required_role_contracts", []),
            delegation_topology_id=d.get("delegation_topology_id", ""),
            workcells=d.get("workcells", []),
            advisor_council=d.get("advisor_council", []),
            reconvergence_protocol=d.get("reconvergence_protocol", ""),
            human_required_actions=d.get("human_required_actions", []),
            approval_gates=d.get("approval_gates", []),
            validation_plan=d.get("validation_plan", ""),
            rollback_plan=d.get("rollback_plan", ""),
            propagation_plan=d.get("propagation_plan", ""),
            output_contracts=d.get("output_contracts", []),
            executor_policy=d.get("executor_policy", ""),
            memory_update_targets=d.get("memory_update_targets", []),
            template_update_targets=d.get("template_update_targets", []),
            agent_reliability_targets=d.get("agent_reliability_targets", []),
            status=status,
            status_reason=d.get("status_reason", ""),
            created_at=float(d.get("created_at", time.time())),
            updated_at=float(d.get("updated_at", time.time())),
            expires_at=float(d.get("expires_at", 0.0)),
            parent_packet_id=d.get("parent_packet_id", ""),
            child_packet_ids=d.get("child_packet_ids", []),
            linked_self_build_item_id=d.get("linked_self_build_item_id", ""),
            linked_roadmap_phase=d.get("linked_roadmap_phase", ""),
            linked_approval_packet_id=d.get("linked_approval_packet_id", ""),
            linked_sandbox_id=d.get("linked_sandbox_id", ""),
            linked_pr_url=d.get("linked_pr_url", ""),
            linked_production_truth_delta_id=d.get("linked_production_truth_delta_id", ""),
            outcome_ids=d.get("outcome_ids", []),
        )

    def summarize(self) -> str:
        parts = [f"[{self.packet_id}] {self.title}"]
        if self.domain:
            parts.append(f"domain={self.domain}")
        if self.subdomain:
            parts.append(f"sub={self.subdomain}")
        parts.append(f"status={self.status.value}")
        parts.append(f"leverage={self.leverage_score:.2f}")
        parts.append(f"risk={self.risk_class}")
        if self.human_required_actions:
            parts.append(f"human_actions={len(self.human_required_actions)}")
        return " | ".join(parts)

    def requires_human_action(self) -> bool:
        return len(self.human_required_actions) > 0

    def requires_operator_approval(self) -> bool:
        return len(self.approval_gates) > 0

    def can_delegate(self) -> bool:
        return (
            self.status == PacketLifecycleStatus.APPROVED
            and not self.blockers
            and self.delegation_topology_id != ""
        )

    def is_execution_ready(self) -> bool:
        return (
            self.status in {PacketLifecycleStatus.APPROVED, PacketLifecycleStatus.DELEGATED}
            and not self.blockers
            and self.risk_class != "medium"
        )


def persist_packets(
    packets: list[WorkPacket],
    store_path: str | None = None,
) -> None:
    path = store_path or os.path.join(
        _REPO_ROOT, "data", "umh", "universal_work", "work_packets.jsonl",
    )
    dir_path = os.path.dirname(path)
    os.makedirs(dir_path, exist_ok=True)
    fd, tmp_path = tempfile.mkstemp(dir=dir_path, suffix=".tmp")
    try:
        with os.fdopen(fd, "w") as f:
            for pkt in packets:
                f.write(json.dumps(pkt.to_dict()) + "\n")
        os.replace(tmp_path, path)
    except BaseException:
        if os.path.exists(tmp_path):
            os.unlink(tmp_path)
        raise


def load_packets(store_path: str | None = None) -> list[WorkPacket]:
    path = store_path or os.path.join(
        _REPO_ROOT, "data", "umh", "universal_work", "work_packets.jsonl",
    )
    if not os.path.exists(path):
        return []
    packets: list[WorkPacket] = []
    with open(path, "r") as f:
        for line_num, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                continue
            try:
                d = json.loads(line)
                packets.append(WorkPacket.from_dict(d))
            except (json.JSONDecodeError, KeyError, TypeError) as exc:
                raise ValueError(
                    f"Corrupt work packet at line {line_num}: {exc}"
                ) from exc
    return packets
