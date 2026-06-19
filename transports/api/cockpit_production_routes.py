"""Cockpit production routes — software production organism surface.

Mounted under /api/umh/ via include_router in cockpit.py.

Campaign 22. UMH transport layer. Instance-agnostic.
"""

from __future__ import annotations

import logging
import time
from typing import Any

from fastapi import APIRouter, Depends, Request

logger = logging.getLogger(__name__)

production_router: APIRouter = APIRouter()

_configured: bool = False


def configure(require_operator_dep: Any) -> None:
    global _configured, production_router
    _configured = True
    production_router = _build_router(require_operator_dep)


# ── Lazy runtime singletons ────────────────────────────────────────────────

_ops_runtime: Any = None
_workforce_runtime: Any = None
_review_runtime: Any = None
_compounding_runtime: Any = None
_factory_runtime: Any = None
_source_truth_runtime: Any = None


def _get_ops() -> Any:
    global _ops_runtime
    if _ops_runtime is None:
        try:
            from substrate.organism.production_ops_runtime import (
                ProductionOpsRuntime,
            )
            _ops_runtime = ProductionOpsRuntime()
        except Exception:
            logger.debug("ProductionOpsRuntime unavailable")
            return None
    return _ops_runtime


def _get_workforce() -> Any:
    global _workforce_runtime
    if _workforce_runtime is None:
        try:
            from substrate.organism.production_workforce_runtime import (
                ProductionWorkforceRuntime,
            )
            _workforce_runtime = ProductionWorkforceRuntime()
        except Exception:
            logger.debug("ProductionWorkforceRuntime unavailable")
            return None
    return _workforce_runtime


def _get_review() -> Any:
    global _review_runtime
    if _review_runtime is None:
        try:
            from substrate.organism.production_review_runtime import (
                ProductionReviewRuntime,
            )
            _review_runtime = ProductionReviewRuntime()
        except Exception:
            logger.debug("ProductionReviewRuntime unavailable")
            return None
    return _review_runtime


def _get_compounding() -> Any:
    global _compounding_runtime
    if _compounding_runtime is None:
        try:
            from substrate.organism.capability_compounding_runtime import (
                CapabilityCompoundingRuntime,
            )
            _compounding_runtime = CapabilityCompoundingRuntime()
        except Exception:
            logger.debug("CapabilityCompoundingRuntime unavailable")
            return None
    return _compounding_runtime


def _get_factory() -> Any:
    global _factory_runtime
    if _factory_runtime is None:
        try:
            from substrate.organism.product_factory_runtime import (
                ProductFactoryRuntime,
            )
            _factory_runtime = ProductFactoryRuntime()
        except Exception:
            logger.debug("ProductFactoryRuntime unavailable")
            return None
    return _factory_runtime


def _get_source_truth() -> Any:
    global _source_truth_runtime
    if _source_truth_runtime is None:
        try:
            from substrate.organism.source_truth_runtime import (
                SourceTruthRuntime,
            )
            _source_truth_runtime = SourceTruthRuntime()
        except Exception:
            logger.debug("SourceTruthRuntime unavailable")
            return None
    return _source_truth_runtime


def _unavailable(name: str) -> dict[str, Any]:
    return {"error": f"{name} not available", "status": "unavailable"}


# ── Route handlers ─────────────────────────────────────────────────────────

async def _snapshot(request: Request) -> dict[str, Any]:
    rt = _get_ops()
    if rt is None:
        return _unavailable("ProductionOpsRuntime")
    try:
        snap = rt.snapshot()
        if hasattr(snap, "to_dict"):
            return snap.to_dict()
        if hasattr(snap, "__dataclass_fields__"):
            from dataclasses import asdict
            return asdict(snap)
        return {"snapshot": snap}
    except Exception as exc:
        logger.debug("snapshot error: %s", exc)
        return {"error": str(exc)}


async def _phase(request: Request) -> dict[str, Any]:
    rt = _get_ops()
    if rt is None:
        return _unavailable("ProductionOpsRuntime")
    try:
        p = rt.phase()
        return {"phase": p if isinstance(p, str) else str(p)}
    except Exception as exc:
        logger.debug("phase error: %s", exc)
        return {"error": str(exc)}


async def _active(request: Request) -> dict[str, Any]:
    rt = _get_ops()
    if rt is None:
        return _unavailable("ProductionOpsRuntime")
    try:
        prods = rt.active_productions()
        return {"active_productions": prods, "count": len(prods)}
    except Exception as exc:
        logger.debug("active error: %s", exc)
        return {"error": str(exc)}


async def _workforce_summary(request: Request) -> dict[str, Any]:
    rt = _get_workforce()
    if rt is None:
        return _unavailable("ProductionWorkforceRuntime")
    try:
        return rt.summary()
    except Exception as exc:
        logger.debug("workforce summary error: %s", exc)
        return {"error": str(exc)}


