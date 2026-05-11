"""
EOS Status Dashboard — daily health check for the AI system.

Usage:
    python3 /opt/OS/eos_ai/status.py
"""

import json
import os
import sys
import datetime
from pathlib import Path

_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

from dotenv import load_dotenv
load_dotenv(os.path.join(_REPO_ROOT, "services", ".env"))

from eos_ai.db import get_conn, ORG_ID
from eos_ai.memory import AgentMemory
from eos_ai.venture_knowledge import VentureKnowledgeBase
from eos_ai.skill_registry import SkillRegistry

# Model pricing (per token) — mirrors cost_tracker.py
_PRICING = {
    "claude-haiku-4-5-20251001": {"input": 0.000001,  "output": 0.000005},
    "claude-sonnet-4-6":         {"input": 0.000003,  "output": 0.000015},
}

DAILY_DIR  = Path(_REPO_ROOT) / "orchestrator" / "daily"
VAULT      = Path(_REPO_ROOT)

_SEP  = "─" * 60
_SEP2 = "═" * 60


# ─── Helpers ──────────────────────────────────────────────────────────────────

def _bar(pct: float, width: int = 20) -> str:
    filled = int(min(pct / 100, 1.0) * width)
    return "█" * filled + "░" * (width - filled)


def _fmt_tokens(n: int) -> str:
    if n >= 1_000_000:
        return f"{n / 1_000_000:.2f}M"
    if n >= 1_000:
        return f"{n / 1_000:.1f}K"
    return str(n)


def _cost_est(interactions_7d: list[dict]) -> float:
    """Estimate USD cost from Neon token records."""
    total = 0.0
    for row in interactions_7d:
        model    = row.get("model_used", "")
        pricing  = _PRICING.get(model)
        if not pricing:
            continue
        # tokens_json is the Neon column; tokens_used is a normalized alias
        raw = row.get("tokens_json") or row.get("tokens_used") or "{}"
        try:
            tokens = json.loads(raw) if isinstance(raw, str) else (raw or {})
        except (json.JSONDecodeError, TypeError):
            tokens = {}
        inp = tokens.get("prompt",  tokens.get("input",  0))
        out = tokens.get("completion", tokens.get("output", 0))
        total += inp * pricing["input"] + out * pricing["output"]
    return total


# ─── Data fetchers ────────────────────────────────────────────────────────────

def _fetch_7d_raw() -> list[dict]:
    cutoff = (
        datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(days=7)
    ).isoformat()
    try:
        with get_conn(ORG_ID) as cur:
            cur.execute(
                """
                SELECT model_used, tokens_json, agent_label AS agent,
                       input_summary, output_summary, created_at
                FROM interactions
                WHERE org_id = %s AND created_at >= %s
                ORDER BY created_at DESC
                """,
                (ORG_ID, cutoff),
            )
            rows = cur.fetchall()
        return [dict(r) for r in rows]
    except Exception as e:
        print(f"[Status] _fetch_7d_raw failed: {e}")
        return []


def _fetch_skill_outcome_counts() -> dict[str, int]:
    """Return {skill_name: count_of_scored_outcomes} for all skills."""
    try:
        with get_conn(ORG_ID) as cur:
            cur.execute(
                """
                SELECT s.name AS skill_used, COUNT(o.id) AS outcome_count
                FROM interactions i
                JOIN outcomes o ON o.interaction_id = i.id
                JOIN skills s ON s.id = i.skill_id
                WHERE i.org_id = %s AND i.skill_id IS NOT NULL AND o.score IS NOT NULL
                GROUP BY s.name
                """,
                (ORG_ID,),
            )
            rows = cur.fetchall()
        return {r["skill_used"]: r["outcome_count"] for r in rows}
    except Exception as e:
        print(f"[Status] _fetch_skill_outcome_counts failed: {e}")
        return {}


def _fetch_reply_rates() -> list[dict]:
    mem = AgentMemory()
    return mem.reply_rate_by_skill()


def _fetch_total_interactions() -> int:
    try:
        with get_conn(ORG_ID) as cur:
            cur.execute("SELECT COUNT(*) AS cnt FROM interactions WHERE org_id = %s", (ORG_ID,))
            row = cur.fetchone()
        return row["cnt"] if row else 0
    except Exception as e:
        print(f"[Status] _fetch_total_interactions failed: {e}")
        return 0


def _fetch_last_orchestrator_run() -> dict | None:
    try:
        with get_conn(ORG_ID) as cur:
            cur.execute(
                """
                SELECT created_at AS timestamp, input_summary, output_summary
                FROM interactions
                WHERE org_id = %s AND agent_label = 'orchestrator'
                ORDER BY created_at DESC
                LIMIT 1
                """,
                (ORG_ID,),
            )
            row = cur.fetchone()
        if not row:
            return None
        d = dict(row)
        # Normalize created_at to isoformat string for callers
        if hasattr(d["timestamp"], "isoformat"):
            d["timestamp"] = d["timestamp"].isoformat()
        return d
    except Exception as e:
        print(f"[Status] _fetch_last_orchestrator_run failed: {e}")
        return None


def _get_last_brief_excerpt() -> str | None:
    if not DAILY_DIR.exists():
        return None
    briefs = sorted(DAILY_DIR.glob("*.md"), reverse=True)
    if not briefs:
        return None
    text = briefs[0].read_text(encoding="utf-8")
    # Return first 300 chars of the brief body (skip header)
    body_start = text.find("## ")
    snippet = text[body_start:body_start + 300] if body_start != -1 else text[:300]
    return snippet.strip()


