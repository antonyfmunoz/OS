"""Data types for the Tool Mastery Author Agent.

All JSON-serialisable via asdict() so runs can be persisted alongside
the research run directory.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from enum import Enum
from typing import Any


class AuthorStatus(str, Enum):
    """Terminal status for an authoring run.

    The four states the orchestration layer must distinguish. Nothing
    else is valid.
    """

    AUTHORED_READY = "authored_ready"
    """Authoring succeeded AND verifier passes."""

    AUTHORED_PARTIAL = "authored_partial"
    """Authoring produced real improvements but not all sections are
    covered. Verifier may still pass (because structure is satisfied)
    but honest placeholders remain in one or more sections."""

    BLOCKED_NO_SOURCES = "blocked_no_sources"
    """Research artifact had zero successful fetches. Nothing the
    Author Agent can do — this is a research-layer problem."""

    VERIFY_FAILED = "verify_failed"
    """Authoring wrote content but the final verifier run failed.
    This is a hard stop — the tool is NOT ready."""


@dataclass
class AuthorRequest:
    """Input to an authoring run."""

    tool_slug: str
    artifact_path: str  # absolute path to research_artifact.json
    mode: str = "author"  # author | refresh | repair (informational only)
    allow_scaffold: bool = True
    force_rewrite: bool = False
    source_agent: str = "tool_mastery_author_agent"

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class SectionDraft:
    """One authored section.

    ``content`` is the literal markdown to write under the section
    heading. ``source_urls`` are the raw-capture URLs the content was
    extracted from. ``sourced`` distinguishes real evidence-backed
    content from an honest placeholder.
    """

    section: str  # section heading text (without ## prefix)
    content: str
    sourced: bool
    source_urls: list[str] = field(default_factory=list)
    raw_paths: list[str] = field(default_factory=list)
    rationale: str = ""  # why this section looks the way it does
    # Phase 6 — how this draft was grounded. One of:
    #   "pattern"   — rendered from ≥1 structured pattern
    #   "prose"     — rendered from raw-capture keyword excerpts
    #   "uncovered" — honest placeholder
    #   "mixed"     — both patterns and prose contributed
    grounding: str = "uncovered"
    pattern_count: int = 0

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class AuthoredProvenance:
    """Sidecar written next to research_artifact.json.

    Maps every drafted section to the raw captures that back it.
    This is the audit trail — keep it honest, keep it complete.
    """

    tool_slug: str
    authored_at: str
    run_dir: str
    drafts: list[SectionDraft] = field(default_factory=list)
    # Sections that were deliberately NOT touched because an existing
    # human-authored skill was stronger than anything the agent could
    # draft. Important for refresh runs against good skills.
    preserved_sections: list[str] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "tool_slug": self.tool_slug,
            "authored_at": self.authored_at,
            "run_dir": self.run_dir,
            "drafts": [d.to_dict() for d in self.drafts],
            "preserved_sections": list(self.preserved_sections),
            "notes": list(self.notes),
        }


@dataclass
class AuthorResult:
    """Terminal result of a full authoring run."""

    request: AuthorRequest
    status: AuthorStatus
    skill_path: str | None = None
    best_practices_path: str | None = None
    provenance_path: str | None = None
    sections_sourced: int = 0
    sections_placeholder: int = 0
    sections_preserved: int = 0
    verifier_passed: bool = False
    verifier_failures: list[str] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        d = {
            "request": self.request.to_dict(),
            "status": self.status.value,
            "skill_path": self.skill_path,
            "best_practices_path": self.best_practices_path,
            "provenance_path": self.provenance_path,
            "sections_sourced": self.sections_sourced,
            "sections_placeholder": self.sections_placeholder,
            "sections_preserved": self.sections_preserved,
            "verifier_passed": self.verifier_passed,
            "verifier_failures": list(self.verifier_failures),
            "notes": list(self.notes),
        }
        return d
