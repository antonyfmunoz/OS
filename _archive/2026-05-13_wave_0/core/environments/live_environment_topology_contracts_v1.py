"""Live Environment Topology Contracts v1.

Contracts for multi-environment operational coordination:
  EnvironmentNode, EnvironmentTopology, EnvironmentCapabilityMap,
  EnvironmentHealthState, EnvironmentExecutionScope, EnvironmentTrustLevel,
  EnvironmentDelegationState, EnvironmentContinuityState,
  EnvironmentCoordinationReceipt, EnvironmentSynchronizationState,
  EnvironmentRoutingDecision, EnvironmentReplayState

UMH substrate subsystem. Phase 96.8BX.
"""

from __future__ import annotations

import enum
import hashlib
import json
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any


def _new_id(prefix: str) -> str:
    return f"{prefix}-{uuid.uuid4().hex[:12]}"


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _content_hash(data: Any) -> str:
    raw = json.dumps(data, sort_keys=True, default=str)
    return hashlib.sha256(raw.encode()).hexdigest()[:16]


# ── Enums ──────────────────────────────────────────────


class EnvironmentLifecycleState(enum.Enum):
    REGISTERED = "registered"
    AVAILABLE = "available"
    SYNCHRONIZED = "synchronized"
    DELEGATED = "delegated"
    EXECUTING = "executing"
    PAUSED = "paused"
    RESTORED = "restored"
    UNAVAILABLE = "unavailable"
    ARCHIVED = "archived"
    TERMINATED = "terminated"


class EnvironmentEventType(enum.Enum):
    ENVIRONMENT_REGISTERED = "environment_registered"
    ENVIRONMENT_AVAILABLE = "environment_available"
    ENVIRONMENT_UNAVAILABLE = "environment_unavailable"
    ENVIRONMENT_SELECTED = "environment_selected"
    ENVIRONMENT_DELEGATED = "environment_delegated"
    ENVIRONMENT_DENIED = "environment_denied"
    ENVIRONMENT_SYNCHRONIZED = "environment_synchronized"
    ENVIRONMENT_RESTORED = "environment_restored"
    ENVIRONMENT_CHECKPOINTED = "environment_checkpointed"
    ENVIRONMENT_REPLAYED = "environment_replayed"


class TrustTier(enum.Enum):
    FULL = "full"
    GOVERNED = "governed"
    RESTRICTED = "restricted"
    UNTRUSTED = "untrusted"


class DelegationType(enum.Enum):
    EXECUTION = "execution"
    OBSERVATION = "observation"
    SYNCHRONIZATION = "synchronization"
    CHECKPOINT = "checkpoint"
    RESTORE = "restore"
    REPLAY = "replay"


class ChronologyEventKind(enum.Enum):
    ENVIRONMENT_REGISTERED = "environment_registered"
    ENVIRONMENT_ROUTED = "environment_routed"
    ENVIRONMENT_DELEGATED = "environment_delegated"
    DELEGATION_COMPLETED = "delegation_completed"
    TOPOLOGY_SYNCHRONIZED = "topology_synchronized"
    ENVIRONMENT_CHECKPOINTED = "environment_checkpointed"
    ENVIRONMENT_RESTORED = "environment_restored"
    ENVIRONMENT_HEALTH_CHANGED = "environment_health_changed"
    ENVIRONMENT_TERMINATED = "environment_terminated"
    ENVIRONMENT_ARCHIVED = "environment_archived"


# ── Contracts ──────────────────────────────────────────


@dataclass
class EnvironmentNode:
    environment_id: str = field(default_factory=lambda: _new_id("env"))
    name: str = ""
    environment_type: str = ""
    trust_tier: str = TrustTier.GOVERNED.value
    capabilities: list[str] = field(default_factory=list)
    state: str = EnvironmentLifecycleState.REGISTERED.value
    parent_id: str = ""
    created_at: str = field(default_factory=_now_iso)

    def to_dict(self) -> dict[str, Any]:
        return {
            "environment_id": self.environment_id,
            "name": self.name,
            "environment_type": self.environment_type,
            "trust_tier": self.trust_tier,
            "capabilities": self.capabilities,
            "state": self.state,
            "parent_id": self.parent_id,
            "created_at": self.created_at,
        }


