---
name: obsidian_markdown
description: "Use when creating or editing Obsidian Flavored Markdown files — wikilinks, embeds, callouts, properties, tags, or any Obsidian-specific syntax in .md files within the vault."
allowed-tools: "Read, Bash"
version: 1.0
source_url: "https://help.obsidian.md/obsidian-flavored-markdown"
last_researched: "2026-04-28"
api_version: "Obsidian 1.8+"
speed_category: "slow"
trigger: both
effort: medium
context: fork
---

# Tool: Obsidian Flavored Markdown

## What This Tool Does

Obsidian extends CommonMark and GitHub Flavored Markdown with wikilinks, embeds, callouts, properties (YAML frontmatter), comments, highlights, and other vault-specific syntax. This skill covers only Obsidian-specific extensions — standard Markdown (headings, bold, italic, lists, quotes, code blocks, tables) is assumed knowledge.

Core capabilities:
- **Internal links (wikilinks)** — `[[Note]]` syntax for linking notes within the vault. Obsidian tracks renames automatically.
- **Embeds** — `![[Note]]` syntax to embed notes, images, audio, PDFs, and search results inline.
- **Callouts** — `> [!type]` admonition blocks with 13 built-in types, foldable and nestable.
- **Properties (frontmatter)** — YAML metadata at the top of notes: tags, aliases, cssclasses, dates, links, custom fields.
- **Tags** — `#tag` and `#nested/tag` for categorization, usable inline and in frontmatter.
- **Comments** — `%%hidden%%` syntax for content invisible in reading view.
- **Highlights** — `==text==` for highlighted text.
- **Math (LaTeX)** — `$inline$` and `$$block$$` math expressions.
- **Diagrams (Mermaid)** — fenced `mermaid` code blocks for flowcharts, sequence diagrams, etc.
- **Footnotes** — `[^1]` reference-style and `^[inline]` footnotes.

## EOS Integration

EOS uses Obsidian as the vault layer for the Wiki system (`/opt/OS/knowledge/`). All wiki pages, palace rooms, and knowledge artifacts are Obsidian Markdown files. The backlink rules in CLAUDE.md govern when and how to use `[[wikilinks]]` in EOS files.

**Relevant EOS rules:**
- Use `[[wikilinks]]` inline where a reader would want to navigate.
- New wiki pages: check existing pages for bidirectional linking opportunities.
- Summaries: link to promoted wiki pages.
- Don't bolt links onto operational files (dashboards, templates) unless they aid navigation.
- Health check: `python3 scripts/vault_backlink_audit.py`

**When to use wikilinks vs Markdown links:** Use `[[wikilinks]]` for notes within the vault (Obsidian tracks renames). Use `[text](url)` for external URLs only.

## Quick Reference

### Workflow: Creating an Obsidian Note

1. **Add frontmatter** with properties (title, tags, aliases) at the top of the file. See [PROPERTIES.md](references/PROPERTIES.md) for all property types.
2. **Write content** using standard Markdown for structure, plus Obsidian-specific syntax below.
3. **Link related notes** using wikilinks (`[[Note]]`) for internal vault connections, or standard Markdown links for external URLs.
4. **Embed content** from other notes, images, or PDFs using the `![[embed]]` syntax. See [EMBEDS.md](references/EMBEDS.md) for all embed types.
5. **Add callouts** for highlighted information using `> [!type]` syntax. See [CALLOUTS.md](references/CALLOUTS.md) for all callout types.
6. **Verify** the note renders correctly in Obsidian's reading view.

### Internal Links (Wikilinks)

```markdown
[[Note Name]]                          Link to note
[[Note Name|Display Text]]             Custom display text
[[Note Name#Heading]]                  Link to heading
[[Note Name#^block-id]]                Link to block
[[#Heading in same note]]              Same-note heading link
```

Define a block ID by appending `^block-id` to any paragraph:

```markdown
This paragraph can be linked to. ^my-block-id
```

For lists and quotes, place the block ID on a separate line after the block:

```markdown
> A quote block

^quote-id
```

### Embeds

Prefix any wikilink with `!` to embed its content inline:

```markdown
![[Note Name]]                         Embed full note
![[Note Name#Heading]]                 Embed section
![[image.png]]                         Embed image
![[image.png|300]]                     Embed image with width
![[document.pdf#page=3]]               Embed PDF page
```

#### Embed Images

```markdown
![[image.png]]
![[image.png|640x480]]    Width x Height
![[image.png|300]]        Width only (maintains aspect ratio)
```

#### External Images

```markdown
![Alt text](https://example.com/image.png)
![Alt text|300](https://example.com/image.png)
```

#### Embed Audio

```markdown
![[audio.mp3]]
![[audio.ogg]]
```

#### Embed PDF

```markdown
![[document.pdf]]
![[document.pdf#page=3]]
![[document.pdf#height=400]]
```

#### Embed Lists

```markdown
![[Note#^list-id]]
```

Where the list has a block ID:

```markdown
- Item 1
- Item 2
- Item 3

^list-id
```

#### Embed Search Results

````markdown
```query
tag:#project status:done
```
````

See [EMBEDS.md](references/EMBEDS.md) for full embed reference.

### Callouts

```markdown
> [!note]
> Basic callout.

> [!warning] Custom Title
> Callout with a custom title.

> [!faq]- Collapsed by default
> Foldable callout (- collapsed, + expanded).
```

Common types: `note`, `tip`, `warning`, `info`, `example`, `quote`, `bug`, `danger`, `success`, `failure`, `question`, `abstract`, `todo`.

#### Foldable Callouts

```markdown
> [!faq]- Collapsed by default
> This content is hidden until expanded.

> [!faq]+ Expanded by default
> This content is visible but can be collapsed.
```

