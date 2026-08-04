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
            "dest": "/tmp/test_fixture", "variant": variant, "run_id": run_id,
        },
        "_dispatch_collector": lambda runner, *, run_id, pass_num, scenario, sha: {
            "ok": True, "run_id": run_id, "pass_num": pass_num,
        },
        "_wait_collector_authorization": lambda runner, run_id, pass_num, timeout_min=25: True,
        "start_runner": lambda runner, sha, run_id, max_iterations: {
            "started": True, "dry_run": True,
        },
        "_poll_status": lambda runner, run_id, pass_num, timeout_min=30, max_mesh_failures=5: {
            "state": "passed", "run_id": run_id, "stages_done": 36,
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
        seed_fixture=track("seed_fixture", lambda *a, **kw: {
            "dest": "/tmp/test", "variant": "clean", "run_id": "r1",
        }),
        _dispatch_collector=track("dispatch_collector", lambda *a, **kw: {
            "ok": True, "run_id": "r1", "pass_num": 1,
        }),
        _wait_collector_authorization=track("wait_w15", lambda *a, **kw: True),
        start_runner=track("start_runner", lambda *a, **kw: {
            "started": True, "dry_run": True,
        }),
        _poll_status=track("poll_status", lambda *a, **kw: {
            "state": "passed", "run_id": "r1",
        }),
        stop_runner=track("stop_runner", lambda *a, **kw: {"stopped": True}),
    )

    runner = _FakeRunner()
    with patches[0], patches[1], patches[2], patches[3], patches[4], patches[5], patches[6], patches[7]:
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
        patch.object(dispatch_mod, "seed_fixture", side_effect=lambda *a, **k: (_ for _ in ()).throw(AssertionError("seed_fixture called in smoke"))),
        patch.object(dispatch_mod, "start_runner", side_effect=lambda *a, **k: (_ for _ in ()).throw(AssertionError("start_runner called in smoke"))),
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
    with patches[0], patches[1], patches[2], patches[3], patches[4], patches[5], patches[6], patches[7]:
        with pytest.raises(RuntimeError):
            dispatch_mod.run_passes(runner, sha="abc123", scenario="full", passes=1)

    assert len(stopped) == 1, "Runner must be stopped even on poll failure"


def test_full_scenario_fails_closed_on_seed_failure(dispatch_mod):
    """If seed_fixture fails, no collector dispatch or runner should happen."""
    call_order: list[str] = []

    patches = _full_scenario_patches(
        dispatch_mod,
        seed_fixture=lambda *a, **kw: (call_order.append("seed_fixture"), {})[1],
        _dispatch_collector=lambda *a, **kw: (_ for _ in ()).throw(AssertionError("dispatch after seed failure")),
        start_runner=lambda *a, **kw: (_ for _ in ()).throw(AssertionError("runner after seed failure")),
    )

    runner = _FakeRunner()
    with patches[0], patches[1], patches[2], patches[3], patches[4], patches[5], patches[6], patches[7]:
        result = dispatch_mod.run_passes(runner, sha="abc123", scenario="full", passes=1)

    assert call_order == ["seed_fixture"]
    assert result["results"][0]["ok"] is False
    assert "seed_fixture" in result["results"][0]["error"]


def test_full_scenario_fails_closed_on_runner_start_failure(dispatch_mod):
    """If start_runner fails, no poll should happen."""
    call_order: list[str] = []

    patches = _full_scenario_patches(
        dispatch_mod,
        seed_fixture=lambda *a, **kw: (call_order.append("seed"), {"dest": "/tmp/t", "variant": "clean", "run_id": "r1"})[1],
        _dispatch_collector=lambda *a, **kw: (call_order.append("dispatch"), {"ok": True, "run_id": "r1", "pass_num": 1})[1],
        _wait_collector_authorization=lambda *a, **kw: (call_order.append("wait"), True)[1],
        start_runner=lambda *a, **kw: (call_order.append("start"), {"started": False, "reason": "isolation fail"})[1],
        _poll_status=lambda *a, **kw: (_ for _ in ()).throw(AssertionError("poll after runner failure")),
    )

    runner = _FakeRunner()
    with patches[0], patches[1], patches[2], patches[3], patches[4], patches[5], patches[6], patches[7]:
        result = dispatch_mod.run_passes(runner, sha="abc123", scenario="full", passes=1)

    assert call_order == ["seed", "dispatch", "wait", "start"]
    assert result["results"][0]["ok"] is False
    assert "start_runner" in result["results"][0]["error"]


