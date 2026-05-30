"""Reliability-Weighted Ranker — deterministic candidate ranking using production signals.

Ranks candidates using template confidence, agent reliability, validation strength,
rollback safety, source reliability, expected leverage, and blast radius. Uses
hard gates for eligibility and promotion classes for recommended actions.

Ranking formula:
  weighted_score = (
      template_reliability * 0.25
    + agent_capability    * 0.20
    + validation_strength * 0.15
    + rollback_safety     * 0.15
    + source_reliability  * 0.10
    + expected_leverage   * 0.10
    + blast_radius_safety * 0.05
  )

UMH substrate subsystem. Instance-agnostic.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from substrate.organism.reliability_signals import (
    ReliabilitySignalAggregator,
    ReliabilitySignalBundle,
    RollbackReliabilitySignal,
)

logger = logging.getLogger(__name__)

_SENSITIVE_PATHS = frozenset({
    ".env", "credentials", "secrets", "private_key",
    "docker-compose", "Dockerfile", "nginx.conf",
    "services/.env", "cockpit/.env",
})

_BLOCKED_KEYWORDS = frozenset({
    "docker", "container", "kubernetes", "helm",
    "migration", "schema", "database", "credential",
    "secret", "auth", "token", "password", "certificate",
    "dns", "ssl", "tls", "firewall", "iptables",
})


class PromotionClass(str, Enum):
    EXECUTE_READY_LOW_RISK = "execute_ready_low_risk"
    SUPERVISED_LOW_RISK = "supervised_low_risk"
    RECOMMEND_ONLY = "recommend_only"
    BLOCKED = "blocked"


@dataclass
class RankedCandidate:
    candidate_id: str = ""
    raw_scores: dict[str, float] = field(default_factory=dict)
    weighted_score: float = 0.0
    rank: int = 0
    eligible: bool = False
    blocking_reasons: list[str] = field(default_factory=list)
    promotion_class: PromotionClass = PromotionClass.BLOCKED
    recommended_action: str = ""
    evidence_trace: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "candidate_id": self.candidate_id,
            "raw_scores": {k: round(v, 3) for k, v in self.raw_scores.items()},
            "weighted_score": round(self.weighted_score, 4),
            "rank": self.rank,
            "eligible": self.eligible,
            "blocking_reasons": self.blocking_reasons,
            "promotion_class": self.promotion_class.value,
            "recommended_action": self.recommended_action,
            "evidence_trace": self.evidence_trace,
        }


class ReliabilityWeightedRanker:
    """Deterministic ranking engine using production-backed reliability signals."""

    WEIGHTS = {
        "template_reliability": 0.25,
        "agent_capability": 0.20,
        "validation_strength": 0.15,
        "rollback_safety": 0.15,
        "source_reliability": 0.10,
        "expected_leverage": 0.10,
        "blast_radius_safety": 0.05,
    }

    EXECUTE_READY_THRESHOLDS = {
        "template_reliability": 0.80,
        "agent_reliability": 0.75,
        "validation_reliability": 0.80,
        "min_production_successes": 2,
    }

    SUPERVISED_THRESHOLDS = {
        "template_reliability": 0.65,
        "agent_reliability": 0.65,
    }

    def __init__(self, aggregator: ReliabilitySignalAggregator | None = None) -> None:
        self._aggregator = aggregator or ReliabilitySignalAggregator()
        self._aggregator.aggregate()

    def rank_candidates(self, candidates: list[dict[str, Any]]) -> list[RankedCandidate]:
        ranked: list[RankedCandidate] = []
        for c in candidates:
            rc = self._score_candidate(c)
            ranked.append(rc)

        ranked.sort(key=lambda r: r.weighted_score, reverse=True)
        for i, rc in enumerate(ranked):
            rc.rank = i + 1
        return ranked

    def _score_candidate(self, candidate: dict[str, Any]) -> RankedCandidate:
        cid = candidate.get("candidate_id", "")
        rc = RankedCandidate(candidate_id=cid)

        blocking = self._check_hard_gates(candidate)
        if blocking:
            rc.blocking_reasons = blocking
            rc.eligible = False
            rc.promotion_class = PromotionClass.BLOCKED
            rc.recommended_action = "blocked — " + "; ".join(blocking)
            return rc

        template_id = candidate.get("template_id", "")
        if not template_id:
            templates = candidate.get("matching_templates", [])
            template_id = templates[0] if templates else ""

        bundle = self._aggregator.build_bundle(
            template_id=template_id,
            agent_type=candidate.get("agent_type", "developer_agent"),
            source_name=candidate.get("source", ""),
            validation_method=candidate.get("validation_method", ""),
            rollback_method=candidate.get("rollback_method", ""),
            non_mutating=candidate.get("non_mutating", False),
        )

        raw = self._compute_raw_scores(candidate, bundle)
        rc.raw_scores = raw
        rc.weighted_score = sum(
            raw.get(k, 0.0) * w for k, w in self.WEIGHTS.items()
        )
        rc.eligible = True
        rc.evidence_trace = {
            "template_id": template_id,
            "template_confidence": bundle.template.confidence,
            "template_production_successes": bundle.template.production_successes,
            "agent_type": bundle.agent.agent_type,
            "agent_score": bundle.agent.score(),
            "source": bundle.source.source_name,
            "source_score": bundle.source.score(),
            "validation_method": bundle.validation.validation_method,
            "validation_score": bundle.validation.score(),
            "rollback_score": bundle.rollback.score(),
            "production_truth_score": bundle.production_truth.score(),
        }

        rc.promotion_class = self._classify_promotion(candidate, bundle)
        rc.recommended_action = self._recommend_action(rc.promotion_class)
        return rc

    def _check_hard_gates(self, candidate: dict[str, Any]) -> list[str]:
        reasons: list[str] = []
        risk = candidate.get("risk_class", "unknown")
        if risk != "low":
            reasons.append(f"risk_not_low ({risk})")

        if not candidate.get("evidence") and not candidate.get("description"):
            reasons.append("no_evidence")

        template_id = candidate.get("template_id", "")
        if not template_id:
            templates = candidate.get("matching_templates", [])
            if not templates:
                reasons.append("no_template_match")

        if not candidate.get("validation_method"):
            reasons.append("no_validation_method")

        if not candidate.get("rollback_method") and not candidate.get("non_mutating"):
            reasons.append("no_rollback_or_non_mutating")

        for f in candidate.get("affected_files", []):
            fl = f.lower()
            for sp in _SENSITIVE_PATHS:
                if sp in fl:
                    reasons.append(f"sensitive_path ({f})")
                    break

        desc = (candidate.get("description", "") + " " + candidate.get("title", "")).lower()
        for kw in _BLOCKED_KEYWORDS:
            if kw in desc:
                reasons.append(f"blocked_keyword ({kw})")
                break

        if candidate.get("policy_decision") == "resolved":
            reasons.append("already_resolved")

        return reasons

    def _compute_raw_scores(
        self, candidate: dict[str, Any], bundle: ReliabilitySignalBundle
    ) -> dict[str, float]:
        template_score = bundle.template.score()
        agent_score = bundle.agent.score()
        validation_score = bundle.validation.score()
        rollback_score = bundle.rollback.score()
        source_score = bundle.source.score()

        affected = candidate.get("affected_files", [])
        file_count = len(affected)
        if file_count == 0:
            leverage = 0.3
        elif file_count <= 3:
            leverage = 0.8
        else:
            leverage = 0.6

        if file_count <= 1:
            blast_safety = 1.0
        elif file_count <= 5:
            blast_safety = 0.8
        elif file_count <= 10:
            blast_safety = 0.5
        else:
            blast_safety = 0.3

        return {
            "template_reliability": template_score,
            "agent_capability": agent_score,
            "validation_strength": validation_score,
            "rollback_safety": rollback_score,
            "source_reliability": source_score,
            "expected_leverage": leverage,
            "blast_radius_safety": blast_safety,
        }

    def _classify_promotion(
        self, candidate: dict[str, Any], bundle: ReliabilitySignalBundle
    ) -> PromotionClass:
        t = self.EXECUTE_READY_THRESHOLDS
        if (
            bundle.template.score() >= t["template_reliability"]
            and bundle.agent.score() >= t["agent_reliability"]
            and bundle.validation.score() >= t["validation_reliability"]
            and (bundle.rollback.non_mutating or bundle.rollback.rollback_method_exists)
            and bundle.template.production_successes >= t["min_production_successes"]
        ):
            return PromotionClass.EXECUTE_READY_LOW_RISK

        s = self.SUPERVISED_THRESHOLDS
        if (
            bundle.template.score() >= s["template_reliability"]
            and bundle.agent.score() >= s["agent_reliability"]
            and bundle.validation.validation_method
        ):
            return PromotionClass.SUPERVISED_LOW_RISK

        if candidate.get("evidence") or candidate.get("description"):
            return PromotionClass.RECOMMEND_ONLY

        return PromotionClass.BLOCKED

    def _recommend_action(self, promotion_class: PromotionClass) -> str:
        actions = {
            PromotionClass.EXECUTE_READY_LOW_RISK: "eligible for supervised PR creation (operator approval required)",
            PromotionClass.SUPERVISED_LOW_RISK: "eligible with operator review — template or agent below execute threshold",
            PromotionClass.RECOMMEND_ONLY: "recommendation only — insufficient reliability for execution",
            PromotionClass.BLOCKED: "blocked by hard gates",
        }
        return actions.get(promotion_class, "unknown")

    def to_dict(self) -> dict[str, Any]:
        return {
            "weights": self.WEIGHTS,
            "execute_ready_thresholds": self.EXECUTE_READY_THRESHOLDS,
            "supervised_thresholds": self.SUPERVISED_THRESHOLDS,
            "hard_gates": [
                "risk must be LOW",
                "evidence must exist",
                "template match must exist",
                "validation method must exist",
                "rollback method or non-mutating proof must exist",
                "no sensitive path",
                "no blocked keywords",
                "candidate not already resolved",
            ],
            "promotion_classes": [pc.value for pc in PromotionClass],
        }
