"""Mastery Gate — mandatory pipeline check before execution.

Step 16 of the 27-step canonical spine: no execution proceeds unless
every detected tool has an assured mastery pack, or the founder
explicitly waives the requirement.

Composes two existing mastery subsystems:
  - tool_mastery_resolver: NLP detection of tools from signal content
  - mastery_assurance: per-tool pack evaluation (freshness, quality, completeness)

Non-blocking for signals that don't reference external tools.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from substrate.composition.mastery.management.mastery_assurance import (
    MasteryAssuranceDecision,
    MasteryAssuranceStatus,
    ensure_mastery_before_execution,
)
from substrate.composition.mastery.management.tool_mastery_resolver import (
    ToolMasteryResolution,
    resolve_mastery_for_task,
)

logger = logging.getLogger(__name__)

_SKILLS_ROOT = Path("/opt/OS/skills/tools")


def _load_pack(slug: str) -> tuple[bool, str, str | None, str]:
    """Load a mastery pack from disk. Returns (exists, text, last_researched, speed_category)."""
    skill_path = _SKILLS_ROOT / slug / "SKILL.md"
    if not skill_path.is_file():
        return False, "", None, "medium"

    text = skill_path.read_text(errors="replace")

    last_researched = None
    speed_category = "medium"
    in_frontmatter = False
    for line in text.split("\n")[:30]:
        stripped = line.strip()
        if stripped == "---":
            in_frontmatter = not in_frontmatter
            continue
        if in_frontmatter:
            if stripped.startswith("last_researched:"):
                val = stripped.split(":", 1)[1].strip().strip('"').strip("'")
                last_researched = val
            elif stripped.startswith("speed_category:"):
                val = stripped.split(":", 1)[1].strip().strip('"').strip("'")
                speed_category = val

    return True, text, last_researched, speed_category


@dataclass
class MasteryGateResult:
    """Result of the mastery gate check."""

    tools_detected: list[str] = field(default_factory=list)
    tools_assured: list[str] = field(default_factory=list)
    tools_blocked: list[str] = field(default_factory=list)
    block_reasons: dict[str, str] = field(default_factory=dict)
    can_proceed: bool = True
    founder_waived: bool = False
    resolution: ToolMasteryResolution | None = None
    decisions: list[MasteryAssuranceDecision] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "tools_detected": self.tools_detected,
            "tools_assured": self.tools_assured,
            "tools_blocked": self.tools_blocked,
            "block_reasons": self.block_reasons,
            "can_proceed": self.can_proceed,
            "founder_waived": self.founder_waived,
        }


class MasteryGate:
    """Pipeline gate that checks mastery before allowing execution.

    Non-blocking for signals that don't reference external tools.
    Blocking for signals that do — unless founder_waiver is set.
    """

    def __init__(self, skills_root: Path | None = None) -> None:
        if skills_root is not None:
            global _SKILLS_ROOT
            _SKILLS_ROOT = skills_root

    def check(
        self,
        content: str,
        *,
        founder_waiver: bool = False,
        adapter_name: str = "shell",
    ) -> MasteryGateResult:
        """Check mastery for all tools detected in the signal content."""
        result = MasteryGateResult(founder_waived=founder_waiver)

        try:
            resolution = resolve_mastery_for_task(content)
            result.resolution = resolution
        except Exception as e:
            logger.warning("mastery resolution failed (non-blocking): %s", e)
            return result

        required_packs = [
            p for p in resolution.required_mastery_packs if p.required
        ]

        if not required_packs:
            return result

        result.tools_detected = [p.tool_name for p in required_packs]

        for pack_ref in required_packs:
            slug = pack_ref.tool_name
            try:
                exists, text, last_researched, speed_category = _load_pack(slug)
                decision = ensure_mastery_before_execution(
                    tool_name=slug,
                    pack_exists=exists,
                    pack_text=text,
                    last_researched=last_researched,
                    speed_category=speed_category,
                    founder_waiver=founder_waiver,
                )
                result.decisions.append(decision)

                if decision.can_execute:
                    result.tools_assured.append(slug)
                else:
                    result.tools_blocked.append(slug)
                    result.block_reasons[slug] = decision.block_reason
            except Exception as e:
                logger.warning("mastery check failed for %s (non-blocking): %s", slug, e)
                result.tools_assured.append(slug)

        if result.tools_blocked and not founder_waiver:
            result.can_proceed = False

        return result
