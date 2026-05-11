"""
EOSOrchestrator — strategic intelligence layer.

Reads venture KPIs, queries 7-day memory stats, identifies the binding
constraint, and dispatches the morning brief via Telegram.

Usage (manual):
    python3 eos_ai/orchestrator.py

Cron (6am daily):
    0 6 * * * cd /opt/OS && python3 eos_ai/orchestrator.py >> logs/orchestrator.log 2>&1
"""

import json
import os
import sys
import datetime
from pathlib import Path

import requests
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))
load_dotenv(os.path.join(os.path.dirname(__file__), "..", "services", ".env"))

_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

from eos_ai.agent_runtime import AgentRuntime, TaskType
from eos_ai.context import EOSContext
from eos_ai.db import get_conn, resolve_venture
from eos_ai.memory import AgentMemory
from eos_ai.venture_knowledge import VentureKnowledgeBase

VAULT = Path(_REPO_ROOT)
DAILY_DIR = VAULT / "orchestrator" / "daily"
POSTMORTEM_DIR = VAULT / "orchestrator" / "postmortems"


# ─── Notifications ───────────────────────────────────────────────────────────


def _notify(text: str) -> None:
    """Send notification via channel router."""
    try:
        from eos_ai.channel import get_channel_router

        router = get_channel_router()
        router.notify(text)
    except Exception as e:
        print(f"[Orchestrator] Notify failed: {e}")


def _send_discord_webhook(
    env_var: str, content: str, title: str = "", username: str = "DEX"
) -> None:
    """Post to a Discord channel via incoming webhook URL stored in env."""
    from eos_ai.discord_utils import post_to_webhook

    webhook_url = os.getenv(env_var, "")
    if not webhook_url:
        return
    post_to_webhook(content, title=title, username=username, webhook_url=webhook_url)


# ─── CEO Agent ────────────────────────────────────────────────────────────────


class CEOAgent:
    """
    Operates one company under the Portfolio. Breaks high-level objectives
    into department tasks, delegates via CoordinationEngine, and produces
    a company health snapshot for the morning cycle.
    """

    _DEPARTMENTS = ("sales", "research", "content", "ops", "finance")

    def __init__(self, ctx: EOSContext, org_id: str) -> None:
        # Scope context to this specific org
        self.ctx = EOSContext(
            org_id=org_id,
            user_id=ctx.user_id,
            portfolio_id=ctx.portfolio_id,
            active_venture_id=ctx.active_venture_id,
        )

    # ─── delegate_objective ──────────────────────────────────────────────────

    def delegate_objective(self, objective: str, venture_id: str) -> dict:
        """
        Formally activate the correct department agents beneath the CEO.
        Returns delegation map with department_tasks, total_tasks, ai_tasks,
        human_tasks counts.
        """
        import json
        from eos_ai.coordination_engine import CoordinationEngine
        from eos_ai.gateway import get_gateway as _get_gw

        # Step 1: break objective into department-level sub-objectives via gateway
        _gw = _get_gw()
        _gw_result = _gw.handle(
            {
                "type": "agent_task",
                "prompt": (
                    "Break this company objective into department-level sub-objectives.\n\n"
                    f"OBJECTIVE: {objective}\n\n"
                    "Departments available: sales, research, content, ops, finance\n\n"
                    "For each relevant department, specify the sub-objective that department owns.\n"
                    "Return a JSON array:\n"
                    '[{"department": "sales", "sub_objective": "..."}]\n\n'
                    "Only include departments that have actual work to do. "
                    "Return ONLY the JSON array. No markdown."
                ),
                "sub_agent": "ceo_agent",
                "task_type": "ANALYZE",
                "venture_id": venture_id,
                "username": "system",
            }
        )

        class _DecompResult:
            output = _gw_result.get("output", "")

        decomp = _DecompResult()

        dept_tasks_raw: list[dict] = []
        if decomp.output:
            try:
                raw = decomp.output.strip()
                if raw.startswith("```"):
                    parts = raw.split("```")
                    raw = parts[1] if len(parts) > 1 else raw
                    if raw.startswith("json"):
                        raw = raw[4:]
                parsed = json.loads(raw.strip(), strict=False)
                dept_tasks_raw = parsed if isinstance(parsed, list) else []
            except Exception:
                dept_tasks_raw = []

        # Step 2: route each department sub-objective through CoordinationEngine
        coordination = CoordinationEngine(self.ctx)
        department_tasks: dict = {d: [] for d in self._DEPARTMENTS}
        total_tasks = 0
        ai_tasks = 0
        human_tasks = 0

        for entry in dept_tasks_raw:
            if not isinstance(entry, dict):
                continue
            dept = (entry.get("department") or "").strip().lower()
            sub_obj = (entry.get("sub_objective") or "").strip()
            if not sub_obj or dept not in department_tasks:
                continue

            delegation = coordination.ceo_delegate(sub_obj, venture_id)
            for t in delegation.get("tasks_created", []):
                department_tasks[dept].append(
                    {
                        "description": t["description"],
                        "priority": t["priority"],
                        "executor": t["executor"],
                    }
                )

            total_tasks += delegation.get("total", 0)
            ai_tasks += delegation.get("ai_tasks", 0)
            human_tasks += delegation.get("human_tasks", 0)

        return {
            "objective": objective,
            "department_tasks": {k: v for k, v in department_tasks.items() if v},
            "total_tasks": total_tasks,
            "ai_tasks": ai_tasks,
            "human_tasks": human_tasks,
        }

    # ─── get_company_status ──────────────────────────────────────────────────

    def get_company_status(self) -> dict:
        """
        Read live company health from Neon.
        Returns ventures revenue, pending tasks, pending approvals,
        7-day interaction count, and skill reply rate.
        """
        # Revenue vs target per venture
        ventures: list[dict] = []
        for vid in VentureKnowledgeBase.list_ventures():
            try:
                v = VentureKnowledgeBase.get(vid)
                gap = v.monthly_target - v.monthly_revenue
                pct = (
                    round(v.monthly_revenue / v.monthly_target * 100, 1)
                    if v.monthly_target > 0
                    else 0.0
                )
                ventures.append(
                    {
                        "venture_id": vid,
                        "revenue": v.monthly_revenue,
                        "target": v.monthly_target,
                        "gap": gap,
                        "percent_to_target": pct,
                    }
                )
            except Exception:
                pass

        # Pending tasks count
        pending_tasks = 0
        try:
            with get_conn(self.ctx.org_id) as cur:
                cur.execute(
                    "SELECT COUNT(*) AS cnt FROM tasks WHERE org_id = %s AND status = 'pending'",
                    (self.ctx.org_id,),
                )
                pending_tasks = cur.fetchone()["cnt"] or 0
        except Exception:
            pass

        # Pending approvals count
        pending_approvals = 0
        try:
            with get_conn(self.ctx.org_id) as cur:
                cur.execute(
                    "SELECT COUNT(*) AS cnt FROM approvals "
                    "WHERE org_id = %s AND status = 'pending'",
                    (self.ctx.org_id,),
                )
                pending_approvals = cur.fetchone()["cnt"] or 0
        except Exception:
            pass

        # Last 7 days interactions count
        cutoff = (
            datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(days=7)
        ).isoformat()
        interactions_7d = 0
        try:
            with get_conn(self.ctx.org_id) as cur:
                cur.execute(
                    "SELECT COUNT(*) AS cnt FROM interactions "
                    "WHERE org_id = %s AND created_at >= %s",
                    (self.ctx.org_id, cutoff),
                )
                interactions_7d = cur.fetchone()["cnt"] or 0
        except Exception:
            pass

        # Skill performance — reply rate
        reply_rate = None
        try:
            with get_conn(self.ctx.org_id) as cur:
                cur.execute(
                    """
                    SELECT
                        COUNT(*) FILTER (WHERE outcome_label = 'reply') AS replies,
                        COUNT(*) AS total
                    FROM outcomes WHERE org_id = %s
                    """,
                    (self.ctx.org_id,),
                )
                row = cur.fetchone()
                if row and row["total"] and row["total"] > 0:
                    reply_rate = round(row["replies"] / row["total"] * 100, 1)
        except Exception:
            pass

        return {
            "ventures": ventures,
            "pending_tasks": pending_tasks,
            "pending_approvals": pending_approvals,
            "interactions_7d": interactions_7d,
            "reply_rate": reply_rate,
        }

    # ─── run_company_morning_cycle ───────────────────────────────────────────

    def run_company_morning_cycle(self) -> dict:
        """
        Per-company morning snapshot used by run_full_morning_cycle.
        Returns structured health dict ready for Telegram formatting.
        """
        return self.get_company_status()


