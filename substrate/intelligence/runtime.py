"""Proprietary Intelligence Runtime — the system's learned intelligence.

Not an LLM wrapper. This is the system's own accumulated intelligence:
pattern recognition, decision heuristics, and predictive models built
from its operational history.

Three intelligence layers:
  1. Pattern Intelligence — what patterns recur in this org's operations
  2. Decision Intelligence — what decisions led to good/bad outcomes
  3. Predictive Intelligence — what's likely to happen next given context

All deterministic-first. LLM calls are optional escalation for
novel situations the heuristic engine hasn't seen before.
"""

from __future__ import annotations

import json
import logging
import time
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class LearnedPattern:
    """A pattern the system has learned from its operational history."""

    pattern_id: str
    description: str
    trigger_conditions: list[str]
    predicted_outcome: str
    confidence: float = 0.5
    observation_count: int = 0
    success_count: int = 0
    failure_count: int = 0
    last_seen: str = ""
    domain: str = "general"

    def success_rate(self) -> float:
        total = self.success_count + self.failure_count
        return self.success_count / total if total > 0 else 0.5

    def to_dict(self) -> dict[str, Any]:
        return {
            "pattern_id": self.pattern_id,
            "description": self.description,
            "trigger_conditions": self.trigger_conditions,
            "predicted_outcome": self.predicted_outcome,
            "confidence": round(self.confidence, 3),
            "observation_count": self.observation_count,
            "success_rate": round(self.success_rate(), 3),
            "last_seen": self.last_seen,
            "domain": self.domain,
        }


@dataclass
class DecisionRecord:
    """A recorded decision and its outcome."""

    decision_id: str
    context_summary: str
    action_taken: str
    outcome: str
    success: bool
    contributing_factors: list[str] = field(default_factory=list)
    timestamp: str = ""

    def __post_init__(self) -> None:
        if not self.timestamp:
            self.timestamp = datetime.now(timezone.utc).isoformat()


@dataclass
class Prediction:
    """A prediction about what will happen."""

    prediction: str
    confidence: float
    basis: str
    patterns_used: list[str] = field(default_factory=list)


class PatternIntelligence:
    """Learns recurring patterns from operational history."""

    def __init__(self, store_path: str = "data/umh/intelligence/patterns.json") -> None:
        self._store_path = Path(store_path)
        self._store_path.parent.mkdir(parents=True, exist_ok=True)
        self._patterns: dict[str, LearnedPattern] = {}
        self._load()

    def _load(self) -> None:
        if self._store_path.exists():
            try:
                data = json.loads(self._store_path.read_text())
                for p in data.get("patterns", []):
                    lp = LearnedPattern(
                        **{k: v for k, v in p.items() if k in LearnedPattern.__dataclass_fields__}
                    )
                    self._patterns[lp.pattern_id] = lp
            except (json.JSONDecodeError, KeyError):
                pass

    def _save(self) -> None:
        data = {"patterns": [p.to_dict() for p in self._patterns.values()]}
        self._store_path.write_text(json.dumps(data, indent=2))

    def record_observation(
        self,
        content: str,
        outcome: str,
        success: bool,
        domain: str = "general",
    ) -> LearnedPattern | None:
        """Record an observation and update or create patterns."""
        words = content.lower().split()[:10]
        trigger_key = "_".join(sorted(words[:5]))
        pattern_id = f"p_{trigger_key[:40]}"

        if pattern_id in self._patterns:
            pattern = self._patterns[pattern_id]
            pattern.observation_count += 1
            if success:
                pattern.success_count += 1
            else:
                pattern.failure_count += 1
            pattern.confidence = pattern.success_rate()
            pattern.last_seen = datetime.now(timezone.utc).isoformat()
        else:
            pattern = LearnedPattern(
                pattern_id=pattern_id,
                description=f"Pattern from: {content[:100]}",
                trigger_conditions=words[:5],
                predicted_outcome=outcome,
                confidence=0.5,
                observation_count=1,
                success_count=1 if success else 0,
                failure_count=0 if success else 1,
                last_seen=datetime.now(timezone.utc).isoformat(),
                domain=domain,
            )
            self._patterns[pattern_id] = pattern

        self._save()
        return pattern

    def match_patterns(self, content: str, min_confidence: float = 0.3) -> list[LearnedPattern]:
        """Find patterns that match the given content."""
        content_lower = content.lower()
        matches: list[tuple[float, LearnedPattern]] = []

        for pattern in self._patterns.values():
            if pattern.confidence < min_confidence:
                continue

            hit_count = sum(1 for trigger in pattern.trigger_conditions if trigger in content_lower)
            if hit_count > 0:
                score = (hit_count / len(pattern.trigger_conditions)) * pattern.confidence
                matches.append((score, pattern))

        matches.sort(key=lambda x: x[0], reverse=True)
        return [p for _, p in matches[:10]]

    def stats(self) -> dict[str, Any]:
        return {
            "total_patterns": len(self._patterns),
            "high_confidence": sum(1 for p in self._patterns.values() if p.confidence > 0.7),
            "low_confidence": sum(1 for p in self._patterns.values() if p.confidence < 0.3),
            "domains": dict(Counter(p.domain for p in self._patterns.values())),
        }


