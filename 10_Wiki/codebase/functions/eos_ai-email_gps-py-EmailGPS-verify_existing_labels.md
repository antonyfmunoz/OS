---
type: codebase-function
file: eos_ai/email_gps.py
line: 1399
generated: 2026-05-07
---

# EmailGPS.verify_existing_labels

**File:** [[eos_ai-email_gps-py]] | **Line:** 1399
**Signature:** `verify_existing_labels(sample) → str`

**Class:** [[eos_ai-email_gps-py-EmailGPS]]

Sample emails from each GPS label already in Gmail.
Used for spot-checking DEX's historical classifications.
Triggered via !verify-inbox in Discord.

## Called By

- [[scripts-inbox_zero_init-py-verify_existing_labels]]
