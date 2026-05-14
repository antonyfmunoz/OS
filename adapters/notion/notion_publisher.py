"""
EOS Notion Publisher — canonical pattern for writing EOS content to Notion.

Every brief, report, summary, and diagnosis uses this module.
Never build a custom Notion writer from scratch.

Operationalization: built once, improved from outcomes.

Usage:
    from adapters.notion.notion_publisher import get_publisher

    publisher = get_publisher(ctx)
    url = publisher.publish_morning_brief(
        content=brief_dict,
    )
    # Returns: https://notion.so/...

Discord then gets: f'Brief ready → {url}'
Not the full content. Just the link.
"""

import json
import logging
import os
from datetime import date, datetime
from typing import Optional
from zoneinfo import ZoneInfo

from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))

logger = logging.getLogger(__name__)
PDT = ZoneInfo("America/Los_Angeles")

# Reuse the same venture → env prefix map as notion_sync.py
_VENTURE_PREFIXES = {
    "personal_brand": "NOTION_PERSONAL_BRAND",
    "lyfe_institute": "NOTION_LYFE_INSTITUTE",
    "empyrean_creative": "NOTION_EMPYREAN_CREATIVE",
}


def _get_db_id(venture_id: str, db_type: str) -> str:
    """
    Resolve Notion database ID from env vars.
    Pattern: NOTION_{VENTURE}_{TYPE}_DB
    Falls back to generic NOTION_{TYPE}_DB.
    """
    prefix = _VENTURE_PREFIXES.get(venture_id, "")
    if prefix:
        db_id = os.getenv(f"{prefix}_{db_type.upper()}_DB", "")
        if db_id:
            return db_id
    return os.getenv(f"NOTION_{db_type.upper()}_DB", "")


# ── Notion API helpers ───────────────────────────────────────────────────────


def _api_call(
    method: str,
    endpoint: str,
    payload: Optional[dict] = None,
) -> dict:
    """Make a Notion API call. Returns response dict or {} on failure."""
    import urllib.request

    token = os.getenv("NOTION_API_KEY", "")
    if not token:
        logger.warning("[NotionPublisher] No NOTION_API_KEY set")
        return {}

    url = f"https://api.notion.com/v1{endpoint}"
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
        "Notion-Version": "2022-06-28",
    }

    data = json.dumps(payload).encode() if payload else None
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            return json.loads(resp.read())
    except Exception as e:
        logger.error(f"[NotionPublisher] {method} {endpoint}: {e}")
        return {}


def _page_url(page_id: str) -> str:
    """Convert Notion page ID to URL."""
    if not page_id:
        return ""
    return f"https://notion.so/{page_id.replace('-', '')}"


# ── Block builders ───────────────────────────────────────────────────────────


def _heading(text: str, level: int = 2) -> dict:
    h_type = f"heading_{min(max(level, 1), 3)}"
    return {
        "object": "block",
        "type": h_type,
        h_type: {"rich_text": [{"type": "text", "text": {"content": text[:100]}}]},
    }


def _paragraph(text: str) -> dict:
    return {
        "object": "block",
        "type": "paragraph",
        "paragraph": {
            "rich_text": [{"type": "text", "text": {"content": text[:2000]}}]
        },
    }


def _divider() -> dict:
    return {"object": "block", "type": "divider", "divider": {}}


def _bulleted(text: str) -> dict:
    return {
        "object": "block",
        "type": "bulleted_list_item",
        "bulleted_list_item": {
            "rich_text": [{"type": "text", "text": {"content": text[:2000]}}]
        },
    }


# ── Core create/query ────────────────────────────────────────────────────────


def _create_page(
    parent_db_id: str,
    title: str,
    blocks: list,
    extra_properties: Optional[dict] = None,
) -> str:
    """Create a Notion page in a database. Returns page URL or ''."""
    if not parent_db_id:
        return ""

    properties = {
        "title": {"title": [{"text": {"content": title}}]},
    }
    if extra_properties:
        properties.update(extra_properties)

    payload = {
        "parent": {"database_id": parent_db_id},
        "properties": properties,
        "children": blocks[:100],  # Notion limit: 100 blocks per create
    }

    result = _api_call("POST", "/pages", payload)
    page_id = result.get("id", "")
    if page_id:
        url = _page_url(page_id)
        logger.info(f"[NotionPublisher] Page created: {url}")
        return url

    # If page creation failed, the DB ID may be dead — log for diagnosis
    logger.warning(
        f"[NotionPublisher] Page creation failed for DB {parent_db_id[:12]}..."
    )
    return ""


def _find_page_by_title(db_id: str, title: str) -> str:
    """Find existing page by exact title in a database. Returns URL or ''."""
    payload = {
        "filter": {"property": "title", "title": {"equals": title}},
        "page_size": 1,
    }
    result = _api_call("POST", f"/databases/{db_id}/query", payload)
    results = result.get("results", [])
    if results:
        return _page_url(results[0].get("id", ""))
    return ""


# ── Content builders (text → blocks) ─────────────────────────────────────────


