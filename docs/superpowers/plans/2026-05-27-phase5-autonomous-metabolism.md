# Phase 5: Event-Driven Autonomous Metabolism — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Transform UMH from request-triggered orchestration to continuous governed organism metabolism — a self-regulating operational nervous system that observes, prioritizes, allocates, supervises, and routes work without direct prompts.

**Architecture:** Layer-by-layer build: (1) Unified Event Spine as the canonical organism event transport, (2) Autonomous Tick Engine as the metabolism heartbeat, (3) Runtime Event Bus wiring all subsystems to the spine, (4) Continuous Objective Queue with lifecycle state machine, (5) Governed Runtime Allocation Loop for adaptive leverage, (6) Async Coordinator Execution converting synchronous DAG execution to event-driven, (7) Continuous Leverage Rebalancing for adaptive routing optimization, (8) Cockpit Realtime Stream via WebSocket SSE upgrade, (9) Meta-IDE Runtime Streams for operational topology, (10) Projection-Agnostic State interfaces for universal consumption.

**Tech Stack:** Python 3.11, dataclasses, enums, asyncio, threading, WebSocket (Hono upgrade_websocket), existing PersistentLoop/ViewSocket infrastructure.

**Anti-Divergence Rules:**
- All new types registered in `substrate/canonical_types.py`
- No imports from transports/services/projections into substrate/
- No instance-specific values in substrate/ code
- No duplicate orchestration paths — extend existing subsystems
- RecursionGovernor governs all autonomous loops
- `scripts/check_type_divergence.py --all` must pass before commit
- `scripts/check_instance_leak.py --all` must pass before commit

---

## File Structure

### New Files (substrate/organism/)

| File | Responsibility |
|------|---------------|
| `substrate/organism/event_spine.py` | Canonical organism event transport — emit, subscribe, replay, snapshot |
| `substrate/organism/autonomous_tick.py` | Continuous metabolism loop with adaptive cadence, governed pause/kill |
| `substrate/organism/objective_queue.py` | Persistent async objective intake with priority, retry, lifecycle FSM |
| `substrate/organism/allocation_loop.py` | Continuous governed runtime allocation — load monitoring, rebalancing |
| `substrate/organism/async_coordinator.py` | Async wrapper around OrganismCoordinator — submit, track, cancel |
| `substrate/organism/projection_port.py` | Projection-agnostic organism state interface — abstract port pattern |

### New Files (tests)

| File | Tests |
|------|-------|
| `substrate/organism/tests/test_event_spine.py` | Event emission, subscription, replay, snapshot, filtering |
| `substrate/organism/tests/test_autonomous_tick.py` | Tick lifecycle, governance interruption, adaptive cadence, degraded mode |
| `substrate/organism/tests/test_objective_queue.py` | Queue ordering, retry, lifecycle FSM, governance escalation |
| `substrate/organism/tests/test_allocation_loop.py` | Load monitoring, rebalancing, throttling, economy integration |
| `substrate/organism/tests/test_async_coordinator.py` | Async submit, progress tracking, cancellation, dependency wakeups |
| `substrate/organism/tests/test_projection_port.py` | Port registration, snapshot delivery, filtering |

### New Files (saas/ — cockpit realtime)

| File | Responsibility |
|------|---------------|
| `saas/api/routes/ws.ts` | WebSocket upgrade endpoint for organism event streaming |
| `saas/bridge/organism_stream_bridge.py` | Python-side event spine → stdout JSON stream for cockpit |

### Modified Files

| File | Changes |
|------|---------|
| `substrate/organism/__init__.py` | Export new public API |
| `substrate/organism/advisor.py` | Wire `_emit_event` to EventSpine instead of ViewSocket directly |
| `substrate/organism/orchestration_loop.py` | Emit events per stage via spine, integrate autonomous tick |
| `substrate/organism/runtime_graph.py` | Emit runtime lifecycle events to spine |
| `substrate/organism/runtime_supervisor.py` | Emit health/crash/recovery events to spine |
| `substrate/organism/coordinator.py` | Add async execution hooks, emit objective lifecycle events |
| `substrate/organism/leverage_assimilation.py` | Add continuous rebalancing loop, emit leverage events |
| `substrate/organism/daemon.py` | Wire EventSpine, AutonomousTick, AllocationLoop into daemon |
| `substrate/canonical_types.py` | Register new enums: EventDomain, EventPriority, ObjectiveQueueStatus, AllocationStrategy |
| `saas/api/index.ts` | Mount WebSocket route |

### Audit File

| File | Purpose |
|------|---------|
| `docs/audits/convergence/phase5_autonomous_metabolism.md` | Architecture delta, flow diagrams, subsystem wiring |

---

## Task 1: Unified Event Spine

**Files:**
- Create: `substrate/organism/event_spine.py`
- Create: `substrate/organism/tests/test_event_spine.py`
- Modify: `substrate/canonical_types.py`

This is the foundation — every subsequent task emits events through this spine.

- [ ] **Step 1: Register new canonical types**

Add to `substrate/canonical_types.py` in the organism section:

```python
# ── substrate/organism/event_spine.py ──────────────────────────────
"EventDomain": ["substrate.organism.event_spine"],
"EventPriority": ["substrate.organism.event_spine"],
```

- [ ] **Step 2: Write failing tests for EventSpine**

Create `substrate/organism/tests/test_event_spine.py`:

```python
"""Tests for the unified organism event spine."""

from __future__ import annotations

import sys
import time

sys.path.insert(0, "/opt/OS")

from substrate.organism.event_spine import (
    EventDomain,
    EventPriority,
    EventSpine,
    OrganismEvent,
)


def test_event_creation():
    event = OrganismEvent(
        domain=EventDomain.RUNTIME,
        event_type="runtime_available",
        source="runtime_graph",
        data={"runtime_id": "cc-opus", "status": "available"},
    )
    assert event.domain == EventDomain.RUNTIME
    assert event.event_type == "runtime_available"
    assert event.source == "runtime_graph"
    assert event.data["runtime_id"] == "cc-opus"
    assert event.timestamp > 0
    assert event.event_id != ""
    d = event.to_dict()
    assert d["domain"] == "runtime"
    assert d["event_type"] == "runtime_available"


def test_event_priority_default():
    event = OrganismEvent(
        domain=EventDomain.GOVERNANCE,
        event_type="kill_switch_activated",
        source="recursion_governor",
        data={},
    )
    assert event.priority == EventPriority.NORMAL


def test_event_priority_critical():
    event = OrganismEvent(
        domain=EventDomain.GOVERNANCE,
        event_type="kill_switch_activated",
        source="recursion_governor",
        data={},
        priority=EventPriority.CRITICAL,
    )
    assert event.priority == EventPriority.CRITICAL


def test_spine_emit_and_recent():
    spine = EventSpine()
    spine.emit(EventDomain.RUNTIME, "runtime_available", "graph", {"id": "r1"})
    spine.emit(EventDomain.GOVERNANCE, "approval_required", "governor", {"id": "a1"})

    recent = spine.recent(limit=10)
    assert len(recent) == 2
    assert recent[0].event_type == "runtime_available"
    assert recent[1].event_type == "approval_required"


def test_spine_subscribe_and_receive():
    spine = EventSpine()
    received = []

    def handler(event: OrganismEvent) -> None:
        received.append(event)

    spine.subscribe("test-sub", handler)
    spine.emit(EventDomain.RUNTIME, "runtime_available", "graph", {"id": "r1"})

    assert len(received) == 1
    assert received[0].event_type == "runtime_available"


def test_spine_subscribe_with_domain_filter():
    spine = EventSpine()
    runtime_events = []
    governance_events = []

    spine.subscribe("runtime-watcher", lambda e: runtime_events.append(e),
                    domains={EventDomain.RUNTIME})
    spine.subscribe("gov-watcher", lambda e: governance_events.append(e),
                    domains={EventDomain.GOVERNANCE})

    spine.emit(EventDomain.RUNTIME, "runtime_available", "graph", {})
    spine.emit(EventDomain.GOVERNANCE, "approval_required", "governor", {})
    spine.emit(EventDomain.RUNTIME, "runtime_degraded", "supervisor", {})

    assert len(runtime_events) == 2
    assert len(governance_events) == 1


def test_spine_unsubscribe():
    spine = EventSpine()
    received = []
    spine.subscribe("sub1", lambda e: received.append(e))

    spine.emit(EventDomain.RUNTIME, "test", "src", {})
    assert len(received) == 1

    spine.unsubscribe("sub1")
    spine.emit(EventDomain.RUNTIME, "test2", "src", {})
    assert len(received) == 1


def test_spine_replay():
    spine = EventSpine()
    spine.emit(EventDomain.RUNTIME, "ev1", "src", {})
    spine.emit(EventDomain.GOVERNANCE, "ev2", "src", {})
    spine.emit(EventDomain.RUNTIME, "ev3", "src", {})

    replayed = spine.replay(domains={EventDomain.RUNTIME})
    assert len(replayed) == 2
    assert replayed[0].event_type == "ev1"
    assert replayed[1].event_type == "ev3"


def test_spine_replay_since():
    spine = EventSpine()
    spine.emit(EventDomain.RUNTIME, "old", "src", {})
    cutoff = time.time()
    time.sleep(0.01)
    spine.emit(EventDomain.RUNTIME, "new", "src", {})

    replayed = spine.replay(since=cutoff)
    assert len(replayed) == 1
    assert replayed[0].event_type == "new"


def test_spine_snapshot():
    spine = EventSpine()
    spine.emit(EventDomain.RUNTIME, "ev1", "src", {"a": 1})
    spine.emit(EventDomain.GOVERNANCE, "ev2", "src", {"b": 2})

    snap = spine.snapshot()
    assert snap["total_events"] == 2
    assert "runtime" in snap["events_by_domain"]
    assert "governance" in snap["events_by_domain"]
    assert snap["events_by_domain"]["runtime"] == 1
    assert snap["events_by_domain"]["governance"] == 1


def test_spine_max_events_bounded():
    spine = EventSpine(max_events=5)
    for i in range(10):
        spine.emit(EventDomain.RUNTIME, f"ev{i}", "src", {})

    recent = spine.recent(limit=100)
    assert len(recent) == 5
    assert recent[0].event_type == "ev5"


def test_spine_subscriber_error_isolation():
    spine = EventSpine()
    good_received = []

    def bad_handler(event: OrganismEvent) -> None:
        raise RuntimeError("boom")

    def good_handler(event: OrganismEvent) -> None:
        good_received.append(event)

    spine.subscribe("bad", bad_handler)
    spine.subscribe("good", good_handler)

    spine.emit(EventDomain.RUNTIME, "test", "src", {})
    assert len(good_received) == 1


def test_event_domains_cover_all_required():
    required = {
        "runtime", "governance", "advisor", "workcell", "objective",
        "execution", "leverage", "supervisor", "filesystem", "tmux",
        "docker", "projection", "transport", "recursion", "memory",
        "observability",
    }
    actual = {d.value for d in EventDomain}
    assert required.issubset(actual), f"missing domains: {required - actual}"


def test_spine_correlation_id():
    spine = EventSpine()
    spine.emit(EventDomain.OBJECTIVE, "started", "coord", {},
               correlation_id="obj-123")
    spine.emit(EventDomain.OBJECTIVE, "completed", "coord", {},
               correlation_id="obj-123")

    recent = spine.recent(limit=10)
    assert all(e.correlation_id == "obj-123" for e in recent)
```

- [ ] **Step 3: Run tests to verify they fail**

Run: `cd /opt/OS/.claude/worktrees/anti-divergence-gate && python3 -m pytest substrate/organism/tests/test_event_spine.py -v`

Expected: ImportError — module does not exist yet.

- [ ] **Step 4: Implement EventSpine**

Create `substrate/organism/event_spine.py`:

