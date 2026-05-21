"""Live runtime loop — session-aware orchestration for continuous interaction.

Maintains an active session across multiple lifecycle invocations.
Accepts streaming inputs (text now, voice later), routes them through
the input router, and delegates to run_lifecycle.

Design rules:
- NO adapter imports — transport-agnostic
- NO IO — pure orchestration wrapper
- NO LLM calls — those happen inside lifecycle executors
- State flows through state_store, not internal fields
- Every public method returns a structured dict
"""

from __future__ import annotations

import logging
import threading
import uuid
from datetime import datetime, timezone
from typing import Any

from umh.adapters.registry import AdapterRegistry
from umh.runtime_loop.context import RuntimeContext
from umh.runtime_loop.input_router import InputEvent, RoutedInput, route_input
from umh.runtime_loop.lifecycle import run_lifecycle
from umh.substrate.runtime_state_store import RuntimeStateStore

logger = logging.getLogger(__name__)


def _utcnow() -> str:
    return datetime.now(timezone.utc).isoformat()


# ── Per-session runtime cache ───────────────────────────────────────────
# One LiveRuntime per session_id, lazily created. Thread-safe.

_runtime_cache: dict[str, LiveRuntime] = {}
_cache_lock = threading.Lock()
_shared_state_store: RuntimeStateStore | None = None
_shared_adapter_registry: AdapterRegistry | None = None


def get_or_create_runtime(session_id: str) -> LiveRuntime:
    """Return a LiveRuntime for the given session, creating one if needed.

    Uses shared RuntimeStateStore and AdapterRegistry singletons.
    The returned runtime is already adopted (active) for the session.
    """
    with _cache_lock:
        rt = _runtime_cache.get(session_id)
        if rt and rt.is_active:
            return rt

    global _shared_state_store, _shared_adapter_registry
    if _shared_state_store is None:
        _shared_state_store = RuntimeStateStore()
    if _shared_adapter_registry is None:
        from umh.protocols.adapters import build_default_registry

        _shared_adapter_registry = build_default_registry()

    rt = LiveRuntime(
        state_store=_shared_state_store,
        adapter_registry=_shared_adapter_registry,
    )
    rt.adopt_session(session_id)

    with _cache_lock:
        _runtime_cache[session_id] = rt

    return rt


def evict_runtime(session_id: str) -> None:
    """Remove a cached runtime for a closed session."""
    with _cache_lock:
        _runtime_cache.pop(session_id, None)


