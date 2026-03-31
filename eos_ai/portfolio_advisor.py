"""
Portfolio Advisor — board-level intelligence across all companies in the portfolio.

Reasons across Lyfe Institute, Empyrean Creative, and any future org under
the portfolio. Advises on capital allocation, cross-company patterns, and
north star trajectory. Does not execute. Thinks in quarters, not days.

Usage:
    from eos_ai.context import load_context_from_env
    from eos_ai.portfolio_advisor import PortfolioAdvisor

    ctx = load_context_from_env()
    pa  = PortfolioAdvisor(ctx)
    print(pa.morning_advisory())
"""

import os
from datetime import datetime, timedelta, timezone
from pathlib import Path

from eos_ai.context import EOSContext, load_context_from_env
from eos_ai.db import get_conn
from eos_ai.agent_runtime import AgentRuntime, TaskType


# ─── Org slug → human-readable name ──────────────────────────────────────────

_ORG_NAMES: dict[str, str] = {
    "lyfe_institute":   "Lyfe Institute",
    "empyrean_creative": "Empyrean Creative",
}


class PortfolioAdvisor:

    def __init__(self, ctx: EOSContext) -> None:
        self.ctx     = ctx
        self._runtime = AgentRuntime()
        self._portfolio_name: str = "Munoz Holdings Portfolio"
        self._north_star: str     = "$100K/month net profit across portfolio"
        self._orgs: list[dict]    = []   # [{id, name, slug, ventures: [...]}]
        self._load_portfolio()

    # ─── Init: load portfolio + orgs from DB ─────────────────────────────────

    def _load_portfolio(self) -> None:
        """Load portfolio metadata and all orgs that belong to it."""
        if not self.ctx.portfolio_id:
            print("[PortfolioAdvisor] No portfolio_id in context — using env fallback.")
            return

        try:
            # Use a direct connection without RLS scoping (portfolio is cross-org)
            import psycopg2
            import psycopg2.extras
            from dotenv import load_dotenv
            load_dotenv(Path(__file__).parent / ".env")
            conn = psycopg2.connect(os.environ["DATABASE_URL"])

            with conn:
                with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                    # Portfolio metadata
                    cur.execute(
                        "SELECT name, north_star FROM portfolios WHERE id = %s",
                        (self.ctx.portfolio_id,),
                    )
                    row = cur.fetchone()
                    if row:
                        self._portfolio_name = row["name"]
                        self._north_star     = row["north_star"] or self._north_star

                    # All orgs in this portfolio
                    cur.execute(
                        "SELECT id, name FROM organizations WHERE portfolio_id = %s",
                        (self.ctx.portfolio_id,),
                    )
                    org_rows = cur.fetchall()

                    for org in org_rows:
                        slug = org["name"].lower().replace(" ", "_")
                        # Load ventures for each org
                        cur.execute(
                            """
                            SELECT id, name, monthly_revenue, monthly_target
                            FROM ventures WHERE org_id = %s
                            """,
                            (str(org["id"]),),
                        )
                        ventures = [dict(v) for v in cur.fetchall()]
                        self._orgs.append({
                            "id":       str(org["id"]),
                            "name":     org["name"],
                            "slug":     slug,
                            "ventures": ventures,
                        })

            conn.close()
            print(
                f"[PortfolioAdvisor] Loaded portfolio '{self._portfolio_name}' "
                f"with {len(self._orgs)} companies."
            )
        except Exception as e:
            print(f"[PortfolioAdvisor] Portfolio load failed: {e}")

    # ─── Public: org list ────────────────────────────────────────────────────

    def get_all_orgs(self) -> list[dict]:
        """Return all orgs loaded into this portfolio [{id, name, slug, ventures}]."""
        return self._orgs

    # ─── Data: live status per company ───────────────────────────────────────

    def get_portfolio_status(self) -> dict:
        """
        For each org in the portfolio return:
          - interactions_7d: count of agent interactions last 7 days
          - reply_rate:       % of outcomes with positive outcome_type
          - ventures:         list of {name, monthly_revenue, monthly_target, progress_pct}

        Returns a dict keyed by company slug.
        """
        cutoff = (datetime.now(timezone.utc) - timedelta(days=7)).isoformat()
        status: dict = {}

        for org in self._orgs:
            org_id = org["id"]
            slug   = org["slug"]

            interactions_7d = 0
            reply_rate      = 0.0

            try:
                with get_conn(org_id) as cur:
                    # Interaction count last 7 days
                    cur.execute(
                        "SELECT COUNT(*) AS cnt FROM interactions WHERE org_id = %s AND created_at > %s",
                        (org_id, cutoff),
                    )
                    interactions_7d = cur.fetchone()["cnt"] or 0

                    # Reply rate: positive outcomes / total outcomes
                    cur.execute(
                        """
                        SELECT
                            COUNT(*) FILTER (WHERE outcome_type = 'positive') AS positives,
                            COUNT(*) AS total
                        FROM outcomes
                        WHERE org_id = %s
                        """,
                        (org_id,),
                    )
                    row = cur.fetchone()
                    if row and row["total"] > 0:
                        reply_rate = round(row["positives"] / row["total"] * 100, 1)
            except Exception as e:
                print(f"[PortfolioAdvisor] Stats query failed for {slug}: {e}")

            venture_data = []
            for v in org["ventures"]:
                target   = float(v["monthly_target"] or 0)
                revenue  = float(v["monthly_revenue"] or 0)
                progress = round(revenue / target * 100, 1) if target > 0 else 0.0
                venture_data.append({
                    "name":            v["name"],
                    "monthly_revenue": revenue,
                    "monthly_target":  target,
                    "progress_pct":    progress,
                })

            status[slug] = {
                "name":             org["name"],
                "interactions_7d":  interactions_7d,
                "reply_rate":       reply_rate,
                "ventures":         venture_data,
            }

        return status

    # ─── Advisory: morning brief ─────────────────────────────────────────────

    def morning_advisory(self) -> str:
        """
        Board-level morning advisory across all portfolio companies.
        Grounded in StrategyEngine position analysis, then layered with
        board-level framing and resource allocation recommendation.
        """
        status = self.get_portfolio_status()
        status_block = self._format_status_block(status)

        # Ground the advisory in real strategy analysis
        strategy_context = ""
        try:
            from eos_ai.strategy_engine import StrategyEngine
            se       = StrategyEngine(self.ctx)
            position = se.analyze_company_position(self.ctx.org_id)
            strategy_context = (
                f"\nSTRATEGY ANALYSIS (from StrategyEngine):\n"
                f"  Binding constraint: {position.get('binding_constraint', '')[:200]}\n"
                f"  90-day priority:    {position.get('90_day_priority', '')[:200]}\n"
                f"  What to stop:       {position.get('what_to_stop', '')[:150]}\n"
            )
        except Exception as e:
            print(f"[PortfolioAdvisor] Strategy context failed: {e}")

        prompt = f"""You are the board-level advisor for {self._portfolio_name}.

NORTH STAR: {self._north_star}

PORTFOLIO STATUS (live data from the last 7 days):
{status_block}{strategy_context}

Produce a board-level morning advisory. Think in quarters, not days.
You see across all companies simultaneously. You reason about capital
allocation, cross-company patterns, and trajectory. You do not execute.
You advise only.

Structure your response EXACTLY as follows:

PORTFOLIO HEALTH SCORE: [0-100] / 100
[2-sentence rationale]

CROSS-COMPANY PATTERN:
[One pattern visible across companies that the operator may not see
from inside any single company]

RESOURCE CONCENTRATION:
[Which company deserves the most resources right now, and why —
be specific about what type of resource: time, money, attention]

NORTH STAR TRAJECTORY:
[At current rate, when does the portfolio hit {self._north_star}?
Show your reasoning. Be honest about the gap.]

ONE THING TO STOP:
[Single thing being done across the portfolio that is costing more
than it's returning — cut it cleanly]

MOST IMPORTANT STRATEGIC DECISION THIS WEEK:
[Single decision. Not a task list. One decision that, if made correctly,
compounds everything else.]"""

        result = self._runtime.run(
            task_type=TaskType.ANALYZE,
            prompt=prompt,
            max_tokens=1200,
            agent="portfolio_advisor",
            ctx=self.ctx,
        )
        return result.output

    # ─── Advisory: cross-company intelligence ────────────────────────────────

    def cross_company_intelligence(self, topic: str) -> str:
        """
        Load all company contexts simultaneously and produce a board-level
        strategic answer to the given topic or question.
        """
        status = self.get_portfolio_status()
        status_block = self._format_status_block(status)

        prompt = f"""You are the board-level advisor for {self._portfolio_name}.

NORTH STAR: {self._north_star}

PORTFOLIO STATUS:
{status_block}

QUESTION FROM THE OPERATOR:
{topic}

Answer at the board level. See across all companies. Reason about
cross-company leverage, resource allocation, and strategic sequencing.
Be direct. No hedging. No lists unless the answer is genuinely a list."""

        result = self._runtime.run(
            task_type=TaskType.ANALYZE,
            prompt=prompt,
            max_tokens=800,
            agent="portfolio_advisor",
            ctx=self.ctx,
        )
        return result.output

    # ─── Advisory: weekly review ─────────────────────────────────────────────

    def run_weekly_review(self) -> str:
        """
        Deeper version of morning_advisory with week-over-week delta,
        compounding vs decaying signals, cross-company leverage opportunities,
        and updated north star trajectory.

        Writes output to /opt/OS/15_Orchestrator/portfolio/YYYY-WW.md
        and returns the full text.
        """
        status       = self.get_portfolio_status()
        status_block = self._format_status_block(status)
        week_label   = datetime.now().strftime("%Y-W%W")

        prompt = f"""You are the board-level advisor for {self._portfolio_name}.
Weekly review — go deeper than the morning advisory.

NORTH STAR: {self._north_star}

PORTFOLIO STATUS (current):
{status_block}

Produce a full weekly board review structured EXACTLY as follows:

PORTFOLIO HEALTH SCORE: [0-100] / 100
[3-sentence rationale]

WHAT CHANGED THIS WEEK:
[What moved — revenue, momentum, activity levels, focus areas.
Be specific about direction: what improved, what degraded.]

WHAT IS COMPOUNDING:
[What is getting stronger with each passing week? Where is the flywheel
starting to turn, even slowly?]

WHAT IS DECAYING:
[What is losing momentum, relevance, or energy? Call it clearly.]

CROSS-COMPANY LEVERAGE OPPORTUNITIES:
[Where can a win in Company A directly accelerate Company B?
Concrete, specific, actionable leverage points.]

NORTH STAR TRAJECTORY:
[Updated projection. At current trajectory, when does the portfolio
reach {self._north_star}? What single variable, if doubled, would
cut that timeline in half?]

CAPITAL ALLOCATION RECOMMENDATION:
[If you had 40 hours of operator time and $1,000 to allocate across
the portfolio this week — exactly where does it go and why?]

ONE THING TO STOP:
[One thing being done that is costing more than it returns. Not a
suggestion — a directive.]

MOST IMPORTANT STRATEGIC DECISION THIS MONTH:
[Single decision. Not a task. One decision that determines the
trajectory of the next 90 days.]"""

        result = self._runtime.run(
            task_type=TaskType.ANALYZE,
            prompt=prompt,
            max_tokens=1800,
            agent="portfolio_advisor.weekly",
            ctx=self.ctx,
        )
        output = result.output

        # Append DRIP scan and Drive health to weekly output
        _extra: list[str] = []
        try:
            from eos_ai.drip_matrix import run_drip_audit
            import json as _json
            from eos_ai.db import get_conn as _get_conn
            with _get_conn(self.ctx.org_id) as _cur:
                _cur.execute(
                    """SELECT payload_json FROM events
                       WHERE org_id = %s AND event_type = 'dex_task'
                       AND (payload_json->>'status' IS NULL
                            OR payload_json->>'status' = 'pending')
                       AND created_at >= NOW() - INTERVAL '7 days'
                       ORDER BY created_at DESC LIMIT 10""",
                    (str(self.ctx.org_id),),
                )
                _task_rows = _cur.fetchall()
            _tasks = []
            for _r in _task_rows:
                _p = _r['payload_json']
                if isinstance(_p, str):
                    _p = _json.loads(_p)
                _t = _p.get('task', '')
                if _t:
                    _tasks.append(_t)
            if _tasks:
                _drip = run_drip_audit(_tasks, self.ctx)
                _delegate_count = len(_drip.get('delegate', []))
                _produce_count = len(_drip.get('produce', []))
                _drip_lines = [
                    "**🔍 DRIP Scan — this week's tasks:**",
                    f'• ⚡ Produce (genius zone): {_produce_count}',
                    f'• 🤖 Delegate to DEX: {_delegate_count}',
                ]
                if _delegate_count > 0:
                    _drip_lines.append(
                        f'• {_delegate_count} tasks should not be on your plate'
                    )
                _extra.append('\n'.join(_drip_lines))
        except Exception:
            pass

        try:
            from eos_ai.gws_connector import GWSConnector
            _gws = GWSConnector()
            _issues = _gws.audit_drive()
            _root_count = len(_issues.get('root_files', []))
            _untitled_count = len(_issues.get('untitled', []))
            if _root_count > 0 or _untitled_count > 0:
                _drive_lines = ['**📁 Drive needs attention:**']
                if _root_count:
                    _drive_lines.append(f'• {_root_count} files in root (unfiled)')
                if _untitled_count:
                    _drive_lines.append(f'• {_untitled_count} untitled documents')
                _drive_lines.append('Use `!driveaudit` to review.')
                _extra.append('\n'.join(_drive_lines))
        except Exception:
            pass

        if _extra:
            output = output + '\n\n---\n\n' + '\n\n'.join(_extra)

        # Write to file
        out_path = Path(__file__).parent.parent / "15_Orchestrator" / "portfolio" / f"{week_label}.md"
        try:
            out_path.write_text(
                f"# Portfolio Weekly Review — {week_label}\n\n"
                f"Generated: {datetime.now().isoformat()[:19]}\n\n"
                f"---\n\n{output}\n",
                encoding="utf-8",
            )
            print(f"[PortfolioAdvisor] Weekly review written to {out_path}")
        except Exception as e:
            print(f"[PortfolioAdvisor] Failed to write weekly review: {e}")

        return output

    # ─── Internal: format status block ───────────────────────────────────────

    def _format_status_block(self, status: dict) -> str:
        lines = []
        for slug, data in status.items():
            lines.append(f"--- {data['name'].upper()} ---")
            lines.append(f"Agent interactions (7d): {data['interactions_7d']}")
            lines.append(f"Reply / outcome rate:    {data['reply_rate']}%")
            for v in data["ventures"]:
                rev    = v["monthly_revenue"]
                target = v["monthly_target"]
                pct    = v["progress_pct"]
                lines.append(
                    f"Venture: {v['name']}  |  "
                    f"Revenue: ${rev:,.0f}/mo  |  "
                    f"Target: ${target:,.0f}/mo  |  "
                    f"Progress: {pct}%"
                )
            lines.append("")
        return "\n".join(lines)
