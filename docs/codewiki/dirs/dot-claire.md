---
type: codewiki-dir
dir: .claire
---

# `.claire/` — dead worktree remnant (cleanup candidate)

**0 inventoried files · [Full file inventory](../inventory/dot-claire.md)**

## Purpose
`.claire/` has no live purpose. It is the leftover shell of an abandoned worktree scheme. The directory inventories to **0 durable files** — everything under it lives in the separately-counted excluded category `.claire/worktrees/`, which holds only **3 files**, and all 3 are Python bytecode caches (`__pycache__/*.pyc`), not source.

## How it fits
It fits nowhere in the architecture. It is not referenced by any layer, imported by any module, or read by any service. The name suggests an earlier agent/worktree experiment ("claire") that predates the current `.claude/worktrees/` isolation scheme; what remains is a hollow `worktrees/full-convergence/` tree containing only compiled `.pyc` artifacts under `tests/` and `substrate/ontology/`, with no accompanying `.py` sources.

## Structure

| Path | Contents |
|---|---|
| `.claire/worktrees/full-convergence/tests/__pycache__/` | `test_ontology_enacted.cpython-312.pyc`, `test_registry.cpython-312.pyc` |
| `.claire/worktrees/full-convergence/substrate/ontology/__pycache__/` | `primitives.cpython-312.pyc` |

That is the entire tree — three `cpython-312` bytecode files and their empty parent directories.

## Data & state
No live state. The three `.pyc` files are stale build artifacts (note the `cpython-312` tag — this repo's Docker runtime is Python 3.11, so these caches were produced by a host interpreter, not the deployment target). Nothing writes here at runtime.

## Gotchas
- **Verdict: dead remnant. Flag for cleanup.** This directory can be removed (`rm -rf .claire/`) with no functional impact — it contains zero source, zero config, and zero referenced state. It survives only because git does not track empty dirs and the `.pyc` files were never gitignored/cleaned.
- Do not confuse `.claire/worktrees/` with `.claude/worktrees/`. The latter is the *active* isolation scheme for parallel agents (~440K live files); the former is its defunct predecessor with 3 orphaned caches.
- The presence of `cpython-312` bytecode is itself a smell: it means these were compiled outside the Python 3.11 Docker environment, reinforcing that this tree is off the live execution path.

## See also
- [dot-claude.md](dot-claude.md) — the active worktree/agent scheme that superseded this
- [health-findings.md](../health-findings.md) — consolidated cleanup candidates
