---
type: codewiki-dir
dir: tests
---

# `tests/` — the pytest suite: campaign regressions, gate enforcement, and law tests

**449 files · 6,622,193 bytes · [Full file inventory](../inventory/tests.md)**

## Purpose
`tests/` is the whole-system pytest suite. It is dominated by a large flat mass of
per-campaign and per-phase regression suites (`test_c<NN>_*.py`,
`test_phase<NN>_*.py`, `test_p<N>_*.py`, `test_gate<N>_*.py`) that pin the behavior
of every runtime built during UMH's campaign era, plus a smaller set of **law
tests** that mechanically defend the architecture contracts, and structural unit
tests under `substrate/`, `adapters/`, `certification/`, and `fixtures/`. This is
the primary verification surface CLAUDE.md's Completion Standards demand you run
before claiming any work done.

## How it fits
`tests/` sits outside the four-layer stack — it imports freely across
projections → transports → adapters → substrate to exercise them. Tests are
collected under the `pytest.ini_options` config in the root `pyproject.toml`
(`testpaths = ["tests"]`, `pythonpath = ["."]`, `asyncio_mode = "auto"`), so
there is **no `pytest.ini`** — the config is in `pyproject.toml`. Several law
tests here are the runtime half of the pre-commit gates in
[`scripts/`](scripts.md): the gate blocks new violations at commit time, the test
caps the existing debt and forbids growth.

## Structure

| Subdir | Files | Role |
|---|---|---|
| `tests/` (root) | ~427 | The flat mass: campaign, phase, gate, and law suites — 424 `test_*.py` files |
| `tests/adapters/` | 5 | Adapter-layer units, notably `broadcast/` (filtergraph builder, node dispatch, process lifecycle) |
| `tests/certification/` | 7 | Production certification suites (C28 Cockpit Supremacy, C29 Harness Superiority benchmark/evidence/report) |
| `tests/fixtures/` | 6 | Test assets: `ingestion_fixture.md` (canary-tagged), synthetic voice fixtures (`.wav` tones, mp4 marker, generator) |
| `tests/substrate/` | 4 | Substrate units: `test_entity_store.py`, `test_feedback_loop.py`, `test_types.py` |

The root also contains `conftest.py` and exactly one non-`test_`-prefixed file,
`phase13_2_runtime_proofs.py` (631 lines) — a standalone `sys.exit()`-style proof
script, not a pytest module.

## Key components

### Collection guard — `tests/conftest.py`
The root conftest does two load-bearing things: (1) imports
`substrate.execution.bridge` before collection so the implicit namespace package
resolves, and (2) `pytest_ignore_collect` **skips standalone script-style test
files** — any `test_*.py` that calls `sys.exit()` but defines no `def test_`
function is ignored, so proof scripts that end in `sys.exit(0/1)` don't crash
collection. This is why `phase13_2_runtime_proofs.py` (which uses `sys.exit`) is
deliberately named *without* the `test_` prefix and never collected.

### The campaign / phase mass
The bulk of the suite is per-campaign and per-phase regression coverage. Roughly:
- **Campaigns** `test_c16`–`test_c40b` and `test_c<N.M>_*` — the governed
  execution loop, voice/vision runtimes (C20/C21), the Software Production
  Organism (C22), benchmark layers (C23A/B), the qualification campaigns
  (C34–C40B). Per the roadmap, C34–C40B are **retired**; their suites remain as
  historical regression pins.
- **Phases** `test_phase5`–`test_phase35`, `test_phase9_5`–`test_phase14_18c`,
  `test_p1_*`–`test_p4s31*` — the P1 core-workflow, P2 capability, P3
  productization, and P4S surface-slice roadmap phases. The largest single files
  are canon-reconstruction suites: `test_phase14_6b_umh_code_resolved_canon.py`
  (1,816 lines), `test_phase14_6b_lyfeos_code_resolved_canon.py` (1,652),
  `test_phase14_6b_eos_lossless_canon.py` (1,398), and
  `test_phase9_8_production_truth.py` (1,859).
- **Gates** `test_gate3`–`test_gate10` — the MVP governed-work / intent /
  capability / operationalization / infrastructure / execution-graph / compounding
  runtime gates.

### Law / contract tests (the enforcement half)
These pin the architecture laws and pair with `scripts/` pre-commit gates:
- `test_type_divergence.py` (157) — the type-coherence system.
  `test_full_codebase_scan_no_growth` is the **shrink-only cap** on pre-existing
  type-divergence debt (may only shrink, never grow).
- `test_single_spine_architecture.py` (173) — WP-P1-001: exactly one canonical
  governed operation runtime.
- `test_governed_mutation_fail_closed.py` (416) — WP-P0-001: `governed_mutation()`
  is fail-closed.
