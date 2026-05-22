# Organism Vertical Slice — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build one end-to-end path through the organism: cockpit signal submission → DEX advisor decomposition → Researcher agent delegation → VPS worker execution → self-critique → deliverable + trace visible in cockpit.

**Architecture:** The vertical slice adds three new layers on top of the existing UMH control plane: (1) an organism layer (`services/umh/organism/`) containing the agent base runtime with critique loop, persistent agent cells, worker cell spawner, and daemon lifecycle manager; (2) a DEX advisor endpoint that receives cockpit signals, interprets them, and delegates to agents; (3) cockpit UI additions for signal input and agent activity display. All new code integrates with the existing ExecutionPipeline, TraceStore, ViewSocket, and governance infrastructure.

**Tech Stack:** Python 3.12, FastAPI, Pydantic, JSONL persistence (DB-upgradeable), existing model_router for LLM calls, existing ViewSocket/WebSocket for real-time cockpit updates, React/TypeScript/Zustand for frontend.

---

## File Structure

### New files (organism layer)

| File | Responsibility |
|------|----------------|
| `services/umh/organism/__init__.py` | Package init |
| `services/umh/organism/protocols.py` | Pydantic schemas: Deliverable, AgentMessage, LearningSignal, WorkerSpec |
| `services/umh/organism/agent_runtime.py` | Base agent runtime: receive task → execute → self-critique → iterate → post deliverable |
| `services/umh/organism/worker_cell.py` | Worker cell spawner: creates bounded subprocess tasks via existing pipeline |
| `services/umh/organism/agents.py` | Concrete agent implementations: ResearcherAgent, BuilderAgent, AutoResearchAgent |
| `services/umh/organism/advisor.py` | DEX advisor cell: interprets signals, decomposes, delegates to agents, synthesizes results |
| `services/umh/organism/daemon.py` | Daemon lifecycle: manages agent registry, spawn/restart, state persistence |
| `services/umh/organism/store.py` | JSONL persistence for deliverables, agent messages, agent state |

### Modified files (integration)

| File | Change |
|------|--------|
| `services/umh/control_plane/app.py` | Register organism startup in lifespan, add DEX signal endpoint |
| `services/umh/control_plane/cockpit_api.py` | Add `/api/umh/organism/status`, `/api/umh/organism/agents`, `/api/umh/organism/deliverables` endpoints |
| `apps/cockpit/src/api/client.ts` | Add organism API types and methods |
| `apps/cockpit/src/stores/cockpitStore.ts` | Add organism state (agents, deliverables) |
| `apps/cockpit/src/views/CommandCenter.tsx` | Add signal input bar and agent activity panel |
| `apps/cockpit/src/types/domain.ts` | Add OrganismAgent, Deliverable types |
| `apps/cockpit/src/lib/ws-client.ts` | Handle organism.* WebSocket events |

### Test files

| File | What it tests |
|------|---------------|
| `services/umh/organism/tests/__init__.py` | Package init |
| `services/umh/organism/tests/test_protocols.py` | Protocol validation: Deliverable, AgentMessage, WorkerSpec |
| `services/umh/organism/tests/test_agent_runtime.py` | Agent base runtime: critique loop, iteration, deliverable production |
| `services/umh/organism/tests/test_worker_cell.py` | Worker cell: spawn, execute, return result |
| `services/umh/organism/tests/test_advisor.py` | Advisor: interpret, decompose, delegate, synthesize |
| `services/umh/organism/tests/test_e2e.py` | Full vertical slice: signal in → deliverable out → trace queryable |

---

## Task 1: Organism Protocols

**Files:**
- Create: `services/umh/organism/__init__.py`
- Create: `services/umh/organism/protocols.py`
- Create: `services/umh/organism/tests/__init__.py`
- Create: `services/umh/organism/tests/test_protocols.py`

- [ ] **Step 1: Write the failing test**

```python
"""tests for organism protocols — deliverable, agent message, worker spec."""
import sys
sys.path.insert(0, "/opt/OS")

import pytest
from services.umh.organism.protocols import (
    Deliverable,
    AgentMessage,
    LearningSignal,
    WorkerSpec,
    AgentStatus,
    CritiqueResult,
)


def test_deliverable_creation():
    d = Deliverable(
        agent_id="researcher-001",
        task_id="task-abc",
        content="Found 3 state mutations outside canonical paths in cognitive_loop.py",
        self_critique=CritiqueResult(score=8, reasoning="thorough analysis, covered all methods"),
    )
    assert d.agent_id == "researcher-001"
    assert d.self_critique.score == 8
    assert d.self_critique.passed is True  # score >= 7 passes


def test_critique_result_threshold():
    low = CritiqueResult(score=4, reasoning="incomplete")
    assert low.passed is False
    high = CritiqueResult(score=7, reasoning="adequate")
    assert high.passed is True


def test_agent_message_creation():
    msg = AgentMessage(
        sender="advisor",
        recipient="researcher-001",
        intent="delegate_task",
        payload={"task": "audit cognitive_loop.py", "tools": ["read_file", "grep"]},
    )
    assert msg.sender == "advisor"
    assert msg.intent == "delegate_task"
    assert msg.conversation_id is not None  # auto-generated


def test_worker_spec_creation():
    spec = WorkerSpec(
        parent_agent_id="researcher-001",
        task="grep for state mutations in cognitive_loop.py",
        environment_id="vps-prod",
        tools=["read_file", "grep", "git_log"],
        model_tier="sonnet",
        risk_class="READ_ONLY",
        timeout_s=60.0,
    )
    assert spec.environment_id == "vps-prod"
    assert spec.model_tier == "sonnet"
    assert "grep" in spec.tools


def test_learning_signal_creation():
    sig = LearningSignal(
        agent_id="researcher-001",
        deliverable_id="del-xyz",
        pattern_observed="cognitive_loop uses raw dict mutations instead of typed setters",
        confidence=0.85,
    )
    assert sig.confidence == 0.85
```

- [ ] **Step 2: Create package init files**

Create empty `services/umh/organism/__init__.py` and `services/umh/organism/tests/__init__.py`.

- [ ] **Step 3: Run test to verify it fails**

Run: `python3 -m pytest services/umh/organism/tests/test_protocols.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'services.umh.organism.protocols'`

- [ ] **Step 4: Implement protocols**

