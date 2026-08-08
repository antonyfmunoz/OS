"""Wave 2 run_passes runner-lifecycle invariant.

Root-cause regression: 16+ consecutive w16_ab_running_concurrent failures were
caused by the runner creating workers before the collector reached w15. The
collector takes ~15-19 minutes to navigate w01-w15 on Beast, but the runner
finds stale authorized plans and creates workers that complete in ~100s — long
before the collector reaches w16 to observe them.

These tests verify that `run_passes` for the `full` scenario:
1. Dispatches the collector BEFORE starting the runner.
2. Waits for the collector to reach w15 before starting the runner.
3. Calls `stop_runner` after poll completes (even on failure).
4. Does NOT start a runner for `smoke` scenario.
5. Fails closed when `seed_fixture` fails.
6. Fails closed when `start_runner` fails.
7. Fails closed when collector dispatch fails.
8. Fails closed when collector doesn't reach w15.
"""

from __future__ import annotations

import contextlib
import sys
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

_WORKTREE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_WORKTREE))


def _import_dispatch():
    """Import the dispatch module with env resolution suppressed."""
    import importlib

    spec = importlib.util.spec_from_file_location(
        "wave2_field_dispatch",
        str(_WORKTREE / "scripts" / "wave2_field_dispatch.py"),
    )
    mod = importlib.util.module_from_spec(spec)
    # Suppress _resolve_env() and global resolution at import time
    mod._ORIGIN = "https://test.example:10443"
    mod._MESH_NODE_ID = "test-node"
    sys.modules["wave2_field_dispatch"] = mod
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture(scope="module")
def dispatch_mod():
    mod = _import_dispatch()
    yield mod
    sys.modules.pop("wave2_field_dispatch", None)


class _FakeRunner:
    """Minimal Runner stub for testing run_passes logic."""

    dry_run = True

    def run(self, cmd, timeout=30, capture=False, check=True):
        return MagicMock(returncode=0, stdout="{}")


def _full_scenario_patches(dispatch_mod, **overrides):
    """Return the standard patch set for full-scenario tests.

    Defaults: seed succeeds, collector dispatches ok, collector reaches w15,
    runner starts ok, poll returns passed, stop ok.
    """
    defaults = {
        "seed_fixture": lambda runner, sha, run_id, variant: {
            "dest": "/tmp/test_fixture",
            "variant": variant,
            "run_id": run_id,
        },
        "_dispatch_collector": lambda runner, *, run_id, pass_num, scenario, sha: {
            "ok": True,
            "run_id": run_id,
            "pass_num": pass_num,
        },
        "_wait_collector_authorization": lambda runner, run_id, pass_num, timeout_min=25: True,
        "_wait_for_bindable_grant": lambda runner, *, sha, run_id, timeout_s=300.0, interval_s=3.0: (
            object(),
            "",
        ),
        "write_scenario_map": lambda runner, sha, run_id: {
            "written": True,
            "run_id": run_id,
        },
        "start_runner": lambda runner, sha, run_id, max_iterations: {
            "started": True,
            "dry_run": True,
        },
        "_poll_status": lambda runner, run_id, pass_num, timeout_min=30, max_mesh_failures=5: {
            "state": "passed",
            "run_id": run_id,
            "stages_done": 36,
        },
        "stop_runner": lambda runner, sha, run_id: {"stopped": True},
        "_wait_candidate_ready": lambda runner, timeout_s=120.0: {"ready": True},
        "_verify_beast_collector_commit": lambda runner, sha: {"ok": True},
    }
    defaults.update(overrides)
    patches = []
    for name, side_effect in defaults.items():
        patches.append(patch.object(dispatch_mod, name, side_effect=side_effect))
    return patches


@contextlib.contextmanager
def _apply(patches):
    """Apply every patch in the list regardless of count (order-agnostic)."""
    with contextlib.ExitStack() as stack:
        for p in patches:
            stack.enter_context(p)
        yield


def test_full_scenario_dispatches_collector_before_starting_runner(dispatch_mod):
    """Full scenario must dispatch collector and wait for w15 BEFORE starting runner."""
    call_order: list[str] = []

    def track(name, fn):
        def wrapper(*a, **kw):
            call_order.append(name)
            return fn(*a, **kw)

        return wrapper

    patches = _full_scenario_patches(
        dispatch_mod,
        seed_fixture=track(
            "seed_fixture",
            lambda *a, **kw: {
                "dest": "/tmp/test",
                "variant": "clean",
                "run_id": "r1",
            },
        ),
        _dispatch_collector=track(
            "dispatch_collector",
            lambda *a, **kw: {
                "ok": True,
                "run_id": "r1",
                "pass_num": 1,
            },
        ),
        _wait_collector_authorization=track("wait_w15", lambda *a, **kw: True),
        start_runner=track(
            "start_runner",
            lambda *a, **kw: {
                "started": True,
                "dry_run": True,
            },
        ),
        _poll_status=track(
            "poll_status",
            lambda *a, **kw: {
                "state": "passed",
                "run_id": "r1",
            },
        ),
        stop_runner=track("stop_runner", lambda *a, **kw: {"stopped": True}),
    )

    runner = _FakeRunner()
    with _apply(patches):
        result = dispatch_mod.run_passes(runner, sha="abc123", scenario="full", passes=1)

    expected = [
        "seed_fixture",
        "dispatch_collector",
        "wait_w15",
        "start_runner",
        "poll_status",
        "stop_runner",
    ]
    assert call_order == expected, (
        f"Expected seed→dispatch→wait_w15→start→poll→stop, got {call_order}"
    )
    assert result["results"][0]["ok"] is True


