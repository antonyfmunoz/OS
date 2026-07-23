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
from typing import Any, Callable
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
    CONSISTENCY_SIGNAL = "consistency_signal"
    EFFICIENCY_SIGNAL = "efficiency_signal"
    QUALITY_SIGNAL = "quality_signal"
    DIVERSITY_SIGNAL = "diversity_signal"


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
            "signal_type": self.signal_type.value
            if isinstance(self.signal_type, SignalType)
            else self.signal_type,
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


@dataclass
class LearningSignalFeed:
    """Aggregated signal feed for governance decisions."""

    action_type: str = ""
    active_signals: list[LearningSignal] = field(default_factory=list)
    auto_approve_candidate: bool = False
    flag_for_optimization: bool = False
    block_auto_approval: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "action_type": self.action_type,
            "active_signals": [s.to_dict() for s in self.active_signals],
            "auto_approve_candidate": self.auto_approve_candidate,
            "flag_for_optimization": self.flag_for_optimization,
            "block_auto_approval": self.block_auto_approval,
        }


def _signal_feed_path() -> str:
    """Signal-feed home under the runtime-state root (Wave 0 boundary).

    Resolved lazily (UMH_STATE_DIR-aware) — the old module-level
    ``data/umh/learning`` repo path made every governed-spine submit fail on
    the Wave-1 candidate's read-only source mount (field run 20260722T165422Z:
    "spine submit failed for state_mutate: Read-only file system").
    """
    from substrate.state.runtime_paths import runtime_state_path

    return str(runtime_state_path("organism/learning", "signal_feed.jsonl"))


