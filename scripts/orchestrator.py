"""
orchestrator.py — Continuous, autonomous execution layer for EOS.

Sits above the workflow engine and turns it from an on-demand runner into a
self-driving system. Four internal agents cooperate:

  1. SCHEDULER AGENT       — time-based triggers (interval + "at HH:MM")
  2. EVENT AGENT           — watchdog filesystem events + completion hooks
  3. ORCHESTRATION AGENT   — job lifecycle, queueing, concurrency, retries
  4. VERIFICATION AGENT    — pre-submit checks + post-run stability guards

Design principles:
  * NEVER run an unbounded loop. Every wait checks a stop event.
  * Every job is idempotent-per-tick — the scheduler will not enqueue a job
    that is already queued or running (per concurrency_key).
  * Workflow failures are retried by the orchestrator with exponential
    backoff. The WorkflowEngine still retries *inside* a workflow; these are
    two different failure modes.
  * Every orchestrator action is logged to data/orchestrator_log.jsonl and,
    best-effort, to AgentMemory so the cognition stack can learn from it.
  * Runaway guard: a job that fails `failure_disable_at` times in a row is
    auto-disabled until operator intervention.

Integration:
  * scripts.workflow_engine.WorkflowEngine    — actual execution
  * scripts.workflow_engine.build_*_workflow  — built-in workflow factories
  * scripts.action_system.ActionSystem        — used by EXECUTE workflow steps
  * runtime.memory.AgentMemory                  — logging outcomes
  * watchdog.Observer                          — file-change events (same
                                                 lib scripts/watch_graph uses)

Usage (CLI):
    python3 scripts/orchestrator.py list
    python3 scripts/orchestrator.py status
    python3 scripts/orchestrator.py trigger research --goal "graph layer"
    python3 scripts/orchestrator.py start            # foreground, Ctrl-C stops
    python3 scripts/orchestrator.py start --once     # one scheduler tick, exit

Programmatic:
    from scripts.orchestrator import Orchestrator, Job, TriggerType
    from scripts.workflow_engine import build_research_workflow

    orch = Orchestrator()
    orch.register(Job(
        id="hourly-research",
        workflow_builder=lambda: build_research_workflow("scan for changes"),
        trigger_type=TriggerType.TIME,
        interval_sec=3600,
    ))
    orch.start()
    # ... later
    orch.stop()
"""

from __future__ import annotations

import argparse
import json
import signal
import sys
import threading
import time
import traceback
import uuid
from concurrent.futures import Future, ThreadPoolExecutor
from dataclasses import asdict, dataclass, field
from datetime import datetime, time as dtime, timezone
from enum import Enum
from pathlib import Path
from queue import Empty, Full, Queue
from typing import Any, Callable

# ── Repo root on sys.path ─────────────────────────────────────────────────
import os as _os

_REPO_ROOT = (
    _os.environ.get("UMH_ROOT")
    or _os.environ.get("OS_ROOT")
    or _os.environ.get("EOS_ROOT")
    or "/opt/OS"
)
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

from scripts.workflow_engine import (  # noqa: E402
    Workflow,
    WorkflowEngine,
    build_content_workflow,
    build_refactor_workflow,
    build_research_workflow,
)

# ── Paths ──────────────────────────────────────────────────────────────────
DATA_DIR = Path(_REPO_ROOT) / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)
ORCH_LOG = DATA_DIR / "orchestrator_log.jsonl"
ORCH_STATE = DATA_DIR / "orchestrator_state.json"


# ═══════════════════════════════════════════════════════════════════════════
# 1. DATA MODEL
# ═══════════════════════════════════════════════════════════════════════════


class TriggerType(str, Enum):
    TIME = "time"  # scheduled by interval or wall-clock time
    EVENT = "event"  # filesystem change or upstream workflow finished
    MANUAL = "manual"  # only fires when submit() is called explicitly


class JobStatus(str, Enum):
    IDLE = "idle"
    QUEUED = "queued"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    BACKOFF = "backoff"
    DISABLED = "disabled"


