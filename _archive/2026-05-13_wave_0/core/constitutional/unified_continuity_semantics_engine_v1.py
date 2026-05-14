"""Unified Continuity Semantics Engine v1.

Unifies session, workflow, deployment, cognition, application,
and environment continuity into coherent cross-layer semantics.

UMH substrate subsystem. Phase 96.8CG.
"""

from __future__ import annotations

from typing import Any

from core.constitutional.constitutional_runtime_contracts_v1 import (
    UnifiedContinuityState,
    _now_iso,
)

KNOWN_CONTINUITY_LAYERS = [
    "session",
    "workflow",
    "deployment",
    "cognition",
    "application",
    "environment",
]


class UnifiedContinuitySemanticsEngine:
    """Validates continuity semantics across all substrate layers."""

    def __init__(self) -> None:
        self._layer_states: dict[str, dict[str, Any]] = {}

    def validate_layer_continuity(
        self,
        layer: str,
        checkpoints_deterministic: bool = True,
        restoration_verified: bool = True,
        lineage_preserved: bool = True,
        session_chain_unbroken: bool = True,
    ) -> dict[str, Any]:
        if layer not in KNOWN_CONTINUITY_LAYERS:
            raise ValueError(
                f"Unknown layer: {layer}. Known: {KNOWN_CONTINUITY_LAYERS}"
            )

        coherent = all([
            checkpoints_deterministic,
            restoration_verified,
            lineage_preserved,
            session_chain_unbroken,
        ])

        result = {
            "layer": layer,
            "checkpoints_deterministic": checkpoints_deterministic,
            "restoration_verified": restoration_verified,
            "lineage_preserved": lineage_preserved,
            "session_chain_unbroken": session_chain_unbroken,
            "coherent": coherent,
            "timestamp": _now_iso(),
        }
        self._layer_states[layer] = result
        return result

    def get_unified_state(self) -> UnifiedContinuityState:
        coherent = all(
            r.get("coherent", False) for r in self._layer_states.values()
        )
        return UnifiedContinuityState(
            layers_synchronized=len(self._layer_states),
            continuity_coherent=coherent,
        )

    def get_incoherent_layers(self) -> list[str]:
        return [
            layer for layer, state in self._layer_states.items()
            if not state.get("coherent", False)
        ]

    def get_stats(self) -> dict[str, object]:
        return {
            "layers_validated": len(self._layer_states),
            "coherent_count": sum(
                1 for r in self._layer_states.values()
                if r.get("coherent", False)
            ),
            "incoherent_count": sum(
                1 for r in self._layer_states.values()
                if not r.get("coherent", False)
            ),
        }
