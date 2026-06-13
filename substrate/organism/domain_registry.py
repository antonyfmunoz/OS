"""Domain Registry — first-class domain definitions for the Empire WorkPacket Engine.

Each domain defines allowed actions, required proofs, default agents,
approval gates, risk classes, and validation methods. Deterministic lookup,
no LLM calls.

Phase 3. UMH substrate subsystem. Instance-agnostic.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class ProofRequirement:
    """What constitutes proof of completion for a domain."""

    proof_type: str = ""
    description: str = ""
    required: bool = True
    validation_command: str = ""


@dataclass
class DomainDefinition:
    """First-class domain with governance, proof, and routing metadata."""

    domain_id: str = ""
    label: str = ""
    description: str = ""
    allowed_actions: list[str] = field(default_factory=list)
    proof_requirements: list[ProofRequirement] = field(default_factory=list)
    default_agent_types: list[str] = field(default_factory=list)
    approval_gates: list[str] = field(default_factory=list)
    default_risk_class: str = "low"
    validation_methods: list[str] = field(default_factory=list)
    background_eligible: bool = True
    escalation_triggers: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "domain_id": self.domain_id,
            "label": self.label,
            "description": self.description,
            "allowed_actions": self.allowed_actions,
            "proof_requirements": [
                {"proof_type": p.proof_type, "description": p.description,
                 "required": p.required, "validation_command": p.validation_command}
                for p in self.proof_requirements
            ],
            "default_agent_types": self.default_agent_types,
            "approval_gates": self.approval_gates,
            "default_risk_class": self.default_risk_class,
            "validation_methods": self.validation_methods,
            "background_eligible": self.background_eligible,
            "escalation_triggers": self.escalation_triggers,
        }


# ── Domain Definitions ────────────────────────────────────────────────

_DOMAINS: dict[str, DomainDefinition] = {}


def _register(d: DomainDefinition) -> None:
    _DOMAINS[d.domain_id] = d


_register(DomainDefinition(
    domain_id="engineering",
    label="UMH / Engineering",
    description="Code, infrastructure, substrate, cockpit, deployment",
    allowed_actions=["implement", "test", "deploy", "refactor", "debug", "review"],
    proof_requirements=[
        ProofRequirement("tests", "Test suite passes", True, "python3 -m pytest"),
        ProofRequirement("diff", "Git diff of changes", True, "git diff HEAD~1"),
        ProofRequirement("commit", "Commit hash", True, "git log --oneline -1"),
        ProofRequirement("import_check", "Import verification", True,
                         "python3 -c \"import substrate\""),
    ],
    default_agent_types=["builder", "reviewer", "qa"],
    approval_gates=["automated_tests"],
    default_risk_class="medium",
    validation_methods=["pytest", "ruff", "typecheck", "import_check"],
    background_eligible=True,
    escalation_triggers=["production_deploy", "schema_migration", "data_loss_risk"],
))

_register(DomainDefinition(
    domain_id="business_operations",
    label="Business Operations",
    description="Offers, pricing, client acquisition, service delivery",
    allowed_actions=["research", "draft", "plan", "analyze", "review", "execute"],
    proof_requirements=[
        ProofRequirement("document", "Deliverable document or artifact", True),
        ProofRequirement("approval_status", "Operator approval recorded", True),
    ],
    default_agent_types=["strategist", "researcher", "operator"],
    approval_gates=["operator_review"],
    default_risk_class="medium",
    validation_methods=["document_exists", "approval_recorded"],
    background_eligible=True,
    escalation_triggers=["pricing_change", "new_client_commitment", "contract_signing"],
))

_register(DomainDefinition(
    domain_id="content",
    label="Content",
    description="Posts, videos, newsletters, brand content, social media",
    allowed_actions=["draft", "outline", "research", "write", "publish", "schedule"],
    proof_requirements=[
        ProofRequirement("draft", "Content draft produced", True),
        ProofRequirement("outline", "Content outline", False),
        ProofRequirement("source_notes", "Research/source material", False),
        ProofRequirement("approval_status", "Content approved for publish", True),
    ],
    default_agent_types=["content_producer", "researcher", "reviewer"],
    approval_gates=["content_review"],
    default_risk_class="low",
    validation_methods=["draft_exists", "approval_recorded"],
    background_eligible=True,
    escalation_triggers=["brand_risk", "legal_mention", "competitor_mention"],
))

_register(DomainDefinition(
    domain_id="sales",
    label="Sales",
    description="Lead generation, outbound sequences, CRM, campaigns",
    allowed_actions=["research", "build_list", "write_sequence", "schedule", "analyze"],
    proof_requirements=[
        ProofRequirement("lead_list", "Lead list with ICP match", True),
        ProofRequirement("sequence", "Outbound sequence drafted", True),
        ProofRequirement("campaign_metrics", "Campaign performance data", False),
    ],
    default_agent_types=["sales_assistant", "researcher", "content_producer"],
    approval_gates=["operator_review", "sequence_approval"],
    default_risk_class="medium",
    validation_methods=["list_exists", "sequence_exists", "approval_recorded"],
    background_eligible=True,
    escalation_triggers=["budget_spend", "mass_outbound", "pricing_commitment"],
))

_register(DomainDefinition(
    domain_id="marketing",
    label="Marketing",
    description="Brand strategy, campaigns, analytics, positioning",
    allowed_actions=["research", "plan", "draft", "analyze", "execute"],
    proof_requirements=[
        ProofRequirement("strategy_doc", "Marketing strategy document", True),
        ProofRequirement("campaign_plan", "Campaign plan with metrics", False),
        ProofRequirement("approval_status", "Marketing approved", True),
    ],
    default_agent_types=["strategist", "content_producer", "researcher"],
    approval_gates=["operator_review"],
    default_risk_class="low",
    validation_methods=["document_exists", "approval_recorded"],
    background_eligible=True,
    escalation_triggers=["budget_spend", "brand_risk"],
))

_register(DomainDefinition(
    domain_id="finance",
    label="Finance",
    description="Budgets, tax, accounting, expense tracking, investment",
    allowed_actions=["analyze", "calculate", "forecast", "report", "audit"],
    proof_requirements=[
        ProofRequirement("spreadsheet", "Financial spreadsheet or model", True),
        ProofRequirement("assumptions", "Assumptions documented", True),
        ProofRequirement("calculation_trace", "Calculation methodology", True),
    ],
    default_agent_types=["finance_analyst", "researcher"],
    approval_gates=["operator_review", "financial_review"],
    default_risk_class="high",
    validation_methods=["calculations_verified", "assumptions_documented"],
    background_eligible=False,
    escalation_triggers=["tax_filing", "large_expense", "investment_decision"],
))

_register(DomainDefinition(
    domain_id="real_estate",
    label="Real Estate",
    description="Property research, deals, contracts, portfolio management",
    allowed_actions=["research", "analyze", "plan", "review"],
    proof_requirements=[
        ProofRequirement("analysis", "Property/deal analysis", True),
        ProofRequirement("financials", "Financial projections", True),
    ],
    default_agent_types=["researcher", "finance_analyst", "strategist"],
    approval_gates=["operator_review", "financial_review"],
    default_risk_class="high",
    validation_methods=["analysis_complete", "financials_verified"],
    background_eligible=False,
    escalation_triggers=["contract_signing", "large_commitment"],
))

_register(DomainDefinition(
    domain_id="music",
    label="Music / Artist",
    description="Music production, releases, artist brand, distribution",
    allowed_actions=["create", "draft", "plan", "review", "publish"],
    proof_requirements=[
        ProofRequirement("artifact", "Creative artifact produced", True),
        ProofRequirement("approval_status", "Creative direction approved", True),
    ],
    default_agent_types=["content_producer", "researcher", "reviewer"],
    approval_gates=["creative_review"],
    default_risk_class="low",
    validation_methods=["artifact_exists", "approval_recorded"],
    background_eligible=True,
    escalation_triggers=["public_release", "brand_risk"],
))

_register(DomainDefinition(
    domain_id="clothing",
    label="Clothing / Product",
    description="Apparel design, production, supply chain, brand",
    allowed_actions=["research", "design", "plan", "source", "review"],
    proof_requirements=[
        ProofRequirement("design_doc", "Design specification", True),
        ProofRequirement("cost_analysis", "Cost and margin analysis", False),
    ],
    default_agent_types=["researcher", "strategist", "finance_analyst"],
    approval_gates=["operator_review"],
    default_risk_class="medium",
    validation_methods=["design_exists", "costs_documented"],
    background_eligible=True,
    escalation_triggers=["production_order", "supplier_commitment"],
))

_register(DomainDefinition(
    domain_id="personal",
    label="Personal / LifeOS",
    description="Personal goals, habits, routines, life optimization",
    allowed_actions=["plan", "track", "research", "review", "schedule"],
    proof_requirements=[
        ProofRequirement("plan", "Action plan or schedule", True),
    ],
    default_agent_types=["operator", "researcher"],
    approval_gates=[],
    default_risk_class="low",
    validation_methods=["plan_exists"],
    background_eligible=True,
    escalation_triggers=[],
))

_register(DomainDefinition(
    domain_id="research",
    label="Research",
    description="Deep dives, market analysis, competitor research, learning",
    allowed_actions=["research", "analyze", "summarize", "report"],
    proof_requirements=[
        ProofRequirement("report", "Research report or summary", True),
        ProofRequirement("sources", "Sources cited", True),
    ],
    default_agent_types=["researcher", "strategist"],
    approval_gates=[],
    default_risk_class="low",
    validation_methods=["report_exists", "sources_cited"],
    background_eligible=True,
    escalation_triggers=[],
))

_register(DomainDefinition(
    domain_id="admin",
    label="Admin",
    description="Organization, cleanup, filing, configuration, setup",
    allowed_actions=["organize", "configure", "clean", "archive", "setup"],
    proof_requirements=[
        ProofRequirement("completion_log", "Task completion log", True),
    ],
    default_agent_types=["operator"],
    approval_gates=[],
    default_risk_class="low",
    validation_methods=["task_completed"],
    background_eligible=True,
    escalation_triggers=[],
))

_register(DomainDefinition(
    domain_id="infrastructure",
    label="Vision / Infrastructure",
    description="Architecture, platform strategy, long-term technical vision",
    allowed_actions=["plan", "research", "design", "review", "implement"],
    proof_requirements=[
        ProofRequirement("design_doc", "Architecture or design document", True),
        ProofRequirement("implementation_plan", "Implementation plan", True),
    ],
    default_agent_types=["strategist", "builder", "reviewer"],
    approval_gates=["operator_review", "architecture_review"],
    default_risk_class="high",
    validation_methods=["design_exists", "plan_exists"],
    background_eligible=False,
    escalation_triggers=["production_impact", "breaking_change"],
))


# ── Mapping from IntentClassifier domains to registry domains ─────────

_CLASSIFIER_TO_REGISTRY: dict[str, str] = {
    "self_build": "engineering",
    "business": "business_operations",
    "client_delivery": "business_operations",
    "content": "content",
    "learning": "research",
    "personal": "personal",
    "finance": "finance",
    "creative": "music",
    "operations": "engineering",
    "research": "research",
    "admin": "admin",
    "portfolio": "business_operations",
    "product": "engineering",
    "legal_risk": "finance",
    "relationship": "business_operations",
    "health": "personal",
    "strategy": "infrastructure",
}


class DomainRegistry:
    """Lookup and query domain definitions."""

    def get(self, domain_id: str) -> DomainDefinition | None:
        if domain_id in _DOMAINS:
            return _DOMAINS[domain_id]
        mapped = _CLASSIFIER_TO_REGISTRY.get(domain_id)
        if mapped:
            return _DOMAINS.get(mapped)
        return None

    def resolve_id(self, classifier_domain: str) -> str:
        return _CLASSIFIER_TO_REGISTRY.get(classifier_domain, classifier_domain)

    def all_domains(self) -> list[DomainDefinition]:
        return list(_DOMAINS.values())

    def domain_ids(self) -> list[str]:
        return list(_DOMAINS.keys())

    def get_proof_requirements(self, domain_id: str) -> list[ProofRequirement]:
        d = self.get(domain_id)
        return d.proof_requirements if d else []

    def get_default_agents(self, domain_id: str) -> list[str]:
        d = self.get(domain_id)
        return d.default_agent_types if d else []

    def is_background_eligible(self, domain_id: str) -> bool:
        d = self.get(domain_id)
        return d.background_eligible if d else True

    def get_approval_gates(self, domain_id: str) -> list[str]:
        d = self.get(domain_id)
        return d.approval_gates if d else []
