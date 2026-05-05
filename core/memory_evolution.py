"""Memory Evolution System — adaptive learning from execution history.

Stores execution runs at the primitive level, detects patterns across
runs, and suggests optimizations.  Feeds back into the transformer
to improve future compositions.

This is NOT a log store.  It operates on primitives — which combinations
work, which fail, which transform into success.

Usage:
    from core.memory_evolution import MemorySystem

    mem = MemorySystem()
    mem.record_run(pipeline_result, feedback_signal, tags)
    patterns = mem.extract_patterns()
    ranked = mem.rank_patterns()
    suggestions = mem.suggest_optimizations()
"""

from __future__ import annotations

import json
import time
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from core.primitives import PrimitiveTag


# ---------------------------------------------------------------------------
# Run record
# ---------------------------------------------------------------------------


@dataclass
class RunRecord:
    """A single execution run recorded at the primitive level."""

    run_id: str
    timestamp: float
    intent: str
    domain_type: str
    primitive_tags: frozenset[PrimitiveTag]
    success_score: float  # 0.0-1.0
    pipeline_ok: bool
    objective_score: float | None = None  # from objective evaluation
    transformation_applied: bool = False
    transformed_from: frozenset[PrimitiveTag] | None = None
    step_scores: dict[str, float] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "run_id": self.run_id,
            "timestamp": self.timestamp,
            "intent": self.intent,
            "domain_type": self.domain_type,
            "primitive_tags": sorted(t.value for t in self.primitive_tags),
            "success_score": round(self.success_score, 4),
            "pipeline_ok": self.pipeline_ok,
            "objective_score": (
                round(self.objective_score, 4)
                if self.objective_score is not None
                else None
            ),
            "transformation_applied": self.transformation_applied,
            "transformed_from": (
                sorted(t.value for t in self.transformed_from)
                if self.transformed_from
                else None
            ),
            "step_scores": {k: round(v, 4) for k, v in self.step_scores.items()},
            "metadata": self.metadata,
        }


# ---------------------------------------------------------------------------
# Pattern detection
# ---------------------------------------------------------------------------


@dataclass
class PrimitivePattern:
    """A recurring primitive combination with performance statistics."""

    tags: frozenset[PrimitiveTag]
    occurrences: int
    avg_score: float
    success_rate: float  # fraction of runs where pipeline_ok
    domains: list[str]  # which domain types use this combination
    best_score: float = 0.0
    worst_score: float = 1.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "tags": sorted(t.value for t in self.tags),
            "occurrences": self.occurrences,
            "avg_score": round(self.avg_score, 4),
            "success_rate": round(self.success_rate, 4),
            "domains": self.domains,
            "best_score": round(self.best_score, 4),
            "worst_score": round(self.worst_score, 4),
        }


# ---------------------------------------------------------------------------
# Memory system
# ---------------------------------------------------------------------------

_PERSIST_DIR = Path("/opt/OS/logs/memory_evolution")