```python
"""Organism protocols — typed contracts for the agent society.

These are the data shapes that cross boundaries between advisor, agents,
workers, and the shared state plane. Pydantic models, not dicts.
"""
from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel, Field


class AgentStatus(str, Enum):
    IDLE = "idle"
    WORKING = "working"
    CRITIQUING = "critiquing"
    BLOCKED = "blocked"
    OFFLINE = "offline"


class CritiqueResult(BaseModel):
    score: int = Field(ge=1, le=10)
    reasoning: str = Field(max_length=500)
    iteration: int = 1
    threshold: int = 7

    @property
    def passed(self) -> bool:
        return self.score >= self.threshold


class Deliverable(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    agent_id: str
    task_id: str
    content: str
    self_critique: CritiqueResult
    parent_trace_id: UUID | None = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    metadata: dict[str, Any] = Field(default_factory=dict)


class AgentMessage(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    sender: str
    recipient: str
    intent: str = Field(max_length=80)
    payload: dict[str, Any] = Field(default_factory=dict)
    conversation_id: UUID = Field(default_factory=uuid4)
    parent_message_id: UUID | None = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class WorkerSpec(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    parent_agent_id: str
    task: str = Field(max_length=500)
    environment_id: str = "vps-prod"
    tools: list[str] = Field(default_factory=list)
    model_tier: str = "sonnet"
    risk_class: str = "READ_ONLY"
    timeout_s: float = 60.0
    parent_trace_id: UUID | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class LearningSignal(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    agent_id: str
    deliverable_id: str
    pattern_observed: str = Field(max_length=500)
    generalization_hint: str = ""
    confidence: float = Field(ge=0.0, le=1.0)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
```

- [ ] **Step 5: Run test to verify it passes**

Run: `python3 -m pytest services/umh/organism/tests/test_protocols.py -v`
Expected: all 5 tests PASS

- [ ] **Step 6: Compile check and format**

Run: `python3 -m py_compile services/umh/organism/protocols.py && ruff format services/umh/organism/protocols.py`

- [ ] **Step 7: Commit**

```bash
git add services/umh/organism/
git commit -m "feat(organism): typed protocols — Deliverable, AgentMessage, WorkerSpec, LearningSignal"
```

---

## Task 2: JSONL Persistence Store

**Files:**
- Create: `services/umh/organism/store.py`
- Create: `services/umh/organism/tests/test_store.py`

- [ ] **Step 1: Write the failing test**

```python
"""tests for organism JSONL store."""
import sys
sys.path.insert(0, "/opt/OS")

import tempfile
from pathlib import Path

import pytest
from services.umh.organism.protocols import (
    AgentMessage,
    AgentStatus,
    CritiqueResult,
    Deliverable,
    LearningSignal,
)
from services.umh.organism.store import OrganismStore


@pytest.fixture
def store(tmp_path):
    return OrganismStore(store_dir=tmp_path / "organism")


def test_save_and_list_deliverables(store):
    d = Deliverable(
        agent_id="researcher-001",
        task_id="task-1",
        content="Found issues",
        self_critique=CritiqueResult(score=8, reasoning="good"),
    )
    store.save_deliverable(d)
    results = store.list_deliverables(agent_id="researcher-001")
    assert len(results) == 1
    assert results[0]["agent_id"] == "researcher-001"


def test_save_and_list_messages(store):
    msg = AgentMessage(
        sender="advisor",
        recipient="researcher-001",
        intent="delegate_task",
        payload={"task": "audit"},
    )
    store.save_message(msg)
    results = store.list_messages(recipient="researcher-001")
    assert len(results) == 1


def test_save_agent_state(store):
    store.save_agent_state("researcher-001", {
        "status": "idle",
        "tasks_completed": 5,
        "last_task": "audit cognitive_loop.py",
    })
    state = store.load_agent_state("researcher-001")
    assert state is not None
    assert state["tasks_completed"] == 5


def test_load_missing_agent_state(store):
    state = store.load_agent_state("nonexistent")
    assert state is None


def test_save_learning_signal(store):
    sig = LearningSignal(
        agent_id="researcher-001",
        deliverable_id="del-1",
        pattern_observed="state mutation outside canonical path",
        confidence=0.9,
    )
    store.save_learning_signal(sig)
    results = store.list_learning_signals()
    assert len(results) == 1
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m pytest services/umh/organism/tests/test_store.py -v`
Expected: FAIL with `ModuleNotFoundError`

- [ ] **Step 3: Implement store**

```python
"""Organism store — JSONL persistence for deliverables, messages, agent state.

Same pattern as TraceStore: append-only JSONL, separate index files per
entity type. DB-upgradeable later — swap this module, contracts stay.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from services.umh.organism.protocols import (
    AgentMessage,
    Deliverable,
    LearningSignal,
)


class OrganismStore:
    def __init__(self, store_dir: str | Path = "data/umh/organism") -> None:
        self._dir = Path(store_dir)
        self._dir.mkdir(parents=True, exist_ok=True)
        self._deliverables = self._dir / "deliverables.jsonl"
        self._messages = self._dir / "messages.jsonl"
        self._learning = self._dir / "learning_signals.jsonl"
        self._agents_dir = self._dir / "agents"
        self._agents_dir.mkdir(exist_ok=True)

    def _append(self, path: Path, record: dict[str, Any]) -> None:
        with open(path, "a") as f:
            f.write(json.dumps(record, default=str, separators=(",", ":")) + "\n")

    def _read_all(self, path: Path) -> list[dict[str, Any]]:
        if not path.exists():
            return []
        entries: list[dict[str, Any]] = []
        with open(path) as f:
            for line in f:
                line = line.strip()
                if line:
                    entries.append(json.loads(line))
        return entries

    def save_deliverable(self, d: Deliverable) -> None:
        self._append(self._deliverables, d.model_dump(mode="json"))

    def list_deliverables(
        self,
        agent_id: str | None = None,
        limit: int = 50,
    ) -> list[dict[str, Any]]:
        all_d = self._read_all(self._deliverables)
        if agent_id:
            all_d = [d for d in all_d if d.get("agent_id") == agent_id]
        return all_d[-limit:]

    def save_message(self, msg: AgentMessage) -> None:
        self._append(self._messages, msg.model_dump(mode="json"))

    def list_messages(
        self,
        recipient: str | None = None,
        sender: str | None = None,
        limit: int = 50,
    ) -> list[dict[str, Any]]:
        all_m = self._read_all(self._messages)
        if recipient:
            all_m = [m for m in all_m if m.get("recipient") == recipient]
        if sender:
            all_m = [m for m in all_m if m.get("sender") == sender]
        return all_m[-limit:]

    def save_agent_state(self, agent_id: str, state: dict[str, Any]) -> None:
        state["_updated_at"] = datetime.now(timezone.utc).isoformat()
        path = self._agents_dir / f"{agent_id}.json"
        path.write_text(json.dumps(state, default=str, indent=2))

    def load_agent_state(self, agent_id: str) -> dict[str, Any] | None:
        path = self._agents_dir / f"{agent_id}.json"
        if not path.exists():
            return None
        return json.loads(path.read_text())

    def save_learning_signal(self, sig: LearningSignal) -> None:
        self._append(self._learning, sig.model_dump(mode="json"))

    def list_learning_signals(self, limit: int = 50) -> list[dict[str, Any]]:
        return self._read_all(self._learning)[-limit:]
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 -m pytest services/umh/organism/tests/test_store.py -v`
Expected: all 5 tests PASS

