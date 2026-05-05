"""
Shared helpers for Tool Mastery Engine system scripts.

One place for:
- Skill directory discovery
- Robust YAML frontmatter parsing (no fragile regex)
- Canonical paths and section lists

Imported by sync_skills_to_neon.py, verify_tool_skill.py,
check_skill_staleness.py, build_skill_graph.py, query_skills.py.
"""

from __future__ import annotations

import sys
from dataclasses import dataclass, field
from datetime import date, datetime
from pathlib import Path
from typing import Any

import yaml

TOOLS_DIR = Path("/opt/OS/skills/tools")
META_TME_DIR = Path("/opt/OS/skills/meta/tool_mastery_engine")

# Best-practices sections required by TME v3.0
REQUIRED_BP_SECTIONS = [
    "Authentication",
    "Core Operations",
    "Pagination",
    "Rate Limits",
    "Error Codes",
    "SDK Idioms",
    "Anti-Patterns",
    "Data Model",
    "Webhooks",
    "Limits",
    "Cost Model",
    "Version Pinning",
    "Design Intent",
    "Problem-Solution Map",
    "Operational Behavior",
    "Ecosystem Position",
    "Trajectory",
    "Conceptual Model",
    "Industry Expert",
]

REQUIRED_SKILL_SECTIONS = ["Authentication", "Gotchas"]
MIN_SKILL_CHARS = 500
MIN_BP_CHARS = 2000

# Freshness windows (days) by speed_category
# fast = AI/ML tools, rapidly evolving APIs (daily check)
# medium = SaaS APIs, frameworks with monthly releases (every 3 days)
# stable = infrastructure, runtimes, mature tools (weekly)
# slow = desktop software, creative tools (biweekly)
FRESHNESS_WINDOWS = {"fast": 14, "medium": 45, "stable": 90, "slow": 120}
DEFAULT_FRESHNESS_WINDOW = 45
NEAR_STALE_FRACTION = 0.8  # flag at 80% of window


@dataclass
class SkillRecord:
    slug: str
    path: Path
    skill_md: Path
    best_practices_md: Path | None
    frontmatter: dict[str, Any] = field(default_factory=dict)
    skill_body: str = ""
    bp_body: str = ""
    parse_error: str | None = None

    @property
    def exists(self) -> bool:
        return self.skill_md.is_file()

    @property
    def title(self) -> str:
        # Prefer H1 after frontmatter, else slug
        for line in self.skill_body.splitlines():
            s = line.strip()
            if s.startswith("# "):
                return s[2:].strip()
        return self.slug

    @property
    def description(self) -> str:
        return str(self.frontmatter.get("description", "")).strip()

    @property
    def last_researched(self) -> date | None:
        val = self.frontmatter.get("last_researched")
        if val is None:
            return None
        if isinstance(val, date):
            return val
        try:
            return datetime.strptime(str(val).strip(), "%Y-%m-%d").date()
        except Exception:
            return None

    @property
    def speed_category(self) -> str:
        return str(self.frontmatter.get("speed_category", "")).strip() or "medium"

    @property
    def api_version(self) -> str:
        return str(self.frontmatter.get("api_version", "")).strip()

    @property
    def sdk_version(self) -> str:
        return str(self.frontmatter.get("sdk_version", "")).strip()


def _split_frontmatter(text: str) -> tuple[dict[str, Any], str, str | None]:
    """
    Return (frontmatter_dict, body, error).
    Uses a real YAML parser — not regex — so multi-line descriptions,
    quoted strings, and nested keys all work correctly.
    """
    if not text.startswith("---"):
        return {}, text, None
    # Find closing fence
    lines = text.splitlines()
    end_idx = None
    for i in range(1, len(lines)):
        if lines[i].strip() == "---":
            end_idx = i
            break
    if end_idx is None:
        return {}, text, "frontmatter fence not closed"
    raw_yaml = "\n".join(lines[1:end_idx])
    body = "\n".join(lines[end_idx + 1 :])
    try:
        fm = yaml.safe_load(raw_yaml) or {}
        if not isinstance(fm, dict):
            return {}, body, f"frontmatter root is {type(fm).__name__}, expected dict"
        return fm, body, None
    except yaml.YAMLError as e:
        return {}, body, f"yaml parse error: {e}"


def load_skill(slug: str, tools_dir: Path = TOOLS_DIR) -> SkillRecord:
    path = tools_dir / slug
    skill_md = path / "SKILL.md"
    bp_md = path / "references" / "best_practices.md"
    rec = SkillRecord(
        slug=slug,
        path=path,
        skill_md=skill_md,
        best_practices_md=bp_md if bp_md.is_file() else None,
    )
    if not skill_md.is_file():
        rec.parse_error = "SKILL.md missing"
        return rec
    try:
        text = skill_md.read_text(encoding="utf-8")
    except Exception as e:
        rec.parse_error = f"read error: {e}"
        return rec
    fm, body, err = _split_frontmatter(text)
    rec.frontmatter = fm
    rec.skill_body = body
    if err:
        rec.parse_error = err
    if rec.best_practices_md and rec.best_practices_md.is_file():
        try:
            rec.bp_body = rec.best_practices_md.read_text(encoding="utf-8")
        except Exception as e:
            rec.parse_error = (rec.parse_error or "") + f"; bp read: {e}"
    return rec


def all_skill_slugs(tools_dir: Path = TOOLS_DIR) -> list[str]:
    if not tools_dir.is_dir():
        return []
    return sorted(
        d.name
        for d in tools_dir.iterdir()
        if d.is_dir() and (d / "SKILL.md").is_file()
    )


def load_all_skills(tools_dir: Path = TOOLS_DIR) -> list[SkillRecord]:
    return [load_skill(s, tools_dir) for s in all_skill_slugs(tools_dir)]


_SECTION_LINE_RE = None


def section_present(body: str, heading: str) -> bool:
    """
    Return True if `body` contains an H2/H3 heading whose visible text
    equals `heading`, ignoring:
      - leading `## ` / `### ` depth
      - optional `N.` / `N)` numbering
      - trailing punctuation and any text after the required name
    Matches case-insensitively. This is tolerant of real-world
    authoring variance ("## 1. Authentication", "### Authentication:",
    "## Authentication (Setup)").
    """
    import re

    global _SECTION_LINE_RE
    if _SECTION_LINE_RE is None:
        _SECTION_LINE_RE = re.compile(r"^\s{0,3}#{2,3}\s+(.*?)\s*$")
    target = heading.strip().lower()
    for line in body.splitlines():
        m = _SECTION_LINE_RE.match(line)
        if not m:
            continue
        text = m.group(1)
        # Strip leading numbering like "1.", "12)", "1 -", "Section 1:"
        text = re.sub(r"^(?:section\s+)?\d+[\.\)\-:]\s*", "", text, flags=re.IGNORECASE).strip().lower()
        if text == target or text.startswith(target + " ") or text.startswith(
            target + ":"
        ) or text.startswith(target + "(") or text.startswith(target + "—"):
            return True
    return False


def days_since(d: date, today: date | None = None) -> int:
    today = today or date.today()
    return (today - d).days


def freshness_window(speed: str) -> int:
    return FRESHNESS_WINDOWS.get(speed, DEFAULT_FRESHNESS_WINDOW)


def eprint(*args: Any, **kwargs: Any) -> None:
    print(*args, file=sys.stderr, **kwargs)
