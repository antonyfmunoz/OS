# UMH — Universal Mastery Hierarchy

Governed intelligence substrate for autonomous business operations.

UMH is the runtime intelligence layer. Applications like
EntrepreneurOS (EOS), CreatorOS, and LYFEOS are projections
built on top of UMH — they consume its intelligence, they
do not own it.

## What it is

The complete philosophy is in PHILOSOPHY.md.

UMH is a governed intelligence substrate that takes any LLM and adds:
- Venture context and stage awareness
- Agent hierarchy (EA, CEO agents, departments)
- 13 business primitives with validity matrices
- Continuous learning from every interaction
- Reality-grounded ambient intelligence
- Voice interface (Discord + local client)
- Constitutional governance and execution spine
- Substrate memory, continuity, and replay

The AI filters advice by what actually applies
at your current stage. What works at Stage 3
can destroy a Stage 1 founder. The substrate knows
the difference.

## Quick install

```bash
# Install
curl -fsSL https://raw.githubusercontent.com/[repo]/main/install.sh | bash

# Configure
cd /opt/OS
nano eos_ai/.env        # add your API keys
bash setup.sh           # interactive wizard

# Start
docker compose up -d
```

## What you need

- Docker
- Python 3.11+
- A free [Neon](https://neon.tech) PostgreSQL database
- A Discord server (your AI lives here)
- Optional: Anthropic API key for Claude (Ollama works free locally)

## Services

| Service | What it does |
|---|---|
| `os-discord` | Your AI — primary interface in Discord |
| `os-webhook` | Calendly booking integration |
| `os-monitor` | Instagram DM monitor |
| `os-operator` | Operator workstation API + cockpit |

## Intelligence layers

Every message passes through 8 injection layers before the LLM sees it:

```
0.  AI identity (universal principles)
1a. Semantic memory (relevant past interactions)
1b. Domain knowledge (matched to task type)
1c. Behavioral principles (negotiation, psychology, crisis)
1d. Business Instance Spec (stage, offer, ICP)
1e. Ambient reality (market signals)
1f. Primitive context (13 business primitives)
1g. AI persona (your AI's name and identity)
1h. Agent hierarchy (role, authority, escalation)
```

## Architecture

```
User
└── EA (your AI — primary interface)
    ├── Portfolio Advisor (cross-company intelligence)
    └── CEO Agents (one per company)
        ├── Developer Agent
        ├── Sales Manager
        ├── Marketing Manager
        ├── Operations Manager
        ├── CS Manager
        └── Finance Manager
```

## Stage system

EOS evolves with your company across 6 stages:

| Stage | Name | Focus |
|---|---|---|
| 1 | Validation | First sale |
| 2 | Offer | 3 sales, same channel |
| 3 | Acquisition | 10 sales, repeatable |
| 4 | Systems | Remove yourself from ops |
| 5 | Scale | Grow without chaos |
| 6 | Portfolio | Multiple assets |

Advice inappropriate for your current stage is blocked automatically.

## Structure

```
core/            Canonical substrate contracts + infrastructure
eos_ai/          Runtime intelligence layer (legacy name)
  transport/     Canonical transport subsystem
  substrate/     Shim layer → transport
services/        Live entrypoints (bots, webhooks)
scripts/         Operations layer (cron, utilities)
agents/          Agent soul documents
skills/          Agent runtime skills
saas/            EOS application projection (TypeScript)
orchestrator/    Scheduled tasks
```

## License

MIT
