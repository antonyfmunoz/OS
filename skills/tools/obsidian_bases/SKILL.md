---
name: obsidian_bases
description: "Use when creating or editing Obsidian Bases (.base files) — database views, filters, formulas, summaries, table/card/list/map views over vault notes."
allowed-tools: "Read, Bash"
version: 1.0
source_url: "https://help.obsidian.md/bases"
last_researched: "2026-04-28"
api_version: "Obsidian 1.8+"
speed_category: "slow"
trigger: both
effort: medium
context: fork
---

# Tool: Obsidian Bases

## What This Tool Does

Obsidian Bases creates database-like views over vault notes using `.base` files written in YAML. A single `.base` file defines filters (which notes to include), formulas (computed properties), property display settings, summaries (aggregations), and one or more views (table, cards, list, map) that render the matching notes as structured data inside Obsidian.

Core capabilities:
- **Filters** — select notes by tag, folder, property value, date, or any combination using `and`/`or`/`not` logic.
- **Formulas** — compute derived values from note properties (arithmetic, conditionals, date math, string formatting).
- **Views** — render filtered notes as table, cards, list, or map. Each view has its own column order, grouping, limits, and per-view filters.
- **Summaries** — aggregate columns with built-in functions (Sum, Average, Min, Max, Median, Range, Stddev, Earliest, Latest, Checked, Unchecked, Empty, Filled, Unique) or custom formula summaries.
- **Properties** — configure display names for note properties, file properties, and formula properties.
- **Embedding** — embed a base or a specific view into any Markdown file via `![[MyBase.base]]` or `![[MyBase.base#View Name]]`.

## EOS Integration

Base files live in the Obsidian vault at `/opt/OS/data/vault/` (or whichever vault path is configured). They are plain YAML text files — create and edit them directly with Write/Edit tools. No build step required; Obsidian picks up changes on file save.

When creating bases for EOS wiki pages or dashboards:
- Place `.base` files alongside the notes they query, or in a dedicated `bases/` folder.
- Use `file.inFolder()` and `file.hasTag()` filters to scope to specific wiki rooms or project areas.
- Embed bases in dashboard pages using `![[filename.base]]` for live data views.

## Quick Reference

### Schema

```yaml
# Global filters — apply to ALL views
filters:
  and: []        # All conditions must match
  or: []         # Any condition can match
  not: []        # Exclude matching notes

# Computed properties
formulas:
  formula_name: 'expression'

# Display configuration
properties:
  property_name:
    displayName: "Display Name"
  formula.formula_name:
    displayName: "Formula Display Name"
  file.ext:
    displayName: "Extension"

# Custom summary formulas
summaries:
  custom_summary_name: 'values.mean().round(3)'

# One or more views
views:
  - type: table | cards | list | map
    name: "View Name"
    limit: 10                    # Optional: limit results
    groupBy:                     # Optional: group results
      property: property_name
      direction: ASC | DESC
    filters:                     # View-specific filters (override global)
      and: []
    order:                       # Properties to display in order
      - file.name
      - property_name
      - formula.formula_name
    summaries:                   # Map properties to summary formulas
      property_name: Average
```

### Filter Syntax

```yaml
# Single filter
filters: 'status == "done"'

# AND — all conditions must be true
filters:
  and:
    - 'status == "done"'
    - 'priority > 3'

# OR — any condition can be true
filters:
  or:
    - 'file.hasTag("book")'
    - 'file.hasTag("article")'

# NOT — exclude matching items
filters:
  not:
    - 'file.hasTag("archived")'

# Nested filters
filters:
  or:
    - file.hasTag("tag")
    - and:
        - file.hasTag("book")
        - file.hasLink("Textbook")
    - not:
        - file.hasTag("book")
        - file.inFolder("Required Reading")
```

### Filter Operators

| Operator | Description |
|----------|-------------|
| `==` | equals |
| `!=` | not equal |
| `>` | greater than |
| `<` | less than |
| `>=` | greater than or equal |
| `<=` | less than or equal |
| `&&` | logical and |
| `\|\|` | logical or |
| `!` | logical not |

### Three Types of Properties

1. **Note properties** — from frontmatter: `note.author` or just `author`
2. **File properties** — file metadata: `file.name`, `file.mtime`, etc.
3. **Formula properties** — computed values: `formula.my_formula`