# ─── Morning cycle helpers ────────────────────────────────────────────────────


def _fmt_company_reports(reports: list[dict]) -> str:
    lines: list[str] = []
    for item in reports:
        name = item["company"]
        report = item["report"]
        ventures = report.get("ventures", [])
        rev_lines = []
        for v in ventures:
            rev_lines.append(
                f"  {v['venture_id']}: ${v['revenue']:,.0f}/"
                f"${v['target']:,.0f} ({v['percent_to_target']}%)"
            )
        rr_str = f"{report['reply_rate']}%" if report.get("reply_rate") is not None else "no data"
        lines.append(
            f"{name}\n"
            + ("\n".join(rev_lines) if rev_lines else "  No venture data")
            + f"\n  Tasks pending: {report.get('pending_tasks', 0)}"
            + f"  |  Interactions 7d: {report.get('interactions_7d', 0)}"
            + f"  |  Reply rate: {rr_str}"
        )
    return "\n\n".join(lines) if lines else "No companies loaded"


def _fmt_signals(signals: list[dict]) -> str:
    if not signals:
        return "None"
    lines = []
    for s in signals[:5]:  # cap at 5 for Telegram length
        lines.append(f"• [{s.get('signal_type', '?')}] {s.get('content', '')[:120]}")
    return "\n".join(lines)


def _fmt_pending(pending: list) -> str:
    if not pending:
        return "None"
    lines = []
    for p in pending[:5]:
        lines.append(
            f"• {p.get('action_type', 'unknown')} "
            f"by {p.get('agent', 'agent')} "
            f"[{str(p.get('id', ''))[:8]}]"
        )
    return "\n".join(lines)


def _fmt_patterns(patterns: list[dict]) -> str:
    if not patterns:
        return "None detected"
    lines = []
    for p in patterns[:2]:
        desc = p.get("description", "")[:120]
        tier = p.get("signal_tier", "")
        lines.append(f"• [{tier}] {desc}")
    return "\n".join(lines)


# ─── Full morning cycle ───────────────────────────────────────────────────────


def run_full_morning_cycle(ctx: EOSContext, return_content: bool = False):
    """
    Unified morning cycle producing one coherent Telegram message:
      1. Portfolio Advisor board view
      2. CEO report per company
      3. Strategy binding constraint
      4. Critical reality signals
      5. Pending approvals
      6. Knowledge graph patterns

    Replaces the old EOSOrchestrator.run_morning_cycle().
    Called by cron at 6am via __main__.
    """
    print("[Orchestrator] ── Full morning cycle start ──")

    # 0. Sync Claude skills to Neon on startup
    try:
        from eos_ai.claude_skill_registry import ClaudeSkillRegistryManager

        csrm = ClaudeSkillRegistryManager()
        csrm.sync_to_neon(ctx)
    except Exception as e:
        print(f"[Orchestrator] Skill sync failed: {e}")

    # 1. Portfolio Advisor board view
    board_view = ""
    pa = None
    try:
        from eos_ai.portfolio_advisor import PortfolioAdvisor

        pa = PortfolioAdvisor(ctx)
        board_view = pa.morning_advisory()
        print("[Orchestrator] Portfolio advisory done.")
    except Exception as e:
        board_view = f"Portfolio advisory failed: {e}"
        print(f"[Orchestrator] Portfolio advisory error: {e}")

    # 2. CEO report per company
    company_reports: list[dict] = []
    if pa is not None:
        for org in pa.get_all_orgs():
            try:
                ceo = CEOAgent(ctx, org["id"])
                report = ceo.run_company_morning_cycle()
                company_reports.append({"company": org["name"], "report": report})
                print(f"[Orchestrator] CEO report done: {org['name']}")
            except Exception as e:
                company_reports.append(
                    {
                        "company": org["name"],
                        "report": {
                            "error": str(e),
                            "ventures": [],
                            "pending_tasks": 0,
                            "pending_approvals": 0,
                            "interactions_7d": 0,
                            "reply_rate": None,
                        },
                    }
                )
                print(f"[Orchestrator] CEO report error ({org['name']}): {e}")

    # 2b. CEO Agent evolution check — stage transitions + org chart
    try:
        from eos_ai.ceo_agent import CEOAgent as _CEOEvolutionAgent

        _ceo_evo = _CEOEvolutionAgent(ctx)
        _evo_changes = _ceo_evo.check_and_evolve()
        if _evo_changes.get("message"):
            _send_discord_webhook(
                env_var="DISCORD_BRIEF_WEBHOOK",
                content=_evo_changes["message"],
                title="Stage Transition",
                username="DEX",
            )
        print(
            f"[Orchestrator] CEO evolution check done. "
            f"Transition: {bool(_evo_changes.get('stage_transition'))}"
        )
    except Exception as e:
        print(f"[Orchestrator] CEO evolution: {e}")

    # 2c. Portfolio Agent — venture health scan
    portfolio_brief = ""
    try:
        from eos_ai.portfolio_advisor import PortfolioAdvisor

        pa_agent = PortfolioAdvisor(ctx)
        _ventures = pa_agent.scan_all_ventures()
        portfolio_brief = pa_agent.generate_portfolio_brief(_ventures)
        print(f"[Orchestrator] Portfolio scan done: {len(_ventures)} ventures.")
    except Exception as e:
        portfolio_brief = f"Portfolio scan failed: {e}"
        print(f"[Orchestrator] Portfolio Agent: {e}")

    # 3. Strategy Engine binding constraint
    binding = ""
    try:
        from eos_ai.strategy_engine import StrategyEngine

        se = StrategyEngine(ctx)
        pulse = se.analyze_portfolio_strategy()
        binding = pulse.get("portfolio_constraint", "")
        print("[Orchestrator] Strategy pulse done.")
    except Exception as e:
        binding = f"Strategy analysis failed: {e}"
        print(f"[Orchestrator] Strategy error: {e}")

    # 4. Reality signals — overnight scan
    critical_signals: list[dict] = []
    try:
        from eos_ai.reality_engine import RealityIntelligenceEngine

        rie = RealityIntelligenceEngine(ctx)
        signals = rie.process_signal_queue()
        all_sigs = signals.get("all_signals", [])
        critical_signals = [s for s in all_sigs if s.get("tier") == "CRITICAL"]
        print(
            f"[Orchestrator] Reality engine done: {len(all_sigs)} signals, "
            f"{len(critical_signals)} critical."
        )
    except Exception as e:
        print(f"[Orchestrator] Reality engine error: {e}")

    # 5. Pending approvals across all companies
    pending: list = []
    try:
        from eos_ai.authority_engine import AuthorityEngine

        ae = AuthorityEngine(ctx)
        pending = ae.get_pending()
        print(f"[Orchestrator] Pending approvals: {len(pending)}")
    except Exception as e:
        print(f"[Orchestrator] Authority engine error: {e}")

    # 6. Knowledge graph patterns
    patterns: list[dict] = []
    try:
        from eos_ai.knowledge_graph import KnowledgeGraph

        kg = KnowledgeGraph(ctx)
        for vid in VentureKnowledgeBase.list_ventures():
            try:
                patterns.extend(kg.find_patterns(vid))
            except Exception:
                pass
        print(f"[Orchestrator] Patterns detected: {len(patterns)}")
    except Exception as e:
        print(f"[Orchestrator] Knowledge graph error: {e}")

    # 7. Google Workspace — calendar + tasks
    calendar_section = "📅 TODAY\nNo events scheduled"
    tasks_section = "✅ TASKS\nNo pending tasks"
    try:
        from eos_ai.gws_connector import GWSConnector

        gws = GWSConnector()

        today_events = gws.get_today_events()
        if today_events:
            calendar_section = "📅 TODAY\n"
            for e in today_events:
                start_str = (e["start"] or "")[:16]
                calendar_section += f"  {start_str} — {e['title']}\n"
                if e.get("meet_link"):
                    calendar_section += f"  🎥 {e['meet_link']}\n"
        print(f"[Orchestrator] Calendar: {len(today_events)} events today.")

        tasks = gws.get_tasks()
        if tasks:
            tasks_section = f"✅ TASKS ({len(tasks)})\n"
            for t in tasks[:5]:
                tasks_section += f"  • {t['title']}\n"
        print(f"[Orchestrator] Tasks: {len(tasks)} pending.")
    except Exception as e:
        print(f"[Orchestrator] GWS error: {e}")

    # ── Notion-first: write structured content, send URL to Discord ──
    brief_content = {
        "binding_constraint": binding[:500],
        "company_reports": _fmt_company_reports(company_reports),
        "portfolio_brief": portfolio_brief[:600],
        "calendar_today": calendar_section,
        "tasks_today": tasks_section,
        "critical_signals": _fmt_signals(critical_signals),
        "pending_approvals": _fmt_pending(pending),
        "patterns": _fmt_patterns(patterns[:2]),
    }

    # Write to Notion
    notion_url = ""
    try:
        from eos_ai.notion_publisher import get_publisher

        publisher = get_publisher(ctx)
        notion_url = publisher.publish_morning_brief(content=brief_content)
        if notion_url:
            print(f"[Orchestrator] Morning brief → Notion: {notion_url}")
    except Exception as e:
        print(f"[Orchestrator] Notion publish failed: {e}")

    # Build Telegram summary (always send — primary mobile channel)
    message = (
        f"☀️ MORNING BRIEF\n"
        f"{'━' * 18}\n"
        f"⚡ {binding[:200]}\n\n"
        f"📊 {_fmt_company_reports(company_reports)[:600]}\n\n"
        f"📅 {calendar_section}\n"
        f"🚨 Critical: {len(critical_signals)} | "
        f"✅ Approvals: {len(pending)}"
    )
    if notion_url:
        message += f"\n\n📋 Full brief → {notion_url}"

    if len(message) > 4000:
        message = message[:3990] + "\n...[truncated]"

    _notify(message)
    print("[Orchestrator] Morning brief summary sent to Telegram.")

    # Discord gets link, not full content
    if notion_url:
        _send_discord_webhook(
            env_var="DISCORD_BRIEF_WEBHOOK",
            content=f"☀️ **Morning Brief ready**\n{notion_url}",
            title="Morning Brief",
            username="DEX",
        )
    else:
        # Fallback: send summary if Notion failed
        _send_discord_webhook(
            env_var="DISCORD_BRIEF_WEBHOOK",
            content=message[:1800],
            title="☀️ MORNING BRIEF",
            username="DEX",
        )

    # 8b. Proactive intelligence — send unsolicited alerts if conditions are met
    try:
        proactive_alerts = check_proactive_triggers(ctx)
        for alert in proactive_alerts:
            _notify(alert)
        if proactive_alerts:
            print(f"[Orchestrator] Proactive alerts sent: {len(proactive_alerts)}")
    except Exception as e:
        print(f"[Orchestrator] Proactive trigger error: {e}")

    # 8c. World pulse — daily market intel; full GWS rescan on Saturdays only
    try:
        from eos_ai.world_pulse import WorldPulse

        wp = WorldPulse(ctx)
        if datetime.datetime.now().weekday() == 5:  # Saturday
            wp.run_pulse_scan()  # full: market intel + GWS doc rescan
        else:
            wp.run_market_intel_scan()  # market intel only
        print("[Orchestrator] Daily pulse complete")
    except Exception as e:
        print(f"[Orchestrator] World pulse: {e}")

    # Log orchestrator run to Neon
    try:
        AgentMemory().log_event(
            org_id=ctx.org_id,
            event_type="orchestrator_run",
            payload={
                "cycle": "morning",
                "companies": len(company_reports),
                "critical_signals": len(critical_signals),
                "pending_approvals": len(pending),
                "patterns": len(patterns),
                "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
            },
        )
    except Exception as e:
        print(f"[Orchestrator] Neon log failed: {e}")

    # 8. Notion dashboard update
    try:
        notion_data = {
            "telegram_message": message,
            "ventures": company_reports,
            "critical_signals": len(critical_signals),
            "pending_approvals": len(pending),
            "patterns": len(patterns),
        }
        write_to_notion_dashboard(ctx, notion_data)
        print("[Orchestrator] Notion dashboard updated.")
    except Exception as e:
        print(f"[Orchestrator] Notion update failed: {e}")

    print("[Orchestrator] ── Full morning cycle complete ──")

    if return_content:
        return {
            "brief_content": brief_content,
            "notion_url": notion_url,
            "message": message,
        }


