"""Workstation Session Runtime — operator leave/return with full context restore.

Answers: "Can the operator leave and return later?"

Resume context consumes OrchestratorAwarenessRuntime — returning to UMH
restores active projection, active repo, active files, active agents,
active compute, active approvals, active loops. Not merely session metadata.

Composes all 4 continuity levels + C4.0-C4.3 for comprehensive resume.

Campaign 4.4. UMH substrate layer. Instance-agnostic.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any
from uuid import uuid4

logger = logging.getLogger(__name__)


# ── Types ─────────────────────────────────────────────────────────────────


class WorkstationSessionStatus(str, Enum):
    ACTIVE = "active"
    PAUSED = "paused"
    RESUMED = "resumed"
    CLOSED = "closed"


@dataclass
class WorkstationSessionCheckpoint:
    checkpoint_id: str = ""
    session_id: str = ""
    orchestrator_context: dict[str, Any] = field(default_factory=dict)
    active_loops: list[dict[str, Any]] = field(default_factory=list)
    pending_approvals: int = 0
    coherence_score: float = 0.0
    situation_summary: dict[str, Any] = field(default_factory=dict)
    attention_items: list[dict[str, Any]] = field(default_factory=list)
    timestamp: float = 0.0

    def __post_init__(self) -> None:
        if not self.checkpoint_id:
            self.checkpoint_id = f"chk-{uuid4().hex[:8]}"
        if self.timestamp == 0.0:
            self.timestamp = time.time()

    def to_dict(self) -> dict[str, Any]:
        return {
            "checkpoint_id": self.checkpoint_id,
            "session_id": self.session_id,
            "orchestrator_context": self.orchestrator_context,
            "active_loops": self.active_loops,
            "pending_approvals": self.pending_approvals,
            "coherence_score": self.coherence_score,
            "situation_summary": self.situation_summary,
            "attention_items": self.attention_items,
            "timestamp": self.timestamp,
        }


@dataclass
class WorkstationSessionResume:
    session_id: str = ""
    previous_checkpoint: dict[str, Any] = field(default_factory=dict)
    elapsed_since_last: float = 0.0
    orchestrator_context: dict[str, Any] = field(default_factory=dict)
    changes_since: list[str] = field(default_factory=list)
    active_loops: list[dict[str, Any]] = field(default_factory=list)
    pending_decisions: int = 0
    coherence_score: float = 0.0
    attention: list[dict[str, Any]] = field(default_factory=list)
    recommendations: list[dict[str, Any]] = field(default_factory=list)
    next_actions: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "session_id": self.session_id,
            "previous_checkpoint": self.previous_checkpoint,
            "elapsed_since_last": self.elapsed_since_last,
            "orchestrator_context": self.orchestrator_context,
            "changes_since": self.changes_since,
            "active_loops": self.active_loops,
            "pending_decisions": self.pending_decisions,
            "coherence_score": self.coherence_score,
            "attention": self.attention,
            "recommendations": self.recommendations,
            "next_actions": self.next_actions,
        }


@dataclass
class WorkstationSession:
    session_id: str = ""
    status: WorkstationSessionStatus = WorkstationSessionStatus.ACTIVE
    started_at: float = 0.0
    last_checkpoint_at: float = 0.0
    checkpoints: list[WorkstationSessionCheckpoint] = field(default_factory=list)
    resume_count: int = 0

    def __post_init__(self) -> None:
        if not self.session_id:
            self.session_id = f"wsess-{uuid4().hex[:8]}"
        if self.started_at == 0.0:
            self.started_at = time.time()

    def to_dict(self) -> dict[str, Any]:
        return {
            "session_id": self.session_id,
            "status": self.status.value,
            "started_at": self.started_at,
            "last_checkpoint_at": self.last_checkpoint_at,
            "checkpoints": [c.to_dict() for c in self.checkpoints],
            "resume_count": self.resume_count,
        }


# ── Helpers ───────────────────────────────────────────────────────────────


def _safe_call(obj: Any, method: str, *args: Any, **kwargs: Any) -> Any:
    if obj is None:
        return None
    fn = getattr(obj, method, None)
    if fn is None:
        return None
    try:
        return fn(*args, **kwargs)
    except Exception as exc:
        logger.debug("Session: %s.%s() failed: %s", type(obj).__name__, method, exc)
        return None


def _safe_dict(obj: Any, method: str, *args: Any, **kwargs: Any) -> dict[str, Any]:
    result = _safe_call(obj, method, *args, **kwargs)
    if isinstance(result, dict):
        return result
    if result is not None and hasattr(result, "to_dict"):
        try:
            return result.to_dict()
        except Exception:
            pass
    return {}


def _safe_list(obj: Any, method: str, *args: Any, **kwargs: Any) -> list[Any]:
    result = _safe_call(obj, method, *args, **kwargs)
    if isinstance(result, list):
        return [
            item.to_dict() if hasattr(item, "to_dict") else
            (item if isinstance(item, dict) else {"value": str(item)})
            for item in result
        ]
    return []


def _safe_float(obj: Any, method: str, *args: Any, **kwargs: Any) -> float:
    result = _safe_call(obj, method, *args, **kwargs)
    if isinstance(result, (int, float)):
        return float(result)
    return 0.0


# ── Runtime ───────────────────────────────────────────────────────────────


class WorkstationSessionRuntime:
    """Operator session lifecycle with full context checkpointing and resume.

    Composes 4 continuity levels + C4.0-C4.3 to produce a comprehensive
    resume context when the operator returns.
    """

    def __init__(
        self,
        # 4 continuity levels
        continuity_runtime: Any | None = None,
        continuity_engine: Any | None = None,
        # Operator subsystems
        snapshot_runtime: Any | None = None,
        attention_engine: Any | None = None,
        # C4.0-C4.3
        awareness: Any | None = None,
        operating_loop: Any | None = None,
        approval_runtime: Any | None = None,
        coherence_runtime: Any | None = None,
    ) -> None:
        self._continuity_rt = continuity_runtime
        self._continuity_eng = continuity_engine
        self._snapshot = snapshot_runtime
        self._attention = attention_engine
        self._awareness = awareness
        self._loop_rt = operating_loop
        self._approval_rt = approval_runtime
        self._coherence_rt = coherence_runtime

        self._sessions: dict[str, WorkstationSession] = {}
        self._active_session_id: str = ""

    # ── Lifecycle ─────────────────────────────────────────────────────

    def start_session(self) -> WorkstationSession:
        session = WorkstationSession()
        self._sessions[session.session_id] = session
        self._active_session_id = session.session_id
        return session

    def checkpoint(self, session_id: str = "") -> WorkstationSessionCheckpoint:
        sid = session_id or self._active_session_id
        session = self._sessions.get(sid)
        if session is None:
            return WorkstationSessionCheckpoint(session_id=sid)

        # Capture full orchestrator context
        orch_ctx = _safe_dict(self._awareness, "context")

        # Active loops from C4.1
        loops = _safe_list(self._loop_rt, "active_loops")

        # Pending approvals from C4.2
        pending = _safe_list(self._approval_rt, "pending")
        pending_count = len(pending)

        # Coherence from C4.3
        coh_score = _safe_float(self._coherence_rt, "coherence_score")

        # Operator state
        situation = _safe_dict(self._snapshot, "situation")
        attention = _safe_list(self._attention, "top", 5)

        chk = WorkstationSessionCheckpoint(
            session_id=sid,
            orchestrator_context=orch_ctx,
            active_loops=loops,
            pending_approvals=pending_count,
            coherence_score=coh_score,
            situation_summary=situation,
            attention_items=attention,
        )
        session.checkpoints.append(chk)
        session.last_checkpoint_at = chk.timestamp

        # Also record in organism-level continuity
        _safe_call(self._continuity_rt, "capture_snapshot")

        return chk

    def pause(self, session_id: str = "") -> WorkstationSession:
        sid = session_id or self._active_session_id
        session = self._sessions.get(sid)
        if session is None:
            s = WorkstationSession(session_id=sid)
            s.status = WorkstationSessionStatus.PAUSED
            return s

        # Auto-checkpoint before pause
        if not session.checkpoints or (time.time() - session.last_checkpoint_at > 60):
            self.checkpoint(sid)

        session.status = WorkstationSessionStatus.PAUSED
        _safe_call(self._continuity_rt, "record_departure")
        return session

    def resume(self, session_id: str = "") -> WorkstationSessionResume:
        sid = session_id or self._active_session_id
        session = self._sessions.get(sid)
        if session is None:
            return WorkstationSessionResume(session_id=sid, next_actions=["No session found"])

        session.status = WorkstationSessionStatus.RESUMED
        session.resume_count += 1
        self._active_session_id = sid

        # 1. Last checkpoint
        last_chk = session.checkpoints[-1] if session.checkpoints else None
        elapsed = time.time() - last_chk.timestamp if last_chk else 0.0

        # 2. Organism-level resume
        organism_resume = _safe_dict(self._continuity_rt, "generate_resume")

        # 3. Workstation state transition
        _safe_call(self._continuity_eng, "resume_from_absence")

        # 4. Full OrchestratorContext (restores everything)
        orch_ctx = _safe_dict(self._awareness, "context")

        # 5. Operator snapshot
        snapshot = _safe_dict(self._snapshot, "snapshot")

        # 6. Active loops from C4.1
        loops = _safe_list(self._loop_rt, "active_loops")

        # 7. Pending approvals from C4.2
        pending = _safe_list(self._approval_rt, "pending")
        pending_count = len(pending)

        # 8. Coherence from C4.3
        coh_score = _safe_float(self._coherence_rt, "coherence_score")

        # 9. Attention
        attention = _safe_list(self._attention, "top", 5)

        # 10. Recommendations
        recommendations: list[dict[str, Any]] = []
        if orch_ctx:
            recommendations = orch_ctx.get("recommendations", [])
            if not isinstance(recommendations, list):
                recommendations = []

        # 11. Changes since last checkpoint
        changes: list[str] = []
        if organism_resume:
            changes = organism_resume.get("changes", [])
            if not isinstance(changes, list):
                changes = []

        # 12. Derive next_actions
        next_actions = self._derive_next_actions(loops, pending, attention)

        return WorkstationSessionResume(
            session_id=sid,
            previous_checkpoint=last_chk.to_dict() if last_chk else {},
            elapsed_since_last=round(elapsed, 2),
            orchestrator_context=orch_ctx,
            changes_since=changes,
            active_loops=loops,
            pending_decisions=pending_count,
            coherence_score=coh_score,
            attention=attention,
            recommendations=recommendations,
            next_actions=next_actions,
        )

    def close(self, session_id: str = "") -> WorkstationSession:
        sid = session_id or self._active_session_id
        session = self._sessions.get(sid)
        if session is None:
            s = WorkstationSession(session_id=sid)
            s.status = WorkstationSessionStatus.CLOSED
            return s

        session.status = WorkstationSessionStatus.CLOSED
        if self._active_session_id == sid:
            self._active_session_id = ""
        return session

    # ── Queries ───────────────────────────────────────────────────────

    def active_session(self) -> WorkstationSession | None:
        if not self._active_session_id:
            return None
        session = self._sessions.get(self._active_session_id)
        if session and session.status in (
            WorkstationSessionStatus.ACTIVE,
            WorkstationSessionStatus.RESUMED,
        ):
            return session
        return None

    def session_history(self, limit: int = 20) -> list[WorkstationSession]:
        sessions = sorted(
            self._sessions.values(),
            key=lambda s: s.started_at,
            reverse=True,
        )
        return sessions[:limit]

    def last_checkpoint(self, session_id: str = "") -> WorkstationSessionCheckpoint | None:
        sid = session_id or self._active_session_id
        session = self._sessions.get(sid)
        if session and session.checkpoints:
            return session.checkpoints[-1]
        return None

    # ── Private ───────────────────────────────────────────────────────

    def _derive_next_actions(
        self,
        loops: list[Any],
        pending: list[Any],
        attention: list[Any],
    ) -> list[str]:
        actions: list[str] = []

        # Blocked loops need attention
        for loop in loops:
            if isinstance(loop, dict):
                stage = loop.get("current_stage", "")
                if stage in ("approve", "review"):
                    text = loop.get("intent_text", "loop")
                    actions.append(f"Review/approve: {text[:60]}")

        # Pending approvals
        if pending:
            actions.append(f"{len(pending)} approval(s) waiting")

        # High-urgency attention items
        for item in attention[:3]:
            if isinstance(item, dict):
                cat = item.get("category", "item")
                actions.append(f"Attention: {cat}")

        if not actions:
            actions.append("No immediate actions — system stable")

        return actions
