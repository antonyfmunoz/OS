"""Agent runtime for OS agents — compatibility wrapper over UMH execution runtime.

Generic execution mechanics (rate limiting, cost calculation, result envelope)
live in UMH. This file adds EOS-specific orchestration:
  - Soul doc loading (agent hierarchy + BIS)
  - Venture context injection
  - Skill registry + auto-selection
  - Semantic memory retrieval
  - Human profile injection
  - Authority engine checks
  - Model preference resolution
  - Team task routing

Usage unchanged:
    from umh.runtime_engine.agent_runtime import AgentRuntime, TaskType
    runtime = AgentRuntime()
    result = runtime.run(task_type=TaskType.ANALYZE, prompt="...")
"""

import os
import time
from dataclasses import dataclass
from enum import Enum
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).parent / ".env")

from umh.environments.system_context import EOSContext, load_context_from_env
try:
    from umh.runtime_engine.venture_knowledge import VentureKnowledgeBase
except ImportError:
    pass
try:
    from umh.runtime_engine.skill_registry import SkillRegistry, get_skill_registry
except ImportError:
    pass
from umh.runtime_engine.authority_engine import AuthorityEngine
try:
    from umh.runtime_engine.model_preferences import ModelPreferences
except ImportError:
    pass

from umh.execution.runtime import (  # noqa: F401
    COST_PER_MILLION_TOKENS,
    RateLimiter,
    calculate_cost,
)

# ─── Models ──────────────────────────────────────────────────────────────────

HAIKU = "claude-haiku-4-5-20251001"
SONNET = "claude-sonnet-4-6"


# ─── TaskType — re-export from UMH with EOS subset ──────────────────────────


class TaskType(Enum):
    SCORE = "score"
    CLASSIFY = "classify"
    ANALYZE = "analyze"
    GENERATE = "generate"
    SUMMARIZE = "summarize"
    FAST_RESPONSE = "fast_response"


# ─── Retry config ─────────────────────────────────────────────────────────────

_MAX_RETRIES = 4
_BACKOFF_BASE = 2


# ─── Result ───────────────────────────────────────────────────────────────────


@dataclass
class AgentResult:
    output: str
    model_used: str
    tokens_used: dict[str, int]
    skill_used: str | None
    interaction_id: int | None = None
    authority: dict | None = None
    cost_usd: float = 0.0
    duration_ms: int = 0


# ─── Runtime ─────────────────────────────────────────────────────────────────


