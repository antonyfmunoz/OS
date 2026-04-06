---
type: wiki_schema
updated: 2026-04-05
---

# Wiki Rules

Schema for the LLM-maintained knowledge layer.
Karpathy pattern: RAW -> WIKI -> SCHEMA.

---

## RAW Layer (Immutable)

These directories are read-only sources. Claude may read but MUST NEVER modify them.

- `01_Inbox/raw_signals/` — raw signal capture
- `01_Inbox/raw_notes/` — raw notes
- `01_Inbox/processed_signals/` — dated signal files
- `data/` — data files
- `docs/` — reference documentation

If new RAW material arrives, it goes into `01_Inbox/`. It is never edited after creation.

---

## WIKI Layer

Location: `/opt/OS/10_Wiki/`

### Page Types

Every wiki page requires YAML frontmatter with `type` and `created` fields.

**concept** — Ideas, frameworks, patterns that recur.
```yaml
---
type: concept
created: 2026-04-05
tags: []
---
```

**entity** — Named things: people, products, companies, offers.
```yaml
---
type: entity
created: 2026-04-05
tags: []
---
```

**decision** — Architectural, strategic, or operational choices.
```yaml
---
type: decision
created: 2026-04-05
status: active | superseded | reverted
---
```

**synthesis** — Cross-cutting analysis connecting multiple sources.
```yaml
---
type: synthesis
created: 2026-04-05
sources: []
---
```

**source** — Summary of ingested RAW material with provenance.
```yaml
---
type: source
created: 2026-04-05
raw_path: "01_Inbox/..."
---
```

### File Naming

Lowercase, hyphenated slugs: `icp-signals.md`, `initiate-arena.md`.

### Linking Rules

- Use Obsidian wikilinks: `[[page-name]]`
- Link between wiki pages freely
- Link to RAW files when citing provenance: `[[01_Inbox/raw_notes/Raw Notes]]`
- Every page should link to at least one other wiki page (no orphans)

---

## Index

File: `10_Wiki/index.md`

- Entry point for all retrieval
- Organized by page type (Concepts, Entities, Decisions, Synthesis, Sources)
- Every new wiki page MUST be added to the index
- Use wikilinks, not raw paths

---

## Log

File: `10_Wiki/log.md`

- Append-only, chronological
- Every wiki mutation gets an entry
- Format:

```
## [ISO_TIMESTAMP] action | page
Description of what changed.
```

Actions: `create`, `update`, `delete`, `merge`, `refactor`

---

## Ingestion Rules

To bring RAW material into the wiki:

1. Read the RAW source completely
2. Create a `source` page summarizing it with `raw_path` in frontmatter
3. Extract concepts, entities, or decisions into their own pages
4. Link the source page to extracted pages
5. Add all new pages to index.md
6. Append entries to log.md

Never copy RAW content verbatim. Summarize, structure, and link.

---

## Update Rules

To modify an existing wiki page:

1. Read the current page
2. Edit with new information
3. Update `updated:` field in frontmatter if present
4. Append entry to log.md

---

## Retrieval Strategy

1. Start at `10_Wiki/index.md`
2. Follow wikilinks to relevant page
3. If page references RAW sources, read those for full detail
4. If no wiki page exists, check `07_Knowledge/` and `01_Inbox/` directly

---

## Conversation Memory

Location: `vault/memory/`

### conversations/
- One file per Claude Code session, named by session_id
- Contains lifecycle timestamps (session start, response completions)
- These are metadata logs, not transcripts
- Created automatically by SessionStart hook
- Appended to by Stop hook

### summaries/
- Compressed knowledge extracted from conversations
- Created manually when a conversation produces reusable insight
- Should link into wiki pages via wikilinks
- Format: `summary_YYYY-MM-DD_topic.md`

### index.md
- Index of conversation sessions and summaries
- Links to both conversations/ and summaries/ files

### Pipeline: conversation -> summary -> wiki

1. After a productive conversation, create a summary in `vault/memory/summaries/`
2. Extract durable knowledge into wiki pages in `10_Wiki/`
3. Link the summary to the wiki pages it fed
4. The wiki is the source of truth, not the conversation logs

---

## Maintenance

### Periodic Cleanup

- Remove contradictions between pages
- Fix orphan pages (pages with no incoming links)
- Improve internal linking
- Archive stale decision pages (mark as `superseded`)
- Verify RAW provenance links still resolve

### What Does NOT Go in the Wiki

- Ephemeral task state (use CC tasks or Neon)
- Session-specific debugging (stays in conversation)
- CC auto-memory content (separate system at ~/.claude/projects/)
- Operational logs (stay in /opt/OS/logs/)