```python
"""Unified organism event spine — canonical event transport layer.

All organism subsystem state changes emit events through this spine.
Subscribers receive events synchronously during emit(). The spine is
append-only, timestamped, source-traceable, and replay-safe.

Supported event domains cover the full organism surface:
runtime, governance, advisor, workcell, objective, execution,
leverage, supervisor, filesystem, tmux, docker, projection,
transport, recursion, memory, observability.

Design properties:
  - In-memory first, future persistence-ready (append-only log)
  - Thread-safe via threading.Lock
  - Subscriber error isolation (one bad handler cannot block others)
  - Domain-filtered subscriptions
  - Bounded event buffer (configurable max_events)
  - Correlation ID for threading related events

UMH substrate subsystem. Instance-agnostic.
"""

from __future__ import annotations

import logging
import threading
import time
from collections import deque
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable
from uuid import uuid4

logger = logging.getLogger(__name__)


class EventDomain(str, Enum):
    RUNTIME = "runtime"
    GOVERNANCE = "governance"
    ADVISOR = "advisor"
    WORKCELL = "workcell"
    OBJECTIVE = "objective"
    EXECUTION = "execution"
    LEVERAGE = "leverage"
    SUPERVISOR = "supervisor"
    FILESYSTEM = "filesystem"
    TMUX = "tmux"
    DOCKER = "docker"
    PROJECTION = "projection"
    TRANSPORT = "transport"
    RECURSION = "recursion"
    MEMORY = "memory"
    OBSERVABILITY = "observability"


class EventPriority(str, Enum):
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass(frozen=True)
class OrganismEvent:
    domain: EventDomain
    event_type: str
    source: str
    data: dict[str, Any]
    priority: EventPriority = EventPriority.NORMAL
    event_id: str = field(default_factory=lambda: uuid4().hex[:12])
    timestamp: float = field(default_factory=time.time)
    correlation_id: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "event_id": self.event_id,
            "domain": self.domain.value,
            "event_type": self.event_type,
            "source": self.source,
            "priority": self.priority.value,
            "data": self.data,
            "timestamp": self.timestamp,
            "correlation_id": self.correlation_id,
        }


EventHandler = Callable[[OrganismEvent], None]


@dataclass
class _Subscriber:
    subscriber_id: str
    handler: EventHandler
    domains: frozenset[EventDomain] | None


class EventSpine:
    """Canonical organism event transport.

    Thread-safe, bounded, append-only event log with pub/sub.
    """

    def __init__(self, max_events: int = 10_000) -> None:
        self._events: deque[OrganismEvent] = deque(maxlen=max_events)
        self._subscribers: dict[str, _Subscriber] = {}
        self._lock = threading.Lock()

    def emit(
        self,
        domain: EventDomain,
        event_type: str,
        source: str,
        data: dict[str, Any],
        priority: EventPriority = EventPriority.NORMAL,
        correlation_id: str | None = None,
    ) -> OrganismEvent:
        event = OrganismEvent(
            domain=domain,
            event_type=event_type,
            source=source,
            data=data,
            priority=priority,
            correlation_id=correlation_id,
        )
        with self._lock:
            self._events.append(event)
            subscribers = list(self._subscribers.values())

        for sub in subscribers:
            if sub.domains is not None and domain not in sub.domains:
                continue
            try:
                sub.handler(event)
            except Exception as exc:
                logger.warning(
                    "event subscriber '%s' raised %s: %s",
                    sub.subscriber_id, type(exc).__name__, exc,
                )

        return event

    def subscribe(
        self,
        subscriber_id: str,
        handler: EventHandler,
        domains: set[EventDomain] | None = None,
    ) -> None:
        frozen = frozenset(domains) if domains is not None else None
        with self._lock:
            self._subscribers[subscriber_id] = _Subscriber(
                subscriber_id=subscriber_id,
                handler=handler,
                domains=frozen,
            )
        logger.debug("event subscriber registered: %s", subscriber_id)

    def unsubscribe(self, subscriber_id: str) -> None:
        with self._lock:
            self._subscribers.pop(subscriber_id, None)
        logger.debug("event subscriber removed: %s", subscriber_id)

    def recent(self, limit: int = 50) -> list[OrganismEvent]:
        with self._lock:
            events = list(self._events)
        return events[-limit:] if len(events) > limit else events

    def replay(
        self,
        domains: set[EventDomain] | None = None,
        since: float | None = None,
    ) -> list[OrganismEvent]:
        with self._lock:
            events = list(self._events)

        result = []
        for event in events:
            if since is not None and event.timestamp <= since:
                continue
            if domains is not None and event.domain not in domains:
                continue
            result.append(event)
        return result

    def snapshot(self) -> dict[str, Any]:
        with self._lock:
            events = list(self._events)

        by_domain: dict[str, int] = {}
        for event in events:
            domain_val = event.domain.value
            by_domain[domain_val] = by_domain.get(domain_val, 0) + 1

        return {
            "total_events": len(events),
            "events_by_domain": by_domain,
            "subscriber_count": len(self._subscribers),
            "subscribers": list(self._subscribers.keys()),
            "oldest_timestamp": events[0].timestamp if events else None,
            "newest_timestamp": events[-1].timestamp if events else None,
        }
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `cd /opt/OS/.claude/worktrees/anti-divergence-gate && python3 -m pytest substrate/organism/tests/test_event_spine.py -v`

Expected: All 14 tests PASS.

- [ ] **Step 6: Compile check**

Run: `python3 -m py_compile substrate/organism/event_spine.py`

Expected: No output (clean compile).

- [ ] **Step 7: Commit**

```bash
git add substrate/organism/event_spine.py substrate/organism/tests/test_event_spine.py substrate/canonical_types.py
git commit -m "feat(organism): unified event spine — canonical organism event transport"
```

---

## Task 2: Autonomous Tick Engine

**Files:**
- Create: `substrate/organism/autonomous_tick.py`
- Create: `substrate/organism/tests/test_autonomous_tick.py`

Depends on: Task 1 (EventSpine)

The heartbeat of the organism. Replaces the static PersistentLoop-only model with an adaptive, governed, event-emitting metabolism loop.

- [ ] **Step 1: Write failing tests**

Create `substrate/organism/tests/test_autonomous_tick.py`:

```python
"""Tests for the autonomous tick engine."""

from __future__ import annotations

import sys
import time
import threading

sys.path.insert(0, "/opt/OS")

from substrate.organism.autonomous_tick import (
    AutonomousTick,
    TickConfig,
    TickMetrics,
    TickStage,
)
from substrate.organism.event_spine import EventDomain, EventSpine


def _make_tick(interval: float = 0.05, **kwargs) -> AutonomousTick:
    spine = EventSpine()
    config = TickConfig(
        base_interval_seconds=interval,
        min_interval_seconds=0.01,
        max_interval_seconds=1.0,
        **kwargs,
    )
    return AutonomousTick(spine=spine, config=config)


def test_tick_config_defaults():
    config = TickConfig()
    assert config.base_interval_seconds == 30.0
    assert config.min_interval_seconds == 5.0
    assert config.max_interval_seconds == 300.0
    assert config.adaptive_cadence is True


def test_tick_register_stage():
    tick = _make_tick()
    called = []
    tick.register_stage("test_stage", lambda: called.append(1))
    assert "test_stage" in tick.stages


def test_tick_single_cycle():
    tick = _make_tick()
    results = []
    tick.register_stage("stage_a", lambda: results.append("a"))
    tick.register_stage("stage_b", lambda: results.append("b"))

    report = tick.execute_cycle()
    assert report.cycle_number == 1
    assert report.stages_executed == 2
    assert report.stages_failed == 0
    assert results == ["a", "b"]


def test_tick_stage_failure_isolation():
    tick = _make_tick()
    good_results = []

    def bad_stage():
        raise RuntimeError("boom")

    tick.register_stage("bad", bad_stage)
    tick.register_stage("good", lambda: good_results.append(1))

    report = tick.execute_cycle()
    assert report.stages_executed == 2
    assert report.stages_failed == 1
    assert len(good_results) == 1


def test_tick_emits_events():
    spine = EventSpine()
    config = TickConfig(base_interval_seconds=0.05)
    tick = AutonomousTick(spine=spine, config=config)
    tick.register_stage("noop", lambda: None)

    tick.execute_cycle()
    events = spine.recent(limit=50)

    tick_events = [e for e in events if e.event_type == "tick_completed"]
    assert len(tick_events) == 1
    assert tick_events[0].domain == EventDomain.EXECUTION


def test_tick_governance_kill():
    tick = _make_tick()
    tick.register_stage("noop", lambda: None)

    tick.kill()
    assert tick.is_killed

    report = tick.execute_cycle()
    assert report.stages_executed == 0
    assert report.skipped_reason == "killed"


def test_tick_governance_pause_resume():
    tick = _make_tick()
    tick.register_stage("noop", lambda: None)

    tick.pause()
    assert tick.is_paused

    report = tick.execute_cycle()
    assert report.stages_executed == 0
    assert report.skipped_reason == "paused"

    tick.resume()
    report = tick.execute_cycle()
    assert report.stages_executed == 1


def test_tick_metrics():
    tick = _make_tick()
    tick.register_stage("fast", lambda: None)

    tick.execute_cycle()
    tick.execute_cycle()

    metrics = tick.metrics
    assert metrics.total_cycles == 2
    assert metrics.total_stages_executed == 2
    assert metrics.total_stages_failed == 0
    assert metrics.avg_cycle_ms >= 0


def test_tick_adaptive_cadence_speeds_up():
    tick = _make_tick(interval=1.0, adaptive_cadence=True)
    results = []
    tick.register_stage("work", lambda: results.append(1))

    tick.execute_cycle()
    first_interval = tick.current_interval

    for _ in range(5):
        tick.execute_cycle()

    assert tick.current_interval <= first_interval


def test_tick_adaptive_cadence_slows_down():
    tick = _make_tick(interval=0.05, adaptive_cadence=True)

    def idle_stage():
        pass

    tick.register_stage("idle", idle_stage)

    for _ in range(20):
        tick.execute_cycle()

    assert tick.current_interval >= 0.05


def test_tick_run_loop_stops_on_kill():
    tick = _make_tick(interval=0.02)
    tick.register_stage("noop", lambda: None)

    def kill_after_delay():
        time.sleep(0.05)
        tick.kill()

    threading.Thread(target=kill_after_delay, daemon=True).start()
    tick.run(max_cycles=100)

    assert tick.is_killed
    assert tick.metrics.total_cycles >= 1
    assert tick.metrics.total_cycles < 100


def test_tick_to_dict():
    tick = _make_tick()
    tick.register_stage("s1", lambda: None)
    tick.execute_cycle()

    d = tick.to_dict()
    assert "metrics" in d
    assert "config" in d
    assert "stages" in d
    assert "is_killed" in d
    assert "is_paused" in d
    assert "current_interval" in d
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd /opt/OS/.claude/worktrees/anti-divergence-gate && python3 -m pytest substrate/organism/tests/test_autonomous_tick.py -v`

Expected: ImportError.

- [ ] **Step 3: Implement AutonomousTick**

Create `substrate/organism/autonomous_tick.py`:

```python
"""Autonomous tick engine — continuous metabolism heartbeat.

The tick engine runs the organism's operational loop: each cycle
executes registered stages (refresh runtimes, inspect queues,
rebalance leverage, emit state updates, etc.) with:

  - Governed pause/kill via RecursionGovernor integration
  - Adaptive cadence: speeds up under load, slows down when idle
  - Per-stage failure isolation: one bad stage cannot crash the tick
  - Tick metrics for observability
  - Event emission through the EventSpine

Usage:
    spine = EventSpine()
    tick = AutonomousTick(spine=spine)
    tick.register_stage("refresh_runtimes", graph.refresh_availability)
    tick.register_stage("homeostasis", homeostasis.check)
    tick.run()  # blocks until killed

UMH substrate subsystem. Instance-agnostic.
"""

from __future__ import annotations

import logging
import time
import threading
from dataclasses import dataclass, field
from typing import Any, Callable

from substrate.organism.event_spine import EventDomain, EventPriority, EventSpine

logger = logging.getLogger(__name__)

