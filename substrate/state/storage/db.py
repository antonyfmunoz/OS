"""
Neon (PostgreSQL) connection layer for the Python AI layer.

RLS pattern: every transaction opens with
    SET LOCAL app.current_org_id = '<org_uuid>'
matching the saas pattern exactly — one Postgres instance, one RLS
firewall, Python and TypeScript layers unified.

Usage:
    from substrate.state.storage.db import get_conn, resolve_venture, resolve_skill, ORG_ID, USER_ID

    with get_conn() as cur:
        cur.execute("SELECT id FROM interactions LIMIT 5")
        rows = cur.fetchall()
"""

import os
import re
from contextlib import contextmanager
from pathlib import Path
from typing import Generator

import psycopg2
import psycopg2.extras
from dotenv import load_dotenv

load_dotenv(Path(__file__).parent / ".env")

_DATABASE_URL = os.environ["DATABASE_URL"]
ORG_ID = os.environ["EOS_ORG_ID"]
USER_ID = os.environ["EOS_USER_ID"]

# ─── ID resolution caches ─────────────────────────────────────────────────────
# Maps Python string slugs → Postgres UUIDs. Loaded once per process.

_venture_cache: dict[str, str] = {}  # "lyfe_institute" → "<uuid>"
_skill_cache: dict[str, str] = {}  # "analyze_icp_signal" → "<uuid>"
_caches_loaded: bool = False


def _load_caches(cur: psycopg2.extensions.cursor) -> None:
    """Populate venture + skill lookup caches. Called once per process."""
    global _caches_loaded
    if _caches_loaded:
        return

    # Ventures: slug = name.lower().replace(" ", "_")
    cur.execute("SELECT id, name FROM ventures")
    for row in cur.fetchall():
        slug = row["name"].lower().replace(" ", "_")
        _venture_cache[slug] = str(row["id"])

    # Skills: name is already slug-like (e.g. "analyze_icp_signal")
    cur.execute("SELECT id, name FROM skills")
    for row in cur.fetchall():
        _skill_cache[row["name"]] = str(row["id"])

    _caches_loaded = True


# ─── Connection context manager ───────────────────────────────────────────────


@contextmanager
def get_conn(org_id: str = ORG_ID) -> Generator:
    """
    Open a Neon connection inside a transaction with RLS enabled for org_id.

    Every transaction begins with SET LOCAL app.current_org_id so the
    PostgreSQL RLS firewall scopes all queries to the correct tenant.

    Usage:
        with get_conn() as cur:
            cur.execute("INSERT INTO interactions (...) VALUES (...) RETURNING id")
            row = cur.fetchone()
    """
    try:
        conn = psycopg2.connect(_DATABASE_URL)
    except Exception as e:
        # Strip credentials from the error before it can appear in logs/tracebacks
        safe_msg = re.sub(r"://[^@]+@", "://***:***@", str(e))
        raise psycopg2.OperationalError(f"Neon connection failed: {safe_msg}") from None
    try:
        with conn:  # transaction — commits on clean exit, rolls back on exception
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                # RLS: tell Postgres which tenant this session belongs to
                cur.execute("SET LOCAL app.current_org_id = %s", (org_id,))
                # Load ID caches while we have an open, RLS-scoped cursor
                _load_caches(cur)
                yield cur
    finally:
        conn.close()


# ─── ID resolution helpers ────────────────────────────────────────────────────


def resolve_venture(slug: str | None) -> str | None:
    """
    Map a Python venture slug to its Neon UUID.

    Slugs are derived from venture names: lowercase, spaces → underscores.
    e.g. "Lyfe Institute" → "lyfe_institute" → "<uuid>"

    Returns None if the slug is unknown or None.
    """
    if not slug:
        return None
    # Normalize — callers may pass either "Lyfe Institute" or "lyfe_institute"
    normalized = slug.lower().replace(" ", "_")
    return _venture_cache.get(normalized)


def resolve_skill(name: str | None) -> str | None:
    """
    Map a Python skill name to its Neon UUID.

    Skill names match the 'name' column in the skills table exactly.
    e.g. "analyze_icp_signal" → "<uuid>"

    Returns None if the name is unknown or None.
    """
    if not name:
        return None
    return _skill_cache.get(name)
