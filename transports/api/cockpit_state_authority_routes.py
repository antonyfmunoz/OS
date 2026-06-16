"""Cockpit State Authority Routes — read-only state domain authority API.

Exposes state domain authority, ownership, and coherence through the
cockpit API. All routes auth-protected.

Phase 29. Transport layer. Instance-agnostic.
"""

from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, Depends, HTTPException

logger = logging.getLogger(__name__)

state_authority_router: APIRouter = APIRouter()
_configured = False


def configure(*, require_operator_dep: Any) -> None:
    global _configured
    if _configured:
        return
    _configured = True
    _router = _build_router(require_operator_dep)
    state_authority_router.include_router(_router)


def _get_registry() -> Any:
    if not hasattr(_get_registry, "_instance"):
        from substrate.organism.state_registry import StateRegistry

        _get_registry._instance = StateRegistry()
    return _get_registry._instance


def _get_coherence() -> Any:
    if not hasattr(_get_coherence, "_instance"):
        from substrate.organism.state_coherence_engine import StateCoherenceEngine

        _get_coherence._instance = StateCoherenceEngine(
            state_registry=_get_registry()
        )
    return _get_coherence._instance


def _build_router(require_operator_dep: Any) -> APIRouter:
    router = APIRouter(
        prefix="/state-authority",
        tags=["state-authority"],
        dependencies=[Depends(require_operator_dep)],
    )

    @router.get("")
    async def state_authority_graph() -> dict[str, Any]:
        reg = _get_registry()
        return reg.topology().to_dict()

    @router.get("/domains")
    async def all_domains() -> dict[str, Any]:
        reg = _get_registry()
        authorities = reg.all_domains()
        return {
            "domain_count": len(authorities),
            "domains": [a.to_dict() for a in authorities],
        }

    @router.get("/coherence")
    async def coherence_report() -> dict[str, Any]:
        engine = _get_coherence()
        return engine.coherence_report()

    @router.get("/domain/{domain}")
    async def domain_detail(domain: str) -> dict[str, Any]:
        reg = _get_registry()
        auth = reg.get_domain(domain)
        if not auth:
            raise HTTPException(
                status_code=404, detail=f"Domain {domain} not found"
            )
        engine = _get_coherence()
        status = engine.domain_status(domain)
        result = auth.to_dict()
        result["status"] = status.to_dict()
        return result

    @router.get("/node/{node_id}")
    async def domains_for_node(node_id: str) -> dict[str, Any]:
        reg = _get_registry()
        domains = reg.domains_for_node(node_id)
        return {
            "node_id": node_id,
            "domain_count": len(domains),
            "domains": [d.to_dict() for d in domains],
        }

    return router
