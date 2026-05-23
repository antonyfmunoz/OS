# UMH Convergence Phase 2: Complete Legacy Elimination

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Eliminate all 324 remaining legacy Python files across 10 directories, leaving only the target architecture: `substrate/`, `adapters/`, `transports/`, `projections/`, `services/` (3 entrypoints only).

**Architecture:** Four-tier attack by dependency coupling. Tier 1 (zero deps) deletes immediately. Tier 2 (minimal deps) moves or absorbs. Tier 3 (medium coupling) rewires imports into substrate. Tier 4 (deep integration) migrates the core persistence and execution layers. Every file either moves into the target architecture or gets deleted.

**Tech Stack:** Python 3.12, Pydantic v2, asyncio, psycopg2 (Neon), substrate types system

**Strategy:** For each legacy module:
1. If it has a substrate equivalent → rewrite importers to use substrate, then delete
2. If it has unique value with no equivalent → move into appropriate target dir, update all imports
3. If it is only imported by other legacy code that will also be deleted → delete together

**Critical constraint:** `transports/discord/bot.py` and `services/discord_bot.py` are the live Discord bot. They import heavily from legacy. Every import rewrite must be verified with `python3 -m py_compile` on these files.

---

## Parallelization Map

```
Tier 1 (Tasks 1-3):     [T1] [T2] [T3]     <- all parallel, zero deps
                              |
Tier 2 (Tasks 4-6):     [T4] [T5] [T6]     <- all parallel after Tier 1
                              |
Tier 3 (Tasks 7-11):    [T7] [T8] [T9] [T10] [T11]  <- parallel after Tier 2
                              |
Tier 4 (Tasks 12-16):   [T12] -> [T13] -> [T14] -> [T15] -> [T16]  <- sequential (shared deps)
```

---

## Tier 1: Zero-Dependency Deletions

### Task 1: Delete `learning/` and `integrations/`

`learning/` is empty. `integrations/` has 15 files but zero imports from target architecture.

**Files:**
- Delete: `learning/` (entire directory)
- Delete: `integrations/` (entire directory, 15 files)

- [ ] **Step 1: Verify zero imports**

```bash
grep -rn "from learning\.\|from integrations\." --include="*.py" substrate/ adapters/ transports/ projections/ services/ | grep -v __pycache__
```

Expected: no output.

- [ ] **Step 2: Delete both directories**

```bash
rm -rf learning/ integrations/
```

- [ ] **Step 3: Verify no broken imports**

```bash
python3 -m py_compile substrate/__init__.py && python3 -m py_compile transports/discord/bot.py && python3 -m py_compile services/discord_bot.py
```

- [ ] **Step 4: Commit**

```bash
git add -A learning/ integrations/
git commit -m "delete learning/ and integrations/ — zero imports, no value to preserve"
```

---

### Task 2: Assess and handle `daemon/`

`daemon/` (14 files) is the Windows node daemon. Zero imports from target arch. Check if `transports/node_mesh/` fully replaces it or if it's a separate Windows-specific deployment artifact.

**Files:**
- Verify: `daemon/` has zero imports from target arch
- Compare: `daemon/umh_node/` vs `transports/node_mesh/`
- Decision: delete if redundant, keep if unique Windows artifact

- [ ] **Step 1: Verify zero imports**

```bash
grep -rn "from daemon\." --include="*.py" substrate/ adapters/ transports/ projections/ services/ | grep -v __pycache__
```

- [ ] **Step 2: Compare with transports/node_mesh**

```bash
diff <(ls daemon/umh_node/*.py | sort) <(ls transports/node_mesh/*.py 2>/dev/null | sort) || true
head -5 daemon/umh_node/service.py
head -5 transports/node_mesh/server.py
```

- [ ] **Step 3: Delete if redundant, keep if unique**

If redundant:
```bash
rm -rf daemon/
git add -A daemon/
git commit -m "delete daemon/ — replaced by transports/node_mesh/"
```

If unique Windows artifact — leave it, no commit needed.

---

### Task 3: Delete `runtime/` compatibility layer

4 files. `runtime/model_router.py` replaced by `adapters/models/model_router.py`. `runtime/ingestion.py` replaced by `substrate/execution/ingestion.py`.

