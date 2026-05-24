"""Execution Authority Engine v1 for the UMH substrate layer.

Determines whether a proposed action (from an ExecutionPlanningCandidate)
can become a governed WorkPacket for execution.

A plan may propose action, but only authority can permit execution.

Authority evaluation dimensions:
  - action type
  - capability requirement
  - adapter requirement
  - environment authority
  - worker/runtime availability
  - data sensitivity
  - reversibility
  - cost
  - external mutation risk
  - financial risk
  - credential risk
  - recursive autonomy risk
  - confidence threshold
  - proof requirement

UMH substrate subsystem.
"""

from __future__ import annotations

import hashlib
import json
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any


class AuthorityClass(str, Enum):
    DENY = "deny"
    READ_ONLY = "read_only"
    PROPOSE_ONLY = "propose_only"
    NOTIFY_EXECUTE = "notify_execute"
    APPROVE_EXECUTE = "approve_execute"
    SUPERVISED_EXECUTE = "supervised_execute"
    AUTONOMOUS_EXECUTE = "autonomous_execute"


AUTHORITY_CLASS_RANK: dict[AuthorityClass, int] = {
    AuthorityClass.DENY: 0,
    AuthorityClass.READ_ONLY: 1,
    AuthorityClass.PROPOSE_ONLY: 2,
    AuthorityClass.NOTIFY_EXECUTE: 3,
    AuthorityClass.APPROVE_EXECUTE: 4,
    AuthorityClass.SUPERVISED_EXECUTE: 5,
    AuthorityClass.AUTONOMOUS_EXECUTE: 6,
}


class RiskClass(str, Enum):
    NEGLIGIBLE = "negligible"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"
    FORBIDDEN = "forbidden"


class ApprovalRequirement(str, Enum):
    NONE = "none"
    SYSTEM_APPROVAL = "system_approval"
    FOUNDER_REVIEW = "founder_review"
    FOUNDER_APPROVAL = "founder_approval"
    EXPLICIT_GOVERNANCE = "explicit_governance"
    BLOCKED = "blocked"


STRUCTURALLY_DENIED_ACTIONS = frozenset(
    {
        "wallet_execution",
        "financial_execution",
        "credential_access",
        "destructive_file_operation",
        "broad_drive_ingestion",
        "autonomous_recursive_execution",
        "trade_placement",
        "money_allocation",
        "payment_processing",
        "token_extraction",
        "key_extraction",
        "database_drop",
        "production_deployment",
        "permission_escalation",
    }
)

DEFAULT_DENY_ACTIONS = frozenset(
    {
        "wallet_execution",
        "financial_execution",
        "credential_access",
        "trade_placement",
        "money_allocation",
        "payment_processing",
        "autonomous_recursive_execution",
    }
)

READ_ONLY_ACTIONS = frozenset(
    {
        "read_only_query",
        "metadata_read",
        "status_check",
        "health_check",
        "inventory_read",
        "configuration_read",
    }
)

SAFE_INGESTION_ACTIONS = frozenset(
    {
        "safe_doc_extraction",
        "safe_doc_normalization",
        "ingestion_candidate_creation",
        "memory_candidate_creation",
        "parity_validation",
    }
)

GUI_REQUIRING_ACTIONS = frozenset(
    {
        "browser_execution",
        "chrome_launch",
        "visible_gui_interaction",
        "computer_use_extraction",
        "desktop_automation",
    }
)

CONTAINER_ACTIONS = frozenset(
    {
        "container_execution",
        "container_spawn",
        "container_browser_automation",
        "container_shell_execution",
    }
)


@dataclass
class EnvironmentAuthority:
    """Authority granted by a specific environment."""

    environment_type: str
    can_own_gui: bool = False
    can_own_local_shell: bool = False
    can_own_remote_orchestration: bool = False
    can_execute_browser: bool = False
    can_execute_filesystem: bool = False
    can_own_container_orchestration: bool = False
    max_risk_class: RiskClass = RiskClass.LOW

    def permits_gui(self) -> bool:
        return self.can_own_gui and self.can_execute_browser

    def permits_container(self) -> bool:
        return self.can_own_container_orchestration

    def permits_action_risk(self, risk: RiskClass) -> bool:
        risk_rank = {
            RiskClass.NEGLIGIBLE: 0,
            RiskClass.LOW: 1,
            RiskClass.MEDIUM: 2,
            RiskClass.HIGH: 3,
            RiskClass.CRITICAL: 4,
            RiskClass.FORBIDDEN: 5,
        }
        return risk_rank.get(risk, 5) <= risk_rank.get(self.max_risk_class, 1)

    def to_dict(self) -> dict[str, Any]:
        return {
            "environment_type": self.environment_type,
            "can_own_gui": self.can_own_gui,
            "can_own_local_shell": self.can_own_local_shell,
            "can_own_remote_orchestration": self.can_own_remote_orchestration,
            "can_execute_browser": self.can_execute_browser,
            "can_execute_filesystem": self.can_execute_filesystem,
            "can_own_container_orchestration": self.can_own_container_orchestration,
            "max_risk_class": self.max_risk_class.value,
        }


