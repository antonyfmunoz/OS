# Obsidian Bases — Creator-Level Best Practices
Source: https://help.obsidian.md/bases
Obsidian Version: 1.8+
File Format: YAML (.base)
Last Researched: 2026-04-28

---

# Tier 1 — Technical Mastery

## 1. Authentication

N/A. Obsidian Bases is a local-first feature built into Obsidian's desktop and
mobile apps. There is no API key, no OAuth flow, no token exchange. `.base` files
are plain YAML text files that live inside the vault directory. Any process that
can read/write files on the filesystem can create and edit bases.

**EOS context:** Claude Code creates `.base` files directly via Write/Edit tools
at the vault path (`/opt/OS/data/vault/` or wherever the vault is mounted).
No authentication is needed — file write access is the only requirement.

No scopes. No secrets. No rotation. No env vars required.

---

## 2. Core Operations with Exact Signatures

Obsidian Bases has no API endpoints. The "operations" are the YAML schema
sections that Obsidian's renderer parses. Every `.base` file is a single
YAML document with these top-level keys:

### Top-Level Schema
```yaml
filters:       # Global note selection — string | object (and/or/not)
formulas:      # Computed properties — map of name → expression string
properties:    # Display config — map of property path → {displayName: str}
summaries:     # Custom summary formulas — map of name → expression string
views:         # List of view definitions — list of view objects
```

### Filter Object Shape
```yaml
# Scalar filter — single expression
filters: 'status == "active"'

# Compound filter — object with and/or/not keys
filters:
  and:                         # list of filter expressions (all must match)
    - 'status == "active"'
    - 'priority >= 3'
  or:                          # list of filter expressions (any can match)
    - file.hasTag("project")
    - file.hasTag("task")
  not:                         # list of filter expressions (exclude matches)
    - file.hasTag("archived")
```

### View Object Shape
```yaml
views:
  - type: table | cards | list | map   # required — view renderer
    name: "View Name"                  # required — display label, used in embed anchors
    limit: int                         # optional — max rows returned
    groupBy:                           # optional — group results
      property: str                    #   property path to group on
      direction: ASC | DESC            #   sort direction within groups
    filters:                           # optional — view-specific filters (override global)
      and: []
    order:                             # optional — columns to show, in display order
      - file.name                      #   file property
      - property_name                  #   note property (frontmatter)
      - formula.formula_name           #   computed property
    summaries:                         # optional — footer aggregations
      property_name: Average           #   built-in summary name
      formula.x: custom_summary_name   #   custom summary from top-level summaries
```

### Formula Definition Shape
```yaml
formulas:
  name: 'expression'
  # Expression can reference:
  #   note properties   — property_name or note.property_name
  #   file properties   — file.name, file.ctime, file.size, etc.
  #   global functions   — now(), today(), date(), if(), duration()
  #   method chains      — value.round(2), string.lower(), list.join(",")
```

### Properties Definition Shape
```yaml
properties:
  property_name:                       # note property
    displayName: "Column Header"
  formula.formula_name:                # formula property
    displayName: "Computed Column"
  file.ext:                            # file property
    displayName: "Extension"
```

### Summaries Definition Shape
```yaml
summaries:
  custom_name: 'values.mean().round(3)'
  # 'values' is a magic variable representing all values in the column
  # Available methods: .mean(), .sum(), .min(), .max(), .length, etc.
```

---

## 3. Pagination Patterns

N/A. Bases render inside Obsidian's UI — there is no paginated API response.
The `limit` key on a view controls how many rows display, but this is a
presentation constraint, not pagination. There is no cursor, no offset,
no "next page" mechanism.

For large result sets, use `limit` to cap display rows and add view-specific
filters to narrow scope:

```yaml
views:
  - type: table
    name: "Recent 50"
    limit: 50
    filters:
      and:
        - 'file.mtime > date("2026-01-01")'
```

---

## 4. Rate Limits

N/A. Bases execute locally inside the Obsidian renderer. There are no API
calls, no request throttling, no tokens consumed. Performance is bounded
by vault size and filesystem I/O:

