"""Environment Mapping Engine v1.

Exploratory pre-ingestion layer that discovers, classifies, and plans
ingestion strategies across the founder workstation environment.

Flow: explore → map → classify → plan → ingest
(never: blind ingest)

Discovery domains:
  Chrome profiles, Google accounts, Notion, Discord, Claude, OpenAI,
  GitHub, Gmail, Drive, Slack, local vaults, Obsidian, VSCode/Cursor,
  terminals, local repos, Docker containers, startup apps, browser
  sessions, installed desktop apps.

No hidden scanning. No credential scraping. No autonomous mutation.
All discovery through visible foreground CU + relay transport.

UMH substrate subsystem. Phase 96.8AT.
"""

from __future__ import annotations

import hashlib
import json
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from core.actuation.actuator_maturity_v1 import (
    MATURITY_LABELS,
    ActuatorMaturityLevel,
)
from eos_ai.substrate.memory_scope_contracts import MemoryScope
import os
_ROOT = os.environ.get("UMH_ROOT") or os.environ.get("OS_ROOT") or os.environ.get("EOS_ROOT") or "/opt/OS"



def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


ENVIRONMENT_MAP_DIR = Path("data/runtime/workstation_relay/environment_maps")

DISCOVERY_DOMAINS = frozenset(
    {
        "chrome_profiles",
        "google_accounts",
        "notion",
        "discord",
        "claude",
        "openai",
        "github",
        "gmail",
        "drive",
        "slack",
        "local_vaults",
        "obsidian",
        "vscode",
        "cursor",
        "terminals",
        "local_repos",
        "docker_containers",
        "startup_apps",
        "browser_sessions",
        "installed_desktop_apps",
    }
)

CANDIDATE_TYPE_CANONICAL = "canonical"
CANDIDATE_TYPE_INSTANCE = "instance"

CANONICAL_PLATFORM_INDICATORS = frozenset(
    {
        "template",
        "schema",
        "framework",
        "workflow",
        "architecture",
        "abstraction",
        "principle",
        "protocol",
        "standard",
        "generic",
        "reusable",
        "universal",
        "open_source",
    }
)

INSTANCE_PLATFORM_INDICATORS = frozenset(
    {
        "account",
        "personal",
        "workspace",
        "profile",
        "credential",
        "identity",
        "subscription",
        "inbox",
        "chat",
        "private",
        "company",
        "founder",
        "team",
        "organization",
    }
)


@dataclass
class DiscoveredPlatform:
    """A platform discovered on the workstation."""

    platform_id: str = ""
    name: str = ""
    domain: str = ""
    detected_via: str = ""
    installed: bool = False
    running: bool = False
    has_visible_window: bool = False
    window_title: str = ""
    process_name: str = ""
    accounts: list[str] = field(default_factory=list)
    candidate_type: str = CANDIDATE_TYPE_INSTANCE
    timestamp: str = ""

    def __post_init__(self) -> None:
        if not self.platform_id:
            self.platform_id = f"PLAT-{uuid.uuid4().hex[:8]}"
        if not self.timestamp:
            self.timestamp = _now_iso()

    def to_dict(self) -> dict[str, Any]:
        return {
            "platform_id": self.platform_id,
            "name": self.name,
            "domain": self.domain,
            "detected_via": self.detected_via,
            "installed": self.installed,
            "running": self.running,
            "has_visible_window": self.has_visible_window,
            "window_title": self.window_title,
            "process_name": self.process_name,
            "accounts": self.accounts,
            "candidate_type": self.candidate_type,
            "timestamp": self.timestamp,
        }


@dataclass
class DiscoveredAccount:
    """An account identity discovered on the workstation."""

    account_id: str = ""
    email: str = ""
    username: str = ""
    platform: str = ""
    domain: str = ""
    detected_via: str = ""
    is_primary: bool = False
    candidate_type: str = CANDIDATE_TYPE_INSTANCE
    timestamp: str = ""

    def __post_init__(self) -> None:
        if not self.account_id:
            self.account_id = f"ACCT-{uuid.uuid4().hex[:8]}"
        if not self.timestamp:
            self.timestamp = _now_iso()

    def to_dict(self) -> dict[str, Any]:
        return {
            "account_id": self.account_id,
            "email": self.email,
            "username": self.username,
            "platform": self.platform,
            "domain": self.domain,
            "detected_via": self.detected_via,
            "is_primary": self.is_primary,
            "candidate_type": self.candidate_type,
            "timestamp": self.timestamp,
        }


