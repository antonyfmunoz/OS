"""
Input Intelligence Layer
==========================================
Sits at the gateway level between request intake and cognitive loop dispatch.

Purpose: Implement the Harness Principle.
Any founder, any communication skill level, gets world-class output.
The system elevates the input — the user never has to learn to prompt.

Architecture:
  Gateway.handle()
    → InputIntelligence.process()   ← THIS MODULE
      → _route_agent_task()
        → CognitiveLoop

Three-stage pipeline per request:
  1. ASSESS   — is this input underpowered, clear, or a non-task?
  2. ENHANCE  — if underpowered, elevate to world-class execution prompt
  3. ANNOTATE — attach enhancement metadata for transparency in footer

Enhancement rules (in priority order):
  1. Non-task signals (greetings, human moments) → never enhance, pass through
  2. Clear, complete inputs → never enhance, pass through
  3. Vague business inputs → enhance with full venture context
  4. Ultra-short inputs (< 4 words, not a greeting) → enhance with intent inference

The enhancer never:
  - Changes the user's intent
  - Adds goals the user didn't express
  - Generates prompts outside the venture context
  - Fires on greetings, check-ins, or human moments
"""

import re
import logging
import os
from dataclasses import dataclass

logger = logging.getLogger(__name__)

# ─────────────────────────────────────────────
# SIGNAL DEFINITIONS
# ─────────────────────────────────────────────

# Messages that are human moments — never enhance
_GREETING_SIGNALS = {
    "hey", "hi", "hello", "morning", "good morning", "gm",
    "good evening", "good afternoon", "evening", "night",
    "what's up", "whats up", "sup", "yo", "how are you",
    "how are you doing", "how's it going", "hows it going",
    "what's going on", "whats going on", "wassup",
    "how you doing", "how are things",
}
# Add AI-name-specific greetings at import time
_ai_lower = os.environ.get("AI_NAME", "").lower()
if _ai_lower:
    _GREETING_SIGNALS.update({f"hey {_ai_lower}", f"hi {_ai_lower}"})

# Messages that are status checks — pass through, already clear
_STATUS_SIGNALS = {
    "status", "update", "brief", "morning brief", "daily brief",
    "give me the brief", "what's the update", "how are we doing",
    "pipeline", "what's happening", "anything going on",
}

# Business domains that signal the input needs venture context
_BUSINESS_SIGNALS = [
    "outreach", "dm", "message", "post", "content", "caption",
    "email", "lead", "sales", "close", "offer", "icp",
    "instagram", "twitch", "audience", "followers",
    "revenue", "money", "pricing", "sell",
    "research", "analyze", "report", "intelligence",
    "strategy", "plan", "roadmap", "next step",
    "marketing", "campaign", "funnel", "conversion",
    "hire", "team", "agent", "workflow", "automate",
    "brand", "content", "video", "script",
]


# ─────────────────────────────────────────────
# DATA CLASSES
# ─────────────────────────────────────────────

@dataclass
class InputAssessment:
    """Result of assessing an input's quality and enhancement needs."""
    original: str
    signal_type: str          # "greeting" | "status" | "clear" | "vague" | "ultra_short"
    should_enhance: bool
    confidence: float         # 0.0 - 1.0
    reason: str


@dataclass
class EnhancedInput:
    """Result of the full input intelligence pipeline."""
    original: str
    enhanced: str
    was_enhanced: bool
    signal_type: str
    enhancement_reason: str


# ─────────────────────────────────────────────
# CORE CLASS
# ─────────────────────────────────────────────

