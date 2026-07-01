# P1 Backlog — Post v1.0.0

Everything deferred from v1.0.0 release. These items extend the platform
through its published contracts — none require architectural changes.

---

## Deferred from v1.0.0

| Item | Risk | Reason Deferred |
|---|---|---|
| ApprovalStore SQL→JSONL migration | MEDIUM | Different backends (Neon vs JSONL), authority_engine has 3 import sites |
| Browser walkthrough verification | LOW | Requires executor node with display; API-level verification passed |

## P1 — Core Operator Workflows

| Item | Description |
|---|---|
| Research workflow | Governed research through browser + web search capabilities |
| Coding workflow | Code generation and review through governed mutation |
| Planning workflow | Strategic planning through intent → plan → approve → execute |
| Execution workflow | Task execution with proof generation and timeline |
| Communication workflow | Discord/Slack/email through governed channel_message_send |
| Review workflow | Code review and quality assessment through governed mutation |

## P2 — Capability Expansion

| Item | Description |
|---|---|
| Voice qualification | LiveKit voice interface end-to-end verification |
| Continuous SLO daemon | Runtime monitoring with automatic alerting |
| GitHub workflow capability | PR creation, review, merge through governed mutation |
| Figma integration | Design system sync through governed mutation |
| Document generation | Report and document creation capability |
| Browser task automation | Full browser workflow through governed mutation |
| Slack adapter | Slack transport for operator notifications |

## P3 — Productization

| Item | Description |
|---|---|
| Autonomous execution | Operator-approved autonomous work cycles |
| Strategy fallback chain | Multi-strategy reasoning with fallback |
| Customer-facing products | Operator experiences exposed as products |

---

## Rules

All P1-P3 work must:
- Extend PLATFORM_SPEC.md contracts, not redesign them
- Use canonical governed_mutation() path
- Use event spine for state changes
- Pass qualification regression before merge
- Preserve ORL-8 and runtime SLOs
- Follow the Breaking Change Process for any contract modifications
