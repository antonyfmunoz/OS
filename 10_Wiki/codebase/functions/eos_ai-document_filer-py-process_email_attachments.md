---
type: codebase-function
file: eos_ai/document_filer.py
line: 115
generated: 2026-05-07
---

# process_email_attachments

**File:** [[eos_ai-document_filer-py]] | **Line:** 115
**Signature:** `process_email_attachments(subject, sender, attachment_names, ctx) → list[dict]`

Process attachments from an email.
Classifies each, logs to Neon, returns results.

## Calls

- [[eos_ai-document_filer-py-classify_document]]
- [[eos_ai-document_filer-py-log_document]]
