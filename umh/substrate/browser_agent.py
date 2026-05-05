"""
Browser agent — real Playwright execution surface for the substrate.

Generic browser automation layer using headless Chromium via Playwright.
NOT EOS-specific. Does not import anything from umh.platforms.

Design rules (substrate conventions):
- Additive only. Hot path never imported.
- Best-effort. Runtime methods catch and log; never raise into callers.
- Bounded. One browser, one context, one page at a time.
- Deterministic. Actions are explicit dispatch via execute().
- Observable. All actions return BrowserActionResult with timing.
- Reversible. Removing this file leaves the substrate intact.

Usage:
    from umh.substrate.browser_agent import execute_browser_action, BrowserActionType
    result = execute_browser_action(BrowserActionType.OPEN_URL, {"url": "https://example.com"})
"""

from __future__ import annotations

import sys
import threading
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Optional


# ---- Constants / helpers ----------------------------------------------------


def _log(msg: str) -> None:
    print(f"[substrate.browser_agent] {msg}", file=sys.stderr)


def _utcnow() -> str:
    return datetime.now(timezone.utc).isoformat()


# ---- Streaming helpers -------------------------------------------------------


_BROWSER_ACTION_NARRATION: dict[str, str] = {
    "open_url": "Opening browser...",
    "click": "Clicking element...",
    "type_text": "Typing text...",
    "extract": "Extracting data...",
    "screenshot": "Taking screenshot...",
    "navigate_back": "Going back...",
    "close": "Closing browser...",
}


def _stream_browser_event(
    event_type_name: str,
    action: "BrowserActionType",
    payload: dict[str, Any],
) -> None:
    """Best-effort streaming event for browser actions."""
    try:
        from umh.platforms.eos.streaming_bridge import StreamEventType, stream_event

        narration = _BROWSER_ACTION_NARRATION.get(
            action.value, f"Browser: {action.value}..."
        )
        # Add context from payload
        if action.value == "open_url" and payload.get("url"):
            narration = f"Opening {payload['url'][:60]}..."
        elif action.value == "click" and payload.get("selector"):
            narration = f"Clicking {payload['selector'][:40]}..."
        elif action.value == "extract" and payload.get("selector"):
            narration = f"Extracting from {payload['selector'][:40]}..."

        stream_event(
            StreamEventType.ACTION_EXECUTED,
            narration,
            payload={"action": action.value, **payload},
            source="browser_agent",
        )
    except Exception:
        pass  # Best-effort, never interrupt browser operations


def _stream_browser_result(
    action: "BrowserActionType",
    result: "BrowserActionResult",
) -> None:
    """Best-effort streaming event for browser action results."""
    try:
        from umh.platforms.eos.streaming_bridge import StreamEventType, stream_event

        if result.ok:
            msg = f"Done: {result.data[:80]}" if result.data else "Done."
            stream_event(
                StreamEventType.ACTION_RESULT,
                msg,
                payload={"action": action.value, "ok": True},
                source="browser_agent",
                speak=False,  # Don't narrate every result — too noisy
            )
        else:
            stream_event(
                StreamEventType.ERROR,
                f"Browser error: {result.error or 'unknown'}",
                payload={"action": action.value, "ok": False},
                source="browser_agent",
            )
    except Exception:
        pass


# ---- Enum -------------------------------------------------------------------


class BrowserActionType(str, Enum):
    """Actions the browser agent can perform."""

    OPEN_URL = "open_url"
    CLICK = "click"
    TYPE_TEXT = "type_text"
    EXTRACT = "extract"
    SCREENSHOT = "screenshot"
    NAVIGATE_BACK = "navigate_back"
    CLOSE = "close"


# ---- Result dataclass -------------------------------------------------------


