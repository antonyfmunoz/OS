# Obsidian CLI — Creator-Level Best Practices
Source: https://help.obsidian.md/cli, Obsidian Desktop App, Obsidian Developer Docs, Obsidian Forum
API Version: Obsidian CLI 1.0+
SDK Version: N/A (CLI tool, not an SDK)
Last Researched: 2026-04-28

---

# Tier 1 — Technical Mastery

## 1. Authentication

The Obsidian CLI communicates with a running Obsidian desktop instance via
a local REST API served by the Obsidian app itself. There is no traditional
authentication layer — the CLI connects to whatever Obsidian instance is
running on the local machine.

Access model:
- **No API key, no OAuth, no tokens.** The CLI talks to the local Obsidian
  process through a localhost socket.
- **Desktop app must be running.** If Obsidian is not open, every CLI
  command fails immediately. There is no daemon or background service.
- **Vault targeting** is implicit (most recently focused vault) or explicit
  via `vault=<name>`. The vault must already be open in the Obsidian app.

EOS consequences:
- The CLI is **unusable on a headless VPS** where Obsidian cannot run
  with a GUI. EOS vault operations on the server use direct file I/O
  against the vault directory (`/opt/OS/10_Wiki/`), not the CLI.
- For local development machines (macOS/Windows/Linux with desktop),
  the CLI provides richer access: live search indexing, backlink
  resolution, plugin reload, and DOM inspection.
- No secrets to store in `.env` for CLI access itself.

Security notes:
- Anyone with local process access can execute CLI commands — no
  multi-user isolation.
- `eval` and `dev:run-js` execute arbitrary JavaScript in the Obsidian
  Electron context. Treat these commands as root-equivalent for the vault.

## 2. Core Operations with Exact Signatures

The CLI uses a `command parameter=value flag` syntax. All commands are
prefixed with `obsidian`. Parameters take `=` with quoted values for
spaces. Flags are bare boolean switches.

### Note CRUD

```
obsidian read                           # read active file
obsidian read file=<name>               # read by wikilink name
obsidian read path=<vault-path>         # read by exact vault path
    Returns: note content as plain text (Markdown)

obsidian create name=<name>             # create empty note
obsidian create name=<name> content=<md> template=<tpl> folder=<dir>
    Flags: silent, overwrite, open
    Returns: confirmation message

obsidian append file=<name> content=<text>
obsidian append path=<path> content=<text>
    Flags: silent
    Returns: confirmation message

obsidian prepend file=<name> content=<text>
obsidian prepend path=<path> content=<text>
    Flags: silent
    Returns: confirmation message

obsidian update file=<name> content=<text>
obsidian update path=<path> content=<text>
    Note: replaces full content. Use append/prepend for partial writes.
    Flags: silent
    Returns: confirmation message

obsidian delete file=<name>
obsidian delete path=<path>
    Flags: confirm (skips confirmation prompt — use with care)
    Returns: confirmation message

obsidian open file=<name>
obsidian open path=<path>
    Opens the note in Obsidian, bringing it into focus.
```

### Search

```
obsidian search query=<text>            # full-text search across vault
obsidian search query=<text> limit=<n>  # cap results
obsidian search query=<text> path=<dir> # scope to folder
    Returns: list of matching notes with excerpts

obsidian list                           # list all notes in vault
obsidian list path=<dir>                # list notes in folder
    Flags: total (return count only)
    Returns: note paths, one per line
```

### Daily Notes

```
obsidian daily:read                     # read today's daily note
obsidian daily:append content=<text>    # append to daily note
obsidian daily:prepend content=<text>   # prepend to daily note
obsidian daily:open                     # open daily note in app
    Returns: content or confirmation
```

### Properties (YAML Frontmatter)

```
obsidian property:get name=<key> file=<name>
    Returns: property value

obsidian property:set name=<key> value=<val> file=<name>
    Sets or overwrites a frontmatter property.

obsidian property:remove name=<key> file=<name>
    Removes a property from frontmatter.
```

