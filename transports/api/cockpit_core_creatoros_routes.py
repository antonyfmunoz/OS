"""Cockpit CreatorOS projection routes — P4S-10.

Covers: /creatoros/activation. Thin transport wrapper over the projection-owned
accessor (projections/creatoros/integration/readiness.py::creatoros_readiness),
per rules/projection-read-surfaces.md. UMH transport layer.
"""

from __future__ import annotations

import logging

logger = logging.getLogger(__name__)


def register_creatoros_routes(router, _require_operator_role, helpers):
    """Register CreatorOS projection routes onto the given router."""

    @router.get("/creatoros/activation")
    def creatoros_activation():
        """CreatorOS projection activation / readiness — P4S-10.

        Proves CreatorOS is alive as a projection over the substrate: registered
        in the canonical seed view (under seed key "cos"), runtime registration
        status, and env-gated boot eligibility. Env-disabled-safe: returns a
        stable "disconnected" readiness response when CREATOROS_DATABASE_URL is
        unset, never a 500.
        """
        try:
            from projections.creatoros.integration.readiness import creatoros_readiness

            return creatoros_readiness()
        except Exception as e:
            return {"error": str(e), "projection_id": "cos", "registered_in_seed": False}
