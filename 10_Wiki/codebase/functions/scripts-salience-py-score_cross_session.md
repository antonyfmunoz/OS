---
type: codebase-function
file: scripts/salience.py
line: 487
generated: 2026-04-12
---

# score_cross_session

**File:** [[scripts-salience-py]] | **Line:** 487
**Signature:** `score_cross_session(parsed, body_text, summaries_dir, exclude_session) → CrossSessionResult`

Score cross-session salience by detecting repeated themes.

Args:
    parsed: Current summary's extracted data (entities, topics, etc.)
    body_text: Full body text of current summary.
...

## Calls

- [[scripts-salience-py-_find_repeated]]
- [[scripts-salience-py-_has_signal]]
- [[scripts-salience-py-_load_recent_summaries]]
- [[scripts-salience-py-_normalize]]
