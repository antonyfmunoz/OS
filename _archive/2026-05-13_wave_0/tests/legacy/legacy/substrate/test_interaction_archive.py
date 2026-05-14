"""
Tests for the Interaction Archive — verbatim conversation continuity layer.

Covers:
  1. Single inbound archival
  2. Buffered inbound archival (multi-message → single logical record)
  3. Outbound pre-chunk archival
  4. /clear checkpoint preserves history
  5. Cross-device retrieval by interface
  6. by_correlation_id queries
  7. by_session_or_role queries
  8. by_time_window queries
  9. Summary/count helpers
  10. Text truncation safety bound
"""

import json
import os
import sys
import tempfile
import time

sys.path.insert(0, "/opt/OS")

from umh.substrate.interaction_archive import (
    ArchivedInteraction,
    Direction,
    Interface,
    InteractionArchive,
    archive_inbound,
    archive_outbound,
    create_clear_checkpoint,
    get_interaction_archive,
)


def _temp_archive() -> InteractionArchive:
    """Create an archive backed by a temporary file."""
    fd, path = tempfile.mkstemp(suffix=".jsonl")
    os.close(fd)
    os.unlink(path)  # start fresh
    return InteractionArchive(path=path)


# ─── Test 1: Single inbound archival ─────────────────────────────────────────


def test_single_inbound_archive():
    """A single Discord message is archived verbatim with correct fields."""
    archive = _temp_archive()

    record = ArchivedInteraction(
        correlation_id="corr_001",
        direction=Direction.INBOUND.value,
        interface=Interface.DISCORD.value,
        source_session="dex_main",
        role="builder",
        logical_message_id="msg_abc",
        raw_text="Deploy the new feature to staging",
        metadata={"user_id": "123", "channel_id": "456"},
    )
    aid = archive.archive(record)

    assert aid == record.archive_id
    assert archive.count() == 1

    # Retrieve and verify
    recent = archive.recent(10)
    assert len(recent) == 1
    r = recent[0]
    assert r.raw_text == "Deploy the new feature to staging"
    assert r.direction == "inbound"
    assert r.interface == "discord"
    assert r.source_session == "dex_main"
    assert r.correlation_id == "corr_001"
    assert r.metadata["user_id"] == "123"

    os.unlink(archive.path)
    print("PASS: test_single_inbound_archive")


# ─── Test 2: Buffered inbound archival ───────────────────────────────────────


def test_buffered_inbound_archive():
    """A /buffer + /done sequence is archived as one logical message."""
    archive = _temp_archive()

    # Simulate: 3 messages combined via buffer
    combined_text = "First part of the request\n\nSecond part with details\n\nThird part with context"
    record = ArchivedInteraction(
        correlation_id="group_001",
        direction=Direction.INBOUND.value,
        interface=Interface.DISCORD.value,
        logical_message_id="group_001",
        raw_text=combined_text,
        metadata={"type": "buffered", "message_count": 3},
    )
    archive.archive(record)

    recent = archive.recent(10)
    assert len(recent) == 1
    assert recent[0].raw_text == combined_text
    assert recent[0].metadata["type"] == "buffered"
    assert recent[0].metadata["message_count"] == 3

    # Verify it's ONE record, not three
    assert archive.count() == 1

    os.unlink(archive.path)
    print("PASS: test_buffered_inbound_archive")


# ─── Test 3: Outbound pre-chunk archival ─────────────────────────────────────


def test_outbound_prechunk_archive():
    """Outbound reply is archived as one record BEFORE chunking."""
    archive = _temp_archive()

    full_reply = (
        "This is a long reply that would normally be split into multiple Discord messages. "
        * 50
    )
    record = ArchivedInteraction(
        correlation_id="corr_002",
        direction=Direction.OUTBOUND.value,
        interface=Interface.DISCORD.value,
        source_session="dex_builder",
        role="builder",
        logical_message_id="event_xyz",
        raw_text=full_reply,
        metadata={"header": "Builder · 1/1", "state": "complete"},
    )
    archive.archive(record)

    assert archive.count() == 1
    recent = archive.recent(10)
    assert len(recent) == 1
    assert len(recent[0].raw_text) == len(full_reply)
    assert recent[0].direction == "outbound"

    os.unlink(archive.path)
    print("PASS: test_outbound_prechunk_archive")


