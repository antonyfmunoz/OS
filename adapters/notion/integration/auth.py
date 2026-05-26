"""Notion auth — credential loading from environment."""

from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv
from notion_client import Client

_ENV_CANDIDATES = [
    Path("/opt/OS/services/.env"),
    Path(__file__).resolve().parents[3] / ".env",
]


def _ensure_env_loaded() -> None:
    if os.getenv("NOTION_API_KEY"):
        return
    for path in _ENV_CANDIDATES:
        if path.exists():
            load_dotenv(path)
            return


def get_notion_client() -> Client:
    """Build an authenticated Notion client from NOTION_API_KEY in environment."""
    _ensure_env_loaded()
    key = os.getenv("NOTION_API_KEY")
    if not key:
        raise RuntimeError("NOTION_API_KEY not set in environment")
    # Pin to 2022-06-28: SDK v3 defaults to 2025-09-03 which dropped databases/{id}/query
    return Client(auth=key, notion_version="2022-06-28")


def discover_database_ids() -> dict[str, str]:
    """Scan os.environ for NOTION_*_DB and NOTION_*_ID vars, return logical-name → UUID mapping.

    Convention: NOTION_{COMPANY}_{TYPE}_DB → strip prefix/suffix, lowercase, underscore join.
    Examples:
        NOTION_LYFE_INSTITUTE_TASKS_DB → lyfe_institute_tasks
        NOTION_EMPYREAN_CREATIVE_PIPELINE_CRM_DB → empyrean_creative_pipeline_crm
        NOTION_PORTFOLIO_ID → portfolio
    """
    _ensure_env_loaded()
    result: dict[str, str] = {}
    for key, value in os.environ.items():
        if not key.startswith("NOTION_") or not value:
            continue
        if key in ("NOTION_API_KEY", "NOTION_TOKEN"):
            continue

        suffix = ""
        if key.endswith("_DB"):
            suffix = "_DB"
        elif key.endswith("_ID"):
            suffix = "_ID"
        else:
            continue

        logical = key[len("NOTION_") : -len(suffix)].lower()
        result[logical] = value

    return result