- Vaults under 10,000 notes: instant rendering.
- Vaults over 50,000 notes with complex filters: noticeable delay on first load.
- Formulas with `file.backlinks` or `file.links` on large vaults are the
  slowest operations because they require graph traversal.

No rate limit headers. No backoff needed. No cost per query.

---

## 5. Error Codes and Recovery

Bases does not return HTTP errors. Errors manifest as:

| Symptom | Cause | Fix |
|---|---|---|
| Base file shows raw YAML | YAML parse error | Check quoting — unquoted colons, unmatched quotes |
| Blank/empty column | Undefined formula reference | Ensure `formula.x` in `order` has matching `formulas.x` entry |
| Column shows "Error" | Formula runtime error | Guard null properties with `if()` — `if(prop, expr, "")` |
| No notes appear | Filter matches nothing | Test filter expressions individually; check tag/folder names |
| Map view shows nothing | Missing Maps plugin or lat/lng properties | Install Maps community plugin; add latitude/longitude frontmatter |
| `![[base.base]]` not rendering | Embed syntax wrong or file path wrong | Verify file exists at the wikilink path; check `.base` extension |

### YAML Parse Error Recovery
The most common failure mode. When Obsidian cannot parse the YAML:
1. Check for unquoted strings containing `:`, `#`, `{`, `}`, `[`, `]`
2. Check for double quotes inside double-quoted strings (use single-quote wrapper)
3. Check indentation — YAML requires consistent spaces, no tabs
4. Validate with `python3 -c "import yaml; yaml.safe_load(open('file.base'))"` from CLI

### Formula Runtime Error Recovery
When a formula shows "Error" in the rendered view:
1. Check that every referenced property exists on at least one matching note
2. Wrap all property references in `if()` guards for notes missing the property
3. Check Duration type usage — `.round()` on Duration fails; access `.days` first
4. Check date parsing — `date()` requires `YYYY-MM-DD` format strings

---

## 6. SDK Idioms

There is no SDK for Obsidian Bases. The `.base` file IS the interface.
The "idiomatic" way to create and edit bases is:

### From Claude Code (EOS pattern)
```python
# Write a .base file directly
import yaml

base = {
    'filters': {'and': ['file.hasTag("task")', 'status != "done"']},
    'formulas': {
        'days_left': 'if(due, (date(due) - today()).days, "")'
    },
    'views': [{
        'type': 'table',
        'name': 'Active Tasks',
        'order': ['file.name', 'status', 'formula.days_left']
    }]
}

with open('/opt/OS/data/vault/tasks.base', 'w') as f:
    yaml.dump(base, f, default_flow_style=False, allow_unicode=True)
```

**WARNING:** Python's `yaml.dump` will double-quote strings containing special
characters and may reorder keys. For precise control, write YAML strings directly
via Write/Edit tools rather than serializing from Python dicts.

### Preferred method — direct file write
Write the YAML as a string literal. This preserves exact quoting, key order,
and formatting:

```yaml
filters:
  and:
    - file.hasTag("task")
    - 'status != "done"'

formulas:
  days_left: 'if(due, (date(due) - today()).days, "")'

views:
  - type: table
    name: "Active Tasks"
    order:
      - file.name
      - status
      - formula.days_left
```

Obsidian hot-reloads `.base` files on save — no restart or refresh needed.

---

## 7. Anti-Patterns

### WRONG: Duration arithmetic without field access
```yaml
# WRONG — Duration type does not support .round() directly
formulas:
  age: '(now() - file.ctime).round(0)'
```
```yaml
# RIGHT — access .days first, then round the number
formulas:
  age: '(now() - file.ctime).days.round(0)'
```

### WRONG: Unguarded property references
```yaml
# WRONG — crashes on notes that lack the "due" property
formulas:
  days_left: '(date(due) - today()).days'
```
```yaml
# RIGHT — guard with if() for missing properties
formulas:
  days_left: 'if(due, (date(due) - today()).days, "")'
```

### WRONG: Double quotes wrapping formulas with string literals
```yaml
# WRONG — YAML parse error, inner quotes collide with outer
formulas:
  label: "if(done, "Yes", "No")"
```
```yaml
# RIGHT — single quotes wrap the formula, double quotes inside
formulas:
  label: 'if(done, "Yes", "No")'
```