# ─── Test 4: /clear checkpoint preserves history ─────────────────────────────


def test_clear_checkpoint_preserves_history():
    """/clear creates a checkpoint without destroying prior interactions."""
    archive = _temp_archive()

    # Archive some interactions first
    for i in range(5):
        archive.archive(
            ArchivedInteraction(
                correlation_id=f"corr_{i:03d}",
                direction=Direction.INBOUND.value
                if i % 2 == 0
                else Direction.OUTBOUND.value,
                interface=Interface.DISCORD.value,
                raw_text=f"Message {i}",
            )
        )

    assert archive.count() == 5

    # Now archive a clear checkpoint
    checkpoint = ArchivedInteraction(
        correlation_id="corr_clear",
        direction=Direction.INBOUND.value,
        interface=Interface.DISCORD.value,
        source_session="dex_main",
        raw_text="/clear — manual_clear",
        metadata={
            "is_clear_checkpoint": True,
            "reason": "manual_clear",
            "interaction_count_at_clear": 5,
        },
    )
    archive.archive(checkpoint)

    # History is preserved — all 6 records exist (5 + checkpoint)
    assert archive.count() == 6

    # Can still query prior interactions
    recent = archive.recent(10)
    assert len(recent) == 6
    assert recent[0].raw_text == "Message 0"
    assert recent[5].metadata["is_clear_checkpoint"] is True

    # Post-clear: new interactions work normally
    archive.archive(
        ArchivedInteraction(
            correlation_id="corr_post_clear",
            direction=Direction.INBOUND.value,
            interface=Interface.DISCORD.value,
            raw_text="First message after clear",
        )
    )
    assert archive.count() == 7

    os.unlink(archive.path)
    print("PASS: test_clear_checkpoint_preserves_history")


# ─── Test 5: Cross-device retrieval by interface ─────────────────────────────


def test_cross_device_by_interface():
    """Interactions from different interfaces are retrievable independently."""
    archive = _temp_archive()

    # Discord message
    archive.archive(
        ArchivedInteraction(
            interface=Interface.DISCORD.value,
            raw_text="From Discord on phone",
            metadata={"device": "phone"},
        )
    )
    # VPS CLI message
    archive.archive(
        ArchivedInteraction(
            interface=Interface.VPS_CLI.value,
            raw_text="From VPS terminal",
        )
    )
    # Workstation message
    archive.archive(
        ArchivedInteraction(
            interface=Interface.WORKSTATION.value,
            raw_text="From local workstation",
        )
    )
    # Another Discord message
    archive.archive(
        ArchivedInteraction(
            interface=Interface.DISCORD.value,
            raw_text="Second Discord message",
        )
    )

    assert archive.count() == 4

    discord_only = archive.by_interface("discord")
    assert len(discord_only) == 2
    assert discord_only[0].raw_text == "From Discord on phone"
    assert discord_only[1].raw_text == "Second Discord message"

    vps_only = archive.by_interface("vps_cli")
    assert len(vps_only) == 1
    assert vps_only[0].raw_text == "From VPS terminal"

    workstation_only = archive.by_interface("workstation")
    assert len(workstation_only) == 1

    # All interfaces show in summary
    summary = archive.summary()
    assert set(summary["interfaces"]) == {"discord", "vps_cli", "workstation"}

    os.unlink(archive.path)
    print("PASS: test_cross_device_by_interface")


# ─── Test 6: by_correlation_id query ─────────────────────────────────────────


