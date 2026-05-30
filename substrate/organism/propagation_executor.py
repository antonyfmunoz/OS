"""Propagation Executor — executes propagation plans in dry-run or governed mode.

Phase 12.0 uses dry_run and recompute_only modes only. No production
mutation occurs from propagation execution in this phase.

Phase 12.0. UMH substrate subsystem. Instance-agnostic.
"""

from __future__ import annotations

import json
import logging
import os
import time
from typing import Any
from uuid import uuid4

from substrate.organism.change_event import (
    PropagationPlan,
    PropagationAction,
    PropagationActionStatus,
    PropagationResult,
    persist_propagation_results,
)
from substrate.organism.propagation_graph import PropagationGraph

logger = logging.getLogger(__name__)

_REPO_ROOT = os.environ.get("UMH_ROOT", "/opt/OS")

_SAFE_DRY_RUN_ACTIONS = frozenset({
    "no_op", "notify", "recompute", "revalidate",
})


class ExecutionMode:
    DRY_RUN = "dry_run"
    RECOMPUTE_ONLY = "recompute_only"
    NOTIFY_ONLY = "notify_only"
    GOVERNED = "governed_execution"


class PropagationExecutor:
    """Executes propagation plans with wave ordering and failure isolation."""

    def __init__(
        self,
        graph: PropagationGraph,
        mode: str = ExecutionMode.DRY_RUN,
    ) -> None:
        self._graph = graph
        self._mode = mode
        self._idempotency_cache: set[str] = set()

    def execute(self, plan: PropagationPlan) -> PropagationResult:
        start = time.time()
        result = PropagationResult(
            result_id=f"pr-{uuid4().hex[:12]}",
            plan_id=plan.plan_id,
            change_event_id=plan.change_event_id,
            status="executing",
        )

        for wave in plan.propagation_waves:
            wave_result = self._execute_wave(wave, result)
            result.wave_results.append(wave_result)

            has_failures = any(
                a.get("status") == "failed"
                for a in wave_result.get("action_results", [])
            )
            if has_failures and wave.reconvergence_required:
                result.reconvergence_results.append({
                    "wave_id": wave.wave_id,
                    "wave_number": wave.wave_number,
                    "status": "reconvergence_blocked_by_failure",
                    "timestamp": time.time(),
                })

        result.duration_ms = (time.time() - start) * 1000

        if result.failed_actions:
            result.status = "partial"
        elif result.blocked_actions or result.approval_required_actions or result.human_required_actions:
            result.status = "completed_with_gates"
        else:
            result.status = "completed"

        return result

    def _execute_wave(
        self,
        wave: Any,
        result: PropagationResult,
    ) -> dict[str, Any]:
        wave_result: dict[str, Any] = {
            "wave_id": wave.wave_id,
            "wave_number": wave.wave_number,
            "action_results": [],
            "started_at": time.time(),
        }

        for action in wave.actions:
            action_result = self._execute_action(action)
            wave_result["action_results"].append(action_result)

            status = action_result.get("status", "")
            action_id = action.action_id
            if status == "completed" or status == "dry_run":
                result.completed_actions.append(action_id)
            elif status == "failed":
                result.failed_actions.append(action_id)
            elif status == "blocked":
                result.blocked_actions.append(action_id)
            elif status == "approval_required":
                result.approval_required_actions.append(action_id)
            elif status == "human_required":
                result.human_required_actions.append(action_id)
            elif status == "skipped":
                result.no_op_actions.append(action_id)

        wave_result["completed_at"] = time.time()
        wave_result["duration_ms"] = (wave_result["completed_at"] - wave_result["started_at"]) * 1000
        return wave_result

    def _execute_action(self, action: PropagationAction) -> dict[str, Any]:
        if action.idempotency_key in self._idempotency_cache:
            return {
                "action_id": action.action_id,
                "status": "skipped",
                "reason": "duplicate idempotency key",
                "timestamp": time.time(),
            }
        self._idempotency_cache.add(action.idempotency_key)

        if action.status == PropagationActionStatus.BLOCKED:
            return {
                "action_id": action.action_id,
                "node_id": action.node_id,
                "action_type": action.action_type,
                "status": "blocked",
                "reason": f"Action blocked: risk_class={action.risk_class}",
                "timestamp": time.time(),
            }

        if action.status == PropagationActionStatus.APPROVAL_REQUIRED:
            return {
                "action_id": action.action_id,
                "node_id": action.node_id,
                "action_type": action.action_type,
                "status": "approval_required",
                "reason": "Requires operator approval before execution",
                "timestamp": time.time(),
            }

        if action.status == PropagationActionStatus.HUMAN_REQUIRED:
            return {
                "action_id": action.action_id,
                "node_id": action.node_id,
                "action_type": action.action_type,
                "status": "human_required",
                "reason": "Requires human action before proceeding",
                "timestamp": time.time(),
            }

        if self._mode == ExecutionMode.DRY_RUN:
            return self._dry_run_action(action)
        elif self._mode == ExecutionMode.RECOMPUTE_ONLY:
            if action.action_type in ("recompute", "revalidate", "no_op", "notify"):
                return self._recompute_action(action)
            return {
                "action_id": action.action_id,
                "node_id": action.node_id,
                "action_type": action.action_type,
                "status": "skipped",
                "reason": f"recompute_only mode: {action.action_type} not safe",
                "timestamp": time.time(),
            }
        elif self._mode == ExecutionMode.NOTIFY_ONLY:
            return {
                "action_id": action.action_id,
                "node_id": action.node_id,
                "action_type": action.action_type,
                "status": "dry_run",
                "reason": "notify_only mode: logged, no mutation",
                "timestamp": time.time(),
            }

        return {
            "action_id": action.action_id,
            "node_id": action.node_id,
            "action_type": action.action_type,
            "status": "blocked",
            "reason": f"Governed execution not enabled in Phase 12.0",
            "timestamp": time.time(),
        }

    def _dry_run_action(self, action: PropagationAction) -> dict[str, Any]:
        node = self._graph.nodes.get(action.node_id)
        node_title = node.title if node else "unknown"
        return {
            "action_id": action.action_id,
            "node_id": action.node_id,
            "node_title": node_title,
            "action_type": action.action_type,
            "status": "dry_run",
            "would_execute": action.action_type,
            "output_expected": action.output_expected,
            "risk_class": action.risk_class,
            "timestamp": time.time(),
        }

    def _recompute_action(self, action: PropagationAction) -> dict[str, Any]:
        node = self._graph.nodes.get(action.node_id)
        node_title = node.title if node else "unknown"
        return {
            "action_id": action.action_id,
            "node_id": action.node_id,
            "node_title": node_title,
            "action_type": action.action_type,
            "status": "completed",
            "result": f"Recomputed: {action.output_expected}",
            "risk_class": action.risk_class,
            "timestamp": time.time(),
        }

    def persist_result(
        self,
        result: PropagationResult,
        path: str | None = None,
    ) -> str:
        path = path or os.path.join(
            _REPO_ROOT, "data", "umh", "propagation_graph", "propagation_results.jsonl",
        )
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "a") as f:
            f.write(json.dumps(result.to_dict()) + "\n")
        logger.info("Propagation result persisted: %s -> %s", result.result_id, path)
        return path
