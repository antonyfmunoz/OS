# MCP Tool Independence Levels v1

**Phase**: 96.2
**Date**: 2026-05-04
**Status**: ACTIVE

---

## Purpose

This document defines how to measure the independence value of any
extraction backend (not just MCP). Independence determines whether
a backend serves as a genuine fallback or merely a different interface
to the same underlying system.

## Independence Level Definitions

### LEVEL_0 — Interface Wrapper
- Wraps the same internal extractor/implementation
- Different protocol surface, same code underneath
- Does NOT count as independent fallback
- If the underlying system fails, this backend also fails
- Examples: MCP proxy to internal API extractor, CLI shell around same Python module

### LEVEL_1 — Different Implementation, Same Provider API
- Different code/implementation from the existing backend
- Still calls the same provider API (e.g., Google Docs API)
- Proves implementation diversity (different bugs, different edge cases)
- Does NOT survive provider API outages
- Examples: MCP server calling Google API directly, alternative CLI tool using same API

### LEVEL_2 — Different Toolchain, Same Provider API
- Uses a completely different toolchain (vendor CLI, native tool)
- May still depend on the same provider API underneath
- Proves toolchain diversity
- Examples: GAM CLI, rclone, gsutil — different tools, possibly same API

### LEVEL_3 — Different Data Access Channel
- Reads data through a fundamentally different channel
- Does not depend on the provider API being available
- Survives API outages
- Examples: Local file sync, exported archives, Google Takeout, cached data

### LEVEL_4 — Different Modality
- Uses a completely different modality (visible UI, accessibility tree, mouse/keyboard)
- Most independent — survives API outages, SDK changes, auth revocations
- May have its own unique blockers (e.g., foreground ownership)
- Examples: Computer Use via desktop GUI, screen reader extraction

### LEVEL_5 — Human Assisted
- Manual human fallback
- Always independent
- Not scalable
- Last resort
- Examples: Human opening document and copy-pasting content

## Independence Matrix

| Level | API Independence | Toolchain Independence | Data Channel Independence | Modality Independence |
|-------|:---:|:---:|:---:|:---:|
| LEVEL_0 | NO | NO | NO | NO |
| LEVEL_1 | NO | PARTIAL | NO | NO |
| LEVEL_2 | NO | YES | NO | NO |
| LEVEL_3 | YES | YES | YES | NO |
| LEVEL_4 | YES | YES | YES | YES |
| LEVEL_5 | YES | YES | YES | YES |

## Rules

1. LEVEL_0 backends NEVER count as independent fallback
2. LEVEL_1+ backends count as independent but may share failure domains
3. True API-outage resilience requires LEVEL_3+
4. The highest-independence backend should be prioritized for hardening
5. All backends must still satisfy the same extraction contract

## Implementation

Enum: `BackendIndependenceLevel` in `eos_ai/substrate/extraction_backend_contracts.py`
Classifier: `eos_ai/substrate/mcp_backend_classifier.py`