@dataclass
class Job:
    """One registered workflow + how/when it should run.

    Only ONE of (interval_sec, at_time, event_pattern) should be set for a
    given trigger_type. Validated by Verifier.validate_job().

    workflow_builder : zero-arg callable returning a Workflow. Called fresh
                       on every trigger so each run gets a unique workflow id.
    conditions       : optional callable returning bool. If provided, a time
                       trigger will only submit when conditions() is True.
    concurrency_key  : jobs sharing a key are mutually exclusive. Defaults
                       to the job id (so the same job cannot double-run).
    """

    id: str
    workflow_builder: Callable[[], Workflow]
    trigger_type: TriggerType = TriggerType.MANUAL
    interval_sec: int | None = None
    at_time: str | None = None  # "HH:MM" in local time
    event_pattern: str | None = None  # glob pattern against repo-relative path
    conditions: Callable[[], bool] | None = None
    concurrency_key: str | None = None
    max_retries: int = 3
    backoff_base: float = 30.0  # seconds; doubled per failure
    failure_disable_at: int = 5  # consecutive failures → DISABLED
    description: str = ""

    # Runtime fields (not part of the construction contract)
    status: JobStatus = JobStatus.IDLE
    last_run_at: str | None = None
    next_run_at: str | None = None
    last_result: str | None = None
    consecutive_failures: int = 0
    total_runs: int = 0
    total_successes: int = 0
    total_failures: int = 0

    def key(self) -> str:
        return self.concurrency_key or self.id

    def to_public(self) -> dict[str, Any]:
        """Serializable view — drops callables."""
        d = asdict(self)
        d.pop("workflow_builder", None)
        d.pop("conditions", None)
        d["trigger_type"] = self.trigger_type.value
        d["status"] = self.status.value
        return d


# ═══════════════════════════════════════════════════════════════════════════
# 2. VERIFICATION AGENT
# ═══════════════════════════════════════════════════════════════════════════


class Verifier:
    """Pre-submit validation + post-run stability guards.

    Does not run workflows itself — the WorkflowEngine has its own internal
    verifier. This class is about the *orchestration* layer: is this job
    well-formed, and is the system in a state where we should run it at all?
    """

    @staticmethod
    def validate_job(job: Job) -> list[str]:
        errors: list[str] = []
        if not job.id or not job.id.strip():
            errors.append("job.id is empty")
        if not callable(job.workflow_builder):
            errors.append("job.workflow_builder must be callable")
        if job.trigger_type == TriggerType.TIME:
            has_interval = job.interval_sec is not None and job.interval_sec > 0
            has_at = bool(job.at_time)
            if not (has_interval or has_at):
                errors.append("time trigger requires interval_sec or at_time")
            if has_at:
                try:
                    _parse_hhmm(job.at_time or "")
                except ValueError as e:
                    errors.append(f"at_time invalid: {e}")
        if job.trigger_type == TriggerType.EVENT and not job.event_pattern:
            errors.append("event trigger requires event_pattern")
        if job.max_retries < 0:
            errors.append("max_retries must be >= 0")
        if job.backoff_base <= 0:
            errors.append("backoff_base must be > 0")
        return errors

    @staticmethod
    def system_is_healthy() -> tuple[bool, str]:
        """Cheap liveness check before submitting work.

        Intentionally permissive — we log the signal but don't block. The
        orchestrator is meant to run on a contended VPS; a strict load guard
        here would wedge the system into permanent BACKOFF. We only hard-fail
        if the repo root is unreachable.
        """
        if not Path(_REPO_ROOT).exists():
            return (False, "repo root missing")
        return (True, "")


def _parse_hhmm(s: str) -> dtime:
    parts = s.strip().split(":")
    if len(parts) != 2:
        raise ValueError(f"expected HH:MM, got {s!r}")
    h, m = int(parts[0]), int(parts[1])
    if not (0 <= h < 24 and 0 <= m < 60):
        raise ValueError(f"out of range: {s!r}")
    return dtime(hour=h, minute=m)


# ═══════════════════════════════════════════════════════════════════════════
# 3. ACTIVITY LOG
# ═══════════════════════════════════════════════════════════════════════════


