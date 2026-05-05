---
type: codebase-function
file: eos_ai/gws_scanner.py
line: 394
generated: 2026-04-12
---

# GWSDocumentScanner.ingest_to_eos

**File:** [[eos_ai-gws_scanner-py]] | **Line:** 394
**Signature:** `ingest_to_eos(documents) → int`

**Class:** [[eos_ai-gws_scanner-py-GWSDocumentScanner]]

Store document knowledge in EOS via KnowledgeIntegrator.
Large docs are split into 3000-char chunks.
Returns count of docs ingested.
