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
singleton from the running daemon — a transport-layer concern. The core
routing and fail-closed logic lives in substrate/organism/mutation_router.py.

Fail-closed contract: when the organism daemon (and therefore the
GovernedExecutionSpine) is unavailable, this shim does NOT execute mutations
directly. It delegates DOWN into substrate's route_mutation_degraded(), which
rejects any non-LOW-risk or non-opted-in mutation with a 503-equivalent result
and performs no state change. Only a low-risk, LOCAL blast-radius mutation whose
spec sets degraded_mode_allowed=True may proceed — and only with a mandatory
degraded audit record. There is no ungoverned execution path.
"""

from __future__ import annotations

import logging
from typing import Any, Callable

from substrate.organism.mutation_router import (
    MutationRequest,
    MutationResponse,
    MutationRouter,
    route_mutation_degraded,
)

logger = logging.getLogger(__name__)

_router_cache: MutationRouter | None = None


def _get_router() -> MutationRouter | None:
    global _router_cache
    if _router_cache is not None:
        return _router_cache

    try:
        # Prefer the CANONICAL substrate organism port (populated by whichever
        # entrypoint started the daemon — operator_api registers it at startup).
        # Fall back to the cockpit_spine_router accessor for entrypoints that
        # configure() that router instead. Consulting only the latter meant an
        # entrypoint that registered the canonical port but never called
        # cockpit_spine_router.configure() (operator_api) saw NO organism, so the
        # governed path degraded every mutation and fail-closed HIGH decisions.
        daemon = None
        try:
            from substrate.sockets.organism_port import get_organism as _canonical_get_organism

            daemon = _canonical_get_organism()
        except Exception:  # noqa: BLE001 — fall back below
            daemon = None
        if daemon is None:
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

    If the organism daemon is running, the request routes through the
    GovernedExecutionSpine as normal. If it is NOT running, the request is
    handled by substrate's deterministic fail-closed gate: non-LOW-risk (and
    any non-opted-in) mutations are rejected with a 503-equivalent response and
    no state change; only low-risk local mutations that explicitly opt in may
    execute in degraded mode, always with a mandatory audit record.
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

    # Control plane unavailable. Delegate DOWN into substrate's fail-closed gate.
    # No ungoverned execution happens here — the decision is owned by substrate.
    return route_mutation_degraded(request)
