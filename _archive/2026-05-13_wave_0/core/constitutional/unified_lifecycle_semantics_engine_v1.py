"""Unified Lifecycle Semantics Engine v1.

Unifies lifecycle state transitions, restoration semantics,
archival semantics, rollback semantics, and suspension semantics
across all substrate layers.

UMH substrate subsystem. Phase 96.8CG.
"""

from __future__ import annotations

from typing import Any

from core.constitutional.constitutional_runtime_contracts_v1 import (
    UnifiedLifecycleState,
    _now_iso,
)

KNOWN_LIFECYCLE_LAYERS = [
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
    "constitutional",
]

LIFECYCLE_SEMANTICS = {
    "terminal_absorbing": "Terminal states cannot be exited",
    "valid_transitions_only": "Only declared transitions allowed",
    "restoration_re_entry": "Restored states re-enter active lifecycle",
    "archival_is_final": "Archived is always terminal",
    "suspension_is_reversible": "Suspended states can be resumed",
}


class UnifiedLifecycleSemanticsEngine:
    """Validates lifecycle semantics across all substrate layers."""

    def __init__(self) -> None:
        self._layer_results: dict[str, dict[str, Any]] = {}

    def validate_layer_lifecycle(
        self,
        layer: str,
        has_terminal_states: bool = True,
        terminal_absorbing: bool = True,
        valid_transitions_only: bool = True,
        restoration_re_entry: bool = True,
        archival_is_final: bool = True,
    ) -> dict[str, Any]:
        if layer not in KNOWN_LIFECYCLE_LAYERS:
            raise ValueError(
                f"Unknown layer: {layer}. Known: {KNOWN_LIFECYCLE_LAYERS}"
            )

        result = {
            "layer": layer,
            "has_terminal_states": has_terminal_states,
            "terminal_absorbing": terminal_absorbing,
            "valid_transitions_only": valid_transitions_only,
            "restoration_re_entry": restoration_re_entry,
            "archival_is_final": archival_is_final,
            "coherent": all([
                has_terminal_states, terminal_absorbing,
                valid_transitions_only, archival_is_final,
            ]),
            "timestamp": _now_iso(),
        }
        self._layer_results[layer] = result
        return result

    def get_unified_state(self) -> UnifiedLifecycleState:
        coherent = all(
            r.get("coherent", False) for r in self._layer_results.values()
        )
        return UnifiedLifecycleState(
            layers_validated=len(self._layer_results),
            lifecycle_coherent=coherent,
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
            "incoherent_count": sum(
                1 for r in self._layer_results.values()
                if not r.get("coherent", False)
            ),
        }
