"""Intent Classifier — converts raw user intent into structured classification.

Deterministic classification using keyword/pattern matching. No LLM calls.
Domains are open-ended, not hardcoded to self-build only.

Phase 11.1. UMH substrate subsystem. Instance-agnostic.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)


DOMAINS = [
    "self_build", "business", "client_delivery", "content", "learning",
    "personal", "finance", "creative", "operations", "research", "admin",
    "portfolio", "product", "legal_risk", "relationship", "health", "strategy",
]

DOMAIN_KEYWORDS: dict[str, list[str]] = {
    "self_build": ["build", "code", "implement", "test", "deploy", "fix", "refactor", "module", "infrastructure", "substrate", "cockpit", "phase"],
    "business": ["launch", "offer", "service", "client", "revenue", "pricing", "proposal", "sales", "b2b", "b2c", "automation"],
    "client_delivery": ["client", "deliverable", "engagement", "project", "handoff"],
    "content": ["content", "post", "video", "write", "publish", "brand", "social", "newsletter"],
    "learning": ["learn", "study", "research", "read", "course", "deep dive", "understand", "explain"],
    "personal": ["personal", "life", "habit", "routine", "goal"],
    "finance": ["finance", "budget", "tax", "accounting", "expense", "revenue", "profit", "investment"],
    "creative": ["design", "art", "music", "fiction", "story", "creative"],
    "operations": ["ops", "infrastructure", "server", "deploy", "monitor", "maintain", "backup", "dns"],
    "research": ["research", "investigate", "analyze", "deep dive", "explore", "survey"],
    "admin": ["admin", "organize", "clean", "archive", "file", "config", "setup"],
    "portfolio": ["portfolio", "company", "entity", "venture", "acquisition"],
    "product": ["product", "feature", "ux", "ui", "dashboard", "panel", "saas", "app"],
    "legal_risk": ["legal", "compliance", "risk", "liability", "contract", "terms"],
    "relationship": ["relationship", "network", "partner", "mentor", "advisor"],
    "health": ["health", "fitness", "sleep", "nutrition", "workout"],
    "strategy": ["strategy", "roadmap", "plan", "vision", "north star", "priority", "milestone"],
}

WORK_TYPES = [
    "implementation", "research", "analysis", "planning", "content_creation",
    "deployment", "testing", "verification", "audit", "design", "financial_analysis",
    "coordination", "cleanup", "configuration", "monitoring",
]

WORK_TYPE_KEYWORDS: dict[str, list[str]] = {
    "implementation": ["build", "implement", "code", "create", "add", "develop", "write"],
    "research": ["research", "investigate", "explore", "deep dive", "study", "analyze"],
    "analysis": ["analyze", "assess", "evaluate", "review", "audit", "examine"],
    "planning": ["plan", "roadmap", "prepare", "design", "architect", "strategy"],
    "content_creation": ["write", "create content", "post", "publish", "record"],
    "deployment": ["deploy", "ship", "release", "launch", "push"],
    "testing": ["test", "verify", "validate", "check"],
    "verification": ["verify", "confirm", "audit", "validate", "prove"],
    "audit": ["audit", "review", "inspect", "check"],
    "design": ["design", "mockup", "wireframe", "ux", "ui"],
    "financial_analysis": ["budget", "forecast", "revenue", "expense", "profit"],
    "coordination": ["coordinate", "orchestrate", "manage", "organize"],
    "cleanup": ["clean", "remove", "delete", "archive", "organize", "tidy"],
    "configuration": ["configure", "setup", "config", "settings"],
    "monitoring": ["monitor", "watch", "track", "observe", "alert"],
}

_DEFAULT_ENTITY_PATTERNS: dict[str, list[str]] = {
    "UMH": ["umh", "universal meta", "metaharness"],
}


def _load_entity_patterns() -> dict[str, list[str]]:
    """Load entity patterns from config file or return defaults.

    Instance-specific entities (companies, products, people) are loaded
    at runtime from data/umh/config/entity_patterns.json, not hardcoded.
    """
    import json
    import os
    config_path = os.path.join(
        os.environ.get("UMH_ROOT", "/opt/OS"),
        "data", "umh", "config", "entity_patterns.json",
    )
    if os.path.exists(config_path):
        try:
            with open(config_path, "r") as f:
                loaded = json.load(f)
            if isinstance(loaded, dict):
                merged = dict(_DEFAULT_ENTITY_PATTERNS)
                merged.update(loaded)
                return merged
        except (json.JSONDecodeError, OSError):
            pass
    return dict(_DEFAULT_ENTITY_PATTERNS)


ENTITY_PATTERNS: dict[str, list[str]] = _load_entity_patterns()


def _load_entity_metadata() -> dict[str, dict[str, str]]:
    """Load entity metadata (type classification) from config."""
    import json
    import os
    config_path = os.path.join(
        os.environ.get("UMH_ROOT", "/opt/OS"),
        "data", "umh", "config", "entity_metadata.json",
    )
    if os.path.exists(config_path):
        try:
            with open(config_path, "r") as f:
                return json.load(f)
        except (json.JSONDecodeError, OSError):
            pass
    return {"UMH": {"type": "product"}}


ENTITY_METADATA: dict[str, dict[str, str]] = _load_entity_metadata()

RISK_KEYWORDS: dict[str, list[str]] = {
    "low": ["clean", "organize", "document", "test", "plan", "research", "analyze"],
    "medium": ["deploy", "migrate", "refactor", "restructure", "delete", "remove"],
    "high": ["production", "dns", "auth", "security", "credential", "payment"],
}


@dataclass
class IntentClassification:
    domain: str = ""
    subdomain: str = ""
    entity: str = ""
    company: str = ""
    project: str = ""
    product: str = ""
    work_type: str = ""
    desired_output: str = ""
    required_knowledge: list[str] = field(default_factory=list)
    required_executor_type: str = ""
    risk_class: str = "low"
    complexity: str = "simple"
    parallel_workcells_needed: bool = False
    human_action_required: bool = False
    approval_required: bool = False
    execution_possible: bool = True

    def to_dict(self) -> dict[str, Any]:
        return {
            "domain": self.domain,
            "subdomain": self.subdomain,
            "entity": self.entity,
            "company": self.company,
            "project": self.project,
            "product": self.product,
            "work_type": self.work_type,
            "desired_output": self.desired_output,
            "required_knowledge": self.required_knowledge,
            "required_executor_type": self.required_executor_type,
            "risk_class": self.risk_class,
            "complexity": self.complexity,
            "parallel_workcells_needed": self.parallel_workcells_needed,
            "human_action_required": self.human_action_required,
            "approval_required": self.approval_required,
            "execution_possible": self.execution_possible,
        }


class IntentClassifier:
    """Deterministic intent classifier using keyword matching."""

    def classify(self, intent: str) -> IntentClassification:
        lower = intent.lower()
        result = IntentClassification()

        result.domain = self._classify_domain(lower)
        result.subdomain = self._classify_subdomain(lower, result.domain)
        result.work_type = self._classify_work_type(lower)
        result.risk_class = self._classify_risk(lower)

        entity_info = self._extract_entities(lower)
        result.entity = entity_info.get("entity", "")
        result.company = entity_info.get("company", "")
        result.project = entity_info.get("project", "")
        result.product = entity_info.get("product", "")

        result.complexity = self._classify_complexity(lower)
        result.parallel_workcells_needed = result.complexity in ("complex", "strategic")
        result.human_action_required = self._needs_human(lower, result.risk_class)
        result.approval_required = result.risk_class in ("medium", "high") or result.human_action_required
        result.execution_possible = result.risk_class != "high"
        result.required_executor_type = self._map_executor_type(result.work_type)
        result.desired_output = self._infer_desired_output(result.work_type, result.domain)
        result.required_knowledge = self._infer_knowledge(result.domain, result.entity)

        return result

    def _classify_domain(self, text: str) -> str:
        scores: dict[str, int] = {}
        for domain, keywords in DOMAIN_KEYWORDS.items():
            score = sum(1 for kw in keywords if kw in text)
            if score > 0:
                scores[domain] = score
        if not scores:
            return "operations"
        return max(scores, key=scores.get)

    def _classify_subdomain(self, text: str, domain: str) -> str:
        if domain == "self_build":
            if "test" in text:
                return "testing"
            if "cockpit" in text or "panel" in text or "dashboard" in text:
                return "cockpit"
            if "api" in text or "route" in text:
                return "api"
            return "implementation"
        if domain == "business":
            if "offer" in text or "service" in text:
                return "offer_development"
            if "client" in text:
                return "client_acquisition"
            return "general"
        return "general"

    def _classify_work_type(self, text: str) -> str:
        scores: dict[str, int] = {}
        for wt, keywords in WORK_TYPE_KEYWORDS.items():
            score = sum(1 for kw in keywords if kw in text)
            if score > 0:
                scores[wt] = score
        if not scores:
            return "implementation"
        return max(scores, key=scores.get)

    def _classify_risk(self, text: str) -> str:
        for risk_level in ("high", "medium", "low"):
            for kw in RISK_KEYWORDS[risk_level]:
                if kw in text:
                    return risk_level
        return "low"

    def _extract_entities(self, text: str) -> dict[str, str]:
        result: dict[str, str] = {}
        for entity_name, patterns in ENTITY_PATTERNS.items():
            for pattern in patterns:
                if pattern in text:
                    entity_meta = ENTITY_METADATA.get(entity_name, {})
                    etype = entity_meta.get("type", "entity")
                    if etype == "company":
                        result["company"] = entity_name
                    elif etype == "product":
                        result["product"] = entity_name
                    elif etype == "project":
                        result["project"] = entity_name
                    result["entity"] = entity_name
                    break
        return result

    def _classify_complexity(self, text: str) -> str:
        complex_signals = ["and", "then", "also", "plus", "multiple", "all", "every", "across"]
        strategic_signals = ["strategy", "roadmap", "vision", "long-term", "architecture"]
        signal_count = sum(1 for s in complex_signals if s in text)
        if any(s in text for s in strategic_signals):
            return "strategic"
        if signal_count >= 2 or len(text) > 200:
            return "complex"
        return "simple"

    def _needs_human(self, text: str, risk_class: str) -> bool:
        human_keywords = ["legal", "tax", "accounting", "sign", "approve", "physical", "mail", "call", "meet"]
        if risk_class in ("medium", "high"):
            return True
        return any(kw in text for kw in human_keywords)

    def _map_executor_type(self, work_type: str) -> str:
        mapping = {
            "implementation": "implementation_operator",
            "research": "research_operator",
            "analysis": "research_operator",
            "planning": "strategy_operator",
            "content_creation": "content_operator",
            "deployment": "operations_operator",
            "testing": "verification_operator",
            "verification": "verification_operator",
            "audit": "verification_operator",
            "design": "content_operator",
            "financial_analysis": "finance_operator",
            "coordination": "orchestrator",
            "cleanup": "operations_operator",
            "configuration": "operations_operator",
            "monitoring": "operations_operator",
        }
        return mapping.get(work_type, "implementation_operator")

    def _infer_desired_output(self, work_type: str, domain: str) -> str:
        outputs = {
            "implementation": "Working code with tests",
            "research": "Research report with findings",
            "analysis": "Analysis document with recommendations",
            "planning": "Plan document with phases and milestones",
            "content_creation": "Published content",
            "deployment": "Deployed and verified service",
            "testing": "Test results and coverage report",
            "verification": "Verification report",
            "audit": "Audit report with findings",
            "design": "Design document or mockup",
            "financial_analysis": "Financial report",
            "coordination": "Coordination plan",
            "cleanup": "Clean codebase/environment",
            "configuration": "Updated configuration",
            "monitoring": "Monitoring dashboard or alerts",
        }
        return outputs.get(work_type, "Completed work")

    def _infer_knowledge(self, domain: str, entity: str) -> list[str]:
        knowledge: list[str] = []
        if domain == "self_build":
            knowledge.append("umh_architecture")
        if domain in ("business", "client_delivery"):
            knowledge.append("business_operations")
        if domain == "finance":
            knowledge.append("financial_management")
        if entity:
            knowledge.append(f"entity_{entity.lower().replace(' ', '_')}")
        return knowledge
