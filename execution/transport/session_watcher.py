"""
Session Watcher — continuous tmux state machine for Claude Code sessions.

Replaces blind before/after polling in ask_session with state-aware monitoring.
One SessionWatcher instance per tmux session (dex_builder_main, dex_product_main).
Runs as a daemon thread, polls tmux pane every 0.5s, detects session state,
emits events via callback when CC needs input.

State machine:
  IDLE → RESPONDING → IDLE (normal reply cycle)
  IDLE → WAITING_QUESTION → IDLE (CC asks a question)
  IDLE → PLAN_MODE → IDLE (CC proposes a plan)
  IDLE → PERMISSION_REQUEST → IDLE (CC needs tool permission)

Design invariants:
  - No hot-path imports (gateway, cognitive_loop, model_router, agent_runtime)
  - Daemon threads only — die with parent process
  - All tmux interaction via claude_session_bridge primitives
  - Safe degradation: if watcher is absent, ask_session falls back to polling
  - Builder and product sessions fully isolated (separate instances)
"""

from __future__ import annotations

import enum
import re
import threading
import time
from dataclasses import dataclass, field
from typing import Any, Callable

from execution.transport.claude_session_bridge import (
    capture_output,
    send_message,
)

LAYER_NAME = "session_watcher"
LAYER_VERSION = "v1"

# ─── Polling config ──────────────────────────────────────────────────────────

_POLL_INTERVAL_S = 2.0
_POLL_INTERVAL_ACTIVE_S = 0.5  # faster polling during active send
_STABLE_CYCLES_FOR_COMPLETE = 3  # output unchanged for N cycles = done
_MAX_REPLY_CHARS = 20_000  # safety cap on extracted reply
_IDLE_TIMEOUT_S = 30.0  # no activity at all → give up
_WORKING_TIMEOUT_S = 120.0  # tool calls in progress → keep waiting


# ─── CC output markers (same as claude_session_bridge) ───────────────────────

_RESPONSE_MARKER = "●"
_PROMPT_MARKER = "❯"
_STREAMING_INDICATORS = {"✻", "⎿"}
_ANSI_RE = re.compile(r"\x1b\[[0-9;]*[A-Za-z]|\x1b\].*?\x07|\x1b\[[\d;]*m")

# Tool call indicators — CC is actively working, not idle
_TOOL_CALL_PATTERNS = re.compile(
    r"(?:Bash|Read|Write|Edit|Glob|Grep|Agent)\s*\("
    r"|python3\s+"
    r"|git\s+"
    r"|⎿\s"
    r"|Running\s"
    r"|npm\s+"
    r"|pip\s+"
    r"|docker\s+"
)

# ─── State detection patterns ────────────────────────────────────────────────

# Plan mode: CC proposes a plan and waits for approval
_PLAN_PATTERNS = [
    re.compile(r"(?i)here is my plan"),
    re.compile(r"(?i)here'?s the plan"),
    re.compile(r"(?i)do you want me to proceed"),
    re.compile(r"(?i)shall i proceed"),
    re.compile(r"(?i)should i proceed"),
    re.compile(r"(?i)want me to go ahead"),
    re.compile(r"(?i)want me to proceed"),
    re.compile(r"(?i)ready to execute"),
    re.compile(r"(?i)approve this plan"),
    re.compile(r"(?i)say the word"),
    re.compile(r"(?i)full plan"),
    re.compile(r"(?i)plan mode"),
]

# Permission request: CC asks to run a tool
_PERMISSION_PATTERNS = [
    re.compile(r"Allow\s+(?:this\s+)?tool"),
    re.compile(r"needs?\s+permission"),
    re.compile(r"(?:Bash|Read|Write|Edit|Glob|Grep)\s*\("),
    re.compile(r"Allow\s+once"),
    re.compile(r"Allow\s+always"),
    re.compile(r"\[Y\]es\s*/\s*\[N\]o"),
    re.compile(r"Do you want to allow"),
]

