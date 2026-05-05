---
type: codebase-file
path: eos_ai/email_reviewer.py
module: eos_ai.email_reviewer
lines: 166
size: 5698
generated: 2026-04-12
---

# eos_ai/email_reviewer.py

EmailReviewer — nightly self-review of Email GPS classification.

Runs at 11pm daily. Pulls all email events from the last 24 hours,
checks for anomalies, builds a report, and posts to Discord.

...

**Lines:** 166 | **Size:** 5,698 bytes

## Contains

- **class** [[eos_ai-email_reviewer-py-EmailReviewer]] — 3 methods

## Import Statements

```python
import json
import uuid
from collections import Counter
from datetime import datetime
from datetime import timedelta
```
