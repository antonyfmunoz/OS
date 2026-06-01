"""Reconciliation Session — structured operator-AI context alignment.

A ReconciliationSession tracks a dialogue between the operator and UMH
where context is diagnosed, canonical updates are proposed, decisions are
recorded, and work packets are generated. Sessions enforce the boundary
between exploration (no canon changes) and decision (approval required).

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
_SESSIONS_PATH = os.path.join(
    _REPO_ROOT, "data", "umh", "context_assimilation", "reconciliation_sessions.jsonl"
)
_DECISIONS_PATH = os.path.join(
    _REPO_ROOT, "data", "umh", "context_assimilation", "reconciliation_decisions.jsonl"
)


class SessionStatus(str, Enum):
    DRAFTED = "drafted"
    ACTIVE = "active"
    WAITING_FOR_OPERATOR = "waiting_for_operator"
    PROPOSALS_READY = "proposals_ready"
    APPROVAL_PENDING = "approval_pending"
    COMPLETED = "completed"
    BLOCKED = "blocked"
    ARCHIVED = "archived"


class ReconciliationMode(str, Enum):
    EXPLORATION = "exploration"
    RECONCILIATION = "reconciliation"
    DECISION = "decision"
    EXECUTION_PLANNING = "execution_planning"


@dataclass
class ReconciliationDecision:
    decision_id: str = ""
    session_id: str = ""
    question: str = ""
    operator_answer: str = ""
    decision_type: str = ""
    affected_proposals: list[str] = field(default_factory=list)
    confidence: float = 1.0
    timestamp: float = 0.0

    def __post_init__(self) -> None:
        if not self.decision_id:
            self.decision_id = f"dec-{uuid4().hex[:8]}"
        if not self.timestamp:
            self.timestamp = time.time()

    def to_dict(self) -> dict[str, Any]:
        return {
            "decision_id": self.decision_id,
            "session_id": self.session_id,
            "question": self.question,
            "operator_answer": self.operator_answer,
            "decision_type": self.decision_type,
            "affected_proposals": self.affected_proposals,
            "confidence": self.confidence,
            "timestamp": self.timestamp,
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> ReconciliationDecision:
        return cls(**{k: v for k, v in d.items() if k in cls.__dataclass_fields__})


@dataclass
class ReconciliationSession:
    session_id: str = ""
    operator_session_id: str = ""
    topic: str = ""
    scope: str = ""
    mode: str = ReconciliationMode.EXPLORATION.value
    status: str = SessionStatus.DRAFTED.value
    started_at: float = 0.0
    completed_at: float = 0.0
    source_ids: list[str] = field(default_factory=list)
    diagnostic_report_id: str = ""
    proposals: list[str] = field(default_factory=list)
    operator_questions: list[str] = field(default_factory=list)
    decisions: list[str] = field(default_factory=list)
    approved_updates: list[str] = field(default_factory=list)
    rejected_updates: list[str] = field(default_factory=list)
    generated_work_packets: list[str] = field(default_factory=list)
    propagation_previews: list[str] = field(default_factory=list)
    summary: str = ""
    confidence: float = 0.0

    def __post_init__(self) -> None:
        if not self.session_id:
            self.session_id = f"recon-{uuid4().hex[:8]}"
        if not self.started_at:
            self.started_at = time.time()

    def to_dict(self) -> dict[str, Any]:
        return {
            "session_id": self.session_id,
            "operator_session_id": self.operator_session_id,
            "topic": self.topic,
            "scope": self.scope,
            "mode": self.mode,
            "status": self.status,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
            "source_ids": self.source_ids,
            "diagnostic_report_id": self.diagnostic_report_id,
            "proposals": self.proposals,
            "operator_questions": self.operator_questions,
            "decisions": self.decisions,
            "approved_updates": self.approved_updates,
            "rejected_updates": self.rejected_updates,
            "generated_work_packets": self.generated_work_packets,
            "propagation_previews": self.propagation_previews,
            "summary": self.summary,
            "confidence": self.confidence,
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> ReconciliationSession:
        return cls(**{k: v for k, v in d.items() if k in cls.__dataclass_fields__})


class ReconciliationSessionStore:
    def __init__(
        self,
        sessions_path: str | None = None,
        decisions_path: str | None = None,
    ) -> None:
        self._sessions_path = sessions_path or _SESSIONS_PATH
        self._decisions_path = decisions_path or _DECISIONS_PATH
        self._sessions: dict[str, ReconciliationSession] = {}
        self._decisions: dict[str, ReconciliationDecision] = {}
        self._load()

    def _load(self) -> None:
        for path, store, cls in [
            (self._sessions_path, self._sessions, ReconciliationSession),
            (self._decisions_path, self._decisions, ReconciliationDecision),
        ]:
            if not os.path.exists(path):
                continue
            with open(path) as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        d = json.loads(line)
                        obj = cls.from_dict(d)
                        id_field = "session_id" if cls is ReconciliationSession else "decision_id"
                        store[getattr(obj, id_field)] = obj
                    except (json.JSONDecodeError, TypeError):
                        logger.warning("Skipping malformed %s line", cls.__name__)

    def _save_sessions(self) -> None:
        os.makedirs(os.path.dirname(self._sessions_path), exist_ok=True)
        with open(self._sessions_path, "w") as f:
            for sess in self._sessions.values():
                f.write(json.dumps(sess.to_dict(), default=str) + "\n")

    def _save_decisions(self) -> None:
        os.makedirs(os.path.dirname(self._decisions_path), exist_ok=True)
        with open(self._decisions_path, "w") as f:
            for dec in self._decisions.values():
                f.write(json.dumps(dec.to_dict(), default=str) + "\n")

    def create_session(self, session: ReconciliationSession) -> ReconciliationSession:
        self._sessions[session.session_id] = session
        self._save_sessions()
        return session

    def get_session(self, session_id: str) -> ReconciliationSession | None:
        return self._sessions.get(session_id)

    def list_sessions(
        self, status: str | None = None, topic: str | None = None
    ) -> list[ReconciliationSession]:
        result = list(self._sessions.values())
        if status:
            result = [s for s in result if s.status == status]
        if topic:
            result = [s for s in result if topic.lower() in s.topic.lower()]
        return result

    def update_session(self, session: ReconciliationSession) -> None:
        self._sessions[session.session_id] = session
        self._save_sessions()

    def add_decision(self, decision: ReconciliationDecision) -> ReconciliationDecision:
        self._decisions[decision.decision_id] = decision
        sess = self._sessions.get(decision.session_id)
        if sess:
            sess.decisions.append(decision.decision_id)
            self._save_sessions()
        self._save_decisions()
        return decision

    def get_decisions_for_session(
        self, session_id: str
    ) -> list[ReconciliationDecision]:
        return [
            d for d in self._decisions.values() if d.session_id == session_id
        ]

    def complete_session(self, session_id: str, summary: str = "") -> bool:
        sess = self._sessions.get(session_id)
        if not sess:
            return False
        sess.status = SessionStatus.COMPLETED.value
        sess.completed_at = time.time()
        sess.summary = summary
        self._save_sessions()
        return True

    def count(self) -> int:
        return len(self._sessions)
