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
