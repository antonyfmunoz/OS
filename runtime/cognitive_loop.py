"""
CognitiveLoop — full Perceive → Understand → Plan → Execute
→ Verify → Reflect → Learn → Store cycle.

Wraps AgentRuntime with authority gating, prompt enhancement,
quality verification, and reflection logging. Every AI task
in the system should enter through here rather than calling
AgentRuntime directly.

Usage:
    from eos_ai.cognitive_loop import CognitiveLoop, CognitiveResult
    from eos_ai.agent_runtime import TaskType

    ctx  = load_context_from_env()
    loop = CognitiveLoop(ctx)
    result = loop.run(
        raw_prompt="Analyze this lead's signal",
        agent="sales_agent",
        task_type=TaskType.ANALYZE,
        venture_id="lyfe_institute",
    )
    print(result.output)
    print(result.iterations)
    print(result.was_enhanced)
"""

from dataclasses import dataclass, field
from pathlib import Path
import os, sys, uuid, tempfile, time as _time

# ─── Spend cache ──────────────────────────────────────────────────────────────
# Queried at most once per minute to avoid a DB round-trip on every response.

_spend_cache: dict = {}
_spend_cache_ts: float = 0.0
_SPEND_CACHE_TTL = 60  # seconds

_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

from eos_ai.context import EOSContext, load_context_from_env
from eos_ai.agent_runtime import AgentRuntime, TaskType
from eos_ai.memory import AgentMemory
from eos_ai.authority_engine import AuthorityEngine
from eos_ai.venture_knowledge import VentureKnowledgeBase


@dataclass
class MultimodalInput:
    text: str | None = None
    file_path: str | None = None
    file_bytes: bytes | None = None
    images: list[bytes] | None = None
    audio_path: str | None = None
    document_bytes: bytes | None = None
    document_mime: str | None = None
    video_path: str | None = None
    modality: str = "text"
    user_prompt: str | None = None


@dataclass
class CognitiveResult:
    status: str  # 'completed' | 'pending_approval'
    output: str | None
    model_used: str = ""
    tokens_used: dict = field(default_factory=dict)
    skill_used: str | None = None
    interaction_id: str | None = None
    approval_id: str | None = None
    iterations: int = 1
    was_enhanced: bool = False
    authority: dict | None = None
    response_audio_path: str | None = None
    response_modality: str = "text"
    input_modality: str = "text"


def _get_neon_spend(org_id: str) -> dict:
    """
    Return accumulated spend from the interactions table: today, this month,
    and all-time. Cost is calculated from stored token counts × model rates
    (cost_usd in tokens_json is 0 for legacy rows — we recalculate always).

    Results are cached for _SPEND_CACHE_TTL seconds so this is cheap to
    call on every response.
    """
    global _spend_cache, _spend_cache_ts

    now = _time.monotonic()
    if _spend_cache and (now - _spend_cache_ts) < _SPEND_CACHE_TTL:
        return _spend_cache

    from eos_ai.db import get_conn
    from eos_ai.agent_runtime import COST_PER_MILLION_TOKENS

    fallback = {"today": 0.0, "month": 0.0, "all_time": 0.0}
    try:
        with get_conn(org_id) as cur:
            cur.execute(
                """
                SELECT
                    model_used,
                    SUM(COALESCE((tokens_json->>'prompt')::int, 0))      AS input_tokens,
                    SUM(COALESCE((tokens_json->>'completion')::int, 0))  AS output_tokens,
                    CASE
                        WHEN created_at >= date_trunc('day',   NOW() AT TIME ZONE 'UTC')
                            THEN 'today'
                        WHEN created_at >= date_trunc('month', NOW() AT TIME ZONE 'UTC')
                            THEN 'month'
                        ELSE 'older'
                    END AS bucket
                FROM interactions
                WHERE org_id = %s
                GROUP BY model_used, bucket
                """,
                (org_id,),
            )
            rows = cur.fetchall()

        totals: dict[str, float] = {"today": 0.0, "month": 0.0, "all_time": 0.0}
        default_rates = {"input": 3.00, "output": 15.00}

        for row in rows:
            model = row["model_used"] or ""
            rates = COST_PER_MILLION_TOKENS.get(model, default_rates)
            inp = row["input_tokens"] or 0
            out = row["output_tokens"] or 0
            cost = inp / 1_000_000 * rates["input"] + out / 1_000_000 * rates["output"]
            bucket = row["bucket"]

            if bucket == "today":
                totals["today"] += cost
                totals["month"] += cost
                totals["all_time"] += cost
            elif bucket == "month":
                totals["month"] += cost
                totals["all_time"] += cost
            else:
                totals["all_time"] += cost

        _spend_cache = totals
        _spend_cache_ts = now
        return totals

    except Exception as e:
        print(f"[CognitiveLoop] spend query failed: {e}")
        return fallback