def _brief_blocks(content: dict, title: str) -> list:
    """Build Notion blocks for a morning brief."""
    blocks = [
        _heading(title, level=1),
        _divider(),
    ]

    # Binding constraint
    blocks.append(_heading("Binding Constraint", level=2))
    blocks.append(_paragraph(content.get("binding_constraint", "Not diagnosed yet")))

    # One objective
    if content.get("one_objective"):
        blocks.append(_heading("One Objective Today", level=2))
        blocks.append(_paragraph(content["one_objective"]))

    # Priority action
    if content.get("priority_action"):
        blocks.append(_heading("Priority Action", level=2))
        blocks.append(_paragraph(content["priority_action"]))

    # Company reports
    if content.get("company_reports"):
        blocks.append(_divider())
        blocks.append(_heading("Company Briefs", level=2))
        blocks.append(_paragraph(content["company_reports"]))

    # Portfolio health
    if content.get("portfolio_brief"):
        blocks.append(_heading("Portfolio Health", level=2))
        blocks.append(_paragraph(content["portfolio_brief"]))

    # Calendar
    if content.get("calendar_today"):
        blocks.append(_divider())
        blocks.append(_heading("Today's Calendar", level=2))
        blocks.append(_paragraph(str(content["calendar_today"])))

    # Tasks
    if content.get("tasks_today"):
        blocks.append(_heading("Tasks", level=2))
        blocks.append(_paragraph(str(content["tasks_today"])))

    # Critical signals
    if content.get("critical_signals"):
        blocks.append(_divider())
        blocks.append(_heading("Critical Signals", level=2))
        blocks.append(_paragraph(str(content["critical_signals"])))

    # Pending approvals
    if content.get("pending_approvals"):
        blocks.append(_heading("Pending Approvals", level=2))
        blocks.append(_paragraph(str(content["pending_approvals"])))

    # Patterns
    if content.get("patterns"):
        blocks.append(_heading("Patterns Detected", level=2))
        blocks.append(_paragraph(str(content["patterns"])))

    # Overnight signals (for intel brief)
    if content.get("overnight_signals"):
        blocks.append(_divider())
        blocks.append(_heading("Overnight Signals", level=2))
        blocks.append(_paragraph(str(content["overnight_signals"])))

    return blocks


# ══════════════════════════════════════════════════════════════════════════════
# PUBLIC API — one method per content type
# ══════════════════════════════════════════════════════════════════════════════


