# W0-001 Backend Selection Recommendation

**Phase**: 96.3-96.5  
**Status**: ACTIVE  
**Date**: 2026-05-04

---

## Core Summary

For W0-001 production ingestion, the Google Docs API backend is the sole production-ready option. All other backends have documented blockers. API remains the reference implementation against which all alternatives are parity-tested.

## Backend Assessment Matrix

| Backend | Completion | Independence | Status | Recommendation |
|---------|-----------|-------------|--------|----------------|
| Google Docs API | COMPLETE | LEVEL_0 (SDK) | REFERENCE | Production use — selected |
| Computer Use (CU) | PARTIAL (~25%) | LEVEL_4 (visual) | IN_PROGRESS | First independent candidate — fix foreground requirement |
| CLI Wrapper | COMPLETE | LEVEL_0 (SDK) | COMPLETE | Same failure domain as API — not independent fallback |
| MCP | NOT STARTED | LEVEL_2-3 | PLANNED | Not yet implemented |
| Browser Automation | BLOCKED | LEVEL_3 | BLOCKED | Proxy/bot detection — not viable from VPS |

## Selection Rationale

### API (Selected)

- 100% tab coverage (321/321 tabs, 28 docs).
- Canonical record format validated.
- Deterministic output — same input always produces same extraction.
- Limitation: shares failure domain with CLI wrapper (both use Google SDK). If Google revokes API access, both fail simultaneously.

### CU (First Fallback Candidate)

- Truly independent — uses visual browser interaction, no SDK dependency.
- Currently at ~25% parity. Blocked by foreground browser requirement on VPS.
- When foreground fix lands, CU becomes the primary independent fallback.
- Parity testing protocol established: CU output compared word-by-word against API reference.

### CLI Wrapper (Not Independent)

- Technically complete — all docs extracted.
- LEVEL_0 independence: uses same Google SDK as API backend.
- Not a meaningful fallback. If API fails due to auth/SDK issues, CLI fails identically.
- Useful only for verifying API extraction consistency, not for resilience.

### MCP (Future)

- Not yet implemented for Google Docs.
- Independence level depends on which MCP server is used (could be LEVEL_2 or LEVEL_3).
- Priority: after CU foreground fix is resolved.

### Browser Automation (Blocked)

- VPS IP addresses trigger bot detection on Google services.
- Proxy (Apify residential) returns 403 when credits depleted.
- Not viable without residential proxy with sufficient credits or local execution.

## Next Actions

1. Fix CU foreground browser requirement — this unlocks the only independent fallback.
2. After CU fix, complete parity testing against API reference (remaining ~75%).
3. Evaluate MCP backend options once CU parity is established.

## References

- `eos_ai/backend_selection.py` — selection engine
- `eos_ai/backend_registry.py` — backend type registry
- `docs/operations/extraction_backend_parity_doctrine_v1.md`
- `docs/system/w0_001_backend_parity_status_after_reextraction.md`
- `docs/system/phase951_w0_001_cu_final_comparison_report.md`