#### Nested Callouts

```markdown
> [!question] Outer callout
> > [!note] Inner callout
> > Nested content
```

#### Supported Callout Types

| Type | Aliases | Color / Icon |
|------|---------|-------------|
| `note` | - | Blue, pencil |
| `abstract` | `summary`, `tldr` | Teal, clipboard |
| `info` | - | Blue, info |
| `todo` | - | Blue, checkbox |
| `tip` | `hint`, `important` | Cyan, flame |
| `success` | `check`, `done` | Green, checkmark |
| `question` | `help`, `faq` | Yellow, question mark |
| `warning` | `caution`, `attention` | Orange, warning |
| `failure` | `fail`, `missing` | Red, X |
| `danger` | `error` | Red, zap |
| `bug` | - | Red, bug |
| `example` | - | Purple, list |
| `quote` | `cite` | Gray, quote |

#### Custom Callouts (CSS)

```css
.callout[data-callout="custom-type"] {
  --callout-color: 255, 0, 0;
  --callout-icon: lucide-alert-circle;
}
```

See [CALLOUTS.md](references/CALLOUTS.md) for full callout reference.

### Properties (Frontmatter)

```yaml
---
title: My Note
date: 2024-01-15
tags:
  - project
  - active
aliases:
  - Alternative Name
cssclasses:
  - custom-class
status: in-progress
rating: 4.5
completed: false
due: 2024-02-01T14:30:00
---
```

Default properties: `tags` (searchable labels), `aliases` (alternative note names for link suggestions), `cssclasses` (CSS classes for styling).

#### Property Types

| Type | Example |
|------|---------|
| Text | `title: My Title` |
| Number | `rating: 4.5` |
| Checkbox | `completed: true` |
| Date | `date: 2024-01-15` |
| Date & Time | `due: 2024-01-15T14:30:00` |
| List | `tags: [one, two]` or YAML list |
| Links | `related: "[[Other Note]]"` |

See [PROPERTIES.md](references/PROPERTIES.md) for full property reference.

### Tags

```markdown
#tag                    Inline tag
#nested/tag             Nested tag with hierarchy
#tag-with-dashes
#tag_with_underscores
```

Tags can contain: letters (any language), numbers (not first character), underscores `_`, hyphens `-`, forward slashes `/` (for nesting). Tags can also be defined in frontmatter under the `tags` property.

In frontmatter:

```yaml
---
tags:
  - tag1
  - nested/tag2
---
```

### Comments

```markdown
This is visible %%but this is hidden%% text.

%%
This entire block is hidden in reading view.
%%
```

### Obsidian-Specific Formatting

```markdown
==Highlighted text==                   Highlight syntax
```

### Math (LaTeX)

```markdown
Inline: $e^{i\pi} + 1 = 0$

Block:
$$
\frac{a}{b} = c
$$
```

### Diagrams (Mermaid)

````markdown
```mermaid
graph TD
    A[Start] --> B{Decision}
    B -->|Yes| C[Do this]
    B -->|No| D[Do that]
```
````

To link Mermaid nodes to Obsidian notes, add `class NodeName internal-link;`.

### Footnotes

```markdown
Text with a footnote[^1].

[^1]: Footnote content.

Inline footnote.^[This is inline.]
```

### Complete Example

````markdown
---
title: Project Alpha
date: 2024-01-15
tags:
  - project
  - active
status: in-progress
---

# Project Alpha

This project aims to [[improve workflow]] using modern techniques.

> [!important] Key Deadline
> The first milestone is due on ==January 30th==.

## Tasks

- [x] Initial planning
- [ ] Development phase
  - [ ] Backend implementation
  - [ ] Frontend design

## Notes

The algorithm uses $O(n \log n)$ sorting. See [[Algorithm Notes#Sorting]] for details.

![[Architecture Diagram.png|600]]

Reviewed in [[Meeting Notes 2024-01-10#Decisions]].
````

## Gotchas

- **Wikilinks vs Markdown links:** Always use `[[wikilinks]]` for vault-internal links. Using `[text](file.md)` will work but Obsidian will not track renames, breaking links when notes move.
- **Block IDs on lists/quotes:** The `^block-id` must be on its own line after the block, not on the last line of the block. Getting this wrong produces a broken link.
- **Frontmatter must be first:** The `---` YAML block must be the very first thing in the file. No blank lines or content before it.
- **Tag naming:** Tags cannot start with a number. `#2024plan` is not a valid tag; `#plan-2024` is.
- **Callout type case:** Callout types are case-insensitive (`[!NOTE]` = `[!note]`), but lowercase is conventional.
- **Embed vs link:** `![[Note]]` embeds (renders inline), `[[Note]]` links. Forgetting the `!` prefix is a common mistake when intending to embed.
- **Highlight syntax conflicts:** `==text==` can conflict with some Markdown parsers outside Obsidian. Only use in Obsidian vault files.
- **Mermaid internal links:** To make a Mermaid node clickable as an Obsidian link, you must add `class NodeName internal-link;` — there is no wikilink syntax inside Mermaid blocks.
- **Properties with special characters:** Property values containing colons, brackets, or other YAML special characters must be quoted. `title: "My Note: A Story"` not `title: My Note: A Story`.
- **Nested callouts whitespace:** Each nesting level requires an additional `>` prefix with a space. Missing the space breaks the nesting.

## References

- [Obsidian Flavored Markdown](https://help.obsidian.md/obsidian-flavored-markdown)
- [Internal links](https://help.obsidian.md/links)
- [Embed files](https://help.obsidian.md/embeds)
- [Callouts](https://help.obsidian.md/callouts)
- [Properties](https://help.obsidian.md/properties)