class ActivityLog:
    """Append-only JSONL log + best-effort AgentMemory mirror.

    The JSONL file is authoritative. AgentMemory is a nice-to-have so the
    cognition stack can semantic-search the orchestrator's history.
    """

    def __init__(self, path: Path = ORCH_LOG, *, verbose: bool = False) -> None:
        self.path = path
        self.verbose = verbose
        self._lock = threading.Lock()
        self._memory_warned = False

    def emit(self, event: str, **fields: Any) -> None:
        entry = {
            "ts": datetime.now(timezone.utc).isoformat(),
            "event": event,
        }
        entry.update(fields)
        line = json.dumps(entry, default=str)
        with self._lock:
            try:
                with self.path.open("a", encoding="utf-8") as f:
                    f.write(line + "\n")
            except Exception as e:
                if self.verbose:
                    print(f"[orchestrator] log write failed: {e}")
        if self.verbose:
            print(f"[orchestrator] {event} {fields.get('job_id', '')}".rstrip())

    def persist_to_memory(self, job: Job, result: dict[str, Any]) -> None:
        """Best-effort — never raises, never blocks the scheduler."""
        try:
            from execution.runtime.agent_runtime import AgentResult
            from state.memory.memory import AgentMemory

            summary = (
                f"job={job.id} status={result.get('status', '?')} "
                f"ok={result.get('ok', False)} "
                f"runs={job.total_runs} failures={job.total_failures}"
            )
            ar = AgentResult(
                output=summary,
                model_used="orchestrator",
                tokens_used={"input": 0, "output": 0, "total": 0},
                skill_used=f"orchestrator:{job.id}",
            )
            AgentMemory().log(
                agent_result=ar,
                venture_id=None,
                input_summary=(job.description or job.id)[:300],
                agent="orchestrator",
                task_type="orchestration",
                lead_username=None,
            )
        except Exception as e:
            # Only warn once — AgentMemory may be down on a pre-revenue VPS
            if not self._memory_warned:
                self._memory_warned = True
                if self.verbose:
                    print(f"[orchestrator] memory log unavailable: {e}")


# ═══════════════════════════════════════════════════════════════════════════
# 4. EXECUTION QUEUE  (ORCHESTRATION AGENT core)
# ═══════════════════════════════════════════════════════════════════════════


class ExecutionQueue:
    """Bounded queue + thread pool that actually runs workflows.

    * Max queue depth bounds backpressure — submit() raises Full rather than
      growing memory forever.
    * max_concurrent bounds how many workflows can run simultaneously.
    * active_keys tracks per-concurrency-key occupancy so the same job
      cannot run twice in parallel even if scheduled twice.
    """

    def __init__(
        self,
        *,
        max_concurrent: int = 2,
        max_queue: int = 100,
        verbose: bool = False,
    ) -> None:
        self.max_concurrent = max_concurrent
        self.max_queue = max_queue
        self.verbose = verbose
        self._queue: Queue[tuple[Job, dict[str, Any]]] = Queue(maxsize=max_queue)
        self._pool = ThreadPoolExecutor(
            max_workers=max_concurrent,
            thread_name_prefix="orch-worker",
        )
        self._active_keys: set[str] = set()
        self._active_lock = threading.Lock()
        self._stop = threading.Event()
        self._dispatcher: threading.Thread | None = None
        self._engine = WorkflowEngine(verbose=verbose)
        self._log = ActivityLog(verbose=verbose)
        self._on_complete: list[Callable[[Job, dict], None]] = []

    # ── Lifecycle ────────────────────────────────────────────────────────

    def start(self) -> None:
        if self._dispatcher is not None and self._dispatcher.is_alive():
            return
        self._stop.clear()
        self._dispatcher = threading.Thread(
            target=self._dispatch_loop,
            name="orch-dispatcher",
            daemon=True,
        )
        self._dispatcher.start()
        self._log.emit("queue_started", max_concurrent=self.max_concurrent)

    def stop(self, *, timeout: float = 10.0) -> None:
        self._stop.set()
        # Drain: push a sentinel so the dispatcher unblocks
        try:
            self._queue.put_nowait((None, None))  # type: ignore[arg-type]
        except Full:
            pass
        if self._dispatcher is not None:
            self._dispatcher.join(timeout=timeout)
        self._pool.shutdown(wait=True, cancel_futures=False)
        self._log.emit("queue_stopped")

    # ── Submit ───────────────────────────────────────────────────────────

    def submit(self, job: Job, *, reason: str = "manual") -> bool:
        """Enqueue a job run. Returns True if accepted, False otherwise.

        Refuses if: queue full, already active with same concurrency key,
        or job is DISABLED.
        """
        if self._stop.is_set():
            return False
        if job.status == JobStatus.DISABLED:
            self._log.emit("submit_rejected", job_id=job.id, why="disabled")
            return False
        key = job.key()
        with self._active_lock:
            if key in self._active_keys:
                self._log.emit("submit_rejected", job_id=job.id, why="key_busy")
                return False
        try:
            self._queue.put_nowait((job, {"reason": reason}))
        except Full:
            self._log.emit("submit_rejected", job_id=job.id, why="queue_full")
            return False
        job.status = JobStatus.QUEUED
        self._log.emit(
            "job_queued",
            job_id=job.id,
            reason=reason,
            queue_depth=self._queue.qsize(),
        )
        return True

    def on_complete(self, handler: Callable[[Job, dict], None]) -> None:
        """Register a callback fired after every run (success OR failure)."""
        self._on_complete.append(handler)

    # ── Internal dispatch ────────────────────────────────────────────────

    def _dispatch_loop(self) -> None:
        while not self._stop.is_set():
            try:
                item = self._queue.get(timeout=0.5)
            except Empty:
                continue
            if item is None or item[0] is None:
                # sentinel
                self._queue.task_done()
                break
            job, meta = item
            try:
                self._pool.submit(self._run_job, job, meta)
            except RuntimeError:
                # pool shut down mid-flight
                break
            finally:
                self._queue.task_done()

    def _run_job(self, job: Job, meta: dict[str, Any]) -> None:
        key = job.key()
        with self._active_lock:
            self._active_keys.add(key)
        job.status = JobStatus.RUNNING
        job.last_run_at = datetime.now(timezone.utc).isoformat()
        job.total_runs += 1
        self._log.emit("job_started", job_id=job.id, reason=meta.get("reason"))

        result: dict[str, Any] = {}
        ok = False
        err: str | None = None
        try:
            wf = job.workflow_builder()
            result = self._engine.run_workflow(wf, dry_run=False)
            ok = bool(result.get("ok"))
        except Exception as exc:  # noqa: BLE001 — orchestration guard
            err = f"{type(exc).__name__}: {exc}"
            if self.verbose:
                traceback.print_exc()
        finally:
            with self._active_lock:
                self._active_keys.discard(key)

        if ok:
            job.status = JobStatus.SUCCEEDED
            job.consecutive_failures = 0
            job.total_successes += 1
            job.last_result = result.get("status", "completed")
            self._log.emit("job_succeeded", job_id=job.id, result=result)
        else:
            job.consecutive_failures += 1
            job.total_failures += 1
            job.last_result = err or str(result.get("status", "failed"))
            if job.consecutive_failures >= job.failure_disable_at:
                job.status = JobStatus.DISABLED
                self._log.emit(
                    "job_disabled",
                    job_id=job.id,
                    consecutive_failures=job.consecutive_failures,
                )
            else:
                job.status = JobStatus.FAILED
                self._log.emit(
                    "job_failed",
                    job_id=job.id,
                    error=job.last_result,
                    consecutive_failures=job.consecutive_failures,
                )

        self._log.persist_to_memory(job, result if ok else {"status": "failed", "ok": False})

        # Fire completion handlers (retry policy + event hooks live here)
        for handler in list(self._on_complete):
            try:
                handler(job, result)
            except Exception as e:  # noqa: BLE001
                if self.verbose:
                    print(f"[orchestrator] on_complete handler failed: {e}")

    # ── Inspection ───────────────────────────────────────────────────────

    def depth(self) -> int:
        return self._queue.qsize()

    def active_keys(self) -> set[str]:
        with self._active_lock:
            return set(self._active_keys)


