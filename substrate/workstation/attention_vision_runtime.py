"""Attention Vision Runtime — Campaign 21.3.

Deterministic visual attention ranking. Scans screen state for error
signals (failing tests, stack traces, build failures) and merges them
with existing attention items from the organism.

Composes:
  - ScreenAwarenessRuntime (C21.0) — current screen state
  - AttentionAggregationRuntime (C18.2) — existing attention queue
  - EnvironmentAwarenessRuntime (C21.1) — active surfaces

100% deterministic — regex/keyword matching, no LLM calls.

C21 substrate workstation subsystem. Instance-agnostic.
"""

from __future__ import annotations

import logging
import re
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

logger = logging.getLogger(__name__)


# ── Detection patterns (compiled once) ────────────────────────────────


_ERROR_PATTERNS = re.compile(
    r"\b(error|failed|failure|exception|traceback|fatal|panic)\b",
    re.IGNORECASE,
)

_TEST_FAIL_PATTERNS = re.compile(
    r"(\b(FAILED|FAIL|failures?|errors?)\s*[=:]\s*\d+|\d+\s+(FAILED|FAIL|failures?|errors?)\b)",
    re.IGNORECASE,
)

_STACK_TRACE_PATTERNS = re.compile(
    r"(Traceback \(most recent|File \".*\", line \d+"
    r"|at .*\.(?:py|js|ts):\d+)",
    re.IGNORECASE,
)

_BUILD_FAIL_PATTERNS = re.compile(
    r"\b(build failed|compilation error|syntax error"
    r"|cannot find module)\b",
    re.IGNORECASE,
)

_LINT_PATTERNS = re.compile(
    r"\b(warning|warn|lint|eslint|ruff|mypy)\b",
    re.IGNORECASE,
)

_BLOCKED_PATTERNS = re.compile(
    r"\b(blocked|stuck|waiting for approval|pending approval)\b",
    re.IGNORECASE,
)


# ── Signal → severity mapping ─────────────────────────────────────────

_SIGNAL_SEVERITY: dict[str, str] = {
    "error_banner": "critical",
    "failing_test": "critical",
    "stack_trace": "critical",
    "build_failure": "critical",
    "blocked_execution": "critical",
    "lint_warning": "warning",
    "notification": "info",
}


# ── Types ─────────────────────────────────────────────────────────────


class VisualSignalType(str, Enum):
    ERROR_BANNER = "error_banner"
    FAILING_TEST = "failing_test"
    STACK_TRACE = "stack_trace"
    BUILD_FAILURE = "build_failure"
    BLOCKED_EXECUTION = "blocked_execution"
    LINT_WARNING = "lint_warning"
    NOTIFICATION = "notification"


class VisualSignalSeverity(str, Enum):
    CRITICAL = "critical"
    WARNING = "warning"
    INFO = "info"


@dataclass
class VisualAttentionSignal:
    signal_type: str = VisualSignalType.NOTIFICATION.value
    severity: str = VisualSignalSeverity.INFO.value
    source_surface: str = ""
    description: str = ""
    detected_from: str = ""
    confidence: float = 0.0
    detected_at: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "signal_type": self.signal_type,
            "severity": self.severity,
            "source_surface": self.source_surface,
            "description": self.description,
            "detected_from": self.detected_from,
            "confidence": self.confidence,
            "detected_at": self.detected_at,
        }


@dataclass
class AttentionVisionSnapshot:
    visual_signals: list[dict[str, Any]] = field(default_factory=list)
    critical_count: int = 0
    warning_count: int = 0
    info_count: int = 0
    attention_items: list[dict[str, Any]] = field(default_factory=list)
    total_attention_count: int = 0
    generated_at: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "visual_signals": self.visual_signals,
            "critical_count": self.critical_count,
            "warning_count": self.warning_count,
            "info_count": self.info_count,
            "attention_items": self.attention_items,
            "total_attention_count": self.total_attention_count,
            "generated_at": self.generated_at,
        }