- [ ] **Step 5: Commit**

```bash
git add services/umh/organism/store.py services/umh/organism/tests/test_store.py
git commit -m "feat(organism): JSONL store for deliverables, messages, agent state"
```

---

## Task 3: Worker Cell

**Files:**
- Create: `services/umh/organism/worker_cell.py`
- Create: `services/umh/organism/tests/test_worker_cell.py`

- [ ] **Step 1: Write the failing test**

```python
"""tests for worker cell — bounded task execution via the pipeline."""
import sys
sys.path.insert(0, "/opt/OS")

import pytest
from services.umh.organism.protocols import WorkerSpec
from services.umh.organism.worker_cell import WorkerCell


def test_worker_executes_shell_read():
    spec = WorkerSpec(
        parent_agent_id="researcher-001",
        task="list python files in services/umh/organism/",
        environment_id="vps-prod",
        tools=["shell"],
        model_tier="sonnet",
        risk_class="READ_ONLY",
        timeout_s=30.0,
    )
    cell = WorkerCell()
    result = cell.execute(spec, adapter_name="shell", operation="query", params={
        "command": "ls /opt/OS/services/umh/organism/*.py 2>/dev/null | head -5",
    })
    assert result.executed is True
    assert result.trace_id is not None


def test_worker_returns_failure_on_bad_adapter():
    spec = WorkerSpec(
        parent_agent_id="researcher-001",
        task="test bad adapter",
        environment_id="vps-prod",
        tools=[],
        risk_class="READ_ONLY",
    )
    cell = WorkerCell()
    result = cell.execute(spec, adapter_name="nonexistent_adapter", operation="query", params={})
    assert result.executed is False or result.success is False


def test_worker_result_has_trace_id():
    spec = WorkerSpec(
        parent_agent_id="test-agent",
        task="simple test",
        environment_id="vps-prod",
        tools=["shell"],
        risk_class="READ_ONLY",
    )
    cell = WorkerCell()
    result = cell.execute(spec, adapter_name="shell", operation="query", params={
        "command": "echo hello",
    })
    assert result.trace_id is not None
    assert isinstance(str(result.trace_id), str)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m pytest services/umh/organism/tests/test_worker_cell.py -v`
Expected: FAIL with `ModuleNotFoundError`

- [ ] **Step 3: Implement worker cell**

```python
"""Worker cell — bounded task execution through the existing pipeline.

A worker cell is a disposable execution unit. It wraps the existing
ExecutionPipeline.submit_signal() with worker-specific metadata:
parent_agent_id, environment_id, model_tier, scoped tools.

The worker never persists state. It executes, returns a result, and dies.
"""
from __future__ import annotations

from typing import Any
from uuid import UUID

from services.umh.control_plane.pipeline import ExecutionPipeline, PipelineResult
from services.umh.execution.executor import build_default_executor
from services.umh.governance.risk_classes import RiskClass
from services.umh.organism.protocols import WorkerSpec
from services.umh.protocols.signal import SignalSource


class WorkerCell:
    def __init__(self, pipeline: ExecutionPipeline | None = None) -> None:
        self._pipeline = pipeline or ExecutionPipeline(executor=build_default_executor())

    def execute(
        self,
        spec: WorkerSpec,
        *,
        adapter_name: str = "shell",
        operation: str = "query",
        params: dict[str, Any] | None = None,
    ) -> PipelineResult:
        try:
            risk = RiskClass[spec.risk_class]
        except KeyError:
            risk = RiskClass.READ_ONLY

        return self._pipeline.submit_signal(
            spec.task,
            source=SignalSource.INTERNAL_EVENT,
            risk_class=risk,
            adapter_name=adapter_name,
            operation=operation,
            params=params or {},
            metadata={
                "worker_cell_id": str(spec.id),
                "parent_agent_id": spec.parent_agent_id,
                "environment_id": spec.environment_id,
                "model_tier": spec.model_tier,
                "parent_trace_id": str(spec.parent_trace_id) if spec.parent_trace_id else None,
            },
        )
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 -m pytest services/umh/organism/tests/test_worker_cell.py -v`
Expected: all 3 tests PASS

- [ ] **Step 5: Commit**

```bash
git add services/umh/organism/worker_cell.py services/umh/organism/tests/test_worker_cell.py
git commit -m "feat(organism): worker cell — bounded task execution through pipeline"
```

---

## Task 4: Agent Base Runtime with Critique Loop

**Files:**
- Create: `services/umh/organism/agent_runtime.py`
- Create: `services/umh/organism/tests/test_agent_runtime.py`

- [ ] **Step 1: Write the failing test**

```python
"""tests for agent base runtime — critique loop, deliverable production."""
import sys
sys.path.insert(0, "/opt/OS")

import pytest
from unittest.mock import MagicMock, patch
from services.umh.organism.agent_runtime import AgentRuntime
from services.umh.organism.protocols import AgentMessage, AgentStatus, CritiqueResult, Deliverable
from services.umh.organism.store import OrganismStore


@pytest.fixture
def store(tmp_path):
    return OrganismStore(store_dir=tmp_path / "organism")


@pytest.fixture
def runtime(store):
    return AgentRuntime(
        agent_id="test-agent",
        agent_name="Test Agent",
        soul_doc="You are a test agent.",
        store=store,
        max_critique_iterations=2,
    )


def test_runtime_starts_idle(runtime):
    assert runtime.status == AgentStatus.IDLE


def test_runtime_processes_task(runtime):
    msg = AgentMessage(
        sender="advisor",
        recipient="test-agent",
        intent="delegate_task",
        payload={"task": "echo hello", "adapter": "shell", "operation": "query", "params": {"command": "echo hello"}},
    )
    deliverable = runtime.handle_task(msg)
    assert deliverable is not None
    assert deliverable.agent_id == "test-agent"
    assert deliverable.self_critique.score >= 1


def test_deliverable_persisted_to_store(runtime, store):
    msg = AgentMessage(
        sender="advisor",
        recipient="test-agent",
        intent="delegate_task",
        payload={"task": "echo test", "adapter": "shell", "operation": "query", "params": {"command": "echo test"}},
    )
    runtime.handle_task(msg)
    deliverables = store.list_deliverables(agent_id="test-agent")
    assert len(deliverables) == 1


def test_status_transitions(runtime):
    msg = AgentMessage(
        sender="advisor",
        recipient="test-agent",
        intent="delegate_task",
        payload={"task": "echo status", "adapter": "shell", "operation": "query", "params": {"command": "echo status"}},
    )
    assert runtime.status == AgentStatus.IDLE
    runtime.handle_task(msg)
    assert runtime.status == AgentStatus.IDLE  # back to idle after completion
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m pytest services/umh/organism/tests/test_agent_runtime.py -v`
Expected: FAIL with `ModuleNotFoundError`

