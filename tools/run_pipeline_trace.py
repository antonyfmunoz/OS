#!/usr/bin/env python3
"""
Run ONE Builder session interaction and dump the full pipeline trace.

Usage:
    python3 scripts/run_pipeline_trace.py

What it does:
1. Clears the trace log
2. Sends a simple message to dex_builder_main
3. Waits for the watcher to detect completion (up to 120s)
4. Dumps the ordered trace to stdout
5. Reports the first missing transition
"""

import json
import sys
import time

sys.path.insert(0, "/opt/OS")

from umh.substrate.pipeline_tracer import get_tracer
from umh.substrate.session_watcher import get_watcher
from umh.substrate.claude_session_bridge import send_message, capture_output

SESSION = "dex_builder_main"
TARGET = "vps"
# Simple, fast-completing prompt — just ask for a one-word answer
TEST_PROMPT = 'respond with exactly: "trace_probe_ok". Nothing else.'
TIMEOUT_S = 120


def main() -> None:
    tracer = get_tracer()
    tracer.clear()
    print(f"[trace_runner] Trace file: {tracer.dump_file()}")
    print(f"[trace_runner] Cleared trace log")

    # Check if watcher is running
    watcher = get_watcher(SESSION)
    if watcher:
        print(f"[trace_runner] Watcher found for {SESSION} — state={watcher.state.value}")
    else:
        print(f"[trace_runner] WARNING: No watcher running for {SESSION}")
        print(f"[trace_runner] The trace will only show lifecycle events (no watcher/bridge/publisher)")
        print(f"[trace_runner] The watcher is started by os-discord — is the bot running?")

    # Verify session is idle (has prompt)
    cap = capture_output(TARGET, SESSION, tail_lines=10)
    if cap.get("ok"):
        tail = cap["output"]
        if "❯" not in tail:
            print(f"[trace_runner] WARNING: No prompt visible — session may not be idle")
            print(f"[trace_runner] Tail: {tail[-200:]}")
    else:
        print(f"[trace_runner] ERROR: Cannot capture output: {cap}")
        sys.exit(1)

    # Send the test prompt
    print(f"[trace_runner] Sending: {TEST_PROMPT!r}")
    send_result = send_message(TARGET, SESSION, TEST_PROMPT)
    if not send_result.get("ok"):
        print(f"[trace_runner] ERROR: Send failed: {send_result}")
        sys.exit(1)
    print(f"[trace_runner] Send OK — waiting for completion (timeout={TIMEOUT_S}s)")

    def _read_trace_file() -> list[dict]:
        """Read events from the shared trace file (cross-process)."""
        try:
            with open(tracer.dump_file(), "r") as f:
                return [json.loads(line) for line in f if line.strip()]
        except FileNotFoundError:
            return []

    # Wait for watcher to detect completion OR timeout
    start = time.monotonic()
    while time.monotonic() - start < TIMEOUT_S:
        time.sleep(2.0)
        events = _read_trace_file()
        # Check if we have a terminal event
        stages = [e["stage"] for e in events]
        if "publisher_success" in stages or "publisher_failed" in stages:
            print(f"[trace_runner] Publisher terminal event detected")
            # Give a small buffer for any trailing events
            time.sleep(1.0)
            break
        if "watcher_classified_complete" in stages:
            # Complete detected but publisher hasn't fired yet — keep waiting
            elapsed = time.monotonic() - start
            if elapsed > 30:
                print(f"[trace_runner] Complete classified but no publisher event after {elapsed:.0f}s")
                break
        if "bridge_permission_auto_approved" in stages:
            # Permission was auto-approved — reset and keep waiting for the actual reply
            pass
        # Progress indicator
        elapsed = time.monotonic() - start
        if int(elapsed) % 10 == 0 and int(elapsed) > 0:
            print(f"[trace_runner] ... {elapsed:.0f}s elapsed, {len(events)} events so far")

    # Dump the full ordered trace (from file, not in-memory — events come from container)
    events = _read_trace_file()
    print()
    print("=" * 80)
    print("FULL PIPELINE TRACE")
    print("=" * 80)
    for i, evt in enumerate(events):
        print(f"[{i:3d}] {json.dumps(evt)}")

    print()
    print("=" * 80)
    print("STAGE SEQUENCE")
    print("=" * 80)
    for i, evt in enumerate(events):
        ts = evt.get("ts", "")
        stage = evt.get("stage", "")
        session = evt.get("session", "")
        cls = evt.get("classification", "")
        reason = evt.get("reason", "")
        input_len = evt.get("input_length", 0)
        print(f"  [{i:3d}] {ts}  {stage:<40s}  cls={cls:<12s}  len={input_len:>6d}  reason={reason}")

    # Identify first missing transition
    print()
    print("=" * 80)
    print("PIPELINE BOUNDARY ANALYSIS")
    print("=" * 80)

    stages = [e["stage"] for e in events]

    # Expected happy-path sequence for a COMPLETE cycle:
    expected_chain = [
        ("watcher_cycle_reset", "Watcher armed for new cycle"),
        ("watcher_responding", "Watcher detected CC started responding"),
        ("watcher_working", "Watcher detected tool activity (optional)"),
        ("watcher_candidate_detected", "Watcher found COMPLETE candidate"),
        ("watcher_stabilization_confirmed", "Stabilization window passed"),
        ("watcher_classified_complete", "Reply classified as COMPLETE"),
        ("watcher_emitted_event", "Watcher emitted event via callback"),
        ("bridge_received_event", "Bridge received the WatcherEvent"),
        ("bridge_scheduled", "Bridge scheduled async processing"),
        ("publisher_attempt", "Publisher attempting Discord send"),
        ("publisher_success", "Publisher confirmed delivery"),
    ]

    # Also check permission path
    permission_chain = [
        ("watcher_classified_permission", "Reply classified as PERMISSION"),
        ("watcher_emitted_event", "Watcher emitted permission event"),
        ("bridge_received_event", "Bridge received permission event"),
        ("bridge_permission_auto_approved", "Bridge auto-approved permission"),
    ]

    last_seen = None
    for stage_name, description in expected_chain:
        if stage_name in stages:
            last_seen = stage_name
            print(f"  [OK]     {stage_name:<40s}  {description}")
        elif stage_name == "watcher_working":
            # Optional — tool activity doesn't always happen
            print(f"  [SKIP]   {stage_name:<40s}  {description} (optional)")
        else:
            print(f"  [MISS]   {stage_name:<40s}  {description}")
            print()
            print(f'  First missing transition: "{stage_name}"')
            print(f'  Last successful stage:    "{last_seen}"')
            print()
            if last_seen:
                print(f"  The break is between:")
                print(f"    {last_seen} (succeeded)")
                print(f"    {stage_name} (never fired)")
            break
    else:
        print()
        print("  FULL PIPELINE INTACT — all stages fired in order")

    # Show any permission events
    perm_events = [e for e in events if "permission" in e.get("stage", "")]
    if perm_events:
        print()
        print("  Permission events detected:")
        for e in perm_events:
            print(f"    {e['ts']}  {e['stage']}  reason={e.get('reason', '')}")

    print()
    print(f"Total events: {len(events)}")
    print(f"Elapsed time: {time.monotonic() - start:.1f}s")
    print(f"Trace file: {tracer.dump_file()}")


if __name__ == "__main__":
    main()
