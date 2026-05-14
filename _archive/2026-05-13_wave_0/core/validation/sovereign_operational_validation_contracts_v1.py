"""Sovereign Operational Validation Contracts v1.

15 contracts, 5 enums for adversarial constitutional validation.

The substrate must remain constitutionally governed under
operational stress, adversarial orchestration pressure,
replay pressure, topology pressure, continuity corruption
attempts, and governance evasion attempts.

UMH substrate subsystem. Phase 96.8CJ.
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


class SovereignValidationPhase(str, Enum):
    DEFINED = "defined"
    STAGED = "staged"
    VALIDATING = "validating"
    STRESSED = "stressed"
    VERIFIED = "verified"
    ARCHIVED = "archived"


class SovereignValidationEventType(str, Enum):
    VALIDATION_STARTED = "validation_started"
    ADVERSARIAL_SCENARIO_STARTED = "adversarial_scenario_started"
    GOVERNANCE_ATTACK_DETECTED = "governance_attack_detected"
    REPLAY_ATTACK_DETECTED = "replay_attack_detected"
    CONTINUITY_ATTACK_DETECTED = "continuity_attack_detected"
    TOPOLOGY_PRESSURE_DETECTED = "topology_pressure_detected"
    SEMANTIC_DRIFT_DETECTED = "semantic_drift_detected"
    SOVEREIGN_INTEGRITY_COMPUTED = "sovereign_integrity_computed"
    VALIDATION_COMPLETED = "validation_completed"


class AttackDomain(str, Enum):
    GOVERNANCE = "governance"
    REPLAY = "replay"
    CONTINUITY = "continuity"
    TOPOLOGY = "topology"
    SEMANTIC = "semantic"
    ORCHESTRATION = "orchestration"
    DEPLOYMENT = "deployment"
    OBSERVABILITY = "observability"


class PressureDomain(str, Enum):
    CONCURRENCY = "concurrency"
    ORCHESTRATION = "orchestration"
    REPLAY = "replay"
    CONTINUITY = "continuity"
    DEPLOYMENT = "deployment"
    RESILIENCE = "resilience"
    OBSERVABILITY = "observability"


class AttackOutcome(str, Enum):
    BLOCKED = "blocked"
    DETECTED = "detected"
    MITIGATED = "mitigated"
    BREACHED = "breached"


@dataclass
class SovereignValidationState:
    run_id: str
    scenarios_executed: int = 0
    attacks_blocked: int = 0
    attacks_breached: int = 0
    validation_id: str = field(default="")
    created_at: str = field(default_factory=_now_iso)

    def __post_init__(self) -> None:
        if not self.validation_id:
            self.validation_id = _deterministic_id(
                "sval-", self.run_id, str(self.scenarios_executed),
                self.created_at,
            )

    def to_dict(self) -> dict[str, Any]:
        return {
            "validation_id": self.validation_id,
            "run_id": self.run_id,
            "scenarios_executed": self.scenarios_executed,
            "attacks_blocked": self.attacks_blocked,
            "attacks_breached": self.attacks_breached,
            "created_at": self.created_at,
        }


@dataclass
class AdversarialScenarioState:
    scenario_name: str
    domain: str
    outcome: str = "blocked"
    scenario_id: str = field(default="")
    created_at: str = field(default_factory=_now_iso)

    def __post_init__(self) -> None:
        if not self.scenario_id:
            self.scenario_id = _deterministic_id(
                "advsc-", self.scenario_name, self.domain, self.created_at,
            )

    def to_dict(self) -> dict[str, Any]:
        return {
            "scenario_id": self.scenario_id,
            "scenario_name": self.scenario_name,
            "domain": self.domain,
            "outcome": self.outcome,
            "created_at": self.created_at,
        }


@dataclass
class GovernanceAttackState:
    attack_type: str
    blocked: bool = True
    attack_id: str = field(default="")
    created_at: str = field(default_factory=_now_iso)

    def __post_init__(self) -> None:
        if not self.attack_id:
            self.attack_id = _deterministic_id(
                "gatk-", self.attack_type, str(self.blocked), self.created_at,
            )

    def to_dict(self) -> dict[str, Any]:
        return {
            "attack_id": self.attack_id,
            "attack_type": self.attack_type,
            "blocked": self.blocked,
            "created_at": self.created_at,
        }


@dataclass
class ReplayAttackState:
    attack_type: str
    determinism_preserved: bool = True
    attack_id: str = field(default="")
    created_at: str = field(default_factory=_now_iso)

    def __post_init__(self) -> None:
        if not self.attack_id:
            self.attack_id = _deterministic_id(
                "ratk-", self.attack_type, str(self.determinism_preserved),
                self.created_at,
            )

    def to_dict(self) -> dict[str, Any]:
        return {
            "attack_id": self.attack_id,
            "attack_type": self.attack_type,
            "determinism_preserved": self.determinism_preserved,
            "created_at": self.created_at,
        }


@dataclass
class ContinuityAttackState:
    attack_type: str
    continuity_preserved: bool = True
    attack_id: str = field(default="")
    created_at: str = field(default_factory=_now_iso)

    def __post_init__(self) -> None:
        if not self.attack_id:
            self.attack_id = _deterministic_id(
                "catk-", self.attack_type, str(self.continuity_preserved),
                self.created_at,
            )

    def to_dict(self) -> dict[str, Any]:
        return {
            "attack_id": self.attack_id,
            "attack_type": self.attack_type,
            "continuity_preserved": self.continuity_preserved,
            "created_at": self.created_at,
        }


@dataclass
class TopologyAttackState:
    attack_type: str
    topology_preserved: bool = True
    attack_id: str = field(default="")
    created_at: str = field(default_factory=_now_iso)

    def __post_init__(self) -> None:
        if not self.attack_id:
            self.attack_id = _deterministic_id(
                "tatk-", self.attack_type, str(self.topology_preserved),
                self.created_at,
            )

    def to_dict(self) -> dict[str, Any]:
        return {
            "attack_id": self.attack_id,
            "attack_type": self.attack_type,
            "topology_preserved": self.topology_preserved,
            "created_at": self.created_at,
        }


@dataclass
class SemanticAttackState:
    attack_type: str
    consistency_preserved: bool = True
    attack_id: str = field(default="")
    created_at: str = field(default_factory=_now_iso)

    def __post_init__(self) -> None:
        if not self.attack_id:
            self.attack_id = _deterministic_id(
                "satk-", self.attack_type, str(self.consistency_preserved),
                self.created_at,
            )

    def to_dict(self) -> dict[str, Any]:
        return {
            "attack_id": self.attack_id,
            "attack_type": self.attack_type,
            "consistency_preserved": self.consistency_preserved,
            "created_at": self.created_at,
        }


@dataclass
class RuntimePressureState:
    domain: str
    pressure_level: int = 0
    bounded: bool = True
    pressure_id: str = field(default="")
    created_at: str = field(default_factory=_now_iso)

    def __post_init__(self) -> None:
        if not self.pressure_id:
            self.pressure_id = _deterministic_id(
                "rpres-", self.domain, str(self.pressure_level),
                self.created_at,
            )

    def to_dict(self) -> dict[str, Any]:
        return {
            "pressure_id": self.pressure_id,
            "domain": self.domain,
            "pressure_level": self.pressure_level,
            "bounded": self.bounded,
            "created_at": self.created_at,
        }


@dataclass
class ValidationBoundaryState:
    limit_name: str
    current_value: int = 0
    max_value: int = 0
    exceeded: bool = False
    boundary_id: str = field(default="")
    created_at: str = field(default_factory=_now_iso)

    def __post_init__(self) -> None:
        if not self.boundary_id:
            self.boundary_id = _deterministic_id(
                "vbnd-", self.limit_name, str(self.current_value),
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
class SovereignIntegrityState:
    governance_integrity: bool = True
    replay_integrity: bool = True
    continuity_integrity: bool = True
    topology_integrity: bool = True
    constitutional_integrity: bool = True
    observability_integrity: bool = True
    deployment_integrity: bool = True
    integrity_id: str = field(default="")
    created_at: str = field(default_factory=_now_iso)

    def __post_init__(self) -> None:
        if not self.integrity_id:
            self.integrity_id = _deterministic_id(
                "sint-", str(self.governance_integrity),
                str(self.constitutional_integrity), self.created_at,
            )

    @property
    def sovereign_integrity_score(self) -> float:
        checks = [
            self.governance_integrity, self.replay_integrity,
            self.continuity_integrity, self.topology_integrity,
            self.constitutional_integrity, self.observability_integrity,
            self.deployment_integrity,
        ]
        return sum(1 for c in checks if c) / len(checks)

    def to_dict(self) -> dict[str, Any]:
        return {
            "integrity_id": self.integrity_id,
            "governance_integrity": self.governance_integrity,
            "replay_integrity": self.replay_integrity,
            "continuity_integrity": self.continuity_integrity,
            "topology_integrity": self.topology_integrity,
            "constitutional_integrity": self.constitutional_integrity,
            "observability_integrity": self.observability_integrity,
            "deployment_integrity": self.deployment_integrity,
            "sovereign_integrity_score": self.sovereign_integrity_score,
            "created_at": self.created_at,
        }


@dataclass
class ConstitutionalDurabilityState:
    domain: str
    attacks_survived: int = 0
    attacks_total: int = 0
    durable: bool = True
    durability_id: str = field(default="")
    created_at: str = field(default_factory=_now_iso)

    def __post_init__(self) -> None:
        if not self.durability_id:
            self.durability_id = _deterministic_id(
                "cdur-", self.domain, str(self.attacks_survived),
                self.created_at,
            )

    def to_dict(self) -> dict[str, Any]:
        return {
            "durability_id": self.durability_id,
            "domain": self.domain,
            "attacks_survived": self.attacks_survived,
            "attacks_total": self.attacks_total,
            "durable": self.durable,
            "created_at": self.created_at,
        }


@dataclass
class RuntimeStressState:
    stress_type: str
    intensity: int = 0
    survived: bool = True
    stress_id: str = field(default="")
    created_at: str = field(default_factory=_now_iso)

    def __post_init__(self) -> None:
        if not self.stress_id:
            self.stress_id = _deterministic_id(
                "rstrs-", self.stress_type, str(self.intensity),
                self.created_at,
            )

    def to_dict(self) -> dict[str, Any]:
        return {
            "stress_id": self.stress_id,
            "stress_type": self.stress_type,
            "intensity": self.intensity,
            "survived": self.survived,
            "created_at": self.created_at,
        }


@dataclass
class ValidationReplayState:
    check_name: str
    input_hash: str = ""
    output_hash: str = ""
    deterministic: bool = True
    replay_id: str = field(default="")
    created_at: str = field(default_factory=_now_iso)

    def __post_init__(self) -> None:
        if not self.replay_id:
            self.replay_id = _deterministic_id(
                "vrplay-", self.check_name, self.input_hash,
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
class ValidationObservabilityState:
    events_emitted: int = 0
    all_persisted: bool = True
    observability_id: str = field(default="")
    created_at: str = field(default_factory=_now_iso)

    def __post_init__(self) -> None:
        if not self.observability_id:
            self.observability_id = _deterministic_id(
                "vobs-", str(self.events_emitted),
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
class SovereignValidationReceipt:
    run_id: str
    outcome: str = "sovereign"
    scenarios_executed: int = 0
    attacks_blocked: int = 0
    receipt_id: str = field(default="")
    created_at: str = field(default_factory=_now_iso)

    def __post_init__(self) -> None:
        if not self.receipt_id:
            self.receipt_id = _deterministic_id(
                "svrcpt-", self.run_id, self.outcome, self.created_at,
            )

    def to_dict(self) -> dict[str, Any]:
        return {
            "receipt_id": self.receipt_id,
            "run_id": self.run_id,
            "outcome": self.outcome,
            "scenarios_executed": self.scenarios_executed,
            "attacks_blocked": self.attacks_blocked,
            "created_at": self.created_at,
        }
