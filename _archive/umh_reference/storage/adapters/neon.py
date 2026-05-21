"""Neon (PostgreSQL) connection layer with RLS tenant isolation.

RLS pattern: every transaction opens with
    SET LOCAL app.current_org_id = '<org_uuid>'
matching the saas pattern — one Postgres instance, one RLS
firewall, Python and TypeScript layers unified.

Usage:
    from umh.storage.adapters.neon import get_conn, resolve_venture, resolve_skill

    with get_conn() as cur:
        cur.execute("SELECT id FROM interactions LIMIT 5")
        rows = cur.fetchall()

This is the UMH-owned extraction of umh/db.py.
"""

from __future__ import annotations

import os
import re
from contextlib import contextmanager
from pathlib import Path
from typing import Generator


def _ensure_dotenv() -> None:
    """Load .env if dotenv is available. No-op if already loaded."""
    global _dotenv_loaded
    if _dotenv_loaded:
        return
    _dotenv_loaded = True
    env_path = Path("/opt/OS/services/.env")
    if not env_path.exists():
        env_path = Path("/opt/OS/umh/.env")
    if env_path.exists():
        try:
            from dotenv import load_dotenv

            load_dotenv(env_path)
        except ImportError:
            pass


_dotenv_loaded: bool = False

_venture_cache: dict[str, str] = {}
_skill_cache: dict[str, str] = {}
_caches_loaded: bool = False


def _get_database_url() -> str:
    _ensure_dotenv()
    url = os.environ.get("DATABASE_URL", "")
    if not url:
        raise RuntimeError("DATABASE_URL not set")
    return url


def _get_org_id() -> str:
    _ensure_dotenv()
    return os.environ.get("EOS_ORG_ID", "default")


def _get_user_id() -> str:
    _ensure_dotenv()
    return os.environ.get("EOS_USER_ID", "default")


def _init_module_constants() -> None:
    """Populate ORG_ID and USER_ID module-level constants from env."""
    global ORG_ID, USER_ID
    _ensure_dotenv()
    ORG_ID = os.environ.get("EOS_ORG_ID", "default")
    USER_ID = os.environ.get("EOS_USER_ID", "default")


ORG_ID: str = ""
USER_ID: str = ""


def _load_caches(cur: object) -> None:
    """Populate venture + skill lookup caches. Called once per process."""
    global _caches_loaded
    if _caches_loaded:
        return

    cur.execute("SELECT id, name FROM ventures")
    for row in cur.fetchall():
        slug = row["name"].lower().replace(" ", "_")
        _venture_cache[slug] = str(row["id"])

    cur.execute("SELECT id, name FROM skills")
    for row in cur.fetchall():
        _skill_cache[row["name"]] = str(row["id"])

    _caches_loaded = True


@contextmanager
def get_conn(org_id: str | None = None) -> Generator:
    """Open a Neon connection with RLS enabled for org_id.

    Every transaction begins with SET LOCAL app.current_org_id so the
    PostgreSQL RLS firewall scopes all queries to the correct tenant.
    """
    import psycopg2
    import psycopg2.extras

    if not ORG_ID:
        _init_module_constants()

    if org_id is None:
        org_id = _get_org_id()

    database_url = _get_database_url()

    try:
        conn = psycopg2.connect(database_url)
    except Exception as e:
        safe_msg = re.sub(r"://[^@]+@", "://***:***@", str(e))
        import psycopg2 as _pg

        raise _pg.OperationalError(f"Neon connection failed: {safe_msg}") from None
    try:
        with conn:
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                cur.execute("SET LOCAL app.current_org_id = %s", (org_id,))
                _load_caches(cur)
                yield cur
    finally:
        conn.close()


def resolve_venture(slug: str | None) -> str | None:
    """Map a Python venture slug to its Neon UUID."""
    if not slug:
        return None
    normalized = slug.lower().replace(" ", "_")
    return _venture_cache.get(normalized)


def resolve_skill(name: str | None) -> str | None:
    """Map a Python skill name to its Neon UUID."""
    if not name:
        return None
    return _skill_cache.get(name)