class NotionPublisher:
    """
    Write EOS content to Notion. Return page URLs for Discord links.
    Stateless — all config comes from env vars.
    """

    def publish_morning_brief(
        self,
        content: dict,
        brief_date: Optional[date] = None,
    ) -> str:
        """
        Write morning brief to Notion.
        Uses NOTION_MORNING_BRIEF_ID as the parent database.
        Returns page URL or ''.

        content keys:
            binding_constraint, one_objective, priority_action,
            company_reports, portfolio_brief, calendar_today,
            tasks_today, critical_signals, pending_approvals, patterns
        """
        today = brief_date or date.today()
        title = f"Daily Brief — {today}"

        db_id = os.getenv("NOTION_MORNING_BRIEF_ID", "")
        if not db_id:
            db_id = _get_db_id("lyfe_institute", "DOCUMENTS")
        if not db_id:
            logger.warning("[NotionPublisher] No brief DB found")
            return ""

        # Check for existing brief today
        existing = _find_page_by_title(db_id, title)
        if existing:
            logger.info(f"[NotionPublisher] Brief already exists: {existing}")
            return existing

        blocks = _brief_blocks(
            content, f"Morning Brief — {today.strftime('%B %d, %Y')}"
        )
        url = _create_page(db_id, title, blocks)

        # If primary DB failed, try Documents DB as fallback
        if not url and db_id != _get_db_id("lyfe_institute", "DOCUMENTS"):
            fallback_db = _get_db_id("lyfe_institute", "DOCUMENTS")
            if fallback_db:
                logger.info("[NotionPublisher] Primary DB failed, trying Documents DB")
                url = _create_page(fallback_db, title, blocks)
        return url

    def publish_intel_brief(
        self,
        content: dict,
        brief_date: Optional[date] = None,
    ) -> str:
        """
        Write intelligence brief to Notion.
        Uses NOTION_MORNING_BRIEF_ID or Documents DB fallback.
        Returns page URL or ''.
        """
        today = brief_date or date.today()
        title = f"Intel Brief — {today}"

        db_id = os.getenv("NOTION_MORNING_BRIEF_ID", "")
        if not db_id:
            db_id = _get_db_id("lyfe_institute", "DOCUMENTS")
        if not db_id:
            return ""

        existing = _find_page_by_title(db_id, title)
        if existing:
            return existing

        blocks = [
            _heading(f"Intelligence Brief — {today.strftime('%B %d, %Y')}", level=1),
            _divider(),
        ]
        if content.get("signals"):
            blocks.append(_heading("Overnight Signals", level=2))
            blocks.append(_paragraph(content["signals"]))
        if content.get("market"):
            blocks.append(_heading("Market", level=2))
            blocks.append(_paragraph(content["market"]))
        if content.get("opportunities"):
            blocks.append(_heading("Opportunities", level=2))
            blocks.append(_paragraph(content["opportunities"]))
        if content.get("synthesis"):
            blocks.append(_heading("Synthesis", level=2))
            blocks.append(_paragraph(content["synthesis"]))

        return _create_page(db_id, title, blocks)

    def publish_constraint_diagnosis(
        self,
        venture_id: str,
        diagnosis: dict,
    ) -> str:
        """
        Write constraint diagnosis to Notion Documents DB.
        Returns page URL.
        """
        today = date.today()
        title = f"Constraint Diagnosis — {today}"

        db_id = _get_db_id(venture_id, "DOCUMENTS")
        if not db_id:
            logger.warning(f"[NotionPublisher] No DOCUMENTS DB for {venture_id}")
            return ""

        constraint = diagnosis.get("constraint", "Unknown")
        blocks = [
            _heading(f"Constraint: {constraint}", level=1),
            _divider(),
            _heading("Diagnosis", level=2),
            _paragraph(diagnosis.get("diagnosis", "")),
            _heading("Evidence", level=2),
            _paragraph(diagnosis.get("evidence", "")),
            _heading("Recommendation", level=2),
            _paragraph(diagnosis.get("recommendation", diagnosis.get("action", ""))),
        ]

        return _create_page(db_id, title, blocks)

    def publish_portfolio_status(
        self,
        status: dict,
    ) -> str:
        """
        Write portfolio status to Notion.
        Uses personal_brand DOCUMENTS DB.
        Returns page URL.
        """
        today = date.today()
        title = f"Portfolio Status — {today}"

        db_id = _get_db_id("personal_brand", "DOCUMENTS")
        if not db_id:
            db_id = os.getenv("NOTION_PORTFOLIO_OVERVIEW_DB", "")
        if not db_id:
            return ""

        blocks = [
            _heading(f"Portfolio Status — {today.strftime('%B %d, %Y')}", level=1),
            _divider(),
        ]

        ventures = status.get("ventures", [])
        for venture in ventures:
            name = venture.get("name", venture.get("venture_id", "Unknown"))
            blocks.append(_heading(name, level=2))
            summary_parts = []
            if venture.get("health"):
                summary_parts.append(f"Health: {venture['health']}")
            if venture.get("stage"):
                summary_parts.append(f"Stage: {venture['stage']}")
            if venture.get("revenue") is not None:
                summary_parts.append(f"Revenue: ${venture['revenue']:,.0f}")
            if venture.get("summary"):
                summary_parts.append(venture["summary"])
            blocks.append(
                _paragraph("\n".join(summary_parts) if summary_parts else "No data")
            )

        return _create_page(db_id, title, blocks)

    def publish_eod_sync(
        self,
        content: dict,
    ) -> str:
        """Write EOD sync to Notion. Uses morning brief DB. Returns URL."""
        today = date.today()
        title = f"EOD Sync — {today}"

        db_id = os.getenv("NOTION_MORNING_BRIEF_ID", "")
        if not db_id:
            db_id = _get_db_id("lyfe_institute", "DOCUMENTS")
        if not db_id:
            return ""

        existing = _find_page_by_title(db_id, title)
        if existing:
            return existing

        blocks = [
            _heading(f"EOD Sync — {today.strftime('%B %d, %Y')}", level=1),
            _divider(),
            _heading("Completed Today", level=2),
            _paragraph(content.get("completed", "None")),
            _heading("Open Loops", level=2),
            _paragraph(content.get("open_loops", "None")),
            _heading("Wins", level=2),
            _paragraph(content.get("wins", "None")),
            _heading("Misses", level=2),
            _paragraph(content.get("misses", "None")),
            _heading("Tomorrow's One Objective", level=2),
            _paragraph(content.get("tomorrow_objective", "Not set")),
        ]

        return _create_page(db_id, title, blocks)

    def publish_ceo_delegation(
        self,
        content: dict,
    ) -> str:
        """Write CEO delegation report to Notion. Returns URL."""
        today = date.today()
        title = f"CEO Delegation — {today}"

        db_id = os.getenv("NOTION_MORNING_BRIEF_ID", "")
        if not db_id:
            db_id = _get_db_id("lyfe_institute", "DOCUMENTS")
        if not db_id:
            return ""

        existing = _find_page_by_title(db_id, title)
        if existing:
            return existing

        blocks = [
            _heading(f"CEO Agent Delegation — {today.strftime('%B %d, %Y')}", level=1),
            _divider(),
        ]
        for result in content.get("results", []):
            blocks.append(_paragraph(result))

        return _create_page(db_id, title, blocks)


# ── Module-level factory ─────────────────────────────────────────────────────


def get_publisher(ctx=None) -> NotionPublisher:
    """Get a configured NotionPublisher instance."""
    return NotionPublisher()
