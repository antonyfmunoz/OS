# Defuddle — Creator-Level Best Practices
Source: https://github.com/nicholasgriffintn/defuddle
CLI Version: defuddle (npm)
Last Researched: 2026-04-28

---

# Tier 1 — Technical Mastery

## 1. Authentication

**N/A** — Defuddle is a local CLI tool. No API keys, tokens, OAuth,
or service accounts. It fetches web pages as an unauthenticated HTTP
client (like curl or wget). No secrets to manage in `.env`.

If a target page requires authentication (login wall, paywall),
Defuddle cannot access it. Use a browser-based approach (Playwright)
for authenticated pages.

---

## 2. Core Operations with Exact Signatures

Defuddle is a CLI tool, not a Python SDK. All operations are shell commands.

### Parse URL to markdown (primary EOS usage)
```bash
defuddle parse <url> --md
# Returns: clean markdown to stdout
# Exit code: 0 on success, non-zero on failure
```

### Parse URL to JSON
```bash
defuddle parse <url> --json
# Returns: JSON object to stdout
# Shape: {"title": "...", "content": "...<html>...", "markdown": "...",
#          "domain": "...", "url": "...", "description": "..."}
```

### Parse URL to HTML (default — rarely used)
```bash
defuddle parse <url>
# Returns: cleaned HTML content to stdout
```

### Extract specific metadata property
```bash
defuddle parse <url> -p <property>
# Valid properties: title, description, domain, url, author, date,
#                   siteName, image, favicon, wordCount
# Returns: single string value to stdout
```

### Save output to file
```bash
defuddle parse <url> --md -o output.md
# Writes markdown to output.md instead of stdout
```

### Pipe to file (alternative)
```bash
defuddle parse <url> --md > output.md
# Shell redirect — equivalent to -o for most uses
```

### Full flag reference
| Flag          | Short | Description                          |
|---------------|-------|--------------------------------------|
| `--md`        |       | Output as markdown                   |
| `--json`      |       | Output as JSON (includes HTML + MD)  |
| `-p <name>`   |       | Extract single metadata property     |
| `-o <file>`   |       | Write output to file                 |
| `--help`      | `-h`  | Show help                            |
| `--version`   | `-v`  | Show version                         |

---

## 3. Pagination Patterns

**N/A** — Defuddle processes one URL per invocation. There is no
pagination concept. For multi-page documentation sites, invoke
Defuddle once per URL. There is no built-in crawl/spider feature.

**Multi-page pattern (EOS):**
```bash
# Process multiple URLs sequentially
for url in "$url1" "$url2" "$url3"; do
  defuddle parse "$url" --md >> combined_output.md
  echo -e "\n---\n" >> combined_output.md
done
```

---

## 4. Rate Limits

**N/A** — Defuddle itself imposes no rate limits. It is a local tool.

However, the target web server may rate-limit or block rapid sequential
fetches. When batch-processing many URLs from the same domain:
- Add 1-2 second delays between requests
- Watch for 429 responses (will show as empty/error output)
- Respect robots.txt even though Defuddle does not check it automatically

---

## 5. Error Codes and Recovery

Defuddle does not produce structured error codes. Failures manifest as:

| Symptom                     | Cause                                     | Recovery                                         |
|-----------------------------|-------------------------------------------|--------------------------------------------------|
| Empty stdout                | JS-rendered page, bot detection           | Fall back to Playwright/browser-task              |
| `ENOTFOUND` / DNS error     | Bad URL or no network                     | Verify URL, check connectivity                   |
| `ETIMEDOUT`                 | Slow server or blocked IP                 | Retry once, then fall back to browser             |
| Garbled/partial markdown    | Non-standard DOM structure                | Try `--json` to inspect raw HTML, or use WebFetch |
| `command not found`         | Not installed                             | `npm install -g defuddle`                         |
| Node.js errors in stderr    | Version incompatibility or corrupt install| `npm uninstall -g defuddle && npm install -g defuddle` |
| Partial content (truncated) | Page uses infinite scroll or lazy loading | Content below fold is not in initial HTML — use browser |

**Retryable:** Network timeouts, temporary 5xx from target server.
**Non-retryable:** Bot detection (Cloudflare challenge), JS-only rendering, auth walls.