def test_smoke_scenario_does_not_start_runner(dispatch_mod):
    """Smoke scenario must NOT call seed_fixture or start_runner."""
    call_order: list[str] = []

    def fake_dispatch(runner, *, run_id, pass_num, scenario, sha):
        call_order.append("dispatch_pass")
        return {"ok": True, "run_id": run_id, "dry_run": True}

    def fake_ready(runner, timeout_s=120.0):
        return {"ready": True}

    def fake_binding(runner, sha):
        return {"ok": True}

    runner = _FakeRunner()
    with (
        patch.object(
            dispatch_mod,
            "seed_fixture",
            side_effect=lambda *a, **k: (_ for _ in ()).throw(
                AssertionError("seed_fixture called in smoke")
            ),
        ),
        patch.object(
            dispatch_mod,
            "start_runner",
            side_effect=lambda *a, **k: (_ for _ in ()).throw(
                AssertionError("start_runner called in smoke")
            ),
        ),
        patch.object(dispatch_mod, "dispatch_pass", side_effect=fake_dispatch),
        patch.object(dispatch_mod, "_wait_candidate_ready", side_effect=fake_ready),
        patch.object(dispatch_mod, "_verify_beast_collector_commit", side_effect=fake_binding),
    ):
        result = dispatch_mod.run_passes(runner, sha="abc123", scenario="smoke", passes=1)

    assert call_order == ["dispatch_pass"]
    assert result["passes"] == 1


def test_full_scenario_stops_runner_on_poll_failure(dispatch_mod):
    """Runner must be stopped even if _poll_status raises."""
    stopped = []

    patches = _full_scenario_patches(
        dispatch_mod,
        _poll_status=lambda *a, **kw: (_ for _ in ()).throw(RuntimeError("poll crash")),
        stop_runner=lambda runner, sha, run_id: (stopped.append(run_id), {"stopped": True})[1],
    )

    runner = _FakeRunner()
    with _apply(patches):
        with pytest.raises(RuntimeError):
            dispatch_mod.run_passes(runner, sha="abc123", scenario="full", passes=1)

    assert len(stopped) == 1, "Runner must be stopped even on poll failure"


def test_full_scenario_fails_closed_on_seed_failure(dispatch_mod):
    """If seed_fixture fails, no collector dispatch or runner should happen."""
    call_order: list[str] = []

    patches = _full_scenario_patches(
        dispatch_mod,
        seed_fixture=lambda *a, **kw: (call_order.append("seed_fixture"), {})[1],
        _dispatch_collector=lambda *a, **kw: (_ for _ in ()).throw(
            AssertionError("dispatch after seed failure")
        ),
        start_runner=lambda *a, **kw: (_ for _ in ()).throw(
            AssertionError("runner after seed failure")
        ),
    )

    runner = _FakeRunner()
    with _apply(patches):
        result = dispatch_mod.run_passes(runner, sha="abc123", scenario="full", passes=1)

    assert call_order == ["seed_fixture"]
    assert result["results"][0]["ok"] is False
    assert "seed_fixture" in result["results"][0]["error"]


def test_full_scenario_fails_closed_on_runner_start_failure(dispatch_mod):
    """If start_runner fails, no poll should happen."""
    call_order: list[str] = []

    patches = _full_scenario_patches(
        dispatch_mod,
        seed_fixture=lambda *a, **kw: (
            call_order.append("seed"),
            {"dest": "/tmp/t", "variant": "clean", "run_id": "r1"},
        )[1],
        _dispatch_collector=lambda *a, **kw: (
            call_order.append("dispatch"),
            {"ok": True, "run_id": "r1", "pass_num": 1},
        )[1],
        _wait_collector_authorization=lambda *a, **kw: (call_order.append("wait"), True)[1],
        start_runner=lambda *a, **kw: (
            call_order.append("start"),
            {"started": False, "reason": "isolation fail"},
        )[1],
        _poll_status=lambda *a, **kw: (_ for _ in ()).throw(
            AssertionError("poll after runner failure")
        ),
    )

    runner = _FakeRunner()
    with _apply(patches):
        result = dispatch_mod.run_passes(runner, sha="abc123", scenario="full", passes=1)

    assert call_order == ["seed", "dispatch", "wait", "start"]
    assert result["results"][0]["ok"] is False
    assert "start_runner" in result["results"][0]["error"]


def test_full_scenario_fails_closed_on_collector_dispatch_failure(dispatch_mod):
    """If collector dispatch fails, runner must not start."""
    call_order: list[str] = []

    patches = _full_scenario_patches(
        dispatch_mod,
        seed_fixture=lambda *a, **kw: (
            call_order.append("seed"),
            {"dest": "/tmp/t", "variant": "clean", "run_id": "r1"},
        )[1],
        _dispatch_collector=lambda *a, **kw: (
            call_order.append("dispatch"),
            {"ok": False, "error": "mesh down"},
        )[1],
        start_runner=lambda *a, **kw: (_ for _ in ()).throw(
            AssertionError("runner after dispatch failure")
        ),
    )

    runner = _FakeRunner()
    with _apply(patches):
        result = dispatch_mod.run_passes(runner, sha="abc123", scenario="full", passes=1)

    assert call_order == ["seed", "dispatch"]
    assert result["results"][0]["ok"] is False


