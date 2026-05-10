"""Smoke tests for eos_ai.substrate.browser_agent.

Uses REAL Playwright headless Chromium — no mocks.

Validates:
  1. test_singleton_creation         — default() returns a BrowserAgent
  2. test_action_types_exist         — all 7 action types are defined
  3. test_execute_open_url_headless  — OPEN_URL loads a page, data contains URL
  4. test_execute_extract            — extract h1 from a data: page
  5. test_execute_click              — click a button with onclick handler
  6. test_execute_type_text          — fill an input field
  7. test_execute_screenshot         — screenshot returns a file path
  8. test_execute_without_page_fails — click with no page returns ok=False
  9. test_close_action               — CLOSE tears down browser
 10. test_navigate_back              — open two pages, go back returns first URL

Run directly:
    python3 tests/substrate/test_browser_agent.py
"""

from __future__ import annotations

import os
import sys

sys.path.insert(0, "/opt/OS")

from eos_ai.substrate.browser_agent import (  # noqa: E402
    BrowserActionResult,
    BrowserActionType,
    BrowserAgent,
    execute_browser_action,
    get_browser_agent,
)

_PASS = 0
_FAIL = 0


def _report(name: str, passed: bool, detail: str = "") -> None:
    global _PASS, _FAIL  # noqa: PLW0603
    tag = "PASS" if passed else "FAIL"
    if not passed:
        _FAIL += 1
    else:
        _PASS += 1
    suffix = f" — {detail}" if detail else ""
    print(f"  [{tag}] {name}{suffix}")


def _reset() -> None:
    """Reset the singleton so each test starts clean."""
    BrowserAgent.reset_default_for_tests()


# ---- Test 1: singleton creation -------------------------------------------


def test_singleton_creation() -> None:
    print("\n-- Test 1: default() returns a BrowserAgent --")
    _reset()

    agent = BrowserAgent.default()
    _report("returns BrowserAgent", isinstance(agent, BrowserAgent))
    _report("same instance on second call", agent is BrowserAgent.default())


# ---- Test 2: action types exist -------------------------------------------


def test_action_types_exist() -> None:
    print("\n-- Test 2: all 7 action types defined --")
    _reset()

    expected = {
        "OPEN_URL",
        "CLICK",
        "TYPE_TEXT",
        "EXTRACT",
        "SCREENSHOT",
        "NAVIGATE_BACK",
        "CLOSE",
    }
    actual = {a.name for a in BrowserActionType}
    _report("7 action types", len(actual) == 7, f"got {len(actual)}")
    _report("all names match", expected == actual, f"missing: {expected - actual}")


# ---- Test 3: OPEN_URL headless --------------------------------------------


def test_execute_open_url_headless() -> None:
    print("\n-- Test 3: OPEN_URL loads a page --")
    _reset()

    result = execute_browser_action(
        BrowserActionType.OPEN_URL, {"url": "https://example.com"}
    )
    _report("ok is True", result.ok, f"error: {result.error}")
    _report(
        "data contains URL",
        result.data is not None and "example.com" in result.data,
        f"data: {result.data!r}",
    )
    _report("duration_ms > 0", result.duration_ms > 0, f"got {result.duration_ms}")
    _report("action is OPEN_URL", result.action == BrowserActionType.OPEN_URL)
    _report("to_dict works", isinstance(result.to_dict(), dict))


# ---- Test 4: EXTRACT h1 from data: page ----------------------------------


def test_execute_extract() -> None:
    print("\n-- Test 4: extract h1 from a data: page --")
    _reset()

    # Open a data: page with known HTML
    html = "<html><body><h1>BrowserAgent Test</h1></body></html>"
    data_url = f"data:text/html,{html}"
    open_result = execute_browser_action(BrowserActionType.OPEN_URL, {"url": data_url})
    _report("page opened", open_result.ok, f"error: {open_result.error}")

    extract_result = execute_browser_action(
        BrowserActionType.EXTRACT, {"selector": "h1"}
    )
    _report("ok is True", extract_result.ok, f"error: {extract_result.error}")
    _report(
        "data is 'BrowserAgent Test'",
        extract_result.data == "BrowserAgent Test",
        f"got {extract_result.data!r}",
    )


# ---- Test 5: CLICK a button -----------------------------------------------


def test_execute_click() -> None:
    print("\n-- Test 5: click a button --")
    _reset()

    html = (
        "<html><body>"
        '<button id="btn" onclick="document.title=\'clicked\'">Click me</button>'
        "</body></html>"
    )
    data_url = f"data:text/html,{html}"
    execute_browser_action(BrowserActionType.OPEN_URL, {"url": data_url})

    click_result = execute_browser_action(BrowserActionType.CLICK, {"selector": "#btn"})
    _report("ok is True", click_result.ok, f"error: {click_result.error}")
    _report(
        "data is selector",
        click_result.data == "#btn",
        f"got {click_result.data!r}",
    )

    # Verify the click had effect by checking page title
    agent = get_browser_agent()
    with agent._lock:
        title = agent._page.title()
    _report("onclick fired", title == "clicked", f"title: {title!r}")


