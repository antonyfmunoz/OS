"""Organism daemon — manages agent lifecycle within the control plane."""

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
