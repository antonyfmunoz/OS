"""Intelligence Synthesis Engine v1.

Synthesizes cross-layer operational state into bounded intelligence.
Composes operational context from 9 substrate layers.

Cannot create objectives. Cannot self-direct.
Synthesis is deterministic and operator-anchored.

UMH substrate subsystem. Phase 96.8CA.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from core.intelligence.operational_intelligence_contracts_v1 import (
    IntelligenceSynthesisState,
    OperationalSignalCluster,
    SignalSource,
    _new_id,
    _now_iso,
)


KNOWN_SOURCES: list[str] = [s.value for s in SignalSource]
MAX_SIGNALS_PER_SYNTHESIS: int = 100
MAX_CLUSTERS: int = 20
MAX_SYNTHESIS_HISTORY: int = 50


class IntelligenceSynthesisEngine:
    """Synthesizes cross-layer operational state."""

    def __init__(self, state_dir: str | Path = "data/runtime/intelligence") -> None:
        self._state_dir = Path(state_dir)
        self._state_dir.mkdir(parents=True, exist_ok=True)
        self._history: list[IntelligenceSynthesisState] = []
        self._clusters: list[OperationalSignalCluster] = []
        self._total_syntheses: int = 0

    def synthesize(
        self,
        signals: dict[str, list[dict[str, Any]]],
        operator_intent: str = "",
    ) -> IntelligenceSynthesisState:
        sources = [s for s in signals if s in KNOWN_SOURCES]
        all_signal_ids: list[str] = []

        for source in sources:
            for sig in signals[source][:MAX_SIGNALS_PER_SYNTHESIS]:
                sid = sig.get("id", sig.get("signal_id", _new_id("sig")))
                all_signal_ids.append(sid)

        synthesis_hash = self._compute_hash({
            "sources": sorted(sources),
            "signal_count": len(all_signal_ids),
            "operator_intent": operator_intent,
        })

        state = IntelligenceSynthesisState(
            sources=sources,
            signal_count=len(all_signal_ids),
            synthesis_hash=synthesis_hash,
            operator_intent=operator_intent,
        )

        self._history.append(state)
        if len(self._history) > MAX_SYNTHESIS_HISTORY:
            self._history = self._history[-MAX_SYNTHESIS_HISTORY:]

        self._total_syntheses += 1
        self._persist_synthesis(state)
        return state

    def cluster_signals(
        self,
        signals: list[dict[str, Any]],
        source: str = "",
        cluster_type: str = "",
    ) -> OperationalSignalCluster:
        signal_ids = [
            s.get("id", s.get("signal_id", "")) for s in signals
        ]
        weight = len(signals) / max(1, MAX_SIGNALS_PER_SYNTHESIS)

        cluster = OperationalSignalCluster(
            signal_ids=signal_ids[:MAX_SIGNALS_PER_SYNTHESIS],
            source=source,
            cluster_type=cluster_type,
            weight=round(min(1.0, weight), 4),
        )

        self._clusters.append(cluster)
        if len(self._clusters) > MAX_CLUSTERS:
            self._clusters = self._clusters[-MAX_CLUSTERS:]

        return cluster

    def get_latest_synthesis(self) -> IntelligenceSynthesisState | None:
        if not self._history:
            return None
        return self._history[-1]

    def get_clusters(self) -> list[OperationalSignalCluster]:
        return list(self._clusters)

    def get_stats(self) -> dict[str, Any]:
        return {
            "total_syntheses": self._total_syntheses,
            "history_length": len(self._history),
            "active_clusters": len(self._clusters),
        }

    def _compute_hash(self, data: dict[str, Any]) -> str:
        serialized = json.dumps(data, sort_keys=True, default=str)
        return hashlib.sha256(serialized.encode()).hexdigest()[:16]

    def _persist_synthesis(self, state: IntelligenceSynthesisState) -> None:
        path = self._state_dir / "intelligence_synthesis.jsonl"
        with path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(state.to_dict(), default=str) + "\n")
