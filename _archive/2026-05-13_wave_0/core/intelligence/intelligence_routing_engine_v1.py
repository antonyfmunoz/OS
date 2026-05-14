"""Intelligence Routing Engine v1.

Coordinates intelligence traversal across substrate layers.
Routes operational cognition with deterministic paths.

Cannot create hidden routing mutations.
Cannot create recursive intelligence traversal.

UMH substrate subsystem. Phase 96.8CA.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from core.intelligence.operational_intelligence_contracts_v1 import (
    IntelligenceRoutingState,
    _new_id,
    _now_iso,
)


KNOWN_LAYERS: list[str] = [
    "ingress", "cognition", "workflows", "operations",
    "sessions", "environments", "scaling", "resilience",
    "continuity", "observability",
]

MAX_ROUTING_DEPTH: int = 5
MAX_ROUTING_FANOUT: int = 3
MAX_ROUTING_HISTORY: int = 100


class IntelligenceRoutingEngine:
    """Routes operational intelligence across substrate layers."""

    def __init__(self, state_dir: str | Path = "data/runtime/intelligence") -> None:
        self._state_dir = Path(state_dir)
        self._state_dir.mkdir(parents=True, exist_ok=True)
        self._routes: list[IntelligenceRoutingState] = []
        self._total_routes: int = 0
        self._total_denied: int = 0

    def route(
        self,
        source_layer: str,
        target_layer: str,
        signal_ids: list[str],
        routing_chain: list[str] | None = None,
    ) -> IntelligenceRoutingState | None:
        if source_layer not in KNOWN_LAYERS:
            self._total_denied += 1
            return None
        if target_layer not in KNOWN_LAYERS:
            self._total_denied += 1
            return None
        if source_layer == target_layer:
            self._total_denied += 1
            return None

        chain = routing_chain or []
        if len(chain) >= MAX_ROUTING_DEPTH:
            self._total_denied += 1
            return None
        if target_layer in chain:
            self._total_denied += 1
            return None

        bounded_signals = signal_ids[:MAX_ROUTING_FANOUT]

        routing_hash = self._compute_hash({
            "source": source_layer,
            "target": target_layer,
            "signals": sorted(bounded_signals),
        })

        state = IntelligenceRoutingState(
            source_layer=source_layer,
            target_layer=target_layer,
            signal_ids=bounded_signals,
            routing_hash=routing_hash,
        )

        self._routes.append(state)
        if len(self._routes) > MAX_ROUTING_HISTORY:
            self._routes = self._routes[-MAX_ROUTING_HISTORY:]

        self._total_routes += 1

        path = self._state_dir / "intelligence_routing.jsonl"
        with path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(state.to_dict(), default=str) + "\n")

        return state

    def get_routes_from(self, source_layer: str) -> list[IntelligenceRoutingState]:
        return [r for r in self._routes if r.source_layer == source_layer]

    def get_routes_to(self, target_layer: str) -> list[IntelligenceRoutingState]:
        return [r for r in self._routes if r.target_layer == target_layer]

    def get_stats(self) -> dict[str, Any]:
        return {
            "total_routes": self._total_routes,
            "total_denied": self._total_denied,
            "active_routes": len(self._routes),
        }

    def _compute_hash(self, data: dict[str, Any]) -> str:
        serialized = json.dumps(data, sort_keys=True, default=str)
        return hashlib.sha256(serialized.encode()).hexdigest()[:16]
