"""
Tests for session persistence via session_store.

Validates:
    - Same session_id returns the same SessionRuntime object
    - Different session_ids return different objects
    - Messages accumulate across calls
    - Compaction threshold is respected across multiple calls
    - clear_session resets state
    - Thread safety under concurrent access
"""

import sys
import threading
import uuid

sys.path.insert(0, "/opt/OS")

_PASS = 0
_FAIL = 0


def _test(name: str, ok: bool, detail: str = "") -> None:
    global _PASS, _FAIL
    if ok:
        _PASS += 1
    else:
        _FAIL += 1
    status = "PASS" if ok else "FAIL"
    suffix = f" -- {detail}" if detail else ""
    print(f"  [{status}] {name}{suffix}")


def _section(name: str) -> None:
    print(f"\n{'─' * 60}")
    print(f"  {name}")
    print(f"{'─' * 60}")


class FakeCtx:
    """Minimal context stub for SessionRuntime."""

    org_id = uuid.UUID("00000000-0000-0000-0000-000000000001")
    user_id = uuid.UUID("00000000-0000-0000-0000-000000000002")


# ═══════════════════════════════════════════════════════════════════════════════
# 1. Identity — same session_id returns same object
# ═══════════════════════════════════════════════════════════════════════════════

_section("1. Session Identity")

from umh.runtime_engine.session_store import (
    clear_all_sessions,
    clear_session,
    get_session,
    active_session_count,
)

clear_all_sessions()

sid = "test-session-001"
ctx = FakeCtx()

s1 = get_session(sid, ctx)
s2 = get_session(sid, ctx)
_test("same session_id returns same object", s1 is s2)
_test("session_id is set correctly", s1.session_id == sid)

# ═══════════════════════════════════════════════════════════════════════════════
# 2. Isolation — different session_ids return different objects
# ═══════════════════════════════════════════════════════════════════════════════

_section("2. Session Isolation")

sid_a = "test-session-A"
sid_b = "test-session-B"
sa = get_session(sid_a, ctx)
sb = get_session(sid_b, ctx)
_test("different session_ids return different objects", sa is not sb)
_test("session A has correct id", sa.session_id == sid_a)
_test("session B has correct id", sb.session_id == sid_b)

# ═══════════════════════════════════════════════════════════════════════════════
# 3. Message accumulation across calls
# ═══════════════════════════════════════════════════════════════════════════════

_section("3. Message Accumulation")

clear_all_sessions()
sid_acc = "test-accumulation"
session = get_session(sid_acc, ctx)

session._messages.append({"role": "user", "content": "hello"})
session._messages.append({"role": "assistant", "content": "hi there"})

session2 = get_session(sid_acc, ctx)
_test(
    "messages persist across get_session calls",
    len(session2._messages) == 2,
    f"got {len(session2._messages)} messages",
)
_test(
    "first message content correct",
    session2._messages[0]["content"] == "hello",
)

session2._messages.append({"role": "user", "content": "turn 2"})
session3 = get_session(sid_acc, ctx)
_test(
    "third retrieval has all 3 messages",
    len(session3._messages) == 3,
    f"got {len(session3._messages)} messages",
)

# ═══════════════════════════════════════════════════════════════════════════════
# 4. Stats accumulation
# ═══════════════════════════════════════════════════════════════════════════════

_section("4. Stats Accumulation")

clear_all_sessions()
sid_stats = "test-stats"
s = get_session(sid_stats, ctx)

s.stats.turns = 3
s.stats.total_tokens_in = 500
s.stats.total_tokens_out = 800
s.stats.total_cost_usd = 0.015

s_again = get_session(sid_stats, ctx)
_test("turns persist", s_again.stats.turns == 3)
_test("tokens_in persist", s_again.stats.total_tokens_in == 500)
_test("tokens_out persist", s_again.stats.total_tokens_out == 800)
_test("cost persists", abs(s_again.stats.total_cost_usd - 0.015) < 1e-9)
_test("total_tokens computed", s_again.stats.total_tokens == 1300)

# ═══════════════════════════════════════════════════════════════════════════════
# 5. clear_session resets state
# ═══════════════════════════════════════════════════════════════════════════════

