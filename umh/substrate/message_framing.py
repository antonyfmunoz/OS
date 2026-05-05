"""
Message Framing Protocol — canonical envelope for Discord transport.

Provides:
  - OutboundFrame: stable reply_id envelope wrapping chunked outbound messages.
  - InboundBuffer: per-user+channel multi-message accumulator with /done finalization.
  - ReplyTracker: lightweight in-memory store for outbound reply lifecycle.

Design invariants:
  - Transport-layer only — no LLM calls, no DB, no gateway imports.
  - Backward compatible — existing single-message flows work unchanged.
  - reply_id is stable for the lifetime of one logical reply.
  - Inbound buffer keys on (user_id, channel_id) to prevent cross-user corruption.
  - /done is the ONLY inbound finalization signal (no implicit timeouts that silently submit).

v1 — 2026-04-15
"""

from __future__ import annotations

import hashlib
import threading
import time
import uuid
from dataclasses import asdict, dataclass, field
from typing import Any, Optional


# ─── Outbound Framing ──────────────────────────────────────────────────────


def _short_id() -> str:
    """4-char hex identifier for human-readable references."""
    return uuid.uuid4().hex[:4]


def _reply_id() -> str:
    """Full reply ID (used internally)."""
    return uuid.uuid4().hex[:12]


def _content_hash(text: str) -> str:
    """Short SHA-256 digest for dedup."""
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]


@dataclass
class OutboundFrame:
    """Envelope for one logical outbound reply.

    A single reply may be split into multiple Discord chunks.
    Each chunk carries framing metadata; the final chunk carries
    the completion marker.
    """

    reply_id: str = field(default_factory=_reply_id)
    correlation_id: str = ""
    role: str = ""
    chunk_count: int = 0
    chunks_sent: int = 0
    completed: bool = False
    created_at: float = field(default_factory=time.time)

    @property
    def ref_short(self) -> str:
        """Short reference for display in Discord headers/footers."""
        return self.reply_id[:4]

    def chunk_header(self, chunk_index: int, chunk_count: int) -> str:
        """Render a human-readable framing header for one chunk.

        Format: Role · 2/4 · ref 8f3a
        Single-chunk replies still get a header (1/1).
        """
        display_role = self.role or "System"
        return (
            f"{display_role} · {chunk_index + 1}/{chunk_count} · ref {self.ref_short}"
        )

    def completion_footer(
        self,
        delivered: int | None = None,
        total: int | None = None,
        mode: str = "",
    ) -> str:
        """Render the final-chunk completion footer with integrity info.

        Variants:
          ✓ Complete (4/4 delivered) · ref 8f3a
          ⚠ Partial (3/4 delivered) · ref 8f3a
          ✓ Complete (summary + attachment) · ref 8f3a
        """
        ref = f"ref {self.ref_short}"
        if mode == "attachment_fallback":
            return f"✓ Complete (summary + attachment) · {ref}"
        if delivered is not None and total is not None:
            if delivered >= total:
                return f"✓ Complete ({delivered}/{total} delivered) · {ref}"
            return f"⚠ Partial ({delivered}/{total} delivered) · {ref}"
        return f"✓ Complete · {ref}"

    def serialize(self) -> dict[str, Any]:
        """JSON-safe dict for logging/storage."""
        return asdict(self)


def apply_outbound_framing(
    chunks: list[str],
    frame: OutboundFrame,
    *,
    embed_footer: bool = False,
) -> list[str]:
    """Apply framing headers to pre-split chunks.

    Mutates nothing — returns a NEW list of framed chunk strings.
    The original Part N/M labels from chunk_message() are replaced.

    Rules:
      - Every chunk gets a header line.
      - Completion footer is sent as a separate message by the bridge
        (with integrity info: delivered/total count) unless embed_footer
        is True for backward-compatible single-shot paths.
    """
    import re

    total = len(chunks)
    frame.chunk_count = total
    framed: list[str] = []

    for i, chunk_text in enumerate(chunks):
        # Strip existing Part N/M labels if present
        chunk_text = re.sub(r"^\*Part \d+/\d+\*\n\n", "", chunk_text)

        header = frame.chunk_header(i, total)
        parts = [header, "", chunk_text]

        if embed_footer and i == total - 1:
            parts.extend(["", frame.completion_footer()])

        framed.append("\n".join(parts))

    return framed