@dataclass
class DiscoveredWorkspace:
    """A workspace or project context discovered on the workstation."""

    workspace_id: str = ""
    name: str = ""
    platform: str = ""
    workspace_type: str = ""
    path: str = ""
    detected_via: str = ""
    candidate_type: str = CANDIDATE_TYPE_INSTANCE
    timestamp: str = ""

    def __post_init__(self) -> None:
        if not self.workspace_id:
            self.workspace_id = f"WKSP-{uuid.uuid4().hex[:8]}"
        if not self.timestamp:
            self.timestamp = _now_iso()

    def to_dict(self) -> dict[str, Any]:
        return {
            "workspace_id": self.workspace_id,
            "name": self.name,
            "platform": self.platform,
            "workspace_type": self.workspace_type,
            "path": self.path,
            "detected_via": self.detected_via,
            "candidate_type": self.candidate_type,
            "timestamp": self.timestamp,
        }


@dataclass
class RelationshipEdge:
    """A cross-reference relationship between two discovered entities."""

    edge_id: str = ""
    source_id: str = ""
    source_type: str = ""
    target_id: str = ""
    target_type: str = ""
    relationship: str = ""
    evidence: str = ""
    confidence: float = 0.0
    timestamp: str = ""

    def __post_init__(self) -> None:
        if not self.edge_id:
            self.edge_id = f"REL-{uuid.uuid4().hex[:8]}"
        if not self.timestamp:
            self.timestamp = _now_iso()

    @property
    def canonical_key(self) -> str:
        parts = sorted([self.source_id, self.target_id])
        return f"{parts[0]}::{self.relationship}::{parts[1]}"

    def to_dict(self) -> dict[str, Any]:
        return {
            "edge_id": self.edge_id,
            "source_id": self.source_id,
            "source_type": self.source_type,
            "target_id": self.target_id,
            "target_type": self.target_type,
            "relationship": self.relationship,
            "evidence": self.evidence,
            "confidence": round(self.confidence, 2),
            "timestamp": self.timestamp,
        }


@dataclass
class IngestionLane:
    """A planned ingestion path for a discovered platform/workspace."""

    lane_id: str = ""
    platform: str = ""
    workspace: str = ""
    extraction_method: str = ""
    required_maturity: ActuatorMaturityLevel = ActuatorMaturityLevel.L3_FOREGROUND_FOCUSED
    canonical_likelihood: float = 0.0
    instance_likelihood: float = 1.0
    replayable: bool = False
    requires_cu: bool = True
    requires_foreground: bool = True
    requires_founder_confirmation: bool = True
    requires_screenshot: bool = True
    safety_rating: str = "safe"
    timestamp: str = ""

    def __post_init__(self) -> None:
        if not self.lane_id:
            self.lane_id = f"LANE-{uuid.uuid4().hex[:8]}"
        if not self.timestamp:
            self.timestamp = _now_iso()

    def to_dict(self) -> dict[str, Any]:
        return {
            "lane_id": self.lane_id,
            "platform": self.platform,
            "workspace": self.workspace,
            "extraction_method": self.extraction_method,
            "required_maturity": self.required_maturity.value,
            "required_maturity_name": self.required_maturity.name,
            "canonical_likelihood": round(self.canonical_likelihood, 2),
            "instance_likelihood": round(self.instance_likelihood, 2),
            "replayable": self.replayable,
            "requires_cu": self.requires_cu,
            "requires_foreground": self.requires_foreground,
            "requires_founder_confirmation": self.requires_founder_confirmation,
            "requires_screenshot": self.requires_screenshot,
            "safety_rating": self.safety_rating,
            "timestamp": self.timestamp,
        }


@dataclass
class EnvironmentTopology:
    """Complete topology of the discovered workstation environment."""

    topology_id: str = ""
    platforms: list[DiscoveredPlatform] = field(default_factory=list)
    accounts: list[DiscoveredAccount] = field(default_factory=list)
    workspaces: list[DiscoveredWorkspace] = field(default_factory=list)
    relationships: list[RelationshipEdge] = field(default_factory=list)
    ingestion_lanes: list[IngestionLane] = field(default_factory=list)
    timestamp: str = ""

    def __post_init__(self) -> None:
        if not self.topology_id:
            self.topology_id = f"TOPO-{uuid.uuid4().hex[:8]}"
        if not self.timestamp:
            self.timestamp = _now_iso()

    @property
    def platform_count(self) -> int:
        return len(self.platforms)

    @property
    def account_count(self) -> int:
        return len(self.accounts)

    @property
    def workspace_count(self) -> int:
        return len(self.workspaces)

    @property
    def relationship_count(self) -> int:
        return len(self.relationships)

    @property
    def lane_count(self) -> int:
        return len(self.ingestion_lanes)

    @property
    def canonical_candidates(self) -> list[DiscoveredPlatform]:
        return [p for p in self.platforms if p.candidate_type == CANDIDATE_TYPE_CANONICAL]

    @property
    def instance_candidates(self) -> list[DiscoveredPlatform]:
        return [p for p in self.platforms if p.candidate_type == CANDIDATE_TYPE_INSTANCE]

    def to_dict(self) -> dict[str, Any]:
        return {
            "topology_id": self.topology_id,
            "platforms": [p.to_dict() for p in self.platforms],
            "accounts": [a.to_dict() for a in self.accounts],
            "workspaces": [w.to_dict() for w in self.workspaces],
            "relationships": [r.to_dict() for r in self.relationships],
            "ingestion_lanes": [l.to_dict() for l in self.ingestion_lanes],
            "platform_count": self.platform_count,
            "account_count": self.account_count,
            "workspace_count": self.workspace_count,
            "relationship_count": self.relationship_count,
            "lane_count": self.lane_count,
            "canonical_count": len(self.canonical_candidates),
            "instance_count": len(self.instance_candidates),
            "timestamp": self.timestamp,
        }


