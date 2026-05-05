# W0-001 Backend Parity Status Review

**Date**: 2026-05-04
**Phase**: Post-96.2 Gate Review
**Reviewer**: Developer Agent
**Status**: REVIEW COMPLETE

---

## Executive Summary

W0-001 Google Docs corpus extraction has one COMPLETE backend (API) producing
28 documents / 321 tabs / 283,831 words with zero errors. CLI is COMPLETE but
is an interface wrapper (LEVEL_0) sharing the same failure domain. MCP is
classified but not implemented. Computer Use is PARTIAL with foreground
ownership blocking all content extraction. No independent fallback backend
has reached COMPLETE.

Memory promotion is conditionally allowed: the API extraction is validated,
complete, and the corpus is ready for founder review. CU hardening is a
separate track and should not block memory promotion review.

---

## 1. Current API Status

| Metric | Value |
|--------|-------|
| Overall | **COMPLETE** |
| Method | Google Docs API with `includeTabsContent=true` via `gws` CLI |
| Documents extracted | 28/28 |
| Tabs traversed | 321/321 |
| Child tabs traversed | 134/134 |
| Empty tabs marked | 72 |
| Total words | 283,831 |
| Prior extraction (first-tab-only) | 22,431 words (7.9% coverage) |
| Coverage correction | 7.9% → 100% |
| Errors | 0 |
| Canonical records produced | 28 (in `data/canonical_source_records/w0_001/`) |
| Tab-aware raw data | 29 files in `data/drive_doc_ingestion_tab_aware/` |
| Source graph rebuilt | YES |
| Contradiction register rebuilt | YES |
| Redundancy register rebuilt | YES |

**Verdict**: API extraction is validated and complete. The 283,831-word
tab-aware corpus supersedes all prior first-tab-only artifacts.

---

## 2. Current CLI Status

### CLI wrapper (wraps API)
| Metric | Value |
|--------|-------|
| Overall | **COMPLETE** (as interface) |
| Independence | **LEVEL_0** — same code, same API, same failure domain |
| Method | `gws docs documents get` with `includeTabsContent=true` |
| Parity with API | 100% (CLI IS the API tool used for extraction) |
| Counts as independent fallback | **NO** |

### CLI direct protocol
| Metric | Value |
|--------|-------|
| Overall | **NOT IMPLEMENTED** |
| Independence | Would be LEVEL_1 if implemented |
| What it would be | Standalone CLI calling `documents.get` directly (not via gws) |
| Notes | No standalone implementation exists |

### CLI vendor/native tool
| Metric | Value |
|--------|-------|
| Overall | **UNKNOWN** |
| Independence | Would be LEVEL_2 if available |
| What it would be | GAM, rclone, or similar vendor tool |
| Notes | No tool evaluated for Google Docs all-tabs support |

### CLI local export
| Metric | Value |
|--------|-------|
| Overall | **NOT APPROVED** |
| Independence | Would be LEVEL_3 |
| Notes | Would require export/download policy approval |

---

## 3. Current MCP Status

| MCP Subtype | Independence | Status | Notes |
|-------------|:------------|:------:|-------|
| MCP wrapper (around API extractor) | LEVEL_0 | NOT IMPLEMENTED | Would not be independent |
| MCP API connector | LEVEL_1 | NOT IMPLEMENTED | Must prove tab-aware + canonical records |
| MCP vendor/tool wrapper | LEVEL_2 | UNKNOWN | No tool evaluated |
| MCP local file/export connector | LEVEL_3 | NOT APPROVED | Requires local-file policy |
| MCP computer-use controller | LEVEL_4 | MAPS TO CU | Same as CU backend below |
| MCP browser automation | varies | BLOCKED | Not approved unless separately approved |

**Verdict**: MCP classification doctrine is encoded (Phase 96.2) but no MCP
tools are currently deployed for Google Docs extraction. This is expected —
MCP becomes relevant when a tool exists to evaluate.

---

## 4. Current Computer Use Status

### What is proven
| Capability | Status | Evidence |
|-----------|:------:|---------|
| Drive file inventory | **COMPLETE** | 100% recall vs API file list |
| Document tab detection | **COMPLETE** | 8/8 tabs detected on UMH via accessibility tree |
| Document title detection | **COMPLETE** | WindowTitle and accessibility tree match |
| Accessibility tree reading | **COMPLETE** | TreeItem enumeration working |
| Provenance capture | **COMPLETE** | Backend type recorded correctly |

### What is blocked
| Capability | Status | Blocker |
|-----------|:------:|---------|
| Tab navigation | **BLOCKED** | Foreground ownership — InvokePattern/click fails |
| Body text extraction | **BLOCKED** | Foreground + canvas rendering — clipboard fails |
| Scrolling (PgDn/wheel) | **BLOCKED** | Foreground ownership — SendKeys not delivered |
| Clipboard capture (Ctrl+A/C) | **BLOCKED** | Foreground ownership — wrong window receives input |
| Canonical record production | **BLOCKED** | All content capabilities blocked |

