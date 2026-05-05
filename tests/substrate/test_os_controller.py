"""Tests for OSController — deep OS-level control surface."""

from __future__ import annotations

import os
import sys
import tempfile
import threading
from unittest.mock import MagicMock, patch

sys.path.insert(0, "/opt/OS")

import pytest

from eos_ai.substrate.os_controller import (
    OSAction,
    OSActionResult,
    OSController,
    execute_os_action,
    get_os_controller,
)


@pytest.fixture(autouse=True)
def _reset_controller():
    """Reset singleton before and after each test."""
    OSController.reset_default_for_tests()
    yield
    OSController.reset_default_for_tests()


# ─── Singleton ──────────────────────────────────────────────────────────────


def test_singleton_returns_same_instance():
    a = OSController.default()
    b = OSController.default()
    assert a is b


def test_reset_creates_new_instance():
    a = OSController.default()
    OSController.reset_default_for_tests()
    b = OSController.default()
    assert a is not b


# ─── Result Dataclass ───────────────────────────────────────────────────────


def test_result_serialization():
    result = OSActionResult(
        action=OSAction.CLICK,
        ok=True,
        data="clicked at (100, 200)",
        duration_ms=45.2,
    )
    d = result.to_dict()
    assert d["action"] == "click"
    assert d["ok"] is True
    assert d["data"] == "clicked at (100, 200)"
    assert d["duration_ms"] == 45.2


# ─── Dispatch ───────────────────────────────────────────────────────────────


def test_all_actions_have_handlers():
    """Verify every OSAction enum value has a dispatch handler."""
    ctrl = get_os_controller()
    for action in OSAction:
        # Execute with empty/minimal payload — should return a result, not crash
        result = ctrl.execute(action, {})
        assert isinstance(result, OSActionResult)
        assert result.action == action


def test_execute_returns_result():
    ctrl = get_os_controller()
    result = ctrl.execute(OSAction.LIST_WINDOWS)
    assert isinstance(result, OSActionResult)
    assert result.action == OSAction.LIST_WINDOWS


def test_module_level_execute():
    result = execute_os_action(OSAction.LIST_WINDOWS)
    assert isinstance(result, OSActionResult)


# ─── File Operations ────────────────────────────────────────────────────────


def test_create_and_read_file():
    ctrl = get_os_controller()

    with tempfile.NamedTemporaryFile(suffix=".txt", delete=False) as tmp:
        path = tmp.name

    try:
        # Create
        result = ctrl.execute(
            OSAction.CREATE_FILE, {"path": path, "content": "hello world"}
        )
        assert result.ok is True
        assert "created" in (result.data or "")

        # Read
        result = ctrl.execute(OSAction.READ_FILE, {"path": path})
        assert result.ok is True
        assert "hello world" in (result.data or "")
    finally:
        os.unlink(path)


def test_write_file():
    ctrl = get_os_controller()

    with tempfile.NamedTemporaryFile(suffix=".txt", delete=False) as tmp:
        path = tmp.name

    try:
        result = ctrl.execute(
            OSAction.WRITE_FILE, {"path": path, "content": "new content"}
        )
        assert result.ok is True

        with open(path) as f:
            assert f.read() == "new content"
    finally:
        os.unlink(path)


def test_create_file_missing_path():
    ctrl = get_os_controller()
    result = ctrl.execute(OSAction.CREATE_FILE, {})
    assert result.ok is False
    assert "missing path" in (result.error or "")


def test_read_file_missing_path():
    ctrl = get_os_controller()
    result = ctrl.execute(OSAction.READ_FILE, {})
    assert result.ok is False
    assert "missing path" in (result.error or "")


def test_read_file_nonexistent():
    ctrl = get_os_controller()
    result = ctrl.execute(
        OSAction.READ_FILE, {"path": "/tmp/nonexistent_eos_test_file.txt"}
    )
    assert result.ok is False


# ─── Input Actions — Missing Parameters ─────────────────────────────────────


def test_type_text_missing():
    ctrl = get_os_controller()
    result = ctrl.execute(OSAction.TYPE_TEXT, {})
    assert result.ok is False
    assert "missing text" in (result.error or "")


def test_press_keys_missing():
    ctrl = get_os_controller()
    result = ctrl.execute(OSAction.PRESS_KEYS, {})
    assert result.ok is False
    assert "missing keys" in (result.error or "")


def test_scroll_zero():
    ctrl = get_os_controller()
    result = ctrl.execute(OSAction.SCROLL, {"amount": 0})
    assert result.ok is False
    assert "zero" in (result.error or "")


def test_open_app_missing():
    ctrl = get_os_controller()
    result = ctrl.execute(OSAction.OPEN_APP, {})
    assert result.ok is False
    assert "missing app_name" in (result.error or "")


def test_focus_window_missing():
    ctrl = get_os_controller()
    result = ctrl.execute(OSAction.FOCUS_WINDOW, {})
    assert result.ok is False
    assert "missing window_name" in (result.error or "")


# ─── Thread Safety ──────────────────────────────────────────────────────────


def test_concurrent_file_operations():
    ctrl = get_os_controller()
    errors: list[str] = []

    def create_and_read(n: int) -> None:
        try:
            path = f"/tmp/eos_test_concurrent_{n}.txt"
            ctrl.execute(OSAction.CREATE_FILE, {"path": path, "content": f"thread {n}"})
            result = ctrl.execute(OSAction.READ_FILE, {"path": path})
            if not result.ok:
                errors.append(f"thread {n}: read failed")
            os.unlink(path)
        except Exception as exc:
            errors.append(str(exc))

    threads = [threading.Thread(target=create_and_read, args=(n,)) for n in range(5)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert not errors


# ─── Enum Values ────────────────────────────────────────────────────────────


def test_os_action_values():
    assert OSAction.OPEN_APP.value == "open_app"
    assert OSAction.FOCUS_WINDOW.value == "focus_window"
    assert OSAction.TYPE_TEXT.value == "type_text"
    assert OSAction.PRESS_KEYS.value == "press_keys"
    assert OSAction.MOVE_MOUSE.value == "move_mouse"
    assert OSAction.CLICK.value == "click"
    assert OSAction.SCROLL.value == "scroll"
    assert OSAction.READ_SCREEN.value == "read_screen"
    assert OSAction.CREATE_FILE.value == "create_file"
    assert OSAction.READ_FILE.value == "read_file"
    assert OSAction.WRITE_FILE.value == "write_file"
    assert OSAction.LIST_WINDOWS.value == "list_windows"


# ─── Duration Tracking ─────────────────────────────────────────────────────


def test_execute_records_duration():
    ctrl = get_os_controller()
    result = ctrl.execute(OSAction.READ_FILE, {"path": "/dev/null"})
    assert result.duration_ms >= 0
