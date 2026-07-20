"""Template Registry — reusable executable structures from governed execution.

Stores verified, reusable action patterns extracted from successful
governed execution. Templates capture what worked, under what conditions,
with what agent type, and how to validate/rollback.

Promotion requires operator governance — no auto-promotion.

UMH substrate subsystem. Instance-agnostic.
"""

from __future__ import annotations

import hashlib
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


class TemplateStatus(str, Enum):
    RAW = "raw"
    CANDIDATE = "candidate"
    APPROVED = "approved"
    PROMOTED = "promoted"
    REJECTED = "rejected"
    SUPERSEDED = "superseded"
    DEPRECATED = "deprecated"


class TemplateType(str, Enum):
    CONTRADICTION_FIX = "contradiction_fix"
    API_CONTRACT_FIX = "api_contract_fix"
    COCKPIT_PANEL_FIX = "cockpit_panel_fix"
    READINESS_IMPROVEMENT = "readiness_improvement"
    GOVERNANCE_VALIDATION = "governance_validation"
    DEPLOYMENT_VALIDATION = "deployment_validation"
    OBSERVATION_ACCURACY_FIX = "observation_accuracy_fix"
    MAINTENANCE_ACTION = "maintenance_action"
    TEST_REPAIR = "test_repair"
    DOCUMENTATION_ALIGNMENT = "documentation_alignment"
    DEPENDENCY_GRAPH_FIX = "dependency_graph_fix"
    WORLD_MODEL_ACCURACY_FIX = "world_model_accuracy_fix"
    ROUTE_EXTRACTION_FIX = "route_extraction_fix"
    ENDPOINT_CONTRACT_FIX = "endpoint_contract_fix"
    EVIDENCE_ALIGNMENT_FIX = "evidence_alignment_fix"


class AgentType(str, Enum):
    DEVELOPER_AGENT = "developer_agent"
    AUDITOR_AGENT = "auditor_agent"
    SECURITY_AGENT = "security_agent"
    DEPLOYMENT_AGENT = "deployment_agent"
    OPERATOR_AGENT = "operator_agent"
    RESEARCHER_AGENT = "researcher_agent"


class CapabilityName(str, Enum):
    FILE_EDIT = "file_edit"
    CODE_SEARCH = "code_search"
    TEST_RUN = "test_run"
    ENDPOINT_VERIFY = "endpoint_verify"
    BROWSER_VERIFY = "browser_verify"
    GIT_COMMIT = "git_commit"
    ROLLBACK = "rollback"
    DEPENDENCY_ANALYSIS = "dependency_analysis"
    CONTRADICTION_DETECTION = "contradiction_detection"
    WORLD_MODEL_UPDATE = "world_model_update"
    API_CONTRACT_VALIDATION = "api_contract_validation"
    ROUTE_DISCOVERY = "route_discovery"
    EVIDENCE_VERIFICATION = "evidence_verification"


@dataclass
class TemplateEvidence:
    source: str
    detail: str
    confidence: float = 0.5
    observed_at: float = field(default_factory=time.time)

    def to_dict(self) -> dict[str, Any]:
        return {
            "source": self.source,
            "detail": self.detail,
            "confidence": self.confidence,
            "observed_at": self.observed_at,
        }


@dataclass
class TemplateStep:
    order: int
    description: str
    action: str
    requires_capability: str = ""
    risk_class: str = "low"
    governance_mode: str = "autonomous"
    verification: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "order": self.order,
            "description": self.description,
            "action": self.action,
            "requires_capability": self.requires_capability,
            "risk_class": self.risk_class,
            "governance_mode": self.governance_mode,
            "verification": self.verification,
        }


@dataclass
class TemplateValidation:
    description: str
    method: str = "assertion"
    timeout_seconds: float = 30.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "description": self.description,
            "method": self.method,
            "timeout_seconds": self.timeout_seconds,
        }


@dataclass
class TemplateRollback:
    description: str
    method: str = "revert"
    timeout_seconds: float = 30.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "description": self.description,
            "method": self.method,
            "timeout_seconds": self.timeout_seconds,
        }


@dataclass
class AgentCapabilityBinding:
    agent_type: AgentType
    capabilities: list[str] = field(default_factory=list)
    confidence: float = 0.5

    def to_dict(self) -> dict[str, Any]:
        return {
            "agent_type": self.agent_type.value,
            "capabilities": self.capabilities,
            "confidence": self.confidence,
        }


