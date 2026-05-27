---
description: "Start all EOS autonomous loops for this session. Run at the start of any working session. Loops run until session closes."
---

Starting EOS autonomous loops for this session.

!`echo "Session: $(date)"`

Schedule the following loops:

/loop 5m "Check pending agent tasks.
  Run: python3 /opt/OS/services/agent_task_executor.py
  Report: how many tasks processed."

/loop 15m "Check for DM replies in the outreach pipeline.
  Run: python3 -c \"
import sys; sys.path.insert(0,'/opt/OS')
from dotenv import load_dotenv
load_dotenv('/opt/OS/services/.env')
try:
    import psycopg2, os
    conn = psycopg2.connect(os.getenv('DATABASE_URL',''))
    cur = conn.cursor()
    cur.execute(\\\"SELECT COUNT(*) FROM leads WHERE replied=true AND status='new'\\\")
    replies = cur.fetchone()[0]
    conn.close()
    if replies > 0:
        print(f'⚡ {replies} replies need handling')
    else:
        print('No new replies')
except Exception as e:
    print(f'Pipeline check: {e}')
\""

/loop 1d "Check Claude Code version for updates.
  Run: python3 /opt/OS/scripts/session_start_context.py
  If version changed: alert and suggest /check-cc-updates"

After scheduling, confirm:
- Loop 1: agent task executor (5m)
- Loop 2: DM reply checker (15m)
- Loop 3: CC version checker (daily)

All loops active. Session is now autonomous.
