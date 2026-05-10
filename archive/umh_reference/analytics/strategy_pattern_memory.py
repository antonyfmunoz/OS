"""StrategyPatternMemory — multi-step action pattern learning and reuse.

Remembers short action sequences that led to high outcomes under specific
context conditions. At decision time, finds matching patterns and applies
a small bias toward actions that appeared in successful sequences.

Sits alongside the existing strategy_memory.py (which tracks response
strategies by name). This module tracks *simulation-level action patterns*
by context signature.

All logic is deterministic, bounded, and additive.
No ML. No embeddings. No randomness. No ExecutionSpine modification.
"""

from __future__ import annotations

from dataclasses import dataclass, field


# ─── Constants ──────────────────────────────────────────────────

MAX_STRATEGIES = 100
MAX_SEQUENCE_LENGTH = 5
MIN_OUTCOME_THRESHOLD = 0.1
MIN_CONFIDENCE_FOR_BIAS = 0.5
MIN_CONTEXT_STABILITY = "stable"
SIGNATURE_SIMILARITY_THRESHOLD = 0.6
MAX_BIAS = 0.05
EMA_ALPHA = 0.2
MIN_SUCCESS_COUNT_FOR_BIAS = 2
MAX_MATCHED_STRATEGIES = 3


# ─── Uncertainty bucketing ─────────────────────────────────────


def _uncertainty_bucket(uncertainty: float) -> str:
    if uncertainty < 0.2:
        return "low"
    if uncertainty < 0.5:
        return "medium"
    return "high"


# ─── Data models ───────────────────────────────────────────────


@dataclass(frozen=True)
class StrategySignature:
    """Context fingerprint — the 'when this happens' key."""

    context_type: str
    objective_mode: str
    uncertainty_bucket: str
    risk_level: str
    dominant_signals: tuple[str, ...]

    def to_dict(self) -> dict:
        return {
            "context_type": self.context_type,
            "objective_mode": self.objective_mode,
            "uncertainty_bucket": self.uncertainty_bucket,
            "risk_level": self.risk_level,
            "dominant_signals": list(self.dominant_signals),
        }


@dataclass
class StrategyRecord:
    """A remembered action pattern with performance tracking."""

    strategy_id: str
    signature: StrategySignature
    action_sequence: tuple[str, ...]
    avg_reward: float = 0.0
    success_count: int = 0
    failure_count: int = 0
    confidence: float = 0.0
    last_update_step: int = 0

    def win_rate(self) -> float:
        total = self.success_count + self.failure_count
        if total == 0:
            return 0.0
        return self.success_count / total

    def to_dict(self) -> dict:
        return {
            "strategy_id": self.strategy_id,
            "signature": self.signature.to_dict(),
            "action_sequence": list(self.action_sequence),
            "avg_reward": round(self.avg_reward, 6),
            "success_count": self.success_count,
            "failure_count": self.failure_count,
            "confidence": round(self.confidence, 6),
            "win_rate": round(self.win_rate(), 6),
            "last_update_step": self.last_update_step,
        }


# ─── Signature construction ───────────────────────────────────


def build_signature(
    context_type: str | None = None,
    objective_mode: str | None = None,
    uncertainty: float = 0.0,
    risk_level: float = 0.0,
    dominant_signals: tuple[str, ...] | None = None,
) -> StrategySignature:
    """Build a strategy signature from context parameters."""
    r_bucket = "low" if risk_level < 0.3 else ("medium" if risk_level < 0.6 else "high")
    sigs = dominant_signals or ()
    capped = sigs[:3]

    return StrategySignature(
        context_type=context_type or "unknown",
        objective_mode=objective_mode or "default",
        uncertainty_bucket=_uncertainty_bucket(uncertainty),
        risk_level=r_bucket,
        dominant_signals=capped,
    )


# ─── Signature similarity ─────────────────────────────────────