StageFunction = Callable[[], Any]


@dataclass
class TickConfig:
    base_interval_seconds: float = 30.0
    min_interval_seconds: float = 5.0
    max_interval_seconds: float = 300.0
    adaptive_cadence: bool = True
    speedup_factor: float = 0.85
    slowdown_factor: float = 1.15
    idle_threshold_cycles: int = 3


@dataclass
class TickMetrics:
    total_cycles: int = 0
    total_stages_executed: int = 0
    total_stages_failed: int = 0
    total_elapsed_ms: float = 0.0
    consecutive_idle: int = 0

    @property
    def avg_cycle_ms(self) -> float:
        if self.total_cycles == 0:
            return 0.0
        return self.total_elapsed_ms / self.total_cycles


@dataclass
class TickStage:
    name: str
    function: StageFunction


@dataclass
class CycleReport:
    cycle_number: int
    stages_executed: int = 0
    stages_failed: int = 0
    elapsed_ms: float = 0.0
    had_work: bool = False
    skipped_reason: str | None = None
    stage_details: list[dict[str, Any]] = field(default_factory=list)


class AutonomousTick:
    """Continuous organism metabolism loop.

    Executes registered stages each cycle, emits events to the spine,
    adapts cadence based on workload, and respects governance kill/pause.
    """

    def __init__(
        self,
        spine: EventSpine,
        config: TickConfig | None = None,
    ) -> None:
        self._spine = spine
        self._config = config or TickConfig()
        self._stages: list[TickStage] = []
        self._metrics = TickMetrics()
        self._current_interval = self._config.base_interval_seconds
        self._killed = False
        self._paused = False
        self._stop_event = threading.Event()
        self._cycle_count = 0

    @property
    def stages(self) -> dict[str, StageFunction]:
        return {s.name: s.function for s in self._stages}

    @property
    def metrics(self) -> TickMetrics:
        return self._metrics

    @property
    def current_interval(self) -> float:
        return self._current_interval

    @property
    def is_killed(self) -> bool:
        return self._killed

    @property
    def is_paused(self) -> bool:
        return self._paused

    def register_stage(self, name: str, function: StageFunction) -> None:
        self._stages.append(TickStage(name=name, function=function))

    def kill(self) -> None:
        self._killed = True
        self._stop_event.set()
        self._spine.emit(
            EventDomain.GOVERNANCE, "tick_killed", "autonomous_tick",
            {"cycle": self._cycle_count},
            priority=EventPriority.CRITICAL,
        )

    def pause(self) -> None:
        self._paused = True
        self._spine.emit(
            EventDomain.GOVERNANCE, "tick_paused", "autonomous_tick",
            {"cycle": self._cycle_count},
        )

    def resume(self) -> None:
        self._paused = False
        self._spine.emit(
            EventDomain.GOVERNANCE, "tick_resumed", "autonomous_tick",
            {"cycle": self._cycle_count},
        )

    def execute_cycle(self) -> CycleReport:
        self._cycle_count += 1
        report = CycleReport(cycle_number=self._cycle_count)

        if self._killed:
            report.skipped_reason = "killed"
            return report

        if self._paused:
            report.skipped_reason = "paused"
            return report

        start = time.monotonic_ns()
        had_work = False

        for stage in self._stages:
            try:
                result = stage.function()
                report.stages_executed += 1
                is_work = result is not None and result is not False
                if is_work:
                    had_work = True
                report.stage_details.append({
                    "stage": stage.name, "success": True,
                    "had_work": is_work,
                })
            except Exception as exc:
                report.stages_executed += 1
                report.stages_failed += 1
                logger.warning("tick stage '%s' failed: %s", stage.name, exc)
                report.stage_details.append({
                    "stage": stage.name, "success": False,
                    "error": str(exc)[:200],
                })

        elapsed_ms = (time.monotonic_ns() - start) / 1_000_000
        report.elapsed_ms = elapsed_ms
        report.had_work = had_work

        self._metrics.total_cycles += 1
        self._metrics.total_stages_executed += report.stages_executed
        self._metrics.total_stages_failed += report.stages_failed
        self._metrics.total_elapsed_ms += elapsed_ms

        if had_work:
            self._metrics.consecutive_idle = 0
        else:
            self._metrics.consecutive_idle += 1

        if self._config.adaptive_cadence:
            self._adapt_cadence(had_work)

        self._spine.emit(
            EventDomain.EXECUTION, "tick_completed", "autonomous_tick",
            {
                "cycle": self._cycle_count,
                "stages_executed": report.stages_executed,
                "stages_failed": report.stages_failed,
                "elapsed_ms": round(elapsed_ms, 2),
                "had_work": had_work,
                "interval": round(self._current_interval, 2),
            },
        )

        return report

    def _adapt_cadence(self, had_work: bool) -> None:
        if had_work:
            self._current_interval = max(
                self._config.min_interval_seconds,
                self._current_interval * self._config.speedup_factor,
            )
        elif self._metrics.consecutive_idle >= self._config.idle_threshold_cycles:
            self._current_interval = min(
                self._config.max_interval_seconds,
                self._current_interval * self._config.slowdown_factor,
            )

    def run(self, max_cycles: int | None = None) -> None:
        cycles = 0
        while not self._killed:
            self.execute_cycle()
            cycles += 1
            if max_cycles is not None and cycles >= max_cycles:
                break
            if not self._killed:
                self._stop_event.wait(timeout=self._current_interval)
                self._stop_event.clear()

    def to_dict(self) -> dict[str, Any]:
        return {
            "is_killed": self._killed,
            "is_paused": self._paused,
            "current_interval": round(self._current_interval, 2),
            "cycle_count": self._cycle_count,
            "stages": [s.name for s in self._stages],
            "config": {
                "base_interval": self._config.base_interval_seconds,
                "min_interval": self._config.min_interval_seconds,
                "max_interval": self._config.max_interval_seconds,
                "adaptive": self._config.adaptive_cadence,
            },
            "metrics": {
                "total_cycles": self._metrics.total_cycles,
                "total_stages_executed": self._metrics.total_stages_executed,
                "total_stages_failed": self._metrics.total_stages_failed,
                "avg_cycle_ms": round(self._metrics.avg_cycle_ms, 2),
                "consecutive_idle": self._metrics.consecutive_idle,
            },
        }
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd /opt/OS/.claude/worktrees/anti-divergence-gate && python3 -m pytest substrate/organism/tests/test_autonomous_tick.py -v`

Expected: All 12 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add substrate/organism/autonomous_tick.py substrate/organism/tests/test_autonomous_tick.py
git commit -m "feat(organism): autonomous tick engine — governed metabolism heartbeat"
```

---

## Task 3: Continuous Objective Queue

**Files:**
- Create: `substrate/organism/objective_queue.py`
- Create: `substrate/organism/tests/test_objective_queue.py`
- Modify: `substrate/canonical_types.py`

Depends on: Task 1 (EventSpine)

Persistent async objective intake with priority scheduling, dependency ordering, retry policy, and governance escalation.

- [ ] **Step 1: Register canonical types**

Add to `substrate/canonical_types.py`:

```python
# ── substrate/organism/objective_queue.py ─────────────────────────
"ObjectiveQueueStatus": ["substrate.organism.objective_queue"],
```

- [ ] **Step 2: Write failing tests**

Create `substrate/organism/tests/test_objective_queue.py`:

```python
"""Tests for the continuous objective queue."""

from __future__ import annotations

import sys

sys.path.insert(0, "/opt/OS")

from substrate.organism.event_spine import EventDomain, EventSpine
from substrate.organism.objective_queue import (
    ObjectiveQueueStatus,
    ObjectiveRequest,
    ObjectiveQueue,
)


def _make_queue() -> tuple[ObjectiveQueue, EventSpine]:
    spine = EventSpine()
    return ObjectiveQueue(spine=spine), spine


def test_enqueue_and_peek():
    q, _ = _make_queue()
    req_id = q.enqueue("Build feature X", "Implement the thing", priority=3)
    assert req_id != ""

    peeked = q.peek()
    assert peeked is not None
    assert peeked.title == "Build feature X"
    assert peeked.priority == 3
    assert peeked.status == ObjectiveQueueStatus.QUEUED


def test_priority_ordering():
    q, _ = _make_queue()
    q.enqueue("Low", "low pri", priority=10)
    q.enqueue("High", "high pri", priority=1)
    q.enqueue("Mid", "mid pri", priority=5)

    peeked = q.peek()
    assert peeked is not None
    assert peeked.title == "High"


def test_dequeue():
    q, _ = _make_queue()
    q.enqueue("Task A", "desc", priority=1)
    q.enqueue("Task B", "desc", priority=2)

    item = q.dequeue()
    assert item is not None
    assert item.title == "Task A"
    assert item.status == ObjectiveQueueStatus.EXECUTING

    next_item = q.peek()
    assert next_item is not None
    assert next_item.title == "Task B"


def test_complete():
    q, _ = _make_queue()
    req_id = q.enqueue("Task", "desc")
    q.dequeue()
    q.complete(req_id, result={"output": "done"})

    item = q.get(req_id)
    assert item is not None
    assert item.status == ObjectiveQueueStatus.COMPLETED


def test_fail_and_retry():
    q, _ = _make_queue()
    req_id = q.enqueue("Flaky task", "desc", max_retries=3)
    q.dequeue()
    q.fail(req_id, error="timeout")

    item = q.get(req_id)
    assert item is not None
    assert item.status == ObjectiveQueueStatus.QUEUED
    assert item.attempt_count == 1


def test_fail_exhausts_retries():
    q, _ = _make_queue()
    req_id = q.enqueue("Bad task", "desc", max_retries=1)

    q.dequeue()
    q.fail(req_id, error="err1")
    q.dequeue()
    q.fail(req_id, error="err2")

    item = q.get(req_id)
    assert item is not None
    assert item.status == ObjectiveQueueStatus.FAILED


def test_dependency_ordering():
    q, _ = _make_queue()
    id_a = q.enqueue("A", "first")
    id_b = q.enqueue("B", "depends on A", depends_on=[id_a])

    peeked = q.peek()
    assert peeked is not None
    assert peeked.title == "A"

    q.dequeue()
    q.complete(id_a)

    peeked = q.peek()
    assert peeked is not None
    assert peeked.title == "B"


def test_blocked_item_not_dequeued():
    q, _ = _make_queue()
    id_a = q.enqueue("A", "first")
    q.enqueue("B", "depends on A", depends_on=[id_a])

    item = q.dequeue()
    assert item is not None
    assert item.title == "A"

    next_item = q.dequeue()
    assert next_item is None


def test_emits_events():
    q, spine = _make_queue()
    q.enqueue("Task", "desc")
    q.dequeue()

    events = spine.recent(limit=50)
    enqueue_events = [e for e in events if e.event_type == "objective_enqueued"]
    dequeue_events = [e for e in events if e.event_type == "objective_dequeued"]
    assert len(enqueue_events) == 1
    assert len(dequeue_events) == 1


def test_cancel():
    q, _ = _make_queue()
    req_id = q.enqueue("Cancellable", "desc")
    q.cancel(req_id)

    item = q.get(req_id)
    assert item is not None
    assert item.status == ObjectiveQueueStatus.CANCELLED


def test_queue_depth():
    q, _ = _make_queue()
    q.enqueue("A", "desc")
    q.enqueue("B", "desc")
    assert q.depth() == 2

    q.dequeue()
    assert q.depth() == 1


def test_list_by_status():
    q, _ = _make_queue()
    q.enqueue("A", "desc")
    id_b = q.enqueue("B", "desc")
    q.dequeue()

    queued = q.list_by_status(ObjectiveQueueStatus.QUEUED)
    executing = q.list_by_status(ObjectiveQueueStatus.EXECUTING)
    assert len(queued) == 1
    assert len(executing) == 1
```

- [ ] **Step 3: Run tests to verify they fail**

Run: `cd /opt/OS/.claude/worktrees/anti-divergence-gate && python3 -m pytest substrate/organism/tests/test_objective_queue.py -v`

