"""EntityStore — persistence layer for the entity hierarchy.

Covers: users, portfolios, companies, departments, roles, workflows, dashboards.
Each entity has CREATE TABLE IF NOT EXISTS, upsert, get, and list operations.
Tables are created lazily on first use.
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from substrate.state.storage.db import get_conn

logger = logging.getLogger(__name__)

_TABLES_CREATED = False


def _ensure_tables(org_id: str) -> None:
    global _TABLES_CREATED
    if _TABLES_CREATED:
        return
    try:
        with get_conn(org_id) as cur:
            cur.execute("""
                CREATE TABLE IF NOT EXISTS umh_users (
                    id TEXT PRIMARY KEY,
                    email TEXT NOT NULL,
                    display_name TEXT DEFAULT '',
                    auth_provider TEXT DEFAULT 'local',
                    auth_provider_id TEXT DEFAULT '',
                    portfolio_id TEXT,
                    preferences JSONB DEFAULT '{}',
                    role_scope TEXT DEFAULT 'founder',
                    active BOOLEAN DEFAULT TRUE,
                    created_at TIMESTAMPTZ DEFAULT NOW(),
                    last_login TIMESTAMPTZ,
                    metadata JSONB DEFAULT '{}'
                )
            """)
            cur.execute("""
                CREATE TABLE IF NOT EXISTS umh_portfolios (
                    id TEXT PRIMARY KEY,
                    user_id TEXT NOT NULL,
                    companies JSONB DEFAULT '[]',
                    created_at TIMESTAMPTZ DEFAULT NOW(),
                    metadata JSONB DEFAULT '{}'
                )
            """)
            cur.execute("""
                CREATE TABLE IF NOT EXISTS umh_companies (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    org_id TEXT NOT NULL,
                    venture_id TEXT DEFAULT '',
                    portfolio_id TEXT,
                    stage INTEGER DEFAULT 1,
                    stage_name TEXT DEFAULT 'validation',
                    bis_id TEXT,
                    departments JSONB DEFAULT '[]',
                    north_star TEXT DEFAULT '',
                    active BOOLEAN DEFAULT TRUE,
                    created_at TIMESTAMPTZ DEFAULT NOW(),
                    metadata JSONB DEFAULT '{}'
                )
            """)
            cur.execute("""
                CREATE TABLE IF NOT EXISTS umh_departments (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    slug TEXT NOT NULL,
                    org_id TEXT NOT NULL,
                    venture_id TEXT DEFAULT '',
                    agent_name TEXT,
                    permission_tier TEXT DEFAULT 'execute',
                    roles JSONB DEFAULT '[]',
                    metrics JSONB DEFAULT '[]',
                    workflows JSONB DEFAULT '[]',
                    active BOOLEAN DEFAULT TRUE,
                    created_at TIMESTAMPTZ DEFAULT NOW(),
                    metadata JSONB DEFAULT '{}'
                )
            """)
            cur.execute("""
                CREATE TABLE IF NOT EXISTS umh_roles (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    department TEXT NOT NULL,
                    org_id TEXT NOT NULL,
                    venture_id TEXT DEFAULT '',
                    operator TEXT DEFAULT 'hybrid',
                    agent_name TEXT,
                    permission_tier TEXT DEFAULT 'execute',
                    responsibilities JSONB DEFAULT '[]',
                    workflows JSONB DEFAULT '[]',
                    metrics JSONB DEFAULT '[]',
                    tools JSONB DEFAULT '[]',
                    documents JSONB DEFAULT '[]',
                    dashboard_id TEXT,
                    autonomy_level INTEGER DEFAULT 2,
                    active BOOLEAN DEFAULT TRUE,
                    created_at TIMESTAMPTZ DEFAULT NOW(),
                    metadata JSONB DEFAULT '{}'
                )
            """)
            cur.execute("""
                CREATE TABLE IF NOT EXISTS umh_workflows (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    slug TEXT NOT NULL,
                    department TEXT DEFAULT '',
                    org_id TEXT DEFAULT '',
                    trigger_type TEXT DEFAULT 'manual',
                    trigger_config JSONB DEFAULT '{}',
                    steps JSONB DEFAULT '[]',
                    output_artifacts JSONB DEFAULT '[]',
                    permission_tier TEXT DEFAULT 'execute',
                    active BOOLEAN DEFAULT TRUE,
                    version INTEGER DEFAULT 1,
                    created_at TIMESTAMPTZ DEFAULT NOW(),
                    metadata JSONB DEFAULT '{}'
                )
            """)
            cur.execute("""
                CREATE TABLE IF NOT EXISTS umh_dashboards (
                    id TEXT PRIMARY KEY,
                    role_id TEXT,
                    department TEXT DEFAULT '',
                    org_id TEXT DEFAULT '',
                    widgets JSONB DEFAULT '[]',
                    layout TEXT DEFAULT 'grid',
                    created_at TIMESTAMPTZ DEFAULT NOW(),
                    metadata JSONB DEFAULT '{}'
                )
            """)
        _TABLES_CREATED = True
    except Exception as e:
        logger.debug("Entity table creation deferred: %s", e)


class EntityStore:
    """Unified persistence for the entity hierarchy."""

    def __init__(self, org_id: str) -> None:
        self._org_id = org_id
        _ensure_tables(org_id)

    def _upsert(self, table: str, entity_id: str, data: dict[str, Any]) -> None:
        cols = list(data.keys())
        vals = list(data.values())
        placeholders = ", ".join(["%s"] * len(cols))
        col_names = ", ".join(cols)
        update_clause = ", ".join(f"{c} = EXCLUDED.{c}" for c in cols if c != "id")
        try:
            with get_conn(self._org_id) as cur:
                cur.execute(
                    f"INSERT INTO {table} (id, {col_names}) VALUES (%s, {placeholders}) "
                    f"ON CONFLICT (id) DO UPDATE SET {update_clause}",
                    [entity_id, *vals],
                )
        except Exception as e:
            logger.error("EntityStore upsert %s failed: %s", table, e)

    def _get(self, table: str, entity_id: str) -> dict[str, Any] | None:
        try:
            with get_conn(self._org_id) as cur:
                cur.execute(f"SELECT * FROM {table} WHERE id = %s", (entity_id,))
                row = cur.fetchone()
                return dict(row) if row else None
        except Exception as e:
            logger.debug("EntityStore get %s failed: %s", table, e)
            return None

    def _list(self, table: str, where: str = "", params: tuple = ()) -> list[dict[str, Any]]:
        try:
            with get_conn(self._org_id) as cur:
                query = f"SELECT * FROM {table}"
                if where:
                    query += f" WHERE {where}"
                query += " ORDER BY created_at DESC"
                cur.execute(query, params)
                return [dict(row) for row in cur.fetchall()]
        except Exception as e:
            logger.debug("EntityStore list %s failed: %s", table, e)
            return []

    def save_user(self, user_id: str, email: str, display_name: str = "", **kwargs: Any) -> None:
        self._upsert(
            "umh_users",
            user_id,
            {
                "email": email,
                "display_name": display_name,
                "role_scope": kwargs.get("role_scope", "founder"),
                "preferences": json.dumps(kwargs.get("preferences", {})),
                "metadata": json.dumps(kwargs.get("metadata", {})),
            },
        )

    def get_user(self, user_id: str) -> dict[str, Any] | None:
        return self._get("umh_users", user_id)

    def list_users(self) -> list[dict[str, Any]]:
        return self._list("umh_users")

    def save_portfolio(
        self, portfolio_id: str, user_id: str, companies: list[str] | None = None
    ) -> None:
        self._upsert(
            "umh_portfolios",
            portfolio_id,
            {
                "user_id": user_id,
                "companies": json.dumps(companies or []),
            },
        )

    def get_portfolio(self, portfolio_id: str) -> dict[str, Any] | None:
        return self._get("umh_portfolios", portfolio_id)

    def save_company(self, company_id: str, name: str, **kwargs: Any) -> None:
        self._upsert(
            "umh_companies",
            company_id,
            {
                "name": name,
                "org_id": kwargs.get("org_id", self._org_id),
                "venture_id": kwargs.get("venture_id", ""),
                "portfolio_id": kwargs.get("portfolio_id", ""),
                "stage": kwargs.get("stage", 1),
                "stage_name": kwargs.get("stage_name", "validation"),
                "departments": json.dumps(kwargs.get("departments", [])),
                "north_star": kwargs.get("north_star", ""),
                "metadata": json.dumps(kwargs.get("metadata", {})),
            },
        )

    def get_company(self, company_id: str) -> dict[str, Any] | None:
        return self._get("umh_companies", company_id)

    def list_companies(self) -> list[dict[str, Any]]:
        return self._list("umh_companies", "org_id = %s", (self._org_id,))

    def save_department(self, dept_id: str, name: str, slug: str, **kwargs: Any) -> None:
        self._upsert(
            "umh_departments",
            dept_id,
            {
                "name": name,
                "slug": slug,
                "org_id": self._org_id,
                "agent_name": kwargs.get("agent_name", ""),
                "permission_tier": kwargs.get("permission_tier", "execute"),
                "roles": json.dumps(kwargs.get("roles", [])),
                "metrics": json.dumps(kwargs.get("metrics", [])),
                "workflows": json.dumps(kwargs.get("workflows", [])),
                "metadata": json.dumps(kwargs.get("metadata", {})),
            },
        )

    def list_departments(self) -> list[dict[str, Any]]:
        return self._list("umh_departments", "org_id = %s", (self._org_id,))

    def save_role(self, role_id: str, name: str, department: str, **kwargs: Any) -> None:
        self._upsert(
            "umh_roles",
            role_id,
            {
                "name": name,
                "department": department,
                "org_id": self._org_id,
                "operator": kwargs.get("operator", "hybrid"),
                "permission_tier": kwargs.get("permission_tier", "execute"),
                "responsibilities": json.dumps(kwargs.get("responsibilities", [])),
                "workflows": json.dumps(kwargs.get("workflows", [])),
                "metrics": json.dumps(kwargs.get("metrics", [])),
                "tools": json.dumps(kwargs.get("tools", [])),
                "documents": json.dumps(kwargs.get("documents", [])),
                "autonomy_level": kwargs.get("autonomy_level", 2),
                "metadata": json.dumps(kwargs.get("metadata", {})),
            },
        )

    def list_roles(self, department: str = "") -> list[dict[str, Any]]:
        if department:
            return self._list(
                "umh_roles", "org_id = %s AND department = %s", (self._org_id, department)
            )
        return self._list("umh_roles", "org_id = %s", (self._org_id,))

    def save_workflow(self, wf_id: str, name: str, slug: str, **kwargs: Any) -> None:
        self._upsert(
            "umh_workflows",
            wf_id,
            {
                "name": name,
                "slug": slug,
                "department": kwargs.get("department", ""),
                "org_id": self._org_id,
                "trigger_type": kwargs.get("trigger_type", "manual"),
                "trigger_config": json.dumps(kwargs.get("trigger_config", {})),
                "steps": json.dumps(kwargs.get("steps", [])),
                "output_artifacts": json.dumps(kwargs.get("output_artifacts", [])),
                "permission_tier": kwargs.get("permission_tier", "execute"),
                "metadata": json.dumps(kwargs.get("metadata", {})),
            },
        )

    def list_workflows(self, department: str = "") -> list[dict[str, Any]]:
        if department:
            return self._list(
                "umh_workflows", "org_id = %s AND department = %s", (self._org_id, department)
            )
        return self._list("umh_workflows", "org_id = %s", (self._org_id,))

    def save_dashboard(self, dash_id: str, **kwargs: Any) -> None:
        self._upsert(
            "umh_dashboards",
            dash_id,
            {
                "role_id": kwargs.get("role_id", ""),
                "department": kwargs.get("department", ""),
                "org_id": self._org_id,
                "widgets": json.dumps(kwargs.get("widgets", [])),
                "layout": kwargs.get("layout", "grid"),
                "metadata": json.dumps(kwargs.get("metadata", {})),
            },
        )

    def list_dashboards(self) -> list[dict[str, Any]]:
        return self._list("umh_dashboards", "org_id = %s", (self._org_id,))