### Remaining gap to 100%
| Phase | Description | Status | Blocks |
|-------|-------------|:------:|--------|
| A | Fix foreground ownership | NOT STARTED | Everything else |
| B | Clipboard content extraction | NOT STARTED | Full text capture |
| C | Tab navigation | NOT STARTED | Multi-tab extraction |
| D | Scroll-and-read | NOT STARTED | Long doc capture |
| E | Parity validation (95%+ word recall) | NOT STARTED | Backend graduation |

**Root cause**: Windows does not allow a non-foreground process to steal
foreground. Task Scheduler `/IT` is NOT the foreground owner. Chrome retains
foreground. Recommended fix: Option A1 — launch Chrome from the same
scheduled task process (zero install, restructure only).

**Estimated effort**: 2-3 sessions for all 5 phases.

**Current parity with API**: ~25% (metadata + tab detection only, no content).

---

## 5. What Is Complete

- [x] API tab-aware extraction: 28/28 docs, 321 tabs, 283,831 words, 0 errors
- [x] Canonical source records produced and indexed
- [x] Source graph rebuilt from tab-aware data
- [x] Contradiction register rebuilt
- [x] Redundancy register rebuilt
- [x] Prior first-tab-only artifacts officially superseded
- [x] CLI wrapper confirmed 100% parity (same tool)
- [x] CU Drive inventory confirmed 100% recall
- [x] CU tab detection confirmed 8/8
- [x] Backend parity contracts defined (Phase 96.0)
- [x] MCP classification doctrine encoded (Phase 96.2)
- [x] Independence level framework defined (LEVEL_0 through LEVEL_5)
- [x] 75 backend parity tests passing

## 6. What Remains Partial

- [ ] CU document reader: detection proven, content extraction blocked
- [ ] CU parity: ~25% (no body text, no tab navigation)

## 7. What Is Blocked

- [ ] CU foreground ownership (blocks all CU content extraction)
- [ ] Browser automation backend (policy-blocked)
- [ ] Local export/file backend (not approved)
- [ ] MCP backends (none implemented)

---

## 8. Memory Promotion Decision

**Memory promotion is CONDITIONALLY ALLOWED.**

Rationale:
1. API extraction is validated and complete (283,831 words, 321 tabs, 0 errors)
2. The tab-aware corpus is 12.65x larger than the prior first-tab-only extraction
3. Source graph, contradiction register, and redundancy register are rebuilt
4. The API is the production backend — it is the source of truth
5. CU hardening is Track B — it should not block Track A memory promotion
6. The prior Phase 96.0 parity status doc explicitly recommended
   `READY_FOR_MEMORY_PROMOTION_REVIEW_AFTER_TAB_AWARE_REEXTRACTION`

Condition: Founder must review the tab-aware outputs before promotion proceeds.
No automated memory promotion without founder sign-off.

CU backend independence (LEVEL_4) remains valuable as a worst-case fallback
but is not a prerequisite for promoting API-extracted content.

---

## 9. Recommended Next Gate

**READY_FOR_MEMORY_PROMOTION_REVIEW_AFTER_TAB_AWARE_REEXTRACTION**

This gate means:
1. Tab-aware corpus (283K words, 321 tabs) is accepted as source of truth
2. Founder reviews what should be promoted to system memory
3. CU hardening proceeds as a separate Track B (not blocking)
4. Prior first-tab-only artifacts are officially superseded and will not be used

### Why not the other gates?
| Gate | Why Not |
|------|---------|
| HARDEN_CU_DOCUMENT_READER_TO_100_PERCENT | Track B — shouldn't block memory promotion |
| APPROVE_CLI_DIRECT_PROTOCOL_BACKEND | Low value — CLI wrapper already works |
| APPROVE_MCP_BACKEND_DISCOVERY | No MCP tools exist to discover yet |
| APPROVE_WORD_DOC_EXPORT | Not in scope for W0-001 |
| PAUSE_INGESTION | No reason to pause — API extraction is complete |

### Next exact action

Founder reviews the tab-aware extraction outputs in
`data/canonical_source_records/w0_001/` and approves which documents/sections
should be promoted to system memory. The review determines what knowledge
becomes part of the permanent operating context.

---

## Appendix: Backend Matrix Summary (13 rows)

| # | Backend | Independence | Status |
|---|---------|:------------|:------:|
| 1 | API tab-aware extractor | Reference | **COMPLETE** |
| 2 | CLI wrapper (wraps API) | LEVEL_0 | COMPLETE (interface) |
| 3 | CLI direct protocol | LEVEL_1 | NOT IMPLEMENTED |
| 4 | CLI vendor/native tool | LEVEL_2 | UNKNOWN |
| 5 | MCP wrapper | LEVEL_0 | NOT IMPLEMENTED |
| 6 | MCP API connector | LEVEL_1 | NOT IMPLEMENTED |
| 7 | MCP vendor/tool wrapper | LEVEL_2 | UNKNOWN |
| 8 | MCP local file connector | LEVEL_3 | NOT APPROVED |
| 9 | MCP computer-use controller | LEVEL_4 | MAPS TO CU |
| 10 | Computer Use (native GUI) | LEVEL_4 | PARTIAL |
| 11 | Browser automation | varies | BLOCKED |
| 12 | Local export/file parser | LEVEL_3 | NOT APPROVED |
| 13 | Manual/human fallback | LEVEL_5 | AVAILABLE |