### Tasks

```
obsidian tasks file=<name>              # list all tasks in a note
obsidian tasks daily                    # list tasks in daily note
obsidian tasks file=<name> todo         # only incomplete tasks
obsidian tasks file=<name> done         # only completed tasks
    Returns: task lines with status indicators
```

### Tags

```
obsidian tags                           # list all tags in vault
obsidian tags sort=count                # sort by frequency
obsidian tags sort=name                 # sort alphabetically
    Flags: counts (show count per tag)
    Returns: tag list with optional counts
```

### Backlinks

```
obsidian backlinks file=<name>          # list incoming links
    Returns: list of notes that link to the target
```

### Developer / Plugin Commands

```
obsidian plugin:reload id=<plugin-id>   # reload a plugin
obsidian eval code=<js>                 # run JS in Obsidian context
obsidian dev:errors                     # show captured errors
obsidian dev:console                    # show console output
obsidian dev:console level=<level>      # filter by log level
    Levels: log, warn, error, info, debug
obsidian dev:screenshot path=<file>     # capture app screenshot
obsidian dev:dom selector=<css>         # inspect DOM element
obsidian dev:dom selector=<css> text    # get text content only
obsidian dev:css selector=<css> prop=<property>
    Returns: computed CSS value
obsidian dev:mobile on|off              # toggle mobile emulation
obsidian dev:run-js file=<path>         # run JS file in app context
```

### Vault Targeting

```
obsidian vault=<name> <any-command>     # target a specific vault
    Must be first parameter on any command.
    Without it, targets the most recently focused vault.
```

### Utility Flags (apply to most commands)

```
--copy                                  # copy output to clipboard
silent                                  # suppress auto-opening files
total                                   # return count instead of items
```

## 3. Pagination Patterns

The Obsidian CLI does not implement cursor-based or offset-based
pagination. Search results use a `limit=<n>` parameter to cap the
number of results returned.

Pattern for large result sets:
- `obsidian search query="term" limit=50` returns up to 50 matches.
- There is no `offset` or `cursor` to fetch the next page.
- If more results exist beyond the limit, they are silently truncated.

Workaround for exhaustive search:
- Narrow with `path=<folder>` to scope searches to subsets of the vault.
- Use multiple targeted searches rather than one broad search.
- For true exhaustive access, use `obsidian list` + `obsidian read`
  in a loop (expensive but complete).

## 4. Rate Limits

The CLI communicates over a local socket with the running Obsidian
instance. There are no formal rate limits.

Practical constraints:
- **Obsidian is an Electron app.** Heavy CLI usage (rapid-fire reads,
  bulk creates) can saturate the main thread and cause the desktop
  app to lag or become unresponsive.
- **File system bottleneck.** Vault operations ultimately hit disk I/O.
  On HDDs, bulk operations (hundreds of creates) will be noticeably slow.
- **Plugin reload** involves unloading and reloading the plugin module.
  Doing this rapidly (< 1s intervals) can cause state corruption in
  the plugin.

Recommended throttling for automation:
- Insert 100-200ms delay between rapid sequential commands.
- For bulk operations (creating 50+ notes), batch in groups of 10-20
  with 500ms pauses.
- Never loop `plugin:reload` — call it once, verify with `dev:errors`,
  then proceed.

## 5. Error Codes and Recovery

The CLI does not use HTTP status codes. Errors are returned as text
messages to stderr with a non-zero exit code.

Common error patterns:
```
"Obsidian is not running"
    Cause: desktop app not open
    Recovery: start Obsidian, wait for it to initialize, retry

"No vault is open"
    Cause: Obsidian running but no vault loaded
    Recovery: open a vault in Obsidian UI

"Vault '<name>' not found"
    Cause: vault= parameter names a vault that is not open
    Recovery: open the vault in Obsidian or check spelling (case-sensitive)

"File not found: <path>"
    Cause: file= or path= targets a note that doesn't exist
    Recovery: check name/path; use obsidian list to find exact path

"File already exists: <name>"
    Cause: create without overwrite flag for existing note
    Recovery: add overwrite flag or use append/update instead

"Plugin '<id>' not found"
    Cause: plugin:reload with wrong plugin ID
    Recovery: check manifest.json for correct plugin ID string

"eval error: <js-error>"
    Cause: JavaScript runtime error in eval command
    Recovery: fix JS syntax; check Obsidian API compatibility
```

