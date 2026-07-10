---
type: codewiki-dir
dir: .claude
---

# `.claude/` — Claude Code project configuration, laws, agents, and skills

**157 files + 18 symlinks · 2,237,329 bytes · [Full file inventory](../inventory/dot-claude.md)**

> The count above **excludes** `.claude/worktrees/`, which is a separately-counted excluded category: 30+ transient agent worktrees holding ~439,792 files and ~10.2 GB. Those are ephemeral isolated repo copies created for parallel background jobs (this very page is being written inside one), auto-cleaned when unchanged. Nothing durable lives there; treat it as scratch.

## Purpose
`.claude/` is the control surface for how Claude Code operates on this repository. It is not application code — it is the *operating contract* between the human developer and the Developer Agent: which model to run, what hooks fire on every tool use, the non-negotiable architectural laws the agent must obey, the CC-native subagents it can delegate to, the slash commands it exposes, and the skill library it loads on demand. Where `/opt/OS/CLAUDE.md` is the soul document, `.claude/` is the machinery that enforces it.

## How it fits
This directory sits *outside* the four-layer architecture (projections → transports → adapters → substrate) — it governs the tooling that edits those layers rather than participating in them. Its `rules/` files are the source of truth for the layer laws that the pre-commit gates in `scripts/` enforce; the narrative here mirrors laws that live in code as `scripts/check_*.py`. `hooks/validate_change.py` runs as a PreToolUse gate on every Edit/Write, and `settings.json` wires the full hook lifecycle.

## Structure

| Subdir / file | Role |
|---|---|
| `agents/` | 4 CC-native subagents (isolated-context reviewers/verifiers) |
| `commands/` | 24 slash commands (EOS workflows, sync, deploy, outreach) |
| `hooks/` | 1 pre-tool-use validation hook (`validate_change.py`) |
| `rules/` | 13 project-law files — the enforced architectural contract |
| `skills/` | 33 top-level entries (14 real `.md` skills, 18 symlinks into `.agents/skills/`, plus the bundled `impeccable/` design toolkit) |
| `CLAUDE.md` | The `.claude`-specific context doc (risk classes, component status, session protocols) |
| `settings.json` | Project settings — model pin (`opus`), full hook lifecycle, permissions, statusline |
| `settings.local.json` | Machine-local settings overrides (27 lines, gitignored-style) |

## Key components

**`agents/` — 4 CC subagents**, each isolated-context and adversarial by design:
- `eos-code-reviewer.md` — senior-staff adversarial review after any change (security, anti-patterns, regressions)
- `eos-researcher.md` — web-research agent for ICP/market/competitor intel
- `eos-simplifier.md` — post-implementation reuse/efficiency pass
- `eos-verifier.md` — runs imports and validates behavior; the Boris Cherny "give Claude a way to verify" step

**`commands/` — 24 slash commands**: `babysit`, `browser-task`, `commit-push-pr`, `constraint-check`, `council`, `deploy`, `eod-sync`, `eos-audit`, `eos-build`, `eos-deploy`, `eos-fix`, `eos-sync`, `morning-brief`, `primitive-check`, `run-outreach`, `session-start`, `start-loops`, `status`, `test-agent`, `test-all-agents`, `test-all`, `update-skills`, `use-opusplan`, `voice-debug`.

**`rules/` — 13 laws** (each enforced by a matching `scripts/check_*.py` pre-commit gate where noted):
- `architecture-layers.md` — one-way downward dependency direction (projections→transports→adapters→substrate)
- `projection-boundary.md` — substrate stays projection-agnostic; apps register at runtime via `substrate/sockets/`
- `ontology-layers.md` — L1 reality / L2 metamodel / L3 domain / L4 bridge; L2 never imports L3
- `type-coherence.md` — check `substrate/canonical_types.py` before defining any new type; no parallel type systems
- `instance-context.md` — no tenant/founder/AI-name literals in `substrate/`; resolve at runtime
- `credential-injection.md` — all computer-use secrets flow through 1Password `op run`, never plaintext CLI args
- `browser-verification.md` — browser evidence only on executor-roled nodes with a real display, never the headless orchestrator
- `device-naming.md` — device display names come from `infra/device_registry.json`, never hardcoded strings
- `client-failure-observability.md` — when a failure never reaches the server, instrument the client before the second fix
- `projection-read-surfaces.md` — the one legal shape for projection read-only HTTP endpoints (`/eos/activation` reference)
- `python.md` — Python 3.11+ syntax, psycopg2/Neon, ruff, no silent excepts
- `skills.md` — every SKILL.md needs a trigger-condition description + Gotchas section
- `agents.md` — soul docs carry character only; CC subagents carry mechanics + a verification step

**`hooks/validate_change.py`** (114 lines) — PreToolUse gate that inspects Edit/Write calls before they land. **`settings.json`** pins `model: opus` and wires the complete hook lifecycle: `PreToolUse`, `PostToolUse`, `PreCompact`/`PostCompact`, `SessionStart`, `Stop`, `PostToolUseFailure`, `TaskCreated`/`TaskCompleted`, `PermissionRequest`, `SubagentStart`, `UserPromptSubmit`.

**`skills/impeccable/`** is the single largest resident: a self-contained frontend design toolkit (SKILL.md + a deep `reference/` and `scripts/detector/` tree, e.g. `live-browser.js` at 11,173 lines) that accounts for most of the directory's byte weight.

## Data & state
Reads/writes are configuration-only: `settings.json` / `settings.local.json` (JSON config), `last_cc_version` (a marker file tracking the last-seen CLI version), and `scheduled_tasks.lock` (a lockfile enforcing single-run semantics for scheduled tasks). The 18 symlinks under `skills/` point outward to `../../.agents/skills/` — the shared skill store — so those skill bodies physically live in `.agents/`, not here.

## Gotchas
- **`worktrees/` is not part of the 157-file count and must never be edited as if durable.** It holds live isolated copies used by parallel background agents. CLAUDE.md's law is explicit: executors write and branch **only** in their own isolated worktree, never in the shared `/opt/OS` checkout, because containers volume-mount the live tree as their file source.
- The 13 `rules/` files are the *documentation* of the laws; the *enforcement* is the `scripts/check_*.py` pre-commit hooks. If you change a rule's intent, you must update its gate — the two can drift, and a stale rule with a live gate (or vice-versa) is a real hazard.
- `skills/` shows 110 files in the raw inventory but **33 top-level entries** — the inflation is the nested `impeccable/` tree. When counting "skills," count top-level entries.
- CC subagents in `agents/` and skills in `skills/` serve different layers and must never duplicate content (per `rules/agents.md`): soul = character, subagent = mechanics.

## See also
- [dot-agents.md](dot-agents.md) — the real home of the symlinked skills
- [dot-planning.md](dot-planning.md) — GSD planning workspace
- [scripts.md](scripts.md) — the `check_*.py` pre-commit gates that enforce these rules
- [conventions.md](../conventions.md) · [architecture.md](../architecture.md)