### WRONG: Referencing a formula in order without defining it
```yaml
# WRONG — formula.priority_label not defined anywhere, renders blank
views:
  - type: table
    order:
      - formula.priority_label
```
```yaml
# RIGHT — define the formula in the formulas section
formulas:
  priority_label: 'if(priority == 1, "High", "Low")'
views:
  - type: table
    order:
      - formula.priority_label
```

### WRONG: Using displayName with unquoted colon
```yaml
# WRONG — YAML interprets colon as key-value separator
properties:
  formula.ratio:
    displayName: Ratio: Revenue/Cost
```
```yaml
# RIGHT — quote the value
properties:
  formula.ratio:
    displayName: "Ratio: Revenue/Cost"
```

### WRONG: Expecting this to always mean the base file
```yaml
# WRONG assumption — when embedded, this refers to the embedding note
formulas:
  self_path: 'this.file.path'  # returns embedding note path, not base path
```

### WRONG: Using Dataview syntax in Bases
```yaml
# WRONG — Dataview-style field access does not work
filters: 'contains(file.tags, "#project")'
```
```yaml
# RIGHT — use Bases-native file.hasTag()
filters: 'file.hasTag("project")'
```

---

## 8. Data Model

### Entity Hierarchy
```
Vault
  └── .base File (YAML document)
        ├── Filters → selects Notes from vault
        ├── Formulas → computed properties per matched Note
        ├── Properties → display configuration
        ├── Summaries → aggregation formulas across matched Notes
        └── Views[] → visual renderings
              ├── Table
              ├── Cards
              ├── List
              └── Map
```

### Three Property Namespaces

| Namespace | Prefix | Source | Examples |
|---|---|---|---|
| Note properties | (none) or `note.` | Frontmatter YAML | `status`, `due`, `author` |
| File properties | `file.` | Filesystem metadata | `file.name`, `file.ctime`, `file.size` |
| Formula properties | `formula.` | Computed in base | `formula.days_left`, `formula.label` |

### Property Types Supported

| Type | Frontmatter Example | Filter/Formula Usage |
|---|---|---|
| String | `status: active` | `status == "active"`, `status.contains("act")` |
| Number | `priority: 3` | `priority > 2`, `priority.round(0)` |
| Boolean | `done: true` | `if(done, "Yes", "No")` |
| Date | `due: 2026-05-01` | `date(due) > today()` |
| List | `tags: [a, b]` | `tags.contains("a")`, `tags.length` |
| Link | `related: "[[Other Note]]"` | `file.hasLink("Other Note")` |

### File Properties (complete, immutable)

| Property | Type | Mutable |
|---|---|---|
| `file.name` | String | No (rename = new file) |
| `file.basename` | String | No |
| `file.path` | String | No |
| `file.folder` | String | No |
| `file.ext` | String | No |
| `file.size` | Number | Read-only (changes with content) |
| `file.ctime` | Date | No |
| `file.mtime` | Date | Read-only (changes with edits) |
| `file.tags` | List | Read-only (derived from content + frontmatter) |
| `file.links` | List | Read-only (derived from content) |
| `file.backlinks` | List | Read-only (derived from graph) |
| `file.embeds` | List | Read-only (derived from content) |
| `file.properties` | Object | Read-only (mirrors frontmatter) |

No soft delete or hard delete via bases — bases are read-only views.
Notes are managed through normal file operations.

---

## 9. Webhooks and Events

N/A. Obsidian Bases is a local rendering feature with no event system,
no webhook support, and no notification mechanism. Changes to notes are
reflected in base views on next render (which is effectively real-time
within the Obsidian app due to filesystem watching).

For automation around vault changes, use:
- Filesystem watchers (inotifywait, watchdog) to detect `.md` file changes
- Obsidian's community plugin API (for plugin developers)
- Git hooks if the vault is version-controlled

---

## 10. Limits