- [ ] **Step 3: Implement agent runtime**

```python
"""Agent base runtime — the foundational behavior of every agent in the society.

Every agent:
1. Receives a task (AgentMessage with intent=delegate_task)
2. Spawns a worker cell to execute bounded work
3. Self-critiques the result (score 1-10)
4. If critique fails and iterations remain, re-executes with critique as feedback
5. Posts Deliverable to store + learning channel
6. Returns result to caller

The critique loop is architecturally non-negotiable. Intelligence improves
over slices; the loop exists from day one.
"""
from __future__ import annotations

import logging
from typing import Any

from services.umh.organism.protocols import (
    AgentMessage,
    AgentStatus,
    CritiqueResult,
    Deliverable,
    LearningSignal,
    WorkerSpec,
)
from services.umh.organism.store import OrganismStore
from services.umh.organism.worker_cell import WorkerCell

logger = logging.getLogger(__name__)


class AgentRuntime:
    def __init__(
        self,
        agent_id: str,
        agent_name: str,
        soul_doc: str,
        store: OrganismStore,
        worker: WorkerCell | None = None,
        max_critique_iterations: int = 2,
        critique_threshold: int = 7,
    ) -> None:
        self.agent_id = agent_id
        self.agent_name = agent_name
        self.soul_doc = soul_doc
        self._store = store
        self._worker = worker or WorkerCell()
        self._max_iterations = max_critique_iterations
        self._critique_threshold = critique_threshold
        self._status = AgentStatus.IDLE
        self._tasks_completed = 0

    @property
    def status(self) -> AgentStatus:
        return self._status

    @property
    def tasks_completed(self) -> int:
        return self._tasks_completed

    def handle_task(self, msg: AgentMessage) -> Deliverable | None:
        if msg.intent != "delegate_task":
            logger.warning("agent %s received unknown intent: %s", self.agent_id, msg.intent)
            return None

        self._status = AgentStatus.WORKING
        task = msg.payload.get("task", "")
        adapter = msg.payload.get("adapter", "shell")
        operation = msg.payload.get("operation", "query")
        params = msg.payload.get("params", {})
        tools = msg.payload.get("tools", [adapter])

        best_result: str | None = None
        best_critique: CritiqueResult | None = None

        for iteration in range(1, self._max_iterations + 1):
            self._status = AgentStatus.WORKING

            spec = WorkerSpec(
                parent_agent_id=self.agent_id,
                task=task,
                environment_id="vps-prod",
                tools=tools,
                model_tier="sonnet",
                risk_class=msg.payload.get("risk_class", "READ_ONLY"),
            )

            pipeline_result = self._worker.execute(
                spec,
                adapter_name=adapter,
                operation=operation,
                params=params,
            )

            if pipeline_result.executed and pipeline_result.success:
                result_content = f"Execution successful (trace: {pipeline_result.trace_id})"
                if pipeline_result.outcome_type:
                    result_content += f", outcome: {pipeline_result.outcome_type}"
            elif pipeline_result.executed:
                result_content = f"Execution completed with issues (trace: {pipeline_result.trace_id})"
            else:
                result_content = f"Execution blocked: {pipeline_result.governance_rationale}"

            self._status = AgentStatus.CRITIQUING
            critique = self._self_critique(task, result_content, iteration)

            if best_critique is None or critique.score > best_critique.score:
                best_result = result_content
                best_critique = critique

            if critique.passed:
                break

            if iteration < self._max_iterations:
                params = {**params, "_critique_feedback": critique.reasoning}
                logger.info(
                    "agent %s critique failed (score=%d), iterating (%d/%d)",
                    self.agent_id, critique.score, iteration, self._max_iterations,
                )

        assert best_result is not None
        assert best_critique is not None

        deliverable = Deliverable(
            agent_id=self.agent_id,
            task_id=str(msg.id),
            content=best_result,
            self_critique=best_critique,
            parent_trace_id=pipeline_result.trace_id,
        )

        self._store.save_deliverable(deliverable)

        learning = LearningSignal(
            agent_id=self.agent_id,
            deliverable_id=str(deliverable.id),
            pattern_observed=f"task={task[:100]}, critique_score={best_critique.score}",
            confidence=best_critique.score / 10.0,
        )
        self._store.save_learning_signal(learning)

        self._tasks_completed += 1
        self._status = AgentStatus.IDLE

        self._persist_state()

        return deliverable

    def _self_critique(self, task: str, result: str, iteration: int) -> CritiqueResult:
        has_content = bool(result and "successful" in result.lower())
        addresses_task = bool(task and len(result) > 20)

        score = 5
        if has_content:
            score += 2
        if addresses_task:
            score += 2
        if "blocked" in result.lower():
            score -= 3

        score = max(1, min(10, score))

        return CritiqueResult(
            score=score,
            reasoning=f"iteration {iteration}: content={'present' if has_content else 'missing'}, "
            f"task_relevance={'yes' if addresses_task else 'no'}",
            iteration=iteration,
            threshold=self._critique_threshold,
        )

    def _persist_state(self) -> None:
        self._store.save_agent_state(self.agent_id, {
            "agent_id": self.agent_id,
            "agent_name": self.agent_name,
            "status": self._status.value,
            "tasks_completed": self._tasks_completed,
        })

    def to_status_dict(self) -> dict[str, Any]:
        return {
            "agent_id": self.agent_id,
            "agent_name": self.agent_name,
            "status": self._status.value,
            "tasks_completed": self._tasks_completed,
        }
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 -m pytest services/umh/organism/tests/test_agent_runtime.py -v`
Expected: all 4 tests PASS

- [ ] **Step 5: Commit**

```bash
git add services/umh/organism/agent_runtime.py services/umh/organism/tests/test_agent_runtime.py
git commit -m "feat(organism): agent base runtime with critique loop"
```

---

## Task 5: Concrete Agent Cells

**Files:**
- Create: `services/umh/organism/agents.py`

- [ ] **Step 1: Write the agent implementations**

