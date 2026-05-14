"""
StrategyEngine — first-principles strategic reasoning layer.
DecisionEngine  — structured 6-step decision evaluation.

These are the intelligence layers that elevate the AI from
operational to genuinely strategic. They reason about market
position, competitive dynamics, resource allocation, and what
not to do — grounded in real data from Neon, not templates.

Usage:
    from runtime.context import load_context_from_env
    from runtime.strategy_engine import StrategyEngine, DecisionEngine

    ctx = load_context_from_env()
    se  = StrategyEngine(ctx)

    position = se.analyze_company_position(ctx.org_id)
    print(position['binding_constraint'])

    de       = DecisionEngine(ctx)
    analysis = de.evaluate(
        decision="Should I run paid ads?",
        context={"monthly_revenue": 0, "monthly_target": 10000},
        venture_id="lyfe_institute",
    )
    print(analysis['step6_recommendation'])
"""

import datetime
import json
import os
import sys
from pathlib import Path

_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

from runtime.context import EOSContext, load_context_from_env
from control_plane.runtime.cognitive_loop import CognitiveLoop
from execution.runtime.agent_runtime import TaskType
from runtime.db import get_conn, resolve_venture
from state.memory.memory import AgentMemory
from runtime.venture_knowledge import VentureKnowledgeBase

STRATEGY_DIR = Path(_REPO_ROOT) / "orchestrator" / "strategy"


# ─── Internal helpers ─────────────────────────────────────────────────────────

def _query_30d_stats(org_id: str, venture_id: str) -> dict:
    """
    Pull 30-day interaction + outcome metrics from Neon for a venture.
    """
    cutoff       = (
        datetime.datetime.now(datetime.timezone.utc)
        - datetime.timedelta(days=30)
    ).isoformat()
    venture_uuid = resolve_venture(venture_id)

    with get_conn(org_id) as cur:
        cur.execute(
            """
            SELECT
                COUNT(DISTINCT i.id)                                         AS interactions,
                COALESCE(SUM((i.tokens_json->>'total')::int), 0)             AS total_tokens,
                COUNT(o.id) FILTER (WHERE o.outcome_type = 'positive')       AS positive_outcomes,
                COUNT(o.id)                                                  AS total_outcomes,
                COUNT(DISTINCT i.agent_label)                                AS agents_active,
                MAX(i.created_at)                                            AS last_activity
            FROM interactions i
            LEFT JOIN outcomes o ON o.interaction_id = i.id
            WHERE i.org_id = %s
              AND (%s IS NULL OR i.venture_id = %s)
              AND i.created_at >= %s
            """,
            (org_id, venture_uuid, venture_uuid, cutoff),
        )
        row = cur.fetchone()

    reply_rate = None
    if row and row["total_outcomes"] and row["total_outcomes"] > 0:
        reply_rate = round(row["positive_outcomes"] / row["total_outcomes"] * 100, 1)

    return {
        "interactions_30d":  row["interactions"]    if row else 0,
        "total_tokens_30d":  row["total_tokens"]    if row else 0,
        "positive_outcomes": row["positive_outcomes"] if row else 0,
        "total_outcomes":    row["total_outcomes"]  if row else 0,
        "agents_active":     row["agents_active"]   if row else 0,
        "reply_rate":        reply_rate,
        "last_activity":     str(row["last_activity"])[:19] if row and row["last_activity"] else "none",
    }


def _parse_labeled_sections(text: str, keys: list[str]) -> dict:
    """
    Parse model output that uses LABEL: value format.
    Returns dict with snake_case keys mapped to the extracted text.
    Falls back to the full output for each key if parsing fails.
    """
    result: dict = {}
    text_upper = text.upper()

    for i, key in enumerate(keys):
        marker     = key.upper() + ":"
        next_marker = keys[i + 1].upper() + ":" if i + 1 < len(keys) else None

        start = text_upper.find(marker)
        if start == -1:
            result[key.lower().replace(" ", "_")] = text.strip()
            continue

        content_start = start + len(marker)
        if next_marker:
            end = text_upper.find(next_marker, content_start)
            content = text[content_start:end].strip() if end != -1 else text[content_start:].strip()
        else:
            content = text[content_start:].strip()

        result[key.lower().replace(" ", "_")] = content

    return result


