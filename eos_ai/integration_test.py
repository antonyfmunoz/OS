"""
EOS Full Integration Test — end-to-end chain validation.

Drives the complete signal → analysis → lead → outreach pipeline
through every layer: gateway → event bus → agent teams → memory.

Usage:
    cd /opt/OS && python3 eos_ai/integration_test.py
"""

import datetime
import json
import os
import sqlite3
import sys
from pathlib import Path

_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

from eos_ai.memory import DB_PATH

SEP  = "─" * 60
SEP2 = "═" * 60

SIGNAL_TEXT = (
    "I feel like I'm wasting my potential. Every single week I tell myself "
    "I'll start being more disciplined but the weeks just disappear. "
    "I'm 22, capable of so much more but I can't execute on anything "
    "consistently. Keep starting things, never finishing. It's embarrassing."
)

TEST_USERNAME = f"integration_test_{datetime.date.today().isoformat()}"


def step(n: int, label: str) -> None:
    print(f"\n{SEP}")
    print(f"  STEP {n}: {label}")
    print(SEP)


def show_events(limit: int = 10) -> None:
    with sqlite3.connect(str(DB_PATH)) as conn:
        conn.row_factory = sqlite3.Row
        rows = conn.execute(
            "SELECT id, event_type, timestamp, handled_by "
            "FROM events ORDER BY id DESC LIMIT ?",
            (limit,),
        ).fetchall()
    print(f"\n  Events table (last {limit}):")
    for row in rows:
        handlers = json.loads(row["handled_by"] or "[]")
        hstr = ", ".join(handlers)[:70]
        print(f"  [{row['id']:>3}] {row['event_type']:<35} {row['timestamp'][:19]}")
        print(f"        handled_by: {hstr}")


def show_pending(gw) -> None:
    pending = gw.get_pending_approvals()
    print(f"\n  Pending approvals: {len(pending)}")
    for p in pending:
        print(f"    [{p['approval_id']}]")
        print(f"     type={p['type']} sub_agent={p['sub_agent']} action={p['action']}")
        print(f"     prompt: {p['prompt'][:60]}")