### File Properties Reference

| Property | Type | Description |
|----------|------|-------------|
| `file.name` | String | File name |
| `file.basename` | String | File name without extension |
| `file.path` | String | Full path to file |
| `file.folder` | String | Parent folder path |
| `file.ext` | String | File extension |
| `file.size` | Number | File size in bytes |
| `file.ctime` | Date | Created time |
| `file.mtime` | Date | Modified time |
| `file.tags` | List | All tags in file |
| `file.links` | List | Internal links in file |
| `file.backlinks` | List | Files linking to this file |
| `file.embeds` | List | Embeds in the note |
| `file.properties` | Object | All frontmatter properties |

### The `this` Keyword

- In main content area: refers to the base file itself
- When embedded: refers to the embedding file
- In sidebar: refers to the active file in main content

### Formula Syntax

```yaml
formulas:
  # Simple arithmetic
  total: "price * quantity"

  # Conditional logic
  status_icon: 'if(done, "done", "pending")'

  # String formatting
  formatted_price: 'if(price, price.toFixed(2) + " dollars")'

  # Date formatting
  created: 'file.ctime.format("YYYY-MM-DD")'

  # Calculate days since created (use .days for Duration)
  days_old: '(now() - file.ctime).days'

  # Calculate days until due date
  days_until_due: 'if(due_date, (date(due_date) - today()).days, "")'
```

### Key Functions

| Function | Signature | Description |
|----------|-----------|-------------|
| `date()` | `date(string): date` | Parse string to date (`YYYY-MM-DD HH:mm:ss`) |
| `now()` | `now(): date` | Current date and time |
| `today()` | `today(): date` | Current date (time = 00:00:00) |
| `if()` | `if(condition, trueResult, falseResult?)` | Conditional |
| `duration()` | `duration(string): duration` | Parse duration string |
| `file()` | `file(path): file` | Get file object |
| `link()` | `link(path, display?): Link` | Create a link |

### Duration Type

When subtracting two dates, the result is a **Duration** type (not a number).

**Duration Fields:** `duration.days`, `duration.hours`, `duration.minutes`, `duration.seconds`, `duration.milliseconds`

**IMPORTANT:** Duration does NOT support `.round()`, `.floor()`, `.ceil()` directly. Access a numeric field first (like `.days`), then apply number functions.

```yaml
# CORRECT: Calculate days between dates
"(date(due_date) - today()).days"                    # Returns number of days
"(now() - file.ctime).days"                          # Days since created
"(date(due_date) - today()).days.round(0)"           # Rounded days

# WRONG — will cause error:
# "((date(due) - today()) / 86400000).round(0)"      # Duration doesn't support division then round
```

### Date Arithmetic

```yaml
# Duration units: y/year/years, M/month/months, d/day/days,
#                 w/week/weeks, h/hour/hours, m/minute/minutes, s/second/seconds
"now() + \"1 day\""       # Tomorrow
"today() + \"7d\""        # A week from today
"now() - file.ctime"      # Returns Duration
"(now() - file.ctime).days"  # Get days as number
```

### View Types

**Table:**
```yaml
views:
  - type: table
    name: "My Table"
    order:
      - file.name
      - status
      - due_date
    summaries:
      price: Sum
      count: Average
```

**Cards:**
```yaml
views:
  - type: cards
    name: "Gallery"
    order:
      - file.name
      - cover_image
      - description
```

**List:**
```yaml
views:
  - type: list
    name: "Simple List"
    order:
      - file.name
      - status
```

**Map** (requires latitude/longitude properties and Maps community plugin):
```yaml
views:
  - type: map
    name: "Locations"
```

### Default Summary Formulas

| Name | Input Type | Description |
|------|------------|-------------|
| `Average` | Number | Mathematical mean |
| `Min` | Number | Smallest number |
| `Max` | Number | Largest number |
| `Sum` | Number | Sum of all numbers |
| `Range` | Number | Max - Min |
| `Median` | Number | Mathematical median |
| `Stddev` | Number | Standard deviation |
| `Earliest` | Date | Earliest date |
| `Latest` | Date | Latest date |
| `Range` | Date | Latest - Earliest |
| `Checked` | Boolean | Count of true values |
| `Unchecked` | Boolean | Count of false values |
| `Empty` | Any | Count of empty values |
| `Filled` | Any | Count of non-empty values |
| `Unique` | Any | Count of unique values |

