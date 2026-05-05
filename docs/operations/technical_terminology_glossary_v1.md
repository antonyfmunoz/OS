# Technical Terminology Glossary — v1

**Phase**: 96.6
**Status**: ACTIVE
**Date**: 2026-05-05

---

## Purpose

Phase 96.6 corrected overloaded terminology. "Backend" conflated 10 distinct concepts.
This glossary defines each precisely. All EOS/UMH documentation uses these terms.

## Definitions

### 1. Interface
Where the operator or agent communicates with the system.
Examples: CLI, Discord, Telegram, web dashboard, voice interface, mobile app.
An interface is NOT an access path. Discord is where you talk to EOS, not how EOS reaches Google Docs.

### 2. Auth Method / Credential Mechanism
How access to an external system is authorized.
Examples: OAuth2, API key, service account, browser profile, SSH key.
Auth is NOT an access path. OAuth authorizes access — it does not define the transport or protocol used to reach data.

### 3. Adapter / Connector
Software bridge that translates an external system's API, protocol, or interface into UMH contracts.
An adapter wraps transport, auth, capability mapping, mastery, governance, execution, tests, and registry into a single operational package. See Adapter Package.

### 4. Access Path
The mechanism used to reach data or trigger actions on an external system.
Examples: REST API, SDK call, CLI direct invocation, MCP server, Computer Use, browser automation, webhook, file sync.
This is the precise replacement for the overloaded term "backend" when referring to how data is reached.
CLI is often an interface, not automatically an independent access path. MCP is not automatically independent.

### 5. Execution Environment
Where work physically runs.
Examples: VPS, Docker container, tmux session, WSL, browser profile, Python venv, local workstation.

### 6. Capability
What needs to be done, independent of which tool or access path does it.
Examples: source inventory, document extraction, tab-aware extraction, credential refresh.
Capabilities are tool-agnostic. Multiple access paths may fulfill the same capability.

### 7. Tool Mastery Pack
Expert operational knowledge about a specific tool: best practices, anti-patterns, traps, failure modes, validation checklists, completeness requirements.
A mastery pack that lacks completeness_requirements, failure_modes, anti_patterns, or validation_checklist is operationally incomplete. See tool_mastery_pack_doctrine_v1.md.

### 8. Adapter Package
The complete 8-layer operational bundle for an external capability.
Layers: Access Adapter, Auth Adapter, Capability Map, Tool Mastery Pack, Governance Policy, Execution Wrapper, Tests/Validation, Registry Entry.
See adapter_package_doctrine_v1.md.

### 9. Worker Runtime
The execution layer that runs work through a selected adapter package, applying governance constraints and mastery guidance during execution.

### 10. Selection Engine
Chooses the best adapter package and access path for a given capability request.
Selection factors: completeness, safety, provenance, independence, auth simplicity, reliability, latency, rate limits, tab awareness, format fidelity, cost, maintenance burden, environment requirements.

## Hard Rules

- Never use "backend" when you mean interface, auth method, adapter, or execution environment.
- BackendCategory enum is retained for backward compatibility — it semantically means "access path category."
- When writing new documentation, use the precise term from this glossary.

## References

- `docs/operations/access_path_vs_backend_doctrine_v1.md` — migration doctrine
- `docs/operations/adapter_package_doctrine_v1.md` — 8-layer bundle
- `docs/operations/tool_mastery_pack_doctrine_v1.md` — mastery requirements
- `eos_ai/adapter_engine_contracts.py` — enums and dataclasses
