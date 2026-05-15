# Runtime Namespace Execution Plan — R8

> Phase: 96.8CQ — 2026-05-10
> Supersedes: R7 recommendation of `umh_runtime/`
> Target namespace: `runtime/`
> Type: Execution plan — no code changes in this commit
> Revision: R8v2 — incorporates architectural tightening

---

## Decision Record

**R7 recommended:** `umh_runtime/`
**R8 decision:** `runtime/`

**Rationale:**
- Repo root will become `/opt/UMH`, so `runtime/` is already UMH-scoped
- Simpler import path: `from runtime.db import get_conn`
- Cleaner long-term architecture: `core/` + `runtime/` + `services/`
- Avoids redundant `umh_runtime` naming inside a UMH repo

**Architectural stance:** This is topology surgery, not cosmetic refactoring.
The migration produces one runtime with many temporary namespace entrypoints —
never two parallel mutable implementations.

---

## 1. Collision Risk Analysis

### 1.1 Three Existing `runtime` Entities

| Entity | Type | Files | Python Package? | Status |
|--------|------|-------|-----------------|--------|
| `runtime/` (top-level) | Docker/deployment config | 14 | NO (no `__init__.py`) | Alternative compose, not actively used |
| `eos_ai/runtime/` | Python subpackage | 2 | YES | CONFIRMED_RUNTIME (work_state, provider_state) |
| `core/runtime/` | Python subpackage | 44 | YES | Substrate contracts |
| `data/runtime/` | Data directory | ~30 dirs | NO | Runtime artifacts |

### 1.2 Top-Level `runtime/` — Relocation Required

The existing `runtime/` directory contains Docker/deployment configuration:

```
runtime/
  docker-compose.yml   — alternative compose (references runtime/Dockerfile)
  Dockerfile           — same image as root Dockerfile
  setup.sh             — setup script (mirror of root setup.sh)
  install.sh           — install script (mirror of root install.sh)
  patch_pycord.py      — py-cord patch
  services.env         — env file
  .env.sessions        — session env
  .env.example         — env template
  umh.env              — UMH env vars
  .dockerignore        — Docker ignore
  .pytest_cache/       — pytest cache (4 files)
```

**Active usage:** Docker Compose runs from root `docker-compose.yml`,
not `runtime/docker-compose.yml`. The `runtime/` compose is an
alternative/mirror last modified during R5.

**Decision:** Relocate to `infra/docker/`

**Rationale:**
- `runtime/` as Docker config is a legacy arrangement
- `infra/docker/` clearly communicates "deployment infrastructure"
- No Python imports reference top-level `runtime/`
- Root `docker-compose.yml` is the active compose — no disruption
- The 6 internal refs in `runtime/docker-compose.yml` and
  `runtime/Dockerfile` update trivially

### 1.3 `eos_ai/runtime/` — Flatten Into New `runtime/`

The 2 files in `eos_ai/runtime/` (`work_state.py`, `provider_state.py`)
are CONFIRMED_RUNTIME with 16 import sites. They flatten to
`runtime/work_state.py` and `runtime/provider_state.py` (matching
eos_ai/ flat module pattern).

### 1.4 `core/runtime/` — No Collision

`core/runtime/` is a subpackage of `core/`, imported as
`from core.runtime.X import Y`. No collision with top-level `runtime/`.

### 1.5 `data/runtime/` — No Collision

Data directory, not a Python package. No collision.

---

## 2. File Migration Map

### 2.1 eos_ai/ → runtime/ (Atomic Move, Not Copy)

**INVARIANT:** At no point do two mutable implementations coexist.
Each file is moved (not copied), then the source location becomes
a compatibility shim. One runtime, many namespace entrypoints.

| Source | Destination | Files | Notes |
|--------|-------------|-------|-------|
| `eos_ai/*.py` (123 files) | `runtime/*.py` | 123 | Top-level modules |
| `eos_ai/transport/*.py` (164 files) | `runtime/transport/*.py` | 164 | Canonical transport subsystem |
| `eos_ai/transport/__init__.py` | `runtime/transport/__init__.py` | 1 | 575-line init with deferred imports |
| `eos_ai/substrate/*.py` (164 shims) | `runtime/substrate/*.py` | 164 | Currently `from eos_ai.transport.X import *` → update to `from runtime.transport.X import *` |
| `eos_ai/substrate/__init__.py` | `runtime/substrate/__init__.py` | 1 | Update: `from eos_ai.transport import *` → `from runtime.transport import *` |
| `eos_ai/runtime/work_state.py` | `runtime/work_state.py` | 1 | Flattened from subdirectory |
| `eos_ai/runtime/provider_state.py` | `runtime/provider_state.py` | 1 | Flattened from subdirectory |
| `eos_ai/interfaces/*.py` (2 files) | `runtime/interfaces/*.py` | 2 | Dormant |
| `eos_ai/platforms/eos/` | `runtime/platforms/eos/` | 0 | No source files remain, only `__pycache__` — skip |
| `eos_ai/CLAUDE.md` | `runtime/CLAUDE.md` | 1 | Update identity |
| `eos_ai/README_STATUS.md` | `runtime/README_STATUS.md` | 1 | Update identity |
| `eos_ai/.env` | See §4 | 1 | Env file |

**Total source files to move:** ~458 `.py` files + 2 `.md` files

### 2.2 runtime/ → infra/docker/ (Deployment Config)

