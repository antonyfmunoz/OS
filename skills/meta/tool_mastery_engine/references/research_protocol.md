<<<<<<< Updated upstream
# Tool Mastery Research Protocol
Version: 1.0
Last Updated: 2026-04-03

This document defines the 19-section standard for creator-level
tool expertise. Every tool skill's best_practices.md must follow
this protocol. No shortcuts. No summaries. Exact data.

Read this file BEFORE researching any tool.

---

# Tier 1 — Technical Mastery (Sections 1-12)

These make the AI an expert. Data comes from official API
documentation, SDK reference, and the tool's own guides.

---

## Section 1: Authentication

**What to research:**
- Auth method (API key, OAuth2, JWT, webhook signing, service account)
- Token types (access token, refresh token, API key, secret key)
- Required scopes/permissions for each operation
- Where secrets live in EOS (which .env file, which var name)
- Token rotation/expiry policy
- Refresh flow (automatic or manual?)
- Multi-tenant considerations (per-org vs per-user tokens)

**Where to find it:**
- `{tool} authentication guide` on official docs
- `{tool} getting started` page (usually covers auth first)
- `{tool} API reference` → authentication section

**What "done" looks like:**
Can set up auth from scratch without consulting docs.
Knows exact env var names, exact scopes needed, exact
token lifetime, and exact refresh mechanism.

**Common pitfall:**
Documenting auth method without documenting scopes.
"OAuth2" is not enough — which scopes for which endpoints?

---

## Section 2: Core Operations with Exact Signatures

**What to research:**
- Every major endpoint/method the tool offers
- Parameter names, types, required vs optional
- Return value shapes (exact JSON structure)
- Python SDK method signatures (not HTTP — the SDK way)

**Where to find it:**
- Official API reference (endpoint-by-endpoint)
- Python SDK docstrings or source code
- `pip show {sdk-package}` for version info

**What "done" looks like:**
Can write any API call from memory with correct parameter
names and types. Knows the return shape without guessing.

**Example of what to capture:**
```python
notion.databases.query(
    database_id: str,           # required
    filter: dict = None,        # optional — filter object
    sorts: list = None,         # optional — sort criteria
    start_cursor: str = None,   # optional — pagination
    page_size: int = 100        # optional — max 100
)
# Returns: {'results': [PageObject], 'has_more': bool, 'next_cursor': str | None}
```

**Common pitfall:**
Documenting endpoints but not return shapes. The return
shape is what the AI needs most to write correct code.

---

## Section 3: Pagination Patterns

**What to research:**
- Pagination method per endpoint (cursor, offset, page number)
- Cursor field name in response
- How to pass cursor in next request
- Maximum page size
- "Fetch all" pattern (loop until has_more=False)

**Where to find it:**
- API reference → pagination section
- Each endpoint's response schema

**What "done" looks like:**
Can write a "fetch all pages" loop from memory for any
paginated endpoint.

**Example:**
```python
results = []
cursor = None
while True:
    response = client.endpoint.list(start_cursor=cursor, page_size=100)
    results.extend(response['results'])
    if not response['has_more']:
        break
    cursor = response['next_cursor']
```

**Common pitfall:**
Assuming all endpoints use the same pagination method.
Some tools use cursor for lists but offset for search.

---

## Section 4: Rate Limits

**What to research:**
- Requests per second / per minute / per day
- Per-endpoint limits if they differ
- Rate limit headers in responses (X-RateLimit-Remaining, etc.)
- What happens when rate limited (429 status? Retry-After header?)
- Recommended backoff strategy (exponential? fixed delay?)
- Burst vs sustained limits

**Where to find it:**
- `{tool} rate limits` in official docs
- API reference → headers section
- Status/limits dashboard if available

**What "done" looks like:**
Can state exact rate limit numbers and implement correct
backoff without consulting docs.

**Common pitfall:**
Documenting per-minute limits but missing per-second burst
limits. Many APIs have both.

---

## Section 5: Error Codes and Recovery

**What to research:**
- HTTP status codes AND tool-specific error codes
- Error response body format (JSON shape)
- Non-obvious error codes (not just 400/401/403/404/500)
- What each error actually means in practice
- Recovery strategy for each error type
- Retryable vs non-retryable errors

**Where to find it:**
- API reference → errors section
- `{tool} error codes` in docs
- GitHub issues and Stack Overflow for non-obvious errors

