"""Outcome Learning Loop — learn from execution outcomes.

Captures:
  1. What was recommended
  2. What was executed
  3. What happened
  4. Whether it worked
  5. What changed in the world model
  6. What should be adjusted

All tracking is deterministic. No LLM required.

UMH substrate subsystem. Instance-agnostic.
"""

from __future__ import annotations

import json
import logging
import os
import time
from collections import defaultdict
from dataclasses import dataclass, field
from enum import Enum
from typing import Any
from uuid import uuid4

logger = logging.getLogger(__name__)

_REPO_ROOT = os.environ.get("UMH_ROOT", "/opt/OS")


class OutcomeStatus(str, Enum):
    SUCCESS = "success"
    PARTIAL = "partial"
    FAILURE = "failure"
    TIMEOUT = "timeout"
    SKIPPED = "skipped"


class SignalType(str, Enum):
    RELIABILITY_UPDATE = "reliability_update"
    REPEATED_FAILURE = "repeated_failure"
    RECOMMENDATION_QUALITY = "recommendation_quality"
    PROMOTION_SIGNAL = "promotion_signal"
    DEMOTION_SIGNAL = "demotion_signal"
    WORLD_MODEL_UPDATE = "world_model_update"


@dataclass
class OutcomeRecord:
    id: str = field(default_factory=lambda: str(uuid4())[:8])
    action_type: str = ""
    plan_id: str = ""
    step_id: str = ""
    description: str = ""
    status: OutcomeStatus = OutcomeStatus.SUCCESS
    expected_result: str = ""
    actual_result: str = ""
    duration_seconds: float = 0.0
    error: str = ""
    recorded_at: float = field(default_factory=time.time)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "action_type": self.action_type,
            "plan_id": self.plan_id,
            "step_id": self.step_id,
            "description": self.description,
            "status": self.status.value,
            "expected_result": self.expected_result,
            "actual_result": self.actual_result,
            "duration_seconds": self.duration_seconds,
            "error": self.error,
            "recorded_at": self.recorded_at,
        }


@dataclass
class LearningSignal:
    id: str = field(default_factory=lambda: str(uuid4())[:8])
    signal_type: SignalType = SignalType.RELIABILITY_UPDATE
    action_type: str = ""
    description: str = ""
    old_value: float = 0.0
    new_value: float = 0.0
    evidence: str = ""
    generated_at: float = field(default_factory=time.time)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "signal_type": self.signal_type.value,
            "action_type": self.action_type,
            "description": self.description,
            "old_value": self.old_value,
            "new_value": self.new_value,
            "evidence": self.evidence,
            "generated_at": self.generated_at,
        }


@dataclass
class OutcomeEvaluation:
    outcome_id: str = ""
    success: bool = False
    quality_score: float = 0.0
    notes: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "outcome_id": self.outcome_id,
            "success": self.success,
            "quality_score": self.quality_score,
            "notes": self.notes,
        }


@dataclass
class RecommendationAdjustment:
    action_type: str = ""
    current_reliability: float = 0.0
    adjustment: float = 0.0
    reason: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "action_type": self.action_type,
            "current_reliability": self.current_reliability,
            "adjustment": self.adjustment,
            "new_reliability": max(0.0, min(1.0, self.current_reliability + self.adjustment)),
            "reason": self.reason,
        }


@dataclass
class ReliabilityUpdate:
    action_type: str = ""
    old_reliability: float = 0.5
    new_reliability: float = 0.5
    sample_size: int = 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "action_type": self.action_type,
            "old_reliability": round(self.old_reliability, 3),
            "new_reliability": round(self.new_reliability, 3),
            "sample_size": self.sample_size,
        }


