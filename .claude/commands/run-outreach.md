---
description: "Execute the outreach sequence: check DM reply queue, score new leads, draft responses for qualified replies, and surface next outreach batch."
---

Run outreach operations.

Check current pipeline:
!`python3 -c "
import sys; sys.path.insert(0,'/opt/OS')
from dotenv import load_dotenv
load_dotenv('/opt/OS/services/.env')
try:
    import psycopg2, os
    conn = psycopg2.connect(os.getenv('DATABASE_URL',''))
    cur = conn.cursor()
    cur.execute(\"SELECT COUNT(*) FROM leads WHERE status='new'\")
    new_leads = cur.fetchone()[0]
    cur.execute(\"SELECT COUNT(*) FROM leads WHERE replied=true AND status='new'\")
    replies = cur.fetchone()[0]
    cur.execute(\"SELECT COUNT(*) FROM leads WHERE dm_sent=true\")
    sent = cur.fetchone()[0]
    conn.close()
    print(f'New leads: {new_leads}')
    print(f'Replies to handle: {replies}')
    print(f'DMs sent total: {sent}')
except Exception as e:
    print(f'Pipeline: {e}')
"`

Based on the pipeline above:
1. For any replies — classify and draft response
   using /reply_handler skill
2. For new qualified leads — draft opener
   using /dm_opener skill
3. Report: what was sent, what's pending,
   what needs Antony's approval
