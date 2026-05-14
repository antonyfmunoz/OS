"""
Agent runtime for OS agents.

Routes calls to the correct Claude model based on task type:
  - Haiku  (claude-haiku-4-5-20251001)  — scoring, classification, quick analysis
  - Sonnet (claude-sonnet-4-6)           — generation, deep analysis, content creation

Usage:
    from execution.runtime.agent_runtime import AgentRuntime, TaskType

    runtime = AgentRuntime()
    result = runtime.run(
        task_type=TaskType.ANALYZE,
        prompt="Analyze this signal...",
        venture_id="lyfe_institute",
        skill_name="analyze_icp_signal",
    )
    print(result.output)
"""

import os
import time
from dataclasses import dataclass
from enum import Enum
from pathlib import Path

from dotenv import load_dotenv

# Load runtime/.env so DATABASE_URL, EOS_ORG_ID, EOS_USER_ID are available
# before any import that touches db.py (memory, human_intelligence, etc.)
load_dotenv(Path(__file__).parent / ".env")

from runtime.context import EOSContext, load_context_from_env
from state.business.venture_knowledge import VentureKnowledgeBase
from runtime.skill_registry import SkillRegistry, get_skill_registry
from governance.policy.authority_engine import AuthorityEngine
from state.preferences.model_preferences import ModelPreferences


# ─── Models ──────────────────────────────────────────────────────────────────

HAIKU = "claude-haiku-4-5-20251001"  # scoring, classification
SONNET = "claude-sonnet-4-6"  # generation, analysis

# ─── Cost table (USD per million tokens) ─────────────────────────────────────

COST_PER_MILLION_TOKENS: dict[str, dict[str, float]] = {
    "claude-haiku-4-5-20251001": {"input": 0.80, "output": 4.00},
    "claude-sonnet-4-6": {"input": 3.00, "output": 15.00},
    "claude-opus-4-6": {"input": 15.00, "output": 75.00},
}


def calculate_cost(model: str, tokens_used: dict[str, int]) -> float:
    """Return USD cost for a completed API call."""
    rates = COST_PER_MILLION_TOKENS.get(model, {"input": 3.00, "output": 15.00})
    input_cost = tokens_used.get("input", 0) / 1_000_000 * rates["input"]
    output_cost = tokens_used.get("output", 0) / 1_000_000 * rates["output"]
    return round(input_cost + output_cost, 8)


class TaskType(Enum):
    SCORE = "score"  # → Haiku: ICP scoring, lead qualification
    CLASSIFY = "classify"  # → Haiku: archetype detection, intent classification
    ANALYZE = "analyze"  # → Sonnet: deep signal analysis, conversation analysis
    GENERATE = "generate"  # → Sonnet: outreach copy, content, market reports
    SUMMARIZE = "summarize"  # → Haiku: quick summaries, call digests
    FAST_RESPONSE = "fast_response"  # → Haiku: low-latency single-turn responses


# ─── Rate limiter ─────────────────────────────────────────────────────────────


class RateLimiter:
    """
    In-memory per-org rate limiter.
    Prevents runaway loops or malicious input from draining API credits.
    Limits: 10 calls/minute, 200 calls/hour per org.
    """

    _counts: dict[str, dict[str, int]] = {}

    LIMITS = {
        "per_minute": 30,
        "per_hour": 500,
    }

    @classmethod
    def check(cls, org_id: str) -> bool:
        """Return True if call is allowed. Return False if rate limited."""
        from datetime import datetime as _dt

        now = _dt.now()
        minute_key = now.strftime("%Y%m%d%H%M")
        hour_key = now.strftime("%Y%m%d%H")

        if org_id not in cls._counts:
            cls._counts[org_id] = {}

        counts = cls._counts[org_id]

        minute_count = counts.get(minute_key, 0)
        if minute_count >= cls.LIMITS["per_minute"]:
            print(f"[RateLimiter] Minute limit hit: {org_id} — {minute_count}/min")
            return False

        hour_count = counts.get(hour_key, 0)
        if hour_count >= cls.LIMITS["per_hour"]:
            print(f"[RateLimiter] Hour limit hit: {org_id} — {hour_count}/hour")
            return False

        counts[minute_key] = minute_count + 1
        counts[hour_key] = hour_count + 1

        # Purge keys not in current window to prevent unbounded growth
        cls._counts[org_id] = {
            k: v for k, v in counts.items() if k in (minute_key, hour_key)
        }
        return True


# ─── Retry config ─────────────────────────────────────────────────────────────

_MAX_RETRIES = 4
_BACKOFF_BASE = 2  # seconds — delays: 2 → 4 → 8 → 16


# ─── Result ───────────────────────────────────────────────────────────────────


@dataclass
class AgentResult:
    output: str
    model_used: str
    tokens_used: dict[str, int]  # {"input": N, "output": N, "total": N}
    skill_used: str | None  # skill_id or None
    interaction_id: int | None = None  # set by memory.log() after persistence
    authority: dict | None = None  # set by AuthorityEngine.check_can_execute()
    cost_usd: float = 0.0  # USD cost for this call
    duration_ms: int = 0  # wall-clock time for API call in ms


# ─── Runtime ─────────────────────────────────────────────────────────────────


