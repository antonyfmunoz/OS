---
type: codebase-function
file: eos_ai/substrate/google_meet_source.py
line: 320
generated: 2026-04-12
---

# GoogleMeetSource.bridge_path

**File:** [[eos_ai-substrate-google_meet_source-py]] | **Line:** 320
**Signature:** `bridge_path() → Optional[Any]`

**Class:** [[eos_ai-substrate-google_meet_source-py-GoogleMeetSource]]

Best-effort: returns the bridge JSONL path if this source is bridge-backed.

Returns None if the source was not built from a bridge or if the
meeting_code is unknown. Used by reporting surfaces to expose
backlog/last-ingress info.
