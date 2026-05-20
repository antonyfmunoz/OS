"""Notion API ↔ UMH payload translations."""

from __future__ import annotations

from typing import Any


def build_create_page_payload(
    database_id: str,
    title: str,
    properties: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Transform UMH create_page params into Notion API payload."""
    payload: dict[str, Any] = {
        "parent": {"database_id": database_id},
        "properties": {
            "Name": {
                "title": [{"text": {"content": title}}],
            },
        },
    }
    if properties:
        for prop_name, prop_value in properties.items():
            if prop_name == "Name":
                continue
            payload["properties"][prop_name] = prop_value
    return payload


def extract_create_page_result(response: dict[str, Any]) -> dict[str, Any]:
    """Transform Notion create_page response into UMH result shape."""
    return {
        "page_id": response.get("id", ""),
        "url": response.get("url", ""),
    }


def build_update_page_payload(
    page_id: str,
    properties: dict[str, Any],
) -> dict[str, Any]:
    """Transform UMH update_page params into Notion API kwargs for pages.update()."""
    return {
        "page_id": page_id,
        "properties": properties,
    }


def extract_update_page_result(response: dict[str, Any]) -> dict[str, Any]:
    return {
        "page_id": response.get("id", ""),
        "updated": True,
    }


def build_append_block_payload(
    page_id: str,
    children: list[dict[str, Any]],
) -> dict[str, Any]:
    """Transform UMH append_block params into Notion API kwargs for blocks.children.append()."""
    return {
        "block_id": page_id,
        "children": children,
    }


def extract_append_block_result(response: dict[str, Any]) -> dict[str, Any]:
    results = response.get("results", [])
    return {
        "block_ids": [r.get("id", "") for r in results],
        "count": len(results),
    }


def build_query_database_payload(
    database_id: str,
    filter_obj: dict[str, Any] | None = None,
    sorts: list[dict[str, Any]] | None = None,
    page_size: int = 100,
) -> dict[str, Any]:
    """Transform UMH query_database params into Notion API body for POST /databases/{id}/query."""
    payload: dict[str, Any] = {
        "database_id": database_id,
        "page_size": min(page_size, 100),
    }
    if filter_obj:
        payload["filter"] = filter_obj
    if sorts:
        payload["sorts"] = sorts
    return payload


def extract_query_database_result(response: dict[str, Any]) -> dict[str, Any]:
    results = response.get("results", [])
    return {
        "results": [
            {
                "page_id": r.get("id", ""),
                "url": r.get("url", ""),
                "properties": r.get("properties", {}),
            }
            for r in results
        ],
        "count": len(results),
        "has_more": response.get("has_more", False),
    }
