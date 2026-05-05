---
type: codebase-class
file: eos_ai/substrate/session_watcher.py
line: 118
generated: 2026-04-12
---

# SessionWatcher

**File:** [[eos_ai-substrate-session_watcher-py]] | **Line:** 118

Continuous state machine monitor for a single CC tmux session.

Usage:
    watcher = SessionWatcher("vps", "dex_builder_main", on_event=my_callback)
    watcher.start()  # daemon thread, non-blocking
...

## Methods

- [[eos_ai-substrate-session_watcher-py-SessionWatcher-__init__]]`(target, session_name) → None` — 
- [[eos_ai-substrate-session_watcher-py-SessionWatcher-state]]`() → SessionState` — 
- [[eos_ai-substrate-session_watcher-py-SessionWatcher-is_running]]`() → bool` — 
- [[eos_ai-substrate-session_watcher-py-SessionWatcher-start]]`() → None` — Start the watcher daemon thread.
- [[eos_ai-substrate-session_watcher-py-SessionWatcher-stop]]`() → None` — Signal the watcher to stop.
- [[eos_ai-substrate-session_watcher-py-SessionWatcher-send_response]]`(text) → dict[str, Any]` — Pipe a response back into the tmux session.
- [[eos_ai-substrate-session_watcher-py-SessionWatcher-wait_for_reply]]`(timeout) → str` — Block until the watcher detects a complete reply.
- [[eos_ai-substrate-session_watcher-py-SessionWatcher-_run_loop]]`() → None` — Main polling loop — runs in daemon thread.
- [[eos_ai-substrate-session_watcher-py-SessionWatcher-_poll_once]]`() → None` — Single poll cycle: capture output, detect state, emit events.
- [[eos_ai-substrate-session_watcher-py-SessionWatcher-_classify_reply]]`(text) → SessionState` — Classify what kind of reply CC produced.
- [[eos_ai-substrate-session_watcher-py-SessionWatcher-_extract_latest_reply]]`(clean_output) → str` — Extract the latest CC reply from clean tmux output.
- [[eos_ai-substrate-session_watcher-py-SessionWatcher-_emit]]`(event) → None` — Emit event via callback (if registered).