| Limit | Value | Notes |
|---|---|---|
| Max notes per base | No hard limit | Performance degrades past ~10,000 matching notes |
| Max views per base | No hard limit | Practical limit ~10-20 for UI usability |
| Max formulas per base | No hard limit | Each formula evaluated per matching note |
| Max filter nesting depth | No documented limit | Deep nesting (5+ levels) works but is hard to maintain |
| Max `limit` value | No cap | Omit for unlimited; set to control render performance |
| Max `order` entries | No cap | All properties in vault are available |
| Summary formula complexity | Limited by expression parser | No recursive formulas; `values` is the only input variable |
| File size for `.base` | No limit | But YAML files over 500 lines are unwieldy |
| View name length | No limit | Used as anchor for `![[base.base#View Name]]` embeds |
| Property name restrictions | No spaces in frontmatter keys | Use underscores: `due_date`, not `due date` |
| Embedding depth | 1 level | Cannot embed a base inside another base |

---

## 11. Cost Model

N/A. Obsidian Bases is a built-in feature of Obsidian (free for personal use).
No per-query cost, no token consumption, no API billing.

Obsidian itself has these tiers:
- **Personal**: Free (includes Bases)
- **Commercial**: $50/year (required for business use)
- **Sync**: $4/month (cloud sync, not needed for Bases)
- **Publish**: $8/month (web publishing, not needed for Bases)

For EOS, the vault is local on the VPS. No Sync or Publish costs.
Bases cost exactly $0 to create and query regardless of volume.

---

## 12. Version Pinning

### Obsidian version
Bases was introduced in Obsidian 1.8 (early 2025). Requires Obsidian 1.8+.
The `.base` file format is versioned implicitly by Obsidian releases — there
is no explicit schema version in the file.

### YAML format stability
The YAML schema has been stable since launch. No breaking changes documented
between 1.8.0 and 1.9.x. New functions are added (not removed) in updates.

### Deprecation policy
Obsidian follows a rolling release model with no formal deprecation schedule.
The team prioritizes backward compatibility — existing `.base` files are
expected to continue working across updates.

### Formula function additions
New functions (e.g., `icon()`, `html()`, `image()`) are added in minor releases.
Using a function that doesn't exist in the user's Obsidian version will show
an error in the formula column. Check the user's Obsidian version if a
formula works in docs but fails in practice.

### Pinning strategy
No version header exists in `.base` files. Pinning is done at the Obsidian
app level. For EOS, the VPS does not run Obsidian GUI — bases are authored
by Claude Code and consumed by Obsidian on Antony's devices (laptop/iPad).
Ensure the authoring device runs Obsidian 1.8+.

---

# Tier 2 — Creator Intelligence

## 13. Design Intent and Tradeoffs

Obsidian's founding thesis is **local-first, plain-text knowledge management**.
Every note is a Markdown file you own. Bases extends this philosophy to
structured data: instead of a proprietary database (Notion, Airtable), Bases
creates database *views* over your existing Markdown notes.

**Core design philosophy:**
- **Notes are the source of truth.** A base never stores data — it queries
  it from frontmatter properties and file metadata. If you delete the base,
  the data remains in your notes.
- **Database views, not databases.** Bases is deliberately not Notion. You
  do not create rows in a database — you create notes with frontmatter, and
  bases surface them as structured views.
- **Plain text all the way down.** A `.base` file is YAML. You can create it
  with any text editor, version-control it with Git, diff it, merge it.
  No binary format, no proprietary encoding.
- **Composability through embedding.** Bases compose into notes via `![[]]`
  wikilink syntax. A dashboard note can embed multiple bases, each showing
  a different filtered/formatted view of the same underlying notes.

**Tradeoffs:**
- No relational joins — you cannot query across two note types with a foreign key.
  Workaround: use `file.hasLink()` for ad-hoc relations.
- No write-back — bases are read-only views. You cannot edit a cell in a table
  view and have it update the note's frontmatter (yet).
- No cross-vault queries — a base can only see notes in its own vault.
- Formula language is limited — no variables, no loops, no user-defined functions.
  Complex logic requires nested `if()` chains.

**What Bases is NOT:**
- Not a relational database (no joins, no schemas, no constraints)
- Not a spreadsheet (no cell editing, no formulas referencing other cells)
- Not Dataview (no DQL, no inline queries, no JavaScript — pure YAML)

**Prior art influencing the design:**
- Notion databases (visual inspiration, but local-first instead of cloud)
- Dataview plugin (proved demand, but YAML-based instead of query language)
- Tana's supertags (property-based organization pattern)