Expected: ImportError.

- [ ] **Step 4: Implement ObjectiveQueue**

Create `substrate/organism/objective_queue.py`:

```python
"""Continuous objective queue — persistent async objective intake.

Manages the lifecycle of objectives from intake to completion:
  QUEUED → EXECUTING → COMPLETED | FAILED | CANCELLED

Features:
  - Priority scheduling (lower number = higher priority)
  - Dependency ordering (blocked objectives wait)
  - Retry policy with configurable max_retries
  - Governance escalation via EventSpine
  - Lifecycle state machine with audit trail

UMH substrate subsystem. Instance-agnostic.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any
from uuid import uuid4

from substrate.organism.event_spine import EventDomain, EventSpine

logger = logging.getLogger(__name__)


class ObjectiveQueueStatus(str, Enum):
    QUEUED = "queued"
    BLOCKED = "blocked"
    EXECUTING = "executing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class ObjectiveRequest:
    request_id: str
    title: str
    description: str
    priority: int = 5
    status: ObjectiveQueueStatus = ObjectiveQueueStatus.QUEUED
    depends_on: list[str] = field(default_factory=list)
    max_retries: int = 0
    attempt_count: int = 0
    result: dict[str, Any] | None = None
    error: str | None = None
    created_at: float = field(default_factory=time.time)
    started_at: float | None = None
    completed_at: float | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "request_id": self.request_id,
            "title": self.title,
            "description": self.description,
            "priority": self.priority,
            "status": self.status.value,
            "depends_on": self.depends_on,
            "max_retries": self.max_retries,
            "attempt_count": self.attempt_count,
            "error": self.error,
            "created_at": self.created_at,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
        }


class ObjectiveQueue:
    """Persistent async objective intake queue.

    Objectives are priority-ordered (lower = higher priority).
    Dependency-blocked items are skipped during dequeue until
    their dependencies complete.
    """

    def __init__(self, spine: EventSpine) -> None:
        self._spine = spine
        self._items: dict[str, ObjectiveRequest] = {}

    def enqueue(
        self,
        title: str,
        description: str,
        priority: int = 5,
        depends_on: list[str] | None = None,
        max_retries: int = 0,
        metadata: dict[str, Any] | None = None,
    ) -> str:
        request_id = f"oq-{uuid4().hex[:8]}"
        item = ObjectiveRequest(
            request_id=request_id,
            title=title,
            description=description,
            priority=priority,
            depends_on=depends_on or [],
            max_retries=max_retries,
            metadata=metadata or {},
        )
        self._items[request_id] = item

        self._spine.emit(
            EventDomain.OBJECTIVE, "objective_enqueued", "objective_queue",
            {"request_id": request_id, "title": title, "priority": priority},
            correlation_id=request_id,
        )

        return request_id

    def peek(self) -> ObjectiveRequest | None:
        candidates = self._ready_candidates()
        return candidates[0] if candidates else None

    def dequeue(self) -> ObjectiveRequest | None:
        candidates = self._ready_candidates()
        if not candidates:
            return None

        item = candidates[0]
        item.status = ObjectiveQueueStatus.EXECUTING
        item.started_at = time.time()
        item.attempt_count += 1

        self._spine.emit(
            EventDomain.OBJECTIVE, "objective_dequeued", "objective_queue",
            {"request_id": item.request_id, "title": item.title,
             "attempt": item.attempt_count},
            correlation_id=item.request_id,
        )

        return item

    def complete(
        self,
        request_id: str,
        result: dict[str, Any] | None = None,
    ) -> None:
        item = self._items.get(request_id)
        if item is None:
            return

        item.status = ObjectiveQueueStatus.COMPLETED
        item.result = result
        item.completed_at = time.time()

        self._spine.emit(
            EventDomain.OBJECTIVE, "objective_completed", "objective_queue",
            {"request_id": request_id, "title": item.title},
            correlation_id=request_id,
        )

    def fail(self, request_id: str, error: str = "") -> None:
        item = self._items.get(request_id)
        if item is None:
            return

        item.error = error

        if item.attempt_count < item.max_retries:
            item.status = ObjectiveQueueStatus.QUEUED
            item.started_at = None
            self._spine.emit(
                EventDomain.OBJECTIVE, "objective_retrying", "objective_queue",
                {"request_id": request_id, "attempt": item.attempt_count,
                 "max_retries": item.max_retries, "error": error[:200]},
                correlation_id=request_id,
            )
        else:
            item.status = ObjectiveQueueStatus.FAILED
            item.completed_at = time.time()
            self._spine.emit(
                EventDomain.OBJECTIVE, "objective_failed", "objective_queue",
                {"request_id": request_id, "title": item.title,
                 "attempts": item.attempt_count, "error": error[:200]},
                correlation_id=request_id,
            )

    def cancel(self, request_id: str) -> None:
        item = self._items.get(request_id)
        if item is None:
            return
        item.status = ObjectiveQueueStatus.CANCELLED
        item.completed_at = time.time()

        self._spine.emit(
            EventDomain.OBJECTIVE, "objective_cancelled", "objective_queue",
            {"request_id": request_id, "title": item.title},
            correlation_id=request_id,
        )

    def get(self, request_id: str) -> ObjectiveRequest | None:
        return self._items.get(request_id)

    def depth(self) -> int:
        return sum(
            1 for item in self._items.values()
            if item.status in {ObjectiveQueueStatus.QUEUED, ObjectiveQueueStatus.BLOCKED}
        )

    def list_by_status(self, status: ObjectiveQueueStatus) -> list[ObjectiveRequest]:
        return [
            item for item in self._items.values()
            if item.status == status
        ]

    def _ready_candidates(self) -> list[ObjectiveRequest]:
        candidates = []
        for item in self._items.values():
            if item.status != ObjectiveQueueStatus.QUEUED:
                continue
            if self._is_blocked(item):
                continue
            candidates.append(item)

        candidates.sort(key=lambda x: (x.priority, x.created_at))
        return candidates

    def _is_blocked(self, item: ObjectiveRequest) -> bool:
        for dep_id in item.depends_on:
            dep = self._items.get(dep_id)
            if dep is None:
                continue
            if dep.status != ObjectiveQueueStatus.COMPLETED:
                return True
        return False
```

- [ ] **Step 5: Run tests**

Run: `cd /opt/OS/.claude/worktrees/anti-divergence-gate && python3 -m pytest substrate/organism/tests/test_objective_queue.py -v`

Expected: All 13 tests PASS.

- [ ] **Step 6: Commit**

```bash
git add substrate/organism/objective_queue.py substrate/organism/tests/test_objective_queue.py substrate/canonical_types.py
git commit -m "feat(organism): continuous objective queue — priority scheduling with lifecycle FSM"
```

---

## Task 4: Governed Runtime Allocation Loop

**Files:**
- Create: `substrate/organism/allocation_loop.py`
- Create: `substrate/organism/tests/test_allocation_loop.py`
- Modify: `substrate/canonical_types.py`

Depends on: Task 1, Task 2

Continuous leverage allocator that monitors runtime load, rebalances execution, shifts workloads dynamically, and throttles recursion under pressure.

- [ ] **Step 1: Register canonical types**

Add to `substrate/canonical_types.py`:

```python
# ── substrate/organism/allocation_loop.py ─────────────────────────
"AllocationStrategy": ["substrate.organism.allocation_loop"],
```

- [ ] **Step 2: Write failing tests**

Create `substrate/organism/tests/test_allocation_loop.py`:

```python
"""Tests for the governed runtime allocation loop."""

from __future__ import annotations

import sys

sys.path.insert(0, "/opt/OS")

from substrate.organism.allocation_loop import (
    AllocationLoop,
    AllocationStrategy,
    AllocationDecision,
)
from substrate.organism.event_spine import EventDomain, EventSpine
from substrate.organism.runtime_graph import (
    AvailabilityStatus,
    CostProfile,
    RuntimeCapability,
    RuntimeClass,
    RuntimeGraph,
)
from substrate.organism.runtime_supervisor import RuntimeSupervisor
from substrate.organism.execution_economy import ExecutionEconomy
from substrate.organism.recursion_governance import RecursionGovernor


def _make_graph() -> RuntimeGraph:
    graph = RuntimeGraph()
    graph.register(
        "cc-opus", RuntimeClass.CLOUD_AI,
        frozenset({RuntimeCapability.CODE_WRITE, RuntimeCapability.REASON}),
        cost=CostProfile(cost_per_1k_input=0.0, is_subscription=True),
    )
    graph.register(
        "gemini-flash", RuntimeClass.CLOUD_AI,
        frozenset({RuntimeCapability.REASON, RuntimeCapability.RESEARCH}),
        cost=CostProfile(cost_per_1k_input=0.0005),
    )
    graph.register(
        "ollama-local", RuntimeClass.LOCAL_AI,
        frozenset({RuntimeCapability.REASON, RuntimeCapability.FAST_RESPONSE}),
        cost=CostProfile(cost_per_1k_input=0.0, is_subscription=True),
    )
    return graph


def _make_loop() -> tuple[AllocationLoop, EventSpine]:
    spine = EventSpine()
    graph = _make_graph()
    supervisor = RuntimeSupervisor(graph)
    economy = ExecutionEconomy()
    governor = RecursionGovernor()

    loop = AllocationLoop(
        spine=spine,
        graph=graph,
        supervisor=supervisor,
        economy=economy,
        governor=governor,
    )
    return loop, spine


def test_allocation_cycle():
    loop, spine = _make_loop()
    decisions = loop.allocation_cycle()
    assert isinstance(decisions, list)


def test_detect_degraded_runtime():
    loop, _ = _make_loop()
    loop._graph.update_status("gemini-flash", AvailabilityStatus.DEGRADED)

    decisions = loop.allocation_cycle()
    degraded = [d for d in decisions if d.action == "flag_degraded"]
    assert len(degraded) >= 1


def test_throttle_under_governor_kill():
    loop, _ = _make_loop()
    loop._governor.kill()

    decisions = loop.allocation_cycle()
    throttled = [d for d in decisions if d.action == "throttled"]
    assert len(throttled) >= 1


def test_emits_allocation_events():
    loop, spine = _make_loop()
    loop.allocation_cycle()

    events = spine.recent(limit=50)
    alloc_events = [e for e in events if e.domain == EventDomain.LEVERAGE]
    assert len(alloc_events) >= 1


def test_cost_spike_detection():
    loop, _ = _make_loop()
    loop._graph.get("gemini-flash").cost = CostProfile(
        cost_per_1k_input=0.05, cost_per_1k_output=0.15,
    )
    loop._last_costs["gemini-flash"] = 0.001

    decisions = loop.allocation_cycle()
    spikes = [d for d in decisions if d.action == "cost_spike"]
    assert len(spikes) >= 1


def test_to_dict():
    loop, _ = _make_loop()
    loop.allocation_cycle()
    d = loop.to_dict()
    assert "cycle_count" in d
    assert "decisions" in d
    assert "strategy" in d
```

- [ ] **Step 3: Run tests to verify they fail**

Run: `cd /opt/OS/.claude/worktrees/anti-divergence-gate && python3 -m pytest substrate/organism/tests/test_allocation_loop.py -v`

Expected: ImportError.

- [ ] **Step 4: Implement AllocationLoop**

Create `substrate/organism/allocation_loop.py`:

