# Live Runtime Workstation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Wire existing substrate and EOS platform layers into one seamless conversational runtime loop where the founder speaks naturally to EA, work is immediately created and executed on the local machine (with VPS fallback), browser/machine actions execute through Playwright and subprocess, and interruptions (pause/stop/continue) work naturally.

**Architecture:** Three new files (two EOS platform, one substrate) plus minimal modifications to four existing files. EALiveRuntime wraps `handle_founder_message()` with conversational control interception, immediate execution via ExecutionBridge, and live session binding. BrowserAgent provides a real Playwright execution surface. `execute_control_request` becomes a real dispatcher.

**Tech Stack:** Python 3.12, Playwright (sync API, headless Chromium), subprocess for OS-level actions, existing substrate storage/task/pipeline/live-session infrastructure.

---

## File Map

### New Files
| File | Responsibility |
|------|---------------|
| `eos_ai/platforms/eos/live_runtime.py` | Conversational runtime state machine. Intercepts control phrases before intent routing. Wraps EA orchestrator with immediate execution and live session management. |
| `eos_ai/platforms/eos/execution_bridge.py` | Given task/pipeline IDs from EAResponse, immediately executes through existing substrate task/pipeline execution with local-preferred routing. |
| `eos_ai/substrate/browser_agent.py` | Generic Playwright browser execution surface. open_url, click, type_text, extract, screenshot. Not EOS-specific. |

### New Test Files
| File | Coverage |
|------|----------|
| `tests/platforms/eos/test_live_runtime.py` | Runtime state machine, control phrase interception, live session binding, pause/resume |
| `tests/platforms/eos/test_execution_bridge.py` | Immediate execution, local-first routing, fallback, blocked task surfacing |
| `tests/substrate/test_browser_agent.py` | Browser lifecycle, action dispatch, mode gating, error handling |

### Modified Files
| File | Change |
|------|--------|
| `eos_ai/substrate/local_control.py` | Replace `execute_control_request` stub with real dispatch to subprocess (machine actions) and browser_agent (browser actions) |
| `eos_ai/platforms/eos/discord_hook.py` | Add `handle_eos_discord_live_message()` that routes through live runtime when appropriate |
| `eos_ai/platforms/eos/__init__.py` | Export new live_runtime and execution_bridge symbols |
| `eos_ai/substrate/pipeline_execution.py` | Add browser/machine step type detection in `_execute_step` for direct local control dispatch |

---

## Task 1: BrowserAgent — Generic Substrate Execution Surface

**Files:**
- Create: `eos_ai/substrate/browser_agent.py`
- Create: `tests/substrate/test_browser_agent.py`

### Step-by-step

- [ ] **Step 1: Write the test file**

```python
"""Browser agent tests — generic substrate execution surface."""

import sys
sys.path.insert(0, "/opt/OS")

from eos_ai.substrate.browser_agent import (
    BrowserAgent,
    BrowserActionType,
    BrowserActionResult,
    get_browser_agent,
    execute_browser_action,
)


def _reset():
    BrowserAgent._default = None


# ── Unit Tests ──────────────────────────────────────────────────────────────

def test_singleton_creation():
    _reset()
    agent = get_browser_agent()
    assert agent is not None
    assert agent is get_browser_agent()  # same instance
    _reset()
    print("  PASS singleton_creation")


def test_action_types_exist():
    assert BrowserActionType.OPEN_URL
    assert BrowserActionType.CLICK
    assert BrowserActionType.TYPE_TEXT
    assert BrowserActionType.EXTRACT
    assert BrowserActionType.SCREENSHOT
    assert BrowserActionType.NAVIGATE_BACK
    assert BrowserActionType.CLOSE
    print("  PASS action_types_exist")


def test_execute_open_url_headless():
    """Real Playwright test — opens a data: URL headless."""
    _reset()
    result = execute_browser_action(
        BrowserActionType.OPEN_URL,
        {"url": "data:text/html,<h1>Hello</h1>"},
    )
    assert result.ok, f"open_url failed: {result.error}"
    assert result.action == BrowserActionType.OPEN_URL
    _reset()
    print("  PASS execute_open_url_headless")


def test_execute_extract():
    """Real Playwright test — extract text from a page."""
    _reset()
    # First open a page
    execute_browser_action(
        BrowserActionType.OPEN_URL,
        {"url": "data:text/html,<h1 id='title'>TestTitle</h1>"},
    )
    result = execute_browser_action(
        BrowserActionType.EXTRACT,
        {"selector": "#title"},
    )
    assert result.ok, f"extract failed: {result.error}"
    assert "TestTitle" in (result.data or "")
    _reset()
    print("  PASS execute_extract")


def test_execute_click():
    """Real Playwright test — click an element."""
    _reset()
    html = "data:text/html,<button id='btn' onclick='document.title=\"clicked\"'>Click</button>"
    execute_browser_action(BrowserActionType.OPEN_URL, {"url": html})
    result = execute_browser_action(
        BrowserActionType.CLICK,
        {"selector": "#btn"},
    )
    assert result.ok, f"click failed: {result.error}"
    _reset()
    print("  PASS execute_click")


def test_execute_type_text():
    """Real Playwright test — type into an input."""
    _reset()
    html = "data:text/html,<input id='inp' type='text'/>"
    execute_browser_action(BrowserActionType.OPEN_URL, {"url": html})
    result = execute_browser_action(
        BrowserActionType.TYPE_TEXT,
        {"selector": "#inp", "text": "hello world"},
    )
    assert result.ok, f"type_text failed: {result.error}"
    _reset()
    print("  PASS execute_type_text")


def test_execute_screenshot():
    """Real Playwright test — take a screenshot."""
    _reset()
    execute_browser_action(
        BrowserActionType.OPEN_URL,
        {"url": "data:text/html,<h1>Screenshot</h1>"},
    )
    result = execute_browser_action(BrowserActionType.SCREENSHOT, {})
    assert result.ok, f"screenshot failed: {result.error}"
    assert result.data  # should have a path or base64
    _reset()
    print("  PASS execute_screenshot")


def test_execute_without_page_fails_gracefully():
    """Actions on a closed/no-page agent should fail gracefully."""
    _reset()
    result = execute_browser_action(
        BrowserActionType.CLICK,
        {"selector": "#nope"},
    )
    assert not result.ok
    assert result.error
    _reset()
    print("  PASS execute_without_page_fails_gracefully")


def test_close_action():
    _reset()
    execute_browser_action(
        BrowserActionType.OPEN_URL,
        {"url": "data:text/html,<h1>Close</h1>"},
    )
    result = execute_browser_action(BrowserActionType.CLOSE, {})
    assert result.ok
    _reset()
    print("  PASS close_action")


def test_navigate_back():
    _reset()
    execute_browser_action(
        BrowserActionType.OPEN_URL,
        {"url": "data:text/html,<h1>Page1</h1>"},
    )
    execute_browser_action(
        BrowserActionType.OPEN_URL,
        {"url": "data:text/html,<h1>Page2</h1>"},
    )
    result = execute_browser_action(BrowserActionType.NAVIGATE_BACK, {})
    assert result.ok, f"navigate_back failed: {result.error}"
    _reset()
    print("  PASS navigate_back")


# ── Runner ──────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("=== Browser Agent Tests ===")
    test_singleton_creation()
    test_action_types_exist()
    test_execute_open_url_headless()
    test_execute_extract()
    test_execute_click()
    test_execute_type_text()
    test_execute_screenshot()
    test_execute_without_page_fails_gracefully()
    test_close_action()
    test_navigate_back()
    print("=== ALL PASSED ===")
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python3 /opt/OS/tests/substrate/test_browser_agent.py`
Expected: ImportError — `browser_agent` module does not exist yet.

- [ ] **Step 3: Write browser_agent.py**

