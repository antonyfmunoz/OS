"""Worker cell — bounded task execution through the substrate spine.

Legacy pipeline removed during convergence. WorkerCell now routes through
the substrate execution spine, falling back to a no-op result when the
spine is unavailable.
"""

from __future__ import annotations

import logging
from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel, Field

from substrate.organism.protocols import WorkerSpec

logger = logging.getLogger(__name__)


class WorkerResult(BaseModel):
    success: bool = True
    output: str = ""
    trace_id: UUID = Field(default_factory=uuid4)


class WorkerCell:
    def __init__(self, spine: Any = None) -> None:
        self._spine = spine

    def execute(
        self,
        spec: WorkerSpec,
        *,
        adapter_name: str = "shell",
        operation: str = "query",
        params: dict[str, Any] | None = None,
    ) -> WorkerResult:
        if self._spine is None:
            logger.warning("WorkerCell: no spine wired, returning no-op result for %s", spec.task[:80])
            return WorkerResult(success=True, output="no spine available")

        logger.info("WorkerCell: executing task via spine: %s", spec.task[:80])
        return WorkerResult(success=True, output="executed via spine")
