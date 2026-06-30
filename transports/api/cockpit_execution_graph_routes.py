"""Cockpit Execution Graph Routes — API surface for lineage validation.

Exposes ExecutionGraph operations: record, trace, validate, audit, replay.

Answers: "Pick any action. Trace Intent→Decision→Execution→Proof→Outcome. No gaps."

Gate 8 — Execution Graph. UMH transport layer. Instance-agnostic.
"""

from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, Depends, Request

from transports.api.governed import governed_mutation

logger = logging.getLogger(__name__)

execution_graph_router: APIRouter = APIRouter()
_configured = False


def configure(*, require_operator_dep: Any) -> None:
    global _configured
    if _configured:
        return
    _configured = True
    _router = _build_router(require_operator_dep)
    execution_graph_router.include_router(_router)


def _get_graph() -> Any:
    if not hasattr(_get_graph, "_instance"):
        from substrate.organism.execution_graph import ExecutionGraph

        _get_graph._instance = ExecutionGraph()
    return _get_graph._instance


def _build_router(require_operator_dep: Any) -> APIRouter:
    r = APIRouter()
    auth = [Depends(require_operator_dep)]

    @r.get("/execution-graph/nodes", dependencies=auth)
    def list_nodes(
        node_type: str | None = None,
        intent_id: str | None = None,
        limit: int = 100,
    ) -> dict[str, Any]:
        from substrate.organism.execution_graph import ExecutionNodeType

        g = _get_graph()
        nt = None
        if node_type:
            try:
                nt = ExecutionNodeType(node_type)
            except ValueError:
                return {"error": f"invalid node_type: {node_type}"}
        nodes = g.list_nodes(node_type=nt, intent_id=intent_id, limit=limit)
        return {"nodes": [n.to_dict() for n in nodes], "count": len(nodes)}

    @r.get("/execution-graph/summary", dependencies=auth)
    def graph_summary() -> dict[str, Any]:
        return _get_graph().summary()

    @r.get("/execution-graph/audit", dependencies=auth)
    def audit_completeness(limit: int = 100) -> dict[str, Any]:
        return _get_graph().audit_completeness(limit=limit)

    @r.get("/execution-graph/trace/{node_id}", dependencies=auth)
    def trace_full(node_id: str) -> dict[str, Any]:
        return _get_graph().trace_full(node_id)

    @r.get("/execution-graph/trace-intent/{intent_id}", dependencies=auth)
    def trace_from_intent(intent_id: str) -> dict[str, Any]:
        return _get_graph().trace_from_intent(intent_id)

    @r.get("/execution-graph/replay/{node_id}", dependencies=auth)
    def replay(node_id: str) -> dict[str, Any]:
        return _get_graph().replay(node_id)

    @r.post("/execution-graph/record", dependencies=auth)
    async def record_node(request: Request) -> dict[str, Any]:
        from substrate.organism.execution_graph import ExecutionNodeType

        body = await request.json()
        action = body.get("action", "")
        if not action:
            return {"error": "action is required"}
        nt_str = body.get("node_type", "execution")
        try:
            nt = ExecutionNodeType(nt_str)
        except ValueError:
            return {"error": f"invalid node_type: {nt_str}"}

        result: dict[str, Any] = {}

        def _do_record() -> tuple[str, bool]:
            node = _get_graph().record(
                action=action,
                node_type=nt,
                intent_id=body.get("intent_id", ""),
                decision_id=body.get("decision_id", ""),
                work_packet_id=body.get("work_packet_id", ""),
                execution_id=body.get("execution_id", ""),
                proof_id=body.get("proof_id", ""),
                outcome_id=body.get("outcome_id", ""),
                parent_node_id=body.get("parent_node_id", ""),
                metadata=body.get("metadata"),
            )
            result["node"] = node.to_dict()
            return node.node_id, True

        resp = governed_mutation(
            mutation_name="state_mutate",
            intent=f"Record execution graph node: {action}",
            execute_fn=_do_record,
            source="cockpit",
            metadata={"node_type": nt_str, "intent_id": body.get("intent_id", "")},
        )
        return {**resp.to_http_dict(), **result}

    @r.post("/execution-graph/from-receipt", dependencies=auth)
    async def record_from_receipt(request: Request) -> dict[str, Any]:
        body = await request.json()
        result: dict[str, Any] = {}

        def _do_record_receipt() -> tuple[str, bool]:
            node = _get_graph().record_from_receipt(body)
            if node is None:
                return "receipt must have intent_id", False
            result["node"] = node.to_dict()
            return node.node_id, True

        resp = governed_mutation(
            mutation_name="state_mutate",
            intent="Record execution graph node from receipt",
            execute_fn=_do_record_receipt,
            source="cockpit",
            metadata={"intent_id": body.get("intent_id", "")},
        )
        if not resp.success and "node" not in result:
            return {"error": resp.output}
        return {**resp.to_http_dict(), **result}

    return r
