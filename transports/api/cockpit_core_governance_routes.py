"""Cockpit governance routes — extracted from cockpit_core_routes.py.

Covers: /governance, /governance/tiers, /governance/tier-check, /approvals.
Phase 0.3 route split. UMH transport layer.
"""
from __future__ import annotations

import logging
from typing import Any

from fastapi import Depends

logger = logging.getLogger(__name__)


def register_governance_routes(router, _require_operator_role, helpers):
    """Register governance and approval routes onto the given router."""
    _get_organism = helpers["_get_organism"]

    @router.get("/approvals")
    async def approvals():
        daemon = _get_organism()
        if daemon is None:
            return []
        return daemon.approval_store.list_approvals()

    @router.post("/approvals/{approval_id}/approve", dependencies=[Depends(_require_operator_role)])
    async def approve_item(approval_id: str):
        daemon = _get_organism()
        if daemon is None:
            return {"ok": False, "error": "organism not running"}
        result = daemon.approval_store.decide(approval_id, "approved")
        if result is None:
            return {"ok": False, "error": "approval not found"}
        return {"ok": True}

    @router.post("/approvals/{approval_id}/deny", dependencies=[Depends(_require_operator_role)])
    async def deny_item(approval_id: str, payload: dict | None = None):
        daemon = _get_organism()
        if daemon is None:
            return {"ok": False, "error": "organism not running"}
        result = daemon.approval_store.decide(approval_id, "denied")
        if result is None:
            return {"ok": False, "error": "approval not found"}
        return {"ok": True}

    def _get_policy_engine():
        """Access the PolicyEngine — try pipeline first, direct instantiation as fallback."""
        try:
            from transports.api.app import _pipeline

            if _pipeline and hasattr(_pipeline, "_policy") and _pipeline._policy is not None:
                return _pipeline._policy
        except (ImportError, AttributeError):
            pass
        try:
            from substrate.governance.policy_engine import PolicyEngine

            return PolicyEngine(safe_roots=["/opt/OS"])
        except Exception:
            return None

    @router.get("/governance")
    async def governance_policy():
        """Return current governance policy table — risk class → authority level."""
        from substrate.governance.authority import AuthorityLevel
        from substrate.governance.risk_classes import RiskClass

        engine = _get_policy_engine()
        if engine is None:
            return {"error": "policy engine not available"}

        from substrate.governance.policy_engine import _DEFAULT_POLICY

        result = []
        for rc in RiskClass:
            authority = _DEFAULT_POLICY.get(rc, AuthorityLevel.DENY)
            result.append(
                {
                    "risk_class": rc.value,
                    "risk_level": rc.to_risk_level().value,
                    "authority": authority.name,
                    "requires_human": authority.requires_human,
                    "is_blocked": authority.is_blocked,
                    "is_blocking_class": rc.is_blocking,
                }
            )

        return {
            "policies": result,
            "safe_roots": engine.safe_roots,
            "allowed_shell_prefixes": engine.allowed_shell_prefixes,
        }

    @router.patch("/governance", dependencies=[Depends(_require_operator_role)])
    async def update_governance(payload: dict):
        """Update governance policy at runtime.

        Accepts: {"policies": {"risk_class_name": "AUTHORITY_LEVEL", ...}}
        Example: {"policies": {"SAFE_WRITE": "AUTONOMOUS", "REVERSIBLE_WRITE": "APPROVE"}}
        """
        from substrate.governance.authority import AuthorityLevel
        from substrate.governance.policy_engine import _DEFAULT_POLICY
        from substrate.governance.risk_classes import RiskClass

        policies = payload.get("policies", {})
        applied = []

        for rc_name, auth_name in policies.items():
            try:
                rc = RiskClass[rc_name]
                auth = AuthorityLevel[auth_name]
                _DEFAULT_POLICY[rc] = auth
                applied.append({"risk_class": rc_name, "authority": auth_name})
            except KeyError:
                continue

        return {"ok": True, "applied": applied}

    @router.get("/governance/tiers")
    async def permission_tiers():
        """Return the 4-tier permission model with action mappings."""
        from substrate.types import PermissionTier, TIER_ACTION_MAP, _PERMISSION_TIER_RANK

        tiers = []
        for tier in PermissionTier:
            tiers.append(
                {
                    "tier": tier.value,
                    "rank": tier.rank,
                    "actions": sorted(TIER_ACTION_MAP[tier]),
                }
            )
        return {"tiers": tiers}

    @router.get("/governance/tier-check")
    async def tier_check(action: str, tier: str = "execute"):
        """Check if a permission tier allows a specific action."""
        from substrate.types import PermissionTier, required_tier_for_action

        try:
            caller_tier = PermissionTier(tier)
        except ValueError:
            return {
                "error": f"invalid tier: {tier}",
                "valid_tiers": [t.value for t in PermissionTier],
            }

        required = required_tier_for_action(action)
        permitted = caller_tier.permits(required)
        return {
            "action": action,
            "caller_tier": caller_tier.value,
            "required_tier": required.value,
            "permitted": permitted,
        }
