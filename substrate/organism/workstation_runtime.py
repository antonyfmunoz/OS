"""Workstation Runtime — canonical workstation planning layer (Phase 10).

Transforms UMH from an intelligent command system into a workstation
orchestration system.  This phase ONLY plans — it never launches
applications, opens browsers, or executes business work.

Composes: Presence (P8), Continuity (P7), Projection (P6), Tick Loop (P5),
Gap Engine (P4), Empire Router (P3), Command Runtime (P9).

Deterministic-first.  No LLM calls in any code path.
"""

from __future__ import annotations

import json
import logging
import os
import re
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any
from uuid import uuid4

logger = logging.getLogger(__name__)


def _repo_root() -> str:
    return os.environ.get("UMH_ROOT", "/opt/OS")


def _workstation_data_dir() -> str:
    return os.path.join(_repo_root(), "data", "umh", "workstation")


def _ensure_dirs() -> None:
    for sub in ("snapshots", "templates"):
        os.makedirs(os.path.join(_workstation_data_dir(), sub), exist_ok=True)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Canonical Types
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


class WorkstationMode(str, Enum):
    """What the operator is doing — drives template selection."""

    ENGINEERING = "engineering"
    CONTENT = "content"
    MUSIC = "music"
    BUSINESS = "business"
    RESEARCH = "research"
    ADMIN = "admin"


class WorkspaceStatus(str, Enum):
    """Lifecycle of a workspace preparation plan."""

    PLANNED = "planned"
    READY = "ready"
    ACTIVE = "active"
    SUSPENDED = "suspended"
    ARCHIVED = "archived"

    @property
    def is_terminal(self) -> bool:
        return self in (WorkspaceStatus.ARCHIVED,)


class PreparationStepType(str, Enum):
    """Categories of preparation actions."""

    APPLICATION = "application"
    REPOSITORY = "repository"
    BROWSER_TAB = "browser_tab"
    COCKPIT_PANEL = "cockpit_panel"
    WORK_PACKET = "work_packet"
    CONTEXT_SOURCE = "context_source"


class SnapshotTrigger(str, Enum):
    """What caused a snapshot to be taken."""

    MANUAL = "manual"
    PROFILE_SWITCH = "profile_switch"
    SESSION_END = "session_end"
    SCHEDULED = "scheduled"
    PREPARATION = "preparation"


class RecommendationType(str, Enum):
    """Categories of workstation recommendations."""

    RESUME_WORK = "resume_work"
    REVIEW_BLOCKED = "review_blocked"
    APPROVE_PROPOSAL = "approve_proposal"
    INVESTIGATE_RISK = "investigate_risk"
    CONTINUE_DRAFT = "continue_draft"
    ADDRESS_GAP = "address_gap"
    FOLLOW_UP = "follow_up"


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Data Models
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


@dataclass
class WorkspaceTemplate:
    """Data-driven workspace template — loaded from JSON, never hardcoded."""

    template_id: str = ""
    mode: str = ""
    label: str = ""
    required_applications: list[str] = field(default_factory=list)
    required_repositories: list[str] = field(default_factory=list)
    recommended_cockpit_panels: list[str] = field(default_factory=list)
    recommended_browser_tabs: list[str] = field(default_factory=list)
    required_context_sources: list[str] = field(default_factory=list)
    description: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "template_id": self.template_id,
            "mode": self.mode,
            "label": self.label,
            "required_applications": self.required_applications,
            "required_repositories": self.required_repositories,
            "recommended_cockpit_panels": self.recommended_cockpit_panels,
            "recommended_browser_tabs": self.recommended_browser_tabs,
            "required_context_sources": self.required_context_sources,
            "description": self.description,
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> WorkspaceTemplate:
        return cls(**{k: v for k, v in d.items() if k in cls.__dataclass_fields__})


@dataclass
class PreparationStep:
    """One step in a workspace preparation plan."""

    step_type: str = ""
    target: str = ""
    reason: str = ""
    priority: int = 0
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "step_type": self.step_type,
            "target": self.target,
            "reason": self.reason,
            "priority": self.priority,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> PreparationStep:
        return cls(**{k: v for k, v in d.items() if k in cls.__dataclass_fields__})