class DecisionIntelligence:
    """Learns from decision outcomes to improve future decisions."""

    def __init__(self, store_path: str = "data/umh/intelligence/decisions.jsonl") -> None:
        self._store_path = Path(store_path)
        self._store_path.parent.mkdir(parents=True, exist_ok=True)
        self._records: list[DecisionRecord] = []
        self._outcome_counts: dict[str, Counter] = defaultdict(Counter)
        self._load()

    def _load(self) -> None:
        if not self._store_path.exists():
            return
        try:
            with open(self._store_path) as f:
                for line in f:
                    line = line.strip()
                    if line:
                        data = json.loads(line)
                        record = DecisionRecord(
                            **{
                                k: v
                                for k, v in data.items()
                                if k in DecisionRecord.__dataclass_fields__
                            }
                        )
                        self._records.append(record)
                        self._outcome_counts[record.action_taken][
                            "success" if record.success else "failure"
                        ] += 1
        except (json.JSONDecodeError, OSError):
            pass

    def record_decision(
        self,
        decision_id: str,
        context: str,
        action: str,
        outcome: str,
        success: bool,
        factors: list[str] | None = None,
    ) -> None:
        """Record a decision and its outcome."""
        record = DecisionRecord(
            decision_id=decision_id,
            context_summary=context[:300],
            action_taken=action,
            outcome=outcome,
            success=success,
            contributing_factors=factors or [],
        )
        self._records.append(record)
        self._outcome_counts[action]["success" if success else "failure"] += 1

        try:
            with open(self._store_path, "a") as f:
                f.write(
                    json.dumps(
                        {
                            "decision_id": record.decision_id,
                            "context_summary": record.context_summary,
                            "action_taken": record.action_taken,
                            "outcome": record.outcome,
                            "success": record.success,
                            "contributing_factors": record.contributing_factors,
                            "timestamp": record.timestamp,
                        },
                        separators=(",", ":"),
                    )
                    + "\n"
                )
        except OSError as e:
            logger.warning("decision record write failed: %s", e)

    def action_success_rate(self, action: str) -> float:
        """What's the historical success rate for this type of action?"""
        counts = self._outcome_counts.get(action)
        if not counts:
            return 0.5
        total = counts["success"] + counts["failure"]
        return counts["success"] / total if total > 0 else 0.5

    def recommend(self, context: str) -> list[dict[str, Any]]:
        """Recommend actions based on historical success rates."""
        context_lower = context.lower()
        scored: list[dict[str, Any]] = []

        for action, counts in self._outcome_counts.items():
            total = counts["success"] + counts["failure"]
            if total < 2:
                continue
            rate = counts["success"] / total
            relevance = sum(1 for w in action.lower().split() if w in context_lower)
            if relevance > 0:
                scored.append(
                    {
                        "action": action,
                        "success_rate": round(rate, 3),
                        "total_observations": total,
                        "relevance_score": relevance,
                    }
                )

        scored.sort(key=lambda x: x["success_rate"] * x["relevance_score"], reverse=True)
        return scored[:5]

    def stats(self) -> dict[str, Any]:
        total = len(self._records)
        successes = sum(1 for r in self._records if r.success)
        return {
            "total_decisions": total,
            "success_count": successes,
            "failure_count": total - successes,
            "overall_success_rate": round(successes / total, 3) if total > 0 else 0.0,
            "unique_actions": len(self._outcome_counts),
        }


NOVEL_SITUATION_THRESHOLD = 0.4