# Question markers: CC is asking user a question
_QUESTION_PATTERNS = [
    re.compile(r"\?\s*$", re.MULTILINE),
    re.compile(r"(?i)which (?:one|option) (?:do you|would you)"),
    re.compile(r"(?i)could you (?:clarify|confirm|specify)"),
    re.compile(r"(?i)please (?:choose|select|confirm)"),
]


class SessionState(enum.Enum):
    """States the watcher tracks for a CC tmux session."""

    IDLE = "idle"
    RESPONDING = "responding"
    WORKING = "working"  # tool calls in progress — keep waiting
    WAITING_QUESTION = "waiting_question"
    PLAN_MODE = "plan_mode"
    PERMISSION_REQUEST = "permission_request"


@dataclass
class WatcherEvent:
    """Event emitted by the watcher when state changes meaningfully."""

    session_name: str
    state: SessionState
    text: str  # extracted content (reply, question, plan, permission desc)
    timestamp: float = field(default_factory=time.time)

    def to_dict(self) -> dict[str, Any]:
        return {
            "session_name": self.session_name,
            "state": self.state.value,
            "text": self.text,
            "timestamp": self.timestamp,
        }


# Type for the callback: receives a WatcherEvent
EventCallback = Callable[[WatcherEvent], None]


class SessionWatcher:
    """Continuous state machine monitor for a single CC tmux session.

    Usage:
        watcher = SessionWatcher("vps", "dex_builder_main", on_event=my_callback)
        watcher.start()  # daemon thread, non-blocking
        ...
        watcher.send_response("yes")  # pipe text back into tmux
        ...
        watcher.stop()
    """

    def __init__(
        self,
        target: str,
        session_name: str,
        *,
        on_event: EventCallback | None = None,
        poll_interval: float = _POLL_INTERVAL_S,
    ) -> None:
        self.target = target
        self.session_name = session_name
        self._on_event = on_event
        self._poll_interval = poll_interval

        self._state = SessionState.IDLE
        self._prev_output = ""
        self._stable_count = 0
        self._last_marker_count = 0
        self._responding_text = ""
        self._last_output_change: float = time.monotonic()  # track when output last changed

        # Baseline: length of clean output at the moment we send a message.
        # Everything before this offset belongs to *prior* interactions and
        # is ignored for state detection and reply extraction.
        self._before_len: int = 0

        # Active send flag: True only between send_response/ask_session_watched
        # and _finalize_reply.  Prevents background tmux activity from causing
        # IDLE → RESPONDING oscillation when no message is pending.
        self._active_send: bool = False

        self._stop_event = threading.Event()
        self._thread: threading.Thread | None = None
        self._lock = threading.Lock()

        # Reply delivery: ask_session_watched waits on this
        self._reply_ready = threading.Event()
        self._reply_text = ""

        # Activity tracking for !watcher_status
        self._last_activity: float = time.time()
        self._last_reply_preview: str = ""

    @property
    def state(self) -> SessionState:
        return self._state

    @property
    def is_running(self) -> bool:
        return self._thread is not None and self._thread.is_alive()

    @property
    def last_activity(self) -> float:
        return self._last_activity

    @property
    def last_reply_preview(self) -> str:
        return self._last_reply_preview

    def start(self) -> None:
        """Start the watcher daemon thread."""
        if self.is_running:
            return
        self._stop_event.clear()
        self._thread = threading.Thread(
            target=self._run_loop,
            name=f"watcher-{self.session_name}",
            daemon=True,
        )
        self._thread.start()
        print(f"[SessionWatcher] Started for {self.session_name}")

    def stop(self) -> None:
        """Signal the watcher to stop."""
        self._stop_event.set()
        if self._thread:
            self._thread.join(timeout=3.0)
            self._thread = None
        print(f"[SessionWatcher] Stopped for {self.session_name}")

    def send_response(self, text: str) -> dict[str, Any]:
        """Pipe a response back into the tmux session."""
        # Snapshot current output length so future polls only inspect new content
        with self._lock:
            self._before_len = len(self._prev_output)
            self._active_send = True
        result = send_message(self.target, self.session_name, text)
        if result.get("ok"):
            with self._lock:
                self._state = SessionState.IDLE
                self._stable_count = 0
        else:
            # Send failed — clear active flag so watcher doesn't wait forever
            with self._lock:
                self._active_send = False
        return result

    def wait_until_idle(
        self,
        timeout: float = 10.0,
        min_stable_polls: int = 2,
    ) -> bool:
        """Block until the session is truly idle (prompt visible, no streaming,
        output stable for *min_stable_polls* consecutive polls).

        Returns True if idle was confirmed, False if timed out.
        """
        deadline = time.monotonic() + timeout
        stable = 0
        prev_snapshot = ""
        while time.monotonic() < deadline:
            with self._lock:
                state = self._state
                snapshot = self._prev_output
                has_streaming = any(ind in snapshot for ind in _STREAMING_INDICATORS)
                lines = snapshot.strip().splitlines()
                last_line = lines[-1].strip() if lines else ""
                has_prompt = _PROMPT_MARKER in last_line
            if state == SessionState.IDLE and has_prompt and not has_streaming:
                if snapshot == prev_snapshot:
                    stable += 1
                else:
                    stable = 0
                if stable >= min_stable_polls:
                    return True
            else:
                stable = 0
            prev_snapshot = snapshot
            time.sleep(self._poll_interval)
        return False

    def wait_for_reply(self, timeout: float = _WORKING_TIMEOUT_S) -> str:
        """Block until the watcher detects a complete reply.

        Adaptive timeout: if CC is actively working (WORKING state),
        waits up to `timeout` seconds. If CC appears idle with no
        output changes, gives up after _IDLE_TIMEOUT_S of inactivity.

        Thread-safe: clears prior state under the watcher lock so a
        concurrent _run_loop iteration cannot set-then-lose the event.
        """
        with self._lock:
            self._reply_ready.clear()
            self._reply_text = ""

        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            # Check if reply arrived
            remaining = deadline - time.monotonic()
            wait_chunk = min(2.0, max(0.1, remaining))
            got_it = self._reply_ready.wait(timeout=wait_chunk)
            if got_it:
                return self._reply_text

            # Adaptive: check if CC is actively working or truly idle
            with self._lock:
                current_state = self._state
                idle_duration = time.monotonic() - self._last_output_change

            if current_state in (SessionState.WORKING, SessionState.RESPONDING):
                # CC is actively doing things — keep waiting up to full timeout
                continue

            # CC is idle with no output changes for _IDLE_TIMEOUT_S → give up
            if idle_duration >= _IDLE_TIMEOUT_S:
                print(
                    f"[SessionWatcher] {self.session_name}: "
                    f"no activity for {idle_duration:.0f}s, returning empty"
                )
                return ""

        return ""

    # ─── Internal loop ───────────────────────────────────────────────────

    def _run_loop(self) -> None:
        """Main polling loop — runs in daemon thread.

        Uses fast polling (0.5s) during active sends for responsiveness,
        slow polling (2s) when idle to reduce CPU overhead.
        """
        while not self._stop_event.is_set():
            try:
                self._poll_once()
            except Exception as e:
                print(f"[SessionWatcher] Error in {self.session_name}: {e}")
            interval = _POLL_INTERVAL_ACTIVE_S if self._active_send else self._poll_interval
            self._stop_event.wait(timeout=interval)

    def _poll_once(self) -> None:
        """Single poll cycle: capture output, detect state, emit events.

        All state detection (tool calls, streaming, markers) only inspects
        content *after* ``self._before_len`` — the snapshot taken when a
        message was sent.  This prevents old tmux history from causing
        oscillation between RESPONDING/WORKING and IDLE.
        """
        cap = capture_output(self.target, self.session_name, tail_lines=200)
        if not cap.get("ok"):
            return

        output = cap.get("output", "")
        clean = _ANSI_RE.sub("", output)

        with self._lock:
            output_changed = clean != self._prev_output

            if not output_changed:
                self._stable_count += 1
            else:
                self._stable_count = 0
                self._last_output_change = time.monotonic()

            # ── New-content window ──────────────────────────────────────
            # Only look at output produced *after* the last send for
            # markers, streaming, and tool call detection.
            new_content = clean[self._before_len :]

            # Count response markers (only in new content)
            marker_count_new = new_content.count(_RESPONSE_MARKER)
            new_marker = marker_count_new > self._last_marker_count

            # Detect streaming indicators (only in new content)
            has_streaming = any(ind in new_content for ind in _STREAMING_INDICATORS)

            # Detect tool call activity (only in new content)
            tail = new_content[-2000:] if len(new_content) > 2000 else new_content
            has_tool_activity = bool(_TOOL_CALL_PATTERNS.search(tail))

            # Detect prompt — still use the absolute last line (prompt is global)
            lines = clean.strip().splitlines()
            last_line = lines[-1].strip() if lines else ""
            has_prompt = _PROMPT_MARKER in last_line

            prev_state = self._state

            if self._state == SessionState.IDLE:
                # Only transition out of IDLE when a send is in progress.
                # Background tmux activity (skill loading, scripts) produces
                # markers/streaming but should not trigger state changes.
                if self._active_send and (new_marker or has_streaming):
                    self._state = SessionState.RESPONDING
                    self._responding_text = ""
                    self._stable_count = 0

            elif self._state == SessionState.RESPONDING:
                # Check if CC is running tool calls — transition to WORKING
                if output_changed and has_tool_activity and not has_prompt:
                    self._state = SessionState.WORKING
                    self._stable_count = 0
                elif self._stable_count >= _STABLE_CYCLES_FOR_COMPLETE and not has_streaming:
                    self._finalize_reply(clean, has_prompt)

            elif self._state == SessionState.WORKING:
                # CC is executing tool calls. Stay here while output changes.
                if output_changed:
                    # Still working — reset stability counter
                    self._stable_count = 0
                elif self._stable_count >= _STABLE_CYCLES_FOR_COMPLETE and not has_streaming:
                    if has_prompt:
                        # Tool calls done, prompt visible — extract final reply
                        self._finalize_reply(clean, has_prompt)
                    elif has_tool_activity:
                        # Tool output stabilized but no prompt yet — keep waiting
                        pass
                    else:
                        # No prompt, no streaming, no tool activity, stable
                        # — might be waiting for permission/plan
                        reply = self._extract_latest_reply(clean)
                        detected = self._classify_reply(reply)
                        if detected in (
                            SessionState.PLAN_MODE,
                            SessionState.PERMISSION_REQUEST,
                            SessionState.WAITING_QUESTION,
                        ):
                            self._state = detected
                            self._active_send = False
                            self._emit(
                                WatcherEvent(
                                    session_name=self.session_name,
                                    state=detected,
                                    text=reply[:1500],
                                )
                            )

                # Detect new streaming after tool calls (CC writing more text)
                if new_marker or has_streaming:
                    self._state = SessionState.RESPONDING
                    self._stable_count = 0

            elif self._state in (
                SessionState.WAITING_QUESTION,
                SessionState.PLAN_MODE,
                SessionState.PERMISSION_REQUEST,
            ):
                # If output changed significantly, CC may have received
                # input and is now responding again
                if new_marker or has_streaming:
                    self._state = SessionState.RESPONDING
                    self._stable_count = 0

            self._prev_output = clean
            self._last_marker_count = marker_count_new

            if prev_state != self._state:
                print(
                    f"[SessionWatcher] {self.session_name}: "
                    f"{prev_state.value} → {self._state.value}"
                )

    def _finalize_reply(self, clean: str, has_prompt: bool) -> None:
        """Extract reply from stabilized output and transition state.

        Must be called under self._lock.

        Key distinction: when ``has_prompt`` is True, the ● marker is stable
        and ❯ is visible — CC's reply is **complete**.  A trailing ``?`` in
        a conversational reply (e.g. "What do you need?") is NOT an
        interactive question; only plan_mode and permission_request warrant
        holding the reply.  ``waiting_question`` is reserved for CC's
        ask_user tool which appears *without* a subsequent ● + ❯ sequence.
        """
        reply = self._extract_latest_reply(clean)

        if has_prompt:
            detected = self._classify_reply(reply)

            if detected == SessionState.PLAN_MODE:
                self._state = SessionState.PLAN_MODE
                self._active_send = False
                self._emit(
                    WatcherEvent(
                        session_name=self.session_name,
                        state=SessionState.PLAN_MODE,
                        text=reply[:1500],
                    )
                )
            elif detected == SessionState.PERMISSION_REQUEST:
                self._state = SessionState.PERMISSION_REQUEST
                self._active_send = False
                self._emit(
                    WatcherEvent(
                        session_name=self.session_name,
                        state=SessionState.PERMISSION_REQUEST,
                        text=reply[:500],
                    )
                )
            else:
                # Normal reply (including conversational "?" replies) —
                # deliver it.  A completed response with ● + ❯ is never
                # a waiting_question; that state is for ask_user tool only.
                self._state = SessionState.IDLE
                self._active_send = False
                self._reply_text = reply
                self._reply_ready.set()
                self._emit(
                    WatcherEvent(
                        session_name=self.session_name,
                        state=SessionState.IDLE,
                        text=reply[:_MAX_REPLY_CHARS],
                    )
                )
        else:
            # No prompt yet but stable — check for plan/permission/question.
            # Without a prompt, CC may genuinely be waiting for user input
            # (ask_user tool), so waiting_question IS valid here.
            detected = self._classify_reply(reply)
            if detected in (
                SessionState.PLAN_MODE,
                SessionState.PERMISSION_REQUEST,
                SessionState.WAITING_QUESTION,
            ):
                self._state = detected
                self._active_send = False
                self._emit(
                    WatcherEvent(
                        session_name=self.session_name,
                        state=detected,
                        text=reply[:1500],
                    )
                )

    def _classify_reply(self, text: str) -> SessionState:
        """Classify what kind of reply CC produced."""
        # Check permission first (most specific)
        for pat in _PERMISSION_PATTERNS:
            if pat.search(text):
                return SessionState.PERMISSION_REQUEST

        # Check plan mode — explicit patterns
        for pat in _PLAN_PATTERNS:
            if pat.search(text):
                return SessionState.PLAN_MODE

        # Check plan mode — reply ends with a question about proceeding
        last_lines = "\n".join(text.strip().splitlines()[-5:])
        if re.search(
            r"(?i)(?:shall|should|want me to|ready to|do you want)"
            r".*(?:proceed|execute|implement|go ahead|start|build)"
            r".*\?",
            last_lines,
        ):
            return SessionState.PLAN_MODE

        # Check question — only if text ends with ? in last few lines
        for pat in _QUESTION_PATTERNS:
            if pat.search(last_lines):
                return SessionState.WAITING_QUESTION

        return SessionState.IDLE

    def _extract_latest_reply(self, clean_output: str) -> str:
        """Extract the latest CC reply from clean tmux output.

        Only considers ``●`` markers that appear in new content (after
        ``self._before_len``), so prior-response markers are ignored.
        """
        # Determine which line index corresponds to _before_len so we
        # only search for markers in the new portion.
        before_len = self._before_len
        lines = clean_output.splitlines()

        if before_len >= len(clean_output):
            # No new content at all — nothing to extract
            return ""

        cum_len = 0
        new_start_line = len(lines)  # default: past end (no new content)
        for idx, line in enumerate(lines):
            # +1 for the newline character stripped by splitlines
            cum_len += len(line) + 1
            if cum_len >= before_len:
                new_start_line = idx
                break

        # Find last ● marker in new content only
        last_marker_idx = -1
        for i in range(new_start_line, len(lines)):
            if _RESPONSE_MARKER in lines[i]:
                last_marker_idx = i

        if last_marker_idx < 0:
            return ""

        # Extract from marker to next prompt or end
        reply_lines: list[str] = []
        for i in range(last_marker_idx, len(lines)):
            line = lines[i]
            # Stop at prompt
            if i > last_marker_idx and _PROMPT_MARKER in line:
                break
            reply_lines.append(line)

        # Strip the ● marker from first line
        if reply_lines:
            reply_lines[0] = reply_lines[0].replace(_RESPONSE_MARKER, "").strip()

        result = "\n".join(reply_lines).strip()
        return result[:_MAX_REPLY_CHARS]

    def _emit(self, event: WatcherEvent) -> None:
        """Emit event via callback (if registered)."""
        self._last_activity = event.timestamp
        if event.text:
            self._last_reply_preview = event.text[:200]
        if self._on_event:
            try:
                self._on_event(event)
            except Exception as e:
                print(f"[SessionWatcher] Callback error: {e}")


