"""Tool Mastery Research Agent.

Consumes queued `tool_mastery:research` actions from the Control Plane
and produces source-grounded research artifacts that downstream
authoring (manual or CC-session) can consume to fill SKILL.md +
references/best_practices.md.

Honest boundaries:
    - This package DOES plan sources, fetch primary docs, and produce
      a structured research artifact with provenance.
    - This package does NOT fabricate `best_practices.md` content, does
      NOT declare a tool "mastered", and does NOT sync to Neon.
    - Safe metadata updates to existing SKILL.md frontmatter (source_url,
      last_researched) are the only auto-writes.
"""

from __future__ import annotations

from .models import (
    FetchStatus,
    FetchedSource,
    ResearchArtifact,
    ResearchMode,
    ResearchRequest,
    ResearchResult,
    ResearchStatus,
    SourcePlan,
    SourceRef,
    SourceTier,
)

__all__ = [
    "FetchStatus",
    "FetchedSource",
    "ResearchArtifact",
    "ResearchMode",
    "ResearchRequest",
    "ResearchResult",
    "ResearchStatus",
    "SourcePlan",
    "SourceRef",
    "SourceTier",
]
