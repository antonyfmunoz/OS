"""
ClaudeSkillRegistry — tracks all .claude/skills files, syncs them to Neon,
and flags skills that need reviewing against their source documentation.

Every skill Claude Code uses to build and operate EOS lives here:
  - Stored in Neon so agents can reference them at runtime
  - Tagged with source URL for auto-update monitoring
  - Checked every 7 days against source docs via world_pulse

Usage:
    from eos_ai.claude_skill_registry import ClaudeSkillRegistryManager
    from eos_ai.context import load_context_from_env
    ctx = load_context_from_env()
    csrm = ClaudeSkillRegistryManager()
    csrm.sync_to_neon(ctx)
    print(csrm.format_status())
"""

import os
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

_DEFAULT_ROOT = os.environ.get("UMH_ROOT") or os.environ.get("OS_ROOT") or os.environ.get("EOS_ROOT") or "/opt/OS"


# ─── Skill dataclass ──────────────────────────────────────────────────────────


@dataclass
class ClaudeSkill:
    id: str
    name: str
    file_path: str
    category: str
    source_url: str  # official docs URL — empty for internal skills
    last_updated: datetime = None
    version: int = 1
    description: str = ""
    auto_update: bool = True


# ─── Registry ─────────────────────────────────────────────────────────────────

CLAUDE_SKILL_REGISTRY: dict[str, ClaudeSkill] = {
    # ── SYSTEM SKILLS ─────────────────────────────────────────────────────────
    "browser-control": ClaudeSkill(
        id="browser-control",
        name="Browser Control",
        file_path=".claude/skills/browser-control.md",
        category="system",
        source_url="",
        auto_update=False,
    ),
    # ── WORKFLOW SKILLS ───────────────────────────────────────────────────────
    "new-agent": ClaudeSkill(
        id="new-agent",
        name="New Agent Protocol",
        file_path=".claude/skills/new-agent.md",
        category="workflow",
        source_url="",
        auto_update=False,
    ),
    "new-skill": ClaudeSkill(
        id="new-skill",
        name="New Skill Protocol",
        file_path=".claude/skills/new-skill.md",
        category="workflow",
        source_url="",
        auto_update=False,
    ),
    "new-primitive": ClaudeSkill(
        id="new-primitive",
        name="New Primitive Protocol",
        file_path=".claude/skills/new-primitive.md",
        category="workflow",
        source_url="",
        auto_update=False,
    ),
    "debug-agent": ClaudeSkill(
        id="debug-agent",
        name="Debug Agent Protocol",
        file_path=".claude/skills/debug-agent.md",
        category="workflow",
        source_url="",
        auto_update=False,
    ),
    "deploy-service": ClaudeSkill(
        id="deploy-service",
        name="Deploy Service Protocol",
        file_path=".claude/skills/deploy-service.md",
        category="workflow",
        source_url="",
        auto_update=False,
    ),
    # ── TOOL SKILLS (auto-update from official docs) ──────────────────────────
    "notion-api": ClaudeSkill(
        id="notion-api",
        name="Notion API",
        file_path=".claude/skills/notion-api.md",
        category="tool",
        source_url="https://developers.notion.com/docs",
        auto_update=True,
    ),
    "discord-admin": ClaudeSkill(
        id="discord-admin",
        name="Discord Admin",
        file_path=".claude/skills/discord-admin.md",
        category="tool",
        source_url="https://docs.pycord.dev/en/stable/",
        auto_update=True,
    ),
    "groq-api": ClaudeSkill(
        id="groq-api",
        name="Groq API",
        file_path=".claude/skills/groq-api.md",
        category="tool",
        source_url="https://console.groq.com/docs/openai",
        auto_update=True,
    ),
    "neon-db": ClaudeSkill(
        id="neon-db",
        name="Neon PostgreSQL",
        file_path=".claude/skills/neon-db.md",
        category="tool",
        source_url="https://neon.tech/docs",
        auto_update=True,
    ),
    "claude-code-cli": ClaudeSkill(
        id="claude-code-cli",
        name="Claude Code CLI",
        file_path=".claude/skills/claude-code-cli.md",
        category="tool",
        source_url="https://docs.anthropic.com/en/docs/claude-code/overview",
        auto_update=True,
    ),
}