# ─── Global watcher registry ────────────────────────────────────────────────

_WATCHERS: dict[str, SessionWatcher] = {}
_WATCHERS_LOCK = threading.Lock()


def get_watcher(session_name: str) -> SessionWatcher | None:
    """Get the running watcher for a session, if any."""
    with _WATCHERS_LOCK:
        w = _WATCHERS.get(session_name)
        if w and w.is_running:
            return w
        return None


def start_watcher(
    target: str,
    session_name: str,
    *,
    on_event: EventCallback | None = None,
) -> SessionWatcher:
    """Start (or return existing) watcher for a session."""
    with _WATCHERS_LOCK:
        existing = _WATCHERS.get(session_name)
        if existing and existing.is_running:
            return existing

        watcher = SessionWatcher(target, session_name, on_event=on_event)
        watcher.start()
        _WATCHERS[session_name] = watcher
        return watcher


def stop_watcher(session_name: str) -> None:
    """Stop and remove watcher for a session."""
    with _WATCHERS_LOCK:
        w = _WATCHERS.pop(session_name, None)
    if w:
        w.stop()


def stop_all_watchers() -> None:
    """Stop all running watchers."""
    with _WATCHERS_LOCK:
        names = list(_WATCHERS.keys())
    for name in names:
        stop_watcher(name)


