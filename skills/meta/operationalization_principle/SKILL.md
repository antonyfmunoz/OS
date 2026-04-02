---
name: operationalization-principle
description: "Invoke after any successful execution, workflow completion, or discovered pattern. Use when something worked and should never have to be rebuilt from scratch. Ensures EOS compounds — every success becomes permanent infrastructure."
allowed-tools: "Read, Write, Edit"
effort: medium
trigger: both
version: "1.0"
last_updated: "2026-04-02"
---

# The Operationalization Principle

## What This Principle Is

This is the second execution mechanism
for EOS's world-class standard principle.
The best practices principle ensures you
start from the right baseline. This
principle ensures every successful execution
raises that baseline permanently.

The principle: done successfully once —
documented — skill or workflow template —
never from scratch again — always improvable.

EOS compounds because of this principle.
Every success is captured. Every failure
adds a Gotcha. The system gets smarter
with every cycle.

## The Four-Stage Cycle

### Stage 1 — Done Successfully Once

The trigger: something worked.
A close happened. An opener got replies.
A hook drove DMs. A workflow ran cleanly.
A configuration produced the right output.

Not theoretical success. Actual execution
with a real outcome that confirms the
pattern works.

Questions:

- What exactly was done?
- What was the input that triggered it?
- What was the output that confirmed success?
- Could someone reproduce this from a
  description alone?

### Stage 2 — Document

Capture the pattern precisely.
Not "we did something like this" —
the exact steps, inputs, decisions, and
outputs that produced the success.

What to document:

- The trigger condition (when to use this)
- The exact steps in sequence
- The decision points and how to decide
- The expected output format
- What failure looks like (so it's caught)
- The measurement (how to know it worked)

### Stage 3 — Skill or Workflow Template

Turn the documentation into a reusable
artifact in EOS:

**If it's a capability** — build a skill
  Location: /opt/OS/skills/[domain]/[name]/
  Format: SKILL.md with proper frontmatter
  Include: trigger, effort, Gotchas, dynamic
  context injection, verification step

**If it's a recurring workflow** — slash command
  Location: /opt/OS/.claude/commands/
  Format: markdown with inline bash for
  pre-computed context

**If it's a configuration pattern** —
  canonical template
  Location: /opt/OS/templates/
  Format: matches the domain template format

**If it's a rule** — CLAUDE.md entry
  Format: "After [trigger]: always [behavior]"
  or "Never [the anti-pattern]"
  Keep CLAUDE.md under 200 lines

**If it's an agent behavior** —
  soul doc update or skill
  Soul doc: if it's character or judgment
  Skill: if it's a repeatable capability

### Stage 4 — Improve From Outcomes

After the skill or template is used again:

- Did it work the same way?
- Did the Gotchas catch real failures?
- What edge case appeared that wasn't documented?
- What shortcut appeared that should be added?

Update the skill. Bump the version.
Add the Gotcha. Remove what didn't apply.

The skill improves with every use.
That improvement is permanent.

## The Test for Operationalization

Ask three questions:

1. Could a new Claude Code session execute
   this correctly from the skill alone —
   with no other context?
2. Would a world-class practitioner in this
   domain recognize this as the right approach?
3. Does it include a verification step so
   the agent can confirm it worked?

If yes to all three: operationalized correctly.
If no to any: incomplete — keep refining.

## What Gets Operationalized in EOS

### Always operationalize:

- Any outreach sequence that gets replies
- Any close sequence that converts
- Any research process that finds real signal
- Any workflow that runs more than once
- Any configuration that produces correct output
- Any hook that fires correctly
- Any agent interaction that produces
  world-class output

### Never operationalize prematurely:

- One data point is not a pattern
- One successful close is not a system
- Wait for repeatability — same inputs
  producing same outputs across multiple
  instances — before capturing as template

## Where This Principle Lives in EOS

**principle_engine.py**: injected into
every agent as an operational standard.
Every successful agent output becomes
a candidate for operationalization.

**CLAUDE.md**: CC sessions apply this
after every successful build. Mistakes
become rules. Successes become skills.

**feedback_loop.py**: the data layer.
Every outcome logged here is raw material
for operationalization. When a pattern
emerges in the feedback data — that's
the operationalization trigger.

**This skill**: loaded when something
worked and needs to be captured.

**Canonical templates**: the output of
this principle applied across domains.

## How to Apply Right Now

After any successful EOS execution:

1. Determine the artifact type:
   skill, command, template, rule, or soul doc

2. Build the artifact using the correct
   format for that type

3. Add verification step before marking done

4. Add to the relevant registry or directory

5. Update CLAUDE.md if it's a daily rule

## Anti-Patterns

Never do this:

- Execute something successfully and move on
  without capturing the pattern
- Build the same workflow twice from scratch
- Operationalize from one data point
- Build a skill without a Gotchas section
- Build a skill without a verification step
- Operationalize a workflow that hasn't
  been verified to work yet
- Write a skill so prescriptive it can't
  adapt to context variation

## Gotchas

- The pressure to move to the next thing
  is always wrong when something just worked.
  Capture it first. Move after.
- Skills without Gotchas sections degrade —
  failures repeat because they weren't
  documented.
- The operationalization step takes 15 minutes.
  The cost of not doing it is rebuilding
  from scratch the next time — which takes
  hours.
- Not everything that worked once is a
  pattern. Wait for three confirmed instances
  before calling it a template.
- When in doubt about artifact type: if it's
  invoked — skill. If it's always true —
  CLAUDE.md rule. If it's reusable structure
  — template.
