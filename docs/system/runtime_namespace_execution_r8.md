# Runtime Namespace Execution Plan — R8

> Phase: 96.8CQ — 2026-05-10
> Supersedes: R7 recommendation of `umh_runtime/`
> Target namespace: `runtime/`
> Type: Execution plan — no code changes in this commit

---

## Decision Record

**R7 recommended:** `umh_runtime/`
**R8 decision:** `runtime/`

**Rationale:**
- Repo root will become `/opt/UMH`, so `runtime/` is already UMH-scoped
- Simpler import path: `from runtime.db import get_conn`
- Cleaner long-term architecture: `core/` + `runtime/` + `services/`
- Avoids redundant `umh_runtime` naming inside a UMH repo

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

### 1.3 `eos_ai/runtime/` — Merge Into New `runtime/`

The 2 files in `eos_ai/runtime/` (`work_state.py`, `provider_state.py`)
are CONFIRMED_RUNTIME with 16 import sites. They become
`runtime/runtime_state/` or simply `runtime/work_state.py` and
`runtime/provider_state.py` (flat, matching eos_ai/ structure).

### 1.4 `core/runtime/` — No Collision

`core/runtime/` is a subpackage of `core/`, imported as
`from core.runtime.X import Y`. No collision with top-level `runtime/`.

### 1.5 `data/runtime/` — No Collision

Data directory, not a Python package. No collision.

---

## 2. File Migration Map

### 2.1 eos_ai/ → runtime/ (Source Code)

| Source | Destination | Files | Notes |
|--------|-------------|-------|-------|
| `eos_ai/*.py` (123 files) | `runtime/*.py` | 123 | Top-level modules |
| `eos_ai/transport/*.py` (164 files) | `runtime/transport/*.py` | 164 | Canonical transport subsystem |
| `eos_ai/transport/__init__.py` | `runtime/transport/__init__.py` | 1 | 575-line init with lazy imports |
| `eos_ai/substrate/*.py` (164 shims) | `runtime/substrate/*.py` | 164 | All are `from eos_ai.transport.X import *` → update to `from runtime.transport.X import *` |
| `eos_ai/substrate/__init__.py` | `runtime/substrate/__init__.py` | 1 | Update: `from eos_ai.transport import *` → `from runtime.transport import *` |
| `eos_ai/runtime/*.py` (2 files) | `runtime/work_state.py`, `runtime/provider_state.py` | 2 | Flatten from subdirectory to top-level |
| `eos_ai/interfaces/*.py` (2 files) | `runtime/interfaces/*.py` | 2 | Dormant |
| `eos_ai/platforms/eos/*.py` (compiled only) | `runtime/platforms/eos/` | 0 | No source files remain, only `__pycache__` |
| `eos_ai/CLAUDE.md` | `runtime/CLAUDE.md` | 1 | Update identity |
| `eos_ai/README_STATUS.md` | `runtime/README_STATUS.md` | 1 | Update identity |
| `eos_ai/.env` | Decision in §5 | 1 | Env file |

**Total source files to migrate:** ~458 `.py` files + 2 `.md` files

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

### 3.1 Shim Architecture

```
runtime/                       ← canonical location (NEW)
  db.py                        ← actual code
  context.py                   ← actual code
  model_router.py              ← actual code
  transport/                   ← canonical transport
  substrate/                   ← shim → transport (preserved)
  ...

eos_ai/                        ← compatibility shim (TEMPORARY)
  db.py                        ← from runtime.db import *
  context.py                   ← from runtime.context import *
  model_router.py              ← from runtime.model_router import *
  transport/__init__.py         ← from runtime.transport import *
  substrate/__init__.py         ← from runtime.substrate import *
  runtime/work_state.py         ← from runtime.work_state import *
  runtime/provider_state.py     ← from runtime.provider_state import *
  ...
```

### 3.2 Shim Module Template

```python
# eos_ai/{module}.py — compatibility shim
from runtime.{module} import *  # noqa: F401,F403
```

No deprecation warnings during shim period. Silent re-export only.
Warnings add noise in a solo-founder project with no external consumers.

### 3.3 eos_ai/runtime/ → runtime/ Shim (Special Case)

Current imports: `from eos_ai.runtime.work_state import ...`
New location: `runtime/work_state.py` (flattened)
Shim: `eos_ai/runtime/work_state.py` → `from runtime.work_state import *`

This is a depth change (2 levels → 1 level). The shim handles it.

### 3.4 eos_ai/substrate/ Shim Chain

