"""Tests for C27 self-use task catalog."""

from __future__ import annotations

import json
import os
import sys
import tempfile

sys.path.insert(0, "/opt/OS")

from substrate.organism.self_use.task_catalog import (
    SelfUseTask,
    TaskCatalog,
    TaskResult,
    TaskStatus,
)
from substrate.organism.self_use.task_taxonomy import (
    CoherenceDomain,
    StreamType,
    TaskDomain,
)


def test_task_roundtrip():
    task = SelfUseTask(
        task_id="c27-test-001",
        title="Test task",
        description="A test task",
        stream=StreamType.PRODUCTION,
        domain=TaskDomain.IMPLEMENTATION,
        projection="CreatorOS",
        surfaces=["cockpit", "meta_ide"],
    )
    d = task.to_dict()
    assert d["task_id"] == "c27-test-001"
    assert d["stream"] == "production"
    assert d["domain"] == "implementation"

    restored = SelfUseTask.from_dict(d)
    assert restored.task_id == task.task_id
    assert restored.stream == StreamType.PRODUCTION
    assert restored.domain == TaskDomain.IMPLEMENTATION
    assert restored.surfaces == ["cockpit", "meta_ide"]


def test_task_coherence_domain():
    task = SelfUseTask(
        task_id="c27-coh-001",
        stream=StreamType.COHERENCE,
        domain=CoherenceDomain.CONTINUITY,
    )
    d = task.to_dict()
    assert d["domain"] == "continuity"

    restored = SelfUseTask.from_dict(d)
    assert restored.domain == CoherenceDomain.CONTINUITY


def test_catalog_from_json():
    worktree = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    catalog = TaskCatalog.from_json(os.path.join(worktree, "data", "umh", "c27_task_catalog.json"))
    assert len(catalog.tasks) > 0


def test_catalog_by_stream():
    worktree = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    catalog = TaskCatalog.from_json(os.path.join(worktree, "data", "umh", "c27_task_catalog.json"))
    production = catalog.by_stream(StreamType.PRODUCTION)
    coherence = catalog.by_stream(StreamType.COHERENCE)
    reality = catalog.by_stream(StreamType.REALITY)
    audit = catalog.by_stream(StreamType.META_IDE_AUDIT)

    assert len(production) > 0
    assert len(coherence) > 0
    assert len(reality) > 0
    assert len(audit) > 0
    assert len(production) + len(coherence) + len(reality) + len(audit) == len(catalog.tasks)


def test_catalog_by_projection():
    worktree = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    catalog = TaskCatalog.from_json(os.path.join(worktree, "data", "umh", "c27_task_catalog.json"))
    cos = catalog.by_projection("CreatorOS")
    eos = catalog.by_projection("EntrepreneurOS")
    assert len(cos) > 0
    assert len(eos) > 0


def test_catalog_record_result():
    catalog = TaskCatalog(
        tasks=[
            SelfUseTask(task_id="t1", stream=StreamType.PRODUCTION),
            SelfUseTask(task_id="t2", stream=StreamType.PRODUCTION),
        ]
    )
    result = TaskResult(task_id="t1", status=TaskStatus.COMPLETED, surfaces_exercised=["cockpit"])
    catalog.record_result(result)
    assert catalog.get("t1").status == TaskStatus.COMPLETED
    assert catalog.completion_rate() == 0.5


def test_catalog_surface_coverage():
    catalog = TaskCatalog(
        tasks=[
            SelfUseTask(task_id="t1"),
        ]
    )
    catalog.record_result(
        TaskResult(
            task_id="t1",
            surfaces_exercised=["cockpit", "meta_ide", "cockpit"],
        )
    )
    coverage = catalog.surface_coverage()
    assert coverage["cockpit"] == 2
    assert coverage["meta_ide"] == 1


def test_catalog_summary():
    worktree = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    catalog = TaskCatalog.from_json(os.path.join(worktree, "data", "umh", "c27_task_catalog.json"))
    summary = catalog.summary()
    assert summary["total_tasks"] > 0
    assert "by_stream" in summary
    assert "by_status" in summary


def test_catalog_missing_file():
    catalog = TaskCatalog.from_json("/nonexistent/path.json")
    assert len(catalog.tasks) == 0


def test_task_result_roundtrip():
    result = TaskResult(
        task_id="t1",
        status=TaskStatus.COMPLETED,
        surfaces_exercised=["cockpit"],
        coherence_preserved=True,
        gap_ids=["gap-001"],
        notes="All good",
        duration_seconds=12.5,
    )
    d = result.to_dict()
    assert d["task_id"] == "t1"
    assert d["surfaces_exercised"] == ["cockpit"]
    assert d["duration_seconds"] == 12.5