```python
"""Governed runtime allocation loop — continuous leverage allocator.

Monitors runtime load, rebalances execution, shifts workloads dynamically,
optimizes latency/cost/reliability, and throttles recursion under pressure.

Integrates:
  - RuntimeGraph: topology and capability awareness
  - RuntimeSupervisor: health state
  - ExecutionEconomy: cost/performance data
  - RecursionGovernor: throttle enforcement

Each allocation cycle:
  1. Check governor state (throttle if killed)
  2. Scan runtime health
  3. Detect cost spikes
  4. Identify degraded/dead runtimes
  5. Emit allocation decisions as events

UMH substrate subsystem. Instance-agnostic.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from substrate.organism.event_spine import EventDomain, EventPriority, EventSpine
from substrate.organism.execution_economy import ExecutionEconomy
from substrate.organism.recursion_governance import RecursionGovernor
from substrate.organism.runtime_graph import AvailabilityStatus, RuntimeGraph
from substrate.organism.runtime_supervisor import RuntimeSupervisor, SupervisedHealth

logger = logging.getLogger(__name__)


class AllocationStrategy(str, Enum):
    COST_OPTIMIZED = "cost_optimized"
    RELIABILITY_FIRST = "reliability_first"
    LATENCY_FIRST = "latency_first"
    BALANCED = "balanced"


@dataclass
class AllocationDecision:
    runtime_id: str
    action: str
    reason: str
    timestamp: float = field(default_factory=time.time)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "runtime_id": self.runtime_id,
            "action": self.action,
            "reason": self.reason,
            "timestamp": self.timestamp,
            "metadata": self.metadata,
        }


class AllocationLoop:
    """Continuous governed runtime allocation.

    Called each tick cycle to evaluate runtime topology and
    produce allocation decisions.
    """

    COST_SPIKE_THRESHOLD = 5.0

    def __init__(
        self,
        spine: EventSpine,
        graph: RuntimeGraph,
        supervisor: RuntimeSupervisor,
        economy: ExecutionEconomy,
        governor: RecursionGovernor,
        strategy: AllocationStrategy = AllocationStrategy.BALANCED,
    ) -> None:
        self._spine = spine
        self._graph = graph
        self._supervisor = supervisor
        self._economy = economy
        self._governor = governor
        self._strategy = strategy
        self._cycle_count = 0
        self._last_costs: dict[str, float] = {}
        self._recent_decisions: list[AllocationDecision] = []

    def allocation_cycle(self) -> list[AllocationDecision]:
        self._cycle_count += 1
        decisions: list[AllocationDecision] = []

        if self._governor.is_killed:
            decisions.append(AllocationDecision(
                runtime_id="*",
                action="throttled",
                reason="recursion governor kill switch active",
            ))
            self._emit_decisions(decisions)
            return decisions

        for node in self._graph.all_nodes():
            if node.status == AvailabilityStatus.DEGRADED:
                decisions.append(AllocationDecision(
                    runtime_id=node.runtime_id,
                    action="flag_degraded",
                    reason=f"runtime {node.runtime_id} is degraded",
                    metadata={"status": node.status.value},
                ))

            if node.status == AvailabilityStatus.UNAVAILABLE:
                decisions.append(AllocationDecision(
                    runtime_id=node.runtime_id,
                    action="flag_unavailable",
                    reason=f"runtime {node.runtime_id} is unavailable",
                ))

            current_cost = node.cost.effective_cost
            last_cost = self._last_costs.get(node.runtime_id, current_cost)
            if last_cost > 0 and current_cost / last_cost > self.COST_SPIKE_THRESHOLD:
                decisions.append(AllocationDecision(
                    runtime_id=node.runtime_id,
                    action="cost_spike",
                    reason=f"cost jumped from {last_cost:.4f} to {current_cost:.4f}",
                    metadata={"old_cost": last_cost, "new_cost": current_cost},
                ))
            self._last_costs[node.runtime_id] = current_cost

        self._recent_decisions = decisions
        self._emit_decisions(decisions)
        return decisions

    def _emit_decisions(self, decisions: list[AllocationDecision]) -> None:
        self._spine.emit(
            EventDomain.LEVERAGE,
            "allocation_cycle_completed",
            "allocation_loop",
            {
                "cycle": self._cycle_count,
                "decision_count": len(decisions),
                "decisions": [d.to_dict() for d in decisions[:20]],
                "strategy": self._strategy.value,
            },
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "cycle_count": self._cycle_count,
            "strategy": self._strategy.value,
            "decisions": [d.to_dict() for d in self._recent_decisions],
            "runtime_count": self._graph.node_count,
        }
```

- [ ] **Step 5: Run tests**

Run: `cd /opt/OS/.claude/worktrees/anti-divergence-gate && python3 -m pytest substrate/organism/tests/test_allocation_loop.py -v`

Expected: All 6 tests PASS.

- [ ] **Step 6: Commit**

```bash
git add substrate/organism/allocation_loop.py substrate/organism/tests/test_allocation_loop.py substrate/canonical_types.py
git commit -m "feat(organism): governed runtime allocation loop — continuous leverage optimization"
```

---

## Task 5: Async Coordinator Execution

**Files:**
- Create: `substrate/organism/async_coordinator.py`
- Create: `substrate/organism/tests/test_async_coordinator.py`

Depends on: Task 1, Task 3

Wraps the synchronous OrganismCoordinator in an async interface with submit, progress tracking, event-driven completion, cancellation, and dependency wakeups.

- [ ] **Step 1: Write failing tests**

Create `substrate/organism/tests/test_async_coordinator.py`:

```python
"""Tests for async coordinator execution."""

from __future__ import annotations

import sys

sys.path.insert(0, "/opt/OS")

from substrate.organism.async_coordinator import (
    AsyncCoordinator,
    AsyncObjective,
    AsyncObjectiveStatus,
)
from substrate.organism.event_spine import EventDomain, EventSpine
from substrate.organism.coordinator import OrganismCoordinator
from substrate.organism.runtime_graph import (
    RuntimeCapability,
    RuntimeClass,
    RuntimeGraph,
)


def _make_coordinator() -> tuple[AsyncCoordinator, EventSpine]:
    spine = EventSpine()
    graph = RuntimeGraph()
    graph.register(
        "test-rt", RuntimeClass.LOCAL_AI,
        frozenset({RuntimeCapability.REASON}),
    )
    coordinator = OrganismCoordinator(graph)
    return AsyncCoordinator(coordinator=coordinator, spine=spine), spine


def test_submit_objective():
    ac, _ = _make_coordinator()
    obj_id = ac.submit("Build X", "description of X")
    assert obj_id != ""

    obj = ac.get(obj_id)
    assert obj is not None
    assert obj.title == "Build X"
    assert obj.status == AsyncObjectiveStatus.SUBMITTED


def test_advance_processes_submitted():
    ac, _ = _make_coordinator()
    obj_id = ac.submit("Task", "desc")
    advanced = ac.advance()

    assert len(advanced) >= 1
    obj = ac.get(obj_id)
    assert obj is not None
    assert obj.status in {
        AsyncObjectiveStatus.DECOMPOSED,
        AsyncObjectiveStatus.EXECUTING,
        AsyncObjectiveStatus.COMPLETED,
    }


def test_cancel_objective():
    ac, _ = _make_coordinator()
    obj_id = ac.submit("Cancelme", "desc")
    ac.cancel(obj_id)

    obj = ac.get(obj_id)
    assert obj is not None
    assert obj.status == AsyncObjectiveStatus.CANCELLED


def test_progress_tracking():
    ac, _ = _make_coordinator()
    obj_id = ac.submit("Track me", "desc")
    ac.advance()

    progress = ac.progress(obj_id)
    assert progress is not None
    assert "completion_rate" in progress
    assert "status" in progress


def test_emits_lifecycle_events():
    ac, spine = _make_coordinator()
    obj_id = ac.submit("Evented", "desc")
    ac.advance()

    events = spine.recent(limit=50)
    submit_events = [e for e in events if e.event_type == "async_objective_submitted"]
    assert len(submit_events) == 1
    assert submit_events[0].correlation_id == obj_id


def test_list_active():
    ac, _ = _make_coordinator()
    ac.submit("A", "desc")
    ac.submit("B", "desc")

    active = ac.list_active()
    assert len(active) == 2


def test_completed_not_in_active():
    ac, _ = _make_coordinator()
    obj_id = ac.submit("Quick", "desc")
    ac.advance()

    obj = ac.get(obj_id)
    if obj and obj.status == AsyncObjectiveStatus.COMPLETED:
        active = ac.list_active()
        assert all(a.objective_id != obj_id for a in active)


def test_dag_state():
    ac, _ = _make_coordinator()
    obj_id = ac.submit("DAG task", "complex work", work_units=[
        {"title": "Step 1", "description": "first"},
        {"title": "Step 2", "description": "second", "blocked_by": [0]},
    ])

    dag = ac.dag_state(obj_id)
    assert dag is not None
    assert "work_units" in dag
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd /opt/OS/.claude/worktrees/anti-divergence-gate && python3 -m pytest substrate/organism/tests/test_async_coordinator.py -v`

Expected: ImportError.

- [ ] **Step 3: Implement AsyncCoordinator**

Create `substrate/organism/async_coordinator.py`:

