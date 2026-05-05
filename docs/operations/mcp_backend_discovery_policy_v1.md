# MCP Backend Discovery — Policy v1
**Phase**: 96.3/96.4  
**Status**: ACTIVE  
**Date**: 2026-05-04
---

## Core Rule
MCP servers are evaluated as potential backends through a structured 10-step discovery process. Classification determines independence level. Interface wrappers are not independent fallbacks. Browser automation via MCP is blocked unless explicitly approved.

## Details
### 10-Step Discovery Process
1. **Identify** — locate MCP server (npm registry, GitHub, MCP directories)
2. **Classify** — assign candidate subtype (see below)
3. **Enumerate tools** — list all exposed tools with parameters
4. **Map to contract** — which CanonicalSourceRecord fields can this server populate?
5. **Auth assessment** — what auth method does it require? Does it handle tokens itself?
6. **Independence check** — does it have its own extraction logic or wrap another tool?
7. **Tab awareness** — for document sources, does it handle multi-tab/multi-section content?
8. **Parity test** — compare output against reference backend (API COMPLETE)
9. **Failure modes** — document error handling, rate limits, timeout behavior
10. **Register** — add to backend registry with full metadata

### 7 Evaluation Criteria
1. Field coverage against CanonicalSourceRecord
2. Independence level (LEVEL_0 / LEVEL_1 / LEVEL_2)
3. Auth complexity and secret handling
4. Error reporting quality
5. Rate limit behavior
6. Multi-document batch support
7. Active maintenance status

### 5 Candidate Subtypes
1. **API_WRAPPER** — wraps an official API (LEVEL_0 if no added logic)
2. **CLI_WRAPPER** — wraps a CLI tool (LEVEL_0 if passthrough)
3. **NATIVE_MCP** — purpose-built MCP server with own logic (LEVEL_1 or LEVEL_2)
4. **BROWSER_BRIDGE** — drives browser automation through MCP (requires approval)
5. **HYBRID_MCP** — combines multiple data sources or methods (assess each path)

### Classification Rules
- API_WRAPPER and CLI_WRAPPER default to LEVEL_0 unless they add material extraction logic
- NATIVE_MCP defaults to LEVEL_1; promoted to LEVEL_2 only if fully self-contained
- BROWSER_BRIDGE is BLOCKED by default — requires explicit founder approval per use case
- HYBRID_MCP: each internal path assessed independently

### Tab-Aware Requirement
- For Google Docs and similar multi-section sources, MCP backend MUST support tab enumeration
- Single-tab-only extraction is a coverage gap, not a passing grade
- Tab-unaware backends receive a coverage penalty in selection scoring

## Constraints
- Interface-only wrappers (LEVEL_0) MUST NOT be listed as independent fallback options
- Browser automation MCP servers MUST NOT be used without explicit approval
- MCP servers MUST NOT handle or store credentials themselves — auth layer owns this
- Discovery results MUST be documented before the backend is used in production
- Unregistered MCP servers MUST NOT be invoked for extraction work orders

## References
- `docs/operations/backend_registry_selection_doctrine_v1.md` — registry structure
- `docs/operations/mcp_backend_classification_doctrine_v1.md` — classification details
- `docs/operations/mcp_tool_independence_levels_v1.md` — independence levels
- `docs/operations/google_docs_mcp_backend_requirements_v1.md` — GDocs MCP specifics
