"""
Tests for the Discord message framing protocol.

Validates:
  - Outbound: single-chunk framing, multi-chunk framing, completion markers,
    failed chunk does not mark complete.
  - Inbound: /done buffering, /done with no buffer, single-message passthrough,
    buffer order preservation.
"""

import sys
import time

sys.path.insert(0, "/opt/OS")

from umh.substrate.message_framing import (
    InboundBuffer,
    OutboundFrame,
    ReplyTracker,
    apply_outbound_framing,
    get_inbound_buffer,
    get_reply_tracker,
)


# ─── Outbound Tests ────────────────────────────────────────────────────────


class TestOutboundFrameSingleChunk:
    """Single-chunk reply includes stable reply ID and completion marker."""

    def test_single_chunk_has_reply_id(self) -> None:
        frame = OutboundFrame(role="Builder")
        assert len(frame.reply_id) == 12
        assert frame.ref_short == frame.reply_id[:4]

    def test_single_chunk_framing(self) -> None:
        frame = OutboundFrame(role="Builder")
        chunks = ["This is a short reply."]
        framed = apply_outbound_framing(chunks, frame)

        assert len(framed) == 1
        assert frame.chunk_count == 1

        text = framed[0]
        # Header present
        assert f"Builder · 1/1 · ref {frame.ref_short}" in text
        # Completion footer present
        assert f"✓ Complete · ref {frame.ref_short}" in text
        # Content present
        assert "This is a short reply." in text

    def test_single_chunk_marked_complete_in_frame(self) -> None:
        frame = OutboundFrame(role="System")
        chunks = ["Hello"]
        framed = apply_outbound_framing(chunks, frame)
        assert frame.chunk_count == 1
        # Completion footer on the only chunk
        assert "✓ Complete" in framed[0]


class TestOutboundFrameMultiChunk:
    """Multi-chunk reply includes chunk numbering and final completion footer."""

    def test_multi_chunk_numbering(self) -> None:
        frame = OutboundFrame(role="Builder")
        chunks = ["Chunk one content.", "Chunk two content.", "Chunk three content."]
        framed = apply_outbound_framing(chunks, frame)

        assert len(framed) == 3
        assert frame.chunk_count == 3

        # First chunk: 1/3, no completion footer
        assert f"Builder · 1/3 · ref {frame.ref_short}" in framed[0]
        assert "✓ Complete" not in framed[0]

        # Second chunk: 2/3, no completion footer
        assert f"Builder · 2/3 · ref {frame.ref_short}" in framed[1]
        assert "✓ Complete" not in framed[1]

        # Third chunk: 3/3, HAS completion footer
        assert f"Builder · 3/3 · ref {frame.ref_short}" in framed[2]
        assert f"✓ Complete · ref {frame.ref_short}" in framed[2]

    def test_strips_existing_part_labels(self) -> None:
        """Existing Part N/M labels from chunk_message() are replaced."""
        frame = OutboundFrame(role="EA")
        chunks = ["*Part 1/2*\n\nFirst part.", "*Part 2/2*\n\nSecond part."]
        framed = apply_outbound_framing(chunks, frame)

        for text in framed:
            assert "*Part" not in text

        assert "EA · 1/2" in framed[0]
        assert "EA · 2/2" in framed[1]

    def test_correlation_id_preserved(self) -> None:
        frame = OutboundFrame(role="Builder", correlation_id="abc123")
        chunks = ["Content"]
        apply_outbound_framing(chunks, frame)
        assert frame.correlation_id == "abc123"


