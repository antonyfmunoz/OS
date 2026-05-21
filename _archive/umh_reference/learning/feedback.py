"""Execution feedback — records job outcomes for scheduling adaptation.

Feedback is recorded AFTER job completion. Immutable once created.
The store maintains insertion order for deterministic replay.

No imports from umh/cells, umh/environments, umh/adapters, subprocess, or shell.
"""

from __future__ import annotations

import threading
from dataclasses import dataclass, field
from typing import Any

from umh.core.clock import iso_now as _iso_now


@dataclass(frozen=True)
class ExecutionFeedback:
    """Immutable record of a completed job's execution outcome."""

    job_id: str
    node_id: str
    task_type: str
    success: bool
    duration_ms: int
    retries: int = 0
    resource_usage: dict[str, float] = field(default_factory=dict)
    timestamp: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.timestamp:
            object.__setattr__(self, "timestamp", _iso_now())

    def to_dict(self) -> dict[str, Any]:
        return {
            "job_id": self.job_id,
            "node_id": self.node_id,
            "task_type": self.task_type,
            "success": self.success,
            "duration_ms": self.duration_ms,
            "retries": self.retries,
            "resource_usage": self.resource_usage,
            "timestamp": self.timestamp,
            "metadata": self.metadata,
        }


_MAX_FEEDBACK_RECORDS = 10000


class FeedbackStore:
    """Thread-safe ordered collection of execution feedback.

    Maintains insertion order for deterministic replay. Automatically
    evicts oldest records when the limit is reached.
    """

    def __init__(self, max_records: int = _MAX_FEEDBACK_RECORDS) -> None:
        self._lock = threading.Lock()
        self._records: list[ExecutionFeedback] = []
        self._by_node: dict[str, list[ExecutionFeedback]] = {}
        self._by_task_type: dict[str, list[ExecutionFeedback]] = {}
        self._max_records = max_records

    def record(self, feedback: ExecutionFeedback) -> None:
        """Record a feedback entry. Thread-safe."""
        with self._lock:
            self._records.append(feedback)
            self._by_node.setdefault(feedback.node_id, []).append(feedback)
            self._by_task_type.setdefault(feedback.task_type, []).append(feedback)

            if len(self._records) > self._max_records:
                removed = self._records.pop(0)
                node_list = self._by_node.get(removed.node_id, [])
                if removed in node_list:
                    node_list.remove(removed)
                type_list = self._by_task_type.get(removed.task_type, [])
                if removed in type_list:
                    type_list.remove(removed)

    def get_for_node(self, node_id: str) -> list[ExecutionFeedback]:
        with self._lock:
            return list(self._by_node.get(node_id, []))

    def get_for_task_type(self, task_type: str) -> list[ExecutionFeedback]:
        with self._lock:
            return list(self._by_task_type.get(task_type, []))

    def get_all(self) -> list[ExecutionFeedback]:
        with self._lock:
            return list(self._records)

    @property
    def total(self) -> int:
        with self._lock:
            return len(self._records)

    @property
    def node_ids(self) -> list[str]:
        with self._lock:
            return list(self._by_node.keys())

    @property
    def task_types(self) -> list[str]:
        with self._lock:
            return list(self._by_task_type.keys())

    def clear(self) -> None:
        with self._lock:
            self._records.clear()
            self._by_node.clear()
            self._by_task_type.clear()
