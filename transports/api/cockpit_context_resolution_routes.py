"""Cockpit routes for Context Resolution — Campaign 5.5.

Exposes the "system already knows" resolution engine to the cockpit.
Read-only — resolves context, never mutates canonical reality.
"""

from __future__ import annotations

import logging
from typing import Any

from pydantic import BaseModel

from transports.api.governed import governed_mutation

logger = logging.getLogger(__name__)


class ResolveRequest(BaseModel):
    # MODULE scope: PEP 563 string annotations resolve against module globals;
    # nested inside _build_router() this model was invisible to FastAPI and
    # the body param degraded to a required query param (422 loc
    # ["query","req"] — same defect family as the unified-approval routes).
    text: str


_engine: Any = None


def _get_engine() -> Any:
    global _engine
    if _engine is None:
        from substrate.organism.reality_graph import RealityGraph
        from substrate.organism.project_registry import ProjectRegistry
        from substrate.organism.context_resolution import ContextResolutionEngine

        graph = RealityGraph.seed_from_registries()
        project_reg = ProjectRegistry()
        _engine = ContextResolutionEngine(
            reality_graph=graph,
            project_registry=project_reg,
        )
    return _engine


def configure(engine: Any) -> None:
    global _engine
    _engine = engine


def _build_router() -> Any:
    from fastapi import APIRouter

    router = APIRouter(prefix="/context-resolution", tags=["context-resolution"])

    @router.post("/resolve")
    def resolve_context(req: ResolveRequest) -> dict[str, Any]:
        eng = _get_engine()

        def _do_resolve():
            eng.resolve(req.text)
            return f"context resolved: {req.text[:50]}", True

        resp = governed_mutation(
            mutation_name="state_mutate",
            intent=f"resolve context: {req.text[:50]}",
            execute_fn=_do_resolve,
            source="cockpit",
        )
        return resp.to_http_dict()

    @router.get("/entity-reference")
    def resolve_entity_reference(q: str) -> dict[str, Any]:
        eng = _get_engine()
        results = eng.resolve_entity_reference(q)
        return {"results": results, "count": len(results)}

    return router


def get_router() -> Any:
    return _build_router()
