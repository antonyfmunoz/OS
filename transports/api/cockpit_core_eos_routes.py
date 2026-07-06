"""Cockpit EOS projection routes — extracted from cockpit_core_routes.py.

Covers: /eos/pipeline, /eos/kpis, /eos/activity, /eos/accountability, /eos/intelligence.
Phase 0.3 route split. UMH transport layer.
"""
from __future__ import annotations

import logging
import os
from typing import Any

logger = logging.getLogger(__name__)


def _get_org_id() -> str:
    """Get org_id from context for projection queries."""
    try:
        from substrate.state.context.context import load_context_from_env

        ctx = load_context_from_env()
        return str(ctx.org_id)
    except Exception:
        return ""


def register_eos_routes(router, _require_operator_role, helpers):
    """Register EOS projection routes onto the given router."""

    @router.get("/eos/pipeline")
    def eos_pipeline():
        """Pipeline view — CRM data projected into sales stages."""
        try:
            from projections.eos.views.pipeline import PipelineView

            org_id = _get_org_id()
            view = PipelineView(org_id=org_id)
            snap = view.snapshot()
            return {
                "stages": [
                    {"name": s.name, "count": s.count, "value": s.total_value} for s in snap.stages
                ],
                "total_leads": snap.total_leads,
                "total_value": snap.total_value,
                "conversion_rate": snap.conversion_rate,
            }
        except Exception as e:
            return {"error": str(e), "stages": []}

    @router.get("/eos/kpis")
    def eos_kpis():
        """KPI dashboard — business metrics as cards."""
        try:
            from projections.eos.views.kpis import KPIView

            org_id = _get_org_id()
            view = KPIView(org_id=org_id)
            dash = view.dashboard()
            return {
                "cards": [
                    {
                        "name": c.name,
                        "value": c.value,
                        "unit": c.unit,
                        "trend": c.trend,
                        "period": c.period,
                    }
                    for c in dash.cards
                ],
                "venture_id": dash.venture_id,
            }
        except Exception as e:
            return {"error": str(e), "cards": []}

    @router.get("/eos/activity")
    def eos_activity(limit: int = 30):
        """Activity feed — recent system events in chronological order."""
        try:
            from projections.eos.views.activity import ActivityView

            org_id = _get_org_id()
            view = ActivityView(org_id=org_id)
            feed = view.feed(limit=limit)
            return {
                "entries": [
                    {
                        "event_type": e.event_type,
                        "summary": e.summary,
                        "agent": e.agent,
                        "timestamp": e.timestamp,
                    }
                    for e in feed.entries
                ],
                "total_count": feed.total_count,
            }
        except Exception as e:
            return {"error": str(e), "entries": []}

    @router.get("/eos/accountability")
    def eos_accountability():
        """Accountability stats — commitment tracking, streaks, fulfillment rate."""
        try:
            from substrate.governance.accountability.accountability import AccountabilityEngine
            from substrate.state.context.context import load_context_from_env

            ctx = load_context_from_env()
            ae = AccountabilityEngine(ctx)
            return ae.stats()
        except Exception as e:
            return {"error": str(e)}

    @router.get("/eos/intelligence")
    def eos_intelligence():
        """Intelligence layer health — pattern/decision stats."""
        try:
            from substrate.intelligence.runtime import IntelligenceRuntime

            intel = IntelligenceRuntime()
            return intel.health()
        except Exception as e:
            return {"error": str(e)}

    @router.get("/eos/activation")
    def eos_activation():
        """EOS projection activation / readiness — WP-P4-006.

        Proves EOS is alive as a projection over the substrate: registered in the
        canonical seed view, runtime registration status, and env-gated boot
        eligibility. Env-disabled-safe: returns a stable "disconnected" readiness
        response when EOS_DATABASE_URL is unset, never a 500.
        """
        try:
            from projections.eos.integration.readiness import eos_readiness

            return eos_readiness()
        except Exception as e:
            return {"error": str(e), "projection_id": "eos", "registered_in_seed": False}

    @router.get("/eos/action-proposals")
    def eos_action_proposals_route(limit: int = 50):
        """EOS ActionProposal read seam — WP-P4-EOS-ACTION-PROPOSAL-READ-001.

        Read-only view of the EOS agent_actions pending queue mapped into UMH
        approval semantics (#182 approval-queue-row seam). Execution is disabled
        by contract (execute_enabled=false). Env-disabled-safe: stable
        "disconnected" envelope when EOS_DATABASE_URL is unset, never a 500.
        """
        try:
            from projections.eos.integration.action_proposals import eos_action_proposals

            return eos_action_proposals(limit=limit)
        except Exception as e:
            return {
                "error": str(e),
                "projection_id": "eos",
                "surface": "action_proposals",
                "execute_enabled": False,
                "proposal_count": 0,
                "proposals": [],
            }
