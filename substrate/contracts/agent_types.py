"""Canonical agent types owned by the substrate layer.

These types define the contract between substrate and adapters for
agent execution. Adapters implement against these types; substrate
consumes them. This is the single source of truth — adapters re-export
for backward compatibility only.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class TaskType(Enum):
    """Task type enum — drives model selection and routing."""

    CONVERSATION = "conversation"
    ANALYSIS = "analysis"
    WEB_SEARCH = "web_search"
    MARKET_INTEL = "market_intel"
    FAST_RESPONSE = "fast_response"
    LONG_CONTEXT = "long_context"
    AUTONOMOUS = "autonomous"
    MULTIMODAL = "multimodal"
    BROWSER_CONTROL = "browser_control"
    SCORE = "score"
    CLASSIFY = "classify"
    ANALYZE = "analyze"
    GENERATE = "generate"
    SUMMARIZE = "summarize"
    STRATEGIC = "strategic"
    CODE = "code"
    RESEARCH = "research"
    SELF_IMPROVE = "self_improve"
    PLAN = "plan"
    COORDINATE = "coordinate"


class ModelProvider(Enum):
    """Known model providers."""

    CLAUDE_CLI = "claude_cli"
    CC_SDK = "cc_sdk"
    ANTHROPIC = "anthropic"
    PERPLEXITY = "perplexity"
    OPENAI = "openai"
    GROQ = "groq"
    OLLAMA = "ollama"
    GEMINI = "gemini"
    CODEX = "codex"
    HERMES = "hermes"
    OPENCODE = "opencode"
    MANUS = "manus"


@dataclass
class AgentResult:
    """Result of an agent execution."""

    output: str
    model_used: str
    tokens_used: dict[str, int]
    skill_used: str | None
    interaction_id: int | None = None
    authority: dict | None = None
    cost_usd: float = 0.0
    duration_ms: int = 0


@dataclass
class RoutingResult:
    """Result of a model routing call."""

    output: str
    provider: str
    model: str
    task_type: str
    tokens_used: int = 0
    input_tokens: int = 0
    output_tokens: int = 0
    cost_usd: float = 0.0
    latency_ms: int = 0


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
