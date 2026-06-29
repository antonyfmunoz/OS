"""Orchestration Quality Scorer — Benchmark C for C33.

Scores whether UMH made correct orchestration decisions:
  - harness selection (Claude Code, Playwright, Computer Use, etc.)
  - model routing (opus, sonnet, haiku)
  - adapter selection
  - task decomposition
  - failure recovery
  - verification method

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
    _REPO_ROOT, "data", "umh", "c33", "orchestration_decisions.jsonl"
)

# Dimension weights for composite score
_WEIGHTS = {
    "harness": 0.25,
    "model": 0.15,
    "adapter": 0.15,
    "decomposition": 0.15,
    "recovery": 0.15,
    "verification": 0.15,
}


@dataclass
class OrchestrationDecision:
    decision_id: str = field(default_factory=lambda: f"orch-{uuid4().hex[:8]}")
    task_description: str = ""
    cycle_id: str = ""
    benchmark_type: str = ""
    timestamp: float = field(default_factory=time.time)

    harness_selected: str = ""
    harness_expected: str = ""
    harness_correct: bool = False

    model_selected: str = ""
    model_expected: str = ""
    model_correct: bool = False

    adapter_selected: str = ""
    adapter_expected: str = ""
    adapter_correct: bool = False

    decomposition_steps: int = 0
    decomposition_expected_steps: int = 0
    decomposition_correct: bool = False

    recovery_attempted: bool = False
    recovery_succeeded: bool = False
    recovery_needed: bool = False

    verification_method: str = ""
    verification_expected: str = ""
    verification_correct: bool = False

    notes: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> OrchestrationDecision:
        fields = {k: v for k, v in d.items() if k in cls.__dataclass_fields__}
        return cls(**fields)


@dataclass
class OrchestrationScore:
    decision_id: str = ""
    harness_score: float = 0.0
    model_score: float = 0.0
    adapter_score: float = 0.0
    decomposition_score: float = 0.0
    recovery_score: float = 0.0
    verification_score: float = 0.0
    composite: float = 0.0
    is_critical_misroute: bool = False

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class OrchestrationQualityScorer:
    """Scores orchestration decisions from governed execution."""

    def __init__(self, store_path: str = _STORE_PATH) -> None:
        self._path = store_path
        self._decisions: list[OrchestrationDecision] = []
        self._scores: list[OrchestrationScore] = []
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
                        self._decisions.append(OrchestrationDecision.from_dict(d))
                    except (json.JSONDecodeError, TypeError) as exc:
                        logger.debug("Skip malformed orchestration line: %s", exc)
        except OSError as exc:
            logger.debug("Cannot read %s: %s", self._path, exc)

    def _persist(self, decision: OrchestrationDecision) -> None:
        os.makedirs(os.path.dirname(self._path), exist_ok=True)
        with open(self._path, "a") as f:
            f.write(json.dumps(decision.to_dict(), default=str) + "\n")

    def record_decision(self, decision: OrchestrationDecision) -> OrchestrationScore:
        self._decisions.append(decision)
        self._persist(decision)
        score = self.score_decision(decision)
        self._scores.append(score)
        return score

    def score_decision(self, decision: OrchestrationDecision) -> OrchestrationScore:
        harness = 1.0 if decision.harness_correct else 0.0
        model = 1.0 if decision.model_correct else 0.0
        adapter = 1.0 if decision.adapter_correct else 0.0
        decomp = 1.0 if decision.decomposition_correct else 0.0

        if decision.recovery_needed:
            recovery = 1.0 if decision.recovery_succeeded else 0.0
        elif decision.recovery_attempted and not decision.recovery_needed:
            recovery = 0.5
        else:
            recovery = 1.0

        verification = 1.0 if decision.verification_correct else 0.0

        composite = (
            harness * _WEIGHTS["harness"]
            + model * _WEIGHTS["model"]
            + adapter * _WEIGHTS["adapter"]
            + decomp * _WEIGHTS["decomposition"]
            + recovery * _WEIGHTS["recovery"]
            + verification * _WEIGHTS["verification"]
        )

        is_critical = not decision.harness_correct and decision.harness_selected != ""

        return OrchestrationScore(
            decision_id=decision.decision_id,
            harness_score=harness,
            model_score=model,
            adapter_score=adapter,
            decomposition_score=decomp,
            recovery_score=recovery,
            verification_score=verification,
            composite=round(composite, 4),
            is_critical_misroute=is_critical,
        )

    def score_all(
        self, decisions: list[OrchestrationDecision] | None = None
    ) -> dict[str, Any]:
        targets = decisions if decisions is not None else self._decisions
        if not targets:
            return {
                "count": 0,
                "composite": 0.0,
                "per_dimension": {},
                "critical_misroutes": 0,
                "pass": False,
            }

        scores = [self.score_decision(d) for d in targets]
        n = len(scores)

        per_dim = {
            "harness": round(sum(s.harness_score for s in scores) / n, 4),
            "model": round(sum(s.model_score for s in scores) / n, 4),
            "adapter": round(sum(s.adapter_score for s in scores) / n, 4),
            "decomposition": round(sum(s.decomposition_score for s in scores) / n, 4),
            "recovery": round(sum(s.recovery_score for s in scores) / n, 4),
            "verification": round(sum(s.verification_score for s in scores) / n, 4),
        }
        composite = round(sum(s.composite for s in scores) / n, 4)
        critical = sum(1 for s in scores if s.is_critical_misroute)

        return {
            "count": n,
            "composite": composite,
            "per_dimension": per_dim,
            "critical_misroutes": critical,
            "pass": composite > 0.75 and critical == 0,
            "recovery_success_rate": round(
                sum(s.recovery_score for s in scores) / n, 4
            ),
            "scores": [s.to_dict() for s in scores],
        }

    def summary(self) -> dict[str, Any]:
        result = self.score_all()
        result.pop("scores", None)
        return result
