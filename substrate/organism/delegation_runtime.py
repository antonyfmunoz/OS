"""Delegation Runtime — intent classification, delegation proposals, mission lifecycle.

Answers: "How does work leave the Primary Orchestrator without blocking it?"

The Primary Orchestrator is a persistent communication layer. It never executes.
This runtime converts clarified operator intent into governed delegation missions
that ephemeral nested orchestrators claim and execute.

Right Rail Execution Invariant: No operator message may cause direct execution
from the Right Rail. Even EXECUTION intents resolve to governed work packet state.

Flow:
  Operator message
    → classify_intent() → OperatorIntentType
    → WORK_INTENT → explain_understanding() → propose_delegation()
    → Operator approves proposal → DelegationMission created → queue
    → Nested Orchestrator claims → drafts WorkPacket
    → Operator approves WP → GovernedWorkRuntime → execution
    → EXECUTION → resolve to existing approved WP or create proposal path

Campaign 4.7. UMH substrate layer. Instance-agnostic.
"""

from __future__ import annotations

import json
import logging
import re
import time
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any
from uuid import uuid4

logger = logging.getLogger(__name__)


# ── Intent Classification ────────────────────────────────────────────────


class OperatorIntentType(str, Enum):
    DISCUSSION = "discussion"
    QUESTION = "question"
    DECISION = "decision"
    WORK_INTENT = "work_intent"
    APPROVAL = "approval"
    EXECUTION = "execution"


_DISCUSSION_PATTERNS: list[re.Pattern[str]] = [
    re.compile(r"\blet'?s talk about\b", re.I),
    re.compile(r"\bwhat do you think about\b", re.I),
    re.compile(r"\bi'?m considering\b", re.I),
    re.compile(r"\bi'?m thinking\b", re.I),
    re.compile(r"\bbrainstorm\b", re.I),
    re.compile(r"\bexplore the idea\b", re.I),
    re.compile(r"\bwhat if we\b", re.I),
    re.compile(r"\bhow about\b", re.I),
]

_QUESTION_PATTERNS: list[re.Pattern[str]] = [
    re.compile(
        r"^(what|how|why|when|where|which|who|can|could|should|would|is|are|do|does)\b", re.I
    ),
    re.compile(r"\bpros and cons\b", re.I),
    re.compile(r"\bwhat are the\b", re.I),
    re.compile(r"\bhow does\b", re.I),
    re.compile(r"\bshould we\b", re.I),
    re.compile(r"\bcan we\b", re.I),
    re.compile(r"\bis it possible\b", re.I),
    re.compile(r"\?$"),
]

_DECISION_PATTERNS: list[re.Pattern[str]] = [
    re.compile(r"\bi think we should\b", re.I),
    re.compile(r"\blet'?s go with\b", re.I),
    re.compile(r"\bi'?ve decided\b", re.I),
    re.compile(r"\bmy decision is\b", re.I),
    re.compile(r"\bwe'?re going with\b", re.I),
    re.compile(r"\bthe plan is\b", re.I),
]

_APPROVAL_PATTERNS: list[re.Pattern[str]] = [
    re.compile(r"^(approve|reject|deny)\b", re.I),
    re.compile(r"\byes,?\s*(do it|go ahead|proceed|approved|execute)\b", re.I),
    re.compile(r"\bgo ahead\b", re.I),
    re.compile(r"\bapproved?\b", re.I),
    re.compile(r"\brejected?\b", re.I),
    re.compile(r"\blooks good,?\s*(proceed|go)\b", re.I),
]

_EXECUTION_PATTERNS: list[re.Pattern[str]] = [
    re.compile(r"^deploy\b", re.I),
    re.compile(r"^run\b", re.I),
    re.compile(r"^execute\b", re.I),
    re.compile(r"^start\b", re.I),
    re.compile(r"^ship\b", re.I),
    re.compile(r"^launch\b", re.I),
    re.compile(r"\bdeploy (it|this|that|now)\b", re.I),
    re.compile(r"\brun (it|this|that|the tests?|now)\b", re.I),
    re.compile(r"\bship (it|this|that|now)\b", re.I),
]

