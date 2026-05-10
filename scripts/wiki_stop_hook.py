#!/usr/bin/env python3
"""
Stop hook: capture real conversation content to session file.

Creates the session file lazily on first real content write.
Only writes if there is meaningful assistant text to capture.
Preserves idempotency via timestamp dedup check.

Stop hook payload fields used:
  - session_id: unique session identifier
  - stop_reason: why Claude stopped (end_turn, tool_use, etc.)
  - transcript_path: path to JSONL transcript file
  - last_assistant_message: the assistant's response text

Input (stdin JSON): stop hook payload
Output: exits 0 always (never blocks stopping).
"""
import sys
import os
import json
from datetime import datetime, timezone
from typing import Any
_ROOT = os.environ.get("UMH_ROOT") or os.environ.get("OS_ROOT") or os.environ.get("EOS_ROOT") or "/opt/OS"



CONVERSATIONS_DIR = f'{_ROOT}/vault/memory/conversations'
# Skip writing if assistant text is shorter than this
MIN_CONTENT_LENGTH = 20


def _read_payload() -> dict[str, Any]:
    """Read and parse the hook payload from stdin."""
    try:
        return json.load(sys.stdin)
    except Exception:
        return {}


def _extract_assistant_text(hook_input: dict[str, Any]) -> str:
    """Extract the last assistant message from the hook payload.

    The Stop hook provides 'last_assistant_message' which contains
    the assistant's response text. Falls back to empty string if unavailable.
    """
    text = hook_input.get('last_assistant_message', '')
    if isinstance(text, str):
        return text.strip()
    return ''


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


def _build_entry(
    iso_ts: str,
    stop_reason: str,
    assistant_text: str,
    has_user_entry: bool = False,
) -> str:
    """Build a turn block entry for the conversation file.

    If has_user_entry is True, the user's prompt was already written by the
    UserPromptSubmit hook, so we only append the assistant section without
    a new timestamp header.
    """
    reason_suffix = f' ({stop_reason})' if stop_reason else ''
    # Truncate very long messages to keep files manageable
    display_text = assistant_text[:2000]
    if len(assistant_text) > 2000:
        display_text += '\n\n[...truncated]'

    if has_user_entry:
        # Append directly after the user's entry (no new ## header)
        return f"""### Assistant{reason_suffix}
{display_text}

---

"""
    else:
        # Standalone assistant entry (no user prompt captured)
        return f"""## {iso_ts}{reason_suffix}

### Assistant
{display_text}

---

"""


def main() -> None:
    hook_input = _read_payload()

    session_id = hook_input.get('session_id', 'unknown')
    stop_reason = hook_input.get('stop_reason', '')
    cwd = hook_input.get('cwd', _ROOT)
    transcript_path = hook_input.get('transcript_path', '')

    assistant_text = _extract_assistant_text(hook_input)

    # Only write if there is meaningful content
    if len(assistant_text) < MIN_CONTENT_LENGTH:
        sys.exit(0)

    now = datetime.now(timezone.utc).astimezone()
    iso_ts = now.isoformat(timespec='seconds')

    filepath = os.path.join(CONVERSATIONS_DIR, f'{session_id}.md')
    os.makedirs(CONVERSATIONS_DIR, exist_ok=True)

    # Lazy create: build file with header on first real content
    if not os.path.exists(filepath):
        started_at = iso_ts  # best available approximation
        header = _build_header(session_id, cwd, started_at)
        with open(filepath, 'w') as f:
            f.write(header)

    # Read existing content for idempotency and user-entry detection
    existing = ''
    try:
        with open(filepath, 'r') as f:
            existing = f.read()
    except Exception:
        pass

    # Idempotency: check if this exact assistant response already logged
    # Use a snippet of the assistant text as marker (more reliable than timestamp)
    snippet = assistant_text[:80].strip()
    if snippet and f'### Assistant' in existing and snippet in existing:
        sys.exit(0)

    # Detect if the UserPromptSubmit hook already wrote a user entry
    # that doesn't yet have a paired assistant response.
    # Pattern: file ends with "### User\n...\n\n" (no "### Assistant" after it)
    has_user_entry = False
    if '### User' in existing:
        last_user_pos = existing.rfind('### User')
        last_assistant_pos = existing.rfind('### Assistant')
        # User entry exists after the last assistant entry = unpaired
        if last_user_pos > last_assistant_pos:
            has_user_entry = True

    entry = _build_entry(iso_ts, stop_reason, assistant_text, has_user_entry)

    with open(filepath, 'a') as f:
        f.write(entry)

    sys.exit(0)


if __name__ == '__main__':
    main()