@dataclass
class CapabilityAuthority:
    """Authority granted by an adapter's declared capabilities."""

    adapter_id: str
    capabilities: list[str] = field(default_factory=list)
    governance_constraints: list[str] = field(default_factory=list)
    is_configured: bool = False
    is_mature: bool = False

    def has_capability(self, capability: str) -> bool:
        return capability in self.capabilities

    def to_dict(self) -> dict[str, Any]:
        return {
            "adapter_id": self.adapter_id,
            "capabilities": self.capabilities,
            "governance_constraints": self.governance_constraints,
            "is_configured": self.is_configured,
            "is_mature": self.is_mature,
        }


@dataclass
class ExecutionAuthorityRequest:
    """Request to evaluate authority for a proposed action."""

    request_id: str
    action_type: str
    action_description: str
    source_plan_id: str = ""
    source_plan_hash: str = ""
    required_capability: str = ""
    required_adapter_id: str = ""
    required_environment_type: str = ""
    data_sensitivity: RiskClass = RiskClass.LOW
    reversibility: str = "reversible"
    estimated_cost: float = 0.0
    external_mutation: bool = False
    financial_risk: float = 0.0
    credential_risk: float = 0.0
    recursive_autonomy_risk: float = 0.0
    confidence: float = 1.0
    proof_requirements: list[str] = field(default_factory=list)
    trace_id: str = ""
    timestamp: str = ""

    def __post_init__(self) -> None:
        if not self.timestamp:
            self.timestamp = datetime.now(timezone.utc).isoformat()
        if not self.request_id:
            self.request_id = f"AUTH-REQ-{uuid.uuid4().hex[:8]}"

    def to_dict(self) -> dict[str, Any]:
        return {
            "request_id": self.request_id,
            "action_type": self.action_type,
            "action_description": self.action_description,
            "source_plan_id": self.source_plan_id,
            "source_plan_hash": self.source_plan_hash,
            "required_capability": self.required_capability,
            "required_adapter_id": self.required_adapter_id,
            "required_environment_type": self.required_environment_type,
            "data_sensitivity": self.data_sensitivity.value,
            "reversibility": self.reversibility,
            "estimated_cost": self.estimated_cost,
            "external_mutation": self.external_mutation,
            "financial_risk": self.financial_risk,
            "credential_risk": self.credential_risk,
            "recursive_autonomy_risk": self.recursive_autonomy_risk,
            "confidence": self.confidence,
            "proof_requirements": self.proof_requirements,
            "trace_id": self.trace_id,
            "timestamp": self.timestamp,
        }


@dataclass
class AuthorityDecision:
    """The engine's decision on whether to permit execution."""

    decision_id: str
    request_id: str
    authority_class: AuthorityClass
    risk_class: RiskClass
    approval_requirement: ApprovalRequirement
    workpacket_allowed: bool
    denial_reasons: list[str] = field(default_factory=list)
    conditions: list[str] = field(default_factory=list)
    required_proofs: list[str] = field(default_factory=list)
    environment_authority_met: bool = False
    capability_authority_met: bool = False
    confidence_met: bool = True
    decision_hash: str = ""
    trace_id: str = ""
    timestamp: str = ""

    def __post_init__(self) -> None:
        if not self.timestamp:
            self.timestamp = datetime.now(timezone.utc).isoformat()
        if not self.decision_id:
            self.decision_id = f"AUTH-DEC-{uuid.uuid4().hex[:8]}"

    def compute_decision_hash(self) -> str:
        payload = json.dumps(
            {
                "request_id": self.request_id,
                "authority_class": self.authority_class.value,
                "risk_class": self.risk_class.value,
                "approval_requirement": self.approval_requirement.value,
                "workpacket_allowed": self.workpacket_allowed,
                "denial_reasons": sorted(self.denial_reasons),
                "environment_authority_met": self.environment_authority_met,
                "capability_authority_met": self.capability_authority_met,
            },
            sort_keys=True,
        )
        self.decision_hash = hashlib.sha256(payload.encode()).hexdigest()
        return self.decision_hash

    def to_dict(self) -> dict[str, Any]:
        return {
            "decision_id": self.decision_id,
            "request_id": self.request_id,
            "authority_class": self.authority_class.value,
            "risk_class": self.risk_class.value,
            "approval_requirement": self.approval_requirement.value,
            "workpacket_allowed": self.workpacket_allowed,
            "denial_reasons": self.denial_reasons,
            "conditions": self.conditions,
            "required_proofs": self.required_proofs,
            "environment_authority_met": self.environment_authority_met,
            "capability_authority_met": self.capability_authority_met,
            "confidence_met": self.confidence_met,
            "decision_hash": self.decision_hash,
            "trace_id": self.trace_id,
            "timestamp": self.timestamp,
        }


