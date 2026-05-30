"""Operator Response — structured response contract for the orchestrator kernel.

Defines the OperatorResponse shape returned from every orchestrator kernel
interaction. Includes preview fields for work packets, delegation topologies,
workcells, propagation plans, human/approval actions, risks, blockers,
options, and system confidence.

Phase 13.0. UMH substrate subsystem. Instance-agnostic.
"""

from __future__ import annotations

import json
import logging
import os
import tempfile
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any
from uuid import uuid4

logger = logging.getLogger(__name__)

_REPO_ROOT = os.environ.get("UMH_ROOT", "/opt/OS")


class OutputMode(str, Enum):
    """Output mode for response rendering."""
    FULL = "full"
    SUMMARY = "summary"
    PREVIEW = "preview"
    CONFIRMATION = "confirmation"
    ERROR = "error"


@dataclass
class Option:
    """A single option presented to the operator for decision."""
    option_id: str = field(default_factory=lambda: "opt-" + uuid4().hex[:8])
    label: str = ""
    description: str = ""
    risk_class: str = "low"
    recommended: bool = False
    action_key: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "option_id": self.option_id,
            "label": self.label,
            "description": self.description,
            "risk_class": self.risk_class,
            "recommended": self.recommended,
            "action_key": self.action_key,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> Option:
        return cls(
            option_id=d.get("option_id", "opt-" + uuid4().hex[:8]),
            label=d.get("label", ""),
            description=d.get("description", ""),
            risk_class=d.get("risk_class", "low"),
            recommended=bool(d.get("recommended", False)),
            action_key=d.get("action_key", ""),
            metadata=d.get("metadata", {}),
        )


@dataclass
class OperatorResponse:
    """Structured response from orchestrator kernel to operator."""
    response_id: str = field(default_factory=lambda: "or-" + uuid4().hex[:12])
    session_id: str = ""
    turn_id: str = ""
    intent_type: str = ""
    output_mode: str = OutputMode.FULL.value
    summary: str = ""

    # Preview fields — populated by orchestrator flows
    work_packet_preview: dict[str, Any] | None = None
    delegation_topology_preview: dict[str, Any] | None = None
    workcells_preview: list[dict[str, Any]] | None = None
    propagation_preview: dict[str, Any] | None = None

    # Action requirements
    human_required_actions: list[dict[str, Any]] = field(default_factory=list)
    approval_required_actions: list[dict[str, Any]] = field(default_factory=list)

    # Risk / governance
    risks: list[dict[str, Any]] = field(default_factory=list)
    blockers: list[dict[str, Any]] = field(default_factory=list)

    # Decision support
    options: list[Option] = field(default_factory=list)
    system_confidence: float = 0.0

    # Linked entities
    linked_packet_ids: list[str] = field(default_factory=list)
    linked_propagation_plan_ids: list[str] = field(default_factory=list)
    linked_approval_ids: list[str] = field(default_factory=list)

    # Metadata
    data: dict[str, Any] = field(default_factory=dict)
    errors: list[str] = field(default_factory=list)
    timestamp: float = field(default_factory=time.time)

    # Safety invariant
    execution_occurred: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "response_id": self.response_id,
            "session_id": self.session_id,
            "turn_id": self.turn_id,
            "intent_type": self.intent_type,
            "output_mode": self.output_mode,
            "summary": self.summary,
            "work_packet_preview": self.work_packet_preview,
            "delegation_topology_preview": self.delegation_topology_preview,
            "workcells_preview": self.workcells_preview,
            "propagation_preview": self.propagation_preview,
            "human_required_actions": self.human_required_actions,
            "approval_required_actions": self.approval_required_actions,
            "risks": self.risks,
            "blockers": self.blockers,
            "options": [o.to_dict() for o in self.options],
            "system_confidence": round(self.system_confidence, 4),
            "linked_packet_ids": self.linked_packet_ids,
            "linked_propagation_plan_ids": self.linked_propagation_plan_ids,
            "linked_approval_ids": self.linked_approval_ids,
            "data": self.data,
            "errors": self.errors,
            "timestamp": self.timestamp,
            "execution_occurred": self.execution_occurred,
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> OperatorResponse:
        output_mode = d.get("output_mode", OutputMode.FULL.value)
        try:
            OutputMode(output_mode)
        except ValueError:
            output_mode = OutputMode.FULL.value
        return cls(
            response_id=d.get("response_id", "or-" + uuid4().hex[:12]),
            session_id=d.get("session_id", ""),
            turn_id=d.get("turn_id", ""),
            intent_type=d.get("intent_type", ""),
            output_mode=output_mode,
            summary=d.get("summary", ""),
            work_packet_preview=d.get("work_packet_preview"),
            delegation_topology_preview=d.get("delegation_topology_preview"),
            workcells_preview=d.get("workcells_preview"),
            propagation_preview=d.get("propagation_preview"),
            human_required_actions=d.get("human_required_actions", []),
            approval_required_actions=d.get("approval_required_actions", []),
            risks=d.get("risks", []),
            blockers=d.get("blockers", []),
            options=[Option.from_dict(o) for o in d.get("options", [])],
            system_confidence=float(d.get("system_confidence", 0.0)),
            linked_packet_ids=d.get("linked_packet_ids", []),
            linked_propagation_plan_ids=d.get("linked_propagation_plan_ids", []),
            linked_approval_ids=d.get("linked_approval_ids", []),
            data=d.get("data", {}),
            errors=d.get("errors", []),
            timestamp=float(d.get("timestamp", time.time())),
            execution_occurred=bool(d.get("execution_occurred", False)),
        )


# ── Persistence ──────────────────────────────────────────────────────────

def _default_responses_path() -> str:
    return os.path.join(
        _REPO_ROOT, "data", "umh", "operator_experience", "responses.jsonl",
    )


def persist_responses(
    responses: list[OperatorResponse],
    path: str | None = None,
) -> None:
    """Atomic JSONL write for operator responses."""
    target = path or _default_responses_path()
    os.makedirs(os.path.dirname(target), exist_ok=True)
    fd, tmp = tempfile.mkstemp(
        dir=os.path.dirname(target), suffix=".tmp",
    )
    try:
        with os.fdopen(fd, "w") as f:
            for r in responses:
                f.write(json.dumps(r.to_dict(), default=str, separators=(",", ":")) + "\n")
        os.replace(tmp, target)
    except Exception:
        if os.path.exists(tmp):
            os.unlink(tmp)
        raise


def load_responses(path: str | None = None) -> list[OperatorResponse]:
    """Load operator responses from JSONL."""
    target = path or _default_responses_path()
    if not os.path.exists(target):
        return []
    responses: list[OperatorResponse] = []
    with open(target, "r") as f:
        for line in f:
            line = line.strip()
            if line:
                try:
                    responses.append(OperatorResponse.from_dict(json.loads(line)))
                except (json.JSONDecodeError, KeyError) as e:
                    logger.warning("skipping malformed response line: %s", e)
    return responses
