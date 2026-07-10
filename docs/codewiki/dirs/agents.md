---
type: codewiki-dir
dir: agents
---

# `agents/` — agent SOUL documents (character, not mechanics)

**11 files · 50,436 bytes · [Full file inventory](../inventory/agents.md)**

## Purpose
`agents/` holds the **soul documents** for UMH's org of agents — one Markdown
file per role in the EntrepreneurOS agent organization. A soul doc defines an
agent's *character*: its identity, its judgment (how it makes decisions), its
role boundary and authority tier, its communication standard, and its hard
stops. It deliberately contains **no mechanics and no process steps** — those
live in Python modules and in [`skills/`](./skills.md) respectively. Per the
Developer Agent soul document in `CLAUDE.md`, "Soul docs follow 5-section
structure." These files are what give each agent a stable persona and a clear
lane; they are the answer to "who is this agent and what is it allowed to
decide," not "how does it do the work."

## How it fits
`agents/` is a knowledge/config surface — like `skills/` and `.agents/`, it is
read at runtime, not imported as a Python module. The agents described here are
the EOS projection's employee roster (CEO, Sales, Marketing, Product,
Engineering, Operations, Finance, HR, Legal, Customer Success, Computer-Use).
They are registered in Neon (per `CLAUDE.md`: "Agents registered in Neon not
just in code") and loaded by the agent runtime in `adapters/models/` and the
control plane in `substrate/`. The soul doc supplies the persona and judgment
frame; the runtime supplies the model routing (`call_with_fallback`), the skills
supply the step-by-step workflows, and the substrate supplies governance and
authority enforcement. The five-section structure and the "character only, no
mechanics" rule are enforced by `.claude/rules/agents.md`.

## Structure
A flat directory — 11 role soul docs, no subdirectories:

| File | Lines | Role / authority focus |
|---|---|---|
| `ceo_agent.md` | 116 | Strategic orchestrator for the EOS projection; authority tier COMMIT; plans/delegates/reviews, does not execute |
| `engineering_agent.md` | 132 | Technical execution role |
| `legal_agent.md` | 132 | Legal review and risk |
| `product_agent.md` | 129 | Product direction |
| `operations_agent.md` | 124 | Operations coordination |
| `finance_agent.md` | 122 | Finance and unit economics |
| `customer_success_agent.md` | 121 | Retention and onboarding |
| `marketing_agent.md` | 121 | Marketing and content strategy |
| `hr_agent.md` | 117 | People/hiring |
| `sales_agent.md` | 110 | Sales execution and pipeline |
| `computer_use_agent.md` | 40 | Computer-use / browser-automation role (thinnest soul — a narrow, tool-bound agent) |

## Key components
`ceo_agent.md` is the reference implementation of the soul-doc form and the most
load-bearing persona. Its **Identity** section fixes the role ("primary
strategic orchestrator for the EntrepreneurOS projection … You do not execute")
and its authority tier (COMMIT — approves plans and allocates resources, founder
retains final say on irreversible decisions). Its **Judgment** section codifies
the four decision lenses applied in order — Reality → Intelligence →
Personalization → Execution — the same four pillars every UMH feature must serve
per `PHILOSOPHY.md`, and it makes stage-awareness the CEO's most critical faculty
(pre-revenue = close the first sale; everything else is "distraction dressed as
progress"). The other soul docs follow the same 5-section shape (Identity,
Judgment, role boundary, communication standard, hard stops) scaled to their
domain. `computer_use_agent.md` (40 lines) is the outlier — a deliberately
narrow, tool-scoped agent with a small persona surface.

## Data & state
- **Reads:** at runtime, agents resolve instance context (founder name, company,
  stage, north star) from BIS rather than from literals in the soul doc — the
  soul docs stay projection-generic in text and become instance-specific only
  when loaded. The CEO's "north star: $10K/month net profit" is the founder's
  north star surfaced through this path, not a hardcoded platform value.
- **Registered in:** Neon (agent registry) — soul docs are not the only record
  of an agent's existence; the registry is authoritative for what is live.
- **Writes:** none — soul docs are static persona definitions.

## Gotchas
- **Do not confuse `agents/` (soul docs) with `.claude/agents/` (CC native
  subagents).** They are two different layers that must not duplicate content.
  `agents/` = character/persona (identity, judgment, hard stops). `.claude/agents/`
  = Claude Code auto-delegated subagents with executable mechanics — the four
  `eos-*` reviewers (`eos-code-reviewer`, `eos-verifier`, `eos-simplifier`,
  `eos-researcher`), each with `name`/`description`/`model`/`tools` frontmatter,
  a Gotchas section, and a verification step. See [dot-claude.md](./dot-claude.md).
  Per `.claude/rules/agents.md`: never put process steps in soul docs, never put
  character in CC subagents, and never duplicate content between the two.
- **Soul docs carry no mechanics on purpose.** If you find yourself wanting to
  add "how to do X" steps to a soul doc, that belongs in a `skills/<Domain>/`
  skill; if you want to add code, it belongs in a Python module. The soul doc's
  job is to constrain judgment and authority, not to script behavior.
- **Under-300-line rule.** `.claude/rules/agents.md` caps soul docs at 300 lines
  and requires the description frontmatter to be written as a trigger condition.
  All 11 current files are well under the cap (largest: 132 lines).
- **Authority tiers are real governance inputs**, not flavor text. The CEO's
  COMMIT tier maps to the substrate authority engine's approval gates — the soul
  doc names the tier, the substrate enforces it.

## See also
- [dot-claude.md](./dot-claude.md) — `.claude/agents/` CC native subagents (the mechanics layer, contrasted above)
- [skills.md](./skills.md) — the workflow/process layer these agents load (`ceo_framework`, `sales`, `ops` skills)
- [substrate.md](./substrate.md) — the control plane and authority engine that enforce agent authority tiers
- [adapters.md](./adapters.md) — the model runtime (`call_with_fallback`) that runs these agents
- [architecture.md](../architecture.md) — the projection/substrate split and the four-pillar philosophy
