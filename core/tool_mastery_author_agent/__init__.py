"""Tool Mastery Author Agent.

Consumes a source-grounded research_artifact.json produced by the
Tool Mastery Research Agent and drafts or refreshes tool skill files
in a truthful, verifier-aware, traceable way.

Core invariant: the Author Agent never fabricates depth. Every
authored claim is traceable to a specific raw capture on disk, or
it is honestly marked as uncovered.

Public entry point:
    from core.tool_mastery_author_agent.agent import author
"""

from .agent import author  # noqa: F401
from .models import (  # noqa: F401
    AuthorRequest,
    AuthorResult,
    AuthorStatus,
    SectionDraft,
)