- `test_ontology_layer_contract.py` (191) + `test_ontology_home_map.py` (287) —
  the L2/L3 ontology-layer contract and the frozen ontology-home map (Gates 11/13).
- `test_projection_read_surface_discipline.py` (181) — the projection read-surface
  discipline, holding a **shrink-only allowlist** of the five sanctioned legacy
  `/eos/*` routes; new routes must conform and are not added to the list.
- `test_projection_source_truth.py` (117), `test_registry_truthfulness.py` (91),
  `test_risk_taxonomy_canonical.py` (156), `test_secrets_runtime_protocol.py`
  (179), `test_mesh_auth_binding.py` (154), `test_eos_tenant_isolation.py` (119).
- `test_voice_runtime_divergence.py` (78) + `test_canonical_voice_runtime.py` (53)
  + `test_voice_error_codes_ts_mirror.py` (48) — the Gate-14 voice convergence
  regressions (single voice runtime, TS↔Python error-code parity).

### Fast lane — smoke tests
`test_p0_smoke.py` (177) is marked `pytest.mark.smoke` (module-level
`pytestmark`): fast import/health checks for every production service. Run the
fast lane with `pytest tests/test_p0_smoke.py -m smoke`. The `smoke` and
`integration` markers are the two registered in `pyproject.toml`
(`integration` = hits real external services/data; deselect with
`-m "not integration"`).

### Certification (Beast-dependent, slow)
`tests/certification/` runs the C28/C29 production certification suites. Several
of these (`c28_panel_audit.py`, `c28_task_acceptance.py`, `c29_evidence.py`) are
documented to run **ON Beast with a real Playwright display** — per the
[Browser Verification Law](../../../.claude/rules/browser-verification.md), real
browser evidence never runs on the headless orchestrator. These are the slowest,
most environment-dependent suites and are not part of a normal fast run.

## Data & state
- **Reads** fixtures under `tests/fixtures/`: `ingestion_fixture.md` (carries a
  canary token to prove ingestion round-trips), synthetic `.wav` voice tones,
  and an iOS mp4 marker for the STT pipeline.
- Most runtime tests use in-memory/temp stores; integration-marked tests hit real
  Neon / external services and are deselected in offline runs.
- `asyncio_mode = "auto"` means async test functions run without explicit
  `@pytest.mark.asyncio` decoration.

## Gotchas
- **`test_type_divergence.py` hardcodes `sys.path.insert(0, "/opt/OS")` at line 6.**
  This is the known path gotcha: the type-divergence *scan* logic was made
  worktree-aware (the old hard-coded `/opt/OS` scan root was replaced — see the
  comment at line 103), but the module still pins `sys.path` to `/opt/OS`, so
  running the suite from a worktree resolves imports against the **main checkout**,
  not the worktree copy. Sync main before relying on a combined-worktree run of
  this test.
- **The Makefile `test-migration` / `test-migration-offline` targets are dead.**
  They run `pytest tests/migration/`, but **`tests/migration/` does not exist** in
  the tree. `test-migration-offline` also filters on `-m "not external and not
  llm"` markers that are **not registered** in `pyproject.toml` (only `smoke` and
  `integration` are). These are stale Makefile targets.
- **Script-style proofs are silently un-collected.** A file that uses `sys.exit()`
  and defines no `def test_` is skipped by `conftest.py`. If you expect a proof to
  run under pytest, give it a real `def test_` function — otherwise it is invisible
  to the suite (this is why `phase13_2_runtime_proofs.py` drops the `test_` prefix).
- **Certification suites need Beast + a display.** Do not run
  `tests/certification/c2*_*` browser suites on the orchestrator — they produce
  false-positive evidence headless (Browser Verification Law).
- **Campaign suites (C34–C40B) are retired runtime** but live regression pins.
  Failures there reflect changes to frozen historical code paths, not active
  roadmap work.

## How to run
- Full suite: `pytest` (config auto-loaded from `pyproject.toml`; `testpaths=tests`).
- Fast lane: `pytest tests/test_p0_smoke.py -m smoke`.
- Offline / no external services: `pytest -m "not integration"`.
- The pre-commit `check_pytest_collection.py` gate (Gate 10) blocks any commit
  that breaks collection, so a green collection is a merge precondition.

## See also
- [`scripts/` — the gates these law tests pair with](scripts.md)
- [`substrate/` — the platform under test](substrate.md) · [`adapters/`](adapters.md)
- [Architecture](../architecture.md) · [Conventions](../conventions.md)
- [Health findings](../health-findings.md) · [Audit 2026-07-10](../audit-2026-07-10.md)
- [Full file inventory](../inventory/tests.md)