class TestReplyTracker:
    """Internal state tracks logical reply completion correctly."""

    def test_register_and_query(self) -> None:
        tracker = ReplyTracker()
        frame = OutboundFrame(role="Builder")
        frame.chunk_count = 3
        tracker.register(frame)

        status = tracker.get_status(frame.reply_id)
        assert status is not None
        assert status["reply_id"] == frame.reply_id
        assert status["chunk_count"] == 3
        assert status["completed"] is False
        assert status["chunks_sent"] == []

    def test_mark_chunks_sent(self) -> None:
        tracker = ReplyTracker()
        frame = OutboundFrame(role="Builder")
        frame.chunk_count = 2
        tracker.register(frame)

        tracker.mark_chunk_sent(frame.reply_id, 0)
        status = tracker.get_status(frame.reply_id)
        assert status["chunks_sent"] == [0]

        tracker.mark_chunk_sent(frame.reply_id, 1)
        status = tracker.get_status(frame.reply_id)
        assert status["chunks_sent"] == [0, 1]

    def test_mark_completed(self) -> None:
        tracker = ReplyTracker()
        frame = OutboundFrame(role="Builder")
        frame.chunk_count = 1
        tracker.register(frame)
        tracker.mark_chunk_sent(frame.reply_id, 0)
        tracker.mark_completed(frame.reply_id)

        assert tracker.is_complete(frame.reply_id) is True
        status = tracker.get_status(frame.reply_id)
        assert status["completed"] is True
        assert status["completed_at"] is not None

    def test_failed_chunk_does_not_mark_complete(self) -> None:
        """If a chunk was never sent, reply must not be marked complete."""
        tracker = ReplyTracker()
        frame = OutboundFrame(role="Builder")
        frame.chunk_count = 3
        tracker.register(frame)

        # Only sent chunks 0 and 1, chunk 2 failed
        tracker.mark_chunk_sent(frame.reply_id, 0)
        tracker.mark_chunk_sent(frame.reply_id, 1)
        # Do NOT call mark_completed — simulating send failure

        assert tracker.is_complete(frame.reply_id) is False
        status = tracker.get_status(frame.reply_id)
        assert status["chunks_sent"] == [0, 1]
        assert status["completed"] is False

    def test_unknown_reply_id(self) -> None:
        tracker = ReplyTracker()
        assert tracker.get_status("nonexistent") is None
        assert tracker.is_complete("nonexistent") is False

    def test_prune(self) -> None:
        tracker = ReplyTracker()
        frame = OutboundFrame(role="Builder")
        frame.chunk_count = 1
        frame.created_at = time.time() - 7200  # 2 hours old
        tracker.register(frame)
        tracker.mark_completed(frame.reply_id)

        removed = tracker.prune(max_age_seconds=3600)
        assert removed == 1
        assert tracker.get_status(frame.reply_id) is None


# ─── Inbound Tests ─────────────────────────────────────────────────────────