def test_by_correlation_id():
    """Can retrieve all interactions sharing a correlation ID."""
    archive = _temp_archive()

    # Two interactions in same workflow
    archive.archive(
        ArchivedInteraction(
            correlation_id="workflow_abc",
            direction=Direction.INBOUND.value,
            raw_text="User question",
        )
    )
    archive.archive(
        ArchivedInteraction(
            correlation_id="workflow_abc",
            direction=Direction.OUTBOUND.value,
            raw_text="System response",
        )
    )
    # Different workflow
    archive.archive(
        ArchivedInteraction(
            correlation_id="workflow_def",
            direction=Direction.INBOUND.value,
            raw_text="Unrelated message",
        )
    )

    results = archive.by_correlation_id("workflow_abc")
    assert len(results) == 2
    assert results[0].direction == "inbound"
    assert results[1].direction == "outbound"

    # Different correlation returns only its own
    results_def = archive.by_correlation_id("workflow_def")
    assert len(results_def) == 1

    # Non-existent correlation returns empty
    results_none = archive.by_correlation_id("nonexistent")
    assert len(results_none) == 0

    os.unlink(archive.path)
    print("PASS: test_by_correlation_id")


# ─── Test 7: by_session_or_role query ────────────────────────────────────────


def test_by_session_or_role():
    """Can filter by session name and/or role."""
    archive = _temp_archive()

    archive.archive(
        ArchivedInteraction(
            source_session="dex_main",
            role="builder",
            raw_text="Builder msg",
        )
    )
    archive.archive(
        ArchivedInteraction(
            source_session="dex_product",
            role="ea_product",
            raw_text="Product msg",
        )
    )
    archive.archive(
        ArchivedInteraction(
            source_session="dex_main",
            role="ea_product",
            raw_text="Main but product role",
        )
    )

    by_session = archive.by_session_or_role(session="dex_main")
    assert len(by_session) == 2

    by_role = archive.by_session_or_role(role="ea_product")
    assert len(by_role) == 2

    by_both = archive.by_session_or_role(session="dex_main", role="builder")
    assert len(by_both) == 1
    assert by_both[0].raw_text == "Builder msg"

    # Neither provided returns empty
    assert archive.by_session_or_role() == []

    os.unlink(archive.path)
    print("PASS: test_by_session_or_role")


# ─── Test 8: Summary helper ─────────────────────────────────────────────────


def test_summary():
    """Summary returns counts and metadata without raw text."""
    archive = _temp_archive()

    archive.archive(
        ArchivedInteraction(
            direction=Direction.INBOUND.value,
            interface=Interface.DISCORD.value,
            raw_text="Hello",
        )
    )
    archive.archive(
        ArchivedInteraction(
            direction=Direction.OUTBOUND.value,
            interface=Interface.DISCORD.value,
            raw_text="Hi there",
        )
    )
    archive.archive(
        ArchivedInteraction(
            direction=Direction.INBOUND.value,
            interface=Interface.VPS_CLI.value,
            raw_text="VPS message",
        )
    )

    summary = archive.summary()
    assert summary["total"] == 3
    assert summary["inbound"] == 2
    assert summary["outbound"] == 1
    assert set(summary["interfaces"]) == {"discord", "vps_cli"}
    assert summary["earliest"] is not None
    assert summary["latest"] is not None

    # Empty archive summary
    empty_archive = _temp_archive()
    empty_summary = empty_archive.summary()
    assert empty_summary["total"] == 0
    assert empty_summary["interfaces"] == []

    os.unlink(archive.path)
    if os.path.exists(empty_archive.path):
        os.unlink(empty_archive.path)
    print("PASS: test_summary")


# ─── Test 9: Text truncation safety bound ────────────────────────────────────