@dataclass
class TemplateCandidate:
    template_id: str = field(default_factory=lambda: f"tpl-{uuid4().hex[:8]}")
    template_type: TemplateType = TemplateType.CONTRADICTION_FIX
    trigger_conditions: list[str] = field(default_factory=list)
    required_context: list[str] = field(default_factory=list)
    required_capabilities: list[str] = field(default_factory=list)
    required_agent_type: AgentType = AgentType.DEVELOPER_AGENT
    reusable_steps: list[TemplateStep] = field(default_factory=list)
    dependencies: list[str] = field(default_factory=list)
    risk_class: str = "low"
    governance_mode: str = "autonomous"
    validation: TemplateValidation | None = None
    rollback: TemplateRollback | None = None
    evidence_requirements: list[str] = field(default_factory=list)
    known_failure_modes: list[str] = field(default_factory=list)
    expected_outcome: str = ""
    observed_success_count: int = 0
    observed_failure_count: int = 0
    confidence: float = 0.0
    source_outcome_ids: list[str] = field(default_factory=list)
    source_trial_ids: list[str] = field(default_factory=list)
    source_action_envelope_ids: list[str] = field(default_factory=list)
    evidence: list[TemplateEvidence] = field(default_factory=list)
    agent_capability_binding: AgentCapabilityBinding | None = None
    created_at: float = field(default_factory=time.time)
    status: TemplateStatus = TemplateStatus.RAW

    @property
    def total_observations(self) -> int:
        return self.observed_success_count + self.observed_failure_count

    @property
    def success_rate(self) -> float:
        if self.total_observations == 0:
            return 0.0
        return self.observed_success_count / self.total_observations

    def to_dict(self) -> dict[str, Any]:
        return {
            "template_id": self.template_id,
            "template_type": self.template_type.value,
            "trigger_conditions": self.trigger_conditions,
            "required_context": self.required_context,
            "required_capabilities": self.required_capabilities,
            "required_agent_type": self.required_agent_type.value,
            "reusable_steps": [s.to_dict() for s in self.reusable_steps],
            "dependencies": self.dependencies,
            "risk_class": self.risk_class,
            "governance_mode": self.governance_mode,
            "validation": self.validation.to_dict() if self.validation else None,
            "rollback": self.rollback.to_dict() if self.rollback else None,
            "evidence_requirements": self.evidence_requirements,
            "known_failure_modes": self.known_failure_modes,
            "expected_outcome": self.expected_outcome,
            "observed_success_count": self.observed_success_count,
            "observed_failure_count": self.observed_failure_count,
            "confidence": round(self.confidence, 3),
            "source_outcome_ids": self.source_outcome_ids,
            "source_trial_ids": self.source_trial_ids,
            "source_action_envelope_ids": self.source_action_envelope_ids,
            "evidence": [e.to_dict() for e in self.evidence],
            "agent_capability_binding": self.agent_capability_binding.to_dict()
            if self.agent_capability_binding
            else None,
            "created_at": self.created_at,
            "status": self.status.value,
        }


@dataclass
class TemplatePromotionDecision:
    template_id: str
    decision: TemplateStatus
    reason: str = ""
    decided_by: str = "system"
    decided_at: float = field(default_factory=time.time)

    def to_dict(self) -> dict[str, Any]:
        return {
            "template_id": self.template_id,
            "decision": self.decision.value,
            "reason": self.reason,
            "decided_by": self.decided_by,
            "decided_at": self.decided_at,
        }


# ---------------------------------------------------------------------------
# Action type → template type inference
# ---------------------------------------------------------------------------