ENVIRONMENT_MATURITY_REQUIREMENTS: dict[str, list[str]] = {
    "L0_NO_MAPPING": [],
    "L1_PROCESSES_ENUMERATED": ["process_list"],
    "L2_PLATFORMS_IDENTIFIED": ["process_list", "platforms_identified"],
    "L3_ENVIRONMENT_INTELLIGENCE": [
        "process_list",
        "platforms_identified",
        "accounts_linked",
        "relationships_synthesized",
        "lanes_planned",
        "screenshots_captured",
        "founder_confirmed",
    ],
}


@dataclass
class EnvironmentMappingEvidence:
    """Evidence collected from exploratory environment mapping."""

    process_list_captured: bool = False
    platforms_identified: bool = False
    platform_count: int = 0
    accounts_linked: bool = False
    account_count: int = 0
    workspaces_discovered: bool = False
    workspace_count: int = 0
    relationships_synthesized: bool = False
    relationship_count: int = 0
    lanes_planned: bool = False
    lane_count: int = 0
    screenshots_captured: bool = False
    screenshot_count: int = 0
    screenshot_paths: list[str] = field(default_factory=list)
    screenshot_hashes: list[str] = field(default_factory=list)
    graph_generated: bool = False
    canonical_separated: bool = False
    canonical_count: int = 0
    instance_count: int = 0
    founder_confirmed: bool = False
    desktop_unlocked: bool = False
    desktop_session_active: bool = False
    is_dry_run: bool = False
    trace_id: str = ""
    request_id: str = ""
    relay_node_id: str = ""
    relay_machine: str = ""

    @property
    def has_screenshots(self) -> bool:
        return self.screenshots_captured and self.screenshot_count > 0

    @property
    def has_graph(self) -> bool:
        return self.graph_generated and self.platform_count > 0

    @property
    def has_relationships(self) -> bool:
        return self.relationships_synthesized and self.relationship_count > 0

    @property
    def has_lanes(self) -> bool:
        return self.lanes_planned and self.lane_count > 0

    @property
    def missing_evidence(self) -> list[str]:
        missing: list[str] = []
        if not self.process_list_captured:
            missing.append("process_list")
        if not self.platforms_identified:
            missing.append("platforms_identified")
        if not self.accounts_linked:
            missing.append("accounts_linked")
        if not self.has_screenshots:
            missing.append("screenshots")
        if not self.has_graph:
            missing.append("graph_generated")
        if not self.has_relationships:
            missing.append("relationships_synthesized")
        if not self.has_lanes:
            missing.append("lanes_planned")
        if not self.founder_confirmed:
            missing.append("founder_confirmed")
        return missing

    def to_dict(self) -> dict[str, Any]:
        return {
            "process_list_captured": self.process_list_captured,
            "platforms_identified": self.platforms_identified,
            "platform_count": self.platform_count,
            "accounts_linked": self.accounts_linked,
            "account_count": self.account_count,
            "workspaces_discovered": self.workspaces_discovered,
            "workspace_count": self.workspace_count,
            "relationships_synthesized": self.relationships_synthesized,
            "relationship_count": self.relationship_count,
            "lanes_planned": self.lanes_planned,
            "lane_count": self.lane_count,
            "screenshots_captured": self.screenshots_captured,
            "screenshot_count": self.screenshot_count,
            "graph_generated": self.graph_generated,
            "canonical_separated": self.canonical_separated,
            "canonical_count": self.canonical_count,
            "instance_count": self.instance_count,
            "founder_confirmed": self.founder_confirmed,
            "desktop_unlocked": self.desktop_unlocked,
            "desktop_session_active": self.desktop_session_active,
            "is_dry_run": self.is_dry_run,
            "trace_id": self.trace_id,
            "request_id": self.request_id,
            "missing_evidence": self.missing_evidence,
        }