---

## 6. SDK Idioms

**N/A** — No Python SDK. Defuddle is CLI-only. EOS invokes it via `subprocess`
or direct Bash tool calls.

**EOS invocation pattern (Python):**
```python
import subprocess

def fetch_markdown(url: str, timeout: int = 30) -> str:
    """Fetch clean markdown from a URL using Defuddle."""
    result = subprocess.run(
        ["defuddle", "parse", url, "--md"],
        capture_output=True,
        text=True,
        timeout=timeout,
    )
    if result.returncode != 0:
        raise RuntimeError(f"Defuddle failed: {result.stderr}")
    return result.stdout
```

**EOS invocation pattern (Claude Code Bash):**
```bash
defuddle parse "https://example.com/docs/api" --md
```

Always quote URLs in shell invocations — URLs with query parameters
(`?`, `&`) will break without quoting.

---

## 7. Anti-Patterns

### WRONG: Using Defuddle on raw markdown URLs
```bash
# WRONG — corrupts the markdown
defuddle parse "https://raw.githubusercontent.com/user/repo/main/README.md" --md
```
```bash
# RIGHT — already markdown, fetch directly
curl -sL "https://raw.githubusercontent.com/user/repo/main/README.md"
# Or use WebFetch
```

### WRONG: Omitting --md flag
```bash
# WRONG — returns HTML, wastes tokens
defuddle parse "https://docs.example.com/api"
```
```bash
# RIGHT — always use --md for token efficiency
defuddle parse "https://docs.example.com/api" --md
```

### WRONG: Using Defuddle in tight loops without delays
```bash
# WRONG — will trigger rate limiting on the target server
for url in $(cat urls.txt); do
  defuddle parse "$url" --md
done
```
```bash
# RIGHT — add delay between requests to same domain
for url in $(cat urls.txt); do
  defuddle parse "$url" --md
  sleep 2
done
```

### WRONG: Not quoting URLs with special characters
```bash
# WRONG — shell interprets & as background operator
defuddle parse https://example.com/page?foo=1&bar=2 --md
```
```bash
# RIGHT — always quote URLs
defuddle parse "https://example.com/page?foo=1&bar=2" --md
```

### WRONG: Expecting JS-rendered content
```bash
# WRONG — SPA content won't be in the initial HTML fetch
defuddle parse "https://app.example.com/dashboard" --md
# Returns empty or nav-only content
```
```bash
# RIGHT — use browser-based tool for JS-rendered pages
# Fall back to Playwright or browser-task skill
```

---

## 8. Data Model

Defuddle's JSON output (`--json`) returns a single object:

```json
{
  "title": "string — page <title> or og:title",
  "description": "string — meta description or og:description",
  "domain": "string — hostname of the URL",
  "url": "string — the fetched URL",
  "siteName": "string — og:site_name if present",
  "author": "string — meta author if present",
  "date": "string — published date if detected",
  "image": "string — og:image URL if present",
  "favicon": "string — favicon URL",
  "wordCount": "number — word count of extracted content",
  "content": "string — cleaned HTML of main content",
  "markdown": "string — markdown conversion of content"
}
```

When using `--md`, only the `markdown` field value is returned (no JSON wrapper).
When using `-p <property>`, only that single field value is returned as a string.

**No nested objects.** The data model is flat. Every field is a string or number.
Missing metadata fields return empty string, not null.

---

## 9. Webhooks and Events

**N/A** — Defuddle is a stateless CLI tool. No webhooks, no events,
no subscriptions, no callbacks. Each invocation is a one-shot operation.

---

## 10. Limits

| Limit                  | Value                                 |
|------------------------|---------------------------------------|
| Max URL length         | OS/shell limit (~2048 chars typical)  |
| Max page size          | Limited by available memory           |
| Concurrent invocations | Limited by system resources            |
| Timeout                | No built-in timeout — use shell timeout or subprocess timeout |
| Output size            | No limit — streams full extracted content |

**Practical limits:**
- Pages over ~5MB of HTML may take 10+ seconds to parse
- Very deeply nested DOM structures can slow extraction significantly
- Node.js default heap (~1.5GB) is the hard ceiling for single-page processing

---

## 11. Cost Model