_ACTION_TO_TEMPLATE_TYPE: dict[str, TemplateType] = {
    "resolve_missing_files": TemplateType.WORLD_MODEL_ACCURACY_FIX,
    "fix_deployment_state": TemplateType.DEPLOYMENT_VALIDATION,
    "run_contradiction_engine": TemplateType.CONTRADICTION_FIX,
    "verify_resolution": TemplateType.CONTRADICTION_FIX,
    "assess_readiness": TemplateType.READINESS_IMPROVEMENT,
    "identify_weakest_dimension": TemplateType.READINESS_IMPROVEMENT,
    "execute_improvement": TemplateType.READINESS_IMPROVEMENT,
    "identify_panel": TemplateType.COCKPIT_PANEL_FIX,
    "create_api_route": TemplateType.API_CONTRACT_FIX,
    "wire_bridge": TemplateType.ROUTE_EXTRACTION_FIX,
    "verify_panel": TemplateType.COCKPIT_PANEL_FIX,
    "check_readiness": TemplateType.READINESS_IMPROVEMENT,
    "run_probes": TemplateType.MAINTENANCE_ACTION,
    "execute_maintenance": TemplateType.MAINTENANCE_ACTION,
    "verify_health": TemplateType.MAINTENANCE_ACTION,
    "assess_state": TemplateType.OBSERVATION_ACCURACY_FIX,
    "plan_execution": TemplateType.GOVERNANCE_VALIDATION,
    "execute": TemplateType.MAINTENANCE_ACTION,
    "verify": TemplateType.EVIDENCE_ALIGNMENT_FIX,
    "documentation_fix": TemplateType.DOCUMENTATION_ALIGNMENT,
    "test_repair": TemplateType.TEST_REPAIR,
}


def _infer_template_type(action_type: str, description: str = "") -> TemplateType:
    if action_type in _ACTION_TO_TEMPLATE_TYPE:
        return _ACTION_TO_TEMPLATE_TYPE[action_type]
    desc = description.lower()
    if "contradiction" in desc or "mismatch" in desc:
        return TemplateType.CONTRADICTION_FIX
    if "readiness" in desc or "improve" in desc:
        return TemplateType.READINESS_IMPROVEMENT
    if "deploy" in desc:
        return TemplateType.DEPLOYMENT_VALIDATION
    if "panel" in desc or "cockpit" in desc:
        return TemplateType.COCKPIT_PANEL_FIX
    if "world model" in desc or "observation" in desc:
        return TemplateType.WORLD_MODEL_ACCURACY_FIX
    if "docstring" in desc or "documentation" in desc or "stale project name" in desc:
        return TemplateType.DOCUMENTATION_ALIGNMENT
    if "test" in desc:
        return TemplateType.TEST_REPAIR
    if "route" in desc or "endpoint" in desc:
        return TemplateType.ENDPOINT_CONTRACT_FIX
    if "dependency" in desc:
        return TemplateType.DEPENDENCY_GRAPH_FIX
    return TemplateType.MAINTENANCE_ACTION


def _infer_trigger_conditions(action_type: str, description: str) -> list[str]:
    conditions = []
    desc = description.lower()
    if "contradiction" in desc:
        conditions.append("contradiction engine reports gap or mismatch")
    if "missing" in desc or "not found" in desc:
        conditions.append("declared entity not found at expected location")
    if "readiness" in desc:
        conditions.append("readiness score below threshold")
    if "deploy" in desc:
        conditions.append("deployment state diverges from declared state")
    if "panel" in desc:
        conditions.append("cockpit panel returns error or missing data")
    if not conditions:
        conditions.append(f"action '{action_type}' required based on observed state")
    return conditions


