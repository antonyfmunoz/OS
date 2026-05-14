"""Context Compression Engine v1.

Compresses operational state to regulate cognition window size.
Preserves critical signals, discards noise.

Cannot silently delete signals. Cannot corrupt context.
Compression is deterministic and traceable.

UMH substrate subsystem. Phase 96.8CA.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from core.intelligence.operational_intelligence_contracts_v1 import (
    ContextCompressionState,
    IntelligenceContextWindow,
    _now_iso,
)


MAX_CONTEXT_WINDOW: int = 50
COMPRESSION_THRESHOLD: float = 0.8
NOISE_THRESHOLD: float = 0.2
MAX_COMPRESSION_HISTORY: int = 50


class ContextCompressionEngine:
    """Compresses operational context while preserving critical signals."""

    def __init__(self, state_dir: str | Path = "data/runtime/intelligence") -> None:
        self._state_dir = Path(state_dir)
        self._state_dir.mkdir(parents=True, exist_ok=True)
        self._window: IntelligenceContextWindow = IntelligenceContextWindow(
            max_signals=MAX_CONTEXT_WINDOW,
        )
        self._history: list[ContextCompressionState] = []
        self._total_compressions: int = 0

    def add_signal(self, signal: dict[str, Any]) -> bool:
        if self._window.current_size >= self._window.max_signals:
            return False
        self._window.signals.append(signal)
        self._window.current_size = len(self._window.signals)
        return True

    def needs_compression(self) -> bool:
        ratio = self._window.current_size / max(1, self._window.max_signals)
        return ratio >= COMPRESSION_THRESHOLD

    def compress(self, relevance_scores: dict[str, float] | None = None) -> ContextCompressionState:
        scores = relevance_scores or {}
        original_size = len(self._window.signals)

        preserved = []
        discarded = 0

        for sig in self._window.signals:
            sig_id = sig.get("id", sig.get("signal_id", ""))
            score = scores.get(sig_id, 0.5)
            if score >= NOISE_THRESHOLD:
                preserved.append(sig)
            else:
                discarded += 1

        compressed_size = len(preserved)
        ratio = round(compressed_size / max(1, original_size), 4)

        compression_hash = self._compute_hash({
            "original": original_size,
            "compressed": compressed_size,
            "discarded": discarded,
        })

        state = ContextCompressionState(
            original_size=original_size,
            compressed_size=compressed_size,
            compression_ratio=ratio,
            preserved_signals=compressed_size,
            discarded_signals=discarded,
            compression_hash=compression_hash,
        )

        self._window.signals = preserved
        self._window.current_size = len(preserved)
        self._window.compressed = True

        self._history.append(state)
        if len(self._history) > MAX_COMPRESSION_HISTORY:
            self._history = self._history[-MAX_COMPRESSION_HISTORY:]

        self._total_compressions += 1
        self._persist(state)
        return state

    def get_window(self) -> IntelligenceContextWindow:
        return self._window

    def get_window_usage(self) -> float:
        return self._window.current_size / max(1, self._window.max_signals)

    def reset_window(self) -> None:
        self._window = IntelligenceContextWindow(
            max_signals=MAX_CONTEXT_WINDOW,
        )

    def get_stats(self) -> dict[str, Any]:
        return {
            "total_compressions": self._total_compressions,
            "current_window_size": self._window.current_size,
            "max_window_size": self._window.max_signals,
            "window_usage": round(self.get_window_usage(), 4),
        }

    def _compute_hash(self, data: dict[str, Any]) -> str:
        serialized = json.dumps(data, sort_keys=True, default=str)
        return hashlib.sha256(serialized.encode()).hexdigest()[:16]

    def _persist(self, state: ContextCompressionState) -> None:
        path = self._state_dir / "context_compressions.jsonl"
        with path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(state.to_dict(), default=str) + "\n")
