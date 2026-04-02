---
description: "End of day sync. Captures what happened today, closes open loops, sets tomorrow's one objective. Run at end of every working day."
---

Run end of day sync for Antony.

Pull today's activity:
!`python3 -c "
import sys; sys.path.insert(0,'/opt/OS')
from dotenv import load_dotenv
load_dotenv('/opt/OS/eos_ai/.env')
try:
    import psycopg2, os
    conn = psycopg2.connect(os.getenv('DATABASE_URL',''))
    cur = conn.cursor()
    cur.execute(\"\"\"
        SELECT COUNT(*) FROM tasks
        WHERE status='completed'
        AND updated_at::date = CURRENT_DATE
    \"\"\")
    completed = cur.fetchone()[0]
    cur.execute(\"\"\"
        SELECT COUNT(*) FROM tasks
        WHERE status='pending'
    \"\"\")
    pending = cur.fetchone()[0]
    conn.close()
    print(f'Completed today: {completed}')
    print(f'Still pending: {pending}')
except Exception as e:
    print(f'DB unavailable: {e}')
"`

Format the EOD sync:
**EOD SYNC — [today's date]**
Completed Today: [what got done]
Open Loops: [what's still pending]
Wins: [what moved the needle]
Misses: [what didn't happen and why]
Tomorrow's One Objective: [single focus]
Tomorrow's First Action: [exactly what to do]