# ─── Sections ─────────────────────────────────────────────────────────────────

def _section_north_star() -> None:
    print(_SEP2)
    print("  EOS STATUS DASHBOARD")
    print(f"  {datetime.datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print(_SEP2)
    print()
    print("NORTH STAR — VENTURE STATUS")
    print(_SEP)
    for vid in VentureKnowledgeBase.list_ventures():
        v   = VentureKnowledgeBase.get(vid)
        gap = v.monthly_target - v.monthly_revenue
        pct = (v.monthly_revenue / v.monthly_target * 100) if v.monthly_target > 0 else 0.0
        label = vid.replace("_", " ").title()
        bar   = _bar(pct)
        print(f"  {label}")
        print(f"    Revenue  : ${v.monthly_revenue:>8,.0f}  /  ${v.monthly_target:,.0f} target")
        print(f"    Gap      : ${gap:,.0f}")
        print(f"    Progress : [{bar}] {pct:.1f}%")
        print(f"    Stage    : {v.stage}")
        print()


def _section_7d_activity(rows_7d: list[dict]) -> None:
    print("7-DAY ACTIVITY")
    print(_SEP)

    total_calls  = len(rows_7d)
    total_tokens = sum(
        json.loads(r.get("tokens_used") or "{}").get("total", 0)
        for r in rows_7d
        if True
    )
    cost_est = _cost_est(rows_7d)

    # per-agent breakdown
    from collections import Counter
    agent_counts = Counter(r["agent"] for r in rows_7d)
    model_counts = Counter(r["model_used"] for r in rows_7d)

    print(f"  Agent calls (7d) : {total_calls}")
    print(f"  Tokens used      : {_fmt_tokens(total_tokens)}")
    print(f"  Cost estimate    : ${cost_est:.4f}")
    print()
    if agent_counts:
        print("  By agent:")
        for agent, count in agent_counts.most_common():
            print(f"    {agent:<30} {count} calls")
    if model_counts:
        print("  By model:")
        for model, count in model_counts.most_common():
            print(f"    {model:<40} {count} calls")
    print()


def _section_skill_performance(reply_rates: list[dict], outcome_counts: dict[str, int]) -> None:
    print("SKILL PERFORMANCE — RLHF")
    print(_SEP)
    if not reply_rates:
        print("  No outcome data yet.")
        print()
        return
    for row in reply_rates:
        skill = row["skill_used"] or "(none)"
        total = row["total_interactions"]
        rrate = row["reply_rate_pct"]
        bar   = _bar(rrate)
        print(f"  {skill}")
        print(f"    [{bar}] {rrate:.1f}%  ({row['replies']}/{total} interactions)")
    print()


def _section_last_orchestrator(orch_row: dict | None, excerpt: str | None) -> None:
    print("LAST ORCHESTRATOR RUN")
    print(_SEP)
    if not orch_row:
        print("  No orchestrator runs logged yet.")
        print()
        return
    ts = orch_row["timestamp"]
    print(f"  Timestamp : {ts}")
    if excerpt:
        print()
        print("  Brief excerpt:")
        for line in excerpt.splitlines()[:8]:
            print(f"    {line}")
    print()


def _section_memory(total_interactions: int) -> None:
    print("NEON DATABASE")
    print(_SEP)
    print(f"  Storage            : Neon PostgreSQL (cloud)")
    print(f"  Total interactions : {total_interactions}")
    print()


def _section_skill_readiness(outcome_counts: dict[str, int], registry: SkillRegistry) -> None:
    print("SKILL IMPROVEMENT READINESS  (threshold: 5 scored outcomes)")
    print(_SEP)
    MIN_OUTCOMES = 5
    ready   = []
    waiting = []
    for skill in registry.all_skills():
        count = outcome_counts.get(skill.skill_id, 0)
        if count >= MIN_OUTCOMES:
            ready.append((skill.skill_id, count))
        else:
            waiting.append((skill.skill_id, count))

    if ready:
        print("  READY TO IMPROVE:")
        for sid, cnt in ready:
            print(f"    ✓  {sid:<40}  {cnt} outcomes")
    else:
        print("  READY TO IMPROVE: none")

    print()
    print("  NEEDS MORE DATA:")
    for sid, cnt in waiting:
        bar = "█" * cnt + "░" * (MIN_OUTCOMES - cnt)
        print(f"    ·  {sid:<40}  [{bar}] {cnt}/{MIN_OUTCOMES}")
    print()


# ─── Main ─────────────────────────────────────────────────────────────────────

def main() -> None:
    # Suppress SkillRegistry stdout during load for cleaner output
    import io
    _old_stdout = sys.stdout
    sys.stdout = io.StringIO()
    registry = SkillRegistry()
    sys.stdout = _old_stdout

    rows_7d             = _fetch_7d_raw()
    reply_rates         = _fetch_reply_rates()
    outcome_counts      = _fetch_skill_outcome_counts()
    total_interactions  = _fetch_total_interactions()
    last_orch           = _fetch_last_orchestrator_run()
    brief_excerpt       = _get_last_brief_excerpt()

    _section_north_star()
    _section_7d_activity(rows_7d)
    _section_skill_performance(reply_rates, outcome_counts)
    _section_last_orchestrator(last_orch, brief_excerpt)
    _section_memory(total_interactions)
    _section_skill_readiness(outcome_counts, registry)
    print(_SEP2)


if __name__ == "__main__":
    main()
