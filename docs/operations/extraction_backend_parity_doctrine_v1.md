# Extraction Backend Parity Doctrine v1

**Phase**: 96.0
**Date**: 2026-05-04
**Status**: ACTIVE

---

## Core Doctrine

API, CLI, and Computer Use are execution backends.
They must all satisfy the same canonical extraction contract
or explicitly report capability gaps.

## The Seven Principles

### 1. Same Target Outcome
API, CLI, and Computer Use must all aim to produce the same canonical
source extraction result. No backend owns the definition of "complete."

### 2. Different Mechanisms Are Allowed
- API may use official structured endpoints.
- CLI may wrap official tools or command interfaces.
- Computer Use may use visible UI, accessibility tree, mouse/keyboard,
  clipboard, scrolling, and tab navigation if approved.

### 3. Same Output Schema
All backends must emit the same `DocumentSourceRecord` format with
`TabSourceRecord` entries and `ProvenanceRecord`. No backend-specific
schema drift.

### 4. Same Completeness Contract
A backend cannot claim success unless it meets ALL coverage requirements:
- All documents in scope
- All document tabs
- All child tabs (recursive)
- All pages/body content in each tab
- Empty tabs marked
- Inaccessible items marked with reason
- Provenance preserved

### 5. Parity Validation
Backends must be compared against each other:
- API vs CLI
- API vs Computer Use
- CLI vs Computer Use

### 6. Capability Gaps Are Not Failures If Honest
If a backend cannot yet capture all tabs/content, it must report:
`COMPUTER_USE_BACKEND_INCOMPLETE` — not "complete."
Honest reporting is correct behavior. Silent downgrade is a defect.

### 7. Production Preference Does Not Erase Parity Goal
API may remain the preferred production backend, but Computer Use
must still be hardened until it can perform equivalent extraction
as worst-case fallback.

## Status Hierarchy

```
COMPLETE    — all contract requirements met
PARTIAL     — some capabilities working, others not
BLOCKED     — specific known blocker preventing progress
FAILED      — attempted and failed
UNKNOWN     — not yet evaluated
```

## Implementation

- Contract definition: `eos_ai/substrate/extraction_backend_contracts.py`
- Output schema: `eos_ai/substrate/canonical_source_record.py`
- Parity measurement: `eos_ai/substrate/extraction_parity_comparator.py`
- Backend matrix: `eos_ai/substrate/google_docs_backend_parity_matrix.py`

## What This Replaces

The prior model treated:
- API as production-complete
- CLI as auth/connector support
- Computer Use as a partial fallback proof

This doctrine corrects that to:
- API as the currently-most-complete backend
- CLI as a backend that must wrap the same contract
- Computer Use as a backend that must be hardened to parity
