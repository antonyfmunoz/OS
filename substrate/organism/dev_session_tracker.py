"""DevSessionTracker — wraps development sessions as governed spine executions.

Every CC session that produces commits becomes a governed execution flowing
through GovernedExecutionSpine, closing the loop: intent → work → proof → learning.

UMH substrate subsystem. Instance-agnostic.
"""

from __future__ import annotations

import json
import logging
import os
import time
from dataclasses import asdict, dataclass, field
from typing import Any
from uuid import uuid4

from substrate.organism.action_envelope import (
    ActionEnvelope,
    ActionType,
    BlastRadius,
    ExecutionConstraints,
    ReversibilityClass,
)

logger = logging.getLogger(__name__)


class DevSessionStatus:
    ACTIVE = "active"
    COMPLETED = "completed"
    ABANDONED = "abandoned"


@dataclass
class DevSession:
    session_id: str = field(default_factory=lambda: f"ds-{uuid4().hex[:12]}")
    started_at: float = field(default_factory=time.time)
    intent: str = ""
    projection_id: str = "umh"
    commits: list[dict[str, str]] = field(default_factory=list)
    files_modified: int = 0
    status: str = DevSessionStatus.ACTIVE
    completed_at: float = 0.0
    outcome: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> DevSession:
        d = dict(d)
        return cls(**{k: v for k, v in d.items() if k in cls.__dataclass_fields__})


class DevSessionTracker:
    """Tracks development sessions and produces ActionEnvelopes on completion."""

    def __init__(self, store_dir: str | None = None) -> None:
        if store_dir is None:
            from substrate.state.runtime_paths import runtime_state_dir

            store_dir = str(runtime_state_dir("organism"))
        self._store_dir = store_dir
        self._path = os.path.join(store_dir, "dev_sessions.jsonl")
        self._sessions: dict[str, DevSession] = {}
        self._load()

    def _load(self) -> None:
        if not os.path.exists(self._path):
            return
        try:
            with open(self._path, "r") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        d = json.loads(line)
                        s = DevSession.from_dict(d)
                        self._sessions[s.session_id] = s
                    except (json.JSONDecodeError, TypeError, KeyError) as exc:
                        logger.debug("skip malformed dev session line: %s", exc)
        except OSError as exc:
            logger.debug("cannot read %s: %s", self._path, exc)

    def _append(self, session: DevSession) -> None:
        os.makedirs(os.path.dirname(self._path), exist_ok=True)
        try:
            with open(self._path, "a") as f:
                f.write(json.dumps(session.to_dict(), default=str) + "\n")
        except OSError as exc:
            logger.debug("cannot append dev session: %s", exc)

    def _rewrite(self) -> None:
        os.makedirs(os.path.dirname(self._path), exist_ok=True)
        try:
            with open(self._path, "w") as f:
                for s in self._sessions.values():
                    f.write(json.dumps(s.to_dict(), default=str) + "\n")
        except OSError as exc:
            logger.debug("cannot rewrite dev sessions: %s", exc)

    def start_session(self, intent: str, projection_id: str = "umh") -> DevSession:
        session = DevSession(intent=intent, projection_id=projection_id)
        self._sessions[session.session_id] = session
        self._append(session)
        logger.info("dev session started: %s (%s)", session.session_id, intent[:80])
        return session

    def record_commit(self, session_id: str, sha: str, message: str) -> bool:
        s = self._sessions.get(session_id)
        if s is None or s.status != DevSessionStatus.ACTIVE:
            return False
        s.commits.append({"sha": sha, "message": message[:200]})
        self._rewrite()
        return True

    def record_files_modified(self, session_id: str, count: int) -> bool:
        s = self._sessions.get(session_id)
        if s is None or s.status != DevSessionStatus.ACTIVE:
            return False
        s.files_modified = count
        self._rewrite()
        return True

    def complete_session(self, session_id: str, outcome: str) -> ActionEnvelope | None:
        s = self._sessions.get(session_id)
        if s is None or s.status != DevSessionStatus.ACTIVE:
            return None
        s.status = DevSessionStatus.COMPLETED
        s.completed_at = time.time()
        s.outcome = outcome[:500]
        self._rewrite()

        duration = max(s.completed_at - s.started_at, 0)
        summary = (
            f"Dev session {s.session_id}: {s.intent[:100]} — "
            f"{len(s.commits)} commits, {s.files_modified} files, "
            f"{duration:.0f}s"
        )

        def _execute() -> tuple[str, bool]:
            return (summary, True)

        envelope = ActionEnvelope(
            intent=s.intent,
            action_type=ActionType.STATE,
            source="dev_session_tracker",
            execute_fn=_execute,
            risk_level="low",
            blast_radius=BlastRadius.LOCAL_RUNTIME,
            reversibility=ReversibilityClass.FULLY_REVERSIBLE,
            constraints=ExecutionConstraints(timeout_seconds=10.0),
            estimated_manual_seconds=duration,
            metadata={
                "session_id": s.session_id,
                "projection_id": s.projection_id,
                "commits": s.commits,
                "files_modified": s.files_modified,
                "duration_seconds": duration,
                "outcome": s.outcome,
            },
        )
        logger.info("dev session completed: %s — %s", s.session_id, outcome[:80])
        return envelope

    def submit_to_spine(
        self,
        session_id: str,
        outcome: str,
        spine: Any,
    ) -> tuple[ActionEnvelope | None, Any]:
        """Complete a session and submit its envelope to the governed spine.

        Returns (envelope, spine_result). If session is invalid or spine
        submission fails, returns (None, None).
        """
        envelope = self.complete_session(session_id, outcome)
        if envelope is None:
            return None, None
        try:
            result = spine.submit(envelope)
            return envelope, result
        except Exception as exc:
            logger.debug("spine submission failed for %s: %s", session_id, exc)
            return envelope, None

    def abandon_session(self, session_id: str) -> bool:
        s = self._sessions.get(session_id)
        if s is None or s.status != DevSessionStatus.ACTIVE:
            return False
        s.status = DevSessionStatus.ABANDONED
        s.completed_at = time.time()
        self._rewrite()
        logger.info("dev session abandoned: %s", session_id)
        return True

    def active_sessions(self) -> list[DevSession]:
        return [s for s in self._sessions.values() if s.status == DevSessionStatus.ACTIVE]

    def recent_sessions(self, limit: int = 20) -> list[DevSession]:
        ordered = sorted(self._sessions.values(), key=lambda s: s.started_at, reverse=True)
        return ordered[:limit]

    def summary(self) -> dict[str, Any]:
        active = [s for s in self._sessions.values() if s.status == DevSessionStatus.ACTIVE]
        completed = [s for s in self._sessions.values() if s.status == DevSessionStatus.COMPLETED]
        last = max(completed, key=lambda s: s.completed_at) if completed else None
        return {
            "active_count": len(active),
            "completed_count": len(completed),
            "total_count": len(self._sessions),
            "last_completed": last.to_dict() if last else None,
        }

    def to_dict(self) -> dict[str, Any]:
        return {
            **self.summary(),
            "active_sessions": [s.to_dict() for s in self.active_sessions()],
            "recent_sessions": [s.to_dict() for s in self.recent_sessions(limit=10)],
        }