class MemorySystem:
    """Adaptive memory that learns from primitive-level execution history.

    Operates entirely on primitives — not logs, not raw output.
    Detects which primitive combinations succeed and suggests
    improvements for future compositions.
    """

    def __init__(self, persist: bool = True) -> None:
        self._runs: list[RunRecord] = []
        self._persist = persist
        if persist:
            _PERSIST_DIR.mkdir(parents=True, exist_ok=True)
            self._load_history()

    def _load_history(self) -> None:
        """Load persisted run records from disk."""
        history_file = _PERSIST_DIR / "runs.jsonl"
        if not history_file.exists():
            return
        for line in history_file.read_text().strip().split("\n"):
            if not line.strip():
                continue
            try:
                data = json.loads(line)
                tags = frozenset(PrimitiveTag(t) for t in data["primitive_tags"])
                transformed_from = None
                if data.get("transformed_from"):
                    transformed_from = frozenset(
                        PrimitiveTag(t) for t in data["transformed_from"]
                    )
                record = RunRecord(
                    run_id=data["run_id"],
                    timestamp=data["timestamp"],
                    intent=data["intent"],
                    domain_type=data["domain_type"],
                    primitive_tags=tags,
                    success_score=data["success_score"],
                    pipeline_ok=data["pipeline_ok"],
                    objective_score=data.get("objective_score"),
                    transformation_applied=data.get("transformation_applied", False),
                    transformed_from=transformed_from,
                    step_scores=data.get("step_scores", {}),
                    metadata=data.get("metadata", {}),
                )
                self._runs.append(record)
            except (json.JSONDecodeError, KeyError, ValueError):
                continue

    def _persist_run(self, record: RunRecord) -> None:
        """Append a single run record to disk."""
        if not self._persist:
            return
        history_file = _PERSIST_DIR / "runs.jsonl"
        with open(history_file, "a") as f:
            f.write(json.dumps(record.to_dict()) + "\n")

    # -------------------------------------------------------------------
    # Public API
    # -------------------------------------------------------------------

    def record_run(
        self,
        *,
        run_id: str,
        intent: str,
        domain_type: str,
        primitive_tags: set[PrimitiveTag],
        success_score: float,
        pipeline_ok: bool,
        objective_score: float | None = None,
        transformation_applied: bool = False,
        transformed_from: set[PrimitiveTag] | None = None,
        step_scores: dict[str, float] | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> RunRecord:
        """Record a completed execution run."""
        record = RunRecord(
            run_id=run_id,
            timestamp=time.time(),
            intent=intent,
            domain_type=domain_type,
            primitive_tags=frozenset(primitive_tags),
            success_score=success_score,
            pipeline_ok=pipeline_ok,
            objective_score=objective_score,
            transformation_applied=transformation_applied,
            transformed_from=frozenset(transformed_from) if transformed_from else None,
            step_scores=step_scores or {},
            metadata=metadata or {},
        )
        self._runs.append(record)
        self._persist_run(record)
        return record

    def extract_patterns(self, min_occurrences: int = 2) -> list[PrimitivePattern]:
        """Detect recurring primitive combinations across runs.

        Groups runs by their primitive tag set and computes statistics
        for each group.
        """
        # Group by tag combination
        groups: dict[frozenset[PrimitiveTag], list[RunRecord]] = {}
        for run in self._runs:
            groups.setdefault(run.primitive_tags, []).append(run)

        patterns: list[PrimitivePattern] = []
        for tags, runs in groups.items():
            if len(runs) < min_occurrences:
                continue

            scores = [r.success_score for r in runs]
            domains = list(set(r.domain_type for r in runs))
            ok_count = sum(1 for r in runs if r.pipeline_ok)

            patterns.append(
                PrimitivePattern(
                    tags=tags,
                    occurrences=len(runs),
                    avg_score=sum(scores) / len(scores),
                    success_rate=ok_count / len(runs),
                    domains=domains,
                    best_score=max(scores),
                    worst_score=min(scores),
                )
            )

        return patterns

    def rank_patterns(self) -> list[PrimitivePattern]:
        """Return patterns ranked by average score (best first)."""
        patterns = self.extract_patterns(min_occurrences=1)
        return sorted(patterns, key=lambda p: p.avg_score, reverse=True)

    def suggest_optimizations(self) -> list[dict[str, Any]]:
        """Suggest primitive composition improvements based on history.

        Analyses:
        1. High-performing combinations → recommend reuse
        2. Low-performing combinations → recommend transformation
        3. Successful transformations → recommend direct composition
        """
        suggestions: list[dict[str, Any]] = []
        patterns = self.extract_patterns(min_occurrences=1)

        # Find high performers
        for p in patterns:
            if p.avg_score >= 0.8 and p.occurrences >= 2:
                suggestions.append(
                    {
                        "type": "reuse",
                        "tags": sorted(t.value for t in p.tags),
                        "reason": f"avg score {p.avg_score:.2f} across {p.occurrences} runs",
                        "domains": p.domains,
                    }
                )

        # Find low performers
        for p in patterns:
            if p.avg_score < 0.5 and p.occurrences >= 2:
                suggestions.append(
                    {
                        "type": "transform",
                        "tags": sorted(t.value for t in p.tags),
                        "reason": f"avg score {p.avg_score:.2f} — consider adding missing primitives",
                        "domains": p.domains,
                    }
                )

        # Find successful transformations
        transformed = [
            r for r in self._runs if r.transformation_applied and r.success_score >= 0.7
        ]
        for run in transformed:
            if run.transformed_from:
                suggestions.append(
                    {
                        "type": "skip_transform",
                        "from_tags": sorted(t.value for t in run.transformed_from),
                        "to_tags": sorted(t.value for t in run.primitive_tags),
                        "reason": f"transformation succeeded (score {run.success_score:.2f}) — use target composition directly",
                        "domain": run.domain_type,
                    }
                )

        # Primitive frequency analysis — which tags appear in high-scoring runs
        high_score_tags: Counter[PrimitiveTag] = Counter()
        low_score_tags: Counter[PrimitiveTag] = Counter()
        for run in self._runs:
            if run.success_score >= 0.7:
                high_score_tags.update(run.primitive_tags)
            elif run.success_score < 0.4:
                low_score_tags.update(run.primitive_tags)

        # Tags that appear in success but rarely in failure
        for tag, count in high_score_tags.most_common():
            low_count = low_score_tags.get(tag, 0)
            if count >= 3 and low_count <= 1:
                suggestions.append(
                    {
                        "type": "always_include",
                        "tag": tag.value,
                        "reason": f"appears in {count} high-scoring runs, only {low_count} low-scoring",
                    }
                )

        return suggestions

    def get_runs(self, limit: int = 50) -> list[RunRecord]:
        """Return most recent runs."""
        return self._runs[-limit:]

    def get_domain_stats(self) -> dict[str, dict[str, Any]]:
        """Aggregate statistics per domain type."""
        stats: dict[str, dict[str, Any]] = {}
        for run in self._runs:
            if run.domain_type not in stats:
                stats[run.domain_type] = {
                    "count": 0,
                    "total_score": 0.0,
                    "ok_count": 0,
                }
            s = stats[run.domain_type]
            s["count"] += 1
            s["total_score"] += run.success_score
            s["ok_count"] += 1 if run.pipeline_ok else 0

        for domain, s in stats.items():
            s["avg_score"] = round(s["total_score"] / max(s["count"], 1), 4)
            s["success_rate"] = round(s["ok_count"] / max(s["count"], 1), 4)
            del s["total_score"]

        return stats


# Module-level singleton
_default_memory: MemorySystem | None = None


def get_memory() -> MemorySystem:
    """Get or create the module-level MemorySystem singleton."""
    global _default_memory
    if _default_memory is None:
        _default_memory = MemorySystem()
    return _default_memory


# ---------------------------------------------------------------------------
# Strategy patterns — reusable primitive combinations with context awareness
# ---------------------------------------------------------------------------


@dataclass
class StrategyPattern:
    """A reusable strategy derived from repeated successful primitive combinations.

    Goes beyond PrimitivePattern (which counts occurrences) to capture:
    - Which contexts make this pattern succeed or fail
    - Which objectives it aligns with
    - Confidence based on sample size and consistency
    """

    id: str
    primitive_signature: frozenset[PrimitiveTag]
    domain: str
    objective_signature: str  # which objective this pattern serves
    repeated_success_rate: float  # fraction of runs scoring >= 0.7
    repeated_failure_rate: float  # fraction of runs scoring < 0.4
    recommended_contexts: list[str]  # intents / domains where this works
    anti_contexts: list[str]  # intents / domains where this fails
    supporting_runs: list[str]  # run_ids that support this pattern
    avg_score: float = 0.0
    confidence: float = 0.0  # 0-1 based on sample size and consistency

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "primitive_signature": sorted(t.value for t in self.primitive_signature),
            "domain": self.domain,
            "objective_signature": self.objective_signature,
            "repeated_success_rate": round(self.repeated_success_rate, 4),
            "repeated_failure_rate": round(self.repeated_failure_rate, 4),
            "recommended_contexts": self.recommended_contexts,
            "anti_contexts": self.anti_contexts,
            "supporting_runs": self.supporting_runs[-10:],  # last 10
            "avg_score": round(self.avg_score, 4),
            "confidence": round(self.confidence, 4),
        }