Current chain: `eos_ai.substrate.X` → `eos_ai.transport.X` (existing shim)
New chain: `eos_ai.substrate.X` → `runtime.transport.X` (updated shim)

The `runtime/substrate/` directory preserves the existing shim behavior
(`runtime.substrate.X` → `runtime.transport.X`), maintaining the same
two-path import surface.

### 3.5 transport/__init__.py Internal References

The 575-line `transport/__init__.py` uses deferred imports like:
```python
("eos_ai.transport.nodes", ["Node", "NodeType", ...])
```

These string-based internal references (inside `_deferred_blocks`) must
be updated to `"runtime.transport.nodes"` during the file migration.
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
5. Remove symlink when `eos_ai/` directory is deleted (R8g)

### 4.3 eos_ai/.env Reference Sites (256 total)

| Category | Count | Migration Wave |
|----------|-------|----------------|
| Docker compose `env_file:` | 3 | R8f (deploy) |
| Shell scripts `source`/`check` | 6 | R8f (deploy) |
| Python `load_dotenv()` | ~20 | R8e (strings) |
| Claude Code skills/commands | 12 | R8f (deploy) |
| Documentation/CLAUDE.md | 10+ | R8f (deploy) |
| Test fixtures | 5 | R8d (tests) |

---

## 5. Import Migration — Complete Site Map

### 5.1 Python Import Sites (2,726 total)

| Consumer | `from eos_ai` | `import eos_ai` | Total | Wave |
|----------|---------------|-----------------|-------|------|
| `eos_ai/` (self) | 1,448 | 2 | 1,450 | R8c (internal) |
| `scripts/` | 470 | 33 | 503 | R8d (scripts) |
| `tests/` | 380 | 4 | 384 | R8d (tests) |
| `services/` | 304 | 0 | 304 | R8d (services) |
| `archive/` | 65 | 0 | 65 | SKIP (frozen) |
| `core/` | 16 | 0 | 16 | R8d (circular dep resolution) |
| `saas/` | 3 | 0 | 3 | R8d (services) |
| `templates/` | 1 | 0 | 1 | R8d (services) |

### 5.2 Non-Python References (789 total)

| Type | Count | Wave |
|------|-------|------|
| `mock.patch("eos_ai.X")` strings | 221 | R8e (strings) |
| Filesystem path refs (`eos_ai/`) | 201 | R8e (strings) |
| Shell script refs | 85 | R8f (deploy) |
| `eos_ai/.env` refs | 256 | R8e + R8f |
| Docker/config refs | 4 | R8f (deploy) |
| `python3 -m eos_ai` | 20 | R8f (deploy) |
| Crontab entries | 2 | R8f (deploy) |

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
or at module level in non-critical paths. During R8d, update them to
`from runtime.X`. The circular dependency is architectural debt but does
not cause import cycles because of lazy import patterns.

**eos_ai/ → core/ (25 imports) — EXPECTED DIRECTION**

These become `runtime/ → core/` imports. No change needed — they're
already the correct dependency direction.

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

### Wave R8b — Create `runtime/` Package + Copy Code (LOW RISK)

**Purpose:** Create the new canonical package with all eos_ai code.

**Actions:**
1. Create `runtime/` directory (no `__init__.py` — implicit namespace, matching eos_ai)
2. Copy all 123 top-level `.py` files from `eos_ai/` to `runtime/`
3. Copy `eos_ai/transport/` → `runtime/transport/` (164 files + `__init__.py`)
4. Copy `eos_ai/substrate/` → `runtime/substrate/` (164 shim files + `__init__.py`)
5. Copy `eos_ai/runtime/work_state.py` → `runtime/work_state.py`
6. Copy `eos_ai/runtime/provider_state.py` → `runtime/provider_state.py`
7. Copy `eos_ai/interfaces/` → `runtime/interfaces/` (2 files)
8. Copy `eos_ai/CLAUDE.md` → `runtime/CLAUDE.md`
9. Copy `eos_ai/README_STATUS.md` → `runtime/README_STATUS.md`
10. **DO NOT update any import statements yet** — both packages coexist

**Verification:**
```bash
python3 -c "import sys; sys.path.insert(0,'/opt/OS'); from runtime.db import get_conn; print('runtime.db: ok')"
python3 -c "import sys; sys.path.insert(0,'/opt/OS'); from runtime.context import load_context_from_env; print('runtime.context: ok')"
python3 -c "import sys; sys.path.insert(0,'/opt/OS'); from eos_ai.db import get_conn; print('eos_ai.db: still ok')"
```

