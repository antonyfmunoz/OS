"""Canonical UMH identity — single source of truth.

Every prompt, handler, and UI that references the system name
must import from here. Never scatter identity strings.
"""

from __future__ import annotations

import os
import re

UMH_ACRONYM = "UMH"
UMH_FULL_NAME = "Universal Meta Harness"

UMH_SHORT_DESCRIPTION = (
    "A governed meta-harness and workstation operating layer that lets the "
    "operator converse with the AI advisor, control the cockpit, orchestrate "
    "work packets, route agents and runtimes, govern approvals, control "
    "workstation nodes, inspect traces, proofs, and logs, and compress "
    "execution time across the full operating system."
)

UMH_VOICE_DESCRIPTION = (
    "UMH stands for Universal Meta Harness. It is your governed AI workstation "
    "layer for controlling your advisor, the cockpit, workstation nodes, work "
    "packets, approvals, and agent execution from one interface."
)

_IDENTITY_PATTERNS = [
    re.compile(r"\bwhat\b.*\bumh\b", re.IGNORECASE),
    re.compile(r"\bwhat\b.*\buniversal meta harness\b", re.IGNORECASE),
    re.compile(r"\bumh\b.*\bstand\s*for\b", re.IGNORECASE),
    re.compile(r"\bwhat\s+does\s+umh\b", re.IGNORECASE),
    re.compile(r"\bwhat\s+are\s+you\b", re.IGNORECASE),
    re.compile(r"\bwho\s+are\s+you\b", re.IGNORECASE),
    re.compile(r"\bwhat\s+is\s+this\s+system\b", re.IGNORECASE),
    re.compile(r"\bwhat\s+is\s+the\s+cockpit\b", re.IGNORECASE),
]


def _get_ai_name() -> str:
    """Resolve the AI instance name at runtime."""
    try:
        from substrate.state.business.business_instance import get_ai_name

        name = get_ai_name()
        if name:
            return name
    except Exception:
        pass
    return os.environ.get("UMH_AI_NAME", "AI")


def _ai_identity_pattern() -> re.Pattern[str]:
    """Build a regex for 'what is <ai_name>' dynamically."""
    name = _get_ai_name()
    return re.compile(rf"\bwhat\s+is\s+{re.escape(name)}\b", re.IGNORECASE)


def get_system_identity_context() -> dict[str, str]:
    """Return canonical identity dict for prompt injection."""
    ai_name = _get_ai_name()

    return {
        "umh_acronym": UMH_ACRONYM,
        "umh_full_name": UMH_FULL_NAME,
        "ai_instance_name": ai_name,
        "short_description": UMH_SHORT_DESCRIPTION,
        "voice_description": UMH_VOICE_DESCRIPTION,
    }


def is_identity_question(text: str) -> bool:
    """Return True if the text is asking about UMH or the AI advisor identity."""
    if any(p.search(text) for p in _IDENTITY_PATTERNS):
        return True
    return bool(_ai_identity_pattern().search(text))


def get_identity_answer(text: str, *, voice: bool = False) -> str | None:
    """Return deterministic identity answer, or None if not an identity question."""
    if not is_identity_question(text):
        return None

    ctx = get_system_identity_context()
    ai_name = ctx["ai_instance_name"]
    t = text.lower()

    if "stand for" in t or "what does umh" in t:
        return f"UMH stands for Universal Meta Harness."

    ai_lower = ai_name.lower()
    if (f"what is {ai_lower}" in t or f"who is {ai_lower}" in t
            or (ai_lower in t and ("what is" in t or "who is" in t))):
        if voice:
            return (
                f"{ai_name} is your AI advisor inside UMH. I handle conversation, "
                f"command routing, governance, and orchestration across your full workstation."
            )
        return (
            f"{ai_name} is the operator's named AI instance and advisor interface "
            f"inside UMH (Universal Meta Harness). {ai_name} handles conversational "
            f"advising, command routing, governance-aware approvals, and orchestration "
            f"across the cockpit, workstation nodes, and agent fleet."
        )

    if "what is this system" in t:
        if voice:
            return ctx["voice_description"]
        return f"This is UMH — Universal Meta Harness. {ctx['short_description']}"

    if "what are you" in t or "who are you" in t:
        if voice:
            return (
                f"I'm {ai_name}, your AI advisor inside UMH, Universal Meta Harness. "
                f"I help you control the cockpit, route work, manage approvals, and "
                f"orchestrate agents across your workstation."
            )
        return (
            f"I'm {ai_name}, the operator's AI advisor inside UMH "
            f"(Universal Meta Harness). {ctx['short_description']}"
        )

    if voice:
        return ctx["voice_description"]
    return f"UMH stands for Universal Meta Harness. {ctx['short_description']}"


def get_prompt_grounding(ai_name: str) -> str:
    """Short identity grounding block injected into every LLM prompt."""
    return (
        f"System identity:\n"
        f"- UMH = Universal Meta Harness (NEVER expand as anything else).\n"
        f"- You are {ai_name}, the operator's AI advisor inside UMH.\n"
        f"- If asked what UMH is, answer from canonical identity: "
        f"a governed meta-harness and workstation operating layer.\n"
        f"- Never invent alternative expansions of UMH.\n"
    )