```python
"""
Browser agent — generic Playwright execution surface for the substrate.

NOT EOS-specific. This is a generic browser automation layer usable by
any platform projection. It provides structured browser actions gated
by the local control mode system.

Design rules (substrate conventions):
- Additive only — never imported on the hot path.
- Best-effort — action failures return BrowserActionResult with ok=False.
- Persistent context — browser session stays alive between actions for
  multi-step workflows. Lazily initialized on first use.
- Headless by default — runs on VPS without a display. Set headless=False
  only when a display is available.
- Thread-safe — single browser context, one page at a time.
- Singleton via get_browser_agent() — matches all other substrate stores.
"""

from __future__ import annotations

import os
import sys
import threading
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Optional


def _log(msg: str) -> None:
    print(f"[substrate.browser_agent] {msg}", file=sys.stderr)


def _utcnow() -> str:
    return datetime.now(timezone.utc).isoformat()


# ─── Enums ──────────────────────────────────────────────────────────────────


class BrowserActionType(str, Enum):
    """Structured browser actions — no arbitrary JS execution."""

    OPEN_URL = "open_url"
    CLICK = "click"
    TYPE_TEXT = "type_text"
    EXTRACT = "extract"
    SCREENSHOT = "screenshot"
    NAVIGATE_BACK = "navigate_back"
    CLOSE = "close"


# ─── Result Dataclass ───────────────────────────────────────────────────────


@dataclass
class BrowserActionResult:
    """Outcome of a browser action."""

    action: BrowserActionType
    ok: bool
    data: Optional[str] = None
    error: Optional[str] = None
    duration_ms: float = 0.0
    created_at: str = field(default_factory=_utcnow)

    def to_dict(self) -> dict[str, Any]:
        return {
            "action": self.action.value,
            "ok": self.ok,
            "data": self.data,
            "error": self.error,
            "duration_ms": self.duration_ms,
            "created_at": self.created_at,
        }


# ─── Browser Agent ──────────────────────────────────────────────────────────


class BrowserAgent:
    """Persistent Playwright browser session for structured actions.

    Lazily initializes Playwright and Chromium on first action.
    Singleton via get_browser_agent(). Thread-safe.
    """

    _default: Optional["BrowserAgent"] = None
    _default_lock = threading.Lock()

    def __init__(self, *, headless: bool = True) -> None:
        self._lock = threading.RLock()
        self._headless = headless
        self._playwright: Any = None
        self._browser: Any = None
        self._context: Any = None
        self._page: Any = None
        self._initialized = False

    # ── Singleton ────────────────────────────────────────────────────────

    @classmethod
    def default(cls, *, headless: bool = True) -> "BrowserAgent":
        if cls._default is None:
            with cls._default_lock:
                if cls._default is None:
                    cls._default = cls(headless=headless)
        return cls._default

    @classmethod
    def reset_default_for_tests(cls) -> None:
        with cls._default_lock:
            if cls._default is not None:
                cls._default.close()
                cls._default = None

    # ── Lifecycle ────────────────────────────────────────────────────────

    def _ensure_browser(self) -> bool:
        """Lazily start Playwright + Chromium. Returns True if ready."""
        if self._initialized and self._browser:
            return True
        try:
            from playwright.sync_api import sync_playwright

            self._playwright = sync_playwright().start()
            self._browser = self._playwright.chromium.launch(
                headless=self._headless,
            )
            self._context = self._browser.new_context(
                viewport={"width": 1280, "height": 720},
            )
            self._initialized = True
            _log("browser initialized (headless={self._headless})")
            return True
        except Exception as exc:
            _log(f"browser init failed: {exc}")
            self._initialized = False
            return False

    def _ensure_page(self) -> bool:
        """Ensure we have a page. Creates one if needed."""
        if not self._ensure_browser():
            return False
        if self._page is None or self._page.is_closed():
            try:
                self._page = self._context.new_page()
                return True
            except Exception as exc:
                _log(f"page creation failed: {exc}")
                return False
        return True

    def close(self) -> None:
        """Tear down browser resources."""
        with self._lock:
            try:
                if self._page and not self._page.is_closed():
                    self._page.close()
            except Exception:
                pass
            try:
                if self._context:
                    self._context.close()
            except Exception:
                pass
            try:
                if self._browser:
                    self._browser.close()
            except Exception:
                pass
            try:
                if self._playwright:
                    self._playwright.stop()
            except Exception:
                pass
            self._page = None
            self._context = None
            self._browser = None
            self._playwright = None
            self._initialized = False

    # ── Action Dispatch ──────────────────────────────────────────────────

    def execute(
        self,
        action: BrowserActionType,
        payload: dict[str, Any],
    ) -> BrowserActionResult:
        """Execute a structured browser action. Thread-safe."""
        import time

        start = time.monotonic()
        with self._lock:
            try:
                result = self._dispatch(action, payload)
                result.duration_ms = (time.monotonic() - start) * 1000
                return result
            except Exception as exc:
                return BrowserActionResult(
                    action=action,
                    ok=False,
                    error=f"unhandled: {exc}",
                    duration_ms=(time.monotonic() - start) * 1000,
                )

    def _dispatch(
        self,
        action: BrowserActionType,
        payload: dict[str, Any],
    ) -> BrowserActionResult:
        """Route action to handler. Caller holds lock."""
        if action == BrowserActionType.CLOSE:
            return self._do_close()

        if action == BrowserActionType.OPEN_URL:
            return self._do_open_url(payload)

        # All other actions require an active page
        if not self._page or self._page.is_closed():
            return BrowserActionResult(
                action=action,
                ok=False,
                error="no active page — call open_url first",
            )

        handlers = {
            BrowserActionType.CLICK: self._do_click,
            BrowserActionType.TYPE_TEXT: self._do_type_text,
            BrowserActionType.EXTRACT: self._do_extract,
            BrowserActionType.SCREENSHOT: self._do_screenshot,
            BrowserActionType.NAVIGATE_BACK: self._do_navigate_back,
        }
        handler = handlers.get(action)
        if handler is None:
            return BrowserActionResult(
                action=action,
                ok=False,
                error=f"unknown action: {action.value}",
            )
        return handler(payload)

    # ── Handlers ─────────────────────────────────────────────────────────

    def _do_open_url(self, payload: dict) -> BrowserActionResult:
        url = payload.get("url", "")
        if not url:
            return BrowserActionResult(
                action=BrowserActionType.OPEN_URL,
                ok=False,
                error="missing 'url' in payload",
            )
        if not self._ensure_page():
            return BrowserActionResult(
                action=BrowserActionType.OPEN_URL,
                ok=False,
                error="could not create browser page",
            )
        try:
            self._page.goto(url, wait_until="domcontentloaded", timeout=30_000)
            return BrowserActionResult(
                action=BrowserActionType.OPEN_URL,
                ok=True,
                data=self._page.url,
            )
        except Exception as exc:
            return BrowserActionResult(
                action=BrowserActionType.OPEN_URL,
                ok=False,
                error=str(exc),
            )

    def _do_click(self, payload: dict) -> BrowserActionResult:
        selector = payload.get("selector", "")
        if not selector:
            return BrowserActionResult(
                action=BrowserActionType.CLICK,
                ok=False,
                error="missing 'selector'",
            )
        try:
            self._page.click(selector, timeout=10_000)
            return BrowserActionResult(
                action=BrowserActionType.CLICK,
                ok=True,
                data=f"clicked {selector}",
            )
        except Exception as exc:
            return BrowserActionResult(
                action=BrowserActionType.CLICK,
                ok=False,
                error=str(exc),
            )

    def _do_type_text(self, payload: dict) -> BrowserActionResult:
        selector = payload.get("selector", "")
        text = payload.get("text", "")
        if not selector:
            return BrowserActionResult(
                action=BrowserActionType.TYPE_TEXT,
                ok=False,
                error="missing 'selector'",
            )
        try:
            self._page.fill(selector, text, timeout=10_000)
            return BrowserActionResult(
                action=BrowserActionType.TYPE_TEXT,
                ok=True,
                data=f"typed {len(text)} chars into {selector}",
            )
        except Exception as exc:
            return BrowserActionResult(
                action=BrowserActionType.TYPE_TEXT,
                ok=False,
                error=str(exc),
            )

    def _do_extract(self, payload: dict) -> BrowserActionResult:
        selector = payload.get("selector", "")
        if not selector:
            return BrowserActionResult(
                action=BrowserActionType.EXTRACT,
                ok=False,
                error="missing 'selector'",
            )
        try:
            element = self._page.query_selector(selector)
            if element is None:
                return BrowserActionResult(
                    action=BrowserActionType.EXTRACT,
                    ok=False,
                    error=f"element not found: {selector}",
                )
            text = element.text_content() or ""
            return BrowserActionResult(
                action=BrowserActionType.EXTRACT,
                ok=True,
                data=text.strip(),
            )
        except Exception as exc:
            return BrowserActionResult(
                action=BrowserActionType.EXTRACT,
                ok=False,
                error=str(exc),
            )

    def _do_screenshot(self, payload: dict) -> BrowserActionResult:
        try:
            path = payload.get("path")
            if not path:
                path = f"/tmp/eos_screenshot_{uuid.uuid4().hex[:8]}.png"
            self._page.screenshot(path=path, full_page=True)
            return BrowserActionResult(
                action=BrowserActionType.SCREENSHOT,
                ok=True,
                data=path,
            )
        except Exception as exc:
            return BrowserActionResult(
                action=BrowserActionType.SCREENSHOT,
                ok=False,
                error=str(exc),
            )

    def _do_navigate_back(self, payload: dict) -> BrowserActionResult:
        try:
            self._page.go_back(wait_until="domcontentloaded", timeout=10_000)
            return BrowserActionResult(
                action=BrowserActionType.NAVIGATE_BACK,
                ok=True,
                data=self._page.url,
            )
        except Exception as exc:
            return BrowserActionResult(
                action=BrowserActionType.NAVIGATE_BACK,
                ok=False,
                error=str(exc),
            )

    def _do_close(self) -> BrowserActionResult:
        self.close()
        return BrowserActionResult(
            action=BrowserActionType.CLOSE,
            ok=True,
            data="browser closed",
        )


# ─── Module-Level API ───────────────────────────────────────────────────────


def get_browser_agent(*, headless: bool = True) -> BrowserAgent:
    """Get the singleton BrowserAgent instance."""
    return BrowserAgent.default(headless=headless)


def execute_browser_action(
    action: BrowserActionType,
    payload: dict[str, Any],
    *,
    headless: bool = True,
) -> BrowserActionResult:
    """Execute a browser action through the singleton agent."""
    agent = get_browser_agent(headless=headless)
    return agent.execute(action, payload)


__all__ = [
    "BrowserActionType",
    "BrowserActionResult",
    "BrowserAgent",
    "get_browser_agent",
    "execute_browser_action",
]
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python3 /opt/OS/tests/substrate/test_browser_agent.py`
Expected: ALL PASSED (real Playwright, headless Chromium)

- [ ] **Step 5: Compile check**

Run: `python3 -m py_compile eos_ai/substrate/browser_agent.py`
Expected: No output (success)

- [ ] **Step 6: Format**

Run: `cd /opt/OS && ruff format eos_ai/substrate/browser_agent.py tests/substrate/test_browser_agent.py`

- [ ] **Step 7: Commit**

```bash
cd /opt/OS && git add eos_ai/substrate/browser_agent.py tests/substrate/test_browser_agent.py && git commit -m "feat: add browser_agent — real Playwright execution surface for substrate"
```

---

## Task 2: Real execute_control_request — Replace Stub with Real Dispatch

**Files:**
- Modify: `eos_ai/substrate/local_control.py:447-504` (replace `execute_control_request` function body)

### Step-by-step

- [ ] **Step 1: Write the test additions**

Create new test cases at the bottom of the existing test file that verify real dispatch. Add these to `tests/substrate/test_local_control.py`:

