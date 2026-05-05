"""
DirectiveMemory — tracks which prompt directives produce better outcomes.

Mirrors StrategyMemory but operates on a separate axis:
    - Strategy = "how to think" (system prompt behavioral shaping)
    - Directive = "how to shape the prompt" (user message approach shaping)

Each directive key (e.g. "clarity", "concise") accumulates performance
stats via EMA scoring with staleness decay — identical math to
StrategyMemory so there is zero new risk.

Learning happens post-selection only.  No side effects before commit.
No LLM calls.  No randomness.  Deterministic ordering.

Usage::

    from umh.runtime_engine.directive_memory import get_directive_memory

    mem = get_directive_memory()
    mem.record_win("clarity", quality_score=0.85)
    ranked = mem.rank_directives()
    # → [("clarity", DirectiveStats(...)), ("baseline", DirectiveStats(...))]
"""

from __future__ import annotations

import math
from dataclasses import dataclass


EMA_ALPHA = 0.3
MIN_CONFIDENCE = 0.6
DECAY_RATE = 0.05


@dataclass
class DirectiveStats:
    """Performance statistics for a single prompt directive."""

    name: str
    uses: int = 0
    wins: int = 0
    total_score: float = 0.0
    ema_score: float = 0.0
    last_used_turn: int = 0

    def effective_score(self, current_turn: int) -> float:
        """EMA score decayed by staleness."""
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


class DirectiveMemory:
    """In-memory directive performance tracker with optional persistence.

    Tracks which prompt directives (keyed by strategy name) correlate
    with higher-quality outcomes.  Uses the same EMA + decay math as
    StrategyMemory so the two systems are independently comparable.

    When ``persist=True``, stats are saved periodically via the persistence
    layer and restored on construction.
    """

    def __init__(self, persist: bool = False) -> None:
        self._stats: dict[str, DirectiveStats] = {}
        self._global_turn: int = 0
        self._persist = persist
        self._update_count: int = 0

        if persist:
            self._load_persisted()

    def record_win(
        self,
        directive_key: str,
        quality_score: float,
        confidence: float = 1.0,
        min_confidence: float | None = None,
    ) -> None:
        """Record that a directive's candidate won selection."""
        self._global_turn += 1
        stats = self._ensure(directive_key)
        stats.last_used_turn = self._global_turn

        threshold = min_confidence if min_confidence is not None else MIN_CONFIDENCE
        if confidence < threshold:
            return

        stats.uses += 1
        stats.wins += 1
        stats.total_score += quality_score
        stats.update_ema(quality_score)
        self._maybe_persist()

    def record_loss(
        self,
        directive_key: str,
        quality_score: float,
        confidence: float = 1.0,
        min_confidence: float | None = None,
    ) -> None:
        """Record that a directive's candidate lost selection."""
        stats = self._ensure(directive_key)

        threshold = min_confidence if min_confidence is not None else MIN_CONFIDENCE
        if confidence < threshold:
            return

        stats.uses += 1
        stats.total_score += quality_score
        stats.update_ema(quality_score)
        self._maybe_persist()

    def rank_directives(self) -> list[tuple[str, DirectiveStats]]:
        """Return directives sorted by effective_score descending.

        Tie-breaking: more uses wins (more data = more trustworthy).
        """
        current = self._global_turn
        return sorted(
            self._stats.items(),
            key=lambda item: (item[1].effective_score(current), item[1].uses),
            reverse=True,
        )

    def get_top_directives(self, count: int = 2) -> list[str]:
        """Return the top N directive keys by effective score."""
        ranked = self.rank_directives()
        return [name for name, _ in ranked[:count]]

    @property
    def global_turn(self) -> int:
        return self._global_turn

    def get_stats(self, directive_key: str) -> DirectiveStats | None:
        """Return stats for a specific directive, or None if never seen."""
        return self._stats.get(directive_key)

    def has_data(self) -> bool:
        """True if any directive has been recorded at least once."""
        return any(s.uses > 0 for s in self._stats.values())

    def to_dict(self) -> dict[str, dict]:
        """Snapshot of all directive stats for serialization."""
        return {name: stats.to_dict() for name, stats in self._stats.items()}

    def apply_outcome(
        self,
        directive_key: str,
        adjusted_score: float,
        outcome_confidence: float,
    ) -> None:
        """Retroactively adjust a directive's EMA with an external outcome signal.

        Only modifies EMA — does not increment uses/wins/turn counters.
        This is a correction to prior learning, not a new observation.
        """
        stats = self._stats.get(directive_key)
        if stats is None or stats.uses == 0:
            return
        blend = min(outcome_confidence, EMA_ALPHA)
        stats.ema_score = (blend * adjusted_score) + ((1 - blend) * stats.ema_score)
        self._maybe_persist()

    def _ensure(self, name: str) -> DirectiveStats:
        if name not in self._stats:
            self._stats[name] = DirectiveStats(name=name)
        return self._stats[name]

    def _maybe_persist(self) -> None:
        """Save to persistent storage if enabled."""
        if not self._persist:
            return
        self._update_count += 1
        try:
            from umh.runtime_engine.persistence import save_directive_memory

            save_directive_memory(self.to_dict(), global_turn=self._global_turn)
        except Exception:
            pass

    def _load_persisted(self) -> None:
        """Restore stats from persistent storage on cold start."""
        try:
            from umh.runtime_engine.persistence import load_directive_memory

            data = load_directive_memory()
            if data is None:
                return

            self._global_turn = data.get("global_turn", 0)
            directives = data.get("directives", {})
            for name, ddict in directives.items():
                stats = DirectiveStats(
                    name=ddict.get("name", name),
                    uses=ddict.get("uses", 0),
                    wins=ddict.get("wins", 0),
                    total_score=ddict.get("total_score", 0.0),
                    ema_score=ddict.get("ema_score", 0.0),
                    last_used_turn=ddict.get("last_used_turn", 0),
                )
                self._stats[name] = stats
        except Exception:
            pass


# ─── Module-level singleton ─────────────────────────────────────────────────

_global_memory: DirectiveMemory | None = None


def get_directive_memory(persist: bool = False) -> DirectiveMemory:
    """Return the process-wide directive memory singleton.

    Pass ``persist=True`` on the first call to enable cross-restart
    persistence via the persistence layer. Subsequent calls ignore the
    flag (singleton is already created).
    """
    global _global_memory
    if _global_memory is None:
        _global_memory = DirectiveMemory(persist=persist)
    return _global_memory


def reset_directive_memory() -> None:
    """Reset the singleton. Used in tests only."""
    global _global_memory
    _global_memory = None
