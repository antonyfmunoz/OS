"""Profile/work modes — operator activity context governing workspace/tool/task selection.

Profile mode is orthogonal to lifecycle mode. Multiple profile modes
can be active simultaneously (e.g., DEVELOPER + RESEARCH during a
spike). The primary profile mode drives workspace defaults.

Phase 14.11B. Substrate layer. Instance-agnostic.
"""

from __future__ import annotations

from enum import Enum


class ProfileMode(str, Enum):
    """Operator work/activity profile modes.

    DEVELOPER      — writing code, debugging, deploying
    RESEARCH       — investigation, reading, analysis
    MUSIC          — music production, composition
    DESIGN         — visual design, UI/UX work
    CONTENT        — content creation, writing, editing
    COMMAND_CENTER — executive overview, dashboards, approvals
    FINANCE        — financial review, accounting, projections
    LEARNING       — studying, courses, skill development
    """

    DEVELOPER = "developer"
    RESEARCH = "research"
    MUSIC = "music"
    DESIGN = "design"
    CONTENT = "content"
    COMMAND_CENTER = "command_center"
    FINANCE = "finance"
    LEARNING = "learning"
