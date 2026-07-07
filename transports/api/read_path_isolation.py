"""Read-path isolation for hot Cockpit poll routes — P4S-31C runtime hardening.

The problem this module solves (proven in
``data/audits/2026-07-06_os_operator_sustained_load_diagnosis.md``):

- Starlette runs **synchronous** ``def`` route handlers on AnyIO's shared
  ``CapacityLimiter`` (default 40 tokens). The Cockpit dashboard polls ~30 read
  routes per refresh cycle. One intrinsically slow synchronous handler
  (``GET /unified-workstation/snapshot``, measured >55 s) holds a token for its
  full duration; repeated polling piles copies up and DRAINS the shared pool.
  Once drained, the fast read surfaces (``/intent-loop``, ``/pulse``, …) queue
  behind it and the whole read path wedges — even though each of them is cheap.

The isolation contract here:

1. **Dedicated bounded executor.** Hot read composition runs on a small,
   dedicated ``ThreadPoolExecutor`` (``READ_POOL``) — NOT the shared AnyIO
   limiter. A slow read can therefore never drain the pool that the rest of the
   API (governed writes, chat, WS) depends on. The pool is intentionally small
   (few workers) because the host is CPU-capped: isolation, not parallelism, is
   the goal (per the diagnosis, more threads under a CPU cap worsen throttling).

2. **Hard per-call timeout.** Every isolated read is wrapped in
   ``asyncio.wait_for``. A read that exceeds its budget NEVER blocks the caller
   indefinitely — the coroutine returns and the worker thread is abandoned to
   finish (or die) on its own without holding the request.

3. **TTL last-known-good cache.** For the expensive composite snapshot, results
   are cached with a short TTL. On a cache hit the route returns instantly
   (zero threadpool tokens). On a timeout/failure with a warm cache, the route
   returns the **last-known-good** value — byte-identical shape — instead of an
   error or a hang. This is behavior-preserving: the response schema is
   unchanged; only freshness degrades gracefully under sustained load.

No response shape changes. No governed-mutation path touched. Read surfaces
only. Instance-agnostic UMH transport infrastructure.
"""

from __future__ import annotations

import asyncio
import logging
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from typing import Any, Callable

logger = logging.getLogger(__name__)

# ── Dedicated read executor ────────────────────────────────────────────────
#
# Small on purpose. The host caps os-operator at 0.5 core; the goal is to keep
# slow reads OFF the shared AnyIO limiter, not to run many reads in parallel.
# 4 workers is enough to absorb a burst of distinct hot reads without becoming
# a CPU-contention source of its own.
_READ_POOL_WORKERS = 4
_READ_POOL: ThreadPoolExecutor | None = None
_READ_POOL_LOCK = threading.Lock()


def get_read_pool() -> ThreadPoolExecutor:
    """Return the process-wide dedicated read executor (lazily created)."""
    global _READ_POOL
    if _READ_POOL is None:
        with _READ_POOL_LOCK:
            if _READ_POOL is None:
                _READ_POOL = ThreadPoolExecutor(
                    max_workers=_READ_POOL_WORKERS,
                    thread_name_prefix="read",
                )
                logger.info(
                    "read-path isolation pool created: %d workers",
                    _READ_POOL_WORKERS,
                )
    return _READ_POOL


async def isolated_read(
    fn: Callable[[], Any],
    *,
    timeout: float,
    fallback: Any,
    label: str = "read",
) -> Any:
    """Run a blocking read ``fn`` on the dedicated pool with a hard timeout.

    On success returns ``fn()``'s result. On timeout or exception returns
    ``fallback`` (never raises, never blocks the event loop past ``timeout``).
    The worker thread is left to finish on its own after a timeout so a slow
    read cannot wedge the request path.
    """
    loop = asyncio.get_running_loop()
    pool = get_read_pool()
    try:
        return await asyncio.wait_for(
            loop.run_in_executor(pool, fn),
            timeout=timeout,
        )
    except asyncio.TimeoutError:
        logger.warning("isolated read '%s' exceeded %.1fs budget", label, timeout)
        return fallback
    except Exception as exc:  # read surface never 500s
        logger.debug("isolated read '%s' failed: %s", label, exc)
        return fallback


class TTLSnapshotCache:
    """Thread-safe last-known-good cache with a short TTL.

    Fresh (age < ttl)  → return cached value, no compute.
    Stale but present   → returned on compute timeout/failure (last-known-good).
    Empty               → caller computes; a failed first compute yields the
                          provided ``empty_fallback`` (stable shape).
    """

    def __init__(self, ttl_seconds: float) -> None:
        self._ttl = ttl_seconds
        self._value: Any = None
        self._stamped_at: float = 0.0
        self._has_value = False
        self._lock = threading.Lock()

    def get_fresh(self) -> tuple[bool, Any]:
        """Return (is_fresh, value). is_fresh is True only within the TTL."""
        with self._lock:
            if self._has_value and (time.time() - self._stamped_at) < self._ttl:
                return True, self._value
            return False, self._value if self._has_value else None

    def last_known_good(self) -> tuple[bool, Any]:
        """Return (has_value, value) regardless of freshness."""
        with self._lock:
            return self._has_value, self._value

    def put(self, value: Any) -> None:
        with self._lock:
            self._value = value
            self._stamped_at = time.time()
            self._has_value = True


async def cached_isolated_read(
    fn: Callable[[], Any],
    *,
    cache: TTLSnapshotCache,
    timeout: float,
    empty_fallback: Any,
    label: str = "cached_read",
) -> Any:
    """TTL-cached, isolated, bounded read.

    Order of resolution:
      1. cache fresh          → return cached (zero threadpool tokens)
      2. compute on read pool → on success cache + return
      3. compute timed out/failed with warm cache → last-known-good
      4. no cache at all      → ``empty_fallback`` (stable shape)

    Byte-compatible: the value returned is exactly what ``fn`` produces; the
    cache and fallbacks carry the identical shape. Only freshness degrades.
    """
    is_fresh, cached_value = cache.get_fresh()
    if is_fresh:
        return cached_value

    sentinel = object()
    result = await isolated_read(fn, timeout=timeout, fallback=sentinel, label=label)
    if result is not sentinel:
        cache.put(result)
        return result

    has_lkg, lkg_value = cache.last_known_good()
    if has_lkg:
        logger.warning(
            "read '%s' degraded to last-known-good (compute exceeded %.1fs)",
            label,
            timeout,
        )
        return lkg_value
    return empty_fallback


def shutdown_read_pool() -> None:
    """Shut the dedicated read pool down (called from app lifespan teardown)."""
    global _READ_POOL
    with _READ_POOL_LOCK:
        if _READ_POOL is not None:
            _READ_POOL.shutdown(wait=False)
            _READ_POOL = None
