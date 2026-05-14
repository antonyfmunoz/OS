"""Runtime Certification Observability Pipeline v1.

9 event types for runtime certification observability.
JSONL persistence per event type.

UMH substrate subsystem. Phase 96.8CI.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from core.certification.runtime_certification_contracts_v1 import (
    CertificationEventType,
    _now_iso,
)


EVENT_FILE_MAP: dict[str, str] = {
    e.value: f"{e.value}.jsonl" for e in CertificationEventType
}


class RuntimeCertificationObservabilityPipeline:
    """Emits and persists certification observability events."""

    def __init__(
        self, state_dir: str | Path = "data/runtime/certification",
    ) -> None:
        self._state_dir = Path(state_dir)
        self._state_dir.mkdir(parents=True, exist_ok=True)
        self._events: list[dict[str, Any]] = []

    def _emit(
        self, event_type: str, payload: dict[str, Any],
    ) -> dict[str, Any]:
        event = {
            "event_type": event_type,
            "timestamp": _now_iso(),
            **payload,
        }
        self._events.append(event)

        filename = EVENT_FILE_MAP.get(event_type, "unknown.jsonl")
        filepath = self._state_dir / filename
        with open(filepath, "a") as f:
            f.write(json.dumps(event) + "\n")

        return event

    def emit_certification_started(
        self, run_id: str = "",
    ) -> dict[str, Any]:
        return self._emit(
            CertificationEventType.CERTIFICATION_STARTED,
            {"run_id": run_id},
        )

    def emit_certification_completed(
        self, run_id: str = "", certified: bool = False,
    ) -> dict[str, Any]:
        return self._emit(
            CertificationEventType.CERTIFICATION_COMPLETED,
            {"run_id": run_id, "certified": certified},
        )

    def emit_invariant_verified(
        self, domain: str = "", invariant_name: str = "",
    ) -> dict[str, Any]:
        return self._emit(
            CertificationEventType.INVARIANT_VERIFIED,
            {"domain": domain, "invariant_name": invariant_name},
        )

    def emit_invariant_failed(
        self, domain: str = "", invariant_name: str = "",
    ) -> dict[str, Any]:
        return self._emit(
            CertificationEventType.INVARIANT_FAILED,
            {"domain": domain, "invariant_name": invariant_name},
        )

    def emit_replay_certified(
        self, checks_passed: int = 0,
    ) -> dict[str, Any]:
        return self._emit(
            CertificationEventType.REPLAY_CERTIFIED,
            {"checks_passed": checks_passed},
        )

    def emit_continuity_certified(
        self, checks_passed: int = 0,
    ) -> dict[str, Any]:
        return self._emit(
            CertificationEventType.CONTINUITY_CERTIFIED,
            {"checks_passed": checks_passed},
        )

    def emit_topology_certified(
        self, checks_passed: int = 0,
    ) -> dict[str, Any]:
        return self._emit(
            CertificationEventType.TOPOLOGY_CERTIFIED,
            {"checks_passed": checks_passed},
        )

    def emit_semantic_consistency_verified(
        self, domains_checked: int = 0,
    ) -> dict[str, Any]:
        return self._emit(
            CertificationEventType.SEMANTIC_CONSISTENCY_VERIFIED,
            {"domains_checked": domains_checked},
        )

    def emit_runtime_attestation_generated(
        self, run_id: str = "", all_certified: bool = False,
    ) -> dict[str, Any]:
        return self._emit(
            CertificationEventType.RUNTIME_ATTESTATION_GENERATED,
            {"run_id": run_id, "all_certified": all_certified},
        )

    def get_events(self) -> list[dict[str, Any]]:
        return list(self._events)

    def get_stats(self) -> dict[str, Any]:
        return {
            "total_events": len(self._events),
            "event_types": len(EVENT_FILE_MAP),
        }