class PredictiveIntelligence:
    """Predicts outcomes based on pattern and decision intelligence.

    When heuristic confidence is below NOVEL_SITUATION_THRESHOLD (no matching
    patterns), escalates to LLM for reasoning about the novel situation.
    The LLM prediction is recorded as a new learned pattern.
    """

    def __init__(
        self,
        pattern_engine: PatternIntelligence | None = None,
        decision_engine: DecisionIntelligence | None = None,
    ) -> None:
        self._patterns = pattern_engine or PatternIntelligence()
        self._decisions = decision_engine or DecisionIntelligence()

    def _ai_predict(self, content: str, action: str) -> Prediction | None:
        """Escalate to LLM for novel situation reasoning."""
        try:
            from adapters.models.model_router import call_with_fallback

            action_ctx = f"\nPlanned action: {action}" if action else ""
            result = call_with_fallback(
                prompt=(
                    f"Predict the outcome of this situation:\n\n"
                    f"{content[:800]}{action_ctx}\n\n"
                    "No historical patterns exist for this situation."
                ),
                system=(
                    "You are UMH's predictive intelligence engine. Given a novel situation "
                    "with no historical patterns, predict the likely outcome.\n"
                    'Return JSON: {"prediction": "success|failure|partial|unknown", '
                    '"confidence": 0.0-1.0, "reasoning": "..."}\n'
                    "Return ONLY valid JSON."
                ),
                task_type="analysis",
            )
            if not result.output:
                return None
            text = result.output.strip()
            if text.startswith("```"):
                text = text.split("\n", 1)[-1].rsplit("```", 1)[0].strip()
            parsed = json.loads(text)
            pred = parsed.get("prediction", "unknown")
            conf = parsed.get("confidence", 0.5)
            reasoning = parsed.get("reasoning", "")
            logger.info("AI prediction for novel situation: %s (%.2f)", pred, conf)
            return Prediction(
                prediction=pred,
                confidence=round(conf, 3),
                basis=f"[AI reasoning] {reasoning[:200]}",
                patterns_used=[],
            )
        except Exception as e:
            logger.debug("AI prediction failed (keeping heuristic): %s", e)
            return None

    def predict(self, content: str, action: str = "") -> Prediction:
        """Predict the outcome of a given action in a given context."""
        matched = self._patterns.match_patterns(content)

        if matched:
            best = matched[0]
            confidence = best.confidence
            prediction = best.predicted_outcome
            basis = (
                f"Matched pattern: {best.description[:100]} ({best.observation_count} observations)"
            )
            pattern_ids = [p.pattern_id for p in matched[:3]]
        else:
            confidence = 0.3
            prediction = "unknown"
            basis = "No historical patterns matched"
            pattern_ids = []

        if action:
            action_rate = self._decisions.action_success_rate(action)
            if action_rate != 0.5:
                confidence = (confidence + action_rate) / 2
                basis += f" | Action '{action}' historical success rate: {action_rate:.1%}"

        if confidence < NOVEL_SITUATION_THRESHOLD and len(content.strip()) > 20:
            ai_pred = self._ai_predict(content, action)
            if ai_pred and ai_pred.confidence > confidence:
                return ai_pred

        return Prediction(
            prediction=prediction,
            confidence=round(confidence, 3),
            basis=basis,
            patterns_used=pattern_ids,
        )


class IntelligenceRuntime:
    """Unified interface to the proprietary intelligence system."""

    def __init__(self) -> None:
        self.patterns = PatternIntelligence()
        self.decisions = DecisionIntelligence()
        self.predictions = PredictiveIntelligence(self.patterns, self.decisions)

    def learn_from_execution(
        self,
        content: str,
        action: str,
        outcome: str,
        success: bool,
        domain: str = "general",
    ) -> dict[str, Any]:
        """Record an execution outcome for learning."""
        pattern = self.patterns.record_observation(content, outcome, success, domain)
        self.decisions.record_decision(
            decision_id=f"d_{int(time.time())}",
            context=content,
            action=action,
            outcome=outcome,
            success=success,
        )
        return {
            "pattern_updated": pattern.pattern_id if pattern else None,
            "pattern_confidence": pattern.confidence if pattern else None,
        }

    def predict_outcome(self, content: str, action: str = "") -> dict[str, Any]:
        """Predict what will happen for a given action."""
        prediction = self.predictions.predict(content, action)
        return {
            "prediction": prediction.prediction,
            "confidence": prediction.confidence,
            "basis": prediction.basis,
            "patterns_used": prediction.patterns_used,
        }

    def health(self) -> dict[str, Any]:
        return {
            "pattern_stats": self.patterns.stats(),
            "decision_stats": self.decisions.stats(),
        }