```python
"""Async coordinator execution — event-driven objective lifecycle.

Wraps the synchronous OrganismCoordinator with:
  - Async submit (non-blocking objective intake)
  - Progress tracking
  - Event-driven completion via EventSpine
  - Cancellation
  - Dependency wakeups (advance unblocks downstream)

The advance() method is called from the autonomous tick engine,
progressing all active objectives one step.

UMH substrate subsystem. Instance-agnostic.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from substrate.organism.coordinator import (
    ObjectiveStatus,
    OrganismCoordinator,
)
from substrate.organism.event_spine import EventDomain, EventSpine

logger = logging.getLogger(__name__)


class AsyncObjectiveStatus(str, Enum):
    SUBMITTED = "submitted"
    DECOMPOSED = "decomposed"
    EXECUTING = "executing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class AsyncObjective:
    objective_id: str
    title: str
    description: str
    status: AsyncObjectiveStatus = AsyncObjectiveStatus.SUBMITTED
    coordinator_objective_id: str | None = None
    work_units_spec: list[dict[str, Any]] | None = None
    submitted_at: float = field(default_factory=time.time)
    completed_at: float | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "objective_id": self.objective_id,
            "title": self.title,
            "description": self.description,
            "status": self.status.value,
            "coordinator_objective_id": self.coordinator_objective_id,
            "submitted_at": self.submitted_at,
            "completed_at": self.completed_at,
        }


class AsyncCoordinator:
    """Async wrapper around OrganismCoordinator.

    Objectives are submitted and tracked independently.
    advance() is called each tick to progress them.
    """

    def __init__(
        self,
        coordinator: OrganismCoordinator,
        spine: EventSpine,
    ) -> None:
        self._coordinator = coordinator
        self._spine = spine
        self._objectives: dict[str, AsyncObjective] = {}

    def submit(
        self,
        title: str,
        description: str,
        work_units: list[dict[str, Any]] | None = None,
    ) -> str:
        from uuid import uuid4
        obj_id = f"async-{uuid4().hex[:8]}"
        obj = AsyncObjective(
            objective_id=obj_id,
            title=title,
            description=description,
            work_units_spec=work_units,
        )
        self._objectives[obj_id] = obj

        self._spine.emit(
            EventDomain.OBJECTIVE,
            "async_objective_submitted",
            "async_coordinator",
            {"objective_id": obj_id, "title": title},
            correlation_id=obj_id,
        )

        return obj_id

    def advance(self) -> list[str]:
        advanced = []
        for obj in list(self._objectives.values()):
            if obj.status == AsyncObjectiveStatus.CANCELLED:
                continue

            if obj.status == AsyncObjectiveStatus.SUBMITTED:
                self._decompose(obj)
                advanced.append(obj.objective_id)

            elif obj.status in {
                AsyncObjectiveStatus.DECOMPOSED,
                AsyncObjectiveStatus.EXECUTING,
            }:
                self._execute_step(obj)
                advanced.append(obj.objective_id)

        return advanced

    def cancel(self, objective_id: str) -> None:
        obj = self._objectives.get(objective_id)
        if obj is None:
            return
        obj.status = AsyncObjectiveStatus.CANCELLED
        obj.completed_at = time.time()

        self._spine.emit(
            EventDomain.OBJECTIVE,
            "async_objective_cancelled",
            "async_coordinator",
            {"objective_id": objective_id},
            correlation_id=objective_id,
        )

    def get(self, objective_id: str) -> AsyncObjective | None:
        return self._objectives.get(objective_id)

    def progress(self, objective_id: str) -> dict[str, Any] | None:
        obj = self._objectives.get(objective_id)
        if obj is None:
            return None

        result: dict[str, Any] = {
            "objective_id": objective_id,
            "status": obj.status.value,
            "completion_rate": 0.0,
        }

        if obj.coordinator_objective_id:
            coord_obj = self._coordinator.get_objective(obj.coordinator_objective_id)
            if coord_obj:
                result["completion_rate"] = coord_obj.completion_rate
                result["work_units_total"] = len(coord_obj.work_units)
                result["work_units_completed"] = sum(
                    1 for wu in coord_obj.work_units
                    if wu.status.value == "completed"
                )

        return result

    def list_active(self) -> list[AsyncObjective]:
        return [
            obj for obj in self._objectives.values()
            if obj.status in {
                AsyncObjectiveStatus.SUBMITTED,
                AsyncObjectiveStatus.DECOMPOSED,
                AsyncObjectiveStatus.EXECUTING,
            }
        ]

    def dag_state(self, objective_id: str) -> dict[str, Any] | None:
        obj = self._objectives.get(objective_id)
        if obj is None or obj.coordinator_objective_id is None:
            return None

        coord_obj = self._coordinator.get_objective(obj.coordinator_objective_id)
        if coord_obj is None:
            return None

        return {
            "objective_id": objective_id,
            "coordinator_id": obj.coordinator_objective_id,
            "status": coord_obj.status.value,
            "completion_rate": coord_obj.completion_rate,
            "work_units": [wu.to_dict() for wu in coord_obj.work_units],
        }

    def _decompose(self, obj: AsyncObjective) -> None:
        try:
            coord_obj = self._coordinator.decompose(
                obj.title, obj.description, obj.work_units_spec,
            )
            obj.coordinator_objective_id = coord_obj.id
            obj.status = AsyncObjectiveStatus.DECOMPOSED

            self._spine.emit(
                EventDomain.OBJECTIVE,
                "async_objective_decomposed",
                "async_coordinator",
                {
                    "objective_id": obj.objective_id,
                    "coordinator_id": coord_obj.id,
                    "work_units": len(coord_obj.work_units),
                },
                correlation_id=obj.objective_id,
            )
        except Exception as exc:
            logger.warning("decompose failed for %s: %s", obj.objective_id, exc)
            obj.status = AsyncObjectiveStatus.FAILED
            obj.completed_at = time.time()

    def _execute_step(self, obj: AsyncObjective) -> None:
        if obj.coordinator_objective_id is None:
            return

        coord_obj = self._coordinator.get_objective(obj.coordinator_objective_id)
        if coord_obj is None:
            obj.status = AsyncObjectiveStatus.FAILED
            obj.completed_at = time.time()
            return

        if coord_obj.is_complete:
            obj.status = AsyncObjectiveStatus.COMPLETED
            obj.completed_at = time.time()
            self._spine.emit(
                EventDomain.OBJECTIVE,
                "async_objective_completed",
                "async_coordinator",
                {
                    "objective_id": obj.objective_id,
                    "completion_rate": coord_obj.completion_rate,
                },
                correlation_id=obj.objective_id,
            )
            return

        if coord_obj.has_failures and coord_obj.completion_rate == 0:
            obj.status = AsyncObjectiveStatus.FAILED
            obj.completed_at = time.time()
            return

        obj.status = AsyncObjectiveStatus.EXECUTING

        try:
            self._coordinator.execute_ready(coord_obj.id)
        except Exception as exc:
            logger.warning("execute_step failed for %s: %s", obj.objective_id, exc)
```

- [ ] **Step 4: Run tests**

Run: `cd /opt/OS/.claude/worktrees/anti-divergence-gate && python3 -m pytest substrate/organism/tests/test_async_coordinator.py -v`

Expected: All 8 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add substrate/organism/async_coordinator.py substrate/organism/tests/test_async_coordinator.py
git commit -m "feat(organism): async coordinator execution — event-driven objective lifecycle"
```

---

## Task 6: Runtime Event Bus Wiring

**Files:**
- Modify: `substrate/organism/advisor.py`
- Modify: `substrate/organism/runtime_supervisor.py`
- Modify: `substrate/organism/runtime_graph.py`
- Create: `substrate/organism/tests/test_runtime_events.py`

Depends on: Task 1

Wire all existing subsystems to emit events through the EventSpine instead of only logging or returning dicts.

- [ ] **Step 1: Write failing tests**

Create `substrate/organism/tests/test_runtime_events.py`:

```python
"""Tests for runtime event bus wiring."""

from __future__ import annotations

import sys

sys.path.insert(0, "/opt/OS")

from substrate.organism.event_spine import EventDomain, EventSpine
from substrate.organism.runtime_graph import (
    AvailabilityStatus,
    RuntimeCapability,
    RuntimeClass,
    RuntimeGraph,
)
from substrate.organism.runtime_supervisor import RuntimeSupervisor


def test_graph_emits_register_event():
    spine = EventSpine()
    graph = RuntimeGraph(event_spine=spine)
    graph.register(
        "test-rt", RuntimeClass.LOCAL_AI,
        frozenset({RuntimeCapability.REASON}),
    )

    events = spine.recent(limit=50)
    reg_events = [e for e in events if e.event_type == "runtime_registered"]
    assert len(reg_events) == 1
    assert reg_events[0].domain == EventDomain.RUNTIME
    assert reg_events[0].data["runtime_id"] == "test-rt"


def test_graph_emits_status_change_event():
    spine = EventSpine()
    graph = RuntimeGraph(event_spine=spine)
    graph.register("rt1", RuntimeClass.LOCAL_AI, frozenset({RuntimeCapability.REASON}))
    graph.update_status("rt1", AvailabilityStatus.DEGRADED)

    events = spine.recent(limit=50)
    status_events = [e for e in events if e.event_type == "runtime_status_changed"]
    assert len(status_events) == 1
    assert status_events[0].data["new_status"] == "degraded"


def test_graph_emits_failure_event():
    spine = EventSpine()
    graph = RuntimeGraph(event_spine=spine)
    graph.register("rt1", RuntimeClass.LOCAL_AI, frozenset({RuntimeCapability.REASON}))
    graph.record_failure("rt1")

    events = spine.recent(limit=50)
    fail_events = [e for e in events if e.event_type == "runtime_failure_recorded"]
    assert len(fail_events) == 1


def test_supervisor_emits_crash_event():
    spine = EventSpine()
    graph = RuntimeGraph(event_spine=spine)
    graph.register("rt1", RuntimeClass.LOCAL_AI, frozenset({RuntimeCapability.REASON}))
    supervisor = RuntimeSupervisor(graph, event_spine=spine)
    supervisor.supervise("rt1")
    supervisor.record_crash("rt1", error="segfault")

    events = spine.recent(limit=50)
    crash_events = [e for e in events if e.event_type == "runtime_crashed"]
    assert len(crash_events) == 1
    assert crash_events[0].domain == EventDomain.SUPERVISOR
    assert crash_events[0].data["error"] == "segfault"


def test_supervisor_emits_recovery_event():
    spine = EventSpine()
    graph = RuntimeGraph(event_spine=spine)
    graph.register("rt1", RuntimeClass.LOCAL_AI, frozenset({RuntimeCapability.REASON}))
    supervisor = RuntimeSupervisor(graph, event_spine=spine)
    supervisor.supervise("rt1")
    supervisor.record_recovery_success("rt1", latency_ms=50)

    events = spine.recent(limit=50)
    recovery_events = [e for e in events if e.event_type == "runtime_recovered"]
    assert len(recovery_events) == 1


def test_graph_works_without_spine():
    graph = RuntimeGraph()
    graph.register("rt1", RuntimeClass.LOCAL_AI, frozenset({RuntimeCapability.REASON}))
    graph.update_status("rt1", AvailabilityStatus.DEGRADED)
    graph.record_failure("rt1")
    # no exceptions — spine is optional
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd /opt/OS/.claude/worktrees/anti-divergence-gate && python3 -m pytest substrate/organism/tests/test_runtime_events.py -v`

Expected: TypeError — `event_spine` parameter not accepted.

- [ ] **Step 3: Wire EventSpine into RuntimeGraph**

Modify `substrate/organism/runtime_graph.py`:

Add `event_spine` optional parameter to `RuntimeGraph.__init__()`. Add `_emit()` helper. Emit events on `register()`, `update_status()`, `record_success()`, `record_failure()`.

The key changes (applied to the existing file):

In `RuntimeGraph.__init__()`, add:
```python
def __init__(self, event_spine: Any | None = None) -> None:
    self._nodes: dict[str, RuntimeNode] = {}
    self._event_spine = event_spine
```

Add helper method:
```python
def _emit(self, event_type: str, data: dict[str, Any]) -> None:
    if self._event_spine is None:
        return
    from substrate.organism.event_spine import EventDomain
    self._event_spine.emit(EventDomain.RUNTIME, event_type, "runtime_graph", data)
```

In `register()`, after adding the node:
```python
self._emit("runtime_registered", {"runtime_id": runtime_id, "class": runtime_class.value})
```

In `update_status()`, after setting status:
```python
self._emit("runtime_status_changed", {"runtime_id": runtime_id, "new_status": status.value})
```

In `record_failure()`:
```python
self._emit("runtime_failure_recorded", {"runtime_id": runtime_id})
```

In `record_success()`:
```python
self._emit("runtime_success_recorded", {"runtime_id": runtime_id, "latency_ms": latency_ms})
```

- [ ] **Step 4: Wire EventSpine into RuntimeSupervisor**

Modify `substrate/organism/runtime_supervisor.py`:

Add `event_spine` optional parameter to `RuntimeSupervisor.__init__()`. Emit events on `record_crash()`, `record_recovery_success()`, `record_recovery_failure()`.

In `__init__()`:
```python
def __init__(self, graph: RuntimeGraph, state_dir: str | None = None, event_spine: Any | None = None) -> None:
    # ... existing code ...
    self._event_spine = event_spine
```

Add helper:
```python
def _emit(self, event_type: str, data: dict[str, Any]) -> None:
    if self._event_spine is None:
        return
    from substrate.organism.event_spine import EventDomain
    self._event_spine.emit(EventDomain.SUPERVISOR, event_type, "runtime_supervisor", data)
```

In `record_crash()`:
```python
self._emit("runtime_crashed", {"runtime_id": runtime_id, "error": error or ""})
```

In `record_recovery_success()`:
```python
self._emit("runtime_recovered", {"runtime_id": runtime_id, "latency_ms": latency_ms or 0})
```

In `record_recovery_failure()`:
```python
self._emit("runtime_recovery_failed", {"runtime_id": runtime_id, "error": error or ""})
```

- [ ] **Step 5: Run tests**

Run: `cd /opt/OS/.claude/worktrees/anti-divergence-gate && python3 -m pytest substrate/organism/tests/test_runtime_events.py -v`

Expected: All 6 tests PASS.

- [ ] **Step 6: Run all existing organism tests to verify no regressions**

Run: `cd /opt/OS/.claude/worktrees/anti-divergence-gate && python3 -m pytest substrate/organism/tests/ -v --tb=short`

Expected: All existing tests still PASS (spine parameter is optional, backward-compatible).

- [ ] **Step 7: Commit**

```bash
git add substrate/organism/runtime_graph.py substrate/organism/runtime_supervisor.py substrate/organism/tests/test_runtime_events.py
git commit -m "feat(organism): runtime event bus — wire subsystems to EventSpine"
```

---

## Task 7: Continuous Leverage Rebalancing

**Files:**
- Modify: `substrate/organism/leverage_assimilation.py`
- Create: `substrate/organism/tests/test_leverage_rebalance.py`

Depends on: Task 1, Task 4

Extend LeverageAssimilator with continuous evaluation, dynamic scoring adjustment, and degraded primitive detection.

- [ ] **Step 1: Write failing tests**

Create `substrate/organism/tests/test_leverage_rebalance.py`:

```python
"""Tests for continuous leverage rebalancing."""

