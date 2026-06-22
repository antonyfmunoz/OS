"""Strategic Compression Benchmark — high-level intent to executable reality.

Campaign 23B. Category O. Tier 5: Strategic Metric.
Measures how efficiently UMH transforms high-level operator intent into
executable plans and code. "Build me a SaaS" → how many steps, how much output.

Deterministic. No LLM calls.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------

@dataclass
class IntentRecord:
    """A single operator intent and its execution outcome."""

    intent_id: str = ""
    intent_text: str = ""
    word_count: int = 0  # words in original intent
    clarification_rounds: int = 0
    steps_to_execution: int = 0  # intent → first code change
    output_loc: int = 0  # lines of code produced
    duration_seconds: float = 0.0

    def resolved_word_count(self) -> int:
        """Return word count, computing it from intent_text if unset."""
        if self.word_count > 0:
            return self.word_count
        return len(self.intent_text.split())

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class StrategicCompressionResult:
    """Complete strategic compression benchmark result."""

    intents_processed: int = 0
    avg_steps_to_execution: float = 0.0
    avg_clarification_rounds: float = 0.0
    direct_execution_rate: float = 0.0  # intents with 0 clarifications / total
    compression_ratio: float = 0.0  # total output_loc / total input words
    avg_duration_seconds: float = 0.0
    fastest_intent_seconds: float = 0.0
    slowest_intent_seconds: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


# ---------------------------------------------------------------------------
# Benchmark
# ---------------------------------------------------------------------------

class StrategicCompressionBenchmark:
    """Measures how efficiently intent compresses into executable output."""

    def evaluate(self, intent_records: list[IntentRecord]) -> StrategicCompressionResult:
        """Evaluate a list of intent records into compression metrics."""
        if not intent_records:
            return StrategicCompressionResult()

        n = len(intent_records)

        total_steps = sum(r.steps_to_execution for r in intent_records)
        total_clarifications = sum(r.clarification_rounds for r in intent_records)
        total_output = sum(r.output_loc for r in intent_records)
        total_words = sum(r.resolved_word_count() for r in intent_records)
        durations = [r.duration_seconds for r in intent_records]
        total_duration = sum(durations)

        direct = sum(1 for r in intent_records if r.clarification_rounds == 0)

        return StrategicCompressionResult(
            intents_processed=n,
            avg_steps_to_execution=round(total_steps / n, 4),
            avg_clarification_rounds=round(total_clarifications / n, 4),
            direct_execution_rate=round(direct / n, 4),
            compression_ratio=round(total_output / max(total_words, 1), 4),
            avg_duration_seconds=round(total_duration / n, 4),
            fastest_intent_seconds=round(min(durations), 4),
            slowest_intent_seconds=round(max(durations), 4),
        )
