---
description: "Generate the morning brief, write to Notion, return the link. Run at start of every day."
---

Generate a morning brief for Antony. Write it to Notion and return the link.

Pull current state:
!`python3 -c "
import sys; sys.path.insert(0,'/opt/OS')
from dotenv import load_dotenv
load_dotenv('/opt/OS/services/.env')
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

!`python3 -c "
import sys; sys.path.insert(0,'/opt/OS')
from dotenv import load_dotenv
load_dotenv('/opt/OS/services/.env')
try:
    from adapters.google_workspace.gws_connector import GWSConnector
    gws = GWSConnector()
    events = gws.get_today_events()
    for e in events[:5]:
        start = e.get('start', '')
        if start and 'T' in str(start):
            start = str(start).split('T')[1][:5]
        print(f'  {start} — {e.get(\"title\", \"\")}')
    if not events:
        print('No events today')
except Exception as e:
    print(f'Calendar: {e}')
"`

Based on the data above, build a brief dict and publish to Notion:

```python
# notion_publisher: dormant — no direct substrate equivalent yet
publisher = get_publisher()
url = publisher.publish_morning_brief(content={
    'binding_constraint': '[diagnosed constraint]',
    'one_objective': '[single objective]',
    'priority_action': '[first action]',
    'calendar_today': '[calendar events]',
    'tasks_today': f'Pending: {pending}',
})
```

Output format:
**Brief written to Notion: {url}**

Then post the URL to Discord:
```python
from transports.discord.discord_utils import post_to_webhook
import os
webhook = os.getenv('DISCORD_BRIEF_WEBHOOK', '')
if webhook and url:
    post_to_webhook(f'☀️ **Morning Brief ready**\n{url}', webhook_url=webhook)
```

Then output the brief content inline for this conversation.
