"""Operator Session — conversational state for operator-orchestrator interaction.

Tracks multi-turn operator sessions with intent extraction, turn history,
linked work packets, and session lifecycle status. Each session captures
the full conversational context needed for the orchestrator kernel
to maintain coherent, stateful operator interaction.

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


class SessionStatus(str, Enum):
    ACTIVE = "active"
    WAITING_FOR_OPERATOR = "waiting_for_operator"
    WAITING_FOR_APPROVAL = "waiting_for_approval"
    PACKET_DRAFTED = "packet_drafted"
    PACKET_RELEASED = "packet_released"
    BLOCKED = "blocked"
    COMPLETED = "completed"
    ARCHIVED = "archived"


_TERMINAL_SESSION_STATUSES = frozenset({
    SessionStatus.COMPLETED,
    SessionStatus.ARCHIVED,
})

_VALID_SESSION_TRANSITIONS: dict[SessionStatus, frozenset[SessionStatus]] = {
    SessionStatus.ACTIVE: frozenset({
        SessionStatus.WAITING_FOR_OPERATOR,
        SessionStatus.WAITING_FOR_APPROVAL,
        SessionStatus.PACKET_DRAFTED,
        SessionStatus.BLOCKED,
        SessionStatus.COMPLETED,
        SessionStatus.ARCHIVED,
    }),
    SessionStatus.WAITING_FOR_OPERATOR: frozenset({
        SessionStatus.ACTIVE,
        SessionStatus.BLOCKED,
        SessionStatus.COMPLETED,
        SessionStatus.ARCHIVED,
    }),
    SessionStatus.WAITING_FOR_APPROVAL: frozenset({
        SessionStatus.ACTIVE,
        SessionStatus.PACKET_RELEASED,
        SessionStatus.BLOCKED,
        SessionStatus.COMPLETED,
        SessionStatus.ARCHIVED,
    }),
    SessionStatus.PACKET_DRAFTED: frozenset({
        SessionStatus.ACTIVE,
        SessionStatus.WAITING_FOR_APPROVAL,
        SessionStatus.PACKET_RELEASED,
        SessionStatus.BLOCKED,
        SessionStatus.COMPLETED,
        SessionStatus.ARCHIVED,
    }),
    SessionStatus.PACKET_RELEASED: frozenset({
        SessionStatus.ACTIVE,
        SessionStatus.COMPLETED,
        SessionStatus.ARCHIVED,
    }),
    SessionStatus.BLOCKED: frozenset({
        SessionStatus.ACTIVE,
        SessionStatus.COMPLETED,
        SessionStatus.ARCHIVED,
    }),
    SessionStatus.COMPLETED: frozenset({
        SessionStatus.ARCHIVED,
    }),
    SessionStatus.ARCHIVED: frozenset(),
}


class IntentType(str, Enum):
    """High-level intent categories for operator input."""
    CREATE_WORK = "create_work"
    QUERY_STATUS = "query_status"
    QUERY_APPROVALS = "query_approvals"
    PREVIEW_PROPAGATION = "preview_propagation"
    PREVIEW_TOPOLOGY = "preview_topology"
    APPROVE = "approve"
    REJECT = "reject"
    ROADMAP_QUERY = "roadmap_query"
    GENERAL_QUERY = "general_query"
    RECOMMEND_NEXT = "recommend_next"


@dataclass
class OperatorIntent:
    """Extracted intent from a single operator input."""
    intent_id: str = field(default_factory=lambda: "oi-" + uuid4().hex[:12])
    intent_type: str = IntentType.GENERAL_QUERY.value
    raw_input: str = ""
    extracted_subject: str = ""
    extracted_action: str = ""
    extracted_constraints: list[str] = field(default_factory=list)
    extracted_entities: list[str] = field(default_factory=list)
    confidence: float = 0.0
    requires_work_packet: bool = False
    requires_approval: bool = False
    timestamp: float = field(default_factory=time.time)

    def to_dict(self) -> dict[str, Any]:
        return {
            "intent_id": self.intent_id,
            "intent_type": self.intent_type,
            "raw_input": self.raw_input,
            "extracted_subject": self.extracted_subject,
            "extracted_action": self.extracted_action,
            "extracted_constraints": self.extracted_constraints,
            "extracted_entities": self.extracted_entities,
            "confidence": round(self.confidence, 4),
            "requires_work_packet": self.requires_work_packet,
            "requires_approval": self.requires_approval,
            "timestamp": self.timestamp,
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> OperatorIntent:
        intent_type = d.get("intent_type", IntentType.GENERAL_QUERY.value)
        try:
            IntentType(intent_type)
        except ValueError:
            intent_type = IntentType.GENERAL_QUERY.value
        return cls(
            intent_id=d.get("intent_id", "oi-" + uuid4().hex[:12]),
            intent_type=intent_type,
            raw_input=d.get("raw_input", ""),
            extracted_subject=d.get("extracted_subject", ""),
            extracted_action=d.get("extracted_action", ""),
            extracted_constraints=d.get("extracted_constraints", []),
            extracted_entities=d.get("extracted_entities", []),
            confidence=float(d.get("confidence", 0.0)),
            requires_work_packet=bool(d.get("requires_work_packet", False)),
            requires_approval=bool(d.get("requires_approval", False)),
            timestamp=float(d.get("timestamp", time.time())),
        )


@dataclass
class OperatorTurn:
    """A single turn in the operator-orchestrator conversation."""
    turn_id: str = field(default_factory=lambda: "ot-" + uuid4().hex[:12])
    session_id: str = ""
    turn_number: int = 0
    operator_input: str = ""
    intent: OperatorIntent = field(default_factory=OperatorIntent)
    response_id: str = ""
    linked_packet_ids: list[str] = field(default_factory=list)
    linked_propagation_plan_ids: list[str] = field(default_factory=list)
    linked_approval_ids: list[str] = field(default_factory=list)
    timestamp: float = field(default_factory=time.time)

    def to_dict(self) -> dict[str, Any]:
        return {
            "turn_id": self.turn_id,
            "session_id": self.session_id,
            "turn_number": self.turn_number,
            "operator_input": self.operator_input,
            "intent": self.intent.to_dict(),
            "response_id": self.response_id,
            "linked_packet_ids": self.linked_packet_ids,
            "linked_propagation_plan_ids": self.linked_propagation_plan_ids,
            "linked_approval_ids": self.linked_approval_ids,
            "timestamp": self.timestamp,
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> OperatorTurn:
        return cls(
            turn_id=d.get("turn_id", "ot-" + uuid4().hex[:12]),
            session_id=d.get("session_id", ""),
            turn_number=int(d.get("turn_number", 0)),
            operator_input=d.get("operator_input", ""),
            intent=OperatorIntent.from_dict(d.get("intent", {})),
            response_id=d.get("response_id", ""),
            linked_packet_ids=d.get("linked_packet_ids", []),
            linked_propagation_plan_ids=d.get("linked_propagation_plan_ids", []),
            linked_approval_ids=d.get("linked_approval_ids", []),
            timestamp=float(d.get("timestamp", time.time())),
        )


@dataclass
class OperatorSession:
    """Multi-turn operator session with lifecycle tracking."""
    session_id: str = field(default_factory=lambda: "os-" + uuid4().hex[:12])
    status: str = SessionStatus.ACTIVE.value
    turns: list[OperatorTurn] = field(default_factory=list)
    linked_packet_ids: list[str] = field(default_factory=list)
    linked_propagation_plan_ids: list[str] = field(default_factory=list)
    linked_approval_ids: list[str] = field(default_factory=list)
    context_summary: str = ""
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)

    def add_turn(self, turn: OperatorTurn) -> None:
        """Add a turn, maintaining session links."""
        turn.session_id = self.session_id
        turn.turn_number = len(self.turns) + 1
        self.turns.append(turn)
        for pid in turn.linked_packet_ids:
            if pid not in self.linked_packet_ids:
                self.linked_packet_ids.append(pid)
        for ppid in turn.linked_propagation_plan_ids:
            if ppid not in self.linked_propagation_plan_ids:
                self.linked_propagation_plan_ids.append(ppid)
        for aid in turn.linked_approval_ids:
            if aid not in self.linked_approval_ids:
                self.linked_approval_ids.append(aid)
        self.updated_at = time.time()

    def transition_status(self, new_status: str) -> bool:
        """Transition session status with validation."""
        try:
            current = SessionStatus(self.status)
            target = SessionStatus(new_status)
        except ValueError:
            logger.warning("invalid session status: %s -> %s", self.status, new_status)
            return False
        if target not in _VALID_SESSION_TRANSITIONS.get(current, frozenset()):
            logger.warning("invalid session transition: %s -> %s", self.status, new_status)
            return False
        self.status = new_status
        self.updated_at = time.time()
        return True

    def to_dict(self) -> dict[str, Any]:
        return {
            "session_id": self.session_id,
            "status": self.status,
            "turns": [t.to_dict() for t in self.turns],
            "linked_packet_ids": self.linked_packet_ids,
            "linked_propagation_plan_ids": self.linked_propagation_plan_ids,
            "linked_approval_ids": self.linked_approval_ids,
            "context_summary": self.context_summary,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> OperatorSession:
        status = d.get("status", SessionStatus.ACTIVE.value)
        try:
            SessionStatus(status)
        except ValueError:
            status = SessionStatus.ACTIVE.value
        return cls(
            session_id=d.get("session_id", "os-" + uuid4().hex[:12]),
            status=status,
            turns=[OperatorTurn.from_dict(t) for t in d.get("turns", [])],
            linked_packet_ids=d.get("linked_packet_ids", []),
            linked_propagation_plan_ids=d.get("linked_propagation_plan_ids", []),
            linked_approval_ids=d.get("linked_approval_ids", []),
            context_summary=d.get("context_summary", ""),
            created_at=float(d.get("created_at", time.time())),
            updated_at=float(d.get("updated_at", time.time())),
        )


# ── Persistence ──────────────────────────────────────────────────────────

def _default_sessions_path() -> str:
    return os.path.join(
        _REPO_ROOT, "data", "umh", "operator_experience", "sessions.jsonl",
    )


def persist_sessions(
    sessions: list[OperatorSession],
    path: str | None = None,
) -> None:
    """Atomic JSONL write for operator sessions."""
    target = path or _default_sessions_path()
    os.makedirs(os.path.dirname(target), exist_ok=True)
    fd, tmp = tempfile.mkstemp(
        dir=os.path.dirname(target), suffix=".tmp",
    )
    try:
        with os.fdopen(fd, "w") as f:
            for s in sessions:
                f.write(json.dumps(s.to_dict(), default=str, separators=(",", ":")) + "\n")
        os.replace(tmp, target)
    except Exception:
        if os.path.exists(tmp):
            os.unlink(tmp)
        raise


def load_sessions(path: str | None = None) -> list[OperatorSession]:
    """Load operator sessions from JSONL."""
    target = path or _default_sessions_path()
    if not os.path.exists(target):
        return []
    sessions: list[OperatorSession] = []
    with open(target, "r") as f:
        for line in f:
            line = line.strip()
            if line:
                try:
                    sessions.append(OperatorSession.from_dict(json.loads(line)))
                except (json.JSONDecodeError, KeyError) as e:
                    logger.warning("skipping malformed session line: %s", e)
    return sessions


def persist_turns(
    turns: list[OperatorTurn],
    path: str | None = None,
) -> None:
    """Append-only JSONL write for operator turns."""
    target = path or os.path.join(
        _REPO_ROOT, "data", "umh", "operator_experience", "turns.jsonl",
    )
    os.makedirs(os.path.dirname(target), exist_ok=True)
    with open(target, "a") as f:
        for t in turns:
            f.write(json.dumps(t.to_dict(), default=str, separators=(",", ":")) + "\n")


def persist_intents(
    intents: list[OperatorIntent],
    path: str | None = None,
) -> None:
    """Append-only JSONL write for operator intents."""
    target = path or os.path.join(
        _REPO_ROOT, "data", "umh", "operator_experience", "intents.jsonl",
    )
    os.makedirs(os.path.dirname(target), exist_ok=True)
    with open(target, "a") as f:
        for i in intents:
            f.write(json.dumps(i.to_dict(), default=str, separators=(",", ":")) + "\n")
