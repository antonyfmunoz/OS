"""Live Continuity Coordinator v1.

Coordinates continuity across the live runtime spine:
  - retrieve continuity state
  - persist continuity events
  - update open loops
  - create resume packets
  - bridge memory/runtime state

Composes the existing SubstrateContinuityEngine (96.8BN),
WorkstationContinuityBridge (96.8BP), and
BrowserContinuityBridge (96.8BQ) into one coordinator.

UMH substrate subsystem. Phase 96.8BR.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .live_runtime_contracts_v1 import (
    RuntimeContext,
    RuntimeContinuation,
    RuntimeContinuationType,
    RuntimeLineageReceipt,
    RuntimeOutcome,
    RuntimeOutcomeStatus,
    RuntimePhase,
    RuntimeSignal,
    _content_hash,
    _new_id,
    _now_iso,
)
from .substrate_continuity_engine_v1 import SubstrateContinuityEngine
try:
    from substrate.execution.workers.workstation.workstation_continuity_bridge_v1 import (
        WorkstationContinuityBridge,
    )
except ModuleNotFoundError:
    WorkstationContinuityBridge = None  # type: ignore[assignment,misc]

try:
    from substrate.execution.workers.workstation.browser_continuity_bridge_v1 import BrowserContinuityBridge
except ModuleNotFoundError:
    BrowserContinuityBridge = None  # type: ignore[assignment,misc]


class LiveContinuityCoordinator:
    """Unified continuity coordination across all substrate layers.

    Bridges substrate continuity, workstation continuity,
    and browser continuity into one coherent layer.
    """

    def __init__(
        self,
        continuity_engine: SubstrateContinuityEngine | None = None,
        workstation_bridge: WorkstationContinuityBridge | None = None,
        browser_bridge: BrowserContinuityBridge | None = None,
        state_dir: str | Path = "data/runtime/live_runtime_state",
    ) -> None:
        self._engine = continuity_engine or SubstrateContinuityEngine()
        if workstation_bridge is not None:
            self._workstation = workstation_bridge
        elif WorkstationContinuityBridge is not None:
            self._workstation = WorkstationContinuityBridge()
        else:
            self._workstation = None
        if browser_bridge is not None:
            self._browser = browser_bridge
        elif BrowserContinuityBridge is not None:
            self._browser = BrowserContinuityBridge()
        else:
            self._browser = None
        self._state_dir = Path(state_dir)
        self._state_dir.mkdir(parents=True, exist_ok=True)
        self._session_id = ""
        self._events_persisted: int = 0
        self._loops_updated: int = 0
        self._resume_packets: int = 0

    def start_session(self, session_id: str = "") -> str:
        """Start a unified continuity session across all layers."""
        self._session_id = session_id or _new_id("lsess")
        self._engine.start_session(self._session_id)
        self._workstation.start_session(self._session_id)
        self._browser.start_session(self._session_id)
        return self._session_id

    def persist_event(
        self,
        signal: RuntimeSignal,
        context: RuntimeContext,
        outcome: RuntimeOutcome,
    ) -> RuntimeContinuation:
        """Persist a runtime event to all continuity layers."""
        context.current_phase = RuntimePhase.CONTINUITY

        self._engine.ingest_event(
            {
                "event_id": outcome.outcome_id,
                "event_type": ("execution_completed" if outcome.succeeded else "execution_failed"),
                "source": "live_spine",
                "severity": "info" if outcome.succeeded else "error",
                "payload": {
                    "command": outcome.command_name,
                    "embodiment": outcome.embodiment_path,
                    "summary": f"Live spine: {outcome.command_name} → {outcome.status.value}",
                },
                "correlation_id": outcome.correlation_id,
            }
        )

        self._engine.record_outcome(
            {
                "outcome_id": f"live-{outcome.outcome_id}",
                "trace_id": outcome.correlation_id,
                "command": outcome.command_name,
                "result": "success" if outcome.succeeded else "failure",
                "duration_ms": outcome.duration_ms,
                "error_message": outcome.error_message,
                "artifacts_produced": [],
            }
        )

        self._engine.ingest_trace(
            {
                "trace_id": outcome.correlation_id,
                "command": outcome.command_name,
                "embodiment_path": outcome.embodiment_path,
                "status": outcome.status.value,
                "duration_ms": outcome.duration_ms,
                "governance_verdict": outcome.governance_verdict,
                "risk_class": context.risk_class,
            }
        )

        self._events_persisted += 1

        continuation = self._build_continuation(outcome)

        receipt = RuntimeLineageReceipt(
            signal_id=signal.signal_id,
            correlation_id=context.correlation_id,
            phase=RuntimePhase.CONTINUITY,
            action="persist_event",
            component="continuity_coordinator",
            input_hash=_content_hash({"outcome_id": outcome.outcome_id}),
            output_hash=continuation.content_hash(),
        )
        context.add_lineage_receipt(receipt.receipt_id)

        return continuation

    def retrieve_state(self) -> dict[str, Any]:
        """Retrieve current continuity state across all layers."""
        engine_stats = self._engine.get_stats()
        workstation_stats = self._workstation.get_stats()
        browser_stats = self._browser.get_stats()

        return {
            "session_id": self._session_id,
            "substrate_continuity": engine_stats,
            "workstation_continuity": workstation_stats,
            "browser_continuity": browser_stats,
            "events_persisted": self._events_persisted,
            "loops_updated": self._loops_updated,
            "resume_packets": self._resume_packets,
            "timestamp": _now_iso(),
        }

    def get_open_loops(self) -> list[dict[str, Any]]:
        """Retrieve open loops from the substrate continuity engine."""
        return self._engine.get_stats().get("open_loops", [])

    def create_resume_packet(
        self,
        active_goals: list[str] | None = None,
        suggested_next_actions: list[str] | None = None,
    ) -> dict[str, Any]:
        """Create a resume packet from current continuity state."""
        packet = self._engine.generate_resume_packet(
            active_goals=active_goals or [],
            suggested_next_actions=suggested_next_actions or [],
        )
        self._resume_packets += 1

        resume_path = self._state_dir / "live_resume_packet.json"
        resume_path.write_text(
            json.dumps(
                packet if isinstance(packet, dict) else {"packet": str(packet)},
                indent=2,
                default=str,
            ),
            encoding="utf-8",
        )

        return packet if isinstance(packet, dict) else {"packet": str(packet)}

    def get_stats(self) -> dict[str, Any]:
        return {
            "session_id": self._session_id,
            "events_persisted": self._events_persisted,
            "loops_updated": self._loops_updated,
            "resume_packets": self._resume_packets,
        }

    def _build_continuation(self, outcome: RuntimeOutcome) -> RuntimeContinuation:
        """Build a continuation record from an outcome."""
        if outcome.succeeded:
            return RuntimeContinuation(
                outcome_id=outcome.outcome_id,
                correlation_id=outcome.correlation_id,
                session_id=outcome.session_id,
                continuation_type=RuntimeContinuationType.COMPLETE,
            )

        if outcome.status == RuntimeOutcomeStatus.DEFERRED:
            return RuntimeContinuation(
                outcome_id=outcome.outcome_id,
                correlation_id=outcome.correlation_id,
                session_id=outcome.session_id,
                continuation_type=RuntimeContinuationType.DEFERRED,
                deferred_reason=outcome.error_message,
            )

        loop_id = _new_id("loop")
        self._loops_updated += 1
        return RuntimeContinuation(
            outcome_id=outcome.outcome_id,
            correlation_id=outcome.correlation_id,
            session_id=outcome.session_id,
            continuation_type=RuntimeContinuationType.OPEN_LOOP,
            open_loop_ids=[loop_id],
            resume_context={
                "failed_command": outcome.command_name,
                "error": outcome.error_message,
                "embodiment": outcome.embodiment_path,
            },
        )
