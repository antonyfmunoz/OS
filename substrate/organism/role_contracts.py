"""Role Contracts + Capability Profiles — template-based role definitions.

Role contracts are templates, not permanent agents. Agent instances are
spawned from role contracts when work requires them.

Phase 11.1. UMH substrate subsystem. Instance-agnostic.
"""

from __future__ import annotations

import json
import logging
import os
import tempfile
import time
from dataclasses import dataclass, field
from typing import Any
from uuid import uuid4

logger = logging.getLogger(__name__)

_REPO_ROOT = os.environ.get("UMH_ROOT", "/opt/OS")


@dataclass
class CapabilityProfile:
    profile_id: str = field(default_factory=lambda: f"cap-{uuid4().hex[:8]}")
    role_id: str = ""
    capabilities: list[str] = field(default_factory=list)
    reliability_by_capability: dict[str, float] = field(default_factory=dict)
    known_failure_modes: list[str] = field(default_factory=list)
    successful_outcomes: int = 0
    failed_outcomes: int = 0
    average_confidence: float = 0.0
    last_updated: float = field(default_factory=time.time)

    def to_dict(self) -> dict[str, Any]:
        return {
            "profile_id": self.profile_id,
            "role_id": self.role_id,
            "capabilities": self.capabilities,
            "reliability_by_capability": self.reliability_by_capability,
            "known_failure_modes": self.known_failure_modes,
            "successful_outcomes": self.successful_outcomes,
            "failed_outcomes": self.failed_outcomes,
            "average_confidence": round(self.average_confidence, 4),
            "last_updated": self.last_updated,
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> CapabilityProfile:
        return cls(
            profile_id=d.get("profile_id", f"cap-{uuid4().hex[:8]}"),
            role_id=d.get("role_id", ""),
            capabilities=d.get("capabilities", []),
            reliability_by_capability=d.get("reliability_by_capability", {}),
            known_failure_modes=d.get("known_failure_modes", []),
            successful_outcomes=int(d.get("successful_outcomes", 0)),
            failed_outcomes=int(d.get("failed_outcomes", 0)),
            average_confidence=float(d.get("average_confidence", 0.0)),
            last_updated=float(d.get("last_updated", time.time())),
        )


@dataclass
class RoleContract:
    role_id: str = field(default_factory=lambda: f"role-{uuid4().hex[:8]}")
    name: str = ""
    description: str = ""
    owned_work_types: list[str] = field(default_factory=list)
    owned_domains: list[str] = field(default_factory=list)
    capability_profile: CapabilityProfile | None = None
    allowed_tools: list[str] = field(default_factory=list)
    knowledge_access_policy: str = ""
    spawn_permissions: list[str] = field(default_factory=list)
    approval_requirements: list[str] = field(default_factory=list)
    validation_responsibilities: list[str] = field(default_factory=list)
    reconvergence_responsibilities: list[str] = field(default_factory=list)
    escalation_rules: list[str] = field(default_factory=list)
    reliability_score: float = 0.0
    status: str = "active"
    version: int = 1

    def to_dict(self) -> dict[str, Any]:
        return {
            "role_id": self.role_id,
            "name": self.name,
            "description": self.description,
            "owned_work_types": self.owned_work_types,
            "owned_domains": self.owned_domains,
            "capability_profile": self.capability_profile.to_dict() if self.capability_profile else None,
            "allowed_tools": self.allowed_tools,
            "knowledge_access_policy": self.knowledge_access_policy,
            "spawn_permissions": self.spawn_permissions,
            "approval_requirements": self.approval_requirements,
            "validation_responsibilities": self.validation_responsibilities,
            "reconvergence_responsibilities": self.reconvergence_responsibilities,
            "escalation_rules": self.escalation_rules,
            "reliability_score": round(self.reliability_score, 4),
            "status": self.status,
            "version": self.version,
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> RoleContract:
        cap_raw = d.get("capability_profile")
        cap = CapabilityProfile.from_dict(cap_raw) if cap_raw else None
        return cls(
            role_id=d.get("role_id", f"role-{uuid4().hex[:8]}"),
            name=d.get("name", ""),
            description=d.get("description", ""),
            owned_work_types=d.get("owned_work_types", []),
            owned_domains=d.get("owned_domains", []),
            capability_profile=cap,
            allowed_tools=d.get("allowed_tools", []),
            knowledge_access_policy=d.get("knowledge_access_policy", ""),
            spawn_permissions=d.get("spawn_permissions", []),
            approval_requirements=d.get("approval_requirements", []),
            validation_responsibilities=d.get("validation_responsibilities", []),
            reconvergence_responsibilities=d.get("reconvergence_responsibilities", []),
            escalation_rules=d.get("escalation_rules", []),
            reliability_score=float(d.get("reliability_score", 0.0)),
            status=d.get("status", "active"),
            version=int(d.get("version", 1)),
        )


SEED_ROLE_CONTRACTS: list[dict[str, Any]] = [
    {
        "role_id": "role-orchestrator",
        "name": "orchestrator",
        "description": "Coordinates multi-workcell execution and reconvergence",
        "owned_work_types": ["coordination", "delegation", "reconvergence"],
        "owned_domains": ["self_build", "operations"],
        "spawn_permissions": ["workcell", "advisor_branch"],
        "escalation_rules": ["escalate_to_operator_on_medium_risk"],
    },
    {
        "role_id": "role-research-op",
        "name": "research_operator",
        "description": "Deep research, analysis, and knowledge synthesis",
        "owned_work_types": ["research", "analysis", "synthesis"],
        "owned_domains": ["research", "learning", "strategy"],
        "allowed_tools": ["web_search", "document_analysis"],
    },
    {
        "role_id": "role-impl-op",
        "name": "implementation_operator",
        "description": "Code implementation, testing, deployment",
        "owned_work_types": ["implementation", "testing", "deployment"],
        "owned_domains": ["self_build", "product"],
        "allowed_tools": ["code_edit", "test_runner", "deploy"],
        "validation_responsibilities": ["py_compile", "test_suite", "type_check"],
    },
    {
        "role_id": "role-verify-op",
        "name": "verification_operator",
        "description": "Production verification, audit, truth validation",
        "owned_work_types": ["verification", "audit", "validation"],
        "owned_domains": ["self_build", "operations"],
        "validation_responsibilities": ["production_truth_check", "regression_check"],
    },
    {
        "role_id": "role-strategy-op",
        "name": "strategy_operator",
        "description": "Strategic planning, roadmap, priority assessment",
        "owned_work_types": ["strategy", "planning", "priority_assessment"],
        "owned_domains": ["business", "strategy", "portfolio"],
    },
    {
        "role_id": "role-ops-op",
        "name": "operations_operator",
        "description": "Operational tasks, infrastructure, monitoring",
        "owned_work_types": ["operations", "infrastructure", "monitoring"],
        "owned_domains": ["operations", "admin"],
        "allowed_tools": ["deploy", "monitor", "config"],
    },
    {
        "role_id": "role-content-op",
        "name": "content_operator",
        "description": "Content creation, editing, publishing",
        "owned_work_types": ["content_creation", "editing", "publishing"],
        "owned_domains": ["content", "creative"],
    },
    {
        "role_id": "role-finance-op",
        "name": "finance_operator",
        "description": "Financial analysis, tracking, reporting",
        "owned_work_types": ["financial_analysis", "tracking", "reporting"],
        "owned_domains": ["finance"],
        "approval_requirements": ["operator_approval_required"],
    },
    {
        "role_id": "role-memory-op",
        "name": "memory_operator",
        "description": "Knowledge management, memory promotion, template governance",
        "owned_work_types": ["memory_management", "template_governance"],
        "owned_domains": ["self_build", "learning"],
    },
]


def persist_role_contracts(
    contracts: list[RoleContract],
    store_path: str | None = None,
) -> None:
    path = store_path or os.path.join(
        _REPO_ROOT, "data", "umh", "universal_work", "role_contracts.jsonl",
    )
    dir_path = os.path.dirname(path)
    os.makedirs(dir_path, exist_ok=True)
    fd, tmp_path = tempfile.mkstemp(dir=dir_path, suffix=".tmp")
    try:
        with os.fdopen(fd, "w") as f:
            for rc in contracts:
                f.write(json.dumps(rc.to_dict()) + "\n")
        os.replace(tmp_path, path)
    except BaseException:
        if os.path.exists(tmp_path):
            os.unlink(tmp_path)
        raise


def load_role_contracts(store_path: str | None = None) -> list[RoleContract]:
    path = store_path or os.path.join(
        _REPO_ROOT, "data", "umh", "universal_work", "role_contracts.jsonl",
    )
    if not os.path.exists(path):
        return []
    contracts: list[RoleContract] = []
    with open(path, "r") as f:
        for line_num, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                continue
            try:
                d = json.loads(line)
                contracts.append(RoleContract.from_dict(d))
            except (json.JSONDecodeError, KeyError, TypeError) as exc:
                raise ValueError(
                    f"Corrupt role contract at line {line_num}: {exc}"
                ) from exc
    return contracts