_WORK_INTENT_PATTERNS: list[re.Pattern[str]] = [
    re.compile(
        r"^(use|add|build|create|implement|migrate|set up|install|configure|remove|delete|update|upgrade|replace|integrate|connect|wire|extract|refactor)\b",
        re.I,
    ),
    re.compile(r"\buse\s+\w+\s+(for|in|on|with)\b", re.I),
    re.compile(r"\badd\s+\w+\s+to\b", re.I),
    re.compile(r"\bbuild\s+(a|the|an)\b", re.I),
    re.compile(r"\bmigrate\s+(from|to)\b", re.I),
    re.compile(r"\bintegrate\s+\w+\s+(with|into)\b", re.I),
]


def classify_intent(message: str) -> OperatorIntentType:
    """Deterministic intent classification. No LLM. Pattern-matched."""
    text = message.strip()
    if not text:
        return OperatorIntentType.DISCUSSION

    for p in _APPROVAL_PATTERNS:
        if p.search(text):
            return OperatorIntentType.APPROVAL

    for p in _EXECUTION_PATTERNS:
        if p.search(text):
            return OperatorIntentType.EXECUTION

    for p in _WORK_INTENT_PATTERNS:
        if p.search(text):
            return OperatorIntentType.WORK_INTENT

    for p in _DECISION_PATTERNS:
        if p.search(text):
            return OperatorIntentType.DECISION

    for p in _DISCUSSION_PATTERNS:
        if p.search(text):
            return OperatorIntentType.DISCUSSION

    for p in _QUESTION_PATTERNS:
        if p.search(text):
            return OperatorIntentType.QUESTION

    return OperatorIntentType.DISCUSSION


# ── Delegation Types ─────────────────────────────────────────────────────


class DelegationMissionStatus(str, Enum):
    PROPOSED = "proposed"
    APPROVED = "approved"
    QUEUED = "queued"
    CLAIMED = "claimed"
    PLANNING = "planning"
    WORK_PACKET_DRAFTED = "work_packet_drafted"
    WORK_PACKET_APPROVED = "work_packet_approved"
    EXECUTING = "executing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


_VALID_TRANSITIONS: dict[DelegationMissionStatus, list[DelegationMissionStatus]] = {
    DelegationMissionStatus.PROPOSED: [
        DelegationMissionStatus.APPROVED,
        DelegationMissionStatus.CANCELLED,
    ],
    DelegationMissionStatus.APPROVED: [
        DelegationMissionStatus.QUEUED,
        DelegationMissionStatus.CANCELLED,
    ],
    DelegationMissionStatus.QUEUED: [
        DelegationMissionStatus.CLAIMED,
        DelegationMissionStatus.CANCELLED,
    ],
    DelegationMissionStatus.CLAIMED: [
        DelegationMissionStatus.PLANNING,
        DelegationMissionStatus.FAILED,
        DelegationMissionStatus.CANCELLED,
    ],
    DelegationMissionStatus.PLANNING: [
        DelegationMissionStatus.WORK_PACKET_DRAFTED,
        DelegationMissionStatus.FAILED,
        DelegationMissionStatus.CANCELLED,
    ],
    DelegationMissionStatus.WORK_PACKET_DRAFTED: [
        DelegationMissionStatus.WORK_PACKET_APPROVED,
        DelegationMissionStatus.CANCELLED,
    ],
    DelegationMissionStatus.WORK_PACKET_APPROVED: [
        DelegationMissionStatus.EXECUTING,
        DelegationMissionStatus.CANCELLED,
    ],
    DelegationMissionStatus.EXECUTING: [
        DelegationMissionStatus.COMPLETED,
        DelegationMissionStatus.FAILED,
    ],
    DelegationMissionStatus.COMPLETED: [],
    DelegationMissionStatus.FAILED: [],
    DelegationMissionStatus.CANCELLED: [],
}


