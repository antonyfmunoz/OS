---
type: codebase-function
file: eos_ai/gws_scanner.py
line: 288
generated: 2026-04-12
---

# GWSDocumentScanner.scan_all

**File:** [[eos_ai-gws_scanner-py]] | **Line:** 288
**Signature:** `scan_all(limit, incremental) → list[GWSDocument]`

**Class:** [[eos_ai-gws_scanner-py-GWSDocumentScanner]]

Scan all Google Docs. Every doc is read and AI-assessed.
incremental=True skips docs already in Neon that haven't changed.

## Calls

- [[eos_ai-gws_scanner-py-GWSDocumentScanner-get_already_ingested]]
- [[eos_ai-gws_scanner-py-GWSDocumentScanner-is_new_or_modified]]
- [[eos_ai-gws_scanner-py-GWSDocumentScanner-list_all_docs]]
- [[eos_ai-gws_scanner-py-GWSDocumentScanner-read_doc]]
- [[eos_ai-gws_scanner-py-GWSDocumentScanner-understand_doc]]
