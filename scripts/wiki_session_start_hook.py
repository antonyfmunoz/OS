#!/usr/bin/env python3
"""
SessionStart hook: no-op.

Previously created per-session stub files in vault/memory/conversations/.
This produced hundreds of empty placeholder files with no content value.

The Stop hook now handles lazy file creation on first real content write.
SessionStart no longer creates anything.

Input (stdin JSON): session_id, cwd, etc.
Output: exits 0 always.
"""
import sys


def main() -> None:
    sys.exit(0)


if __name__ == '__main__':
    main()