# ─── Watcher-aware ask_session replacement ───────────────────────────────────


def ask_session_watched(
    target: str,
    session_name: str,
    text: str,
    *,
    timeout: float = 120.0,
) -> dict[str, Any]:
    """Send a message and wait for the watcher to detect the reply.

    If no watcher is running for this session, returns fallback signal
    so the caller can use the original ask_session polling.

    Returns same shape as ask_session for compatibility.
    """
    watcher = get_watcher(session_name)
    if not watcher:
        return {"ok": False, "reason": "no_watcher", "fallback": True}

    # Wait for the session to be truly idle before injecting text.
    # On rapid sequential messages the ❯ prompt can appear before CC
    # has fully settled — sending too early causes Enter to be lost.
    idle_ok = watcher.wait_until_idle(timeout=30.0, min_stable_polls=2)
    # If still not idle after 30s, send anyway (best effort)
    if not idle_ok:
        print(f"[SessionWatcher] {session_name}: idle wait timed out, sending anyway")

    # Snapshot pane length before sending so the watcher only inspects
    # new content produced *after* this message.
    with watcher._lock:
        watcher._before_len = len(watcher._prev_output)
        watcher._active_send = True

    # Send the message
    send_res = send_message(target, session_name, text)
    if not send_res.get("ok"):
        return {
            "ok": False,
            "stage": "send",
            "send": send_res,
            "layer": LAYER_NAME,
            "version": LAYER_VERSION,
        }

    # Wait for watcher to detect reply
    reply = watcher.wait_for_reply(timeout=timeout)

    return {
        "ok": True,
        "target": target,
        "session_name": session_name,
        "sent_chars": len(text),
        "reply_text": reply,
        "reply_chars": len(reply),
        "watcher": True,
        "layer": LAYER_NAME,
        "version": LAYER_VERSION,
    }


__all__ = [
    "LAYER_NAME",
    "LAYER_VERSION",
    "SessionState",
    "WatcherEvent",
    "EventCallback",
    "SessionWatcher",
    "get_watcher",
    "start_watcher",
    "stop_watcher",
    "stop_all_watchers",
    "ask_session_watched",
]