def test_full_scenario_fails_closed_when_collector_doesnt_reach_w15(dispatch_mod):
    """If collector doesn't reach w15, runner must not start."""
    call_order: list[str] = []

    patches = _full_scenario_patches(
        dispatch_mod,
        seed_fixture=lambda *a, **kw: (
            call_order.append("seed"),
            {"dest": "/tmp/t", "variant": "clean", "run_id": "r1"},
        )[1],
        _dispatch_collector=lambda *a, **kw: (
            call_order.append("dispatch"),
            {"ok": True, "run_id": "r1", "pass_num": 1},
        )[1],
        _wait_collector_authorization=lambda *a, **kw: (call_order.append("wait"), False)[1],
        start_runner=lambda *a, **kw: (_ for _ in ()).throw(
            AssertionError("runner when w15 not reached")
        ),
    )

    runner = _FakeRunner()
    with _apply(patches):
        result = dispatch_mod.run_passes(runner, sha="abc123", scenario="full", passes=1)

    assert call_order == ["seed", "dispatch", "wait"]
    assert result["results"][0]["ok"] is False
    assert "w15" in result["results"][0]["error"]


def test_multi_pass_starts_runner_per_pass(dispatch_mod):
    """Each pass gets its own runner (run-scoped spool/targets)."""
    starts: list[str] = []
    stops: list[str] = []

    patches = _full_scenario_patches(
        dispatch_mod,
        start_runner=lambda runner, sha, run_id, max_iterations: (
            starts.append(run_id),
            {"started": True},
        )[1],
        stop_runner=lambda runner, sha, run_id: (stops.append(run_id), {"stopped": True})[1],
    )

    runner = _FakeRunner()
    with _apply(patches):
        result = dispatch_mod.run_passes(runner, sha="abc123", scenario="full", passes=3)

    assert len(starts) == 3, f"Expected 3 runner starts, got {len(starts)}"
    assert len(stops) == 3, f"Expected 3 runner stops, got {len(stops)}"
    assert len(result["results"]) == 3


# ── Mutation tests (kill resistant) ─────────────────────────────────────────


def test_mutation_omit_seed_fixture_kills_full(dispatch_mod):
    """Mutation: removing seed_fixture call must fail (no fixture = no workers)."""
    called = {"seed": False, "dispatch": False, "start": False}

    patches = _full_scenario_patches(
        dispatch_mod,
        seed_fixture=lambda *a, **kw: (
            called.__setitem__("seed", True),
            {"dest": "/tmp/t", "variant": "clean", "run_id": "r1"},
        )[1],
        _dispatch_collector=lambda *a, **kw: (
            called.__setitem__("dispatch", True),
            {"ok": True, "run_id": "r1", "pass_num": 1},
        )[1],
        start_runner=lambda *a, **kw: (called.__setitem__("start", True), {"started": True})[1],
    )

    runner = _FakeRunner()
    with _apply(patches):
        dispatch_mod.run_passes(runner, sha="abc123", scenario="full", passes=1)

    assert called["seed"], "seed_fixture was not called for full scenario"
    assert called["dispatch"], "collector dispatch was not called for full scenario"
    assert called["start"], "start_runner was not called for full scenario"


def test_mutation_skip_stop_runner_detected(dispatch_mod):
    """Mutation: removing stop_runner must leave the runner alive (detectable)."""
    stopped = []

    patches = _full_scenario_patches(
        dispatch_mod,
        stop_runner=lambda runner, sha, run_id: (stopped.append(run_id), {"stopped": True})[1],
    )

    runner = _FakeRunner()
    with _apply(patches):
        dispatch_mod.run_passes(runner, sha="abc123", scenario="full", passes=1)

    assert len(stopped) == 1, "stop_runner not called — runner would be leaked"


def test_mutation_one_worker_instead_of_two_concurrency(dispatch_mod):
    """Mutation: start_runner must pass max_iterations=0 (run until stopped)."""
    recorded_kwargs: list[dict[str, Any]] = []

    patches = _full_scenario_patches(
        dispatch_mod,
        start_runner=lambda runner, sha, run_id, max_iterations: (
            recorded_kwargs.append({"max_iterations": max_iterations}),
            {"started": True},
        )[1],
    )

    runner = _FakeRunner()
    with _apply(patches):
        dispatch_mod.run_passes(runner, sha="abc123", scenario="full", passes=1)

    assert recorded_kwargs[0]["max_iterations"] == 0, (
        "Runner must run until stopped (max_iterations=0)"
    )


def test_mutation_collector_dispatched_before_runner(dispatch_mod):
    """Mutation: the collector MUST be dispatched before runner starts.

    This is the core invariant that prevents the w16 timing race. If the runner
    starts first, it finds stale grants and creates workers that complete before
    the collector reaches w16 to observe them.
    """
    order: list[str] = []

    patches = _full_scenario_patches(
        dispatch_mod,
        _dispatch_collector=lambda *a, **kw: (
            order.append("dispatch"),
            {"ok": True, "run_id": "r1", "pass_num": 1},
        )[1],
        _wait_collector_authorization=lambda *a, **kw: (order.append("wait_w15"), True)[1],
        start_runner=lambda *a, **kw: (order.append("runner"), {"started": True})[1],
    )

    runner = _FakeRunner()
    with _apply(patches):
        dispatch_mod.run_passes(runner, sha="abc123", scenario="full", passes=1)

    assert order.index("dispatch") < order.index("runner"), (
        f"Collector must dispatch before runner starts. Order: {order}"
    )
    assert order.index("wait_w15") < order.index("runner"), (
        f"Must wait for w15 before runner starts. Order: {order}"
    )