**Files:**
- Delete: `runtime/` (4 files)
- Modify: `transports/api/operator.py` — rewrite imports
- Modify: `services/operator_api.py` — rewrite imports

- [ ] **Step 1: Find all importers**

```bash
grep -rn "from runtime\." --include="*.py" . | grep -v __pycache__ | grep -v "^./runtime/"
```

- [ ] **Step 2: Rewrite imports**

```python
# OLD: from runtime.model_router import call_with_fallback
# NEW: from adapters.models.model_router import call_with_fallback
# OLD: from runtime.ingestion import GenericIngestionOrchestrator
# NEW: from substrate.execution.ingestion import GenericIngestionOrchestrator
```

- [ ] **Step 3: Compile check**

```bash
python3 -m py_compile transports/api/operator.py && python3 -m py_compile services/operator_api.py
```

- [ ] **Step 4: Delete and commit**

```bash
rm -rf runtime/
git add -A runtime/ transports/api/operator.py services/operator_api.py
git commit -m "delete runtime/ — imports rewired to adapters.models and substrate.execution"
```

---

## Tier 2: Low-Coupling Moves

### Task 4: Absorb `composition/` into `substrate/composition/`

44 files. Only 3 imports from target arch (all from `adapters/adapter_engine/`). Contains mastery registries and command registry.

**Files:**
- Move: `composition/` → `substrate/composition/`
- Modify: `adapters/adapter_engine/capability_discovery.py` — rewrite 3 imports
- Modify: all internal imports within moved files

- [ ] **Step 1: Find all importers**

```bash
grep -rn "from composition\." --include="*.py" . | grep -v __pycache__ | grep -v "^./composition/"
```

- [ ] **Step 2: Move files**

```bash
mkdir -p substrate/composition
cp -r composition/registries composition/mastery composition/__init__.py substrate/composition/
```

- [ ] **Step 3: Update all internal imports**

```bash
find substrate/composition/ -name "*.py" -exec sed -i 's/from composition\./from substrate.composition./g' {} +
```

- [ ] **Step 4: Update external importers**

In `adapters/adapter_engine/capability_discovery.py`, replace `from composition.` with `from substrate.composition.`.

- [ ] **Step 5: Compile check, delete old, verify, commit**

```bash
find substrate/composition/ -name "*.py" | xargs -I{} python3 -m py_compile {}
python3 -m py_compile adapters/adapter_engine/capability_discovery.py
rm -rf composition/
grep -rn "from composition\." --include="*.py" . | grep -v __pycache__ | grep -v "^./substrate/composition/"
git add -A composition/ substrate/composition/ adapters/adapter_engine/capability_discovery.py
git commit -m "move composition/ into substrate/composition/"
```

---

### Task 5: Absorb `services/umh/sockets/` into `substrate/sockets/`

11 files. ViewFrame, signal/capability/outcome sockets, integration registry. Substrate infrastructure.

**Files:**
- Move: `services/umh/sockets/` → `substrate/sockets/`
- Modify: `substrate/organism/advisor.py`, `substrate/organism/tests/test_organism_events.py`, `transports/node_mesh/server.py`, `transports/node_mesh/run.py`

- [ ] **Step 1: Find all importers**

```bash
grep -rn "from services\.umh\.sockets\." --include="*.py" . | grep -v __pycache__ | grep -v "^./services/umh/sockets/"
```

- [ ] **Step 2: Move and update internal imports**

```bash
mkdir -p substrate/sockets
cp -r services/umh/sockets/* substrate/sockets/
find substrate/sockets/ -name "*.py" -exec sed -i 's/from services\.umh\.sockets\./from substrate.sockets./g' {} +
```

- [ ] **Step 3: Update external importers**

Replace `from services.umh.sockets.` with `from substrate.sockets.` in all files from Step 1.

- [ ] **Step 4: Compile check, delete old, commit**

```bash
python3 -m py_compile substrate/sockets/envelopes.py
python3 -m py_compile substrate/organism/advisor.py
python3 -m py_compile transports/node_mesh/server.py
rm -rf services/umh/sockets/
git add -A services/umh/sockets/ substrate/sockets/
git commit -m "move services/umh/sockets/ into substrate/sockets/"
```

---

### Task 6: Absorb `services/umh/protocols/` into `substrate/types.py`