**What "done" looks like:**
Can handle any error response without guessing. Knows
which errors to retry and which to fail on.

**Common pitfall:**
Only documenting HTTP status codes. Tool-specific error
codes in the body (e.g., Notion's "validation_error",
Stripe's "card_declined") carry the real information.

---

## Section 6: SDK Idioms

**What to research:**
- Official Python SDK package name and import pattern
- SDK version and any version-specific syntax changes
- The "right way" to initialize the client
- Async vs sync patterns (does the SDK support both?)
- Context managers, connection pooling, retry built-ins
- Common SDK-specific gotchas

**Where to find it:**
- SDK GitHub repo README
- SDK documentation / quickstart
- SDK changelog for version-specific changes

**What "done" looks like:**
Can write idiomatic SDK code that a maintainer of the
SDK would approve of. No anti-patterns.

**Common pitfall:**
Using raw HTTP when the SDK has a built-in method.
Or using an older SDK pattern when a newer, better one exists.

---

## Section 7: Anti-Patterns

**What to research:**
- What the AI WILL get wrong without explicit guidance
- Common mistakes from Stack Overflow and GitHub issues
- What the official docs warn against
- Data format mistakes (e.g., Stripe amounts in cents not dollars,
  Notion rich text requires array of text objects)
- Timing mistakes (e.g., Apify runs are async, must poll)

**Where to find it:**
- Official docs → common mistakes / troubleshooting
- Stack Overflow → highest-voted issues for the tool
- GitHub issues → most common error reports

**What "done" looks like:**
Lists 5+ specific anti-patterns with exact wrong code
and exact correct code.

**Common pitfall:**
Being too generic ("don't make too many requests").
Anti-patterns must be specific and actionable.

---

## Section 8: Data Model

**What to research:**
- Entity relationships (hierarchy, references)
- Field types and constraints (string max length, number ranges)
- Required vs optional fields on create/update
- Immutable fields (can't change after creation)
- Soft delete vs hard delete behavior

**Where to find it:**
- API reference → object schemas
- Conceptual guides → "how X works"
- Database/object model diagrams

**What "done" looks like:**
Can draw the entity relationship diagram from memory.
Knows which fields are required, which are immutable,
and how entities reference each other.

**Common pitfall:**
Documenting top-level entities but missing nested objects
or relationship constraints.

---

## Section 9: Webhooks and Events

**What to research:**
- Available webhook/event types
- Payload shapes for each event type
- Webhook verification/signing mechanism
- Retry behavior (how many retries, backoff, timeout)
- Delivery guarantees (at-least-once? at-most-once?)
- How to register/manage webhook subscriptions

**Where to find it:**
- `{tool} webhooks` in official docs
- API reference → webhooks/events section

**What "done" looks like:**
Can set up a webhook receiver that correctly verifies
signatures and handles all event types.

**Mark N/A if tool has no webhook support.**

**Common pitfall:**
Not documenting the verification mechanism. Skipping
signature verification is a security vulnerability.

---

## Section 10: Limits

**What to research:**
- Maximum items per request (batch size)
- Maximum field/property value lengths
- Maximum file upload size
- Maximum number of entities (databases, pages, etc.)
- Maximum nesting depth
- Request body size limits

**Where to find it:**
- API reference → limits section
- `{tool} API limits` or `{tool} quotas`
- Often buried in footnotes or FAQ

**What "done" looks like:**
Knows every hard limit that could cause a request to fail.

**Common pitfall:**
Assuming limits are documented in one place. They're often
scattered across different endpoint docs.

---

## Section 11: Cost Model

**What to research:**
- Pricing structure (per-request, per-record, per-user, flat)
- Free tier limits
- What operations consume credits/quota
- Cost per typical operation (e.g., 1000 API calls = $X)
- How to monitor usage/spend
- Budget alerting mechanisms

**Where to find it:**
- Pricing page
- `{tool} API pricing` or `{tool} usage billing`
- Dashboard → usage/billing section

**What "done" looks like:**
Can estimate the cost of any operation before executing it.

**Common pitfall:**
Ignoring cost entirely. Some tools charge per-record
(Airtable), per-compute-unit (Apify), or per-event
(Twilio). This changes how you design integrations.

---

## Section 12: Version Pinning

**What to research:**
- Current API version (and how versioning works)
- Current SDK version
- How to pin to a specific API version (header, URL, config?)
- Deprecation policy (how much notice before breaking changes?)
- Migration guides between versions
- Known upcoming deprecations

**Where to find it:**
- API reference → versioning section
- Changelog / release notes
- `{tool} deprecation` announcements

**What "done" looks like:**
Can state the exact API version and SDK version in use.
Knows what's deprecated and when it will break.

**Common pitfall:**
Not pinning API version. Unpinned requests silently
upgrade when the tool ships a new version.

---

# Tier 2 — Creator Intelligence (Sections 13-19)

These make the AI a creator. Data comes from founder content,
engineering blogs, community patterns, architectural analysis,
and industry expert usage. This is what separates "knows the API"
from "understands the tool."

---

## Section 13: Design Intent and Tradeoffs

**What to research:**
- Why was this tool built? What problem was the founder solving?
- What mental model did the creators optimize for?
  (Stripe = money movement primitives, Notion = blocks as atoms,
   Twilio = communications as API calls)
- What tradeoffs were consciously made?
  (Flexibility vs. structure, speed vs. customization)
- What is this tool explicitly NOT?
  (Notion is not a database, Airtable is not Excel)
- What prior tools/paradigms influenced the design?

**Where to find it:**
- Founder interviews, launch blog posts
- "Why we built X" engineering blog posts
- Conference talks by the founding team
- WebSearch: `{tool} founder philosophy design decisions`

**What "done" looks like:**
Can explain why any API design decision was made. Can predict
how the team would design a new feature based on their philosophy.

**Common pitfall:**
Confusing marketing positioning with design philosophy.
"We're the future of X" is marketing. "We chose eventual
consistency because Y" is design philosophy.

---

## Section 14: Problem-Solution Map and Hidden Capabilities

**What to research:**
- What problems does this tool ACTUALLY solve (beyond marketing)?
- What hidden or underdocumented capabilities exist?
- What creative compositions of the tool's own primitives
  create emergent solutions most users don't discover?
- What advanced features are available but rarely used?
- What can this tool do that its competitors can't?

**Where to find it:**
- Power user forums and communities
- Advanced tutorials and "X tips you didn't know" articles
- Community showcase projects
- WebSearch: `{tool} hidden features power user tips`

**What "done" looks like:**
Can suggest 3+ non-obvious uses the user hasn't considered.
Knows capabilities that aren't in the "getting started" guide.

**Common pitfall:**
Only documenting the "happy path" features. The hidden
capabilities are often in the advanced/edge-case docs
or discovered by the community.

---

## Section 15: Operational Behavior and Edge Cases

**What to research:**
- Failure modes beyond error codes (eventual consistency delays,
  silent failures, partial failures)
- Performance characteristics docs don't mention
  (what's fast, what's slow, what's unreliable)
- Behavioral quirks (timezone handling, Unicode normalization,
  concurrent write behavior, midnight UTC edge cases)
- Eventual consistency windows (how long until data propagates?)
- What happens when referenced objects are deleted?

**Where to find it:**
- GitHub issues (especially closed ones with "wontfix")
- Stack Overflow edge case questions
- Production incident reports / postmortems
- WebSearch: `{tool} edge cases gotchas production issues`

**What "done" looks like:**
Can predict behavior in untested scenarios. Knows what
will break before it breaks.

**Common pitfall:**
Assuming the API behaves exactly as documented. Edge cases
live in GitHub issues, not in official docs.

---

## Section 16: Ecosystem Position and Composition

**What to research:**
- Where does this tool sit in a typical data architecture?
  (System of record, processing layer, presentation layer)
- Natural complements (tools designed to work together)
- Forced integrations (tools that seem compatible but aren't)
- Integration anti-patterns (combinations that seem obvious but fail)
- Data handoff patterns between tools (what maps cleanly, where
  transformation is needed, where fidelity is lost)

**Where to find it:**
- Integration marketplace / partners page
- "X + Y" tutorials and architecture guides
- WebSearch: `{tool} integration architecture best practices`

**What "done" looks like:**
Can recommend whether to use this tool or an alternative
for a given architecture. Knows which tools pair well and
which combinations to avoid.

**Common pitfall:**
Treating every tool as standalone. In practice, tools
compose — the value is in the composition, not isolation.

---

## Section 17: Trajectory and Evolution

**What to research:**
- Where is the tool heading? (product roadmap, founder statements)
- What features are being de-emphasized or deprecated?
- What's getting increased investment?
- Community-discovered patterns the company later adopted
- Deprecation signals (endpoints with "v2" alternatives,
  docs pages getting less love, features removed from UI)

**Where to find it:**
- Changelogs and release notes
- Roadmap pages (public if available)
- Founder/CEO tweets, blog posts, conference talks
- WebSearch: `{tool} roadmap {current_year}` + `{tool} deprecations`

**What "done" looks like:**
Can warn against building on dead-end features. Knows
which new features to adopt early for competitive advantage.

**Common pitfall:**
Ignoring trajectory means building on features that
get deprecated 6 months later.

---

## Section 18: Conceptual Model and Solution Recipes

**What to research:**
- How should you THINK about this tool's domain?
  (What are the primitives? What are the verbs?)
- How do primitives compose into higher-order solutions?
- 3-5 concrete end-to-end recipes for common use cases
- The "right" mental model for approaching new problems
  with this tool

**Where to find it:**
- Official conceptual guides
- "Getting started" and "best practices" architecture docs
- Well-designed example applications
- WebSearch: `{tool} architecture patterns best practices`

**What "done" looks like:**
Can solve a new problem by composing known primitives
without searching docs. Has the mental model to reason
about novel situations.

**Example recipe:**
```
Notion: Full task management pipeline
1. Create database with Status, Priority, Assignee properties
2. Create pages via API as tasks come in
3. Use database query with filter for "Status = In Progress"
4. Webhook on page update → trigger downstream automation
5. Archive completed items via page update (Status = Done)
```

**Common pitfall:**
Listing features instead of composing them into solutions.
A recipe is a complete workflow, not a feature list.

---

## Section 19: Industry Expert and Cutting-Edge Usage

**What to research:**
- How are top practitioners and companies using this tool now?
- What frontier patterns exist that most users haven't discovered?
- What novel AI-powered automations have emerged?
- How are experts combining this tool with other tools and AI
  to multiply its capabilities?
- What conference talks, case studies, or showcases demonstrate
  pushing the tool's boundaries?

**Where to find it:**
- Expert blogs and "how I use X" threads
- Case studies on the tool's website
- Automation showcases (Zapier templates, Make scenarios)
- Community forums (advanced sections)
- Conference talks from current year
- WebSearch: `{tool} advanced workflows expert tips {current_year}`
- WebSearch: `{tool} AI integration automation {current_year}`
- WebSearch: `how top companies use {tool}`

**What "done" looks like:**
Can recommend cutting-edge approaches that put the user
ahead of 95% of the tool's userbase. Knows what's possible
at the frontier, not just what's documented.

**Common pitfall:**
Confusing "advanced" with "complex." The best cutting-edge
patterns are often elegantly simple — they just require
knowing the tool deeply enough to see the shortcut.

---

# Tier 3 — Community Intelligence (Cross-cutting)

These sources supplement Tier 1 and Tier 2. They provide
edge cases, real-world gotchas, and patterns that official
docs never cover.

---

## Source A: GitHub Skill/Config Repos

**What to research:**
- Community-maintained best practice repos for the tool
- Awesome-{tool} lists with curated resources
- Popular config/dotfile repos that use the tool
- Claude Code / AI agent skill repos that cover the tool

**How to find them:**
- WebSearch: `site:github.com {tool} best practices OR awesome-{tool}`
- WebSearch: `site:github.com {tool} skill OR config OR dotfiles`
- WebSearch: `{tool} claude code skill OR claude-code`

**What "done" looks like:**
Any structured knowledge repo found is evaluated. If its
content exceeds our current skill quality for any section,
the knowledge is ABSORBED: extracted into our references/,
merged into relevant sections, external dependency deleted.

**The Absorption Pattern:**
1. Evaluate — is this higher quality than what we have?
2. Extract — pull knowledge into our references/ directory
3. Merge — integrate into existing sections
4. Delete external dependency — our system owns it now
5. Record the repo in update_intelligence.md for future checks

---

## Source B: Real User Edge Cases

**What to research:**
- Stack Overflow / GitHub Issues — actual failure modes
- Reddit / HackerNews threads — real production experiences
- Discord / Slack communities — operational tips
- Blog posts by power users (not tutorials — production stories)

**How to find them:**
- WebSearch: `{tool} production gotchas lessons learned`
- WebSearch: `{tool} site:stackoverflow.com common errors`
- WebSearch: `{tool} "we switched from" OR "we migrated" {current_year}`

**What "done" looks like:**
At least 3 real-world gotchas that aren't in official docs
are documented in the Gotchas section.

---

## Source C: Obsidian / Tool Ecosystem Plugins

**When applicable:** tools that have Obsidian plugins, VS Code
extensions, or ecosystem integrations that affect how EOS uses them.

**What to research:**
- Obsidian community plugins for the tool
- VS Code extensions and their config patterns
- Tool-specific ecosystem patterns (Dataview queries for data tools,
  template patterns for content tools, etc.)

**How to find them:**
- WebSearch: `{tool} obsidian plugin OR vault template`
- WebSearch: `{tool} vscode extension configuration`
- WebSearch: `site:github.com obsidian-{tool} OR {tool}-obsidian`

**What "done" looks like:**
If the tool has ecosystem integrations relevant to EOS,
they're documented in the Composition section of best_practices.md.

---

# Quality Gate

Before marking any tool skill complete, verify:

1. All 19 sections have real content (not placeholders)
2. Tier 1 sections contain exact numbers, signatures, and code
3. Tier 2 sections contain insights you can't find in the API reference
4. The best_practices.md is over 2000 characters
5. Source URLs are real and accessible
6. The created SKILL.md has an action-verb trigger description
7. The Gotchas section has at least 1 real entry (even if just
   "WebFetch failed on JS-rendered docs — used WebSearch instead")
=======
# Tool Mastery Research Protocol
Version: 1.0
Last Updated: 2026-04-03

This document defines the 19-section standard for creator-level
tool expertise. Every tool skill's best_practices.md must follow
this protocol. No shortcuts. No summaries. Exact data.

Read this file BEFORE researching any tool.

---

# Tier 1 — Technical Mastery (Sections 1-12)

These make the AI an expert. Data comes from official API
documentation, SDK reference, and the tool's own guides.

---

## Section 1: Authentication

**What to research:**
- Auth method (API key, OAuth2, JWT, webhook signing, service account)
- Token types (access token, refresh token, API key, secret key)
- Required scopes/permissions for each operation
- Where secrets live in EOS (which .env file, which var name)
- Token rotation/expiry policy
- Refresh flow (automatic or manual?)
- Multi-tenant considerations (per-org vs per-user tokens)

**Where to find it:**
- `{tool} authentication guide` on official docs
- `{tool} getting started` page (usually covers auth first)
- `{tool} API reference` → authentication section

**What "done" looks like:**
Can set up auth from scratch without consulting docs.
Knows exact env var names, exact scopes needed, exact
token lifetime, and exact refresh mechanism.

**Common pitfall:**
Documenting auth method without documenting scopes.
"OAuth2" is not enough — which scopes for which endpoints?

---

## Section 2: Core Operations with Exact Signatures

**What to research:**
- Every major endpoint/method the tool offers
- Parameter names, types, required vs optional
- Return value shapes (exact JSON structure)
- Python SDK method signatures (not HTTP — the SDK way)

**Where to find it:**
- Official API reference (endpoint-by-endpoint)
- Python SDK docstrings or source code
- `pip show {sdk-package}` for version info

**What "done" looks like:**
Can write any API call from memory with correct parameter
names and types. Knows the return shape without guessing.

**Example of what to capture:**
```python
notion.databases.query(
    database_id: str,           # required
    filter: dict = None,        # optional — filter object
    sorts: list = None,         # optional — sort criteria
    start_cursor: str = None,   # optional — pagination
    page_size: int = 100        # optional — max 100
)
# Returns: {'results': [PageObject], 'has_more': bool, 'next_cursor': str | None}
```

**Common pitfall:**
Documenting endpoints but not return shapes. The return
shape is what the AI needs most to write correct code.

---

## Section 3: Pagination Patterns

**What to research:**
- Pagination method per endpoint (cursor, offset, page number)
- Cursor field name in response
- How to pass cursor in next request
- Maximum page size
- "Fetch all" pattern (loop until has_more=False)

**Where to find it:**
- API reference → pagination section
- Each endpoint's response schema

**What "done" looks like:**
Can write a "fetch all pages" loop from memory for any
paginated endpoint.

**Example:**
```python
results = []
cursor = None
while True:
    response = client.endpoint.list(start_cursor=cursor, page_size=100)
    results.extend(response['results'])
    if not response['has_more']:
        break
    cursor = response['next_cursor']
```

**Common pitfall:**
Assuming all endpoints use the same pagination method.
Some tools use cursor for lists but offset for search.

---

## Section 4: Rate Limits

**What to research:**
- Requests per second / per minute / per day
- Per-endpoint limits if they differ
- Rate limit headers in responses (X-RateLimit-Remaining, etc.)
- What happens when rate limited (429 status? Retry-After header?)
- Recommended backoff strategy (exponential? fixed delay?)
- Burst vs sustained limits

**Where to find it:**
- `{tool} rate limits` in official docs
- API reference → headers section
- Status/limits dashboard if available

**What "done" looks like:**
Can state exact rate limit numbers and implement correct
backoff without consulting docs.

**Common pitfall:**
Documenting per-minute limits but missing per-second burst
limits. Many APIs have both.

---

## Section 5: Error Codes and Recovery

**What to research:**
- HTTP status codes AND tool-specific error codes
- Error response body format (JSON shape)
- Non-obvious error codes (not just 400/401/403/404/500)
- What each error actually means in practice
- Recovery strategy for each error type
- Retryable vs non-retryable errors

**Where to find it:**
- API reference → errors section
- `{tool} error codes` in docs
- GitHub issues and Stack Overflow for non-obvious errors

**What "done" looks like:**
Can handle any error response without guessing. Knows
which errors to retry and which to fail on.

**Common pitfall:**
Only documenting HTTP status codes. Tool-specific error
codes in the body (e.g., Notion's "validation_error",
Stripe's "card_declined") carry the real information.

---

## Section 6: SDK Idioms

**What to research:**
- Official Python SDK package name and import pattern
- SDK version and any version-specific syntax changes
- The "right way" to initialize the client
- Async vs sync patterns (does the SDK support both?)
- Context managers, connection pooling, retry built-ins
- Common SDK-specific gotchas

**Where to find it:**
- SDK GitHub repo README
- SDK documentation / quickstart
- SDK changelog for version-specific changes

**What "done" looks like:**
Can write idiomatic SDK code that a maintainer of the
SDK would approve of. No anti-patterns.

**Common pitfall:**
Using raw HTTP when the SDK has a built-in method.
Or using an older SDK pattern when a newer, better one exists.

---

## Section 7: Anti-Patterns

**What to research:**
- What the AI WILL get wrong without explicit guidance
- Common mistakes from Stack Overflow and GitHub issues
- What the official docs warn against
- Data format mistakes (e.g., Stripe amounts in cents not dollars,
  Notion rich text requires array of text objects)
- Timing mistakes (e.g., Apify runs are async, must poll)

**Where to find it:**
- Official docs → common mistakes / troubleshooting
- Stack Overflow → highest-voted issues for the tool
- GitHub issues → most common error reports

**What "done" looks like:**
Lists 5+ specific anti-patterns with exact wrong code
and exact correct code.

**Common pitfall:**
Being too generic ("don't make too many requests").
Anti-patterns must be specific and actionable.

---

## Section 8: Data Model

**What to research:**
- Entity relationships (hierarchy, references)
- Field types and constraints (string max length, number ranges)
- Required vs optional fields on create/update
- Immutable fields (can't change after creation)
- Soft delete vs hard delete behavior

**Where to find it:**
- API reference → object schemas
- Conceptual guides → "how X works"
- Database/object model diagrams

**What "done" looks like:**
Can draw the entity relationship diagram from memory.
Knows which fields are required, which are immutable,
and how entities reference each other.

**Common pitfall:**
Documenting top-level entities but missing nested objects
or relationship constraints.

---

## Section 9: Webhooks and Events

**What to research:**
- Available webhook/event types
- Payload shapes for each event type
- Webhook verification/signing mechanism
- Retry behavior (how many retries, backoff, timeout)
- Delivery guarantees (at-least-once? at-most-once?)
- How to register/manage webhook subscriptions

**Where to find it:**
- `{tool} webhooks` in official docs
- API reference → webhooks/events section

**What "done" looks like:**
Can set up a webhook receiver that correctly verifies
signatures and handles all event types.

**Mark N/A if tool has no webhook support.**

**Common pitfall:**
Not documenting the verification mechanism. Skipping
signature verification is a security vulnerability.

---

## Section 10: Limits

**What to research:**
- Maximum items per request (batch size)
- Maximum field/property value lengths
- Maximum file upload size
- Maximum number of entities (databases, pages, etc.)
- Maximum nesting depth
- Request body size limits

**Where to find it:**
- API reference → limits section
- `{tool} API limits` or `{tool} quotas`
- Often buried in footnotes or FAQ

**What "done" looks like:**
Knows every hard limit that could cause a request to fail.

**Common pitfall:**
Assuming limits are documented in one place. They're often
scattered across different endpoint docs.

---

## Section 11: Cost Model

**What to research:**
- Pricing structure (per-request, per-record, per-user, flat)
- Free tier limits
- What operations consume credits/quota
- Cost per typical operation (e.g., 1000 API calls = $X)
- How to monitor usage/spend
- Budget alerting mechanisms

**Where to find it:**
- Pricing page
- `{tool} API pricing` or `{tool} usage billing`
- Dashboard → usage/billing section

**What "done" looks like:**
Can estimate the cost of any operation before executing it.

**Common pitfall:**
Ignoring cost entirely. Some tools charge per-record
(Airtable), per-compute-unit (Apify), or per-event
(Twilio). This changes how you design integrations.

---

## Section 12: Version Pinning

**What to research:**
- Current API version (and how versioning works)
- Current SDK version
- How to pin to a specific API version (header, URL, config?)
- Deprecation policy (how much notice before breaking changes?)
- Migration guides between versions
- Known upcoming deprecations

**Where to find it:**
- API reference → versioning section
- Changelog / release notes
- `{tool} deprecation` announcements

**What "done" looks like:**
Can state the exact API version and SDK version in use.
Knows what's deprecated and when it will break.

**Common pitfall:**
Not pinning API version. Unpinned requests silently
upgrade when the tool ships a new version.

---

# Tier 2 — Creator Intelligence (Sections 13-19)

These make the AI a creator. Data comes from founder content,
engineering blogs, community patterns, architectural analysis,
and industry expert usage. This is what separates "knows the API"
from "understands the tool."

---

## Section 13: Design Intent and Tradeoffs

**What to research:**
- Why was this tool built? What problem was the founder solving?
- What mental model did the creators optimize for?
  (Stripe = money movement primitives, Notion = blocks as atoms,
   Twilio = communications as API calls)
- What tradeoffs were consciously made?
  (Flexibility vs. structure, speed vs. customization)
- What is this tool explicitly NOT?
  (Notion is not a database, Airtable is not Excel)
- What prior tools/paradigms influenced the design?

**Where to find it:**
- Founder interviews, launch blog posts
- "Why we built X" engineering blog posts
- Conference talks by the founding team
- WebSearch: `{tool} founder philosophy design decisions`

**What "done" looks like:**
Can explain why any API design decision was made. Can predict
how the team would design a new feature based on their philosophy.

**Common pitfall:**
Confusing marketing positioning with design philosophy.
"We're the future of X" is marketing. "We chose eventual
consistency because Y" is design philosophy.

---

## Section 14: Problem-Solution Map and Hidden Capabilities

**What to research:**
- What problems does this tool ACTUALLY solve (beyond marketing)?
- What hidden or underdocumented capabilities exist?
- What creative compositions of the tool's own primitives
  create emergent solutions most users don't discover?
- What advanced features are available but rarely used?
- What can this tool do that its competitors can't?

**Where to find it:**
- Power user forums and communities
- Advanced tutorials and "X tips you didn't know" articles
- Community showcase projects
- WebSearch: `{tool} hidden features power user tips`

**What "done" looks like:**
Can suggest 3+ non-obvious uses the user hasn't considered.
Knows capabilities that aren't in the "getting started" guide.

**Common pitfall:**
Only documenting the "happy path" features. The hidden
capabilities are often in the advanced/edge-case docs
or discovered by the community.

---

## Section 15: Operational Behavior and Edge Cases

**What to research:**
- Failure modes beyond error codes (eventual consistency delays,
  silent failures, partial failures)
- Performance characteristics docs don't mention
  (what's fast, what's slow, what's unreliable)
- Behavioral quirks (timezone handling, Unicode normalization,
  concurrent write behavior, midnight UTC edge cases)
- Eventual consistency windows (how long until data propagates?)
- What happens when referenced objects are deleted?

**Where to find it:**
- GitHub issues (especially closed ones with "wontfix")
- Stack Overflow edge case questions
- Production incident reports / postmortems
- WebSearch: `{tool} edge cases gotchas production issues`

**What "done" looks like:**
Can predict behavior in untested scenarios. Knows what
will break before it breaks.

**Common pitfall:**
Assuming the API behaves exactly as documented. Edge cases
live in GitHub issues, not in official docs.

---

## Section 16: Ecosystem Position and Composition

**What to research:**
- Where does this tool sit in a typical data architecture?
  (System of record, processing layer, presentation layer)
- Natural complements (tools designed to work together)
- Forced integrations (tools that seem compatible but aren't)
- Integration anti-patterns (combinations that seem obvious but fail)
- Data handoff patterns between tools (what maps cleanly, where
  transformation is needed, where fidelity is lost)

**Where to find it:**
- Integration marketplace / partners page
- "X + Y" tutorials and architecture guides
- WebSearch: `{tool} integration architecture best practices`

**What "done" looks like:**
Can recommend whether to use this tool or an alternative
for a given architecture. Knows which tools pair well and
which combinations to avoid.

**Common pitfall:**
Treating every tool as standalone. In practice, tools
compose — the value is in the composition, not isolation.

---

## Section 17: Trajectory and Evolution

**What to research:**
- Where is the tool heading? (product roadmap, founder statements)
- What features are being de-emphasized or deprecated?
- What's getting increased investment?
- Community-discovered patterns the company later adopted
- Deprecation signals (endpoints with "v2" alternatives,
  docs pages getting less love, features removed from UI)

**Where to find it:**
- Changelogs and release notes
- Roadmap pages (public if available)
- Founder/CEO tweets, blog posts, conference talks
- WebSearch: `{tool} roadmap {current_year}` + `{tool} deprecations`

**What "done" looks like:**
Can warn against building on dead-end features. Knows
which new features to adopt early for competitive advantage.

**Common pitfall:**
Ignoring trajectory means building on features that
get deprecated 6 months later.

---

## Section 18: Conceptual Model and Solution Recipes

**What to research:**
- How should you THINK about this tool's domain?
  (What are the primitives? What are the verbs?)
- How do primitives compose into higher-order solutions?
- 3-5 concrete end-to-end recipes for common use cases
- The "right" mental model for approaching new problems
  with this tool

**Where to find it:**
- Official conceptual guides
- "Getting started" and "best practices" architecture docs
- Well-designed example applications
- WebSearch: `{tool} architecture patterns best practices`

**What "done" looks like:**
Can solve a new problem by composing known primitives
without searching docs. Has the mental model to reason
about novel situations.

**Example recipe:**
```
Notion: Full task management pipeline
1. Create database with Status, Priority, Assignee properties
2. Create pages via API as tasks come in
3. Use database query with filter for "Status = In Progress"
4. Webhook on page update → trigger downstream automation
5. Archive completed items via page update (Status = Done)
```

**Common pitfall:**
Listing features instead of composing them into solutions.
A recipe is a complete workflow, not a feature list.

---

## Section 19: Industry Expert and Cutting-Edge Usage

**What to research:**
- How are top practitioners and companies using this tool now?
- What frontier patterns exist that most users haven't discovered?
- What novel AI-powered automations have emerged?
- How are experts combining this tool with other tools and AI
  to multiply its capabilities?
- What conference talks, case studies, or showcases demonstrate
  pushing the tool's boundaries?

**Where to find it:**
- Expert blogs and "how I use X" threads
- Case studies on the tool's website
- Automation showcases (Zapier templates, Make scenarios)
- Community forums (advanced sections)
- Conference talks from current year
- WebSearch: `{tool} advanced workflows expert tips {current_year}`
- WebSearch: `{tool} AI integration automation {current_year}`
- WebSearch: `how top companies use {tool}`

**What "done" looks like:**
Can recommend cutting-edge approaches that put the user
ahead of 95% of the tool's userbase. Knows what's possible
at the frontier, not just what's documented.

**Common pitfall:**
Confusing "advanced" with "complex." The best cutting-edge
patterns are often elegantly simple — they just require
knowing the tool deeply enough to see the shortcut.

---

# Quality Gate

Before marking any tool skill complete, verify:

1. All 19 sections have real content (not placeholders)
2. Tier 1 sections contain exact numbers, signatures, and code
3. Tier 2 sections contain insights you can't find in the API reference
4. The best_practices.md is over 2000 characters
5. Source URLs are real and accessible
6. The created SKILL.md has an action-verb trigger description
7. The Gotchas section has at least 1 real entry (even if just
   "WebFetch failed on JS-rendered docs — used WebSearch instead")
>>>>>>> Stashed changes
