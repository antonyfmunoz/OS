"""Convergence Continuity Bridges v1.

9 bridges connecting convergence to substrate domains.
Uses _BaseBridge pattern with JSONL persistence.

UMH substrate subsystem. Phase 96.8CO.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from core.convergence.repository_topology_contracts_v1 import _now_iso


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


class RuntimeConvergenceBridge(_BaseBridge):
    def __init__(self, state_dir: str | Path = "data/runtime/convergence_bridges") -> None:
        super().__init__("runtime_convergence", state_dir)


class GovernanceConvergenceBridge(_BaseBridge):
    def __init__(self, state_dir: str | Path = "data/runtime/convergence_bridges") -> None:
        super().__init__("governance_convergence", state_dir)


class ReplayConvergenceBridge(_BaseBridge):
    def __init__(self, state_dir: str | Path = "data/runtime/convergence_bridges") -> None:
        super().__init__("replay_convergence", state_dir)


class ContinuityConvergenceBridge(_BaseBridge):
    def __init__(self, state_dir: str | Path = "data/runtime/convergence_bridges") -> None:
        super().__init__("continuity_convergence", state_dir)


class ObservabilityConvergenceBridge(_BaseBridge):
    def __init__(self, state_dir: str | Path = "data/runtime/convergence_bridges") -> None:
        super().__init__("observability_convergence", state_dir)


class IngestionConvergenceBridge(_BaseBridge):
    def __init__(self, state_dir: str | Path = "data/runtime/convergence_bridges") -> None:
        super().__init__("ingestion_convergence", state_dir)


class TopologyConvergenceBridge(_BaseBridge):
    def __init__(self, state_dir: str | Path = "data/runtime/convergence_bridges") -> None:
        super().__init__("topology_convergence", state_dir)


class FederationConvergenceBridge(_BaseBridge):
    def __init__(self, state_dir: str | Path = "data/runtime/convergence_bridges") -> None:
        super().__init__("federation_convergence", state_dir)


class ConstitutionalConvergenceBridge(_BaseBridge):
    def __init__(self, state_dir: str | Path = "data/runtime/convergence_bridges") -> None:
        super().__init__("constitutional_convergence", state_dir)


ALL_BRIDGE_CLASSES = [
    RuntimeConvergenceBridge,
    GovernanceConvergenceBridge,
    ReplayConvergenceBridge,
    ContinuityConvergenceBridge,
    ObservabilityConvergenceBridge,
    IngestionConvergenceBridge,
    TopologyConvergenceBridge,
    FederationConvergenceBridge,
    ConstitutionalConvergenceBridge,
]
