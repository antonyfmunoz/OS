"""Google Workspace Future Service Package Candidates.

Services that are part of the Google Workspace suite but are NOT
declared for W0-001. They do not block W0-001 and will require
their own Adapter Packages and Tool Mastery Packs when declared.

UMH substrate subsystem. EOS is one platform consumer.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class FutureServiceCandidate:
    service_name: str
    candidate_package_id: str
    family_id: str = "google_workspace"
    declared_for_w0_001: bool = False
    blocks_w0_001: bool = False
    target_maturity_when_declared: float = 100.0
    requires_own_adapter_package: bool = True
    requires_own_tool_mastery_pack: bool = True
    notes: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "service_name": self.service_name,
            "candidate_package_id": self.candidate_package_id,
            "family_id": self.family_id,
            "declared_for_w0_001": self.declared_for_w0_001,
            "blocks_w0_001": self.blocks_w0_001,
            "target_maturity_when_declared": self.target_maturity_when_declared,
            "requires_own_adapter_package": self.requires_own_adapter_package,
            "requires_own_tool_mastery_pack": self.requires_own_tool_mastery_pack,
            "notes": self.notes,
        }


_FUTURE_CANDIDATES = [
    FutureServiceCandidate(
        service_name="Gmail",
        candidate_package_id="W-GMAIL-001",
    ),
    FutureServiceCandidate(
        service_name="Google Sheets",
        candidate_package_id="W-GSHEETS-001",
    ),
    FutureServiceCandidate(
        service_name="Google Slides",
        candidate_package_id="W-GSLIDES-001",
    ),
    FutureServiceCandidate(
        service_name="Google Calendar",
        candidate_package_id="W-GCALENDAR-001",
    ),
    FutureServiceCandidate(
        service_name="Google Forms",
        candidate_package_id="W-GFORMS-001",
    ),
    FutureServiceCandidate(
        service_name="Google Meet",
        candidate_package_id="W-GMEET-001",
    ),
    FutureServiceCandidate(
        service_name="Google Admin / Workspace Identity",
        candidate_package_id="W-GADMIN-001",
    ),
]


def build_google_workspace_future_service_candidates() -> (
    list[FutureServiceCandidate]
):
    return list(_FUTURE_CANDIDATES)


def candidate_is_declared_for_w0_001(
    candidate: FutureServiceCandidate,
) -> bool:
    return candidate.declared_for_w0_001


def candidate_blocks_w0_001(candidate: FutureServiceCandidate) -> bool:
    return candidate.blocks_w0_001


def no_candidate_blocks_w0_001(
    candidates: list[FutureServiceCandidate],
) -> bool:
    return not any(c.blocks_w0_001 for c in candidates)


def all_candidates_require_own_package(
    candidates: list[FutureServiceCandidate],
) -> bool:
    return all(c.requires_own_adapter_package for c in candidates)
