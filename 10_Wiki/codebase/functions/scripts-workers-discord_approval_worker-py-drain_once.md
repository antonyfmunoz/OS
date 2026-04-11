---
type: codebase-function
file: scripts/workers/discord_approval_worker.py
line: 122
generated: 2026-04-11
---

# drain_once

**File:** [[scripts-workers-discord_approval_worker-py]] | **Line:** 122
**Signature:** `drain_once(webhook_url) → dict`

Process any un-notified entries in notifications.jsonl.

Returns a summary dict: {"read": N, "posted": N, "skipped": N, "failed": N}.

## Calls

- [[scripts-workers-discord_approval_worker-py-_format_discord_payload]]
- [[scripts-workers-discord_approval_worker-py-_is_still_deferred]]
- [[scripts-workers-discord_approval_worker-py-_log]]
- [[scripts-workers-discord_approval_worker-py-_post_to_discord]]
- [[scripts-workers-discord_approval_worker-py-_read_offset]]
- [[scripts-workers-discord_approval_worker-py-_write_offset]]

## Called By

- [[scripts-workers-discord_approval_worker-py-main]]
