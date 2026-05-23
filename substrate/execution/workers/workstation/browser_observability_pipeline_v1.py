"""Browser Observability Pipeline v1.

Captures browser/GUI execution telemetry: URL transitions,
governance verdicts, adapter routing, visible actions, screenshots,
DOM summaries, continuity updates, execution latency.

Persist to: data/runtime/browser_observability/

UMH substrate subsystem.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .browser_gui_contracts_v1 import (
    BrowserExecutionOutcome,
    BrowserExecutionRequest,
    BrowserExecutionResult,
    VisibleActuationEvent,
    _new_id,
    _now_iso,
)


class BrowserObservabilityPipeline:
    """Append-only telemetry pipeline for browser/GUI executions."""

    def __init__(
        self,
        observability_dir: str | Path = "data/runtime/browser_observability",
    ) -> None:
        self._dir = Path(observability_dir)
        self._dir.mkdir(parents=True, exist_ok=True)
        self._records_path = self._dir / "browser_records.jsonl"
        self._denials_path = self._dir / "browser_denials.jsonl"
        self._metrics_path = self._dir / "browser_metrics.jsonl"
        self._actuation_path = self._dir / "visible_actuation_log.jsonl"
        self._total_recorded = 0
        self._total_successes = 0
        self._total_failures = 0
        self._total_denials = 0

    def record_execution(
        self,
        request: BrowserExecutionRequest,
        result: BrowserExecutionResult,
    ) -> dict[str, Any]:
        """Record a browser execution telemetry event."""
        record = {
            "record_id": _new_id("bobs"),
            "request_id": request.request_id,
            "action_type": request.action_type.value,
            "target_url": request.target_url,
            "operational_mode": request.operational_mode.value,
            "risk_class": request.risk_class,
            "governance_verdict": result.governance_verdict,
            "outcome": result.outcome.value,
            "adapter_used": result.adapter_used,
            "url_before": result.url_before,
            "url_after": result.url_after,
            "screenshot_path": result.screenshot_path,
            "dom_summary": result.dom_summary[:500] if result.dom_summary else "",
            "duration_ms": result.duration_ms,
            "error_message": result.error_message,
            "correlation_id": request.correlation_id,
            "timestamp": _now_iso(),
        }

        self._total_recorded += 1
        if result.outcome == BrowserExecutionOutcome.SUCCESS:
            self._total_successes += 1
        elif result.outcome == BrowserExecutionOutcome.DENIED:
            self._total_denials += 1
            self._persist_denial(record)
        else:
            self._total_failures += 1

        self._persist_record(record)
        self._persist_metric(record)
        return record

    def record_actuation_event(self, event: VisibleActuationEvent) -> None:
        """Record a visible actuation event."""
        with open(self._actuation_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(event.to_dict(), default=str) + "\n")

    def get_recent_records(self, limit: int = 20) -> list[dict[str, Any]]:
        if not self._records_path.exists():
            return []
        records: list[dict[str, Any]] = []
        with open(self._records_path, encoding="utf-8") as f:
            for line in f:
                stripped = line.strip()
                if stripped:
                    records.append(json.loads(stripped))
        return records[-limit:]

    def get_denial_records(self, limit: int = 20) -> list[dict[str, Any]]:
        if not self._denials_path.exists():
            return []
        records: list[dict[str, Any]] = []
        with open(self._denials_path, encoding="utf-8") as f:
            for line in f:
                stripped = line.strip()
                if stripped:
                    records.append(json.loads(stripped))
        return records[-limit:]

    def get_actuation_log(self, limit: int = 20) -> list[dict[str, Any]]:
        if not self._actuation_path.exists():
            return []
        records: list[dict[str, Any]] = []
        with open(self._actuation_path, encoding="utf-8") as f:
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
                self._total_successes / self._total_recorded if self._total_recorded > 0 else 0.0
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
            "action_type": record["action_type"],
            "outcome": record["outcome"],
            "duration_ms": record["duration_ms"],
            "governance_verdict": record["governance_verdict"],
            "target_url": record.get("target_url", ""),
            "timestamp": record["timestamp"],
        }
        with open(self._metrics_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(metric, default=str) + "\n")
