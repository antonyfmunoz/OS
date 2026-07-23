"""Deterministic legacy identity resolution — org/user → principal/tenant/membership.

Wave 1 bridge from the existing single-org runtime identity (UMH_ORG_ID /
authenticated Clerk user) to the canonical identity semantics of
``substrate.contracts.work_context``:

    org_id                → tenant_id      (sovereign boundary)
    authenticated user id → principal_id   (who acts)
    principal + tenant    → membership_id  (durable relationship — DERIVED
                            deterministically, NEVER from a browser session)

All derived values carry ``migration_status="legacy_derived"``. The same
principal + tenant always yields the same membership_id across processes and
restarts (test AA); a different tenant yields a different membership_id.

Fail-closed posture: ``resolve_principal_context`` returns a context that may
lack authority; WORK mutations must call ``require_work_authority()`` on it
(raises without principal+tenant+membership). Communication paths answer
safely without authority and never call it.

UMH substrate subsystem. Instance-agnostic — no founder/org literals.
"""

from __future__ import annotations

import hashlib
import logging
import os

from substrate.contracts.work_context import (
    MIGRATION_STATUS_LEGACY_DERIVED,
    PrincipalContext,
    PrincipalKind,
)

logger = logging.getLogger(__name__)

_MEMBERSHIP_PREFIX = "mem-"
_TENANT_PREFIX = "tenant-"


def derive_tenant_id(org_id: str) -> str:
    """Deterministic tenant id for a legacy org id. Empty in → empty out."""
    org_id = (org_id or "").strip()
    if not org_id:
        return ""
    if org_id.startswith(_TENANT_PREFIX):
        return org_id
    return f"{_TENANT_PREFIX}{org_id}"


def derive_membership_id(principal_id: str, tenant_id: str) -> str:
    """Durable membership id for one principal↔tenant relationship.

    Deterministic (stable across restarts and processes), never derived from
    a session. Empty when either side is missing — callers fail closed.
    """
    principal_id = (principal_id or "").strip()
    tenant_id = (tenant_id or "").strip()
    if not principal_id or not tenant_id:
        return ""
    digest = hashlib.sha256(f"{principal_id}|{tenant_id}".encode()).hexdigest()
    return f"{_MEMBERSHIP_PREFIX}{digest[:16]}"


def resolve_principal_context(
    user_id: str = "",
    org_id: str = "",
    authenticated_by: str = "",
    principal_kind: str = PrincipalKind.HUMAN.value,
) -> PrincipalContext:
    """Resolve the legacy identity pair into a canonical PrincipalContext.

    Falls back to UMH_ORG_ID (with the legacy projection env var as
    secondary fallback) / UMH_USER_ID when explicit values are not provided —
    the same resolution path a future tenant would use, never a hardcoded
    instance value.
    """
    user_id = (user_id or os.environ.get("UMH_USER_ID", "")).strip()
    org_id = (
        org_id or os.environ.get("UMH_ORG_ID", "") or os.environ.get("EOS_ORG_ID", "")
    ).strip()

    tenant_id = derive_tenant_id(org_id)
    membership_id = derive_membership_id(user_id, tenant_id)

    ctx = PrincipalContext(
        principal_id=user_id,
        principal_kind=principal_kind,
        tenant_id=tenant_id,
        membership_id=membership_id,
        authenticated_by=authenticated_by or ("env" if user_id else ""),
        authority_source="legacy_org_resolution",
        compatibility_origin=f"org:{org_id}" if org_id else "",
        migration_status=MIGRATION_STATUS_LEGACY_DERIVED,
    )
    if not ctx.has_work_authority():
        logger.debug(
            "principal resolution incomplete (principal=%s tenant=%s) — "
            "work mutations will fail closed",
            bool(user_id),
            bool(tenant_id),
        )
    return ctx


__all__ = [
    "derive_membership_id",
    "derive_tenant_id",
    "resolve_principal_context",
]
