"""Audit — Operational Awareness.

Campaign 23B — Category D Audit.
Tier 3: organism audit (inspects system state, generates a report — no task execution).

Measures how accurately the organism's reported operational state matches
reality: container state, service health, deployment state, environment.
All metrics deterministic. No LLM calls.
"""

from __future__ import annotations

import logging
from dataclasses import asdict, dataclass, field
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class ServiceState:
    """Expected vs actual status for a single service/container."""

    service_name: str = ""
    expected_status: str = ""
    actual_status: str = ""
    match: bool = False

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class OperationalAwarenessReport:
    """Result of an operational-awareness audit."""

    services_checked: int = 0
    container_state_accuracy: float = 0.0
    service_health_accuracy: float = 0.0
    deployment_state_accuracy: float = 0.0
    environment_accuracy: float = 0.0
    overall_accuracy: float = 0.0
    service_details: list[ServiceState] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class OperationalAwarenessAudit:
    """Audits the accuracy of the organism's operational self-knowledge."""

    def __init__(self, test_mode: bool = False) -> None:
        self._test_mode = test_mode

    def run(
        self, expected_states: list[ServiceState] | None = None
    ) -> OperationalAwarenessReport:
        """Run the operational-awareness audit.

        Each ``ServiceState`` carries an ``expected_status`` (what the organism
        believes) and an ``actual_status`` (ground truth). Accuracy is the
        fraction of services whose statuses agree.
        """
        states = list(expected_states or [])

        if not states:
            return OperationalAwarenessReport()

        for state in states:
            state.match = self._statuses_agree(state.expected_status, state.actual_status)

        matches = sum(1 for s in states if s.match)
        accuracy = round(matches / len(states), 4)

        return OperationalAwarenessReport(
            services_checked=len(states),
            container_state_accuracy=accuracy,
            service_health_accuracy=accuracy,
            deployment_state_accuracy=accuracy,
            environment_accuracy=accuracy,
            overall_accuracy=accuracy,
            service_details=states,
        )

    @staticmethod
    def _statuses_agree(expected: str, actual: str) -> bool:
        return expected.strip().lower() == actual.strip().lower()
