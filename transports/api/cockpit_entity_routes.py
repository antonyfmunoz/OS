"""Cockpit entity and product routes — portfolio, departments, roles, companies
CRUD, product connections.

Extracted from cockpit.py (Phase 10.0) to bring the main file under 3000 lines.
All routes are mounted under /api/umh/ via include_router in cockpit.py.

Auth model: configure() must be called before include_router(). It receives
the real operator-auth dependency and _get_org_id from cockpit.py and wires
them into route handlers.

UMH transport layer. Instance-agnostic.
"""

from __future__ import annotations

import logging
from typing import Any, Callable

from fastapi import APIRouter, Depends

logger = logging.getLogger(__name__)

entity_router: APIRouter = APIRouter()

_get_org_id: Callable[[], str] = lambda: ""
_configured: bool = False


def configure(
    get_org_id_fn: Callable[[], str],
    require_operator_dep: Any,
) -> None:
    """Wire shared cockpit utilities into the entity router.

    Must be called once from cockpit.py before include_router(). Rebuilds
    the router with the injected dependencies.
    """
    global _get_org_id, _configured, entity_router

    _get_org_id = get_org_id_fn
    _configured = True

    entity_router = _build_router(require_operator_dep)


def _build_router(require_operator_dep: Any) -> APIRouter:
    """Construct the entity router with route registrations."""
    r = APIRouter()

    # ── Entity and product routes (no operator auth required) ──────────────

    r.add_api_route("/entities/portfolio", _entity_portfolio, methods=["GET"])
    r.add_api_route("/entities/departments", _entity_departments, methods=["GET"])
    r.add_api_route("/entities/departments/{slug}", _entity_department_detail, methods=["GET"])
    r.add_api_route("/entities/roles", _entity_roles, methods=["GET"])
    r.add_api_route("/entities/companies", _entity_companies, methods=["GET"])
    r.add_api_route("/entities/companies/{company_id}", _entity_company_detail, methods=["GET"])
    r.add_api_route("/entities/companies", _upsert_company, methods=["POST"])
    r.add_api_route("/products", _product_connections, methods=["GET"])
    r.add_api_route("/products/refresh", _refresh_product_connections, methods=["POST"])

    return r


# ── Entity views (Portfolio / Company / Department / Role) ───────────────────


async def _entity_portfolio():
    """Portfolio-level view — all companies, cross-venture summary."""
    org_id = _get_org_id()
    try:
        from projections.eos.entities import default_departments, default_roles

        departments = default_departments(org_id)
        roles = default_roles(org_id)
        return {
            "org_id": org_id,
            "department_count": len(departments),
            "role_count": len(roles),
            "departments": [
                {
                    "name": d.name,
                    "slug": d.slug,
                    "agent_name": d.agent_name,
                    "permission_tier": d.permission_tier,
                    "metrics": d.metrics,
                }
                for d in departments
            ],
        }
    except Exception as e:
        return {"error": str(e), "departments": []}


async def _entity_departments():
    """All departments with agents, metrics, workflows."""
    org_id = _get_org_id()
    try:
        from projections.eos.entities import default_departments
        from projections.eos.agents import AGENT_CLASSES

        departments = default_departments(org_id)
        result = []
        for dept in departments:
            agent_cls = AGENT_CLASSES.get(dept.slug)
            agent_info = None
            if agent_cls:
                agent = agent_cls(org_id=org_id)
                agent_info = {
                    "skill_count": len(agent.skills),
                    "skills": list(agent.skills.keys()),
                    "permission_tier": agent.PERMISSION_TIER.value,
                    "browser_capable": agent.metadata().get("browser_capable", False),
                }
            result.append(
                {
                    "name": dept.name,
                    "slug": dept.slug,
                    "agent_name": dept.agent_name,
                    "permission_tier": dept.permission_tier,
                    "roles": dept.roles,
                    "metrics": dept.metrics,
                    "workflows": dept.workflows,
                    "agent": agent_info,
                }
            )
        return {"departments": result}
    except Exception as e:
        return {"error": str(e), "departments": []}


