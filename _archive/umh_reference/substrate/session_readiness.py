"""Stub for session readiness tracking.

Placeholder implementation that satisfies the import from
webhooks/cc_receiver.py. Logs and returns without side effects.

Replace with full implementation when session readiness
state machine is built.
"""

from __future__ import annotations

import sys

_LOG_PREFIX = "[substrate.session_readiness:stub]"


def _log(msg: str) -> None:
    print(f"{_LOG_PREFIX} {msg}", file=sys.stderr)


def record_publication_complete(session_name: str) -> None:
    """Record that a session's publication was delivered.

    Stub: logs the call and returns. Full implementation will
    update session readiness state to reflect completed delivery.
    """
    _log(f"record_publication_complete called: session={session_name}")