def format_response_footer(
    result,
    iterations: int = 1,
    was_enhanced: bool = False,
    original_prompt: str = "",
    enhanced_prompt: str = "",
    org_id: str | None = None,
) -> str:
    """
    Build a stats footer for any AgentResult or CognitiveResult.

    Appended to the output string so every response surfaced through
    Telegram or the gateway carries model, cost, latency, and (when
    the prompt was enhanced) the optimized version.
    """
    from eos_ai.agent_runtime import calculate_cost

    model = getattr(result, "model_used", None) or "unknown"
    cost = getattr(result, "cost_usd", 0.0) or calculate_cost(
        model, getattr(result, "tokens_used", None) or {}
    )
    duration = getattr(result, "duration_ms", 0) or 0
    skill = getattr(result, "skill_used", None) or "—"
    tokens = getattr(result, "tokens_used", None) or {}
    total_tokens = tokens.get("total", 0)

    _display_map = {
        "claude-haiku-4-5-20251001": "Haiku",
        "claude-sonnet-4-6": "Sonnet",
        "claude-opus-4-6": "Opus",
        "sonar-pro": "Perplexity",
        "gemini-2.0-flash": "Gemini Flash",
        "gemma3:4b": "Gemma3 4B (local)",
    }
    # Claude CLI tmux sessions: "claude_cli/tmux:session_name" → "Opus (CLI session_name)"
    if model.startswith("claude_cli/tmux:"):
        _session_name = model.split("tmux:", 1)[1]
        model_display = f"Opus (CLI {_session_name})"
    else:
        model_display = _display_map.get(model, model)

    if cost == 0.0 and model.startswith("claude_cli/"):
        cost_str = "CC session"
    elif cost == 0.0:
        cost_str = "free (local)"
    elif cost < 0.001:
        cost_str = "<$0.001"
    else:
        cost_str = f"${cost:.4f}"

    dur_str = f"{duration}ms" if duration < 1000 else f"{duration / 1000:.1f}s"

    lines = [
        "",
        "─" * 33,
        f"⚙  {model_display}",
        f"🪙  {cost_str}  ⏱  {dur_str}  📊  {total_tokens:,} tokens",
    ]
    if skill and skill != "—":
        lines.append(f"🔧  Skill: {skill}")
    if iterations > 1:
        lines.append(f"🔄  {iterations} iterations")
    if (
        was_enhanced
        and enhanced_prompt
        and enhanced_prompt.strip() != original_prompt.strip()
    ):
        lines.append(f"✨  Optimized prompt:")
        lines.append(f"    Original: {original_prompt}")
        lines.append(f"    Enhanced: {enhanced_prompt}")

    # Show running spend totals for paid models only
    if cost > 0.0 and org_id:
        spend = _get_neon_spend(org_id)

        def _fmt(v: float) -> str:
            return f"${v:.2f}" if v >= 0.01 else (f"${v:.4f}" if v > 0 else "$0.00")

        lines.append(
            f"💰  Today {_fmt(spend['today'])}"
            f"  ·  Month {_fmt(spend['month'])}"
            f"  ·  All-time {_fmt(spend['all_time'])}"
        )

    lines.append("─" * 33)

    return "\n".join(lines)