@dataclass
class EnvironmentTopology:
    topology_id: str = field(default_factory=lambda: _new_id("topo"))
    nodes: list[EnvironmentNode] = field(default_factory=list)
    edges: list[dict[str, str]] = field(default_factory=list)
    created_at: str = field(default_factory=_now_iso)
    content_hash: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "topology_id": self.topology_id,
            "nodes": [n.to_dict() for n in self.nodes],
            "edges": self.edges,
            "created_at": self.created_at,
            "content_hash": self.content_hash,
        }


@dataclass
class EnvironmentCapabilityMap:
    environment_id: str = ""
    capabilities: dict[str, bool] = field(default_factory=dict)
    max_concurrent: int = 1
    supports_delegation: bool = False
    supports_checkpoint: bool = True
    supports_replay: bool = True
    updated_at: str = field(default_factory=_now_iso)

    def to_dict(self) -> dict[str, Any]:
        return {
            "environment_id": self.environment_id,
            "capabilities": self.capabilities,
            "max_concurrent": self.max_concurrent,
            "supports_delegation": self.supports_delegation,
            "supports_checkpoint": self.supports_checkpoint,
            "supports_replay": self.supports_replay,
            "updated_at": self.updated_at,
        }


@dataclass
class EnvironmentHealthState:
    environment_id: str = ""
    healthy: bool = True
    last_heartbeat: str = field(default_factory=_now_iso)
    consecutive_failures: int = 0
    degraded: bool = False
    reason: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "environment_id": self.environment_id,
            "healthy": self.healthy,
            "last_heartbeat": self.last_heartbeat,
            "consecutive_failures": self.consecutive_failures,
            "degraded": self.degraded,
            "reason": self.reason,
        }


@dataclass
class EnvironmentExecutionScope:
    environment_id: str = ""
    allowed_commands: list[str] = field(default_factory=list)
    forbidden_commands: list[str] = field(default_factory=list)
    max_execution_depth: int = 5
    max_delegation_depth: int = 3
    governance_required: bool = True

    def to_dict(self) -> dict[str, Any]:
        return {
            "environment_id": self.environment_id,
            "allowed_commands": self.allowed_commands,
            "forbidden_commands": self.forbidden_commands,
            "max_execution_depth": self.max_execution_depth,
            "max_delegation_depth": self.max_delegation_depth,
            "governance_required": self.governance_required,
        }


@dataclass
class EnvironmentTrustLevel:
    environment_id: str = ""
    tier: str = TrustTier.GOVERNED.value
    can_execute: bool = True
    can_delegate: bool = False
    can_synchronize: bool = True
    can_checkpoint: bool = True
    verified_at: str = field(default_factory=_now_iso)

    def to_dict(self) -> dict[str, Any]:
        return {
            "environment_id": self.environment_id,
            "tier": self.tier,
            "can_execute": self.can_execute,
            "can_delegate": self.can_delegate,
            "can_synchronize": self.can_synchronize,
            "can_checkpoint": self.can_checkpoint,
            "verified_at": self.verified_at,
        }


@dataclass
class EnvironmentDelegationState:
    delegation_id: str = field(default_factory=lambda: _new_id("edel"))
    from_environment: str = ""
    to_environment: str = ""
    delegation_type: str = DelegationType.EXECUTION.value
    campaign_id: str = ""
    approved: bool = False
    approved_by: str = ""
    depth: int = 0
    max_depth: int = 3
    state: str = "pending"
    created_at: str = field(default_factory=_now_iso)
    completed_at: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "delegation_id": self.delegation_id,
            "from_environment": self.from_environment,
            "to_environment": self.to_environment,
            "delegation_type": self.delegation_type,
            "campaign_id": self.campaign_id,
            "approved": self.approved,
            "approved_by": self.approved_by,
            "depth": self.depth,
            "max_depth": self.max_depth,
            "state": self.state,
            "created_at": self.created_at,
            "completed_at": self.completed_at,
        }