# ── Green-pass authenticated-binding lifecycle (harness binding-gap fix) ──────
#
# Root-cause regression: `run_passes` (green path) went w15 → start_runner,
# omitting the execution-binding materialization the qualified failure/recovery
# driver performs. With no `execution_binding.json`, the runner's attempt-
# creation boundary read an UNANSWERABLE declaration and stayed SEALED — zero
# Attempts, whole A+B→C→D graph failed (field run 20260808T053806Z-p1). These
# pin: green now writes the authenticated binding BEFORE the runner, differing
# from the failure/recovery path ONLY by the absence of deliberate injection.


class _NonDryRunner:
    """Runner whose non-dry-run branch (the real binding gate) is exercised."""

    dry_run = False

    def run(self, cmd, timeout=30, capture=False, check=True):
        return MagicMock(returncode=0, stdout="{}")


def _order_tracking_patches(dispatch_mod, order, **overrides):
    """Full-scenario patches that append each lifecycle call to `order`."""
    base = {
        "seed_fixture": lambda *a, **kw: (
            order.append("seed"),
            {"dest": "/tmp/t", "variant": "clean", "run_id": "r1"},
        )[1],
        "_dispatch_collector": lambda *a, **kw: (
            order.append("dispatch"),
            {"ok": True, "run_id": "r1", "pass_num": 1},
        )[1],
        "_wait_collector_authorization": lambda *a, **kw: (order.append("wait_w15"), True)[1],
        "_preseed_worktree_substrate": lambda *a, **kw: order.append("preseed"),
        "_wait_for_bindable_grant": lambda *a, **kw: (order.append("grant_wait"), (object(), ""))[
            1
        ],
        "write_scenario_map": lambda *a, **kw: (
            order.append("write_binding"),
            {"written": True, "run_id": "r1"},
        )[1],
        "pause_before_dispatch": lambda *a, **kw: (order.append("pause"), {"paused": True})[1],
        "inject_failure": lambda *a, **kw: (order.append("inject"), {"armed": True})[1],
        "resume_after_pause": lambda *a, **kw: (order.append("resume"), {"released": True})[1],
        "start_runner": lambda *a, **kw: (order.append("runner"), {"started": True})[1],
        "_poll_status": lambda *a, **kw: (
            order.append("poll"),
            {"state": "passed", "run_id": "r1"},
        )[1],
        "stop_runner": lambda *a, **kw: (order.append("stop"), {"stopped": True})[1],
        "_wait_candidate_ready": lambda *a, **kw: {"ready": True},
        "_verify_beast_collector_commit": lambda *a, **kw: {"ok": True},
    }
    base.update(overrides)
    return [patch.object(dispatch_mod, n, side_effect=se) for n, se in base.items()]


def test_green_writes_binding_before_runner_admission(dispatch_mod):
    """T2/T3/T9: green run_passes writes the authenticated binding BEFORE the runner starts."""
    order: list[str] = []
    with _apply(_order_tracking_patches(dispatch_mod, order)):
        dispatch_mod.run_passes(_NonDryRunner(), sha="abc123", scenario="full", passes=1)
    assert "write_binding" in order, "green path must call write_scenario_map"
    assert order.index("write_binding") < order.index("runner"), (
        f"binding must be durable BEFORE runner admission. Order: {order}"
    )
    assert order.index("grant_wait") < order.index("write_binding"), (
        f"grant must be bindable BEFORE write_scenario_map. Order: {order}"
    )


def test_green_grant_wait_precedes_binding_precedes_runner(dispatch_mod):
    """T3/T9: exact green ordering w15 → grant_wait → write_binding → runner."""
    order: list[str] = []
    with _apply(_order_tracking_patches(dispatch_mod, order)):
        dispatch_mod.run_passes(_NonDryRunner(), sha="abc123", scenario="full", passes=1)
    green = [s for s in order if s in {"wait_w15", "grant_wait", "write_binding", "runner"}]
    assert green == ["wait_w15", "grant_wait", "write_binding", "runner"], (
        f"green lifecycle order wrong: {green}"
    )


def test_green_does_not_inject_failure(dispatch_mod):
    """T6: the green path never arms deliberate failure injection."""
    order: list[str] = []
    with _apply(_order_tracking_patches(dispatch_mod, order)):
        dispatch_mod.run_passes(_NonDryRunner(), sha="abc123", scenario="full", passes=1)
    assert "inject" not in order, "green path must NOT call inject_failure"


def test_green_does_not_arm_admission_pause(dispatch_mod):
    """T6: green does not arm/release the admission pause (injection scaffolding only)."""
    order: list[str] = []
    with _apply(_order_tracking_patches(dispatch_mod, order)):
        dispatch_mod.run_passes(_NonDryRunner(), sha="abc123", scenario="full", passes=1)
    assert "pause" not in order and "resume" not in order, (
        "green path must not arm/release the admission pause"
    )


def test_green_fails_closed_when_grant_never_bindable(dispatch_mod):
    """T11/T12: if the grant never becomes bindable, the runner never starts."""
    order: list[str] = []
    patches = _order_tracking_patches(
        dispatch_mod,
        order,
        _wait_for_bindable_grant=lambda *a, **kw: (order.append("grant_wait"), (None, "timeout"))[
            1
        ],
        start_runner=lambda *a, **kw: (_ for _ in ()).throw(
            AssertionError("runner started with no bindable grant")
        ),
        write_scenario_map=lambda *a, **kw: (_ for _ in ()).throw(
            AssertionError("write_scenario_map after unbindable grant")
        ),
    )
    with _apply(patches):
        result = dispatch_mod.run_passes(_NonDryRunner(), sha="abc", scenario="full", passes=1)
    assert result["results"][0]["ok"] is False
    assert "binding" in result["results"][0]["error"].lower()
    assert "runner" not in order


