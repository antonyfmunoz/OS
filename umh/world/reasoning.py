"""WorldReasoning — deterministic derived understanding from WorldSnapshot.

Transforms the passive world substrate into active understanding:
entity trends, health/stability classification, single-hop risk
propagation, and global world flags.

All logic is deterministic, bounded, and domain-agnostic.
No LLM calls. No embeddings. No randomness. No external dependencies.

WorldUnderstanding is a derived view — NOT persisted. It is recomputed
each turn from the current WorldSnapshot + observation history.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field

from umh.world.types import (
    Entity,
    Observation,
    Relation,
    StateFact,
    WorldSnapshot,
)

# ─── Constants ───────────────────────────────────────────────────

MIN_TREND_POINTS = 3
SLOPE_EPSILON = 0.005
VOLATILITY_RATIO = 2.0
MAX_TREND_POINTS = 50

HEALTH_GOOD_THRESHOLD = 0.6
HEALTH_WATCH_THRESHOLD = 0.3

STABILITY_VOLATILE_THRESHOLD = 0.5
STABILITY_UNSTABLE_THRESHOLD = 0.3

PROPAGATION_SCALE = 0.5
PROPAGATION_MAX = 1.0

DEGRADING_THRESHOLD = 0.5
VOLATILE_THRESHOLD = 0.4
INSUFFICIENT_DATA_MIN = 3

WARNING_KEYWORDS = frozenset(
    {"risk", "error", "failed", "failure", "warning", "critical", "degraded", "alert"}
)

# ─── Data models ─────────────────────────────────────────────────


@dataclass(frozen=True)
class EntityTrend:
    """Trend for one numeric signal of one entity."""

    entity_id: str
    key: str
    direction: str
    slope: float
    confidence: float
    reason: str

    def to_dict(self) -> dict:
        return {
            "entity_id": self.entity_id,
            "key": self.key,
            "direction": self.direction,
            "slope": round(self.slope, 6),
            "confidence": round(self.confidence, 4),
            "reason": self.reason,
        }


@dataclass(frozen=True)
class EntityAssessment:
    """Derived assessment of one entity's condition."""

    entity_id: str
    health: str
    stability: str
    trend_summary: tuple[EntityTrend, ...]
    risk_flags: tuple[str, ...]
    confidence: float

    def to_dict(self) -> dict:
        return {
            "entity_id": self.entity_id,
            "health": self.health,
            "stability": self.stability,
            "trend_summary": [t.to_dict() for t in self.trend_summary],
            "risk_flags": list(self.risk_flags),
            "confidence": round(self.confidence, 4),
        }


@dataclass(frozen=True)
class RelationImpact:
    """Single-hop risk propagation from source to target."""

    source_id: str
    target_id: str
    relation_type: str
    propagated_risk: float
    propagated_reason: str

    def to_dict(self) -> dict:
        return {
            "source_id": self.source_id,
            "target_id": self.target_id,
            "relation_type": self.relation_type,
            "propagated_risk": round(self.propagated_risk, 4),
            "propagated_reason": self.propagated_reason,
        }


@dataclass(frozen=True)
class WorldUnderstanding:
    """Derived understanding of the world at a point in time."""

    entity_assessments: tuple[EntityAssessment, ...]
    relation_impacts: tuple[RelationImpact, ...]
    global_flags: tuple[str, ...]
    snapshot_version: int
    derived_count: int

    def to_dict(self) -> dict:
        return {
            "entity_assessments": [a.to_dict() for a in self.entity_assessments],
            "relation_impacts": [r.to_dict() for r in self.relation_impacts],
            "global_flags": list(self.global_flags),
            "snapshot_version": self.snapshot_version,
            "derived_count": self.derived_count,
        }


# ─── Trend detection ────────────────────────────────────────────


def _compute_slope(values: list[float]) -> float:
    """Simple least-squares slope over indexed values."""
    n = len(values)
    if n < 2:
        return 0.0
    x_mean = (n - 1) / 2.0
    y_mean = sum(values) / n
    num = sum((i - x_mean) * (v - y_mean) for i, v in enumerate(values))
    den = sum((i - x_mean) ** 2 for i in range(n))
    if den == 0.0:
        return 0.0
    return num / den


def _compute_variance(values: list[float]) -> float:
    """Population variance."""
    n = len(values)
    if n < 2:
        return 0.0
    mean = sum(values) / n
    return sum((v - mean) ** 2 for v in values) / n