| Source | Destination | Files |
|--------|-------------|-------|
| `runtime/docker-compose.yml` | `infra/docker/docker-compose.yml` | 1 |
| `runtime/Dockerfile` | `infra/docker/Dockerfile` | 1 |
| `runtime/setup.sh` | `infra/docker/setup.sh` | 1 |
| `runtime/install.sh` | `infra/docker/install.sh` | 1 |
| `runtime/patch_pycord.py` | `infra/docker/patch_pycord.py` | 1 |
| `runtime/services.env` | `infra/docker/services.env` | 1 |
| `runtime/.env.sessions` | `infra/docker/.env.sessions` | 1 |
| `runtime/.env.example` | `infra/docker/.env.example` | 1 |
| `runtime/umh.env` | `infra/docker/umh.env` | 1 |
| `runtime/.dockerignore` | `infra/docker/.dockerignore` | 1 |
| `runtime/.pytest_cache/` | delete | — |

**Total deployment files to relocate:** 10

---

## 3. Compatibility Shim Design

### 3.1 Core Invariant

**One runtime. Many entrypoints. Zero duplication.**

After migration, `runtime/` contains the only mutable implementation.
`eos_ai/` contains only generated shims — single-line re-exports that
forward to `runtime/`. No logic, no state, no conditional behavior.

### 3.2 Shim Architecture

```
runtime/                       ← canonical location (ONLY mutable code)
  db.py                        ← actual code
  context.py                   ← actual code
  model_router.py              ← actual code
  transport/                   ← canonical transport
  substrate/                   ← shim → transport (preserved behavior)
  ...

eos_ai/                        ← generated compatibility layer (IMMUTABLE)
  db.py                        ← from runtime.db import *
  context.py                   ← from runtime.context import *
  model_router.py              ← from runtime.model_router import *
  transport/__init__.py         ← from runtime.transport import *
  substrate/__init__.py         ← from runtime.substrate import *
  runtime/work_state.py         ← from runtime.work_state import *
  runtime/provider_state.py     ← from runtime.provider_state import *
  ...
```

### 3.3 Shim Generation Requirements

Shims are generated by a deterministic script, never handwritten.

**Generator responsibilities:**
1. Walk `runtime/` to discover all `.py` modules
2. For each module, emit the corresponding `eos_ai/` shim
3. Handle special cases:
   - `substrate/*.py` → target is `runtime.transport.{module}` (preserving
     existing shim chain behavior)
   - `runtime/work_state.py` → shim at `eos_ai/runtime/work_state.py`
     (depth differs)
   - `transport/__init__.py` → single `from runtime.transport import *`
4. Produce a shim manifest (`data/migration/r8_shim_manifest.json`)
5. Produce a diff report (expected vs actual shim count)
6. Detect orphan shims (eos_ai/ files with no runtime/ counterpart)
7. Detect missing shims (runtime/ files with no eos_ai/ shim)

**Shim format (deterministic):**

For top-level modules:
```python
from runtime.{module} import *  # noqa: F401,F403
```

For transport submodules:
```python
from runtime.transport.{module} import *  # noqa: F401,F403
```

For substrate submodules (preserving shim chain):
```python
from runtime.transport.{module} import *  # noqa: F401,F403
```

For `__init__.py` files:
```python
from runtime.{package} import *  # noqa: F401,F403
```

### 3.4 Shim Manifest Schema

```json
{
  "generated_at": "2026-05-10T...",
  "generator": "scripts/r8_generate_shims.py",
  "runtime_modules": 458,
  "shims_generated": 458,
  "orphans": [],
  "missing": [],
  "special_cases": {
    "depth_changes": ["eos_ai/runtime/work_state.py", "eos_ai/runtime/provider_state.py"],
    "chain_preservations": ["eos_ai/substrate/*.py → runtime.transport.*"]
  }
}
```

### 3.5 Shim Validation

After generation, verify:
```bash
# 1. Every runtime/ module has a corresponding eos_ai/ shim
python3 scripts/r8_validate_shims.py --check-coverage

# 2. No shim contains more than 1 line of executable code
find eos_ai/ -name '*.py' -exec wc -l {} + | awk '$1 > 1 {print "OVERSIZED:", $0}'

# 3. Every shim imports from runtime/, never from eos_ai/
grep -rn "from eos_ai\." eos_ai/ --include='*.py' | wc -l  # expect: 0

# 4. Replay test: import through shim, import canonical, compare identity
python3 -c "
from eos_ai.db import get_conn as shim_fn
from runtime.db import get_conn as canon_fn
assert shim_fn is canon_fn, 'identity mismatch'
print('replay identity: PASS')
"
```

### 3.6 eos_ai/substrate/ Shim Chain

Current chain: `eos_ai.substrate.X` → `eos_ai.transport.X` (existing shim)
New chain: `eos_ai.substrate.X` → `runtime.transport.X` (updated shim)

The `runtime/substrate/` directory preserves the existing shim behavior
(`runtime.substrate.X` → `runtime.transport.X`), maintaining the same
two-path import surface.

### 3.7 transport/__init__.py Deferred Import Strings

The 575-line `transport/__init__.py` uses deferred imports like:
```python
("eos_ai.transport.nodes", ["Node", "NodeType", ...])
```

These string-based internal references (inside `_deferred_blocks`) must
be updated to `"runtime.transport.nodes"` during the file move (R8b).
This is an internal self-reference, not an external consumer.

---

## 4. eos_ai/.env Strategy

### 4.1 Options

| Option | Pros | Cons |
|--------|------|------|
| `runtime/.env` | Direct rename, simple | Still split across dirs |
| Root `.env` | Single env file, simpler | Large file, mixes concerns |
| Keep `eos_ai/.env` symlink | Zero migration | Preserves legacy path |

