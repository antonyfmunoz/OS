<<<<<<< Updated upstream
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
version: "4.0"
last_updated: "2026-04-28"
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
            threshold = {'fast': 14, 'medium': 45, 'stable': 90, 'slow': 120}.get(speed, 45)
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
  (fast=14d, medium=45d, stable=90d, slow=120d)
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


## Incremental Update Flow

Updates are NOT full re-research. After the first creation pass,
updates only diff against what changed. The 19-section research
protocol is for first-time creation ONLY.

### What triggers an update

- **Staleness** — `check_skill_staleness.py` flags skill past threshold
- **Version change** — API or SDK version changed since last research
- **Runtime failure** — an API call failed unexpectedly
- **External intelligence** — a community skill repo or real-user
  pattern was discovered that our skill doesn't cover
- **Automated cron** — scheduled agent runs weekly (see Automation below)

### Update steps (incremental, not from zero)

1. Read existing SKILL.md and references/ (know what we HAVE)
2. Identify the trigger (staleness, version, failure, external source)

3. **Source layer 1 — Official changelog/docs (what changed):**
   - Context7 query for version diff (new methods, deprecated patterns)
   - WebFetch the source_url from frontmatter (official docs)
   - WebSearch: `{tool} changelog release notes {current_year}`
   - If version changed: `{tool} migration guide {old} to {new}`

4. **Source layer 2 — Community intelligence (what real users found):**
   This is what separates creator-level from expert-level.
   - WebSearch: `{tool} github:* best practices OR skill OR config`
     (find community skill repos like shanraisshan/claude-code-best-practice)
   - WebSearch: `{tool} advanced tips edge cases {current_year}`
   - WebSearch: `{tool} production gotchas lessons learned`
   - WebSearch: `site:github.com {tool} awesome-{tool} OR {tool}-examples`
   - If a GitHub repo has structured knowledge (README, docs/, references/),
     ABSORB it: extract the knowledge into our references/, then our system
     owns it. Same pattern as: external CC skill → our claude_code tool skill.
   - Check for Obsidian community patterns if the tool has an Obsidian
     plugin or integration (vault templates, dataview queries, etc.)

5. **Source layer 3 — Frontier patterns (what experts push):**
   - WebSearch: `{tool} creator founder design philosophy`
   - WebSearch: `{tool} conference talk OR workshop {current_year}`
   - WebSearch: `how top companies use {tool} {current_year}`

6. **Diff and merge** — only update sections where sources found new info.
   **Preserve:** EOS Usage Patterns, Gotchas (append only), Composition Patterns
   **Update:** technical sections that changed, trajectory, industry expert
   **Add:** any new Gotchas from community intelligence

7. Update frontmatter: `last_researched`, `api_version`, `sdk_version`
8. If failure-triggered: add the failure and fix to Gotchas
9. Run verification
10. If this is the `claude_code` skill: run CC artifact cascade

### The absorption pattern

When you find an external repo that has structured tool knowledge:

1. **Evaluate** — is the content higher quality than what we have?
2. **Extract** — pull the knowledge into our `references/` directory
3. **Merge** — integrate into existing sections, don't duplicate
4. **Create best_practices.md** — the absorbed content goes into SKILL.md
   for quick reference, but the 19-section BP file MUST also be created.
   A tool skill without best_practices.md is incomplete regardless of
   how good the SKILL.md is. This is non-negotiable.
5. **Delete the external dependency** — our system now owns this knowledge
6. **Add the repo as a research source** in `references/update_intelligence.md`
   so future re-research checks it again
7. **Run quality audit** — `python3 scripts/tme_quality_audit.py {toolname}`
   to verify the absorbed skill meets the standard

This is how the TME stays ahead: it doesn't just read official docs,
it consumes the best community knowledge and makes it its own.


## Automation

The TME MUST be self-triggering. Manual staleness checks failed —
the checker existed for 22 days and nobody ran it.

### Staleness thresholds by speed_category

AI and developer tools ship daily. Infrastructure tools ship
yearly. The check frequency must match the tool's rate of change.

| speed_category | Stale after | Check frequency | Examples |
|---------------|-------------|-----------------|----------|
| fast          | 14 days     | daily           | claude_code, anthropic_api, google_gemini, ollama, openai |
| medium        | 45 days     | every 3 days    | notion, discord, apify, stripe, drizzle_orm |
| stable        | 90 days     | weekly          | systemd, tmux, docker, python, bash |
| slow          | 120 days    | biweekly        | acrobat, photoshop, lightroom, obs |

`fast` = AI/ML tools, rapidly evolving APIs, tools with weekly releases
`medium` = SaaS APIs, frameworks with monthly releases
`stable` = Infrastructure, runtimes, mature tools with quarterly releases
`slow` = Desktop software, creative tools with infrequent updates

### Scheduled staleness sweep (tiered frequency)

Three scheduled agents, each at a different cadence:

```
Schedule: 0 6 * * *   (daily)
Task: TME fast-tool sweep
Scope: speed_category=fast only
Steps:
  1. python3 scripts/tme_staleness_sweep.py --speed fast
  2. For each stale: run Incremental Update Flow
  3. python3 scripts/tme_quality_audit.py --speed fast --quiet
  4. Post summary to Discord #agent-activity

Schedule: 0 6 */3 * * (every 3 days)
Task: TME medium-tool sweep
Scope: speed_category=medium only
Steps:
  1. python3 scripts/tme_staleness_sweep.py --speed medium
  2. For each stale: run Incremental Update Flow
  3. python3 scripts/tme_quality_audit.py --speed medium --quiet

Schedule: 0 6 * * 1   (weekly, Monday)
Task: TME full sweep
Scope: all speed categories (catches stable + slow)
Steps:
  1. python3 scripts/tme_staleness_sweep.py
  2. python3 scripts/tme_quality_audit.py --all --quiet
  3. For each stale: run Incremental Update Flow
  4. Post summary to Discord #agent-activity
```

### SessionStart hook (lightweight check)

The SessionStart hook already runs. Add a fast staleness flag:

```bash
python3 -c "
import sys; sys.path.insert(0, '/opt/OS')
from scripts._tme_common import load_all_skills, freshness_window, days_since
stale = []
for s in load_all_skills():
    lr = s.frontmatter.get('last_researched')
    speed = s.frontmatter.get('speed_category', 'medium')
    if lr and days_since(lr) > freshness_window(speed):
        stale.append(s.slug)
if stale:
    print(f'[TME] {len(stale)} stale skills: {\" \".join(stale[:5])}')
" 2>/dev/null
```

### Failure-triggered update

When any tool API call fails unexpectedly in a session:
1. Check if a tool skill exists for that tool
2. If yes: add the failure to Gotchas immediately
3. Flag the skill for incremental update on next scheduled run


## Research Quality Standard

Read references/research_protocol.md before researching ANY tool.

The bar is creator-level — know the tool like you built it.

### What "creator-level" actually means

Having 19 section headers is not quality. Having 19 sections
with real, actionable content is. The difference:

**Expert-level (what official docs produce):**
- "Stripe uses OAuth2 for authentication"
- "Rate limit is 100 req/sec"
- Lists features the tool markets

**Creator-level (what the TME must produce):**
- Exact scopes needed per endpoint, token lifetime, refresh
  mechanism, EOS env var mapping, multi-tenant considerations
- Rate limit numbers + burst vs sustained + backoff strategy +
  what the rate limit headers actually look like + what happens
  when you hit the limit at 2am with no human watching
- Real production gotchas from GitHub issues and SO that the
  official docs will never mention
- How the founder thinks about the tool's design space, what
  they consciously chose NOT to build, what mental model they
  optimized for
- Specific EOS integration: which agents use it, which workflows,
  what broke in production and how we fixed it

### Content depth markers (not just section headers)

Every best_practices.md section MUST contain:

**Tier 1 sections (1-12):**
- Exact numbers (rate limits, timeouts, max sizes — not "high" or "fast")
- Exact code (method signatures with parameter types, not pseudocode)
- Exact error shapes (JSON response bodies, not just status codes)
- At least 1 anti-pattern with wrong code → correct code

**Tier 2 sections (13-19):**
- Named sources (founder name, blog post title, conference — not "reportedly")
- Specific insight that contradicts or goes beyond official docs
- At least 1 recommendation the user wouldn't get from reading the docs

**Community intelligence (Tier 3, embedded in relevant sections):**
- At least 3 gotchas sourced from GitHub issues, SO, or production experience
- At least 1 composition pattern with another tool EOS uses
- Real failure modes, not theoretical ones

### EOS Usage Patterns (required section)

Every best_practices.md MUST include a final section:

```
## EOS Usage Patterns
- Which EOS agents/services use this tool
- How the tool is configured in EOS (.env vars, Docker mounts, etc.)
- Known EOS-specific gotchas (things that broke for us)
- Integration with model_router, cognitive_loop, or other EOS infra
```

If EOS doesn't use the tool yet, write:
"Not yet integrated. Planned use: [description]."

### The quality bar in one sentence

If someone reads the skill and still needs to open the official
docs to write working code, the skill has failed.


## Quality Tiers

Not all tools need the same depth. A simple CLI wrapper
doesn't need 13 reference files. A tool that IS the
development environment does.

### Tier assignment

| Criteria | Tier | Min BP chars | Min refs | Min gotchas | EOS section |
|----------|------|-------------|----------|-------------|-------------|
| Tool EOS is BUILT INSIDE (Claude Code) | Critical | 20000 | 5+ | 10+ | required |
| Tool called in production daily (Discord, Neon, Gemini) | Core | 15000 | 1+ | 5+ | required |
| Tool used regularly (Apify, Notion, Groq) | Standard | 8000 | 1 | 3+ | required |
| Tool used occasionally (Clo3D, Rumble) | Light | 5000 | 1 | 1+ | optional |

### Quality checks (beyond size)

Size alone doesn't guarantee quality. A 40K char file of
reformatted docs is worse than a 15K file with real depth.
Every skill must pass these content checks:

1. **Code examples are real** — actual method signatures with
   parameter types and return shapes, not pseudocode
2. **Numbers are exact** — rate limits, timeouts, max sizes
   are specific numbers, not "high" or "varies"
3. **Gotchas are from production** — at least 1 gotcha per
   tool from a real failure (GitHub issue, SO, or our own EOS)
4. **Community sources cited** — at least 1 insight per tool
   from outside official docs (GitHub repo, SO answer, blog)
5. **EOS Usage Patterns present** — how EOS actually uses the
   tool (agents, services, env vars, known issues)
6. **Anti-patterns show wrong→right** — not just "don't do X"
   but actual wrong code and actual correct code

Run `python3 scripts/tme_quality_audit.py` to check all skills.

### When to split into multiple reference files

A single `best_practices.md` works for most tools. Split when:
- The tool has 3+ distinct concern domains (settings, plugins, hooks)
- A single section exceeds 500 lines
- Different team members would reference different sections
- The tool is in the Critical tier

Split pattern: `references/{concern}_reference.md`
Example (claude_code): `settings_reference.md`, `skills_reference.md`,
`subagents_reference.md`, `mcp_reference.md`, etc.

### CC artifact compliance (applies to claude_code skill ONLY)

The claude_code tool skill owns the standards for ALL Claude Code
artifacts in EOS. When this skill updates, it MUST cascade to:
- `.claude/settings.json` — validate against CC schema
- `.claude/skills/*.md` — validate frontmatter (name, description as trigger, allowed-tools)
- `.claude/agents/*.md` — validate frontmatter (name, description, model, tools)
- `CLAUDE.md` files — validate no stale CC references
- `skills/meta/claude_code_best_practices/SKILL.md` — sync standards

This is the ONLY tool skill with cascade responsibilities.
Other tool skills are self-contained.


## Verification

After creating or updating any tool skill, run:

```bash
python3 scripts/tme_quality_audit.py {toolname}
```

This checks both structural requirements (frontmatter, sections)
and content quality (code examples, exact numbers, community
sources, EOS usage patterns).

### System-wide quality audit

Run periodically to catch drift across all skills:

```bash
# Full quality audit — checks content depth, not just structure
python3 scripts/tme_quality_audit.py --all

# Staleness check
python3 scripts/tme_staleness_sweep.py

# Combined (weekly scheduled agent runs both)
python3 scripts/tme_quality_audit.py --all --quiet && python3 scripts/tme_staleness_sweep.py
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
  almost daily. Use 14-day threshold with daily checks, not 90.
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
- The TME failed to keep its own claude_code skill current for 24 days.
  Root cause: no automated staleness trigger. The checker existed but
  nobody ran it. Fixed: scheduled agent + SessionStart hook.
- 77/91 tool skills had only 1 reference file (best_practices.md).
  A single monolithic file is insufficient for complex tools. Quality
  Tiers now define when to split into multiple reference files.
- The TME never consumed external community knowledge repos (GitHub
  skill repos, awesome-X lists, community configs). Research was
  limited to official docs + WebSearch. The Absorption Pattern in the
  Incremental Update Flow now addresses this.
- 2000 char minimum for best_practices.md was too low. The external
  CC reference we absorbed had 66K chars for settings alone. Quality
  Tiers now set minimums by tool importance (5K-20K chars).
- An external skill repo (shanraisshan/claude-code-best-practice) had
  to teach us what our own system should have known. The TME must
  treat itself as a tool it maintains — Claude Code IS a tool, and
  the claude_code skill must be kept at Critical tier quality.
- The meta skill (claude_code_best_practices) maintained its own copy
  of CC facts instead of reading from the TME tool skill. This caused
  drift — the meta skill taught autoDreamEnabled as valid while the
  setting never existed. Meta skills must READ from tool skills, not
  maintain parallel copies.
- Skill descriptions that say "This skill does X" instead of "Use when X"
  don't auto-trigger in Claude Code. Every tool skill and CC-native skill
  must use the trigger condition pattern.
- Absorbing external skills into TME creates SKILL.md but NOT
  best_practices.md. The absorption pattern must include creating
  the 19-section BP file, not just moving the surface-level content.
  5 absorbed Obsidian/utility skills all graded D until BP was created.
- 52 of 96 skills were missing trigger/effort/context frontmatter fields.
  These were added as TME standards after the original batch creation.
  Backfill script at /tmp/fix_frontmatter.py. Fixed: all 96 now 10/10.
- Having 19 section headers is not quality. The TME was checking for
  section names but not content depth. Skills passed structural checks
  while lacking exact numbers, community sources, and EOS usage patterns.
  Fixed: tme_quality_audit.py now checks 6 depth markers per skill.
- Staleness thresholds were too generous for AI tools (30 days). Claude
  Code, Anthropic API, Gemini, and Ollama ship changes weekly. Tightened
  fast category from 30 to 14 days with daily automated checks.
  stable and slow categories remain at 90/120 days respectively.
=======
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
>>>>>>> Stashed changes