class TemplateRegistry:
    """Registry of reusable execution templates extracted from governed outcomes."""

    def __init__(self, store_dir: str | None = None):
        if store_dir is None:
            from substrate.state.runtime_paths import runtime_state_dir

            store_dir = str(runtime_state_dir("organism", create=False) / "templates")
        self._store_dir = store_dir
        self._candidates_path = os.path.join(self._store_dir, "template_candidates.jsonl")
        self._templates_path = os.path.join(self._store_dir, "templates.jsonl")
        self._decisions_path = os.path.join(self._store_dir, "template_decisions.jsonl")
        self._candidates: dict[str, TemplateCandidate] = {}
        self._promoted: dict[str, TemplateCandidate] = {}
        self._decisions: list[TemplatePromotionDecision] = []
        self._load()

    def _load(self) -> None:
        self._candidates = self._load_from_path(self._candidates_path)
        self._promoted = self._load_from_path(self._templates_path)

    def _load_from_path(self, path: str) -> dict[str, TemplateCandidate]:
        templates: dict[str, TemplateCandidate] = {}
        if not os.path.isfile(path):
            return templates
        try:
            with open(path) as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    data = json.loads(line)
                    tpl = self._deserialize(data)
                    templates[tpl.template_id] = tpl
        except (json.JSONDecodeError, OSError) as e:
            logger.warning("Failed to load templates from %s: %s", path, e)
        return templates

    @staticmethod
    def _deserialize(data: dict[str, Any]) -> TemplateCandidate:
        steps = [TemplateStep(**s) for s in data.pop("reusable_steps", [])]
        evidence = [TemplateEvidence(**e) for e in data.pop("evidence", [])]
        validation = data.pop("validation", None)
        if validation and isinstance(validation, dict):
            validation = TemplateValidation(**validation)
        rollback = data.pop("rollback", None)
        if rollback and isinstance(rollback, dict):
            rollback = TemplateRollback(**rollback)
        binding = data.pop("agent_capability_binding", None)
        if binding and isinstance(binding, dict):
            binding = AgentCapabilityBinding(
                agent_type=AgentType(binding["agent_type"]),
                capabilities=binding.get("capabilities", []),
                confidence=binding.get("confidence", 0.5),
            )
        if "template_type" in data and isinstance(data["template_type"], str):
            data["template_type"] = TemplateType(data["template_type"])
        if "required_agent_type" in data and isinstance(data["required_agent_type"], str):
            data["required_agent_type"] = AgentType(data["required_agent_type"])
        if "status" in data and isinstance(data["status"], str):
            data["status"] = TemplateStatus(data["status"])
        return TemplateCandidate(
            **data,
            reusable_steps=steps,
            evidence=evidence,
            validation=validation,
            rollback=rollback,
            agent_capability_binding=binding,
        )

    def _persist(self, path: str, data: dict[str, Any]) -> None:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "a") as f:
            f.write(json.dumps(data, default=str) + "\n")

    def generate_candidate_from_outcome(self, outcome: dict[str, Any]) -> TemplateCandidate:
        """Extract a TemplateCandidate from a successful governed outcome."""
        action_type = outcome.get("action_type", "")
        description = outcome.get("description", "")
        tpl_type = _infer_template_type(action_type, description)
        trigger_conditions = _infer_trigger_conditions(action_type, description)

        capabilities_used = outcome.get("capabilities_used", [])
        if not capabilities_used:
            capabilities_used = ["code_search", "file_edit"]

        agent_type_str = outcome.get("agent_type", "developer_agent")
        try:
            agent_type = AgentType(agent_type_str)
        except ValueError:
            agent_type = AgentType.DEVELOPER_AGENT

        steps_data = outcome.get("steps", [])
        steps = []
        for i, s in enumerate(steps_data):
            if isinstance(s, dict):
                steps.append(
                    TemplateStep(
                        order=i,
                        description=s.get("description", s.get("desc", "")),
                        action=s.get("action", ""),
                        requires_capability=s.get("requires_capability", ""),
                        risk_class=s.get("risk_class", s.get("risk", "low")),
                        governance_mode=s.get("governance_mode", s.get("gov", "autonomous")),
                        verification=s.get("verification", s.get("verify", "")),
                    )
                )

        if not steps:
            steps = [
                TemplateStep(
                    order=0,
                    description="Verify precondition",
                    action="verify_precondition",
                    requires_capability="code_search",
                    verification="Precondition holds",
                ),
                TemplateStep(
                    order=1,
                    description=description or f"Execute {action_type}",
                    action=action_type,
                    requires_capability="file_edit",
                    verification="Action completed",
                ),
                TemplateStep(
                    order=2,
                    description="Validate result",
                    action="validate_result",
                    requires_capability="evidence_verification",
                    verification="Result verified",
                ),
            ]

        validation_desc = outcome.get("validation_strategy", "Re-run verification after action")
        rollback_desc = outcome.get("rollback_plan", "Revert to pre-execution state")

        evidence_items = []
        if outcome.get("evidence"):
            for ev in (
                outcome["evidence"]
                if isinstance(outcome["evidence"], list)
                else [outcome["evidence"]]
            ):
                evidence_items.append(
                    TemplateEvidence(
                        source="outcome",
                        detail=str(ev),
                        confidence=0.8,
                    )
                )

        candidate = TemplateCandidate(
            template_type=tpl_type,
            trigger_conditions=trigger_conditions,
            required_context=outcome.get(
                "required_context", ["world model entity metadata", "contradiction report"]
            ),
            required_capabilities=capabilities_used,
            required_agent_type=agent_type,
            reusable_steps=steps,
            risk_class=outcome.get("risk_class", "low"),
            governance_mode=outcome.get("governance_mode", "autonomous"),
            validation=TemplateValidation(description=validation_desc),
            rollback=TemplateRollback(description=rollback_desc),
            evidence_requirements=outcome.get(
                "evidence_requirements", ["contradiction report", "world model snapshot"]
            ),
            known_failure_modes=outcome.get("known_failure_modes", []),
            expected_outcome=outcome.get("expected_outcome", description),
            observed_success_count=1 if outcome.get("success", True) else 0,
            observed_failure_count=0 if outcome.get("success", True) else 1,
            confidence=0.6 if outcome.get("success", True) else 0.2,
            source_outcome_ids=[outcome.get("outcome_id", "")] if outcome.get("outcome_id") else [],
            source_trial_ids=[outcome.get("trial_id", "")] if outcome.get("trial_id") else [],
            source_action_envelope_ids=[outcome.get("envelope_id", "")]
            if outcome.get("envelope_id")
            else [],
            evidence=evidence_items,
            agent_capability_binding=AgentCapabilityBinding(
                agent_type=agent_type,
                capabilities=capabilities_used,
                confidence=0.7,
            ),
            status=TemplateStatus.RAW,
        )

        self._candidates[candidate.template_id] = candidate
        self._persist(self._candidates_path, candidate.to_dict())
        logger.info(
            "Generated template candidate %s from outcome (type=%s)",
            candidate.template_id,
            tpl_type.value,
        )
        return candidate

    def submit_candidate(self, candidate: TemplateCandidate) -> TemplateCandidate:
        """Submit a pre-built TemplateCandidate."""
        self._candidates[candidate.template_id] = candidate
        self._persist(self._candidates_path, candidate.to_dict())
        return candidate

    def get_template(self, template_id: str) -> TemplateCandidate | None:
        """Look up a template by ID across candidates and promoted stores."""
        return self._candidates.get(template_id) or self._promoted.get(template_id)

    def promote_to_candidate(self, template_id: str) -> bool:
        """Move from raw → candidate (ready for operator review)."""
        tpl = self._candidates.get(template_id)
        if not tpl:
            return False
        if tpl.status != TemplateStatus.RAW:
            return False
        tpl.status = TemplateStatus.CANDIDATE
        return True

    def approve(self, template_id: str, decided_by: str = "operator") -> bool:
        """Operator approves a candidate → approved status."""
        tpl = self._candidates.get(template_id)
        if not tpl:
            return False
        if tpl.status not in (TemplateStatus.RAW, TemplateStatus.CANDIDATE):
            return False
        tpl.status = TemplateStatus.APPROVED
        decision = TemplatePromotionDecision(
            template_id=template_id,
            decision=TemplateStatus.APPROVED,
            reason="Operator approved",
            decided_by=decided_by,
        )
        self._decisions.append(decision)
        self._persist(self._decisions_path, decision.to_dict())
        return True

    def promote(self, template_id: str, decided_by: str = "operator") -> bool:
        """Promote an approved template to the canonical templates store."""
        tpl = self._candidates.get(template_id)
        if not tpl:
            return False
        if tpl.status not in (
            TemplateStatus.APPROVED,
            TemplateStatus.CANDIDATE,
            TemplateStatus.RAW,
        ):
            return False
        tpl.status = TemplateStatus.PROMOTED
        self._promoted[template_id] = tpl
        self._persist(self._templates_path, tpl.to_dict())
        decision = TemplatePromotionDecision(
            template_id=template_id,
            decision=TemplateStatus.PROMOTED,
            reason="Promoted to canonical",
            decided_by=decided_by,
        )
        self._decisions.append(decision)
        self._persist(self._decisions_path, decision.to_dict())
        return True

    def reject(self, template_id: str, reason: str = "", decided_by: str = "operator") -> bool:
        """Reject a template candidate."""
        tpl = self._candidates.get(template_id)
        if not tpl:
            return False
        tpl.status = TemplateStatus.REJECTED
        decision = TemplatePromotionDecision(
            template_id=template_id,
            decision=TemplateStatus.REJECTED,
            reason=reason,
            decided_by=decided_by,
        )
        self._decisions.append(decision)
        self._persist(self._decisions_path, decision.to_dict())
        return True

    def supersede(self, old_id: str, new_id: str) -> bool:
        """Mark an old template as superseded by a new one."""
        old = self._candidates.get(old_id) or self._promoted.get(old_id)
        if not old:
            return False
        old.status = TemplateStatus.SUPERSEDED
        return True

    def deprecate(self, template_id: str) -> bool:
        """Deprecate a template."""
        tpl = self._candidates.get(template_id) or self._promoted.get(template_id)
        if not tpl:
            return False
        tpl.status = TemplateStatus.DEPRECATED
        return True

    def record_usage(self, template_id: str, success: bool) -> None:
        """Record a template usage result — updates confidence."""
        tpl = self._candidates.get(template_id) or self._promoted.get(template_id)
        if not tpl:
            return
        if success:
            tpl.observed_success_count += 1
        else:
            tpl.observed_failure_count += 1
        total = tpl.total_observations
        tpl.confidence = tpl.observed_success_count / total if total > 0 else 0.0

    def find_matching(self, action_type: str, description: str = "") -> list[TemplateCandidate]:
        """Find templates matching the given action context.

        Returns promoted templates first, then high-confidence candidates.
        """
        tpl_type = _infer_template_type(action_type, description)
        matches = []
        for tpl in self._promoted.values():
            if tpl.template_type == tpl_type and tpl.status == TemplateStatus.PROMOTED:
                matches.append(tpl)
        for tpl in self._candidates.values():
            if (
                tpl.template_type == tpl_type
                and tpl.status in (TemplateStatus.APPROVED, TemplateStatus.CANDIDATE)
                and tpl.confidence >= 0.5
            ):
                matches.append(tpl)
        matches.sort(
            key=lambda t: (t.status == TemplateStatus.PROMOTED, t.confidence), reverse=True
        )
        return matches

    def get_candidate(self, template_id: str) -> TemplateCandidate | None:
        return self._candidates.get(template_id)

    def get_promoted(self, template_id: str) -> TemplateCandidate | None:
        return self._promoted.get(template_id)

    def list_candidates(self, status: TemplateStatus | None = None) -> list[TemplateCandidate]:
        if status:
            return [t for t in self._candidates.values() if t.status == status]
        return list(self._candidates.values())

    def list_promoted(self) -> list[TemplateCandidate]:
        return [t for t in self._promoted.values() if t.status == TemplateStatus.PROMOTED]

    def pending_approvals(self) -> list[TemplateCandidate]:
        return [
            t
            for t in self._candidates.values()
            if t.status in (TemplateStatus.RAW, TemplateStatus.CANDIDATE)
        ]

    def summary(self) -> dict[str, Any]:
        status_counts: dict[str, int] = {}
        for t in self._candidates.values():
            status_counts[t.status.value] = status_counts.get(t.status.value, 0) + 1
        return {
            "total_candidates": len(self._candidates),
            "by_status": status_counts,
            "promoted_count": len(self.list_promoted()),
            "pending_approvals": len(self.pending_approvals()),
            "total_decisions": len(self._decisions),
        }

    def to_dict(self) -> dict[str, Any]:
        return {
            "summary": self.summary(),
            "candidates": [t.to_dict() for t in self._candidates.values()],
            "promoted": [t.to_dict() for t in self.list_promoted()],
            "pending_approvals": [t.to_dict() for t in self.pending_approvals()],
        }

    def to_safe_dict(self) -> dict[str, Any]:
        """HTTP-safe serialization."""
        candidates = []
        for t in list(self._candidates.values())[-20:]:
            candidates.append(
                {
                    "template_id": t.template_id,
                    "template_type": t.template_type.value,
                    "status": t.status.value,
                    "confidence": round(t.confidence, 3),
                    "observed_success_count": t.observed_success_count,
                    "observed_failure_count": t.observed_failure_count,
                    "created_at": t.created_at,
                }
            )
        promoted = []
        for t in self.list_promoted():
            promoted.append(
                {
                    "template_id": t.template_id,
                    "template_type": t.template_type.value,
                    "confidence": round(t.confidence, 3),
                    "observed_success_count": t.observed_success_count,
                }
            )
        return {
            "summary": self.summary(),
            "candidates": candidates,
            "promoted": promoted,
            "pending_approvals": len(self.pending_approvals()),
        }


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Task-shape template extraction (C33 D4 fix)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

