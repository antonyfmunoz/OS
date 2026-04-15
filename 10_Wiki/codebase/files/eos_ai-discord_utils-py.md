---
type: codebase-file
path: eos_ai/discord_utils.py
module: eos_ai.discord_utils
lines: 173
size: 5372
generated: 2026-04-12
---

# eos_ai/discord_utils.py

discord_utils — single source of truth for all Discord posting from EOS.

Every module that posts to Discord must use this.
Never write custom chunking or webhook logic elsewhere.

...

**Lines:** 173 | **Size:** 5,372 bytes

## Used By

- [[scripts-inbox_gps_afternoon-py]]
- [[services-discord_bot-py]]

## Contains

- **fn** [[eos_ai-discord_utils-py-chunk_message]]`(content, title) → list[str]`
- **fn** [[eos_ai-discord_utils-py-post_to_webhook]]`(content, title, username, webhook_url) → bool`
- **fn** [[eos_ai-discord_utils-py-post_to_channel]]`(channel, content, title) → None`

## Import Statements

```python
import os
import time
from dotenv import load_dotenv
```