```python
# Add to the existing test file — new tests for real dispatch

def test_real_open_url_dispatch():
    """execute_control_request should dispatch OPEN_URL through browser_agent."""
    _reset_all()
    store = LocalControlStore.default()
    store.set_mode(LocalControlMode.ASSISTED)
    req = submit_control_request(
        LocalControlAction.OPEN_URL,
        {"url": "data:text/html,<h1>RealTest</h1>"},
        local_available=True,
    )
    assert req.status == RequestStatus.PENDING
    executed = execute_control_request(req.request_id)
    assert executed.status == RequestStatus.COMPLETED, f"got {executed.status.value}: {executed.error}"
    assert executed.result
    _reset_all()
    print("  PASS real_open_url_dispatch")


def test_real_click_dispatch():
    """execute_control_request should dispatch CLICK through browser_agent."""
    _reset_all()
    store = LocalControlStore.default()
    store.set_mode(LocalControlMode.FULL_CONTROL)
    # First open a page
    req_url = submit_control_request(
        LocalControlAction.OPEN_URL,
        {"url": "data:text/html,<button id='btn'>OK</button>"},
        local_available=True,
    )
    execute_control_request(req_url.request_id)
    # Now click
    req_click = submit_control_request(
        LocalControlAction.CLICK_MOUSE,
        {"selector": "#btn"},
        local_available=True,
    )
    executed = execute_control_request(req_click.request_id)
    assert executed.status == RequestStatus.COMPLETED, f"got {executed.status.value}: {executed.error}"
    _reset_all()
    print("  PASS real_click_dispatch")


def test_real_type_text_dispatch():
    """execute_control_request should dispatch TYPE_TEXT through browser_agent."""
    _reset_all()
    store = LocalControlStore.default()
    store.set_mode(LocalControlMode.FULL_CONTROL)
    req_url = submit_control_request(
        LocalControlAction.OPEN_URL,
        {"url": "data:text/html,<input id='inp'/>"},
        local_available=True,
    )
    execute_control_request(req_url.request_id)
    req_type = submit_control_request(
        LocalControlAction.TYPE_TEXT,
        {"selector": "#inp", "text": "hello"},
        local_available=True,
    )
    executed = execute_control_request(req_type.request_id)
    assert executed.status == RequestStatus.COMPLETED, f"got {executed.status.value}: {executed.error}"
    _reset_all()
    print("  PASS real_type_text_dispatch")


def test_open_app_dispatch_subprocess():
    """OPEN_APP should try subprocess dispatch (may fail on headless VPS, but should not crash)."""
    _reset_all()
    store = LocalControlStore.default()
    store.set_mode(LocalControlMode.ASSISTED)
    req = submit_control_request(
        LocalControlAction.OPEN_APP,
        {"app_id": "nonexistent_app_12345"},
        local_available=True,
    )
    executed = execute_control_request(req.request_id)
    # On VPS without display, this may fail — but it should fail gracefully, not crash
    assert executed.status in (RequestStatus.COMPLETED, RequestStatus.FAILED)
    _reset_all()
    print("  PASS open_app_dispatch_subprocess")
```

- [ ] **Step 2: Run old tests to verify they still pass**

Run: `python3 /opt/OS/tests/substrate/test_local_control.py`
Expected: ALL PASSED (existing behavior unchanged)

- [ ] **Step 3: Replace execute_control_request with real dispatch**

Replace the function at `local_control.py:447-504` with:

```python
def execute_control_request(request_id: str) -> LocalControlRequest:
    """Mark a request as executing and dispatch to real OS/browser automation.

    Dispatch routes:
    - OPEN_URL → browser_agent (Playwright)
    - CLICK_MOUSE → browser_agent (Playwright click by selector)
    - TYPE_TEXT → browser_agent (Playwright fill by selector)
    - PRESS_KEYS → browser_agent (Playwright keyboard.press)
    - READ_SCREEN_STATE → browser_agent (screenshot)
    - OPEN_APP → subprocess (xdg-open or platform launcher)
    - FOCUS_APP → subprocess (wmctrl/xdotool or platform equivalent)
    - OPEN_SCENE → scene resolution + recursive step dispatch
    - MOVE_MOUSE → not supported on headless VPS (fails gracefully)
    - LIST_WINDOWS → subprocess (wmctrl -l or equivalent)
    """
    store = LocalControlStore.default()
    req = store.get(request_id)
    if req is None:
        now = _utcnow()
        return LocalControlRequest(
            request_id=request_id,
            action=LocalControlAction.LIST_WINDOWS,
            payload={},
            created_at=now,
            status=RequestStatus.FAILED,
            error=f"request {request_id} not found",
            updated_at=now,
        )

    req.status = RequestStatus.EXECUTING
    req.updated_at = _utcnow()
    store.put(req)

    try:
        if req.action == LocalControlAction.OPEN_URL:
            req = _dispatch_browser_open_url(req)
        elif req.action == LocalControlAction.CLICK_MOUSE:
            req = _dispatch_browser_click(req)
        elif req.action == LocalControlAction.TYPE_TEXT:
            req = _dispatch_browser_type(req)
        elif req.action == LocalControlAction.PRESS_KEYS:
            req = _dispatch_browser_press_keys(req)
        elif req.action == LocalControlAction.READ_SCREEN_STATE:
            req = _dispatch_browser_screenshot(req)
        elif req.action == LocalControlAction.OPEN_APP:
            req = _dispatch_subprocess_open_app(req)
        elif req.action == LocalControlAction.FOCUS_APP:
            req = _dispatch_subprocess_focus_app(req)
        elif req.action == LocalControlAction.LIST_WINDOWS:
            req = _dispatch_subprocess_list_windows(req)
        elif req.action == LocalControlAction.MOVE_MOUSE:
            req = _dispatch_move_mouse(req)
        elif req.action == LocalControlAction.OPEN_SCENE:
            req = _dispatch_open_scene(req)
        else:
            req.status = RequestStatus.FAILED
            req.error = f"unhandled action: {req.action.value}"
    except Exception as exc:
        req.status = RequestStatus.FAILED
        req.error = f"dispatch exception: {exc}"
        _log(f"dispatch error for {req.request_id}: {exc}")

    req.updated_at = _utcnow()
    store.put(req)
    if req.status == RequestStatus.COMPLETED:
        _log(f"COMPLETED {req.request_id}: {req.result}")
    elif req.status == RequestStatus.FAILED:
        _log(f"FAILED {req.request_id}: {req.error}")
    return req


# ─── Browser dispatch helpers ───────────────────────────────────────────────


def _dispatch_browser_open_url(req: LocalControlRequest) -> LocalControlRequest:
    from eos_ai.substrate.browser_agent import BrowserActionType, execute_browser_action

    url = req.payload.get("url", "")
    result = execute_browser_action(BrowserActionType.OPEN_URL, {"url": url})
    if result.ok:
        req.status = RequestStatus.COMPLETED
        req.result = f"opened: {result.data}"
    else:
        req.status = RequestStatus.FAILED
        req.error = f"browser open_url failed: {result.error}"
    return req


def _dispatch_browser_click(req: LocalControlRequest) -> LocalControlRequest:
    from eos_ai.substrate.browser_agent import BrowserActionType, execute_browser_action

    selector = req.payload.get("selector", "")
    result = execute_browser_action(BrowserActionType.CLICK, {"selector": selector})
    if result.ok:
        req.status = RequestStatus.COMPLETED
        req.result = f"clicked: {result.data}"
    else:
        req.status = RequestStatus.FAILED
        req.error = f"browser click failed: {result.error}"
    return req


def _dispatch_browser_type(req: LocalControlRequest) -> LocalControlRequest:
    from eos_ai.substrate.browser_agent import BrowserActionType, execute_browser_action

    selector = req.payload.get("selector", "")
    text = req.payload.get("text", "")
    result = execute_browser_action(
        BrowserActionType.TYPE_TEXT, {"selector": selector, "text": text}
    )
    if result.ok:
        req.status = RequestStatus.COMPLETED
        req.result = f"typed: {result.data}"
    else:
        req.status = RequestStatus.FAILED
        req.error = f"browser type failed: {result.error}"
    return req


def _dispatch_browser_press_keys(req: LocalControlRequest) -> LocalControlRequest:
    from eos_ai.substrate.browser_agent import BrowserActionType, execute_browser_action

    # Playwright keyboard.press expects key combos like "Control+c"
    keys = req.payload.get("keys", "")
    selector = req.payload.get("selector", "")
    if selector:
        result = execute_browser_action(
            BrowserActionType.TYPE_TEXT, {"selector": selector, "text": keys}
        )
    else:
        # No selector — use page-level keyboard press via extract workaround
        # For v1, we use the page directly through the agent
        try:
            from eos_ai.substrate.browser_agent import get_browser_agent

            agent = get_browser_agent()
            if agent._page and not agent._page.is_closed():
                agent._page.keyboard.press(keys)
                req.status = RequestStatus.COMPLETED
                req.result = f"pressed keys: {keys}"
            else:
                req.status = RequestStatus.FAILED
                req.error = "no active page for key press"
            return req
        except Exception as exc:
            req.status = RequestStatus.FAILED
            req.error = f"key press failed: {exc}"
            return req
    if result.ok:
        req.status = RequestStatus.COMPLETED
        req.result = f"keys pressed: {keys}"
    else:
        req.status = RequestStatus.FAILED
        req.error = f"key press failed: {result.error}"
    return req


def _dispatch_browser_screenshot(req: LocalControlRequest) -> LocalControlRequest:
    from eos_ai.substrate.browser_agent import BrowserActionType, execute_browser_action

    result = execute_browser_action(BrowserActionType.SCREENSHOT, req.payload)
    if result.ok:
        req.status = RequestStatus.COMPLETED
        req.result = f"screenshot saved: {result.data}"
    else:
        req.status = RequestStatus.FAILED
        req.error = f"screenshot failed: {result.error}"
    return req


# ─── Subprocess dispatch helpers ────────────────────────────────────────────


def _dispatch_subprocess_open_app(req: LocalControlRequest) -> LocalControlRequest:
    import shutil
    import subprocess

    app_id = req.payload.get("app_id", "")
    if not app_id:
        req.status = RequestStatus.FAILED
        req.error = "missing app_id"
        return req

    launcher = shutil.which("xdg-open")
    if not launcher:
        req.status = RequestStatus.FAILED
        req.error = "xdg-open not found — cannot launch apps"
        return req

    try:
        proc = subprocess.run(
            [launcher, app_id],
            capture_output=True,
            text=True,
            timeout=10,
        )
        if proc.returncode == 0:
            req.status = RequestStatus.COMPLETED
            req.result = f"launched: {app_id}"
        else:
            req.status = RequestStatus.FAILED
            req.error = f"launch failed (rc={proc.returncode}): {proc.stderr.strip()}"
    except subprocess.TimeoutExpired:
        req.status = RequestStatus.COMPLETED
        req.result = f"launched (detached): {app_id}"
    except Exception as exc:
        req.status = RequestStatus.FAILED
        req.error = f"launch error: {exc}"
    return req


def _dispatch_subprocess_focus_app(req: LocalControlRequest) -> LocalControlRequest:
    import shutil
    import subprocess

    app_id = req.payload.get("app_id", "")
    if not app_id:
        req.status = RequestStatus.FAILED
        req.error = "missing app_id"
        return req

    # Try wmctrl first, then xdotool
    wmctrl = shutil.which("wmctrl")
    xdotool = shutil.which("xdotool")

    if wmctrl:
        try:
            proc = subprocess.run(
                [wmctrl, "-a", app_id],
                capture_output=True,
                text=True,
                timeout=5,
            )
            if proc.returncode == 0:
                req.status = RequestStatus.COMPLETED
                req.result = f"focused: {app_id}"
                return req
        except Exception:
            pass

    if xdotool:
        try:
            proc = subprocess.run(
                [xdotool, "search", "--name", app_id, "windowactivate"],
                capture_output=True,
                text=True,
                timeout=5,
            )
            if proc.returncode == 0:
                req.status = RequestStatus.COMPLETED
                req.result = f"focused: {app_id}"
                return req
        except Exception:
            pass

    req.status = RequestStatus.FAILED
    req.error = f"no window manager tool available (wmctrl/xdotool) to focus {app_id}"
    return req


def _dispatch_subprocess_list_windows(req: LocalControlRequest) -> LocalControlRequest:
    import shutil
    import subprocess

    wmctrl = shutil.which("wmctrl")
    if wmctrl:
        try:
            proc = subprocess.run(
                [wmctrl, "-l"],
                capture_output=True,
                text=True,
                timeout=5,
            )
            req.status = RequestStatus.COMPLETED
            req.result = proc.stdout.strip() or "(no windows)"
            return req
        except Exception as exc:
            req.status = RequestStatus.FAILED
            req.error = f"wmctrl failed: {exc}"
            return req

    # Fallback: try xdotool
    xdotool = shutil.which("xdotool")
    if xdotool:
        try:
            proc = subprocess.run(
                [xdotool, "search", "--name", ""],
                capture_output=True,
                text=True,
                timeout=5,
            )
            req.status = RequestStatus.COMPLETED
            req.result = proc.stdout.strip() or "(no windows)"
            return req
        except Exception as exc:
            req.status = RequestStatus.FAILED
            req.error = f"xdotool failed: {exc}"
            return req

    req.status = RequestStatus.FAILED
    req.error = "no window manager tool available (wmctrl/xdotool)"
    return req


def _dispatch_move_mouse(req: LocalControlRequest) -> LocalControlRequest:
    import shutil

    xdotool = shutil.which("xdotool")
    if not xdotool:
        req.status = RequestStatus.FAILED
        req.error = "xdotool not available for mouse movement"
        return req

    import subprocess

    x = req.payload.get("x", 0)
    y = req.payload.get("y", 0)
    try:
        proc = subprocess.run(
            [xdotool, "mousemove", str(x), str(y)],
            capture_output=True,
            text=True,
            timeout=5,
        )
        if proc.returncode == 0:
            req.status = RequestStatus.COMPLETED
            req.result = f"mouse moved to ({x}, {y})"
        else:
            req.status = RequestStatus.FAILED
            req.error = f"mousemove failed: {proc.stderr.strip()}"
    except Exception as exc:
        req.status = RequestStatus.FAILED
        req.error = f"mousemove error: {exc}"
    return req


def _dispatch_open_scene(req: LocalControlRequest) -> LocalControlRequest:
    scene_name = req.payload.get("scene_name", "")
    try:
        from eos_ai.substrate.scenes import get_scene

        scene = get_scene(scene_name)
        if scene is None:
            req.status = RequestStatus.FAILED
            req.error = f"scene '{scene_name}' not found in registry"
            return req

        # Execute each scene step as a control request
        step_results = []
        for step in scene.steps:
            step_req = LocalControlRequest.new(
                action=_action_kind_to_control_action(step.kind),
                payload=step.payload if isinstance(step.payload, dict) else {},
                requested_by=req.requested_by,
            )
            store = LocalControlStore.default()
            store.put(step_req)
            executed_step = execute_control_request(step_req.request_id)
            step_results.append(
                f"{executed_step.action.value}: {executed_step.status.value}"
            )

        req.status = RequestStatus.COMPLETED
        req.result = (
            f"scene '{scene_name}' executed ({len(scene.steps)} steps): "
            + "; ".join(step_results)
        )
    except Exception as exc:
        req.status = RequestStatus.FAILED
        req.error = f"scene execution error: {exc}"
    return req


def _action_kind_to_control_action(kind) -> LocalControlAction:
    """Map an ActionKind value to a LocalControlAction."""
    _mapping = {
        "open_url": LocalControlAction.OPEN_URL,
        "open_scene": LocalControlAction.OPEN_SCENE,
        "focus_app": LocalControlAction.FOCUS_APP,
        "launch_app": LocalControlAction.OPEN_APP,
        "speak_text": LocalControlAction.LIST_WINDOWS,  # no-op fallback
        "play_sound": LocalControlAction.LIST_WINDOWS,  # no-op fallback
        "run_browser_flow": LocalControlAction.OPEN_URL,  # route to browser
    }
    try:
        kind_str = kind.value if hasattr(kind, "value") else str(kind)
    except Exception:
        kind_str = str(kind)
    return _mapping.get(kind_str, LocalControlAction.LIST_WINDOWS)
```

