---
type: codewiki-inventory
dir: _census
source_sha: 70deadbac8667755a38ac49595afd09afc209c2f
---

# Repository Census — Full Accounting

Raw total (regular files, no excludes): **719,408**

| Category | Regular files | Symlinks |
|---|---|---|
| Inventoried per-file (code + skills) | 4,605 | 37 |
| Rolled up (runtime data) | 258,314 | 2 |
| Excluded categories (counted below) | 456,489 | 757 |
| **Accounted total** | **719,408** | **796** |

## Per-directory census

| Directory | Treatment | Files | Symlinks | Bytes |
|---|---|---|---|---|
| [`logs`](logs.md) | rollup | 213,108 | 1 | 346,952,117 |
| [`data`](data.md) | rollup | 42,112 | 1 | 38,468,993,893 |
| [`vault`](vault.md) | rollup | 2,929 | 0 | 15,832,279 |
| [`substrate`](substrate.md) | code | 1,009 | 0 | 12,452,560 |
| [`docs`](docs.md) | code | 738 | 0 | 7,383,636 |
| [`skills`](skills.md) | skill | 466 | 16 | 6,794,042 |
| [`tests`](tests.md) | code | 449 | 0 | 6,622,193 |
| [`cockpit`](cockpit.md) | code | 431 | 0 | 4,598,832 |
| [`knowledge`](knowledge.md) | code | 344 | 3 | 522,787 |
| [`transports`](transports.md) | code | 221 | 0 | 2,047,311 |
| [`scripts`](scripts.md) | code | 215 | 0 | 9,982,132 |
| [`.agents`](dot-agents.md) | code | 183 | 0 | 3,024,145 |
| [`.playwright-mcp`](dot-playwright-mcp.md) | rollup | 162 | 0 | 30,269,065 |
| [`.claude`](dot-claude.md) | code | 157 | 18 | 2,237,329 |
| [`adapters`](adapters.md) | code | 101 | 0 | 780,940 |
| [`projections`](projections.md) | code | 69 | 0 | 529,495 |
| [`nodes`](nodes.md) | code | 58 | 0 | 393,902 |
| [`services`](services.md) | code | 43 | 0 | 726,549 |
| [`.planning`](dot-planning.md) | code | 39 | 0 | 348,539 |
| [`_root-files`](_root-files.md) | code | 35 | 0 | 250,428 |
| [`infra`](infra.md) | code | 19 | 0 | 60,510 |
| [`agents`](agents.md) | code | 11 | 0 | 50,436 |
| [`.obsidian`](dot-obsidian.md) | code | 8 | 0 | 2,613 |
| [`docker`](docker.md) | code | 3 | 0 | 1,832 |
| [`umh`](umh.md) | code | 3 | 0 | 139,588 |
| [`runtime`](runtime.md) | rollup | 2 | 0 | 48,428,136 |
| [`.github`](dot-github.md) | code | 1 | 0 | 2,680 |
| [`.vscode`](dot-vscode.md) | code | 1 | 0 | 38 |
| [`config`](config.md) | code | 1 | 0 | 7,862 |
| [`graphify-out`](graphify-out.md) | rollup | 1 | 0 | 43,661,207 |
| [`.claire`](dot-claire.md) | code | 0 | 0 | 0 |
| [`media`](media.md) | rollup | 0 | 0 | 0 |
| [`saas`](saas.md) | code | 0 | 0 | 0 |

## Excluded categories (counted, not inventoried)

| Category | Files | Symlinks | Bytes |
|---|---|---|---|
| `.claire/worktrees` | 3 | 0 | 10,774 |
| `.claude/worktrees` | 439,872 | 733 | 10,242,273,921 |
| `.git` | 3,223 | 1 | 201,627,619 |
| `.mypy_cache` | 18 | 0 | 23,539,936 |
| `.pytest_cache` | 5 | 0 | 5,197,536 |
| `.ruff_cache` | 82 | 0 | 143,333 |
| `__pycache__` | 2,982 | 0 | 61,025,083 |
| `cockpit/dist` | 12 | 0 | 3,592,173 |
| `cockpit/dist-web` | 875 | 0 | 23,305,957 |
| `cockpit/out` | 6 | 0 | 2,031,232 |
| `node_modules` | 9,411 | 23 | 228,797,798 |