All errors are non-retryable in the conventional sense — they indicate
a state problem (app not running, file missing) rather than a transient
failure. Fix the state, then retry the command.

## 6. SDK Idioms

The Obsidian CLI is a standalone command-line binary, not a Python
SDK. There is no Python client library to wrap it.

Shell invocation from Python:
```python
import subprocess
from pathlib import Path

def obsidian_cmd(
    command: str,
    params: dict[str, str] | None = None,
    flags: list[str] | None = None,
    vault: str | None = None,
    timeout: int = 10
) -> str:
    """Execute an Obsidian CLI command and return stdout."""
    args = ["obsidian"]
    if vault:
        args.append(f'vault="{vault}"')
    args.append(command)
    for key, value in (params or {}).items():
        if " " in str(value):
            args.append(f'{key}="{value}"')
        else:
            args.append(f'{key}={value}')
    for flag in (flags or []):
        args.append(flag)

    result = subprocess.run(
        " ".join(args),
        shell=True,
        capture_output=True,
        text=True,
        timeout=timeout
    )
    if result.returncode != 0:
        raise RuntimeError(f"obsidian CLI error: {result.stderr.strip()}")
    return result.stdout.strip()

# Usage examples:
content = obsidian_cmd("read", {"file": "My Note"})
obsidian_cmd("create", {"name": "New Note", "content": "# Hello"}, ["silent"])
obsidian_cmd("search", {"query": "project plan", "limit": "10"})
obsidian_cmd("daily:append", {"content": "- [ ] Review PR"})
obsidian_cmd("property:set", {"name": "status", "value": "done", "file": "Tasks"})
```

Idiomatic patterns:
- Always use `shell=True` because parameter values with quotes need shell
  interpretation.
- Set a `timeout` — if Obsidian hangs, the subprocess should not block
  the calling process forever.
- Capture stderr for error messages; stdout carries the command output.
- Wrap in a retry with state-check: if "Obsidian is not running", wait
  and retry once rather than failing immediately.

## 7. Anti-Patterns

**Anti-pattern 1: Using `file=` for notes with duplicate names**

Wrong:
```bash
obsidian read file="Meeting Notes"
# Which "Meeting Notes"? Could be in any folder.
```
Correct:
```bash
obsidian read path="03_CRM/meetings/Meeting Notes.md"
```
`file=` resolves like a wikilink — if two notes share a name, the result
is ambiguous and may not return the one you expect.

**Anti-pattern 2: Creating notes without `silent` in automation**

Wrong:
```bash
for note in "${notes[@]}"; do
    obsidian create name="$note" content="# $note"
done
```
Correct:
```bash
for note in "${notes[@]}"; do
    obsidian create name="$note" content="# $note" silent
done
```
Without `silent`, each create opens the note in Obsidian, stealing focus
and causing a cascade of tab-switching in the desktop app.

**Anti-pattern 3: Using `update` when you mean `append`**

Wrong:
```bash
obsidian update file="Daily Log" content="New entry"
# Overwrites the entire file contents with "New entry"
```
Correct:
```bash
obsidian append file="Daily Log" content="\nNew entry"
```
`update` replaces all content. This is a data-destruction footgun
in automation scripts.

**Anti-pattern 4: Relying on `dev:errors` to persist**