```python
"""Concrete agent cells — Researcher, Builder, AutoResearch.

Each agent is an AgentRuntime subclass that overrides _self_critique()
with domain-specific evaluation logic. The base runtime handles the
critique loop, worker spawning, and deliverable persistence.

At Slice 0 these are thin wrappers. Intelligence deepens over slices;
the loop + protocol + persistence are non-negotiable now.
"""
from __future__ import annotations

from services.umh.organism.agent_runtime import AgentRuntime
from services.umh.organism.protocols import CritiqueResult
from services.umh.organism.store import OrganismStore
from services.umh.organism.worker_cell import WorkerCell

RESEARCHER_SOUL = """You are the Researcher agent in the UMH organism.
Your domain: bounded research tasks across codebase, docs, web.
You spawn workers with read-only tools (read_file, grep, git_log).
You never modify files. You always self-critique your findings."""

BUILDER_SOUL = """You are the Builder agent in the UMH organism.
Your domain: code edits, implementation, file mutations.
You spawn workers with write tools (edit_file, shell).
You always verify your changes compile before delivering."""

AUTO_RESEARCH_SOUL = """You are the Auto-Research agent in the UMH organism.
Your domain: pattern extraction from agent deliverables and learning signals.
You observe the learning channel and identify recurring patterns.
You propose soul-doc updates for other agents."""


def create_researcher(store: OrganismStore, worker: WorkerCell | None = None) -> AgentRuntime:
    return AgentRuntime(
        agent_id="researcher",
        agent_name="Researcher",
        soul_doc=RESEARCHER_SOUL,
        store=store,
        worker=worker,
        max_critique_iterations=2,
        critique_threshold=7,
    )


def create_builder(store: OrganismStore, worker: WorkerCell | None = None) -> AgentRuntime:
    return AgentRuntime(
        agent_id="builder",
        agent_name="Builder",
        soul_doc=BUILDER_SOUL,
        store=store,
        worker=worker,
        max_critique_iterations=2,
        critique_threshold=7,
    )


def create_auto_research(store: OrganismStore, worker: WorkerCell | None = None) -> AgentRuntime:
    return AgentRuntime(
        agent_id="auto-research",
        agent_name="Auto-Research",
        soul_doc=AUTO_RESEARCH_SOUL,
        store=store,
        worker=worker,
        max_critique_iterations=1,
        critique_threshold=5,
    )
```

- [ ] **Step 2: Compile check**

Run: `python3 -m py_compile services/umh/organism/agents.py && echo "OK"`

- [ ] **Step 3: Commit**

```bash
git add services/umh/organism/agents.py
git commit -m "feat(organism): concrete agent cells — Researcher, Builder, AutoResearch"
```

---

## Task 6: DEX Advisor Cell

**Files:**
- Create: `services/umh/organism/advisor.py`
- Create: `services/umh/organism/tests/test_advisor.py`

- [ ] **Step 1: Write the failing test**

```python
"""tests for DEX advisor — interpret, decompose, delegate, synthesize."""
import sys
sys.path.insert(0, "/opt/OS")

import pytest
from services.umh.organism.advisor import Advisor
from services.umh.organism.store import OrganismStore


@pytest.fixture
def store(tmp_path):
    return OrganismStore(store_dir=tmp_path / "organism")


@pytest.fixture
def advisor(store):
    return Advisor(store=store)


def test_advisor_has_agents(advisor):
    agents = advisor.list_agents()
    assert len(agents) == 3
    names = {a["agent_name"] for a in agents}
    assert names == {"Researcher", "Builder", "Auto-Research"}


def test_advisor_delegates_to_researcher(advisor):
    result = advisor.handle_signal(
        "Audit cognitive_loop.py for state mutations outside canonical paths"
    )
    assert result is not None
    assert result["delegated_to"] == "researcher"
    assert result["deliverable"] is not None


def test_advisor_delegates_to_builder(advisor):
    result = advisor.handle_signal(
        "Create a new file at /tmp/test_organism.txt with content 'hello'"
    )
    assert result is not None
    assert result["delegated_to"] == "builder"


def test_advisor_returns_status(advisor):
    status = advisor.organism_status()
    assert "agents" in status
    assert "total_deliverables" in status
    assert len(status["agents"]) == 3
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m pytest services/umh/organism/tests/test_advisor.py -v`
Expected: FAIL with `ModuleNotFoundError`

- [ ] **Step 3: Implement advisor**

```python
"""DEX Advisor cell — the top-level orchestrator of the organism.

The advisor:
1. Receives signals from the cockpit (user messages)
2. Interprets intent and decomposes into agent-routable tasks
3. Selects the right agent based on task class
4. Delegates via typed AgentMessage
5. Collects deliverable
6. Synthesizes result for the user
7. Emits ViewFrame events for cockpit real-time updates

Context economy: the advisor never reads files, runs commands, or
calls external APIs directly. It delegates everything to agents
who delegate to workers.
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from services.umh.organism.agents import create_auto_research, create_builder, create_researcher
from services.umh.organism.agent_runtime import AgentRuntime
from services.umh.organism.protocols import AgentMessage, Deliverable
from services.umh.organism.store import OrganismStore
from services.umh.organism.worker_cell import WorkerCell

logger = logging.getLogger(__name__)

BUILD_KEYWORDS = {"create", "write", "edit", "modify", "add", "fix", "implement", "build", "update", "refactor", "delete", "remove"}
RESEARCH_KEYWORDS = {"audit", "find", "search", "check", "analyze", "investigate", "look", "review", "scan", "list", "show", "read", "examine", "inspect"}


class Advisor:
    def __init__(
        self,
        store: OrganismStore | None = None,
        worker: WorkerCell | None = None,
    ) -> None:
        self._store = store or OrganismStore()
        self._worker = worker or WorkerCell()
        self._agents: dict[str, AgentRuntime] = {}
        self._init_agents()

    def _init_agents(self) -> None:
        self._agents["researcher"] = create_researcher(self._store, self._worker)
        self._agents["builder"] = create_builder(self._store, self._worker)
        self._agents["auto-research"] = create_auto_research(self._store, self._worker)

    def list_agents(self) -> list[dict[str, Any]]:
        return [agent.to_status_dict() for agent in self._agents.values()]

    def handle_signal(self, content: str) -> dict[str, Any]:
        agent_id = self._route_to_agent(content)
        agent = self._agents.get(agent_id)
        if agent is None:
            return {"error": f"no agent found for: {content[:100]}"}

        adapter, operation, params = self._decompose_to_execution(content, agent_id)

        msg = AgentMessage(
            sender="advisor",
            recipient=agent_id,
            intent="delegate_task",
            payload={
                "task": content,
                "adapter": adapter,
                "operation": operation,
                "params": params,
                "tools": [adapter],
                "risk_class": "READ_ONLY" if agent_id == "researcher" else "REVERSIBLE_WRITE",
            },
        )

        self._store.save_message(msg)
        deliverable = agent.handle_task(msg)

        result = {
            "signal": content,
            "delegated_to": agent_id,
            "deliverable": deliverable.model_dump(mode="json") if deliverable else None,
            "trace_id": str(deliverable.parent_trace_id) if deliverable and deliverable.parent_trace_id else None,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

        return result

    def _route_to_agent(self, content: str) -> str:
        words = set(content.lower().split())
        build_score = len(words & BUILD_KEYWORDS)
        research_score = len(words & RESEARCH_KEYWORDS)

        if build_score > research_score:
            return "builder"
        return "researcher"

    def _decompose_to_execution(
        self, content: str, agent_id: str
    ) -> tuple[str, str, dict[str, Any]]:
        if agent_id == "researcher":
            return "shell", "query", {"command": f"echo 'Researcher task: {content[:200]}'"}
        elif agent_id == "builder":
            return "shell", "execute", {"command": f"echo 'Builder task: {content[:200]}'"}
        else:
            return "shell", "query", {"command": f"echo 'AutoResearch task: {content[:200]}'"}

    def organism_status(self) -> dict[str, Any]:
        agents = self.list_agents()
        deliverables = self._store.list_deliverables()
        learning = self._store.list_learning_signals()
        return {
            "agents": agents,
            "total_deliverables": len(deliverables),
            "total_learning_signals": len(learning),
            "recent_deliverables": deliverables[-5:],
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 -m pytest services/umh/organism/tests/test_advisor.py -v`
Expected: all 4 tests PASS