from __future__ import annotations

import sys

sys.path.insert(0, "/opt/OS")

from substrate.organism.event_spine import EventDomain, EventSpine
from substrate.organism.leverage_assimilation import LeverageAssimilator


def test_rebalance_cycle():
    spine = EventSpine()
    assim = LeverageAssimilator(event_spine=spine)
    assim.ingest("Test Framework", content="pattern library for testing")
    assim.full_pipeline("Test Framework")

    result = assim.rebalance_cycle()
    assert isinstance(result, dict)
    assert "artifacts_evaluated" in result


def test_rebalance_emits_events():
    spine = EventSpine()
    assim = LeverageAssimilator(event_spine=spine)
    assim.ingest("Test", content="tool")
    assim.full_pipeline("Test")
    assim.rebalance_cycle()

    events = spine.recent(limit=50)
    rebalance_events = [e for e in events if e.event_type == "leverage_rebalanced"]
    assert len(rebalance_events) == 1
    assert rebalance_events[0].domain == EventDomain.LEVERAGE


def test_detect_degraded_primitives():
    spine = EventSpine()
    assim = LeverageAssimilator(event_spine=spine)
    assim.ingest("Flaky Tool", content="unreliable adapter")
    assim.full_pipeline("Flaky Tool")

    degraded = assim.detect_degraded()
    assert isinstance(degraded, list)


def test_works_without_spine():
    assim = LeverageAssimilator()
    assim.ingest("NoSpine", content="test")
    assim.full_pipeline("NoSpine")
    result = assim.rebalance_cycle()
    assert "artifacts_evaluated" in result
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd /opt/OS/.claude/worktrees/anti-divergence-gate && python3 -m pytest substrate/organism/tests/test_leverage_rebalance.py -v`

Expected: TypeError — `event_spine` not accepted.

- [ ] **Step 3: Add rebalancing to LeverageAssimilator**

Modify `substrate/organism/leverage_assimilation.py`:

Add `event_spine` optional parameter to `__init__()`. Add `rebalance_cycle()` and `detect_degraded()` methods.

In `__init__()`, add:
```python
self._event_spine = event_spine
```

Add helper:
```python
def _emit(self, event_type: str, data: dict[str, Any]) -> None:
    if self._event_spine is None:
        return
    from substrate.organism.event_spine import EventDomain
    self._event_spine.emit(EventDomain.LEVERAGE, event_type, "leverage_assimilator", data)
```

Add methods:
```python
def rebalance_cycle(self) -> dict[str, Any]:
    """Continuous leverage evaluation cycle.

    Re-scores all artifacts based on current state,
    detects degraded primitives, and emits rebalancing events.
    """
    evaluated = 0
    adjustments = []

    for artifact in self._artifacts.values():
        if artifact.status.value not in ("extracted", "mapped"):
            continue
        evaluated += 1
        old_scores = [p.leverage.composite for p in artifact.primitives]
        self.score_leverage(artifact.id)
        new_scores = [p.leverage.composite for p in artifact.primitives]

        for i, (old, new) in enumerate(zip(old_scores, new_scores)):
            if abs(old - new) > 0.1:
                adjustments.append({
                    "artifact": artifact.name,
                    "primitive_index": i,
                    "old_score": round(old, 3),
                    "new_score": round(new, 3),
                })

    result = {
        "artifacts_evaluated": evaluated,
        "adjustments": adjustments,
    }

    self._emit("leverage_rebalanced", result)
    return result

def detect_degraded(self) -> list[dict[str, Any]]:
    """Detect primitives with declining leverage scores."""
    degraded = []
    for artifact in self._artifacts.values():
        for prim in artifact.primitives:
            if prim.leverage.composite < 0.3:
                degraded.append({
                    "artifact": artifact.name,
                    "primitive": prim.name,
                    "score": round(prim.leverage.composite, 3),
                })
    if degraded:
        self._emit("leverage_degraded_detected", {
            "count": len(degraded),
            "primitives": degraded[:10],
        })
    return degraded
```

- [ ] **Step 4: Run tests**

Run: `cd /opt/OS/.claude/worktrees/anti-divergence-gate && python3 -m pytest substrate/organism/tests/test_leverage_rebalance.py -v`

Expected: All 4 tests PASS.

- [ ] **Step 5: Run existing leverage tests for regression check**

Run: `cd /opt/OS/.claude/worktrees/anti-divergence-gate && python3 -m pytest substrate/organism/tests/test_leverage_assimilation.py -v`

Expected: All existing tests still PASS.

- [ ] **Step 6: Commit**

```bash
git add substrate/organism/leverage_assimilation.py substrate/organism/tests/test_leverage_rebalance.py
git commit -m "feat(organism): continuous leverage rebalancing — adaptive scoring and degradation detection"
```

---

## Task 8: Projection-Agnostic Organism State Port

**Files:**
- Create: `substrate/organism/projection_port.py`
- Create: `substrate/organism/tests/test_projection_port.py`

Depends on: Task 1

Abstract port that any projection (UMH cockpit, EOS, CreatorOS, LyfeOS) can register against to receive organism state without coupling.

- [ ] **Step 1: Write failing tests**

Create `substrate/organism/tests/test_projection_port.py`:

```python
"""Tests for projection-agnostic organism state port."""

from __future__ import annotations

import sys

sys.path.insert(0, "/opt/OS")

from substrate.organism.projection_port import (
    OrganismStatePort,
    ProjectionSubscriber,
    StateSlice,
)
from substrate.organism.event_spine import EventDomain, EventSpine, OrganismEvent


class MockProjection(ProjectionSubscriber):
    def __init__(self, projection_id: str, slices: set[StateSlice] | None = None):
        self._id = projection_id
        self._slices = slices
        self.received: list[dict] = []

    @property
    def subscriber_id(self) -> str:
        return self._id

    def accepts_slices(self) -> set[StateSlice] | None:
        return self._slices

    def on_state_update(self, slice_type: StateSlice, data: dict) -> None:
        self.received.append({"slice": slice_type, "data": data})


def test_register_projection():
    port = OrganismStatePort()
    proj = MockProjection("cockpit")
    port.register(proj)
    assert "cockpit" in port.registered_projections()


def test_unregister_projection():
    port = OrganismStatePort()
    proj = MockProjection("cockpit")
    port.register(proj)
    port.unregister("cockpit")
    assert "cockpit" not in port.registered_projections()


def test_broadcast_to_all():
    port = OrganismStatePort()
    p1 = MockProjection("cockpit")
    p2 = MockProjection("eos")
    port.register(p1)
    port.register(p2)

    port.broadcast(StateSlice.RUNTIMES, {"count": 3})
    assert len(p1.received) == 1
    assert len(p2.received) == 1


def test_filtered_broadcast():
    port = OrganismStatePort()
    runtime_only = MockProjection("runtime-watcher", slices={StateSlice.RUNTIMES})
    all_slices = MockProjection("full-view")
    port.register(runtime_only)
    port.register(all_slices)

    port.broadcast(StateSlice.RUNTIMES, {"count": 3})
    port.broadcast(StateSlice.OBJECTIVES, {"active": 2})

    assert len(runtime_only.received) == 1
    assert len(all_slices.received) == 2


def test_subscriber_error_isolation():
    port = OrganismStatePort()

    class BadProjection(ProjectionSubscriber):
        @property
        def subscriber_id(self) -> str:
            return "bad"
        def accepts_slices(self):
            return None
        def on_state_update(self, slice_type, data):
            raise RuntimeError("boom")

    good = MockProjection("good")
    port.register(BadProjection())
    port.register(good)

    port.broadcast(StateSlice.RUNTIMES, {"x": 1})
    assert len(good.received) == 1


def test_spine_bridge():
    spine = EventSpine()
    port = OrganismStatePort()
    proj = MockProjection("cockpit")
    port.register(proj)

    port.bridge_from_spine(spine, {
        EventDomain.RUNTIME: StateSlice.RUNTIMES,
        EventDomain.OBJECTIVE: StateSlice.OBJECTIVES,
    })

    spine.emit(EventDomain.RUNTIME, "runtime_available", "graph", {"id": "rt1"})
    assert len(proj.received) == 1
    assert proj.received[0]["slice"] == StateSlice.RUNTIMES


def test_state_slices_cover_domains():
    required = {
        "runtimes", "objectives", "governance", "leverage",
        "workcells", "economy", "observability",
    }
    actual = {s.value for s in StateSlice}
    assert required.issubset(actual), f"missing slices: {required - actual}"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd /opt/OS/.claude/worktrees/anti-divergence-gate && python3 -m pytest substrate/organism/tests/test_projection_port.py -v`

Expected: ImportError.

- [ ] **Step 3: Implement OrganismStatePort**

Create `substrate/organism/projection_port.py`:

```python
"""Projection-agnostic organism state port.

Abstract port that any projection can register against to receive
organism state updates. Follows the socket/port pattern used
throughout UMH substrate (see substrate/sockets/).

Projections register as subscribers with optional slice filtering.
The port broadcasts state updates and bridges EventSpine events
to the appropriate state slices.

No projection-specific code lives here. The port knows about
state slices, not about cockpits, EOS, or any specific consumer.

UMH substrate subsystem. Instance-agnostic.
"""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from enum import Enum
from typing import Any

from substrate.organism.event_spine import EventDomain, EventSpine, OrganismEvent

logger = logging.getLogger(__name__)


class StateSlice(str, Enum):
    RUNTIMES = "runtimes"
    OBJECTIVES = "objectives"
    GOVERNANCE = "governance"
    LEVERAGE = "leverage"
    WORKCELLS = "workcells"
    ECONOMY = "economy"
    OBSERVABILITY = "observability"
    SUPERVISOR = "supervisor"
    ADVISORS = "advisors"
    FILESYSTEM = "filesystem"
    DOCKER = "docker"
    TMUX = "tmux"


class ProjectionSubscriber(ABC):
    """Interface that projections implement to receive state updates."""

    @property
    @abstractmethod
    def subscriber_id(self) -> str:
        ...

    @abstractmethod
    def accepts_slices(self) -> set[StateSlice] | None:
        """Return the set of slices this projection wants.
        None means all slices.
        """
        ...

    @abstractmethod
    def on_state_update(self, slice_type: StateSlice, data: dict[str, Any]) -> None:
        ...


class OrganismStatePort:
    """Projection-agnostic organism state broadcast port.

    Register any number of projections. Each receives state
    updates filtered by the slices they accept.
    """

    def __init__(self) -> None:
        self._subscribers: dict[str, ProjectionSubscriber] = {}

    def register(self, subscriber: ProjectionSubscriber) -> None:
        self._subscribers[subscriber.subscriber_id] = subscriber
        logger.debug("projection registered: %s", subscriber.subscriber_id)

    def unregister(self, subscriber_id: str) -> None:
        self._subscribers.pop(subscriber_id, None)
        logger.debug("projection unregistered: %s", subscriber_id)

    def registered_projections(self) -> list[str]:
        return list(self._subscribers.keys())

    def broadcast(self, slice_type: StateSlice, data: dict[str, Any]) -> None:
        for sub in self._subscribers.values():
            accepted = sub.accepts_slices()
            if accepted is not None and slice_type not in accepted:
                continue
            try:
                sub.on_state_update(slice_type, data)
            except Exception as exc:
                logger.warning(
                    "projection '%s' raised %s: %s",
                    sub.subscriber_id, type(exc).__name__, exc,
                )

    def bridge_from_spine(
        self,
        spine: EventSpine,
        domain_to_slice: dict[EventDomain, StateSlice],
    ) -> None:
        """Subscribe to EventSpine and forward events to projections.

        Maps EventDomains to StateSlices so projections receive
        typed state updates without knowing about the event spine.
        """
        def _handler(event: OrganismEvent) -> None:
            slice_type = domain_to_slice.get(event.domain)
            if slice_type is None:
                return
            self.broadcast(slice_type, event.to_dict())

        spine.subscribe(
            f"projection_port_bridge",
            _handler,
            domains=set(domain_to_slice.keys()),
        )