**Free and open source.** MIT license. No API costs, no usage limits,
no billing. The only cost is compute time on the VPS.

Indirect cost consideration: Defuddle reduces LLM token consumption by
stripping HTML clutter. A typical documentation page:
- Raw HTML fetch: ~15,000-50,000 tokens
- Defuddle markdown: ~2,000-8,000 tokens
- **Token savings: 70-90%** per page

This is the primary reason EOS uses Defuddle over raw fetches for
web content ingestion during TME research.

---

## 12. Version Pinning

**Current installed version:** Check with `defuddle --version`.

**Install specific version:**
```bash
npm install -g defuddle@1.2.3
```

**No API versioning** — CLI tool, not a hosted API. Version is the
npm package version.

**Deprecation policy:** Open source, community maintained. No formal
deprecation policy. Pin to a known-good version if stability is critical:
```bash
npm install -g defuddle@$(defuddle --version)
```

**Update check:**
```bash
npm outdated -g defuddle
```

---

# Tier 2 — Creator Intelligence

## 13. Design Intent and Tradeoffs

**Why Defuddle exists:** Web pages are bloated. Documentation pages embed
navigation, ads, cookie banners, sidebars, footers, and JavaScript that
have nothing to do with the actual content. For AI agents that need to
read web content, this bloat wastes tokens and degrades comprehension.

**Mental model:** Defuddle treats every web page as a signal-to-noise
problem. The "signal" is the main content area (article body, documentation
text). The "noise" is everything else (chrome, navigation, ads). Defuddle
uses Mozilla's Readability algorithm (same engine as Firefox Reader View)
under the hood to identify and extract the signal.

**Key tradeoffs:**
- **Simplicity over configurability** — no CSS selectors, no custom extraction
  rules. It either works on a page's structure or it doesn't.
- **Speed over completeness** — fetches raw HTML, does not execute JavaScript.
  This means fast extraction but no access to JS-rendered content.
- **Clean output over perfect fidelity** — aggressively strips formatting
  that might carry semantic meaning (tables sometimes simplified, code blocks
  occasionally mangled on poorly structured pages).

**What Defuddle is NOT:**
- Not a web scraper (no crawling, no session management, no form filling)
- Not a browser (no JS execution, no rendering)
- Not a data extraction tool (no CSS/XPath selectors, no structured scraping)

---

## 14. Problem-Solution Map and Hidden Capabilities

**Primary problem solved:** Token-efficient web content ingestion for AI agents.

**Hidden capabilities:**
1. **Metadata extraction without content** — `-p title` or `-p wordCount`
   lets you check a page's metadata without downloading the full content.
   Useful for pre-filtering URLs before full extraction.
2. **JSON mode for archival** — `--json` captures both HTML and markdown
   in one call, useful for creating searchable archives where you want
   markdown for display but HTML for fallback rendering.
3. **Word count pre-check** — `defuddle parse <url> -p wordCount` returns
   just the word count. Use this to estimate token cost before processing.
4. **Domain extraction** — `-p domain` extracts the hostname, useful for
   categorizing/grouping scraped content by source.

**Non-obvious uses:**
- **Changelog monitoring** — parse release/changelog pages to markdown,
  diff against previous version to detect changes
- **Documentation diffing** — periodically extract docs pages and compare
  to detect API changes or deprecations
- **Content quality check** — word count + title extraction as a quick
  sanity check before committing to full page processing

---

## 15. Operational Behavior and Edge Cases

**Failure modes beyond error codes:**

1. **Silent partial extraction** — some pages return content but Defuddle
   only captures the first section (above-the-fold content). No error is
   raised. The output looks valid but is incomplete. Always check word count
   against expectations for critical content.

2. **Encoding issues** — pages with non-UTF-8 encoding may produce garbled
   output. Defuddle assumes UTF-8. No encoding detection or conversion.

3. **Redirect chains** — Defuddle follows HTTP redirects but very long
   chains (5+) or JavaScript redirects will fail silently with empty output.

4. **Cookie consent walls** — European sites with GDPR cookie banners
   may return the cookie consent overlay instead of actual content. Defuddle
   cannot interact with these banners.

