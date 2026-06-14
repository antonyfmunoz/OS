"""Tests for Runtime State Registry — Phase 16.

Validates:
  - Snapshot creation and immutability
  - Store bounded retention (FIFO eviction)
  - Collector functions
  - Registry query surface
  - Refresher lifecycle
  - Domain model serialization
  - Singleton management
"""

from __future__ import annotations

import sys
import threading
import time

sys.path.insert(0, "/opt/OS")

import pytest

from substrate.organism.runtime_state_registry import (
    ContainerInfo,
    ExecutionInfo,
    GitRepoInfo,
    ProcessInfo,
    RuntimeSnapshot,
    RuntimeStateRefresher,
    RuntimeStateRegistry,
    RuntimeStateStore,
    WorktreeInfo,
    collect_containers,
    collect_executions,
    collect_git_info,
    collect_processes,
    collect_worktrees,
    get_runtime_state_registry,
    reset_runtime_state_registry,
)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Domain Model Tests
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


def test_worktree_info_frozen():
    wt = WorktreeInfo(
        worktree_id="abc",
        path="/opt/OS",
        branch="main",
    )
    with pytest.raises(AttributeError):
        wt.path = "/other"  # type: ignore[misc]


def test_worktree_info_to_dict():
    wt = WorktreeInfo(
        worktree_id="abc",
        path="/opt/OS",
        branch="main",
        is_bare=False,
        executor_owner="test",
    )
    d = wt.to_dict()
    assert d["worktree_id"] == "abc"
    assert d["path"] == "/opt/OS"
    assert d["branch"] == "main"
    assert d["executor_owner"] == "test"


def test_git_repo_info_to_dict():
    repo = GitRepoInfo(
        repository="/opt/OS",
        current_branch="main",
        dirty=True,
        untracked_count=3,
        last_commit_hash="abc123",
        last_commit_message="test commit",
    )
    d = repo.to_dict()
    assert d["dirty"] is True
    assert d["untracked_count"] == 3
    assert d["last_commit_hash"] == "abc123"


def test_process_info_to_dict():
    proc = ProcessInfo(
        pid=1234,
        command="python3 test.py",
        started_at=1000.0,
        cpu_percent=5.2,
        memory_mb=128.5,
    )
    d = proc.to_dict()
    assert d["pid"] == 1234
    assert d["cpu_percent"] == 5.2


def test_container_info_to_dict():
    c = ContainerInfo(
        container_id="abc123",
        name="os-discord",
        status="Up 2 hours",
        image="os-discord:latest",
    )
    d = c.to_dict()
    assert d["name"] == "os-discord"
    assert d["status"] == "Up 2 hours"


def test_execution_info_to_dict():
    e = ExecutionInfo(
        execution_id="exec-1",
        status="executing",
        executor_type="workstation",
        started_at=1000.0,
        duration_seconds=5.5,
    )
    d = e.to_dict()
    assert d["execution_id"] == "exec-1"
    assert d["duration_seconds"] == 5.5


def test_snapshot_immutable():
    snap = RuntimeSnapshot(
        snapshot_id="snap-1",
        timestamp=time.time(),
        worktrees=(),
        repositories=(),
        processes=(),
        containers=(),
        executions=(),
    )
    with pytest.raises(AttributeError):
        snap.timestamp = 0.0  # type: ignore[misc]


def test_snapshot_to_dict_summary():
    snap = RuntimeSnapshot(
        snapshot_id="snap-1",
        timestamp=1000.0,
        worktrees=(
            WorktreeInfo(worktree_id="w1", path="/a", branch="main"),
        ),
        repositories=(),
        processes=(
            ProcessInfo(pid=1, command="python", started_at=0, cpu_percent=1.0, memory_mb=50),
            ProcessInfo(pid=2, command="node", started_at=0, cpu_percent=2.0, memory_mb=100),
        ),
        containers=(),
        executions=(),
    )
    d = snap.to_dict()
    assert d["snapshot_id"] == "snap-1"
    assert d["summary"]["worktree_count"] == 1
    assert d["summary"]["process_count"] == 2
    assert d["summary"]["container_count"] == 0
    assert len(d["worktrees"]) == 1
    assert len(d["processes"]) == 2


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Store Tests
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


def _make_snap(sid: str = "s1") -> RuntimeSnapshot:
    return RuntimeSnapshot(
        snapshot_id=sid,
        timestamp=time.time(),
        worktrees=(),
        repositories=(),
        processes=(),
        containers=(),
        executions=(),
    )


def test_store_empty():
    store = RuntimeStateStore()
    assert store.latest() is None
    assert store.count() == 0
    assert store.all() == []


def test_store_append_and_latest():
    store = RuntimeStateStore()
    s1 = _make_snap("s1")
    store.append(s1)
    assert store.latest() is s1
    assert store.count() == 1


def test_store_bounded_eviction():
    store = RuntimeStateStore(max_size=5)
    for i in range(10):
        store.append(_make_snap(f"s{i}"))
    assert store.count() == 5
    latest = store.latest()
    assert latest is not None
    assert latest.snapshot_id == "s9"
    oldest = store.all()[0]
    assert oldest.snapshot_id == "s5"


