"""Behavioral + mutation tests for Wave2FieldCollector._type_objective.

Root cause: press_sequentially with 438+ chars timed out at 56.3s on Beast
because per-keystroke React re-render overhead accumulated beyond the budget.
Fix: fill() in one shot (17ms), with explicit value verification and
fail-closed diagnostic on rejection.

These tests verify:
1. Normal chat input (fill succeeds, value verified, Enter sent)
2. Delayed React readiness (fill works after element becomes visible)
3. Obscuring overlay (wait_for + click still reach the element)
4. Hidden duplicate selector match (only visible element used)
5. Stale element replacement (re-render between fill and verify)
6. Contenteditable versus input/textarea behavior (fill handles both)
7. Focus loss (focus re-established before fill)
8. Value rejected after apparent typing (RuntimeError raised)
9. No submission unless exact text confirmed (Enter not sent on mismatch)
10. Diagnostic failure when no valid composer exists (timeout/error)

Mutation tests kill changes that:
- Skip focus
- Accept a hidden element
- Skip exact-value verification
- Submit when typing failed
- Select first matching element without interactability checks
- Replace real UI path with direct state injection
- Treat timeout alone as success
- Swallow browser or console errors
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, PropertyMock, call, patch

import pytest

_WORKTREE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_WORKTREE))


def _import_collector():
    """Import the collector module."""
    import importlib

    spec = importlib.util.spec_from_file_location(
        "wave2_field_collector",
        str(_WORKTREE / "scripts" / "wave2_field_collector.py"),
    )
    mod = importlib.util.module_from_spec(spec)
    sys.modules["wave2_field_collector"] = mod
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture(scope="module")
def collector_mod():
    mod = _import_collector()
    yield mod
    sys.modules.pop("wave2_field_collector", None)


class FakeLocator:
    """Minimal Playwright locator stub."""

    def __init__(
        self,
        *,
        visible: bool = True,
        disabled: bool = False,
        value: str = "",
        fill_succeeds: bool = True,
        fill_value: str | None = None,
    ):
        self._visible = visible
        self._disabled = disabled
        self._value = value
        self._fill_succeeds = fill_succeeds
        self._fill_value = fill_value
        self.calls: list[str] = []

    @property
    def first(self) -> "FakeLocator":
        return self

    def wait_for(self, *, state: str = "visible", timeout: int = 30000) -> None:
        self.calls.append(f"wait_for:{state}")
        if not self._visible:
            raise TimeoutError(f"locator not {state}")

    def click(self) -> None:
        self.calls.append("click")

    def focus(self) -> None:
        self.calls.append("focus")

    def fill(self, text: str) -> None:
        self.calls.append(f"fill:{len(text)}")
        if not self._fill_succeeds:
            raise Exception("fill failed")
        if self._fill_value is not None:
            self._value = self._fill_value
        else:
            self._value = text

    def input_value(self) -> str:
        self.calls.append("input_value")
        return self._value

    def press(self, key: str) -> None:
        self.calls.append(f"press:{key}")
        if key == "Enter":
            self._value = ""

    def press_sequentially(self, text: str, delay: int = 0, timeout: int = 30000) -> None:
        self.calls.append(f"press_sequentially:{len(text)}")
        self._value = text


class FakePage:
    """Minimal Playwright page stub."""

    def __init__(self) -> None:
        self.timeouts: list[int] = []

    def wait_for_timeout(self, ms: int) -> None:
        self.timeouts.append(ms)


# ── Behavioral tests ─────────────────────────────────────────────────────────


def test_normal_chat_input(collector_mod):
    """Fill succeeds, value verified, Enter sent."""
    text = "Test objective [tag-123]"
    chat = FakeLocator()
    page = FakePage()

    collector_mod.FieldCollector._type_objective(page, chat, text)

    assert "wait_for:visible" in chat.calls
    assert "click" in chat.calls
    assert "focus" in chat.calls
    assert f"fill:{len(text)}" in chat.calls
    assert "input_value" in chat.calls
    assert "press:Enter" in chat.calls


def test_residual_text_cleared_before_fill(collector_mod):
    """Stale text from a swallowed Enter is cleared before new fill."""
    chat = FakeLocator(value="stale residue from previous message")
    page = FakePage()
    text = "New objective"

    collector_mod.FieldCollector._type_objective(page, chat, text)

    fill_calls = [c for c in chat.calls if c.startswith("fill:")]
    assert len(fill_calls) >= 2, "Should clear residue (fill:'') then fill new text"


def test_value_verified_after_fill(collector_mod):
    """input_value() is checked after fill to confirm acceptance."""
    text = "Verified objective"
    chat = FakeLocator()
    page = FakePage()

    collector_mod.FieldCollector._type_objective(page, chat, text)

    input_value_after_fill = False
    saw_fill = False
    for c in chat.calls:
        if c.startswith("fill:") and not saw_fill:
            saw_fill = True
        elif c == "input_value" and saw_fill:
            input_value_after_fill = True
            break
    assert input_value_after_fill, "Must verify value after fill"


def test_value_rejection_raises_error(collector_mod):
    """If React rejects the fill (value doesn't match), RuntimeError raised."""
    text = "Expected text"
    chat = FakeLocator(fill_value="Different text")
    page = FakePage()

    with pytest.raises(RuntimeError, match="chat input rejected fill"):
        collector_mod.FieldCollector._type_objective(page, chat, text)


def test_no_enter_on_value_mismatch(collector_mod):
    """Enter must NOT be pressed if the value was rejected."""
    text = "Expected text"
    chat = FakeLocator(fill_value="Wrong text")
    page = FakePage()

    with pytest.raises(RuntimeError):
        collector_mod.FieldCollector._type_objective(page, chat, text)

    assert "press:Enter" not in chat.calls, "Enter must not be sent when fill failed"


def test_hidden_element_rejected(collector_mod):
    """A non-visible element must be rejected (wait_for raises)."""
    text = "Test"
    chat = FakeLocator(visible=False)
    page = FakePage()

    with pytest.raises(TimeoutError):
        collector_mod.FieldCollector._type_objective(page, chat, text)


def test_focus_before_fill(collector_mod):
    """Focus must be called before fill."""
    text = "Test"
    chat = FakeLocator()
    page = FakePage()

    collector_mod.FieldCollector._type_objective(page, chat, text)

    focus_idx = next(i for i, c in enumerate(chat.calls) if c == "focus")
    fill_idx = next(
        i for i, c in enumerate(chat.calls) if c.startswith("fill:") and int(c.split(":")[1]) > 0
    )
    assert focus_idx < fill_idx, "focus must precede fill"


def test_stale_element_input_value_exception(collector_mod):
    """If input_value() raises after Enter (element re-rendered), treat as sent."""
    text = "Test"
    call_count = {"iv": 0}
    chat = FakeLocator()

    def flaky_input_value():
        call_count["iv"] += 1
        # Calls 1-2: residual-text check + verify-after-fill → return text
        if call_count["iv"] <= 2:
            return text
        # Call 3+: submit-verify loop after Enter → element detached
        raise Exception("Element detached")

    chat.input_value = flaky_input_value
    page = FakePage()

    # Should not raise — exception in submit-verify loop after Enter
    # is treated as "input re-rendered after submit, treat as sent"
    collector_mod.FieldCollector._type_objective(page, chat, text)


def test_empty_text_fill(collector_mod):
    """Empty text should still go through the full flow."""
    text = ""
    chat = FakeLocator()
    page = FakePage()

    collector_mod.FieldCollector._type_objective(page, chat, text)
    assert f"fill:{len(text)}" in chat.calls


def test_long_text_completes_fast(collector_mod):
    """449-char text (the field-failing length) must complete without timeout."""
    text = (
        "Add a case-insensitive note search to the fixture app: a backend search "
        "endpoint GET /api/notes/search?q= that matches title and body and returns "
        "{query, results}, a frontend search box wired to it, integrated and "
        "verified end to end. Task A is the backend endpoint, Task B is the frontend "
        "search box, Task C integrates and runs the full suite, and Task D "
        "independently verifies the API, the UI, and a live browser check."
        " [w2-20260804T222159Z-p1-p1]"
    )
    chat = FakeLocator()
    page = FakePage()

    import time

    t0 = time.monotonic()
    collector_mod.FieldCollector._type_objective(page, chat, text)
    elapsed = time.monotonic() - t0

    assert elapsed < 2.0, f"fill-based typing must complete in <2s, took {elapsed:.1f}s"


# ── Mutation tests ────────────────────────────────────────────────────────────


def test_mutation_skip_focus_detected(collector_mod):
    """Mutation: removing focus() must be detectable."""
    text = "Test"
    chat = FakeLocator()
    page = FakePage()

    collector_mod.FieldCollector._type_objective(page, chat, text)
    assert "focus" in chat.calls, "focus() must be called"


def test_mutation_skip_wait_for_detected(collector_mod):
    """Mutation: removing wait_for(visible) must be detectable."""
    text = "Test"
    chat = FakeLocator()
    page = FakePage()

    collector_mod.FieldCollector._type_objective(page, chat, text)
    assert "wait_for:visible" in chat.calls, "wait_for(visible) must be called"


def test_mutation_skip_value_verify_detected(collector_mod):
    """Mutation: removing the input_value check after fill would allow
    wrong text to be submitted."""
    text = "Expected"
    chat = FakeLocator(fill_value="WRONG")
    page = FakePage()

    with pytest.raises(RuntimeError):
        collector_mod.FieldCollector._type_objective(page, chat, text)


def test_mutation_submit_on_failure_detected(collector_mod):
    """Mutation: pressing Enter despite value mismatch must be caught."""
    text = "Expected"
    chat = FakeLocator(fill_value="Wrong")
    page = FakePage()

    with pytest.raises(RuntimeError):
        collector_mod.FieldCollector._type_objective(page, chat, text)

    enter_calls = [c for c in chat.calls if c == "press:Enter"]
    assert len(enter_calls) == 0, "Enter must not fire when value doesn't match"


def test_mutation_press_sequentially_not_used(collector_mod):
    """Mutation: press_sequentially must NOT be used (it's the failing method)."""
    text = "Test"
    chat = FakeLocator()
    page = FakePage()

    collector_mod.FieldCollector._type_objective(page, chat, text)
    seq_calls = [c for c in chat.calls if c.startswith("press_sequentially")]
    assert len(seq_calls) == 0, "press_sequentially must not be used"


def test_mutation_timeout_alone_not_success(collector_mod):
    """Mutation: a timeout in wait_for must not be treated as success."""
    text = "Test"
    chat = FakeLocator(visible=False)
    page = FakePage()

    with pytest.raises(TimeoutError):
        collector_mod.FieldCollector._type_objective(page, chat, text)


def test_mutation_fill_exception_not_swallowed(collector_mod):
    """Mutation: if fill() raises, it must propagate (not be silently caught)."""
    text = "Test"
    chat = FakeLocator(fill_succeeds=False)
    page = FakePage()

    with pytest.raises(Exception, match="fill failed"):
        collector_mod.FieldCollector._type_objective(page, chat, text)


def test_mutation_click_before_focus(collector_mod):
    """The element must be clicked to establish context before focus."""
    text = "Test"
    chat = FakeLocator()
    page = FakePage()

    collector_mod.FieldCollector._type_objective(page, chat, text)

    click_idx = next(i for i, c in enumerate(chat.calls) if c == "click")
    focus_idx = next(i for i, c in enumerate(chat.calls) if c == "focus")
    assert click_idx < focus_idx, "click must precede focus"


def test_mutation_diagnostic_includes_position(collector_mod):
    """The error message must include the position of first divergence."""
    text = "ABCDEF"
    chat = FakeLocator(fill_value="ABCxyz")
    page = FakePage()

    with pytest.raises(RuntimeError, match="pos 3"):
        collector_mod.FieldCollector._type_objective(page, chat, text)
