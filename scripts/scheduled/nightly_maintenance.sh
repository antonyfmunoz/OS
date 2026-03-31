#!/bin/bash
# EOS Nightly Maintenance — runs 2:00am via cron
# claude -p with dangerously-skip-permissions on private VPS

set -euo pipefail

LOG="/opt/OS/logs/nightly_$(date +%Y%m%d).log"
echo "=== EOS Nightly Maintenance: $(date) ===" >> "$LOG"

cd /opt/OS

claude -p --allowedTools "Bash Read Write Edit Glob Grep" \
  --add-dir /opt/OS \
  --max-budget-usd 0.50 \
  "Read /opt/OS/.claude/CLAUDE.md and /opt/OS/CLAUDE.md.

Run EOS nightly maintenance. Execute each step, report results.

Step 0 — GWS auth check:
  AUTH_STATUS=\$(npx @googleworkspace/cli auth status 2>&1)
  if echo \"\$AUTH_STATUS\" | grep -q \"invalid\|expired\|error\"; then
    python3 -c \"
import os, sys; sys.path.insert(0, '/opt/OS')
from dotenv import load_dotenv
load_dotenv('/opt/OS/13_Scripts/.env')
from eos_ai.discord_utils import post_to_webhook
webhook = os.getenv('DISCORD_BRIEF_WEBHOOK', '')
if webhook:
  post_to_webhook(
    '⚠️ GWS token expired. Re-auth needed.\n'
    'Run: npx @googleworkspace/cli auth login',
    webhook=webhook)
\"
  fi

Step 1 — Service health check:
  docker ps --format '{{.Names}}: {{.Status}}'
  docker logs os-discord --tail 5
  docker logs os-bot --tail 5
  If any container is not Up — restart it with docker compose restart [service].

Step 2 — Import check:
  python3 -c \"import sys; sys.path.insert(0,'/opt/OS'); import eos_ai; print('imports: clean')\"

Step 3 — Memory compression:
  Read /root/.claude/projects/-opt-OS/memory/MEMORY.md
  Review all memory files in /root/.claude/projects/-opt-OS/memory/
  Remove entries that are outdated or redundant.
  Keep only permanently true facts.
  The MEMORY.md index must stay under 200 lines.

Step 4 — Clean temp files:
  find /opt/OS/logs -name '*.log' -mtime +7 -delete 2>/dev/null || true
  find /tmp -name 'eos_*' -mtime +1 -delete 2>/dev/null || true

Step 5 — Notion outcome sync:
  python3 /opt/OS/scripts/notion_outcome_sync.py

Step 6 — Session state update:
  python3 -c \"
import sys; sys.path.insert(0,'/opt/OS')
from eos_ai.session_state import SessionState
SessionState.save(
  phase='Nightly maintenance',
  last_completed='Nightly cycle completed: $(date +%Y-%m-%d)',
  in_progress=None,
  next_steps=['Check morning prep log', 'Review any restart events'],
  files_modified=[]
)
print('State saved')
\"

Report: PASS or list any issues found." >> "$LOG" 2>&1

# Research workflows — run outside claude -p to avoid budget conflict
echo "--- Research cycle: $(date) ---" >> "$LOG"

python3 << 'RESEARCH_EOF'
import sys, os, json, glob
from datetime import datetime
from pathlib import Path

sys.path.insert(0, '/opt/OS')
from dotenv import load_dotenv
load_dotenv('/opt/OS/eos_ai/.env')
from eos_ai.gateway import EOSGateway

gateway = EOSGateway()

SIGNALS_DIR = Path('/opt/OS/01_Inbox/processed_signals')
KNOWLEDGE_DIR = Path('/opt/OS/07_Knowledge')
today = datetime.now().strftime('%Y-%m-%d')

# Load recent processed signals — last 50 files by modification time
signal_files = sorted(SIGNALS_DIR.glob('*.md'), key=lambda f: f.stat().st_mtime, reverse=True)[:50]
signal_content = ''
for sf in signal_files:
    try:
        signal_content += sf.read_text()[:500] + '\n---\n'
    except Exception:
        pass

if not signal_content:
    print('[Research] No signals found — skipping')
    exit(0)

print(f'[Research] Loaded {len(signal_files)} signals')

tasks = [
    {
        'name': 'signal_intelligence',
        'prompt': f"""Analyze these Instagram ICP signals from Lyfe Institute's target audience (men 18-25, ambitious but stuck):

{signal_content[:6000]}

Extract:
1. Top 3 recurring pain patterns with exact quotes where possible
2. Strongest conversion signals (language that shows buying intent)
3. Any new ICP archetypes emerging beyond Ambitious But Stuck and Frustrated Drifter
4. Recommended messaging adjustments based on what you see

Be specific. Cite signal sources. End with 3 actionable implications.""",
        'output_path': KNOWLEDGE_DIR / 'ICP' / f'signal_analysis_{today}.md',
    },
    {
        'name': 'pattern_analysis',
        'prompt': f"""Analyze these ICP signals for patterns that should update our understanding of the Lyfe Institute target customer:

{signal_content[:4000]}

Focus on:
1. What do they say they want vs what they actually need
2. What language do they use naturally (copy this exactly for outreach)
3. What objections or fears appear repeatedly
4. What triggers them to engage vs scroll past

Output a structured ICP pattern update that can be used to improve outreach messaging.""",
        'output_path': KNOWLEDGE_DIR / 'ICP' / f'icp_patterns_{today}.md',
    },
    {
        'name': 'market_intelligence',
        'prompt': f"""Generate a weekly market intelligence report for Lyfe Institute (Initiate Arena, $750, 90-day coaching, men 18-25).

Based on these recent ICP signals:
{signal_content[:3000]}

Include:
1. ICP signal trends this week
2. Competitor observations if any signals mention alternatives
3. Recommended offer or messaging adjustments
4. One high-confidence action to take this week

Format as a structured report.""",
        'output_path': KNOWLEDGE_DIR / 'Reports' / 'Market_Reports' / f'market_intelligence_{today}.md',
    },
]

for task in tasks:
    try:
        print(f'[Research] Running {task["name"]}...')
        result = gateway.handle({
            'type': 'agent_task',
            'prompt': task['prompt'],
            'venture_id': 'lyfe_institute',
            'sub_agent': 'research_agent',
            'channel': 'nightly_maintenance',
            'session_id': f'nightly_{task["name"]}_{today}',
        })

        status = result.get('status', 'unknown')
        tokens = result.get('tokens', 0)
        output = result.get('output', '')

        print(f'[Research] {task["name"]}: {status} — {tokens} tokens')

        if status == 'ok' and output:
            # Write to knowledge base
            output_path = task['output_path']
            output_path.parent.mkdir(parents=True, exist_ok=True)
            output_path.write_text(f'# {task["name"]} — {today}\n\n{output}')
            print(f'[Research] Written: {output_path.name}')
        else:
            print(f'[Research] {task["name"]} produced no output')

    except Exception as e:
        print(f'[Research] {task["name"]} failed: {e}')

print('[Research] Cycle complete')
RESEARCH_EOF
>> "$LOG" 2>&1

echo "--- Research cycle done: $(date) ---" >> "$LOG"

echo "=== Done: $(date) ===" >> "$LOG"