**Files affected:** ~460 files copied (additive)
**Rollback:** `rm -rf runtime/`
**Commit:** `root-migration-r8b: create runtime/ package from eos_ai/ source`

### Wave R8c — Update Internal Self-References (HIGH RISK)

**Purpose:** Make `runtime/` self-consistent — all internal imports
reference `runtime.*` instead of `eos_ai.*`.

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
7. Update `eos_ai/ → core/` refs to `runtime/ → core/` (25 sites, trivial)

**Estimated edits:** ~1,450 import statements across ~300 files

**Verification:**
```bash
# Compile check all runtime/ files
find runtime/ -name '*.py' -exec python3 -m py_compile {} +
# Import check critical modules
python3 -c "from runtime.db import get_conn; print('ok')"
python3 -c "from runtime.model_router import get_router; print('ok')"
python3 -c "from runtime.transport.storage import get_storage; print('ok')"
python3 -c "from runtime.substrate.storage import get_storage; print('ok')"
# Verify no eos_ai refs remain inside runtime/
grep -rn "from eos_ai\|import eos_ai" runtime/ --include='*.py' | wc -l  # expect: 0
```

**Rollback:** `rm -rf runtime/ && git checkout HEAD -- runtime/` (restores
infra/docker version — wait, R8a already moved it. Rollback: `rm -rf runtime/`
then re-copy from eos_ai/)
**Commit:** `root-migration-r8c: update runtime/ internal self-references`

### Wave R8d — Install Compatibility Shims in eos_ai/ (MEDIUM RISK)

**Purpose:** Replace eos_ai/ source files with shims that re-export
from runtime/. All existing `from eos_ai.*` imports continue working.

**Actions:**
1. For each `eos_ai/*.py` (123 files): replace contents with:
   ```python
   from runtime.{module} import *  # noqa: F401,F403
   ```
2. Replace `eos_ai/substrate/__init__.py` with:
   ```python
   from runtime.substrate import *  # noqa: F401,F403
   ```
3. Replace `eos_ai/substrate/*.py` shims (164 files) with:
   ```python
   from runtime.transport.{module} import *  # noqa: F401,F403
   ```
   (Same target as before, but via runtime/ instead of eos_ai.transport)
4. Replace `eos_ai/transport/__init__.py` with:
   ```python
   from runtime.transport import *  # noqa: F401,F403
   ```
5. Replace `eos_ai/transport/*.py` (164 files) with:
   ```python
   from runtime.transport.{module} import *  # noqa: F401,F403
   ```
6. Create `eos_ai/runtime/work_state.py` shim:
   ```python
   from runtime.work_state import *  # noqa: F401,F403
   ```
7. Create `eos_ai/runtime/provider_state.py` shim:
   ```python
   from runtime.provider_state import *  # noqa: F401,F403
   ```
8. Move `eos_ai/.env` → `runtime/.env`, create symlink `eos_ai/.env → runtime/.env`

**Verification — FULL TEST SUITE:**
```bash
cd /opt/OS && python3 -m pytest tests/ -x --tb=short -q
# Expected: 8558 passed, 27 failed (pre-existing), 0 new regressions
```

**Verification — Critical Import Paths:**
```bash
python3 -c "from eos_ai.db import get_conn; print('shim ok')"
python3 -c "from eos_ai.context import load_context_from_env; print('shim ok')"
python3 -c "from eos_ai.substrate.storage import get_storage; print('shim ok')"
python3 -c "from eos_ai.runtime.work_state import detect_work_state; print('shim ok')"
python3 -c "from runtime.db import get_conn; print('canonical ok')"
```

**Files affected:** ~458 shim files + 1 .env move + 1 symlink
**Rollback:** `git checkout HEAD -- eos_ai/`
**Commit:** `root-migration-r8d: install eos_ai/ compatibility shims`

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

Verify: `python3 -c "import services.discord_bot; print('ok')"`

#### R8e-4: core/ (16 imports — circular dep resolution)

Manual update. Each of the 16 sites:
`from eos_ai.X` → `from runtime.X`

Verify: `python3 -c "from core.execution_contract import run_task; print('ok')"`

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

**Careful:** Only replace inside `patch()` / `patch.object()` calls.
The sed above is safe because `"eos_ai.` as a string literal only
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
  -exec grep -l 'eos_ai/' {} + | \
  xargs sed -i 's|eos_ai/|runtime/|g'