def signature_similarity(a: StrategySignature, b: StrategySignature) -> float:
    """Compute similarity between two signatures. Returns 0.0–1.0."""
    score = 0.0
    total = 4.0

    if a.context_type == b.context_type:
        score += 1.0
    if a.objective_mode == b.objective_mode:
        score += 1.0
    if a.uncertainty_bucket == b.uncertainty_bucket:
        score += 1.0
    if a.risk_level == b.risk_level:
        score += 1.0

    if a.dominant_signals and b.dominant_signals:
        total += 1.0
        overlap = len(set(a.dominant_signals) & set(b.dominant_signals))
        union = len(set(a.dominant_signals) | set(b.dominant_signals))
        if union > 0:
            score += overlap / union

    return score / total


# ─── Strategy ID generation ───────────────────────────────────


def _make_strategy_id(signature: StrategySignature, sequence: tuple[str, ...]) -> str:
    sig_key = f"{signature.context_type}_{signature.objective_mode}_{signature.uncertainty_bucket}_{signature.risk_level}"
    seq_key = "_".join(a[:20] for a in sequence[:3])
    return f"sp_{sig_key}_{seq_key}"


# ─── Bias computation ─────────────────────────────────────────


def compute_strategy_bias(
    action_id: str,
    matched_strategies: list[StrategyRecord],
) -> float:
    """Compute the bias for an action based on matched strategy patterns.

    Returns a value in [-MAX_BIAS, +MAX_BIAS].
    Only strategies with sufficient confidence and success count contribute.
    """
    if not matched_strategies:
        return 0.0

    total_bias = 0.0
    contributors = 0

    for record in matched_strategies:
        if record.confidence < MIN_CONFIDENCE_FOR_BIAS:
            continue
        if record.success_count < MIN_SUCCESS_COUNT_FOR_BIAS:
            continue

        if action_id in record.action_sequence:
            position = record.action_sequence.index(action_id)
            position_weight = 1.0 / (1.0 + position)
            total_bias += record.confidence * record.win_rate() * position_weight
            contributors += 1

    if contributors == 0:
        return 0.0

    avg_bias = total_bias / contributors
    scaled = avg_bias * MAX_BIAS
    return max(-MAX_BIAS, min(MAX_BIAS, scaled))


# ─── Memory store ─────────────────────────────────────────────


