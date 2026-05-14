"""
Backpressure and safety validation for the Discord relay pipeline.

Tests:
  1. RelayQueue compaction removes old entries
  2. RelayQueue respects max retry attempts
  3. EventStore compaction removes old entries
  4. Watcher callback errors don't crash the watcher
  5. _schedule_on_bot_loop returns False when loop is None
"""

import sys
import time

sys.path.insert(0, "/opt/OS")

PASS = 0
FAIL = 0


def check(name: str, condition: bool, detail: str = "") -> None:
    global PASS, FAIL
    if condition:
        PASS += 1
        print(f"  PASS  {name}")
    else:
        FAIL += 1
        msg = f"  FAIL  {name}"
        if detail:
            msg += f" — {detail}"
        print(msg)


# ═══════════════════════════════════════════════════════════════════════════
# 1. RelayQueue max retries
# ═══════════════════════════════════════════════════════════════════════════
print("\n═══ 1. RelayQueue Max Retries ═══")

import tempfile
import os

from umh.substrate.session_discord_bridge import RelayQueue

# Create temporary queue file
tmp_dir = tempfile.mkdtemp()
tmp_file = os.path.join(tmp_dir, "test_queue.jsonl")
q = RelayQueue(queue_file=tmp_file)

# Enqueue an item
q.enqueue({"event_id": "test1", "reply_text": "hello"})
pending = q.get_pending()
check("queue has 1 pending item", len(pending) == 1, f"got {len(pending)}")

# Mark it as failed 5 times (max attempts)
for i in range(5):
    q.mark_retrying("test1", i + 1)
q.mark_failed("test1", "max_retries", 5)
pending = q.get_pending()
check(
    "exhausted item not in pending",
    len(pending) == 0,
    f"got {len(pending)} pending items",
)

# Enqueue another and verify it's still retrievable
q.enqueue({"event_id": "test2", "reply_text": "world"})
pending = q.get_pending()
check(
    "new item still retrievable after exhausted item",
    len(pending) == 1 and pending[0]["event_id"] == "test2",
    f"got {len(pending)} items",
)

# ═══════════════════════════════════════════════════════════════════════════
# 2. RelayQueue compaction
# ═══════════════════════════════════════════════════════════════════════════
print("\n═══ 2. RelayQueue Compaction ═══")

tmp_file2 = os.path.join(tmp_dir, "test_queue2.jsonl")
q2 = RelayQueue(queue_file=tmp_file2)

# Add old completed item (simulate created_at 2 hours ago)
old_time = time.strftime(
    "%Y-%m-%dT%H:%M:%S%z", time.localtime(time.time() - 7200)
)
q2.enqueue({"event_id": "old1", "reply_text": "old", "created_at": old_time})
q2.mark_done("old1")  # status = sent

# Add recent item
q2.enqueue({"event_id": "recent1", "reply_text": "recent"})

removed = q2.compact()
check("compaction removes old completed item", removed == 1, f"removed {removed}")

# Recent queued item should survive
pending = q2.get_pending()
check(
    "recent item survives compaction",
    len(pending) == 1 and pending[0]["event_id"] == "recent1",
    f"got {len(pending)} items",
)


# ═══════════════════════════════════════════════════════════════════════════
# 3. EventStore compaction
# ═══════════════════════════════════════════════════════════════════════════
print("\n═══ 3. EventStore Compaction ═══")

from umh.substrate.event_spine import EventType, create_event
from umh.substrate.event_store import EventStore

tmp_store = os.path.join(tmp_dir, "test_spine.jsonl")
store = EventStore(path=tmp_store)

# Add an old event (fake timestamp)
old_event = create_event(EventType.REPLY_COMPLETE, source="test")
old_event.created_at = time.strftime(
    "%Y-%m-%dT%H:%M:%S%z", time.localtime(time.time() - 100000)
)
store.append(old_event)

# Add a recent event
recent_event = create_event(EventType.REPLY_COMPLETE, source="test")
store.append(recent_event)

removed = store.compact(max_age_hours=24)
check("event store compaction removes old events", removed == 1, f"removed {removed}")

recent = store.read_recent(limit=10)
check(
    "recent event survives compaction",
    len(recent) == 1 and recent[0].event_id == recent_event.event_id,
    f"got {len(recent)} events",
)


# ═══════════════════════════════════════════════════════════════════════════
# 4. SessionDiscordBridge handles no loop gracefully
# ═══════════════════════════════════════════════════════════════════════════
print("\n═══ 4. Bridge No-Loop Safety ═══")

from umh.substrate.session_discord_bridge import SessionDiscordBridge

bridge = SessionDiscordBridge()
# bridge._loop is None (no bot registered)

import asyncio

async def noop():
    pass

result = bridge._schedule_on_bot_loop(noop())
check(
    "schedule returns False when loop is None",
    result is False,
    f"got: {result}",
)


# ═══════════════════════════════════════════════════════════════════════════
# 5. Watcher callback error isolation
# ═══════════════════════════════════════════════════════════════════════════
print("\n═══ 5. Watcher Callback Error Isolation ═══")

from umh.substrate.session_watcher import SessionWatcher, SessionState, WatcherEvent

# Create a watcher with a callback that throws
errors_caught = []


def bad_callback(event):
    raise ValueError("Intentional test error")


watcher = SessionWatcher("test", "test_session", on_event=bad_callback)

# Manually call _emit — should NOT raise
test_event = WatcherEvent(
    session_name="test_session",
    state=SessionState.COMPLETE,
    text="test reply",
)

try:
    watcher._emit(test_event)
    check("callback error does not propagate", True, "")
except Exception as e:
    check("callback error does not propagate", False, f"propagated: {e}")


# ═══════════════════════════════════════════════════════════════════════════
# 6. Event spine role-aware dedup
# ═══════════════════════════════════════════════════════════════════════════
print("\n═══ 6. Role-Aware Dedup ═══")

from umh.substrate.event_spine import EventStatus

tmp_dedup = os.path.join(tmp_dir, "test_dedup.jsonl")
dedup_store = EventStore(path=tmp_dedup)

# Create a completed reply for builder
builder_reply = create_event(
    EventType.REPLY_COMPLETE,
    source="test",
    role="builder",
    correlation_id="corr_123",
)
builder_reply.update_status(EventStatus.COMPLETED)
dedup_store.append(builder_reply)

# Builder should be detected as completed
check(
    "builder reply detected as completed",
    dedup_store.has_completed_reply("corr_123", role="builder"),
    "",
)

# Product should NOT be blocked by builder's reply
check(
    "product NOT blocked by builder reply",
    not dedup_store.has_completed_reply("corr_123", role="ea_product"),
    "",
)

# Different correlation_id should not match
check(
    "different correlation_id not matched",
    not dedup_store.has_completed_reply("corr_999", role="builder"),
    "",
)


# Cleanup
import shutil

shutil.rmtree(tmp_dir)


# ═══════════════════════════════════════════════════════════════════════════
# RESULTS
# ═══════════════════════════════════════════════════════════════════════════
print(f"\n{'═' * 60}")
print(f"RESULTS: {PASS} passed, {FAIL} failed, {PASS + FAIL} total")
print(f"{'═' * 60}")

if FAIL > 0:
    print("\n⚠️  BACKPRESSURE/SAFETY ISSUES DETECTED")
    sys.exit(1)
else:
    print("\n✅ Backpressure and safety checks pass")
    sys.exit(0)
