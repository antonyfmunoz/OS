---
type: codebase-function
file: services/apify_scraper.py
line: 485
generated: 2026-04-11
---

# transcribe_video

**File:** [[services-apify_scraper-py]] | **Line:** 485
**Signature:** `transcribe_video(video_url)`

Download audio and transcribe with Whisper. Returns transcript text or None.

## Calls

- [[eos_ai-agent_runtime-py-AgentRuntime-run]]
- [[services-apify_scraper-py-_get_whisper_model]]

## Called By

- [[services-apify_scraper-py-is_icp_relevant_post]]