# Strategy extraction methods — added to MemorySystem


def _extract_strategies(self: MemorySystem, min_runs: int = 3) -> list[StrategyPattern]:
    """Extract reusable strategy patterns from run history.

    Groups runs by (primitive_tags, domain) and builds strategy patterns
    from groups with enough data.
    """
    # Group by (tags, domain)
    groups: dict[tuple[frozenset[PrimitiveTag], str], list[RunRecord]] = {}
    for run in self._runs:
        key = (run.primitive_tags, run.domain_type)
        groups.setdefault(key, []).append(run)

    strategies: list[StrategyPattern] = []
    for (tags, domain), runs in groups.items():
        if len(runs) < min_runs:
            continue

        scores = [r.success_score for r in runs]
        success_runs = [r for r in runs if r.success_score >= 0.7]
        failure_runs = [r for r in runs if r.success_score < 0.4]
        avg = sum(scores) / len(scores)

        # Find which intents succeed vs fail
        success_intents = list(set(r.intent for r in success_runs))
        failure_intents = list(set(r.intent for r in failure_runs))

        # Anti-contexts: intents that appear ONLY in failures
        anti = [i for i in failure_intents if i not in success_intents]

        # Objective signature from metadata
        obj_names = [
            r.metadata.get("objective_name", "")
            for r in runs
            if r.metadata.get("objective_name")
        ]
        obj_sig = obj_names[0] if obj_names else ""

        # Confidence: higher with more runs and more consistent scores
        score_std = (sum((s - avg) ** 2 for s in scores) / len(scores)) ** 0.5
        size_factor = min(len(runs) / 10, 1.0)  # max out at 10 runs
        consistency_factor = max(1.0 - score_std, 0.0)
        confidence = size_factor * 0.6 + consistency_factor * 0.4

        strategy_id = f"s_{domain}_{hash(tags) % 10000:04d}"

        strategies.append(
            StrategyPattern(
                id=strategy_id,
                primitive_signature=tags,
                domain=domain,
                objective_signature=obj_sig,
                repeated_success_rate=len(success_runs) / len(runs),
                repeated_failure_rate=len(failure_runs) / len(runs),
                recommended_contexts=success_intents[:5],
                anti_contexts=anti[:5],
                supporting_runs=[r.run_id for r in runs],
                avg_score=avg,
                confidence=confidence,
            )
        )

    return strategies