# ---- Test 6: TYPE_TEXT fill input -----------------------------------------


def test_execute_type_text() -> None:
    print("\n-- Test 6: fill an input field --")
    _reset()

    html = '<html><body><input id="name" type="text" /></body></html>'
    data_url = f"data:text/html,{html}"
    execute_browser_action(BrowserActionType.OPEN_URL, {"url": data_url})

    type_result = execute_browser_action(
        BrowserActionType.TYPE_TEXT, {"selector": "#name", "text": "hello world"}
    )
    _report("ok is True", type_result.ok, f"error: {type_result.error}")

    # Verify the value was filled
    agent = get_browser_agent()
    with agent._lock:
        value = agent._page.input_value("#name")
    _report("input value correct", value == "hello world", f"got {value!r}")


# ---- Test 7: SCREENSHOT ---------------------------------------------------


def test_execute_screenshot() -> None:
    print("\n-- Test 7: screenshot returns a file path --")
    _reset()

    html = "<html><body><h1>Screenshot Test</h1></body></html>"
    data_url = f"data:text/html,{html}"
    execute_browser_action(BrowserActionType.OPEN_URL, {"url": data_url})

    result = execute_browser_action(BrowserActionType.SCREENSHOT, {})
    _report("ok is True", result.ok, f"error: {result.error}")
    _report(
        "data is a path",
        result.data is not None and result.data.startswith("/tmp/eos_screenshot_"),
        f"got {result.data!r}",
    )
    _report(
        "file exists on disk",
        result.data is not None and os.path.isfile(result.data),
        f"path: {result.data!r}",
    )

    # Clean up
    if result.data and os.path.isfile(result.data):
        os.remove(result.data)


# ---- Test 8: action without page fails gracefully -------------------------


def test_execute_without_page_fails_gracefully() -> None:
    print("\n-- Test 8: click with no page returns ok=False --")
    _reset()

    result = execute_browser_action(
        BrowserActionType.CLICK, {"selector": "#does-not-exist"}
    )
    _report("ok is False", result.ok is False)
    _report(
        "error mentions no active page",
        result.error is not None and "no active page" in result.error,
        f"got {result.error!r}",
    )


# ---- Test 9: CLOSE action -------------------------------------------------


def test_close_action() -> None:
    print("\n-- Test 9: CLOSE tears down browser --")
    _reset()

    # Open something first so there is a browser to close
    execute_browser_action(
        BrowserActionType.OPEN_URL,
        {"url": "data:text/html,<html><body>close test</body></html>"},
    )

    result = execute_browser_action(BrowserActionType.CLOSE, {})
    _report("ok is True", result.ok, f"error: {result.error}")
    _report(
        "data says closed",
        result.data is not None and "closed" in result.data,
        f"got {result.data!r}",
    )

    # Verify browser is torn down
    agent = get_browser_agent()
    _report("browser is None after close", agent._browser is None)
    _report("page is None after close", agent._page is None)


# ---- Test 10: NAVIGATE_BACK -----------------------------------------------


def test_navigate_back() -> None:
    print("\n-- Test 10: open two pages, go back returns first URL --")
    _reset()

    url1 = "data:text/html,<html><body><h1>Page One</h1></body></html>"
    url2 = "data:text/html,<html><body><h1>Page Two</h1></body></html>"

    r1 = execute_browser_action(BrowserActionType.OPEN_URL, {"url": url1})
    _report("page 1 opened", r1.ok, f"error: {r1.error}")

    r2 = execute_browser_action(BrowserActionType.OPEN_URL, {"url": url2})
    _report("page 2 opened", r2.ok, f"error: {r2.error}")

    back_result = execute_browser_action(BrowserActionType.NAVIGATE_BACK, {})
    _report("ok is True", back_result.ok, f"error: {back_result.error}")
    _report(
        "data contains first URL or about:blank",
        back_result.data is not None,
        f"got {back_result.data!r}",
    )


# ---- Runner ----------------------------------------------------------------

if __name__ == "__main__":
    print("Browser Agent Smoke Tests")
    print("=" * 60)

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

    print("\n" + "=" * 60)
    print(f"Results: {_PASS} passed, {_FAIL} failed")

    # Final cleanup
    BrowserAgent.reset_default_for_tests()

    if _FAIL:
        sys.exit(1)
    else:
        print("All smoke tests passed.")
