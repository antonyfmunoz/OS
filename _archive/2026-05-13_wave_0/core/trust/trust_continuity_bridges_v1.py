"""Trust Continuity Bridges v1.

9 bridges connecting trust to substrate domains.
Uses _BaseBridge pattern with JSONL persistence.

UMH substrate subsystem. Phase 96.8CM.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from core.trust.sovereign_operational_trust_contracts_v1 import _now_iso


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


class CertificationTrustBridge(_BaseBridge):
    def __init__(self, state_dir: str | Path = "data/runtime/trust_bridges") -> None:
        super().__init__("certification_trust", state_dir)


class ValidationTrustBridge(_BaseBridge):
    def __init__(self, state_dir: str | Path = "data/runtime/trust_bridges") -> None:
        super().__init__("validation_trust", state_dir)


class ExplainabilityTrustBridge(_BaseBridge):
    def __init__(self, state_dir: str | Path = "data/runtime/trust_bridges") -> None:
        super().__init__("explainability_trust", state_dir)


class AccountabilityTrustBridge(_BaseBridge):
    def __init__(self, state_dir: str | Path = "data/runtime/trust_bridges") -> None:
        super().__init__("accountability_trust", state_dir)


class ReplayTrustBridge(_BaseBridge):
    def __init__(self, state_dir: str | Path = "data/runtime/trust_bridges") -> None:
        super().__init__("replay_trust", state_dir)


class ProvenanceTrustBridge(_BaseBridge):
    def __init__(self, state_dir: str | Path = "data/runtime/trust_bridges") -> None:
        super().__init__("provenance_trust", state_dir)


class ChronologyTrustBridge(_BaseBridge):
    def __init__(self, state_dir: str | Path = "data/runtime/trust_bridges") -> None:
        super().__init__("chronology_trust", state_dir)


class GovernanceTrustBridge(_BaseBridge):
    def __init__(self, state_dir: str | Path = "data/runtime/trust_bridges") -> None:
        super().__init__("governance_trust", state_dir)


class ObservabilityTrustBridge(_BaseBridge):
    def __init__(self, state_dir: str | Path = "data/runtime/trust_bridges") -> None:
        super().__init__("observability_trust", state_dir)


ALL_BRIDGE_CLASSES = [
    CertificationTrustBridge,
    ValidationTrustBridge,
    ExplainabilityTrustBridge,
    AccountabilityTrustBridge,
    ReplayTrustBridge,
    ProvenanceTrustBridge,
    ChronologyTrustBridge,
    GovernanceTrustBridge,
    ObservabilityTrustBridge,
]