@dataclass
class EnvironmentMappingProof:
    """Complete proof of environment mapping execution."""

    proof_id: str = ""
    trace_id: str = ""
    maturity_level: str = "L0_NO_MAPPING"
    maturity_ceiling: str = "L3_ENVIRONMENT_INTELLIGENCE"
    escalation_blocked: bool = False
    escalation_reason: str = ""
    evidence: EnvironmentMappingEvidence | None = None
    topology: EnvironmentTopology | None = None
    timestamp: str = ""

    def __post_init__(self) -> None:
        if not self.proof_id:
            h = hashlib.sha256(f"{self.trace_id}-{_now_iso()}".encode()).hexdigest()[:8]
            self.proof_id = f"ENVMAP-{h}"
        if not self.timestamp:
            self.timestamp = _now_iso()

    def to_dict(self) -> dict[str, Any]:
        return {
            "proof_id": self.proof_id,
            "proof_type": "environment_mapping",
            "trace_id": self.trace_id,
            "maturity_level": self.maturity_level,
            "maturity_ceiling": self.maturity_ceiling,
            "escalation_blocked": self.escalation_blocked,
            "escalation_reason": self.escalation_reason,
            "evidence": self.evidence.to_dict() if self.evidence else None,
            "topology": self.topology.to_dict() if self.topology else None,
            "timestamp": self.timestamp,
        }


PLATFORM_PROCESS_MAP: dict[str, dict[str, str]] = {
    "chrome": {"name": "Google Chrome", "domain": "google.com", "process": "chrome"},
    "discord": {"name": "Discord", "domain": "discord.com", "process": "Discord"},
    "slack": {"name": "Slack", "domain": "slack.com", "process": "slack"},
    "code": {"name": "VS Code", "domain": "vscode.dev", "process": "Code"},
    "cursor": {"name": "Cursor", "domain": "cursor.com", "process": "Cursor"},
    "obsidian": {"name": "Obsidian", "domain": "obsidian.md", "process": "Obsidian"},
    "notion": {"name": "Notion", "domain": "notion.so", "process": "Notion"},
    "docker": {"name": "Docker Desktop", "domain": "docker.com", "process": "Docker Desktop"},
    "windowsterminal": {
        "name": "Windows Terminal",
        "domain": "terminal",
        "process": "WindowsTerminal",
    },
    "powershell": {"name": "PowerShell", "domain": "terminal", "process": "powershell"},
    "github": {"name": "GitHub Desktop", "domain": "github.com", "process": "GitHubDesktop"},
    "claude": {"name": "Claude", "domain": "anthropic.com", "process": "claude"},
    "spotify": {"name": "Spotify", "domain": "spotify.com", "process": "Spotify"},
    "steam": {"name": "Steam", "domain": "steampowered.com", "process": "steam"},
    "explorer": {"name": "File Explorer", "domain": "local", "process": "explorer"},
}

LANE_EXTRACTION_METHODS: dict[str, str] = {
    "google_chrome": "foreground_cu_clipboard",
    "notion": "foreground_cu_clipboard",
    "discord": "foreground_cu_clipboard",
    "slack": "foreground_cu_clipboard",
    "gmail": "foreground_cu_clipboard",
    "drive": "foreground_cu_clipboard",
    "github": "foreground_cu_clipboard",
    "obsidian": "local_vault_read",
    "vscode": "local_workspace_read",
    "cursor": "local_workspace_read",
    "local_repos": "local_git_read",
    "docker": "docker_api_read",
    "terminals": "visible_terminal_read",
}

LANE_SAFETY_RATINGS: dict[str, str] = {
    "foreground_cu_clipboard": "safe",
    "local_vault_read": "safe",
    "local_workspace_read": "safe",
    "local_git_read": "safe",
    "docker_api_read": "safe",
    "visible_terminal_read": "caution",
}


def classify_platform_type(name: str, domain: str) -> str:
    """Classify whether a platform discovery is canonical or instance."""
    text = f"{name} {domain}".lower()
    canonical_score = sum(1 for ind in CANONICAL_PLATFORM_INDICATORS if ind in text)
    instance_score = sum(1 for ind in INSTANCE_PLATFORM_INDICATORS if ind in text)
    if instance_score > canonical_score:
        return CANDIDATE_TYPE_INSTANCE
    if canonical_score > 0:
        return CANDIDATE_TYPE_CANONICAL
    return CANDIDATE_TYPE_INSTANCE