def run_ceo_morning_delegation(
    ctx: EOSContext,
    ventures: list = None,
) -> None:
    """
    CEO agent morning delegation cycle.
    For each venture, identifies today's key objective
    and delegates to specialist agents via CoordinationEngine.
    Runs after the morning brief.
    """
    import json as _json
    from zoneinfo import ZoneInfo as _ZI

    _PDT = _ZI("America/Los_Angeles")

    from eos_ai.ceo_agent import CEOAgent as _EvoCEO
    from eos_ai.coordination_engine import CoordinationEngine as _CE
    from eos_ai.portfolio_advisor import PortfolioAdvisor as _PA

    # Get binding constraint from portfolio
    binding_constraint = "Grow revenue"
    binding_venture = None
    try:
        pa = _PA(ctx)
        all_ventures = pa.scan_all_ventures()
        binding = pa.identify_binding_constraint(all_ventures)
        if binding:
            binding_constraint = binding.binding_constraint
            binding_venture = binding.venture_id
    except Exception as e:
        print(f"[CEOMorning] Portfolio scan failed: {e}")

    # Get ventures — from arg, then ctx.ventures, then BIM default (substrate-neutral)
    venture_list = ventures or getattr(ctx, "ventures", [])
    if not venture_list:
        try:
            from eos_ai.business_instance import BusinessInstanceManager

            _default_vid = BusinessInstanceManager(ctx).get_default_venture_id()
            if _default_vid:
                venture_list = [{"id": _default_vid, "name": _default_vid}]
        except Exception as _e:
            print(f"[CEOMorning] BIM default venture lookup failed: {_e}")
            venture_list = []

    results = []

    for venture_config in venture_list[:3]:
        venture_id = venture_config.get("id", "")
        venture_name = venture_config.get("name", venture_id)

        try:
            # Scope context to this venture
            from eos_ai.context import EOSContext as _EC

            venture_ctx = _EC(
                org_id=ctx.org_id,
                user_id=ctx.user_id,
                portfolio_id=getattr(ctx, "portfolio_id", ctx.org_id),
                active_venture_id=venture_id,
            )

            # Check evolution
            evo_ceo = _EvoCEO(venture_ctx)
            changes = evo_ceo.check_and_evolve()
            if changes.get("stage_transition"):
                results.append(f"🚀 **{venture_name}:** {changes['message']}")

            # Determine today's objective for this venture
            from eos_ai.gateway import get_gateway as _get_gw

            primitives = evo_ceo.detect_primitives()
            stage = primitives.get("stage", 1)
            north_star = venture_config.get("north_star", "")
            constraint = venture_config.get(
                "binding_constraint",
                binding_constraint if venture_id == binding_venture else "",
            )

            # Diagnose active constraint from live data
            constraint_data = {}
            active_agents = None
            offer_data = {}
            constraint_context = ""
            try:
                from eos_ai.ceo_intelligence import (
                    diagnose_constraint as _dc,
                    get_offer_stage as _gos,
                )

                constraint_data = _dc(venture_id, venture_ctx)
                offer_data = _gos(venture_id, venture_ctx)
                active_agents = constraint_data.get("active_agents", [])
                constraint_context = (
                    f"ACTIVE CONSTRAINT: "
                    f"{constraint_data['constraint'].upper()}"
                    f"\nDiagnosis: "
                    f"{constraint_data['diagnosis']}"
                    f"\nRecommendation: "
                    f"{constraint_data['recommendation']}"
                    f"\nOffer stage: "
                    f"{offer_data['stage']} — "
                    f"{offer_data['label']}"
                    f"\nOffer objective: "
                    f"{offer_data['objective']}"
                )
                print(
                    f"[CEOMorning] Constraint: "
                    f"{constraint_data['constraint']} "
                    f"| Active agents: {active_agents}"
                )
            except Exception as _ce:
                print(f"[CEOMorning] Intel: {_ce}")

            today = datetime.datetime.now(_PDT).strftime("%A %B %d")
            _gw = _get_gw()
            _gw_result = _gw.handle(
                {
                    "type": "agent_task",
                    "prompt": (
                        f"You are the CEO of {venture_name}.\n\n"
                        f"Stage: {stage}\n"
                        f"North star: {north_star}\n"
                        f"Binding constraint: {constraint}\n"
                        + (f"{constraint_context}\n\n" if constraint_context else "\n")
                        + f"Today is {today}.\n\n"
                        f"What is the single most important objective "
                        f"for your specialist agents to work on today "
                        f"to move the needle on the binding constraint?\n\n"
                        f"State it in one clear sentence."
                    ),
                    "sub_agent": "ceo_agent",
                    "task_type": "FAST_RESPONSE",
                    "venture_id": venture_id,
                    "username": "system",
                }
            )

            class _ObjResult:
                output = _gw_result.get("output", "")

            objective_result = _ObjResult()

            today_objective = (objective_result.output or f"Advance {binding_constraint}").strip()

            # Delegate to specialist agents
            coordination = _CE(venture_ctx)
            delegation = coordination.ceo_delegate(
                company_objective=today_objective,
                venture_id=venture_id,
            )

            # Filter to constraint-active agents only
            if active_agents:
                all_tasks = delegation.get("tasks_created", [])
                filtered = [
                    t
                    for t in all_tasks
                    if (
                        t.get("executor") in active_agents
                        or t.get("executor") == "human"
                        or t.get("executor", "").startswith("operations")
                    )
                ]
                if len(filtered) < len(all_tasks):
                    skipped = len(all_tasks) - len(filtered)
                    print(
                        f"[CEOMorning] Constraint filter: "
                        f"{len(all_tasks)} → {len(filtered)} "
                        f"tasks ({skipped} idle agents skipped)"
                    )

            total = delegation.get("total", 0)
            ai_tasks = delegation.get("ai_tasks", 0)
            human_tasks = delegation.get("human_tasks", 0)

            results.append(
                f"🏢 **{venture_name}**\n"
                f"Objective: _{today_objective}_\n"
                f"{total} tasks delegated ({ai_tasks} AI, {human_tasks} founder)"
            )

        except Exception as e:
            print(f"[CEOMorning] {venture_id} failed: {e}")
            results.append(f"⚠️ {venture_name}: delegation failed — {e}")

    # Write delegation report to Notion, send link to Discord
    if results:
        notion_url = ""
        try:
            from eos_ai.notion_publisher import get_publisher

            publisher = get_publisher(ctx)
            notion_url = publisher.publish_ceo_delegation(content={"results": results})
            if notion_url:
                print(f"[CEOMorning] Delegation → Notion: {notion_url}")
        except Exception as e:
            print(f"[CEOMorning] Notion publish failed: {e}")

        try:
            if notion_url:
                _send_discord_webhook(
                    env_var="DISCORD_BRIEF_WEBHOOK",
                    content=f"🏢 **CEO Delegation ready**\n{notion_url}",
                    title="CEO Delegation",
                    username="DEX",
                )
            else:
                # Fallback: send summary if Notion failed
                msg = (
                    "## 🏢 CEO Agent Morning Delegation\n\n"
                    + "\n\n".join(results)
                    + "\n\nSpecialist agents executing. "
                    "Results surface as tasks complete."
                )
                _send_discord_webhook(
                    env_var="DISCORD_BRIEF_WEBHOOK",
                    content=msg[:1900],
                    title="CEO Delegation",
                    username="DEX",
                )
        except Exception as e:
            print(f"[CEOMorning] Discord alert failed: {e}")