class AgentRuntime:
    def __init__(self, ctx: EOSContext | None = None) -> None:
        self._skills = get_skill_registry()
        self._prefs = ModelPreferences(ctx or load_context_from_env())

        from umh.runtime_engine.memory import AgentMemory

        self._memory = AgentMemory()

    @property
    def client(self):
        """Removed: use model_router.call_with_fallback() instead."""
        raise RuntimeError("Deprecated: use model_router.call_with_fallback() instead")

    # ─── Public: run task ────────────────────────────────────────────────────

    def run(
        self,
        task_type: TaskType,
        prompt: str,
        venture_id: str | None = None,
        skill_name: str | None = None,
        max_tokens: int = 1024,
        agent: str = "default",
        system_extra: str | None = None,
        ctx: EOSContext | None = None,
        modality: str = "text",
        data_tier: str = "internal",
        require_realtime: bool = False,
        forced_model: str | None = None,
        task_criticality: str = "normal",
        raw_input: str | None = None,
    ) -> AgentResult:
        """Execute a task with the appropriate model.

        EOS-specific orchestration: soul docs, venture context, skill
        injection, memory retrieval, authority checking.  Generic rate
        limiting and cost calculation delegate to UMH execution runtime.
        """
        if ctx is None:
            ctx = load_context_from_env()

        _org_id = ctx.org_id if ctx else "default"
        if not RateLimiter.check(_org_id):
            return AgentResult(
                output="Rate limit reached. Please wait a moment.",
                model_used="rate_limiter",
                tokens_used={"input": 0, "output": 0, "total": 0},
                skill_used=None,
            )

        model_config = self._prefs.resolve_model(
            task_type=task_type.value,
            modality=modality,
            data_tier=data_tier,
            require_realtime=require_realtime,
            forced_model=forced_model,
            task_criticality=task_criticality,
        )
        model = model_config["model"]
        system_parts: list[str] = []
        skill_used: str | None = None

        if agent == "default":
            try:
                from umh.runtime_engine.agent_hierarchy import AgentHierarchy

                agent = AgentHierarchy().get_primary_interface()
            except Exception:
                agent = "executive_assistant"

        soul_doc_loaded = False

        if agent == "executive_assistant":
            try:
                from umh.workstation.business import BusinessInstanceManager

                _bim = BusinessInstanceManager(ctx)
                _primary_vid = venture_id or "lyfe_institute"
                _bis = _bim.get_bis(_primary_vid)
                _user_soul_doc = getattr(_bis, "ai_soul_doc_path", "") if _bis else ""
                if _user_soul_doc and Path(_user_soul_doc).exists():
                    system_parts.append(
                        Path(_user_soul_doc).read_text(encoding="utf-8")
                    )
                    print(f"[AgentRuntime] User soul doc: {_user_soul_doc}")
                    soul_doc_loaded = True
            except Exception:
                pass

        if not soul_doc_loaded:
            _soul_path = Path(__file__).parent.parent / "agents" / f"{agent}.md"
            if agent not in ("gateway.direct",) and _soul_path.exists():
                try:
                    system_parts.append(_soul_path.read_text(encoding="utf-8"))
                except Exception:
                    pass

        if system_extra:
            system_parts.append(system_extra)

        try:
            past = self._memory.semantic_search(prompt, venture_id=venture_id, limit=3)
            if past:
                past_lines = []
                for p in past:
                    outcome_str = ""
                    _iid = p.get("interaction_id") or p.get("id", "")
                    outcomes = self._memory.get_outcomes_for(_iid)
                    if outcomes:
                        outcome_str = f" → outcome: {outcomes[-1]['outcome_type']}"
                    _agent_label = p.get("agent_label") or p.get("agent", "unknown")
                    past_lines.append(
                        f"  [{p.get('similarity', 0):.2f}] {_agent_label} | {p.get('input_summary', '')[:120]}"
                        f"{outcome_str}"
                    )
                system_parts.append(
                    "## RELEVANT PAST INTERACTIONS\n\n"
                    "These past interactions are semantically similar to the current task. "
                    "Use them to inform your approach — especially outcomes.\n\n"
                    + "\n".join(past_lines)
                )
        except Exception:
            pass

        if venture_id:
            try:
                venture_context = VentureKnowledgeBase.to_agent_context(
                    venture_id, detail="full"
                )
                system_parts.append(
                    "## VENTURE CONTEXT\n\n"
                    "Use the following venture intelligence to inform your analysis. "
                    "Match language and positioning exactly to this venture.\n\n"
                    + venture_context
                )
            except KeyError as e:
                print(f"[AgentRuntime] Warning: {e}")

        if skill_name:
            skill = self._skills.get_skill(skill_name)
            if skill:
                skill_used = skill.skill_id
                system_parts.append(
                    "## SKILL INSTRUCTIONS\n\n"
                    "Follow the skill instructions below exactly. "
                    "Use the specified output format.\n\n" + skill.content
                )
            else:
                print(
                    f"[AgentRuntime] Warning: skill '{skill_name}' not found — running without skill"
                )
        elif venture_id:
            relevant = self._skills.get_relevant_skills(prompt, top_n=1)
            if relevant:
                skill = relevant[0]
                skill_used = skill.skill_id
                system_parts.append(
                    "## SKILL INSTRUCTIONS (auto-selected)\n\n" + skill.content
                )

        system_prompt = "\n\n---\n\n".join(system_parts) if system_parts else None

        from umh.runtime_engine.model_router import call_with_fallback as _router_call

        _start = time.time()

        routing_result = _router_call(
            prompt=prompt,
            system=system_prompt,
            task_type=task_type.value,
            agent_type=agent,
            raw_input=raw_input,
        )
        output = routing_result.output
        model = f"{routing_result.provider}/{routing_result.model}"
        tokens_used = {
            "input": routing_result.input_tokens,
            "output": routing_result.output_tokens,
            "total": routing_result.tokens_used,
        }

        _duration_ms = int((time.time() - _start) * 1000)
        _cost_usd = calculate_cost(model, tokens_used)

        result = AgentResult(
            output=output,
            model_used=model,
            tokens_used=tokens_used,
            skill_used=skill_used,
            cost_usd=_cost_usd,
            duration_ms=_duration_ms,
        )

        input_summary = prompt[:200].replace("\n", " ")
        interaction_id = self._memory.log(
            agent_result=result,
            venture_id=venture_id,
            input_summary=input_summary,
            agent=agent,
            task_type=task_type.value,
        )
        result.interaction_id = interaction_id
        self._memory.embed_and_store(interaction_id, input_summary)

        action_tasks = {
            "score": "analyze",
            "classify": "classify",
            "generate": "draft_message",
            "analyze": "analyze",
        }
        action_type = action_tasks.get(
            task_type.value if hasattr(task_type, "value") else str(task_type),
            "analyze",
        )
        ae = AuthorityEngine(ctx or load_context_from_env())
        result.authority = ae.check_can_execute(action_type)

        return result

    def run_team_task(
        self,
        team: str,
        sub_agent: str,
        prompt: str,
        venture_id: str,
        username: str | None = None,
    ) -> AgentResult:
        """Route a task to the correct sub-agent within a domain team."""
        try:
            from umh.runtime_engine.agent_teams import route as team_route
        except ImportError:
            pass

        config = team_route(team, sub_agent)
        agent_label = f"{team}.{sub_agent}"

        system_extra: str | None = None
        if username and config.task_type in (TaskType.GENERATE, TaskType.ANALYZE):
            try:
                from umh.runtime_engine.human_intelligence import HumanIntelligenceEngine

                engine = HumanIntelligenceEngine()
                profile = engine.get_profile(username)
                if profile:
                    system_extra = (
                        "## HUMAN PROFILE — WHO YOU ARE SPEAKING TO\n\n"
                        f"Username        : @{profile.get('username', username)}\n"
                        f"Dominant pain   : {profile.get('dominant_pain', 'unknown')}\n"
                        f"Comm style      : {profile.get('communication_style', 'unknown')}\n"
                        f"Recommended tone: {profile.get('recommended_tone', 'unknown')}\n"
                        f"Objection risk  : {', '.join(profile.get('objection_risk', []))}\n"
                        f"Next best action: {profile.get('next_best_action', 'unknown')}\n\n"
                        "Adapt your output to this person's style and pain. "
                        "Do not reference this profile explicitly in your output."
                    )
            except Exception as e:
                print(f"[AgentRuntime] Human profile load failed for @{username}: {e}")

        return self.run(
            task_type=config.task_type,
            prompt=prompt,
            venture_id=venture_id,
            skill_name=config.skill_name,
            max_tokens=config.max_tokens,
            agent=agent_label,
            system_extra=system_extra,
        )

    def run_with_auto_skill(
        self,
        task_type: TaskType,
        prompt: str,
        venture_id: str | None = None,
        max_tokens: int = 1024,
        agent: str = "default",
        username: str | None = None,
        ctx: EOSContext | None = None,
    ) -> AgentResult:
        """Same as run() but auto-selects the top matching skill."""
        if ctx is None:
            ctx = load_context_from_env()

        relevant = self._skills.get_relevant_skills(prompt, top_n=1)
        skill_name = relevant[0].skill_id if relevant else None

        system_extra: str | None = None
        if username and task_type in (TaskType.GENERATE, TaskType.ANALYZE):
            try:
                from umh.runtime_engine.human_intelligence import HumanIntelligenceEngine

                engine = HumanIntelligenceEngine()
                profile = engine.get_profile(username)
                if profile:
                    system_extra = (
                        "## HUMAN PROFILE — WHO YOU ARE SPEAKING TO\n\n"
                        f"Username        : @{profile.get('username', username)}\n"
                        f"Dominant pain   : {profile.get('dominant_pain', 'unknown')}\n"
                        f"Comm style      : {profile.get('communication_style', 'unknown')}\n"
                        f"Recommended tone: {profile.get('recommended_tone', 'unknown')}\n"
                        f"Objection risk  : {', '.join(profile.get('objection_risk', []))}\n"
                        f"Next best action: {profile.get('next_best_action', 'unknown')}\n\n"
                        "Adapt your output to this person's style and pain. "
                        "Do not reference this profile explicitly in your output."
                    )
            except Exception as e:
                print(f"[AgentRuntime] Human profile load failed for @{username}: {e}")

        return self.run(
            task_type=task_type,
            prompt=prompt,
            venture_id=venture_id,
            skill_name=skill_name,
            max_tokens=max_tokens,
            agent=agent,
            system_extra=system_extra,
            ctx=ctx,
        )
