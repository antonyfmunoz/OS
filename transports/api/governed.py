"""Governed mutation wrapper for FastAPI route handlers.

Usage in any route file::

    from transports.api.governed import governed_mutation

    async def _some_handler(request: Request):
        payload = await request.json()
        result = governed_mutation(
            mutation_name="settings_update",
            intent=f"Update setting {payload['key']}",
            execute_fn=lambda: (_do_write(payload), True),
            source="cockpit",
        )
        if not result.success:
            raise HTTPException(status_code=422, detail=result.to_http_dict())
        return result.to_http_dict()

This module lives in transports/ because it obtains the organism
singleton from the running daemon — a transport-layer concern.
The core routing logic lives in substrate/organism/mutation_router.py.
"""

from __future__ import annotations

import logging
from typing import Any, Callable

from substrate.organism.mutation_router import (
    MutationRequest,
    MutationResponse,
    MutationRouter,
)

logger = logging.getLogger(__name__)

_router_cache: MutationRouter | None = None


def _get_router() -> MutationRouter | None:
    global _router_cache
    if _router_cache is not None:
        return _router_cache

    try:
        from transports.api.cockpit_spine_router import _get_organism
        daemon = _get_organism()
        if daemon is None:
            return None
        _router_cache = MutationRouter(
            spine=daemon.governed_spine,
            registry=daemon.mutation_registry,
        )
        return _router_cache
    except Exception as exc:
        logger.debug("cannot obtain mutation router: %s", exc)
        return None


def reset_router_cache() -> None:
    global _router_cache
    _router_cache = None


def governed_mutation(
    mutation_name: str,
    intent: str,
    execute_fn: Callable[[], tuple[str, bool]],
    source: str = "cockpit",
    metadata: dict[str, Any] | None = None,
    verification_fn: Callable[[], bool] | None = None,
    rollback_fn: Callable[[], bool] | None = None,
    require_approval: bool | None = None,
) -> MutationResponse:
    """Submit a mutation through the governed spine.

    If the organism is not running, falls back to direct execution
    with ungoverned status so the caller still gets a response.
    """
    request = MutationRequest(
        mutation_name=mutation_name,
        intent=intent,
        execute_fn=execute_fn,
        source=source,
        metadata=metadata or {},
        verification_fn=verification_fn,
        rollback_fn=rollback_fn,
        require_approval=require_approval,
    )

    router = _get_router()
    if router is not None:
        return router.execute(request)

    logger.warning(
        "organism not running — executing %s ungoverned", mutation_name
    )
    try:
        output, success = execute_fn()
        return MutationResponse(
            success=success,
            output=output,
            status="completed_ungoverned",
        )
    except Exception as exc:
        logger.error("ungoverned execution failed for %s: %s", mutation_name, exc)
        return MutationResponse(
            success=False,
            output=str(exc),
            status="failed_ungoverned",
        )
