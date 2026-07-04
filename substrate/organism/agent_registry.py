"""Agent Registry — agent types, capabilities, permissions, and routing.

Deterministic registry. Each agent type defines what it can do, which domains
it operates in, what tools it needs, and its risk limits.

Phase 3. UMH substrate subsystem. Instance-agnostic.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class AgentType:
    """Registered agent type with capabilities and governance."""

    agent_type_id: str = ""
    label: str = ""
    description: str = ""
    capabilities: list[str] = field(default_factory=list)
    permissions: list[str] = field(default_factory=list)
    allowed_domains: list[str] = field(default_factory=list)
    required_tools: list[str] = field(default_factory=list)
    max_risk_class: str = "medium"
    can_auto_execute: bool = False
    can_create_subpackets: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "agent_type_id": self.agent_type_id,
            "label": self.label,
            "description": self.description,
            "capabilities": self.capabilities,
            "permissions": self.permissions,
            "allowed_domains": self.allowed_domains,
            "required_tools": self.required_tools,
            "max_risk_class": self.max_risk_class,
            "can_auto_execute": self.can_auto_execute,
            "can_create_subpackets": self.can_create_subpackets,
        }

    def can_handle_domain(self, domain_id: str) -> bool:
        return not self.allowed_domains or domain_id in self.allowed_domains

    def can_handle_risk(self, risk_class: str) -> bool:
        # WP-P2-002: fail-closed on BOTH sides. Unknown REQUEST risk → strict
        # (HIGH) so it is rejected unless the ceiling truly permits high work.
        # Unknown CEILING → the most RESTRICTIVE band (NEGLIGIBLE) so a
        # misconfigured/unrecognized max_risk_class permits almost nothing,
        # rather than silently allowing everything. The two unknown defaults
        # point in opposite directions precisely so neither can fail open.
        from substrate.governance.risk_classes import (
            _KNOWN_RISK_NAMES,
            _SEVERITY_ORDER,
            SeverityClass,
            coerce_risk_class,
        )

        request_rank = _SEVERITY_ORDER[coerce_risk_class(risk_class)]
        ceiling = (self.max_risk_class or "").strip().lower()
        ceiling_class = (
            coerce_risk_class(ceiling) if ceiling in _KNOWN_RISK_NAMES else SeverityClass.NEGLIGIBLE
        )
        return request_rank <= _SEVERITY_ORDER[ceiling_class]


# ── Agent Type Definitions ────────────────────────────────────────────

_AGENTS: dict[str, AgentType] = {}


def _register(a: AgentType) -> None:
    _AGENTS[a.agent_type_id] = a


_register(
    AgentType(
        agent_type_id="builder",
        label="Builder",
        description="Implements code, creates artifacts, executes technical work",
        capabilities=["code", "test", "deploy", "refactor", "debug"],
        permissions=["read_code", "write_code", "run_tests", "create_branch"],
        allowed_domains=["engineering", "infrastructure"],
        required_tools=["claude_cli", "git", "pytest"],
        max_risk_class="high",
        can_auto_execute=True,
        can_create_subpackets=True,
    )
)

_register(
    AgentType(
        agent_type_id="researcher",
        label="Researcher",
        description="Investigates topics, gathers data, produces analysis",
        capabilities=["web_search", "document_analysis", "data_gathering", "summarization"],
        permissions=["read_code", "web_access", "file_read"],
        allowed_domains=[],
        required_tools=["web_search"],
        max_risk_class="low",
        can_auto_execute=True,
        can_create_subpackets=False,
    )
)

_register(
    AgentType(
        agent_type_id="reviewer",
        label="Reviewer",
        description="Reviews work output, identifies issues, provides feedback",
        capabilities=["code_review", "document_review", "quality_check"],
        permissions=["read_code", "comment"],
        allowed_domains=[],
        required_tools=[],
        max_risk_class="high",
        can_auto_execute=True,
        can_create_subpackets=False,
    )
)

_register(
    AgentType(
        agent_type_id="strategist",
        label="Strategist",
        description="Strategic planning, roadmaps, architecture, business strategy",
        capabilities=["planning", "analysis", "synthesis", "prioritization"],
        permissions=["read_code", "web_access", "file_read"],
        allowed_domains=[],
        required_tools=[],
        max_risk_class="high",
        can_auto_execute=False,
        can_create_subpackets=True,
    )
)

_register(
    AgentType(
        agent_type_id="operator",
        label="Operator",
        description="Executes operational tasks, admin, configuration, coordination",
        capabilities=["execute", "configure", "organize", "coordinate"],
        permissions=["read_code", "write_code", "run_commands"],
        allowed_domains=[],
        required_tools=[],
        max_risk_class="medium",
        can_auto_execute=True,
        can_create_subpackets=False,
    )
)

_register(
    AgentType(
        agent_type_id="qa",
        label="QA",
        description="Quality assurance, testing, validation, verification",
        capabilities=["test", "validate", "verify", "audit"],
        permissions=["read_code", "run_tests"],
        allowed_domains=["engineering", "infrastructure"],
        required_tools=["pytest"],
        max_risk_class="medium",
        can_auto_execute=True,
        can_create_subpackets=False,
    )
)

_register(
    AgentType(
        agent_type_id="finance_analyst",
        label="Finance Analyst",
        description="Financial analysis, budgets, forecasts, calculations",
        capabilities=["financial_modeling", "analysis", "forecasting", "reporting"],
        permissions=["file_read", "spreadsheet_access"],
        allowed_domains=["finance", "real_estate", "business_operations"],
        required_tools=[],
        max_risk_class="high",
        can_auto_execute=False,
        can_create_subpackets=False,
    )
)

_register(
    AgentType(
        agent_type_id="content_producer",
        label="Content Producer",
        description="Creates content — drafts, outlines, copy, scripts",
        capabilities=["writing", "editing", "outlining", "creative"],
        permissions=["file_read", "file_write"],
        allowed_domains=["content", "marketing", "music", "sales"],
        required_tools=[],
        max_risk_class="low",
        can_auto_execute=True,
        can_create_subpackets=False,
    )
)

_register(
    AgentType(
        agent_type_id="sales_assistant",
        label="Sales Assistant",
        description="Lead research, list building, sequence writing, CRM",
        capabilities=["lead_research", "list_building", "sequence_writing", "crm_update"],
        permissions=["web_access", "file_read", "file_write"],
        allowed_domains=["sales", "marketing", "business_operations"],
        required_tools=["web_search"],
        max_risk_class="medium",
        can_auto_execute=False,
        can_create_subpackets=True,
    )
)

_register(
    AgentType(
        agent_type_id="infrastructure_agent",
        label="Infrastructure Agent",
        description="Server ops, deployment, monitoring, infrastructure management",
        capabilities=["deploy", "monitor", "configure", "troubleshoot"],
        permissions=["read_code", "write_code", "run_commands", "deploy"],
        allowed_domains=["engineering", "infrastructure"],
        required_tools=["docker", "ssh"],
        max_risk_class="high",
        can_auto_execute=False,
        can_create_subpackets=False,
    )
)


class AgentRegistry:
    """Lookup and query agent types."""

    def get(self, agent_type_id: str) -> AgentType | None:
        return _AGENTS.get(agent_type_id)

    def all_agents(self) -> list[AgentType]:
        return list(_AGENTS.values())

    def agent_type_ids(self) -> list[str]:
        return list(_AGENTS.keys())

    def agents_for_domain(self, domain_id: str) -> list[AgentType]:
        return [a for a in _AGENTS.values() if a.can_handle_domain(domain_id)]

    def agents_for_risk(self, risk_class: str) -> list[AgentType]:
        return [a for a in _AGENTS.values() if a.can_handle_risk(risk_class)]

    def agents_with_capability(self, capability: str) -> list[AgentType]:
        return [a for a in _AGENTS.values() if capability in a.capabilities]

    def best_agent_for(self, domain_id: str, risk_class: str = "low") -> AgentType | None:
        candidates = [
            a
            for a in _AGENTS.values()
            if a.can_handle_domain(domain_id) and a.can_handle_risk(risk_class)
        ]
        if not candidates:
            return self.get("operator")
        return candidates[0]