def test_green_fails_closed_when_binding_write_refused(dispatch_mod):
    """T11/T12: if write_scenario_map refuses, no worker attempt / runner start."""
    order: list[str] = []
    patches = _order_tracking_patches(
        dispatch_mod,
        order,
        write_scenario_map=lambda *a, **kw: (
            order.append("write_binding"),
            {"written": False, "error": "no execution_binding.json"},
        )[1],
        start_runner=lambda *a, **kw: (_ for _ in ()).throw(
            AssertionError("runner started with no execution binding")
        ),
    )
    with _apply(patches):
        result = dispatch_mod.run_passes(_NonDryRunner(), sha="abc", scenario="full", passes=1)
    assert result["results"][0]["ok"] is False
    assert "binding" in result["results"][0]["error"].lower()
    assert "runner" not in order


def test_green_reaches_runner_when_binding_durable(dispatch_mod):
    """T1/T13: fresh green with a durable binding reaches runner start + passes."""
    order: list[str] = []
    with _apply(_order_tracking_patches(dispatch_mod, order)):
        result = dispatch_mod.run_passes(_NonDryRunner(), sha="abc", scenario="full", passes=1)
    assert "runner" in order
    assert result["results"][0]["ok"] is True


def test_bindable_grant_wait_reuses_capture_binding(dispatch_mod):
    """T8: the wait derives authority ONLY through _capture_execution_binding.

    Reusing the one binding-capture function (never a copied predicate) is what
    guarantees the wait can't accept something the binding gate would reject.
    """
    calls = {"n": 0}

    def fake_capture(records, *, sha, run_id):
        calls["n"] += 1
        return (object(), "") if calls["n"] >= 2 else (None, "grant not durable yet")

    with (
        patch.object(dispatch_mod, "_read_state_records", side_effect=lambda sha: []),
        patch.object(dispatch_mod, "_capture_execution_binding", side_effect=fake_capture),
        patch.object(dispatch_mod.time, "sleep", side_effect=lambda s: None),
    ):
        binding, err = dispatch_mod._wait_for_bindable_grant(
            _NonDryRunner(), sha="s", run_id="r", timeout_s=30.0, interval_s=0.0
        )
    assert binding is not None and err == ""
    assert calls["n"] >= 2, "must poll _capture_execution_binding until it binds"


def test_bindable_grant_wait_fails_closed_on_timeout(dispatch_mod):
    """T11: the wait fails closed (returns None + reason) when the grant never binds."""
    with (
        patch.object(dispatch_mod, "_read_state_records", side_effect=lambda sha: []),
        patch.object(
            dispatch_mod,
            "_capture_execution_binding",
            side_effect=lambda records, *, sha, run_id: (None, "0 grants carry exact correlation"),
        ),
        patch.object(dispatch_mod.time, "sleep", side_effect=lambda s: None),
        patch.object(
            dispatch_mod.time,
            "monotonic",
            side_effect=[0.0, 0.0, 100.0],  # start, first-check, past-deadline
        ),
    ):
        binding, err = dispatch_mod._wait_for_bindable_grant(
            _NonDryRunner(), sha="s", run_id="r", timeout_s=1.0, interval_s=0.0
        )
    assert binding is None
    assert "not bindable" in err


def test_bindable_grant_wait_dryrun_does_not_block(dispatch_mod):
    """Dry-run returns immediately (no state to read); caller does not gate on it."""
    binding, err = dispatch_mod._wait_for_bindable_grant(_FakeRunner(), sha="s", run_id="r")
    assert binding is None and err == "dry-run"


# ── Most-important regression + its killing mutations ────────────────────────


def test_regression_fresh_green_binding_before_admission_ABCD(dispatch_mod):
    """MOST IMPORTANT: fresh green → binding durable BEFORE runner admission → run proceeds.

    The mutation `remove write_scenario_map from run_passes` MUST kill this test.
    """
    order: list[str] = []
    with _apply(_order_tracking_patches(dispatch_mod, order)):
        result = dispatch_mod.run_passes(_NonDryRunner(), sha="abc", scenario="full", passes=1)
    # binding materialized, and materialized before the runner admitted work
    assert "write_binding" in order
    assert order.index("write_binding") < order.index("runner")
    assert result["results"][0]["ok"] is True


def test_mutation_remove_write_scenario_map_kills_regression(dispatch_mod):
    """Mutation `remove write_scenario_map`: no binding on disk → runner would refuse.

    Simulated by making write_scenario_map a no-op that never writes: the fail-
    closed guard must trip and the runner must not start.
    """
    order: list[str] = []
    patches = _order_tracking_patches(
        dispatch_mod,
        order,
        # mutation: write_scenario_map "removed" — reports nothing written
        write_scenario_map=lambda *a, **kw: {"written": False},
        start_runner=lambda *a, **kw: (_ for _ in ()).throw(
            AssertionError("runner started though binding was never written")
        ),
    )
    with _apply(patches):
        result = dispatch_mod.run_passes(_NonDryRunner(), sha="abc", scenario="full", passes=1)
    assert result["results"][0]["ok"] is False, "removing the binding write must fail the pass"