def test_full_scenario_fails_closed_on_collector_dispatch_failure(dispatch_mod):
    """If collector dispatch fails, runner must not start."""
    call_order: list[str] = []

    patches = _full_scenario_patches(
        dispatch_mod,
        seed_fixture=lambda *a, **kw: (call_order.append("seed"), {"dest": "/tmp/t", "variant": "clean", "run_id": "r1"})[1],
        _dispatch_collector=lambda *a, **kw: (call_order.append("dispatch"), {"ok": False, "error": "mesh down"})[1],
        start_runner=lambda *a, **kw: (_ for _ in ()).throw(AssertionError("runner after dispatch failure")),
    )

    runner = _FakeRunner()
    with patches[0], patches[1], patches[2], patches[3], patches[4], patches[5], patches[6], patches[7]:
        result = dispatch_mod.run_passes(runner, sha="abc123", scenario="full", passes=1)

    assert call_order == ["seed", "dispatch"]
    assert result["results"][0]["ok"] is False


def test_full_scenario_fails_closed_when_collector_doesnt_reach_w15(dispatch_mod):
    """If collector doesn't reach w15, runner must not start."""
    call_order: list[str] = []

    patches = _full_scenario_patches(
        dispatch_mod,
        seed_fixture=lambda *a, **kw: (call_order.append("seed"), {"dest": "/tmp/t", "variant": "clean", "run_id": "r1"})[1],
        _dispatch_collector=lambda *a, **kw: (call_order.append("dispatch"), {"ok": True, "run_id": "r1", "pass_num": 1})[1],
        _wait_collector_authorization=lambda *a, **kw: (call_order.append("wait"), False)[1],
        start_runner=lambda *a, **kw: (_ for _ in ()).throw(AssertionError("runner when w15 not reached")),
    )

    runner = _FakeRunner()
    with patches[0], patches[1], patches[2], patches[3], patches[4], patches[5], patches[6], patches[7]:
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
        start_runner=lambda runner, sha, run_id, max_iterations: (starts.append(run_id), {"started": True})[1],
        stop_runner=lambda runner, sha, run_id: (stops.append(run_id), {"stopped": True})[1],
    )

    runner = _FakeRunner()
    with patches[0], patches[1], patches[2], patches[3], patches[4], patches[5], patches[6], patches[7]:
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
        seed_fixture=lambda *a, **kw: (called.__setitem__("seed", True), {"dest": "/tmp/t", "variant": "clean", "run_id": "r1"})[1],
        _dispatch_collector=lambda *a, **kw: (called.__setitem__("dispatch", True), {"ok": True, "run_id": "r1", "pass_num": 1})[1],
        start_runner=lambda *a, **kw: (called.__setitem__("start", True), {"started": True})[1],
    )

    runner = _FakeRunner()
    with patches[0], patches[1], patches[2], patches[3], patches[4], patches[5], patches[6], patches[7]:
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
    with patches[0], patches[1], patches[2], patches[3], patches[4], patches[5], patches[6], patches[7]:
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
    with patches[0], patches[1], patches[2], patches[3], patches[4], patches[5], patches[6], patches[7]:
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
        _dispatch_collector=lambda *a, **kw: (order.append("dispatch"), {"ok": True, "run_id": "r1", "pass_num": 1})[1],
        _wait_collector_authorization=lambda *a, **kw: (order.append("wait_w15"), True)[1],
        start_runner=lambda *a, **kw: (order.append("runner"), {"started": True})[1],
    )

    runner = _FakeRunner()
    with patches[0], patches[1], patches[2], patches[3], patches[4], patches[5], patches[6], patches[7]:
        dispatch_mod.run_passes(runner, sha="abc123", scenario="full", passes=1)

    assert order.index("dispatch") < order.index("runner"), (
        f"Collector must dispatch before runner starts. Order: {order}"
    )
    assert order.index("wait_w15") < order.index("runner"), (
        f"Must wait for w15 before runner starts. Order: {order}"
    )