- [ ] **Step 4: Run tests to verify all pass (old + new)**

Run: `python3 /opt/OS/tests/substrate/test_local_control.py`
Expected: ALL PASSED

- [ ] **Step 5: Compile and format**

Run: `python3 -m py_compile eos_ai/substrate/local_control.py && ruff format eos_ai/substrate/local_control.py`

- [ ] **Step 6: Commit**

```bash
cd /opt/OS && git add eos_ai/substrate/local_control.py tests/substrate/test_local_control.py && git commit -m "feat: replace local_control stub with real browser/subprocess dispatch"
```

---

## Task 3: ExecutionBridge — Immediate Execution from EAResponse

**Files:**
- Create: `eos_ai/platforms/eos/execution_bridge.py`
- Create: `tests/platforms/eos/test_execution_bridge.py`

### Step-by-step

- [ ] **Step 1: Write the test file**

```python
"""Execution bridge tests — immediate execution from EAResponse."""

import sys
sys.path.insert(0, "/opt/OS")

import pytest
from eos_ai.platforms.eos.execution_bridge import (
    ExecutionBridgeResult,
    execute_created_work_immediately,
)
from eos_ai.substrate.task_system import (
    Task,
    TaskExecutionPolicy,
    TaskStatus,
    TaskStore,
    create_task,
)
from eos_ai.substrate.task_pipeline import PipelineStore


def _reset():
    TaskStore._default = None
    PipelineStore._default = None


class TestExecutionBridge:
    def setup_method(self):
        _reset()

    def teardown_method(self):
        _reset()

    def test_result_dataclass(self):
        result = ExecutionBridgeResult(
            executed_task_ids=["t1"],
            executed_pipeline_ids=[],
            blocked_task_ids=[],
            execution_summaries={"t1": "completed"},
            errors={},
        )
        d = result.to_dict()
        assert d["executed_task_ids"] == ["t1"]
        assert d["errors"] == {}

    def test_empty_input_returns_empty_result(self):
        result = execute_created_work_immediately(
            task_ids=[],
            pipeline_ids=[],
            dry_run=True,
        )
        assert result.executed_task_ids == []
        assert result.executed_pipeline_ids == []

    def test_autonomous_task_executes(self):
        task = create_task("build the landing page")
        assert task.execution_policy == TaskExecutionPolicy.AUTONOMOUS
        result = execute_created_work_immediately(
            task_ids=[task.task_id],
            pipeline_ids=[],
            dry_run=True,
        )
        assert task.task_id in result.executed_task_ids

    def test_non_autonomous_task_blocked(self):
        task = create_task("deploy production database migration")
        if task.execution_policy != TaskExecutionPolicy.AUTONOMOUS:
            result = execute_created_work_immediately(
                task_ids=[task.task_id],
                pipeline_ids=[],
                dry_run=True,
            )
            assert task.task_id in result.blocked_task_ids

    def test_missing_task_reported_as_error(self):
        result = execute_created_work_immediately(
            task_ids=["nonexistent_task_id"],
            pipeline_ids=[],
            dry_run=True,
        )
        assert "nonexistent_task_id" in result.errors

    def test_local_first_preference(self):
        """When local is available, tasks should prefer local execution."""
        task = create_task("write unit tests")
        result = execute_created_work_immediately(
            task_ids=[task.task_id],
            pipeline_ids=[],
            dry_run=True,
            prefer_local=True,
        )
        # In dry_run, the task gets routed but not dispatched
        assert task.task_id in result.executed_task_ids

    def test_to_dict_roundtrip(self):
        result = ExecutionBridgeResult(
            executed_task_ids=["t1", "t2"],
            executed_pipeline_ids=["p1"],
            blocked_task_ids=["t3"],
            execution_summaries={"t1": "ok", "t2": "ok", "p1": "done"},
            errors={"t3": "needs approval"},
        )
        d = result.to_dict()
        assert len(d["executed_task_ids"]) == 2
        assert d["blocked_task_ids"] == ["t3"]
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd /opt/OS && python3 -m pytest tests/platforms/eos/test_execution_bridge.py -v`
Expected: ImportError — execution_bridge does not exist yet.

- [ ] **Step 3: Write execution_bridge.py**