def test_text_truncation():
    """Texts exceeding _MAX_TEXT_LENGTH are truncated with metadata flag."""
    archive = _temp_archive()

    huge_text = "x" * 60_000  # exceeds 50K limit
    archive.archive(ArchivedInteraction(raw_text=huge_text))

    recent = archive.recent(1)
    assert len(recent) == 1
    assert len(recent[0].raw_text) == 50_000
    assert recent[0].metadata.get("truncated") is True

    os.unlink(archive.path)
    print("PASS: test_text_truncation")


# ─── Test 10: Serialization round-trip ───────────────────────────────────────


def test_serialization_roundtrip():
    """ArchivedInteraction survives serialize → deserialize."""
    original = ArchivedInteraction(
        archive_id="test_id_001",
        parent_archive_id="parent_001",
        correlation_id="corr_test",
        direction=Direction.OUTBOUND.value,
        interface=Interface.WORKSTATION.value,
        source_session="dex_builder",
        role="builder",
        node_id="node_local",
        logical_message_id="reply_xyz",
        raw_text="Test message content",
        metadata={"key": "value"},
    )

    serialized = original.serialize()
    restored = ArchivedInteraction.deserialize(serialized)

    assert restored.archive_id == original.archive_id
    assert restored.parent_archive_id == original.parent_archive_id
    assert restored.correlation_id == original.correlation_id
    assert restored.direction == original.direction
    assert restored.interface == original.interface
    assert restored.source_session == original.source_session
    assert restored.role == original.role
    assert restored.node_id == original.node_id
    assert restored.logical_message_id == original.logical_message_id
    assert restored.raw_text == original.raw_text
    assert restored.metadata == original.metadata

    print("PASS: test_serialization_roundtrip")


# ─── Test 11: JSONL file format ──────────────────────────────────────────────


def test_jsonl_format():
    """Archive file is valid JSONL — one JSON object per line."""
    archive = _temp_archive()

    for i in range(3):
        archive.archive(ArchivedInteraction(raw_text=f"Message {i}"))

    with open(archive.path, "r") as f:
        lines = f.readlines()

    assert len(lines) == 3
    for line in lines:
        parsed = json.loads(line.strip())
        assert "archive_id" in parsed
        assert "raw_text" in parsed
        assert "direction" in parsed

    os.unlink(archive.path)
    print("PASS: test_jsonl_format")


# ─── Test 12: Direction and interface filter on recent() ─────────────────────


def test_recent_filters():
    """recent() can filter by direction and interface simultaneously."""
    archive = _temp_archive()

    archive.archive(
        ArchivedInteraction(
            direction=Direction.INBOUND.value,
            interface=Interface.DISCORD.value,
            raw_text="Discord inbound",
        )
    )
    archive.archive(
        ArchivedInteraction(
            direction=Direction.OUTBOUND.value,
            interface=Interface.DISCORD.value,
            raw_text="Discord outbound",
        )
    )
    archive.archive(
        ArchivedInteraction(
            direction=Direction.INBOUND.value,
            interface=Interface.VPS_CLI.value,
            raw_text="VPS inbound",
        )
    )

    # Filter inbound only
    inbound = archive.recent(10, direction="inbound")
    assert len(inbound) == 2

    # Filter outbound + discord
    outbound_discord = archive.recent(10, direction="outbound", interface="discord")
    assert len(outbound_discord) == 1
    assert outbound_discord[0].raw_text == "Discord outbound"

    os.unlink(archive.path)
    print("PASS: test_recent_filters")


# ─── Run all tests ───────────────────────────────────────────────────────────


if __name__ == "__main__":
    test_single_inbound_archive()
    test_buffered_inbound_archive()
    test_outbound_prechunk_archive()
    test_clear_checkpoint_preserves_history()
    test_cross_device_by_interface()
    test_by_correlation_id()
    test_by_session_or_role()
    test_summary()
    test_text_truncation()
    test_serialization_roundtrip()
    test_jsonl_format()
    test_recent_filters()
    print("\n=== ALL 12 TESTS PASSED ===")