def extract_platforms_from_process_list(
    process_list: list[dict[str, Any]],
) -> list[DiscoveredPlatform]:
    """Extract discovered platforms from a raw process list."""
    platforms: list[DiscoveredPlatform] = []
    seen_processes: set[str] = set()

    for proc in process_list:
        proc_name = proc.get("name", "").lower().replace(".exe", "")
        if not proc_name or proc_name in seen_processes:
            continue

        for key, meta in PLATFORM_PROCESS_MAP.items():
            if key in proc_name:
                seen_processes.add(proc_name)
                platforms.append(
                    DiscoveredPlatform(
                        name=meta["name"],
                        domain=meta["domain"],
                        detected_via="process_enumeration",
                        installed=True,
                        running=True,
                        has_visible_window=proc.get("has_window", False),
                        window_title=proc.get("window_title", ""),
                        process_name=proc_name,
                        candidate_type=classify_platform_type(meta["name"], meta["domain"]),
                    )
                )
                break

    return platforms


def extract_platforms_from_installed_apps(
    app_list: list[dict[str, Any]],
) -> list[DiscoveredPlatform]:
    """Extract discovered platforms from installed application list."""
    platforms: list[DiscoveredPlatform] = []
    seen_names: set[str] = set()

    for app in app_list:
        app_name = app.get("name", "")
        if not app_name or app_name.lower() in seen_names:
            continue

        for key, meta in PLATFORM_PROCESS_MAP.items():
            if key in app_name.lower():
                seen_names.add(app_name.lower())
                platforms.append(
                    DiscoveredPlatform(
                        name=meta["name"],
                        domain=meta["domain"],
                        detected_via="installed_app_enumeration",
                        installed=True,
                        running=False,
                        process_name=meta["process"],
                        candidate_type=classify_platform_type(meta["name"], meta["domain"]),
                    )
                )
                break

    return platforms


def extract_accounts_from_chrome_profiles(
    profiles: list[dict[str, Any]],
) -> list[DiscoveredAccount]:
    """Extract account identities from Chrome profile data."""
    accounts: list[DiscoveredAccount] = []
    seen_emails: set[str] = set()

    for profile in profiles:
        email = profile.get("email", "")
        if not email or email in seen_emails:
            continue
        seen_emails.add(email)

        domain = email.split("@")[1] if "@" in email else ""
        accounts.append(
            DiscoveredAccount(
                email=email,
                username=profile.get("name", ""),
                platform="google_chrome",
                domain=domain,
                detected_via="chrome_profile",
                is_primary=profile.get("is_default", False),
            )
        )

    return accounts


def extract_accounts_from_browser_sessions(
    sessions: list[dict[str, Any]],
) -> list[DiscoveredAccount]:
    """Extract account identities from browser session data."""
    accounts: list[DiscoveredAccount] = []
    seen: set[str] = set()

    for session in sessions:
        email = session.get("email", "")
        platform = session.get("platform", "")
        key = f"{email}:{platform}"
        if not email or key in seen:
            continue
        seen.add(key)

        domain = email.split("@")[1] if "@" in email else ""
        accounts.append(
            DiscoveredAccount(
                email=email,
                username=session.get("username", ""),
                platform=platform,
                domain=domain,
                detected_via="browser_session",
            )
        )

    return accounts


def synthesize_relationships(
    platforms: list[DiscoveredPlatform],
    accounts: list[DiscoveredAccount],
    workspaces: list[DiscoveredWorkspace],
) -> list[RelationshipEdge]:
    """Cross-reference entities to find relationships."""
    edges: list[RelationshipEdge] = []
    seen_keys: set[str] = set()

    for acct in accounts:
        for plat in platforms:
            if acct.platform and acct.platform.lower() in plat.name.lower():
                edge = RelationshipEdge(
                    source_id=acct.account_id,
                    source_type="account",
                    target_id=plat.platform_id,
                    target_type="platform",
                    relationship="account_on_platform",
                    evidence=f"{acct.email} on {plat.name}",
                    confidence=0.9,
                )
                if edge.canonical_key not in seen_keys:
                    seen_keys.add(edge.canonical_key)
                    edges.append(edge)

    email_to_accounts: dict[str, list[DiscoveredAccount]] = {}
    for acct in accounts:
        if acct.email:
            email_to_accounts.setdefault(acct.email, []).append(acct)

    for email, accts in email_to_accounts.items():
        if len(accts) > 1:
            for i in range(len(accts)):
                for j in range(i + 1, len(accts)):
                    edge = RelationshipEdge(
                        source_id=accts[i].account_id,
                        source_type="account",
                        target_id=accts[j].account_id,
                        target_type="account",
                        relationship="same_email",
                        evidence=f"shared email: {email}",
                        confidence=1.0,
                    )
                    if edge.canonical_key not in seen_keys:
                        seen_keys.add(edge.canonical_key)
                        edges.append(edge)

    domain_to_accounts: dict[str, list[DiscoveredAccount]] = {}
    for acct in accounts:
        if acct.domain:
            domain_to_accounts.setdefault(acct.domain, []).append(acct)

    for domain, accts in domain_to_accounts.items():
        if len(accts) > 1:
            for i in range(len(accts)):
                for j in range(i + 1, len(accts)):
                    key = f"{accts[i].account_id}::same_email::{accts[j].account_id}"
                    normalized = "::".join(sorted([accts[i].account_id, accts[j].account_id]))
                    same_email_key = f"{normalized}::same_email"
                    if same_email_key in {
                        e.canonical_key.replace("same_email", "same_email")
                        for e in edges
                        if e.relationship == "same_email"
                    }:
                        continue
                    edge = RelationshipEdge(
                        source_id=accts[i].account_id,
                        source_type="account",
                        target_id=accts[j].account_id,
                        target_type="account",
                        relationship="same_domain",
                        evidence=f"shared domain: {domain}",
                        confidence=0.7,
                    )
                    if edge.canonical_key not in seen_keys:
                        seen_keys.add(edge.canonical_key)
                        edges.append(edge)

    for ws in workspaces:
        for plat in platforms:
            if ws.platform and ws.platform.lower() in plat.name.lower():
                edge = RelationshipEdge(
                    source_id=ws.workspace_id,
                    source_type="workspace",
                    target_id=plat.platform_id,
                    target_type="platform",
                    relationship="workspace_on_platform",
                    evidence=f"{ws.name} on {plat.name}",
                    confidence=0.85,
                )
                if edge.canonical_key not in seen_keys:
                    seen_keys.add(edge.canonical_key)
                    edges.append(edge)

    return edges


