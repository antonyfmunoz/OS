"""Stage 7: Response footer — append observability footer to response."""

from __future__ import annotations

import logging
import time as _time
from dataclasses import dataclass

from umh.execution.stages import StageContext

_log = logging.getLogger(__name__)

# ── Spend cache ──────────────────────────────────────────────────────────────
_spend_cache: dict = {}
_spend_cache_ts: float = 0.0
_SPEND_CACHE_TTL = 60


def _get_neon_spend(org_id: str) -> dict:
    """Return accumulated spend from the interactions table: today, month, all-time."""
    global _spend_cache, _spend_cache_ts

    now = _time.monotonic()
    if _spend_cache and (now - _spend_cache_ts) < _SPEND_CACHE_TTL:
        return _spend_cache

    from umh.storage.adapters.neon import get_conn
    from umh.runtime_engine.agent_runtime import COST_PER_MILLION_TOKENS

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
        _log.debug("Spend query failed: %s", e)
        return fallback


_DISPLAY_MAP = {
    "claude-haiku-4-5-20251001": "Haiku",
    "claude-sonnet-4-6": "Sonnet",
    "claude-opus-4-6": "Opus",
    "sonar-pro": "Perplexity",
    "gemini-2.0-flash": "Gemini Flash",
    "gemma3:4b": "Gemma3 4B (local)",
}


def format_response_footer(
    result,
    iterations: int = 1,
    was_enhanced: bool = False,
    original_prompt: str = "",
    enhanced_prompt: str = "",
    org_id: str | None = None,
) -> str:
    """Build a stats footer for any AgentResult or SpineResult."""
    from umh.runtime_engine.agent_runtime import calculate_cost

    model = getattr(result, "model_used", None) or "unknown"
    cost = getattr(result, "cost_usd", 0.0) or calculate_cost(
        model, getattr(result, "tokens_used", None) or {}
    )
    duration = getattr(result, "duration_ms", 0) or 0
    skill = getattr(result, "skill_used", None) or "—"
    tokens = getattr(result, "tokens_used", None) or {}
    total_tokens = tokens.get("total", 0)

    if model.startswith("claude_cli/tmux:"):
        _session_name = model.split("tmux:", 1)[1]
        model_display = f"Opus (CLI {_session_name})"
    else:
        model_display = _DISPLAY_MAP.get(model, model)

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
        lines.append("✨  Optimized prompt:")
        lines.append(f"    Original: {original_prompt}")
        lines.append(f"    Enhanced: {enhanced_prompt}")

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


@dataclass(frozen=True)
class ResponseFooterStage:
    name: str = "response_footer"
    description: str = "Append model/cost/token footer to response text"
    dependencies: tuple[str, ...] = ("commit",)
    can_abort: bool = False

    def run(self, context: StageContext) -> StageContext:
        try:
            from umh.runtime_engine.agent_runtime import AgentResult

            _footer_result = AgentResult(
                output=context.response,
                model_used=context.model_used,
                tokens_used=context.tokens_used,
                skill_used=context.skill_name,
            )
            footer = format_response_footer(
                result=_footer_result,
                iterations=context.iterations,
                was_enhanced=context.was_enhanced,
                original_prompt=context.original_message,
                enhanced_prompt=context.message if context.was_enhanced else "",
                org_id=context.org_id,
            )
            context.response = context.response + footer
        except Exception as e:
            _log.debug("Footer generation skipped: %s", e)
        return context
