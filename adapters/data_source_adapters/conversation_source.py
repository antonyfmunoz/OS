"""ConversationSource — wraps parsed conversation data as an ingestion Source."""

from __future__ import annotations

import hashlib
import json
import os
import sys
from dataclasses import dataclass, field
from typing import Any

sys.path.insert(0, os.environ.get("UMH_ROOT", "/opt/OS"))

from substrate.governance.policy.authority_tier import T9_OLD_CHATS, validate_tier
from substrate.understanding.perception.source import RawContent, Source


@dataclass
class ConversationTurn:
    """A single turn in a conversation."""

    role: str  # "user" | "assistant"
    content: str
    timestamp: str | None = None
    model: str | None = None


@dataclass
class Conversation:
    """Parsed conversation from any platform."""

    conversation_id: str
    title: str
    platform: str  # "claude" | "chatgpt"
    turns: list[ConversationTurn]
    created_at: str
    updated_at: str
    metadata: dict[str, Any] = field(default_factory=dict)


class ConversationSource:
    """Wraps a Conversation as an ingestion Source (authority tier 9 — old chats)."""

    source_type: str = "conversation_export"

    def __init__(self, conversation: Conversation, *, authority_tier: int = T9_OLD_CHATS) -> None:
        self._conversation = conversation
        self.authority_tier: int = validate_tier(authority_tier)
        self._cached_content: RawContent | None = None

    @property
    def source_id(self) -> str:
        return f"conversation:{self._conversation.platform}:{self._conversation.conversation_id}"

    def exists(self) -> bool:
        """Data already parsed in memory — always exists."""
        return True

    def read(self) -> RawContent:
        """Serialize conversation to JSON and return as RawContent."""
        if self._cached_content is not None:
            return self._cached_content

        payload = {
            "conversation_id": self._conversation.conversation_id,
            "title": self._conversation.title,
            "platform": self._conversation.platform,
            "created_at": self._conversation.created_at,
            "updated_at": self._conversation.updated_at,
            "metadata": self._conversation.metadata,
            "turns": [
                {
                    "role": t.role,
                    "content": t.content,
                    "timestamp": t.timestamp,
                    "model": t.model,
                }
                for t in self._conversation.turns
            ],
        }
        serialized = json.dumps(payload, ensure_ascii=False, indent=2)
        encoded = serialized.encode("utf-8")
        sha = hashlib.sha256(encoded).hexdigest()

        self._cached_content = RawContent(
            content=serialized,
            content_type="application/x-conversation+json",
            size_bytes=len(encoded),
            sha256=sha,
        )
        return self._cached_content

    def metadata(self) -> dict[str, Any]:
        """Return conversation metadata for pipeline stages."""
        return {
            "platform": self._conversation.platform,
            "conversation_id": self._conversation.conversation_id,
            "title": self._conversation.title,
            "turn_count": len(self._conversation.turns),
            "created_at": self._conversation.created_at,
            "updated_at": self._conversation.updated_at,
        }


# Protocol conformance check
assert isinstance(ConversationSource, type)
_check: type[Source] = ConversationSource  # type: ignore[assignment]
