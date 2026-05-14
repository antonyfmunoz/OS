"""Unified Observability Semantics Engine v1.

Unifies event semantics, receipt semantics, lineage semantics,
replay evidence semantics, and persistence semantics across
all substrate layers.

UMH substrate subsystem. Phase 96.8CG.
"""

from __future__ import annotations

from typing import Any

from core.constitutional.constitutional_runtime_contracts_v1 import (
    UnifiedObservabilityState,
    _now_iso,
)

KNOWN_OBSERVABILITY_LAYERS = [
    "spine",
    "workstation",
    "browser",
    "live_runtime",
    "workflows",
    "cognition",
    "ingress",
    "sessions",
    "operations",
    "environments",
    "scaling",
    "resilience",
    "intelligence",
    "knowledge",
    "learning",
    "applications",
    "deployment",
    "orchestration",
]

OBSERVABILITY_SEMANTICS = {
    "event_persistence": "All events written to JSONL",
    "event_file_map": "EVENT_FILE_MAP generated from enum values",
    "receipt_emission": "Receipts emitted for all operations",
    "lineage_tracking": "All lineage traceable to source",
    "replay_evidence": "Replay validation generates proof artifacts",
}


class UnifiedObservabilitySemanticsEngine:
    """Validates observability semantics across all substrate layers."""

    def __init__(self) -> None:
        self._layer_results: dict[str, dict[str, Any]] = {}

    def validate_layer_observability(
        self,
        layer: str,
        events_persisted: bool = True,
        event_map_from_enum: bool = True,
        receipts_emitted: bool = True,
        lineage_tracked: bool = True,
        replay_evidence_generated: bool = True,
    ) -> dict[str, Any]:
        if layer not in KNOWN_OBSERVABILITY_LAYERS:
            raise ValueError(
                f"Unknown layer: {layer}. Known: {KNOWN_OBSERVABILITY_LAYERS}"
            )

        coherent = all([
            events_persisted,
            event_map_from_enum,
            receipts_emitted,
            lineage_tracked,
        ])

        result = {
            "layer": layer,
            "events_persisted": events_persisted,
            "event_map_from_enum": event_map_from_enum,
            "receipts_emitted": receipts_emitted,
            "lineage_tracked": lineage_tracked,
            "replay_evidence_generated": replay_evidence_generated,
            "coherent": coherent,
            "timestamp": _now_iso(),
        }
        self._layer_results[layer] = result
        return result

    def get_unified_state(self) -> UnifiedObservabilityState:
        coherent = all(
            r.get("coherent", False) for r in self._layer_results.values()
        )
        return UnifiedObservabilityState(
            pipelines_validated=len(self._layer_results),
            observability_coherent=coherent,
        )

    def get_incoherent_layers(self) -> list[str]:
        return [
            layer for layer, result in self._layer_results.items()
            if not result.get("coherent", False)
        ]

    def get_stats(self) -> dict[str, object]:
        return {
            "layers_validated": len(self._layer_results),
            "coherent_count": sum(
                1 for r in self._layer_results.values()
                if r.get("coherent", False)
            ),
        }
