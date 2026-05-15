"""Execution trace for EOS request lifecycle.

Collects metadata as a request flows through:
mode routing → target policy → workflow delegation → workflow execution →
resource guard → context lifecycle → model router → response.

Thread-safe. No external dependencies beyond stdlib.
"""

from __future__ import annotations

import collections
import sys
import threading
from contextlib import contextmanager
from datetime import datetime
from typing import Any, Generator, Optional
from uuid import uuid4


# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------


def _log(msg: str) -> None:
    """Print to stderr with module prefix."""
    print(f"[substrate.execution_trace] {msg}", file=sys.stderr, flush=True)


# ---------------------------------------------------------------------------
# Schema definition
# ---------------------------------------------------------------------------

_TRACE_KEYS: set[str] = {
    "trace_id",
    "source",
    "mode",
    "target_initial",
    "target_final",
    "session_name",
    "workflow_intent",
    "workflow_kind",
    "workflow_allowed",
    "workflow_executed",
    "workflow_handler",
    "workload_class",
    "resource_pressure",
    "resource_guard_allowed",
    "resource_guard_reason",
    "context_pressure_score",
    "context_checkpoint_used",
    "context_restore_used",
    "execution_path",
    "provider",
    "model",
    "latency_ms",
    "result",
    "timestamp",
}


# ---------------------------------------------------------------------------
# Trace factory
# ---------------------------------------------------------------------------


def new_trace(source: str, mode: str, session_name: str, **kwargs: Any) -> dict:
    """Create a new trace dict with defaults for the full request lifecycle.

    Args:
        source: Origin channel — "discord_text", "discord_voice", etc.
        mode: Routing mode — "builder", "product", "unknown".
        session_name: Active session name at request time.
        **kwargs: Override any default trace field.

    Returns:
        Trace dict ready to be passed through pipeline stages.
    """
    trace: dict[str, Any] = {
        "trace_id": str(uuid4()),
        "source": source,
        "mode": mode,
        "target_initial": None,
        "target_final": None,
        "session_name": session_name,
        "workflow_intent": None,
        "workflow_kind": None,
        "workflow_allowed": None,
        "workflow_executed": None,
        "workflow_handler": None,
        "workload_class": None,
        "resource_pressure": None,
        "resource_guard_allowed": None,
        "resource_guard_reason": None,
        "context_pressure_score": None,
        "context_checkpoint_used": False,
        "context_restore_used": False,
        "execution_path": None,
        "provider": None,
        "model": None,
        "latency_ms": None,
        "result": None,
        "timestamp": datetime.utcnow().isoformat() + "Z",
    }
    # Apply caller overrides (only known keys)
    for k, v in kwargs.items():
        if k in _TRACE_KEYS:
            trace[k] = v
    return trace


# ---------------------------------------------------------------------------
# Trace updater
# ---------------------------------------------------------------------------


def update_trace(trace: dict, **fields: Any) -> dict:
    """Merge fields into an existing trace dict.

    Unknown keys are silently ignored — only schema-defined keys are set.

    Args:
        trace: The trace dict to update.
        **fields: Key-value pairs to merge.

    Returns:
        The same trace dict (mutated in place).
    """
    for k, v in fields.items():
        if k in _TRACE_KEYS:
            trace[k] = v
    return trace


# ---------------------------------------------------------------------------
# Trace finalizer
# ---------------------------------------------------------------------------


def finalize_trace(
    trace: dict,
    provider: Optional[str] = None,
    model: Optional[str] = None,
    latency_ms: Optional[int] = None,
    result: Optional[str] = None,
) -> dict:
    """Finalize a trace after the request lifecycle completes.

    Sets provider/model/result/latency and stamps ``finalized_at``.

    Args:
        trace: The trace dict to finalize.
        provider: LLM provider used ("anthropic", "gemini", "ollama", …).
        model: Model identifier.
        latency_ms: End-to-end latency in milliseconds.
        result: Outcome — "success", "fallback", "blocked", "deferred".

    Returns:
        The same trace dict (mutated in place).
    """
    if provider is not None:
        trace["provider"] = provider
    if model is not None:
        trace["model"] = model
    if latency_ms is not None:
        trace["latency_ms"] = latency_ms
    if result is not None:
        trace["result"] = result
    trace["finalized_at"] = datetime.utcnow().isoformat() + "Z"
    return trace


