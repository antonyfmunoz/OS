"""
End-to-end Builder delivery test.

Injects a synthetic COMPLETE WatcherEvent into the SessionDiscordBridge,
exercising the full path: format_event → _send_chunked_reply → Discord.

Run inside the os-discord container where the bot loop is active:
  docker exec os-discord python3 /opt/OS/scripts/test_builder_delivery.py

Or from host (will use bridge.on_watcher_event which schedules onto bot loop):
  python3 /opt/OS/scripts/test_builder_delivery.py
"""

import sys
import time

sys.path.insert(0, "/opt/OS")

from umh.substrate.session_watcher import SessionState, WatcherEvent
from umh.substrate.session_discord_bridge import get_bridge

TEST_REPLY = """# EOS Builder Delivery Validation

## System Health
- **Discord Bot**: Running (os-discord container)
- **Monitor Service**: Active, polling every 60s
- **Webhook Receiver**: Listening on port 8080
- **Bot Service**: Operational

## Intelligence Layer
- Model Router: Gemini 2.5 Flash (primary), Ollama gemma3:4b (fallback)
- Cognitive Loop: 8-stage pipeline verified
- Agent Runtime: Multi-model dispatch active

## Current Priorities
1. **Initiate Arena outreach** — first revenue target
2. **Personal brand content** — marketing vehicle
3. **OS infrastructure** — AI backbone for operations

## Metrics
- Venture count: 2 active (Lyfe Institute, Empyrean Studio)
- Active agents: 4 registered
- Skills indexed: 154 cached embeddings
- Proactive signals: 1 pending action

## Next Actions
- Review proactive signal: paid advertising primitive check
- Refresh GWS calendar auth (token expired)
- Monitor Groq rate limit reset (2h window)

---
*Builder delivery validation — synthetic test event*
"""


def main() -> None:
    print(f"[TEST] Content length: {len(TEST_REPLY)} chars")
    print(f"[TEST] Has headers: {'#' in TEST_REPLY}")
    print(f"[TEST] Has bullets: {'-' in TEST_REPLY}")
    print(f"[TEST] Multi-section: {TEST_REPLY.count('##') >= 3}")

    # Create synthetic WatcherEvent as if Builder session completed a reply
    event = WatcherEvent(
        session_name="dex_builder_main",
        state=SessionState.COMPLETE,
        text=TEST_REPLY,
        role="builder",
        timestamp=time.time(),
    )

    bridge = get_bridge()
    has_bot = bridge._bot is not None
    has_loop = bridge._loop is not None

    print(f"[TEST] Bridge has bot: {has_bot}")
    print(f"[TEST] Bridge has loop: {has_loop}")

    if not has_bot or not has_loop:
        print("[TEST] FAIL — bridge not connected to Discord bot")
        print("[TEST] This script must run when os-discord is active")
        sys.exit(1)

    # Fire the event through the bridge
    print("[TEST] Injecting synthetic COMPLETE event into bridge...")
    bridge.on_watcher_event(event)

    # The event is processed async on the bot loop.
    # Give it time to send.
    print("[TEST] Event dispatched — checking relay log in 3s...")
    time.sleep(3)

    # Check relay log for this event
    import json

    relay_log_path = "/opt/OS/logs/discord_relay.log"
    try:
        with open(relay_log_path, "r") as f:
            lines = f.readlines()
        # Find recent entries
        recent = [json.loads(l) for l in lines[-20:] if l.strip()]
        builder_events = [
            e
            for e in recent
            if e.get("source_session") == "dex_builder_main"
            and e.get("ts", "").startswith(time.strftime("%Y-%m-%d"))
        ]
        print(f"\n[TEST] Recent builder relay events: {len(builder_events)}")
        for e in builder_events:
            stage = e.get("delivery_stage", "?")
            clen = e.get("content_len", 0)
            err = e.get("error", "")
            print(f"  stage={stage} content_len={clen} error={err or 'none'}")

        # Check for completion
        completed = [e for e in builder_events if e.get("delivery_stage") == "completed"]
        sent = [e for e in builder_events if e.get("delivery_stage") == "sent"]
        failed = [e for e in builder_events if "fail" in e.get("delivery_stage", "")]

        if completed or sent:
            print("\n[TEST] PASS — delivery reached Discord")
        elif failed:
            print(f"\n[TEST] FAIL — delivery failed: {failed[0].get('error', '?')}")
        else:
            print("\n[TEST] PENDING — no completion/failure yet (may still be processing)")
    except FileNotFoundError:
        print("[TEST] No relay log found — first run?")
    except Exception as ex:
        print(f"[TEST] Error reading relay log: {ex}")


if __name__ == "__main__":
    main()
