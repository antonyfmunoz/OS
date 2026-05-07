---
type: codebase-function
file: eos_ai/gws_scanner.py
line: 197
generated: 2026-05-07
---

# GWSDocumentScanner.understand_doc

**File:** [[eos_ai-gws_scanner-py]] | **Line:** 197
**Signature:** `understand_doc(name, content) → dict`

**Class:** [[eos_ai-gws_scanner-py-GWSDocumentScanner]]

Use Claude Haiku to understand every document properly.
Falls back to keyword scoring if AI call fails.

## Calls

- [[eos_ai-gws_scanner-py-GWSDocumentScanner-_keyword_assess]]

## Called By

- [[eos_ai-gws_scanner-py-GWSDocumentScanner-scan_all]]
