"""External Sync Policy — governs how UMH relates to external tools.

An ExternalSyncPolicy defines the read/write/conflict resolution
strategy for a specific external source. Phase 13.3 implements
the model and dry-run evaluation only — no actual external writes.

Phase 13.3. UMH substrate subsystem. Instance-agnostic.
"""

from __future__ import annotations

import json
import logging
import os
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any
from uuid import uuid4

logger = logging.getLogger(__name__)

_REPO_ROOT = os.environ.get("UMH_ROOT", "/opt/OS")
_POLICIES_PATH = os.path.join(
    _REPO_ROOT, "data", "umh", "context_assimilation", "sync_policies.jsonl"
)


class CanonicalDirection(str, Enum):
    EXTERNAL_TO_UMH = "external_to_umh"
    UMH_TO_EXTERNAL = "umh_to_external"
    BIDIRECTIONAL_WITH_REVIEW = "bidirectional_with_review"
    UMH_CANONICAL_EXTERNAL_REFERENCE = "umh_canonical_external_reference"
    EXTERNAL_CANONICAL_REFERENCE_ONLY = "external_canonical_reference_only"
    DEPRECATED_EXTERNAL = "deprecated_external"


class ReadPolicy(str, Enum):
    ALLOWED = "allowed"
    ON_DEMAND = "on_demand"
    SCHEDULED = "scheduled"
    BLOCKED = "blocked"


class WritePolicy(str, Enum):
    DISABLED = "disabled"
    SUGGEST_ONLY = "suggest_only"
    OPERATOR_APPROVED = "operator_approved"
    AUTOMATIC_SAFE = "automatic_safe"


class ConflictPolicy(str, Enum):
    ASK_OPERATOR = "ask_operator"
    PREFER_NEWER = "prefer_newer"
    PREFER_UMH = "prefer_umh"
    PREFER_EXTERNAL = "prefer_external"
    PRESERVE_BOTH = "preserve_both"
    CREATE_CONTRADICTION = "create_contradiction"
    DEPRECATE_EXTERNAL = "deprecate_external"


class ExternalSyncStatus(str, Enum):
    ACTIVE = "active"
    PAUSED = "paused"
    DISABLED = "disabled"
    ERROR = "error"


@dataclass
class ExternalSyncPolicy:
    policy_id: str = ""
    source_type: str = ""
    source_id: str = ""
    canonical_direction: str = CanonicalDirection.EXTERNAL_TO_UMH.value
    read_policy: str = ReadPolicy.ON_DEMAND.value
    write_policy: str = WritePolicy.DISABLED.value
    conflict_policy: str = ConflictPolicy.ASK_OPERATOR.value
    approval_required: bool = True
    allowed_operations: list[str] = field(default_factory=list)
    blocked_operations: list[str] = field(default_factory=list)
    last_sync_at: float = 0.0
    status: str = ExternalSyncStatus.ACTIVE.value

    def __post_init__(self) -> None:
        if not self.policy_id:
            self.policy_id = f"sync-{uuid4().hex[:8]}"

    def to_dict(self) -> dict[str, Any]:
        return {
            "policy_id": self.policy_id,
            "source_type": self.source_type,
            "source_id": self.source_id,
            "canonical_direction": self.canonical_direction,
            "read_policy": self.read_policy,
            "write_policy": self.write_policy,
            "conflict_policy": self.conflict_policy,
            "approval_required": self.approval_required,
            "allowed_operations": self.allowed_operations,
            "blocked_operations": self.blocked_operations,
            "last_sync_at": self.last_sync_at,
            "status": self.status,
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> ExternalSyncPolicy:
        return cls(**{k: v for k, v in d.items() if k in cls.__dataclass_fields__})

    def evaluate_operation(self, operation: str) -> dict[str, Any]:
        """Dry-run policy evaluation — returns whether an operation is allowed."""
        if operation in self.blocked_operations:
            return {"allowed": False, "reason": "operation_blocked", "policy_id": self.policy_id}
        if self.write_policy == WritePolicy.DISABLED.value and operation.startswith("write"):
            return {"allowed": False, "reason": "writes_disabled", "policy_id": self.policy_id}
        if self.approval_required:
            return {"allowed": False, "reason": "approval_required", "policy_id": self.policy_id}
        if self.allowed_operations and operation not in self.allowed_operations:
            return {"allowed": False, "reason": "not_in_allowed_list", "policy_id": self.policy_id}
        return {"allowed": True, "reason": "policy_permits", "policy_id": self.policy_id}


class SyncPolicyStore:
    def __init__(self, path: str | None = None) -> None:
        self._path = path or _POLICIES_PATH
        self._policies: dict[str, ExternalSyncPolicy] = {}
        self._load()

    def _load(self) -> None:
        if not os.path.exists(self._path):
            return
        with open(self._path) as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    d = json.loads(line)
                    pol = ExternalSyncPolicy.from_dict(d)
                    self._policies[pol.policy_id] = pol
                except (json.JSONDecodeError, TypeError):
                    logger.warning("Skipping malformed sync policy line")

    def _save(self) -> None:
        os.makedirs(os.path.dirname(self._path), exist_ok=True)
        with open(self._path, "w") as f:
            for pol in self._policies.values():
                f.write(json.dumps(pol.to_dict(), default=str) + "\n")

    def save_policy(self, policy: ExternalSyncPolicy) -> ExternalSyncPolicy:
        self._policies[policy.policy_id] = policy
        self._save()
        return policy

    def get_policy(self, policy_id: str) -> ExternalSyncPolicy | None:
        return self._policies.get(policy_id)

    def get_for_source(self, source_id: str) -> ExternalSyncPolicy | None:
        for pol in self._policies.values():
            if pol.source_id == source_id:
                return pol
        return None

    def list_policies(
        self, source_type: str | None = None, status: str | None = None
    ) -> list[ExternalSyncPolicy]:
        result = list(self._policies.values())
        if source_type:
            result = [p for p in result if p.source_type == source_type]
        if status:
            result = [p for p in result if p.status == status]
        return result

    def count(self) -> int:
        return len(self._policies)