### 4.2 Decision: `runtime/.env` with `eos_ai/.env` Symlink

1. Move `eos_ai/.env` → `runtime/.env`
2. Create symlink: `eos_ai/.env` → `runtime/.env`
3. Symlink ensures Docker compose `env_file: eos_ai/.env` continues working
4. Migrate `load_dotenv` calls to `runtime/.env` during consumer update waves
5. Remove symlink when `eos_ai/` directory is deleted (R8i)

### 4.3 eos_ai/.env Reference Sites (256 total)

| Category | Count | Migration Wave |
|----------|-------|----------------|
| Docker compose `env_file:` | 3 | R8g (deploy) |
| Shell scripts `source`/`check` | 6 | R8g (deploy) |
| Python `load_dotenv()` | ~20 | R8f (strings) |
| Claude Code skills/commands | 12 | R8g (deploy) |
| Documentation/CLAUDE.md | 10+ | R8g (deploy) |
| Test fixtures | 5 | R8e (tests) |

---

## 5. Import Migration — Complete Site Map

### 5.1 Python Import Sites (2,726 total)

| Consumer | `from eos_ai` | `import eos_ai` | Total | Wave |
|----------|---------------|-----------------|-------|------|
| `eos_ai/` (self) | 1,448 | 2 | 1,450 | R8b+R8c (move + internal topology) |
| `scripts/` | 470 | 33 | 503 | R8e (external) |
| `tests/` | 380 | 4 | 384 | R8e (external) |
| `services/` | 304 | 0 | 304 | R8e (external) |
| `archive/` | 65 | 0 | 65 | SKIP (frozen) |
| `core/` | 16 | 0 | 16 | R8e (circular dep resolution) |
| `saas/` | 3 | 0 | 3 | R8e (external) |
| `templates/` | 1 | 0 | 1 | R8e (external) |

### 5.2 Non-Python References (789 total)

| Type | Count | Wave |
|------|-------|------|
| `mock.patch("eos_ai.X")` strings | 221 | R8f (strings) |
| Filesystem path refs (`eos_ai/`) | 201 | R8f (strings) |
| Shell script refs | 85 | R8g (deploy) |
| `eos_ai/.env` refs | 256 | R8f + R8g |
| Docker/config refs | 4 | R8g (deploy) |
| `python3 -m eos_ai` | 20 | R8g (deploy) |
| Crontab entries | 2 | R8g (deploy) |

### 5.3 Circular Dependencies (41 cross-imports)

**core/ → eos_ai/ (16 imports) — PROBLEMATIC DIRECTION**

| File | What It Imports | Resolution |
|------|-----------------|------------|
| `core/execution_contract.py` | `context`, `db`, `substrate.execution_trace`, `gateway`, `authority_engine`, `memory`, `agent_runtime` | Update to `from runtime.X` — acceptable since core/ already depends on runtime layer via lazy imports |
| `core/coord_assignment.py` | `embedder` | Update to `from runtime.embedder` |
| `core/semantic_space.py` | `embedder` | Update to `from runtime.embedder` |
| `core/agent_harness.py` | `memory`, `model_router`, `agent_runtime` | Update to `from runtime.X` |
| `core/workstation/*.py` | `substrate.memory_scope_contracts` | Update to `from runtime.substrate.X` |
| `core/action_system/policy.py` | `authority_engine` | Update to `from runtime.authority_engine` |

**Strategy:** All 16 core/ → eos_ai/ imports are lazy (inside function bodies)
or at module level in non-critical paths. During R8e, update them to
`from runtime.X`. The circular dependency is architectural debt but does
not cause import cycles because of lazy import patterns.

**eos_ai/ → core/ (25 imports) — EXPECTED DIRECTION**

These become `runtime/ → core/` imports. Updated during R8c as part
of internal topology migration.

---

## 6. Execution Waves

### Wave R8a — Relocate Top-Level `runtime/` (LOW RISK)

**Purpose:** Clear the `runtime/` namespace for the new Python package.

**Actions:**
1. Create `infra/docker/` directory
2. `git mv runtime/docker-compose.yml infra/docker/docker-compose.yml`
3. `git mv runtime/Dockerfile infra/docker/Dockerfile`
4. `git mv runtime/setup.sh infra/docker/setup.sh`
5. `git mv runtime/install.sh infra/docker/install.sh`
6. `git mv runtime/patch_pycord.py infra/docker/patch_pycord.py`
7. `git mv runtime/services.env infra/docker/services.env`
8. `git mv runtime/.env.sessions infra/docker/.env.sessions`
9. `git mv runtime/.env.example infra/docker/.env.example`
10. `git mv runtime/umh.env infra/docker/umh.env`
11. `git mv runtime/.dockerignore infra/docker/.dockerignore`
12. Delete `runtime/.pytest_cache/`
13. Update internal refs in `infra/docker/docker-compose.yml` and
    `infra/docker/Dockerfile` (6 refs: `runtime/` → `infra/docker/`)
14. Verify: `ls runtime/` → directory gone

**Files affected:** 10 moved, 2 updated
**Rollback:** `git mv infra/docker/* runtime/`
**Commit:** `root-migration-r8a: relocate runtime/ docker config to infra/docker/`

### Wave R8b — Create Canonical `runtime/` via Atomic Move (MEDIUM RISK)

**Purpose:** Move eos_ai/ implementation into runtime/ atomically.
No duplicated live implementations.

