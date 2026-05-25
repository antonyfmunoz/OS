"""Base department agent with skill execution, permission tiers, and governance integration."""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, field
from typing import Any, Callable

from substrate.types import PermissionTier, required_tier_for_action

logger = logging.getLogger(__name__)


@dataclass
class SkillResult:
    success: bool
    output: Any = None
    error: str = ""
    action_type: str = ""
    tier_used: str = ""


@dataclass
class AgentSkill:
    name: str
    action_type: str
    description: str
    handler: Callable[..., SkillResult]
    min_tier: PermissionTier = PermissionTier.READ


class DepartmentAgent:
    """Base class for EOS department agents with skill execution and tier enforcement."""

    DEPARTMENT: str = ""
    PERMISSION_TIER: PermissionTier = PermissionTier.EXECUTE

    def __init__(self, org_id: str = "", venture_id: str = "") -> None:
        self._org_id = org_id
        self._venture_id = venture_id
        self._skills: dict[str, AgentSkill] = {}
        self._register_skills()
        self._register_browser_skills()

    def _register_skills(self) -> None:
        """Override in subclass to register skills via _add_skill()."""

    def _register_browser_skills(self) -> None:
        """Register browser research and browser act skills on every agent."""
        self._add_skill(
            "browser_research",
            "browser_research",
            "Research a URL — navigate, extract text, return findings",
            self._skill_browser_research,
        )
        self._add_skill(
            "browser_act",
            "browser_act",
            "Act on a URL — fill forms, click buttons, submit data",
            self._skill_browser_act,
        )

    def _skill_browser_research(self, **kwargs: Any) -> SkillResult:
        url = kwargs.get("url", "")
        task = kwargs.get("task", "")
        if not url:
            return SkillResult(success=False, error="url required")
        return self._browser_research(url, task or "Extract all relevant information")

    def _skill_browser_act(self, **kwargs: Any) -> SkillResult:
        url = kwargs.get("url", "")
        task = kwargs.get("task", "")
        if not url or not task:
            return SkillResult(success=False, error="url and task required")
        return self._browser_act(url, task)

    def _add_skill(
        self,
        name: str,
        action_type: str,
        description: str,
        handler: Callable[..., SkillResult],
        min_tier: PermissionTier | None = None,
    ) -> None:
        skill_tier = min_tier or required_tier_for_action(action_type)
        self._skills[name] = AgentSkill(
            name=name,
            action_type=action_type,
            description=description,
            handler=handler,
            min_tier=skill_tier,
        )

    def execute_skill(self, skill_name: str, **kwargs: Any) -> SkillResult:
        skill = self._skills.get(skill_name)
        if not skill:
            return SkillResult(
                success=False,
                error=f"Unknown skill: {skill_name}",
                action_type="",
                tier_used=self.PERMISSION_TIER.value,
            )

        if not self.PERMISSION_TIER.permits(skill.min_tier):
            return SkillResult(
                success=False,
                error=(
                    f"Agent tier {self.PERMISSION_TIER.value} cannot execute "
                    f"{skill_name} (requires {skill.min_tier.value})"
                ),
                action_type=skill.action_type,
                tier_used=self.PERMISSION_TIER.value,
            )

        try:
            result = skill.handler(**kwargs)
            result.action_type = skill.action_type
            result.tier_used = self.PERMISSION_TIER.value
            return result
        except Exception as e:
            logger.error("[%s] Skill %s failed: %s", self.DEPARTMENT, skill_name, e)
            return SkillResult(
                success=False,
                error=str(e),
                action_type=skill.action_type,
                tier_used=self.PERMISSION_TIER.value,
            )

    @property
    def skills(self) -> dict[str, dict[str, str]]:
        return {
            name: {
                "action_type": s.action_type,
                "description": s.description,
                "min_tier": s.min_tier.value,
            }
            for name, s in self._skills.items()
        }

    def metadata(self) -> dict[str, Any]:
        return {
            "projection": "eos",
            "department": self.DEPARTMENT,
            "permission_tier": self.PERMISSION_TIER.value,
            "skill_count": len(self._skills),
            "skills": list(self._skills.keys()),
            "browser_capable": True,
        }

    # ── Browser capabilities ─────────────────────────────────────────────────

    def _browser_research(self, url: str, task: str) -> SkillResult:
        """Research via browser — navigate and extract information. READ tier."""
        return self._run_browser(url, task, "research")

    def _browser_act(self, url: str, task: str) -> SkillResult:
        """Act via browser — fill forms, click, submit. EXECUTE tier."""
        return self._run_browser(url, task, "act")

    def _run_browser(self, url: str, task: str, mode: str) -> SkillResult:
        """Execute a browser task. Handles async-to-sync bridge."""
        try:
            from substrate import run_browser_task

            loop = None
            try:
                loop = asyncio.get_running_loop()
            except RuntimeError:
                pass

            if loop and loop.is_running():
                import concurrent.futures

                with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
                    result = pool.submit(asyncio.run, run_browser_task(url=url, task=task)).result(
                        timeout=60
                    )
            else:
                result = asyncio.run(run_browser_task(url=url, task=task))

            return SkillResult(
                success=result.get("success", False),
                output={
                    "mode": mode,
                    "url": result.get("final_url", url),
                    "findings": result.get("findings", ""),
                    "steps": result.get("steps_taken", []),
                },
                action_type=f"browser_{mode}",
            )
        except Exception as e:
            logger.error("[%s] Browser %s failed: %s", self.DEPARTMENT, mode, e)
            return SkillResult(
                success=False,
                error=f"Browser {mode} failed: {e}",
                action_type=f"browser_{mode}",
            )
