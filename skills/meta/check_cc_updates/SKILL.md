---
name: check-cc-updates
description: "Run when Claude Code version changes or weekly to check for new Boris patterns. Fetches official changelog and Boris's latest threads. Diffs against current best practices skill. Proposes updates for human approval. Never updates automatically without approval."
allowed-tools: "Read, WebFetch, WebSearch, Write, Edit, Bash"
effort: high
trigger: scheduled
version: "1.0"
last_updated: "2026-04-02"
---

# Check Claude Code Updates

## Purpose

Keeps /claude-code-best-practices current
automatically. Runs when:

1. SessionStart detects version change
2. Weekly /loop fires
3. Manual invocation

## Execution Steps

### Step 1 — Check current version

!`claude --version 2>/dev/null | head -1`

Compare against cc_version_at_research in
/opt/OS/skills/meta/claude_code_best_practices/SKILL.md

If same version AND checked within 7 days:
Report "No updates needed" and stop.

### Step 2 — Fetch official changelog

Fetch: https://code.claude.com/docs/en/changelog

Extract entries newer than cc_version_at_research.

Identify:

- New hook events
- New CLI flags
- New settings options
- New bundled skills
- Behavior changes that affect EOS

### Step 3 — Fetch Boris's latest

Fetch: https://howborisusesclaudecode.com

Check date of most recent thread vs
boris_threads_captured in skill frontmatter.

If new thread exists: extract new patterns.

### Step 4 — Diff against current skill

For each new finding:

- Is it already in the skill? Skip.
- Is it relevant to EOS? Flag for addition.
- Does it contradict existing content?
  Flag as conflict requiring review.

### Step 5 — Produce update proposal

Format:

```
Claude Code Update Proposal
Version: [current] → [new]
Date: [today]

New Capabilities to Add:
[list each with where it goes in the skill]

Conflicts with Existing Content:
[list each with recommendation]

EOS Gap List Updates:
[what moves from Still Needed to Applied
 if new feature solves an existing gap]

Recommended Settings Changes:
[any settings.json updates needed]
```

### Step 6 — Wait for approval

Present the proposal. Do NOT apply changes.
Human reviews and approves specific items.
Only then apply the approved changes.
Update cc_version_at_research and last_researched.

## Gotchas

- Never auto-apply updates to settings.json.
  A bad settings change breaks 24+ agents.
- New CC features often require CC version
  update first: claude update
- Boris tips are advisory. Not all apply to
  EOS. Filter for relevance before proposing.
- If changelog is behind actual version,
  check GitHub: github.com/anthropics/claude-code
  CHANGELOG.md for the real source.
