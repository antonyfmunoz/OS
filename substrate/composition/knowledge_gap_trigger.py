"""Knowledge gap trigger — detects gaps during execution and triggers composition.

Watches execution outcomes for signs of knowledge gaps:
  - Low confidence from intelligence patterns
  - "unknown" intent classifications
  - Failed or partial executions with no matching skill
  - Repeated similar queries with no skill match

When a gap is detected, queues a composition request that the
AuthoringAgent or ResearchAgent can pick up.
"""

from __future__ import annotations

import json
import logging
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

GAP_CONFIDENCE_THRESHOLD = 0.3
GAP_COOLDOWN_SECONDS = 3600
MAX_QUEUED_GAPS = 50


@dataclass
class KnowledgeGap:
    gap_id: str
    topic: str
    source: str
    confidence: float
    detected_at: float = 0.0
    trigger_count: int = 1
    status: str = "queued"

    def __post_init__(self) -> None:
        if not self.detected_at:
            self.detected_at = time.time()

    def to_dict(self) -> dict[str, Any]:
        return {
            "gap_id": self.gap_id,
            "topic": self.topic,
            "source": self.source,
            "confidence": self.confidence,
            "detected_at": self.detected_at,
            "trigger_count": self.trigger_count,
            "status": self.status,
        }


class KnowledgeGapTrigger:
    """Detects knowledge gaps and queues composition requests."""

    def __init__(self, queue_path: str = "data/umh/composition/gap_queue.jsonl") -> None:
        self._queue_path = Path(queue_path)
        self._queue_path.parent.mkdir(parents=True, exist_ok=True)
        self._recent_topics: dict[str, float] = {}
        self._gaps: list[KnowledgeGap] = []

    def check_execution_outcome(
        self,
        input_signal: str,
        intent: str,
        output: str,
        success: bool,
        pattern_confidence: float = 1.0,
        skill_matched: bool = True,
    ) -> KnowledgeGap | None:
        """Check an execution outcome for knowledge gaps.

        Returns a KnowledgeGap if one is detected, None otherwise.
        """
        gap = None

        if not success and not skill_matched:
            gap = self._create_gap(
                topic=input_signal[:200],
                source="execution_failure_no_skill",
                confidence=pattern_confidence,
            )

        elif intent == "unknown" and pattern_confidence < GAP_CONFIDENCE_THRESHOLD:
            gap = self._create_gap(
                topic=input_signal[:200],
                source="unknown_intent_low_confidence",
                confidence=pattern_confidence,
            )

        elif not skill_matched and pattern_confidence < 0.5:
            gap = self._create_gap(
                topic=input_signal[:200],
                source="no_skill_low_confidence",
                confidence=pattern_confidence,
            )

        if gap:
            self._persist_gap(gap)
            self._try_trigger_composition(gap)

        return gap

    def _create_gap(self, topic: str, source: str, confidence: float) -> KnowledgeGap | None:
        topic_key = topic[:50].lower().strip()
        last_seen = self._recent_topics.get(topic_key, 0)
        if time.time() - last_seen < GAP_COOLDOWN_SECONDS:
            return None

        self._recent_topics[topic_key] = time.time()

        import hashlib

        gap_id = f"gap-{hashlib.sha256(topic_key.encode()).hexdigest()[:12]}"

        for existing in self._gaps:
            if existing.gap_id == gap_id:
                existing.trigger_count += 1
                return existing

        gap = KnowledgeGap(
            gap_id=gap_id,
            topic=topic,
            source=source,
            confidence=confidence,
        )
        self._gaps.append(gap)
        if len(self._gaps) > MAX_QUEUED_GAPS:
            self._gaps = self._gaps[-MAX_QUEUED_GAPS:]

        return gap

    def _persist_gap(self, gap: KnowledgeGap) -> None:
        try:
            with open(self._queue_path, "a") as f:
                f.write(json.dumps(gap.to_dict(), separators=(",", ":")) + "\n")
        except OSError as e:
            logger.warning("gap queue write failed: %s", e)

    def _try_trigger_composition(self, gap: KnowledgeGap) -> None:
        """Attempt to trigger the composition pipeline for a knowledge gap."""
        if gap.trigger_count < 2:
            return

        try:
            from substrate.composition.mastery.research.cli import run_research

            logger.info(
                "triggering composition research for gap: %s (triggered %d times)",
                gap.topic[:60],
                gap.trigger_count,
            )
            run_research(gap.topic[:200])
            gap.status = "research_triggered"
        except Exception as e:
            logger.debug("composition trigger failed (non-critical): %s", e)
            gap.status = "trigger_failed"

    def get_queued_gaps(self, limit: int = 20) -> list[dict[str, Any]]:
        return [g.to_dict() for g in self._gaps[-limit:]]

    def stats(self) -> dict[str, Any]:
        return {
            "total_gaps_detected": len(self._gaps),
            "queued": sum(1 for g in self._gaps if g.status == "queued"),
            "research_triggered": sum(1 for g in self._gaps if g.status == "research_triggered"),
            "trigger_failed": sum(1 for g in self._gaps if g.status == "trigger_failed"),
        }
