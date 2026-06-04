# UMH Codebase Quarantine and Rewrite Candidates

**Phase:** 14.6B-UMH (revised 14.6F)
**Status:** DRAFT

Revised in Phase 14.6F to align with 18 ratified P0 decisions (2026-06-04).

## Quarantine

### substrate/execution/workers/workstation/

- **Size**: 26,671 lines across 43 files
- **Status**: Dead code per exhaustive codebase audit
- **Evidence**: No imports from any live module reference this directory
- **Action**: RESOLVED per DEC-146B-UMH-004 (ratified 2026-06-04): Extract conceptual value into design docs, then delete dead workstation code. Not yet implemented.
- **Risk**: LOW -- audit confirmed no callers

## Rewrite Candidates

### 1. ProductConnectionManager

- **Location**: `substrate/integrations/product_connections.py`
- **Issue**: Architecture violation -- substrate imports from projection-specific modules
- **Impact**: Violates the architecture layer law (substrate must not reach upward)
- **Fix**: RESOLVED per DEC-146B-UMH-005 (ratified 2026-06-04): Abstract port pattern via `substrate/sockets/projection_port.py`. Projections register via abstract port; manager queries port registry only. Not yet implemented.

### 2. PHILOSOPHY.md

- **Location**: `/opt/OS/PHILOSOPHY.md`
- **Issue**: Contains EOS-specific naming that should be projection-agnostic
- **Impact**: Violates projection boundary law for documentation
- **Fix**: Rewrite to use UMH/substrate terminology; EOS references move to projections/

### 3. cognitive_loop.py _dept_map

- **Location**: `substrate/control_plane/runtime/cognitive_loop.py`
- **Issue**: `_dept_map` contains hardcoded EOS agent names (CEO, CMO, etc.)
- **Impact**: Violates projection boundary law -- substrate contains EOS-specific agent mapping
- **Fix**: Agent mapping should come from projection manifest or runtime registration, not hardcoded in substrate

### 4. gateway.py broken import

- **Location**: `substrate/control_plane/runtime/gateway.py`
- **Issue**: Broken import referencing `observability.status.status`
- **Impact**: Import fails at runtime; module path does not exist
- **Fix**: Update to correct import path per post-convergence module structure
