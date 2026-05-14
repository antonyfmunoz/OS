"""Explainability Continuity Bridges v1.

9 bridges connecting explainability to substrate domains.
Uses _BaseBridge pattern with JSONL persistence.

UMH substrate subsystem. Phase 96.8CK.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from core.explainability.constitutional_explainability_contracts_v1 import (
    _now_iso,
)


class _BaseBridge:
    """Base bridge with JSONL persistence."""

    def __init__(self, bridge_name: str, state_dir: str | Path) -> None:
        self._bridge_name = bridge_name
        self._state_dir = Path(state_dir)
        self._state_dir.mkdir(parents=True, exist_ok=True)
        self._records: list[dict[str, Any]] = []

    def record(self, action: str, details: dict[str, Any] | None = None) -> dict[str, Any]:
        entry = {
            "bridge": self._bridge_name,
            "action": action,
            "timestamp": _now_iso(),
            **(details or {}),
        }
        self._records.append(entry)
        filepath = self._state_dir / f"{self._bridge_name}.jsonl"
        with open(filepath, "a") as f:
            f.write(json.dumps(entry) + "\n")
        return entry

    def get_records(self) -> list[dict[str, Any]]:
        return list(self._records)

    def get_stats(self) -> dict[str, Any]:
        return {"bridge_name": self._bridge_name, "total_records": len(self._records)}


class GovernanceExplainabilityBridge(_BaseBridge):
    def __init__(self, state_dir: str | Path = "data/runtime/explainability_bridges") -> None:
        super().__init__("governance_explainability", state_dir)


class ReplayExplainabilityBridge(_BaseBridge):
    def __init__(self, state_dir: str | Path = "data/runtime/explainability_bridges") -> None:
        super().__init__("replay_explainability", state_dir)


class ContinuityExplainabilityBridge(_BaseBridge):
    def __init__(self, state_dir: str | Path = "data/runtime/explainability_bridges") -> None:
        super().__init__("continuity_explainability", state_dir)


class TopologyExplainabilityBridge(_BaseBridge):
    def __init__(self, state_dir: str | Path = "data/runtime/explainability_bridges") -> None:
        super().__init__("topology_explainability", state_dir)


class DeploymentExplainabilityBridge(_BaseBridge):
    def __init__(self, state_dir: str | Path = "data/runtime/explainability_bridges") -> None:
        super().__init__("deployment_explainability", state_dir)


class ValidationExplainabilityBridge(_BaseBridge):
    def __init__(self, state_dir: str | Path = "data/runtime/explainability_bridges") -> None:
        super().__init__("validation_explainability", state_dir)


class CertificationExplainabilityBridge(_BaseBridge):
    def __init__(self, state_dir: str | Path = "data/runtime/explainability_bridges") -> None:
        super().__init__("certification_explainability", state_dir)


class IntelligenceExplainabilityBridge(_BaseBridge):
    def __init__(self, state_dir: str | Path = "data/runtime/explainability_bridges") -> None:
        super().__init__("intelligence_explainability", state_dir)


class OrchestrationExplainabilityBridge(_BaseBridge):
    def __init__(self, state_dir: str | Path = "data/runtime/explainability_bridges") -> None:
        super().__init__("orchestration_explainability", state_dir)


ALL_BRIDGE_CLASSES = [
    GovernanceExplainabilityBridge,
    ReplayExplainabilityBridge,
    ContinuityExplainabilityBridge,
    TopologyExplainabilityBridge,
    DeploymentExplainabilityBridge,
    ValidationExplainabilityBridge,
    CertificationExplainabilityBridge,
    IntelligenceExplainabilityBridge,
    OrchestrationExplainabilityBridge,
]