def test_store_clear():
    store = RuntimeStateStore()
    store.append(_make_snap())
    store.clear()
    assert store.count() == 0
    assert store.latest() is None


def test_store_thread_safety():
    store = RuntimeStateStore(max_size=50)
    errors: list[str] = []

    def writer(prefix: str) -> None:
        for i in range(20):
            try:
                store.append(_make_snap(f"{prefix}-{i}"))
            except Exception as exc:
                errors.append(str(exc))

    threads = [threading.Thread(target=writer, args=(f"t{i}",)) for i in range(4)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert not errors
    assert store.count() <= 50


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Collector Tests
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


def test_collect_worktrees_returns_tuple():
    result = collect_worktrees()
    assert isinstance(result, tuple)
    for wt in result:
        assert isinstance(wt, WorktreeInfo)
        assert wt.path
        assert wt.branch


def test_collect_git_info_returns_tuple():
    result = collect_git_info()
    assert isinstance(result, tuple)
    if result:
        repo = result[0]
        assert isinstance(repo, GitRepoInfo)
        assert repo.repository
        assert repo.current_branch


def test_collect_processes_returns_tuple():
    result = collect_processes()
    assert isinstance(result, tuple)
    for p in result:
        assert isinstance(p, ProcessInfo)
        assert p.pid > 0


def test_collect_containers_returns_tuple():
    result = collect_containers()
    assert isinstance(result, tuple)
    for c in result:
        assert isinstance(c, ContainerInfo)


def test_collect_executions_returns_tuple():
    result = collect_executions()
    assert isinstance(result, tuple)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Refresher Tests
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


def test_refresher_once():
    store = RuntimeStateStore()
    refresher = RuntimeStateRefresher(store, interval=60.0)
    snap = refresher.refresh_once()
    assert isinstance(snap, RuntimeSnapshot)
    assert store.count() == 1
    assert store.latest() is snap


def test_refresher_start_stop():
    store = RuntimeStateStore()
    refresher = RuntimeStateRefresher(store, interval=0.1)
    assert not refresher.running
    refresher.start()
    assert refresher.running
    time.sleep(0.35)
    refresher.stop()
    assert not refresher.running
    assert store.count() >= 2


def test_refresher_idempotent_start():
    store = RuntimeStateStore()
    refresher = RuntimeStateRefresher(store, interval=60.0)
    refresher.start()
    refresher.start()
    assert refresher.running
    refresher.stop()


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Registry Tests
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


def test_registry_get_runtime_state():
    registry = RuntimeStateRegistry()
    state = registry.get_runtime_state()
    assert "snapshot_id" in state
    assert "summary" in state
    assert "worktrees" in state
    assert "processes" in state
    assert "containers" in state
    assert "executions" in state
    registry.stop()


def test_registry_refresh():
    registry = RuntimeStateRegistry()
    snap = registry.refresh()
    assert isinstance(snap, RuntimeSnapshot)
    assert registry.snapshot_count() >= 1
    registry.stop()


def test_registry_query_methods():
    registry = RuntimeStateRegistry()
    registry.refresh()
    assert isinstance(registry.get_worktrees(), list)
    assert isinstance(registry.get_processes(), list)
    assert isinstance(registry.get_containers(), list)
    assert isinstance(registry.get_executions(), list)
    assert isinstance(registry.get_repositories(), list)
    registry.stop()


def test_registry_snapshot_history():
    registry = RuntimeStateRegistry()
    for _ in range(3):
        registry.refresh()
    history = registry.snapshot_history(limit=2)
    assert len(history) == 2
    for entry in history:
        assert "snapshot_id" in entry
        assert "summary" in entry
    registry.stop()


def test_registry_empty_queries():
    registry = RuntimeStateRegistry()
    assert registry.get_worktrees() == []
    assert registry.get_processes() == []
    assert registry.get_containers() == []
    assert registry.get_executions() == []
    registry.stop()


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Singleton Tests
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


def test_singleton_same_instance():
    reset_runtime_state_registry()
    r1 = get_runtime_state_registry()
    r2 = get_runtime_state_registry()
    assert r1 is r2
    reset_runtime_state_registry()


def test_singleton_reset():
    reset_runtime_state_registry()
    r1 = get_runtime_state_registry()
    reset_runtime_state_registry()
    r2 = get_runtime_state_registry()
    assert r1 is not r2
    reset_runtime_state_registry()


def test_singleton_thread_safe():
    reset_runtime_state_registry()
    instances: list[RuntimeStateRegistry] = []

    def get_instance() -> None:
        instances.append(get_runtime_state_registry())

    threads = [threading.Thread(target=get_instance) for _ in range(10)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert len(set(id(i) for i in instances)) == 1
    reset_runtime_state_registry()


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# API Route Tests (import-level)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


def test_route_module_imports():
    from transports.api.runtime_state_routes import (
        runtime_containers,
        runtime_executions,
        runtime_history,
        runtime_processes,
        runtime_snapshot_latest,
        runtime_state,
        runtime_worktrees,
    )
    assert callable(runtime_state)
    assert callable(runtime_snapshot_latest)
    assert callable(runtime_executions)
    assert callable(runtime_processes)
    assert callable(runtime_worktrees)
    assert callable(runtime_containers)
    assert callable(runtime_history)
