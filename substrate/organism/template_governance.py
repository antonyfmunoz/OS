"""Template Governance — 9-dimension scoring engine for template cadence eligibility.

Evaluates every template on evidence, validation, rollback, risk, reliability,
specificity, reversibility, blast_radius, and agent_capability. Produces one of
four decisions: cadence_eligible, candidate_only, operator_review_required, or
blocked — each with reason codes.

UMH substrate subsystem. Instance-agnostic.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from substrate.organism.template_registry import TemplateCandidate, TemplateStatus

logger = logging.getLogger(__name__)

_SENSITIVE_PATHS = [
    r"\.env$",
    r"credentials",
    r"secrets?\.ya?ml",
    r"\.pem$",
    r"\.key$",
    r"authorized_keys",
    r"ssh_config",
    r"id_rsa",
    r"\.htpasswd",
    r"docker-compose\.ya?ml",
    r"Dockerfile",
    r"services/\.env",
]
_SENSITIVE_PATH_PATTERNS = [re.compile(p, re.IGNORECASE) for p in _SENSITIVE_PATHS]

_SENSITIVE_KEYWORDS = [
    "password",
    "credential",
    "secret",
    "api_key",
    "apikey",
    "token",
    "private_key",
    "oauth",
    "jwt",
    "auth_token",
    "session_secret",
]

_BROAD_FILE_PATTERNS = [
    r"\*\*\/\*",
    r"\*\.\*",
    r"\.\*$",
]
_BROAD_FILE_RE = [re.compile(p) for p in _BROAD_FILE_PATTERNS]

_MUTATION_KEYWORDS = [
    "auth",
    "credential",
    "dns",
    "container",
    "docker run",
    "docker build",
    "docker push",
    "iptables",
    "firewall",
    "chmod 777",
    "rm -rf /",
    "drop table",
    "drop database",
    "truncate table",
]


class GovernanceDecision(str, Enum):
    CADENCE_ELIGIBLE = "cadence_eligible"
    CANDIDATE_ONLY = "candidate_only"
    OPERATOR_REVIEW_REQUIRED = "operator_review_required"
    BLOCKED = "blocked"


@dataclass
class DimensionScore:
    name: str
    score: float
    weight: float = 1.0
    reason: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "score": round(self.score, 3),
            "weight": self.weight,
            "reason": self.reason,
        }


@dataclass
class TemplateGovernanceScore:
    template_id: str
    dimensions: list[DimensionScore] = field(default_factory=list)
    decision: GovernanceDecision = GovernanceDecision.BLOCKED
    reason_codes: list[str] = field(default_factory=list)
    weighted_score: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "template_id": self.template_id,
            "dimensions": [d.to_dict() for d in self.dimensions],
            "decision": self.decision.value,
            "reason_codes": self.reason_codes,
            "weighted_score": round(self.weighted_score, 3),
        }


class TemplateGovernance:
    """Evaluates templates on 9 dimensions and produces governance decisions."""

    CADENCE_THRESHOLDS = {
        "evidence": 0.70,
        "validation": 0.80,
        "rollback": 0.70,
        "reliability": 0.70,
    }

    OPERATOR_REVIEW_THRESHOLDS = {
        "evidence": 0.50,
        "validation": 0.60,
        "rollback": 0.50,
        "reliability": 0.50,
    }

    def evaluate(self, template: TemplateCandidate) -> TemplateGovernanceScore:
        dimensions = [
            self._score_evidence(template),
            self._score_validation(template),
            self._score_rollback(template),
            self._score_risk(template),
            self._score_reliability(template),
            self._score_specificity(template),
            self._score_reversibility(template),
            self._score_blast_radius(template),
            self._score_agent_capability(template),
        ]

        reason_codes: list[str] = []
        blocked = False

        block_reasons = self._check_blocking_rules(template)
        if block_reasons:
            blocked = True
            reason_codes.extend(block_reasons)

        if template.risk_class not in ("low",):
            blocked = True
            reason_codes.append(f"risk_class_not_low:{template.risk_class}")

        total_weight = sum(d.weight for d in dimensions)
        weighted_score = (
            sum(d.score * d.weight for d in dimensions) / total_weight
            if total_weight > 0
            else 0.0
        )

        for d in dimensions:
            if d.reason:
                reason_codes.append(f"{d.name}:{d.reason}")

        if blocked:
            decision = GovernanceDecision.BLOCKED
        else:
            decision = self._decide(dimensions, reason_codes)

        return TemplateGovernanceScore(
            template_id=template.template_id,
            dimensions=dimensions,
            decision=decision,
            reason_codes=reason_codes,
            weighted_score=weighted_score,
        )

    def evaluate_batch(self, templates: list[TemplateCandidate]) -> list[TemplateGovernanceScore]:
        return [self.evaluate(t) for t in templates]

    def _decide(self, dimensions: list[DimensionScore], reason_codes: list[str]) -> GovernanceDecision:
        dim_map = {d.name: d.score for d in dimensions}

        cadence_pass = True
        for dim_name, threshold in self.CADENCE_THRESHOLDS.items():
            if dim_map.get(dim_name, 0.0) < threshold:
                cadence_pass = False
                reason_codes.append(f"{dim_name}_below_cadence_threshold:{dim_map.get(dim_name, 0.0):.2f}<{threshold}")

        if cadence_pass:
            return GovernanceDecision.CADENCE_ELIGIBLE

        operator_pass = True
        for dim_name, threshold in self.OPERATOR_REVIEW_THRESHOLDS.items():
            if dim_map.get(dim_name, 0.0) < threshold:
                operator_pass = False
                reason_codes.append(f"{dim_name}_below_operator_threshold:{dim_map.get(dim_name, 0.0):.2f}<{threshold}")

        if operator_pass:
            return GovernanceDecision.OPERATOR_REVIEW_REQUIRED

        return GovernanceDecision.CANDIDATE_ONLY

    def _check_blocking_rules(self, template: TemplateCandidate) -> list[str]:
        reasons: list[str] = []

        all_text = " ".join(
            template.trigger_conditions
            + template.required_context
            + template.evidence_requirements
            + template.known_failure_modes
            + [template.expected_outcome]
            + [s.description + " " + s.action + " " + s.verification for s in template.reusable_steps]
            + ([template.validation.description] if template.validation else [])
            + ([template.rollback.description] if template.rollback else [])
        ).lower()

        for pattern in _SENSITIVE_PATH_PATTERNS:
            if pattern.search(all_text):
                reasons.append(f"sensitive_path:{pattern.pattern}")

        for kw in _SENSITIVE_KEYWORDS:
            if kw in all_text:
                reasons.append(f"sensitive_keyword:{kw}")

        for pattern in _BROAD_FILE_RE:
            if pattern.search(all_text):
                reasons.append(f"broad_file_pattern:{pattern.pattern}")

        for mutation in _MUTATION_KEYWORDS:
            if mutation in all_text:
                reasons.append(f"mutation_keyword:{mutation}")

        return reasons

    def _score_evidence(self, template: TemplateCandidate) -> DimensionScore:
        if not template.evidence:
            return DimensionScore(name="evidence", score=0.0, reason="no_evidence_items")
        avg_conf = sum(e.confidence for e in template.evidence) / len(template.evidence)
        source_count = len({e.source for e in template.evidence})
        score = min(1.0, avg_conf * (1.0 + 0.1 * (source_count - 1)))
        return DimensionScore(name="evidence", score=score)

    def _score_validation(self, template: TemplateCandidate) -> DimensionScore:
        if not template.validation:
            return DimensionScore(name="validation", score=0.0, reason="no_validation_strategy")
        desc = template.validation.description
        if not desc or desc == "Re-run verification after action":
            return DimensionScore(name="validation", score=0.2, reason="generic_validation_stub")
        specificity_bonus = 0.0
        if any(kw in desc.lower() for kw in ["py_compile", "pytest", "curl", "assert", "exit code", "returns"]):
            specificity_bonus = 0.2
        base = 0.7
        return DimensionScore(name="validation", score=min(1.0, base + specificity_bonus))

    def _score_rollback(self, template: TemplateCandidate) -> DimensionScore:
        if not template.rollback:
            return DimensionScore(name="rollback", score=0.0, reason="no_rollback_strategy")
        desc = template.rollback.description
        if not desc or desc == "Revert to pre-execution state":
            return DimensionScore(name="rollback", score=0.2, reason="generic_rollback_stub")
        if "non-destructive" in desc.lower() or "no rollback required" in desc.lower():
            return DimensionScore(name="rollback", score=1.0)
        specificity_bonus = 0.0
        if any(kw in desc.lower() for kw in ["git checkout", "os.remove", "docker restart", "git revert"]):
            specificity_bonus = 0.2
        base = 0.7
        return DimensionScore(name="rollback", score=min(1.0, base + specificity_bonus))

    def _score_risk(self, template: TemplateCandidate) -> DimensionScore:
        risk_scores = {"low": 1.0, "medium": 0.5, "high": 0.2, "critical": 0.0}
        score = risk_scores.get(template.risk_class, 0.3)
        reason = "" if template.risk_class == "low" else f"risk_class={template.risk_class}"
        return DimensionScore(name="risk", score=score, reason=reason)

    def _score_reliability(self, template: TemplateCandidate) -> DimensionScore:
        if template.total_observations == 0:
            return DimensionScore(name="reliability", score=0.3, reason="no_observations")
        score = template.success_rate
        if template.total_observations < 3:
            score *= 0.8
        return DimensionScore(name="reliability", score=min(1.0, score))

    def _score_specificity(self, template: TemplateCandidate) -> DimensionScore:
        score = 0.0
        if len(template.trigger_conditions) >= 2:
            score += 0.3
        if len(template.reusable_steps) >= 2:
            score += 0.3
        if template.validation and len(template.validation.description) > 50:
            score += 0.2
        if template.rollback and len(template.rollback.description) > 30:
            score += 0.2
        return DimensionScore(name="specificity", score=min(1.0, score))

    def _score_reversibility(self, template: TemplateCandidate) -> DimensionScore:
        if not template.rollback:
            return DimensionScore(name="reversibility", score=0.2, reason="no_rollback")
        desc = template.rollback.description.lower()
        if "non-destructive" in desc or "no rollback required" in desc:
            return DimensionScore(name="reversibility", score=1.0)
        if "git checkout" in desc or "git revert" in desc:
            return DimensionScore(name="reversibility", score=0.9)
        if "os.remove" in desc or "docker restart" in desc:
            return DimensionScore(name="reversibility", score=0.8)
        return DimensionScore(name="reversibility", score=0.6)

    def _score_blast_radius(self, template: TemplateCandidate) -> DimensionScore:
        step_count = len(template.reusable_steps)
        if step_count <= 3:
            score = 1.0
        elif step_count <= 5:
            score = 0.7
        else:
            score = 0.4

        dep_count = len(template.dependencies)
        if dep_count > 3:
            score *= 0.7

        return DimensionScore(name="blast_radius", score=min(1.0, score))

    def _score_agent_capability(self, template: TemplateCandidate) -> DimensionScore:
        if not template.agent_capability_binding:
            return DimensionScore(name="agent_capability", score=0.3, reason="no_agent_binding")
        binding = template.agent_capability_binding
        score = binding.confidence
        if len(binding.capabilities) == 0:
            score *= 0.5
        return DimensionScore(name="agent_capability", score=min(1.0, score))
