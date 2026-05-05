"""
Tool Mastery Pack loader for Phase 96.5.

Tool Mastery is an internal layer of the Adapter Engine.
This module loads and parses skill files to build Tool Mastery Packs.

The Claude Code Best Practices Skill is classified as:
  ToolMasteryPack: Claude Code
It belongs inside the Claude Code Adapter Package as the mastery layer.

Does not execute or modify skills — only reads/parses text to extract
best practices, workflows, failure modes, and quality standards.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


_DEFAULT_SEARCH_ROOTS = [
    "/opt/OS/.claude/skills/",
    "/opt/OS/.claude/rules/",
    "/opt/OS/.claude/commands/",
    "/opt/OS/docs/operations/",
    "/opt/OS/skills/tools/",
]

_SKILL_FILENAMES = [
    "claude-code-cli.md",
    "claude-code-best-practices.md",
    "coding-standards.md",
]

_ADAPTER_RELEVANT_KEYWORDS = [
    "before any change",
    "before declaring done",
    "before any deploy",
    "never do",
    "risk class",
    "import check",
    "test pass",
    "protocol",
    "hardcode",
    "secret",
    "credential",
    "neon registration",
]


@dataclass
class AdapterBestPracticesPolicy:
    """Policy extracted from the Claude Code best-practices skill."""

    source_file: str = ""
    rules: list[str] = field(default_factory=list)
    pre_change_checks: list[str] = field(default_factory=list)
    pre_done_checks: list[str] = field(default_factory=list)
    pre_deploy_checks: list[str] = field(default_factory=list)
    never_do: list[str] = field(default_factory=list)
    risk_classes: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "source_file": self.source_file,
            "rules": self.rules,
            "pre_change_checks": self.pre_change_checks,
            "pre_done_checks": self.pre_done_checks,
            "pre_deploy_checks": self.pre_deploy_checks,
            "never_do": self.never_do,
            "risk_classes": self.risk_classes,
        }


@dataclass
class MergedAdapterPolicy:
    """Merged policy from skill + default quality gate."""

    skill_rules: list[str] = field(default_factory=list)
    default_rules: list[str] = field(default_factory=list)
    merged_rules: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "skill_rules_count": len(self.skill_rules),
            "default_rules_count": len(self.default_rules),
            "merged_rules_count": len(self.merged_rules),
        }


def locate_claude_code_best_practices_skill(
    search_roots: list[str] | None = None,
) -> str | None:
    """Locate the Claude Code best-practices skill file."""
    roots = search_roots or _DEFAULT_SEARCH_ROOTS
    for root in roots:
        root_path = Path(root)
        if not root_path.exists():
            continue
        for filename in _SKILL_FILENAMES:
            candidate = root_path / filename
            if candidate.exists():
                return str(candidate)
        for candidate in root_path.rglob("*.md"):
            try:
                text = candidate.read_text(encoding="utf-8", errors="ignore")[:500].lower()
                if "best practice" in text or "claude code" in text and "skill" in text:
                    return str(candidate)
            except OSError:
                continue
    return None


def load_best_practices_skill(path: str) -> str:
    """Load the skill file content."""
    return Path(path).read_text(encoding="utf-8", errors="ignore")


def extract_adapter_relevant_rules(skill_text: str) -> list[str]:
    """Extract adapter-relevant rules from skill text."""
    rules: list[str] = []
    lines = skill_text.split("\n")
    for line in lines:
        lower = line.lower().strip()
        if not lower or lower.startswith("#"):
            continue
        for keyword in _ADAPTER_RELEVANT_KEYWORDS:
            if keyword in lower:
                rules.append(line.strip())
                break
    return rules


def build_adapter_policy_from_skill(skill_text: str) -> AdapterBestPracticesPolicy:
    """Build a structured policy from skill text."""
    rules = extract_adapter_relevant_rules(skill_text)

    pre_change: list[str] = []
    pre_done: list[str] = []
    pre_deploy: list[str] = []
    never: list[str] = []
    risk: list[str] = []

    in_section = ""
    for line in skill_text.split("\n"):
        lower = line.lower().strip()
        if "before any change" in lower:
            in_section = "pre_change"
        elif "before declaring done" in lower:
            in_section = "pre_done"
        elif "before any deploy" in lower:
            in_section = "pre_deploy"
        elif "never do" in lower:
            in_section = "never"
        elif "risk class" in lower:
            in_section = "risk"
        elif lower.startswith("##"):
            in_section = ""

        if in_section and line.strip().startswith(("-", "1", "2", "3")):
            target = {
                "pre_change": pre_change,
                "pre_done": pre_done,
                "pre_deploy": pre_deploy,
                "never": never,
                "risk": risk,
            }.get(in_section)
            if target is not None:
                target.append(line.strip())

    return AdapterBestPracticesPolicy(
        rules=rules,
        pre_change_checks=pre_change,
        pre_done_checks=pre_done,
        pre_deploy_checks=pre_deploy,
        never_do=never,
        risk_classes=risk,
    )


def build_tool_mastery_pack_from_skill(
    adapter_id: str,
    tool_name: str,
    skill_path: str,
) -> Any:
    """Build a ToolMasteryPack from a skill file.

    This is the bridge between skill files on disk and the Adapter Engine's
    Tool Mastery layer. The returned pack becomes part of the adapter package.
    """
    from eos_ai.substrate.adapter_engine_contracts import ToolMasteryPack

    skill_text = load_best_practices_skill(skill_path)
    policy = build_adapter_policy_from_skill(skill_text)

    return ToolMasteryPack(
        adapter_id=adapter_id,
        tool_name=tool_name,
        best_practices=policy.rules,
        common_workflows=policy.pre_change_checks
        + policy.pre_done_checks
        + policy.pre_deploy_checks,
        failure_modes=policy.never_do,
        edge_cases=[],
        quality_standards=policy.risk_classes,
        skill_file_ref=skill_path,
    )


def merge_skill_policy_with_adapter_quality_gate(
    skill_policy: AdapterBestPracticesPolicy,
    default_rules: list[str] | None = None,
) -> MergedAdapterPolicy:
    """Merge skill-derived policy with default quality gate rules."""
    defaults = default_rules or [
        "adapter must have contract",
        "adapter must have tests",
        "adapter must have safety policy",
        "adapter must have no-secret policy",
        "adapter must have documentation",
    ]
    merged = list(set(skill_policy.rules + defaults))
    return MergedAdapterPolicy(
        skill_rules=skill_policy.rules,
        default_rules=defaults,
        merged_rules=merged,
    )