class LiveRuntime:
    """Session-aware runtime loop for continuous interaction.

    Lifecycle:
        1. start_session(context)  → open_day lifecycle
        2. handle_input(event)     → action lifecycle (repeatable)
        3. end_session()           → close_day lifecycle

    The runtime maintains session identity and active state.
    All execution delegates to run_lifecycle.

    Args:
        state_store:      Mutable runtime state store.
        adapter_registry: AdapterRegistry with registered adapters.
    """

    def __init__(
        self,
        state_store: RuntimeStateStore,
        adapter_registry: AdapterRegistry,
    ) -> None:
        self._state_store = state_store
        self._registry = adapter_registry
        self._session_id: str = ""
        self._active: bool = False
        self._last_activity_ts: str = ""

    # ── Read-only properties ─────────────────────────────────────────

    @property
    def session_id(self) -> str:
        """Current session identifier. Empty when no session is active."""
        return self._session_id

    @property
    def is_active(self) -> bool:
        """Whether a session is currently active."""
        return self._active

    @property
    def last_activity_ts(self) -> str:
        """ISO-8601 timestamp of the last activity. Empty before first activity."""
        return self._last_activity_ts

    # ── Context builder ──────────────────────────────────────────────

    def _build_context(
        self,
        transport: str = "local",
        trigger: str = "manual",
        profile_id: str | None = None,
        intent_text: str = "",
    ) -> RuntimeContext:
        """Build a RuntimeContext bound to the current session."""
        prev = None
        try:
            from umh.runtime_loop.lifecycle_behaviors import get_resume_context

            ctx = get_resume_context(self._session_id)
            if ctx:
                prev = ctx.get("previous_session")
        except Exception:
            pass

        return RuntimeContext(
            runtime_session_id=self._session_id,
            transport=transport,
            timestamp=_utcnow(),
            correlation_id=f"cor_{uuid.uuid4().hex[:12]}",
            requested_profile_id=profile_id,
            trigger=trigger,
            intent_text=intent_text,
            previous_session=prev,
        )

    # ── Session lifecycle ────────────────────────────────────────────

    def adopt_session(self, session_id: str) -> None:
        """Bind this runtime to an existing session from SessionRegistry.

        Unlike start_session(), this does NOT run open_day — the session
        was already opened externally. It just makes handle_input() available.
        """
        if self._active and self._session_id != session_id:
            raise RuntimeError(
                f"Runtime already bound to {self._session_id}. "
                f"Cannot adopt {session_id}."
            )
        self._session_id = session_id
        self._active = True
        self._last_activity_ts = _utcnow()
        logger.info("LiveRuntime: adopted session %s", session_id)

    def start_session(
        self,
        *,
        transport: str = "local",
        profile_id: str | None = None,
        trigger: str = "session_start",
    ) -> dict[str, Any]:
        """Start a new session and execute the open_day lifecycle.

        Args:
            transport:  Origin channel (discord, local, voice).
            profile_id: Optional profile to activate.
            trigger:    What initiated this session.

        Returns:
            Structured dict with lifecycle result and session metadata.

        Raises:
            RuntimeError: If a session is already active.
        """
        if self._active:
            raise RuntimeError(
                f"Session already active: {self._session_id}. "
                f"Call end_session() before starting a new one."
            )

        self._session_id = f"live_{uuid.uuid4().hex[:12]}"
        self._active = True
        self._last_activity_ts = _utcnow()

        logger.info(
            "LiveRuntime: starting session %s via %s",
            self._session_id,
            transport,
        )

        context = self._build_context(
            transport=transport,
            trigger=trigger,
            profile_id=profile_id,
        )

        result = run_lifecycle(self._state_store, self._registry, context, "open_day")

        return {
            "session_id": self._session_id,
            "request_type": "open_day",
            "lifecycle_result": result,
            "started_at": self._last_activity_ts,
        }

    def handle_input(self, event: InputEvent) -> dict[str, Any]:
        """Handle an input event within the active session.

        Routes the event through the input router, then delegates to
        run_lifecycle with the appropriate request type.

        Args:
            event: Normalized input from any transport.

        Returns:
            Structured dict with lifecycle result and routing metadata.

        Raises:
            RuntimeError: If no session is active.
        """
        if not self._active:
            raise RuntimeError("No active session. Call start_session() first.")

        self._last_activity_ts = _utcnow()

        routed: RoutedInput = route_input(event)

        logger.info(
            "LiveRuntime: input routed as %s in session %s",
            routed.request_type,
            self._session_id,
        )

        context = self._build_context(
            transport=routed.transport,
            trigger="input",
            intent_text=routed.intent_text,
        )

        result = run_lifecycle(
            self._state_store,
            self._registry,
            context,
            routed.request_type,
        )

        return {
            "session_id": self._session_id,
            "request_type": routed.request_type,
            "intent_text": routed.intent_text,
            "lifecycle_result": result,
            "handled_at": self._last_activity_ts,
        }

    def end_session(self) -> dict[str, Any]:
        """End the active session and execute the close_day lifecycle.

        Returns:
            Structured dict with lifecycle result and session metadata.

        Raises:
            RuntimeError: If no session is active.
        """
        if not self._active:
            raise RuntimeError("No active session. Call start_session() first.")

        logger.info(
            "LiveRuntime: ending session %s",
            self._session_id,
        )

        ended_at = _utcnow()
        context = self._build_context(trigger="session_end")

        result = run_lifecycle(self._state_store, self._registry, context, "close_day")

        session_id = self._session_id
        self._active = False
        self._last_activity_ts = ended_at

        return {
            "session_id": session_id,
            "request_type": "close_day",
            "lifecycle_result": result,
            "ended_at": ended_at,
        }