def _rank_strategies(self: MemorySystem, min_runs: int = 3) -> list[StrategyPattern]:
    """Return strategies ranked by (confidence * avg_score), best first."""
    strategies = self.extract_strategies(min_runs=min_runs)
    return sorted(
        strategies,
        key=lambda s: s.confidence * s.avg_score,
        reverse=True,
    )


def _suggest_strategy_reuse(
    self: MemorySystem,
    intent: str,
    domain: str,
    current_tags: set[PrimitiveTag] | None = None,
) -> list[dict[str, Any]]:
    """Suggest strategy patterns to reuse for a given intent/domain.

    Returns ranked suggestions with reasoning.
    """
    strategies = self.rank_strategies()
    suggestions: list[dict[str, Any]] = []

    for s in strategies:
        # Skip if this intent is in anti-contexts
        if intent in s.anti_contexts:
            continue

        # Score relevance
        relevance = 0.0

        # Domain match
        if s.domain == domain:
            relevance += 0.4

        # Intent match
        if any(intent.lower() in ctx.lower() for ctx in s.recommended_contexts):
            relevance += 0.3

        # Tag overlap with current composition
        if current_tags:
            overlap = len(s.primitive_signature & current_tags) / max(
                len(s.primitive_signature | current_tags), 1
            )
            relevance += overlap * 0.3

        if relevance < 0.2:
            continue

        suggestion: dict[str, Any] = {
            "strategy_id": s.id,
            "primitive_signature": sorted(t.value for t in s.primitive_signature),
            "relevance": round(relevance, 4),
            "confidence": round(s.confidence, 4),
            "avg_score": round(s.avg_score, 4),
            "success_rate": round(s.repeated_success_rate, 4),
            "reason": (
                f"{'domain match' if s.domain == domain else 'cross-domain'}, "
                f"{s.repeated_success_rate:.0%} success over {len(s.supporting_runs)} runs"
            ),
        }

        # Recommend tag additions if strategy has tags current doesn't
        if current_tags:
            missing = s.primitive_signature - current_tags
            if missing:
                suggestion["recommend_add"] = sorted(t.value for t in missing)

        suggestions.append(suggestion)

    return sorted(suggestions, key=lambda s: s["relevance"], reverse=True)[:5]


# Bind methods to MemorySystem
MemorySystem.extract_strategies = _extract_strategies
MemorySystem.rank_strategies = _rank_strategies
MemorySystem.suggest_strategy_reuse = _suggest_strategy_reuse


__all__ = [
    "MemorySystem",
    "RunRecord",
    "PrimitivePattern",
    "StrategyPattern",
    "get_memory",
]
