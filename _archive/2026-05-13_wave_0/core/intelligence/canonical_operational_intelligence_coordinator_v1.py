"""Canonical Operational Intelligence Coordinator v1.

Coordinates operational intelligence:
  synthesis, relevance arbitration, routing, reasoning,
  compression, awareness, intent anchoring, projection.

The intelligence layer understands and synthesizes —
it NEVER self-directs or creates autonomous objectives.
All execution must still traverse spine.process().

UMH substrate subsystem. Phase 96.8CA.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from core.intelligence.operational_intelligence_contracts_v1 import (
    IntelligenceCoordinationReceipt,
    IntelligenceLifecycleState,
    _now_iso,
)
from core.intelligence.intelligence_lifecycle_engine_v1 import (
    IntelligenceLifecycleEngine,
)
from core.intelligence.intelligence_synthesis_engine_v1 import (
    IntelligenceSynthesisEngine,
)
from core.intelligence.operational_relevance_arbitration_engine_v1 import (
    OperationalRelevanceArbitrationEngine,
)
from core.intelligence.intelligence_routing_engine_v1 import (
    IntelligenceRoutingEngine,
)
from core.intelligence.operational_reasoning_composition_engine_v1 import (
    OperationalReasoningCompositionEngine,
)
from core.intelligence.context_compression_engine_v1 import (
    ContextCompressionEngine,
)
from core.intelligence.operational_awareness_engine_v1 import (
    OperationalAwarenessEngine,
)
from core.intelligence.intent_anchoring_engine_v1 import (
    IntentAnchoringEngine,
)
from core.intelligence.intelligence_observability_pipeline_v1 import (
    IntelligenceObservabilityPipeline,
)


class CanonicalOperationalIntelligenceCoordinator:
    """Coordinates operational intelligence synthesis and awareness.

    Cannot execute directly. Cannot create objectives.
    Cannot mutate operator intent. Cannot dispatch autonomous workflows.
    All execution through canonical spine only.
    """

    def __init__(
        self,
        state_dir: str | Path = "data/runtime/intelligence",
    ) -> None:
        self._state_dir = Path(state_dir)
        self._state_dir.mkdir(parents=True, exist_ok=True)

        self._lifecycle = IntelligenceLifecycleEngine(state_dir=self._state_dir)
        self._synthesis = IntelligenceSynthesisEngine(state_dir=self._state_dir)
        self._relevance = OperationalRelevanceArbitrationEngine(
            state_dir=self._state_dir,
        )
        self._routing = IntelligenceRoutingEngine(state_dir=self._state_dir)
        self._reasoning = OperationalReasoningCompositionEngine(
            state_dir=self._state_dir,
        )
        self._compression = ContextCompressionEngine(state_dir=self._state_dir)
        self._awareness = OperationalAwarenessEngine(state_dir=self._state_dir)
        self._intent = IntentAnchoringEngine(state_dir=self._state_dir)
        self._observability = IntelligenceObservabilityPipeline(
            state_dir=self._state_dir / "observability",
        )
        self._receipts: list[IntelligenceCoordinationReceipt] = []

    def synthesize(
        self,
        signals: dict[str, list[dict[str, Any]]],
        operator_intent: str = "",
    ) -> dict[str, Any]:
        old_state = self._lifecycle.current_state
        if old_state == "inactive":
            self._lifecycle.transition(IntelligenceLifecycleState.OBSERVING)
        if self._lifecycle.current_state == "observing":
            self._lifecycle.transition(IntelligenceLifecycleState.SYNTHESIZING)

        state = self._synthesis.synthesize(signals, operator_intent)

        self._observability.emit_intelligence_synthesized(
            sources=state.sources, signal_count=state.signal_count,
        )

        self._emit_receipt(
            "synthesize", old_state,
            self._lifecycle.current_state, state.signal_count,
            state.synthesis_hash,
        )

        return state.to_dict()

    def score_relevance(
        self,
        signal_id: str,
        source: str = "",
        severity: float = 0.0,
        recency: float = 1.0,
    ) -> dict[str, Any]:
        focus = self._relevance.get_focus()
        score = self._relevance.score_signal(
            signal_id=signal_id,
            source=source,
            severity=severity,
            recency=recency,
            operator_focus=focus.active_focus,
        )

        self._observability.emit_relevance_scored(
            signal_id=signal_id, score=score.score,
        )

        return score.to_dict()

    def route_intelligence(
        self,
        source_layer: str,
        target_layer: str,
        signal_ids: list[str],
    ) -> dict[str, Any] | None:
        state = self._routing.route(source_layer, target_layer, signal_ids)
        if state is None:
            self._observability.emit_intelligence_boundary_denied(
                action="route", reason=f"{source_layer}→{target_layer} denied",
            )
            return None

        self._observability.emit_intelligence_route_created(
            source=source_layer, target=target_layer,
        )
        return state.to_dict()

    def compose_reasoning(
        self,
        reasoning_type: str,
        inputs: list[str],
        conclusion: str,
        confidence: float = 0.0,
        reasoning_chain: list[str] | None = None,
    ) -> dict[str, Any]:
        state = self._reasoning.compose(
            reasoning_type=reasoning_type,
            inputs=inputs,
            conclusion=conclusion,
            confidence=confidence,
            reasoning_chain=reasoning_chain,
            set_by="operator",
        )

        self._observability.emit_reasoning_composed(
            reasoning_type=reasoning_type, confidence=state.confidence,
        )
        return state.to_dict()

    def compress_context(
        self,
        relevance_scores: dict[str, float] | None = None,
    ) -> dict[str, Any]:
        if self._lifecycle.current_state in ("synthesizing", "contextualizing"):
            self._lifecycle.transition(IntelligenceLifecycleState.CONTEXTUALIZING)
            self._lifecycle.transition(IntelligenceLifecycleState.PRIORITIZING)
            self._lifecycle.transition(IntelligenceLifecycleState.COMPRESSING)

        state = self._compression.compress(relevance_scores)

        self._observability.emit_context_compressed(
            original=state.original_size, compressed=state.compressed_size,
        )
        return state.to_dict()

    def add_context_signal(self, signal: dict[str, Any]) -> bool:
        added = self._compression.add_signal(signal)
        if added:
            self._observability.emit_cognition_window_regulated(
                window_size=self._compression.get_window().current_size,
                max_size=self._compression.get_window().max_signals,
            )
        return added

    def update_awareness(
        self,
        subsystems: list[str] | None = None,
        pressures: list[str] | None = None,
        risks: list[str] | None = None,
        open_loops: list[str] | None = None,
        environments: dict[str, str] | None = None,
        constraints: list[str] | None = None,
        priorities: list[str] | None = None,
    ) -> dict[str, Any]:
        if subsystems is not None:
            self._awareness.update_subsystems(subsystems)
        if pressures is not None:
            self._awareness.update_pressure(pressures)
        if risks is not None:
            self._awareness.update_continuity_risks(risks)
        if open_loops is not None:
            self._awareness.update_open_loops(open_loops)
        if environments is not None:
            self._awareness.update_environment_status(environments)
        if constraints is not None:
            self._awareness.update_governance_constraints(constraints)
        if priorities is not None:
            self._awareness.update_priorities(priorities)

        self._observability.emit_operational_awareness_updated(
            subsystems=len(self._awareness.get_awareness().active_subsystems),
            pressures=len(self._awareness.get_awareness().pressure_signals),
        )

        return self._awareness.get_awareness().to_dict()

    def anchor_intent(
        self,
        operator_intent: str,
    ) -> dict[str, Any]:
        state = self._intent.anchor(operator_intent, set_by="operator")

        self._observability.emit_intent_anchor_validated(
            intent=operator_intent, valid=True,
        )
        return state.to_dict()

    def project(self) -> dict[str, Any]:
        if self._lifecycle.current_state in ("compressing",):
            self._lifecycle.transition(IntelligenceLifecycleState.PROJECTING)

        projection = self._awareness.project()

        self._observability.emit_operational_projection_updated(
            risks=len(projection.projected_risks),
            pressures=len(projection.projected_pressures),
        )
        return projection.to_dict()

    def set_focus(self, focus: str) -> dict[str, Any]:
        state = self._relevance.set_focus(focus, set_by="operator")
        return state.to_dict()

    def get_context_window(self) -> dict[str, Any]:
        return self._compression.get_window().to_dict()

    def get_awareness(self) -> dict[str, Any]:
        return self._awareness.get_awareness().to_dict()

    def get_signal_clusters(self) -> list[dict[str, Any]]:
        return [c.to_dict() for c in self._synthesis.get_clusters()]

    def get_reasoning_lineage(self, limit: int = 10) -> list[dict[str, Any]]:
        return self._reasoning.get_lineage(limit)

    def get_intent_lineage(self, limit: int = 10) -> list[dict[str, Any]]:
        return self._intent.get_lineage(limit)

    def get_priority_signals(self, limit: int = 20) -> list[dict[str, Any]]:
        return [s.to_dict() for s in self._relevance.get_priority_signals(limit)]

    def get_health(self) -> dict[str, Any]:
        return {
            "lifecycle_state": self._lifecycle.current_state,
            "context_window_usage": self._compression.get_window_usage(),
            "active_intent": self._intent.get_active_intent(),
            "synthesis_count": self._synthesis.get_stats()["total_syntheses"],
            "awareness": self._awareness.get_stats(),
        }

    def get_recent_receipts(self, limit: int = 10) -> list[dict[str, Any]]:
        return [r.to_dict() for r in self._receipts[-limit:]]

    def get_stats(self) -> dict[str, Any]:
        return {
            "lifecycle": self._lifecycle.get_stats(),
            "synthesis": self._synthesis.get_stats(),
            "relevance": self._relevance.get_stats(),
            "routing": self._routing.get_stats(),
            "reasoning": self._reasoning.get_stats(),
            "compression": self._compression.get_stats(),
            "awareness": self._awareness.get_stats(),
            "intent": self._intent.get_stats(),
            "observability": self._observability.get_stats(),
        }

    def _emit_receipt(
        self,
        operation: str,
        from_state: str,
        to_state: str,
        signal_count: int,
        synthesis_hash: str = "",
    ) -> IntelligenceCoordinationReceipt:
        receipt = IntelligenceCoordinationReceipt(
            operation=operation,
            from_state=from_state,
            to_state=to_state,
            signal_count=signal_count,
            synthesis_hash=synthesis_hash,
        )
        self._receipts.append(receipt)

        path = self._state_dir / "intelligence_coordination_receipts.jsonl"
        with path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(receipt.to_dict(), default=str) + "\n")

        return receipt