### Embedding Bases

```markdown
![[MyBase.base]]

<!-- Specific view -->
![[MyBase.base#View Name]]
```

### YAML Quoting Rules

- Use single quotes for formulas containing double quotes: `'if(done, "Yes", "No")'`
- Use double quotes for simple strings: `"My View Name"`
- Escape nested quotes properly in complex expressions

## Complete Examples

### Task Tracker Base

```yaml
filters:
  and:
    - file.hasTag("task")
    - 'file.ext == "md"'

formulas:
  days_until_due: 'if(due, (date(due) - today()).days, "")'
  is_overdue: 'if(due, date(due) < today() && status != "done", false)'
  priority_label: 'if(priority == 1, "High", if(priority == 2, "Medium", "Low"))'

properties:
  status:
    displayName: Status
  formula.days_until_due:
    displayName: "Days Until Due"
  formula.priority_label:
    displayName: Priority

views:
  - type: table
    name: "Active Tasks"
    filters:
      and:
        - 'status != "done"'
    order:
      - file.name
      - status
      - formula.priority_label
      - due
      - formula.days_until_due
    groupBy:
      property: status
      direction: ASC
    summaries:
      formula.days_until_due: Average

  - type: table
    name: "Completed"
    filters:
      and:
        - 'status == "done"'
    order:
      - file.name
      - completed_date
```

### Reading List Base

```yaml
filters:
  or:
    - file.hasTag("book")
    - file.hasTag("article")

formulas:
  reading_time: 'if(pages, (pages * 2).toString() + " min", "")'
  year_read: 'if(finished_date, date(finished_date).year, "")'

properties:
  author:
    displayName: Author
  formula.reading_time:
    displayName: "Est. Time"

views:
  - type: cards
    name: "Library"
    order:
      - cover
      - file.name
      - author
    filters:
      not:
        - 'status == "dropped"'

  - type: table
    name: "Reading List"
    filters:
      and:
        - 'status == "to-read"'
    order:
      - file.name
      - author
      - pages
      - formula.reading_time
```

### Daily Notes Index

```yaml
filters:
  and:
    - file.inFolder("Daily Notes")
    - '/^\d{4}-\d{2}-\d{2}$/.matches(file.basename)'

formulas:
  word_estimate: '(file.size / 5).round(0)'
  day_of_week: 'date(file.basename).format("dddd")'

properties:
  formula.day_of_week:
    displayName: "Day"
  formula.word_estimate:
    displayName: "~Words"

views:
  - type: table
    name: "Recent Notes"
    limit: 30
    order:
      - file.name
      - formula.day_of_week
      - formula.word_estimate
      - file.mtime
```

## Gotchas

- **Duration is not a number.** Subtracting two dates returns a Duration type. You must access `.days`, `.hours`, etc. before calling `.round()`, `.floor()`, or `.ceil()`. Writing `(now() - file.ctime).round(0)` will error silently.
- **Null property crashes.** If a note lacks a property used in a formula, the formula errors. Always guard with `if()`: `'if(due_date, (date(due_date) - today()).days, "")'`.
- **Undefined formula reference.** Every `formula.X` in `order` or `properties` must have a matching entry in `formulas`. Missing definitions fail silently (blank column).
- **YAML special characters.** Strings containing `:`, `{`, `}`, `[`, `]`, `,`, `&`, `*`, `#`, `?`, `|`, `-`, `<`, `>`, `=`, `!`, `%`, `@`, or backticks must be quoted. Unquoted colons in `displayName` are the most common YAML parse error.
- **Double quotes inside double quotes.** Formulas with string literals need single-quote wrapping: `'if(done, "Yes", "No")'`. Wrapping with double quotes causes a YAML parse error.
- **Map view requires plugin.** The map view type requires the Maps community plugin and latitude/longitude properties on notes.
- **`this` context changes.** `this` refers to the base file in the main content area, but refers to the embedding file when the base is embedded via `![[base.base]]`.

## References

- [Bases Syntax](https://help.obsidian.md/bases/syntax)
- [Functions](https://help.obsidian.md/bases/functions)
- [Views](https://help.obsidian.md/bases/views)
- [Formulas](https://help.obsidian.md/formulas)
- [Complete Functions Reference](references/FUNCTIONS_REFERENCE.md)
