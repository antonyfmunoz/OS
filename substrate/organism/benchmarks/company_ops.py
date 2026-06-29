"""Company Operations Scorer — Benchmark F for C33.

Scores whether UMH can govern real business operations across
registered projections. Measures automation ratio, governance
coverage, proof generation, and correctness of external-facing
actions.

All scoring is deterministic. No LLM calls.
Projection-agnostic — company names are runtime data, not code.

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
    _REPO_ROOT, "data", "umh", "c33", "company_ops_tasks.jsonl"
)

VALID_COMPANIES: set[str] = set()  # populated at runtime from projection registry
VALID_OPS = {
    "outreach", "crm", "proposal", "research", "publishing",
    "coaching", "missions", "reviews", "communities", "demand_signals",
    "fulfillment", "reporting", "opportunity", "work_packets",
}
VALID_SURFACES = {"cockpit", "discord", "cli", "manual", "mobile", "voice", "api"}
VALID_OUTCOMES = {"completed", "partial", "failed"}


@dataclass
class CompanyOpsTask:
    task_id: str = field(default_factory=lambda: f"ops-{uuid4().hex[:8]}")
    company: str = ""
    operation_type: str = ""
    task_description: str = ""
    timestamp: float = field(default_factory=time.time)

    started_via: str = ""
    completed_via: str = ""

    required_human_steps: int = 0
    automated_steps: int = 0
    total_steps: int = 0

    outcome: str = "completed"
    time_seconds: float = 0.0

    governance_applied: bool = False
    proof_generated: bool = False
    external_facing: bool = False
    data_loss: bool = False

    envelope_ids: list[str] = field(default_factory=list)
    notes: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> CompanyOpsTask:
        fields = {k: v for k, v in d.items() if k in cls.__dataclass_fields__}
        return cls(**fields)


@dataclass
class CompanyOpsScore:
    task_id: str = ""
    automation_ratio: float = 0.0
    governance_score: float = 0.0
    proof_score: float = 0.0
    outcome_score: float = 0.0
    safety_score: float = 0.0
    composite: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class CompanyOpsScorer:
    """Scores company operation tasks run through UMH governance."""

    def __init__(self, store_path: str = _STORE_PATH) -> None:
        self._path = store_path
        self._tasks: list[CompanyOpsTask] = []
        self._scores: list[CompanyOpsScore] = []
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
                        self._tasks.append(CompanyOpsTask.from_dict(d))
                    except (json.JSONDecodeError, TypeError) as exc:
                        logger.debug("Skip malformed company ops line: %s", exc)
        except OSError as exc:
            logger.debug("Cannot read %s: %s", self._path, exc)

    def _persist(self, task: CompanyOpsTask) -> None:
        os.makedirs(os.path.dirname(self._path), exist_ok=True)
        with open(self._path, "a") as f:
            f.write(json.dumps(task.to_dict(), default=str) + "\n")

    def record_task(self, task: CompanyOpsTask) -> CompanyOpsScore:
        if task.total_steps == 0:
            task.total_steps = task.required_human_steps + task.automated_steps
        self._tasks.append(task)
        self._persist(task)
        score = self.score_task(task)
        self._scores.append(score)
        return score

    def score_task(self, task: CompanyOpsTask) -> CompanyOpsScore:
        total = task.total_steps or (task.required_human_steps + task.automated_steps)
        automation = task.automated_steps / total if total > 0 else 0.0

        if task.external_facing:
            governance = 1.0 if task.governance_applied else 0.0
        else:
            governance = 1.0 if task.governance_applied else 0.5

        if task.external_facing:
            proof = 1.0 if task.proof_generated else 0.0
        else:
            proof = 1.0 if task.proof_generated else 0.5

        outcome_map = {"completed": 1.0, "partial": 0.5, "failed": 0.0}
        outcome = outcome_map.get(task.outcome, 0.0)

        safety = 0.0 if task.data_loss else 1.0

        composite = (
            automation * 0.20
            + governance * 0.25
            + proof * 0.20
            + outcome * 0.20
            + safety * 0.15
        )

        return CompanyOpsScore(
            task_id=task.task_id,
            automation_ratio=round(automation, 4),
            governance_score=governance,
            proof_score=proof,
            outcome_score=outcome,
            safety_score=safety,
            composite=round(composite, 4),
        )

    def score_all(
        self, tasks: list[CompanyOpsTask] | None = None
    ) -> dict[str, Any]:
        targets = tasks if tasks is not None else self._tasks
        if not targets:
            return {
                "count": 0,
                "composite": 0.0,
                "per_dimension": {},
                "pass": False,
            }

        scores = [self.score_task(t) for t in targets]
        n = len(scores)

        per_dim = {
            "automation": round(sum(s.automation_ratio for s in scores) / n, 4),
            "governance": round(sum(s.governance_score for s in scores) / n, 4),
            "proof": round(sum(s.proof_score for s in scores) / n, 4),
            "outcome": round(sum(s.outcome_score for s in scores) / n, 4),
            "safety": round(sum(s.safety_score for s in scores) / n, 4),
        }
        composite = round(sum(s.composite for s in scores) / n, 4)

        primarily_umh = sum(
            1 for t in targets
            if t.automated_steps > t.required_human_steps
        )

        external = [t for t in targets if t.external_facing]
        external_governed = [t for t in external if t.governance_applied]
        external_proofed = [t for t in external if t.proof_generated]

        by_company: dict[str, int] = {}
        for t in targets:
            by_company[t.company] = by_company.get(t.company, 0) + 1

        return {
            "count": n,
            "composite": composite,
            "per_dimension": per_dim,
            "primarily_umh_count": primarily_umh,
            "primarily_umh_ratio": round(primarily_umh / n, 4),
            "pass": primarily_umh >= 3 and per_dim["safety"] == 1.0,
            "external_facing_count": len(external),
            "external_governed_count": len(external_governed),
            "external_proofed_count": len(external_proofed),
            "by_company": by_company,
            "data_loss_events": sum(1 for t in targets if t.data_loss),
            "scores": [s.to_dict() for s in scores],
        }

    def summary(self) -> dict[str, Any]:
        result = self.score_all()
        result.pop("scores", None)
        return result
