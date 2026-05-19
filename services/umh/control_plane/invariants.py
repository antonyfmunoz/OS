"""Invariant enforcement — validates substrate laws at every transition point."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

from ..foundation.laws import (
    ADAPTER_MEDIATION_LAW,
    MEMORY_PATHWAY_LAW,
    NO_DIRECT_EXECUTION_LAW,
    SIGNAL_INTAKE_LAW,
    SUBSTRATE_LAWS,
    TRACEABILITY_LAW,
    Law,
    Severity,
)
from ..protocols.governance import GovernanceVerdict
from ..protocols.signal import Signal
from ..protocols.trace import Trace
from ..protocols.work_packet import WorkPacket

logger = logging.getLogger(__name__)


@dataclass
class InvariantViolation:
    """A detected violation of a substrate law."""

    law: Law
    context: str
    data: dict[str, Any]

    def __str__(self) -> str:
        return f"VIOLATION [{self.law.severity.value}] {self.law.name}: {self.context}"


class InvariantChecker:
    """Enforces substrate laws at runtime. Hard blocks raise, soft blocks warn."""

    def __init__(self) -> None:
        self._violations: list[InvariantViolation] = []

    def check_signal_intake(self, signal: Signal) -> InvariantViolation | None:
        """Verify signal entered through proper intake."""
        if not signal.id:
            violation = InvariantViolation(
                law=SIGNAL_INTAKE_LAW,
                context="Signal has no ID — may not have entered through intake",
                data={"signal": signal.model_dump(mode="json")},
            )
            self._record(violation)
            return violation
        return None

    def check_governance_required(
        self,
        governance_verdict_id: Any | None,
        context_label: str = "",
    ) -> InvariantViolation | None:
        """Verify that a governance verdict exists before execution is attempted."""
        if not governance_verdict_id:
            violation = InvariantViolation(
                law=NO_DIRECT_EXECUTION_LAW,
                context=f"No governance verdict — direct execution attempted{': ' + context_label if context_label else ''}",
                data={"context": context_label},
            )
            self._record(violation)
            return violation
        return None

    def check_trace_required(
        self,
        trace_id: Any | None,
        context_label: str = "",
    ) -> InvariantViolation | None:
        """Verify that a trace context exists before execution."""
        if not trace_id:
            violation = InvariantViolation(
                law=TRACEABILITY_LAW,
                context=f"No trace ID — execution would be untraceable{': ' + context_label if context_label else ''}",
                data={"context": context_label},
            )
            self._record(violation)
            return violation
        return None

    def check_adapter_mediation(
        self, adapter_id: Any | None, operation: str
    ) -> InvariantViolation | None:
        """Verify that external access goes through an adapter."""
        if not adapter_id:
            violation = InvariantViolation(
                law=ADAPTER_MEDIATION_LAW,
                context=f"External operation '{operation}' attempted without adapter",
                data={"operation": operation},
            )
            self._record(violation)
            return violation
        return None

    def validate_work_packet(self, work_packet: WorkPacket) -> list[InvariantViolation]:
        """Run all relevant checks on a constructed work packet."""
        violations = []
        v = self.check_governance_required(work_packet.governance_verdict_id, str(work_packet.id))
        if v:
            violations.append(v)
        v = self.check_trace_required(work_packet.trace_id, str(work_packet.id))
        if v:
            violations.append(v)
        return violations

    def validate_pre_creation(
        self,
        governance_verdict_id: Any | None,
        trace_id: Any | None,
        description: str = "",
    ) -> list[InvariantViolation]:
        """Validate BEFORE work packet construction — catches missing fields that Pydantic would reject."""
        violations = []
        v = self.check_governance_required(governance_verdict_id, description)
        if v:
            violations.append(v)
        v = self.check_trace_required(trace_id, description)
        if v:
            violations.append(v)
        return violations

    def has_hard_violations(self, violations: list[InvariantViolation]) -> bool:
        return any(v.law.severity == Severity.HARD_BLOCK for v in violations)

    @property
    def violations(self) -> list[InvariantViolation]:
        return list(self._violations)

    def clear_violations(self) -> None:
        self._violations.clear()

    def _record(self, violation: InvariantViolation) -> None:
        self._violations.append(violation)
        if violation.law.severity == Severity.HARD_BLOCK:
            logger.error(str(violation))
        elif violation.law.severity == Severity.SOFT_BLOCK:
            logger.warning(str(violation))
        else:
            logger.info(str(violation))
