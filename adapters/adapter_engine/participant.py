"""Participant type classification for UMH adapters.

Binary distinction: ECOSYSTEM participants (Trinity: EOS, LyfeOS, CreatorOS)
get full socket wiring. EXTERNAL adapters (Notion, Drive, GitHub, etc.) use
the general adapter pattern with canonical ingestion pipeline only.

Layer 3 Unified Architecture §2.2.
UMH substrate subsystem.
"""

from __future__ import annotations

from enum import Enum


class ParticipantType(str, Enum):
    """Whether an adapter is an ecosystem participant or external tool."""

    ECOSYSTEM = "ecosystem"
    EXTERNAL = "external"