# ─── Manager ──────────────────────────────────────────────────────────────────


class ClaudeSkillRegistryManager:
    def __init__(self, base_path: str = _DEFAULT_ROOT):
        self.base_path = Path(base_path)
        self.registry = CLAUDE_SKILL_REGISTRY

    # ── Queries ───────────────────────────────────────────────────────────────

    def get_all(self) -> list[ClaudeSkill]:
        return list(self.registry.values())

    def get_by_category(self, category: str) -> list[ClaudeSkill]:
        return [s for s in self.registry.values() if s.category == category]

    def get_auto_update_skills(self) -> list[ClaudeSkill]:
        return [s for s in self.registry.values() if s.auto_update and s.source_url]

    # ── File I/O ──────────────────────────────────────────────────────────────

    def read_skill(self, skill_id: str) -> str:
        skill = self.registry.get(skill_id)
        if not skill:
            return ""
        path = self.base_path / skill.file_path
        if path.exists():
            return path.read_text()
        return ""

    def update_skill(self, skill_id: str, new_content: str) -> bool:
        skill = self.registry.get(skill_id)
        if not skill:
            return False
        path = self.base_path / skill.file_path
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(new_content)
        skill.last_updated = datetime.now()
        print(f"[SkillRegistry] Updated: {skill_id}")
        return True

    # ── Neon sync ─────────────────────────────────────────────────────────────

    def sync_to_neon(self, ctx) -> int:
        """
        Sync all skills that have content to Neon database.
        Skills without files are skipped silently.
        Returns count of skills synced.
        """
        from eos_ai.db import get_conn
        import uuid as _uuid

        synced = 0
        try:
            with get_conn(ctx.org_id) as cur:
                for skill_id, skill in self.registry.items():
                    content = self.read_skill(skill_id)
                    if not content:
                        continue
                    cur.execute(
                        """
                        INSERT INTO skills (
                            id, org_id, name, content, version)
                        VALUES (%s, %s, %s, %s, %s)
                        ON CONFLICT (org_id, name)
                        DO UPDATE SET
                            content = EXCLUDED.content,
                            version = EXCLUDED.version
                        """,
                        (
                            str(_uuid.uuid4()),
                            ctx.org_id,
                            skill_id,
                            content,
                            int(skill.version),
                        ),
                    )
                    synced += 1
            print(f"[SkillRegistry] Synced {synced} Claude skills to Neon")
        except Exception as e:
            print(f"[SkillRegistry] Sync failed: {e}")
        return synced

    # ── Update check ──────────────────────────────────────────────────────────

    def check_for_updates(self) -> list[str]:
        """
        Return list of skill IDs that need review against their source docs.
        Criteria: never updated OR last updated > 7 days ago.
        World pulse handles the actual doc fetching.
        """
        needs_update: list[str] = []
        for skill in self.get_auto_update_skills():
            if not skill.last_updated:
                needs_update.append(skill.id)
                continue
            days_since = (datetime.now() - skill.last_updated).days
            if days_since > 7:
                needs_update.append(skill.id)
        return needs_update

    # ── Status ────────────────────────────────────────────────────────────────

    def format_status(self) -> str:
        lines = ["CLAUDE SKILL REGISTRY:"]
        for category in ("system", "workflow", "tool"):
            skills = self.get_by_category(category)
            if not skills:
                continue
            lines.append(f"\n{category.upper()} SKILLS:")
            for s in skills:
                updated = s.last_updated.strftime("%Y-%m-%d") if s.last_updated else "never"
                auto = "🔄" if s.auto_update else "📌"
                exists = "✓" if (self.base_path / s.file_path).exists() else "✗"
                lines.append(f"  {auto} [{exists}] {s.name} (updated: {updated})")
        return "\n".join(lines)
