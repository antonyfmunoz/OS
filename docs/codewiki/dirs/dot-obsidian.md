---
type: codewiki-dir
dir: .obsidian
---

# `.obsidian/` — Obsidian vault config that makes `knowledge/` + `docs/` browsable

**8 files · 2,613 bytes · [Full file inventory](../inventory/dot-obsidian.md)**

## Purpose
`.obsidian/` is the configuration for treating the whole `/opt/OS` repo as an
Obsidian vault. It exists so the LLM-maintained CANON wiki (`knowledge/`) and the
CORPUS reference tree (`docs/`) can be navigated as a linked note graph — with
backlinks, `[[wikilink]]` resolution, a visual graph view, tags, daily notes, and
task/dataview queries — rather than as flat files. It carries no code and no
knowledge content; it is eight small JSON files (2,613 bytes total) that turn the
`WIKI_RULES.md` linking discipline into a working, clickable vault.

## How it fits
Not a code layer — nothing imports it, it imports nothing. It is the human/LLM
reading surface for the two documentation trees: `knowledge/` uses Obsidian
`[[wikilinks]]` by rule (`WIKI_RULES.md`), and this config is what resolves those
links, renders the backlink pane, and draws the graph. The vault root spans the
repo's numbered PARA-style folders (referenced by the configs below:
`01_Inbox`, `02_Daily`, `06_Skills`, `12_Templates`) plus `knowledge/` and
`docs/`.

## Structure
| File | Lines | Role |
|---|---|---|
| `app.json` | 5 | Core app behavior: `promptDelete: false`, `openBehavior: "daily"`, `alwaysUpdateLinks: true` (auto-rewrite links on file move) |
| `appearance.json` | 1 | Empty `{}` — default theme/appearance (no committed customization) |
| `core-plugins.json` | 33 | Toggles for built-in plugins: graph, backlink, canvas, outgoing-link, tag-pane, daily-notes, templates, properties, sync, bases all on; slides/audio-recorder/publish/webviewer off |
| `community-plugins.json` | 7 | Enabled community plugins: `dataview`, `obsidian-kanban`, `obsidian-tasks-plugin`, `templater-obsidian`, `obsidian-git` |
| `graph.json` | 22 | Graph-view tuning: shows orphans, hides tags/attachments, `repelStrength: 10`, `linkDistance: 250` |
| `daily-notes.json` | 5 | Daily notes → `02_Daily`, format `dddd MMMM Do YYYY`, template `12_Templates/Daily Note Properties` |
| `templates.json` | 5 | Templates folder `12_Templates`, date/time format config |
| `types.json` | 30 | Property type map: `aliases`, `tags`, `date`, plus a large `TQ_*` set of checkbox/text types for the Tasks plugin's query toolbar |

## Key components
- `community-plugins.json` is the most load-bearing: it declares that the vault
  depends on **dataview** (live queries over frontmatter — the mechanism the CANON
  dashboards use instead of a manual Related section), **obsidian-tasks-plugin**
  (the `TQ_*` types in `types.json` are its toolbar toggles),
  **templater-obsidian** (dynamic templates), **obsidian-kanban**, and
  **obsidian-git** (which lets vault edits sync through the repo's normal git
  flow — consistent with `CLAUDE.md`'s GitHub-as-sync-layer model).
- `daily-notes.json` + `templates.json` point at `02_Daily` and `12_Templates`,
  showing the vault is scoped to the numbered PARA folders as well as
  `knowledge/`/`docs/`.
- `core-plugins.json` enabling `backlink`, `outgoing-link`, and `graph` is what
  operationalizes `WIKI_RULES.md`'s rule that CANON pages should carry incoming
  links — those links are only navigable because these plugins are on.

## Data & state
Pure JSON config; reads/writes nothing at runtime. `sync: true` in
`core-plugins.json` references Obsidian Sync, but the committed
`community-plugins.json` shows `obsidian-git` as the actual sync path in this
repo. No secrets, tokens, or credentials are present in any of the eight files.

## Gotchas
- **`appearance.json` is empty (`{}`)** — the vault ships with no theme override;
  it renders in whatever the local Obsidian default is. Not a bug, just bare.
- **Community plugins must be installed locally.** `community-plugins.json` only
  lists which plugins are *enabled*; the plugin code itself is not vaulted here.
  A fresh Obsidian install pointed at this repo will show the config but must
  fetch dataview/tasks/templater/kanban/git before the vault renders as intended.
- **`alwaysUpdateLinks: true` will rewrite links on move.** Moving a note inside
  Obsidian auto-updates `[[wikilinks]]` — convenient, but a rename done outside
  Obsidian (e.g. via git/editor) will not, so the two paths can diverge.
- **Vault scope is repo-wide.** Because the vault root is `/opt/OS`, the graph view
  includes far more than `knowledge/` — this is intended (docs + inbox + daily),
  but explains why `graph.json` sets `showOrphans: true` and a high `repelStrength`
  to keep a large node set legible.

## See also
- [`knowledge/`](knowledge.md) — the CANON wiki this vault is built to navigate
- [`docs/`](docs.md) — the CORPUS reference tree also inside the vault
- [Conventions](../conventions.md) · [Index](../index.md)
