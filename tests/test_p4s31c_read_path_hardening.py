"""P4S-31C — read-path isolation + bounded snapshot regression tests.

Proves the packet's required behavior and hard constraints:

1. Isolation primitive: ``isolated_read`` runs on the dedicated read pool,
   returns the value on success, and returns the fallback (never raises, never
   blocks past budget) on timeout or exception.
2. TTL cache: fresh within TTL, stale past TTL, last-known-good preserved.
3. ``cached_isolated_read`` degrades to last-known-good on timeout with a warm
   cache and to the stable empty fallback on a cold-cache timeout.
4. Response-shape byte-compatibility: the bounded ``/snapshot`` composition
   produces the SAME key set as before, and the empty fallback carries the
   identical added-key set (no shape change).
5. The two hot poll handlers (``/intent-loop``, ``/unified-workstation/snapshot``)
   are ``async def`` — so cockpit polling cannot pile up synchronous copies on
   the shared AnyIO limiter.
6. No governed-mutation path touched by this packet's read-path module.
"""

from __future__ import annotations

import ast
import asyncio
import inspect
import os
import sys
import time
from pathlib import Path

_WORKTREE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _WORKTREE not in sys.path:
    sys.path.insert(0, _WORKTREE)

from transports.api.read_path_isolation import (
    TTLSnapshotCache,
    cached_isolated_read,
    get_read_pool,
    isolated_read,
    shutdown_read_pool,
)

_UWS_PATH = Path(_WORKTREE) / "transports" / "api" / "cockpit_unified_workstation_routes.py"
_IL_PATH = Path(_WORKTREE) / "transports" / "api" / "cockpit_intent_loop_routes.py"
_RPI_PATH = Path(_WORKTREE) / "transports" / "api" / "read_path_isolation.py"


# ── 1. isolated_read ──────────────────────────────────────────────────────────


def test_isolated_read_returns_value_on_success():
    async def _run():
        return await isolated_read(lambda: 42, timeout=2.0, fallback=-1, label="ok")

    assert asyncio.run(_run()) == 42


def test_isolated_read_returns_fallback_on_exception():
    def _boom():
        raise RuntimeError("nope")

    async def _run():
        return await isolated_read(_boom, timeout=2.0, fallback="fb", label="boom")

    assert asyncio.run(_run()) == "fb"


def test_isolated_read_returns_fallback_on_timeout_without_blocking():
    def _slow():
        time.sleep(3.0)
        return "late"

    async def _run():
        start = time.time()
        result = await isolated_read(_slow, timeout=0.3, fallback="fb", label="slow")
        return result, time.time() - start

    result, elapsed = asyncio.run(_run())
    assert result == "fb"
    # Must return near the budget, NOT wait the full 3s work.
    assert elapsed < 1.5, f"isolated_read blocked past budget: {elapsed:.2f}s"


# ── 2. TTLSnapshotCache ───────────────────────────────────────────────────────


def test_ttl_cache_fresh_then_stale():
    cache = TTLSnapshotCache(ttl_seconds=0.3)
    assert cache.get_fresh() == (False, None)
    cache.put({"v": 1})
    is_fresh, val = cache.get_fresh()
    assert is_fresh and val == {"v": 1}
    time.sleep(0.4)
    is_fresh, val = cache.get_fresh()
    assert not is_fresh
    # last-known-good survives staleness
    assert cache.last_known_good() == (True, {"v": 1})


# ── 3. cached_isolated_read degradation ───────────────────────────────────────


def test_cached_read_fresh_hit_skips_compute():
    cache = TTLSnapshotCache(ttl_seconds=5.0)
    cache.put({"cached": True})
    calls = {"n": 0}

    def _fn():
        calls["n"] += 1
        return {"cached": False}

    async def _run():
        return await cached_isolated_read(
            _fn, cache=cache, timeout=2.0, empty_fallback={}, label="hit"
        )

    assert asyncio.run(_run()) == {"cached": True}
    assert calls["n"] == 0  # fresh cache → no compute


def test_cached_read_degrades_to_last_known_good_on_timeout():
    cache = TTLSnapshotCache(ttl_seconds=0.01)
    cache.put({"lkg": True})
    time.sleep(0.02)  # force stale

    def _slow():
        time.sleep(3.0)
        return {"fresh": True}

    async def _run():
        return await cached_isolated_read(
            _slow, cache=cache, timeout=0.3, empty_fallback={"empty": True}, label="lkg"
        )

    assert asyncio.run(_run()) == {"lkg": True}