Wrong:
```bash
obsidian plugin:reload id=my-plugin
sleep 2
obsidian dev:errors        # Errors captured
# ... later ...
obsidian dev:errors        # May be empty — errors cleared on first read
```
Correct:
```bash
obsidian plugin:reload id=my-plugin
sleep 2
errors=$(obsidian dev:errors)
echo "$errors" >> plugin-errors.log
```
Capture errors on first read. They may not survive a second invocation.

**Anti-pattern 5: Forgetting vault= on multi-vault setups**

Wrong:
```bash
obsidian search query="important" 
# Searches whichever vault was last focused — might not be the right one
```
Correct:
```bash
obsidian vault="EOS Wiki" search query="important"
```
On machines with multiple open vaults, always specify `vault=` to
avoid targeting the wrong vault.

**Anti-pattern 6: Embedding actual newlines in content parameter**

Wrong:
```bash
obsidian append file="Note" content="Line one
Line two"
```
Correct:
```bash
obsidian append file="Note" content="Line one\nLine two"
```
The CLI interprets literal `\n` as newline. Actual newlines in the
shell argument break parameter parsing.

## 8. Data Model

The Obsidian data model is file-system-native:

```
Vault (root directory)
  +-- Folder (filesystem directory)
  |     +-- Note (.md file)
  |     |     +-- Frontmatter (YAML between --- delimiters)
  |     |     |     +-- Property (key-value pair)
  |     |     +-- Content (Markdown body)
  |     |     +-- Tasks (lines matching /- \[.\]/)
  |     |     +-- Tags (inline #tag or frontmatter tags:)
  |     |     +-- Links ([[wikilinks]] or [text](url))
  |     +-- Attachment (non-.md files: images, PDFs, etc.)
  +-- .obsidian/ (config directory)
        +-- plugins/ (community plugins)
        +-- themes/ (CSS themes)
        +-- app.json, appearance.json, etc.
```

Entity relationships:
- **Notes** are Markdown files. The filename (without `.md`) is the
  note's identity for wikilinks.
- **Backlinks** are bidirectional references derived from `[[wikilinks]]`.
  They are indexed by Obsidian at runtime, not stored in files.
- **Properties** live in YAML frontmatter and are typed: text, number,
  date, datetime, checkbox, list, tags.
- **Tags** can appear inline (`#tag`) or in frontmatter (`tags: [tag]`).
  The CLI's `tags` command aggregates both.
- **Daily notes** are regular notes auto-created with a date-based name
  per the vault's daily note settings.
- **Templates** are notes in a designated template folder. `create` with
  `template=` copies template content into the new note.

Immutable constraints:
- Note identity is filename. Renaming a file changes its identity and
  breaks all incoming wikilinks (Obsidian offers auto-rename but that
  is a UI feature, not a CLI operation).
- Folder structure is arbitrary — no enforced hierarchy.
- `.obsidian/` is vault configuration and should not be modified via
  CLI content commands.

## 9. Webhooks and Events

**N/A.** The Obsidian CLI does not support webhooks or push events.
It is a pull-only interface — you query the running instance, it does
not notify you of changes.

For event-driven workflows, alternatives include:
- **File system watchers** (e.g., `inotifywait`, `watchdog` in Python)
  on the vault directory to detect changes.
- **Obsidian community plugins** (e.g., Local REST API plugin) that
  expose HTTP endpoints with webhook-like capabilities.
- **Polling** via `obsidian search` or `obsidian read` at intervals.

## 10. Limits

Known limits:
- **Content parameter size:** shell argument length limits apply. On
  most systems, `ARG_MAX` is ~2MB. For notes larger than ~100KB of
  content in a single parameter, write the file directly instead.
- **Search results:** `limit=` caps results. Without it, the CLI returns
  all matches, which can be slow on vaults with 10,000+ notes.
- **`eval` code length:** limited by shell argument parsing. For complex
  scripts, use `dev:run-js file=<path>` instead of inline `eval`.
- **Concurrent commands:** the CLI serializes through the Obsidian main
  thread. Running multiple CLI commands simultaneously may cause
  non-deterministic ordering or dropped commands.
