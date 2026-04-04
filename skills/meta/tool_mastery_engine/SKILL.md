---
name: tool-mastery-engine
description: >
  Use when ANY external tool, API, or SaaS platform is being utilized or
  about to be utilized — creating, reading, updating, syncing, scraping,
  sending, configuring, authenticating, debugging, setting up, connecting,
  or when the user expresses intent to use a tool ("I want to use Notion
  for X", "let's set up Calendly", "can we connect Stripe", "use Apify
  to scrape", "send this via SendGrid"). Covers: Notion, Stripe, Apify,
  Slack, Calendly, Shopify, SendGrid, Typeform, ManyChat, Discord, Twilio,
  HubSpot, Airtable, Zapier, and any other external tool/API/platform.
  Also triggers on unexpected API failures or tool version changes.
  Do NOT load for purely abstract comparisons with no intent to act
  ("which is better, Notion or Airtable?" with no follow-up action).
allowed-tools: "Read, Write, Edit, Bash, WebFetch, WebSearch"
effort: high
trigger: both
version: "3.0"
last_updated: "2026-04-04"
context: fork
---
<!-- claude-doc: auto-maintain -->


# Tool Mastery Engine

This skill ensures EOS operates at creator-level expertise
with every external tool it touches. Not beginner-level
(copies from docs). Not expert-level (knows rate limits).
Creator-level ��� knows why the tool was designed this way,
what hidden capabilities exist, how it composes with other
tools, and how industry experts push its boundaries.

The original Best Practices Principle (Research → Document →
Templatize → Instantiate → Improve) is now automated by
this engine.


## Current Tool Skills

!`python3 -c "
import os, re, datetime
tools_dir = '/opt/OS/skills/tools'
today = datetime.date.today()
print(f'Date: {today}')
print()
if not os.path.isdir(tools_dir):
    print('No tools directory found.')
else:
    for d in sorted(os.listdir(tools_dir)):
        skill = os.path.join(tools_dir, d, 'SKILL.md')
        if not os.path.isfile(skill):
            continue
        with open(skill) as f:
            content = f.read()
        lr = re.search(r'last_researched:\s*[\"'']?(\d{4}-\d{2}-\d{2})', content)
        av = re.search(r'api_version:\s*[\"'']?([^\"''\\n]+)', content)
        sv = re.search(r'sdk_version:\s*[\"'']?([^\"''\\n]+)', content)
        sc = re.search(r'speed_category:\s*[\"'']?([^\"''\\n]+)', content)
        lr_date = lr.group(1) if lr else '?'
        api_v = av.group(1).strip() if av else '?'
        sdk_v = sv.group(1).strip() if sv else '?'
        speed = sc.group(1).strip() if sc else 'medium'
        # Check staleness
        flag = ''
        if lr and lr_date != '?':
            age = (today - datetime.date.fromisoformat(lr_date)).days
            threshold = {'fast': 30, 'medium': 60, 'stable': 90}.get(speed, 60)
            if age > threshold:
                flag = f' ⚠ STALE ({age}d > {threshold}d)'
        print(f'  {d}: researched={lr_date} api={api_v} sdk={sdk_v} speed={speed}{flag}')
" 2>/dev/null`


## Decision Tree

Follow this exactly when a tool is being utilized:

### Step 1 — Identify the tool

What tool is being UTILIZED in the current task?
"Utilized" means any action: create, read, update, delete,
sync, scrape, send, configure, authenticate, debug, deploy,
monitor — or intent to do any of these.

### Step 2 — Normalize the name

**Alias resolution** — check this map BEFORE converting to snake_case.
If the user's term matches an alias, use the canonical name.

| User says | Canonical tool name |
|-----------|-------------------|
| postgres, postgresql, pg | neon_postgres |
| neon | neon_postgres |
| google sheets, gsheets | google_sheets |
| gcp, google cloud | google_cloud |
| meta, facebook (for DM/ads) | instagram |
| drizzle | drizzle_orm |

If no alias match, convert to snake_case for the directory name:
- Google Sheets → google_sheets
- ManyChat → manychat
- Claude Code → claude_code
- Anthropic API → anthropic_api

### Step 3 — Check for existing skill

Does `/opt/OS/skills/tools/{toolname}/SKILL.md` exist?

**IF `.creating` lock file exists** (`/opt/OS/skills/tools/{toolname}/.creating`):
  Skill creation is already in progress from another context.
  Do NOT attempt a second creation.
  Log: "Skill creation in progress for {tool}. Using best available
  context for now. Will apply full expertise when ready."
  Proceed with the task using general knowledge. Done.

**IF YES** → go to Step 4 (Load and Check Freshness)
**IF NO** → go to Step 5 (Create New Tool Skill)

### Step 4 — Load and check freshness

**Integrity check** (before loading):
1. Does `SKILL.md` exist AND contain >500 chars?
2. Does `references/best_practices.md` exist AND contain all 19 section headers?
   (Authentication, Core Operations, Pagination, Rate Limits, Error Codes,
   SDK Idioms, Anti-Patterns, Data Model, Webhooks, Limits, Cost Model,
   Version Pinning, Design Intent, Problem-Solution Map, Operational Behavior,
   Ecosystem Position, Trajectory, Conceptual Model, Industry Expert)

**Both YES** → proceed to freshness check below.
**Either NO** → skill is CORRUPT. Log: "Skill for {tool} is corrupt
(missing or incomplete files). Routing to Re-Research."
→ Re-Research Flow (below). Do NOT apply a corrupt skill.

**Freshness check** (if integrity passed):
Read the tool skill:
1. Read `/opt/OS/skills/tools/{toolname}/SKILL.md`
2. Read `/opt/OS/skills/tools/{toolname}/references/best_practices.md`

Check if the skill needs updating
(read references/update_intelligence.md for full trigger list):
- Is `last_researched` past the threshold for its speed_category?
  (fast=30d, medium=60d, stable=90d)
- Has the tool's API or SDK version changed since `api_version`/`sdk_version`?
- Did an API call fail unexpectedly in this session?

**If update needed** → Re-Research Flow (below), then apply expertise.
**If current** → Apply the loaded expertise to the current task. Done.

### Step 5 — Create new tool skill

Inform the user: "No tool skill exists for {tool}. Creating one
now — this ensures creator-level usage in all future sessions."

**Create Flow:**

0. Create lock file:
   ```bash
   touch /opt/OS/skills/tools/{toolname}/.creating
   ```
   This prevents concurrent creation attempts (see Step 3 check).

1. Run the scaffold script:
   ```
   python3 /opt/OS/skills/meta/tool_mastery_engine/scripts/scaffold_tool_skill.py {toolname}
   ```

2. Check `references/tool_doc_registry.md` for known docs URL.
   If not listed, WebSearch:
   `{tool} official documentation site:docs.{tool}.com OR site:developer.{tool}.com`

3. **Research Phase 0 — Context7 Fast Pass (SDK surface):**
   Use Context7 MCP to pull authoritative SDK documentation first.
   This is the fastest path to exact method signatures, parameter
   types, return shapes, and code examples.

   a. Resolve the library ID:
      `mcp__plugin_context7_context7__resolve-library-id`
      with libraryName="{tool}" or the SDK package name.

   b. Query docs with up to 3 targeted calls:
      `mcp__plugin_context7_context7__query-docs`
      - Query 1: "Schema/setup, configuration, authentication, getting started"
      - Query 2: "Core operations, CRUD, API methods, parameters, return types"
      - Query 3: "Advanced patterns, transactions, error handling, edge cases"

   c. Extract from results: exact method signatures, parameter types,
      return shapes, code examples, and configuration patterns.
      This populates Tier 1 sections 1-3, 6, 8, and 10.

   d. Note gaps — anything Context7 returned "not covered" or shallow
      results on. These gaps drive the parallel research agents below.

   **If Context7 has no results for this tool** (not in their corpus),
   skip to Phase 1 and run all research via WebSearch/WebFetch.

4. **Research Phases 1-3 — Parallel Subagents:**
   Launch 2 subagents in parallel (single message, both Agent calls).
   Each subagent writes its findings to a temp file, then the main
   thread synthesizes into the final SKILL.md and best_practices.md.

   **Subagent A — Operational Knowledge (Tier 1 gaps + sections 4-5, 7, 9-12):**
   Fills gaps Context7 missed plus sections requiring community sources.
   - WebSearch: `{tool} rate limits quotas throttling`
   - WebSearch: `{tool} error codes error handling recovery`
   - WebSearch: `{tool} common mistakes anti-patterns gotchas`
   - WebSearch: `{tool} webhooks events real-time`
   - WebSearch: `{tool} pricing cost model billing API`
   - WebSearch: `{tool} changelog breaking changes deprecations {current_year}`
   - WebFetch official docs pages for: rate limits, errors, webhooks, pricing
   - WebFetch any Context7 gaps identified in Phase 0 step (d)
   Writes to: `/tmp/{toolname}_operational.md`

   **Subagent B — Creator Intelligence (Tier 2, sections 13-19):**
   Insights that don't exist in API documentation.
   - WebSearch: `{tool} founder philosophy design decisions`
   - WebSearch: `{tool} architecture blog engineering`
   - WebSearch: `{tool} hidden features power user tips`
   - WebSearch: `{tool} vs alternatives tradeoffs`
   - WebSearch: `{tool} advanced workflows expert tips {current_year}`
   - WebSearch: `{tool} case study automation {current_year}`
   - WebSearch: `how top companies use {tool}` OR `{tool} best implementations`
   - WebSearch: `{tool} AI integration automation patterns {current_year}`
   - WebSearch: `{tool} roadmap deprecations {current_year}`
   - Look for novel applications, frontier patterns, unconventional uses
   Writes to: `/tmp/{toolname}_creator_intel.md`

5. **Handle subagent failures before synthesizing.**

   Check `/tmp/{toolname}_operational.md`:
   - If missing or empty after Subagent A completes:
     Log: "Subagent A failed — falling back to sequential
     WebSearch for operational sections."
     Run Subagent A's WebSearch queries sequentially in the
     main thread. Write results to `/tmp/{toolname}_operational.md`.

   Check `/tmp/{toolname}_creator_intel.md`:
   - If missing or empty after Subagent B completes:
     Log: "Subagent B failed — sections 13-19 will be incomplete."
     Proceed with available content.
     Mark best_practices.md with at the top:
     `<!-- INCOMPLETE: creator_intel subagent failed — sections 13-19 need manual research -->`

6. **Synthesize all research.**
   Read `/tmp/{toolname}_operational.md` and `/tmp/{toolname}_creator_intel.md`.
   Combine with Context7 results from Phase 0.

   **Read references/research_protocol.md NOW.**
   Follow ALL 19 sections. No shortcuts. This is the quality bar.

6. Fill the SKILL.md with:
   - Tool identity and design philosophy summary
   - EOS integration points (which agents, which workflows)
   - Authentication setup with exact details
   - Quick reference with exact code examples
   - Conceptual model (how to think about this tool)
   - Gotchas section (seed with at least 1 from research)

7. Fill references/best_practices.md with all 19 sections:
   - Tier 1 (1-12): Technical Mastery — Context7 output + Subagent A
   - Tier 2 (13-19): Creator Intelligence — Subagent B output

8. Write an action-verb trigger description for the created SKILL.md.
   Make it specific to this tool's operations so it fires independently
   in future sessions without needing the engine.

   Example for Notion:
   "Use when creating, querying, or updating Notion pages, databases,
   or blocks via the Notion API. Also use when syncing data to/from
   Notion or debugging Notion integration issues."

9. Sync to Neon:
    ```python
    python3 -c "
    import sys, uuid; sys.path.insert(0, '/opt/OS')
    from eos_ai.db import get_conn
    from eos_ai.context import load_context_from_env
    from pathlib import Path
    ctx = load_context_from_env()
    path = '/opt/OS/skills/tools/{toolname}/SKILL.md'
    with get_conn(ctx.org_id) as cur:
      cur.execute('''
        INSERT INTO skills (id, org_id, name, content, version)
        VALUES (%s,%s,%s,%s,1)
        ON CONFLICT (org_id, name) DO UPDATE SET content=EXCLUDED.content
      ''', (str(uuid.uuid4()), ctx.org_id,
        '{toolname}', Path(path).read_text()))
      print('Synced to Neon')
    "
    ```

10. Clean up temp files:
    ```bash
    rm -f /tmp/{toolname}_operational.md /tmp/{toolname}_creator_intel.md
    ```

11. Run verification (below).

After creation, apply the new expertise to the current task.


## Re-Research Flow

When an existing tool skill needs updating:

1. Read the existing SKILL.md and references/best_practices.md
2. Identify what triggered the update (staleness, version, failure, manual)
3. **Context7 version check:** Query Context7 for the tool to compare
   current SDK signatures against what's documented. Note any new
   methods, changed parameters, or deprecated patterns.
4. **Launch 2 parallel subagents:**

   **Subagent A — Technical Updates:**
   - WebSearch: `{tool} API changelog {current_year}` +
     `{tool} release notes {current_year}` +
     `{tool} breaking changes`
   - WebFetch the source_url from the skill's frontmatter
   - If version changed: WebSearch
     `{tool} migration guide {old_version} to {new_version}`
   - Check for new hidden capabilities or deprecated features
   - WebFetch any Context7 gaps from step 3
   Writes to: `/tmp/{toolname}_update_technical.md`

   **Subagent B — Intelligence Updates:**
   - Check for new industry expert patterns and cutting-edge usage
   - WebSearch: `{tool} advanced workflows {current_year}`
   - WebSearch: `{tool} roadmap deprecations {current_year}`
   Writes to: `/tmp/{toolname}_update_intel.md`

5. Synthesize updates from both subagents + Context7 diff
6. Update changed sections in best_practices.md
   **Preserve:** EOS Usage Patterns, Gotchas, Composition Patterns
   **Update:** technical sections, trajectory, industry expert
7. Update frontmatter: last_researched, api_version, sdk_version
8. If failure-triggered: add the failure and fix to Gotchas
   and Operational Behavior sections
9. Clean up: `rm -f /tmp/{toolname}_update_technical.md /tmp/{toolname}_update_intel.md`


## Research Quality Standard

Read references/research_protocol.md before researching ANY tool.

The bar is creator-level — know the tool like you built it.

**Technical Mastery (sections 1-12):** exact method signatures,
exact rate limit numbers, exact error codes. Not summaries.
Not approximations. Real data from official docs.

**Creator Intelligence (sections 13-19):** why it was designed
this way, what problems it actually solves beyond the obvious,
what hidden capabilities most users miss, how it composes
with other tools, where it's heading, how to think about the
domain, and how industry experts push its boundaries right now.

A tool skill with only technical sections produces expert-level
work. Including creator intelligence produces creator-level
work — the AI leverages maximum capabilities and knows frontier
patterns that put the user ahead of 95% of the tool's userbase.


## Verification

After creating or updating any tool skill:

```python
python3 -c "
import sys
toolname = '{toolname}'  # replace with actual
path = f'/opt/OS/skills/tools/{toolname}/SKILL.md'
bp = f'/opt/OS/skills/tools/{toolname}/references/best_practices.md'
content = open(path).read()
bp_content = open(bp).read()
checks = [
    (len(content) > 500, f'SKILL.md too short: {len(content)} chars'),
    ('last_researched' in content, 'Missing last_researched'),
    ('source_url' in content, 'Missing source_url'),
    ('api_version' in content, 'Missing api_version'),
    ('## Authentication' in content, 'Missing Authentication section'),
    ('## Gotchas' in content, 'Missing Gotchas section'),
    (len(bp_content) > 2000, f'best_practices.md too short: {len(bp_content)} chars'),
    ('## Rate Limits' in bp_content, 'Missing Rate Limits'),
    ('## Error Codes' in bp_content, 'Missing Error Codes'),
    ('## SDK Idioms' in bp_content, 'Missing SDK Idioms'),
    ('## Design Intent' in bp_content, 'Missing Design Intent'),
    ('## Problem-Solution Map' in bp_content, 'Missing Problem-Solution Map'),
    ('## Operational Behavior' in bp_content, 'Missing Operational Behavior'),
    ('## Ecosystem Position' in bp_content, 'Missing Ecosystem Position'),
    ('## Trajectory' in bp_content, 'Missing Trajectory'),
    ('## Conceptual Model' in bp_content, 'Missing Conceptual Model'),
    ('## Industry Expert' in bp_content, 'Missing Industry Expert'),
]
failed = [msg for ok, msg in checks if not ok]
if failed:
    print('FAIL:', '; '.join(failed))
else:
    print('PASS: Creator-level tool skill verified')
"
```


## Gotchas

- WebFetch fails on JS-rendered docs (React/Next doc sites).
  Fall back to WebSearch for specific topics. Search for
  "raw" or "markdown" versions of docs if available.
- Skill registry MIN_CONTENT_LENGTH is 500 chars — skills
  below this are silently ignored by the registry.
- Tool names: always normalize to snake_case
  (Google Sheets → google_sheets, ManyChat → manychat).
- Shared auth across tool suites (Google suite, Meta suite).
  Cross-reference auth in the tool skill.
- Never create tool skills from blog posts or tutorials alone.
  Official docs and creator's own words are primary sources.
  Blog posts supplement Creator Intelligence sections only.
- Preserve EOS Usage Patterns, Gotchas, and Composition
  Patterns during re-research. This is production knowledge
  that docs cannot provide.
- AI tools (Claude Code, Anthropic API, OpenAI, etc.) change
  almost daily. Use 30-day threshold, not 90.
- Context7 only covers tools in its corpus (major open-source libs).
  SaaS APIs (Calendly, ManyChat, Typeform) may not be indexed.
  If `resolve-library-id` returns no results, skip Phase 0 entirely.
- Context7 is strong on SDK surface (methods, params, examples) but
  weak on operational knowledge (rate limits, error codes, edge cases)
  and absent on creator intelligence (design philosophy, trajectory).
  Never rely on Context7 alone for a complete tool skill.
- Parallel subagents must write to /tmp/ files, not directly to the
  skill directory. The main thread synthesizes to avoid write conflicts.
- Created tool skill trigger descriptions must use action verbs
  specific to that tool's operations, so they fire independently
  in future sessions without needing this engine.
- Creator Intelligence sections (13-19) require different
  research queries than technical sections — founder interviews,
  engineering blog posts, conference talks, expert showcases.
  These are NOT in standard API documentation.
- best_practices.md must exceed 2000 chars. Creator-level
  expertise requires depth. If under 2000, research is incomplete.
- When a tool is part of a larger platform (e.g., Gmail is part
  of Google Workspace), document the specific tool, not the
  entire platform. Cross-reference sibling tools.
