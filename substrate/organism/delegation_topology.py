"""Delegation Topology Planner — chooses execution structure for a work packet.

Deterministic topology selection based on work packet classification.
Uses simplest topology that satisfies the intent.

Phase 11.1. UMH substrate subsystem. Instance-agnostic.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from typing import Any
from uuid import uuid4

logger = logging.getLogger(__name__)


class TopologyType:
    SINGLE_AGENT = "single_agent"
    ADVISOR_COUNCIL = "advisor_council"
    SEQUENTIAL_WORKFLOW = "sequential_workflow"
    PARALLEL_WORKCELL = "parallel_workcell"
    RECURSIVE_WORKCELL = "recursive_workcell"
    HUMAN_ASSISTED = "human_assisted"
    EXTERNAL_HUMAN_REQUIRED = "external_human_required"
    TOOL_ONLY = "tool_only"
    PLANNING_ONLY = "planning_only"
    GOVERNED_EXECUTION = "governed_execution"

    ALL = [
        SINGLE_AGENT, ADVISOR_COUNCIL, SEQUENTIAL_WORKFLOW,
        PARALLEL_WORKCELL, RECURSIVE_WORKCELL, HUMAN_ASSISTED,
        EXTERNAL_HUMAN_REQUIRED, TOOL_ONLY, PLANNING_ONLY,
        GOVERNED_EXECUTION,
    ]


@dataclass
class DelegationTopology:
    topology_id: str = field(default_factory=lambda: f"topo-{uuid4().hex[:8]}")
    packet_id: str = ""
    topology_type: str = TopologyType.SINGLE_AGENT
    reason: str = ""
    lead_role_contract: str = ""
    supporting_role_contracts: list[str] = field(default_factory=list)
    workcells: list[str] = field(default_factory=list)
    advisor_council: list[str] = field(default_factory=list)
    subdivision_policy: str = ""
    reconvergence_protocol: str = ""
    governance_boundary: str = ""
    expected_outputs: list[str] = field(default_factory=list)
    confidence: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "topology_id": self.topology_id,
            "packet_id": self.packet_id,
            "topology_type": self.topology_type,
            "reason": self.reason,
            "lead_role_contract": self.lead_role_contract,
            "supporting_role_contracts": self.supporting_role_contracts,
            "workcells": self.workcells,
            "advisor_council": self.advisor_council,
            "subdivision_policy": self.subdivision_policy,
            "reconvergence_protocol": self.reconvergence_protocol,
            "governance_boundary": self.governance_boundary,
            "expected_outputs": self.expected_outputs,
            "confidence": round(self.confidence, 4),
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> DelegationTopology:
        return cls(
            topology_id=d.get("topology_id", f"topo-{uuid4().hex[:8]}"),
            packet_id=d.get("packet_id", ""),
            topology_type=d.get("topology_type", TopologyType.SINGLE_AGENT),
            reason=d.get("reason", ""),
            lead_role_contract=d.get("lead_role_contract", ""),
            supporting_role_contracts=d.get("supporting_role_contracts", []),
            workcells=d.get("workcells", []),
            advisor_council=d.get("advisor_council", []),
            subdivision_policy=d.get("subdivision_policy", ""),
            reconvergence_protocol=d.get("reconvergence_protocol", ""),
            governance_boundary=d.get("governance_boundary", ""),
            expected_outputs=d.get("expected_outputs", []),
            confidence=float(d.get("confidence", 0.0)),
        )


class DelegationTopologyPlanner:
    """Deterministic topology selection based on classification."""

    def plan(
        self,
        risk_class: str,
        complexity: str,
        work_type: str,
        human_action_required: bool,
        approval_required: bool,
        execution_possible: bool,
        parallel_needed: bool,
        packet_id: str = "",
    ) -> DelegationTopology:
        topo = DelegationTopology(packet_id=packet_id)

        if not execution_possible:
            topo.topology_type = TopologyType.PLANNING_ONLY
            topo.reason = "High-risk work requires planning only"
            topo.governance_boundary = "no_execution"
            topo.confidence = 0.9
            return topo

        if human_action_required and risk_class == "high":
            topo.topology_type = TopologyType.EXTERNAL_HUMAN_REQUIRED
            topo.reason = "High-risk with human action required"
            topo.governance_boundary = "operator_approval_required"
            topo.confidence = 0.85
            return topo

        if human_action_required:
            topo.topology_type = TopologyType.HUMAN_ASSISTED
            topo.reason = "Human action required for completion"
            topo.governance_boundary = "human_checkpoint"
            topo.confidence = 0.85
            return topo

        if complexity == "strategic":
            topo.topology_type = TopologyType.ADVISOR_COUNCIL
            topo.reason = "Strategic complexity requires multi-perspective analysis"
            topo.reconvergence_protocol = "synthesis_required"
            topo.confidence = 0.8
            return topo

        if parallel_needed and complexity == "complex":
            topo.topology_type = TopologyType.PARALLEL_WORKCELL
            topo.reason = "Complex work benefits from parallel execution"
            topo.reconvergence_protocol = "merge_required"
            topo.subdivision_policy = "depth_limited"
            topo.confidence = 0.8
            return topo

        if work_type in ("cleanup", "configuration"):
            topo.topology_type = TopologyType.TOOL_ONLY
            topo.reason = "Simple tool-based operation"
            topo.confidence = 0.95
            return topo

        if approval_required:
            topo.topology_type = TopologyType.GOVERNED_EXECUTION
            topo.reason = "Execution requires governance approval"
            topo.governance_boundary = "approval_gate"
            topo.confidence = 0.85
            return topo

        if complexity == "complex":
            topo.topology_type = TopologyType.SEQUENTIAL_WORKFLOW
            topo.reason = "Complex work with sequential dependencies"
            topo.confidence = 0.85
            return topo

        topo.topology_type = TopologyType.SINGLE_AGENT
        topo.reason = "Simple work suitable for single agent"
        topo.confidence = 0.9
        return topo

    def assign_roles(
        self,
        topo: DelegationTopology,
        work_type: str,
        domain: str,
    ) -> DelegationTopology:
        role_mapping = {
            "implementation": "role-impl-op",
            "research": "role-research-op",
            "analysis": "role-research-op",
            "planning": "role-strategy-op",
            "content_creation": "role-content-op",
            "deployment": "role-ops-op",
            "testing": "role-verify-op",
            "verification": "role-verify-op",
            "audit": "role-verify-op",
            "financial_analysis": "role-finance-op",
            "coordination": "role-orchestrator",
            "cleanup": "role-ops-op",
            "configuration": "role-ops-op",
            "monitoring": "role-ops-op",
        }
        topo.lead_role_contract = role_mapping.get(work_type, "role-impl-op")

        if topo.topology_type == TopologyType.ADVISOR_COUNCIL:
            topo.supporting_role_contracts = ["role-strategy-op", "role-research-op"]
            topo.advisor_council = ["role-strategy-op", "role-research-op"]

        if topo.topology_type in (TopologyType.PARALLEL_WORKCELL, TopologyType.SEQUENTIAL_WORKFLOW):
            topo.supporting_role_contracts = ["role-verify-op"]

        if topo.topology_type == TopologyType.GOVERNED_EXECUTION:
            topo.supporting_role_contracts = ["role-verify-op"]

        return topo
