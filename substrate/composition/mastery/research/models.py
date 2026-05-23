"""Data types for the Tool Mastery Research Agent.

Everything here is JSON-serialisable (str/int/float/bool/list/dict) via
dataclasses.asdict() so that research runs can be persisted to disk
without custom encoders, matching the Manager convention.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from enum import Enum
from typing import Any


class ResearchMode(str, Enum):
    """What the research agent is being asked to do."""

    RESEARCH = "research"  # brand new tool, no skill yet (MISSING)
    REFRESH = "refresh"  # skill exists but stale
    REPAIR = "repair"  # skill exists but verifier fails


class ResearchStatus(str, Enum):
    """Terminal status for a single research run."""

    OK = "ok"  # artifact produced, sources fetched
    NO_SOURCES = "no_sources"  # discovery returned nothing
    FETCH_FAILED = "fetch_failed"  # all sources failed to fetch
    PARTIAL = "partial"  # some sources ok, some failed
    ERROR = "error"  # unexpected failure


class SourceTier(str, Enum):
    """Trust tier for a source. Primary sources are preferred."""

    OFFICIAL_DOCS = "official_docs"  # tier 1: vendor docs site
    OFFICIAL_API_REF = "official_api_ref"  # tier 1: API reference
    OFFICIAL_REPO = "official_repo"  # tier 1: canonical GitHub
    OFFICIAL_PACKAGE = "official_package"  # tier 1: npm/pypi page
    MCP_MANIFEST = "mcp_manifest"  # tier 1 for MCP tools
    SECONDARY = "secondary"  # tier 2: tutorials, blogs (last resort)


class FetchStatus(str, Enum):
    """Result of fetching a single source."""

    OK = "ok"
    HTTP_ERROR = "http_error"
    TIMEOUT = "timeout"
    NETWORK_ERROR = "network_error"
    UNSUPPORTED_SCHEME = "unsupported_scheme"
    SKIPPED = "skipped"


@dataclass
class ResearchRequest:
    """Input to a research run."""

    tool_slug: str
    mode: ResearchMode = ResearchMode.RESEARCH
    action_id: str | None = None  # Control Plane provenance
    source_hints: list[str] = field(default_factory=list)  # explicit URLs
    official_url: str | None = None
    source_agent: str = "tool_mastery_research_agent"

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d["mode"] = self.mode.value
        return d


@dataclass
class SourceRef:
    """A candidate source identified during discovery."""

    url: str
    tier: SourceTier
    label: str = ""
    origin: str = (
        ""  # where this ref came from (registry | claude_json | hint | derived)
    )

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d["tier"] = self.tier.value
        return d


@dataclass
class SourcePlan:
    """Output of source discovery for a single tool."""

    tool_slug: str
    sources: list[SourceRef] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)

    @property
    def is_empty(self) -> bool:
        return not self.sources

    def to_dict(self) -> dict[str, Any]:
        return {
            "tool_slug": self.tool_slug,
            "sources": [s.to_dict() for s in self.sources],
            "notes": list(self.notes),
        }


@dataclass
class FetchedSource:
    """Result of fetching a single SourceRef."""

    ref: SourceRef
    status: FetchStatus
    http_status: int | None = None
    content_type: str | None = None
    bytes: int = 0
    raw_path: str | None = None  # relative path under run dir
    error: str | None = None
    fetched_at: str = ""  # ISO8601 UTC

    def to_dict(self) -> dict[str, Any]:
        return {
            "ref": self.ref.to_dict(),
            "status": self.status.value,
            "http_status": self.http_status,
            "content_type": self.content_type,
            "bytes": self.bytes,
            "raw_path": self.raw_path,
            "error": self.error,
            "fetched_at": self.fetched_at,
        }


@dataclass
class ResearchArtifact:
    """Structured research output for one tool.

    This is the primary hand-off to authoring. It does NOT contain
    synthesised best-practices prose — only the raw, source-backed
    material that a later authoring pass can quote from.
    """

    tool_slug: str
    mode: ResearchMode
    generated_at: str
    sources: list[FetchedSource] = field(default_factory=list)
    # Self-reported coverage against the TME 19-section protocol.
    # Each entry: {"section": str, "has_source": bool, "source_urls": [..]}
    section_coverage: list[dict[str, Any]] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)
    # Run-level quality flag: "high" | "mixed" | "low"
    quality: str = "low"
    # Per-source signal reports (pre-author-agent prose density check).
    signal_reports: list[dict[str, Any]] = field(default_factory=list)
    # Phase 5 — per-source content classification reports.
    # Each entry is a SourceTypeReport.to_dict().
    source_type_reports: list[dict[str, Any]] = field(default_factory=list)
    # Phase 5 — structured patterns extracted from OK, classified sources.
    # Shape: {"usage": [...], "api": [...], "workflows": [...]}.
    # Each pattern dict carries kind, excerpt, url, confidence, occurrences,
    # and structured flags so the Author Agent can route by kind.
    extracted_patterns: dict[str, list[dict[str, Any]]] = field(
        default_factory=lambda: {"usage": [], "api": [], "workflows": []}
    )

    def to_dict(self) -> dict[str, Any]:
        return {
            "tool_slug": self.tool_slug,
            "mode": self.mode.value,
            "generated_at": self.generated_at,
            "sources": [s.to_dict() for s in self.sources],
            "section_coverage": list(self.section_coverage),
            "notes": list(self.notes),
            "quality": self.quality,
            "signal_reports": list(self.signal_reports),
            "source_type_reports": list(self.source_type_reports),
            "extracted_patterns": {
                "usage": list(self.extracted_patterns.get("usage", [])),
                "api": list(self.extracted_patterns.get("api", [])),
                "workflows": list(self.extracted_patterns.get("workflows", [])),
            },
        }


@dataclass
class ResearchResult:
    """Terminal result of a full research run."""

    request: ResearchRequest
    status: ResearchStatus
    run_dir: str
    artifact_path: str | None = None
    summary_path: str | None = None
    sources_path: str | None = None
    next_steps: list[str] = field(default_factory=list)
    error: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "request": self.request.to_dict(),
            "status": self.status.value,
            "run_dir": self.run_dir,
            "artifact_path": self.artifact_path,
            "summary_path": self.summary_path,
            "sources_path": self.sources_path,
            "next_steps": list(self.next_steps),
            "error": self.error,
        }
