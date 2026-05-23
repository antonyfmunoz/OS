"""Runtime Observability Pipeline v1 for the canonical runtime spine.

Captures execution telemetry: latency, outcome, proof artifacts,
governance decisions, adapter usage. All records append to JSONL.

Integrates with SubstrateContinuityEngine for continuity updates
and with RuntimeMemoryGovernanceBridge for memory promotion decisions.

UMH substrate subsystem.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from .execution_contracts_v1 import (
    ExecutionEnvelope,
    GovernanceVerdict,
    ObservabilityRecord,
    RiskClass,
    SpineOutcome,
    _new_id,
    _now_iso,
)


class RuntimeObservabilityPipeline:
    """Append-only observability pipeline for spine executions."""

    def __init__(
        self,
        observability_dir: str | Path = "data/runtime/observability",
    ) -> None:
        self._dir = Path(observability_dir)
        self._dir.mkdir(parents=True, exist_ok=True)
        self._records_path = self._dir / "execution_records.jsonl"
        self._metrics_path = self._dir / "execution_metrics.jsonl"
        self._total_recorded = 0
        self._total_successes = 0
        self._total_failures = 0

    def record_execution(
        self,
        envelope: ExecutionEnvelope,
        outcome: SpineOutcome,
        latency_ms: float = 0.0,
        error_message: str = "",
        proof_artifact_count: int = 0,
        continuity_updated: bool = False,
        memory_promoted: bool = False,
    ) -> ObservabilityRecord:
        """Record the telemetry for a single spine execution."""
        record = ObservabilityRecord(
            envelope_id=envelope.envelope_id,
            correlation_id=envelope.correlation_id,
            command_name=envelope.intent.command_name if envelope.intent else "",
            outcome=outcome,
            risk_class=(
                envelope.governance_evaluation.risk_class
                if envelope.governance_evaluation
                else envelope.intent.risk_class
                if envelope.intent
                else RiskClass.SAFE
            ),
            governance_verdict=(
                envelope.governance_evaluation.verdict
                if envelope.governance_evaluation
                else GovernanceVerdict.APPROVED
            ),
            adapter_id=(
                envelope.adapter_selection.adapter_id if envelope.adapter_selection else ""
            ),
            environment_id=(
                envelope.environment_selection.environment_id
                if envelope.environment_selection
                else ""
            ),
            latency_ms=latency_ms,
            execution_started_at=envelope.timestamp,
            execution_completed_at=_now_iso(),
            proof_artifact_count=proof_artifact_count,
            error_message=error_message,
            continuity_updated=continuity_updated,
            memory_promoted=memory_promoted,
        )

        self._persist_record(record)
        self._update_metrics(record)
        return record

    def get_recent_records(self, limit: int = 20) -> list[dict[str, Any]]:
        """Load most recent observability records."""
        if not self._records_path.exists():
            return []
        records = []
        with open(self._records_path, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    records.append(json.loads(line))
        return records[-limit:]

    def get_stats(self) -> dict[str, Any]:
        return {
            "total_recorded": self._total_recorded,
            "total_successes": self._total_successes,
            "total_failures": self._total_failures,
            "success_rate": (
                self._total_successes / self._total_recorded if self._total_recorded > 0 else 0.0
            ),
        }

    def to_dict(self) -> dict[str, Any]:
        return {
            "stats": self.get_stats(),
            "recent_records": self.get_recent_records(limit=5),
        }

    def _persist_record(self, record: ObservabilityRecord) -> None:
        with open(self._records_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(record.to_dict(), default=str) + "\n")

    def _update_metrics(self, record: ObservabilityRecord) -> None:
        self._total_recorded += 1
        if record.outcome == SpineOutcome.SUCCESS:
            self._total_successes += 1
        else:
            self._total_failures += 1

        metric = {
            "record_id": record.record_id,
            "command_name": record.command_name,
            "outcome": record.outcome.value,
            "latency_ms": record.latency_ms,
            "timestamp": record.timestamp,
        }
        with open(self._metrics_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(metric, default=str) + "\n")