# ─── Outbound Reply Tracker ────────────────────────────────────────────────


class ReplyTracker:
    """In-memory tracker for outbound reply lifecycle.

    Thread-safe. Answers:
      - What is the logical reply ID?
      - How many chunks were produced?
      - Which chunks were sent?
      - Was the logical reply completed?
    """

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._replies: dict[str, dict[str, Any]] = {}

    def register(self, frame: OutboundFrame, delivery_mode: str = "chunked") -> None:
        """Register a new outbound reply."""
        with self._lock:
            self._replies[frame.reply_id] = {
                "reply_id": frame.reply_id,
                "correlation_id": frame.correlation_id,
                "role": frame.role,
                "chunk_count": frame.chunk_count,
                "chunks_sent": set(),
                "chunks_failed": set(),
                "completed": False,
                "delivery_mode": delivery_mode,
                "created_at": frame.created_at,
                "completed_at": None,
            }

    def mark_chunk_sent(self, reply_id: str, chunk_index: int) -> None:
        """Record that a specific chunk was successfully sent."""
        with self._lock:
            rec = self._replies.get(reply_id)
            if rec is not None:
                rec["chunks_sent"].add(chunk_index)

    def mark_chunk_failed(self, reply_id: str, chunk_index: int) -> None:
        """Record that a specific chunk failed delivery."""
        with self._lock:
            rec = self._replies.get(reply_id)
            if rec is not None:
                rec["chunks_failed"].add(chunk_index)
                # Remove from sent if it was prematurely recorded
                rec["chunks_sent"].discard(chunk_index)

    def mark_completed(self, reply_id: str) -> None:
        """Mark a reply as fully delivered.

        Only call this when ALL chunks are confirmed sent.
        """
        with self._lock:
            rec = self._replies.get(reply_id)
            if rec is not None:
                rec["completed"] = True
                rec["completed_at"] = time.time()

    def mark_partial(self, reply_id: str) -> None:
        """Mark a reply as partially delivered (some chunks failed)."""
        with self._lock:
            rec = self._replies.get(reply_id)
            if rec is not None:
                rec["completed"] = False
                rec["completed_at"] = time.time()

    def is_complete(self, reply_id: str) -> bool:
        """Check if a reply was fully delivered."""
        with self._lock:
            rec = self._replies.get(reply_id)
            if rec is None:
                return False
            return rec["completed"]

    def get_status(self, reply_id: str) -> Optional[dict[str, Any]]:
        """Get full status for a reply. Returns None if unknown."""
        with self._lock:
            rec = self._replies.get(reply_id)
            if rec is None:
                return None
            return {
                **rec,
                "chunks_sent": sorted(rec["chunks_sent"]),
                "chunks_failed": sorted(rec.get("chunks_failed", set())),
                "delivery_mode": rec.get("delivery_mode", "chunked"),
            }

    def get_all(self) -> list[dict[str, Any]]:
        """Get status for all tracked replies."""
        with self._lock:
            return [
                {
                    **rec,
                    "chunks_sent": sorted(rec["chunks_sent"]),
                    "chunks_failed": sorted(rec.get("chunks_failed", set())),
                    "delivery_mode": rec.get("delivery_mode", "chunked"),
                }
                for rec in self._replies.values()
            ]

    def prune(self, max_age_seconds: float = 3600.0) -> int:
        """Remove completed replies older than max_age_seconds. Returns count removed."""
        cutoff = time.time() - max_age_seconds
        removed = 0
        with self._lock:
            to_remove = [
                rid
                for rid, rec in self._replies.items()
                if rec["completed"] and rec["created_at"] < cutoff
            ]
            for rid in to_remove:
                del self._replies[rid]
                removed += 1
        return removed


# Module-level singleton
_reply_tracker = ReplyTracker()


def get_reply_tracker() -> ReplyTracker:
    """Get the module-level reply tracker."""
    return _reply_tracker


# ─── Inbound Buffering ─────────────────────────────────────────────────────


def _buffer_key(user_id: str, channel_id: str) -> str:
    """Canonical buffer key scoped to user + channel."""
    return f"{user_id}:{channel_id}"


def _inbound_group_id() -> str:
    """Unique ID for one logical inbound message group."""
    return uuid.uuid4().hex[:12]