---

## 14. Problem-Solution Map and Hidden Capabilities

**Problem: Need a project dashboard without leaving Obsidian**
Solution: Create a `projects.base` with `file.hasTag("project")` filter,
formulas for status/progress/days-until-deadline, and embed via
`![[projects.base#Active]]` in a dashboard note.

**Problem: Track reading list with computed reading time estimates**
Solution: Store `pages` in frontmatter. Formula: `'if(pages, (pages * 2).toString() + " min", "")'`.
Cards view with cover image property for visual browsing.

**Problem: Daily notes index with word count and day-of-week**
Solution: `file.inFolder("Daily Notes")` filter. Formulas:
`'(file.size / 5).round(0)'` for word estimate, `'date(file.basename).format("dddd")'` for day name.

**Problem: Find orphan notes (no backlinks)**
Solution: Filter `'file.backlinks.isEmpty()'` surfaces notes nothing links to.

**Hidden capabilities:**
- **Regex filters.** `/^\d{4}-\d{2}-\d{2}$/.matches(file.basename)` — full regex
  support via `.matches()` for pattern-based note selection.
- **List aggregation in formulas.** `file.tags.length` counts tags per note.
  `file.links.filter(value.linksTo(file("Index"))).length` counts links to a
  specific file.
- **Custom summary formulas.** Beyond built-in Sum/Average/etc., define custom
  aggregations in the `summaries` block: `'values.filter(value > 0).length'`
  counts positive values.
- **HTML rendering.** `html("<span style='color:red'>Alert</span>")` renders
  styled HTML in table cells. Use for status badges, colored indicators.
- **Icon rendering.** `icon("check-circle")` renders Lucide icons inline.
  Combine with `if()` for status indicators: `'if(done, icon("check"), icon("circle"))'`.
- **Image rendering.** `image("path/to/image.png")` renders images in table cells.
  Combine with cover image properties for gallery-style card views.
- **Multi-view files.** A single `.base` file can define unlimited views. Use
  `![[base.base#View Name]]` to embed a specific view. One base file powers
  multiple dashboard sections.

---

## 15. Operational Behavior and Edge Cases

### Null property handling
If a note matches the base's filters but lacks a property referenced in a formula,
the formula returns an error for that row. This is the single most common
source of confusing behavior. Always guard with `if()`:
```yaml
# Safe pattern for any optional property
formulas:
  safe_calc: 'if(optional_prop, optional_prop * 2, "")'
```

### Date parsing strictness
`date()` expects `YYYY-MM-DD` or `YYYY-MM-DD HH:mm:ss`. Other formats
(US-style `MM/DD/YYYY`, European `DD.MM.YYYY`) silently fail and return
an empty/error value. Standardize all date frontmatter to ISO 8601.

### Tag matching behavior
`file.hasTag("project")` matches `#project` and `#project/sub`. It does NOT
match `#projects` (plural). Tag matching is exact prefix, not substring.
Tags with nested paths (`#project/web`) are matched by both
`file.hasTag("project")` and `file.hasTag("project/web")`.

### Boolean coercion
YAML booleans (`true`, `false`, `yes`, `no`) are automatically coerced.
The string `"true"` in frontmatter is NOT the same as boolean `true`.
`if(done, ...)` works with boolean `true` but fails with string `"true"`.
Ensure frontmatter uses unquoted `true`/`false`.

### `this` context switching
`this` refers to different objects depending on context:
- In main content area: `this` = the `.base` file itself
- When embedded via `![[base.base]]`: `this` = the note containing the embed
- In sidebar: `this` = the active note in main content
This is intentional and enables context-sensitive bases (e.g., "show all notes
linking to the current note").

### Empty vault edge case
A base with filters that match zero notes renders as an empty table with
column headers. This is correct behavior, not an error.

### File rename propagation
If you rename a note that is referenced in a base's filters (e.g.,
`file.hasLink("Old Name")`), Obsidian's link updater will NOT update
the base file. `.base` files are not treated as Markdown by the link
updater. Manually update references after renames.