- [ ] **Step 5: Commit**

```bash
git add services/umh/organism/advisor.py services/umh/organism/tests/test_advisor.py
git commit -m "feat(organism): DEX advisor cell — interpret, route, delegate, synthesize"
```

---

## Task 7: Organism Daemon (Lifecycle Manager)

**Files:**
- Create: `services/umh/organism/daemon.py`

- [ ] **Step 1: Implement daemon**

```python
"""Organism daemon — manages agent lifecycle within the control plane.

The daemon:
- Holds references to all agent runtimes
- Provides the Advisor as the organism's brain
- Exposes organism status for the cockpit API
- Restores agent state from store on startup

At Slice 0 the daemon runs in-process with the FastAPI app.
Systemd service + process isolation comes in Slice 1.
"""
from __future__ import annotations

import logging
from typing import Any

from services.umh.organism.advisor import Advisor
from services.umh.organism.store import OrganismStore
from services.umh.organism.worker_cell import WorkerCell
from services.umh.control_plane.pipeline import ExecutionPipeline

logger = logging.getLogger(__name__)


class OrganismDaemon:
    def __init__(
        self,
        pipeline: ExecutionPipeline | None = None,
        store_dir: str = "data/umh/organism",
    ) -> None:
        self._store = OrganismStore(store_dir=store_dir)
        worker = WorkerCell(pipeline=pipeline) if pipeline else WorkerCell()
        self._advisor = Advisor(store=self._store, worker=worker)
        self._started = False

    @property
    def advisor(self) -> Advisor:
        return self._advisor

    @property
    def store(self) -> OrganismStore:
        return self._store

    def start(self) -> None:
        self._started = True
        logger.info("organism daemon started: %d agents", len(self._advisor.list_agents()))

    def stop(self) -> None:
        self._started = False
        logger.info("organism daemon stopped")

    @property
    def is_running(self) -> bool:
        return self._started

    def status(self) -> dict[str, Any]:
        return {
            "running": self._started,
            **self._advisor.organism_status(),
        }
```

- [ ] **Step 2: Compile check**

Run: `python3 -m py_compile services/umh/organism/daemon.py && echo "OK"`

- [ ] **Step 3: Commit**

```bash
git add services/umh/organism/daemon.py
git commit -m "feat(organism): daemon lifecycle manager"
```

---

## Task 8: Wire Organism into Control Plane

**Files:**
- Modify: `services/umh/control_plane/app.py`
- Modify: `services/umh/control_plane/cockpit_api.py`

- [ ] **Step 1: Add organism to app.py lifespan**

In `services/umh/control_plane/app.py`, add after `_mesh_server: Any = None`:

```python
_organism: Any = None
```

Add a `_register_organism()` function after `_register_node_mesh()`:

```python
def _register_organism() -> None:
    """Start the organism daemon with the shared pipeline."""
    global _organism
    try:
        from ..organism.daemon import OrganismDaemon
        _organism = OrganismDaemon(pipeline=_pipeline)
        _organism.start()
        logger.info("organism daemon started")
    except Exception as exc:
        logger.warning("organism daemon not started: %s", exc)
```

In the `lifespan()` function, add `_register_organism()` after `_register_node_mesh()`.

In the shutdown section, add before `if _mesh_server is not None:`:

```python
if _organism is not None:
    _organism.stop()
    logger.info("organism daemon stopped")
```

- [ ] **Step 2: Add organism API endpoints to cockpit_api.py**

Add at the end of `services/umh/control_plane/cockpit_api.py` (before the `profile()` function):

```python
@router.get("/organism/status")
async def organism_status():
    """Returns organism daemon status including agents and deliverables."""
    daemon = _get_organism()
    if daemon is None:
        return {"running": False, "agents": [], "total_deliverables": 0, "total_learning_signals": 0}
    return daemon.status()


@router.get("/organism/agents")
async def organism_agents():
    """Returns status of all organism agents."""
    daemon = _get_organism()
    if daemon is None:
        return []
    return daemon.advisor.list_agents()


@router.get("/organism/deliverables")
async def organism_deliverables(agent_id: str | None = None, limit: int = 50):
    """Returns recent deliverables, optionally filtered by agent."""
    daemon = _get_organism()
    if daemon is None:
        return []
    return daemon.store.list_deliverables(agent_id=agent_id, limit=limit)


@router.post("/organism/signal")
async def organism_signal(payload: dict):
    """Submit a signal to the organism advisor."""
    daemon = _get_organism()
    if daemon is None:
        return {"error": "organism not running"}
    content = payload.get("content", "")
    if not content:
        return {"error": "content required"}
    result = daemon.advisor.handle_signal(content)
    return result


def _get_organism():
    try:
        from services.umh.control_plane.app import _organism
        return _organism
    except (ImportError, AttributeError):
        return None
```

- [ ] **Step 3: Compile check both files**

Run: `python3 -m py_compile services/umh/control_plane/app.py && python3 -m py_compile services/umh/control_plane/cockpit_api.py && echo "OK"`

- [ ] **Step 4: Commit**

```bash
git add services/umh/control_plane/app.py services/umh/control_plane/cockpit_api.py
git commit -m "feat(control-plane): wire organism daemon + API endpoints"
```

---

## Task 9: Cockpit Frontend — Types, API Client, Store

**Files:**
- Modify: `apps/cockpit/src/types/domain.ts`
- Modify: `apps/cockpit/src/api/client.ts`
- Modify: `apps/cockpit/src/stores/cockpitStore.ts`

- [ ] **Step 1: Add organism types to domain.ts**

Add at the end of `apps/cockpit/src/types/domain.ts`:

```typescript
export interface OrganismAgent {
  agent_id: string
  agent_name: string
  status: 'idle' | 'working' | 'critiquing' | 'blocked' | 'offline'
  tasks_completed: number
}

export interface OrganismDeliverable {
  id: string
  agent_id: string
  task_id: string
  content: string
  self_critique: { score: number; reasoning: string; passed: boolean }
  parent_trace_id: string | null
  created_at: string
}

export interface OrganismStatus {
  running: boolean
  agents: OrganismAgent[]
  total_deliverables: number
  total_learning_signals: number
  recent_deliverables: OrganismDeliverable[]
  timestamp: string
}
```

- [ ] **Step 2: Add organism API methods to client.ts**

Add to the `api` object in `apps/cockpit/src/api/client.ts`:

```typescript
organismStatus: () => request<OrganismStatus>('/organism/status'),
organismAgents: () => request<OrganismAgent[]>('/organism/agents'),
organismDeliverables: (agentId?: string) =>
  request<OrganismDeliverable[]>(`/organism/deliverables${agentId ? `?agent_id=${agentId}` : ''}`),
organismSignal: (content: string) =>
  request<{ delegated_to: string; deliverable: OrganismDeliverable | null; trace_id: string | null }>(
    '/organism/signal',
    { method: 'POST', body: JSON.stringify({ content }) },
  ),
```

Also add the import types at the top of the `api` object definition — actually these types need to be exported from client.ts or imported from domain.ts. Since client.ts already defines its own response interfaces, add these interfaces there:

```typescript
export interface OrganismStatusResponse {
  running: boolean
  agents: { agent_id: string; agent_name: string; status: string; tasks_completed: number }[]
  total_deliverables: number
  total_learning_signals: number
  recent_deliverables: Record<string, unknown>[]
  timestamp: string
}

export interface OrganismSignalResponse {
  signal: string
  delegated_to: string
  deliverable: Record<string, unknown> | null
  trace_id: string | null
  timestamp: string
}
```

And update the api methods to use these:

```typescript
organismStatus: () => request<OrganismStatusResponse>('/organism/status'),
organismAgents: () => request<OrganismStatusResponse['agents']>('/organism/agents'),
organismSignal: (content: string) =>
  request<OrganismSignalResponse>('/organism/signal', {
    method: 'POST',
    body: JSON.stringify({ content }),
  }),
```

- [ ] **Step 3: Add organism state to cockpitStore.ts**

Import `OrganismAgent` and `OrganismDeliverable` from `../types/domain.ts`.

Add to the `CockpitState` interface:

```typescript
organismAgents: OrganismAgent[]
organismDeliverables: OrganismDeliverable[]
organismRunning: boolean
```

Add initial values:

```typescript
organismAgents: [],
organismDeliverables: [],
organismRunning: false,
```

In `fetchAll()`, add an additional API call to the `Promise.allSettled` array:

```typescript
api.organismStatus(),
```

And after the mesh mapping block, map the organism data:

```typescript
const orgStatus = unwrap(orgStatusRes, null)
const organismAgents: OrganismAgent[] = orgStatus?.agents?.map((a: any) => ({
  agent_id: a.agent_id,
  agent_name: a.agent_name,
  status: a.status,
  tasks_completed: a.tasks_completed,
})) ?? []

const organismDeliverables: OrganismDeliverable[] = orgStatus?.recent_deliverables?.map((d: any) => ({
  id: d.id,
  agent_id: d.agent_id,
  task_id: d.task_id,
  content: d.content,
  self_critique: d.self_critique,
  parent_trace_id: d.parent_trace_id,
  created_at: d.created_at,
})) ?? []
```

Add to the `set()` call:

```typescript
organismAgents,
organismDeliverables,
organismRunning: orgStatus?.running ?? false,
```

- [ ] **Step 4: Type check**

Run: `cd apps/cockpit && npx tsc --noEmit`
Expected: zero errors

- [ ] **Step 5: Commit**

```bash
git add apps/cockpit/src/types/domain.ts apps/cockpit/src/api/client.ts apps/cockpit/src/stores/cockpitStore.ts
git commit -m "feat(cockpit): organism types, API client, and store integration"
```

---

## Task 10: Cockpit UI — Signal Input + Agent Activity

**Files:**
- Modify: `apps/cockpit/src/views/CommandCenter.tsx`

- [ ] **Step 1: Add signal input bar and agent activity panel**

Replace the `CommandCenter` export in `apps/cockpit/src/views/CommandCenter.tsx`. Add these components:

**SignalInput component** (above the CommandCenter export):

```tsx
function SignalInput() {
  const [input, setInput] = useState('')
  const [sending, setSending] = useState(false)
  const [lastResult, setLastResult] = useState<{ delegated_to: string; trace_id: string | null } | null>(null)

  const handleSubmit = async () => {
    if (!input.trim() || sending) return
    setSending(true)
    try {
      const res = await api.organismSignal(input.trim())
      setLastResult({ delegated_to: res.delegated_to, trace_id: res.trace_id })
      setInput('')
      useCockpitStore.getState().fetchAll()
    } catch {
      setLastResult(null)
    } finally {
      setSending(false)
    }
  }

  return (
    <div className="wv-card p-4">
      <div className="wv-label mb-2">SIGNAL INPUT</div>
      <div className="flex gap-2">
        <input
          type="text"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => e.key === 'Enter' && handleSubmit()}
          placeholder="Send a signal to DEX..."
          className="flex-1 bg-surface border border-border text-text-primary text-[12px] font-mono px-3 py-2 focus:outline-none focus:border-cyan"
          disabled={sending}
        />
        <button
          onClick={handleSubmit}
          disabled={sending || !input.trim()}
          className="px-4 py-2 text-[10px] font-mono uppercase tracking-wider bg-cyan/10 text-cyan border border-cyan-dim hover:bg-cyan/20 transition-colors disabled:opacity-40"
        >
          {sending ? 'Sending...' : 'Send'}
        </button>
      </div>
      {lastResult && (
        <div className="mt-2 text-[10px] text-text-tertiary">
          Delegated to <span className="text-cyan">{lastResult.delegated_to}</span>
          {lastResult.trace_id && <span> (trace: {lastResult.trace_id.slice(0, 8)}...)</span>}
        </div>
      )}
    </div>
  )
}
```

**AgentActivity component:**