def test_mutation_binding_after_runner_kills_ordering(dispatch_mod):
    """Mutation `call write_scenario_map AFTER start_runner`: ordering guard catches it.

    The real code calls binding before runner; this asserts the durable order so
    a reordering mutation is detected.
    """
    order: list[str] = []
    with _apply(_order_tracking_patches(dispatch_mod, order)):
        dispatch_mod.run_passes(_NonDryRunner(), sha="abc", scenario="full", passes=1)
    assert order.index("write_binding") < order.index("runner"), (
        "binding must precede runner; a post-runner binding is a defect"
    )


def test_mutation_ignore_binding_failure_and_continue_is_caught(dispatch_mod):
    """Mutation `ignore binding creation failure`: a False write must NOT reach the runner."""
    order: list[str] = []
    reached_runner = {"v": False}
    patches = _order_tracking_patches(
        dispatch_mod,
        order,
        write_scenario_map=lambda *a, **kw: {"written": False, "error": "refused"},
        start_runner=lambda *a, **kw: (reached_runner.__setitem__("v", True), {"started": True})[1],
    )
    with _apply(patches):
        result = dispatch_mod.run_passes(_NonDryRunner(), sha="abc", scenario="full", passes=1)
    assert reached_runner["v"] is False, "a failed binding write must never reach the runner"
    assert result["results"][0]["ok"] is False


def test_failure_recovery_primitives_still_present(dispatch_mod):
    """T7 (surface): the green fix did not delete the failure-path primitive surface.

    This is a SMOKE check, not a behavioral proof of the failure driver: the
    green fix touches only run_passes, so the frozen failure/recovery driver's
    primitives (write_scenario_map → pause → inject_failure → start → resume)
    must all still be exposed by the dispatcher, and green must share the SAME
    binding writer. The failure path's *behavior* (injects exactly once) is
    pinned by field_failure_policy tests, not here — this only guards that the
    surface the frozen driver composes was not removed by this change.
    """
    for fn in (
        "write_scenario_map",
        "pause_before_dispatch",
        "inject_failure",
        "start_runner",
        "resume_after_pause",
    ):
        assert hasattr(dispatch_mod, fn), f"failure/recovery primitive {fn} missing"
    # and the green path uses the SAME binding writer as failure/recovery
    assert hasattr(dispatch_mod, "_wait_for_bindable_grant")


# ── Worktree-substrate preseed (green sys.path race) ─────────────────────────
#
# Root-cause regression: the green `run_passes` path first drives `_mesh_read`
# (candidate readiness + Beast commit binding), which imports
# `substrate.sockets.mesh_dispatch_port` from `/opt/OS` — caching `substrate` /
# `substrate.execution` against the MAIN checkout, which has no
# `execution/attempts/`. The later binding wait imports
# `substrate.execution.attempts.*`; without a preseed it resolves against that
# stale parent and the whole green pass crashes with ModuleNotFoundError BEFORE
# any Attempt is created (field run 20260808T213735Z-p1, invocation #51).


def _reset_substrate_cache_to_root():
    """Simulate the green-path pollution: /opt/OS substrate cached first.

    Evicts any worktree-rooted substrate from sys.modules, ensures `/opt/OS` is
    on the path, and imports the mesh port exactly as `_mesh_read` does — so the
    process enters the test with `substrate.execution` cached from the MAIN
    checkout, which is the precondition the preseed must overcome.
    """
    root = "/opt/OS"
    for name in list(sys.modules):
        if name == "substrate" or name.startswith("substrate."):
            del sys.modules[name]
    if root not in sys.path:
        sys.path.append(root)
    # Front-load /opt/OS so the FIRST substrate import resolves against main.
    sys.path.insert(0, root)
    import substrate.sockets.mesh_dispatch_port  # noqa: F401

    return sys.modules["substrate.execution"].__file__


@pytest.fixture
def _polluted_then_restore(dispatch_mod):
    """Enter with /opt/OS substrate cached; restore a clean cache on exit."""
    saved_path = list(sys.path)
    saved_mods = {
        n: m for n, m in sys.modules.items() if n == "substrate" or n.startswith("substrate.")
    }
    exec_file = _reset_substrate_cache_to_root()
    try:
        yield exec_file
    finally:
        # Restore whatever substrate modules the process legitimately had.
        for name in list(sys.modules):
            if name == "substrate" or name.startswith("substrate."):
                del sys.modules[name]
        sys.modules.update(saved_mods)
        sys.path[:] = saved_path


def _opt_os_has_attempts() -> bool:
    return (Path("/opt/OS") / "substrate" / "execution" / "attempts").exists()


def test_preseed_precondition_opt_os_lacks_attempts(_polluted_then_restore):
    """T1/T5: the failure is real only when /opt/OS is cached first AND lacks attempts.

    This pins the environment the preseed exists for. If /opt/OS ever gains
    execution/attempts/ (a merged branch), the crash disappears — but the
    invariant (candidate imports come from the worktree) must still hold, which
    the resolution tests below assert independently.
    """
    exec_file = _polluted_then_restore
    assert exec_file.startswith("/opt/OS/substrate"), (
        "precondition: substrate.execution must be cached from /opt/OS"
    )


@pytest.mark.skipif(
    _opt_os_has_attempts(),
    reason="/opt/OS already carries execution/attempts (merged) — the crash is not reproducible",
)
def test_plain_import_crashes_without_preseed(_polluted_then_restore):
    """T5: WITHOUT the preseed, the crashing import reproduces deterministically."""
    sys.path.insert(0, str(_WORKTREE))
    with pytest.raises(ModuleNotFoundError, match=r"substrate\.execution\.attempts"):
        # exact line the dispatcher crashed on (field_scenario_map import)
        import importlib

        importlib.import_module("substrate.execution.attempts.field_scenario_map")