```

**Exceptions:** Docstrings and comments that document the migration
itself should NOT be updated (they describe the old state).

#### R8f-4: `eos_ai.runtime.X` → `runtime.X` (depth flattening)

The `eos_ai.runtime.work_state` and `eos_ai.runtime.provider_state`
import paths lose one level. All 16 import sites become:
- `from runtime.work_state import ...`
- `from runtime.provider_state import ...`

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

- `CLAUDE.md`: `eos_ai/.env` → `runtime/.env`
- `.claude/CLAUDE.md`: `eos_ai/` references → `runtime/`
- `services/CLAUDE.md`: `eos_ai/.env` → `runtime/.env`
- `README.md`: `eos_ai/.env` → `runtime/.env`

#### R8g-6: python3 -m invocations (20 sites)

All `python3 -m eos_ai.X` → `python3 -m runtime.X`

**Commit:** `root-migration-r8g: migrate shell, config, and deployment references`

### Wave R8h — Validation + Replay Equivalence (VERIFICATION ONLY)

**Purpose:** Prove that the migration is functionally equivalent.
No code changes — validation and reporting only.

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

#### R8h-5: Circular Dependency Report

```bash
# Verify core/ → runtime/ imports are all lazy (inside function bodies)
grep -rn "from runtime\." --include='*.py' core/ | cat
# Classify each as module-level vs function-level
```

#### R8h-6: Replay Identity Report

```bash
# Verify runtime/ has no remaining eos_ai references
grep -rn "eos_ai" --include='*.py' runtime/ | wc -l
# Expected: 0 (or only in comments documenting the migration)

# Verify eos_ai/ shims all point to runtime/
grep -rn "from runtime\." --include='*.py' eos_ai/ | wc -l
# Should equal number of shim files

# Verify eos_ai/ has NO original code (only shim one-liners)
find eos_ai/ -name '*.py' -exec wc -l {} + | sort -rn | head -10
# Each file should be 1-2 lines
```

**Commit:** `root-migration-r8h: validation and replay equivalence proof`

### Wave R8i — Shim Removal (DEFERRED)

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
```

---

## 7. Risk Matrix

| Wave | Risk | Blast Radius | Rollback Complexity |
|------|------|-------------|---------------------|
| R8a — Relocate runtime/ | LOW | 0 (unused config) | `git mv infra/docker/* runtime/` |
| R8b — Create package | NONE | 0 (additive) | `rm -rf runtime/` |
| R8c — Internal refs | HIGH | runtime/ only | Re-copy from eos_ai/ |
| R8d — Install shims | MEDIUM | All consumers | `git checkout HEAD -- eos_ai/` |
| R8e — External consumers | MEDIUM | tests, scripts, services | `git checkout HEAD -- <dir>` |
| R8f — String refs | MEDIUM | tests (mock.patch) | `git checkout HEAD -- tests/` |
| R8g — Shell/config/deploy | MEDIUM | Deployment | `git checkout HEAD -- <files>` |
| R8h — Validation | NONE | 0 (read-only) | N/A |
| R8i — Shim removal | LOW | None if validated | Restore shims from git |

---

## 8. Execution Constraints

1. **Each wave is an atomic commit** — pass or fail as a unit
2. **Full test suite after R8d** (shim installation is the critical gate)
3. **No Docker restart until R8g** — shims keep current containers working
4. **archive/ is NEVER modified** — dead imports are expected
5. **Stop after R8h** — shim removal (R8i) is a separate approval
6. **Crontab updated last** (R8g-3) — after all Python imports validated

---

## 9. Updated Migration Readiness Matrix

| Wave | Status | Files | Regressions |
|------|--------|-------|-------------|
| R1 — UMH_ROOT env chain | Complete | core/paths.py + env setup | 0 |
| R2 — Runtime bootstrap | Complete | 193 files | 0 |
| R3 — Runtime filesystem refs | Complete | 154 files | 0 |
| R4 — Test topology | Complete | 179 files | 0 |
| R5 — Deployment infrastructure | Complete | 27 files | 0 |
| R6 — Semantic identity | Complete | 8 docs | 0 |
| R7 — Namespace migration plan | Complete | 1 doc | 0 |
| R8a — Relocate runtime/ config | Ready | 12 files | — |
| R8b — Create runtime/ package | Ready | ~460 files | — |
| R8c — Internal self-references | Ready | ~300 files | — |
| R8d — Install eos_ai/ shims | Ready | ~460 files | — |
| R8e — External consumers | Ready | ~400 files | — |
| R8f — String-based refs | Ready | ~100 files | — |
| R8g — Shell/config/deploy | Ready | ~30 files | — |
| R8h — Validation | Ready | 0 (read-only) | — |
| R8i — Shim removal | DEFERRED | ~460 files deleted | — |