async def _workforce_chart(request: Request) -> dict[str, Any]:
    rt = _get_workforce()
    if rt is None:
        return _unavailable("ProductionWorkforceRuntime")
    try:
        chart = rt.org_chart()
        return {"org_chart": chart}
    except Exception as exc:
        logger.debug("workforce chart error: %s", exc)
        return {"error": str(exc)}


async def _reviews(request: Request) -> dict[str, Any]:
    rt = _get_review()
    if rt is None:
        return _unavailable("ProductionReviewRuntime")
    try:
        pending = rt.pending_reviews()
        return {"pending_reviews": pending, "count": len(pending)}
    except Exception as exc:
        logger.debug("reviews error: %s", exc)
        return {"error": str(exc)}


async def _ship_readiness(request: Request) -> dict[str, Any]:
    rt = _get_review()
    if rt is None:
        return _unavailable("ProductionReviewRuntime")
    try:
        project_id = request.query_params.get("project_id", "")
        readiness = rt.ship_readiness(project_id) if project_id else rt.ship_readiness()
        return {"ship_readiness": readiness}
    except Exception as exc:
        logger.debug("ship readiness error: %s", exc)
        return {"error": str(exc)}


async def _learning(request: Request) -> dict[str, Any]:
    rt = _get_compounding()
    if rt is None:
        return _unavailable("CapabilityCompoundingRuntime")
    try:
        snap = rt.snapshot()
        if hasattr(snap, "to_dict"):
            return snap.to_dict()
        if hasattr(snap, "__dataclass_fields__"):
            from dataclasses import asdict
            return asdict(snap)
        return {"snapshot": snap}
    except Exception as exc:
        logger.debug("learning error: %s", exc)
        return {"error": str(exc)}


async def _compounding(request: Request) -> dict[str, Any]:
    rt = _get_compounding()
    if rt is None:
        return _unavailable("CapabilityCompoundingRuntime")
    try:
        promotions = rt.pending_promotions()
        return {"pending_promotions": promotions, "count": len(promotions)}
    except Exception as exc:
        logger.debug("compounding error: %s", exc)
        return {"error": str(exc)}


async def _products(request: Request) -> dict[str, Any]:
    rt = _get_factory()
    if rt is None:
        return _unavailable("ProductFactoryRuntime")
    try:
        products = rt.list_products()
        return {"products": products, "count": len(products)}
    except Exception as exc:
        logger.debug("products error: %s", exc)
        return {"error": str(exc)}


async def _lineage(request: Request, node_id: str) -> dict[str, Any]:
    rt = _get_source_truth()
    if rt is None:
        return _unavailable("SourceTruthRuntime")
    try:
        node_type = request.query_params.get("node_type", "work_packet")
        chain = rt.trace_lineage(node_id, node_type)
        if hasattr(chain, "to_dict"):
            return chain.to_dict()
        if hasattr(chain, "__dataclass_fields__"):
            from dataclasses import asdict
            return asdict(chain)
        return {"lineage": chain}
    except Exception as exc:
        logger.debug("lineage error: %s", exc)
        return {"error": str(exc)}


# ── Router builder ─────────────────────────────────────────────────────────

def _build_router(require_operator_dep: Any) -> APIRouter:
    r = APIRouter()
    auth = [Depends(require_operator_dep)]

    r.add_api_route(
        "/production/snapshot", _snapshot,
        methods=["GET"], dependencies=auth,
    )
    r.add_api_route(
        "/production/phase", _phase,
        methods=["GET"], dependencies=auth,
    )
    r.add_api_route(
        "/production/active", _active,
        methods=["GET"], dependencies=auth,
    )
    r.add_api_route(
        "/production/workforce", _workforce_summary,
        methods=["GET"], dependencies=auth,
    )
    r.add_api_route(
        "/production/workforce/chart", _workforce_chart,
        methods=["GET"], dependencies=auth,
    )
    r.add_api_route(
        "/production/reviews", _reviews,
        methods=["GET"], dependencies=auth,
    )
    r.add_api_route(
        "/production/ship-readiness", _ship_readiness,
        methods=["GET"], dependencies=auth,
    )
    r.add_api_route(
        "/production/learning", _learning,
        methods=["GET"], dependencies=auth,
    )
    r.add_api_route(
        "/production/compounding", _compounding,
        methods=["GET"], dependencies=auth,
    )
    r.add_api_route(
        "/production/products", _products,
        methods=["GET"], dependencies=auth,
    )
    r.add_api_route(
        "/production/lineage/{node_id}", _lineage,
        methods=["GET"], dependencies=auth,
    )

    return r
