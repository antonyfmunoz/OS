"""Wave 2 run_passes runner-lifecycle invariant.

Root-cause regression: 16 consecutive w16_ab_running_concurrent failures were
caused by `run_passes` dispatching the Beast collector without starting the
host-side attempt runner. The collector drove the cockpit through plan approval
and execution authorization (w15), but no scheduler ever ran to create Attempts,
so the collector observed dom_running=0 and failed at w16.

These tests verify that `run_passes` for the `full` scenario:
1. Calls `seed_fixture` before starting the runner.
2. Calls `start_runner` before dispatching the collector.
3. Calls `stop_runner` after the collector finishes (even on failure).
4. Does NOT start a runner for `smoke` scenario.
5. Fails closed when `seed_fixture` fails.
6. Fails closed when `start_runner` fails.
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


def test_full_scenario_calls_seed_and_start_before_dispatch(dispatch_mod):
    """Full scenario must seed fixture + start runner before dispatching."""
    call_order: list[str] = []

    def fake_seed(runner, sha, run_id, variant):
        call_order.append("seed_fixture")
        return {"dest": "/tmp/test_fixture", "variant": variant, "run_id": run_id}

    def fake_start(runner, sha, run_id, max_iterations):
        call_order.append("start_runner")
        return {"started": True, "dry_run": True}

    def fake_dispatch(runner, *, run_id, pass_num, scenario, sha):
        call_order.append("dispatch_pass")
        return {"ok": True, "run_id": run_id}

    def fake_stop(runner, sha, run_id):
        call_order.append("stop_runner")
        return {"stopped": True}

    def fake_ready(runner, timeout_s=120.0):
        return {"ready": True}

    def fake_binding(runner, sha):
        return {"ok": True}

    runner = _FakeRunner()
    with (
        patch.object(dispatch_mod, "seed_fixture", side_effect=fake_seed),
        patch.object(dispatch_mod, "start_runner", side_effect=fake_start),
        patch.object(dispatch_mod, "dispatch_pass", side_effect=fake_dispatch),
        patch.object(dispatch_mod, "stop_runner", side_effect=fake_stop),
        patch.object(dispatch_mod, "_wait_candidate_ready", side_effect=fake_ready),
        patch.object(dispatch_mod, "_verify_beast_collector_commit", side_effect=fake_binding),
    ):
        result = dispatch_mod.run_passes(runner, sha="abc123", scenario="full", passes=1)

    assert call_order == ["seed_fixture", "start_runner", "dispatch_pass", "stop_runner"], (
        f"Expected seed→start→dispatch→stop, got {call_order}"
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


def test_full_scenario_stops_runner_on_dispatch_failure(dispatch_mod):
    """Runner must be stopped even if dispatch_pass raises."""
    stopped = []

    def fake_seed(runner, sha, run_id, variant):
        return {"dest": "/tmp/test_fixture", "variant": variant, "run_id": run_id}

    def fake_start(runner, sha, run_id, max_iterations):
        return {"started": True}

    def fake_dispatch(runner, *, run_id, pass_num, scenario, sha):
        raise RuntimeError("collector crash")

    def fake_stop(runner, sha, run_id):
        stopped.append(run_id)
        return {"stopped": True}

    def fake_ready(runner, timeout_s=120.0):
        return {"ready": True}

    def fake_binding(runner, sha):
        return {"ok": True}

    runner = _FakeRunner()
    with (
        patch.object(dispatch_mod, "seed_fixture", side_effect=fake_seed),
        patch.object(dispatch_mod, "start_runner", side_effect=fake_start),
        patch.object(dispatch_mod, "dispatch_pass", side_effect=fake_dispatch),
        patch.object(dispatch_mod, "stop_runner", side_effect=fake_stop),
        patch.object(dispatch_mod, "_wait_candidate_ready", side_effect=fake_ready),
        patch.object(dispatch_mod, "_verify_beast_collector_commit", side_effect=fake_binding),
    ):
        with pytest.raises(RuntimeError):
            dispatch_mod.run_passes(runner, sha="abc123", scenario="full", passes=1)

    assert len(stopped) == 1, "Runner must be stopped even on dispatch failure"


def test_full_scenario_fails_closed_on_seed_failure(dispatch_mod):
    """If seed_fixture fails, no runner or dispatch should happen."""
    call_order: list[str] = []

    def fake_seed(runner, sha, run_id, variant):
        call_order.append("seed_fixture")
        return {}  # no "dest" key = failure

    def fake_ready(runner, timeout_s=120.0):
        return {"ready": True}

    def fake_binding(runner, sha):
        return {"ok": True}

    runner = _FakeRunner()
    with (
        patch.object(dispatch_mod, "seed_fixture", side_effect=fake_seed),
        patch.object(dispatch_mod, "start_runner", side_effect=lambda *a, **k: (_ for _ in ()).throw(AssertionError("start_runner called after seed failure"))),
        patch.object(dispatch_mod, "dispatch_pass", side_effect=lambda *a, **k: (_ for _ in ()).throw(AssertionError("dispatch called after seed failure"))),
        patch.object(dispatch_mod, "_wait_candidate_ready", side_effect=fake_ready),
        patch.object(dispatch_mod, "_verify_beast_collector_commit", side_effect=fake_binding),
    ):
        result = dispatch_mod.run_passes(runner, sha="abc123", scenario="full", passes=1)

    assert call_order == ["seed_fixture"]
    assert result["results"][0]["ok"] is False
    assert "seed_fixture" in result["results"][0]["error"]


def test_full_scenario_fails_closed_on_runner_start_failure(dispatch_mod):
    """If start_runner fails, no dispatch should happen."""
    call_order: list[str] = []

    def fake_seed(runner, sha, run_id, variant):
        call_order.append("seed_fixture")
        return {"dest": "/tmp/test", "variant": variant, "run_id": run_id}

    def fake_start(runner, sha, run_id, max_iterations):
        call_order.append("start_runner")
        return {"started": False, "reason": "isolation preflight failed"}

    def fake_ready(runner, timeout_s=120.0):
        return {"ready": True}

    def fake_binding(runner, sha):
        return {"ok": True}

    runner = _FakeRunner()
    with (
        patch.object(dispatch_mod, "seed_fixture", side_effect=fake_seed),
        patch.object(dispatch_mod, "start_runner", side_effect=fake_start),
        patch.object(dispatch_mod, "dispatch_pass", side_effect=lambda *a, **k: (_ for _ in ()).throw(AssertionError("dispatch called after runner failure"))),
        patch.object(dispatch_mod, "_wait_candidate_ready", side_effect=fake_ready),
        patch.object(dispatch_mod, "_verify_beast_collector_commit", side_effect=fake_binding),
    ):
        result = dispatch_mod.run_passes(runner, sha="abc123", scenario="full", passes=1)

    assert call_order == ["seed_fixture", "start_runner"]
    assert result["results"][0]["ok"] is False
    assert "start_runner" in result["results"][0]["error"]


def test_multi_pass_starts_runner_per_pass(dispatch_mod):
    """Each pass gets its own runner (run-scoped spool/targets)."""
    starts: list[str] = []
    stops: list[str] = []

    def fake_seed(runner, sha, run_id, variant):
        return {"dest": "/tmp/test", "variant": variant, "run_id": run_id}

    def fake_start(runner, sha, run_id, max_iterations):
        starts.append(run_id)
        return {"started": True}

    def fake_dispatch(runner, *, run_id, pass_num, scenario, sha):
        return {"ok": True, "run_id": run_id}

    def fake_stop(runner, sha, run_id):
        stops.append(run_id)
        return {"stopped": True}

    def fake_ready(runner, timeout_s=120.0):
        return {"ready": True}

    def fake_binding(runner, sha):
        return {"ok": True}

    runner = _FakeRunner()
    with (
        patch.object(dispatch_mod, "seed_fixture", side_effect=fake_seed),
        patch.object(dispatch_mod, "start_runner", side_effect=fake_start),
        patch.object(dispatch_mod, "dispatch_pass", side_effect=fake_dispatch),
        patch.object(dispatch_mod, "stop_runner", side_effect=fake_stop),
        patch.object(dispatch_mod, "_wait_candidate_ready", side_effect=fake_ready),
        patch.object(dispatch_mod, "_verify_beast_collector_commit", side_effect=fake_binding),
    ):
        result = dispatch_mod.run_passes(runner, sha="abc123", scenario="full", passes=3)

    assert len(starts) == 3, f"Expected 3 runner starts, got {len(starts)}"
    assert len(stops) == 3, f"Expected 3 runner stops, got {len(stops)}"
    assert len(result["results"]) == 3


# ── Mutation tests (kill resistant) ─────────────────────────────────────────

def test_mutation_omit_seed_fixture_kills_full(dispatch_mod):
    """Mutation: removing seed_fixture call must fail (no fixture = no workers)."""
    # This test exists to detect if someone removes the seed_fixture call from
    # the full scenario path. We verify that the seed_fixture IS called by
    # checking the call order.
    called = {"seed": False, "start": False}

    def fake_seed(runner, sha, run_id, variant):
        called["seed"] = True
        return {"dest": "/tmp/test", "variant": variant, "run_id": run_id}

    def fake_start(runner, sha, run_id, max_iterations):
        called["start"] = True
        assert called["seed"], "start_runner called before seed_fixture"
        return {"started": True}

    def fake_dispatch(runner, *, run_id, pass_num, scenario, sha):
        assert called["start"], "dispatch called before start_runner"
        return {"ok": True, "run_id": run_id}

    def fake_stop(runner, sha, run_id):
        return {"stopped": True}

    def fake_ready(runner, timeout_s=120.0):
        return {"ready": True}

    def fake_binding(runner, sha):
        return {"ok": True}

    runner = _FakeRunner()
    with (
        patch.object(dispatch_mod, "seed_fixture", side_effect=fake_seed),
        patch.object(dispatch_mod, "start_runner", side_effect=fake_start),
        patch.object(dispatch_mod, "dispatch_pass", side_effect=fake_dispatch),
        patch.object(dispatch_mod, "stop_runner", side_effect=fake_stop),
        patch.object(dispatch_mod, "_wait_candidate_ready", side_effect=fake_ready),
        patch.object(dispatch_mod, "_verify_beast_collector_commit", side_effect=fake_binding),
    ):
        dispatch_mod.run_passes(runner, sha="abc123", scenario="full", passes=1)

    assert called["seed"], "seed_fixture was not called for full scenario"
    assert called["start"], "start_runner was not called for full scenario"


def test_mutation_skip_stop_runner_detected(dispatch_mod):
    """Mutation: removing stop_runner must leave the runner alive (detectable)."""
    stopped = []

    def fake_seed(runner, sha, run_id, variant):
        return {"dest": "/tmp/test", "variant": variant, "run_id": run_id}

    def fake_start(runner, sha, run_id, max_iterations):
        return {"started": True}

    def fake_dispatch(runner, *, run_id, pass_num, scenario, sha):
        return {"ok": True, "run_id": run_id}

    def fake_stop(runner, sha, run_id):
        stopped.append(run_id)
        return {"stopped": True}

    def fake_ready(runner, timeout_s=120.0):
        return {"ready": True}

    def fake_binding(runner, sha):
        return {"ok": True}

    runner = _FakeRunner()
    with (
        patch.object(dispatch_mod, "seed_fixture", side_effect=fake_seed),
        patch.object(dispatch_mod, "start_runner", side_effect=fake_start),
        patch.object(dispatch_mod, "dispatch_pass", side_effect=fake_dispatch),
        patch.object(dispatch_mod, "stop_runner", side_effect=fake_stop),
        patch.object(dispatch_mod, "_wait_candidate_ready", side_effect=fake_ready),
        patch.object(dispatch_mod, "_verify_beast_collector_commit", side_effect=fake_binding),
    ):
        dispatch_mod.run_passes(runner, sha="abc123", scenario="full", passes=1)

    assert len(stopped) == 1, "stop_runner not called — runner would be leaked"


def test_mutation_one_worker_instead_of_two_concurrency(dispatch_mod):
    """Mutation: start_runner must pass max_iterations=0 (run until stopped)."""
    recorded_kwargs: list[dict[str, Any]] = []

    def fake_seed(runner, sha, run_id, variant):
        return {"dest": "/tmp/test", "variant": variant, "run_id": run_id}

    def fake_start(runner, sha, run_id, max_iterations):
        recorded_kwargs.append({"max_iterations": max_iterations})
        return {"started": True}

    def fake_dispatch(runner, *, run_id, pass_num, scenario, sha):
        return {"ok": True, "run_id": run_id}

    def fake_stop(runner, sha, run_id):
        return {"stopped": True}

    def fake_ready(runner, timeout_s=120.0):
        return {"ready": True}

    def fake_binding(runner, sha):
        return {"ok": True}

    runner = _FakeRunner()
    with (
        patch.object(dispatch_mod, "seed_fixture", side_effect=fake_seed),
        patch.object(dispatch_mod, "start_runner", side_effect=fake_start),
        patch.object(dispatch_mod, "dispatch_pass", side_effect=fake_dispatch),
        patch.object(dispatch_mod, "stop_runner", side_effect=fake_stop),
        patch.object(dispatch_mod, "_wait_candidate_ready", side_effect=fake_ready),
        patch.object(dispatch_mod, "_verify_beast_collector_commit", side_effect=fake_binding),
    ):
        dispatch_mod.run_passes(runner, sha="abc123", scenario="full", passes=1)

    assert recorded_kwargs[0]["max_iterations"] == 0, (
        "Runner must run until stopped (max_iterations=0)"
    )
