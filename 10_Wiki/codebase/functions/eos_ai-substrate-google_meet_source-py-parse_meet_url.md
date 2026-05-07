---
type: codebase-function
file: eos_ai/substrate/google_meet_source.py
line: 79
generated: 2026-05-07
---

# parse_meet_url

**File:** [[eos_ai-substrate-google_meet_source-py]] | **Line:** 79
**Signature:** `parse_meet_url(url_or_code) → Optional[str]`

Extract a Google Meet meeting code from a URL or raw code.

Returns the lowercase ``abc-defg-hij`` code, or ``None`` if no plausible
code can be found. Never raises.

...

## Called By

- [[eos_ai-substrate-google_meet_source-py-GoogleMeetSource-__init__]]
- [[scripts-substrate_google_meet_smoke_test-py-main]]
