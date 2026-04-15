"""
EALiveRuntime — Conversational state machine for real-time EA interaction.

Manages the full lifecycle of a live founder conversation:
control-phrase interception, intent routing via EA orchestrator,
immediate execution via execution bridge, and live session binding.

Design rules:
- Control phrases intercept BEFORE intent routing — hard constraint.
- Singleton pattern — one runtime per process.
- Best-effort live session management — failures degrade gracefully.
- State transitions are explicit and logged.
"""

from __future__ import annotations

import re
import sys
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Optional


# ─── Logging ─────────────────────────────────────────────────────────────────


def _log(msg: str) -> None:
    print(f"[platform.eos.live_runtime] {msg}", file=sys.stderr)


def _utcnow() -> str:
    return datetime.now(timezone.utc).isoformat()


def _new_id(prefix: str = "lr") -> str:
    return f"{prefix}_{uuid.uuid4().hex[:12]}"


# ─── RuntimeState ────────────────────────────────────────────────────────────


class RuntimeState(str, Enum):
    """Lifecycle state of the live runtime."""

    IDLE = "idle"
    LISTENING = "listening"
    EXECUTING = "executing"
    SPEAKING = "speaking"
    PAUSED = "paused"
    STOPPED = "stopped"


# ─── Control phrase patterns ─────────────────────────────────────────────────

_PAUSE_RE = re.compile(
    r"^(pause|hold on|wait|one moment|hang on|one sec)$",
    re.IGNORECASE,
)
_STOP_RE = re.compile(
    r"^(stop|cancel|abort|quit|end|shut down)$",
    re.IGNORECASE,
)
_RESUME_RE = re.compile(
    r"^(continue|resume|keep going|go ahead|carry on|go on|proceed)$",
    re.IGNORECASE,
)


def _classify_control_phrase(text: str) -> Optional[str]:
    """Classify text as a control phrase.

    Returns "pause", "stop", "resume", or None.
    Matches full string only, case-insensitive.
    """
    stripped = text.strip()
    if _PAUSE_RE.match(stripped):
        return "pause"
    if _STOP_RE.match(stripped):
        return "stop"
    if _RESUME_RE.match(stripped):
        return "resume"
    return None


# ─── LiveRuntimeResult ───────────────────────────────────────────────────────


@dataclass
class LiveRuntimeResult:
    """Outcome of a single live runtime interaction."""

    spoken_text: str
    created_task_ids: list[str] = field(default_factory=list)
    created_pipeline_ids: list[str] = field(default_factory=list)
    executed_actions_summary: dict[str, str] = field(default_factory=dict)
    blocked_items: list[str] = field(default_factory=list)
    live_session_id: Optional[str] = None
    is_control_action: bool = False

    def to_dict(self) -> dict:
        """Serialize to a JSON-safe dict."""
        return {
            "spoken_text": self.spoken_text,
            "created_task_ids": list(self.created_task_ids),
            "created_pipeline_ids": list(self.created_pipeline_ids),
            "executed_actions_summary": dict(self.executed_actions_summary),
            "blocked_items": list(self.blocked_items),
            "live_session_id": self.live_session_id,
            "is_control_action": self.is_control_action,
        }


# ─── EALiveRuntime ───────────────────────────────────────────────────────────


