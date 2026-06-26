"""Cockpit reality intelligence routes — read-only reality retrieval.

Mounted under /api/umh/ via include_router in cockpit.py.
All routes are GET (read-only). No mutations, no execution.

Phase 20. UMH transport layer. Instance-agnostic.
"""

from __future__ import annotations

import logging
import os
from typing import Any

from fastapi import APIRouter, Depends, Query

logger = logging.getLogger(__name__)

reality_intelligence_router: APIRouter = APIRouter()

_configured: bool = False


def configure(require_operator_dep: Any) -> None:
    global _configured, reality_intelligence_router
    _configured = True
    reality_intelligence_router = _build_router(require_operator_dep)


def _get_engine():
    from substrate.reality_model.reality_intelligence import (
        RealityIntelligenceEngine,
    )
    from substrate.reality_model.instance import InstanceRealityModel
    from substrate.reality_model.canonical import CanonicalRealityModel

    org_id = os.environ.get("UMH_ORG_ID", os.environ.get("EOS_ORG_ID", "default"))
    user_id = os.environ.get("UMH_USER_ID", os.environ.get("EOS_USER_ID", "default"))

    instance_model = None
    canonical_model = None
    memory_store = None
    event_spine = None

    try:
        instance_model = InstanceRealityModel(user_id=user_id, org_id=org_id)
    except Exception:
        pass
    try:
        canonical_model = CanonicalRealityModel()
    except Exception:
        pass
    try:
        from substrate.state.memory.contracts.canonical_memory_store_v1 import (
            CanonicalMemoryStore,
        )
        memory_store = CanonicalMemoryStore()
    except Exception:
        pass
    try:
        from substrate.organism.event_spine import EventSpine

        es = EventSpine()
        es.recover()
        event_spine = es
    except Exception:
        pass

    return RealityIntelligenceEngine(
        instance_model=instance_model,
        canonical_model=canonical_model,
        memory_store=memory_store,
        event_spine=event_spine,
    )


def _result_to_dict(result: Any) -> dict[str, Any]:
    return {
        "query_id": result.query_id,
        "query_type": result.query_type,
        "evidence": [
            {
                "source_type": e.source_type,
                "source_id": e.source_id,
                "content": e.content,
                "confidence": e.confidence,
                "domain": e.domain,
                "timestamp": e.timestamp,
                "metadata": e.metadata,
            }
            for e in result.evidence
        ],
        "confidence": result.confidence,
        "reasoning": result.reasoning,
        "generated_at": result.generated_at,
        "sources_queried": result.sources_queried,
    }


def _build_router(require_operator_dep: Any) -> APIRouter:
    r = APIRouter()
    auth = [Depends(require_operator_dep)]

    @r.get("/reality-intelligence/query", dependencies=auth)
    def _query(
        q: str = Query("", description="Query text"),
        type: str = Query("why", description="Query type"),
        domain: str = Query("", description="Domain filter"),
        entity: str = Query("", description="Entity name"),
        since: float = Query(0.0, description="Since timestamp"),
        min_confidence: float = Query(0.0, description="Min confidence"),
        limit: int = Query(20, description="Max results"),
    ) -> dict[str, Any]:
        from substrate.reality_model.reality_query import (
            RealityQuery,
            RealityQueryType,
        )
        from uuid import uuid4

        engine = _get_engine()
        try:
            qt = RealityQueryType(type)
        except ValueError:
            return {"error": f"Unknown query type: {type}"}

        rq = RealityQuery(
            query_id=f"rq-{uuid4().hex[:12]}",
            query_type=qt,
            text=q or entity,
            domain=domain,
            entity=entity or q,
            since_timestamp=since if since > 0 else None,
            min_confidence=min_confidence,
            limit=limit,
        )
        result = engine.query(rq)
        return _result_to_dict(result)

    @r.get("/reality-intelligence/why/{entity}", dependencies=auth)
    def _why(
        entity: str,
        limit: int = Query(20),
        min_confidence: float = Query(0.0),
    ) -> dict[str, Any]:
        engine = _get_engine()
        result = engine.why(entity, limit=limit, min_confidence=min_confidence)
        return _result_to_dict(result)

    @r.get("/reality-intelligence/what-changed", dependencies=auth)
    def _what_changed(
        since: float = Query(0.0, description="Unix timestamp"),
        limit: int = Query(20),
        min_confidence: float = Query(0.0),
    ) -> dict[str, Any]:
        engine = _get_engine()
        result = engine.what_changed(
            since=since, limit=limit, min_confidence=min_confidence,
        )
        return _result_to_dict(result)

    @r.get("/reality-intelligence/evidence/{entity}", dependencies=auth)
    def _evidence(
        entity: str,
        limit: int = Query(20),
        min_confidence: float = Query(0.0),
    ) -> dict[str, Any]:
        engine = _get_engine()
        result = engine.find_evidence(
            entity, limit=limit, min_confidence=min_confidence,
        )
        return _result_to_dict(result)

    @r.get("/reality-intelligence/contradictions", dependencies=auth)
    def _contradictions(
        domain: str = Query("", description="Domain filter"),
        limit: int = Query(20),
        min_confidence: float = Query(0.0),
    ) -> dict[str, Any]:
        engine = _get_engine()
        result = engine.find_contradictions(
            domain=domain, limit=limit, min_confidence=min_confidence,
        )
        return _result_to_dict(result)

    @r.get("/reality-intelligence/lineage/{entity}", dependencies=auth)
    def _lineage(
        entity: str,
        limit: int = Query(20),
        min_confidence: float = Query(0.0),
    ) -> dict[str, Any]:
        engine = _get_engine()
        result = engine.trace_lineage(
            entity, limit=limit, min_confidence=min_confidence,
        )
        return _result_to_dict(result)

    @r.get("/reality-intelligence/domain/{domain}", dependencies=auth)
    def _domain_summary(
        domain: str,
        limit: int = Query(20),
        min_confidence: float = Query(0.0),
    ) -> dict[str, Any]:
        engine = _get_engine()
        result = engine.summarize_domain(
            domain, limit=limit, min_confidence=min_confidence,
        )
        return _result_to_dict(result)

    @r.get("/reality-intelligence/priorities", dependencies=auth)
    def _priorities(
        limit: int = Query(10),
        min_confidence: float = Query(0.0),
    ) -> dict[str, Any]:
        engine = _get_engine()
        result = engine.identify_priorities(
            limit=limit, min_confidence=min_confidence,
        )
        return _result_to_dict(result)

    return r
