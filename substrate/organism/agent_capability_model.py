"""Agent Capability Model — track agent reliability per capability.

Maps which agent types can execute which capabilities, with observed
reliability, success/failure counts, and linked evidence. Updates
automatically from execution outcomes.

UMH substrate subsystem. Instance-agnostic.
"""

from __future__ import annotations

import json
import logging
import os
import time
from dataclasses import dataclass, field
from typing import Any
from uuid import uuid4

logger = logging.getLogger(__name__)

_REPO_ROOT = os.environ.get("UMH_ROOT", "/opt/OS")


@dataclass
class AgentReliabilityRecord:
    record_id: str = field(default_factory=lambda: f"rel-{uuid4().hex[:8]}")
    agent_type: str = "developer_agent"
    capability: str = ""
    success: bool = True
    duration_ms: float = 0.0
    outcome_id: str = ""
    action_envelope_id: str = ""
    template_id: str = ""
    risk_class: str = "low"
    recorded_at: float = field(default_factory=time.time)

    def to_dict(self) -> dict[str, Any]:
        return {
            "record_id": self.record_id,
            "agent_type": self.agent_type,
            "capability": self.capability,
            "success": self.success,
            "duration_ms": self.duration_ms,
            "outcome_id": self.outcome_id,
            "action_envelope_id": self.action_envelope_id,
            "template_id": self.template_id,
            "risk_class": self.risk_class,
            "recorded_at": self.recorded_at,
        }


@dataclass
class AgentCapability:
    agent_type: str
    capability: str
    attempts: int = 0
    successes: int = 0
    failures: int = 0
    average_duration_ms: float = 0.0
    last_success_at: float = 0.0
    last_failure_at: float = 0.0
    linked_template_ids: list[str] = field(default_factory=list)
    linked_outcome_ids: list[str] = field(default_factory=list)
    linked_action_envelope_ids: list[str] = field(default_factory=list)
    risk_classes_handled: list[str] = field(default_factory=list)

    @property
    def confidence(self) -> float:
        if self.attempts == 0:
            return 0.0
        return self.successes / self.attempts

    @property
    def validation_success_rate(self) -> float:
        return self.confidence

    def to_dict(self) -> dict[str, Any]:
        return {
            "agent_type": self.agent_type,
            "capability": self.capability,
            "attempts": self.attempts,
            "successes": self.successes,
            "failures": self.failures,
            "average_duration_ms": round(self.average_duration_ms, 1),
            "confidence": round(self.confidence, 3),
            "validation_success_rate": round(self.validation_success_rate, 3),
            "last_success_at": self.last_success_at,
            "last_failure_at": self.last_failure_at,
            "linked_template_ids": self.linked_template_ids[-10:],
            "linked_outcome_ids": self.linked_outcome_ids[-10:],
            "linked_action_envelope_ids": self.linked_action_envelope_ids[-10:],
            "risk_classes_handled": sorted(set(self.risk_classes_handled)),
        }


@dataclass
class AgentCapabilityProfile:
    agent_type: str
    capabilities: dict[str, AgentCapability] = field(default_factory=dict)
    total_attempts: int = 0
    total_successes: int = 0
    total_failures: int = 0
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)

    @property
    def overall_reliability(self) -> float:
        if self.total_attempts == 0:
            return 0.0
        return self.total_successes / self.total_attempts

    def to_dict(self) -> dict[str, Any]:
        return {
            "agent_type": self.agent_type,
            "overall_reliability": round(self.overall_reliability, 3),
            "total_attempts": self.total_attempts,
            "total_successes": self.total_successes,
            "total_failures": self.total_failures,
            "capabilities": {k: v.to_dict() for k, v in self.capabilities.items()},
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }


