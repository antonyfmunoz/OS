"""Trust Observability Pipeline v1.

6 event types with JSONL persistence for trust operations.

UMH substrate subsystem. Phase 96.8CM.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from core.trust.sovereign_operational_trust_contracts_v1 import (
    TrustEventType,
    _now_iso,
)


EVENT_FILE_MAP = {e.value: f"{e.value}.jsonl" for e in TrustEventType}


class TrustObservabilityPipeline:
    """Emits and persists trust observability events."""

    def __init__(self, output_dir: str = "data/runtime/trust") -> None:
        self._output_dir = Path(output_dir)
        self._output_dir.mkdir(parents=True, exist_ok=True)
        self._events: list[dict[str, Any]] = []

    def _emit(self, event_type: TrustEventType, details: dict[str, Any]) -> dict[str, Any]:
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

    def emit_trust_bundle_created(self, details: dict[str, Any]) -> dict[str, Any]:
        return self._emit(TrustEventType.TRUST_BUNDLE_CREATED, details)

    def emit_trust_artifact_hashed(self, details: dict[str, Any]) -> dict[str, Any]:
        return self._emit(TrustEventType.TRUST_ARTIFACT_HASHED, details)

    def emit_trust_bundle_verified(self, details: dict[str, Any]) -> dict[str, Any]:
        return self._emit(TrustEventType.TRUST_BUNDLE_VERIFIED, details)

    def emit_external_verification_completed(self, details: dict[str, Any]) -> dict[str, Any]:
        return self._emit(TrustEventType.EXTERNAL_VERIFICATION_COMPLETED, details)

    def emit_trust_boundary_denied(self, details: dict[str, Any]) -> dict[str, Any]:
        return self._emit(TrustEventType.TRUST_BOUNDARY_DENIED, details)

    def emit_trust_replay_validated(self, details: dict[str, Any]) -> dict[str, Any]:
        return self._emit(TrustEventType.TRUST_REPLAY_VALIDATED, details)

    def get_stats(self) -> dict[str, Any]:
        return {"total_events": len(self._events)}