# ═══════════════════════════════════════════════════════════════════════════
# 5. SCHEDULER AGENT
# ═══════════════════════════════════════════════════════════════════════════


class SchedulerAgent:
    """Time-based trigger thread. Ticks once a second.

    For interval jobs: schedules next_run = now + interval_sec after each
    submission (drift-free — we don't care about wall-clock precision, only
    monotonic cadence).

    For at_time jobs: fires at most once per day at the matching HH:MM.
    """

    def __init__(
        self,
        orchestrator: "Orchestrator",
        *,
        tick_sec: float = 1.0,
        verbose: bool = False,
    ) -> None:
        self.orch = orchestrator
        self.tick_sec = tick_sec
        self.verbose = verbose
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None
        self._last_at_fire: dict[str, str] = {}  # job_id → "YYYY-MM-DD HH:MM"

    def start(self) -> None:
        if self._thread is not None and self._thread.is_alive():
            return
        self._stop.clear()
        self._thread = threading.Thread(
            target=self._loop,
            name="orch-scheduler",
            daemon=True,
        )
        self._thread.start()

    def stop(self, timeout: float = 5.0) -> None:
        self._stop.set()
        if self._thread is not None:
            self._thread.join(timeout=timeout)

    def tick_once(self) -> int:
        """One pass over the registry. Returns the number of jobs submitted."""
        submitted = 0
        now = time.time()
        for job in self.orch.jobs():
            if job.trigger_type != TriggerType.TIME:
                continue
            if job.status in (JobStatus.DISABLED, JobStatus.QUEUED, JobStatus.RUNNING):
                continue
            if job.conditions is not None:
                try:
                    if not job.conditions():
                        continue
                except Exception as e:  # noqa: BLE001
                    self.orch.log.emit("job_condition_error", job_id=job.id, error=str(e))
                    continue

            if job.interval_sec is not None:
                # Use next_run_at as epoch string if present; otherwise seed
                if job.next_run_at is None:
                    job.next_run_at = str(now + job.interval_sec)
                    continue
                try:
                    due = float(job.next_run_at)
                except ValueError:
                    due = now
                if now >= due:
                    if self.orch.submit(job, reason="scheduled_interval"):
                        job.next_run_at = str(now + job.interval_sec)
                        submitted += 1
            elif job.at_time:
                try:
                    target = _parse_hhmm(job.at_time)
                except ValueError:
                    continue
                now_local = datetime.now()
                key = f"{now_local.date().isoformat()} {job.at_time}"
                already = self._last_at_fire.get(job.id) == key
                if (
                    not already
                    and now_local.hour == target.hour
                    and now_local.minute == target.minute
                ):
                    if self.orch.submit(job, reason="scheduled_at_time"):
                        self._last_at_fire[job.id] = key
                        submitted += 1
        return submitted

    def _loop(self) -> None:
        while not self._stop.is_set():
            try:
                self.tick_once()
            except Exception as e:  # noqa: BLE001
                if self.verbose:
                    traceback.print_exc()
                self.orch.log.emit("scheduler_error", error=str(e))
            # Short sleeps, checked against stop event → clean shutdown
            self._stop.wait(self.tick_sec)