# ─── Proactive Intelligence ───────────────────────────────────────────────────


def check_proactive_triggers(ctx: EOSContext) -> list[str]:
    """
    Runs after morning cycle. Checks conditions that warrant unsolicited
    Telegram alerts. Returns list of alert messages (empty = nothing to surface).
    """
    alerts: list[str] = []

    try:
        with get_conn(ctx.org_id) as cur:
            # 1. Stale leads: leads with no contact in > 7 days
            cur.execute(
                """
                SELECT COUNT(*) AS cnt FROM human_profiles
                WHERE org_id = %s
                  AND updated_at < NOW() - INTERVAL '7 days'
                  AND profile_json::text NOT ILIKE '%%closed%%'
                """,
                (ctx.org_id,),
            )
            stale = cur.fetchone()["cnt"] or 0
            if stale > 0:
                alerts.append(
                    f"⚠️ {stale} lead{'s' if stale > 1 else ''} with no contact "
                    f"in 7+ days. Use /leads to review."
                )

            # 2. Pending approvals > 24h old
            cur.execute(
                """
                SELECT COUNT(*) AS cnt FROM approvals
                WHERE org_id = %s
                  AND status = 'pending'
                  AND created_at < NOW() - INTERVAL '24 hours'
                """,
                (ctx.org_id,),
            )
            old_approvals = cur.fetchone()["cnt"] or 0
            if old_approvals > 0:
                alerts.append(
                    f"⏳ {old_approvals} approval{'s' if old_approvals > 1 else ''} "
                    f"waiting > 24h. Use /pending to review."
                )

            # 3. Outcome milestone: 10th, 25th, 50th, 100th outcome logged
            cur.execute(
                "SELECT COUNT(*) AS cnt FROM outcomes WHERE org_id = %s",
                (ctx.org_id,),
            )
            outcome_count = cur.fetchone()["cnt"] or 0
            if outcome_count in (10, 25, 50, 100):
                alerts.append(
                    f"🎯 {outcome_count} outcomes logged. "
                    f"Skill improvement cycle will run Saturday. RLHF signal growing."
                )

            # 4. Revenue milestone — estimated from closed outcomes
            cur.execute(
                """
                SELECT COALESCE(SUM(score * 750), 0) AS est
                FROM outcomes
                WHERE org_id = %s
                  AND outcome_type = 'positive'
                  AND notes ILIKE '%%closed%%'
                """,
                (ctx.org_id,),
            )
            est_revenue = float(cur.fetchone()["est"] or 0)
            if est_revenue > 0 and est_revenue % 750 == 0:
                alerts.append(f"💰 Estimated revenue milestone: ${est_revenue:,.0f}. Keep going.")

    except Exception as e:
        print(f"[Orchestrator] Proactive trigger check failed: {e}")

    return alerts


def check_outcome_milestone(ctx: EOSContext, new_outcome_count: int) -> None:
    """
    Event-driven milestone check called immediately when a new outcome is logged.
    Sends Telegram alert without waiting for 6am cycle.
    """
    if new_outcome_count in (10, 25, 50, 100):
        _notify(
            f"🎯 {new_outcome_count} outcomes logged. "
            f"Skill improvement cycle will run Saturday. RLHF signal growing."
        )


# ─── Data-first Morning Brief (DEPRECATED) ──────────────────────────────────
# DEPRECATED: Use run_full_morning_cycle() instead.
# This was a partial reimplementation. The canonical system is
# run_full_morning_cycle() which writes to Notion via NotionPublisher
# and sends the URL to Discord. Kept for backward compatibility with
# discord_bot.py callers — will be removed in next cleanup pass.


