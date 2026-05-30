"""Cockpit propagation graph routes — graph, impact, plan, execute, results.

Mounted under /api/umh/ via include_router in cockpit.py.

Phase 12.0. UMH transport layer. Instance-agnostic.
"""

from __future__ import annotations

import json
import logging
import os
from typing import Any, Callable

from fastapi import APIRouter, Depends, Request

logger = logging.getLogger(__name__)

propagation_graph_router: APIRouter = APIRouter()

_configured: bool = False
_REPO_ROOT = os.environ.get("UMH_ROOT", "/opt/OS")


def configure(require_operator_dep: Any) -> None:
    global _configured, propagation_graph_router
    _configured = True
    propagation_graph_router = _build_router(require_operator_dep)


def _get_graph():
    from substrate.organism.propagation_graph import PropagationGraph
    return PropagationGraph.load()


def _get_builder():
    from substrate.organism.propagation_graph_builder import PropagationGraphBuilder
    return PropagationGraphBuilder()


def _get_analyzer(graph: Any):
    from substrate.organism.impact_analyzer import ImpactAnalyzer
    return ImpactAnalyzer(graph)


def _get_planner(graph: Any):
    from substrate.organism.propagation_planner import PropagationPlanner
    return PropagationPlanner(graph)


def _get_executor(graph: Any, mode: str = "dry_run"):
    from substrate.organism.propagation_executor import PropagationExecutor
    return PropagationExecutor(graph, mode=mode)


def _build_router(require_operator_dep: Any) -> APIRouter:
    r = APIRouter()
    auth = [Depends(require_operator_dep)]

    r.add_api_route("/organism/propagation-graph", _overview, methods=["GET"])
    r.add_api_route("/organism/propagation-graph/summary", _summary, methods=["GET"])
    r.add_api_route("/organism/propagation-graph/nodes", _nodes, methods=["GET"])
    r.add_api_route("/organism/propagation-graph/edges", _edges, methods=["GET"])
    r.add_api_route("/organism/propagation-graph/change-events", _change_events, methods=["GET"])
    r.add_api_route("/organism/propagation-graph/results", _results, methods=["GET"])
    r.add_api_route("/organism/propagation-graph/correspondence-proof", _correspondence_proof, methods=["GET"])
    r.add_api_route("/organism/propagation-graph/impact", _impact, methods=["POST"], dependencies=auth)
    r.add_api_route("/organism/propagation-graph/plan", _plan, methods=["POST"], dependencies=auth)
    r.add_api_route("/organism/propagation-graph/execute-dry-run", _execute_dry_run, methods=["POST"], dependencies=auth)

    return r


async def _overview(request: Request) -> dict[str, Any]:
    graph = _get_graph()
    return {
        "status": "operational",
        "phase": "12.0",
        "graph": graph.to_safe_dict(),
    }


async def _summary(request: Request) -> dict[str, Any]:
    graph = _get_graph()
    return graph.graph_stats()


async def _nodes(request: Request) -> dict[str, Any]:
    graph = _get_graph()
    return {
        "total": len(graph.nodes),
        "nodes": [n.to_dict() for n in graph.nodes.values()],
    }


async def _edges(request: Request) -> dict[str, Any]:
    graph = _get_graph()
    return {
        "total": len(graph.edges),
        "edges": [e.to_dict() for e in graph.edges.values()],
    }


async def _change_events(request: Request) -> dict[str, Any]:
    from substrate.organism.change_event import load_change_events
    events = load_change_events()
    return {
        "total": len(events),
        "events": [e.to_dict() for e in events],
    }


async def _results(request: Request) -> dict[str, Any]:
    path = os.path.join(_REPO_ROOT, "data", "umh", "propagation_graph", "propagation_results.jsonl")
    results = []
    if os.path.exists(path):
        from substrate.organism.change_event import PropagationResult
        with open(path) as f:
            for line in f:
                line = line.strip()
                if line:
                    results.append(PropagationResult.from_dict(json.loads(line)).to_dict())
    return {
        "total": len(results),
        "results": results,
    }


async def _correspondence_proof(request: Request) -> dict[str, Any]:
    proof_path = os.path.join(
        _REPO_ROOT, "data", "umh", "propagation_graph",
        "phase12_0_correspondence_layer_proof.json",
    )
    if not os.path.exists(proof_path):
        return {"status": "not_generated", "proof": None}
    with open(proof_path) as f:
        return {"status": "available", "proof": json.load(f)}


async def _impact(request: Request) -> dict[str, Any]:
    body = await request.json()
    from substrate.organism.change_event import ChangeEvent, ChangeType
    source_node_id = body.get("source_node_id", "")
    change_type_str = body.get("change_type", "work_packet_updated")
    try:
        change_type = ChangeType(change_type_str)
    except ValueError:
        change_type = ChangeType.WORK_PACKET_UPDATED

    event = ChangeEvent(
        source_node_id=source_node_id,
        change_type=change_type,
        title=body.get("title", "Manual impact analysis"),
        description=body.get("description", ""),
        risk_class=body.get("risk_class", "low"),
    )

    graph = _get_graph()
    analyzer = _get_analyzer(graph)
    analysis = analyzer.analyze(event)
    return analysis.to_dict()


async def _plan(request: Request) -> dict[str, Any]:
    body = await request.json()
    from substrate.organism.change_event import ChangeEvent, ChangeType
    source_node_id = body.get("source_node_id", "")
    change_type_str = body.get("change_type", "work_packet_updated")
    try:
        change_type = ChangeType(change_type_str)
    except ValueError:
        change_type = ChangeType.WORK_PACKET_UPDATED

    event = ChangeEvent(
        source_node_id=source_node_id,
        change_type=change_type,
        title=body.get("title", "Manual plan request"),
        description=body.get("description", ""),
        risk_class=body.get("risk_class", "low"),
    )

    graph = _get_graph()
    analyzer = _get_analyzer(graph)
    analysis = analyzer.analyze(event)
    planner = _get_planner(graph)
    plan = planner.plan(event, analysis)
    return plan.to_dict()


async def _execute_dry_run(request: Request) -> dict[str, Any]:
    body = await request.json()
    from substrate.organism.change_event import ChangeEvent, ChangeType
    source_node_id = body.get("source_node_id", "")
    change_type_str = body.get("change_type", "work_packet_updated")
    try:
        change_type = ChangeType(change_type_str)
    except ValueError:
        change_type = ChangeType.WORK_PACKET_UPDATED

    event = ChangeEvent(
        source_node_id=source_node_id,
        change_type=change_type,
        title=body.get("title", "Dry-run execution"),
        description=body.get("description", ""),
        risk_class=body.get("risk_class", "low"),
    )

    graph = _get_graph()
    analyzer = _get_analyzer(graph)
    analysis = analyzer.analyze(event)
    planner = _get_planner(graph)
    plan = planner.plan(event, analysis)
    executor = _get_executor(graph, mode="dry_run")
    result = executor.execute(plan)
    executor.persist_result(result)
    return result.to_dict()