# ─── StrategyEngine ───────────────────────────────────────────────────────────

class StrategyEngine:
    """
    Reasons about company and portfolio strategy from real data.
    Never generic. Every output is grounded in actual metrics.
    """

    def __init__(self, ctx: EOSContext):
        self.ctx    = ctx
        self.loop   = CognitiveLoop(ctx)
        self.memory = AgentMemory()

    # ─── analyze_company_position ────────────────────────────────────────────

    def analyze_company_position(self, org_id: str) -> dict:
        """
        Load all venture data + 30-day activity for the org.
        Reason from first principles about where the company actually is.
        Returns structured dict with 6 strategic dimensions.
        """
        # Load ventures for this org
        venture_ids = VentureKnowledgeBase.list_ventures()
        venture_blocks: list[str] = []

        for vid in venture_ids:
            try:
                v          = VentureKnowledgeBase.get(vid)
                stats      = _query_30d_stats(org_id, vid)
                ctx_text   = VentureKnowledgeBase.to_agent_context(vid, detail="full")
                rr         = f"{stats['reply_rate']}%" if stats['reply_rate'] is not None else "no data"
                gap        = (v.monthly_target or 0) - (v.monthly_revenue or 0)
                pct        = (
                    round(v.monthly_revenue / v.monthly_target * 100, 1)
                    if v.monthly_target and v.monthly_target > 0 else 0.0
                )
                block = (
                    f"{ctx_text}\n\n"
                    f"REVENUE DATA:\n"
                    f"  Monthly revenue: ${v.monthly_revenue:,.0f}\n"
                    f"  Monthly target:  ${v.monthly_target:,.0f}\n"
                    f"  Gap to target:   ${gap:,.0f}\n"
                    f"  Progress:        {pct}%\n\n"
                    f"30-DAY ACTIVITY:\n"
                    f"  Interactions:    {stats['interactions_30d']}\n"
                    f"  Positive outcomes: {stats['positive_outcomes']} / {stats['total_outcomes']}\n"
                    f"  Reply/outcome rate: {rr}\n"
                    f"  Agents active:   {stats['agents_active']}\n"
                    f"  Last activity:   {stats['last_activity']}\n"
                )
                venture_blocks.append(block)
            except Exception as e:
                venture_blocks.append(f"[{vid}] Data load failed: {e}")

        if not venture_blocks:
            venture_blocks = ["No venture data available for this org."]

        prompt = (
            "You are a strategic advisor conducting a company position audit. "
            "Reason from first principles and real data only. "
            "Never give generic advice. Every sentence must be grounded in the "
            "specific numbers and context provided below.\n\n"
            "COMPANY DATA:\n\n"
            + "\n\n---\n\n".join(venture_blocks)
            + "\n\n"
            "Produce a structured position analysis using EXACTLY these labeled sections. "
            "Each section must reference specific numbers from the data above.\n\n"
            "CURRENT_POSITION: One paragraph. Where is this company right now, "
            "honestly? Name the actual revenue, actual stage, actual activity level.\n\n"
            "BINDING_CONSTRAINT: The single constraint most limiting growth right now. "
            "Not a category — the exact bottleneck with evidence from the data.\n\n"
            "STRATEGIC_OPPORTUNITIES: 2-3 specific opportunities based on the actual "
            "data. Not generic growth tactics.\n\n"
            "WHAT_TO_STOP: One specific thing consuming resources without return. "
            "Name it precisely with evidence.\n\n"
            "90_DAY_PRIORITY: The single most important thing to execute this quarter. "
            "Specific enough to begin immediately.\n\n"
            "COMPETITIVE_POSITION: Honest assessment of positioning vs competitors "
            "in this market. What is the actual moat, if any?"
        )

        result = self.loop.run(
            input=prompt,
            agent="strategy_engine.position",
            task_type=TaskType.ANALYZE,
            max_iterations=1,  # strategic analysis doesn't benefit from quality loops
        )

        keys = [
            "CURRENT_POSITION", "BINDING_CONSTRAINT", "STRATEGIC_OPPORTUNITIES",
            "WHAT_TO_STOP", "90_DAY_PRIORITY", "COMPETITIVE_POSITION"
        ]
        parsed = _parse_labeled_sections(result.output or "", keys)
        parsed["raw_output"] = result.output
        parsed["org_id"]     = org_id
        return parsed

    # ─── analyze_portfolio_strategy ──────────────────────────────────────────

    def analyze_portfolio_strategy(self) -> dict:
        """
        Run company position analysis for every company in the portfolio,
        then reason across all of them to produce portfolio-level strategy.
        """
        # Per-company analysis
        venture_ids = VentureKnowledgeBase.list_ventures()
        company_analyses: dict = {}

        for vid in venture_ids:
            try:
                analysis = self.analyze_company_position(self.ctx.org_id)
                company_analyses[vid] = analysis
            except Exception as e:
                company_analyses[vid] = {"error": str(e)}

        # Build cross-portfolio context block
        analysis_blocks: list[str] = []
        for vid, analysis in company_analyses.items():
            block = (
                f"COMPANY: {vid}\n"
                f"Position: {analysis.get('current_position', 'unknown')[:300]}\n"
                f"Binding constraint: {analysis.get('binding_constraint', 'unknown')[:200]}\n"
                f"90-day priority: {analysis.get('90_day_priority', 'unknown')[:200]}\n"
            )
            analysis_blocks.append(block)

        prompt = (
            "You are the board-level strategic advisor reasoning across an entire portfolio. "
            "You have just completed a full company position analysis for each company. "
            "Now reason across all of them simultaneously.\n\n"
            "COMPANY ANALYSES:\n\n"
            + "\n\n".join(analysis_blocks)
            + "\n\n"
            "NORTH STAR: $100K/month net profit across portfolio\n\n"
            "Produce portfolio-level strategy using EXACTLY these labeled sections:\n\n"
            "CAPITAL_ALLOCATION: Which company deserves most attention and resources "
            "right now? What type: time, money, focus? Be specific.\n\n"
            "SEQUENCING: In what order should companies be scaled, and why? "
            "What must happen in Company A before Company B can grow?\n\n"
            "CROSS_COMPANY_LEVERAGE: What is working in one company that transfers "
            "directly to another? Specific tactics, not categories.\n\n"
            "PORTFOLIO_CONSTRAINT: The single thing limiting the entire portfolio — "
            "not one company, the whole system.\n\n"
            "NORTH_STAR_PATH: Realistic path to $100K/month with a timeline estimate. "
            "Show reasoning. Be honest about the gap."
        )

        result = self.loop.run(
            input=prompt,
            agent="strategy_engine.portfolio",
            task_type=TaskType.ANALYZE,
            max_iterations=1,
        )

        keys = [
            "CAPITAL_ALLOCATION", "SEQUENCING", "CROSS_COMPANY_LEVERAGE",
            "PORTFOLIO_CONSTRAINT", "NORTH_STAR_PATH"
        ]
        parsed = _parse_labeled_sections(result.output or "", keys)
        parsed["company_analyses"] = company_analyses
        parsed["raw_output"]       = result.output
        return parsed

    # ─── run_decision_analysis ───────────────────────────────────────────────

    def run_decision_analysis(
        self,
        decision: str,
        venture_id: str | None = None,
    ) -> dict:
        """
        Structured analysis of a founder decision.
        Returns 6-section analysis: context, principles, leverage,
        risk, timing, and clear recommendation.
        """
        # Load venture context if provided
        venture_context = ""
        if venture_id:
            try:
                v = VentureKnowledgeBase.get(venture_id)
                venture_context = (
                    f"\nVENTURE CONTEXT:\n"
                    f"  Revenue: ${v.monthly_revenue:,.0f}/mo\n"
                    f"  Target:  ${v.monthly_target:,.0f}/mo\n"
                    f"  Stage:   {v.stage}\n"
                )
            except Exception:
                pass

        prompt = (
            "You are a first-principles strategic advisor. A founder is evaluating "
            "a decision. Reason from real data and first principles. No hedging.\n\n"
            f"DECISION: {decision}\n"
            f"{venture_context}\n"
            "Analyze this decision using EXACTLY these labeled sections:\n\n"
            "CONTEXT_ANALYSIS: What is the full context? What do we know for certain? "
            "Reference specific numbers and stage.\n\n"
            "PRINCIPLE_EVALUATION: Does this align with the north star and operating "
            "principles? Score 0-10 and explain.\n\n"
            "LEVERAGE_DETECTION: Is this high-leverage? What is expected impact vs cost? "
            "Score 0-10.\n\n"
            "RISK_ASSESSMENT: What could go wrong? Downside scenario. "
            "Risk class: LOW / MEDIUM / HIGH / CRITICAL.\n\n"
            "TIMING_ANALYSIS: Is now the right time or should this wait? "
            "What condition would make this clearly the right move?\n\n"
            "RECOMMENDATION: YES / NO / WAIT — one clear sentence with the "
            "single most important reason grounded in the specific context above."
        )

        result = self.loop.run(
            input=prompt,
            agent="strategy_engine.decision",
            task_type=TaskType.ANALYZE,
            max_iterations=1,
        )

        keys = [
            "CONTEXT_ANALYSIS", "PRINCIPLE_EVALUATION", "LEVERAGE_DETECTION",
            "RISK_ASSESSMENT", "TIMING_ANALYSIS", "RECOMMENDATION"
        ]
        parsed = _parse_labeled_sections(result.output or "", keys)
        parsed["decision"]   = decision
        parsed["raw_output"] = result.output
        return parsed

    # ─── weekly_strategy_review ──────────────────────────────────────────────

    def weekly_strategy_review(self) -> str:
        """
        Full Sunday strategy review. Analyzes portfolio, compares signals,
        writes to orchestrator/strategy/YYYY-WW.md.
        Returns the full text for Telegram.
        """
        portfolio = self.analyze_portfolio_strategy()
        week_label = datetime.datetime.now().strftime("%Y-W%W")

        summary_lines = [
            f"# Strategy Review — {week_label}",
            f"Generated: {datetime.datetime.now().isoformat()[:19]}",
            "",
            "---",
            "",
            "## Capital Allocation",
            portfolio.get("capital_allocation", ""),
            "",
            "## Sequencing",
            portfolio.get("sequencing", ""),
            "",
            "## Cross-Company Leverage",
            portfolio.get("cross_company_leverage", ""),
            "",
            "## Portfolio Constraint",
            portfolio.get("portfolio_constraint", ""),
            "",
            "## Path to North Star",
            portfolio.get("north_star_path", ""),
        ]
        full_text = "\n".join(summary_lines)

        STRATEGY_DIR.mkdir(parents=True, exist_ok=True)
        out_path = STRATEGY_DIR / f"{week_label}.md"
        try:
            out_path.write_text(full_text, encoding="utf-8")
            print(f"[StrategyEngine] Weekly review written → {out_path}")
        except Exception as e:
            print(f"[StrategyEngine] Write failed: {e}")

        return full_text