async def generate_morning_brief(ctx: EOSContext) -> str:
    """
    DEPRECATED: Use run_full_morning_cycle() instead.

    Data-first morning brief. Pulls real venture data, primitives, and reality
    signals first, then asks AI to add one insight on top.

    Works with Qwen (limited context) because the AI call is scoped to 100 tokens.
    Can be called from discord_bot.py or tested directly.
    """
    import asyncio
    from datetime import datetime as _dt

    now = _dt.now()
    date_str = now.strftime("%A, %B %d")

    # Substrate-neutral venture list — pulled from ctx/BIM, not hardcoded.
    # Falls back to ctx.ventures, then BIM default, then an empty list.
    companies: list[tuple[str, str, str]] = []
    try:
        _ctx_ventures = getattr(ctx, "ventures", []) if "ctx" in dir() else []
    except Exception:
        _ctx_ventures = []
    if not _ctx_ventures:
        try:
            from eos_ai.context import load_context_from_env as _lctx
            from eos_ai.business_instance import BusinessInstanceManager as _BIM

            _c = _lctx()
            _ctx_ventures = getattr(_c, "ventures", []) or []
            if not _ctx_ventures:
                _vid = _BIM(_c).get_default_venture_id()
                if _vid:
                    _ctx_ventures = [{"id": _vid, "name": _vid}]
        except Exception as _e:
            print(f"[Portfolio] venture resolution failed: {_e}")
            _ctx_ventures = []
    for _v in _ctx_ventures:
        companies.append(
            (
                _v.get("id", ""),
                _v.get("name", _v.get("id", "")),
                _v.get("icon", "🏢"),
            )
        )

    company_sections: list[str] = []

    for venture_id, name, icon in companies:
        try:
            from eos_ai.business_instance import BusinessInstanceManager
            from eos_ai.evolution_engine import EvolutionEngine
            from eos_ai.primitives import PRIMITIVE_LIBRARY

            bim = BusinessInstanceManager(ctx)
            ee = EvolutionEngine(ctx)
            bis = bim.get_bis(venture_id)
            stage = ee.get_current_stage(venture_id)

            active = [
                pid
                for pid, p in PRIMITIVE_LIBRARY.items()
                if p.stage_applicability.get(stage, True)
            ]

            section = (
                f"{icon} **{name}**\n"
                f"Stage: {stage} — Validation\n"
                f"Offer: {getattr(bis, 'offer_name', '—')}\n"
                f"Channel: {getattr(bis, 'primary_channel', '—')}\n"
                f"Revenue: ${getattr(bis, 'revenue_total', 0)}\n"
                f"Active primitives: {', '.join(active[:3])}\n"
                f"Focus: First sale as fast as possible"
            )
            company_sections.append(section)
        except Exception:
            company_sections.append(f"{icon} **{name}**: data unavailable")

    # Pull reality signals
    reality_section = ""
    try:
        from eos_ai.reality_context import RealityContextEngine

        rce = RealityContextEngine(ctx)
        reality = rce.get_ambient_state()
        if reality:
            reality_section = f"\n📡 **Reality Signals**\n{str(reality)[:300]}"
    except Exception:
        pass

    # Build data-first brief
    # Try Daily Sync first — Dan Martell's 7-section format
    try:
        from eos_ai.daily_sync import DailySyncEngine

        dse = DailySyncEngine(ctx)
        brief = dse.run_sync()
        print("[Brief] Daily sync generated.")
        return brief
    except Exception as e:
        print(f"[Brief] Daily sync failed, falling back: {e}")

    # Fallback: original data-first brief
    brief = f"━━━━━━━━━━━━━━━━━━━━━━\n☀️ **MORNING BRIEF**\n{date_str}\n━━━━━━━━━━━━━━━━━━━━━━\n\n"

    for section in company_sections:
        brief += section + "\n\n"

    brief += (
        f"━━━━━━━━━━━━━━━━━━━━━━\n"
        f"🎯 **TODAY'S FOCUS**\n"
        f"Stage 1 across all companies.\n"
        f"One job: get the first sale.\n"
        f"Outreach before everything.\n\n"
        f"Active: conversation_first, outreach_before_content\n"
        f"Locked: content_strategy, paid_advertising\n"
    )

    if reality_section:
        brief += reality_section

    # Add today's calendar
    calendar_section = ""
    try:
        from eos_ai.gws_connector import GWSConnector

        gws = GWSConnector()
        events = gws.get_today_events()
        if events:
            event_lines = []
            for event in events[:5]:
                title = event.get("title", "")
                start = event.get("start", "")
                if start and "T" in str(start):
                    start = str(start).split("T")[1][:5]
                event_lines.append(f"  {start} — {title}")
            calendar_section = "\n📅 **Today's Calendar**\n" + "\n".join(event_lines)
        else:
            calendar_section = "\n📅 **Today's Calendar**\n  No events scheduled."
    except Exception as e:
        print(f"[Brief] Calendar: {e}")

    if calendar_section:
        brief += calendar_section

    # Add AI insight on top of data — route through gateway
    try:
        from eos_ai.gateway import get_gateway as _get_gw_brief

        _gw_brief = _get_gw_brief()
        _insight_result = _gw_brief.handle(
            {
                "type": "agent_task",
                "prompt": (
                    f"Based on this morning brief data:\n{brief[:500]}\n\n"
                    f"What is the single most important action for today? "
                    f"One sentence only."
                ),
                "sub_agent": "executive_assistant",
                "task_type": "FAST_RESPONSE",
                "username": "system",
            }
        )
        _insight_text = _insight_result.get("output", "")
        if _insight_text:
            brief += f"\n━━━━━━━━━━━━━━━━━━━━━━\n💡 **DEX says:**\n{_insight_text}"
    except Exception:
        brief += (
            f"\n━━━━━━━━━━━━━━━━━━━━━━\n"
            f"💡 **DEX says:**\n"
            f"Send 20 DMs today. That is the only metric that matters."
        )

    brief += f"\n\n— DEX"
    return brief


# ─── Notion Dashboard ─────────────────────────────────────────────────────────


def write_to_notion_dashboard(ctx: EOSContext, morning_data: dict) -> None:
    """
    DEPRECATED: Use NotionPublisher.publish_morning_brief() instead.
    This function is kept for backward compatibility only.
    The morning brief is now written to Notion by run_full_morning_cycle()
    via NotionPublisher before this function is called.
    """
    # The brief is already written to Notion by run_full_morning_cycle().
    # This is a no-op now — the Notion write happens earlier in the cycle.
    print("[Orchestrator] write_to_notion_dashboard: skipped (handled by NotionPublisher)")


# ─── Orchestrator ─────────────────────────────────────────────────────────────


