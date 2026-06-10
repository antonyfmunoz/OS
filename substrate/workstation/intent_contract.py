"""Intent contract — converts high-level operator intent into end-state designs.

When the operator says "build this", "fix this", "get this shipped", the
advisor creates an IntentContract: a structured end-state specification with
acceptance criteria, proof requirements, and autonomy boundaries.

The contract feeds the loop engine — loops run until the contract's
acceptance criteria are verified or a blocker requires human judgment.

Substrate layer. Instance-agnostic.
"""

from __future__ import annotations

import json
import logging
import os
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


class IntentStatus(str):
    CAPTURED = "captured"
    CONTRACT_CREATED = "contract_created"
    PLANNED = "planned"
    EXECUTING = "executing"
    CHECKING = "checking"
    NOT_DONE_RETRYING = "not_done_retrying"
    BLOCKED = "blocked"
    NEEDS_APPROVAL = "needs_approval"
    VERIFIED_DONE = "verified_done"
    SEALED = "sealed"
    ABANDONED = "abandoned"


@dataclass
class IntentContract:
    """Structured end-state design from high-level operator intent."""

    intent_id: str = ""
    operator_intent: str = ""
    desired_end_state: str = ""
    acceptance_criteria: list[str] = field(default_factory=list)
    constraints: list[str] = field(default_factory=list)
    allowed_autonomy: str = "autonomous_with_approval"
    risk_level: str = "medium"
    proof_required: list[str] = field(default_factory=list)
    max_iterations: int = 10
    review_cadence: str = "on_blocker_or_completion"
    status: str = IntentStatus.CAPTURED
    current_iteration: int = 0
    blocker: str = ""
    evidence_log: list[str] = field(default_factory=list)
    created_at: str = ""
    updated_at: str = ""
    completed_at: str = ""

    def __post_init__(self) -> None:
        if not self.intent_id:
            self.intent_id = f"intent_{uuid.uuid4().hex[:12]}"
        if not self.created_at:
            self.created_at = datetime.now(timezone.utc).isoformat()
        if not self.updated_at:
            self.updated_at = self.created_at

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> IntentContract:
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})

    @property
    def is_terminal(self) -> bool:
        return self.status in (
            IntentStatus.VERIFIED_DONE,
            IntentStatus.SEALED,
            IntentStatus.ABANDONED,
        )

    @property
    def is_blocked(self) -> bool:
        return self.status in (
            IntentStatus.BLOCKED,
            IntentStatus.NEEDS_APPROVAL,
        )

    def advance(self, evidence: str, new_status: str | None = None) -> None:
        """Record evidence and optionally advance status."""
        self.current_iteration += 1
        self.evidence_log.append(
            f"iteration={self.current_iteration}: {evidence}"
        )
        if new_status:
            self.status = new_status
        self.updated_at = datetime.now(timezone.utc).isoformat()

    def mark_verified(self, proof: str) -> None:
        self.status = IntentStatus.VERIFIED_DONE
        self.evidence_log.append(f"VERIFIED: {proof}")
        self.completed_at = datetime.now(timezone.utc).isoformat()
        self.updated_at = self.completed_at

    def mark_blocked(self, blocker: str) -> None:
        self.status = IntentStatus.BLOCKED
        self.blocker = blocker
        self.updated_at = datetime.now(timezone.utc).isoformat()

    def mark_needs_approval(self, reason: str) -> None:
        self.status = IntentStatus.NEEDS_APPROVAL
        self.blocker = reason
        self.updated_at = datetime.now(timezone.utc).isoformat()

    def seal(self) -> None:
        self.status = IntentStatus.SEALED
        self.completed_at = datetime.now(timezone.utc).isoformat()
        self.updated_at = self.completed_at

    def abandon(self, reason: str) -> None:
        self.status = IntentStatus.ABANDONED
        self.blocker = reason
        self.completed_at = datetime.now(timezone.utc).isoformat()
        self.updated_at = self.completed_at