# ---------------------------------------------------------------------------
# Compact formatter
# ---------------------------------------------------------------------------


def format_trace_compact(trace: dict) -> str:
    """Return a one-line human-readable summary of a trace.

    Format:
        [trace_id[:8]] mode→target | exec_path | provider/model | result | latency_ms
    """
    tid = trace.get("trace_id", "????????")[:8]
    mode = trace.get("mode", "?")
    target = trace.get("target_final") or trace.get("target_initial") or "?"
    path = trace.get("execution_path") or "?"
    provider = trace.get("provider") or "?"
    model = trace.get("model") or "?"
    result = trace.get("result") or "?"
    latency = trace.get("latency_ms")
    latency_str = f"{latency}ms" if latency is not None else "?ms"
    return f"[{tid}] {mode}→{target} | {path} | {provider}/{model} | {result} | {latency_str}"


# ---------------------------------------------------------------------------
# Bounded history ring
# ---------------------------------------------------------------------------


class _TraceHistory:
    """Thread-safe in-memory ring buffer of finalized traces."""

    def __init__(self, maxlen: int = 200) -> None:
        self._buf: collections.deque[dict] = collections.deque(maxlen=maxlen)
        self._lock = threading.Lock()

    def record(self, trace: dict) -> None:
        """Append a finalized trace to the ring buffer."""
        with self._lock:
            self._buf.append(trace)

    def latest(self, limit: int = 20) -> list[dict]:
        """Return the most recent *limit* traces (newest last)."""
        with self._lock:
            items = list(self._buf)
        return items[-limit:]

    def by_mode(self, mode: str, limit: int = 20) -> list[dict]:
        """Return recent traces filtered by mode."""
        with self._lock:
            items = [t for t in self._buf if t.get("mode") == mode]
        return items[-limit:]

    def by_session(self, session_name: str, limit: int = 20) -> list[dict]:
        """Return recent traces filtered by session_name."""
        with self._lock:
            items = [t for t in self._buf if t.get("session_name") == session_name]
        return items[-limit:]

    def by_provider(self, provider: str, limit: int = 20) -> list[dict]:
        """Return recent traces filtered by provider."""
        with self._lock:
            items = [t for t in self._buf if t.get("provider") == provider]
        return items[-limit:]

    def by_execution_path(self, path: str, limit: int = 20) -> list[dict]:
        """Return recent traces filtered by execution_path."""
        with self._lock:
            items = [t for t in self._buf if t.get("execution_path") == path]
        return items[-limit:]

    def clear(self) -> None:
        """Empty the buffer."""
        with self._lock:
            self._buf.clear()


_history_singleton: Optional[_TraceHistory] = None
_history_lock = threading.Lock()


def get_trace_history() -> _TraceHistory:
    """Return the module-level TraceHistory singleton (created on first call)."""
    global _history_singleton
    if _history_singleton is None:
        with _history_lock:
            if _history_singleton is None:
                _history_singleton = _TraceHistory()
    return _history_singleton


# ---------------------------------------------------------------------------
# Thread-local trace context
# ---------------------------------------------------------------------------

_thread_local = threading.local()


def set_current_trace(trace: dict) -> None:
    """Store a trace in thread-local storage."""
    _thread_local.current_trace = trace


def get_current_trace() -> Optional[dict]:
    """Retrieve the current thread-local trace, or None."""
    return getattr(_thread_local, "current_trace", None)


def clear_current_trace() -> None:
    """Clear the thread-local trace."""
    _thread_local.current_trace = None


@contextmanager
def trace_context(trace: dict) -> Generator[dict, None, None]:
    """Context manager that sets the thread-local trace and clears on exit.

    Usage::

        with trace_context(my_trace) as t:
            # t is the trace dict, also accessible via get_current_trace()
            ...
    """
    set_current_trace(trace)
    try:
        yield trace
    finally:
        clear_current_trace()