class EOSOrchestrator:
    def __init__(self) -> None:
        self._runtime = AgentRuntime()
        self._memory = AgentMemory()

    # ─── Internal: 7-day stats ───────────────────────────────────────────────

    def _query_7d_stats(self, venture_id: str) -> dict:
        """
        Query Neon for interactions + outcomes in the last 7 days for a given
        venture. Returns a summary dict — no new AgentMemory methods required.
        """
        cutoff = (
            datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(days=7)
        ).isoformat()

        venture_uuid = resolve_venture(venture_id)

        with get_conn() as cur:
            cur.execute(
                """
                SELECT i.id, i.agent_label, s.name AS skill_used, i.tokens_json,
                       o.outcome_label, o.score
                FROM interactions i
                LEFT JOIN outcomes o ON o.interaction_id = i.id
                LEFT JOIN skills   s ON s.id = i.skill_id
                WHERE i.venture_id = %s AND i.created_at >= %s
                """,
                (venture_uuid, cutoff),
            )
            rows = cur.fetchall()

        seen_ids: set = set()
        total_tokens: int = 0
        skills_used: dict = {}
        replies: int = 0
        outcomes_total: int = 0

        for row in rows:
            iid = str(row["id"])
            if iid not in seen_ids:
                seen_ids.add(iid)
                tokens = row["tokens_json"] or {}
                if isinstance(tokens, str):
                    try:
                        tokens = json.loads(tokens)
                    except (json.JSONDecodeError, TypeError):
                        tokens = {}
                total_tokens += tokens.get("total", 0)
                skill = row["skill_used"]
                if skill:
                    skills_used[skill] = skills_used.get(skill, 0) + 1

            if row["outcome_label"]:
                outcomes_total += 1
            if row["outcome_label"] == "reply":
                replies += 1

        reply_rate = round(replies / outcomes_total, 3) if outcomes_total > 0 else None

        return {
            "venture_id": venture_id,
            "interactions_7d": len(seen_ids),
            "total_tokens_7d": total_tokens,
            "skills_invoked": skills_used,
            "replies": replies,
            "outcomes_total": outcomes_total,
            "reply_rate": reply_rate,
        }

    # ─── Public: north star status ───────────────────────────────────────────

    def get_north_star_status(self) -> list[dict]:
        """
        Return revenue vs target for every venture.
        """
        results = []
        for venture_id in VentureKnowledgeBase.list_ventures():
            v = VentureKnowledgeBase.get(venture_id)
            gap = v.monthly_target - v.monthly_revenue
            pct = (
                round(v.monthly_revenue / v.monthly_target * 100, 1)
                if v.monthly_target > 0
                else 0.0
            )
            results.append(
                {
                    "venture_id": venture_id,
                    "revenue": v.monthly_revenue,
                    "target": v.monthly_target,
                    "gap": gap,
                    "percent_to_target": pct,
                }
            )
        return results

    # ─── Public: morning brief (DEPRECATED) ────────────────────────────────
    # DEPRECATED: Use run_full_morning_cycle() instead.
    # The canonical brief system writes to Notion via NotionPublisher.
    # This class method is kept for backward compatibility only.

    def morning_brief(self) -> str:
        """
        DEPRECATED: Use run_full_morning_cycle() instead.

        Generate a structured AI brief, write it to orchestrator/daily/,
        and return the full text.
        """
        venture_ids = VentureKnowledgeBase.list_ventures()

        venture_blocks: list[str] = []
        for vid in venture_ids:
            ctx = VentureKnowledgeBase.to_agent_context(vid, detail="brief")
            stats = self._query_7d_stats(vid)
            skills_str = ", ".join(f"{k}×{v}" for k, v in stats["skills_invoked"].items()) or "none"
            rr = f"{stats['reply_rate']:.1%}" if stats["reply_rate"] is not None else "no data"
            stats_block = (
                f"7-Day Activity:\n"
                f"  Interactions : {stats['interactions_7d']}\n"
                f"  Tokens used  : {stats['total_tokens_7d']:,}\n"
                f"  Skills       : {skills_str}\n"
                f"  Reply rate   : {rr}\n"
            )
            venture_blocks.append(ctx + "\n" + stats_block)

        north_star = self.get_north_star_status()
        ns_block = "\n".join(
            f"  {s['venture_id']}: "
            f"${s['revenue']:,.0f} / ${s['target']:,.0f} "
            f"({s['percent_to_target']}% to target, ${s['gap']:,.0f} gap)"
            for s in north_star
        )

        # Behavioral patterns — inject into brief for pattern-aware recommendations
        pattern_context = ""
        try:
            from eos_ai.context import load_context_from_env as _lctx
            from eos_ai.pattern_engine import PatternEngine as _PE

            _ctx_pe = _lctx()
            _patterns = _PE(_ctx_pe).analyze(days_back=7)
            if _patterns:
                _lines = ["BEHAVIORAL PATTERNS (last 7 days):"]
                for _p in _patterns[:2]:
                    _lines.append(f"- {_p.pattern_type}: {_p.description[:120]}")
                pattern_context = "\n" + "\n".join(_lines) + "\n\n"
        except Exception:
            pass

        prompt = (
            "You are the strategic intelligence layer for a founder-operator "
            "running multiple ventures toward an 11-figure empire.\n\n"
            "VENTURE DATA:\n\n"
            + "\n\n---\n\n".join(venture_blocks)
            + f"\n\nNORTH STAR STATUS:\n{ns_block}\n\n"
            + pattern_context
            + "Generate a structured morning brief with EXACTLY these four sections. "
            "Be specific and ruthlessly practical — no platitudes.\n\n"
            "## Current Status\n"
            "One sentence per venture. Name the actual number and actual stage.\n\n"
            "## Binding Constraint\n"
            "The single constraint that, if removed, unlocks the most forward "
            "progress. Name the exact bottleneck — not a category, the specific "
            "thing.\n\n"
            "## Highest-Leverage Action Today\n"
            "The one executable action that moves the needle on the binding "
            "constraint. Concrete enough to start immediately.\n\n"
            "## One Thing To Stop\n"
            "One specific behavior, task, or pattern consuming resources without "
            "moving toward the north star. Name it precisely."
        )

        result = self._runtime.run(
            task_type=TaskType.ANALYZE,
            prompt=prompt,
            max_tokens=1200,
            agent="orchestrator",
        )
        brief_text = result.output

        # Persist brief to disk
        DAILY_DIR.mkdir(parents=True, exist_ok=True)
        today = datetime.date.today().isoformat()
        brief_path = DAILY_DIR / f"{today}.md"

        header = f"# Morning Brief — {today}\n\n**North Star Status**\n{ns_block}\n\n---\n\n"
        brief_path.write_text(header + brief_text, encoding="utf-8")
        print(f"[Orchestrator] Brief written → {brief_path}")

        return header + brief_text

    # ─── Public: postmortem engine ───────────────────────────────────────────

    def write_postmortem(
        self,
        failure_description: str,
        error_log: str,
        affected_component: str,
    ) -> str:
        """
        Generate an AI-written postmortem for a system failure.
        Writes to orchestrator/postmortems/YYYY-MM-DD_component.md.
        Logs to memory.db via AgentRuntime.
        Returns the postmortem file path.
        """
        POSTMORTEM_DIR.mkdir(parents=True, exist_ok=True)

        prompt = (
            "You are the intelligence layer for a founder-operator's AI system. "
            "A component has failed. Write a structured postmortem.\n\n"
            f"AFFECTED COMPONENT: {affected_component}\n\n"
            f"FAILURE DESCRIPTION:\n{failure_description}\n\n"
            f"ERROR LOG:\n{error_log[:2000]}\n\n"
            "Write the postmortem with EXACTLY these four sections:\n\n"
            "## Timeline\n"
            "Reconstruct what likely happened in chronological order based on "
            "the error log. Be specific about which call failed and why.\n\n"
            "## Root Cause\n"
            "Single most likely root cause. Not a category — the exact mechanism "
            "that caused the failure.\n\n"
            "## Fix\n"
            "Specific, immediately actionable fix. Code-level or config-level. "
            "Concrete enough to implement in under 30 minutes.\n\n"
            "## Prevention\n"
            "One systemic change that prevents this class of failure from "
            "recurring. Name exactly what to add, monitor, or gate."
        )

        result = self._runtime.run(
            task_type=TaskType.ANALYZE,
            prompt=prompt,
            max_tokens=1000,
            agent="orchestrator.postmortem",
        )

        today = datetime.date.today().isoformat()
        safe_component = affected_component.replace("/", "_").replace(".", "_")[:40]
        pm_path = POSTMORTEM_DIR / f"{today}_{safe_component}.md"

        header = (
            f"# Postmortem — {affected_component}\n"
            f"**Date:** {today}\n"
            f"**Component:** {affected_component}\n\n"
            f"---\n\n"
            f"**Failure:** {failure_description}\n\n"
            f"---\n\n"
        )
        pm_path.write_text(header + result.output, encoding="utf-8")
        print(f"[Orchestrator] Postmortem written → {pm_path}")

        return str(pm_path)

    # ─── Public: full morning cycle ──────────────────────────────────────────

    def run_morning_cycle(self) -> None:
        """
        Full cycle: north star check → morning brief → skill improvement →
        Telegram.  Called by cron at 6am.
        """
        print("[Orchestrator] ── Morning cycle start ──")

        north_star = self.get_north_star_status()
        ns_lines = "\n".join(
            f"  {s['venture_id']}: ${s['revenue']:,.0f} / ${s['target']:,.0f}" for s in north_star
        )
        print(f"[Orchestrator] North star:\n{ns_lines}")

        # Email GPS — 6am inbox processing pass (DEX handles email before Antony)
        try:
            from eos_ai.email_gps import EmailGPS
            from eos_ai.context import load_context_from_env as _lcfe

            _ctx = _lcfe()
            gps = EmailGPS(_ctx)
            gps_processed = gps.process_inbox(limit=50)
            gps_report = gps.generate_inbox_report(gps_processed)
            print(f"[Orchestrator] Email GPS morning pass:\n{gps_report}")
        except Exception as e:
            print(f"[Orchestrator] Email GPS morning pass error: {e}")

        brief = self.morning_brief()
        print("[Orchestrator] Brief generated.")

        # Skill improvement cycle
        improvement_summary = ""
        try:
            from eos_ai.skill_improvement import SkillImprovementEngine

            engine = SkillImprovementEngine()
            summary = engine.run_improvement_cycle()
            improved = [s for s in summary if s["action"] == "improved"]
            skipped = [s for s in summary if s["action"] != "improved"]
            improvement_summary = (
                f"\n\n---\nSkill Improvement: {len(improved)} improved, {len(skipped)} skipped"
            )
            if improved:
                names = ", ".join(s["skill_id"] for s in improved)
                improvement_summary += f"\nImproved: {names}"
        except Exception as e:
            improvement_summary = f"\n\nSkill improvement skipped: {e}"
            print(f"[Orchestrator] Skill improvement error: {e}")

        # Human intelligence profile cycle
        profile_summary = ""
        try:
            from eos_ai.human_intelligence import HumanIntelligenceEngine

            hi_engine = HumanIntelligenceEngine()
            hi_result = hi_engine.run_profile_cycle()
            profile_summary = (
                f"\nHuman Profiles: "
                f"{hi_result['built']} built, "
                f"{hi_result['skipped']} fresh, "
                f"{hi_result['errors']} errors"
            )
        except Exception as e:
            profile_summary = f"\nHuman profiles skipped: {e}"
            print(f"[Orchestrator] Human intelligence error: {e}")

        # Strategy review cycle — runs weekly on Sundays
        strategy_summary = ""
        if datetime.date.today().weekday() == 6:  # Sunday = 6
            try:
                from eos_ai.strategy_engine import StrategyEngine
                from eos_ai.context import load_context_from_env

                ctx = load_context_from_env()
                se = StrategyEngine(ctx)
                strategy_text = se.weekly_strategy_review()
                preview = strategy_text[:400].replace("\n", " ")
                strategy_summary = f"\n\n---\nWeekly Strategy Review written.\nPreview: {preview}"
            except Exception as e:
                strategy_summary = f"\n\nStrategy review skipped: {e}"
                print(f"[Orchestrator] Strategy review error: {e}")

        # Self-organization cycle — runs weekly on Mondays
        self_org_summary = ""
        if datetime.date.today().weekday() == 0:  # Monday = 0
            try:
                from eos_ai.skill_improvement import SkillImprovementEngine

                si_engine = SkillImprovementEngine()
                created = si_engine.run_self_organization_cycle()
                if created:
                    names = ", ".join(s["skill_id"] for s in created)
                    self_org_summary = (
                        f"\n\nSelf-Organization: {len(created)} new skill(s) proposed\n"
                        f"Created: {names}"
                    )
                else:
                    self_org_summary = "\n\nSelf-Organization: no new patterns detected"
            except Exception as e:
                self_org_summary = f"\n\nSelf-organization skipped: {e}"
                print(f"[Orchestrator] Self-organization error: {e}")

        # Reality intelligence signal scan — runs every morning (6am pass)
        reality_summary = ""
        try:
            from eos_ai.reality_engine import RealityIntelligenceEngine
            from eos_ai.context import load_context_from_env

            ctx = load_context_from_env()
            rie = RealityIntelligenceEngine(ctx)
            signal_summary = rie.process_signal_queue()
            total_signals = sum(
                sum(v.values()) if isinstance(v, dict) else 0 for v in signal_summary.values()
            )
            critical_count = sum(
                v.get("CRITICAL", 0) if isinstance(v, dict) else 0 for v in signal_summary.values()
            )
            high_count = sum(
                v.get("HIGH", 0) if isinstance(v, dict) else 0 for v in signal_summary.values()
            )
            reality_summary = (
                f"\n\nReality Engine: {total_signals} signals scanned"
                f" ({critical_count} critical, {high_count} high)"
            )
        except Exception as e:
            reality_summary = f"\n\nReality engine skipped: {e}"
            print(f"[Orchestrator] Reality engine error: {e}")

        # Research gap-fill cycle — runs weekly on Wednesdays
        research_summary = ""
        if datetime.date.today().weekday() == 2:  # Wednesday = 2
            try:
                from eos_ai.research_engine import ResearchEngine
                from eos_ai.context import load_context_from_env

                ctx = load_context_from_env()
                re_engine = ResearchEngine(ctx)
                gap_result = re_engine.run_gap_fill_cycle()
                research_summary = (
                    f"\n\nResearch Engine: {gap_result['gaps_found']} gaps found, "
                    f"{gap_result['gaps_filled']} researched, "
                    f"{gap_result['knowledge_objects_created']} stored"
                )
            except Exception as e:
                research_summary = f"\n\nResearch engine skipped: {e}"
                print(f"[Orchestrator] Research engine error: {e}")

        # Evolution cycle — runs weekly on Saturdays
        evolution_summary = ""
        if datetime.date.today().weekday() == 5:  # Saturday = 5
            try:
                from eos_ai.evolution_engine import EvolutionEngine
                from eos_ai.context import load_context_from_env

                ctx = load_context_from_env()
                ee = EvolutionEngine(ctx)
                evo_result = ee.run_weekly_evolution_cycle()
                evolution_summary = f"\n\n{ee.format_evolution_summary(evo_result)}"
            except Exception as e:
                evolution_summary = f"\n\nEvolution cycle skipped: {e}"
                print(f"[Orchestrator] Evolution engine error: {e}")

        # Domain update cycle — runs weekly on Saturdays alongside evolution
        domain_summary = ""
        if datetime.date.today().weekday() == 5:  # Saturday = 5
            try:
                from eos_ai.context import load_context_from_env
                from eos_ai.research_engine import ResearchEngine

                ctx_d = load_context_from_env()
                re_d = ResearchEngine(ctx_d)
                d_result = re_d.run_domain_update_cycle()
                domain_summary = (
                    f"\n\nDomain update: {d_result['scanned']} scanned, "
                    f"{len(d_result['updated'])} updated"
                    + (f" ({', '.join(d_result['updated'])})" if d_result["updated"] else "")
                )
            except Exception as e:
                domain_summary = f"\n\nDomain update skipped: {e}"
                print(f"[Orchestrator] Domain update error: {e}")

        # AI landscape scan — runs weekly on Saturdays
        ai_scan_summary = ""
        if datetime.date.today().weekday() == 5:  # Saturday = 5
            try:
                from eos_ai.context import load_context_from_env
                from eos_ai.research_engine import ResearchEngine

                ctx_ai = load_context_from_env()
                re_ai = ResearchEngine(ctx_ai)
                ai_scan = re_ai.scan_ai_landscape()
                ai_scan_summary = (
                    f"\n\nAI landscape scan: {ai_scan.get('cost_updates', 0)} cost updates"
                )
                print(
                    f"[Orchestrator] AI landscape scan: "
                    f"{ai_scan.get('cost_updates', 0)} cost updates"
                )
            except Exception as e:
                ai_scan_summary = f"\n\nAI landscape scan skipped: {e}"
                print(f"[Orchestrator] AI landscape scan error: {e}")

        # Embedding backfill — runs weekly on Saturdays
        if datetime.date.today().weekday() == 5:  # Saturday = 5
            try:
                from eos_ai.embedding_engine import EmbeddingEngine
                from eos_ai.context import load_context_from_env

                ctx_ee = load_context_from_env()
                ee = EmbeddingEngine()
                backfill = ee.backfill_missing(ctx_ee.org_id)
                if backfill.get("embedded", 0) > 0:
                    print(f"[Orchestrator] Backfilled {backfill['embedded']} embeddings")
            except Exception as e:
                print(f"[Orchestrator] Embedding backfill error: {e}")

        # World pulse scan — runs weekly on Saturdays
        world_pulse_summary = ""
        if datetime.date.today().weekday() == 5:  # Saturday = 5
            try:
                from eos_ai.context import load_context_from_env
                from eos_ai.world_pulse import WorldPulse

                ctx_wp = load_context_from_env()
                wp = WorldPulse(ctx_wp)
                pulse = wp.run_pulse_scan()
                world_pulse_summary = (
                    f"\n\nWorld pulse: {pulse['total_integrated']} items integrated "
                    f"across {len(pulse['sources_scanned'])} sources"
                )
                print(f"[Orchestrator] World pulse: {pulse['total_integrated']} items integrated")
            except Exception as e:
                world_pulse_summary = f"\n\nWorld pulse skipped: {e}"
                print(f"[Orchestrator] World pulse error: {e}")

        # Ambient state refresh — runs every morning
        try:
            refresh_ambient_state(ctx)
        except Exception as e:
            print(f"[Orchestrator] Ambient state refresh error: {e}")

        # Pattern detection cycle — runs every morning
        pattern_summary = ""
        try:
            from eos_ai.context import load_context_from_env
            from eos_ai.knowledge_graph import KnowledgeGraph

            ctx_kg = load_context_from_env()
            kg = KnowledgeGraph(ctx_kg)
            all_patterns: list[dict] = []
            for vid in VentureKnowledgeBase.list_ventures():
                all_patterns.extend(kg.find_patterns(vid))
            high_patterns = [p for p in all_patterns if p.get("signal_tier") == "HIGH"]
            if high_patterns:
                top = high_patterns[0]
                pattern_summary = (
                    f"\n\nPatterns: {len(all_patterns)} detected, "
                    f"{len(high_patterns)} high-confidence\n"
                    f"Top: {top['description']}"
                )
            else:
                pattern_summary = (
                    f"\n\nPatterns: {len(all_patterns)} detected, none high-confidence yet"
                )
        except Exception as e:
            pattern_summary = f"\n\nPattern detection skipped: {e}"
            print(f"[Orchestrator] Pattern detection error: {e}")

        # Daily backup — critical local files to /opt/OS/backups/
        backup_summary = ""
        try:
            import subprocess as _sp

            _br = _sp.run(
                ["bash", f"{_REPO_ROOT}/scripts/backup.sh"],
                capture_output=True,
                text=True,
                timeout=60,
            )
            if _br.returncode == 0:
                _first_line = _br.stdout.strip().splitlines()[0] if _br.stdout.strip() else "done"
                backup_summary = f"\n\nBackup: {_first_line}"
            else:
                backup_summary = f"\n\nBackup: failed ({_br.stderr[:80]})"
            print(f"[Orchestrator] {backup_summary.strip()}")
        except Exception as _be:
            backup_summary = f"\n\nBackup: skipped ({_be})"
            print(f"[Orchestrator] Backup error: {_be}")

        # Build Telegram message (4096 char limit)
        tg_text = (
            "EOS MORNING BRIEF\n"
            + "=" * 30
            + "\n\n"
            + brief
            + improvement_summary
            + profile_summary
            + self_org_summary
            + strategy_summary
            + reality_summary
            + research_summary
            + evolution_summary
            + domain_summary
            + ai_scan_summary
            + world_pulse_summary
            + pattern_summary
            + backup_summary
        )
        if len(tg_text) > 4000:
            tg_text = tg_text[:3990] + "\n...[truncated]"

        _notify(tg_text)
        print("[Orchestrator] Brief sent to Telegram.")
        print("[Orchestrator] ── Morning cycle complete ──")


