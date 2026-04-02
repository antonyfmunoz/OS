---
name: best-practices-principle
description: "Invoke before building, configuring, or designing anything in EOS. Use when starting any new domain, tool integration, workflow, agent, or system component. Ensures EOS always operates at world-class standard and never starts from scratch like a beginner."
allowed-tools: "Read, WebFetch, WebSearch"
effort: high
trigger: both
version: "1.0"
last_updated: "2026-04-02"
context: fork
---

# The Best Practices Principle

## What This Principle Is

This is one of two execution mechanisms
for EOS's world-class standard principle.
The world-class standard says WHAT level
to operate at. This principle says HOW to
achieve and maintain that level in any
domain.

The principle: before building anything,
research the authoritative approach. Then
build from that baseline. Never start from
zero. Never start from assumptions.

## The Five-Stage Cycle

### Stage 1 — Research

Find the authoritative source for the domain.
Not a blog post. Not assumptions. The source
closest to ground truth:

- Official documentation (the tool maker)
- The creator of the tool (Boris Cherny
  for Claude Code, not a secondary source)
- Proven practitioners with documented results
  (Hormozi for sales, Martell for EA ops,
   Munger for capital decisions)
- Primary research data (what actually converts,
  not what sounds good)

Questions to answer:

- Who is the highest-signal source for this?
- What does the authoritative source actually say?
- What patterns appear consistently across
  multiple authoritative sources?
- What do world-class practitioners do
  differently from average practitioners?

### Stage 2 — Document

Capture what the research found.
Not a summary. The actual pattern, rule,
or framework — specific enough to execute.

Format for documentation:

- Source URL and date researched
- The core pattern or rule
- When to apply it
- When NOT to apply it
- What failure looks like
- What success looks like

This document becomes the reference.
Every future build in this domain starts here.

### Stage 3 — Templatize

Turn the documented pattern into a reusable
template. Remove the instance-specific details.
Keep the structure that always works.

A good template:

- Can be instantiated for any context
- Contains the decisions that are always right
- Leaves blank only what must vary per instance
- Is the starting point, not a suggestion

### Stage 4 — Instantiate

Apply the template to the specific context.
Fill in what varies. Adapt what must adapt.
Never change what the research says is universal.

The test: could a world-class practitioner
in this domain look at the output and say
"yes, this is the right approach"?

### Stage 5 — Improve From Outcomes

After real execution:

- What worked exactly as the research predicted?
- What failed despite following the pattern?
- What worked better than expected?
- What does the authoritative source NOT cover
  that reality revealed?

Update the document and template.
The next instantiation benefits from the
outcomes of the previous one.
This is how EOS compounds over time.

## Where This Principle Lives in EOS

**principle_engine.py**: injected into every
agent at runtime as an operational standard.
Every agent operates by this principle.

**CLAUDE.md**: governs every CC session.
Claude Code itself operates by this principle
before building anything in EOS.

**This skill**: loaded on demand before any
new domain build. Walks through the cycle
explicitly when needed.

**Canonical templates (/opt/OS/templates/)**:
the principle made concrete. Every template
is a crystallized best practice ready to
instantiate. The principle explains WHY
templates exist. The templates ARE the
principle in action.

## How to Apply This to Any Domain

### Before building a new skill:

1. What is the world-class approach to this
   capability? Who does it best?
2. What does the authoritative source say?
3. Does a template exist in /opt/OS/templates/?
4. If not — research, document, then build.
5. After first use — update with outcomes.

### Before integrating a new tool:

1. Read the official documentation fully.
2. Read what the creator of the tool says
   about how to use it correctly.
3. Check the tool skill in
   /opt/OS/skills/tools/ — does it exist?
4. If not — research, build the tool skill,
   then integrate.
5. Add last_researched date. Update when
   new versions ship.

### Before configuring a new agent:

1. What does a world-class version of this
   role do? Who is the authoritative source?
2. What frameworks apply to this domain?
3. Check /opt/OS/templates/agents/ for
   the template.
4. Instantiate from template, not from scratch.
5. After first real interaction — what judgment
   gaps exist? Update soul doc.

### Before designing a new workflow:

1. Has this workflow been done before
   anywhere in EOS?
2. If yes — load the existing skill or
   workflow template. Don't rebuild.
3. If no — find the world-class approach first.
4. Document it. Build from that.

## Examples in EOS

### Claude Code configuration:

Research source: official docs +
  Boris Cherny (creator).
Output: /opt/OS/skills/meta/
  claude_code_best_practices/SKILL.md
Template: .claude/settings.json structure,
  hook patterns, subagent frontmatter.

### Sales closing:

Research source: Alex Hormozi —
  $100M Offers, $100M Leads.
Output: operational standards in
  ceo_operational_standards.py
Template: /opt/OS/templates/ offer structure.
Skill: skills/sales/proof_promise_plan_close/

### EA operations:

Research source: Dan Martell —
  Buy Back Your Time.
Output: ea_operational_standards.py
Template: ideal_week.py framework.
Skill: skills/ EA-specific workflows.

### Capital allocation:

Research source: Charlie Munger, Ray Dalio.
Output: portfolio_advisor_standards.py

## The Anti-Patterns

Never do this:

- Build from assumptions without research
- Use a secondary source when the primary
  source is available
- Copy a framework verbatim without
  adapting to EOS context
- Skip the templatization step because
  "this is a one-off"
- Fail to update the template after outcomes
- Start a new domain build without checking
  if a template already exists

## Gotchas

- Authoritative does not equal popular. A blog post
  with 10,000 shares is not the same as
  the original source.
- Research takes time upfront but saves
  multiples in rework. The pressure to skip
  research is always wrong.
- Templates become stale. Add last_updated
  dates and update when outcomes contradict
  the template.
- When two authoritative sources contradict
  each other, test both. Let EOS outcomes
  determine which is right for this context.
- The principle applies to the principle
  itself. This skill was built by applying
  it to the domain of EOS system design.