5. **Cloudflare/DDoS protection** — sites behind Cloudflare's challenge
   page return the challenge HTML, not the actual content. Defuddle extracts
   the challenge text as if it were content — producing misleading output
   that looks like valid markdown but says "checking your browser."

6. **Tab/accordion content** — hidden content in tabs, accordions, or
   collapsible sections is often excluded because it is hidden in the DOM
   or loaded lazily.

7. **iframe content** — embedded iframes (including embedded code playgrounds,
   maps, videos) are stripped. Only the main document is processed.

---

## 16. Ecosystem Position and Composition

**Position:** Content extraction layer. Sits between "discover a URL" and
"process the content with an LLM." It is a preprocessing step, not an
end-to-end solution.

**EOS data flow:**
```
URL discovered (search, link, reference)
  → Defuddle extracts markdown
    → Content fed to LLM for analysis/summarization
      → Results stored in EOS knowledge system
```

**Natural complements:**
- **WebSearch** — finds URLs; Defuddle extracts their content
- **WebFetch** — fallback for .md URLs or when raw content is needed
- **Playwright/browser-task** — fallback for JS-rendered or auth-protected pages
- **LLM (any)** — processes the extracted markdown

**When NOT to use Defuddle (use alternative):**
| Scenario                          | Use Instead          |
|-----------------------------------|----------------------|
| URL ends in `.md`                 | WebFetch / curl      |
| Page requires login               | Playwright           |
| Page is JS-rendered SPA           | Playwright           |
| Need structured data extraction   | Apify / custom scraper |
| Need full page screenshot         | Playwright screenshot |
| API endpoint returning JSON       | curl / WebFetch      |

---

## 17. Trajectory and Evolution

Defuddle is an open-source community tool. Development pace is moderate.

**Current direction:**
- Improving Readability-based extraction accuracy
- Better handling of modern web frameworks (React/Next.js SSR pages)
- CLI UX improvements

**Risks:**
- Small maintainer team — if abandoned, fork or find alternative
- Relies on Mozilla Readability algorithm — upstream changes affect behavior
- No commercial backing — no SLA, no support guarantees

**Alternatives to monitor:**
- `readable` (npm) — similar Readability-based extraction
- `mercury-parser` — Postlight's parser (less actively maintained)
- `trafilatura` (Python) — extraction with more language support
- Jina AI Reader (`r.jina.ai`) — hosted extraction API (but adds external dependency)

---

## 18. Conceptual Model and Solution Recipes

**Mental model:** Think of Defuddle as "Firefox Reader View for the terminal."
It applies the same Readability algorithm that powers browser reader modes.
If a page looks good in Firefox Reader View, Defuddle will extract it well.
If Reader View fails on a page, Defuddle will too.

**Recipe 1: TME research — fetch documentation for a new tool**
```bash
# 1. Find the docs URL via search
# 2. Extract the main page
defuddle parse "https://docs.tool.com/getting-started" --md > /tmp/tool_docs.md

# 3. Check word count to verify extraction worked
defuddle parse "https://docs.tool.com/getting-started" -p wordCount

# 4. If word count is suspiciously low (<100), fall back to browser
# 5. Feed extracted markdown to LLM for skill generation
```

**Recipe 2: Pre-filter batch of URLs**
```bash
# Check which URLs have substantial content before full processing
while read url; do
  wc=$(defuddle parse "$url" -p wordCount 2>/dev/null)
  if [ -n "$wc" ] && [ "$wc" -gt 200 ]; then
    echo "PROCESS: $url ($wc words)"
  else
    echo "SKIP: $url (${wc:-failed} words)"
  fi
  sleep 1
done < urls.txt
```

**Recipe 3: Save documentation snapshot for diffing**
```bash
# Date-stamped snapshot of a documentation page
DATE=$(date +%Y-%m-%d)
defuddle parse "https://docs.example.com/api" --md \
  -o "data/docs_snapshots/example_api_${DATE}.md"
```

---

## 19. Industry Expert and Cutting-Edge Usage

**AI agent usage (current frontier):**
Defuddle's primary value is in AI agent pipelines where token cost and
context quality matter. The pattern gaining traction:

1. **Agent discovers URL** (via search, link parsing, or user input)
2. **Defuddle extracts clean markdown** (70-90% token reduction)
3. **Agent processes content** (summarize, extract facts, answer questions)