_INTENT_VERBS: dict[str, str] = {
    "build": "medium",
    "fix": "medium",
    "ship": "high",
    "deploy": "high",
    "research": "low",
    "investigate": "low",
    "set up": "medium",
    "finish": "medium",
    "get": "medium",
    "make": "medium",
    "create": "medium",
    "implement": "medium",
    "add": "low",
    "remove": "medium",
    "delete": "high",
    "refactor": "medium",
    "optimize": "medium",
    "debug": "medium",
    "test": "low",
    "review": "low",
    "audit": "low",
}


def extract_intent_risk(intent_text: str) -> str:
    """Deterministically classify risk from intent text."""
    lower = intent_text.lower().strip()
    for verb, risk in _INTENT_VERBS.items():
        if lower.startswith(verb):
            return risk
    return "medium"


def create_contract_from_intent(
    operator_intent: str,
    desired_end_state: str = "",
    acceptance_criteria: list[str] | None = None,
    constraints: list[str] | None = None,
    autonomy: str = "autonomous_with_approval",
    max_iterations: int = 10,
) -> IntentContract:
    """Create an IntentContract from operator intent.

    If desired_end_state is not provided, it is derived from the intent.
    """
    if not desired_end_state:
        desired_end_state = f"Completed: {operator_intent}"

    risk = extract_intent_risk(operator_intent)

    contract = IntentContract(
        operator_intent=operator_intent,
        desired_end_state=desired_end_state,
        acceptance_criteria=acceptance_criteria or [],
        constraints=constraints or [],
        allowed_autonomy=autonomy,
        risk_level=risk,
        max_iterations=max_iterations,
        status=IntentStatus.CONTRACT_CREATED,
    )

    logger.info(
        "Intent contract created: %s (risk=%s, autonomy=%s)",
        contract.intent_id, risk, autonomy,
    )
    return contract


class IntentContractManager:
    """Manages intent contract persistence and lifecycle."""

    def __init__(self, state_dir: str | Path | None = None) -> None:
        if state_dir is None:
            root = os.environ.get("UMH_ROOT", "/opt/OS")
            state_dir = os.path.join(root, "data", "umh", "workstation_state")
        self._dir = Path(state_dir)
        self._dir.mkdir(parents=True, exist_ok=True)
        self._active_path = self._dir / "active_intents.json"
        self._history_path = self._dir / "intent_history.jsonl"

    def save(self, contract: IntentContract) -> None:
        """Persist a contract (upsert into active list)."""
        active = self._load_active()
        active[contract.intent_id] = contract.to_dict()
        self._active_path.write_text(
            json.dumps(active, indent=2, default=str), encoding="utf-8",
        )

    def get(self, intent_id: str) -> IntentContract | None:
        """Load a specific contract by ID."""
        active = self._load_active()
        data = active.get(intent_id)
        if data:
            return IntentContract.from_dict(data)
        return None

    def get_active(self) -> list[IntentContract]:
        """Return all non-terminal contracts."""
        active = self._load_active()
        contracts = []
        for data in active.values():
            contract = IntentContract.from_dict(data)
            if not contract.is_terminal:
                contracts.append(contract)
        return contracts

    def get_blocked(self) -> list[IntentContract]:
        """Return contracts that are blocked or need approval."""
        return [c for c in self.get_active() if c.is_blocked]

    def archive(self, contract: IntentContract) -> None:
        """Move a terminal contract from active to history."""
        active = self._load_active()
        active.pop(contract.intent_id, None)
        self._active_path.write_text(
            json.dumps(active, indent=2, default=str), encoding="utf-8",
        )
        with open(self._history_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(contract.to_dict(), separators=(",", ":"), default=str) + "\n")

    def _load_active(self) -> dict[str, dict[str, Any]]:
        if not self._active_path.exists():
            return {}
        try:
            return json.loads(self._active_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, ValueError):
            return {}
