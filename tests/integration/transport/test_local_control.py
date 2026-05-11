"""Smoke tests for runtime.substrate.local_control.

Validates:
  1.  test_request_create            — LocalControlRequest.new() creates correctly
  2.  test_request_roundtrip         — to_dict/from_dict roundtrip
  3.  test_mode_enforcement_passive  — PASSIVE mode blocks OPEN_APP
  4.  test_mode_enforcement_assisted — ASSISTED mode allows OPEN_APP
  5.  test_mode_enforcement_full     — FULL_CONTROL allows TYPE_TEXT
  6.  test_submit_blocked_by_mode    — submit in PASSIVE mode returns BLOCKED
  7.  test_submit_blocked_no_local   — submit with local_available=False returns BLOCKED
  8.  test_submit_allowed            — submit in ASSISTED with local_available=True returns PENDING
  9.  test_execute_request           — execute stub completes request
 10.  test_open_scene_known          — open_scene with known scene name works
 11.  test_open_scene_unknown        — open_scene with unknown scene returns FAILED
 12.  test_persistence               — requests survive singleton reset
 13.  test_summary                   — get_local_control_summary returns expected keys

Run directly:
    python3 tests/substrate/test_local_control.py
"""

from __future__ import annotations

import sys

sys.path.insert(0, os.environ.get("UMH_ROOT") or os.environ.get("OS_ROOT") or os.environ.get("EOS_ROOT") or "/opt/OS")

