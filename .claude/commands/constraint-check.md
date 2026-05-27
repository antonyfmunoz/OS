---
description: "Diagnose current binding constraint across all ventures. Write diagnosis to Notion, return the link."
---

Run a constraint check across all ventures.

!`python3 -c "
import sys; sys.path.insert(0,'/opt/OS')
from dotenv import load_dotenv
load_dotenv('/opt/OS/services/.env')
try:
    from substrate.state.context.context import load_context_from_env
    from substrate.understanding.intelligence.input_intelligence import InputIntelligence as CEOIntelligence
    ctx = load_context_from_env()
    intel = CEOIntelligence(ctx)
    diagnosis = intel.diagnose_constraint()
    print(diagnosis)
except Exception as e:
    print(f'Constraint diagnosis error: {e}')
"`

Based on the diagnosis above, answer:
1. What is the binding constraint right now?
2. What is the ONE objective that addresses it?
3. What would unlock stage advancement?
4. What should NOT be worked on today?

Then write the diagnosis to Notion:

```python
# notion_publisher: dormant — no direct substrate equivalent yet
publisher = get_publisher()
url = publisher.publish_constraint_diagnosis(
    venture_id='lyfe_institute',  # or whichever venture is constrained
    diagnosis={
        'constraint': '[the binding constraint]',
        'diagnosis': '[full diagnosis text]',
        'evidence': '[data supporting the diagnosis]',
        'recommendation': '[the ONE action to take]',
    },
)
```

Output: **Constraint diagnosis written to Notion: {url}**

Post to Discord:
```python
from transports.discord.discord_utils import post_to_webhook
import os
webhook = os.getenv('DISCORD_BRIEF_WEBHOOK', '')
if webhook and url:
    post_to_webhook(f'🎯 **Constraint Diagnosis ready**\n{url}', webhook_url=webhook)
```