def detect_trend(
    entity_id: str,
    key: str,
    values: list[float],
) -> EntityTrend:
    """Detect trend direction from a series of numeric values.

    Rules:
    - < MIN_TREND_POINTS -> unknown
    - slope magnitude < EPSILON -> flat
    - if variance/|slope| > VOLATILITY_RATIO -> volatile
    - else: up or down based on sign
    """
    if len(values) < MIN_TREND_POINTS:
        return EntityTrend(
            entity_id=entity_id,
            key=key,
            direction="unknown",
            slope=0.0,
            confidence=0.0,
            reason=f"insufficient data ({len(values)} < {MIN_TREND_POINTS})",
        )

    trimmed = values[-MAX_TREND_POINTS:]
    slope = _compute_slope(trimmed)
    variance = _compute_variance(trimmed)
    std = math.sqrt(variance) if variance > 0 else 0.0

    if abs(slope) < SLOPE_EPSILON:
        conf = min(1.0, len(trimmed) / 20.0) * max(0.0, 1.0 - std)
        return EntityTrend(
            entity_id=entity_id,
            key=key,
            direction="flat",
            slope=slope,
            confidence=max(0.0, min(1.0, conf)),
            reason="slope below epsilon",
        )

    if abs(slope) > 0 and std / abs(slope) > VOLATILITY_RATIO:
        conf = max(0.0, min(1.0, 0.3 * len(trimmed) / 10.0))
        return EntityTrend(
            entity_id=entity_id,
            key=key,
            direction="volatile",
            slope=slope,
            confidence=conf,
            reason=f"high variance relative to slope (std/|slope|={std / abs(slope):.2f})",
        )

    consistency = _direction_consistency(trimmed)
    n_factor = min(1.0, len(trimmed) / 10.0)
    conf = max(0.0, min(1.0, consistency * n_factor))

    direction = "up" if slope > 0 else "down"
    return EntityTrend(
        entity_id=entity_id,
        key=key,
        direction=direction,
        slope=slope,
        confidence=conf,
        reason=f"consistent {direction} trend (slope={slope:.4f})",
    )


def _direction_consistency(values: list[float]) -> float:
    """Fraction of consecutive steps that go in the same direction as overall."""
    if len(values) < 2:
        return 0.0
    overall = values[-1] - values[0]
    if overall == 0.0:
        return 0.5
    sign = 1.0 if overall > 0 else -1.0
    steps = len(values) - 1
    same = sum(1 for i in range(steps) if (values[i + 1] - values[i]) * sign > 0)
    return same / steps


# ─── Observation history extraction ─────────────────────────────


def _extract_numeric_series(
    observations: tuple[Observation, ...],
    entity_id: str,
    signal_type: str,
) -> list[float]:
    """Extract numeric values for (entity_id, signal_type) in chronological order."""
    result: list[float] = []
    for obs in observations:
        if obs.entity_id != entity_id or obs.signal_type != signal_type:
            continue
        if isinstance(obs.value, bool):
            continue
        if isinstance(obs.value, (int, float)):
            result.append(float(obs.value))
    return result[-MAX_TREND_POINTS:]


# ─── Entity health classification ───────────────────────────────


def _health_score_from_facts_and_trends(
    facts: list[StateFact],
    trends: list[EntityTrend],
) -> float:
    """Compute a bounded [0, 1] health score from state facts and trends.

    Higher = healthier. Domain-agnostic heuristics:
    - Numeric facts: normalized positive values contribute
    - Downward trends penalize
    - Warning-keyword facts penalize
    - Low confidence reduces certainty
    """
    if not facts and not trends:
        return 0.5

    score = 0.5
    contributions = 0

    for fact in facts:
        if isinstance(fact.value, bool) or isinstance(fact.value, str):
            has_warning = any(kw in fact.key.lower() for kw in WARNING_KEYWORDS)
            if has_warning:
                if fact.value is True or (
                    isinstance(fact.value, str)
                    and fact.value.lower() in ("true", "yes", "1")
                ):
                    score -= 0.15 * fact.confidence
                    contributions += 1
        elif isinstance(fact.value, (int, float)):
            contributions += 1

    for trend in trends:
        if trend.direction == "down":
            score -= 0.1 * trend.confidence
            contributions += 1
        elif trend.direction == "up":
            score += 0.05 * trend.confidence
            contributions += 1
        elif trend.direction == "volatile":
            score -= 0.05 * trend.confidence
            contributions += 1

    return max(0.0, min(1.0, score))


def _classify_health(score: float) -> str:
    if score >= HEALTH_GOOD_THRESHOLD:
        return "good"
    if score >= HEALTH_WATCH_THRESHOLD:
        return "watch"
    return "bad"


# ─── Entity stability classification ────────────────────────────