@dataclass
class DelegationMission:
    mission_id: str = ""
    title: str = ""
    operator_intent: str = ""
    clarified_intent: str = ""
    projection: str = ""
    repository: str = ""
    device_target: str = ""
    priority: str = "normal"
    risk_class: str = "low"
    required_capabilities: list[str] = field(default_factory=list)
    required_specialists: list[str] = field(default_factory=list)
    topology_type: str = ""
    status: DelegationMissionStatus = DelegationMissionStatus.PROPOSED
    proposal_id: str = ""
    nested_orchestrator_id: str = ""
    work_packet_id: str = ""
    created_at: float = 0.0
    claimed_at: float = 0.0
    completed_at: float = 0.0
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.mission_id:
            self.mission_id = f"dm-{uuid4().hex[:8]}"
        if self.created_at == 0.0:
            self.created_at = time.time()

    def can_transition(self, to: DelegationMissionStatus) -> bool:
        return to in _VALID_TRANSITIONS.get(self.status, [])

    def transition(self, to: DelegationMissionStatus) -> None:
        if not self.can_transition(to):
            raise ValueError(f"Invalid transition: {self.status.value} → {to.value}")
        self.status = to

    def to_dict(self) -> dict[str, Any]:
        return {
            "mission_id": self.mission_id,
            "title": self.title,
            "operator_intent": self.operator_intent,
            "clarified_intent": self.clarified_intent,
            "projection": self.projection,
            "repository": self.repository,
            "device_target": self.device_target,
            "priority": self.priority,
            "risk_class": self.risk_class,
            "required_capabilities": self.required_capabilities,
            "required_specialists": self.required_specialists,
            "topology_type": self.topology_type,
            "status": self.status.value,
            "proposal_id": self.proposal_id,
            "nested_orchestrator_id": self.nested_orchestrator_id,
            "work_packet_id": self.work_packet_id,
            "created_at": self.created_at,
            "claimed_at": self.claimed_at,
            "completed_at": self.completed_at,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> DelegationMission:
        status_val = d.get("status", "proposed")
        try:
            status = DelegationMissionStatus(status_val)
        except ValueError:
            status = DelegationMissionStatus.PROPOSED
        return cls(
            mission_id=d.get("mission_id", ""),
            title=d.get("title", ""),
            operator_intent=d.get("operator_intent", ""),
            clarified_intent=d.get("clarified_intent", ""),
            projection=d.get("projection", ""),
            repository=d.get("repository", ""),
            device_target=d.get("device_target", ""),
            priority=d.get("priority", "normal"),
            risk_class=d.get("risk_class", "low"),
            required_capabilities=d.get("required_capabilities", []),
            required_specialists=d.get("required_specialists", []),
            topology_type=d.get("topology_type", ""),
            status=status,
            proposal_id=d.get("proposal_id", ""),
            nested_orchestrator_id=d.get("nested_orchestrator_id", ""),
            work_packet_id=d.get("work_packet_id", ""),
            created_at=float(d.get("created_at", 0.0)),
            claimed_at=float(d.get("claimed_at", 0.0)),
            completed_at=float(d.get("completed_at", 0.0)),
            metadata=d.get("metadata", {}),
        )


@dataclass
class DelegationProposal:
    proposal_id: str = ""
    operator_intent: str = ""
    proposed_title: str = ""
    proposed_scope: str = ""
    estimated_complexity: str = "simple"
    estimated_risk: str = "low"
    required_capabilities: list[str] = field(default_factory=list)
    topology_preview: dict[str, Any] = field(default_factory=dict)
    understanding: dict[str, Any] = field(default_factory=dict)
    why_delegate: str = ""
    what_orchestrator_keeps: list[str] = field(default_factory=list)
    what_gets_delegated: list[str] = field(default_factory=list)
    goal_refs: list[str] = field(default_factory=list)
    decision_refs: list[str] = field(default_factory=list)
    capability_refs: list[str] = field(default_factory=list)
    status: str = "pending"
    decided_at: float = 0.0
    created_at: float = 0.0

    def __post_init__(self) -> None:
        if not self.proposal_id:
            self.proposal_id = f"dp-{uuid4().hex[:8]}"
        if self.created_at == 0.0:
            self.created_at = time.time()

    def to_dict(self) -> dict[str, Any]:
        return {
            "proposal_id": self.proposal_id,
            "operator_intent": self.operator_intent,
            "proposed_title": self.proposed_title,
            "proposed_scope": self.proposed_scope,
            "estimated_complexity": self.estimated_complexity,
            "estimated_risk": self.estimated_risk,
            "required_capabilities": self.required_capabilities,
            "topology_preview": self.topology_preview,
            "understanding": self.understanding,
            "why_delegate": self.why_delegate,
            "what_orchestrator_keeps": self.what_orchestrator_keeps,
            "what_gets_delegated": self.what_gets_delegated,
            "goal_refs": self.goal_refs,
            "decision_refs": self.decision_refs,
            "capability_refs": self.capability_refs,
            "status": self.status,
            "decided_at": self.decided_at,
            "created_at": self.created_at,
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> DelegationProposal:
        return cls(
            proposal_id=d.get("proposal_id", ""),
            operator_intent=d.get("operator_intent", ""),
            proposed_title=d.get("proposed_title", ""),
            proposed_scope=d.get("proposed_scope", ""),
            estimated_complexity=d.get("estimated_complexity", "simple"),
            estimated_risk=d.get("estimated_risk", "low"),
            required_capabilities=d.get("required_capabilities", []),
            topology_preview=d.get("topology_preview", {}),
            understanding=d.get("understanding", {}),
            why_delegate=d.get("why_delegate", ""),
            what_orchestrator_keeps=d.get("what_orchestrator_keeps", []),
            what_gets_delegated=d.get("what_gets_delegated", []),
            goal_refs=d.get("goal_refs", []),
            decision_refs=d.get("decision_refs", []),
            capability_refs=d.get("capability_refs", []),
            status=d.get("status", "pending"),
            decided_at=float(d.get("decided_at", 0.0)),
            created_at=float(d.get("created_at", 0.0)),
        )


@dataclass
class NestedOrchestratorState:
    orchestrator_id: str = ""
    mission_id: str = ""
    status: str = "initializing"
    capabilities_used: list[str] = field(default_factory=list)
    work_packet_draft: dict[str, Any] | None = None
    progress_notes: list[str] = field(default_factory=list)
    created_at: float = 0.0
    completed_at: float = 0.0

    def __post_init__(self) -> None:
        if not self.orchestrator_id:
            self.orchestrator_id = f"no-{uuid4().hex[:8]}"
        if self.created_at == 0.0:
            self.created_at = time.time()

    def to_dict(self) -> dict[str, Any]:
        return {
            "orchestrator_id": self.orchestrator_id,
            "mission_id": self.mission_id,
            "status": self.status,
            "capabilities_used": self.capabilities_used,
            "work_packet_draft": self.work_packet_draft,
            "progress_notes": self.progress_notes,
            "created_at": self.created_at,
            "completed_at": self.completed_at,
        }


# ── Orchestrator-keeps / gets-delegated constants ────────────────────────

_ORCHESTRATOR_KEEPS: list[str] = [
    "operator_communication",
    "context_synthesis",
    "intent_clarification",
    "status_reporting",
    "session_continuity",
    "governance_explanations",
    "delegation_proposals",
]

_GETS_DELEGATED: list[str] = [
    "work_packet_construction",
    "execution_planning",
    "specialist_coordination",
    "code_changes",
    "execution_routing",
    "task_implementation",
]


# ── DelegationRuntime ────────────────────────────────────────────────────


class DelegationRuntime:
    """Converts clarified operator intent into governed delegation missions.

    The Primary Orchestrator stays available. Nested orchestrators do the work.
    All execution routes through GovernedWorkRuntime — delegation never bypasses.
    """

    def __init__(self, store_dir: str | None = None) -> None:
        from substrate.state.runtime_paths import runtime_state_dir

        self._store_dir = Path(store_dir) if store_dir else runtime_state_dir("organism")
        self._store_dir.mkdir(parents=True, exist_ok=True)
        self._missions_path = self._store_dir / "delegation_missions.jsonl"
        self._proposals_path = self._store_dir / "delegation_proposals.jsonl"

        self._missions: dict[str, DelegationMission] = {}
        self._proposals: dict[str, DelegationProposal] = {}
        self._nested_orchestrators: dict[str, NestedOrchestratorState] = {}
        self._max_concurrent = 3

        self._load()

    # ── Intent classification ────────────────────────────────────────

    def classify_intent(self, message: str) -> OperatorIntentType:
        return classify_intent(message)

    def explain_understanding(
        self,
        message: str,
        intent_type: OperatorIntentType,
    ) -> dict[str, Any]:
        """When WORK_INTENT or EXECUTION, explain what the orchestrator thinks
        the work affects. Presented to operator BEFORE offering delegation."""
        if intent_type not in (OperatorIntentType.WORK_INTENT, OperatorIntentType.EXECUTION):
            return {}

        from substrate.organism.intent_classifier import IntentClassifier

        classifier = IntentClassifier()
        classification = classifier.classify(message)

        affected_systems: list[str] = []
        if classification.domain:
            affected_systems.append(classification.domain)
        if classification.subdomain and classification.subdomain != "general":
            affected_systems.append(classification.subdomain)

        return {
            "affected_systems": affected_systems,
            "affected_projection": classification.project or classification.product or "",
            "affected_repo": "",
            "estimated_scope": classification.complexity,
            "work_type": classification.work_type,
            "risk_class": classification.risk_class,
            "domain": classification.domain,
            "entity": classification.entity,
            "classification": classification.to_dict(),
        }

    # ── Delegation proposal ──────────────────────────────────────────

    def propose_delegation(
        self,
        operator_intent: str,
        clarified_intent: str = "",
        understanding: dict[str, Any] | None = None,
    ) -> DelegationProposal:
        """Create a delegation proposal. Deterministic — no LLM."""
        from substrate.organism.delegation_topology import DelegationTopologyPlanner
        from substrate.organism.intent_classifier import IntentClassifier

        classifier = IntentClassifier()
        classification = classifier.classify(clarified_intent or operator_intent)

        planner = DelegationTopologyPlanner()
        topology = planner.plan(
            risk_class=classification.risk_class,
            complexity=classification.complexity,
            work_type=classification.work_type,
            human_action_required=classification.human_action_required,
            approval_required=classification.approval_required,
            execution_possible=classification.execution_possible,
            parallel_needed=classification.parallel_workcells_needed,
        )
        topology = planner.assign_roles(topology, classification.work_type, classification.domain)

        title = self._generate_title(classification)
        scope = self._generate_scope(classification)
        why = self._delegation_reason(classification, topology)

        proposal = DelegationProposal(
            operator_intent=operator_intent,
            proposed_title=title,
            proposed_scope=scope,
            estimated_complexity=classification.complexity,
            estimated_risk=classification.risk_class,
            required_capabilities=[classification.required_executor_type]
            if classification.required_executor_type
            else [],
            topology_preview=topology.to_dict(),
            understanding=understanding or {},
            why_delegate=why,
            what_orchestrator_keeps=list(_ORCHESTRATOR_KEEPS),
            what_gets_delegated=list(_GETS_DELEGATED),
        )

        self._proposals[proposal.proposal_id] = proposal
        self._persist_proposal(proposal)
        return proposal

    def approve_proposal(self, proposal_id: str) -> DelegationMission | None:
        """Operator approves → mission created → enters queue."""
        proposal = self._proposals.get(proposal_id)
        if not proposal or proposal.status != "pending":
            return None

        proposal.status = "approved"
        proposal.decided_at = time.time()
        self._persist_proposal(proposal)

        mission = DelegationMission(
            title=proposal.proposed_title,
            operator_intent=proposal.operator_intent,
            clarified_intent=proposal.proposed_scope,
            projection=proposal.understanding.get("affected_projection", ""),
            repository=proposal.understanding.get("affected_repo", ""),
            priority=self._risk_to_priority(proposal.estimated_risk),
            risk_class=proposal.estimated_risk,
            required_capabilities=proposal.required_capabilities,
            required_specialists=[proposal.topology_preview.get("lead_role_contract", "")],
            topology_type=proposal.topology_preview.get("topology_type", ""),
            status=DelegationMissionStatus.QUEUED,
            proposal_id=proposal_id,
        )

        self._missions[mission.mission_id] = mission
        self._persist_mission(mission)
        return mission

    def reject_proposal(self, proposal_id: str, reason: str = "") -> DelegationProposal | None:
        proposal = self._proposals.get(proposal_id)
        if not proposal or proposal.status != "pending":
            return None

        proposal.status = "rejected"
        proposal.decided_at = time.time()
        if reason:
            proposal.understanding["rejection_reason"] = reason
        self._persist_proposal(proposal)
        return proposal

    # ── Queue management ─────────────────────────────────────────────

    def queue_status(self) -> dict[str, Any]:
        queued = [m for m in self._missions.values() if m.status == DelegationMissionStatus.QUEUED]
        active = [
            m
            for m in self._missions.values()
            if m.status
            in (
                DelegationMissionStatus.CLAIMED,
                DelegationMissionStatus.PLANNING,
                DelegationMissionStatus.WORK_PACKET_DRAFTED,
                DelegationMissionStatus.EXECUTING,
            )
        ]
        return {
            "queue_depth": len(queued),
            "active_count": len(active),
            "max_concurrent": self._max_concurrent,
            "queued_missions": [
                m.to_dict()
                for m in sorted(
                    queued,
                    key=lambda m: (
                        {"critical": 0, "high": 1, "normal": 2, "low": 3}.get(m.priority, 2),
                        m.created_at,
                    ),
                )
            ],
            "active_missions": [m.to_dict() for m in active],
            "nested_orchestrators": {k: v.to_dict() for k, v in self._nested_orchestrators.items()},
        }

    def claim_mission(self, mission_id: str) -> NestedOrchestratorState | None:
        """Spawn a nested orchestrator for this mission."""
        mission = self._missions.get(mission_id)
        if not mission or mission.status != DelegationMissionStatus.QUEUED:
            return None

        active_count = sum(
            1
            for m in self._missions.values()
            if m.status
            in (
                DelegationMissionStatus.CLAIMED,
                DelegationMissionStatus.PLANNING,
                DelegationMissionStatus.WORK_PACKET_DRAFTED,
            )
        )
        if active_count >= self._max_concurrent:
            logger.info("Delegation queue at capacity (%d/%d)", active_count, self._max_concurrent)
            return None

        nested = NestedOrchestratorState(mission_id=mission_id)
        mission.transition(DelegationMissionStatus.CLAIMED)
        mission.claimed_at = time.time()
        mission.nested_orchestrator_id = nested.orchestrator_id

        self._nested_orchestrators[mission_id] = nested
        self._persist_mission(mission)
        return nested

    def process_queue(self) -> list[str]:
        """Auto-claim queued missions up to max_concurrent."""
        claimed: list[str] = []
        queued = sorted(
            [m for m in self._missions.values() if m.status == DelegationMissionStatus.QUEUED],
            key=lambda m: (
                {"critical": 0, "high": 1, "normal": 2, "low": 3}.get(m.priority, 2),
                m.created_at,
            ),
        )
        for mission in queued:
            result = self.claim_mission(mission.mission_id)
            if result:
                claimed.append(mission.mission_id)
            else:
                break
        return claimed

    # ── Nested orchestrator lifecycle ────────────────────────────────

    def submit_work_packet_draft(
        self,
        mission_id: str,
        draft: dict[str, Any],
    ) -> dict[str, Any] | None:
        """Nested orchestrator submits WP draft. Does NOT execute."""
        mission = self._missions.get(mission_id)
        if not mission or mission.status not in (
            DelegationMissionStatus.CLAIMED,
            DelegationMissionStatus.PLANNING,
        ):
            return None

        nested = self._nested_orchestrators.get(mission_id)
        if nested:
            nested.work_packet_draft = draft
            nested.status = "drafting_wp"
            nested.progress_notes.append("Work packet draft submitted")

        if mission.status == DelegationMissionStatus.CLAIMED:
            mission.transition(DelegationMissionStatus.PLANNING)
        mission.transition(DelegationMissionStatus.WORK_PACKET_DRAFTED)
        self._persist_mission(mission)
        return {"mission_id": mission_id, "status": "work_packet_drafted", "draft": draft}

    def approve_work_packet(self, mission_id: str) -> dict[str, Any] | None:
        """Operator approves WP → mission moves toward execution."""
        mission = self._missions.get(mission_id)
        if not mission or mission.status != DelegationMissionStatus.WORK_PACKET_DRAFTED:
            return None

        mission.transition(DelegationMissionStatus.WORK_PACKET_APPROVED)
        self._persist_mission(mission)

        nested = self._nested_orchestrators.get(mission_id)
        if nested:
            nested.progress_notes.append("Work packet approved by operator")

        return {
            "mission_id": mission_id,
            "status": "work_packet_approved",
            "next": "Route to GovernedWorkRuntime for execution",
        }

    def start_execution(self, mission_id: str) -> dict[str, Any] | None:
        """Move approved mission to executing state."""
        mission = self._missions.get(mission_id)
        if not mission or mission.status != DelegationMissionStatus.WORK_PACKET_APPROVED:
            return None

        mission.transition(DelegationMissionStatus.EXECUTING)
        self._persist_mission(mission)
        return {"mission_id": mission_id, "status": "executing"}

    def complete_mission(
        self,
        mission_id: str,
        result: dict[str, Any] | None = None,
    ) -> DelegationMission | None:
        mission = self._missions.get(mission_id)
        if not mission or not mission.can_transition(DelegationMissionStatus.COMPLETED):
            return None

        mission.transition(DelegationMissionStatus.COMPLETED)
        mission.completed_at = time.time()
        if result:
            mission.metadata["result"] = result
        self._persist_mission(mission)

        nested = self._nested_orchestrators.pop(mission_id, None)
        if nested:
            nested.status = "completed"
            nested.completed_at = time.time()

        return mission

    def fail_mission(self, mission_id: str, reason: str = "") -> DelegationMission | None:
        mission = self._missions.get(mission_id)
        if not mission or not mission.can_transition(DelegationMissionStatus.FAILED):
            return None

        mission.transition(DelegationMissionStatus.FAILED)
        mission.completed_at = time.time()
        mission.metadata["failure_reason"] = reason
        self._persist_mission(mission)

        nested = self._nested_orchestrators.pop(mission_id, None)
        if nested:
            nested.status = "failed"
            nested.completed_at = time.time()

        return mission

    def cancel_mission(self, mission_id: str) -> DelegationMission | None:
        mission = self._missions.get(mission_id)
        if not mission or not mission.can_transition(DelegationMissionStatus.CANCELLED):
            return None

        mission.transition(DelegationMissionStatus.CANCELLED)
        mission.completed_at = time.time()
        self._persist_mission(mission)

        self._nested_orchestrators.pop(mission_id, None)
        return mission

    # ── Execution intent resolution ──────────────────────────────────

    def resolve_execution_intent(
        self,
        message: str,
        understanding: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """EXECUTION intents resolve to governed WP state. Never direct execution.

        Returns either a reference to an existing approved WP or a delegation
        proposal path to create one.
        """
        approved = [
            m
            for m in self._missions.values()
            if m.status == DelegationMissionStatus.WORK_PACKET_APPROVED
        ]
        if approved:
            best = approved[0]
            return {
                "resolution": "existing_work_packet",
                "mission_id": best.mission_id,
                "title": best.title,
                "action": "start_execution",
            }

        return {
            "resolution": "needs_work_packet",
            "action": "propose_delegation",
            "message": "No approved work packet found. Creating delegation proposal.",
        }

    # ── Query interface ──────────────────────────────────────────────

    def list_proposals(self, status: str | None = None, limit: int = 20) -> list[dict[str, Any]]:
        proposals = list(self._proposals.values())
        if status:
            proposals = [p for p in proposals if p.status == status]
        proposals.sort(key=lambda p: p.created_at, reverse=True)
        return [p.to_dict() for p in proposals[:limit]]

    def list_missions(self, status: str | None = None, limit: int = 20) -> list[dict[str, Any]]:
        missions = list(self._missions.values())
        if status:
            try:
                s = DelegationMissionStatus(status)
                missions = [m for m in missions if m.status == s]
            except ValueError:
                pass
        missions.sort(key=lambda m: m.created_at, reverse=True)
        return [m.to_dict() for m in missions[:limit]]

    def get_mission(self, mission_id: str) -> dict[str, Any] | None:
        m = self._missions.get(mission_id)
        return m.to_dict() if m else None

    def get_proposal(self, proposal_id: str) -> dict[str, Any] | None:
        p = self._proposals.get(proposal_id)
        return p.to_dict() if p else None

    def get_nested_orchestrator(self, mission_id: str) -> dict[str, Any] | None:
        n = self._nested_orchestrators.get(mission_id)
        return n.to_dict() if n else None

    def active_missions(self) -> list[dict[str, Any]]:
        active_states = {
            DelegationMissionStatus.QUEUED,
            DelegationMissionStatus.CLAIMED,
            DelegationMissionStatus.PLANNING,
            DelegationMissionStatus.WORK_PACKET_DRAFTED,
            DelegationMissionStatus.WORK_PACKET_APPROVED,
            DelegationMissionStatus.EXECUTING,
        }
        return [m.to_dict() for m in self._missions.values() if m.status in active_states]

    def summary(self) -> dict[str, Any]:
        total = len(self._missions)
        by_status: dict[str, int] = {}
        for m in self._missions.values():
            by_status[m.status.value] = by_status.get(m.status.value, 0) + 1

        pending_proposals = sum(1 for p in self._proposals.values() if p.status == "pending")

        return {
            "total_missions": total,
            "missions_by_status": by_status,
            "pending_proposals": pending_proposals,
            "total_proposals": len(self._proposals),
            "active_nested_orchestrators": len(self._nested_orchestrators),
            "queue": self.queue_status(),
        }

    # ── Helpers ───────────────────────────────────────────────────────

    @staticmethod
    def _generate_title(classification: Any) -> str:
        parts: list[str] = []
        if classification.work_type:
            parts.append(classification.work_type.replace("_", " ").title())
        if classification.entity:
            parts.append(f"for {classification.entity}")
        elif classification.domain:
            parts.append(f"in {classification.domain}")
        return " ".join(parts) if parts else "Delegation Mission"

    @staticmethod
    def _generate_scope(classification: Any) -> str:
        parts: list[str] = []
        if classification.domain:
            parts.append(f"Domain: {classification.domain}")
        if classification.work_type:
            parts.append(f"Type: {classification.work_type}")
        if classification.complexity:
            parts.append(f"Complexity: {classification.complexity}")
        return "; ".join(parts) if parts else "General work"

    @staticmethod
    def _delegation_reason(classification: Any, topology: Any) -> str:
        reasons: list[str] = []
        if classification.complexity in ("complex", "strategic"):
            reasons.append(f"{classification.complexity} work requires dedicated orchestration")
        if classification.risk_class in ("medium", "high"):
            reasons.append(f"{classification.risk_class}-risk work needs governed execution")
        if classification.parallel_workcells_needed:
            reasons.append("parallel execution benefits from dedicated coordination")
        if not reasons:
            reasons.append(
                "work packet construction delegated to maintain orchestrator availability"
            )
        return "; ".join(reasons)

    @staticmethod
    def _risk_to_priority(risk: str) -> str:
        return {"high": "high", "medium": "normal", "low": "low"}.get(risk, "normal")

    # ── Persistence ──────────────────────────────────────────────────

    def _persist_mission(self, mission: DelegationMission) -> None:
        try:
            with open(self._missions_path, "a") as f:
                f.write(json.dumps(mission.to_dict(), default=str, separators=(",", ":")) + "\n")
        except OSError as e:
            logger.error("Failed to persist mission %s: %s", mission.mission_id, e)

    def _persist_proposal(self, proposal: DelegationProposal) -> None:
        try:
            with open(self._proposals_path, "a") as f:
                f.write(json.dumps(proposal.to_dict(), default=str, separators=(",", ":")) + "\n")
        except OSError as e:
            logger.error("Failed to persist proposal %s: %s", proposal.proposal_id, e)

    def _load(self) -> None:
        self._missions = {}
        self._proposals = {}

        if self._missions_path.exists():
            try:
                seen: dict[str, dict[str, Any]] = {}
                with open(self._missions_path) as f:
                    for line in f:
                        line = line.strip()
                        if line:
                            d = json.loads(line)
                            mid = d.get("mission_id", "")
                            if mid:
                                seen[mid] = d
                for mid, d in seen.items():
                    self._missions[mid] = DelegationMission.from_dict(d)
            except (json.JSONDecodeError, OSError) as e:
                logger.error("Failed to load missions: %s", e)

        if self._proposals_path.exists():
            try:
                seen_p: dict[str, dict[str, Any]] = {}
                with open(self._proposals_path) as f:
                    for line in f:
                        line = line.strip()
                        if line:
                            d = json.loads(line)
                            pid = d.get("proposal_id", "")
                            if pid:
                                seen_p[pid] = d
                for pid, d in seen_p.items():
                    self._proposals[pid] = DelegationProposal.from_dict(d)
            except (json.JSONDecodeError, OSError) as e:
                logger.error("Failed to load proposals: %s", e)
