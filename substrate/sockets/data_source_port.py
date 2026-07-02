"""Data source port — substrate-layer abstraction for external data adapters.

The adapter layer (adapters/notion/, adapters/google_workspace/, etc.)
registers its concrete implementations at startup. Substrate code calls
the thin wrappers here, never importing from adapters/.

Covers: Notion (client, publisher), Google Workspace (connector, email,
scanner), NotebookLM, and Calendar.
"""

from __future__ import annotations

from typing import Any, Callable, Optional

# ── Notion ──────────────────────────────────────────────────────────

_notion_client_fn: Optional[Callable] = None
_notion_publisher_fn: Optional[Callable] = None


def register_notion(
    *,
    get_client: Optional[Callable] = None,
    get_publisher: Optional[Callable] = None,
) -> None:
    """Register Notion adapter functions."""
    global _notion_client_fn, _notion_publisher_fn
    if get_client is not None:
        _notion_client_fn = get_client
    if get_publisher is not None:
        _notion_publisher_fn = get_publisher


def get_notion_client() -> Any:
    """Return a Notion client, or None if not registered."""
    if _notion_client_fn is not None:
        return _notion_client_fn()
    return None


def get_notion_publisher() -> Any:
    """Return a Notion publisher, or None if not registered."""
    if _notion_publisher_fn is not None:
        return _notion_publisher_fn()
    return None


# ── Google Workspace ────────────────────────────────────────────────

_gws_connector_cls: Optional[type] = None
_email_gps_cls: Optional[type] = None
_gws_scanner_cls: Optional[type] = None


def register_google_workspace(
    *,
    connector_cls: Optional[type] = None,
    email_gps_cls: Optional[type] = None,
    scanner_cls: Optional[type] = None,
) -> None:
    """Register Google Workspace adapter classes."""
    global _gws_connector_cls, _email_gps_cls, _gws_scanner_cls
    if connector_cls is not None:
        _gws_connector_cls = connector_cls
    if email_gps_cls is not None:
        _email_gps_cls = email_gps_cls
    if scanner_cls is not None:
        _gws_scanner_cls = scanner_cls


def get_gws_connector_class() -> Optional[type]:
    """Return GWSConnector class, or None if not registered."""
    return _gws_connector_cls


def get_email_gps_class() -> Optional[type]:
    """Return EmailGPS class, or None if not registered."""
    return _email_gps_cls


def get_gws_scanner_class() -> Optional[type]:
    """Return GWSDocumentScanner class, or None if not registered."""
    return _gws_scanner_cls


# ── NotebookLM ──────────────────────────────────────────────────────

_notebooklm_sync_cls: Optional[type] = None


def register_notebooklm(*, sync_cls: type) -> None:
    """Register NotebookLM sync adapter."""
    global _notebooklm_sync_cls
    _notebooklm_sync_cls = sync_cls


def get_notebooklm_sync_class() -> Optional[type]:
    """Return NotebookLMSync class, or None if not registered."""
    return _notebooklm_sync_cls


# ── Calendar ────────────────────────────────────────────────────────

_calendar_meetings_fn: Optional[Callable] = None
_draft_minutes_fn: Optional[Callable] = None


def register_calendar(
    *,
    get_open_loop_meetings: Optional[Callable] = None,
    draft_meeting_minutes: Optional[Callable] = None,
) -> None:
    """Register calendar adapter functions."""
    global _calendar_meetings_fn, _draft_minutes_fn
    if get_open_loop_meetings is not None:
        _calendar_meetings_fn = get_open_loop_meetings
    if draft_meeting_minutes is not None:
        _draft_minutes_fn = draft_meeting_minutes


def get_open_loop_meetings(**kwargs: Any) -> Any:
    """Return open loop meetings, or empty list if not registered."""
    if _calendar_meetings_fn is not None:
        return _calendar_meetings_fn(**kwargs)
    return []


def draft_meeting_minutes(**kwargs: Any) -> Any:
    """Draft meeting minutes, or None if not registered."""
    if _draft_minutes_fn is not None:
        return _draft_minutes_fn(**kwargs)
    return None