class AgentCapabilityModel:
    """Tracks agent capability reliability from execution outcomes."""

    def __init__(self, store_dir: str | None = None):
        self._store_dir = store_dir or os.path.join(_REPO_ROOT, "data", "umh", "agents")
        self._profiles_path = os.path.join(self._store_dir, "capability_profiles.jsonl")
        self._records_path = os.path.join(self._store_dir, "reliability_records.jsonl")
        self._profiles: dict[str, AgentCapabilityProfile] = {}
        self._records: list[AgentReliabilityRecord] = []
        self._load()

    def _load(self) -> None:
        if os.path.isfile(self._records_path):
            try:
                with open(self._records_path) as f:
                    for line in f:
                        line = line.strip()
                        if not line:
                            continue
                        data = json.loads(line)
                        rec = AgentReliabilityRecord(**data)
                        self._records.append(rec)
                        self._apply_record(rec)
            except (json.JSONDecodeError, OSError) as e:
                logger.warning("Failed to load reliability records: %s", e)

    def _apply_record(self, rec: AgentReliabilityRecord) -> None:
        profile = self._profiles.get(rec.agent_type)
        if not profile:
            profile = AgentCapabilityProfile(agent_type=rec.agent_type)
            self._profiles[rec.agent_type] = profile

        cap = profile.capabilities.get(rec.capability)
        if not cap:
            cap = AgentCapability(agent_type=rec.agent_type, capability=rec.capability)
            profile.capabilities[rec.capability] = cap

        cap.attempts += 1
        profile.total_attempts += 1
        if rec.success:
            cap.successes += 1
            profile.total_successes += 1
            cap.last_success_at = rec.recorded_at
        else:
            cap.failures += 1
            profile.total_failures += 1
            cap.last_failure_at = rec.recorded_at

        if rec.duration_ms > 0:
            cap.average_duration_ms = (
                (cap.average_duration_ms * (cap.attempts - 1) + rec.duration_ms) / cap.attempts
            )

        if rec.outcome_id and rec.outcome_id not in cap.linked_outcome_ids:
            cap.linked_outcome_ids.append(rec.outcome_id)
        if rec.action_envelope_id and rec.action_envelope_id not in cap.linked_action_envelope_ids:
            cap.linked_action_envelope_ids.append(rec.action_envelope_id)
        if rec.template_id and rec.template_id not in cap.linked_template_ids:
            cap.linked_template_ids.append(rec.template_id)
        if rec.risk_class and rec.risk_class not in cap.risk_classes_handled:
            cap.risk_classes_handled.append(rec.risk_class)

        profile.updated_at = time.time()

    def _persist_record(self, rec: AgentReliabilityRecord) -> None:
        os.makedirs(os.path.dirname(self._records_path), exist_ok=True)
        with open(self._records_path, "a") as f:
            f.write(json.dumps(rec.to_dict(), default=str) + "\n")

    def update_reliability(
        self,
        agent_type: str,
        capabilities_used: list[str],
        success: bool,
        duration_ms: float = 0.0,
        outcome_id: str = "",
        action_envelope_id: str = "",
        template_id: str = "",
        risk_class: str = "low",
    ) -> list[AgentReliabilityRecord]:
        """Record reliability update for an agent's capabilities after execution."""
        records = []
        for cap_name in capabilities_used:
            rec = AgentReliabilityRecord(
                agent_type=agent_type,
                capability=cap_name,
                success=success,
                duration_ms=duration_ms,
                outcome_id=outcome_id,
                action_envelope_id=action_envelope_id,
                template_id=template_id,
                risk_class=risk_class,
            )
            self._records.append(rec)
            self._apply_record(rec)
            self._persist_record(rec)
            records.append(rec)
        return records

    def get_profile(self, agent_type: str) -> AgentCapabilityProfile | None:
        return self._profiles.get(agent_type)

    def get_capability(self, agent_type: str, capability: str) -> AgentCapability | None:
        profile = self._profiles.get(agent_type)
        if not profile:
            return None
        return profile.capabilities.get(capability)

    def get_reliability(self, agent_type: str, capability: str) -> float:
        cap = self.get_capability(agent_type, capability)
        return cap.confidence if cap else 0.0

    def list_profiles(self) -> list[AgentCapabilityProfile]:
        return list(self._profiles.values())

    def summary(self) -> dict[str, Any]:
        return {
            "total_profiles": len(self._profiles),
            "total_records": len(self._records),
            "profiles": {
                at: {
                    "overall_reliability": round(p.overall_reliability, 3),
                    "capabilities_tracked": len(p.capabilities),
                    "total_attempts": p.total_attempts,
                }
                for at, p in self._profiles.items()
            },
        }

    def to_dict(self) -> dict[str, Any]:
        return {
            "summary": self.summary(),
            "profiles": {at: p.to_dict() for at, p in self._profiles.items()},
        }

    def to_safe_dict(self) -> dict[str, Any]:
        """HTTP-safe serialization."""
        profiles = {}
        for at, p in self._profiles.items():
            caps = {}
            for cn, c in p.capabilities.items():
                caps[cn] = {
                    "confidence": round(c.confidence, 3),
                    "attempts": c.attempts,
                    "successes": c.successes,
                    "failures": c.failures,
                }
            profiles[at] = {
                "overall_reliability": round(p.overall_reliability, 3),
                "total_attempts": p.total_attempts,
                "capabilities": caps,
            }
        return {
            "summary": self.summary(),
            "profiles": profiles,
        }
