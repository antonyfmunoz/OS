---
type: codebase-file
path: services/icp_scorer.py
module: services.icp_scorer
lines: 604
size: 20640
tags: [entry-point]
generated: 2026-05-07
---

# services/icp_scorer.py

> **ENTRY POINT** — Contains `if __name__` or server start.

*No docstring.*

**Lines:** 604 | **Size:** 20,640 bytes

## Depends On

- [[eos_ai-agent_runtime-py]]
- [[eos_ai-memory-py]]

## Contains

- **class** [[services-icp_scorer-py-RateLimiter]] — 2 methods
- **fn** [[services-icp_scorer-py-parse_frontmatter]]`(content)`
- **fn** [[services-icp_scorer-py-extract_comment_text]]`(body)`
- **fn** [[services-icp_scorer-py-get_processed_filenames]]`()`
- **fn** [[services-icp_scorer-py-lead_exists]]`(username)`
- **fn** [[services-icp_scorer-py-already_contacted]]`(username)`
- **fn** [[services-icp_scorer-py-in_pipeline]]`(username)`
- **fn** [[services-icp_scorer-py-load_outreach_messages]]`()`
- **fn** [[services-icp_scorer-py-_extract_openers]]`(outreach_text, archetype)`
- **fn** [[services-icp_scorer-py-pick_opener]]`(outreach_text, archetype, pain_signals, comment_text)`
- **fn** [[services-icp_scorer-py-score_comment]]`(runtime, comment_text, api_call_counter)`
- **fn** [[services-icp_scorer-py-update_opener_stats_sent]]`(opener_text)`
- **fn** [[services-icp_scorer-py-push_lead_to_notion]]`(username, score, archetype, pain_signals, channel) → bool`
- **fn** [[services-icp_scorer-py-create_lead_file]]`(username, comment_text, source, post_url, timestamp, result, opener, opener_index)`
- **fn** [[services-icp_scorer-py-add_to_kanban]]`(username, score, archetype, comment_text, lead_filename)`
- **fn** [[services-icp_scorer-py-main]]`()`

## Import Statements

```python
import os
import sys
import json
import time
import shutil
import datetime
import glob
from dotenv import load_dotenv
from eos_ai.agent_runtime import AgentRuntime
from eos_ai.memory import AgentMemory
```
