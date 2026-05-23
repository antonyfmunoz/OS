"""Natural Language Tool Mastery Resolver.

Detects tools, capabilities, and runtimes from natural language text
and resolves the required Tool Mastery Packs. No slash commands needed.

TME is a UMH substrate subsystem. EOS is one platform consumer.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any
import os
_ROOT = os.environ.get("UMH_ROOT") or os.environ.get("OS_ROOT") or os.environ.get("EOS_ROOT") or "/opt/OS"



KNOWN_TOOLS: dict[str, list[str]] = {
    "claude_code": ["claude code", "claude-code", "cc"],
    "codex": ["codex", "openai codex"],
    "cursor": ["cursor"],
    "google_docs": ["google docs", "gdocs", "google document"],
    "google_drive": ["google drive", "gdrive"],
    "google_sheets": ["google sheets", "gsheets"],
    "google_workspace": ["google workspace", "gws", "gsuite", "g suite"],
    "github": ["github", "gh"],
    "discord": ["discord"],
    "notion": ["notion"],
    "neon_postgres": ["neon", "neon postgres", "postgres", "postgresql", "pg"],
    "mcp": ["mcp", "model context protocol"],
    "tmux": ["tmux"],
    "wsl": ["wsl", "windows subsystem"],
    "docker": ["docker"],
    "anthropic_api": ["anthropic api", "anthropic", "claude api"],
    "gemini": ["gemini", "google gemini"],
    "ollama": ["ollama"],
    "apify": ["apify"],
    "stripe": ["stripe"],
    "sendgrid": ["sendgrid"],
    "slack": ["slack"],
    "tailscale": ["tailscale"],
    "vite": ["vite"],
    "drizzle_orm": ["drizzle", "drizzle orm"],
    "playwright": ["playwright"],
}

CAPABILITY_MAP: dict[str, list[str]] = {
    "document_ingestion": ["ingest docs", "ingest documents", "document ingestion", "source ingestion"],
    "google_docs_tab_aware_extraction": [
        "extract google docs",
        "google docs extraction",
        "tab-aware extraction",
        "extract tabs",
        "google docs tabs",
    ],
    "software_engineering": ["edit code", "fix code", "write code", "refactor", "implement"],
    "test_execution": ["run tests", "test execution", "execute tests", "pytest", "unittest"],
    "computer_use": ["browse", "use the computer", "computer use", "screen", "screenshot"],
    "deployment": ["deploy", "deployment", "ship", "release"],
    "database_operations": ["query database", "db operations", "sql", "migration"],
}

RUNTIME_MAP: dict[str, list[str]] = {
    "vps": ["vps", "server", "remote server"],
    "tmux": ["tmux", "tmux session"],
    "docker": ["docker", "container", "containerized"],
    "wsl": ["wsl", "windows subsystem"],
    "local_desktop": ["local", "desktop", "workstation"],
    "claude_code_session": ["claude code session", "cc session"],
}


@dataclass
class ResolvedToolMention:
    raw_mention: str
    normalized_tool_name: str
    confidence: float = 0.0
    detected_from: str = "text_match"
    reason: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "raw_mention": self.raw_mention,
            "normalized_tool_name": self.normalized_tool_name,
            "confidence": self.confidence,
            "detected_from": self.detected_from,
            "reason": self.reason,
        }


@dataclass
class ResolvedCapabilityMention:
    capability_name: str
    confidence: float = 0.0
    reason: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "capability_name": self.capability_name,
            "confidence": self.confidence,
            "reason": self.reason,
        }


@dataclass
class ResolvedMasteryPack:
    pack_id: str
    tool_name: str
    pack_path: str = ""
    scope: str = "tool"
    required: bool = True
    reason: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "pack_id": self.pack_id,
            "tool_name": self.tool_name,
            "pack_path": self.pack_path,
            "scope": self.scope,
            "required": self.required,
            "reason": self.reason,
        }


@dataclass
class ToolMasteryResolution:
    user_intent: str
    detected_tools: list[ResolvedToolMention] = field(default_factory=list)
    detected_capabilities: list[ResolvedCapabilityMention] = field(default_factory=list)
    detected_runtimes: list[str] = field(default_factory=list)
    required_mastery_packs: list[ResolvedMasteryPack] = field(default_factory=list)
    adapter_package_candidates: list[str] = field(default_factory=list)
    governance_notes: list[str] = field(default_factory=list)
    confidence: float = 0.0
    needs_clarification: bool = False
    notes: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "user_intent": self.user_intent,
            "detected_tools": [t.to_dict() for t in self.detected_tools],
            "detected_capabilities": [c.to_dict() for c in self.detected_capabilities],
            "detected_runtimes": self.detected_runtimes,
            "required_mastery_packs": [p.to_dict() for p in self.required_mastery_packs],
            "adapter_package_candidates": self.adapter_package_candidates,
            "governance_notes": self.governance_notes,
            "confidence": self.confidence,
            "needs_clarification": self.needs_clarification,
            "notes": self.notes,
        }


def detect_tool_mentions(
    text: str,
    known_tools: dict[str, list[str]] | None = None,
) -> list[ResolvedToolMention]:
    tools = known_tools or KNOWN_TOOLS
    lower = text.lower()
    results: list[ResolvedToolMention] = []
    seen: set[str] = set()

    sorted_entries = []
    for slug, aliases in tools.items():
        for alias in aliases:
            sorted_entries.append((slug, alias))
    sorted_entries.sort(key=lambda x: len(x[1]), reverse=True)

    for slug, alias in sorted_entries:
        if slug in seen:
            continue
        pattern = r"\b" + re.escape(alias) + r"\b"
        match = re.search(pattern, lower)
        if match:
            seen.add(slug)
            results.append(
                ResolvedToolMention(
                    raw_mention=match.group(0),
                    normalized_tool_name=slug,
                    confidence=0.9,
                    detected_from="text_match",
                    reason=f"matched alias '{alias}'",
                )
            )

    return results


def detect_capability_mentions(text: str) -> list[ResolvedCapabilityMention]:
    lower = text.lower()
    results: list[ResolvedCapabilityMention] = []
    seen: set[str] = set()

    for cap_name, phrases in CAPABILITY_MAP.items():
        if cap_name in seen:
            continue
        for phrase in phrases:
            if phrase in lower:
                seen.add(cap_name)
                results.append(
                    ResolvedCapabilityMention(
                        capability_name=cap_name,
                        confidence=0.85,
                        reason=f"matched phrase '{phrase}'",
                    )
                )
                break

    return results


def _detect_runtimes(text: str) -> list[str]:
    lower = text.lower()
    runtimes: list[str] = []
    for runtime, phrases in RUNTIME_MAP.items():
        for phrase in phrases:
            if phrase in lower:
                runtimes.append(runtime)
                break
    return runtimes


def infer_required_mastery_packs(
    text: str,
    known_tools: dict[str, list[str]] | None = None,
    active_context: Any | None = None,
) -> list[ResolvedMasteryPack]:
    tools = detect_tool_mentions(text, known_tools)
    capabilities = detect_capability_mentions(text)

    packs: list[ResolvedMasteryPack] = []
    seen: set[str] = set()

    for tool in tools:
        if tool.normalized_tool_name not in seen:
            seen.add(tool.normalized_tool_name)
            packs.append(
                ResolvedMasteryPack(
                    pack_id=f"pack:{tool.normalized_tool_name}",
                    tool_name=tool.normalized_tool_name,
                    pack_path=f"{_ROOT}/skills/tools/{tool.normalized_tool_name}/SKILL.md",
                    scope="tool",
                    required=True,
                    reason=f"tool '{tool.raw_mention}' detected in user intent",
                )
            )

    for cap in capabilities:
        cap_pack_id = f"cap:{cap.capability_name}"
        if cap_pack_id not in seen:
            seen.add(cap_pack_id)
            packs.append(
                ResolvedMasteryPack(
                    pack_id=cap_pack_id,
                    tool_name=cap.capability_name,
                    scope="capability",
                    required=False,
                    reason=f"capability '{cap.capability_name}' detected",
                )
            )

    return packs


def resolve_mastery_for_task(
    text: str,
    known_tools: dict[str, list[str]] | None = None,
    active_context: Any | None = None,
) -> ToolMasteryResolution:
    tools = detect_tool_mentions(text, known_tools)
    capabilities = detect_capability_mentions(text)
    runtimes = _detect_runtimes(text)
    packs = infer_required_mastery_packs(text, known_tools, active_context)

    confidence = 0.0
    if tools:
        confidence = max(t.confidence for t in tools)
    elif capabilities:
        confidence = max(c.confidence for c in capabilities)

    needs_clarification = len(tools) == 0 and len(capabilities) == 0

    return ToolMasteryResolution(
        user_intent=text,
        detected_tools=tools,
        detected_capabilities=capabilities,
        detected_runtimes=runtimes,
        required_mastery_packs=packs,
        confidence=confidence,
        needs_clarification=needs_clarification,
    )


def should_reuse_active_tool_context(
    text: str,
    active_context: Any | None,
) -> bool:
    if active_context is None:
        return False
    new_tools = detect_tool_mentions(text)
    if not new_tools:
        return True
    active_tools = getattr(active_context, "active_tools", [])
    new_tool_names = {t.normalized_tool_name for t in new_tools}
    if new_tool_names.issubset(set(active_tools)):
        return True
    return False


def explain_mastery_resolution(resolution: ToolMasteryResolution) -> str:
    parts: list[str] = []
    if resolution.detected_tools:
        tool_names = [t.normalized_tool_name for t in resolution.detected_tools]
        parts.append(f"Tools detected: {', '.join(tool_names)}")
    if resolution.detected_capabilities:
        cap_names = [c.capability_name for c in resolution.detected_capabilities]
        parts.append(f"Capabilities: {', '.join(cap_names)}")
    if resolution.detected_runtimes:
        parts.append(f"Runtimes: {', '.join(resolution.detected_runtimes)}")
    if resolution.required_mastery_packs:
        pack_names = [p.tool_name for p in resolution.required_mastery_packs]
        parts.append(f"Required mastery packs: {', '.join(pack_names)}")
    if resolution.needs_clarification:
        parts.append("No tools or capabilities detected — clarification needed")
    return "; ".join(parts) if parts else "No resolution"