def test_preseed_resolves_worktree_attempts_after_pollution(dispatch_mod, _polluted_then_restore):
    """T2/T3/T5: after preseed, substrate.execution.attempts resolves from the WORKTREE."""
    dispatch_mod._preseed_worktree_substrate()
    import substrate  # noqa
    import substrate.execution  # noqa
    import substrate.execution.attempts  # noqa

    wt = str(_WORKTREE.resolve())
    for name in ("substrate", "substrate.execution", "substrate.execution.attempts"):
        f = sys.modules[name].__file__
        assert f.startswith(wt), f"{name} resolved from {f}, not the worktree {wt}"


def test_preseed_capture_binding_import_resolves(dispatch_mod, _polluted_then_restore):
    """T3: the exact import _capture_execution_binding performs resolves from the worktree."""
    dispatch_mod._preseed_worktree_substrate()
    from substrate.execution.attempts.field_scenario_map import ExecutionBinding

    assert ExecutionBinding.__module__ == "substrate.execution.attempts.field_scenario_map"
    assert sys.modules["substrate.execution.attempts.field_scenario_map"].__file__.startswith(
        str(_WORKTREE.resolve())
    )


def test_preseed_resolves_internal_leaf_dependency(dispatch_mod, _polluted_then_restore):
    """T7: the leaf's OWN internal substrate.* imports also resolve from the worktree.

    This is the proof a pointwise leaf-load is insufficient: field_scenario_map
    imports substrate.execution.attempts.field_task_scope internally, which would
    still resolve against the stale /opt/OS parent under a leaf-only fix.
    """
    dispatch_mod._preseed_worktree_substrate()
    import substrate.execution.attempts.field_scenario_map  # noqa
    import substrate.execution.attempts.field_task_scope as fts

    assert fts.__file__.startswith(str(_WORKTREE.resolve())), (
        "internal dependency field_task_scope must resolve from the worktree, not /opt/OS"
    )


def test_preseed_is_idempotent(dispatch_mod, _polluted_then_restore):
    """T7: calling the preseed twice is a clean no-op (worktree already owns the cache)."""
    dispatch_mod._preseed_worktree_substrate()
    import substrate  # noqa

    first = sys.modules["substrate"].__file__
    dispatch_mod._preseed_worktree_substrate()
    import substrate  # noqa

    second = sys.modules["substrate"].__file__
    assert first == second == sys.modules["substrate"].__file__
    assert first.startswith(str(_WORKTREE.resolve()))


def test_preseed_puts_worktree_first_on_syspath(dispatch_mod, _polluted_then_restore):
    """T5: the worktree wins path resolution; a single copy, front-loaded."""
    dispatch_mod._preseed_worktree_substrate()
    wt = str(_WORKTREE.resolve())
    assert sys.path[0] == wt, f"worktree must be sys.path[0], got {sys.path[0]}"
    assert sys.path.count(wt) == 1, "worktree must appear exactly once (no accumulation)"


def test_preseed_evicts_sibling_worktree_prefix_superset(dispatch_mod, _polluted_then_restore):
    """Boundary: a SIBLING worktree whose path is a string-prefix superset is evicted.

    A bare `startswith(wt)` would wrongly RETAIN a module loaded from
    `<wt>-other/...` because that path starts with the worktree string. The
    os.sep boundary must treat it as OUTSIDE and evict it.
    """
    import types

    wt = str(_WORKTREE.resolve())
    sibling = types.ModuleType("substrate.execution._sibling_probe")
    sibling.__file__ = wt + "-other/substrate/execution/_sibling_probe.py"
    sys.modules["substrate.execution._sibling_probe"] = sibling
    dispatch_mod._preseed_worktree_substrate()
    assert "substrate.execution._sibling_probe" not in sys.modules, (
        "a sibling-worktree module (prefix superset) must be evicted, not retained"
    )


def test_preseed_evicts_anchorless_substrate_module(dispatch_mod, _polluted_then_restore):
    """Fail-closed: a substrate.* module with no __file__/__path__ is evicted.

    It cannot be PROVEN to come from the worktree, so it must be evicted (forcing
    a clean re-resolve), never silently retained.
    """
    import types

    ghost = types.ModuleType("substrate.execution._anchorless_probe")
    # no __file__, no __path__
    sys.modules["substrate.execution._anchorless_probe"] = ghost
    dispatch_mod._preseed_worktree_substrate()
    assert "substrate.execution._anchorless_probe" not in sys.modules, (
        "an anchorless substrate.* module must be evicted (fail-closed), not retained"
    )


def test_preseed_no_cross_worktree_accumulation(dispatch_mod, _polluted_then_restore):
    """T8: repeated fresh green passes do not accumulate stale substrate identities.

    After N preseeds interleaved with re-pollution, there is exactly ONE
    substrate identity resident and it is the worktree's.
    """
    for _ in range(3):
        _reset_substrate_cache_to_root()  # re-pollute with /opt/OS
        dispatch_mod._preseed_worktree_substrate()
        import substrate.execution.attempts.field_scenario_map  # noqa
    wt = str(_WORKTREE.resolve())
    resident = {
        n: sys.modules[n].__file__
        for n in sys.modules
        if (n == "substrate" or n.startswith("substrate."))
        and getattr(sys.modules[n], "__file__", None)
    }
    off_worktree = {n: f for n, f in resident.items() if not f.startswith(wt)}
    assert not off_worktree, f"stale non-worktree substrate modules accumulated: {off_worktree}"