class OutcomeLearningLoop:
    """Tracks execution outcomes and derives learning signals."""

    def __init__(self, store_path: str | None = None):
        self._store_path = store_path or os.path.join(
            _REPO_ROOT, "data", "umh", "organism", "outcome_learning.jsonl"
        )
        self._outcomes: list[OutcomeRecord] = []
        self._signals: list[LearningSignal] = []
        self._reliability: dict[str, float] = defaultdict(lambda: 0.5)
        self._outcome_counts: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
        self._load()

    def _load(self) -> None:
        if not os.path.isfile(self._store_path):
            return
        try:
            with open(self._store_path) as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    data = json.loads(line)
                    if data.get("record_type") == "outcome":
                        rec = OutcomeRecord(**{k: v for k, v in data.items() if k != "record_type"})
                        self._outcomes.append(rec)
                        self._outcome_counts[rec.action_type][rec.status.value if isinstance(rec.status, OutcomeStatus) else rec.status] += 1
                    elif data.get("record_type") == "signal":
                        sig = LearningSignal(**{k: v for k, v in data.items() if k != "record_type"})
                        self._signals.append(sig)
                    elif data.get("record_type") == "reliability":
                        self._reliability[data["action_type"]] = data["value"]
        except (json.JSONDecodeError, OSError) as e:
            logger.warning("Failed to load outcome learning data: %s", e)

    def _persist_record(self, data: dict) -> None:
        os.makedirs(os.path.dirname(self._store_path), exist_ok=True)
        with open(self._store_path, "a") as f:
            f.write(json.dumps(data, default=str) + "\n")

    def record_outcome(self, outcome: OutcomeRecord) -> OutcomeEvaluation:
        """Record an execution outcome and evaluate it."""
        self._outcomes.append(outcome)
        self._outcome_counts[outcome.action_type][outcome.status.value] += 1

        data = outcome.to_dict()
        data["record_type"] = "outcome"
        self._persist_record(data)

        success = outcome.status in (OutcomeStatus.SUCCESS, OutcomeStatus.PARTIAL)
        quality = 1.0 if outcome.status == OutcomeStatus.SUCCESS else (
            0.6 if outcome.status == OutcomeStatus.PARTIAL else 0.0
        )

        eval_result = OutcomeEvaluation(
            outcome_id=outcome.id,
            success=success,
            quality_score=quality,
            notes=f"Status: {outcome.status.value}",
        )

        self._update_reliability(outcome.action_type, success)
        self._check_repeated_failures(outcome.action_type)

        return eval_result

    def _update_reliability(self, action_type: str, success: bool) -> None:
        old = self._reliability[action_type]
        counts = self._outcome_counts[action_type]
        total = sum(counts.values())
        success_count = counts.get("success", 0) + counts.get("partial", 0)
        new = success_count / total if total > 0 else 0.5

        if abs(new - old) > 0.01:
            signal = LearningSignal(
                signal_type=SignalType.RELIABILITY_UPDATE,
                action_type=action_type,
                description=f"Reliability updated from {old:.3f} to {new:.3f}",
                old_value=old,
                new_value=new,
                evidence=f"{success_count}/{total} successful outcomes",
            )
            self._signals.append(signal)
            sig_data = signal.to_dict()
            sig_data["record_type"] = "signal"
            self._persist_record(sig_data)

        self._reliability[action_type] = new
        self._persist_record({
            "record_type": "reliability",
            "action_type": action_type,
            "value": new,
        })

    def _check_repeated_failures(self, action_type: str) -> None:
        recent = [o for o in self._outcomes[-20:] if o.action_type == action_type]
        recent_failures = [o for o in recent if o.status == OutcomeStatus.FAILURE]

        if len(recent_failures) >= 3:
            signal = LearningSignal(
                signal_type=SignalType.REPEATED_FAILURE,
                action_type=action_type,
                description=f"Repeated failures detected: {len(recent_failures)} in last {len(recent)} attempts",
                old_value=0.0,
                new_value=float(len(recent_failures)),
                evidence=f"Failure IDs: {[f.id for f in recent_failures[-3:]]}",
            )
            self._signals.append(signal)
            sig_data = signal.to_dict()
            sig_data["record_type"] = "signal"
            self._persist_record(sig_data)

    def get_reliability(self, action_type: str) -> float:
        return self._reliability.get(action_type, 0.5)

    def get_adjustments(self) -> list[RecommendationAdjustment]:
        """Recommend adjustments based on observed reliability."""
        adjustments = []
        for action_type, reliability in self._reliability.items():
            if reliability < 0.3:
                adjustments.append(RecommendationAdjustment(
                    action_type=action_type,
                    current_reliability=reliability,
                    adjustment=-0.1,
                    reason=f"Low reliability ({reliability:.2f}) — consider demoting or fixing",
                ))
            elif reliability > 0.9:
                adjustments.append(RecommendationAdjustment(
                    action_type=action_type,
                    current_reliability=reliability,
                    adjustment=0.05,
                    reason=f"High reliability ({reliability:.2f}) — eligible for promotion",
                ))
        return adjustments

    def recent_outcomes(self, limit: int = 20) -> list[OutcomeRecord]:
        return self._outcomes[-limit:]

    def recent_signals(self, limit: int = 20) -> list[LearningSignal]:
        return self._signals[-limit:]

    def summary(self) -> dict[str, Any]:
        return {
            "total_outcomes": len(self._outcomes),
            "total_signals": len(self._signals),
            "reliability_scores": {k: round(v, 3) for k, v in self._reliability.items()},
            "outcome_counts": {
                at: dict(counts) for at, counts in self._outcome_counts.items()
            },
            "pending_adjustments": len(self.get_adjustments()),
        }

    def to_dict(self) -> dict[str, Any]:
        return {
            "summary": self.summary(),
            "recent_outcomes": [o.to_dict() for o in self.recent_outcomes(10)],
            "recent_signals": [s.to_dict() for s in self.recent_signals(10)],
            "adjustments": [a.to_dict() for a in self.get_adjustments()],
        }


if __name__ == "__main__":
    import sys
    sys.path.insert(0, _REPO_ROOT)
    import tempfile

    with tempfile.NamedTemporaryFile(suffix=".jsonl", delete=False) as f:
        path = f.name

    loop = OutcomeLearningLoop(store_path=path)

    for i in range(5):
        outcome = OutcomeRecord(
            action_type="run_probes",
            description=f"Probe execution #{i}",
            status=OutcomeStatus.SUCCESS if i < 4 else OutcomeStatus.FAILURE,
        )
        loop.record_outcome(outcome)

    print(json.dumps(loop.summary(), indent=2))
    print(f"\nReliability for run_probes: {loop.get_reliability('run_probes'):.3f}")
    adjustments = loop.get_adjustments()
    for adj in adjustments:
        print(f"  Adjustment: {adj.action_type} → {adj.reason}")

    os.unlink(path)
