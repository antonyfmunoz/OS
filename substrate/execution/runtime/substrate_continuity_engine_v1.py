"""Substrate Continuity Engine v1.

The central orchestrator for runtime continuity. Consumes runtime traces,
execution outcomes, governance events, and reconciliation events.
Maintains longitudinal continuity. Generates continuity summaries.
Preserves deterministic replay and source provenance.

Observe + persist only. Does NOT mutate runtime behavior.

UMH substrate subsystem.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .continuity_classification_engine_v1 import (
    ContinuityClass,
    classify_event,
    classify_outcome,
)
from .continuity_summary_engine_v1 import ContinuitySummaryEngine
from .open_loop_registry_v1 import LoopType, OpenLoopRegistry
from .runtime_cognition_contracts_v1 import (
    ContinuityPhase,
    EventSeverity,
    OutcomeResult,
    RuntimeContextUpdate,
    RuntimeContinuityState,
    RuntimeEvent,
    RuntimeOutcome,
    RuntimeSessionSummary,
    RuntimeTrace,
)
from .runtime_continuity_store_v1 import RuntimeContinuityStore
from .runtime_memory_governance_bridge_v1 import RuntimeMemoryGovernanceBridge
from .runtime_resume_packet_v1 import ResumePacketGenerator


class SubstrateContinuityEngine:
    """Central continuity orchestrator.

    Ingests runtime activity, classifies it, persists what matters,
    tracks open loops, and generates resumable state.
    """

    def __init__(
        self,
        store_dir: str | Path = "data/runtime/substrate_continuity",
        loop_dir: str | Path = "data/runtime/open_loop_registry",
        memory_store_dir: str | Path = "data/runtime/reconciliation_memory_store",
        summaries_dir: str | Path = "data/runtime/continuity_summaries",
        promotion_dir: str | Path = "data/runtime/runtime_promotion_receipts",
    ):
        self.store = RuntimeContinuityStore(store_dir=store_dir)
        self.loop_registry = OpenLoopRegistry(store_dir=loop_dir)
        self.summary_engine = ContinuitySummaryEngine(
            continuity_store=self.store,
            loop_registry=self.loop_registry,
            summaries_dir=summaries_dir,
        )
        self.resume_generator = ResumePacketGenerator(
            continuity_store=self.store,
            loop_registry=self.loop_registry,
            memory_store_dir=memory_store_dir,
        )
        self.governance_bridge = RuntimeMemoryGovernanceBridge(
            receipts_dir=promotion_dir,
        )

        self._session_id = ""
        self._phase = ContinuityPhase.IDLE
        self._events_ingested = 0
        self._traces_ingested = 0
        self._outcomes_recorded = 0

    def start_session(self, session_id: str) -> None:
        """Begin a new continuity session."""
        self._session_id = session_id
        self._phase = ContinuityPhase.ACTIVE
        self._events_ingested = 0
        self._traces_ingested = 0
        self._outcomes_recorded = 0

    def ingest_event(self, event: dict[str, Any]) -> dict[str, Any]:
        """Ingest a runtime event into the continuity pipeline.

        Returns the classification decision.
        """
        classification = classify_event(event)

        if not classification.persist:
            return classification.to_dict()

        rt_event = RuntimeEvent(
            event_type=event.get("event_type", ""),
            source=event.get("source", ""),
            severity=EventSeverity(event.get("severity", "info"))
            if event.get("severity") in [s.value for s in EventSeverity]
            else EventSeverity.INFO,
            payload=event.get("payload", {}),
            correlation_id=event.get("correlation_id", ""),
            session_id=self._session_id,
        )
        self.store.append_event(rt_event.to_dict())
        self._events_ingested += 1

        if classification.track_as_open_loop:
            event_type = event.get("event_type", "unknown")
            loop_type = self._event_to_loop_type(event_type)
            self.loop_registry.create_loop(
                loop_type=loop_type,
                description=f"Event {event_type}: {event.get('payload', {}).get('summary', event_type)}",
                source_event_id=event.get("event_id", ""),
                correlation_id=event.get("correlation_id", ""),
                session_id=self._session_id,
            )

        return classification.to_dict()

    def ingest_trace(self, trace: dict[str, Any]) -> None:
        """Ingest an execution trace into continuity."""
        rt_trace = RuntimeTrace(
            trace_id=trace.get("trace_id", ""),
            source=trace.get("source", ""),
            mode=trace.get("mode", ""),
            command=trace.get("execution_path", ""),
            execution_path=trace.get("execution_path", ""),
            provider=trace.get("provider", ""),
            model=trace.get("model", ""),
            latency_ms=trace.get("latency_ms"),
            result=trace.get("result", ""),
            session_id=self._session_id,
            correlation_id=trace.get("correlation_id", ""),
            raw_trace=trace,
        )
        self.store.append_trace(rt_trace.to_dict())
        self._traces_ingested += 1

    def record_outcome(self, outcome: dict[str, Any]) -> dict[str, Any]:
        """Record a runtime execution outcome.

        Returns the classification + promotion decision.
        """
        classification = classify_outcome(outcome)

        rt_outcome = RuntimeOutcome(
            trace_id=outcome.get("trace_id", ""),
            command=outcome.get("command", ""),
            result=OutcomeResult(outcome.get("result", "success"))
            if outcome.get("result") in [r.value for r in OutcomeResult]
            else OutcomeResult.SUCCESS,
            error_message=outcome.get("error_message", ""),
            duration_ms=outcome.get("duration_ms"),
            artifacts_produced=outcome.get("artifacts_produced", []),
            governance_decision=outcome.get("governance_decision", ""),
            session_id=self._session_id,
        )
        self.store.append_outcome(rt_outcome.to_dict())
        self._outcomes_recorded += 1

        if classification.track_as_open_loop:
            self.loop_registry.create_loop(
                loop_type=LoopType.FAILED_EXECUTION,
                description=f"Outcome {outcome.get('result', '?')}: {outcome.get('command', '?')}",
                source_trace_id=outcome.get("trace_id", ""),
                session_id=self._session_id,
            )

        promotion = self.governance_bridge.evaluate_outcome(outcome)

        return {
            "classification": classification.to_dict(),
            "promotion": promotion.to_dict(),
        }

    def record_context_update(
        self,
        update_type: str,
        field_name: str,
        old_value: Any,
        new_value: Any,
        reason: str = "",
        source: str = "",
    ) -> None:
        """Record a change to operational context."""
        update = RuntimeContextUpdate(
            update_type=update_type,
            field_name=field_name,
            old_value=old_value,
            new_value=new_value,
            reason=reason,
            source=source,
            session_id=self._session_id,
        )
        self.store.append_context_update(update.to_dict())

    def take_snapshot(self, active_goals: list[str] | None = None) -> RuntimeContinuityState:
        """Take a continuity state snapshot."""
        open_loops = self.loop_registry.get_open_loops()
        recent_outcomes = self.store.load_recent_outcomes(limit=5)

        state = RuntimeContinuityState(
            phase=self._phase,
            current_session_id=self._session_id,
            active_goals=active_goals or [],
            unresolved_blockers=[
                l["description"]
                for l in open_loops
                if l.get("loop_type") in ("failed_execution", "pending_governance")
            ],
            recent_outcomes=[
                f"{o.get('command', '?')}: {o.get('result', '?')}" for o in recent_outcomes
            ],
            pending_approvals=[
                l["description"] for l in open_loops if l.get("loop_type") == "pending_governance"
            ],
            open_loop_count=len(open_loops),
            total_events_ingested=self._events_ingested,
            total_traces_ingested=self._traces_ingested,
            total_outcomes_recorded=self._outcomes_recorded,
            last_activity_at=datetime.now(timezone.utc).isoformat(),
        )

        self.store.save_snapshot(state.to_dict())
        return state

    def generate_resume_packet(
        self,
        active_goals: list[str] | None = None,
        suggested_next_actions: list[str] | None = None,
    ) -> dict[str, Any]:
        """Generate a resume packet for session continuation."""
        self.take_snapshot(active_goals=active_goals)
        packet = self.resume_generator.generate(
            session_id=self._session_id,
            active_goals=active_goals,
            suggested_next_actions=suggested_next_actions,
        )
        return packet.to_dict()

    def generate_session_summary(
        self,
        phase_name: str = "",
        files_modified: list[str] | None = None,
    ) -> RuntimeSessionSummary:
        """Generate a session summary."""
        return self.summary_engine.generate_session_summary(
            session_id=self._session_id,
            phase_name=phase_name,
            files_modified=files_modified,
        )

    def generate_restart_summary(self) -> dict[str, Any]:
        """Generate a restart summary."""
        return self.summary_engine.generate_restart_summary()

    def generate_operator_briefing(self) -> dict[str, Any]:
        """Generate an operator briefing."""
        return self.summary_engine.generate_operator_briefing()

    def get_stats(self) -> dict[str, Any]:
        """Return overall continuity stats."""
        store_stats = self.store.get_stats()
        loop_stats = self.loop_registry.get_stats()
        return {
            "session_id": self._session_id,
            "phase": self._phase.value,
            "events_ingested": self._events_ingested,
            "traces_ingested": self._traces_ingested,
            "outcomes_recorded": self._outcomes_recorded,
            "store": store_stats,
            "loops": loop_stats,
        }

    def _event_to_loop_type(self, event_type: str) -> LoopType:
        """Map event types to loop types."""
        mapping = {
            "execution_failed": LoopType.FAILED_EXECUTION,
            "execution_timed_out": LoopType.FAILED_EXECUTION,
            "execution_rejected": LoopType.PENDING_GOVERNANCE,
            "action_failed": LoopType.FAILED_EXECUTION,
            "action_expired": LoopType.INTERRUPTED_WORKFLOW,
            "relay_failed": LoopType.FAILED_EXECUTION,
            "permission_denied": LoopType.PENDING_GOVERNANCE,
            "node_degraded": LoopType.UNFINISHED_OPERATION,
            "execution_started": LoopType.UNFINISHED_OPERATION,
            "pipeline_created": LoopType.UNFINISHED_OPERATION,
            "action_dispatched": LoopType.UNFINISHED_OPERATION,
            "execution_requested": LoopType.UNFINISHED_OPERATION,
        }
        return mapping.get(event_type, LoopType.UNFINISHED_OPERATION)