14 protocol files defining typed contracts. Merge unique types into `substrate/types.py`, rewrite importers.

**Files:**
- Audit: `services/umh/protocols/` types vs `substrate/types.py`
- Move: unique types into `substrate/types.py`
- Delete: `services/umh/protocols/`

- [ ] **Step 1: Inventory protocol types**

```bash
grep -rn "^class " services/umh/protocols/ --include="*.py" | grep -v __pycache__
grep -rn "^class " substrate/types.py
```

- [ ] **Step 2: Add unique types to substrate/types.py**

- [ ] **Step 3: Find and rewrite all importers**

```bash
grep -rn "from services\.umh\.protocols\." --include="*.py" . | grep -v __pycache__ | grep -v "^./services/umh/protocols/"
```

Change each to `from substrate.types import ...`

- [ ] **Step 4: Delete and commit**

```bash
rm -rf services/umh/protocols/
python3 -m py_compile substrate/types.py
git add -A services/umh/protocols/ substrate/types.py
git commit -m "absorb services/umh/protocols/ into substrate/types.py"
```

---

## Tier 3: Medium-Coupling Migration

### Task 7: Absorb `governance/` into substrate

15 files. Authority engine, policy engine, quality gates, authority tiers, confidentiality.

**Files:**
- Move: `governance/policy/authority_tier.py` → `substrate/ontology/authority_tier.py`
- Move: `governance/policy/authority_engine.py` → `substrate/control_plane/authority.py`
- Move: `governance/quality/quality_gate.py` → `substrate/control_plane/quality_gate.py`
- Move: `governance/policies/confidentiality.py` → `substrate/control_plane/confidentiality.py`
- Delete: remaining governance files
- Modify: 9 importers in adapters/ and transports/

- [ ] **Step 1: Map all importers**

```bash
grep -rn "from governance\." --include="*.py" . | grep -v __pycache__ | grep -v "^./governance/"
```

- [ ] **Step 2: Move valuable files, update internal imports**

- [ ] **Step 3: Rewrite external importers**

Key rewrites:
- `from governance.policy.authority_tier import ...` → `from substrate.ontology.authority_tier import ...`
- `from governance.policy.authority_engine import AuthorityEngine` → `from substrate.control_plane.authority import AuthorityEngine`
- `from governance.quality.quality_gate import ...` → `from substrate.control_plane.quality_gate import ...`
- `from governance.policies.confidentiality import ...` → `from substrate.control_plane.confidentiality import ...`

- [ ] **Step 4: Compile check all modified files (especially bot.py)**

- [ ] **Step 5: Delete governance/, verify, commit**

```bash
rm -rf governance/
grep -rn "from governance\." --include="*.py" . | grep -v __pycache__
git add -A governance/ substrate/
git commit -m "absorb governance/ into substrate"
```

---

### Task 8: Absorb `interface/` into `transports/`

12 files. Discord utilities and presence handlers.

**Files:**
- Move: `interface/discord/discord_utils.py` → `transports/discord/utils.py`
- Move: `interface/presence/handlers/` → `transports/discord/handlers/`
- Modify: `transports/discord/bot.py`, `services/discord_bot.py`, `services/bridge_health.py`, `adapters/google_workspace/gws_scanner.py`

- [ ] **Step 1: Map importers, move files, update internal imports**

- [ ] **Step 2: Rewrite external importers**

- `from interface.discord.discord_utils import ...` → `from transports.discord.utils import ...`
- `from interface.presence.handlers.X import ...` → `from transports.discord.handlers.X import ...`

- [ ] **Step 3: Compile check (bot.py critical), delete, commit**

```bash
rm -rf interface/
git add -A interface/ transports/discord/
git commit -m "absorb interface/ into transports/"
```

---

### Task 9: Absorb `understanding/` into substrate and adapters

45 files. Perception, intelligence, knowledge, ontology decomposition, signals, domains.

**Files:**
- Move: `understanding/perception/` → `substrate/perception/`
- Move: `understanding/ontology/` remaining → `substrate/ontology/decomposition/`
- Move: `understanding/intelligence/` → `adapters/intelligence/`
- Move: `understanding/knowledge/` → `adapters/knowledge/`
- Move: `understanding/signals/` → `substrate/signals/`
- Move: `understanding/domains/` remaining → `substrate/ontology/domains/`
- Modify: 20+ importers

