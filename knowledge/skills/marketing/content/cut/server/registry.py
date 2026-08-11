"""JobRegistry — background work for CutStudio (D6).

Two lanes with fixed worker counts: `transcribe` (1 worker — a whisper
instance must never be entered concurrently) and `render` (2 workers —
ffmpeg is short and I/O bound). Threads, not asyncio: the payloads are
blocking subprocess and CTranslate2 calls.

CPU-gate discipline (the reason this registry exists rather than
FastAPI BackgroundTasks): before a job runs, `cpu_gate_check` decides
whether the host can take it. A refused job goes BACK to `queued` with
detail "host busy, retrying" and is retried by the lane every
RETRY_SECONDS — it is NOT an error. A `gated_subprocess_run` returning
None inside a worker is disambiguated the same way: re-check the gate,
and only call it a real error when the gate says work was allowed.
"""

from __future__ import annotations

import logging
import queue
import threading
import time
import uuid
from dataclasses import asdict, dataclass, field
from typing import Callable

from substrate.execution.cpu_gate import cpu_gate_check

logger = logging.getLogger("cutstudio.registry")

PRUNE_AFTER_SECONDS = 24 * 3600
RETRY_SECONDS = 60.0
BUSY_DETAIL = "host busy, retrying"

LANES = {"transcribe": 1, "render": 2}


@dataclass
class Job:
    """One unit of background work. `artifact` holds the worker's result."""

    id: str
    kind: str
    project_id: str
    state: str = "queued"  # queued|running|done|error
    detail: str = ""
    progress: float = 0.0
    artifact: object | None = None
    created: float = field(default_factory=time.time)
    started: float | None = None
    finished: float | None = None

    def to_dict(self) -> dict:
        return asdict(self)


class JobRegistry:
    """Thread-backed job store. One instance per process."""

    def __init__(self) -> None:
        self._jobs: dict[str, Job] = {}
        self._lock = threading.Lock()
        self._queues: dict[str, queue.Queue] = {lane: queue.Queue() for lane in LANES}
        self._threads: list[threading.Thread] = []
        self._started = False

    # ── lifecycle ────────────────────────────────────────────────────────
    def start(self) -> None:
        """Spawn the worker threads. Idempotent."""
        with self._lock:
            if self._started:
                return
            self._started = True
        for lane, count in LANES.items():
            for n in range(count):
                t = threading.Thread(
                    target=self._worker,
                    args=(lane,),
                    name="cutstudio-%s-%d" % (lane, n),
                    daemon=True,
                )
                t.start()
                self._threads.append(t)
        logger.info("job registry started: %s", LANES)

    # ── submission ───────────────────────────────────────────────────────
    def submit(self, kind: str, project_id: str, fn: Callable[[Job], object]) -> Job:
        """Queue `fn` on the lane for `kind`. `fn` receives the Job and may
        set `job.progress`; its return value becomes `job.artifact`."""
        lane = "transcribe" if kind == "transcribe" else "render"
        job = Job(id=uuid.uuid4().hex[:12], kind=kind, project_id=project_id)
        with self._lock:
            self._jobs[job.id] = job
        self._queues[lane].put((job.id, fn))
        self._prune()
        return job

    def get(self, job_id: str) -> Job | None:
        with self._lock:
            return self._jobs.get(job_id)

    def running_count(self) -> int:
        with self._lock:
            return sum(1 for j in self._jobs.values() if j.state == "running")

    def list_for_project(self, project_id: str) -> list[dict]:
        with self._lock:
            return [j.to_dict() for j in self._jobs.values() if j.project_id == project_id]

    # ── internals ────────────────────────────────────────────────────────
    def _prune(self) -> None:
        cutoff = time.time() - PRUNE_AFTER_SECONDS
        with self._lock:
            stale = [
                jid
                for jid, j in self._jobs.items()
                if j.state in ("done", "error") and (j.finished or j.created) < cutoff
            ]
            for jid in stale:
                del self._jobs[jid]

    def _worker(self, lane: str) -> None:
        q = self._queues[lane]
        while True:
            job_id, fn = q.get()
            try:
                self._run_one(lane, job_id, fn, q)
            except Exception as exc:  # a worker thread must never die
                logger.exception("worker %s crashed on job %s: %s", lane, job_id, exc)
            finally:
                q.task_done()

    def _run_one(self, lane: str, job_id: str, fn: Callable, q: queue.Queue) -> None:
        job = self.get(job_id)
        if job is None:
            return

        gate = cpu_gate_check("cutstudio.%s" % lane)
        if not gate.allowed:
            # Not an error — the host is hot. Re-queue after a cooldown.
            with self._lock:
                job.state = "queued"
                job.detail = BUSY_DETAIL
            threading.Timer(RETRY_SECONDS, lambda: q.put((job_id, fn))).start()
            logger.info("job %s deferred (load/core %.2f)", job_id, gate.load_per_core)
            return

        with self._lock:
            job.state = "running"
            job.detail = ""
            job.started = time.time()
        try:
            artifact = fn(job)
            with self._lock:
                job.artifact = artifact
                job.state = "done"
                job.progress = 1.0
                job.finished = time.time()
        except Exception as exc:
            logger.warning("job %s (%s) failed: %s", job_id, job.kind, exc)
            with self._lock:
                job.state = "error"
                job.detail = str(exc)[:500]
                job.finished = time.time()


def gate_failure_detail(caller: str) -> str:
    """Explain a `gated_subprocess_run` -> None.

    The wrapper returns None for two very different reasons: the CPU gate
    refused, or the binary was missing. Re-checking the gate separates them
    so a busy host is never reported as a broken install.
    """
    gate = cpu_gate_check(caller)
    if not gate.allowed:
        return BUSY_DETAIL
    return "command failed to start (binary missing or not runnable)"


_registry: JobRegistry | None = None


def get_registry() -> JobRegistry:
    """Process-wide registry singleton."""
    global _registry
    if _registry is None:
        _registry = JobRegistry()
    return _registry