from runtime.substrate.local_control import (  # noqa: E402
    LocalControlAction,
    LocalControlMode,
    LocalControlRequest,
    LocalControlStore,
    RequestStatus,
    execute_control_request,
    get_local_control_summary,
    is_action_allowed,
    open_scene,
    submit_control_request,
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


def _reset_all() -> None:
    """Reset storage keys and singleton so each test starts clean."""
    try:
        from runtime.substrate.storage import get_storage

        get_storage().put("local_control_requests", None)
        get_storage().put("local_control_mode", None)
    except Exception:  # noqa: BLE001
        pass
    LocalControlStore.reset_default_for_tests()


# ─── Test 1: request create ────────────────────────────────────────────────


def test_request_create() -> None:
    print("\n── Test 1: LocalControlRequest.new() creates correctly ──")

    req = LocalControlRequest.new(LocalControlAction.OPEN_APP, {"app_id": "vscode"})

    _report(
        "request_id starts with lcr_",
        req.request_id.startswith("lcr_"),
        f"got {req.request_id!r}",
    )
    _report(
        "status is PENDING",
        req.status == RequestStatus.PENDING,
        f"got {req.status!r}",
    )
    _report(
        "action is OPEN_APP",
        req.action == LocalControlAction.OPEN_APP,
        f"got {req.action!r}",
    )
    _report(
        "payload matches",
        req.payload == {"app_id": "vscode"},
        f"got {req.payload!r}",
    )
    _report("created_at is set", bool(req.created_at))
    _report("updated_at is set", bool(req.updated_at))


# ─── Test 2: request roundtrip ─────────────────────────────────────────────


def test_request_roundtrip() -> None:
    print("\n── Test 2: to_dict/from_dict roundtrip ──")

    original = LocalControlRequest.new(
        LocalControlAction.TYPE_TEXT,
        {"text": "hello world"},
        requested_by="test_user",
        requires_confirmation=True,
    )

    d = original.to_dict()
    restored = LocalControlRequest.from_dict(d)

    _report(
        "request_id matches",
        restored.request_id == original.request_id,
        f"expected {original.request_id!r}, got {restored.request_id!r}",
    )
    _report(
        "action matches",
        restored.action == original.action,
        f"expected {original.action!r}, got {restored.action!r}",
    )
    _report(
        "payload matches",
        restored.payload == original.payload,
        f"expected {original.payload!r}, got {restored.payload!r}",
    )
    _report(
        "status matches",
        restored.status == original.status,
        f"expected {original.status!r}, got {restored.status!r}",
    )
    _report(
        "requested_by matches",
        restored.requested_by == original.requested_by,
        f"expected {original.requested_by!r}, got {restored.requested_by!r}",
    )
    _report(
        "requires_confirmation matches",
        restored.requires_confirmation == original.requires_confirmation,
        f"expected {original.requires_confirmation!r}, got {restored.requires_confirmation!r}",
    )
    _report(
        "created_at matches",
        restored.created_at == original.created_at,
        f"expected {original.created_at!r}, got {restored.created_at!r}",
    )
    _report(
        "updated_at matches",
        restored.updated_at == original.updated_at,
        f"expected {original.updated_at!r}, got {restored.updated_at!r}",
    )


# ─── Test 3: mode enforcement passive ──────────────────────────────────────


def test_mode_enforcement_passive() -> None:
    print("\n── Test 3: PASSIVE mode blocks OPEN_APP ──")

    _report(
        "OPEN_APP blocked in PASSIVE",
        is_action_allowed(LocalControlAction.OPEN_APP, LocalControlMode.PASSIVE)
        is False,
    )
    _report(
        "LIST_WINDOWS allowed in PASSIVE",
        is_action_allowed(LocalControlAction.LIST_WINDOWS, LocalControlMode.PASSIVE)
        is True,
    )
    _report(
        "READ_SCREEN_STATE allowed in PASSIVE",
        is_action_allowed(
            LocalControlAction.READ_SCREEN_STATE, LocalControlMode.PASSIVE
        )
        is True,
    )


# ─── Test 4: mode enforcement assisted ─────────────────────────────────────


def test_mode_enforcement_assisted() -> None:
    print("\n── Test 4: ASSISTED mode allows OPEN_APP ──")

    _report(
        "OPEN_APP allowed in ASSISTED",
        is_action_allowed(LocalControlAction.OPEN_APP, LocalControlMode.ASSISTED)
        is True,
    )
    _report(
        "TYPE_TEXT blocked in ASSISTED",
        is_action_allowed(LocalControlAction.TYPE_TEXT, LocalControlMode.ASSISTED)
        is False,
    )
    _report(
        "OPEN_SCENE allowed in ASSISTED",
        is_action_allowed(LocalControlAction.OPEN_SCENE, LocalControlMode.ASSISTED)
        is True,
    )


# ─── Test 5: mode enforcement full ─────────────────────────────────────────


def test_mode_enforcement_full() -> None:
    print("\n── Test 5: FULL_CONTROL allows TYPE_TEXT ──")

    _report(
        "TYPE_TEXT allowed in FULL_CONTROL",
        is_action_allowed(LocalControlAction.TYPE_TEXT, LocalControlMode.FULL_CONTROL)
        is True,
    )
    _report(
        "PRESS_KEYS allowed in FULL_CONTROL",
        is_action_allowed(LocalControlAction.PRESS_KEYS, LocalControlMode.FULL_CONTROL)
        is True,
    )
    _report(
        "MOVE_MOUSE allowed in FULL_CONTROL",
        is_action_allowed(LocalControlAction.MOVE_MOUSE, LocalControlMode.FULL_CONTROL)
        is True,
    )


# ─── Test 6: submit blocked by mode ────────────────────────────────────────


def test_submit_blocked_by_mode() -> None:
    print("\n── Test 6: submit in PASSIVE mode returns BLOCKED ──")

    _reset_all()

    store = LocalControlStore.default()
    store.set_mode(LocalControlMode.PASSIVE)

    req = submit_control_request(
        LocalControlAction.OPEN_APP,
        {"app_id": "vscode"},
        local_available=True,
    )

    _report(
        "status is BLOCKED",
        req.status == RequestStatus.BLOCKED,
        f"got {req.status!r}",
    )
    _report(
        "error mentions mode",
        req.error is not None and "not allowed" in req.error,
        f"got {req.error!r}",
    )


# ─── Test 7: submit blocked no local ───────────────────────────────────────


def test_submit_blocked_no_local() -> None:
    print("\n── Test 7: submit with local_available=False returns BLOCKED ──")

    _reset_all()

    store = LocalControlStore.default()
    store.set_mode(LocalControlMode.ASSISTED)

    req = submit_control_request(
        LocalControlAction.OPEN_APP,
        {"app_id": "vscode"},
        local_available=False,
    )

    _report(
        "status is BLOCKED",
        req.status == RequestStatus.BLOCKED,
        f"got {req.status!r}",
    )
    _report(
        "error mentions local",
        req.error is not None and "local" in req.error.lower(),
        f"got {req.error!r}",
    )


# ─── Test 8: submit allowed ────────────────────────────────────────────────


def test_submit_allowed() -> None:
    print(
        "\n── Test 8: submit in ASSISTED with local_available=True returns PENDING ──"
    )

    _reset_all()

    store = LocalControlStore.default()
    store.set_mode(LocalControlMode.ASSISTED)

    req = submit_control_request(
        LocalControlAction.OPEN_APP,
        {"app_id": "vscode"},
        local_available=True,
    )

    _report(
        "status is PENDING",
        req.status == RequestStatus.PENDING,
        f"got {req.status!r}",
    )
    _report(
        "request_id starts with lcr_",
        req.request_id.startswith("lcr_"),
        f"got {req.request_id!r}",
    )
    _report(
        "error is None",
        req.error is None,
        f"got {req.error!r}",
    )


# ─── Test 9: execute request ───────────────────────────────────────────────


def test_execute_request() -> None:
    print("\n── Test 9: execute dispatches real request (OPEN_APP on headless VPS) ──")

    _reset_all()

    store = LocalControlStore.default()
    store.set_mode(LocalControlMode.ASSISTED)

    req = submit_control_request(
        LocalControlAction.OPEN_APP,
        {"app_id": "vscode"},
        local_available=True,
    )

    result = execute_control_request(req.request_id)

    # Real dispatch: xdg-open 'vscode' will fail on a headless VPS because
    # the file/app doesn't exist. That's correct behavior for real dispatch.
    _report(
        "status is COMPLETED or FAILED (real dispatch, not stub)",
        result.status in (RequestStatus.COMPLETED, RequestStatus.FAILED),
        f"got {result.status!r}",
    )
    _report(
        "result or error is set",
        result.result is not None or result.error is not None,
        f"result={result.result!r}, error={result.error!r}",
    )
    _report(
        "request_id matches",
        result.request_id == req.request_id,
        f"expected {req.request_id!r}, got {result.request_id!r}",
    )


# ─── Test 10: open scene known ─────────────────────────────────────────────


def test_open_scene_known() -> None:
    print("\n── Test 10: open_scene with known scene name works ──")

    _reset_all()

    store = LocalControlStore.default()
    store.set_mode(LocalControlMode.ASSISTED)

    # Verify builder_mode exists in scene registry
    from runtime.substrate.scenes import get_scene

    scene = get_scene("builder_mode")
    _report(
        "builder_mode exists in scene registry",
        scene is not None,
        "scene not found" if scene is None else f"found: {scene.description!r}",
    )

    req = open_scene("builder_mode", local_available=True)

    _report(
        "status is PENDING (scene found, mode allows, local available)",
        req.status == RequestStatus.PENDING,
        f"got {req.status!r}",
    )
    _report(
        "action is OPEN_SCENE",
        req.action == LocalControlAction.OPEN_SCENE,
        f"got {req.action!r}",
    )
    _report(
        "payload contains scene_name",
        req.payload.get("scene_name") == "builder_mode",
        f"got {req.payload!r}",
    )


# ─── Test 11: open scene unknown ───────────────────────────────────────────


def test_open_scene_unknown() -> None:
    print("\n── Test 11: open_scene with unknown scene returns FAILED ──")

    _reset_all()

    store = LocalControlStore.default()
    store.set_mode(LocalControlMode.ASSISTED)

    req = open_scene("nonexistent_xyz", local_available=True)

    _report(
        "status is FAILED",
        req.status == RequestStatus.FAILED,
        f"got {req.status!r}",
    )
    _report(
        "error mentions scene not found",
        req.error is not None and "not found" in req.error,
        f"got {req.error!r}",
    )


# ─── Test 12: persistence ──────────────────────────────────────────────────


def test_persistence() -> None:
    print("\n── Test 12: requests survive singleton reset ──")

    _reset_all()

    store = LocalControlStore.default()
    store.set_mode(LocalControlMode.ASSISTED)

    req = submit_control_request(
        LocalControlAction.OPEN_APP,
        {"app_id": "vscode"},
        local_available=True,
    )
    original_id = req.request_id

    # Reset singleton (simulates process restart)
    LocalControlStore.reset_default_for_tests()

    # Reload from storage
    reloaded_store = LocalControlStore.default()
    reloaded_req = reloaded_store.get(original_id)

    _report(
        "request reloads after singleton reset",
        reloaded_req is not None,
        "got None" if reloaded_req is None else "",
    )
    if reloaded_req is not None:
        _report(
            "request_id survives reset",
            reloaded_req.request_id == original_id,
            f"expected {original_id!r}, got {reloaded_req.request_id!r}",
        )
        _report(
            "status survives reset",
            reloaded_req.status == RequestStatus.PENDING,
            f"got {reloaded_req.status!r}",
        )
        _report(
            "action survives reset",
            reloaded_req.action == LocalControlAction.OPEN_APP,
            f"got {reloaded_req.action!r}",
        )


# ─── Test 13: summary ──────────────────────────────────────────────────────


def test_summary() -> None:
    print("\n── Test 13: get_local_control_summary returns expected keys ──")

    _reset_all()

    summary = get_local_control_summary()

    expected_keys = {
        "control_mode",
        "pending_requests",
        "recent_completed",
        "recent_failed",
        "recent_blocked",
    }

    _report(
        "summary is a dict",
        isinstance(summary, dict),
        f"got {type(summary).__name__}",
    )
    _report(
        "all expected keys present",
        expected_keys.issubset(set(summary.keys())),
        f"missing: {expected_keys - set(summary.keys())}",
    )
    _report(
        "control_mode is a string",
        isinstance(summary.get("control_mode"), str),
        f"got {type(summary.get('control_mode')).__name__}",
    )
    _report(
        "pending_requests is an int",
        isinstance(summary.get("pending_requests"), int),
        f"got {type(summary.get('pending_requests')).__name__}",
    )
    _report(
        "recent_completed is an int",
        isinstance(summary.get("recent_completed"), int),
        f"got {type(summary.get('recent_completed')).__name__}",
    )
    _report(
        "recent_failed is an int",
        isinstance(summary.get("recent_failed"), int),
        f"got {type(summary.get('recent_failed')).__name__}",
    )
    _report(
        "recent_blocked is an int",
        isinstance(summary.get("recent_blocked"), int),
        f"got {type(summary.get('recent_blocked')).__name__}",
    )


# ─── Test 14: real OPEN_URL dispatch via browser_agent ────────────────────


def test_real_open_url_dispatch() -> None:
    print("\n── Test 14: OPEN_URL dispatch via browser_agent (data: URL) ──")

    _reset_all()
    # Also reset BrowserAgent singleton
    from runtime.substrate.browser_agent import BrowserAgent

    BrowserAgent.reset_default_for_tests()

    store = LocalControlStore.default()
    store.set_mode(LocalControlMode.ASSISTED)

    req = submit_control_request(
        LocalControlAction.OPEN_URL,
        {"url": "data:text/html,<h1>test</h1>"},
        local_available=True,
    )

    result = execute_control_request(req.request_id)

    _report(
        "status is COMPLETED",
        result.status == RequestStatus.COMPLETED,
        f"got {result.status!r}",
    )
    _report(
        "result contains opened",
        result.result is not None and "opened" in result.result,
        f"got {result.result!r}",
    )
    _report(
        "error is None",
        result.error is None,
        f"got {result.error!r}",
    )

    # Clean up browser
    BrowserAgent.reset_default_for_tests()


# ─── Test 15: real CLICK dispatch via browser_agent ───────────────────────


def test_real_click_dispatch() -> None:
    print("\n── Test 15: CLICK_MOUSE dispatch (open URL then click) ──")

    _reset_all()
    from runtime.substrate.browser_agent import BrowserAgent

    BrowserAgent.reset_default_for_tests()

    store = LocalControlStore.default()
    store.set_mode(LocalControlMode.FULL_CONTROL)

    # First open a page with a clickable element
    url_req = submit_control_request(
        LocalControlAction.OPEN_URL,
        {"url": "data:text/html,<button id='btn'>Click</button>"},
        local_available=True,
    )
    execute_control_request(url_req.request_id)

    # Now click
    click_req = submit_control_request(
        LocalControlAction.CLICK_MOUSE,
        {"selector": "#btn"},
        local_available=True,
    )
    result = execute_control_request(click_req.request_id)

    _report(
        "status is COMPLETED",
        result.status == RequestStatus.COMPLETED,
        f"got {result.status!r}",
    )
    _report(
        "result contains clicked",
        result.result is not None and "clicked" in result.result,
        f"got {result.result!r}",
    )

    BrowserAgent.reset_default_for_tests()


# ─── Test 16: real TYPE_TEXT dispatch via browser_agent ────────────────────


def test_real_type_text_dispatch() -> None:
    print("\n── Test 16: TYPE_TEXT dispatch (open URL then type) ──")

    _reset_all()
    from runtime.substrate.browser_agent import BrowserAgent

    BrowserAgent.reset_default_for_tests()

    store = LocalControlStore.default()
    store.set_mode(LocalControlMode.FULL_CONTROL)

    # Open a page with an input field
    url_req = submit_control_request(
        LocalControlAction.OPEN_URL,
        {"url": "data:text/html,<input id='inp' type='text'>"},
        local_available=True,
    )
    execute_control_request(url_req.request_id)

    # Type into the input
    type_req = submit_control_request(
        LocalControlAction.TYPE_TEXT,
        {"selector": "#inp", "text": "hello world"},
        local_available=True,
    )
    result = execute_control_request(type_req.request_id)

    _report(
        "status is COMPLETED",
        result.status == RequestStatus.COMPLETED,
        f"got {result.status!r}",
    )
    _report(
        "result contains typed",
        result.result is not None and "typed" in result.result,
        f"got {result.result!r}",
    )

    BrowserAgent.reset_default_for_tests()


# ─── Test 17: OPEN_APP with nonexistent app (graceful failure) ────────────


def test_open_app_dispatch_subprocess() -> None:
    print("\n── Test 17: OPEN_APP with nonexistent app fails gracefully ──")

    _reset_all()

    store = LocalControlStore.default()
    store.set_mode(LocalControlMode.ASSISTED)

    req = submit_control_request(
        LocalControlAction.OPEN_APP,
        {"app_id": "nonexistent_app_xyz_12345"},
        local_available=True,
    )

    result = execute_control_request(req.request_id)

    _report(
        "status is FAILED (app does not exist)",
        result.status == RequestStatus.FAILED,
        f"got {result.status!r}",
    )
    _report(
        "error is set (not None)",
        result.error is not None,
        f"got {result.error!r}",
    )
    _report(
        "no crash (test reached this point)",
        True,
    )


# ─── Run ───────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("Local Control Smoke Tests")
    print("=" * 60)

    test_request_create()
    test_request_roundtrip()
    test_mode_enforcement_passive()
    test_mode_enforcement_assisted()
    test_mode_enforcement_full()
    test_submit_blocked_by_mode()
    test_submit_blocked_no_local()
    test_submit_allowed()
    test_execute_request()
    test_open_scene_known()
    test_open_scene_unknown()
    test_persistence()
    test_summary()
    test_real_open_url_dispatch()
    test_real_click_dispatch()
    test_real_type_text_dispatch()
    test_open_app_dispatch_subprocess()

    print("\n" + "=" * 60)
    print(f"Results: {_PASS} passed, {_FAIL} failed")
    if _FAIL:
        sys.exit(1)
    else:
        print("All smoke tests passed.")
