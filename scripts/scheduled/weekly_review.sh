#!/bin/bash
# EOS Weekly Review — runs Sunday 6:00am via cron
# Full health audit + report to Discord

set -euo pipefail

LOG="/opt/OS/logs/weekly_$(date +%Y%m%d).log"
REPORT="/tmp/weekly_report_$(date +%Y%m%d).txt"
echo "=== EOS Weekly Review: $(date) ===" >> "$LOG"

cd /opt/OS

# Provider health gate — skip if no LLM provider is reachable
if ! python3 -c "
import sys; sys.path.insert(0, '/opt/OS')
from dotenv import load_dotenv; load_dotenv('/opt/OS/eos_ai/.env')
from eos_ai.provider_health import check_all
sys.exit(0 if check_all().any_healthy else 1)
" 2>/dev/null; then
  echo "[$(date -Iseconds)] SKIP weekly_review: no healthy LLM provider" >> "$LOG"
  exit 0
fi

claude -p --allowedTools "Bash Read Write Glob Grep" \
  --add-dir /opt/OS \
  --max-budget-usd 1.00 \
  "Read /opt/OS/.claude/CLAUDE.md and /opt/OS/CLAUDE.md.

Run the full weekly EOS health review. Write a concise report to $REPORT.

Step 1 — Run core imports test:
  python3 -c \"
import sys; sys.path.insert(0,'/opt/OS')
import eos_ai
from eos_ai.cognitive_loop import CognitiveLoop
from eos_ai.agent_runtime import AgentRuntime
from eos_ai.authority_engine import AuthorityEngine
from eos_ai.memory import MemoryEngine
from eos_ai.primitives import PRIMITIVE_LIBRARY
print('Core imports: PASS')
print(f'Primitives: {len(PRIMITIVE_LIBRARY)}')
\"

Step 2 — Service uptime:
  docker ps --format '{{.Names}}: {{.Status}} — {{.RunningFor}}'

Step 3 — Skill count:
  python3 -c \"
import sys; sys.path.insert(0,'/opt/OS')
from eos_ai.skill_registry import get_skill_registry
sr = get_skill_registry()
print(f'Skills in registry: {len(sr._skills)}')
\"

Step 4 — Log summary (last 7 days):
  Count lines in /opt/OS/logs/*.log from the past 7 days.
  Note any ERROR patterns: grep -i error /opt/OS/logs/*.log 2>/dev/null | tail -10

Step 5 — Write report to $REPORT:
  Format:
  === EOS Weekly Health Report — [date] ===
  Services: [status]
  Core imports: [PASS/FAIL]
  Primitives: [N]
  Skills: [N]
  Errors this week: [N or list]
  Recommendation: [1-2 lines of highest leverage action]

Step 6 — Post to Discord:
  python3 -c \"
import sys; sys.path.insert(0,'/opt/OS')
from eos_ai.discord_utils import post_to_webhook
report = open('$REPORT').read()
post_to_webhook(report, title='Weekly EOS Health Report')
print('Posted to Discord')
\" 2>/dev/null || echo 'Discord post skipped (webhook not configured)'" >> "$LOG" 2>&1

echo "=== Done: $(date) ===" >> "$LOG"
