"""ChatGPT conversation export parser.

Handles ChatGPT's export format:
- ZIP archive containing conversations.json (and other files)
- conversations.json: list of conversation objects
- Each conversation: id, title, create_time, update_time, mapping
- mapping is a dict of node_id -> {id, message, parent, children}
- message: {author: {role}, content: {content_type, parts: [text]}, create_time}
- Tree structure: walk from root following children to build ordered turn list
"""

from __future__ import annotations

import json
import logging
import os
import sys
import zipfile
from pathlib import Path
from typing import Any

sys.path.insert(0, os.environ.get("UMH_ROOT", "/opt/OS"))

from adapters.data_source_adapters.conversation_source import (
    Conversation,
    ConversationTurn,
)

logger = logging.getLogger(__name__)


def _unix_to_iso(ts: float | int | None) -> str:
    """Convert unix timestamp to ISO 8601 string."""
    if ts is None:
        return ""
    from datetime import datetime, timezone

    try:
        return datetime.fromtimestamp(float(ts), tz=timezone.utc).isoformat()
    except (ValueError, OSError, OverflowError):
        return ""


def _extract_message_text(message: dict[str, Any] | None) -> str:
    """Extract text content from a ChatGPT message node."""
    if not message:
        return ""

    content = message.get("content", {})
    if not isinstance(content, dict):
        return ""

    parts = content.get("parts", [])
    if not parts:
        return ""

    text_parts: list[str] = []
    for part in parts:
        if isinstance(part, str):
            text_parts.append(part)
        elif isinstance(part, dict) and "text" in part:
            text_parts.append(part["text"])

    return "\n".join(text_parts)


def _get_message_role(message: dict[str, Any] | None) -> str | None:
    """Get the role from a ChatGPT message, returning None for system/tool."""
    if not message:
        return None

    author = message.get("author", {})
    if not isinstance(author, dict):
        return None

    role = author.get("role", "")
    if role == "user":
        return "user"
    if role == "assistant":
        return "assistant"
    # Skip system, tool, and unknown roles
    return None


def _walk_conversation_tree(mapping: dict[str, Any]) -> list[ConversationTurn]:
    """Walk the ChatGPT conversation tree to produce ordered turns.

    Strategy: find root node (no parent or parent not in mapping),
    then follow first child chain to build linear order.
    """
    if not mapping:
        return []

    # Find root node(s) — nodes whose parent is None or not in mapping
    roots: list[str] = []
    for node_id, node in mapping.items():
        parent = node.get("parent")
        if parent is None or parent not in mapping:
            roots.append(node_id)

    if not roots:
        return []

    # BFS from root following children to build ordered list
    turns: list[ConversationTurn] = []
    visited: set[str] = set()
    queue: list[str] = list(roots)

    while queue:
        node_id = queue.pop(0)
        if node_id in visited:
            continue
        visited.add(node_id)

        node = mapping.get(node_id, {})
        message = node.get("message")

        if message:
            role = _get_message_role(message)
            text = _extract_message_text(message)

            if role and text.strip():
                timestamp = message.get("create_time")
                ts_str = _unix_to_iso(timestamp) if timestamp else None
                model_slug = message.get("metadata", {}).get("model_slug")

                turns.append(
                    ConversationTurn(
                        role=role,
                        content=text,
                        timestamp=ts_str,
                        model=model_slug,
                    )
                )

        # Add children to queue (in order)
        children = node.get("children", [])
        queue.extend(children)

    return turns


def _parse_single_conversation(data: dict[str, Any]) -> Conversation | None:
    """Parse a single ChatGPT conversation object."""
    conversation_id = data.get("id", "")
    if not conversation_id:
        logger.warning("Skipping ChatGPT conversation without ID")
        return None

    title = data.get("title", "Untitled")
    created_at = _unix_to_iso(data.get("create_time"))
    updated_at = _unix_to_iso(data.get("update_time"))

    mapping = data.get("mapping", {})
    if not mapping:
        logger.debug("Conversation %s has empty mapping, skipping", conversation_id)
        return None

    turns = _walk_conversation_tree(mapping)
    if not turns:
        return None

    return Conversation(
        conversation_id=conversation_id,
        title=title,
        platform="chatgpt",
        turns=turns,
        created_at=created_at,
        updated_at=updated_at,
        metadata={"source_format": "chatgpt_export"},
    )


def parse_chatgpt_export(export_path: Path) -> list[Conversation]:
    """Parse a ChatGPT conversation export into Conversation objects.

    Args:
        export_path: Path to either a ZIP archive (ChatGPT's export format),
                     a conversations.json file, or a directory containing one.

    Returns:
        List of parsed Conversation objects.
    """
    export_path = Path(export_path)
    conversations: list[Conversation] = []

    if export_path.is_file() and export_path.suffix == ".zip":
        conversations = _parse_zip(export_path)
    elif export_path.is_file() and export_path.suffix == ".json":
        conversations = _parse_json_file(export_path)
    elif export_path.is_dir():
        # Look for conversations.json in directory
        conv_file = export_path / "conversations.json"
        if conv_file.exists():
            conversations = _parse_json_file(conv_file)
        else:
            # Try all JSON files
            json_files = sorted(export_path.glob("*.json"))
            for json_file in json_files:
                conversations.extend(_parse_json_file(json_file))
    else:
        logger.error("Export path does not exist: %s", export_path)
        return []

    logger.info(
        "Parsed %d conversations from ChatGPT export at %s",
        len(conversations),
        export_path,
    )
    return conversations


def _parse_zip(zip_path: Path) -> list[Conversation]:
    """Extract and parse conversations.json from a ChatGPT export ZIP."""
    try:
        with zipfile.ZipFile(zip_path, "r") as zf:
            if "conversations.json" not in zf.namelist():
                logger.error("No conversations.json found in %s", zip_path)
                return []
            raw = json.loads(zf.read("conversations.json"))
    except (zipfile.BadZipFile, json.JSONDecodeError, OSError) as e:
        logger.error("Failed to read ZIP %s: %s", zip_path, e)
        return []

    return _parse_raw_conversations(raw)


def _parse_json_file(file_path: Path) -> list[Conversation]:
    """Parse a conversations.json file."""
    try:
        raw = json.loads(file_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as e:
        logger.error("Failed to read %s: %s", file_path, e)
        return []

    return _parse_raw_conversations(raw)


def _parse_raw_conversations(raw: Any) -> list[Conversation]:
    """Parse raw JSON data into Conversation list."""
    results: list[Conversation] = []

    if isinstance(raw, list):
        for item in raw:
            if isinstance(item, dict):
                conv = _parse_single_conversation(item)
                if conv:
                    results.append(conv)
    elif isinstance(raw, dict) and "conversations" in raw:
        for item in raw["conversations"]:
            if isinstance(item, dict):
                conv = _parse_single_conversation(item)
                if conv:
                    results.append(conv)

    return results