@dataclass
class EnvironmentContinuityState:
    environment_id: str = ""
    checkpoint_id: str = ""
    topology_hash: str = ""
    delegation_chain: list[str] = field(default_factory=list)
    synchronization_epoch: int = 0
    last_sync: str = ""
    content_hash: str = ""

    def _hashable(self) -> dict[str, Any]:
        return {
            "environment_id": self.environment_id,
            "checkpoint_id": self.checkpoint_id,
            "topology_hash": self.topology_hash,
            "delegation_chain": self.delegation_chain,
            "synchronization_epoch": self.synchronization_epoch,
        }

    def to_dict(self) -> dict[str, Any]:
        return {
            "environment_id": self.environment_id,
            "checkpoint_id": self.checkpoint_id,
            "topology_hash": self.topology_hash,
            "delegation_chain": self.delegation_chain,
            "synchronization_epoch": self.synchronization_epoch,
            "last_sync": self.last_sync,
            "content_hash": self.content_hash,
        }


@dataclass
class EnvironmentCoordinationReceipt:
    receipt_id: str = field(default_factory=lambda: _new_id("ercpt"))
    environment_id: str = ""
    operation: str = ""
    from_state: str = ""
    to_state: str = ""
    campaign_id: str = ""
    delegation_id: str = ""
    timestamp: str = field(default_factory=_now_iso)

    def to_dict(self) -> dict[str, Any]:
        return {
            "receipt_id": self.receipt_id,
            "environment_id": self.environment_id,
            "operation": self.operation,
            "from_state": self.from_state,
            "to_state": self.to_state,
            "campaign_id": self.campaign_id,
            "delegation_id": self.delegation_id,
            "timestamp": self.timestamp,
        }


@dataclass
class EnvironmentSynchronizationState:
    sync_id: str = field(default_factory=lambda: _new_id("esync"))
    source_environment: str = ""
    target_environment: str = ""
    sync_type: str = ""
    epoch: int = 0
    topology_hash: str = ""
    state: str = "pending"
    started_at: str = field(default_factory=_now_iso)
    completed_at: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "sync_id": self.sync_id,
            "source_environment": self.source_environment,
            "target_environment": self.target_environment,
            "sync_type": self.sync_type,
            "epoch": self.epoch,
            "topology_hash": self.topology_hash,
            "state": self.state,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
        }


@dataclass
class EnvironmentRoutingDecision:
    decision_id: str = field(default_factory=lambda: _new_id("eroute"))
    command: str = ""
    selected_environment: str = ""
    candidate_environments: list[str] = field(default_factory=list)
    trust_tier: str = ""
    governance_passed: bool = False
    reason: str = ""
    timestamp: str = field(default_factory=_now_iso)

    def to_dict(self) -> dict[str, Any]:
        return {
            "decision_id": self.decision_id,
            "command": self.command,
            "selected_environment": self.selected_environment,
            "candidate_environments": self.candidate_environments,
            "trust_tier": self.trust_tier,
            "governance_passed": self.governance_passed,
            "reason": self.reason,
            "timestamp": self.timestamp,
        }


@dataclass
class EnvironmentReplayState:
    replay_id: str = field(default_factory=lambda: _new_id("erply"))
    environment_id: str = ""
    trace_hash: str = ""
    routing_hash: str = ""
    delegation_hash: str = ""
    synchronization_hash: str = ""
    topology_hash: str = ""
    all_deterministic: bool = False
    timestamp: str = field(default_factory=_now_iso)

    def to_dict(self) -> dict[str, Any]:
        return {
            "replay_id": self.replay_id,
            "environment_id": self.environment_id,
            "trace_hash": self.trace_hash,
            "routing_hash": self.routing_hash,
            "delegation_hash": self.delegation_hash,
            "synchronization_hash": self.synchronization_hash,
            "topology_hash": self.topology_hash,
            "all_deterministic": self.all_deterministic,
            "timestamp": self.timestamp,
        }