# ═══════════════════════════════════════════════════════════════════════════
# 6. EVENT AGENT
# ═══════════════════════════════════════════════════════════════════════════


class EventAgent:
    """Event-driven triggers.

    Two event families:
      1. Filesystem changes — via watchdog. Jobs can register a glob pattern
         (e.g. "runtime/*.py"). The first match in a debounce window submits
         the job. watchdog is optional — if it's not installed, FS events
         are silently disabled and the orchestrator still runs.
      2. Workflow-completion hooks — a job can subscribe to "after job X
         succeeds, run me". Implemented via on_complete callback on the
         execution queue.
    """

    DEBOUNCE_SEC = 1.5

    def __init__(
        self,
        orchestrator: "Orchestrator",
        *,
        watch_dirs: list[str] | None = None,
        verbose: bool = False,
    ) -> None:
        self.orch = orchestrator
        self.verbose = verbose
        self.watch_dirs = watch_dirs or ["runtime", "services", "scripts", "core"]
        self._observer: Any = None
        self._last_fire: dict[str, float] = {}
        self._completion_hooks: dict[str, list[str]] = {}  # source_job → [target_jobs]
        # Wire completion hook dispatch into the queue
        self.orch.queue.on_complete(self._on_workflow_complete)

    # ── Filesystem watcher ──────────────────────────────────────────────

    def start(self) -> None:
        try:
            from watchdog.events import FileSystemEventHandler
            from watchdog.observers import Observer
        except ImportError:
            self.orch.log.emit("event_agent_no_watchdog")
            return

        handler = self._make_handler(FileSystemEventHandler)
        self._observer = Observer()
        for d in self.watch_dirs:
            p = Path(_REPO_ROOT) / d
            if p.exists():
                self._observer.schedule(handler, str(p), recursive=True)
        self._observer.daemon = True
        self._observer.start()
        self.orch.log.emit("event_agent_started", watch_dirs=self.watch_dirs)

    def stop(self, timeout: float = 5.0) -> None:
        if self._observer is not None:
            obs = self._observer
            self._observer = None  # clear ref early to avoid GC SIGABRT
            try:
                obs.stop()
                obs.join(timeout=timeout)
            except Exception:
                pass
            # If join timed out, the thread is still alive. Mark it
            # as daemon so interpreter shutdown won't wait on it.
            try:
                obs.daemon = True
            except Exception:
                pass

    def _make_handler(self, base_cls: type) -> Any:
        outer = self

        class _Handler(base_cls):  # type: ignore[misc,valid-type]
            def on_any_event(self, event: Any) -> None:
                try:
                    if getattr(event, "is_directory", False):
                        return
                    path = Path(getattr(event, "src_path", ""))
                    try:
                        rel = str(path.relative_to(_REPO_ROOT))
                    except ValueError:
                        rel = str(path)
                    outer._dispatch_fs_event(rel)
                except Exception as e:  # noqa: BLE001
                    if outer.verbose:
                        print(f"[orchestrator] event handler error: {e}")

        return _Handler()

    def _dispatch_fs_event(self, rel_path: str) -> None:
        now = time.time()
        from fnmatch import fnmatch

        for job in self.orch.jobs():
            if job.trigger_type != TriggerType.EVENT or not job.event_pattern:
                continue
            if not fnmatch(rel_path, job.event_pattern):
                continue
            # Debounce per job
            last = self._last_fire.get(job.id, 0.0)
            if now - last < self.DEBOUNCE_SEC:
                continue
            self._last_fire[job.id] = now
            self.orch.submit(job, reason=f"fs_event:{rel_path}")

    # ── Workflow completion hooks ───────────────────────────────────────

    def chain(self, source_job_id: str, target_job_id: str) -> None:
        """When source succeeds, submit target."""
        self._completion_hooks.setdefault(source_job_id, []).append(target_job_id)

    def _on_workflow_complete(self, job: Job, result: dict[str, Any]) -> None:
        targets = self._completion_hooks.get(job.id) or []
        for tid in targets:
            target = self.orch.registry.get(tid)
            if target is None:
                continue
            if not bool(result.get("ok")):
                continue
            self.orch.submit(target, reason=f"chain_from:{job.id}")