### Concurrent base editing
If the `.base` file is edited externally (by Claude Code) while Obsidian
has it open, Obsidian detects the filesystem change and re-renders.
No conflict resolution — the filesystem version wins.

---

## 16. Ecosystem Position and Composition

### Where Bases sits in the Obsidian ecosystem
Bases is the **native replacement for Dataview** for most structured-data use
cases. Before Bases, users relied on the Dataview community plugin (DQL queries,
JavaScript expressions) to create tables and lists from note properties.

**Bases vs. Dataview:**
| Aspect | Bases | Dataview |
|---|---|---|
| Format | YAML file | Inline code block |
| Language | Expression functions | DQL + JavaScript |
| Views | Table, Cards, List, Map | Table, List, Task, Calendar |
| Summaries | Built-in + custom formulas | Manual JavaScript |
| Maintenance | First-party (Obsidian team) | Community plugin |
| Performance | Optimized native renderer | Plugin-level performance |
| Embedding | `![[file.base]]` | Inline only |
| Learning curve | Lower (YAML + simple functions) | Higher (DQL + JS) |

**Migration path:** Bases does not import Dataview queries. Migration is manual:
rewrite DQL queries as `.base` YAML files. For most TABLE/LIST queries, the
mapping is straightforward. For complex JS-powered Dataview views, Bases may
not yet have equivalent capabilities.

### Natural complements
- **Templater plugin** — auto-generate frontmatter properties that bases query
- **Obsidian Sync** — sync `.base` files across devices (treated as vault files)
- **Obsidian Publish** — bases render on published sites
- **Maps plugin** — required for map view type (latitude/longitude properties)
- **Git plugin** — version control `.base` files alongside notes

### Integration anti-patterns
- Do NOT embed bases inside Dataview code blocks (they are separate systems)
- Do NOT use Dataview's `dv.pages()` to query `.base` files (different format)
- Do NOT rely on Obsidian mobile for complex base editing (no syntax highlighting)

---

## 17. Trajectory and Evolution

### Where Bases is heading (2025-2026)
- **Write-back capability**: The most requested feature is editing cell values
  in a base table view and having changes write back to note frontmatter.
  Obsidian team has acknowledged this as a priority.
- **More view types**: Calendar view and Kanban view are likely additions
  given community demand and competitor features (Notion, Tana).
- **Cross-vault search**: Currently limited to single vault. Multi-vault
  support would unlock enterprise use cases.
- **Formula language expansion**: Expect more string/date/list functions
  per Obsidian update. The `html()` and `icon()` functions were recent additions.

### Deprecation signals
- **Dataview is not deprecated** but development has slowed. The Dataview
  maintainer (blacksmithgu) has been less active. Bases being first-party
  means long-term investment shifts to Bases.
- **No `.base` format deprecations yet** — the format is too new for anything
  to be deprecated.

### What to watch
- Obsidian changelog: https://obsidian.md/changelog
- Obsidian forum: https://forum.obsidian.md (Bases feature requests)
- Obsidian Discord: announcements channel for new releases

---

## 18. Conceptual Model and Solution Recipes

### Mental model: Bases as live database views over a folder of Markdown files
Think of your vault as a flat-file database where each `.md` file is a row
and each frontmatter property is a column. A `.base` file is a saved query —
it defines which rows to include (filters), what computed columns to add
(formulas), and how to render the results (views). The query re-runs live
as notes change.

### Primitives
1. **Filter** — select notes by property value, tag, folder, link, or regex
2. **Formula** — compute a derived value per matched note
3. **View** — render matched notes as table, cards, list, or map
4. **Summary** — aggregate a column across all matched notes
5. **Embed** — inject a base or specific view into any Markdown note
6. **Property config** — rename columns for display without changing data

### Recipe: EOS Wiki Room Dashboard
```yaml
# File: /opt/OS/data/vault/bases/wiki-room.base
filters:
  and:
    - file.inFolder("knowledge/palace/rooms")
    - 'file.ext == "md"'

formulas:
  last_updated: 'file.mtime.format("YYYY-MM-DD")'
  link_count: 'file.links.length'
  backlink_count: 'file.backlinks.length'
  connectivity: 'file.links.length + file.backlinks.length'

properties:
  formula.last_updated:
    displayName: "Last Updated"
  formula.connectivity:
    displayName: "Connections"

views:
  - type: table
    name: "All Rooms"
    order:
      - file.name
      - formula.last_updated
      - formula.link_count
      - formula.backlink_count
      - formula.connectivity
    summaries:
      formula.connectivity: Sum
```

