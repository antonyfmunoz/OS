#!/usr/bin/env python3
"""
UserPromptSubmit hook: capture user messages into conversation files.

Pairs with wiki_stop_hook.py which captures assistant responses.
Together they create a complete conversation log.

Hook payload fields used (CC 2.1.92):
  - session_id: unique session identifier
  - prompt: the user's prompt text

Input (stdin JSON): UserPromptSubmit hook payload
Output: exits 0 always (never blocks the prompt).
"""
import sys
import os
import json
from datetime import datetime, timezone
from typing import Any


CONVERSATIONS_DIR = "/opt/OS/data/vault/memory/conversations"
# Skip capturing very short prompts (single-word commands, etc.)
MIN_PROMPT_LENGTH = 5


def _read_payload() -> dict[str, Any]:
    """Read and parse the hook payload from stdin."""
    try:
        return json.load(sys.stdin)
    except Exception:
        return {}


def _build_header(session_id: str, cwd: str, started_at: str) -> str:
    """Build the markdown frontmatter header for a new session file."""
    return f"""---
type: conversation
session_id: {session_id}
started_at: {started_at}
cwd: {cwd}
---

# Session {session_id[:8]}

## Metadata
- Started: {started_at}
- CWD: {cwd}

"""


def main() -> None:
    hook_input = _read_payload()

    session_id = hook_input.get("session_id", "unknown")

    # CC 2.1.92: field name is "prompt" per official hooks docs
    user_text = hook_input.get("prompt", "")
    if not isinstance(user_text, str):
        user_text = str(user_text) if user_text else ""
    user_text = user_text.strip()

    # Skip trivial prompts
    if len(user_text) < MIN_PROMPT_LENGTH:
        sys.exit(0)

    now = datetime.now(timezone.utc).astimezone()
    iso_ts = now.isoformat(timespec="seconds")
    cwd = hook_input.get("cwd", "/opt/OS")

    filepath = os.path.join(CONVERSATIONS_DIR, f"{session_id}.md")
    os.makedirs(CONVERSATIONS_DIR, exist_ok=True)

    # Create file with header if it doesn't exist yet
    if not os.path.exists(filepath):
        header = _build_header(session_id, cwd, iso_ts)
        with open(filepath, "w") as f:
            f.write(header)

    # Idempotency: check if we already captured a user message at this second
    # Use a unique marker that won't collide with assistant entries
    entry_marker = f"### User\n{user_text[:80]}"
    try:
        with open(filepath, "r") as f:
            existing = f.read()
        if entry_marker in existing:
            sys.exit(0)
    except Exception:
        pass

    # Truncate very long prompts to keep files manageable
    display_text = user_text[:2000]
    if len(user_text) > 2000:
        display_text += "\n\n[...truncated]"

    entry = f"""## {iso_ts}

### User
{display_text}

"""

    with open(filepath, "a") as f:
        f.write(entry)

    sys.exit(0)


if __name__ == "__main__":
    main()