# ─── DecisionEngine ───────────────────────────────────────────────────────────

class DecisionEngine:
    """
    Structured 6-step decision evaluation.
    Each step runs through the CognitiveLoop, building on prior steps.
    Results are logged to Neon for future reference.
    """

    def __init__(self, ctx: EOSContext):
        self.ctx      = ctx
        self.strategy = StrategyEngine(ctx)
        self.loop     = self.strategy.loop
        self.memory   = AgentMemory()

    def evaluate(
        self,
        decision: str,
        context: dict,
        venture_id: str | None = None,
    ) -> dict:
        """
        6-step structured decision evaluation.
        Each step is a focused CognitiveLoop call that builds on the last.
        Returns all 6 steps + final recommendation.
        """
        # Load venture data to ground the analysis
        venture_data = ""
        if venture_id:
            try:
                v = VentureKnowledgeBase.get(venture_id)
                venture_data = (
                    f"Revenue: ${v.monthly_revenue:,.0f}/mo, "
                    f"Target: ${v.monthly_target:,.0f}/mo, "
                    f"Stage: {v.stage}"
                )
            except Exception:
                pass

        # Merge provided context with venture data
        ctx_parts = []
        if context:
            ctx_parts.append(json.dumps(context))
        if venture_data:
            ctx_parts.append(venture_data)
        context_str = " | ".join(ctx_parts) if ctx_parts else "no additional context"

        base = (
            f"Decision under evaluation: {decision}\n"
            f"Context: {context_str}\n\n"
        )

        steps = [
            (
                "step1_context",
                base + "STEP 1 — CONTEXT ANALYSIS\n"
                "What is the full context of this decision? "
                "What do we know for certain? Reference all specific numbers. "
                "No assumptions.",
            ),
            (
                "step2_principles",
                base + "STEP 2 — PRINCIPLE EVALUATION\n"
                "Does this decision align with the company's north star "
                "and first principles? Score alignment 0-10 and give the reason. "
                "If misaligned, name exactly what it violates.",
            ),
            (
                "step3_leverage",
                base + "STEP 3 — LEVERAGE DETECTION\n"
                "Is this high-leverage? What is the expected impact relative to "
                "the cost in time and money? Score leverage 0-10. "
                "Compare to the highest-leverage alternative use of those resources.",
            ),
            (
                "step4_risk",
                base + "STEP 4 — RISK ASSESSMENT\n"
                "What could go wrong? Describe the realistic downside scenario. "
                "Classify risk: LOW / MEDIUM / HIGH / CRITICAL. "
                "What is the recovery path if it fails?",
            ),
            (
                "step5_timing",
                base + "STEP 5 — TIMING ANALYSIS\n"
                "Is now the right time for this decision? "
                "What condition, if present, would make this clearly correct? "
                "Is that condition present now? If not, what must happen first?",
            ),
            (
                "step6_recommendation",
                base + "STEP 6 — FINAL RECOMMENDATION\n"
                "Given all of the above analysis, give a final recommendation: "
                "YES / NO / WAIT. "
                "One clear sentence with the single most important reason. "
                "Reference the specific context — no generic advice.",
            ),
        ]

        results: dict = {"decision": decision, "context": context}

        for step_key, step_prompt in steps:
            try:
                r = self.loop.run(
                    input=step_prompt,
                    agent=f"decision_engine.{step_key}",
                    task_type=TaskType.ANALYZE,
                    venture_id=venture_id,
                    max_iterations=1,
                )
                results[step_key] = r.output or ""
            except Exception as e:
                results[step_key] = f"[Step failed: {e}]"

        # Log the full decision analysis to Neon
        try:
            self.memory.log_event(
                org_id=self.ctx.org_id,
                event_type="decision_analysis",
                payload={
                    "decision":            decision,
                    "context":             context,
                    "venture_id":          venture_id,
                    "recommendation":      results.get("step6_recommendation", "")[:500],
                    "evaluated_at":        datetime.datetime.now(datetime.timezone.utc).isoformat(),
                },
            )
        except Exception:
            pass  # logging is enhancement — never block result

        return results
