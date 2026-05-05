#!/usr/bin/env python3
"""watch_graph.py — Near real-time file watcher for the codebase graph.

Watches SCAN_DIRS (eos_ai, services, scripts, core) via watchdog/inotify and
triggers incremental graph updates as files are edited, created, or deleted.
Keeps the cognition stack fresh without manual rebuilds or git-hook latency.

Flow per event batch (debounced):
  1. Accumulate events for `--debounce` ms.
  2. Ask incremental_graph.update() to rebuild affected region.
  3. If the updater falls back to a full rebuild, that's logged.
  4. Optionally chain:
        run_graphify.py → merge_graphs.py → summarize_nodes.py
     behind --with-overlay.

Usage
-----
    python3 scripts/watch_graph.py
    python3 scripts/watch_graph.py --debounce 2000 --verbose
    python3 scripts/watch_graph.py --with-overlay
    python3 scripts/watch_graph.py --once eos_ai/memory.py   # smoke-test path

CLI flags
---------
    --debounce MS       event coalescing window (default 1500 ms)
    --with-overlay      run graphify + merge after each settled batch
    --full-threshold N  force full rebuild when >N unique files in one batch
    --verbose           log every event + timing
    --once PATH [...]   run a single incremental update for given paths, no watch
    --dry-run           log what WOULD happen, don't touch the graph
"""

from __future__ import annotations

import argparse
import json
import os
import signal
import subprocess
import sys
import threading
import time
from collections import deque
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable

sys.path.insert(0, "/opt/OS")

try:
    from watchdog.events import FileSystemEvent, FileSystemEventHandler
    from watchdog.observers import Observer
except ImportError as exc:  # pragma: no cover
    print(
        "watchdog not installed. Run:\n"
        "  pip3 install --break-system-packages -r scripts/requirements.txt",
        file=sys.stderr,
    )
    raise

from scripts.incremental_graph import (  # noqa: E402
    NON_PYTHON_EXTENSIONS,
    ROOT,
    SCAN_DIRS,
    SKIP_DIRS,
    SKIP_FILES,
    update as incremental_update,
)

PERF_LOG = ROOT / "data" / "watch_perf.log"

# Runaway detection: if >N events arrive in WINDOW seconds, back off debounce.
RUNAWAY_THRESHOLD = 20
RUNAWAY_WINDOW = 10.0
RUNAWAY_BACKOFF_MS = 5000

# Skip updates when load is above this (5-min avg unreliable, use 1-min).
CPU_GUARD_LOAD = 4.0

# Tracked extensions: python + non-python handled by the parser registry.
TRACKED_EXTS = {".py"} | set(NON_PYTHON_EXTENSIONS)


# ─── Helpers ─────────────────────────────────────────────────────────────────


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _is_tracked_path(abs_path: Path) -> bool:
    """Mirrors incremental_graph._is_tracked but operates on absolute paths."""
    try:
        rel = abs_path.resolve().relative_to(ROOT)
    except (ValueError, OSError):
        return False
    parts = rel.parts
    if not parts or parts[0] not in SCAN_DIRS:
        return False
    if any(part in SKIP_DIRS for part in parts):
        return False
    if rel.name in SKIP_FILES:
        return False
    if abs_path.suffix.lower() not in TRACKED_EXTS:
        return False
    return True


def _append_perf(record: dict[str, object]) -> None:
    PERF_LOG.parent.mkdir(parents=True, exist_ok=True)
    with PERF_LOG.open("a", encoding="utf-8") as f:
        f.write(json.dumps(record) + "\n")


# ─── Event handler ───────────────────────────────────────────────────────────