**Core invariant:** After R8b, `runtime/` is the only location with
mutable source code. `eos_ai/` is either empty or contains only
generated shims. At no point do two parallel mutable implementations exist.

**Actions:**

1. **Capture pre-move import graph snapshot:**
   ```bash
   python3 scripts/r8_import_graph_snapshot.py --output data/migration/r8_pre_move_graph.json
   ```
   Records: every importable module, its dependencies, initialization order,
   cycle membership. This is the baseline for R8c comparison.

2. **Atomic move** of all eos_ai/ source into runtime/:
   ```bash
   # Move top-level modules
   for f in eos_ai/*.py; do git mv "$f" "runtime/$(basename $f)"; done

   # Move transport/ (canonical subsystem)
   git mv eos_ai/transport runtime/transport

   # Move substrate/ (shim layer)
   git mv eos_ai/substrate runtime/substrate

   # Flatten eos_ai/runtime/ into runtime/ top-level
   git mv eos_ai/runtime/work_state.py runtime/work_state.py
   git mv eos_ai/runtime/provider_state.py runtime/provider_state.py

   # Move interfaces/ (dormant)
   git mv eos_ai/interfaces runtime/interfaces

   # Move docs
   git mv eos_ai/CLAUDE.md runtime/CLAUDE.md
   git mv eos_ai/README_STATUS.md runtime/README_STATUS.md
   ```

3. **Immediately install temporary re-export bridges** where atomic move
   is unsafe (where external consumers would break before R8d/R8e):
   - Create minimal `eos_ai/` directory with bridge modules that re-export
     from `runtime/` — these are NOT the final shims (R8d generates those)
   - These bridges exist solely to keep `from eos_ai.X` imports working
     during the transition window between R8b and R8d
   - Bridge modules are marked with a generation header so R8d can
     safely overwrite them

4. **Move .env:** `eos_ai/.env` → `runtime/.env`, create symlink
   `eos_ai/.env → runtime/.env`

**What remains in eos_ai/ after R8b:**
- Temporary re-export bridges (overwritten by R8d generated shims)
- `.env` symlink → `runtime/.env`
- `__pycache__/` (stale, harmless)

**Verification:**
```bash
# Canonical imports work
python3 -c "from runtime.db import get_conn; print('runtime.db: ok')"
python3 -c "from runtime.context import load_context_from_env; print('runtime.context: ok')"
# Bridge imports work
python3 -c "from eos_ai.db import get_conn; print('eos_ai.db bridge: ok')"
# No duplicated source
find runtime/ -name '*.py' | wc -l   # should be ~458
find eos_ai/ -name '*.py' | wc -l    # should be ~458 (bridges only)
# Bridge files are all single-line
find eos_ai/ -name '*.py' -exec wc -l {} + | awk '$1 > 1 {print "WARNING:", $0}'
```

**Files affected:** ~458 moved + ~458 bridge files created
**Rollback:** `git checkout HEAD -- eos_ai/ && rm -rf runtime/`
**Commit:** `root-migration-r8b: move eos_ai/ implementation to runtime/ with re-export bridges`

### Wave R8c — Internal Topology Migration (HIGHEST RISK)

**Purpose:** Make `runtime/` internally self-consistent — all internal
imports reference `runtime.*` instead of `eos_ai.*`.

**Why this is the most dangerous step:**

Updating 1,450 internal self-references alters:
- Runtime import topology
- Module initialization order
- Implicit dependency resolution
- Circular graph behavior
- Lazy import timing
- Deferred registration order
- Singleton identity

A "successful" sed replacement can still subtly corrupt bootstrap
ordering, lazy import timing, or singleton identity. These are the
hardest bugs to detect because tests pass but runtime behavior diverges.

**Pre-flight requirements (MANDATORY):**

1. **Import graph snapshot BEFORE:**
   ```bash
   python3 scripts/r8_import_graph_snapshot.py \
     --root runtime/ \
     --output data/migration/r8c_pre_graph.json
   ```
   Records for every module in `runtime/`:
   - Direct imports (module-level)
   - Lazy imports (inside function bodies)
   - Cycle membership (which modules participate in circular imports)
   - Init order (topological sort position)
   - Singleton registrations (globals, registries)

2. **Cold boot baseline timing:**
   ```bash
   python3 -c "
   import time, sys
   sys.path.insert(0, '/opt/OS')
   t0 = time.monotonic()
   from runtime.db import get_conn
   from runtime.context import load_context_from_env
   from runtime.model_router import get_router
   from runtime.gateway import EOSGateway
   from runtime.memory import AgentMemory
   from runtime.agent_runtime import AgentRuntime
   from runtime.cognitive_loop import CognitiveLoop
   from runtime.transport.storage import get_storage
   elapsed = time.monotonic() - t0
   print(f'cold boot: {elapsed:.3f}s')
   " 2>&1 | tee data/migration/r8c_pre_boot_timing.txt
   ```

**Actions:**

1. In all `runtime/*.py` (top-level): `from eos_ai.` → `from runtime.`
2. In all `runtime/transport/*.py`: `from eos_ai.` → `from runtime.`
3. In `runtime/transport/__init__.py`: update deferred import strings
   `"eos_ai.transport.X"` → `"runtime.transport.X"`
4. In all `runtime/substrate/*.py` shims:
   `from eos_ai.transport.X import *` → `from runtime.transport.X import *`
5. In `runtime/substrate/__init__.py`:
   `from eos_ai.transport import *` → `from runtime.transport import *`
