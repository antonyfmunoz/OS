---
description: "End of day sync. Write to Notion, return the link. Captures what happened, closes open loops, sets tomorrow's objective."
---

Run end of day sync for Antony. Write to Notion and return the link.

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

Based on the data and today's conversation context, build an EOD sync and publish to Notion:

```python
from eos_ai.notion_publisher import get_publisher
publisher = get_publisher()
url = publisher.publish_eod_sync(content={
    'completed': '[what got done today]',
    'open_loops': '[what is still pending]',
    'wins': '[what moved the needle]',
    'misses': '[what did not happen and why]',
    'tomorrow_objective': '[single focus for tomorrow]',
})
```

Output format:
**EOD Sync written to Notion: {url}**

Then post the URL to Discord:
```python
from eos_ai.discord_utils import post_to_webhook
import os
webhook = os.getenv('DISCORD_BRIEF_WEBHOOK', '')
if webhook and url:
    post_to_webhook(f'📋 **EOD Sync ready**\n{url}', webhook_url=webhook)
```

Then output the EOD sync content inline for this conversation.
