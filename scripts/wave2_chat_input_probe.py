"""Zero-quota browser probe: reproduces the chat-input typing failure.

Drives the deployed cockpit (candidate or production) chat input through
the same interaction path as the collector, testing multiple methods:

1. press_sequentially (the failing method) with the exact text and delay
2. fill() (bulk set — the proposed fix)
3. evaluate-based native input (InputEvent dispatch)
4. focus + keyboard.type

Captures DOM state, screenshots, console errors, and timing for each method.
Does NOT submit (no Enter), does NOT consume field quota.

Usage (on Beast via mesh dispatch):
  python scripts/wave2_chat_input_probe.py --url <cockpit_url>
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

CHAT_INPUT_SELECTOR = 'input[placeholder^="Message "]'

PROBE_TEXT = (
    "Add a case-insensitive note search to the fixture app: a backend search "
    "endpoint GET /api/notes/search?q= that matches title and body and returns "
    "{query, results}, a frontend search box wired to it, integrated and "
    "verified end to end. Task A is the backend endpoint, Task B is the frontend "
    "search box, Task C integrates and runs the full suite, and Task D "
    "independently verifies the API, the UI, and a live browser check."
    " [probe-test-tag]"
)

_AUTH_DIR = Path(os.path.expanduser("~")) / ".umh" / "playwright-auth"
_AUTH_STATE_FILE = _AUTH_DIR / "chromium_state_wave2.json"


def _no_window() -> dict[str, Any]:
    if sys.platform == "win32":
        return {"creationflags": subprocess.CREATE_NO_WINDOW}
    return {}


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _element_diagnostics(page: Any, locator: Any) -> dict[str, Any]:
    """Capture comprehensive element diagnostics."""
    diag: dict[str, Any] = {}
    try:
        el = locator.first.element_handle()
        if not el:
            diag["error"] = "element_handle returned None"
            return diag

        diag["tag"] = el.evaluate("e => e.tagName")
        diag["type"] = el.evaluate("e => e.type || null")
        diag["role"] = el.evaluate("e => e.getAttribute('role')")
        diag["contenteditable"] = el.evaluate("e => e.contentEditable")
        diag["disabled"] = el.evaluate("e => e.disabled")
        diag["readonly"] = el.evaluate("e => e.readOnly")
        diag["visibility"] = el.evaluate("e => getComputedStyle(e).visibility")
        diag["display"] = el.evaluate("e => getComputedStyle(e).display")
        diag["pointer_events"] = el.evaluate("e => getComputedStyle(e).pointerEvents")
        diag["opacity"] = el.evaluate("e => getComputedStyle(e).opacity")

        box = el.bounding_box()
        diag["bounding_box"] = box

        diag["z_index"] = el.evaluate("e => getComputedStyle(e).zIndex")
        diag["placeholder"] = el.evaluate("e => e.placeholder || null")
        diag["value"] = el.evaluate("e => e.value || null")
        diag["class"] = el.evaluate("e => e.className")

        diag["active_element_before_focus"] = page.evaluate(
            "document.activeElement ? document.activeElement.tagName + '.' + document.activeElement.className : null"
        )

        # Check for overlaying elements
        if box:
            cx, cy = box["x"] + box["width"] / 2, box["y"] + box["height"] / 2
            diag["element_at_point"] = page.evaluate(
                f"""(() => {{
                    const el = document.elementFromPoint({cx}, {cy});
                    return el ? el.tagName + '.' + el.className.toString().slice(0,60) : null;
                }})()"""
            )

        # Count matching elements
        diag["selector_match_count"] = locator.count()

        # Check if any match is hidden
        if locator.count() > 1:
            diag["multiple_matches"] = True
            visibilities = []
            for i in range(min(locator.count(), 5)):
                try:
                    vis = locator.nth(i).is_visible()
                    visibilities.append(vis)
                except Exception:
                    visibilities.append("error")
            diag["match_visibilities"] = visibilities

    except Exception as exc:
        diag["diagnostic_error"] = str(exc)

    return diag


def _test_press_sequentially(page: Any, locator: Any, text: str) -> dict[str, Any]:
    """Test the exact method that failed: press_sequentially."""
    import random

    result: dict[str, Any] = {"method": "press_sequentially"}

    try:
        locator.first.click()
        try:
            if (locator.first.input_value() or "").strip():
                locator.first.fill("")
        except Exception:
            pass

        delay = random.randint(40, 90)
        budget_ms = len(text) * (delay + 30) + 15000
        result["delay_ms"] = delay
        result["budget_ms"] = budget_ms
        result["text_len"] = len(text)

        t0 = time.monotonic()
        locator.first.press_sequentially(text, delay=delay, timeout=budget_ms)
        elapsed = (time.monotonic() - t0) * 1000
        result["elapsed_ms"] = round(elapsed)

        actual = locator.first.input_value()
        result["value_matches"] = actual == text
        result["actual_len"] = len(actual)
        result["ok"] = result["value_matches"]

    except Exception as exc:
        result["ok"] = False
        result["error"] = str(exc)[:500]
        result["elapsed_ms"] = round((time.monotonic() - t0) * 1000) if "t0" in dir() else None

    # Clean up
    try:
        locator.first.fill("")
    except Exception:
        pass

    return result


def _test_fill(page: Any, locator: Any, text: str) -> dict[str, Any]:
    """Test fill() — bulk value injection."""
    result: dict[str, Any] = {"method": "fill"}

    try:
        locator.first.click()
        t0 = time.monotonic()
        locator.first.fill(text)
        elapsed = (time.monotonic() - t0) * 1000
        result["elapsed_ms"] = round(elapsed)

        actual = locator.first.input_value()
        result["value_matches"] = actual == text
        result["actual_len"] = len(actual)
        result["ok"] = result["value_matches"]

    except Exception as exc:
        result["ok"] = False
        result["error"] = str(exc)[:500]

    try:
        locator.first.fill("")
    except Exception:
        pass

    return result


def _test_focus_then_fill(page: Any, locator: Any, text: str) -> dict[str, Any]:
    """Test explicit focus + fill."""
    result: dict[str, Any] = {"method": "focus_then_fill"}

    try:
        locator.first.focus()
        page.wait_for_timeout(200)

        active = page.evaluate(
            "document.activeElement ? document.activeElement.tagName + '.' + document.activeElement.className.toString().slice(0,40) : null"
        )
        result["active_after_focus"] = active

        t0 = time.monotonic()
        locator.first.fill(text)
        elapsed = (time.monotonic() - t0) * 1000
        result["elapsed_ms"] = round(elapsed)

        actual = locator.first.input_value()
        result["value_matches"] = actual == text
        result["actual_len"] = len(actual)
        result["ok"] = result["value_matches"]

    except Exception as exc:
        result["ok"] = False
        result["error"] = str(exc)[:500]

    try:
        locator.first.fill("")
    except Exception:
        pass

    return result


def _test_evaluate_insert(page: Any, locator: Any, text: str) -> dict[str, Any]:
    """Test evaluate-based native input (InputEvent dispatch)."""
    result: dict[str, Any] = {"method": "evaluate_insert"}

    try:
        locator.first.focus()
        page.wait_for_timeout(200)

        t0 = time.monotonic()
        safe_text = json.dumps(text)
        page.evaluate(f"""(() => {{
            const el = document.querySelector('{CHAT_INPUT_SELECTOR}');
            if (!el) throw new Error('no element');
            const nativeSet = Object.getOwnPropertyDescriptor(
                HTMLInputElement.prototype, 'value'
            ).set;
            nativeSet.call(el, {safe_text});
            el.dispatchEvent(new Event('input', {{ bubbles: true }}));
            el.dispatchEvent(new Event('change', {{ bubbles: true }}));
        }})()""")
        elapsed = (time.monotonic() - t0) * 1000
        result["elapsed_ms"] = round(elapsed)

        page.wait_for_timeout(100)
        actual = locator.first.input_value()
        result["value_matches"] = actual == text
        result["actual_len"] = len(actual)
        result["ok"] = result["value_matches"]

    except Exception as exc:
        result["ok"] = False
        result["error"] = str(exc)[:500]

    try:
        locator.first.fill("")
    except Exception:
        pass

    return result


def run_probe(url: str, evidence_dir: Path) -> dict[str, Any]:
    """Run the probe against the cockpit at `url`."""
    from playwright.sync_api import sync_playwright

    evidence_dir.mkdir(parents=True, exist_ok=True)
    results: dict[str, Any] = {
        "url": url,
        "text_len": len(PROBE_TEXT),
        "started_at": _utc_now(),
        "methods": [],
    }

    with sync_playwright() as pw:
        # Use stored auth state if available
        ctx_opts: dict[str, Any] = {
            "ignore_https_errors": True,
            "viewport": {"width": 1920, "height": 1080},
        }
        if _AUTH_STATE_FILE.exists():
            ctx_opts["storage_state"] = str(_AUTH_STATE_FILE)

        browser = pw.chromium.launch(headless=False, channel="chrome")
        context = browser.new_context(**ctx_opts)
        page = context.new_page()

        # Collect console errors
        console_errors: list[dict[str, Any]] = []
        page.on(
            "console",
            lambda msg: (
                console_errors.append(
                    {
                        "type": msg.type,
                        "text": msg.text[:200],
                        "ms": round((time.monotonic() - probe_start) * 1000),
                    }
                )
                if msg.type in ("error", "warning")
                else None
            ),
        )

        probe_start = time.monotonic()

        # Navigate
        page.goto(url, wait_until="networkidle", timeout=60000)
        page.wait_for_timeout(3000)

        # Find chat input
        chat = page.locator(CHAT_INPUT_SELECTOR)
        if chat.count() == 0:
            # Try opening drawer
            toggle = page.locator('button[title="Open panel"]')
            if toggle.count() > 0:
                toggle.first.click()
                page.wait_for_timeout(1000)
                chat = page.locator(CHAT_INPUT_SELECTOR)

        if chat.count() == 0:
            results["error"] = "chat input not found"
            results["finished_at"] = _utc_now()
            (evidence_dir / "probe_result.json").write_text(
                json.dumps(results, indent=2), encoding="utf-8"
            )
            browser.close()
            return results

        # Screenshot before
        page.screenshot(path=str(evidence_dir / "00_before_typing.png"))

        # Element diagnostics
        results["element_diagnostics"] = _element_diagnostics(page, chat)

        # Test each method
        for test_fn in [
            _test_fill,
            _test_focus_then_fill,
            _test_evaluate_insert,
            _test_press_sequentially,
        ]:
            page.wait_for_timeout(500)
            method_result = test_fn(page, chat, PROBE_TEXT)
            results["methods"].append(method_result)
            print(
                f"  {method_result['method']}: ok={method_result.get('ok')} elapsed={method_result.get('elapsed_ms')}ms"
            )

        # Screenshot after
        page.screenshot(path=str(evidence_dir / "99_after_tests.png"))

        results["console_errors_during_probe"] = console_errors[:50]
        results["finished_at"] = _utc_now()

        (evidence_dir / "probe_result.json").write_text(
            json.dumps(results, indent=2), encoding="utf-8"
        )

        browser.close()

    return results


def main() -> None:
    parser = argparse.ArgumentParser(description="Chat input interaction probe")
    parser.add_argument("--url", required=True, help="Cockpit URL")
    parser.add_argument("--evidence-dir", default=None, help="Evidence output dir")
    args = parser.parse_args()

    evidence_dir = (
        Path(args.evidence_dir)
        if args.evidence_dir
        else (
            Path("C:/dev/wave2_evidence/probe")
            if sys.platform == "win32"
            else Path("/tmp/wave2_probe")
        )
    )

    print(f"Probe starting: url={args.url} evidence={evidence_dir}")
    result = run_probe(args.url, evidence_dir)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