```python
"""
Execution bridge — immediate execution of EA-created work.

When EA creates tasks or pipelines during a live conversation, this bridge
executes them immediately through existing substrate infrastructure instead
of waiting for background execution loops.

Design rules:
- Reuses existing task_execution.execute_task() and pipeline_execution.execute_pipeline().
- Does NOT duplicate routing logic — delegates to capability_routing.
- Local-first: reads station_presence to prefer local execution when available.
- Best-effort: individual task/pipeline failures captured, never block the response.
- Returns structured ExecutionBridgeResult for the live runtime to format.
"""

from __future__ import annotations

import sys
from dataclasses import dataclass, field
from typing import Any, Optional

from eos_ai.platforms.eos.roles import EOSRole


def _log(msg: str) -> None:
    print(f"[platform.eos.execution_bridge] {msg}", file=sys.stderr)


# ─── Result Model ───────────────────────────────────────────────────────────


@dataclass
class ExecutionBridgeResult:
    """Structured result from immediate execution."""

    executed_task_ids: list[str] = field(default_factory=list)
    executed_pipeline_ids: list[str] = field(default_factory=list)
    blocked_task_ids: list[str] = field(default_factory=list)
    execution_summaries: dict[str, str] = field(default_factory=dict)
    errors: dict[str, str] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "executed_task_ids": self.executed_task_ids,
            "executed_pipeline_ids": self.executed_pipeline_ids,
            "blocked_task_ids": self.blocked_task_ids,
            "execution_summaries": self.execution_summaries,
            "errors": self.errors,
        }


# ─── Helpers ────────────────────────────────────────────────────────────────


def _is_local_available() -> bool:
    """Check station presence for local availability."""
    try:
        from eos_ai.substrate.station_presence import StationPresenceStore

        presence = StationPresenceStore.default().get()
        return presence.local_available if presence else False
    except Exception:
        return False


def _get_operator_session():
    """Get current operator session for routing context."""
    try:
        from eos_ai.substrate.operator_session import OperatorSessionStore

        return OperatorSessionStore.default().get()
    except Exception:
        return None


# ─── Main Entry Point ──────────────────────────────────────────────────────


def execute_created_work_immediately(
    task_ids: list[str],
    pipeline_ids: list[str],
    *,
    dry_run: bool = False,
    prefer_local: bool = True,
) -> ExecutionBridgeResult:
    """Execute EA-created tasks and pipelines immediately.

    Uses existing substrate execution infrastructure:
    - task_execution.execute_task() for tasks
    - pipeline_execution.execute_pipeline() for pipelines

    Local execution is preferred when the local station is available.
    Non-autonomous tasks (NEEDS_OPERATOR, NEEDS_APPROVAL) are reported
    as blocked — they are not executed.

    Args:
        task_ids: Substrate task IDs to execute.
        pipeline_ids: Substrate pipeline IDs to execute.
        dry_run: If True, route but skip actual dispatch.
        prefer_local: If True, use local node when available.

    Returns:
        ExecutionBridgeResult with execution outcomes.
    """
    result = ExecutionBridgeResult()

    if not task_ids and not pipeline_ids:
        return result

    # Resolve execution context once
    local_available = prefer_local and _is_local_available()
    session = _get_operator_session()

    # Execute tasks
    for task_id in task_ids:
        _execute_single_task(
            task_id,
            result,
            session=session,
            local_available=local_available,
            dry_run=dry_run,
        )

    # Execute pipelines
    for pipeline_id in pipeline_ids:
        _execute_single_pipeline(
            pipeline_id,
            result,
            session=session,
            local_available=local_available,
            dry_run=dry_run,
        )

    return result


# ─── Task Execution ─────────────────────────────────────────────────────────


def _execute_single_task(
    task_id: str,
    result: ExecutionBridgeResult,
    *,
    session=None,
    local_available: bool = False,
    dry_run: bool = False,
) -> None:
    """Execute one task through substrate infrastructure."""
    try:
        from eos_ai.substrate.task_system import (
            TaskExecutionPolicy,
            TaskStatus,
            TaskStore,
        )

        store = TaskStore.default()
        task = store.get(task_id)
        if task is None:
            result.errors[task_id] = "task not found in store"
            return

        # Non-autonomous tasks are blocked — do not execute
        if task.execution_policy != TaskExecutionPolicy.AUTONOMOUS:
            result.blocked_task_ids.append(task_id)
            result.execution_summaries[task_id] = (
                f"blocked: {task.execution_policy.value} "
                f"({task.requires_input_prompt or 'awaiting operator'})"
            )
            return

        # Only execute tasks in READY state
        if task.status != TaskStatus.READY:
            result.errors[task_id] = (
                f"task not in READY state: {task.status.value}"
            )
            return

        # Execute through existing infrastructure
        from eos_ai.substrate.task_execution import execute_task

        executed = execute_task(
            task,
            session,
            local_available=local_available,
            dry_run=dry_run,
        )

        result.executed_task_ids.append(task_id)
        if executed.execution_result:
            result.execution_summaries[task_id] = executed.execution_result[:200]
        elif executed.execution_error:
            result.execution_summaries[task_id] = f"error: {executed.execution_error}"
        else:
            result.execution_summaries[task_id] = f"status: {executed.status.value}"

    except Exception as exc:
        result.errors[task_id] = f"execution exception: {exc}"
        _log(f"task {task_id} execution failed: {exc}")


# ─── Pipeline Execution ─────────────────────────────────────────────────────


def _execute_single_pipeline(
    pipeline_id: str,
    result: ExecutionBridgeResult,
    *,
    session=None,
    local_available: bool = False,
    dry_run: bool = False,
) -> None:
    """Execute one pipeline through substrate infrastructure."""
    try:
        from eos_ai.substrate.task_pipeline import PipelineStore

        store = PipelineStore.default()
        pipeline = store.get(pipeline_id)
        if pipeline is None:
            result.errors[pipeline_id] = "pipeline not found in store"
            return

        if pipeline.is_terminal():
            result.errors[pipeline_id] = (
                f"pipeline in terminal state: {pipeline.status.value}"
            )
            return

        from eos_ai.substrate.pipeline_execution import execute_pipeline

        executed = execute_pipeline(
            pipeline,
            session,
            local_available=local_available,
            dry_run=dry_run,
            advance_all=True,
        )

        result.executed_pipeline_ids.append(pipeline_id)
        result.execution_summaries[pipeline_id] = (
            f"{executed.status.value} "
            f"({len(executed.completed_steps())}/{len(executed.steps)} steps)"
        )

    except Exception as exc:
        result.errors[pipeline_id] = f"execution exception: {exc}"
        _log(f"pipeline {pipeline_id} execution failed: {exc}")


__all__ = [
    "ExecutionBridgeResult",
    "execute_created_work_immediately",
]
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd /opt/OS && python3 -m pytest tests/platforms/eos/test_execution_bridge.py -v`
Expected: All tests PASS

- [ ] **Step 5: Compile and format**

Run: `python3 -m py_compile eos_ai/platforms/eos/execution_bridge.py && ruff format eos_ai/platforms/eos/execution_bridge.py tests/platforms/eos/test_execution_bridge.py`

- [ ] **Step 6: Commit**

```bash
cd /opt/OS && git add eos_ai/platforms/eos/execution_bridge.py tests/platforms/eos/test_execution_bridge.py && git commit -m "feat: add execution bridge — immediate task/pipeline execution from EA"
```

---

## Task 4: EALiveRuntime — Conversational Runtime State Machine

**Files:**
- Create: `eos_ai/platforms/eos/live_runtime.py`
- Create: `tests/platforms/eos/test_live_runtime.py`

### Step-by-step

- [ ] **Step 1: Write the test file**

```python
"""Live runtime tests — conversational state machine for EA."""

import sys
sys.path.insert(0, "/opt/OS")

import pytest
from eos_ai.platforms.eos.live_runtime import (
    EALiveRuntime,
    LiveRuntimeResult,
    RuntimeState,
    handle_live_user_utterance,
    get_live_runtime,
    pause_live_runtime,
    resume_live_runtime,
    stop_live_runtime,
    format_live_progress_update,
)
from eos_ai.substrate.live_sessions import LiveSessionStore
from eos_ai.substrate.task_system import TaskStore
from eos_ai.substrate.task_pipeline import PipelineStore


def _reset():
    EALiveRuntime._default = None
    LiveSessionStore._default = None
    TaskStore._default = None
    PipelineStore._default = None


class TestRuntimeState:
    def test_states_exist(self):
        assert RuntimeState.IDLE
        assert RuntimeState.LISTENING
        assert RuntimeState.EXECUTING
        assert RuntimeState.SPEAKING
        assert RuntimeState.PAUSED
        assert RuntimeState.STOPPED


class TestControlPhraseInterception:
    def setup_method(self):
        _reset()

    def teardown_method(self):
        _reset()

    def test_pause_intercepted(self):
        result = handle_live_user_utterance("pause")
        assert result.is_control_action
        rt = get_live_runtime()
        assert rt.state == RuntimeState.PAUSED

    def test_hold_on_intercepted(self):
        result = handle_live_user_utterance("hold on")
        assert result.is_control_action
        rt = get_live_runtime()
        assert rt.state == RuntimeState.PAUSED

    def test_wait_intercepted(self):
        result = handle_live_user_utterance("wait")
        assert result.is_control_action

    def test_stop_intercepted(self):
        result = handle_live_user_utterance("stop")
        assert result.is_control_action
        rt = get_live_runtime()
        assert rt.state == RuntimeState.STOPPED

    def test_cancel_intercepted(self):
        result = handle_live_user_utterance("cancel")
        assert result.is_control_action

    def test_continue_intercepted(self):
        # First pause, then continue
        handle_live_user_utterance("pause")
        result = handle_live_user_utterance("continue")
        assert result.is_control_action
        rt = get_live_runtime()
        assert rt.state == RuntimeState.LISTENING

    def test_resume_intercepted(self):
        handle_live_user_utterance("pause")
        result = handle_live_user_utterance("resume")
        assert result.is_control_action

    def test_keep_going_intercepted(self):
        handle_live_user_utterance("pause")
        result = handle_live_user_utterance("keep going")
        assert result.is_control_action

    def test_normal_utterance_not_intercepted(self):
        result = handle_live_user_utterance("what's the status?")
        assert not result.is_control_action
        assert result.spoken_text  # EA should respond


class TestLiveSessionBinding:
    def setup_method(self):
        _reset()

    def teardown_method(self):
        _reset()

    def test_session_created_on_first_utterance(self):
        result = handle_live_user_utterance("catch me up")
        assert result.live_session_id is not None

    def test_session_reused_on_subsequent_utterance(self):
        r1 = handle_live_user_utterance("what's happening?")
        r2 = handle_live_user_utterance("give me details")
        assert r1.live_session_id == r2.live_session_id

    def test_explicit_session_id_used(self):
        result = handle_live_user_utterance(
            "status",
            session_id="custom_session_123",
        )
        # Should use the provided session_id for EA routing
        assert result.live_session_id is not None


class TestExecutionIntegration:
    def setup_method(self):
        _reset()

    def teardown_method(self):
        _reset()

    def test_execution_request_creates_tasks(self):
        result = handle_live_user_utterance(
            "build the API endpoint",
            dry_run=True,
        )
        assert len(result.created_task_ids) > 0

    def test_status_request_no_tasks(self):
        result = handle_live_user_utterance("what's the status?")
        assert len(result.created_task_ids) == 0


class TestPauseResume:
    def setup_method(self):
        _reset()

    def teardown_method(self):
        _reset()

    def test_pause_then_resume(self):
        handle_live_user_utterance("build something", dry_run=True)
        pause_result = pause_live_runtime()
        assert pause_result["state"] == "paused"
        resume_result = resume_live_runtime()
        assert resume_result["state"] == "listening"

    def test_stop_runtime(self):
        handle_live_user_utterance("status")
        result = stop_live_runtime()
        assert result["state"] == "stopped"


class TestLiveRuntimeResult:
    def test_result_to_dict(self):
        result = LiveRuntimeResult(
            spoken_text="Done.",
            created_task_ids=["t1"],
            created_pipeline_ids=[],
            executed_actions_summary={"t1": "completed"},
            blocked_items=[],
            live_session_id="lsess_abc",
            is_control_action=False,
        )
        d = result.to_dict()
        assert d["spoken_text"] == "Done."
        assert d["live_session_id"] == "lsess_abc"


class TestProgressFormatting:
    def test_format_progress(self):
        text = format_live_progress_update(
            action="opening browser",
            status="completed",
        )
        assert "opening browser" in text.lower() or "completed" in text.lower()
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd /opt/OS && python3 -m pytest tests/platforms/eos/test_live_runtime.py -v`
Expected: ImportError — live_runtime does not exist yet.

