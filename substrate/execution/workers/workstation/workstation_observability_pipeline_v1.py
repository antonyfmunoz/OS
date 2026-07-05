"""Workstation Observability Pipeline v1.

Captures workstation execution telemetry: command, governance verdict,
environment, adapter used, execution latency, operational impact,
continuity updates.

Persist to: data/runtime/workstation_observability/

UMH substrate subsystem.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .workstation_contracts_v1 import (
    WorkstationExecutionOutcome,
    WorkstationExecutionRequest,
    WorkstationExecutionResult,
    _new_id,
    _now_iso,
)


class WorkstationObservabilityPipeline:
    """Append-only telemetry pipeline for workstation executions."""

    def __init__(
        self,
        observability_dir: str | Path = "data/runtime/workstation_observability",
    ) -> None:
        self._dir = Path(observability_dir)
        self._dir.mkdir(parents=True, exist_ok=True)
        self._records_path = self._dir / "execution_records.jsonl"
        self._denials_path = self._dir / "denial_records.jsonl"
        self._metrics_path = self._dir / "execution_metrics.jsonl"
        self._total_recorded = 0
        self._total_successes = 0
        self._total_failures = 0
        self._total_denials = 0

    def record_execution(
        self,
        request: WorkstationExecutionRequest,
        result: WorkstationExecutionResult,
    ) -> dict[str, Any]:
        """Record a workstation execution telemetry event."""
        record = {
            "record_id": _new_id("wobs"),
            "request_id": request.request_id,
            "command": request.command,
            "adapter_type": request.adapter_type,
            "operational_mode": request.operational_mode.value,
            "risk_class": request.risk_class,
            "governance_verdict": result.governance_verdict,
            "outcome": result.outcome.value,
            "adapter_used": result.adapter_used,
            "environment_id": result.environment_id,
            "duration_ms": result.duration_ms,
            "exit_code": result.exit_code,
            "correlation_id": request.correlation_id,
            "error_message": result.error_message,
            "timestamp": _now_iso(),
        }

        self._total_recorded += 1
        if result.outcome == WorkstationExecutionOutcome.SUCCESS:
            self._total_successes += 1
        elif result.outcome == WorkstationExecutionOutcome.DENIED:
            self._total_denials += 1
            self._persist_denial(record)
        else:
            self._total_failures += 1

        self._persist_record(record)
        self._persist_metric(record)
        return record

    def get_recent_records(self, limit: int = 20) -> list[dict[str, Any]]:
        if not self._records_path.exists():
            return []
        records = []
        with open(self._records_path, encoding="utf-8") as f:
            for line in f:
                stripped = line.strip()
                if stripped:
                    records.append(json.loads(stripped))
        return records[-limit:]

    def get_denial_records(self, limit: int = 20) -> list[dict[str, Any]]:
        if not self._denials_path.exists():
            return []
        records = []
        with open(self._denials_path, encoding="utf-8") as f:
            for line in f:
                stripped = line.strip()
                if stripped:
                    records.append(json.loads(stripped))
        return records[-limit:]

    def get_stats(self) -> dict[str, Any]:
        return {
            "total_recorded": self._total_recorded,
            "total_successes": self._total_successes,
            "total_failures": self._total_failures,
            "total_denials": self._total_denials,
            "success_rate": (
                self._total_successes / self._total_recorded
                if self._total_recorded > 0
                else 0.0
            ),
        }

    def _persist_record(self, record: dict[str, Any]) -> None:
        with open(self._records_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(record, default=str) + "\n")

    def _persist_denial(self, record: dict[str, Any]) -> None:
        with open(self._denials_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(record, default=str) + "\n")

    def _persist_metric(self, record: dict[str, Any]) -> None:
        metric = {
            "record_id": record["record_id"],
            "command": record["command"],
            "outcome": record["outcome"],
            "duration_ms": record["duration_ms"],
            "governance_verdict": record["governance_verdict"],
            "timestamp": record["timestamp"],
        }
        with open(self._metrics_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(metric, default=str) + "\n")