@dataclass
class AuthorityProof:
    """Immutable proof that an authority decision was made."""

    proof_id: str
    decision_id: str
    request_id: str
    authority_class: str
    workpacket_allowed: bool
    decision_hash: str
    trace_id: str = ""
    timestamp: str = ""

    def __post_init__(self) -> None:
        if not self.timestamp:
            self.timestamp = datetime.now(timezone.utc).isoformat()
        if not self.proof_id:
            self.proof_id = f"AUTH-PROOF-{uuid.uuid4().hex[:8]}"

    def to_dict(self) -> dict[str, Any]:
        return {
            "proof_id": self.proof_id,
            "decision_id": self.decision_id,
            "request_id": self.request_id,
            "authority_class": self.authority_class,
            "workpacket_allowed": self.workpacket_allowed,
            "decision_hash": self.decision_hash,
            "trace_id": self.trace_id,
            "timestamp": self.timestamp,
        }


class ExecutionAuthorityEngine:
    """Evaluates whether proposed actions may become WorkPackets.

    Multi-dimensional authority evaluation:
    1. Structural denial check (hardcoded forbidden actions)
    2. Risk classification
    3. Environment authority check
    4. Capability authority check
    5. Confidence threshold check
    6. Proof requirement check
    7. Authority class determination
    8. Approval requirement determination
    """

    VERSION = "v1"
    CONFIDENCE_THRESHOLD = 0.7

    def __init__(
        self,
        environment_authorities: list[EnvironmentAuthority] | None = None,
        capability_authorities: list[CapabilityAuthority] | None = None,
        configured_overrides: dict[str, AuthorityClass] | None = None,
        proof_dir: Path | None = None,
    ) -> None:
        self._env_authorities: dict[str, EnvironmentAuthority] = {}
        if environment_authorities:
            for ea in environment_authorities:
                self._env_authorities[ea.environment_type] = ea

        self._cap_authorities: dict[str, CapabilityAuthority] = {}
        if capability_authorities:
            for ca in capability_authorities:
                self._cap_authorities[ca.adapter_id] = ca

        self._overrides = configured_overrides or {}
        self._proof_dir = proof_dir or Path("data/runtime/execution_authority_proofs")
        self._proof_dir.mkdir(parents=True, exist_ok=True)

    def evaluate(self, request: ExecutionAuthorityRequest) -> AuthorityDecision:
        denial_reasons: list[str] = []
        conditions: list[str] = []
        required_proofs: list[str] = []

        # 1. Structural denial
        if request.action_type in STRUCTURALLY_DENIED_ACTIONS:
            return self._deny(
                request,
                [f"structurally_denied_action: {request.action_type}"],
                RiskClass.FORBIDDEN,
            )

        if request.action_type in DEFAULT_DENY_ACTIONS:
            if request.action_type not in self._overrides:
                return self._deny(
                    request,
                    [f"default_deny_action: {request.action_type}"],
                    RiskClass.CRITICAL,
                )

        # 2. Risk classification
        risk_class = self._classify_risk(request)

        # 3. Environment authority
        env_met = True
        if request.required_environment_type:
            env_auth = self._env_authorities.get(request.required_environment_type)
            if not env_auth:
                denial_reasons.append(
                    f"missing_environment_authority: {request.required_environment_type}"
                )
                env_met = False
            elif request.action_type in GUI_REQUIRING_ACTIONS and not env_auth.permits_gui():
                denial_reasons.append(
                    f"environment_lacks_gui_authority: {request.required_environment_type}"
                )
                env_met = False
            elif not env_auth.permits_action_risk(risk_class):
                denial_reasons.append(
                    f"environment_risk_exceeds_max: {risk_class.value} > {env_auth.max_risk_class.value}"
                )
                env_met = False

        if request.action_type in GUI_REQUIRING_ACTIONS and not request.required_environment_type:
            denial_reasons.append("gui_action_requires_environment_specification")
            env_met = False

        if request.action_type in CONTAINER_ACTIONS:
            env_auth = self._env_authorities.get(request.required_environment_type, None)
            if env_auth and not env_auth.permits_container():
                denial_reasons.append(
                    f"environment_lacks_container_authority: {request.required_environment_type}"
                )
                env_met = False

        # 4. Capability authority
        cap_met = True
        if request.required_adapter_id:
            cap_auth = self._cap_authorities.get(request.required_adapter_id)
            if not cap_auth:
                denial_reasons.append(
                    f"missing_capability_authority: {request.required_adapter_id}"
                )
                cap_met = False
            elif not cap_auth.is_configured:
                denial_reasons.append(f"adapter_not_configured: {request.required_adapter_id}")
                cap_met = False
            elif request.required_capability and not cap_auth.has_capability(
                request.required_capability
            ):
                denial_reasons.append(f"adapter_lacks_capability: {request.required_capability}")
                cap_met = False

        # 5. Confidence check
        confidence_met = request.confidence >= self.CONFIDENCE_THRESHOLD

        if not confidence_met:
            denial_reasons.append(
                f"confidence_below_threshold: {request.confidence:.2f} < {self.CONFIDENCE_THRESHOLD}"
            )

        # 6. Proof requirements
        if request.proof_requirements:
            required_proofs.extend(request.proof_requirements)
            conditions.append(f"proofs_required_before_execution: {request.proof_requirements}")

        # 7. If any denial reasons accumulated, deny
        if denial_reasons:
            return AuthorityDecision(
                decision_id="",
                request_id=request.request_id,
                authority_class=AuthorityClass.DENY,
                risk_class=risk_class,
                approval_requirement=ApprovalRequirement.BLOCKED,
                workpacket_allowed=False,
                denial_reasons=denial_reasons,
                conditions=conditions,
                required_proofs=required_proofs,
                environment_authority_met=env_met,
                capability_authority_met=cap_met,
                confidence_met=confidence_met,
                trace_id=request.trace_id,
            )

        # 8. Determine authority class
        authority_class = self._determine_authority_class(request, risk_class)
        approval = self._determine_approval(authority_class, risk_class)
        workpacket_allowed = authority_class != AuthorityClass.DENY

        if authority_class == AuthorityClass.PROPOSE_ONLY:
            workpacket_allowed = False
            conditions.append("propose_only_no_execution")

        decision = AuthorityDecision(
            decision_id="",
            request_id=request.request_id,
            authority_class=authority_class,
            risk_class=risk_class,
            approval_requirement=approval,
            workpacket_allowed=workpacket_allowed,
            denial_reasons=denial_reasons,
            conditions=conditions,
            required_proofs=required_proofs,
            environment_authority_met=env_met,
            capability_authority_met=cap_met,
            confidence_met=confidence_met,
            trace_id=request.trace_id,
        )
        decision.compute_decision_hash()
        return decision

    def create_proof(self, decision: AuthorityDecision) -> AuthorityProof:
        proof = AuthorityProof(
            proof_id="",
            decision_id=decision.decision_id,
            request_id=decision.request_id,
            authority_class=decision.authority_class.value,
            workpacket_allowed=decision.workpacket_allowed,
            decision_hash=decision.decision_hash,
            trace_id=decision.trace_id,
        )
        path = self._proof_dir / f"{proof.proof_id}.json"
        with open(path, "w") as f:
            json.dump(proof.to_dict(), f, indent=2)
        return proof

    def evaluate_planning_candidate(
        self,
        plan_id: str,
        plan_hash: str,
        action_type: str,
        action_description: str,
        risk_envelope: dict[str, float] | None = None,
        required_capability: str = "",
        required_adapter_id: str = "",
        required_environment_type: str = "",
        proof_requirements: list[str] | None = None,
        trace_id: str = "",
    ) -> AuthorityDecision:
        """Convenience method: build request from planning candidate fields."""
        risk = risk_envelope or {}
        request = ExecutionAuthorityRequest(
            request_id="",
            action_type=action_type,
            action_description=action_description,
            source_plan_id=plan_id,
            source_plan_hash=plan_hash,
            required_capability=required_capability,
            required_adapter_id=required_adapter_id,
            required_environment_type=required_environment_type,
            financial_risk=risk.get("financial_risk", 0.0),
            credential_risk=risk.get("credential_risk", 0.0),
            recursive_autonomy_risk=risk.get("recursive_autonomy_risk", 0.0),
            data_sensitivity=RiskClass.LOW,
            proof_requirements=proof_requirements or [],
            trace_id=trace_id,
        )
        return self.evaluate(request)

    def _classify_risk(self, request: ExecutionAuthorityRequest) -> RiskClass:
        if request.action_type in STRUCTURALLY_DENIED_ACTIONS:
            return RiskClass.FORBIDDEN

        if request.financial_risk > 0.5 or request.credential_risk > 0.5:
            return RiskClass.CRITICAL

        if request.recursive_autonomy_risk > 0.3:
            return RiskClass.CRITICAL

        if request.external_mutation:
            return RiskClass.HIGH

        if request.estimated_cost > 100.0:
            return RiskClass.HIGH

        if request.data_sensitivity in (RiskClass.HIGH, RiskClass.CRITICAL):
            return RiskClass.HIGH

        if request.reversibility == "irreversible":
            return RiskClass.HIGH

        if request.action_type in READ_ONLY_ACTIONS:
            return RiskClass.NEGLIGIBLE

        if request.action_type in SAFE_INGESTION_ACTIONS:
            return RiskClass.LOW

        if request.action_type in GUI_REQUIRING_ACTIONS:
            return RiskClass.MEDIUM

        if request.action_type in CONTAINER_ACTIONS:
            return RiskClass.LOW

        return RiskClass.LOW

    def _determine_authority_class(
        self,
        request: ExecutionAuthorityRequest,
        risk_class: RiskClass,
    ) -> AuthorityClass:
        if request.action_type in self._overrides:
            return self._overrides[request.action_type]

        if request.action_type in READ_ONLY_ACTIONS:
            return AuthorityClass.READ_ONLY

        if risk_class == RiskClass.FORBIDDEN:
            return AuthorityClass.DENY

        if risk_class == RiskClass.CRITICAL:
            return AuthorityClass.DENY

        if request.action_type in SAFE_INGESTION_ACTIONS:
            return AuthorityClass.APPROVE_EXECUTE

        if request.action_type in GUI_REQUIRING_ACTIONS:
            return AuthorityClass.SUPERVISED_EXECUTE

        if request.action_type in CONTAINER_ACTIONS:
            return AuthorityClass.APPROVE_EXECUTE

        if risk_class == RiskClass.HIGH:
            return AuthorityClass.APPROVE_EXECUTE

        if risk_class == RiskClass.MEDIUM:
            return AuthorityClass.NOTIFY_EXECUTE

        return AuthorityClass.NOTIFY_EXECUTE

    def _determine_approval(
        self,
        authority_class: AuthorityClass,
        risk_class: RiskClass,
    ) -> ApprovalRequirement:
        if authority_class == AuthorityClass.DENY:
            return ApprovalRequirement.BLOCKED

        if authority_class == AuthorityClass.READ_ONLY:
            return ApprovalRequirement.NONE

        if authority_class == AuthorityClass.PROPOSE_ONLY:
            return ApprovalRequirement.NONE

        if authority_class == AuthorityClass.SUPERVISED_EXECUTE:
            return ApprovalRequirement.FOUNDER_APPROVAL

        if authority_class == AuthorityClass.APPROVE_EXECUTE:
            if risk_class in (RiskClass.HIGH, RiskClass.CRITICAL):
                return ApprovalRequirement.FOUNDER_APPROVAL
            return ApprovalRequirement.SYSTEM_APPROVAL

        if authority_class == AuthorityClass.NOTIFY_EXECUTE:
            return ApprovalRequirement.SYSTEM_APPROVAL

        if authority_class == AuthorityClass.AUTONOMOUS_EXECUTE:
            return ApprovalRequirement.NONE

        return ApprovalRequirement.BLOCKED

    def _deny(
        self,
        request: ExecutionAuthorityRequest,
        reasons: list[str],
        risk_class: RiskClass,
    ) -> AuthorityDecision:
        decision = AuthorityDecision(
            decision_id="",
            request_id=request.request_id,
            authority_class=AuthorityClass.DENY,
            risk_class=risk_class,
            approval_requirement=ApprovalRequirement.BLOCKED,
            workpacket_allowed=False,
            denial_reasons=reasons,
            environment_authority_met=False,
            capability_authority_met=False,
            trace_id=request.trace_id,
        )
        decision.compute_decision_hash()
        return decision
