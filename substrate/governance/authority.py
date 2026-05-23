"""Authority levels — what the system can do without human intervention."""

from __future__ import annotations

from enum import IntEnum


class AuthorityLevel(IntEnum):
    """Authority required to proceed with an action.

    Ordered from most autonomous (0) to most restricted (4).
    Higher values require more human involvement.
    """

    AUTONOMOUS = 0
    NOTIFY = 1
    APPROVE = 2
    ESCALATE = 3
    DENY = 4

    @property
    def requires_human(self) -> bool:
        return self >= AuthorityLevel.APPROVE

    @property
    def is_blocked(self) -> bool:
        return self == AuthorityLevel.DENY
