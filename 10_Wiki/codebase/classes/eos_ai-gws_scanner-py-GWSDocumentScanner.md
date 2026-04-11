---
type: codebase-class
file: eos_ai/gws_scanner.py
line: 50
generated: 2026-04-11
---

# GWSDocumentScanner

**File:** [[eos_ai-gws_scanner-py]] | **Line:** 50

Scans all Google Docs owned by the founder.
Uses AI to understand every document. Deduplicates against Neon.
Ingests with chunking. Saves context summary for cognitive loop.

## Methods

- [[eos_ai-gws_scanner-py-GWSDocumentScanner-__init__]]`(ctx)` — 
- [[eos_ai-gws_scanner-py-GWSDocumentScanner-_run]]`() → dict | list | None` — Run a gws CLI command and return parsed JSON, or None on error.
- [[eos_ai-gws_scanner-py-GWSDocumentScanner-list_all_docs]]`(limit) → list[dict]` — List all Google Docs in Drive.
- [[eos_ai-gws_scanner-py-GWSDocumentScanner-read_doc]]`(doc_id) → str` — Read plain-text content of a Google Doc.
- [[eos_ai-gws_scanner-py-GWSDocumentScanner-get_already_ingested]]`() → dict` — Returns doc_id → modified_time for docs already in Neon.
- [[eos_ai-gws_scanner-py-GWSDocumentScanner-is_new_or_modified]]`(doc_id, modified_time, already_ingested) → bool` — 
- [[eos_ai-gws_scanner-py-GWSDocumentScanner-understand_doc]]`(name, content) → dict` — Use Claude Haiku to understand every document properly.
- [[eos_ai-gws_scanner-py-GWSDocumentScanner-_keyword_assess]]`(name, content) → dict` — Keyword-based fallback when AI is unavailable.
- [[eos_ai-gws_scanner-py-GWSDocumentScanner-scan_all]]`(limit, incremental) → list[GWSDocument]` — Scan all Google Docs. Every doc is read and AI-assessed.
- [[eos_ai-gws_scanner-py-GWSDocumentScanner-ingest_to_eos]]`(documents) → int` — Store document knowledge in EOS via KnowledgeIntegrator.
- [[eos_ai-gws_scanner-py-GWSDocumentScanner-_complete_if_truncated]]`(text, rt, context) → str` — Request continuation if text ends mid-sentence.
- [[eos_ai-gws_scanner-py-GWSDocumentScanner-generate_founder_profile]]`(documents) → str` — Generate a four-section profile of what EOS learned from all docs.
- [[eos_ai-gws_scanner-py-GWSDocumentScanner-save_context_summary]]`(documents) → None` — Save a markdown summary of all scanned docs.
