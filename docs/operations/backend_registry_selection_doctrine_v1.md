# Backend Registry & Selection — Doctrine v1
**Phase**: 96.3/96.4  
**Status**: ACTIVE  
**Date**: 2026-05-04
---

## Core Rule
Every extraction backend is registered with its category, implementation type, independence level, and capability profile. Selection prefers completeness, safety, and provenance over speed or convenience.

## Details
### 16 Backend Categories
1. API — official REST/GraphQL endpoints
2. CLI — command-line tool wrappers
3. SDK — language-native client libraries
4. MCP — Model Context Protocol servers
5. CU — Computer Use (screen-based automation)
6. RPA — robotic process automation scripts
7. BROWSER — browser automation (Playwright, Puppeteer)
8. WEBHOOK — inbound event receivers
9. EXTENSION — browser extension interfaces
10. SYNC — bidirectional sync adapters
11. EXPORT — bulk export utilities
12. SCRAPER — HTML/DOM extraction
13. FEED — RSS/Atom/structured feed readers
14. MANUAL — human-assisted fallback
15. BRIDGE — cross-environment relay (VPS ↔ local)
16. HYBRID — combines multiple categories

### 23 Implementation Types
- API: rest, graphql, grpc
- CLI: native, wrapper, pipe
- SDK: python, node, go
- MCP: stdio, http, sse
- CU: anthropic, openai, local
- BROWSER: playwright, puppeteer, selenium
- RPA: pyautogui, sikuli
- Other: webhook_inbound, extension_native, file_sync, bulk_export, dom_scraper, rss_reader

### 13 Selection Factors (Priority Order)
1. Extraction completeness (all fields populated)
2. Safety (no credential exposure to model context)
3. Source provenance (auditable chain)
4. Independence level (self-contained vs wrapper)
5. Auth simplicity (API key > OAuth > session)
6. Reliability (uptime, error rate)
7. Latency (acceptable, not optimized for)
8. Rate limits (headroom for batch operations)
9. Tab/section awareness (critical for multi-part docs)
10. Format fidelity (preserves structure, not just text)
11. Cost (API calls, proxy credits)
12. Maintenance burden (breaking changes, deprecation risk)
13. Environment requirements (VPS-only, local-only, either)

### Independence Levels
- **LEVEL_2** — fully independent, own auth, own extraction logic
- **LEVEL_1** — semi-independent, relies on shared infra but has own logic
- **LEVEL_0** — interface wrapper only, delegates to another backend (NOT an independent fallback)

## Constraints
- LEVEL_0 wrappers MUST NOT be counted as independent fallback options
- All backends MUST target the same CanonicalSourceRecord extraction contract
- Backend selection MUST be logged with rationale
- New backends MUST be registered before first use
- Category + implementation type combination must be unique per source system

## Phase 96.6 Terminology Note

`BackendCategory` semantically means **access path category**. The term "backend" is used throughout this document for backward compatibility. See `docs/operations/technical_terminology_glossary_v1.md` for precise definitions of all 10 terms previously conflated under "backend."

Key distinctions:
- **CLI** is an interface, not automatically an independent access path. A CLI that wraps the API (e.g., `gcloud`) is LEVEL_0.
- **OAuth** is an auth method, not an access path. It authorizes access through an access path but is not itself a mechanism for reaching data.
- **MCP** is a transport protocol. An MCP server that wraps an API is LEVEL_0, not an independent access path.

## References
- `docs/operations/mcp_backend_discovery_policy_v1.md` — MCP-specific discovery
- `docs/operations/google_workspace_backend_options_matrix_v1.md` — GWS backends
- `docs/operations/auth_layer_vs_backend_doctrine_v1.md` — auth separation
- `docs/operations/access_path_vs_backend_doctrine_v1.md` — terminology doctrine
- `docs/operations/technical_terminology_glossary_v1.md` — full glossary
