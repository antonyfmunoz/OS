---
type: codebase-function
file: eos_ai/gws_scanner.py
line: 100
generated: 2026-04-12
---

# GWSDocumentScanner.read_doc

**File:** [[eos_ai-gws_scanner-py]] | **Line:** 100
**Signature:** `read_doc(doc_id) → str`

**Class:** [[eos_ai-gws_scanner-py-GWSDocumentScanner]]

Read plain-text content of a Google Doc.

The gws CLI export command saves to a file and returns JSON metadata
with the saved_file path. We read that file then clean up.

## Called By

- [[eos_ai-gws_scanner-py-GWSDocumentScanner-scan_all]]