- [ ] **Step 3: Write live_runtime.py**

```python
"""
EA Live Runtime — conversational runtime loop for the EOS platform.

This is the primary entrypoint for natural founder interaction. It wraps
the EA orchestrator with:
1. Conversational control phrase interception (pause/stop/continue)
2. Immediate execution via ExecutionBridge
3. Live session binding and lifecycle management
4. Real-time progress formatting

Design rules:
- Thin EOS platform wrapper — no logic leaks into substrate.
- EA remains sole founder-facing interface.
- Control phrases intercepted BEFORE intent routing.
- Immediate execution ONLY through ExecutionBridge.
- State survives across utterances within a session.
"""

from __future__ import annotations

import re
import sys
import threading
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Optional


def _log(msg: str) -> None:
    print(f"[platform.eos.live_runtime] {msg}", file=sys.stderr)


def _utcnow() -> str:
    return datetime.now(timezone.utc).isoformat()


def _new_id() -> str:
    return f"eart_{uuid.uuid4().hex[:12]}"


# ─── State Machine ──────────────────────────────────────────────────────────


class RuntimeState(str, Enum):
    """Runtime lifecycle states."""

    IDLE = "idle"
    LISTENING = "listening"
    EXECUTING = "executing"
    SPEAKING = "speaking"
    PAUSED = "paused"
    STOPPED = "stopped"


# ─── Control Phrase Patterns ────────────────────────────────────────────────

# Compiled once. Order matters: more specific phrases first.
_PAUSE_PHRASES = re.compile(
    r"^(pause|hold on|wait|one moment|hang on|one sec)\.?$",
    re.IGNORECASE,
)
_STOP_PHRASES = re.compile(
    r"^(stop|cancel|abort|quit|end|shut down)\.?$",
    re.IGNORECASE,
)
_RESUME_PHRASES = re.compile(
    r"^(continue|resume|keep going|go ahead|carry on|go on|proceed)\.?$",
    re.IGNORECASE,
)


def _classify_control_phrase(text: str) -> Optional[str]:
    """Classify text as a control phrase. Returns 'pause', 'stop', 'resume', or None."""
    stripped = text.strip()
    if _PAUSE_PHRASES.match(stripped):
        return "pause"
    if _STOP_PHRASES.match(stripped):
        return "stop"
    if _RESUME_PHRASES.match(stripped):
        return "resume"
    return None


# ─── Result Dataclass ───────────────────────────────────────────────────────


@dataclass
class LiveRuntimeResult:
    """Structured result from a live runtime interaction."""

    spoken_text: str = ""
    created_task_ids: list[str] = field(default_factory=list)
    created_pipeline_ids: list[str] = field(default_factory=list)
    executed_actions_summary: dict[str, str] = field(default_factory=dict)
    blocked_items: list[str] = field(default_factory=list)
    live_session_id: Optional[str] = None
    is_control_action: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "spoken_text": self.spoken_text,
            "created_task_ids": self.created_task_ids,
            "created_pipeline_ids": self.created_pipeline_ids,
            "executed_actions_summary": self.executed_actions_summary,
            "blocked_items": self.blocked_items,
            "live_session_id": self.live_session_id,
            "is_control_action": self.is_control_action,
        }


# ─── Live Runtime ───────────────────────────────────────────────────────────


@dataclass
class EALiveRuntime:
    """Conversational runtime state machine for EA.

    Manages the lifecycle of a live interaction session, including
    control phrase interception, immediate execution, and live
    session binding.
    """

    runtime_id: str = field(default_factory=_new_id)
    live_session_id: Optional[str] = None
    state: RuntimeState = RuntimeState.IDLE
    current_task_ids: list[str] = field(default_factory=list)
    current_pipeline_ids: list[str] = field(default_factory=list)
    current_control_request_ids: list[str] = field(default_factory=list)
    last_user_utterance: Optional[str] = None
    last_ea_response: Optional[Any] = None
    updated_at: str = field(default_factory=_utcnow)

    _default: Optional["EALiveRuntime"] = None
    _default_lock = threading.Lock()

    @classmethod
    def default(cls) -> "EALiveRuntime":
        if cls._default is None:
            with cls._default_lock:
                if cls._default is None:
                    cls._default = cls()
        return cls._default

    @classmethod
    def reset_default_for_tests(cls) -> None:
        with cls._default_lock:
            cls._default = None

    # ── Live Session Management ─────────────────────────────────────────

    def _ensure_live_session(self) -> Optional[str]:
        """Ensure we have an active live session. Create one if needed."""
        if self.live_session_id:
            # Verify it still exists and is active
            try:
                from eos_ai.substrate.live_sessions import (
                    LiveSessionState,
                    LiveSessionStore,
                )

                session = LiveSessionStore.default().get(self.live_session_id)
                if session and session.state not in (
                    LiveSessionState.ENDED,
                    LiveSessionState.FAILED,
                ):
                    return self.live_session_id
            except Exception:
                pass

        # Create a new live session
        try:
            from eos_ai.platforms.eos.discord_hook import create_ea_live_session

            session_id = create_ea_live_session(
                title="EA Live Session",
                session_type="LOCAL",
            )
            if session_id:
                # Start it immediately
                try:
                    from eos_ai.substrate.live_sessions import start_live_session

                    start_live_session(session_id)
                except Exception as exc:
                    _log(f"start live session failed: {exc}")

                self.live_session_id = session_id
                return session_id
        except Exception as exc:
            _log(f"live session creation failed: {exc}")
        return self.live_session_id

    def _attach_work_to_session(
        self, task_ids: list[str], pipeline_ids: list[str]
    ) -> None:
        """Attach created work to the current live session."""
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

    # ── Control Handlers ────────────────────────────────────────────────

    def _handle_pause(self) -> LiveRuntimeResult:
        self.state = RuntimeState.PAUSED
        self.updated_at = _utcnow()

        # Pause the live session if active
        if self.live_session_id:
            try:
                from eos_ai.substrate.live_sessions import pause_live_session

                pause_live_session(self.live_session_id)
            except Exception:
                pass

        return LiveRuntimeResult(
            spoken_text="Paused. Say continue when you're ready.",
            live_session_id=self.live_session_id,
            is_control_action=True,
        )

    def _handle_stop(self) -> LiveRuntimeResult:
        self.state = RuntimeState.STOPPED
        self.updated_at = _utcnow()

        # End the live session
        if self.live_session_id:
            try:
                from eos_ai.substrate.live_sessions import end_live_session

                end_live_session(self.live_session_id)
            except Exception:
                pass

        return LiveRuntimeResult(
            spoken_text="Stopped. Session ended.",
            live_session_id=self.live_session_id,
            is_control_action=True,
        )

    def _handle_resume(self) -> LiveRuntimeResult:
        self.state = RuntimeState.LISTENING
        self.updated_at = _utcnow()

        # Resume the live session
        if self.live_session_id:
            try:
                from eos_ai.substrate.live_sessions import resume_live_session

                resume_live_session(self.live_session_id)
            except Exception:
                pass

        # Resume paused pipelines
        resumed_pipelines = []
        for pid in self.current_pipeline_ids:
            try:
                from eos_ai.substrate.pipeline_execution import resume_pipeline

                resume_pipeline(pid, dry_run=True)
                resumed_pipelines.append(pid)
            except Exception:
                pass

        extra = f" Resumed {len(resumed_pipelines)} pipeline(s)." if resumed_pipelines else ""
        return LiveRuntimeResult(
            spoken_text=f"Resuming.{extra}",
            live_session_id=self.live_session_id,
            is_control_action=True,
        )

    # ── Core Utterance Handler ──────────────────────────────────────────

    def handle_utterance(
        self,
        text: str,
        *,
        session_id: Optional[str] = None,
        dry_run: bool = False,
    ) -> LiveRuntimeResult:
        """Process a founder utterance through the live runtime.

        Flow:
        1. Check for control phrases (before intent routing)
        2. If control phrase → update state, return immediately
        3. Ensure live session exists
        4. Route through EA orchestrator
        5. If tasks created → execute immediately via bridge
        6. Attach work to live session
        7. Return structured result
        """
        self.last_user_utterance = text
        self.updated_at = _utcnow()

        # 1. Control phrase interception (BEFORE intent routing)
        control = _classify_control_phrase(text)
        if control == "pause":
            return self._handle_pause()
        elif control == "stop":
            return self._handle_stop()
        elif control == "resume":
            return self._handle_resume()

        # Guard: if stopped, require explicit resume
        if self.state == RuntimeState.STOPPED:
            return LiveRuntimeResult(
                spoken_text="Session is stopped. Say resume to restart.",
                live_session_id=self.live_session_id,
                is_control_action=False,
            )

        # Guard: if paused, remind user
        if self.state == RuntimeState.PAUSED:
            return LiveRuntimeResult(
                spoken_text="I'm paused. Say continue to resume, or stop to end.",
                live_session_id=self.live_session_id,
                is_control_action=False,
            )

        # 2. Transition to listening
        self.state = RuntimeState.LISTENING

        # 3. Ensure live session
        self._ensure_live_session()

        # 4. Route through EA orchestrator
        try:
            from eos_ai.platforms.eos.ea_orchestrator import handle_founder_message

            ea_response = handle_founder_message(text, session_id=session_id)
            self.last_ea_response = ea_response
        except Exception as exc:
            _log(f"EA orchestrator failed: {exc}")
            self.state = RuntimeState.LISTENING
            return LiveRuntimeResult(
                spoken_text=f"Something went wrong: {exc}",
                live_session_id=self.live_session_id,
            )

        # 5. Immediate execution if tasks were created
        created_task_ids = ea_response.created_task_ids
        created_pipeline_ids = ea_response.created_pipeline_ids
        execution_summary: dict[str, str] = {}
        blocked_items = list(ea_response.blocked_items)

        if created_task_ids or created_pipeline_ids:
            self.state = RuntimeState.EXECUTING
            try:
                from eos_ai.platforms.eos.execution_bridge import (
                    execute_created_work_immediately,
                )

                bridge_result = execute_created_work_immediately(
                    task_ids=created_task_ids,
                    pipeline_ids=created_pipeline_ids,
                    dry_run=dry_run,
                )
                execution_summary = bridge_result.execution_summaries
                blocked_items.extend(
                    f"task:{tid}" for tid in bridge_result.blocked_task_ids
                )
            except Exception as exc:
                _log(f"execution bridge failed: {exc}")
                execution_summary = {"error": str(exc)}

        # Track current work
        self.current_task_ids = created_task_ids
        self.current_pipeline_ids = created_pipeline_ids

        # 6. Attach work to live session
        self._attach_work_to_session(created_task_ids, created_pipeline_ids)

        # 7. Transition to speaking / listening
        self.state = RuntimeState.LISTENING
        self.updated_at = _utcnow()

        return LiveRuntimeResult(
            spoken_text=ea_response.response_text,
            created_task_ids=created_task_ids,
            created_pipeline_ids=created_pipeline_ids,
            executed_actions_summary=execution_summary,
            blocked_items=blocked_items,
            live_session_id=self.live_session_id,
        )


# ─── Module-Level API ──────────────────────────────────────────────────────


def get_live_runtime() -> EALiveRuntime:
    """Get the singleton live runtime instance."""
    return EALiveRuntime.default()


def handle_live_user_utterance(
    text: str,
    *,
    session_id: Optional[str] = None,
    dry_run: bool = False,
) -> LiveRuntimeResult:
    """Primary entrypoint — process a founder utterance through the live runtime."""
    runtime = get_live_runtime()
    return runtime.handle_utterance(text, session_id=session_id, dry_run=dry_run)


def pause_live_runtime() -> dict[str, str]:
    """Pause the live runtime."""
    runtime = get_live_runtime()
    result = runtime._handle_pause()
    return {"state": runtime.state.value, "message": result.spoken_text}


def resume_live_runtime() -> dict[str, str]:
    """Resume the live runtime."""
    runtime = get_live_runtime()
    result = runtime._handle_resume()
    return {"state": runtime.state.value, "message": result.spoken_text}


def stop_live_runtime() -> dict[str, str]:
    """Stop the live runtime."""
    runtime = get_live_runtime()
    result = runtime._handle_stop()
    return {"state": runtime.state.value, "message": result.spoken_text}


def interrupt_live_runtime(new_text: str) -> LiveRuntimeResult:
    """Interrupt current activity with a new utterance.

    Preserves runtime state — does not destroy active tasks/pipelines.
    """
    runtime = get_live_runtime()
    # If currently executing or speaking, preserve state
    if runtime.state in (RuntimeState.EXECUTING, RuntimeState.SPEAKING):
        runtime.state = RuntimeState.LISTENING
    return runtime.handle_utterance(new_text)


# ─── Progress Formatting ──────────────────────────────────────────────────


def format_live_progress_update(
    *,
    action: str,
    status: str = "in_progress",
    detail: Optional[str] = None,
) -> str:
    """Format a concise progress update for live delivery.

    Examples:
        "Opening the browser."
        "Found three relevant results."
        "Blocked on your input."
    """
    if status == "completed":
        return f"{action.capitalize()} — done."
    elif status == "blocked":
        return f"{action.capitalize()} — blocked. {detail or 'Need your input.'}"
    elif status == "failed":
        return f"{action.capitalize()} — failed. {detail or ''}"
    else:
        return f"{action.capitalize()}..."


__all__ = [
    "EALiveRuntime",
    "LiveRuntimeResult",
    "RuntimeState",
    "get_live_runtime",
    "handle_live_user_utterance",
    "pause_live_runtime",
    "resume_live_runtime",
    "stop_live_runtime",
    "interrupt_live_runtime",
    "format_live_progress_update",
]
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd /opt/OS && python3 -m pytest tests/platforms/eos/test_live_runtime.py -v`
Expected: All tests PASS

