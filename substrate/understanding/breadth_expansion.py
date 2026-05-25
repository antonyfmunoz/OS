"""Breadth Expansion Engine — step 9 of the 27-step spine.

Before narrowing to a specific capability, expand context across all
relevant domains. Cross-pollinate signals so the system considers
adjacent opportunities and risks that narrow focus would miss.

Example: "set up Stripe" should expand to:
  - Payment processing (primary)
  - Compliance/PCI requirements (governance)
  - Webhook integration (technical)
  - Revenue analytics (business)
  - Customer data handling (security)

Deterministic-first: keyword-based domain expansion using the
existing domain registry and reality model.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class DomainExpansion:
    domain: str
    relevance: float = 0.0
    reason: str = ""
    keywords_matched: list[str] = field(default_factory=list)


@dataclass
class BreadthResult:
    original_content: str
    primary_domains: list[str] = field(default_factory=list)
    expanded_domains: list[DomainExpansion] = field(default_factory=list)
    cross_domain_signals: list[str] = field(default_factory=list)
    total_domains: int = 0
    expansion_ratio: float = 1.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "primary_domains": self.primary_domains,
            "expanded_domains": [
                {
                    "domain": d.domain,
                    "relevance": round(d.relevance, 3),
                    "reason": d.reason,
                }
                for d in self.expanded_domains
            ],
            "cross_domain_signals": self.cross_domain_signals,
            "total_domains": self.total_domains,
            "expansion_ratio": round(self.expansion_ratio, 2),
        }


_DOMAIN_KEYWORDS: dict[str, list[str]] = {
    "execution": ["run", "execute", "command", "shell", "script", "process", "start", "stop", "deploy"],
    "governance": ["approve", "policy", "risk", "permission", "compliance", "audit", "review", "gate"],
    "integrations": ["api", "webhook", "sync", "connect", "integrate", "oauth", "token", "endpoint"],
    "security": ["credential", "secret", "encrypt", "auth", "permission", "access", "password", "key"],
    "data": ["database", "query", "schema", "migration", "store", "persist", "cache", "index"],
    "business": ["revenue", "customer", "pipeline", "deal", "lead", "sale", "conversion", "metric"],
    "content": ["write", "draft", "publish", "post", "article", "content", "copy", "message"],
    "infrastructure": ["docker", "container", "server", "deploy", "ci", "build", "monitor", "scale"],
    "communication": ["email", "discord", "slack", "notify", "broadcast", "message", "channel"],
    "analytics": ["track", "measure", "dashboard", "report", "metric", "insight", "trend", "analyze"],
    "design": ["ui", "layout", "component", "style", "visual", "interface", "mockup", "wireframe"],
    "knowledge": ["learn", "memory", "pattern", "observation", "mastery", "skill", "research"],
}

_CROSS_DOMAIN_RULES: list[tuple[str, str, str]] = [
    ("integrations", "security", "API integrations require credential management"),
    ("integrations", "governance", "External API calls need governance review"),
    ("data", "security", "Data operations involve access control"),
    ("data", "governance", "Schema changes require approval"),
    ("business", "analytics", "Business actions need measurement"),
    ("business", "communication", "Business outcomes should be communicated"),
    ("execution", "governance", "Execution requires governance gate"),
    ("execution", "infrastructure", "Execution needs environment context"),
    ("content", "business", "Content serves business objectives"),
    ("communication", "security", "External communication has data exposure risk"),
    ("infrastructure", "security", "Infrastructure changes affect security posture"),
    ("design", "analytics", "UI changes should be measured"),
]


class BreadthExpansionEngine:
    """Expand signal context across adjacent domains before narrowing."""

    def expand(
        self,
        content: str,
        existing_domains: list[str] | None = None,
    ) -> BreadthResult:
        """Expand a signal across all relevant domains."""
        result = BreadthResult(original_content=content)
        content_lower = content.lower()

        primary = self._detect_primary_domains(content_lower)
        result.primary_domains = primary

        expanded = self._expand_from_primary(primary, content_lower)
        result.expanded_domains = expanded

        result.cross_domain_signals = self._find_cross_signals(
            primary, [e.domain for e in expanded]
        )

        all_domains = set(primary) | {e.domain for e in expanded}
        if existing_domains:
            all_domains |= set(existing_domains)

        result.total_domains = len(all_domains)
        result.expansion_ratio = (
            len(all_domains) / len(primary) if primary else 1.0
        )

        return result

    def _detect_primary_domains(self, content_lower: str) -> list[str]:
        """Detect primary domains from content keywords."""
        scored: list[tuple[float, str]] = []

        for domain, keywords in _DOMAIN_KEYWORDS.items():
            matches = sum(1 for kw in keywords if kw in content_lower)
            if matches > 0:
                score = matches / len(keywords)
                scored.append((score, domain))

        scored.sort(key=lambda x: x[0], reverse=True)
        return [domain for _, domain in scored[:3]]

    def _expand_from_primary(
        self, primary: list[str], content_lower: str
    ) -> list[DomainExpansion]:
        """Expand to adjacent domains using cross-domain rules."""
        expanded: list[DomainExpansion] = []
        seen = set(primary)

        for source, target, reason in _CROSS_DOMAIN_RULES:
            if source in primary and target not in seen:
                keywords = _DOMAIN_KEYWORDS.get(target, [])
                matches = [kw for kw in keywords if kw in content_lower]
                relevance = 0.3 + (0.1 * len(matches))

                expanded.append(DomainExpansion(
                    domain=target,
                    relevance=min(1.0, relevance),
                    reason=reason,
                    keywords_matched=matches,
                ))
                seen.add(target)

            elif target in primary and source not in seen:
                keywords = _DOMAIN_KEYWORDS.get(source, [])
                matches = [kw for kw in keywords if kw in content_lower]
                relevance = 0.2 + (0.1 * len(matches))

                expanded.append(DomainExpansion(
                    domain=source,
                    relevance=min(1.0, relevance),
                    reason=f"Reverse: {reason}",
                    keywords_matched=matches,
                ))
                seen.add(source)

        expanded.sort(key=lambda x: x.relevance, reverse=True)
        return expanded

    def _find_cross_signals(
        self, primary: list[str], expanded: list[str]
    ) -> list[str]:
        """Generate cross-domain signals for downstream processing."""
        signals: list[str] = []
        all_domains = set(primary) | set(expanded)

        for source, target, reason in _CROSS_DOMAIN_RULES:
            if source in all_domains and target in all_domains:
                signals.append(reason)

        return signals