@dataclass
class EALiveRuntime:
    """Singleton conversational state machine for EA live interaction.

    Tracks runtime state, current work items, and the bound live session.
    All founder utterances flow through handle_utterance().
    """

    runtime_id: str = field(default_factory=lambda: _new_id("rt"))
    live_session_id: Optional[str] = None
    state: RuntimeState = RuntimeState.IDLE
    current_task_ids: list[str] = field(default_factory=list)
    current_pipeline_ids: list[str] = field(default_factory=list)
    current_control_request_ids: list[str] = field(default_factory=list)
    last_user_utterance: Optional[str] = None
    last_ea_response: Optional[str] = None
    updated_at: str = field(default_factory=_utcnow)

    # ── singleton ─────────────────────────────────────────────────────────

    _default: Optional["EALiveRuntime"] = None

    @classmethod
    def default(cls) -> "EALiveRuntime":
        """Return the process-level singleton."""
        if cls._default is None:
            cls._default = cls()
        return cls._default

    @classmethod
    def reset_default_for_tests(cls) -> None:
        """Tear down the singleton for test isolation."""
        cls._default = None

    # ── live session management ───────────────────────────────────────────

    def _ensure_live_session(self) -> None:
        """Create or verify the bound live session.

        If no session exists, creates one via discord_hook and starts it.
        If session exists but is terminal, creates a new one.
        """
        if self.live_session_id is not None:
            # Verify it's not terminal
            try:
                from eos_ai.substrate.live_sessions import LiveSessionStore

                existing = LiveSessionStore.default().get(self.live_session_id)
                if existing is not None and not existing.is_terminal():
                    return  # Session still valid
                _log(
                    f"live session {self.live_session_id} is terminal or missing, creating new"
                )
            except Exception as exc:
                _log(f"live session check failed: {exc}")

        # Create new session
        try:
            from eos_ai.platforms.eos.discord_hook import create_ea_live_session
            from eos_ai.substrate.live_sessions import start_live_session

            session_id = create_ea_live_session("EA Live Session", session_type="LOCAL")
            if session_id:
                start_live_session(session_id)
                self.live_session_id = session_id
                _log(f"created and started live session {session_id}")
            else:
                _log("live session creation returned None")
        except Exception as exc:
            _log(f"live session creation failed: {exc}")

    def _attach_work_to_session(
        self,
        task_ids: list[str],
        pipeline_ids: list[str],
    ) -> None:
        """Attach tasks and pipelines to the current live session."""
        if not self.live_session_id:
            return

        try:
            from eos_ai.substrate.live_sessions import (
                attach_pipeline_to_live_session,
                attach_task_to_live_session,
            )

            for tid in task_ids:
                attach_task_to_live_session(self.live_session_id, tid)
            for pid in pipeline_ids:
                attach_pipeline_to_live_session(self.live_session_id, pid)
        except Exception as exc:
            _log(f"attach work to session failed: {exc}")

    # ── streaming bridge integration ─────────────────────────────────────

    def _bind_streaming_bridge(self) -> None:
        """Bind the streaming bridge to the current live session."""
        try:
            from eos_ai.platforms.eos.streaming_bridge import get_streaming_bridge

            bridge = get_streaming_bridge()
            bridge.set_session(self.live_session_id)
        except Exception as exc:
            _log(f"streaming bridge bind failed: {exc}")

    def _stream_state_change(self, message: str) -> None:
        """Emit a streaming event for runtime state transitions."""
        try:
            from eos_ai.platforms.eos.streaming_bridge import (
                StreamEventType,
                stream_event,
            )

            stream_event(
                StreamEventType.INFO,
                message,
                source="live_runtime",
                speak=False,
            )
        except Exception:
            pass

    # ── control handlers ──────────────────────────────────────────────────

    def _handle_pause(self) -> LiveRuntimeResult:
        """Pause the runtime and the bound live session."""
        self.state = RuntimeState.PAUSED
        self.updated_at = _utcnow()

        if self.live_session_id:
            try:
                from eos_ai.substrate.live_sessions import pause_live_session

                pause_live_session(self.live_session_id)
            except Exception as exc:
                _log(f"pause live session failed: {exc}")

        msg = "Paused. Say continue when you're ready."
        self.last_ea_response = msg
        return LiveRuntimeResult(
            spoken_text=msg,
            is_control_action=True,
            live_session_id=self.live_session_id,
        )

    def _handle_stop(self) -> LiveRuntimeResult:
        """Stop the runtime and end the live session."""
        self.state = RuntimeState.STOPPED
        self.updated_at = _utcnow()

        if self.live_session_id:
            try:
                from eos_ai.substrate.live_sessions import end_live_session

                end_live_session(self.live_session_id)
            except Exception as exc:
                _log(f"end live session failed: {exc}")

        msg = "Stopped. Session ended."
        self.last_ea_response = msg
        return LiveRuntimeResult(
            spoken_text=msg,
            is_control_action=True,
            live_session_id=self.live_session_id,
        )

    def _handle_resume(self) -> LiveRuntimeResult:
        """Resume the runtime, the live session, and any paused pipelines."""
        self.state = RuntimeState.LISTENING
        self.updated_at = _utcnow()

        if self.live_session_id:
            try:
                from eos_ai.substrate.live_sessions import resume_live_session

                resume_live_session(self.live_session_id)
            except Exception as exc:
                _log(f"resume live session failed: {exc}")

        # Resume paused pipelines
        try:
            from eos_ai.substrate.task_pipeline import PipelineStatus, PipelineStore

            store = PipelineStore.default()
            paused = store.by_status(PipelineStatus.PAUSED)
            for p in paused:
                if p.pipeline_id in self.current_pipeline_ids:
                    p.status = PipelineStatus.READY
                    p.updated_at = _utcnow()
                    store.put(p)
                    _log(f"resumed pipeline {p.pipeline_id}")
        except Exception as exc:
            _log(f"resume paused pipelines failed: {exc}")

        msg = "Resuming."
        self.last_ea_response = msg
        return LiveRuntimeResult(
            spoken_text=msg,
            is_control_action=True,
            live_session_id=self.live_session_id,
        )

    # ── core utterance handler ────────────────────────────────────────────

    def handle_utterance(
        self,
        text: str,
        *,
        session_id: Optional[str] = None,
        dry_run: bool = False,
    ) -> LiveRuntimeResult:
        """Process a founder utterance through the live runtime.

        Flow:
        1. Classify control phrase — if match, route to handler immediately.
        2. If STOPPED, return stop message.
        3. If PAUSED, return pause message.
        4. Set LISTENING.
        5. Ensure live session.
        6. Route through EA orchestrator.
        7. If tasks/pipelines created, execute immediately.
        8. Track work, attach to session.
        9. Return result.
        """
        self.last_user_utterance = text
        self.updated_at = _utcnow()

        # 1. Control phrase interception — BEFORE anything else
        control = _classify_control_phrase(text)
        if control == "pause":
            return self._handle_pause()
        if control == "stop":
            return self._handle_stop()
        if control == "resume":
            return self._handle_resume()

        # 2. Stopped state
        if self.state == RuntimeState.STOPPED:
            msg = "Session is stopped. Say resume to restart."
            self.last_ea_response = msg
            return LiveRuntimeResult(
                spoken_text=msg,
                live_session_id=self.live_session_id,
            )

        # 3. Paused state
        if self.state == RuntimeState.PAUSED:
            msg = "I'm paused. Say continue to resume, or stop to end."
            self.last_ea_response = msg
            return LiveRuntimeResult(
                spoken_text=msg,
                live_session_id=self.live_session_id,
            )

        # 4. Set LISTENING
        self.state = RuntimeState.LISTENING
        self.updated_at = _utcnow()

        # 5. Ensure live session
        self._ensure_live_session()

        # Bind streaming bridge to the live session
        self._bind_streaming_bridge()

        # 6. Route through EA orchestrator
        from eos_ai.platforms.eos.ea_orchestrator import handle_founder_message

        ea_response = handle_founder_message(text, session_id=session_id)

        created_task_ids = list(ea_response.created_task_ids)
        created_pipeline_ids = list(ea_response.created_pipeline_ids)
        blocked_items = list(ea_response.blocked_items)
        executed_actions_summary: dict[str, str] = {}

        # 7. If work created, execute immediately
        if created_task_ids or created_pipeline_ids:
            self.state = RuntimeState.EXECUTING
            self.updated_at = _utcnow()
            self._stream_state_change(
                f"Executing {len(created_task_ids)} tasks, "
                f"{len(created_pipeline_ids)} pipelines..."
            )

            try:
                from eos_ai.platforms.eos.execution_bridge import (
                    execute_created_work_immediately,
                )

                bridge_result = execute_created_work_immediately(
                    task_ids=created_task_ids,
                    pipeline_ids=created_pipeline_ids,
                    dry_run=dry_run,
                )
                executed_actions_summary = dict(bridge_result.execution_summaries)
            except Exception as exc:
                _log(f"execution bridge failed: {exc}")

        # 8. Track current work
        for tid in created_task_ids:
            if tid not in self.current_task_ids:
                self.current_task_ids.append(tid)
        for pid in created_pipeline_ids:
            if pid not in self.current_pipeline_ids:
                self.current_pipeline_ids.append(pid)

        # 9. Attach to live session
        self._attach_work_to_session(created_task_ids, created_pipeline_ids)

        # 10. Return result
        self.state = RuntimeState.LISTENING
        self.last_ea_response = ea_response.response_text
        self.updated_at = _utcnow()

        return LiveRuntimeResult(
            spoken_text=ea_response.response_text,
            created_task_ids=created_task_ids,
            created_pipeline_ids=created_pipeline_ids,
            executed_actions_summary=executed_actions_summary,
            blocked_items=blocked_items,
            live_session_id=self.live_session_id,
            is_control_action=False,
        )


