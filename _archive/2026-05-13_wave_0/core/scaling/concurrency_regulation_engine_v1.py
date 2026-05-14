"""Concurrency Regulation Engine v1.

Enforces:
  max concurrent traversals, environment concurrency ceilings,
  workflow concurrency ceilings, session concurrency ceilings,
  operational concurrency ceilings.

Prevents:
  concurrency storms, recursive fanout, hidden parallelism.

UMH substrate subsystem. Phase 96.8BY.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from core.scaling.operational_scaling_contracts_v1 import (
    CapacityAllocationDecision,
    ConcurrencyWindow,
    _content_hash,
    _now_iso,
)


DEFAULT_CONCURRENCY_LIMITS: dict[str, int] = {
    "global": 5,
    "per_environment": 3,
    "per_workflow": 2,
    "per_session": 2,
    "per_campaign": 3,
}


class ConcurrencyRegulationEngine:
    """Enforces bounded concurrency across all dimensions."""

    def __init__(
        self,
        state_dir: str | Path = "data/runtime/scaling",
        overrides: dict[str, int] | None = None,
    ) -> None:
        self._state_dir = Path(state_dir)
        self._state_dir.mkdir(parents=True, exist_ok=True)
        self._limits = dict(DEFAULT_CONCURRENCY_LIMITS)
        if overrides:
            for key, val in overrides.items():
                if key in self._limits:
                    self._limits[key] = min(val, self._limits[key])

        self._global_active: int = 0
        self._environment_active: dict[str, int] = {}
        self._workflow_active: dict[str, int] = {}
        self._session_active: dict[str, int] = {}
        self._decisions: list[CapacityAllocationDecision] = []
        self._total_grants: int = 0
        self._total_denials: int = 0

    def request_slot(
        self,
        item_id: str = "",
        environment_id: str = "",
        workflow_id: str = "",
        session_id: str = "",
        pressure_score: float = 0.0,
    ) -> CapacityAllocationDecision:
        if self._global_active >= self._limits["global"]:
            return self._deny(item_id, "global_limit_reached", pressure_score)

        if environment_id:
            env_active = self._environment_active.get(environment_id, 0)
            if env_active >= self._limits["per_environment"]:
                return self._deny(item_id, "environment_limit_reached", pressure_score)

        if workflow_id:
            wf_active = self._workflow_active.get(workflow_id, 0)
            if wf_active >= self._limits["per_workflow"]:
                return self._deny(item_id, "workflow_limit_reached", pressure_score)

        if session_id:
            sess_active = self._session_active.get(session_id, 0)
            if sess_active >= self._limits["per_session"]:
                return self._deny(item_id, "session_limit_reached", pressure_score)

        self._global_active += 1
        if environment_id:
            self._environment_active[environment_id] = (
                self._environment_active.get(environment_id, 0) + 1
            )
        if workflow_id:
            self._workflow_active[workflow_id] = (
                self._workflow_active.get(workflow_id, 0) + 1
            )
        if session_id:
            self._session_active[session_id] = (
                self._session_active.get(session_id, 0) + 1
            )

        self._total_grants += 1
        decision = CapacityAllocationDecision(
            item_id=item_id,
            allocated=True,
            reason="granted",
            concurrency_at_decision=self._global_active,
            queue_depth_at_decision=0,
            pressure_at_decision=pressure_score,
        )
        self._decisions.append(decision)
        self._persist_decision(decision)
        return decision

    def release_slot(
        self,
        environment_id: str = "",
        workflow_id: str = "",
        session_id: str = "",
    ) -> None:
        self._global_active = max(0, self._global_active - 1)
        if environment_id and environment_id in self._environment_active:
            self._environment_active[environment_id] = max(
                0, self._environment_active[environment_id] - 1,
            )
        if workflow_id and workflow_id in self._workflow_active:
            self._workflow_active[workflow_id] = max(
                0, self._workflow_active[workflow_id] - 1,
            )
        if session_id and session_id in self._session_active:
            self._session_active[session_id] = max(
                0, self._session_active[session_id] - 1,
            )

    def get_window(self) -> ConcurrencyWindow:
        return ConcurrencyWindow(
            max_concurrent=self._limits["global"],
            current_active=self._global_active,
            environment_limits=dict(self._environment_active),
            workflow_limits=dict(self._workflow_active),
            session_limits=dict(self._session_active),
        )

    def get_concurrency_hash(self) -> str:
        return _content_hash([d.to_dict() for d in self._decisions])

    def _deny(
        self,
        item_id: str,
        reason: str,
        pressure_score: float,
    ) -> CapacityAllocationDecision:
        self._total_denials += 1
        decision = CapacityAllocationDecision(
            item_id=item_id,
            allocated=False,
            reason=reason,
            concurrency_at_decision=self._global_active,
            pressure_at_decision=pressure_score,
        )
        self._decisions.append(decision)
        self._persist_decision(decision)
        return decision

    def _persist_decision(self, decision: CapacityAllocationDecision) -> None:
        path = self._state_dir / "concurrency_decisions.jsonl"
        with path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(decision.to_dict(), default=str) + "\n")

    def get_stats(self) -> dict[str, Any]:
        return {
            "global_active": self._global_active,
            "total_grants": self._total_grants,
            "total_denials": self._total_denials,
            "limits": dict(self._limits),
        }
