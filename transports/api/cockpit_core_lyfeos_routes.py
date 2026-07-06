"""Cockpit LyfeOS projection routes — P4S-10.

Covers: /lyfeos/activation. Thin transport wrapper over the projection-owned
accessor (projections/lyfeos/integration/readiness.py::lyfeos_readiness), per
rules/projection-read-surfaces.md. UMH transport layer.
"""

from __future__ import annotations

import logging

logger = logging.getLogger(__name__)


def register_lyfeos_routes(router, _require_operator_role, helpers):
    """Register LyfeOS projection routes onto the given router."""

    @router.get("/lyfeos/activation")
    def lyfeos_activation():
        """LyfeOS projection activation / readiness — P4S-10.

        Proves LyfeOS is alive as a projection over the substrate: registered in
        the canonical seed view, runtime registration status, and env-gated boot
        eligibility. Env-disabled-safe: returns a stable "disconnected" readiness
        response when LYFEOS_DATABASE_URL is unset, never a 500.
        """
        try:
            from projections.lyfeos.integration.readiness import lyfeos_readiness

            return lyfeos_readiness()
        except Exception as e:
            return {"error": str(e), "projection_id": "lyfeos", "registered_in_seed": False}