# ═══════════════════════════════════════════════════════════════════════════
# 7. RETRY POLICY
# ═══════════════════════════════════════════════════════════════════════════


class RetryPolicy:
    """Exponential backoff across job runs.

    Invoked via on_complete: after a failure, schedules the job for a retry
    after base * 2^(consecutive_failures-1) seconds by setting next_run_at.
    For EVENT jobs we don't reschedule — the next event will retry naturally.
    """

    def __init__(self, orchestrator: "Orchestrator", *, verbose: bool = False) -> None:
        self.orch = orchestrator
        self.verbose = verbose
        orchestrator.queue.on_complete(self._handle)

    def _handle(self, job: Job, result: dict[str, Any]) -> None:
        if result.get("ok"):
            return
        if job.status == JobStatus.DISABLED:
            return
        if job.consecutive_failures > job.max_retries:
            return
        if job.trigger_type != TriggerType.TIME:
            return
        delay = job.backoff_base * (2 ** (job.consecutive_failures - 1))
        job.status = JobStatus.BACKOFF
        job.next_run_at = str(time.time() + delay)
        self.orch.log.emit(
            "job_backoff",
            job_id=job.id,
            delay_sec=delay,
            consecutive_failures=job.consecutive_failures,
        )


# ═══════════════════════════════════════════════════════════════════════════
# 8. ORCHESTRATOR
# ═══════════════════════════════════════════════════════════════════════════


class Orchestrator:
    """Top-level coordinator. One per process.

    Lifecycle:
        orch = Orchestrator()
        orch.register(job1); orch.register(job2)
        orch.start()         # non-blocking; spawns scheduler + event + queue
        ...
        orch.stop()          # signals all threads + drains queue
    """

    def __init__(
        self,
        *,
        max_concurrent: int = 2,
        max_queue: int = 100,
        tick_sec: float = 1.0,
        watch_dirs: list[str] | None = None,
        verbose: bool = False,
    ) -> None:
        self.verbose = verbose
        self.log = ActivityLog(verbose=verbose)
        self.registry: dict[str, Job] = {}
        self.queue = ExecutionQueue(
            max_concurrent=max_concurrent,
            max_queue=max_queue,
            verbose=verbose,
        )
        self.scheduler = SchedulerAgent(self, tick_sec=tick_sec, verbose=verbose)
        self.events = EventAgent(self, watch_dirs=watch_dirs, verbose=verbose)
        self.retry = RetryPolicy(self, verbose=verbose)
        self._started = False
        self._stop_signal = threading.Event()

    # ── Registration ─────────────────────────────────────────────────────

    def register(self, job: Job) -> None:
        errors = Verifier.validate_job(job)
        if errors:
            raise ValueError(f"invalid job {job.id!r}: {errors}")
        if job.id in self.registry:
            raise ValueError(f"duplicate job id: {job.id!r}")
        self.registry[job.id] = job
        self.log.emit(
            "job_registered",
            job_id=job.id,
            trigger=job.trigger_type.value,
            description=job.description,
        )

    def unregister(self, job_id: str) -> bool:
        job = self.registry.pop(job_id, None)
        if job is None:
            return False
        self.log.emit("job_unregistered", job_id=job_id)
        return True

    def jobs(self) -> list[Job]:
        return list(self.registry.values())

    # ── Submission ───────────────────────────────────────────────────────

    def submit(self, job: Job, *, reason: str = "manual") -> bool:
        ok, why = Verifier.system_is_healthy()
        if not ok:
            self.log.emit("submit_blocked", job_id=job.id, why=why)
            return False
        return self.queue.submit(job, reason=reason)

    def trigger(self, job_id: str, *, reason: str = "manual_trigger") -> bool:
        job = self.registry.get(job_id)
        if job is None:
            return False
        return self.submit(job, reason=reason)

    # ── Lifecycle ────────────────────────────────────────────────────────

    def start(self) -> None:
        if self._started:
            return
        self._started = True
        self._stop_signal.clear()
        self.queue.start()
        self.scheduler.start()
        self.events.start()
        self.log.emit(
            "orchestrator_started",
            jobs=len(self.registry),
            max_concurrent=self.queue.max_concurrent,
        )

    def stop(self) -> None:
        if not self._started:
            return
        self._started = False
        self._stop_signal.set()
        self.events.stop()
        self.scheduler.stop()
        self.queue.stop()
        self.log.emit("orchestrator_stopped")

    def wait(self) -> None:
        """Block until stop() is called. Intended for foreground `start`."""
        try:
            while not self._stop_signal.is_set():
                self._stop_signal.wait(1.0)
        except KeyboardInterrupt:
            self.stop()

    # ── Inspection ───────────────────────────────────────────────────────

    def status(self) -> dict[str, Any]:
        return {
            "started": self._started,
            "queue_depth": self.queue.depth(),
            "max_concurrent": self.queue.max_concurrent,
            "active_keys": sorted(self.queue.active_keys()),
            "jobs": [j.to_public() for j in self.jobs()],
        }

    def save_state(self) -> None:
        try:
            ORCH_STATE.write_text(
                json.dumps(self.status(), indent=2, default=str),
                encoding="utf-8",
            )
        except Exception as e:
            if self.verbose:
                print(f"[orchestrator] state save failed: {e}")


