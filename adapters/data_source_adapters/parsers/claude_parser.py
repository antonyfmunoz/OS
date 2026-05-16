"""Claude conversation export parser.

Handles Claude's JSON export format:
- Single JSON file containing a list of conversations
- Each conversation: uuid, name, created_at, updated_at, chat_messages
- Each message: sender (human/assistant), text or content blocks, created_at
- Also handles directory of individual conversation JSON files
"""

from __future__ import annotations

import json
import logging
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, "/opt/OS")

from adapters.data_source_adapters.conversation_source import (
    Conversation,
    ConversationTurn,
)

logger = logging.getLogger(__name__)


def _extract_text_content(content: Any) -> str:
    """Extract plain text from Claude message content (string or blocks)."""
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        # Content blocks: [{"type": "text", "text": "..."}, ...]
        parts: list[str] = []
        for block in content:
            if isinstance(block, dict):
                if block.get("type") == "text":
                    parts.append(block.get("text", ""))
                elif "text" in block:
                    parts.append(block["text"])
            elif isinstance(block, str):
                parts.append(block)
        return "\n".join(parts)
    return str(content) if content else ""


def _normalize_role(sender: str) -> str:
    """Map Claude's role names to canonical roles."""
    sender_lower = sender.lower()
    if sender_lower in ("human", "user"):
        return "user"
    if sender_lower in ("assistant", "ai"):
        return "assistant"
    return sender_lower


def _parse_single_conversation(data: dict[str, Any]) -> Conversation | None:
    """Parse a single conversation object from Claude export."""
    conversation_id = data.get("uuid", data.get("id", ""))
    if not conversation_id:
        logger.warning("Skipping conversation without ID")
        return None

    title = data.get("name", data.get("title", "Untitled"))
    created_at = data.get("created_at", "")
    updated_at = data.get("updated_at", created_at)

    # Messages can be under various keys
    messages = data.get("chat_messages", data.get("messages", []))
    if not messages:
        logger.debug("Conversation %s has no messages, skipping", conversation_id)
        return None

    turns: list[ConversationTurn] = []
    for msg in messages:
        if not isinstance(msg, dict):
            continue

        sender = msg.get("sender", msg.get("role", ""))
        if not sender:
            continue

        role = _normalize_role(sender)
        content = _extract_text_content(msg.get("text", msg.get("content", "")))
        if not content.strip():
            continue

        timestamp = msg.get("created_at", msg.get("timestamp", None))
        model = msg.get("model", None)

        turns.append(
            ConversationTurn(
                role=role,
                content=content,
                timestamp=timestamp,
                model=model,
            )
        )

    if not turns:
        return None

    return Conversation(
        conversation_id=conversation_id,
        title=title,
        platform="claude",
        turns=turns,
        created_at=created_at,
        updated_at=updated_at,
        metadata={"source_format": "claude_export"},
    )


def parse_claude_export(export_path: Path) -> list[Conversation]:
    """Parse a Claude conversation export into Conversation objects.

    Args:
        export_path: Path to either a single JSON file or a directory
                     containing individual conversation JSON files.

    Returns:
        List of parsed Conversation objects.
    """
    export_path = Path(export_path)
    conversations: list[Conversation] = []

    if export_path.is_file():
        conversations = _parse_file(export_path)
    elif export_path.is_dir():
        json_files = sorted(export_path.glob("*.json"))
        if not json_files:
            logger.warning("No JSON files found in %s", export_path)
            return []
        for json_file in json_files:
            conversations.extend(_parse_file(json_file))
    else:
        logger.error("Export path does not exist: %s", export_path)
        return []

    logger.info("Parsed %d conversations from Claude export at %s", len(conversations), export_path)
    return conversations


def _parse_file(file_path: Path) -> list[Conversation]:
    """Parse a single JSON file that may contain one or many conversations."""
    try:
        raw = json.loads(file_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as e:
        logger.error("Failed to read %s: %s", file_path, e)
        return []

    results: list[Conversation] = []

    if isinstance(raw, list):
        # List of conversations
        for item in raw:
            if isinstance(item, dict):
                conv = _parse_single_conversation(item)
                if conv:
                    results.append(conv)
    elif isinstance(raw, dict):
        # Could be a single conversation or an object wrapping a list
        if "conversations" in raw:
            for item in raw["conversations"]:
                if isinstance(item, dict):
                    conv = _parse_single_conversation(item)
                    if conv:
                        results.append(conv)
        else:
            conv = _parse_single_conversation(raw)
            if conv:
                results.append(conv)

    return results
