#!/usr/bin/env python3
"""P4S-31C bounded load probe — CPU-law compliant.

Simulates the cockpit poll profile against a target operator API and reports
latency percentiles for the P4S-31 read surface (/intent-loop) plus the hot
sibling pollers. Read-only; GETs only; no mutations.

SAFETY (Hostinger VPS, 4 cores):
- max 8 concurrent requests
- hard wall-clock cap (default 60s)
- aborts immediately if /proc/loadavg 1-min average exceeds 3.0
- intended to be launched under `nice -n 15`

Usage:
  nice -n 15 python3 scripts/p4s31c_load_probe.py \
    --base http://127.0.0.1:8199/api/umh --duration 45 --concurrency 8
"""

from __future__ import annotations

import argparse
import asyncio
import statistics
import time
from typing import Any

import httpx

# The cockpit poll profile: the P4S-31 surface + the hot sibling pollers named
# in the diagnosis. All GET, all read-only.
_POLL_PATHS = [
    "/intent-loop",
    "/pulse",
    "/unified-workstation/snapshot",
    "/build",
    "/models",
]

_LOAD_ABORT = 3.0
_MAX_CONCURRENCY = 8


def _loadavg_1m() -> float:
    with open("/proc/loadavg", encoding="utf-8") as fh:
        return float(fh.read().split()[0])


async def _worker(
    client: httpx.AsyncClient,
    base: str,
    deadline: float,
    sem: asyncio.Semaphore,
    results: dict[str, list[float]],
    stop: asyncio.Event,
) -> None:
    idx = 0
    while time.monotonic() < deadline and not stop.is_set():
        path = _POLL_PATHS[idx % len(_POLL_PATHS)]
        idx += 1
        async with sem:
            start = time.monotonic()
            try:
                resp = await client.get(base + path, timeout=65.0)
                elapsed = time.monotonic() - start
                results.setdefault(path, []).append(elapsed)
                _ = resp.status_code
            except Exception:
                elapsed = time.monotonic() - start
                results.setdefault(path + " [ERR]", []).append(elapsed)


async def _load_guard(stop: asyncio.Event, deadline: float) -> None:
    while time.monotonic() < deadline and not stop.is_set():
        la = _loadavg_1m()
        if la > _LOAD_ABORT:
            print(f"ABORT: loadavg {la:.2f} > {_LOAD_ABORT}")
            stop.set()
            return
        await asyncio.sleep(1.0)


def _pct(values: list[float], p: float) -> float:
    if not values:
        return 0.0
    s = sorted(values)
    k = max(0, min(len(s) - 1, int(round((p / 100.0) * (len(s) - 1)))))
    return s[k]


async def _main(base: str, duration: float, concurrency: int) -> None:
    concurrency = min(concurrency, _MAX_CONCURRENCY)
    sem = asyncio.Semaphore(concurrency)
    results: dict[str, list[float]] = {}
    stop = asyncio.Event()
    deadline = time.monotonic() + duration

    print(f"probe: base={base} duration={duration}s concurrency={concurrency}")
    print(f"loadavg at start: {_loadavg_1m():.2f}")

    async with httpx.AsyncClient() as client:
        workers = [
            asyncio.create_task(_worker(client, base, deadline, sem, results, stop))
            for _ in range(concurrency)
        ]
        guard = asyncio.create_task(_load_guard(stop, deadline))
        await asyncio.gather(*workers)
        stop.set()
        await guard

    print(f"loadavg at end:   {_loadavg_1m():.2f}")
    print()
    print(f"{'path':<44} {'n':>5} {'p50':>8} {'p95':>8} {'p99':>8} {'max':>8}")
    for path in sorted(results):
        vals = results[path]
        print(
            f"{path:<44} {len(vals):>5} "
            f"{_pct(vals, 50) * 1000:>7.0f}m {_pct(vals, 95) * 1000:>7.0f}m "
            f"{_pct(vals, 99) * 1000:>7.0f}m {max(vals) * 1000:>7.0f}m"
        )
    # Focused summary for the acceptance surface.
    il = results.get("/intent-loop", [])
    if il:
        print()
        print(
            f"/intent-loop  n={len(il)}  "
            f"p50={_pct(il, 50) * 1000:.0f}ms  p95={_pct(il, 95) * 1000:.0f}ms  "
            f"p99={_pct(il, 99) * 1000:.0f}ms  max={max(il) * 1000:.0f}ms"
        )


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", required=True)
    ap.add_argument("--duration", type=float, default=45.0)
    ap.add_argument("--concurrency", type=int, default=8)
    args = ap.parse_args()
    if args.duration > 90:
        raise SystemExit("duration capped at 90s by CPU law")
    asyncio.run(_main(args.base, args.duration, args.concurrency))