def plan_ingestion_lanes(
    platforms: list[DiscoveredPlatform],
    workspaces: list[DiscoveredWorkspace],
) -> list[IngestionLane]:
    """Plan ingestion strategies for discovered platforms."""
    lanes: list[IngestionLane] = []

    for plat in platforms:
        platform_key = plat.name.lower().replace(" ", "_")
        method = LANE_EXTRACTION_METHODS.get(platform_key, "foreground_cu_clipboard")
        safety = LANE_SAFETY_RATINGS.get(method, "caution")
        is_local = method in ("local_vault_read", "local_workspace_read", "local_git_read")

        canonical_likelihood = 0.2
        instance_likelihood = 0.8
        if plat.candidate_type == CANDIDATE_TYPE_CANONICAL:
            canonical_likelihood = 0.6
            instance_likelihood = 0.4

        lanes.append(
            IngestionLane(
                platform=plat.name,
                extraction_method=method,
                required_maturity=(
                    ActuatorMaturityLevel.L1_PROCESS_STARTED
                    if is_local
                    else ActuatorMaturityLevel.L3_FOREGROUND_FOCUSED
                ),
                canonical_likelihood=canonical_likelihood,
                instance_likelihood=instance_likelihood,
                replayable=is_local,
                requires_cu=not is_local,
                requires_foreground=not is_local,
                requires_founder_confirmation=True,
                requires_screenshot=not is_local,
                safety_rating=safety,
            )
        )

    for ws in workspaces:
        platform_key = ws.platform.lower().replace(" ", "_")
        method = LANE_EXTRACTION_METHODS.get(platform_key, "foreground_cu_clipboard")
        safety = LANE_SAFETY_RATINGS.get(method, "caution")
        is_local = method in ("local_vault_read", "local_workspace_read", "local_git_read")

        lanes.append(
            IngestionLane(
                platform=ws.platform,
                workspace=ws.name,
                extraction_method=method,
                required_maturity=(
                    ActuatorMaturityLevel.L1_PROCESS_STARTED
                    if is_local
                    else ActuatorMaturityLevel.L3_FOREGROUND_FOCUSED
                ),
                canonical_likelihood=0.3 if ws.candidate_type == CANDIDATE_TYPE_CANONICAL else 0.1,
                instance_likelihood=0.7 if ws.candidate_type == CANDIDATE_TYPE_CANONICAL else 0.9,
                replayable=is_local,
                requires_cu=not is_local,
                requires_foreground=not is_local,
                requires_founder_confirmation=True,
                requires_screenshot=not is_local,
                safety_rating=safety,
            )
        )

    return lanes


def compute_environment_maturity(evidence: EnvironmentMappingEvidence) -> str:
    """Compute environment mapping maturity level."""
    if evidence.is_dry_run:
        return "L0_NO_MAPPING"

    evidence_map = {
        "process_list": evidence.process_list_captured,
        "platforms_identified": evidence.platforms_identified,
        "accounts_linked": evidence.accounts_linked,
        "relationships_synthesized": evidence.has_relationships,
        "lanes_planned": evidence.has_lanes,
        "screenshots_captured": evidence.has_screenshots,
        "founder_confirmed": evidence.founder_confirmed,
    }

    reqs = ENVIRONMENT_MATURITY_REQUIREMENTS["L3_ENVIRONMENT_INTELLIGENCE"]
    if all(evidence_map.get(r, False) for r in reqs):
        return "L3_ENVIRONMENT_INTELLIGENCE"

    reqs = ENVIRONMENT_MATURITY_REQUIREMENTS["L2_PLATFORMS_IDENTIFIED"]
    if all(evidence_map.get(r, False) for r in reqs):
        return "L2_PLATFORMS_IDENTIFIED"

    reqs = ENVIRONMENT_MATURITY_REQUIREMENTS["L1_PROCESSES_ENUMERATED"]
    if all(evidence_map.get(r, False) for r in reqs):
        return "L1_PROCESSES_ENUMERATED"

    return "L0_NO_MAPPING"