6. Flatten `eos_ai.runtime.X` refs within runtime/:
   `from eos_ai.runtime.work_state` → `from runtime.work_state`
   `from eos_ai.runtime.provider_state` → `from runtime.provider_state`
7. Update `from core.` imports — these stay as `from core.` (correct
   direction, no change needed)

**Estimated edits:** ~1,450 import statements across ~300 files

**Post-flight verification (MANDATORY):**

1. **Compile check:**
   ```bash
   find runtime/ -name '*.py' -exec python3 -m py_compile {} +
   ```

2. **Import graph snapshot AFTER:**
   ```bash
   python3 scripts/r8_import_graph_snapshot.py \
     --root runtime/ \
     --output data/migration/r8c_post_graph.json
   ```

3. **Graph comparison:**
   ```bash
   python3 scripts/r8_compare_import_graphs.py \
     data/migration/r8c_pre_graph.json \
     data/migration/r8c_post_graph.json \
     --output data/migration/r8c_graph_diff.json
   ```
   Validates:
   - **Cycle count comparison:** same number of cycles, same members
     (modulo `eos_ai` → `runtime` rename)
   - **Module init order diff:** topological sort is isomorphic
   - **Dependency count per module:** unchanged
   - **New cycles introduced:** MUST be zero
   - **Lost edges:** MUST be zero (every old dependency has a
     corresponding new dependency)

4. **Cold boot timing comparison:**
   ```bash
   python3 -c "
   import time, sys
   sys.path.insert(0, '/opt/OS')
   t0 = time.monotonic()
   from runtime.db import get_conn
   from runtime.context import load_context_from_env
   from runtime.model_router import get_router
   from runtime.gateway import EOSGateway
   from runtime.memory import AgentMemory
   from runtime.agent_runtime import AgentRuntime
   from runtime.cognitive_loop import CognitiveLoop
   from runtime.transport.storage import get_storage
   elapsed = time.monotonic() - t0
   print(f'cold boot: {elapsed:.3f}s')
   " 2>&1 | tee data/migration/r8c_post_boot_timing.txt
   ```
   **Acceptance:** post timing within 20% of pre timing.
   Significant deviation indicates init order corruption.

5. **Zero residual eos_ai refs:**
   ```bash
   grep -rn "from eos_ai\|import eos_ai" runtime/ --include='*.py' | wc -l
   # MUST be 0
   ```

6. **Replay identity verification:**
   ```bash
   python3 -c "
   import sys; sys.path.insert(0, '/opt/OS')
   # Import through bridge (eos_ai/) and canonical (runtime/)
   from eos_ai.db import get_conn as bridge_fn
   from runtime.db import get_conn as canon_fn
   assert bridge_fn is canon_fn, 'IDENTITY MISMATCH: db.get_conn'

   from eos_ai.model_router import get_router as bridge_r
   from runtime.model_router import get_router as canon_r
   assert bridge_r is canon_r, 'IDENTITY MISMATCH: model_router.get_router'

   from eos_ai.context import load_context_from_env as bridge_c
   from runtime.context import load_context_from_env as canon_c
   assert bridge_c is canon_c, 'IDENTITY MISMATCH: context.load_context_from_env'

   print('replay identity: ALL PASS')
   "
   ```

**If ANY post-flight check fails:** Do NOT proceed to R8d. Diagnose
the topology corruption before continuing.

**Rollback:** `rm -rf runtime/ && git checkout HEAD -- eos_ai/`
**Commit:** `root-migration-r8c: internal topology migration with graph verification`

### Wave R8d — Generate Compatibility Shims (MEDIUM RISK)

**Purpose:** Replace temporary R8b bridges in eos_ai/ with
deterministically generated, validated compatibility shims.

**Why generated, not handwritten:**

458 shims is large enough that manual work becomes a consistency risk.
Handwritten shims produce:
- Partial migration drift
- Inconsistent exports
- Hidden replay mismatches
- Orphan detection failures

**Actions:**

1. **Run shim generator:**
   ```bash
   python3 scripts/r8_generate_shims.py \
     --source runtime/ \
     --target eos_ai/ \
     --manifest data/migration/r8_shim_manifest.json
   ```

   The generator:
   - Walks `runtime/` to discover all importable `.py` modules
   - For each module, emits the corresponding `eos_ai/` shim
   - Handles special cases (substrate chain, depth flattening)
   - Produces a manifest with counts, orphans, missing, special cases
   - Produces a diff report comparing generated vs existing

2. **Validate manifest:**
   ```bash
   python3 scripts/r8_validate_shims.py \
     --manifest data/migration/r8_shim_manifest.json \
     --check-coverage \
     --check-identity \
     --check-orphans
   ```

   Checks:
   - **Coverage:** every runtime/ module has a shim
   - **Identity:** importing through shim returns same object as canonical
   - **Orphans:** no eos_ai/ shim without a runtime/ counterpart
   - **Missing:** no runtime/ module without an eos_ai/ shim
   - **Oversized:** no shim exceeds 1 line of executable code
   - **Self-reference:** no shim imports from eos_ai/ (would create a loop)

3. **Full test suite:**
   ```bash
   cd /opt/OS && python3 -m pytest tests/ -x --tb=short -q
   # Expected: 8558 passed, 27 failed (pre-existing), 0 new regressions
   ```