def _compute_stability_score(trends: list[EntityTrend]) -> float:
    """Stability score from trends. Higher = more stable.

    - flat/up/down with high consistency -> stable
    - volatile -> unstable
    - conflicting directions -> lower stability
    """
    if not trends:
        return 0.5

    volatile_count = sum(1 for t in trends if t.direction == "volatile")
    unknown_count = sum(1 for t in trends if t.direction == "unknown")
    known = [t for t in trends if t.direction not in ("unknown",)]

    if not known:
        return 0.5

    volatile_frac = volatile_count / len(known) if known else 0.0
    avg_confidence = sum(t.confidence for t in known) / len(known)

    stability = 1.0 - volatile_frac * 0.6

    directions = {t.direction for t in known} - {"volatile", "unknown"}
    if len(directions) > 1:
        stability -= 0.2

    stability *= max(0.3, avg_confidence)

    return max(0.0, min(1.0, stability))


def _classify_stability(score: float) -> str:
    if score >= (1.0 - STABILITY_UNSTABLE_THRESHOLD):
        return "stable"
    if score >= STABILITY_VOLATILE_THRESHOLD:
        return "unstable"
    return "volatile"


# ─── Risk flags ──────────────────────────────────────────────────


def _compute_risk_flags(
    facts: list[StateFact],
    trends: list[EntityTrend],
    health: str,
) -> list[str]:
    """Generate risk flags for an entity based on its state."""
    flags: list[str] = []

    for fact in facts:
        has_warning = any(kw in fact.key.lower() for kw in WARNING_KEYWORDS)
        if has_warning and fact.value is True:
            flags.append(f"warning_active:{fact.key}")

    for trend in trends:
        if trend.direction == "down" and trend.confidence > 0.5:
            flags.append(f"declining:{trend.key}")
        if trend.direction == "volatile" and trend.confidence > 0.3:
            flags.append(f"volatile:{trend.key}")

    if health == "bad":
        flags.append("entity_unhealthy")

    return sorted(set(flags))


# ─── Relation-based risk propagation ─────────────────────────────


def _propagate_risk(
    relations: tuple[Relation, ...],
    assessments: dict[str, EntityAssessment],
) -> list[RelationImpact]:
    """Single-hop risk propagation from unhealthy sources to targets."""
    impacts: list[RelationImpact] = []

    for rel in relations:
        source_assessment = assessments.get(rel.source_id)
        if source_assessment is None:
            continue

        source_risk = 0.0
        if source_assessment.health == "bad":
            source_risk = 0.8
        elif source_assessment.health == "watch":
            source_risk = 0.4
        elif source_assessment.risk_flags:
            source_risk = 0.2

        if source_risk <= 0.0:
            continue

        propagated = min(
            PROPAGATION_MAX,
            rel.weight * source_risk * PROPAGATION_SCALE,
        )

        if propagated < 0.01:
            continue

        reasons: list[str] = []
        if source_assessment.health == "bad":
            reasons.append(f"source {rel.source_id} is unhealthy")
        if source_assessment.risk_flags:
            reasons.append(f"source has {len(source_assessment.risk_flags)} risk flags")

        impacts.append(
            RelationImpact(
                source_id=rel.source_id,
                target_id=rel.target_id,
                relation_type=rel.relation_type,
                propagated_risk=propagated,
                propagated_reason="; ".join(reasons),
            )
        )

    return impacts


# ─── Global flags ────────────────────────────────────────────────


def _compute_global_flags(
    assessments: tuple[EntityAssessment, ...],
    snapshot: WorldSnapshot,
) -> list[str]:
    """Compute world-level flags from entity assessments."""
    flags: list[str] = []

    if not assessments:
        flags.append("insufficient_world_data")
        return sorted(flags)

    total = len(assessments)
    bad_count = sum(1 for a in assessments if a.health == "bad")
    volatile_count = sum(
        1 for a in assessments if a.stability in ("volatile", "unstable")
    )

    if total > 0 and bad_count / total >= DEGRADING_THRESHOLD:
        flags.append("world_degrading")

    if total > 0 and volatile_count / total >= VOLATILE_THRESHOLD:
        flags.append("world_volatile")

    if snapshot.observation_count < INSUFFICIENT_DATA_MIN:
        flags.append("insufficient_world_data")

    risk_entities = {a.entity_id for a in assessments if a.risk_flags}
    if len(risk_entities) >= 3:
        flags.append("risk_cluster_detected")

    return sorted(set(flags))


# ─── World Reasoning Engine ─────────────────────────────────────