- **Vault size:** performance degrades on vaults with 50,000+ notes.
  Search and tag commands become noticeably slow.

## 11. Cost Model

**Free.** The Obsidian CLI ships with Obsidian Desktop and requires
no additional license. Obsidian itself is free for personal use;
commercial use requires a $50/user/year license.

No per-operation costs, no API quotas, no usage-based billing.

Related costs:
- Obsidian Sync ($4/month) and Obsidian Publish ($8/month) are
  optional paid services but do not affect CLI functionality.
- Plugin development and CLI usage are unaffected by plan tier.

## 12. Version Pinning

The CLI version is tied to the Obsidian Desktop app version.
There is no independent CLI version or separate release cycle.

Current version tracking:
- Check app version: `obsidian --version` or via `eval`:
  ```bash
  obsidian eval code="require('obsidian').apiVersion"
  ```
- CLI commands are stable across Obsidian 1.x releases. No breaking
  changes have been introduced in the CLI command surface.
- The Obsidian API version (used in `eval` and plugin development) is
  pinned per plugin in `manifest.json`'s `minAppVersion` field.

Deprecation policy:
- Obsidian does not publish a formal deprecation timeline.
- Breaking changes to the plugin API are announced in Obsidian
  Developer Docs changelogs with migration guides.
- The CLI surface has been additive-only since introduction.

---

# Tier 2 — Creator Intelligence

## 13. Design Intent and Tradeoffs

Obsidian was built by Shida Li and Erica Xu as a "second brain" tool
that treats local Markdown files as the fundamental unit. The design
philosophy:

- **Local-first.** Your notes are plain Markdown files on your filesystem.
  No proprietary format, no cloud dependency, no lock-in. The CLI
  extends this by treating the running app as an enhanced interface
  to those same files.
- **Graph-of-thought over hierarchy.** While files live in folders, the
  real structure emerges from `[[wikilinks]]` forming a knowledge graph.
  The CLI's `backlinks` command exposes this graph programmatically.
- **Extensibility via plugins.** The core app is intentionally minimal.
  Community plugins add functionality. The CLI's `plugin:reload` and
  `dev:*` commands reflect this — they exist to accelerate plugin
  development, which is Obsidian's growth engine.
- **Privacy as constraint.** No telemetry, no server-side indexing.
  This means the CLI can only work when the app is running — there is
  no cloud API to fall back to.

Tradeoffs:
- **No remote API.** Unlike Notion or Roam, there is no cloud endpoint.
  You gain privacy and speed but lose remote access.
- **File-system coupling.** Performance scales with filesystem performance.
  Network-mounted vaults (NFS, cloud drives) introduce latency the
  CLI cannot mitigate.
- **Single-user.** No multi-user collaboration at the CLI level. Obsidian
  is a personal tool; the CLI reflects this.

What Obsidian is NOT:
- Not a database (use Dataview plugin for query-like access).
- Not a CMS (Obsidian Publish is a separate product).
- Not a real-time collaboration tool.

## 14. Problem-Solution Map and Hidden Capabilities

**Problem: Automated knowledge capture from scripts**
Solution: `obsidian create` + `obsidian append` with `silent` flag in
cron jobs or pipeline scripts. Notes are created without interrupting
the user's workflow.

**Problem: Plugin development iteration speed**
Solution: The `plugin:reload` + `dev:errors` + `dev:screenshot` loop
eliminates the need to restart Obsidian. One reload command picks up
all code changes instantly.

**Problem: Vault-wide content auditing**
Solution: Combine `obsidian tags sort=count counts` with
`obsidian search query="TODO"` to find orphaned tags and unfinished work.

**Problem: Programmatic frontmatter management**
Solution: `property:set` and `property:get` allow scripts to manage
metadata without parsing YAML manually — Obsidian handles the
frontmatter serialization correctly.

Hidden capabilities:
- `eval` can access the full Obsidian Plugin API (`app.vault`,
  `app.workspace`, `app.metadataCache`). This means any operation
  possible in a plugin is possible from the CLI.