class CognitiveLoop:
    """
    Full cognitive loop. Wraps AgentRuntime with:
      - PERCEIVE:  load venture context and recent memory
      - UNDERSTAND: prompt enhancement for vague inputs
      - PLAN:      authority check before any execution
      - EXECUTE:   agent runtime call
      - VERIFY:    quality loop (up to max_iterations)
      - REFLECT:   extract and log learnings
      - LEARN:     memory already handled by runtime
      - STORE:     Neon event for reflections
    """

    def __init__(self, ctx: EOSContext):
        self.ctx = ctx
        self.runtime = AgentRuntime()
        self.memory = AgentMemory()
        self.authority = AuthorityEngine(ctx)
        # Session tracking for context compaction
        self.session_id: str = str(uuid.uuid4())
        self._messages: list[dict] = []
        self._last_transcript: str = ""
        # Ordering — monotonic turn counter for in-order processing
        self._turn_counter: int = 0

    # ─── Public: run ─────────────────────────────────────────────────────────

    def run(
        self,
        input: str | MultimodalInput,
        session_id: str = None,
        cm=None,
        agent: str = "executive_assistant",
        task_type: TaskType = None,
        venture_id: str | None = None,
        skill_name: str | None = None,
        workflow_id: str | None = None,
        channel: str = "",
        max_iterations: int = 3,
        raw_input: str | None = None,
    ) -> CognitiveResult:

        # 0. PERCEIVE — resolve multimodal input to text
        self._last_transcript = ""

        if isinstance(input, MultimodalInput):
            modality = input.modality
            user_prompt_override = input.user_prompt

            if modality != "text" and (
                input.file_path
                or input.audio_path
                or input.images
                or input.document_bytes
                or input.video_path
            ):
                from eos_ai.media_processor import MediaProcessor

                # write bytes to temp file if no path given
                tmp_path = None
                process_path = input.file_path or input.audio_path or input.video_path

                if not process_path:
                    suffix_map = {
                        "image": ".jpg",
                        "document": ".pdf",
                        "video": ".mp4",
                        "audio": ".wav",
                    }
                    suffix = suffix_map.get(modality, ".bin")
                    raw = (
                        input.file_bytes
                        or (input.images[0] if input.images else None)
                        or input.document_bytes
                    )
                    if raw:
                        with tempfile.NamedTemporaryFile(
                            suffix=suffix, delete=False
                        ) as f:
                            f.write(raw)
                            tmp_path = f.name
                        process_path = tmp_path

                if process_path:
                    # get venture context for business-aware framing
                    biz_ctx = ""
                    if venture_id:
                        try:
                            biz_ctx = VentureKnowledgeBase.to_agent_context(
                                venture_id, detail="brief"
                            )
                        except Exception:
                            pass

                    mp = MediaProcessor()
                    text = mp.process(
                        file_path=process_path,
                        modality=modality,
                        user_prompt=user_prompt_override or "",
                        business_context=biz_ctx,
                    )

                    # preserve transcript for voice messages
                    if modality in ("voice", "audio"):
                        self._last_transcript = text

                    # clean up temp file
                    if tmp_path:
                        try:
                            os.unlink(tmp_path)
                        except Exception:
                            pass
                else:
                    text = input.text or ""
            else:
                text = input.text or ""
        else:
            text = input
            modality = "text"
            user_prompt_override = None

        # COMPACT — check if context window approaching limit before proceeding
        self._messages.append({"role": "user", "content": text})
        self._maybe_compact()

        # 1. PERCEIVE + 2. UNDERSTAND — unified context assembly via ContextBuilder
        from eos_ai.context_builder import ContextBuilder

        _ctx_builder = ContextBuilder()
        _unified = _ctx_builder.build(
            ctx=self.ctx,
            message=text,
            session_id=session_id or self.session_id,
            agent=agent,
            venture_id=venture_id,
            channel=channel,
            conversation_memory=cm,
        )
        if _unified.failed_sources:
            print(f"[CognitiveLoop] ContextBuilder failures: {_unified.failed_sources}")

        original_prompt = text
        _true_raw_input = raw_input if raw_input else text
        enhanced = self._enhance_prompt(text)
        enhanced_prompt = enhanced
        system_extra = _unified.to_system_prompt() or None

        # 3. PLAN — authority check before committing
        action_type = self._infer_action_type(task_type)
        authority_check = self.authority.check_can_execute(action_type, workflow_id)
        if not authority_check["can_execute"] and authority_check["requires_approval"]:
            approval_id = self.authority.queue_for_approval(
                action_type,
                {"prompt": enhanced, "agent": agent},
                agent,
            )
            return CognitiveResult(
                status="pending_approval",
                output=None,
                approval_id=approval_id,
                authority=authority_check,
            )

        # 4. EXECUTE — initial run through agent runtime
        result = self.runtime.run(
            task_type=task_type,
            prompt=enhanced,
            venture_id=venture_id,
            skill_name=skill_name,
            agent=agent,
            ctx=self.ctx,
            system_extra=system_extra,
            raw_input=_true_raw_input,
        )

        # 5. VERIFY — quality loop
        # Skip verify for lightweight and structured task types.
        # Only GENERATE benefits from quality checking — it produces
        # unstructured content where a second pass catches real issues.
        # SCORE/CLASSIFY/SUMMARIZE/ANALYZE are structured by design.
        # FAST_RESPONSE/CONVERSATION are latency-sensitive.
        _tt_val = getattr(task_type, "value", None)
        _skip_verify = _tt_val in (
            "fast_response",
            "conversation",
            "score",
            "classify",
            "summarize",
            "analyze",
        )
        if _skip_verify:
            print(f"[CognitiveLoop] Skipping verify — task_type: {task_type}")

        iteration = 0
        while iteration < max_iterations and not _skip_verify:
            quality = self._verify_output(result.output, text, task_type)
            if quality["passes"]:
                break
            result = self.runtime.run(
                task_type=task_type,
                prompt=(
                    f"{enhanced}\n\nPrior attempt:\n"
                    f"{result.output}\n\nIssues found:\n"
                    f"{quality['issues']}\n\nImprove:"
                ),
                venture_id=venture_id,
                skill_name=skill_name,
                agent=agent,
                ctx=self.ctx,
                system_extra=system_extra,
                raw_input=_true_raw_input,
            )
            iteration += 1

        # 5b. STAGE FILTER — prepend stage-appropriate correction if needed
        _output_str = result.output or ""
        try:
            from eos_ai.primitives import ContextualReasoningEngine

            _cre = ContextualReasoningEngine(self.ctx)
            _stage_ctx = _cre.get_current_context(
                venture_id or self.ctx.active_venture_id or ""
            )
            _advice_triggers = [
                "hire",
                "build a team",
                "outsource",
                "automate outreach",
                "run paid",
                "launch ads",
                "paid ads",
                "scale",
                "raise",
                "invest",
                "expand",
            ]
            _resp_lower = _output_str.lower()
            _premature = [t for t in _advice_triggers if t in _resp_lower]
            if _premature and _stage_ctx.get("stage") == 1:
                _eval = _cre.evaluate_principle(
                    f"Advice about: {', '.join(_premature)}", _stage_ctx
                )
                if not _eval.get("applies", True):
                    _warning = (
                        f"⚠️ Stage check: {_eval.get('warning', '')}\n"
                        f"What applies now: "
                        f"{_eval.get('what_applies_instead', '')}\n\n"
                    )
                    _output_str = _warning + _output_str
        except Exception:
            pass  # stage filter is enhancement — never block result

        # 5c. QUALITY GATE — moved to gateway boundary (gateway._validate_output)
        # Pre-flight quality enhancement (Layer 0c above) still active here.
        # Post-flight scoring now happens at gateway output, not inside the loop.

        # 6. REFLECT — extract learnings from iteration count
        reflection = self._reflect(text, result.output, iteration)

        # 7. LEARN — log reflection to Neon if there's a real insight
        if reflection.get("insight"):
            try:
                self.memory.log_event(
                    org_id=self.ctx.org_id,
                    event_type="cognitive_reflection",
                    payload={
                        "prompt": text[:200],
                        "insight": reflection["insight"],
                        "iterations": iteration,
                        "agent": agent,
                    },
                )
            except Exception:
                pass  # reflection logging is enhancement — never block result

        # 7b. LEARN — permanently integrate conversation into knowledge base
        try:
            from eos_ai.knowledge_integrator import KnowledgeIntegrator
            from datetime import datetime, timezone as _tz

            _ki = KnowledgeIntegrator(self.ctx)
            if text and result.output:
                _ki.integrate(
                    content=(
                        f"Conversation:\n"
                        f"Founder: {text[:500]}\n"
                        f"System: {(result.output or '')[:500]}"
                    ),
                    source="telegram_conversation",
                    category="conversation",
                    metadata={
                        "task_type": str(task_type),
                        "agent": agent or "system",
                        "timestamp": datetime.now(_tz.utc).isoformat(),
                    },
                )
        except Exception:
            pass  # knowledge integration is enhancement — never block result

        # 7c. FEEDBACK — auto-check if user message closes pending recommendations
        try:
            if text and modality == "text":
                from eos_ai.feedback_loop import FeedbackLoop

                _fl = FeedbackLoop(self.ctx)
                _fl.log_outcome(
                    text=text,
                    venture_id=venture_id or "",
                )
        except Exception as _fb_err:
            print(f"[CognitiveLoop] Feedback loop error: {_fb_err}")
            # Never block result — feedback is enhancement

        # 8. STORE — handled by memory.log() inside runtime.run()

        was_enhanced = enhanced != text
        footer = format_response_footer(
            result=result,
            iterations=iteration + 1,
            was_enhanced=was_enhanced,
            original_prompt=original_prompt,
            enhanced_prompt=enhanced_prompt,
            org_id=self.ctx.org_id,
        )
        output_with_footer = _output_str + footer

        cognitive_result = CognitiveResult(
            status="completed",
            output=output_with_footer,
            model_used=result.model_used,
            tokens_used=result.tokens_used,
            skill_used=result.skill_used,
            interaction_id=result.interaction_id,
            iterations=iteration + 1,
            was_enhanced=was_enhanced,
            authority=result.authority,
        )

        # Append assistant response to session messages (without footer)
        if _output_str:
            self._messages.append({"role": "assistant", "content": _output_str})

        return cognitive_result

    # ─── Private helpers ─────────────────────────────────────────────────────

    def _maybe_compact(self) -> None:
        """
        Check if the session message list is approaching the token limit.
        If so, compact into a brief, seed the next context, and reset messages.
        User never sees the reset — conversation continues seamlessly.
        """
        try:
            from eos_ai.context_compaction import ContextCompactor

            compactor = ContextCompactor(self.ctx)
            if compactor.should_compact(self._messages):
                brief = compactor.compact(self._messages, self.session_id)
                seed = compactor.build_seeded_context(brief)
                # Reset messages with the seeded context as the first entry
                self._messages = [{"role": "system", "content": seed}]
                print(
                    f"[CognitiveLoop] Context compacted for session "
                    f"{self.session_id[:8]}..."
                )
        except Exception as e:
            print(f"[CognitiveLoop] Context compaction skipped: {e}")

    def _enhance_prompt(self, prompt: str) -> str:
        """
        Expand prompts shorter than the trust-adjusted threshold into precise,
        actionable form.

        Threshold shrinks as trust grows (system knows the user better):
          trust 1-2: expand if < 15 words (default — user is new)
          trust 3:   expand if < 11 words
          trust 4:   expand if <  7 words
          trust 5:   expand if <  5 words (minimal friction — shorthand mastered)

        Priority order:
          1. UserModel.get_intent_expansion() — uses founder's communication
             profile. Only active at trust_level >= 3. Takes priority because
             it understands domain-specific shorthand.
          2. Generic Haiku enhancement — fires when user model can't expand
             or trust_level is too low.
        """
        # Greeting guard — never enhance casual greetings or status checks
        # Must be first — before threshold check and before any expansion path
        _greeting_signals = [
            "hey",
            "hi",
            "hello",
            "morning",
            "good morning",
            "gm",
            "what's up",
            "whats up",
            "sup",
            "yo",
            "how are",
            "how's it",
            "hows it",
            "what's going on",
            "wassup",
            "good evening",
            "good afternoon",
            "evening",
            "night",
        ]
        _p = prompt.lower().strip().rstrip("?!.")
        if any(
            _p == g or _p.startswith(g + " ") or _p.startswith(g + ",")
            for g in _greeting_signals
        ):
            return prompt  # Never enhance greetings

        try:
            from eos_ai.user_model import UserModel

            _um = UserModel(self.ctx)
            _trust = _um.get_trust_level()
            # trust 1→15, trust 2→13, trust 3→11, trust 4→9, trust 5→5
            threshold = max(5, 15 - (_trust * 2))
        except Exception:
            threshold = 15

        if len(prompt.split()) >= threshold:
            return prompt

        # Guard: never enhance greetings or casual messages
        _greeting_signals = [
            "hey",
            "hi",
            "hello",
            "morning",
            "good morning",
            "what's up",
            "whats up",
            "sup",
            "yo",
            "how are",
            "how's it",
            "hows it",
            "what's going on",
        ]
        _prompt_lower = prompt.lower().strip()
        if any(
            _prompt_lower.startswith(g) or _prompt_lower == g for g in _greeting_signals
        ):
            return prompt  # Never enhance greetings

        # 1. User model expansion (profile-aware, higher fidelity)
        try:
            from eos_ai.user_model import UserModel

            um = UserModel(self.ctx)
            expanded = um.get_intent_expansion(prompt)
            if expanded != prompt:
                return expanded
        except Exception:
            pass  # user model is enhancement — never block execution

        # 2. Generic Haiku enhancement fallback
        try:
            # Build context-aware enhancement prompt
            _ctx_hint = ""
            try:
                _ctx_hint = (
                    f"Business context: Lyfe Institute (Initiate Arena, $750, "
                    f"90-day program, men 18-25). "
                    f"Empyrean Creative (AI infrastructure, creative studio). "
                    f"DEX is the name of the AI Executive Assistant — "
                    f"never expand DEX as decentralized exchange. "
                    f"Founder: Antony Munoz. North star: $10K/month. Stage 1 validation.\n\n"
                )
            except Exception:
                pass

            # Detect greetings and casual messages — never enhance these
            _greeting_signals = [
                "hey",
                "hi",
                "hello",
                "morning",
                "good morning",
                "what's up",
                "whats up",
                "sup",
                "yo",
                "how are",
                "how's it",
                "hows it",
                "what's going on",
            ]
            _prompt_lower = prompt.lower().strip()
            _is_greeting = any(
                _prompt_lower.startswith(g) or _prompt_lower == g
                for g in _greeting_signals
            )
            if _is_greeting:
                return prompt  # Never enhance greetings

            enhancement = self.runtime.run(
                task_type=TaskType.CLASSIFY,
                prompt=(
                    _ctx_hint
                    + "You are expanding a founder's shorthand message into a "
                    "precise, actionable execution prompt for their AI EA. "
                    "Preserve the original intent exactly. Do not add unrelated "
                    "context. Return ONLY the expanded prompt, nothing else:\n\n"
                    + prompt
                ),
                agent="prompt_engine",
            )
            expanded = enhancement.output.strip()
            return expanded if expanded else prompt
        except Exception:
            return prompt

    def _verify_output(
        self,
        output: str,
        original_prompt: str,
        task_type: TaskType,
    ) -> dict:
        """
        Quick quality check. Returns {'passes': bool, 'issues': str|None}.
        Scoring and classification tasks always pass — they are structured
        by design. Generation tasks get a Haiku PASS/FAIL review.
        """
        if len(output) < 50:
            return {"passes": False, "issues": "Output too short"}

        if task_type in (TaskType.SCORE, TaskType.CLASSIFY):
            return {"passes": True, "issues": None}

        try:
            check = self.runtime.run(
                task_type=TaskType.CLASSIFY,
                prompt=(
                    "Does this output adequately address the request? "
                    "Reply with PASS or FAIL and one sentence why.\n\n"
                    f"Request: {original_prompt[:200]}\n\n"
                    f"Output: {output[:500]}"
                ),
                agent="quality_checker",
            )
            passes = "PASS" in check.output.upper()
            return {
                "passes": passes,
                "issues": check.output if not passes else None,
            }
        except Exception:
            return {"passes": True, "issues": None}  # never block on checker failure

    def _reflect(
        self,
        prompt: str,
        output: str,
        iterations: int,
    ) -> dict:
        """
        Extract insight from the run. Only meaningful when iterations > 0
        (i.e., first attempt failed quality check).
        """
        if iterations == 0:
            return {"insight": None}
        return {
            "insight": (
                f"Required {iterations + 1} iterations. "
                "Prompt may benefit from more specificity."
            )
        }

    def process_in_order(
        self,
        input: "str | MultimodalInput",
        agent: str,
        task_type: TaskType,
        venture_id: str | None = None,
        **kwargs,
    ) -> "CognitiveResult":
        """
        Process a message and attach a monotonic turn number to the result.

        Callers that need strict ordering (e.g. the Telegram handler after
        the per-chat lock is acquired) should use this instead of run() so
        the result carries a turn_number they can use for logging / ordering
        assertions.

        turn N+1 is never assigned until turn N's run() returns, because
        this method is synchronous — the real sequencing guarantee comes from
        the asyncio per-chat lock in the Telegram handler.
        """
        turn = self._turn_counter
        self._turn_counter += 1
        result = self.run(
            input=input,
            agent=agent,
            task_type=task_type,
            venture_id=venture_id,
            **kwargs,
        )
        result.turn_number = turn  # type: ignore[attr-defined]
        return result

    def _infer_action_type(self, task_type: TaskType) -> str:
        """Map TaskType to authority engine action type string."""
        mapping = {
            "SCORE": "analyze",
            "CLASSIFY": "classify",
            "SUMMARIZE": "analyze",
            "ANALYZE": "analyze",
            "GENERATE": "draft_message",
        }
        key = (
            task_type.value.upper()
            if hasattr(task_type, "value")
            else str(task_type).upper()
        )
        return mapping.get(key, "analyze")

    def _map_task_to_domain(
        self,
        task_type: TaskType,
        context: str = "",
    ) -> str | None:
        """
        Map a TaskType + context to the most relevant knowledge domain key.
        Returns None when no strong mapping exists.

        GENERATE → business_sales (outreach/close context) or business_marketing (content)
        ANALYZE  → business_sales (lead/dm context) or business_strategy (general)
        CLASSIFY → human_psychology (default — classifying behavior/intent)
        SCORE    → human_psychology (lead scoring = reading human signals)
        SUMMARIZE → None (pure distillation, no domain enrichment needed)
        """
        ctx_lower = context.lower()
        task_val = task_type.value if hasattr(task_type, "value") else str(task_type)

        if task_val == "generate":
            sales_words = (
                "outreach",
                "dm",
                "close",
                "follow",
                "prospect",
                "lead",
                "pitch",
            )
            if any(w in ctx_lower for w in sales_words):
                return "business_sales"
            return "business_marketing"

        if task_val == "analyze":
            sales_words = (
                "lead",
                "dm",
                "conversation",
                "objection",
                "close",
                "pipeline",
            )
            finance_words = (
                "revenue",
                "cash",
                "profit",
                "unit economics",
                "burn",
                "cost",
            )
            ops_words = ("process", "workflow", "bottleneck", "automate", "system")
            if any(w in ctx_lower for w in sales_words):
                return "business_sales"
            if any(w in ctx_lower for w in finance_words):
                return "business_finance"
            if any(w in ctx_lower for w in ops_words):
                return "business_operations"
            return "business_strategy"

        if task_val == "classify":
            return "human_psychology"

        if task_val == "score":
            return "human_psychology"

        return None


