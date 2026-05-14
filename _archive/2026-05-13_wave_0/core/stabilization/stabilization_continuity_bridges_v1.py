"""Stabilization Continuity Bridges v1.

9 bridges connecting stabilization to substrate domains.
Uses _BaseBridge pattern with JSONL persistence.

UMH substrate subsystem. Phase 96.8CH.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from core.stabilization.constitutional_operational_fabric_contracts_v1 import (
    _now_iso,
)


class _BaseBridge:
    """Base bridge with JSONL persistence."""

    def __init__(
        self, bridge_name: str, state_dir: str | Path,
    ) -> None:
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
        return {
            "bridge_name": self._bridge_name,
            "total_records": len(self._records),
        }


class ConcurrencyStabilizationBridge(_BaseBridge):
    def __init__(self, state_dir: str | Path = "data/runtime/stabilization_bridges") -> None:
        super().__init__("concurrency_stabilization", state_dir)


class ReplayStabilizationBridge(_BaseBridge):
    def __init__(self, state_dir: str | Path = "data/runtime/stabilization_bridges") -> None:
        super().__init__("replay_stabilization", state_dir)


class ContinuityStabilizationBridge(_BaseBridge):
    def __init__(self, state_dir: str | Path = "data/runtime/stabilization_bridges") -> None:
        super().__init__("continuity_stabilization", state_dir)


class TopologyStabilizationBridge(_BaseBridge):
    def __init__(self, state_dir: str | Path = "data/runtime/stabilization_bridges") -> None:
        super().__init__("topology_stabilization", state_dir)


class ResilienceStabilizationBridge(_BaseBridge):
    def __init__(self, state_dir: str | Path = "data/runtime/stabilization_bridges") -> None:
        super().__init__("resilience_stabilization", state_dir)


class GovernanceStabilizationBridge(_BaseBridge):
    def __init__(self, state_dir: str | Path = "data/runtime/stabilization_bridges") -> None:
        super().__init__("governance_stabilization", state_dir)


class DeploymentStabilizationBridge(_BaseBridge):
    def __init__(self, state_dir: str | Path = "data/runtime/stabilization_bridges") -> None:
        super().__init__("deployment_stabilization", state_dir)


class OrchestrationStabilizationBridge(_BaseBridge):
    def __init__(self, state_dir: str | Path = "data/runtime/stabilization_bridges") -> None:
        super().__init__("orchestration_stabilization", state_dir)


class ObservabilityStabilizationBridge(_BaseBridge):
    def __init__(self, state_dir: str | Path = "data/runtime/stabilization_bridges") -> None:
        super().__init__("observability_stabilization", state_dir)


ALL_BRIDGE_CLASSES = [
    ConcurrencyStabilizationBridge,
    ReplayStabilizationBridge,
    ContinuityStabilizationBridge,
    TopologyStabilizationBridge,
    ResilienceStabilizationBridge,
    GovernanceStabilizationBridge,
    DeploymentStabilizationBridge,
    OrchestrationStabilizationBridge,
    ObservabilityStabilizationBridge,
]