# ─── Ambient state refresh ───────────────────────────────────────────────────


def refresh_ambient_state(ctx: EOSContext) -> None:
    """
    Compute a fresh reality snapshot and cache it as ambient state.
    Called every morning by run_morning_cycle() and on first startup.
    The cached state is consumed by CognitiveLoop PERCEIVE (step 1e) so
    reality context is always available without a fresh LLM call per message.
    """
    try:
        from eos_ai.reality_context import RealityContext
        from eos_ai.session_state import SessionState

        rc = RealityContext(ctx)
        reality = rc.get_current_reality()
        SessionState.set_ambient(reality)
        venture_count = len([v for v, s in reality.items() if s])
        print(f"[Orchestrator] Ambient state refreshed — {venture_count} ventures")
    except Exception as e:
        print(f"[Orchestrator] Ambient state refresh error: {e}")


# ─── Ambient refresh background loop ─────────────────────────────────────────


def start_ambient_refresh_loop(ctx: EOSContext) -> None:
    """
    Start a background daemon thread that refreshes ambient state.
    Uses work_state to idle efficiently — exponential backoff under pressure,
    instant wake on signal.

    Called by:
      - telegram_control.py at startup
      - discord_bot.py at startup
      - orchestrator __main__ (no-op in cron context — process exits)
    """
    import threading
    import time

    def _refresh_loop() -> None:
        while True:
            from runtime.work_state import detect_work_state, record_signal

            ws = detect_work_state()

            # Idle gate — no work, no signal → sleep with backoff
            if ws.is_idle and ws.pressure in (
                ws.pressure.HIGH,
                ws.pressure.CRITICAL,
            ):
                if ws.idle_delay > 60:
                    print(
                        f"[Ambient] Idle — pressure={ws.pressure.value}, "
                        f"next check in {int(ws.idle_delay)}s"
                    )
                time.sleep(ws.idle_delay)
                continue

            # Backpressure gate — moderate pressure, skip heavy work
            try:
                from runtime.provider_state import get_system_state

                _sys = get_system_state()
                if not _sys.allow_execution():
                    time.sleep(ws.idle_delay)
                    continue
                _sys.budget.record_cycle()
            except Exception:
                pass

            try:
                refresh_ambient_state(ctx)
            except Exception as _e:
                print(f"[Ambient] Refresh error: {_e}")

            # Proactive intelligence scan
            try:
                from eos_ai.proactive_engine import ProactiveIntelligenceEngine

                _pie = ProactiveIntelligenceEngine(ctx)
                _signals = _pie.scan()
                if _signals:
                    print(f"[Proactive] {len(_signals)} signal(s) detected:")
                    for _s in _signals:
                        print(f"  [{_s.urgency}] {_s.title}")
                    _pie.scan_and_deliver(
                        send_telegram_fn=_notify,
                        min_urgency=3,
                    )
            except Exception as _pe:
                print(f"[Proactive] Scan failed: {_pe}")

            time.sleep(ws.idle_delay)

    t = threading.Thread(target=_refresh_loop, daemon=True, name="ambient-refresh")
    t.start()
    print("[Ambient] Background refresh loop started (adaptive interval)")


# ─── CLI entry point ─────────────────────────────────────────────────────────

if __name__ == "__main__":
    from eos_ai.context import load_context_from_env
    from eos_ai.knowledge_domains import KnowledgeDomainRegistry
    from eos_ai.research_engine import ResearchEngine

    _ctx = load_context_from_env()

    # Run AI landscape scan on first start if technology_ai domain has never been updated
    try:
        _registry = KnowledgeDomainRegistry()
        _due = _registry.get_update_schedule()
        if "technology_ai" in _due:
            print("[Orchestrator] technology_ai domain never updated — running AI landscape scan")
            _re = ResearchEngine(_ctx)
            _re.scan_ai_landscape()
    except Exception as _e:
        print(f"[Orchestrator] First-start AI scan failed: {_e}")

    run_full_morning_cycle(_ctx)
    try:
        from eos_ai.context import load_ventures_from_env

        _ventures = load_ventures_from_env()
        run_ceo_morning_delegation(_ctx, _ventures)
    except Exception as e:
        print(f"[Morning] CEO delegation failed: {e}")
    start_ambient_refresh_loop(_ctx)