@dataclass
class BrowserActionResult:
    """Outcome of a single browser action."""

    action: BrowserActionType
    ok: bool
    data: Optional[str] = None
    error: Optional[str] = None
    duration_ms: float = 0.0
    created_at: str = field(default_factory=_utcnow)

    def to_dict(self) -> dict[str, Any]:
        """Serialize to a JSON-safe dict."""
        return {
            "action": self.action.value,
            "ok": self.ok,
            "data": self.data,
            "error": self.error,
            "duration_ms": self.duration_ms,
            "created_at": self.created_at,
        }


# ---- BrowserAgent -----------------------------------------------------------


class BrowserAgent:
    """Singleton browser execution surface backed by Playwright headless Chromium.

    Thread-safe. Lazy init on first use. One browser / context / page at a time.
    """

    _default: Optional[BrowserAgent] = None
    _default_lock = threading.Lock()

    def __init__(self, *, headless: bool = True) -> None:
        self._lock = threading.RLock()
        self._headless = headless
        self._playwright: Any = None
        self._browser: Any = None
        self._context: Any = None
        self._page: Any = None

    # ---- Singleton ----------------------------------------------------------

    @classmethod
    def default(cls, *, headless: bool = True) -> BrowserAgent:
        """Return the process-wide singleton, creating on first call."""
        if cls._default is None:
            with cls._default_lock:
                if cls._default is None:
                    cls._default = cls(headless=headless)
        return cls._default

    @classmethod
    def reset_default_for_tests(cls) -> None:
        """Tear down the singleton. Next default() creates a fresh instance."""
        with cls._default_lock:
            if cls._default is not None:
                try:
                    cls._default.close()
                except Exception:  # noqa: BLE001
                    pass
            cls._default = None

    # ---- Lifecycle ----------------------------------------------------------

    def _ensure_browser(self) -> None:
        """Lazily start Playwright + headless Chromium. Caller holds _lock."""
        if self._browser is not None:
            return
        try:
            from playwright.sync_api import sync_playwright

            self._playwright = sync_playwright().start()
            self._browser = self._playwright.chromium.launch(
                headless=self._headless,
                args=["--disable-gpu", "--no-sandbox"],
            )
            self._context = self._browser.new_context(
                viewport={"width": 1280, "height": 720},
            )
            _log("browser started (headless={})".format(self._headless))
        except Exception as e:  # noqa: BLE001
            _log(f"failed to start browser: {e}")
            # Clean up partial state
            self._context = None
            self._browser = None
            if self._playwright is not None:
                try:
                    self._playwright.stop()
                except Exception:  # noqa: BLE001
                    pass
            self._playwright = None
            raise

    def _ensure_page(self) -> None:
        """Create a page if one does not exist. Caller holds _lock."""
        self._ensure_browser()
        if self._page is None or self._page.is_closed():
            self._page = self._context.new_page()

    def close(self) -> None:
        """Tear down all resources: page, context, browser, playwright."""
        with self._lock:
            if self._page is not None:
                try:
                    self._page.close()
                except Exception:  # noqa: BLE001
                    pass
                self._page = None

            if self._context is not None:
                try:
                    self._context.close()
                except Exception:  # noqa: BLE001
                    pass
                self._context = None

            if self._browser is not None:
                try:
                    self._browser.close()
                except Exception:  # noqa: BLE001
                    pass
                self._browser = None

            if self._playwright is not None:
                try:
                    self._playwright.stop()
                except Exception:  # noqa: BLE001
                    pass
                self._playwright = None

            _log("browser closed")

    # ---- Execute dispatch ---------------------------------------------------

    def execute(
        self, action: BrowserActionType, payload: Optional[dict[str, Any]] = None
    ) -> BrowserActionResult:
        """Thread-safe dispatch to the appropriate action handler.

        Always returns a BrowserActionResult, never raises.
        Emits streaming events for real-time narration.
        """
        payload = payload or {}
        _stream_browser_event("action_executed", action, payload)
        t0 = time.monotonic()
        try:
            with self._lock:
                result = self._dispatch(action, payload)
        except Exception as e:  # noqa: BLE001
            result = BrowserActionResult(
                action=action,
                ok=False,
                error=str(e),
            )
        result.duration_ms = round((time.monotonic() - t0) * 1000, 2)
        _stream_browser_result(action, result)
        return result

    def _dispatch(
        self, action: BrowserActionType, payload: dict[str, Any]
    ) -> BrowserActionResult:
        """Route to the correct handler. Caller holds _lock."""
        handlers = {
            BrowserActionType.OPEN_URL: self._do_open_url,
            BrowserActionType.CLICK: self._do_click,
            BrowserActionType.TYPE_TEXT: self._do_type_text,
            BrowserActionType.EXTRACT: self._do_extract,
            BrowserActionType.SCREENSHOT: self._do_screenshot,
            BrowserActionType.NAVIGATE_BACK: self._do_navigate_back,
            BrowserActionType.CLOSE: lambda _p: self._do_close(),
        }
        handler = handlers.get(action)
        if handler is None:
            return BrowserActionResult(
                action=action,
                ok=False,
                error=f"unknown action: {action.value}",
            )
        return handler(payload)

    # ---- Helpers ------------------------------------------------------------

    def _has_page(self) -> bool:
        """Return True if there is an active, non-closed page."""
        return self._page is not None and not self._page.is_closed()

    def _no_page_error(self, action: BrowserActionType) -> BrowserActionResult:
        """Return a standard error for actions that require an active page."""
        return BrowserActionResult(
            action=action,
            ok=False,
            error="no active page — call OPEN_URL first",
        )

    # ---- Action handlers ----------------------------------------------------

    def _do_open_url(self, payload: dict[str, Any]) -> BrowserActionResult:
        """Navigate to a URL. Creates a page if needed."""
        url = payload.get("url")
        if not url:
            return BrowserActionResult(
                action=BrowserActionType.OPEN_URL,
                ok=False,
                error="payload missing 'url'",
            )
        try:
            self._ensure_page()
            self._page.goto(url, wait_until="domcontentloaded", timeout=30000)
            final_url = self._page.url
            _log(f"opened {final_url}")
            return BrowserActionResult(
                action=BrowserActionType.OPEN_URL,
                ok=True,
                data=final_url,
            )
        except Exception as e:  # noqa: BLE001
            return BrowserActionResult(
                action=BrowserActionType.OPEN_URL,
                ok=False,
                error=str(e),
            )

    def _do_click(self, payload: dict[str, Any]) -> BrowserActionResult:
        """Click an element by CSS selector."""
        if not self._has_page():
            return self._no_page_error(BrowserActionType.CLICK)
        selector = payload.get("selector")
        if not selector:
            return BrowserActionResult(
                action=BrowserActionType.CLICK,
                ok=False,
                error="payload missing 'selector'",
            )
        try:
            self._page.click(selector, timeout=10000)
            _log(f"clicked {selector!r}")
            return BrowserActionResult(
                action=BrowserActionType.CLICK,
                ok=True,
                data=selector,
            )
        except Exception as e:  # noqa: BLE001
            return BrowserActionResult(
                action=BrowserActionType.CLICK,
                ok=False,
                error=str(e),
            )

    def _do_type_text(self, payload: dict[str, Any]) -> BrowserActionResult:
        """Fill a text field by CSS selector."""
        if not self._has_page():
            return self._no_page_error(BrowserActionType.TYPE_TEXT)
        selector = payload.get("selector")
        text = payload.get("text")
        if not selector or text is None:
            return BrowserActionResult(
                action=BrowserActionType.TYPE_TEXT,
                ok=False,
                error="payload missing 'selector' and/or 'text'",
            )
        try:
            self._page.fill(selector, text, timeout=10000)
            _log(f"typed into {selector!r}")
            return BrowserActionResult(
                action=BrowserActionType.TYPE_TEXT,
                ok=True,
                data=selector,
            )
        except Exception as e:  # noqa: BLE001
            return BrowserActionResult(
                action=BrowserActionType.TYPE_TEXT,
                ok=False,
                error=str(e),
            )

    def _do_extract(self, payload: dict[str, Any]) -> BrowserActionResult:
        """Extract text content from an element by CSS selector."""
        if not self._has_page():
            return self._no_page_error(BrowserActionType.EXTRACT)
        selector = payload.get("selector")
        if not selector:
            return BrowserActionResult(
                action=BrowserActionType.EXTRACT,
                ok=False,
                error="payload missing 'selector'",
            )
        try:
            element = self._page.query_selector(selector)
            if element is None:
                return BrowserActionResult(
                    action=BrowserActionType.EXTRACT,
                    ok=False,
                    error=f"element not found: {selector!r}",
                )
            text = element.text_content() or ""
            _log(f"extracted from {selector!r}: {text[:80]!r}")
            return BrowserActionResult(
                action=BrowserActionType.EXTRACT,
                ok=True,
                data=text,
            )
        except Exception as e:  # noqa: BLE001
            return BrowserActionResult(
                action=BrowserActionType.EXTRACT,
                ok=False,
                error=str(e),
            )

    def _do_screenshot(self, payload: dict[str, Any]) -> BrowserActionResult:
        """Take a full-page screenshot. Optional 'path' in payload."""
        if not self._has_page():
            return self._no_page_error(BrowserActionType.SCREENSHOT)
        path = payload.get("path") or f"/tmp/eos_screenshot_{uuid.uuid4().hex[:12]}.png"
        try:
            self._page.screenshot(path=path, full_page=True)
            _log(f"screenshot saved to {path}")
            return BrowserActionResult(
                action=BrowserActionType.SCREENSHOT,
                ok=True,
                data=path,
            )
        except Exception as e:  # noqa: BLE001
            return BrowserActionResult(
                action=BrowserActionType.SCREENSHOT,
                ok=False,
                error=str(e),
            )

    def _do_navigate_back(self, payload: dict[str, Any]) -> BrowserActionResult:
        """Go back in browser history."""
        if not self._has_page():
            return self._no_page_error(BrowserActionType.NAVIGATE_BACK)
        try:
            self._page.go_back(wait_until="domcontentloaded")
            current_url = self._page.url
            _log(f"navigated back to {current_url}")
            return BrowserActionResult(
                action=BrowserActionType.NAVIGATE_BACK,
                ok=True,
                data=current_url,
            )
        except Exception as e:  # noqa: BLE001
            return BrowserActionResult(
                action=BrowserActionType.NAVIGATE_BACK,
                ok=False,
                error=str(e),
            )

    def _do_close(self) -> BrowserActionResult:
        """Close the browser and all resources."""
        try:
            self.close()
            return BrowserActionResult(
                action=BrowserActionType.CLOSE,
                ok=True,
                data="browser closed",
            )
        except Exception as e:  # noqa: BLE001
            return BrowserActionResult(
                action=BrowserActionType.CLOSE,
                ok=False,
                error=str(e),
            )


# ---- Module-level API -------------------------------------------------------


def get_browser_agent(headless: bool = True) -> BrowserAgent:
    """Return the process-wide BrowserAgent singleton."""
    return BrowserAgent.default(headless=headless)


def execute_browser_action(
    action: BrowserActionType,
    payload: Optional[dict[str, Any]] = None,
    headless: bool = True,
) -> BrowserActionResult:
    """Convenience: execute a browser action via the singleton agent."""
    agent = get_browser_agent(headless=headless)
    return agent.execute(action, payload)


# ---- Exports ----------------------------------------------------------------

__all__ = [
    "BrowserActionType",
    "BrowserActionResult",
    "BrowserAgent",
    "get_browser_agent",
    "execute_browser_action",
]