class InputIntelligence:
    """
    Gateway-level input intelligence layer.
    Processes every agent_task request before it reaches the cognitive loop.
    """

    def __init__(self, ctx=None, venture_id: str = None):
        self.ctx = ctx
        self.venture_id = venture_id
        self._venture_context = None

    def process(self, prompt: str, venture_id: str = None) -> EnhancedInput:
        """
        Main entry point. Assess and optionally enhance the input.
        Always returns an EnhancedInput — safe to use even if enhancement is skipped.
        """
        if not prompt or not prompt.strip():
            return EnhancedInput(
                original=prompt,
                enhanced=prompt,
                was_enhanced=False,
                signal_type="empty",
                enhancement_reason="Empty input — passed through",
            )

        vid = venture_id or self.venture_id
        assessment = self._assess(prompt)

        if not assessment.should_enhance:
            return EnhancedInput(
                original=prompt,
                enhanced=prompt,
                was_enhanced=False,
                signal_type=assessment.signal_type,
                enhancement_reason=assessment.reason,
            )

        # Enhance
        enhanced = self._enhance(prompt, assessment, vid)

        if not enhanced or enhanced.strip() == prompt.strip():
            return EnhancedInput(
                original=prompt,
                enhanced=prompt,
                was_enhanced=False,
                signal_type=assessment.signal_type,
                enhancement_reason="Enhancement produced no change — passed through",
            )

        return EnhancedInput(
            original=prompt,
            enhanced=enhanced,
            was_enhanced=True,
            signal_type=assessment.signal_type,
            enhancement_reason=assessment.reason,
        )

    # ─────────────────────────────────────────
    # ASSESSMENT
    # ─────────────────────────────────────────

    def _assess(self, prompt: str) -> InputAssessment:
        """
        Determine the signal type and whether enhancement is warranted.
        Priority order matters — check from most specific to least.
        """
        normalized = prompt.lower().strip().rstrip("?!.,")
        normalized = normalized.replace('\u2019', "'").replace('\u2018', "'")

        # 1. Greeting / human moment — never enhance
        if self._is_greeting(normalized):
            return InputAssessment(
                original=prompt,
                signal_type="greeting",
                should_enhance=False,
                confidence=0.95,
                reason="Human moment — passed through as-is",
            )

        # 2. Status check — clear intent, no enhancement needed
        if self._is_status_check(normalized):
            return InputAssessment(
                original=prompt,
                signal_type="status",
                should_enhance=False,
                confidence=0.90,
                reason="Status request — clear intent, no enhancement needed",
            )

        word_count = len(prompt.split())

        # 3. Long, detailed input — already well-specified
        if word_count >= 20:
            return InputAssessment(
                original=prompt,
                signal_type="clear",
                should_enhance=False,
                confidence=0.85,
                reason="Input is detailed and complete — no enhancement needed",
            )

        # 4. Contains business signals but is vague (4-19 words)
        if 4 <= word_count < 20 and self._has_business_signal(normalized):
            return InputAssessment(
                original=prompt,
                signal_type="vague",
                should_enhance=True,
                confidence=0.80,
                reason=f"Business intent detected but under-specified ({word_count} words) — elevating",
            )

        # 5. Ultra-short with business signal (< 4 words)
        if word_count < 4 and self._has_business_signal(normalized):
            return InputAssessment(
                original=prompt,
                signal_type="ultra_short",
                should_enhance=True,
                confidence=0.75,
                reason=f"Ultra-short business input ({word_count} words) — inferring intent and elevating",
            )

        # 6. Default — pass through, unclear if enhancement would help
        return InputAssessment(
            original=prompt,
            signal_type="clear",
            should_enhance=False,
            confidence=0.60,
            reason="No clear enhancement signal — passed through",
        )

    def _is_greeting(self, normalized: str) -> bool:
        """Check if the input is a greeting or human moment."""
        # Normalize curly apostrophes to straight — phone keyboards use curly
        normalized = normalized.replace('\u2019', "'").replace('\u2018', "'")
        if normalized in _GREETING_SIGNALS:
            return True
        for g in _GREETING_SIGNALS:
            if normalized.startswith(g + " ") or normalized.startswith(g + ","):
                return True
        return False

    def _is_status_check(self, normalized: str) -> bool:
        """Check if the input is a status check that's already clear."""
        return any(s in normalized for s in _STATUS_SIGNALS)

    def _has_business_signal(self, normalized: str) -> bool:
        """Check if the input contains business-relevant language."""
        return any(signal in normalized for signal in _BUSINESS_SIGNALS)

    # ─────────────────────────────────────────
    # ENHANCEMENT
    # ─────────────────────────────────────────

    def _enhance(self, prompt: str, assessment: InputAssessment,
                 venture_id: str = None) -> str:
        """
        Elevate an underpowered input to a world-class execution prompt.
        Uses Haiku with full venture context — fast and cheap.
        """
        try:
            from substrate.contracts.agent_types import TaskType
            from adapters.models.agent_runtime import AgentRuntime
            from substrate.state.context.context import load_context_from_env

            ctx = self.ctx or load_context_from_env()
            runtime = AgentRuntime(ctx)

            venture_context = self._get_venture_context(venture_id)

            system_prompt = f"""You are an input intelligence layer for UMH.

Your job: convert a founder's short or vague message into a precise,
actionable execution prompt that will get world-class output from an AI agent.

CRITICAL RULES:
- Never change the founder's intent — only clarify and expand it
- Never add goals the founder didn't express
- Never reference concepts outside the venture context below
- Output ONLY the enhanced prompt — no explanation, no preamble
- If the input is already clear, return it unchanged
- Keep the enhanced prompt under 150 words
- Write in first person as the founder

VENTURE CONTEXT:
{venture_context}

SIGNAL TYPE: {assessment.signal_type}
ORIGINAL INPUT: {prompt}

Produce the enhanced execution prompt:"""

            result = runtime.run(
                task_type=TaskType.CLASSIFY,
                prompt=f"Enhance this input for execution: {prompt}",
                system_extra=system_prompt,
                max_tokens=200,
            )

            enhanced = result.output.strip() if result and result.output else prompt

            # Safety check — only revert if output is clearly broken (empty or absurdly long)
            if not enhanced or len(enhanced) > 2000:
                logger.warning("Enhancement produced broken output — reverting")
                return prompt

            return enhanced

        except Exception as e:
            logger.warning(f"InputIntelligence enhancement failed: {e}")
            return prompt

    def _get_venture_context(self, venture_id: str = None) -> str:
        """Build a compact venture context string for the enhancement prompt."""
        try:
            if venture_id:
                from substrate.state.business.business_instance import BusinessInstanceManager
                bim = BusinessInstanceManager(self.ctx)
                bis = bim.get_bis(venture_id)
                if bis:
                    return (
                        f"Company: {bis.company_name or venture_id}\n"
                        f"Stage: {bis.current_stage}\n"
                        f"North Star: {bis.north_star}\n"
                        f"Active Offer: {getattr(bis, 'active_offer', 'N/A')}\n"
                        f"Primary Channel: {getattr(bis, 'primary_channel', 'N/A')}\n"
                    )
        except Exception:
            pass

        # Fallback — load from instance config
        _ai = os.environ.get("AI_NAME", "AI")
        _founder = os.environ.get("UMH_FOUNDER_NAME", "the founder")
        _org = os.environ.get("UMH_ORG_NAME", "Portfolio")
        _venture = os.environ.get("UMH_ACTIVE_VENTURE", "")
        return (
            f"Portfolio: {_org}\n"
            f"Active venture: {_venture}\n"
            f"Founder: {_founder}\n"
            f"{_ai} = the AI Executive Assistant\n"
        )