class TestInboundBuffer:
    """Inbound multi-message buffering with /done finalization."""

    def test_buffer_add_and_finalize(self) -> None:
        """Multiple user messages + /done become one logical input."""
        buf = InboundBuffer()
        buf.add("user1", "chan1", "First message")
        buf.add("user1", "chan1", "Second message")
        buf.add("user1", "chan1", "Third message")

        group = buf.finalize("user1", "chan1")
        assert group is not None
        assert group.message_count == 3
        assert group.combined_text == "First message\n\nSecond message\n\nThird message"
        assert group.finalized_at is not None

    def test_done_with_no_buffer(self) -> None:
        """/done with no active buffer returns None."""
        buf = InboundBuffer()
        group = buf.finalize("user1", "chan1")
        assert group is None

    def test_single_message_passthrough(self) -> None:
        """Existing single-message input path still works (no buffer active)."""
        buf = InboundBuffer()
        assert buf.has_active("user1", "chan1") is False
        assert buf.get_count("user1", "chan1") == 0

    def test_buffer_order_preserved(self) -> None:
        """Buffered message order is preserved."""
        buf = InboundBuffer()
        for i in range(5):
            buf.add("user1", "chan1", f"Message {i}")

        group = buf.finalize("user1", "chan1")
        assert group is not None
        lines = group.combined_text.split("\n\n")
        assert lines == [f"Message {i}" for i in range(5)]

    def test_per_user_isolation(self) -> None:
        """Buffers are isolated per user+channel."""
        buf = InboundBuffer()
        buf.add("user1", "chan1", "User 1 msg")
        buf.add("user2", "chan1", "User 2 msg")

        assert buf.has_active("user1", "chan1") is True
        assert buf.has_active("user2", "chan1") is True

        g1 = buf.finalize("user1", "chan1")
        g2 = buf.finalize("user2", "chan1")

        assert g1.combined_text == "User 1 msg"
        assert g2.combined_text == "User 2 msg"
        assert g1.group_id != g2.group_id

    def test_per_channel_isolation(self) -> None:
        """Same user, different channels = different buffers."""
        buf = InboundBuffer()
        buf.add("user1", "chan1", "Chan 1 msg")
        buf.add("user1", "chan2", "Chan 2 msg")

        g1 = buf.finalize("user1", "chan1")
        g2 = buf.finalize("user1", "chan2")

        assert g1.combined_text == "Chan 1 msg"
        assert g2.combined_text == "Chan 2 msg"

    def test_abandon(self) -> None:
        """Abandon clears buffer without submitting."""
        buf = InboundBuffer()
        buf.add("user1", "chan1", "Message 1")
        buf.add("user1", "chan1", "Message 2")

        abandoned = buf.abandon("user1", "chan1")
        assert abandoned is not None
        assert abandoned.message_count == 2
        assert buf.has_active("user1", "chan1") is False

    def test_cleanup_stale(self) -> None:
        """Stale buffers are cleaned up."""
        buf = InboundBuffer()
        buf.add("user1", "chan1", "Old message")

        # Manually backdate the buffer
        key = "user1:chan1"
        with buf._lock:
            buf._buffers[key].created_at = time.time() - 600

        removed = buf.cleanup_stale()
        assert removed == 1
        assert buf.has_active("user1", "chan1") is False

    def test_finalized_history(self) -> None:
        """Finalized groups appear in history."""
        buf = InboundBuffer()
        buf.add("user1", "chan1", "Msg 1")
        buf.finalize("user1", "chan1")

        history = buf.get_finalized_history()
        assert len(history) == 1
        assert history[0]["user_id"] == "user1"
        assert history[0]["channel_id"] == "chan1"
        assert history[0]["message_count"] == 1
        assert history[0]["finalized_at"] is not None

    def test_group_serialization(self) -> None:
        """InboundMessageGroup serializes for tracing."""
        buf = InboundBuffer()
        buf.add("user1", "chan1", "Hello")
        buf.add("user1", "chan1", "World")
        group = buf.finalize("user1", "chan1")

        data = group.serialize()
        assert data["user_id"] == "user1"
        assert data["channel_id"] == "chan1"
        assert data["message_count"] == 2
        assert data["combined_text_length"] == len("Hello\n\nWorld")
        assert "group_id" in data


# ─── Integration: frame + tracker lifecycle ─────────────────────────────────


class TestOutboundLifecycle:
    """Full outbound lifecycle: frame → chunk → track → complete."""

    def test_full_lifecycle(self) -> None:
        tracker = ReplyTracker()
        frame = OutboundFrame(role="Builder", correlation_id="corr-001")

        # Simulate chunking
        raw_chunks = ["First part of reply.", "Second part of reply."]
        framed = apply_outbound_framing(raw_chunks, frame)
        assert frame.chunk_count == 2

        # Register
        tracker.register(frame)
        assert tracker.is_complete(frame.reply_id) is False

        # Simulate sending both chunks
        tracker.mark_chunk_sent(frame.reply_id, 0)
        tracker.mark_chunk_sent(frame.reply_id, 1)
        tracker.mark_completed(frame.reply_id)

        assert tracker.is_complete(frame.reply_id) is True
        status = tracker.get_status(frame.reply_id)
        assert status["chunks_sent"] == [0, 1]
        assert status["correlation_id"] == "corr-001"

    def test_partial_send_not_complete(self) -> None:
        """If last chunk fails, reply is NOT marked complete."""
        tracker = ReplyTracker()
        frame = OutboundFrame(role="Builder")
        frame.chunk_count = 3
        tracker.register(frame)

        tracker.mark_chunk_sent(frame.reply_id, 0)
        tracker.mark_chunk_sent(frame.reply_id, 1)
        # Chunk 2 fails — do NOT call mark_completed

        assert tracker.is_complete(frame.reply_id) is False


if __name__ == "__main__":
    import pytest

    pytest.main([__file__, "-v"])