def environment_maturity_ceiling(evidence: EnvironmentMappingEvidence) -> str:
    """Compute hard ceiling for environment mapping maturity."""
    if evidence.is_dry_run:
        return "L0_NO_MAPPING"
    if not evidence.has_screenshots:
        return "L1_PROCESSES_ENUMERATED"
    if not evidence.has_graph:
        return "L2_PLATFORMS_IDENTIFIED"
    if not evidence.has_relationships:
        return "L2_PLATFORMS_IDENTIFIED"
    if not evidence.has_lanes:
        return "L2_PLATFORMS_IDENTIFIED"
    if not evidence.founder_confirmed:
        return "L2_PLATFORMS_IDENTIFIED"
    return "L3_ENVIRONMENT_INTELLIGENCE"


def classify_environment_mapping(
    evidence: EnvironmentMappingEvidence,
) -> EnvironmentMappingProof:
    """Classify environment mapping into a maturity-aware proof."""
    if evidence.is_dry_run:
        return EnvironmentMappingProof(
            trace_id=evidence.trace_id,
            maturity_level="L0_NO_MAPPING",
            maturity_ceiling="L0_NO_MAPPING",
            escalation_blocked=True,
            escalation_reason="dry_run_always_L0",
            evidence=evidence,
        )

    raw_level = compute_environment_maturity(evidence)
    ceiling = environment_maturity_ceiling(evidence)

    level_order = [
        "L0_NO_MAPPING",
        "L1_PROCESSES_ENUMERATED",
        "L2_PLATFORMS_IDENTIFIED",
        "L3_ENVIRONMENT_INTELLIGENCE",
    ]
    raw_idx = level_order.index(raw_level) if raw_level in level_order else 0
    ceil_idx = level_order.index(ceiling) if ceiling in level_order else 0
    final_idx = min(raw_idx, ceil_idx)
    final_level = level_order[final_idx]

    missing = evidence.missing_evidence
    blocked = len(missing) > 0
    reason = ""
    if blocked:
        if not evidence.has_screenshots:
            reason = "no_screenshots"
        elif not evidence.has_graph:
            reason = "no_graph_generated"
        elif not evidence.has_relationships:
            reason = "no_relationship_synthesis"
        elif not evidence.has_lanes:
            reason = "no_lane_planning"
        elif not evidence.founder_confirmed:
            reason = "founder_confirmation_missing"
        else:
            reason = f"missing: {', '.join(missing)}"

    return EnvironmentMappingProof(
        trace_id=evidence.trace_id,
        maturity_level=final_level,
        maturity_ceiling=ceiling,
        escalation_blocked=blocked,
        escalation_reason=reason,
        evidence=evidence,
    )


def extract_mapping_evidence(
    relay_result: dict[str, Any],
    founder_confirmed: bool = False,
) -> EnvironmentMappingEvidence:
    """Extract environment mapping evidence from relay result."""
    discovery = relay_result.get("discovery_result", {})
    obs = relay_result.get("observed_desktop_state", {})

    process_list = discovery.get("processes", [])
    installed_apps = discovery.get("installed_apps", [])
    chrome_profiles = discovery.get("chrome_profiles", [])
    browser_sessions = discovery.get("browser_sessions", [])
    screenshots = discovery.get("screenshots", {})

    has_processes = len(process_list) > 0
    has_apps = len(installed_apps) > 0

    return EnvironmentMappingEvidence(
        process_list_captured=has_processes,
        platforms_identified=has_processes or has_apps,
        platform_count=len(process_list) + len(installed_apps),
        accounts_linked=len(chrome_profiles) > 0 or len(browser_sessions) > 0,
        account_count=len(chrome_profiles) + len(browser_sessions),
        workspaces_discovered=discovery.get("workspaces_discovered", False),
        workspace_count=len(discovery.get("workspaces", [])),
        relationships_synthesized=False,
        relationship_count=0,
        lanes_planned=False,
        lane_count=0,
        screenshots_captured=len(screenshots) > 0 or bool(obs.get("screenshot_path")),
        screenshot_count=len(screenshots),
        screenshot_paths=list(screenshots.get("paths", [])),
        screenshot_hashes=list(screenshots.get("hashes", [])),
        graph_generated=False,
        canonical_separated=False,
        founder_confirmed=founder_confirmed,
        desktop_unlocked=obs.get("desktop_unlocked", False),
        desktop_session_active=obs.get("active_user_session", False),
        is_dry_run=relay_result.get("dry_run", False),
        trace_id=relay_result.get("trace_id", ""),
        request_id=relay_result.get("request_id", ""),
        relay_node_id=relay_result.get("node_id", ""),
        relay_machine=relay_result.get("machine_name", ""),
    )


