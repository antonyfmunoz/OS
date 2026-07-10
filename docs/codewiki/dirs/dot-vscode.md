---
type: codewiki-dir
dir: .vscode
---

# `.vscode/` — VS Code / code-server editor settings

**1 file · 38 bytes · [Full file inventory](../inventory/dot-vscode.md)**

## Purpose
`.vscode/` holds workspace-scoped editor settings for VS Code and the browser-based code-server the developer uses on the iPad. It is a single tiny `settings.json`. Its only content is one directive:

```json
{
    "git.ignoreLimitWarning": true
}
```

This suppresses VS Code's "too many active changes" warning that would otherwise fire constantly, because this repo's working tree routinely shows thousands of modified/untracked files (JSONL runtime stores in `data/`, agent worktrees, generated artifacts).

## How it fits
Editor tooling only — it is not part of the projections→transports→adapters→substrate stack and imports/exports nothing. It exists purely to make the editor usable against a repo whose working tree is intentionally noisy.

## Structure

| File | Role |
|---|---|
| `.vscode/settings.json` | Sets `git.ignoreLimitWarning: true` — nothing else |

## Data & state
Static config, 38 bytes, no runtime state, no secrets. Committed to the repo so the setting applies uniformly across the developer's devices (VS Code on Windows, code-server on iPad).

## Gotchas
- The single setting is a direct consequence of the repo's design: `data/**` JSONL event stores mutate on every service tick, so the git working tree is expected to have a large, ever-changing diff. That noise is normal, not a problem to "fix" — the setting just stops the editor complaining about it.
- Do not add IDE-specific launch configs, debug profiles, or extension recommendations here without cause; the repo deliberately keeps editor config minimal so it does not diverge across the developer's four devices.

## See also
- [conventions.md](../conventions.md) — repo-wide conventions
- [data.md](data.md) — the JSONL runtime stores that make the working tree noisy