class AgentRuntime:
    def __init__(self, ctx: EOSContext | None = None) -> None:
        self._skills = get_skill_registry()
        self._prefs = ModelPreferences(ctx or load_context_from_env())

        # Import here to avoid circular imports if memory imports runtime
        from state.memory.memory import AgentMemory

        self._memory = AgentMemory()

    @property
    def client(self):
        """Deprecated: use model_router.call_with_fallback() instead.
        Kept for backward compatibility — logs warning on use."""
        import warnings
        warnings.warn(
            "AgentRuntime.client is deprecated — use model_router.call_with_fallback()",
            DeprecationWarning,
            stacklevel=2,
        )
        import anthropic
        api_key = os.environ.get("ANTHROPIC_API_KEY")
        return anthropic.Anthropic(api_key=api_key) if api_key else None

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
        """
        Execute a task with the appropriate model.

        Args:
            task_type:    Determines model selection (Haiku vs Sonnet).
            prompt:       The user-facing task description / input.
            venture_id:   If provided, injects venture context as system context.
            skill_name:   If provided, loads the skill and injects it as a
                          system-level instruction set.
            max_tokens:   Max tokens for the response.
            agent:        Logical agent name for memory logging (e.g. "outreach_agent").
            system_extra: Optional additional context prepended to the system
                          prompt before venture and skill context. Used to inject
                          human profiles, user model data, etc.

        Returns:
            AgentResult with output, model, token counts, skill used, and
            interaction_id (set after memory is persisted).
        """
        if ctx is None:
            ctx = load_context_from_env()

        # Rate limit check — hard block before any model call
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

        # 0a. Load agent soul doc if present (agents/{agent}.md)
        # Agent identity is the outermost layer — injected first so it
        # shapes how all downstream context (venture, skills, memory) is used.
        # When no agent specified, default to executive_assistant.
        if agent == "default":
            try:
                from control_plane.agents.agent_hierarchy import AgentHierarchy

                agent = AgentHierarchy().get_primary_interface()
            except Exception:
                agent = "executive_assistant"

        soul_doc_loaded = False

        # For EA: check BIS for user-generated soul doc first.
        # Every user gets their own AI name and identity — loaded from BIS.
        if agent == "executive_assistant":
            try:
                from state.business.business_instance import BusinessInstanceManager

                _bim = BusinessInstanceManager(ctx)
                # Try primary venture — EA soul doc is stored on the first venture
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
                pass  # fall through to hierarchy soul doc

        # Fall back to hierarchy soul doc (agents/{agent}.md)
        if not soul_doc_loaded:
            _soul_path = Path(__file__).parent.parent / "agents" / f"{agent}.md"
            if agent not in ("gateway.direct",) and _soul_path.exists():
                try:
                    system_parts.append(_soul_path.read_text(encoding="utf-8"))
                except Exception:
                    pass

        # 0. Prepend any caller-supplied extra context (e.g. human profile)
        if system_extra:
            system_parts.append(system_extra)

        # 0b. Inject semantically relevant past interactions from memory
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
            pass  # semantic retrieval is enhancement — never block execution

        # 1. Inject venture context
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

        # 2. Inject skill instructions
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
            # Auto-select relevant skills from the prompt
            relevant = self._skills.get_relevant_skills(prompt, top_n=1)
            if relevant:
                skill = relevant[0]
                skill_used = skill.skill_id
                system_parts.append(
                    "## SKILL INSTRUCTIONS (auto-selected)\n\n" + skill.content
                )

        system_prompt = "\n\n---\n\n".join(system_parts) if system_parts else None

        # 3. Call the API — single path through model_router fallback chain:
        #    cc_sdk → Anthropic → Gemini → Ollama
        from execution.runtime.model_router import call_with_fallback as _router_call

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

        # 4. Persist to memory + embed for future semantic retrieval
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

        # 5. Authority check — classify action and attach to result
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
        """
        Route a task to the correct sub-agent within a domain team.

        - Resolves team + sub_agent to a SubAgentConfig via agent_teams.route().
        - Loads the matching skill automatically by skill_name.
        - Injects human profile when username is provided and task is GENERATE/ANALYZE.
        - Logs to memory.db using 'team.sub_agent' as the agent label.

        Args:
            team:       Domain team name — "sales", "research", or "content".
            sub_agent:  Named sub-agent within that team.
            prompt:     Task input — the signal, message, or question.
            venture_id: Venture context to inject (e.g. "lyfe_institute").
            username:   Instagram handle for human profile injection (optional).

        Returns:
            AgentResult with output, model, token counts, skill used, and interaction_id.
        """
        from runtime.agent_teams import route as team_route

        config = team_route(team, sub_agent)
        agent_label = f"{team}.{sub_agent}"

        # Inject human profile for generation/analysis tasks when username provided
        system_extra: str | None = None
        if username and config.task_type in (TaskType.GENERATE, TaskType.ANALYZE):
            try:
                from runtime.human_intelligence import HumanIntelligenceEngine

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
        """
        Same as run() but auto-selects the top matching skill from the registry
        based on keyword overlap with the prompt.

        If username is provided and the task is outreach-oriented (GENERATE),
        the human profile for that lead is loaded and injected into the system
        prompt so the agent knows exactly who it is speaking to.
        """
        if ctx is None:
            ctx = load_context_from_env()

        relevant = self._skills.get_relevant_skills(prompt, top_n=1)
        skill_name = relevant[0].skill_id if relevant else None

        # Inject human profile for outreach tasks when username is provided
        system_extra: str | None = None
        if username and task_type in (TaskType.GENERATE, TaskType.ANALYZE):
            try:
                from runtime.human_intelligence import HumanIntelligenceEngine

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
