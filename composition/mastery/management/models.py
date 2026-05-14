"""Data types for the Tool Mastery Manager.

Kept deliberately small. Everything is JSON-serialisable so coverage
reports and ensure results can be written to disk as backlog artifacts
without custom encoders.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from enum import Enum
from typing import Any


class CoverageStatus(str, Enum):
    """Unified verdict for a single tool's mastery coverage.

    Ordering reflects repair priority — READY is the only terminal "good"
    state. All others represent work to be done.
    """

    READY = "ready"          # skill exists, passes verifier, not stale
    MISSING = "missing"      # no skill directory at all
    STALE = "stale"          # exists and valid but past freshness window
    INVALID = "invalid"      # exists but fails the verifier outright
    PARTIAL = "partial"      # exists, mostly valid, only soft gaps (warnings / near-stale)

    @property
    def needs_work(self) -> bool:
        return self is not CoverageStatus.READY


class DiscoverySource(str, Enum):
    """Where a tool reference came from. Used for provenance in reports."""

    SKILLS_DIR = "skills_dir"      # /opt/OS/skills/tools/
    EXPLICIT = "explicit"          # passed by caller / CLI
    SEED_LIST = "seed_list"        # config/tool_mastery_seeds.yaml
    CLAUDE_JSON = "claude_json"    # ~/.claude.json mcpServers


@dataclass
class ToolRef:
    """A normalised reference to a tool that is in scope for mastery."""

    slug: str                              # canonical snake_case slug
    display_name: str = ""                 # human-friendly label
    sources: list[DiscoverySource] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d["sources"] = [s.value for s in self.sources]
        return d


@dataclass
class CoverageReport:
    """Structured coverage verdict for a single tool."""

    slug: str
    status: CoverageStatus
    reasons: list[str] = field(default_factory=list)         # why it landed here
    verifier_failures: list[str] = field(default_factory=list)
    verifier_warnings: list[str] = field(default_factory=list)
    staleness_status: str | None = None                       # fresh|near_stale|stale|missing_date
    age_days: int | None = None
    last_researched: str | None = None
    speed_category: str | None = None
    exists_on_disk: bool = False

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d["status"] = self.status.value
        return d


@dataclass
class ManagerPlan:
    """Planned Control Plane action for a non-READY tool.

    The Manager never invokes action types outside the Control Plane's
    allowed set. Research / refresh / repair are encoded as medium-risk
    `run_script` actions targeting the research dispatcher, with the
    semantic work_type carried in inputs.
    """

    work_type: str              # "research" | "refresh" | "repair"
    tool_slug: str
    reason: str
    script_path: str            # the dispatcher script
    script_args: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class EnsureResult:
    """What happened when ensure_mastery() ran on a single tool."""

    slug: str
    final_status: CoverageStatus
    initial_status: CoverageStatus
    scaffolded: bool = False
    action_id: str | None = None         # Control Plane action id, if queued
    action_status: str | None = None     # executed|deferred|rejected|skipped_duplicate|None
    plan: ManagerPlan | None = None
    notes: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "slug": self.slug,
            "final_status": self.final_status.value,
            "initial_status": self.initial_status.value,
            "scaffolded": self.scaffolded,
            "action_id": self.action_id,
            "action_status": self.action_status,
            "plan": self.plan.to_dict() if self.plan else None,
            "notes": self.notes,
        }