def test_green_preseeds_before_binding_wait(dispatch_mod):
    """MOST IMPORTANT ordering: green preseeds the worktree substrate BEFORE the binding wait.

    The binding wait imports substrate.execution.attempts.*; the preseed MUST run
    first, or the whole green pass crashes before any Attempt is created.
    """
    order: list[str] = []
    with _apply(_order_tracking_patches(dispatch_mod, order)):
        dispatch_mod.run_passes(_NonDryRunner(), sha="abc123", scenario="full", passes=1)
    assert "preseed" in order, "green path must preseed the worktree substrate"
    assert order.index("preseed") < order.index("grant_wait"), (
        f"preseed must precede the binding wait. Order: {order}"
    )
    assert order.index("preseed") < order.index("write_binding"), (
        f"preseed must precede write_scenario_map. Order: {order}"
    )


def test_green_full_lifecycle_order_includes_preseed(dispatch_mod):
    """T12: full green order is w15 → preseed → grant_wait → write_binding → runner."""
    order: list[str] = []
    with _apply(_order_tracking_patches(dispatch_mod, order)):
        dispatch_mod.run_passes(_NonDryRunner(), sha="abc123", scenario="full", passes=1)
    green = [
        s for s in order if s in {"wait_w15", "preseed", "grant_wait", "write_binding", "runner"}
    ]
    assert green == ["wait_w15", "preseed", "grant_wait", "write_binding", "runner"], (
        f"green lifecycle order wrong: {green}"
    )


def test_mutation_remove_preseed_reproduces_crash(dispatch_mod, _polluted_then_restore):
    """Mutation `remove _preseed_worktree_substrate call`: the crash returns.

    Directly proves the preseed is load-bearing: with /opt/OS cached and NOT
    preseeded, the binding import that run_passes performs fails closed.
    """
    if _opt_os_has_attempts():
        pytest.skip("/opt/OS carries attempts — crash not reproducible in this tree")
    # No preseed call. The dispatcher's binding import must fail.
    sys.path.insert(0, str(_WORKTREE))
    with pytest.raises(ModuleNotFoundError, match=r"substrate\.execution\.attempts"):
        import importlib

        importlib.import_module("substrate.execution.attempts.field_scenario_map")


def test_mutation_preseed_wrong_root_leaves_stale(dispatch_mod, _polluted_then_restore):
    """Mutation `preseed points at /opt/OS instead of the worktree`: attempts still missing.

    A preseed that front-loads the wrong root and evicts nothing leaves the stale
    parent resident — the import still fails. This pins that the preseed must
    target the WORKTREE, not merely 'some root'.
    """
    if _opt_os_has_attempts():
        pytest.skip("/opt/OS carries attempts — crash not reproducible in this tree")

    # Emulate the mutated preseed: front-load /opt/OS, evict nothing.
    sys.path.insert(0, "/opt/OS")
    with pytest.raises(ModuleNotFoundError, match=r"substrate\.execution\.attempts"):
        import importlib

        importlib.import_module("substrate.execution.attempts.field_scenario_map")


def test_failure_recovery_import_path_unchanged(dispatch_mod):
    """T9: the failure/recovery CLI subcommands still guard their own imports.

    The green fix adds a preseed to run_passes ONLY; it must not have removed the
    per-subcommand `sys.path.insert(0, str(_WORKTREE))` guards the frozen
    failure/recovery driver relies on (each subcommand runs in a fresh process
    with no prior mesh read, so it needs its own guard). This asserts the EXACT
    guard line is still present — asserting merely that the string `_WORKTREE`
    appears is too weak (these functions reference it elsewhere), so a mutation
    that strips only the guard line would survive.
    """
    import inspect

    guard = "sys.path.insert(0, str(_WORKTREE))"
    for fn_name in (
        "write_scenario_map",
        "inject_failure",
        "pause_before_dispatch",
        "resume_after_pause",
        "_capture_execution_binding",
    ):
        src = inspect.getsource(getattr(dispatch_mod, fn_name))
        assert guard in src, (
            f"{fn_name} lost its worktree-guarded import ({guard!r} missing) — "
            f"the failure/recovery CLI path would resolve stale /opt/OS substrate"
        )


def test_capture_binding_import_not_swallowed(dispatch_mod, _polluted_then_restore):
    """M7-killer: _capture_execution_binding must NOT catch ModuleNotFoundError and continue.

    Under the green-path pollution (/opt/OS substrate cached, no preseed), the
    real function's `from substrate.execution.attempts.field_scenario_map import
    ExecutionBinding` must RAISE — a mutation that wraps it in try/except and
    returns a benign refusal would hide a real harness defect behind a fail-closed
    string. The green path's preseed is what makes this import succeed in
    production; here we prove the import is load-bearing and never swallowed.
    """
    if _opt_os_has_attempts():
        pytest.skip("/opt/OS carries attempts — the import cannot fail in this tree")
    # Records that would pass the correlation filter IF the import succeeded, so
    # the function reaches the import line rather than short-circuiting earlier.
    records = [
        {
            "grant_id": "g1",
            "task_frontier": ["wp-a"],
            "correlation_id": "w2-r1",
            "status": "active",
        }
    ]
    with pytest.raises(ModuleNotFoundError, match=r"substrate\.execution\.attempts"):
        dispatch_mod._capture_execution_binding(records, sha="abc", run_id="r1")