def build_environment_topology(
    relay_result: dict[str, Any],
) -> EnvironmentTopology:
    """Build complete topology from relay discovery result."""
    discovery = relay_result.get("discovery_result", {})

    process_list = discovery.get("processes", [])
    installed_apps = discovery.get("installed_apps", [])
    chrome_profiles = discovery.get("chrome_profiles", [])
    browser_sessions = discovery.get("browser_sessions", [])
    workspaces_raw = discovery.get("workspaces", [])

    platforms = extract_platforms_from_process_list(process_list)
    platforms.extend(extract_platforms_from_installed_apps(installed_apps))

    seen_names: set[str] = set()
    deduped: list[DiscoveredPlatform] = []
    for p in platforms:
        if p.name not in seen_names:
            seen_names.add(p.name)
            deduped.append(p)
    platforms = deduped

    accounts = extract_accounts_from_chrome_profiles(chrome_profiles)
    accounts.extend(extract_accounts_from_browser_sessions(browser_sessions))

    workspaces: list[DiscoveredWorkspace] = []
    for ws in workspaces_raw:
        workspaces.append(
            DiscoveredWorkspace(
                name=ws.get("name", ""),
                platform=ws.get("platform", ""),
                workspace_type=ws.get("type", ""),
                path=ws.get("path", ""),
                detected_via=ws.get("detected_via", "relay_discovery"),
                candidate_type=classify_platform_type(ws.get("name", ""), ws.get("platform", "")),
            )
        )

    relationships = synthesize_relationships(platforms, accounts, workspaces)
    ingestion_lanes = plan_ingestion_lanes(platforms, workspaces)

    return EnvironmentTopology(
        platforms=platforms,
        accounts=accounts,
        workspaces=workspaces,
        relationships=relationships,
        ingestion_lanes=ingestion_lanes,
    )


def build_full_environment_proof(
    relay_result: dict[str, Any],
    founder_confirmed: bool = False,
) -> EnvironmentMappingProof:
    """Build complete environment mapping proof with topology."""
    evidence = extract_mapping_evidence(relay_result, founder_confirmed)
    topology = build_environment_topology(relay_result)

    evidence.graph_generated = topology.platform_count > 0
    evidence.canonical_separated = True
    evidence.canonical_count = len(topology.canonical_candidates)
    evidence.instance_count = len(topology.instance_candidates)
    evidence.relationships_synthesized = topology.relationship_count > 0
    evidence.relationship_count = topology.relationship_count
    evidence.lanes_planned = topology.lane_count > 0
    evidence.lane_count = topology.lane_count

    proof = classify_environment_mapping(evidence)
    proof.topology = topology
    return proof


def persist_environment_mapping_proof(
    proof: EnvironmentMappingProof,
    base_dir: Path = Path(_ROOT),
) -> Path:
    """Persist environment mapping proof to disk."""
    proof_dir = base_dir / ENVIRONMENT_MAP_DIR
    proof_dir.mkdir(parents=True, exist_ok=True)
    path = proof_dir / f"{proof.proof_id}.json"
    path.write_text(json.dumps(proof.to_dict(), indent=2, default=str))
    return path


def send_explore_environment_request(
    timeout_seconds: int = 60,
) -> Any:
    """Send explore-environment request via relay transport."""
    from core.workstation.relay_execution_transport_v1 import send_and_wait

    request = {
        "request_id": f"REQ-W0-EXPLORE-ENV-{uuid.uuid4().hex[:8]}",
        "trace_id": f"W0-explore-env-{uuid.uuid4().hex[:12]}",
        "work_order_id": "WO-LOCAL-PILOT-EXPLORE-ENV-001",
        "action_type": "explore_environment",
        "environment_id": "local_windows_desktop",
        "no_mutation": True,
        "no_secret_capture": True,
        "dry_run": False,
        "timestamp": _now_iso(),
        "notes": [
            "Exploratory environment mapping ONLY",
            "No credential scraping",
            "No autonomous mutation",
            "No hidden scanning",
            "All discovery through visible process enumeration",
            "Screenshot proof REQUIRED",
            "Founder must physically confirm results",
        ],
    }
    return send_and_wait(request, timeout_seconds=timeout_seconds)