- `dev:dom` with CSS selectors can extract rendered content from the
  app, including rendered Dataview queries and embedded content.
- `dev:run-js` can load complex scripts that register commands,
  modify settings, or interact with other plugins.
- `dev:css` can inspect computed styles for theme debugging —
  no need to open DevTools manually.

## 15. Operational Behavior and Edge Cases

- **Vault index lag.** After creating a note via CLI, search may not
  find it for 1-3 seconds while Obsidian re-indexes. Insert a delay
  before searching for newly created content.
- **Frontmatter parsing.** `property:set` modifies YAML frontmatter.
  If the file has malformed YAML (unclosed quotes, tabs instead of
  spaces), the command may fail or corrupt the frontmatter block.
  Validate YAML before using property commands on untrusted files.
- **Template resolution.** `template=` resolves against the vault's
  configured template folder. If the template folder setting is empty
  or misconfigured, template application silently does nothing.
- **Concurrent access.** If another process (Git, rsync, Obsidian Sync)
  modifies a file while the CLI is reading/writing, race conditions
  are possible. The CLI does not lock files.
- **Unicode in filenames.** Obsidian handles Unicode filenames, but
  shell quoting gets tricky. Use `path=` with proper shell escaping
  for notes with non-ASCII names.
- **`dev:errors` is not buffered indefinitely.** Errors captured during
  plugin execution are stored in a limited buffer. On plugins that
  throw frequently, old errors rotate out.
- **`daily:read` before daily note exists.** If today's daily note
  has not been created yet, `daily:read` fails. Use `daily:prepend`
  or `daily:append` which auto-create the daily note if missing.
- **`delete` is permanent.** There is no trash/recycle bin integration
  in the CLI. The file is removed from the filesystem. Obsidian's
  "Move to Trash" setting does not apply to CLI deletions.

## 16. Ecosystem Position and Composition

Obsidian CLI sits at the **local knowledge layer** of a personal
knowledge management stack:

```
[Capture Tools] → [Obsidian Vault] → [Publishing/Sharing]
                         ^
                    CLI operates here
```

Natural complements:
- **Git** — version control for the vault. The CLI creates/modifies
  files; Git tracks history. `git` + `obsidian` is the standard
  backup pattern.
- **Dataview plugin** — query engine for vault content. CLI cannot
  run Dataview queries directly but `eval` can access Dataview's API.
- **Templater plugin** — advanced templating beyond `template=`.
  CLI's `create` with `template=` uses core templates; Templater
  requires its own invocation.
- **Local REST API plugin** — adds HTTP endpoints to Obsidian,
  enabling remote access that the CLI alone cannot provide.

Integration anti-patterns:
- **Obsidian + cloud-synced vault (Dropbox/iCloud) + CLI automation.**
  Sync conflicts are common when automation writes while sync is active.
  Use Obsidian Sync or Git instead.
- **Obsidian + database tools (Notion, Airtable) as dual source of truth.**
  Pick one system of record. Obsidian is files; databases are structured
  data. Sync between them creates drift.

EOS composition:
- The vault at `/opt/OS/10_Wiki/` is managed by direct file I/O on
  the VPS (no GUI available). The CLI skill exists for local machines
  where Obsidian runs with a desktop.
- The `scripts/vault_backlink_audit.py` operates on files directly,
  not through the CLI.
- If EOS ever runs on a desktop machine, the CLI enables richer
  integration: live search, backlink queries, and plugin reloads.

## 17. Trajectory and Evolution

Obsidian CLI was introduced as part of Obsidian's push toward
developer experience and automation. Trajectory signals:

- **Increasing plugin API surface.** Each Obsidian release expands the
  plugin API, which means `eval` and `dev:run-js` gain more capabilities
  without CLI-specific changes.
- **Mobile parity.** Obsidian Mobile is approaching feature parity with
  Desktop. CLI remains desktop-only with no announced mobile plans.