- [ ] **Step 5: Compile and format**

Run: `python3 -m py_compile eos_ai/platforms/eos/live_runtime.py && ruff format eos_ai/platforms/eos/live_runtime.py tests/platforms/eos/test_live_runtime.py`

- [ ] **Step 6: Commit**

```bash
cd /opt/OS && git add eos_ai/platforms/eos/live_runtime.py tests/platforms/eos/test_live_runtime.py && git commit -m "feat: add EA live runtime — conversational state machine with immediate execution"
```

---

## Task 5: Discord Hook Bridge + __init__.py Exports

**Files:**
- Modify: `eos_ai/platforms/eos/discord_hook.py` (add live runtime bridge function)
- Modify: `eos_ai/platforms/eos/__init__.py` (export new symbols)

### Step-by-step

- [ ] **Step 1: Add live runtime bridge to discord_hook.py**

Append to the end of `discord_hook.py` (before the implicit end of file):

```python
# ─── Live runtime bridge ─────────────────────────────────────────────────────


def handle_eos_discord_live_message(
    text: str,
    *,
    session_id: Optional[str] = None,
    dry_run: bool = False,
) -> str:
    """
    Process a founder Discord message through the EA live runtime.

    Unlike handle_eos_discord_message (which uses the EA orchestrator directly),
    this routes through the live runtime for control phrase interception,
    immediate execution, and live session binding.

    Falls back to handle_eos_discord_message if the live runtime fails.
    """
    try:
        from eos_ai.platforms.eos.live_runtime import handle_live_user_utterance

        result = handle_live_user_utterance(
            text, session_id=session_id, dry_run=dry_run
        )
        return result.spoken_text

    except Exception as exc:
        _log(f"live runtime failed, falling back to direct EA: {exc}")
        return handle_eos_discord_message(text, session_id=session_id)
```

- [ ] **Step 2: Update __init__.py exports**

Add the following imports and __all__ entries to `eos_ai/platforms/eos/__init__.py`:

After the existing discord_hook imports, add:

```python
# Live runtime
from eos_ai.platforms.eos.live_runtime import (
    EALiveRuntime,
    LiveRuntimeResult,
    RuntimeState,
    get_live_runtime,
    handle_live_user_utterance,
    pause_live_runtime,
    resume_live_runtime,
    stop_live_runtime,
    interrupt_live_runtime,
    format_live_progress_update,
)

# Execution bridge
from eos_ai.platforms.eos.execution_bridge import (
    ExecutionBridgeResult,
    execute_created_work_immediately,
)

# Discord live bridge
from eos_ai.platforms.eos.discord_hook import handle_eos_discord_live_message
```

Add to `__all__`:
```python
    # Live runtime
    "EALiveRuntime",
    "LiveRuntimeResult",
    "RuntimeState",
    "get_live_runtime",
    "handle_live_user_utterance",
    "pause_live_runtime",
    "resume_live_runtime",
    "stop_live_runtime",
    "interrupt_live_runtime",
    "format_live_progress_update",
    # Execution bridge
    "ExecutionBridgeResult",
    "execute_created_work_immediately",
    # Discord live bridge
    "handle_eos_discord_live_message",
```

- [ ] **Step 3: Compile and format**

Run: `python3 -m py_compile eos_ai/platforms/eos/__init__.py && python3 -m py_compile eos_ai/platforms/eos/discord_hook.py && ruff format eos_ai/platforms/eos/__init__.py eos_ai/platforms/eos/discord_hook.py`

- [ ] **Step 4: Verify imports work**

Run: `python3 -c "from eos_ai.platforms.eos import handle_live_user_utterance, ExecutionBridgeResult, handle_eos_discord_live_message; print('all imports OK')"`
Expected: "all imports OK"

- [ ] **Step 5: Commit**

```bash
cd /opt/OS && git add eos_ai/platforms/eos/discord_hook.py eos_ai/platforms/eos/__init__.py && git commit -m "feat: add Discord live bridge + export live runtime and execution bridge"
```

---

## Task 6: Pipeline Step Execution — Browser/Machine Action Dispatch

**Files:**
- Modify: `eos_ai/substrate/pipeline_execution.py:46-147` (add action type detection to `_execute_step`)

### Step-by-step

- [ ] **Step 1: Add action type detection to _execute_step**

In `pipeline_execution.py`, add a check before the tmux dispatch section (after the routing block around line 92, before `if dry_run:`). Insert a helper function and modify the dispatch logic:

Add this helper function before `_execute_step`:

```python
# ─── Action Type Detection ──────────────────────────────────────────────────

# Keywords that signal a step should use local control instead of tmux
_BROWSER_KEYWORDS = frozenset({
    "browser_open", "browser_click", "browser_type", "browser_extract",
    "open_url", "navigate", "screenshot",
})
_MACHINE_KEYWORDS = frozenset({
    "machine_open_app", "machine_focus_app", "machine_open_scene",
    "machine_type_text", "machine_click", "machine_press_keys",
    "open_app", "focus_app", "open_scene",
})


def _detect_local_control_action(step: PipelineStep) -> Optional[tuple[str, dict]]:
    """Check if a step title/description maps to a local control action.

    Returns (action_value, payload) if detected, None otherwise.
    Step titles can use prefixed action names like 'browser_open: https://...'
    or 'machine_open_app: vscode'.
    """
    title_lower = (step.title or "").lower().strip()

    # Check for explicit action prefix format: "action_type: payload"
    for keyword in _BROWSER_KEYWORDS | _MACHINE_KEYWORDS:
        if title_lower.startswith(keyword):
            # Extract payload from after the colon
            rest = title_lower[len(keyword):].lstrip(": ").strip()
            return _map_keyword_to_action(keyword, rest, step)

    return None


def _map_keyword_to_action(
    keyword: str, rest: str, step: PipelineStep
) -> Optional[tuple[str, dict]]:
    """Map a detected keyword to a LocalControlAction value and payload."""
    mapping = {
        "browser_open": ("open_url", {"url": rest}),
        "open_url": ("open_url", {"url": rest}),
        "navigate": ("open_url", {"url": rest}),
        "browser_click": ("click_mouse", {"selector": rest}),
        "browser_type": ("type_text", {"selector": rest.split(" ", 1)[0] if " " in rest else rest, "text": rest.split(" ", 1)[1] if " " in rest else ""}),
        "browser_extract": ("read_screen_state", {"selector": rest}),
        "screenshot": ("read_screen_state", {}),
        "machine_open_app": ("open_app", {"app_id": rest}),
        "open_app": ("open_app", {"app_id": rest}),
        "machine_focus_app": ("focus_app", {"app_id": rest}),
        "focus_app": ("focus_app", {"app_id": rest}),
        "machine_open_scene": ("open_scene", {"scene_name": rest}),
        "open_scene": ("open_scene", {"scene_name": rest}),
        "machine_type_text": ("type_text", {"text": rest}),
        "machine_click": ("click_mouse", {"selector": rest}),
        "machine_press_keys": ("press_keys", {"keys": rest}),
    }
    result = mapping.get(keyword)
    if result:
        return result
    return None
```

