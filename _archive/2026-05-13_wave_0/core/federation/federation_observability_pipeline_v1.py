"""Federation Observability Pipeline v1.

9 event types with JSONL persistence for federation operations.

UMH substrate subsystem. Phase 96.8CN.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from core.federation.sovereign_federation_readiness_contracts_v1 import (
    FederationEventType,
    _now_iso,
)


EVENT_FILE_MAP = {e.value: f"{e.value}.jsonl" for e in FederationEventType}


class FederationObservabilityPipeline:
    """Emits and persists federation observability events."""

    def __init__(self, output_dir: str = "data/runtime/federation") -> None:
        self._output_dir = Path(output_dir)
        self._output_dir.mkdir(parents=True, exist_ok=True)
        self._events: list[dict[str, Any]] = []

    def _emit(self, event_type: FederationEventType, details: dict[str, Any]) -> dict[str, Any]:
        entry = {
            "event_type": event_type.value,
            "timestamp": _now_iso(),
            **details,
        }
        self._events.append(entry)
        filepath = self._output_dir / EVENT_FILE_MAP[event_type.value]
        with open(filepath, "a") as f:
            f.write(json.dumps(entry) + "\n")
        return entry

    def emit_runtime_identity_created(self, details: dict[str, Any]) -> dict[str, Any]:
        return self._emit(FederationEventType.RUNTIME_IDENTITY_CREATED, details)

    def emit_peer_manifest_received(self, details: dict[str, Any]) -> dict[str, Any]:
        return self._emit(FederationEventType.PEER_MANIFEST_RECEIVED, details)

    def emit_peer_recognized(self, details: dict[str, Any]) -> dict[str, Any]:
        return self._emit(FederationEventType.PEER_RECOGNIZED, details)

    def emit_peer_verified(self, details: dict[str, Any]) -> dict[str, Any]:
        return self._emit(FederationEventType.PEER_VERIFIED, details)

    def emit_peer_rejected(self, details: dict[str, Any]) -> dict[str, Any]:
        return self._emit(FederationEventType.PEER_REJECTED, details)

    def emit_trust_exchange_validated(self, details: dict[str, Any]) -> dict[str, Any]:
        return self._emit(FederationEventType.TRUST_EXCHANGE_VALIDATED, details)

    def emit_topology_manifest_validated(self, details: dict[str, Any]) -> dict[str, Any]:
        return self._emit(FederationEventType.TOPOLOGY_MANIFEST_VALIDATED, details)

    def emit_federation_boundary_denied(self, details: dict[str, Any]) -> dict[str, Any]:
        return self._emit(FederationEventType.FEDERATION_BOUNDARY_DENIED, details)

    def emit_interoperability_report_generated(self, details: dict[str, Any]) -> dict[str, Any]:
        return self._emit(FederationEventType.INTEROPERABILITY_REPORT_GENERATED, details)

    def get_stats(self) -> dict[str, Any]:
        return {"total_events": len(self._events)}