# ── Pattern checkers ──────────────────────────────────────────────────

_CHECKERS: list[tuple[re.Pattern[str], str, float]] = [
    (_STACK_TRACE_PATTERNS, VisualSignalType.STACK_TRACE.value, 0.9),
    (_TEST_FAIL_PATTERNS, VisualSignalType.FAILING_TEST.value, 0.9),
    (_BUILD_FAIL_PATTERNS, VisualSignalType.BUILD_FAILURE.value, 0.9),
    (_BLOCKED_PATTERNS, VisualSignalType.BLOCKED_EXECUTION.value, 0.8),
    (_ERROR_PATTERNS, VisualSignalType.ERROR_BANNER.value, 0.7),
    (_LINT_PATTERNS, VisualSignalType.LINT_WARNING.value, 0.7),
]


# ── Runtime ───────────────────────────────────────────────────────────


class AttentionVisionRuntime:
    """Visual attention ranking — deterministic screen-signal detection."""

    def __init__(
        self,
        screen_awareness_runtime: Any | None = None,
        attention_aggregation_runtime: Any | None = None,
        environment_awareness_runtime: Any | None = None,
    ) -> None:
        self._screen_awareness_runtime = screen_awareness_runtime
        self._attention_aggregation_runtime = attention_aggregation_runtime
        self._environment_awareness_runtime = environment_awareness_runtime

    # ── Lazy accessors ────────────────────────────────────────────

    @property
    def screen_awareness_runtime(self) -> Any | None:
        if self._screen_awareness_runtime is None:
            try:
                from substrate.workstation.screen_awareness_runtime import (
                    ScreenAwarenessRuntime,
                )

                self._screen_awareness_runtime = ScreenAwarenessRuntime()
            except Exception:
                logger.debug("ScreenAwarenessRuntime unavailable")
        return self._screen_awareness_runtime

    @property
    def attention_aggregation_runtime(self) -> Any | None:
        if self._attention_aggregation_runtime is None:
            try:
                from substrate.workstation.attention_aggregation_runtime import (
                    AttentionAggregationRuntime,
                )

                self._attention_aggregation_runtime = AttentionAggregationRuntime()
            except Exception:
                logger.debug("AttentionAggregationRuntime unavailable")
        return self._attention_aggregation_runtime

    @property
    def environment_awareness_runtime(self) -> Any | None:
        if self._environment_awareness_runtime is None:
            try:
                from substrate.workstation.environment_awareness_runtime import (
                    EnvironmentAwarenessRuntime,
                )

                self._environment_awareness_runtime = EnvironmentAwarenessRuntime()
            except Exception:
                logger.debug("EnvironmentAwarenessRuntime unavailable")
        return self._environment_awareness_runtime

    # ── Detection ─────────────────────────────────────────────────

    def _scan_text(
        self,
        text: str,
        source_surface: str,
    ) -> list[VisualAttentionSignal]:
        """Match *text* against all compiled patterns."""
        if not text:
            return []
        signals: list[VisualAttentionSignal] = []
        seen_types: set[str] = set()
        now = time.time()
        for pattern, signal_type, confidence in _CHECKERS:
            if signal_type in seen_types:
                continue
            if pattern.search(text):
                seen_types.add(signal_type)
                severity = _SIGNAL_SEVERITY.get(
                    signal_type,
                    VisualSignalSeverity.INFO.value,
                )
                signals.append(
                    VisualAttentionSignal(
                        signal_type=signal_type,
                        severity=severity,
                        source_surface=source_surface,
                        description=f"{signal_type} detected",
                        detected_from=text[:200],
                        confidence=confidence,
                        detected_at=now,
                    ),
                )
        return signals

    def detect_visual_signals(self) -> list[VisualAttentionSignal]:
        """Scan current screen state for error/warning signals."""
        rt = self.screen_awareness_runtime
        if rt is None:
            return []
        try:
            screen = rt.current_screen()
        except Exception:
            logger.debug("Failed to get current screen for signal detection")
            return []
        if not screen:
            return []

        surface = screen.get("device_id", "unknown")
        signals: list[VisualAttentionSignal] = []

        focused = screen.get("focused_application", {})
        if isinstance(focused, dict):
            title = focused.get("window_title", "")
            signals.extend(self._scan_text(title, surface))

        for win in screen.get("active_windows", []):
            if isinstance(win, dict):
                title = win.get("title", "")
                signals.extend(self._scan_text(title, surface))

        file_ctx = screen.get("file_context", {})
        if isinstance(file_ctx, dict):
            fp = file_ctx.get("file_path", "")
            signals.extend(self._scan_text(fp, surface))

        seen: set[str] = set()
        deduped: list[VisualAttentionSignal] = []
        for sig in signals:
            key = f"{sig.signal_type}:{sig.detected_from[:80]}"
            if key not in seen:
                seen.add(key)
                deduped.append(sig)
        return deduped

    def critical_signals(self) -> list[VisualAttentionSignal]:
        """Return only CRITICAL visual signals."""
        return [
            s
            for s in self.detect_visual_signals()
            if s.severity == VisualSignalSeverity.CRITICAL.value
        ]

    def warning_signals(self) -> list[VisualAttentionSignal]:
        """Return only WARNING visual signals."""
        return [
            s
            for s in self.detect_visual_signals()
            if s.severity == VisualSignalSeverity.WARNING.value
        ]

    # ── Merged attention ──────────────────────────────────────────

    def _visual_to_attention_item(
        self,
        sig: VisualAttentionSignal,
    ) -> dict[str, Any]:
        """Convert a visual signal into the normalised attention format."""
        severity_rank = {"critical": 0, "warning": 1, "info": 2}
        return {
            "priority": severity_rank.get(sig.severity, 2),
            "category": "visual",
            "severity": sig.severity,
            "title": sig.description,
            "description": sig.detected_from[:200],
            "action_hint": "investigate",
            "source_id": sig.signal_type,
            "source_system": "attention_vision",
            "capability_link": None,
            "timestamp": sig.detected_at,
        }

    def merged_attention(self) -> list[dict[str, Any]]:
        """Visual signals + existing attention items, sorted by severity."""
        items: list[dict[str, Any]] = []
        for sig in self.detect_visual_signals():
            items.append(self._visual_to_attention_item(sig))
        agg = self.attention_aggregation_runtime
        if agg is not None:
            try:
                q = agg.queue()
                if hasattr(q, "items"):
                    items.extend(q.items)
            except Exception:
                logger.debug("AttentionAggregationRuntime queue unavailable")
        items.sort(key=lambda i: (i.get("priority", 9), -i.get("timestamp", 0)))
        return items

    # ── Snapshot ──────────────────────────────────────────────────

    def snapshot(self) -> AttentionVisionSnapshot:
        signals = self.detect_visual_signals()
        merged = self.merged_attention()
        crit = sum(1 for s in signals if s.severity == VisualSignalSeverity.CRITICAL.value)
        warn = sum(1 for s in signals if s.severity == VisualSignalSeverity.WARNING.value)
        info = sum(1 for s in signals if s.severity == VisualSignalSeverity.INFO.value)
        return AttentionVisionSnapshot(
            visual_signals=[s.to_dict() for s in signals],
            critical_count=crit,
            warning_count=warn,
            info_count=info,
            attention_items=merged,
            total_attention_count=len(merged),
            generated_at=time.time(),
        )

    def summary(self) -> dict[str, Any]:
        snap = self.snapshot()
        return {
            "critical_count": snap.critical_count,
            "warning_count": snap.warning_count,
            "info_count": snap.info_count,
            "total_attention_count": snap.total_attention_count,
            "signal_count": len(snap.visual_signals),
        }
