"""Outcome Learning Engine v1.

Learns from operational outcomes: successes, failures, denials,
replay divergence, resilience events, scaling pressure, operator
corrections, and reconciliation results.

Cannot execute actions. Cannot mutate state.
Collects and classifies learning signals only.

UMH substrate subsystem. Phase 96.8CC.
"""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any

from core.learning.adaptive_learning_contracts_v1 import (
    LearningSignal,
    OutcomeLearningState,
    OperatorCorrectionState,
    LearningSignalSource,
    _new_id,
    _now_iso,
)

MAX_SIGNALS = 1000
MAX_CORRECTIONS = 200
KNOWN_SOURCES = {s.value for s in LearningSignalSource}


class OutcomeLearningEngine:
    """Collects and classifies learning signals from outcomes."""

    def __init__(self, state_dir: str | Path | None = None) -> None:
        self._signals: list[LearningSignal] = []
        self._corrections: list[OperatorCorrectionState] = []
        self._success_count = 0
        self._failure_count = 0
        self._denial_count = 0
        self._correction_count = 0
        self._total_signals = 0

    def observe(
        self,
        source: str,
        content: str,
        severity: float = 0.0,
        session_id: str = "",
    ) -> dict[str, Any]:
        severity = max(0.0, min(1.0, severity))

        signal = LearningSignal(
            source=source,
            content=content,
            severity=severity,
            session_id=session_id,
        )

        if len(self._signals) < MAX_SIGNALS:
            self._signals.append(signal)
        self._total_signals += 1

        if source == "workflow_success":
            self._success_count += 1
        elif source == "workflow_failure":
            self._failure_count += 1
        elif source == "action_denied":
            self._denial_count += 1
        elif source == "operator_correction":
            self._correction_count += 1

        return signal.to_dict()

    def record_correction(
        self,
        original_action: str,
        corrected_action: str,
        reason: str = "",
        corrected_by: str = "operator",
    ) -> dict[str, Any]:
        if corrected_by != "operator":
            raise ValueError(
                f"Only operator can record corrections. Got: {corrected_by}"
            )

        correction = OperatorCorrectionState(
            original_action=original_action,
            corrected_action=corrected_action,
            reason=reason,
            corrected_by=corrected_by,
        )

        if len(self._corrections) < MAX_CORRECTIONS:
            self._corrections.append(correction)
        self._correction_count += 1

        self.observe("operator_correction", reason, severity=0.5)

        return correction.to_dict()

    def get_outcome_state(self) -> dict[str, Any]:
        raw = (
            f"{self._success_count}:{self._failure_count}:"
            f"{self._denial_count}:{self._correction_count}"
        )
        outcome_hash = hashlib.sha256(raw.encode()).hexdigest()[:16]

        state = OutcomeLearningState(
            signal_count=self._total_signals,
            success_count=self._success_count,
            failure_count=self._failure_count,
            denial_count=self._denial_count,
            correction_count=self._correction_count,
            outcome_hash=outcome_hash,
        )
        return state.to_dict()

    def get_signals(self, limit: int = 50) -> list[dict[str, Any]]:
        return [s.to_dict() for s in self._signals[-limit:]]

    def get_signals_by_source(self, source: str) -> list[dict[str, Any]]:
        return [
            s.to_dict() for s in self._signals if s.source == source
        ]

    def get_corrections(self, limit: int = 20) -> list[dict[str, Any]]:
        return [c.to_dict() for c in self._corrections[-limit:]]

    def get_stats(self) -> dict[str, object]:
        return {
            "total_signals": self._total_signals,
            "success_count": self._success_count,
            "failure_count": self._failure_count,
            "denial_count": self._denial_count,
            "correction_count": self._correction_count,
            "stored_signals": len(self._signals),
            "stored_corrections": len(self._corrections),
        }