class OutcomeLearningLoop:
    """Tracks execution outcomes and derives learning signals."""

    def __init__(self, store_path: str | None = None):
        if store_path is None:
            from substrate.state.runtime_paths import runtime_state_path

            store_path = str(runtime_state_path("organism", "outcome_learning.jsonl"))
        self._store_path = store_path
        self._outcomes: list[OutcomeRecord] = []
        self._signals: list[LearningSignal] = []
        self._reliability: dict[str, float] = defaultdict(lambda: 0.5)
        self._outcome_counts: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
        self._seen_action_types: set[str] = set()
        self._degradation_callback: Callable[[str, float, list[LearningSignal]], None] | None = None
        self._degradation_threshold: float = 0.7
        self._degradation_fired: set[str] = set()
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
                        fields = {k: v for k, v in data.items() if k != "record_type"}
                        if "status" in fields and isinstance(fields["status"], str):
                            try:
                                fields["status"] = OutcomeStatus(fields["status"])
                            except ValueError:
                                logger.warning(
                                    "Skipping outcome record with unknown status: %s",
                                    fields.get("status"),
                                )
                                continue
                        rec = OutcomeRecord(**fields)
                        self._outcomes.append(rec)
                        self._outcome_counts[rec.action_type][rec.status.value] += 1
                        self._seen_action_types.add(rec.action_type)
                    elif data.get("record_type") == "signal":
                        sig_fields = {k: v for k, v in data.items() if k != "record_type"}
                        if "signal_type" in sig_fields and isinstance(
                            sig_fields["signal_type"], str
                        ):
                            try:
                                sig_fields["signal_type"] = SignalType(sig_fields["signal_type"])
                            except ValueError:
                                logger.warning(
                                    "Skipping signal with unknown type: %s",
                                    sig_fields.get("signal_type"),
                                )
                                continue
                        sig = LearningSignal(**sig_fields)
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
        quality = (
            1.0
            if outcome.status == OutcomeStatus.SUCCESS
            else (0.6 if outcome.status == OutcomeStatus.PARTIAL else 0.0)
        )

        eval_result = OutcomeEvaluation(
            outcome_id=outcome.id,
            success=success,
            quality_score=quality,
            notes=f"Status: {outcome.status.value}",
        )

        self._update_reliability(outcome.action_type, success)
        self._check_repeated_failures(outcome.action_type)
        self._check_consistency(outcome.action_type)
        self._check_efficiency(outcome.action_type, outcome.duration_seconds)
        self._check_quality(outcome.action_type)
        self._check_diversity(outcome.action_type)

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
        self._persist_record(
            {
                "record_type": "reliability",
                "action_type": action_type,
                "value": new,
            }
        )

    def register_degradation_callback(
        self,
        callback: Callable[[str, float, list[LearningSignal]], None],
        threshold: float = 0.7,
    ) -> None:
        """Register callback for reliability degradation (self-maintenance).

        Called when reliability drops below threshold after repeated failures.
        Args: action_type, current_reliability, recent_failure_signals.
        """
        self._degradation_callback = callback
        self._degradation_threshold = threshold

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

            reliability = self._reliability.get(action_type, 0.5)
            if (
                reliability < self._degradation_threshold
                and action_type not in self._degradation_fired
                and self._degradation_callback is not None
            ):
                self._degradation_fired.add(action_type)
                failure_signals = [
                    s
                    for s in self._signals[-20:]
                    if s.signal_type == SignalType.REPEATED_FAILURE and s.action_type == action_type
                ]
                try:
                    self._degradation_callback(action_type, reliability, failure_signals)
                except Exception as exc:
                    logger.debug("Degradation callback failed for %s: %s", action_type, exc)

    def _check_consistency(self, action_type: str) -> None:
        """Emit signal when last N outcomes of same type all share the same status."""
        recent = [o for o in self._outcomes if o.action_type == action_type][-5:]
        if len(recent) < 5:
            return
        statuses = {o.status for o in recent}
        if len(statuses) == 1:
            self._emit_signal(
                SignalType.CONSISTENCY_SIGNAL,
                action_type,
                f"Last 5 outcomes all {recent[0].status.value}",
                old_value=0.0,
                new_value=5.0,
                evidence=f"IDs: {[o.id for o in recent]}",
            )

    def _check_efficiency(self, action_type: str, duration: float) -> None:
        """Emit signal when execution duration is trending down (or up)."""
        recent = [
            o for o in self._outcomes if o.action_type == action_type and o.duration_seconds > 0
        ]
        if len(recent) < 6:
            return
        prev_avg = sum(o.duration_seconds for o in recent[-6:-3]) / 3
        curr_avg = sum(o.duration_seconds for o in recent[-3:]) / 3
        if prev_avg == 0:
            return
        delta_pct = (curr_avg - prev_avg) / prev_avg
        if abs(delta_pct) < 0.05:
            return
        improving = delta_pct < 0
        self._emit_signal(
            SignalType.EFFICIENCY_SIGNAL,
            action_type,
            f"Duration {'improved' if improving else 'degraded'} by {abs(delta_pct):.0%} ({prev_avg:.1f}s → {curr_avg:.1f}s)",
            old_value=prev_avg,
            new_value=curr_avg,
            evidence=f"{'faster' if improving else 'slower'} trend over last 6 outcomes",
        )

    def _check_quality(self, action_type: str) -> None:
        """Emit signal when quality score is trending up or down."""
        recent = [o for o in self._outcomes if o.action_type == action_type]
        if len(recent) < 6:
            return
        prev_q = [
            1.0
            if o.status == OutcomeStatus.SUCCESS
            else (0.6 if o.status == OutcomeStatus.PARTIAL else 0.0)
            for o in recent[-6:-3]
        ]
        curr_q = [
            1.0
            if o.status == OutcomeStatus.SUCCESS
            else (0.6 if o.status == OutcomeStatus.PARTIAL else 0.0)
            for o in recent[-3:]
        ]
        prev_avg = sum(prev_q) / 3
        curr_avg = sum(curr_q) / 3
        delta = curr_avg - prev_avg
        if abs(delta) < 0.1:
            return
        self._emit_signal(
            SignalType.QUALITY_SIGNAL,
            action_type,
            f"Quality {'improving' if delta > 0 else 'degrading'}: {prev_avg:.2f} → {curr_avg:.2f}",
            old_value=prev_avg,
            new_value=curr_avg,
            evidence="trend over last 6 outcomes",
        )

    def _check_diversity(self, action_type: str) -> None:
        """Emit signal when a new action type is seen for the first time."""
        if action_type in self._seen_action_types:
            return
        self._seen_action_types.add(action_type)
        self._emit_signal(
            SignalType.DIVERSITY_SIGNAL,
            action_type,
            f"New action type discovered: {action_type}",
            old_value=float(len(self._seen_action_types) - 1),
            new_value=float(len(self._seen_action_types)),
            evidence=f"Total action types now: {len(self._seen_action_types)}",
        )

    def _emit_signal(
        self,
        signal_type: SignalType,
        action_type: str,
        description: str,
        old_value: float,
        new_value: float,
        evidence: str,
    ) -> None:
        signal = LearningSignal(
            signal_type=signal_type,
            action_type=action_type,
            description=description,
            old_value=old_value,
            new_value=new_value,
            evidence=evidence,
        )
        self._signals.append(signal)
        sig_data = signal.to_dict()
        sig_data["record_type"] = "signal"
        self._persist_record(sig_data)

    def get_active_signals(
        self, action_type: str | None = None, min_confidence: float = 0.5
    ) -> list[LearningSignal]:
        """Return recent signals, optionally filtered by action type."""
        cutoff = time.time() - 86400  # last 24 hours
        result = [s for s in self._signals if s.generated_at >= cutoff]
        if action_type is not None:
            result = [s for s in result if s.action_type == action_type]
        return result

    def get_signal_feed(self, action_type: str) -> LearningSignalFeed:
        """Aggregate signals into a governance decision feed."""
        active = self.get_active_signals(action_type)
        reliability = self._reliability.get(action_type, 0.5)

        has_consistency = any(s.signal_type == SignalType.CONSISTENCY_SIGNAL for s in active)
        has_efficiency_degradation = any(
            s.signal_type == SignalType.EFFICIENCY_SIGNAL and s.new_value > s.old_value
            for s in active
        )
        has_quality_degradation = any(
            s.signal_type == SignalType.QUALITY_SIGNAL and s.new_value < s.old_value for s in active
        )

        feed = LearningSignalFeed(
            action_type=action_type,
            active_signals=active,
            auto_approve_candidate=has_consistency and reliability > 0.95,
            flag_for_optimization=has_efficiency_degradation,
            block_auto_approval=has_quality_degradation,
        )

        self._persist_signal_feed(feed)
        return feed

    def _persist_signal_feed(self, feed: LearningSignalFeed) -> None:
        # runtime_state_path creates the parent directory on resolution.
        with open(_signal_feed_path(), "a") as f:
            data = feed.to_dict()
            data["persisted_at"] = time.time()
            f.write(json.dumps(data, default=str) + "\n")

    def get_reliability(self, action_type: str) -> float:
        return self._reliability.get(action_type, 0.5)

    def reliability_history(self) -> dict[str, Any]:
        """Per-action-type reliability timeline from recorded outcomes.

        Returns a dict keyed by action_type, each containing:
          - current: current reliability score
          - sample_size: total outcomes for this type
          - timeline: list of {timestamp, status, cumulative_reliability}
        """
        history: dict[str, list[dict[str, Any]]] = defaultdict(list)
        running_counts: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))

        for outcome in self._outcomes:
            at = outcome.action_type
            running_counts[at][outcome.status.value] += 1
            total = sum(running_counts[at].values())
            successes = running_counts[at].get("success", 0) + running_counts[at].get("partial", 0)
            cumulative = successes / total if total > 0 else 0.5

            history[at].append(
                {
                    "timestamp": outcome.recorded_at,
                    "status": outcome.status.value,
                    "cumulative_reliability": round(cumulative, 4),
                }
            )

        result: dict[str, Any] = {}
        for at, timeline in history.items():
            result[at] = {
                "current": round(self._reliability.get(at, 0.5), 4),
                "sample_size": sum(self._outcome_counts[at].values()),
                "timeline": timeline,
            }

        return result

    def get_adjustments(self) -> list[RecommendationAdjustment]:
        """Recommend adjustments based on observed reliability."""
        adjustments = []
        for action_type, reliability in self._reliability.items():
            if reliability < 0.3:
                adjustments.append(
                    RecommendationAdjustment(
                        action_type=action_type,
                        current_reliability=reliability,
                        adjustment=-0.1,
                        reason=f"Low reliability ({reliability:.2f}) — consider demoting or fixing",
                    )
                )
            elif reliability > 0.9:
                adjustments.append(
                    RecommendationAdjustment(
                        action_type=action_type,
                        current_reliability=reliability,
                        adjustment=0.05,
                        reason=f"High reliability ({reliability:.2f}) — eligible for promotion",
                    )
                )
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
            "outcome_counts": {at: dict(counts) for at, counts in self._outcome_counts.items()},
            "pending_adjustments": len(self.get_adjustments()),
        }

    def to_dict(self) -> dict[str, Any]:
        return {
            "summary": self.summary(),
            "recent_outcomes": [o.to_dict() for o in self.recent_outcomes(10)],
            "recent_signals": [s.to_dict() for s in self.recent_signals(10)],
            "adjustments": [a.to_dict() for a in self.get_adjustments()],
        }

    def to_safe_dict(self) -> dict[str, Any]:
        """HTTP-safe serialization — strips internal evidence and error details."""
        safe_outcomes = []
        for o in self.recent_outcomes(10):
            safe_outcomes.append(
                {
                    "id": o.id,
                    "action_type": o.action_type,
                    "status": o.status.value if isinstance(o.status, OutcomeStatus) else o.status,
                    "duration_seconds": o.duration_seconds,
                    "recorded_at": o.recorded_at,
                }
            )
        safe_signals = []
        for s in self.recent_signals(10):
            safe_signals.append(
                {
                    "id": s.id,
                    "signal_type": s.signal_type.value
                    if isinstance(s.signal_type, SignalType)
                    else s.signal_type,
                    "action_type": s.action_type,
                    "description": s.description,
                    "generated_at": s.generated_at,
                }
            )
        return {
            "summary": self.summary(),
            "recent_outcomes": safe_outcomes,
            "recent_signals": safe_signals,
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
