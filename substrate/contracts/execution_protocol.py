"""Execution protocol — canonical contracts for the execution pipeline.

Consolidates ExecutionSpine, TraceRecorder, and FeedbackCapture Protocols.
Import from here for type annotations; implement against the Protocol shapes.
"""

from __future__ import annotations

from substrate.execution.spine import ExecutionSpine  # noqa: F401
from substrate.execution.trace import TraceRecorder  # noqa: F401
from substrate.execution.feedback import FeedbackCapture  # noqa: F401

__all__ = ["ExecutionSpine", "TraceRecorder", "FeedbackCapture"]
