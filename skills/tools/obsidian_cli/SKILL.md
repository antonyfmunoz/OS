---
name: obsidian_cli
description: "Use when interacting with Obsidian vaults via CLI — reading, creating, searching notes, managing tasks/properties, developing plugins, or debugging themes."
allowed-tools: "Read, Bash"
version: 1.0
source_url: "https://help.obsidian.md/cli"
last_researched: "2026-04-28"
api_version: "Obsidian CLI 1.0+"
speed_category: "slow"
trigger: both
effort: medium
context: fork
---

# Tool: Obsidian CLI

## What This Tool Does

The `obsidian` CLI interacts with a running Obsidian instance from the command line. It requires Obsidian to be open. Capabilities include:

- **Note CRUD** — read, create, append, prepend, overwrite notes
- **Search** — full-text and property-based search across the vault
- **Daily notes** — read, append, prepend to the daily note
- **Properties** — get, set, remove YAML frontmatter properties
- **Tasks** — list tasks from notes or daily note, filter by status
- **Tags** — list all tags with counts and sorting
- **Backlinks** — list incoming links for any note
- **Plugin development** — reload plugins, run JS eval, inspect DOM, capture errors, take screenshots, check console, inspect CSS, toggle mobile emulation
- **Vault targeting** — operate on any open vault by name

Run `obsidian help` to see all available commands. This is always the authoritative, up-to-date reference.

## EOS Integration

EOS uses Obsidian as the vault layer for wiki content at `/opt/OS/knowledge/`. The CLI enables:

- Automated note creation and updates from EOS agents
- Search and retrieval for the knowledge retrieval hierarchy
- Task management integrated with daily operations
- Backlink auditing for wiki health checks

## Quick Reference

### Syntax

**Parameters** take a value with `=`. Quote values with spaces:

```bash
obsidian create name="My Note" content="Hello world"
```

**Flags** are boolean switches with no value:

```bash
obsidian create name="My Note" silent overwrite
```

For multiline content use `\n` for newline and `\t` for tab.

### File targeting

Many commands accept `file` or `path` to target a file. Without either, the active file is used.

- `file=<name>` — resolves like a wikilink (name only, no path or extension needed)
- `path=<path>` — exact path from vault root, e.g. `folder/note.md`

### Vault targeting

Commands target the most recently focused vault by default. Use `vault=<name>` as the first parameter to target a specific vault:

```bash
obsidian vault="My Vault" search query="test"
```

### Common patterns

```bash
obsidian read file="My Note"
obsidian create name="New Note" content="# Hello" template="Template" silent
obsidian append file="My Note" content="New line"
obsidian search query="search term" limit=10
obsidian daily:read
obsidian daily:append content="- [ ] New task"
obsidian property:set name="status" value="done" file="My Note"
obsidian tasks daily todo
obsidian tags sort=count counts
obsidian backlinks file="My Note"
```

Use `--copy` on any command to copy output to clipboard. Use `silent` to prevent files from opening. Use `total` on list commands to get a count.

### Plugin development workflow

After making code changes to a plugin or theme:

1. **Reload** the plugin to pick up changes:
   ```bash
   obsidian plugin:reload id=my-plugin
   ```
2. **Check for errors** — if errors appear, fix and repeat from step 1:
   ```bash
   obsidian dev:errors
   ```
3. **Verify visually** with a screenshot or DOM inspection:
   ```bash
   obsidian dev:screenshot path=screenshot.png
   obsidian dev:dom selector=".workspace-leaf" text
   ```
4. **Check console output** for warnings or unexpected logs:
   ```bash
   obsidian dev:console level=error
   ```

### Additional developer commands

Run JavaScript in the app context:

```bash
obsidian eval code="app.vault.getFiles().length"
```

Inspect CSS values:

```bash
obsidian dev:css selector=".workspace-leaf" prop=background-color
```

Toggle mobile emulation:

```bash
obsidian dev:mobile on
```

Run `obsidian help` to see additional developer commands including CDP and debugger controls.

## Gotchas

- **Obsidian must be running** — all commands fail if the desktop app is not open. On a headless VPS without Obsidian, the CLI is unusable.
- **Vault focus matters** — without explicit `vault=`, commands target the most recently focused vault, which may not be the one you expect.
- **`file=` vs `path=`** — `file=` resolves like a wikilink (ambiguous if duplicate names exist). Use `path=` for precision.
- **Quote values with spaces** — `name=My Note` will fail; must be `name="My Note"`.
- **Multiline content** — use literal `\n` and `\t` escape sequences, not actual newlines.
- **`silent` flag** — without it, create/append commands will open the note in Obsidian, stealing focus.
- **Plugin reload scope** — `plugin:reload` only reloads the specified plugin ID. If you renamed the plugin or changed its manifest, you may need to disable/enable it manually.
- **`dev:errors` clears on read** — errors may not persist across multiple reads; capture them on first check.
