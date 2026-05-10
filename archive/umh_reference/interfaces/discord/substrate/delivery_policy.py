"""Deterministic policy module for Discord delivery decisions.

Pure policy — no side effects, no hot-path imports.
All thresholds match the values already used in session_discord_bridge
and discord_utils so there is a single source of truth.
"""

import math
import time
from dataclasses import dataclass, field
from enum import Enum


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

DISCORD_CHAR_LIMIT: int = 2000
MAX_SAFE_CHARS: int = 1800
MAX_CHUNKS_BEFORE_FALLBACK: int = 6
MAX_TOTAL_CHARS_BEFORE_FALLBACK: int = 9000
RETRY_ATTEMPTS: int = 3
INTER_CHUNK_DELAY: float = 0.3
RETRY_DELAY: float = 1.0


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------


class DeliveryMode(Enum):
    """How a message should be delivered to Discord."""

    SINGLE = "single"
    CHUNKED = "chunked"
    ATTACHMENT_FALLBACK = "attachment_fallback"


class DeliveryState(Enum):
    """Lifecycle state of a delivery attempt."""

    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    PARTIAL = "partial"
    COMPLETE = "complete"
    FAILED = "failed"


# ---------------------------------------------------------------------------
# Helper functions
# ---------------------------------------------------------------------------


def estimate_chunks(total_chars: int) -> int:
    """Return the estimated number of chunks for *total_chars*.

    Simple ceiling division by MAX_SAFE_CHARS.
    """
    if total_chars <= 0:
        return 0
    return math.ceil(total_chars / MAX_SAFE_CHARS)


def should_fallback_to_attachment(total_chars: int, estimated_chunks: int) -> bool:
    """Return True when the message is too large for chunked delivery.

    Triggers when *total_chars* exceeds MAX_TOTAL_CHARS_BEFORE_FALLBACK
    **or** *estimated_chunks* exceeds MAX_CHUNKS_BEFORE_FALLBACK.
    """
    return (
        total_chars > MAX_TOTAL_CHARS_BEFORE_FALLBACK
        or estimated_chunks > MAX_CHUNKS_BEFORE_FALLBACK
    )


def determine_delivery_mode(total_chars: int) -> DeliveryMode:
    """Choose the delivery strategy for a message of *total_chars* length.

    Returns SINGLE when the message fits in one safe-sized Discord message,
    ATTACHMENT_FALLBACK when the message is too large for reasonable chunking,
    and CHUNKED for everything in between.
    """
    if total_chars <= MAX_SAFE_CHARS:
        return DeliveryMode.SINGLE

    chunks = estimate_chunks(total_chars)
    if should_fallback_to_attachment(total_chars, chunks):
        return DeliveryMode.ATTACHMENT_FALLBACK

    return DeliveryMode.CHUNKED


# ---------------------------------------------------------------------------
# Delivery record
# ---------------------------------------------------------------------------


@dataclass
class DeliveryRecord:
    """Tracks one logical delivery through its lifecycle."""

    reply_id: str
    delivery_mode: DeliveryMode
    total_chars: int
    total_chunks: int = 0
    delivered_chunks: int = 0
    failed_chunks: int = 0
    attachment_name: str = ""
    completion_state: DeliveryState = DeliveryState.PENDING
    retry_count: int = 0
    created_at: float = field(default_factory=time.time)
    completed_at: float | None = None

    # Attachment-specific tracking
    attachment_attempted: bool = False
    attachment_success: bool = False
    attachment_verified: bool = False
    attachment_file_size: int = 0
    fallback_triggered: bool = False

    # -- mutation helpers ---------------------------------------------------

    def mark_chunk_delivered(self) -> None:
        """Increment delivered_chunks."""
        self.delivered_chunks += 1

    def mark_chunk_failed(self) -> None:
        """Increment failed_chunks."""
        self.failed_chunks += 1

    def mark_complete(self) -> None:
        """Set completion_state to COMPLETE and record timestamp."""
        self.completion_state = DeliveryState.COMPLETE
        self.completed_at = time.time()

    def mark_partial(self) -> None:
        """Set completion_state to PARTIAL."""
        self.completion_state = DeliveryState.PARTIAL

    def mark_failed(self) -> None:
        """Set completion_state to FAILED."""
        self.completion_state = DeliveryState.FAILED

    # -- queries ------------------------------------------------------------

    def is_fully_delivered(self) -> bool:
        """Return True when every chunk has been delivered.

        For ATTACHMENT_FALLBACK mode, also requires attachment_verified.
        """
        chunks_ok = self.delivered_chunks == self.total_chunks and self.total_chunks > 0
        if self.delivery_mode == DeliveryMode.ATTACHMENT_FALLBACK:
            return chunks_ok and self.attachment_verified
        return chunks_ok

    # -- serialization ------------------------------------------------------

    def serialize(self) -> dict:
        """Return a JSON-safe dict for logging and event spine."""
        d = {
            "reply_id": self.reply_id,
            "delivery_mode": self.delivery_mode.value,
            "total_chars": self.total_chars,
            "total_chunks": self.total_chunks,
            "delivered_chunks": self.delivered_chunks,
            "failed_chunks": self.failed_chunks,
            "attachment_name": self.attachment_name,
            "completion_state": self.completion_state.value,
            "retry_count": self.retry_count,
            "created_at": self.created_at,
            "completed_at": self.completed_at,
        }
        if self.delivery_mode == DeliveryMode.ATTACHMENT_FALLBACK:
            d.update(
                {
                    "attachment_attempted": self.attachment_attempted,
                    "attachment_success": self.attachment_success,
                    "attachment_verified": self.attachment_verified,
                    "attachment_file_size": self.attachment_file_size,
                    "fallback_triggered": self.fallback_triggered,
                }
            )
        return d