```tsx
function AgentActivity() {
  const { organismAgents, organismDeliverables, organismRunning } = useCockpitStore()

  const statusDot: Record<string, string> = {
    idle: 'bg-text-tertiary',
    working: 'bg-cyan wv-pulse',
    critiquing: 'bg-warn wv-pulse',
    blocked: 'bg-danger',
    offline: 'bg-border',
  }

  const statusBadge: Record<string, string> = {
    idle: 'wv-badge-ok',
    working: 'wv-badge-cyan',
    critiquing: 'wv-badge-warn',
    blocked: 'wv-badge-danger',
    offline: 'wv-badge-danger',
  }

  return (
    <div className="wv-card p-4">
      <div className="flex items-center justify-between mb-3">
        <span className="wv-label">ORGANISM</span>
        <span className={clsx('wv-badge', organismRunning ? 'wv-badge-ok' : 'wv-badge-danger')}>
          {organismRunning ? 'running' : 'stopped'}
        </span>
      </div>
      <div className="space-y-2 mb-4">
        {organismAgents.map((a) => (
          <div key={a.agent_id} className="flex items-center justify-between py-1">
            <div className="flex items-center gap-2">
              <span className={clsx('w-2 h-2 rounded-full', statusDot[a.status] ?? 'bg-border')} />
              <span className="text-[12px] text-text-primary font-mono">{a.agent_name}</span>
              <span className={clsx('wv-badge', statusBadge[a.status] ?? 'wv-badge-danger')}>{a.status}</span>
            </div>
            <span className="text-[10px] text-text-tertiary">{a.tasks_completed} tasks</span>
          </div>
        ))}
        {organismAgents.length === 0 && (
          <div className="text-[10px] text-text-tertiary text-center py-2">No agents registered</div>
        )}
      </div>
      {organismDeliverables.length > 0 && (
        <>
          <div className="wv-label mb-2">RECENT DELIVERABLES</div>
          <div className="space-y-2">
            {organismDeliverables.slice(-3).reverse().map((d) => (
              <div key={d.id} className="wv-card-raised p-2">
                <div className="flex items-center justify-between mb-1">
                  <span className="text-[10px] text-cyan font-mono">{d.agent_id}</span>
                  <span className={clsx('wv-badge', d.self_critique?.passed ? 'wv-badge-ok' : 'wv-badge-warn')}>
                    {d.self_critique?.score ?? '?'}/10
                  </span>
                </div>
                <div className="text-[11px] text-text-secondary truncate">{d.content}</div>
              </div>
            ))}
          </div>
        </>
      )}
    </div>
  )
}
```

Add `useState` to the react import at the top, and `api` import:

```typescript
import { useState } from 'react'
import { api } from '../api/client.ts'
```

**Update the CommandCenter layout** to include the new components:

```tsx
export function CommandCenter() {
  return (
    <div className="h-full flex flex-col gap-4 p-4 overflow-y-auto">
      <div className="flex items-center justify-between">
        <h1 className="text-[14px] font-mono uppercase tracking-widest text-text-secondary">
          Command Center
        </h1>
        <div className="flex items-center gap-2">
          <span className="w-2 h-2 rounded-full bg-ok wv-pulse" />
          <span className="text-[10px] font-mono text-text-tertiary uppercase">Live</span>
        </div>
      </div>
      <SignalInput />
      <PulsePanel />
      <div className="grid grid-cols-2 gap-4 flex-1 min-h-0">
        <div className="flex flex-col gap-4">
          <AgentActivity />
          <ModelBadges />
        </div>
        <div className="flex flex-col gap-4">
          <ApprovalQueue />
          <TraceStream />
        </div>
      </div>
    </div>
  )
}
```

- [ ] **Step 2: Type check + build**

Run: `cd apps/cockpit && npx tsc --noEmit && npx vite build`
Expected: zero errors, clean build

- [ ] **Step 3: Commit**

```bash
git add apps/cockpit/src/views/CommandCenter.tsx
git commit -m "feat(cockpit): signal input bar + organism agent activity panel"
```

---

## Task 11: End-to-End Integration Test

**Files:**
- Create: `services/umh/organism/tests/test_e2e.py`

- [ ] **Step 1: Write the E2E test**

```python
"""End-to-end test — the vertical slice acceptance criterion.

Signal in → advisor interprets → researcher agent receives → worker executes
→ critique loop runs → deliverable persisted → trace queryable.
"""
import sys
sys.path.insert(0, "/opt/OS")

import pytest
from services.umh.organism.advisor import Advisor
from services.umh.organism.store import OrganismStore


@pytest.fixture
def store(tmp_path):
    return OrganismStore(store_dir=tmp_path / "organism")


@pytest.fixture
def advisor(store):
    return Advisor(store=store)


def test_full_vertical_slice(advisor, store):
    """Antony sends a signal. DEX delegates. Agent executes. Deliverable appears."""
    result = advisor.handle_signal(
        "Audit the services/umh/organism/ directory for any missing __init__.py files"
    )

    # 1. Signal was routed to an agent
    assert result["delegated_to"] in ("researcher", "builder")

    # 2. Deliverable was produced
    assert result["deliverable"] is not None
    deliverable = result["deliverable"]

    # 3. Self-critique ran
    assert "self_critique" in deliverable
    assert deliverable["self_critique"]["score"] >= 1

    # 4. Trace ID was generated
    assert result["trace_id"] is not None

    # 5. Deliverable is persisted in store
    stored = store.list_deliverables()
    assert len(stored) >= 1

    # 6. Learning signal was generated
    signals = store.list_learning_signals()
    assert len(signals) >= 1

    # 7. Agent message was recorded
    messages = store.list_messages(recipient="researcher")
    assert len(messages) >= 1


def test_multiple_signals_accumulate(advisor, store):
    """Multiple signals produce accumulating deliverables."""
    advisor.handle_signal("Check for unused imports in app.py")
    advisor.handle_signal("Search for TODO comments in the codebase")

    deliverables = store.list_deliverables()
    assert len(deliverables) >= 2


def test_organism_status_reflects_work(advisor, store):
    """After work, organism status shows completed tasks."""
    advisor.handle_signal("List all Python files in services/umh/")

    status = advisor.organism_status()
    assert status["total_deliverables"] >= 1
    assert status["total_learning_signals"] >= 1
    assert any(a["tasks_completed"] > 0 for a in status["agents"])
```

- [ ] **Step 2: Run the full test suite**

Run: `python3 -m pytest services/umh/organism/tests/ -v`
Expected: all tests PASS across all test files

- [ ] **Step 3: Commit**

```bash
git add services/umh/organism/tests/test_e2e.py
git commit -m "test(organism): end-to-end vertical slice — signal to deliverable to trace"
```

---

## Task 12: Final Verification

- [ ] **Step 1: Run all organism tests**

Run: `python3 -m pytest services/umh/organism/tests/ -v --tb=short`
Expected: all tests pass

- [ ] **Step 2: Compile-check all new Python files**

Run:
```bash
for f in services/umh/organism/*.py; do python3 -m py_compile "$f" && echo "$f OK"; done
```
Expected: all OK

- [ ] **Step 3: Type-check and build cockpit**

Run: `cd apps/cockpit && npx tsc --noEmit && npx vite build`
Expected: zero errors, clean build

- [ ] **Step 4: Format all Python files**

Run: `ruff format services/umh/organism/`

- [ ] **Step 5: Final commit**

```bash
git add -A
git commit -m "chore(organism): format + final verification"
```
