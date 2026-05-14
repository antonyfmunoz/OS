"""Constitutional Operational Fabric Contracts v1.

15 contracts, 5 enums for operational fabric stabilization.

The substrate must remain constitutionally coherent under
concurrency, continuity restoration, replay validation,
scaling pressure, resilience events, deployment rollback,
cross-environment synchronization, long-horizon orchestration,
application projection, and operational recovery.

UMH substrate subsystem. Phase 96.8CH.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _deterministic_id(prefix: str, *parts: str) -> str:
    raw = "|".join(parts)
    h = hashlib.sha256(raw.encode()).hexdigest()[:12]
    return f"{prefix}{h}"


class StabilizationPhase(str, Enum):
    DEFINED = "defined"
    STAGED = "staged"
    STRESSED = "stressed"
    VALIDATED = "validated"
    HARDENED = "hardened"
    ARCHIVED = "archived"


class StabilizationEventType(str, Enum):
    STABILIZATION_RUN_STARTED = "stabilization_run_started"
    STABILIZATION_RUN_COMPLETED = "stabilization_run_completed"
    CONCURRENCY_VALIDATED = "concurrency_validated"
    REPLAY_DURABILITY_VALIDATED = "replay_durability_validated"
    CONTINUITY_DURABILITY_VALIDATED = "continuity_durability_validated"
    TOPOLOGY_DURABILITY_VALIDATED = "topology_durability_validated"
    STABILIZATION_BOUNDARY_DENIED = "stabilization_boundary_denied"


class DurabilityDomain(str, Enum):
    CONCURRENCY = "concurrency"
    REPLAY = "replay"
    CONTINUITY = "continuity"
    TOPOLOGY = "topology"
    RESILIENCE = "resilience"
    SCALING = "scaling"
    DEPLOYMENT = "deployment"
    ORCHESTRATION = "orchestration"


class StressIntensity(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    EXTREME = "extreme"


class StabilizationOutcome(str, Enum):
    STABLE = "stable"
    DEGRADED = "degraded"
    UNSTABLE = "unstable"
    FAILED = "failed"


@dataclass
class StabilizationScenario:
    name: str
    domain: str
    intensity: str = "medium"
    scenario_id: str = field(default="")
    created_at: str = field(default_factory=_now_iso)

    def __post_init__(self) -> None:
        if not self.scenario_id:
            self.scenario_id = _deterministic_id(
                "stab-", self.name, self.domain, self.created_at,
            )

    def to_dict(self) -> dict[str, Any]:
        return {
            "scenario_id": self.scenario_id,
            "name": self.name,
            "domain": self.domain,
            "intensity": self.intensity,
            "created_at": self.created_at,
        }


@dataclass
class RuntimeStressState:
    scenario_id: str
    outcome: str = "stable"
    checks_passed: int = 0
    checks_failed: int = 0
    stress_id: str = field(default="")
    created_at: str = field(default_factory=_now_iso)

    def __post_init__(self) -> None:
        if not self.stress_id:
            self.stress_id = _deterministic_id(
                "rstress-", self.scenario_id, self.outcome, self.created_at,
            )

    def to_dict(self) -> dict[str, Any]:
        return {
            "stress_id": self.stress_id,
            "scenario_id": self.scenario_id,
            "outcome": self.outcome,
            "checks_passed": self.checks_passed,
            "checks_failed": self.checks_failed,
            "created_at": self.created_at,
        }


@dataclass
class OperationalDurabilityState:
    domain: str
    durable: bool = True
    iterations: int = 0
    durability_id: str = field(default="")
    created_at: str = field(default_factory=_now_iso)

    def __post_init__(self) -> None:
        if not self.durability_id:
            self.durability_id = _deterministic_id(
                "odur-", self.domain, str(self.durable), self.created_at,
            )

    def to_dict(self) -> dict[str, Any]:
        return {
            "durability_id": self.durability_id,
            "domain": self.domain,
            "durable": self.durable,
            "iterations": self.iterations,
            "created_at": self.created_at,
        }


@dataclass
class ConcurrencyValidationState:
    concurrent_operations: int = 0
    all_deterministic: bool = True
    fanout_bounded: bool = True
    concurrency_id: str = field(default="")
    created_at: str = field(default_factory=_now_iso)

    def __post_init__(self) -> None:
        if not self.concurrency_id:
            self.concurrency_id = _deterministic_id(
                "cval-", str(self.concurrent_operations),
                str(self.all_deterministic), self.created_at,
            )

    def to_dict(self) -> dict[str, Any]:
        return {
            "concurrency_id": self.concurrency_id,
            "concurrent_operations": self.concurrent_operations,
            "all_deterministic": self.all_deterministic,
            "fanout_bounded": self.fanout_bounded,
            "created_at": self.created_at,
        }


@dataclass
class ReplayDurabilityState:
    layers_validated: int = 0
    all_deterministic: bool = True
    lineage_intact: bool = True
    replay_id: str = field(default="")
    created_at: str = field(default_factory=_now_iso)

    def __post_init__(self) -> None:
        if not self.replay_id:
            self.replay_id = _deterministic_id(
                "rdur-", str(self.layers_validated),
                str(self.all_deterministic), self.created_at,
            )

    def to_dict(self) -> dict[str, Any]:
        return {
            "replay_id": self.replay_id,
            "layers_validated": self.layers_validated,
            "all_deterministic": self.all_deterministic,
            "lineage_intact": self.lineage_intact,
            "created_at": self.created_at,
        }


@dataclass
class ContinuityDurabilityState:
    layers_validated: int = 0
    checkpoints_restored: int = 0
    all_restored: bool = True
    continuity_id: str = field(default="")
    created_at: str = field(default_factory=_now_iso)

    def __post_init__(self) -> None:
        if not self.continuity_id:
            self.continuity_id = _deterministic_id(
                "cdur-", str(self.layers_validated),
                str(self.all_restored), self.created_at,
            )

    def to_dict(self) -> dict[str, Any]:
        return {
            "continuity_id": self.continuity_id,
            "layers_validated": self.layers_validated,
            "checkpoints_restored": self.checkpoints_restored,
            "all_restored": self.all_restored,
            "created_at": self.created_at,
        }


@dataclass
class RecoveryDurabilityState:
    recovery_scenarios: int = 0
    all_stable: bool = True
    no_recursive_loops: bool = True
    recovery_id: str = field(default="")
    created_at: str = field(default_factory=_now_iso)

    def __post_init__(self) -> None:
        if not self.recovery_id:
            self.recovery_id = _deterministic_id(
                "recdur-", str(self.recovery_scenarios),
                str(self.all_stable), self.created_at,
            )

    def to_dict(self) -> dict[str, Any]:
        return {
            "recovery_id": self.recovery_id,
            "recovery_scenarios": self.recovery_scenarios,
            "all_stable": self.all_stable,
            "no_recursive_loops": self.no_recursive_loops,
            "created_at": self.created_at,
        }


@dataclass
class TopologyDurabilityState:
    topologies_validated: int = 0
    all_intact: bool = True
    no_orphans: bool = True
    no_hidden_mutation: bool = True
    topology_id: str = field(default="")
    created_at: str = field(default_factory=_now_iso)

    def __post_init__(self) -> None:
        if not self.topology_id:
            self.topology_id = _deterministic_id(
                "tdur-", str(self.topologies_validated),
                str(self.all_intact), self.created_at,
            )

    def to_dict(self) -> dict[str, Any]:
        return {
            "topology_id": self.topology_id,
            "topologies_validated": self.topologies_validated,
            "all_intact": self.all_intact,
            "no_orphans": self.no_orphans,
            "no_hidden_mutation": self.no_hidden_mutation,
            "created_at": self.created_at,
        }


@dataclass
class SynchronizationDurabilityState:
    targets_validated: int = 0
    all_synchronized: bool = True
    epoch_gaps_bounded: bool = True
    sync_id: str = field(default="")
    created_at: str = field(default_factory=_now_iso)

    def __post_init__(self) -> None:
        if not self.sync_id:
            self.sync_id = _deterministic_id(
                "sdur-", str(self.targets_validated),
                str(self.all_synchronized), self.created_at,
            )

    def to_dict(self) -> dict[str, Any]:
        return {
            "sync_id": self.sync_id,
            "targets_validated": self.targets_validated,
            "all_synchronized": self.all_synchronized,
            "epoch_gaps_bounded": self.epoch_gaps_bounded,
            "created_at": self.created_at,
        }


@dataclass
class FabricStabilityReceipt:
    run_id: str
    outcome: str = "stable"
    domains_validated: int = 0
    receipt_id: str = field(default="")
    created_at: str = field(default_factory=_now_iso)

    def __post_init__(self) -> None:
        if not self.receipt_id:
            self.receipt_id = _deterministic_id(
                "frcpt-", self.run_id, self.outcome, self.created_at,
            )

    def to_dict(self) -> dict[str, Any]:
        return {
            "receipt_id": self.receipt_id,
            "run_id": self.run_id,
            "outcome": self.outcome,
            "domains_validated": self.domains_validated,
            "created_at": self.created_at,
        }


@dataclass
class StabilityBoundaryState:
    limit_name: str
    current_value: int = 0
    max_value: int = 0
    exceeded: bool = False
    boundary_id: str = field(default="")
    created_at: str = field(default_factory=_now_iso)

    def __post_init__(self) -> None:
        if not self.boundary_id:
            self.boundary_id = _deterministic_id(
                "sbnd-", self.limit_name, str(self.current_value),
                self.created_at,
            )

    def to_dict(self) -> dict[str, Any]:
        return {
            "boundary_id": self.boundary_id,
            "limit_name": self.limit_name,
            "current_value": self.current_value,
            "max_value": self.max_value,
            "exceeded": self.exceeded,
            "created_at": self.created_at,
        }


@dataclass
class StabilityReplayState:
    check_name: str
    input_hash: str = ""
    output_hash: str = ""
    deterministic: bool = True
    replay_id: str = field(default="")
    created_at: str = field(default_factory=_now_iso)

    def __post_init__(self) -> None:
        if not self.replay_id:
            self.replay_id = _deterministic_id(
                "srplay-", self.check_name, self.input_hash,
                self.output_hash, self.created_at,
            )

    def to_dict(self) -> dict[str, Any]:
        return {
            "replay_id": self.replay_id,
            "check_name": self.check_name,
            "input_hash": self.input_hash,
            "output_hash": self.output_hash,
            "deterministic": self.deterministic,
            "created_at": self.created_at,
        }


@dataclass
class StabilityObservabilityState:
    events_emitted: int = 0
    all_persisted: bool = True
    observability_id: str = field(default="")
    created_at: str = field(default_factory=_now_iso)

    def __post_init__(self) -> None:
        if not self.observability_id:
            self.observability_id = _deterministic_id(
                "sobs-", str(self.events_emitted),
                str(self.all_persisted), self.created_at,
            )

    def to_dict(self) -> dict[str, Any]:
        return {
            "observability_id": self.observability_id,
            "events_emitted": self.events_emitted,
            "all_persisted": self.all_persisted,
            "created_at": self.created_at,
        }


@dataclass
class StabilityLifecycleState:
    phase: str = "defined"
    transitions: int = 0
    lifecycle_id: str = field(default="")
    created_at: str = field(default_factory=_now_iso)

    def __post_init__(self) -> None:
        if not self.lifecycle_id:
            self.lifecycle_id = _deterministic_id(
                "slc-", self.phase, str(self.transitions), self.created_at,
            )

    def to_dict(self) -> dict[str, Any]:
        return {
            "lifecycle_id": self.lifecycle_id,
            "phase": self.phase,
            "transitions": self.transitions,
            "created_at": self.created_at,
        }


@dataclass
class StabilityGovernanceState:
    governance_preserved: bool = True
    spine_enforced: bool = True
    no_bypass: bool = True
    governance_id: str = field(default="")
    created_at: str = field(default_factory=_now_iso)

    def __post_init__(self) -> None:
        if not self.governance_id:
            self.governance_id = _deterministic_id(
                "sgov-", str(self.governance_preserved),
                str(self.spine_enforced), self.created_at,
            )

    def to_dict(self) -> dict[str, Any]:
        return {
            "governance_id": self.governance_id,
            "governance_preserved": self.governance_preserved,
            "spine_enforced": self.spine_enforced,
            "no_bypass": self.no_bypass,
            "created_at": self.created_at,
        }
