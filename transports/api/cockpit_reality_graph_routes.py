"""Cockpit routes for Reality Graph — Campaign 5.0.

Exposes the operator-world graph to the cockpit frontend.
Read-only — RealityGraph never mutates canonical reality.
"""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)

_graph: Any = None


def _get_graph() -> Any:
    global _graph
    if _graph is None:
        from substrate.organism.reality_graph import RealityGraph
        _graph = RealityGraph.seed_from_registries()
    return _graph


def configure(graph: Any) -> None:
    global _graph
    _graph = graph


def _build_router() -> Any:
    from fastapi import APIRouter, HTTPException

    router = APIRouter(prefix="/reality-graph", tags=["reality-graph"])

    @router.get("/summary")
    def get_summary() -> dict[str, Any]:
        g = _get_graph()
        return g.summary()

    @router.get("/entities")
    def list_entities(entity_type: str | None = None) -> dict[str, Any]:
        g = _get_graph()
        if entity_type:
            from substrate.organism.reality_graph import RealityEntityType
            try:
                et = RealityEntityType(entity_type)
            except ValueError:
                raise HTTPException(status_code=400, detail=f"Unknown entity type: {entity_type}")
            entities = g.find_by_type(et)
        else:
            entities = g.all_entities()
        return {"entities": [e.to_dict() for e in entities], "count": len(entities)}

    @router.get("/entity/{entity_id}")
    def get_entity(entity_id: str) -> dict[str, Any]:
        g = _get_graph()
        entity = g.get(entity_id)
        if entity is None:
            raise HTTPException(status_code=404, detail=f"Entity not found: {entity_id}")
        return entity.to_dict()

    @router.get("/neighbors/{entity_id}")
    def get_neighbors(entity_id: str, relation_type: str | None = None) -> dict[str, Any]:
        g = _get_graph()
        if g.get(entity_id) is None:
            raise HTTPException(status_code=404, detail=f"Entity not found: {entity_id}")

        rt = None
        if relation_type:
            from substrate.organism.reality_graph import RealityRelationType
            try:
                rt = RealityRelationType(relation_type)
            except ValueError:
                raise HTTPException(status_code=400, detail=f"Unknown relation type: {relation_type}")

        neighbors = g.neighbors(entity_id, rt)
        return {"neighbors": [n.to_dict() for n in neighbors], "count": len(neighbors)}

    @router.get("/search")
    def search_entities(q: str) -> dict[str, Any]:
        g = _get_graph()
        results = g.find_by_name(q)
        return {"results": [e.to_dict() for e in results], "count": len(results)}

    @router.get("/path")
    def find_path(from_id: str, to_id: str) -> dict[str, Any]:
        g = _get_graph()
        path = g.path(from_id, to_id)
        return {"path": [r.to_dict() for r in path], "hops": len(path)}

    @router.get("/subgraph/{entity_id}")
    def get_subgraph(entity_id: str, depth: int = 2) -> dict[str, Any]:
        g = _get_graph()
        if g.get(entity_id) is None:
            raise HTTPException(status_code=404, detail=f"Entity not found: {entity_id}")
        sub = g.subgraph(entity_id, depth=min(depth, 4))
        return sub.summary()

    return router


def get_router() -> Any:
    return _build_router()