- [ ] **Step 1: Map all importers**

```bash
grep -rn "from understanding\." --include="*.py" . | grep -v __pycache__ | grep -v "^./understanding/"
```

- [ ] **Step 2: Move files to target locations**

- [ ] **Step 3: Update internal + external imports**

- [ ] **Step 4: Compile check all modified files**

- [ ] **Step 5: Delete understanding/, verify, commit**

```bash
rm -rf understanding/
git add -A understanding/ substrate/perception/ substrate/signals/ adapters/intelligence/ adapters/knowledge/
git commit -m "absorb understanding/ into substrate and adapters"
```

---

### Task 10: Absorb `services/umh/` remaining modules

After Tasks 5+6, ~59 files remain: governance (4), control_plane (8), execution (4), model_routing (3), integrations (38), root files.

**Files:**
- Move: `services/umh/governance/` types → `substrate/types.py` or `substrate/control_plane/`
- Move: `services/umh/integrations/` → `projections/` or `adapters/`
- Move: `services/umh/model_routing/` → `adapters/models/`
- Delete: `services/umh/control_plane/` (replaced by substrate)
- Delete: `services/umh/execution/` (replaced by substrate)

- [ ] **Step 1: Map all external importers**

```bash
grep -rn "from services\.umh\." --include="*.py" . | grep -v __pycache__ | grep -v "^./services/umh/"
```

- [ ] **Step 2: Migrate each submodule to target location**

- [ ] **Step 3: Rewrite all importers**

- [ ] **Step 4: Delete services/umh/ entirely**

```bash
rm -rf services/umh/
git add -A services/umh/
git commit -m "eliminate services/umh/"
```

---

### Task 11: Rewire `transports/api/cockpit.py` legacy globals

Cockpit imports `_mesh_server`, `_organism`, `_pipeline` from `services.umh.control_plane.app`. Replace with substrate dependency injection.

**Files:**
- Modify: `transports/api/cockpit.py`

- [ ] **Step 1: Read cockpit and legacy app globals**

- [ ] **Step 2: Replace with substrate equivalents (DI, not globals)**

- [ ] **Step 3: Compile check, commit**

```bash
python3 -m py_compile transports/api/cockpit.py
git add transports/api/cockpit.py
git commit -m "rewire cockpit to substrate instance"
```

---

## Tier 4: Deep Integration Migration

### Task 12: Absorb `state/storage/` and `state/context/` into substrate

Persistence foundation. `get_conn()`, `ORG_ID`, `EntrepreneurOSContext`, `load_context_from_env()`. 20+ importers.

**Files:**
- Move: `state/storage/db.py` → `substrate/persistence/db.py`
- Move: `state/context/context.py` → `substrate/control_plane/boot_context.py`
- Modify: 20+ files

- [ ] **Step 1: Map all importers**

- [ ] **Step 2: Move files**

- [ ] **Step 3: Bulk rewrite importers**

```bash
find . -name "*.py" ! -path "*__pycache__*" ! -path "./state/*" -exec grep -l "from state\.storage\.db\|from state\.context\.context" {} + | while read f; do
    sed -i 's/from state\.storage\.db/from substrate.persistence.db/g' "$f"
    sed -i 's/from state\.context\.context/from substrate.control_plane.boot_context/g' "$f"
done
```

- [ ] **Step 4: Compile check, commit**

---

### Task 13: Absorb `state/memory/` and `state/business/` into substrate

Memory and business state.

**Files:**
- Move: `state/memory/` → `substrate/persistence/memory/`
- Move: `state/business/` → `substrate/control_plane/`
- Modify: all importers

- [ ] **Step 1-4: Map, move, rewrite, compile, commit** (same pattern as Task 12)

---

### Task 14: Absorb remaining `state/` and delete

stores/, registries/, metrics/, finance/, lifecycle/, logs/, permissions/, preferences/, profiles/, providers/, session/, tenancy/, work/.

**Files:**
- Move: `state/stores/` → `substrate/persistence/stores/`
- Move: `state/registries/` → `substrate/persistence/registries/`
- Move: remaining → `substrate/persistence/` by category
- Delete: `state/` entirely

- [ ] **Step 1: Map remaining importers**