4. **Critical import path check:**
   ```bash
   python3 -c "from eos_ai.db import get_conn; print('shim ok')"
   python3 -c "from eos_ai.context import load_context_from_env; print('shim ok')"
   python3 -c "from eos_ai.substrate.storage import get_storage; print('shim ok')"
   python3 -c "from eos_ai.runtime.work_state import detect_work_state; print('shim ok')"
   python3 -c "from runtime.db import get_conn; print('canonical ok')"
   ```

**Manifest output example:**
```json
{
  "generated_at": "2026-05-10T...",
  "generator": "scripts/r8_generate_shims.py",
  "runtime_modules": 458,
  "shims_generated": 458,
  "orphans": [],
  "missing": [],
  "oversized": [],
  "self_referencing": [],
  "special_cases": {
    "depth_changes": [
      "eos_ai/runtime/work_state.py → runtime.work_state",
      "eos_ai/runtime/provider_state.py → runtime.provider_state"
    ],
    "chain_preservations": [
      "eos_ai/substrate/*.py → runtime.transport.*"
    ]
  },
  "identity_checks_passed": true
}
```

**Files affected:** ~458 shim files (replacing temporary bridges)
**Rollback:** `git checkout HEAD -- eos_ai/`
**Commit:** `root-migration-r8d: install generated compatibility shims with manifest`

### Wave R8e — Migrate External Consumers (MEDIUM RISK)

**Purpose:** Update all non-eos_ai Python files to import from
`runtime.*` instead of `eos_ai.*`.

**Sequencing (safest → riskiest):**

#### R8e-1: tests/ (384 imports)

```bash
find tests/ -name '*.py' -exec sed -i \
  's/from eos_ai\./from runtime./g; s/import eos_ai\./import runtime./g' {} +
```

**Special handling:** Skip `tests/legacy/unit/test_umh_wave9_wrapper_removal.py`
and other tests that assert on `eos_ai` string presence — these are
meta-tests that check the migration itself.

Verify: `python3 -m pytest tests/ -x --tb=short -q`

#### R8e-2: scripts/ (503 imports)

```bash
find scripts/ -name '*.py' -exec sed -i \
  's/from eos_ai\./from runtime./g; s/import eos_ai\./import runtime./g' {} +
```

Verify: compile check all scripts

#### R8e-3: services/ (304 imports)

```bash
find services/ -name '*.py' -exec sed -i \
  's/from eos_ai\./from runtime./g; s/import eos_ai\./import runtime./g' {} +
```

**Special handling — dynamic imports:**
- `services/discord_bot.py:787` — `__import__("eos_ai.agent_teams")` → `__import__("runtime.agent_teams")`
- `services/discord_bot.py:882` — same
- `services/discord_bot.py:3247` — `__import__("eos_ai.world_pulse")` → `__import__("runtime.world_pulse")`

Verify: `python3 -c "import sys; sys.path.insert(0,'/opt/OS'); import services.discord_bot; print('ok')"`

#### R8e-4: core/ (16 imports — circular dep resolution)

Manual update. Each of the 16 sites:
`from eos_ai.X` → `from runtime.X`

Verify: `python3 -c "import sys; sys.path.insert(0,'/opt/OS'); from core.execution_contract import run_task; print('ok')"`

#### R8e-5: saas/ + templates/ (4 imports)

```bash
find saas/ templates/ -name '*.py' -exec sed -i \
  's/from eos_ai\./from runtime./g' {} +
```

**Commit:** `root-migration-r8e: migrate external consumers to runtime/ namespace`

### Wave R8f — Migrate String-Based References (MEDIUM RISK)

**Purpose:** Update mock.patch strings, importlib strings, filesystem
path strings, and other non-import references.

#### R8f-1: mock.patch strings (221 sites)

```bash
find tests/ -name '*.py' -exec sed -i \
  's/"eos_ai\./"runtime./g' {} +
```

**Safe because:** `"eos_ai.` as a string literal in tests only
appears in mock.patch contexts and importlib contexts.

#### R8f-2: importlib / __import__ strings (8 sites)

Manual update in:
- `runtime/transport/discord_voice_playback.py:93`
- `scripts/substrate_workflow_delegation_smoke_test.py` (3 sites)
- `scripts/substrate_execution_trace_smoke_test.py:278`

(services/discord_bot.py already updated in R8e-3)

#### R8f-3: Filesystem path strings (201 sites)

```bash
# In Python files: "eos_ai/" → "runtime/" for path construction
find . -name '*.py' -not -path './archive/*' -not -path './.git/*' \
  -not -path './eos_ai/*' \
  -exec grep -l 'eos_ai/' {} + | \
  xargs sed -i 's|eos_ai/|runtime/|g'
```

