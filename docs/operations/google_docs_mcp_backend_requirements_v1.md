# Google Docs MCP Backend Requirements v1

**Phase**: 96.2
**Date**: 2026-05-04
**Status**: ACTIVE

---

## Purpose

For an MCP Google Docs backend to claim COMPLETE, it must satisfy
every requirement in this document. No exceptions. No partial claims.

## The 12 Requirements

### 1. Inventory all docs in scope
The MCP tool must be able to list all documents in the configured
scope (Drive folder, shared drives, specific file IDs).

### 2. Retrieve all top-level tabs
Every top-level tab in each document must be discovered and retrieved.

### 3. Retrieve all child tabs recursively
Child tabs (nested under top-level tabs) must be traversed recursively.
No tab depth limit.

### 4. Retrieve body content for every tab
The full text/body content of every tab must be extracted.
This is the primary extraction target.

### 5. Preserve per-document provenance
Each document must record: backend type, extraction method,
source observed from, content origin flags.

### 6. Preserve per-tab provenance
Each tab must record its extraction status, whether it was
empty, and any extraction notes.

### 7. Mark empty tabs
Tabs with no content must be explicitly marked as `is_empty=True`
with `word_count=0`.

### 8. Mark inaccessible content with reason
Any content that cannot be extracted must be marked with:
- `ExtractionCoverageStatus.BLOCKED` or `FAILED`
- An `ExtractionFailureReason` explaining why
- Human-readable notes

### 9. Emit CanonicalSourceRecord schema
Output must conform to `DocumentSourceRecord` with `TabSourceRecord`
entries and `ProvenanceRecord`. No custom schemas.

### 10. Pass parity comparator against reference extraction
The MCP extraction must pass the parity comparator when compared
against the reference API extraction:
- Tab discovery recall >= 100%
- Word recall >= 95% (MVP) / 99% (production)
- No false positive content

### 11. Avoid credential/token/cookie exposure
The MCP tool must NOT capture, store, log, or transmit:
- OAuth tokens
- API keys
- Session cookies
- Browser credentials
- Any authentication material

### 12. Avoid hidden scope expansion
The MCP tool must NOT:
- Open Gmail or unrelated Google services
- Switch Google accounts
- Access documents outside the configured scope
- Download/export documents unless explicitly approved

## API-Based MCP Requirements

If the MCP tool uses Google APIs:
- MUST use `includeTabsContent=true` or equivalent parameter
- MUST prove tab traversal works (not just document body)
- MUST NOT be labeled as "independent from Google API availability"
  because it shares the same API dependency

## Computer Use MCP Requirements

If the MCP tool uses Computer Use (desktop/accessibility/keyboard):
- MUST satisfy the Computer Use document reader requirements
  (see `computer_use_full_document_reader_requirements_v1.md`)
- MUST NOT use API/CLI/CDP/Playwright unless classified as hybrid
- MUST declare its foreground ownership approach

## Blocked Actions

Any MCP Google Docs backend must NOT:
- Edit documents
- Delete documents
- Share documents
- Download documents (unless approved as local-file backend)
- Switch accounts
- Open Gmail
- Capture credentials
- Store screenshots

## Implementation

Requirements enforced via:
- Contract: `eos_ai/substrate/extraction_backend_contracts.py`
- Classifier: `eos_ai/substrate/mcp_backend_classifier.py`
- Evaluator: `evaluate_mcp_against_extraction_contract()`
