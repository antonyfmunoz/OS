"""
Memory scope contracts.

W0-001 data defaults to instance memory, not global UMH canon.
CanonicalSourceRecord means normalized schema, not universal truth.
No user-account source may be promoted to global canon without
explicit abstraction and founder approval.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class MemoryScope(str, Enum):
    GLOBAL_UMH_CANON = "global_umh_canon"
    INSTANCE_MEMORY = "instance_memory"
    PROJECT_MEMORY = "project_memory"
    PRODUCT_MEMORY = "product_memory"
    BRAND_MEMORY = "brand_memory"
    TEMPLATE_CANDIDATE = "template_candidate"
    ARCHIVE_ONLY = "archive_only"
    DO_NOT_PROMOTE = "do_not_promote"
    REQUIRES_FOUNDER_DECISION = "requires_founder_decision"


class PromotionPath(str, Enum):
    SOURCE_TO_INSTANCE_MEMORY = "source_to_instance_memory"
    INSTANCE_TO_PROJECT_MEMORY = "instance_to_project_memory"
    INSTANCE_TO_PRODUCT_MEMORY = "instance_to_product_memory"
    INSTANCE_TO_TEMPLATE_CANDIDATE = "instance_to_template_candidate"
    TEMPLATE_CANDIDATE_TO_GLOBAL_CANON = "template_candidate_to_global_canon"
    SOURCE_TO_ARCHIVE_ONLY = "source_to_archive_only"


def raw_account_data_default_scope() -> MemoryScope:
    """Raw account data defaults to INSTANCE_MEMORY, not global canon."""
    return MemoryScope.INSTANCE_MEMORY


def canonical_source_record_is_not_global_canon() -> bool:
    """CanonicalSourceRecord means normalized format, not universal truth."""
    return True


def can_promote_to_global_canon(
    current_scope: MemoryScope,
    abstracted: bool,
    founder_approved: bool,
) -> bool:
    """Global canon requires abstraction AND founder approval."""
    if current_scope == MemoryScope.DO_NOT_PROMOTE:
        return False
    return abstracted and founder_approved


def requires_abstraction_for_global(scope: MemoryScope) -> bool:
    """Instance facts cannot go directly to global canon."""
    return scope in (
        MemoryScope.INSTANCE_MEMORY,
        MemoryScope.PROJECT_MEMORY,
        MemoryScope.PRODUCT_MEMORY,
        MemoryScope.BRAND_MEMORY,
    )


@dataclass
class MemoryScopeAssignment:
    """Assigns a memory scope to a source or record."""

    source_id: str
    assigned_scope: MemoryScope = MemoryScope.INSTANCE_MEMORY
    global_canon_allowed_by_default: bool = False
    abstraction_applied: bool = False
    founder_approved: bool = False
    promotion_path: PromotionPath | None = None
    notes: str = ""

    def can_promote_to_global(self) -> bool:
        return can_promote_to_global_canon(
            self.assigned_scope,
            self.abstraction_applied,
            self.founder_approved,
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "source_id": self.source_id,
            "assigned_scope": self.assigned_scope.value,
            "global_canon_allowed_by_default": self.global_canon_allowed_by_default,
            "abstraction_applied": self.abstraction_applied,
            "founder_approved": self.founder_approved,
            "promotion_path": self.promotion_path.value if self.promotion_path else None,
            "notes": self.notes,
        }