- [ ] **Step 2: Move, rewrite, compile**

- [ ] **Step 3: Delete state/ entirely, verify zero remaining imports**

- [ ] **Step 4: Commit**

---

### Task 15: Absorb `control_plane/` and `execution/`

195 files — the largest task. Break into sub-steps at execution time.

**Strategy:**
- Modules with substrate equivalents → rewrite importers, delete
- Modules with unique value (agents, scheduling, strategy, transport) → move to target arch
- `transports/discord/bot.py` has 20+ imports from these — compile-check after every batch

**Files:**
- Move: `control_plane/agents/` → `substrate/control_plane/agents/`
- Move: `control_plane/scheduling/` → `substrate/control_plane/scheduling/`
- Move: `control_plane/strategy/` → `substrate/control_plane/strategy/`
- Move: `control_plane/delegation/` → `substrate/control_plane/delegation/`
- Move: `control_plane/events/` → `substrate/control_plane/events/`
- Move: `control_plane/coordination/` → `substrate/control_plane/coordination/`
- Move: `control_plane/onboarding/` → `substrate/control_plane/onboarding/`
- Move: `control_plane/runtime/gateway.py` → keep as compatibility (bot depends on it)
- Move: `execution/runtime/agent_runtime.py` → `adapters/models/legacy_agent_runtime.py`
- Move: `execution/transport/` valuable modules → `transports/` or `adapters/`
- Delete: everything with substrate replacements
- Delete: `control_plane/` and `execution/` entirely

- [ ] **Step 1: Map ALL importers from both dirs**

- [ ] **Step 2: Categorize (replace/move/delete-together)**

- [ ] **Step 3: Move valuable modules**

- [ ] **Step 4: Rewrite ALL importers (bot.py is critical)**

- [ ] **Step 5: Compile check after every batch**

- [ ] **Step 6: Delete both dirs, verify zero remaining imports**

- [ ] **Step 7: Commit**

```bash
git add -A control_plane/ execution/ substrate/ adapters/ transports/
git commit -m "eliminate control_plane/ and execution/"
```

---

### Task 16: Final verification and cleanup

- [ ] **Step 1: Verify no legacy directories remain**

```bash
for dir in execution control_plane state interface understanding governance composition integrations learning runtime services/umh; do
    if [ -d "$dir" ]; then echo "STILL EXISTS: $dir"; else echo "DELETED: $dir"; fi
done
```

- [ ] **Step 2: Verify no legacy imports remain**

```bash
grep -rn "from \(execution\|control_plane\|state\|interface\|understanding\|governance\|composition\|integrations\|learning\|runtime\)\." --include="*.py" . | grep -v __pycache__ | grep -v "^./substrate/" | grep -v "^./adapters/" | grep -v "^./transports/" | grep -v "^./projections/"
```

- [ ] **Step 3: Compile check all entry points**

```bash
python3 -m py_compile substrate/__init__.py
python3 -m py_compile transports/discord/bot.py
python3 -m py_compile services/discord_bot.py
python3 -m py_compile services/operator_api.py
python3 -m py_compile adapters/models/model_router.py
```

- [ ] **Step 4: Run full test suite**

```bash
python3 -m pytest tests/ substrate/organism/tests/ -v --no-header
```

- [ ] **Step 5: Count final architecture**

```bash
for dir in substrate adapters transports projections services; do
    count=$(find $dir -name "*.py" ! -path "*__pycache__*" | wc -l)
    echo "$dir: $count files"
done
echo "Legacy: $(find . -name '*.py' ! -path '*__pycache__*' ! -path './.git/*' ! -path './venv/*' ! -path './data/*' ! -path './scripts/*' ! -path './tests/*' ! -path './skills/*' ! -path './saas/*' ! -path './.claude/*' ! -path './substrate/*' ! -path './adapters/*' ! -path './transports/*' ! -path './projections/*' ! -path './services/*' ! -path './daemon/*' | wc -l)"
```

Expected: Legacy = 0.

- [ ] **Step 6: Update CLAUDE.md project structure**

- [ ] **Step 7: Rebuild codebase graph**

```bash
scripts/update-graph
```

- [ ] **Step 8: Final commit**

```bash
git add -A
git commit -m "convergence complete: all legacy eliminated, one coherent substrate architecture"
```