# ─── Natural language intent detection ────────────────────────────────────────


def _format_intent_context(intent_data: dict) -> str:
    """Format intent data for system prompt injection."""
    parts = []
    intent = intent_data.get("intent", "")

    if intent == "okr_check" and intent_data.get("okr_data"):
        parts.append(f"OKR data:\n{intent_data['okr_data']}")

    if intent == "send_email" and intent_data.get("pending_email"):
        pe = intent_data["pending_email"]
        parts.append(f"Pending email to {pe['to']}:\n{pe['preview']}")

    if intent == "calendar" and intent_data.get("upcoming_events"):
        events = intent_data["upcoming_events"]
        parts.append(
            "Upcoming events:\n"
            + "\n".join(f"- {e['start']}: {e['title']}" for e in events)
        )

    if intent == "financial" and intent_data.get("expense_summary"):
        s = intent_data["expense_summary"]
        parts.append(
            f"Monthly expenses: ${s.get('total', 0):,.2f}\n"
            f"Transactions: {s.get('count', 0)}"
        )

    if intent == "relationship_lookup" and intent_data.get("person_profile"):
        parts.append(f"Profile:\n{intent_data['person_profile']}")

    if intent == "tasks" and intent_data.get("pending_tasks"):
        tasks = intent_data["pending_tasks"]
        parts.append("Pending tasks:\n" + "\n".join(f"- {t}" for t in tasks[:5]))

    if intent_data.get("hint"):
        parts.append(f"Hint: {intent_data['hint']}")

    return "\n".join(parts)