async def _entity_department_detail(slug: str):
    """Single department detail with full agent skills."""
    org_id = _get_org_id()
    try:
        from projections.eos.entities import default_departments, default_roles
        from projections.eos.agents import AGENT_CLASSES

        departments = default_departments(org_id)
        dept = next((d for d in departments if d.slug == slug), None)
        if not dept:
            return {"error": f"department {slug} not found"}

        roles = [r for r in default_roles(org_id) if r.department == slug]
        agent_cls = AGENT_CLASSES.get(slug)
        agent_detail = None
        if agent_cls:
            agent = agent_cls(org_id=org_id)
            agent_detail = {
                "skills": agent.skills,
                "permission_tier": agent.PERMISSION_TIER.value,
                "metadata": agent.metadata(),
            }

        return {
            "department": {
                "name": dept.name,
                "slug": dept.slug,
                "agent_name": dept.agent_name,
                "permission_tier": dept.permission_tier,
                "roles": dept.roles,
                "metrics": dept.metrics,
                "workflows": dept.workflows,
            },
            "roles": [
                {
                    "name": r.name,
                    "operator": r.operator.value,
                    "permission_tier": r.permission_tier,
                    "responsibilities": r.responsibilities,
                    "workflows": r.workflows,
                    "metrics": r.metrics,
                }
                for r in roles
            ],
            "agent": agent_detail,
        }
    except Exception as e:
        return {"error": str(e)}


async def _entity_roles():
    """All roles across all departments."""
    org_id = _get_org_id()
    try:
        from projections.eos.entities import default_roles

        roles = default_roles(org_id)
        return {
            "roles": [
                {
                    "name": r.name,
                    "department": r.department,
                    "operator": r.operator.value,
                    "permission_tier": r.permission_tier,
                    "responsibilities": r.responsibilities,
                    "workflows": r.workflows,
                    "metrics": r.metrics,
                }
                for r in roles
            ]
        }
    except Exception as e:
        return {"error": str(e), "roles": []}


# ── Companies CRUD ────────────────────────────────────────────────────────────


async def _entity_companies():
    """List all companies for the current org."""
    org_id = _get_org_id()
    try:
        from substrate.state.stores.entity_store import EntityStore

        store = EntityStore(org_id)
        persisted = store.list_companies()
        if persisted:
            return {"companies": persisted}

        from projections.eos.entities import default_company

        company = default_company(org_id)
        return {
            "companies": [
                {
                    "id": company.id,
                    "name": company.name,
                    "org_id": company.organization_id,
                    "venture_id": company.venture_id,
                    "stage": company.stage,
                    "stage_name": company.stage_name,
                    "departments": company.departments,
                    "north_star": company.north_star,
                }
            ]
        }
    except Exception as e:
        return {"error": str(e), "companies": []}


async def _entity_company_detail(company_id: str):
    """Get a single company by ID."""
    org_id = _get_org_id()
    try:
        from substrate.state.stores.entity_store import EntityStore

        store = EntityStore(org_id)
        company = store.get_company(company_id)
        if company:
            return {"company": company}

        from projections.eos.entities import default_company

        default = default_company(org_id)
        if default.id == company_id:
            return {
                "company": {
                    "id": default.id,
                    "name": default.name,
                    "org_id": default.organization_id,
                    "venture_id": default.venture_id,
                    "stage": default.stage,
                    "stage_name": default.stage_name,
                    "departments": default.departments,
                    "north_star": default.north_star,
                }
            }
        return {"error": f"company {company_id} not found"}
    except Exception as e:
        return {"error": str(e)}


async def _upsert_company(payload: dict):
    """Create or update a company."""
    org_id = _get_org_id()
    name = payload.get("name", "")
    if not name:
        return {"error": "name required"}
    try:
        from substrate.state.stores.entity_store import EntityStore

        store = EntityStore(org_id)
        company_id = payload.get("id", "")
        if not company_id:
            from uuid import uuid4

            company_id = f"company-{uuid4().hex[:12]}"

        store.save_company(
            company_id,
            name,
            org_id=org_id,
            venture_id=payload.get("venture_id", ""),
            portfolio_id=payload.get("portfolio_id", ""),
            stage=payload.get("stage", 1),
            stage_name=payload.get("stage_name", "validation"),
            departments=payload.get("departments", []),
            north_star=payload.get("north_star", ""),
            metadata=payload.get("metadata", {}),
        )
        return {"ok": True, "company_id": company_id}
    except Exception as e:
        return {"error": str(e)}


# ── Product connections (EOS / CreatorOS / LYFEOS) ───────────────────────────


async def _product_connections():
    """Status of all three SaaS product connections."""
    try:
        from substrate.integrations.product_connections import get_product_manager

        mgr = get_product_manager()
        return {
            "connections": mgr.all_connections(),
            "summary": mgr.cross_product_summary(),
        }
    except Exception as e:
        return {"error": str(e), "connections": []}


async def _refresh_product_connections():
    """Re-check all product connections."""
    try:
        from substrate.integrations.product_connections import get_product_manager

        mgr = get_product_manager()
        mgr.refresh()
        return {"refreshed": True, "connections": mgr.all_connections()}
    except Exception as e:
        return {"error": str(e)}
