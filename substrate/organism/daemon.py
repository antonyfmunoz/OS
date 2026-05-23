"""Organism daemon — manages agent lifecycle within the control plane."""

from __future__ import annotations

import logging
from typing import Any

from substrate.organism.advisor import Advisor
from substrate.organism.approval_store import ApprovalStore
from substrate.organism.store import OrganismStore
from substrate.organism.worker_cell import WorkerCell

logger = logging.getLogger(__name__)

_RISK_DECISION_MAP: dict[str, str] = {
    "DENY": "high",
    "ESCALATE": "critical",
    "DEFER": "medium",
}


def _map_risk_level(data: dict[str, Any]) -> str:
    decision = data.get("decision", "")
    return _RISK_DECISION_MAP.get(decision, "medium")


class OrganismDaemon:
    def __init__(
        self,
        spine: Any = None,
        store_dir: str = "data/umh/organism",
        view_socket: Any = None,
    ) -> None:
        self._store = OrganismStore(store_dir=store_dir)
        self._approval_store = ApprovalStore(store_dir=store_dir)
        self._spine = spine
        worker = WorkerCell(spine=spine)
        self._advisor = Advisor(store=self._store, worker=worker, view_socket=view_socket)
        self._view_socket = view_socket
        self._started = False

    @property
    def advisor(self) -> Advisor:
        return self._advisor

    @property
    def store(self) -> OrganismStore:
        return self._store

    @property
    def approval_store(self) -> ApprovalStore:
        return self._approval_store

    def start(self) -> None:
        self._started = True
        logger.info("organism daemon started: %d agents", len(self._advisor.list_agents()))

    def _on_pipeline_event(self, event_type: str, data: dict[str, Any]) -> None:
        if event_type == "governance" and not data.get("approved", True):
            self._approval_store.create_approval(
                title=f"Governance blocked: {data.get('decision', 'unknown')}",
                description=data.get("rationale", "No rationale provided"),
                agent="governance",
                risk_level=_map_risk_level(data),
                trace_id=data.get("verdict_id"),
                governance_rationale=data.get("rationale", ""),
            )

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
