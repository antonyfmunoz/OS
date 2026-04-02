---
description: "Babysit loop. Auto-handles pending tasks, surfaces replies, monitors pipeline. Run as: /loop 5m /babysit"
---

Running babysit check.

!`python3 -c "
import sys; sys.path.insert(0,'/opt/OS')
from dotenv import load_dotenv
load_dotenv('/opt/OS/eos_ai/.env')
results = []
try:
    import psycopg2, os
    conn = psycopg2.connect(os.getenv('DATABASE_URL',''))
    cur = conn.cursor()
    cur.execute(\"SELECT COUNT(*) FROM tasks WHERE status='pending'\")
    pending = cur.fetchone()[0]
    cur.execute(\"SELECT COUNT(*) FROM leads WHERE replied=true AND status='new'\")
    replies = cur.fetchone()[0]
    conn.close()
    if pending: results.append(f'{pending} tasks pending')
    if replies: results.append(f'{replies} DM replies')
    print(', '.join(results) if results else 'All clear')
except Exception as e:
    print(f'Check failed: {e}')
"`

If anything needs attention: surface it clearly.
If all clear: report "All clear — system nominal."