- **Properties system maturation.** Properties (typed frontmatter)
  were introduced in Obsidian 1.4+. The CLI's `property:*` commands
  reflect this — expect continued investment in structured metadata.
- **No cloud API announced.** Despite user requests, Obsidian has shown
  no signals toward a cloud REST API. The local-first philosophy
  appears non-negotiable.

What to build on:
- Properties system — it is actively developed and CLI support will deepen.
- Plugin development workflow (reload/errors/screenshot) — Obsidian is
  investing heavily in plugin ecosystem tooling.

What to avoid building on:
- Any assumption of remote/cloud CLI access — it is not coming.
- `eval` with undocumented internal APIs — these change between releases.

## 18. Conceptual Model and Solution Recipes

### Mental model

Think of the CLI as a **programmatic sidebar** for Obsidian. Everything
you can do in the UI — read notes, search, check backlinks, manage
properties — the CLI exposes as commands. The vault is the filesystem.
The CLI is a lens into the running app's enhanced view of that filesystem.

### Primitives

- **Note** — a Markdown file. CRUD via read/create/append/prepend/update/delete.
- **Property** — a typed frontmatter field. CRUD via property:get/set/remove.
- **Search** — full-text query against Obsidian's index.
- **Backlink** — incoming reference graph, read-only.
- **Daily note** — today's timestamped note, with dedicated commands.
- **Tag** — metadata label, queryable across vault.
- **Task** — checkbox line item, filterable by status.
- **Plugin** — extensible module, reloadable via CLI.
- **Eval** — escape hatch to the full Obsidian Plugin API.

### Recipe 1: Automated daily standup capture

```bash
# Append standup entry to daily note
obsidian daily:append content="\n## Standup $(date +%H:%M)\n- Yesterday: $YESTERDAY\n- Today: $TODAY\n- Blockers: $BLOCKERS"
```

### Recipe 2: Bulk property update across notes

```bash
# Set status=archived on all notes in a folder
for note in $(obsidian list path="archive/2025"); do
    obsidian property:set name="status" value="archived" path="$note"
done
```

### Recipe 3: Plugin development cycle

```bash
# Full dev cycle: edit → reload → verify → screenshot
vim my-plugin/main.ts
obsidian plugin:reload id=my-plugin
errors=$(obsidian dev:errors)
if [ -z "$errors" ]; then
    echo "Clean reload"
    obsidian dev:screenshot path=verify.png
else
    echo "Errors detected:"
    echo "$errors"
fi
```

### Recipe 4: Knowledge graph health check

```bash
# Find orphan notes (no backlinks)
all_notes=$(obsidian list)
for note in $all_notes; do
    backlinks=$(obsidian backlinks file="$note")
    if [ -z "$backlinks" ]; then
        echo "ORPHAN: $note"
    fi
done
```

### Recipe 5: Automated note creation from pipeline

```bash
# Create meeting note from structured data
obsidian create \
    name="Meeting $(date +%Y-%m-%d) - $CLIENT" \
    content="# Meeting with $CLIENT\n\nDate: $(date +%Y-%m-%d)\nAttendees: $ATTENDEES\n\n## Agenda\n$AGENDA\n\n## Notes\n\n## Action Items\n" \
    folder="03_CRM/meetings" \
    silent
obsidian property:set name="type" value="meeting" file="Meeting $(date +%Y-%m-%d) - $CLIENT"
obsidian property:set name="client" value="$CLIENT" file="Meeting $(date +%Y-%m-%d) - $CLIENT"
```

## 19. Industry Expert and Cutting-Edge Usage

### AI-powered vault management

Power users are combining the CLI with LLM pipelines:
- **Auto-tagging:** Read a note via CLI, pass content to an LLM for
  tag suggestions, then apply via `property:set name="tags"`.
- **Summarization:** Read long notes, generate summaries, prepend them
  as frontmatter or a summary section.
- **Link suggestion:** Search for related notes, use LLM to determine
  which wikilinks to add, then append link sections.

