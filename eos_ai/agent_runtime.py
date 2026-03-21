"""
Agent runtime for OS agents.

Routes calls to the correct Claude model based on task type:
  - Haiku  (claude-haiku-4-5-20251001)  — scoring, classification, quick analysis
  - Sonnet (claude-sonnet-4-6)           — generation, deep analysis, content creation

Usage:
    from eos_ai.agent_runtime import AgentRuntime, TaskType

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

import anthropic

from eos_ai.venture_knowledge import VentureKnowledgeBase
from eos_ai.skill_registry import SkillRegistry


# ─── Models ──────────────────────────────────────────────────────────────────

HAIKU  = "claude-haiku-4-5-20251001"   # scoring, classification
SONNET = "claude-sonnet-4-6"            # generation, analysis


class TaskType(Enum):
    SCORE       = "score"       # → Haiku: ICP scoring, lead qualification
    CLASSIFY    = "classify"    # → Haiku: archetype detection, intent classification
    ANALYZE     = "analyze"     # → Sonnet: deep signal analysis, conversation analysis
    GENERATE    = "generate"    # → Sonnet: outreach copy, content, market reports
    SUMMARIZE   = "summarize"   # → Haiku: quick summaries, call digests


_MODEL_MAP: dict[TaskType, str] = {
    TaskType.SCORE:    HAIKU,
    TaskType.CLASSIFY: HAIKU,
    TaskType.ANALYZE:  SONNET,
    TaskType.GENERATE: SONNET,
    TaskType.SUMMARIZE: HAIKU,
}


# ─── Retry config ─────────────────────────────────────────────────────────────

_MAX_RETRIES   = 4
_BACKOFF_BASE  = 2   # seconds — delays: 2 → 4 → 8 → 16


# ─── Result ───────────────────────────────────────────────────────────────────

@dataclass
class AgentResult:
    output: str
    model_used: str
    tokens_used: dict[str, int]   # {"input": N, "output": N, "total": N}
    skill_used: str | None        # skill_id or None
    interaction_id: int | None = None  # set by memory.log() after persistence


# ─── Runtime ─────────────────────────────────────────────────────────────────

class AgentRuntime:

    def __init__(self) -> None:
        api_key = os.environ.get("ANTHROPIC_API_KEY")
        if not api_key:
            raise EnvironmentError(
                "ANTHROPIC_API_KEY is not set. "
                "Export it or add it to your .env file."
            )
        self._client = anthropic.Anthropic(api_key=api_key)
        self._skills = SkillRegistry()

        # Import here to avoid circular imports if memory imports runtime
        from eos_ai.memory import AgentMemory
        self._memory = AgentMemory()

    @property
    def client(self) -> anthropic.Anthropic:
        """Expose the configured Anthropic client for scripts that manage
        their own prompts (e.g. icp_scorer)."""
        return self._client

    # ─── Internal: resilient API call ────────────────────────────────────────

    def _call_with_retry(self, **kwargs) -> anthropic.types.Message:
        """
        Call the Anthropic API with exponential backoff.
        Delays: 2s → 4s → 8s → 16s across 4 retries before raising.
        """
        last_exc: Exception | None = None

        for attempt in range(_MAX_RETRIES + 1):
            try:
                return self._client.messages.create(**kwargs)

            except (
                anthropic.RateLimitError,
                anthropic.InternalServerError,
                anthropic.APIConnectionError,
                anthropic.APITimeoutError,
            ) as exc:
                last_exc = exc
                if attempt == _MAX_RETRIES:
                    break
                delay = _BACKOFF_BASE ** (attempt + 1)   # 2, 4, 8, 16
                reason = type(exc).__name__
                print(
                    f"[AgentRuntime] API error on attempt {attempt + 1}/{_MAX_RETRIES} "
                    f"({reason}: {exc}) — retrying in {delay}s..."
                )
                time.sleep(delay)

            except anthropic.APIStatusError as exc:
                # 4xx errors other than 429 won't recover on retry
                last_exc = exc
                if exc.status_code == 429:
                    if attempt == _MAX_RETRIES:
                        break
                    delay = _BACKOFF_BASE ** (attempt + 1)
                    print(
                        f"[AgentRuntime] 429 rate limit on attempt {attempt + 1}/{_MAX_RETRIES} "
                        f"— retrying in {delay}s..."
                    )
                    time.sleep(delay)
                else:
                    raise  # non-recoverable, surface immediately

        raise RuntimeError(
            f"[AgentRuntime] API call failed after {_MAX_RETRIES} retries. "
            f"Last error: {last_exc}"
        ) from last_exc

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
        model = _MODEL_MAP[task_type]
        system_parts: list[str] = []
        skill_used: str | None = None

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
                    outcomes = self._memory.get_outcomes_for(p["id"])
                    if outcomes:
                        outcome_str = f" → outcome: {outcomes[-1]['outcome_type']}"
                    past_lines.append(
                        f"  [{p['similarity']:.2f}] {p['agent']} | {p['input_summary'][:120]}"
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
                    "Use the specified output format.\n\n"
                    + skill.content
                )
            else:
                print(f"[AgentRuntime] Warning: skill '{skill_name}' not found — running without skill")
        elif venture_id:
            # Auto-select relevant skills from the prompt
            relevant = self._skills.get_relevant_skills(prompt, top_n=1)
            if relevant:
                skill = relevant[0]
                skill_used = skill.skill_id
                system_parts.append(
                    "## SKILL INSTRUCTIONS (auto-selected)\n\n"
                    + skill.content
                )

        system_prompt = "\n\n---\n\n".join(system_parts) if system_parts else None

        # 3. Call the API (with retry)
        kwargs: dict = {
            "model": model,
            "max_tokens": max_tokens,
            "messages": [{"role": "user", "content": prompt}],
        }
        if system_prompt:
            kwargs["system"] = system_prompt

        response = self._call_with_retry(**kwargs)

        output = response.content[0].text
        tokens_used = {
            "input":  response.usage.input_tokens,
            "output": response.usage.output_tokens,
            "total":  response.usage.input_tokens + response.usage.output_tokens,
        }

        result = AgentResult(
            output=output,
            model_used=model,
            tokens_used=tokens_used,
            skill_used=skill_used,
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
        from eos_ai.agent_teams import route as team_route

        config = team_route(team, sub_agent)
        agent_label = f"{team}.{sub_agent}"

        # Inject human profile for generation/analysis tasks when username provided
        system_extra: str | None = None
        if username and config.task_type in (TaskType.GENERATE, TaskType.ANALYZE):
            try:
                from eos_ai.human_intelligence import HumanIntelligenceEngine
                engine  = HumanIntelligenceEngine()
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
    ) -> AgentResult:
        """
        Same as run() but auto-selects the top matching skill from the registry
        based on keyword overlap with the prompt.

        If username is provided and the task is outreach-oriented (GENERATE),
        the human profile for that lead is loaded and injected into the system
        prompt so the agent knows exactly who it is speaking to.
        """
        relevant   = self._skills.get_relevant_skills(prompt, top_n=1)
        skill_name = relevant[0].skill_id if relevant else None

        # Inject human profile for outreach tasks when username is provided
        system_extra: str | None = None
        if username and task_type in (TaskType.GENERATE, TaskType.ANALYZE):
            try:
                from eos_ai.human_intelligence import HumanIntelligenceEngine
                engine  = HumanIntelligenceEngine()
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
        )
