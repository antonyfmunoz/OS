"""
IntentRouter — classify founder messages to the correct agent domain.

Lightweight keyword routing layer. Runs before the cognitive loop
so the right agent gets context injected before it responds.

Usage:
    from substrate.control_plane.router.intent_router import IntentRouter, IntentDomain
    ir = IntentRouter(ctx)
    domain = ir.route("How is my portfolio doing?")
    agent  = ir.get_agent(domain)
"""

import os
from enum import Enum

from substrate.state.context.context import SubstrateContext


class IntentDomain(Enum):
    PORTFOLIO = "portfolio"
    CEO = "ceo"
    EA = "ea"
    OUTREACH = "outreach"
    CONTENT = "content"
    RESEARCH = "research"
    GENERAL = "general"


class IntentRouter:
    """
    Keyword-based intent classifier.
    Fast — no LLM call. Runs on every gateway message.
    """

    PORTFOLIO_SIGNALS = [
        "portfolio",
        "all companies",
        "all ventures",
        "overall",
        "empire",
        "holdings",
        "which company",
        "compare",
        "allocation",
        "north star",
        "across my",
        "all three",
    ]

    def __init__(self, ctx: SubstrateContext) -> None:
        self.ctx = ctx
        # Conversational / greeting patterns — must match before CEO to prevent
        # casual questions like "hey <AI> what are we building today?" from
        # escalating to CEO agent. Built dynamically from AI_NAME.
        _ai_lower = os.environ.get("AI_NAME", "").lower()
        self.CONVERSATION_SIGNALS: list[str] = [
            *(f"{g} {_ai_lower}" for g in ("hey", "hi", "yo") if _ai_lower),
            "what's up",
            "how are you",
            "what are we",
            "what do we",
            "good morning",
            "good afternoon",
            "what's going on",
            "talk to me",
            "hey there",
            "sup",
        ]

    CEO_SIGNALS = [
        "personal brand",
        "revenue",
        "clients",
        "stage",
        "strategy",
        "focus",
        "binding constraint",
        "priority",
        "what should i",
        "performance",
        "business",
    ]

    EA_SIGNALS = [
        "email",
        "inbox",
        "calendar",
        "schedule",
        "meeting",
        "call",
        "book",
        "block time",
        "remind",
        "draft",
        "respond to",
        "sync",
        "daily sync",
        "follow up",
    ]

    OUTREACH_SIGNALS = [
        "dm",
        "outreach",
        "lead",
        "prospect",
        "send message",
        "instagram",
        "pipeline",
        "follow up with",
        "message them",
    ]

    CONTENT_SIGNALS = [
        "post",
        "content",
        "caption",
        "video",
        "reel",
        "story",
        "publish",
        "create content",
        "write a",
    ]

    RESEARCH_SIGNALS = [
        "research",
        "find out",
        "look up",
        "competitor",
        "market",
        "analyze",
        "who is",
        "what is",
        "search for",
    ]

    def route(self, text: str) -> IntentDomain:
        """Classify text into the most specific matching domain."""
        t = text.lower()

        # Conversational greetings → EA before anything else
        if any(s in t for s in self.CONVERSATION_SIGNALS):
            return IntentDomain.EA

        if any(s in t for s in self.PORTFOLIO_SIGNALS):
            return IntentDomain.PORTFOLIO
        if any(s in t for s in self.EA_SIGNALS):
            return IntentDomain.EA
        if any(s in t for s in self.OUTREACH_SIGNALS):
            return IntentDomain.OUTREACH
        if any(s in t for s in self.CONTENT_SIGNALS):
            return IntentDomain.CONTENT
        if any(s in t for s in self.RESEARCH_SIGNALS):
            return IntentDomain.RESEARCH
        if any(s in t for s in self.CEO_SIGNALS):
            return IntentDomain.CEO
        return IntentDomain.GENERAL

    def get_agent(self, domain: IntentDomain) -> str:
        """Map domain to canonical agent_id."""
        return {
            IntentDomain.PORTFOLIO: "portfolio_agent",
            IntentDomain.CEO: "ceo_agent",
            IntentDomain.EA: "executive_assistant",
            IntentDomain.OUTREACH: "outreach_agent",
            IntentDomain.CONTENT: "content_agent",
            IntentDomain.RESEARCH: "research_agent",
            IntentDomain.GENERAL: "executive_assistant",
        }.get(domain, "executive_assistant")
