"""SystemGraph — multi-step execution graph for UMH.

Transforms a list of ExecutableActions into a structured dependency
graph that can be executed in topologically-sorted order through
the ExecutionRouter.

This is the transition from "what action?" to "what system?"

Pipeline position:
    ActionSchema → SystemGraph → ExecutionRouter (per node)

Pure functions + immutable results. No side effects. No I/O.
Deterministic: same input always produces the same output.

Usage::

    from umh.runtime_engine.system_graph import build_system_graph, execute_system_graph
    from umh.runtime_engine.execution_router import ExecutionRouter

    graph = build_system_graph(action_plan)
    result = execute_system_graph(graph, ExecutionRouter())
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field


# ─── Constants ────────────────────────────────────────────────────

MAX_NODES = 10
VALID_NODE_STATUSES = frozenset(
    {"pending", "ready", "running", "done", "failed", "blocked"}
)
VALID_GRAPH_STATUSES = frozenset(
    {"pending", "running", "completed", "partial", "failed"}
)


# ─── Data models ─────────────────────────────────────────────────


@dataclass
class SystemNode:
    """A single node in the execution graph."""

    node_id: str
    action: object  # ExecutableAction
    depends_on: tuple[str, ...]
    status: str = "pending"
    output: dict | None = None

    def to_dict(self) -> dict:
        action = self.action
        action_dict = action.to_dict() if hasattr(action, "to_dict") else str(action)
        return {
            "node_id": self.node_id,
            "action": action_dict,
            "depends_on": list(self.depends_on),
            "status": self.status,
            "output": dict(self.output) if self.output is not None else None,
        }


@dataclass(frozen=True)
class SystemGraph:
    """A DAG of actions with dependency edges."""

    graph_id: str
    nodes: dict[str, SystemNode]
    entry_points: tuple[str, ...]
    exit_nodes: tuple[str, ...]
    status: str = "pending"

    def to_dict(self) -> dict:
        return {
            "graph_id": self.graph_id,
            "nodes": {nid: n.to_dict() for nid, n in self.nodes.items()},
            "entry_points": list(self.entry_points),
            "exit_nodes": list(self.exit_nodes),
            "status": self.status,
            "node_count": len(self.nodes),
        }


@dataclass(frozen=True)
class SystemExecutionResult:
    """Output from executing a system graph."""

    graph_id: str
    completed_nodes: int
    failed_nodes: int
    blocked_nodes: int
    total_nodes: int
    outputs: dict[str, dict | None]
    node_execution_order: tuple[str, ...]
    node_statuses: dict[str, str]
    status: str

    def to_dict(self) -> dict:
        return {
            "graph_id": self.graph_id,
            "completed_nodes": self.completed_nodes,
            "failed_nodes": self.failed_nodes,
            "blocked_nodes": self.blocked_nodes,
            "total_nodes": self.total_nodes,
            "outputs": {
                k: dict(v) if v is not None else None for k, v in self.outputs.items()
            },
            "node_execution_order": list(self.node_execution_order),
            "node_statuses": dict(self.node_statuses),
            "status": self.status,
        }


NO_RESULT = SystemExecutionResult(
    graph_id="",
    completed_nodes=0,
    failed_nodes=0,
    blocked_nodes=0,
    total_nodes=0,
    outputs={},
    node_execution_order=(),
    node_statuses={},
    status="failed",
)


# ─── Graph ID ─────────────────────────────────────────────────────


def _compute_graph_id(action_ids: tuple[str, ...]) -> str:
    canonical = json.dumps(
        {"action_ids": list(action_ids)},
        sort_keys=True,
        separators=(",", ":"),
    )
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()[:16]


# ─── Dependency analysis ──────────────────────────────────────────


def _actions_are_independent(a: object, b: object) -> bool:
    """Two actions are independent if they target different domains."""
    domain_a = getattr(a, "domain", "")
    domain_b = getattr(b, "domain", "")
    if domain_a and domain_b and domain_a != domain_b:
        return True

    target_a = getattr(a, "target", None)
    target_b = getattr(b, "target", None)
    if target_a and target_b and target_a != target_b:
        if domain_a == domain_b:
            return False
        return True

    return False


def _detect_dependencies(
    actions: list[object],
) -> dict[int, tuple[int, ...]]:
    """Build a dependency map: index → tuple of dependency indices.

    Default is a linear chain. Actions targeting different domains
    can execute independently (no dependency between them).
    """
    n = len(actions)
    if n <= 1:
        return {i: () for i in range(n)}

    deps: dict[int, list[int]] = {i: [] for i in range(n)}

    for i in range(1, n):
        has_dependency = False
        for j in range(i):
            if not _actions_are_independent(actions[i], actions[j]):
                deps[i].append(j)
                has_dependency = True

        if not has_dependency and i > 0:
            pass

    return {i: tuple(sorted(d)) for i, d in deps.items()}


# ─── Cycle detection ──────────────────────────────────────────────


def _has_cycle(node_deps: dict[str, tuple[str, ...]]) -> bool:
    """Detect cycles via DFS coloring. Returns True if cycle found."""
    WHITE, GRAY, BLACK = 0, 1, 2
    color: dict[str, int] = {nid: WHITE for nid in node_deps}

    def dfs(nid: str) -> bool:
        color[nid] = GRAY
        for dep in node_deps.get(nid, ()):
            if dep not in color:
                continue
            if color[dep] == GRAY:
                return True
            if color[dep] == WHITE and dfs(dep):
                return True
        color[nid] = BLACK
        return False

    for nid in node_deps:
        if color[nid] == WHITE:
            if dfs(nid):
                return True
    return False


# ─── Topological sort ─────────────────────────────────────────────


def _topological_sort(node_deps: dict[str, tuple[str, ...]]) -> tuple[str, ...]:
    """Kahn's algorithm for topological ordering.

    Returns nodes in execution order. Raises ValueError on cycle.
    """
    in_degree: dict[str, int] = {nid: 0 for nid in node_deps}
    for nid, deps in node_deps.items():
        for dep in deps:
            if dep in in_degree:
                in_degree[nid] = in_degree.get(nid, 0)

    in_degree = {nid: 0 for nid in node_deps}
    for nid, deps in node_deps.items():
        in_degree[nid] = len([d for d in deps if d in node_deps])

    queue: list[str] = sorted(nid for nid, deg in in_degree.items() if deg == 0)
    result: list[str] = []

    while queue:
        current = queue.pop(0)
        result.append(current)

        for nid, deps in node_deps.items():
            if current in deps:
                in_degree[nid] -= 1
                if in_degree[nid] == 0:
                    queue.append(nid)
        queue.sort()

    if len(result) != len(node_deps):
        raise ValueError("Cycle detected in system graph")

    return tuple(result)


# ─── Graph construction ──────────────────────────────────────────


def build_system_graph(
    action_plan: list[object],
) -> SystemGraph:
    """Convert a list of ExecutableActions into a SystemGraph.

    Default behavior: linear chain unless actions target different
    domains (in which case they can be independent).

    Enforces MAX_NODES limit and rejects cyclic dependencies.
    """
    if not action_plan:
        return SystemGraph(
            graph_id=_compute_graph_id(()),
            nodes={},
            entry_points=(),
            exit_nodes=(),
            status="completed",
        )

    if len(action_plan) > MAX_NODES:
        truncated = action_plan[:MAX_NODES]
    else:
        truncated = action_plan

    dep_map = _detect_dependencies(truncated)

    node_ids: list[str] = []
    for i, action in enumerate(truncated):
        aid = getattr(action, "action_id", "") or f"node_{i}"
        node_ids.append(f"n_{i}_{aid[:8]}")

    node_deps: dict[str, tuple[str, ...]] = {}
    for i, nid in enumerate(node_ids):
        dep_indices = dep_map.get(i, ())
        dep_nids = tuple(node_ids[j] for j in dep_indices if j < len(node_ids))
        node_deps[nid] = dep_nids

    if _has_cycle(node_deps):
        raise ValueError("Cyclic dependencies detected in action plan")

    nodes: dict[str, SystemNode] = {}
    for i, nid in enumerate(node_ids):
        dep_nids = node_deps[nid]
        status = "ready" if not dep_nids else "pending"
        nodes[nid] = SystemNode(
            node_id=nid,
            action=truncated[i],
            depends_on=dep_nids,
            status=status,
        )

    entry_points = tuple(nid for nid, deps in node_deps.items() if not deps)

    has_dependent: set[str] = set()
    for deps in node_deps.values():
        has_dependent.update(deps)
    exit_nodes = tuple(nid for nid in node_ids if nid not in has_dependent)

    action_ids = tuple(getattr(a, "action_id", "") for a in truncated)
    graph_id = _compute_graph_id(action_ids)

    return SystemGraph(
        graph_id=graph_id,
        nodes=nodes,
        entry_points=entry_points,
        exit_nodes=exit_nodes,
        status="pending",
    )


# ─── Execution engine ────────────────────────────────────────────


def _all_deps_done(node: SystemNode, nodes: dict[str, SystemNode]) -> bool:
    for dep_id in node.depends_on:
        dep = nodes.get(dep_id)
        if dep is None or dep.status != "done":
            return False
    return True


def _any_dep_failed(node: SystemNode, nodes: dict[str, SystemNode]) -> bool:
    for dep_id in node.depends_on:
        dep = nodes.get(dep_id)
        if dep is not None and dep.status in ("failed", "blocked"):
            return True
    return False


def execute_system_graph(
    graph: SystemGraph,
    router: object,
) -> SystemExecutionResult:
    """Execute a system graph through the router in topological order.

    Nodes run when all dependencies are complete.
    Failed nodes block their dependents.
    The graph is not mutated — node states are tracked in a copy.

    Router must have a .route(request) method that accepts an
    ExecutionRequest and returns an ExecutionResult.
    """
    if not graph.nodes:
        return SystemExecutionResult(
            graph_id=graph.graph_id,
            completed_nodes=0,
            failed_nodes=0,
            blocked_nodes=0,
            total_nodes=0,
            outputs={},
            node_execution_order=(),
            node_statuses={},
            status="completed",
        )

    node_deps = {nid: n.depends_on for nid, n in graph.nodes.items()}

    try:
        execution_order = _topological_sort(node_deps)
    except ValueError:
        return SystemExecutionResult(
            graph_id=graph.graph_id,
            completed_nodes=0,
            failed_nodes=0,
            blocked_nodes=0,
            total_nodes=len(graph.nodes),
            outputs={},
            node_execution_order=(),
            node_statuses={nid: "failed" for nid in graph.nodes},
            status="failed",
        )

    states: dict[str, SystemNode] = {}
    for nid, node in graph.nodes.items():
        states[nid] = SystemNode(
            node_id=node.node_id,
            action=node.action,
            depends_on=node.depends_on,
            status=node.status,
            output=None,
        )

    outputs: dict[str, dict | None] = {}
    executed_order: list[str] = []

    for nid in execution_order:
        node = states[nid]

        if _any_dep_failed(node, states):
            node.status = "blocked"
            outputs[nid] = None
            continue

        if not _all_deps_done(node, states):
            node.status = "blocked"
            outputs[nid] = None
            continue

        node.status = "running"

        try:
            from umh.runtime_engine.execution_router import ExecutionRequest

            request = ExecutionRequest(action=node.action)
            result = router.route(request)
            executed_order.append(nid)

            result_status = getattr(result, "status", "unhandled")
            result_output = getattr(result, "output", None)
            result_error = getattr(result, "error", None)

            if result_status == "success":
                node.status = "done"
                outputs[nid] = dict(result_output) if result_output else {}
            elif result_status in ("failed", "unhandled"):
                node.status = "failed"
                outputs[nid] = {"error": result_error or result_status}
            else:
                node.status = "done"
                outputs[nid] = dict(result_output) if result_output else {}

        except Exception as exc:
            node.status = "failed"
            outputs[nid] = {"error": str(exc)}
            executed_order.append(nid)

    completed = sum(1 for n in states.values() if n.status == "done")
    failed = sum(1 for n in states.values() if n.status == "failed")
    blocked = sum(1 for n in states.values() if n.status == "blocked")
    total = len(states)

    if completed == total:
        graph_status = "completed"
    elif failed == total:
        graph_status = "failed"
    elif completed > 0 or failed > 0:
        graph_status = "partial"
    else:
        graph_status = "failed"

    return SystemExecutionResult(
        graph_id=graph.graph_id,
        completed_nodes=completed,
        failed_nodes=failed,
        blocked_nodes=blocked,
        total_nodes=total,
        outputs=outputs,
        node_execution_order=tuple(executed_order),
        node_statuses={nid: n.status for nid, n in states.items()},
        status=graph_status,
    )


if __name__ == "__main__":
    print("system_graph import OK")
