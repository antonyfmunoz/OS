"""DomainAdapter — pure mapping layer between real-world domains and the meta-harness.

Translates domain-specific metrics into Observations and abstract actions
into concrete ActionPlans. Stateless, deterministic, no side effects.

The meta-harness operates on abstract signals (confidence, risk, exploration).
The real world speaks in revenue, leads, sleep hours, views. This module
bridges the gap with rule-based mapping tables.

Usage::

    from umh.runtime_engine.domain_adapter import adapt_input, adapt_output, DomainType

    observations = adapt_input({
        "domain": "business",
        "metrics": {"revenue": 5000, "leads": 12, "churn_rate": 0.08},
        "entity_id": "lyfe_institute",
    })

    plan = adapt_output(decision_output, domain=DomainType.BUSINESS)
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from enum import Enum

from umh.world.types import Observation


# ─── Domain types ─────────────────────────────────────────────────


class DomainType(Enum):
    BUSINESS = "business"
    CREATOR = "creator"
    LIFE = "life"
    FINANCE = "finance"


# ─── Metric mapping tables ────────────────────────────────────────
# Each entry: metric_name → (signal_type, confidence, normalization)
#
# signal_type: what the Observation.signal_type field becomes
# base_confidence: default confidence for this metric (overridable)
# normalizer: function to normalize raw value to a comparable scale


@dataclass(frozen=True)
class MetricMapping:
    """Rule for translating one domain metric into an Observation."""

    signal_type: str
    base_confidence: float
    unit: str
    direction: str  # "up_good", "down_good", "neutral"

    def normalize(self, value: float | int) -> float:
        return float(value)


# ─── Business domain ──────────────────────────────────────────────

_BUSINESS_METRICS: dict[str, MetricMapping] = {
    "revenue": MetricMapping(
        signal_type="financial_revenue",
        base_confidence=0.95,
        unit="usd",
        direction="up_good",
    ),
    "mrr": MetricMapping(
        signal_type="financial_mrr",
        base_confidence=0.95,
        unit="usd",
        direction="up_good",
    ),
    "leads": MetricMapping(
        signal_type="pipeline_leads",
        base_confidence=0.9,
        unit="count",
        direction="up_good",
    ),
    "leads_contacted": MetricMapping(
        signal_type="pipeline_outreach",
        base_confidence=0.9,
        unit="count",
        direction="up_good",
    ),
    "replies": MetricMapping(
        signal_type="pipeline_replies",
        base_confidence=0.85,
        unit="count",
        direction="up_good",
    ),
    "meetings_booked": MetricMapping(
        signal_type="pipeline_meetings",
        base_confidence=0.9,
        unit="count",
        direction="up_good",
    ),
    "deals_closed": MetricMapping(
        signal_type="pipeline_closed",
        base_confidence=0.95,
        unit="count",
        direction="up_good",
    ),
    "churn_rate": MetricMapping(
        signal_type="retention_churn",
        base_confidence=0.85,
        unit="ratio",
        direction="down_good",
    ),
    "conversion_rate": MetricMapping(
        signal_type="pipeline_conversion",
        base_confidence=0.85,
        unit="ratio",
        direction="up_good",
    ),
    "cac": MetricMapping(
        signal_type="financial_cac",
        base_confidence=0.8,
        unit="usd",
        direction="down_good",
    ),
    "ltv": MetricMapping(
        signal_type="financial_ltv",
        base_confidence=0.8,
        unit="usd",
        direction="up_good",
    ),
    "burn_rate": MetricMapping(
        signal_type="financial_burn",
        base_confidence=0.9,
        unit="usd",
        direction="down_good",
    ),
    "nps": MetricMapping(
        signal_type="sentiment_nps",
        base_confidence=0.75,
        unit="score",
        direction="up_good",
    ),
}

# ─── Creator domain ──────────────────────────────────────────────

_CREATOR_METRICS: dict[str, MetricMapping] = {
    "views": MetricMapping(
        signal_type="content_views",
        base_confidence=0.9,
        unit="count",
        direction="up_good",
    ),
    "impressions": MetricMapping(
        signal_type="content_impressions",
        base_confidence=0.85,
        unit="count",
        direction="up_good",
    ),
    "engagement_rate": MetricMapping(
        signal_type="content_engagement",
        base_confidence=0.8,
        unit="ratio",
        direction="up_good",
    ),
    "followers": MetricMapping(
        signal_type="audience_followers",
        base_confidence=0.9,
        unit="count",
        direction="up_good",
    ),
    "follower_growth": MetricMapping(
        signal_type="audience_growth",
        base_confidence=0.8,
        unit="ratio",
        direction="up_good",
    ),
    "shares": MetricMapping(
        signal_type="content_shares",
        base_confidence=0.85,
        unit="count",
        direction="up_good",
    ),
    "comments": MetricMapping(
        signal_type="content_comments",
        base_confidence=0.8,
        unit="count",
        direction="up_good",
    ),
    "saves": MetricMapping(
        signal_type="content_saves",
        base_confidence=0.85,
        unit="count",
        direction="up_good",
    ),
    "watch_time": MetricMapping(
        signal_type="content_watch_time",
        base_confidence=0.85,
        unit="seconds",
        direction="up_good",
    ),
    "click_through_rate": MetricMapping(
        signal_type="content_ctr",
        base_confidence=0.8,
        unit="ratio",
        direction="up_good",
    ),
}

# ─── Life domain ──────────────────────────────────────────────────

_LIFE_METRICS: dict[str, MetricMapping] = {
    "sleep_hours": MetricMapping(
        signal_type="health_sleep",
        base_confidence=0.85,
        unit="hours",
        direction="up_good",
    ),
    "sleep_quality": MetricMapping(
        signal_type="health_sleep_quality",
        base_confidence=0.7,
        unit="score",
        direction="up_good",
    ),
    "energy": MetricMapping(
        signal_type="health_energy",
        base_confidence=0.7,
        unit="score",
        direction="up_good",
    ),
    "stress": MetricMapping(
        signal_type="health_stress",
        base_confidence=0.7,
        unit="score",
        direction="down_good",
    ),
    "exercise_minutes": MetricMapping(
        signal_type="health_exercise",
        base_confidence=0.85,
        unit="minutes",
        direction="up_good",
    ),
    "focus_hours": MetricMapping(
        signal_type="productivity_focus",
        base_confidence=0.8,
        unit="hours",
        direction="up_good",
    ),
    "tasks_completed": MetricMapping(
        signal_type="productivity_tasks",
        base_confidence=0.9,
        unit="count",
        direction="up_good",
    ),
    "mood": MetricMapping(
        signal_type="health_mood",
        base_confidence=0.65,
        unit="score",
        direction="up_good",
    ),
}

# ─── Finance domain ─────────────────────────────────��────────────

_FINANCE_METRICS: dict[str, MetricMapping] = {
    "cash_balance": MetricMapping(
        signal_type="financial_cash",
        base_confidence=0.95,
        unit="usd",
        direction="up_good",
    ),
    "monthly_expenses": MetricMapping(
        signal_type="financial_expenses",
        base_confidence=0.9,
        unit="usd",
        direction="down_good",
    ),
    "monthly_income": MetricMapping(
        signal_type="financial_income",
        base_confidence=0.9,
        unit="usd",
        direction="up_good",
    ),
    "savings_rate": MetricMapping(
        signal_type="financial_savings_rate",
        base_confidence=0.85,
        unit="ratio",
        direction="up_good",
    ),
    "debt": MetricMapping(
        signal_type="financial_debt",
        base_confidence=0.9,
        unit="usd",
        direction="down_good",
    ),
    "runway_months": MetricMapping(
        signal_type="financial_runway",
        base_confidence=0.85,
        unit="months",
        direction="up_good",
    ),
    "investment_return": MetricMapping(
        signal_type="financial_roi",
        base_confidence=0.75,
        unit="ratio",
        direction="up_good",
    ),
}

# ─── Domain registry ──────────────────────────────────────────────

_DOMAIN_METRIC_TABLES: dict[DomainType, dict[str, MetricMapping]] = {
    DomainType.BUSINESS: _BUSINESS_METRICS,
    DomainType.CREATOR: _CREATOR_METRICS,
    DomainType.LIFE: _LIFE_METRICS,
    DomainType.FINANCE: _FINANCE_METRICS,
}


def get_metric_table(domain: DomainType) -> dict[str, MetricMapping]:
    """Return the mapping table for a domain."""
    return _DOMAIN_METRIC_TABLES.get(domain, {})


def list_supported_metrics(domain: DomainType) -> tuple[str, ...]:
    """Return all recognized metric names for a domain."""
    return tuple(get_metric_table(domain).keys())


# ─── Action mapping tables ────────────────────────────────────────
# Maps abstract action keywords in the system output to concrete
# domain-specific instructions.


@dataclass(frozen=True)
class ActionMapping:
    """Rule for translating an abstract action keyword to a concrete instruction."""

    keyword: str
    instruction: str
    category: str  # "outreach", "content", "health", "financial", etc.
    priority: int  # 1 = highest


_BUSINESS_ACTIONS: tuple[ActionMapping, ...] = (
    ActionMapping(
        "increase exploration",
        "Test 3 new marketing channels this week.",
        "outreach",
        1,
    ),
    ActionMapping("explore", "Test 3 new marketing channels this week.", "outreach", 1),
    ActionMapping(
        "increase outreach", "Send 20 direct outreach messages today.", "outreach", 1
    ),
    ActionMapping("outreach", "Send 20 direct outreach messages today.", "outreach", 1),
    ActionMapping(
        "reduce risk",
        "Focus on proven outreach channels only. Pause experiments.",
        "outreach",
        2,
    ),
    ActionMapping(
        "optimize",
        "Review conversion rates. Double down on the highest-performing channel.",
        "optimization",
        2,
    ),
    ActionMapping(
        "stabilize",
        "Maintain current outreach volume. Fix any broken follow-up sequences.",
        "operations",
        3,
    ),
    ActionMapping(
        "increase revenue",
        "Raise prices 10% or add an upsell to the current offer.",
        "revenue",
        1,
    ),
    ActionMapping(
        "reduce churn",
        "Call every at-risk customer this week. Ask what's missing.",
        "retention",
        1,
    ),
    ActionMapping(
        "improve conversion",
        "A/B test the sales page headline and CTA.",
        "optimization",
        2,
    ),
    ActionMapping(
        "follow up",
        "Contact all leads who haven't replied in 48+ hours.",
        "outreach",
        1,
    ),
    ActionMapping(
        "close deals",
        "Move all warm leads to a call or proposal this week.",
        "sales",
        1,
    ),
    ActionMapping(
        "cut costs",
        "Cancel unused subscriptions and defer non-essential purchases.",
        "financial",
        2,
    ),
)

_CREATOR_ACTIONS: tuple[ActionMapping, ...] = (
    ActionMapping(
        "increase exploration",
        "Try 3 new content formats or topics this week.",
        "content",
        1,
    ),
    ActionMapping(
        "explore", "Try 3 new content formats or topics this week.", "content", 1
    ),
    ActionMapping(
        "increase engagement",
        "Post 2 conversation-starting pieces today. Respond to every comment.",
        "content",
        1,
    ),
    ActionMapping(
        "grow audience",
        "Collaborate with 2 creators in an adjacent niche.",
        "growth",
        1,
    ),
    ActionMapping(
        "optimize",
        "Analyze top 5 performing posts. Replicate the format.",
        "optimization",
        2,
    ),
    ActionMapping(
        "stabilize",
        "Maintain posting schedule. No format changes this week.",
        "content",
        3,
    ),
    ActionMapping(
        "reduce risk",
        "Stick to proven content formats. Avoid controversial topics.",
        "content",
        2,
    ),
    ActionMapping(
        "increase reach",
        "Post during peak hours. Use 3-5 trending hashtags per post.",
        "growth",
        1,
    ),
    ActionMapping(
        "improve quality", "Spend 2x editing time on the next 3 pieces.", "content", 2
    ),
)

_LIFE_ACTIONS: tuple[ActionMapping, ...] = (
    ActionMapping(
        "increase exploration", "Try 1 new habit or routine this week.", "habits", 1
    ),
    ActionMapping("explore", "Try 1 new habit or routine this week.", "habits", 1),
    ActionMapping(
        "optimize",
        "Track the 3 habits with the highest impact. Drop the lowest.",
        "optimization",
        2,
    ),
    ActionMapping(
        "stabilize", "No routine changes. Protect sleep and exercise.", "health", 3
    ),
    ActionMapping(
        "reduce risk", "Cut late-night work. Prioritize 8 hours sleep.", "health", 1
    ),
    ActionMapping(
        "reduce stress", "Block 30 minutes for decompression. No screens.", "health", 1
    ),
    ActionMapping(
        "increase energy",
        "Add a 20-minute walk after lunch. Hydrate to 3L/day.",
        "health",
        1,
    ),
    ActionMapping(
        "improve focus",
        "Use 90-minute deep work blocks. Phone in another room.",
        "productivity",
        1,
    ),
    ActionMapping(
        "improve sleep", "No caffeine after 2pm. Screen off by 10pm.", "health", 1
    ),
)

_FINANCE_ACTIONS: tuple[ActionMapping, ...] = (
    ActionMapping(
        "increase exploration",
        "Research 2 new income streams or investment vehicles.",
        "financial",
        1,
    ),
    ActionMapping(
        "explore",
        "Research 2 new income streams or investment vehicles.",
        "financial",
        1,
    ),
    ActionMapping(
        "optimize",
        "Review all recurring expenses. Eliminate subscriptions under $50/mo value.",
        "financial",
        2,
    ),
    ActionMapping(
        "stabilize",
        "Build 3-month emergency fund before any new investments.",
        "financial",
        3,
    ),
    ActionMapping(
        "reduce risk",
        "Move 20% of investments to lower-volatility assets.",
        "financial",
        2,
    ),
    ActionMapping(
        "reduce expenses",
        "Cut discretionary spending by 15% this month.",
        "financial",
        1,
    ),
    ActionMapping(
        "increase income",
        "Add 1 new revenue stream or raise rates 10%.",
        "financial",
        1,
    ),
    ActionMapping(
        "increase savings",
        "Automate 20% of income to savings before spending.",
        "financial",
        1,
    ),
)

_DOMAIN_ACTION_TABLES: dict[DomainType, tuple[ActionMapping, ...]] = {
    DomainType.BUSINESS: _BUSINESS_ACTIONS,
    DomainType.CREATOR: _CREATOR_ACTIONS,
    DomainType.LIFE: _LIFE_ACTIONS,
    DomainType.FINANCE: _FINANCE_ACTIONS,
}


# ─── Output types ─────────────────────────────────────────────────


@dataclass(frozen=True)
class ActionStep:
    """Single concrete action in an ActionPlan."""

    instruction: str
    category: str
    priority: int
    source_keyword: str

    def to_dict(self) -> dict:
        return {
            "instruction": self.instruction,
            "category": self.category,
            "priority": self.priority,
            "source_keyword": self.source_keyword,
        }


@dataclass(frozen=True)
class ActionPlan:
    """Concrete domain-specific plan derived from a DecisionOutput."""

    domain: str
    steps: tuple[ActionStep, ...]
    confidence: float
    risk_score: float
    raw_action: str
    unmapped_keywords: tuple[str, ...]

    def to_dict(self) -> dict:
        return {
            "domain": self.domain,
            "steps": [s.to_dict() for s in self.steps],
            "confidence": round(self.confidence, 4),
            "risk_score": round(self.risk_score, 4),
            "raw_action": self.raw_action,
            "unmapped_keywords": list(self.unmapped_keywords),
        }


@dataclass(frozen=True)
class AdaptedInput:
    """Result of adapting raw domain metrics into observations."""

    domain: str
    observations: tuple[Observation, ...]
    unmapped_metrics: tuple[str, ...]
    summary: str

    def to_dict(self) -> dict:
        return {
            "domain": self.domain,
            "observations": [o.to_dict() for o in self.observations],
            "unmapped_metrics": list(self.unmapped_metrics),
            "summary": self.summary,
        }


# ─── Input adapter ────────────────────────────────────────────────


def _resolve_domain(raw: str) -> DomainType | None:
    """Resolve a string domain name to DomainType. Case-insensitive."""
    normalized = raw.strip().lower()
    for dt in DomainType:
        if dt.value == normalized:
            return dt
    return None


def adapt_input(
    raw_input: dict,
    timestamp_turn: int = 0,
) -> AdaptedInput:
    """Translate domain-specific metrics into world-model Observations.

    Expected raw_input shape::

        {
            "domain": "business",
            "metrics": {"revenue": 5000, "leads": 12},
            "entity_id": "lyfe_institute",  # optional, defaults to domain name
            "confidence_overrides": {"revenue": 0.99},  # optional
        }

    Returns AdaptedInput with observations and any unmapped metric names.
    Pure function — no side effects.
    """
    domain_str = raw_input.get("domain", "")
    domain = _resolve_domain(domain_str)
    if domain is None:
        return AdaptedInput(
            domain=domain_str,
            observations=(),
            unmapped_metrics=tuple(raw_input.get("metrics", {}).keys()),
            summary=f"Unknown domain '{domain_str}'. No metrics mapped.",
        )

    metrics: dict = raw_input.get("metrics", {})
    entity_id: str = raw_input.get("entity_id", domain.value)
    confidence_overrides: dict = raw_input.get("confidence_overrides", {})
    table = get_metric_table(domain)

    observations: list[Observation] = []
    unmapped: list[str] = []

    for metric_name, value in metrics.items():
        mapping = table.get(metric_name)
        if mapping is None:
            unmapped.append(metric_name)
            continue

        if not isinstance(value, (int, float)):
            unmapped.append(metric_name)
            continue

        confidence = confidence_overrides.get(metric_name, mapping.base_confidence)
        confidence = max(0.0, min(1.0, float(confidence)))

        obs = Observation(
            observation_id=str(uuid.uuid4()),
            timestamp_turn=timestamp_turn,
            source=f"domain_adapter:{domain.value}",
            entity_id=entity_id,
            signal_type=mapping.signal_type,
            value=mapping.normalize(value),
            confidence=confidence,
            metadata={
                "metric_name": metric_name,
                "unit": mapping.unit,
                "direction": mapping.direction,
                "raw_value": value,
            },
        )
        observations.append(obs)

    mapped_count = len(observations)
    total_count = len(metrics)
    summary = (
        f"Mapped {mapped_count}/{total_count} {domain.value} metrics "
        f"to observations for entity '{entity_id}'."
    )

    return AdaptedInput(
        domain=domain.value,
        observations=tuple(observations),
        unmapped_metrics=tuple(unmapped),
        summary=summary,
    )


# ─── Output adapter ──────────────────────────────────────────────


def _extract_action_keywords(action_text: str) -> list[str]:
    """Extract action keyword phrases from raw action text.

    Scans for multi-word and single-word keywords that appear in
    any domain action table. Longer phrases match first.
    """
    text_lower = action_text.lower()
    all_keywords: set[str] = set()
    for table in _DOMAIN_ACTION_TABLES.values():
        for mapping in table:
            all_keywords.add(mapping.keyword)

    sorted_keywords = sorted(all_keywords, key=len, reverse=True)

    matched: list[str] = []
    for kw in sorted_keywords:
        if kw in text_lower and kw not in matched:
            matched.append(kw)

    return matched


def adapt_output(
    decision_output: object,
    domain: DomainType,
) -> ActionPlan:
    """Translate an abstract DecisionOutput into a concrete ActionPlan.

    Scans the decision_output.action text for recognized keywords,
    maps each to domain-specific instructions, and returns an ordered
    ActionPlan. Keywords not found in the domain's action table are
    reported as unmapped.

    Pure function — no side effects.
    """
    action_text = getattr(decision_output, "action", "") or ""
    confidence = getattr(decision_output, "confidence", 0.5)
    risk_score = getattr(decision_output, "risk_score", 0.5)

    action_table = _DOMAIN_ACTION_TABLES.get(domain, ())
    keywords = _extract_action_keywords(action_text)

    steps: list[ActionStep] = []
    matched_keywords: set[str] = set()
    unmapped: list[str] = []

    for kw in keywords:
        found = False
        for mapping in action_table:
            if mapping.keyword == kw:
                steps.append(
                    ActionStep(
                        instruction=mapping.instruction,
                        category=mapping.category,
                        priority=mapping.priority,
                        source_keyword=kw,
                    )
                )
                matched_keywords.add(kw)
                found = True
                break
        if not found:
            unmapped.append(kw)

    steps.sort(key=lambda s: s.priority)

    return ActionPlan(
        domain=domain.value,
        steps=tuple(steps),
        confidence=confidence,
        risk_score=risk_score,
        raw_action=action_text,
        unmapped_keywords=tuple(unmapped),
    )


# ─── Observation-to-text formatter ────────────────────────────────
# Converts adapted observations into a natural-language summary
# suitable for passing to SessionInterface.step() as the observation string.


def format_observations_as_text(adapted: AdaptedInput) -> str:
    """Format AdaptedInput observations into a natural-language summary.

    Used to bridge adapt_input() output into SessionInterface.step(),
    which accepts a string observation.
    """
    if not adapted.observations:
        return adapted.summary

    parts: list[str] = [f"Domain: {adapted.domain}. Current metrics:"]
    for obs in adapted.observations:
        meta = obs.metadata
        name = meta.get("metric_name", obs.signal_type)
        unit = meta.get("unit", "")
        direction = meta.get("direction", "")
        raw = meta.get("raw_value", obs.value)

        direction_label = ""
        if direction == "up_good":
            direction_label = " (higher is better)"
        elif direction == "down_good":
            direction_label = " (lower is better)"

        if unit == "usd":
            parts.append(f"  {name}: ${raw:,.2f}{direction_label}")
        elif unit == "ratio":
            parts.append(f"  {name}: {raw:.1%}{direction_label}")
        elif unit in ("hours", "minutes", "seconds", "months"):
            parts.append(f"  {name}: {raw} {unit}{direction_label}")
        else:
            parts.append(f"  {name}: {raw}{direction_label}")

    if adapted.unmapped_metrics:
        parts.append(f"  (unrecognized: {', '.join(adapted.unmapped_metrics)})")

    return "\n".join(parts)


if __name__ == "__main__":
    print("domain_adapter import OK")

    test_input = {
        "domain": "business",
        "metrics": {"revenue": 5000, "leads": 12, "churn_rate": 0.08},
        "entity_id": "lyfe_institute",
    }
    result = adapt_input(test_input)
    print(f"Adapted: {result.summary}")
    print(f"Observations: {len(result.observations)}")
    print(f"Unmapped: {result.unmapped_metrics}")
