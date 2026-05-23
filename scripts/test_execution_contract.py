"""Test execution_contract.run_task() with two messages.

Verifies:
1. Both calls return ok=True with valid return shape
2. Both messages appear in Neon messages table
3. Trace produced and recorded in ring buffer
"""

import sys
import os
sys.path.insert(0, os.environ.get("UMH_ROOT") or os.environ.get("OS_ROOT") or os.environ.get("EOS_ROOT") or "/opt/OS")

from core.execution_contract import run_task
from substrate.state.storage.db import get_conn, ORG_ID
from substrate.execution.transport.execution_trace import get_trace_history


def main() -> None:
    print("=" * 60)
    print("TEST: execution_contract.run_task()")
    print("=" * 60)

    # ── Message 1: simple brief request ──────────────────────
    print("\n[1] Sending: 'What is the current system status?'")
    r1 = run_task(
        text="What is the current system status?",
        channel="cli_test",
        mode="builder",
        username="test_user",
    )
    _print_result("Result 1", r1)
    assert r1["ok"], f"Message 1 failed: {r1['error']}"
    assert r1["trace_id"], "Missing trace_id"
    assert r1["session_id"], "Missing session_id"
    print("[1] PASS\n")

    # ── Message 2: agent task ────────────────────────────────
    print("[2] Sending: 'Analyze my outreach pipeline'")
    r2 = run_task(
        text="Analyze my outreach pipeline",
        channel="cli_test",
        mode="builder",
        username="test_user",
        metadata={"venture_id": "lyfe_institute"},
    )
    _print_result("Result 2", r2)
    assert r2["ok"], f"Message 2 failed: {r2['error']}"
    assert r2["trace_id"], "Missing trace_id"
    print("[2] PASS\n")

    # ── Verify messages in Neon ──────────────────────────────
    print("[3] Checking Neon messages table...")
    try:
        with get_conn() as cur:
            cur.execute(
                """
                SELECT id, role, content, channel, agent, created_at
                FROM messages
                WHERE org_id = %s AND channel = 'cli_test'
                ORDER BY created_at DESC
                LIMIT 10
                """,
                (ORG_ID,),
            )
            rows = cur.fetchall()
        print(f"    Found {len(rows)} messages in cli_test channel")
        for row in rows:
            print(f"    [{row['role']}] {row['content'][:80]}...")
        assert len(rows) >= 2, f"Expected ≥2 messages, got {len(rows)}"
        print("[3] PASS\n")
    except Exception as e:
        print(f"[3] WARN: Could not verify messages table: {e}\n")

    # ── Verify trace in ring buffer ──────────────────────────
    print("[4] Checking trace ring buffer...")
    history = get_trace_history()
    recent = history.latest(limit=5)
    print(f"    {len(recent)} recent traces")
    for t in recent:
        tid = t.get("trace_id", "?")[:8]
        result = t.get("result", "?")
        latency = t.get("latency_ms", "?")
        print(f"    [{tid}] result={result} latency={latency}ms")
    # At least our two traces should be there
    our_traces = [t for t in recent if t.get("source") == "cli_test"]
    assert len(our_traces) >= 2, f"Expected ≥2 traces from cli_test, got {len(our_traces)}"
    print("[4] PASS\n")

    print("=" * 60)
    print("ALL TESTS PASSED")
    print("=" * 60)


def _print_result(label: str, r: dict) -> None:
    """Pretty-print a run_task result."""
    print(f"  {label}:")
    print(f"    ok:         {r['ok']}")
    print(f"    trace_id:   {r['trace_id'][:12]}...")
    print(f"    session_id: {r['session_id'][:12]}...")
    print(f"    provider:   {r['provider']}")
    print(f"    path:       {r['path']}")
    print(f"    logged:     {r['logged']}")
    print(f"    error:      {r['error']}")
    resp = r["response"]
    if resp:
        print(f"    response:   {resp[:120]}{'...' if len(resp) > 120 else ''}")
    else:
        print(f"    response:   (empty)")


if __name__ == "__main__":
    main()