### Plugin development with hot reload

The `plugin:reload` + `dev:errors` loop is the expert workflow for
Obsidian plugin development. Combined with `dev:screenshot`, developers
can build visual verification into CI-like scripts without touching
the Obsidian UI.

### Vault-as-database pattern

Advanced users treat the vault as a lightweight database using:
- Properties as typed columns.
- Folders as tables.
- Search + property queries as SELECT.
- `create` with templates as INSERT with defaults.
- `property:set` as UPDATE.
- Dataview plugin (accessible via `eval`) for complex queries.

This pattern works for personal CRMs, project tracking, and content
management where a full database is overkill.

### Headless testing for plugin developers

Using `dev:screenshot` and `dev:dom`, plugin developers build
headless visual regression tests:
1. `plugin:reload` to apply changes.
2. `dev:screenshot` to capture current state.
3. Image diff against baseline screenshot.
4. `dev:dom` to assert specific DOM structures exist.

### EOS Usage Patterns

EOS integrates with Obsidian at the vault level, not the CLI level,
because the primary execution environment is a headless VPS:

- **Wiki system** (`/opt/OS/10_Wiki/`) is managed via direct file I/O
  and Python scripts (`scripts/vault_backlink_audit.py`).
- **Memory palace** (`10_Wiki/palace/`) is built and queried by
  `scripts/query_graph.py` without CLI dependency.
- **Knowledge graph** uses `data/node_summaries.json` generated from
  file parsing, not CLI search.
- **When running locally** (dev machine with Obsidian Desktop), the
  CLI becomes useful for:
  - Live search during development sessions.
  - Plugin reloads when developing Obsidian plugins for EOS.
  - Backlink verification that matches Obsidian's own index.
  - Property management for wiki pages with structured metadata.
- **Vault sync pattern:** the VPS vault is synced via Git. Local
  Obsidian opens the same vault. CLI commands on the local machine
  operate on the Git-synced copy.

---

# Gotchas

1. **Obsidian must be running with a GUI.** The CLI is entirely unusable
   on headless servers, Docker containers, or SSH sessions without X11
   forwarding. All EOS server-side vault operations must use direct
   file I/O, not the CLI.

2. **`update` replaces all content.** This is the single most dangerous
   command in automation. A script that accidentally calls `update`
   instead of `append` destroys the entire note body. Always double-check
   which write command you are using in loops.

3. **`vault=` is order-sensitive.** It must be the first parameter after
   `obsidian`. Placing it after the command name causes it to be parsed
   as a command parameter and silently targets the wrong vault.

4. **`file=` is ambiguous with duplicate names.** If your vault has
   `projects/Tasks.md` and `personal/Tasks.md`, `file="Tasks"` picks one
   non-deterministically. Always use `path=` for vaults with potential
   name collisions.

5. **`dev:errors` clears on read.** The error buffer is consumed when you
   read it. If you need to reference errors multiple times, capture the
   output to a variable or file on first read.

6. **`silent` flag is not default.** Every `create`, `append`, `prepend`
   command without `silent` will open the note in Obsidian and steal
   window focus. In automation scripts, always include `silent`.

7. **Newlines require `\n` literal, not actual newlines.** Shell newlines
   in content parameters break argument parsing. Use `\n` for line breaks
   and `\t` for tabs within content strings.

8. **No undo for `delete`.** CLI deletions bypass Obsidian's trash
   settings. The file is removed from the filesystem immediately. Use
   Git or backup the vault before running delete operations in scripts.

9. **Search index lag after writes.** Creating or modifying a note via
   CLI does not immediately update the search index. Searching within
   1-2 seconds of a write may miss the new content. Add a sleep(2)
   before search-after-write patterns.

10. **`eval` and `dev:run-js` execute with full app privileges.** These
    commands can modify vault settings, disable plugins, or corrupt
    vault configuration. Treat them as privileged operations and never
    pass untrusted input to them.
