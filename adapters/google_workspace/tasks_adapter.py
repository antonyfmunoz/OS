"""Google Tasks adapter — thin wrapper over GWSConnector task methods.

Provides list/create/complete/update operations with typed returns.
Uses GWSConnector's gws CLI integration under the hood.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class TaskItem:
    id: str
    title: str
    notes: str = ""
    status: str = "needsAction"
    due: str = ""
    completed: str = ""
    updated: str = ""
    parent: str = ""
    position: str = ""
    links: list[dict[str, str]] = field(default_factory=list)

    @classmethod
    def from_api(cls, data: dict[str, Any]) -> TaskItem:
        return cls(
            id=data.get("id", ""),
            title=data.get("title", ""),
            notes=data.get("notes", ""),
            status=data.get("status", "needsAction"),
            due=data.get("due", ""),
            completed=data.get("completed", ""),
            updated=data.get("updated", ""),
            parent=data.get("parent", ""),
            position=data.get("position", ""),
            links=data.get("links", []),
        )

    @property
    def is_completed(self) -> bool:
        return self.status == "completed"


class GoogleTasksAdapter:
    """Adapter for Google Tasks API via GWSConnector."""

    def __init__(self) -> None:
        from adapters.google_workspace.gws_connector import GWSConnector

        self._gws = GWSConnector()

    def list_tasks(self, max_results: int = 100) -> list[TaskItem]:
        try:
            raw = self._gws.get_tasks()
            return [TaskItem.from_api(t) for t in raw[:max_results]]
        except Exception as e:
            logger.error("GoogleTasksAdapter.list_tasks failed: %s", e)
            return []

    def create_task(self, title: str, notes: str = "", due: str = "") -> TaskItem | None:
        try:
            result = self._gws.create_task(title=title, notes=notes, due=due)
            if result:
                return TaskItem.from_api(result)
            return None
        except Exception as e:
            logger.error("GoogleTasksAdapter.create_task failed: %s", e)
            return None

    def complete_task(self, task_id: str) -> bool:
        try:
            return self._gws.complete_task(task_id)
        except Exception as e:
            logger.error("GoogleTasksAdapter.complete_task failed: %s", e)
            return False

    def get_pending(self) -> list[TaskItem]:
        return [t for t in self.list_tasks() if not t.is_completed]

    def get_overdue(self) -> list[TaskItem]:
        now = datetime.now(timezone.utc).isoformat()
        return [t for t in self.list_tasks() if not t.is_completed and t.due and t.due < now]