_FILE_CATEGORY_RULES: list[tuple[str, str]] = [
    ("tests/", "test"),
    ("test_", "test"),
    ("transports/api/", "route"),
    ("routes/", "route"),
    ("adapters/", "adapter"),
    ("substrate/organism/", "substrate"),
    ("substrate/execution/", "execution"),
    ("transports/", "transport"),
    ("cockpit/", "cockpit"),
    ("migrations/", "migration"),
    ("scripts/", "script"),
    ("data/", "data"),
    (".json", "config"),
    (".yaml", "config"),
    (".yml", "config"),
    (".toml", "config"),
    (".md", "docs"),
]


@dataclass
class TaskShapeTemplate:
    """Reusable structural pattern extracted from completed governed cycles."""

    template_id: str = field(default_factory=lambda: f"tshape-{uuid4().hex[:8]}")
    task_shape: str = ""
    file_patterns: list[str] = field(default_factory=list)
    function_signatures: list[str] = field(default_factory=list)
    test_patterns: list[str] = field(default_factory=list)
    structural_hash: str = ""
    times_extracted: int = 0
    times_matched: int = 0
    success_rate: float = 1.0
    source_cycles: list[str] = field(default_factory=list)
    created_at: float = field(default_factory=time.time)

    def to_dict(self) -> dict[str, Any]:
        return {
            "template_id": self.template_id,
            "task_shape": self.task_shape,
            "file_patterns": self.file_patterns,
            "function_signatures": self.function_signatures,
            "test_patterns": self.test_patterns,
            "structural_hash": self.structural_hash,
            "times_extracted": self.times_extracted,
            "times_matched": self.times_matched,
            "success_rate": self.success_rate,
            "source_cycles": self.source_cycles,
            "created_at": self.created_at,
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> TaskShapeTemplate:
        fields = {k: v for k, v in d.items() if k in cls.__dataclass_fields__}
        return cls(**fields)


class TemplateExtractor:
    """Extracts reusable task-shape templates from completed governed cycles."""

    def __init__(self, store_path: str = "") -> None:
        self._store_path = store_path or os.path.join(
            _REPO_ROOT, "data", "umh", "compounding", "templates.jsonl"
        )
        self._templates: dict[str, TaskShapeTemplate] = {}
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
                        data = json.loads(line)
                        tpl = TaskShapeTemplate.from_dict(data)
                        self._templates[tpl.template_id] = tpl
                    except (json.JSONDecodeError, TypeError) as exc:
                        logger.debug("Skip malformed template line: %s", exc)
        except OSError as exc:
            logger.debug("Cannot read %s: %s", self._store_path, exc)

    def _persist(self, template: TaskShapeTemplate) -> None:
        os.makedirs(os.path.dirname(self._store_path), exist_ok=True)
        with open(self._store_path, "a") as f:
            f.write(json.dumps(template.to_dict(), default=str) + "\n")

    def _rewrite(self) -> None:
        os.makedirs(os.path.dirname(self._store_path), exist_ok=True)
        with open(self._store_path, "w") as f:
            for tpl in self._templates.values():
                f.write(json.dumps(tpl.to_dict(), default=str) + "\n")

    @staticmethod
    def _categorize_files(files: list[str]) -> list[str]:
        categories: list[str] = []
        for fp in files:
            fp_lower = fp.lower().replace("\\", "/")
            matched = False
            for pattern, cat in _FILE_CATEGORY_RULES:
                if pattern in fp_lower:
                    categories.append(cat)
                    matched = True
                    break
            if not matched:
                if fp_lower.endswith(".py"):
                    categories.append("python")
                elif fp_lower.endswith((".ts", ".tsx")):
                    categories.append("typescript")
                else:
                    categories.append("other")
        return sorted(categories)

    @staticmethod
    def _compute_structural_hash(categories: list[str]) -> str:
        canonical = "|".join(sorted(set(categories)))
        return hashlib.md5(canonical.encode()).hexdigest()[:12]

    @staticmethod
    def _similarity(a: list[str], b: list[str]) -> float:
        set_a = set(a)
        set_b = set(b)
        if not set_a and not set_b:
            return 1.0
        union = set_a | set_b
        if not union:
            return 0.0
        return len(set_a & set_b) / len(union)

    @staticmethod
    def _infer_task_shape(files: list[str], description: str) -> str:
        desc = description.lower()
        has_route = any("route" in f.lower() or "transports/api" in f.lower() for f in files)
        has_test = any("test" in f.lower() for f in files)
        has_adapter = any("adapter" in f.lower() for f in files)
        has_migration = any("migration" in f.lower() for f in files)

        if has_migration or "migration" in desc or "schema" in desc:
            return "schema_change"
        if has_adapter or "adapter" in desc:
            return "adapter_integration"
        if has_route and has_test:
            return "endpoint_addition"
        if "fix" in desc or "bug" in desc or "repair" in desc:
            return "bug_fix"
        if "refactor" in desc or "rename" in desc or "move" in desc:
            return "refactor"
        if has_route:
            return "endpoint_addition"
        return "general"

    def extract_from_cycle(
        self,
        cycle_id: str,
        files_changed: list[str],
        task_description: str,
    ) -> TaskShapeTemplate | None:
        if not files_changed:
            return None

        categories = self._categorize_files(files_changed)
        struct_hash = self._compute_structural_hash(categories)

        for tpl in self._templates.values():
            if tpl.structural_hash == struct_hash:
                tpl.times_matched += 1
                if cycle_id not in tpl.source_cycles:
                    tpl.source_cycles.append(cycle_id)
                self._rewrite()
                logger.info(
                    "Cycle %s matched existing template %s (hash=%s, matched=%d)",
                    cycle_id,
                    tpl.template_id,
                    struct_hash,
                    tpl.times_matched,
                )
                return tpl

        best_match: TaskShapeTemplate | None = None
        best_sim = 0.0
        for tpl in self._templates.values():
            existing_cats = self._categorize_files(tpl.file_patterns)
            sim = self._similarity(categories, existing_cats)
            if sim > best_sim:
                best_sim = sim
                best_match = tpl

        if best_match and best_sim >= 0.7:
            best_match.times_matched += 1
            if cycle_id not in best_match.source_cycles:
                best_match.source_cycles.append(cycle_id)
            self._rewrite()
            logger.info(
                "Cycle %s similar to template %s (sim=%.2f, matched=%d)",
                cycle_id,
                best_match.template_id,
                best_sim,
                best_match.times_matched,
            )
            return best_match

        task_shape = self._infer_task_shape(files_changed, task_description)
        test_patterns = [f for f in files_changed if "test" in f.lower()]
        new_tpl = TaskShapeTemplate(
            task_shape=task_shape,
            file_patterns=files_changed,
            test_patterns=test_patterns,
            structural_hash=struct_hash,
            times_extracted=1,
            source_cycles=[cycle_id],
        )
        self._templates[new_tpl.template_id] = new_tpl
        self._persist(new_tpl)
        logger.info(
            "Extracted new template %s from cycle %s (shape=%s, hash=%s)",
            new_tpl.template_id,
            cycle_id,
            task_shape,
            struct_hash,
        )
        return new_tpl

    def match_template(
        self,
        files_changed: list[str],
        task_description: str = "",
    ) -> TaskShapeTemplate | None:
        if not files_changed:
            return None

        categories = self._categorize_files(files_changed)
        struct_hash = self._compute_structural_hash(categories)

        for tpl in self._templates.values():
            if tpl.structural_hash == struct_hash:
                return tpl

        best_match: TaskShapeTemplate | None = None
        best_sim = 0.0
        for tpl in self._templates.values():
            existing_cats = self._categorize_files(tpl.file_patterns)
            sim = self._similarity(categories, existing_cats)
            if sim > best_sim:
                best_sim = sim
                best_match = tpl

        if best_match and best_sim >= 0.7:
            return best_match
        return None

    def list_templates(self, limit: int = 50) -> list[TaskShapeTemplate]:
        templates = sorted(
            self._templates.values(),
            key=lambda t: t.times_matched,
            reverse=True,
        )
        return templates[:limit]

    def get_template(self, template_id: str) -> TaskShapeTemplate | None:
        return self._templates.get(template_id)

    def summary(self) -> dict[str, Any]:
        by_shape: dict[str, int] = {}
        total_matched = 0
        for tpl in self._templates.values():
            by_shape[tpl.task_shape] = by_shape.get(tpl.task_shape, 0) + 1
            total_matched += tpl.times_matched
        return {
            "total_templates": len(self._templates),
            "by_shape": by_shape,
            "total_matches": total_matched,
        }