**Exclusions:**
- `eos_ai/` (shims — don't modify)
- `archive/` (frozen)
- Docstrings/comments documenting the migration (describe old state)

#### R8f-4: `eos_ai.runtime.X` → `runtime.X` (depth flattening in strings)

The `eos_ai.runtime.work_state` and `eos_ai.runtime.provider_state`
mock.patch paths lose one level. All string-based refs become:
- `"runtime.work_state.*"`
- `"runtime.provider_state.*"`

#### R8f-5: load_dotenv path strings (~20 sites)

```python
# Old: load_dotenv('/opt/OS/eos_ai/.env')
# New: load_dotenv(os.path.join(os.environ.get('UMH_ROOT', '/opt/OS'), 'runtime/.env'))
```

**Commit:** `root-migration-r8f: migrate string-based and path references`

### Wave R8g — Migrate Shell/Config/Deployment (MEDIUM RISK)

**Purpose:** Update shell scripts, Docker, crontab, skills, commands.

#### R8g-1: Shell scripts (85 refs)

- Inline Python: `from eos_ai.X` → `from runtime.X`
- Filesystem paths: `eos_ai/` → `runtime/`
- `python3 -m eos_ai.X` → `python3 -m runtime.X`

#### R8g-2: Docker compose (4 refs)

```yaml
# docker-compose.yml
env_file:
  - runtime/.env    # was: eos_ai/.env
```

#### R8g-3: Crontab (2 entries)

```bash
# Current:
0 6 * * * cd /opt/OS && python3 eos_ai/orchestrator.py >> ...
0 23 * * * python3 -c "... from eos_ai.X import Y ..."

# Updated:
0 6 * * * cd /opt/OS && python3 runtime/orchestrator.py >> ...
0 23 * * * python3 -c "... from runtime.X import Y ..."
```

#### R8g-4: Claude Code skills/commands (12+ files)

- `.claude/skills/*.md`: `eos_ai/.env` → `runtime/.env`
- `.claude/commands/*.md`: `load_dotenv('*/eos_ai/.env')` → `load_dotenv('*/runtime/.env')`
- `.claude/rules/python.md`: `load_dotenv('/opt/OS/eos_ai/.env')` → `load_dotenv('/opt/OS/runtime/.env')`

#### R8g-5: CLAUDE.md / documentation

- `CLAUDE.md`: `eos_ai/.env` → `runtime/.env`, `eos_ai/` → `runtime/`
- `.claude/CLAUDE.md`: `eos_ai/` references → `runtime/`
- `services/CLAUDE.md`: `eos_ai/.env` → `runtime/.env`
- `README.md`: `eos_ai/.env` → `runtime/.env`

#### R8g-6: python3 -m invocations (20 sites)

All `python3 -m eos_ai.X` → `python3 -m runtime.X`

**Commit:** `root-migration-r8g: migrate shell, config, and deployment references`

### Wave R8h — Epistemic Equivalence Proof (VERIFICATION ONLY)

**Purpose:** Prove that the migration is functionally and topologically
equivalent to the pre-migration state. No code changes.

#### R8h-1: Discord Dry-Run

```bash
python3 -c "
import sys; sys.path.insert(0, '/opt/OS')
from runtime.context import load_context_from_env
from runtime.db import get_conn
from runtime.model_router import get_router, TaskType
from runtime.gateway import EOSGateway
from runtime.memory import AgentMemory, ConversationMemory
from runtime.agent_runtime import AgentRuntime
print('Discord import chain: PASS')
conn = get_conn()
print(f'Neon connection: PASS ({conn.info.host})')
"
```

#### R8h-2: Orchestrator Dry-Run

```bash
python3 -c "
import sys; sys.path.insert(0, '/opt/OS')
from runtime.orchestrator import EOSOrchestrator
from runtime.cognitive_loop import CognitiveLoop
print('Orchestrator import chain: PASS')
"
```

#### R8h-3: Full Substrate Suite

```bash
python3 -m pytest tests/ -x --tb=short -q
# Expected: 8558 passed, 27 failed (pre-existing)
```

#### R8h-4: Import Graph Scan

```bash
# Verify NO external consumer still imports from eos_ai
grep -rn "from eos_ai\.\|import eos_ai\." --include='*.py' \
  | grep -v "^eos_ai/" | grep -v "^archive/" \
  | grep -v "test_umh_wave" \
  | wc -l
# Expected: 0
```

#### R8h-5: Final Circular Dependency Report

```bash
# core/ → runtime/ imports: classify each as lazy vs module-level
python3 scripts/r8_circular_dep_report.py \
  --output data/migration/r8h_circular_dep_report.json
```

Report contains:
- Every `core/ → runtime/` import site
- Whether it's module-level or inside a function body
- Whether it participates in a cycle
- Risk classification

#### R8h-6: Replay Identity Report

```bash
python3 scripts/r8_replay_identity_report.py \
  --output data/migration/r8h_replay_identity.json
```

Validates for every shim module:
- `eos_ai.X.func is runtime.X.func` (object identity)
- `eos_ai.X.Class is runtime.X.Class` (class identity)
- `id(sys.modules['eos_ai.X']) != id(sys.modules['runtime.X'])` (module
  objects are different, but their contents point to same objects)

#### R8h-7: Import Graph Final Snapshot

```bash
python3 scripts/r8_import_graph_snapshot.py \
  --root runtime/ \
  --output data/migration/r8h_final_graph.json

python3 scripts/r8_compare_import_graphs.py \
  data/migration/r8_pre_move_graph.json \
  data/migration/r8h_final_graph.json \
  --output data/migration/r8h_full_migration_diff.json
```

**Acceptance criteria for R8h:**
- [ ] Discord import chain: PASS
- [ ] Orchestrator import chain: PASS
- [ ] Test suite: 8558 pass, 27 fail (pre-existing), 0 new
- [ ] External eos_ai imports remaining: 0
- [ ] New circular dependencies introduced: 0
- [ ] Module init order: isomorphic to pre-migration
- [ ] Cold boot timing: within 20% of pre-migration
- [ ] Replay identity: all shim→canonical pairs verified
- [ ] Shim manifest: 0 orphans, 0 missing

**Commit:** `root-migration-r8h: epistemic equivalence proof`

### Wave R8i — Shim Retirement (DEFERRED)

**Purpose:** Remove `eos_ai/` directory entirely.
**Status:** NOT part of this execution plan. Deferred until:
1. All waves R8a-R8h complete and validated
2. Minimum 1 week runtime with shims active
3. No import errors in production logs
4. `test_umh_wave9_wrapper_removal.py` used as completion gate

**When ready:**
```bash
rm -rf eos_ai/
python3 -m pytest tests/legacy/unit/test_umh_wave9_wrapper_removal.py -v
python3 -m pytest tests/ -x --tb=short -q
```

---

## 7. Risk Matrix

| Wave | Risk | Blast Radius | Rollback Complexity |
|------|------|-------------|---------------------|
| R8a — Relocate runtime/ | LOW | 0 (unused config) | `git mv infra/docker/* runtime/` |
| R8b — Atomic move + bridges | MEDIUM | All consumers (bridges maintain compat) | `git checkout HEAD -- eos_ai/ && rm -rf runtime/` |
| R8c — Internal topology | **HIGHEST** | runtime/ bootstrap, init order, singletons | `rm -rf runtime/` + re-move from git |
| R8d — Generated shims | MEDIUM | All consumers (replaces bridges) | `git checkout HEAD -- eos_ai/` |
| R8e — External consumers | MEDIUM | tests, scripts, services | `git checkout HEAD -- <dir>` |
| R8f — String refs | MEDIUM | tests (mock.patch) | `git checkout HEAD -- tests/` |
| R8g — Shell/config/deploy | MEDIUM | Deployment | `git checkout HEAD -- <files>` |
| R8h — Equivalence proof | NONE | 0 (read-only) | N/A |
| R8i — Shim retirement | LOW | None if validated | Restore shims from git |

---

## 8. Execution Constraints

1. **Each wave is an atomic commit** — pass or fail as a unit
2. **One runtime, many entrypoints** — no duplicated mutable code, ever
3. **R8c requires pre/post graph snapshots** — do not skip
4. **R8d shims are generated, not handwritten** — deterministic, validated
5. **Full test suite after R8d** (shim installation is the critical gate)
6. **No Docker restart until R8g** — shims keep current containers working
7. **archive/ is NEVER modified** — dead imports are expected
8. **Stop after R8h** — shim retirement (R8i) is a separate approval
9. **Crontab updated last** (R8g-3) — after all Python imports validated
10. **If R8c post-flight fails, STOP** — do not proceed to R8d

---

## 9. Required Tooling (Built During Execution)

| Script | Purpose | Used In |
|--------|---------|---------|
| `scripts/r8_import_graph_snapshot.py` | Capture module dependency graph, init order, cycles | R8b, R8c, R8h |
| `scripts/r8_compare_import_graphs.py` | Diff two graph snapshots, detect new cycles | R8c, R8h |
| `scripts/r8_generate_shims.py` | Deterministically generate eos_ai/ shim modules | R8d |
| `scripts/r8_validate_shims.py` | Coverage, identity, orphan, oversized checks | R8d |
| `scripts/r8_circular_dep_report.py` | Classify core/→runtime/ imports as lazy vs module-level | R8h |
| `scripts/r8_replay_identity_report.py` | Verify object identity through shim vs canonical | R8h |

These scripts are built as needed during execution, not pre-built.
They are migration tooling, not permanent infrastructure.

---

## 10. Target Architecture

After R8h (shims still present):

```
/opt/OS  (→ /opt/UMH after physical rename)
  core/            ← substrate contracts, infrastructure
  runtime/         ← canonical intelligence/runtime layer (was eos_ai/)
  services/        ← live daemons, interface surfaces
  scripts/         ← operational tooling, cron scripts
  infra/docker/    ← deployment config (was runtime/)
  eos_ai/          ← compatibility shims only (removed in R8i)
  archive/         ← historical code (frozen)
  saas/            ← SaaS product (EOS projection)
  platforms/       ← future: EOS, LyfeOS, CreatorOS projections
```

After R8i (shims removed):

```
/opt/UMH
  core/            ← substrate/contracts/infrastructure
  runtime/         ← intelligence/runtime layer
  services/        ← live daemons/interfaces
  scripts/         ← operational tooling
  infra/docker/    ← deployment config
  platforms/       ← EOS, LyfeOS, CreatorOS projections
```

This is the first time the repository topology matches the
philosophical architecture: UMH as substrate, with application
projections as peers, not owners.

---

## 11. Updated Migration Readiness Matrix

| Wave | Status | Files | Regressions |
|------|--------|-------|-------------|
| R1 — UMH_ROOT env chain | Complete | core/paths.py + env setup | 0 |
| R2 — Runtime bootstrap | Complete | 193 files | 0 |
| R3 — Runtime filesystem refs | Complete | 154 files | 0 |
| R4 — Test topology | Complete | 179 files | 0 |
| R5 — Deployment infrastructure | Complete | 27 files | 0 |
| R6 — Semantic identity | Complete | 8 docs | 0 |
| R7 — Namespace migration plan | Complete | 1 doc | 0 |
| R8 — Execution plan (this) | Complete | 1 doc | 0 |
| R8a — Relocate runtime/ config | Ready | 12 files | — |
| R8b — Atomic move + bridges | Ready | ~916 files | — |
| R8c — Internal topology | Ready | ~300 files | — |
| R8d — Generated shims | Ready | ~458 files | — |
| R8e — External consumers | Ready | ~400 files | — |
| R8f — String-based refs | Ready | ~100 files | — |
| R8g — Shell/config/deploy | Ready | ~30 files | — |
| R8h — Equivalence proof | Ready | 0 (read-only) | — |
| R8i — Shim retirement | DEFERRED | ~460 files deleted | — |
