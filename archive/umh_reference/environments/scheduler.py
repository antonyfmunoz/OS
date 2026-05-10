"""Scheduler — deterministic node selection for execution tasks.

Pure function: same inputs always produce same output.
No side effects, no state mutation, no I/O.

Selection logic:
1. Filter AVAILABLE nodes
2. Filter by resource requirements
3. Prefer environment_preference if specified
4. Prefer LOCAL for latency-sensitive tasks
5. Prefer VPS when LOCAL is overloaded (load > threshold)
6. Fall back to any available node

Also provides select_node_for_job() which uses the job priority
scoring system to pick the best node for an ExecutionJob.

Accepts telemetry as input — no global state.

No imports from umh/cells, umh/adapters, or umh/execution.
"""

from __future__ import annotations

from typing import Any

from umh.environments.models import ExecutionTask, Node, NodeStatus, NodeType
from umh.environments.telemetry import NodeTelemetry

_LOAD_THRESHOLD = 0.8
_HIGH_MEMORY_THRESHOLD_PCT = 85.0


def select_node(
    task: ExecutionTask,
    nodes: list[Node],
    telemetry: dict[str, NodeTelemetry] | None = None,
) -> Node | None:
    """Select the best node for a task. Returns None if no node fits.

    If telemetry is provided, node current_load is updated from real metrics
    before selection (non-mutating — uses telemetry values for comparison only).
    """
    available = [n for n in nodes if n.status == NodeStatus.AVAILABLE]
    if not available:
        return None

    capable = [n for n in available if n.can_satisfy(task.resources)]
    if not capable:
        return None

    if telemetry:
        capable = _filter_by_telemetry(capable, task, telemetry)
        if not capable:
            return None

    if task.environment_preference:
        preferred = [n for n in capable if n.node_type == task.environment_preference]
        if preferred:
            return _best_of(preferred, telemetry)

    if task.latency_sensitive:
        local = [n for n in capable if n.node_type == NodeType.LOCAL]
        if local:
            low_load = [n for n in local if _effective_load(n, telemetry) < _LOAD_THRESHOLD]
            if low_load:
                return _best_of(low_load, telemetry)

    low_load = [n for n in capable if _effective_load(n, telemetry) < _LOAD_THRESHOLD]
    if low_load:
        return _best_of(low_load, telemetry)

    return _best_of(capable, telemetry)


def select_node_for_job(
    job: Any,
    nodes: list[Node],
    telemetry: dict[str, NodeTelemetry] | None = None,
) -> Node | None:
    """Select the best node for an ExecutionJob using priority scoring.

    Converts environment Nodes to NodeCapability snapshots, scores the
    job against each, and returns the best-fitting node.
    """
    from umh.jobs.priority import NodeCapability, score_job

    available = [n for n in nodes if n.status == NodeStatus.AVAILABLE]
    if not available:
        return None

    best_node: Node | None = None
    best_score: float = float("-inf")

    for node in available:
        load = _effective_load(node, telemetry)
        cap = NodeCapability(
            node_id=node.node_id,
            cpu_cores=node.cpu_cores,
            memory_mb=node.memory_mb,
            current_load=load,
            gpu=node.gpu,
        )
        scored = score_job(job, cap)
        if scored.score > best_score or (
            scored.score == best_score and (best_node is None or node.node_id < best_node.node_id)
        ):
            best_score = scored.score
            best_node = node

    return best_node


def _effective_load(node: Node, telemetry: dict[str, NodeTelemetry] | None) -> float:
    if telemetry and node.node_id in telemetry:
        t = telemetry[node.node_id]
        return max(t.cpu_percent / 100.0, t.memory_percent / 100.0)
    return node.current_load


def _filter_by_telemetry(
    nodes: list[Node],
    task: ExecutionTask,
    telemetry: dict[str, NodeTelemetry],
) -> list[Node]:
    result = []
    for n in nodes:
        t = telemetry.get(n.node_id)
        if t is None:
            result.append(n)
            continue
        if t.memory_percent > _HIGH_MEMORY_THRESHOLD_PCT:
            if task.resources.memory_mb > (t.memory_available_mb * 0.8):
                continue
        result.append(n)
    return result


def _best_of(
    nodes: list[Node],
    telemetry: dict[str, NodeTelemetry] | None = None,
) -> Node:
    """Pick the best node from a non-empty list: lowest load, highest priority."""
    return min(nodes, key=lambda n: (_effective_load(n, telemetry), -n.priority))