# ═══════════════════════════════════════════════════════════════════════════
# 9. EXAMPLE JOBS
# ═══════════════════════════════════════════════════════════════════════════


def _graph_freshness_ok() -> bool:
    """Condition: don't run maintenance if the graph file is missing entirely."""
    graph_file = Path(_REPO_ROOT) / "data" / "codebase_graph.json"
    return graph_file.exists()


def build_default_jobs() -> list[Job]:
    """The three example workflows from the spec, wired into orchestration."""
    return [
        Job(
            id="continuous-research",
            description="Every 2h: scan graph + recent signals via research workflow.",
            workflow_builder=lambda: build_research_workflow(
                "What changed in EOS in the last 2 hours? "
                "Summarize the most structurally significant edits."
            ),
            trigger_type=TriggerType.TIME,
            interval_sec=2 * 60 * 60,
            max_retries=2,
            backoff_base=60.0,
        ),
        Job(
            id="content-pipeline",
            description="Daily at 09:00: generate + refine content for Initiate Arena.",
            workflow_builder=lambda: build_content_workflow(
                "Write a tactical-luxury tweet positioning Initiate Arena "
                "for the Life Maxing audience."
            ),
            trigger_type=TriggerType.TIME,
            at_time="09:00",
            max_retries=2,
            backoff_base=120.0,
        ),
        Job(
            id="system-maintenance",
            description="Every 30m: verify graph freshness via refactor/impact workflow.",
            workflow_builder=lambda: build_refactor_workflow(
                "Audit graph freshness — no code changes, read-only.",
                target_file="scripts/query_graph.py",
            ),
            trigger_type=TriggerType.TIME,
            interval_sec=30 * 60,
            conditions=_graph_freshness_ok,
            max_retries=1,
            backoff_base=30.0,
        ),
    ]


# ═══════════════════════════════════════════════════════════════════════════
# 10. CLI
# ═══════════════════════════════════════════════════════════════════════════


def _install_signal_handlers(orch: Orchestrator) -> None:
    def _handler(signum: int, frame: Any) -> None:
        print(f"\n[orchestrator] signal {signum} received — stopping...")
        orch.stop()

    for sig in (signal.SIGINT, signal.SIGTERM):
        try:
            signal.signal(sig, _handler)
        except ValueError:
            # Not in main thread — skip
            pass


def _cmd_list(args: argparse.Namespace) -> int:
    orch = Orchestrator()
    for j in build_default_jobs():
        orch.register(j)
    print("Registered jobs:")
    for j in orch.jobs():
        trig = j.trigger_type.value
        spec = (
            f"every {j.interval_sec}s"
            if j.interval_sec
            else f"at {j.at_time}"
            if j.at_time
            else f"on {j.event_pattern}"
            if j.event_pattern
            else "manual"
        )
        print(f"  - {j.id:22s}  [{trig}] {spec}")
        if j.description:
            print(f"      {j.description}")
    return 0


