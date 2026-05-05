# Access Path vs Backend — Terminology Doctrine v1

**Phase**: 96.6
**Status**: ACTIVE
**Date**: 2026-05-05

---

## Core Rule

"Backend" was overloaded. It conflated 10 distinct concepts: interface, auth method, adapter, access path, execution environment, capability, Tool Mastery Pack, Adapter Package, registry, and worker runtime. Phase 96.6 introduces precise terminology. The word "backend" is not banned — but its meaning must be explicit or replaced with the correct term.

## The Precise Term: Access Path

When previous documentation said "backend" to mean "how data is reached," the correct term is **access path**.

An access path is the mechanism used to reach data or trigger actions on an external system: REST API, SDK, CLI direct invocation, MCP server, Computer Use, browser automation, webhook, file sync, etc.

## BackendCategory Enum — Backward Compatibility

The `BackendCategory` enum in `adapter_engine_contracts.py` is retained for backward compatibility. Its 16 values (API, CLI, SDK, MCP, CU, RPA, BROWSER, WEBHOOK, EXTENSION, SYNC, EXPORT, SCRAPER, FEED, MANUAL, BRIDGE, HYBRID) semantically represent **access path categories**, not "backends" in any other sense.

New code should treat `BackendCategory` as `AccessPathCategory` in concept. A future refactor may rename the enum — the semantic correction is immediate, the code rename is deferred.

## Common Misclassifications

### CLI is often an interface, not an access path
A CLI tool like `gcloud` is an interface that wraps the API. It is LEVEL_0 — not an independent access path. Only CLI tools that implement their own extraction logic (not wrapping an API) qualify as independent access paths.

### MCP is not automatically independent
An MCP server that wraps the Google Docs API is LEVEL_0 — it adds MCP transport but delegates extraction to the API. It is not an independent fallback.

### OAuth is auth, not an access path
OAuth2 is a credential mechanism. It authorizes access through an access path (API, SDK, etc.) but is not itself a path to data.

### Discord is an interface, not an access path
Discord is where an operator communicates with EOS. It has nothing to do with how EOS reaches Google Docs.

## Migration Guidance

- Existing docs that say "backend" in the selection/registry sense: add a terminology note referencing this doctrine. Do not mass-rename existing docs.
- New docs: use "access path" when describing how data is reached.
- Code: `BackendCategory` remains. Comments and docstrings should clarify "access path category."
- Conversation: prefer "access path" over "backend" unless context is unambiguous.

## Hard Rules

- Never introduce a new "backend" that is actually an auth method, interface, or execution environment.
- Never count a LEVEL_0 wrapper as an independent access path.
- Never treat MCP transport as automatic independence — evaluate the underlying implementation.

## References

- `docs/operations/technical_terminology_glossary_v1.md` — full 10-term glossary
- `docs/operations/backend_registry_selection_doctrine_v1.md` — selection factors (uses "backend" for compat)
- `eos_ai/adapter_engine_contracts.py` — BackendCategory enum