class CodebaseEventHandler(FileSystemEventHandler):
    """Accumulates file-system events into a thread-safe pending set."""

    def __init__(self, pending: set[str], lock: threading.Lock, cond: threading.Condition, verbose: bool):
        self.pending = pending
        self.lock = lock
        self.cond = cond
        self.verbose = verbose
        # For runaway detection
        self.recent_events: deque[float] = deque()

    def _record(self, src_path: str) -> None:
        p = Path(src_path)
        if not _is_tracked_path(p):
            return
        try:
            rel = str(p.resolve().relative_to(ROOT))
        except (ValueError, OSError):
            return
        with self.cond:
            self.pending.add(rel)
            self.recent_events.append(time.monotonic())
            # Trim window
            cutoff = time.monotonic() - RUNAWAY_WINDOW
            while self.recent_events and self.recent_events[0] < cutoff:
                self.recent_events.popleft()
            self.cond.notify()
        if self.verbose:
            print(f"[watch] event {p.suffix} → {rel}")

    # watchdog dispatches these on any file change (directories filtered via is_directory)
    def on_created(self, event: FileSystemEvent) -> None:
        if event.is_directory:
            return
        self._record(event.src_path)

    def on_modified(self, event: FileSystemEvent) -> None:
        if event.is_directory:
            return
        self._record(event.src_path)

    def on_deleted(self, event: FileSystemEvent) -> None:
        if event.is_directory:
            return
        self._record(event.src_path)

    def on_moved(self, event: FileSystemEvent) -> None:
        if event.is_directory:
            return
        # Treat as delete + create.
        self._record(event.src_path)
        dest = getattr(event, "dest_path", None)
        if dest:
            self._record(dest)

    # ─── Runaway helper ────────────────────────────────────────────────
    def runaway_active(self) -> bool:
        return len(self.recent_events) >= RUNAWAY_THRESHOLD


# ─── Overlay chain ───────────────────────────────────────────────────────────


def _run_overlay_chain(verbose: bool) -> None:
    """graphify → merge → summaries → palace(--with-overlay).

    Each step runs as a subprocess so a failure in one doesn't crash the
    watcher. Palace rebuild only emits candidate rooms; curated ROOM_DEFS
    remain the source of truth.
    """
    steps = [
        ("graphify", ["python3", str(ROOT / "scripts" / "run_graphify.py")]),
        ("merge", ["python3", str(ROOT / "scripts" / "merge_graphs.py")]),
        ("summaries", ["python3", str(ROOT / "scripts" / "summarize_nodes.py")]),
        (
            "palace",
            [
                "python3",
                str(ROOT / "scripts" / "build_palace.py"),
                "--with-overlay",
            ],
        ),
    ]
    for name, cmd in steps:
        if not Path(cmd[1]).exists():
            if verbose:
                print(f"[watch] overlay step '{name}' skipped (missing {cmd[1]})")
            continue
        start = time.monotonic()
        try:
            result = subprocess.run(
                cmd, capture_output=True, text=True, timeout=120, cwd=str(ROOT)
            )
        except Exception as exc:
            print(f"[watch] overlay '{name}' crashed: {exc}")
            continue
        duration = time.monotonic() - start
        if result.returncode != 0:
            print(
                f"[watch] overlay '{name}' failed ({duration:.1f}s): "
                f"{result.stderr.strip()[:160]}"
            )
            continue
        if verbose:
            print(f"[watch] overlay '{name}' ok ({duration:.2f}s)")


# ─── Main loop ───────────────────────────────────────────────────────────────


