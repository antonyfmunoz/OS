"""Authority tier constants and validation for ingestion sources.

Tier scale: 1 (highest, canonical) to 9 (lowest, archive/scratch).
Each source declares its tier. Tier flows unchanged through all
pipeline stages — no stage modifies it.
"""

from __future__ import annotations

T1_CANONICAL = 1
T2_ACTIVE = 2
T3_REFERENCE = 3
T4_SUPPORTING = 4
T5_DEFAULT = 5
T6_LEGACY = 6
T7_ARCHIVED = 7
T8_SCRATCH = 8
T9_OLD_CHATS = 9

VALID_TIERS = range(1, 10)

_TIER_NAMES: dict[int, str] = {
    T1_CANONICAL: "canonical",
    T2_ACTIVE: "active",
    T3_REFERENCE: "reference",
    T4_SUPPORTING: "supporting",
    T5_DEFAULT: "default",
    T6_LEGACY: "legacy",
    T7_ARCHIVED: "archived",
    T8_SCRATCH: "scratch",
    T9_OLD_CHATS: "old_chats",
}


def validate_tier(tier: int) -> int:
    """Validate and return tier. Raises ValueError if invalid."""
    if tier not in VALID_TIERS:
        raise ValueError(f"authority_tier must be 1-9, got {tier}")
    return tier


def tier_name(tier: int) -> str:
    """Human-readable label for a tier."""
    return _TIER_NAMES.get(tier, f"tier_{tier}")


def get_authority_tier(entry: dict) -> int:
    """Read authority_tier from a memory entry, defaulting to T5_DEFAULT."""
    return entry.get("authority_tier", T5_DEFAULT)