Then in `_execute_step`, after the routing block but before `if dry_run:` (around line 92), add:

```python
    # ── Check for local control action ──────────────────────────────────────
    local_action = _detect_local_control_action(step)
    if local_action is not None:
        action_value, payload = local_action
        return _execute_local_control_step(step, action_value, payload, dry_run=dry_run)
```

And add the execution helper:

```python
def _execute_local_control_step(
    step: PipelineStep,
    action_value: str,
    payload: dict,
    *,
    dry_run: bool = False,
) -> PipelineStep:
    """Execute a step through the local control layer instead of tmux."""
    if dry_run:
        step.status = StepStatus.COMPLETED
        step.execution_result = f"dry_run — local_control: {action_value}"
        step.execution_finished_at = _utcnow()
        step.updated_at = _utcnow()
        return step

    try:
        from eos_ai.substrate.local_control import (
            LocalControlAction,
            execute_control_request,
            submit_control_request,
        )

        action_enum = LocalControlAction(action_value)
        req = submit_control_request(action_enum, payload, local_available=True)

        from eos_ai.substrate.local_control import RequestStatus

        if req.status == RequestStatus.BLOCKED:
            step.status = StepStatus.WAITING_ON_OPERATOR
            step.requires_input_prompt = f"Local control blocked: {req.error or action_value}"
            step.execution_finished_at = _utcnow()
            step.updated_at = _utcnow()
            return step

        result = execute_control_request(req.request_id)
        if result.status == RequestStatus.COMPLETED:
            step.status = StepStatus.COMPLETED
            step.execution_result = result.result or f"completed: {action_value}"
        elif result.status == RequestStatus.FAILED:
            step.status = StepStatus.FAILED
            step.execution_error = result.error or f"failed: {action_value}"
        else:
            step.status = StepStatus.WAITING_ON_OPERATOR
            step.requires_input_prompt = f"Pending: {action_value}"

    except Exception as exc:
        step.status = StepStatus.FAILED
        step.execution_error = f"local control dispatch error: {exc}"
        _log(f"local control step failed: {exc}")

    step.execution_finished_at = _utcnow()
    step.updated_at = _utcnow()
    return step
```

- [ ] **Step 2: Run existing pipeline tests to verify no regression**

Run: `python3 /opt/OS/tests/substrate/test_pipeline_execution.py`
Expected: ALL PASSED (no change to existing behavior — new code only triggers on action-prefixed step titles)

- [ ] **Step 3: Compile and format**

Run: `python3 -m py_compile eos_ai/substrate/pipeline_execution.py && ruff format eos_ai/substrate/pipeline_execution.py`

- [ ] **Step 4: Commit**

```bash
cd /opt/OS && git add eos_ai/substrate/pipeline_execution.py && git commit -m "feat: add browser/machine action dispatch to pipeline step execution"
```

---

## Task 7: Run Full Test Suite + Verification

**Files:** No new files — verification only.

### Step-by-step

- [ ] **Step 1: Run all substrate tests**

Run: `cd /opt/OS && for f in tests/substrate/test_*.py; do echo "--- $f ---"; python3 "$f" 2>&1 | tail -3; done`
Expected: All test files pass (ALL PASSED or equivalent for each)

- [ ] **Step 2: Run all EOS platform tests**

Run: `cd /opt/OS && python3 -m pytest tests/platforms/eos/ -v`
Expected: All tests pass

- [ ] **Step 3: Verify live utterance handled conversationally**

Run:
```python
python3 -c "
import sys; sys.path.insert(0, '/opt/OS')
from eos_ai.platforms.eos import handle_live_user_utterance
result = handle_live_user_utterance('catch me up on everything')
print('spoken_text:', result.spoken_text[:200])
print('is_control:', result.is_control_action)
print('session_id:', result.live_session_id)
print('tasks:', result.created_task_ids)
"
```
Expected: Spoken text contains a briefing, is_control=False, session_id set, no tasks created.

- [ ] **Step 4: Verify execution request creates and executes work**

Run:
```python
python3 -c "
import sys; sys.path.insert(0, '/opt/OS')
from eos_ai.platforms.eos import handle_live_user_utterance
result = handle_live_user_utterance('build the API endpoint', dry_run=True)
print('spoken_text:', result.spoken_text[:200])
print('tasks:', result.created_task_ids)
print('execution:', result.executed_actions_summary)
"
```
Expected: Tasks created, execution summaries populated (dry_run).

- [ ] **Step 5: Verify browser task through local machine path**

Run:
```python
python3 -c "
import sys; sys.path.insert(0, '/opt/OS')
from eos_ai.substrate.browser_agent import BrowserActionType, execute_browser_action
result = execute_browser_action(BrowserActionType.OPEN_URL, {'url': 'data:text/html,<h1>Test</h1>'})
print('ok:', result.ok)
print('data:', result.data)
extract = execute_browser_action(BrowserActionType.EXTRACT, {'selector': 'h1'})
print('extracted:', extract.data)
execute_browser_action(BrowserActionType.CLOSE, {})
print('browser closed')
"
```
Expected: ok=True, data includes URL, extracted='Test'.

- [ ] **Step 6: Verify machine control action through local path**

Run:
```python
python3 -c "
import sys; sys.path.insert(0, '/opt/OS')
from eos_ai.substrate.local_control import (
    LocalControlAction, LocalControlMode, LocalControlStore,
    submit_control_request, execute_control_request,
)
LocalControlStore._default = None
store = LocalControlStore.default()
store.set_mode(LocalControlMode.ASSISTED)
req = submit_control_request(
    LocalControlAction.OPEN_URL,
    {'url': 'data:text/html,<h1>MachineTest</h1>'},
    local_available=True,
)
print('submitted:', req.status.value)
result = execute_control_request(req.request_id)
print('executed:', result.status.value, result.result or result.error)
"
```
Expected: submitted=pending, executed=completed with browser URL.

- [ ] **Step 7: Verify pause/continue interaction**

Run:
```python
python3 -c "
import sys; sys.path.insert(0, '/opt/OS')
from eos_ai.platforms.eos.live_runtime import (
    EALiveRuntime, handle_live_user_utterance, get_live_runtime
)
EALiveRuntime._default = None
# Normal utterance
r1 = handle_live_user_utterance('status')
print('state after status:', get_live_runtime().state.value)
# Pause
r2 = handle_live_user_utterance('pause')
print('state after pause:', get_live_runtime().state.value)
print('pause text:', r2.spoken_text)
# Continue
r3 = handle_live_user_utterance('continue')
print('state after continue:', get_live_runtime().state.value)
print('resume text:', r3.spoken_text)
"
```
Expected: listening → paused → listening.

- [ ] **Step 8: Verify blocked-on-operator case**

Run:
```python
python3 -c "
import sys; sys.path.insert(0, '/opt/OS')
from eos_ai.substrate.task_system import TaskStore, create_task
TaskStore._default = None
task = create_task('deploy production database migration')
print('policy:', task.execution_policy.value)
print('status:', task.status.value)
print('prompt:', task.requires_input_prompt)
from eos_ai.platforms.eos.execution_bridge import execute_created_work_immediately
result = execute_created_work_immediately([task.task_id], [], dry_run=True)
print('blocked:', result.blocked_task_ids)
print('summary:', result.execution_summaries.get(task.task_id, ''))
"
```
Expected: Task classified as non-autonomous, appears in blocked_task_ids.

- [ ] **Step 9: Verify live session auto-created**

Run:
```python
python3 -c "
import sys; sys.path.insert(0, '/opt/OS')
from eos_ai.platforms.eos.live_runtime import EALiveRuntime, handle_live_user_utterance
from eos_ai.substrate.live_sessions import LiveSessionStore
EALiveRuntime._default = None
LiveSessionStore._default = None
result = handle_live_user_utterance('what is happening')
print('session_id:', result.live_session_id)
store = LiveSessionStore.default()
session = store.get(result.live_session_id)
print('session state:', session.state.value if session else 'NOT FOUND')
print('session type:', session.session_type.value if session else 'N/A')
"
```
Expected: Session created, state=active, type=local.

- [ ] **Step 10: Verify platform/substrate separation**

Run:
```python
python3 -c "
import sys; sys.path.insert(0, '/opt/OS')
# browser_agent should NOT import any EOS platform module
import ast
with open('eos_ai/substrate/browser_agent.py') as f:
    tree = ast.parse(f.read())
imports = [n for n in ast.walk(tree) if isinstance(n, (ast.Import, ast.ImportFrom))]
for imp in imports:
    if isinstance(imp, ast.ImportFrom) and imp.module and 'platforms' in imp.module:
        print(f'VIOLATION: browser_agent imports {imp.module}')
        sys.exit(1)
print('browser_agent: no platform imports — CLEAN')

# live_runtime should NOT import substrate directly except through platform adapters
# (it imports discord_hook.create_ea_live_session and live_sessions for session management)
print('Separation check PASSED')
"
```
Expected: CLEAN — no platform imports in substrate.

- [ ] **Step 11: Verify existing tests still pass**

Run: `cd /opt/OS && python3 /opt/OS/tests/substrate/test_live_sessions.py 2>&1 | tail -5 && python3 /opt/OS/tests/substrate/test_pipeline_execution.py 2>&1 | tail -5 && python3 /opt/OS/tests/substrate/test_task_execution.py 2>&1 | tail -5`
Expected: ALL PASSED for each.

- [ ] **Step 12: Final commit — verification complete**

No code changes — verification only. Tag with a note if all verifications pass.

---

## Summary of Files Created/Modified

### New Files (3 + 3 tests)
1. `eos_ai/substrate/browser_agent.py` — Real Playwright browser surface
2. `eos_ai/platforms/eos/execution_bridge.py` — Immediate execution from EAResponse
3. `eos_ai/platforms/eos/live_runtime.py` — Conversational runtime state machine
4. `tests/substrate/test_browser_agent.py`
5. `tests/platforms/eos/test_execution_bridge.py`
6. `tests/platforms/eos/test_live_runtime.py`

### Modified Files (4)
1. `eos_ai/substrate/local_control.py` — Real dispatch (browser + subprocess)
2. `eos_ai/substrate/pipeline_execution.py` — Browser/machine action step dispatch
3. `eos_ai/platforms/eos/discord_hook.py` — Live runtime bridge function
4. `eos_ai/platforms/eos/__init__.py` — New exports

### Not Modified (per constraint)
- `gateway.py`, `cognitive_loop.py`, `model_router.py`, `agent_runtime.py`, `primitives.py`
- `ea_orchestrator.py` (wrapped, not modified)
- `live_sessions.py` (used via existing API)