def _cmd_status(args: argparse.Namespace) -> int:
    # Status from the last saved state file, not a live process
    if not ORCH_STATE.exists():
        print("no saved state (orchestrator has not run yet)")
        return 1
    print(ORCH_STATE.read_text())
    return 0


def _cmd_trigger(args: argparse.Namespace) -> int:
    """Run one workflow immediately, synchronously. Good for smoke tests."""
    orch = Orchestrator(verbose=args.verbose)
    for j in build_default_jobs():
        orch.register(j)

    # Ad-hoc workflow builder from CLI args, if --goal given
    if args.name in ("research", "content", "refactor"):
        builders = {
            "research": build_research_workflow,
            "content": build_content_workflow,
            "refactor": build_refactor_workflow,
        }
        builder = builders[args.name]
        goal = args.goal or f"ad-hoc {args.name} run"
        job = Job(
            id=f"adhoc-{args.name}-{uuid.uuid4().hex[:6]}",
            workflow_builder=(lambda g=goal, b=builder: b(g)),
            trigger_type=TriggerType.MANUAL,
            description=f"ad-hoc {args.name}",
        )
        orch.register(job)
        target_id = job.id
    else:
        target_id = args.name

    orch.start()
    ok = orch.trigger(target_id, reason="cli_trigger")
    if not ok:
        print(f"trigger failed: {target_id}")
        orch.stop()
        return 2
    # Wait for the queue to drain this one job
    deadline = time.time() + (args.timeout or 600)
    while time.time() < deadline:
        job = orch.registry.get(target_id)
        if job and job.status in (
            JobStatus.SUCCEEDED,
            JobStatus.FAILED,
            JobStatus.DISABLED,
        ):
            break
        time.sleep(0.5)
    orch.save_state()
    orch.stop()
    job = orch.registry.get(target_id)
    print(json.dumps(job.to_public() if job else {"error": "lost"}, indent=2))
    return 0 if job and job.status == JobStatus.SUCCEEDED else 2


def _cmd_start(args: argparse.Namespace) -> int:
    orch = Orchestrator(
        max_concurrent=args.max_concurrent,
        max_queue=args.max_queue,
        verbose=args.verbose,
    )
    for j in build_default_jobs():
        orch.register(j)

    _install_signal_handlers(orch)
    orch.start()
    print(
        f"[orchestrator] started with {len(orch.jobs())} jobs "
        f"(max_concurrent={args.max_concurrent}, max_queue={args.max_queue})"
    )
    print("[orchestrator] Ctrl-C to stop")

    if args.once:
        orch.scheduler.tick_once()
        # Let any submitted work drain
        time.sleep(2.0)
        orch.save_state()
        orch.stop()
        return 0

    try:
        while orch._started:
            time.sleep(5.0)
            orch.save_state()
    except KeyboardInterrupt:
        pass
    orch.stop()
    return 0


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(
        prog="orchestrator",
        description="EOS orchestration layer — continuous autonomous execution.",
    )
    sub = ap.add_subparsers(dest="cmd", required=True)

    p_list = sub.add_parser("list", help="list default registered jobs")
    p_list.set_defaults(func=_cmd_list)

    p_status = sub.add_parser("status", help="show last saved orchestrator state")
    p_status.set_defaults(func=_cmd_status)

    p_trigger = sub.add_parser("trigger", help="run one workflow synchronously")
    p_trigger.add_argument(
        "name",
        help="job id OR workflow type (research/content/refactor)",
    )
    p_trigger.add_argument("--goal", default="", help="goal string for ad-hoc runs")
    p_trigger.add_argument("--timeout", type=int, default=600, help="seconds")
    p_trigger.add_argument("-v", "--verbose", action="store_true")
    p_trigger.set_defaults(func=_cmd_trigger)

    p_start = sub.add_parser("start", help="start the orchestrator in foreground")
    p_start.add_argument("--max-concurrent", type=int, default=2)
    p_start.add_argument("--max-queue", type=int, default=100)
    p_start.add_argument(
        "--once",
        action="store_true",
        help="run one scheduler tick and exit (smoke test)",
    )
    p_start.add_argument("-v", "--verbose", action="store_true")
    p_start.set_defaults(func=_cmd_start)

    args = ap.parse_args(argv)
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())