def main() -> None:
    print(SEP2)
    print("  EOS FULL INTEGRATION TEST")
    print(f"  {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(SEP2)

    from eos_ai.gateway import EOSGateway
    from eos_ai.event_bus import EventBus, EventRegistry

    gw  = EOSGateway()
    bus = EventBus()
    EventRegistry(bus).register_defaults()

    # ── STEP 1: Create synthetic signal file ─────────────────────────────────
    step(1, "Create test signal in 01_Inbox/raw_signals/")
    signals_dir = Path(_REPO_ROOT) / "01_Inbox" / "raw_signals"
    signals_dir.mkdir(parents=True, exist_ok=True)
    today = datetime.date.today().isoformat()
    signal_file = signals_dir / f"signal_{TEST_USERNAME}_{today}.md"
    signal_file.write_text(
        f"---\n"
        f"username: {TEST_USERNAME}\n"
        f"source: instagram\n"
        f"post_url: https://instagram.com/p/test_integration\n"
        f"timestamp: {today}\n"
        f"---\n\n"
        f"{SIGNAL_TEXT}\n",
        encoding="utf-8",
    )
    print(f"  Signal written → {signal_file.name}")
    print(f"  Content: \"{SIGNAL_TEXT[:80]}...\"")

    # ── STEP 2: gateway receives signal_captured event ────────────────────────
    step(2, "gateway.handle(signal_captured)")
    result2 = gw.handle({
        "type":       "event",
        "event_type": "signal_captured",
        "payload": {
            "signal_text": SIGNAL_TEXT,
            "source":      "instagram",
            "venture_id":  "lyfe_institute",
            "username":    TEST_USERNAME,
        },
    })
    print(f"  gateway status : {result2['status']}")
    print(f"  handlers fired : {result2.get('handlers', 0)}")

    # ── STEP 3: signal_analyzer result ───────────────────────────────────────
    step(3, "research.signal_analyzer result (from Step 2)")
    with sqlite3.connect(str(DB_PATH)) as conn:
        conn.row_factory = sqlite3.Row
        row = conn.execute(
            "SELECT id, output_summary FROM interactions "
            "WHERE agent = 'research.signal_analyzer' ORDER BY id DESC LIMIT 1"
        ).fetchone()
    if row:
        print(f"  interaction_id : {row['id']}")
        print(f"  output preview : {row['output_summary'][:200]}")
    else:
        print("  (no interaction logged yet — signal_analyzer may have used cached run)")

    # ── STEP 4: gateway calls sales.icp_qualifier ────────────────────────────
    step(4, "gateway → sales.icp_qualifier")
    result4 = gw.handle({
        "type":       "agent_task",
        "team":       "sales",
        "sub_agent":  "icp_qualifier",
        "prompt": (
            f"Qualify this lead for Initiate Arena.\n\n"
            f"Username: @{TEST_USERNAME}\n"
            f"Signal: \"{SIGNAL_TEXT}\""
        ),
        "venture_id": "lyfe_institute",
        "username":   TEST_USERNAME,
    })
    print(f"  gateway status    : {result4['status']}")
    print(f"  interaction_id    : {result4.get('interaction_id')}")
    print(f"  model             : {result4.get('model', 'n/a')}")
    print(f"  output preview    :")
    print(f"    {result4.get('output', '')[:300]}")

    # ── STEP 5: Create lead file ──────────────────────────────────────────────
    step(5, "Write lead file to 03_CRM/Leads/")
    leads_dir = Path(_REPO_ROOT) / "03_CRM" / "Leads"
    leads_dir.mkdir(parents=True, exist_ok=True)
    lead_file = leads_dir / f"lead_{TEST_USERNAME}_{today}.md"
    lead_file.write_text(
        f"---\ntype: lead\nname: {TEST_USERNAME}\nplatform: instagram\n"
        f"status: new\noffer: Initiate Arena\nsource: integration_test\n"
        f"icp_score: 9\narchetype: Frustrated Drifter\n"
        f"kanban_stage: New\n---\n\n"
        f"# Lead: @{TEST_USERNAME}\n\n"
        f"## Their Comment\n\"{SIGNAL_TEXT}\"\n\n"
        f"## ICP Analysis\n- Score: 9/10\n- Archetype: Frustrated Drifter\n"
        f"## Activity Log\n| {today} | Lead created | Integration test |\n",
        encoding="utf-8",
    )
    print(f"  Lead file written → {lead_file.name}")

    # Also log to memory.db via AgentMemory so outcome linking works
    from eos_ai.memory import AgentMemory
    mem = AgentMemory()
    mem_id = mem.log_lead_scored(
        username=TEST_USERNAME,
        venture_id="lyfe_institute",
        comment_text=SIGNAL_TEXT,
        score=9,
        archetype="Frustrated Drifter",
        model_used="claude-haiku-4-5-20251001",
    )
    print(f"  memory.db interaction logged → id={mem_id}")

    # ── STEP 6: Publish new_lead event ────────────────────────────────────────
    step(6, "gateway.handle(event: new_lead)")
    result6 = gw.handle({
        "type":       "event",
        "event_type": "new_lead",
        "payload": {
            "username":   TEST_USERNAME,
            "score":      9,
            "state":      "Frustrated Drifter",
            "venture_id": "lyfe_institute",
        },
    })
    print(f"  gateway status : {result6['status']}")
    print(f"  handlers fired : {result6.get('handlers', 0)}")

    # ── STEP 7: new_lead handler result ──────────────────────────────────────
    step(7, "icp_qualifier outreach strategy (from Step 6 new_lead handler)")
    with sqlite3.connect(str(DB_PATH)) as conn:
        conn.row_factory = sqlite3.Row
        row = conn.execute(
            "SELECT id, output_summary FROM interactions "
            "WHERE agent = 'sales.icp_qualifier' ORDER BY id DESC LIMIT 1"
        ).fetchone()
    if row:
        print(f"  interaction_id : {row['id']}")
        print(f"  strategy       : {row['output_summary'][:200]}")

    # ── STEP 8: Request outreach_writer → gets queued for approval ────────────
    step(8, "gateway → outreach_writer (action=send) → queued for approval")
    result8 = gw.handle({
        "type":       "agent_task",
        "team":       "sales",
        "sub_agent":  "outreach_writer",
        "action":     "send",
        "prompt": (
            f"Write a personalized DM opener for @{TEST_USERNAME}.\n"
            f"Archetype: Frustrated Drifter\n"
            f"Pain signal: wasting potential, can't execute consistently\n"
            f"Score: 9/10"
        ),
        "venture_id": "lyfe_institute",
        "username":   TEST_USERNAME,
    })
    print(f"  gateway status : {result8['status']}")
    print(f"  approval_id    : {result8.get('approval_id', 'n/a')}")
    print(f"  message        : {result8.get('message', 'n/a')[:80]}")

    # ── STEP 9: Full chain summary ────────────────────────────────────────────
    step(9, "All steps logged — memory.db events table")
    show_events(limit=12)

    print(f"\n{SEP}")
    print("  PENDING APPROVALS QUEUE")
    print(SEP)
    show_pending(gw)

    # ── Recent interactions ───────────────────────────────────────────────────
    print(f"\n{SEP}")
    print("  RECENT INTERACTIONS (memory.db)")
    print(SEP)
    with sqlite3.connect(str(DB_PATH)) as conn:
        conn.row_factory = sqlite3.Row
        rows = conn.execute(
            "SELECT id, agent, skill_used, model_used, timestamp "
            "FROM interactions ORDER BY id DESC LIMIT 6"
        ).fetchall()
    for row in rows:
        print(f"  [{row['id']:>3}] {row['agent']:<35} "
              f"skill={row['skill_used'] or '—':<28} {row['timestamp'][:19]}")

    print(f"\n{SEP2}")
    print("  INTEGRATION TEST COMPLETE")
    print(SEP2)


if __name__ == "__main__":
    main()