def detect_intent_and_inject(
    text: str,
    req: dict,
    ctx,
) -> dict:
    """
    Detect founder intent from natural language and inject
    the right capability context into the system prompt.

    This is what makes DEX conversational — no commands needed.
    """
    text_lower = text.lower()
    injections: dict = {}

    # Meeting minutes intent
    if any(
        p in text_lower
        for p in [
            "meeting minutes",
            "minutes from",
            "minutes for",
            "draft minutes",
            "write up the meeting",
            "document what we discussed",
        ]
    ):
        injections["intent"] = "meeting_minutes"
        injections["capability"] = "draft_meeting_minutes"
        try:
            from eos_ai.meetings import draft_meeting_minutes  # noqa: F401

            injections["capability_available"] = True
        except Exception:
            pass

    # OKR intent
    elif any(
        p in text_lower
        for p in [
            "okr",
            "key result",
            "objective",
            "quarterly goal",
            "how are we tracking",
            "progress this quarter",
            "are we on track",
        ]
    ):
        injections["intent"] = "okr_check"
        try:
            from eos_ai.okr_tracker import generate_okr_report

            report = generate_okr_report(ctx)
            injections["okr_data"] = report
        except Exception:
            pass

    # Email send intent
    elif any(
        p in text_lower
        for p in [
            "send that email",
            "send the email",
            "send it",
            "approve that",
            "go ahead and send",
            "send the follow up",
            "send the follow-up",
            "send that follow up",
            "send that followup",
        ]
    ):
        injections["intent"] = "send_email"
        try:
            from eos_ai.db import get_conn
            import json as _j

            with get_conn(ctx.org_id) as cur:
                cur.execute(
                    """
                    SELECT id, payload_json FROM events
                    WHERE org_id = %s
                    AND event_type = \'email_draft_pending\'
                    AND payload_json->>\'status\' = \'pending_approval\'
                    ORDER BY created_at DESC LIMIT 1
                """,
                    (str(ctx.org_id),),
                )
                row = cur.fetchone()
            if row:
                p = row["payload_json"]
                if isinstance(p, str):
                    p = _j.loads(p)
                injections["pending_email"] = {
                    "to": p.get("to_email", ""),
                    "preview": p.get("draft", "")[:200],
                    "event_id": str(row["id"]),
                }
                injections["hint"] = (
                    "There is a pending email. "
                    "Confirm with founder then send via "
                    "gws_connector.send_email()"
                )
        except Exception:
            pass

    # Calendar/scheduling intent
    elif any(
        p in text_lower
        for p in [
            "schedule",
            "book a call",
            "set up a meeting",
            "find a time",
            "block",
            "add to calendar",
            "what's on my calendar",
            "what do i have",
            "any meetings",
            "free thursday",
            "conflicts",
        ]
    ):
        injections["intent"] = "calendar"
        try:
            from eos_ai.gws_connector import GWSConnector

            gws = GWSConnector()
            events = gws.get_upcoming_events(days=7)
            injections["upcoming_events"] = [
                {
                    "title": e.get("title", e.get("summary", "")),
                    "start": str(e.get("start", ""))[:16],
                }
                for e in events[:10]
            ]
        except Exception:
            pass

    # Travel intent
    elif any(
        p in text_lower
        for p in [
            "trip to",
            "flying to",
            "traveling to",
            "travel to",
            "going to",
            "conference in",
            "book flights",
            "find hotels",
            "itinerary",
        ]
    ):
        injections["intent"] = "travel"

    # Expense/financial intent
    elif any(
        p in text_lower
        for p in [
            "expenses",
            "how much did i spend",
            "spending",
            "invoice",
            "invoices",
            "subscriptions",
            "what do i owe",
            "budget",
        ]
    ):
        injections["intent"] = "financial"
        try:
            from eos_ai.expense_tracker import get_monthly_summary

            summary = get_monthly_summary(ctx)
            injections["expense_summary"] = summary
        except Exception:
            pass

    # People/relationship intent
    elif any(
        p in text_lower
        for p in [
            "what do i know about",
            "tell me about",
            "who is",
            "relationship with",
            "last time i talked",
            "when did i last",
            "contact",
        ]
    ):
        injections["intent"] = "relationship_lookup"
        for trigger in [
            "what do i know about",
            "tell me about",
            "who is",
            "relationship with",
        ]:
            if trigger in text_lower:
                name_part = text_lower.split(trigger)[-1].strip()
                name = name_part.split("?")[0].strip().title()
                if name:
                    try:
                        from eos_ai.person_recognition import (
                            build_intelligence_profile,
                            format_intelligence_profile,
                        )

                        profile = build_intelligence_profile(name=name)
                        if profile:
                            injections["person_profile"] = format_intelligence_profile(
                                profile
                            )
                    except Exception:
                        pass
                break

    # Task/action items intent
    elif any(
        p in text_lower
        for p in [
            "what do i need to do",
            "my tasks",
            "action items",
            "what's on my plate",
            "what should i focus on",
            "priorities",
            "to do",
        ]
    ):
        injections["intent"] = "tasks"
        try:
            from eos_ai.db import get_conn
            import json as _j

            with get_conn(ctx.org_id) as cur:
                cur.execute(
                    """
                    SELECT payload_json FROM events
                    WHERE org_id = %s
                    AND event_type = \'dex_task\'
                    AND (payload_json->>\'status\' IS NULL
                         OR payload_json->>\'status\' = \'pending\')
                    ORDER BY created_at DESC LIMIT 10
                """,
                    (str(ctx.org_id),),
                )
                rows = cur.fetchall()
            tasks = []
            for r in rows:
                p = r["payload_json"]
                if isinstance(p, str):
                    p = _j.loads(p)
                if p.get("task"):
                    tasks.append(p["task"])
            injections["pending_tasks"] = tasks
        except Exception:
            pass

    # Drive/document intent
    elif any(
        p in text_lower
        for p in [
            "create a doc",
            "write a document",
            "draft a",
            "create a folder",
            "find in drive",
            "organize drive",
            "drive audit",
        ]
    ):
        injections["intent"] = "document"

    # Event/speaking intent
    elif any(
        p in text_lower
        for p in [
            "speaking engagement",
            "podcast",
            "interview",
            "conference",
            "offsite",
            "client dinner",
            "talking points",
            "event planning",
        ]
    ):
        injections["intent"] = "event_speaking"

    return injections
