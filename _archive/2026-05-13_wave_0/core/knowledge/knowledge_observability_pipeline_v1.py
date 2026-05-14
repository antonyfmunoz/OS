"""Knowledge Observability Pipeline v1.

Emits structured events for all knowledge fabric operations.
10 event types from KnowledgeEventType enum.
JSONL per event type, dynamic EVENT_FILE_MAP.

UMH substrate subsystem. Phase 96.8CB.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from core.knowledge.knowledge_fabric_contracts_v1 import (
    KnowledgeEventType,
    _now_iso,
)

EVENT_FILE_MAP: dict[str, str] = {
    evt.value: f"{evt.value}.jsonl" for evt in KnowledgeEventType
}


class KnowledgeObservabilityPipeline:
    """Emits knowledge fabric observability events."""

    def __init__(self, state_dir: str | Path = "data/runtime/knowledge/observability") -> None:
        self._state_dir = Path(state_dir)
        self._state_dir.mkdir(parents=True, exist_ok=True)
        self._counts: dict[str, int] = {evt.value: 0 for evt in KnowledgeEventType}

    def _emit(self, event_type: str, payload: dict[str, Any]) -> None:
        event = {
            "event_type": event_type,
            "timestamp": _now_iso(),
            **payload,
        }
        filename = EVENT_FILE_MAP.get(event_type, "unknown.jsonl")
        path = self._state_dir / filename
        with path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(event, default=str) + "\n")
        self._counts[event_type] = self._counts.get(event_type, 0) + 1

    def emit_knowledge_promoted(self, node_id: str, from_tier: str, to_tier: str) -> None:
        self._emit("knowledge_promoted", {
            "node_id": node_id, "from_tier": from_tier, "to_tier": to_tier,
        })

    def emit_semantic_relationship_created(
        self, source: str, target: str, relationship_type: str,
    ) -> None:
        self._emit("semantic_relationship_created", {
            "source": source, "target": target, "relationship_type": relationship_type,
        })

    def emit_semantic_conflict_detected(
        self, node_a: str, node_b: str, severity: str,
    ) -> None:
        self._emit("semantic_conflict_detected", {
            "node_a": node_a, "node_b": node_b, "severity": severity,
        })

    def emit_corroboration_strengthened(
        self, node_id: str, corroboration_count: int,
    ) -> None:
        self._emit("corroboration_strengthened", {
            "node_id": node_id, "corroboration_count": corroboration_count,
        })

    def emit_retrieval_executed(
        self, query: str, result_count: int,
    ) -> None:
        self._emit("retrieval_executed", {
            "query": query, "result_count": result_count,
        })

    def emit_compression_generated(
        self, original: int, compressed: int,
    ) -> None:
        self._emit("compression_generated", {
            "original": original, "compressed": compressed,
        })

    def emit_conceptual_integrity_validated(
        self, integrity_score: float, coherent: bool,
    ) -> None:
        self._emit("conceptual_integrity_validated", {
            "integrity_score": integrity_score, "coherent": coherent,
        })

    def emit_ontology_drift_detected(
        self, concept: str, expected_tier: str, actual_tier: str,
    ) -> None:
        self._emit("ontology_drift_detected", {
            "concept": concept, "expected_tier": expected_tier,
            "actual_tier": actual_tier,
        })

    def emit_semantic_boundary_denied(
        self, action: str, reason: str,
    ) -> None:
        self._emit("semantic_boundary_denied", {
            "action": action, "reason": reason,
        })

    def emit_lineage_transition_recorded(
        self, node_id: str, from_tier: str, to_tier: str,
    ) -> None:
        self._emit("lineage_transition_recorded", {
            "node_id": node_id, "from_tier": from_tier, "to_tier": to_tier,
        })

    def get_stats(self) -> dict[str, Any]:
        return {
            "event_counts": dict(self._counts),
            "total_events": sum(self._counts.values()),
        }
