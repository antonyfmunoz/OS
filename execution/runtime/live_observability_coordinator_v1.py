"""Live Observability Coordinator v1.

Unifies all observability across the live runtime spine:
  - execution traces
  - actuation lineage
  - governance lineage
  - execution lineage
  - continuity lineage

Persist to: data/runtime/live_runtime_observability/

UMH substrate subsystem. Phase 96.8BR.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .live_runtime_contracts_v1 import (
    RuntimeContext,
    RuntimeLineageReceipt,
    RuntimeOutcome,
    RuntimePhase,
    RuntimeSignal,
    _content_hash,
    _new_id,
    _now_iso,
)


class LiveObservabilityCoordinator:
    """Unified observability across the live runtime spine.

    Records every spine traversal as a complete trace with
    all lineage receipts, decisions, governance verdicts,
    and execution outcomes.
    """

    def __init__(
        self,
        observability_dir: str | Path = "data/runtime/live_runtime_observability",
    ) -> None:
        self._dir = Path(observability_dir)
        self._dir.mkdir(parents=True, exist_ok=True)
        self._traces_path = self._dir / "runtime_traces.jsonl"
        self._governance_path = self._dir / "governance_lineage.jsonl"
        self._execution_path = self._dir / "execution_lineage.jsonl"
        self._continuity_path = self._dir / "continuity_lineage.jsonl"
        self._lineage_path = self._dir / "lineage_receipts.jsonl"
        self._total_traces: int = 0
        self._total_governance: int = 0
        self._total_execution: int = 0
        self._total_continuity: int = 0

    def record_trace(
        self,
        signal: RuntimeSignal,
        context: RuntimeContext,
        outcome: RuntimeOutcome,
    ) -> dict[str, Any]:
        """Record a complete runtime spine trace."""
        trace = {
            "trace_id": _new_id("ltrace"),
            "signal_id": signal.signal_id,
            "correlation_id": context.correlation_id,
            "session_id": context.session_id,
            "command_name": context.command_name,
            "intent_type": context.intent_type,
            "domain": context.domain,
            "capability": context.capability_resolved,
            "environment": context.environment_resolved,
            "embodiment_path": context.embodiment_path,
            "governance_verdict": context.governance_verdict,
            "governance_rules": context.governance_rules,
            "risk_class": context.risk_class,
            "outcome_status": outcome.status.value,
            "steps_completed": outcome.steps_completed,
            "steps_total": outcome.steps_total,
            "duration_ms": outcome.duration_ms,
            "error_message": outcome.error_message,
            "decisions_count": len(context.decisions),
            "lineage_receipts": context.lineage_receipts,
            "memory_promotions": outcome.memory_promotions,
            "timestamp": _now_iso(),
        }

        self._append(self._traces_path, trace)
        self._total_traces += 1

        receipt = RuntimeLineageReceipt(
            signal_id=signal.signal_id,
            correlation_id=context.correlation_id,
            phase=RuntimePhase.OBSERVATION,
            action="record_trace",
            component="observability_coordinator",
            input_hash=_content_hash({"outcome_id": outcome.outcome_id}),
            output_hash=_content_hash({"trace_id": trace["trace_id"]}),
        )
        context.add_lineage_receipt(receipt.receipt_id)

        return trace

    def record_governance_event(
        self,
        signal: RuntimeSignal,
        context: RuntimeContext,
    ) -> None:
        """Record a governance lineage event."""
        event = {
            "event_id": _new_id("lgov"),
            "signal_id": signal.signal_id,
            "correlation_id": context.correlation_id,
            "command_name": context.command_name,
            "governance_verdict": context.governance_verdict,
            "governance_rules": context.governance_rules,
            "risk_class": context.risk_class,
            "decisions": context.decisions,
            "timestamp": _now_iso(),
        }
        self._append(self._governance_path, event)
        self._total_governance += 1

    def record_execution_event(
        self,
        signal: RuntimeSignal,
        context: RuntimeContext,
        outcome: RuntimeOutcome,
    ) -> None:
        """Record an execution lineage event."""
        event = {
            "event_id": _new_id("lexec"),
            "signal_id": signal.signal_id,
            "correlation_id": context.correlation_id,
            "command_name": context.command_name,
            "embodiment_path": outcome.embodiment_path,
            "status": outcome.status.value,
            "steps_completed": outcome.steps_completed,
            "steps_total": outcome.steps_total,
            "duration_ms": outcome.duration_ms,
            "error_message": outcome.error_message,
            "timestamp": _now_iso(),
        }
        self._append(self._execution_path, event)
        self._total_execution += 1

    def record_continuity_event(
        self,
        signal: RuntimeSignal,
        context: RuntimeContext,
        continuation_type: str,
    ) -> None:
        """Record a continuity lineage event."""
        event = {
            "event_id": _new_id("lcont"),
            "signal_id": signal.signal_id,
            "correlation_id": context.correlation_id,
            "command_name": context.command_name,
            "continuation_type": continuation_type,
            "open_loops_count": len(context.open_loops),
            "timestamp": _now_iso(),
        }
        self._append(self._continuity_path, event)
        self._total_continuity += 1

    def persist_lineage_receipts(
        self,
        context: RuntimeContext,
    ) -> None:
        """Persist all lineage receipts from a runtime context."""
        for receipt_id in context.lineage_receipts:
            entry = {
                "receipt_id": receipt_id,
                "correlation_id": context.correlation_id,
                "session_id": context.session_id,
                "timestamp": _now_iso(),
            }
            self._append(self._lineage_path, entry)

    def get_recent_traces(self, limit: int = 20) -> list[dict[str, Any]]:
        return self._read_recent(self._traces_path, limit)

    def get_recent_governance(self, limit: int = 20) -> list[dict[str, Any]]:
        return self._read_recent(self._governance_path, limit)

    def get_recent_execution(self, limit: int = 20) -> list[dict[str, Any]]:
        return self._read_recent(self._execution_path, limit)

    def get_stats(self) -> dict[str, Any]:
        return {
            "total_traces": self._total_traces,
            "total_governance_events": self._total_governance,
            "total_execution_events": self._total_execution,
            "total_continuity_events": self._total_continuity,
        }

    def _append(self, path: Path, record: dict[str, Any]) -> None:
        with open(path, "a", encoding="utf-8") as f:
            f.write(json.dumps(record, default=str) + "\n")

    def _read_recent(self, path: Path, limit: int) -> list[dict[str, Any]]:
        if not path.exists():
            return []
        records: list[dict[str, Any]] = []
        with open(path, encoding="utf-8") as f:
            for line in f:
                stripped = line.strip()
                if stripped:
                    records.append(json.loads(stripped))
        return records[-limit:]
