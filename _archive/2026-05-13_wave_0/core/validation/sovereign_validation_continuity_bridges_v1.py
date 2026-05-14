"""Sovereign Validation Continuity Bridges v1.

9 bridges connecting sovereign validation to substrate domains.
Uses _BaseBridge pattern with JSONL persistence.

UMH substrate subsystem. Phase 96.8CJ.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from core.validation.sovereign_operational_validation_contracts_v1 import (
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

    def record(
        self, action: str, details: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
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


class GovernanceValidationBridge(_BaseBridge):
    def __init__(self, state_dir: str | Path = "data/runtime/validation_bridges") -> None:
        super().__init__("governance_validation", state_dir)


class ReplayValidationBridge(_BaseBridge):
    def __init__(self, state_dir: str | Path = "data/runtime/validation_bridges") -> None:
        super().__init__("replay_validation", state_dir)


class ContinuityValidationBridge(_BaseBridge):
    def __init__(self, state_dir: str | Path = "data/runtime/validation_bridges") -> None:
        super().__init__("continuity_validation", state_dir)


class TopologyValidationBridge(_BaseBridge):
    def __init__(self, state_dir: str | Path = "data/runtime/validation_bridges") -> None:
        super().__init__("topology_validation", state_dir)


class ResilienceValidationBridge(_BaseBridge):
    def __init__(self, state_dir: str | Path = "data/runtime/validation_bridges") -> None:
        super().__init__("resilience_validation", state_dir)


class DeploymentValidationBridge(_BaseBridge):
    def __init__(self, state_dir: str | Path = "data/runtime/validation_bridges") -> None:
        super().__init__("deployment_validation", state_dir)


class StabilizationValidationBridge(_BaseBridge):
    def __init__(self, state_dir: str | Path = "data/runtime/validation_bridges") -> None:
        super().__init__("stabilization_validation", state_dir)


class CertificationValidationBridge(_BaseBridge):
    def __init__(self, state_dir: str | Path = "data/runtime/validation_bridges") -> None:
        super().__init__("certification_validation", state_dir)


class IntelligenceValidationBridge(_BaseBridge):
    def __init__(self, state_dir: str | Path = "data/runtime/validation_bridges") -> None:
        super().__init__("intelligence_validation", state_dir)


ALL_BRIDGE_CLASSES = [
    GovernanceValidationBridge,
    ReplayValidationBridge,
    ContinuityValidationBridge,
    TopologyValidationBridge,
    ResilienceValidationBridge,
    DeploymentValidationBridge,
    StabilizationValidationBridge,
    CertificationValidationBridge,
    IntelligenceValidationBridge,
]
