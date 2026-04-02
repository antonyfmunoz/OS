---
description: "Generate the morning brief: today's one objective, binding constraint, pending tasks, calendar, and priorities. Run at start of every day."
---

Generate a morning brief for Antony.

Pull:
!`python3 -c "
import sys; sys.path.insert(0,'/opt/OS')
from dotenv import load_dotenv
load_dotenv('/opt/OS/eos_ai/.env')
try:
    import psycopg2, os
    conn = psycopg2.connect(os.getenv('DATABASE_URL',''))
    cur = conn.cursor()
    cur.execute(\"SELECT COUNT(*) FROM tasks WHERE status='pending'\")
    pending = cur.fetchone()[0]
    conn.close()
    print(f'Pending tasks: {pending}')
except:
    print('Pending tasks: (DB unavailable)')
"`

Format:
**TODAY'S BRIEF**
Date: [today PDT]
Stage: [current stage]
Binding Constraint: [what's blocking growth]
One Objective: [the single thing that matters]
Pending Tasks: [count and top 3]
Calendar: [today's meetings if any]
Priority Action: [exactly what to do first]
