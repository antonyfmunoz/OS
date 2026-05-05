"""
StrategyMemory — tracks which response strategies produce better outcomes.

Pure data structure. No LLM calls. No randomness. Deterministic ordering.

Each strategy accumulates uses and total_score. The avg_score drives
selection policy in multi_strategy.generate_candidates().

Short-term: lives in-process (module-level singleton per org).
Long-term (future): persist to WorldModel for cross-session learning.

Usage::

    from umh.strategy.memory import get_strategy_memory

    mem = get_strategy_memory()
    mem.record_win("clarity", quality_score=0.85)
    ranked = mem.rank_strategies()
    # → [("clarity", StrategyStats(...)), ("baseline", StrategyStats(...))]
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field


EMA_ALPHA = 0.3

MIN_CONFIDENCE = 0.6

DECAY_RATE = 0.05


@dataclass
class StrategyStats:
    """Performance statistics for a single strategy."""

    name: str
    uses: int = 0
    wins: int = 0
    total_score: float = 0.0
    ema_score: float = 0.0
    last_used_turn: int = 0

    def effective_score(self, current_turn: int) -> float:
        """EMA score decayed by staleness — stale strategies lose influence."""
        if self.uses == 0:
            return 0.0
        staleness = max(0, current_turn - self.last_used_turn)
        return self.ema_score * math.exp(-DECAY_RATE * staleness)

    @property
    def avg_score(self) -> float:
        if self.uses == 0:
            return 0.0
        return self.ema_score

    def update_ema(self, new_score: float) -> None:
        """Update score using exponential moving average."""
        if self.uses <= 1:
            self.ema_score = new_score
        else:
            self.ema_score = (EMA_ALPHA * new_score) + (
                (1 - EMA_ALPHA) * self.ema_score
            )

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "uses": self.uses,
            "wins": self.wins,
            "total_score": round(self.total_score, 4),
            "avg_score": round(self.avg_score, 4),
            "ema_score": round(self.ema_score, 4),
            "last_used_turn": self.last_used_turn,
        }


class StrategyMemory:
    """In-memory strategy performance tracker with optional persistence.

    Thread-safe for the single-process UMH runtime.
    When ``persist=True``, stats are saved periodically via the persistence
    layer and restored on construction.
    """

    def __init__(self, persist: bool = False) -> None:
        self._stats: dict[str, StrategyStats] = {}
        self._global_turn: int = 0
        self._persist = persist
        self._update_count: int = 0

        if persist:
            self._load_persisted()

    def record_win(
        self,
        strategy_name: str,
        quality_score: float,
        confidence: float = 1.0,
        min_confidence: float | None = None,
        goal_score: float | None = None,
    ) -> None:
        """Record that a strategy won selection with a given quality score.

        Only updates ranking stats if confidence >= min_confidence threshold.
        When ``min_confidence`` is provided (from calibration), uses that
        instead of the module-level MIN_CONFIDENCE constant.

        When ``goal_score`` is provided, the recorded quality is amplified
        by goal alignment — high goal_score strengthens reinforcement,
        low goal_score dampens it. This is separate from the goal_relevance
        weighting applied at select_best() time.
        Always increments turn counter and marks last_used_turn.
        """
        self._global_turn += 1
        stats = self._ensure(strategy_name)
        stats.last_used_turn = self._global_turn

        threshold = min_confidence if min_confidence is not None else MIN_CONFIDENCE
        if confidence < threshold:
            return

        effective_score = quality_score
        if goal_score is not None:
            effective_score = quality_score * (0.5 + 0.5 * goal_score)

        stats.uses += 1
        stats.wins += 1
        stats.total_score += effective_score
        stats.update_ema(effective_score)
        self._maybe_persist()

    def record_loss(
        self,
        strategy_name: str,
        quality_score: float,
        confidence: float = 1.0,
        min_confidence: float | None = None,
        goal_score: float | None = None,
    ) -> None:
        """Record that a strategy was evaluated but lost selection.

        Only updates ranking stats if confidence >= min_confidence threshold.
        When ``min_confidence`` is provided (from calibration), uses that
        instead of the module-level MIN_CONFIDENCE constant.

        When ``goal_score`` is provided, same weighting as record_win.
        """
        stats = self._ensure(strategy_name)

        threshold = min_confidence if min_confidence is not None else MIN_CONFIDENCE
        if confidence < threshold:
            return

        effective_score = quality_score
        if goal_score is not None:
            effective_score = quality_score * (0.5 + 0.5 * goal_score)

        stats.uses += 1
        stats.total_score += effective_score
        stats.update_ema(effective_score)
        self._maybe_persist()

    def rank_strategies(
        self,
        conditioning_bias: dict[str, float] | None = None,
        transfer_scores: dict[str, float] | None = None,
        influence_adjustment: float = 0.0,
    ) -> list[tuple[str, StrategyStats]]:
        """Return strategies sorted by effective_score (decay-adjusted) descending.

        When ``conditioning_bias`` is provided (strategy_name → float), each
        strategy's sort score is adjusted additively. The bias is transient —
        StrategyStats objects are NOT mutated.

        When ``transfer_scores`` is provided (from cross-state generalization),
        each strategy's sort score is further adjusted additively. Transfer
        scores come from similar clusters' historical performance.

        When ``influence_adjustment`` is provided (from influence scoring),
        it is added uniformly to all strategies' sort scores. This shifts
        the entire ranking baseline without changing relative order.

        Strategies with no data sort last (score=0.0).
        Tie-breaking: more uses wins (more data = more trustworthy).
        """
        current = self._global_turn
        bias = conditioning_bias or {}
        transfer = transfer_scores or {}
        adj = influence_adjustment
        return sorted(
            self._stats.items(),
            key=lambda item: (
                item[1].effective_score(current)
                + bias.get(item[0], 0.0)
                + transfer.get(item[0], 0.0)
                + adj,
                item[1].uses,
            ),
            reverse=True,
        )

    def get_conditioned_scores(
        self,
        conditioning_bias: dict[str, float] | None = None,
        transfer_scores: dict[str, float] | None = None,
        influence_adjustment: float = 0.0,
    ) -> tuple[dict[str, float], dict[str, float]]:
        """Return base and conditioned score dicts for observability.

        Returns (base_scores, conditioned_scores) where both are
        {strategy_name: score}. Conditioned includes bias + transfer +
        influence_adjustment.
        """
        current = self._global_turn
        bias = conditioning_bias or {}
        transfer = transfer_scores or {}
        adj = influence_adjustment
        base: dict[str, float] = {}
        conditioned: dict[str, float] = {}
        for name, stats in self._stats.items():
            b = stats.effective_score(current)
            base[name] = round(b, 4)
            conditioned[name] = round(
                b + bias.get(name, 0.0) + transfer.get(name, 0.0) + adj, 4
            )
        return base, conditioned

    def get_top_strategies(self, count: int = 2) -> list[str]:
        """Return the top N strategy names by avg_score.

        Returns names only — the caller maps them to directives.
        """
        ranked = self.rank_strategies()
        return [name for name, _ in ranked[:count]]

    def get_stale_strategy(
        self,
        known_strategies: list[str],
        stale_threshold: int = 5,
    ) -> str | None:
        """Return the least-recently-used strategy that is stale.

        A strategy is stale if it hasn't been used in ``stale_threshold`` turns.
        Returns None if no strategy is stale.
        """
        current_turn = self._global_turn
        stale_candidates: list[tuple[str, int]] = []

        for name in known_strategies:
            stats = self._stats.get(name)
            if stats is None:
                stale_candidates.append((name, 0))
            elif (current_turn - stats.last_used_turn) >= stale_threshold:
                stale_candidates.append((name, stats.last_used_turn))

        if not stale_candidates:
            return None

        stale_candidates.sort(key=lambda x: x[1])
        return stale_candidates[0][0]

    @property
    def global_turn(self) -> int:
        return self._global_turn

    def get_stats(self, strategy_name: str) -> StrategyStats | None:
        """Return stats for a specific strategy, or None if never seen."""
        return self._stats.get(strategy_name)

    def has_data(self) -> bool:
        """True if any strategy has been recorded at least once."""
        return any(s.uses > 0 for s in self._stats.values())

    def to_dict(self) -> dict[str, dict]:
        """Snapshot of all strategy stats for serialization."""
        return {name: stats.to_dict() for name, stats in self._stats.items()}

    def apply_outcome(
        self,
        strategy_name: str,
        adjusted_score: float,
        outcome_confidence: float,
    ) -> None:
        """Retroactively adjust a strategy's EMA with an external outcome signal.

        Only modifies EMA — does not increment uses/wins/turn counters.
        This is a correction to prior learning, not a new observation.
        The outcome_confidence gates how aggressively EMA shifts.
        """
        stats = self._stats.get(strategy_name)
        if stats is None or stats.uses == 0:
            return
        blend = min(outcome_confidence, EMA_ALPHA)
        stats.ema_score = (blend * adjusted_score) + ((1 - blend) * stats.ema_score)
        self._maybe_persist()

    def record_execution_credit(
        self,
        action_id: str,
        effective_credit: float,
        context_signature: dict | None = None,
    ) -> bool:
        """Record execution credit against the most recently selected strategy.

        Strengthens pattern memory using real execution outcomes.
        Uses apply_outcome() to adjust EMA without incrementing counters.

        Returns True if credit was applied, False if no strategy selected.
        """
        ranked = self.rank_strategies()
        if not ranked:
            return False

        selected = ranked[0][0]
        stats = self._stats.get(selected)
        if stats is None or stats.uses == 0:
            return False

        confidence = min(1.0, abs(effective_credit))
        self.apply_outcome(
            strategy_name=selected,
            adjusted_score=effective_credit,
            outcome_confidence=confidence,
        )
        return True

    def _ensure(self, name: str) -> StrategyStats:
        if name not in self._stats:
            self._stats[name] = StrategyStats(name=name)
        return self._stats[name]

    def _maybe_persist(self) -> None:
        """Save to persistent storage if enabled."""
        if not self._persist:
            return
        self._update_count += 1
        try:
            from umh.strategy.interfaces import get_strategy_persistence

            backend = get_strategy_persistence()
            backend.save_strategy_memory(self.to_dict(), global_turn=self._global_turn)
        except Exception:
            pass

    def _load_persisted(self) -> None:
        """Restore stats from persistent storage on cold start."""
        try:
            from umh.strategy.interfaces import get_strategy_persistence

            backend = get_strategy_persistence()
            data = backend.load_strategy_memory()
            if data is None:
                return

            self._global_turn = data.get("global_turn", 0)
            strategies = data.get("strategies", {})
            for name, sdict in strategies.items():
                stats = StrategyStats(
                    name=sdict.get("name", name),
                    uses=sdict.get("uses", 0),
                    wins=sdict.get("wins", 0),
                    total_score=sdict.get("total_score", 0.0),
                    ema_score=sdict.get("ema_score", 0.0),
                    last_used_turn=sdict.get("last_used_turn", 0),
                )
                self._stats[name] = stats
        except Exception:
            pass


# ─── Module-level singleton ─────────────────────────────────────────────────

_global_memory: StrategyMemory | None = None


def get_strategy_memory(persist: bool = False) -> StrategyMemory:
    """Return the process-wide strategy memory singleton.

    Pass ``persist=True`` on the first call to enable cross-restart
    persistence via the persistence layer. Subsequent calls ignore the
    flag (singleton is already created).
    """
    global _global_memory
    if _global_memory is None:
        _global_memory = StrategyMemory(persist=persist)
    return _global_memory


def reset_strategy_memory() -> None:
    """Reset the singleton. Used in tests only."""
    global _global_memory
    _global_memory = None
