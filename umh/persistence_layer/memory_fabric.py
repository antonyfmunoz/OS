"""
MemoryFabric — unified append-only memory for all EOS learning signals.

Every subsystem (StrategyMemory, WorldStateEngine, MetaWeightEngine,
DirectiveEngine) records learning events to the fabric.  All subsystems
can query the fabric for cross-cutting aggregation that no single
system has.

Append-only.  Bounded (MAX_ENTRIES with FIFO eviction).
Deterministic aggregation (EMA).  No LLM calls.  No randomness.
Stored entries are never mutated after recording.

Entry types::

    strategy_outcome — strategy was evaluated, won/lost, scored
    state_observation — world state was observed and clustered
    signal_outcome   — influence signal correlated with outcome
    directive_event  — directive was created, evolved, or expired
    plan_outcome     — plan step was attributed a score
    credit_event     — causal credit was assigned to an entity

Usage::

    from umh.persistence_layer.memory_fabric import get_memory_fabric

    fabric = get_memory_fabric()
    fabric.record(MemoryEntry(
        entry_type=EntryType.STRATEGY_OUTCOME,
        turn=5,
        features={"strategy": "direct", "quality": 0.8},
        outcome=0.75,
    ))

    results = fabric.query(entry_type=EntryType.STRATEGY_OUTCOME)
    agg = fabric.aggregate()
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class EntryType(Enum):
    STRATEGY_OUTCOME = "strategy_outcome"
    STATE_OBSERVATION = "state_observation"
    SIGNAL_OUTCOME = "signal_outcome"
    DIRECTIVE_EVENT = "directive_event"
    PLAN_OUTCOME = "plan_outcome"
    CREDIT_EVENT = "credit_event"


MAX_ENTRIES = 500
AGG_ALPHA = 0.20
MIN_ENTRIES_FOR_AGG = 3


def _clamp(v: float, lo: float, hi: float) -> float:
    if v < lo:
        return lo
    if v > hi:
        return hi
    return v


@dataclass(frozen=True)
class MemoryEntry:
    """A single learning event recorded to the fabric.

    Immutable after creation — append-only semantics.
    """

    entry_type: EntryType
    turn: int
    features: dict[str, float | str]
    outcome: float
    source: str = ""
    entry_id: str = ""

    def to_dict(self) -> dict:
        return {
            "entry_type": self.entry_type.value,
            "turn": self.turn,
            "features": dict(self.features),
            "outcome": round(self.outcome, 4),
            "source": self.source,
            "entry_id": self.entry_id,
        }


@dataclass(frozen=True)
class AggregationResult:
    """Deterministic summary of fabric contents."""

    total_entries: int
    entries_by_type: dict[str, int]
    outcome_ema_by_type: dict[str, float]
    feature_emas: dict[str, float]
    recent_outcome_trend: float
    oldest_turn: int
    newest_turn: int

    def to_dict(self) -> dict:
        return {
            "total_entries": self.total_entries,
            "entries_by_type": dict(self.entries_by_type),
            "outcome_ema_by_type": {
                k: round(v, 4) for k, v in self.outcome_ema_by_type.items()
            },
            "feature_emas": {k: round(v, 4) for k, v in self.feature_emas.items()},
            "recent_outcome_trend": round(self.recent_outcome_trend, 4),
            "oldest_turn": self.oldest_turn,
            "newest_turn": self.newest_turn,
        }


NO_AGGREGATION = AggregationResult(
    total_entries=0,
    entries_by_type={},
    outcome_ema_by_type={},
    feature_emas={},
    recent_outcome_trend=0.0,
    oldest_turn=0,
    newest_turn=0,
)


@dataclass(frozen=True)
class FabricSnapshot:
    """Immutable snapshot of fabric state for a single turn."""

    entries_written: tuple[str, ...]
    queries_used: tuple[str, ...]
    aggregation_summary: dict

    def to_dict(self) -> dict:
        return {
            "entries_written": list(self.entries_written),
            "queries_used": list(self.queries_used),
            "aggregation_summary": self.aggregation_summary,
        }


NO_SNAPSHOT = FabricSnapshot(
    entries_written=(),
    queries_used=(),
    aggregation_summary={},
)


class MemoryFabric:
    """Unified append-only memory for all EOS learning signals.

    Bounded to MAX_ENTRIES with FIFO eviction.  Entries are never
    mutated after recording.  Aggregation is deterministic (EMA).
    """

    def __init__(self, max_entries: int = MAX_ENTRIES) -> None:
        self._entries: list[MemoryEntry] = []
        self._max_entries = max_entries
        self._entry_counter: int = 0
        self._turn_writes: list[str] = []
        self._turn_queries: list[str] = []

    @property
    def entry_count(self) -> int:
        return len(self._entries)

    def record(self, entry: MemoryEntry) -> str:
        """Append a learning event to the fabric.

        Assigns a unique entry_id if not provided.  Evicts oldest
        entries when capacity is exceeded.  Returns the entry_id.
        """
        self._entry_counter += 1
        eid = entry.entry_id or f"mf_{self._entry_counter}"

        if not entry.entry_id:
            entry = MemoryEntry(
                entry_type=entry.entry_type,
                turn=entry.turn,
                features=entry.features,
                outcome=entry.outcome,
                source=entry.source,
                entry_id=eid,
            )

        self._entries.append(entry)
        self._turn_writes.append(eid)

        if len(self._entries) > self._max_entries:
            self._entries = self._entries[-self._max_entries :]

        return eid

    def query(
        self,
        entry_type: EntryType | None = None,
        source: str | None = None,
        min_turn: int | None = None,
        max_turn: int | None = None,
        feature_key: str | None = None,
        feature_value: str | float | None = None,
        limit: int | None = None,
    ) -> list[MemoryEntry]:
        """Query entries with optional filters.

        All filters are AND-combined.  Returns entries in chronological
        order (oldest first).  Deterministic.
        """
        query_desc = f"type={entry_type},src={source},turns=[{min_turn},{max_turn}]"
        self._turn_queries.append(query_desc)

        results: list[MemoryEntry] = []
        for e in self._entries:
            if entry_type is not None and e.entry_type != entry_type:
                continue
            if source is not None and e.source != source:
                continue
            if min_turn is not None and e.turn < min_turn:
                continue
            if max_turn is not None and e.turn > max_turn:
                continue
            if feature_key is not None:
                fv = e.features.get(feature_key)
                if fv is None:
                    continue
                if feature_value is not None and fv != feature_value:
                    continue
            results.append(e)

        if limit is not None and len(results) > limit:
            results = results[-limit:]

        return results

    def _query_internal(
        self,
        entry_type: EntryType | None = None,
        min_turn: int | None = None,
    ) -> list[MemoryEntry]:
        """Internal query that does not track in _turn_queries."""
        results: list[MemoryEntry] = []
        for e in self._entries:
            if entry_type is not None and e.entry_type != entry_type:
                continue
            if min_turn is not None and e.turn < min_turn:
                continue
            results.append(e)
        return results

    def _aggregate_internal(
        self,
        entry_type: EntryType | None = None,
        min_turn: int | None = None,
    ) -> AggregationResult:
        """Internal aggregation that does not track queries."""
        return self._compute_aggregation(
            self._query_internal(entry_type=entry_type, min_turn=min_turn)
        )

    @staticmethod
    def _compute_aggregation(entries: list[MemoryEntry]) -> AggregationResult:
        """Compute deterministic EMA-based summary from a list of entries."""
        if not entries:
            return NO_AGGREGATION

        counts: dict[str, int] = {}
        outcome_emas: dict[str, float] = {}
        feature_emas: dict[str, float] = {}
        feature_counts: dict[str, int] = {}

        for e in entries:
            t = e.entry_type.value
            counts[t] = counts.get(t, 0) + 1

            if t not in outcome_emas:
                outcome_emas[t] = e.outcome
            else:
                outcome_emas[t] = (
                    AGG_ALPHA * e.outcome + (1.0 - AGG_ALPHA) * outcome_emas[t]
                )

            for k, v in e.features.items():
                if not isinstance(v, (int, float)):
                    continue
                fv = float(v)
                if k not in feature_emas:
                    feature_emas[k] = fv
                    feature_counts[k] = 1
                else:
                    feature_emas[k] = (
                        AGG_ALPHA * fv + (1.0 - AGG_ALPHA) * feature_emas[k]
                    )
                    feature_counts[k] += 1

        recent_trend = 0.0
        if len(entries) >= 2:
            half = len(entries) // 2
            first_half = entries[:half]
            second_half = entries[half:]
            avg_first = sum(e.outcome for e in first_half) / len(first_half)
            avg_second = sum(e.outcome for e in second_half) / len(second_half)
            recent_trend = avg_second - avg_first

        return AggregationResult(
            total_entries=len(entries),
            entries_by_type=counts,
            outcome_ema_by_type=outcome_emas,
            feature_emas=feature_emas,
            recent_outcome_trend=recent_trend,
            oldest_turn=entries[0].turn,
            newest_turn=entries[-1].turn,
        )

    def aggregate(
        self,
        entry_type: EntryType | None = None,
        min_turn: int | None = None,
    ) -> AggregationResult:
        """Compute deterministic EMA-based summary of fabric contents.

        Walks entries chronologically.  EMA ensures recent entries
        dominate.  Deterministic: same entries → same result.
        """
        entries = self.query(entry_type=entry_type, min_turn=min_turn)
        return self._compute_aggregation(entries)

    def get_outcome_ema(
        self,
        entry_type: EntryType,
        feature_key: str | None = None,
        feature_value: str | float | None = None,
    ) -> float | None:
        """Get the EMA outcome for a specific entry type/feature combo.

        Returns None if fewer than MIN_ENTRIES_FOR_AGG entries match.
        """
        entries = self.query(
            entry_type=entry_type,
            feature_key=feature_key,
            feature_value=feature_value,
        )
        if len(entries) < MIN_ENTRIES_FOR_AGG:
            return None

        ema = entries[0].outcome
        for e in entries[1:]:
            ema = AGG_ALPHA * e.outcome + (1.0 - AGG_ALPHA) * ema
        return ema

    def flush_turn_tracking(self) -> FabricSnapshot:
        """Capture and reset per-turn write/query tracking.

        Returns a FabricSnapshot for DecisionTrace integration.
        Called once per turn after all subsystems have written.
        """
        writes = tuple(self._turn_writes)
        queries = tuple(self._turn_queries)
        self._turn_writes = []
        self._turn_queries = []

        agg = self._aggregate_internal()
        snap = FabricSnapshot(
            entries_written=writes,
            queries_used=queries,
            aggregation_summary=agg.to_dict() if agg.total_entries > 0 else {},
        )
        return snap

    def snapshot(self) -> dict:
        """Serialize fabric state for persistence."""
        return {
            "entry_count": len(self._entries),
            "entry_counter": self._entry_counter,
            "max_entries": self._max_entries,
            "entries": [e.to_dict() for e in self._entries],
        }

    def restore(self, data: dict) -> None:
        """Restore fabric state from serialized data."""
        self._entry_counter = data.get("entry_counter", 0)
        self._max_entries = data.get("max_entries", MAX_ENTRIES)
        self._entries = []
        for ed in data.get("entries", []):
            self._entries.append(
                MemoryEntry(
                    entry_type=EntryType(ed["entry_type"]),
                    turn=ed["turn"],
                    features=ed["features"],
                    outcome=ed["outcome"],
                    source=ed.get("source", ""),
                    entry_id=ed.get("entry_id", ""),
                )
            )

    def reset(self) -> None:
        """Clear all fabric state."""
        self._entries = []
        self._entry_counter = 0
        self._turn_writes = []
        self._turn_queries = []


_fabric: MemoryFabric | None = None


def get_memory_fabric() -> MemoryFabric:
    """Singleton accessor.

    On first access, attempts to restore from persisted state.
    Falls back cleanly to empty state if persistence is unavailable.
    Restored state respects the current MAX_ENTRIES cap immediately.
    """
    global _fabric
    if _fabric is None:
        _fabric = MemoryFabric()
        try:
            from umh.persistence_layer.persistence import load_memory_fabric

            data = load_memory_fabric()
            if data is not None:
                _fabric.restore(data)
                if len(_fabric._entries) > _fabric._max_entries:
                    _fabric._entries = _fabric._entries[-_fabric._max_entries :]
        except Exception:
            pass
    return _fabric