def _process_batch(
    paths: list[str],
    *,
    full_threshold: int,
    with_overlay: bool,
    dry_run: bool,
    verbose: bool,
    full_rebuild_on_error: bool = False,
) -> None:
    start = time.monotonic()
    load1 = 0.0
    try:
        load1 = os.getloadavg()[0]
    except (AttributeError, OSError):
        pass
    if load1 > CPU_GUARD_LOAD:
        print(f"[watch] CPU guard tripped (load {load1:.2f} > {CPU_GUARD_LOAD}), skipping batch of {len(paths)}")
        _append_perf(
            {
                "ts": _now(),
                "batch_size": len(paths),
                "skipped": "cpu_guard",
                "load1": load1,
            }
        )
        return

    forced_full = len(paths) > full_threshold
    mode = "full" if forced_full else "auto"

    if dry_run:
        print(
            f"[watch] DRY RUN mode={mode} batch={len(paths)} "
            f"paths={paths[:5]}{'…' if len(paths) > 5 else ''}"
        )
        return

    try:
        report = incremental_update(
            paths, mode=mode, verbose=verbose
        )
    except Exception as exc:
        print(f"[watch] incremental update crashed: {exc}")
        _append_perf(
            {
                "ts": _now(),
                "batch_size": len(paths),
                "error": str(exc),
                "phase": "incremental",
            }
        )
        if not full_rebuild_on_error:
            return
        # Escalate: run a forced full rebuild so the graph reconverges
        # even when an incremental scan crashed (malformed file, AST
        # regression, parser bug, etc.).
        print("[watch] --full-rebuild-on-error → escalating to full rebuild")
        try:
            report = incremental_update(paths, mode="full", verbose=verbose)
        except Exception as exc2:
            print(f"[watch] full rebuild also crashed: {exc2}")
            _append_perf(
                {
                    "ts": _now(),
                    "batch_size": len(paths),
                    "error": str(exc2),
                    "phase": "full_rebuild_escalation",
                }
            )
            return

    duration = time.monotonic() - start
    print(
        f"[watch] batch={len(paths)} → mode={report.get('mode')} "
        f"dirty_py={report.get('dirty_files', 0)} "
        f"edges_added={report.get('edges_added', 0)} "
        f"edges_removed={report.get('edges_removed', 0)} "
        f"in {duration:.2f}s"
    )
    _append_perf(
        {
            "ts": _now(),
            "batch_size": len(paths),
            "report": report,
            "duration_seconds": round(duration, 3),
        }
    )

    if with_overlay and report.get("mode") in ("incremental", "full"):
        _run_overlay_chain(verbose=verbose)


def _debounce_loop(
    handler: CodebaseEventHandler,
    pending: set[str],
    lock: threading.Lock,
    cond: threading.Condition,
    stop_flag: threading.Event,
    *,
    base_debounce_ms: int,
    full_threshold: int,
    with_overlay: bool,
    dry_run: bool,
    verbose: bool,
    full_rebuild_on_error: bool = False,
) -> None:
    """Pulls batches from the pending set on a debounced cadence and calls
    _process_batch for each settled batch."""
    while not stop_flag.is_set():
        with cond:
            # Wait until there is pending work or we get stopped.
            while not pending and not stop_flag.is_set():
                cond.wait(timeout=1.0)
            if stop_flag.is_set():
                return

            debounce_ms = base_debounce_ms
            if handler.runaway_active():
                debounce_ms = max(debounce_ms, RUNAWAY_BACKOFF_MS)
                if verbose:
                    print(
                        f"[watch] runaway active ({len(handler.recent_events)} "
                        f"events in {RUNAWAY_WINDOW}s) → backoff {debounce_ms}ms"
                    )

            # Settle period: keep waiting while new events arrive.
            last_size = len(pending)
            deadline = time.monotonic() + debounce_ms / 1000.0
            while time.monotonic() < deadline and not stop_flag.is_set():
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    break
                cond.wait(timeout=remaining)
                if len(pending) != last_size:
                    last_size = len(pending)
                    # Reset the deadline: new events extend the settle window.
                    deadline = time.monotonic() + debounce_ms / 1000.0

            if stop_flag.is_set():
                return

            batch = sorted(pending)
            pending.clear()

        _process_batch(
            batch,
            full_threshold=full_threshold,
            with_overlay=with_overlay,
            dry_run=dry_run,
            verbose=verbose,
            full_rebuild_on_error=full_rebuild_on_error,
        )