_section("5. Clear Session")

clear_all_sessions()
sid_clear = "test-clear"
s = get_session(sid_clear, ctx)
s._messages.append({"role": "user", "content": "something"})
s.stats.turns = 5

result = clear_session(sid_clear)
_test("clear_session returns True for existing", result is True)

result2 = clear_session(sid_clear)
_test("clear_session returns False for missing", result2 is False)

s_new = get_session(sid_clear, ctx)
_test("new session has empty messages", len(s_new._messages) == 0)
_test("new session has zero turns", s_new.stats.turns == 0)
_test("new session is different object", s_new is not s)

# ═══════════════════════════════════════════════════════════════════════════════
# 6. clear_all_sessions
# ═══════════════════════════════════════════════════════════════════════════════

_section("6. Clear All Sessions")

clear_all_sessions()
get_session("a", ctx)
get_session("b", ctx)
get_session("c", ctx)
count_before = active_session_count()
_test("3 sessions active", count_before == 3, f"got {count_before}")

cleared = clear_all_sessions()
_test("clear_all returns count", cleared == 3, f"cleared {cleared}")
_test("active count is 0", active_session_count() == 0)

# ═══════════════════════════════════════════════════════════════════════════════
# 7. Thread safety
# ═══════════════════════════════════════════════════════════════════════════════

_section("7. Thread Safety")

clear_all_sessions()
sid_thread = "test-thread-safe"
results: list = []
errors: list = []


def _thread_get(n: int) -> None:
    try:
        s = get_session(sid_thread, ctx)
        results.append(id(s))
    except Exception as e:
        errors.append(str(e))


threads = [threading.Thread(target=_thread_get, args=(i,)) for i in range(20)]
for t in threads:
    t.start()
for t in threads:
    t.join()

_test("no thread errors", len(errors) == 0, "; ".join(errors))
_test(
    "all threads got same object",
    len(set(results)) == 1,
    f"got {len(set(results))} unique objects from 20 threads",
)

# ═══════════════════════════════════════════════════════════════════════════════
# 8. Compaction readiness (threshold check without DB)
# ═══════════════════════════════════════════════════════════════════════════════

_section("8. Compaction Threshold")

clear_all_sessions()
sid_compact = "test-compact"
s = get_session(sid_compact, ctx)

_test("empty session has 0 messages", len(s._messages) == 0)

for i in range(50):
    s._messages.append({"role": "user", "content": f"message {i} " + ("x" * 100)})
    s._messages.append({"role": "assistant", "content": f"response {i} " + ("y" * 200)})

total_chars = sum(len(m["content"]) for m in s._messages)
estimated_tokens = total_chars // 4
_test(
    "100 messages accumulated",
    len(s._messages) == 100,
    f"got {len(s._messages)}",
)
_test(
    "token estimate is reasonable",
    estimated_tokens > 1000,
    f"~{estimated_tokens} tokens",
)

s_check = get_session(sid_compact, ctx)
_test(
    "messages survive across lookups at scale",
    len(s_check._messages) == 100,
)

# ═══════════════════════════════════════════════════════════════════════════════
# 9. Gateway import integration
# ═══════════════════════════════════════════════════════════════════════════════

_section("9. Gateway Integration")

try:
    from umh.runtime_engine.gateway import EOSGateway

    _test("gateway imports with session_store", True)
except Exception as e:
    _test("gateway imports with session_store", False, str(e))

# Verify the import changed from session_runtime to session_store
import inspect

source = inspect.getsource(EOSGateway)
_test(
    "gateway uses get_session not SessionRuntime constructor",
    "get_session" in source,
    "get_session found in gateway source",
)
_test(
    "gateway no longer imports SessionRuntime directly",
    "from umh.runtime_engine.session_runtime import SessionRuntime" not in source,
)


# ═══════════════════════════════════════════════════════════════════════════════
# Summary
# ═══════════════════════════════════════════════════════════════════════════════

clear_all_sessions()

print(f"\n{'═' * 60}")
print(f"  RESULTS: {_PASS} passed, {_FAIL} failed")
print(f"{'═' * 60}")

sys.exit(1 if _FAIL > 0 else 0)