This is exactly how EOS uses it in the Tool Mastery Engine research flow.

**Emerging patterns:**
- **RAG ingestion** — extract docs pages to markdown, chunk, embed, store
  in vector DB. Defuddle's clean output produces better embeddings than
  raw HTML.
- **Documentation monitoring** — scheduled extraction + diff to detect
  API changes. Cheaper than commercial monitoring services.
- **Content curation** — extract articles for newsletters or knowledge
  bases without the visual clutter.

**What puts you ahead of 95% of users:**
- Always check word count before trusting extraction results
- Use `-p` metadata extraction for pre-filtering, not full extraction
- Chain Defuddle with a browser-based fallback (never rely on it alone)
- Quote all URLs in shell invocations
- Set subprocess timeouts — Defuddle can hang on slow servers indefinitely

---

# EOS Usage Patterns

## Primary use case: Tool Mastery Engine research

When the TME researches a new tool, Defuddle is the first-choice method
for fetching official documentation pages. The flow:

1. **WebSearch** finds relevant documentation URLs
2. **Defuddle** extracts clean markdown from each URL
3. Extracted content feeds into best_practices.md generation
4. Token savings compound across multi-page documentation research

**Decision tree:**
```
Is the URL a .md file? → YES → Use WebFetch or curl
                       → NO  → Use Defuddle --md
Did Defuddle return content? → YES → Process markdown
                              → NO  → Fall back to browser-task
```

## When agents should use Defuddle

Any EOS agent or skill that needs to read a web page for information
should default to Defuddle unless:
- The URL is already markdown
- The page requires authentication
- The page is a known SPA (JS-rendered)
- The content is behind a Cloudflare challenge

## Token savings estimate

For a typical TME research session fetching 5-10 documentation pages:
- Without Defuddle: ~100,000-300,000 input tokens
- With Defuddle: ~15,000-50,000 input tokens
- **Net savings: ~80% token reduction per research session**

---

# Gotchas

### 1. Cloudflare challenge pages produce misleading output
Defuddle extracts the Cloudflare "checking your browser" text as valid
markdown. The output looks real but contains no actual page content.
Always verify output contains expected content, not just non-empty output.
**Mitigation:** Check for strings like "checking your browser" or
"Cloudflare" in the output.

### 2. No timeout by default — can hang indefinitely
Defuddle has no built-in timeout. If the target server is slow or
unresponsive, the process hangs until the OS kills it or the shell
times out.
**Mitigation:** Always set a timeout:
```bash
timeout 30 defuddle parse "https://slow-site.com" --md
```
Or in Python: `subprocess.run(..., timeout=30)`.

### 3. Cookie consent walls return overlay content
European sites with GDPR banners return the consent overlay text
instead of actual content. Output appears valid but is just the
cookie policy text.
**Mitigation:** If output mentions cookies/consent/GDPR prominently,
fall back to browser-task which can dismiss the overlay.

### 4. Silent truncation on lazy-loaded pages
Pages that lazy-load content below the fold return only the initially
visible content. No error is raised. Output looks complete but may be
missing 50%+ of the page.
**Mitigation:** Check word count against expectations. If a documentation
page returns <200 words, suspect truncation.

### 5. URLs with special characters break without quoting
URLs containing `&`, `?`, `#`, or other shell metacharacters will be
interpreted by the shell, producing incorrect behavior (background
process, empty query params, truncated URL).
**Mitigation:** Always wrap URLs in double quotes:
```bash
defuddle parse "https://example.com/search?q=test&page=2" --md
```

### 6. Raw .md URLs get double-processed
Fetching a URL that already serves markdown (e.g., raw GitHub files)
causes Defuddle to parse the markdown as HTML, corrupting formatting —
headers become plain text, links break, code blocks lose fencing.
**Mitigation:** Check URL extension before invoking. If it ends in `.md`,
use `curl -sL` or WebFetch instead.

### 7. Node.js version sensitivity
Defuddle requires a reasonably modern Node.js (16+). Older versions
may produce cryptic errors about unsupported syntax (optional chaining,
nullish coalescing).
**Mitigation:** Verify with `node --version` if Defuddle fails with
syntax errors. EOS VPS runs Node 18+, so this is only relevant on
new environments.