### Recipe: CRM Pipeline Tracker
```yaml
filters:
  and:
    - file.hasTag("lead")
    - 'file.ext == "md"'

formulas:
  days_since_contact: 'if(last_contact, (today() - date(last_contact)).days, 999)'
  is_stale: 'if(last_contact, (today() - date(last_contact)).days > 14, true)'
  deal_label: 'if(deal_value, "$" + deal_value.toString(), "")'

views:
  - type: table
    name: "Active Pipeline"
    filters:
      not:
        - 'stage == "closed"'
    order:
      - file.name
      - stage
      - formula.deal_label
      - formula.days_since_contact
    groupBy:
      property: stage
      direction: ASC
    summaries:
      deal_value: Sum

  - type: cards
    name: "Hot Leads"
    filters:
      and:
        - 'stage == "qualified"'
    order:
      - file.name
      - company
      - formula.deal_label
```

### Recipe: Content Calendar
```yaml
filters:
  and:
    - file.hasTag("content")
    - file.inFolder("content-calendar")

formulas:
  status_icon: 'if(status == "published", icon("check-circle"), if(status == "draft", icon("edit"), icon("circle")))'
  days_until_publish: 'if(publish_date, (date(publish_date) - today()).days, "")'
  platform_list: 'if(platforms, platforms.join(", "), "")'

views:
  - type: table
    name: "Upcoming"
    filters:
      and:
        - 'status != "published"'
    order:
      - file.name
      - formula.status_icon
      - publish_date
      - formula.days_until_publish
      - formula.platform_list
    summaries:
      formula.days_until_publish: Average
```

---

## 19. Industry Expert and Cutting-Edge Usage

### Multi-base dashboard pattern
Power users create a single `dashboard.md` note that embeds 5-10 different
`.base` files, each showing a different slice of the vault. The dashboard
becomes a live command center:
```markdown
# Dashboard
## Active Projects
![[projects.base#In Progress]]

## This Week's Tasks
![[tasks.base#Due This Week]]

## Recent Notes
![[daily.base#Recent Notes]]

## Reading Queue
![[reading.base#To Read]]
```

### Context-sensitive bases using `this`
Advanced pattern: create a base that uses `this` to show notes related to
whatever note embeds it. Embed the same base in multiple notes for
context-sensitive views:
```yaml
# related-notes.base — embed in any note to see its connections
filters:
  and:
    - 'file.hasLink(this.file.basename)'
views:
  - type: list
    name: "Related"
    order:
      - file.name
      - file.mtime
```
Embed `![[related-notes.base]]` in any note — it automatically shows
notes that link TO the embedding note.

### Formula-driven status systems
Replace manual status tracking with computed states:
```yaml
formulas:
  auto_status: 'if(done, "Complete", if(due, if(date(due) < today(), "Overdue", if((date(due) - today()).days < 3, "Urgent", "On Track")), "No Due Date"))'
```
This single formula replaces manual status updates for most task-tracking
use cases. The status is always current because it's computed from the
due date.

### Bases as Dataview migration path
Teams migrating from Dataview to Bases use this pattern:
1. Identify all Dataview TABLE queries in the vault
2. For each, create an equivalent `.base` file
3. Replace the Dataview code block with `![[equivalent.base]]`
4. Disable the Dataview plugin once all queries are migrated
This eliminates dependency on a community plugin for core vault functionality.

### Property standardization pattern
Before creating bases, standardize frontmatter across note types:
- Dates: always `YYYY-MM-DD` (ISO 8601)
- Booleans: always unquoted `true`/`false`
- Tags: always in `tags:` frontmatter array (not just inline `#tags`)
- Lists: always YAML arrays, not comma-separated strings
This ensures formulas and filters work consistently across all notes.

---

## EOS Usage Patterns

### Vault location
EOS vault lives at `/opt/OS/data/vault/`. Base files go here or in
subdirectories. Claude Code creates and edits them via Write/Edit tools.

