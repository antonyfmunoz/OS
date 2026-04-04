# Tool Skill Update Intelligence
Version: 1.0
Last Updated: 2026-04-03

Smart update triggers for tool skills. Date-based staleness
alone is too slow — tech moves fast, especially AI tools.

---

## Tool Speed Categories

Assign a speed category when creating each tool skill.
Store in frontmatter as `speed_category`.

| Category | Threshold | Examples | Why |
|----------|-----------|---------|-----|
| fast | 30 days | Claude Code, Anthropic API, OpenAI, Vercel, Cursor | Ship daily/weekly, breaking changes common |
| medium | 60 days | Notion, Slack, Stripe, Calendly, Shopify, HubSpot | Versioned APIs, monthly-ish releases |
| stable | 90 days | Google Sheets, Twilio, SendGrid, Typeform, Mailchimp | Mature, slow-moving, backward-compatible |

When unsure, default to `medium`.

---

## Update Triggers

Any ONE of these fires → enter Re-Research Flow.

### 1. Date Threshold Exceeded
Compare `last_researched` in frontmatter against today.
Use the threshold for the tool's speed_category.

### 2. API Version Mismatch
The `api_version` in frontmatter differs from the tool's
current version. Check via:
- WebSearch: `{tool} API latest version`
- WebFetch: tool's API versioning page

### 3. SDK Major Release
The `sdk_version` in frontmatter is behind a major release.
Check via:
- WebSearch: `{tool} Python SDK latest version`
- `pip index versions {package}` if available

### 4. Unexpected API Error
An API call failed with an error code NOT documented in
the tool skill's Error Codes section. This means:
- The API changed behavior
- The skill has a documentation gap
- Both

### 5. Breaking Change Announced
Detected during any research (even for a different tool).
If you see `{tool} breaking change` or `{tool} deprecation`
in results, flag the affected skill for update.

### 6. User Reports Update
The user explicitly says the tool has changed, released
a new feature, or deprecated something.

### 7. New Major Feature
Detected via changelog search. A new major feature means:
- New API endpoints to document
- New capabilities to add to Problem-Solution Map
- Potential new recipes
- Updated Trajectory section

---

## Monitoring Queries by Trigger

| Trigger | Search Queries |
|---------|---------------|
| Staleness | `{tool} API changelog {year}`, `{tool} release notes {year}` |
| Version | `{tool} API latest version`, check official docs version page |
| SDK | `{tool} Python SDK changelog`, `pip index versions {package}` |
| Failure | `{tool} {error_code} {error_message}`, check status page |
| Breaking | `{tool} breaking changes {year}`, `{tool} migration guide` |
| Feature | `{tool} new features {year}`, `{tool} launch blog {year}` |

---

## What to Preserve During Re-Research

These sections contain production knowledge that docs
can't provide. Never overwrite them during updates:

- **EOS Usage Patterns** — how WE use the tool, discovered
  through real execution. Docs don't know our workflows.
- **Gotchas** — real failures we encountered. These compound
  over time and are the most valuable part of any tool skill.
- **Composition Patterns** — how this tool works with our
  other tools. Unique to our architecture.
- **Custom recipes** — EOS-specific workflows built on top
  of the tool's primitives.

When updating: add to these sections, never replace them.

---

## What to Update During Re-Research

These sections reflect the tool's current state and
should be refreshed:

- **Authentication** — if auth flows changed
- **Core Operations** — new/deprecated endpoints
- **Rate Limits** — if limits changed
- **Error Codes** — new errors discovered
- **SDK Idioms** — if SDK version changed
- **Version Pinning** — always update to current
- **Trajectory** — what's new in the roadmap
- **Industry Expert** — what's new at the frontier

Always update `last_researched` and `api_version`/`sdk_version`
in frontmatter after any re-research.
