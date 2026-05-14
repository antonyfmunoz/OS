"""Accountability Continuity Bridges v1.

9 bridges connecting accountability to substrate domains.
Uses _BaseBridge pattern with JSONL persistence.

UMH substrate subsystem. Phase 96.8CL.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from core.accountability.sovereign_operational_accountability_contracts_v1 import (
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


class ReplayAccountabilityBridge(_BaseBridge):
    def __init__(self, state_dir: str | Path = "data/runtime/accountability_bridges") -> None:
        super().__init__("replay_accountability", state_dir)


class GovernanceAccountabilityBridge(_BaseBridge):
    def __init__(self, state_dir: str | Path = "data/runtime/accountability_bridges") -> None:
        super().__init__("governance_accountability", state_dir)


class ContinuityAccountabilityBridge(_BaseBridge):
    def __init__(self, state_dir: str | Path = "data/runtime/accountability_bridges") -> None:
        super().__init__("continuity_accountability", state_dir)


class TopologyAccountabilityBridge(_BaseBridge):
    def __init__(self, state_dir: str | Path = "data/runtime/accountability_bridges") -> None:
        super().__init__("topology_accountability", state_dir)


class DeploymentAccountabilityBridge(_BaseBridge):
    def __init__(self, state_dir: str | Path = "data/runtime/accountability_bridges") -> None:
        super().__init__("deployment_accountability", state_dir)


class ValidationAccountabilityBridge(_BaseBridge):
    def __init__(self, state_dir: str | Path = "data/runtime/accountability_bridges") -> None:
        super().__init__("validation_accountability", state_dir)


class CertificationAccountabilityBridge(_BaseBridge):
    def __init__(self, state_dir: str | Path = "data/runtime/accountability_bridges") -> None:
        super().__init__("certification_accountability", state_dir)


class ExplainabilityAccountabilityBridge(_BaseBridge):
    def __init__(self, state_dir: str | Path = "data/runtime/accountability_bridges") -> None:
        super().__init__("explainability_accountability", state_dir)


class OrchestrationAccountabilityBridge(_BaseBridge):
    def __init__(self, state_dir: str | Path = "data/runtime/accountability_bridges") -> None:
        super().__init__("orchestration_accountability", state_dir)


ALL_BRIDGE_CLASSES = [
    ReplayAccountabilityBridge,
    GovernanceAccountabilityBridge,
    ContinuityAccountabilityBridge,
    TopologyAccountabilityBridge,
    DeploymentAccountabilityBridge,
    ValidationAccountabilityBridge,
    CertificationAccountabilityBridge,
    ExplainabilityAccountabilityBridge,
    OrchestrationAccountabilityBridge,
]
