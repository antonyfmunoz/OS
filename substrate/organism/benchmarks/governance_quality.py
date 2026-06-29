"""Governance Quality Scorer — Benchmark D for C33.

Scores governance decision quality:
  - approval correctness
  - blast-radius classification accuracy
  - policy adherence
  - audit trail completeness
  - replayability

All scoring is deterministic. No LLM calls.

UMH substrate subsystem. Instance-agnostic.
"""

from __future__ import annotations

import json
import logging
import os
import time
from dataclasses import asdict, dataclass, field
from typing import Any
from uuid import uuid4

logger = logging.getLogger(__name__)

_REPO_ROOT = os.environ.get("UMH_ROOT", "/opt/OS")
_STORE_PATH = os.path.join(
    _REPO_ROOT, "data", "umh", "c33", "governance_assessments.jsonl"
)

_WEIGHTS = {
    "approval": 0.25,
    "blast_radius": 0.20,
    "policy": 0.20,
    "audit": 0.20,
    "replay": 0.15,
}


@dataclass
class GovernanceAssessment:
    assessment_id: str = field(default_factory=lambda: f"gov-{uuid4().hex[:8]}")
    envelope_id: str = ""
    cycle_id: str = ""
    task_description: str = ""
    timestamp: float = field(default_factory=time.time)

    approval_decision: str = ""
    approval_expected: str = ""
    approval_correct: bool = False

    blast_radius_classified: str = ""
    blast_radius_expected: str = ""
    blast_radius_correct: bool = False

    policies_checked: list[str] = field(default_factory=list)
    policies_violated: list[str] = field(default_factory=list)
    policies_adhered: bool = False

    audit_trail_complete: bool = False
    audit_has_intent: bool = False
    audit_has_decision: bool = False
    audit_has_execution: bool = False
    audit_has_outcome: bool = False
    audit_has_learning: bool = False

    replay_attempted: bool = False
    replay_succeeded: bool = False

    human_approval_required: bool = False
    human_approval_obtained: bool = False
    approval_surface: str = ""

    notes: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> GovernanceAssessment:
        fields = {k: v for k, v in d.items() if k in cls.__dataclass_fields__}
        return cls(**fields)


@dataclass
class GovernanceScore:
    assessment_id: str = ""
    approval_score: float = 0.0
    blast_radius_score: float = 0.0
    policy_score: float = 0.0
    audit_score: float = 0.0
    replay_score: float = 0.0
    composite: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class GovernanceQualityScorer:
    """Scores governance decisions from governed execution."""

    def __init__(self, store_path: str = _STORE_PATH) -> None:
        self._path = store_path
        self._assessments: list[GovernanceAssessment] = []
        self._scores: list[GovernanceScore] = []
        self._load()

    def _load(self) -> None:
        if not os.path.isfile(self._path):
            return
        try:
            with open(self._path) as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        d = json.loads(line)
                        self._assessments.append(GovernanceAssessment.from_dict(d))
                    except (json.JSONDecodeError, TypeError) as exc:
                        logger.debug("Skip malformed governance line: %s", exc)
        except OSError as exc:
            logger.debug("Cannot read %s: %s", self._path, exc)

    def _persist(self, assessment: GovernanceAssessment) -> None:
        os.makedirs(os.path.dirname(self._path), exist_ok=True)
        with open(self._path, "a") as f:
            f.write(json.dumps(assessment.to_dict(), default=str) + "\n")

    def record_assessment(self, assessment: GovernanceAssessment) -> GovernanceScore:
        self._assessments.append(assessment)
        self._persist(assessment)
        score = self.score_assessment(assessment)
        self._scores.append(score)
        return score

    def score_assessment(self, assessment: GovernanceAssessment) -> GovernanceScore:
        approval = 1.0 if assessment.approval_correct else 0.0
        blast = 1.0 if assessment.blast_radius_correct else 0.0
        policy = 1.0 if assessment.policies_adhered else 0.0

        audit_parts = [
            assessment.audit_has_intent,
            assessment.audit_has_decision,
            assessment.audit_has_execution,
            assessment.audit_has_outcome,
            assessment.audit_has_learning,
        ]
        audit = sum(audit_parts) / len(audit_parts) if audit_parts else 0.0
        if assessment.audit_trail_complete:
            audit = 1.0

        if assessment.replay_attempted:
            replay = 1.0 if assessment.replay_succeeded else 0.0
        else:
            replay = 0.5

        composite = (
            approval * _WEIGHTS["approval"]
            + blast * _WEIGHTS["blast_radius"]
            + policy * _WEIGHTS["policy"]
            + audit * _WEIGHTS["audit"]
            + replay * _WEIGHTS["replay"]
        )

        return GovernanceScore(
            assessment_id=assessment.assessment_id,
            approval_score=approval,
            blast_radius_score=blast,
            policy_score=policy,
            audit_score=round(audit, 4),
            replay_score=replay,
            composite=round(composite, 4),
        )

    def score_all(
        self, assessments: list[GovernanceAssessment] | None = None
    ) -> dict[str, Any]:
        targets = assessments if assessments is not None else self._assessments
        if not targets:
            return {
                "count": 0,
                "composite": 0.0,
                "per_dimension": {},
                "pass": False,
            }

        scores = [self.score_assessment(a) for a in targets]
        n = len(scores)

        per_dim = {
            "approval": round(sum(s.approval_score for s in scores) / n, 4),
            "blast_radius": round(sum(s.blast_radius_score for s in scores) / n, 4),
            "policy": round(sum(s.policy_score for s in scores) / n, 4),
            "audit": round(sum(s.audit_score for s in scores) / n, 4),
            "replay": round(sum(s.replay_score for s in scores) / n, 4),
        }
        composite = round(sum(s.composite for s in scores) / n, 4)

        human_required = [a for a in targets if a.human_approval_required]
        human_obtained = [a for a in human_required if a.human_approval_obtained]

        return {
            "count": n,
            "composite": composite,
            "per_dimension": per_dim,
            "pass": composite > 0.9 and per_dim["audit"] == 1.0,
            "human_approval_required_count": len(human_required),
            "human_approval_obtained_count": len(human_obtained),
            "human_gate_pass": len(human_required) == len(human_obtained),
            "scores": [s.to_dict() for s in scores],
        }

    def summary(self) -> dict[str, Any]:
        result = self.score_all()
        result.pop("scores", None)
        return result
