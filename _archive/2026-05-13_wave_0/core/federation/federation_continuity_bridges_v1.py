"""Federation Continuity Bridges v1.

9 bridges connecting federation to substrate domains.
Uses _BaseBridge pattern with JSONL persistence.

UMH substrate subsystem. Phase 96.8CN.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from core.federation.sovereign_federation_readiness_contracts_v1 import _now_iso


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


class TrustFederationBridge(_BaseBridge):
    def __init__(self, state_dir: str | Path = "data/runtime/federation_bridges") -> None:
        super().__init__("trust_federation", state_dir)


class CertificationFederationBridge(_BaseBridge):
    def __init__(self, state_dir: str | Path = "data/runtime/federation_bridges") -> None:
        super().__init__("certification_federation", state_dir)


class ValidationFederationBridge(_BaseBridge):
    def __init__(self, state_dir: str | Path = "data/runtime/federation_bridges") -> None:
        super().__init__("validation_federation", state_dir)


class AccountabilityFederationBridge(_BaseBridge):
    def __init__(self, state_dir: str | Path = "data/runtime/federation_bridges") -> None:
        super().__init__("accountability_federation", state_dir)


class ExplainabilityFederationBridge(_BaseBridge):
    def __init__(self, state_dir: str | Path = "data/runtime/federation_bridges") -> None:
        super().__init__("explainability_federation", state_dir)


class TopologyFederationBridge(_BaseBridge):
    def __init__(self, state_dir: str | Path = "data/runtime/federation_bridges") -> None:
        super().__init__("topology_federation", state_dir)


class ObservabilityFederationBridge(_BaseBridge):
    def __init__(self, state_dir: str | Path = "data/runtime/federation_bridges") -> None:
        super().__init__("observability_federation", state_dir)


class ReplayFederationBridge(_BaseBridge):
    def __init__(self, state_dir: str | Path = "data/runtime/federation_bridges") -> None:
        super().__init__("replay_federation", state_dir)


class GovernanceFederationBridge(_BaseBridge):
    def __init__(self, state_dir: str | Path = "data/runtime/federation_bridges") -> None:
        super().__init__("governance_federation", state_dir)


ALL_BRIDGE_CLASSES = [
    TrustFederationBridge,
    CertificationFederationBridge,
    ValidationFederationBridge,
    AccountabilityFederationBridge,
    ExplainabilityFederationBridge,
    TopologyFederationBridge,
    ObservabilityFederationBridge,
    ReplayFederationBridge,
    GovernanceFederationBridge,
]