@dataclass
class InboundMessageGroup:
    """One logical inbound message composed from multiple Discord messages."""

    group_id: str = field(default_factory=_inbound_group_id)
    user_id: str = ""
    channel_id: str = ""
    messages: list[str] = field(default_factory=list)
    created_at: float = field(default_factory=time.time)
    finalized_at: Optional[float] = None

    @property
    def message_count(self) -> int:
        return len(self.messages)

    @property
    def combined_text(self) -> str:
        """Join buffered messages preserving order."""
        return "\n\n".join(self.messages)

    @property
    def combined_text_length(self) -> int:
        return len(self.combined_text)

    def finalize(self) -> str:
        """Mark as finalized and return combined text."""
        self.finalized_at = time.time()
        return self.combined_text

    def serialize(self) -> dict[str, Any]:
        """JSON-safe dict for tracing."""
        return {
            "group_id": self.group_id,
            "user_id": self.user_id,
            "channel_id": self.channel_id,
            "message_count": self.message_count,
            "combined_text_length": self.combined_text_length,
            "created_at": self.created_at,
            "finalized_at": self.finalized_at,
        }


class InboundBuffer:
    """Per-user+channel multi-message buffer with /done finalization.

    Usage:
      1. Call add() for each incoming Discord message.
      2. Call finalize() when the user sends /done.
      3. Call has_active() to check if buffering is in progress.
      4. Call abandon() to clear without submitting (timeout/cleanup).

    Thread-safe via lock.
    """

    # Maximum buffer age before cleanup is allowed (seconds)
    MAX_BUFFER_AGE = 300.0  # 5 minutes

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._buffers: dict[str, InboundMessageGroup] = {}
        self._finalized: list[InboundMessageGroup] = []

    def add(self, user_id: str, channel_id: str, text: str) -> InboundMessageGroup:
        """Add a message to the user's active buffer. Creates buffer if none exists."""
        key = _buffer_key(user_id, channel_id)
        with self._lock:
            if key not in self._buffers:
                self._buffers[key] = InboundMessageGroup(
                    user_id=user_id,
                    channel_id=channel_id,
                )
            self._buffers[key].messages.append(text)
            return self._buffers[key]

    def has_active(self, user_id: str, channel_id: str) -> bool:
        """Check if user has an active (unfinalized) buffer."""
        key = _buffer_key(user_id, channel_id)
        with self._lock:
            return key in self._buffers

    def get_count(self, user_id: str, channel_id: str) -> int:
        """Get current message count in active buffer. 0 if no buffer."""
        key = _buffer_key(user_id, channel_id)
        with self._lock:
            buf = self._buffers.get(key)
            return buf.message_count if buf else 0

    def finalize(self, user_id: str, channel_id: str) -> Optional[InboundMessageGroup]:
        """Finalize the active buffer and return it.

        Returns None if no active buffer exists.
        The buffer is removed from active state and moved to finalized history.
        """
        key = _buffer_key(user_id, channel_id)
        with self._lock:
            buf = self._buffers.pop(key, None)
            if buf is None:
                return None
            buf.finalize()
            self._finalized.append(buf)
            return buf

    def abandon(self, user_id: str, channel_id: str) -> Optional[InboundMessageGroup]:
        """Abandon (discard) the active buffer without submitting.

        Returns the abandoned group for logging, or None if no buffer.
        """
        key = _buffer_key(user_id, channel_id)
        with self._lock:
            return self._buffers.pop(key, None)

    def cleanup_stale(self) -> int:
        """Remove buffers older than MAX_BUFFER_AGE. Returns count removed."""
        cutoff = time.time() - self.MAX_BUFFER_AGE
        removed = 0
        with self._lock:
            stale_keys = [
                k for k, buf in self._buffers.items() if buf.created_at < cutoff
            ]
            for k in stale_keys:
                del self._buffers[k]
                removed += 1
        return removed

    def get_finalized_history(self, limit: int = 50) -> list[dict[str, Any]]:
        """Get recent finalized groups for tracing."""
        with self._lock:
            return [g.serialize() for g in self._finalized[-limit:]]


# Module-level singleton
_inbound_buffer = InboundBuffer()


def get_inbound_buffer() -> InboundBuffer:
    """Get the module-level inbound buffer."""
    return _inbound_buffer