class StrategyPatternMemory:
    """Bounded memory of successful action patterns indexed by context signature."""

    def __init__(self, max_strategies: int = MAX_STRATEGIES) -> None:
        self._records: dict[str, StrategyRecord] = {}
        self._insertion_order: list[str] = []
        self._max_strategies = max_strategies
        self._step: int = 0

    @property
    def size(self) -> int:
        return len(self._records)

    @property
    def step(self) -> int:
        return self._step

    def record_outcome(
        self,
        signature: StrategySignature,
        action_sequence: tuple[str, ...],
        outcome_score: float,
        step: int | None = None,
    ) -> bool:
        """Record an action sequence outcome. Returns True if stored/updated."""
        if step is not None:
            self._step = max(self._step, step)
        else:
            self._step += 1

        capped_seq = action_sequence[:MAX_SEQUENCE_LENGTH]
        if not capped_seq:
            return False

        strategy_id = _make_strategy_id(signature, capped_seq)

        existing = self._find_mergeable(signature, capped_seq)
        if existing is not None:
            self._update_record(existing, outcome_score)
            return True

        if outcome_score >= MIN_OUTCOME_THRESHOLD:
            record = StrategyRecord(
                strategy_id=strategy_id,
                signature=signature,
                action_sequence=capped_seq,
                avg_reward=outcome_score,
                success_count=1,
                failure_count=0,
                confidence=outcome_score,
                last_update_step=self._step,
            )
            self._insert(record)
            return True
        return False

    def find_matching(
        self,
        query: StrategySignature,
        max_results: int = MAX_MATCHED_STRATEGIES,
    ) -> list[StrategyRecord]:
        """Find strategies whose signature matches the query above threshold."""
        candidates: list[tuple[float, StrategyRecord]] = []

        for record in self._records.values():
            sim = signature_similarity(query, record.signature)
            if sim >= SIGNATURE_SIMILARITY_THRESHOLD:
                candidates.append((sim, record))

        candidates.sort(key=lambda x: (-x[0], -x[1].confidence))
        return [rec for _, rec in candidates[:max_results]]

    def get_action_biases(
        self,
        query: StrategySignature,
        action_ids: tuple[str, ...],
        context_type: str | None = None,
    ) -> dict[str, float]:
        """Compute bias for each action based on matching strategy patterns.

        Returns empty dict if safety conditions aren't met.
        """
        if context_type is not None and context_type != MIN_CONTEXT_STABILITY:
            return {}

        matched = self.find_matching(query)
        if not matched:
            return {}

        if _has_conflicting_strategies(matched, action_ids):
            return {}

        biases: dict[str, float] = {}
        for aid in action_ids:
            b = compute_strategy_bias(aid, matched)
            if abs(b) > 1e-10:
                biases[aid] = b
        return biases

    def get_record(self, strategy_id: str) -> StrategyRecord | None:
        return self._records.get(strategy_id)

    def all_records(self) -> list[StrategyRecord]:
        return list(self._records.values())

    def reset(self) -> None:
        self._records.clear()
        self._insertion_order.clear()
        self._step = 0

    def get_trace_fields(self) -> dict:
        return {
            "strat_pattern_count": self.size,
            "strat_pattern_step": self._step,
        }

    def _find_mergeable(
        self,
        signature: StrategySignature,
        sequence: tuple[str, ...],
    ) -> StrategyRecord | None:
        """Find an existing record with identical signature and sequence."""
        for record in self._records.values():
            if record.signature == signature and record.action_sequence == sequence:
                return record
        return None

    def _update_record(self, record: StrategyRecord, outcome_score: float) -> None:
        """Update an existing record with a new outcome using EMA."""
        if outcome_score >= MIN_OUTCOME_THRESHOLD:
            record.success_count += 1
        else:
            record.failure_count += 1

        record.avg_reward = (
            1.0 - EMA_ALPHA
        ) * record.avg_reward + EMA_ALPHA * outcome_score
        record.confidence = (
            1.0 - EMA_ALPHA
        ) * record.confidence + EMA_ALPHA * record.win_rate()
        record.last_update_step = self._step

    def _insert(self, record: StrategyRecord) -> None:
        """Insert a new record, evicting oldest if at capacity."""
        if len(self._records) >= self._max_strategies:
            self._evict_oldest()
        self._records[record.strategy_id] = record
        self._insertion_order.append(record.strategy_id)

    def _evict_oldest(self) -> None:
        """FIFO eviction of the oldest record."""
        while self._insertion_order:
            oldest_id = self._insertion_order.pop(0)
            if oldest_id in self._records:
                del self._records[oldest_id]
                return


# ─── Conflict detection ───────────────────────────────────────


def _has_conflicting_strategies(
    strategies: list[StrategyRecord],
    action_ids: tuple[str, ...],
) -> bool:
    """Return True if matched strategies disagree on action preference.

    Conflict = two strategies with opposite action ordering for the
    same position in the sequence.
    """
    if len(strategies) < 2:
        return False

    first_actions = set()
    for s in strategies:
        if s.action_sequence:
            first_actions.add(s.action_sequence[0])

    if len(first_actions) > 1:
        confidences = [s.confidence for s in strategies]
        if max(confidences) - min(confidences) < 0.1:
            return True
    return False


# ─── Module-level singleton ───────────────────────────────────

_global_pattern_memory: StrategyPatternMemory | None = None


def get_strategy_pattern_memory() -> StrategyPatternMemory:
    global _global_pattern_memory
    if _global_pattern_memory is None:
        _global_pattern_memory = StrategyPatternMemory()
    return _global_pattern_memory


def reset_strategy_pattern_memory() -> None:
    global _global_pattern_memory
    _global_pattern_memory = None