### Wiki integration
EOS wiki pages in `knowledge/` use frontmatter properties (tags, categories,
dates). Bases can surface wiki content as structured views:
- Room index: `file.inFolder("knowledge/palace/rooms")`
- Knowledge by topic: `file.hasTag("topic-name")`
- Stale pages: formula on `file.mtime` to find outdated content

### Dashboard pattern
Place `.base` files in `data/vault/bases/` directory. Embed them in
dashboard notes using `![[bases/name.base]]` or `![[bases/name.base#View]]`.

### Naming convention
- `{domain}.base` — e.g., `tasks.base`, `projects.base`, `leads.base`
- Use lowercase-hyphenated names matching the note domain they query
- One base per concern (don't create a single monolithic base)

### Frontmatter standards for base-queryable notes
```yaml
---
tags: [project, active]          # always list format for tag filters
status: active                   # unquoted strings for string comparison
priority: 3                      # unquoted numbers for arithmetic
due: 2026-05-01                  # ISO date for date() parsing
done: false                      # unquoted boolean for if() guards
---
```

### Git workflow
`.base` files are plain text — commit them alongside notes. They diff cleanly
and merge without conflict in most cases. Include in `.gitignore` only if
they contain user-specific view preferences that shouldn't sync.

---

## Gotchas

### 1. Duration.round() silent failure
`(now() - file.ctime).round(0)` silently produces an error value. Duration is
not a number. You must access a numeric field first: `(now() - file.ctime).days.round(0)`.
This is the most common formula error and the one most likely to be written
by an AI without explicit guidance.

### 2. YAML quoting destroys formulas
Wrapping a formula in double quotes when it contains double-quoted string
literals causes a YAML parse error. The entire `.base` file stops rendering.
Always use single quotes for formulas with string literals:
`'if(done, "Yes", "No")'` not `"if(done, "Yes", "No")"`.

### 3. Missing frontmatter property = formula error per row
If even one matching note lacks a property used in a formula, that row shows
"Error". This is not a global failure — other rows with the property render
fine. But it looks broken. Always wrap optional properties:
`'if(prop, expr_using_prop, fallback_value)'`.

### 4. Undefined formula.X in order = silent blank column
If `order` references `formula.my_calc` but `formulas` has no `my_calc` key,
the column renders with the correct header (or blank header) and empty cells.
No error message. Check that every `formula.` reference in `order` and
`properties` has a corresponding entry in `formulas`.

### 5. file.hasTag() does not match plurals
`file.hasTag("task")` matches `#task` and `#task/sub` but NOT `#tasks`.
Tag matching is exact prefix, not fuzzy. Double-check singular vs. plural
tags — this is the most common filter that "should work but doesn't."

### 6. displayName with unquoted special characters breaks YAML
`displayName: Status: Active` is invalid YAML because the second colon
creates a nested key. Quote it: `displayName: "Status: Active"`. The same
applies to `#`, `[`, `]`, `{`, `}`, and other YAML special characters.

### 7. .base files are not updated by Obsidian's link updater
Renaming a note that is referenced in a base filter (e.g.,
`file.hasLink("Old Name")`) will NOT auto-update the base file. Obsidian's
rename refactoring only updates `.md` files, not `.base` files. Manually
find-and-replace in affected base files after renames.

### 8. date() requires ISO format strings
`date("05/01/2026")` silently fails. `date("2026-05-01")` works. All date
properties in frontmatter must use `YYYY-MM-DD` format for `date()` parsing
to succeed. No error message — just empty/error values.

### 9. Boolean "true" vs true in frontmatter
`done: "true"` (string) and `done: true` (boolean) behave differently.
`if(done, ...)` works with boolean `true` but may not work as expected
with the string `"true"`. Ensure frontmatter booleans are unquoted.

### 10. Python yaml.dump mangles formula quoting
Using Python's `yaml.dump()` to generate `.base` files will re-quote
strings in ways that break formula expressions. `yaml.dump` converts
`'if(done, "Yes", "No")'` to `"if(done, \"Yes\", \"No\")"` which may
parse differently. Write `.base` files as raw strings, not via yaml.dump.