class WorldReasoningEngine:
    """Stateless engine that derives understanding from WorldSnapshot.

    All methods are pure functions over the snapshot and observation
    history. No internal state is retained between calls.
    """

    def derive_understanding(
        self,
        snapshot: WorldSnapshot,
        observation_history: tuple[Observation, ...] | None = None,
    ) -> WorldUnderstanding:
        """Derive a complete WorldUnderstanding from snapshot + history."""
        observations = observation_history or ()

        entity_assessments: list[EntityAssessment] = []
        assessment_map: dict[str, EntityAssessment] = {}

        for entity in snapshot.entities:
            entity_facts = [
                f for f in snapshot.state_facts if f.entity_id == entity.entity_id
            ]

            numeric_keys = _get_numeric_signal_keys(entity.entity_id, entity_facts)
            trends: list[EntityTrend] = []
            for key in numeric_keys:
                series = _extract_numeric_series(observations, entity.entity_id, key)
                if series:
                    trends.append(detect_trend(entity.entity_id, key, series))

            health_score = _health_score_from_facts_and_trends(entity_facts, trends)
            health = _classify_health(health_score)

            stability_score = _compute_stability_score(trends)
            stability = _classify_stability(stability_score)

            risk_flags = _compute_risk_flags(entity_facts, trends, health)

            fact_confidences = [f.confidence for f in entity_facts if f.confidence > 0]
            avg_confidence = (
                sum(fact_confidences) / len(fact_confidences)
                if fact_confidences
                else 0.5
            )

            assessment = EntityAssessment(
                entity_id=entity.entity_id,
                health=health,
                stability=stability,
                trend_summary=tuple(trends),
                risk_flags=tuple(risk_flags),
                confidence=max(0.0, min(1.0, avg_confidence)),
            )
            entity_assessments.append(assessment)
            assessment_map[entity.entity_id] = assessment

        relation_impacts = _propagate_risk(snapshot.relations, assessment_map)

        global_flags = _compute_global_flags(tuple(entity_assessments), snapshot)

        return WorldUnderstanding(
            entity_assessments=tuple(entity_assessments),
            relation_impacts=tuple(relation_impacts),
            global_flags=tuple(global_flags),
            snapshot_version=snapshot.version,
            derived_count=len(entity_assessments),
        )


def _get_numeric_signal_keys(
    entity_id: str,
    facts: list[StateFact],
) -> list[str]:
    """Extract signal keys that have numeric values."""
    keys: list[str] = []
    for fact in facts:
        if (
            fact.entity_id == entity_id
            and isinstance(fact.value, (int, float))
            and not isinstance(fact.value, bool)
        ):
            keys.append(fact.key)
    return sorted(keys)


# ─── Query helpers ───────────────────────────────────────────────


def get_entity_assessment(
    understanding: WorldUnderstanding,
    entity_id: str,
) -> EntityAssessment | None:
    """Look up assessment for a specific entity."""
    for a in understanding.entity_assessments:
        if a.entity_id == entity_id:
            return a
    return None


def get_riskiest_entities(
    understanding: WorldUnderstanding,
    limit: int = 5,
) -> list[EntityAssessment]:
    """Return the riskiest entities, sorted by severity then risk flag count."""
    health_order = {"bad": 0, "watch": 1, "unknown": 2, "good": 3}
    ranked = sorted(
        understanding.entity_assessments,
        key=lambda a: (health_order.get(a.health, 4), -len(a.risk_flags)),
    )
    return ranked[:limit]


def get_impacted_targets(
    understanding: WorldUnderstanding,
    source_id: str,
) -> list[RelationImpact]:
    """Return all relation impacts originating from source_id."""
    return [r for r in understanding.relation_impacts if r.source_id == source_id]


def summarize_understanding(understanding: WorldUnderstanding) -> dict:
    """Return a compact summary suitable for trace/log."""
    assessments = understanding.entity_assessments
    total = len(assessments)
    health_counts = {}
    stability_counts = {}
    for a in assessments:
        health_counts[a.health] = health_counts.get(a.health, 0) + 1
        stability_counts[a.stability] = stability_counts.get(a.stability, 0) + 1

    riskiest = get_riskiest_entities(understanding, limit=1)

    return {
        "snapshot_version": understanding.snapshot_version,
        "entity_count": total,
        "derived_count": understanding.derived_count,
        "health_distribution": health_counts,
        "stability_distribution": stability_counts,
        "global_flags": list(understanding.global_flags),
        "relation_impact_count": len(understanding.relation_impacts),
        "riskiest_entity": riskiest[0].entity_id if riskiest else None,
        "riskiest_entity_health": riskiest[0].health if riskiest else None,
    }
