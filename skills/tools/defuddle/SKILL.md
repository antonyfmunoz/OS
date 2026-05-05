---
name: defuddle
description: "Use when extracting clean markdown content from web pages — prefer over WebFetch for standard web pages to reduce tokens. Do NOT use for URLs ending in .md (already markdown)."
allowed-tools: "Read, Bash"
version: 1.0
source_url: "https://github.com/nicholasgriffintn/defuddle"
last_researched: "2026-04-28"
api_version: "defuddle CLI"
speed_category: slow
trigger: both
effort: low
context: fork
---

# Tool: Defuddle CLI

## What This Tool Does

Defuddle is a CLI tool that extracts clean, readable content from web pages by
stripping navigation, ads, sidebars, and other clutter. It outputs markdown by
default when using `--md`, dramatically reducing token count compared to raw
HTML fetches.

Core capabilities:
- **Markdown extraction** — converts web page main content to clean markdown
- **JSON output** — returns both HTML and markdown in structured JSON
- **Metadata extraction** — pull specific properties (title, description, domain)
- **File output** — save extracted content directly to a file

When to use Defuddle vs WebFetch:
- **Defuddle** — standard web pages, documentation sites, articles, blog posts.
  Strips clutter, saves tokens.
- **WebFetch** — URLs ending in `.md` (already markdown), raw API responses,
  or when you need the full unmodified page content.

## EOS Integration

### Installation
```bash
npm install -g defuddle
```

### Usage pattern
Defuddle is invoked directly from the CLI. No Python wrapper or EOS module
required. Agents and skills call it via Bash when they need to read a web page.

## Quick Reference

### Extract markdown from a URL (primary usage)
```bash
defuddle parse <url> --md
```

### Save markdown to file
```bash
defuddle parse <url> --md -o content.md
```

### Extract specific metadata
```bash
defuddle parse <url> -p title
defuddle parse <url> -p description
defuddle parse <url> -p domain
```

### Output formats

| Flag       | Format                              |
|------------|-------------------------------------|
| `--md`     | Markdown (default choice for EOS)   |
| `--json`   | JSON with both HTML and markdown    |
| (none)     | HTML                                |
| `-p <name>`| Specific metadata property          |

## Gotchas

### Always use `--md` flag
Without `--md`, Defuddle returns HTML which defeats the purpose of using it
for token reduction. Every EOS invocation should include `--md`.

### Do not use on `.md` URLs
If the URL already points to a markdown file (e.g., a raw GitHub `.md` file),
Defuddle will try to parse it as HTML and may corrupt the content. Use WebFetch
directly for those.

### Slow on large pages
Defuddle fetches the full page, parses the DOM, and extracts content. For very
large pages this can take several seconds. The `speed_category: slow` rating
reflects this — do not use in tight loops or high-frequency batch operations.

### Node.js required
Defuddle is an npm package. If `defuddle` is not found, run
`npm install -g defuddle` first. Requires Node.js on the system.

### Some sites block headless fetches
Sites with aggressive bot detection (Cloudflare challenges, JS-required
rendering) may return empty or partial content. If Defuddle returns nothing
useful, fall back to a browser-based approach (Playwright/browser-task).