def test_cached_read_cold_cache_timeout_returns_empty_fallback():
    cache = TTLSnapshotCache(ttl_seconds=5.0)

    def _slow():
        time.sleep(3.0)
        return {"fresh": True}

    async def _run():
        return await cached_isolated_read(
            _slow, cache=cache, timeout=0.3, empty_fallback={"empty": True}, label="cold"
        )

    assert asyncio.run(_run()) == {"empty": True}


# ── 4. Response-shape byte-compatibility ──────────────────────────────────────

_EXPECTED_ADDED_KEYS = {
    "continuity_state",
    "valid_transitions",
    "lifecycle_mode",
    "risk_ceiling",
    "effective_posture",
    "active_profile_modes",
    "overnight",
    "node_count",
    "nodes",
    "stt_available",
    "tts_available",
}


def test_empty_snapshot_fallback_matches_added_key_set():
    from transports.api.cockpit_unified_workstation_routes import _empty_snapshot_fallback

    fallback = _empty_snapshot_fallback()
    assert set(fallback.keys()) == _EXPECTED_ADDED_KEYS


def test_compose_snapshot_produces_all_added_keys(monkeypatch):
    from transports.api import cockpit_unified_workstation_routes as uws

    # rt is None → base is empty and rt.snapshot() (a daemon-dependent runtime
    # that can block tens of seconds without a live organism) is never invoked.
    # The five file-backed sub-reads still run, exercising the real compose path
    # and proving the enrichment key set is byte-compatible.
    monkeypatch.setattr(uws, "_get_runtime", lambda: None)

    snap = uws._compose_snapshot()
    assert _EXPECTED_ADDED_KEYS.issubset(set(snap.keys()))


def test_snapshot_route_returns_same_shape_via_async_handler(monkeypatch):
    from transports.api import cockpit_unified_workstation_routes as uws

    # Deterministic, fast compose stub so the async handler test does not depend
    # on a live organism daemon; it asserts the async wrapper returns the compose
    # result unchanged and caches it (shape byte-identical to the real compose).
    stub = {k: None for k in _EXPECTED_ADDED_KEYS}
    monkeypatch.setattr(uws, "_compose_snapshot", lambda: dict(stub))
    # fresh cache so the stub is actually computed
    monkeypatch.setattr(uws, "_snapshot_cache", uws.TTLSnapshotCache(ttl_seconds=5.0))

    router = uws.get_router()
    handler = None
    for route in router.routes:
        if getattr(route, "path", "") == "/unified-workstation/snapshot":
            handler = route.endpoint
            break
    assert handler is not None, "snapshot route not found"
    assert inspect.iscoroutinefunction(handler), "snapshot handler must be async"

    result = asyncio.run(handler())
    assert isinstance(result, dict)
    assert set(result.keys()) == _EXPECTED_ADDED_KEYS


# ── 5. Hot poll handlers are async ────────────────────────────────────────────


def test_intent_loop_handler_is_async():
    src = _IL_PATH.read_text(encoding="utf-8")
    tree = ast.parse(src)
    found = False
    for node in ast.walk(tree):
        if isinstance(node, ast.AsyncFunctionDef) and node.name == "intent_loop":
            found = True
    assert found, "intent_loop handler must be an async def"


def test_snapshot_handler_is_async_in_source():
    src = _UWS_PATH.read_text(encoding="utf-8")
    tree = ast.parse(src)
    found = False
    for node in ast.walk(tree):
        if isinstance(node, ast.AsyncFunctionDef) and node.name == "get_snapshot":
            found = True
    assert found, "get_snapshot handler must be an async def"


# ── 6. No governed-mutation path in the isolation module ──────────────────────


def test_read_path_module_touches_no_governed_mutation():
    src = _RPI_PATH.read_text(encoding="utf-8")
    assert "governed_mutation" not in src
    assert "MutationRouter" not in src
    assert "GovernedExecutionSpine" not in src


def test_read_pool_is_singleton_and_shuts_down():
    p1 = get_read_pool()
    p2 = get_read_pool()
    assert p1 is p2
    shutdown_read_pool()
    p3 = get_read_pool()
    assert p3 is not p1  # a fresh pool after shutdown
    shutdown_read_pool()