```

- [ ] **Step 4: Run tests**

Run: `cd /opt/OS/.claude/worktrees/anti-divergence-gate && python3 -m pytest substrate/organism/tests/test_projection_port.py -v`

Expected: All 7 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add substrate/organism/projection_port.py substrate/organism/tests/test_projection_port.py
git commit -m "feat(organism): projection-agnostic state port — universal consumer interface"
```

---

## Task 9: Cockpit Realtime Stream

**Files:**
- Create: `saas/api/routes/ws.ts`
- Create: `saas/bridge/organism_stream_bridge.py`
- Modify: `saas/api/index.ts`

Depends on: Task 1, Task 8

WebSocket endpoint for the cockpit to receive organism events in realtime. Replaces polling-first architecture with event push.

- [ ] **Step 1: Create the Python stream bridge**

Create `saas/bridge/organism_stream_bridge.py`:

```python
"""Organism stream bridge — continuous event emission for cockpit WebSocket.

Subscribes to the EventSpine and streams events as newline-delimited JSON
to stdout, which the TypeScript API reads and forwards to WebSocket clients.

Usage:
    Spawned as a long-running subprocess by the cockpit API.
    Each line of stdout is one JSON event object.

UMH substrate bridge — no instance context.
"""

import sys
import json
import time

_stdout = sys.stdout
sys.stdout = sys.stderr

import os as _os
_BRIDGE_ROOT = _os.path.dirname(
    _os.path.dirname(_os.path.dirname(
        _os.path.abspath(__file__))))
sys.path.insert(0, _BRIDGE_ROOT)

from dotenv import load_dotenv
load_dotenv(_os.path.join(_BRIDGE_ROOT, 'services', '.env'))

import logging
logger = logging.getLogger(__name__)

from substrate.organism.event_spine import EventSpine, OrganismEvent


def _emit(obj: dict) -> None:
    _stdout.write(json.dumps(obj, default=str) + '\n')
    _stdout.flush()


def main():
    spine = EventSpine()

    def on_event(event: OrganismEvent) -> None:
        _emit(event.to_dict())

    spine.subscribe("cockpit_stream", on_event)

    _emit({"type": "stream_ready", "timestamp": time.time()})

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Create WebSocket route**

Create `saas/api/routes/ws.ts`:

```typescript
import type { Env } from '../types.js'
import { Hono } from 'hono'
import { createBunWebSocket } from 'hono/bun'

const { upgradeWebSocket, websocket } = createBunWebSocket()

const router = new Hono<Env>()

interface WsClient {
  ws: any
  filters: string[]
}

const clients: Map<string, WsClient> = new Map()

router.get(
  '/',
  upgradeWebSocket((c) => {
    const clientId = crypto.randomUUID()
    return {
      onOpen(_event, ws) {
        clients.set(clientId, { ws, filters: [] })
        ws.send(JSON.stringify({ type: 'connected', clientId }))
      },
      onMessage(event, ws) {
        try {
          const msg = JSON.parse(event.data as string)
          if (msg.type === 'ping') {
            ws.send(JSON.stringify({ type: 'pong' }))
          } else if (msg.type === 'subscribe' && Array.isArray(msg.domains)) {
            const client = clients.get(clientId)
            if (client) client.filters = msg.domains
            ws.send(JSON.stringify({ type: 'subscribed', domains: msg.domains }))
          }
        } catch {
          // ignore malformed messages
        }
      },
      onClose() {
        clients.delete(clientId)
      },
    }
  })
)

export function broadcastEvent(event: Record<string, unknown>): void {
  const domain = event.domain as string
  const payload = JSON.stringify({ type: 'organism_event', data: event })

  for (const client of clients.values()) {
    if (client.filters.length > 0 && !client.filters.includes(domain)) {
      continue
    }
    try {
      client.ws.send(payload)
    } catch {
      // stale connection — cleaned up on next onClose
    }
  }
}

export { websocket }
export default router
```

- [ ] **Step 3: Mount WebSocket route in API**

Modify `saas/api/index.ts` — add the WebSocket route mount. Read the current file first to find the right insertion point, then add:

```typescript
import wsRouter, { websocket } from './routes/ws.js'
```

And mount it:
```typescript
app.route('/ws', wsRouter)
```

Export websocket for Bun server:
```typescript
export { websocket }
```

- [ ] **Step 4: Compile check**

Run: `python3 -m py_compile saas/bridge/organism_stream_bridge.py`

Expected: Clean compile.

- [ ] **Step 5: Commit**

```bash
git add saas/api/routes/ws.ts saas/bridge/organism_stream_bridge.py saas/api/index.ts
git commit -m "feat(cockpit): WebSocket organism event stream — realtime push replaces polling"
```

---

## Task 10: Daemon Wiring & Meta-IDE Streams

**Files:**
- Modify: `substrate/organism/daemon.py`
- Modify: `substrate/organism/orchestration_loop.py`
- Modify: `substrate/organism/__init__.py`

Depends on: Tasks 1–8

Wire everything together in the OrganismDaemon. The daemon becomes the metabolism host.

- [ ] **Step 1: Wire EventSpine into OrganismDaemon**

Modify `substrate/organism/daemon.py`:

Add `EventSpine` as a first-class daemon subsystem. Wire it into Advisor, RuntimeGraph, RuntimeSupervisor, and the new subsystems.

Key changes to `OrganismDaemon.__init__()`:
```python
from substrate.organism.event_spine import EventSpine
from substrate.organism.autonomous_tick import AutonomousTick, TickConfig
from substrate.organism.objective_queue import ObjectiveQueue
from substrate.organism.allocation_loop import AllocationLoop
from substrate.organism.async_coordinator import AsyncCoordinator
from substrate.organism.projection_port import OrganismStatePort

# In __init__:
self._event_spine = EventSpine()
self._objective_queue = ObjectiveQueue(spine=self._event_spine)
self._allocation_loop = AllocationLoop(
    spine=self._event_spine,
    graph=self._graph,
    supervisor=self._supervisor,
    economy=ExecutionEconomy(),
    governor=RecursionGovernor(),
) if self._graph and self._supervisor else None
self._async_coordinator = AsyncCoordinator(
    coordinator=self._advisor.coordinator,
    spine=self._event_spine,
) if self._advisor.coordinator else None
self._projection_port = OrganismStatePort()

# Properties:
@property
def event_spine(self) -> EventSpine:
    return self._event_spine

@property
def objective_queue(self) -> ObjectiveQueue:
    return self._objective_queue

@property
def projection_port(self) -> OrganismStatePort:
    return self._projection_port
```

- [ ] **Step 2: Wire event emission into orchestration loop stages**

Modify `substrate/organism/orchestration_loop.py`:

Each stage emits an event to the spine after executing. The spine reference is obtained from the daemon.

Add to each `_stage_*` function, after the existing logic:
```python
spine = getattr(daemon, '_event_spine', None)
if spine:
    from substrate.organism.event_spine import EventDomain
    spine.emit(EventDomain.EXECUTION, "stage_completed", "orchestration_loop", {
        "stage": "stage_name",
        "details": report.details[-1] if report.details else {},
    })
```

- [ ] **Step 3: Update organism __init__.py exports**

Modify `substrate/organism/__init__.py`:

```python
"""UMH Organism — distributed orchestration substrate.

Public API for the organism subsystem. All external code should
import from this module rather than reaching into submodules.

Core subsystems:
  - EventSpine: canonical organism event transport
  - AutonomousTick: continuous metabolism heartbeat
  - Advisor: unified orchestration hub
  - OrganismDaemon: persistent daemon with full subsystem wiring
  - RuntimeGraph: capability-based runtime registry and selection
  - RuntimeSupervisor: health monitoring, crash recovery, restart
  - OrganismCoordinator: DAG decomposition and execution
  - AsyncCoordinator: event-driven async objective execution
  - ObjectiveQueue: priority-ordered objective intake
  - AllocationLoop: governed runtime allocation
  - HomeostasisEngine: 8-dimension self-regulation
  - OrganismObserver: cockpit snapshot aggregation
  - LeverageAssimilator: external framework ingestion and scoring
  - OrganismStatePort: projection-agnostic state interface
  - Orchestration loop: PersistentLoop integration for daemon mode
"""
```

- [ ] **Step 4: Run full organism test suite**

Run: `cd /opt/OS/.claude/worktrees/anti-divergence-gate && python3 -m pytest substrate/organism/tests/ -v --tb=short 2>&1 | tail -30`

Expected: All tests PASS including new ones from Tasks 1–8.

- [ ] **Step 5: Commit**

```bash
git add substrate/organism/daemon.py substrate/organism/orchestration_loop.py substrate/organism/__init__.py
git commit -m "feat(organism): full metabolism wiring — daemon hosts EventSpine, tick engine, allocation loop"
```

---

## Task 11: Anti-Divergence Validation & Audit

**Files:**
- Create: `docs/audits/convergence/phase5_autonomous_metabolism.md`

Depends on: Tasks 1–10

Final validation pass — compile, test, anti-divergence gates, instance leak gates.

- [ ] **Step 1: Run anti-divergence gate**

Run: `cd /opt/OS/.claude/worktrees/anti-divergence-gate && python3 scripts/check_type_divergence.py --all 2>&1 | tail -10`

Expected: PASS (no shadow types).

- [ ] **Step 2: Run instance leak gate**

Run: `cd /opt/OS/.claude/worktrees/anti-divergence-gate && python3 scripts/check_instance_leak.py --all 2>&1 | tail -10`

Expected: PASS (no instance values in substrate/).

- [ ] **Step 3: Run full test suite**

Run: `cd /opt/OS/.claude/worktrees/anti-divergence-gate && python3 -m pytest substrate/organism/tests/ -v --tb=short`

Expected: All tests PASS.

- [ ] **Step 4: Compile all new modules**

Run:
```bash
for f in substrate/organism/event_spine.py substrate/organism/autonomous_tick.py substrate/organism/objective_queue.py substrate/organism/allocation_loop.py substrate/organism/async_coordinator.py substrate/organism/projection_port.py; do
  python3 -m py_compile "$f" && echo "OK: $f" || echo "FAIL: $f"
done
```

Expected: All OK.

- [ ] **Step 5: Generate audit document**

Create `docs/audits/convergence/phase5_autonomous_metabolism.md` with:
- Architecture delta (what changed from phase 4)
- New subsystem inventory
- Event topology diagram (ASCII)
- Governance flow
- Leverage flow
- Async execution lifecycle
- Test coverage summary
- Remaining bottlenecks
- Next leverage frontier

- [ ] **Step 6: Final commit**

```bash
git add docs/audits/convergence/phase5_autonomous_metabolism.md
git commit -m "docs: phase 5 autonomous metabolism audit — architecture delta and validation"
```

---

## Execution Summary

| Task | Subsystem | New Files | Tests |
|------|-----------|-----------|-------|
| 1 | Unified Event Spine | 1 module + 1 test | 14 |
| 2 | Autonomous Tick Engine | 1 module + 1 test | 12 |
| 3 | Continuous Objective Queue | 1 module + 1 test | 13 |
| 4 | Governed Runtime Allocation | 1 module + 1 test | 6 |
| 5 | Async Coordinator Execution | 1 module + 1 test | 8 |
| 6 | Runtime Event Bus Wiring | 0 new + 1 test | 6 |
| 7 | Continuous Leverage Rebalance | 0 new + 1 test | 4 |
| 8 | Projection-Agnostic State Port | 1 module + 1 test | 7 |
| 9 | Cockpit Realtime Stream | 2 files (TS+Py) | 0 (integration) |
| 10 | Daemon Wiring & Meta-IDE | 0 new | 0 (uses existing) |
| 11 | Validation & Audit | 1 doc | gates |
| **Total** | | **6 new modules, 8 test files, 2 bridge files, 1 audit** | **~70 tests** |

All tasks build layer-by-layer. No circular dependencies. No projection coupling. Full governance integration.