# ─── Module-level API ────────────────────────────────────────────────────────


def get_live_runtime() -> EALiveRuntime:
    """Return the singleton EALiveRuntime."""
    return EALiveRuntime.default()


def handle_live_user_utterance(
    text: str,
    *,
    session_id: Optional[str] = None,
    dry_run: bool = False,
) -> LiveRuntimeResult:
    """Process a live user utterance through the EA runtime."""
    return EALiveRuntime.default().handle_utterance(
        text, session_id=session_id, dry_run=dry_run
    )


def pause_live_runtime() -> dict:
    """Pause the live runtime. Returns state and message."""
    rt = EALiveRuntime.default()
    result = rt._handle_pause()
    return {"state": rt.state.value, "message": result.spoken_text}


def resume_live_runtime() -> dict:
    """Resume the live runtime. Returns state and message."""
    rt = EALiveRuntime.default()
    result = rt._handle_resume()
    return {"state": rt.state.value, "message": result.spoken_text}


def stop_live_runtime() -> dict:
    """Stop the live runtime. Returns state and message."""
    rt = EALiveRuntime.default()
    result = rt._handle_stop()
    return {"state": rt.state.value, "message": result.spoken_text}


def interrupt_live_runtime(new_text: str) -> LiveRuntimeResult:
    """Interrupt the current activity and handle new text.

    If the runtime is EXECUTING or SPEAKING, transitions to LISTENING first.
    Then processes the new utterance.
    """
    rt = EALiveRuntime.default()
    if rt.state in (RuntimeState.EXECUTING, RuntimeState.SPEAKING):
        rt.state = RuntimeState.LISTENING
        rt.updated_at = _utcnow()
        _log(f"interrupted from {rt.state.value} to LISTENING")

    return rt.handle_utterance(new_text)


def format_live_progress_update(
    *,
    action: str,
    status: str = "in_progress",
    detail: Optional[str] = None,
) -> str:
    """Format a progress update for live display.

    Returns a human-readable progress string.
    """
    parts = [f"[{status}] {action}"]
    if detail:
        parts.append(f"— {detail}")
    return " ".join(parts)


# ─── Exports ─────────────────────────────────────────────────────────────────

__all__ = [
    "RuntimeState",
    "LiveRuntimeResult",
    "EALiveRuntime",
    "get_live_runtime",
    "handle_live_user_utterance",
    "pause_live_runtime",
    "resume_live_runtime",
    "stop_live_runtime",
    "interrupt_live_runtime",
    "format_live_progress_update",
]
