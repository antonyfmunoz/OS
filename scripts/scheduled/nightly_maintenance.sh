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

Step 5 — Session state update:
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

echo "=== Done: $(date) ===" >> "$LOG"