def watch(
    *,
    debounce_ms: int = 1500,
    with_overlay: bool = False,
    full_threshold: int = 100,
    dry_run: bool = False,
    verbose: bool = False,
    full_rebuild_on_error: bool = False,
) -> int:
    pending: set[str] = set()
    lock = threading.Lock()
    cond = threading.Condition(lock)
    stop_flag = threading.Event()

    handler = CodebaseEventHandler(pending, lock, cond, verbose=verbose)
    observer = Observer()

    watched = 0
    for scan in SCAN_DIRS:
        target = ROOT / scan
        if target.exists():
            observer.schedule(handler, str(target), recursive=True)
            watched += 1
            if verbose:
                print(f"[watch] watching {target}")
    if not watched:
        print(f"[watch] no SCAN_DIRS found under {ROOT}", file=sys.stderr)
        return 2

    observer.start()
    print(
        f"[watch] active — debounce={debounce_ms}ms overlay={with_overlay} "
        f"full_threshold={full_threshold} dry_run={dry_run} "
        f"rebuild_on_error={full_rebuild_on_error}"
    )
    print("[watch] press Ctrl+C to stop")

    worker = threading.Thread(
        target=_debounce_loop,
        args=(handler, pending, lock, cond, stop_flag),
        kwargs={
            "base_debounce_ms": debounce_ms,
            "full_threshold": full_threshold,
            "with_overlay": with_overlay,
            "dry_run": dry_run,
            "verbose": verbose,
            "full_rebuild_on_error": full_rebuild_on_error,
        },
        name="watch-debounce",
        daemon=True,
    )
    worker.start()

    def _shutdown(signum, frame):  # noqa: ARG001
        print(f"\n[watch] signal {signum} received, shutting down")
        stop_flag.set()
        with cond:
            cond.notify_all()

    signal.signal(signal.SIGINT, _shutdown)
    signal.signal(signal.SIGTERM, _shutdown)

    try:
        while not stop_flag.is_set():
            time.sleep(0.5)
    finally:
        observer.stop()
        observer.join(timeout=5)
        stop_flag.set()
        with cond:
            cond.notify_all()
        worker.join(timeout=5)
        print("[watch] stopped")
    return 0


def once(paths: Iterable[str], **kwargs) -> int:
    """Run a single batch without entering watch mode — used for smoke tests."""
    _process_batch(
        list(paths),
        full_threshold=kwargs.get("full_threshold", 100),
        with_overlay=kwargs.get("with_overlay", False),
        dry_run=kwargs.get("dry_run", False),
        verbose=kwargs.get("verbose", False),
        full_rebuild_on_error=kwargs.get("full_rebuild_on_error", False),
    )
    return 0


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="watch_graph")
    p.add_argument("--debounce", type=int, default=1500, help="ms (default 1500)")
    # Primary spec flag: --graphify. --with-overlay is retained as an
    # alias so existing invocations (docs, tmux panes, scripts) keep
    # working verbatim.
    p.add_argument(
        "--graphify",
        "--with-overlay",
        dest="with_overlay",
        action="store_true",
        help="run graphify + merge + palace overlay after each batch",
    )
    p.add_argument(
        "--full-threshold",
        type=int,
        default=100,
        help="force full rebuild when a batch exceeds this many files",
    )
    p.add_argument(
        "--full-rebuild-on-error",
        action="store_true",
        help="escalate to full rebuild when an incremental batch raises",
    )
    p.add_argument("--dry-run", action="store_true")
    p.add_argument("--verbose", "-v", action="store_true")
    p.add_argument(
        "--once",
        nargs="+",
        metavar="PATH",
        help="run a single batch without entering watch mode",
    )
    args = p.parse_args(argv)

    if args.once:
        return once(
            args.once,
            full_threshold=args.full_threshold,
            with_overlay=args.with_overlay,
            dry_run=args.dry_run,
            verbose=args.verbose,
            full_rebuild_on_error=args.full_rebuild_on_error,
        )

    return watch(
        debounce_ms=args.debounce,
        with_overlay=args.with_overlay,
        full_threshold=args.full_threshold,
        full_rebuild_on_error=args.full_rebuild_on_error,
        dry_run=args.dry_run,
        verbose=args.verbose,
    )


if __name__ == "__main__":
    sys.exit(main())