@dataclass
class WorkspacePreparationPlan:
    """Complete plan for preparing a workspace — never executes, only plans."""

    plan_id: str = ""
    mode: str = ""
    template_id: str = ""
    profile_mode: str = ""
    intent: str = ""
    steps: list[PreparationStep] = field(default_factory=list)
    context_summary: dict[str, Any] = field(default_factory=dict)
    active_work_packets: list[dict[str, Any]] = field(default_factory=list)
    continuity_context: dict[str, Any] = field(default_factory=dict)
    projection_context: dict[str, Any] = field(default_factory=dict)
    recommendations: list[dict[str, Any]] = field(default_factory=list)
    status: str = WorkspaceStatus.PLANNED.value
    created_at: float = 0.0
    operator_id: str = ""

    def __post_init__(self) -> None:
        if not self.plan_id:
            self.plan_id = f"wsp-{uuid4().hex[:12]}"
        if not self.created_at:
            self.created_at = time.time()

    def to_dict(self) -> dict[str, Any]:
        return {
            "plan_id": self.plan_id,
            "mode": self.mode,
            "template_id": self.template_id,
            "profile_mode": self.profile_mode,
            "intent": self.intent,
            "steps": [s.to_dict() for s in self.steps],
            "context_summary": self.context_summary,
            "active_work_packets": self.active_work_packets,
            "continuity_context": self.continuity_context,
            "projection_context": self.projection_context,
            "recommendations": [r for r in self.recommendations],
            "status": self.status,
            "created_at": self.created_at,
            "operator_id": self.operator_id,
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> WorkspacePreparationPlan:
        raw = {k: v for k, v in d.items() if k in cls.__dataclass_fields__}
        if "steps" in raw and isinstance(raw["steps"], list):
            raw["steps"] = [
                PreparationStep.from_dict(s) if isinstance(s, dict) else s for s in raw["steps"]
            ]
        return cls(**raw)


@dataclass
class ApplicationState:
    """State of a single application in a workspace."""

    name: str = ""
    running: bool = False
    window_title: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "running": self.running,
            "window_title": self.window_title,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> ApplicationState:
        return cls(**{k: v for k, v in d.items() if k in cls.__dataclass_fields__})


@dataclass
class WorkspaceState:
    """Current state of a workspace — what's open and active."""

    mode: str = ""
    active_template_id: str = ""
    applications: list[ApplicationState] = field(default_factory=list)
    active_panels: list[str] = field(default_factory=list)
    active_repositories: list[str] = field(default_factory=list)
    active_work_packet_ids: list[str] = field(default_factory=list)
    timestamp: float = 0.0

    def __post_init__(self) -> None:
        if not self.timestamp:
            self.timestamp = time.time()

    def to_dict(self) -> dict[str, Any]:
        return {
            "mode": self.mode,
            "active_template_id": self.active_template_id,
            "applications": [a.to_dict() for a in self.applications],
            "active_panels": self.active_panels,
            "active_repositories": self.active_repositories,
            "active_work_packet_ids": self.active_work_packet_ids,
            "timestamp": self.timestamp,
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> WorkspaceState:
        raw = {k: v for k, v in d.items() if k in cls.__dataclass_fields__}
        if "applications" in raw and isinstance(raw["applications"], list):
            raw["applications"] = [
                ApplicationState.from_dict(a) if isinstance(a, dict) else a
                for a in raw["applications"]
            ]
        return cls(**raw)


@dataclass
class WorkspaceSnapshot:
    """Point-in-time snapshot of workspace — restorable."""

    snapshot_id: str = ""
    trigger: str = SnapshotTrigger.MANUAL.value
    workspace_state: dict[str, Any] = field(default_factory=dict)
    open_objectives: list[str] = field(default_factory=list)
    active_profile: str = ""
    active_session_id: str = ""
    active_loops: list[str] = field(default_factory=list)
    active_work_packets: list[dict[str, Any]] = field(default_factory=list)
    active_recommendations: list[dict[str, Any]] = field(default_factory=list)
    attention_state: str = ""
    operator_notes: str = ""
    created_at: float = 0.0

    def __post_init__(self) -> None:
        if not self.snapshot_id:
            self.snapshot_id = f"snap-{uuid4().hex[:12]}"
        if not self.created_at:
            self.created_at = time.time()

    def to_dict(self) -> dict[str, Any]:
        return {
            "snapshot_id": self.snapshot_id,
            "trigger": self.trigger,
            "workspace_state": self.workspace_state,
            "open_objectives": self.open_objectives,
            "active_profile": self.active_profile,
            "active_session_id": self.active_session_id,
            "active_loops": self.active_loops,
            "active_work_packets": self.active_work_packets,
            "active_recommendations": self.active_recommendations,
            "attention_state": self.attention_state,
            "operator_notes": self.operator_notes,
            "created_at": self.created_at,
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> WorkspaceSnapshot:
        return cls(**{k: v for k, v in d.items() if k in cls.__dataclass_fields__})


@dataclass
class RestorationPlan:
    """Plan for restoring a workspace from a snapshot — planning only."""

    restoration_id: str = ""
    source_snapshot_id: str = ""
    target_mode: str = ""
    objectives_to_restore: list[str] = field(default_factory=list)
    work_packets_to_load: list[dict[str, Any]] = field(default_factory=list)
    loops_to_restore: list[str] = field(default_factory=list)
    continuity_state: dict[str, Any] = field(default_factory=dict)
    projection_state: dict[str, Any] = field(default_factory=dict)
    operator_notes: str = ""
    preparation_plan: dict[str, Any] = field(default_factory=dict)
    created_at: float = 0.0

    def __post_init__(self) -> None:
        if not self.restoration_id:
            self.restoration_id = f"rst-{uuid4().hex[:12]}"
        if not self.created_at:
            self.created_at = time.time()

    def to_dict(self) -> dict[str, Any]:
        return {
            "restoration_id": self.restoration_id,
            "source_snapshot_id": self.source_snapshot_id,
            "target_mode": self.target_mode,
            "objectives_to_restore": self.objectives_to_restore,
            "work_packets_to_load": self.work_packets_to_load,
            "loops_to_restore": self.loops_to_restore,
            "continuity_state": self.continuity_state,
            "projection_state": self.projection_state,
            "operator_notes": self.operator_notes,
            "preparation_plan": self.preparation_plan,
            "created_at": self.created_at,
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> RestorationPlan:
        return cls(**{k: v for k, v in d.items() if k in cls.__dataclass_fields__})


@dataclass
class WorkspaceSequence:
    """Ordered sequence of preparation steps for a workspace mode."""

    sequence_id: str = ""
    mode: str = ""
    steps: list[PreparationStep] = field(default_factory=list)
    estimated_items: int = 0
    created_at: float = 0.0

    def __post_init__(self) -> None:
        if not self.sequence_id:
            self.sequence_id = f"seq-{uuid4().hex[:12]}"
        if not self.created_at:
            self.created_at = time.time()

    def to_dict(self) -> dict[str, Any]:
        return {
            "sequence_id": self.sequence_id,
            "mode": self.mode,
            "steps": [s.to_dict() for s in self.steps],
            "estimated_items": self.estimated_items,
            "created_at": self.created_at,
        }


@dataclass
class WorkstationProfile:
    """Operator profile within the workstation context."""

    profile_mode: str = ""
    preferred_template: str = ""
    preferred_panels: list[str] = field(default_factory=list)
    preferred_repositories: list[str] = field(default_factory=list)
    last_active_at: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "profile_mode": self.profile_mode,
            "preferred_template": self.preferred_template,
            "preferred_panels": self.preferred_panels,
            "preferred_repositories": self.preferred_repositories,
            "last_active_at": self.last_active_at,
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> WorkstationProfile:
        return cls(**{k: v for k, v in d.items() if k in cls.__dataclass_fields__})


@dataclass
class Workstation:
    """Top-level workstation entity."""

    workstation_id: str = ""
    operator_id: str = ""
    current_mode: str = ""
    current_state: dict[str, Any] = field(default_factory=dict)
    profiles: list[WorkstationProfile] = field(default_factory=list)
    last_snapshot_id: str = ""
    created_at: float = 0.0

    def __post_init__(self) -> None:
        if not self.workstation_id:
            self.workstation_id = f"ws-{uuid4().hex[:12]}"
        if not self.created_at:
            self.created_at = time.time()

    def to_dict(self) -> dict[str, Any]:
        return {
            "workstation_id": self.workstation_id,
            "operator_id": self.operator_id,
            "current_mode": self.current_mode,
            "current_state": self.current_state,
            "profiles": [p.to_dict() for p in self.profiles],
            "last_snapshot_id": self.last_snapshot_id,
            "created_at": self.created_at,
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> Workstation:
        raw = {k: v for k, v in d.items() if k in cls.__dataclass_fields__}
        if "profiles" in raw and isinstance(raw["profiles"], list):
            raw["profiles"] = [
                WorkstationProfile.from_dict(p) if isinstance(p, dict) else p
                for p in raw["profiles"]
            ]
        return cls(**raw)


@dataclass
class WorkstationRecommendation:
    """A deterministic recommendation for the operator."""

    recommendation_id: str = ""
    recommendation_type: str = RecommendationType.RESUME_WORK.value
    title: str = ""
    description: str = ""
    source_system: str = ""
    source_data: dict[str, Any] = field(default_factory=dict)
    priority: int = 0
    created_at: float = 0.0

    def __post_init__(self) -> None:
        if not self.recommendation_id:
            self.recommendation_id = f"rec-{uuid4().hex[:12]}"
        if not self.created_at:
            self.created_at = time.time()

    def to_dict(self) -> dict[str, Any]:
        return {
            "recommendation_id": self.recommendation_id,
            "recommendation_type": self.recommendation_type,
            "title": self.title,
            "description": self.description,
            "source_system": self.source_system,
            "source_data": self.source_data,
            "priority": self.priority,
            "created_at": self.created_at,
        }


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Mode Classifier — deterministic intent → workstation mode mapping
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

_MODE_PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    (
        "engineering",
        re.compile(
            r"\b(code|develop|engineer|debug|deploy|build|implement|refactor|"
            r"test|ci|cd|pipeline|merge|commit|branch|pull.?request|pr|"
            r"fix.?bug|api|endpoint|service|container|docker|kubernetes|"
            r"database|migration|schema|operator|runtime|substrate|cockpit|"
            r"repository|repo|vscode|ide|terminal|ssh)\b",
            re.IGNORECASE,
        ),
    ),
    (
        "content",
        re.compile(
            r"\b(content|write|article|blog|post|video|script|edit|publish|"
            r"social.?media|twitter|instagram|linkedin|youtube|thumbnail|"
            r"newsletter|copy|brand|marketing|outreach|campaign|seo|"
            r"audience|creator|podcast|stream)\b",
            re.IGNORECASE,
        ),
    ),
    (
        "music",
        re.compile(
            r"\b(music|produce|mix|master|beat|track|song|album|daw|"
            r"ableton|fl.?studio|logic|midi|audio|vocal|synth|sample|"
            r"instrument|record|studio|sound)\b",
            re.IGNORECASE,
        ),
    ),
    (
        "business",
        re.compile(
            r"\b(business|revenue|profit|sales|client|customer|invoice|"
            r"proposal|contract|pricing|strategy|forecast|budget|finance|"
            r"accounting|tax|legal|meeting|call|pitch|deal|lead|funnel|"
            r"crm|pipeline|prospect|close)\b",
            re.IGNORECASE,
        ),
    ),
    (
        "research",
        re.compile(
            r"\b(research|investigate|analyze|study|paper|report|data|"
            r"survey|benchmark|compare|evaluate|explore|discover|learn|"
            r"understand|literature|review|source|reference|academic|"
            r"experiment|hypothesis|finding)\b",
            re.IGNORECASE,
        ),
    ),
    (
        "admin",
        re.compile(
            r"\b(admin|manage|organize|schedule|calendar|email|inbox|"
            r"todo|task|ticket|issue|setup|configure|install|update|"
            r"backup|restore|clean|maintain|monitor|log|alert|notify)\b",
            re.IGNORECASE,
        ),
    ),
]


class ModeClassifier:
    """Deterministic mode classifier — pattern matching only, no LLM."""

    def classify(self, intent: str) -> tuple[WorkstationMode, float]:
        if not intent or not intent.strip():
            return WorkstationMode.ENGINEERING, 0.3

        scores: dict[str, int] = {}
        text = intent.lower()
        for mode_name, pattern in _MODE_PATTERNS:
            matches = pattern.findall(text)
            if matches:
                scores[mode_name] = len(matches)

        if not scores:
            return WorkstationMode.ENGINEERING, 0.3

        best_mode = max(scores, key=lambda k: scores[k])
        total_matches = sum(scores.values())
        confidence = min(1.0, scores[best_mode] / max(total_matches, 1))

        return WorkstationMode(best_mode), round(confidence, 2)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Template Registry — loads from JSON, no hardcoding
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


class WorkspaceTemplateRegistry:
    """Data-driven template registry backed by JSON files."""

    def __init__(self, templates_dir: str = "") -> None:
        self._dir = templates_dir or os.path.join(_workstation_data_dir(), "templates")
        os.makedirs(self._dir, exist_ok=True)
        self._templates: dict[str, WorkspaceTemplate] = {}
        self._load()

    def _load(self) -> None:
        templates_file = os.path.join(self._dir, "workspace_templates.json")
        if not os.path.exists(templates_file):
            self._seed_defaults()
            return
        try:
            with open(templates_file, "r") as f:
                data = json.load(f)
            for entry in data:
                tpl = WorkspaceTemplate.from_dict(entry)
                self._templates[tpl.template_id] = tpl
        except Exception as e:
            logger.warning("Failed to load workspace templates: %s", e)
            self._seed_defaults()

    def _seed_defaults(self) -> None:
        defaults = _default_templates()
        for tpl in defaults:
            self._templates[tpl.template_id] = tpl
        self._save()

    def _save(self) -> None:
        templates_file = os.path.join(self._dir, "workspace_templates.json")
        try:
            with open(templates_file, "w") as f:
                json.dump([t.to_dict() for t in self._templates.values()], f, indent=2)
        except Exception as e:
            logger.warning("Failed to save workspace templates: %s", e)

    def get(self, template_id: str) -> WorkspaceTemplate | None:
        return self._templates.get(template_id)

    def get_by_mode(self, mode: str) -> WorkspaceTemplate | None:
        for tpl in self._templates.values():
            if tpl.mode == mode:
                return tpl
        return None

    def all_templates(self) -> list[WorkspaceTemplate]:
        return list(self._templates.values())

    def add(self, template: WorkspaceTemplate) -> WorkspaceTemplate:
        self._templates[template.template_id] = template
        self._save()
        return template

    def remove(self, template_id: str) -> bool:
        if template_id in self._templates:
            del self._templates[template_id]
            self._save()
            return True
        return False


def _default_templates() -> list[WorkspaceTemplate]:
    """Seed templates — these are the initial data, not hardcoded logic."""
    return [
        WorkspaceTemplate(
            template_id="tpl-engineering",
            mode="engineering",
            label="Engineering",
            required_applications=["vscode", "claude_code", "terminal"],
            required_repositories=["OS"],
            recommended_cockpit_panels=["commandcenter", "work", "execution", "workspace"],
            recommended_browser_tabs=["github"],
            required_context_sources=["continuity", "work_packets", "gap_engine"],
            description="Full development environment with IDE, CLI, and work tracking",
        ),
        WorkspaceTemplate(
            template_id="tpl-content",
            mode="content",
            label="Content",
            required_applications=["browser", "editor"],
            required_repositories=[],
            recommended_cockpit_panels=["commandcenter", "comms", "knowledge"],
            recommended_browser_tabs=["social_dashboard", "content_calendar"],
            required_context_sources=["continuity", "projections", "reality_model"],
            description="Content creation and publishing workflow",
        ),
        WorkspaceTemplate(
            template_id="tpl-music",
            mode="music",
            label="Music",
            required_applications=["daw", "browser"],
            required_repositories=[],
            recommended_cockpit_panels=["commandcenter", "activity"],
            recommended_browser_tabs=[],
            required_context_sources=["continuity"],
            description="Music production environment",
        ),
        WorkspaceTemplate(
            template_id="tpl-business",
            mode="business",
            label="Business",
            required_applications=["browser", "email", "calendar"],
            required_repositories=[],
            recommended_cockpit_panels=["commandcenter", "strategy", "projections", "work"],
            recommended_browser_tabs=["crm", "analytics"],
            required_context_sources=["continuity", "projections", "gap_engine", "reality_model"],
            description="Business operations, sales, and strategy",
        ),
        WorkspaceTemplate(
            template_id="tpl-research",
            mode="research",
            label="Research",
            required_applications=["browser", "editor"],
            required_repositories=[],
            recommended_cockpit_panels=["commandcenter", "knowledge", "projections"],
            recommended_browser_tabs=["search", "references"],
            required_context_sources=["continuity", "projections", "reality_model"],
            description="Research, analysis, and investigation workflow",
        ),
        WorkspaceTemplate(
            template_id="tpl-admin",
            mode="admin",
            label="Admin",
            required_applications=["browser", "terminal", "email"],
            required_repositories=[],
            recommended_cockpit_panels=["commandcenter", "infrastructure", "settings"],
            recommended_browser_tabs=["admin_dashboard"],
            required_context_sources=["continuity", "presence"],
            description="System administration and maintenance",
        ),
    ]


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Workspace Context Assembler — pulls from all Phase 4-8 subsystems
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


class WorkspaceContextAssembler:
    """Assembles unified context from all UMH subsystems.

    No subsystem owns workstation context — this assembler composes.
    Each source is individually try/excepted for graceful degradation.
    """

    def assemble(self) -> dict[str, Any]:
        ctx: dict[str, Any] = {
            "continuity": {},
            "presence": {},
            "strategy": {},
            "tick_loop": {},
            "projections": {},
            "reality_model": {},
            "work_packets": [],
            "assembled_at": time.time(),
        }
        self._assemble_continuity(ctx)
        self._assemble_presence(ctx)
        self._assemble_strategy(ctx)
        self._assemble_tick_loop(ctx)
        self._assemble_projections(ctx)
        self._assemble_reality_model(ctx)
        self._assemble_work_packets(ctx)
        return ctx

    def _assemble_continuity(self, ctx: dict[str, Any]) -> None:
        try:
            from substrate.organism.continuity_runtime import ContinuityRuntime

            rt = ContinuityRuntime()
            brief = rt.generate_brief()
            if hasattr(brief, "to_dict"):
                ctx["continuity"] = brief.to_dict()
            elif isinstance(brief, dict):
                ctx["continuity"] = brief
            else:
                ctx["continuity"] = {"raw": str(brief)}
        except Exception as e:
            logger.debug("continuity assembly: %s", e)

    def _assemble_presence(self, ctx: dict[str, Any]) -> None:
        try:
            from substrate.organism.presence_runtime import PresenceRuntime

            rt = PresenceRuntime()
            snap = rt.snapshot()
            if hasattr(snap, "to_dict"):
                ctx["presence"] = snap.to_dict()
            elif isinstance(snap, dict):
                ctx["presence"] = snap
            else:
                ctx["presence"] = {"raw": str(snap)}
        except Exception as e:
            logger.debug("presence assembly: %s", e)

    def _assemble_strategy(self, ctx: dict[str, Any]) -> None:
        try:
            from substrate.organism.strategic_gap_engine import (
                StrategicGapEngine,
            )

            engine = StrategicGapEngine()
            gaps = engine.get_all_gaps()
            ctx["strategy"] = {
                "total_gaps": len(gaps),
                "gaps": [g.to_dict() if hasattr(g, "to_dict") else g for g in gaps[:10]],
            }
        except Exception as e:
            logger.debug("strategy assembly: %s", e)

    def _assemble_tick_loop(self, ctx: dict[str, Any]) -> None:
        try:
            from substrate.organism.strategic_tick_loop import (
                CandidateWorkQueue,
            )

            queue = CandidateWorkQueue()
            pending = queue.pending()
            ctx["tick_loop"] = {
                "pending_candidates": len(pending),
                "candidates": [c.to_dict() if hasattr(c, "to_dict") else c for c in pending[:10]],
            }
        except Exception as e:
            logger.debug("tick_loop assembly: %s", e)

    def _assemble_projections(self, ctx: dict[str, Any]) -> None:
        try:
            from substrate.organism.projection_engine import ProjectionEngine

            engine = ProjectionEngine()
            projections = engine.get_active_projections()
            ctx["projections"] = {
                "active_count": len(projections),
                "projections": [
                    p.to_dict() if hasattr(p, "to_dict") else p for p in projections[:10]
                ],
            }
        except Exception as e:
            logger.debug("projections assembly: %s", e)

    def _assemble_reality_model(self, ctx: dict[str, Any]) -> None:
        try:
            from substrate.reality_model.canonical import CanonicalRealityModel

            canonical = CanonicalRealityModel()
            all_patterns = canonical.all()
            domains = sorted(set(p.domain for p in all_patterns if p.domain))
            ctx["reality_model"] = {
                "loaded": True,
                "pattern_count": len(all_patterns),
                "domains": domains,
                "patterns": [
                    {
                        "name": p.name,
                        "domain": p.domain,
                        "confidence": p.effective_confidence(),
                        "evidence_count": p.evidence_count,
                    }
                    for p in sorted(
                        all_patterns,
                        key=lambda x: x.effective_confidence(),
                        reverse=True,
                    )[:20]
                ],
                "stats": canonical.stats(),
            }
        except Exception as e:
            logger.debug("reality_model assembly: %s", e)

    def _assemble_work_packets(self, ctx: dict[str, Any]) -> None:
        try:
            from substrate.state.runtime_paths import runtime_state_path

            wp_path = str(
                runtime_state_path("universal_work", "work_packets.jsonl", create_parent=False)
            )
            if os.path.exists(wp_path):
                packets = []
                with open(wp_path) as f:
                    for line in f:
                        line = line.strip()
                        if not line:
                            continue
                        try:
                            pkt = json.loads(line)
                            status = pkt.get("status", "")
                            if status not in ("completed", "cancelled", "archived"):
                                packets.append(pkt)
                        except json.JSONDecodeError:
                            continue
                ctx["work_packets"] = packets[:20]
        except Exception as e:
            logger.debug("work_packets assembly: %s", e)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Snapshot Store — JSONL-backed persistence
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


class SnapshotStore:
    """JSONL-backed workspace snapshot persistence."""

    def __init__(self, data_dir: str = "") -> None:
        self._dir = data_dir or os.path.join(_workstation_data_dir(), "snapshots")
        os.makedirs(self._dir, exist_ok=True)
        self._path = os.path.join(self._dir, "snapshots.jsonl")

    def save(self, snapshot: WorkspaceSnapshot) -> None:
        try:
            with open(self._path, "a") as f:
                f.write(json.dumps(snapshot.to_dict()) + "\n")
        except Exception as e:
            logger.warning("Failed to save snapshot: %s", e)

    def get_recent(self, limit: int = 20) -> list[dict[str, Any]]:
        results: list[dict[str, Any]] = []
        if not os.path.exists(self._path):
            return results
        try:
            with open(self._path) as f:
                for line in f:
                    line = line.strip()
                    if line:
                        try:
                            results.append(json.loads(line))
                        except json.JSONDecodeError:
                            continue
            results.sort(key=lambda x: x.get("created_at", 0), reverse=True)
            return results[:limit]
        except Exception as e:
            logger.warning("Failed to load snapshots: %s", e)
            return results

    def get_by_id(self, snapshot_id: str) -> dict[str, Any] | None:
        if not os.path.exists(self._path):
            return None
        try:
            with open(self._path) as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        entry = json.loads(line)
                        if entry.get("snapshot_id") == snapshot_id:
                            return entry
                    except json.JSONDecodeError:
                        continue
        except Exception as e:
            logger.warning("Failed to find snapshot %s: %s", snapshot_id, e)
        return None

    def get_latest(self) -> dict[str, Any] | None:
        recent = self.get_recent(limit=1)
        return recent[0] if recent else None


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Recommendation Engine — deterministic, no LLM
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


class RecommendationEngine:
    """Generates deterministic recommendations from existing subsystems.

    Sources: Gap Engine, Projection Engine, Tick Loop.
    No LLM calls.
    """

    def generate(self) -> list[WorkstationRecommendation]:
        recs: list[WorkstationRecommendation] = []
        self._from_gap_engine(recs)
        self._from_projection_engine(recs)
        self._from_tick_loop(recs)
        self._from_work_packets(recs)
        recs.sort(key=lambda r: r.priority, reverse=True)
        return recs

    def _from_gap_engine(self, recs: list[WorkstationRecommendation]) -> None:
        try:
            from substrate.organism.strategic_gap_engine import (
                StrategicGapEngine,
            )

            engine = StrategicGapEngine()
            gaps = engine.get_all_gaps()
            for gap in gaps[:5]:
                gap_dict = gap.to_dict() if hasattr(gap, "to_dict") else {}
                severity = gap_dict.get("severity", "low")
                priority = {"critical": 90, "high": 70, "medium": 50, "low": 30}.get(severity, 30)
                recs.append(
                    WorkstationRecommendation(
                        recommendation_type=RecommendationType.ADDRESS_GAP.value,
                        title=f"Address gap: {gap_dict.get('label', 'unknown')}",
                        description=gap_dict.get("description", ""),
                        source_system="strategic_gap_engine",
                        source_data={"gap_id": gap_dict.get("gap_id", "")},
                        priority=priority,
                    )
                )
        except Exception as e:
            logger.debug("gap engine recommendations: %s", e)

    def _from_projection_engine(self, recs: list[WorkstationRecommendation]) -> None:
        try:
            from substrate.organism.projection_engine import ProjectionEngine

            engine = ProjectionEngine()
            risks = engine.get_active_risks()
            for risk in risks[:3]:
                risk_dict = risk.to_dict() if hasattr(risk, "to_dict") else {}
                severity = risk_dict.get("severity", "low")
                priority = {"critical": 85, "high": 65, "medium": 45, "low": 25}.get(severity, 25)
                recs.append(
                    WorkstationRecommendation(
                        recommendation_type=RecommendationType.INVESTIGATE_RISK.value,
                        title=f"Investigate risk: {risk_dict.get('title', 'unknown')}",
                        description=risk_dict.get("description", ""),
                        source_system="projection_engine",
                        source_data={"risk_id": risk_dict.get("risk_id", "")},
                        priority=priority,
                    )
                )
        except Exception as e:
            logger.debug("projection engine recommendations: %s", e)

    def _from_tick_loop(self, recs: list[WorkstationRecommendation]) -> None:
        try:
            from substrate.organism.strategic_tick_loop import (
                CandidateWorkQueue,
            )

            queue = CandidateWorkQueue()
            pending = queue.pending()
            for candidate in pending[:3]:
                c_dict = candidate.to_dict() if hasattr(candidate, "to_dict") else {}
                recs.append(
                    WorkstationRecommendation(
                        recommendation_type=RecommendationType.FOLLOW_UP.value,
                        title=f"Review candidate: {c_dict.get('title', 'unknown')}",
                        description=c_dict.get("description", ""),
                        source_system="tick_loop",
                        source_data={
                            "candidate_id": c_dict.get("candidate_id", ""),
                        },
                        priority=40,
                    )
                )
        except Exception as e:
            logger.debug("tick loop recommendations: %s", e)

    def _from_work_packets(self, recs: list[WorkstationRecommendation]) -> None:
        try:
            from substrate.state.runtime_paths import runtime_state_path

            wp_path = str(
                runtime_state_path("universal_work", "work_packets.jsonl", create_parent=False)
            )
            if not os.path.exists(wp_path):
                return
            with open(wp_path) as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        pkt = json.loads(line)
                        status = pkt.get("status", "")
                        if status == "blocked":
                            recs.append(
                                WorkstationRecommendation(
                                    recommendation_type=RecommendationType.REVIEW_BLOCKED.value,
                                    title=f"Review blocked: {pkt.get('title', pkt.get('packet_id', 'unknown'))}",
                                    description=pkt.get("description", ""),
                                    source_system="work_packets",
                                    source_data={
                                        "packet_id": pkt.get("packet_id", ""),
                                    },
                                    priority=75,
                                )
                            )
                        elif status == "pending_approval":
                            recs.append(
                                WorkstationRecommendation(
                                    recommendation_type=RecommendationType.APPROVE_PROPOSAL.value,
                                    title=f"Approve: {pkt.get('title', pkt.get('packet_id', 'unknown'))}",
                                    description=pkt.get("description", ""),
                                    source_system="work_packets",
                                    source_data={
                                        "packet_id": pkt.get("packet_id", ""),
                                    },
                                    priority=80,
                                )
                            )
                    except json.JSONDecodeError:
                        continue
        except Exception as e:
            logger.debug("work packet recommendations: %s", e)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Preparation Sequencer — builds ordered preparation steps
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


class PreparationSequencer:
    """Builds ordered preparation sequences from templates.

    Only plans. Never launches.
    """

    def sequence(
        self,
        template: WorkspaceTemplate,
        work_packets: list[dict[str, Any]] | None = None,
    ) -> WorkspaceSequence:
        steps: list[PreparationStep] = []
        priority = 100

        for app in template.required_applications:
            steps.append(
                PreparationStep(
                    step_type=PreparationStepType.APPLICATION.value,
                    target=app,
                    reason=f"Required by {template.label} template",
                    priority=priority,
                )
            )
            priority -= 1

        for repo in template.required_repositories:
            steps.append(
                PreparationStep(
                    step_type=PreparationStepType.REPOSITORY.value,
                    target=repo,
                    reason=f"Required repository for {template.label}",
                    priority=priority,
                )
            )
            priority -= 1

        for panel in template.recommended_cockpit_panels:
            steps.append(
                PreparationStep(
                    step_type=PreparationStepType.COCKPIT_PANEL.value,
                    target=panel,
                    reason=f"Recommended panel for {template.label}",
                    priority=priority,
                )
            )
            priority -= 1

        for tab in template.recommended_browser_tabs:
            steps.append(
                PreparationStep(
                    step_type=PreparationStepType.BROWSER_TAB.value,
                    target=tab,
                    reason=f"Recommended tab for {template.label}",
                    priority=priority,
                )
            )
            priority -= 1

        for source in template.required_context_sources:
            steps.append(
                PreparationStep(
                    step_type=PreparationStepType.CONTEXT_SOURCE.value,
                    target=source,
                    reason=f"Required context for {template.label}",
                    priority=priority,
                )
            )
            priority -= 1

        if work_packets:
            for pkt in work_packets[:10]:
                pkt_id = pkt.get("packet_id", pkt.get("id", "unknown"))
                steps.append(
                    PreparationStep(
                        step_type=PreparationStepType.WORK_PACKET.value,
                        target=pkt_id,
                        reason="Active work packet",
                        priority=priority,
                        metadata={"title": pkt.get("title", "")},
                    )
                )
                priority -= 1

        seq = WorkspaceSequence(
            mode=template.mode,
            steps=steps,
            estimated_items=len(steps),
        )
        return seq


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Workstation Runtime — the orchestrator
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


class WorkstationRuntime:
    """Canonical workstation planning layer.

    Composes Phase 3-9 subsystems.  Never executes — only plans.
    """

    def __init__(self) -> None:
        _ensure_dirs()
        self._classifier = ModeClassifier()
        self._templates = WorkspaceTemplateRegistry()
        self._assembler = WorkspaceContextAssembler()
        self._sequencer = PreparationSequencer()
        self._snapshots = SnapshotStore()
        self._recommendations = RecommendationEngine()
        self._plans_path = os.path.join(_workstation_data_dir(), "preparation_plans.jsonl")
        self._state_path = os.path.join(_workstation_data_dir(), "workstation_state.json")

    # ── Primary API ────────────────────────────────────────────────

    def prepare_workspace(
        self,
        intent: str,
        profile_mode: str = "",
        session_id: str = "",
        operator_id: str = "",
    ) -> WorkspacePreparationPlan:
        """Prepare a workspace plan for a given intent.

        Does NOT launch anything.  Returns a plan only.
        """
        mode, confidence = self._classifier.classify(intent)
        template = self._templates.get_by_mode(mode.value)
        if not template:
            template = WorkspaceTemplate(
                template_id="tpl-fallback",
                mode=mode.value,
                label=mode.value.title(),
            )

        context = self._assembler.assemble()
        work_packets = context.get("work_packets", [])

        sequence = self._sequencer.sequence(template, work_packets)

        recs = self._recommendations.generate()
        rec_dicts = [r.to_dict() for r in recs[:10]]

        plan = WorkspacePreparationPlan(
            mode=mode.value,
            template_id=template.template_id,
            profile_mode=profile_mode or mode.value,
            intent=intent,
            steps=sequence.steps,
            context_summary={
                "classification_confidence": confidence,
                "mode": mode.value,
                "template": template.label,
                "assembled_at": context.get("assembled_at", 0),
            },
            active_work_packets=work_packets[:10],
            continuity_context=context.get("continuity", {}),
            projection_context=context.get("projections", {}),
            recommendations=rec_dicts,
            operator_id=operator_id,
        )

        self._save_plan(plan)
        self._update_state(mode.value, template.template_id)

        return plan

    def restore_workspace(self, snapshot_id: str = "") -> RestorationPlan:
        """Generate a restoration plan from a snapshot.

        Reconstructs last active objectives, work packets, loops,
        continuity state, projection state, and operator notes.
        Does NOT execute the restoration.
        """
        if snapshot_id:
            snap_data = self._snapshots.get_by_id(snapshot_id)
        else:
            snap_data = self._snapshots.get_latest()

        if not snap_data:
            context = self._assembler.assemble()
            return RestorationPlan(
                target_mode="engineering",
                work_packets_to_load=context.get("work_packets", [])[:10],
                continuity_state=context.get("continuity", {}),
                projection_state=context.get("projections", {}),
            )

        snapshot = WorkspaceSnapshot.from_dict(snap_data)

        ws_state = snapshot.workspace_state
        target_mode = (
            ws_state.get("mode", "engineering") if isinstance(ws_state, dict) else "engineering"
        )
        template = self._templates.get_by_mode(target_mode)

        prep_plan: dict[str, Any] = {}
        if template:
            sequence = self._sequencer.sequence(template)
            prep_plan = {
                "sequence_id": sequence.sequence_id,
                "mode": sequence.mode,
                "steps": [s.to_dict() for s in sequence.steps],
                "estimated_items": sequence.estimated_items,
            }

        context = self._assembler.assemble()

        plan = RestorationPlan(
            source_snapshot_id=snapshot.snapshot_id,
            target_mode=target_mode,
            objectives_to_restore=snapshot.open_objectives,
            work_packets_to_load=snapshot.active_work_packets
            or context.get("work_packets", [])[:10],
            loops_to_restore=snapshot.active_loops,
            continuity_state=context.get("continuity", {}),
            projection_state=context.get("projections", {}),
            operator_notes=snapshot.operator_notes,
            preparation_plan=prep_plan,
        )

        return plan

    def take_snapshot(
        self,
        trigger: str = SnapshotTrigger.MANUAL.value,
        operator_notes: str = "",
    ) -> WorkspaceSnapshot:
        """Capture current workspace state as a restorable snapshot."""
        context = self._assembler.assemble()
        state = self._load_state()

        presence = context.get("presence", {})
        active_profile = presence.get("profile_mode", "")
        active_session = presence.get("active_session_id", "")
        attention = presence.get("attention_state", "")

        objectives: list[str] = []
        try:
            from substrate.organism.strategic_gap_engine import (
                StrategicGapEngine,
            )

            engine = StrategicGapEngine()
            goals = engine.get_all_goals()
            objectives = [
                g.label if hasattr(g, "label") else str(g)
                for g in goals[:10]
                if (hasattr(g, "status") and g.status != "completed") or True
            ]
        except Exception as e:
            logger.debug("snapshot objectives: %s", e)

        active_loops: list[str] = []
        tick_data = context.get("tick_loop", {})
        if isinstance(tick_data, dict):
            candidates = tick_data.get("candidates", [])
            active_loops = [c.get("candidate_id", "") for c in candidates if isinstance(c, dict)][
                :5
            ]

        snapshot = WorkspaceSnapshot(
            trigger=trigger,
            workspace_state=state,
            open_objectives=objectives,
            active_profile=active_profile,
            active_session_id=active_session,
            active_loops=active_loops,
            active_work_packets=context.get("work_packets", [])[:10],
            active_recommendations=[r.to_dict() for r in self._recommendations.generate()[:5]],
            attention_state=attention,
            operator_notes=operator_notes,
        )

        self._snapshots.save(snapshot)
        return snapshot

    def get_templates(self) -> list[dict[str, Any]]:
        """Return all workspace templates."""
        return [t.to_dict() for t in self._templates.all_templates()]

    def get_snapshots(self, limit: int = 20) -> list[dict[str, Any]]:
        """Return recent snapshots."""
        return self._snapshots.get_recent(limit=limit)

    def get_recommendations(self) -> list[dict[str, Any]]:
        """Generate and return current recommendations."""
        return [r.to_dict() for r in self._recommendations.generate()]

    def get_state(self) -> dict[str, Any]:
        """Return current workstation state."""
        state = self._load_state()
        state["templates_available"] = len(self._templates.all_templates())
        state["latest_snapshot"] = self._snapshots.get_latest()
        return state

    # ── Persistence helpers ────────────────────────────────────────

    def _save_plan(self, plan: WorkspacePreparationPlan) -> None:
        try:
            with open(self._plans_path, "a") as f:
                f.write(json.dumps(plan.to_dict()) + "\n")
        except Exception as e:
            logger.warning("Failed to save preparation plan: %s", e)

    def _load_state(self) -> dict[str, Any]:
        if os.path.exists(self._state_path):
            try:
                with open(self._state_path) as f:
                    return json.load(f)
            except Exception:
                pass
        return {"mode": "", "template_id": "", "updated_at": 0}

    def _update_state(self, mode: str, template_id: str) -> None:
        state = self._load_state()
        state["mode"] = mode
        state["template_id"] = template_id
        state["updated_at"] = time.time()
        try:
            with open(self._state_path, "w") as f:
                json.dump(state, f, indent=2)
        except Exception as e:
            logger.warning("Failed to update workstation state: %s", e)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Singleton
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

_INSTANCE: WorkstationRuntime | None = None


def get_workstation_runtime() -> WorkstationRuntime:
    global _INSTANCE
    if _INSTANCE is None:
        _INSTANCE = WorkstationRuntime()
    return _INSTANCE


def reset_workstation_runtime() -> None:
    global _INSTANCE
    _INSTANCE = None
