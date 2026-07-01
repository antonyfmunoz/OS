"""Runtime SLO Definitions — concrete operational targets.

Defines Service Level Objectives for the UMH organism runtime.
SLOs are evaluated by HomeostasisEngine as a health dimension.
Critical violations trigger PROTECTIVE mode.

UMH substrate subsystem. Instance-agnostic.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class SLODefinition:
    """A single Service Level Objective."""

    name: str
    metric: str
    target: float
    window_seconds: int
    comparison: str
    severity: str
    description: str = ""

    def evaluate(self, actual: float) -> bool:
        if self.comparison == "gte":
            return actual >= self.target
        if self.comparison == "lte":
            return actual <= self.target
        if self.comparison == "gt":
            return actual > self.target
        if self.comparison == "lt":
            return actual < self.target
        return False


RUNTIME_SLOS: list[SLODefinition] = [
    SLODefinition(
        name="mutation_success_rate",
        metric="governed_spine.success_rate",
        target=0.95,
        window_seconds=300,
        comparison="gte",
        severity="critical",
        description="95% of governed mutations succeed within 5-minute window",
    ),
    SLODefinition(
        name="spine_latency_p95",
        metric="governed_spine.p95_latency_ms",
        target=500.0,
        window_seconds=300,
        comparison="lte",
        severity="warning",
        description="P95 spine submission latency under 500ms",
    ),
    SLODefinition(
        name="homeostasis_healthy_ratio",
        metric="homeostasis.healthy_time_ratio",
        target=0.90,
        window_seconds=3600,
        comparison="gte",
        severity="critical",
        description="System in HEALTHY mode 90%+ of the time per hour",
    ),
    SLODefinition(
        name="proof_capture_rate",
        metric="proof_store.capture_rate",
        target=0.80,
        window_seconds=3600,
        comparison="gte",
        severity="warning",
        description="80%+ of non-fast-path mutations have proof packages",
    ),
    SLODefinition(
        name="learning_signal_freshness",
        metric="outcome_learning.latest_signal_age_s",
        target=3600.0,
        window_seconds=3600,
        comparison="lte",
        severity="warning",
        description="Learning signals generated within the last hour",
    ),
    SLODefinition(
        name="recovery_mttr",
        metric="homeostasis.mean_recovery_time_s",
        target=30.0,
        window_seconds=86400,
        comparison="lte",
        severity="critical",
        description="Mean time to recovery under 30 seconds",
    ),
    SLODefinition(
        name="journal_write_rate",
        metric="execution_journal.entries_per_mutation",
        target=1.0,
        window_seconds=300,
        comparison="gte",
        severity="critical",
        description="Every mutation produces at least one journal entry",
    ),
    SLODefinition(
        name="event_emission_rate",
        metric="event_spine.events_per_mutation",
        target=1.0,
        window_seconds=300,
        comparison="gte",
        severity="critical",
        description="Every mutation emits at least one event",
    ),
]


def get_slo_by_name(name: str) -> SLODefinition | None:
    for slo in RUNTIME_SLOS:
        if slo.name == name:
            return slo
    return None


def critical_slos() -> list[SLODefinition]:
    return [s for s in RUNTIME_SLOS if s.severity == "critical"]


def warning_slos() -> list[SLODefinition]:
    return [s for s in RUNTIME_SLOS if s.severity == "warning"]
